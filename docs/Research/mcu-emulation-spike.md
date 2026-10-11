# MCU Emulation Spike: Push 1 as a Mackie Control Universal

**Goal**: Make Push 1 work with Logic Pro (and nearly every other DAW) by having the
Python middleware impersonate a Mackie Control Universal (MCU) on a virtual MIDI port.

**Why MCU**: Logic, Cubase, Studio One, Reaper, Bitwig, Digital Performer — and Live
itself — all natively speak the Mackie Control protocol. One emulator replaces N
per-DAW bridges. The Reason Lua-codec approach was the hard road; MCU is the standard
road.

**Status**: Research complete, unimplemented. Protocol details below verified against
community reverse-engineering documentation (see Sources).

---

## Why the hardware match is unusually good

| MCU concept | Push 1 equivalent | Fit |
|---|---|---|
| 8 V-Pots (endless relative encoders) | 8 endless encoders (CC 71–78) | Perfect — both relative |
| V-Pot push switches | Encoder touch or lower-row buttons | Good |
| 2×56-char LCD (7 chars per channel strip) | 4×68-char LCD, 8 fields of 8–9 chars (`Push1Display.set_fields`) | Better than the original — 4 lines vs 2 |
| **Fader touch events** (notes 104–112) | **Push encoders are touch-sensitive** (touch sends notes) | Rare — most DIY MCU emulators can't do this |
| 8 motorized faders (pitch bend ch 0–7) | Encoders send pitch-bend deltas; values shown on LCD | Workable (no motor feedback needed — we *are* the display) |
| VU meters (channel pressure) | **Pad grid as 8 meter columns** (8 levels tall, color-graded) | Better than the original hardware |
| Transport buttons | Push Play/Record/Stop buttons | Direct |
| Jog wheel (CC 60) | Tempo encoder (CC 14) | Direct |
| Timecode 7-segment display (CC 64–73) | LCD line 4 segment | Direct |

The pad grid is the differentiator: an MCU has 8 small LED meters; Push can render
8 full meter columns in color, plus use spare rows for record-arm/mute/solo state.

---

## Protocol essentials (host ↔ surface)

All from community documentation of the MCU protocol (TouchMCU, htlab.net):

- **SysEx header**: `F0 00 00 66 14 ... F7` (`00 00 66` = Mackie, `0x14` = MCU device ID).
- **LCD write** (host → surface): `F0 00 00 66 14 12 <offset> <chars…> F7`.
  Offset 0x00–0x37 = top line, 0x38–0x6F = bottom line (2×56-char buffer).
  We re-render these 112 chars onto Push's LCD fields.
- **Buttons** (surface → host): Note On ch 0, velocity 127 = press, 0 = release.
  - Transport: Stop 93, Play 94, Record 95, Rewind 91, FFwd 92
  - Per-channel: Rec 0–7, Solo 8–15, Mute 16–23, Select 24–31, V-Pot switch 32–39
  - Bank ◀/▶ 46/47, Channel ◀/▶ 48/49, Flip 50
  - Fader touch: 104–111 (channels), 112 (master)
- **V-Pot rotation** (surface → host): CC 16–23 on ch 0.
  Value `0x01–0x0F` = CW by n clicks, `0x41–0x4F` = CCW by n clicks.
  (Push encoders send `1–63` CW / `127–65` CCW on CC 71–78 — trivial translation.)
- **V-Pot LED rings** (host → surface): CC 48–55. We render these as value bars on the
  LCD instead (Push 1 encoders have no LED rings).
- **Faders**: Pitch bend, ch 0–7 = faders 1–8, ch 8 = master, 14-bit 0–16383.
  Host echoes positions (for motor faders) — we display them; encoder turns emit
  relative pitch-bend updates from the last echoed position.
- **VU meters** (host → surface): Channel pressure `D0 sv` — high nibble s = strip,
  low nibble v = level (0x0 silent … 0xC = 0 dB … 0xF clip).
- **Timecode/assignment** (host → surface): CC 64–73 / 74–75, 7-seg character encoding.
- **Handshake**: There is a serial/challenge handshake (`… 14 02 <serial> <response>`),
  but hosts since MCU firmware v1.02 generally work without it — Logic simply starts
  sending once the surface is added in Control Surfaces setup. **Risk item: verify
  empirically with Logic; implement the device-query reply with an arbitrary serial if
  needed.**

## Proposed Push control mapping (v1)

| Push control | MCU action |
|---|---|
| Encoders 1–8 (CC 71–78) | V-Pots 1–8 (default) or faders (Volume mode / Flip) |
| Encoder touch | Fader touch notes 104–111 (touch-to-grab, release-to-commit) |
| Master encoder (CC 79) | Master fader (pitch bend ch 8) |
| Tempo encoder (CC 14) | Jog wheel (CC 60) |
| Play / Record / Stop buttons | Notes 94 / 95 / 93 |
| Arrows left/right (CC 44/45) | Channel ◀/▶ (notes 48/49) |
| Page left/right (CC 62/63) | Bank ◀/▶ (notes 46/47) |
| Upper LCD row (CC 20–27) | Channel Select (notes 24–31) |
| Lower LCD row (CC 102–109) | Mute (16–23); with Solo button held → Solo (8–15); with Record held → Rec-arm (0–7) |
| Volume / Pan-Send / Device buttons | Encoder assignment modes (map to MCU assignment buttons) |
| Pad grid | VU meters (8 columns × 8 levels) + state rows; later: drum/keys modes as today |
| LCD lines 1–2 | MCU LCD top/bottom (channel names / values, 7 chars per strip) |
| LCD line 4 | Timecode + assignment display |

## Architecture

```
Push 1  <—MIDI—>  Python middleware  <—virtual port "OpenPush MCU">  DAW (Logic etc.)
                    │
                    ├─ MCUSurface: parses host→surface (LCD, meters, LEDs, fader echo)
                    ├─ MCUEmitter: builds surface→host (notes, V-Pot CCs, pitch bend)
                    └─ renders MCU state onto Push (LCD fields, pad meters, button LEDs)
```

This is exactly the existing "dumb terminal + middleware" pattern; MCU is just another
target protocol like Seqtrak SysEx. Prerequisite: the shared Push surface layer in
`core/` (hardware, display, encoder accumulator) — build on that, don't fork a third app.

## Risks / open questions

1. **Handshake enforcement** — likely unnecessary; verify against Logic first session.
2. **Fader semantics without motors** — pickup/takeover feel needs tuning (touch-grab
   using encoder touch should solve this elegantly).
3. **Windows** — python-rtmidi cannot create virtual ports on Windows; document
   loopMIDI as the workaround.
4. **Logic-specific extensions** — Logic uses some function-key and assignment quirks
   beyond base MCU; iterate with a MIDI monitor, same methodology as Seqtrak.

## v0 milestone (validation slice)

Transport + LCD + 8 V-Pots + channel select, tested against Logic:
1. Open virtual port, add "Mackie Control" in Logic's Control Surfaces setup.
2. Prove host→surface: receive and render LCD text + timecode.
3. Prove surface→host: Play/Stop, one V-Pot controlling pan, channel select.
4. Then: faders via pitch bend + touch, meters on pads, bank switching, Flip.

## Sources

- [TouchMCU — Mackie Control protocol documentation](https://github.com/NicoG60/TouchMCU/blob/main/doc/mackie_control_protocol.md)
- [htlab.net — Mackie Control Protocol reverse-engineering (PDF)](https://htlab.net/computer/protocol/mackie-control/MackieControlProtocol_EN.pdf)
- [htlab.net — Mackie Control MIDI map (PDF)](https://htlab.net/computer/protocol/mackie-control/Mackie_Control_MIDI_Map.pdf)
- [libMackieControl protocol notes](https://github.com/Do-sth-sharp/libMackieControl/blob/main/doc/MackieControl.md)
