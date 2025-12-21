"""
Push Hardware Constants
=======================

Protocol constants for Push 1 (and future Push 2/3 support).
"""

# =============================================================================
# SYSEX PROTOCOL
# =============================================================================

# Push 1 SysEx header: F0 47 7F 15 [data] F7
PUSH1_SYSEX_HEADER = [0x47, 0x7F, 0x15]

# Mode switching commands
PUSH1_USER_MODE = [0x62, 0x00, 0x01, 0x01]   # Switch to User Mode (away from Live)
PUSH1_LIVE_MODE = [0x62, 0x00, 0x01, 0x00]   # Switch to Live Mode (back to Live)


# =============================================================================
# LCD DISPLAY
# =============================================================================

# LCD line addresses for Push 1
LCD_LINE_ADDRESSES = {
    1: 0x18,  # Top line
    2: 0x19,
    3: 0x1A,
    4: 0x1B,  # Bottom line
}

# Display geometry
LCD_CHARS_PER_LINE = 68
LCD_SEGMENT_COUNT = 4
LCD_CHARS_PER_SEGMENT = 17  # 68 / 4 = 17
LCD_FIELD_COUNT = 8         # 8 fields (one per encoder)


# =============================================================================
# PAD GRID
# =============================================================================

# Pad grid is 8x8, notes 36-99
PAD_NOTE_MIN = 36
PAD_NOTE_MAX = 99
PAD_ROWS = 8
PAD_COLS = 8


def pad_to_note(row: int, col: int) -> int:
    """Convert grid position to MIDI note. Row 0 = bottom, Col 0 = left."""
    return PAD_NOTE_MIN + (row * PAD_COLS) + col


def note_to_pad(note: int) -> tuple:
    """Convert MIDI note to grid position (row, col)."""
    if PAD_NOTE_MIN <= note <= PAD_NOTE_MAX:
        offset = note - PAD_NOTE_MIN
        return (offset // PAD_COLS, offset % PAD_COLS)
    return None


# =============================================================================
# BUTTON CC NUMBERS
# =============================================================================

# Button CC mappings for Push 1
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
    # Upper row (closer to LCD) = CC 20-27
    # Lower row (closer to pads) = CC 102-109
    'upper_1': 20,
    'upper_2': 21,
    'upper_3': 22,
    'upper_4': 23,
    'upper_5': 24,
    'upper_6': 25,
    'upper_7': 26,
    'upper_8': 27,

    'lower_1': 102,
    'lower_2': 103,
    'lower_3': 104,
    'lower_4': 105,
    'lower_5': 106,
    'lower_6': 107,
    'lower_7': 108,
    'lower_8': 109,
}

# Reverse lookup: CC number -> button name
CC_TO_BUTTON = {v: k for k, v in BUTTON_CC.items()}

# Encoder CC numbers (for touch detection and relative values)
ENCODER_CC = {
    'encoder_1': 71,
    'encoder_2': 72,
    'encoder_3': 73,
    'encoder_4': 74,
    'encoder_5': 75,
    'encoder_6': 76,
    'encoder_7': 77,
    'encoder_8': 78,
    'master_encoder': 79,
    'tempo_encoder': 14,
    'swing_encoder': 15,
}

# Touch strip CC
TOUCH_STRIP_CC = 12


# =============================================================================
# LED COLORS (Push 1 Palette)
# =============================================================================

# Push 1 uses velocity values for pad colors (fixed palette, not RGB)
COLORS = {
    'off': 0,
    'dark_gray': 1,
    'gray': 2,
    'white': 3,
    'white_dim': 1,
    'dim_white': 1,  # Alias for convenience

    'red': 5,
    'red_dim': 7,

    'orange': 9,
    'orange_dim': 11,

    'yellow': 13,
    'yellow_dim': 15,

    'lime': 17,
    'lime_dim': 19,

    'green': 21,
    'green_dim': 23,

    'spring': 25,
    'spring_dim': 27,

    'turquoise': 29,
    'turquoise_dim': 31,

    'cyan': 33,
    'cyan_dim': 35,

    'sky': 37,
    'sky_dim': 39,

    'ocean': 41,
    'ocean_dim': 43,

    'blue': 45,
    'blue_dim': 47,

    'purple': 49,
    'purple_dim': 51,

    'magenta': 53,
    'magenta_dim': 55,

    'pink': 57,
    'pink_dim': 59,
}


def color_value(color) -> int:
    """Get color velocity value. Accepts name (str) or direct value (int)."""
    if isinstance(color, str):
        return COLORS.get(color, 0)
    return color


# =============================================================================
# NOTE NAMES
# =============================================================================

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


def note_name(midi_note: int) -> str:
    """Get note name with octave (e.g., 'C4' for MIDI note 60)."""
    return NOTE_NAMES[midi_note % 12] + str((midi_note // 12) - 1)


def name_to_note(name: str) -> int:
    """Convert note name to MIDI note (e.g., 'C4' -> 60)."""
    # Extract note and octave
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
