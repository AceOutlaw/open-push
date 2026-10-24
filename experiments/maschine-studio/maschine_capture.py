"""Read-only capture of Maschine Studio input: HID reports (interface 2) and MIDI Port 1.

Nothing is ever written to the device. Prints each HID report when it differs from the
previous report with the same report ID, plus every MIDI message, with timestamps.
"""
import sys
import time

import hid
import mido

VID, PID = 0x17CC, 0x1300
DURATION = float(sys.argv[1]) if len(sys.argv) > 1 else 40.0

t0 = time.monotonic()


def ts():
    return f"{time.monotonic() - t0:7.3f}"


def on_midi(msg):
    print(f"{ts()} MIDI  {msg}", flush=True)


infos = [d for d in hid.enumerate(VID, PID)]
for d in infos:
    print(f"HID candidate: iface={d.get('interface_number')} usage_page=0x{d.get('usage_page', 0):04x} "
          f"usage={d.get('usage')} path={d['path']!r}", flush=True)
target = next((d for d in infos if d.get("usage_page") == 0xFF01), infos[0] if infos else None)
if target is None:
    sys.exit("No Maschine Studio HID interface found")

dev = hid.device()
dev.open_path(target["path"])
dev.set_nonblocking(True)
print(f"Opened HID {target['path']!r}; manufacturer={dev.get_manufacturer_string()!r} "
      f"product={dev.get_product_string()!r}", flush=True)

midi_in = None
try:
    midi_in = mido.open_input("Maschine Studio Port 1", callback=on_midi)
    print("Listening on MIDI 'Maschine Studio Port 1'", flush=True)
except Exception as exc:  # the port may be missing or busy
    print(f"MIDI not opened: {exc}", flush=True)

print(f"=== capturing for {DURATION:.0f}s: press pads, buttons, knobs, jog wheel ===", flush=True)
last = {}
counts = {}
while time.monotonic() - t0 < DURATION:
    data = dev.read(512)
    if not data:
        time.sleep(0.002)
        continue
    rid = data[0]
    counts[rid] = counts.get(rid, 0) + 1
    if last.get(rid) != data:
        print(f"{ts()} HID id=0x{rid:02x} len={len(data):3d} {bytes(data).hex(' ')}", flush=True)
        last[rid] = data

dev.close()
if midi_in:
    midi_in.close()
print("=== done. reports per ID:", {f"0x{k:02x}": v for k, v in sorted(counts.items())}, flush=True)
