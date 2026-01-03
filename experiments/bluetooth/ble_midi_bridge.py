#!/usr/bin/env python3
"""
BLE MIDI Bridge - Simple Experiment
====================================

Forwards MIDI from a USB device (Launchkey Mini) to BLE for iOS.

Usage:
    python3 ble_midi_bridge.py

Requirements (on Pi):
    sudo apt install python3-dbus python3-gi python3-mido python3-rtmidi
"""

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib
import sys
import threading
import time
import mido

# =============================================================================
# Configuration
# =============================================================================

DEVICE_NAME = 'PiBLE MIDI'  # Name that appears on iOS

# BLE MIDI UUIDs (standard)
MIDI_SERVICE_UUID = '03B80E5A-EDE8-4B33-A751-6CE34EC4C700'
MIDI_CHRC_UUID = '7772E5DB-3868-4112-A1A9-F2669D106BF3'

# D-Bus constants
BLUEZ_SERVICE_NAME = 'org.bluez'
ADAPTER_IFACE = 'org.bluez.Adapter1'
LE_ADVERTISING_MANAGER_IFACE = 'org.bluez.LEAdvertisingManager1'
LE_ADVERTISEMENT_IFACE = 'org.bluez.LEAdvertisement1'
GATT_MANAGER_IFACE = 'org.bluez.GattManager1'
GATT_SERVICE_IFACE = 'org.bluez.GattService1'
GATT_CHRC_IFACE = 'org.bluez.GattCharacteristic1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'

# =============================================================================
# D-Bus Exceptions
# =============================================================================

class InvalidArgsException(dbus.exceptions.DBusException):
    _dbus_error_name = 'org.freedesktop.DBus.Error.InvalidArgs'

# =============================================================================
# GATT Application
# =============================================================================

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
            for chrc in service.get_characteristics():
                response[chrc.get_path()] = chrc.get_properties()
        return response

# =============================================================================
# GATT Service
# =============================================================================

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
                    [c.get_path() for c in self.characteristics],
                    signature='o')
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def add_characteristic(self, chrc):
        self.characteristics.append(chrc)

    def get_characteristics(self):
        return self.characteristics

# =============================================================================
# MIDI Characteristic
# =============================================================================

class MidiCharacteristic(dbus.service.Object):
    def __init__(self, bus, index, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = MIDI_CHRC_UUID
        self.service = service
        self.flags = ['read', 'write-without-response', 'notify']
        self.notifying = False
        dbus.service.Object.__init__(self, bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.uuid,
                'Flags': self.flags,
                'Descriptors': dbus.Array([], signature='o')
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        return dbus.Array([], signature='y')

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        # Data from iOS -> could forward to MIDI out if needed
        print(f"[BLE RX] {len(value)} bytes: {list(value)}")

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        if self.notifying:
            return
        self.notifying = True
        print("[BLE] Client subscribed to notifications - READY TO SEND MIDI")

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        if not self.notifying:
            return
        self.notifying = False
        print("[BLE] Client unsubscribed")

    @dbus.service.signal(DBUS_PROP_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

    def send_midi(self, midi_bytes):
        """Send MIDI bytes over BLE."""
        if not self.notifying:
            return False

        # Wrap in BLE-MIDI packet: [header, timestamp, ...midi_bytes]
        ble_packet = [0x80, 0x80] + list(midi_bytes)

        value = dbus.Array(ble_packet, signature=dbus.Signature('y'))
        self.PropertiesChanged(GATT_CHRC_IFACE, {'Value': value}, [])
        return True

# =============================================================================
# Advertisement
# =============================================================================

class Advertisement(dbus.service.Object):
    def __init__(self, bus, index):
        self.path = '/org/bluez/example/advertisement' + str(index)
        self.bus = bus
        dbus.service.Object.__init__(self, bus, self.path)

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_properties(self):
        return {
            LE_ADVERTISEMENT_IFACE: {
                'Type': 'peripheral',
                'ServiceUUIDs': dbus.Array([MIDI_SERVICE_UUID], signature='s'),
                'LocalName': dbus.String(DEVICE_NAME),
                'Includes': dbus.Array(['tx-power'], signature='s'),
            }
        }

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != LE_ADVERTISEMENT_IFACE:
            raise InvalidArgsException()
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE, in_signature='', out_signature='')
    def Release(self):
        print('[ADV] Released')

# =============================================================================
# Helper Functions
# =============================================================================

def find_adapter(bus):
    """Find Bluetooth adapter that supports LE advertising and GATT."""
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    for path, ifaces in objects.items():
        if GATT_MANAGER_IFACE in ifaces and LE_ADVERTISING_MANAGER_IFACE in ifaces:
            return path
    raise RuntimeError('No suitable Bluetooth adapter found')

def setup_adapter(bus, adapter_path):
    """Configure adapter: power on, set name, make discoverable."""
    props = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
        DBUS_PROP_IFACE
    )

    # Power on
    try:
        props.Set(ADAPTER_IFACE, 'Powered', dbus.Boolean(True))
    except:
        pass

    # Wait for power
    for _ in range(30):
        try:
            if props.Get(ADAPTER_IFACE, 'Powered'):
                break
        except:
            pass
        time.sleep(0.1)

    # Set discoverable
    try:
        props.Set(ADAPTER_IFACE, 'Discoverable', dbus.Boolean(True))
        props.Set(ADAPTER_IFACE, 'Pairable', dbus.Boolean(True))
    except Exception as e:
        print(f"[WARN] Could not set discoverable: {e}")

    print(f"[BT] Adapter ready: {adapter_path}")

def find_midi_input():
    """Find a USB MIDI input device (Launchkey, etc)."""
    inputs = mido.get_input_names()
    print(f"[MIDI] Available inputs: {inputs}")

    for name in inputs:
        # Skip virtual/through ports
        if 'Through' in name or 'RtMidi' in name:
            continue
        print(f"[MIDI] Using input: {name}")
        return name

    return None

# =============================================================================
# Main
# =============================================================================

def main():
    print("=" * 50)
    print("  BLE MIDI Bridge - Experiment")
    print("=" * 50)
    print()

    # Initialize D-Bus
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    mainloop = GLib.MainLoop()

    # Find and setup adapter
    adapter_path = find_adapter(bus)
    setup_adapter(bus, adapter_path)

    # Create GATT application
    app = Application(bus)
    service = Service(bus, 0, MIDI_SERVICE_UUID, True)
    midi_chrc = MidiCharacteristic(bus, 0, service)
    service.add_characteristic(midi_chrc)
    app.add_service(service)

    # Register GATT application
    gatt_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
        GATT_MANAGER_IFACE
    )

    def on_gatt_registered():
        print("[GATT] Application registered")

    def on_gatt_error(error):
        print(f"[GATT] Registration failed: {error}")
        mainloop.quit()

    gatt_manager.RegisterApplication(
        app.get_path(),
        dbus.Dictionary({}, signature='sv'),
        reply_handler=on_gatt_registered,
        error_handler=on_gatt_error
    )

    # Create and register advertisement
    ad = Advertisement(bus, 0)
    ad_manager = dbus.Interface(
        bus.get_object(BLUEZ_SERVICE_NAME, adapter_path),
        LE_ADVERTISING_MANAGER_IFACE
    )

    def on_ad_registered():
        print(f"[ADV] Advertising as '{DEVICE_NAME}'")

    def on_ad_error(error):
        print(f"[ADV] Registration failed: {error}")
        mainloop.quit()

    ad_manager.RegisterAdvertisement(
        ad.get_path(),
        dbus.Dictionary({}, signature='sv'),
        reply_handler=on_ad_registered,
        error_handler=on_ad_error
    )

    # Find MIDI input
    midi_input_name = find_midi_input()

    if midi_input_name:
        # MIDI forwarding thread
        def midi_thread():
            print(f"[MIDI] Opening {midi_input_name}...")
            try:
                with mido.open_input(midi_input_name) as midi_in:
                    print("[MIDI] Listening for MIDI messages...")
                    for msg in midi_in:
                        midi_bytes = msg.bytes()
                        if midi_chrc.notifying:
                            GLib.idle_add(midi_chrc.send_midi, midi_bytes)
                            print(f"[MIDI->BLE] {msg}")
                        else:
                            print(f"[MIDI] {msg} (no BLE client)")
            except Exception as e:
                print(f"[MIDI] Error: {e}")

        t = threading.Thread(target=midi_thread, daemon=True)
        t.start()
    else:
        print("[MIDI] No input device found - BLE will still work for testing")

    print()
    print("=" * 50)
    print("  Ready! Connect from iOS Bluetooth MIDI settings")
    print("=" * 50)
    print()

    try:
        mainloop.run()
    except KeyboardInterrupt:
        print("\n[EXIT] Shutting down...")

if __name__ == '__main__':
    main()
