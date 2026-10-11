#!/usr/bin/env python3
"""
Run Seqtrak bridge with verbose MIDI logging.

This wrapper adds detailed MIDI output logging to help debug issues
like variation launching not working.
"""

import mido
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

# Monkey-patch mido to add verbose logging
original_send = mido.ports.BaseOutput.send

def verbose_send(self, msg):
    """Wrapper that logs all outgoing MIDI."""
    if msg.type == 'sysex':
        hex_str = ' '.join(f'{b:02X}' for b in msg.data)
        print(f"  → SysEx: F0 {hex_str} F7")

        # Parse Seqtrak variation messages
        if len(msg.data) >= 9 and msg.data[0] == 0x43 and msg.data[5] == 0x0C:
            addr = msg.data[6:9]
            data = msg.data[9:]

            # Variation select?
            if addr[0] == 0x30 and addr[2] == 0x0F:
                track = (addr[1] - 0x50) + 1
                variation = data[0] + 1 if data else 0
                track_names = ['', 'KICK', 'SNARE', 'CLAP', 'HAT1', 'HAT2',
                              'PERC1', 'PERC2', 'SYNTH1', 'SYNTH2', 'DX', 'SAMPLER']
                track_name = track_names[track] if 1 <= track <= 11 else f"Track{track}"
                print(f"     💡 {track_name} → Variation {variation}")

    elif msg.type in ('note_on', 'note_off', 'control_change'):
        print(f"  → {msg}")

    # Call original
    return original_send(self, msg)

# Apply monkey-patch
mido.ports.BaseOutput.send = verbose_send

print("="*60)
print(" SEQTRAK BRIDGE - VERBOSE MODE")
print("="*60)
print("All outgoing MIDI will be logged to help debug issues.")
print("Look for '💡' markers to see variation changes.\n")

# Now import and run the app
from open_push.seqtrak.app import main

main()
