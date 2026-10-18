"""Compare two SEQTRAK app project exports (.Y3P) and list what changed.

    python3 tools/y3p_diff.py before.Y3P after.Y3P

Export the same project twice with ONE change in between (tempo, one step, one volume ...): every changed
byte in project.bin is then that change. Format notes: docs/Seqtrak/Y3P-PROJECT-FILE.md.
Read-only: the exports are opened as ZIP files, nothing is extracted or run.
"""
import sys
import zipfile

# Regions of project.bin known so far (docs/Seqtrak/Y3P-PROJECT-FILE.md)
REGIONS = [(0x0000, "header / name"), (0x0069, "project settings"), (0x0074, "chord tables"),
           (0x0CE1, "A/D insertion"), (0x0D6A, "track sound blocks (0x5C5 each)"),
           (0x4903, "SAMPLER pads (0x75 each)"), (0x4C38, "?"), (0x4CA9, "pattern / song memory")]


def region(offset):
    name = REGIONS[0][1]
    for start, label in REGIONS:
        if offset >= start:
            name = label
    if name.startswith("track sound"):
        return f"{name}: track {(offset - 0x0D6A) // 0x5C5 + 1}, +0x{(offset - 0x0D6A) % 0x5C5:X}"
    if name.startswith("SAMPLER"):
        return f"{name}: pad {(offset - 0x4903) // 0x75 + 1}, +0x{(offset - 0x4903) % 0x75:X}"
    return name


def runs(a, b):
    """Changed byte ranges as (start, end) pairs."""
    out, i, n = [], 0, max(len(a), len(b))
    while i < n:
        if i >= len(a) or i >= len(b) or a[i] != b[i]:
            j = i
            while j < n and (j >= len(a) or j >= len(b) or a[j] != b[j]):
                j += 1
            out.append((i, j))
            i = j
        else:
            i += 1
    return out


def main():
    za, zb = zipfile.ZipFile(sys.argv[1]), zipfile.ZipFile(sys.argv[2])
    names_a, names_b = set(za.namelist()), set(zb.namelist())
    for n in sorted(names_a - names_b):
        print(f"only in first:  {n}")
    for n in sorted(names_b - names_a):
        print(f"only in second: {n}")
    for n in sorted(names_a & names_b):
        a, b = za.read(n), zb.read(n)
        if a == b:
            continue
        if n.endswith(".xml"):
            print(f"\n{n} changed:\n--- {a.decode('utf-8', 'replace')}\n+++ {b.decode('utf-8', 'replace')}")
            continue
        changed = runs(a, b)
        print(f"\n{n}: {len(changed)} changed range(s), sizes {len(a)} -> {len(b)}")
        for s, e in changed[:200]:
            where = f"  [{region(s)}]" if n == "project.bin" else ""
            print(f"  0x{s:06X}-0x{e - 1:06X}: {a[s:min(e, s + 24)].hex(' ')}  ->  {b[s:min(e, s + 24)].hex(' ')}{where}")
        if len(changed) > 200:
            print(f"  ... {len(changed) - 200} more")


if __name__ == "__main__":
    main()
