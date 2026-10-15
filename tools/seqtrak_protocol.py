#!/usr/bin/env python3
"""Seqtrak protocol spec: load, validate, render, and cross-reference the bridge.

The spec lives in docs/Seqtrak/protocol/spec/*.toml (one [[message]] table per message).
It describes the Yamaha SEQTRAK's MIDI protocol on its own, independent of the Push bridge.

Usage:
    python3 tools/seqtrak_protocol.py check     # validate the spec
    python3 tools/seqtrak_protocol.py render    # write docs/Seqtrak/protocol/PROTOCOL.md
    python3 tools/seqtrak_protocol.py datalist  # write DATALIST-PARAMS.md from Yamaha's Data List extract
    python3 tools/seqtrak_protocol.py bridge    # what the bridge uses, vs. the spec
"""
import pathlib
import re
import sys
import tomllib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC_DIR = ROOT / "docs" / "Seqtrak" / "protocol" / "spec"
OUT = ROOT / "docs" / "Seqtrak" / "protocol" / "PROTOCOL.md"
DATALIST_OUT = ROOT / "docs" / "Seqtrak" / "protocol" / "DATALIST-PARAMS.md"
DATALIST_MD = ROOT / "reference files" / "Yamaha" / "Seqtrak Data List V2" / "md"
BRIDGE = [ROOT / "src" / "open_push" / "seqtrak" / "app.py", ROOT / "src" / "open_push" / "seqtrak" / "protocol.py"]

KINDS = {"parameter", "bulk", "cc", "note", "program", "realtime"}
DIRS = {"command", "report", "readable"}
# Strongest first. Only "verified" means proven on this unit (readback, the device, or ear).
STATUSES = ["verified", "app", "official", "reported", "inferred", "unknown"]
STATUS_TEXT = {
    "verified": "✅ verified on the hardware (readback, device LEDs or by ear)",
    "app": "📱 sent by the official SEQTRAK app for this control (not yet re-tested by us)",
    "official": "📗 in Yamaha's Data List / user guide, not tested by us",
    "reported": "📥 sent by the Seqtrak; meaning from context, not tested as a command",
    "inferred": "🟡 meaning inferred from evidence, needs a test",
    "unknown": "❓ seen, meaning unknown",
}
ICON = {k: v.split()[0] for k, v in STATUS_TEXT.items()}
REQUIRED = ["id", "name", "area", "kind", "status", "meaning"]


def load(spec_dir=SPEC_DIR):
    entries = []
    for path in sorted(spec_dir.glob("*.toml")):
        with open(path, "rb") as f:
            data = tomllib.load(f)
        for e in data.get("message", []):
            e["_file"] = path.name
            entries.append(e)
    return entries


def validate(entries):
    problems = []
    seen = {}
    for e in entries:
        where = f"{e.get('_file')}:{e.get('id', '?')}"
        for key in REQUIRED:
            if not e.get(key):
                problems.append(f"{where}: missing '{key}'")
        if e.get("kind") not in KINDS:
            problems.append(f"{where}: kind '{e.get('kind')}' not in {sorted(KINDS)}")
        if e.get("status") not in STATUSES:
            problems.append(f"{where}: status '{e.get('status')}' not in {STATUSES}")
        for d in e.get("dir", []):
            if d not in DIRS:
                problems.append(f"{where}: dir '{d}' not in {sorted(DIRS)}")
        if e.get("kind") in ("parameter", "bulk") and not e.get("address"):
            problems.append(f"{where}: parameter/bulk needs 'address'")
        for a in [e.get("address")] + e.get("also", []):
            if a and not address_regex(a):
                problems.append(f"{where}: bad address '{a}'")
        if e.get("status") in ("verified", "app") and not e.get("evidence"):
            problems.append(f"{where}: status {e['status']} needs evidence")
        if e.get("id") in seen:
            problems.append(f"{where}: duplicate id (also in {seen[e['id']]})")
        seen[e.get("id")] = e.get("_file")
    return problems


def address_regex(address):
    """'30 5p 0F' -> regex over 'HH HH HH'. Lowercase letters are variable nibbles; 'ss' etc. any byte."""
    tokens = address.split()
    if not 1 <= len(tokens) <= 3:
        return None
    parts = []
    for tok in tokens:
        if len(tok) != 2:
            return None
        part = ""
        for ch in tok:
            if ch in "0123456789ABCDEF":
                part += ch
            elif ch.islower():
                part += "[0-9A-F]"
            else:
                return None
        parts.append(part)
    return re.compile("^" + " ".join(parts) + "$")


def find(entries, address):
    """Spec entries whose address (or one of its 'also' addresses) matches a concrete 'HH HH HH'."""
    return [e for e in entries
            if any(address_regex(a).match(address) for a in [e.get("address")] + e.get("also", []) if a)]


# ---------------------------------------------------------------------------- render

AREA_ORDER = ["system", "transport", "project", "patterns", "track", "mixer", "sound", "dx", "sampler",
              "effects", "steps", "notes", "song", "device-state", "bulk", "midi"]


def render(entries):
    areas = {}
    for e in entries:
        areas.setdefault(e["area"], []).append(e)
    counts = {s: sum(1 for e in entries if e["status"] == s) for s in STATUSES}
    out = ["# Seqtrak MIDI protocol (generated)", "",
           "> Generated by `python3 tools/seqtrak_protocol.py render` from `spec/*.toml` — edit the TOML, not this file.",
           "> The spec describes the Yamaha SEQTRAK on its own; the Push bridge is one user of it.", "",
           "**Status:** " + " · ".join(f"{ICON[s]} {s} {counts[s]}" for s in STATUSES), ""]
    out += [f"- {STATUS_TEXT[s]}" for s in STATUSES]
    out += ["", "Frame for `parameter` messages: change `F0 43 10 7F 1C 0C [address] [data] F7`, "
            "request `F0 43 30 7F 1C 0C [address] F7`. Placeholders: `p` part 0–A (KICK…SAMPLER), "
            "`t` drum track 0–6, `e` sampler pad / element, `o` DX operator 0–3, `g` note-list group "
            "(0 SYNTH 1, 1 SYNTH 2, 2 DX, 3 SAMPLER), `ss` step, `nn`/`cc` a whole byte.", ""]
    for area in sorted(areas, key=lambda a: AREA_ORDER.index(a) if a in AREA_ORDER else 99):
        out += [f"## {area}", "", "| | Message | Address / form | Data | Dir | Meaning | Evidence |",
                "|---|---|---|---|---|---|---|"]
        for e in sorted(areas[area], key=lambda e: (e.get("address") or e.get("form") or "", e["id"])):
            form = (" ".join(f"`{a}`" for a in [e["address"]] + e.get("also", []))
                    if e.get("address") else e.get("form", ""))
            data = e.get("data", "")
            if e.get("values"):
                data += (" — " if data else "") + ", ".join(f"`{k}` {v}" for k, v in e["values"].items())
            meaning = e["meaning"] + (f" ({e['guide']})" if e.get("guide") else "")
            if e.get("notes"):
                meaning += f"<br>{e['notes']}"
            ev = "<br>".join(e.get("evidence", []))
            out.append(f"| {ICON[e['status']]} | **{e['name']}** | {form} | {data} | "
                       f"{', '.join(e.get('dir', []))} | {meaning} | {ev} |")
        out.append("")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------- Data List layer

def datalist_params():
    """Parse Yamaha's Parameter Change Table (PDF-to-markdown extract, local only) into
    {(H, M-template, L): (range, name, description, default)}. The extract's tables are messy,
    so a few names can be misaligned; check the PDF before relying on a single row."""
    hex2 = re.compile(r"^[0-9A-Fa-f]{2}$")
    tmpl = re.compile(r"^[0-9A-Fa-fpeon]{2}$")
    toks = lambda c: [t.strip() for t in c.replace("**", "").split("<br>") if t.strip()]
    params = {}
    for f in sorted(DATALIST_MD.glob("3[4-6]-*.md")):
        H = M = None
        for row in open(f, encoding="utf-8"):
            if not row.startswith("|") or row.startswith("|---") or "**Addre" in row:
                continue
            r = row.rstrip("\n").strip()
            cells = r[1:-1].split("|") if r.endswith("|") else r[1:].split("|")
            if len(cells) < 4:
                continue
            c1 = toks(cells[0])
            if len(c1) >= 2 and hex2.match(c1[0]) and len(c1[1]) == 1 and c1[1].isdigit():
                c1[1] += "p"
            rest_from, Ls = 1, []
            if len(c1) >= 2 and hex2.match(c1[0]) and tmpl.match(c1[1]):
                H, M = c1[0].upper(), c1[1]
                if len(c1) >= 3 and hex2.match(c1[2]):
                    Ls = [c1[2].upper()]
                else:
                    Ls, rest_from = [t.upper() for t in toks(cells[1]) if hex2.match(t)], 2
            elif not c1:
                Ls, rest_from = [t.upper() for t in toks(cells[1]) if hex2.match(t)], 2
            elif len(c1) == 1 and hex2.match(c1[0]) and H not in (None, "11", "12"):
                Ls = [c1[0].upper()]
            if H is None or not Ls:
                continue
            rest = cells[rest_from:]
            if rest and re.fullmatch(r"(\s*(\d+|nn)\s*(<br>)?)*", rest[0]):
                rest = rest[1:]
            cols = [toks(rest[i]) if i < len(rest) else [] for i in range(4)]
            for i, L in enumerate(Ls):
                pick = lambda a: a[i] if i < len(a) else (a[0] if len(a) == 1 else "")
                params.setdefault((H, M, L), tuple(pick(c) for c in cols))
    return params


def render_datalist(entries):
    params = datalist_params()
    out = ["# Seqtrak Data List parameters (generated)", "",
           "> Generated by `python3 tools/seqtrak_protocol.py datalist` from Yamaha's Data List V2 (PDF-to-markdown",
           "> extract in `reference files/`, local only). Parsed automatically: a few names may sit in the wrong",
           "> column — check the PDF before relying on one row. **Spec** = the curated `spec/*.toml` entry covering it.", "",
           f"{len(params)} parameter addresses.", "",
           "| Address | Name | Range | Description | Default | Spec |", "|---|---|---|---|---|---|"]
    def key(k):
        return (k[0], k[1], k[2])
    for (H, M, L), (rng, name, desc, dflt) in sorted(params.items(), key=lambda kv: key(kv[0])):
        concrete = f"{H} {M.replace('p', '0').replace('e', '0').replace('o', '0').replace('n', '0').upper()} {L}"
        hits = find(entries, concrete)
        spec = ", ".join(f"{ICON[h['status']]} `{h['id']}`" for h in hits[:2])
        clean = lambda x: x.replace("|", "/")
        out.append(f"| `{H} {M} {L}` | {clean(name)} | {clean(rng)} | {clean(desc)} | {clean(dflt)} | {spec} |")
    return "\n".join(out) + "\n", len(params)


# ---------------------------------------------------------------------------- bridge

# First address bytes that are Seqtrak parameter blocks (filters out other hex lists such as SysEx headers)
SEQTRAK_H = {"00", "01", "0B", "0C", "0D", "10", "11", "12", "30", "31", "41", "42", "48", "49", "50",
             "70", "71", "72", "73", "74", "75", "76", "77"}
HEX_ADDR = re.compile(r"\[\s*0x([0-9A-Fa-f]{2})\s*,\s*0x([0-9A-Fa-f]{2})\s*(?:\+[^,\]]*)?,\s*0x([0-9A-Fa-f]{2})\s*\]")


def bridge_addresses(paths=BRIDGE):
    """SysEx addresses written as literals [0xHH, 0xHH, 0xHH] in the bridge (incl. '0x50 + track' forms)."""
    found = {}
    for path in paths:
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if line.strip().startswith("#"):
                continue
            for m in HEX_ADDR.finditer(line):
                addr = " ".join(x.upper() for x in m.groups())
                if addr.split()[0] in SEQTRAK_H and "0x" in line[m.start():m.start() + 4]:
                    found.setdefault(addr, []).append(f"{path.name}:{n}")
    return found


def bridge_report(entries):
    used = bridge_addresses()
    lines, missing, weak = [], [], []
    for addr, where in sorted(used.items()):
        hits = find(entries, addr)
        if not hits:
            missing.append((addr, where))
        elif all(h["status"] not in ("verified", "app", "official") for h in hits):
            weak.append((addr, [h["status"] for h in hits], where))
    lines.append(f"Bridge uses {len(used)} literal SysEx addresses.")
    lines.append(f"Not in the spec: {len(missing)}")
    lines += [f"  {a}  ({', '.join(w[:3])})" for a, w in missing]
    lines.append(f"Only reported/inferred/unknown in the spec: {len(weak)}")
    lines += [f"  {a}  {s}  ({', '.join(w[:3])})" for a, s, w in weak]
    return "\n".join(lines), missing


def main(argv):
    cmd = argv[1] if len(argv) > 1 else "check"
    entries = load()
    problems = validate(entries)
    if cmd == "check":
        print(f"{len(entries)} messages")
        print("\n".join(problems) or "spec OK")
        return 1 if problems else 0
    if problems:
        print("\n".join(problems))
        return 1
    if cmd == "render":
        OUT.write_text(render(entries), encoding="utf-8")
        print(f"wrote {OUT.relative_to(ROOT)} ({len(entries)} messages)")
    elif cmd == "datalist":
        text, n = render_datalist(entries)
        DATALIST_OUT.write_text(text, encoding="utf-8")
        print(f"wrote {DATALIST_OUT.relative_to(ROOT)} ({n} parameters)")
    elif cmd == "bridge":
        print(bridge_report(entries)[0])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
