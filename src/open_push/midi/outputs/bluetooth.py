"""
Bluetooth MIDI Output
=====================

Output module for Bluetooth MIDI (BLE-MIDI) on Raspberry Pi.

This allows the Pi to appear as a wireless MIDI controller to
iOS devices, iPads, and other BLE-MIDI compatible hosts.

Requirements:
- Raspberry Pi with Bluetooth (Pi Zero 2W, Pi 4, etc.)
- BlueZ 5.50+ with BLE support
- Python dbus bindings

Setup on Pi:
    1. Install dependencies:
       sudo apt install bluez bluez-tools python3-dbus

    2. Enable Bluetooth:
       sudo systemctl enable bluetooth
       sudo systemctl start bluetooth

    3. Optional: Use ble-midi-server for easier setup:
       pip3 install ble-midi-server

BLE-MIDI Protocol:
    - Service UUID: 03B80E5A-EDE8-4B33-A751-6CE34EC4C700
    - Characteristic UUID: 7772E5DB-3868-4112-A1A9-F2669D106BF3
    - MIDI data wrapped in BLE-MIDI packet format

Note: Full BLE-MIDI implementation is complex. This module provides
a wrapper around external BLE-MIDI tools and a fallback to virtual
MIDI ports that can be bridged to Bluetooth.
"""

import subprocess
import threading
import time
from typing import Optional, List, Callable
import mido


# BLE-MIDI service and characteristic UUIDs
BLE_MIDI_SERVICE_UUID = "03B80E5A-EDE8-4B33-A751-6CE34EC4C700"
BLE_MIDI_CHAR_UUID = "7772E5DB-3868-4112-A1A9-F2669D106BF3"


def check_bluetooth_available() -> bool:
    """Check if Bluetooth is available and enabled."""
    # First check if ble-midi service or ble_gatt.py is running
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'ble_gatt.py'],
            capture_output=True,
            timeout=2
        )
        if result.returncode == 0:
            return True  # BLE MIDI service is running, BT is available
    except Exception:
        pass

    # Fall back to checking via hciconfig (more reliable than bluetoothctl)
    try:
        result = subprocess.run(
            ['hciconfig', 'hci0'],
            capture_output=True,
            text=True,
            timeout=5
        )
        return 'UP RUNNING' in result.stdout
    except Exception:
        pass

    # Last resort: try bluetoothctl with short timeout
    try:
        result = subprocess.run(
            ['bluetoothctl', 'show'],
            capture_output=True,
            text=True,
            timeout=2
        )
        return 'Powered: yes' in result.stdout
    except Exception:
        return False


def enable_bluetooth() -> bool:
    """Enable Bluetooth adapter."""
    try:
        subprocess.run(['sudo', 'bluetoothctl', 'power', 'on'], check=True)
        return True
    except Exception:
        return False


def get_bluetooth_status() -> dict:
    """Get Bluetooth adapter status."""
    status = {
        'available': False,
        'powered': False,
        'discoverable': False,
        'pairable': False,
        'name': 'Unknown'
    }

    # First check if ble-midi service is running - if so, BT is available
    try:
        result = subprocess.run(
            ['pgrep', '-f', 'ble_gatt.py'],
            capture_output=True,
            timeout=2
        )
        if result.returncode == 0:
            status['available'] = True
            status['powered'] = True
            status['discoverable'] = True
            status['pairable'] = True
            status['name'] = 'OpenPush MIDI (BLE)'
            return status
    except Exception:
        pass

    # Check via hciconfig (more reliable than bluetoothctl when btmidi runs)
    try:
        result = subprocess.run(
            ['hciconfig', 'hci0'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if 'UP RUNNING' in result.stdout:
            status['available'] = True
            status['powered'] = True
            if 'PSCAN' in result.stdout:
                status['discoverable'] = True
            if 'ISCAN' in result.stdout:
                status['pairable'] = True
            # Try to get name from btmgmt
            try:
                name_result = subprocess.run(
                    ['btmgmt', 'info'],
                    capture_output=True,
                    text=True,
                    timeout=2
                )
                for line in name_result.stdout.split('\n'):
                    if 'name' in line.lower() and 'short' not in line.lower():
                        parts = line.split()
                        if len(parts) >= 2:
                            status['name'] = ' '.join(parts[1:])
                            break
            except Exception:
                pass
            return status
    except Exception:
        pass

    # Fall back to bluetoothctl with short timeout
    try:
        result = subprocess.run(
            ['bluetoothctl', 'show'],
            capture_output=True,
            text=True,
            timeout=2
        )

        for line in result.stdout.split('\n'):
            if 'Powered:' in line:
                status['powered'] = 'yes' in line.lower()
                status['available'] = True
            elif 'Discoverable:' in line:
                status['discoverable'] = 'yes' in line.lower()
            elif 'Pairable:' in line:
                status['pairable'] = 'yes' in line.lower()
            elif 'Name:' in line:
                status['name'] = line.split(':', 1)[1].strip()

    except Exception as e:
        print(f"Error getting Bluetooth status: {e}")

    return status


class BluetoothMIDIOutput:
    """
    Bluetooth MIDI output wrapper.

    This class connects to the 'OpenPush BLE' virtual port created by the
    systemd service (ble-midi.service running ble_gatt.py).
    It does NOT manage the Bluetooth adapter or spawn servers itself.
    """

    def __init__(self, name: str = "OpenPush MIDI"):
        self.name = name
        self._running = False
        self._connected = False
        self._midi_port = None
        self._virtual_port_name = "OpenPush BLE" # Must match ble_gatt.py

    def start(self, use_virtual_port: bool = True) -> bool:
        """Connect to the BLE service's virtual port."""
        if self._running:
            return True

        print(f"Connecting to BLE service port: {self._virtual_port_name}...")
        
        # We don't spawn servers anymore. We just look for the port.
        try:
            # Check if port exists
            outputs = mido.get_output_names()
            port_name = None
            for name in outputs:
                if self._virtual_port_name in name:
                    port_name = name
                    break
            
            if not port_name:
                print(f"Waiting for {self._virtual_port_name}...")
                # It might not be created yet if service is starting
                return False

            self._midi_port = mido.open_output(port_name)
            self._running = True
            print(f"Connected to {port_name}")
            return True

        except Exception as e:
            print(f"Error connecting to BLE port: {e}")
            return False

    def stop(self):
        """Close connection to virtual port."""
        self._running = False
        if self._midi_port:
            self._midi_port.close()
            self._midi_port = None
        print("Bluetooth output closed")

    def _start_virtual_port(self) -> bool:
        # Legacy method kept for interface compatibility, maps to start()
        return self.start()

    def _start_ble_server(self) -> bool:
        # Legacy method kept for interface compatibility, maps to start()
        return self.start()

    def start_advertising(self):
        # The system service handles advertising.
        # We could potentially signal it via DBus if we wanted dynamic control,
        # but for now we assume it's always advertising/available.
        print("BLE Advertising is managed by system service")

    def stop_advertising(self):
        print("BLE Advertising is managed by system service")

    def send(self, msg: mido.Message):
        """Send a MIDI message."""
        if self._midi_port:
            self._midi_port.send(msg)

    def send_note_on(self, note: int, velocity: int, channel: int = 0):
        """Send note on."""
        if self._midi_port:
            msg = mido.Message('note_on', note=note, velocity=velocity, channel=channel)
            self._midi_port.send(msg)

    def send_note_off(self, note: int, channel: int = 0, velocity: int = 0):
        """Send note off."""
        if self._midi_port:
            msg = mido.Message('note_off', note=note, velocity=velocity, channel=channel)
            self._midi_port.send(msg)

    def send_cc(self, cc: int, value: int, channel: int = 0):
        """Send control change."""
        if self._midi_port:
            msg = mido.Message('control_change', control=cc, value=value, channel=channel)
            self._midi_port.send(msg)

    def send_program_change(self, program: int, channel: int = 0):
        """Send program change."""
        if self._midi_port:
            msg = mido.Message('program_change', program=program, channel=channel)
            self._midi_port.send(msg)

    def send_start(self):
        """Send MIDI Start."""
        if self._midi_port:
            self._midi_port.send(mido.Message('start'))

    def send_stop(self):
        """Send MIDI Stop."""
        if self._midi_port:
            self._midi_port.send(mido.Message('stop'))

    def send_all_notes_off(self, channel: int = None):
        """Send all notes off."""
        if not self._midi_port:
            return

        if channel is not None:
            self._midi_port.send(mido.Message('control_change', control=123, value=0, channel=channel))
        else:
            for ch in range(16):
                self._midi_port.send(mido.Message('control_change', control=123, value=0, channel=ch))

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
        return False


def check_ble_midi_setup():
    """
    Check BLE-MIDI setup and print status.

    Useful for debugging Bluetooth MIDI issues.
    """
    print("Bluetooth MIDI Status")
    print("=" * 40)

    # Check Bluetooth
    status = get_bluetooth_status()
    if status['available']:
        print(f"✓ Bluetooth available")
        print(f"  Name: {status['name']}")
        print(f"  Powered: {'Yes' if status['powered'] else 'No'}")
        print(f"  Discoverable: {'Yes' if status['discoverable'] else 'No'}")
    else:
        print("✗ Bluetooth not available")
        print("\nTo enable Bluetooth:")
        print("  sudo systemctl enable bluetooth")
        print("  sudo systemctl start bluetooth")
        return

    # Check for ble-midi-server
    print()
    try:
        result = subprocess.run(
            ['python3', '-c', 'import ble_midi_server'],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("✓ ble-midi-server installed")
        else:
            print("✗ ble-midi-server not installed")
            print("  Install with: pip3 install ble-midi-server")
    except Exception:
        print("✗ ble-midi-server not installed")
        print("  Install with: pip3 install ble-midi-server")

    print()


if __name__ == "__main__":
    check_ble_midi_setup()
