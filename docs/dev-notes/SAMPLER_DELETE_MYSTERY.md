> ⚠️ **Superseded (2026-10-12):** the sampler/melodic remove described here never worked. See `docs/Seqtrak/STEP-SEQUENCER.md` — verified remove is `74 [g] [index] 00`, readback `75 [g] [index]`.

# Yamaha Seqtrak Sampler Step Delete Mystery

## The Problem

We're reverse-engineering the Yamaha Seqtrak's MIDI SysEx protocol to control its step sequencer from an Ableton Push controller. **ADD steps works perfectly, but DELETE steps doesn't work**, even though we're using the same methodology.

## Background: What Works (Other Track Types)

### Drum Tracks - FULLY WORKING ✓

**Pattern discovered:**
- ADD step: `F0 43 10 7F 1C 0C 70 [track] 00 [step] [note] [vel] [gate] [prob] F7`
- DELETE step: `F0 43 10 7F 1C 0C 70 [0x20+track] 00 [step] F7`

**How we figured it out:**
1. Captured MIDI from Seqtrak hardware when adding/deleting drum steps
2. Replayed those exact SysEx messages from Push → Seqtrak
3. It worked! Steps add and delete correctly

**Key pattern:** DELETE uses same command (`70`) but adds 0x20 offset to middle byte, with minimal data

### Sampler Track - PARTIALLY WORKING (ADD ✓, DELETE ✗)

**What works:**
- ADD step: `F0 43 10 7F 1C 0C 72 30 00 [step] [tick] 00 [note] [vel] 00 00 [dur] F7`

**Verification:**
1. Captured this format from Seqtrak hardware
2. Send from Push → Seqtrak
3. **Steps appear on Seqtrak display ✓**
4. **Steps play when pressing PLAY ✓**
5. **Functions exactly like hardware-added steps ✓**

**What doesn't work:**
- DELETE step: `F0 43 10 7F 1C 0C 74 73 00 [step] [tick] 00 [note] [vel] 00 00 [dur] F7`

**What happens:**
1. Captured this format from Seqtrak hardware when deleting steps
2. Send from Push → Seqtrak
3. **Seqtrak echoes it back (receives the message) ✓**
4. **But step is NOT deleted ✗**
5. **Step still plays when pressing PLAY ✗**

## Detailed Test Log

### Successful ADD Test
```
→ SEND: F0 43 10 7F 1C 0C 72 30 00 00 00 00 3C 64 00 00 78 F7
(No response from Seqtrak)
Result: Step 1 appears on Seqtrak, plays correctly ✓
```

### Failed DELETE Test
```
→ SEND: F0 43 10 7F 1C 0C 74 73 00 00 00 00 3C 64 00 00 78 F7
← RECV: F0 43 10 7F 1C 0C 01 10 2D 06 06 F7  (state messages)
← RECV: F0 43 10 7F 1C 0C 01 10 39 0A 0A F7
← RECV: ... (multiple similar messages)
← RECV: F0 43 10 7F 1C 0C 74 73 00 00 00 00 3C 64 00 00 78 F7  (echo!)
← RECV: F0 43 10 7F 1C 0C 01 10 2D 01 01 F7  (state messages)
← RECV: F0 43 10 7F 1C 0C 01 10 39 01 01 F7
← RECV: ... (multiple similar messages)
Result: Step still present, still plays ✗
```

## The Mystery: Why This Asymmetry?

### ADD Command Path:
1. Capture from hardware → `72 30 00`
2. Send to hardware → `72 30 00`
3. **Works! ✓**

### DELETE Command Path:
1. Capture from hardware → `74 73 00`
2. Send to hardware → `74 73 00`
3. **Doesn't work! ✗**

## Key Observations

1. **Seqtrak DOES receive the DELETE command** - proven by echo response
2. **No error/reject message** - it just doesn't act on it
3. **Different command byte**: ADD uses `72`, DELETE capture shows `74`
4. **State messages appear**: Multiple `01 10 XX` messages before/after, values change
5. **Same methodology works for drums** - so the approach is sound

## What We've Tried (All Failed)

1. **Exact replay of captured DELETE**: `74 73 00 [full data]` - Echoed but ignored
2. **Offset pattern like drums**: `72 50 00` (0x30+0x20) - No response
3. **Various `74 XX 00` sub-commands**: `74 53 00`, `74 63 00`, etc. - No effect
4. **Zero field variations**: velocity=0, duration=0, note=0 - No effect
5. **Minimal data**: Just step position without full data - No effect
6. **Different timing/delays**: No change

## Hardware Details

- **Device**: Yamaha Seqtrak
- **Track**: Sampler (Track 11)
- **Sample Pad**: Pad 1 (note 0x3C = C4)
- **Steps**: 16-step pattern (step 0 = first step)

## Message Format Breakdown

### Working ADD Format
```
F0 43 10 7F 1C 0C 72 30 00 [step] [tick] 00 [note] [vel] 00 00 [dur] F7
│  └──────┬──────┘  │  │   │   └──┬──┘ │   └─┬─┘ └─┬─┘ │  │  └─┬─┘
│      Yamaha       │  │   │      │    │     │     │   │  │    │
│      Seqtrak      │  │   │   Address  │  Data (8 bytes)      │
│      Header       │  │   │            │                       │
│                   │  │   │         Step/Tick/Note/Vel/etc    │
│                Command: 72 30 00                              │
└─ SysEx Start                                    SysEx End ────┘

Example (Step 1, Sample 1):
72 30 00 00 00 00 3C 64 00 00 78
│  │  │  │  │  │  │  │  │  │  └─ Duration: 0x78 (120)
│  │  │  │  │  │  │  │  └──┴─ Padding: 00 00
│  │  │  │  │  │  │  └─ Velocity: 0x64 (100)
│  │  │  │  │  │  └─ Note: 0x3C (C4, Middle C)
│  │  │  │  │  └─ Padding: 00
│  │  │  │  └─ Tick: 00 (on-grid)
│  │  │  └─ Step: 00 (step 1)
│  │  └─ Unknown: 00
│  └─ Sub-command: 30 (ADD)
└─ Command: 72 (SAMPLER)
```

### Captured DELETE Format (doesn't work when sent)
```
F0 43 10 7F 1C 0C 74 73 00 [step] [tick] 00 [note] [vel] 00 00 [dur] F7
                  └─┬─┘
              Command: 74 (SYNTH/DX, not 72!)

Example (Step 1, Sample 1):
74 73 00 00 00 00 3C 64 00 00 78
│  │  │  └─────────┬─────────┘
│  │  │        Same data as ADD
│  │  └─ Unknown: 00
│  └─ Sub-command: 73
└─ Command: 74 (SYNTH/DX track command, not SAMPLER!)
```

## The Core Question

**Why does command `74 73 00` appear in MIDI captures from the hardware when deleting steps, but sending that same command back doesn't delete steps?**

### Theories:

1. **MIDI OUT ≠ MIDI IN Theory**
   - `74 73 00` might be a status/echo message (MIDI OUT only)
   - Actual control command might be different (MIDI IN)
   - Analogy: Piano sends Note On when key pressed, but sending Note On doesn't press piano keys

2. **Sampler Uses Different Pattern Theory**
   - Drums use `70 [track+0x20]` offset for delete
   - Sampler might use `72 [0x30+offset]` but we haven't found the right offset
   - Or uses `72 30 00` with different data field (velocity=0?)

3. **Command 74 Is Read-Only Theory**
   - Command `74` might be output-only (status reporting)
   - All control commands might need to use `72 XX 00` family
   - We just haven't found the right `XX` value

4. **No MIDI DELETE Exists Theory**
   - Maybe step deletion can ONLY be done via hardware buttons
   - MIDI can only add steps, not remove them
   - (But this seems unlikely given other tracks support it)

## What Would Help

1. **Official Yamaha MIDI implementation chart** for Seqtrak step sequencer
2. **Capture from official Yamaha controller/software** (if any exists) showing DELETE commands
3. **Fresh perspective** on the data - what are we missing?
4. **Pattern recognition** - is there something in the `01 10 XX` state messages that matters?

## Files for Reference

- Working drum implementation: `src/open_push/seqtrak/app.py` (lines 2546-2595)
- Sampler implementation: `src/open_push/seqtrak/app.py` (lines 2597-2655)
- Test script: `src/minimal_sampler_test.py`
- Full protocol docs: `docs/Seqtrak/sysex-protocol-reference.md`

## Summary

We successfully reverse-engineered sampler step ADD using MIDI capture/replay. The exact same methodology fails for DELETE - we capture `74 73 00`, send it back, Seqtrak receives it (proven by echo), but doesn't act on it. What are we missing?
