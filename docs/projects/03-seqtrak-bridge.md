# 3. Seqtrak Bridge

**What**: The Push 1 controls a Yamaha Seqtrak, running headless on a Raspberry Pi. The aim is a racked
Seqtrak you never touch: the Push does everything, with enough controls to show what the Seqtrak can do.

**State**: ✅ Deployed and working (Dec 2025 → now). The main project.

## What it does today

Isomorphic keyboard, transport (play/stop/record), mixer (volume, mute, solo), device mode (preset
navigation), step sequencer for drum, melodic and sampler tracks, session view (pattern launcher),
pattern duplicate and double loop. Bugs and gaps are tracked; see below.

## What's here

| Path | What |
|---|---|
| `src/open_push/seqtrak/app.py` | The bridge (~4,950 lines; CRLF line endings). Run: `python3 src/open_push/seqtrak/app.py` |
| `src/open_push/seqtrak/protocol.py` | Seqtrak SysEx messages |
| `src/open_push/seqtrak/requests.py` | Paced Parameter Requests with replies and retries |
| `src/open_push/seqtrak/sync.py`, `presets.py` | State sync and preset names |
| `tests/` | Bridge, protocol, request and sync tests (`pytest tests`) |
| `docs/Seqtrak/BUGS_AND_ENHANCEMENTS.md` | Known bugs |
| `docs/Seqtrak/PARITY.md`, `FUNCTIONALITY-MAP.md` | What's done vs. the Seqtrak and its app |
| `docs/Seqtrak/TERMINOLOGY.md` | Read first: 11 tracks, **6** variations, Pattern (drums) vs. Bar (melodic) |

## Deployment

Runs as the `open-push-seqtrak` service on the Pi (project 5). Deploy only committed code; the Pi records
the deployed commit in `.deployed`.

## Linear

Bugs first (KM-100), then one epic per Seqtrak user-guide chapter (KM-101–113). Architecture work in
KM-244.

## Related

Depends on project 4 for every message it sends, and on project 5 to run.
