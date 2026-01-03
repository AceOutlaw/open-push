#!/usr/bin/env python3
"""
BLE MIDI Bridge with Integrated Pairing Agent (Auth Fix)
======================================================

This script implements a BLE MIDI Peripheral with a built-in BlueZ Pairing Agent.
It is designed to fix connection issues with macOS/iOS where the device disconnects
due to encryption/pairing failures (LTK Negative Reply).

Key Features:
1. Integrated NoInputNoOutput Agent to handle pairing requests automatically.
2. MIDI Characteristic flags set to 'encrypt-read'/'encrypt-write' to force
   security upgrade (pairing) on connection.
3. Standard BLE MIDI Service/Characteristic UUIDs.

Usage:
    sudo python3 ble_midi_auth_fix.py

Requirements:
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

DEVICE_NAME = 'OpenPush BLE'

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
AGENT_MANAGER_IFACE = 'org.bluez.AgentManager1'
AGENT_IFACE = 'org.bluez.Agent1'
DBUS_OM_IFACE = 'org.freedesktop.DBus.ObjectManager'
DBUS_PROP_IFACE = 'org.freedesktop.DBus.Properties'

# =============================================================================
# Pairing Agent
# =============================================================================

class Agent(dbus.service.Object):
    def __init__(self, bus, path):
        self.path = path
        self.bus = bus
        dbus.service.Object.__init__(self, bus, self.path)
        print(f"Agent initialized at {path}")

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Release(self):
        print("[Agent] Release")

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def AuthorizeService(self, device, uuid):
        print(f"[Agent] AuthorizeService ({device}, {uuid})")
        return

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="s")
    def RequestPinCode(self, device):
        print(f"[Agent] RequestPinCode ({device})")
        return "0000"

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="u")
    def RequestPasskey(self, device):
        print(f"[Agent] RequestPasskey ({device})")
        return dbus.UInt32(0)

    @dbus.service.method(AGENT_IFACE, in_signature="ouq", out_signature="")
    def DisplayPasskey(self, device, passkey, entered):
        print(f"[Agent] DisplayPasskey ({device}, {passkey} entered {entered})")

    @dbus.service.method(AGENT_IFACE, in_signature="os", out_signature="")
    def DisplayPinCode(self, device, pincode):
        print(f"[Agent] DisplayPinCode ({device}, {pincode})")

    @dbus.service.method(AGENT_IFACE, in_signature="ou", out_signature="")
    def RequestConfirmation(self, device, passkey):
        print(f"[Agent] RequestConfirmation ({device}, {passkey})")
        return

    @dbus.service.method(AGENT_IFACE, in_signature="o", out_signature="")
    def RequestAuthorization(self, device):
        print(f"[Agent] RequestAuthorization ({device})")
        return

    @dbus.service.method(AGENT_IFACE, in_signature="", out_signature="")
    def Cancel(self):
        print("[Agent] Cancel")

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

class MidiCharacteristic(dbus.service.Object):
    def __init__(self, bus, index, service):
        self.path = service.path + '/char' + str(index)
        self.bus = bus
        self.uuid = MIDI_CHRC_UUID
        self.service = service
        
        # KEY CHANGE: 'encrypt-read' and 'encrypt-write' force pairing
        self.flags = [
            'read', 
            'write', 
            'write-without-response', 
            'notify',
            'encrypt-read',
            'encrypt-write'
        ]
        
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
            raise Exception('org.freedesktop.DBus.Error.InvalidArgs')
        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        # Empty read, but triggers encryption check due to flag
        return dbus.Array([], signature='y')

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='aya{sv}')
    def WriteValue(self, value, options):
        # Handle incoming MIDI
        pass

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        if self.notifying:
            return
        self.notifying = True
        print("[BLE] Notifications started")

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        if not self.notifying:
            return
        self.notifying = False
        print("[BLE] Notifications stopped")

    @dbus.service.signal(DBUS_PROP_IFACE, signature='sa{sv}as')
    def PropertiesChanged(self, interface, changed, invalidated):
        pass

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
            raise Exception('org.freedesktop.DBus.Error.InvalidArgs')
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE, in_signature='', out_signature='')
    def Release(self):
        print('[ADV] Released')

# =============================================================================
# Main
# =============================================================================

def find_adapter(bus):
    remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/'), DBUS_OM_IFACE)
    objects = remote_om.GetManagedObjects()
    for path, ifaces in objects.items():
        if GATT_MANAGER_IFACE in ifaces and LE_ADVERTISING_MANAGER_IFACE in ifaces:
            return path
    raise RuntimeError('No suitable Bluetooth adapter found')

def setup_adapter(bus, adapter_path):
    props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter_path), DBUS_PROP_IFACE)
    props.Set(ADAPTER_IFACE, 'Powered', dbus.Boolean(True))
    props.Set(ADAPTER_IFACE, 'Discoverable', dbus.Boolean(True))
    props.Set(ADAPTER_IFACE, 'Pairable', dbus.Boolean(True))
    props.Set(ADAPTER_IFACE, 'Alias', dbus.String(DEVICE_NAME))

def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SystemBus()
    mainloop = GLib.MainLoop()

    adapter_path = find_adapter(bus)
    setup_adapter(bus, adapter_path)
    print(f"Using adapter: {adapter_path}")

    # 1. Register Agent
    agent_path = "/org/bluez/example/agent"
    agent = Agent(bus, agent_path)
    agent_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, '/org/bluez'), AGENT_MANAGER_IFACE)
    
    # Unregister any existing agent
    try:
        agent_manager.UnregisterAgent(agent_path)
    except:
        pass
        
    agent_manager.RegisterAgent(agent_path, "NoInputNoOutput")
    print("Agent registered (NoInputNoOutput)")
    
    try:
        agent_manager.RequestDefaultAgent(agent_path)
        print("Agent set as default")
    except Exception as e:
        print(f"Warning: Could not set default agent: {e}")

    # 2. Register GATT
    app = Application(bus)
    service = Service(bus, 0, MIDI_SERVICE_UUID, True)
    midi_chrc = MidiCharacteristic(bus, 0, service)
    service.add_characteristic(midi_chrc)
    app.add_service(service)

    gatt_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter_path), GATT_MANAGER_IFACE)
    gatt_manager.RegisterApplication(app.get_path(), {},
                                     reply_handler=lambda: print("GATT registered"),
                                     error_handler=lambda e: print(f"GATT error: {e}"))

    # 3. Register Advertisement
    ad = Advertisement(bus, 0)
    ad_manager = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, adapter_path), LE_ADVERTISING_MANAGER_IFACE)
    ad_manager.RegisterAdvertisement(ad.get_path(), {},
                                     reply_handler=lambda: print("Advertisement registered"),
                                     error_handler=lambda e: print(f"ADV error: {e}"))

    print("Running... Press Ctrl+C to stop")
    try:
        mainloop.run()
    except KeyboardInterrupt:
        pass

if __name__ == '__main__':
    main()
