#!/usr/bin/env python3
"""
Test if DELETE uses 72 30 00 (same as ADD) but with different data fields.
Theory: Maybe velocity=0, duration=0, or note=0 indicates delete?
"""

import mido
import sys
import time

seqtrak_ports = [p for p in mido.get_output_names() if 'SEQTRAK' in p]
if not seqtrak_ports:
    print("❌ Seqtrak not found!")
    sys.exit(1)

seqtrak_out = mido.open_output(seqtrak_ports[0])
print(f"✓ Seqtrak: {seqtrak_ports[0]}")

SYSEX_HEADER = [0x43, 0x10, 0x7F, 0x1C, 0x0C]

def send_sysex(cmd, data, label):
    """Send SysEx and log it."""
    sysex = SYSEX_HEADER + cmd + data
    hex_str = " ".join(f"{b:02X}" for b in data)
    print(f"   {label}: {hex_str}")
    seqtrak_out.send(mido.Message('sysex', data=sysex))
    time.sleep(0.3)

print("\n" + "="*60)
print("TEST: 72 30 00 with Data Field Variations")
print("="*60)

# Normal ADD for reference
add_data = [0x00, 0x00, 0x00, 0x3C, 0x64, 0x00, 0x00, 0x78]

# DELETE variations (same command 72 30 00, different data)
delete_tests = [
    ("Velocity = 0",     [0x00, 0x00, 0x00, 0x3C, 0x00, 0x00, 0x00, 0x78]),
    ("Duration = 0",     [0x00, 0x00, 0x00, 0x3C, 0x64, 0x00, 0x00, 0x00]),
    ("Vel & Dur = 0",    [0x00, 0x00, 0x00, 0x3C, 0x00, 0x00, 0x00, 0x00]),
    ("Note = 0",         [0x00, 0x00, 0x00, 0x00, 0x64, 0x00, 0x00, 0x78]),
    ("All zeros",        [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]),
    ("Step = 0xFF",      [0xFF, 0x00, 0x00, 0x3C, 0x64, 0x00, 0x00, 0x78]),
    ("Tick = 0xFF",      [0x00, 0xFF, 0x00, 0x3C, 0x64, 0x00, 0x00, 0x78]),
]

for description, data in delete_tests:
    print(f"\n{'='*60}")
    print(f"Test: {description}")
    print(f"{'='*60}")

    # Add step
    print("\n   1. ADD step (72 30 00)")
    send_sysex([0x72, 0x30, 0x00], add_data, "ADD DATA")

    # Try delete with modified data
    print(f"\n   2. DELETE attempt (72 30 00) - {description}")
    send_sysex([0x72, 0x30, 0x00], data, "DEL DATA")

    print("\n   → Press PLAY on Seqtrak")
    response = input("   Did it DELETE? (y/n): ").lower().strip()

    if response == 'y':
        print(f"\n🎉 SUCCESS! DELETE uses 72 30 00 with: {description}")
        break
    else:
        print("   ✗ Didn't work, trying next...")

print("\n" + "="*60)
print("Test complete")
print("="*60)

seqtrak_out.close()
