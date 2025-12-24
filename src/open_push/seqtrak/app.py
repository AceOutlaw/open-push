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
    'mute': 60, 'solo': 61, 'accent': 57,

    # Navigation
    'up': 46, 'down': 47, 'left': 44, 'right': 45,
    'page_left': 62, 'page_right': 63,
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
        self.current_mode = 'welcome'  # welcome, note, track, device, mixer, scale
        self.previous_mode = 'track'   # Mode to return to after scale mode
        self.shift_held = False

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

        # Tempo (for display, updated from Seqtrak feedback)
        self.tempo = 120

        # Master volume (0-127)
        self.master_volume = 100

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

    def _update_welcome_display(self):
        """Show welcome/loading screen."""
        self.set_lcd_segments(1, "", "OpenPush", "", "")
        self.set_lcd_segments(2, "", "Seqtrak Bridge", "", "")
        self.set_lcd_segments(3, "", "", "", "")
        self.set_lcd_segments(4, "Track", "Device", "Mixer", "to start")

    def _update_track_display(self):
        """Update LCD for track mode."""
        kb_track = Track.NAMES.get(self.keyboard_track, f"T{self.keyboard_track}")
        root_name = ROOT_NAMES[self.root_note]
        scale_name = get_scale_display_name(SCALE_NAMES[self.scale_index])
        octave = self.layout.get_octave()

        # Line 1: Track name, patch info, tempo
        self.set_lcd_segments(1, kb_track, self.patch_name or "", "", f"{self.tempo} BPM")
        # Line 2: Scale, octave info
        self.set_lcd_segments(2, f"{root_name} {scale_name}", f"Oct {octave}", "", "")
        # Line 3: Available for future use
        self.set_lcd_segments(3, "", "", "", "")
        # Line 4: Available for future use
        self.set_lcd_segments(4, "", "", "", "")

    def _update_device_display(self):
        """Update LCD for device mode."""
        transport = "PLAYING" if self.is_playing else "STOPPED"
        kb_track = Track.NAMES.get(self.keyboard_track, f"T{self.keyboard_track}")

        self.set_lcd_segments(1, "DEVICE", kb_track, "", transport)
        self.set_lcd_segments(2, "", "", "", "")
        self.set_lcd_segments(3, "", "", "", "")
        self.set_lcd_segments(4, "", "", "", "open-push")

    def _update_mixer_display(self):
        """Update LCD for mixer mode."""
        transport = "PLAYING" if self.is_playing else "STOPPED"

        self.set_lcd_segments(1, "MIXER", "", "", transport)
        self.set_lcd_segments(2, "Mute/Solo", "", "", "")
        self.set_lcd_segments(3, "", "", "", "")
        self.set_lcd_segments(4, "", "", "", "open-push")

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
        """Update grid for note mode (isomorphic keyboard)."""
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
        """Enter scale selection mode."""
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
    # Mode Switching (matching Reason app pattern)
    # -------------------------------------------------------------------------

    def _set_mode(self, mode):
        """Switch to a different mode and update display."""
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
        else:
            self.set_button_led(BUTTONS['upper_1'], LED_OFF)
            self.set_button_led(BUTTONS['lower_1'], LED_OFF)

        # Patch cycling buttons always available (CC 22, CC 104)
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
            # Toggle record via SysEx
            self.is_recording = not self.is_recording
            self.protocol.record(self.is_recording)
            self.set_button_led(BUTTONS['record'], LED_ON if self.is_recording else LED_DIM)
            self.update_display()
            print(f"● RECORD {'ON' if self.is_recording else 'OFF'}")

        elif cc == BUTTONS['tap_tempo']:
            # Tap tempo - send to protocol
            self.protocol.tap_tempo()
            print("  -> Tap Tempo")

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

        # Track mode: CC 20 = prev track, CC 102 = next track
        elif self.current_mode == 'track' and cc == BUTTONS['upper_1']:  # CC 20
            self._select_prev_track()
        elif self.current_mode == 'track' and cc == BUTTONS['lower_1']:  # CC 102
            self._select_next_track()

        # Patch cycling: CC 22 = prev patch, CC 104 = next patch
        elif cc == BUTTONS['upper_3']:  # CC 22
            self._cycle_patch(-1)
        elif cc == BUTTONS['lower_3']:  # CC 104
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
        elif cc == BUTTONS['scale']:
            if self.current_mode == 'scale':
                self._exit_scale_mode()
            else:
                self._enter_scale_mode()

    def handle_encoder(self, cc, value):
        """Handle encoder turn."""
        # Relative encoder: 1-63 = clockwise, 65-127 = counter-clockwise
        if value < 64:
            delta = 1  # Clockwise
        else:
            delta = -1  # Counter-clockwise

        # Tempo encoder (CC 14)
        if cc == 14:
            # Use actual delta for tempo (faster turns = bigger change)
            if value < 64:
                tempo_delta = value
            else:
                tempo_delta = value - 128

            new_tempo = max(20, min(300, self.tempo + tempo_delta))
            if new_tempo != self.tempo:
                self.tempo = new_tempo
                self.protocol.set_tempo(self.tempo)
                self.update_display()
                print(f"Tempo: {self.tempo}")

        # Track encoder (CC 71) - cycle through tracks
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
        elif cc == 73:
            self.patch_encoder_accum += delta
            if abs(self.patch_encoder_accum) >= self.patch_encoder_threshold:
                # Trigger patch change
                patch_delta = 1 if self.patch_encoder_accum > 0 else -1
                self._cycle_patch(patch_delta)
                self.patch_encoder_accum = 0  # Reset accumulator

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

    def handle_pad(self, note, velocity):
        """Handle pad press/release."""
        if note < 36 or note > 99:
            return

        row = (note - 36) // 8
        col = (note - 36) % 8

        if velocity == 0:
            # Note off
            if note in self.active_notes:
                midi_note = self.active_notes.pop(note)
                self.protocol.release_note(self.keyboard_track, midi_note)

                # Restore pad color
                info = self.layout.get_pad_info(row, col)
                if info['is_root']:
                    color = COLOR_BLUE
                elif info['is_in_scale']:
                    color = COLOR_WHITE
                else:
                    color = COLOR_OFF if self.in_key_mode else COLOR_DIM
                self.set_pad_color(note, color)
            return

        # Mute mode: bottom rows control track mutes
        if self.current_mode == 'mute':
            if row == 0:
                track = col + 1
            elif row == 1 and col < 3:
                track = col + 9
            else:
                return

            if track <= 11:
                self._toggle_track_mute(track)
            return

        # Note mode: play notes
        midi_note = self.layout.get_midi_note(note)

        # Send to Seqtrak
        self.protocol.trigger_note(self.keyboard_track, midi_note, velocity)
        self.active_notes[note] = midi_note

        # Flash pad green
        self.set_pad_color(note, COLOR_GREEN)

        track_name = Track.NAMES.get(self.keyboard_track, f"T{self.keyboard_track}")
        print(f"♪ {midi_note} → {track_name}")

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

    def _get_track_preset_display(self, track):
        """Get preset display string for a track from stored bank/program."""
        bank = self.track_bank_msb[track]
        sub = self.track_bank_lsb[track]
        prog = self.track_program[track]
        if bank or sub or prog:
            return get_preset_name_short(track, bank, sub, prog)
        return ""

    def _cycle_patch(self, delta):
        """Cycle through patches for the current track."""
        track = self.keyboard_track
        bank = self.track_bank_msb[track]
        sub = self.track_bank_lsb[track]
        prog = self.track_program[track]

        # Calculate new program/bank
        new_prog = prog + delta

        if new_prog > 127:
            # Wrap to next bank
            new_prog = 0
            new_sub = sub + 1
            if new_sub > 31:  # Max preset bank LSB
                new_sub = 0
        elif new_prog < 0:
            # Wrap to previous bank
            new_prog = 127
            new_sub = sub - 1
            if new_sub < 0:
                new_sub = 31
        else:
            new_sub = sub

        # Send Bank Select + Program Change to Seqtrak
        channel = track - 1  # Convert to 0-indexed MIDI channel
        self.seqtrak.send(mido.Message('control_change', channel=channel, control=0, value=bank))
        self.seqtrak.send(mido.Message('control_change', channel=channel, control=32, value=new_sub))
        self.seqtrak.send(mido.Message('program_change', channel=channel, program=new_prog))

        # Update local state
        self.track_bank_lsb[track] = new_sub
        self.track_program[track] = new_prog
        self.patch_name = get_preset_name_short(track, bank, new_sub, new_prog)
        self.update_display()
        print(f"  Patch: {self.patch_name}")

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
        self.update_display()

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
        self.update_display()

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

            # Request current preset info from Seqtrak
            self.protocol.request_parameter(Address.PRESET_NAME)

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
