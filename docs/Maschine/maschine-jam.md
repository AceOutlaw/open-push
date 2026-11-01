# Native Instruments Maschine Jam: reading it without NI software

**State (2026-11-01)**: 🔄 Every input and every LED works from macOS with plain Python (`hidapi`):
64 pads, 52 buttons, the encoder (turn + push) and 8 touch strips in; pad/scene/group colours, button
LEDs, the LEVEL meter and the strip LEDs out. Palette not fully charted. Not yet tried on the Pi.

All of this is **our own measurement** (guided runs on the hardware, labels from a photo of this unit).
Status marks: ✅ verified on the hardware · 🟡 likely · ❓ unknown.

- Experiments and data: [`experiments/maschine-jam/`](../../experiments/maschine-jam/)
- Raw captures and panel photo: local only, `reference files/NativeInstruments/maschine-jam/captures/`

## USB ✅

Vendor `0x17CC`, product `0x1500`. Bus-powered. One interface only: **HID, vendor usage page
`0xFF01`** (interface 0). No class-compliant MIDI port appears without NI software.

**No handshake.** Input arrives as soon as the HID interface is opened. Reports are sent only on
change (nothing while idle). Only one program can hold the interface at a time on macOS (a second
`open_path` fails).

## Report `0x01`: buttons, pads, encoder (17 bytes incl. id) ✅

- **Byte 1, low nibble: encoder position**, a 4-bit counter that wraps 15→0. Turning right counts up.
- **Bytes 2–16: one bit per control.** Bit index = `(byte - 2) * 8 + bit` (bit 0 = mask `0x01`).
  1 = pressed.

| Bits | Controls |
|---|---|
| 0 | SONG |
| 1–8 | SCENE 1–8 (the numbered row above the pads) |
| 9–12 | STEP, PAD MODE, CLEAR, DUPLICATE |
| 13, 14, 15, 16 | D-pad up, left, right, down (four separate buttons) |
| 17 | NOTE REPEAT |
| 18–81 | **pads**: pad = bit - 18, row by row from the top-left, 8 per row |
| 82–89 | GROUP A–H (the lettered row below the pads) |
| 90–94 | MST, GRP, IN 1, headphones, BROWSE |
| 95–99 | MACRO, LEVEL, AUX, CONTROL, AUTO (left of the strips) |
| 100–104 | PERFORM, NOTES, LOCK, TUNE, SWING (right of the strips) |
| 105–114 | SHIFT, PLAY, REC, PAGE ◀, PAGE ▶, TEMPO, GRID, SOLO, MUTE, SELECT |
| 115 | 🟡 encoder touch: on in stretches of seconds, flickers when a hand is near; silent for a whole run with the hand away from the knob |
| 116 | encoder push |
| 117–119 | ❓ never seen set |

The full name → bit table is [`button-map.json`](../../experiments/maschine-jam/button-map.json).
The pads are **on/off only** (no velocity, no pressure).

**This unit:** the top row, 5th pad (bit 22) is worn: a normal press does nothing, a hard press
registers (16 clean presses in 30 s on 2026-10-31). ✅ bit 22 is that pad; the fault is the contact.

## Report `0x02`: touch strips (49 bytes incl. id) ✅

Eight blocks of 6 bytes, strip 1 (left) = bytes 1–6 … strip 8 = bytes 43–48. Each block, little-endian:

| Bytes | Meaning |
|---|---|
| 0–1 | ❓ a 16-bit value that changes while the strip is touched (🟡 a timestamp/counter) |
| 2–3 | **position of the first finger**: 0 = not touched, about 20 (bottom) … ~1000 (top) |
| 4–5 | 🟡 second finger (the strips are dual-touch); stayed 0 with one finger |

Sent continuously while a strip is touched (~100 per second).

## LEDs ✅

The HID descriptor lists output reports `0x80` (53 bytes), `0x81` (80), `0x82` (88) and `0xF4` (3), plus
feature reports `0xD0`, `0xD8`–`0xDD`, `0xF1`, `0xF2`. Only `0x80`–`0x82` are written; the others are
left alone (could be configuration or firmware). One write sets the whole report; the LEDs hold their
state until the next write.

### Colour values

The pads, scene/group buttons and strips take a **palette index**: `value = colour * 4 + shade`, 0 = off.
Shade 3 looks lighter (pinker on the reds) than shades 0–2. Colours 1–16 at shade 2, from the demo
(photo 2026-11-01, 🟡 to be confirmed by eye; phone photos under-report the LEDs):

| Colour | Look | Colour | Look |
|---|---|---|---|
| 1 | red | 9 | cyan |
| 2 | red-orange | 10 | light blue |
| 3 | orange | 11 | blue |
| 4 | amber | 12 | violet |
| 5 | yellow | 13 | purple |
| 6 | pale yellow-green | 14 | magenta |
| 7 | green | 15 | pink |
| 8 | teal | 16 | pink-red |

Colours 17 and up (values 68+) and colour 0's shades 1–3 are not charted; 72–79 looked near-white.
The **top LED of each LEVEL meter column is red** (a fixed-colour LED); the other seven are white.

### Report `0x81`: scene buttons, pads, group buttons (80 bytes) ✅

| Bytes | LEDs |
|---|---|
| 0–7 | SCENE 1–8 |
| 8–71 | pads, row by row from the top-left (pad = byte - 8, the same order as the input bits) |
| 72–79 | GROUP A–H |

### Report `0x80`: buttons and LEVEL meter (53 bytes) ✅

Single-colour button LEDs (127 = full on). Guided run, data in
[`led-map.json`](../../experiments/maschine-jam/led-map.json):

| Bytes | LEDs |
|---|---|
| 0–9 | SONG, STEP, PAD MODE, CLEAR, DUPLICATE, D-pad up, left, right, down, NOTE REPEAT |
| 10–12 | MST, GRP, IN 1 |
| 13 | ❓ nothing visible |
| 14 | headphones |
| 15 | ❓ nothing visible |
| 16 | BROWSE |
| 17–21 | MACRO, LEVEL, AUX, CONTROL, AUTO |
| 22–26 | PERFORM, NOTES, LOCK, TUNE, SWING |
| 27–36 | SHIFT, PLAY, REC, PAGE ◀, PAGE ▶, TEMPO, GRID, SOLO, MUTE, SELECT |
| 37–44 | LEVEL meter, left column, **bottom to top** (37 = bottom) |
| 45–52 | LEVEL meter, right column, **bottom to top** (45 = bottom) |

Encoder push has no LED.

### Report `0x82`: touch strip LEDs (88 bytes) ✅

8 strips × 11 LEDs: strip `s` (0 = left) = bytes `s*11` … `s*11 + 10`, **LED 0 at the bottom**, LED 10
at the top. Same palette as the pads (value 7 showed pink on the strip, as on the pads).

## Still to do

1. Confirm bit 115 (touch the encoder knob on cue) and the second-finger field (two fingers on one
   strip).
2. Chart colours 17+ and confirm the table above by eye.
3. ✅ Live demo: `jam_demo.py` (2026-11-01). Still open: a guided mapper that lights the control it asks for.
4. Run on the Pi.

## Tools

```bash
python3 -m venv venv && venv/bin/pip install hidapi
venv/bin/python experiments/maschine-jam/jam_capture.py 60      # read-only log of every change
venv/bin/python experiments/maschine-jam/jam_order.py LOG       # bits in first-press order
venv/bin/python experiments/maschine-jam/jam_map.py             # guided button mapping (needs a Terminal)
```
