# Seqtrak MIDI Data Table Reference

Extracted from Yamaha Seqtrak Data List documentation.

## SysEx Message Formats

All Seqtrak SysEx messages use:
- **Group Number**: `7F 1C`
- **Model ID**: `0C`

### Message Types

| Message Type | Format |
|-------------|--------|
| Parameter Change | `F0 43 1n gh gl id ah am al dt ... F7` |
| Parameter Request | `F0 43 3n gh gl id ah am al F7` |
| Bulk Dump | `F0 43 0n gh gl bh bl id ah am al dt ... cc F7` |
| Bulk Request | `F0 43 2n gh gl id ah am al F7` |

Where:
- `n` = Device Number
- `gh gl` = Group Number (`7F 1C`)
- `bh bl` = Byte Count (MSB LSB)
- `id` = Model ID (`0C`)
- `ah am al` = Parameter Address (High, Middle, Low)
- `dt` = Data
- `cc` = Checksum

### Example: Parameter Change
```
F0 43 10 7F 1C 0C [addr_h] [addr_m] [addr_l] [data...] F7
```

### Example: Parameter Request
```
F0 43 30 7F 1C 0C [addr_h] [addr_m] [addr_l] F7
```

---

## Bank Select / Program Change

### Project Selection (MSB 64 / 0x40)

| MSB | LSB | Program | Type | Memory | Notes |
|-----|-----|---------|------|--------|-------|
| 64 (0x40) | 0 | 0-8 | Project / Temporary Project | User 1 | Channel ignored. Program 8 = Temporary |

### Drum / Synth / DX Sound (MSB 63 / 0x3F)

| MSB | LSB | Program | Memory |
|-----|-----|---------|--------|
| 63 | 0-31 | 0-127 | Preset 1-32 |
| 63 | 32-47 | 0-127 | User 1-16 |

### Sampler Element (MSB 62 / 0x3E)

| MSB | LSB | Program | Memory | Notes |
|-----|-----|---------|--------|-------|
| 62 | 0-3 | 0-127 | Preset 1-4 | Channel = element number |
| 62 | 4-11 | 0-127 | User 1-8 | Programs 72-127 reserved for sampler function |

---

## Parameter Base Address

### System
| Address (H M L) | Description |
|----------------|-------------|
| 00 00 00 | General |
| 00 7F 00 | Format Version |

### Bulk Control
| Address (H M L) | Description |
|----------------|-------------|
| 11 00 00 | Header |
| 12 00 00 | Footer |

### Project Common
| Address (H M L) | Description |
|----------------|-------------|
| 30 40 00 | General |
| 30 41 00 | Send Reverb |
| 30 42 00 | Send Delay |
| 30 43-46 00 | Master Effect 1-4 |
| 30 47 00 | Master EQ |
| 30 49 00 | A/D Part Insertion A |
| 30 4A 00 | A/D Part Insertion B |
| 30 4B 00 | A/D Part General |
| 30 4C 00 | USB Audio Input |
| 30 4D 00 | Scale |

### Project Track
| Address (H M L) | Description |
|----------------|-------------|
| 30 5p 00 | General [p=Part 0-10] |
| 30 6p 00 | Chord Notes Scale 1-4 [p=Part 7-9] |
| 30 7p 00 | Chord Notes Scale 5-8 [p=Part 7-9] |

### Sound Common
| Address (H M L) | Description |
|----------------|-------------|
| 31 0p 00 | Name [p=Part 0-10] |
| 31 1p 00 | General [p=Part 0-10] |
| 31 2p 00 | Insertion A [p=Part 0-10] |
| 31 3p 00 | Insertion B [p=Part 0-10] |
| 31 4p 00 | LFO [p=Part 0-8,10] |
| 31 5p 00 | Arpeggiator [p=Part 7-9] |

### Sound Drum/Synth/SAMPLER
| Address (H M L) | Description |
|----------------|-------------|
| 41 ep 00 | Oscillator/Amplitude/Pitch [p=Part 0-8,10; e=Element 0-7] |
| 42 ep 00 | Filter/EQ/LFO [p=Part 0-8,10; e=Element 0-7] |

### Sound DX
| Address (H M L) | Description |
|----------------|-------------|
| 48 09 00 | Common |
| 49 o9 00 | Operator [o=Operator 0-3] |

### SAMPLER Sample
| Address (H M L) | Description |
|----------------|-------------|
| 50 eA 00 | General [e=Element 0-6] |

---

## System Parameters (00 00 xx)

| Offset | Size | Range | Parameter | Description | Default |
|--------|------|-------|-----------|-------------|---------|
| 00 | 1 | 0-127 | Speaker Master Volume | 0-127 | 100 (0x64) |
| 01 | 1 | 0-127 | Headphone Master Volume | 0-127 | 32 (0x20) |
| 02 | 4 | - | Master Tune | -102.4 to +102.3 | 0 |
| 06 | 1 | 0-1 | Local Switch | Off, On | On |
| 07 | 1 | 0-1 | Receive/Transmit Bank Select | Off, On | On |
| 08 | 1 | 0-1 | Receive/Transmit Program Change | Off, On | On |
| 09 | 1 | 0-1 | Legacy MIDI In/Out | Off, On | On |
| 0D | 1 | 0-1 | USB MIDI In/Out | Off, On | On |
| 11 | 1 | 0-1 | Bluetooth MIDI In/Out | Off, On | Off |
| 20 | 1 | 1-127 | Pad Velocity | 1-127 | 100 (0x64) |
| 25 | 1 | 0-1 | Click Switch | Off, On | Off |
| 26 | 1 | 0-9 | Click Type | 1-10 | 0 |
| 27 | 1 | 0-127 | Click Volume | 0-127 | 64 (0x40) |
| 2A | 1 | 0-1 | MIDI Sync | Internal, MIDI(Auto) | On |
| 2B | 1 | 0-1 | Transmit Sequencer Control | Off, On | On |
| 2D | 1 | 0-1 | MIDI Clock Out | Off, On | On |

---

## Project Common General (30 40 xx)

| Offset | Size | Parameter | Description | Default |
|--------|------|-----------|-------------|---------|
| 00-57 | 88 | Project Name 1-88 | UTF8 (7-bit encoded) | 0 |
| 63 | 1 | Sampler Element Mute | bit6-0: element7-1 mute | 0 |
| 65 | 1 | Pan | L63...C...R63 | 64 (center) |
| 66 | 1 | Volume | 0-127 | 127 |
| 68 | 1 | Solo Track | Off, Track 1-11 | Off |
| 75 | 1 | ARP Synchro Quantize Value | 240 | 5 |
| 76 | 2 | Tempo | 5-300 BPM | 120 (0x0078) |
| 79 | 1 | Pattern Select Mode | Normal, Advanced | Normal |
| 7A | 2 | Pattern Master Step | 1-128 | 16 (0x0010) |
| 7C | 2 | Swing Offset | -58 to +58 | 0 |
| 7E | 1 | Scale | Scale 1-8 | 0 |
| 7F | 1 | Key | 0-11 (C to B) | 0 (C) |

---

## Project Track General (30 5p 00)

Part numbers: 0-10 (Part 1-11: Drum, Synth, DX, SAMPLER)

| Offset | Size | Parameter | Description | Default |
|--------|------|-----------|-------------|---------|
| 00 | 1 | Volume | 0-127 | 100 (0x64) |
| 01 | 1 | Pan | L63...C...R63 | 64 (center) |
| 02 | 1 | Velocity Limit Low | 1-127 | 1 |
| 03 | 1 | Velocity Limit High | 1-127 | 127 |
| 04 | 1 | Note Limit Low | C-2...G8 | 0 |
| 05 | 1 | Note Limit High | C-2...G8 | 127 |
| 08 | 1 | Group Number | Off, Group 1-127 | Off |
| 0C | 1 | Octave | -2 to +2 | 0 (0x40) |
| 0F | 1 | Pattern Select | 1-6 | 0 |
| 16-21 | 2 each | Pattern 1-6 Step | 1-128 | 16 |
| 29 | 1 | Mute | Off, On | Off |

---

## Sound Common Name (31 0p 00)

| Offset | Size | Parameter | Description |
|--------|------|-----------|-------------|
| 00-63 | 100 | Sound Name 1-100 | UTF8 (7-bit encoded) |

---

## Sound Common General (31 1p 00)

| Offset | Size | Parameter | Description | Default |
|--------|------|-----------|-------------|---------|
| 00 | 1 | AEG Decay/Release Offset | -64 to +63 | 0 (0x40) |
| 0D | 1 | Trigger/Gate Mode | Trigger, Gate, Depend on Voice | 2 |
| 10 | 1 | Pitch Bend Range Upper | -48 to +24 | +2 (0x42) |
| 11 | 1 | Pitch Bend Range Lower | -48 to +24 | -2 (0x3E) |
| 12 | 1 | Velocity Sense Depth | 0-127 | 64 |
| 13 | 1 | Velocity Sense Offset | 0-127 | 64 |
| 14 | 1 | Volume | 0-127 | 100 |
| 15 | 1 | Pan | L63...C...R63 | 64 |
| 19 | 1 | Reverb Send | 0-127 | 0 |
| 1A | 1 | Variation Send | 0-127 | 0 |
| 1B | 1 | Dry Level | 0-127 | 127 |
| 1C | 1 | Note Shift | -24 to +24 semitones | 0 |
| 1E | 1 | Portamento Switch | Off, On | Off |
| 1F | 1 | Portamento Time | 0-127 | 64 |
| 23 | 1 | Mono/Poly Mode | Mono, Poly, Chord | Poly |
| 2C-2F | 1 each | AEG Attack/Decay/Sustain/Release | -64 to +63 | 0 |
| 30-34 | 1 each | FEG Attack/Decay/Sustain/Release/Depth | -64 to +63 | 0 |
| 36 | 1 | Filter Cutoff Frequency | -64 to +63 | 0 |
| 37 | 1 | Filter Resonance/Width | -64 to +63 | 0 |

---

## Sound Element Oscillator/Amplitude/Pitch (41 ep 00)

| Offset | Size | Parameter | Description | Default |
|--------|------|-----------|-------------|---------|
| 00 | 1 | Element Assign | Off, On | On (element 1), Off (2-8) |
| 01 | 1 | Wave Select | Preset, User | Preset |
| 02 | 1 | Element Group Number | 1-8 | 1 |
| 03 | 2 | Wave Number | 1-4096 (Preset), 1-2048 (User) | 1 |
| 08 | 1 | Trigger/Gate Mode | Trigger, Gate | Trigger |
| 0A | 1 | Alternate Group | Off, 1-127 | Off |
| 0B | 1 | Pan | L63...C...R63 | 64 |
| 0F | 1 | XA Control | Normal, Legato, Key Off, Cycle, Random | Normal |
| 10 | 1 | Note Limit Low | C-2...G8 | 0 |
| 11 | 1 | Note Limit High | C-2...G8 | 127 |
| 12 | 1 | Velocity Limit Low | 1-127 | 1 |
| 13 | 1 | Velocity Limit High | 1-127 | 127 |
| 18 | 1 | Insertion Effect Switch | Thru, InsA, InsB | InsA |
| 2E | 1 | Element Level | 0-127 | 100 |
| 2F | 1 | Level Velocity Sensitivity | -64 to +63 | 20 (0x54) |
| 33-37 | 1 each | AEG Attack/Decay1/Decay2/HalfDamper/Release | 0-127 | varies |
| 4F | 1 | Coarse Tune | -24 to +24 | 0 |
| 50 | 1 | Fine Tune | -64 to +63 | 0 |
| 54 | 1 | Pitch Key Follow Sensitivity | -200 to +200% | 96 (0x60) |

---

## Sound Element Filter/EQ/LFO (42 ep 00)

| Offset | Size | Parameter | Description | Default |
|--------|------|-----------|-------------|---------|
| 00 | 1 | Filter Type | LPF24D, LPF24A, LPF18, etc. | LPF12+HPF12 |
| 01 | 2 | Filter Cutoff Frequency | 0-255 | 288 (0x0120) |
| 03 | 1 | Filter Cutoff Velocity Sensitivity | -64 to +63 | 0 |
| 05 | 1 | Filter Resonance/Width | 0-127 | 0 |
| 0E-12 | 1 each | FEG Hold/Attack/Decay1/Decay2/Release | 0-127 | varies |
| 1D | 1 | FEG Depth | -64 to +63 | 40 (0x68) |
| 32 | 1 | EQ Type | 2-band, P.EQ, Boost6/12/18, Thru | 2-band |
| 3A | 1 | LFO Wave | Saw, Triangle, Square | Triangle |
| 3D | 1 | LFO Speed | 0-63 | 38 (0x26) |
| 3E | 1 | LFO AMod Depth | 0-127 | 0 |
| 3F | 1 | LFO PMod Depth | 0-127 | 0 |
| 40 | 1 | LFO FMod Depth | 0-127 | 0 |

---

## DX Sound Common (48 09 00)

| Offset | Size | Parameter | Description | Default |
|--------|------|-----------|-------------|---------|
| 00 | 1 | Algorithm | 1-12 | 1 |
| 02 | 1 | Pitch Bend Sensitivity | -24 to +24 semitones | +2 |
| 04 | 1 | LFO Wave | Sin, Tri, Saw-Up, Saw-Down, Square, S&H8, S&H | Sin |
| 05 | 1 | LFO Speed | 0-127 | 64 |
| 06 | 1 | LFO Delay | 0-127 | 0 |
| 07 | 1 | LFO PMD | 0-127 | 0 |
| 0A-0D | 1 each | PEG Rate 1-4 | 0-127 | 64 |
| 0E-11 | 1 each | PEG Level 1-4 | -48 to +48 | 0 |

---

## DX Sound Operator (49 o9 00)

Operator numbers: 0-3 (Operator 1-4)

| Offset | Size | Parameter | Description | Default |
|--------|------|-----------|-------------|---------|
| 00 | 1 | ON/OFF | Off, On | On |
| 02-05 | 1 each | EG Rate 1-4 | 0-127 | 127,127,127,100 |
| 06-09 | 1 each | EG Level 1-4 | 0-127 | 127,127,127,0 |
| 0A | 1 | EG Keyboard Rate Scaling | 0-127 | 0 |
| 0C | 1 | KLS Left Depth | 0-127 | 0 |
| 0D | 1 | KLS Right Depth | 0-127 | 0 |
| 0E | 1 | KLS Left Curve | -LIN, -EXP, +EXP, +LIN | -LIN |
| 0F | 1 | KLS Right Curve | -LIN, -EXP, +EXP, +LIN | +LIN |
| 11 | 1 | LFO AMD Depth | 0-127 | 0 |
| 12 | 1 | Level Velocity Sensitivity | 0-127 | 0 |
| 13 | 1 | Level Output Level | 0-127 | 100 (Op1), 0 (Op2-3), 100 (Op4) |
| 14 | 1 | Feedback Level | 0-127 | 0 |
| 15 | 1 | Feedback Type | SAW, SQUARE | SAW |
| 17 | 1 | LFO PMD ON/OFF | Off, On | On |
| 18 | 1 | PEG ON/OFF | Off, On | On |
| 19 | 1 | Freq. Mode | RATIO, FIXED | RATIO |
| 1A | 1 | Freq. Coarse | 0-31 | 1 |
| 1B | 1 | Freq. Fine | 0-99 | 0 |
| 1C | 1 | Freq. Detune | -64 to +63 | 0 |

---

## SAMPLER Sample (50 eA 00)

Element numbers: 0-6 (Element 1-7)

| Offset | Size | Parameter | Description | Default |
|--------|------|-----------|-------------|---------|
| 00-57 | 88 | Sample Name 1-88 | UTF8 (7-bit encoded) | 0 |
| 5F | 1 | Loop On/Off | Off, On | Off |
| 60 | 4 | Loop Length | 0x50 to 0xFFFFFF | 0 |
| 66 | 4 | Start Point | 0x00 to 0xFFFFFF | 0 |
| 6A | 4 | End Point | 0x00, 0x0F to 0xFFFFFF | 0 (empty) |

---

## LFO Parameters (31 4p 00)

| Offset | Size | Parameter | Description | Default |
|--------|------|-----------|-------------|---------|
| 00 | 1 | LFO Phase | 0, 90, 120, 180, 240, 270 | 0 |
| 01 | 1 | LFO Wave | Triangle, Triangle+, Saw Up/Down, Square variants, S/H, User | Triangle |
| 02 | 1 | LFO Speed | 0-63 | 32 |
| 03 | 1 | LFO Tempo Speed | 16th to 4thX64 | 11 (4th) |
| 04 | 1 | LFO Tempo Sync | Off, On | Off |
| 05 | 1 | LFO Delay Time | 0-127 | 0 |
| 06 | 1 | LFO Fade In Time | 0-127 | 0 |
| 07 | 1 | LFO Hold Time | 0-126, Hold | Hold |
| 08 | 1 | LFO Fade Out Time | 0-127 | 64 |
| 09 | 1 | LFO Key On Reset | Off, Each-On, 1st-On | 1st-On |
| 0A | 1 | LFO Play Mode | Loop, One-shot | Loop |
| 0B | 1 | LFO Box1 Destination | 0-68 | 64 (Element Level) |
| 0C | 1 | LFO Box1 Depth | 0-127 | 0 |
| 0E | 1 | LFO Box2 Destination | 0-68 | 65 (Element Pitch) |
| 0F | 1 | LFO Box2 Depth | 0-127 | 0 |
| 11 | 1 | LFO Box3 Destination | 0-68 | 66 (Element Filter Cutoff) |
| 12 | 1 | LFO Box3 Depth | 0-127 | 0 |
| 16-25 | 1 each | User Wave Step Value 1-16 | -64 to +63 | 0 |

---

## Arpeggiator Parameters (31 5p 00)

Part numbers: 7-9 (Part 8-10: Synth, DX)

| Offset | Size | Parameter | Description | Default |
|--------|------|-----------|-------------|---------|
| 00 | 1 | ARP Template | Off, Up, Up 2Oct, Down, etc. | Off |
| 01 | 1 | ARP Switch | Off, On | Off |
| 06 | 1 | ARP Loop | Off, On | On |
| 07 | 1 | ARP Hold | Sync-Off, Off, On | Off |
| 08 | 1 | ARP Unit Multiply | 50%-400% | 100% |
| 09 | 1 | ARP Note Limit Low | C-2...G8 | 0 |
| 0A | 1 | ARP Note Limit High | C-2...G8 | 127 |
| 0D | 1 | ARP Key Mode | Sort, Thru, Direct, Sort+Drct, Thru+Drct | Sort |
| 0E | 1 | ARP Vel Mode | Original, Thru | Thru |
| 1C | 1 | ARP Octave Range | -3 to +3 | 0 |
| 1E | 2 | ARP Type | Up, Down, Random, Up Down 1/2, Slap & Pop, Unison, Rhythm 1/2 | Up |

---

## LFO Destinations

### Common Parameters (0-63)
| No. | Parameter |
|-----|-----------|
| 0-23 | Insertion Effect A Parameter 1-24 |
| 32-55 | Insertion Effect B Parameter 1-24 |

### Drum/Synth/SAMPLER Parameters (64-68)
| No. | Parameter |
|-----|-----------|
| 64 | Element Level |
| 65 | Element Pitch |
| 66 | Element Filter Cutoff |
| 67 | Element Filter Resonance/Width |
| 68 | Element Pan |

---

## Filter Types

| Value | Type |
|-------|------|
| 0 | LPF24D |
| 1 | LPF24A |
| 2 | LPF18 |
| 3 | LPF18s |
| 4 | LPF12+HPF12 |
| 5 | LPF6+HPF12 |
| 6 | HPF24D |
| 7 | HPF12 |
| 8 | BPF12D |
| 10 | BPFw |
| 11 | BPF6 |
| 12 | BEF12 |
| 13 | BEF6 |
| 14 | DualLPF |
| 15 | DualHPF |
| 16 | DualBPF |
| 17 | DualBEF |
| 19 | LPF12+BPF6 |
| 21 | Thru |

---

## Bulk Control Headers

### Bulk Header (11 xx nn)

| Address | Description |
|---------|-------------|
| 11 00 nn | Project Edit Buffer (nn=0) |
| 11 01 nn | Project User 1 (nn=0-7) |
| 11 02 nn | Sound Edit Buffer Part nn (nn=0-10) |
| 11 03-12 nn | Sound User 1-16 (nn=0-127) |
| 11 13 nn | Sampler Element Edit Buffer (nn=0-6) |
| 11 14-1B nn | Sampler Element User 1-8 (nn=0-127) |

### Bulk Footer (12 xx nn)
Same structure as Bulk Header but with address prefix 12.

---

## Notes

- Part numbers are 0-indexed in addresses (Part 1 = 0, Part 11 = 10)
- Element numbers are 0-indexed (Element 1 = 0, Element 8 = 7)
- MIDI channel in Bank Select/Program Change corresponds to Part number (Ch 1-11 = Part 1-11)
- For Sampler Element, channel number represents element number
- Multi-byte values use 7-bit encoding: MSB bit6-0 → high bits, LSB bit6-0 → low bits
- UTF8 names use 7-bit encoding
- All addresses are hexadecimal
