#!/usr/bin/env python3
"""
Test sampler step delete fix.

Before fix:
  Delete sent: 74 73 00 [ticks] [note] [vel] [gate] [prob]  (WRONG - synth command!)
  Result: Step not deleted

After fix:
  Delete sent: 72 50 00 [tick_hi] [tick_lo]  (CORRECT - minimal data like drums)
  Result: Step should be deleted
"""

import mido
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from open_push.seqtrak.protocol import SeqtrakProtocol, find_seqtrak_port


def test_sampler_step_delete():
    """Test sampler step add/delete."""

    port_name = find_seqtrak_port()
    if not port_name:
        print("❌ Seqtrak not found!")
        return False

    print(f"✓ Found Seqtrak: {port_name}")
    port = mido.open_output(port_name)
    protocol = SeqtrakProtocol(port)

    print("\n" + "="*60)
    print("TEST: Sampler Step Delete Fix")
    print("="*60)

    # Add step 0
    print("\n1. ADD step 0 on sampler")
    print("   SysEx: F0 43 10 7F 1C 0C 72 30 00 00 00 00 3C 64 00 00 78 F7")
    print("          Command: 72 30 00 (sampler add)")
    print("          Ticks: 00 00 (step 0 = 0 ticks)")
    print("          Data: 00 3C 64 00 00 78")

    addr = [0x72, 0x30, 0x00]
    data = [0x00, 0x00, 0x00, 0x3C, 0x64, 0x00, 0x00, 0x78]
    protocol.send_parameter(addr, data)
    time.sleep(0.2)
    print("   ✓ Sent")

    # Delete step 0 (NEW FORMAT)
    print("\n2. DELETE step 0 on sampler (NEW FORMAT)")
    print("   SysEx: F0 43 10 7F 1C 0C 72 50 00 00 00 F7")
    print("          Command: 72 50 00 (0x30 + 0x20 offset)")
    print("          Ticks: 00 00 (step 0)")
    print("          NO extra data (minimal like drums)")

    addr = [0x72, 0x50, 0x00]
    data = [0x00, 0x00]  # Just ticks
    protocol.send_parameter(addr, data)
    time.sleep(0.2)
    print("   ✓ Sent")

    print("\n3. Verify on Seqtrak:")
    print("   - Switch to SAMPLER track")
    print("   - Press PLAY")
    print("   - Step 1 should NOT play (it was deleted)")
    print("   - If it DOES play: Delete didn't work")

    print("\n" + "="*60)
    print("COMPARISON:")
    print("="*60)
    print("OLD (WRONG) delete format:")
    print("  F0 43 10 7F 1C 0C 74 73 00 00 00 00 3C 64 00 00 78 F7")
    print("  └─ Command 74 (synth/DX, not sampler!)")
    print("  └─ Full data payload (same as add)")
    print()
    print("NEW (CORRECT) delete format:")
    print("  F0 43 10 7F 1C 0C 72 50 00 00 00 F7")
    print("  └─ Command 72 (sampler)")
    print("  └─ Offset +0x20 (like drum delete)")
    print("  └─ Minimal data (just ticks)")

    port.close()
    return True


if __name__ == "__main__":
    print("="*60)
    print(" SAMPLER STEP DELETE FIX TEST")
    print("="*60)
    print()
    print("This tests the fixed delete command for sampler steps.")
    print("The bug was using command 74 (synth) instead of 72 (sampler).")
    print()

    test_sampler_step_delete()

    print("\n✅ Test complete!")
    print("\nTo test in the app:")
    print("1. Run: python3 -m open_push.seqtrak.app")
    print("2. Switch to SAMPLER track (track 11)")
    print("3. Tap a pad in the top 4 rows to add a step")
    print("4. Tap it again to DELETE the step")
    print("5. Press PLAY on Seqtrak - step should not play")
