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
PLAYHEAD_COLOR = COLOR_WHITE      # Playhead on an empty step
PLAYHEAD_COLOR_HIT = COLOR_YELLOW # Playhead on a set step

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

def sysex_address_for_cc(track, cc):
    """The SysEx parameter a Sound Design CC sets, so the Push can read the real value.

    From the SEQTRAK app click-through (APP-CLICKTHROUGH-P1.md) and the Data List; the CC and
    SysEx values share one scale for these (e.g. pitch 40-88 = 0x28-0x58, 0x40 = centre).
    Not listed (no known 1:1 SysEx value): filter cutoff/resonance (one combined LPF/HPF value
    in SysEx), synth/sampler decay, arp type/gate/speed, the FM macros.
    """
    p = track - 1
    kind = get_track_type(track)
    table = {
        7: [0x30, 0x50 + p, 0x00],    # volume
        10: [0x30, 0x50 + p, 0x01],   # pan
        91: [0x31, 0x10 + p, 0x19],   # reverb send
        94: [0x31, 0x10 + p, 0x1A],   # delay send
        20: [0x31, 0x10 + p, 0x4D],   # EQ high gain
        21: [0x31, 0x10 + p, 0x48],   # EQ low gain
    }
    if kind == 'drum':
        table.update({25: [0x31, 0x10 + p, 0x1C],   # pitch (note shift)
                      73: [0x31, 0x10 + p, 0x2C],   # attack
                      75: [0x31, 0x10 + p, 0x2D]})  # decay
    elif kind in ('synth', 'dx'):
        table.update({26: [0x31, 0x10 + p, 0x23],   # mono / poly / chord
                      5: [0x31, 0x10 + p, 0x1F],    # portamento time
                      65: [0x31, 0x10 + p, 0x1E]})  # portamento switch
        # attack: SYNTH 31 1p 2C; DX's amp envelope is the carrier offset 31 19 01
        table[73] = [0x31, 0x10 + p, 0x01 if kind == 'dx' else 0x2C]
    return table.get(cc)


# Value ranges of the Sound Design CCs that aren't 0-127 (user guide §18.3.1)
CC_RANGES = {
    10: (1, 127),   # pan
    20: (40, 88),   # EQ high gain
    21: (40, 88),   # EQ low gain
    25: (40, 88),   # drum pitch
    26: (0, 2),     # mono / poly / chord
    27: (0, 16),    # arp type (0 = off)
    29: (0, 9),     # arp speed
    65: (0, 1),     # portamento switch
}

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
    'shift': 49,
    'select': 48,
    'delete': 118,  # Hold for the delete menu
    'undo': 119,    # Seqtrak UNDO/REDO (sound and effect parameters)
    'double_loop': 117,  # double the selected track's pattern length
    'duplicate': 88,     # hold: copy a pattern to another pattern (Track / Drums / All)
    'user': 59,     # Shift+User = settings menu

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
        self.delete_held = False  # SELECT button held (acts as DELETE)
        self.track_select_overlay = False  # Track selection overlay active

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

        # Step count per (track, variation), read from 30 5p 16..20 (16 if not read yet)
        self.track_step_counts = {}

        # Playhead, worked out from the tempo and when playback started (no MIDI clock).
        # (start time, steps already played, BPM) while playing, else None.
        self._playhead_origin = None
        self._playhead_stopped_at = 0.0  # steps played at the last Stop (for Continue)
        self._playhead_drawn = None      # (track, step) currently lit as the cursor

        # Notes recorded live (Push pads or Seqtrak keys) are not reported by the Seqtrak,
        # so the steps on show are re-read while recording, and everything when it ends.
        self._record_reread_at = 0.0

        # After a project load or a delete, re-read the Seqtrak like at power-on.
        self._resync_at = 0.0        # when to re-read (0 = not scheduled)
        self._resync_full = False    # True: everything; False: steps only
        self._seqtrak_ui_mode = 0    # 01 10 19: 00 idle, 03 step input, 04 Delete held
        self._seqtrak_project = None # 01 10 15: current project, 0-based (None = not heard yet)

        # Variation mode: 3 or 6 variations available (global setting)
        self.variation_mode = 3  # Default: 3 variations

        # Track states (1-11)
        self.track_states = [MuteState.UNMUTED] * 11
        self.track_muted = [False] * 11      # Seqtrak mute per track (30 5p 29)
        self.solo_track = 0                  # the one soloed track, 0 = none (30 40 68)
        self.metronome_on = False            # Seqtrak click on/off (00 00 25)

        # Duplicate panel (hold Duplicate): copy From pattern -> To pattern for one track,
        # the 7 drum tracks or all 11 (the Seqtrak itself only does one track or all).
        self.duplicate_held = False
        self.dup_scope = 'drums'     # 'track' | 'drums' | 'all'
        self.dup_from = None         # None = each track's current pattern
        self.dup_goto = True         # switch to the copy afterwards
        self._timed_sends = []       # [(when, fn)] spaced-out Seqtrak messages, sent from the main loop
        self._drum_solo_saved_mutes = {}     # SYNTH/DX/SAMPLER mutes to restore after DRUM bus solo

        # Selected track for keyboard input (default SYNTH 1)
        self.keyboard_track = Track.SYNTH1
        self.patch_name = ""  # Patch name (updated from Seqtrak feedback)
        self.track_preset_names = {}  # {track: name} read from Seqtrak (01 1p 35)
        self._last_track_select_sent = 0.0  # time of our own track select (echo guard)
        self._step_read_queue = []          # pending step/note read addresses (throttled)
        self._last_step_read_sent = 0.0
        # Mirror of the Seqtrak's sampler note list, in index order: [(tick, note, length), ...].
        # Read with 75 30 [index]; the index is what a remove (74 30 [index] 00) needs.
        self.sampler_notes = []
        self._sampler_read_buf = {}         # index -> (tick, note) while a read is in flight
        self._sampler_read_next = 0         # next index to queue
        self._sampler_read_done = True
        self._sampler_resync_at = 0.0       # when to re-read the list (0 = not scheduled)

        # Active notes for proper note-off
        self.active_notes = {}  # {pad_note: midi_note}

        # Scale settings
        self.scale_index = 1  # Minor
        self.scale_scroll_offset = 0
        self.root_note = 0  # C
        # The Seqtrak project's 8 scale slots (30 4D [16*slot + 0..6] = pad notes) and the selected
        # slot (30 40 7E). Push scales are matched to a slot by their intervals.
        self.seqtrak_scale_slots = {}
        self.seqtrak_scale_slot = None
        self.in_key_mode = True

        # Tempo (for display, synced from Seqtrak on startup)
        # None = unknown, will be queried from Seqtrak
        self.tempo = None

        # Master volume (0-127)
        self.master_volume = 64  # Seqtrak default; replaced by the value read at startup
        self._master_volume_known = False

        # Mixer mode state
        self.mixer_page = 0              # 0 or 1 (12 items across 2 pages)
        self.track_volumes = [100] * 11  # Volume per track (0-127)

        # DRUM bus state (virtual channel controlling all drum tracks)
        self.drum_bus_volume = 100       # 0-127, scales all drum track volumes
        self.drum_bus_muted = False
        self.drum_bus_soloed = False

        # Swing offset in ticks, -58..+58 (0 = straight; the app shows (120 + offset) / 240 as %)
        self.swing = 0
        self._swing_known = False  # True once read from the Seqtrak (no popup for the first read)

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
        # SysEx address -> (track, CC), to fill that cache from the Seqtrak (read at start and
        # whenever the Seqtrak reports a change, e.g. its own knobs)
        self._cc_for_sysex = {}
        for track in range(1, 12):
            for cc in (7, 10, 91, 94, 20, 21, 25, 73, 75, 26, 5, 65):
                addr = sysex_address_for_cc(track, cc)
                if addr:
                    self._cc_for_sysex[tuple(addr)] = (track, cc)

        # Session view state (clip-launcher style)
        self.session_mode = False
        self.session_page = 0        # tracks 1-8 / 9-11
        self.scene_page = 0          # scenes 1-8 / 9-16
        # The Seqtrak's song (read from it): scene -> {'length': bars (0 = AUTO), 'patterns': [11 x 0-5]}
        self.song_scenes = {}
        self.song_mode = False       # 01 10 17 = 02
        self.scene_mode = False      # 71 50 00 (on top of Song mode)
        self.current_scene = None    # 71 10 04
        self.next_scene = None       # 71 10 05 (queued)
        self.song_loop = False       # 71 10 06
        self.scene_loop = False      # 71 10 07
        self.song_selected_scene = 0
        self.song_selected_track = 1
        self.scene_mutes = {}        # (scene, track) -> muted, as set from the Push (not readable)
        self.scene_solo = {}         # scene -> soloed track (0 = none), as set from the Push
        self.song_mute_held = False  # Mute / Solo held = modifiers for pads in Song view
        self.song_solo_held = False
        self._last_scene_press = (None, 0.0)

        # Isomorphic layout (same as Reason app)
        self.layout = IsomorphicLayout()
        self.layout.set_scale(self.root_note, SCALE_NAMES[self.scale_index])
        self.layout.set_in_key_mode(self.in_key_mode)

        # Settings menu state
        self.settings_mode = False  # Whether in settings menu
        self.selected_audio_direction = 'ipad_to_seqtrak'  # Which audio route is selected

        # Import SubprocessManager for iPad audio routing
        try:
            from .helpers import SubprocessManager
        except ImportError:
            # Running as script, use absolute import
            from open_push.seqtrak.helpers import SubprocessManager
        self.subprocess_mgr = SubprocessManager()

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
        elif msg.type == 'start':
            self._playhead_start()
        elif msg.type == 'continue':
            self._playhead_start(self._playhead_stopped_at)
        elif msg.type == 'stop':
            self._playhead_stop()
        elif msg.type == 'control_change':
            # Bank Select messages
            channel = msg.channel + 1  # Convert to 1-indexed track
            # A Sound Design knob turned on the Seqtrak (or undone/redone) is reported as the
            # same CC on the track's channel (seen 2026-10-14: KICK attack = CC 73 on ch 1)
            if 1 <= channel <= 11 and msg.control not in (0, 32):
                self.device_params[(channel, msg.control)] = msg.value
                if msg.control == 7:
                    self.track_volumes[channel - 1] = msg.value
                if channel == self.keyboard_track and self.current_mode in ('device', 'mixer'):
                    self.update_display()
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

    def _send_track_select(self, track):
        """Select a track on the Seqtrak and remember when we did it."""
        self._last_track_select_sent = time.time()
        self.protocol.select_track(track)

    @staticmethod
    def _decode_preset_name(sysex_data):
        """Decode a preset name from Yamaha 7-bit packed data.

        Data comes in 8-byte groups: one byte of high bits, then 7 data bytes,
        e.g. 00 'TS_RNB_' 00 'kick_rn' 00 'b' -> "TS_RNB_kick_rnb".
        """
        raw = bytearray()
        for i in range(0, len(sysex_data), 8):
            high_bits = sysex_data[i]
            for j, b in enumerate(sysex_data[i + 1:i + 8]):
                raw.append(b | (0x80 if high_bits & (0x40 >> j) else 0))
        name = raw.split(b'\x00', 1)[0]
        return name.decode('ascii', errors='ignore').strip()

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

        # Song mode state (also kept when the Song view isn't open)
        if addr[0] == 0x71 or addr == [0x01, 0x10, 0x17]:
            if self._handle_song_sysex(addr, sysex_data):
                return

        # A Sound Design value the Push shows (volume, pan, sends, EQ, pitch, ...): keep the
        # Push's copy in step with the Seqtrak so the first encoder turn doesn't jump
        param = self._cc_for_sysex.get(tuple(addr))
        if param and sysex_data:
            track, cc = param
            self.device_params[(track, cc)] = sysex_data[0]
            if cc == 7:
                self.track_volumes[track - 1] = sysex_data[0]
            if track == self.keyboard_track and self.current_mode in ('device', 'mixer'):
                self.update_display()
            return

        # Play State
        if addr == Address.PLAY_STATE and sysex_data:
            self.is_playing = (sysex_data[0] == 0x01)
            if self.is_playing and self._playhead_origin is None:
                self._playhead_start()
            elif not self.is_playing:
                self._playhead_stop()
            self.update_transport_leds()
            self.update_display()
            print(f"Seqtrak: {'PLAYING' if self.is_playing else 'STOPPED'}")

        # Record State
        elif addr == Address.RECORD_STATE and sysex_data:
            was_recording = self.is_recording
            self.is_recording = (sysex_data[0] == 0x01)
            if was_recording and not self.is_recording:
                self._reread_all_steps()
            self.set_button_led(BUTTONS['record'], LED_ON if self.is_recording else LED_DIM)
            self.update_display()
            print(f"Seqtrak: RECORD {'ON' if self.is_recording else 'OFF'}")

        # Sample Record State
        elif addr == Address.SAMPLE_RECORD and sysex_data:
            self.is_sample_recording = (sysex_data[0] == 0x01)
            self.set_button_led(BUTTONS['record'], LED_ON if self.is_sample_recording else LED_DIM)
            self.update_display()
            print(f"Seqtrak: SAMPLE RECORD {'ON' if self.is_sample_recording else 'OFF'}")

        # Per-track pattern (variation) select: 30 5[track-1] 0F [0-5]
        elif addr[0] == 0x30 and 0x50 <= addr[1] <= 0x5A and addr[2] == 0x0F and sysex_data:
            track = addr[1] - 0x50 + 1
            variation = sysex_data[0] + 1
            if self.track_variation.get(track) != variation:
                self.track_variation[track] = variation
                self._request_track_steps(track)
                if track == self.keyboard_track:
                    self.update_display()

        # Step count per variation: 30 5[track-1] 16/18/1A/1C/1E/20 [msb] [lsb]
        elif (addr[0] == 0x30 and 0x50 <= addr[1] <= 0x5A and 0x16 <= addr[2] <= 0x20
              and addr[2] % 2 == 0 and len(sysex_data) >= 2):
            track = addr[1] - 0x50 + 1
            variation = (addr[2] - 0x16) // 2 + 1
            steps = (sysex_data[0] << 7) | sysex_data[1]
            if 1 <= steps <= 128:
                self.track_step_counts[(track, variation)] = steps

        # Project switched on the Seqtrak: it sends the new project number, 01 10 15 [0-7]
        # (seen 2026-10-14). Its parameters aren't broadcast, so re-read everything.
        elif addr == [0x01, 0x10, 0x15] and sysex_data:
            if sysex_data[0] != self._seqtrak_project:
                self._seqtrak_project = sysex_data[0]
                self._schedule_resync(full=True, delay=1.0)

        # 01 10 00 00 ends the burst the Seqtrak sends after a project delete and after it
        # (re)connects (seen 2026-10-13/14); the bridge never requests it, so it is always that.
        # Not 01 10 17: that is the Song mode state and changes on every scene key in Song mode.
        elif addr == [0x01, 0x10, 0x00]:
            self._schedule_resync(full=True)

        # Seqtrak UI mode 01 10 19: 04 = Delete held. Whatever was deleted isn't always
        # reported step by step, so re-read the steps when Delete is let go.
        elif addr == [0x01, 0x10, 0x19] and sysex_data:
            if self._seqtrak_ui_mode == 0x04 and sysex_data[0] != 0x04:
                self._schedule_resync()
            self._seqtrak_ui_mode = sysex_data[0]

        # Global variation indicator (Seqtrak variation buttons): 01 10 2A [0-5]
        # 3 or 6 patterns per track: 30 40 79 00/01 (read at start, reported on change)
        elif addr == Address.PATTERN_SELECT_MODE and sysex_data:
            self._set_variation_mode(6 if sysex_data[0] else 3)

        elif addr == Address.GLOBAL_VARIATION and sysex_data:
            variation = sysex_data[0] + 1
            for track in range(1, 12):
                self.track_variation[track] = variation
                self._request_track_steps(track)
            self.update_display()

        # Drum step added on the Seqtrak: 70 [track-1] 00 [step] [note] [vel] [gate] [prob]
        elif addr[0] == 0x70 and addr[1] <= 0x06 and addr[2] == 0x00 and sysex_data:
            self._set_drum_step(addr[1] + 1, sysex_data[0], True)

        # Drum step deleted on the Seqtrak: 70 [0x20+track-1] 00 [step]
        elif addr[0] == 0x70 and 0x20 <= addr[1] <= 0x26 and addr[2] == 0x00 and sysex_data:
            self._set_drum_step(addr[1] - 0x20 + 1, sysex_data[0], False)

        # Drum step readback: 70 [0x40+track-1] [step] -> event data, or nothing if empty
        elif addr[0] == 0x70 and 0x40 <= addr[1] <= 0x46:
            self._set_drum_step(addr[1] - 0x40 + 1, addr[2], bool(sysex_data))

        # Speaker master volume (Seqtrak volume buttons, or reply to our startup read): 00 00 00 [vv]
        # Metronome (click) on/off: 00 00 25 (read at start, reported when changed on the Seqtrak)
        elif addr == [0x00, 0x00, 0x25] and sysex_data:
            self.metronome_on = bool(sysex_data[0])
            self.set_button_led(BUTTONS['metronome'], LED_ON if self.metronome_on else LED_DIM)

        elif addr == Address.MASTER_VOLUME and sysex_data:
            changed = sysex_data[0] != self.master_volume
            self.master_volume = sysex_data[0]
            if changed and self._master_volume_known:
                self._show_lcd_popup("VOLUME", self.master_volume)
            self._master_volume_known = True

        # Sampler note added (72 30 00 ...) or removal reported (74 73 00 ...) by the Seqtrak.
        # Reports also follow replaces and overlaps, so re-read the list instead of
        # trusting them one by one.
        elif addr in ([0x72, 0x30, 0x00], [0x74, 0x73, 0x00]):
            self._schedule_sampler_resync()

        # Sample pad selected on the Seqtrak itself: 01 10 28 [pad 0-6]
        elif addr == Address.SAMPLER_ELEMENT and sysex_data and sysex_data[0] <= 6:
            if sysex_data[0] != self.selected_sampler_pad:
                self.selected_sampler_pad = sysex_data[0]
                if self.current_pad_mode == PadMode.SAMPLER:
                    self.update_grid()
                    self.update_display()

        # Sampler note list readback: 75 30 [index] -> 8 bytes, or no data past the end
        elif addr[0] == 0x75 and addr[1] == 0x30:
            self._handle_sampler_note_reply(addr[2], sysex_data)

        # Track selected on the Seqtrak itself: 01 10 27 [0-10]
        elif addr == Address.TRACK_SELECT and sysex_data and sysex_data[0] <= 0x0A:
            track = sysex_data[0] + 1
            # Ignore echoes of our own recent selects (fast encoder turns)
            recent_local = time.time() - self._last_track_select_sent < 0.5
            if track != self.keyboard_track and not recent_local:
                self.keyboard_track = track
                self.patch_name = (self.track_preset_names.get(track)
                                   or self._get_track_preset_display(track))
                self.protocol.request_preset_name(track)
                self._update_pad_mode()
                self.update_display()
                print(f"Seqtrak: track -> {Track.NAMES.get(track, f'Track {track}')}")

        # Preset Name (per track: 01 1[track-1] 35)
        elif addr[0] == 0x01 and addr[2] == 0x35 and 0x10 <= addr[1] <= 0x1A and sysex_data:
            track = addr[1] - 0x10 + 1
            name = self._decode_preset_name(sysex_data)
            self.track_preset_names[track] = name
            if track == self.keyboard_track:
                self.patch_name = name
                self.update_display()
            print(f"Seqtrak: {Track.NAMES.get(track, f'Track {track}')} preset '{name}'")

        # Mute per track: 30 5p 29, 7D = muted, 00 = not (Data List; read at start, reported on change)
        elif addr[0] == 0x30 and 0x50 <= addr[1] <= 0x5A and addr[2] == 0x29 and sysex_data:
            self.track_muted[addr[1] - 0x50] = sysex_data[0] != 0
            self._sync_track_states()
            self._refresh_mute_solo_view()

        # Solo: 30 40 68 = the soloed track 1-11, 0 = none
        elif addr == [0x30, 0x40, 0x68] and sysex_data:
            self.solo_track = sysex_data[0] if sysex_data[0] <= 11 else 0
            self._sync_track_states()
            self._refresh_mute_solo_view()

        # Key 30 40 7F = 0x40 + semitone; scale 30 40 7E = project slot 0-7; slot pad notes 30 4D
        elif addr == Address.KEY and sysex_data and 0x40 <= sysex_data[0] <= 0x4B:
            self.root_note = sysex_data[0] - 0x40
            self._follow_seqtrak_scale()
        elif addr == Address.SCALE and sysex_data and sysex_data[0] <= 7:
            self.seqtrak_scale_slot = sysex_data[0]
            self._follow_seqtrak_scale()
        elif addr[:2] == [0x30, 0x4D] and sysex_data and (addr[2] & 0x0F) <= 6:
            self.seqtrak_scale_slots.setdefault(addr[2] >> 4, {})[addr[2] & 0x0F] = sysex_data[0]

        # Swing: 128 + offset in ticks (7-bit pair)
        elif addr == Address.SWING and len(sysex_data) >= 2:
            swing = ((sysex_data[0] << 7) | sysex_data[1]) - 128
            if swing != self.swing and self._swing_known:
                self.swing = swing
                self._show_swing()  # changed on the Seqtrak
            self.swing = swing
            self._swing_known = True

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

    def _update_mute_solo_leds(self):
        """Mute / Solo buttons show the selected track's state."""
        track = self.keyboard_track
        self.set_button_led(BUTTONS['mute'], LED_ON if self.track_muted[track - 1] else LED_DIM)
        self.set_button_led(BUTTONS['solo'], LED_ON if self.solo_track == track else LED_DIM)

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
        self._update_mute_solo_leds()
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
            self.set_lcd_segments(2, f"Steps:{selected_drum}", page_info, self._pattern_length_label(), f"Var {variation}")
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
            self.set_lcd_segments(2, f"Pad {pad_num}", page_info, self._pattern_length_label(), f"Var {variation}")
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
            self.set_lcd_segments(2, f"{root_name} {scale_name}", f"Oct {octave}", self._pattern_length_label(), f"Var {variation}")
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

    def _show_track_select_overlay(self):
        """Display track selection overlay on LCD and light up track buttons."""
        # Update LCD to show track selection prompt
        self.set_lcd_segments(1, "SELECT TRACK", "", "", "")
        self.set_lcd_segments(2, "KICK  SNAR CLAP", "HAT1  HAT2 PERC1", "PERC2 SYN1", "")
        self.set_lcd_segments(3, "SYN2  DX   SMPL", "", "", "")
        self.set_lcd_segments(4, "", "", "", "")

        # Light up LCD buttons for tracks 1-11
        # Upper row: Tracks 1-8
        for i, cc in enumerate([20, 21, 22, 23, 24, 25, 26, 27]):
            self.push_out.send(mido.Message('control_change', control=cc, value=1))

        # Lower row: Tracks 9-11, rest off
        for i, cc in enumerate([102, 103, 104, 105, 106, 107, 108, 109]):
            if i < 3:  # SYNTH2, DX, SAMPLER
                self.push_out.send(mido.Message('control_change', control=cc, value=1))
            else:
                self.push_out.send(mido.Message('control_change', control=cc, value=0))

    def _handle_track_select_button(self, cc):
        """Handle LCD button press for direct track selection.

        Returns True if the button was handled, False otherwise.
        """
        # Map LCD button CCs to track numbers
        track_map = {
            20: 1,   # KICK
            21: 2,   # SNARE
            22: 3,   # CLAP
            23: 4,   # HAT1
            24: 5,   # HAT2
            25: 6,   # PERC1
            26: 7,   # PERC2
            27: 8,   # SYNTH1
            102: 9,  # SYNTH2
            103: 10, # DX
            104: 11, # SAMPLER
        }

        if cc in track_map:
            track = track_map[cc]
            self.keyboard_track = track
            self.patch_name = (self.track_preset_names.get(track)
                               or self._get_track_preset_display(track))
            self._send_track_select(track)
            self.protocol.request_preset_name(track)
            self._update_pad_mode()
            track_name = Track.NAMES.get(track, f"T{track}")
            print(f"  → Selected track {track}: {track_name}")

            # Exit overlay after selection
            self.track_select_overlay = False
            self.update_display()
            return True

        return False

    # -------------------------------------------------------------------------
    # Duplicate panel
    # -------------------------------------------------------------------------

    DUP_SCOPES = ('track', 'drums', 'all')

    def _dup_tracks(self):
        if self.dup_scope == 'track':
            return [self.keyboard_track]
        return list(range(1, 8)) if self.dup_scope == 'drums' else list(range(1, 12))

    def _show_duplicate_panel(self):
        n = self.variation_mode
        scope = {'track': Track.NAMES.get(self.keyboard_track, 'Track'), 'drums': 'Drums', 'all': 'All 11'}[self.dup_scope]
        src = f"P{self.dup_from}" if self.dup_from else "current"
        self.set_lcd_segments(1, "DUPLICATE", scope, f"From {src}", "To: bottom")
        self.set_lcd_segments(2, "Top 1-%d: from" % n, "Bottom 1-%d: to" % n, "Top 7: what", "Btm 7: go %s" % ('ON' if self.dup_goto else 'OFF'))
        self.set_lcd_segments(3, "", "", "", "")
        self.set_lcd_segments(4, "", "", "", "")
        for i in range(8):
            upper, lower = 20 + i, 102 + i
            if i < n:
                self.set_button_led(upper, LED_ON if self.dup_from == i + 1 else LED_DIM)
                self.set_button_led(lower, LED_DIM)
            else:
                self.set_button_led(upper, LED_OFF)
                self.set_button_led(lower, LED_OFF)
        self.set_button_led(26, LED_ON)                                   # what to copy
        self.set_button_led(108, LED_ON if self.dup_goto else LED_DIM)   # go to the copy

    def _close_duplicate_panel(self):
        for cc in list(range(20, 28)) + list(range(102, 110)):
            self.set_button_led(cc, LED_OFF)
        if self.current_mode == 'mixer':
            self._update_mixer_button_leds()
        elif self.current_mode == 'track':
            self.set_button_led(BUTTONS['upper_1'], LED_ON)
            self.set_button_led(BUTTONS['lower_1'], LED_ON)
        if self.current_mode != 'mixer':
            self._update_bar_length_buttons()
        self.update_display()

    def _handle_duplicate_button(self, cc):
        n = self.variation_mode
        if cc == 26:
            i = self.DUP_SCOPES.index(self.dup_scope)
            self.dup_scope = self.DUP_SCOPES[(i + 1) % len(self.DUP_SCOPES)]
        elif cc == 108:
            self.dup_goto = not self.dup_goto
        elif 20 <= cc < 20 + n:
            pattern = cc - 20 + 1
            self.dup_from = None if self.dup_from == pattern else pattern
        elif 102 <= cc < 102 + n:
            self._duplicate_patterns(cc - 102 + 1)
            return
        self._show_duplicate_panel()

    def _duplicate_patterns(self, to_pattern):
        """Copy From -> To on every track in scope, like the Seqtrak's copy/paste (guide §5.5).

        Per track: select it on the Seqtrak, copy 77 01 20 [track] [from], paste 77 01 21 [track] [to]
        (verified 2026-10-14 on PERC 2: notes and length copied, target replaced). The Seqtrak's copy
        buffer holds one pattern, so tracks go one after another, spaced out from the main loop.
        """
        tracks = self._dup_tracks()
        copied = []
        delay = 0.0
        for track in tracks:
            src = self.dup_from or self.track_variation.get(track, 1)
            if src == to_pattern:
                continue
            t = track - 1
            for fn in (lambda t=t: self.protocol.select_track(t + 1),
                       lambda t=t, s=src: self.protocol.send_parameter([0x77, 0x01, 0x20], [t, s - 1]),
                       lambda t=t: self.protocol.send_parameter([0x77, 0x01, 0x21], [t, to_pattern - 1])):
                self._timed_sends.append((time.time() + delay, fn))
                delay += 0.06
            copied.append(track)
        if not copied:
            self._show_lcd_popup("DUPLICATE", f"already on P{to_pattern}")
            return
        # Back to the selected track on the Seqtrak, then (optionally) show the copies
        self._timed_sends.append((time.time() + delay, lambda: self._send_track_select(self.keyboard_track)))
        delay += 0.06
        if self.dup_goto:
            for track in copied:
                self._timed_sends.append((time.time() + delay, lambda tr=track: self.protocol.select_track_variation(tr, to_pattern)))
                self.track_variation[track] = to_pattern
                delay += 0.02
        self._last_track_select_sent = time.time() + delay  # ignore the Seqtrak's track-select echoes
        self._schedule_resync(delay=delay + 0.5)
        names = {'track': Track.NAMES.get(self.keyboard_track, ''), 'drums': 'Drums', 'all': 'All'}[self.dup_scope]
        src_label = f"P{self.dup_from}" if self.dup_from else "current"
        self._show_lcd_popup("DUPLICATED", f"{names} {src_label}->P{to_pattern}", duration=3.0)
        print(f"Duplicate: {names} {src_label} -> P{to_pattern} ({len(copied)} tracks)")

    def _process_timed_sends(self):
        now = time.time()
        while self._timed_sends and self._timed_sends[0][0] <= now:
            self._timed_sends.pop(0)[1]()

    def _show_delete_menu(self):
        """Display delete menu when DELETE button is held."""
        track_name = Track.NAMES.get(self.keyboard_track, f"T{self.keyboard_track}")
        variation = self.track_variation.get(self.keyboard_track, 1)

        # Line 1: DELETE menu title
        self.set_lcd_segments(1, "DELETE MENU", "", "", f"{track_name} V{variation}")

        # Line 2: Delete options
        self.set_lcd_segments(2, "[1] Current Var", "[2] All Vars (T)", "[3] Cur Var AllT", "")

        # Line 3: Description
        self.set_lcd_segments(3, f"Delete V{variation}", f"Delete all 6", "Clear song", "")

        # Line 4: Warning
        self.set_lcd_segments(4, "Press LCD button", "to confirm", "", "")

        # Light up option buttons
        for cc in [20, 21, 22]:  # Buttons 1-3
            self.push_out.send(mido.Message('control_change', control=cc, value=1))
        # Turn off remaining buttons
        for cc in list(range(23, 28)) + list(range(102, 110)):
            self.push_out.send(mido.Message('control_change', control=cc, value=0))

    def _handle_delete_button(self, cc):
        """Handle delete menu button presses.

        Returns True if button was handled, False otherwise.
        """
        if cc == 20:  # Button 1: Delete current variation
            self._delete_current_variation()
            return True
        elif cc == 21:  # Button 2: Delete all variations for current track
            self._delete_all_variations_track()
            return True
        elif cc == 22:  # Button 3: Delete all variations for all tracks
            self._delete_all_variations_song()
            return True

        return False

    def _delete_current_variation(self):
        """Level 1: Delete current variation for selected track."""
        track = self.keyboard_track
        variation = self.track_variation.get(track, 1)

        print(f"  Deleting Track {track} Variation {variation}...")

        # Select the variation first
        self.protocol.select_track_variation(track, variation)

        # Delete all steps/ticks in this variation
        self._clear_variation_data(track, variation)

        print(f"  ✓ Deleted T{track} V{variation}")
        self._schedule_resync()
        self.delete_held = False  # Release delete mode
        self.update_display()

    def _delete_all_variations_track(self):
        """Level 2: Delete all 6 variations for current track."""
        track = self.keyboard_track
        track_name = Track.NAMES.get(track, f"T{track}")

        print(f"  Deleting all variations for Track {track} ({track_name})...")

        for variation in range(1, 7):  # Variations 1-6
            self.protocol.select_track_variation(track, variation)
            self._clear_variation_data(track, variation)
            print(f"    Cleared V{variation}")

        # Return the track to the variation it was on (not left on V6)
        self.protocol.select_track_variation(track, self.track_variation.get(track, 1))

        print(f"  ✓ Cleared all variations for {track_name}")
        self._schedule_resync()
        self.delete_held = False
        self.update_display()

    def _delete_all_variations_song(self):
        """Level 3: delete the current pattern on every track, like DELETE + [ALL] (guide §5.4)."""
        print("  Deleting the current pattern on all tracks...")
        for track in range(1, 12):
            variation = self.track_variation.get(track, 1)
            self.protocol.select_track_variation(track, variation)
            self._clear_variation_data(track, variation)
        print("  ✓ Current pattern deleted on all tracks")
        self._schedule_resync()
        self.delete_held = False
        self.update_display()

    def _clear_variation_data(self, track, variation):
        """Clear all note data for a specific track variation.

        Sends delete commands for all steps/ticks based on track type.
        Assumes max pattern length for safety.
        """
        if track <= 7:  # Drum tracks (1-7)
            # Delete all 128 possible steps
            for step in range(128):
                self.protocol.send_drum_delete(track, step)

        else:  # Sampler (11) and melodic tracks (8-10): note lists
            # Read how many notes the selected variation holds, then remove them
            # highest index first: 74 [g] [index] 00. (01 1p 37 00 "clear track"
            # acts on the variation shown on the Seqtrak, not the one selected
            # over MIDI, so it isn't used here.)
            time.sleep(0.05)  # let the variation select land
            count = self._read_note_list_blocking(track)
            if count is None:
                print(f"    Could not read notes for track {track}; nothing removed")
                return
            for index in reversed(range(count)):
                self.protocol.remove_note(track, index)
            if track == 11:
                self._schedule_sampler_resync()

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

    def _display_settings_menu(self):
        """Display settings menu - iPad Audio controls."""
        # Get status
        i2s_running = self.subprocess_mgr.is_running('ipad_to_seqtrak')
        s2i_running = self.subprocess_mgr.is_running('seqtrak_to_ipad')
        i2s_status = self.subprocess_mgr.get_status('ipad_to_seqtrak')
        s2i_status = self.subprocess_mgr.get_status('seqtrak_to_ipad')

        # Build indicators with selection marker
        i2s_sel = ">" if self.selected_audio_direction == 'ipad_to_seqtrak' else " "
        s2i_sel = ">" if self.selected_audio_direction == 'seqtrak_to_ipad' else " "

        i2s_ind = "*" if i2s_running else "o"
        s2i_ind = "*" if s2i_running else "o"

        # Line 1: Title and column headers
        self.set_lcd_segments(1, "Settings", "iPad>Seqtrak", "Seqtrak>iPad", "")

        # Line 2: Audio routing status with selection
        self.set_lcd_segments(2, "Audio Route", f"{i2s_sel}{i2s_ind} ON" if i2s_running else f"{i2s_sel}{i2s_ind} OFF",
                                                f"{s2i_sel}{s2i_ind} ON" if s2i_running else f"{s2i_sel}{s2i_ind} OFF", "")

        # Line 3: Status details
        self.set_lcd_segments(3, "", i2s_status, s2i_status, "")

        # Line 4: Help text
        self.set_lcd_segments(4, "Enc1:Select", "Press:Toggle", "", "User:Exit")

    def _handle_settings_encoder(self, cc, value):
        """Handle encoder input in settings mode."""
        print(f"[Settings] Encoder CC {cc}, value {value}")

        # Encoder 1 turn (CC 71) - Select audio direction
        if cc == 71:
            if value < 64:  # Clockwise
                self.selected_audio_direction = 'seqtrak_to_ipad'
                print(f"  Selected: Seqtrak>iPad")
            else:  # Counter-clockwise
                self.selected_audio_direction = 'ipad_to_seqtrak'
                print(f"  Selected: iPad>Seqtrak")
            self._display_settings_menu()

        # Encoder 1 press (CC 20) - Toggle selected direction
        elif cc == 20:
            print(f"  Encoder press detected")
            if self.subprocess_mgr.is_running(self.selected_audio_direction):
                success, msg = self.subprocess_mgr.stop(self.selected_audio_direction)
                print(f"  Stopped {self.selected_audio_direction}: {msg}")
            else:
                success, msg = self.subprocess_mgr.start_alsaloop(self.selected_audio_direction)
                print(f"  Started {self.selected_audio_direction}: {msg}")
            self._display_settings_menu()

    def _handle_settings_button(self, cc, value):
        """Handle button input in settings mode."""
        print(f"[Settings] Button CC {cc}, value {value}")

        # Encoder 1 press (CC 20) - Toggle selected direction
        if cc == 20:
            print(f"  Encoder press detected (button handler)")
            if self.subprocess_mgr.is_running(self.selected_audio_direction):
                success, msg = self.subprocess_mgr.stop(self.selected_audio_direction)
                print(f"  Stopped {self.selected_audio_direction}: {msg}")
            else:
                success, msg = self.subprocess_mgr.start_alsaloop(self.selected_audio_direction)
                print(f"  Started {self.selected_audio_direction}: {msg}")
            self._display_settings_menu()

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
                    self.set_pad_color(note, self._step_pad_color(self.selected_drum_track, step_index))

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
                        self.set_pad_color(note, self._step_pad_color(Track.SAMPLER, step_index))
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
        """Apply current scale settings to layout, and send key and scale to the Seqtrak.

        Key and scale only change the Seqtrak's own Synth keys and chords (guide §7.4, §7.5);
        the Push pads already play the notes. The scale is sent only if one of the project's
        8 scale slots has the same intervals.
        """
        self.layout.set_scale(self.root_note, SCALE_NAMES[self.scale_index])
        self.layout.set_in_key_mode(self.in_key_mode)
        self.update_grid()
        self.protocol.set_key_from_semitone(self.root_note)
        slot = self._seqtrak_slot_for_scale(SCALE_NAMES[self.scale_index])
        if slot is None:
            print("  (not one of the Seqtrak project's 8 scales; Seqtrak scale unchanged)")
        elif slot != self.seqtrak_scale_slot:
            self.seqtrak_scale_slot = slot
            self.protocol.set_scale(slot)

    def _slot_intervals(self, slot):
        notes = self.seqtrak_scale_slots.get(slot, {})
        if len(notes) < 5 or 0 not in notes:
            return None
        return frozenset((notes[i] - notes[0]) % 12 for i in notes)

    def _seqtrak_slot_for_scale(self, scale_name):
        want = frozenset(SCALES[scale_name])
        for slot in range(8):
            if self._slot_intervals(slot) == want:
                return slot
        return None

    def _push_scale_for_slot(self, slot):
        have = self._slot_intervals(slot)
        if have is None:
            return None
        if frozenset(SCALES[SCALE_NAMES[self.scale_index]]) == have:
            return self.scale_index
        for i, name in enumerate(SCALE_NAMES):
            if frozenset(SCALES[name]) == have:
                return i
        return None

    def _follow_seqtrak_scale(self):
        """Show the Seqtrak's key and scale on the Push (when it is one the Push knows)."""
        if self.seqtrak_scale_slot is not None:
            index = self._push_scale_for_slot(self.seqtrak_scale_slot)
            if index is not None:
                self.scale_index = index
        self.layout.set_scale(self.root_note, SCALE_NAMES[self.scale_index])
        self.update_grid()
        self.update_display()

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

    # Session view = the Seqtrak's song (guide §13). Rows = scenes (top row = first scene on the
    # page, Up/Down = scenes 1-8 / 9-16), columns = tracks 1-8 / 9-11 (Page buttons), pad
    # colour = that track's pattern in the scene. Messages: UNDOCUMENTED-MESSAGES.md §2, all
    # verified as commands from the Pi on 2026-10-15 except loop (71 10 07) and queueing.

    SCENE_PATTERN_COLORS = [COLOR_RED, COLOR_ORANGE, COLOR_YELLOW, COLOR_GREEN, COLOR_CYAN, COLOR_BLUE]

    def _enter_session_mode(self):
        self.session_mode = True
        self.session_page = 0
        self.scene_page = 0
        print("Entering Song view")
        self.set_button_led(BUTTONS['session'], LED_ON)
        self._request_song()
        self._refresh_song_view()

    def _exit_session_mode(self):
        self.session_mode = False
        print("Exiting Song view")
        self.set_button_led(BUTTONS['session'], LED_DIM)
        for cc in range(36, 44):
            self.set_button_led(cc, LED_OFF)
        for cc in (BUTTONS['up'], BUTTONS['down']):
            self.set_button_led(cc, LED_OFF)
        self.update_grid()
        self.update_display()

    def _request_song(self):
        """Read the song: mode, current scene, loops and all 16 scenes."""
        for addr in ([0x01, 0x10, 0x17], [0x71, 0x50, 0x00], [0x71, 0x10, 0x04],
                     [0x71, 0x10, 0x06], [0x71, 0x10, 0x07]):
            self.protocol.request_parameter(addr)
        for scene in range(16):
            self.protocol.request_parameter([0x71, 0x40, scene])

    def _song_mode_label(self):
        if self.scene_mode:
            return "SCENE MODE"
        return "SONG MODE" if self.song_mode else "NORMAL"

    def _scene_tracks_on_page(self):
        return list(range(1, 9)) if self.session_page == 0 else [9, 10, 11]

    def _first_empty_scene(self):
        for scene in range(16):
            if scene not in self.song_scenes:
                return scene
        return None

    def _refresh_song_view(self):
        if not self.session_mode:
            return
        self._update_session_grid()
        self._update_session_display()

    def _update_session_grid(self):
        tracks = self._scene_tracks_on_page()
        empty = self._first_empty_scene()
        for vrow in range(8):
            scene = self.scene_page * 8 + vrow
            data = self.song_scenes.get(scene)
            for col in range(8):
                note = 36 + (7 - vrow) * 8 + col
                color = COLOR_OFF
                if data and col < len(tracks):
                    track = tracks[col]
                    pattern = data['patterns'][track - 1]
                    if (scene, track) == (self.song_selected_scene, self.song_selected_track):
                        color = COLOR_WHITE
                    elif self.scene_solo.get(scene) == track:
                        color = COLOR_PURPLE
                    elif self.scene_mutes.get((scene, track)):
                        color = COLOR_DIM
                    else:
                        color = self.SCENE_PATTERN_COLORS[pattern % 6]
                elif scene == empty and col == 0:
                    color = COLOR_DIM  # "+": press to add a scene
                self.push_out.send(mido.Message('note_on', note=note, velocity=color, channel=0))
            # Scene launch buttons: on = playing scene, dim = scene exists, off = empty
            cc = 43 - vrow
            if data:
                self.set_button_led(cc, LED_ON if scene == self.current_scene else LED_DIM)
            else:
                self.set_button_led(cc, LED_OFF)
        self.set_button_led(BUTTONS['page_left'], LED_ON if self.session_page > 0 else LED_DIM)
        self.set_button_led(BUTTONS['page_right'], LED_ON if self.session_page == 0 else LED_DIM)
        self.set_button_led(BUTTONS['up'], LED_ON if self.scene_page > 0 else LED_DIM)
        self.set_button_led(BUTTONS['down'], LED_ON if self.scene_page == 0 else LED_DIM)
        self.set_button_led(BUTTONS['upper_1'], LED_ON)                       # mode
        self.set_button_led(BUTTONS['upper_8'], LED_ON if self.song_loop else LED_DIM)  # song loop

    def _update_session_display(self):
        tracks = self._scene_tracks_on_page()
        names = [MIXER_TRACK_ABBREV.get(t, f"T{t}") for t in tracks] + [""] * (8 - len(tracks))
        scene = self.song_selected_scene
        data = self.song_scenes.get(scene)
        pats = [str(data['patterns'][t - 1] + 1) if data else "" for t in tracks] + [""] * (8 - len(tracks))
        count = len(self.song_scenes)
        length = (("AUTO" if data['length'] == 0 else f"{data['length']} bar") if data else "-")
        playing = f"Play S{self.current_scene + 1}" if self.current_scene is not None else ""
        if self.next_scene is not None and self.next_scene != self.current_scene:
            playing += f">S{self.next_scene + 1}"
        self.set_lcd_segments(1, self._song_mode_label(), f"Scene {scene + 1}/{count}",
                              f"Len {length}", playing)
        self.set_lcd_segments(2, f"{names[0]:^8s}{names[1]:^9s}", f"{names[2]:^8s}{names[3]:^9s}",
                              f"{names[4]:^8s}{names[5]:^9s}", f"{names[6]:^8s}{names[7]:^9s}")
        self.set_lcd_segments(3, f"{pats[0]:^8s}{pats[1]:^9s}", f"{pats[2]:^8s}{pats[3]:^9s}",
                              f"{pats[4]:^8s}{pats[5]:^9s}", f"{pats[6]:^8s}{pats[7]:^9s}")
        loop = "Loop scn ON" if self.scene_loop else ""
        self.set_lcd_segments(4, "[1] mode", f"Scenes {self.scene_page * 8 + 1}-{self.scene_page * 8 + 8}",
                              loop, f"[8] SongLoop {'ON' if self.song_loop else 'off'}")

    def _handle_session_pad(self, row, col):
        """Pad: select a scene+track; hold Mute / Solo to mute / solo it in that scene;
        the dim pad below the last scene adds a scene (a copy of the current one)."""
        vrow = 7 - row
        scene = self.scene_page * 8 + vrow
        tracks = self._scene_tracks_on_page()
        if scene not in self.song_scenes:
            if scene == self._first_empty_scene() and col == 0:
                self.protocol.send_parameter([0x71, 0x00, 0x00], [scene])
                print(f"  Song: add scene {scene + 1}")
                self.protocol.request_parameter([0x71, 0x40, scene])
                self.song_selected_scene = scene
            return
        if col >= len(tracks):
            return
        track = tracks[col]
        if self.song_mute_held:
            muted = not self.scene_mutes.get((scene, track), False)
            self.scene_mutes[(scene, track)] = muted
            self.protocol.send_parameter([0x71, 0x10 + track - 1, 0x02], [scene, 0x01 if muted else 0x00])
            print(f"  Scene {scene + 1} {MIXER_TRACK_ABBREV.get(track)}: {'muted' if muted else 'unmuted'}")
        elif self.song_solo_held:
            solo = 0 if self.scene_solo.get(scene) == track else track
            self.scene_solo[scene] = solo
            self.protocol.send_parameter([0x71, 0x10, 0x03], [scene, solo])
            print(f"  Scene {scene + 1} solo: {MIXER_TRACK_ABBREV.get(solo, 'off')}")
        self.song_selected_scene = scene
        self.song_selected_track = track
        self._refresh_song_view()

    def _handle_session_encoder(self, encoder_index, delta):
        """Encoder over a column: that track's pattern in the selected scene."""
        tracks = self._scene_tracks_on_page()
        scene = self.song_selected_scene
        data = self.song_scenes.get(scene)
        if not data or encoder_index >= len(tracks):
            return
        track = tracks[encoder_index]
        current = data['patterns'][track - 1]
        new = max(0, min(self.variation_mode - 1, current + (1 if delta > 0 else -1)))
        if new != current:
            data['patterns'][track - 1] = new
            self.protocol.send_parameter([0x71, 0x10 + track - 1, 0x01], [scene, new])
            self.song_selected_track = track
            print(f"  Scene {scene + 1} {MIXER_TRACK_ABBREV.get(track)}: pattern {new + 1}")
            self._refresh_song_view()

    def _adjust_scene_length(self, delta):
        """Master encoder in Song view: selected scene's length, AUTO or 1-96 bars."""
        data = self.song_scenes.get(self.song_selected_scene)
        if not data:
            return
        new = max(0, min(96, data['length'] + (1 if delta > 0 else -1)))
        if new != data['length']:
            data['length'] = new
            self.protocol.send_parameter([0x71, 0x10, 0x00], [self.song_selected_scene, new >> 7, new & 0x7F])
            self._show_lcd_popup("LENGTH", "AUTO" if new == 0 else f"{new} bars")
            self._update_session_display()

    def _handle_session_row_launch(self, vrow):
        """Scene launch button: go to the scene (in Song mode while playing the Seqtrak plays it
        next); press again within 0.4 s to loop it; Delete + button deletes the scene."""
        scene = self.scene_page * 8 + vrow
        if scene not in self.song_scenes:
            return
        if self.delete_held:
            self.protocol.send_parameter([0x71, 0x20, 0x00], [scene])
            print(f"  Song: delete scene {scene + 1}")
            self._request_song()  # later scenes move up
            return
        now = time.time()
        last_scene, last_time = self._last_scene_press
        if last_scene == scene and now - last_time < 0.4:
            self.scene_loop = not self.scene_loop
            self.protocol.send_parameter([0x71, 0x10, 0x07], [0x01 if self.scene_loop else 0x00])
            print(f"  Scene {scene + 1} loop: {'ON' if self.scene_loop else 'off'}")
            self._last_scene_press = (None, 0.0)
        else:
            self.protocol.send_parameter([0x71, 0x10, 0x04], [scene])
            if not self.is_playing:
                self.current_scene = scene
            self.next_scene = scene
            print(f"  Song: go to scene {scene + 1}")
            self._last_scene_press = (scene, now)
        self.song_selected_scene = scene
        self._refresh_song_view()

    def _cycle_song_mode(self):
        """Normal -> Song -> Scene -> Normal (01 10 17, 71 50 00; leaving Scene mode also
        leaves Song mode on the Seqtrak)."""
        if not self.song_mode:
            self.protocol.send_parameter([0x01, 0x10, 0x17], [0x02])
            self.song_mode, self.scene_mode = True, False
        elif not self.scene_mode:
            self.protocol.send_parameter([0x71, 0x50, 0x00], [0x01])
            self.scene_mode = True
        else:
            self.protocol.send_parameter([0x71, 0x50, 0x00], [0x00])
            self.song_mode, self.scene_mode = False, False
        self._show_lcd_popup("MODE", self._song_mode_label())
        print(f"  {self._song_mode_label()}")
        self._refresh_song_view()

    def _toggle_song_loop(self):
        self.song_loop = not self.song_loop
        self.protocol.send_parameter([0x71, 0x10, 0x06], [0x01 if self.song_loop else 0x00])
        print(f"  Song loop: {'ON' if self.song_loop else 'off'}")
        self._refresh_song_view()

    def _handle_song_sysex(self, addr, data):
        """Song state from the Seqtrak (replies and its own reports). True if handled."""
        if addr == [0x01, 0x10, 0x17] and data:
            self.song_mode = data[0] == 0x02
        elif addr == [0x71, 0x50, 0x00] and data:
            self.scene_mode = bool(data[0])
        elif addr == [0x71, 0x10, 0x04] and data:
            self.current_scene = data[0]
            self.next_scene = None
        elif addr == [0x71, 0x10, 0x05] and data:
            self.next_scene = data[0]
        elif addr == [0x71, 0x10, 0x06] and data:
            self.song_loop = bool(data[0])
        elif addr == [0x71, 0x10, 0x07] and data:
            self.scene_loop = bool(data[0])
        elif addr[:2] == [0x71, 0x40]:
            scene = addr[2]
            if len(data) >= 13:
                self.song_scenes[scene] = {'length': (data[0] << 7) | data[1], 'patterns': list(data[2:13])}
            else:
                self.song_scenes.pop(scene, None)
        elif addr == [0x71, 0x10, 0x00] and len(data) >= 3 and data[0] in self.song_scenes:
            self.song_scenes[data[0]]['length'] = (data[1] << 7) | data[2]
        elif addr[0] == 0x71 and 0x10 <= addr[1] <= 0x1A and addr[2] == 0x01 and len(data) >= 2:
            if data[0] in self.song_scenes:
                self.song_scenes[data[0]]['patterns'][addr[1] - 0x10] = data[1]
        elif addr in ([0x71, 0x00, 0x00], [0x71, 0x20, 0x00]):
            self._request_song()  # scene added / deleted on the Seqtrak: scenes may have moved
        else:
            return False
        self._refresh_song_view()
        return True

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

        # Patch cycling (CC 22, CC 104) and bar length (CC 24, CC 106) - not in mixer mode
        if mode != 'mixer':
            self.set_button_led(BUTTONS['upper_3'], LED_ON)  # CC 22 - prev patch
            self.set_button_led(BUTTONS['lower_3'], LED_ON)  # CC 104 - next patch
            self.set_button_led(BUTTONS['upper_5'], LED_ON)  # CC 24 - bar length down
            self.set_button_led(BUTTONS['lower_5'], LED_ON)  # CC 106 - bar length up

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
            was_held = self.shift_held
            self.shift_held = (value > 0)
            self.set_button_led(cc, LED_ON if self.shift_held else LED_DIM)
            # Exit track selection overlay when shift is released
            if was_held and not self.shift_held and self.track_select_overlay:
                self.track_select_overlay = False
                self.update_display()
                print("← Exited track selection overlay")
            return

        # Track DELETE button state (hold for the delete menu)
        if cc == BUTTONS['delete']:
            self.delete_held = (value > 0)
            self.set_button_led(cc, LED_ON if self.delete_held else LED_DIM)
            if self.delete_held:
                self._show_delete_menu()
            else:
                self.update_display()  # Restore normal display
            return

        # METRONOME: the Seqtrak's click on/off (00 00 25, SEQTRAK app capture 112-03)
        if cc == BUTTONS['metronome']:
            if value > 0:
                self.metronome_on = not self.metronome_on
                self.protocol.set_metronome(self.metronome_on)
                self.set_button_led(cc, LED_ON if self.metronome_on else LED_DIM)
                self._show_lcd_popup("METRONOME", "ON" if self.metronome_on else "OFF")
                print(f"Metronome: {'ON' if self.metronome_on else 'OFF'}")
            return

        # MUTE / SOLO: mute or solo the selected track (the Seqtrak solos one track at a time)
        if cc in (BUTTONS['mute'], BUTTONS['solo']) and self.session_mode:
            # Song view: hold Mute / Solo and press a pad = mute / solo that track in that scene
            if cc == BUTTONS['mute']:
                self.song_mute_held = value > 0
            else:
                self.song_solo_held = value > 0
            self.set_button_led(cc, LED_ON if value > 0 else LED_DIM)
            return
        if cc in (BUTTONS['mute'], BUTTONS['solo']):
            if value > 0:
                if cc == BUTTONS['mute']:
                    self._toggle_track_mute_simple(self.keyboard_track)
                else:
                    self._toggle_track_solo(self.keyboard_track)
                self._update_mute_solo_leds()
                if self.current_mode != 'mixer':
                    self.update_grid()
            return

        # DUPLICATE: hold for the copy panel (buttons below the LCD), release to close it
        if cc == BUTTONS['duplicate']:
            self.duplicate_held = value > 0
            self.set_button_led(cc, LED_ON if self.duplicate_held else LED_DIM)
            if self.duplicate_held:
                self.dup_from = None
                self._show_duplicate_panel()
            else:
                self._close_duplicate_panel()
            return
        if self.duplicate_held and (20 <= cc <= 27 or 102 <= cc <= 109):
            if value > 0:
                self._handle_duplicate_button(cc)
            return

        # DOUBLE LOOP: double the selected track's pattern length (max 128 steps). The Seqtrak
        # copies the existing bars into the new ones itself (verified 2026-10-14 on PERC 2).
        if cc == BUTTONS['double_loop']:
            self.set_button_led(cc, LED_ON if value > 0 else LED_DIM)
            if value > 0:
                track = self.keyboard_track
                steps = self._track_steps(track)
                if steps * 2 > 128:
                    self._show_lcd_popup("DOUBLE", f"max 128 ({steps})")
                else:
                    self._set_pattern_steps(track, steps * 2)
                    self._schedule_resync()  # re-read once the Seqtrak has copied the bars
                    self._show_lcd_popup("DOUBLE", f"{steps * 2} steps")
            return

        # UNDO: the Seqtrak's [UNDO/REDO] button, which toggles between undo and redo of the
        # last sound/effect parameter change (guide §9.4). 01 10 1F 01 verified 2026-10-14.
        if cc == BUTTONS['undo']:
            self.set_button_led(cc, LED_ON if value > 0 else LED_DIM)
            if value > 0:
                self.protocol.undo_redo()
                self._show_lcd_popup("UNDO/REDO", "")
                print("Undo/Redo")
            return

        # Shift + Track = Enter track selection overlay
        if cc == BUTTONS['track'] and value > 0 and self.shift_held:
            self.track_select_overlay = True
            self._show_track_select_overlay()
            print("→ Entered track selection overlay")
            return

        # Handle track selection via LCD buttons when overlay is active
        if self.track_select_overlay and value > 0:
            if self._handle_track_select_button(cc):
                return  # Button was handled by track select

        # Handle delete menu options when DELETE is held
        if self.delete_held and value > 0:
            if self._handle_delete_button(cc):
                return  # Button was handled by delete menu

        # Only process button presses, not releases
        if value == 0:
            return

        # Shift + User (CC 59) = Enter/exit settings menu
        if cc == 59:  # User button
            if self.shift_held and not self.settings_mode:
                # Enter settings mode
                self.settings_mode = True
                self._display_settings_menu()
                print("→ Entered settings menu")
                return
            elif self.settings_mode:
                # Exit settings mode
                self.settings_mode = False
                self.update_display()
                print("← Exited settings menu")
                return

        # If in settings mode, handle settings-specific input
        if self.settings_mode:
            self._handle_settings_button(cc, value)
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
                self._playhead_stop()
                self.update_transport_leds()
                self.update_display()
                print("  -> Sent Stop (Shift+Play = return to zero)")
            elif self.is_playing:
                # Already playing -> Stop
                self.protocol.stop()
                self.is_playing = False
                self._playhead_stop()
                self.update_transport_leds()
                self.update_display()
                print("■ STOP (toggle)")
            else:
                # Not playing -> Play
                self.protocol.start()
                self.is_playing = True
                self._playhead_start()
                self.update_transport_leds()
                self.update_display()
                print("▶ PLAY")

        elif cc == BUTTONS['stop']:
            self.protocol.stop()
            self.is_playing = False
            self._playhead_stop()
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
                if not self.is_recording:
                    self._reread_all_steps()
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
        elif cc == BUTTONS['session'] and self.shift_held:
            if not self.session_mode:
                self._enter_session_mode()
            self._cycle_song_mode()
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

        # Song view: [1] = Normal / Song / Scene mode, [8] = loop the whole song
        elif self.session_mode and (20 <= cc <= 27 or 102 <= cc <= 109):
            if cc == BUTTONS['upper_1']:
                self._cycle_song_mode()
            elif cc == BUTTONS['upper_8']:
                self._toggle_song_loop()

        # Song view: Up / Down = scenes 1-8 / 9-16
        elif self.session_mode and cc in (BUTTONS['up'], BUTTONS['down']):
            self.scene_page = 0 if cc == BUTTONS['up'] else 1
            self._refresh_song_view()

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
        # If in settings mode, handle settings-specific encoder input
        if self.settings_mode:
            self._handle_settings_encoder(cc, value)
            return

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

            new_tempo = max(5, min(300, self.tempo + tempo_delta))
            if new_tempo != self.tempo:
                self.tempo = new_tempo
                self.protocol.set_tempo(self.tempo)
                self.update_display()
                print(f"Tempo: {self.tempo}")

        # Swing encoder (CC 15)
        elif cc == 15:
            # -58..+58 ticks; one click = 2 ticks (1 % in the app), like the app's arrows
            new_swing = max(-58, min(58, self.swing + (delta * 2)))
            if new_swing != self.swing:
                self.swing = new_swing
                self.protocol.set_swing(self.swing)
                self._show_swing()
                print(f"Swing: {self.swing:+d} ticks ({self.protocol.swing_percent(self.swing)}%)")

        # Session mode: CC 71-78 encoders set pattern for selected slot
        # Must be checked BEFORE device/mixer modes to block other encoder behavior
        elif self.session_mode and 71 <= cc <= 78:
            encoder_index = cc - 71  # 0-7
            self._handle_session_encoder(encoder_index, delta)

        # Song view: master encoder = selected scene's length (Shift = master volume as usual)
        elif self.session_mode and cc == 79 and not self.shift_held:
            self._adjust_scene_length(delta)

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
                low, high = CC_RANGES.get(param_cc, (0, 127))
                new_val = max(low, min(high, current_val + val_delta))

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
                self._show_lcd_popup("VOLUME", self.master_volume)
                print(f"Master Volume: {self.master_volume}")

        # Bar length control (CC 75)
        elif cc == 75:
            self._adjust_bar_length(delta, by_steps=True)

    def _adjust_bar_length(self, delta, by_steps=False):
        """Change the current track's pattern length, like the Seqtrak (guide §5.2).

        Bar length buttons: 1, 2, 4 or 8 bars (wrapping). Encoder: any length from 1 to 128
        steps, one step per click, or one bar (16 steps) per click with Shift held.
        """
        track = self.keyboard_track
        current = self._track_steps(track) or 16 * self.track_bar_length.get(track, 1)
        if by_steps:
            unit = 16 if self.shift_held else 1
            if unit == 16:
                # A bar at a time, landing on whole bars (24 steps -> up 32, down 16)
                if delta > 0:
                    steps = (current // 16 + delta) * 16
                else:
                    steps = ((current - 1) // 16 + 1 + delta) * 16
                steps = max(16, min(128, steps))
            else:
                steps = max(1, min(128, current + delta))
        else:
            valid = [16, 32, 64, 128]
            if delta > 0:
                bigger = [v for v in valid if v > current]
                steps = bigger[0] if bigger else valid[0]
            else:
                smaller = [v for v in valid if v < current]
                steps = smaller[-1] if smaller else valid[-1]
        if steps != current:
            self._set_pattern_steps(track, steps)

    def _pattern_length_label(self):
        """'2 Bar(s)', or the step count when it isn't whole bars (e.g. '24 Steps')."""
        steps = self._track_steps(self.keyboard_track) or 16 * self.track_bar_length.get(self.keyboard_track, 1)
        return f"{steps // 16} Bar(s)" if steps % 16 == 0 else f"{steps} Steps"

    def _set_pattern_steps(self, track, steps):
        # Address: 30 5[part] [16 + 2 * (variation - 1)] (pattern 1-6 step count), 2 bytes
        variation = self.track_variation.get(track, 1)
        addr = [0x30, 0x50 + track - 1, 0x16 + 2 * (variation - 1)]
        self.protocol.send_parameter(addr, [steps >> 7, steps & 0x7F])
        self.track_step_counts[(track, variation)] = steps
        self.track_bar_length[track] = max(1, (steps + 15) // 16)
        self.update_display()
        self._update_bar_length_buttons()
        print(f"  Pattern length: {steps} steps ({steps / 16:g} bars)")

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
        self._request_track_steps(track)

        self.update_display()
        print(f"  Variation: {new_var}/{max_var} for {Track.NAMES.get(track, f'Track {track}')}")

    def _toggle_variation_mode(self):
        """Toggle between 3 and 6 patterns per track (Seqtrak project setting 30 40 79)."""
        self._set_variation_mode(6 if self.variation_mode == 3 else 3)
        self.protocol.set_pattern_select_mode(self.variation_mode == 6)
        print(f"  Variation Mode: {self.variation_mode} variations")

    def _set_variation_mode(self, mode):
        self.variation_mode = mode
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

    def _show_swing(self):
        """Swing popup: ticks (guide §4.5.2, -58..+58) and the app's % (50 % = straight)."""
        self._show_lcd_popup("SWING", f"{self.swing:+d} {self.protocol.swing_percent(self.swing)}%")

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

    # -------------------------------------------------------------------------
    # Playhead (step cursor)
    # -------------------------------------------------------------------------

    def _track_steps(self, track):
        """Step count of the track's current variation (16 until read from the Seqtrak)."""
        return self.track_step_counts.get((track, self.track_variation.get(track, 1)), 16)

    def _step_is_set(self, track, step_index):
        if track == Track.SAMPLER:
            steps = self.sampler_step_states.get(self.selected_sampler_pad, ())
        else:
            steps = self.step_states.get(track, ())
        return step_index < len(steps) and steps[step_index]

    def _step_pad_color(self, track, step_index):
        """Pad colour for a step, with the playhead cursor on top."""
        step_on = self._step_is_set(track, step_index)
        if self._playhead_drawn == (track, step_index):
            return PLAYHEAD_COLOR_HIT if step_on else PLAYHEAD_COLOR
        return STEP_COLOR_ON if step_on else STEP_COLOR_OFF

    def _step_grid_track(self):
        """Track whose steps are on the pads, or None if no step grid is showing."""
        if self.session_mode or self.current_mode in ('mute', 'welcome'):
            return None
        if self.current_pad_mode == PadMode.DRUM:
            return self.selected_drum_track
        if self.current_pad_mode == PadMode.SAMPLER:
            return Track.SAMPLER
        return None

    def _step_pad_note(self, step_index):
        """Pad note showing this step on the current page, or None if it's on another page."""
        local = step_index - self.step_page * 32
        if not 0 <= local < 32:
            return None
        row, col = 7 - local // 8, local % 8
        return 36 + row * 8 + col

    def _playhead_start(self, steps_played=0.0):
        self._playhead_origin = (time.time(), steps_played, self.tempo or 120)

    def _playhead_stop(self):
        if self._playhead_origin is not None:
            self._playhead_stopped_at = self._playhead_steps()
        self._playhead_origin = None
        self._draw_playhead(None)

    def _playhead_steps(self):
        """Sixteenth-note steps played since Start (one step = 15 / BPM seconds)."""
        t0, steps0, bpm = self._playhead_origin
        now = time.time()
        steps = steps0 + (now - t0) * bpm / 15.0
        tempo = self.tempo or 120
        if tempo != bpm:
            # Tempo changed while playing: carry on from here at the new speed
            self._playhead_origin = (now, steps, tempo)
        return steps

    def _process_playhead(self):
        """Light the pad of the step that is playing now (called from the main loop)."""
        track = self._step_grid_track()
        if self._playhead_origin is None or track is None:
            self._draw_playhead(None)
            return
        step = int(self._playhead_steps()) % self._track_steps(track)
        self._draw_playhead((track, step))

    def _draw_playhead(self, target):
        """Move the cursor to (track, step), or remove it with None. Repaints only two pads."""
        if target == self._playhead_drawn:
            return
        old, self._playhead_drawn = self._playhead_drawn, target
        for track, step in (p for p in (old, target) if p):
            note = self._step_pad_note(step)
            if note is not None and track == self._step_grid_track():
                self.set_pad_color(note, self._step_pad_color(track, step))

    def _set_drum_step(self, track, step_index, on):
        """Record a drum step state reported by the Seqtrak and redraw if visible."""
        if not 1 <= track <= 7 or not 0 <= step_index < 128:
            return
        steps = self.step_states.setdefault(track, [False] * 128)
        if steps[step_index] == on:
            return
        steps[step_index] = on
        if self.current_pad_mode == PadMode.DRUM and track == self.selected_drum_track:
            self.update_grid()

    def _request_track_steps(self, track):
        """Re-read a track's steps from the Seqtrak (drums: step grid, sampler: note list)."""
        if track == 11:
            self._schedule_sampler_resync(0.0)
        else:
            self._request_drum_steps(track)

    def _schedule_sampler_resync(self, delay=0.15):
        """Re-read the sampler note list after `delay` seconds (debounced)."""
        self._sampler_resync_at = time.time() + delay

    def _request_sampler_notes(self):
        """Queue a read of the sampler note list (75 30 0, 1, 2, ... until an empty reply)."""
        self._sampler_read_buf = {}
        self._sampler_read_done = False
        self._step_read_queue = [a for a in self._step_read_queue if a[0] != 0x75]
        self._sampler_read_next = 0
        self._queue_sampler_reads(max(16, len(self.sampler_notes) + 8))

    def _queue_sampler_reads(self, count):
        last = min(128, self._sampler_read_next + count)
        self._step_read_queue.extend([0x75, 0x30, i] for i in range(self._sampler_read_next, last))
        self._sampler_read_next = last

    def _handle_sampler_note_reply(self, index, data):
        if self._sampler_read_done:
            return
        if len(data) >= 8:
            self._sampler_read_buf[index] = ((data[0] << 7) | data[1], data[3],
                                             (data[6] << 7) | data[7])
            if index == self._sampler_read_next - 1 and self._sampler_read_next < 128:
                self._queue_sampler_reads(16)
            return
        # First empty reply = end of list
        if all(i in self._sampler_read_buf for i in range(index)):
            self._sampler_read_done = True
            self._step_read_queue = [a for a in self._step_read_queue if a[0] != 0x75]
            self._apply_sampler_notes([self._sampler_read_buf[i] for i in range(index)])

    def _apply_sampler_notes(self, notes):
        """Replace the sampler mirror and rebuild the per-pad step grid from it."""
        self.sampler_notes = notes
        states = {}
        for tick, note, _length in notes:
            pad, step = note - 0x3C, round(tick / 120)
            if 0 <= pad <= 6 and 0 <= step < 128:
                states.setdefault(pad, [False] * 128)[step] = True
        if states != {p: v for p, v in self.sampler_step_states.items() if any(v)}:
            self.sampler_step_states = states
            if self.current_pad_mode == PadMode.SAMPLER:
                self.update_grid()

    def _read_note_list_blocking(self, track, timeout=1.0):
        """Read a sampler/melodic note list right now (used by the delete menu).

        Other Seqtrak messages that arrive meanwhile are passed to the normal handler.
        Returns the number of notes, or None if the list couldn't be read.
        """
        port = getattr(self, 'seqtrak_in', None)
        if port is None:
            return None
        group = self.protocol.NOTE_GROUPS[track]
        for index in range(128):
            self.protocol.request_note(track, index)
            deadline = time.time() + timeout
            reply = None
            while reply is None and time.time() < deadline:
                for msg in port.iter_pending():
                    d = list(msg.data) if msg.type == 'sysex' else []
                    if len(d) >= 8 and d[0] == 0x43 and d[5:8] == [0x75, group, index]:
                        reply = d[8:]
                    else:
                        self.handle_seqtrak_message(msg)
                time.sleep(0.002)
            if reply is None:
                return None
            if len(reply) < 8:
                return index
        return 128

    def _request_seqtrak_state(self):
        """Read everything the Push shows from the Seqtrak (power-on, project load)."""
        for track in range(1, 12):
            self.protocol.request_preset_name(track)
            self.protocol.request_parameter([0x30, 0x50 + track - 1, 0x0F])
        self.protocol.request_parameter(Address.TEMPO)
        self.protocol.request_parameter(Address.MASTER_VOLUME)
        self.protocol.request_parameter(Address.PATTERN_SELECT_MODE)
        self.protocol.request_parameter(Address.SWING)
        self.protocol.request_parameter([0x30, 0x40, 0x68])
        self.protocol.request_parameter([0x00, 0x00, 0x25])  # metronome
        self._request_song()
        for addr in self._cc_for_sysex:
            self.protocol.request_parameter(list(addr))
        for slot in range(8):
            for pad in range(7):
                self.protocol.request_parameter([0x30, 0x4D, slot * 16 + pad])
        self.protocol.request_parameter(Address.SCALE)
        self.protocol.request_parameter(Address.KEY)
        for track in range(1, 12):
            self.protocol.request_parameter([0x30, 0x50 + track - 1, 0x29])
        for track in range(1, 12):
            for variation in range(6):
                self.protocol.request_parameter([0x30, 0x50 + track - 1, 0x16 + 2 * variation])
        for track in range(1, 8):
            self._request_drum_steps(track)
        self._request_sampler_notes()

    def _schedule_resync(self, full=False, delay=0.5):
        """Re-read the Seqtrak after `delay` s (debounced, so a burst of changes lands first)."""
        self._resync_full = self._resync_full or full
        self._resync_at = time.time() + delay

    def _process_resync(self):
        if not self._resync_at or time.time() < self._resync_at:
            return
        self._resync_at = 0.0
        if self._resync_full:
            print("Seqtrak: re-reading project")
            self._request_seqtrak_state()
        else:
            for track in range(1, 8):
                self._request_drum_steps(track)
            self._request_sampler_notes()
        self._resync_full = False

    def _reread_all_steps(self):
        """Re-read every drum track and the sampler list (after recording)."""
        for track in range(1, 8):
            self._request_drum_steps(track, self._track_steps(track))
        self._request_sampler_notes()

    def _process_record_reads(self):
        """While recording, re-read the steps on show about once a second."""
        if not (self.is_recording and self.is_playing):
            return
        now = time.time()
        if now < self._record_reread_at or self._step_read_queue:
            return
        self._record_reread_at = now + 1.0
        if self.current_pad_mode == PadMode.SAMPLER:
            self._request_sampler_notes()
        elif self.current_pad_mode == PadMode.DRUM:
            self._request_drum_steps(self.selected_drum_track,
                                     self._track_steps(self.selected_drum_track))

    def _request_drum_steps(self, track, count=128):
        """Queue a read of the first `count` steps (default all 128) of a drum track's current pattern.

        Request 70 [0x40+track-1] [step]; the Seqtrak answers with the step's
        event data, or with no data if the step is empty. Sent throttled from
        the main loop so the USB MIDI link isn't flooded.
        """
        if not 1 <= track <= 7:
            return
        addrs = [[0x70, 0x40 + track - 1, step] for step in range(count)]
        self._step_read_queue = [a for a in self._step_read_queue if a[1] != 0x40 + track - 1]
        self._step_read_queue.extend(addrs)

    def _process_step_reads(self):
        """Send queued step/note reads, one every 3 ms; start due sampler re-reads."""
        now = time.time()
        if self._sampler_resync_at and now >= self._sampler_resync_at:
            self._sampler_resync_at = 0.0
            self._request_sampler_notes()
        if not self._step_read_queue:
            return
        if now - self._last_step_read_sent < 0.003:
            return
        self._last_step_read_sent = now
        self.protocol.request_parameter(self._step_read_queue.pop(0))

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

    # Length for a sampler step with no later step on its pad: let the sample ring
    # out (4 bars). The pad's next step chokes it anyway.
    SAMPLER_RING_OUT = 4 * 16 * 120

    def _sampler_ring_length(self, note, tick):
        """Ticks from `tick` up to just before the pad's next note (or the ring-out length)."""
        later = [t for t, n, _ in self.sampler_notes if n == note and t > tick]
        return min(later) - tick - 1 if later else self.SAMPLER_RING_OUT

    def _toggle_sampler_step(self, pad_index, step_index):
        """Toggle a sampler step (pad 0-6, step 0-127) on the Seqtrak.

        The sampler stores an ordered note list (see docs/Seqtrak/STEP-SEQUENCER.md):
        - add:    72 30 00 [tick_hi] [tick_lo] 00 [3C+pad] 64 00 [len_hi] [len_lo]
        - remove: 74 30 [index] 00, index from the mirror read with 75 30 [index]
        The Seqtrak stops a sample when its note ends, so each step rings until the
        pad's next step (or rings out if there is none). Removing a step re-extends
        the pad's previous step if it had been cut short at the removed one.
        The list is re-read shortly after every edit to keep indexes exact.
        """
        note = 0x3C + pad_index
        tick = step_index * 120
        matches = [i for i, (t, n, _) in enumerate(self.sampler_notes)
                   if n == note and round(t / 120) == step_index]

        if matches:
            for index in reversed(matches):  # highest first so lower indexes stay valid
                self.protocol.remove_note(11, index)
                self.sampler_notes.pop(index)
            # Re-extend the previous step on this pad if it stopped at the removed one
            earlier = [(i, t, length) for i, (t, n, length) in enumerate(self.sampler_notes)
                       if n == note and t < tick]
            if earlier:
                i, t, length = earlier[-1]
                if t + length >= tick - 1:
                    new_length = self._sampler_ring_length(note, t)
                    self.protocol.remove_note(11, i)
                    self.protocol.add_note(11, t, note, length=new_length)
                    self.sampler_notes[i] = (t, note, new_length)
            on = False
        else:
            # Shorten an earlier step on this pad that would ring past this one
            # (remove it and add it back), so the new step doesn't depend on how
            # the Seqtrak resolves the overlap.
            for i, (t, n, old) in enumerate(self.sampler_notes):
                if n == note and t < tick <= t + old:
                    self.protocol.remove_note(11, i)
                    self.protocol.add_note(11, t, n, length=tick - t - 1)
                    self.sampler_notes[i] = (t, n, tick - t - 1)
            length = self._sampler_ring_length(note, tick)
            self.protocol.add_note(11, tick, note, length=length)
            position = sum(1 for t, _, _ in self.sampler_notes if t <= tick)
            self.sampler_notes.insert(position, (tick, note, length))
            on = True

        self.sampler_step_states.setdefault(pad_index, [False] * 128)[step_index] = on
        self._schedule_sampler_resync()
        self.update_grid()
        print(f"  Sampler Step {step_index + 1} for Pad {pad_index + 1}: {'ON' if on else 'OFF'}")

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
            self.update_grid()  # show this pad's steps
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

    # Mute and solo. On the Seqtrak they are independent: any number of tracks can be muted
    # (CC 23 / 30 5p 29), but only ONE track can be soloed (CC 24 value = track, 30 40 68;
    # SEQTRAK app capture 110-02). Un-soloing brings the track's own mute back (guide §5.8.2).
    # self.track_muted / self.solo_track hold that; self.track_states is derived for the LEDs.

    def _refresh_mute_solo_view(self):
        self._update_mute_solo_leds()
        if self.current_mode == 'mixer':
            self._update_mixer_button_leds()
        else:
            self.update_grid()

    def _sync_track_states(self):
        for i in range(11):
            if self.solo_track == i + 1:
                self.track_states[i] = MuteState.SOLO
            else:
                self.track_states[i] = MuteState.MUTED if self.track_muted[i] else MuteState.UNMUTED

    def _set_mute(self, track, muted):
        self.track_muted[track - 1] = muted
        self.protocol.mute_track_cc(track, muted=muted)

    def _set_solo(self, track):
        """Solo one track (1-11), or none (0). Mutes are left alone."""
        if self.drum_bus_soloed and track:
            self._end_drum_bus_solo()
        self.solo_track = track
        self.protocol.solo_track_cc(track)

    def _toggle_track_mute(self, track):
        """Toggle track mute state: unmuted → muted → solo → unmuted."""
        track_name = Track.NAMES.get(track, f"Track {track}")
        if self.solo_track == track:
            self._set_solo(0)
        elif self.track_muted[track - 1]:
            self._set_mute(track, False)
            self._set_solo(track)
        else:
            self._set_mute(track, True)
        self._sync_track_states()
        self.update_grid()
        print(f"{track_name}: {['UNMUTED', 'MUTED', 'SOLO'][self.track_states[track - 1]]}")

    def _toggle_track_mute_simple(self, track):
        """Toggle track mute (muting a soloed track also ends the solo)."""
        track_name = MIXER_TRACK_ABBREV.get(track, f"T{track}")
        muted = not self.track_muted[track - 1]
        if muted and self.solo_track == track:
            self._set_solo(0)
        self._set_mute(track, muted)
        self._sync_track_states()
        self._update_mixer_button_leds()
        print(f"{track_name}: {'MUTED' if muted else 'UNMUTED'}")

    def _toggle_track_solo(self, track):
        """Solo this track (un-soloing any other), or un-solo it; its own mute comes back."""
        track_name = MIXER_TRACK_ABBREV.get(track, f"T{track}")
        self._set_solo(0 if self.solo_track == track else track)
        self._sync_track_states()
        self._update_mixer_button_leds()
        print(f"{track_name}: {'SOLO' if self.solo_track == track else 'UNSOLO'}")

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
            self._set_mute(track, self.drum_bus_muted)
        self._sync_track_states()
        self._update_mixer_button_leds()
        print(f"DRUM Bus: {'MUTED' if self.drum_bus_muted else 'UNMUTED'}")

    def _toggle_drum_bus_solo(self):
        """Solo the drum tracks together.

        The Seqtrak can only solo one track, so the bus solo mutes the other tracks
        (SYNTH 1/2, DX, SAMPLER) and un-soloing gives them back their own mute.
        """
        if self.drum_bus_soloed:
            self._end_drum_bus_solo()
        else:
            self._set_solo(0)
            self._drum_solo_saved_mutes = {t: self.track_muted[t - 1] for t in range(8, 12)}
            for track in range(8, 12):
                self._set_mute(track, True)
            self.drum_bus_soloed = True
        self._sync_track_states()
        self._update_mixer_button_leds()
        print(f"DRUM Bus: {'SOLO' if self.drum_bus_soloed else 'UNSOLO'}")

    def _end_drum_bus_solo(self):
        for track, muted in self._drum_solo_saved_mutes.items():
            self._set_mute(track, muted)
        self._drum_solo_saved_mutes = {}
        self.drum_bus_soloed = False

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
        self.track_preset_names[track] = self.patch_name  # keep cache in step with the change
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

        # Show cached name immediately (from Seqtrak, else bank/program lookup)
        self.patch_name = (self.track_preset_names.get(self.keyboard_track)
                           or self._get_track_preset_display(self.keyboard_track))

        # Inform Seqtrak of track selection and request this track's preset name
        self._send_track_select(self.keyboard_track)
        self.protocol.request_preset_name(self.keyboard_track)

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

        # Show cached name immediately (from Seqtrak, else bank/program lookup)
        self.patch_name = (self.track_preset_names.get(self.keyboard_track)
                           or self._get_track_preset_display(self.keyboard_track))

        # Inform Seqtrak of track selection and request this track's preset name
        self._send_track_select(self.keyboard_track)
        self.protocol.request_preset_name(self.keyboard_track)

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

        # Find ports. On the headless Pi the service may start before the Push or the Seqtrak
        # is plugged in (or switched on), so wait for both instead of exiting.
        print("Searching for MIDI ports...")
        reported = False
        while True:
            push_in_name, push_out_name = self.find_push_ports()
            seqtrak_name = find_seqtrak_port()
            if push_out_name and seqtrak_name:
                break
            if not reported:
                missing = [n for n, ok in (("Ableton Push", push_out_name), ("Seqtrak", seqtrak_name)) if not ok]
                print(f"\nWaiting for: {', '.join(missing)} (checking every 2 s)")
                print("Available MIDI outputs:")
                for name in mido.get_output_names():
                    print(f"  - {name}")
                reported = True
            time.sleep(2)

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
            # Every other button that does something, so it can be found in the dark
            for name in ('session', 'shift', 'delete', 'undo', 'double_loop', 'duplicate', 'metronome', 'mute', 'solo',
                         'user', 'record', 'repeat', 'accent'):
                self.set_button_led(BUTTONS[name], LED_DIM)

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
            self._send_track_select(self.keyboard_track)
            self.patch_name = self._get_track_preset_display(self.keyboard_track)
            self.update_display()

            # Request current state from Seqtrak
            self._request_seqtrak_state()

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

                    # Send queued step reads (throttled)
                    self._process_timed_sends()
                    self._process_resync()
                    self._process_record_reads()
                    self._process_step_reads()

                    # Process note repeat for held pads
                    self._process_note_repeat()

                    # Process arpeggiator
                    self._process_arpeggiator()

                    # Move the step cursor
                    self._process_playhead()

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
