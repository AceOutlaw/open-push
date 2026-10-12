# Seqtrak Step Data over SysEx — Authoritative Reference

**Status:** verified on hardware 2026-10-12 (Seqtrak key LEDs checked by the user, plus device readback).
**Read this first** for anything about steps. Where older docs disagree, this file wins
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
- **Length** (last byte) in ticks. `78` = 120 = one full step. The device's own key presses use `00`.

## 2. Verified behaviours (2026-10-12)

1. **Add** `72 30 00 01 70 00 3C 64 00 00 78` → pad 1 step 3 lit. No reply.
2. **Add at an occupied position replaces** the note; the device reports the old one with `74 73 00 …`.
3. **A note that reaches the next note on the same pad removes that next note** (device reports it
   with `74 73 …`). With length `78` (a full step), adding step N removes step N+1. Use length `00`.
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
