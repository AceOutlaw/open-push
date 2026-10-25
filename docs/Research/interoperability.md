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
| **Seqtrak bridge** (today's rig) | Push controls the Seqtrak | Working, with bugs | Bug epic KM-100 | `docs/Seqtrak/` |
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

What to look for: **finished in days, not weeks**; **used in your own music right away**; **builds the shared
piece** the others need.

| Candidate | Days to a result | Used right away | Builds the shared piece |
|---|---|---|---|
| OP-1 Field → DAW | ~1 session: the format is already decoded | Yes: open real tapes in Bitwig/Cubase | Yes: first real converter into the model |
| Seqtrak → DAW | Weeks: needs the export session, then decoding | Yes, once it works | Yes |
| Pi sequencer | Weeks to months | Only once it's tight enough to perform with | Yes, but needs the model first |
| Seqtrak bridge bugs | Ongoing | Yes, it's the rig | No |

**Recommendation: OP-1 Field → DAW first.** It's the only path that ends in a working result in one sitting,
it puts real music through the song model, and it settles the DAWproject details (audio clips, mixer, markers)
before anything harder depends on them. **Seqtrak → DAW** is the natural second: same output side, only the
input is new. The Pi sequencer comes after both, when the model has carried real songs.

The exception: if a gig is coming, the rig wins, and the bridge bugs (KM-100) come first.

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
