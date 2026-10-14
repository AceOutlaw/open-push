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
1. **Project select messages.** In 102-01 (03:00:47) and again in LE-04 (13:55) the project-name popup sent
   `B0 00 40`, `B0 20 00`, `C0 07` (= Bank MSB 64, LSB 0, Program 7 = **project 8**, Data List project select).
   Both times it was program 7, so 🟡 the app probably re-selects the *current* project when that popup closes,
   rather than switching. The tempo/swing change seen after the Seqtrak's battery died (120 BPM, 50 % swing) is
   more likely the project reloading without unsaved edits. ❓ Check which slot the scratch project is in.
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

**Piano roll (melodic / sampler note list), block LE-03:** add C3 at step 5, drag it to step 1, long-press to delete.
| Message | Meaning |
|---|---|
| `72 00 00` + `03 60 00 3C 64 00 00 78` | 📱 add note (known): tick 480 = step 5, C3, velocity 100, length 120 |
| `76 00 00` + `[tick hi lo] 00 [note] 00 00` → device replies `76 01 00` + same 6 bytes + `00 00` | 📱 **find a note by position and pitch**. 🟡 The reply's last two bytes are the note's index (`00 00` = index 0). Lets a bridge find a note without reading the whole list |
| `73 00 00` + 8-byte note | 📱 **replace the found note** (here: moved to tick 0). ❓ Whether `73 [g] [index]` takes the index in the address like `74` |
| `74 00 00` (no data byte) | 📱 remove note index 0 — same as the known `74 [g] [index] 00`, the data byte is optional |

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
| `31 5p 08` [ARP Unit Multiply] | ARP SPEED | 📱 app speed `00` 200 %, `01` 150 %, `02` 133 %, `03` 100 %, `04` 75 %, `05` 66 %, `06` 50 %, `07` 37 %, `08` 33 %, `09` 25 %. The Data List names the same values as note-length multipliers (50 % … 400 %); the app shows the inverse |
| `31 5p 14` (2 bytes) [ARP Gate Time Rate] | ARP GATE 0–200 % | 📱 value = percent (`00 64` = 100, `01 48` = 200) |
| `31 5p 1C` [ARP Octave Range] | ARP OCTAVE −3…+3 | 📱 `40` + octave (`43` = +3, `3D` = −3) |
| `31 1p 23` [Mono/Poly Mode] | TYPE MONO/POLY and CHORD toggle | 📱 `00` mono, `01` poly, `02` chord |
| `30 6p 00–1B` [Chord notes of scale 1] | CHORD PACK | 📱 the app rewrites all 7 pads × 4 notes (MIDI note numbers), each address first `00`, then the new note |
| `30 40 7F` [Key] | SETTINGS > KEY | 📱 **`40` = C**, `41` = C# … `4B` = B (key = `0x40` + semitone; `midi-data-table.md`'s 0–11 is wrong) |
| `30 40 7E` [Scale] | SETTINGS > SCALE (slot 1–8) | 📱 `00`–`07` = the project's 8 scale slots |
| `30 4D 70–76` (slot 8; 🟡 slot n probably at `30 4D [16*(n−1)]…`) | SCALES IN THIS PROJECT: change slot 8 | 📱 rewrites the slot's pad notes (`30 4D 70–76` for slot 8: e.g. MINOR-type note sets `3C 3E 3F 41 43 44 46`) |
| `00 00 1F` [Record Quantize Value] | ADVANCED > LIVE REC QUANTIZATION | 📱 `00` OFF, `01` 1/32, `02` 1/16T, `03` 1/16, `04` 1/8T, `05` 1/8 |

## KM-106 SAMPLER

Blocks 106-01…06 (overnight) and 106-07…22 (re-run 11:05–11:13 after the Seqtrak was reconnected). `e` = pad − 1
(0–6), so pad 1 = `0A`, pad 2 = `1A` … pad 7 = `6A` in the middle byte. Confirmed for pads 1, 2 and 7.

### Sample length, start, end and loop (`50 eA` [SAMPLER Sample])
All four are **4-byte values of 7 bits each** (`b0*2^21 + b1*2^14 + b2*2^7 + b3`), counted in **sample frames**.

| Address | [Name] (Data List range) | What the app does |
|---|---|---|
| `50 eA 66` | [Start Point] (0 … 0x00FFFFFF) | 📱 START handle. Pad 1 dragged to ~20 % → `00 00 26 57` = 4,951 |
| `50 eA 6A` | [End Point] (0, 0x0F … 0x00FFFFFF) | 📱 END handle. Pad 1 dragged to ~75 % → `00 00 7A 77` = 15,735. With loop off, the app writes the same value to Loop Length (LE-09) |
| `50 eA 5F` | [Loop On/Off] | 📱 LOOP OFF/ON: `00` off, `01` on |
| `50 eA 60` | [Loop Length] (0x50 … 0x00FFFFFF) | 📱 LOOP handle. The loop **ends at the End Point**, so moving the loop point right makes Loop Length smaller (loop start = End − Loop Length) |
| `50 eA 00–57` | [Sample Name 1–88] | Not read by the app in these blocks |

🟡 **Sample length:** the app reads Start, End, Loop On/Off and Loop Length every time a sample editor opens. On an
untrimmed sample (start 0, loop off) the End Point and the Loop Length both equal the last frame, i.e. the sample's
length:

| Pad (sample) | End Point read | Frames |
|---|---|---|
| 1 "Female Count 1" | `00 01 26 5F` | 21,343 |
| 2 "Singing - Female - Ah 1" | `00 05 60 1F` | 94,239 |
| 7 | `00 02 15 64` | 35,556 |

- ❓ **Sample rate** — needed to turn frames into seconds. Not in the user guide (it only says each recording
  is up to 16 s, §8.2) or the Data List extract. If it's 44.1 kHz, pad 1 is 0.48 s and pad 2 is 2.14 s.
  Test: record exactly 16 s and read its End Point.
- ❓ When the app dragged END back to the maximum it wrote `00 01 26 70` (21,360), 17 more than the 21,343
  it had read. Read End Point back after writing to see what the Seqtrak keeps.
- So the Push can show a waveform-less sample editor: length, start/end and loop as percentages or seconds.

### Per-pad sound parameters (`41 eA` [Sound element], `42 eA`)
| Address | [Name] | App control | Values |
|---|---|---|---|
| `41 eA 4F` | [Coarse Tune] | PITCH knob | 📱 `40` = 0 |
| `41 eA 08` | [Trigger/Gate Mode] | TYPE TRIGGER / GATE | 📱 Data List: `00` Trigger, `01` Gate (sampler default `01`) |
| `41 eA 0B` | [Pan] | PAN knob | 📱 `40` = centre |
| `41 eA 2E` | [Element Level] | VOLUME knob, PERFORM > SAMPLER fader | 📱 0–127 (`64` default) |
| `41 eA 33` | [AEG Attack Time] | AEG ATTACK | 📱 the number typed (0 → `00`, 20 → `14`) |
| `41 eA 37` | [AEG Release Time] | AEG **DECAY** in the app | 📱 typed value (50 → `32`, 80 → `50`) |
| `41 eA 35` | [AEG Decay 2 Time] | — (read only, `7F` on pad 1) | |
| `41 eA 5E / 60 / 62 / 64` (2 bytes) | [PEG Attack / Decay 1 / Decay 2 / Release Level] | PITCH ENVELOPE ATK PITCH, DEC PITCH | 📱 128 + value: `01 00` = 0, `01 1E` = +30, `00 62` = −30. DEC PITCH writes Decay 1, Decay 2 **and** Release level together |
| `41 eA 59` | [PEG Decay 1 Time] | PITCH ENV DEC TIME | 📱 typed value (100 → `64`, 64 → `40`) |
| `41 eA 58` | [PEG Attack Time] | PITCH ENV ATK TIME | 📱 only the **GUIDE panel knob** sends it (LE-10/11: `30`, back to `28`). The edit page's field and graph send nothing (106-13…15) — an app bug |
| `42 eA 36` / `42 eA 39` | element EQ gain (Data List `36` = EQ 1 Gain) | GUIDE EQ LOW GAIN / EQ HIGH GAIN (LE-08) | 📱 `40` = 0 dB, knob up → `44`. 🟡 36 = low, 39 = high (from the order the knobs were turned) |

### Track-level and other
| Message | Control | Values |
|---|---|---|
| `30 5A 01` / `30 5A 00` | SAMPLER track PAN / VOLUME | 📱 as other tracks |
| `01 1p 30 [page]` | GUIDE panel next page (pages 1–4 seen) | 📱 UI state only |
| GUIDE knobs (LE-06…10) | WAVEFORM sends nothing; PITCH = `41 eA 4F`; AEG DECAY = `41 eA 37`; FILTER FREQ / RES = `31 3A 03 / 05`; SENDS = `31 1A 19 / 1A`; START / END / LOOP LENGTH = `50 eA 66 / 6A / 60`; LOOP MODE knob sent nothing; PEG knobs = `41 eA 5E / 58 / 60–64 / 59` | 📱 |
| `00 00 0E 01`, `00 00 0F 70`, `00 00 10 01` | sent by the app on reconnect (LE-02) | 📱 the app turns **USB MIDI channel messages, CC/bank/PC and SysEx transmit on** whenever it connects |
| `31 2A 03` (2 bytes) | SAMPLER track effect parameter 1 (WAVE FOLDER: FOLD) | 📱 FOLD 0.642 → `05 02`, 0.202 → `01 4A` |
| `B0 00 3E`, `B0 20 [bank]`, `C[pad−1] [n]` | SOUND picker: choose a preset sample for a pad | 📱 Bank MSB 62 = sampler element (Data List), channel = pad. Female Count 1 = bank 0 prog 0, Female Count 2 = prog 1, Male Count 1 A = prog 8, first RISER = bank 4 prog `5D` |
| Bulk Request `0D 01 [cat]`, `0D 02 [cat]`, `0D 00 0F` | SOUND picker category lists | 🟡 like the sound list (P0): `0D 02 04` (RISER) answered 2 pages of names; others answered empty headers |
| `00 00 1C` [Auto Normalize] | RECORD SETTINGS > NORMALIZE | 📱 `00` off, `01` on |
| `00 00 19` [Sampling Source] | RECORD SETTINGS > SOURCE | 📱 `00` USB, `01` MIC/LINE IN, `02` RESAMPLING |
| `30 40 63` [Sampler Element Mute] | PERFORM > SAMPLER pad MUTE | 📱 bit mask, pad 1 = `01` |

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

First pass (111-01) mixed several actions. Re-run as blocks **SG-01…23** (2026-10-14 14:31 and 16:34–16:46), one
action each. The app can only add scenes and edit them; switching to Song mode was done **on the device**
(Ace: hold [ALL] + [PROJECT↑], guide §13.1) during SG-11/13. User guide §13 (p. 79–84). A song has up to 16 scenes.

| Message | Direction | Meaning |
|---|---|---|
| `71 00 00 [scene]` | app → | 📱 **add scene** (`+`), scene = 0-based slot. The guide says the selected scene is copied into it (§13.3) |
| `71 40 [scene]` + 2 bytes + 11 bytes | device reply / readable | 📱 **scene data**: then one byte per track (KICK … SAMPLER) = the track's pattern, 0-based. ❓ the 2 leading bytes (length? `00 00` seen). Readable for all 16 slots with a Parameter Request |
| `71 [10+t] 01 [scene] [pattern]` | app → | 📱 **set a track's pattern in a scene**: KICK scene 2 → pattern 2 = `71 10 01 01 01`; SNARE scene 1 → pattern 3 = `71 11 01 00 02` |
| `71 [10+t] 02 [scene] [0/1]` | app → | 📱 **scene mute** for track t: HAT2 = `71 14 02 00 01` on, `… 00` off |
| `71 10 03 [scene] [track]` | app → | 📱 **scene solo**: track number 1–11 (HAT2 = `05`), `00` = off. One track per scene, like the mixer solo |
| `71 10 04 [scene]` | device → | 📱 **current scene**; changes as the song plays (0 → 1 → 2 during SG-16) and when a scene key is pressed |
| `01 10 17 [mode]` | device → | 🟡 **Song mode state**: `00` normal, `02` song (seen when Ace switched modes and pressed scene keys). ❓ Scene mode value not captured (probably `01`) |
| `71 50 00 01` / `00` | device → | ❓ toggles around each scene-key press (queued / pressed flag?) |
| `71 10 06` | readable | ❓ `00`; `71 10 01…03` are also sent by the device when a scene popup opens |
| `01 10 20 01` / `00` | app → | Play / Stop (same as normal mode); in Song mode it plays the scenes in order |

⚠️ **This changes what we thought `01 10 17` meant.** `STEP-SEQUENCER.md` called `01 10 17 00` the start of a
"project loaded" burst, and the bridge does a full re-read 0.5 s after it (`42d6679`). It is the song-mode state,
which a project load re-broadcasts — so in Song mode the bridge would re-read everything on every scene key
press. Needs a fix (KM-114 follow-up).

**Not captured from the app:**
- the whole-song loop button (§13.2.3, app-only): a screen overlay (Wispr Flow) blocked that spot twice
- deleting a scene: the app has no control for it (right-click / long-press do nothing). Device only (§13.4)
- scene length and AUTO (§13.5.2): device only ([PAGE] + [ALL] knob)
- switching Song / Scene mode: device only; the app just shows it
- the app's SONG page only shows scenes added in the same app session, not the ones already on the device

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

## Extra pass (blocks EX-01…21, 14:07–14:21)

| Message | Control | Values |
|---|---|---|
| `9[t] 3C 64` / `8[t] 3C 00` | PERFORM > PAD/KEY drum pads | 📱 plain MIDI notes: note 60 (`3C`), velocity 100, channel = drum track (KICK ch 1 … PERC2 ch 7) |
| `97 [note] 64` / `87 [note] 00` | PAD/KEY SYNTH 1 keys | 📱 plain MIDI notes on channel 8; the app's OCTAVE buttons just change the note number (C3 = `3C`, C4 = `48`). SYNTH 2 / DX on ch 9 / 10; SAMPLER pads on ch 11 as notes `3C` + pad − 1 (pad 1 = `3C`, pad 7 = `42`) |
| `8[ch] 00 00` × many | switching PAD/KEY pages | the app's all-notes-off, on channels 8–11 |
| `01 10 21 01` / `01 10 21 00` | RECORD button (PAD/KEY) | 📱 **record on / off by SysEx** (the device reports the same) |
| `31 1p 1C` [Note Shift] | PITCH knob on SNARE … PERC2 | 📱 same address on every drum track (p = 1…6), confirming the per-track offset |
| `31 18 2C`, `31 18 00` | SYNTH 2 AEG ATTACK / DECAY | 📱 as SYNTH 1 |
| `31 19 01` [Carrier Attack Offset] / `31 19 02` [Carrier Decay Offset] | **DX** AEG ATTACK / DECAY | 📱 the DX's amp envelope goes to different addresses from the other synths |
| GUIDE pages on SYNTH 2, DX, KICK | filter, sends, EQ, portamento, ARP on/gate/speed | 📱 same addresses as the full pages; `01 1p 30 [page]` = GUIDE page |
| `B[ch] 00 3F`, `B[ch] 20 [bank]`, `C[ch] [prog]` | SOUND picker on KICK (ch 1), SYNTH 1 (ch 8), DX (ch 10) | 📱 Bank MSB 63 = sound (Data List); LSB `00`–`1F` preset, `20`–`2F` user. KICK "TS_RNB_kick_rnb" = LSB `20` program `51` |
| Bulk Request `0C [type][cat]` | SOUND picker lists | 🟡 type `00/01/02` = drum / synth / DX; `0C 1x [cat]` = a category list (KICK `0C 10 00`, SYNTH 1 BASS `0C 11 00`, DX `0C 12 01`); `0C 0x 0F` read alongside |
| `F0 43 00 7F 1C 00 07 0C 10 01 03 20 51 [0/1] [sum] F7` | favourite heart on a sound (KICK, toggled twice) | 🟡 a small **bulk write**: bank LSB `20`, program `51`, last byte = favourite off/on. ❓ the `03` byte |
| — | HOME > VISUALIZER | separate 3D visual app; nothing relevant sent |

## Still to capture
- Song mode: the whole-song loop button (blocked by a screen overlay); scene length, delete and Song/Scene
  switching are device-only, so capture them with the Seqtrak's keys on the Pi. Track TYPE change is skipped
  (needs firmware 2.0; this unit runs 1.21.3).
- fractional BPM; HPF range of the track filter; ARP types beyond 9; the sampler's sample rate (record a
  timed sample and read its End Point); block LE-02 was cut off when the Seqtrak powered down.
- Readback verification of 📱 rows from the Pi or Mac (Parameter Request after the write).
