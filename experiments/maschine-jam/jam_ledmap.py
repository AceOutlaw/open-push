"""Guided LED mapping for the Maschine Jam button report 0x80 (53 bytes).

The script lights one byte at a time. You press the button that lit up; it is recorded by name
(from button-map.json).
  - encoder RIGHT -> the lit LED is not a button (a meter light, or nothing visible): recorded as null
  - encoder LEFT  -> go back one byte
Ctrl-C stops; running again resumes. All LEDs are switched off at the end.

Usage (in a normal Terminal window, from the repo root):
    venv/bin/python experiments/maschine-jam/jam_ledmap.py [--from BYTE] [VALUE]
"""
import json
import os
import sys
import time

import hid

VID, PID = 0x17CC, 0x1500
HERE = os.path.dirname(__file__)
OUT = os.path.join(HERE, "led-map.json")
SIZE = 53
IGNORE = set(range(18, 82)) | {115}

args = sys.argv[1:]
start = None
if "--from" in args:
    k = args.index("--from")
    start = int(args[k + 1], 0)
    del args[k:k + 2]
VALUE = int(args[0], 0) if args else 127

names = {b: n for n, b in json.load(open(os.path.join(HERE, "button-map.json"))).items() if b is not None}
ledmap = {int(k): v for k, v in json.load(open(OUT)).items()} if os.path.exists(OUT) else {}

info = next((d for d in hid.enumerate(VID, PID) if d.get("usage_page") == 0xFF01), None)
if info is None:
    sys.exit("Maschine Jam not found (is another script holding it?)")
dev = hid.device()
dev.open_path(info["path"])
dev.set_nonblocking(True)


def light(byte):
    data = [0] * SIZE
    if byte is not None:
        data[byte] = VALUE
    dev.write(bytes([0x80] + data))


def bits(report):
    return {(i - 2) * 8 + k for i in range(2, len(report)) for k in range(8) if report[i] >> k & 1}


last_enc = None


def wait():
    global last_enc
    prev = set()
    while True:
        data = dev.read(512)
        if not data:
            time.sleep(0.002)
            continue
        if data[0] != 0x01:
            continue
        now, enc = bits(data), data[1] & 0x0F
        if last_enc is not None and enc != last_enc:
            step = (enc - last_enc) % 16
            last_enc = enc
            return "none" if step < 8 else "back"
        last_enc = enc
        new = (now - prev) - IGNORE
        prev = now
        if new:
            return min(new)


def drain():
    time.sleep(0.4)
    while dev.read(512):
        pass


def save():
    json.dump({str(k): ledmap[k] for k in sorted(ledmap)}, open(OUT, "w"), indent=1)


i = start if start is not None else next((n for n in range(SIZE) if n not in ledmap), SIZE)
print(f"Saving to {OUT}. {len(ledmap)} of {SIZE} bytes done. LED value {VALUE}.")
print("Press the button that lights up.  Encoder RIGHT = not a button,  LEFT = back.  Ctrl-C to stop.\n")
try:
    while i < SIZE:
        light(i)
        old = ledmap.get(i, "-")
        print(f"[byte {i:2d}] (was {old})", end=" ", flush=True)
        got = wait()
        if got == "back":
            print("<- back")
            i = max(0, i - 1)
            drain()
            continue
        if got == "none":
            ledmap[i] = None
            print("-> not a button")
        else:
            name = names.get(got, f"bit {got}")
            ledmap[i] = name
            print(f"-> {name}")
        save()
        drain()
        i += 1
except KeyboardInterrupt:
    print("\nstopped")
finally:
    light(None)
    dev.close()
done = {k: v for k, v in ledmap.items() if v}
print(f"\n{len(done)} button LEDs mapped, {sum(v is None for v in ledmap.values())} not buttons, in {OUT}")
