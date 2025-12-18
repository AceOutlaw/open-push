#!/usr/bin/env python3
"""
Push 1 LCD Segment Explorer
===========================
Figure out the exact segment layout of Push 1's display.

The display is 68 characters per line but has physical gaps.
This script helps identify where those gaps are.
"""

import mido
import time
import sys

SYSEX_HEADER = [0x47, 0x7F, 0x15]
USER_MODE = [0x62, 0x00, 0x01, 0x01]

LCD_LINES = {
    1: 0x18,
    2: 0x19,
    3: 0x1A,
    4: 0x1B,
}

def find_push():
    """Find Push User Port."""
    print("Available MIDI outputs:")
    for name in mido.get_output_names():
        print(f"  - {name}")
    print()

    for name in mido.get_output_names():
        if 'Ableton Push' in name and 'User' in name:
            return name
    for name in mido.get_output_names():
        if 'Ableton Push' in name:
            return name
    return None

def send_sysex(port, data):
    msg = mido.Message('sysex', data=SYSEX_HEADER + data)
    port.send(msg)

def set_lcd_line(port, line_num, text):
    """Set a full 68-character line."""
    text = text.ljust(68)[:68]
    line_addr = LCD_LINES.get(line_num, LCD_LINES[1])
    data = [line_addr, 0x00, 0x45, 0x00]
    data.extend([ord(c) for c in text])
    send_sysex(port, data)

def clear_lcd(port):
    for line in range(1, 5):
        set_lcd_line(port, line, "")

def main():
    print("=" * 60)
    print("  PUSH 1 LCD SEGMENT EXPLORER")
    print("=" * 60)
    print()

    push_out = find_push()
    if not push_out:
        print("ERROR: Push not found!")
        sys.exit(1)

    print(f"Using: {push_out}")
    print()

    with mido.open_output(push_out) as port:
        # Wake up Push
        send_sysex(port, USER_MODE)
        time.sleep(0.1)

        print("Test 1: Number ruler to see character positions")
        print("Press Enter...")
        input()

        # Create a ruler showing position numbers
        # 68 chars: 0         1         2         3         4         5         6
        #           0123456789012345678901234567890123456789012345678901234567890123456789
        ruler1 = "0       8       16      24      32      40      48      56      64  "
        ruler2 = "01234567890123456789012345678901234567890123456789012345678901234567"

        set_lcd_line(port, 1, ruler1[:68])
        set_lcd_line(port, 2, ruler2[:68])
        set_lcd_line(port, 3, "||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||"[:68])
        set_lcd_line(port, 4, "Look for gaps in the lines above to find segment boundaries")

        print("Look at the display - where do you see gaps in the ruler?")
        print()
        print("Press Enter for Test 2...")
        input()

        print("Test 2: Block pattern to highlight segments")

        # Try 8 segments of ~8.5 chars each (8 encoders)
        # 68 / 8 = 8.5, so maybe 9+8+9+8+9+8+9+8 = 68? or 8+9 alternating?

        # Pattern with clear segment markers
        seg8 = "AAAAAAAA" + "BBBBBBBB" + "CCCCCCCC" + "DDDDDDDD" + "EEEEEEEE" + "FFFFFFFF" + "GGGGGGGG" + "HHHHHHHH"
        set_lcd_line(port, 1, seg8[:68] + "    ")  # 64 chars for 8x8

        # Try 9-char segments
        seg9 = "AAAAAAAAA" + "BBBBBBBBB" + "CCCCCCCCC" + "DDDDDDDDD" + "EEEEEEEEE" + "FFFFFFFFF" + "GGGGGGGGG" + "HHHHHHHHH"
        set_lcd_line(port, 2, seg9[:68])  # 72 chars truncated to 68

        # Try 4 segments of 17 chars
        seg17 = "AAAAAAAAAAAAAAAAA" + "BBBBBBBBBBBBBBBBB" + "CCCCCCCCCCCCCCCCC" + "DDDDDDDDDDDDDDDDD"
        set_lcd_line(port, 3, seg17[:68])

        set_lcd_line(port, 4, "8x8=64 chars | 8x9=72 chars | 4x17=68 chars")

        print("Which row aligns best with the physical segments?")
        print("- Row 1: 8 segments of 8 chars (AAAA BBBB...)")
        print("- Row 2: 8 segments of 9 chars")
        print("- Row 3: 4 segments of 17 chars")
        print()
        print("Press Enter for Test 3...")
        input()

        print("Test 3: Single character markers")

        # Place 'X' at various positions to see where gaps fall
        line = [' '] * 68
        positions = [0, 8, 9, 16, 17, 24, 25, 32, 33, 34, 40, 41, 48, 49, 56, 57, 64, 65, 67]
        for i, pos in enumerate(positions):
            if pos < 68:
                line[pos] = str(i % 10)

        set_lcd_line(port, 1, ''.join(line))
        set_lcd_line(port, 2, "Positions: 0,8,9,16,17,24,25,32,33,34,40,41,48,49,56,57,64,65,67")
        set_lcd_line(port, 3, "")
        set_lcd_line(port, 4, "Which numbers appear at segment starts?")

        print("Look at Row 1 - which position numbers appear at segment starts?")
        print()
        print("Press Enter to exit...")
        input()

        clear_lcd(port)

    print("Done!")

if __name__ == "__main__":
    main()
