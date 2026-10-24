# 7. Hardware Research

**What**: Studying how other music hardware is built and how it talks, to learn from the implementation and
to revive controllers that have been abandoned. Self-taught by taking finished systems apart, not by copying
them: nothing from vendors' code goes into this repo.

**State**: 🔄 Ongoing. The output is write-ups; study material stays local in `reference files/`.

## Write-ups

| Doc | What |
|---|---|
| `docs/Research/how-instruments-are-built.md` | Firmware update models (Chase Bliss, teenage engineering, Ableton Move), CHOMPI's firmware architecture, how the Move's OS and clip launcher work, offline vs. live device protocols |
| `docs/Research/hardware-sysex-survey.md` | Which devices are worth integrating, by how well their SysEx is known |
| `docs/Research/mcu-emulation-spike.md` | Push 1 as a Mackie Control Universal (Logic and most DAWs) |
| `docs/Research/standalone-instrument.md` | Plan for an instrument of my own, built on what was learned |
| `docs/Research/second-opinion-codex-2026-10-15.md` | An outside review of the Seqtrak bridge |
| `docs/Maschine/maschine-studio.md` | Maschine Studio driven without NI software: full input, screen and LED protocol (tools in `experiments/maschine-studio/`) · KM-261 |

## Devices studied

| Device | What was looked at |
|---|---|
| Ableton Move | Public recovery image, community projects (Schwung): CM4 + XMOS, OS layout, clip launcher |
| teenage engineering EP / OP series | Web updater and sample tool: `.tfw` header, SysEx update and file protocols |
| Chase Bliss | Web flasher and raw firmware images; CHOMPI's open-source firmware |
| Telepathic Instruments Orchid | Manual, firmware and app, for the planned chord bridge (KM-233) |
| Synido TempoPAD C16 | Full hardware map; next step needs an SWD debug probe |
| Native Instruments Maschine Studio | Every button, knob, pad, both screens and every LED mapped and driven from Python on macOS; live demo. Next: the Pi (KM-261) |
| Others | FCC filings (OP-1 field, Seqtrak), Roland TR-8 MIDI chart, Logic control-surface scripts, Pushpin groovebox |

## Method

Read the official manuals first. When the vendor's tool is a web page, its code is downloaded to the
browser and can be read. Record the traffic while the official tool runs. Experiment with read-only
requests before anything that writes. Mark what's verified and what's assumed.
