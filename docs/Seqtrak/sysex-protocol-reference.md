# Seqtrak MIDI Protocol Reference

Complete MIDI protocol documentation for Yamaha Seqtrak, combining official Yamaha documentation with reverse-engineered SysEx addresses.

*Source: Yamaha SEQTRAK User Guide (MIDI section) + live MIDI capture logs*

> **Read this before using this file (updated 2026-10-13).** The Seqtrak is not in any AI model's training
> data; this file is the reference for what each message does. Status key: ✅ verified on hardware ·
> 🟡 observed, not fully verified · ❓ unknown — anything unmarked from Dec 2025 should be treated as 🟡.
> - **Step data:** the "Step Sequencer Data" section below was rewritten from verified tests; details in
>   `docs/Seqtrak/STEP-SEQUENCER.md` (wins on any disagreement).
> - **What a button / LED / mode does on the device:** Yamaha's user guide, text extract at
>   `reference files/Yamaha/User Guide/SEQTRAK_user_guide_En_D0.txt` (local only) — cite its § numbers.
> - **Official parameter addresses:** `docs/Seqtrak/midi-data-table.md` and the Data List PDFs.
> - **How things were found + lessons:** `docs/Seqtrak/REVERSE-ENGINEERING-LOG-2026-10.md`.
> - A message the Seqtrak *sends* may only be a report; never assume it works as a command until tested.

---

# PART 1: Standard MIDI (Official Documentation)

Use standard MIDI CC where available - it's documented, reliable, and easier to implement.

---

## Track Types Reference

*Source: SEQTRAK_data_list_Core.pdf*

Each track has a dedicated MIDI channel and belongs to a track group:

| Track Name | Track Group | MIDI Channel |
|------------|-------------|--------------|
| KICK | Drum | 1 |
| SNARE | Drum | 2 |
| CLAP | Drum | 3 |
| HAT 1 | Drum | 4 |
| HAT 2 | Drum | 5 |
| PERC 1 | Drum | 6 |
| PERC 2 | Drum | 7 |
| SYNTH 1 | Synth | 8 |
| SYNTH 2 | Synth | 9 |
| DX | DX | 10 |
| SAMPLER | SAMPLER | 11 |

---

## Sound Categories

*Source: SEQTRAK_data_list_Core.pdf*

Each track type has 15 sound categories available:

| No. | Drum | Synth | DX | SAMPLER |
|-----|------|-------|-----|---------|
| 1 | Kick | Bass | Bass | Vocal Count |
| 2 | Snare | Synth Lead | Synth Lead | Vocal Phrase / Chant |
| 3 | Rim | Piano | Piano | Singing Vocal |
| 4 | Clap | Keyboard | Keyboard | Robotic Vocal / Effect |
| 5 | Snap | Organ | Organ | Riser |
| 6 | Closed HiHat | Pad | Pad | Laser / Sci-Fi |
| 7 | Open HiHat | Strings | Strings | Impact |
| 8 | Shaker / Tambourine | Brass | Brass | Noise / Distorted Sound |
| 9 | Ride | Woodwind | Woodwind | Ambient / Soundscape |
| 10 | Crash | Guitar | Guitar | SFX |
| 11 | Tom | World | World | Scratch |
| 12 | Bell | Mallet | Mallet | Nature / Animals |
| 13 | Conga / Bongo | Bell | Bell | Hit / Stab / Musical Instrument Sound |
| 14 | World | Rhythmic | Rhythmic | Percussion |
| 15 | SFX | SFX | SFX | Recorded Sound |

---

## Sound Design Parameters (CC)

### Universal Parameters (All Tracks)

| Parameter | CC | Channel | Range | Notes |
|-----------|-----|---------|-------|-------|
| Volume | 7 | 1-11 | 0-127 | Track volume |
| Pan | 10 | 1-11 | 1-127 | 64=center |
| Attack Time | 73 | 1-11 | 0-127 | AEG attack |
| Decay/Release | 75 | 1-11 | 0-127 | AEG decay/release |
| Filter Cutoff | 74 | 1-11 | 0-127 | LP-HP cutoff |
| Filter Resonance | 71 | 1-11 | 0-127 | LP-HP resonance |
| Reverb Send | 91 | 1-11 | 0-127 | Send to reverb |
| Delay Send | 94 | 1-11 | 0-127 | Send to delay |
| EQ High Gain | 20 | 1-11 | 40-88 | 64=flat |
| EQ Low Gain | 21 | 1-11 | 40-88 | 64=flat |
| Expression | 11 | 1-11 | 0-127 | Expression control (receive only) |

**Bridge use (from code):** Device mode sends these CCs on the selected track's channel —
drums: 7, 10, 25, 73, 75, 74, 71, 91, 94, 20, 21; synth/DX add 26, 5, 65, 27, 28, 29; DX adds 116–119;
sampler: 7, 10, 73, 75, 74, 71, 91, 94, 20, 21. 🟡 (official CCs, "Sound design knobs ✅ Send" in
`FUNCTIONALITY-MAP.md`; not individually verified). Used by bridge: `protocol.py:send_track_cc` ←
`app.py:handle_encoder` (device mode, tables `DEVICE_PARAMS_*`). Mixer mode sends CC 7 per track
(`protocol.py:set_track_volume` ← `app.py:handle_encoder`, `app.py:_adjust_drum_bus_volume` = CC 7 on
channels 1–7 scaled by the DRUM bus level). Note: the bridge clamps every value to 0–127, not to the
ranges above (e.g. EQ 40–88, CC 26 0–2, CC 27 0–16, CC 29 0–9). The bridge does not read these back
(it starts each knob from a default) and ignores CCs the Seqtrak sends, except Bank Select.

### Drum-Only Parameters (Channels 1-7)

| Parameter | CC | Channel | Range | Notes |
|-----------|-----|---------|-------|-------|
| Drum Pitch | 25 | 1-7 | 40-88 | 64=center pitch |

### Synth/DX Parameters (Channels 8-10)

| Parameter | CC | Channel | Range | Notes |
|-----------|-----|---------|-------|-------|
| Mono/Poly/Chord | 26 | 8-10 | 0-2 | 0=Mono, 1=Poly, 2=Chord |
| Portamento Time | 5 | 8-10 | 0-127 | 0=OFF (must be mono) |
| Portamento Switch | 65 | 8-10 | 0/1 | 0=OFF, 1=ON |
| Arp Type | 27 | 8-10 | 0-16 | 0=OFF |
| Arp Gate | 28 | 8-10 | 0-127 | Gate time |
| Arp Speed | 29 | 8-10 | 0-9 | Speed setting |

### DX-Only Parameters (Channel 10)

| Parameter | CC | Channel | Range | Notes |
|-----------|-----|---------|-------|-------|
| FM Algorithm | 116 | 10 | 0-127 | 12 algorithms |
| FM Mod Amount | 117 | 10 | 0-127 | Modulator level |
| FM Mod Frequency | 118 | 10 | 0-127 | Modulator freq |
| FM Mod Feedback | 119 | 10 | 0-127 | Modulator feedback |

### Keyboard/Pedal (Channels 8-11)

| Parameter | CC | Channel | Range | Notes |
|-----------|-----|---------|-------|-------|
| Damper Pedal | 64 | 8-11 | 0-127 | Sustain (receive only) |
| Sostenuto | 66 | 8,9,11 | 0-63/64-127 | OFF/ON (receive only) |

---

## Effect Parameters (CC)

### Master Effects (Channel 1 only)

| Parameter | CC | Range | Notes |
|-----------|-----|-------|-------|
| Master FX 1 Param 1 | 102 | 0-127 | Assigned parameter |
| Master FX 1 Param 2 | 103 | 0-127 | Assigned parameter |
| Master FX 1 Param 3 | 104 | 0-127 | Assigned parameter |
| Master FX 2 Param | 105 | 0-127 | Assigned parameter |
| Master FX 3 Param | 106 | 0-127 | Assigned parameter |

### Single Effects (Per-Track)

| Parameter | CC | Channel | Range | Notes |
|-----------|-----|---------|-------|-------|
| Single FX Param 1 | 107 | 1-11 | 0-127 | Per-track effect |
| Single FX Param 2 | 108 | 1-11 | 0-127 | Per-track effect |
| Single FX Param 3 | 109 | 1-11 | 0-127 | Per-track effect |

### Send Effects (Channel 1 only)

| Parameter | CC | Range | Notes |
|-----------|-----|-------|-------|
| Send Reverb Param 1 | 110 | 0-127 | Reverb parameter |
| Send Reverb Param 2 | 111 | 0-127 | Reverb parameter |
| Send Reverb Param 3 | 112 | 0-127 | Reverb parameter |
| Send Delay Param 1 | 113 | 0-127 | Delay parameter |
| Send Delay Param 2 | 114 | 0-127 | Delay parameter |
| Send Delay Param 3 | 115 | 0-127 | Delay parameter |

---

## Mute/Solo (CC)

| Parameter | CC | Channel | Range | Notes |
|-----------|-----|---------|-------|-------|
| Mute | 23 | 1-11 | 0-63=OFF, 64-127=ON | **Receive only** |
| Solo | 24 | 1-11 | 0-11 | 0=OFF, 1-11=Track# | **Receive only** |

**Important**: Mute and Solo are receive-only. Seqtrak will respond to these CCs but won't send them.

**Bridge use (from code):** Mute = CC 23 value `127` (on) / `0` (off) on the track's channel; Solo = CC 24
**always sent on channel 1**, value = track 1–11, `0` = solo off. 🟡 (official CCs; mixer listed as
working, not explicitly re-verified). Used by bridge: `protocol.py:mute_track_cc` / `solo_track_cc` ←
`app.py:_toggle_track_mute`, `_toggle_track_mute_simple`, `_toggle_track_solo`, `_toggle_drum_bus_mute`
(DRUM bus = mute CC on channels 1–7). The bridge can't read mute/solo back, so its LEDs don't follow
changes made on the Seqtrak (the readable SysEx equivalents are `30 5p 29` and `30 40 68`).

---

## Transport (MIDI Realtime)

| Message | Hex | Function |
|---------|-----|----------|
| Start | FA | Start playback from beginning |
| Stop | FC | Stop playback |
| Continue | FB | Continue from current position |
| Clock | F8 | MIDI clock tick (24 ppqn) |

---

## Sound Selection (Standard MIDI)

Sound/preset changes use standard Bank Select + Program Change:

```
Bank Select MSB (CC 0): [bank_msb]
Bank Select LSB (CC 32): [bank_lsb]
Program Change: [program]
```

Send on the appropriate channel (1-11) for the target track.

**Bank values (official, `midi-data-table.md`) and bridge use (from code):**
| Target | Bank MSB | Bank LSB | Program | Channel | Status / used by bridge |
|---|---|---|---|---|---|
| Drum / Synth / DX sound | 63 (`3F`) | 0–31 preset, 32–47 user | 0–127 | track 1–10 | ✅ (official + "Preset select ✅" in `FUNCTIONALITY-MAP.md`). `app.py:_cycle_patch` (patch encoder CC 73; Shift = jump 128) |
| SAMPLER element (pad) sound | 62 (`3E`) | 0–3 preset, 4–11 user | 0–127 (72–127 reserved) | **channel = element number** (official) | 🟡 Bridge sends on MIDI channels **1–7** for pads 1–7 (mido channel 0–6), *not* channel 11. `app.py:_cycle_sampler_pad_preset` (19e7dbd, 2025-12-24). Not verified on hardware — worth testing, since channels 1–7 are also the drum tracks |
| Project | 64 (`40`) | 0 | 0–8 (8 = temporary) | ignored | Not used by the bridge |

The bridge also **listens** for CC 0 / CC 32 / Program Change from the Seqtrak on channels 1–11
(`app.py:handle_seqtrak_message`) and shows the looked-up preset name when it's the selected track. The
name the Seqtrak itself reports (`01 1p 35`, Part 3) overrides this lookup.

---

## Notes (bridge use, from code)

| What | Channel | Note | Status | Used by bridge |
|---|---|---|---|---|
| Drum pads | track 1–7 | 60 (`3C`, C4); the 8th pad = PERC 2 at note 67 | 🟡 | `protocol.py:trigger_note` / `release_note` ← `app.py:_handle_drum_pad`, note repeat `app.py:_process_note_repeat` |
| Melodic keyboard | 8–10 (SYNTH 1, SYNTH 2, DX) | from the isomorphic layout | 🟡 | `protocol.py:trigger_note` ← `app.py:_handle_melodic_pad`, arpeggiator `app.py:_process_arpeggiator` (bridge-side arp, not the Seqtrak's) |
| Sampler pads 1–7 | 11 | 60–66 (`3C`–`42`) = pad 1–7 | 🟡 (same note mapping as sampler step data, ✅ there) | `app.py:_handle_sampler_pad` (direct `note_on`/`note_off`) |

Note off is sent as `8n` with velocity 0. With Accent on, the bridge replaces the velocity with a fixed accent value.

---

# PART 2: Effect Preset Reference

## Master Effect Presets

### Filter (8 presets)
| No. | Name | Param 1 | Param 2 | Param 3 |
|-----|------|---------|---------|---------|
| 1-4 | LPF (No/Low/Mid/High Res) | Cutoff | Resonance | Output Level |
| 5-8 | HPF (No/Low/Mid/High Res) | Cutoff | Resonance | Output Level |

### Reverb (8 presets)
| No. | Name | Type | Param 1 | Param 2 | Param 3 |
|-----|------|------|---------|---------|---------|
| 1-3 | Small Room 1/2, Mid Room | SPX Room | Dry/Wet | Reverb Time | LPF Cutoff |
| 4-5 | Small Hall, Mid Hall | SPX Hall | Dry/Wet | Reverb Time | LPF Cutoff |
| 6 | Stage | SPX Stage | Dry/Wet | Reverb Time | LPF Cutoff |
| 7 | Gated Reverb | Gated | Dry/Wet | Room Size | LPF Cutoff |
| 8 | Reverse Reverb | Reverse | Dry/Wet | Room Size | LPF Cutoff |

### Delay (8 presets)
| No. | Name | Type | Param 1 | Param 2 | Param 3 |
|-----|------|------|---------|---------|---------|
| 1 | Tempo Delay 4th | Stereo | Dry/Wet | Delay Time | Feedback |
| 2 | Ping Pong 4th | Cross | Dry/Wet | Time L>R/R>L | Feedback |
| 3 | Tempo Delay 8th Dot | Stereo | Dry/Wet | Delay Time | Feedback |
| 4 | Tempo Delay 8th | Stereo | Dry/Wet | Delay Time | Feedback |
| 5 | Ping Pong 8th | Cross | Dry/Wet | Time L>R/R>L | Feedback |
| 6 | Tempo Delay 16th | Stereo | Dry/Wet | Delay Time | Feedback |
| 7 | Analog Delay Modern | Analog | Dry/Wet | Delay Time | Feedback |
| 8 | Analog Delay Retro | Analog | Dry/Wet | Delay Time | Feedback |

### Compressor (8 presets)
| No. | Name | Param 1 | Param 2 | Param 3 |
|-----|------|---------|---------|---------|
| 1-8 | Comp Setting 1-8 | Ratio | Threshold | Make Up Gain |

### Distortion (8 presets)
| No. | Name | Type | Param 1 | Param 2 | Param 3 |
|-----|------|------|---------|---------|---------|
| 1 | Wave Folder Saturation | Wave Folder | Dry/Wet | Fold | Input Level |
| 2 | Comp Distortion | Comp Dist | Dry/Wet | Overdrive | LPF Cutoff |
| 3 | Wave Folder | Wave Folder | Dry/Wet | Fold | Input Level |
| 4,6 | Amp Simulator 2 | Amp Sim 2 | Dry/Wet | Overdrive | LPF Cutoff |
| 5 | Amp Simulator 1 | Amp Sim 1 | Dry/Wet | Overdrive | Presence |
| 7 | Bit Crusher | Bit Crush | Sample Rate | Bit | Dry/Wet |
| 8 | Digital Turntable | Turntable | Noise Level | Click Level | Dry Send |

### Modulation (8 presets)
| No. | Name | Type | Param 1 | Param 2 | Param 3 |
|-----|------|------|---------|---------|---------|
| 1 | SPX Chorus | Chorus | Dry/Wet | LFO Speed | LFO Depth |
| 2 | Tempo Flanger | Flanger | Dry/Wet | LFO Speed | LFO Depth |
| 3 | Tempo Phaser | Phaser | LFO Depth | LFO Speed | Feedback |
| 4 | Ensemble Detune | Detune | Dry/Wet | Detune | Spread |
| 5 | Auto Pan | Auto Pan | L/R Depth | LFO Speed | LFO Wave |
| 6 | Tremolo | Tremolo | AM Depth | LFO Speed | PM Depth |
| 7 | VCM Auto Wah | Auto Wah | Speed | Resonance | Output |
| 8 | Ring Modulator | Ring Mod | Dry/Wet | OSC Freq | LFO Depth |

### Ducker (8 presets)
| No. | Name | Param 1 | Param 2 | Param 3 |
|-----|------|---------|---------|---------|
| 1-8 | Ducker Setting 1-8 | Side Chain Level | Attack | Release |

### Other (8 presets)
| No. | Name | Type | Param 1 | Param 2 | Param 3 |
|-----|------|------|---------|---------|---------|
| 1 | Beat Repeat | Beat Repeat | Repeat/Length | Gate Time | Play Speed |
| 2 | Talking Modulator | Talk Mod | Vowel | Move Speed | Drive |
| 3 | Rotary Speaker Slow | Rotary 1 | Speed | Rotor/Horn | Mic Angle |
| 4 | Rotary Speaker Fast | Rotary 2 | Speed | Rotor/Horn | Mod Depth |
| 5 | Harmonic Enhancer | Enhancer | Mix Level | Drive | HPF Cutoff |
| 6 | Auto Synth | Auto Synth | Mod Depth | AM Depth | Delay Level |
| 7 | Slice | Slice | Dry/Wet | Gate Time | Divide Type |
| 8 | Vinyl Break | Vinyl | Break | Speed | Speed Adjust |

---

## Single Effect Presets

Single effects use the same preset types as Master Effects (Filter, Reverb, Delay, Compressor, Distortion, Modulation, Ducker, Other) with 8 presets each.

Notable differences in Single Effect Distortion:
| No. | Name | Notes |
|-----|------|-------|
| 4 | Jazz Combo | Distortion/Depth/Treble |
| 6 | Small Stereo | Drive/Tone/Presence |

---

## Send Effect Presets

### Send Reverb (8 presets)
| No. | Name | Type | Param 1 | Param 2 | Param 3 |
|-----|------|------|---------|---------|---------|
| 1 | HD Room | HD Room | Reverb Time | Room Size | High Damp |
| 2 | R3 Room | R3 Room | Reverb Time | Diffusion | LPF Cutoff |
| 3 | R3 Hall | R3 Hall | Reverb Time | Diffusion | LPF Cutoff |
| 4 | HD Hall | HD Hall | Reverb Time | Room Size | High Damp |
| 5 | R3 Plate | R3 Plate | Reverb Time | Diffusion | LPF Cutoff |
| 6 | HD Plate | HD Plate | Reverb Time | Plate Type | High Damp |
| 7 | SPX Stage | SPX Stage | Reverb Time | Diffusion | LPF Cutoff |
| 8 | REV X Hall | REV X | Reverb Time | Room Size | LPF Cutoff |

### Send Delay (8 presets)
| No. | Name | Type | Param 1 | Param 2 | Param 3 |
|-----|------|------|---------|---------|---------|
| 1 | Tempo Delay 4th | Stereo | Delay Time | Feedback | High Damp |
| 2 | Ping Pong 4th | Cross | Time L>R/R>L | Feedback | High Damp |
| 3 | Tempo Delay 8th Dot | Stereo | Delay Time | Feedback | High Damp |
| 4 | Tempo Delay 8th | Stereo | Delay Time | Feedback | High Damp |
| 5 | Ping Pong 8th | Cross | Time L>R/R>L | Feedback | High Damp |
| 6 | Tempo Delay 16th | Stereo | Delay Time | Feedback | High Damp |
| 7 | Analog Delay Modern | Analog | Delay Time | Feedback | Input Level |
| 8 | Analog Delay Retro | Analog | Delay Time | Feedback | Input Level |

---

## Effect Block Diagram

*Source: SEQTRAK_data_list_Effects.pdf*

The Seqtrak effect chain flows through three stages:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TRACK EFFECT (per-track)                                                     │
│                                                                              │
│  TONE GENERATOR ──► SINGLE EFFECT ──► LP-HP FILTER ──► 2 BAND EQ ──► TRACK  │
│  (Drum/Synth/DX/                                                    OUTPUT  │
│   Sampler)                                                     ↓            │
│                                                          EFFECT SENDS       │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ SEND EFFECT                                                                  │
│                                                                              │
│  EFFECT SENDS ──┬──► SEND LEVEL DELAY ──► DELAY ──────► DELAY RETURNS       │
│                 │                                              │             │
│                 └──► SEND LEVEL REVERB ──► REVERB ──► REVERB RETURNS        │
│                                             │              │                 │
│                                        RETURN LEVEL   RETURN LEVEL          │
└─────────────────────────────────────────────────────────────────────────────┘
                                        │
                                        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ MASTER EFFECT                                                                │
│                                                                              │
│  TRACK OUTPUTS ──┐                                                          │
│  DELAY RETURNS ──┼──► MASTER ──► HIGH PASS ──► REPEATER ──► COMPRESSOR ──►  │
│  REVERB RETURNS ─┤   (MASTER1)   (MASTER2)    (MASTER3)     (MASTER4)       │
│  MIC/LINE INPUT ─┤                                               │          │
│  USB INPUT ──────┘                                          5 BAND EQ ──►   │
│                                                                  │          │
│                                                            MASTER VOLUME    │
│                                                                  │          │
│                                                               OUTPUT        │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Signal Flow Summary:**
- **Track Effect**: Per-track processing (Single FX → LP-HP Filter → 2-Band EQ)
- **Send Effect**: Shared reverb and delay with adjustable send/return levels
- **Master Effect**: 4-stage master chain plus 5-band EQ and master volume

---

## Effect Type Reference

*Source: SEQTRAK_data_list_Effects.pdf*

Effect types are selected using MSB/LSB hex values. The assignability columns show where each effect can be used.

### REVERB

| Type Name | MSB | LSB | Description | Single | Send | M1 | M2 | M3 | M4 |
|-----------|-----|-----|-------------|--------|------|----|----|----|-----|
| No Effect/Thru | 00 | 00 | Bypass | ✓ | ✓ | | | | |
| SPX HALL | 01 | 02 | Concert hall (SPX1000) | ✓ | ✓ | ✓ | ✓ | ✓ | |
| SPX ROOM | 01 | 12 | Room reverb (SPX1000) | ✓ | ✓ | ✓ | | | |
| SPX STAGE | 01 | 30 | Solo instrument reverb | ✓ | ✓ | ✓ | | | |
| EARLY REFLECTION | 0D | 50 | Early reflections only | ✓ | | ✓ | | | |
| GATED REVERB | 01 | 50 | Gated reverb simulation | ✓ | | ✓ | | | |
| REVERSE REVERB | 01 | 58 | Reverse playback reverb | ✓ | | ✓ | | | |
| HD HALL | 01 | 03 | High-definition hall | | ✓ | | | | |
| HD ROOM | 01 | 13 | High-definition room | | ✓ | | | | |
| HD PLATE | 01 | 21 | Metal plate reverb | | ✓ | | | | |
| REV-X HALL | 01 | 00 | REV-X technology hall | | ✓ | | | | |
| REV-X ROOM | 01 | 10 | REV-X technology room | | ✓ | | | | |
| R3 HALL | 01 | 01 | ProR3 algorithm hall | | ✓ | | | | |
| R3 ROOM | 01 | 11 | ProR3 algorithm room | | ✓ | | | | |
| R3 PLATE | 01 | 20 | ProR3 plate reverb | | ✓ | | | | |
| SPACE SIMULATOR | 01 | 40 | Configurable space (W/H/D) | | ✓ | | | | |

### DELAY

| Type Name | MSB | LSB | Description | Single | Send | M1 | M2 | M3 | M4 |
|-----------|-----|-----|-------------|--------|------|----|----|----|-----|
| CROSS DELAY | 02 | 00 | Crossed feedback stereo | ✓ | ✓ | ✓ | | | |
| TEMPO CROSS DELAY | 02 | 10 | Tempo-synced cross delay | ✓ | ✓ | ✓ | ✓ | | ✓ |
| TEMPO DELAY MONO | 02 | 20 | Tempo-synced mono | ✓ | ✓ | ✓ | | | |
| TEMPO DELAY STEREO | 02 | 28 | Tempo-synced stereo | ✓ | ✓ | ✓ | | | |
| CONTROL DELAY | 02 | 30 | Real-time controllable | ✓ | ✓ | ✓ | | | |
| DELAY LR | 02 | 40 | Stereo L/R delay | ✓ | ✓ | ✓ | | | |
| DELAY LCR | 02 | 50 | Three-tap L/C/R delay | ✓ | ✓ | ✓ | | | |
| ANALOG DELAY RETRO | 02 | 60 | BBD short delay (25-800ms) | ✓ | ✓ | ✓ | ✓ | | ✓ |
| ANALOG DELAY MODERN | 02 | 68 | BBD long delay (50ms-1s) | ✓ | ✓ | ✓ | | | |

### FILTER

| Type Name | MSB | LSB | Description | Single | Send | M1 | M2 | M3 | M4 |
|-----------|-----|-----|-------------|--------|------|----|----|----|-----|
| CONTROL FILTER | 0C | 28 | Manual filter control | ✓ | | ✓ | ✓ | | ✓ |
| VCM MINI FILTER | 0D | 29 | Analog synth character | ✓ | | ✓ | ✓ | | |
| LP-HP FILTER | 0D | 2F | LPF 24dB/HPF 24dB combo | ✓ | | ✓ | | | |

### COMPRESSOR / DUCKER

| Type Name | MSB | LSB | Description | SC | Single | Send | M1 | M2 | M3 | M4 |
|-----------|-----|-----|-------------|-----|--------|------|----|----|----|-----|
| VCM COMPRESSOR 376 | 08 | 00 | Analog studio compressor | | ✓ | ✓ | | | | ✓ |
| CLASSIC COMPRESSOR | 08 | 10 | Conventional compressor | | ✓ | ✓ | | ✓ | | ✓ |
| MULTI BAND COMP | 08 | 20 | 3-band compressor | | ✓ | ✓ | | ✓ | | ✓ |
| UNI COMP DOWN | 08 | 30 | Downward compression | | ✓ | ✓ | | ✓ | | ✓ |
| UNI COMP UP | 08 | 38 | Upward compression | | ✓ | ✓ | | ✓ | | ✓ |
| PARALLEL COMP | 08 | 40 | Parallel processing | | ✓ | | ✓ | | | ✓ |

*SC = Side Chain capable when used as Ducker*

### DISTORTION

| Type Name | MSB | LSB | Description | Single | Send | M1 | M2 | M3 | M4 |
|-----------|-----|-----|-------------|--------|------|----|----|----|-----|
| AMP SIMULATOR 1 | 07 | 00 | Guitar amp (5 devices) | ✓ | ✓ | | | | |
| AMP SIMULATOR 2 | 07 | 10 | Guitar amp (6 types) | ✓ | ✓ | | | | |
| COMP DISTORTION | 07 | 20 | Comp + distortion | ✓ | ✓ | | | | |
| COMP DISTORTION DELAY | 07 | 30 | Comp + dist + delay | ✓ | ✓ | | | | |
| US COMBO | 07 | 40 | American combo amp | ✓ | ✓ | | | | |
| JAZZ COMBO | 07 | 41 | Jazz combo amp | ✓ | ✓ | | | | |
| US HIGH GAIN | 07 | 42 | American high gain | ✓ | ✓ | | | | |
| BRITISH LEAD | 07 | 43 | British stack amp | ✓ | ✓ | | | | |
| MULTI FX | 07 | 44 | Multi-effect guitar | ✓ | ✓ | | | | |
| SMALL STEREO | 07 | 45 | Stereo distortion | ✓ | ✓ | | | | |
| BRITISH COMBO | 07 | 46 | British combo amp | ✓ | ✓ | | | | |
| BRITISH LEGEND | 07 | 47 | British stack amp | ✓ | ✓ | | | | |
| LO-FI | 0B | 00 | Degrade audio quality | ✓ | ✓ | | | | |
| NOISY | 0B | 10 | Add noise to sound | ✓ | ✓ | | | | |
| DIGITAL TURNTABLE | 0B | 20 | Analog record noise | ✓ | ✓ | | | | |
| BIT CRUSHER | 0B | 30 | Bit/sample rate reduction | ✓ | ✓ | ✓ | ✓ | | |
| WAVE FOLDER | 0D | 28 | Harmonic wave folding | ✓ | ✓ | | | | |

### MODULATION

| Type Name | MSB | LSB | Description | SC | Single | Send | M1 | M2 | M3 | M4 |
|-----------|-----|-----|-------------|-----|--------|------|----|----|----|-----|
| G CHORUS | 03 | 00 | Rich chorus modulation | | ✓ | ✓ | | | | |
| 2 MODULATOR | 03 | 10 | Pitch + amplitude mod | | ✓ | ✓ | | | | |
| SPX CHORUS | 03 | 20 | 3-phase LFO chorus | | ✓ | ✓ | | | | |
| SYMPHONIC | 03 | 30 | 3-phase complex LFO | | ✓ | ✓ | | | | |
| ENSEMBLE DETUNE | 03 | 40 | Detune without mod | | ✓ | ✓ | | | | |
| VCM FLANGER | 04 | 00 | 1970s analog flanger | | ✓ | ✓ | | | | |
| CLASSIC FLANGER | 04 | 10 | Conventional flanger | | ✓ | ✓ | | | | |
| TEMPO FLANGER | 04 | 20 | Tempo-synced flanger | | ✓ | ✓ | ✓ | ✓ | | |
| DYNAMIC FLANGER | 04 | 30 | Dynamic control flanger | ✓ | ✓ | ✓ | | | | |
| CONTROL FLANGER | 04 | 08 | Manual flanger | | ✓ | ✓ | | | | |
| VCM PHASER MONO | 05 | 00 | 1970s mono phaser | | ✓ | ✓ | | | | |
| VCM PHASER STEREO | 05 | 10 | 1970s stereo phaser | | ✓ | ✓ | | | | |
| TEMPO PHASER | 05 | 20 | Tempo-synced phaser | | ✓ | ✓ | ✓ | ✓ | | |
| DYNAMIC PHASER | 05 | 30 | Dynamic phase shifter | ✓ | ✓ | ✓ | | | | |
| CONTROL PHASER | 05 | 18 | Manual phaser | | ✓ | ✓ | | | | |
| AUTO PAN | 06 | 00 | Cyclic L/R panning | | ✓ | ✓ | | | | |
| TREMOLO | 06 | 10 | Volume modulation | | ✓ | ✓ | | | | |
| VCM AUTO WAH | 0A | 00 | LFO wah modulation | | ✓ | ✓ | | | | |
| VCM TOUCH WAH | 0A | 10 | Amplitude wah | | ✓ | ✓ | | | | |
| VCM PEDAL WAH | 0A | 20 | Pedal-controlled wah | | ✓ | ✓ | | | | |
| RING MODULATOR | 0C | 00 | Pitch AM modulation | | ✓ | ✓ | | | | |
| DYNAMIC RING MOD | 0C | 10 | Dynamic ring modulator | ✓ | ✓ | ✓ | | | | |
| SPIRALIZER P | 0C | 38 | Endless pitch phaser | | ✓ | ✓ | | | | |
| TEMPO SPIRALIZER P | 0C | 39 | Tempo-synced spiralizer | | ✓ | ✓ | | | | |
| SPIRALIZER F | 0C | 3A | Endless pitch flanger | | ✓ | ✓ | | | | |
| TEMPO SPIRALIZER F | 0C | 3B | Tempo-synced flanger | | ✓ | ✓ | | | | |
| TECH MODULATION | 0C | 60 | Ring mod-like modulation | | ✓ | ✓ | | | | |

*SC = Side Chain capable*

### OTHER

| Type Name | MSB | LSB | Description | SC | Single | Send | M1 | M2 | M3 | M4 |
|-----------|-----|-----|-------------|-----|--------|------|----|----|----|-----|
| ROTARY SPEAKER 1 | 06 | 20 | Basic rotary sim | | ✓ | ✓ | | | | |
| ROTARY SPEAKER 2 | 06 | 30 | Rotary with amp block | | ✓ | ✓ | | | | |
| DYNAMIC FILTER | 0C | 20 | Dynamic filter control | ✓ | ✓ | ✓ | | | | |
| AUTO SYNTH | 0C | 30 | Synth-type processing | | ✓ | ✓ | | | | |
| ISOLATOR | 0C | 40 | Frequency band control | | ✓ | ✓ | | | | |
| SLICE | 0C | 50 | Amplitude EG slicing | | ✓ | ✓ | | | | |
| VINYL BREAK | 0C | 70 | Turntable slowdown | | ✓ | ✓ | ✓ | ✓ | | |
| BEAT REPEAT | 0C | 7C | Mechanical beat repeat | | ✓ | ✓ | ✓ | ✓ | | |
| VCM EQ 501 | 0D | 00 | 1970s analog EQ | | ✓ | ✓ | | | | |
| PRESENCE | 0D | 08 | Presence enhancer | | ✓ | ✓ | | | | |
| HARMONIC ENHANCER | 0D | 10 | Harmonic layering | | ✓ | ✓ | | | | |
| STEREOPHONIC OPTIMIZER | 0D | 18 | Stereo spacing/distance | | ✓ | ✓ | | | | |
| TALKING MODULATOR | 0D | 20 | Vowel sound addition | | ✓ | ✓ | | | | |
| VCM MINI BOOSTER | 0D | 2A | Analog synth texture | | ✓ | ✓ | | | | |
| DAMPER RESONANCE | 0D | 30 | Piano damper pedal sim | | ✓ | ✓ | | | | |
| PITCH CHANGE | 0D | 40 | Pitch shifting | | ✓ | ✓ | | | | |
| NOISE GATE+COMP+EQ | 0D | 70 | Vocal processing chain | | ✓ | ✓ | | | | |

*SC = Side Chain capable*

---

## Arpeggio Presets Reference

*Source: SEQTRAK_data_list_Core.pdf*

Arpeggiator presets available for Synth/DX tracks (controlled via CC 27 on channels 8-10):

| No. | Preset Name | Type | Mode | Octave |
|-----|-------------|------|------|--------|
| 1 | Off | - | - | - |
| 2 | Up | Up | Sort | 0 |
| 3 | Up 2Octave | Up | Sort | +1 |
| 4 | Down | Down | Sort | 0 |
| 5 | Down 2Octave | Down | Sort | +1 |
| 6 | Random | Random | Sort | 0 |
| 7 | Random 2Octave | Random | Sort | +1 |
| 8 | Up / Down A | Up Down 1 | Sort | 0 |
| 9 | Up / Down A 2Octave | Up Down 1 | Sort | +1 |
| 10 | Up / Down B | Up Down 2 | Sort | 0 |
| 11 | Up / Down B 2Octave | Up Down 2 | Sort | +1 |
| 12 | Thumb Up | Slap & Pop | Sort | 0 |
| 13 | Unison | Unison | Sort | 0 |
| 14 | Chord 1 | Rhythm 1 | Sort | 0 |
| 15 | Chord 2 | Rhythm 2 | Sort | 0 |
| 16 | As Played | Up | Thru | 0 |

**Mode Types:**
- **Sort**: Notes are sorted before arpeggiation (lowest to highest)
- **Thru**: Notes are played in the order they were pressed

**Octave Values:**
- **0**: Play notes in the original octave only
- **+1**: Extend the arpeggio pattern over 2 octaves

---

## DX Algorithm Chart

*Source: SEQTRAK_data_list_Core.pdf*

The DX track uses 4-operator FM synthesis with 12 algorithm configurations. Operators are numbered 1-4.

**Legend:**
- **■ (Square)** = CARRIER (produces audible output)
- **● (Circle)** = MODULATOR (modulates other operators)

```
Algorithm 1:                Algorithm 2:                Algorithm 3:
■1 → ■2 → ■3 → ■4          ■1 → ■2 ──┐                 ●2 → ●3
(all in series)                      ↓                    ↘
                           ●4 → ●3 ──┴→ OUT          ●1 → ■4
                                                         ↓
                                                        OUT

Algorithm 4:                Algorithm 5:                Algorithm 6:
    ●2                          ●2                      ●1
   ↗   ↘                       ↓                        ↓
●1      ■4                 ■1 → ●3                  ■2  ■3  ■4
   ↘   ↗                        ↓                    ↘  ↓  ↙
    ●3                          ■4                    OUT
     ↓
    OUT

Algorithm 7:                Algorithm 8:                Algorithm 9:
●1                          ●1 → ●2                     ●1
 ↓                              ↓                        ↓
●2 → ●3 → ■4                ●3 → ■4                     ●2    ■4
              ↓                  ↓                        ↓   ↙
             OUT                OUT                      ●3
                                                          ↓
                                                         OUT

Algorithm 10:               Algorithm 11:               Algorithm 12:
●1                          ●1                          ■1
 ↓                           ↓                          ■2
●2                          ●2                          ■3
 ↓                           ↓                          ■4
●3 → ■4                     ●3 → ■4                      ↓
      ↓                          ↓                      OUT
     OUT                        OUT                 (all parallel)
```

**Algorithm Characteristics:**
- **Algorithm 1**: Maximum modulation depth (all operators in series)
- **Algorithm 6**: 3 carriers with 1 modulator (rich harmonic output)
- **Algorithm 8**: 2 parallel stacks (good for layered sounds)
- **Algorithm 12**: All carriers, no modulation (additive synthesis)

**FM Control CCs (Channel 10 only):**
| Parameter | CC | Range | Description |
|-----------|-----|-------|-------------|
| FM Algorithm | 116 | 0-127 | Selects algorithm 1-12 |
| FM Mod Amount | 117 | 0-127 | Modulator output level |
| FM Mod Frequency | 118 | 0-127 | Modulator frequency ratio |
| FM Mod Feedback | 119 | 0-127 | Operator self-feedback |

---

## MIDI Implementation Chart Reference

*Source: SEQTRAK_data_list_Core.pdf - MIDI Implementation Chart v1.0 (26-SEP-2023)*

### Basic Channel
| Function | Transmitted | Recognized | Notes |
|----------|-------------|------------|-------|
| Default | 1-11 | 1-11 | One channel per track |
| Changed | X | X | Fixed assignment |

### Mode
| Function | Transmitted | Recognized | Notes |
|----------|-------------|------------|-------|
| Default | X | 3 | Mode 3 = OMNI OFF, POLY |
| Messages | X | 3, 4 (m=1) | m always treated as 1 |

### Note Number
| Function | Transmitted | Recognized | Notes |
|----------|-------------|------------|-------|
| Range | 0-127 | 0-127 | Full MIDI range |

### Velocity
| Function | Transmitted | Recognized | Notes |
|----------|-------------|------------|-------|
| Note ON | O (9nH, v=1-127) | O (9nH, v=1-127) | |
| Note OFF | X (8nH, v=0) | X (9nH, v=0 or 8nH) | |

### Control Change Summary

| CC | Transmitted | Recognized | Description |
|----|-------------|------------|-------------|
| 0, 32 | O | O | Bank Select MSB/LSB |
| 5 | O | O | Portamento Time |
| 7, 10 | O | O | Channel Volume, Pan |
| 6, 38 | X | O | Data Entry MSB/LSB |
| 11 | X | O | Expression |
| 20, 21, 25-29 | O | O | Model-Specific |
| 23, 24 | X | O | Model-Specific (Mute/Solo) |
| 64 | X | O | Sustain Switch |
| 65 | O | O | Portamento Switch |
| 66 | X | O | Sostenuto |
| 71, 73-75 | O | O | Sound Control |
| 91, 94 | O | O | Reverb/Delay Send |
| 96, 97 | X | O | RPN Inc/Dec |
| 100, 101 | X | O | RPN LSB/MSB |
| 102-119 | O | O | Model-Specific |
| 126, 127 | X | O | Mono On, Poly On |

### Other Messages

| Function | Transmitted | Recognized | Notes |
|----------|-------------|------------|-------|
| Program Change | O (0-127) * | O (0-127) * | *If switch is on |
| System Exclusive | O * | O | *If switch is on |
| Clock | O ** | O *** | **If clock out on, ***If MIDI sync Auto |
| Start/Stop/Continue | O * | O | *If switch is on |
| All Sound Off | X | O (120) | |
| Reset All Controllers | X | O (121) | |
| All Notes Off | X | O (123-125) | |
| Active Sense | O | O | |

---

## Sound Design Parameters by Track Type

*Source: SEQTRAK_data_list_Sound_Design_Parameter_List.pdf*

Each track type has a set of sound design parameters organized into pages. The "Parameter Scope" indicates whether the parameter affects the entire Track, the Sound (patch), or individual Elements/Samples.

### Drum Sound Design (Tracks 1-7)

| Page | Parameter | Display | Scope | CC | Notes |
|------|-----------|---------|-------|-----|-------|
| 1 | Sound Select | SOUND | - | CC 0/32 + PC | Bank Select + Program Change |
| 1 | Pitch | PITCH | Sound | CC 25 | Note Shift |
| 1 | Pan | PAN | Track | CC 10 | Track Pan |
| 1 | Volume | VOLUME | Track/Note | CC 7 | Track Volume (Note Velocity for P-Lock) |
| 2 | AEG Attack | ATTACK | Sound | CC 73 | AEG Attack Time |
| 2 | AEG Decay | DECAY | Sound | CC 75 | AEG Decay Time |
| 2 | LP-HP Filter Cutoff | FILTER | Sound | CC 74 | LPF/HPF Cutoff Frequency |
| 2 | LP-HP Filter Resonance | RESONANCE | Sound | CC 71 | LPF/HPF Resonance |
| 3 | Reverb Send | REVERB | Sound | CC 91 | Reverb Send |
| 3 | Delay Send | DELAY | Sound | CC 94 | Variation Send |
| 3 | EQ High Gain | OTHER | Sound | CC 20 | 2-Band EQ High Gain |
| 3 | EQ Low Gain | OTHER | Sound | CC 21 | 2-Band EQ Low Gain |

### Synth Sound Design (Tracks 8-9)

| Page | Parameter | Display | Scope | CC | Notes |
|------|-----------|---------|-------|-----|-------|
| 1 | Sound Select | SOUND | - | CC 0/32 + PC | Bank Select + Program Change |
| 1 | Mono/Poly/Chord | MONO/POLY/CHORD | Sound | CC 26 | Mono/Poly Mode, Chordset Select |
| 1 | Pan | PAN | Track | CC 10 | Track Pan |
| 1 | Volume | VOLUME | Track | CC 7 | Track Volume |
| 2 | AEG Attack | ATTACK | Sound | CC 73 | AEG Attack Time |
| 2 | AEG Decay/Release | DECAY | Sound | CC 75 | AEG Decay/Release Offset |
| 2 | LP-HP Filter Cutoff | FILTER | Sound | CC 74 | LPF/HPF Cutoff Frequency |
| 2 | LP-HP Filter Resonance | RESONANCE | Sound | CC 71 | LPF/HPF Resonance |
| 3 | Reverb Send | REVERB | Sound | CC 91 | Reverb Send |
| 3 | Delay Send | DELAY | Sound | CC 94 | Variation Send |
| 3 | EQ High Gain | OTHER | Sound | CC 20 | 2-Band EQ High Gain |
| 3 | EQ Low Gain | OTHER | Sound | CC 21 | 2-Band EQ Low Gain |
| 4 | Portamento Time | OTHER | Sound | CC 5 | Portamento Time/Switch |
| 4 | Arpeggiator Type | OTHER | Sound | CC 27 | Arpeggiator Preset/Switch |
| 4 | Arpeggiator Gate Time | OTHER | Sound | CC 28 | Arpeggiator Gate Time Rate |
| 4 | Arpeggiator Speed | OTHER | Sound | CC 29 | Arpeggiator Unit |

### DX Sound Design (Track 10)

| Page | Parameter | Display | Scope | CC | Notes |
|------|-----------|---------|-------|-----|-------|
| 1 | Sound Select | SOUND | - | CC 0/32 + PC | Bank Select + Program Change |
| 1 | Mono/Poly/Chord | MONO/POLY/CHORD | Sound | CC 26 | Mono/Poly Mode, Chordset Select |
| 1 | Pan | PAN | Track | CC 10 | Track Pan |
| 1 | Volume | VOLUME | Track | CC 7 | Track Volume |
| 2 | AEG Attack | ATTACK | Sound | CC 73 | AEG Attack Time |
| 2 | AEG Decay/Release | DECAY | Sound | CC 75 | AEG Decay/Release Offset |
| 2 | LP-HP Filter Cutoff | FILTER | Sound | CC 74 | LPF/HPF Cutoff Frequency |
| 2 | LP-HP Filter Resonance | RESONANCE | Sound | CC 71 | LPF/HPF Resonance |
| 3 | Reverb Send | REVERB | Sound | CC 91 | Reverb Send |
| 3 | Delay Send | DELAY | Sound | CC 94 | Variation Send |
| 3 | EQ High Gain | OTHER | Sound | CC 20 | 2-Band EQ High Gain |
| 3 | EQ Low Gain | OTHER | Sound | CC 21 | 2-Band EQ Low Gain |
| 4 | Portamento Time | OTHER | Sound | CC 5 | Mono only |
| 4 | Arpeggiator Type | OTHER | Sound | CC 27 | Arpeggiator Preset/Switch |
| 4 | Arpeggiator Gate Time | OTHER | Sound | CC 28 | Arpeggiator Gate Time Rate |
| 4 | Arpeggiator Speed | OTHER | Sound | CC 29 | Arpeggiator Unit |
| 5 | FM Algorithm | OTHER | FM Operator | CC 116 | FM Algorithm (1-12) |
| 5 | Modulator Amount | OTHER | Sound | CC 117 | Mod Amount Offset |
| 5 | Modulator Frequency | OTHER | Sound | CC 118 | Freq Ratio Offset |
| 5 | Modulator Feedback | OTHER | Sound | CC 119 | Feedback Offset |

### SAMPLER Sound Design (Track 11)

| Page | Parameter | Display | Scope | CC | Notes |
|------|-----------|---------|-------|-----|-------|
| 1 | Sound Select | SOUND | - | - | Element Change |
| 1 | Pitch | PITCH | Element | - | Coarse Tune |
| 1 | Pan | PAN | Element | CC 10 | Pan |
| 1 | Volume | VOLUME | Element | CC 7 | Level (Note Velocity for P-Lock) |
| 2 | AEG Attack | ATTACK | Element | CC 73 | AEG Attack Time |
| 2 | AEG Decay | DECAY | Element | CC 75 | Release Time (Gate) / Decay 1/2 Time (Trigger) |
| 2 | LP-HP Filter Cutoff | FILTER | Sound | CC 74 | LPF/HPF Cutoff Frequency |
| 2 | LP-HP Filter Resonance | RESONANCE | Sound | CC 71 | LPF/HPF Resonance |
| 3 | Reverb Send | REVERB | Sound | CC 91 | Reverb Send |
| 3 | Delay Send | DELAY | Sound | CC 94 | Variation Send |
| 3 | EQ High Gain | OTHER | Sample | CC 20 | EQ2 Gain |
| 3 | EQ Low Gain | OTHER | Sample | CC 21 | EQ1 Gain |
| 4 | Start Point | OTHER | Sample | SysEx | Sample Start Point |
| 4 | End Point | OTHER | Sample | SysEx | Sample End Point |
| 4 | Loop On/Off | OTHER | Sample | SysEx | Sample Loop On/Off |
| 4 | Loop Length | OTHER | Sample | SysEx | Sample Loop Length |
| 5 | PEG Attack Level | OTHER | Sample | SysEx | Pitch EG Attack Level |
| 5 | PEG Attack Time | OTHER | Sample | SysEx | Pitch EG Attack Time |
| 5 | PEG Decay Level | OTHER | Sample | SysEx | PEG Decay1/Decay2/Release Level |
| 5 | PEG Decay Time | OTHER | Sample | SysEx | PEG Decay1 Time |

**Parameter Lock / Motion Recording:**
- Parameters marked with ✓ in the official documentation support Parameter Lock (per-step automation) and/or Motion Recording (real-time recording of parameter changes)
- Volume on Drum tracks uses Note Velocity for Parameter Lock
- Volume on Synth/DX tracks uses Note Velocity for P-Lock, Sound Volume for Motion Recording

---

# PART 3: SysEx Protocol (Reverse-Engineered)

Use SysEx for parameters not available via standard MIDI CC.

---

> **Read first (2026-10-11):** Yamaha's Data List "MIDI Data Table" (`reference files/Yamaha/Seqtrak
> Data List V2/md/32–36-*.md`) is the **official** map for every parameter address (`00`, `30`, `31`,
> `41`, `42`, `48`, `49`, `50` blocks). Several speculative labels below have been corrected against
> it. The `01 1x xx` UI/feedback range and `70/72/74` step data are **not** in Yamaha's docs — those
> remain reverse-engineered. Coverage tracking, capture findings and open questions:
> **`FUNCTIONALITY-MAP.md`**.

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

### Parameter Request (read any address) ✅
```
F0 43 30 7F 1C 0C [addr_h] [addr_m] [addr_l] F7      ← 3n = Parameter Request (n = device 0)
```
The Seqtrak answers with a normal Parameter Change (`F0 43 10 … [addr] [data] F7`) on the same address,
or with **no data bytes** when the slot is empty (step reads `70 4t ss`, note reads `75 g i`). Works for
official and undocumented ranges (`01 1x`, `70`, `75`) — verified 2026-10-11/12
(`REVERSE-ENGINEERING-LOG-2026-10.md` §1). Used by bridge: `protocol.py:request_parameter`, called from
`app.py:_request_seqtrak_state` (startup + project load: all 11 preset names `01 1p 35`, all 11
`30 5p 0F`, tempo, master volume, all 66 `30 5p 16–20` step counts, drum steps, sampler notes),
`app.py:_process_step_reads` (throttled to one request every 3 ms), `app.py:handle_encoder` (tempo
when unknown), `app.py:_read_note_list_blocking`.

---

## Transport Control

| Function | Address | Data | Notes |
|----------|---------|------|-------|
| Play State | `01 10 20` | 01=Playing, 00=Stopped | Feedback from device. ✅ Used by bridge: `app.py:handle_seqtrak_sysex` (transport LEDs, playhead start/stop) |
| Record State | `01 10 21` | 01=Recording, 00=Stopped | Feedback from device. ✅ Used by bridge: `app.py:handle_seqtrak_sysex` (record LED; on 01→00 re-reads all steps, since live-recorded notes are not reported) |
| Record (command) | `01 10 21` | 01=On, 00=Off | 🟡 The bridge **sends** this to start/stop recording — no separate command address is known. Used by bridge: `protocol.py:record` ← `app.py:handle_button` (Record) |
| Sample Record State | `01 10 22` | 01=Sampling, 00=Stopped | ✅ Feedback from device. Used by bridge: `app.py:handle_seqtrak_sysex` |
| Sample Record (command) | `01 10 22` | 01=On, 00=Off | 🟡 Sent by the bridge on Shift+Record, preceded by `01 10 28 [pad]` (sampler pad select). Used by bridge: `protocol.py:sample_record` ← `app.py:handle_button`. Added 2025-12-25 (d344a59), not explicitly verified |

**Note**: For controlling transport, use MIDI Realtime messages (FA=Start, FC=Stop, FB=Continue).

**Bridge use of realtime messages (from code):**
| Message | Direction | Status | Used by bridge |
|---|---|---|---|
| FA Start | bridge → Seqtrak | ✅ | `protocol.py:start` ← `app.py:handle_button` (Play), `app.py:_launch_session_row` (starts playback if stopped) |
| FC Stop | bridge → Seqtrak | ✅ | `protocol.py:stop` ← `app.py:handle_button` (Play toggle, Shift+Play, Stop), `app.py:run` (on exit) |
| FB Continue | bridge → Seqtrak | — | `protocol.py:continue_playback` exists but is never called |
| FA / FB / FC | Seqtrak → bridge | 🟡 | `app.py:handle_seqtrak_message` → playhead start / resume / stop (150927a, 2026-10-12). The bridge does **not** use F8 clock; the playhead is computed from tempo |

---

## Global Parameters

### Master Volume
| Address | Data | Notes |
|---------|------|-------|
| `00 00 00` | 00-7F | ✅ **Speaker Master Volume** (official), default `0x64` = 100 (corrected from code + midi-data-table, 2026-10-12; previously read "default 64"). Sent by the volume buttons, preceded by `01 10 2E 09` (volume display mode). Readable with a Parameter Request |
| `00 00 01` | 00-7F | **Headphone Master Volume** (official), default 32 (`0x20`) |

Step size per button press not yet confirmed (only 0–2 observed).

Used by bridge (09fd543, 2026-10-12; ✅ per `REVERSE-ENGINEERING-LOG-2026-10.md` §1 "Volume"):
write `protocol.py:set_master_volume` ← `app.py:handle_encoder` (Push master encoder CC 79);
read at startup `app.py:_request_seqtrak_state`; listen `app.py:handle_seqtrak_sysex` (shows a VOLUME popup
when the Seqtrak's own buttons change it).

### Tempo (BPM)
| Address | Data | Notes |
|---------|------|-------|
| `30 40 76` | [MSB] [LSB] | 2 bytes, 5-300 BPM. Example: `00 78` = 120 BPM |

✅ (official + working). Used by bridge: write `protocol.py:set_tempo` ← `app.py:handle_encoder` (tempo
encoder CC 14; the bridge clamps to 20–300) and `protocol.py:tap_tempo` (Tap Tempo button: the bridge
averages up to 4 taps itself and sends the BPM here — no device tap command is known); read at startup
`app.py:_request_seqtrak_state`; listen `app.py:handle_seqtrak_sysex`.

### Pattern Length
| Address | Data | Notes |
|---------|------|-------|
| `30 40 7A` | [MSB] [LSB] | 2 bytes, 1-128 steps. Official name **Pattern Master Step**. Not used by the bridge (it writes the per-variation counts `30 5p 16–20` instead) |

### Swing
| Address | Data | Notes |
|---------|------|-------|
| `30 40 7C` | [MSB] [LSB] | 2 bytes. Official name **Swing Offset**, −58…+58, default 0. Captured on project load as `01 00` = 0 (`FUNCTIONALITY-MAP.md`) |

**Corrected from code, 2025-12-24 (d107efd) + official table:** previously only "swing amount". The bridge
sends `01 [amount]` with amount `00–1C` (0–28, even numbers only) — i.e. 0…+28 above the `01 00` centre.
🟡 Not explicitly verified on hardware; ❓ how negative swing is encoded (presumably below `01 00`).
Used by bridge: `protocol.py:set_swing` ← `app.py:handle_encoder` (swing encoder CC 15). The bridge does
not read or listen for swing.

### Pattern Select Mode
| Address | Data | Notes |
|---------|------|-------|
| `30 40 79` | 00/01 | **Pattern Select Mode**: 0 = normal, 1 = advanced (official name; previously mislabeled "Loop Enable") |

### Scale Type (Global)

Official name: **Scale** = scale *slot* 1–8. Each slot's notes are user-definable at `30 4D xx`
(8 slots × 7 notes, MIDI note values, sent on project load). The names below may only be the
default slot contents — verify.

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

✅ Both directions. Used by bridge: send `protocol.py:select_track` ← `app.py:_send_track_select` (track
encoder CC 71, startup); listen `app.py:handle_seqtrak_sysex` (follows track changes made on the device,
then requests that track's preset name `01 1p 35`). The bridge ignores a `01 10 27` that arrives within
0.5 s of its own select, because the Seqtrak echoes it (4ffd6f7, 2026-10-11).

### Track Octave
Address format: `30 5[track] 0C`

| Track | Address | Data Range |
|-------|---------|------------|
| KICK | `30 50 0C` | 3D-42 (center=40) |
| SNARE | `30 51 0C` | 3D-42 |
| ... | ... | ... |
| SYNTH 1 | `30 57 0C` | 3D-42 |

Values: 3D=-3, 3E=-2, 3F=-1, 40=0, 41=+1, 42=+2

⚠️ Yamaha's official table (`midi-data-table.md`) gives **Octave −2…+2** (`3E`–`42`); `3D` (−3) is unverified.
Not used by the bridge (`protocol.py:set_track_octave` exists but is never called; Push octave buttons only
shift the pad layout).

### Per-Track Variation Selection
Address format: `30 5[track] 0F`

Selects the active variation for a specific track. Each track can have an independent variation (1-6).

| Track | Address | Data | Notes |
|-------|---------|------|-------|
| KICK | `30 50 0F` | 00-05 | Variation 1-6 |
| SNARE | `30 51 0F` | 00-05 | Variation 1-6 |
| CLAP | `30 52 0F` | 00-05 | Variation 1-6 |
| HAT1 | `30 53 0F` | 00-05 | Variation 1-6 |
| HAT2 | `30 54 0F` | 00-05 | Variation 1-6 |
| PERC1 | `30 55 0F` | 00-05 | Variation 1-6 |
| PERC2 | `30 56 0F` | 00-05 | Variation 1-6 |
| SYNTH1 | `30 57 0F` | 00-05 | Variation 1-6 |
| SYNTH2 | `30 58 0F` | 00-05 | Variation 1-6 |
| DX | `30 59 0F` | 00-05 | Variation 1-6 |
| SAMPLER | `30 5A 0F` | 00-05 | Variation 1-6 |

**Hardware behavior (captured 2026-10-11):**
- **Global variation change** (all tracks): Seqtrak sends `30 5p 0F vv` for all 11 tracks, then `01 10 2A vv`.
- **Per-track change**: `01 10 27 tt` (track select), then only that track's `30 5t 0F vv` — no `01 10 2A`.
- The bridge's `select_track_variation()` sends exactly this (`select_all_variations()` exists but is not called).
- **Corrected from code, 2026-10-11 (4ffd6f7):** the bridge now **listens** for `30 5p 0F` and `01 10 2A`
  (`app.py:handle_seqtrak_sysex`) and **reads** all 11 `30 5p 0F` at startup / project load
  (`app.py:_request_seqtrak_state`), so Seqtrak-side changes update the Push and trigger a step re-read.
  ✅ readable and reported on change (`REVERSE-ENGINEERING-LOG-2026-10.md` §1).
- Used by bridge (send): `app.py:_adjust_variation` (encoder CC 78 in track mode), `app.py:_launch_session_row`
  (session row launch → every track), `app.py:_delete_current_variation` / `_delete_all_variations_track` /
  `_delete_all_variations_song` (select each variation, clear it, then restore the previous one).

**Note**: Mute/Solo uses documented MIDI CC, not SysEx. See official Seqtrak MIDI spec:
- CC 23 = Mute (on any channel)
- CC 24 = Solo (on any channel)

Official SysEx equivalents: **Mute** `30 5p 29` (`00` off, `7D` on); **Solo Track** `30 40 68`
(`00` off, `01–0B` = track 1–11).

### Choke Group
| Address | Data | Notes |
|---------|------|-------|
| `30 5p 08` | 00-7F | **Group Number** (official): 0 = off, 1–127 = group. Seen for HAT1/HAT2/PERC1/PERC2 |

### Track Volume
Address format: `30 5[track] 00`

| Track | Address | Data |
|-------|---------|------|
| KICK | `30 50 00` | 00-7F (0-127) |
| ... | ... | ... |

### Track Pan
Address format: `30 5[track] 01`

| Track | Address | Data |
|-------|---------|------|
| KICK | `30 50 01` | 00-7F (0=L, 40=Center, 7F=R) |
| ... | ... | ... |

### Pattern Step Counts (per variation)
**Corrected 2026-10-11** — previously labeled "Track Filter/Cutoff (Speculative)". Official name:
**Pattern n Step**, 2 bytes, 1–128 (`1st bit6-0 → bit13-7, 2nd bit6-0 → bit6-0`), default `00 10` (16).

| Offset | Pattern |
|--------|---------|
| `30 5p 16` | Pattern 1 |
| `30 5p 18` | Pattern 2 |
| `30 5p 1A` | Pattern 3 |
| `30 5p 1C` | Pattern 4 |
| `30 5p 1E` | Pattern 5 |
| `30 5p 20` | Pattern 6 |

The observed values `00 10`, `00 20`, `00 40`, `01 00` = 16, 32, 64, 128 steps — explains the
"powers of 2" pattern.

Used by bridge: write `app.py:_adjust_bar_length` (encoder CC 75: cycles 16/32/64/128 steps on the
**current** variation's offset — corrected 150927a, 2026-10-12, it used to always write pattern 1); read
all 66 at startup `app.py:_request_seqtrak_state`; listen `app.py:handle_seqtrak_sysex` (playhead loop length).

---

## Pattern/Variation Control

### Global Variation Indicator
| Address | Data | Notes |
|---------|------|-------|
| `01 10 2A` | 00-05 | Global variation (read-only feedback from device) |

When Seqtrak's variation buttons are pressed (selecting all tracks at once), the device broadcasts this address as feedback. It indicates the "global" variation state when all tracks are synchronized.

**Note**: To set variation per-track programmatically, use `30 5[track] 0F` (see Track Parameters section above).

🟡 Used by bridge (listen only): `app.py:handle_seqtrak_sysex` sets all 11 tracks to that variation and
re-reads their steps (4ffd6f7, 2026-10-11). The bridge never sends `01 10 2A`.

### Pattern State Broadcast
When changing patterns, state is broadcast to all 11 tracks:

| Address | Data | Notes |
|---------|------|-------|
| `01 10 39` | [val] [val] | Track 1 pattern state (2 bytes) |
| `01 11 39` | [val] [val] | Track 2 pattern state |
| `01 12 39` | [val] [val] | Track 3 pattern state |
| ... | ... | ... |
| `01 1A 39` | [val] [val] | Track 11 pattern state |

Values observed: `0A 0A` (active/highlighted), `01 01` (inactive)

---

## UI State / Display Mode

### Mode Indicator
| Address | Data | Mode |
|---------|------|------|
| `01 10 2E` | 01 | Default/idle |
| | 02, 03 | ❓ Seen around master-effect knob use (likely master-effect screens) |
| | 09 | Volume adjust |
| | 14 | Scale select (0x14 = 20) |
| | 17 | Octave adjust (0x17 = 23) |
| | 1A | BPM adjust (0x1A = 26) |

### Options Page Navigation
| Address | Data | Page |
|---------|------|------|
| `01 17 30` | 00 | Page 1 |
| | 01 | Page 2 |
| | 02 | Page 3 |
| | 03 | Page 4 |

### Additional UI State Addresses
| Address | Data | Notes |
|---------|------|-------|
| `01 10 30` | 00/01 | Unknown toggle (seen during pattern change); also `01 1p 30` per track on track select |
| `01 10 2D` | [val] [val] | 2-byte state (seen: 06 06, 01 01) |
| `01 10 1D` / `1E` / `1F` | 00/01 | ❓ Likely Master Effect 1 / 2 / 3 state (1D seen before FX1 knob, 1F before FX3 knob) |
| `01 10 16` | 110-byte block | 🟡 **Project name** (all zero for device-created, unnamed projects). Official project name: `30 40 00–57` |
| `01 1p 53`/`54`/`55` | 1 byte each | ❓ Per-track sound info on track select (`09 00 02` drum/synth, `08 00` for sampler) |
| `01 1p 5C`/`5D`/`5E` | 1 byte each | ❓ Per-track, differs per preset — likely an ID of the loaded sound |
| `01 1n 50–52`, `59–5B` | 1 byte each | ❓ n = 0–2, sent with master-effect state on project load |
| `01 10 17` | 00 | 🟡 First message of the **project-load broadcast** (seen on project delete 2026-10-13, burst ends `01 10 00 00`); the bridge re-reads everything after it |
| `01 10 18` | 00/02/03/08/16 | 🟡 Device display state: `03` = a step key is held, `08` = micro timing shown, `00` = back to normal |
| `01 10 18` (bridge write) | 02 / 00 | ❓ The bridge **sends** `02` = "6 variations", `00` = "3 variations" (Shift + encoder CC 78 in track mode; `app.py:_toggle_variation_mode`, since 059a98a, 2025-12-27). Never verified; the device read `01 10 18 = 00` while Pattern Select Mode `30 40 79 = 01` (`REVERSE-ENGINEERING-LOG-2026-10.md` §1), and the observed meaning above is display state. The official setting is probably Pattern Select Mode `30 40 79` |
| `01 10 28` | 00-06 | 🟡 **Sampler pad (element) selected**, pad 1–7. Both directions: the device sends it when a pad is picked on the Seqtrak; the bridge sends it on Shift+pad and before sample recording. Used by bridge: `protocol.py:select_sampler_element` ← `app.py:_sync_sampler_element`, `app.py:handle_button` (Shift+Record); listen `app.py:handle_seqtrak_sysex` (redraws that pad's steps; e9017bc, 2026-10-12). Captured on track select as `01 10 28 00` (`FUNCTIONALITY-MAP.md`) |
| `01 10 19` | 00/03/04 | ✅ Device UI mode: `03` step-input edit, `04` **Delete held**, `00` idle |
| `01 10 20` / `21` / `22` | 00/01 | ✅ Play / Record / Sample-record state (Stop while recording sends `21 00`) |
| `01 10 27` | 00-0A | ✅ Track selected on the device |
| `77 01 10 [x] 00 [step]` | — | 🟡 A step key is held on the device (x = `01` SNARE, `00` KICK seen — likely track) |
| `01 10 2E` | 31 / 0A / 03 | 🟡 Sent with step-key hold (31), micro timing (0A), release (03) — the blinking indicator |
| `01 10 53` | 00-7F | Unknown state (seen: 09) |
| `01 10 54` | 00-7F | Unknown state (seen: 00) |
| `01 10 55` | 00-7F | Unknown state (seen: 02) |
| `01 10 5C` | 00-7F | Unknown state (seen: 00) |
| `01 10 5D` | 00-7F | Unknown state (seen: 50 = 80 decimal) |
| `01 10 5E` | 00-7F | Unknown state (seen: 7F = 127) |
| `01 10 2C` | 01-06 | ❓ Only in `protocol.py` (`PATTERN_VAR_B`, sent with `01 10 28` by the unused `select_variation()`). Never captured from the device for variations |
| `01 18 30` | 00-03 | ❓ Only in `protocol.py` (`PATTERN_BANK`, "banks 1–4", unused `select_bank()`). Unverified; compare `01 17 30` (options page) and `01 1p 30` above |

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

Bank values, the SAMPLER element variant (MSB 62, channel = element) and bridge use: see Part 1 "Sound Selection".

---

## Step Sequencer Data

> **Status key:** ✅ verified on hardware (readback or the user's eyes) · 🟡 observed, not fully verified ·
> ❓ unknown. Full write-up, test history and examples: `docs/Seqtrak/STEP-SEQUENCER.md` (wins if this
> section ever disagrees). Rewritten 2026-10-13; the Dec 2025 version of this section was wrong about the
> drum data bytes, the sampler delete (`72 50 00` never worked) and the "SYNTH/DX command `74 73`" (a report).

### Two storage models
| | Drum tracks 1–7 | SAMPLER (11) + SYNTH 1 / SYNTH 2 / DX (8–10) |
|---|---|---|
| Stored as | Fixed grid, one slot per step 0–127 | Ordered **list of notes**, addressed by **index** (0 = earliest; renumbers after a remove) |
| Add | `70 [t] 00` + `[step] [note] [vel] [len_hi] [len_lo]` ✅ | `72 [g] 00` + 8-byte note ✅ |
| Remove | `70 [20+t] 00` + `[step]` ✅ | **`74 [g] [index] 00`** ✅ (index in the address; `74 [g] 00 [n]` always removes #0) |
| Read (Parameter Request) | `70 [40+t] [step]` → 6 bytes, or no data if empty ✅ | `75 [g] [index]` → 8-byte note, no data = end of list ✅ |
| Clear whole track | — | `01 [10+t] 37 00` ✅ — but acts on the variation **shown on the device**, not the MIDI-selected one |

`t` = track − 1 (KICK 0 … PERC2 6). `g` = group: SYNTH 1 `00` ✅, SYNTH 2 `10` 🟡, DX `20` 🟡, SAMPLER `30` ✅.
Reads and edits act on the track's **currently selected variation** (`30 5p 0F`).

### Drum step data (6 bytes, as read back)
```
[note] [vel] [substep] [60 + micro] [len_hi] [len_lo]
  3C    64      00          3C          00       78      ← a step entered on the step keys
```
| Byte | Meaning | Status |
|---|---|---|
| note | always `3C` so far | 🟡 |
| vel | `64` (100) on every note so far, incl. played-in | ❓ soft/hard Push hits not yet tested |
| substep | `00` none; seen `01`, `02`, `04` (user guide §6.4: none, ×2, ×3 8th-trip, ×3 16th-trip, ×4) | ✅ it's substep; ❓ value→option mapping |
| 60 + micro | micro timing in ticks, −60…+59 (§6.3); `3C` = on the grid | ✅ (`6C` = +48, `0E` = −46) |
| len (14-bit) | note length in ticks (120 = 1 step). Step entry = `00 78`; played in = key hold time (48…134 seen) | 🟡 strong evidence |

The add command `70 [t] 00 [step] 3C 64 00 78` = note, vel, then length 120 (substep/micro not included).

### Sampler / melodic note (8 bytes)
```
[tick_hi] [tick_lo] 00 [note] [vel] 00 [len_hi] [len_lo]
```
- Position = 14-bit tick, **120 ticks per step**: step 1 `00 00`, step 2 `00 78`, step 3 `01 70`, step 6 `04 58`, step 16 `0E 08`.
- Note: sampler pad n (1–7) = `3C + n − 1`; melodic = MIDI note. ✅
- Length = 14-bit ticks. **The Seqtrak stops the sample when the note ends** (`0` = silent). A note that
  reaches the next note on the same pad removes that next note. ✅ Adding at an occupied position replaces. ✅

### What the device reports (Seqtrak → bridge)
| Message | When | Status |
|---|---|---|
| `70 [t] 00 [step] …` | drum step turned on with the step keys | ✅ |
| `70 [20+t] 00 [step]` | drum step turned off on the device | ✅ |
| `70 [10+t] [param] [step] [value]` | per-step edit on the device: param `00` = micro timing (60+offset), `03` = substep | ✅ report; ❓ untested as a command; ❓ probability param |
| `72 [g] 00` + note | sampler/melodic note added on the device | ✅ |
| `74 [70+g>>4] 00` + note | note removed (also after a replace or overlap) — **report only, sending it does nothing** | ✅ |
| *(nothing)* | **notes recorded live** (Record on, played from Push or device keys) — they are stored and read back normally, but never reported | ✅ |

### Step-related LEDs and modes (Yamaha user guide)
- **Purple step key = Parameter Lock** on that step (§9.2, p. 64). A VOLUME parameter lock changes the
  note's velocity. ❓ where parameter locks are stored in SysEx.
- Micro timing: hold a lit step key + turn the track knob (§6.3). Substep: hold a lit step key 2 s (§6.4).
  Probability: hold a lit step key + [MUTE], 8 levels (§6.6). Note length (synth/sampler only): hold a
  lit step key + turn [ALL] (§7.9, §8.10).
- Pattern length 1–128 steps per variation: `30 5p 16/18/1A/1C/1E/20` (2 bytes, = steps) ✅ readable.
  Lengthening copies existing bars into the new ones; shortening keeps data past the end (§5.2).

---

## Preset Name Data

Long-form message (110 bytes) contains preset name as ASCII:

**Address**: `01 1p 35` — **per track** (p = track 0–A). `01 10 35` is KICK; e.g. `01 17 35` =
SYNTH1, `01 18 35` = SYNTH2, `01 19 35` = DX. Sent as part of the track-select state dump.

**Corrected from code, 2026-10-11 (4b05c4c — "Verified on pibridge with Seqtrak + Push 1"):** ✅ the bridge
now **requests** `01 1p 35` with a Parameter Request (`F0 43 30 7F 1C 0C 01 1p 35 F7`) and accepts the
reply on any `01 10–1A 35` (previously it only matched `01 10 35`). Used by bridge:
`protocol.py:request_preset_name` ← `app.py:_request_seqtrak_state` (all 11 at startup), `_select_next_track`,
`_select_prev_track`, `handle_seqtrak_sysex` (device track change); decode `app.py:_decode_preset_name`.

**Encoding (Yamaha 7-bit packing):** groups of 8 bytes = 1 high-bit byte + 7 data bytes. Bit `0x40 >> j`
of the high-bit byte is bit 7 of data byte j. The name ends at the first decoded `00`.

**Example:**
```
01 10 35 00 54 53 5F 52 4E 42 5F 00 6B 69 63 6B 5F 72 6E 00 62 ...
              T  S  _  R  N  B  _     k  i  c  k  _  r  n     b
```

Decoded: "TS_RNB_" + "kick_rn" + "b" = Preset name for RnB kick sound

---

## Sound Element Parameters (41 / 42) — corrected

> **Corrected 2026-10-11.** These were originally labeled "effect sends/params". Official:
> `41 ep xx` = **Sound element Oscillator / Amplitude / Pitch** and `42 ep xx` = **element
> Filter / EQ / LFO**, where the middle byte = **e** (element 0–7, high nibble) + **p** (part 0–A,
> low nibble). So `41 00/10/20…70 0A` are KICK's elements 0–7 (offset `0A`), not 8 tracks, and
> `41 xA` is SAMPLER (part A) element x. Per-track reverb/delay **sends** are actually
> `31 1p 19` / `31 1p 1A`. Look up offset names in the Data List (`36-…part-3.md`). The original
> observations are kept below.

### (original) Per-Track Effect Sends (Drum Tracks)
Address format: `41 [track*16] 0A`

| Track | Address | Data | Notes |
|-------|---------|------|-------|
| KICK | `41 00 0A` | 00-7F | Effect send level |
| SNARE | `41 10 0A` | 00-7F | Effect send level |
| CLAP | `41 20 0A` | 00-7F | Effect send level |
| HAT1 | `41 30 0A` | 00-7F | Effect send level |
| HAT2 | `41 40 0A` | 00-7F | Effect send level |
| PERC1 | `41 50 0A` | 00-7F | Effect send level |
| PERC2 | `41 60 0A` | 00-7F | Effect send level |
| SYNTH1 | `41 70 0A` | 00-7F | Effect send level |

**Note**: Address middle byte increments by 0x10 (16) for each drum track.

### Per-Track Effect Parameters (Synth/DX/Sampler)
Address format: `41 [0A + track*16] [param]`

For tracks 8-11, the addressing uses a different base offset:

| Track | Base Addr | Notes |
|-------|-----------|-------|
| DX (9) | `41 0A xx` | Track 9 params |
| SAMPLER (10) | `41 1A xx` | Track 10 params |
| ? | `41 2A xx` | Additional track |
| ? | `41 3A xx` | Additional track |
| ? | `41 4A xx` | Additional track |

**Effect Parameters per Track:**

| Param Addr | Data | Notes |
|------------|------|-------|
| `41 xA 0B` | 40 | Center position (speculative: pan/balance) |
| `41 xA 2E` | 64 | Value 100 (speculative: level) |
| `41 xA 33` | 00 | Off/disabled |
| `41 xA 35` | 00-7F | Range 0-127 (speculative: send level) |
| `41 xA 4F` | 40 | Center position |
| `41 xA 58` | 28 | Value 40 |
| `41 xA 59` | 40 | Center position |
| `41 xA 5E` | [h] [l] | 2-byte value (seen: 01 00) |
| `41 xA 60` | [h] [l] | 2-byte value (seen: 01 00) |

---

## Sound Engine Parameters (31 xx xx)

These addresses control the synth engine parameters per-track.

> **Corrected 2026-10-11.** Official block names (Data List): `31 0p` = Sound Name,
> `31 1p` = **Sound Common General**, `31 2p` = **Insertion Effect A**, `31 3p` = **Insertion
> Effect B**, `31 4p` = LFO, `31 5p` = **Arpeggiator**. Insertion type = offset `00` (2 bytes,
> codes in the Effect Type List), params from `03`. Known `31 1p` names: `00` AEG decay/release
> (synth) · `01–05` DX carrier attack/decay, mod amount, ratio, feedback · `14` Volume ·
> `19` Reverb Send · `1A` Delay Send · `1E/1F` Portamento switch/time · `22` Key Assign ·
> `23` Mono/Poly/Chord · `2C/2D/2E` AEG attack/decay/sustain · `31–34` FEG · `39–43` 3-band EQ ·
> `45–4F` 2-band EQ (`48` low gain, `4D` high gain). The original observations are kept below.

### Address Structure

The `31` address space uses a consistent pattern:
- `31 1[track] xx` - Single-byte parameters per track
- `31 2[track] xx` - 2-byte parameters per track (possibly modulation)
- `31 3[track] xx` - 2-byte parameters per track (possibly envelopes)

Where track: 0=KICK, 1=SNARE, ..., 9=DX, A=SAMPLER

### Single-Byte Sound Parameters (31 1x xx)
| Address | Data | Notes |
|---------|------|-------|
| `31 00 67` | 00-7F | Unknown global param (seen: 00) |
| `31 1x 19` | 00-7F | Per-track param (seen: 00) |
| `31 1x 1A` | 00-7F | Per-track param (seen: 00) |
| `31 1x 1C` | 00-7F | Per-track param (seen: 40 = center) |
| `31 1x 22` | 00-7F | Per-track param (seen: 01 = enabled?) |
| `31 1x 23` | 00-7F | Per-track param (seen: 01 = enabled?) |
| `31 1x 2C` | 00-7F | Per-track param (seen: 40 = center) |
| `31 1x 2D` | 00-7F | Per-track param (seen: 40 = center) |
| `31 1x 48` | 00-7F | Per-track param (seen: 40 = center) |
| `31 1x 4D` | 00-7F | Per-track param (seen: 40 = center) |

### 2-Byte Sound Parameters (31 2x xx)

These appear to be synth/modulation parameters:

| Address | Data | Notes |
|---------|------|-------|
| `31 2x 00` | [h] [l] | 2 bytes (seen: 07 10, 0D 28) |
| `31 2x 03` | [h] [l] | 2 bytes (seen: 00 50, 01 38, 02 00) |
| `31 2x 05` | [h] [l] | 2 bytes (seen: 00 00, 00 10) |
| `31 2x 07` | [h] [l] | 2 bytes (seen: 00 00, 00 3C) |
| `31 2x 09` | [h] [l] | 2 bytes (seen: 00 34, 02 7B) |
| `31 2x 0B` | [h] [l] | 2 bytes (seen: 00 34) |
| `31 2x 13` | [h] [l] | 2 bytes (seen: 00 50) |
| `31 2x 15` | [h] [l] | 2 bytes (seen: 00 01) |
| `31 2x 17` | [h] [l] | 2 bytes (seen: 00 4F) |
| `31 2x 19` | [h] [l] | 2 bytes (seen: 00 00) |
| `31 2x 1B` | [h] [l] | 2 bytes (seen: 00 00) |
| `31 2x 1D` | [h] [l] | 2 bytes (seen: 00 00) |
| `31 2x 1F` | [h] [l] | 2 bytes (seen: 00 00) |
| `31 2x 21` | [h] [l] | 2 bytes (seen: 00 00) |
| `31 2x 43` | 00-7F | Enable flag? (seen: 7F = on) |

### Envelope/Filter Parameters (31 3x xx)

| Address | Data | Notes |
|---------|------|-------|
| `31 3x 03` | [h] [l] | 2 bytes (seen: 02 00) |
| `31 3x 05` | [h] [l] | 2 bytes (seen: 00 10) |

**Note**: Replace `x` with track number (0-A) in the middle byte position.

---

## SAMPLER Sample Parameters (50 eA xx) — corrected

> **Corrected 2026-10-11.** Originally labeled "Arpeggiator/Motion". Official: `50 eA xx` =
> **SAMPLER Sample**, e = pad/element 0–6. Confirmed by capture on sampler track select:
>
> | Address | Size | Name | Seen |
> |---|---|---|---|
> | `50 eA 60` | 4 | Loop Length | `00 01 26 5F` |
> | `50 eA 66` | 4 | **Start Point** | `00 00 00 00` |
> | `50 eA 6A` | 4 | **End Point** | `00 01 26 5F` |
>
> 4-byte values: `1st bit2-0 → bit23-21, 2nd → bit20-14, 3rd → bit13-7, 4th → bit6-0`.
> The arpeggiator is at `31 5p xx`. Original observations kept below.

## (original) Arpeggiator/Motion Parameters (50 xx xx)

| Address | Data | Notes |
|---------|------|-------|
| `50 0A 66` | 00 00 00 00 | Track A (DX) arp/motion param |
| `50 1A 66` | 00 00 00 00 | Track 1A (Sampler?) |
| `50 2A 66` | 00 00 00 00 | Unknown track |
| `50 3A 66` | 00 00 00 00 | Unknown track |
| `50 4A 66` | 00 00 00 00 | Unknown track |
| `50 5A 66` | 00 00 00 00 | Unknown track |
| `50 6A 66` | 00 00 00 00 | Unknown track |

**Note**: 4-byte data values. Address pattern suggests per-track parameters using `xA` offset.

---

## Address Space Summary

| Range | Purpose |
|-------|---------|
| `00 00 xx` | System settings (master volumes, MIDI, Wi-Fi, click, sync, sampling…) — official |
| `01 1p xx` | UI state / feedback, per track p (selection, display, preset name, project name) — undocumented |
| `30 40 xx` | Project common (name, tempo, swing, master step, scale slot, key, solo) — official |
| `30 41`–`30 4D` | Send reverb/delay, Master FX 1–4, Master EQ, A/D input, USB audio in, scale definitions — official |
| `30 5p xx` | Project track (vol, pan, choke group, octave, pattern select, pattern step counts, mute) — official |
| `30 6p` / `30 7p` | Chord notes of scale — official |
| `31 0p`–`31 5p` | Sound name, common, Insertion A, Insertion B, LFO, Arpeggiator — official |
| `41 ep` / `42 ep` | Sound element osc/amp/pitch, filter/EQ/LFO (e = element, p = part) — official |
| `48 09` / `49 o9` | DX common / operator — official |
| `50 eA xx` | SAMPLER sample (start/end/loop per pad) — official |
| `70 xx xx` | Drum step data (tracks 0-6): add `70 0t`, remove `70 2t`, read `70 4t`, per-step edit report `70 1t` |
| `72 g 00` | Sampler/melodic **note add** (g = `00` SYNTH 1, `10` SYNTH 2, `20` DX, `30` SAMPLER) |
| `74 g [index]` | Sampler/melodic **note remove** by index; `74 7g 00` = removal *report* from the device |
| `75 g [index]` | Sampler/melodic **note read** (Parameter Request) |

*(`72`/`74`/`75` rows corrected from code, 2026-10-12 (09fd543); previously "72 = sampler (track 10)",
"74 = Synth/DX (tracks 7-9)". See "Step Sequencer Data".)*

---

## What Requires SysEx (Not Available via CC)

These parameters are NOT in the official MIDI CC spec and require SysEx:

1. **Tempo** - `30 40 76`
2. **Scale type** - `30 40 7E`
3. **Key** - `30 40 7F`
4. **Pattern length** - `30 40 7A`
5. **Swing** - `30 40 7C`
6. **Track octave** - `30 5x 0C`
7. **Step sequence data** - `70 xx` (drums), `72`/`74`/`75` (sampler + melodic note lists)
8. **Pattern/variation select** - `30 5x 0F`
9. **Track select** - `01 10 27`
10. **Preset names** - `01 1p 35` (per track)
11. **Master volume** - `00 00 00`
12. **Record / sample record** - `01 10 21` / `01 10 22`
13. **Sampler pad select** - `01 10 28`

---

## Messages used by the bridge (from code)

Index of every Seqtrak message in `src/open_push/seqtrak/` as of 2026-10-12 (branch `integration`, 150927a +
working tree). No other module under `src/open_push/` talks to the Seqtrak. Details are in the sections
linked above; this table is the cross-check. → = bridge to Seqtrak, ← = Seqtrak to bridge, R = read with a
Parameter Request.

| Message | Dir | Status | Used by bridge |
|---|---|---|---|
| FA Start / FC Stop | → | ✅ | `app.py:handle_button`, `_launch_session_row`, `run` |
| FA / FB / FC | ← | 🟡 | `app.py:handle_seqtrak_message` (playhead) |
| Note on/off, ch 1–7 note 60 (+67) | → | 🟡 | `app.py:_handle_drum_pad`, `_process_note_repeat` |
| Note on/off, ch 8–10 | → | 🟡 | `app.py:_handle_melodic_pad`, `_process_arpeggiator` |
| Note on/off, ch 11 notes 60–66 | → | 🟡 | `app.py:_handle_sampler_pad` |
| Sound CCs 5, 7, 10, 20, 21, 25–29, 65, 71, 73–75, 91, 94, 116–119 | → | 🟡 | `app.py:handle_encoder` (device mode) |
| CC 7 volume | → | 🟡 | `app.py:handle_encoder` (mixer), `_adjust_drum_bus_volume` |
| CC 23 mute / CC 24 solo (ch 1) | → | 🟡 | `app.py:_toggle_track_mute`, `_toggle_track_mute_simple`, `_toggle_track_solo`, `_toggle_drum_bus_mute` |
| CC 0 / 32 + Program Change, MSB 63, ch 1–10 | → ← | ✅ | `app.py:_cycle_patch`; listen `handle_seqtrak_message` |
| CC 0 / 32 + Program Change, MSB 62, ch 1–7 (sampler pads) | → | 🟡 | `app.py:_cycle_sampler_pad_preset` |
| Parameter Request `F0 43 30 7F 1C 0C [addr] F7` | → | ✅ | `protocol.py:request_parameter` |
| `00 00 00` speaker master volume | → ← R | ✅ | `app.py:handle_encoder`, `handle_seqtrak_sysex`, `_request_seqtrak_state` |
| `01 10 17` project-load broadcast start | ← | 🟡 | `app.py:handle_seqtrak_sysex` → full re-read |
| `01 10 18` 02/00 "3/6 variations" | → | ❓ | `app.py:_toggle_variation_mode` |
| `01 10 19` UI mode (04 = Delete held) | ← | ✅ | `app.py:handle_seqtrak_sysex` → step re-read on release |
| `01 10 20` play state | ← | ✅ | `app.py:handle_seqtrak_sysex` |
| `01 10 21` record | → ← | ✅ ← / 🟡 → | `protocol.py:record` ← `app.py:handle_button`; `handle_seqtrak_sysex` |
| `01 10 22` sample record | → ← | ✅ ← / 🟡 → | `protocol.py:sample_record` ← `app.py:handle_button`; `handle_seqtrak_sysex` |
| `01 10 27` track select | → ← | ✅ | `app.py:_send_track_select`; `handle_seqtrak_sysex` |
| `01 10 28` sampler pad select | → ← | 🟡 | `app.py:_sync_sampler_element`, `handle_button`; `handle_seqtrak_sysex` |
| `01 10 2A` global variation | ← | 🟡 | `app.py:handle_seqtrak_sysex` |
| `01 1p 35` preset name (110 B) | ← R | ✅ | `protocol.py:request_preset_name`; `app.py:handle_seqtrak_sysex`, `_decode_preset_name` |
| `30 40 76` tempo | → ← R | ✅ | `app.py:handle_encoder`, `protocol.py:tap_tempo`; `handle_seqtrak_sysex` |
| `30 40 7C` swing `01 [00–1C]` | → | 🟡 | `app.py:handle_encoder` |
| `30 5p 0F` pattern select | → ← R | ✅ | `app.py:_adjust_variation`, `_launch_session_row`, delete menu; `handle_seqtrak_sysex` |
| `30 5p 16–20` pattern 1–6 step count | → ← R | ✅ R / 🟡 → | `app.py:_adjust_bar_length`; `handle_seqtrak_sysex`, `_request_seqtrak_state` |
| `70 0t 00` drum add / report | → ← | ✅ | `app.py:_toggle_step`; `handle_seqtrak_sysex` |
| `70 2t 00` drum remove / report | → ← | ✅ | `app.py:_toggle_step`, `protocol.py:send_drum_delete` ← `_clear_variation_data`; `handle_seqtrak_sysex` |
| `70 4t [step]` drum read | R | ✅ | `app.py:_request_drum_steps`, `handle_seqtrak_sysex` |
| `72 30 00` sampler note add / report | → ← | ✅ | `protocol.py:add_note` ← `app.py:_toggle_sampler_step`; report → re-read |
| `74 g [index] 00` note remove | → | ✅ (g = `30`; `00/10/20` via delete menu, SYNTH 2/DX 🟡) | `protocol.py:remove_note` ← `app.py:_toggle_sampler_step`, `_clear_variation_data` |
| `74 73 00` removal report | ← | ✅ | `app.py:handle_seqtrak_sysex` → sampler re-read |
| `75 g [index]` note read | R | ✅ | `app.py:_request_sampler_notes`, `_read_note_list_blocking`, `_handle_sampler_note_reply` |

The bridge only listens for **sampler** note reports and replies (`72 30`, `74 73`, `75 30`); melodic
(SYNTH/DX) reports are ignored, and melodic notes are only read by the delete menu.

**Defined in `protocol.py` but never called by the app** (not evidence that they work):
`continue_playback` (FB), `set_scale` `30 40 7E`, `set_key` `30 40 7F`, `set_track_octave` `30 5p 0C`,
`select_all_variations`, `select_variation` (`01 10 28` + `01 10 2C`), `select_bank` (`01 18 30`),
`set_track_pan` / `set_track_filter` / `set_track_reverb` / `set_track_delay` / `set_drum_pitch` /
`set_arp_type` (CC helpers; device mode uses `send_track_cc` instead), constants `DISPLAY_MODE` `01 10 2E`,
`REVERB_TYPE` `30 41 00`, `REVERB_ON` `30 41 46`, `DELAY_TYPE` `30 42 00`, `DELAY_ON` `30 42 47`,
`MASTER_FX_1–4` `30 43–46 00`, and CC 102–115 (master / single / send FX params).

---

## Raw Capture Archive

> Raw Dec 2025 captures, kept for reference. The byte annotations here predate the verified format —
> use the Step Sequencer Data section above for meanings (e.g. sampler position is one 14-bit tick).

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

### Completed
- [x] Synth/sampler step data - note list: add `72 [g] 00`, read `75 [g] [i]`, remove `74 [g] [i] 00` (✅ 2026-10-12; `74 73` is only a removal report)
- [x] Drum step delete - Command `70 [0x20+track] 00 [step]` (0x20 offset pattern)
- [x] Sampler step delete - `74 30 [index] 00` (✅ 2026-10-12; the old `72 50 00` never worked)
- [x] Drum step bytes - `[note] [vel] [substep] [60+micro] [len 14-bit]` (micro + substep ✅ 2026-10-13)
- [x] Live-recorded notes are not reported; project-load broadcast starts `01 10 17` (2026-10-13)
- [x] Sound engine parameter structure (31 xx xx) - Identified 1x, 2x, 3x sub-ranges
- [x] Effect parameter structure (41 xx xx) - Identified drum and synth track addressing
- [x] Arpeggiator/motion parameters (50 xx xx) - Identified base addresses
- [x] `30 5p 16…20` - **pattern 1–6 step counts** (not a filter; ✅ readable 2026-10-12)
- [x] Effect type MSB/LSB codes - See "Effect Type Reference" section (70+ effect types documented)
- [x] Arpeggio preset types - See "Arpeggio Presets Reference" section (16 presets)
- [x] DX FM algorithms - See "DX Algorithm Chart" section (12 algorithms)
- [x] Sound design parameters by track type - See "Sound Design Parameters by Track Type"
- [x] MIDI Implementation details - See "MIDI Implementation Chart Reference"

- [x] Effect type selection addresses — master FX `30 43–46 00`, send reverb `30 41 00`, send delay `30 42 00`, track insertion `31 2p 00` / `31 3p 00` (official, 2026-10-11)
- [x] Sample start/end points — `50 eA 66` / `50 eA 6A` (official + captured, 2026-10-11)
- [x] Variation hardware behavior — global vs per-track (captured, 2026-10-11)
- [x] Choke groups — `30 5p 08` (official + captured, 2026-10-11)

### Remaining
- [ ] Substep value → option mapping; probability (§6.6) per-step param; velocity on played-in drum notes
- [ ] Where Parameter Locks (purple steps, §9.2) are stored
- [ ] Whether `70 [10+t] [param] [step] [value]` works as a command
- [ ] Pattern copy/paste SysEx commands
- [ ] Load preset / load project commands from the app (needs MIDI Monitor spy mode)
- [ ] Meaning of `01 1p 53–55`, `01 1p 5C–5E`, `01 1n 50–5B`, `01 10 1D–1F` (see `FUNCTIONALITY-MAP.md`)
- [ ] Motion sequence data format (within 50 xx xx)
- [ ] Complete 31 xx xx parameter name mapping (need correlation with Sound Design params)
- [ ] Complete 41 xx xx parameter name mapping (need correlation with Effect params)
- [ ] Preset name encoding for custom presets

---

## Capture Sources

This document was compiled from:

**Official Yamaha Documentation:**
- SEQTRAK_data_list_Core.pdf - Track types, sound categories, arpeggio presets, DX algorithms, MIDI implementation
- SEQTRAK_data_list_Effects.pdf - Effect block diagram, effect type list with MSB/LSB codes
- SEQTRAK_data_list_Sound_Design_Parameter_List.pdf - Per-track-type parameter listings
- SEQTRAK_data_list_Effect_Preset_List.pdf - Single/Send/Master effect preset configurations

**Reverse Engineering:**
- Live MIDI capture sessions using MIDI Monitor
- `reference files/Yamaha/Seqtrak Data List/md/Seqtrak SysEX Data.md`
- Experimentation with Seqtrak hardware
- Bridge code audit 2026-10-12 (`src/open_push/seqtrak/app.py`, `protocol.py`) — see "Messages used by the bridge"

---

## Code comments that disagree with verified docs

Found in the 2026-10-12 code audit. The docs win; these comments (not necessarily the behaviour) should be
fixed in the code later.

1. **Drum step add bytes** — `app.py:_toggle_step` (docstring + `data = [step, note, 0x64, 0x00, 0x78]  # step,
   note, vel, gate, prob`) and the `70 [t] 00` branch comment in `app.py:handle_seqtrak_sysex`
   (`[note] [vel] [gate] [prob]`) call the last two bytes gate and probability. Verified: they are a 14-bit
   **length** in ticks, `00 78` = 120 = one step (`STEP-SEQUENCER.md`; the RE log: "the last byte is the note
   length in ticks, not probability"). The bytes sent are right; only the labels are wrong.
2. **Bar length "powers of 2 only"** — `app.py:_adjust_bar_length` docstring ("Hardware limitation: Only
   supports powers of 2 (1, 2, 4, 8 bars)", from 3c088b7). Official Pattern n Step is any value 1–128 (user guide §5.2).
   Powers of 2 are only what had been observed.
3. **`01 10 18` = 3/6 variation mode** — `app.py:_toggle_variation_mode` docstring states `02` enables 6
   variations. Unverified (❓ in the RE log); the observed meaning of `01 10 18` is device display state.
4. **Variation via `01 10 28` + `01 10 2C`** — `protocol.py` (`PATTERN_VAR_A/B`, `select_variation`:
   "Seqtrak uses paired messages for variation"). Captures show variations use `30 5p 0F` (+ `01 10 2A`),
   and `01 10 28` is the sampler pad select. Dead code, but a trap if anyone calls it.
5. **Preset name address** — `protocol.py` `Address.PRESET_NAME = 01 10 35` ("ASCII preset name (up to 16
   chars)"). It is per track, `01 1p 35`, and 7-bit packed, not plain ASCII (the code that is actually used,
   `request_preset_name` / `_decode_preset_name`, is correct).
6. **Track octave range** — `protocol.py:set_track_octave` ("-3 to +2", `3D`–`42`). Official: −2…+2.
7. **SysEx header labels** — `protocol.py` module docstring calls `7F` "Category (bulk/system)" and `1C`
   "Sub-group". Official: `7F 1C` together is the **Group Number** (`midi-data-table.md`). (This doc's
   "General SysEx Format" diagram has the same old labels.)
