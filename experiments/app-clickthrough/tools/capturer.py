#!/usr/bin/env python3
"""Capturer side of experiments/app-clickthrough handshake.

READY <ID> -> note start time, write ARMED <ID>
DONE <ID>  -> wait 2 s, cut the local spy log (spy/spy.log) between start-1s and now into
              captures/<ID>.txt, write SAVED <ID>. On failure write HOLD.
"""
import datetime as dt
import pathlib
import time

HERE = pathlib.Path(__file__).resolve().parent

D = HERE.parent  # experiments/app-clickthrough
STATUS = D / "status"
CAP = D / "captures"
LOG = D / "capturer.log"


def say(msg):
    with LOG.open("a") as f:
        f.write(f"{dt.datetime.now():%H:%M:%S} {msg}\n")


SPY = D / "spy.log"  # written by: tools/seqspy >> spy.log


def fetch(start, end):
    # Local spy log (seqspy on skai); times are skai local time.
    try:
        lines = SPY.read_text().splitlines()
    except OSError:
        return None
    return "".join(l + "\n" for l in lines if start <= l[:8] <= end)


armed = {}
say("capturer watching")
while True:
    try:
        line = STATUS.read_text().strip()
    except OSError:
        line = ""
    parts = line.split(None, 1)
    if len(parts) == 2 and parts[0] == "READY":
        bid = parts[1].strip()
        armed[bid] = dt.datetime.now().astimezone() - dt.timedelta(seconds=1)
        STATUS.write_text(f"ARMED {bid}\n")
        say(f"ARMED {bid} from {armed[bid]:%H:%M:%S}")
    elif len(parts) == 2 and parts[0] == "DONE":
        bid = parts[1].strip()
        start = armed.get(bid)
        if start is None:
            STATUS.write_text(f"HOLD capturer never saw READY {bid}\n")
            say(f"DONE without READY: {bid}")
        else:
            time.sleep(2)
            end = dt.datetime.now().astimezone()
            data = fetch(f"{start:%H:%M:%S}", f"{end:%H:%M:%S}")
            if data is None:
                STATUS.write_text(f"HOLD capturer could not read the spy log for {bid}\n")
            else:
                hdr = (f"# {bid}  skai {start:%H:%M:%S}-{end:%H:%M:%S} {start:%Z}\n"
                       "# OUT = sent to SEQTRAK by any Mac app (MIDI Monitor spy), IN = sent by SEQTRAK\n")
                (CAP / f"{bid}.txt").write_text(hdr + data)
                n = data.count("\n")
                STATUS.write_text(f"SAVED {bid}\n")
                say(f"SAVED {bid}: {n} lines")
            armed.pop(bid, None)
    time.sleep(2)
