#!/usr/bin/env python3
"""Replay the Seqtrak protocol spec against a real SEQTRAK and report what holds.

Runs wherever the Seqtrak is plugged in (normally the Pi bridge, next to the running bridge:
ALSA lets both open the port). Needs mido + python-rtmidi and Python 3.11+.

    python3 tools/seqtrak_verify.py                  # read-only: request every readable address
    python3 tools/seqtrak_verify.py --probe          # also request command/report-only addresses
    python3 tools/seqtrak_verify.py --write          # also write test values, read back, restore
    python3 tools/seqtrak_verify.py --only project.  # entries whose id starts with this
    python3 tools/seqtrak_verify.py --compare old.json   # what changed since an earlier run (firmware update)

A Parameter Request (F0 43 30 7F 1C 0C H M L F7) never changes anything. --write sends real
Parameter Changes (only for entries with a `test.write` in the spec;
a list for the first test address, or a table {address: values}), reads the value back, then
puts the original value back and checks that too. It's audible for a moment if the Seqtrak is playing.

Results go to seqtrak-verify-<time>.json (and are printed). A reply proves the address is
readable; a write that reads back proves the command — that is evidence for promoting an entry
to `verified`. It doesn't prove what the value *means*: that still needs the device or an ear.
"""
import argparse
import datetime
import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import seqtrak_protocol as sp  # noqa: E402

HEADER = [0x43, 0x10, 0x7F, 0x1C, 0x0C]
REQUEST = [0x43, 0x30, 0x7F, 0x1C, 0x0C]
FIRMWARE = "01 00 00"


def hexs(bs):
    return " ".join(f"{b:02X}" for b in bs)


def parse(s):
    return [int(x, 16) for x in s.split()]


def test_addresses(e):
    """Concrete addresses to request for an entry: test.address, else its addresses with placeholder
    nibbles set to 0. A whole-byte placeholder ('nn', 'ss') can't be guessed and needs test.address."""
    t = e.get("test", {})
    if t.get("address"):
        return t["address"] if isinstance(t["address"], list) else [t["address"]], []
    out, skipped = [], []
    for a in [e["address"]] + e.get("also", []):
        toks = a.split()
        if any(tok[0].islower() and tok[0] == tok[1] for tok in toks):   # 'nn', 'ss' (but 'ep' = two nibbles)
            skipped.append(a)
            continue
        out.append(" ".join("".join("0" if c.islower() else c for c in tok) for tok in toks))
    return out, skipped


class Seqtrak:
    def __init__(self, mido, timeout):
        self.mido = mido
        self.timeout = timeout
        out_name = next((n for n in mido.get_output_names() if "SEQTRAK" in n.upper()), None)
        in_name = next((n for n in mido.get_input_names() if "SEQTRAK" in n.upper()), None)
        if not out_name or not in_name:
            sys.exit(f"No SEQTRAK MIDI port. Outputs: {mido.get_output_names()}")
        self.out = mido.open_output(out_name)
        self.inp = mido.open_input(in_name)
        print(f"Seqtrak: {out_name}")

    def read(self, addr):
        """Request one address; the data bytes of the matching reply, or None."""
        for _ in self.inp.iter_pending():
            pass
        self.out.send(self.mido.Message("sysex", data=REQUEST + addr))
        end = time.monotonic() + self.timeout
        while time.monotonic() < end:
            for msg in self.inp.iter_pending():
                d = list(msg.data) if msg.type == "sysex" else []
                if d[:5] == HEADER and d[5:8] == addr:
                    return d[8:]
            time.sleep(0.005)
        return None

    def write(self, addr, data):
        self.out.send(self.mido.Message("sysex", data=HEADER + addr + data))
        time.sleep(0.15)


def run(args):
    import mido
    entries = [e for e in sp.load() if e["kind"] == "parameter" and e["id"].startswith(args.only or "")]
    dev = Seqtrak(mido, args.timeout)
    fw = dev.read(parse(FIRMWARE))
    results = []

    for e in entries:
        readable = "readable" in e.get("dir", [])
        if not readable and not args.probe:
            continue
        if e.get("test", {}).get("skip"):
            results.append({"id": e["id"], "address": e["address"], "test": "read", "result": "skipped",
                            "note": e["test"]["skip"]})
            continue
        addrs, skipped = test_addresses(e)
        for a in skipped:
            results.append({"id": e["id"], "address": a, "test": "read", "result": "skipped",
                            "note": "whole-byte placeholder: add test.address to the spec"})
        for a in addrs:
            data = dev.read(parse(a))
            results.append({"id": e["id"], "address": a, "test": "read", "claims_readable": readable,
                            "status": e["status"], "result": "no reply" if data is None else "answered" if data else "empty reply",
                            "data": hexs(data) if data is not None else None})
            time.sleep(args.gap)

        if args.write:
            for a, values in write_plan(e, addrs):
                results.append(write_test(dev, e, a, values))

    report = {"time": datetime.datetime.now().isoformat(timespec="seconds"),
              "firmware": hexs(fw) if fw else None, "results": results}
    path = pathlib.Path(args.out or f"seqtrak-verify-{datetime.datetime.now():%Y-%m-%d-%H%M%S}.json")
    path.write_text(json.dumps(report, indent=1), encoding="utf-8")
    print_report(report)
    print(f"\nSaved {path}")
    if args.compare:
        print_compare(json.loads(pathlib.Path(args.compare).read_text(encoding="utf-8")), report)


def write_plan(e, addrs):
    """[(address, values)]: test.write is a list (for the first test address) or a table {address: values}."""
    write = e.get("test", {}).get("write")
    if isinstance(write, dict):
        return list(write.items())
    return [(addrs[0], write)] if write and addrs else []


def write_test(dev, e, a, write):
    """Read the original, write the first test value that differs, read back, restore, read back."""
    addr = parse(a)
    r = {"id": e["id"], "address": a, "test": "write", "status": e["status"]}
    orig = dev.read(addr)
    if orig is None:
        return {**r, "result": "no reply", "note": "can't read the original, so nothing was written"}
    value = next((parse(w) for w in write if parse(w) != orig), None)
    if value is None:
        return {**r, "result": "skipped", "note": "every test value equals the current value"}
    dev.write(addr, value)
    back = dev.read(addr)
    dev.write(addr, orig)
    restored = dev.read(addr)
    r.update(original=hexs(orig), wrote=hexs(value), read_back=hexs(back) if back else None,
             restored=hexs(restored) if restored else None)
    if restored != orig:
        r["result"] = "NOT RESTORED"
        r["note"] = f"set it back by hand: F0 {hexs(HEADER)} {a} {hexs(orig)} F7"
    else:
        r["result"] = "pass" if back == value else "FAIL"
    return r


def print_report(report):
    rs = report["results"]
    print(f"\nFirmware (01 00 00): {report['firmware'] or 'no reply'}   {report['time']}")
    reads = [r for r in rs if r["test"] == "read" and r["result"] != "skipped"]
    print(f"Read {len(reads)} addresses: {sum(r['result'] == 'answered' for r in reads)} answered")
    groups = [
        ("Spec says readable, but no reply", lambda r: r["test"] == "read" and r.get("claims_readable")
         and r["result"] == "no reply"),
        ("Answers, but the spec doesn't say readable (add 'readable' to dir)", lambda r: r["test"] == "read"
         and not r.get("claims_readable") and r["result"] == "answered"),
        ("Empty reply: the address exists but returns no value (it may need data, e.g. a scene number)",
         lambda r: r["test"] == "read" and r["result"] == "empty reply"),
        ("Write + readback passed (evidence for 'verified')", lambda r: r["test"] == "write"
         and r["result"] == "pass"),
        ("Write FAILED or not restored", lambda r: r["test"] == "write" and r["result"] in ("FAIL", "NOT RESTORED")),
        ("Skipped", lambda r: r["result"] == "skipped"),
    ]
    for title, pick in groups:
        hit = [r for r in rs if pick(r)]
        if not hit:
            continue
        print(f"\n{title}: {len(hit)}")
        for r in hit:
            extra = {k: r[k] for k in ("original", "wrote", "read_back", "restored", "note") if r.get(k)}
            print(f"  {r['id']:<32} {r['address']}  {r.get('status', '')}  {extra or ''}")


def print_compare(old, new):
    key = lambda r: (r["test"], r["id"], r["address"])
    before = {key(r): r for r in old["results"]}
    print(f"\nCompared with {old['time']} (firmware {old['firmware']} → {new['firmware']}):")
    changed = 0
    for r in new["results"]:
        b = before.get(key(r))
        if not b:
            continue
        lengths = [len((x.get("data") or "").split()) for x in (b, r)]
        if b["result"] != r["result"] or lengths[0] != lengths[1]:
            changed += 1
            print(f"  {r['id']:<32} {r['address']}  {b['result']} ({lengths[0]} bytes) → {r['result']} ({lengths[1]} bytes)")
    print(f"  {changed} changed")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--probe", action="store_true", help="also request addresses the spec doesn't call readable")
    ap.add_argument("--write", action="store_true", help="run the write + readback + restore tests")
    ap.add_argument("--only", help="only entries whose id starts with this")
    ap.add_argument("--out", help="results file (default seqtrak-verify-<time>.json)")
    ap.add_argument("--compare", help="an earlier results file to compare with")
    ap.add_argument("--timeout", type=float, default=0.4, help="seconds to wait for each reply")
    ap.add_argument("--gap", type=float, default=0.02, help="seconds between requests")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
