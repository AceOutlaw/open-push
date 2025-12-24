#!/usr/bin/env python3
"""
Seqtrak Transport Control via Push
===================================
Control Seqtrak play/pause from Push hardware buttons,
with transport state displayed on Push LCD.

Requirements:
    pip install mido python-rtmidi

Usage:
    1. Connect Push via USB
    2. Connect Seqtrak via USB
    3. Run: python seqtrak_transport.py
    4. Press Play (CC 85) or Stop (CC 29) on Push
"""

import mido
import time
import sys

# =============================================================================
# PUSH 1 PROTOCOL CONSTANTS
# =============================================================================

SYSEX_HEADER = [0x47, 0x7F, 0x15]
USER_MODE = [0x62, 0x00, 0x01, 0x01]

LCD_LINES = {1: 0x18, 2: 0x19, 3: 0x1A, 4: 0x1B}
CHARS_PER_LINE = 68
CHARS_PER_SEGMENT = 17

# Push button CCs
BUTTON_PLAY = 85
BUTTON_STOP = 29
BUTTON_RECORD = 86

# Button LED values (different from pad colors!)
LED_OFF = 0
LED_DIM = 1
LED_ON = 4


# =============================================================================
# MIDI HELPER FUNCTIONS
# =============================================================================

def find_push_ports():
    """Find Push MIDI ports."""
    inputs = mido.get_input_names()
    outputs = mido.get_output_names()

    push_in = None
    push_out = None

    for name in inputs:
        if 'Ableton Push' in name and 'User' in name:
            push_in = name
            break
        elif 'Ableton Push' in name:
            push_in = name

    for name in outputs:
        if 'Ableton Push' in name and 'User' in name:
            push_out = name
            break
        elif 'Ableton Push' in name:
            push_out = name

    return push_in, push_out


def find_seqtrak_port():
    """Find Seqtrak MIDI output port."""
    outputs = mido.get_output_names()

    for name in outputs:
        if 'Seqtrak' in name or 'SEQTRAK' in name:
            return name

    # Also check for partial matches
    for name in outputs:
        if 'seqtrak' in name.lower():
            return name

    return None


def send_sysex(port, data):
    """Send a SysEx message to Push."""
    msg = mido.Message('sysex', data=SYSEX_HEADER + data)
    port.send(msg)


def set_lcd_segments(port, line_num, seg0="", seg1="", seg2="", seg3=""):
    """Set LCD line using 4 segments (17 chars each, centered)."""
    parts = [seg0, seg1, seg2, seg3]
    text = ""
    for part in parts:
        text += part[:CHARS_PER_SEGMENT].center(CHARS_PER_SEGMENT)

    line_addr = LCD_LINES.get(line_num, LCD_LINES[1])
    data = [line_addr, 0x00, 0x45, 0x00]
    data.extend([ord(c) for c in text])
    send_sysex(port, data)


def set_button_led(port, cc, value):
    """Set a button's LED state (0=off, 1=dim, 4=on)."""
    msg = mido.Message('control_change', control=cc, value=value)
    port.send(msg)


def clear_lcd(port):
    """Clear all LCD lines."""
    for line in range(1, 5):
        set_lcd_segments(port, line)


# =============================================================================
# TRANSPORT STATE MANAGEMENT
# =============================================================================

class SeqtrakTransport:
    """Manages transport state between Push and Seqtrak."""

    def __init__(self, push_out, seqtrak_out):
        self.push_out = push_out
        self.seqtrak_out = seqtrak_out
        self.is_playing = False

    def update_display(self):
        """Update Push LCD and button LEDs to reflect current state."""
        if self.is_playing:
            # Playing state
            set_lcd_segments(self.push_out, 2, "", ">>> PLAYING >>>", "", "")
            set_button_led(self.push_out, BUTTON_PLAY, LED_ON)   # Play lit
            set_button_led(self.push_out, BUTTON_STOP, LED_DIM)  # Stop dim
        else:
            # Stopped state
            set_lcd_segments(self.push_out, 2, "", "[ STOPPED ]", "", "")
            set_button_led(self.push_out, BUTTON_PLAY, LED_DIM)  # Play dim
            set_button_led(self.push_out, BUTTON_STOP, LED_ON)   # Stop lit

    def play(self):
        """Start Seqtrak playback."""
        if not self.is_playing:
            self.seqtrak_out.send(mido.Message('start'))
            self.is_playing = True
            self.update_display()
            print("▶ PLAY - Sent START to Seqtrak")

    def stop(self):
        """Stop Seqtrak playback."""
        if self.is_playing:
            self.seqtrak_out.send(mido.Message('stop'))
            self.is_playing = False
            self.update_display()
            print("■ STOP - Sent STOP to Seqtrak")

    def toggle(self):
        """Toggle between play and stop."""
        if self.is_playing:
            self.stop()
        else:
            self.play()


# =============================================================================
# MAIN
# =============================================================================

def main():
    print("=" * 60)
    print("  SEQTRAK TRANSPORT CONTROL via PUSH")
    print("=" * 60)
    print()

    # Find Push ports
    print("Searching for MIDI ports...")
    push_in, push_out = find_push_ports()
    seqtrak_port = find_seqtrak_port()

    if not push_out:
        print("\nERROR: Could not find Ableton Push!")
        print("\nAvailable MIDI outputs:")
        for name in mido.get_output_names():
            print(f"  - {name}")
        sys.exit(1)

    if not seqtrak_port:
        print("\nERROR: Could not find Seqtrak!")
        print("\nAvailable MIDI outputs:")
        for name in mido.get_output_names():
            print(f"  - {name}")
        sys.exit(1)

    print(f"  Push Input:  {push_in}")
    print(f"  Push Output: {push_out}")
    print(f"  Seqtrak:     {seqtrak_port}")
    print()

    # Open ports
    with mido.open_output(push_out) as push_out_port, \
         mido.open_output(seqtrak_port) as seqtrak_out_port, \
         mido.open_input(push_in) as push_in_port:

        # Initialize Push
        print("Initializing Push...")
        send_sysex(push_out_port, USER_MODE)
        time.sleep(0.1)

        # Create transport controller
        transport = SeqtrakTransport(push_out_port, seqtrak_out_port)

        # Set up LCD
        clear_lcd(push_out_port)
        set_lcd_segments(push_out_port, 1, "SEQTRAK", "TRANSPORT", "CONTROL", "v0.1")
        set_lcd_segments(push_out_port, 3, "Play: CC 85", "Stop: CC 29", "", "")
        set_lcd_segments(push_out_port, 4, "Ctrl+C to exit", "", "", "open-push")

        # Set initial button states
        transport.update_display()

        print()
        print("=" * 60)
        print("  READY! Press Play or Stop on Push")
        print("=" * 60)
        print()
        print("Press Ctrl+C to exit")
        print()

        # Main loop - listen for button presses
        try:
            for msg in push_in_port:
                if msg.type == 'control_change' and msg.value > 0:
                    # Button pressed (not released)
                    if msg.control == BUTTON_PLAY:
                        transport.play()
                    elif msg.control == BUTTON_STOP:
                        transport.stop()
                    else:
                        # Show other button presses for debugging
                        print(f"  Button CC {msg.control} pressed")

        except KeyboardInterrupt:
            print("\n\nExiting...")

        # Cleanup
        print("Cleaning up...")
        transport.stop()  # Stop Seqtrak if playing
        clear_lcd(push_out_port)
        set_button_led(push_out_port, BUTTON_PLAY, LED_OFF)
        set_button_led(push_out_port, BUTTON_STOP, LED_OFF)

    print("Done!")


if __name__ == "__main__":
    main()
