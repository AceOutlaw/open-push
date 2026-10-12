> ⚠️ **Superseded (2026-10-12):** the sampler/melodic remove described here never worked. See `docs/Seqtrak/STEP-SEQUENCER.md` — verified remove is `74 [g] [index] 00`, readback `75 [g] [index]`.

# Sampler Step Delete Fix

## The Bug

**Symptom:** Sampler steps can be added but NOT deleted
- Tap pad → step added ✅
- Tap again → local state updates (pad dims) but Seqtrak still plays the step ❌

## Root Cause

The delete SysEx was using the **wrong command**:

**WRONG (before fix):**
```
F0 43 10 7F 1C 0C 74 73 00 [tick_hi] [tick_lo] 00 3C 64 00 00 78 F7
                  └─┬─┘
                    Command 74 = SYNTH/DX (not sampler!)
```

**CORRECT (after fix):**
```
F0 43 10 7F 1C 0C 72 50 00 [tick_hi] [tick_lo] F7
                  └─┬─┘
                    Command 72 = Sampler
                       └─ 0x50 = 0x30 + 0x20 offset (like drums)
                  Minimal data (just ticks, like drums)
```

## Why It Was Wrong

The original code (line 2606) said:
```python
# Delete step: F0 43 10 7F 1C 0C 74 73 00 [tick_hi] [tick_lo] 00 3C 64 00 00 78 F7
```

This was captured from MIDI logs, but:
1. **Command 0x74** is for SYNTH/DX tracks, NOT sampler
2. **Full data payload** was sent (same as add), but delete should be minimal
3. The SysEx protocol docs don't document delete commands - this was a guess

## The Fix

Following the **drum delete pattern** (which works):

| Track Type | Add Command | Delete Command | Delete Data |
|------------|-------------|----------------|-------------|
| Drum | `70 [track] 00` | `70 [0x20+track] 00` | `[step]` only |
| Sampler | `72 30 00` | `72 50 00` | `[tick_hi] [tick_lo]` only |

**Pattern:**
- Add 0x20 offset to middle byte
- Send minimal data (just the step identifier)

## Code Changes

**File:** `src/open_push/seqtrak/app.py` lines 2637-2645

**Before:**
```python
if new_state:
    addr = [0x72, 0x30, 0x00]
    data = [tick_hi, tick_lo, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]
else:
    # WRONG - uses synth command!
    addr = [0x74, 0x73, 0x00]
    data = [tick_hi, tick_lo, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]
```

**After:**
```python
if new_state:
    addr = [0x72, 0x30, 0x00]
    data = [tick_hi, tick_lo, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]
else:
    # CORRECT - follows drum pattern
    addr = [0x72, 0x50, 0x00]  # 0x30 + 0x20 offset
    data = [tick_hi, tick_lo]  # Minimal data
```

## Testing

**Quick test:**
```bash
cd src
python3 test_sampler_delete.py
```

This sends:
1. Add step 0: `F0 43 10 7F 1C 0C 72 30 00 00 00 00 3C 64 00 00 78 F7`
2. Delete step 0: `F0 43 10 7F 1C 0C 72 50 00 00 00 F7`

**In the app:**
1. Run: `python3 -m open_push.seqtrak.app`
2. Switch to SAMPLER track (track 11 - octave up repeatedly)
3. Tap a pad in top 4 rows → step added (pad lights up)
4. Tap again → step deleted (pad dims, AND Seqtrak stops playing it)
5. Press PLAY on Seqtrak to verify

## Does Drum Delete Work?

**Yes!** The drum delete was already correct:
- Command: `70 [0x20 + track] 00`
- Data: `[step_index]` only
- This was captured from working MIDI logs

The sampler delete was GUESSED incorrectly because:
- No MIDI logs showed sampler delete
- It assumed synth command (74) would work
- It sent full data payload instead of minimal

## Documentation Update

Updated `sysex-protocol-reference.md` to mark this as discovered:

**Before:**
```
### SAMPLER Track (Channel 11) - Command `72`
(Only ADD step shown)
```

**Should add:**
```
### SAMPLER Delete - Command `72 50`
Format: F0 43 10 7F 1C 0C 72 50 00 [tick_hi] [tick_lo] F7

Follows drum pattern:
- Middle byte = 0x50 (0x30 + 0x20 offset)
- Data = minimal (just tick position)
```

## Related Issues

If **drum delete** also doesn't work:
- Check the drum delete code (line 2583-2585)
- Format: `70 [0x20 + track_idx] 00 [step_index]`
- Drums send step_index directly (0-127)
- Sampler sends ticks (step * 120, as 14-bit hi/lo)

The pattern is consistent: **delete = add command + 0x20 offset + minimal data**
