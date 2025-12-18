#!/usr/bin/env python3
"""
Isomorphic MIDI Controller for Push 1
=====================================
Turns Push into a playable instrument with an isomorphic layout.

Layout: Fourths (each row is +5 semitones from the row below)
Scale: Selectable (Major/Minor)
Root: Selectable (C through B)

Moving right = +1 semitone
Moving up = +5 semitones (perfect fourth)

This creates a consistent geometric pattern where chord shapes
are the same regardless of key.

Features:
    - Octave Up/Down (Up/Down arrows)
    - Accent mode (fixed velocity 127)
    - Scale selection (Major/Minor)
    - Root note selection
    - In-Key / Chromatic mode

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

# Button CC numbers
BUTTONS = {
    'octave_up': 55,      # Octave Up
    'octave_down': 54,    # Octave Down
    'accent': 57,         # Accent
    'scale': 58,          # Scale button (opens scale page)
    'up': 46,             # Up arrow
    'down': 47,           # Down arrow
    'left': 44,           # Left arrow
    'right': 45,          # Right arrow
    'play': 85,           # Play
    'note': 50,           # Note mode
    'session': 51,        # Session mode
}

# Colors (Push 1 palette)
COLORS = {
    'off': 0,
    'dim_white': 1,
    'white': 3,
    'dim_red': 7,
    'red': 5,
    'dim_orange': 11,
    'orange': 9,
    'dim_yellow': 15,
    'yellow': 13,
    'lime': 17,
    'dim_green': 23,
    'green': 21,
    'cyan': 33,
    'dim_blue': 47,
    'blue': 45,
    'purple': 49,
    'pink': 57,
}

# Scale definitions (semitones from root)
SCALES = {
    'major': [0, 2, 4, 5, 7, 9, 11],
    'minor': [0, 2, 3, 5, 7, 8, 10],
    'dorian': [0, 2, 3, 5, 7, 9, 10],
    'pentatonic': [0, 3, 5, 7, 10],
    'blues': [0, 3, 5, 6, 7, 10],
    'chromatic': list(range(12)),
}

SCALE_NAMES = ['major', 'minor', 'dorian', 'pentatonic', 'blues', 'chromatic']

# Note names
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Pages
PAGE_PLAY = 'play'
PAGE_SCALE = 'scale'

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
        self._rebuild_map()

    def _rebuild_map(self):
        """Rebuild the note map based on current root_note."""
        self.note_map = {}
        for row in range(8):
            for col in range(8):
                pad_note = 36 + (row * 8) + col
                midi_note = self.root_note + (row * self.row_interval) + (col * self.col_interval)
                self.note_map[pad_note] = midi_note

    def set_root_note(self, root_note):
        """Change the root note and rebuild the map."""
        self.root_note = root_note
        self._rebuild_map()

    def shift_octave(self, direction):
        """Shift octave up (+1) or down (-1). Returns new octave number."""
        new_root = self.root_note + (direction * 12)
        # Clamp to valid MIDI range (keep some playable range)
        if 0 <= new_root <= 96:
            self.root_note = new_root
            self._rebuild_map()
        return (self.root_note // 12) - 1  # Return octave number

    def get_octave(self):
        """Get current octave number."""
        return (self.root_note // 12) - 1

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
        self.push_port = None
        self.midi_channel = midi_channel
        self.layout = IsomorphicLayout(root_note=36)  # C2
        self.scale_name = 'minor'
        self.scale = SCALES[self.scale_name]
        self.root = 0  # C (0-11)
        self.active_notes = {}  # pad_note -> midi_note (currently held)
        self.in_key_mode = True  # True = only play in-scale notes, False = chromatic

        # Feature states
        self.accent_on = False  # Fixed velocity mode
        self.current_page = PAGE_PLAY

        # Velocity curve settings
        self.velocity_min = 40      # Minimum output velocity (floor)
        self.velocity_max = 127     # Maximum output velocity
        self.velocity_curve = 1.0   # Curve exponent (1.0=linear, <1=soft, >1=hard)

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

    def _send_sysex(self, data):
        msg = mido.Message('sysex', data=SYSEX_HEADER + data)
        self.push_port.send(msg)

    def _set_lcd_segments(self, line, seg0="", seg1="", seg2="", seg3=""):
        parts = [seg0, seg1, seg2, seg3]
        text = ""
        for part in parts:
            text += part[:CHARS_PER_SEGMENT].center(CHARS_PER_SEGMENT)

        line_addr = LCD_LINES[line]
        data = [line_addr, 0x00, 0x45, 0x00]
        data.extend([ord(c) for c in text])
        self._send_sysex(data)

    def _set_button_led(self, button_name, color):
        """Set a button LED color."""
        cc = BUTTONS.get(button_name)
        if cc:
            color_val = COLORS.get(color, color) if isinstance(color, str) else color
            self.push_port.send(mido.Message('control_change', control=cc, value=color_val))

    def _set_button_led_cc(self, cc, color):
        """Set a button LED color by CC number."""
        color_val = COLORS.get(color, color) if isinstance(color, str) else color
        self.push_port.send(mido.Message('control_change', control=cc, value=color_val))

    def apply_velocity_curve(self, velocity):
        """
        Apply velocity curve to make pads more playable.

        Takes raw velocity (1-127) and maps it to a more usable range
        with a minimum floor so light touches still produce sound.
        """
        if velocity <= 0:
            return 0

        # Normalize input to 0-1 range
        normalized = (velocity - 1) / 126.0

        # Apply curve (optional - 1.0 = linear)
        curved = pow(normalized, self.velocity_curve)

        # Map to output range with minimum floor
        output_range = self.velocity_max - self.velocity_min
        output = int(self.velocity_min + (curved * output_range))

        # Clamp to valid MIDI range
        return max(1, min(127, output))

    def is_in_scale(self, midi_note):
        """Check if a MIDI note is in the current scale."""
        degree = (midi_note - self.root) % 12
        return degree in self.scale

    def is_root(self, midi_note):
        """Check if a MIDI note is a root note."""
        return (midi_note - self.root) % 12 == 0

    def get_in_key_note(self, row, col):
        """
        Get MIDI note for in-key mode where all pads are scale notes.
        Uses scale degrees instead of semitones.
        Row interval = 3 scale degrees (similar to a fourth feel)
        Col interval = 1 scale degree
        """
        scale_len = len(self.scale)
        row_interval = 3  # Scale degrees per row (gives fourth-like feel)

        # Calculate which scale degree this pad represents
        scale_degree = (row * row_interval) + col

        # Calculate octave offset and position within scale
        octave_offset = scale_degree // scale_len
        note_index = scale_degree % scale_len

        # Get the actual semitone offset from the scale
        semitone = self.scale[note_index]

        # Calculate final MIDI note
        base_note = self.layout.root_note + self.root  # Add root offset
        midi_note = base_note + (octave_offset * 12) + semitone

        return midi_note

    def get_midi_note_for_pad(self, pad_note):
        """Get the MIDI note for a pad based on current mode."""
        row = (pad_note - 36) // 8
        col = (pad_note - 36) % 8

        if self.in_key_mode:
            return self.get_in_key_note(row, col)
        else:
            return self.layout.get_midi_note(pad_note)

    def get_pad_color(self, row, col):
        """Get the color for a pad based on its position and mode."""
        if self.in_key_mode:
            midi_note = self.get_in_key_note(row, col)
        else:
            pad_note = 36 + (row * 8) + col
            midi_note = self.layout.get_midi_note(pad_note)

        if self.is_root(midi_note):
            return COLORS['blue']  # Root notes in blue
        elif self.is_in_scale(midi_note):
            return COLORS['white']  # Scale notes in white
        else:
            return COLORS['dim_white']  # Non-scale notes dim (only in chromatic)

    def light_grid(self):
        """Light up the pad grid according to scale and mode."""
        for row in range(8):
            for col in range(8):
                pad_note = 36 + (row * 8) + col
                color = self.get_pad_color(row, col)
                self.push_port.send(mido.Message('note_on', note=pad_note, velocity=color))

    def light_scale_page_grid(self):
        """Light up the grid for scale page selection."""
        # Clear grid first
        for note in range(36, 100):
            self.push_port.send(mido.Message('note_on', note=note, velocity=0))

        # Bottom row: Root note selection (C through B)
        for col in range(8):
            pad_note = 36 + col
            if col < 8:  # C, C#, D, D#, E, F, F#, G
                if col == self.root or (col + 4 == self.root and col >= 4):
                    color = COLORS['blue']  # Selected root
                else:
                    color = COLORS['dim_white']
            self.push_port.send(mido.Message('note_on', note=pad_note, velocity=color))

        # Second row: More root notes (G#, A, A#, B) and empty
        for col in range(4):
            pad_note = 44 + col  # Row 2, cols 0-3
            root_index = 8 + col  # G#, A, A#, B
            if root_index == self.root:
                color = COLORS['blue']
            else:
                color = COLORS['dim_white']
            self.push_port.send(mido.Message('note_on', note=pad_note, velocity=color))

        # Row 4: Scale selection (all available scales)
        for i, scale_name in enumerate(SCALE_NAMES):
            if i < 8:  # Max 8 scales on one row
                pad_note = 60 + i  # Row 4
                if scale_name == self.scale_name:
                    color = COLORS['green']
                else:
                    color = COLORS['dim_green']
                self.push_port.send(mido.Message('note_on', note=pad_note, velocity=color))

        # Row 6: In-Key / Chromatic toggle
        # Pad 76 = In-Key, Pad 77 = Chromatic
        self.push_port.send(mido.Message('note_on', note=76,
            velocity=COLORS['cyan'] if self.in_key_mode else COLORS['dim_white']))
        self.push_port.send(mido.Message('note_on', note=77,
            velocity=COLORS['cyan'] if not self.in_key_mode else COLORS['dim_white']))

    def clear_grid(self):
        """Turn off all pads."""
        for note in range(36, 100):
            self.push_port.send(mido.Message('note_on', note=note, velocity=0))

    def note_name(self, midi_note):
        """Get note name from MIDI note number."""
        return NOTE_NAMES[midi_note % 12] + str((midi_note // 12) - 1)

    def update_button_leds(self):
        """Update all button LEDs based on current state."""
        # Octave buttons - dim when at limit, solid when available
        # Check if we can go up (max root_note is 96)
        can_go_up = self.layout.root_note <= 84  # Leave room for the grid
        can_go_down = self.layout.root_note >= 12

        # Use velocity 4 for solid dim, 127 for solid bright
        if can_go_up:
            self._set_button_led_cc(BUTTONS['octave_up'], 4)  # Solid on
        else:
            self._set_button_led_cc(BUTTONS['octave_up'], 0)  # Off at limit

        if can_go_down:
            self._set_button_led_cc(BUTTONS['octave_down'], 4)  # Solid on
        else:
            self._set_button_led_cc(BUTTONS['octave_down'], 0)  # Off at limit

        # Accent button - bright when on, dim when off
        if self.accent_on:
            self._set_button_led_cc(BUTTONS['accent'], 4)  # Solid on
        else:
            self._set_button_led_cc(BUTTONS['accent'], 1)  # Dim

        # Scale button - bright when on scale page, dim otherwise
        if self.current_page == PAGE_SCALE:
            self._set_button_led_cc(BUTTONS['scale'], 4)  # Solid on
        else:
            self._set_button_led_cc(BUTTONS['scale'], 1)  # Dim

        # Play button - solid on to show ready
        self._set_button_led_cc(BUTTONS['play'], 4)

    def update_display(self):
        """Update LCD display based on current page."""
        if self.current_page == PAGE_PLAY:
            self._update_play_display()
        elif self.current_page == PAGE_SCALE:
            self._update_scale_display()

    def _update_play_display(self):
        """Update display for play page."""
        root_name = NOTE_NAMES[self.root]
        scale_display = f"{root_name} {self.scale_name.capitalize()}"
        octave = self.layout.get_octave()
        octave_display = f"Oct {octave}"
        mode_display = "In-Key" if self.in_key_mode else "Chromatic"

        self._set_lcd_segments(1, "open-push", scale_display, octave_display, mode_display)

        accent_display = "Accent: ON" if self.accent_on else "Accent: OFF"
        self._set_lcd_segments(2, accent_display, "Fourths", "", "")

        self._set_lcd_segments(3, "Oct Up/Down", "Accent", "Scale", "")
        self._set_lcd_segments(4, "Play the pads!", "", "", "v0.2")

    def _update_scale_display(self):
        """Update display for scale settings page."""
        root_name = NOTE_NAMES[self.root]

        self._set_lcd_segments(1, "SCALE SETTINGS", f"Root: {root_name}", f"{self.scale_name.capitalize()}", "")

        self._set_lcd_segments(2, "Row1-2: Root", "Row4: Scale", "", "")

        mode_display = "In-Key" if self.in_key_mode else "Chromatic"
        self._set_lcd_segments(3, "Row6: Mode", f"({mode_display})", "", "")

        self._set_lcd_segments(4, "Maj Min Dor Pent", "Blues Chrom", "", "Scale=Exit")

    def handle_octave_up(self):
        """Handle octave up button press."""
        octave = self.layout.shift_octave(+1)
        print(f"Octave Up -> {octave}")
        self.light_grid()
        self.update_button_leds()
        self.update_display()

    def handle_octave_down(self):
        """Handle octave down button press."""
        octave = self.layout.shift_octave(-1)
        print(f"Octave Down -> {octave}")
        self.light_grid()
        self.update_button_leds()
        self.update_display()

    def handle_accent_toggle(self):
        """Toggle accent (fixed velocity) mode."""
        self.accent_on = not self.accent_on
        print(f"Accent: {'ON (vel=127)' if self.accent_on else 'OFF'}")
        self.update_button_leds()
        self.update_display()

    def handle_scale_button(self):
        """Toggle between play and scale pages."""
        if self.current_page == PAGE_PLAY:
            self.current_page = PAGE_SCALE
            print("Entering Scale Settings page")
            self.light_scale_page_grid()
        else:
            self.current_page = PAGE_PLAY
            print("Returning to Play page")
            self.light_grid()
        self.update_button_leds()
        self.update_display()

    def handle_scale_page_pad(self, pad_note):
        """Handle pad press on scale settings page."""
        row = (pad_note - 36) // 8
        col = (pad_note - 36) % 8

        if row == 0 and col < 8:
            # Root note selection: C through G
            self.root = col
            print(f"Root set to: {NOTE_NAMES[self.root]}")
        elif row == 1 and col < 4:
            # Root note selection: G# through B
            self.root = 8 + col
            print(f"Root set to: {NOTE_NAMES[self.root]}")
        elif row == 3 and col < len(SCALE_NAMES):
            # Scale selection
            self.scale_name = SCALE_NAMES[col]
            self.scale = SCALES[self.scale_name]
            print(f"Scale set to: {self.scale_name}")
        elif row == 5 and col in [0, 1]:
            # In-Key / Chromatic toggle
            self.in_key_mode = (col == 0)
            print(f"Mode set to: {'In-Key' if self.in_key_mode else 'Chromatic'}")

        self.light_scale_page_grid()
        self.update_display()

    def handle_button_press(self, cc):
        """Handle button press (CC message with value > 0)."""
        if cc == BUTTONS['octave_up']:
            self.handle_octave_up()
        elif cc == BUTTONS['octave_down']:
            self.handle_octave_down()
        elif cc == BUTTONS['accent']:
            self.handle_accent_toggle()
        elif cc == BUTTONS['scale']:
            self.handle_scale_button()

    def run(self):
        """Main loop."""
        print()
        print("=" * 60)
        print("  open-push : Isomorphic Controller v0.2")
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
        print("  Scale:  C Minor (changeable)")
        print("  Colors: Blue=Root, White=Scale, Dim/Off=Other")
        print(f"  Channel: {self.midi_channel + 1}")
        print(f"  Velocity: {self.velocity_min}-{self.velocity_max} (curved)")
        print()
        print("  Controls:")
        print("    Octave Up/Down - Shift octave")
        print("    Accent - Toggle fixed velocity (127)")
        print("    Scale - Open scale settings page")
        print()
        print("  Press pads to play! Ctrl+C to exit.")
        print("=" * 60)
        print()

        with mido.open_output(self.push_out_name) as push_port:
            self.push_port = push_port

            # Wake up Push
            self._send_sysex(USER_MODE)
            time.sleep(0.1)

            # Initialize display and LEDs
            self.update_display()
            self.update_button_leds()
            self.light_grid()

            # Listen for input
            with mido.open_input(self.push_in_name) as in_port:
                try:
                    for msg in in_port:
                        if msg.type == 'note_on':
                            pad_note = msg.note
                            velocity = msg.velocity

                            if 36 <= pad_note <= 99:  # Pad range
                                if self.current_page == PAGE_SCALE:
                                    # Handle scale page pad selection
                                    if velocity > 0:
                                        self.handle_scale_page_pad(pad_note)
                                else:
                                    # Play mode - send MIDI notes
                                    midi_note = self.get_midi_note_for_pad(pad_note)

                                    if velocity > 0:
                                        # Note on
                                        self.active_notes[pad_note] = midi_note

                                        # Apply velocity curve (or accent override)
                                        if self.accent_on:
                                            out_velocity = 127
                                        else:
                                            out_velocity = self.apply_velocity_curve(velocity)

                                        print(f"ON:  Pad {pad_note:2d} -> {self.note_name(midi_note):4s} (MIDI {midi_note}, vel {velocity}->{out_velocity})")

                                        # Flash pad brighter
                                        push_port.send(mido.Message('note_on', note=pad_note, velocity=COLORS['green']))

                                        # Send MIDI to virtual port -> DAW
                                        if self.virtual_out:
                                            self.virtual_out.send(mido.Message('note_on', note=midi_note, velocity=out_velocity, channel=self.midi_channel))

                                    else:
                                        # Note off (velocity 0)
                                        if pad_note in self.active_notes:
                                            midi_note = self.active_notes.pop(pad_note)
                                            print(f"OFF: Pad {pad_note:2d} -> {self.note_name(midi_note):4s}")

                                            # Restore pad color
                                            row = (pad_note - 36) // 8
                                            col = (pad_note - 36) % 8
                                            color = self.get_pad_color(row, col)
                                            push_port.send(mido.Message('note_on', note=pad_note, velocity=color))

                                            # Send MIDI off
                                            if self.virtual_out:
                                                self.virtual_out.send(mido.Message('note_off', note=midi_note, velocity=0, channel=self.midi_channel))

                        elif msg.type == 'note_off':
                            pad_note = msg.note
                            if 36 <= pad_note <= 99 and pad_note in self.active_notes:
                                midi_note = self.active_notes.pop(pad_note)
                                print(f"OFF: Pad {pad_note:2d} -> {self.note_name(midi_note):4s}")

                                row = (pad_note - 36) // 8
                                col = (pad_note - 36) % 8
                                color = self.get_pad_color(row, col)
                                push_port.send(mido.Message('note_on', note=pad_note, velocity=color))

                                if self.virtual_out:
                                    self.virtual_out.send(mido.Message('note_off', note=midi_note, velocity=0, channel=self.midi_channel))

                        elif msg.type == 'control_change':
                            # Handle button presses
                            if msg.value > 0:  # Button pressed (not released)
                                self.handle_button_press(msg.control)

                except KeyboardInterrupt:
                    print("\n\nShutting down...")

            # Cleanup
            print("Cleaning up...")
            self.clear_grid()

            # Turn off all button LEDs we used
            for button in ['octave_up', 'octave_down', 'accent', 'scale', 'play']:
                self._set_button_led(button, 'off')

            for line in range(1, 5):
                self._set_lcd_segments(line, "", "", "", "")

            self.push_port = None

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
