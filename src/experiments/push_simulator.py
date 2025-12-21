#!/usr/bin/env python3
"""
Push 1 Terminal Simulator

A terminal-based simulator for Ableton Push 1.
Uses keyboard input to simulate button/pad presses.
Displays LCD text and pad colors in terminal.

Usage:
    python3 push_simulator.py

Controls:
    1-8     : Upper LCD buttons (CC 102-109)
    q-i     : Lower LCD buttons (CC 20-27)
    Space   : Play (CC 85)
    r       : Record (CC 86)
    s       : Stop (CC 29)
    [/]     : Octave Down/Up
    n       : Note mode (CC 50)
    m       : Session mode (CC 51)
    z       : Scale mode (CC 58)
    Arrows  : Navigation
    Escape  : Quit
"""

import mido
import threading
import time
import sys
import select
import os

# Try to use termios for raw keyboard input
try:
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False

# ANSI color codes
RESET = '\033[0m'
ORANGE = '\033[38;5;208m'
DIM = '\033[2m'
BOLD = '\033[1m'
BG_BLACK = '\033[40m'
CLEAR_SCREEN = '\033[2J\033[H'

# Push 1 Constants
SYSEX_HEADER = [0x47, 0x7F, 0x15]

# Keyboard to CC mapping
KEY_MAP = {
    # Upper LCD buttons (1-8) -> CC 102-109
    '1': 102, '2': 103, '3': 104, '4': 105,
    '5': 106, '6': 107, '7': 108, '8': 109,
    # Lower LCD buttons (q-i) -> CC 20-27
    'q': 20, 'w': 21, 'e': 22, 'r': 23,
    't': 24, 'y': 25, 'u': 26, 'i': 27,
    # Transport
    ' ': 85,   # Space = Play
    'p': 86,   # p = Record
    's': 29,   # s = Stop
    # Mode
    'n': 50,   # Note
    'm': 51,   # Session
    'z': 58,   # Scale
    'x': 59,   # User
    # Octave
    '[': 54,   # Octave down
    ']': 55,   # Octave up
    # Navigation (will handle arrows separately)
    'h': 44,   # Left
    'l': 45,   # Right
    'k': 46,   # Up
    'j': 47,   # Down
    # Other
    'v': 114,  # Volume
    'b': 112,  # Track
    'd': 110,  # Device
}

# Pad keyboard mapping (a-; for bottom row, etc)
PAD_KEYS = {
    # Bottom row (notes 36-43)
    'a': 36, 'o': 37, 'f': 38, 'g': 39,
    # ... simplified for demo
}


class TerminalSimulator:
    def __init__(self):
        self.midi_out = None
        self.midi_in = None
        self.running = True
        self.lcd_lines = ["", "", "", ""]
        self.button_states = {}
        self.old_settings = None

    def _connect_midi(self):
        """Connect to MIDI ports."""
        try:
            self.midi_out = mido.open_output("Push Simulator", virtual=True)
            self.midi_in = mido.open_input("Push Simulator", virtual=True)
            return True
        except Exception as e:
            print(f"MIDI Error: {e}")
            return False

    def _start_midi_listener(self):
        """Listen for MIDI from app."""
        def listen():
            while self.running:
                if self.midi_in:
                    for msg in self.midi_in.iter_pending():
                        self._handle_midi(msg)
                time.sleep(0.02)
        threading.Thread(target=listen, daemon=True).start()

    def _handle_midi(self, msg):
        """Handle incoming MIDI (LED/LCD updates)."""
        if msg.type == 'sysex':
            self._handle_sysex(msg.data)
        elif msg.type == 'control_change':
            self.button_states[msg.control] = msg.value
        elif msg.type == 'note_on':
            pass  # Pad color updates

    def _handle_sysex(self, data):
        """Parse SysEx for LCD updates."""
        data = list(data)
        if len(data) < 4 or data[0:3] != SYSEX_HEADER:
            return

        # LCD update
        if len(data) > 7 and data[4] == 0x00 and data[5] == 0x45:
            line_map = {0x18: 0, 0x19: 1, 0x1A: 2, 0x1B: 3}
            if data[3] in line_map:
                idx = line_map[data[3]]
                text = ''.join(chr(b) if 32 <= b < 127 else ' ' for b in data[7:])
                self.lcd_lines[idx] = text
                self._redraw()

    def _send_button(self, cc, value):
        """Send button CC."""
        if self.midi_out:
            self.midi_out.send(mido.Message('control_change', control=cc, value=value))

    def _send_pad(self, note, velocity):
        """Send pad note."""
        if self.midi_out:
            msg_type = 'note_on' if velocity > 0 else 'note_off'
            self.midi_out.send(mido.Message(msg_type, note=note, velocity=velocity))

    def _redraw(self):
        """Redraw the terminal display."""
        # Move cursor to home
        print('\033[H', end='')

        print(f"\n{BOLD}  Push 1 Simulator{RESET} (Terminal Mode)")
        print("  " + "=" * 50)

        # LCD Display
        print(f"\n  {BG_BLACK}╔{'═' * 70}╗{RESET}")
        for i, line in enumerate(self.lcd_lines):
            text = line[:68].ljust(68) if line else " " * 68
            print(f"  {BG_BLACK}║ {ORANGE}{text}{RESET} {BG_BLACK}║{RESET}")
        print(f"  {BG_BLACK}╚{'═' * 70}╝{RESET}")

        # Button indicators
        upper = "  Upper: "
        for cc in range(102, 110):
            state = self.button_states.get(cc, 0)
            marker = "●" if state >= 4 else "○" if state > 0 else "·"
            upper += f" {marker} "
        print(upper)

        lower = "  Lower: "
        for cc in range(20, 28):
            state = self.button_states.get(cc, 0)
            marker = "●" if state >= 4 else "○" if state > 0 else "·"
            lower += f" {marker} "
        print(lower)

        print("\n  " + "-" * 50)
        print(f"  {DIM}Keys: 1-8=Upper | q-i=Lower | Space=Play | n=Note | z=Scale{RESET}")
        print(f"  {DIM}      [/]=Octave | v=Vol | b=Track | d=Device | Esc=Quit{RESET}")

    def _get_key(self):
        """Get a single keypress."""
        if not HAS_TERMIOS:
            return None

        if select.select([sys.stdin], [], [], 0.05)[0]:
            return sys.stdin.read(1)
        return None

    def run(self):
        """Main loop."""
        if not self._connect_midi():
            print("Failed to connect MIDI. Exiting.")
            return

        print(CLEAR_SCREEN)
        print("\n" + "=" * 50)
        print("  Push 1 Terminal Simulator")
        print("=" * 50)
        print("\nMIDI port 'Push Simulator' created.")
        print("Run: python3 src/open_push/reason/app.py")
        print("\nPress any key to start, Escape to quit...")

        self._start_midi_listener()

        if HAS_TERMIOS:
            # Set terminal to raw mode
            self.old_settings = termios.tcgetattr(sys.stdin)
            try:
                tty.setcbreak(sys.stdin.fileno())

                self._redraw()

                while self.running:
                    key = self._get_key()
                    if key:
                        if key == '\x1b':  # Escape
                            self.running = False
                            break
                        elif key in KEY_MAP:
                            cc = KEY_MAP[key]
                            self._send_button(cc, 127)
                            time.sleep(0.05)
                            self._send_button(cc, 0)
                            print(f"\r  → Sent CC {cc}             ", end='')
                        elif key in PAD_KEYS:
                            note = PAD_KEYS[key]
                            self._send_pad(note, 100)
                            time.sleep(0.05)
                            self._send_pad(note, 0)
                            print(f"\r  → Sent Note {note}          ", end='')

                    time.sleep(0.02)

            finally:
                # Restore terminal
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)
        else:
            print("\nTerminal raw mode not available.")
            print("Running in passive mode - LCD display only.")
            print("Press Ctrl+C to quit.\n")

            try:
                while self.running:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                pass

        print("\n\nSimulator closed.")

        if self.midi_out:
            self.midi_out.close()
        if self.midi_in:
            self.midi_in.close()


if __name__ == '__main__':
    TerminalSimulator().run()
