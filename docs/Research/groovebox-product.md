# Groovebox: a Maschine-style standalone instrument

*Written 2026-10-27. Status: **parked**. This becomes its own repo and product when work starts, after the
Seqtrak bridge reaches parity. Nothing here is being built yet.*

## What it is (aspiration)

> **A standalone groovebox for my rig.** It works the Maschine way: groups, pads, patterns, scenes and song.
> It runs on hardware I already own and rescued, with no computer and no vendor's permission. It plays the
> moment I touch it, it never loses my work, and anything I start can be finished in a DAW. It's built like a
> real instrument: specified, tested and versioned, even if I'm its only user.

*(First draft, to be rewritten in my own words.)*

**Why the Maschine Studio fits**: its buttons are the Maschine workflow (GROUP A–H, PATTERN, SCENE, STEP,
NOTE REPEAT, SAMPLING, MUTE/SOLO/SELECT, two screens, jog wheel), and it's already fully mapped from Python
(`docs/Maschine/maschine-studio.md`). Native Instruments never made the software run on Linux. The hardware
half is solved; this product is the software that gives those buttons meaning.

**Who it's for**: me, performing on the rig and sketching ideas.

**Principles**
- Instant response from the hardware.
- Never loses work, even if the power is cut.
- Playable without staring at a screen.
- Anything made can be opened in a DAW (DAWproject).

**Not in v1**: touchscreen, plugin hosting, Wi-Fi sync, a polished Mac app, other people's needs.

## Aspiration vs. v1

| | Aspiration | v1 (sized for a Pi 4) |
|---|---|---|
| Groups | 8 groups × 16 pads, like Maschine | **4 groups**, like the Move |
| Sounds | Sampler, several synths, per-pad effects | Sampler + 1–2 light synths, a few effects |
| Song | Patterns, scenes, arranger, sampling | Patterns + scenes, then song mode |
| Surfaces | Maschine + Push together | Maschine first, Push second |

## The workflow model

```
Project
 └─ 8 Groups (A–H)          ← GROUP buttons
     └─ 16 Sounds (pads)    ← each: a sound source + effects
     └─ Patterns            ← PATTERN button, step or live recorded
 └─ Scenes                  ← one pattern per group, SCENE button
 └─ Song / Sections         ← scenes in order
```

Plus pad modes (drums, keyboard, chords, step), note repeat, sampling and a mixer. Each mode gets a short
spec page listing what every button does, in the style of the Seqtrak docs. The project file follows the
DAWproject shape so a song can be opened in Bitwig (see `interoperability.md`).

## Is a Raspberry Pi powerful enough?

- **Four tracks is proven.** The Ableton Move is a Pi 4-class chip (a CM4) running four tracks, each with an
  instrument and effects (`tracks[4]` in its set file; see `how-instruments-are-built.md`).
- **Caveat 1**: the Move runs Ableton's own optimised engine. Open-source synths such as Surge XT can be
  heavier, so the number of voices and effects has to be **measured** (milestone M0), not assumed.
- **Caveat 2**: the Move gives audio, pads and LEDs to a separate XMOS chip so the CPU is never interrupted.
  An audio hat plus real-time tuning gets most of that; a Pi 5 is the upgrade path.
- **Pi vs. OP-1 Field**: in raw computing the Pi is almost certainly far stronger (4 cores at 1.5–1.8 GHz,
  4 GB RAM). The OP-1 Field's main chip carries an Analog Devices logo, part number unreadable in the FCC
  photos (`reference files/FCC/README.md`); the original OP-1 used a Blackfin DSP at a few hundred MHz.
  ❓ The Field's exact chip is unconfirmed. A DSP runs tight audio code with no operating system in the way,
  so the OP-1 shows how much a small, focused engine can do.

## Architecture

```
┌──────────────── Raspberry Pi 4 ──────────────────────────────┐
│                                                              │
│  surface service (Python)        engine (C++, real-time)     │
│  ├ Maschine driver ┐             ├ sequencer + clock         │
│  ├ Push 1 driver   ├─ events ──► ├ voices: sampler, synths   │
│  └ simulator (Mac) ┘   (fast,    ├ effects, mixer            │
│  modes, screens, LEDs  no JSON)  └ audio out → audio hat     │
│         ▲                                │                   │
│         └────── state (playhead, levels) ┘                   │
│                                                              │
│  project service: save/load, DAWproject export               │
│  system service:  settings, updates, shutdown                │
│  systemd: restarts each service on its own                   │
└──────────────────────────────────────────────────────────────┘
```

Key decisions (recommended, not final):

1. **The sequencer lives inside the engine**, next to the audio clock, so timing is accurate to the sample.
   Python is never in the path from pad hit or step to sound.
2. **The UI stays in Python.** Modes, screens and LEDs aren't time-critical, and this reuses the existing
   Maschine and Push code.
3. **Fixed, versioned contracts** between the parts: the event list, the engine's command list, the project
   file format. Each part can then be rewritten without breaking the others.
4. **The engine is built from open-source parts** and is its own GPL program if it uses GPL parts; the
   surface stays MIT (see Licensing).
5. **A simulator from day one**, so development doesn't need the Pi or the hardware attached.

### Lessons from the Behringer KICK source

The Behringer KICK (BE 0700-AAM) is an announced, not yet released, Linux groovebox whose full source was
published as AGPL in October 2026: <https://github.com/MusicTribeOpenSource/0700-AAM>. It's
MPC-style: programs (drum, keygroup, clip, MIDI, CV), sequences, Song mode (sequence × repeats in order),
Next Sequence launching (Next Bar / Sudden), clip pads (toggle / one-shot, quantised), a sampler and a looper.

From reading the code (2026-10-26):
- **Copy the shape**: separate processes for engine, GUI, device control and MIDI; one small message type for
  every control (pad, button, knob, slider, LED); a desktop simulator (`kickem`).
- **Don't copy the transport**: pad hits travel panel → serial → device control → JSON over TCP → GUI →
  JSON over TCP → engine. The UI process sits in the pad-to-sound path.
- **Don't copy the supervision**: if any process stops answering its heartbeat, all of them are restarted, so
  a GUI hang also stops the audio. systemd restarting each service on its own is better.
- **Learn from the bugs**: the panel parser assumes every serial read starts on a packet boundary, drops
  packets with no data, and can read past its buffer. Treat partial reads as normal.
- **Licence**: AGPL. Ideas and structure are free to learn from; the code must not enter MIT repos. AudIO (its
  engine) could only be used as a separate AGPL program talking over a socket. Its Airwindows effects are MIT.

## Every job the product needs

**Reuse** = existing library as-is; **adapt** = existing code changed to fit; **build** = write it myself.

### Product and design

| Job | What it covers | Options | Effort |
|---|---|---|---|
| Product management | Vision, scope, "not in v1", priorities | Me + Linear | Build |
| Interaction design | What every button does in every mode, screen layouts | Maschine manual as reference; Maschine HID map | Build |
| Physical design | Mounting, cables, power on the keyboard stand | Existing rig | Adapt |
| Sound content | Factory kits, samples, presets | CC0 packs (Freesound CC0), own sampling | Reuse + build |

### Platform

| Job | What it covers | Options | Effort |
|---|---|---|---|
| Hardware | Pi, audio hat, powered hub | Pisound / HiFiBerry DAC+ ADC | Buy |
| Operating system | Image, real-time kernel, read-only system, boot time | Raspberry Pi OS Lite + rpi-image-gen, Patchbox OS (Blokas), Zynthian's system scripts as reference | Adapt |
| Safe updates | A/B system copies, rollback | RAUC, SWUpdate, Mender | Reuse |
| Device drivers | Maschine and Push on Linux, audio hat | Own Maschine and Push code; hat drivers are in the kernel | Adapt |

### Sound

| Job | What it covers | Options | Effort |
|---|---|---|---|
| Audio engine core | Audio in/out, real-time thread, mixer, routing | miniaudio (public domain), RtAudio (MIT), JACK/PipeWire; JUCE is heavier and GPL/paid | Build on a library |
| Sampler | Pads play samples, layers, pitch | sfizz (BSD), or a simple one of my own | Reuse or build |
| Synths | Melodic sounds | DaisySP (MIT, known from Jasmine), Mutable Instruments code (MIT; Plaits, Braids, Rings), Dexed (GPL), Surge XT (GPL, heavier) | Reuse |
| Effects | Reverb, delay, filter, compression | Airwindows (MIT), DaisySP, Mutable Clouds (MIT), Freeverb (public domain) | Reuse |
| DSP prototyping | Trying new sounds quickly | Faust, Pure Data / libpd (BSD) | Optional |

### Music logic

| Job | What it covers | Options | Effort |
|---|---|---|---|
| Sequencer and clock | Patterns, steps, swing, note repeat, scenes, song | Seqtrak step knowledge; nothing off-the-shelf fits | **Build: the heart of the product** |
| Sync | MIDI clock in/out, tempo shared with other gear | RtMidi (MIT), ALSA sequencer, Ableton Link (GPL) | Reuse |
| Sampling and editing | Record, slice, time-stretch, find hits | dr_libs (public domain), libsndfile (LGPL), Signalsmith Stretch (MIT), libsamplerate (BSD), aubio (GPL) | Reuse + build |

### Software around it

| Job | What it covers | Options | Effort |
|---|---|---|---|
| Surface and modes | LEDs, screens, button logic | Own Python, Pillow for the screens | Adapt |
| Messages between parts | Surface ↔ engine ↔ project | OSC (python-osc, liblo), shared-memory queues, ZeroMQ | Reuse |
| Project storage | Save, autosave, never corrupt a file | JSON + safe file writes, SQLite | Build on a library |
| DAW export | Open a song in Bitwig | DAWproject spec (MIT, from Bitwig) | Build on a spec |
| External gear | MIDI out to Seqtrak/Orchid, USB audio to iPad | Existing bridge and Pi notes | Reuse own |
| Services | Start, restart, shutdown | systemd | Reuse |

### Quality and delivery

| Job | What it covers | Options | Effort |
|---|---|---|---|
| Developer tools | Simulator on the Mac, build system, Pi builds | CMake, uv/pyproject, GitHub Actions (ARM runners) | Build |
| Testing | Unit tests, timing tests, long runs with no dropouts | pytest, Catch2/doctest for C++ | Build |
| Performance | CPU per voice, latency, timing jitter | `perf`, audio loopback cable for latency, dropout (xrun) counters | Build |
| Releases | Versions, changelog, deploy record | `.deployed` rule, git tags | Adapt |
| Documentation | Manual, button reference, specs | Same habits as open-push | Build |
| Licensing | Which part uses which licence | One `LICENSES.md` | Build |

### What I actually build myself

1. **The sequencer**: patterns, scenes, song, timing. This is the product.
2. **The interaction design**: what the Maschine buttons do.
3. **The engine glue**: joining sampler, synths and effects into one real-time engine.
4. **The surface modes**, in Python, on top of the existing drivers.
5. **The project format and DAW export.**

Everything else is choosing well, wiring together and testing.

## Hardware

| Part | Have | Role |
|---|---|---|
| Maschine Studio | ✅ fully mapped | Main surface |
| Push 1 | ✅ | Second surface (keyboard mode, 8×8 step grid) |
| Pi 4 (4 GB) | ✅ pibridge, but that's the Seqtrak rig | The brain. **Use a second Pi or spare SD card** so the rig stays untouched |
| Audio hat | ❌ | Sound out. Pisound or HiFiBerry DAC+ ADC |
| Powered USB hub | ❌ probably | Maschine + Push together |
| Seqtrak, Orchid, OP-1 Field | ✅ | External instruments over MIDI later; not needed for v1 |

## Milestones (each has a pass/fail gate)

| Stage | Goal | Done when |
|---|---|---|
| **M0 Proof** | Maschine on Pi + audio hat + one pad plays a sample | Pad-to-sound under 10 ms, no dropouts in 1 hour |
| **M1 Drum machine** | 1 group, 16 pads, step sequencer, save/load | A beat can be made and reloaded after a reboot |
| **M2 Maschine workflow** | 4 groups, scenes, note repeat, keyboard mode, mixer | A full song sketch with no computer |
| **M3 Song + sampling** | Song mode, sampling, DAWproject export | A rig song opens in Bitwig |
| **M4 Appliance** | Read-only system, safe updates, fast boot, mounted on the stand | Pull the power mid-song, nothing is lost |

M0 is the go/no-go point: if latency isn't good enough on a Pi 4, that's found out for the price of an audio
hat.

Performance targets are checked by tests, not by feel: latency, timing jitter, boot time, an 8-hour run with
no dropouts.

## If the Pi 4 isn't enough

M0 shows *how* the Pi falls short, and that decides the fallback:

| M0 result | Try first | Then |
|---|---|---|
| CPU too slow (too few voices/tracks) | **Pi 5** (Raspberry Pi quotes 2–3× a Pi 4; same OS, hats, tools) | A faster board (below) |
| Latency or dropouts, CPU fine | Real-time tuning, a USB audio interface instead of the hat | An audio co-processor (Daisy) or Bela |
| USB trouble | Powered hub, separate supplies | — |

Other platforms, roughly in order of how much changes:

| Platform | Strength | Cost |
|---|---|---|
| **Pi 5** | Same ecosystem, much faster | Needs active cooling, more power |
| **Pi + Daisy Seed** as sound engine | The Move's idea (it uses an XMOS chip): the Pi does surface, sequencer and files; the Daisy (Cortex-M7, 480 MHz, 64 MB RAM, audio codec on board) makes the sound with no OS in the way. Known from Jasmine | Engine code must run bare-metal; samples limited by the Daisy's RAM |
| **Rockchip RK3588 boards** (Orange Pi 5, Radxa Rock 5B) | Several times a Pi 4's CPU | Weaker Linux support and fewer audio hats; more fiddly |
| **Intel N100 mini PC** | Far more CPU, ordinary Linux, USB audio interface | More power (bigger battery), no hats, bigger box |
| **Bela** | Built for sub-millisecond audio latency | Weak CPU; good only if latency, not power, is the problem |
| **NXP i.MX8 module** (what the KICK uses) | Industrial, long-lived, good audio support | Slower than a Pi 4; more a real-product choice than a better one |
| **Daisy only**, bare-metal (like the OP-1) | Fully predictable, instant boot | No Linux; screens, files and USB hosting all become hard work |

**Keep the doors open now**: choosing libraries that also run on microcontrollers (DaisySP, Mutable
Instruments, Airwindows) keeps the Daisy option possible, and the fixed contracts plus a cross-platform engine
mean a platform change only touches the thin platform layer.

## Mac or Linux?

**Both at once.** Write and debug on the Mac; run on a test Pi from the first week. Don't build a finished
Mac app and port it at the end.

- The risky parts only show up on the Pi: the CPU budget (the Mac Studio is several times faster), latency
  and dropouts (Linux audio, the hat, real-time tuning), USB permissions on Linux, and the appliance parts.
- Nearly all the code is cross-platform: the Maschine driver (hidapi, libusb), the Push driver (MIDI), the
  Python modes, the C++ engine (miniaudio covers CoreAudio and ALSA), and the sound libraries. Only a thin
  layer differs: audio backend, device permissions, OS image.

Working rules:
1. Develop on the Mac, with the Maschine plugged in or the simulator.
2. A test Pi on the desk (not pibridge); one command builds and copies to it.
3. M0 happens on the Pi first.
4. **Every milestone must pass on the Pi, not the Mac.** In between, run it on the Pi at least weekly.
5. A CPU meter in the engine from day one, with a Mac budget well below the Pi's limit.
6. Later: CI builds for ARM Linux on every push.

The Mac build is a development tool with a simple simulator window, not a product. A polished Mac app would
be a second product and is on the "not in v1" list.

## Its own repo

- The groovebox is **its own repo and product**. open-push stays focused on the Seqtrak bridge and parity.
- open-push is MIT and my own code, so it can be reused freely in the new project.
- **Share, don't copy.** The Push driver, Maschine driver and shared control language move into **one small
  package** that both repos depend on. A fix made once reaches both, and the drivers can't drift apart (the
  October 2026 three-versions problem). This fits the planned module-host work (KM-268).

## Licensing

| Part | Licence | Rule |
|---|---|---|
| open-push and the shared driver package | MIT | Stays MIT |
| Groovebox surface/UI | MIT (my choice) | Can use MIT/BSD/public-domain libraries freely |
| Groovebox engine | GPL if it uses GPL parts (Surge XT, Dexed, aubio, Link) | A separate program, talking to the surface by messages |
| Behringer KICK / AudIO | AGPL | Learn from it; never paste it in. AudIO only as a separate AGPL program |
| Airwindows, DaisySP, Mutable Instruments | MIT | Use directly |

Separate programs that exchange plain messages are generally treated as separate works (the Free Software
Foundation's reading); tight coupling such as shared memory structures blurs the line. Not legal advice.

## Open questions

1. Rewrite the vision in my own words.
2. Maschine Studio as main surface, Push 1 second: confirm.
3. Does the Seqtrak become an external instrument for the groovebox, or stay a separate rig?
4. Which audio hat? (Blocks M0.)
5. Engine library and synth set: decision records once M0 is done.
6. A codename for the product (separate from the umbrella naming in `umbrella-naming.md`).
7. Does this absorb the standalone epic KM-243, or get its own Linear project?

## Related

- `standalone-instrument.md`: the earlier "own Push 3" goal (Push 1 + Pi 4 + audio hat + own engine)
- `how-instruments-are-built.md`: Move, Chase Bliss, teenage engineering, CHOMPI
- `bridge-architecture.md`: surface host + modules + systemd
- `interoperability.md`: DAWproject song model; parking-lot entry for this product
- `docs/Maschine/maschine-studio.md`: the Maschine Studio map
