#!/usr/bin/env python3
"""
Test sampler step delete with note field included.

Hypothesis: The DELETE command might need the sample note to identify
which sample's step to delete (since one sampler track can have multiple
samples playing different notes).
"""

import mido
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from open_push.seqtrak.protocol import SeqtrakProtocol, find_seqtrak_port


def test_formats():
    """Test different delete formats."""

    port_name = find_seqtrak_port()
    if not port_name:
        print("❌ Seqtrak not found!")
        return False

    print(f"✓ Found Seqtrak: {port_name}")
    port = mido.open_output(port_name)
    protocol = SeqtrakProtocol(port)

    print("\n" + "="*60)
    print("TEST: Sampler Delete With Note")
    print("="*60)

    # Test parameters
    step_index = 0
    ticks = step_index * 120  # 0 for step 0
    tick_hi = (ticks >> 7) & 0x7F  # 0x00
    tick_lo = ticks & 0x7F         # 0x00
    sample_note = 0x3C  # C4

    # Add step first
    print("\n1. ADD step 0")
    print(f"   Note: 0x{sample_note:02X} ({sample_note})")
    addr = [0x72, 0x30, 0x00]
    data = [tick_hi, tick_lo, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]
    protocol.send_parameter(addr, data)
    time.sleep(0.5)

    # Test 1: Delete with just ticks (current implementation)
    print("\n2. DELETE Format 1: Just ticks (current)")
    print("   SysEx: F0 43 10 7F 1C 0C 72 50 00 00 00 F7")
    addr = [0x72, 0x50, 0x00]
    data = [tick_hi, tick_lo]
    protocol.send_parameter(addr, data)
    time.sleep(0.5)
    print("   ✓ Sent")
    print("   -> Press PLAY on Seqtrak to test")
    print("   -> If step still plays, try next format...")
    input("   Press Enter to continue...")

    # Add again
    print("\n3. RE-ADD step 0 for next test")
    addr = [0x72, 0x30, 0x00]
    data = [tick_hi, tick_lo, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]
    protocol.send_parameter(addr, data)
    time.sleep(0.5)

    # Test 2: Delete with ticks + note
    print("\n4. DELETE Format 2: Ticks + note")
    print("   SysEx: F0 43 10 7F 1C 0C 72 50 00 00 00 3C F7")
    addr = [0x72, 0x50, 0x00]
    data = [tick_hi, tick_lo, sample_note]  # Add note!
    protocol.send_parameter(addr, data)
    time.sleep(0.5)
    print("   ✓ Sent")
    print("   -> Press PLAY on Seqtrak to test")
    print("   -> Does this format work?")
    input("   Press Enter to continue...")

    # Add again
    print("\n5. RE-ADD step 0 for next test")
    addr = [0x72, 0x30, 0x00]
    data = [tick_hi, tick_lo, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]
    protocol.send_parameter(addr, data)
    time.sleep(0.5)

    # Test 3: Delete with full data (like ADD but with 0x50 address)
    print("\n6. DELETE Format 3: Full data (like ADD)")
    print("   SysEx: F0 43 10 7F 1C 0C 72 50 00 00 00 00 3C 64 00 00 78 F7")
    addr = [0x72, 0x50, 0x00]
    data = [tick_hi, tick_lo, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]  # Full data!
    protocol.send_parameter(addr, data)
    time.sleep(0.5)
    print("   ✓ Sent")
    print("   -> Press PLAY on Seqtrak to test")
    print("   -> Does this format work?")

    print("\n" + "="*60)
    print("Which format worked?")
    print("="*60)

    port.close()
    return True


if __name__ == "__main__":
    print("="*60)
    print(" SAMPLER DELETE FORMAT TESTING")
    print("="*60)
    print()
    print("Testing 3 different delete formats to find the correct one:")
    print("1. Just ticks (current implementation)")
    print("2. Ticks + note")
    print("3. Full data (same as ADD)")
    print()

    test_formats()

    print("\n✅ Test complete!")
