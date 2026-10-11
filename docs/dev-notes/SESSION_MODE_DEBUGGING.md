# Session Mode Variation Launching - Debugging Guide

## Summary

**Good news:** The variation launching code **is already implemented** and looks correct!

The code path is:
1. Press **Session button** (CC 51) → enters session mode
2. In session mode, press **CC 36-43 buttons** → launches that row
3. `_handle_session_row_launch(row)` → calls `protocol.select_track_variation(track, pattern)` for each track
4. Protocol sends correct SysEx: `F0 43 10 7F 1C 0C 30 5[track-1] 0F [variation-1] F7`

## Implementation Details

### Session Mode Entry
- **File:** `src/open_push/seqtrak/app.py`
- **Line:** 1309 - `_enter_session_mode()`
- **Trigger:** Press Session button (CC 51)

### Row Launching
- **File:** `src/open_push/seqtrak/app.py`
- **Line:** 1486 - `_handle_session_row_launch(row)`
- **Trigger:** In session mode, press CC 36-43 buttons
- **What it does:** Sends variation select to each track based on `session_patterns` grid

### SysEx Protocol
- **File:** `src/open_push/seqtrak/protocol.py`
- **Line:** 456 - `select_track_variation(track, variation)`
- **Format:** `F0 43 10 7F 1C 0C 30 5[track-1] 0F [variation-1] F7`

Example for KICK (track 1) variation 2:
```
F0 43 10 7F 1C 0C 30 50 0F 01 F7
   │  │  │  │  │  │  │  │  │  └─ Variation 2 (0-indexed = 01)
   │  │  │  │  │  │  │  │  └─ Offset 0x0F (variation parameter)
   │  │  │  │  │  │  │  └─ Track byte (0x50 = KICK)
   │  │  │  │  │  │  └─ Address high (0x30)
   │  │  │  │  │  └─ Model ID (0x0C = Seqtrak)
   │  │  │  │  └─ Sub-group (0x1C)
   │  │  │  └─ Category (0x7F)
   │  │  └─ Device 0 (0x10)
   │  └─ Yamaha (0x43)
   └─ SysEx start
```

This matches the documentation in `docs/Seqtrak/sysex-protocol-reference.md` **exactly**.

## Why It Might Not Be Working

Since the code is correct, here are the most likely issues:

### 1. MIDI Port Not Connected
The SysEx is being sent, but Seqtrak isn't receiving it.
- Check: Is the MIDI cable connected?
- Check: Is the right port selected when the app starts?

### 2. Timing Issues
Seqtrak might need a small delay between messages.
- Currently: No delay between track variation messages
- Fix: Add `time.sleep(0.01)` between calls (see below)

### 3. Seqtrak State
Seqtrak might need to be in a specific state to accept variation changes.
- Try: Stop playback before launching
- Try: Make sure you're not in a special mode on Seqtrak

### 4. Missing Feedback
You can't see what's being sent, so you don't know if it's working.
- Solution: Use the verbose logging tools (see below)

## Diagnostic Tools

### Tool 1: Test Script
Run the standalone test to verify SysEx is correct:

```bash
cd /Users/aceoutlaw/CascadeProjects/open-push/src
python3 test_variation_launch.py
```

This will:
- Find your Seqtrak
- Send test variation changes
- Show exactly what SysEx is being sent
- Give you instructions on what to check

### Tool 2: Verbose Bridge
Run the app with MIDI logging enabled:

```bash
cd /Users/aceoutlaw/CascadeProjects/open-push/src
python3 run_seqtrak_verbose.py
```

This will:
- Run the normal Seqtrak bridge
- Log every MIDI message sent
- Highlight variation changes with 💡 markers
- Let you see exactly what happens when you press buttons

## Quick Fix: Add Timing Delay

If you find that the SysEx is being sent but Seqtrak isn't responding, try adding a small delay.

**Edit:** `src/open_push/seqtrak/app.py` line ~1505

**Change from:**
```python
for col in range(8):
    mixer_pos = base_pos + col
    if mixer_pos < len(MIXER_TRACK_ORDER):
        track = MIXER_TRACK_ORDER[mixer_pos]
        if track is not None:
            pattern = self.session_patterns[mixer_pos][row]
            self.protocol.select_track_variation(track, pattern)
            launched_tracks.append(f"{MIXER_DISPLAY_NAMES[mixer_pos]}:{pattern}")
```

**Change to:**
```python
for col in range(8):
    mixer_pos = base_pos + col
    if mixer_pos < len(MIXER_TRACK_ORDER):
        track = MIXER_TRACK_ORDER[mixer_pos]
        if track is not None:
            pattern = self.session_patterns[mixer_pos][row]
            self.protocol.select_track_variation(track, pattern)
            launched_tracks.append(f"{MIXER_DISPLAY_NAMES[mixer_pos]}:{pattern}")
            time.sleep(0.01)  # 10ms delay between messages
```

## Testing Session Mode

1. **Start the bridge** (verbose mode recommended):
   ```bash
   python3 run_seqtrak_verbose.py
   ```

2. **Enter session mode:**
   - Press **Session** button on Push (should light up)
   - Display should show session grid

3. **Select a pattern:**
   - Press a pad (selects a slot)
   - Turn the encoder above it to change the variation number (1-6)
   - You should see the number update on the LCD

4. **Launch the row:**
   - Press one of the **CC 36-43 buttons** (below the pads)
   - In verbose mode, you should see:
     ```
     → SysEx: F0 43 10 7F 1C 0C 30 50 0F 01 F7
        💡 KICK → Variation 2
     → SysEx: F0 43 10 7F 1C 0C 30 51 0F 02 F7
        💡 SNARE → Variation 3
     ...
     ```

5. **Verify on Seqtrak:**
   - Press **Play** on Seqtrak
   - The variations should match what you launched
   - If they don't, the SysEx isn't being received

## Still Not Working?

If you've tried everything above and it's still not working, please provide:

1. Output from `python3 test_variation_launch.py`
2. Output from `python3 run_seqtrak_verbose.py` when you launch a row
3. What you see on the Seqtrak hardware when you press buttons
4. Seqtrak firmware version (if known)

This will help diagnose if it's:
- A hardware/firmware issue
- A protocol incompatibility
- A Seqtrak mode/state issue

## Reference

- **SysEx Protocol:** `docs/Seqtrak/sysex-protocol-reference.md` (lines 869-887)
- **Session Mode Code:** `src/open_push/seqtrak/app.py` (lines 1309-1508)
- **Protocol Code:** `src/open_push/seqtrak/protocol.py` (lines 456-472)
