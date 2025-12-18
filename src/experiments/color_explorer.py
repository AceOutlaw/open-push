#!/usr/bin/env python3
"""
Push 1 Color Explorer
=====================
Cycle through velocity values to see exactly what colors Push 1 supports.
This will answer: Does Push 1 have full RGB or a fixed palette?

Usage:
    python color_explorer.py
"""

import mido
import time
import sys

SYSEX_HEADER = [0x47, 0x7F, 0x15]
USER_MODE = [0x62, 0x00, 0x01, 0x01]

def find_push():
    """Find Push MIDI ports."""
    for name in mido.get_output_names():
        if 'Ableton Push' in name and 'User' in name:
            return name
        elif 'Ableton Push' in name:
            return name
    return None

def pad_note(row, col):
    return 36 + (row * 8) + col

def main():
    print("=" * 60)
    print("  PUSH 1 COLOR EXPLORER")
    print("=" * 60)
    print()

    push_out = find_push()
    if not push_out:
        print("ERROR: Push not found!")
        print("\nAvailable MIDI outputs:")
        for name in mido.get_output_names():
            print(f"  - {name}")
        sys.exit(1)

    print(f"Found: {push_out}")
    print()

    with mido.open_output(push_out) as port:
        # Wake up Push
        msg = mido.Message('sysex', data=SYSEX_HEADER + USER_MODE)
        port.send(msg)
        time.sleep(0.1)

        # Clear all pads first
        for note in range(36, 100):
            port.send(mido.Message('note_on', note=note, velocity=0))

        print("Mode 1: Display velocities 0-63 on the pad grid")
        print("        Each pad shows a different velocity value")
        print("        Row 1 (bottom): 0-7, Row 2: 8-15, ... Row 8: 56-63")
        print()
        print("Press Enter to start...")
        input()

        # Display velocities 0-63 on the 8x8 grid
        for row in range(8):
            for col in range(8):
                velocity = row * 8 + col
                note = pad_note(row, col)
                port.send(mido.Message('note_on', note=note, velocity=velocity))

        print("Velocities 0-63 displayed. Look at your Push!")
        print("Press Enter to see 64-127...")
        input()

        # Display velocities 64-127
        for row in range(8):
            for col in range(8):
                velocity = 64 + row * 8 + col
                note = pad_note(row, col)
                port.send(mido.Message('note_on', note=note, velocity=velocity))

        print("Velocities 64-127 displayed.")
        print()
        print("=" * 60)
        print("  INTERACTIVE MODE")
        print("=" * 60)
        print()
        print("Now you can type a velocity (0-127) to see that color on ALL pads.")
        print("This helps identify exactly which velocities produce which colors.")
        print("Type 'q' to quit.")
        print()

        while True:
            try:
                val = input("Velocity (0-127, or 'q'): ").strip()
                if val.lower() == 'q':
                    break

                velocity = int(val)
                if 0 <= velocity <= 127:
                    # Set all pads to this velocity
                    for note in range(36, 100):
                        port.send(mido.Message('note_on', note=note, velocity=velocity))
                    print(f"  All pads set to velocity {velocity}")
                else:
                    print("  Out of range. Use 0-127.")
            except ValueError:
                print("  Enter a number or 'q'")
            except KeyboardInterrupt:
                break

        # Cleanup
        print("\nCleaning up...")
        for note in range(36, 100):
            port.send(mido.Message('note_on', note=note, velocity=0))

    print("Done!")

if __name__ == "__main__":
    main()
