# Step Sequencer Not Working - Debugging Guide

## Quick Diagnosis

The step sequencer code IS still there and looks correct. The issue is likely one of:

1. **Session mode stuck ON** - Blocks pad routing to step sequencer
2. **Wrong pad mode** - Not in DRUM mode when you think you are
3. **Seqtrak not responding** - SysEx sent but hardware doesn't respond

## How Step Sequencer Should Work

1. **Switch to a drum track** (1-7):
   - Press octave down repeatedly
   - Display shows: KICK, SNARE, CLAP, HAT 1, HAT 2, PERC 1, or PERC 2
   - You should see console message: `Pad Mode: drum`

2. **Tap pads in top 4 rows** (rows 4-7):
   - Each tap toggles a step ON/OFF
   - Sends SysEx: `F0 43 10 7F 1C 0C 70 XX XX ...`
   - Step should light up on the pad grid

3. **Play on Seqtrak**:
   - Press PLAY on hardware
   - Enabled steps should trigger drums

## Common Issues (Post-Session Mode)

### Issue 1: Session Mode Blocking Pads

**Symptom:** Pads don't trigger step sequencer

**Cause:** Session mode check happens BEFORE pad routing:
```python
# In _handle_note_on() around line 2434:
if self.session_mode:
    if velocity > 0:
        row = (note - 36) // 8
        col = (note - 36) % 8
        self._handle_session_pad(row, col)
    return  # <--- Exits early, never reaches drum handler!
```

**Fix:** Make sure session mode is OFF
- Session button should be **DIM** (not lit)
- If lit, press Session button to exit
- Should see: "Exiting Session mode"

### Issue 2: Mode Switching Exits Session

**Code:** `_set_mode()` auto-exits session when switching modes (line ~1517):
```python
def _set_mode(self, mode):
    # Exit session mode when switching to another mode
    if self.session_mode:
        self._exit_session_mode()
```

**Problem:** If you switch modes (Track/Device/Mixer), session exits

**Good:** This SHOULD work correctly - session exits automatically

**But:** What if exit doesn't complete properly?

### Issue 3: Pad Mode Not Updating

**Symptom:** You're on a drum track but pads still play notes (melodic mode)

**Cause:** `_update_pad_mode()` wasn't called or failed

**Fix:** Force a pad mode update:
```bash
# In the app console:
# Press octave up then octave down
# This triggers _update_pad_mode()
```

## Diagnostic Tools

### 1. Test SysEx Format
```bash
cd src
python3 test_step_sequencer.py
```

This verifies the SysEx being sent is correct.

### 2. Run Verbose App
```bash
cd src
python3 run_seqtrak_verbose.py
```

Then:
- Switch to a drum track (KICK, SNARE, etc.)
- Tap a pad in the top 4 rows
- Look for: `→ SysEx: F0 43 10 7F 1C 0C 70 ...`

If you see the SysEx, the code is working!
If you DON'T see it, something's blocking the handler.

### 3. Add Debug Print

Edit `src/open_push/seqtrak/app.py` line ~2442:

**Find:**
```python
# Route based on pad mode
if self.current_pad_mode == PadMode.DRUM:
    self._handle_drum_pad(note, velocity)
```

**Change to:**
```python
# Route based on pad mode
print(f"DEBUG: session_mode={self.session_mode}, pad_mode={self.current_pad_mode}")  # ADD THIS
if self.current_pad_mode == PadMode.DRUM:
    print(f"DEBUG: Calling _handle_drum_pad({note}, {velocity})")  # ADD THIS
    self._handle_drum_pad(note, velocity)
```

Now tap pads and see:
- If you see the debug prints: pad routing works!
- If NOT: session_mode is True OR pad_mode is wrong

## Git History

**Last working commit:** `8532e2d` (Drum step sequencer with verified SysEx protocol)

**Changes since then:**
- `c7e6457`: Mixer mode UX redesign (might affect mode switching)
- `5319a56`: Device mode, note repeat, sample recording (added complexity)
- **Session mode was added** - Early return in pad handler!

**To compare:**
```bash
git diff 8532e2d HEAD -- src/open_push/seqtrak/app.py
```

Look for changes to:
- `_handle_note_on()`
- `_handle_drum_pad()`
- `session_mode` checks

## Quick Workaround

If session mode is the culprit, you can temporarily disable it:

Edit `src/open_push/seqtrak/app.py` around line 2434:

**Find:**
```python
# Session mode: handle variation selection
if self.session_mode:
    if velocity > 0:
        row = (note - 36) // 8
        col = (note - 36) % 8
        self._handle_session_pad(row, col)
    return
```

**Comment it out:**
```python
# Session mode: handle variation selection
# TEMPORARILY DISABLED FOR TESTING
# if self.session_mode:
#     if velocity > 0:
#         row = (note - 36) // 8
#         col = (note - 36) % 8
#         self._handle_session_pad(row, col)
#     return
```

If step sequencer works after this, session mode is the issue.

## Expected Behavior

When working correctly:

1. **Enter drum mode:**
   ```
   Pad Mode: drum
   ```

2. **Tap pad in row 4-7:**
   ```
   → SysEx: F0 43 10 7F 1C 0C 70 00 00 00 3C 64 00 78 F7
     Step 1 for KICK: ON
   ```

3. **Press PLAY on Seqtrak:**
   - Kick should play on step 1

## Still Broken?

If none of the above helps, provide:

1. Output from `python3 run_seqtrak_verbose.py` when tapping pads
2. Console output showing:
   - What mode you're in
   - What happens when you tap a pad
   - Whether you see "session_mode" or "pad_mode" messages
3. Whether the workaround (commenting out session check) fixes it

This will pinpoint exactly where the routing is breaking.
