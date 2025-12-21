#!/usr/bin/env python3
"""
Button Color Test
=================
Test color values on the upper row buttons (CC 20-27) to find solid yellow.

Usage:
    python3 src/experiments/button_color_test.py

Controls:
    Enter / n / .  = Next value
    p / ,          = Previous value
    0-9            = Jump to value (type number, press Enter)
    q              = Quit

Watch the buttons and note which value gives SOLID yellow (not blinking).
"""
import mido
import time
import sys
import select

SYSEX_HEADER = [0x47, 0x7F, 0x15]
USER_MODE = [0x62, 0x00, 0x01, 0x01]
UPPER_BUTTONS = [20, 21, 22, 23, 24, 25, 26, 27]
LOWER_BUTTONS = [102, 103, 104, 105, 106, 107, 108, 109]

def find_push():
    for name in mido.get_output_names():
        if 'Push' in name and 'User' in name:
            return name
    return None

def set_buttons(port, value):
    """Set all 16 buttons to the given value."""
    for cc in UPPER_BUTTONS + LOWER_BUTTONS:
        port.send(mido.Message('control_change', control=cc, value=value))

def clear_buttons(port):
    """Turn off all 16 buttons."""
    set_buttons(port, 0)

def main():
    push_out = find_push()
    if not push_out:
        print("Push not found!")
        print("\nAvailable outputs:")
        for name in mido.get_output_names():
            print(f"  {name}")
        return

    print(f"Found: {push_out}")
    print("\n" + "=" * 50)
    print("  BUTTON COLOR TEST - Manual Mode")
    print("=" * 50)
    print("\nControls:")
    print("  Enter / n / .  = Next value")
    print("  p / ,          = Previous value")
    print("  [number]       = Jump to specific value (0-127)")
    print("  q              = Quit")
    print("\nBoth rows will light up for comparison.")
    print("Upper row = CC 20-27, Lower row = CC 102-109")
    print("\nPress Enter to start...")
    input()

    with mido.open_output(push_out) as port:
        # Wake up Push
        port.send(mido.Message('sysex', data=SYSEX_HEADER + USER_MODE))
        time.sleep(0.2)

        current_value = 0
        running = True

        # Show initial value
        set_buttons(port, current_value)
        print(f"\n>>> Value: {current_value:3d}  (0x{current_value:02X})")

        while running:
            try:
                cmd = input("    Command (Enter=next, p=prev, #=jump, q=quit): ").strip().lower()

                if cmd == 'q':
                    running = False
                elif cmd == '' or cmd == 'n' or cmd == '.':
                    # Next
                    current_value = min(127, current_value + 1)
                elif cmd == 'p' or cmd == ',':
                    # Previous
                    current_value = max(0, current_value - 1)
                elif cmd.isdigit() or (cmd.startswith('-') and cmd[1:].isdigit()):
                    # Jump to value
                    try:
                        new_val = int(cmd)
                        if 0 <= new_val <= 127:
                            current_value = new_val
                        else:
                            print("    (Value must be 0-127)")
                            continue
                    except ValueError:
                        print("    (Invalid number)")
                        continue
                else:
                    print("    (Unknown command)")
                    continue

                # Update buttons
                set_buttons(port, current_value)
                print(f"\n>>> Value: {current_value:3d}  (0x{current_value:02X})")

            except KeyboardInterrupt:
                print("\n\nStopped by user.")
                running = False
            except EOFError:
                running = False

        # Clear all
        clear_buttons(port)

    print("\nDone!")

if __name__ == '__main__':
    main()
