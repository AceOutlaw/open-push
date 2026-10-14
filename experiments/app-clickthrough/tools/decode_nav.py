#!/usr/bin/env python3
"""Decode P0-NAV: every Parameter Request the app made, the Seqtrak's reply, and the official name
from Yamaha's Data List (Parameter Change Table, md extract). Writes a TSV + prints a summary."""
import collections
import glob
import re
import sys

ROOT = str(__import__("pathlib").Path(__file__).resolve().parents[3])  # repo root
MD = ROOT + "/reference files/Yamaha/Seqtrak Data List V2/md/"
CAP = ROOT + "/experiments/app-clickthrough/captures/P0-NAV.txt"
HEX2 = re.compile(r"^[0-9A-Fa-f]{2}$")
TMPL = re.compile(r"^[0-9A-Fa-fpeon]{2}$")


def toks(cell):
    return [t.strip() for t in cell.replace("**", "").split("<br>") if t.strip()]


# ---- official table ----
official = {}  # (H, Mtemplate, L) -> (size, range, name, desc, default)
for f in sorted(glob.glob(MD + "3[4-6]-*.md")):
    H = M = None
    for row in open(f, encoding="utf-8"):
        if not row.startswith("|") or row.startswith("|---") or "**Addre" in row or "**Addres" in row:
            continue
        r = row.rstrip("\n").strip()
        cells = r[1:-1].split("|") if r.endswith("|") else r[1:].split("|")
        if len(cells) < 4:
            continue
        c1 = toks(cells[0])
        rest_from = 1
        Ls = []
        if len(c1) >= 2 and HEX2.match(c1[0]) and len(c1[1]) == 1 and c1[1] in "0123456789":
            c1[1] = c1[1] + "p"  # "31<br>2" + "<br>p" split across rows
        if len(c1) >= 2 and HEX2.match(c1[0]) and TMPL.match(c1[1]):
            H, M = c1[0].upper(), c1[1]
            if len(c1) >= 3 and HEX2.match(c1[2]):
                Ls = [c1[2].upper()]
                rest_from = 1
            else:
                Ls = [t.upper() for t in toks(cells[1]) if HEX2.match(t)]
                rest_from = 2
        elif not c1:
            Ls = [t.upper() for t in toks(cells[1]) if HEX2.match(t)]
            rest_from = 2
        elif len(c1) == 1 and HEX2.match(c1[0]) and H not in (None, "11", "12"):
            Ls = [c1[0].upper()]  # blocks whose L sits in the first column
            rest_from = 1
        else:
            continue
        if H is None or not Ls:
            continue
        rest = cells[rest_from:]
        # rest = size, range, name, desc, default, notes  (size may be missing when merged into L cell)
        if rest and re.fullmatch(r"(\s*(\d+|nn)\s*(<br>)?)*", rest[0]):
            rest = rest[1:]
        rng, name, desc, dflt = (toks(rest[i]) if i < len(rest) else [] for i in range(4))
        for i, L in enumerate(Ls):
            pick = lambda a: a[i] if i < len(a) else (a[0] if len(a) == 1 else "")
            official.setdefault((H, M, L), (pick(rng), pick(name), pick(desc), pick(dflt)))


for row in open(ROOT + "/docs/Seqtrak/midi-data-table.md", encoding="utf-8"):
    pass
CLEAN_3040 = {}
sec = None
for row in open(ROOT + "/docs/Seqtrak/midi-data-table.md", encoding="utf-8"):
    if row.startswith("## "):
        sec = row
    elif sec and "(30 40 xx)" in sec and row.startswith("| ") and not row.startswith("| Offset"):
        c = [x.strip() for x in row.strip().strip("|").split("|")]
        if HEX2.match(c[0]):
            official.setdefault(("30", "40", c[0].upper()), ("", c[2], c[3], c[4]))


def lookup(h, m, l):
    if (h, m, l) in official:  # exact block first (e.g. 30 47 before template 30 4n)
        return (h, m, l), official[(h, m, l)]
    for (H, M, L), v in official.items():
        if H != h or L != l:
            continue
        if all(t == a or t in "peon" for t, a in zip(M, m)):
            return (H, M, L), v
    return None, None


# ---- capture: requests + replies ----
reqs = collections.OrderedDict()  # addr -> first time
replies = {}
for line in open(CAP):
    p = line.split()
    if len(p) < 3 or p[1] not in ("OUT", "IN"):
        continue
    b = p[2:]
    if b[:6] == ["F0", "43", "30", "7F", "1C", "0C"] and p[1] == "OUT":
        reqs.setdefault(tuple(b[6:9]), p[0])
    elif b[:6] == ["F0", "43", "10", "7F", "1C", "0C"] and p[1] == "IN":
        replies.setdefault(tuple(b[6:9]), b[9:-1])

pages = []
for line in open(ROOT + "/experiments/app-clickthrough/clicklog.md"):
    mm = re.search(r"done ~(\d\d:\d\d:\d\d)-(\d\d:\d\d:\d\d): (.*)", line)
    if mm:
        pages.append((mm.group(1), mm.group(2), mm.group(3)))


def page_at(t):
    t = t[:8]
    best = ""
    for a, b, d in pages:
        if a <= t:
            best = d
    return best[:90]


out = open(sys.argv[1], "w")
out.write("time\taddr\treply\tofficial_block\tname\trange\tdesc\tdefault\tapp_pages_in_that_batch\n")
unk = collections.Counter()
known = 0
for a, t in reqs.items():
    key, v = lookup(*a)
    r = " ".join(replies.get(a, [])) or "(no reply)"
    if v:
        known += 1
        out.write(f"{t}\t{' '.join(a)}\t{r}\t{' '.join(key)}\t{v[1]}\t{v[0]}\t{v[2]}\t{v[3]}\t{page_at(t)}\n")
    else:
        unk[a[0] + " " + a[1]] += 1
        out.write(f"{t}\t{' '.join(a)}\t{r}\t\t\t\t\t\t{page_at(t)}\n")
print("official entries parsed:", len(official))
print("unique addresses requested:", len(reqs), "named:", known)
print("unnamed by block:", unk.most_common(40))
