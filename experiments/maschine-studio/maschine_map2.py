"""Guided mapping run v2 for the Maschine Studio, with confirm / back / skip on the device itself.

Navigation (bits from run 1, used here as controls, so they are not asked for again):
  ENTER (b7.4)            keep the result shown
  BACK  (b7.7)            on a result: try this item again; on a prompt: go to the previous item
  jog RIGHT arrow (b7.5)  skip this item (your unit doesn't have it)
  jog LEFT arrow  (b7.6)  go to the previous item

Each item: the left screen asks, the right screen shows what was detected, and nothing is
stored until ENTER. Results merge into OUT.json by item name, so a rerun only overwrites
what you confirm again. Start partway with a second argument (item number, 1-based).

Reads interface 2 (HID, plus one GET_REPORT for the baseline); writes only the display
(interface 4, endpoint 0x03). Never touches interface 3 (DFU), never sends HID output reports.
Usage: python maschine_map2.py OUT.json [start_item]
"""
import glob
import json
import os
import sys
import time

import hid
import numpy as np
import usb.backend.libusb1
import usb.core
import usb.util
from PIL import Image, ImageDraw, ImageFont

VID, PID = 0x17CC, 0x1300
W, H = 480, 272
OUT = sys.argv[1]
START = int(sys.argv[2]) - 1 if len(sys.argv) > 2 else 0
BUTTON_BYTES = [i for i in range(1, 15) if i != 13]
ENTER, BACK, RIGHT, LEFT = (7, 4), (7, 7), (7, 5), (7, 6)
NAV = {ENTER, BACK, RIGHT, LEFT}

ITEMS = (
    [("touch", f"TOUCH knob {i} (don't turn)") for i in range(1, 9)]
    + [("touch", "TOUCH the jog wheel (don't turn)")]
    + [("turn", f"TURN knob {i} (below the screens)") for i in range(1, 9)]
    + [("turn", "TURN the big JOG WHEEL"), ("turn", "TURN the VOLUME knob (master section)")]
    + [("button", n) for n in
       ["CHANNEL", "PLUG-IN", "ARRANGE", "MIX", "BROWSE", "SAMPLING", "page LEFT arrow", "page RIGHT arrow",
        "ALL", "AUTO"]
       + [f"display button {i} (above screens)" for i in range(1, 9)]
       + ["IN 1", "IN 2", "IN 3", "IN 4", "MASTER", "GROUP", "SOUND", "CUE", "PRESS DOWN on the JOG WHEEL",
          "COPY", "PASTE", "NOTE", "NUDGE", "UNDO", "REDO", "QUANTIZE", "CLEAR",
          "SHIFT", "RESTART / LOOP", "METRO", "EVENTS", "GRID", "PLAY", "REC", "ERASE",
          "TAP", "SNAP", "MACRO", "NOTE REPEAT", "SCENE", "PATTERN", "PAD MODE", "NAVIGATE",
          "DUPLICATE", "SELECT", "SOLO", "MUTE", "STEP"]
       + [f"GROUP {c}" for c in "ABCDEFGH"]]
    + [("pad", f"PAD {n}") for n in range(1, 17)]
    + [("button", "any button NOT asked about (or skip)")] * 6
)
# the last six are free slots; make their names unique
ITEMS = ITEMS[:-6] + [("button", f"EXTRA {k}: any button not asked about") for k in range(1, 7)]

# ---------------------------------------------------------------- device I/O
lib = glob.glob(os.popen("brew --prefix libusb").read().strip() + "/lib/libusb-1.0*.dylib")[0]
udev = usb.core.find(idVendor=VID, idProduct=PID,
                     backend=usb.backend.libusb1.get_backend(find_library=lambda _: lib))
if udev is None:
    sys.exit("Maschine Studio not found")
usb.util.claim_interface(udev, 4)
hdev = hid.device()
hdev.open_path(next(d for d in hid.enumerate(VID, PID) if d.get("usage_page") == 0xFF01)["path"])

rep = list(hdev.get_input_report(0x01, 64))     # 0x01 is only pushed on change, so ask once
pads = [0] * 16


def poll(timeout_ms=10):
    global rep
    r = hdev.read(64, max(1, timeout_ms))       # cython-hidapi: timeout 0 = block forever
    for _ in range(64):
        if not r:
            break
        if r[0] == 0x01 and len(r) >= 33:
            rep = list(r)
        elif r[0] == 0x20 and len(r) >= 25:
            for g in range(8):
                a, b, c = r[1 + 3 * g], r[2 + 3 * g], r[3 + 3 * g]
                pads[2 * g], pads[2 * g + 1] = (a << 4) | (b >> 4), ((b & 0xF) << 8) | c
        r = hdev.read(64, 1)


def bits():
    return {(i, b) for i in BUTTON_BYTES for b in range(8) if rep[i] >> b & 1}


def knob_raw():
    return [rep[15 + 2 * k] | (rep[16 + 2 * k] << 8) for k in range(9)]


def wrapdiff(a, b):
    d = (a - b) % 1000
    return d - 1000 if d > 500 else d


baseline = bits()


class Nav:
    """Edge detector for the four navigation buttons."""
    def __init__(self):
        self.prev = bits() & NAV

    def pressed(self):
        now = bits() & NAV
        new = now - self.prev
        self.prev = now
        return new


def wait_all_released(limit=8):
    t = time.monotonic()
    while time.monotonic() - t < limit:
        poll(20)
        if not (bits() - baseline) and max(pads) < 150:
            return


# ---------------------------------------------------------------- screens
def font(size, bold=False):
    return ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", size, index=1 if bold else 0)


F_BIG, F_MID, F_SMALL = font(32, True), font(20), font(15)
GREY, WHITE, ORANGE, GREEN = (130, 130, 145), (255, 255, 255), (255, 170, 40), (120, 255, 140)


def send(screen, img):
    a = np.asarray(img, dtype=np.uint16)
    px = (((a[..., 0] >> 3) << 11) | ((a[..., 1] >> 2) << 5) | (a[..., 2] >> 3)).astype(">u2")
    for y in range(0, H, 34):
        h = min(34, H - y)
        m = bytes([0x84, 0, screen, 0x60, 0, 0, 0, 0]) + (0).to_bytes(2, "big") + y.to_bytes(2, "big")
        m += W.to_bytes(2, "big") + h.to_bytes(2, "big") + bytes([0]) + ((W * h) // 2).to_bytes(3, "big")
        m += px[y:y + h].tobytes() + bytes([3, 0, 0, 0, 0x40, 0, screen, 0])
        udev.write(0x03, m, timeout=1000)


def wrap(d, text, fnt, x, y, width, fill, gap=6):
    line = ""
    for word in text.split():
        trial = (line + " " + word).strip()
        if d.textlength(trial, font=fnt) > width and line:
            d.text((x, y), line, font=fnt, fill=fill)
            y += fnt.size + gap
            line = word
        else:
            line = trial
    d.text((x, y), line, font=fnt, fill=fill)


def screen_left(i, title, footer, colour=WHITE):
    kind, _ = ITEMS[i]
    img = Image.new("RGB", (W, H), (6, 6, 10))
    d = ImageDraw.Draw(img)
    d.text((16, 12), f"{kind.upper()}   item {i + 1} of {len(ITEMS)}", font=F_SMALL, fill=GREY)
    wrap(d, title, F_BIG, 16, 56, 448, colour)
    wrap(d, footer, F_SMALL, 16, 208, 448, ORANGE, gap=4)
    send(0, img)


def screen_right(lines, pad_grid=False):
    img = Image.new("RGB", (W, H), (6, 6, 10))
    d = ImageDraw.Draw(img)
    y = 12
    for text, colour in lines:
        wrap(d, text, F_MID, 16, y, 448 if not pad_grid else 260, colour)
        y += 34
    if pad_grid:                                  # 4x4 as on the hardware: sensor 0 = top-left
        for s in range(16):
            x0, y0 = 300 + (s % 4) * 42, 70 + (s // 4) * 42
            v = min(255, pads[s] * 255 // 2000)
            d.rectangle([x0, y0, x0 + 38, y0 + 38], fill=(v, v // 2, 0) if pads[s] > 60 else (24, 24, 32))
    send(1, img)


# ---------------------------------------------------------------- detection per kind
def detect(kind, touch_bits, nav):
    """Wait for a reading. Returns ('result', data), ('back', None) or ('skip', None)."""
    k0 = knob_raw()
    move = [0] * 9
    t_move = None
    peak = [0] * 16
    t_draw = 0
    while True:
        poll(15)
        p = nav.pressed()
        if BACK in p or LEFT in p:
            return "back", None
        if RIGHT in p:
            return "skip", None
        new = bits() - baseline - NAV
        if kind == "touch":
            if new:
                time.sleep(0.15)
                poll(1)
                return "result", {"bits": sorted(bits() - baseline - NAV)}
        elif kind == "button":
            new -= touch_bits
            if new:
                time.sleep(0.04)
                poll(1)
                return "result", {"bits": sorted(bits() - baseline - NAV - touch_bits)}
        elif kind == "turn":
            k = knob_raw()
            for f in range(9):
                move[f] += abs(wrapdiff(k[f], k0[f]))
            k0 = k
            if t_move is None and max(move) > 20:
                t_move = time.monotonic()
            if t_move and time.monotonic() - t_move > 1.5:
                order = sorted(range(9), key=lambda f: -move[f])
                return "result", {"field": order[0], "movement": move,
                                  "also": [f for f in order[1:] if move[f] > move[order[0]] * 0.2]}
        elif kind == "pad":
            peak = [max(a, b) for a, b in zip(peak, pads)]
            if time.monotonic() - t_draw > 0.12:
                screen_right([("live pad pressure (sensor grid):", GREY)], pad_grid=True)
                t_draw = time.monotonic()
            if max(peak) > 1000 and max(pads) < 150:
                order = sorted(range(16), key=lambda s: -peak[s])
                return "result", {"sensor": order[0], "peak": peak,
                                  "also": [s for s in order[1:] if peak[s] > 300]}


def describe(kind, data):
    if data is None:
        return "skipped"
    if kind in ("touch", "button"):
        return " + ".join(f"byte {i} bit {b}" for i, b in data["bits"])
    if kind == "turn":
        s = f"field {data['field']} (bytes {15 + 2 * data['field']}-{16 + 2 * data['field']})"
        return s + (f"   also moved: {data['also']}" if data["also"] else "")
    s = f"sensor {data['sensor']}  peak {data['peak'][data['sensor']]}"
    return s + (f"   also: {data['also']}" if data["also"] else "")


# ---------------------------------------------------------------- main loop
results = json.load(open(OUT)) if os.path.exists(OUT) else {}
results.setdefault("_meta", {})["baseline_bits"] = sorted(baseline)
results["_meta"]["navigation"] = {"ENTER": ENTER, "BACK": BACK, "jog RIGHT": RIGHT, "jog LEFT": LEFT}


def save():
    with open(OUT, "w") as f:
        json.dump(results, f, indent=1)


def touch_bits_now():
    return {tuple(b) for k, n in ITEMS if k == "touch" and results.get(n, {}).get("data")
            for b in results[n]["data"]["bits"]}


HELP = "ENTER keep  ·  BACK try again / previous  ·  jog → skip  ·  jog ← previous"
try:
    # start screen doubles as a test of ENTER
    screen_left(START, "Press ENTER to start", HELP)
    screen_right([("Mapping run v2", WHITE), ("Nothing is saved until you press ENTER on a result.", GREY)])
    nav = Nav()
    while ENTER not in nav.pressed():
        poll(20)
    wait_all_released()

    i = START
    while i < len(ITEMS):
        kind, name = ITEMS[i]
        prev = results.get(name)
        screen_left(i, name, HELP)
        screen_right([("previous: " + (describe(kind, prev["data"]) if prev else "none yet"), GREY)],
                     pad_grid=(kind == "pad"))
        wait_all_released()
        nav = Nav()
        what, data = detect(kind, touch_bits_now(), nav)
        if what == "back":
            i = max(0, i - 1)
            print(f"<- back to item {i + 1}", flush=True)
            continue
        if what == "skip":
            results[name] = {"kind": kind, "data": None}
            print(f"{i + 1:3d} {name}: skipped", flush=True)
            save()
            i += 1
            continue
        # show the reading and wait for ENTER (keep) or BACK (retry)
        screen_left(i, name, "ENTER = keep  ·  BACK = try again  ·  jog → skip", GREEN)
        screen_right([("got:", GREY), (describe(kind, data), GREEN)])
        wait_all_released()
        nav = Nav()
        while True:
            poll(20)
            p = nav.pressed()
            if ENTER in p:
                results[name] = {"kind": kind, "data": data}
                print(f"{i + 1:3d} {name}: {describe(kind, data)}", flush=True)
                save()
                i += 1
                break
            if BACK in p or LEFT in p:
                print(f"{i + 1:3d} {name}: retry", flush=True)
                break
            if RIGHT in p:
                results[name] = {"kind": kind, "data": None}
                print(f"{i + 1:3d} {name}: skipped", flush=True)
                save()
                i += 1
                break
        wait_all_released()
    screen_left(len(ITEMS) - 1, "All done. Thank you!", "results saved")
    screen_right([("Mapping run v2 finished.", GREEN)])
finally:
    save()
    hdev.close()
    usb.util.release_interface(udev, 4)
    usb.util.dispose_resources(udev)
    print("saved", OUT, flush=True)
