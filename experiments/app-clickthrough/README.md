# SEQTRAK app click-through experiment

Records the exact MIDI the official SEQTRAK app sends for each control, so the Push bridge can send the same.
Run 2026-10-14 (Phase 0 + Phase 1, 234 blocks). Results: `docs/Seqtrak/APP-CLICKTHROUGH-P0.md` and `-P1.md`.

## What's here
| Path | What |
|---|---|
| `PLAN.md` | Roles, handshake, rules, block list (section 5), capture method (section 6) |
| `status` | One-line handshake file (`READY` / `ARMED` / `DONE` / `SAVED` / `HOLD` + block ID) |
| `clicklog.md` | The clicker's log: what was clicked and what the app showed, per block |
| `captures/<ID>.txt` | One capture per block. `OUT` = app → Seqtrak, `IN` = Seqtrak → app |
| `raw-spy-2026-10-14.log` | Everything recorded on 2026-10-14, uncut |
| `screens/INVENTORY.md` | Every app screen and its controls (Phase 0) |
| `tools/` | Recorder, handshake watcher, decoders |

## Run it again (macOS)
Needs: the SEQTRAK app, [MIDI Monitor](https://www.snoize.com/midimonitor/) installed (its spy driver is used, the
window can stay closed), Xcode command-line tools, and the Seqtrak **plugged in by USB**. Over Bluetooth the app
bypasses CoreMIDI and nothing is captured — check HOME > DEVICE CONNECTION shows the wired icon.

```bash
cd experiments/app-clickthrough
FW="/Applications/MIDI Monitor.app/Contents/Frameworks"
clang -fobjc-arc -framework CoreMIDI -framework Foundation -F"$FW" -framework SnoizeMIDISpy \
  -Wl,-rpath,"$FW" tools/seqspy.m -o tools/seqspy
tools/seqspy >> spy.log &          # recorder: every byte to/from the SEQTRAK
python3 tools/capturer.py &        # handshake: READY→ARMED, DONE→captures/<ID>.txt + SAVED
echo "HOLD new run" > status       # the clicker starts each block by writing READY <ID>
```
Check the recorder first: `PLAN.md` block `P0-PROBE` (move one slider) must give `OUT` lines.

## Decode
```bash
python3 tools/decode_nav.py nav.tsv   # P0-NAV: every address the app read + reply + official name
python3 tools/decode_p1.py            # Phase 1: per-block writes → p1_summary.txt
```
The decoders read Yamaha's Data List extract in `reference files/` (local only, not in git — rsync it from
another machine).

## Lessons from the 2026-10-14 run
- One control per block, ~40 s each; 232 blocks took 2.5 h unattended.
- The app's on-screen value can lag or miss a typed value; the capture is the truth.
- The app re-sends the previously edited field when focus moves, so a block can contain a write from the
  control before it.
- Keep block IDs matched to the plan; a few were reused for other controls (the log says what really happened).
- Add the project grid / rename popup to the never-touch list: a click there switched the Seqtrak's project.
