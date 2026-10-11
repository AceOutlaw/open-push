#!/usr/bin/env python3
"""
Test sampler step add/delete using command 0x74 (SYNTH/DX format).

Based on MIDI capture showing:
  Delete step 0: F0 43 10 7F 1C 0C 74 73 00 00 00 00 3C 64 00 00 78 F7

This uses command 0x74 (SYNTH/DX), not 0x72 (SAMPLER)!
"""

import mido
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from open_push.seqtrak.protocol import SeqtrakProtocol, find_seqtrak_port


def test_cmd74_format():
    """Test sampler steps using 0x74 command (from MIDI capture)."""

    port_name = find_seqtrak_port()
    if not port_name:
        print("❌ Seqtrak not found!")
        return False

    print(f"✓ Found Seqtrak: {port_name}")
    port = mido.open_output(port_name)
    protocol = SeqtrakProtocol(port)

    print("\n" + "="*60)
    print("TEST: Sampler with Command 0x74 (SYNTH/DX format)")
    print("="*60)

    # Step 0 (first step), Sample 1
    step_index = 0
    sample_note = 0x3C  # C4 = 60

    # ADD step using 0x74 73 00 format (from MIDI capture)
    print("\n1. ADD step 0, sample 1 (note C4)")
    print("   Using command: 74 73 00")
    print("   SysEx: F0 43 10 7F 1C 0C 74 73 00 00 00 00 3C 64 00 00 78 F7")

    addr = [0x74, 0x73, 0x00]
    data = [0x00, 0x00, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]
    protocol.send_parameter(addr, data)
    time.sleep(0.5)
    print("   ✓ Sent ADD command")
    print("   -> Switch to SAMPLER track on Seqtrak")
    print("   -> Press PLAY - step 1 should play")
    input("\n   Press Enter when ready to test DELETE...")

    # DELETE with full data (matching the captured message exactly)
    print("\n2. DELETE step 0 using FULL data (match capture)")
    print("   Command: 74 73 00 (NO offset!)")
    print("   SysEx: F0 43 10 7F 1C 0C 74 73 00 00 00 00 3C 64 00 00 78 F7")
    print("   (This matches the captured delete message)")

    addr = [0x74, 0x73, 0x00]  # NO offset
    data = [0x00, 0x00, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]  # Full data
    protocol.send_parameter(addr, data)
    time.sleep(0.5)
    print("   ✓ Sent DELETE command (full data, no offset)")
    print("   -> Press PLAY on Seqtrak")
    print("   -> Step 1 should NOT play")

    print("\n" + "="*60)
    print("DELETE TEST COMPLETE")
    print("="*60)
    print("Tested: 74 73 00 [00 00 00 3C 64 00 00 78]")
    print("(Matches MIDI capture - same command as ADD, full data)")
    print()
    print("Did the step get deleted? (Press PLAY to verify)")
    print()

    port.close()
    return True


if __name__ == "__main__":
    print("="*60)
    print(" SAMPLER STEP SEQUENCER - Command 0x74 Test")
    print("="*60)
    print()
    print("Based on MIDI capture showing:")
    print("  Delete: F0 43 10 7F 1C 0C 74 73 00 00 00 00 3C 64 00 00 78 F7")
    print()
    print("This uses command 0x74 (SYNTH/DX), NOT 0x72 (SAMPLER)!")
    print()

    test_cmd74_format()

    print("\n✅ Test complete!")
    print("\nPlease report which format successfully deleted the step.")
