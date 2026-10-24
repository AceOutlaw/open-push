# Standalone Instrument: My Own Push 3

**Goal**: An instrument I can play on its own: the Push 1 as the surface, a Raspberry Pi 4 as the
brain, an audio hat for sound, and my own sound engine. No computer, no DAW. That has been the goal of
open-push from the start; the Seqtrak bridge is one stop on the way.

**Why build instead of buy**: a Push 3 standalone or a Move would do much of this, but building it
teaches how instruments are made. The Move proves the platform works: it's a CM4 (the same chip as a
Pi 4) plus an audio/IO processor. It may not reach commercial quality; that's fine.

**Status**: Idea and research only (2026-10-24). Tracked in Linear as epic KM-243
*Standalone · My own Push instrument* (sub-issues KM-245 to KM-253). Nothing is ordered; backlog
refinement will prioritise.

See `how-instruments-are-built.md` for what was learned from Chase Bliss, teenage engineering,
CHOMPI and the Ableton Move.

---

## Three layers

| Layer | What it is | Where open-push is |
|---|---|---|
| **Control** | Pads, buttons, encoders, LCD, modes | The bridge already does this for the Push 1 |
| **Sound** | The engine that makes audio | Not yet; the Seqtrak plays the sound today. Jasmine (granular DSP on the Daisy) is the experience to draw on |
| **Platform** | Linux tuned for audio, audio hardware, power-safe storage | pibridge is a Pi 4 Model B (4 GB, Debian 13, kernel 6.12); not tuned for audio yet |

## What the platform needs (learned from the Move)

- **Audio hardware**: the Pi's headphone output isn't good enough. Candidates, all over I2S:
  - Pisound (Blokas): audio in/out, MIDI ports and a button.
  - HiFiBerry DAC+ ADC: good-quality stereo in/out.
  - Raspberry Pi Codec Zero: official and inexpensive.
- **Real-time tuning**: audio threads at real-time priority (`chrt`), pinned to their own core
  (`taskset` / `isolcpus`), everything else on the other cores. `PREEMPT_RT` is in mainline Linux since
  6.12 but not switched on in Raspberry Pi OS by default.
- **Read-only system** with a writable data area, so a battery cut can't corrupt anything.
- **Separate processes**: audio engine, control surface, settings/web UI, talking over a message bus,
  so a slow UI can't glitch the audio.
- **Later**: A/B partitions for safe updates.

## First milestone

Pi 4 + audio hat + a minimal engine (a simple sampler or synth) played from the Push pads. **Measure
the delay from pad hit to sound.** Under ~10 ms with nothing struggling means the platform works, and
everything after that is features. Build it on a spare SD card so pibridge stays a working Seqtrak rig.

## Open questions

- Which audio hat? Audio quality vs. MIDI ports vs. price.
- Engine: write my own (C++), host plugins (LV2, like Zynthian), or Pure Data (like Organelle)?
- Display: the Push 1 LCD is 4 lines of text. Is that enough, or does it need a small screen,
  a phone/tablet view, or a Push 2 (pixel display, protocol published by Ableton)?
- Does the Seqtrak stay in the rig as a sound module next to the Pi's own engine?

## Study material (local, `reference files/`)

- `OpenSource/`: Zynthian, Blokas (Pisound, Patchbox OS, RT kernel), Organelle, Ableton `push-interface`
- `Ableton/Move/`: recovery image and community projects (Schwung, `schwung-spi`, `ableton-move-lab`)
- `jasmine-granular-pedal/analysis/CHOMPI-main`: CHOMPI firmware (open source)
