# SEQTRAK project export (`.Y3P`)

What the SEQTRAK app writes when it exports a project. Decoded 2026-10-18 from one export
(`random 1.Y3P`, 1.9 MB, firmware 1.21.3 unit). Status per line: ✅ seen in the file and checked,
🟡 inferred, ❓ unknown.

## Container

✅ A plain **ZIP** (deflate). Every item is a pair: `<name>N.xml` (metadata) + `<name>N.bin` (data).

| Files | What | Notes |
|---|---|---|
| `project.xml` / `project.bin` | The project | `project.bin` 1.1 MB; starts `00 00 00 A8` + the name in Yamaha 7-bit packed text (same packing as the SysEx name replies) 🟡 |
| `soundN.*` | Non-preset **sounds** used by the project (e.g. saved `_edit` sounds) | `.bin` 1,792 bytes each, starts with the sound name in 7-bit packed text |
| `elementN.*` | Non-preset **SAMPLER elements** (pad sounds) | `.bin` 512 bytes, starts with the sample name (e.g. `STRICTLY LO FI 2 PERCUSSION 01`) |
| `waveformN.*` | Waveforms (audio headers) for those sounds/elements | `.bin` 132 bytes: two 66-byte keybank headers |
| `sampleN.*` | **The audio** | Raw PCM, one file per keybank (see below) |

Preset content is **not** included: the project refers to it by number only.

## project.xml

```xml
<ProjectData>
  <UUID>…</UUID> <Order>8</Order> <Name>random 1</Name> <CompatibleVersion>1</CompatibleVersion>
  <Part01SoundNumber>0</Part01SoundNumber> … <Part11SoundNumber>0</Part11SoundNumber>   <!-- per track -->
  <Element1SampleNumber>0</Element1SampleNumber> … <Element8SampleNumber>16383</Element8SampleNumber>
  <CreatedDate>2026-10-18T00:54:37</CreatedDate>
</ProjectData>
```

- ✅ `PartNNSoundNumber` = the sound on track NN (1–11), as a **content number**.
- ✅ `ElementNSampleNumber` = the sample on SAMPLER pad N (1–7); `Element8` = 16383 (`3FFF`, likely "none").
- ✅ Content numbers ≥ ~4000 for sounds / ~594 for elements here are the user / non-preset items, and each
  one has a matching `soundN` / `elementN` in the archive (`ContentNumber`).
  Example: pad 3 = element 605 (Riser), pad 7 = element 594 (Tom / STRICTLY LO FI perc).
- 🟡 Low numbers (e.g. Part08 855, Part09 1221, Part10 1970; pads 75, 136, 208, 292) are presets, not in the file.

## Content metadata (`sound/element/waveform N.xml`)

`ContentNumber`, `UUID`, `Order`, `Tag1`/`Tag2` (e.g. Tom / Electronic), `MainCategory`, `SubCategory`,
`Commercial`, `Favorite`. ✅ So user content has a **stable UUID** as well as a number.

## Audio (`sampleN.*` + `waveformN.bin`)

- ✅ `sampleN.xml`: `WaveformNumber`, `KeybankNumber` (0 / 1), `DataSize`.
- ✅ Every waveform has two keybanks of equal size, different data: **stereo, left and right stored separately**
  (rebuilt as a stereo WAV, 2026-10-18).
- ✅ `sampleN.bin` = **raw 16-bit little-endian PCM**, frames = DataSize / 2.
- ✅ `waveformN.bin` per keybank (66 bytes): sample rate at offset 0x28 = `44 AC` → **44,100 Hz**;
  u32 LE at 0x34 = last frame (length − 1), 0x40 = length in frames; 0x3C 🟡 (loop point?).
- ✅ The frame counts match the SysEx sample length `01 1e 40`: pad 3 riser 498,071 frames (11.29 s),
  pad 7 perc 35,573 (0.81 s). So the SAMPLER runs at **44.1 kHz** (not 48 kHz).

## project.bin map (1,101,825 bytes)

Mapped 2026-10-18 by structure and by comparing with 2,291 values read live from the same project
(`random 1` was the project on the device: tempo 87, the same track sounds and pad samples).

| Offset | Size | What | Status |
|---|---|---|---|
| `0x0000` | 4 | `00 00 00 A8` | ❓ header / size |
| `0x0004` | — | Project name, 7-bit packed ("random 1") | ✅ |
| `0x0069` | 1 | Tempo (`57` = 87 BPM; `00` before it) | ✅ value matches |
| `0x0074` | ~0xC5C | Repeating note-number tables (`<`=60 …), period 0xF5 | 🟡 chord notes of scale (Data List "Chord Notes of Scale") |
| `0x0CE1` | 68 | A/D Part Insertion A (`30 49`), MIDI layout | 🟡 61/68 values match |
| `0x0D6A` + 0x5C5 × t | 0x5C5 each | **Track sound blocks**, tracks 1–10 (KICK … DX), each starts `01 51` + 7-bit packed sound name | ✅ names; 🟡 contents (only ~45 % match the MIDI layout: own order) |
| `0x4903` + 0x75 × e | 0x75 each | **SAMPLER pads 1–7**: `00 71` + SAMPLER Sample General (`50 eA`) in MIDI layout, name first | ✅ pad 1: 103/112 values match |
| `0x4C38` | ~0x70 | Zeros, one `01` at 0x4C98 | ❓ |
| `0x4CA9` → end | ~1.08 MB | **Pattern / song memory**: fixed-size store, mostly `FF`; records repeat every 0x46 (70) bytes and look bit-packed | ❓ needs differential exports |

**Number format**: blocks follow Yamaha's MIDI parameter map (Data List), but multi-byte numbers are stored
as native **little-endian** integers, not 7-bit groups. Example: pad 1 End Point 21,343 = `01 26 5F` over MIDI,
`5F 53 00 00` in the file. Names keep the 7-bit packed text form.

**Method for the rest**: export the same project twice with one change in between and diff the two
`project.bin` files (tempo, one track's volume, one drum step, one synth note, one lock, one scene).

### Differential exports, 2026-10-18 (`~/Downloads/Seqtak projects/`, `tools/y3p_diff.py`)

Six exports of `random 1`, each one change after the previous:

| Change | Bytes that changed | Result |
|---|---|---|
| Tempo 87 → 88 | `0x69` `57` → `58` | ✅ **tempo** = byte at 0x69 |
| Export name | `0x04`… (packed name) | ✅ the name is the export name |
| KICK step 1, pattern 2 (also selected pattern 2) | `0x6D` `00`→`01`; `0x255` `00`→`01`; headers of pages 2–5 | 🟡 0x6D likely KICK's selected pattern; step 1 itself didn't change (probably already on) |
| + KICK step 5, pattern 2 | page 1 +0x12A, +0x12F, +0x132 (`… 3C …`) | ✅ page 1 = KICK pattern 2 |
| + SYNTH 1 note | page 42 +0x8…+0x16 (`… 64 … 00 78 …` = vel 100, len 120) | ✅ page 42 = SYNTH 1 pattern 1 |
| "KICK vol" | page 1 +0x10 `64` → `52` (100 → 82) | 🟡 a KICK pattern-2 value; which control was changed to be confirmed |
| + one scene | `0x255` `01`→`00`; `0x4E08`…`0x4E67` | ✅ **song / scenes** around 0x4E00 |

**Pattern memory** = 66 pages of 0x4000 (16 KB) from `0x5000`:
- ✅ Pages 0–41: **drum tracks**, track by track, 6 patterns each: page = (track − 1) × 6 + (pattern − 1).
  KICK pattern 2 = page 1 (0x9000).
- ✅ Pages 42–65: **SYNTH 1, SYNTH 2, DX, SAMPLER**, 6 patterns each: page = 42 + (n) × 6 + (pattern − 1).
  SAMPLER pattern 1 = page 60 (0xF5000), where the pad-2 test notes (`3D 64`) were.
- 🟡 Drum pages are full (~1,400 non-`FF` bytes, maybe defaults for 128 steps); note pages are nearly empty.
- ❓ The page contents are a **bit-packed stream**: values like `3C` (note 60) and `00 78` (length 120) appear,
  but not at fixed record offsets. Needs exports that change one step property at a time (below).

**Next exports for the step format** (KICK, an empty pattern, one change each):
step 1 on → step 2 on → step 1 velocity changed → step 1 micro timing changed → step 16 on.

## What it means for saving projects on the Pi (KM-230)

- The app's own file already bundles **user sounds, sampler elements and their audio** with the project, and
  refers to presets by number. A Pi save could use the same shape (or this exact format).
- ❓ How the app gets these bytes off the device (Wi-Fi / USB content mode) and pushes them back: not captured.
- ❓ `project.bin` layout (where patterns, scenes, locks live): not decoded.
