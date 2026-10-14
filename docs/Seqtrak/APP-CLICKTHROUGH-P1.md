# SEQTRAK app click-through, Phase 1: the command behind every app control

**Captured 2026-10-14 00:33–03:01** (`experiments/app-clickthrough/captures/1*.txt`, 232 blocks; per-block notes in
`clicklog.md`). One app control per block, each moved through its range and back. The Seqtrak was on **USB**, and
everything the app sent (OUT) and received (IN) was recorded with MIDI Monitor's spy driver. Method and Phase 0:
`APP-CLICKTHROUGH-P0.md`.

**Status in this file:**
- 📱 = **the official app sends this to change the control**, and the app's screen showed the change. Strong
  evidence it is a command, but per the project rule it is ✅ only after a Push/Pi readback or the user's eyes on
  the device. Promote rows to ✅ in `sysex-protocol-reference.md` as they are tested.
- ✅ = also verified another way (named in the row). ❓ = unknown.
- Names in [brackets] are the official Data List names for that address.

All messages are Parameter Changes `F0 43 10 7F 1C 0C [H M L] [data] F7`. `p` = part (0 KICK … 6 PERC2,
7 SYNTH 1, 8 SYNTH 2, 9 DX, A SAMPLER). 2-byte values are 7-bit pairs (`hi*128 + lo`).

---

## ⚠️ Things to know first
1. **The app switched the Seqtrak to project 8 at 03:00:47** (block 102-01, project rename). It sent
   `B0 00 40`, `B0 20 00`, `C0 07` (= Bank MSB 64, LSB 0, Program 7 = **project 8**, Data List project select)
   after a click landed in the project grid. ❓ Check which project the Seqtrak is on before using it; the scratch
   project should still be in its own slot.
2. Many app edits send **several messages**: e.g. KICK CHOKE writes the track's key-assign mode **and** an
   alternate group on all 8 drum elements; SWING writes the project swing **and** each synth track's ARP swing.
   A Push implementation should send the same set.
3. Some Phase 1 blocks carry two controls; the clicker's log says which came first.

---

## KM-104 Drum tracks: steps (biggest find)

The app **sends** the per-step edits that the Seqtrak reports when you edit on the device, so they are commands:

| Message | Control | Values (from the app's display) |
|---|---|---|
| `70 [10+t] 00 [step] [60+offset]` | Micro timing | `3C` = on the grid, drag to +44 → `68`. Range −60…+59 (§6.3) |
| `70 [10+t] 03 [step] [v]` | **Substep** (§6.4) | 📱 `00` = 1 (none) · `01` = ×2 · `04` = ×3 8th triplet · `02` = ×3 16th triplet · `03` = ×4 |
| `70 [10+t] 04 [step] [v]` | **Probability** (§6.6) | 📱 `00` = 100 % · `01` = 87 % · `04` = 49 % · `07` = 10 % (8 levels, `00`–`07`; the in-between percentages not captured) |
| `70 0t 00 [step] 3C 64 00 78` / `70 2t 00 [step]` | Step on / off | Same as the known drum add/remove (`STEP-SEQUENCER.md`) |
| `72 00 00` + `00 00 00 3C 64 00 00 78` | SYNTH 1 piano roll: add C3 at step 1 | Same as the known melodic add (8-byte note) |
| `30 5p 16` (2 bytes) | BARS / STEPS fields | Pattern 1 step count, e.g. 32 → `00 20` |

So the substep values seen earlier on SNARE steps 5/7/13/15 (`02 04 02 01`) were ×3 16th, ×3 8th, ×3 16th, ×2.

## KM-103 Tracks & patterns

| Message | Control | Values |
|---|---|---|
| `30 5p 0F [0–5]` [Pattern Select] | Track pattern 1–6 (track page and PERFORM > PATTERN grid) | 00 = pattern 1 |
| `30 40 79` [Pattern Select Mode] | SETTINGS > PATTERNS 3 ↔ 6 | 📱 `00` = 3 patterns, `01` = 6 patterns. ⚠️ the bridge's 3/6 toggle writes `01 10 18` instead (bug, KM-100) |
| `30 40 7A` (2 bytes) [Pattern Master Step] | ADVANCED > LAUNCH QUANTIZE | 📱 1 → `00 01`, 4 → `00 04`, 16 → `00 10`, 32 → `00 20` |
| `77 01 20 00 [pattern]` then `77 01 21 00 [pattern]` | Pattern COPY, then PASTE (KICK P1 → P6) | 📱 `20` = copy from pattern 0, `21` = paste to pattern 5. ❓ The `00` byte is probably the track (KICK = 0) |
| — | Track TYPE DRUM/DRUMKIT/SYNTH | Not captured: the app warns that the pattern is deleted, so it was cancelled |

## KM-105 Synth tracks: arp, chords, scale, key

| Message | Control | Values |
|---|---|---|
| `31 5p 00` [ARP Template] | ARP on/off | 📱 `01` on, `00` off |
| `31 5p 0D` [ARP Key Mode] | ARP MODE | 📱 `00` ARP, `03` +DIRECT |
| `31 5p 1E` (2 bytes) [ARP Type] | ARP TYPE | 📱 `00 00` UP, `00 01` DOWN, `00 02` RANDOM, `00 03` UP DOWN 1, `00 04` UP DOWN 2, `00 05` SLAP & POP, `00 06` UNISON, `00 07` RHYTHM 1, `00 08` RHYTHM 2 (the app list showed 9; Data List says more exist) |
| `31 5p 08` [ARP Unit Multiply] | ARP SPEED | 📱 `00` 200 %, `01` 150 %, `02` 133 %, `03` 100 %, `04` 75 %, `05` 66 %, `06` 50 %, `07` 37 %, `08` 33 %, `09` 25 % |
| `31 5p 14` (2 bytes) [ARP Gate Time Rate] | ARP GATE 0–200 % | 📱 value = percent (`00 64` = 100, `01 48` = 200) |
| `31 5p 1C` [ARP Octave Range] | ARP OCTAVE −3…+3 | 📱 `40` + octave (`43` = +3, `3D` = −3) |
| `31 1p 23` [Mono/Poly Mode] | TYPE MONO/POLY and CHORD toggle | 📱 `00` mono, `01` poly, `02` chord |
| `30 6p 00–1B` [Chord notes of scale 1] | CHORD PACK | 📱 the app rewrites all 7 pads × 4 notes (MIDI note numbers), each address first `00`, then the new note |
| `30 40 7F` [Key] | SETTINGS > KEY | 📱 **`40` = C**, `41` = C# … `4B` = B (key = `0x40` + semitone; `midi-data-table.md`'s 0–11 is wrong) |
| `30 40 7E` [Scale] | SETTINGS > SCALE (slot 1–8) | 📱 `00`–`07` = the project's 8 scale slots |
| `30 4D 70–76` (slot 8; 🟡 slot n probably at `30 4D [16*(n−1)]…`) | SCALES IN THIS PROJECT: change slot 8 | 📱 rewrites the slot's pad notes (`30 4D 70–76` for slot 8: e.g. MINOR-type note sets `3C 3E 3F 41 43 44 46`) |
| `00 00 1F` [Record Quantize Value] | ADVANCED > LIVE REC QUANTIZATION | 📱 `00` OFF, `01` 1/32, `02` 1/16T, `03` 1/16, `04` 1/8T, `05` 1/8 |

## KM-106 SAMPLER

| Message | Control | Values |
|---|---|---|
| `00 00 1C` [Auto Normalize] | RECORD SETTINGS > NORMALIZE | 📱 `00` off, `01` on |
| `00 00 19` [Sampling Source] | RECORD SETTINGS > SOURCE | 📱 `00` USB, `01` MIC/LINE IN, `02` RESAMPLING |
| `50 eA 66` (4 bytes) [Start Point] / `50 eA 6A` (4 bytes) [End Point] | SAMPLE edit START / END | 📱 sample position, e.g. `00 00 18 43`; e = pad − 1. ❓ LOOP point and LOOP OFF sent nothing |
| `41 eA 2E` [Element Level] | PERFORM > SAMPLER pad fader | 📱 0–127 |
| `30 40 63` [Sampler Element Mute] | PERFORM > SAMPLER pad MUTE | 📱 bit mask, pad 1 = `01` |
| `41 eA 4F` [Coarse Tune] | GUIDE PITCH knob (SAMPLER) | 📱 `40` = 0. ❓ Wrote element 6 (`41 6A`) although pad 1 looked selected |
| `31 3A 03/05` | SAMPLER filter / resonance | Same as the track filter below |

## KM-107 Sound design (track pages)

| Message | Control | Values |
|---|---|---|
| `31 1p 1C` [Note Shift] | PITCH −24…+24 | 📱 `40` = 0 (`28`–`58`) |
| `30 5p 01` [Pan] / `30 5p 00` [Volume] | PAN / VOLUME (also the PERFORM mixer faders) | 📱 `40` = centre; 0–127 |
| `31 1p 2C` [AEG Attack Time] / `31 1p 2D` [AEG Decay Time] | ATTACK / DECAY (drums) | 📱 `40` = 0, `7F` = +63, `00` = −64 |
| `31 17 00` | DECAY on SYNTH 1 | 📱 `40` = 0. ❓ The parsed Data List name for this address is unreliable; check the PDF |
| `31 1p 22` [Key Assign Mode] + `41 e p 0A` [Alternate Group] ×8 elements | Drum CHOKE on/off | 📱 on = `00` + group `01`; off = `01` + group `00` |
| `31 3p 03` (2 bytes) [Insertion-B Parameter 1] | FILTER type + FREQ (one combined value) | 📱 `02 00` = THRU; below it = LPF (`00 09` = 20 Hz … `01 7E` = 19.4 kHz), above it = HPF (`03 00` ≈ 438 Hz). ❓ HPF top end not captured |
| `31 3p 05` (2 bytes) [Insertion-B Parameter 2] | FILTER RES | 📱 `00 00` = −6 dB (min), `00 7F` = max, `00 10` = default |
| `31 1p 48` / `31 1p 4D` [2bandEQ Low/High Gain] | EQ GAIN LOW / HIGH | 📱 `40` = 0 dB, `58` = +12, `28` = −12 |
| `31 1p 46` / `31 1p 4B` (2 bytes) [2bandEQ Low/High Frequency] | EQ FREQ LOW / HIGH | 📱 `00 30` = 63 Hz, `00 66` = 300 Hz, `01 10` = 1 kHz, `01 74` = 18 kHz |
| `31 1p 19` [Reverb Send] / `31 1p 1A` [Variation Send] | SEND 1 / SEND 2 (also PERFORM > SEND faders) | 📱 0–127 |
| `31 1p 1E` [Portamento Switch] / `31 1p 1F` [Portamento Time] | PORTAMENTO | 📱 on/off; 0–127 |
| LFO `31 4p 01` wave · `02` speed · `03` tempo speed · `04` tempo sync · `05` delay · `0B` destination · `0C` depth | SOUND DESIGN > LFO (KICK, SYNTH 1) | 📱 wave `00`–`0B` in the app's grid order (TRIANGLE, TRIANGLE 2, SAW UP, SAW DOWN, SQUARE 1/4, 1/3, SQUARE, 2/3, 3/4, TRAPEZOID, S/H 1, S/H 2); tempo speed `05`–`18` in grid order 1/16 … 1/4×64 (1/4 = `0B`); destination `00` FX OVERDRIVE, `01` AMP TYPE, `02` LPF CUTOFF, `03` OUTPUT LEVEL, `09` DRY/WET, `20` FILTER CUTOFF, `21` RESONANCE, `40` SOUND LEVEL, `41` PITCH, `44` PAN (FX names follow the track's effect) |
| `01 1p 5C`, `01 1p 53/54` | DX / SAMPLER overview effect slider, effect MAP popup | 📱 these go to **UI-state** addresses, not the effect itself. ❓ Probably the device-knob mapping ("FX knob") rather than a sound parameter |
| — | GUIDE WAVEFORM knob | Nothing sent |

## KM-108 Effects

**Effect types:** every type the app selected matches Yamaha's **Effect Type List** (Data List p. 61–63; md
`14-effect-type-list.md`), MSB LSB as the 2-byte value, and the names the app showed. ✅ (two sources agree)

| Slot in the app | Block | Type | Parameters | Other |
|---|---|---|---|---|
| MASTER EFFECT | `30 43` [Master Effect 1] | `30 43 00` | `30 43 03, 05, 07 …` = parameters 1, 2, 3 … (2 bytes each, odd addresses); DRY/WET = parameter 10 at `15` | DUCKER category = compressor types + `30 43 43` [Side Chain Part] (`00` = KICK, `7F` = off) |
| EFFECT 1 | `30 44` [Master Effect 2] | `30 44 00` | same layout | |
| EFFECT 2 | `30 45` [Master Effect 3] | `30 45 00` | same layout | |
| COMP | `30 46` [Master Effect 4] | `30 46 00` | same layout | `30 46 47` = COMP ON/OFF |
| 5 BAND EQ | `30 47` [Master EQ] | — | band n (1–5): gain `30 47 [4(n−1)]` (`34` = −12 dB, `40` = 0, `4C` = +12), freq `+1`, Q `+2` (`01` = 0.1 … `78` = 12.0, `07` = 0.7) | freq: band 1 `04` = 32 Hz … `28` = 2 kHz; bands 2–4 `0E`…`36` (to 10 kHz); band 5 `1C`…`3A` (to 16 kHz) |
| SEND 1 REVERB | `30 41` [Send Reverb] | `30 41 00` | `03, 05, …` | `30 41 44` = RETURN VOL |
| SEND 2 DELAY | `30 42` [Send Variation] | `30 42 00` | `03, 05, …` | `30 42 44` = RETURN VOL |
| Track EFFECT | `31 2p` [Insertion A] | `31 2p 00` | `31 2p 03, 05, …`; same per track (`31 20` KICK, `31 26` PERC2, `31 27` SYNTH 1) | `31 2p 43` [Side Chain Part] |

Parameter value ranges depend on the effect type (Data List "Effect Parameter List", md `15`–`18`); the captures
hold the raw values for every parameter page of SPX ROOM, CONTROL FILTER, BEAT REPEAT, R3 HALL,
TEMPO DELAY STEREO, UNI COMP DOWN and AMP SIMULATOR 2 (blocks 108-03, 11, 21, 32, 42, 52, 71).

## KM-109 Mixer / KM-110 Mute & solo

| Message | Control | Values |
|---|---|---|
| `30 5p 00` [Volume] | PERFORM > MIXER fader | 📱 0–127 |
| `30 5p 29` [Mute] | MIXER MUTE | 📱 **`7D` = muted**, `00` = unmuted (not `01`) |
| `30 40 68` [Solo Track] | MIXER SOLO | 📱 track number (1–11, KICK = `01`, SYNTH 1 = `08`), `00` = off. Only one track can be soloed |
| `30 40 66` [Volume] | MASTER Overview VOLUME | ✅ P0-PROBE |
| `00 00 00` [Speaker Master Volume] | HARDWARE > MASTER VOLUME SPEAKER | 📱 0–127 |
| `00 00 18` [Analog Audio Output Gain] / `00 00 15` [USB Audio Output Gain] | OUTPUT GAIN | 📱 `00` −6 dB, `01` 0 dB, `02` +6, `03` +12 |

## KM-111 Song mode

| Message | Control | Values |
|---|---|---|
| `71 00 00 00`, `71 10 06 01/00`, `71 10 01 00 01` | SONG: add scene 1, loop button | ❓ scene data lives in the `71` block; one block only — needs its own capture (one action per block) |

## KM-112 Connections & settings

| Message | Control | Values |
|---|---|---|
| `01 10 20 01` / `01 10 20 00` | **Transport Play / Stop** from the app | 📱 SysEx play/stop (the device reports the same address) |
| `30 40 76` (2 bytes) [Tempo] | BPM (field and ▲▼) | 📱 BPM as a 7-bit pair: 100 = `00 64`, 120 = `00 78`. Typing "60.5" sent `02 2C` (= 300, the maximum) — ❓ how fractional BPM is sent |
| `30 40 7C` (2 bytes) [Swing Offset] + `31 5p 16` (2 bytes) on SYNTH 1/2/DX | SWING | 📱 value = **128 + swing offset in ticks**; the app's % = (120 + offset) / 240. 68 % → `01 2C` (172), 70 % → `01 30`, 66 % → `01 26`. The app also writes the same value to each synth track's ARP swing |
| `00 00 25` [Click Switch] / `00 00 27` [Click Volume] / `00 00 26` [Click Type] | Metronome | 📱 type A–E = `00`–`04`. Beat buttons 1–4 sent nothing |
| `00 00 21` [Sound Design Mode] | ADVANCED SOUND DESIGN | 📱 |
| `30 4B 06` [A/D Part Insertion FX Switch] | NOISE GATE (MIC/LINE IN) | 📱 `03` / `02` |
| `00 00 1B` [Sampling Count In] | COUNT-IN MIDI RECORDING | 📱 |
| `30 4B 16` [A/D Part Output Select] / `30 4C 16` [USB Part Output Select] | MASTER FX (MIC/LINE IN) / (USB) THRU–ON | 📱 `01` / `00` |
| `00 00 20` [Pad Velocity] | INPUT VELOCITY | 📱 1–127 |
| `00 00 1D` [Project Resume Switch] + `00 00 1E` [Project Resume Auto Trigger] | PLAYBACK MODE AFTER PROJECT SWITCH | 📱 OFF / MANUAL / AUTO (exact pairs: see block 112-06) |
| `00 00 2D` [Midi Clock Out] / `00 00 2A` [MIDI Sync] / `00 00 2B` [Transmit Sequencer Control] | CLOCK SEND / SYNC / START/STOP SEND | 📱 |
| `00 00 0A/0B/0C/22` (MIDI cable), `00 00 0E/0F/10/23` (USB), `00 00 12/13/14/24` (Bluetooth) | Per port: CH MSG SEND / CC+BANK+PC / SYSEX SEND / THRU | 📱 the middle one is a bit mask: `70` = all on, CC off clears `40`, BANK SELECT off clears `20`, PROGRAM CHANGE off clears `10`. THRU `03` on / `00` off |
| `00 00 2F` | KNOB SENSITIVITY | 📱 `01` FAST, `02` NORMAL, `03` SLOW |
| `01 10 03` | AUTO POWER OFF | 📱 `00` off, `01` 5 min, `02` 10, `03` 15, `04` 30, `05` 60, `06` 120 |
| `00 60 06` | Wi-Fi country | ASCII ("US") — see P0 |

## KM-113 App-only: DX engine and drum choke

| Message | Control | Values |
|---|---|---|
| `48 09 00` [Algorithm] | DX ALGORITHM 1–12 | 📱 `00`–`0B` |
| `49 o9 00` [ON/OFF] | Operator on/off | 📱 o = operator − 1 (`49 09` OP1 … `49 39` OP4) |
| `49 o9 19` [Freq. Mode] / `1A` [Coarse] / `1B` [Fine] / `1C` [Detune] | MODE RATIO/FIXED, FREQ, DETUNE | 📱 detune `40` = 0 |
| `49 o9 13` [Output Level] / `12` [Velocity Sensitivity] / `14` [Feedback Level] + `15` [Feedback Type] / `0A` [Keyboard Rate Scaling] | LEVEL, VEL.S, FEEDBACK (bipolar = level + type), KSC.R | 📱 |
| `49 o9 02–05` [EG Rate 1–4] / `06–09` [EG Level 1–4] | EG times / levels | 📱 the app's "time" maps inversely onto rate (time 0 = `7F`) |
| `49 o9 0C/0D` [KLS Left/Right Depth] / `0E/0F` [Curve] | KSC L/R DEPTH and MODE | 📱 curve `00` LIN, `01` EXP |
| `48 09 0A–0D` [PEG Rate 1–4] / `0E–11` [PEG Level 1–4] / `49 o9 18` [PEG ON/OFF] | PITCH EG | 📱 level `40` = 0 |
| `48 09 04` [LFO Wave] / `05` [Speed] / `06` [Delay] / `07` [PMD] / `49 o9 17` [PMD on/off] / `49 o9 11` [AMD depth] | DX LFO | 📱 wave `00` SINE, `01` TRIANGLE, `02` SAW UP, `03` SAW DOWN, `04` SQUARE, `05` S/HB, `06` S/H. ⚠️ SPEED shows 0–63 in the app but sends 0–127 (typed 63 → `7F`, 32 → `41`, 13 → `1A`) |
| `30 5p 08` [Group Number] | SETTINGS > DRUM CHOKE: HAT (HAT1+HAT2) / PERC (PERC1+PERC2) | 📱 HAT pair `7E`, PERC pair `7F`, off `00` (written to both tracks) |

## KM-102 Projects

| Message | Control | Values |
|---|---|---|
| Bulk Request `0B 00 00` → 1-page dump | PROJECT/SOUND MANAGER, project name popup | 🟡 project list |
| `B0 00 40`, `B0 20 00`, `C0 [n]` | Project select | 📱 Data List project select, program 0–7 = project 1–8 (sent by accident, see top) |
| — | PROJECT name rename | The rename did not apply; nothing captured |

## Still to capture
- Song mode (KM-111) one action per block; track TYPE change (destructive, needs a throwaway project);
  SAMPLER loop point; fractional BPM; HPF range of the track filter; ARP types beyond 9.
- Readback verification of 📱 rows from the Pi or Mac (Parameter Request after the write).
