"""Calibrate the jog ring geometry and hunt for the meters' white LEDs.

Answers come from the 8 buttons above the screens (labels drawn under them); ENTER = next.
Part 1 (ring): the jog wheel moves ONE lit ring segment. Turn until it points at a label, then
         press that label's button. Do as many as you like; ENTER when done.
Part 2 (meters): each test lights something; pick what you see, ENTER for the next test.
Writes HID LED reports and the display only; never touches DFU. Results -> OUT.json
"""
import glob, json, os, sys, time
import hid, numpy as np, usb.backend.libusb1, usb.core, usb.util
from PIL import Image, ImageDraw, ImageFont

VID, PID = 0x17CC, 0x1300
W, H = 480, 272
OUT = sys.argv[1]
SIZES = {0x80: 62, 0x81: 44, 0x82: 52, 0x83: 55}
DISPLAY_BITS = [(9, 0), (9, 7), (9, 6), (9, 1), (9, 5), (9, 2), (9, 4), (9, 3)]   # buttons 1..8
ENTER, BACK = (7, 4), (7, 7)
RING = list(range(41, 56))
LABELS = {35: "EDIT", 36: "CHANNEL", 37: "BROWSE", 38: "TUNE", 39: "SWING", 40: "VOLUME"}

lib = glob.glob(os.popen("brew --prefix libusb").read().strip() + "/lib/libusb-1.0*.dylib")[0]
udev = usb.core.find(idVendor=VID, idProduct=PID, backend=usb.backend.libusb1.get_backend(find_library=lambda _: lib))
usb.util.claim_interface(udev, 4)
hdev = hid.device()
hdev.open_path(next(d for d in hid.enumerate(VID, PID) if d.get("usage_page") == 0xFF01)["path"])
rep = list(hdev.get_input_report(0x01, 64))


def poll():
    global rep
    r = hdev.read(64, 15)
    for _ in range(64):
        if not r:
            break
        if r[0] == 0x01:
            rep = list(r)
        r = hdev.read(64, 1)


def down():
    return {(i, b) for i in (7, 9) for b in range(8) if rep[i] >> b & 1}


def leds(spec):
    """spec: {report: {byte: value}}; every report is sent, unnamed bytes off."""
    for rid, n in SIZES.items():
        buf = [rid] + [0] * n
        for byte, v in spec.get(rid, {}).items():
            buf[byte] = v
        hdev.write(buf)


F_BIG = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 24, index=1)
F_MID = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 17)
F_MENU = ImageFont.truetype("/System/Library/Fonts/HelveticaNeue.ttc", 15, index=1)


def send(screen, img):
    a = np.asarray(img, dtype=np.uint16)
    px = (((a[..., 0] >> 3) << 11) | ((a[..., 1] >> 2) << 5) | (a[..., 2] >> 3)).astype(">u2")
    for y in range(0, H, 34):
        m = bytes([0x84, 0, screen, 0x60, 0, 0, 0, 0, 0, 0]) + y.to_bytes(2, "big") + W.to_bytes(2, "big")
        m += (34).to_bytes(2, "big") + bytes([0]) + (W * 17).to_bytes(3, "big") + px[y:y + 34].tobytes()
        udev.write(0x03, m + bytes([3, 0, 0, 0, 0x40, 0, screen, 0]), timeout=1000)


def draw(menu, lines, picked=None):
    for screen in (0, 1):
        img = Image.new("RGB", (W, H), (6, 6, 10))
        d = ImageDraw.Draw(img)
        for k in range(4):
            label = menu[screen * 4 + k]
            on = label and label == picked
            d.rectangle([k * 120 + 4, 4, k * 120 + 115, 38], fill=(255, 170, 40) if on else (30, 30, 42))
            tw = d.textlength(label, font=F_MENU)
            d.text((k * 120 + 60 - tw / 2, 12), label, font=F_MENU, fill=(0, 0, 0) if on else (230, 230, 240))
        y = 54
        for text, big in (lines[0] if screen == 0 else lines[1]):
            d.text((14, y), text, font=F_BIG if big else F_MID, fill=(255, 255, 255) if big else (255, 170, 40))
            y += 34 if big else 26
        send(screen, img)


results = {"ring": {}, "meters": []}


def save():
    with open(OUT, "w") as f:
        json.dump(results, f, indent=1)


try:
    # ---------------------------------------------------------------- part 1: ring
    menu = ["TOP 12:00", "EDIT", "CHANNEL", "BROWSE", "TUNE", "SWING", "VOLUME", "BOTTOM 6:00"]
    seg, jog_prev, held = 0, rep[13] & 15, down()
    jog_sum = 0

    def ring_screen(note=""):
        assigned = ", ".join(f"{k}={v}" for k, v in sorted(results["ring"].items(), key=lambda x: x[1]))
        draw(menu, ([("RING: turn the jog wheel", True), (f"lit segment = byte {RING[seg]} (index {seg})", True),
                     ("point it at a label, press that label above", False),
                     ("ENTER when done", False)],
                    [("assigned:", False), (assigned[:60] or "-", False), (assigned[60:120], False),
                     (note, False), (f"jog clicks so far: {jog_sum:+d}", False)]))

    leds({0x83: {RING[seg]: 127}})
    ring_screen()
    while True:
        poll()
        j = rep[13] & 15
        d = (j - jog_prev) % 16
        d = d - 16 if d > 8 else d
        jog_prev = j
        if d:
            jog_sum += d
            seg = (seg + d) % 15
            leds({0x83: {RING[seg]: 127}})
            ring_screen()
        now = down()
        new, held = now - held, now
        if ENTER in new:
            break
        for b in new:
            if b in DISPLAY_BITS:
                label = menu[DISPLAY_BITS.index(b)]
                results["ring"][label] = seg
                save()
                ring_screen(f"{label} = segment {seg}")
                print("ring", label, "=", seg, flush=True)

    # ---------------------------------------------------------------- part 2: meters
    menu = ["no change", "BLUE", "WHITE", "blue+white", "dimmer", "IN/OUT marks", "other", ""]
    seg15 = range(1, 16)
    TESTS = [
        ("meters bytes 1-15 + 17-31 at 127 (reference)", {0x83: {**{b: 127 for b in seg15}, **{b + 16: 127 for b in seg15}}}),
        ("same at 40", {0x83: {**{b: 40 for b in seg15}, **{b + 16: 40 for b in seg15}}}),
        ("same at 127 + 0x83 byte 33", {0x83: {33: 127, **{b: 127 for b in seg15}, **{b + 16: 127 for b in seg15}}}),
        ("same at 127 + 0x83 byte 34", {0x83: {34: 127, **{b: 127 for b in seg15}, **{b + 16: 127 for b in seg15}}}),
        ("same at 255", {0x83: {**{b: 255 for b in seg15}, **{b + 16: 255 for b in seg15}}}),
        ("same at 200", {0x83: {**{b: 200 for b in seg15}, **{b + 16: 200 for b in seg15}}}),
        ("meters + 0x80 bytes 51-54", {0x83: {**{b: 127 for b in seg15}, **{b + 16: 127 for b in seg15}},
                                        0x80: {51: 127, 52: 127, 53: 127, 54: 127}}),
        ("ONLY 0x80 byte 51 (look at IN / OUT marks)", {0x80: {51: 127}}),
        ("ONLY 0x80 byte 52", {0x80: {52: 127}}),
        ("ONLY 0x80 byte 53", {0x80: {53: 127}}),
        ("ONLY 0x80 byte 54", {0x80: {54: 127}}),
        ("ONLY 0x83 bytes 33 + 34", {0x83: {33: 127, 34: 127}}),
    ]
    held = down()
    for n, (desc, spec) in enumerate(TESTS, 1):
        leds(spec)
        picked = None
        lines = ([("METERS: what do you see?", True), (f"test {n} of {len(TESTS)}", False), (desc, False),
                  ("pick above, ENTER = next", False)], [("look at the meters and the", False),
                                                          ("small IN / OUT 1-3 marks above them", False)])
        draw(menu, lines)
        while True:
            poll()
            now = down()
            new, held = now - held, now
            if ENTER in new and picked:
                break
            for b in new:
                if b in DISPLAY_BITS and menu[DISPLAY_BITS.index(b)]:
                    picked = menu[DISPLAY_BITS.index(b)]
                    draw(menu, lines, picked)
        results["meters"].append({"test": desc, "seen": picked})
        save()
        print(f"meter test {n}: {desc}: {picked}", flush=True)
    leds({})
    draw(["", "", "", "", "", "", "", ""], ([("Calibration done", True)], [("thank you", False)]))
finally:
    save()
    hdev.close()
    usb.util.release_interface(udev, 4)
    usb.util.dispose_resources(udev)
    print("saved", OUT, flush=True)
