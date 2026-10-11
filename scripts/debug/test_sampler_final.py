#!/usr/bin/env python3
"""
Final test based on MIDI captures:
ADD:    72 30 00 [step] [tick] 00 [note] 64 00 00 78
DELETE: 74 73 00 [step] [tick] 00 [note] 64 00 00 78
"""

import mido
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from open_push.seqtrak.protocol import SeqtrakProtocol, find_seqtrak_port


def test_correct_format():
    """Test the correct format from MIDI captures."""

    port_name = find_seqtrak_port()
    if not port_name:
        print("❌ Seqtrak not found!")
        return False

    print(f"✓ Found Seqtrak: {port_name}")
    port = mido.open_output(port_name)
    protocol = SeqtrakProtocol(port)

    print("\n" + "="*60)
    print("SAMPLER STEP TEST - Verified Format")
    print("="*60)

    # Sample 1 (pad_index=0), Step 1 (step_index=0)
    pad_index = 0
    step_index = 0
    sample_note = 0x3C + pad_index  # C4 for sample 1
    tick = 0x00  # On-grid timing

    print(f"\nTesting Sample {pad_index + 1}, Step {step_index + 1}")
    print(f"Note: 0x{sample_note:02X} ({sample_note})")

    # Select sampler element (like _sync_sampler_element does)
    print("\n1. Select sampler element (pad)")
    print(f"   SysEx: F0 43 10 7F 1C 0C 01 10 28 {pad_index:02X} F7")
    protocol.select_sampler_element(pad_index)
    time.sleep(0.2)

    # ADD step
    print("\n2. ADD step")
    print(f"   SysEx: F0 43 10 7F 1C 0C 72 30 00 {step_index:02X} {tick:02X} 00 {sample_note:02X} 64 00 00 78 F7")
    addr = [0x72, 0x30, 0x00]
    data = [step_index, tick, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]
    protocol.send_parameter(addr, data)
    time.sleep(0.5)
    print("   ✓ Step added")
    print("\n   -> Press PLAY on Seqtrak - step 1 should play")
    input("   Press Enter when ready to test DELETE...")

    # DELETE step
    print("\n3. DELETE step")
    print(f"   SysEx: F0 43 10 7F 1C 0C 74 73 00 {step_index:02X} {tick:02X} 00 {sample_note:02X} 64 00 00 78 F7")
    addr = [0x74, 0x73, 0x00]  # Different command!
    data = [step_index, tick, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]  # Same data!
    protocol.send_parameter(addr, data)
    time.sleep(0.5)
    print("   ✓ Delete command sent")
    print("\n   -> Press PLAY on Seqtrak - step 1 should NOT play")

    print("\n" + "="*60)
    response = input("Did the DELETE work? (y/n): ").lower().strip()
    if response == 'y':
        print("\n🎉 SUCCESS! The sampler delete is working!")
        print("\nPattern confirmed:")
        print("  ADD:    72 30 00 [data]")
        print("  DELETE: 74 73 00 [data] (same data, different command)")
    else:
        print("\n❌ Still not working. Possible issues:")
        print("1. Are you on SAMPLER track (track 11)?")
        print("2. Is the sample loaded/active?")
        print("3. Check Seqtrak's response messages")

    port.close()
    return True


if __name__ == "__main__":
    print("="*60)
    print(" SAMPLER STEP DELETE - Verified Format Test")
    print("="*60)
    print()
    print("Based on MIDI capture analysis:")
    print("  ADD uses command:    72 30 00")
    print("  DELETE uses command: 74 73 00")
    print("  (Same data, different command addresses!)")
    print()
    input("Press Enter to start...")

    test_correct_format()
