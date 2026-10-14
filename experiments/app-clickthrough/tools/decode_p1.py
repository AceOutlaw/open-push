#!/usr/bin/env python3
"""Summarise each Phase 1 capture: clicklog lines for the block + the app's writes (OUT, non-request),
grouped by address with the value sequence and the official Data List name."""
import collections
import glob
import os
import re
import sys

sys.argv = [sys.argv[0], "/dev/null"]
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "decode_nav.py")).read().split("# ---- capture")[0])

D = ROOT + "/experiments/app-clickthrough/"
clog = collections.defaultdict(list)
for line in open(D + "clicklog.md"):
    p = [x.strip() for x in line.lstrip("- ").split("|")]
    if len(p) >= 3:
        clog[p[1]].append(" | ".join(p[2:]))
plan = {}
for line in open(D + "PLAN.md"):
    p = [x.strip() for x in line.strip().strip("|").split("|")]
    if len(p) >= 4 and re.match(r"\d{3}-", p[0]):
        plan[p[0]] = p[2] + " [" + p[3] + "] " + (p[4] if len(p) > 4 else "")


def name_of(a):
    if len(a) < 3:
        return ""
    key, v = lookup(a[0], a[1], a[2])
    return v[1] if v else ""


def summarise(path):
    bid = os.path.basename(path)[:-4]
    writes = collections.OrderedDict()
    other = collections.Counter()
    nreq = 0
    for line in open(path):
        p = line.split()
        if len(p) < 3 or p[1] != "OUT":
            continue
        b = p[2:]
        if b[:6] == ["F0", "43", "30", "7F", "1C", "0C"]:
            nreq += 1
            continue
        if b[:6] == ["F0", "43", "10", "7F", "1C", "0C"]:
            a = tuple(b[6:9])
            writes.setdefault(a, []).append(" ".join(b[9:-1]))
        else:
            other[" ".join(b[:3]) if b[0] != "F0" else " ".join(b[:10]) + "…"] += 1
    out = [f"## {bid}"]
    pr = plan.get(bid) or plan.get(re.sub(r"[a-z]$", "", bid))
    if pr:
        out.append(f"plan: {pr}")
    for c in clog.get(bid, []):
        if "wrote READY" in c or "wrote DONE" in c:
            continue
        out.append(f"log: {c[:300]}")
    out.append(f"requests: {nreq}")
    for a, vals in writes.items():
        if a[:2] in (("01", "10"),) and a[2] in ("56", "57", "58", "50", "51", "52"):
            continue
        seq = vals if len(vals) <= 12 else vals[:5] + [f"…({len(vals)})…"] + vals[-5:]
        out.append(f"W {' '.join(a)} [{name_of(a)}]: " + " / ".join(seq))
    for k, n in other.most_common(8):
        out.append(f"other {k} ×{n}")
    return "\n".join(out)


files = sorted(glob.glob(D + "captures/1*.txt"))
with open(D + "p1_summary.txt", "w") as f:
    for p in files:
        f.write(summarise(p) + "\n\n")
print(len(files))
