"""Draw text on both Maschine Studio screens. Renders 480x272 images with Pillow, converts to
RGB565 big-endian, sends each screen as 8 horizontal strips (34 rows each) to interface 4 / ep 0x03.
Header 84 00 SS 60 + rect, raw pixel command, then 03 00 00 00 + 40 00 SS 00 (show). Never touches DFU."""
import glob, os, sys, time
from PIL import Image, ImageDraw, ImageFont
import usb.backend.libusb1, usb.core, usb.util

W, H, STRIP = 480, 272, 34

def font(size, bold=False):
    for path in ["/System/Library/Fonts/HelveticaNeue.ttc", "/System/Library/Fonts/Helvetica.ttc"]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size, index=1 if bold else 0)
    return ImageFont.load_default()

def render(lines, accent):
    img = Image.new("RGB", (W, H), (10, 10, 14))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W - 1, 5], fill=accent)
    y = 30
    for text, size, color, bold in lines:
        f = font(size, bold)
        d.text((24, y), text, font=f, fill=color)
        y += int(size * 1.35)
    return img

def to_rgb565(img):
    out = bytearray()
    for r, g, b in img.getdata():
        v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
        out += v.to_bytes(2, "big")
    return bytes(out)

def strip_msg(screen, y, h, pixels):
    pairs = (W * h) // 2
    m = bytes([0x84, 0x00, screen, 0x60, 0, 0, 0, 0])
    m += (0).to_bytes(2, "big") + y.to_bytes(2, "big") + W.to_bytes(2, "big") + h.to_bytes(2, "big")
    m += bytes([0x00]) + pairs.to_bytes(3, "big") + pixels
    m += bytes([0x03, 0, 0, 0, 0x40, 0, screen, 0])
    return m

stamp = time.strftime("%H:%M")
left = render([
    ("open-push", 64, (255, 255, 255), True),
    ("Maschine Studio, freed", 30, (150, 255, 0), False),
    ("no Native Instruments software", 22, (170, 170, 185), False),
    ("pads · knobs · both screens", 22, (170, 170, 185), False),
], accent=(255, 90, 30))
right = render([
    ("Hello from open-push", 46, (255, 255, 255), True),
    ("Python  →  USB  →  screen", 26, (90, 170, 255), False),
    ("RGB565 · 480 × 272 · double-buffered", 20, (170, 170, 185), False),
    (f"drawn at {stamp}", 20, (170, 170, 185), False),
], accent=(90, 170, 255))

lib = glob.glob(os.popen("brew --prefix libusb").read().strip() + "/lib/libusb-1.0*.dylib")[0]
dev = usb.core.find(idVendor=0x17CC, idProduct=0x1300, backend=usb.backend.libusb1.get_backend(find_library=lambda _: lib))
if dev is None: sys.exit("Maschine Studio not found")
usb.util.claim_interface(dev, 4)
try:
    for screen, img in ((0, left), (1, right)):
        raw = to_rgb565(img)
        t0 = time.monotonic(); total = 0
        for y in range(0, H, STRIP):
            h = min(STRIP, H - y)
            total += dev.write(0x03, strip_msg(screen, y, h, raw[y * W * 2:(y + h) * W * 2]), timeout=2000)
        print(f"screen {screen}: {total} bytes in {(time.monotonic() - t0) * 1000:.0f} ms")
finally:
    usb.util.release_interface(dev, 4); usb.util.dispose_resources(dev)
