"""
Push 1 Hardware Interface for MIDI Bridge
==========================================

Unified hardware control for Push 1 in MIDI-only mode.
Handles connection, LCD display, pad/button LEDs, and input.

SysEx is used ONLY for Push hardware control (LCD, LEDs, mode switch).
No SysEx is sent to external MIDI destinations.
"""

import mido
import time
from typing import Optional, List, Tuple, Callable


# =============================================================================
# SYSEX PROTOCOL (Push hardware control only)
# =============================================================================

PUSH1_SYSEX_HEADER = [0x47, 0x7F, 0x15]
PUSH1_USER_MODE = [0x62, 0x00, 0x01, 0x01]
PUSH1_LIVE_MODE = [0x62, 0x00, 0x01, 0x00]


# =============================================================================
# LCD DISPLAY CONSTANTS
# =============================================================================

LCD_LINE_ADDRESSES = {1: 0x18, 2: 0x19, 3: 0x1A, 4: 0x1B}
LCD_CHARS_PER_LINE = 68
LCD_SEGMENT_COUNT = 4
LCD_CHARS_PER_SEGMENT = 17
LCD_FIELD_COUNT = 8


# =============================================================================
# PAD GRID
# =============================================================================

PAD_NOTE_MIN = 36
PAD_NOTE_MAX = 99
PAD_ROWS = 8
PAD_COLS = 8


def pad_to_note(row: int, col: int) -> int:
    """Convert grid position to MIDI note. Row 0 = bottom, Col 0 = left."""
    return PAD_NOTE_MIN + (row * PAD_COLS) + col


def note_to_pad(note: int) -> Optional[Tuple[int, int]]:
    """Convert MIDI note to grid position (row, col)."""
    if PAD_NOTE_MIN <= note <= PAD_NOTE_MAX:
        offset = note - PAD_NOTE_MIN
        return (offset // PAD_COLS, offset % PAD_COLS)
    return None


def is_pad_note(note: int) -> bool:
    """Check if a MIDI note is a pad note."""
    return PAD_NOTE_MIN <= note <= PAD_NOTE_MAX


# =============================================================================
# BUTTON CC NUMBERS
# =============================================================================

BUTTON_CC = {
    # Transport
    'play': 85,
    'record': 86,
    'tap_tempo': 3,
    'metronome': 9,

    # Navigation
    'up': 46,
    'down': 47,
    'left': 44,
    'right': 45,

    # Octave/Page
    'octave_up': 55,
    'octave_down': 54,
    'page_left': 62,
    'page_right': 63,

    # Mode buttons
    'note': 50,
    'session': 51,
    'scale': 58,
    'user': 59,
    'repeat': 56,
    'accent': 57,

    # Encoder mode selectors
    'volume': 114,
    'pan_send': 115,
    'track': 112,
    'clip': 113,
    'device': 110,
    'browse': 111,

    # Other controls
    'shift': 49,
    'select': 48,
    'delete': 118,
    'undo': 119,
    'double': 117,
    'quantize': 116,
    'fixed_length': 90,
    'automation': 89,
    'duplicate': 88,
    'new': 87,
    'mute': 60,
    'solo': 61,
    'stop': 29,
    'master': 28,

    # 16 Buttons Below LCD
    'upper_1': 20, 'upper_2': 21, 'upper_3': 22, 'upper_4': 23,
    'upper_5': 24, 'upper_6': 25, 'upper_7': 26, 'upper_8': 27,
    'lower_1': 102, 'lower_2': 103, 'lower_3': 104, 'lower_4': 105,
    'lower_5': 106, 'lower_6': 107, 'lower_7': 108, 'lower_8': 109,
}

CC_TO_BUTTON = {v: k for k, v in BUTTON_CC.items()}

# Encoder CC numbers
ENCODER_CC = {
    'encoder_1': 71, 'encoder_2': 72, 'encoder_3': 73, 'encoder_4': 74,
    'encoder_5': 75, 'encoder_6': 76, 'encoder_7': 77, 'encoder_8': 78,
    'master_encoder': 79,
    'tempo_encoder': 14,
    'swing_encoder': 15,
}

CC_TO_ENCODER = {v: k for k, v in ENCODER_CC.items()}

TOUCH_STRIP_CC = 12


# =============================================================================
# LED COLORS (Push 1 Palette)
# =============================================================================

COLORS = {
    'off': 0,
    'dark_gray': 1, 'gray': 2, 'white': 3,
    'white_dim': 1, 'dim_white': 1,
    'red': 5, 'red_dim': 7,
    'orange': 9, 'orange_dim': 11,
    'yellow': 13, 'yellow_dim': 15,
    'lime': 17, 'lime_dim': 19,
    'green': 21, 'green_dim': 23,
    'spring': 25, 'spring_dim': 27,
    'turquoise': 29, 'turquoise_dim': 31,
    'cyan': 33, 'cyan_dim': 35,
    'sky': 37, 'sky_dim': 39,
    'ocean': 41, 'ocean_dim': 43,
    'blue': 45, 'blue_dim': 47,
    'purple': 49, 'purple_dim': 51,
    'magenta': 53, 'magenta_dim': 55,
    'pink': 57, 'pink_dim': 59,
}


def color_value(color) -> int:
    """Get color velocity value. Accepts name (str) or direct value (int)."""
    if isinstance(color, str):
        return COLORS.get(color.lower(), 0)
    return color


# =============================================================================
# NOTE UTILITIES
# =============================================================================

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def note_name(midi_note: int) -> str:
    """Get note name with octave (e.g., 'C4' for MIDI note 60)."""
    return NOTE_NAMES[midi_note % 12] + str((midi_note // 12) - 1)


def name_to_note(name: str) -> int:
    """Convert note name to MIDI note (e.g., 'C4' -> 60)."""
    if len(name) == 2:
        note_part = name[0].upper()
        octave = int(name[1])
    elif len(name) == 3:
        note_part = name[:2].upper()
        octave = int(name[2])
    else:
        raise ValueError(f"Invalid note name: {name}")
    note_index = NOTE_NAMES.index(note_part)
    return (octave + 1) * 12 + note_index


# =============================================================================
# PUSH HARDWARE CLASS
# =============================================================================

class PushHardware:
    """
    Unified Push 1 hardware interface for MIDI-only bridge.

    Combines port management, LCD display, and LED control.

    Usage:
        push = PushHardware()
        if push.connect():
            push.set_user_mode()
            push.display.set_line(1, "MIDI Bridge v1.0")
            push.set_pad_color(36, 'blue')
            for msg in push.iter_messages():
                # handle input
            push.disconnect()
    """

    # Field positions for 8-field display (one per encoder)
    FIELD_POSITIONS = [
        (0, 8), (8, 9), (17, 8), (25, 9),
        (34, 8), (42, 9), (51, 8), (59, 9),
    ]

    def __init__(self):
        self.input_port_name: Optional[str] = None
        self.output_port_name: Optional[str] = None
        self._input_port = None
        self._output_port = None
        self._connected = False

        # LCD buffer: 4 lines × 68 characters
        self._lcd_buffer: List[List[str]] = [[' '] * LCD_CHARS_PER_LINE for _ in range(4)]

    @property
    def connected(self) -> bool:
        """Check if connected to Push hardware."""
        return self._connected and self._output_port is not None

    # =========================================================================
    # CONNECTION
    # =========================================================================

    def find_ports(self) -> Tuple[Optional[str], Optional[str]]:
        """Find Push MIDI ports. Prefers User ports."""
        input_name = None
        output_name = None

        for name in mido.get_input_names():
            if 'Ableton Push' in name and 'User' in name:
                input_name = name
                break
            elif 'Ableton Push' in name and input_name is None:
                input_name = name

        for name in mido.get_output_names():
            if 'Ableton Push' in name and 'User' in name:
                output_name = name
                break
            elif 'Ableton Push' in name and output_name is None:
                output_name = name

        self.input_port_name = input_name
        self.output_port_name = output_name
        return input_name, output_name

    def connect(self) -> bool:
        """Connect to Push hardware."""
        if self._connected:
            return True

        if not self.output_port_name:
            self.find_ports()

        if not self.output_port_name:
            print("Push not found")
            return False

        try:
            self._output_port = mido.open_output(self.output_port_name)
            if self.input_port_name:
                self._input_port = mido.open_input(self.input_port_name)
            self._connected = True
            print(f"Connected to Push: {self.output_port_name}")
            return True
        except Exception as e:
            print(f"Error connecting to Push: {e}")
            return False

    def disconnect(self):
        """Disconnect from Push hardware."""
        if self._input_port:
            self._input_port.close()
            self._input_port = None
        if self._output_port:
            self._output_port.close()
            self._output_port = None
        self._connected = False

    # =========================================================================
    # SYSEX (Push hardware only - never sent externally)
    # =========================================================================

    def _send_sysex(self, data: list):
        """Send SysEx to Push hardware."""
        if not self._output_port:
            return
        msg = mido.Message('sysex', data=PUSH1_SYSEX_HEADER + data)
        self._output_port.send(msg)

    def set_user_mode(self):
        """Switch Push to User Mode (away from Live control)."""
        self._send_sysex(PUSH1_USER_MODE)
        time.sleep(0.05)

    def set_live_mode(self):
        """Switch Push back to Live Mode."""
        self._send_sysex(PUSH1_LIVE_MODE)
        time.sleep(0.05)

    # =========================================================================
    # LCD DISPLAY
    # =========================================================================

    def _flush_lcd_line(self, line_num: int):
        """Send a line from buffer to LCD hardware."""
        if not (1 <= line_num <= 4) or not self._output_port:
            return
        line_addr = LCD_LINE_ADDRESSES[line_num]
        text = ''.join(self._lcd_buffer[line_num - 1])
        data = [line_addr, 0x00, 0x45, 0x00]
        data.extend([ord(c) for c in text])
        self._send_sysex(data)

    def clear_lcd(self):
        """Clear all LCD lines."""
        for i in range(4):
            self._lcd_buffer[i] = [' '] * LCD_CHARS_PER_LINE
        for line in range(1, 5):
            self._flush_lcd_line(line)

    def clear_lcd_line(self, line_num: int):
        """Clear a single LCD line."""
        if not (1 <= line_num <= 4):
            return
        self._lcd_buffer[line_num - 1] = [' '] * LCD_CHARS_PER_LINE
        self._flush_lcd_line(line_num)

    def set_lcd_line(self, line_num: int, text: str):
        """Set a full LCD line (68 chars, truncated/padded)."""
        if not (1 <= line_num <= 4):
            return
        text = text.ljust(LCD_CHARS_PER_LINE)[:LCD_CHARS_PER_LINE]
        self._lcd_buffer[line_num - 1] = list(text)
        self._flush_lcd_line(line_num)

    def set_lcd_segment(self, line_num: int, segment: int, text: str, align: str = 'center'):
        """
        Set text in a specific segment (4 segments of 17 chars each).

        Args:
            line_num: 1-4
            segment: 0-3 (left to right)
            text: Up to 17 characters
            align: 'left', 'center', or 'right'
        """
        if not (1 <= line_num <= 4) or not (0 <= segment <= 3):
            return

        text = text[:LCD_CHARS_PER_SEGMENT]
        if align == 'center':
            text = text.center(LCD_CHARS_PER_SEGMENT)
        elif align == 'right':
            text = text.rjust(LCD_CHARS_PER_SEGMENT)
        else:
            text = text.ljust(LCD_CHARS_PER_SEGMENT)

        start = segment * LCD_CHARS_PER_SEGMENT
        for i, char in enumerate(text):
            self._lcd_buffer[line_num - 1][start + i] = char
        self._flush_lcd_line(line_num)

    def set_lcd_segments(self, line_num: int, texts: List[str], align: str = 'center'):
        """Set all 4 segments at once."""
        if not (1 <= line_num <= 4):
            return

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
                self._lcd_buffer[line_num - 1][start + j] = char

        self._flush_lcd_line(line_num)

    def set_lcd_field(self, line_num: int, field: int, text: str, align: str = 'center'):
        """
        Set text in a field (8 fields per line, one per encoder).

        Args:
            line_num: 1-4
            field: 0-7 (left to right)
            text: Up to 8-9 characters
            align: 'left', 'center', or 'right'
        """
        if not (1 <= line_num <= 4) or not (0 <= field <= 7):
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
            self._lcd_buffer[line_num - 1][start + i] = char
        self._flush_lcd_line(line_num)

    def set_lcd_fields(self, line_num: int, texts: List[str], align: str = 'center'):
        """Set all 8 fields at once (one per encoder column)."""
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
                self._lcd_buffer[line_num - 1][start + i] = char

        self._flush_lcd_line(line_num)

    # =========================================================================
    # PAD LED CONTROL
    # =========================================================================

    def set_pad_color(self, note: int, color):
        """Set a pad's LED color by MIDI note (36-99)."""
        if not self._output_port:
            return
        if not (PAD_NOTE_MIN <= note <= PAD_NOTE_MAX):
            return
        velocity = color_value(color)
        msg = mido.Message('note_on', note=note, velocity=velocity)
        self._output_port.send(msg)

    def set_pad_color_xy(self, row: int, col: int, color):
        """Set a pad's LED color by grid position (row 0-7, col 0-7)."""
        note = pad_to_note(row, col)
        self.set_pad_color(note, color)

    def clear_all_pads(self):
        """Turn off all pad LEDs."""
        for note in range(PAD_NOTE_MIN, PAD_NOTE_MAX + 1):
            self.set_pad_color(note, 'off')

    def set_all_pads(self, color):
        """Set all pads to a single color."""
        for note in range(PAD_NOTE_MIN, PAD_NOTE_MAX + 1):
            self.set_pad_color(note, color)

    # =========================================================================
    # BUTTON LED CONTROL
    # =========================================================================

    def set_button_color(self, button: str, color):
        """Set a button's LED color by name."""
        cc = BUTTON_CC.get(button)
        if cc is not None:
            self.set_button_color_cc(cc, color)

    def set_button_color_cc(self, cc: int, color):
        """Set a button's LED color by CC number."""
        if not self._output_port:
            return
        value = color_value(color)
        msg = mido.Message('control_change', control=cc, value=value)
        self._output_port.send(msg)

    def set_button_led(self, cc: int, value: int):
        """Set a button's LED to a raw value (0-127)."""
        if not self._output_port:
            return
        msg = mido.Message('control_change', control=cc, value=value)
        self._output_port.send(msg)

    def clear_button(self, button: str):
        """Turn off a button's LED."""
        self.set_button_color(button, 'off')

    def clear_all_buttons(self):
        """Turn off all button LEDs."""
        for cc in BUTTON_CC.values():
            self.set_button_color_cc(cc, 'off')

    # =========================================================================
    # INPUT HANDLING
    # =========================================================================

    def read_message(self, timeout: float = None) -> Optional[mido.Message]:
        """
        Read a single message from Push input.

        Args:
            timeout: Maximum wait time (seconds), None for non-blocking

        Returns:
            mido.Message or None
        """
        if not self._input_port:
            return None

        if timeout is None:
            return self._input_port.poll()
        elif timeout == 0:
            return self._input_port.receive()
        else:
            return self._input_port.receive(block=True)

    def iter_messages(self):
        """Iterate over incoming messages (blocking)."""
        if not self._input_port:
            return
        for msg in self._input_port:
            yield msg

    def poll_messages(self):
        """
        Get all pending messages (non-blocking).

        Yields:
            mido.Message objects
        """
        if not self._input_port:
            return
        while True:
            msg = self._input_port.poll()
            if msg is None:
                break
            yield msg

    # =========================================================================
    # MESSAGE CLASSIFICATION HELPERS
    # =========================================================================

    def is_button_press(self, msg) -> bool:
        """Check if message is a button press (CC with value > 0)."""
        return msg.type == 'control_change' and msg.value > 0

    def is_button_release(self, msg) -> bool:
        """Check if message is a button release (CC with value == 0)."""
        return msg.type == 'control_change' and msg.value == 0

    def get_button_name(self, cc: int) -> Optional[str]:
        """Get button name from CC number."""
        return CC_TO_BUTTON.get(cc)

    def is_encoder(self, cc: int) -> bool:
        """Check if CC is an encoder."""
        return cc in CC_TO_ENCODER

    def get_encoder_name(self, cc: int) -> Optional[str]:
        """Get encoder name from CC number."""
        return CC_TO_ENCODER.get(cc)

    def decode_relative_encoder(self, value: int) -> int:
        """
        Decode relative encoder value to signed delta.

        Push encoders send:
        - 1-63: Clockwise (1 = slow, 63 = fast)
        - 65-127: Counter-clockwise (65 = slow, 127 = fast)
        """
        if value < 64:
            return value  # Clockwise (positive)
        else:
            return value - 128  # Counter-clockwise (negative)

    # =========================================================================
    # CONTEXT MANAGER
    # =========================================================================

    def __enter__(self):
        if not self._connected:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
