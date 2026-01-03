#!/usr/bin/env python3
"""
Minimal BLE MIDI with USB Forwarding
=====================================
Forwards MIDI from USB controller to BLE.
"""

import dbus
import dbus.mainloop.glib
import dbus.service
from gi.repository import GLib
import mido
import threading

# BLE MIDI UUIDs (standard)
MIDI_SERVICE_UUID = '03b80e5a-ede8-4b33-a751-6ce34ec4c700'
MIDI_CHAR_UUID = '7772e5db-3868-4112-a1a9-f2669d106bf3'

BLUEZ = 'org.bluez'
ADAPTER_PATH = '/org/bluez/hci0'
AGENT_PATH = '/org/bluez/midi/agent'
AGENT_IFACE = 'org.bluez.Agent1'

# =============================================================================
# Pairing Agent - Auto-accepts pairing with "Just Works" mode
# =============================================================================

class PairingAgent(dbus.service.Object):
    """BlueZ pairing agent that auto-accepts all pairing requests."""

    def __init__(self, bus):
        dbus.service.Object.__init__(self, bus, AGENT_PATH)

    @dbus.service.method(AGENT_IFACE, in_signature='', out_signature='')
    def Release(self):
        print("[AGENT] Released")

    @dbus.service.method(AGENT_IFACE, in_signature='os', out_signature='')
    def AuthorizeService(self, device, uuid):
        print(f"[AGENT] AuthorizeService: {device} {uuid}")
        return  # Auto-authorize

    @dbus.service.method(AGENT_IFACE, in_signature='o', out_signature='')
    def RequestAuthorization(self, device):
        print(f"[AGENT] RequestAuthorization: {device}")
        return  # Auto-authorize

    @dbus.service.method(AGENT_IFACE, in_signature='o', out_signature='s')
    def RequestPinCode(self, device):
        print(f"[AGENT] RequestPinCode: {device}")
        return "0000"

    @dbus.service.method(AGENT_IFACE, in_signature='o', out_signature='u')
    def RequestPasskey(self, device):
        print(f"[AGENT] RequestPasskey: {device}")
        return dbus.UInt32(0)

    @dbus.service.method(AGENT_IFACE, in_signature='ouq', out_signature='')
    def DisplayPasskey(self, device, passkey, entered):
        print(f"[AGENT] DisplayPasskey: {device} {passkey}")

    @dbus.service.method(AGENT_IFACE, in_signature='os', out_signature='')
    def DisplayPinCode(self, device, pincode):
        print(f"[AGENT] DisplayPinCode: {device} {pincode}")

    @dbus.service.method(AGENT_IFACE, in_signature='ou', out_signature='')
    def RequestConfirmation(self, device, passkey):
        print(f"[AGENT] RequestConfirmation: {device} {passkey} - AUTO ACCEPTING")
        return  # Auto-confirm

    @dbus.service.method(AGENT_IFACE, in_signature='', out_signature='')
    def Cancel(self):
        print("[AGENT] Cancel")


class MidiChar(dbus.service.Object):
    PATH = '/org/bluez/midi/char0'

    def __init__(self, bus):
        dbus.service.Object.__init__(self, bus, self.PATH)
        self.notifying = False

    def get_properties(self):
        return {
            'org.bluez.GattCharacteristic1': {
                'Service': dbus.ObjectPath('/org/bluez/midi/service0'),
                'UUID': MIDI_CHAR_UUID,
                # encrypt-* flags force macOS to initiate pairing before using the characteristic
                'Flags': dbus.Array([
                    'read', 'encrypt-read',
                    'write-without-response', 'encrypt-write',
                    'notify', 'encrypt-notify'
                ], signature='s'),
                'Descriptors': dbus.Array([], signature='o')
            }
        }

    @dbus.service.method('org.freedesktop.DBus.Properties', in_signature='s', out_signature='a{sv}')
    def GetAll(self, iface):
        return self.get_properties().get(iface, {})

    @dbus.service.method('org.bluez.GattCharacteristic1', in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, opts):
        return dbus.Array([], signature='y')

    @dbus.service.method('org.bluez.GattCharacteristic1', in_signature='aya{sv}')
    def WriteValue(self, value, opts):
        print(f"[RX] {list(value)}")

    @dbus.service.method('org.bluez.GattCharacteristic1')
    def StartNotify(self):
        self.notifying = True
        print("[CONNECTED] Client subscribed!")

    @dbus.service.method('org.bluez.GattCharacteristic1')
    def StopNotify(self):
        self.notifying = False
        print("[DISCONNECTED] Client unsubscribed")

    @dbus.service.signal('org.freedesktop.DBus.Properties', signature='sa{sv}as')
    def PropertiesChanged(self, iface, changed, invalidated):
        pass

    def send_midi(self, midi_bytes):
        """Send MIDI bytes over BLE - minimal, no processing."""
        if not self.notifying:
            return False
        # BLE-MIDI packet: [header, timestamp, ...midi]
        value = dbus.Array(bytes([0x80, 0x80]) + midi_bytes, signature='y')
        self.PropertiesChanged('org.bluez.GattCharacteristic1', {'Value': value}, [])
        return False  # Return False to remove from idle queue

class MidiService(dbus.service.Object):
    PATH = '/org/bluez/midi/service0'

    def __init__(self, bus):
        dbus.service.Object.__init__(self, bus, self.PATH)

    def get_properties(self):
        return {
            'org.bluez.GattService1': {
                'UUID': MIDI_SERVICE_UUID,
                'Primary': dbus.Boolean(True),
                'Characteristics': dbus.Array([dbus.ObjectPath(MidiChar.PATH)], signature='o')
            }
        }

    @dbus.service.method('org.freedesktop.DBus.Properties', in_signature='s', out_signature='a{sv}')
    def GetAll(self, iface):
        return self.get_properties().get(iface, {})

class App(dbus.service.Object):
    PATH = '/'

    def __init__(self, bus, service, char):
        dbus.service.Object.__init__(self, bus, self.PATH)
        self.service = service
        self.char = char

    @dbus.service.method('org.freedesktop.DBus.ObjectManager', out_signature='a{oa{sa{sv}}}')
    def GetManagedObjects(self):
        return {
            dbus.ObjectPath(MidiService.PATH): self.service.get_properties(),
            dbus.ObjectPath(MidiChar.PATH): self.char.get_properties()
        }

class Advert(dbus.service.Object):
    PATH = '/org/bluez/midi/ad0'

    def __init__(self, bus):
        dbus.service.Object.__init__(self, bus, self.PATH)

    def get_properties(self):
        return {
            'org.bluez.LEAdvertisement1': {
                'Type': dbus.String('peripheral'),
                'ServiceUUIDs': dbus.Array([MIDI_SERVICE_UUID], signature='s'),
                'LocalName': dbus.String('PiBLE'),
                'Includes': dbus.Array(['tx-power'], signature='s')
            }
        }

    @dbus.service.method('org.freedesktop.DBus.Properties', in_signature='s', out_signature='a{sv}')
    def GetAll(self, iface):
        return self.get_properties().get(iface, {})

    @dbus.service.method('org.bluez.LEAdvertisement1')
    def Release(self):
        print("[AD] Released")


def find_midi_input():
    """Find a USB MIDI input device. Prefers 'MIDI In' over 'DAW In' ports."""
    candidates = []
    for name in mido.get_input_names():
        if 'Through' not in name and 'RtMidi' not in name:
            candidates.append(name)

    if not candidates:
        return None

    # Prefer ports with "MIDI In" over "DAW In" (for Launchpad X, etc.)
    for name in candidates:
        if 'MIDI In' in name:
            return name

    # Fall back to first candidate
    return candidates[0]


def midi_monitor_thread(char):
    """Monitor for MIDI devices and forward messages. Auto-reconnects on unplug."""
    import time
    current_device = None
    midi_in = None

    while True:
        try:
            # Check for available MIDI input
            available = find_midi_input()

            # If no device and we had one, it was unplugged
            if available is None:
                if current_device:
                    print(f"[MIDI] {current_device} disconnected")
                    current_device = None
                    if midi_in:
                        try:
                            midi_in.close()
                        except Exception:
                            pass
                        midi_in = None
                time.sleep(1)  # Poll every second when no device
                continue

            # If device changed, switch to new one
            if available != current_device:
                if midi_in:
                    try:
                        midi_in.close()
                    except Exception:
                        pass
                print(f"[MIDI] Connecting to: {available}")
                midi_in = mido.open_input(available)
                current_device = available
                print(f"[MIDI] Ready: {current_device}")

            # Read MIDI messages (non-blocking with timeout)
            for msg in midi_in.iter_pending():
                midi_bytes = msg.bytes()
                if char.notifying:
                    GLib.timeout_add(0, char.send_midi, midi_bytes)
                    print(f"[TX] {msg}")
                else:
                    print(f"[--] {msg} (no client)")

            time.sleep(0.001)  # Small delay to prevent CPU spin

        except Exception as e:
            print(f"[MIDI] Error: {e}")
            current_device = None
            if midi_in:
                try:
                    midi_in.close()
                except Exception:
                    pass
                midi_in = None
            time.sleep(1)  # Wait before retry


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()

    # Power on adapter
    props = dbus.Interface(bus.get_object(BLUEZ, ADAPTER_PATH), 'org.freedesktop.DBus.Properties')
    props.Set('org.bluez.Adapter1', 'Powered', dbus.Boolean(True))
    props.Set('org.bluez.Adapter1', 'Discoverable', dbus.Boolean(True))
    props.Set('org.bluez.Adapter1', 'Pairable', dbus.Boolean(True))
    print("[OK] Adapter powered")

    # Register pairing agent
    agent = PairingAgent(bus)
    agent_mgr = dbus.Interface(bus.get_object(BLUEZ, '/org/bluez'), 'org.bluez.AgentManager1')
    try:
        agent_mgr.RegisterAgent(dbus.ObjectPath(AGENT_PATH), 'NoInputNoOutput')
        agent_mgr.RequestDefaultAgent(dbus.ObjectPath(AGENT_PATH))
        print("[OK] Pairing agent registered")
    except Exception as e:
        print(f"[WARN] Agent: {e}")

    # Create GATT
    service = MidiService(bus)
    char = MidiChar(bus)
    app = App(bus, service, char)

    # Register GATT
    gatt_mgr = dbus.Interface(bus.get_object(BLUEZ, ADAPTER_PATH), 'org.bluez.GattManager1')
    gatt_mgr.RegisterApplication(dbus.ObjectPath('/'), {},
        reply_handler=lambda: print("[OK] GATT registered"),
        error_handler=lambda e: print(f"[ERR] GATT: {e}"))

    # Create and register advertisement
    ad = Advert(bus)
    ad_mgr = dbus.Interface(bus.get_object(BLUEZ, ADAPTER_PATH), 'org.bluez.LEAdvertisingManager1')
    ad_mgr.RegisterAdvertisement(dbus.ObjectPath(Advert.PATH), {},
        reply_handler=lambda: print("[OK] Advertising as 'PiBLE'"),
        error_handler=lambda e: print(f"[ERR] Ad: {e}"))

    # Start MIDI monitor thread (auto-detects and reconnects devices)
    t = threading.Thread(target=midi_monitor_thread, args=(char,), daemon=True)
    t.start()
    print("[OK] MIDI monitor started (auto-detects controllers)")

    print("\nReady! Connect from iOS.")
    GLib.MainLoop().run()

if __name__ == '__main__':
    main()
