"""LED mapping run 2: light one LED byte at a time; answer with the buttons above the screens.

The 8 display buttons are a menu (labels drawn on the screens under each button):
  1 nothing   2 EDIT   3 CHANNEL   4 BROWSE   5 TUNE   6 SWING   7 VOLUME   8 other
  press the JOG WHEEL down = jog ring
Pick one (it highlights; you can change your mind), then
  ENTER = confirm and go to the next byte
  BACK  = clear the pick, or (with nothing picked) go back one byte
For LEDs on a pad or a button: press that pad/button instead, then ENTER.

Results merge into OUT.json by "report:byte". Steps from argv, e.g. 0x83:33-55 0x80:51-54.
Writes HID LED output reports (0x80-0x83) and the display; never touches DFU.
Usage: python maschine_ledmap2.py OUT.json MAP2.json RANGE [RANGE ...]
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
OUT, MAP2 = sys.argv[1], sys.argv[2]
SIZES = {0x80: 62, 0x81: 44, 0x82: 52, 0x83: 55}
STEPS = []
for spec in sys.argv[3:]:
    rid, rng = spec.split(":")
    lo, hi = (rng.split("-") + [rng])[:2]
    STEPS += [(int(rid, 0), b) for b in range(int(lo), int(hi) + 1)]

BUTTON_BYTES = [i for i in range(1, 15) if i != 13]
TOUCH = {(12, b) for b in range(8)}
ENTER, BACK, JOG_PRESS = (7, 4), (7, 7), (7, 3)
MENU = ["nothing", "EDIT", "CHANNEL", "BROWSE", "TUNE", "SWING", "VOLUME", "other"]

m2 = json.load(open(MAP2))
NAME = {(7, 5): "jog RIGHT arrow", (7, 6): "jog LEFT arrow"}
DISPLAY = {}                                      # bit -> display button index 0..7
for name, v in m2.items():
    if name.startswith("_") or not v.get("data") or v["kind"] != "button":
        continue
    b = tuple(v["data"]["bits"][0])
    NAME[b] = name
    if name.startswith("display button"):
        DISPLAY[b] = int(name.split()[2]) - 1

# ---------------------------------------------------------------- devices
lib = glob.glob(os.popen("brew --prefix libusb").read().strip() + "/lib/libusb-1.0*.dylib")[0]
udev = usb.core.find(idVendor=VID, idProduct=PID,
                     backend=usb.backend.libusb1.get_backend(find_library=lambda _: lib))
usb.util.claim_interface(udev, 4)
hdev = hid.device()
hdev.open_path(next(d for d in hid.enumerate(VID, PID) if d.get("usage_page") == 0xFF01)["path"])
rep = list(hdev.get_input_report(0x01, 64))
pads = [0] * 16


def poll(timeout_ms=10):
    global rep
    r = hdev.read(64, max(1, timeout_ms))
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


def led(rid, byte=None, value=127):
    buf = [0] * (SIZES[rid] + 1)
    buf[0] = rid
    if byte:
        buf[byte] = value
    hdev.write(buf)


baseline = bits()

# ---------------------------------------------------------------- screens
F_BIG = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 28, index=1)
F_MID = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 18)
F_MENU = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 17, index=1)


def send(screen, img):
    a = np.asarray(img, dtype=np.uint16)
    px = (((a[..., 0] >> 3) << 11) | ((a[..., 1] >> 2) << 5) | (a[..., 2] >> 3)).astype(">u2")
    for y in range(0, H, 34):
        m = bytes([0x84, 0, screen, 0x60, 0, 0, 0, 0, 0, 0]) + y.to_bytes(2, "big") + W.to_bytes(2, "big")
        m += (34).to_bytes(2, "big") + bytes([0]) + (W * 17).to_bytes(3, "big") + px[y:y + 34].tobytes()
        m += bytes([3, 0, 0, 0, 0x40, 0, screen, 0])
        udev.write(0x03, m, timeout=1000)


def draw(i, pick, log):
    rid, byte = STEPS[i]
    for screen in (0, 1):
        img = Image.new("RGB", (W, H), (6, 6, 10))
        d = ImageDraw.Draw(img)
        for k in range(4):                          # menu labels under the 4 buttons above this screen
            idx = screen * 4 + k
            x0 = k * 120
            on = pick == MENU[idx]
            d.rectangle([x0 + 4, 4, x0 + 115, 40], fill=(255, 170, 40) if on else (30, 30, 42))
            tw = d.textlength(MENU[idx], font=F_MENU)
            d.text((x0 + 60 - tw / 2, 12), MENU[idx], font=F_MENU, fill=(0, 0, 0) if on else (230, 230, 240))
        if screen == 0:
            d.text((16, 60), f"step {i + 1} of {len(STEPS)}   report {rid:#04x} byte {byte}", font=F_MID,
                   fill=(130, 130, 145))
            d.text((16, 92), "What lit up?", font=F_BIG, fill=(255, 255, 255))
            d.text((16, 136), f"picked: {pick or '-'}", font=F_BIG, fill=(120, 255, 140) if pick else (90, 90, 100))
            d.text((16, 190), "pick above (or press the pad / button / jog)", font=F_MID, fill=(255, 170, 40))
            d.text((16, 220), "ENTER = confirm   BACK = clear / previous", font=F_MID, fill=(255, 170, 40))
        else:
            for k, line in enumerate(log[-6:]):
                d.text((16, 60 + k * 33), line, font=F_MID,
                       fill=(200, 255, 200) if k == len(log[-6:]) - 1 else (150, 150, 165))
        send(screen, img)


results = json.load(open(OUT)) if os.path.exists(OUT) else {}
log = []
try:
    for r in SIZES:
        led(r)
    i, pick = 0, None
    held = set()
    pad_held = False
    while i < len(STEPS):
        rid, byte = STEPS[i]
        for r in SIZES:
            led(r, byte if r == rid else None)
        prev = results.get(f"{rid:#04x}:{byte}")
        pick = None
        draw(i, pick, log + ([f"(earlier answer: {prev})"] if prev else []))
        while True:
            poll(15)
            now = bits() - baseline - TOUCH
            new = now - held
            held = now
            changed = None
            for b in sorted(new):
                if b == ENTER:
                    if pick:
                        changed = "enter"
                elif b == BACK:
                    changed = "back"
                elif b in DISPLAY:
                    pick, changed = MENU[DISPLAY[b]], "pick"
                elif b == JOG_PRESS:
                    pick, changed = "JOG RING", "pick"
                else:
                    pick, changed = NAME.get(b, f"unknown bit b{b[0]}.{b[1]}"), "pick"
            p_now = max(pads) > 1500
            if p_now and not pad_held:
                s = max(range(16), key=lambda k: pads[k])
                pick, changed = f"PAD {13 - 4 * (s // 4) + (s % 4)}", "pick"
            pad_held = max(pads) > 300
            if changed == "pick":
                draw(i, pick, log)
            elif changed == "enter":
                results[f"{rid:#04x}:{byte}"] = pick
                log.append(f"{rid:#04x} byte {byte}: {pick}")
                print(log[-1], flush=True)
                with open(OUT, "w") as f:
                    json.dump(results, f, indent=1)
                i += 1
                break
            elif changed == "back":
                if pick:
                    pick = None
                    draw(i, pick, log)
                else:
                    i = max(0, i - 1)
                    log.append(f"<- back to step {i + 1}")
                    print(log[-1], flush=True)
                    break
    for r in SIZES:
        led(r)
    log.append("LED mapping finished")
    draw(len(STEPS) - 1, None, log)
finally:
    with open(OUT, "w") as f:
        json.dump(results, f, indent=1)
    hdev.close()
    usb.util.release_interface(udev, 4)
    usb.util.dispose_resources(udev)
    print("saved", OUT, flush=True)
