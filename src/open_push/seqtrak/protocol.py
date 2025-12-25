"""
Seqtrak SysEx Protocol
======================
Decoded addresses and helper functions for Yamaha Seqtrak communication.

IMPORTANT: Each track has its own MIDI channel (1-11).
Many parameters can be controlled via standard MIDI CC on the track's channel,
which is simpler than SysEx for real-time control.

MIDI Channel Mapping (Official):
    Channel 1:  KICK
    Channel 2:  SNARE
    Channel 3:  CLAP
    Channel 4:  HAT 1
    Channel 5:  HAT 2
    Channel 6:  PERC 1
    Channel 7:  PERC 2
    Channel 8:  SYNTH 1
    Channel 9:  SYNTH 2
    Channel 10: DX
    Channel 11: SAMPLER

SysEx Format:
    F0 43 1n 7F 1C 0C [addr_h] [addr_m] [addr_l] [data...] F7
    │  │  │  │  │  │  └──────────────────────────┴── Address + Data
    │  │  │  │  │  └── Model ID (Seqtrak = 0C)
    │  │  │  │  └── Sub-group
    │  │  │  └── Category (7F = bulk/system)
    │  │  └── Device number (1n where n=0-F, typically 10)
    │  └── Manufacturer ID (Yamaha = 43)
    └── SysEx start

Transport uses MIDI Realtime messages (not SysEx):
    - Start: FA
    - Stop: FC
    - Continue: FB
"""

import mido

# Yamaha SysEx header (without F0, mido adds that)
SYSEX_HEADER = [0x43, 0x10, 0x7F, 0x1C, 0x0C]


# =============================================================================
# TRACK DEFINITIONS (Official from MIDI guide)
# =============================================================================

class Track:
    """Track numbers and names. MIDI channel = track number."""
    KICK = 1
    SNARE = 2
    CLAP = 3
    HAT1 = 4
    HAT2 = 5
    PERC1 = 6
    PERC2 = 7
    SYNTH1 = 8
    SYNTH2 = 9
    DX = 10
    SAMPLER = 11

    NAMES = {
        1: 'KICK', 2: 'SNARE', 3: 'CLAP', 4: 'HAT 1', 5: 'HAT 2',
        6: 'PERC 1', 7: 'PERC 2', 8: 'SYNTH 1', 9: 'SYNTH 2',
        10: 'DX', 11: 'SAMPLER'
    }

    # Track types
    DRUM_TRACKS = [1, 2, 3, 4, 5, 6, 7]      # Channels 1-7
    SYNTH_TRACKS = [8, 9, 10]                 # Channels 8-10
    SAMPLER_TRACKS = [11]                     # Channel 11


# =============================================================================
# MIDI CC PARAMETERS (Official from MIDI guide - simpler than SysEx!)
# =============================================================================

class CC:
    """
    MIDI Control Change numbers for Seqtrak.
    Send on the track's MIDI channel (1-11).
    """
    # Sound Design (all tracks)
    VOLUME = 7              # 0-127
    PAN = 10                # 1-127 (64 = center)
    ATTACK = 73             # 0-127
    DECAY_RELEASE = 75      # 0-127
    FILTER_CUTOFF = 74      # 0-127
    FILTER_RESONANCE = 71   # 0-127
    REVERB_SEND = 91        # 0-127
    DELAY_SEND = 94         # 0-127
    EQ_HIGH = 20            # 40-88 (64 = center)
    EQ_LOW = 21             # 40-88 (64 = center)
    EXPRESSION = 11         # 0-127

    # Drum only (channels 1-7)
    DRUM_PITCH = 25         # 40-88 (64 = center)

    # Synth/DX only (channels 8-10)
    MONO_POLY_CHORD = 26    # 0=MONO, 1=POLY, 2=CHORD
    PORTAMENTO_TIME = 5     # 0-127 (0=OFF)
    PORTAMENTO_SW = 65      # 0=OFF, 1=ON
    ARP_TYPE = 27           # 0-16 (0=OFF)
    ARP_GATE = 28           # 0-127
    ARP_SPEED = 29          # 0-9

    # DX only (channel 10)
    FM_ALGORITHM = 116      # 0-127
    FM_MOD_AMOUNT = 117     # 0-127
    FM_MOD_FREQ = 118       # 0-127
    FM_MOD_FEEDBACK = 119   # 0-127

    # Mute/Solo (RECEIVE ONLY - we can send to Seqtrak!)
    MUTE = 23               # 0-63=OFF, 64-127=ON
    SOLO = 24               # 0=OFF, 1-11=track number to solo

    # Effects (channel 1 for master effects)
    MASTER_FX1_P1 = 102
    MASTER_FX1_P2 = 103
    MASTER_FX1_P3 = 104
    MASTER_FX2 = 105
    MASTER_FX3 = 106
    SINGLE_FX_P1 = 107      # Per-track (channel 1-11)
    SINGLE_FX_P2 = 108
    SINGLE_FX_P3 = 109
    REVERB_P1 = 110         # Channel 1
    REVERB_P2 = 111
    REVERB_P3 = 112
    DELAY_P1 = 113          # Channel 1
    DELAY_P2 = 114
    DELAY_P3 = 115

# =============================================================================
# PARAMETER ADDRESSES
# =============================================================================

# Global Parameters
class Address:
    """Seqtrak SysEx address constants."""

    # Master
    MASTER_VOLUME = [0x00, 0x00, 0x00]  # 0x00-0x7F

    # Tempo/Transport
    TEMPO = [0x30, 0x40, 0x76]          # 2 bytes, 5-300 BPM
    PATTERN_STEPS = [0x30, 0x40, 0x7A]  # 2 bytes, 1-128
    SWING = [0x30, 0x40, 0x7C]          # 2 bytes, increments by 2

    # Transport State (for SysEx control/feedback)
    PLAY_STATE = [0x01, 0x10, 0x20]     # 01=Playing, 00=Stopped
    RECORD_STATE = [0x01, 0x10, 0x21]   # 01=Recording, 00=Stopped
    PRESET_NAME = [0x01, 0x10, 0x35]    # ASCII preset name (up to 16 chars)

    # Scale/Key
    SCALE = [0x30, 0x40, 0x7E]          # 0-7
    KEY = [0x30, 0x40, 0x7F]            # 0x40-0x4B (C-B)

    # Track Base (add track number 0-10 to middle byte)
    # Example: Track 1 mute = [0x30, 0x50, 0x0F]
    #          Track 5 mute = [0x30, 0x54, 0x0F]
    TRACK_BASE = 0x50
    TRACK_MUTE_OFFSET = 0x0F            # [0x30, 0x5x, 0x0F] where x = track
    TRACK_OCTAVE_OFFSET = 0x0C          # [0x30, 0x5x, 0x0C]

    # Pattern/Variation
    TRACK_SELECT = [0x01, 0x10, 0x27]   # 0x00-0x0A (tracks 1-11)
    PATTERN_VAR_A = [0x01, 0x10, 0x28]  # 0x01-0x06
    PATTERN_VAR_B = [0x01, 0x10, 0x2C]  # 0x01-0x06
    PATTERN_BANK = [0x01, 0x18, 0x30]   # 0x00-0x03 (banks 1-4)
    DISPLAY_MODE = [0x01, 0x10, 0x2E]   # UI state

    # Effects
    REVERB_TYPE = [0x30, 0x41, 0x00]
    REVERB_ON = [0x30, 0x41, 0x46]
    DELAY_TYPE = [0x30, 0x42, 0x00]
    DELAY_ON = [0x30, 0x42, 0x47]
    MASTER_FX_1 = [0x30, 0x43, 0x00]
    MASTER_FX_2 = [0x30, 0x44, 0x00]
    MASTER_FX_3 = [0x30, 0x45, 0x00]
    MASTER_FX_4 = [0x30, 0x46, 0x00]


# =============================================================================
# VALUE CONSTANTS
# =============================================================================

# Mute states
class MuteState:
    UNMUTED = 0
    MUTED = 1
    SOLO = 2


# Scale types
class Scale:
    CHROMATIC = 0
    MAJOR = 1
    MINOR = 2
    HARMONIC_MINOR = 3
    DORIAN = 4
    MIXOLYDIAN = 5
    PENTATONIC_MAJOR = 6
    PENTATONIC_MINOR = 7

    NAMES = [
        'Chromatic', 'Major', 'Minor', 'Harm Minor',
        'Dorian', 'Mixolydian', 'Pent Maj', 'Pent Min'
    ]


# Key values (0x40 = C, 0x4B = B)
class Key:
    C = 0x40
    CS = 0x41
    D = 0x42
    DS = 0x43
    E = 0x44
    F = 0x45
    FS = 0x46
    G = 0x47
    GS = 0x48
    A = 0x49
    AS = 0x4A
    B = 0x4B

    NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

    @classmethod
    def from_semitone(cls, semitone):
        """Convert semitone (0-11) to Seqtrak key value."""
        return cls.C + (semitone % 12)

    @classmethod
    def to_semitone(cls, key_value):
        """Convert Seqtrak key value to semitone (0-11)."""
        return (key_value - cls.C) % 12


# =============================================================================
# PROTOCOL CLASS
# =============================================================================

class SeqtrakProtocol:
    """
    Handles Seqtrak SysEx encoding/decoding and transport control.

    Usage:
        protocol = SeqtrakProtocol(seqtrak_port)
        protocol.start()
        protocol.stop()
        protocol.set_tempo(120)
        protocol.mute_track(3, MuteState.MUTED)
    """

    def __init__(self, port):
        """
        Initialize with a mido output port.

        Args:
            port: mido output port connected to Seqtrak
        """
        self.port = port

    # -------------------------------------------------------------------------
    # Transport (MIDI Realtime)
    # -------------------------------------------------------------------------

    def start(self):
        """Start playback (MIDI Realtime Start)."""
        self.port.send(mido.Message('start'))

    def stop(self):
        """Stop playback (MIDI Realtime Stop)."""
        self.port.send(mido.Message('stop'))

    def continue_playback(self):
        """Continue from current position (MIDI Realtime Continue)."""
        self.port.send(mido.Message('continue'))

    def tap_tempo(self):
        """Tap tempo - calculates BPM from tap intervals and sets tempo.

        Uses a rolling window of up to 4 taps. Resets if more than 2 seconds
        between taps (assumes user started a new tap sequence).

        Returns:
            The calculated BPM if enough taps, or None if still collecting.
        """
        import time

        current_time = time.time()

        # Initialize tap history if needed
        if not hasattr(self, '_tap_times'):
            self._tap_times = []

        # Reset if more than 2 seconds since last tap
        if self._tap_times and (current_time - self._tap_times[-1]) > 2.0:
            self._tap_times = []

        # Add current tap
        self._tap_times.append(current_time)

        # Keep only last 4 taps
        if len(self._tap_times) > 4:
            self._tap_times = self._tap_times[-4:]

        # Need at least 2 taps to calculate BPM
        if len(self._tap_times) < 2:
            return None

        # Calculate average interval
        intervals = []
        for i in range(1, len(self._tap_times)):
            intervals.append(self._tap_times[i] - self._tap_times[i - 1])

        avg_interval = sum(intervals) / len(intervals)

        # Convert to BPM (60 seconds / interval)
        bpm = int(round(60.0 / avg_interval))

        # Clamp to valid range
        bpm = max(5, min(300, bpm))

        # Set the tempo
        self.set_tempo(bpm)

        return bpm

    def record(self, enable=True):
        """
        Start/stop recording via SysEx.

        Sends: F0 43 10 7F 1C 0C 01 10 21 [01/00] F7
        """
        self._send_sysex(Address.RECORD_STATE, [0x01 if enable else 0x00])

    def request_parameter(self, address):
        """
        Request a parameter value from Seqtrak.

        Format: F0 43 3n 7F 1C 0C [addr_h] [addr_m] [addr_l] F7
        (0x30 for Parameter Request per MIDI Data Format doc)

        Args:
            address: 3-byte address list [h, m, l]
        """
        # Parameter Request header uses 0x30 instead of 0x10
        request_header = [0x43, 0x30, 0x7F, 0x1C, 0x0C]
        sysex_data = request_header + address
        self.port.send(mido.Message('sysex', data=sysex_data))

    # -------------------------------------------------------------------------
    # SysEx Helpers
    # -------------------------------------------------------------------------

    def _send_sysex(self, address, data):
        """
        Send a SysEx parameter change.

        Args:
            address: 3-byte address list [h, m, l]
            data: data bytes list
        """
        sysex_data = SYSEX_HEADER + address + data
        self.port.send(mido.Message('sysex', data=sysex_data))

    def send_parameter(self, address, data):
        """
        Public method to send a SysEx parameter change.

        Args:
            address: 3-byte address list [h, m, l]
            data: data bytes list
        """
        self._send_sysex(address, data)

    # -------------------------------------------------------------------------
    # Global Parameters
    # -------------------------------------------------------------------------

    def set_master_volume(self, volume):
        """Set master volume (0-127)."""
        volume = max(0, min(127, volume))
        self._send_sysex(Address.MASTER_VOLUME, [volume])

    def set_tempo(self, bpm):
        """Set tempo in BPM (5-300)."""
        bpm = max(5, min(300, bpm))
        # 2-byte format: MSB, LSB
        msb = (bpm >> 7) & 0x7F
        lsb = bpm & 0x7F
        self._send_sysex(Address.TEMPO, [msb, lsb])

    def set_swing(self, amount):
        """Set swing amount (0-28, even numbers only)."""
        amount = max(0, min(28, amount))
        amount = (amount // 2) * 2  # Force even
        self._send_sysex(Address.SWING, [0x01, amount])

    # -------------------------------------------------------------------------
    # Scale/Key
    # -------------------------------------------------------------------------

    def set_scale(self, scale_type):
        """Set scale type (0-7, use Scale constants)."""
        scale_type = max(0, min(7, scale_type))
        self._send_sysex(Address.SCALE, [scale_type])

    def set_key(self, key_value):
        """Set key (0x40-0x4B or use Key constants)."""
        self._send_sysex(Address.KEY, [key_value])

    def set_key_from_semitone(self, semitone):
        """Set key from semitone (0=C, 1=C#, ... 11=B)."""
        key_value = Key.from_semitone(semitone)
        self.set_key(key_value)

    # -------------------------------------------------------------------------
    # Track Control
    # -------------------------------------------------------------------------

    def _track_address(self, track, offset):
        """Build track-specific address."""
        # Track 1-11 maps to 0x50-0x5A
        track_byte = Address.TRACK_BASE + (track - 1)
        return [0x30, track_byte, offset]

    def set_track_mute(self, track, state):
        """
        Set track mute state.

        Args:
            track: Track number (1-11)
            state: MuteState.UNMUTED, MUTED, or SOLO
        """
        if not 1 <= track <= 11:
            return
        address = self._track_address(track, Address.TRACK_MUTE_OFFSET)
        self._send_sysex(address, [state])

    def mute_track(self, track):
        """Mute a track."""
        self.set_track_mute(track, MuteState.MUTED)

    def unmute_track(self, track):
        """Unmute a track."""
        self.set_track_mute(track, MuteState.UNMUTED)

    def solo_track(self, track):
        """Solo a track."""
        self.set_track_mute(track, MuteState.SOLO)

    def set_track_octave(self, track, octave):
        """
        Set track octave.

        Args:
            track: Track number (1-11)
            octave: Octave offset (-3 to +2), 0x40 = center
        """
        if not 1 <= track <= 11:
            return
        # Convert offset to value: -3=0x3D, -2=0x3E, -1=0x3F, 0=0x40, +1=0x41, +2=0x42
        value = 0x40 + octave
        value = max(0x3D, min(0x42, value))
        address = self._track_address(track, Address.TRACK_OCTAVE_OFFSET)
        self._send_sysex(address, [value])

    def select_track(self, track):
        """Select a track (1-11)."""
        if not 1 <= track <= 11:
            return
        self._send_sysex(Address.TRACK_SELECT, [track - 1])

    # -------------------------------------------------------------------------
    # Pattern Control
    # -------------------------------------------------------------------------

    def select_variation(self, variation):
        """Select pattern variation (1-6)."""
        if not 1 <= variation <= 6:
            return
        # Seqtrak uses paired messages for variation
        self._send_sysex(Address.PATTERN_VAR_A, [variation])
        self._send_sysex(Address.PATTERN_VAR_B, [variation])

    def select_bank(self, bank):
        """Select pattern bank (1-4)."""
        if not 1 <= bank <= 4:
            return
        self._send_sysex(Address.PATTERN_BANK, [bank - 1])

    # -------------------------------------------------------------------------
    # CC-Based Control (Official MIDI - simpler than SysEx for real-time!)
    # -------------------------------------------------------------------------

    def _send_cc(self, channel, cc, value):
        """Send a Control Change message to a specific channel."""
        # mido uses 0-indexed channels
        msg = mido.Message('control_change', channel=channel - 1, control=cc, value=value)
        self.port.send(msg)

    def mute_track_cc(self, track, muted=True):
        """
        Mute/unmute a track using MIDI CC (official method).

        Args:
            track: Track number (1-11) = MIDI channel
            muted: True to mute, False to unmute
        """
        if not 1 <= track <= 11:
            return
        value = 127 if muted else 0
        self._send_cc(track, CC.MUTE, value)

    def solo_track_cc(self, track):
        """
        Solo a track using MIDI CC (official method).
        Send to any channel, value = track number to solo.

        Args:
            track: Track number (1-11) to solo, or 0 to unsolo
        """
        if not 0 <= track <= 11:
            return
        # Solo CC can be sent on any channel, value indicates which track
        self._send_cc(1, CC.SOLO, track)

    def set_track_volume(self, track, volume):
        """Set track volume (0-127)."""
        if not 1 <= track <= 11:
            return
        volume = max(0, min(127, volume))
        self._send_cc(track, CC.VOLUME, volume)

    def set_track_pan(self, track, pan):
        """Set track pan (1-127, 64=center)."""
        if not 1 <= track <= 11:
            return
        pan = max(1, min(127, pan))
        self._send_cc(track, CC.PAN, pan)

    def set_track_filter(self, track, cutoff, resonance=None):
        """Set track filter cutoff and optionally resonance."""
        if not 1 <= track <= 11:
            return
        cutoff = max(0, min(127, cutoff))
        self._send_cc(track, CC.FILTER_CUTOFF, cutoff)
        if resonance is not None:
            resonance = max(0, min(127, resonance))
            self._send_cc(track, CC.FILTER_RESONANCE, resonance)

    def set_track_reverb(self, track, amount):
        """Set track reverb send (0-127)."""
        if not 1 <= track <= 11:
            return
        amount = max(0, min(127, amount))
        self._send_cc(track, CC.REVERB_SEND, amount)

    def set_track_delay(self, track, amount):
        """Set track delay send (0-127)."""
        if not 1 <= track <= 11:
            return
        amount = max(0, min(127, amount))
        self._send_cc(track, CC.DELAY_SEND, amount)

    def set_drum_pitch(self, track, pitch):
        """Set drum pitch (40-88, 64=center). Only for drum tracks 1-7."""
        if not 1 <= track <= 7:
            return
        pitch = max(40, min(88, pitch))
        self._send_cc(track, CC.DRUM_PITCH, pitch)

    def set_arp_type(self, track, arp_type):
        """Set arpeggiator type (0-16, 0=OFF). Only for synth tracks 8-10."""
        if not 8 <= track <= 10:
            return
        arp_type = max(0, min(16, arp_type))
        self._send_cc(track, CC.ARP_TYPE, arp_type)

    def trigger_note(self, track, note, velocity=100, channel=None):
        """
        Send a note to a track.

        Args:
            track: Track number (1-11)
            note: MIDI note number (0-127)
            velocity: Note velocity (0-127)
            channel: Override MIDI channel (default = track number)
        """
        if channel is None:
            channel = track
        if not 1 <= channel <= 11:
            return
        msg = mido.Message('note_on', channel=channel - 1, note=note, velocity=velocity)
        self.port.send(msg)

    def release_note(self, track, note, channel=None):
        """Send note off to a track."""
        if channel is None:
            channel = track
        if not 1 <= channel <= 11:
            return
        msg = mido.Message('note_off', channel=channel - 1, note=note, velocity=0)
        self.port.send(msg)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def find_seqtrak_port():
    """Find Seqtrak MIDI output port."""
    for name in mido.get_output_names():
        if 'Seqtrak' in name or 'SEQTRAK' in name:
            return name
        if 'seqtrak' in name.lower():
            return name
    return None


def parse_seqtrak_sysex(data):
    """
    Parse a Seqtrak SysEx message.

    Args:
        data: SysEx data bytes (from mido Message)

    Returns:
        dict with 'address' and 'data' keys, or None if not valid
    """
    if len(data) < 9:
        return None
    if data[0] != 0x43:  # Not Yamaha
        return None
    if data[5] != 0x0C:  # Not Seqtrak
        return None

    return {
        'address': list(data[6:9]),
        'data': list(data[9:]),
        'address_hex': f"{data[6]:02X} {data[7]:02X} {data[8]:02X}",
        'data_hex': ' '.join(f"{b:02X}" for b in data[9:])
    }
