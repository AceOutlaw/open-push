# Maschine Jam experiments

Reading the Native Instruments Maschine Jam (`17cc:1500`) with plain Python on macOS, no NI software.
Write-up and full protocol: [`docs/Maschine/maschine-jam.md`](../../docs/Maschine/maschine-jam.md).

Setup: a venv with `hidapi`. Only one script can hold the Jam at a time.

| Script | What |
|---|---|
| `jam_demo.py [seconds]` | **Live demo**: pads, SCENE/GROUP colour picker, strips as faders, encoder → LEVEL meter, buttons |
| `jam_capture.py [seconds]` | Read-only log of every HID report change |
| `jam_order.py LOG` | List the bits in a capture in the order they were first pressed |
| `jam_map.py [--from NAME] [OUT.json]` | Guided button mapping: it names a button, you press it. Encoder right = skip, left = back |

| `jam_led.py REPORT [fill=V] [ramp] [N=V] [A-B=V]` / `jam_led.py off` | Send one LED report (`0x80`–`0x82` only) |
| `jam_ledmap.py [--from BYTE] [VALUE]` | Guided LED mapping of report `0x80`: one LED lights, press its button. Encoder right = not a button, left = back |

Data (our measurements): `button-map.json` (button name → bit in report `0x01`), `led-map.json`
(report `0x80` byte → button name; null = meter or nothing visible).
