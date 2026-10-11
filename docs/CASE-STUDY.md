# Case Study: open-push — Ten Days to Un-Brick a Controller

*How a locked-down Ableton controller became a standalone groovebox brain — and what it took.*

---

## The problem worth telling

Ableton Push 1 is a $500 instrument: 64 velocity-sensitive RGB pads, 11 endless
touch-sensitive encoders, a character LCD. Unplug it from Ableton Live and it becomes a
paperweight displaying a single line:

> *"Ableton Push — Please start Live to play..."*

Thousands of these sit in closets. People switched DAWs, bought one used without a Live
license, or moved to hardware grooveboxes. Fully functional 2013 hardware, abandoned by
software policy. That is e-waste by design.

open-push's answer: treat Push as what it physically is — a beautifully built generic
MIDI surface — and write the brain it's missing.

## Act 1 — Archaeology (Dec 18–23, 2025): learn the hardware by studying the dead

Day one alone produced 18 commits, and the revealing ones aren't features — they're
research: *"PusheR reference analysis"*, *"Lua de-obfuscation guide"*, *"Remote SDK API
reference"*. The project started by dissecting PusheR (a discontinued commercial
Push-to-Reason product) and the Reason Remote SDK. Sixteen numbered analysis chapters
were written, mined, and later distilled into the 900-line master hardware reference
that now anchors `docs/`.

That phase produced the foundational discoveries:

- the SysEx wake-up handshake that unlocks Push without Live;
- User Mode, where every pad, button, and encoder becomes software-defined;
- the fact that Push 1's display is not a 68-character line but **four 17-character
  segments with physical gaps** — a constraint that shapes every screen the project
  renders.

It also produced the architecture thesis that still holds: **Push is a dumb terminal;
all intelligence lives in a Python middleware layer** — mode state, scales, sequencing,
display formatting — while the target device only ever sees clean, normalized MIDI.

The commit log shows honest struggle too: an IAC-ports feature committed, reverted,
then un-reverted within a single day. This wasn't a polished march; it was contact with
reality.

## Act 2 — The Christmas sprint (Dec 24–27): reverse-engineering the Seqtrak

On December 24 the project pivoted from DAW integration to standalone hardware — and
shipped an entire Yamaha Seqtrak bridge in **eleven commits in one day**: SysEx protocol
capture, transport control, track-aware pad modes, preset browsing, a verified drum
step sequencer, and a mixer redesign, ending Christmas Eve with *"Mixer mode UX redesign
with DRUM bus and bug fixes."*

Two things made that velocity possible. First, the reusable core already existed — the
isomorphic keyboard, 40+ scale definitions, and LCD handling written for Reason
transferred to the Seqtrak on day one. Second, a disciplined capture methodology: MIDI
monitor attached, every control on the device systematically actuated, every SysEx
logged, pattern-matched, correlated — then *documented before being coded*.

The output is the repository's crown jewel: a 1,400-line Seqtrak protocol reference
(`docs/Seqtrak/sysex-protocol-reference.md`) that merges Yamaha's official MIDI spec
with reverse-engineered SysEx nobody else has published — per-track variation
selection, step-sequencer add/delete opcodes, pattern state broadcasts. It effectively
liberates the Seqtrak from its own iOS app, and it is an asset independent of any code
in this repo.

By December 25 the project was auditing *itself*: a gap analysis comparing the bridge
against 22 screenshots of Yamaha's app, feature by feature, concluding ~65% coverage
with a phased plan for the rest.

## Act 3 — The standalone rig

The endgame shipped quietly: the bridge deployed to a Raspberry Pi — headless,
auto-starting via systemd, USB audio routed so Push can even trigger sample recording.

**Push + Seqtrak + Pi. No computer, no Ableton, no license.**

For context: the only official way to get a "standalone Push" is Push 3 standalone at
roughly $2,000. This rig builds one from 2013 hardware and a $60 computer, and it is
the project's real differentiator.

## The scoreboard

- **10 days, 50 commits**, ~7,600 lines of Python, ~5,000 lines of documentation
- One fully reverse-engineered protocol (Seqtrak), one DAW integration (Reason), one
  deployed standalone product (the Pi rig)
- A documented, repeatable capture methodology — plus a survey
  (`docs/Research/hardware-sysex-survey.md`) that already scouts and ranks the next
  five target devices
- An honest, tracked backlog: known bugs with repro steps, enhancement requests, a
  testing checklist

The honest epilogue: sprint velocity bought engineering debt. The two bridge apps
forked rather than shared code, and hardening came second to discovery. That is the
normal shape of a successful prototype phase — the knowledge assets (protocol docs,
methodology, working rig) are the hard-to-replace part, and those are excellent. The
cleanup is the easy, well-understood part.

## The road ahead

1. **Harden the standalone rig** — watchdog and auto-recovery, heartbeat LED, safe
   shutdown from the hardware itself. The Pi rig is the product; make it trustworthy.
2. **Close the Seqtrak gaps** — LFO control, song mode, sampler deep-editing, using the
   same capture methodology that built the protocol reference.
3. **Escape the per-DAW trap** — instead of one bespoke bridge per DAW, emulate the
   industry-standard **Mackie Control Universal** protocol. One MCU emulator makes Push
   a native control surface for Logic, Cubase, Studio One, Reaper, Bitwig, and more —
   the "works with any DAW" vision delivered through a standard rather than N custom
   integrations. See `docs/Research/mcu-emulation-spike.md`.
