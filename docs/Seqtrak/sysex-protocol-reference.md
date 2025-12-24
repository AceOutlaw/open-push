# Seqtrak SysEx Protocol Reference

Reverse-engineered SysEx addresses for Yamaha Seqtrak.

## General SysEx Format

```
F0 43 10 7F 1C 0C [addr_h] [addr_m] [addr_l] [data...] F7
│  │  │  │  │  │
│  │  │  │  │  └── Model ID (Seqtrak = 0C)
│  │  │  │  └── Sub-group (1C)
│  │  │  └── Category (7F = bulk/system)
│  │  └── Device number (10 = device 0)
│  └── Manufacturer ID (Yamaha = 43)
└── SysEx start
```

---

## Transport Control

| Function | Address | Data | Notes |
|----------|---------|------|-------|
| Play State | `01 10 20` | 01=Playing, 00=Stopped | Feedback from device |
| Record State | `01 10 21` | 01=Recording, 00=Stopped | Feedback from device |

**Note**: For controlling transport, use MIDI Realtime messages (FA=Start, FC=Stop, FB=Continue).

---

## Global Parameters

### Master Volume
| Address | Data | Notes |
|---------|------|-------|
| `00 00 00` | 00-7F | 0-127, global output level |

### Tempo (BPM)
| Address | Data | Notes |
|---------|------|-------|
| `30 40 76` | [MSB] [LSB] | 2 bytes, 5-300 BPM. Example: `00 78` = 120 BPM |

### Scale Type (Global)
| Address | Data | Scale |
|---------|------|-------|
| `30 40 7E` | 00 | Chromatic |
| | 01 | Major |
| | 02 | Minor |
| | 03 | Harmonic Minor |
| | 04 | Dorian |
| | 05 | Mixolydian |
| | 06 | Pentatonic Major |
| | 07 | Pentatonic Minor |

### Key (Global)
| Address | Data | Key |
|---------|------|-----|
| `30 40 7F` | 40 | C |
| | 41 | C# |
| | 42 | D |
| | ... | ... |
| | 4B | B |

---

## Track Parameters

### Track Selection
| Address | Data | Track |
|---------|------|-------|
| `01 10 27` | 00 | KICK |
| | 01 | SNARE |
| | 02 | CLAP |
| | 03 | HAT 1 |
| | 04 | HAT 2 |
| | 05 | PERC 1 |
| | 06 | PERC 2 |
| | 07 | SYNTH 1 |
| | 08 | SYNTH 2 |
| | 09 | DX |
| | 0A | SAMPLER |

### Track Octave
Address format: `30 5[track] 0C`

| Track | Address | Data Range |
|-------|---------|------------|
| KICK | `30 50 0C` | 3D-42 (center=40) |
| SNARE | `30 51 0C` | 3D-42 |
| ... | ... | ... |
| SYNTH 1 | `30 57 0C` | 3D-42 |

Values: 3D=-3, 3E=-2, 3F=-1, 40=0, 41=+1, 42=+2

### Track Mute
Address format: `30 5[track] 0F`

| Track | Address | Data |
|-------|---------|------|
| KICK | `30 50 0F` | 00=unmute, 01=mute, 02=solo |
| SNARE | `30 51 0F` | ... |

---

## Pattern/Variation Control

### Pattern Variation Selection
| Address | Data | Notes |
|---------|------|-------|
| `30 50 0F` | 00-05 | Variation 1-6 (for KICK track) |

Variation addresses are per-track: `30 5[track] 0F`

---

## UI State / Display Mode

| Address | Data | Mode |
|---------|------|------|
| `01 10 2E` | 01 | Default/idle |
| | 09 | Volume adjust |
| | 14 | Scale select |
| | 17 | Octave adjust |
| | 1A | BPM adjust |

### Options Page Navigation
| Address | Data | Page |
|---------|------|------|
| `01 17 30` | 00 | Page 1 |
| | 01 | Page 2 |
| | 02 | Page 3 |
| | 03 | Page 4 |

---

## Sound Selection (Standard MIDI)

Sound changes use standard MIDI, not SysEx:
```
Bank Select MSB (CC 0): [bank_msb]
Bank Select LSB (CC 32): [bank_lsb]
Program Change: [program]
```

Example from capture (SYNTH 1, channel 8):
- Bank Select: 63
- Bank Select (fine): 6
- Program: 96

---

## Step Sequencer Data

### DRUM Tracks (Channels 1-7) - Command `70`

**Format (15 bytes total):**
```
70 [track] [var] [step] [note] [vel] [dur_h] [dur_l]
│    │      │      │      │      │      └───────────── Duration (2 bytes)
│    │      │      │      │      └── Velocity (0-127)
│    │      │      │      └── MIDI note (3C = 60 = C4)
│    │      │      └── Step number (00-7F, up to 128 steps)
│    │      └── Variation (00 = variation 1)
│    └── Track: 00=KICK, 01=SNARE, 02=CLAP, 03=HAT1, 04=HAT2, 05=PERC1, 06=PERC2
└── Drum step command
```

**Example - KICK step 0:**
```
70 00 00 00 3C 64 00 78
   │  │  │  │  │  └────── Duration = 0x78 = 120 ticks
   │  │  │  │  └── Velocity = 0x64 = 100
   │  │  │  └── Note = 0x3C = 60 (C4)
   │  │  └── Step 0
   │  └── Variation 0
   └── Track 0 (KICK)
```

**Example - SNARE step 5:**
```
70 01 00 05 3C 64 00 78
   └── Track 1 (SNARE)
```

### SAMPLER Track (Channel 11) - Command `72`

**Format (18 bytes total) - DIFFERENT from drums!**
```
72 30 00 [step] [tick_pos] 00 [note] [vel] 00 00 [dur]
│     │    │      │          │   │      │          └── Duration
│     │    │      │          │   │      └── Velocity (0x64 = 100)
│     │    │      │          │   └── Note (0x3F = 63)
│     │    │      │          └── Padding
│     │    │      └── Tick position within pattern (for micro-timing)
│     │    └── Step number (00-0F)
│     └── Unknown (always 00?)
└── Sampler step command
```

**Tick position progression (16-step pattern):**
| Step | Tick Pos | Calculation |
|------|----------|-------------|
| 0 | 00 00 | Step 0 at tick 0 |
| 0 | 00 78 | Step 0 at tick 120 (alternative position?) |
| 1 | 01 70 | Step 1 at tick 112? |
| 2 | 02 68 | Step 2 at tick 104? |
| ... | ... | Decreasing by 8 |
| 15 | 0F 00 | Step 15 |

**Note**: The tick position byte needs more analysis - may relate to swing or micro-timing.

---

## Preset Name Data

Long-form message (110 bytes) contains preset name as ASCII:

**Address**: `01 10 35`

**Example:**
```
01 10 35 00 54 53 5F 52 4E 42 5F 00 6B 69 63 6B 5F 72 6E 00 62 ...
              T  S  _  R  N  B  _     k  i  c  k  _  r  n     b
```

Decoded: "TS_RNB_" + "kick_rn" + "b" = Preset name for RnB kick sound

---

## Address Space Summary

| Range | Purpose |
|-------|---------|
| `00 xx xx` | Master/global parameters |
| `01 1x xx` | UI state, display, selection |
| `01 17 xx` | Options/navigation |
| `30 40 xx` | Global settings (tempo, scale, key) |
| `30 5x xx` | Track parameters (x = track 0-A) |
| `31 xx xx` | Sound engine parameters |
| `41 xx xx` | Effect parameters |
| `70 xx xx` | Drum step data (tracks 0-6) |
| `72 xx xx` | Sampler step data (track 10) |

---

## What Requires SysEx (Not Available via CC)

These parameters are NOT in the official MIDI CC spec and require SysEx:

1. **Tempo** - `30 40 76`
2. **Scale type** - `30 40 7E`
3. **Key** - `30 40 7F`
4. **Pattern length** - `30 40 7A`
5. **Swing** - `30 40 7C`
6. **Track octave** - `30 5x 0C`
7. **Step sequence data** - `70 xx` (drums), `72 xx` (sampler)
8. **Pattern/variation select** - `30 5x 0F`
9. **Track select** - `01 10 27`
10. **Preset names** - `01 10 35`

---

## Raw Capture Archive

### Kick Drum - 16 Steps (for reference)
```
70 00 00 00 3C 64 00 78  Step 0
70 00 00 01 3C 64 00 78  Step 1
70 00 00 02 3C 64 00 78  Step 2
...
70 00 00 0F 3C 64 00 78  Step 15
```

### Snare Drum - 16 Steps
```
70 01 00 00 3C 64 00 78  Step 0
70 01 00 01 3C 64 00 78  Step 1
...
70 01 00 0F 3C 64 00 78  Step 15
```

### Sampler - 16 Steps (different format!)
```
72 30 00 00 00 00 3F 64 00 00 78  Step 0 (tick 0)
72 30 00 00 78 00 3F 64 00 00 78  Step 0 (tick 120?)
72 30 00 01 70 00 3F 64 00 00 78  Step 1
72 30 00 02 68 00 3F 64 00 00 78  Step 2
72 30 00 03 60 00 3F 64 00 00 78  Step 3
72 30 00 04 58 00 3F 64 00 00 78  Step 4
72 30 00 05 50 00 3F 64 00 00 78  Step 5
72 30 00 06 48 00 3F 64 00 00 78  Step 6
72 30 00 07 40 00 3F 64 00 00 78  Step 7
72 30 00 08 38 00 3F 64 00 00 78  Step 8
72 30 00 09 30 00 3F 64 00 00 78  Step 9
72 30 00 0A 28 00 3F 64 00 00 78  Step 10
72 30 00 0B 20 00 3F 64 00 00 78  Step 11
72 30 00 0C 18 00 3F 64 00 00 78  Step 12
72 30 00 0D 10 00 3F 64 00 00 78  Step 13
72 30 00 0E 08 00 3F 64 00 00 78  Step 14
72 30 00 0F 00 00 3F 64 00 00 78  Step 15 (inferred)
```

---

## Still To Decode

- [ ] Synth track recording (if different from sampler)
- [ ] Effect type selection addresses
- [ ] Pattern copy/paste
- [ ] Sample start/end points (sampler-specific)
- [ ] Motion sequence data
