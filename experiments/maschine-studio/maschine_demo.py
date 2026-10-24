"""Maschine Studio live demo: the whole surface, with no NI software.

  pads       glow in the selected group's colour, brighter the harder you press
  groups A-H pick the pad colour (selected group bright, the others dim in their own colour)
  meters     left = hardest pad right now (red clip near full), right = VOLUME knob; white, CUE = blue
  jog wheel  moves a lit segment around the ring; the jog label nearest to it lights
  buttons    light while held (dim backlight otherwise); PLAY / REC / SHIFT / CUE toggle
  screens    knobs 1-8 (left: 1-4, right: 5-8), pad grid, last button, volume, jog

Maps come from our own runs: map-run2.json (inputs) and led-map.json (LEDs).
HID interface 2 (read + LED output reports), display interface 4 (endpoint 0x03). Never touches DFU.
Usage: python maschine_demo.py [seconds]
"""
import colorsys
import glob
import json
import os
import sys
import threading
import time

import hid
import numpy as np
import usb.backend.libusb1
import usb.core
import usb.util
from PIL import Image, ImageDraw, ImageFont

VID, PID = 0x17CC, 0x1300
W, H = 480, 272
REF = os.path.dirname(os.path.abspath(__file__))          # map-run2.json, led-map.json live here
DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 600.0
SIZES = {0x80: 62, 0x81: 44, 0x82: 52, 0x83: 55}
BUTTON_BYTES = [i for i in range(1, 15) if i != 13]
DIM = 32                                    # resting backlight for buttons and jog labels (0-127)
GROUP_HUES = [0.0, 0.08, 0.15, 0.33, 0.5, 0.6, 0.75, 0.88]   # A..H
DIM_OF = {"PLAY": 72, "REC": 72}          # coloured LEDs look darker at the same value
TOGGLES = {"PLAY", "REC", "SHIFT", "CUE"}         # CUE = meters blue (as NI does), else white

# ---------------------------------------------------------------- maps
m2 = json.load(open(f"{REF}/map-run2.json"))
BIT_NAME = {(7, 4): "ENTER", (7, 7): "BACK", (7, 5): "jog RIGHT arrow", (7, 6): "jog LEFT arrow"}
for name, v in m2.items():
    if not name.startswith("_") and v.get("data") and v["kind"] == "button":
        BIT_NAME[tuple(v["data"]["bits"][0])] = name
LED_OF = {}                                 # button name -> (report, byte)
for key, what in json.load(open(f"{REF}/led-map.json")).items():
    rid, byte = key.split(":")
    if what in BIT_NAME.values():
        LED_OF.setdefault(what, (int(rid, 16), int(byte)))
PAD_RGB = {n: (0x80, 1 + 3 * (n - 1)) if n <= 8 else (0x81, 1 + 3 * (n - 9)) for n in range(1, 17)}
GROUP_RGB = {g: (0x82, 1 + 3 * g) for g in range(8)}
METER_L, METER_R = range(1, 17), range(17, 33)        # report 0x83, bottom -> top, last = red
JOG_RING = range(41, 56)                              # 15 segments, index 0 = 12 o'clock, clockwise
# jog labels: report 0x83 byte -> ring segment it sits next to (calibration.json)
JOG_LABEL_AT = {36: 0, 37: 2, 40: 6, 39: 7.5, 38: 9, 35: 13}   # CHANNEL BROWSE VOLUME SWING TUNE EDIT
METER_WHITE = 33                                      # 0x83 byte 33 on = meters white, off = blue
PAD_IDLE = 30


def pad_from_sensor(s):
    return 13 - 4 * (s // 4) + (s % 4)


# ---------------------------------------------------------------- state
class State:
    def __init__(self):
        self.lock = threading.Lock()
        self.held = set()                   # button names currently down
        self.toggled = set()
        self.last_button = "-"
        self.knobs = [64] * 9               # 0..127; index 8 = VOLUME
        self.knob_raw = [None] * 9
        self.knob_acc = [0.0] * 9
        self.pads = [0] * 16                # by pad number - 1
        self.jog = 0                        # accumulated detents
        self.jog_raw = None
        self.group = 0


state = State()
running = True
hdev = hid.device()


def input_thread():
    while running:
        r = hdev.read(64, 50)
        if not r:
            continue
        with state.lock:
            if r[0] == 0x01 and len(r) >= 33:
                down = {BIT_NAME.get((i, b), f"b{i}.{b}") for i in BUTTON_BYTES for b in range(8)
                        if r[i] >> b & 1 and (i, b) != (11, 1) and i != 12}
                for name in down - state.held:
                    state.last_button = name
                    if name in TOGGLES:
                        state.toggled ^= {name}
                    if name.startswith("GROUP ") and len(name) == 7:
                        state.group = "ABCDEFGH".index(name[-1])
                state.held = down
                for k in range(9):
                    raw = r[15 + 2 * k] | (r[16 + 2 * k] << 8)
                    prev, state.knob_raw[k] = state.knob_raw[k], raw
                    if prev is None:
                        continue
                    d = (raw - prev) % 1000
                    d = d - 1000 if d > 500 else d
                    state.knob_acc[k] += d / 8
                    step = int(state.knob_acc[k])
                    state.knob_acc[k] -= step
                    state.knobs[k] = max(0, min(127, state.knobs[k] + step))
                j = r[13] & 0x0F
                if state.jog_raw is not None:
                    d = (j - state.jog_raw) % 16
                    state.jog += d - 16 if d > 8 else d
                state.jog_raw = j
            elif r[0] == 0x20 and len(r) >= 25:
                for g in range(8):
                    a, b, c = r[1 + 3 * g], r[2 + 3 * g], r[3 + 3 * g]
                    state.pads[pad_from_sensor(2 * g) - 1] = (a << 4) | (b >> 4)
                    state.pads[pad_from_sensor(2 * g + 1) - 1] = ((b & 0xF) << 8) | c


# ---------------------------------------------------------------- LEDs
def rgb(hue, level):
    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    return [int(r * level), int(g * level), int(b * level)]


meter_peak = [0.0, 0.0]


def build_leds(s):
    rep = {rid: [rid] + [0] * n for rid, n in SIZES.items()}
    # buttons: dim backlight, bright when held or toggled on
    for name, (rid, byte) in LED_OF.items():
        rep[rid][byte] = 127 if (name in s["held"] or name in s["toggled"]) else DIM_OF.get(name, DIM)
    # pads: group colour, brightness from pressure
    hue = GROUP_HUES[s["group"]]
    for n in range(1, 17):
        p = s["pads"][n - 1]
        level = PAD_IDLE if p < 80 else min(127, PAD_IDLE + p * (127 - PAD_IDLE) // 3000)
        rid, byte = PAD_RGB[n]
        rep[rid][byte:byte + 3] = rgb(hue, level)
    # groups: each in its own colour, the selected one bright
    for g in range(8):
        rid, byte = GROUP_RGB[g]
        rep[rid][byte:byte + 3] = rgb(GROUP_HUES[g], 127 if g == s["group"] else 14)
    # meters (with a short fall-off)
    meter_peak[0] = max(max(s["pads"]) / 4095 * 16, meter_peak[0] - 0.6)
    meter_peak[1] = s["knobs"][8] / 127 * 16
    for side, seg in ((0, METER_L), (1, METER_R)):
        lit = int(meter_peak[side] + 0.5)
        for k, byte in enumerate(seg):
            if k < 15:
                rep[0x83][byte] = 100 if k < lit else 0
            else:
                rep[0x83][byte] = 127 if lit >= 16 else 0          # red top = clip
    # jog ring: a bright head with a short tail; labels step with it
    head = s["jog"] % 15
    for k, byte in enumerate(JOG_RING):
        dist = (head - k) % 15
        rep[0x83][byte] = {0: 127, 1: 40, 2: 12}.get(dist, 0)
    def ring_dist(a, b):
        d = abs(a - b) % 15
        return min(d, 15 - d)
    nearest = min(JOG_LABEL_AT, key=lambda byte: ring_dist(JOG_LABEL_AT[byte], head))
    for byte in JOG_LABEL_AT:
        rep[0x83][byte] = 127 if byte == nearest else DIM
    rep[0x83][METER_WHITE] = 0 if "CUE" in s["toggled"] else 127
    return rep


# ---------------------------------------------------------------- screens
def font(size, bold=False):
    return ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", size, index=1 if bold else 0)


F_NUM, F_LABEL, F_SMALL = font(40, True), font(16), font(13)
BG, FG, GREY = (8, 8, 12), (240, 240, 245), (120, 120, 135)


def draw_screen(screen, s, fps):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    hue = GROUP_HUES[s["group"]]
    accent = tuple(int(c * 2) for c in rgb(hue, 127))
    for col in range(4):
        k = screen * 4 + col
        x0, val = col * 120, s["knobs"][k]
        d.text((x0 + 10, 8), f"KNOB {k + 1}", font=F_LABEL, fill=GREY)
        d.text((x0 + 10, 30), f"{val:3d}", font=F_NUM, fill=FG)
        top, bottom = 90, 196
        d.rectangle([x0 + 14, top, x0 + 106, bottom], outline=(40, 40, 52))
        if val:
            d.rectangle([x0 + 15, min(bottom - 1, bottom - int((bottom - top) * val / 127)), x0 + 105, bottom - 1],
                        fill=accent)
        if col < 3:
            d.line([x0 + 119, 8, x0 + 119, 200], fill=(30, 30, 40))
    if screen == 0:
        d.text((10, 208), f"button: {s['last_button']}", font=F_LABEL, fill=FG)
        d.text((10, 230), f"group {'ABCDEFGH'[s['group']]}   volume {s['knobs'][8]:3d}   jog {s['jog']:+d}",
               font=F_LABEL, fill=GREY)
        on = " ".join(sorted(s["toggled"])) or "-"
        d.text((10, 252), f"on: {on}    {fps:4.1f} fps", font=F_SMALL, fill=GREY)
    else:                                   # 4x4 pad grid, pad 1 bottom-left, as on the hardware
        for n in range(1, 17):
            row, col = 3 - (n - 1) // 4, (n - 1) % 4
            x, y = 8 + col * 58, 206 + row * 16
            p = s["pads"][n - 1]
            fill = tuple(int(c * 2) for c in rgb(hue, min(127, p * 127 // 3000))) if p >= 80 else (22, 22, 30)
            d.rectangle([x, y, x + 52, y + 13], fill=fill)
        d.text((250, 214), "pads (pad 1 bottom-left)", font=F_SMALL, fill=GREY)
        d.text((250, 236), f"hardest: {max(s['pads']):4d}", font=F_SMALL, fill=GREY)
    return img


def to_rgb565_be(img):
    a = np.asarray(img, dtype=np.uint16)
    return (((a[..., 0] >> 3) << 11) | ((a[..., 1] >> 2) << 5) | (a[..., 2] >> 3)).astype(">u2")


def tile_msg(screen, x, y, w, h, px):
    m = bytes([0x84, 0, screen, 0x60, 0, 0, 0, 0]) + x.to_bytes(2, "big") + y.to_bytes(2, "big")
    m += w.to_bytes(2, "big") + h.to_bytes(2, "big") + bytes([0]) + ((w * h) // 2).to_bytes(3, "big") + px
    return m + bytes([3, 0, 0, 0, 0x40, 0, screen, 0])


# ---------------------------------------------------------------- main loop
def main():
    global running
    lib = glob.glob(os.popen("brew --prefix libusb").read().strip() + "/lib/libusb-1.0*.dylib")[0]
    udev = usb.core.find(idVendor=VID, idProduct=PID,
                         backend=usb.backend.libusb1.get_backend(find_library=lambda _: lib))
    if udev is None:
        sys.exit("Maschine Studio not found")
    usb.util.claim_interface(udev, 4)
    hdev.open_path(next(d for d in hid.enumerate(VID, PID) if d.get("usage_page") == 0xFF01)["path"])
    t_in = threading.Thread(target=input_thread, daemon=True)
    t_in.start()

    last_led = {}
    last_img = [None, None]
    frames, fps = 0, 0.0
    t_start = t_fps = next_tick = time.monotonic()
    tick = 0
    try:
        while time.monotonic() - t_start < DURATION:
            with state.lock:
                s = {"held": set(state.held), "toggled": set(state.toggled), "last_button": state.last_button,
                     "knobs": list(state.knobs), "pads": list(state.pads), "jog": state.jog,
                     "group": state.group}
            for rid, buf in build_leds(s).items():          # LEDs at 60 Hz, only reports that changed
                if last_led.get(rid) != buf:
                    hdev.write(buf)
                    last_led[rid] = buf
            if tick % 2 == 0:                                # screens at 30 Hz, only tiles that changed
                for screen in (0, 1):
                    cur = to_rgb565_be(draw_screen(screen, s, fps))
                    for ty in range(0, H, 34):
                        for tx in range(0, W, 120):
                            block = cur[ty:ty + 34, tx:tx + 120]
                            if last_img[screen] is not None and np.array_equal(
                                    block, last_img[screen][ty:ty + 34, tx:tx + 120]):
                                continue
                            udev.write(0x03, tile_msg(screen, tx, ty, 120, 34, block.tobytes()), timeout=1000)
                    last_img[screen] = cur
                frames += 1
            tick += 1
            now = time.monotonic()
            if now - t_fps >= 5:
                fps = frames / (now - t_fps)
                frames, t_fps = 0, now
                print(f"{now - t_start:6.0f}s  screens {fps:4.1f} fps  last button {s['last_button']}  "
                      f"group {'ABCDEFGH'[s['group']]}  jog {s['jog']:+d}  hardest pad {max(s['pads'])}", flush=True)
            next_tick += 1 / 60
            time.sleep(max(0.0, next_tick - time.monotonic()))
    finally:
        running = False
        t_in.join(timeout=1)
        for rid, n in SIZES.items():                         # all LEDs off on exit
            hdev.write([rid] + [0] * n)
        hdev.close()
        usb.util.release_interface(udev, 4)
        usb.util.dispose_resources(udev)
        print("stopped", flush=True)


if __name__ == "__main__":
    main()
