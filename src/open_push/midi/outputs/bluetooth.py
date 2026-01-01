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
    try:
        result = subprocess.run(
            ['bluetoothctl', 'show'],
            capture_output=True,
            text=True,
            timeout=5
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

    try:
        result = subprocess.run(
            ['bluetoothctl', 'show'],
            capture_output=True,
            text=True,
            timeout=5
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
    Bluetooth MIDI output using BLE-MIDI protocol.

    This class provides a high-level interface for sending MIDI over
    Bluetooth LE. It can use different backends:

    1. ble-midi-server (Python package) - Recommended
    2. bluez-alsa with MIDI bridging
    3. Custom GATT server (most complex)

    Usage:
        bt_midi = BluetoothMIDIOutput(name="OpenPush MIDI")
        if bt_midi.start():
            bt_midi.send_note_on(60, 100, 0)
            bt_midi.send_note_off(60, 0)
            bt_midi.stop()
    """

    def __init__(self, name: str = "OpenPush MIDI"):
        """
        Initialize Bluetooth MIDI output.

        Args:
            name: Bluetooth device name shown to clients
        """
        self.name = name
        self._running = False
        self._connected = False
        self._server_process = None
        self._midi_port = None
        self._virtual_port_name = "OpenPush-BT"

        # Callbacks
        self.on_connect: Optional[Callable] = None
        self.on_disconnect: Optional[Callable] = None

    @property
    def connected(self) -> bool:
        """Check if a client is connected."""
        return self._connected

    @property
    def running(self) -> bool:
        """Check if the BLE-MIDI server is running."""
        return self._running

    def start(self, use_virtual_port: bool = True) -> bool:
        """
        Start the Bluetooth MIDI server.

        Args:
            use_virtual_port: If True, create a virtual MIDI port that can
                            be bridged to Bluetooth via external tools

        Returns:
            True if started successfully
        """
        if self._running:
            return True

        # Check Bluetooth status
        status = get_bluetooth_status()
        if not status['available']:
            print("Bluetooth not available")
            return False

        if not status['powered']:
            print("Enabling Bluetooth...")
            if not enable_bluetooth():
                print("Failed to enable Bluetooth")
                return False

        if use_virtual_port:
            return self._start_virtual_port()
        else:
            return self._start_ble_server()

    def _start_virtual_port(self) -> bool:
        """
        Start with a virtual MIDI port approach.

        This creates a virtual MIDI port that can be bridged to Bluetooth
        using tools like bluez-alsa or a separate BLE-MIDI server.
        """
        try:
            # Create virtual MIDI port using mido
            self._midi_port = mido.open_output(
                self._virtual_port_name,
                virtual=True
            )
            self._running = True
            print(f"Virtual MIDI port created: {self._virtual_port_name}")
            print("Use bluez-alsa or ble-midi-server to bridge to Bluetooth")
            return True
        except Exception as e:
            print(f"Error creating virtual port: {e}")
            return False

    def _start_ble_server(self) -> bool:
        """
        Start the BLE-MIDI GATT server.

        This requires the ble-midi-server package or custom implementation.
        """
        try:
            # Try ble-midi-server first
            self._server_process = subprocess.Popen(
                ['python3', '-m', 'ble_midi_server', '--name', self.name],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self._running = True
            print(f"BLE-MIDI server started as '{self.name}'")
            return True
        except FileNotFoundError:
            print("ble-midi-server not found")
            print("Install with: pip3 install ble-midi-server")
            print("Falling back to virtual port mode")
            return self._start_virtual_port()
        except Exception as e:
            print(f"Error starting BLE server: {e}")
            return False

    def stop(self):
        """Stop the Bluetooth MIDI server."""
        self._running = False

        if self._server_process:
            self._server_process.terminate()
            self._server_process = None

        if self._midi_port:
            self._midi_port.close()
            self._midi_port = None

        print("Bluetooth MIDI stopped")

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


# Script to setup Bluetooth MIDI on the Pi
SETUP_SCRIPT = """#!/bin/bash
# Setup Bluetooth MIDI on Raspberry Pi

echo "Setting up Bluetooth MIDI..."

# Install dependencies
sudo apt update
sudo apt install -y bluez bluez-tools python3-dbus

# Enable Bluetooth
sudo systemctl enable bluetooth
sudo systemctl start bluetooth

# Make discoverable and pairable
sudo bluetoothctl << EOF
power on
discoverable on
pairable on
agent on
default-agent
EOF

# Install ble-midi-server (optional)
pip3 install ble-midi-server

echo "Bluetooth MIDI setup complete!"
echo ""
echo "To start BLE-MIDI server:"
echo "  python3 -m ble_midi_server --name 'OpenPush MIDI'"
"""


if __name__ == "__main__":
    check_ble_midi_setup()
