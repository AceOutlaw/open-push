#!/usr/bin/env python3
"""
MIDI-Only Bridge for Ableton Push
==================================

A lightweight MIDI controller bridge that outputs pure MIDI
(notes, CCs, transport) without hardware-specific protocols.

Architecture follows SeqTrak patterns:
- Pad grid ALWAYS active for notes (independent of encoder bank)
- Encoder banks switchable via buttons (Volume, Pan, Filter, etc.)
- Scale selection is an OVERLAY, not a separate mode
- Settings accessible via Shift+User

Designed for Pi Zero 2W deployment with outputs to:
- USB MIDI gadget (iPad)
- External USB MIDI devices
- Bluetooth MIDI (wireless)

Usage:
    python -m open_push.midi.app
"""

import mido
import time
import sys
import os
from typing import Optional, Dict, List, Callable

# Ensure imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from open_push.midi.push_hardware import (
    PushHardware,
    BUTTON_CC, CC_TO_BUTTON,
    ENCODER_CC, CC_TO_ENCODER,
    COLORS, color_value,
    PAD_NOTE_MIN, PAD_NOTE_MAX,
    is_pad_note, note_to_pad,
)
from open_push.midi.config import MIDIConfig

# Import music modules
from open_push.music.layout import IsomorphicLayout
from open_push.music.scales import SCALE_NAMES, SCALE_DISPLAY_NAMES, get_scale_display_name

# =============================================================================
# SCALE MODE BUTTON MAPPINGS (From SeqTrak)
# =============================================================================

# Root note button CCs - chromatic ascending layout
ROOT_UPPER_BUTTONS = [21, 22, 23, 24, 25, 26]      # C, C#, D, D#, E, F
ROOT_LOWER_BUTTONS = [103, 104, 105, 106, 107, 108]  # F#, G, G#, A, A#, B
ROOT_UPPER_NOTES = [0, 1, 2, 3, 4, 5]              # C=0 through F=5
ROOT_LOWER_NOTES = [6, 7, 8, 9, 10, 11]            # F#=6 through B=11
ROOT_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Scale mode special buttons
SCALE_UP_CC = 20      # Upper left button - scroll scale up
SCALE_DOWN_CC = 102   # Lower left button - scroll scale down
IN_KEY_CC = 27        # Upper right button - In Key mode
CHROMAT_CC = 109      # Lower right button - Chromatic mode

# Note repeat subdivision rates (CC 36-43)
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

# LED brightness values for buttons
LED_ON = 127
LED_DIM = 1
UPPER_BRIGHT = 10
UPPER_DIM = 7
LOWER_BRIGHT = 13
LOWER_DIM = 11


# =============================================================================
# MIDI OUTPUT WRAPPER
# =============================================================================

class MIDIOutput:
    """
    MIDI output wrapper for sending notes, CCs, and transport.

    Abstracts the output destination (USB gadget, external device, etc.)
    Sends ONLY pure MIDI - no SysEx to external destinations.
    """

    def __init__(self, port=None):
        self.port = port
        self._active_notes: Dict[int, set] = {}  # channel -> set of active notes

    def set_port(self, port):
        """Set/change the output port."""
        self.port = port

    def send(self, msg: mido.Message):
        """Send a MIDI message."""
        if self.port:
            self.port.send(msg)

    def send_note_on(self, note: int, velocity: int, channel: int = 0):
        """Send note on."""
        if self.port:
            msg = mido.Message('note_on', note=note, velocity=velocity, channel=channel)
            self.port.send(msg)
            # Track active notes
            if channel not in self._active_notes:
                self._active_notes[channel] = set()
            self._active_notes[channel].add(note)

    def send_note_off(self, note: int, channel: int = 0, velocity: int = 0):
        """Send note off."""
        if self.port:
            msg = mido.Message('note_off', note=note, velocity=velocity, channel=channel)
            self.port.send(msg)
            # Remove from active notes
            if channel in self._active_notes:
                self._active_notes[channel].discard(note)

    def send_cc(self, cc: int, value: int, channel: int = 0):
        """Send control change."""
        if self.port:
            msg = mido.Message('control_change', control=cc, value=value, channel=channel)
            self.port.send(msg)

    def send_program_change(self, program: int, channel: int = 0):
        """Send program change."""
        if self.port:
            msg = mido.Message('program_change', program=program, channel=channel)
            self.port.send(msg)

    def send_pitchwheel(self, value: int, channel: int = 0):
        """Send pitch wheel (-8192 to 8191)."""
        if self.port:
            msg = mido.Message('pitchwheel', pitch=value, channel=channel)
            self.port.send(msg)

    def send_start(self):
        """Send MIDI Start (0xFA)."""
        if self.port:
            msg = mido.Message('start')
            self.port.send(msg)

    def send_stop(self):
        """Send MIDI Stop (0xFC)."""
        if self.port:
            msg = mido.Message('stop')
            self.port.send(msg)

    def send_continue(self):
        """Send MIDI Continue (0xFB)."""
        if self.port:
            msg = mido.Message('continue')
            self.port.send(msg)

    def send_all_notes_off(self, channel: int = None):
        """
        Send all notes off.

        Args:
            channel: Specific channel, or None for all channels
        """
        if not self.port:
            return

        if channel is not None:
            # Specific channel
            msg = mido.Message('control_change', control=123, value=0, channel=channel)
            self.port.send(msg)
            self._active_notes.pop(channel, None)
        else:
            # All channels
            for ch in range(16):
                msg = mido.Message('control_change', control=123, value=0, channel=ch)
                self.port.send(msg)
            self._active_notes.clear()

    def release_all_active(self):
        """Send note off for all currently active notes."""
        if not self.port:
            return

        for channel, notes in list(self._active_notes.items()):
            for note in list(notes):
                self.send_note_off(note, channel)
        self._active_notes.clear()


# =============================================================================
# MIDI BRIDGE
# =============================================================================

class MIDIBridge:
    """
    Main application class for the MIDI-only Push bridge.

    Architecture (matches SeqTrak pattern):
    - Pad grid ALWAYS active for notes (independent of encoder bank)
    - Encoder banks switchable via buttons (Volume, Pan, etc.)
    - Scale selection is an OVERLAY, not a separate mode
    - Settings accessible via Shift+User

    NO standalone "modes" - just:
    - Pad playing (always active)
    - Encoder banks (switchable)
    - Scale overlay (temporary, returns to previous state)
    - Settings menu (Shift+User)
    """

    def __init__(self, config: MIDIConfig = None):
        self.config = config or MIDIConfig()
        self.push = PushHardware()
        self.output = MIDIOutput()

        # State
        self.running = False
        self.shift_held = False
        self.is_playing = False
        self.is_recording = False

        # =================================================================
        # ISOMORPHIC LAYOUT (always active for pads)
        # =================================================================
        keyboard_cfg = self.config.keyboard_config
        self.layout = IsomorphicLayout()
        self.layout.set_scale(
            keyboard_cfg.get('default_root', 0),
            keyboard_cfg.get('default_scale', 'minor')
        )
        self.layout.set_in_key_mode(keyboard_cfg.get('in_key_mode', True))

        # Scale state
        self.scale_index = SCALE_NAMES.index(keyboard_cfg.get('default_scale', 'minor')) \
            if keyboard_cfg.get('default_scale', 'minor') in SCALE_NAMES else 0
        self.root_note = keyboard_cfg.get('default_root', 0)
        self.in_key_mode = keyboard_cfg.get('in_key_mode', True)

        # Octave offset
        self.octave_offset = keyboard_cfg.get('default_octave', 0)

        # Velocity curve
        self.velocity_curve = keyboard_cfg.get('velocity_curve', 1.0)
        self.velocity_min = keyboard_cfg.get('velocity_min', 1)
        self.velocity_max = keyboard_cfg.get('velocity_max', 127)

        # =================================================================
        # SCALE OVERLAY STATE (not a separate mode)
        # =================================================================
        self.scale_mode_active = False  # Scale overlay is showing

        # =================================================================
        # ENCODER BANK STATE
        # =================================================================
        self.encoder_bank = 0  # Current encoder bank (0=Volume, 1=Pan, etc.)
        self.encoder_values = [[64] * 8 for _ in range(self.config.num_encoder_banks)]

        # =================================================================
        # GLOBAL CONTROLS
        # =================================================================
        self.master_volume = 100
        self.accent_mode = False
        self.accent_velocity = self.config.accent_config.get('fixed_velocity', 127)
        self.tempo = 120.0  # BPM
        self.swing = 0  # 0-127
        self.tap_times: List[float] = []
        self.metronome_on = False

        # =================================================================
        # NOTE REPEAT STATE
        # =================================================================
        self.note_repeat_active = False
        self.note_repeat_rate = 0.25  # Default 1/16 note (beats)
        self.note_repeat_rate_index = 4  # Index into rates (1/16)
        self.note_repeat_rates = [1.0, 2/3, 0.5, 1/3, 0.25, 1/6, 0.125, 1/12]
        self.note_repeat_rate_names = ['1/4', '1/4t', '1/8', '1/8t', '1/16', '1/16t', '1/32', '1/32t']
        self.note_repeat_notes: Dict[int, tuple] = {}  # {pad_note: (midi_note, channel, last_trigger)}

        # =================================================================
        # PAD COLORS (configurable via config)
        # =================================================================
        self.pad_colors = self.config.pad_colors

        # =================================================================
        # LCD POPUP STATE
        # =================================================================
        self.lcd_popup_active = False
        self.lcd_popup_end_time = 0
        self.lcd_popup_line = 0

        # =================================================================
        # SETTINGS STATE
        # =================================================================
        self.settings_mode_active = False
        self.settings_category = 0  # Current settings category
        self.settings_categories = [
            {
                'name': 'Bluetooth',
                'items': [
                    {'name': 'BT Enable', 'type': 'bool', 'key': 'bt_enabled', 'value': False},
                    {'name': 'Advertise', 'type': 'bool', 'key': 'bt_advertising', 'value': False},
                ]
            },
            {
                'name': 'MIDI',
                'items': [
                    {'name': 'Channel', 'type': 'int', 'key': 'midi_channel', 'min': 1, 'max': 16, 'value': 1},
                    {'name': 'DrumCh', 'type': 'int', 'key': 'drum_channel', 'min': 1, 'max': 16, 'value': 10},
                ]
            },
            {
                'name': 'Velocity',
                'items': [
                    {'name': 'Curve', 'type': 'float', 'key': 'velocity_curve', 'min': 0.5, 'max': 2.0, 'step': 0.1, 'value': 1.0},
                    {'name': 'Min', 'type': 'int', 'key': 'velocity_min', 'min': 1, 'max': 127, 'value': 1},
                    {'name': 'Max', 'type': 'int', 'key': 'velocity_max', 'min': 1, 'max': 127, 'value': 127},
                    {'name': 'Accent', 'type': 'int', 'key': 'accent_velocity', 'min': 100, 'max': 127, 'value': 127},
                ]
            },
            {
                'name': 'Defaults',
                'items': [
                    {'name': 'Octave', 'type': 'int', 'key': 'default_octave', 'min': -2, 'max': 4, 'value': 2},
                    {'name': 'Root', 'type': 'select', 'key': 'default_root', 'options': ROOT_NAMES, 'value': 0},
                    {'name': 'Scale', 'type': 'select', 'key': 'default_scale', 'options': SCALE_NAMES[:12], 'value': 0},
                ]
            },
        ]
        self.settings_item = 0  # Current item within category

    # =========================================================================
    # OUTPUT SETUP
    # =========================================================================

    def find_output_port(self) -> Optional[str]:
        """Find MIDI output port based on config."""
        output_type = self.config.output_type
        device_name = self.config.output_device

        available = mido.get_output_names()

        if device_name:
            # Specific device requested
            for name in available:
                if device_name in name:
                    return name

        if output_type == 'usb_gadget':
            # Look for USB MIDI gadget
            for name in available:
                if 'f_midi' in name.lower() or 'gadget' in name.lower():
                    return name

        elif output_type == 'bluetooth':
            # Look for BLE-MIDI
            for name in available:
                if 'bluetooth' in name.lower() or 'ble' in name.lower():
                    return name

        # Auto-detect: use first non-Push port
        for name in available:
            if 'push' not in name.lower():
                return name

        return None

    # =========================================================================
    # GLOBAL CONTROL HANDLERS
    # =========================================================================

    def handle_global_controls(self, msg) -> bool:
        """
        Handle global controls that work in all modes.

        Returns:
            True if message was handled (don't pass to mode)
        """
        if msg.type != 'control_change':
            return False

        cc = msg.control
        value = msg.value

        # Shift button
        if cc == BUTTON_CC['shift']:
            self.shift_held = value > 0
            return True

        # Master volume (always active)
        if cc == ENCODER_CC['master_encoder']:
            delta = self.push.decode_relative_encoder(value)
            self.master_volume = max(0, min(127, self.master_volume + delta))
            global_cfg = self.config.global_controls.get('master_volume', {})
            if global_cfg.get('enabled', True):
                self.output.send_cc(
                    global_cfg.get('cc', 7),
                    self.master_volume,
                    global_cfg.get('channel', 0)
                )
            self._update_volume_display()
            return True

        # Tempo encoder
        if cc == ENCODER_CC['tempo_encoder']:
            delta = self.push.decode_relative_encoder(value)
            self.tempo = max(20.0, min(300.0, self.tempo + delta))
            tempo_cfg = self.config.global_controls.get('tempo_knob', {})
            if tempo_cfg.get('enabled', True):
                # Map tempo (20-300 BPM) to MIDI CC (0-127)
                tempo_cc = int((self.tempo - 20) / 280 * 127)
                self.output.send_cc(
                    tempo_cfg.get('cc', 80),
                    tempo_cc,
                    tempo_cfg.get('channel', 0)
                )
            self._update_tempo_display()
            return True

        # Swing encoder
        if cc == ENCODER_CC['swing_encoder']:
            delta = self.push.decode_relative_encoder(value)
            self.swing = max(0, min(127, self.swing + delta))
            swing_cfg = self.config.global_controls.get('swing_knob', {})
            if swing_cfg.get('enabled', True):
                self.output.send_cc(
                    swing_cfg.get('cc', 81),
                    self.swing,
                    swing_cfg.get('channel', 0)
                )
            self._update_swing_display()
            return True

        # Tap tempo
        if cc == BUTTON_CC['tap_tempo'] and value > 0:
            self._handle_tap_tempo()
            return True

        # Metronome
        if cc == BUTTON_CC['metronome'] and value > 0:
            self._handle_metronome()
            return True

        # Transport: Play
        if cc == BUTTON_CC['play'] and value > 0:
            self._handle_play()
            return True

        # Transport: Stop
        if cc == BUTTON_CC['stop'] and value > 0:
            self._handle_stop()
            return True

        # Transport: Record
        if cc == BUTTON_CC['record'] and value > 0:
            self._handle_record()
            return True

        # Accent toggle
        if cc == BUTTON_CC['accent'] and value > 0:
            self.accent_mode = not self.accent_mode
            self.push.set_button_color('accent', 'orange' if self.accent_mode else 'dim_white')
            print(f"Accent mode: {'ON' if self.accent_mode else 'OFF'}")
            return True

        # Note Repeat toggle
        if cc == BUTTON_CC['repeat'] and value > 0:
            self._toggle_note_repeat()
            return True

        # Note Repeat rate selection (CC 36-43 = subdivision buttons)
        if cc in NOTE_REPEAT_SUBDIVISIONS and value > 0:
            rate_name, rate_beats = NOTE_REPEAT_SUBDIVISIONS[cc]
            self.note_repeat_rate = rate_beats
            self.note_repeat_rate_index = list(NOTE_REPEAT_SUBDIVISIONS.keys()).index(cc)
            print(f"Note Repeat Rate: {rate_name}")
            # Show popup on LCD
            self._show_popup(f"Rate: {rate_name}", 1.0)
            return True

        # Octave up/down
        if cc == BUTTON_CC['octave_up'] and value > 0:
            if self.octave_offset < 4:
                self.octave_offset += 1
                self._update_octave_display()
            return True

        if cc == BUTTON_CC['octave_down'] and value > 0:
            if self.octave_offset > -2:
                self.octave_offset -= 1
                self._update_octave_display()
            return True

        # Scale button - toggle scale overlay
        if cc == BUTTON_CC.get('scale') and value > 0:
            self._toggle_scale_mode()
            return True

        # Encoder bank switching buttons
        if value > 0:
            if cc == BUTTON_CC.get('volume'):
                self._switch_encoder_bank(0, 'volume')
                return True
            elif cc == BUTTON_CC.get('pan_send'):
                self._switch_encoder_bank(1, 'pan_send')
                return True
            elif cc == BUTTON_CC.get('track'):
                self._switch_encoder_bank(2, 'track')
                return True
            elif cc == BUTTON_CC.get('device'):
                self._switch_encoder_bank(3, 'device')
                return True

        # Settings menu (Shift + User)
        if cc == BUTTON_CC.get('user') and value > 0 and self.shift_held:
            self._toggle_settings_mode()
            return True

        return False

    def _handle_play(self):
        """Handle play button."""
        transport_cfg = self.config.transport_config.get('play', {})
        if transport_cfg.get('type') == 'midi_start':
            self.output.send_start()
        elif transport_cfg.get('type') == 'cc':
            self.output.send_cc(transport_cfg.get('cc', 115), 127, transport_cfg.get('channel', 0))

        self.is_playing = True
        self.push.set_button_color('play', 'green')
        print("Transport: PLAY")

    def _handle_stop(self):
        """Handle stop button."""
        transport_cfg = self.config.transport_config.get('stop', {})
        if transport_cfg.get('type') == 'midi_stop':
            self.output.send_stop()
        elif transport_cfg.get('type') == 'cc':
            self.output.send_cc(transport_cfg.get('cc', 116), 127, transport_cfg.get('channel', 0))

        self.is_playing = False
        self.is_recording = False
        self.output.release_all_active()
        self.push.set_button_color('play', 'dim_white')
        self.push.set_button_color('record', 'dim_white')
        print("Transport: STOP")

    def _handle_record(self):
        """Handle record button."""
        self.is_recording = not self.is_recording
        transport_cfg = self.config.transport_config.get('record', {})
        if transport_cfg.get('type') == 'cc':
            self.output.send_cc(
                transport_cfg.get('cc', 117),
                127 if self.is_recording else 0,
                transport_cfg.get('channel', 0)
            )
        self.push.set_button_color('record', 'red' if self.is_recording else 'dim_white')
        print(f"Transport: RECORD {'ON' if self.is_recording else 'OFF'}")

    def _update_volume_display(self):
        """Update LCD to show master volume."""
        vol_str = f"Vol: {self.master_volume}"
        self.push.set_lcd_segment(4, 3, vol_str, 'right')

    def _update_octave_display(self):
        """Update octave button LEDs."""
        self.push.set_button_color('octave_up', 'white' if self.octave_offset > 0 else 'dim_white')
        self.push.set_button_color('octave_down', 'white' if self.octave_offset < 0 else 'dim_white')

    def _update_tempo_display(self):
        """Update LCD to show tempo."""
        # Show tempo in segment 0 of line 4
        tempo_str = f"{self.tempo:.1f} BPM"
        self.push.set_lcd_segment(4, 0, tempo_str, 'left')

    def _update_swing_display(self):
        """Update LCD to show swing."""
        # Show swing in segment 1 of line 4
        swing_pct = int(self.swing / 127 * 100)
        swing_str = f"Swing: {swing_pct}%"
        self.push.set_lcd_segment(4, 1, swing_str, 'left')

    def _handle_tap_tempo(self):
        """Handle tap tempo button press."""
        current_time = time.time()

        # Clear old taps (more than 2 seconds ago)
        self.tap_times = [t for t in self.tap_times if current_time - t < 2.0]

        # Add this tap
        self.tap_times.append(current_time)

        # Need at least 2 taps to calculate tempo
        if len(self.tap_times) >= 2:
            # Calculate average interval
            intervals = []
            for i in range(1, len(self.tap_times)):
                intervals.append(self.tap_times[i] - self.tap_times[i-1])
            avg_interval = sum(intervals) / len(intervals)

            # Convert to BPM
            if avg_interval > 0:
                self.tempo = max(20.0, min(300.0, 60.0 / avg_interval))
                self._update_tempo_display()

                # Send CC if enabled
                tempo_cfg = self.config.global_controls.get('tempo_knob', {})
                if tempo_cfg.get('enabled', True):
                    tempo_cc = int((self.tempo - 20) / 280 * 127)
                    self.output.send_cc(
                        tempo_cfg.get('cc', 80),
                        tempo_cc,
                        tempo_cfg.get('channel', 0)
                    )

        # Keep only last 8 taps
        if len(self.tap_times) > 8:
            self.tap_times = self.tap_times[-8:]

        # Visual feedback
        self.push.set_button_color('tap_tempo', 'white')
        print(f"Tap Tempo: {self.tempo:.1f} BPM")

    def _handle_metronome(self):
        """Handle metronome button press."""
        self.metronome_on = not self.metronome_on

        # Send CC
        transport_cfg = self.config.transport_config.get('metronome', {})
        if transport_cfg.get('type') == 'cc':
            self.output.send_cc(
                transport_cfg.get('cc', 83),
                127 if self.metronome_on else 0,
                transport_cfg.get('channel', 0)
            )

        self.push.set_button_color('metronome', 'green' if self.metronome_on else 'dim_white')
        print(f"Metronome: {'ON' if self.metronome_on else 'OFF'}")

    # =========================================================================
    # NOTE REPEAT
    # =========================================================================

    def _toggle_note_repeat(self):
        """Toggle note repeat mode on/off."""
        self.note_repeat_active = not self.note_repeat_active

        if self.note_repeat_active:
            self.push.set_button_color('repeat', 'green')
            rate_name = self.note_repeat_rate_names[self.note_repeat_rate_index]
            print(f"Note Repeat: ON ({rate_name})")
        else:
            self.push.set_button_color('repeat', 'dim_white')
            # Release all repeating notes
            self._stop_all_note_repeats()
            print("Note Repeat: OFF")

    def start_note_repeat(self, pad_note: int, midi_note: int, channel: int):
        """
        Start repeating a note.

        Called by modes when a pad is pressed while note repeat is active.
        """
        if self.note_repeat_active:
            self.note_repeat_notes[pad_note] = (midi_note, channel, time.time())

    def stop_note_repeat(self, pad_note: int):
        """
        Stop repeating a note.

        Called by modes when a pad is released.
        """
        if pad_note in self.note_repeat_notes:
            del self.note_repeat_notes[pad_note]

    def _stop_all_note_repeats(self):
        """Stop all repeating notes."""
        self.note_repeat_notes.clear()

    def _process_note_repeat(self):
        """Process note repeat in main loop."""
        if not self.note_repeat_active or not self.note_repeat_notes:
            return

        current_time = time.time()
        seconds_per_beat = 60.0 / self.tempo
        interval = seconds_per_beat * self.note_repeat_rate

        for pad_note, (midi_note, channel, last_trigger) in list(self.note_repeat_notes.items()):
            if current_time - last_trigger >= interval:
                # Apply accent if enabled
                velocity = self.accent_velocity if self.accent_mode else 100

                # Send note off then on for retrigger
                self.output.send_note_off(midi_note, channel)
                self.output.send_note_on(midi_note, velocity, channel)

                # Update last trigger time
                self.note_repeat_notes[pad_note] = (midi_note, channel, current_time)

    def set_note_repeat_rate(self, index: int):
        """Set note repeat rate by index."""
        if 0 <= index < len(self.note_repeat_rates):
            self.note_repeat_rate_index = index
            self.note_repeat_rate = self.note_repeat_rates[index]
            print(f"Note Repeat Rate: {self.note_repeat_rate_names[index]}")

    def next_note_repeat_rate(self):
        """Cycle to next note repeat rate."""
        self.set_note_repeat_rate((self.note_repeat_rate_index + 1) % len(self.note_repeat_rates))

    # =========================================================================
    # SCALE OVERLAY (Ported from SeqTrak)
    # =========================================================================

    def _toggle_scale_mode(self):
        """Toggle scale selection overlay on/off."""
        if self.scale_mode_active:
            self._exit_scale_mode()
        else:
            self._enter_scale_mode()

    def _enter_scale_mode(self):
        """Enter scale selection overlay (temporary, returns to previous state)."""
        if self.scale_mode_active:
            return

        self.scale_mode_active = True
        print("Entering Scale mode")
        self.push.set_button_color('scale', 'white')
        self._update_scale_button_leds()
        self._update_scale_display()

    def _exit_scale_mode(self):
        """Exit scale selection overlay."""
        if not self.scale_mode_active:
            return

        print(f"Exiting Scale mode -> {ROOT_NAMES[self.root_note]} {get_scale_display_name(SCALE_NAMES[self.scale_index])}")

        # Clear scale buttons
        for cc in ROOT_UPPER_BUTTONS + ROOT_LOWER_BUTTONS + [SCALE_UP_CC, SCALE_DOWN_CC, IN_KEY_CC, CHROMAT_CC]:
            self.push.set_button_led(cc, 0)

        self.scale_mode_active = False
        self.push.set_button_color('scale', 'dim_white')
        self._update_main_display()
        self._update_pad_grid()

    def _update_scale_button_leds(self):
        """Update button LEDs for scale selection overlay."""
        if not self.scale_mode_active:
            return

        at_top = self.scale_index == 0
        at_bottom = self.scale_index >= len(SCALE_NAMES) - 1

        # Scale scroll buttons
        self.push.set_button_led(SCALE_UP_CC, UPPER_DIM if at_top else UPPER_BRIGHT)
        self.push.set_button_led(SCALE_DOWN_CC, LOWER_DIM if at_bottom else LOWER_BRIGHT)

        # Root note buttons - highlight current root
        for i, cc in enumerate(ROOT_UPPER_BUTTONS):
            root_val = ROOT_UPPER_NOTES[i]
            self.push.set_button_led(cc, UPPER_BRIGHT if root_val == self.root_note else UPPER_DIM)

        for i, cc in enumerate(ROOT_LOWER_BUTTONS):
            root_val = ROOT_LOWER_NOTES[i]
            self.push.set_button_led(cc, LOWER_BRIGHT if root_val == self.root_note else LOWER_DIM)

        # In-key/Chromatic toggle
        self.push.set_button_led(IN_KEY_CC, UPPER_BRIGHT if self.in_key_mode else UPPER_DIM)
        self.push.set_button_led(CHROMAT_CC, LOWER_BRIGHT if not self.in_key_mode else LOWER_DIM)

    def _apply_scale_changes(self):
        """Apply current scale settings to layout."""
        self.layout.set_scale(self.root_note, SCALE_NAMES[self.scale_index])
        self.layout.set_in_key_mode(self.in_key_mode)
        self._update_pad_grid()

    def _scroll_scale(self, direction: int):
        """Scroll through scale list (direction: -1=up, 1=down)."""
        total_scales = len(SCALE_NAMES)
        new_index = max(0, min(total_scales - 1, self.scale_index + direction))

        if new_index != self.scale_index:
            self.scale_index = new_index
            print(f"  Scale: {get_scale_display_name(SCALE_NAMES[self.scale_index])}")
            self._apply_scale_changes()
            self._update_scale_display()
            self._update_scale_button_leds()

    def _handle_scale_mode_cc(self, cc: int, value: int) -> bool:
        """Handle CC in scale mode. Returns True if handled."""
        if not self.scale_mode_active:
            return False

        # Only handle button presses
        if value == 0:
            return False

        # Scroll scale via encoder 1 (first encoder)
        if cc == ENCODER_CC.get('encoder_1'):
            delta = self.push.decode_relative_encoder(value)
            self._scroll_scale(delta)
            return True

        # Scale up/down buttons
        if cc == SCALE_UP_CC:
            self._scroll_scale(-1)
            return True
        if cc == SCALE_DOWN_CC:
            self._scroll_scale(1)
            return True

        # In-key/Chromatic toggle
        if cc == IN_KEY_CC:
            self.in_key_mode = True
            print("  Mode: In Key")
            self._apply_scale_changes()
            self._update_scale_display()
            self._update_scale_button_leds()
            return True

        if cc == CHROMAT_CC:
            self.in_key_mode = False
            print("  Mode: Chromatic")
            self._apply_scale_changes()
            self._update_scale_display()
            self._update_scale_button_leds()
            return True

        # Root note selection - upper row (C, C#, D, D#, E, F)
        if cc in ROOT_UPPER_BUTTONS:
            idx = ROOT_UPPER_BUTTONS.index(cc)
            self.root_note = ROOT_UPPER_NOTES[idx]
            print(f"  Root: {ROOT_NAMES[self.root_note]}")
            self._apply_scale_changes()
            self._update_scale_display()
            self._update_scale_button_leds()
            return True

        # Root note selection - lower row (F#, G, G#, A, A#, B)
        if cc in ROOT_LOWER_BUTTONS:
            idx = ROOT_LOWER_BUTTONS.index(cc)
            self.root_note = ROOT_LOWER_NOTES[idx]
            print(f"  Root: {ROOT_NAMES[self.root_note]}")
            self._apply_scale_changes()
            self._update_scale_display()
            self._update_scale_button_leds()
            return True

        # Scale button again exits
        if cc == BUTTON_CC.get('scale'):
            self._exit_scale_mode()
            return True

        return False

    # =========================================================================
    # ENCODER BANK SWITCHING
    # =========================================================================

    def _switch_encoder_bank(self, bank_index: int, bank_name: str):
        """Switch to encoder bank."""
        if self.encoder_bank == bank_index:
            return  # Already on this bank

        self.encoder_bank = bank_index
        print(f"Encoder Bank: {bank_name}")

        # Update bank button LEDs
        bank_buttons = ['volume', 'pan_send', 'track', 'device']
        for i, btn in enumerate(bank_buttons):
            if BUTTON_CC.get(btn):
                self.push.set_button_color(btn, 'white' if i == bank_index else 'dim_white')

        self._update_encoder_display()

    def _handle_encoder(self, encoder_index: int, value: int):
        """Handle encoder turn - sends CC based on current bank."""
        if encoder_index < 0 or encoder_index > 7:
            return

        delta = self.push.decode_relative_encoder(value)
        bank = self.encoder_bank

        # Update stored value
        current = self.encoder_values[bank][encoder_index]
        new_value = max(0, min(127, current + delta))
        self.encoder_values[bank][encoder_index] = new_value

        # Get CC mapping from config
        encoder_cfg = self.config.get_encoder_mapping(bank, encoder_index)
        if encoder_cfg and encoder_cfg.get('enabled', True):
            cc = encoder_cfg.get('cc', 21 + bank * 8 + encoder_index)
            channel = encoder_cfg.get('channel', 0)
            self.output.send_cc(cc, new_value, channel)

        # Update display
        self._update_encoder_display()

    # =========================================================================
    # SETTINGS MODE
    # =========================================================================

    def _toggle_settings_mode(self):
        """Toggle settings menu on/off."""
        if self.settings_mode_active:
            self._exit_settings_mode()
        else:
            self._enter_settings_mode()

    def _enter_settings_mode(self):
        """Enter settings menu."""
        self.settings_mode_active = True
        self.settings_category = 0
        self.settings_item = 0
        print("Entering Settings mode")
        self.push.set_button_color('user', 'white')
        self._update_settings_display()

    def _exit_settings_mode(self):
        """Exit settings menu and save settings."""
        # Apply settings to config
        self._apply_settings_to_config()

        self.settings_mode_active = False
        print("Exiting Settings mode")
        self.push.set_button_color('user', 'dim_white')
        self._update_main_display()
        self._update_pad_grid()

    def _update_settings_display(self):
        """Update LCD for settings menu."""
        cat = self.settings_categories[self.settings_category]
        cat_name = cat['name']
        items = cat['items']

        # Line 1: Category name
        self.push.set_lcd_line(1, f"SETTINGS: {cat_name}".center(68))

        # Line 2: Current item value
        if items:
            item = items[self.settings_item]
            value_str = self._format_setting_value(item)
            self.push.set_lcd_line(2, f"{item['name']}: {value_str}".center(68))
        else:
            self.push.set_lcd_line(2, "(No settings)".center(68))

        # Line 3: Category tabs
        cat_names = [c['name'][:8] for c in self.settings_categories]
        # Highlight current category
        segments = []
        for i, name in enumerate(cat_names):
            if i == self.settings_category:
                segments.append(f"[{name}]".center(17))
            else:
                segments.append(name.center(17))
        self.push.set_lcd_segments(3, segments)

        # Line 4: Instructions
        self.push.set_lcd_line(4, "Enc1:Cat Enc2:Item Enc3:Value | User:Exit")

    def _format_setting_value(self, item: dict) -> str:
        """Format a setting value for display."""
        val = item['value']
        if item['type'] == 'bool':
            return 'ON' if val else 'OFF'
        elif item['type'] == 'select':
            options = item.get('options', [])
            return options[val] if 0 <= val < len(options) else str(val)
        elif item['type'] == 'float':
            return f"{val:.1f}"
        else:
            return str(val)

    def _handle_settings_encoder(self, encoder_index: int, value: int):
        """Handle encoder turn in settings mode."""
        delta = self.push.decode_relative_encoder(value)

        if encoder_index == 0:
            # Category selection
            new_cat = max(0, min(len(self.settings_categories) - 1, self.settings_category + delta))
            if new_cat != self.settings_category:
                self.settings_category = new_cat
                self.settings_item = 0  # Reset item selection
                self._update_settings_display()

        elif encoder_index == 1:
            # Item selection within category
            items = self.settings_categories[self.settings_category]['items']
            if items:
                new_item = max(0, min(len(items) - 1, self.settings_item + delta))
                if new_item != self.settings_item:
                    self.settings_item = new_item
                    self._update_settings_display()

        elif encoder_index == 2:
            # Value adjustment
            items = self.settings_categories[self.settings_category]['items']
            if items:
                item = items[self.settings_item]
                self._adjust_setting_value(item, delta)
                self._update_settings_display()

    def _adjust_setting_value(self, item: dict, delta: int):
        """Adjust a setting value by delta."""
        val = item['value']

        if item['type'] == 'bool':
            item['value'] = not val if delta != 0 else val

        elif item['type'] == 'int':
            min_val = item.get('min', 0)
            max_val = item.get('max', 127)
            item['value'] = max(min_val, min(max_val, val + delta))

        elif item['type'] == 'float':
            min_val = item.get('min', 0.0)
            max_val = item.get('max', 1.0)
            step = item.get('step', 0.1)
            item['value'] = max(min_val, min(max_val, val + delta * step))

        elif item['type'] == 'select':
            options = item.get('options', [])
            if options:
                new_val = (val + delta) % len(options)
                item['value'] = new_val

    def _apply_settings_to_config(self):
        """Apply current settings values to config and save."""
        for cat in self.settings_categories:
            for item in cat['items']:
                key = item['key']
                val = item['value']

                # Map settings to config locations
                if key == 'midi_channel':
                    self.config.config['midi_channel'] = val - 1  # 0-indexed
                elif key == 'velocity_curve':
                    self.velocity_curve = val
                    self.config.config.setdefault('keyboard', {})['velocity_curve'] = val
                elif key == 'velocity_min':
                    self.velocity_min = val
                    self.config.config.setdefault('keyboard', {})['velocity_min'] = val
                elif key == 'velocity_max':
                    self.velocity_max = val
                    self.config.config.setdefault('keyboard', {})['velocity_max'] = val
                elif key == 'accent_velocity':
                    self.accent_velocity = val
                    self.config.config.setdefault('accent', {})['fixed_velocity'] = val
                elif key == 'default_octave':
                    self.config.config.setdefault('keyboard', {})['default_octave'] = val
                elif key == 'default_root':
                    self.config.config.setdefault('keyboard', {})['default_root'] = val
                elif key == 'default_scale':
                    self.config.config.setdefault('keyboard', {})['default_scale'] = SCALE_NAMES[val]

        # Save config
        try:
            self.config.save()
            print("Settings saved")
        except Exception as e:
            print(f"Failed to save settings: {e}")

    # =========================================================================
    # PAD HANDLING (Always active, independent of encoder bank)
    # =========================================================================

    def _handle_pad_press(self, pad_note: int, velocity: int):
        """Handle pad press - plays note based on isomorphic layout."""
        # Convert pad note to row/col
        pos = note_to_pad(pad_note)
        if pos is None:
            return

        row, col = pos

        # Get MIDI note from layout
        midi_note = self.layout.get_note_at(row, col)
        if midi_note is None:
            return

        # Check if in scale (for in-key mode filtering)
        info = self.layout.get_pad_info(row, col)
        in_scale = info.get('is_in_scale', info.get('in_scale', True)) if info else True

        # If in-key mode and not in scale, don't play
        if self.in_key_mode and not in_scale:
            return

        # Apply octave offset
        midi_note += self.octave_offset * 12

        # Clamp to MIDI range
        if midi_note < 0 or midi_note > 127:
            return

        # Apply velocity curve and accent
        if self.accent_mode:
            out_velocity = self.accent_velocity
        else:
            # Apply velocity curve
            normalized = velocity / 127.0
            curved = pow(normalized, self.velocity_curve)
            out_velocity = int(self.velocity_min + curved * (self.velocity_max - self.velocity_min))
            out_velocity = max(1, min(127, out_velocity))

        # Get output channel from config
        channel = self.config.keyboard_config.get('midi_channel', 0)

        # Send note on
        self.output.send_note_on(midi_note, out_velocity, channel)

        # If note repeat is active, start repeating
        if self.note_repeat_active:
            self.start_note_repeat(pad_note, midi_note, channel)

        # Visual feedback - light pad brighter
        self.push.set_pad_color(pad_note, self._get_pressed_pad_color())

    def _handle_pad_release(self, pad_note: int):
        """Handle pad release."""
        # Convert pad note to row/col
        pos = note_to_pad(pad_note)
        if pos is None:
            return

        row, col = pos

        # Get MIDI note from layout
        midi_note = self.layout.get_note_at(row, col)
        if midi_note is None:
            return

        # Apply octave offset
        midi_note += self.octave_offset * 12

        # Clamp to MIDI range
        if midi_note < 0 or midi_note > 127:
            return

        channel = self.config.keyboard_config.get('midi_channel', 0)

        # Send note off
        self.output.send_note_off(midi_note, channel)

        # Stop note repeat
        if self.note_repeat_active:
            self.stop_note_repeat(pad_note)

        # Restore pad color
        self._update_single_pad(pad_note)

    def _get_pressed_pad_color(self) -> int:
        """Get color for pressed pad."""
        return color_value('white')  # Full brightness white

    def _update_single_pad(self, pad_note: int):
        """Update color of a single pad based on layout."""
        # Convert pad note to row/col
        pos = note_to_pad(pad_note)
        if pos is None:
            self.push.set_pad_color(pad_note, 0)
            return

        row, col = pos
        info = self.layout.get_pad_info(row, col)
        if info is None:
            self.push.set_pad_color(pad_note, 0)
            return

        # Determine color based on note type
        # Layout uses 'is_in_scale' key
        in_scale = info.get('is_in_scale', info.get('in_scale', False))

        if not in_scale and self.in_key_mode:
            # Out of scale in in-key mode - off
            color = color_value(self.pad_colors.get('off_note', 'off'))
        elif info.get('is_root', False):
            # Root note
            color = color_value(self.pad_colors.get('root_note', 'blue'))
        elif in_scale:
            # In scale
            color = color_value(self.pad_colors.get('scale_note', 'white'))
        else:
            # Chromatic (not in scale)
            color = color_value(self.pad_colors.get('chromatic_note', 'gray'))

        self.push.set_pad_color(pad_note, color)

    def _update_pad_grid(self):
        """Update entire pad grid based on current scale/layout."""
        for note in range(PAD_NOTE_MIN, PAD_NOTE_MAX + 1):
            self._update_single_pad(note)

    # =========================================================================
    # DISPLAY UPDATE
    # =========================================================================

    def _update_main_display(self):
        """Update main LCD display."""
        # Line 1: Mode/Bank name
        bank_names = ['Volume', 'Pan/Send', 'Track', 'Device']
        bank_name = bank_names[self.encoder_bank] if self.encoder_bank < len(bank_names) else 'Unknown'
        self.push.set_lcd_line(1, f"MIDI Bridge - {bank_name}".center(68))

        # Line 2: Scale info
        scale_name = get_scale_display_name(SCALE_NAMES[self.scale_index])
        root_name = ROOT_NAMES[self.root_note]
        mode_str = "In Key" if self.in_key_mode else "Chromatic"
        self.push.set_lcd_line(2, f"{root_name} {scale_name} ({mode_str})".center(68))

        # Line 3: Encoder labels
        self._update_encoder_display()

        # Line 4: Transport/status
        self._update_status_line()

    def _update_encoder_display(self):
        """Update encoder labels and values on LCD."""
        bank = self.encoder_bank
        labels = []
        values = []

        for i in range(8):
            encoder_cfg = self.config.get_encoder_mapping(bank, i)
            if encoder_cfg:
                name = encoder_cfg.get('name', f'CC{encoder_cfg.get("cc", 21 + bank * 8 + i)}')
                labels.append(name[:8])  # Truncate to fit segment
                values.append(f"{self.encoder_values[bank][i]:3d}")
            else:
                labels.append(f'Enc {i+1}')
                values.append(f"{self.encoder_values[bank][i]:3d}")

        # Line 3: Encoder names
        # Pack 8 labels into 4 segments (2 per segment)
        segments = []
        for seg in range(4):
            left = labels[seg * 2][:8].ljust(8)
            right = labels[seg * 2 + 1][:8].rjust(8)
            segments.append(f"{left} {right}")
        self.push.set_lcd_segments(3, segments)

    def _update_status_line(self):
        """Update line 4 with transport/tempo status."""
        tempo_str = f"{self.tempo:.0f}BPM"
        octave_str = f"Oct:{self.octave_offset:+d}"
        play_str = "PLAY" if self.is_playing else "STOP"
        rec_str = "REC" if self.is_recording else "   "

        self.push.set_lcd_segments(4, [tempo_str, octave_str, play_str, rec_str])

    def _update_scale_display(self):
        """Update display for scale mode overlay."""
        # Line 1: Title
        self.push.set_lcd_line(1, "SCALE SELECTION".center(68))

        # Line 2: Current scale and root
        scale_name = get_scale_display_name(SCALE_NAMES[self.scale_index])
        root_name = ROOT_NAMES[self.root_note]
        mode_str = "In Key" if self.in_key_mode else "Chromatic"
        self.push.set_lcd_line(2, f"{root_name} {scale_name}".center(68))

        # Line 3: Instructions
        self.push.set_lcd_segments(3, ["<Root>", mode_str, "Scroll:", "Scale>"])

        # Line 4: Hint
        self.push.set_lcd_line(4, "Press Scale again to exit".center(68))

    def _show_popup(self, text: str, duration: float = 1.5):
        """Show a temporary popup message on LCD line 4."""
        self.lcd_popup_active = True
        self.lcd_popup_end_time = time.time() + duration
        self.push.set_lcd_line(4, text.center(68))

    # =========================================================================
    # MAIN EVENT LOOP
    # =========================================================================

    def run(self):
        """Main entry point."""
        print("=" * 60)
        print("  OPEN-PUSH MIDI BRIDGE")
        print("=" * 60)
        print()

        # Find Push
        print("Searching for MIDI devices...")
        push_in, push_out = self.push.find_ports()

        if not push_out:
            print("\nERROR: Could not find Ableton Push!")
            print("\nAvailable MIDI ports:")
            for name in mido.get_output_names():
                print(f"  - {name}")
            return

        print(f"  Push Input:  {push_in}")
        print(f"  Push Output: {push_out}")

        # Find output
        output_name = self.find_output_port()
        if output_name:
            print(f"  MIDI Output: {output_name}")
        else:
            print("  MIDI Output: None (dry run mode)")
        print()

        # Connect
        if not self.push.connect():
            print("ERROR: Failed to connect to Push")
            return

        # Open output port
        output_port = None
        if output_name:
            try:
                output_port = mido.open_output(output_name)
                self.output.set_port(output_port)
            except Exception as e:
                print(f"Warning: Could not open output port: {e}")

        try:
            self._initialize()
            self._main_loop()
        except KeyboardInterrupt:
            print("\nShutting down...")
        finally:
            self._cleanup()
            if output_port:
                output_port.close()
            self.push.disconnect()

    def _initialize(self):
        """Initialize Push hardware."""
        print("Initializing Push...")
        self.push.set_user_mode()
        time.sleep(0.1)

        # Clear display and pads
        self.push.clear_lcd()
        self.push.clear_all_pads()
        self.push.clear_all_buttons()

        # Set initial button states
        self.push.set_button_color('play', 'dim_white')
        self.push.set_button_color('record', 'dim_white')
        self.push.set_button_color('stop', 'white')
        self.push.set_button_color('accent', 'dim_white')
        self.push.set_button_color('repeat', 'dim_white')
        self.push.set_button_color('scale', 'dim_white')
        self.push.set_button_color('user', 'dim_white')

        # Set encoder bank buttons (Volume is default)
        self.push.set_button_color('volume', 'white')
        self.push.set_button_color('pan_send', 'dim_white')
        self.push.set_button_color('track', 'dim_white')
        self.push.set_button_color('device', 'dim_white')

        self._update_octave_display()

        # Initialize pad grid with current scale
        self._update_pad_grid()

        # Update main display
        self._update_main_display()

        self.running = True

        print()
        print("=" * 60)
        print("  READY!")
        print("=" * 60)
        print()

    def _main_loop(self):
        """Main event loop."""
        last_update = time.time()
        update_interval = 0.05  # 50ms

        while self.running:
            # Process all pending messages
            for msg in self.push.poll_messages():
                self._handle_message(msg)

            # Process note repeat
            self._process_note_repeat()

            # Periodic display updates (if needed for popups, etc.)
            now = time.time()
            if now - last_update >= update_interval:
                self._periodic_update()
                last_update = now

            # Brief sleep to prevent CPU spinning
            time.sleep(0.001)

    def _periodic_update(self):
        """Called periodically for display updates, popup timeouts, etc."""
        # Handle LCD popup timeout
        if self.lcd_popup_active and time.time() > self.lcd_popup_end_time:
            self.lcd_popup_active = False
            self._update_main_display()

    def _handle_message(self, msg):
        """Handle a single MIDI message from Push."""
        # Check global controls first
        if self.handle_global_controls(msg):
            return

        # If in settings mode, route encoders to settings handler
        if self.settings_mode_active and msg.type == 'control_change':
            encoder_ccs = [ENCODER_CC.get(f'encoder_{i+1}') for i in range(8)]
            if msg.control in encoder_ccs:
                encoder_idx = encoder_ccs.index(msg.control)
                self._handle_settings_encoder(encoder_idx, msg.value)
                return
            # User button to exit settings
            if msg.control == BUTTON_CC.get('user') and msg.value > 0:
                self._exit_settings_mode()
                return

        # If in scale mode overlay, handle scale mode CCs
        if msg.type == 'control_change':
            if self._handle_scale_mode_cc(msg.control, msg.value):
                return

            # Handle main encoders (1-8 in config, but 0-7 index)
            encoder_ccs = [ENCODER_CC.get(f'encoder_{i+1}') for i in range(8)]
            if msg.control in encoder_ccs:
                encoder_idx = encoder_ccs.index(msg.control)
                self._handle_encoder(encoder_idx, msg.value)
                return

        # Handle pad presses (always active, unless in settings mode)
        if not self.settings_mode_active:
            if msg.type == 'note_on' and is_pad_note(msg.note):
                if msg.velocity > 0:
                    self._handle_pad_press(msg.note, msg.velocity)
                else:
                    self._handle_pad_release(msg.note)
                return

            if msg.type == 'note_off' and is_pad_note(msg.note):
                self._handle_pad_release(msg.note)
                return

    def _cleanup(self):
        """Cleanup before exit."""
        self.running = False

        # Exit scale mode if active
        if self.scale_mode_active:
            self._exit_scale_mode()

        # Exit settings mode if active
        if self.settings_mode_active:
            self._exit_settings_mode()

        # Release all notes
        self.output.release_all_active()

        # Clear Push
        self.push.clear_lcd()
        self.push.clear_all_pads()
        self.push.clear_all_buttons()

        # Return to Live mode
        self.push.set_live_mode()

        print("Cleanup complete.")


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    """Main entry point - creates bridge and runs."""
    config = MIDIConfig()
    bridge = MIDIBridge(config)
    bridge.run()


if __name__ == "__main__":
    main()
