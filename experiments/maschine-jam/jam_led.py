"""Send one LED output report to the Maschine Jam (17cc:1500).

Only the LED reports 0x80, 0x81, 0x82 are allowed (sizes from the HID descriptor). Feature reports
and 0xF4 are never sent.

Usage:
    jam_led.py REPORT [fill=V] [ramp] [OFFSET=V ...] [A-B=V ...]
      REPORT   0x80 | 0x81 | 0x82
      fill=V   every byte = V (default 0)
      ramp     byte n = n
      OFFSET=V one byte (0-based, after the report id); A-B=V a range
    jam_led.py off            all three reports to 0
"""
import sys

import hid

VID, PID = 0x17CC, 0x1500
SIZES = {0x80: 53, 0x81: 80, 0x82: 88}


def num(s):
    return int(s, 0)


def send(dev, rid, payload):
    assert rid in SIZES and len(payload) == SIZES[rid]
    n = dev.write(bytes([rid]) + bytes(payload))
    print(f"report 0x{rid:02x}: wrote {n} bytes")


info = next((d for d in hid.enumerate(VID, PID) if d.get("usage_page") == 0xFF01), None)
if info is None:
    sys.exit("Maschine Jam not found (is another script holding it?)")
dev = hid.device()
dev.open_path(info["path"])
try:
    if sys.argv[1] == "off":
        for rid, size in SIZES.items():
            send(dev, rid, [0] * size)
    else:
        rid = num(sys.argv[1])
        if rid not in SIZES:
            sys.exit(f"only {', '.join(hex(r) for r in SIZES)} allowed")
        data = [0] * SIZES[rid]
        for arg in sys.argv[2:]:
            if arg == "ramp":
                data = [i & 0x7F for i in range(SIZES[rid])]
            elif arg.startswith("fill="):
                data = [num(arg[5:])] * SIZES[rid]
            else:
                where, val = arg.split("=")
                a, _, b = where.partition("-")
                for i in range(num(a), num(b or a) + 1):
                    data[i] = num(val)
        send(dev, rid, data)
finally:
    dev.close()
