#!/usr/bin/env python3
"""
Systematic test to find the correct sampler delete command.

We know:
- ADD uses: 74 73 00 [step] [tick] 00 [note] [vel] 00 00 [dur]
- DELETE must use command 74, but with different sub-command than 73
- Can't use 73+20=93 (>127, invalid MIDI)

Testing:
- 74 53 00 (73 - 20 = 53) - negative offset pattern
- 74 63 00 (73 - 10 = 63)
- 74 43 00 (73 - 30 = 43)
- 74 70 00 (matching drum command)
- 74 72 00 (matching sampler single-note command)
"""

import mido
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from open_push.seqtrak.protocol import SeqtrakProtocol, find_seqtrak_port


def test_delete_commands():
    """Test multiple possible delete command formats."""

    port_name = find_seqtrak_port()
    if not port_name:
        print("❌ Seqtrak not found!")
        return False

    print(f"✓ Found Seqtrak: {port_name}")
    port = mido.open_output(port_name)
    protocol = SeqtrakProtocol(port)

    print("\n" + "="*60)
    print("SYSTEMATIC SAMPLER DELETE TEST")
    print("="*60)

    # Test parameters
    step_index = 0
    sample_note = 0x3C  # C4

    # Possible delete sub-commands to try
    delete_tests = [
        (0x53, "74 53 00", "0x73 - 0x20 (negative offset)"),
        (0x63, "74 63 00", "0x73 - 0x10"),
        (0x43, "74 43 00", "0x73 - 0x30"),
        (0x70, "74 70 00", "drum command value"),
        (0x72, "74 72 00", "sampler command value"),
        (0x50, "74 50 00", "0x30 + 0x20 (sampler offset)"),
        (0x00, "74 00 00", "zero sub-command"),
    ]

    for sub_cmd, cmd_str, description in delete_tests:
        print(f"\n{'='*60}")
        print(f"Test: {cmd_str} - {description}")
        print(f"{'='*60}")

        # ADD step first
        print(f"\n1. ADD step 0 (note {sample_note:02X})")
        addr = [0x74, 0x73, 0x00]
        data = [0x00, 0x00, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]
        protocol.send_parameter(addr, data)
        time.sleep(0.3)
        print("   ✓ Step added")

        # Try DELETE with this sub-command
        print(f"\n2. DELETE using command: {cmd_str}")
        print(f"   Testing: F0 43 10 7F 1C 0C 74 {sub_cmd:02X} 00 00 00 F7")

        addr = [0x74, sub_cmd, 0x00]
        data = [0x00, 0x00]  # Minimal: just step position

        try:
            protocol.send_parameter(addr, data)
            time.sleep(0.3)
            print("   ✓ DELETE command sent")
            print("\n   -> Press PLAY on Seqtrak")
            print("   -> Does step 1 still play?")

            response = input("\n   Did it DELETE? (y/n/skip): ").lower().strip()
            if response == 'y':
                print(f"\n🎉 SUCCESS! Command {cmd_str} works for DELETE!")
                print(f"   Pattern: {description}")
                port.close()
                return True
            elif response == 'skip':
                print("   Skipping to next test...")
                continue
            else:
                print("   Delete didn't work, trying next...")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            continue

    print("\n" + "="*60)
    print("All tests completed - no working delete command found")
    print("="*60)
    print("\nPossible reasons:")
    print("1. Delete needs full data (not minimal)")
    print("2. Delete uses a different field to mark deletion")
    print("3. Velocity=0 might indicate delete")
    print("4. We need to test with the note field included")

    port.close()
    return False


if __name__ == "__main__":
    print("="*60)
    print(" SAMPLER DELETE - SYSTEMATIC SEARCH")
    print("="*60)
    print()
    print("This will test multiple sub-command values to find")
    print("the correct DELETE format for sampler steps.")
    print()
    print("Make sure:")
    print("- Seqtrak is on SAMPLER track (track 11)")
    print("- You can hear when steps play")
    print()
    input("Press Enter to start testing...")

    test_delete_commands()

    print("\n✅ Test complete!")
