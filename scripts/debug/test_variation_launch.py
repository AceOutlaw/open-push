#!/usr/bin/env python3
"""
Test Seqtrak variation launching - diagnostic tool.

This script helps debug why variation launching might not be working:
1. Tests the SysEx format
2. Adds verbose MIDI output logging
3. Tests with delays to avoid timing issues
"""

import mido
import time
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from open_push.seqtrak.protocol import SeqtrakProtocol, find_seqtrak_port


def test_variation_launch():
    """Test variation launching with verbose output."""

    # Find Seqtrak
    port_name = find_seqtrak_port()
    if not port_name:
        print("❌ Seqtrak not found!")
        print("\nAvailable MIDI ports:")
        for name in mido.get_output_names():
            print(f"  - {name}")
        return False

    print(f"✓ Found Seqtrak: {port_name}")

    # Open port
    try:
        port = mido.open_output(port_name)
        print(f"✓ Connected to {port_name}")
    except Exception as e:
        print(f"❌ Failed to open port: {e}")
        return False

    # Create protocol
    protocol = SeqtrakProtocol(port)

    # Test 1: Simple variation change on KICK track
    print("\n" + "="*60)
    print("TEST 1: Select Variation 2 on KICK track")
    print("="*60)
    print("  Track: 1 (KICK)")
    print("  Variation: 2")
    print("  Expected SysEx: F0 43 10 7F 1C 0C 30 50 0F 01 F7")
    print("                     │  │  │  │  │  │  │  │  │  └─ Variation 2 (0-indexed)")
    print("                     │  │  │  │  │  │  │  │  └─ Offset 0x0F (variation)")
    print("                     │  │  │  │  │  │  │  └─ Track 1 = 0x50")
    print("                     │  │  │  │  │  │  └─ Address high = 0x30")
    print("                     │  │  │  │  │  └─ Model ID (Seqtrak)")
    print("                     │  │  │  │  └─ Sub-group")
    print("                     │  │  │  └─ Category")
    print("                     │  │  └─ Device 0")
    print("                     │  └─ Yamaha")
    print("                     └─ SysEx start")

    # Send it
    protocol.select_track_variation(1, 2)
    time.sleep(0.1)
    print("✓ Sent")

    # Test 2: Launch a pattern (multiple tracks)
    print("\n" + "="*60)
    print("TEST 2: Launch variation pattern across tracks")
    print("="*60)
    print("  Simulating session row launch:")
    print("    KICK    (track 1) -> Variation 2")
    print("    SNARE   (track 2) -> Variation 3")
    print("    CLAP    (track 3) -> Variation 1")
    print("    SYNTH 1 (track 8) -> Variation 4")

    variations = {
        1: 2,  # KICK -> Var 2
        2: 3,  # SNARE -> Var 3
        3: 1,  # CLAP -> Var 1
        8: 4,  # SYNTH1 -> Var 4
    }

    for track, var in variations.items():
        print(f"  Sending track {track} -> variation {var}...", end=" ")
        protocol.select_track_variation(track, var)
        time.sleep(0.05)  # Small delay between messages
        print("✓")

    # Test 3: Select all variations at once
    print("\n" + "="*60)
    print("TEST 3: Select Variation 5 for ALL tracks")
    print("="*60)
    print("  This sends 11 SysEx messages (one per track)")

    protocol.select_all_variations(5)
    print("✓ Sent to all 11 tracks")

    # Done
    print("\n" + "="*60)
    print("TESTS COMPLETE")
    print("="*60)
    print("\nWhat to check on Seqtrak:")
    print("  1. Did the variation indicators change?")
    print("  2. Press PLAY - do the patterns match what was selected?")
    print("  3. If nothing changed:")
    print("     - Check MIDI cable is connected")
    print("     - Try selecting a different pattern manually on Seqtrak")
    print("     - Make sure Seqtrak is not in a mode that blocks MIDI")

    port.close()
    return True


def monitor_seqtrak_midi():
    """Monitor MIDI input from Seqtrak to see feedback."""
    print("\n" + "="*60)
    print("BONUS: Monitor Seqtrak MIDI output")
    print("="*60)

    # Find input port
    input_ports = [p for p in mido.get_input_names() if 'Seqtrak' in p or 'SEQTRAK' in p]
    if not input_ports:
        print("No Seqtrak input port found - skipping monitoring")
        return

    print(f"Listening on: {input_ports[0]}")
    print("Press Ctrl+C to stop...")
    print("\nWaiting for MIDI messages from Seqtrak...")

    try:
        with mido.open_input(input_ports[0]) as inport:
            for msg in inport:
                if msg.type == 'sysex':
                    hex_str = ' '.join(f'{b:02X}' for b in msg.data)
                    print(f"SysEx: F0 {hex_str} F7")

                    # Parse if it's a variation change
                    if len(msg.data) >= 9:
                        if msg.data[0] == 0x43 and msg.data[5] == 0x0C:  # Yamaha Seqtrak
                            addr = msg.data[6:9]
                            data = msg.data[9:]
                            if addr[0] == 0x30 and addr[2] == 0x0F:  # Variation change
                                track = (addr[1] - 0x50) + 1
                                variation = data[0] + 1 if data else 0
                                print(f"  → Variation change: Track {track} -> Variation {variation}")
                else:
                    print(f"{msg}")
    except KeyboardInterrupt:
        print("\nMonitoring stopped")


if __name__ == "__main__":
    print("="*60)
    print(" SEQTRAK VARIATION LAUNCH DIAGNOSTIC")
    print("="*60)

    # Run tests
    success = test_variation_launch()

    if success:
        # Optionally monitor feedback
        try:
            response = input("\nMonitor Seqtrak MIDI output? (y/n): ").strip().lower()
            if response == 'y':
                monitor_seqtrak_midi()
        except (EOFError, KeyboardInterrupt):
            print("\nSkipping monitoring")

    print("\nDone!")
