# DAWproject experiments

Can [DAWproject](https://github.com/bitwig/dawproject) (open, MIT, Bitwig + PreSonus) carry songs for the
planned Pi sequencer? The plan: a native JSON song file on the Pi with the same structure, plus import
and export of `.dawproject` for Bitwig, Cubase and Cubasis. Background: `docs/Research/bridge-architecture.md`.

Standard library only. Run with `python3 -I`, since `.dawproject` files from elsewhere are untrusted input.

| Script | What |
|---|---|
| `dawproject_read.py FILE [--json]` | Read-only: tracks, devices, scenes × clip slots, clips, notes, arrangement. Velocities 0–1 → 0–127, notes sorted |
| `make_roundtrip.py [OUT]` | Writes `roundtrip-test.dawproject` (validates against the official `Project.xsd`) |

## Round-trip test

`roundtrip-test.dawproject`: 120 bpm, tracks "Seqtrak Kick" and "Orchid Chords", 2 scenes, one arrangement
clip. DAWproject has no element for hardware, so each track carries a generic
`<Device deviceName="SEQTRAK" deviceVendor="Yamaha">` whose `<State path="openpush/….json"/>` holds our
routing (device, port, MIDI channel, Seqtrak track). Plug-ins store their presets the same way.

1. Open it in Bitwig 8-Track and in Cubasis; export each as DAWproject.
2. `python3 -I dawproject_read.py EXPORT.dawproject` and compare with the original.
3. Questions: do the clips, loops and notes survive? Does each DAW keep the unknown `Device` and its
   `openpush/*.json` state file? Are the scenes kept (Cubasis has no clip launcher)?

## What the exports showed (2026-10-24)

- **Cubasis 3.8.3** (audio-only song): bare `Channel`s for master and send FX in `Structure`; arrangement only,
  no `Scenes`. Clips nest: the outer clip is placed in beats, the inner one holds the audio (trimmed in seconds).
- **Bitwig Studio 5.3.13** (8-Track): every track is a `Track`, master included. `Scenes` → `Scene` → `Lanes`
  → one `ClipSlot` per track (empty or not, Send and Master too) → `Clip` with `loopStart`/`loopEnd` → `Notes`.
  `Note`: `time`/`duration` in beats from the clip start, `channel` 0-based, `vel`/`rel` 0–1, optional
  per-note expression (`<Points>`, here `timbre`). Notes are **not** in time order. A clip in a slot keeps a
  leftover `time` from the arrangement; ignore it. The VST3 instrument's state is a binary `.vstpreset` in
  `plugins/`.
- **Round trip, import side (2026-10-24, screenshots):** Bitwig 8-Track opened `roundtrip-test.dawproject`
  with both scenes, clip names, colours, loops and notes intact (Kick 2: 5 notes, channel 1, C1 = key 36,
  velocity 78.7 % = 100/127). It reported the generic `Device`s as missing plug-ins. Cubase LE 15 opened
  the arrangement only (no clip launcher): both tracks, the 2-bar Kick clip with 8 notes. Still to check:
  whether either keeps the `Device` and `openpush/*.json` when exporting again.
- The two test exports (`Gravity`, with stems and a Splice preset) stay in Downloads, not in the repo.
