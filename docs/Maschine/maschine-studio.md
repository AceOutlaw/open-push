# Native Instruments Maschine Studio: driving it without NI software

**State (2026-10-24)**: 🔄 Every control, both screens and every LED work from macOS with plain Python
(`hidapi` + `pyusb`/libusb). No NI driver, no NI software, no firmware change. A live demo ties it all
together. Not yet tried on Linux / the Pi.

All of this is **our own measurement** of the device's USB traffic and behaviour (guided runs on the
hardware, confirmed by eye). Third-party projects were used only for names and leads (cabl,
KompleteSynthesia, Encdr); their byte layouts turned out **not** to match this unit, so nothing here is
taken from them. Status marks: ✅ verified on the hardware · 🟡 likely · ❓ unknown.

- Experiments and data: [`experiments/maschine-studio/`](../../experiments/maschine-studio/)
- Raw captures and photos: local only, `reference files/NativeInstruments/maschine-studio/`

## Why

Revive an abandoned controller (NI dropped it) as a general instrument surface, the same way open-push
revives the Push 1: 16 RGB pads with pressure, 8 touch-sensitive endless knobs, a jog wheel, ~70
buttons and two 480×272 colour screens.

## USB ✅

Vendor `0x17CC`, product `0x1300`, USB 2.0 High Speed, firmware `bcdDevice 0x0021`. **Self-powered**: it
needs its own power supply. Five interfaces:

| # | What | Endpoints | Used for |
|---|---|---|---|
| 0 | Audio Control | – | companion of the MIDI interface |
| 1 | MIDI (class-compliant) | bulk `0x81` in / `0x01` out | the DIN MIDI in + 3 outs only (no control data) |
| 2 | **HID**, vendor usage page `0xFF01` | interrupt `0x82` in (64 B) / `0x02` out (64 B) | **all controls and LEDs** |
| 3 | DFU | – | firmware update: **never touch** |
| 4 | **Display**, vendor class | bulk `0x03` out, 512 B packets | **both screens** |

No driver needed: HID and MIDI are standard classes; the display is claimed with libusb. The HID report
descriptor (1,327 B) declares: input `0x01` (32 B), `0x20` (48 B); output `0x80` (62 B), `0x81` (44 B),
`0x82` (52 B), `0x83` (55 B); feature reports `0xd0–0xdb`, `0xf0–0xfa` (not explored).

**No handshake.** Input streams as soon as the HID interface is opened; LEDs and screens accept data
straight away.

## Input

### Report `0x01`: buttons, touch, jog, knobs (33 bytes incl. id) ✅

Only sent **when something changes**. Read the current state on demand with GET_REPORT
(`hid.device.get_input_report(0x01, 64)`).

| Byte | bit 0 | bit 1 | bit 2 | bit 3 | bit 4 | bit 5 | bit 6 | bit 7 |
|---|---|---|---|---|---|---|---|---|
| 1 | PLUG-IN | MIX | SAMPLING | page → | page ← | BROWSE | ARRANGE | CHANNEL |
| 2 | TAP | STEP | MACRO | NOTE REPEAT | AUTO | ALL | ❓ | ❓ |
| 3 | GROUP A | GROUP E | GROUP F | GROUP B | GROUP C | GROUP G | GROUP H | GROUP D |
| 4 | EVENTS | ERASE | SHIFT | GRID | RESTART/LOOP | PLAY | REC | METRO |
| 5 | NAVIGATE | PAD MODE | PATTERN | SCENE | MUTE | SOLO | SELECT | DUPLICATE |
| 6 | PASTE | REDO | UNDO | COPY | NUDGE | CLEAR | QUANTIZE | NOTE |
| 7 | ❓ | ❓ | ❓ | jog press | ENTER | jog → | jog ← | BACK |
| 8 | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ |
| 9 | display 1 | display 4 | display 6 | display 8 | display 7 | display 5 | display 3 | display 2 |
| 10 | IN 1 | IN 2 | IN 3 | IN 4 | CUE | SOUND | GROUP | MASTER |
| 11 | ❓ | always 1 | ❓ | ❓ | ❓ | ❓ | ❓ | ❓ |
| 12 | touch knob 1 | touch 2 | touch 3 | touch 4 | touch 5 | touch 6 | touch 7 | touch 8 |

- Display buttons 1–8 = the buttons above the screens, left to right (wired out of order: use a table).
- There is no SNAP button on this unit; that position is STEP.
- The jog wheel has **no touch sensor**.
- **Byte 13** (low nibble) = **jog wheel**: a 4-bit counter, ±1 per detent, wraps 15 ↔ 0. Take the delta
  mod 16.
- **Bytes 15–32** = 9 endless encoders, 16-bit little-endian, ~0–999, wrapping: fields 0–7 = **knobs 1–8**
  below the screens (left → right), field 8 = **VOLUME** knob. Take the delta mod 1000.
- Never set by any control: byte 2 bits 6–7, byte 7 bits 0–2, byte 8, byte 11 (except bit 1), byte 14 ❓
  (footswitch inputs, or unused matrix positions).

### Report `0x20`: pads (49 bytes incl. id) ✅

Streams continuously (~750 reports/s on macOS). Bytes 1–24 hold **16 × 12-bit raw pressure** (0–4095;
a firm press reaches ~3,900–4,080), packed 3 bytes per pair of sensors:

```
for g in 0..7:  a, b, c = r[1+3g], r[2+3g], r[3+3g]
    sensor[2g]   = (a << 4) | (b >> 4)
    sensor[2g+1] = ((b & 0x0F) << 8) | c
pad = 13 - 4*(sensor // 4) + (sensor % 4)     # sensors count from the top-left; pads 1-16 from the bottom-left
```

The pads give **raw pressure**, not velocity: note-on threshold, velocity and aftertouch have to be computed
in software (like the Push does in its firmware). Bytes 25–48 have the same layout but different values ❓
(a second sample in time?).

## Screens ✅

Two **480 × 272**, **RGB565 big-endian** (`RRRRRGGG GGGBBBBB`, high byte first). Each bulk transfer to
endpoint `0x03` (interface 4):

```
84 00 SS 60 00 00 00 00          header: SS = screen buffer to draw into (00 left, 01 right)
XX XX YY YY WW WW HH HH          rectangle, 16-bit big-endian
00 NN NN NN  + 4·N bytes         N pixel pairs, raw
01 NN NN NN  + 4 bytes           one pixel pair repeated N times (fills)
03 00 00 00                      blit
40 00 SS 00                      end: SHOW screen SS (double-buffered: drawing is invisible until this)
```

- Partial rectangles need **x aligned to 4, y aligned to 2**. The demo sends changed 120 × 34 tiles at 30 fps.
- A whole screen in 8 strips of 34 rows takes ~23 ms.
- ⚠️ A header with byte 0 ≠ `0x84` or byte 3 ≠ `0x60` makes **both screens fall back to the firmware
  splash** and ignore drawing **until a power cycle**. Byte 2 = 2 or 3, or x ≥ 480: silently dropped.
- At power-on the screen memory is noise: clear first.

## LEDs: output reports `0x80`–`0x83` ✅

hidapi `write([id] + data)` on the HID interface. Values **0–127** = brightness. Each report rewrites all
of its LEDs; they keep their state until the next report with the same id. RGB LEDs are 3 bytes **R, G, B**.

| Report | Bytes | LEDs |
|---|---|---|
| **0x80** (62) | 1–24 | pads 1–8, RGB (pad 1 = bytes 1–3 … pad 8 = 22–24) |
| | 25–32 | pads 1–8, a second single-colour LED each |
| | 33–40 | display buttons 1–8 |
| | 41–50 | CHANNEL, PLUG-IN, ARRANGE, MIX, BROWSE, SAMPLING, page ←, page →, ALL, AUTO |
| | 51–54 | ❓ (nothing obvious; maybe the IN / OUT 1–3 marks) |
| | 55–62 | IN 1–4 (blue), MASTER, GROUP, SOUND, CUE |
| **0x81** (44) | 1–24 | pads 9–16, RGB |
| | 25–32 | pads 9–16, second single-colour LED |
| | 33–40 | COPY, PASTE, NOTE, NUDGE, UNDO, REDO, QUANTIZE, CLEAR |
| | 41–44 | BACK, jog ←, jog →, ENTER |
| **0x82** (52) | 1–24 | groups A–H, RGB |
| | 25–32 | groups A–H, second single-colour LED |
| | 33–36 | TAP, STEP, MACRO, NOTE REPEAT |
| | 37–44 | RESTART/LOOP, METRO, EVENTS, GRID, PLAY, REC, ERASE, SHIFT |
| | 45–52 | SCENE, PATTERN, PAD MODE, NAVIGATE, DUPLICATE, SELECT, SOLO, MUTE |
| **0x83** (55) | 1–16 | left level meter, bottom → top; 16 = red top (clip) |
| | 17–32 | right level meter, bottom → top; 32 = red top |
| | 33 | **meter colour switch**: on = segments white, off = blue |
| | 34 | ❓ |
| | 35–40 | jog labels: EDIT, CHANNEL, BROWSE, TUNE, SWING, VOLUME |
| | 41–55 | jog ring, 15 segments: byte 41 = 12 o'clock (at CHANNEL), clockwise |

Jog ring segment nearest each label: CHANNEL 0, BROWSE 2, VOLUME 6, SWING 7–8, TUNE 9, EDIT 13.

Brightness that looks even: pads idle 30 (full at 127), white buttons resting 32, PLAY / REC resting 72
(the coloured LEDs look darker at the same value).

## How it was mapped

1. **Read-only capture** of HID and MIDI while using the controls (`maschine_capture.py`).
2. **Screens**: build the header from published leads, test one small square, then variants. The right
   screen only worked once the end command carried the screen number.
3. **Guided input run on the device's own screens** (`maschine_map2.py`): the left screen asks for one
   control, the right screen shows what was detected, ENTER keeps it, BACK retries, jog → skips. A first
   version without confirmation recorded knob-turn and pad mix-ups; confirmation fixed that.
4. **LEDs**: one colour-coded photo per report for the RGB blocks (red, green, blue, yellow, cyan,
   magenta, white, dim white in successive triples), then a guided run lighting one byte at a time while
   the user pressed what lit or picked from a menu drawn under the display buttons (`maschine_ledmap2.py`).
5. **Calibration** of the jog ring and the meter colour (`maschine_calibrate.py`).

Lessons: let the user confirm every reading; answer with buttons, not knobs (knobs need many turns to
register and get brushed by accident); the screen above the display buttons makes a free menu.

## Running it (macOS)

```bash
brew install libusb
python3 -m venv venv && venv/bin/pip install hidapi pyusb pillow numpy
venv/bin/python experiments/maschine-studio/maschine_demo.py 600     # seconds
```

The demo: pads glow in the selected group's colour and brighten with pressure; groups A–H pick the
colour; left meter = hardest pad, right meter = VOLUME knob (white; CUE toggles blue); the jog ring
follows the wheel and the nearest jog label lights; buttons light while held (PLAY / REC / SHIFT / CUE
toggle); the screens show knobs 1–8, the last button, the group, volume and jog.

## Open questions

- Pad report bytes 25–48.
- LED `0x80` 51–54 and `0x83` 34; the IN / OUT 1–3 indicator marks; what the second single-colour LED on
  each pad and group looks like.
- Unused input bits (footswitch jacks?).
- Feature reports `0xd0–0xfa`.
- Linux / Raspberry Pi behaviour (hidraw + libusb; udev permissions).

## Next steps

Tracked in Linear (Kace Music / OpenPush, label Maschine): epic **KM-261** (In Progress).

| Issue | Step |
|---|---|
| KM-262 | Run the demo on the Raspberry Pi (Linux): udev rule, hidraw, libusb display |
| KM-263 | Reusable driver module (input decoder, LED state, screen framebuffer) with tests |
| KM-264 | Pads as an instrument: note-on threshold, velocity, aftertouch, MIDI out |
| KM-265 | Decode the open questions above |
| KM-266 | Use it from the bridge (second surface for Seqtrak / Reason) or the standalone instrument (KM-243) |
| KM-267 | Maschine Jam (`17cc:1500`) with the same method |
