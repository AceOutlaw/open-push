#!/usr/bin/env python3
"""
Isomorphic MIDI Controller for Push 1
=====================================
Turns Push into a playable instrument with an isomorphic layout.

Layout: Fourths (each row is +5 semitones from the row below)
Scale: C Minor (C, D, Eb, F, G, Ab, Bb)

Moving right = +1 semitone
Moving up = +5 semitones (perfect fourth)

This creates a consistent geometric pattern where chord shapes
are the same regardless of key.

Requirements:
    pip install mido python-rtmidi

Usage:
    python isomorphic_controller.py

    Then play the pads! MIDI notes will be sent to the default output.
    Press Ctrl+C to exit.
"""

import mido
import time

# =============================================================================
# CONSTANTS
# =============================================================================

SYSEX_HEADER = [0x47, 0x7F, 0x15]
USER_MODE = [0x62, 0x00, 0x01, 0x01]

# LCD
LCD_LINES = {1: 0x18, 2: 0x19, 3: 0x1A, 4: 0x1B}
CHARS_PER_SEGMENT = 17

# Colors (Push 1 palette)
COLORS = {
    'off': 0,
    'dim_white': 1,
    'white': 3,
    'red': 5,
    'orange': 9,
    'yellow': 13,
    'lime': 17,
    'green': 21,
    'cyan': 33,
    'blue': 45,
    'purple': 49,
    'pink': 57,
}

# Scale definitions (semitones from root)
SCALES = {
    'minor': [0, 2, 3, 5, 7, 8, 10],      # Natural minor
    'major': [0, 2, 4, 5, 7, 9, 11],
    'dorian': [0, 2, 3, 5, 7, 9, 10],
    'pentatonic_minor': [0, 3, 5, 7, 10],
    'blues': [0, 3, 5, 6, 7, 10],
    'chromatic': list(range(12)),
}

# Note names
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# =============================================================================
# ISOMORPHIC LAYOUT
# =============================================================================

class IsomorphicLayout:
    """
    Isomorphic keyboard layout in fourths.

    Each row is +5 semitones from the row below.
    Each column is +1 semitone from the column to the left.
    """

    def __init__(self, root_note=36, row_interval=5, col_interval=1):
        """
        Args:
            root_note: MIDI note for bottom-left pad (default 36 = C2)
            row_interval: Semitones between rows (default 5 = fourth)
            col_interval: Semitones between columns (default 1)
        """
        self.root_note = root_note
        self.row_interval = row_interval
        self.col_interval = col_interval

        # Build note map: pad_note -> MIDI note
        self.note_map = {}
        for row in range(8):
            for col in range(8):
                pad_note = 36 + (row * 8) + col
                midi_note = root_note + (row * row_interval) + (col * col_interval)
                self.note_map[pad_note] = midi_note

    def get_midi_note(self, pad_note):
        """Get MIDI note for a pad."""
        return self.note_map.get(pad_note, pad_note)

    def get_note_at(self, row, col):
        """Get MIDI note at grid position."""
        pad_note = 36 + (row * 8) + col
        return self.note_map.get(pad_note, 0)


# =============================================================================
# PUSH CONTROLLER
# =============================================================================

class PushController:
    """Controls Push hardware and handles MIDI I/O."""

    def __init__(self, midi_channel=0):
        """
        Args:
            midi_channel: MIDI channel for output (0-15, where 0=Ch1, 15=Ch16)
        """
        self.push_in_name = None
        self.push_out_name = None
        self.midi_channel = midi_channel
        self.layout = IsomorphicLayout(root_note=36)  # C2
        self.scale = SCALES['minor']
        self.root = 0  # C
        self.active_notes = {}  # pad_note -> midi_note (currently held)

        # Virtual port for DAW connection (created at runtime)
        self.virtual_out = None
        self.virtual_out_name = "open-push"

    def find_push(self):
        """Find Push hardware ports."""
        print("Scanning for Push hardware...")

        for name in mido.get_input_names():
            if 'Ableton Push' in name and 'User' in name:
                self.push_in_name = name
                break

        for name in mido.get_output_names():
            if 'Ableton Push' in name and 'User' in name:
                self.push_out_name = name
                break

        if self.push_in_name and self.push_out_name:
            print(f"  Found: {self.push_in_name}")
            return True
        else:
            print("  Push not found!")
            print("  Available inputs:", mido.get_input_names())
            print("  Available outputs:", mido.get_output_names())
            return False

    def create_virtual_port(self):
        """Create a virtual MIDI port for DAW connection."""
        try:
            # Create virtual output port - DAWs will see this as a MIDI input
            self.virtual_out = mido.open_output(self.virtual_out_name, virtual=True)
            print(f"  Created virtual port: '{self.virtual_out_name}'")
            print(f"  -> In your DAW, select '{self.virtual_out_name}' as MIDI input")
            return True
        except Exception as e:
            print(f"  Could not create virtual port: {e}")
            print("  Notes will only be printed to console.")
            return False

    def _send_sysex(self, port, data):
        msg = mido.Message('sysex', data=SYSEX_HEADER + data)
        port.send(msg)

    def _set_lcd_segments(self, port, line, seg0="", seg1="", seg2="", seg3=""):
        parts = [seg0, seg1, seg2, seg3]
        text = ""
        for part in parts:
            text += part[:CHARS_PER_SEGMENT].center(CHARS_PER_SEGMENT)

        line_addr = LCD_LINES[line]
        data = [line_addr, 0x00, 0x45, 0x00]
        data.extend([ord(c) for c in text])
        self._send_sysex(port, data)

    def is_in_scale(self, midi_note):
        """Check if a MIDI note is in the current scale."""
        degree = (midi_note - self.root) % 12
        return degree in self.scale

    def is_root(self, midi_note):
        """Check if a MIDI note is a root note."""
        return (midi_note - self.root) % 12 == 0

    def get_pad_color(self, midi_note):
        """Get the color for a pad based on its note."""
        if self.is_root(midi_note):
            return COLORS['blue']  # Root notes in blue
        elif self.is_in_scale(midi_note):
            return COLORS['white']  # Scale notes in white
        else:
            return COLORS['dim_white']  # Non-scale notes dim

    def light_grid(self, port):
        """Light up the pad grid according to scale."""
        for row in range(8):
            for col in range(8):
                pad_note = 36 + (row * 8) + col
                midi_note = self.layout.get_midi_note(pad_note)
                color = self.get_pad_color(midi_note)
                msg = mido.Message('note_on', note=pad_note, velocity=color)
                port.send(msg)

    def clear_grid(self, port):
        """Turn off all pads."""
        for note in range(36, 100):
            msg = mido.Message('note_on', note=note, velocity=0)
            port.send(msg)

    def note_name(self, midi_note):
        """Get note name from MIDI note number."""
        return NOTE_NAMES[midi_note % 12] + str((midi_note // 12) - 1)

    def run(self):
        """Main loop."""
        print()
        print("=" * 60)
        print("  open-push : Isomorphic Controller")
        print("=" * 60)
        print()

        # Find Push hardware
        if not self.find_push():
            return

        # Create virtual MIDI port for DAW
        print()
        print("Creating virtual MIDI port...")
        self.create_virtual_port()

        print()
        print("  Layout: Fourths (row +5, col +1)")
        print("  Scale:  C Minor")
        print("  Colors: Blue=Root, White=Scale, Dim=Other")
        print(f"  Channel: {self.midi_channel + 1}")
        print()
        print("  Press pads to play! Ctrl+C to exit.")
        print("=" * 60)
        print()

        with mido.open_output(self.push_out_name) as push_port:
            # Wake up Push
            self._send_sysex(push_port, USER_MODE)
            time.sleep(0.1)

            # Set up display
            self._set_lcd_segments(push_port, 1, "open-push", "C Minor", "Fourths", "")
            self._set_lcd_segments(push_port, 2, "Blue=Root", "White=Scale", "Dim=Other", "")
            self._set_lcd_segments(push_port, 3, "", "", "", "")
            self._set_lcd_segments(push_port, 4, "Play the pads!", "", "", "v0.1")

            # Light up some buttons to show we're alive
            # Play button = green, to indicate "ready"
            push_port.send(mido.Message('control_change', control=85, value=COLORS['green']))

            # Light up grid
            self.light_grid(push_port)

            # Listen for input
            with mido.open_input(self.push_in_name) as in_port:
                try:
                    for msg in in_port:
                        if msg.type == 'note_on':
                            pad_note = msg.note
                            velocity = msg.velocity

                            if 36 <= pad_note <= 99:  # Pad range
                                midi_note = self.layout.get_midi_note(pad_note)

                                if velocity > 0:
                                    # Note on
                                    self.active_notes[pad_note] = midi_note
                                    print(f"ON:  Pad {pad_note:2d} -> {self.note_name(midi_note):4s} (MIDI {midi_note}, vel {velocity})")

                                    # Flash pad brighter
                                    push_port.send(mido.Message('note_on', note=pad_note, velocity=COLORS['green']))

                                    # Send MIDI to virtual port -> DAW
                                    if self.virtual_out:
                                        self.virtual_out.send(mido.Message('note_on', note=midi_note, velocity=velocity, channel=self.midi_channel))
                                else:
                                    # Note off (velocity 0)
                                    if pad_note in self.active_notes:
                                        midi_note = self.active_notes.pop(pad_note)
                                        print(f"OFF: Pad {pad_note:2d} -> {self.note_name(midi_note):4s}")

                                        # Restore pad color
                                        color = self.get_pad_color(midi_note)
                                        push_port.send(mido.Message('note_on', note=pad_note, velocity=color))

                                        # Send MIDI off
                                        if self.virtual_out:
                                            self.virtual_out.send(mido.Message('note_off', note=midi_note, velocity=0, channel=self.midi_channel))

                        elif msg.type == 'note_off':
                            pad_note = msg.note
                            if 36 <= pad_note <= 99 and pad_note in self.active_notes:
                                midi_note = self.active_notes.pop(pad_note)
                                print(f"OFF: Pad {pad_note:2d} -> {self.note_name(midi_note):4s}")

                                color = self.get_pad_color(midi_note)
                                push_port.send(mido.Message('note_on', note=pad_note, velocity=color))

                                if self.virtual_out:
                                    self.virtual_out.send(mido.Message('note_off', note=midi_note, velocity=0, channel=self.midi_channel))

                        elif msg.type == 'control_change':
                            # Could handle buttons/encoders here
                            pass

                except KeyboardInterrupt:
                    print("\n\nShutting down...")

            # Cleanup
            print("Cleaning up...")
            self.clear_grid(push_port)
            push_port.send(mido.Message('control_change', control=85, value=0))  # Play LED off
            for line in range(1, 5):
                self._set_lcd_segments(push_port, line, "", "", "", "")

        # Close virtual port
        if self.virtual_out:
            self.virtual_out.close()

        print("Done!")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='open-push: Isomorphic MIDI Controller')
    parser.add_argument('-c', '--channel', type=int, default=1,
                        help='MIDI channel (1-16, default: 1)')
    args = parser.parse_args()

    # Convert 1-16 to 0-15 for mido
    channel = max(0, min(15, args.channel - 1))

    controller = PushController(midi_channel=channel)
    controller.run()
