#!/usr/bin/env python3
"""
Piano Roll LCD Display Experiment

Displays a step sequencer / piano roll on Push 1's 4-line LCD.
- 4 lines = 4 pitch rows visible at a time
- 17 chars per segment = 16 steps + 1 bar marker
- Up/Down buttons scroll through octaves
- Solid block (char 2) = note on
- Dot = note off
- Playhead moves across the display

Run: python3 src/experiments/piano_roll_display.py
"""

import mido
import time
import sys
import select
import random

# Push 1 SysEx
SYSEX_HEADER = [0x47, 0x7F, 0x15]
LCD_LINES = {1: 0x18, 2: 0x19, 3: 0x1A, 4: 0x1B}

# Characters
BLOCK = chr(5)      # Note on (0x05)
EMPTY = ' '         # Empty step - no note
BAR = '|'           # Bar marker (between bars)
PLAYHEAD = '>'      # Playhead position

# Button CCs
BUTTONS = {
    'up': 46,
    'down': 47,
    'left': 44,
    'right': 45,
    'play': 85,
    'stop': 29,
    'session': 51,  # Exit
}

# Note names for display
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

def get_note_name(midi_note):
    """Convert MIDI note to name like C4, D#5"""
    octave = (midi_note // 12) - 1
    note = NOTE_NAMES[midi_note % 12]
    return f"{note}{octave}"


class PianoRollDisplay:
    def __init__(self):
        self.push_in = None
        self.push_out = None
        self.running = True

        # Sequencer state
        self.steps = 64  # 4 bars of 16th notes
        self.rows = 12   # One octave visible range (scrollable)
        self.base_note = 60  # C4 - bottom visible note

        # Pattern storage: dict of {(row, step): velocity}
        self.pattern = {}

        # Playhead
        self.playhead_pos = 0
        self.playing = False
        self.last_step_time = time.time()
        self.step_duration = 0.125  # 16th notes at 120 BPM

        # View offset
        self.view_offset_x = 0  # Horizontal scroll (in steps)

        # Initialize with a demo pattern
        self._init_demo_pattern()

    def _init_demo_pattern(self):
        """Create a demo drum pattern or melody."""
        # Simple drum pattern (4 lanes: kick, snare, hihat, perc)
        # Using notes 36-39 (bottom 4 rows)

        # Kick on 1 and 3
        for bar in range(4):
            self.pattern[(0, bar * 16 + 0)] = 127   # Beat 1
            self.pattern[(0, bar * 16 + 8)] = 100   # Beat 3

        # Snare on 2 and 4
        for bar in range(4):
            self.pattern[(1, bar * 16 + 4)] = 127   # Beat 2
            self.pattern[(1, bar * 16 + 12)] = 127  # Beat 4

        # Hi-hat 8ths
        for step in range(0, 64, 2):
            self.pattern[(2, step)] = 80

        # Some percussion accents
        for step in [3, 7, 11, 19, 23, 35, 51]:
            self.pattern[(3, step)] = random.randint(60, 100)

    def connect(self):
        """Connect to Push hardware."""
        # Find Push
        for name in mido.get_input_names():
            if 'Ableton Push' in name and 'User' in name:
                self.push_in = mido.open_input(name)
                print(f"Input: {name}")
                break

        for name in mido.get_output_names():
            if 'Ableton Push' in name and 'User' in name:
                self.push_out = mido.open_output(name)
                print(f"Output: {name}")
                break

        if not self.push_in or not self.push_out:
            print("ERROR: Push not found!")
            return False

        # Wake up Push
        self._send_sysex([0x62, 0x00, 0x01, 0x01])
        time.sleep(0.1)
        return True

    def _send_sysex(self, data):
        """Send SysEx to Push."""
        self.push_out.send(mido.Message('sysex', data=SYSEX_HEADER + data))

    def set_lcd_line(self, line, text):
        """Set a full LCD line (68 chars)."""
        text = text[:68].ljust(68)
        line_addr = LCD_LINES[line]
        data = SYSEX_HEADER + [line_addr, 0x00, 0x45, 0x00]
        data.extend([ord(c) if ord(c) < 128 else ord('?') for c in text])
        self.push_out.send(mido.Message('sysex', data=data))

    def set_button_led(self, cc, value):
        """Set button LED. value: 0=off, 1=dim, 4=bright"""
        self.push_out.send(mido.Message('control_change', control=cc, value=value))

    def render_piano_roll(self):
        """Render the pattern to LCD.

        Layout: 4 segments x 17 chars = 68 chars
        Each segment = 16 steps + 1 bar separator
        Total = 64 steps visible (4 bars)
        """
        for row_offset in range(4):
            row_idx = 3 - row_offset  # Invert so higher pitches are on top

            line = ""

            for seg in range(4):
                for step_in_seg in range(16):
                    step = self.view_offset_x + (seg * 16) + step_in_seg

                    if (row_idx, step) in self.pattern:
                        line += BLOCK
                    elif step == self.playhead_pos and self.playing:
                        line += PLAYHEAD
                    else:
                        line += EMPTY

                line += BAR

            self.set_lcd_line(row_offset + 1, line[:68])

    def render_status_bar(self):
        """Show status on line 4 instead of pattern."""
        note_name = get_note_name(self.base_note)
        top_note = get_note_name(self.base_note + 3)
        status = f"Range: {note_name}-{top_note}"
        playing = "PLAY" if self.playing else "STOP"
        pos = f"Step: {self.playhead_pos + 1}/{self.steps}"

        # Format for 4 segments
        line = f"{status:^17}{playing:^17}{pos:^17}{'UP/DN=Scroll':^17}"
        self.set_lcd_line(4, line[:68])

    def render_with_labels(self):
        """Render with pitch labels on the left edge.

        Line format: "C4" + 16 steps per segment
        First segment has 2-char label + 14 steps + bar
        Other segments have 16 steps + bar
        """
        for row_offset in range(4):
            row_idx = 3 - row_offset  # Higher pitches on top
            midi_note = self.base_note + row_idx
            note_name = get_note_name(midi_note)[:2].ljust(2)

            line = note_name  # Start with label

            # First segment: 14 steps after 2-char label
            for step_in_seg in range(14):
                step = self.view_offset_x + step_in_seg
                if (row_idx, step) in self.pattern:
                    line += BLOCK
                elif step == self.playhead_pos and self.playing:
                    line += PLAYHEAD
                else:
                    line += EMPTY
            line += BAR

            # Remaining 3 segments: 16 steps each
            for seg in range(1, 4):
                for step_in_seg in range(16):
                    step = self.view_offset_x + 14 + ((seg - 1) * 16) + step_in_seg
                    if (row_idx, step) in self.pattern:
                        line += BLOCK
                    elif step == self.playhead_pos and self.playing:
                        line += PLAYHEAD
                    else:
                        line += EMPTY
                line += BAR

            self.set_lcd_line(row_offset + 1, line[:68])

    def render_drum_mode(self):
        """Render for drums with lane names.

        Layout: 4 segments x 17 chars = 68 chars
        Each segment = 16 steps + 1 bar separator
        Total = 64 steps visible (4 bars of 16th notes)
        """
        drum_names = ['KICK', 'SNAR', 'HHAT', 'PERC']

        for row_offset in range(4):
            row_idx = row_offset

            line = ""

            for seg in range(4):
                # 16 steps per segment
                for step_in_seg in range(16):
                    step = self.view_offset_x + (seg * 16) + step_in_seg

                    if (row_idx, step) in self.pattern:
                        line += BLOCK
                    elif step == self.playhead_pos and self.playing:
                        line += PLAYHEAD
                    else:
                        line += EMPTY

                # Bar separator after each 16 steps
                line += BAR

            self.set_lcd_line(row_offset + 1, line[:68])

    def handle_button(self, cc, value):
        """Handle button presses."""
        if value == 0:  # Release
            return

        if cc == BUTTONS['up']:
            # Scroll up (show higher pitches)
            self.base_note = min(108, self.base_note + 1)
            print(f"Scrolled up: base note = {get_note_name(self.base_note)}")

        elif cc == BUTTONS['down']:
            # Scroll down (show lower pitches)
            self.base_note = max(24, self.base_note - 1)
            print(f"Scrolled down: base note = {get_note_name(self.base_note)}")

        elif cc == BUTTONS['left']:
            # Scroll left in time
            self.view_offset_x = max(0, self.view_offset_x - 16)
            print(f"Scrolled left: offset = {self.view_offset_x}")

        elif cc == BUTTONS['right']:
            # Scroll right in time
            self.view_offset_x = min(self.steps - 64, self.view_offset_x + 16)
            print(f"Scrolled right: offset = {self.view_offset_x}")

        elif cc == BUTTONS['play']:
            self.playing = not self.playing
            print(f"Playing: {self.playing}")

        elif cc == BUTTONS['stop']:
            self.playing = False
            self.playhead_pos = 0
            print("Stopped and reset")

        elif cc == BUTTONS['session']:
            self.running = False
            print("Exiting...")

    def advance_playhead(self):
        """Advance playhead based on tempo."""
        if not self.playing:
            return

        now = time.time()
        if now - self.last_step_time >= self.step_duration:
            self.playhead_pos = (self.playhead_pos + 1) % self.steps
            self.last_step_time = now

    def init_ui(self):
        """Initialize button LEDs."""
        self.set_button_led(BUTTONS['up'], 4)
        self.set_button_led(BUTTONS['down'], 4)
        self.set_button_led(BUTTONS['left'], 4)
        self.set_button_led(BUTTONS['right'], 4)
        self.set_button_led(BUTTONS['play'], 1)
        self.set_button_led(BUTTONS['stop'], 4)
        self.set_button_led(BUTTONS['session'], 1)

    def cleanup(self):
        """Clean up on exit."""
        # Clear display
        for line in range(1, 5):
            self.set_lcd_line(line, "")

        # Turn off button LEDs
        for cc in BUTTONS.values():
            self.set_button_led(cc, 0)

    def run(self):
        """Main loop."""
        if not self.connect():
            return

        self.init_ui()

        print("\n=== Piano Roll Display Experiment ===")
        print("Up/Down: Scroll pitches")
        print("Left/Right: Scroll time")
        print("Play: Start/stop playhead")
        print("Stop: Reset to beginning")
        print("Session: Exit")
        print("\nKeyboard: d=drum mode, p=piano mode, l=labeled mode, q=quit")
        print("=" * 40)

        render_mode = 'drum'  # 'drum', 'piano', 'labeled'

        try:
            while self.running:
                # Advance playhead
                self.advance_playhead()

                # Render based on mode
                if render_mode == 'drum':
                    self.render_drum_mode()
                elif render_mode == 'labeled':
                    self.render_with_labels()
                else:
                    self.render_piano_roll()

                # Handle Push input
                for msg in self.push_in.iter_pending():
                    if msg.type == 'control_change':
                        self.handle_button(msg.control, msg.value)

                # Handle keyboard input
                if select.select([sys.stdin], [], [], 0)[0]:
                    key = sys.stdin.read(1).lower()
                    if key == 'q':
                        self.running = False
                    elif key == 'd':
                        render_mode = 'drum'
                        print("Mode: Drum")
                    elif key == 'p':
                        render_mode = 'piano'
                        print("Mode: Piano roll")
                    elif key == 'l':
                        render_mode = 'labeled'
                        print("Mode: Labeled piano")
                    elif key == ' ':
                        self.playing = not self.playing
                        print(f"Playing: {self.playing}")

                time.sleep(0.02)  # ~50fps update

        except KeyboardInterrupt:
            print("\nInterrupted")

        finally:
            self.cleanup()
            print("Done!")


def main():
    app = PianoRollDisplay()
    app.run()


if __name__ == '__main__':
    main()
