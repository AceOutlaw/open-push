#!/usr/bin/env python3
"""
Push 1 Display Module
=====================
Handles the segmented LCD display on Push 1.

LCD Structure:
- 4 lines, 68 characters each
- Each line divided into 4 segments of 17 characters
- Physical gaps between segments (aligned with encoder pairs)

Segment layout per line:
    |---Seg 0---|  |---Seg 1---|  |---Seg 2---|  |---Seg 3---|
       0-16          17-33          34-50          51-67
"""

import mido
import time

# SysEx constants
SYSEX_HEADER = [0x47, 0x7F, 0x15]
USER_MODE = [0x62, 0x00, 0x01, 0x01]
LIVE_MODE = [0x62, 0x00, 0x01, 0x00]

LCD_LINES = {
    1: 0x18,  # Top
    2: 0x19,
    3: 0x1A,
    4: 0x1B,  # Bottom
}

# Display geometry
CHARS_PER_LINE = 68
SEGMENT_COUNT = 4
CHARS_PER_SEGMENT = 17  # 68 / 4 = 17


class Push1Display:
    """Manages the Push 1 LCD display with segment awareness."""

    def __init__(self, port):
        self.port = port
        # Internal buffer: 4 lines × 68 characters
        self.buffer = [[' '] * CHARS_PER_LINE for _ in range(4)]

    def _send_sysex(self, data):
        """Send a SysEx message."""
        msg = mido.Message('sysex', data=SYSEX_HEADER + data)
        self.port.send(msg)

    def _flush_line(self, line_num):
        """Send a line from buffer to hardware."""
        if line_num < 1 or line_num > 4:
            return
        line_addr = LCD_LINES[line_num]
        text = ''.join(self.buffer[line_num - 1])
        data = [line_addr, 0x00, 0x45, 0x00]
        data.extend([ord(c) for c in text])
        self._send_sysex(data)

    def clear(self):
        """Clear all lines."""
        for i in range(4):
            self.buffer[i] = [' '] * CHARS_PER_LINE
        for line in range(1, 5):
            self._flush_line(line)

    def set_line(self, line_num, text):
        """Set a full line (68 chars, will be truncated/padded)."""
        if line_num < 1 or line_num > 4:
            return
        text = text.ljust(CHARS_PER_LINE)[:CHARS_PER_LINE]
        self.buffer[line_num - 1] = list(text)
        self._flush_line(line_num)

    def set_segment(self, line_num, segment, text, align='left'):
        """
        Set text in a specific segment.

        Args:
            line_num: 1-4
            segment: 0-3 (left to right)
            text: Up to 17 characters
            align: 'left', 'center', or 'right'
        """
        if line_num < 1 or line_num > 4:
            return
        if segment < 0 or segment > 3:
            return

        # Truncate to segment width
        text = text[:CHARS_PER_SEGMENT]

        # Apply alignment
        if align == 'center':
            text = text.center(CHARS_PER_SEGMENT)
        elif align == 'right':
            text = text.rjust(CHARS_PER_SEGMENT)
        else:  # left
            text = text.ljust(CHARS_PER_SEGMENT)

        # Calculate position in buffer
        start = segment * CHARS_PER_SEGMENT
        for i, char in enumerate(text):
            self.buffer[line_num - 1][start + i] = char

        self._flush_line(line_num)

    def set_segments(self, line_num, texts, align='center'):
        """
        Set all 4 segments at once.

        Args:
            line_num: 1-4
            texts: List of up to 4 strings
            align: 'left', 'center', or 'right'
        """
        for i, text in enumerate(texts[:4]):
            self.set_segment(line_num, i, text, align)

    def set_field(self, line_num, field, text, align='center'):
        """
        Set text in a field (8 fields per line, 2 per segment).
        Useful for parameter labels/values aligned with encoders.

        Args:
            line_num: 1-4
            field: 0-7 (left to right, one per encoder)
            text: Up to 8 characters
            align: 'left', 'center', or 'right'
        """
        if line_num < 1 or line_num > 4:
            return
        if field < 0 or field > 7:
            return

        # Each field is ~8 chars, but segments are 17 chars
        # Field 0-1 in segment 0, field 2-3 in segment 1, etc.
        # Field widths: 8 + 9 = 17 per segment pair

        # Approximate positions for 8 fields across 68 chars
        # 68 / 8 = 8.5, so alternate 8 and 9
        field_positions = [
            (0, 8),    # Field 0: chars 0-7
            (8, 9),    # Field 1: chars 8-16
            (17, 8),   # Field 2: chars 17-24
            (25, 9),   # Field 3: chars 25-33
            (34, 8),   # Field 4: chars 34-41
            (42, 9),   # Field 5: chars 42-50
            (51, 8),   # Field 6: chars 51-58
            (59, 9),   # Field 7: chars 59-67
        ]

        start, width = field_positions[field]
        text = text[:width]

        if align == 'center':
            text = text.center(width)
        elif align == 'right':
            text = text.rjust(width)
        else:
            text = text.ljust(width)

        for i, char in enumerate(text):
            self.buffer[line_num - 1][start + i] = char

        self._flush_line(line_num)

    def set_fields(self, line_num, texts, align='center'):
        """
        Set all 8 fields at once (one per encoder column).

        Args:
            line_num: 1-4
            texts: List of up to 8 strings
            align: 'left', 'center', or 'right'
        """
        for i, text in enumerate(texts[:8]):
            self.set_field(line_num, i, text, align)


def find_push_port():
    """Find Push User Port."""
    for name in mido.get_output_names():
        if 'Ableton Push' in name and 'User' in name:
            return name
    for name in mido.get_output_names():
        if 'Ableton Push' in name:
            return name
    return None


def demo():
    """Demo the display functions."""
    print("Push 1 Display Demo")
    print("=" * 40)

    port_name = find_push_port()
    if not port_name:
        print("ERROR: Push not found!")
        return

    print(f"Using: {port_name}")

    with mido.open_output(port_name) as port:
        # Wake up Push
        msg = mido.Message('sysex', data=SYSEX_HEADER + USER_MODE)
        port.send(msg)
        time.sleep(0.1)

        display = Push1Display(port)

        # Demo 1: Clear and show segment structure
        print("\nDemo 1: Segment structure")
        display.clear()
        display.set_segments(1, ["SEGMENT 0", "SEGMENT 1", "SEGMENT 2", "SEGMENT 3"])
        display.set_segments(2, ["(chars 0-16)", "(chars 17-33)", "(chars 34-50)", "(chars 51-67)"])
        display.set_line(3, "")
        display.set_line(4, "Each segment is 17 characters wide")

        input("Press Enter for Demo 2...")

        # Demo 2: Field structure (8 fields for encoders)
        print("\nDemo 2: Field structure (8 fields)")
        display.clear()
        display.set_fields(1, ["Track 1", "Track 2", "Track 3", "Track 4",
                               "Track 5", "Track 6", "Track 7", "Track 8"])
        display.set_fields(2, ["Vol", "Pan", "Send A", "Send B",
                               "Vol", "Pan", "Send A", "Send B"])
        display.set_fields(3, ["64", "C", "-12dB", "-6dB",
                               "100", "L20", "0dB", "-3dB"])
        display.set_line(4, "8 fields align with the 8 encoders above")

        input("Press Enter for Demo 3...")

        # Demo 3: Practical example - mixer view
        print("\nDemo 3: Mixer view")
        display.clear()
        display.set_fields(1, ["Bass", "Drums", "Keys", "Guitar",
                               "Vocal", "FX 1", "FX 2", "Master"])
        display.set_fields(2, ["Volume", "Volume", "Volume", "Volume",
                               "Volume", "Volume", "Volume", "Volume"])
        display.set_fields(3, ["-6.2dB", "0.0dB", "-3.1dB", "-8.4dB",
                               "-2.0dB", "-12dB", "-inf", "0.0dB"])
        display.set_segments(4, ["", "MIXER MODE", "", ""])

        input("Press Enter to clear and exit...")
        display.clear()

    print("Done!")


if __name__ == "__main__":
    demo()
