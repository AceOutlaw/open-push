#!/usr/bin/env python3
"""
Test 72 XX 00 command variations for sampler DELETE.

Theory: 74 73 00 is STATUS (output only), not CONTROL.
The actual DELETE command might use 72 XX 00 like ADD does.
"""

import mido
import sys
import time

# Find Seqtrak
seqtrak_ports = [p for p in mido.get_output_names() if 'SEQTRAK' in p]
if not seqtrak_ports:
    print("❌ Seqtrak not found!")
    sys.exit(1)

seqtrak_out = mido.open_output(seqtrak_ports[0])
print(f"✓ Seqtrak: {seqtrak_ports[0]}")

SYSEX_HEADER = [0x43, 0x10, 0x7F, 0x1C, 0x0C]

def send_sysex(cmd, data):
    """Send SysEx and log it."""
    sysex = SYSEX_HEADER + cmd + data
    hex_str = " ".join(f"{b:02X}" for b in sysex)
    print(f"   SEND: F0 {hex_str} F7")
    seqtrak_out.send(mido.Message('sysex', data=sysex))
    time.sleep(0.3)

print("\n" + "="*60)
print("SYSTEMATIC 72 XX 00 DELETE TEST")
print("="*60)

# First, add a step we can try to delete
print("\n1. ADD step 0 (reference)")
print("   Command: 72 30 00")
send_sysex([0x72, 0x30, 0x00], [0x00, 0x00, 0x00, 0x3C, 0x64, 0x00, 0x00, 0x78])
print("   → Verify on Seqtrak: Step 1 should be added")
input("   Press Enter to start DELETE tests...")

# Test different 72 XX 00 commands
delete_tests = [
    (0x50, "72 50 00", "0x30 + 0x20 offset (like drums)"),
    (0x40, "72 40 00", "0x30 + 0x10 offset"),
    (0x10, "72 10 00", "0x30 - 0x20 offset"),
    (0x20, "72 20 00", "0x30 - 0x10 offset"),
    (0x00, "72 00 00", "Zero sub-command"),
    (0x31, "72 31 00", "0x30 + 1"),
    (0x2F, "72 2F 00", "0x30 - 1"),
]

for sub_cmd, cmd_str, description in delete_tests:
    print(f"\n{'='*60}")
    print(f"Test: {cmd_str} - {description}")
    print(f"{'='*60}")

    # Re-add step
    print("   Re-adding step 0...")
    send_sysex([0x72, 0x30, 0x00], [0x00, 0x00, 0x00, 0x3C, 0x64, 0x00, 0x00, 0x78])

    # Try delete with this command
    print(f"   Trying DELETE with: {cmd_str}")
    send_sysex([0x72, sub_cmd, 0x00], [0x00, 0x00, 0x00, 0x3C, 0x64, 0x00, 0x00, 0x78])

    print("\n   → Press PLAY on Seqtrak")
    response = input("   Did it DELETE? (y/n): ").lower().strip()

    if response == 'y':
        print(f"\n🎉 SUCCESS! DELETE command is: {cmd_str}")
        print(f"   Pattern: {description}")
        break
    else:
        print("   ✗ Didn't work, trying next...")

print("\n" + "="*60)
print("Test complete")
print("="*60)

seqtrak_out.close()
