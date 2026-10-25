# Bridge Architecture: Modules and Separate Programs, Like the Move

**Decision (proposal, 2026-10-24)**: the bridge becomes one surface host that loads modules, plus a
few separate programs started by systemd. Programs are split by timing and by what can fail, not by
feature. That is how the Ableton Move is built.

Tracked in Linear under epic KM-244 (*Bridge · Architecture & reliability*). Diagrams of everything
below are in the Claude doc "open-push Bridge Architecture":
https://claude.ai/artifact/3Gw5q1Y7JB9AQvtqRuRRST

Sources: the Move 2.1.1 recovery image and the community projects in `reference files/Ableton/Move/`
(local only, not in git). See also `how-instruments-are-built.md` §3 and `standalone-instrument.md`.

---

## 1. How the Ableton Move is built

Read from the recovery image (`parts/p2.img`, with `debugfs`): startup scripts, `/opt/move`, the D-Bus
config and the text strings in `MoveLauncher`. No Ableton code was decompiled.

```
Startup scripts (/etc/init.d, sysvinit)
├── MoveLauncher        supervisor: starts the others, restarts them when they crash
│   ├── Move            30 MB, compiled C++: audio engine, sequencer and UI in ONE process
│   ├── MoveControlModeHandler, MoveMessageDisplay, MoveFirmwareAutoUpdater,
│   │   MoveSSHKeyInstaller, MoveResetter, MoveSentryRunProcessor (crash reports)
│   └── rnbo/bin/RNBOLauncher (named in its strings; not inspected)
└── MoveWebService      web pages; talks to Move over D-Bus

D-Bus names: com.ableton.move, com.ableton.system, com.ableton.update
Move  <-- SPI: one 4 KB page every 128-frame block (2.9 ms) -->  XMOS chip (pads, buttons, LEDs, display, audio)
```

- **The lesson is in what is not split.** The engine, sequencer and UI share one process because they
  run on the same 2.9 ms clock. Programs are separated where timing or failure differs: web, updates,
  settings and crash reporting can be slow or crash without the music glitching.
- **The supervisor guards the hardware.** `MoveLauncher` refuses to start `Move` without the SPI link
  ("No SPI connection available, abort launching Move").
- **Real-time tuning in the startup script** (`/etc/init.d/move`): `chrt` gives the SPI threads
  priority 90/91; interrupts and work queues are pinned to cores 0–2; audio interrupts get core 3.
- About 18 programs ship in `/opt/move`, plus test and benchmark tools.

## 2. How Schwung adds modules to the Move

Schwung (MIT, formerly "Move Everything", `charlesvestal_schwung/docs/ARCHITECTURE.md`, `MODULES.md`):

```
Move process (real-time priority)
├── stock Move app
└── schwung-shim.so   loaded with LD_PRELOAD; hooks every SPI exchange; runs module dsp.so code
        ↕ shared memory
shadow_ui process (normal priority)   QuickJS runs each module's ui.js; menus and display overlay

Module folder: module.json + ui.js + dsp.so, found on disk at startup
Standalone tool: stops Move and its supervisor, owns the hardware; Move restarts when it exits
```

- **Fixed sound interface**, `plugin_api_v2` (`src/host/plugin_api_v1.h`): `create_instance`,
  `destroy_instance`, `on_midi`, `set_param`, `get_param`, `get_error`, `render_block`.
- **A slow UI can't glitch audio**: `shadow_ui` is forked back to normal scheduling and only talks to
  the shim through shared memory.
- **One hardware owner at a time**: standalone tools are the model for our mode switching.

## 3. open-push today

```
open-push-seqtrak.service → python3 src/open_push/seqtrak/app.py
Push 1 ↔ SeqtrakBridge (one 4,950-line class) ↔ Seqtrak
          modes = flags in each handler; protocol, state, LED/LCD output, settings
          main loop polls both ports with 1 ms sleeps (app.py ~4874)
          handlers can block (sleep ~1612, note-list read: KM-254)
midi/app.py        separate generic MIDI app (pimini); already split into modes/ and outputs/
bridge_app.py      unfinished mode switching; not run; has drifted from app.py
```

## 4. Proposed architecture

```
systemd   starts each program and restarts it on failure (MoveLauncher's job)
├── openpush-surface (Python)
│     Host            owns the Push; loads modules from folders; frame buffer, sends only changes,
│                     fixed redraw clock
│     modules/seqtrak  kind=device: owns the Seqtrak port, protocol and state cache
│     modules/mixer, step-seq, session, keyboard   kind=mode: one page each
├── openpush-system (Python)   settings, network info, shutdown, later a web page
└── openpush-engine (later)    C++ or Rust, real-time, own CPU core, audio HAT
```

| Program | Job | Language | Like the Move's |
|---|---|---|---|
| `openpush-surface` | Owns the Push; hosts mode and device modules | Python | `Move` (UI side) |
| `openpush-system` | Settings, network info, shutdown, later a web page | Python | `MoveWebService`, `SystemDBusService` |
| `openpush-engine` (later) | Sound engine for the standalone instrument | C++ or Rust | `Move` (engine side) |
| systemd | Starts, orders and restarts the others | — | `MoveLauncher` |

Mode switching (Seqtrak control, generic MIDI, the engine) swaps which program owns the Push, the
way Schwung's standalone tools take over from Move.

## 5. Module interface

A module never writes to the Push itself: it handles events and draws into a buffer, and the host sends
only what changed.

```python
class Module:
    # described by module.toml: id, name, kind = "mode" | "device" | "tool"
    def on_enter(self, ctx): ...     # ctx: settings, the device drivers it may use, a logger
    def on_exit(self): ...
    def on_input(self, event): ...   # decoded pad / button / encoder events
    def on_device(self, msg): ...    # messages from the device this module owns
    def tick(self, now): ...         # move pending operations along; never block
    def render(self, frame): ...     # draw LEDs and LCD into the frame buffer
```

Rules:
1. **Never block** in a handler. Multi-step work becomes an operation that `tick()` advances.
2. **One owner per port.** The host owns the Push; each device module owns its device.
3. **Modes are pages.** Switching calls `on_exit` / `on_enter`; the host redraws on a fixed clock.

## 6. Executables vs. Python scripts

| Option | What | Gain | Cost | When |
|---|---|---|---|---|
| Installed commands | `pyproject.toml` declares `openpush-surface`, `openpush-system`; a versioned package in a venv on the Pi | Named programs; every deploy traceable to a commit | Little | Now (KM-270) |
| Frozen binaries | PyInstaller / Nuitka, one file per command | No Python setup on the Pi | An arm64 build step (Schwung uses Docker) | Only if Pi setup becomes a problem |
| Compiled code | C++ or Rust | Real-time safe, no garbage-collector pauses | Second language and toolchain | The engine; the surface only if latency measurements say so (KM-243) |

## 7. Migration

No rewrite; each step leaves a working Seqtrak rig.

1. Installed commands run by systemd — KM-270 (independent, can go first)
2. LEDs and LCD from a frame buffer on a fixed clock — KM-257
3. Modes as pages — KM-256
4. No blocking reads — KM-254
5. Module host and module folders — KM-268 (after 2 and 3)
6. Seqtrak device module — KM-269 (after 5)
7. `openpush-system` split out; mode switching = change of hardware owner — KM-271 (after 1 and 5)
8. Atomic saves and a read-only system — KM-255, KM-258 (any time)
9. The sound engine as its own compiled process — epic KM-243, on a spare SD card

## 8. Open questions

- **How do the processes talk?** Decide in KM-271, not before.

  | Option | Used by | For | Against |
  |---|---|---|---|
  | D-Bus | The Move; Pi system tools (systemd, BlueZ) | Built in; names survive restarts; access rules | Clunky Python API (`dasbus`, `pydbus`); hard to watch |
  | OSC over UDP | Zynthian | Music-native; any OSC monitor shows the traffic | No delivery guarantee; no access rules |
  | JSON over a Unix socket | Many small daemons | Simplest; plain Python; easy to log | We define the message format |

- Does the generic MIDI app (`midi/app.py`) become a profile of the same host?
- Is the Push 1 LCD (4 × 68 characters) enough for the system tool, or does it need a web page?
