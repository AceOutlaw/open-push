# Seqtrak Push Implementation Gap Analysis

## Overview
This document compares features visible in the Yamaha Seqtrak iOS app (from screenshots) against the current OpenPush Seqtrak bridge implementation to identify what still needs to be implemented.

**Source**: 22 screenshots from `/reference files/Yamaha/App Screenshots/`
**Implementation**: `/src/open_push/seqtrak/app.py` (2,978 lines)
**Generated**: December 25, 2025

---

## Current Implementation Status

### Fully Implemented
| Feature | Location | Notes |
|---------|----------|-------|
| Transport Control | Play/Stop/Record buttons | SysEx-based, bi-directional |
| Track Selection | 11 tracks (7 drum, 2 synth, DX, sampler) | Full support |
| Mixer Mode | Volume per track + DRUM bus | 8 encoders, 2 pages |
| Mute/Solo | Per-track toggle | With visual feedback |
| Device Mode - Basic Params | Vol, Pan, Pitch, Attack, Decay, Filter, Reso | CC-based |
| Device Mode - EQ/Send | Reverb, Delay, EQ Hi, EQ Lo | Page 2 |
| Device Mode - Synth | Portamento On/Off, Time | Page 3 |
| Device Mode - Arp | Type, Gate, Speed | Partial (16 types) |
| Device Mode - DX/FM | Algorithm, Mod Amt/Freq/Feedback | Page 4 |
| Isomorphic Keyboard | Fourths layout with scale highlighting | Full |
| Scale Mode | 40+ scales, root selection | Full UI |
| In-Key / Chromatic | Toggle mode | Working |
| Step Sequencer | Drums + Sampler, 4 pages × 32 steps | Visual grid |
| Session View | Pattern launcher grid | 6 patterns × 12 tracks |
| Note Repeat | 8 subdivisions (1/4 to 1/32t) | With accent |
| Preset Browsing | Prev/Next via encoder | 2,032+ presets |
| Tempo Sync | Read tempo from Seqtrak | Display only |
| Sample Recording | Shift+Record | Basic trigger |

### Partially Implemented
| Feature | Current State | Gap |
|---------|--------------|-----|
| Arpeggiator | Type/Gate/Speed | Missing: MODE, OCTAVE range |
| Sampler Pads | 7 pads with presets | Missing: per-pad editing |
| Bar Length | State tracked | Missing: UI to change |

---

## Missing Features (From App Screenshots)

### Priority 1: High Impact Sound Design

#### 1.1 LFO Section (All Tracks)
**Screenshot**: 9.59.15 AM, 9.59.28 AM
- **DEPTH** (0-127) - Modulation amount
- **DELAY** - LFO onset delay
- **TEMPO SYNC** - On/Off toggle
- **SPEED** - LFO rate (Hz or synced)
- **DESTINATION** - Target parameter:
  - FX: Overdrive, Amp Type, LPF Cutoff Freq, Output Level, Dry/Wet Balance
  - FILTER: LPF/HPF Cutoff Frequency, Resonance
  - SOUND: Level
- **SHAPE** - 12 waveform types:
  - Triangle, Tri+, Tri-
  - Saw Up, Saw Down
  - Square, Square+, Square-
  - Trapezoid, S/H (Sample & Hold)
  - Asymmetric variants

**Implementation needs**: New Device Mode page for LFO with encoder mappings for each parameter. Shape/Destination require list selection UI.

#### 1.2 Effect Category/Type Selection
**Screenshot**: 9.59.39 AM, 9.59.53 AM
- **8 Effect Categories**:
  1. Filter
  2. Reverb
  3. Delay
  4. Compressor
  5. Distortion
  6. Modulation
  7. Ducker
  8. Other
- **Type selection** within each category (e.g., Amp Simulator, Bit Crusher, Lo-Fi)
- **3 Assignable Sliders** - Map to effect parameters

**Implementation needs**: Effect browser UI using upper/lower LCD buttons for category, encoder for type. Parameter page shows assignable slider targets.

#### 1.3 Choke Groups (Drums)
**Screenshot**: 9.58.40 AM
- **CHOKE** - On/Off toggle per drum track
- Links drum sounds (e.g., open/closed hi-hat)

**Implementation needs**: Add to Device Mode drum page. Simple on/off CC.

### Priority 2: Sampler Deep Editing

#### 2.1 Sample Start/End/Loop Points
**Screenshot**: 10.02.44 AM
- **START** - Sample start point (visual waveform)
- **END** - Sample end point
- **LOOP** - Loop start point
- **LOOP OFF/ON** toggle
- **SAMPLE LENGTH** display

**Implementation needs**: Dedicated sampler edit page. Requires SysEx for sample point parameters.

#### 2.2 Pitch Envelope (Sampler)
**Screenshot**: 10.02.44 AM
- **PITCH** graph with attack/decay curves
- **ATTACK TIME** (0-127)
- **ATTACK LEVEL** (-128 to +127)
- **DECAY TIME** (0-127)
- **DECAY LEVEL** (-128 to +127)

**Implementation needs**: New device page for sampler with 4 envelope parameters.

#### 2.3 Sample Playback Mode
**Screenshot**: 10.02.44 AM
- **TYPE**: GATE vs TRIGGER
  - GATE = plays while held
  - TRIGGER = plays full sample

**Implementation needs**: Toggle parameter in sampler device page.

### Priority 3: Synth Features

#### 3.1 Chord Mode
**Screenshot**: 10.01.13 AM
- **TYPE**: MONO / POLY / CHORD toggle
- **CHORD** dropdown with chord types

**Implementation needs**: Current MODE param exists but only shows MONO/POLY. Add CHORD type selection.

#### 3.2 Sampling Frequency Control
**Screenshot**: 10.01.13 AM
- **SAMPLING FREQUENCY CONTROL**: 44.1kHz display
- Lo-Fi sample rate reduction effect

**Implementation needs**: May be part of effect routing, not direct control.

### Priority 4: Performance Features

#### 4.1 Song Mode (Pattern Chaining)
**Screenshot**: 10.03.16 AM
- **Pattern Chain**: 1 → 2 → 3 → + (add more)
- **MODE**: NORMAL / SONG / SCENE
  - NORMAL = single pattern loops
  - SONG = plays chain sequentially
  - SCENE = variation switching

**Implementation needs**: New mode accessible from Session view. Chain editing UI on pads.

#### 4.2 Send Mixer
**Screenshot**: 10.03.02 AM (referenced in PERFORM menu)
- **11 track faders** for SEND levels
- **SEND1 / SEND2** toggle (Reverb/Delay sends)

**Implementation needs**: New mixer page or sub-mode. Per-track send level encoders.

### Priority 5: Settings/Global

#### 5.1 Advanced Settings
**Screenshot**: 10.03.49 AM
- **Live Rec Quantization**: 1/16 default
- **Advanced Sound Design**: On/Off (unlocks more params)
- **Noise Gate** (Mic/Line In): On/Off
- **Count-in MIDI Recording**: On/Off
- **Launch Quantize**: 16 (bars/beats)
- **Master FX (Mic/Line In)**: Thru/On
- **Input Velocity**: 100
- **Playback Mode After Project Switch**: Off

**Implementation needs**: Global settings page, likely via Shift+Device or dedicated button.

---

## Sound Browser Enhancement

#### Search and Category Filtering
**Screenshot**: 10.00.57 AM
- **Search bar** with text input
- **Category grid** (15 categories per track type)
- **Sound list** with scrolling
- **Favorites** (heart icon)

**Current state**: Encoder scrolls presets sequentially.
**Gap**: No category filtering, no search, no favorites.

**Implementation needs**: Major UI work. Could use:
- Upper buttons = category selection
- Lower buttons = page through sounds in category
- Encoder = fine scroll within filtered list

---

## Implementation Priority Recommendation

### Phase 1: Quick Wins (CC-based, minimal SysEx)
1. **Choke Group toggle** - Single CC addition
2. **Arp Mode/Octave** - Extend existing arp page
3. **Sample Playback Type** - GATE/TRIGGER toggle

### Phase 2: New Device Pages
4. **LFO Section** - New page with 6-7 parameters
5. **Pitch Envelope (Sampler)** - 4 new parameters
6. **Send Levels** - Per-track SEND1/SEND2

### Phase 3: Browser/Selection UI
7. **Effect Category/Type Browser** - List selection pattern
8. **Sound Category Browser** - Filter by category

### Phase 4: Advanced Features
9. **Song Mode** - Pattern chain editor
10. **Global Settings** - Quantization, count-in, etc.

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/open_push/seqtrak/app.py` | Add device pages, LFO params, send mixer |
| `src/open_push/seqtrak/protocol.py` | Add SysEx addresses for new parameters |
| `docs/Seqtrak/sysex-protocol-reference.md` | Document new addresses discovered |

---

## SysEx Research Needed

Before implementing, need to capture/document SysEx for:
- LFO Destination address
- LFO Shape address
- Effect Type selection address
- Sample Start/End/Loop point addresses
- Pitch Envelope addresses
- Song mode addresses

Method: Use MIDI monitor while adjusting params in iOS app.

---

## Summary

**Total features in Seqtrak app**: ~45+ distinct parameters/modes
**Currently implemented**: ~30 (65%)
**Gap**: ~15 features (35%)

The largest gaps are:
1. **LFO modulation** - Core sound design feature
2. **Effect browser** - Category/type selection
3. **Sampler editing** - Start/end/loop/envelope
4. **Song mode** - Pattern chaining

These represent the main areas where Push users cannot access Seqtrak functionality that iOS app users can.
