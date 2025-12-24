#!/usr/bin/env python3
"""
OpenPush Seqtrak Bridge
=======================
Control Yamaha Seqtrak from Ableton Push hardware.

Uses:
- Core Push hardware abstraction (LCD, buttons, pads)
- Music module (scales, isomorphic layout)
- Seqtrak protocol (SysEx addresses)

Usage:
    python -m open_push.seqtrak.app

Features:
- Transport control (Play/Stop)
- Track mute/solo (bottom row of pads)
- Isomorphic keyboard (upper rows)
- Scale/key selection
- LCD status display
"""

import mido
import threading
import time
import sys
import os

# Ensure imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from open_push.music.layout import IsomorphicLayout
from open_push.music.scales import SCALES, SCALE_NAMES, is_in_scale, is_root_note
from open_push.seqtrak.protocol import (
    SeqtrakProtocol, MuteState, Scale, Key, Track,
    find_seqtrak_port, SYSEX_HEADER
)

# =============================================================================
# PUSH CONSTANTS (from core)
# =============================================================================

PUSH_SYSEX_HEADER = [0x47, 0x7F, 0x15]
USER_MODE = [0x62, 0x00, 0x01, 0x01]

LCD_LINES = {1: 0x18, 2: 0x19, 3: 0x1A, 4: 0x1B}
CHARS_PER_SEGMENT = 17

# Button CCs
BUTTONS = {
    'play': 85, 'stop': 29, 'record': 86,
    'octave_up': 55, 'octave_down': 54,
    'scale': 58, 'note': 50, 'session': 51,
    'mute': 60, 'solo': 61,
    'up': 46, 'down': 47, 'left': 44, 'right': 45,
}

# Pad colors
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


# =============================================================================
# SEQTRAK BRIDGE APP
# =============================================================================

class SeqtrakBridge:
    """
    Bridge between Push hardware and Yamaha Seqtrak.
    """

    def __init__(self):
        # State
        self.is_playing = False
        self.current_mode = 'note'  # 'note', 'mute', 'session'
        self.octave = 0
        self.root = 0  # C
        self.scale_index = 2  # Minor

        # Track states (1-11)
        self.track_states = [MuteState.UNMUTED] * 11

        # Selected track for keyboard input (default SYNTH 1)
        self.keyboard_track = Track.SYNTH1  # Channel 8

        # Track active notes for proper note-off
        self.active_notes = {}  # {pad_note: midi_note}

        # Layout
        self.layout = IsomorphicLayout(
            root_note=self.root,
            scale=SCALES[SCALE_NAMES[self.scale_index]],
            interval_right=1,
            interval_up=5
        )

        # Ports (set in run())
        self.push_in = None
        self.push_out = None
        self.seqtrak = None
        self.protocol = None

        # Threading
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
    # Push Communication
    # -------------------------------------------------------------------------

    def send_sysex(self, data):
        """Send SysEx to Push."""
        msg = mido.Message('sysex', data=PUSH_SYSEX_HEADER + data)
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
        """Update LCD with current state."""
        # Line 1: Mode and status
        mode_text = self.current_mode.upper()
        transport = "PLAYING" if self.is_playing else "STOPPED"

        self.set_lcd_segments(1, "SEQTRAK", mode_text, transport, f"Oct:{self.octave:+d}")

        # Line 2: Scale info and keyboard target
        root_name = Key.NAMES[self.root]
        scale_name = SCALE_NAMES[self.scale_index][:8]
        kb_track = Track.NAMES.get(self.keyboard_track, f"T{self.keyboard_track}")
        self.set_lcd_segments(2, f"Key: {root_name}", f"Scale: {scale_name}", f"KB: {kb_track}", "")

        # Line 3-4: Context-dependent
        if self.current_mode == 'mute':
            self.set_lcd_segments(3, "Tracks 1-8", "Row2: 9-11", "", "")
            self.set_lcd_segments(4, "Pad = Toggle", "Red=Mute", "Yel=Solo", "")
        else:
            self.set_lcd_segments(3, "Play/Stop", "Mute/Solo", "Oct Up/Dn", "")
            self.set_lcd_segments(4, "Bottom row", "= Track mutes", "", "open-push")

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
        """Update grid for note mode (isomorphic keyboard + mute row)."""
        for row in range(8):
            for col in range(8):
                note = 36 + (row * 8) + col

                if row == 0:
                    # Bottom row = track mutes (tracks 1-8)
                    track = col + 1
                    state = self.track_states[track - 1]
                    if state == MuteState.MUTED:
                        color = COLOR_RED
                    elif state == MuteState.SOLO:
                        color = COLOR_YELLOW
                    else:
                        color = COLOR_GREEN
                else:
                    # Upper rows = isomorphic keyboard
                    midi_note = self.layout.get_note(row - 1, col) + (self.octave * 12)
                    semitone = midi_note % 12

                    if is_root_note(semitone, self.root):
                        color = COLOR_BLUE
                    elif is_in_scale(semitone, self.root, self.layout.scale):
                        color = COLOR_WHITE
                    else:
                        color = COLOR_DIM

                self.set_pad_color(note, color)

    def _update_mute_grid(self):
        """Update grid for mute mode (all tracks visible)."""
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

    # -------------------------------------------------------------------------
    # Input Handlers
    # -------------------------------------------------------------------------

    def handle_button(self, cc, value):
        """Handle button press."""
        if value == 0:  # Button released
            return

        if cc == BUTTONS['play']:
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

        elif cc == BUTTONS['octave_up']:
            if self.octave < 4:
                self.octave += 1
                self.update_grid()
                self.update_display()
                print(f"Octave: {self.octave:+d}")

        elif cc == BUTTONS['octave_down']:
            if self.octave > -4:
                self.octave -= 1
                self.update_grid()
                self.update_display()
                print(f"Octave: {self.octave:+d}")

        elif cc == BUTTONS['mute']:
            self.current_mode = 'mute'
            self.update_grid()
            self.update_display()
            print("Mode: MUTE")

        elif cc == BUTTONS['note']:
            self.current_mode = 'note'
            self.update_grid()
            self.update_display()
            print("Mode: NOTE")

    def handle_pad(self, note, velocity):
        """Handle pad press/release."""
        row = (note - 36) // 8
        col = (note - 36) % 8

        if velocity == 0:  # Pad released
            # Send note-off if we have an active note for this pad
            if note in self.active_notes:
                midi_note = self.active_notes[note]
                self.protocol.release_note(self.keyboard_track, midi_note)
                del self.active_notes[note]
            return

        if self.current_mode == 'mute' or row == 0:
            # Mute mode or bottom row = track control
            if row == 0:
                track = col + 1
            elif row == 1 and col < 3:
                track = col + 9
            else:
                return

            if track <= 11:
                self._toggle_track_mute(track)

        else:
            # Note mode (upper rows)
            # Calculate MIDI note and send to Seqtrak
            midi_note = self.layout.get_note(row - 1, col) + (self.octave * 12)

            # Clamp to valid MIDI range
            midi_note = max(0, min(127, midi_note))

            # Send note to Seqtrak
            self.protocol.trigger_note(self.keyboard_track, midi_note, velocity)
            self.active_notes[note] = midi_note

            # Show on LCD
            track_name = Track.NAMES.get(self.keyboard_track, f"Track {self.keyboard_track}")
            print(f"♪ {midi_note} → {track_name}")

    def _toggle_track_mute(self, track):
        """Toggle track mute state: unmuted → muted → solo → unmuted."""
        current = self.track_states[track - 1]
        track_name = Track.NAMES.get(track, f"Track {track}")

        if current == MuteState.UNMUTED:
            new_state = MuteState.MUTED
            state_name = "MUTED"
            # Use CC-based mute (official MIDI method)
            self.protocol.mute_track_cc(track, muted=True)
        elif current == MuteState.MUTED:
            new_state = MuteState.SOLO
            state_name = "SOLO"
            # Unmute first, then solo
            self.protocol.mute_track_cc(track, muted=False)
            self.protocol.solo_track_cc(track)
        else:
            new_state = MuteState.UNMUTED
            state_name = "UNMUTED"
            # Unsolo and unmute
            self.protocol.solo_track_cc(0)  # 0 = unsolo
            self.protocol.mute_track_cc(track, muted=False)

        self.track_states[track - 1] = new_state
        self.update_grid()
        print(f"{track_name}: {state_name}")

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

        print(f"  Push Input:  {push_in_name}")
        print(f"  Push Output: {push_out_name}")
        print(f"  Seqtrak:     {seqtrak_name}")
        print()

        # Open ports
        with mido.open_output(push_out_name) as push_out, \
             mido.open_output(seqtrak_name) as seqtrak_out, \
             mido.open_input(push_in_name) as push_in:

            self.push_out = push_out
            self.push_in = push_in
            self.seqtrak = seqtrak_out
            self.protocol = SeqtrakProtocol(seqtrak_out)

            # Initialize Push
            print("Initializing Push...")
            self.send_sysex(USER_MODE)
            time.sleep(0.1)

            # Set up display and grid
            self.clear_all_pads()
            self.update_display()
            self.update_grid()
            self.update_transport_leds()

            # Light up mode buttons
            self.set_button_led(BUTTONS['note'], LED_ON)
            self.set_button_led(BUTTONS['mute'], LED_DIM)
            self.set_button_led(BUTTONS['octave_up'], LED_DIM)
            self.set_button_led(BUTTONS['octave_down'], LED_DIM)

            print()
            print("=" * 60)
            print("  READY!")
            print("=" * 60)
            print()
            print("Controls:")
            print("  Play/Stop    - Transport")
            print("  Bottom row   - Track mutes (cycles: unmute→mute→solo)")
            print("  Upper rows   - Isomorphic keyboard")
            print("  Oct Up/Down  - Shift octave")
            print("  Note/Mute    - Switch modes")
            print()
            print("Press Ctrl+C to exit")
            print()

            # Main loop
            self.running = True
            try:
                for msg in push_in:
                    if msg.type == 'control_change':
                        self.handle_button(msg.control, msg.value)

                    elif msg.type == 'note_on':
                        if 36 <= msg.note <= 99:  # Pad range
                            self.handle_pad(msg.note, msg.velocity)

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

        print("Done!")


# =============================================================================
# ENTRY POINT
# =============================================================================

def main():
    bridge = SeqtrakBridge()
    bridge.run()


if __name__ == "__main__":
    main()
