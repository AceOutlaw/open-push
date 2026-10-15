# Second-opinion brief: Push 1 → Yamaha SEQTRAK bridge

You're being asked for an independent review and fresh ideas. Please form your own view from the
sources. Don't assume the current design is right. Where you disagree with how something is done, say so
and explain why.

## The project

**open-push** gives old Ableton Push 1 controllers a second life outside Ableton Live.

This brief is about one part of it: a **headless Push 1 → Yamaha SEQTRAK bridge**. A Raspberry Pi 4
mounted on a keyboard stand runs a Python program. The Push 1 and a SEQTRAK are both plugged into it by
USB. The goal is that **the SEQTRAK stays racked and never gets touched: the Push does everything**. It
should reach parity with what the SEQTRAK's own buttons and Yamaha's SEQTRAK app can do, as described in
Yamaha's user guide.

Two deliverables come out of this:
1. **The bridge**, which turns the Push into a full SEQTRAK controller (`src/open_push/seqtrak/`).
2. **A SEQTRAK MIDI protocol description that stands on its own** and that other software could use, for
   example a better desktop editor (`docs/Seqtrak/protocol/`). Yamaha publishes only part of the
   protocol. The rest was reverse-engineered: from MIDI captures on the Pi, from the official app's
   traffic recorded while someone clicked every control, and from send-and-read-back tests. Every message
   carries a status (verified / sent by the app / official / reported / inferred / unknown) and its
   evidence.

The person behind it has a software and UI background, writes firmware for their own hardware, and
performs with this rig. They care about the instrument feeling solid in performance. They don't want to
pile on features while the core is shaky.

## The hardware and the link

- **Push 1:** 8×8 velocity pads with a fixed colour palette, 11 encoders, a 4×68-character LCD, two rows
  of 8 buttons under the LCD, many single-colour and two-colour buttons, and a touch strip. It's driven
  over its "User" MIDI port: notes and CCs for LEDs, SysEx for the LCD.
- **SEQTRAK:** 11 tracks (7 drum, SYNTH 1, SYNTH 2, DX FM, sampler) and 6 patterns per track (Yamaha calls
  them variations). It has Song and Scene modes, 8 projects, per-project scales, effects, and Sound
  Design parameters.
  - **Control:** plain MIDI (notes, CCs, program changes) plus Yamaha SysEx Parameter Change / Request
    (`F0 43 1n/3n 7F 1C 0C H M L …`) and bulk dumps.
  - **What it reports:** some state changes on the device are announced, others aren't.
  - **Readback:** many parameters can be read back on request, some can't.
  - **Firmware:** version 1.21.3 on the test unit.
- **The link:** everything runs over USB MIDI through ALSA on the Pi, in a single Python process (mido +
  python-rtmidi). The Pi has no screen; the Push LCD is the only display.

## What we want from you

Look at it from whatever angle you think matters. These are open questions, not a checklist:

1. **Keeping two devices in agreement.** The Push has to mirror the SEQTRAK's state: tempo, presets,
   patterns, steps, scales, song and scenes, mutes, and so on. That state can change from either side, and
   from the SEQTRAK's own controls. What's a robust way to model and synchronise it, given what the device
   does and doesn't report and that a request's answer isn't guaranteed? How should the bridge behave
   after a project load, a reconnect, or a change made on the device?
2. **Talking to the SEQTRAK reliably.** What should the bridge assume about how fast, in what order and in
   what volume it can send and read? How should it know it has the true state, and how should it detect
   and recover when it doesn't?
3. **Push UI architecture.** Several "views" share the same physical controls: the pads, the LCD, the
   button rows and the encoders. Examples are note/keyboard, step sequencer, mixer, device parameters,
   scales, song/scenes, and temporary overlays such as delete or duplicate menus. What's a sound way to
   structure modes, overlays and redraws so they never fight over controls or leave stale LEDs or text?
4. **The protocol deliverable.** Is the spec format, its statuses and its evidence model the right shape
   for something other tools would rely on? What's missing? How would you make it easier to verify again
   after a firmware update?
5. **Code structure.** The main bridge file is large. What would you change first, and what should stay?
6. **Anything we're not seeing:** a different overall approach, existing prior art, risks, or things
   that will hurt in live performance.

Please give:
- a short summary of how you read the current state;
- your top recommendations, ranked, each with its reasoning and the files it touches;
- concrete designs or pseudo-code where they help;
- risks and open questions you'd want answered on the hardware before acting.

## Ground rules

- **The SEQTRAK isn't in model training data.** Don't guess its behaviour. Use the protocol spec and the
  Yamaha sources below. Where they don't say, mark it as unknown and propose a test that would settle it.
- **A message the SEQTRAK sends may only be a report, not something it accepts as a command.** The spec
  marks which.
- **Prefer evidence over the older docs:** a ✅ verified entry with evidence beats an older note.

## Sources

**The SEQTRAK protocol**, the main thing to read:
- `docs/Seqtrak/protocol/README.md`: the spec format, statuses and evidence rules
- `docs/Seqtrak/protocol/spec/*.toml`: every known message, one file per area (source of truth)
- `docs/Seqtrak/protocol/PROTOCOL.md`: the same messages as a readable reference (generated)
- `docs/Seqtrak/protocol/runs/*.json`: results of automated read and write tests against the device
- `tools/seqtrak_protocol.py`: validates the spec and cross-checks it against the bridge;
  `tools/seqtrak_verify.py` replays it against a real SEQTRAK
- `docs/Seqtrak/STEP-SEQUENCER.md`: step and note data in detail (verified)
- `docs/Seqtrak/UNDOCUMENTED-MESSAGES.md`: messages that aren't in Yamaha's Data List
- `docs/Seqtrak/APP-CLICKTHROUGH-P0.md`, `APP-CLICKTHROUGH-P1.md`, and `experiments/app-clickthrough/`:
  what the official app sends for each control
- `docs/Seqtrak/sysex-protocol-reference.md`, `docs/Seqtrak/midi-data-table.md`: older narrative
  references
- `docs/Seqtrak/REVERSE-ENGINEERING-LOG-2026-10.md`: how things were found, including mistakes
- `docs/Seqtrak/TERMINOLOGY.md`: terms (pattern vs bar, 6 variations, track numbering)

**Yamaha's own documents** (in `reference files/`, kept local only and not in the public repo):
- `reference files/Yamaha/User Guide/SEQTRAK_user_guide_En_D0.txt`: the full user guide, as text
- `reference files/Yamaha/Seqtrak Data List V2/`: the official parameter tables

**Goals and status:**
- `docs/Seqtrak/PARITY.md`: each user-guide feature against what the Push can do
- `docs/Seqtrak/FUNCTIONALITY-MAP.md`: the feature tracker

**The bridge:**
- `src/open_push/seqtrak/app.py`: the bridge (modes, Push UI, SEQTRAK sync), about 4,900 lines
- `src/open_push/seqtrak/protocol.py`: SEQTRAK message helpers

**The Push 1:**
- `docs/open-push-master-reference.md`: the hardware: buttons, encoders, LCD, LED values

## Symptoms seen on the hardware

These are reported here as observations. They're not diagnosed, and they're not a list of what to fix.
- After switching projects on the SEQTRAK, the Push sometimes kept showing the previous project's values,
  tempo for example, until something was changed on the device.
- Views that take over the LCD buttons and encoders have at times drawn over each other.
- python-rtmidi on the Pi sometimes logs `MidiInAlsa::alsaMidiHandler: unknown MIDI input error`
  (`Resource temporarily unavailable`) when the SEQTRAK sends a lot at once.
- The Push 1's white Note and Session LEDs look dimmer than its amber buttons at the same value. This
  turned out to be the hardware, not the code.
