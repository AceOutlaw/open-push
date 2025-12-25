# Seqtrak Data List Documentation Plan

This document outlines the plan to chronicle and document the Yamaha Seqtrak Data List PDFs into organized, usable reference documentation.

---

## Source Material Inventory

### PDF Files (11 total)
Located in: `reference files/Yamaha/Seqtrak Data List/`

| PDF File | Size | Content Type | Priority |
|----------|------|--------------|----------|
| `SEQTRAK_data_list_Core.pdf` | 870KB | Core system overview | High |
| `SEQTRAK_data_list_Drums.pdf` | 760KB | Drum preset list | High |
| `SEQTRAK_data_list_Drums_Synths.pdf` | 803KB | Drum synth presets | High |
| `SEQTRAK_data_list_Drums_MIDI_Data_Format.pdf` | 797KB | MIDI format spec | **Done** |
| `SEQTRAK_data_list_Drums_MIDI_Data_Table.pdf` | 1.4MB | MIDI data tables | High |
| `SEQTRAK_data_list_DX_sampler.pdf` | 728KB | DX/Sampler presets | High |
| `SEQTRAK_data_list_Effects.pdf` | 1.3MB | Effect parameters | Medium |
| `SEQTRAK_data_list_Effect_Preset_List.pdf` | 708KB | Effect preset names | Medium |
| `SEQTRAK_data_list_Effect_Data_Assign_Table.pdf` | 1.3MB | Effect CC assignments | Medium |
| `SEQTRAK_data_list_Sound_Design_Parameter_List.pdf` | 871KB | Synth parameters | Medium |
| `SEQTRAK_data_list_wave_list.pdf` | 1MB | Waveform names | Low |

### Existing Documentation
Located in: `docs/Seqtrak/`

| File | Status | Content |
|------|--------|---------|
| `midi-data-format.md` | Complete | MIDI transmit/receive flows, CC mappings |
| `sysex-protocol-reference.md` | Complete | Reverse-engineered SysEx addresses |

### Raw Captures
Located in: `reference files/Yamaha/Seqtrak Data List/md/`

| File | Size | Content |
|------|------|---------|
| `Seqtrak SysEX Data.md` | 50KB | Live MIDI capture logs (useful for validation) |
| `SEQTRAK-data-list-old.md` | 602KB | Earlier conversion attempt (may be redundant) |

---

## Documentation Structure

### Proposed `docs/Seqtrak/` Folder Organization

```
docs/Seqtrak/
├── README.md                        # Index and quick reference
├── DOCUMENTATION-PLAN.md            # This file
├── midi-data-format.md              # [EXISTING] MIDI protocol
├── sysex-protocol-reference.md      # [EXISTING] SysEx addresses
├── presets/
│   ├── drum-presets.md              # [NEW] Tracks 1-7 preset names
│   ├── synth-presets.md             # [NEW] Tracks 8-9 preset names
│   ├── dx-presets.md                # [NEW] Track 10 preset names
│   └── sampler-presets.md           # [NEW] Track 11 sample slots
├── effects/
│   ├── effect-types.md              # [NEW] Reverb, Delay, Master FX types
│   ├── effect-parameters.md         # [NEW] Parameter ranges per effect
│   └── effect-cc-assignments.md     # [NEW] CC to parameter mapping
├── sound-design/
│   ├── synth-parameters.md          # [NEW] FM, filter, envelope params
│   └── waveforms.md                 # [NEW] Oscillator waveform list
└── tables/
    ├── bank-program-table.md        # [NEW] Bank/Program → Name mapping
    └── address-map.md               # [NEW] Complete SysEx address space
```

---

## Phase 1: Preset Data (Priority for Push Integration)

**Goal**: Create `src/open_push/seqtrak/presets.py` with name lookup tables

### 1.1 Document Drum Presets
- **Source**: `Drums.pdf`, `Drums_Synths.pdf`
- **Output**: `docs/Seqtrak/presets/drum-presets.md`
- **Deliverable**: Python dict mapping `(bank_msb, bank_lsb, program) → preset_name`

### 1.2 Document Synth Presets
- **Source**: `DX_sampler.pdf`, `Sound_Design_Parameter_List.pdf`
- **Output**: `docs/Seqtrak/presets/synth-presets.md`
- **Deliverable**: Add to presets.py SYNTH_PRESETS dict

### 1.3 Document DX Presets
- **Source**: `DX_sampler.pdf`
- **Output**: `docs/Seqtrak/presets/dx-presets.md`
- **Deliverable**: Add to presets.py DX_PRESETS dict

### 1.4 Document Sampler Slots
- **Source**: `DX_sampler.pdf`
- **Output**: `docs/Seqtrak/presets/sampler-presets.md`
- **Note**: Sampler uses user samples, names may be dynamic

---

## Phase 2: Effect Documentation

**Goal**: Complete effect reference for future encoder control

### 2.1 Effect Types and Parameters
- **Source**: `Effects.pdf`
- **Output**: `docs/Seqtrak/effects/effect-types.md`
- **Content**:
  - Reverb types (Hall, Room, Plate, etc.)
  - Delay types (Stereo, Ping-Pong, etc.)
  - Master FX types (Compressor, EQ, Distortion, etc.)

### 2.2 Effect Preset List
- **Source**: `Effect_Preset_List.pdf`
- **Output**: `docs/Seqtrak/effects/effect-types.md` (append)
- **Content**: Named effect presets per category

### 2.3 Effect CC Assignments
- **Source**: `Effect_Data_Assign_Table.pdf`
- **Output**: `docs/Seqtrak/effects/effect-cc-assignments.md`
- **Content**: Which CC controls which parameter per effect type

---

## Phase 3: Sound Design Parameters

**Goal**: Complete synth engine reference

### 3.1 Synth Parameters
- **Source**: `Sound_Design_Parameter_List.pdf`
- **Output**: `docs/Seqtrak/sound-design/synth-parameters.md`
- **Content**:
  - FM algorithm list
  - Filter types
  - Envelope parameters
  - Modulation options

### 3.2 Waveform List
- **Source**: `wave_list.pdf`
- **Output**: `docs/Seqtrak/sound-design/waveforms.md`
- **Content**: All oscillator waveform names and indices

---

## Phase 4: Reference Tables

**Goal**: Comprehensive lookup tables

### 4.1 Bank/Program Mapping Table
- **Source**: All preset PDFs combined
- **Output**: `docs/Seqtrak/tables/bank-program-table.md`
- **Format**:
  ```
  | Bank MSB | Bank LSB | Program | Track Type | Preset Name |
  |----------|----------|---------|------------|-------------|
  | 63       | 0        | 0       | Drum       | 808 Kick    |
  ```

### 4.2 Complete Address Map
- **Source**: `Drums_MIDI_Data_Table.pdf`, existing sysex-protocol-reference.md
- **Output**: `docs/Seqtrak/tables/address-map.md`
- **Content**: Every SysEx address and its function

---

## Implementation Approach

### Per-PDF Processing Workflow

1. **Read PDF** using Claude's PDF reading capability
2. **Extract tables** into markdown format
3. **Validate** against live MIDI captures where possible
4. **Create Python data** for presets.py integration
5. **Cross-reference** with existing sysex-protocol-reference.md

### Validation Method

For each preset mapping:
1. Select preset on Seqtrak hardware
2. Capture Bank Select + Program Change MIDI
3. Verify `(bank, program) → name` matches documentation

---

## Integration Deliverable

### `src/open_push/seqtrak/presets.py`

```python
"""
Seqtrak Preset Name Lookup Tables
Generated from Yamaha Seqtrak Data List documentation.
"""

# Drum presets (tracks 1-7: KICK, SNARE, CLAP, HAT1, HAT2, PERC1, PERC2)
DRUM_PRESETS = {
    # (bank_msb, bank_lsb, program): "Preset Name"
    (63, 0, 0): "TR-808 Kick 1",
    (63, 0, 1): "TR-808 Kick 2",
    # ... extracted from Drums.pdf
}

# Synth presets (tracks 8-9: SYNTH1, SYNTH2)
SYNTH_PRESETS = {
    (63, 0, 0): "Init Synth",
    # ... extracted from DX_sampler.pdf
}

# DX presets (track 10)
DX_PRESETS = {
    (63, 0, 0): "DX Piano 1",
    # ... extracted from DX_sampler.pdf
}

# Sampler presets (track 11)
SAMPLER_PRESETS = {
    # User samples - may be dynamic
}

def get_preset_name(track: int, bank_msb: int, bank_lsb: int, program: int) -> str | None:
    """Get preset name for track's current bank/program."""
    key = (bank_msb, bank_lsb, program)

    if 1 <= track <= 7:
        return DRUM_PRESETS.get(key)
    elif 8 <= track <= 9:
        return SYNTH_PRESETS.get(key)
    elif track == 10:
        return DX_PRESETS.get(key)
    elif track == 11:
        return SAMPLER_PRESETS.get(key)
    return None
```

---

## Progress Tracking

| Phase | Task | Status | Output File |
|-------|------|--------|-------------|
| 1.1 | Drum Presets | Not Started | presets/drum-presets.md |
| 1.2 | Synth Presets | Not Started | presets/synth-presets.md |
| 1.3 | DX Presets | Not Started | presets/dx-presets.md |
| 1.4 | Sampler Slots | Not Started | presets/sampler-presets.md |
| 2.1 | Effect Types | Not Started | effects/effect-types.md |
| 2.2 | Effect Presets | Not Started | effects/effect-types.md |
| 2.3 | Effect CC Map | Not Started | effects/effect-cc-assignments.md |
| 3.1 | Synth Params | Not Started | sound-design/synth-parameters.md |
| 3.2 | Waveforms | Not Started | sound-design/waveforms.md |
| 4.1 | Bank/Program | Not Started | tables/bank-program-table.md |
| 4.2 | Address Map | Not Started | tables/address-map.md |
| - | presets.py | Not Started | src/open_push/seqtrak/presets.py |

---

## Next Steps

1. **Start with Phase 1.1** - Read `SEQTRAK_data_list_Drums.pdf` and extract preset list
2. **Create folder structure** - Set up `docs/Seqtrak/presets/`, `effects/`, etc.
3. **Process each PDF** - Extract, format, validate
4. **Build presets.py** - Incrementally as each section is completed
5. **Validate on hardware** - Test preset name display in app.py
