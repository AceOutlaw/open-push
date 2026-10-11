#!/usr/bin/env python3
"""
Test if sampler DELETE uses the same command (74 73 00) but with
specific fields set to zero (velocity, duration, etc).
"""

import mido
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))
from open_push.seqtrak.protocol import SeqtrakProtocol, find_seqtrak_port


def test_zero_field_formats():
    """Test DELETE with same command but zero fields."""

    port_name = find_seqtrak_port()
    if not port_name:
        print("❌ Seqtrak not found!")
        return False

    print(f"✓ Found Seqtrak: {port_name}")
    port = mido.open_output(port_name)
    protocol = SeqtrakProtocol(port)

    print("\n" + "="*60)
    print("TEST: DELETE with Zero Fields")
    print("="*60)

    step_index = 0
    sample_note = 0x3C

    tests = [
        ("Velocity = 0", [0x00, 0x00, 0x00, sample_note, 0x00, 0x00, 0x00, 0x78]),
        ("Duration = 0", [0x00, 0x00, 0x00, sample_note, 0x64, 0x00, 0x00, 0x00]),
        ("Vel & Dur = 0", [0x00, 0x00, 0x00, sample_note, 0x00, 0x00, 0x00, 0x00]),
        ("All zeros except note", [0x00, 0x00, 0x00, sample_note, 0x00, 0x00, 0x00, 0x00]),
        ("Note = 0", [0x00, 0x00, 0x00, 0x00, 0x64, 0x00, 0x00, 0x78]),
    ]

    for description, data in tests:
        print(f"\n{'='*60}")
        print(f"Test: {description}")
        print(f"{'='*60}")

        # ADD step first
        print(f"\n1. ADD step 0")
        addr = [0x74, 0x73, 0x00]
        add_data = [0x00, 0x00, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]
        protocol.send_parameter(addr, add_data)
        time.sleep(0.3)
        print("   ✓ Step added")

        # Try DELETE with zero field
        print(f"\n2. DELETE with: {description}")
        data_hex = " ".join(f"{b:02X}" for b in data)
        print(f"   Data: {data_hex}")

        addr = [0x74, 0x73, 0x00]  # Same command as ADD
        protocol.send_parameter(addr, data)
        time.sleep(0.3)
        print("   ✓ Sent")

        print("\n   -> Press PLAY on Seqtrak")
        response = input("   Did it DELETE? (y/n/skip): ").lower().strip()

        if response == 'y':
            print(f"\n🎉 SUCCESS! DELETE uses: {description}")
            print(f"   Data: {data_hex}")
            port.close()
            return True
        elif response == 'skip':
            continue
        else:
            print("   Didn't work, trying next...")

    print("\n❌ No zero-field pattern worked")
    port.close()
    return False


if __name__ == "__main__":
    print("="*60)
    print(" SAMPLER DELETE - Zero Field Test")
    print("="*60)
    print()
    print("Testing if DELETE uses same command (74 73 00)")
    print("but with specific fields set to zero...")
    print()
    input("Press Enter to start...")

    test_zero_field_formats()
