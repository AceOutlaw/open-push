"""Live demo for the Maschine Jam (17cc:1500): every mapped input drives its LEDs.

  - pads light while pressed, in the selected colour
  - SCENE 1-8 and GROUP A-H show 16 palette colours; press one to pick the pad colour
    (the terminal prints the value, so this doubles as a palette chart)
  - touch strips act as faders: a bar follows your finger and stays where you let go
  - the encoder moves both LEVEL meter columns
  - other buttons light while held

Usage (from the repo root):  venv/bin/python experiments/maschine-jam/jam_demo.py [seconds]
Ctrl-C stops; all LEDs go off at the end.
"""
import json
import os
import sys
import time

import hid

VID, PID = 0x17CC, 0x1500
HERE = os.path.dirname(__file__)
DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 600.0
SHADE = 2                       # 0-3 within a colour; 3 looks lighter/pinker


def colour(hue):
    return hue * 4 + SHADE


BUTTON_BIT = {n: b for n, b in json.load(open(os.path.join(HERE, "button-map.json"))).items() if b is not None}
LED_BYTE = {n: int(k) for k, n in json.load(open(os.path.join(HERE, "led-map.json"))).items() if n}
BIT_TO_LED = {BUTTON_BIT[n]: LED_BYTE[n] for n in LED_BYTE if n in BUTTON_BIT}
SCENE_BITS = [BUTTON_BIT[f"SCENE {i}"] for i in range(1, 9)]
GROUP_BITS = [BUTTON_BIT[f"GROUP {c}"] for c in "ABCDEFGH"]
SWATCH_HUES = list(range(1, 17))          # SCENE 1-8 = hues 1-8, GROUP A-H = hues 9-16

info = next((d for d in hid.enumerate(VID, PID) if d.get("usage_page") == 0xFF01), None)
if info is None:
    sys.exit("Maschine Jam not found (is another script holding it?)")
dev = hid.device()
dev.open_path(info["path"])
dev.set_nonblocking(True)

pad_hue = 1
pressed = set()
strip_level = [0] * 8           # 0-11 lit LEDs per strip
meter = 0                       # 0-8
last_enc = None
sent = {}


def send(rid, payload):
    if sent.get(rid) != payload:
        dev.write(bytes([rid] + payload))
        sent[rid] = payload


def render():
    grid = [0] * 80
    for i, hue in enumerate(SWATCH_HUES):
        byte = i if i < 8 else 72 + (i - 8)
        grid[byte] = hue * 4 + (3 if hue == pad_hue else 0)   # selected swatch brighter
    for bit in pressed:
        if 18 <= bit <= 81:
            grid[bit - 18 + 8] = colour(pad_hue)
    send(0x81, grid)

    buttons = [0] * 53
    for bit in pressed:
        if bit in BIT_TO_LED:
            buttons[BIT_TO_LED[bit]] = 127
    for i in range(meter):
        buttons[37 + i] = buttons[45 + i] = 127
    send(0x80, buttons)

    strips = [0] * 88
    for s, level in enumerate(strip_level):
        for j in range(level):
            strips[s * 11 + j] = colour(SWATCH_HUES[8 + s])   # strip s in GROUP colour s
    send(0x82, strips)


def bits(report):
    return {(i - 2) * 8 + k for i in range(2, 17) for k in range(8) if report[i] >> k & 1}


print(f"Demo running for {DURATION:.0f}s. Pads, SCENE/GROUP colours, strips, encoder, buttons. Ctrl-C to stop.")
t0 = time.monotonic()
render()
try:
    while time.monotonic() - t0 < DURATION:
        data = dev.read(512)
        if not data:
            time.sleep(0.002)
            continue
        if data[0] == 0x01 and len(data) >= 17:
            now = bits(data)
            for bit in now - pressed:
                if bit in SCENE_BITS + GROUP_BITS:
                    pad_hue = SWATCH_HUES[(SCENE_BITS + GROUP_BITS).index(bit)]
                    print(f"pad colour: hue {pad_hue} -> values {pad_hue * 4}-{pad_hue * 4 + 3}", flush=True)
            pressed = now
            enc = data[1] & 0x0F
            if last_enc is not None and enc != last_enc:
                step = (enc - last_enc) % 16
                meter = max(0, min(8, meter + (1 if step < 8 else -1)))
            last_enc = enc
        elif data[0] == 0x02 and len(data) >= 49:
            for s in range(8):
                pos = data[1 + 6 * s + 2] | data[1 + 6 * s + 3] << 8
                if pos:                                   # 0 = not touched: keep the last level
                    strip_level[s] = max(1, min(11, round(pos / 1000 * 11)))
        render()
except KeyboardInterrupt:
    pass
finally:
    for rid, size in ((0x80, 53), (0x81, 80), (0x82, 88)):
        dev.write(bytes([rid] + [0] * size))
    dev.close()
print("stopped, LEDs off")
