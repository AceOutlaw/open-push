#!/usr/bin/env python3
"""
Push Wake-Up Experiment
=======================
This script demonstrates how to initialize an Ableton Push 1
and control it without Ableton Live running.

Requirements:
    pip install mido python-rtmidi

Usage:
    1. Connect your Push via USB
    2. Run: python push_wakeup.py
    3. Watch Push wake up and light up!

LCD Display Notes:
    Push 1 has a 4-line display, 68 characters per line.
    Each line is physically divided into 4 SEGMENTS of 17 chars each.
    There are visible gaps between segments (aligned with encoder pairs).

    |--Seg 0--|  |--Seg 1--|  |--Seg 2--|  |--Seg 3--|
      0-16        17-33        34-50        51-67
"""

import mido
import time
import sys

# =============================================================================
# PUSH 1 PROTOCOL CONSTANTS
# =============================================================================

# SysEx header for Push 1: F0 47 7F 15 ...
SYSEX_HEADER = [0x47, 0x7F, 0x15]

# Mode switching
USER_MODE = [0x62, 0x00, 0x01, 0x01]   # Switch to User Mode
LIVE_MODE = [0x62, 0x00, 0x01, 0x00]   # Switch to Live Mode

# LCD line addresses (Push 1 has 4 lines, 68 chars each)
LCD_LINES = {
    1: 0x18,  # Line 1 (top)
    2: 0x19,  # Line 2
    3: 0x1A,  # Line 3
    4: 0x1B,  # Line 4 (bottom)
}

# LCD geometry
CHARS_PER_LINE = 68
CHARS_PER_SEGMENT = 17  # 4 segments × 17 chars = 68

# Color palette (velocity values for pad LEDs)
# Push 1 uses a fixed palette, not full RGB
COLORS = {
    'off': 0,
    'dark_gray': 1,
    'gray': 2,
    'white': 3,
    'red': 5,
    'red_dim': 7,
    'orange': 9,
    'yellow': 13,
    'lime': 17,
    'green': 21,
    'spring': 25,
    'turquoise': 29,
    'cyan': 33,
    'sky': 37,
    'blue': 45,
    'purple': 49,
    'magenta': 53,
    'pink': 57,
}

# Pad note numbers (8x8 grid, bottom-left = 36)
def pad_note(row, col):
    """Get MIDI note number for pad at (row, col). Row 0 = bottom, Col 0 = left."""
    return 36 + (row * 8) + col


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


def send_sysex(port, data):
    """Send a SysEx message to Push."""
    msg = mido.Message('sysex', data=SYSEX_HEADER + data)
    port.send(msg)


def set_user_mode(port):
    """Switch Push to User Mode."""
    send_sysex(port, USER_MODE)


def set_pad_color(port, note, color):
    """Set a pad's LED color by sending a Note On message."""
    velocity = COLORS.get(color, color) if isinstance(color, str) else color
    msg = mido.Message('note_on', note=note, velocity=velocity)
    port.send(msg)


def set_button_color(port, cc, color):
    """Set a button's LED color by sending a CC message."""
    value = COLORS.get(color, color) if isinstance(color, str) else color
    msg = mido.Message('control_change', control=cc, value=value)
    port.send(msg)


def clear_all_pads(port):
    """Turn off all pad LEDs."""
    for note in range(36, 100):  # Pads are notes 36-99
        set_pad_color(port, note, 'off')


def format_segments(seg0="", seg1="", seg2="", seg3=""):
    """
    Format text into 4 segments for Push 1 LCD.
    Each segment is 17 chars, centered by default.
    Returns a 68-character string.
    """
    parts = [seg0, seg1, seg2, seg3]
    line = ""
    for part in parts:
        line += part[:CHARS_PER_SEGMENT].center(CHARS_PER_SEGMENT)
    return line


def set_lcd_line(port, line_num, text):
    """
    Set text on a specific LCD line.

    Push 1 LCD format:
    F0 47 7F 15 [line] 00 45 00 [68 ASCII bytes] F7

    Note: The display has 4 physical segments with gaps.
    Use format_segments() for clean display.
    """
    # Pad or truncate text to 68 characters
    text = text.ljust(CHARS_PER_LINE)[:CHARS_PER_LINE]

    # Build the SysEx data
    line_addr = LCD_LINES.get(line_num, LCD_LINES[1])
    data = [line_addr, 0x00, 0x45, 0x00]
    data.extend([ord(c) for c in text])

    send_sysex(port, data)


def set_lcd_segments(port, line_num, seg0="", seg1="", seg2="", seg3=""):
    """Set LCD line using 4 segments (17 chars each, centered)."""
    text = format_segments(seg0, seg1, seg2, seg3)
    set_lcd_line(port, line_num, text)


def clear_lcd(port):
    """Clear all LCD lines."""
    for line in range(1, 5):
        set_lcd_line(port, line, "")


# =============================================================================
# MAIN DEMO
# =============================================================================

def main():
    print("=" * 60)
    print("  PUSH WAKE-UP EXPERIMENT")
    print("=" * 60)
    print()

    # Find Push ports
    print("Searching for Push MIDI ports...")
    push_in, push_out = find_push_ports()

    if not push_out:
        print("\nERROR: Could not find Ableton Push!")
        print("\nAvailable MIDI outputs:")
        for name in mido.get_output_names():
            print(f"  - {name}")
        print("\nMake sure Push is connected via USB.")
        sys.exit(1)

    print(f"  Input:  {push_in}")
    print(f"  Output: {push_out}")
    print()

    # Open output port
    print("Connecting to Push...")
    with mido.open_output(push_out) as port:

        # Step 1: Switch to User Mode
        print("Sending User Mode command...")
        set_user_mode(port)
        time.sleep(0.1)

        # Step 2: Clear everything
        print("Clearing display and pads...")
        clear_lcd(port)
        clear_all_pads(port)
        time.sleep(0.1)

        # Step 3: Set LCD text (using segment-aware formatting)
        print("Setting LCD text...")
        set_lcd_segments(port, 1, "PUSH AWAKE!", "No Ableton", "Required!", "open-push")
        set_lcd_segments(port, 2, "Controlled by", "Python", "not Live!", "")
        set_lcd_segments(port, 3, "", "Press any pad", "to test input", "")
        set_lcd_segments(port, 4, "Ctrl+C to exit", "", "", "v0.1")
        time.sleep(0.1)

        # Step 4: Light up pads in a pattern
        print("Lighting up pads...")

        # Rainbow diagonal pattern
        colors_list = ['red', 'orange', 'yellow', 'green', 'cyan', 'blue', 'purple', 'pink']
        for row in range(8):
            for col in range(8):
                color_index = (row + col) % len(colors_list)
                note = pad_note(row, col)
                set_pad_color(port, note, colors_list[color_index])
                time.sleep(0.01)  # Small delay for visual effect

        # Step 5: Light up some buttons
        print("Lighting up buttons...")
        # Upper row buttons (CC 102-109)
        for i, cc in enumerate(range(102, 110)):
            set_button_color(port, cc, colors_list[i])

        # Transport buttons
        set_button_color(port, 85, 'green')   # Play
        set_button_color(port, 86, 'red')     # Record

        print()
        print("=" * 60)
        print("  PUSH IS AWAKE!")
        print("=" * 60)
        print()
        print("Look at your Push - it should be lit up with a rainbow pattern!")
        print()

        # Step 6: Listen for pad presses
        if push_in:
            print("Now listening for input. Press pads to see MIDI messages.")
            print("Press Ctrl+C to exit.")
            print()

            with mido.open_input(push_in) as in_port:
                try:
                    for msg in in_port:
                        if msg.type == 'note_on' and msg.velocity > 0:
                            # Calculate row/col from note
                            note = msg.note
                            if 36 <= note <= 99:
                                row = (note - 36) // 8
                                col = (note - 36) % 8
                                print(f"Pad pressed: Row {row+1}, Col {col+1} (Note {note}, Velocity {msg.velocity})")

                                # Flash the pad white then back to rainbow
                                set_pad_color(port, note, 'white')
                                time.sleep(0.05)
                                color_index = (row + col) % len(colors_list)
                                set_pad_color(port, note, colors_list[color_index])

                        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                            pass  # Pad released

                        elif msg.type == 'control_change':
                            print(f"Button/Encoder: CC {msg.control} = {msg.value}")

                        else:
                            print(f"Other: {msg}")

                except KeyboardInterrupt:
                    print("\n\nExiting...")
        else:
            print("No input port found - can't listen for pad presses.")
            print("Press Enter to exit...")
            input()

        # Cleanup: Turn off everything
        print("Cleaning up...")
        clear_all_pads(port)
        clear_lcd(port)

        # Turn off buttons
        for cc in range(102, 110):
            set_button_color(port, cc, 'off')
        set_button_color(port, 85, 'off')
        set_button_color(port, 86, 'off')

    print("Done!")


if __name__ == "__main__":
    main()
