# open-push: Project Map

open-push is several connected projects in one repo. This page is the map: what each one is, where it
lives, and how far along it is. Each project has a one-page overview in [`docs/projects/`](docs/projects/)
that links to its detailed docs. Nothing here moves code; it's a view on top of it.

**The goal behind all of them**: an instrument I can play. The Push 1 is the controller; the projects
give it something to control, the knowledge to control it, and a box to run on.

*Last reviewed 2026-10-24.*

---

## Projects worked on

| # | Project | One line | State |
|---|---|---|---|
| 1 | [Push 1 foundation](docs/projects/01-push-foundation.md) | Learning and driving the Push 1 hardware: pads, LEDs, LCD, encoders, layouts, scales | ✅ Done; everything builds on it |
| 2 | [Reason bridge](docs/projects/02-reason-bridge.md) | The Push as a Reason control surface via Lua codecs | 🟡 Basics work; mixer and device modes unfinished |
| 3 | [Seqtrak bridge](docs/projects/03-seqtrak-bridge.md) | The Push controls a Yamaha Seqtrak through a Raspberry Pi | ✅ Deployed and working; **the main project** |
| 4 | [Seqtrak protocol](docs/projects/04-seqtrak-protocol.md) | Reverse engineering what the Seqtrak says and accepts, kept as its own deliverable | 🔄 Active |
| 5 | [Pi bridge platform](docs/projects/05-pi-platform.md) | The headless Pi: setup, service, deploys, remote access, iPad USB audio, mode switching | ✅ Running; mode switching partly built |
| 6 | [Generic MIDI / BLE controller](docs/projects/06-generic-midi-ble.md) | The Push as a plain MIDI controller over Bluetooth or USB gadget, on a Pi Zero 2W | 💤 Worked as an experiment; dormant |
| 7 | [Hardware research](docs/projects/07-hardware-research.md) | Studying other devices to learn how they're built and to revive abandoned ones | 🔄 Ongoing; notes and study material, no product code |
| 8 | [Writing](docs/projects/08-writing.md) | The story of open-push: case study, development history, blog drafts | 🔄 Ongoing |

**Connected, in their own repos**: *Jasmine* (granular pedal firmware on a Daisy Seed) and
*field-arrange* (OP-1 Field tape arranger).

## How they connect

```
            (1) Push 1 foundation
                  │
     ┌────────────┼──────────────┬──────────────────┐
(2) Reason    (3) Seqtrak      (6) Generic MIDI     future: Orchid, Logic/MCU,
    bridge        bridge           / BLE              standalone instrument
                  │  ▲
     (4) Seqtrak protocol
                  │
          (5) Pi bridge platform ── runs (3); a Pi Zero 2W runs (6)

(7) Hardware research feeds all of them.   (8) Writing tells the story.
```

One controller, several targets, and two kinds of support every target needs: **protocol knowledge**
and a **platform to run on**.

## Future work (researched or planned, not built)

| Idea | Builds on | Where it's written down |
|---|---|---|
| Standalone instrument: Push 1 + Pi 4 + audio hat + own sound engine | 1, 3, 5, Jasmine | [`docs/Research/standalone-instrument.md`](docs/Research/standalone-instrument.md) · Linear KM-243 |
| Bridge architecture: modes as pages, non-blocking reads, atomic saves, read-only system | 3, 5 | [`docs/Research/how-instruments-are-built.md`](docs/Research/how-instruments-are-built.md) §6 · KM-244 |
| Seqtrak parity: the remaining features, chapter by chapter | 3, 4 | [`docs/Seqtrak/PARITY.md`](docs/Seqtrak/PARITY.md) · KM-100–113 |
| Orchid chord bridge: play the Telepathic Instruments Orchid from the Push | 1, 7 | KM-233 |
| Logic and other DAWs via Mackie Control emulation | 1, 2 | [`docs/Research/mcu-emulation-spike.md`](docs/Research/mcu-emulation-spike.md) |
| Seqtrak arranger: prepare sets off the device, audition them live | 4 | [`docs/Research/seqtrak-arranger.md`](docs/Research/seqtrak-arranger.md) |
| Finish runtime mode switching and system settings on the Pi | 5, 6 | Project 5 page |
| A reproducible Pi image (working name KaceMusicOS) | 5 | Project 5 page |
| More devices from the SysEx survey | 1, 7 | [`docs/Research/hardware-sysex-survey.md`](docs/Research/hardware-sysex-survey.md) |
| Maschine Studio as a surface without NI software (fully mapped and driven on macOS; next: Pi, driver module, pads as MIDI, Jam) | 7 | [`docs/Maschine/maschine-studio.md`](docs/Maschine/maschine-studio.md) · KM-261 |

Prioritising these is a backlog-refinement task (Linear KM-259).

## Where things live

| Path | What |
|---|---|
| `src/open_push/core`, `music` | Shared Push and music code (project 1) |
| `src/open_push/reason` | Reason bridge (2) |
| `src/open_push/seqtrak` | Seqtrak bridge (3), plus unfinished mode switching (5) |
| `src/open_push/midi` | Generic MIDI / BLE controller (6) |
| `src/experiments` | Push hardware explorers (1) |
| `docs/Seqtrak`, `tools/`, `scripts/debug`, `experiments/app-clickthrough` | Seqtrak protocol work (4) |
| `docs/Research` | Research write-ups (7) and future plans |
| `docs/Maschine`, `experiments/maschine-studio` | Maschine Studio protocol write-up, mapping tools, data and live demo (7) |
| `tests/` | Bridge and protocol tests (3, 4) |
| Local only, gitignored | `raspberry-pi-setup/` (5), `reference files/` (7), `Content/` (8), private `CLAUDE.md` / `AGENTS.md` |
