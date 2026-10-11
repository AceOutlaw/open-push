"""
USB MIDI Gadget Output
======================

Output module for USB MIDI gadget mode on Raspberry Pi.

When the Pi is configured as a USB gadget, it appears as a MIDI
device to the connected host (iPad, computer, etc.).

Requirements:
- Raspberry Pi with USB gadget support (Pi Zero, Pi 4, etc.)
- USB gadget mode enabled (dwc2 overlay)
- g_midi kernel module loaded

Setup on Pi:
    1. Add to /boot/config.txt:
       dtoverlay=dwc2

    2. Add to /boot/cmdline.txt (after rootwait):
       modules-load=dwc2,g_midi

    3. Reboot

    4. Verify with:
       ls /dev/snd/midiC*

The gadget port typically appears as "f_midi" or similar.
"""

import mido
from typing import Optional, List


def find_gadget_port() -> Optional[str]:
    """
    Find the USB MIDI gadget port.

    Returns:
        Port name if found, None otherwise
    """
    gadget_keywords = ['f_midi', 'gadget', 'g_midi', 'midi gadget']

    for name in mido.get_output_names():
        name_lower = name.lower()
        for keyword in gadget_keywords:
            if keyword in name_lower:
                return name

    return None


def is_gadget_available() -> bool:
    """Check if USB MIDI gadget is available."""
    return find_gadget_port() is not None


def list_gadget_devices() -> List[str]:
    """
    List all potential USB MIDI gadget devices.

    Returns:
        List of port names that might be gadget devices
    """
    gadget_keywords = ['f_midi', 'gadget', 'g_midi', 'midi']
    ports = []

    for name in mido.get_output_names():
        name_lower = name.lower()
        for keyword in gadget_keywords:
            if keyword in name_lower:
                ports.append(name)
                break

    return ports


class USBGadgetOutput:
    """
    USB MIDI gadget output wrapper.

    Provides a simple interface for sending MIDI to the USB gadget port.

    Usage:
        gadget = USBGadgetOutput()
        if gadget.connect():
            gadget.send_note_on(60, 100, 0)
            gadget.send_note_off(60, 0)
            gadget.disconnect()
    """

    def __init__(self):
        self.port = None
        self.port_name: Optional[str] = None
        self._connected = False

    @property
    def connected(self) -> bool:
        return self._connected and self.port is not None

    def connect(self, port_name: str = None) -> bool:
        """
        Connect to the USB gadget port.

        Args:
            port_name: Specific port name, or None for auto-detect

        Returns:
            True if connected successfully
        """
        if self._connected:
            return True

        # Find port
        if port_name:
            self.port_name = port_name
        else:
            self.port_name = find_gadget_port()

        if not self.port_name:
            print("USB MIDI gadget not found")
            return False

        try:
            self.port = mido.open_output(self.port_name)
            self._connected = True
            print(f"Connected to USB gadget: {self.port_name}")
            return True
        except Exception as e:
            print(f"Error connecting to USB gadget: {e}")
            return False

    def disconnect(self):
        """Disconnect from the USB gadget port."""
        if self.port:
            self.port.close()
            self.port = None
        self._connected = False

    def send(self, msg: mido.Message):
        """Send a MIDI message."""
        if self.port:
            self.port.send(msg)

    def send_note_on(self, note: int, velocity: int, channel: int = 0):
        """Send note on."""
        if self.port:
            msg = mido.Message('note_on', note=note, velocity=velocity, channel=channel)
            self.port.send(msg)

    def send_note_off(self, note: int, channel: int = 0, velocity: int = 0):
        """Send note off."""
        if self.port:
            msg = mido.Message('note_off', note=note, velocity=velocity, channel=channel)
            self.port.send(msg)

    def send_cc(self, cc: int, value: int, channel: int = 0):
        """Send control change."""
        if self.port:
            msg = mido.Message('control_change', control=cc, value=value, channel=channel)
            self.port.send(msg)

    def send_program_change(self, program: int, channel: int = 0):
        """Send program change."""
        if self.port:
            msg = mido.Message('program_change', program=program, channel=channel)
            self.port.send(msg)

    def send_start(self):
        """Send MIDI Start."""
        if self.port:
            self.port.send(mido.Message('start'))

    def send_stop(self):
        """Send MIDI Stop."""
        if self.port:
            self.port.send(mido.Message('stop'))

    def send_continue(self):
        """Send MIDI Continue."""
        if self.port:
            self.port.send(mido.Message('continue'))

    def send_all_notes_off(self, channel: int = None):
        """Send all notes off."""
        if not self.port:
            return

        if channel is not None:
            msg = mido.Message('control_change', control=123, value=0, channel=channel)
            self.port.send(msg)
        else:
            for ch in range(16):
                msg = mido.Message('control_change', control=123, value=0, channel=ch)
                self.port.send(msg)

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False


# Convenience function to check setup
def check_gadget_setup():
    """
    Check USB gadget setup and print status.

    Useful for debugging gadget mode issues.
    """
    print("USB MIDI Gadget Status")
    print("=" * 40)

    # Check for gadget port
    port = find_gadget_port()
    if port:
        print(f"✓ Gadget port found: {port}")
    else:
        print("✗ Gadget port not found")
        print("\nAvailable MIDI outputs:")
        for name in mido.get_output_names():
            print(f"  - {name}")
        print("\nTo enable USB gadget mode:")
        print("  1. Add to /boot/config.txt: dtoverlay=dwc2")
        print("  2. Add to /boot/cmdline.txt: modules-load=dwc2,g_midi")
        print("  3. Reboot")

    print()


if __name__ == "__main__":
    check_gadget_setup()
