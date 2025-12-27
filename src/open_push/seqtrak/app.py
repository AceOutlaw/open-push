#!/usr/bin/env python3
"""
OpenPush Seqtrak Bridge
=======================
Control Yamaha Seqtrak from Ableton Push hardware.

Reuses the same UI paradigm as the Reason bridge:
- Pads (notes 36-99) for isomorphic keyboard
- Scale button (CC 58) for scale/root selection
- 16 buttons below LCD (CC 20-27, CC 102-109) are dynamic per mode
- Octave up/down, transport controls

Usage:
    python -m open_push.seqtrak.app
"""

import mido
import time
import sys
import os

# Ensure imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from open_push.music.layout import IsomorphicLayout
from open_push.music.scales import SCALES, SCALE_NAMES, get_scale_display_name
from open_push.seqtrak.protocol import (
    SeqtrakProtocol, MuteState, Track, Address,
    find_seqtrak_port
)
from open_push.seqtrak.presets import get_preset_name_short

# =============================================================================
# PUSH CONSTANTS (matching Reason app)
# =============================================================================

SYSEX_HEADER = [0x47, 0x7F, 0x15]
USER_MODE = [0x62, 0x00, 0x01, 0x01]

LCD_LINES = {1: 0x18, 2: 0x19, 3: 0x1A, 4: 0x1B}
CHARS_PER_SEGMENT = 17

# Root note names
ROOT_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Scale mode button layout (chromatic ascending):
#   Upper: [ScaleUp] [C] [C#][D] [D#][E] [F] [InKey]
#          CC 20     21  22  23  24  25  26    27
#   Lower: [ScaleDn] [F#][G] [G#][A] [A#][B] [Chromat]
#          CC 102    103 104 105 106 107 108  109
ROOT_UPPER_BUTTONS = [21, 22, 23, 24, 25, 26]
ROOT_LOWER_BUTTONS = [103, 104, 105, 106, 107, 108]
ROOT_UPPER_NOTES = [0, 1, 2, 3, 4, 5]    # C, C#, D, D#, E, F
ROOT_LOWER_NOTES = [6, 7, 8, 9, 10, 11]  # F#, G, G#, A, A#, B

SCALE_UP_CC = 20
SCALE_DOWN_CC = 102
IN_KEY_CC = 27
CHROMAT_CC = 109

# Pad colors (velocity values)
COLOR_OFF = 0
COLOR_DIM = 1
COLOR_WHITE = 3
COLOR_RED = 5
COLOR_ORANGE = 9
COLOR_YELLOW = 13
COLOR_GREEN = 21
COLOR_CYAN = 33
COLOR_BLUE = 45
COLOR_PURPLE = 49

# =============================================================================
# PAD MODES - Different behavior based on track type
# =============================================================================

class PadMode:
    """Pad mode determines grid colors and note behavior."""
    DRUM = 'drum'       # Chromatic pads, no scale filtering
    MELODIC = 'melodic' # Isomorphic keyboard with scales
    SAMPLER = 'sampler' # 7 sample pads with per-pad presets

# Map track types to pad modes
TRACK_TYPE_TO_PAD_MODE = {
    'drum': PadMode.DRUM,
    'synth': PadMode.MELODIC,
    'dx': PadMode.MELODIC,
    'sampler': PadMode.SAMPLER,
}

# Mixer display order: Melodic first, then drums, drum bus, sampler last
# Maps display position (0-11) to MIDI track number (1-11), None = DRUM bus
MIXER_TRACK_ORDER = [8, 9, 10, 1, 2, 3, 4, 5, 6, 7, None, 11]

# Display names for mixer (matches MIXER_TRACK_ORDER positions)
MIXER_DISPLAY_NAMES = [
    'SYN1', 'SYN2', 'DX', 'KICK', 'SNAR', 'CLAP', 'HAT1', 'HAT2',
    'PRC1', 'PRC2', 'DRUM', 'SMPL'
]

# Drum tracks that are controlled by the DRUM bus (tracks 1-7)
DRUM_BUS_TRACKS = [1, 2, 3, 4, 5, 6, 7]

# Track abbreviations for mixer display (short names to fit in segments)
MIXER_TRACK_ABBREV = {
    1: 'KICK', 2: 'SNAR', 3: 'CLAP', 4: 'HAT1', 5: 'HAT2',
    6: 'PRC1', 7: 'PRC2', 8: 'SYN1', 9: 'SYN2', 10: 'DX', 11: 'SMPL'
}

# =============================================================================
# ARPEGGIATOR PATTERNS - Software-based arpeggiator (runs in Python, not Seqtrak)
# =============================================================================

ARP_PATTERNS = ['up', 'down', 'up_down', 'down_up', 'random',
                'converge', 'diverge', 'chord', 'as_played', 'custom']
ARP_PATTERN_NAMES = ['Up', 'Down', 'Up/Dn', 'Dn/Up', 'Rnd',
                     'Conv', 'Div', 'Chord', 'Played', 'Custom']

# =============================================================================
# DRUM MODE LAYOUT - 2x4 grid in bottom 2 rows + step sequencer in top 4 rows
# =============================================================================

# Drum pad positions (8 pads in 2x4 layout, bottom 2 rows)
DRUM_PAD_POSITIONS = [
    (0, 0), (0, 1), (0, 2), (0, 3),  # Row 0: KICK, SNARE, CLAP, HAT1
    (1, 0), (1, 1), (1, 2), (1, 3),  # Row 1: HAT2, PERC1, PERC2, PERC2+G
]

# MIDI notes for each drum pad (C4=60 for tracks 1-7, G4=67 for 8th pad)
DRUM_PAD_NOTES = [60, 60, 60, 60, 60, 60, 60, 67]

# Track assignment for each drum pad (8th pad = PERC2 at higher note)
DRUM_PAD_TRACKS = [1, 2, 3, 4, 5, 6, 7, 7]

# Colors for each drum track (1-7)
DRUM_TRACK_COLORS = {
    1: COLOR_RED,      # KICK
    2: COLOR_ORANGE,   # SNARE
    3: COLOR_YELLOW,   # CLAP
    4: COLOR_GREEN,    # HAT1
    5: COLOR_CYAN,     # HAT2
    6: COLOR_BLUE,     # PERC1
    7: COLOR_PURPLE,   # PERC2
}

# Step sequencer colors
STEP_COLOR_ON = COLOR_GREEN
STEP_COLOR_OFF = COLOR_DIM

# =============================================================================
# NOTE REPEAT RATES (CC 36-43 → subdivision rate in beats)
# =============================================================================
# Maps CC number to (name, beats) where beats is fraction of a beat
# At 120 BPM, 1 beat = 500ms. These are used to calculate repeat interval.
NOTE_REPEAT_SUBDIVISIONS = {
    36: ('1/4', 1.0),       # Quarter note = 1 beat
    37: ('1/4t', 2/3),      # Quarter triplet
    38: ('1/8', 0.5),       # Eighth note
    39: ('1/8t', 1/3),      # Eighth triplet
    40: ('1/16', 0.25),     # Sixteenth note
    41: ('1/16t', 1/6),     # Sixteenth triplet
    42: ('1/32', 0.125),    # 32nd note
    43: ('1/32t', 1/12),    # 32nd triplet
}

# =============================================================================
# DEVICE MODE PARAMETERS
# =============================================================================
# Each parameter: (name, cc, default, min, max, display_func)
# display_func is optional for custom formatting (e.g., pan shows L/R)

def _format_pan(val):
    """Format pan value: 1-63=L, 64=C, 65-127=R"""
    if val < 64:
        return f"L{64 - val}"
    elif val > 64:
        return f"R{val - 64}"
    return "C"

def _format_mono_poly(val):
    """Format mono/poly/chord value."""
    return ['MONO', 'POLY', 'CHORD'][min(val, 2)]

def _format_on_off(val):
    """Format on/off value."""
    return 'ON' if val >= 64 else 'OFF'

def _format_arp_type(val):
    """Format arpeggiator type (0=Off, 1-16=preset)."""
    if val == 0:
        return "OFF"
    ARP_NAMES = ['Up', 'Up2', 'Dn', 'Dn2', 'Rnd', 'Rnd2',
                 'U/DA', 'U/DA2', 'U/DB', 'U/DB2', 'Thm',
                 'Uni', 'Chd1', 'Chd2', 'Play', 'Play']
    if 1 <= val <= 16:
        return ARP_NAMES[val - 1]
    return str(val)

def _format_arp_speed(val):
    """Format arp speed (0-9)."""
    SPEEDS = ['1/1', '1/2', '1/2T', '1/4', '1/4T',
              '1/8', '1/8T', '1/16', '1/16T', '1/32']
    if 0 <= val <= 9:
        return SPEEDS[val]
    return str(val)

def _format_fm_algo(val):
    """Format FM algorithm (1-12)."""
    # Map 0-127 to algo 1-12
    algo = min(12, max(1, (val // 11) + 1))
    return f"Alg{algo}"

# =============================================================================
# DEVICE MODE PARAMETERS - Track-type-aware pages
# =============================================================================
# Each parameter: (label, cc_number, default, format_func or None)

# Drum tracks (channels 1-7): 2 pages
DEVICE_PARAMS_DRUM = [
    # Page 0: Core Sound
    [
        ('Volume', 7, 100, None),
        ('Pan', 10, 64, _format_pan),
        ('Pitch', 25, 64, None),
        ('Attack', 73, 64, None),
        ('Decay', 75, 64, None),
        ('Cutoff', 74, 127, None),
        ('Reso', 71, 0, None),
        ('', 0, 0, None),
    ],
    # Page 1: FX/EQ
    [
        ('Reverb', 91, 0, None),
        ('Delay', 94, 0, None),
        ('EQ Hi', 20, 64, None),
        ('EQ Lo', 21, 64, None),
        ('', 0, 0, None),
        ('', 0, 0, None),
        ('', 0, 0, None),
        ('', 0, 0, None),
    ],
]

# Synth tracks (channels 8-9): 3 pages
DEVICE_PARAMS_SYNTH = [
    # Page 0: Core Sound
    [
        ('Volume', 7, 100, None),
        ('Pan', 10, 64, _format_pan),
        ('Mode', 26, 1, _format_mono_poly),
        ('Attack', 73, 64, None),
        ('Decay', 75, 64, None),
        ('Cutoff', 74, 127, None),
        ('Reso', 71, 0, None),
        ('', 0, 0, None),
    ],
    # Page 1: FX/EQ
    [
        ('Reverb', 91, 0, None),
        ('Delay', 94, 0, None),
        ('EQ Hi', 20, 64, None),
        ('EQ Lo', 21, 64, None),
        ('', 0, 0, None),
        ('', 0, 0, None),
        ('', 0, 0, None),
        ('', 0, 0, None),
    ],
    # Page 2: Arp/Porta
    [
        ('Porta', 5, 0, None),
        ('PortaSw', 65, 0, _format_on_off),
        ('ArpType', 27, 0, _format_arp_type),
        ('ArpGate', 28, 64, None),
        ('ArpSpd', 29, 4, _format_arp_speed),
        ('', 0, 0, None),
        ('', 0, 0, None),
        ('', 0, 0, None),
    ],
]

# DX track (channel 10): 4 pages (synth params + FM)
DEVICE_PARAMS_DX = [
    # Page 0: Core Sound (same as synth)
    DEVICE_PARAMS_SYNTH[0],
    # Page 1: FX/EQ (same as synth)
    DEVICE_PARAMS_SYNTH[1],
    # Page 2: Arp/Porta (same as synth)
    DEVICE_PARAMS_SYNTH[2],
    # Page 3: FM Synthesis
    [
        ('FMAlgo', 116, 0, _format_fm_algo),
        ('ModAmt', 117, 64, None),
        ('ModFreq', 118, 64, None),
        ('ModFB', 119, 64, None),
        ('', 0, 0, None),
        ('', 0, 0, None),
        ('', 0, 0, None),
        ('', 0, 0, None),
    ],
]

# Sampler track (channel 11): 2 pages (CC params only, SysEx params later)
DEVICE_PARAMS_SAMPLER = [
    # Page 0: Core Sound
    [
        ('Volume', 7, 100, None),
        ('Pan', 10, 64, _format_pan),
        ('Attack', 73, 64, None),
        ('Decay', 75, 64, None),
        ('Cutoff', 74, 127, None),
        ('Reso', 71, 0, None),
        ('', 0, 0, None),
        ('', 0, 0, None),
    ],
    # Page 1: FX/EQ
    [
        ('Reverb', 91, 0, None),
        ('Delay', 94, 0, None),
        ('EQ Hi', 20, 64, None),
        ('EQ Lo', 21, 64, None),
        ('', 0, 0, None),
        ('', 0, 0, None),
        ('', 0, 0, None),
        ('', 0, 0, None),
    ],
]

# Track type to parameter pages mapping
DEVICE_PARAMS = {
    'drum': DEVICE_PARAMS_DRUM,
    'synth': DEVICE_PARAMS_SYNTH,
    'dx': DEVICE_PARAMS_DX,
    'sampler': DEVICE_PARAMS_SAMPLER,
}

# =============================================================================
# SAMPLER MODE LAYOUT - 2x4 grid in bottom 2 rows (7 pads + 1 empty)
# =============================================================================

# Sampler pad positions (7 pads in 2x4 layout, bottom 2 rows)
SAMPLER_PAD_POSITIONS = [
    (0, 0), (0, 1), (0, 2), (0, 3),  # Row 0: samples 1-4
    (1, 0), (1, 1), (1, 2),          # Row 1: samples 5-7
]
# Position (1, 3) is empty/unused

# Colors for each sampler pad (distinctive colors for visual identification)
SAMPLER_PAD_COLORS = [
    COLOR_RED, COLOR_ORANGE, COLOR_YELLOW, COLOR_GREEN,
    COLOR_CYAN, COLOR_BLUE, COLOR_PURPLE
]
SAMPLER_SELECTED_COLOR = 3  # Bright white for selected pad

# =============================================================================
# PRESET RANGES
# =============================================================================

# Track type preset ranges (preset numbers, 1-indexed)
# Formula: preset_number = (bank_lsb * 128) + program + 1
PRESET_RANGES = {
    'drum': (1, 855),       # Tracks 1-7: all drum sounds
    'synth': (856, 1932),   # Tracks 8-9: synth sounds only
    'dx': (1933, 2032),     # Track 10: DX/FM sounds only
    'sampler': (1, 392),    # Track 11: sampler sounds (separate bank MSB 62)
}

# Default starting presets for each track
# SYNTH1 starts on "Rn Bass" (preset 856), SYNTH2 on "Slow Saw Lead" (preset 951)
# DX starts on "FM Chorus Jazz EP" (preset 1970)
TRACK_DEFAULTS = {
    # Tracks 1-7 (drums): preset 1 = "Tight Punchy Kick 1"
    1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 1,
    # Track 8 (SYNTH1): preset 856 = "Rn Bass"
    8: 856,
    # Track 9 (SYNTH2): preset 951 = "Slow Saw Lead"
    9: 951,
    # Track 10 (DX): preset 1970 = "FM Chorus Jazz EP"
    10: 1970,
    # Track 11 (Sampler): preset 1
    11: 1,
}

def get_track_type(track):
    """Get the track type for preset range limits."""
    if 1 <= track <= 7:
        return 'drum'
    elif 8 <= track <= 9:
        return 'synth'
    elif track == 10:
        return 'dx'
    elif track == 11:
        return 'sampler'
    return None

def preset_to_bank_program(preset_num):
    """Convert preset number (1-indexed) to bank_lsb and program."""
    idx = preset_num - 1
    return idx // 128, idx % 128

def bank_program_to_preset(bank_lsb, program):
    """Convert bank_lsb and program to preset number (1-indexed)."""
    return (bank_lsb * 128) + program + 1

# Button LED values
LED_OFF = 0
LED_DIM = 1
LED_ON = 4

# Button CCs (matching Reason app)
BUTTONS = {
    # Transport
    'play': 85, 'stop': 29, 'record': 86,
    'tap_tempo': 3, 'metronome': 9,

    # Mode buttons
    'note': 50, 'session': 51, 'scale': 58,
    'volume': 114,    # Mixer mode
    'track': 112,     # Track mode
    'device': 110,    # Device mode
    'clip': 113, 'browse': 111, 'master': 28,

    # Performance
    'octave_up': 55, 'octave_down': 54,
    'mute': 60, 'solo': 61,
    'repeat': 56, 'accent': 57,

    # Navigation
    'up': 46, 'down': 47, 'left': 44, 'right': 45,
    'page_left': 63, 'page_right': 62,
    'shift': 49, 'select': 48,

    # 16 Buttons Below LCD
    'upper_1': 20, 'upper_2': 21, 'upper_3': 22, 'upper_4': 23,
    'upper_5': 24, 'upper_6': 25, 'upper_7': 26, 'upper_8': 27,
    'lower_1': 102, 'lower_2': 103, 'lower_3': 104, 'lower_4': 105,
    'lower_5': 106, 'lower_6': 107, 'lower_7': 108, 'lower_8': 109,
}


# =============================================================================
# SEQTRAK BRIDGE APP
# =============================================================================

class SeqtrakBridge:
    """
    Bridge between Push hardware and Yamaha Seqtrak.
    Uses the same UI paradigm as the Reason bridge.
    """

    def __init__(self):
        # State (matching Reason app patterns)
        self.is_playing = False
        self.is_recording = False
        self.is_sample_recording = False  # Sample recording (Shift+Record)
        self.current_mode = 'welcome'  # welcome, note, track, device, mixer, scale
        self.previous_mode = 'track'   # Mode to return to after scale mode
        self.shift_held = False

        # Pad mode (derived from keyboard_track type)
        self.current_pad_mode = PadMode.MELODIC  # Default for SYNTH1

        # Sampler-specific state
        self.selected_sampler_pad = 0  # Which of 7 pads is selected for editing (0-6)
        self.sampler_pad_presets = [
            {'bank_msb': 62, 'bank_lsb': 0, 'program': i, 'preset_num': i + 1}
            for i in range(7)  # Initialize 7 pads with presets 1-7
        ]

        # Step sequencer state (for drum mode)
        self.selected_drum_track = 1  # Which drum track's steps to display (1-7)
        self.step_page = 0            # Current page (0 = steps 1-32, 1 = steps 33-64, etc.)
        self.step_states = {}         # {track: [bool]*128} - step on/off states per track

        # Sampler step sequencer state (7 sample pads, each with 128 steps)
        self.sampler_step_states = {}  # {pad_index: [bool]*128} - step states per sample pad

        # Bar length per track (defaults to 1 bar = 16 steps)
        self.track_bar_length = {i: 1 for i in range(1, 12)}

        # Variation per track (defaults to variation 1)
        self.track_variation = {i: 1 for i in range(1, 12)}

        # Variation mode: 3 or 6 variations available (global setting)
        self.variation_mode = 3  # Default: 3 variations

        # Track states (1-11)
        self.track_states = [MuteState.UNMUTED] * 11

        # Selected track for keyboard input (default SYNTH 1)
        self.keyboard_track = Track.SYNTH1
        self.patch_name = ""  # Patch name (updated from Seqtrak feedback)

        # Active notes for proper note-off
        self.active_notes = {}  # {pad_note: midi_note}

        # Scale settings
        self.scale_index = 1  # Minor
        self.scale_scroll_offset = 0
        self.root_note = 0  # C
        self.in_key_mode = True

        # Tempo (for display, synced from Seqtrak on startup)
        # None = unknown, will be queried from Seqtrak
        self.tempo = None

        # Master volume (0-127)
        self.master_volume = 100

        # Mixer mode state
        self.mixer_page = 0              # 0 or 1 (12 items across 2 pages)
        self.track_volumes = [100] * 11  # Volume per track (0-127)

        # DRUM bus state (virtual channel controlling all drum tracks)
        self.drum_bus_volume = 100       # 0-127, scales all drum track volumes
        self.drum_bus_muted = False
        self.drum_bus_soloed = False

        # Swing (0-28, even numbers only)
        self.swing = 0

        # Accent mode (fixed velocity)
        self.accent_mode = False
        self.accent_velocity = 127

        # Note repeat state
        self.note_repeat_active = False
        self.note_repeat_rate = None  # Current subdivision rate in ms
        self.note_repeat_notes = {}   # {pad_note: (midi_note, track, last_trigger_time)}

        # Arpeggiator state (software-based, runs in Python)
        self.arp_mode_active = False           # True = Arp mode, False = Note Repeat
        self.arp_enabled = False               # Is arpeggiator currently running
        self.arp_rate = None                   # Subdivision rate (in beats, like note_repeat)
        self.arp_pattern = 'up'                # Current pattern name
        self.arp_pattern_index = 0             # Index for cycling through ARP_PATTERNS
        self.arp_octave_range = 1              # 1-4 octaves to span
        self.arp_gate = 0.5                    # Gate percentage (0.1-0.9)
        self.arp_latch = False                 # Latch mode: notes sustain after release

        # Arpeggiator note tracking
        self.arp_held_notes = []               # Notes currently held (in press order for As Played)
        self.arp_latched_notes = []            # Notes preserved by latch mode
        self.arp_sequence = []                 # Computed arp sequence with octave extension
        self.arp_position = 0                  # Current position in sequence
        self.arp_last_trigger_time = 0         # Timestamp of last note trigger
        self.arp_last_note_played = None       # For note-off before next note

        # LCD popup state
        self.lcd_popup_active = False
        self.lcd_popup_end_time = 0

        # Device mode state
        self.device_page = 0  # 0-1 for different parameter pages
        self.device_params = {}  # Cache: {(track, param_name): value}

        # Session view state (clip-launcher style)
        self.session_mode = False
        self.session_page = 0  # 0 or 1 (like mixer_page)
        self.session_selected_col = 0  # Currently selected column (0-7)
        self.session_selected_row = 0  # Currently selected row (0-5)
        # Pattern assignments: session_patterns[mixer_pos][row] = pattern (1-6)
        # 12 mixer positions × 6 rows
        self.session_patterns = [[1] * 6 for _ in range(12)]

        # Isomorphic layout (same as Reason app)
        self.layout = IsomorphicLayout()
        self.layout.set_scale(self.root_note, SCALE_NAMES[self.scale_index])
        self.layout.set_in_key_mode(self.in_key_mode)

        # Ports (set in run())
        self.push_in = None
        self.push_out = None
        self.seqtrak = None
        self.protocol = None

        # Track program/bank info per channel (for preset display)
        # Initialize MSB to 63 for tracks 1-10 (Drum/Synth/DX), 62 for track 11 (Sampler)
        self.track_bank_msb = [0, 63, 63, 63, 63, 63, 63, 63, 63, 63, 63, 62]
        self.track_bank_lsb = [0] * 12   # Bank LSB per track
        self.track_program = [0] * 12    # Program number per track

        # Initialize each track with its default preset
        for track, preset_num in TRACK_DEFAULTS.items():
            bank_lsb, program = preset_to_bank_program(preset_num)
            self.track_bank_lsb[track] = bank_lsb
            self.track_program[track] = program

        # Encoder accumulators for slower response (require multiple ticks)
        self.patch_encoder_accum = 0
        self.patch_encoder_threshold = 4  # Ticks needed per patch change

        self.running = False

    # -------------------------------------------------------------------------
    # Port Discovery
    # -------------------------------------------------------------------------

    def find_push_ports(self):
        """Find Push MIDI ports."""
        push_in = push_out = None

        for name in mido.get_input_names():
            if 'Ableton Push' in name and 'User' in name:
                push_in = name
                break

        for name in mido.get_output_names():
            if 'Ableton Push' in name and 'User' in name:
                push_out = name
                break

        return push_in, push_out

    # -------------------------------------------------------------------------
    # Seqtrak Message Handling
    # -------------------------------------------------------------------------

    def handle_seqtrak_message(self, msg):
        """Handle any MIDI message from Seqtrak."""
        if msg.type == 'sysex':
            self.handle_seqtrak_sysex(msg.data)
        elif msg.type == 'control_change':
            # Bank Select messages
            channel = msg.channel + 1  # Convert to 1-indexed track
            if 1 <= channel <= 11:
                if msg.control == 0:  # Bank Select MSB
                    self.track_bank_msb[channel] = msg.value
                elif msg.control == 32:  # Bank Select LSB
                    self.track_bank_lsb[channel] = msg.value
        elif msg.type == 'program_change':
            # Program change - update track preset info
            channel = msg.channel + 1  # Convert to 1-indexed track
            if 1 <= channel <= 11:
                self.track_program[channel] = msg.program
                # If this is the currently selected track, update display
                if channel == self.keyboard_track:
                    bank = self.track_bank_msb[channel]
                    sub = self.track_bank_lsb[channel]
                    prog = msg.program
                    self.patch_name = get_preset_name_short(channel, bank, sub, prog)
                    print(f"  Preset: {self.patch_name}")
                    self.update_display()

    def handle_seqtrak_sysex(self, data):
        """Parse and handle SysEx from Seqtrak."""
        # Expected format: 43 10 7F 1C 0C [addr_h] [addr_m] [addr_l] [data...]
        if len(data) < 8:
            return

        # Check Yamaha header
        if data[0] != 0x43:
            return

        # Check Seqtrak model ID (0x0C at position 4)
        if len(data) < 5 or data[4] != 0x0C:
            return

        # Extract address (bytes 5-7) and data (byte 8+)
        addr = list(data[5:8])
        sysex_data = list(data[8:])

        # Debug: show address for preset-related messages
        if addr == Address.PRESET_NAME:
            print(f"  [SysEx] Got PRESET_NAME response, {len(sysex_data)} bytes")

        # Play State
        if addr == Address.PLAY_STATE and sysex_data:
            self.is_playing = (sysex_data[0] == 0x01)
            self.update_transport_leds()
            self.update_display()
            print(f"Seqtrak: {'PLAYING' if self.is_playing else 'STOPPED'}")

        # Record State
        elif addr == Address.RECORD_STATE and sysex_data:
            self.is_recording = (sysex_data[0] == 0x01)
            self.set_button_led(BUTTONS['record'], LED_ON if self.is_recording else LED_DIM)
            self.update_display()
            print(f"Seqtrak: RECORD {'ON' if self.is_recording else 'OFF'}")

        # Sample Record State
        elif addr == Address.SAMPLE_RECORD and sysex_data:
            self.is_sample_recording = (sysex_data[0] == 0x01)
            self.set_button_led(BUTTONS['record'], LED_ON if self.is_sample_recording else LED_DIM)
            self.update_display()
            print(f"Seqtrak: SAMPLE RECORD {'ON' if self.is_sample_recording else 'OFF'}")

        # Preset Name
        elif addr == Address.PRESET_NAME and sysex_data:
            # Extract ASCII name from data
            name_bytes = []
            for b in sysex_data:
                if b == 0x00:
                    break
                if 0x20 <= b <= 0x7E:
                    name_bytes.append(b)
            self.patch_name = bytes(name_bytes).decode('ascii', errors='ignore').strip()
            self.update_display()
            print(f"Seqtrak: Preset '{self.patch_name}'")

        # Tempo
        elif addr == Address.TEMPO and len(sysex_data) >= 2:
            # 2-byte format: MSB, LSB
            msb = sysex_data[0] & 0x7F
            lsb = sysex_data[1] & 0x7F
            self.tempo = (msb << 7) | lsb
            self.update_display()
            print(f"Seqtrak: Tempo {self.tempo} BPM")

    # -------------------------------------------------------------------------
    # Push Communication
    # -------------------------------------------------------------------------

    def send_sysex(self, data):
        """Send SysEx to Push."""
        msg = mido.Message('sysex', data=SYSEX_HEADER + data)
        self.push_out.send(msg)

    def set_lcd_segments(self, line, seg0="", seg1="", seg2="", seg3=""):
        """Set LCD line using 4 segments (17 chars each, centered)."""
        parts = [seg0, seg1, seg2, seg3]
        text = ""
        for part in parts:
            text += part[:CHARS_PER_SEGMENT].center(CHARS_PER_SEGMENT)

        line_addr = LCD_LINES.get(line, LCD_LINES[1])
        data = [line_addr, 0x00, 0x45, 0x00]
        data.extend([ord(c) for c in text])
        self.send_sysex(data)

    def set_lcd_line_raw(self, line, text):
        """Set LCD line with raw 68-char string."""
        text = text[:68].ljust(68)
        line_addr = LCD_LINES.get(line, LCD_LINES[1])
        data = [line_addr, 0x00, 0x45, 0x00]
        data.extend([ord(c) for c in text])
        self.send_sysex(data)

    def set_pad_color(self, note, color):
        """Set pad LED color."""
        self.push_out.send(mido.Message('note_on', note=note, velocity=color))

    def set_button_led(self, cc, value):
        """Set button LED (0=off, 1=dim, 4=on)."""
        self.push_out.send(mido.Message('control_change', control=cc, value=value))

    def clear_all_pads(self):
        """Turn off all pad LEDs."""
        for note in range(36, 100):
            self.set_pad_color(note, COLOR_OFF)

    # -------------------------------------------------------------------------
    # Display Updates
    # -------------------------------------------------------------------------

    def update_display(self):
        """Update LCD based on current mode."""
        # Clear all 4 lines first to prevent stale content
        self._clear_display()

        if self.current_mode == 'welcome':
            self._update_welcome_display()
        elif self.current_mode == 'scale':
            self._update_scale_display()
        elif self.current_mode == 'track':
            self._update_track_display()
        elif self.current_mode == 'device':
            self._update_device_display()
        elif self.current_mode == 'mixer':
            self._update_mixer_display()
        elif self.current_mode == 'note':
            self._update_note_display()
        else:
            self._update_note_display()

    def _clear_display(self):
        """Clear all 4 LCD lines with spaces."""
        blank = " " * 17  # Full segment of spaces
        for line in range(1, 5):
            self.set_lcd_segments(line, blank, blank, blank, blank)

    def _update_welcome_display(self):
        """Show welcome/loading screen."""
        self.set_lcd_segments(1, "", "OpenPush", "", "")
        self.set_lcd_segments(2, "", "Seqtrak Bridge", "", "")
        self.set_lcd_segments(3, "", "", "", "")
        self.set_lcd_segments(4, "Track", "Device", "Mixer", "to start")

    def _update_track_display(self):
        """Update LCD for track mode - mode-specific display."""
        kb_track = Track.NAMES.get(self.keyboard_track, f"T{self.keyboard_track}")
        octave = self.layout.get_octave()
        variation = self.track_variation.get(self.keyboard_track, 1)
        tempo_str = f"{self.tempo} BPM" if self.tempo else "--- BPM"
        var_mode_str = f"{self.variation_mode} Var"  # "3 Var" or "6 Var"

        # Mode-specific display
        if self.current_pad_mode == PadMode.DRUM:
            # Drum mode: show track, step sequencer info, bar length
            mode_info = "DRUM"
            selected_drum = Track.NAMES.get(self.selected_drum_track, f"T{self.selected_drum_track}")
            bars = self.track_bar_length.get(self.keyboard_track, 1)
            page_info = f"Pg {self.step_page + 1}/4"

            # Line 1: Track name, patch info, mode info, variation label
            self.set_lcd_segments(1, kb_track, self.patch_name or "", mode_info, "Variation")
            # Line 2: Step sequencer info, variation value
            self.set_lcd_segments(2, f"Steps:{selected_drum}", page_info, f"{bars} Bar(s)", f"Var {variation}")
            # Line 3: Variation mode display
            self.set_lcd_segments(3, "", "", "", var_mode_str)
            # Line 4: BPM
            self.set_lcd_segments(4, "", "", "", tempo_str)

        elif self.current_pad_mode == PadMode.SAMPLER:
            # Sampler mode: split view with sample pads + step sequencer
            pad_num = self.selected_sampler_pad + 1
            pad_info = self.sampler_pad_presets[self.selected_sampler_pad]
            pad_preset = get_preset_name_short(11, pad_info['bank_msb'], pad_info['bank_lsb'], pad_info['program'])
            bars = self.track_bar_length.get(self.keyboard_track, 1)
            page_info = f"Pg {self.step_page + 1}/4"

            # Line 1: Track name, mode labels, variation label
            self.set_lcd_segments(1, kb_track, "SAMPLER", "STEP", "Variation")
            # Line 2: Selected pad, step info, bar length, variation value
            self.set_lcd_segments(2, f"Pad {pad_num}", page_info, f"{bars} Bar(s)", f"Var {variation}")
            # Line 3: Variation mode display
            self.set_lcd_segments(3, "", "", "", var_mode_str)
            # Line 4: BPM
            self.set_lcd_segments(4, "", "", "", tempo_str)

        else:
            # Melodic mode: show scale info
            root_name = ROOT_NAMES[self.root_note]
            scale_name = get_scale_display_name(SCALE_NAMES[self.scale_index])
            bars = self.track_bar_length.get(self.keyboard_track, 1)

            # Line 1: Track name, patch info, mode label, variation label
            self.set_lcd_segments(1, kb_track, self.patch_name or "", "MELODIC", "Variation")
            # Line 2: Scale, octave, bar length, variation value
            self.set_lcd_segments(2, f"{root_name} {scale_name}", f"Oct {octave}", f"{bars} Bar(s)", f"Var {variation}")
            # Line 3: Variation mode display
            self.set_lcd_segments(3, "", "", "", var_mode_str)
            # Line 4: BPM
            self.set_lcd_segments(4, "", "", "", tempo_str)

    def _update_device_display(self):
        """Update LCD for device mode with parameter names and values."""
        kb_track = Track.NAMES.get(self.keyboard_track, f"T{self.keyboard_track}")
        page = self.device_page + 1
        total_pages = self._get_device_max_pages()

        # Line 1: Track, DEVICE label, page info, preset
        self.set_lcd_segments(1, kb_track, "DEVICE", f"Pg {page}/{total_pages}", self.patch_name or "")

        # Get current page parameters (track-type-aware)
        all_params = self._get_device_params()
        params = all_params[self.device_page]

        # Build parameter labels (2 per segment) for line 2
        # Build parameter values (2 per segment) for line 3
        labels = []
        values = []
        for i in range(8):
            label, cc, default, fmt_func = params[i]
            if not label:
                labels.append("")
                values.append("")
                continue

            # Get current value from cache, or use default
            val = self.device_params.get((self.keyboard_track, cc), default)

            # Format value
            if fmt_func:
                val_str = fmt_func(val)
            else:
                val_str = str(val)

            labels.append(label)
            values.append(val_str)

        # Format into segments (2 params per segment)
        def format_pair(items, idx):
            """Format 2 items for a segment."""
            a = items[idx] if idx < len(items) else ""
            b = items[idx + 1] if idx + 1 < len(items) else ""
            return f"{a:^8s}{b:^9s}"

        self.set_lcd_segments(2,
            format_pair(labels, 0), format_pair(labels, 2),
            format_pair(labels, 4), format_pair(labels, 6))

        self.set_lcd_segments(3,
            format_pair(values, 0), format_pair(values, 2),
            format_pair(values, 4), format_pair(values, 6))

        # Line 4: Empty (page navigation via CC 62/63 buttons)
        self.set_lcd_segments(4, "", "", "", "")

    def _update_mixer_display(self):
        """Update LCD for mixer mode with track volumes.

        Names on line 1, volumes on line 2, 2 tracks per segment.
        Uses MIXER_TRACK_ORDER for display order (melodic, drums, bus, sampler).

        Page 0: Positions 0-7 (SYN1, SYN2, DX, KICK, SNAR, CLAP, HAT1, HAT2)
        Page 1: Positions 8-11 (PRC1, PRC2, DRUM, SMPL) - encoders 5-8 inactive

        Display layout:
        Line 1: [SYN1 SYN2]  [DX   KICK]  [SNAR CLAP]  [HAT1 HAT2]
        Line 2: [ 79   85 ]  [ 90  100 ]  [ 75   80 ]  [ 65   70 ]
        Line 3: (empty)
        Line 4: (empty)
        """
        base_pos = self.mixer_page * 8  # 0 or 8

        def get_name(pos):
            """Get track name for position, or empty if out of range."""
            if pos >= len(MIXER_TRACK_ORDER):
                return ""
            return MIXER_DISPLAY_NAMES[pos]

        def get_volume(pos):
            """Get volume as 0-100 string for position, or empty if out of range."""
            if pos >= len(MIXER_TRACK_ORDER):
                return ""
            track = MIXER_TRACK_ORDER[pos]
            if track is None:  # DRUM bus
                vol = round(self.drum_bus_volume * 100 / 127)
            else:
                vol = round(self.track_volumes[track - 1] * 100 / 127)
            return str(vol)

        def format_segment_names(pos1, pos2):
            """Format 2 track names for a segment (17 chars)."""
            name1 = get_name(pos1)
            name2 = get_name(pos2)
            # Always return 17 chars - spaces if empty
            return f"{name1:^8s}{name2:^9s}"

        def format_segment_vols(pos1, pos2):
            """Format 2 volumes for a segment (17 chars), aligned under names."""
            vol1 = get_volume(pos1)
            vol2 = get_volume(pos2)
            # Always return 17 chars - spaces if empty
            return f"{vol1:^8s}{vol2:^9s}"

        # Line 1: Names (2 per segment)
        self.set_lcd_segments(1,
            format_segment_names(base_pos, base_pos + 1),
            format_segment_names(base_pos + 2, base_pos + 3),
            format_segment_names(base_pos + 4, base_pos + 5),
            format_segment_names(base_pos + 6, base_pos + 7))

        # Line 2: Volumes (2 per segment)
        self.set_lcd_segments(2,
            format_segment_vols(base_pos, base_pos + 1),
            format_segment_vols(base_pos + 2, base_pos + 3),
            format_segment_vols(base_pos + 4, base_pos + 5),
            format_segment_vols(base_pos + 6, base_pos + 7))

        # Lines 3-4: Empty
        self.set_lcd_segments(3, "", "", "", "")
        self.set_lcd_segments(4, "", "", "", "")

    def _update_note_display(self):
        """Update LCD for note/play mode."""
        root_name = ROOT_NAMES[self.root_note]
        scale_name = get_scale_display_name(SCALE_NAMES[self.scale_index])
        octave = self.layout.get_octave()
        mode_str = "In-Key" if self.in_key_mode else "Chromatic"
        transport = "PLAYING" if self.is_playing else "STOPPED"

        kb_track = Track.NAMES.get(self.keyboard_track, f"T{self.keyboard_track}")

        self.set_lcd_segments(1, "SEQTRAK", f"{root_name} {scale_name}", f"Oct {octave}", transport)
        self.set_lcd_segments(2, f"KB: {kb_track}", mode_str, "", "")
        self.set_lcd_segments(3, "Play/Stop", "Mute mode", "Oct Up/Dn", "Scale")
        self.set_lcd_segments(4, "", "", "", "open-push")

    def _update_mute_display(self):
        """Update LCD for mute mode."""
        transport = "PLAYING" if self.is_playing else "STOPPED"
        self.set_lcd_segments(1, "SEQTRAK", "MUTE MODE", transport, "")
        self.set_lcd_segments(2, "Tracks 1-8", "Row 2: 9-11", "", "")
        self.set_lcd_segments(3, "Pad = Toggle", "Red=Mute", "Yel=Solo", "Grn=Play")
        self.set_lcd_segments(4, "", "", "", "")

    def _update_scale_display(self):
        """Update LCD for scale selection mode (matches Reason app)."""
        total_scales = len(SCALE_NAMES)

        # Keep current scale visible
        if self.scale_index < self.scale_scroll_offset:
            self.scale_scroll_offset = self.scale_index
        elif self.scale_index >= self.scale_scroll_offset + 4:
            self.scale_scroll_offset = self.scale_index - 3

        # Build scale list
        scale_texts = []
        for i in range(4):
            idx = self.scale_scroll_offset + i
            if idx < total_scales:
                name = get_scale_display_name(SCALE_NAMES[idx])
                if idx == self.scale_index:
                    scale_texts.append(f">{name[:15]}")
                else:
                    scale_texts.append(f" {name[:15]}")
            else:
                scale_texts.append("")

        # Root display
        def format_roots(roots_list):
            parts = []
            for r in roots_list:
                label = ROOT_NAMES[r]
                if r == self.root_note:
                    parts.append(f"[{label}]")
                else:
                    parts.append(f" {label} ")
            return "  ".join(parts)

        upper_seg1 = format_roots(ROOT_UPPER_NOTES[:3])
        upper_seg2 = format_roots(ROOT_UPPER_NOTES[3:])
        lower_seg1 = format_roots(ROOT_LOWER_NOTES[:3])
        lower_seg2 = format_roots(ROOT_LOWER_NOTES[3:])

        in_key_mark = ">" if self.in_key_mode else " "
        chromat_mark = ">" if not self.in_key_mode else " "

        def build_line(scale_text, root_seg1, root_seg2, mode_text):
            seg0 = scale_text[:17].ljust(17)
            seg1 = root_seg1[:17].center(17)
            seg2 = root_seg2[:17].center(17)
            seg3 = mode_text[:17].rjust(17)
            return seg0 + seg1 + seg2 + seg3

        self.set_lcd_line_raw(1, scale_texts[0].ljust(17) + " " * 51)
        self.set_lcd_line_raw(2, scale_texts[1].ljust(17) + " " * 51)
        self.set_lcd_line_raw(3, build_line(scale_texts[2], upper_seg1, upper_seg2, f"{in_key_mark}In Key"))
        self.set_lcd_line_raw(4, build_line(scale_texts[3], lower_seg1, lower_seg2, f"{chromat_mark}Chromat"))

    def update_transport_leds(self):
        """Update Play/Stop button LEDs."""
        if self.is_playing:
            self.set_button_led(BUTTONS['play'], LED_ON)
            self.set_button_led(BUTTONS['stop'], LED_DIM)
        else:
            self.set_button_led(BUTTONS['play'], LED_DIM)
            self.set_button_led(BUTTONS['stop'], LED_ON)

    def update_grid(self):
        """Update pad grid based on current mode."""
        if self.current_mode == 'mute':
            self._update_mute_grid()
        else:
            self._update_note_grid()

    def _update_note_grid(self):
        """Update grid based on current pad mode."""
        if self.current_pad_mode == PadMode.DRUM:
            self._update_drum_grid()
        elif self.current_pad_mode == PadMode.SAMPLER:
            self._update_sampler_grid()
        else:
            self._update_melodic_grid()

    def _update_melodic_grid(self):
        """Update grid for melodic mode (isomorphic keyboard)."""
        for row in range(8):
            for col in range(8):
                note = 36 + (row * 8) + col
                info = self.layout.get_pad_info(row, col)

                if info['is_root']:
                    color = COLOR_BLUE
                elif info['is_in_scale']:
                    color = COLOR_WHITE
                else:
                    color = COLOR_OFF if self.in_key_mode else COLOR_DIM

                self.set_pad_color(note, color)

    def _update_drum_grid(self):
        """Update grid for drum mode with split layout.

        Layout:
        - Rows 0-1 (bottom 2): 8 drum sound pads in 2x4 layout
        - Rows 2-3 (middle): Empty/off
        - Rows 4-7 (top 4): Step sequencer for selected drum track
        """
        # First, clear all pads
        for note in range(36, 100):
            self.set_pad_color(note, COLOR_OFF)

        # Bottom 2 rows: drum sound pads
        for i, (row, col) in enumerate(DRUM_PAD_POSITIONS):
            note = 36 + (row * 8) + col
            track = DRUM_PAD_TRACKS[i]

            if track == self.selected_drum_track:
                color = SAMPLER_SELECTED_COLOR  # Bright white for selected
            else:
                color = DRUM_TRACK_COLORS.get(track, COLOR_DIM)

            self.set_pad_color(note, color)

        # Rows 2-3: Empty (already cleared above)

        # Top 4 rows (rows 4-7): step sequencer
        # Row 7 (top) = steps 0-7, Row 6 = steps 8-15, Row 5 = steps 16-23, Row 4 = steps 24-31
        for row in range(4, 8):
            for col in range(8):
                # Calculate step index: top row first (row 7 = steps 0-7)
                step_index = ((7 - row) * 8) + col + (self.step_page * 32)
                note = 36 + (row * 8) + col

                # Check if step is beyond 128 steps
                if step_index >= 128:
                    self.set_pad_color(note, COLOR_OFF)
                else:
                    # Get step state for selected drum track
                    track_steps = self.step_states.get(self.selected_drum_track, [False] * 128)
                    step_on = track_steps[step_index] if step_index < len(track_steps) else False
                    color = STEP_COLOR_ON if step_on else STEP_COLOR_OFF
                    self.set_pad_color(note, color)

    def _update_sampler_grid(self):
        """Update grid for sampler mode - split view like drums.

        Layout:
        - Rows 0-1 (bottom 2): Sample pads (7 pads)
        - Rows 2-3 (middle): Empty
        - Rows 4-7 (top 4): Step sequencer for selected sample pad
        """
        for row in range(8):
            for col in range(8):
                note = 36 + (row * 8) + col
                pos = (row, col)

                # Check if it's a sampler pad position (bottom 2 rows)
                if pos in SAMPLER_PAD_POSITIONS:
                    pad_index = SAMPLER_PAD_POSITIONS.index(pos)
                    if pad_index == self.selected_sampler_pad:
                        color = SAMPLER_SELECTED_COLOR
                    else:
                        color = SAMPLER_PAD_COLORS[pad_index]
                    self.set_pad_color(note, color)

                # Step sequencer rows (top 4 rows)
                elif row >= 4:
                    # Calculate step index: row 7 = steps 0-7, row 6 = steps 8-15, etc.
                    step_index = ((7 - row) * 8) + col + (self.step_page * 32)

                    if step_index < 128:
                        # Get step state for selected sampler pad
                        pad_steps = self.sampler_step_states.get(self.selected_sampler_pad, [False] * 128)
                        step_on = pad_steps[step_index] if step_index < len(pad_steps) else False
                        color = STEP_COLOR_ON if step_on else STEP_COLOR_OFF
                        self.set_pad_color(note, color)
                    else:
                        self.set_pad_color(note, COLOR_OFF)

                # Middle rows (2-3) are empty
                else:
                    self.set_pad_color(note, COLOR_OFF)

    def _update_mute_grid(self):
        """Update grid for mute mode (track mutes on bottom rows)."""
        for row in range(8):
            for col in range(8):
                note = 36 + (row * 8) + col

                if row == 0:
                    # Row 0 = tracks 1-8
                    track = col + 1
                elif row == 1 and col < 3:
                    # Row 1, cols 0-2 = tracks 9-11
                    track = col + 9
                else:
                    self.set_pad_color(note, COLOR_OFF)
                    continue

                if track <= 11:
                    state = self.track_states[track - 1]
                    if state == MuteState.MUTED:
                        color = COLOR_RED
                    elif state == MuteState.SOLO:
                        color = COLOR_YELLOW
                    else:
                        color = COLOR_GREEN
                    self.set_pad_color(note, color)

    def _update_scale_button_leds(self):
        """Update button LEDs for scale selection mode."""
        if self.current_mode != 'scale':
            return

        UPPER_BRIGHT = 10
        UPPER_DIM = 7
        LOWER_BRIGHT = 13
        LOWER_DIM = 11

        at_top = self.scale_index == 0
        at_bottom = self.scale_index >= len(SCALE_NAMES) - 1

        self.set_button_led(SCALE_UP_CC, UPPER_DIM if at_top else UPPER_BRIGHT)
        self.set_button_led(SCALE_DOWN_CC, LOWER_DIM if at_bottom else LOWER_BRIGHT)

        for i, cc in enumerate(ROOT_UPPER_BUTTONS):
            root_val = ROOT_UPPER_NOTES[i]
            self.set_button_led(cc, UPPER_BRIGHT if root_val == self.root_note else UPPER_DIM)

        for i, cc in enumerate(ROOT_LOWER_BUTTONS):
            root_val = ROOT_LOWER_NOTES[i]
            self.set_button_led(cc, LOWER_BRIGHT if root_val == self.root_note else LOWER_DIM)

        self.set_button_led(IN_KEY_CC, UPPER_BRIGHT if self.in_key_mode else UPPER_DIM)
        self.set_button_led(CHROMAT_CC, LOWER_BRIGHT if not self.in_key_mode else LOWER_DIM)

    # -------------------------------------------------------------------------
    # Scale Mode
    # -------------------------------------------------------------------------

    def _enter_scale_mode(self):
        """Enter scale selection mode (only for melodic tracks)."""
        # Scale mode only available for melodic tracks (synths and DX)
        if self.current_pad_mode != PadMode.MELODIC:
            track_name = Track.NAMES.get(self.keyboard_track, f"T{self.keyboard_track}")
            print(f"Scale mode not available for {track_name} (only Synth/DX tracks)")
            return

        self.previous_mode = self.current_mode
        self.current_mode = 'scale'
        print("Entering Scale mode")
        self.set_button_led(BUTTONS['scale'], LED_ON)
        self._update_scale_button_leds()
        self.update_display()

    def _exit_scale_mode(self):
        """Exit scale selection mode."""
        print(f"Exiting Scale mode -> {ROOT_NAMES[self.root_note]} {get_scale_display_name(SCALE_NAMES[self.scale_index])}")

        # Clear scale buttons
        for cc in ROOT_UPPER_BUTTONS + ROOT_LOWER_BUTTONS + [SCALE_UP_CC, SCALE_DOWN_CC, IN_KEY_CC, CHROMAT_CC]:
            self.set_button_led(cc, 0)

        self.current_mode = self.previous_mode if self.previous_mode != 'scale' else 'note'
        self.set_button_led(BUTTONS['scale'], LED_DIM)
        self.update_display()
        self.update_grid()

    def _apply_scale_changes(self):
        """Apply current scale settings to layout."""
        self.layout.set_scale(self.root_note, SCALE_NAMES[self.scale_index])
        self.layout.set_in_key_mode(self.in_key_mode)
        self.update_grid()

    def _scroll_scale(self, direction):
        """Scroll through scale list."""
        total_scales = len(SCALE_NAMES)
        new_index = max(0, min(total_scales - 1, self.scale_index + direction))

        if new_index != self.scale_index:
            self.scale_index = new_index
            print(f"  Scale: {get_scale_display_name(SCALE_NAMES[self.scale_index])}")
            self._apply_scale_changes()
            self.update_display()
            self._update_scale_button_leds()

    def _handle_scale_mode_button(self, cc, value):
        """Handle button press in scale mode."""
        if cc == 71:  # Encoder for scrolling
            if value < 64:
                self._scroll_scale(1)
            else:
                self._scroll_scale(-1)
            return

        if cc == SCALE_UP_CC:
            self._scroll_scale(-1)
            return

        if cc == SCALE_DOWN_CC:
            self._scroll_scale(1)
            return

        if cc == IN_KEY_CC:
            self.in_key_mode = True
            print("  Mode: In Key")
            self._apply_scale_changes()
            self.update_display()
            self._update_scale_button_leds()
            return

        if cc == CHROMAT_CC:
            self.in_key_mode = False
            print("  Mode: Chromatic")
            self._apply_scale_changes()
            self.update_display()
            self._update_scale_button_leds()
            return

        if cc in ROOT_UPPER_BUTTONS:
            idx = ROOT_UPPER_BUTTONS.index(cc)
            self.root_note = ROOT_UPPER_NOTES[idx]
            print(f"  Root: {ROOT_NAMES[self.root_note]}")
            self._apply_scale_changes()
            self.update_display()
            self._update_scale_button_leds()
            return

        if cc in ROOT_LOWER_BUTTONS:
            idx = ROOT_LOWER_BUTTONS.index(cc)
            self.root_note = ROOT_LOWER_NOTES[idx]
            print(f"  Root: {ROOT_NAMES[self.root_note]}")
            self._apply_scale_changes()
            self.update_display()
            self._update_scale_button_leds()
            return

    # -------------------------------------------------------------------------
    # Session Mode - Clip-Launcher Style Variation Selector
    # -------------------------------------------------------------------------

    def _enter_session_mode(self):
        """Enter session view - clip-launcher style.

        Layout matches mixer exactly:
        - Columns = Tracks (using MIXER_TRACK_ORDER)
        - Rows 0-5 = Variation slots
        - Rows 6-7 = unused (off)

        Behavior:
        - Press pad to SELECT slot
        - Turn encoder to SET pattern for selected slot
        - Press CC 36-43 buttons to LAUNCH that row's patterns
        """
        self.session_mode = True
        self.session_page = 0  # Start on page 0
        self.session_selected_col = 0  # Default selection
        self.session_selected_row = 0
        print("Entering Session mode")

        # Light session button
        self.set_button_led(BUTTONS['session'], LED_ON)

        # Enable page buttons (like mixer mode)
        self.set_button_led(BUTTONS['page_left'], LED_DIM)  # On page 0
        self.set_button_led(BUTTONS['page_right'], LED_ON)  # Can go to page 1

        self._update_session_grid()
        self._update_session_display()

    def _exit_session_mode(self):
        """Exit session view."""
        self.session_mode = False
        print("Exiting Session mode")

        # Dim session button
        self.set_button_led(BUTTONS['session'], LED_DIM)

        # Restore normal grid and display
        self.update_grid()
        self.update_display()

    def _update_session_grid(self):
        """Update pad grid for session view - matches mixer layout exactly.

        Layout (matches MIXER_TRACK_ORDER):
           Col0    Col1    Col2    Col3    Col4    Col5    Col6    Col7
           SYN1    SYN2    DX      KICK    SNAR    CLAP    HAT1    HAT2
        Row 5:    [slot]  [slot]  [slot]  [slot]  [slot]  [slot]  [slot]  [slot]
        Row 4:    [slot]  [slot]  [slot]  [slot]  [slot]  [slot]  [slot]  [slot]
        ...
        Row 0:    [slot]  [slot]  [slot]  [slot]  [slot]  [slot]  [slot]  [slot]
        Rows 6-7: unused (off)

        Colors:
        - Green (21): Currently selected slot
        - White (3): Available slot (brighter)
        - Yellow (13): DRUM bus column
        - Off (0): Invalid or unused
        """
        base_pos = self.session_page * 8  # Page 0: positions 0-7, Page 1: positions 8-11

        for col in range(8):
            mixer_pos = base_pos + col

            for row in range(8):
                note = 36 + (row * 8) + col

                if row < 6 and mixer_pos < len(MIXER_TRACK_ORDER):
                    track = MIXER_TRACK_ORDER[mixer_pos]

                    # Determine color
                    if col == self.session_selected_col and row == self.session_selected_row:
                        color = COLOR_GREEN  # Selected slot
                    elif track is None:
                        color = COLOR_YELLOW  # DRUM bus - distinctive color
                    else:
                        color = COLOR_WHITE  # Available slot (brighter)
                else:
                    color = COLOR_OFF  # Rows 6-7 or invalid position

                self.push_out.send(mido.Message('note_on', note=note, velocity=color, channel=0))

    def _update_session_display(self):
        """Update LCD for session mode - match mixer format exactly."""
        base_pos = self.session_page * 8

        # Line 1: Track names (EXACT same format as mixer)
        def format_segment_names(idx):
            pos1 = base_pos + idx
            pos2 = base_pos + idx + 1
            name1 = MIXER_DISPLAY_NAMES[pos1] if pos1 < len(MIXER_DISPLAY_NAMES) else ""
            name2 = MIXER_DISPLAY_NAMES[pos2] if pos2 < len(MIXER_DISPLAY_NAMES) else ""
            return f"{name1:^8s}{name2:^9s}"

        self.set_lcd_segments(1,
            format_segment_names(0), format_segment_names(2),
            format_segment_names(4), format_segment_names(6))

        # Line 2: Pattern number for each track in the selected row
        def format_segment_patterns(idx):
            pos1 = base_pos + idx
            pos2 = base_pos + idx + 1
            pat1 = str(self.session_patterns[pos1][self.session_selected_row]) if pos1 < len(MIXER_TRACK_ORDER) else ""
            pat2 = str(self.session_patterns[pos2][self.session_selected_row]) if pos2 < len(MIXER_TRACK_ORDER) else ""
            return f"{pat1:^8s}{pat2:^9s}"

        self.set_lcd_segments(2,
            format_segment_patterns(0), format_segment_patterns(2),
            format_segment_patterns(4), format_segment_patterns(6))

        # Line 3: Selection indicator
        selected_mixer_pos = base_pos + self.session_selected_col
        if selected_mixer_pos < len(MIXER_DISPLAY_NAMES):
            sel_name = MIXER_DISPLAY_NAMES[selected_mixer_pos]
            sel_pattern = self.session_patterns[selected_mixer_pos][self.session_selected_row]
            self.set_lcd_segments(3, f"{sel_name} Row{self.session_selected_row + 1}", f"Pattern {sel_pattern}", "", "")
        else:
            self.set_lcd_segments(3, "", "", "", "")

        # Line 4: Empty (clean interface)
        self.set_lcd_segments(4, "", "", "", "")

    def _handle_session_pad(self, row, col):
        """Handle pad press in session mode - SELECT the slot only.

        Does NOT change patterns. Just selects which slot is active.
        Use encoder or buttons to change the pattern for the selected slot.
        """
        if row >= 6:  # Rows 6-7 unused
            return

        base_pos = self.session_page * 8
        mixer_pos = base_pos + col

        if mixer_pos >= len(MIXER_TRACK_ORDER):
            return  # Invalid position

        # Update selection
        self.session_selected_col = col
        self.session_selected_row = row

        name = MIXER_DISPLAY_NAMES[mixer_pos]
        pattern = self.session_patterns[mixer_pos][row]
        print(f"  Selected: {name} Row {row + 1} (Pattern {pattern})")

        self._update_session_grid()
        self._update_session_display()

    def _handle_session_encoder(self, encoder_index, delta):
        """Handle encoder turn in session mode - set pattern for selected slot.

        Only responds if encoder matches selected column.
        """
        if encoder_index != self.session_selected_col:
            return  # Only respond to encoder for selected column

        base_pos = self.session_page * 8
        mixer_pos = base_pos + encoder_index

        if mixer_pos >= len(MIXER_TRACK_ORDER):
            return

        row = self.session_selected_row
        current_pattern = self.session_patterns[mixer_pos][row]

        # Adjust pattern (1-6)
        if delta > 0:
            new_pattern = min(6, current_pattern + 1)
        else:
            new_pattern = max(1, current_pattern - 1)

        if new_pattern != current_pattern:
            self.session_patterns[mixer_pos][row] = new_pattern
            name = MIXER_DISPLAY_NAMES[mixer_pos]
            print(f"  {name} Row {row + 1}: Pattern {new_pattern}")
            self._update_session_display()

    def _handle_session_row_launch(self, row):
        """Handle CC 36-43 button press in session mode - LAUNCH this row.

        Sends per-track variation for each track based on session_patterns.
        Each track can have a different variation assigned in the session grid.
        """
        if row >= 6:
            return

        base_pos = self.session_page * 8

        # Send variation to each track based on pattern assignments
        launched_tracks = []
        for col in range(8):
            mixer_pos = base_pos + col
            if mixer_pos < len(MIXER_TRACK_ORDER):
                track = MIXER_TRACK_ORDER[mixer_pos]
                if track is not None:  # Skip DRUM bus
                    pattern = self.session_patterns[mixer_pos][row]
                    self.protocol.select_track_variation(track, pattern)
                    launched_tracks.append(f"{MIXER_DISPLAY_NAMES[mixer_pos]}:{pattern}")

        print(f"  Launched Row {row + 1}: {', '.join(launched_tracks)}")

    # -------------------------------------------------------------------------
    # Mode Switching (matching Reason app pattern)
    # -------------------------------------------------------------------------

    def _set_mode(self, mode):
        """Switch to a different mode and update display."""
        # Exit session mode when switching to another mode
        if self.session_mode:
            self._exit_session_mode()

        # Track previous mode for returning from scale mode
        if self.current_mode in ('track', 'device', 'mixer', 'note'):
            self.previous_mode = self.current_mode

        self.current_mode = mode
        print(f"Mode: {mode}")

        # Update button LEDs for mode buttons
        self.set_button_led(BUTTONS['volume'], LED_ON if mode == 'mixer' else LED_DIM)
        self.set_button_led(BUTTONS['device'], LED_ON if mode == 'device' else LED_DIM)
        self.set_button_led(BUTTONS['note'], LED_ON if mode == 'note' else LED_DIM)
        self.set_button_led(BUTTONS['scale'], LED_ON if mode == 'scale' else LED_DIM)
        self.set_button_led(BUTTONS['track'], LED_ON if mode == 'track' else LED_DIM)

        # Track mode: light up track nav buttons (CC 20 = prev, CC 102 = next)
        if mode == 'track':
            self.set_button_led(BUTTONS['upper_1'], LED_ON)  # CC 20 - prev track
            self.set_button_led(BUTTONS['lower_1'], LED_ON)  # CC 102 - next track
        elif mode == 'mixer':
            # Mixer mode: initialize mixer page and update button LEDs
            self.mixer_page = 0
            self._update_mixer_button_leds()
            # Page buttons for mixer navigation
            self.set_button_led(BUTTONS['page_left'], LED_DIM)  # On page 0, can't go back
            self.set_button_led(BUTTONS['page_right'], LED_ON)  # Can go to page 1
        elif mode == 'device':
            # Device mode: initialize device page and enable page buttons
            self.device_page = 0
            max_page = self._get_device_max_pages() - 1
            self.set_button_led(BUTTONS['page_left'], LED_DIM)  # On page 0, can't go back
            self.set_button_led(BUTTONS['page_right'], LED_ON if max_page > 0 else LED_DIM)
        else:
            self.set_button_led(BUTTONS['upper_1'], LED_OFF)
            self.set_button_led(BUTTONS['lower_1'], LED_OFF)

        # Turn off page buttons when not in mixer, device, or step sequencer mode
        if mode not in ('mixer', 'device') and self.current_pad_mode not in (PadMode.DRUM, PadMode.SAMPLER):
            self.set_button_led(BUTTONS['page_left'], LED_OFF)
            self.set_button_led(BUTTONS['page_right'], LED_OFF)

        # Patch cycling buttons always available (CC 22, CC 104) - but not in mixer mode
        if mode != 'mixer':
            self.set_button_led(BUTTONS['upper_3'], LED_ON)  # CC 22 - prev patch
            self.set_button_led(BUTTONS['lower_3'], LED_ON)  # CC 104 - next patch

        # Update display
        self.update_display()

        # Update grid
        self.update_grid()

    # -------------------------------------------------------------------------
    # Input Handlers
    # -------------------------------------------------------------------------

    def handle_button(self, cc, value):
        """Handle button press/release."""
        # Track shift state
        if cc == BUTTONS['shift']:
            self.shift_held = (value > 0)
            return

        # Only process button presses, not releases
        if value == 0:
            return

        # Scale mode buttons
        if self.current_mode == 'scale':
            scale_ccs = ROOT_UPPER_BUTTONS + ROOT_LOWER_BUTTONS + [SCALE_UP_CC, SCALE_DOWN_CC, IN_KEY_CC, CHROMAT_CC, 71]
            if cc in scale_ccs:
                self._handle_scale_mode_button(cc, value)
                return

        # Transport: Play/Stop toggle (matching Reason app pattern)
        if cc == BUTTONS['play']:
            if self.shift_held:
                # Shift+Play = Stop (return to zero)
                self.protocol.stop()
                self.is_playing = False
                self.update_transport_leds()
                self.update_display()
                print("  -> Sent Stop (Shift+Play = return to zero)")
            elif self.is_playing:
                # Already playing -> Stop
                self.protocol.stop()
                self.is_playing = False
                self.update_transport_leds()
                self.update_display()
                print("■ STOP (toggle)")
            else:
                # Not playing -> Play
                self.protocol.start()
                self.is_playing = True
                self.update_transport_leds()
                self.update_display()
                print("▶ PLAY")

        elif cc == BUTTONS['stop']:
            self.protocol.stop()
            self.is_playing = False
            self.update_transport_leds()
            self.update_display()
            print("■ STOP")

        elif cc == BUTTONS['record']:
            if self.shift_held:
                # Shift+Record = Sample recording
                self.is_sample_recording = not self.is_sample_recording
                if self.is_sample_recording:
                    # Send active sampler element before starting recording
                    self.protocol.select_sampler_element(self.selected_sampler_pad)
                self.protocol.sample_record(self.is_sample_recording)
                # Blink record LED when sample recording
                self.set_button_led(BUTTONS['record'], LED_ON if self.is_sample_recording else LED_DIM)
                self.update_display()
                pad_num = self.selected_sampler_pad + 1
                print(f"🎤 SAMPLE RECORD {'ON (Pad ' + str(pad_num) + ')' if self.is_sample_recording else 'OFF'}")
            else:
                # Normal record toggle via SysEx
                self.is_recording = not self.is_recording
                self.protocol.record(self.is_recording)
                self.set_button_led(BUTTONS['record'], LED_ON if self.is_recording else LED_DIM)
                self.update_display()
                print(f"● RECORD {'ON' if self.is_recording else 'OFF'}")

        elif cc == BUTTONS['tap_tempo']:
            # Tap tempo - calculates BPM from tap intervals
            new_bpm = self.protocol.tap_tempo()
            if new_bpm:
                self.tempo = new_bpm
                self.update_display()
                print(f"  Tap Tempo: {new_bpm} BPM")
            else:
                print("  Tap...")

        # Octave
        elif cc == BUTTONS['octave_up']:
            self.layout.shift_octave(1)
            self.update_grid()
            self.update_display()
            print(f"Octave: {self.layout.get_octave()}")

        elif cc == BUTTONS['octave_down']:
            self.layout.shift_octave(-1)
            self.update_grid()
            self.update_display()
            print(f"Octave: {self.layout.get_octave()}")

        # Repeat button (CC 56) - toggles note repeat/arp mode
        # Shift+Repeat = toggle latch (in arp mode)
        elif cc == BUTTONS['repeat']:
            if self.shift_held and self.arp_mode_active:
                # Shift + Repeat = toggle latch mode
                self.arp_latch = not self.arp_latch
                self._show_lcd_popup("LATCH", "ON" if self.arp_latch else "OFF")
                print(f"Arp Latch: {'ON' if self.arp_latch else 'OFF'}")
                if not self.arp_latch:
                    # Clear latched notes when disabling latch
                    self._release_all_arp_notes()
                    self.arp_latched_notes = []
                    self._rebuild_arp_sequence()
            elif self.arp_mode_active:
                # Exit arp mode
                self._exit_arp_mode()
            elif self.note_repeat_active:
                # Exit note repeat mode
                self._exit_note_repeat_mode()
            else:
                # Enter note repeat mode (regular, not arp)
                self._enter_note_repeat_mode()

        # Accent button (CC 57) - toggles fixed velocity mode
        elif cc == BUTTONS['accent']:
            self.accent_mode = not self.accent_mode
            self.set_button_led(BUTTONS['accent'], LED_ON if self.accent_mode else LED_DIM)
            print(f"Accent: {'ON (vel={self.accent_velocity})' if self.accent_mode else 'OFF'}")

        # Shift + Subdivision buttons (CC 36-43) = Enter/set Arp mode
        # (Must come BEFORE session mode check)
        elif 36 <= cc <= 43 and self.shift_held and not self.session_mode:
            if not self.arp_mode_active:
                self._enter_arp_mode()
            name, beats = NOTE_REPEAT_SUBDIVISIONS[cc]
            self.arp_rate = beats
            self._light_arp_leds(selected_cc=cc)
            self._show_lcd_popup("ARP", f"{name}")
            print(f"Arp Rate: {name}")

        # Session mode: CC 36-43 buttons launch rows (CC 43=row 0, CC 38=row 5)
        elif self.session_mode and 36 <= cc <= 43:
            row = 43 - cc  # CC 43 = row 0, CC 42 = row 1, ... CC 38 = row 5
            self._handle_session_row_launch(row)

        # Subdivision buttons (CC 36-43) - select note repeat rate when in note repeat mode
        # (Not in arp mode - arp mode uses Shift+CC 36-43)
        elif 36 <= cc <= 43 and self.note_repeat_active and not self.arp_mode_active:
            name, beats = NOTE_REPEAT_SUBDIVISIONS[cc]
            self.note_repeat_rate = beats
            self._light_subdivision_leds(selected_cc=cc)
            self._show_lcd_popup("REPEAT", f"{name}")
            print(f"Note Repeat Rate: {name}")

        # Subdivision buttons in arp mode (without shift) - also set rate
        elif 36 <= cc <= 43 and self.arp_mode_active:
            name, beats = NOTE_REPEAT_SUBDIVISIONS[cc]
            self.arp_rate = beats
            self._light_arp_leds(selected_cc=cc)
            self._show_lcd_popup("ARP", f"{name}")
            print(f"Arp Rate: {name}")

        # Track mode: CC 20 = prev track, CC 102 = next track
        elif self.current_mode == 'track' and cc == BUTTONS['upper_1']:  # CC 20
            self._select_prev_track()
        elif self.current_mode == 'track' and cc == BUTTONS['lower_1']:  # CC 102
            self._select_next_track()

        # Patch cycling: CC 22 = prev patch, CC 104 = next patch (not in mixer mode)
        elif cc == BUTTONS['upper_3'] and self.current_mode != 'mixer':  # CC 22
            self._cycle_patch(-1)
        elif cc == BUTTONS['lower_3'] and self.current_mode != 'mixer':  # CC 104
            self._cycle_patch(1)

        # Mode buttons (matching Reason app pattern)
        elif cc == BUTTONS['track']:
            self._set_mode('track')
        elif cc == BUTTONS['volume']:
            self._set_mode('mixer')
        elif cc == BUTTONS['device']:
            self._set_mode('device')
        elif cc == BUTTONS['note']:
            self._set_mode('note')
        elif cc == BUTTONS['session']:
            # Toggle session view
            if self.session_mode:
                self._exit_session_mode()
            else:
                self._enter_session_mode()
        elif cc == BUTTONS['scale']:
            if self.current_mode == 'scale':
                self._exit_scale_mode()
            else:
                self._enter_scale_mode()

        # Session mode: Upper buttons (CC 20-27) increment pattern, Lower (CC 102-109) decrement
        elif self.session_mode and 20 <= cc <= 27:
            button_index = cc - 20
            if button_index == self.session_selected_col:
                # Increment pattern for selected slot
                base_pos = self.session_page * 8
                mixer_pos = base_pos + self.session_selected_col
                if mixer_pos < len(MIXER_TRACK_ORDER):
                    row = self.session_selected_row
                    current = self.session_patterns[mixer_pos][row]
                    new_pattern = min(6, current + 1)
                    if new_pattern != current:
                        self.session_patterns[mixer_pos][row] = new_pattern
                        name = MIXER_DISPLAY_NAMES[mixer_pos]
                        print(f"  {name} Row {row + 1}: Pattern {new_pattern}")
                        self._update_session_display()

        elif self.session_mode and 102 <= cc <= 109:
            button_index = cc - 102
            if button_index == self.session_selected_col:
                # Decrement pattern for selected slot
                base_pos = self.session_page * 8
                mixer_pos = base_pos + self.session_selected_col
                if mixer_pos < len(MIXER_TRACK_ORDER):
                    row = self.session_selected_row
                    current = self.session_patterns[mixer_pos][row]
                    new_pattern = max(1, current - 1)
                    if new_pattern != current:
                        self.session_patterns[mixer_pos][row] = new_pattern
                        name = MIXER_DISPLAY_NAMES[mixer_pos]
                        print(f"  {name} Row {row + 1}: Pattern {new_pattern}")
                        self._update_session_display()

        # Mixer mode: Upper buttons (CC 20-27) = Solo, Lower buttons (CC 102-109) = Mute
        # Uses MIXER_TRACK_ORDER for display order
        elif self.current_mode == 'mixer' and 20 <= cc <= 27:
            # Upper row: Solo
            button_index = cc - 20
            mixer_pos = self.mixer_page * 8 + button_index
            if mixer_pos < len(MIXER_TRACK_ORDER):
                track = MIXER_TRACK_ORDER[mixer_pos]
                if track is None:
                    self._toggle_drum_bus_solo()
                else:
                    self._toggle_track_solo(track)

        elif self.current_mode == 'mixer' and 102 <= cc <= 109:
            # Lower row: Mute
            button_index = cc - 102
            mixer_pos = self.mixer_page * 8 + button_index
            if mixer_pos < len(MIXER_TRACK_ORDER):
                track = MIXER_TRACK_ORDER[mixer_pos]
                if track is None:
                    self._toggle_drum_bus_mute()
                else:
                    self._toggle_track_mute_simple(track)

        # Page navigation (session mode, mixer mode, device mode, and step sequencer modes)
        elif cc == BUTTONS['page_left']:  # CC 62
            if self.session_mode:
                # Session mode: page through tracks (like mixer)
                if self.session_page > 0:
                    self.session_page -= 1
                    self._update_session_grid()
                    self._update_session_display()
                    self.set_button_led(BUTTONS['page_left'], LED_DIM if self.session_page == 0 else LED_ON)
                    self.set_button_led(BUTTONS['page_right'], LED_ON)
                    print(f"  Session Page: {self.session_page + 1}")
            elif self.current_mode == 'mixer':
                # Mixer mode: page through tracks
                if self.mixer_page > 0:
                    self.mixer_page -= 1
                    self.update_display()
                    self._update_mixer_button_leds()
                    self.set_button_led(BUTTONS['page_left'], LED_DIM if self.mixer_page == 0 else LED_ON)
                    self.set_button_led(BUTTONS['page_right'], LED_ON)
                    print(f"  Mixer Page: {self.mixer_page + 1}")
            elif self.current_mode == 'device':
                # Device mode: page through parameter pages (track-type-aware)
                if self.device_page > 0:
                    self.device_page -= 1
                    self.update_display()
                    max_page = self._get_device_max_pages() - 1
                    self.set_button_led(BUTTONS['page_left'], LED_DIM if self.device_page == 0 else LED_ON)
                    self.set_button_led(BUTTONS['page_right'], LED_ON)
                    print(f"  Device Page: {self.device_page + 1}/{max_page + 1}")
            elif self.current_pad_mode in (PadMode.DRUM, PadMode.SAMPLER) and self.step_page > 0:
                self.step_page -= 1
                self.update_grid()
                self.update_display()
                # Update page button LEDs
                self.set_button_led(BUTTONS['page_left'], LED_DIM if self.step_page == 0 else LED_ON)
                self.set_button_led(BUTTONS['page_right'], LED_ON)
                print(f"  Step Page: {self.step_page + 1}")

        elif cc == BUTTONS['page_right']:  # CC 63
            if self.session_mode:
                # Session mode: page through tracks (like mixer)
                if self.session_page < 1:
                    self.session_page += 1
                    self._update_session_grid()
                    self._update_session_display()
                    self.set_button_led(BUTTONS['page_left'], LED_ON)
                    self.set_button_led(BUTTONS['page_right'], LED_DIM if self.session_page >= 1 else LED_ON)
                    print(f"  Session Page: {self.session_page + 1}")
            elif self.current_mode == 'mixer':
                # Mixer mode: page through tracks (2 pages: 1-8, 9-11)
                if self.mixer_page < 1:
                    self.mixer_page += 1
                    self.update_display()
                    self._update_mixer_button_leds()
                    self.set_button_led(BUTTONS['page_left'], LED_ON)
                    self.set_button_led(BUTTONS['page_right'], LED_DIM if self.mixer_page >= 1 else LED_ON)
                    print(f"  Mixer Page: {self.mixer_page + 1}")
            elif self.current_mode == 'device':
                # Device mode: page through parameter pages (track-type-aware)
                max_page = self._get_device_max_pages() - 1
                if self.device_page < max_page:
                    self.device_page += 1
                    self.update_display()
                    self.set_button_led(BUTTONS['page_left'], LED_ON)
                    self.set_button_led(BUTTONS['page_right'], LED_DIM if self.device_page >= max_page else LED_ON)
                    print(f"  Device Page: {self.device_page + 1}/{max_page + 1}")
            elif self.current_pad_mode in (PadMode.DRUM, PadMode.SAMPLER):
                # Allow up to 4 pages (128 steps / 32 steps per page)
                if self.step_page < 3:
                    self.step_page += 1
                    self.update_grid()
                    self.update_display()
                    # Update page button LEDs
                    self.set_button_led(BUTTONS['page_left'], LED_ON)
                    self.set_button_led(BUTTONS['page_right'], LED_DIM if self.step_page >= 3 else LED_ON)
                    print(f"  Step Page: {self.step_page + 1}")

        # Bar length buttons: CC 24 (decrement), CC 106 (increment) - not in mixer mode
        elif cc == BUTTONS['upper_5'] and self.current_mode != 'mixer':  # CC 24 - bar length down
            self._adjust_bar_length(-1)

        elif cc == BUTTONS['lower_5'] and self.current_mode != 'mixer':  # CC 106 - bar length up
            self._adjust_bar_length(1)

    def handle_encoder(self, cc, value):
        """Handle encoder turn."""
        # Relative encoder: 1-63 = clockwise, 65-127 = counter-clockwise
        if value < 64:
            delta = 1  # Clockwise
        else:
            delta = -1  # Counter-clockwise

        # Debug for CC 78
        if cc == 78:
            print(f"[DEBUG] CC 78 received, mode={self.current_mode}, shift={self.shift_held}, value={value}")

        # Tempo encoder (CC 14)
        if cc == 14:
            # Use actual delta for tempo (faster turns = bigger change)
            if value < 64:
                tempo_delta = value
            else:
                tempo_delta = value - 128

            # If tempo is unknown, request it from Seqtrak first
            if self.tempo is None:
                print("Tempo unknown - requesting from Seqtrak...")
                self.protocol.request_parameter(Address.TEMPO)
                return

            new_tempo = max(20, min(300, self.tempo + tempo_delta))
            if new_tempo != self.tempo:
                self.tempo = new_tempo
                self.protocol.set_tempo(self.tempo)
                self.update_display()
                print(f"Tempo: {self.tempo}")

        # Swing encoder (CC 15)
        elif cc == 15:
            # Swing range: 0-28, even numbers only
            new_swing = max(0, min(28, self.swing + (delta * 2)))
            if new_swing != self.swing:
                self.swing = new_swing
                self.protocol.set_swing(self.swing)
                self.update_display()
                print(f"Swing: {self.swing}")

        # Session mode: CC 71-78 encoders set pattern for selected slot
        # Must be checked BEFORE device/mixer modes to block other encoder behavior
        elif self.session_mode and 71 <= cc <= 78:
            encoder_index = cc - 71  # 0-7
            self._handle_session_encoder(encoder_index, delta)

        # Track mode: CC 78 = variation selection (1-6)
        # Shift+CC 78 = toggle between 3 and 6 variation modes
        # Must be checked BEFORE arp mode
        elif self.current_mode == 'track' and cc == 78:
            if self.shift_held:
                print(f"[DEBUG] Shift held, toggling variation mode (current: {self.variation_mode})")
                self._toggle_variation_mode()
            else:
                self._adjust_variation(delta)

        # Arp mode: CC 77 = pattern, CC 78 = octave range
        # Must be checked BEFORE device mode
        elif self.arp_mode_active and cc == 77:
            # Encoder 7: Cycle through arp patterns
            new_index = (self.arp_pattern_index + delta) % len(ARP_PATTERNS)
            if new_index != self.arp_pattern_index:
                self.arp_pattern_index = new_index
                self.arp_pattern = ARP_PATTERNS[new_index]
                self._rebuild_arp_sequence()
                pattern_name = ARP_PATTERN_NAMES[new_index]
                self._show_lcd_popup("PATTERN", pattern_name)
                print(f"Arp Pattern: {pattern_name}")

        elif self.arp_mode_active and cc == 78:
            # Encoder 8: Adjust octave range (1-4)
            new_range = max(1, min(4, self.arp_octave_range + delta))
            if new_range != self.arp_octave_range:
                self.arp_octave_range = new_range
                self._rebuild_arp_sequence()
                self._show_lcd_popup("OCTAVES", str(self.arp_octave_range))
                print(f"Arp Octaves: {self.arp_octave_range}")

        elif self.arp_mode_active and cc == 79:
            # Master encoder: Adjust gate (10%-90%)
            new_gate = max(0.1, min(0.9, self.arp_gate + (delta * 0.05)))
            if new_gate != self.arp_gate:
                self.arp_gate = new_gate
                gate_pct = int(self.arp_gate * 100)
                self._show_lcd_popup("GATE", f"{gate_pct}%")
                print(f"Arp Gate: {gate_pct}%")

        # Device mode: CC 71-78 control device parameters (track-type-aware)
        elif self.current_mode == 'device' and 71 <= cc <= 78:
            encoder_index = cc - 71  # 0-7
            all_params = self._get_device_params()
            params = all_params[self.device_page]
            label, param_cc, default, fmt_func = params[encoder_index]

            if label and param_cc:  # Skip empty slots
                # Get current value from cache or default
                cache_key = (self.keyboard_track, param_cc)
                current_val = self.device_params.get(cache_key, default)

                # Use scaled delta for smoother control
                if value < 64:
                    val_delta = value
                else:
                    val_delta = value - 128

                # Calculate new value with limits
                new_val = max(0, min(127, current_val + val_delta))

                if new_val != current_val:
                    self.device_params[cache_key] = new_val

                    # Send CC to Seqtrak for current track
                    self.protocol.send_track_cc(self.keyboard_track, param_cc, new_val)
                    self.update_display()

                    # Format value for display
                    if fmt_func:
                        val_str = fmt_func(new_val)
                    else:
                        val_str = str(new_val)
                    print(f"{label}: {val_str}")

        # Mixer mode: CC 71-78 control track volumes (using MIXER_TRACK_ORDER)
        elif self.current_mode == 'mixer' and 71 <= cc <= 78:
            encoder_index = cc - 71  # 0-7
            mixer_pos = self.mixer_page * 8 + encoder_index  # 0-11

            if mixer_pos < len(MIXER_TRACK_ORDER):
                track = MIXER_TRACK_ORDER[mixer_pos]
                name = MIXER_DISPLAY_NAMES[mixer_pos]

                # Use actual encoder value for smoother volume control
                if value < 64:
                    vol_delta = value * 2
                else:
                    vol_delta = (value - 128) * 2

                if track is None:
                    # DRUM bus - adjust master drum level
                    self._adjust_drum_bus_volume(vol_delta)
                else:
                    # Regular track volume
                    new_vol = max(0, min(127, self.track_volumes[track - 1] + vol_delta))
                    if new_vol != self.track_volumes[track - 1]:
                        self.track_volumes[track - 1] = new_vol
                        self.protocol.set_track_volume(track, new_vol)
                        self.update_display()
                        vol_pct = round(new_vol * 100 / 127)
                        print(f"{name} Volume: {vol_pct}")

        # Track encoder (CC 71) - cycle through tracks (not in mixer mode)
        elif cc == 71:
            if self.current_mode == 'scale':
                # In scale mode, scroll scales
                self._scroll_scale(delta)
            else:
                # In other modes, cycle through tracks
                if delta > 0:
                    self._select_next_track()
                else:
                    self._select_prev_track()

        # Patch encoder (CC 73) - cycle through patches (with accumulator for slower response)
        # Shift+Encoder = jump by bank (128 presets) for faster navigation
        elif cc == 73:
            if self.shift_held:
                # Bank jumping: lower threshold, jump by 128
                self.patch_encoder_accum += delta
                if abs(self.patch_encoder_accum) >= 2:  # Lower threshold for bank jumps
                    bank_delta = 128 if self.patch_encoder_accum > 0 else -128
                    self._cycle_patch(bank_delta)
                    self.patch_encoder_accum = 0
            else:
                # Normal patch cycling
                self.patch_encoder_accum += delta
                if abs(self.patch_encoder_accum) >= self.patch_encoder_threshold:
                    patch_delta = 1 if self.patch_encoder_accum > 0 else -1
                    self._cycle_patch(patch_delta)
                    self.patch_encoder_accum = 0

        # Master volume encoder (CC 79)
        elif cc == 79:
            # Use actual encoder value for smoother volume control
            if value < 64:
                vol_delta = value * 2  # Clockwise, scale up for faster response
            else:
                vol_delta = (value - 128) * 2  # Counter-clockwise

            new_volume = max(0, min(127, self.master_volume + vol_delta))
            if new_volume != self.master_volume:
                self.master_volume = new_volume
                self.protocol.set_master_volume(self.master_volume)
                print(f"Master Volume: {self.master_volume}")

        # Bar length control (CC 75)
        elif cc == 75:
            self._adjust_bar_length(delta)

    def _adjust_bar_length(self, delta):
        """Adjust bar/loop length for current track.

        Uses SysEx to set the pattern step count on Seqtrak.
        Address: 30 5[part] 16 where part = track - 1 (0-10)
        Data: 2 bytes MSB/LSB, value = steps (16 per bar)

        Hardware limitation: Only supports powers of 2 (1, 2, 4, 8 bars).
        No support for 3, 5, 6, or 7 bars.
        """
        track = self.keyboard_track

        # Get current bar length
        current_bars = self.track_bar_length.get(track, 1)

        # Valid bar lengths (powers of 2 only)
        valid_bars = [1, 2, 4, 8]

        # Find current index in valid_bars
        try:
            current_index = valid_bars.index(current_bars)
        except ValueError:
            # If somehow we have an invalid value, reset to 1 bar
            current_index = 0
            current_bars = 1

        # Calculate new index
        new_index = current_index + delta

        # Wrap around (8 bars -> 1 bar, 1 bar -> 8 bars)
        new_index = new_index % len(valid_bars)

        new_bars = valid_bars[new_index]

        # If no change, don't send anything
        if new_bars == current_bars:
            return

        # Update local state
        self.track_bar_length[track] = new_bars

        # Address: 30 5[part] 16 where part = track - 1 (0-indexed)
        # Offset is 0x16 for melodic bar length (confirmed via MIDI capture)
        part = track - 1  # Convert 1-11 to 0-10
        addr = [0x30, 0x50 + part, 0x16]

        # Data: 2 bytes MSB/LSB, 16 steps per bar
        steps = new_bars * 16
        data = [steps >> 7, steps & 0x7F]

        self.protocol.send_parameter(addr, data)

        self.update_display()
        self._update_bar_length_buttons()
        print(f"  Bar Length: {new_bars} bar(s) ({steps} steps)")

    def _update_bar_length_buttons(self):
        """Update bar length button LEDs based on current bar count.

        Since bar length cycles through [1, 2, 4, 8] bars,
        both buttons are always active (no min/max boundaries).
        """
        # CC 24 (decrement) and CC 106 (increment) - always active for cycling
        self.set_button_led(24, LED_ON)   # Bar length down
        self.set_button_led(106, LED_ON)  # Bar length up

    def _adjust_variation(self, delta):
        """Adjust variation for current track.

        Uses SysEx to set the variation on Seqtrak.
        Address: 30 5[part] 0F where part = track - 1 (0-10)
        Data: 1 byte, variation (0-5 for variations 1-6)

        Respects current variation_mode (3 or 6 variations available).
        """
        track = self.keyboard_track

        # Get current variation
        current_var = self.track_variation.get(track, 1)

        # Calculate new variation with wraparound based on mode (3 or 6 variations)
        max_var = self.variation_mode
        new_var = ((current_var - 1 + delta) % max_var) + 1

        # Update local state
        self.track_variation[track] = new_var

        # Send SysEx to Seqtrak
        self.protocol.select_track_variation(track, new_var)

        self.update_display()
        print(f"  Variation: {new_var}/{max_var} for {Track.NAMES.get(track, f'Track {track}')}")

    def _toggle_variation_mode(self):
        """Toggle between 3 and 6 variation modes.

        Sends SysEx to Seqtrak to enable/disable 6 variation mode.
        Address: 01 10 18
        Data: 02 = enable 6 variations, 00 = 3 variations (default)
        """
        # Toggle between 3 and 6
        if self.variation_mode == 3:
            self.variation_mode = 6
            # Send SysEx to enable 6 variations
            self.protocol.send_parameter([0x01, 0x10, 0x18], [0x02])
            print("  Variation Mode: 6 variations enabled")
        else:
            self.variation_mode = 3
            # Send SysEx to disable 6 variations (back to 3)
            self.protocol.send_parameter([0x01, 0x10, 0x18], [0x00])
            print("  Variation Mode: 3 variations (default)")

        # Clamp current variations to new max
        for track in range(1, 12):
            if self.track_variation.get(track, 1) > self.variation_mode:
                self.track_variation[track] = self.variation_mode

        self.update_display()

    def _clear_subdivision_leds(self):
        """Turn off all subdivision button LEDs (CC 36-43)."""
        for cc in range(36, 44):
            self.set_button_led(cc, LED_OFF)

    def _light_subdivision_leds(self, selected_cc=None):
        """Light up subdivision button LEDs for note repeat mode."""
        for cc in range(36, 44):
            if cc == selected_cc:
                self.set_button_led(cc, LED_ON)
            else:
                self.set_button_led(cc, LED_DIM)

    def _process_note_repeat(self):
        """Process note repeats for held pads. Called from main loop."""
        if not self.note_repeat_active or self.note_repeat_rate is None:
            return

        if not self.note_repeat_notes:
            return

        current_time = time.time()

        # Calculate repeat interval based on tempo
        # beats_per_minute = self.tempo or 120
        # seconds_per_beat = 60.0 / beats_per_minute
        # interval = seconds_per_beat * self.note_repeat_rate
        bpm = self.tempo if self.tempo else 120
        seconds_per_beat = 60.0 / bpm
        interval = seconds_per_beat * self.note_repeat_rate

        # Check each held note
        for pad_note, (midi_note, track, last_trigger) in list(self.note_repeat_notes.items()):
            elapsed = current_time - last_trigger
            if elapsed >= interval:
                # Retrigger the note
                out_velocity = self.accent_velocity if self.accent_mode else 100
                self.protocol.trigger_note(track, midi_note, out_velocity)
                self.note_repeat_notes[pad_note] = (midi_note, track, current_time)

    # =========================================================================
    # ARPEGGIATOR - Software-based arpeggiator running in Python
    # =========================================================================

    def _get_arp_sequence(self, pattern, notes, octave_range):
        """
        Generate the note sequence for the current arpeggiator pattern.

        Args:
            pattern: Pattern name from ARP_PATTERNS
            notes: List of held MIDI notes (in press order for 'as_played')
            octave_range: 1-4 octaves to span

        Returns:
            List of MIDI notes in arp order, extended across octaves
        """
        import random

        if not notes:
            return []

        sorted_notes = sorted(notes)

        if pattern == 'up':
            base = sorted_notes
        elif pattern == 'down':
            base = sorted_notes[::-1]
        elif pattern == 'up_down':
            # Up then down, no repeat at ends
            if len(sorted_notes) > 1:
                base = sorted_notes + sorted_notes[-2:0:-1]
            else:
                base = sorted_notes
        elif pattern == 'down_up':
            # Down then up, no repeat at ends
            if len(sorted_notes) > 1:
                base = sorted_notes[::-1] + sorted_notes[1:-1]
            else:
                base = sorted_notes
        elif pattern == 'random':
            base = sorted_notes[:]
            random.shuffle(base)
        elif pattern == 'converge':
            # Outside notes move inward (low, high, low+1, high-1, ...)
            result = []
            left, right = 0, len(sorted_notes) - 1
            while left <= right:
                if left == right:
                    result.append(sorted_notes[left])
                else:
                    result.extend([sorted_notes[left], sorted_notes[right]])
                left += 1
                right -= 1
            base = result
        elif pattern == 'diverge':
            # Center notes move outward
            mid = len(sorted_notes) // 2
            result = []
            for i in range(mid + 1):
                if mid - i >= 0 and mid - i < len(sorted_notes):
                    result.append(sorted_notes[mid - i])
                if i > 0 and mid + i < len(sorted_notes):
                    result.append(sorted_notes[mid + i])
            base = result
        elif pattern == 'chord':
            # All notes at once - handled specially in _process_arpeggiator
            base = sorted_notes
        elif pattern == 'as_played':
            # Original press order preserved
            base = notes
        elif pattern == 'custom':
            # Future: user-defined order, for now same as 'up'
            base = sorted_notes
        else:
            base = sorted_notes

        # Extend across octaves
        full_sequence = []
        for octave in range(octave_range):
            for note in base:
                full_sequence.append(note + (12 * octave))

        return full_sequence

    def _rebuild_arp_sequence(self):
        """Rebuild the arp sequence when notes, pattern, or octaves change."""
        # Use latched notes if in latch mode and we have them, otherwise held notes
        if self.arp_latch and self.arp_latched_notes:
            notes = self.arp_latched_notes
        else:
            notes = self.arp_held_notes

        if not notes:
            self.arp_sequence = []
            self.arp_position = 0
            return

        self.arp_sequence = self._get_arp_sequence(
            self.arp_pattern,
            notes,
            self.arp_octave_range
        )

        # Reset position if sequence changed significantly
        if self.arp_position >= len(self.arp_sequence):
            self.arp_position = 0

    def _enter_arp_mode(self):
        """Enter arpeggiator mode, exiting note repeat if active."""
        if self.note_repeat_active:
            self._exit_note_repeat_mode()

        self.arp_mode_active = True
        self.arp_enabled = True
        self._light_arp_leds()
        self.set_button_led(BUTTONS['repeat'], LED_ON)
        self._show_lcd_popup("ARP", "Select rate")
        print("Arpeggiator: ON")

    def _exit_arp_mode(self):
        """Exit arpeggiator mode, release all notes."""
        self.arp_mode_active = False
        self.arp_enabled = False
        self.arp_rate = None
        self._release_all_arp_notes()
        self.arp_held_notes = []
        self.arp_latched_notes = []
        self.arp_sequence = []
        self.arp_position = 0
        self._clear_subdivision_leds()
        self.set_button_led(BUTTONS['repeat'], LED_DIM)
        print("Arpeggiator: OFF")

    def _enter_note_repeat_mode(self):
        """Enter note repeat mode (keep existing, but add popup)."""
        self.note_repeat_active = True
        self._light_subdivision_leds()
        self.set_button_led(BUTTONS['repeat'], LED_ON)
        self._show_lcd_popup("REPEAT", "Select rate")
        print("Note Repeat: ON")

    def _exit_note_repeat_mode(self):
        """Exit note repeat mode."""
        self.note_repeat_active = False
        self.note_repeat_rate = None
        self._clear_subdivision_leds()
        self.set_button_led(BUTTONS['repeat'], LED_DIM)
        print("Note Repeat: OFF")

    def _process_arpeggiator(self):
        """Process arpeggiator playback. Called from main loop."""
        if not self.arp_enabled or self.arp_rate is None:
            return

        if not self.arp_sequence:
            return

        current_time = time.time()

        # Calculate interval based on tempo and rate
        bpm = self.tempo if self.tempo else 120
        seconds_per_beat = 60.0 / bpm
        interval = seconds_per_beat * self.arp_rate
        gate_duration = interval * self.arp_gate

        # Check if it's time for the next note
        elapsed = current_time - self.arp_last_trigger_time
        if elapsed >= interval:
            # Release previous note (if any)
            if self.arp_last_note_played is not None:
                self.protocol.release_note(self.keyboard_track, self.arp_last_note_played)
                self.arp_last_note_played = None

            # Handle Chord pattern (all notes at once)
            if self.arp_pattern == 'chord':
                out_velocity = self.accent_velocity if self.accent_mode else 100
                # Get unique notes from sequence (remove octave duplicates for chord)
                unique_notes = list(set(self.arp_sequence))
                for note in unique_notes:
                    self.protocol.trigger_note(self.keyboard_track, note, out_velocity)
                # For chord, track all notes for release (use the first as marker)
                self.arp_last_note_played = unique_notes[0] if unique_notes else None
            else:
                # Single note patterns
                if self.arp_position < len(self.arp_sequence):
                    midi_note = self.arp_sequence[self.arp_position]
                    out_velocity = self.accent_velocity if self.accent_mode else 100
                    self.protocol.trigger_note(self.keyboard_track, midi_note, out_velocity)
                    self.arp_last_note_played = midi_note

                    # Advance position (with wrap)
                    self.arp_position = (self.arp_position + 1) % len(self.arp_sequence)

                    # For Random pattern, reshuffle when we complete a cycle
                    if self.arp_pattern == 'random' and self.arp_position == 0:
                        self._rebuild_arp_sequence()

            self.arp_last_trigger_time = current_time

    def _release_all_arp_notes(self):
        """Release any currently playing arp note."""
        if self.arp_last_note_played is not None:
            self.protocol.release_note(self.keyboard_track, self.arp_last_note_played)
            self.arp_last_note_played = None

        # For chord mode, release all notes in sequence
        if self.arp_pattern == 'chord' and self.arp_sequence:
            for note in set(self.arp_sequence):
                self.protocol.release_note(self.keyboard_track, note)

    def _light_arp_leds(self, selected_cc=None):
        """Light up subdivision buttons for arp mode (different brightness than repeat)."""
        ARP_LED_DIM = 2  # Different from note repeat's LED_DIM (1)
        for cc in range(36, 44):
            if cc == selected_cc:
                self.set_button_led(cc, LED_ON)
            else:
                self.set_button_led(cc, ARP_LED_DIM)

    def _clear_subdivision_leds(self):
        """Turn off all subdivision button LEDs."""
        for cc in range(36, 44):
            self.set_button_led(cc, LED_OFF)

    def _light_subdivision_leds(self, selected_cc=None):
        """Light up subdivision buttons for note repeat mode."""
        for cc in range(36, 44):
            if cc == selected_cc:
                self.set_button_led(cc, LED_ON)
            else:
                self.set_button_led(cc, LED_DIM)

    def _show_lcd_popup(self, title, value, duration=2.0):
        """Show a momentary LCD popup on line 4."""
        self.lcd_popup_active = True
        self.lcd_popup_end_time = time.time() + duration
        self.set_lcd_segments(4, "", f"{title}: {value}", "", "")

    def _check_lcd_popup(self):
        """Check if popup should be cleared. Called from main loop."""
        if self.lcd_popup_active and time.time() >= self.lcd_popup_end_time:
            self.lcd_popup_active = False
            self.update_display()  # Restore normal display

    def handle_pad(self, note, velocity):
        """Handle pad press/release - routes to mode-specific handler."""
        if note < 36 or note > 99:
            return

        # Mute mode always handles pads specially
        if self.current_mode == 'mute':
            self._handle_mute_pad(note, velocity)
            return

        # Session mode: handle variation selection
        if self.session_mode:
            if velocity > 0:  # Only on press
                row = (note - 36) // 8
                col = (note - 36) % 8
                self._handle_session_pad(row, col)
            return

        # Route based on pad mode
        if self.current_pad_mode == PadMode.DRUM:
            self._handle_drum_pad(note, velocity)
        elif self.current_pad_mode == PadMode.SAMPLER:
            self._handle_sampler_pad(note, velocity)
        else:
            self._handle_melodic_pad(note, velocity)

    def _handle_mute_pad(self, note, velocity):
        """Handle pad press in mute mode."""
        if velocity == 0:
            return

        row = (note - 36) // 8
        col = (note - 36) % 8

        if row == 0:
            track = col + 1
        elif row == 1 and col < 3:
            track = col + 9
        else:
            return

        if track <= 11:
            self._toggle_track_mute(track)

    def _handle_drum_pad(self, note, velocity):
        """Handle pad press in drum mode with split layout.

        Layout:
        - Rows 0-1 (bottom 2): Drum sound pads - trigger sounds, Shift+Pad to select
        - Rows 2-3 (middle): Empty
        - Rows 4-7 (top 4): Step sequencer - toggle steps on/off
        """
        row = (note - 36) // 8
        col = (note - 36) % 8
        pos = (row, col)

        # Check if it's a drum sound pad (bottom 2 rows)
        if row < 2:
            try:
                pad_index = DRUM_PAD_POSITIONS.index(pos)
            except ValueError:
                return  # Not a valid drum pad position

            track = DRUM_PAD_TRACKS[pad_index]
            midi_note = DRUM_PAD_NOTES[pad_index]

            if velocity == 0:
                # Note off
                if note in self.active_notes:
                    self.active_notes.pop(note)
                    self.protocol.release_note(track, midi_note)

                    # Remove from note repeat tracking
                    if note in self.note_repeat_notes:
                        del self.note_repeat_notes[note]

                    # Restore color based on selection
                    if track == self.selected_drum_track:
                        self.set_pad_color(note, SAMPLER_SELECTED_COLOR)
                    else:
                        self.set_pad_color(note, DRUM_TRACK_COLORS.get(track, COLOR_DIM))
                return

            # Note on
            if self.shift_held:
                # Shift+Pad = select this drum track for step sequencer
                old_selected = self.selected_drum_track
                self.selected_drum_track = track

                # Update visual feedback for old and new selection
                self.update_grid()
                self.update_display()

                track_name = Track.NAMES.get(track, f"T{track}")
                print(f"  Selected drum track: {track_name}")
            else:
                # Normal press = trigger drum sound
                # Apply accent velocity if accent mode is active
                out_velocity = self.accent_velocity if self.accent_mode else velocity
                self.protocol.trigger_note(track, midi_note, out_velocity)
                self.active_notes[note] = midi_note

                # Register for note repeat if active
                if self.note_repeat_active and self.note_repeat_rate is not None:
                    self.note_repeat_notes[note] = (midi_note, track, time.time())

                # Flash pad green
                self.set_pad_color(note, COLOR_GREEN)

                track_name = Track.NAMES.get(track, f"T{track}")
                print(f"[D] {track_name} note {midi_note}")

        # Check if it's a step sequencer pad (top 4 rows)
        elif row >= 4:
            if velocity > 0:  # Only on press, not release
                # Calculate step index: top row first (row 7 = steps 0-7)
                step_index = ((7 - row) * 8) + col + (self.step_page * 32)

                if step_index < 128:
                    self._toggle_step(self.selected_drum_track, step_index)

        # Middle rows (2-3) are empty - ignore

    def _toggle_step(self, track, step_index):
        """Toggle a step in the drum sequencer.

        Args:
            track: Drum track number (1-7)
            step_index: Step index (0-127)

        SysEx formats (from MIDI capture):
            Add step:    F0 43 10 7F 1C 0C 70 [track-1] 00 [step] [note] [vel] [gate] [prob] F7
            Delete step: F0 43 10 7F 1C 0C 70 [0x20+track-1] 00 [step] F7

        Where:
            - Add address: 70 [track-1] 00
            - Delete address: 70 [0x20 + track-1] 00
            - step: Step index (0-127)
            - note: MIDI note (0x3C = C4 for drums)
            - vel: Velocity (0x64 = 100)
            - gate: Gate/length (0x00)
            - prob: Probability (0x78 = 120)
        """
        # Initialize step states for this track if not present
        if track not in self.step_states:
            self.step_states[track] = [False] * 128

        # Toggle local state
        self.step_states[track][step_index] = not self.step_states[track][step_index]
        new_state = self.step_states[track][step_index]

        # Track index (0-indexed for SysEx)
        track_idx = track - 1

        if new_state:
            # Add step: address 70 [track-1] 00
            addr = [0x70, track_idx, 0x00]
            note = 0x3C  # C4 = 60 for all drum tracks
            data = [step_index, note, 0x64, 0x00, 0x78]  # step, note, vel, gate, prob
        else:
            # Delete step: address 70 [0x20 + track-1] 00
            addr = [0x70, 0x20 + track_idx, 0x00]
            data = [step_index]

        self.protocol.send_parameter(addr, data)

        # Update grid to show new state
        self.update_grid()

        track_name = Track.NAMES.get(track, f"T{track}")
        step_num = step_index + 1
        state_str = "ON" if new_state else "OFF"
        print(f"  Step {step_num} for {track_name}: {state_str}")

    def _toggle_sampler_step(self, pad_index, step_index):
        """Toggle a step in the sampler sequencer.

        Args:
            pad_index: Sample pad index (0-6)
            step_index: Step index (0-127)

        SysEx format (verified from capture):
            Both ADD and DELETE use the full 8-byte payload with 14-bit tick position.
            
            Payload: [tick_hi] [tick_lo] 00 [note] [vel] 00 00 [prob]
            - tick: 14-bit value, 120 ticks per step (480 PPQN)
            - note: 0x3C (60) + pad_index
            - vel: 0x64 (100)
            - prob: 0x78 (120)

            Add Address:    72 30 00
            Delete Address: 74 73 00
        """
        # Initialize step states for this pad if not present
        if pad_index not in self.sampler_step_states:
            self.sampler_step_states[pad_index] = [False] * 128

        # Toggle local state
        self.sampler_step_states[pad_index][step_index] = not self.sampler_step_states[pad_index][step_index]
        new_state = self.sampler_step_states[pad_index][step_index]

        # Note: Do NOT send _sync_sampler_element here. 
        # The logs show that sending the select command (01 10 28) is not required 
        # and likely interferes with the step command flow.

        # Calculate 14-bit tick position (16th notes @ 480 PPQN = 120 ticks)
        ticks = step_index * 120
        tick_hi = (ticks >> 7) & 0x7F
        tick_lo = ticks & 0x7F

        # Sample note is pad-specific (C4 + pad index).
        sample_note = 0x3C + pad_index

        # Construct full data payload (used for BOTH add and delete)
        # [tick_hi, tick_lo, 00, note, vel, 00, 00, prob]
        data = [tick_hi, tick_lo, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]

        if new_state:
            # Add step: 72 30 00
            addr = [0x72, 0x30, 0x00]
        else:
            # Delete step: 74 73 00
            addr = [0x74, 0x73, 0x00]

        self.protocol.send_parameter(addr, data)

        # Update grid to show new state
        self.update_grid()

        step_num = step_index + 1
        state_str = "ON" if new_state else "OFF"
        print(f"  Sampler Step {step_num} for Pad {pad_index + 1}: {state_str}")

    def _sync_sampler_element(self, element):
        """Tell Seqtrak which sampler element (pad) is active for edits/recording."""
        if self.protocol:
            self.protocol.select_sampler_element(element)

    def _handle_melodic_pad(self, note, velocity):
        """Handle pad press in melodic mode (isomorphic keyboard)."""
        row = (note - 36) // 8
        col = (note - 36) % 8

        if velocity == 0:
            # Note off
            if note in self.active_notes:
                midi_note = self.active_notes.pop(note)

                # Handle arpeggiator note release
                if self.arp_enabled:
                    if midi_note in self.arp_held_notes:
                        self.arp_held_notes.remove(midi_note)

                        # Latch mode: when all pads released, latch the current notes
                        if self.arp_latch and not self.arp_held_notes and self.arp_sequence:
                            # Preserve the base notes (without octave extension)
                            base_notes = [n for n in self.arp_sequence if n < 128]
                            # Remove duplicates while preserving order
                            seen = set()
                            unique_notes = []
                            for n in base_notes:
                                base_n = n % 12 + (n // 12) * 12  # normalize
                                if base_n not in seen:
                                    seen.add(base_n)
                                    unique_notes.append(n)
                            if unique_notes:
                                self.arp_latched_notes = unique_notes[:len(set(self.arp_sequence))]

                        if not self.arp_latch:
                            self._rebuild_arp_sequence()
                else:
                    # Normal release (no arp)
                    self.protocol.release_note(self.keyboard_track, midi_note)

                # Remove from note repeat tracking
                if note in self.note_repeat_notes:
                    del self.note_repeat_notes[note]

                # Restore pad color based on scale
                info = self.layout.get_pad_info(row, col)
                if info['is_root']:
                    color = COLOR_BLUE
                elif info['is_in_scale']:
                    color = COLOR_WHITE
                else:
                    color = COLOR_OFF if self.in_key_mode else COLOR_DIM
                self.set_pad_color(note, color)
            return

        # Note on - use isomorphic layout
        midi_note = self.layout.get_midi_note(note)

        # Handle arpeggiator note input
        if self.arp_enabled:
            if midi_note not in self.arp_held_notes:
                self.arp_held_notes.append(midi_note)  # Preserve order for 'as_played'
                self._rebuild_arp_sequence()

                # If latch mode and we're adding new notes, clear latched notes
                if self.arp_latch and self.arp_latched_notes:
                    self.arp_latched_notes = []

            self.active_notes[note] = midi_note
            # Flash pad green
            self.set_pad_color(note, COLOR_GREEN)
            track_name = Track.NAMES.get(self.keyboard_track, f"T{self.keyboard_track}")
            print(f"[ARP] +{midi_note} → {track_name}")
            return

        # Normal note trigger (no arp)
        # Apply accent velocity if accent mode is active
        out_velocity = self.accent_velocity if self.accent_mode else velocity

        # Send to Seqtrak
        self.protocol.trigger_note(self.keyboard_track, midi_note, out_velocity)
        self.active_notes[note] = midi_note

        # Register for note repeat if active
        if self.note_repeat_active and self.note_repeat_rate is not None:
            self.note_repeat_notes[note] = (midi_note, self.keyboard_track, time.time())

        # Flash pad green
        self.set_pad_color(note, COLOR_GREEN)

        track_name = Track.NAMES.get(self.keyboard_track, f"T{self.keyboard_track}")
        print(f"[M] {midi_note} → {track_name}")

    def _get_sampler_element_for_pad(self, pad_note):
        """Get sampler element index (0-6) for a pad, or None if not a sampler pad."""
        row = (pad_note - 36) // 8
        col = (pad_note - 36) % 8
        pos = (row, col)

        try:
            return SAMPLER_PAD_POSITIONS.index(pos)
        except ValueError:
            return None

    def _handle_sampler_pad(self, note, velocity):
        """Handle pad press in sampler mode with split layout.

        Layout:
        - Rows 0-1 (bottom 2): Sample pads - trigger sounds, Shift+Pad to select
        - Rows 2-3 (middle): Empty
        - Rows 4-7 (top 4): Step sequencer - toggle steps on/off

        Sampler triggering on Seqtrak:
        - All 7 samples trigger on MIDI channel 11 (0-indexed: 10)
        - Notes: C4 (60) through F#4 (66) - one note per sample slot
        """
        row = (note - 36) // 8
        col = (note - 36) % 8

        # Check if it's a step sequencer pad (top 4 rows)
        if row >= 4:
            if velocity > 0:  # Only on press, not release
                # Calculate step index: top row first (row 7 = steps 0-7)
                step_index = ((7 - row) * 8) + col + (self.step_page * 32)

                if step_index < 128:
                    self._toggle_sampler_step(self.selected_sampler_pad, step_index)
            return

        # Check if it's a sample pad (bottom 2 rows)
        element = self._get_sampler_element_for_pad(note)

        if element is None:
            # Not a sampler pad (middle rows) - ignore
            return

        # Sampler uses channel 11 (0-indexed: 10) for all sample triggering
        sampler_channel = 10  # Channel 11 in MIDI terms

        # Notes 60-66 (C4 through F#4) for samples 0-6
        midi_note = 60 + element

        if velocity == 0:
            # Note off
            if note in self.active_notes:
                self.active_notes.pop(note)
                self.seqtrak.send(mido.Message('note_off', channel=sampler_channel, note=midi_note, velocity=0))

                # Remove from note repeat tracking
                if note in self.note_repeat_notes:
                    del self.note_repeat_notes[note]

                # Restore pad color
                if element == self.selected_sampler_pad:
                    self.set_pad_color(note, SAMPLER_SELECTED_COLOR)
                else:
                    self.set_pad_color(note, SAMPLER_PAD_COLORS[element])
            return

        # Note on
        if self.shift_held:
            # Shift+Pad = select this pad for editing (don't trigger sound)
            old_selected = self.selected_sampler_pad
            self.selected_sampler_pad = element

            # Update visual feedback
            old_row, old_col = SAMPLER_PAD_POSITIONS[old_selected]
            old_note = 36 + (old_row * 8) + old_col
            self.set_pad_color(old_note, SAMPLER_PAD_COLORS[old_selected])
            self.set_pad_color(note, SAMPLER_SELECTED_COLOR)

            self._sync_sampler_element(self.selected_sampler_pad)
            print(f"  Selected sampler pad {element + 1}")
            self.update_display()
        else:
            # Normal press = trigger sample on channel 11
            # Apply accent velocity if accent mode is active
            out_velocity = self.accent_velocity if self.accent_mode else velocity
            self.seqtrak.send(mido.Message('note_on', channel=sampler_channel, note=midi_note, velocity=out_velocity))
            self.active_notes[note] = midi_note

            # Register for note repeat if active (use track 11 for sampler)
            if self.note_repeat_active and self.note_repeat_rate is not None:
                self.note_repeat_notes[note] = (midi_note, 11, time.time())

            # Flash green
            self.set_pad_color(note, COLOR_GREEN)

            pad_info = self.sampler_pad_presets[element]
            preset_name = get_preset_name_short(11, pad_info['bank_msb'], pad_info['bank_lsb'], pad_info['program'])
            print(f"[S] Pad{element + 1} (note {midi_note}): {preset_name}")

    def _toggle_track_mute(self, track):
        """Toggle track mute state: unmuted → muted → solo → unmuted."""
        current = self.track_states[track - 1]
        track_name = Track.NAMES.get(track, f"Track {track}")

        if current == MuteState.UNMUTED:
            new_state = MuteState.MUTED
            self.protocol.mute_track_cc(track, muted=True)
        elif current == MuteState.MUTED:
            new_state = MuteState.SOLO
            self.protocol.mute_track_cc(track, muted=False)
            self.protocol.solo_track_cc(track)
        else:
            new_state = MuteState.UNMUTED
            self.protocol.solo_track_cc(0)
            self.protocol.mute_track_cc(track, muted=False)

        self.track_states[track - 1] = new_state
        self.update_grid()
        print(f"{track_name}: {['UNMUTED', 'MUTED', 'SOLO'][new_state]}")

    def _toggle_track_mute_simple(self, track):
        """Toggle track mute state (simple: unmuted ↔ muted, clears solo)."""
        current = self.track_states[track - 1]
        track_name = MIXER_TRACK_ABBREV.get(track, f"T{track}")

        if current == MuteState.MUTED:
            # Unmute
            new_state = MuteState.UNMUTED
            self.protocol.mute_track_cc(track, muted=False)
        else:
            # Mute (also clears solo)
            new_state = MuteState.MUTED
            if current == MuteState.SOLO:
                self.protocol.solo_track_cc(0)  # Clear solo first
            self.protocol.mute_track_cc(track, muted=True)

        self.track_states[track - 1] = new_state
        self._update_mixer_button_leds()
        print(f"{track_name}: {'MUTED' if new_state == MuteState.MUTED else 'UNMUTED'}")

    def _toggle_track_solo(self, track):
        """Toggle track solo state (clears mute if setting solo)."""
        current = self.track_states[track - 1]
        track_name = MIXER_TRACK_ABBREV.get(track, f"T{track}")

        if current == MuteState.SOLO:
            # Unsolo
            new_state = MuteState.UNMUTED
            self.protocol.solo_track_cc(0)
        else:
            # Solo (clears mute)
            new_state = MuteState.SOLO
            if current == MuteState.MUTED:
                self.protocol.mute_track_cc(track, muted=False)
            self.protocol.solo_track_cc(track)

        self.track_states[track - 1] = new_state
        self._update_mixer_button_leds()
        print(f"{track_name}: {'SOLO' if new_state == MuteState.SOLO else 'UNMUTED'}")

    def _adjust_drum_bus_volume(self, delta):
        """Adjust master drum level, scaling all drum track volumes.

        The DRUM bus acts as a master fader for all drum tracks (1-7).
        When adjusted, it updates the drum_bus_volume and sends volume
        commands to all drum tracks scaled proportionally.
        """
        new_vol = max(0, min(127, self.drum_bus_volume + delta))
        if new_vol == self.drum_bus_volume:
            return

        self.drum_bus_volume = new_vol

        # Scale all drum track volumes based on bus level
        scale = self.drum_bus_volume / 127.0
        for track in DRUM_BUS_TRACKS:
            scaled_vol = int(self.track_volumes[track - 1] * scale)
            self.protocol.set_track_volume(track, scaled_vol)

        self.update_display()
        vol_pct = round(new_vol * 100 / 127)
        print(f"DRUM Bus Volume: {vol_pct}")

    def _toggle_drum_bus_mute(self):
        """Mute/unmute all drum tracks together."""
        self.drum_bus_muted = not self.drum_bus_muted

        for track in DRUM_BUS_TRACKS:
            if self.drum_bus_muted:
                self.protocol.mute_track_cc(track, muted=True)
                self.track_states[track - 1] = MuteState.MUTED
            else:
                self.protocol.mute_track_cc(track, muted=False)
                self.track_states[track - 1] = MuteState.UNMUTED

        # Clear solo if we're unmuting
        if not self.drum_bus_muted:
            self.drum_bus_soloed = False

        self._update_mixer_button_leds()
        print(f"DRUM Bus: {'MUTED' if self.drum_bus_muted else 'UNMUTED'}")

    def _toggle_drum_bus_solo(self):
        """Solo/unsolo all drum tracks together."""
        self.drum_bus_soloed = not self.drum_bus_soloed

        if self.drum_bus_soloed:
            # Solo all drum tracks (clear mute first)
            self.drum_bus_muted = False
            for track in DRUM_BUS_TRACKS:
                self.protocol.mute_track_cc(track, muted=False)
                self.protocol.solo_track_cc(track)
                self.track_states[track - 1] = MuteState.SOLO
        else:
            # Unsolo all drum tracks
            for track in DRUM_BUS_TRACKS:
                self.protocol.solo_track_cc(0)
                self.track_states[track - 1] = MuteState.UNMUTED

        self._update_mixer_button_leds()
        print(f"DRUM Bus: {'SOLO' if self.drum_bus_soloed else 'UNMUTED'}")

    def _update_mixer_button_leds(self):
        """Update button LEDs for mixer mode mute/solo states.

        Uses MIXER_TRACK_ORDER for display order. Handles DRUM bus specially.
        """
        base_pos = self.mixer_page * 8  # 0 or 8

        for i in range(8):
            mixer_pos = base_pos + i
            upper_cc = 20 + i   # Solo buttons
            lower_cc = 102 + i  # Mute buttons

            if mixer_pos < len(MIXER_TRACK_ORDER):
                track = MIXER_TRACK_ORDER[mixer_pos]

                if track is None:
                    # DRUM bus - use bus state
                    self.set_button_led(upper_cc, LED_ON if self.drum_bus_soloed else LED_DIM)
                    self.set_button_led(lower_cc, LED_ON if self.drum_bus_muted else LED_DIM)
                else:
                    # Regular track
                    state = self.track_states[track - 1]
                    self.set_button_led(upper_cc, LED_ON if state == MuteState.SOLO else LED_DIM)
                    self.set_button_led(lower_cc, LED_ON if state == MuteState.MUTED else LED_DIM)
            else:
                # No track for this button position (page 2, buttons 5-8)
                self.set_button_led(upper_cc, LED_OFF)
                self.set_button_led(lower_cc, LED_OFF)

    def _get_track_preset_display(self, track):
        """Get preset display string for a track from stored bank/program."""
        bank = self.track_bank_msb[track]
        sub = self.track_bank_lsb[track]
        prog = self.track_program[track]
        if bank or sub or prog:
            return get_preset_name_short(track, bank, sub, prog)
        return ""

    def _get_device_params(self):
        """Get parameter pages for current keyboard track type."""
        track_type = get_track_type(self.keyboard_track)
        return DEVICE_PARAMS.get(track_type, DEVICE_PARAMS['drum'])

    def _get_device_max_pages(self):
        """Get max page count for current track type."""
        return len(self._get_device_params())

    def _update_pad_mode(self):
        """Update pad mode based on current keyboard track type."""
        track_type = get_track_type(self.keyboard_track)
        new_mode = TRACK_TYPE_TO_PAD_MODE.get(track_type, PadMode.MELODIC)

        if new_mode != self.current_pad_mode:
            self.current_pad_mode = new_mode
            print(f"  Pad Mode: {new_mode}")

            # Reset sampler selection and step page when entering sampler mode
            if new_mode == PadMode.SAMPLER:
                self.selected_sampler_pad = 0
                self.step_page = 0
                self._sync_sampler_element(self.selected_sampler_pad)

            # Reset step page and selected drum track when entering drum mode
            if new_mode == PadMode.DRUM:
                self.step_page = 0
                # Select the current keyboard track if it's a drum track (1-7)
                if 1 <= self.keyboard_track <= 7:
                    self.selected_drum_track = self.keyboard_track

        # Reset device page if it exceeds max for new track type
        max_device_pages = self._get_device_max_pages()
        if self.device_page >= max_device_pages:
            self.device_page = max_device_pages - 1

        # Update page button LEDs based on mode
        if self.current_pad_mode in (PadMode.DRUM, PadMode.SAMPLER):
            # Light up page buttons for step sequencer navigation
            self.set_button_led(BUTTONS['page_left'], LED_DIM if self.step_page == 0 else LED_ON)
            self.set_button_led(BUTTONS['page_right'], LED_DIM if self.step_page >= 3 else LED_ON)
        else:
            # Turn off page buttons for non-step-sequencer modes
            self.set_button_led(BUTTONS['page_left'], LED_OFF)
            self.set_button_led(BUTTONS['page_right'], LED_OFF)

        # Update bar length button LEDs for new track
        self._update_bar_length_buttons()

        # Always update grid and display for track changes
        self.update_grid()
        self.update_display()

    def _cycle_patch(self, delta):
        """Cycle through patches for the current track, respecting preset range limits."""
        track = self.keyboard_track
        track_type = get_track_type(track)

        # Sampler mode: cycle preset for selected pad only
        if track_type == 'sampler':
            self._cycle_sampler_pad_preset(delta)
            return

        # Non-sampler tracks: cycle preset for the whole track
        bank_msb = self.track_bank_msb[track]
        bank_lsb = self.track_bank_lsb[track]
        program = self.track_program[track]

        # Get current preset number and track type range
        current_preset = bank_program_to_preset(bank_lsb, program)

        if track_type and track_type in PRESET_RANGES:
            min_preset, max_preset = PRESET_RANGES[track_type]
        else:
            # Fallback: allow all presets
            min_preset, max_preset = 1, 2032

        # Calculate new preset, clamping to range (no wrap)
        new_preset = current_preset + delta
        new_preset = max(min_preset, min(max_preset, new_preset))

        # If no change (at boundary), don't send anything
        if new_preset == current_preset:
            return

        # Convert back to bank_lsb and program
        new_lsb, new_prog = preset_to_bank_program(new_preset)

        # Send Bank Select + Program Change to Seqtrak
        channel = track - 1  # Convert to 0-indexed MIDI channel
        self.seqtrak.send(mido.Message('control_change', channel=channel, control=0, value=bank_msb))
        self.seqtrak.send(mido.Message('control_change', channel=channel, control=32, value=new_lsb))
        self.seqtrak.send(mido.Message('program_change', channel=channel, program=new_prog))

        # Update local state
        self.track_bank_lsb[track] = new_lsb
        self.track_program[track] = new_prog
        self.patch_name = get_preset_name_short(track, bank_msb, new_lsb, new_prog)
        self.update_display()
        print(f"  Patch: {self.patch_name}")

    def _cycle_sampler_pad_preset(self, delta):
        """Cycle preset for the currently selected sampler pad."""
        pad_info = self.sampler_pad_presets[self.selected_sampler_pad]

        # Calculate current preset number
        current_preset = bank_program_to_preset(pad_info['bank_lsb'], pad_info['program'])

        # Sampler preset range
        min_preset, max_preset = PRESET_RANGES['sampler']

        # Calculate new preset, clamping to range (no wrap)
        new_preset = current_preset + delta
        new_preset = max(min_preset, min(max_preset, new_preset))

        # If no change (at boundary), don't send anything
        if new_preset == current_preset:
            return

        # Convert back to bank_lsb and program
        new_lsb, new_prog = preset_to_bank_program(new_preset)

        # Send Bank Select + Program Change on element's channel
        # Sampler elements use channels 0-6 for elements 0-6
        channel = self.selected_sampler_pad
        bank_msb = 62  # Sampler always uses bank MSB 62

        self.seqtrak.send(mido.Message('control_change', channel=channel, control=0, value=bank_msb))
        self.seqtrak.send(mido.Message('control_change', channel=channel, control=32, value=new_lsb))
        self.seqtrak.send(mido.Message('program_change', channel=channel, program=new_prog))

        # Update local state for this pad
        pad_info['bank_lsb'] = new_lsb
        pad_info['program'] = new_prog
        pad_info['preset_num'] = new_preset

        # Update display to show selected pad's preset
        preset_name = get_preset_name_short(11, bank_msb, new_lsb, new_prog)
        self.patch_name = f"P{self.selected_sampler_pad + 1}:{preset_name}"
        self.update_display()
        print(f"  Sampler Pad {self.selected_sampler_pad + 1}: {preset_name}")

    def _select_prev_track(self):
        """Select previous track (wraps around)."""
        if self.keyboard_track > 1:
            self.keyboard_track -= 1
        else:
            self.keyboard_track = 11  # Wrap to last track

        # Get stored preset info for this track
        self.patch_name = self._get_track_preset_display(self.keyboard_track)

        # Inform Seqtrak of track selection and request current preset
        self.protocol.select_track(self.keyboard_track)
        self.protocol.request_parameter(Address.PRESET_NAME)

        track_name = Track.NAMES.get(self.keyboard_track, f"T{self.keyboard_track}")
        print(f"<< Track: {track_name}")

        # Update pad mode (also updates grid and display)
        self._update_pad_mode()

    def _select_next_track(self):
        """Select next track (wraps around)."""
        if self.keyboard_track < 11:
            self.keyboard_track += 1
        else:
            self.keyboard_track = 1  # Wrap to first track

        # Get stored preset info for this track
        self.patch_name = self._get_track_preset_display(self.keyboard_track)

        # Inform Seqtrak of track selection and request current preset
        self.protocol.select_track(self.keyboard_track)
        self.protocol.request_parameter(Address.PRESET_NAME)

        track_name = Track.NAMES.get(self.keyboard_track, f"T{self.keyboard_track}")
        print(f"Track: {track_name} >>")

        # Update pad mode (also updates grid and display)
        self._update_pad_mode()

    # -------------------------------------------------------------------------
    # Main Loop
    # -------------------------------------------------------------------------

    def run(self):
        """Main entry point."""
        print("=" * 60)
        print("  OPENPUSH SEQTRAK BRIDGE")
        print("=" * 60)
        print()

        # Find ports
        print("Searching for MIDI ports...")
        push_in_name, push_out_name = self.find_push_ports()
        seqtrak_name = find_seqtrak_port()

        if not push_out_name:
            print("\nERROR: Could not find Ableton Push!")
            print("\nAvailable MIDI outputs:")
            for name in mido.get_output_names():
                print(f"  - {name}")
            return

        if not seqtrak_name:
            print("\nERROR: Could not find Seqtrak!")
            print("\nAvailable MIDI outputs:")
            for name in mido.get_output_names():
                print(f"  - {name}")
            return

        # Find Seqtrak input port (for receiving SysEx feedback)
        seqtrak_in_name = None
        for name in mido.get_input_names():
            if 'SEQTRAK' in name.upper():
                seqtrak_in_name = name
                break

        print(f"  Push Input:  {push_in_name}")
        print(f"  Push Output: {push_out_name}")
        print(f"  Seqtrak Out: {seqtrak_name}")
        print(f"  Seqtrak In:  {seqtrak_in_name or 'Not found'}")
        print()

        # Open ports
        with mido.open_output(push_out_name) as push_out, \
             mido.open_output(seqtrak_name) as seqtrak_out, \
             mido.open_input(push_in_name) as push_in:

            self.push_out = push_out
            self.push_in = push_in
            self.seqtrak = seqtrak_out
            self.protocol = SeqtrakProtocol(seqtrak_out)

            # Open Seqtrak input if available
            seqtrak_in = None
            if seqtrak_in_name:
                seqtrak_in = mido.open_input(seqtrak_in_name)
                self.seqtrak_in = seqtrak_in

            # Initialize Push
            print("Initializing Push...")
            self.send_sysex(USER_MODE)
            time.sleep(0.1)

            # Show welcome screen briefly
            self.clear_all_pads()
            self.update_display()  # Shows welcome screen (current_mode = 'welcome')
            self.update_grid()
            self.update_transport_leds()

            # Light up all mode buttons as dim initially
            self.set_button_led(BUTTONS['track'], LED_DIM)
            self.set_button_led(BUTTONS['device'], LED_DIM)
            self.set_button_led(BUTTONS['volume'], LED_DIM)
            self.set_button_led(BUTTONS['note'], LED_DIM)
            self.set_button_led(BUTTONS['scale'], LED_DIM)
            self.set_button_led(BUTTONS['tap_tempo'], LED_ON)  # Tap tempo always available
            self.set_button_led(BUTTONS['octave_up'], LED_DIM)
            self.set_button_led(BUTTONS['octave_down'], LED_DIM)

            print()
            print("=" * 60)
            print("  READY!")
            print("=" * 60)
            print()
            print("Controls:")
            print("  Play         - Play/Stop toggle")
            print("  Record       - Record arm")
            print("  Track/Device/Volume - Switch modes")
            print("  Pads         - Isomorphic keyboard")
            print("  Scale button - Scale/root selection")
            print("  Oct Up/Down  - Shift octave")
            print("  Tempo knob   - Adjust BPM")
            print("  Patch knob   - Cycle patches (Shift+Knob = jump bank)")
            print("  Tap Tempo    - Tap tempo")
            print()
            print("Press Ctrl+C to exit")
            print()

            # Transition from welcome to track mode
            time.sleep(0.5)
            self._set_mode('track')

            # Select initial track and set initial patch name
            self.protocol.select_track(self.keyboard_track)
            self.patch_name = self._get_track_preset_display(self.keyboard_track)
            self.update_display()

            # Request current state from Seqtrak
            self.protocol.request_parameter(Address.PRESET_NAME)
            self.protocol.request_parameter(Address.TEMPO)

            # Main loop - poll both Push and Seqtrak inputs
            self.running = True
            try:
                while self.running:
                    # Poll Push input (non-blocking)
                    for msg in push_in.iter_pending():
                        if msg.type == 'control_change':
                            # Encoders (CC 14-15 for tempo/swing, CC 71-79 for track encoders)
                            if msg.control in (14, 15) or msg.control in range(71, 80):
                                self.handle_encoder(msg.control, msg.value)
                            else:
                                self.handle_button(msg.control, msg.value)
                        elif msg.type == 'note_on':
                            if 36 <= msg.note <= 99:
                                self.handle_pad(msg.note, msg.velocity)
                        elif msg.type == 'note_off':
                            if 36 <= msg.note <= 99:
                                self.handle_pad(msg.note, 0)

                    # Poll Seqtrak input for feedback (non-blocking)
                    if seqtrak_in:
                        for msg in seqtrak_in.iter_pending():
                            self.handle_seqtrak_message(msg)

                    # Process note repeat for held pads
                    self._process_note_repeat()

                    # Process arpeggiator
                    self._process_arpeggiator()

                    # Check LCD popup timeout
                    self._check_lcd_popup()

                    # Small sleep to avoid busy-waiting
                    time.sleep(0.001)

            except KeyboardInterrupt:
                print("\n\nExiting...")

            # Cleanup
            print("Cleaning up...")
            self.protocol.stop()
            self.clear_all_pads()
            for line in range(1, 5):
                self.set_lcd_segments(line)
            for cc in BUTTONS.values():
                self.set_button_led(cc, LED_OFF)

            # Close Seqtrak input port
            if seqtrak_in:
                seqtrak_in.close()

        print("Done!")


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    bridge = SeqtrakBridge()
    bridge.run()


if __name__ == "__main__":
    main()
