"""List the input bits from a jam_capture.py log in the order they were first pressed.

Bit index = (byte - 2) * 8 + bit, counting report 0x01 bytes 2-16 (byte 1 is the encoder).
Byte 16 bit 3 (index 115) flickers constantly and is ignored.

Usage: venv/bin/python experiments/maschine-jam/jam_order.py LOG
"""
import re
import sys

NOISY = {115}
seen, order = set(), []
for line in open(sys.argv[1]):
    parts = line.split()
    if len(parts) < 3 or not re.match(r"^[\d.]+$", parts[0]):
        continue
    for tok in parts[2:]:
        m = re.match(r"\[(\d+)\]([0-9a-f]+)->([0-9a-f]+)", tok)
        if not m or m[1] == "1":
            continue
        byte, old, new = int(m[1]), int(m[2], 16), int(m[3], 16)
        for k in range(8):
            idx = (byte - 2) * 8 + k
            if new >> k & 1 and not old >> k & 1 and idx not in NOISY and idx not in seen:
                seen.add(idx)
                order.append((parts[0], idx, byte, k))
for n, (t, idx, byte, k) in enumerate(order, 1):
    print(f"{n:3d}  t={t:>8}  bit {idx:3d}  (byte {byte}, mask 0x{1 << k:02x})")
