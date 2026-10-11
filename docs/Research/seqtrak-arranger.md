# Seqtrak Arranger: Prepare Sets Off the Device

**Goal**: Prepare a full performance away from the device. Arrange all 8 project
slots on a computer, with variations, sounds, song chains and samples cut to
tempo, then load them onto the Seqtrak and play the set without setting
anything up live. Projects are stored as a library on the computer, so
there's no limit of 8 slots.

**Inspiration**: field-arrange (`~/CascadeProjects/field-arrange`), which does
this for OP-1 Field tapes. It reads a tape copied off the device, edits it on
four lanes and exports a tape folder to copy back with Field Kit.

**Status**: Feasibility discussion only (2026-10-04). Nothing built yet.

---

## The Seqtrak works differently from the OP-1 Field

| | OP-1 Field | Seqtrak |
|---|---|---|
| Music stored as | Long audio timeline (tape) | Loops: 11 tracks × 6 variations, Pattern (drums) / Bar (melodic) |
| Song structure | The tape *is* the song | Song mode chains variations (NORMAL / SONG / SCENE) |
| Slots on device | Limited tape slots | 8 projects |
| Moving data on/off | Field Kit, file-based | Seqtrak app (Mac/Win/iOS) backup and restore. **Only works with the device connected** |
| Format documented? | Reverse-engineered (`docs/op1-field-tape-format.md` in field-arrange) | **No.** Yamaha doesn't publish the backup format |

A Seqtrak arranger therefore arranges the device's structure: which variation
each track plays, the song chain, sounds and samples. It doesn't place audio
clips on a timeline.

---

## Three ways to build it

1. **Offline project editor (the main goal).** Read a project, edit it on the
   computer, write it back and restore it to a slot. Fits "have the set ready
   and just play it" best.
2. **Live conductor.** The arrangement lives on the Mac or Pi, which follows
   the Seqtrak's MIDI clock and sends variation and mute changes at bar
   lines. It can do more than Song mode (different variations per track,
   per-section mutes, tempo and parameter changes) and works with the SysEx
   we already have. Push pads could serve as the arrangement grid.
   Untested: whether variation switches land exactly on the bar.
3. **Seqtrak as a sound module.** Turn its sequencer off and play MIDI clips
   from a timeline. Possible, but it duplicates what any DAW already does.

Options 1 and 2 can be combined: prepare the projects offline, then let the
conductor run the set live.

---

## How to get to the offline editor

### Key point: the app is the protocol documentation

The desktop and iPad apps can't edit anything while the Seqtrak is
disconnected. So everything they do (backups, restores, sound edits, sample
loading) travels over USB MIDI. Anything the app can do, we can do once we
capture it.

### What's already decoded

`docs/Seqtrak/sysex-protocol-reference.md` was built from MIDI Monitor captures
of single edits:

- Step **write and delete** for drum, synth/DX and sampler tracks (`70` / `74` / `72`)
- Track parameters, sound engine (`31 xx xx`), effects (`41 xx xx`), arp/motion (`50 xx xx`)
- Variation select, mute, tempo and other globals

Still open (line ~1431): effect type selection, pattern copy/paste,
sample start/end points, motion sequence format, custom preset names.

### What hasn't been captured: a full backup and restore

- **Backup** = the app reads the whole project off the device. That's the
  read path we're missing, probably the Dump Request messages
  (`F0 43 2n 7F 1C 0C ah am al F7`) from Yamaha's MIDI Data Format.
- **Restore** = the app writes the whole project back in one stream.

**Update (2026-10-04), from the V2 Data List** (converted to Markdown in
`reference files/Yamaha/Seqtrak Data List V2/md/`, Bulk Dump Block on pp. 120–121):
Yamaha documents the full project bulk dump format. Header `11 mm nn` /
footer `12 mm nn`, where nn = project slot 0–7 for User projects. It covers
project settings, sends and master effects, scale, track settings, sounds,
DX operators and sampler sample settings. It **does not list pattern or step
note data.** The sequence data (our `70`/`72`/`74` commands) is undocumented,
so it either travels outside the documented blocks or isn't in the dump at
all. A capture of the app's backup will tell us which.

With both captured, we'd have every part of a project (variations, sounds,
effects, mixer, song chain) in Yamaha's own order. The editor could then
either generate its own restore stream or write a backup file that the
official app restores.

### Methods

1. **Capture and compare.** Back up a project, change one thing on the
   device, back up again, and compare. Repeat once per feature. Scripted
   rather than done by hand.
2. **Inspect the desktop app.** Look in the Mac app bundle for resource files
   and strings: parameter tables, address maps, preset names. This could fill
   in a lot of the map without capturing anything. (Check the app's license
   before publishing anything taken from it.)
3. **Inspect the backup file itself.** Compare a backup of one project with a
   backup of the same project after one step is changed. The result tells us
   whether the format is:
   - **Best case:** zip, JSON or XML. Straightforward to edit.
   - **Likely case:** a binary block that lines up with the addresses in
     Yamaha's MIDI Data Table, which we've partly mapped. Doable.
   - **Worst case:** encrypted or signed. Fall back to generating restore
     streams ourselves, or to MIDI file import (needs the 2.0 app).

**First tool to build**: a decoder for MIDI Monitor exports. It turns
captured SysEx into address/value tables using what's already decoded, and
compares two captures so each session immediately produces a list of new
addresses.

---

## Sample tracks: tempo prep

**Problem**: The Seqtrak has **no time-stretching**. A longer sample (a loop,
a vocal phrase, a stem) only lines up with the project if it was cut to that
tempo before loading. The factory content treats the sampler as one-shots, so
the sample tracks are mostly underused.

**This part doesn't need any reverse engineering.** It's offline audio
processing, and field-arrange already has WAV I/O we could reuse:

- Time-stretch each sample to the project's BPM, keeping the pitch
- Trim and pad to exact bar lengths so loops repeat cleanly
- Slice loops onto pads; normalize and fade edges to avoid clicks
- Preview against the project's tempo before loading
- Load the results with the app's user-sample import

Check sampler limits before building: maximum sample length, total sample
memory, and the sample rate and format the import accepts. These are in the
user guide and haven't been confirmed here. Firmware 2.0 adds **sample
looping with loop points**, which makes longer samples much more useful.

This piece works on its own and could be the first thing to ship.

---

## Firmware: V1 vs V2

**OS 2.0** (released 2026-01-14) adds:

- Drum tracks can be converted to AWM2 synth tracks, or combine multiple kits
  in one track
- Sample looping with loop points, per-slot sample mute
- Bar length control on drum tracks, smooth muting, count-in recording, global knob functions
- App 2.0: better backup, MIDI file import and export

**Risks**:

- Yamaha says data saved on 2.0 may not work on older firmware. Downgrading
  isn't documented (the V1.21 updater is still on Yamaha's Europe site, but
  rolling back is unconfirmed).
- open-push's SysEx map was captured on 1.x. **Update (2026-10-04):** a
  comparison of the V1.20 and V2.00 Data Lists found that **no documented
  address moved**. V2 only adds DrumKit Bank Selects (MSB 32–38), allows
  chord and arpeggiator blocks on drum parts, and adds new drum knob pages
  (see `reference files/Yamaha/Seqtrak Data List V2/compare/V1-vs-V2.md`).
  What's still untested is what the doc doesn't cover: step data
  (`70`/`72`/`74`, especially for drum tracks converted to Synth type) and
  UI/state addresses (`01 1x xx`).

**Decision**: Keep the current unit on **1.x** and don't update the desktop
app either (unknown whether the 2.0 app works with 1.x firmware). The 1.x app
already does backup and restore, so the work can start now.

**Plan: buy a second Seqtrak** as a dedicated V2 test unit:

- The current unit stays the safe performance unit on V1
- Compare V1 and V2: same SysEx and same project on both, then compare the
  results to get both address maps
- A spare for a device that's central to the setup
- Buy soon: shops have discounted it by up to 50% and users report
  shrinking supply. Yamaha says it isn't discontinued.

**Before ever updating a unit**: back up all 8 projects plus user
samples and sounds; keep copies of the V1.21 updater and the current app
installer; ask Yamaha whether downgrading is supported; record a SysEx
baseline session on 1.x.

**In open-push**: the Seqtrak answers the standard MIDI identity request
(`F0 7E 0n 06 01 F7`). If the reply includes the firmware version
(unconfirmed), the bridge and arranger can choose the V1 or V2 address map
automatically.

---

## Suggested order

1. **Sample prep tool**: time-stretch, trim and slice. No unknowns, useful
   right away.
2. **Capture decoder and comparison tool** for MIDI Monitor exports.
3. **Capture session** on the V1 unit: backup and restore of one project,
   plus one-change backups.
4. **Decide the format path** (edit backup files vs. generate restore streams).
5. **Arranger UI** for 8 project slots, variations, song chain and samples.
6. **V2 support** once the second unit arrives.
7. Optional: **live conductor** on the Pi with Push.

---

## Sources

- [SEQTRAK App for Windows V2.0.0 – Yamaha USA](https://usa.yamaha.com/support/updates/seqtrak_app_win.html)
- [SEQTRAK App for Mac V2.0.0 – Yamaha](https://ch.yamaha.com/de/support/updates/seqtrak-app-mac.html)
- [SEQTRAK OS Updater V2.00 – Yamaha Asia/Oceania](https://asia-oceania.yamaha.com/en/support/updates/seqtrak-os-updater.html)
- [SEQTRAK OS Updater V1.21 – Yamaha Europe](https://europe.yamaha.com/en/support/updates/seqtrak-os-updater.html)
- [Blake's Take: SEQTRAK OS v2.0 – YamahaSynth](https://yamahasynth.com/learn/seqtrak/blakes-take-seqtrak-os-v2-0/)
- [Synth Anatomy – SEQTRAK firmware 2.0](https://synthanatomy.com/2026/01/yamaha-seqtrak-new-groovebox-with-sampler-and-synths.html)
- [Yamaha Seqtrak 2.0: What's New (And What's Missing) – Sunwarper](https://www.sunwarper.com/post/yamaha-seqtrak-2-0-update-what-s-new-and-what-s-missing)
- [Discontinuation discussion – YamahaMusicians](https://yamahamusicians.com/forum/threads/is-that-normal-to-release-new-os2-0-discontinue-seqtrak.23770/post-144621)
- [SEQTRAK User Guide (PDF)](https://data.yamaha.com/files/download/other_assets/9/2227389/SEQTRAK_user_guide_En_D0.pdf)
- Local: `docs/Seqtrak/sysex-protocol-reference.md`, `docs/Seqtrak/midi-data-format.md`,
  `docs/Seqtrak/IMPLEMENTATION-GAP-ANALYSIS.md`
