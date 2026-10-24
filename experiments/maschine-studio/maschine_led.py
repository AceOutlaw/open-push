"""Send one LED output report to the Maschine Studio over HID (interface 2, endpoint 0x02).
Report sizes from the device's own HID descriptor: 0x80 = 62, 0x81 = 44, 0x82 = 52, 0x83 = 55 data bytes.
Usage: python maschine_led.py REPORT OFFSET=VALUE [OFFSET=VALUE ...]   (offsets 1-based, after the id)
Everything not named is sent as 0 (off). Never touches DFU; LED reports only."""
import sys
import hid

SIZES = {0x80: 62, 0x81: 44, 0x82: 52, 0x83: 55}
rid = int(sys.argv[1], 0)
buf = [0] * (SIZES[rid] + 1)
buf[0] = rid
for arg in sys.argv[2:]:
    off, val = arg.split("=")
    buf[int(off, 0)] = int(val, 0)
d = hid.device()
d.open_path(next(x for x in hid.enumerate(0x17CC, 0x1300) if x.get("usage_page") == 0xFF01)["path"])
n = d.write(buf)
d.close()
print(f"report {rid:#04x}: wrote {n} bytes, nonzero = {[(i, v) for i, v in enumerate(buf) if i and v]}")
