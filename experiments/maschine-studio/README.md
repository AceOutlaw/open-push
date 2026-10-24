# Maschine Studio experiments

Driving the Native Instruments Maschine Studio (`17cc:1300`) with plain Python on macOS, no NI software.
Write-up and full protocol: [`docs/Maschine/maschine-studio.md`](../../docs/Maschine/maschine-studio.md).

Setup: `brew install libusb`, then a venv with `hidapi pyusb pillow numpy` (plus `mido python-rtmidi` for
the capture). The Studio needs its own power supply.

| Script | What |
|---|---|
| `maschine_demo.py [seconds]` | **Live demo**: pads, groups, meters, jog ring, buttons and both screens together |
| `maschine_capture.py` | Read-only capture of HID and MIDI input |
| `maschine_display_text.py` | Draw text on both screens (the working display reference) |
| `maschine_map2.py OUT.json [start]` | Guided input mapping run on the Studio's own screens (ENTER keep, BACK retry, jog → skip) |
| `maschine_led.py REPORT OFFSET=VALUE ...` | Send one LED report (`0x80`–`0x83`) |
| `maschine_ledmap2.py OUT.json map-run2.json RANGE...` | Guided LED mapping: light one byte, pick what lit (e.g. `0x83:33-55`) |
| `maschine_calibrate.py OUT.json` | Jog ring geometry and meter colour tests |

Data (our measurements): `map-run2.json` (inputs), `led-map.json` (LEDs), `calibration.json` (jog ring,
meter colour). The demo reads the first two from this folder.

Safety: the scripts only open the HID interface and the display interface. They never touch interface 3
(DFU). A malformed display header sends the screens to the firmware splash until a power cycle.
