# `.Y3P` export plan: decoding the notes

**Goal**: read every note of every track and variation out of a SEQTRAK app export (`.Y3P`), so a project
can be converted to DAWproject and opened in Bitwig / Cubase (11 tracks × 6 variations → tracks × scenes
of clips). What's known so far: `Y3P-PROJECT-FILE.md`. Writer and parser for DAWproject:
`experiments/dawproject/`.

**What's missing** (2026-10-24):
- ❓ Patterns the SEQTRAK wrote itself: the drum-step rule (record = page + 0x0E + (n − 1) × 0x48) finds the
  hand-entered steps in `test project` but **no steps at all** in `random 1`, whose patterns play beats.
- ❓ Melody and sampler notes (SYNTH 1, SYNTH 2, DX, SAMPLER): bit-packed, not decoded.
- ❓ Pattern length, and which variation each track plays.

Method: the one that already decoded tempo, velocity, micro timing, substep and probability. **Pairs of
exports that differ by exactly one change**, compared with `python3 tools/y3p_diff.py before.Y3P after.Y3P`.

---

## Rules for every export

1. **One change per export.** Nothing else: don't select another track, pattern or project in between unless
   the step says so (selecting a pattern changes bytes too, e.g. `0x6D`).
2. **Before exporting, switch to another project in the app and back.** Otherwise the app exports its old copy
   and the file is unchanged (seen twice, 2026-10-18).
3. **Name the file with its number** and save it to `~/Downloads/y3p-exports/`, e.g. `07 SYNTH1 note step2.Y3P`.
4. **Write down exactly what you did** if it differs from the list (another note, another step), in a
   `notes.txt` next to the files.
5. Changes can be made on the SEQTRAK, in the app or from the Push. Whichever is easiest, as long as it's one
   change. Note which one you used.

**Base project**: delete project 8 (hold [PROJECT↑] + [DELETE], press Drum key 8; user guide §4.4). A deleted
project "will contain only one KICK step", so every other track and pattern starts empty. Tempo stays at the
default; don't touch it.

---

## A. Drums: structure (KICK, then SNARE)

| # | Change from the previous export | Answers |
|---|---|---|
| 00 | Base: project 8 just deleted | Starting point; where the one KICK step is |
| 01 | KICK pattern 1: turn **step 5 on** | Step record position in a fresh project |
| 02 | KICK pattern 1: turn **step 1 off** (step 5 stays) | What "off" looks like |
| 03 | KICK pattern 1: **bar length 1 → 2 bars** ([BAR LENGTH]) | Where pattern length lives; is bar 2 copied? (guide §5.2: new bars copy from bar 1) |
| 04 | KICK pattern 1: **length → 13 steps** (hold [BAR LENGTH] + turn KICK knob) | Length in steps, not just bars |
| 05 | SNARE pattern 1: **step 1 on** | Second track, same layout? |
| 06 | KICK **pattern 2**: step 1 on (select pattern 2 first) | Second variation; also logs the selection byte |
| 07 | Switch KICK back to **pattern 1** | Which byte says which variation plays |

## B. Melody: SYNTH 1, pattern 1

| # | Change from the previous export | Answers |
|---|---|---|
| 10 | SYNTH 1: **one note C4 (60) on step 1**, default length and velocity | The note record |
| 11 | Move that note to **step 2** | Position field |
| 12 | Change its pitch to **D4 (62)** | Pitch field |
| 13 | Make it **2 steps long** | Length field (one step = 120? the earlier export showed `00 78`) |
| 14 | Set its **velocity to 80** | Velocity field |
| 15 | Add a **second note, E4 (64), on step 5** | How records follow each other |
| 16 | Add **G4 (67) on step 5** (a two-note chord) | Two notes on one step |
| 17 | **Bar length 1 → 2 bars** | Melody pattern length |
| 18 | Add **C5 (72) on step 17** (bar 2, step 1) | Notes past bar 1 |
| 19 | Give the step-2 note **micro timing +30** | Same micro timing as drums? |

## C. Other melody tracks and the sampler

| # | Change from the previous export | Answers |
|---|---|---|
| 20 | SYNTH 2 pattern 1: one note C4 on step 1 | Same layout as SYNTH 1? |
| 21 | DX pattern 1: one note C4 on step 1 | Same for DX? |
| 22 | SAMPLER pattern 1: **pad 1** on step 1 | Sampler note record (pad number vs note) |
| 23 | Same note moved to **pad 2** | Which field is the pad |

## D. Ground truth for real projects

The bytes above decode a fresh project. Patterns the SEQTRAK made itself (demo projects, `random 1`) look
different, so they need a known answer to compare against:

| # | What | How |
|---|---|---|
| 30 | Load **demo project 1**, export it | The file |
| 31 | **Read every track and variation of the same project over MIDI** and save it as JSON | The bridge's verified step readback (`STEP-SEQUENCER.md`), from the Pi or a Mac. Needs a small capture script (not written yet) |

Matching the two shows how the stored form maps onto steps we already know how to read.

## E. Optional, later

- A step with a **parameter lock** (e.g. volume on KICK step 1), since step 1 looked different after a lock (`Y3P-PROJECT-FILE.md`).
- **Swing**, **track volume / mute** saved in the project.
- **Scenes / song**: the V1.20 user guide doesn't describe them (the OS 2.0 guide does), yet the
  2026-10-18 `random scene` export changed bytes around `0x4E00`. ❓ Check what the app offers on 1.21.3 first.

---

## After the exports

Each finding goes into `Y3P-PROJECT-FILE.md` with its status (✅ / 🟡 / ❓) and the file pair that shows it.
Then a converter (`experiments/dawproject/`) writes the project as DAWproject: tracks with MIDI channels 1–11,
variations as scenes, pattern length as the clip loop, sampler audio as WAV.
