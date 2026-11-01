"""Read-only capture of Maschine Jam (17cc:1500) HID input.

Nothing is ever written to the device. Prints each HID report when it differs from the
previous report with the same report ID, and lists which bytes changed.

Usage: venv/bin/python experiments/maschine-jam/jam_capture.py [seconds] [> log.txt]
"""
import sys
import time

import hid

VID, PID = 0x17CC, 0x1500
DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 60.0

infos = hid.enumerate(VID, PID)
for d in infos:
    print(f"HID: iface={d.get('interface_number')} usage_page=0x{d.get('usage_page', 0):04x} "
          f"usage={d.get('usage')}", flush=True)
target = next((d for d in infos if d.get("usage_page") == 0xFF01), infos[0] if infos else None)
if target is None:
    sys.exit("No Maschine Jam HID interface found")

dev = hid.device()
dev.open_path(target["path"])
dev.set_nonblocking(True)

t0 = time.monotonic()
print(f"=== capturing {DURATION:.0f}s ===", flush=True)
last, counts = {}, {}
while time.monotonic() - t0 < DURATION:
    data = dev.read(512)
    if not data:
        time.sleep(0.002)
        continue
    rid = data[0]
    counts[rid] = counts.get(rid, 0) + 1
    prev = last.get(rid)
    if prev != data:
        t = time.monotonic() - t0
        if prev is None or len(prev) != len(data):
            print(f"{t:7.3f} id=0x{rid:02x} len={len(data)} FULL {bytes(data).hex(' ')}", flush=True)
        else:
            diff = " ".join(f"[{i}]{prev[i]:02x}->{data[i]:02x}" for i in range(len(data)) if prev[i] != data[i])
            print(f"{t:7.3f} id=0x{rid:02x} {diff}", flush=True)
        last[rid] = data
print("report counts:", {f"0x{k:02x}": v for k, v in counts.items()}, flush=True)
dev.close()
