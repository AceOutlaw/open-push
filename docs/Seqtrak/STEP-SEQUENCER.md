# Seqtrak Step Data over SysEx — Authoritative Reference

**Status:** verified on hardware 2026-10-12 (Seqtrak key LEDs checked by the user, plus device readback).
**Read this first** for anything about steps. For what the device does (buttons, LED colours, modes),
grep Yamaha's user guide: `reference files/Yamaha/User Guide/SEQTRAK_user_guide_En_D0.txt` (local only;
online at https://manual.yamaha.com/mi/de/seqtrak/en/). Where older docs disagree, this file wins
(see "Corrections to older docs" at the bottom).

All messages are Parameter Changes `F0 43 10 7F 1C 0C [H] [M] [L] [data] F7` unless marked
Request (`F0 43 30 7F 1C 0C [H] [M] [L] F7`, the device replies with a Parameter Change).

---

## 1. Two storage models

| | Drum tracks 1–7 | Sampler + SYNTH 1 / SYNTH 2 / DX |
|---|---|---|
| Stored as | Fixed grid: one slot per step (0–127) | **Ordered list of notes** (position in ticks, pad/note, velocity, length) |
| Address of one item | step number | **note index** (0 = earliest note, list renumbers after a remove) |
| Read one item | Request `70 [40+t] [step]` → data if set, empty if not | Request `75 [g] [index]` → 8-byte note, empty = past end of list |
| Add | `70 [t] 00` + `[step] [note] [vel] 00 78` | `72 [g] 00` + 8-byte note (below) |
| Remove | `70 [20+t] 00` + `[step]` | **`74 [g] [index]` + `00`** |
| What the device sends when you edit on its keys | same as add / remove | add: `72 [g] 00` + note · remove: `74 [70+g>>4] 00` + note (**report only**) |

`t` = drum track − 1 (0–6). `g` = track group: **SYNTH 1 `00`**, SYNTH 2 `10`, DX `20`, **SAMPLER `30`**
(bold = verified; SYNTH 2 and DX follow the same pattern but are not yet verified).

### The 8-byte note (sampler / melodic)
```
[tick_hi] [tick_lo] 00 [note] [vel] 00 00 [length]
```
- **Position** = 14-bit tick `hi*128 + lo`, **120 ticks per step** (480 PPQN):
  step 1 = `00 00`, step 2 = `00 78`, step 3 = `01 70`, step 5 = `03 60`, step 6 = `04 58`, step 16 = `0E 08`.
- **Note:** sampler pad n (1–7) = `3C + n − 1`. Melodic = MIDI note.
- **Length** = last two bytes, 14-bit ticks (`hi*128 + lo`): `00 78` = 120 = one step, `05 50` = 720.
  **The Seqtrak stops the sample when the note ends** — `00` is silent, 119/120 cut a sample after one
  step (including notes from the Seqtrak's own Step Input), 720 let it ring out (verified by ear 2026-10-12).
  The bridge gives each Push step a length up to just before that pad's next step, or 4 bars if none,
  and shortens/re-extends the pad's previous step itself when steps are added or removed.

## 2. Verified behaviours (2026-10-12)

1. **Add** `72 30 00 01 70 00 3C 64 00 00 78` → pad 1 step 3 lit. No reply.
2. **Add at an occupied position replaces** the note; the device reports the old one with `74 73 00 …`.
3. **A note that reaches the next note on the same pad removes that next note** (device reports it
   with `74 73 …`). With length `78` (a full step), adding step N removes step N+1. Length `77` doesn't.
4. **`74 73 00` + note (the device's own report) is NOT accepted as a command** — tested exact bytes,
   and wrapped in the device's own edit messages (`01 10 2D 06 06` … `01 10 2D 01 01`, byte-for-byte
   what the device emits on a key press). Key stayed lit every time.
5. **Readback works:** `75 30 00`, `75 30 01`, … return the notes in time order; e.g. with pad 1 step 3
   and pad 2 step 6 set: `75 30 00 → 01 70 00 3C 64 00 00 00`, `75 30 01 → 04 58 00 3D 64 00 00 00`.
6. **Remove works:** `74 30 [index] 00`. With notes at steps 2, 5, 9: `74 30 02 00` removed step 9,
   then `74 30 01 00` removed step 5, then `74 30 00 00` removed step 2 (LEDs and readback agree).
   ⚠️ `74 30 00 [n]` (index in the *data*) always removes note #0 — the index belongs in the address.
7. **SYNTH 1** (g = `00`): add, readback `75 00 [index]` and remove `74 00 [index] 00` all verified.
8. **Clear a whole track:** `01 [10+t] 37 00` (device: hold Delete + press the track knob). Verified on
   the sampler (`01 1A 37 00`) — cleared all pads. ⚠️ It clears the variation **shown on the Seqtrak**,
   not the one selected over MIDI with `30 5p 0F`: with the sampler switched to V2 over MIDI, the clear
   emptied V1 and left V2. Readback (`75 g`) and remove (`74 g`) do follow the MIDI-selected variation,
   so the bridge clears by reading the list and removing every index.

To remove "pad p, step s": read `75 [g] 00, 01, …` until an empty reply, find the note whose position
and note number match, send `74 [g] [index] 00`.

### Project load / delete (seen 2026-10-13, Pi capture)
- Deleting the project on the device (user guide §4.4: [PROJECT↑]+[DELETE]+Drum key; leaves one KICK
  step) made the Seqtrak broadcast the whole project: `01 10 17 00`, `01 10 27/1E/1A/1B/1C`,
  `01 1p 31 00` per track, master FX `30 43…46`, `31 2x`, `01 1p 30`, … ending `01 10 00 00`.
  No step data is in the burst. 🟡 `01 10 17` assumed to mean "project loaded" (only seen in this burst);
  the bridge re-reads everything 0.5 s after it. ❓ Not yet checked: does switching projects send the same?
- Delete on the device is bracketed by `01 10 19 04` (Delete held) … `01 10 19 00`; the bridge re-reads
  all steps when Delete is released, since not every deletion is reported step by step.

### Live recording (verified 2026-10-13, Pi capture + readback)
- ✅ Steps entered on the Seqtrak's **step keys** are reported (`70 0t 00 [step] 3C 64 00 78`).
- ✅ Notes **recorded live** (Record on, played from Push pads or Seqtrak keys) are **not reported at all** —
  the capture showed only `01 10 21 01/00` (record on/off) around them. Stop while recording also sends
  `01 10 21 00`.
- ✅ The recorded notes **are stored** and read back normally with `70 4t [step]`, e.g.
  `70 40 06 → 3C 64 00 3C 00 30`. So a bridge must re-read to see them (the bridge re-reads the
  visible track ~1/s while recording and all tracks when recording ends).
- 🟡 **Drum readback = `[note] [vel] 00 [?] [len_hi] [len_lo]`** — the last TWO bytes are one 14-bit
  **note length in ticks**, same as the sampler. Evidence (2026-10-13 test: KICK played in, SNARE step-entered):
  step-entered notes are always `00 78` (120 = one step, and the drum add command ends in the same `00 78`);
  played-in notes vary with how long the key was held: `00 30`…`00 50` (48–80), `00 7A` (122), `01 06` (134).
  134 is outside micro timing's −60…+59 range (§6.3), so it isn't micro timing.
- ✅ **The 4th byte is micro timing: value = 60 + offset in ticks** (`3C` = on the grid; range −60…+59,
  §6.3). Verified 2026-10-13: user shifted SNARE steps on the device; readback and the device's reports
  agree: step 5 `6C` (+48), step 7 `0E` (−46), step 13 `6B` (+47), untouched step 15 `3C`.
- ✅ The device reports micro timing edits live: **`70 [10+t] 00 [step] [60+offset]`** (one message per knob
  click). ❓ Not yet tested whether sending it works as a command.
- 🟡 Holding a lit step key on the device sends `77 01 10 01 00 [step]`, then display mode `01 10 18 03`;
  turning the knob switches to `01 10 18 08` (micro timing shown); release → `01 10 18 00`.
  `01 10 2E 31/0A/03` accompany these (the blinking indicator). Meanings beyond that are unconfirmed.
- ✅ **Substep (§6.4) is the 3rd byte** (`00` = none). Verified 2026-10-13: user set substeps on SNARE
  steps 5, 7, 13, 15 and KICK step 12; readback 3rd byte = `02`, `04`, `02`, `01`, and the device reported each
  edit as **`70 [10+t] 03 [step] [value]`** with the same values. ❓ Value → option mapping (guide options:
  none, ×2, ×3 8th-triplet, ×3 16th-triplet, ×4) not yet matched to what was chosen on each step.
- So the device's per-step edit report is `70 [10+t] [param] [step] [value]`: param `00` = micro timing,
  `03` = substep, `04` = probability.
- 📱 **The SEQTRAK app sends these same messages to edit a step** (2026-10-14 click-through, block 104-03,
  `APP-CLICKTHROUGH-P1.md`), so they are commands, not only reports. Readback after a Push write not yet done.
  - Substep values: `00` none · `01` ×2 · `04` ×3 8th triplet · `02` ×3 16th triplet · `03` ×4
    (so the SNARE steps above were ×3 16th, ×3 8th, ×3 16th, ×2).
  - Probability `70 [10+t] 04 [step] [v]`: `00` = 100 %, `01` = 87 %, `04` = 49 %, `07` = 10 % (8 levels).
  - ❓ The app also reads `70 [50+t] [step]` (never answered) and `70 [60+t] [step]` (`00` on every set step) —
    probability may be stored in `70 6t`; check by reading it after setting a probability.
- So the full drum readback is **`[note] [vel] [substep] [60+micro] [len_hi] [len_lo]`**.
- ❓ Velocity byte read `64` (100) on every note so far; soft/hard Push pad hits not yet tested.
- 📖 **Purple step keys = Parameter Lock** (user guide §9.2, p. 64). The guide also says a VOLUME
  parameter lock changes the note's velocity — so live-recorded velocity is probably stored as a
  parameter lock, which would explain why recorded steps light purple. ❓ Where parameter locks live in
  SysEx is not yet known.

## 3. Other addresses found by the read sweep (meaning unknown)
- `75 [00–3F] [00–7F]` all answer; only `75 [g] …` with g = 00/10/20/30 has held data so far.
  The low nibble of the middle byte may extend the index beyond 127 or select a variation — untested.
- `71 10 00` (empty), `71 40 [00..]` (26 bytes, e.g. `00 00 01 01 … 01 00 …`), `71 50 00 → 00`, `77 01 00 → 00`.
- `01 10 19 xx` = device UI mode (03 step input edit, 04 Delete held, 00 idle); `01 10 2D` / `01 1p 39`
  = UI state broadcasts around edits. Not needed to make edits work.

## 4. How this was found (so it isn't lost again)
- Dec 2025: drum add/remove were found by replaying device captures — that works for drums because
  the drum remove message is also the command. The same replay failed for the sampler and the
  investigation stalled (`docs/dev-notes/SAMPLER_DELETE_*.md`). Those tests also sent wrong positions
  for every step except step 1 (128 instead of 120 ticks per step).
- Oct 2026: a read-only Request sweep of the unexplored `71`–`7F` ranges found `75 [g] [index]` answering
  with the note list. Seeing that notes are addressed by **index** led to `74 [g] [index]`.
- Lesson: a message the device *sends* may be a report, not a command. Verify every command with
  readback or the device LEDs.

## 5. Corrections to older docs
- `docs/Seqtrak/sysex-protocol-reference.md`: sampler remove `72 50 00 [tick]` is **wrong** (never worked);
  the "[step] [tick_pos]" tables are wrong (it is one 14-bit tick); "74 = SYNTH/DX command" is wrong
  (`74 [g] [index]` is remove for every melodic/sampler group, `74 7x` is the device's report).
- `docs/dev-notes/SAMPLER_DELETE_FIX.md`: the `72 50 00` "fix" never worked.
- `protocol.py` `send_sampler_delete` / `send_melodic_delete` (used by the delete menu) use the wrong
  messages — to be replaced with `74 [g] [index] 00` / `01 [10+t] 37 00`.
