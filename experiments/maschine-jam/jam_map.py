"""Guided button mapping for the Maschine Jam (17cc:1500). Read-only: nothing is sent to the device.

The script names a button; you press it. No typing.
  - encoder RIGHT -> skip this button (keeps its old bit if it had one)
  - encoder LEFT  -> go back one button and redo it
  - pressing a button that is already mapped -> warning, asked again
Pads (bits 18-81) and the flickering bit 115 are ignored. Every answer is saved straight away;
Ctrl-C stops, and running again resumes at the first unmapped or skipped button.

Usage (in a normal Terminal window, from the repo root):
    venv/bin/python experiments/maschine-jam/jam_map.py [--from "BUTTON NAME"] [OUT.json]

Button names follow the panel photo of 2026-10-31 (main label; the shift label in brackets).
"""
import json
import os
import sys
import time

import hid

VID, PID = 0x17CC, 0x1500
args = sys.argv[1:]
START = None
if "--from" in args:
    k = args.index("--from")
    START = args[k + 1]
    del args[k:k + 2]
OUT = args[0] if args else os.path.join(os.path.dirname(__file__), "button-map.json")
IGNORE = set(range(18, 82)) | {115}

BUTTONS = (
    # left column, top to bottom
    ["SONG", "STEP", "PAD MODE", "CLEAR", "DUPLICATE",
     "D-PAD UP", "D-PAD DOWN", "D-PAD LEFT", "D-PAD RIGHT", "NOTE REPEAT"]
    # above and below the pad grid
    + [f"SCENE {n}" for n in range(1, 9)]
    + [f"GROUP {c}" for c in "ABCDEFGH"]
    # right column, top to bottom
    + ["MST", "GRP", "IN 1", "HEADPHONES", "ENCODER PUSH", "BROWSE"]
    # beside the touch strips
    + ["MACRO", "LEVEL", "AUX", "CONTROL", "AUTO"]
    + ["PERFORM", "NOTES", "LOCK", "TUNE", "SWING"]
    # bottom row, left to right
    + ["SHIFT", "PLAY", "REC", "PAGE LEFT", "PAGE RIGHT", "TEMPO", "GRID", "SOLO", "MUTE", "SELECT"]
)

mapping = json.load(open(OUT)) if os.path.exists(OUT) else {}  # name -> bit (None = skipped)

info = next((d for d in hid.enumerate(VID, PID) if d.get("usage_page") == 0xFF01), None)
if info is None:
    sys.exit("Maschine Jam not found (is another capture still running?)")
dev = hid.device()
dev.open_path(info["path"])
dev.set_nonblocking(True)


def bits(report):
    return {(i - 2) * 8 + k for i in range(2, len(report)) for k in range(8) if report[i] >> k & 1}


def save():
    json.dump({b: mapping[b] for b in BUTTONS if b in mapping}, open(OUT, "w"), indent=1)


last_enc = None


def wait_for_press():
    """Return the new bit pressed, or 'skip' if the encoder turned."""
    global last_enc
    prev_bits = set()
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
            return "skip" if step < 8 else "back"
        last_enc = enc
        new = (now - prev_bits) - IGNORE
        prev_bits = now
        if new:
            return min(new)


def drain():
    time.sleep(0.4)  # let the encoder settle so one turn = one step
    while dev.read(512):
        pass


# start at --from NAME, else at the first button not mapped yet (skipped ones count as not mapped)
if START:
    i = next((n for n, b in enumerate(BUTTONS) if b.lower() == START.lower()), None)
    if i is None:
        sys.exit(f"--from: unknown button {START!r}. Names: {', '.join(BUTTONS)}")
else:
    i = next((n for n, b in enumerate(BUTTONS) if mapping.get(b) is None), len(BUTTONS))
print(f"Saving to {OUT}. {sum(v is not None for v in mapping.values())} of {len(BUTTONS)} mapped.")
print("Press the button named.  Encoder RIGHT = skip,  encoder LEFT = go back one.  Ctrl-C to stop.\n")
try:
    while i < len(BUTTONS):
        name = BUTTONS[i]
        old = mapping.get(name)
        was = f" (was bit {old})" if old is not None else ""
        print(f"[{i + 1:2d}/{len(BUTTONS)}] press  {name:<14}{was}", end=" ", flush=True)
        mapping.pop(name, None)
        got = wait_for_press()
        if got == "back":
            if old is not None:
                mapping[name] = old
            print("<- back")
            i = max(0, i - 1)
            drain()
            continue
        if got == "skip":
            if old is not None:
                mapping[name] = old
                print(f"-> kept bit {old}")
            else:
                mapping[name] = None
                print("-> skipped")
        else:
            owner = next((n for n, b in mapping.items() if b == got), None)
            if owner:
                if old is not None:
                    mapping[name] = old
                print(f"-> bit {got} is already {owner}! try again")
                drain()
                continue
            mapping[name] = got
            print(f"-> bit {got}")
        save()
        drain()
        i += 1
except KeyboardInterrupt:
    print("\nstopped")
finally:
    dev.close()
print(f"\n{sum(v is not None for v in mapping.values())} buttons mapped in {OUT}")
