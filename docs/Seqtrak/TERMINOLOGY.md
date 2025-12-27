# Seqtrak Terminology Reference

**Purpose**: Critical definitions for working with Yamaha Seqtrak integration. Read this first when starting work on Seqtrak-related code.

**Last Updated**: 2025-12-26

---

## Track Structure

The Seqtrak has **11 tracks** divided into track groups:

| Track Type | Tracks | MIDI Channels | Description |
|------------|--------|---------------|-------------|
| **Drum** | KICK, SNARE, CLAP, HAT1, HAT2, PERC1, PERC2 | 1-7 | Percussion tracks |
| **Melodic** | SYNTH 1, SYNTH 2, DX, SAMPLER | 8-11 | Tonal/melodic tracks |

### Track Groups Breakdown

**Drum Tracks (Channels 1-7):**
- KICK (Ch 1)
- SNARE (Ch 2)
- CLAP (Ch 3)
- HAT 1 (Ch 4)
- HAT 2 (Ch 5)
- PERC 1 (Ch 6)
- PERC 2 (Ch 7)

**Melodic Tracks (Channels 8-11):**
- SYNTH 1 (Ch 8)
- SYNTH 2 (Ch 9)
- DX (Ch 10)
- SAMPLER (Ch 11)

---

## Pattern vs Bar

### Pattern
**Used for**: Drum tracks (channels 1-7)

**What it is**: The step sequence length for drum tracks. Each drum track can have independent pattern lengths.

**Control**:
- Global: `30 40 7A` - "Pattern Master Step" (1-128 steps)
- Per-track: `30 5[track] 16-21` - Individual pattern lengths for variations 1-6

**User Interface**: Pattern length can be adjusted for drum tracks in the Seqtrak bridge.

### Bar
**Used for**: Melodic tracks (channels 8-11: SYNTH 1, SYNTH 2, DX, SAMPLER)

**What it is**: The step sequence length for melodic tracks. Each melodic track can have independent bar lengths.

**Control**:
- Same SysEx addresses as patterns: `30 5[track] 16-21`
- Separate from drum pattern lengths

**KNOWN BUG**: Bar length adjustment for melodic tracks is NOT working in the current Seqtrak bridge implementation. Can adjust pattern length for drums, but cannot adjust bar length for melodic tracks.

---

## Variations

**Count**: 6 variations per track (numbered 1-6, data values 00-05)

**What they are**: Different sequence variations for each track. Each track can store up to 6 different patterns/bars with different note sequences.

**SysEx Control**:
- Per-track variation select: `30 5[track] 0F` (data 00-05)
- Global variation indicator: `01 10 2A` (read-only feedback)

**Independent**: Each track can be on a different variation simultaneously.

**Example**: KICK could be playing variation 3 while SYNTH 1 is playing variation 1.

---

## Step Sequencer

**What it is**: Grid-based note programming for tracks

**Two Types**:
1. **Drum Step Sequencer** (Command `70`)
   - Used for drum tracks (channels 1-7)
   - Note-based triggering
   - Simple add/delete commands

2. **Melodic Step Sequencer** (Commands `72` for sampler, `74` for synth/DX)
   - Used for melodic tracks (channels 8-11)
   - Tick-based positioning (more precise timing)
   - Different format from drum sequencer

**Max Steps**: 1-128 steps per pattern/bar

---

## Session View

**What it is**: Pattern/variation launcher grid

**Layout**: 6 variations × 11 tracks (technically 12 with DRUM bus, but 11 actual tracks)

**Function**: Press pads to launch different variations on different tracks

**KNOWN BUG**: Session view sometimes doesn't launch clips at all (intermittent).

---

## Mode Types (Synth/DX Tracks Only)

**Applies to**: SYNTH 1, SYNTH 2, DX tracks (channels 8-10)

**Options**:
- **MONO** - Monophonic (one note at a time)
- **POLY** - Polyphonic (multiple notes simultaneously)
- **CHORD** - Chord mode (plays chords)

**SysEx**: CC 26 on channels 8-10 (values 0-2)

**Not available on**: Drum tracks or Sampler

---

## Arpeggiator

**Applies to**: SYNTH 1, SYNTH 2, DX tracks only (channels 8-10)

**Presets**: 16 arpeggio types (0=OFF, 1-16=different patterns)

**Controls**:
- Type: CC 27 (0-16)
- Gate: CC 28 (0-127)
- Speed: CC 29 (0-9)

**Not available on**: Drum tracks or Sampler

---

## Preset/Sound Selection

**Method**: Standard MIDI Bank Select + Program Change
```
Bank Select MSB (CC 0): [bank_msb]
Bank Select LSB (CC 32): [bank_lsb]
Program Change: [program]
```

**Sound Categories**: Each track type has 15 sound categories (see `sysex-protocol-reference.md` lines 37-60)

**Total Sounds**: 2,032+ presets across all tracks

---

## Common Terminology Mistakes

### ❌ WRONG: "4 variations"
### ✅ CORRECT: **6 variations** (data 00-05)

### ❌ WRONG: "Pattern length applies to all tracks"
### ✅ CORRECT: **Pattern length for drums, Bar length for melodic tracks** (different concepts)

### ❌ WRONG: "Track indices 0-10"
### ✅ CORRECT: **MIDI channels 1-11** (or track indices 0-10 in code depending on context)

### ❌ WRONG: "Melodic tracks can use arpeggiator"
### ✅ CORRECT: **Only SYNTH 1, SYNTH 2, and DX** have arpeggiator (not SAMPLER)

---

## Related Documentation

For detailed SysEx addresses and protocol:
- **[sysex-protocol-reference.md](sysex-protocol-reference.md)** - Complete protocol documentation

For feature gaps and implementation status:
- **[IMPLEMENTATION-GAP-ANALYSIS.md](IMPLEMENTATION-GAP-ANALYSIS.md)** - What's missing vs iOS app

For current bugs and enhancement requests:
- **[BUGS_AND_ENHANCEMENTS.md](BUGS_AND_ENHANCEMENTS.md)** - Active issue tracking

---

## Quick Reference Table

| Concept | Drum Tracks (1-7) | Melodic Tracks (8-11) |
|---------|-------------------|----------------------|
| Sequence length | Pattern | Bar |
| Variations | 6 (00-05) | 6 (00-05) |
| Step sequencer cmd | `70` | `72` (sampler), `74` (synth/DX) |
| Mono/Poly mode | N/A | Available (SYNTH/DX only) |
| Arpeggiator | N/A | Available (SYNTH/DX only, NOT sampler) |
| Sound categories | 15 per track | 15 per track |
| Max steps | 1-128 | 1-128 |

---

## Notes

- This terminology reflects both official Yamaha documentation AND practical usage patterns
- "Pattern" vs "Bar" distinction may not be explicit in Yamaha docs but is important for understanding track behavior differences
- Always verify track type before assuming available features (arp, mono/poly, etc.)
- When in doubt, consult `sysex-protocol-reference.md` for exact SysEx addresses and data formats
