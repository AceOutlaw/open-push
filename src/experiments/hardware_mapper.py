#!/usr/bin/env python3
"""
Hardware Mapper for Push 1

Listens to all MIDI input from Push and logs every message.
Useful for:
- Verifying CC mappings
- Discovering undocumented behaviors
- Creating a definitive hardware reference

Usage:
    python3 src/experiments/hardware_mapper.py

Modes:
    listen  - Passive listening, logs everything
    guided  - Prompts you to press specific controls
    export  - Export collected mappings to JSON

Controls:
    l - Switch to listen mode
    g - Switch to guided mode
    e - Export mappings to JSON
    c - Clear collected data
    s - Show summary of collected data
    q - Quit
"""

import mido
import time
import json
import os
from datetime import datetime
from collections import defaultdict

# Known mappings from documentation (for verification)
KNOWN_BUTTONS = {
    3: 'tap_tempo', 9: 'metronome',
    85: 'play', 86: 'record', 29: 'stop',
    119: 'undo', 118: 'delete', 116: 'quantize',
    90: 'fixed_length', 117: 'double_loop', 89: 'automation',
    88: 'duplicate', 87: 'new',
    114: 'volume', 115: 'pan_send',
    112: 'track', 113: 'clip',
    110: 'device', 111: 'browse',
    28: 'master',
    50: 'note', 51: 'session',
    58: 'scale', 59: 'user',
    54: 'octave_down', 55: 'octave_up',
    57: 'accent', 56: 'repeat',
    60: 'mute', 61: 'solo',
    44: 'left', 45: 'right', 46: 'up', 47: 'down',
    62: 'page_left', 63: 'page_right',
    48: 'select', 49: 'shift',
    36: '1/4', 37: '1/4t', 38: '1/8', 39: '1/8t',
    40: '1/16', 41: '1/16t', 42: '1/32', 43: '1/32t',
    # Upper row below LCD
    102: 'upper_1', 103: 'upper_2', 104: 'upper_3', 105: 'upper_4',
    106: 'upper_5', 107: 'upper_6', 108: 'upper_7', 109: 'upper_8',
    # Lower row below LCD
    20: 'lower_1', 21: 'lower_2', 22: 'lower_3', 23: 'lower_4',
    24: 'lower_5', 25: 'lower_6', 26: 'lower_7', 27: 'lower_8',
}

KNOWN_ENCODERS = {
    14: ('tempo', 10),      # (name, touch_note)
    15: ('swing', 9),
    71: ('track_1', 0), 72: ('track_2', 1), 73: ('track_3', 2), 74: ('track_4', 3),
    75: ('track_5', 4), 76: ('track_6', 5), 77: ('track_7', 6), 78: ('track_8', 7),
    79: ('master', 8),
}

# Guided mode prompts
GUIDED_PROMPTS = [
    # Transport
    ("Press TAP TEMPO button", "tap_tempo", "cc", 3),
    ("Press METRONOME button", "metronome", "cc", 9),
    ("Press PLAY button", "play", "cc", 85),
    ("Press RECORD button", "record", "cc", 86),
    ("Press STOP button", "stop", "cc", 29),
    # Editing
    ("Press UNDO button", "undo", "cc", 119),
    ("Press DELETE button", "delete", "cc", 118),
    ("Press QUANTIZE button", "quantize", "cc", 116),
    ("Press FIXED LENGTH button", "fixed_length", "cc", 90),
    ("Press DOUBLE LOOP button", "double_loop", "cc", 117),
    ("Press DUPLICATE button", "duplicate", "cc", 88),
    ("Press NEW button", "new", "cc", 87),
    # Mode buttons
    ("Press NOTE button", "note", "cc", 50),
    ("Press SESSION button", "session", "cc", 51),
    ("Press SCALE button", "scale", "cc", 58),
    ("Press SHIFT button", "shift", "cc", 49),
    ("Press SELECT button", "select", "cc", 48),
    # Navigation
    ("Press LEFT arrow", "left", "cc", 44),
    ("Press RIGHT arrow", "right", "cc", 45),
    ("Press UP arrow", "up", "cc", 46),
    ("Press DOWN arrow", "down", "cc", 47),
    # Encoders
    ("Turn TEMPO encoder", "tempo_enc", "cc", 14),
    ("Turn SWING encoder", "swing_enc", "cc", 15),
    ("Turn ENCODER 1 (leftmost above display)", "track_1", "cc", 71),
    ("Turn MASTER encoder", "master_enc", "cc", 79),
    # Touch
    ("Touch TEMPO encoder (don't turn)", "tempo_touch", "note", 10),
    ("Touch ENCODER 1", "track_1_touch", "note", 0),
    # Pads
    ("Press bottom-left PAD", "pad_36", "note", 36),
    ("Press top-right PAD", "pad_99", "note", 99),
    # Touch strip
    ("Touch the TOUCH STRIP", "touch_strip", "note", 12),
    ("Slide on TOUCH STRIP", "touch_strip_bend", "pitchwheel", None),
]


class HardwareMapper:
    def __init__(self):
        self.push_in = None
        self.push_out = None
        self.running = False
        self.mode = 'listen'

        # Collected data
        self.cc_messages = defaultdict(list)  # cc_number -> [(value, timestamp), ...]
        self.note_messages = defaultdict(list)  # note_number -> [(velocity, timestamp), ...]
        self.pitchwheel_messages = []
        self.aftertouch_messages = []
        self.sysex_messages = []

        # Verification results
        self.verified = {}
        self.unknown = {}

    def connect(self):
        """Connect to Push 1 ports."""
        for port_name in mido.get_input_names():
            if 'Ableton Push' in port_name and 'User' in port_name:
                self.push_in = mido.open_input(port_name)
                print(f"Input connected: {port_name}")
                break

        for port_name in mido.get_output_names():
            if 'Ableton Push' in port_name and 'User' in port_name:
                self.push_out = mido.open_output(port_name)
                print(f"Output connected: {port_name}")
                break

        if not self.push_in:
            print("ERROR: Push 1 User Port (input) not found")
            return False

        return True

    def set_user_mode(self):
        """Switch Push to User Mode."""
        if self.push_out:
            sysex_data = [0x47, 0x7F, 0x15, 0x62, 0x00, 0x01, 0x01]
            self.push_out.send(mido.Message('sysex', data=sysex_data))
            time.sleep(0.1)

    def process_message(self, msg):
        """Process and log a MIDI message."""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        if msg.type == 'control_change':
            cc = msg.control
            value = msg.value
            self.cc_messages[cc].append((value, timestamp))

            # Check against known mappings
            known_name = KNOWN_BUTTONS.get(cc) or (KNOWN_ENCODERS.get(cc, [None])[0])

            if known_name:
                status = f"[VERIFIED: {known_name}]"
                self.verified[cc] = known_name
            else:
                status = "[UNKNOWN]"
                self.unknown[cc] = f"cc_{cc}"

            # Determine if it's a button (0/127) or encoder (relative)
            if value == 127:
                action = "PRESSED"
            elif value == 0:
                action = "RELEASED"
            elif value < 64:
                action = f"CW +{value}"
            else:
                action = f"CCW -{128-value}"

            print(f"{timestamp} | CC {cc:3d} | {action:12} | {status}")

        elif msg.type == 'note_on':
            note = msg.note
            vel = msg.velocity
            self.note_messages[note].append((vel, timestamp))

            # Check if it's a pad (36-99) or encoder touch (0-10) or touch strip (12)
            if 36 <= note <= 99:
                row = (note - 36) // 8
                col = (note - 36) % 8
                desc = f"PAD row={row} col={col}"
            elif note <= 10:
                enc_name = None
                for cc, (name, touch) in KNOWN_ENCODERS.items():
                    if touch == note:
                        enc_name = name
                        break
                desc = f"ENCODER TOUCH ({enc_name})" if enc_name else f"ENCODER TOUCH"
            elif note == 12:
                desc = "TOUCH STRIP"
            else:
                desc = "UNKNOWN"

            action = "TOUCH" if vel > 0 else "RELEASE"
            print(f"{timestamp} | Note {note:3d} | vel={vel:3d} {action:8} | {desc}")

        elif msg.type == 'note_off':
            note = msg.note
            self.note_messages[note].append((0, timestamp))
            print(f"{timestamp} | Note {note:3d} | RELEASE")

        elif msg.type == 'pitchwheel':
            self.pitchwheel_messages.append((msg.pitch, timestamp))
            # Normalize to 0-100 for display
            normalized = int((msg.pitch + 8192) / 16383 * 100)
            print(f"{timestamp} | PitchWheel | value={msg.pitch:6d} ({normalized:3d}%)")

        elif msg.type == 'aftertouch':
            self.aftertouch_messages.append((msg.value, timestamp))
            print(f"{timestamp} | Aftertouch | value={msg.value}")

        elif msg.type == 'polytouch':
            print(f"{timestamp} | PolyTouch  | note={msg.note} value={msg.value}")

        elif msg.type == 'sysex':
            self.sysex_messages.append((list(msg.data), timestamp))
            data_hex = ' '.join(f'{b:02X}' for b in msg.data[:20])
            if len(msg.data) > 20:
                data_hex += '...'
            print(f"{timestamp} | SysEx      | {data_hex}")

    def listen_mode(self):
        """Passive listening mode."""
        print("\n" + "=" * 60)
        print("LISTEN MODE - Press any control on Push")
        print("All MIDI messages will be logged")
        print("Press Ctrl+C to return to menu")
        print("=" * 60 + "\n")

        try:
            while self.mode == 'listen':
                for msg in self.push_in.iter_pending():
                    self.process_message(msg)
                time.sleep(0.01)
        except KeyboardInterrupt:
            print("\n\nReturning to menu...")

    def guided_mode(self):
        """Guided verification mode."""
        print("\n" + "=" * 60)
        print("GUIDED MODE - Follow prompts to verify mappings")
        print("Press Enter after each control, 's' to skip, 'q' to quit")
        print("=" * 60 + "\n")

        for prompt, name, msg_type, expected in GUIDED_PROMPTS:
            print(f"\n>> {prompt}")
            print(f"   Expected: {msg_type} {expected}")

            # Wait for input
            user_input = input("   Press the control, then Enter (s=skip, q=quit): ")

            if user_input.lower() == 'q':
                break
            if user_input.lower() == 's':
                print("   Skipped")
                continue

            # Check what we received
            received = None
            for msg in self.push_in.iter_pending():
                self.process_message(msg)

                if msg_type == 'cc' and msg.type == 'control_change':
                    received = msg.control
                elif msg_type == 'note' and msg.type in ['note_on', 'note_off']:
                    received = msg.note
                elif msg_type == 'pitchwheel' and msg.type == 'pitchwheel':
                    received = 'pitchwheel'

            if received == expected or (expected is None and received):
                print(f"   ✓ VERIFIED: {name} = {received}")
                self.verified[expected or received] = name
            elif received:
                print(f"   ✗ MISMATCH: Expected {expected}, got {received}")
            else:
                print(f"   ? No message received")

    def show_summary(self):
        """Show summary of collected data."""
        print("\n" + "=" * 60)
        print("COLLECTED DATA SUMMARY")
        print("=" * 60)

        print(f"\nCC Messages: {len(self.cc_messages)} unique controls")
        for cc in sorted(self.cc_messages.keys()):
            count = len(self.cc_messages[cc])
            known = KNOWN_BUTTONS.get(cc) or (KNOWN_ENCODERS.get(cc, [None])[0])
            status = f"({known})" if known else "(unknown)"
            print(f"  CC {cc:3d}: {count:4d} messages {status}")

        print(f"\nNote Messages: {len(self.note_messages)} unique notes")
        for note in sorted(self.note_messages.keys()):
            count = len(self.note_messages[note])
            if 36 <= note <= 99:
                desc = f"pad row={(note-36)//8} col={(note-36)%8}"
            elif note <= 10:
                desc = "encoder touch"
            elif note == 12:
                desc = "touch strip"
            else:
                desc = ""
            print(f"  Note {note:3d}: {count:4d} messages {desc}")

        print(f"\nPitchwheel Messages: {len(self.pitchwheel_messages)}")
        print(f"Aftertouch Messages: {len(self.aftertouch_messages)}")
        print(f"SysEx Messages: {len(self.sysex_messages)}")

        print(f"\nVerified: {len(self.verified)}")
        print(f"Unknown: {len(self.unknown)}")

    def export_mappings(self):
        """Export collected mappings to JSON."""
        export_data = {
            'timestamp': datetime.now().isoformat(),
            'verified': self.verified,
            'unknown': self.unknown,
            'cc_controls': {str(k): len(v) for k, v in self.cc_messages.items()},
            'notes': {str(k): len(v) for k, v in self.note_messages.items()},
            'pitchwheel_count': len(self.pitchwheel_messages),
            'aftertouch_count': len(self.aftertouch_messages),
            'sysex_count': len(self.sysex_messages),
        }

        filename = f"push1_mapping_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(os.path.dirname(__file__), filename)

        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f"\nExported to: {filepath}")

    def clear_data(self):
        """Clear all collected data."""
        self.cc_messages.clear()
        self.note_messages.clear()
        self.pitchwheel_messages.clear()
        self.aftertouch_messages.clear()
        self.sysex_messages.clear()
        self.verified.clear()
        self.unknown.clear()
        print("All collected data cleared.")

    def show_menu(self):
        """Show main menu."""
        print("\n" + "=" * 50)
        print("Push 1 Hardware Mapper")
        print("=" * 50)
        print("Commands:")
        print("  l - Listen mode (passive logging)")
        print("  g - Guided mode (verification prompts)")
        print("  s - Show summary of collected data")
        print("  e - Export mappings to JSON")
        print("  c - Clear collected data")
        print("  q - Quit")
        print("=" * 50)

    def run(self):
        """Main run loop."""
        if not self.connect():
            return

        self.set_user_mode()
        self.show_menu()

        self.running = True
        while self.running:
            try:
                cmd = input("\nCommand: ").strip().lower()

                if cmd == 'q':
                    self.running = False
                elif cmd == 'l':
                    self.mode = 'listen'
                    self.listen_mode()
                    self.show_menu()
                elif cmd == 'g':
                    self.mode = 'guided'
                    self.guided_mode()
                    self.show_menu()
                elif cmd == 's':
                    self.show_summary()
                elif cmd == 'e':
                    self.export_mappings()
                elif cmd == 'c':
                    self.clear_data()
                else:
                    print("Unknown command. Try: l, g, s, e, c, q")

            except KeyboardInterrupt:
                print("\n")
                self.show_menu()

        if self.push_in:
            self.push_in.close()
        if self.push_out:
            self.push_out.close()

        print("\nHardware Mapper closed.")


if __name__ == "__main__":
    mapper = HardwareMapper()
    mapper.run()
