# One Idea, Anywhere: Interoperability and What to Do First

*Written 2026-10-24, after a session that went from the Ableton Move's architecture to DAWproject, the
Seqtrak's `.Y3P` file and OP-1 Field tapes. Purpose: put every thread in one place, then pick one.*

## The goal underneath everything

**An idea started on any instrument can move to wherever it's needed next**: performed on the rig, or opened in a
DAW to finish. Start a beat on the Seqtrak, perform it from the Push. Record a tape on the OP-1 Field, open it
in Bitwig. Sketch on the Push, take it into Cubase.

The instruments all store music differently, but underneath it's the same few things: **tracks, clips, notes
in beats, audio, tempo**. That's why it keeps looking possible: it is. It needs one shared model in the middle
and a converter per instrument around it.

```
  Seqtrak (.Y3P file, or read live)  ─┐
  OP-1 Field (tape folders)          ─┤                           ┌─►  DAWs: Bitwig, Cubase, Cubasis
  Push / Pi sequencer (our own song) ─┼──►  the song model  ◄─────┤     (.dawproject)
  Orchid (live MIDI only, no file)   ─┘     tracks · clips ·      └─►  the performance rig
                                            notes · audio · tempo       (Pi sequencer → devices)
```

The model is DAWproject-shaped (`experiments/dawproject/`): it opens in the DAWs as is, and our own JSON uses
the same structure plus a section for hardware routing.

## Every thread, where it stands

| Thread | What it gives | Where it stands | Next step | Notes |
|---|---|---|---|---|
| **Seqtrak bridge** (today's rig) | Push controls the Seqtrak | Working; **28 features built but not yet tested by hand** (Linear "In Review"); Pi 3 fixes behind | Hardware test session | `docs/Seqtrak/HARDWARE-TEST-v1.md`, KM-100 |
| **Bridge architecture** | Modules, runs as a proper program, no Seqtrak required at startup | Designed | KM-270 (packaging) first | `bridge-architecture.md`, KM-244, KM-268–271 |
| **Song model + DAWproject** | The middle of the diagram | Writer and parser done; Bitwig and Cubase open our file with notes and scenes intact | Re-export test (do devices survive?) | `experiments/dawproject/` |
| **OP-1 Field → DAW** | Tapes open in a DAW | Tape format fully decoded in field-arrange | One converter, about one session | `field-arrange/docs/op1-field-tape-format.md`; field-arrange isn't in git yet |
| **Seqtrak → DAW** | Seqtrak projects open in a DAW | File container and drum steps partly decoded; melody notes not | ~25 exports (`Y3P-EXPORT-PLAN.md`), or read live over MIDI | `Y3P-PROJECT-FILE.md` |
| **Pi sequencer** | The Pi keeps time; Seqtrak, Orchid etc. become sound modules | Idea | Timing test on pibridge (jitter) | Conversation 2026-10-24; not yet in a doc |
| **Orchid chord bridge** | Push plays the Orchid's chords | Planned | KM-234 | KM-233 |
| **Standalone instrument** | Push + Pi + audio HAT + own engine | Research | Pad-to-sound latency test | `standalone-instrument.md`, KM-243 |
| **Other hardware** (Maschine, TempoPAD) | Second life for more controllers | Maschine mapped on macOS; TempoPAD mapped | Pi port / SWD probe | `docs/Maschine/`, KM-261–267 |
| **Seqtrak arranger** | Offline set arranging | Parked | — | `seqtrak-arranger.md` |

## Why it feels like everything at once

Each thread is viable, and each one is small next to the whole. But most of them depend on the **same middle
piece**, the song model and its DAWproject converter. Working on five threads means building that piece five
times, partly. Finishing one path end to end builds it once, and the others reuse it.

## Picking one

*Revised 2026-10-25 after reading the repo and Linear.*

**First: finish the Seqtrak bridge as v1.0.** It's the main project and nearly done, but nothing in it is
marked finished: 28 features (every KM-100 fix, Song mode, micro timing, probability, substeps, copy/paste,
undo, metronome, project switching) are built and verified from the Pi but have never been tried by hand. No
code has changed since 2026-10-18; the days since went to research. Finishing means:

1. Deploy the current commit to pibridge (it's 3 fixes behind).
2. One test session with `docs/Seqtrak/HARDWARE-TEST-v1.md`.
3. Fix what fails, plus KM-126 and KM-128.
4. Tag `v1.0`.

**Then, one at a time:**

| Order | Thread | Why then |
|---|---|---|
| 2 | Stability: non-blocking reads, atomic saves (KM-254, KM-255) | Freezes and corrupt files hurt on stage, and the Pi runs on a battery |
| 3 | Run as a proper program (KM-270) | Small, and the base for the modular bridge |
| 4 | One converter: **OP-1 Field → DAW** | First interoperability thread: the format is decoded, about one session, and it builds the song model the others reuse |
| 5 | Seqtrak → DAW | Same output side; needs the `.Y3P` export session first |

The Pi sequencer, the Orchid, the standalone instrument and Maschine wait until after v1.0. Maschine's KM-261 is
still marked In Progress in Linear and should go back to Backlog.

## Rule for new ideas

When a new idea arrives: **one line in the parking lot below, then back to the current thread.** Not started,
not lost.

### Parking lot

- Pi sequencer with every device as a sound module; profiles (Seqtrak controller / Pi sequencer / generic MIDI).
- Who owns the clock: Seqtrak, or the bridge. Does the Orchid follow incoming MIDI clock? (❓ untested)
- DAWproject → OP-1 Field tape (the reverse direction).
- Bitwig HW Instrument export test: does a DAW write "this track plays hardware" into DAWproject?
- Seqtrak `.Y3P` writer: save projects from the Pi in the app's own format (KM-230, KM-232).
- Reason songs (`.reason`, closed binary format, not on the DAWproject list): bring them in through Reason's
  own exports (MIDI file + stems), not by decoding the file.
