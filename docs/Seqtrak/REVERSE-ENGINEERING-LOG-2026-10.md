# Seqtrak Reverse-Engineering Log — 2026-10-11/12

What we learned about the Seqtrak's MIDI/SysEx protocol in this session, how we learned it, and
what went wrong along the way. Protocol details for steps live in `STEP-SEQUENCER.md`; the
feature coverage map is `FUNCTIONALITY-MAP.md`.

Status key: ✅ verified on hardware · 🟡 observed, not fully verified · ❓ open

---

## 1. Discoveries

### State can be read, not just written
- ✅ **Parameter Request** `F0 43 30 7F 1C 0C [addr] F7` works for **any** address, including the
  undocumented `01 1x xx`, `70` and `75` ranges. The Seqtrak replies with a normal Parameter Change.
  The official app reads all its state this way (MIDI Monitor spy mode).
- ✅ The device **announces its own edits** (button presses, knob turns) as Parameter Changes, so a
  bridge can follow the Seqtrak as well as control it.

### Names, tracks, variations
- ✅ Patch name per track: request `01 1p 35` (p = track − 1). Reply is 110 bytes of Yamaha 7-bit
  packed ASCII (1 high-bit byte + 7 data bytes per group).
- ✅ Per-track pattern (variation) `30 5p 0F` (0–5) is readable and is reported when it changes.
- 🟡 `01 10 2A` = global variation indicator; `01 10 27` = selected track (sent when you change track
  on the device).
- ❓ 3/6-variation switch: the bridge writes `01 10 18`, but the device read `01 10 18 = 0` while
  Pattern Select Mode `30 40 79 = 1`. Not settled.

### Volume
- ✅ Speaker master volume `00 00 00` (0–127) is readable, and the Seqtrak's volume buttons report it.
  Headphone volume is a separate address, `00 00 01`.
- ✅ The Push 1 master encoder can drive it.

### Step data — the big one
- ✅ **Two storage models.** Drums are a fixed grid with one slot per step. Sampler, SYNTH 1, SYNTH 2
  and DX are an **ordered list of notes**, each with a position in ticks, a note, a velocity and a
  length.
- ✅ Drums: add `70 0t 00 [step] …`, remove `70 2t 00 [step]`, read `70 4t [step]`.
  - An empty slot answers with no data. A set slot answers `3C 64 00 3C 00 78`.
  - `70 6t` answers `00` on set steps. `70 5t` has not answered yet.
- ✅ Sampler and melodic tracks:
  - add `72 [g] 00` + 8 bytes `[tick_hi tick_lo] 00 [note] [vel] 00 00 [length]`
  - **read `75 [g] [index]`**
  - **remove `74 [g] [index] 00`**
  - **The index goes in the address.** `74 [g] 00 [n]` always removes note #0.
  - Group g: SYNTH 1 = `00` ✅, SYNTH 2 = `10` ❓, DX = `20` ❓, SAMPLER = `30` ✅.
- ✅ Positions are **120 ticks per step**: step 1 = `00 00`, step 2 = `00 78`, step 6 = `04 58`,
  step 16 = `0E 08`.
- ✅ **The last byte is the note length in ticks, not probability.**
  - `78` = 120 = a full step. A note that long reaches the next note on the same pad, and the
    Seqtrak removes that next note.
  - The device's own key presses use `00`.
- ✅ Adding at an occupied position **replaces** the note.
- ✅ When a note disappears (removed on the keys, replaced, or pushed out by an overlap), the device
  sends **`74 [70 + group] 00` + the note**. This is a **report only**: sending it back does nothing,
  even wrapped in the device's own edit messages.
- ✅ Clear a whole track: `01 [10+t] 37 00`. On the device this is Delete + track knob.
  - Around it the device sends `01 10 19 04` (Delete held) and `01 10 19 00`.
- ✅ The Seqtrak has **Step Input mode** for melodic tracks and the sampler: hold [PAGE] and press
  the track knob (manual §7.9).
  - The Seqtrak app has no step view for these tracks.
  - Edits made in this mode are wrapped in `01 10 19 03 … 00` and `01 10 2D 06 06 … 01 01`.
- 🟡 Other addresses that answer read requests, meaning unknown:
  - `75 [00–3F] [00–7F]` (only g = `00/10/20/30` has held data so far)
  - `71 10`, `71 40 [n]` (26 bytes), `71 50`, `77 01`
- ✅ Yamaha's official Data List documents bulk dumps of project and sound data, but **no pattern or
  step data**. The `70–77` ranges are undocumented internals.

### Push 1
- ✅ The Push 1 has a dedicated **Delete** button (CC 118). The bridge had been using Select (CC 48)
  for delete, which got in the way of normal use.

## 2. Methods that worked
1. **Spy mode in MIDI Monitor** ("Spy on output to destinations") shows what the official app
   *sends*, not only what the device replies.
2. **Three-way capture on the Pi** with `aseqdump -p 36:1,129:0,32:0` (Push in, bridge out,
   Seqtrak out), timestamped. Lining the three streams up shows cause and effect: Push press →
   bridge message → Seqtrak reaction. ALSA client numbers change when the bridge restarts, so
   check `aconnect -l` first.
3. **Read-only sweeps.** Fire Parameter Requests across a whole range, 3 ms apart, and collect the
   replies. They are safe because they cannot change anything. **This is what found `75`, and from
   it `74 [g] [index]`.**
4. **Independent ground truth** before concluding anything:
   - the Seqtrak's key LEDs, read by a person (the most trusted check)
   - readback (`70 4t`, `75 g`)
   - the replace probe: adding at a position draws a removal report only if that position was
     already occupied
5. **Offline replay:** feed captured bytes through the bridge's handler before deploying.
6. **One change at a time on a known state.** Clear the track first, then add one note, check it,
   remove it, check again.
7. **Recovering lost context:** the user's prompt history (`~/.claude/history.jsonl` on the machine
   where the work happened) and `docs/dev-notes/` held the December story. The pasted captures
   themselves were not kept.

## 3. Mistakes and what they taught
| What happened | Lesson |
|---|---|
| Dec 2025 and again today: we replayed the device's `74 73` removal and expected it to work | What a device **sends** may be a **report**, not a command. Verify every command against ground truth. |
| `SAMPLER_DELETE_FIX.md` presented `72 50 00` as "the fix", and the protocol reference called it verified. It never worked | Mark every claim ✅ verified or ❓ assumed. Never write "fix" before a hardware test. |
| The last byte was "probability" in the code and "duration" in an old doc | Vary **one field** and watch the effect, instead of guessing from names. |
| The December test scripts placed every step after step 1 at 128 ticks per step, and I hand-computed `04 58` as step 5 (it is step 6) | Compute positions in code. Never do hex arithmetic by hand. |
| The first index-remove attempt "worked" only because it targeted note #0. A cleanup check showed `74 30 00 [n]` always removes #0 | Confirm a success with a **second, different** case (here, index 2 then index 1). |
| The new sampler listener treated removal reports as real removals, flipping Push pads off after every add | Reports have side effects such as replace and overlap. Resync from readback; don't mirror reports blindly. |
| Tests ran on a dirty pattern: earlier tests had left steps behind, the device had a different pad selected, and it was in Step Input mode | Start each experiment from a known, cleared state, and note the device's mode and selected pad. |
| A 25-minute capture timed out before the user's test | Check that the capture is alive before asking the user to act. |
| `ssh pi 'pkill -f /tmp/x.py'` killed its own SSH session | Use `pkill -f "[x]"`-style patterns. |
| Context compaction erased what we already knew | Write findings to the repo and memory **immediately**, and read `docs/dev-notes/` and memory before experimenting. |

## 4. Open questions
- SYNTH 2 (`10`) and DX (`20`) groups: verify add, read and remove.
- `75 [g+1…F]` — variations, or the index above 127? `71`/`77` meanings.
- Does `01 [10+t] 37 00` clear only the current variation, or all of them?
- Drum readback bytes `3C 64 00 3C 00 78` and `70 5t`/`70 6t` meanings.
- Does a note's length change how a sample plays (one-shot vs gated)?
- The real 3/6-variation switch.

## 5. Device state left after testing
- Sampler: empty (cleared by the user, test notes removed).
- KICK: steps 1, 9, 13 from the drum test. SYNTH 1: empty in the current variation.
