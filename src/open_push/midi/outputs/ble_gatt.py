
import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib
import sys
import threading
import time
import mido

BLUEZ_SERVICE_NAME = 'org.bluez'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'
ADAPTER_IFACE = 'org.bluez.Adapter1'

LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'

# BLE MIDI UUIDs
MIDI_SERVICE_UUID = '03B80E5A-EDE8-4B33-A751-6CE34EC4C700'
MIDI_CHRC_UUID = '7772E5DB-3868-4112-A1A9-F2669D106BF3'

class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'

class NotSupportedException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.bluez.Error.NotSupported'

class Application(dbus.service.Object):
    def __init__(self, bus):
        self.path = '/'
        self.services = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_service(self, service):
        self.services.append(service)

    @dbus.service.method(DBUS_OM_IFACE, out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            chrcs = service.get_characteristics()
            for chrc in chrcs:
                response[chrc.get_path()] = chrc.get_properties()
        return response

class Service(dbus.service.Object):
    PATH_BASE = '/org/bluez/example/service'

    def __init__(self, bus, index, uuid, primary):
        self.path = self.PATH_BASE + str(index)
        self.bus = bus
        self.uuid = uuid
        self.primary = primary
        self.characteristics = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.uuid,
                'Primary': self.primary,
                'Characteristics': dbus.Array(
                    self.get_characteristic_paths(),
                    signature='o')
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, chrc):
        self.characteristics.append(chrc)

    def get_characteristic_paths(self):
        result = []
        for chrc in self.characteristics:
            result.append(chrc.get_path())
        return result

    def get_characteristics(self):
        return self.characteristics

class Characteristic(dbus.service.Object):
    def __init__(self, bus, index, uuid, flags, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = uuid
        self.service = service
        self.flags = flags
        self.descriptors = []
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags,
                'Descriptors': dbus.Array(
                    self.get_descriptor_paths(),
                    signature='o')
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_descriptor_paths(self):
        result = []
        for desc in self.descriptors:
            result.append(desc.get_path())
        return result

    def get_descriptors(self):
        return self.descriptors

    @dbus.service.signal(DBUS_PROP_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE,
                        in_signature='a{sv}',
                        out_signature='ay')
    def ReadValue(self, options):
        # MIDI reads are generally not used for data transfer, 
        # but required for characteristic discovery
        return []

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        # Override this
        pass

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        # Override this
        pass

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        # Override this
        pass

class MidiCharacteristic(Characteristic):
    def __init__(self, bus, index, service, midi_out_port):
        Characteristic.__init__(
            self, bus, index,
            MIDI_CHRC_UUID,
            ['read', 'write', 'write-without-response', 'notify'],
            service)
        self.notifying = False
        self.midi_out_port = midi_out_port

    def WriteValue(self, value, options):
        # Data received from BLE (e.g. from iPad) -> Send to MIDI Output
        data = bytearray(value)
        if len(data) < 3:
            return

        # Strip BLE MIDI Header (Byte 0) and Timestamp (Byte 1)
        # Ideally we should respect timestamps, but for real-time we just process immediately
        midi_bytes = data[2:]
        
        if len(midi_bytes) > 0:
            # Parse raw bytes into messages
            parser = mido.Parser()
            parser.feed(midi_bytes)
            for msg in parser:
                if self.midi_out_port:
                    self.midi_out_port.send(msg)

    def StartNotify(self):
        if self.notifying:
            return
        self.notifying = True
        print("BLE MIDI Notification started (Client connected)")

    def StopNotify(self):
        if not self.notifying:
            return
        self.notifying = False
        print("BLE MIDI Notification stopped (Client disconnected)")

    def send_midi_notification(self, data):
        if not self.notifying:
            return False

        try:
            # Wrap MIDI data in BLE-MIDI packet
            # Byte 0: Header (0x80 | (timestamp_high & 0x3F))
            # Byte 1: Timestamp Low (0x80 | (timestamp_low & 0x7F))
            # Byte 2...: MIDI Data (Status byte must be prefixed with timestamp if generic)

            # Simplified: Use 0x80 as header (timestamp 0) and 0x80 as timestamp
            ble_packet = [0x80, 0x80] + list(data)

            value = dbus.Array(ble_packet, signature=dbus.Signature('y'))
            self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': value}, [])
            return True
        except Exception as e:
            print(f"Error sending notification: {e}")
            return False

class MidiAdvertisement(dbus.service.Object):
    def __init__(self, bus, index):
        self.path = '/org/bluez/example/advertisement' + str(index)
        self.bus = bus
        self.ad_type = 'peripheral'
        self.service_uuids = [MIDI_SERVICE_UUID]
        # Use short name to fit in 31-byte advertising packet
        # 128-bit UUID = 18 bytes, short name must be < 10 bytes
        self.local_name = 'OP MIDI'
        self.include_tx_power = False
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        properties = dict()
        properties['Type'] = self.ad_type
        properties['ServiceUUIDs'] = dbus.Array(self.service_uuids,
                                              signature='s')
        # Put local name in scan response via Includes, not in main advertising
        properties['Includes'] = dbus.Array(['local-name'], signature='s')
        properties['IncludeTxPower'] = dbus.Boolean(self.include_tx_power)
        return {LE_ADVERTISEMENT_IFACE: properties}

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE,
                         in_signature='s',
                         out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE,
                         in_signature='',
                         out_signature='')
    def Release(self):
        print('%s: Released!' % self.path)

def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    for path, ifaces in objects.items():
        if ADAPTER_IFACE not in ifaces:
            continue
        if LE_ADVERTISING_MANAGER_IFACE not in ifaces:
            continue
        if GATT_MANAGER_IFACE not in ifaces:
            continue
        return path
    raise RuntimeError('No Bluetooth adapter with LE advertising + GATT support found')


def ensure_adapter_powered(bus, adapter_path):
    props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter_path), DBUS_PROP_IFACE)
    try:
        props.Set(ADAPTER_IFACE, 'Powered', dbus.Boolean(True))
    except dbus.DBusException:
        pass

    for _ in range(50):
        try:
            if bool(props.Get(ADAPTER_IFACE, 'Powered')):
                break
        except dbus.DBusException:
            pass
        time.sleep(0.1)
    else:
        raise RuntimeError('Bluetooth adapter did not become Powered')

    # Set discoverable and pairable (required for iOS visibility)
    print("Setting adapter discoverable...")
    try:
        props.Set(ADAPTER_IFACE, 'Discoverable', dbus.Boolean(True))
        props.Set(ADAPTER_IFACE, 'Pairable', dbus.Boolean(True))
    except dbus.DBusException as e:
        print(f"Warning: Could not set discoverable: {e}")


def register_app_cb():
    print('GATT application registered')

def register_app_error_cb(error):
    print(f'Failed to register GATT application: {error}')
    mainloop.quit()

def register_ad_cb():
    print('Advertisement registered')

def register_ad_error_cb(error):
    print(f'Failed to register advertisement: {error}')
    mainloop.quit()

def main():
    global mainloop
    
    # Ensure stdout is flushed for systemd logs
    sys.stdout.reconfigure(line_buffering=True)
    
    print("Initializing OpenPush BLE MIDI Service...")

    try:
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        mainloop = GLib.MainLoop()

        adapter_path = find_adapter(bus)
        ensure_adapter_powered(bus, adapter_path)
        
        # Setup Virtual MIDI Port
        print("Creating virtual MIDI ports...")
        midi_out = mido.open_output('OpenPush BLE', virtual=True)
        midi_in = mido.open_input('OpenPush BLE', virtual=True)
        
        # Setup GATT Server
        print("Setting up GATT server...")
        app = Application(bus)
        service = Service(bus, 0, MIDI_SERVICE_UUID, True)
        
        # Pass midi_out to characteristic so it can forward writes
        midi_chrc = MidiCharacteristic(bus, 0, service, midi_out)
        service.add_characteristic(midi_chrc)
        app.add_service(service)

        # Register Application (async with callbacks)
        print("Registering Application...")
        service_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
                                       GATT_MANAGER_IFACE)
        service_manager.RegisterApplication(
            app.get_path(),
            dbus.Dictionary({}, signature='sv'),
            reply_handler=register_app_cb,
            error_handler=register_app_error_cb
        )

        # Setup Advertisement (async with callbacks)
        print("Registering Advertisement...")
        ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
                                  LE_ADVERTISING_MANAGER_IFACE)
        ad = MidiAdvertisement(bus, 0)
        ad_manager.RegisterAdvertisement(
            ad.get_path(),
            dbus.Dictionary({}, signature='sv'),
            reply_handler=register_ad_cb,
            error_handler=register_ad_error_cb
        )

        # MIDI Forwarding Thread
        def midi_poll():
            print("MIDI Poll thread started")
            while True:
                try:
                    # Poll for messages from the virtual input port
                    # and send them via notification
                    msg = midi_in.poll()
                    if msg:
                        # Convert mido message to bytes
                        data = msg.bytes()
                        # Send notification (only if client connected)
                        if midi_chrc.notifying:
                            GLib.idle_add(midi_chrc.send_midi_notification, data)
                    # 10ms poll interval - fast enough for MIDI, easy on CPU
                    time.sleep(0.01)
                except Exception as e:
                    print(f"Error in MIDI poll: {e}")
                    time.sleep(1)

        t = threading.Thread(target=midi_poll, daemon=True)
        t.start()

        print("BLE MIDI Server Running... Waiting for connections.")
        
        mainloop.run()
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        pass
    finally:
        try:
            if 'ad_manager' in locals():
                ad_manager.UnregisterAdvertisement(ad.get_path())
        except:
            pass
        try:
            if 'service_manager' in locals():
                service_manager.UnregisterApplication(app.get_path())
        except:
            pass

if __name__ == '__main__':
    main()
