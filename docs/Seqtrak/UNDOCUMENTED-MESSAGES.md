# Seqtrak messages that are NOT in Yamaha's Data List

Everything here was seen on the wire but is **not** in the official Data List (Parameter Base Address table,
Data List p. 119; Bulk Dump Block table, p. 120–121). The official blocks are `00 00`, `00 7F`, `11`, `12`, `30`,
`31`, `41`, `42`, `48`, `49` and `50`; anything else is here. For official addresses use `midi-data-table.md` and
the Data List.

**Sources:** the SEQTRAK app click-through of 2026-10-14 (`experiments/app-clickthrough/raw-spy-2026-10-14.log`;
`APP-CLICKTHROUGH-P0.md`, `-P1.md`), Pi captures of the device's own reports (`STEP-SEQUENCER.md`,
`REVERSE-ENGINEERING-LOG-2026-10.md`) and the bridge code.

**Status:** ✅ verified by readback or on the device · 📱 the official app sends it as a command (not yet tested
from the bridge) · 📥 the Seqtrak sends it / answers a Parameter Request · 🟡 meaning inferred from evidence given ·
❓ unknown. **Dir:** → = to the Seqtrak, ← = from the Seqtrak.

Message frame for all rows unless noted: Parameter Change `F0 43 10 7F 1C 0C [H M L] [data] F7`, Request
`F0 43 30 7F 1C 0C [H M L] F7`. `t` = drum track 0–6, `p` = part 0–10 (KICK … SAMPLER), `g` = note-list group
(`00` SYNTH 1, `10` SYNTH 2, `20` DX, `30` SAMPLER), `e` = sampler pad − 1.

---

## 1. Step data (`70`–`77`)

### Drum steps — fixed grid, one slot per step (0–127)
| Address | Dir | Data | Meaning | Status |
|---|---|---|---|---|
| `70 [0t] 00` | → ← | `[step] [note] [vel] 00 78` | Add a step (`3C 64 00 78` = note 60, vel 100) | ✅ |
| `70 [2t] 00` | → ← | `[step]` | Remove a step | ✅ |
| `70 [1t] [param] [step] [value]` | → ← | | Edit one step: param `00` micro timing (`60` + offset, −60…+59), `03` substep (`00` none, `01` ×2, `02` ×3 16th triplet, `03` ×4, `04` ×3 8th triplet), `04` probability (`00` = 100 %, `01` = 87 %, `04` = 49 %, `07` = 10 %) | 📱 (device reports the same) |
| `70 [4t] [step]` | read | `[note] [vel] [substep] [60+micro] [len hi] [len lo]`; no data = empty step | Read a step | ✅ |
| `70 [5t] [step]` | read | never answered so far | ❓ second step table (parameter locks?) — the app reads it for every step | ❓ |
| `70 [6t] [step]` | read | `00` on every set step | ❓ third step table (probability?) | ❓ |

### Sampler / melodic notes — an ordered list, addressed by index
| Address | Dir | Data | Meaning | Status |
|---|---|---|---|---|
| `72 [g] 00` | → ← | 8-byte note `[tick hi] [tick lo] 00 [note] [vel] 00 [len hi] [len lo]` | Add a note (120 ticks per step) | ✅ |
| `73 [g] 00` | → | 8-byte note | Replace the note just found with `76` (the app's drag-to-move) | 📱 |
| `74 [g] [index]` | → | `00` or nothing | Remove note `index` | ✅ |
| `74 [70+g>>4] 00` | ← | 8-byte note | The device's report of a removal. **Not a command** | ✅ |
| `75 [g] [index]` | read | 8-byte note; no data = past the end | Read note `index` (time order) | ✅ |
| `76 [g] 00` | → | `[tick hi] [tick lo] 00 [note] 00 00` | Find the note at this position and pitch | 📱 |
| `76 [g+1] 00` | ← | same 6 bytes + `00 00` | Answer to the find; 🟡 last two bytes = the note's index | 📱 |

### Pattern copy / paste and step keys
| Address | Dir | Data | Meaning | Status |
|---|---|---|---|---|
| `77 01 20` | → | `[track 0-10] [pattern 0-5]` | **Copy pattern** (0-based). Verified 2026-10-14 from the Pi on PERC 2 (`06 00`) with PERC 2 also selected on the device; the bridge selects the track first, so whether the track byte or the device's selected track counts is still 🟡 | ✅ |
| `77 01 21` | → | `[track] [pattern]` | **Paste** into that pattern: notes **and the pattern length** are copied, the target's old content is replaced; the device reports the new length (`30 56 18 00 20`). Other tracks untouched (KICK checked) | ✅ |
| `77 01 24` | ← | `00 00` | ❓ seen when the pattern editor changed page | 📥 |
| `77 01 10 [x] 00 [step]` | ← | | A step key is held on the device | 🟡 |

## 2. Song mode (`71`)
| Address | Dir | Data | Meaning | Status |
|---|---|---|---|---|
| `71 00 00` | → ← | `[scene]` | **Add a scene** in slot `scene` (0–15); the selected scene is copied (guide §13.3). The device sends the same when you press an unlit scene key (2026-10-14 Pi capture) | 📱 |
| `71 20 00` | ← | `[scene]` | **Delete a scene** ([DELETE] + red scene key, guide §13.4): deleting scenes 6, 5, 4 sent `71 20 00 05`, `… 04`, `… 03`. ❓ untested as a command | 📥 |
| `71 10 00` | ← | `[scene] [len hi] [len lo]` | **Scene length** ([PAGE] + [ALL] knob, §13.5.2): one message per knob click, e.g. scene 1 went `00 01` … `00 21` and back; `00 00` = **AUTO**. Value = **bars**: one bar up on the device (Ace, 23:56) went `00 01` → `00 02`. Range **AUTO (`00 00`), 1–96 bars**: turned to the end, the Seqtrak stopped at `00 60` = 96 (2026-10-15 00:00). ❓ whether it works as a command | 📥 |
| `71 40 [scene]` | read / ← | `[len hi] [len lo]` + 11 bytes; no data = empty slot | **Scene contents**: the scene length (same value as `71 10 00`, `00 00` = AUTO — confirmed by readback 2026-10-14: scene 1 `00 01`, scene 2 `00 00`) then one pattern number per track (0-based, KICK … SAMPLER) | ✅ |
| `71 [10+t] 01` | → read | `[scene] [pattern]` | Set track t's pattern in a scene | 📱 |
| `71 [10+t] 02` | → read | `[scene] [0/1]` | Mute track t in a scene | 📱 |
| `71 10 03` | → read | `[scene] [track 1–11, 0 = off]` | Solo one track in a scene | 📱 |
| `71 10 04` | ← read | `[scene]` | Current scene; follows playback | 📥 |
| `71 10 05` | ← | `[scene]` | **Next scene** (queued: pressing a scene key while playing; it starts when the current one ends, §13.2.1) | 📥 |
| `71 10 07` | ← read | `0/1` | **Scene loop** on/off (double-tap a scene key while playing, §13.2.2) | 📥 |
| `01 10 29` | ← | `00` | Sent each time a scene ends and the next (or the same, looping) starts — a scene-boundary tick | 🟡 |
| `71 10 06` | → read | `0/1` | **Whole-song loop** on/off (the app's SONG loop button, guide §13.2.3; SG-25/26: `01` on, `00` off) | 📱 |
| `71 50 00` | ← read | `0/1` | 🟡 **Scene mode** on/off. Every [ALL] + [PROJECT↑] into Scene mode sent `01`; leaving it sent `00`, followed by `01 10 17` = `02` (back to Song) or `00` (out of Song mode). Earlier read as "scene-key flag" | 🟡 |

## 3. Device state (`01 10`, `01 00`, `00 60/61`)
`01 10` is shared state; `01 1p` (p = 1…A) repeats some of it per track, and `01 1[e]` per sampler pad (see §4).

| Address | Dir | Data | Meaning | Status |
|---|---|---|---|---|
| `01 00 00` | read | `01 02 01 03` | Firmware version (the app showed 1.21.3) | 🟡 |
| `01 00 04` | read | `01` | ❓ | 📥 |
| `01 10 00` | ← read | `00` | Ends the burst after a project delete and after the Seqtrak (re)connects; never seen otherwise unless requested. The bridge re-reads everything on it | 🟡 |
| `01 10 01` | → ← | `0/1` | ❓ written by the app on the PROJECT/SOUND MANAGER page | 📱 |
| `01 10 03` | → | `00` off, `01` 5 min, `02` 10, `03` 15, `04` 30, `05` 60, `06` 120 | **Auto power off** | 📱 |
| `01 10 09 / 0B / 0D / 0F / 11 / 13` | read | 2 bytes each (e.g. `0F 19`, `06 66`) | 🟡 memory meters on the PROJECT/SOUND MANAGER page | 📥 |
| `01 10 15` | ← read | `[project 0-7]` | **Current project, 0-based** (project 8 = `07`). Sent by the Seqtrak on its own when the project is switched on the device (14:29: `07` → `00`, and it was the only project message). The bridge re-reads everything when it changes | 📥 |
| `01 10 16` | read | ~88 bytes, zeros | ❓ (project name? empty in this project) | 📥 |
| `01 10 17` | ← read | `00` normal, `02` song | **Song mode state**; also re-sent at the start of a project load. Scene mode is `71 50 00` on top of Song mode, not a value here. ❓ whether sending it switches the mode | 🟡 |
| `01 10 18` | ← read | `00`, `03`, `08`, `13`, `15`, `16` | Device display mode (`03` step held, `08` micro timing shown, `00` normal; others ❓) | 🟡 |
| `01 10 19` | ← | `00` idle, `03` step input, `04` Delete held | Device UI mode | 🟡 |
| `01 10 1F` | → ← | `01` | **[UNDO/REDO] button**: the Seqtrak sends it when the button is pressed, then reports the restored value (as the knob's CC). Sending it from the Pi toggled undo/redo of the last sound/effect change (2026-10-14: KICK attack CC 73 went 64 → 109 → 64). Guide §9.4 | ✅ |
| `01 10 20` | → ← | `01` / `00` | **Play / Stop** | 📱 |
| `01 10 21` | → ← | `01` / `00` | **Record on / off** | 📱 |
| `01 10 27` | ← read | `00`, `09` | ❓ | 📥 |
| `01 10 28`, `01 10 29`, `01 10 2A` | ← read | small values | ❓ | 📥 |
| `01 10 2D` | ← | `01 01`, `04 04`, `00 00` | UI state around device edits | 🟡 |
| `01 10 2E` | ← read | `01`, `03`, `06`, `09`, `11` | Display indicator (`09` = volume display) | 🟡 |
| `01 10 2F` | → | `01` | ❓ written by the app on the PROJECT/SOUND MANAGER page | 📱 |
| `00 60 06` | → read | 2 ASCII bytes ("US") | Wi-Fi country (HARDWARE page) | 🟡 |
| `00 60 00`, `00 60 01`, `00 61 02` | read | `00` | ❓ other HARDWARE settings (Wi-Fi mode?) | 📥 |

> **Knobs on the device are reported as CCs**, not SysEx: turning a Sound Design knob on the Seqtrak sends the
> same CC as the guide's table (§18.3.1) on the track's channel (e.g. KICK attack = CC 73, ch 1). An undo/redo
> sends the restored value the same way. ✅ (Pi capture 2026-10-14)

## 4. Per-track and per-pad state (`01 1p`, `01 1[e]`)
| Address | Dir | Data | Meaning | Status |
|---|---|---|---|---|
| `01 1p 30` | → ← read | `00`–`04` | GUIDE panel page shown for track p | 📱 |
| `01 1p 33` | read | `[bank LSB] [program]` | 🟡 **current sound of track p** (KICK: `20 51` = the "TS_RNB_kick_rnb" the picker selected with bank LSB `20`, program `51`) | 📥 |
| `01 1p 35` | read | 7-bit packed text | **Current sound name** of track p ("TS_RNB_kick_rnb", "LO-FI SOUL 1 BASS 01") | 📥 |
| `01 1p 36`, `01 1p 39`, `01 1p 3C` | read | small values; `3C` never answered | ❓ read when a track is selected | 📥 |
| `01 1p 50 / 51 / 52`, `01 1p 56 / 57 / 58` | → ← | small values | App page / sub-tab state, echoed by the Seqtrak | 📱 |
| `01 1p 53 / 54 / 55`, `01 1p 5C / 5D / 5E` | → read | | 🟡 the device's FX-knob mapping for the track effect (written by the overview DRY/WET slider and the MAP popup) | 📱 |
| `01 1[e] 40` | read | 4 bytes, 7 bits each | 🟡 **Sample length in frames** of pad e+1: pad 1 21,360, pad 2 94,256, pad 7 35,573. The End Point maximum is exactly 17 less on all three | 📥 |
| `01 1[e] 46` | read | 7-bit packed text | **Sample name** of pad e+1 ("Female Count 1", "Singing…") | 📥 |
| `01 10 44`, `01 10 47` | read | `00 00`, `00` | ❓ read by the sample picker | 📥 |

⚠️ `01 1x` is numbered by **track** for `30–3C`/`5x` but by **sampler pad** for `40`/`46` (pad 1 = `01 10`, pad 7 = `01 16`), so `01 16 40` is pad 7, not PERC2.

Text encoding (`35`, `46`): Yamaha 7-bit packing, groups of 8 bytes = one byte of high bits + 7 characters.

## 5. Bulk transfers outside the official block table
Format: request `F0 43 20 7F 1C 0C [H M L] F7`; reply pages `F0 43 00 7F 1C [count hi lo] 0C [H M L] [total pages hi lo]
[page hi lo] [data] [checksum] F7`; the app acknowledges every page with a bulk message to **`01 22 00`** carrying
`[H M L] 00 [page] 00 00`.

| Address | Pages | Meaning | Status |
|---|---|---|---|
| `0B 00 00` | 1 | 🟡 project list (PROJECT/SOUND MANAGER, project-name popup) | 📥 |
| `0C [type] [cat]` | 1–8 | 🟡 **sound list**: type `0x` = drum / synth / DX (`00`/`01`/`02`), `1x` = category list (KICK `0C 10 00`, SYNTH 1 BASS `0C 11 00`, DX `0C 12 01`); entries hold names and categories | 📥 |
| `0D [type] [cat]` | 0–2 | 🟡 **sample list** for the SAMPLER picker (RISER = `0D 02 04`, 2 pages) | 📥 |
| `10 01 03` | → | data `[bank LSB] [program] [0/1]` | 🟡 **favourite a sound** (the heart, toggled on/off) | 📱 |
| `01 40 00` | ← | `00 07` | ❓ sent once by the Seqtrak right after it reconnected (current project = 8?) | 📥 |

## 6. Official addresses used differently from their name
| Address | Data List name | What it actually controls in the app | Status |
|---|---|---|---|
| `00 00 2F` | Pattern Select Sensitivity | KNOB SENSITIVITY (`01` fast, `02` normal, `03` slow) | 📱 |
| `31 17 00` (SYNTH) / `31 19 01–02` (DX) | (parser unsure) / Carrier Attack/Decay Offset | the AEG DECAY / ATTACK knobs | 📱 |
| `41 eA 37` | AEG Release Time | the sampler's AEG **DECAY** | 📱 |
| `30 40 7F` | Key | value `40`–`4B` (our old docs said 0–11) | ✅ Data List range |

## Open questions (best next captures)
1. `70 5t` / `70 6t`: set a probability and a parameter lock on the device, then read both tables.
2. Song mode commands: does sending `01 10 17 02`, `71 50 00 01`, `71 20 00 [scene]`, `71 10 00 [scene] [len]` do the same as the device keys? Scene length unit.
4. Sample rate: record exactly 16 s and read `01 1[e] 40`.
5. `01 10 15`: switch to a few different projects on the device to confirm the value is always the project number.
