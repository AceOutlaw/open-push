"""
Push 1 Display Module
=====================

Manages the segmented LCD display on Push 1.

LCD Structure:
- 4 lines, 68 characters each
- Each line divided into 4 segments of 17 characters
- Physical gaps between segments (aligned with encoder pairs)

Segment layout per line:
    |---Seg 0---|  |---Seg 1---|  |---Seg 2---|  |---Seg 3---|
       0-16          17-33          34-50          51-67
"""

import mido
from typing import List, Optional

from .constants import (
    PUSH1_SYSEX_HEADER,
    LCD_LINE_ADDRESSES,
    LCD_CHARS_PER_LINE,
    LCD_CHARS_PER_SEGMENT,
    LCD_SEGMENT_COUNT,
    LCD_FIELD_COUNT,
)


class Push1Display:
    """
    Manages the Push 1 LCD display with segment and field awareness.

    The display has 4 lines of 68 characters each.
    Each line is divided into 4 segments of 17 characters.
    Each line also maps to 8 fields (one per encoder column).

    Usage:
        display = Push1Display(port)
        display.set_segments(1, ["Track 1", "Track 2", "Track 3", "Track 4"])
        display.set_fields(2, ["Vol", "Pan", "Send", "FX", "Vol", "Pan", "Send", "FX"])
        display.clear()
    """

    def __init__(self, port):
        """
        Initialize display.

        Args:
            port: mido output port for Push
        """
        self.port = port
        # Internal buffer: 4 lines x 68 characters
        self.buffer: List[List[str]] = [[' '] * LCD_CHARS_PER_LINE for _ in range(4)]

    def _send_sysex(self, data: list):
        """Send a SysEx message."""
        msg = mido.Message('sysex', data=PUSH1_SYSEX_HEADER + data)
        self.port.send(msg)

    def _flush_line(self, line_num: int):
        """Send a line from buffer to hardware."""
        if not (1 <= line_num <= 4):
            return
        line_addr = LCD_LINE_ADDRESSES[line_num]
        text = ''.join(self.buffer[line_num - 1])
        data = [line_addr, 0x00, 0x45, 0x00]
        data.extend([ord(c) for c in text])
        self._send_sysex(data)

    # =========================================================================
    # FULL LINE METHODS
    # =========================================================================

    def clear(self):
        """Clear all lines."""
        for i in range(4):
            self.buffer[i] = [' '] * LCD_CHARS_PER_LINE
        for line in range(1, 5):
            self._flush_line(line)

    def clear_line(self, line_num: int):
        """Clear a single line."""
        if not (1 <= line_num <= 4):
            return
        self.buffer[line_num - 1] = [' '] * LCD_CHARS_PER_LINE
        self._flush_line(line_num)

    def set_line(self, line_num: int, text: str):
        """
        Set a full line (68 chars, will be truncated/padded).

        Args:
            line_num: 1-4
            text: Text to display (up to 68 characters)
        """
        if not (1 <= line_num <= 4):
            return
        text = text.ljust(LCD_CHARS_PER_LINE)[:LCD_CHARS_PER_LINE]
        self.buffer[line_num - 1] = list(text)
        self._flush_line(line_num)

    # =========================================================================
    # SEGMENT METHODS (4 segments of 17 chars each)
    # =========================================================================

    def set_segment(self, line_num: int, segment: int, text: str, align: str = 'center'):
        """
        Set text in a specific segment.

        Args:
            line_num: 1-4
            segment: 0-3 (left to right)
            text: Up to 17 characters
            align: 'left', 'center', or 'right'
        """
        if not (1 <= line_num <= 4):
            return
        if not (0 <= segment <= 3):
            return

        # Truncate to segment width
        text = text[:LCD_CHARS_PER_SEGMENT]

        # Apply alignment
        if align == 'center':
            text = text.center(LCD_CHARS_PER_SEGMENT)
        elif align == 'right':
            text = text.rjust(LCD_CHARS_PER_SEGMENT)
        else:  # left
            text = text.ljust(LCD_CHARS_PER_SEGMENT)

        # Calculate position in buffer
        start = segment * LCD_CHARS_PER_SEGMENT
        for i, char in enumerate(text):
            self.buffer[line_num - 1][start + i] = char

        self._flush_line(line_num)

    def set_segments(self, line_num: int, texts: List[str], align: str = 'center'):
        """
        Set all 4 segments at once.

        Args:
            line_num: 1-4
            texts: List of up to 4 strings
            align: 'left', 'center', or 'right'
        """
        if not (1 <= line_num <= 4):
            return

        # Process each segment
        for i in range(LCD_SEGMENT_COUNT):
            text = texts[i] if i < len(texts) else ""
            text = text[:LCD_CHARS_PER_SEGMENT]

            if align == 'center':
                text = text.center(LCD_CHARS_PER_SEGMENT)
            elif align == 'right':
                text = text.rjust(LCD_CHARS_PER_SEGMENT)
            else:
                text = text.ljust(LCD_CHARS_PER_SEGMENT)

            start = i * LCD_CHARS_PER_SEGMENT
            for j, char in enumerate(text):
                self.buffer[line_num - 1][start + j] = char

        self._flush_line(line_num)

    # =========================================================================
    # FIELD METHODS (8 fields for encoder columns)
    # =========================================================================

    # Field positions: 8 fields across 68 characters
    # Alternating widths of 8 and 9 to fill 68 chars
    FIELD_POSITIONS = [
        (0, 8),    # Field 0: chars 0-7
        (8, 9),    # Field 1: chars 8-16
        (17, 8),   # Field 2: chars 17-24
        (25, 9),   # Field 3: chars 25-33
        (34, 8),   # Field 4: chars 34-41
        (42, 9),   # Field 5: chars 42-50
        (51, 8),   # Field 6: chars 51-58
        (59, 9),   # Field 7: chars 59-67
    ]

    def set_field(self, line_num: int, field: int, text: str, align: str = 'center'):
        """
        Set text in a field (8 fields per line, one per encoder).

        Args:
            line_num: 1-4
            field: 0-7 (left to right, one per encoder)
            text: Up to 8-9 characters
            align: 'left', 'center', or 'right'
        """
        if not (1 <= line_num <= 4):
            return
        if not (0 <= field <= 7):
            return

        start, width = self.FIELD_POSITIONS[field]
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

    def set_fields(self, line_num: int, texts: List[str], align: str = 'center'):
        """
        Set all 8 fields at once (one per encoder column).

        Args:
            line_num: 1-4
            texts: List of up to 8 strings
            align: 'left', 'center', or 'right'
        """
        if not (1 <= line_num <= 4):
            return

        for field in range(LCD_FIELD_COUNT):
            text = texts[field] if field < len(texts) else ""
            start, width = self.FIELD_POSITIONS[field]
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

    # =========================================================================
    # UTILITY METHODS
    # =========================================================================

    def get_line(self, line_num: int) -> str:
        """Get the current text of a line from the buffer."""
        if not (1 <= line_num <= 4):
            return ""
        return ''.join(self.buffer[line_num - 1])

    def get_segment(self, line_num: int, segment: int) -> str:
        """Get the current text of a segment from the buffer."""
        if not (1 <= line_num <= 4) or not (0 <= segment <= 3):
            return ""
        start = segment * LCD_CHARS_PER_SEGMENT
        end = start + LCD_CHARS_PER_SEGMENT
        return ''.join(self.buffer[line_num - 1][start:end])
