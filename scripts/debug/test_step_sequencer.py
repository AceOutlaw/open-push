#!/usr/bin/env python3
"""
Diagnostic tool for step sequencer issues.

Tests:
1. Step sequencer SysEx format
2. Session mode state
3. Pad routing logic
"""

import mido
import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from open_push.seqtrak.protocol import SeqtrakProtocol, find_seqtrak_port


def test_step_add_delete():
    """Test step sequencer add/delete SysEx."""

    port_name = find_seqtrak_port()
    if not port_name:
        print("❌ Seqtrak not found!")
        return False

    print(f"✓ Found Seqtrak: {port_name}")
    port = mido.open_output(port_name)
    protocol = SeqtrakProtocol(port)

    print("\n" + "="*60)
    print("TEST: Step Sequencer Add/Delete")
    print("="*60)

    # Test adding a step on KICK (track 1)
    print("\n1. Add step 0 on KICK track")
    print("   SysEx: F0 43 10 7F 1C 0C 70 00 00 00 3C 64 00 78 F7")
    print("          │  │  │  │  │  │  │  │  │  │  │  │  │  └─ Probability (0x78 = 120)")
    print("          │  │  │  │  │  │  │  │  │  │  │  │  └─ Gate (0x00)")
    print("          │  │  │  │  │  │  │  │  │  │  └─ Velocity (0x64 = 100)")
    print("          │  │  │  │  │  │  │  │  │  └─ Note (0x3C = C4)")
    print("          │  │  │  │  │  │  │  │  └─ Step index (0)")
    print("          │  │  │  │  │  │  │  └─ Variation (00)")
    print("          │  │  │  │  │  │  └─ Track (00 = KICK)")
    print("          │  │  │  │  │  └─ Command (0x70 = drum step)")
    print("          └──────────────┴─ Yamaha Seqtrak SysEx header")

    # Add step
    addr = [0x70, 0x00, 0x00]  # drum step, KICK, variation 0
    data = [0x00, 0x3C, 0x64, 0x00, 0x78]  # step 0, note C4, vel 100, gate 0, prob 120
    protocol.send_parameter(addr, data)
    time.sleep(0.1)
    print("   ✓ Sent ADD step")

    # Wait a moment
    time.sleep(1)

    # Delete step
    print("\n2. Delete step 0 on KICK track")
    print("   SysEx: F0 43 10 7F 1C 0C 70 20 00 00 F7")
    print("          │  │  │  │  │  │  │  │  │  └─ Step index (0)")
    print("          │  │  │  │  │  │  │  │  └─ Variation (00)")
    print("          │  │  │  │  │  │  └─ Track (0x20 = delete offset)")
    print("          │  │  │  │  │  └─ Command (0x70 = drum step)")
    print("          └──────────────┴─ Yamaha Seqtrak SysEx header")

    addr = [0x70, 0x20, 0x00]  # delete command, KICK
    data = [0x00]  # step 0
    protocol.send_parameter(addr, data)
    time.sleep(0.1)
    print("   ✓ Sent DELETE step")

    print("\n3. Check on Seqtrak:")
    print("   - Press PLAY and listen for KICK on step 1")
    print("   - It should NOT play (step was deleted)")
    print("   - If it DOES play, SysEx delete isn't working")

    port.close()
    return True


def check_app_state():
    """Provide instructions for checking app state."""
    print("\n" + "="*60)
    print("DIAGNOSTIC: Check App State")
    print("="*60)

    print("""
To diagnose step sequencer issues in the running app:

1. Start the verbose app:
   python3 run_seqtrak_verbose.py

2. Switch to a DRUM track (tracks 1-7):
   - Press octave down until you reach track 1-7
   - Display should show track name (KICK, SNARE, etc.)
   - You should see: "Pad Mode: drum"

3. Check if you're in session mode:
   - Session button (CC 51) should be DIM (not lit)
   - If it's LIT, you're in session mode
   - Press Session button to exit

4. Try the step sequencer:
   - Tap a pad in the TOP 4 rows (rows 4-7)
   - In verbose mode, you should see:
     → SysEx: F0 43 10 7F 1C 0C 70 XX XX XX XX XX XX XX F7
     (step add/delete message)

5. Common issues:

   a) If you see NO SysEx when tapping pads:
      - Check: Are you in DRUM mode? (see step 2)
      - Check: Is session mode ON? (see step 3)
      - Check: Are you tapping rows 4-7 (top 4 rows)?

   b) If session mode is stuck ON:
      - Press Session button to toggle it off
      - Session LED should dim
      - Try step sequencer again

   c) If you're in MELODIC mode on a drum track:
      - This is a bug - pad mode didn't update
      - Press octave up then down to force update
      - Check if mode changed to "drum"

   d) If SysEx IS being sent but steps don't work:
      - The Seqtrak might not be responding
      - Try pressing PLAY on Seqtrak to hear if steps trigger
      - Check firmware version (might be incompatible)
""")


def main():
    print("="*60)
    print(" STEP SEQUENCER DIAGNOSTIC")
    print("="*60)

    # Test SysEx
    test_step_add_delete()

    # Provide app diagnostic instructions
    check_app_state()

    print("\n" + "="*60)
    print("If step sequencer still doesn't work:")
    print("="*60)
    print("""
1. Check git history for the last working version:
   git log --oneline | grep "step sequencer"

2. The commit that added step sequencer was: 8532e2d
   "feat: Drum step sequencer with verified SysEx protocol"

3. To see what changed since then:
   git diff 8532e2d HEAD -- src/open_push/seqtrak/app.py

4. Potential culprits (added after step sequencer):
   - Session mode (might be blocking pads)
   - Mode switching logic (might not enter DRUM mode)
   - Note repeat mode (might interfere)

5. Quick fix: Add debug print to _handle_drum_pad():
   Edit src/open_push/seqtrak/app.py line ~2467:

   def _handle_drum_pad(self, note, velocity):
       print(f"DEBUG: _handle_drum_pad called! note={note} vel={velocity}")  # ADD THIS
       \"\"\"Handle pad press in drum mode.\"\"\"
       ...

   If you DON'T see this print when tapping pads:
   - Pads aren't reaching _handle_drum_pad
   - session_mode might be True
   - current_pad_mode might not be PadMode.DRUM
""")


if __name__ == "__main__":
    main()
