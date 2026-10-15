# Seqtrak protocol spec

A description of the Yamaha SEQTRAK's MIDI protocol **on its own**, independent of the Push bridge. Any program
can use it: this bridge, a desktop editor, other hardware. Every message carries its **status** and the
**evidence** behind it, so it's always clear what is proven and what is still a guess.

| File | What |
|---|---|
| `spec/*.toml` | **The source of truth.** One `[[message]]` per message, grouped by area. Edit these. |
| `PROTOCOL.md` | Generated readable reference (all messages, by area). Don't edit. |
| `DATALIST-PARAMS.md` | Generated from Yamaha's Data List extract (local only, not in git — it reproduces Yamaha's tables). Shows which official parameters the spec covers. |
| `../../../tools/seqtrak_protocol.py` | Validate, render, and cross-check the bridge. |

```bash
python3 tools/seqtrak_protocol.py check     # validate the spec
python3 tools/seqtrak_protocol.py render    # regenerate PROTOCOL.md
python3 tools/seqtrak_protocol.py datalist  # regenerate DATALIST-PARAMS.md (needs reference files/)
python3 tools/seqtrak_protocol.py bridge    # the SysEx addresses and plain MIDI the bridge sends, vs. the spec
```
`tests/test_seqtrak_protocol.py` runs the check and fails if the bridge uses a SysEx address, CC number,
program change, note or transport message the spec doesn't describe.

## Checking the spec against a real Seqtrak

`tools/seqtrak_verify.py` runs where the Seqtrak is plugged in (the Pi, next to the running bridge) and
replays the spec. Re-run it after every firmware update.

```bash
python3 tools/seqtrak_verify.py                    # read-only: request every readable address
python3 tools/seqtrak_verify.py --write            # also: write test value, read back, restore the original
python3 tools/seqtrak_verify.py --probe            # also request addresses the spec doesn't call readable
python3 tools/seqtrak_verify.py --compare runs/2026-10-15-read.json   # what changed since that run
```
It reports addresses that should answer and don't, addresses that answer but aren't marked readable, and
write tests that pass (evidence for ✅) or fail. Keep the results file in `runs/`.

An entry steers its test with an inline `test` table:
```toml
test = { address = ["30 50 00"], write = ["50", "60"] }   # concrete addresses; values to try writing
test = { skip = "an empty step sends no reply" }         # why it can't be checked automatically
test = { write = { "00 00 25" = ["01", "00"], "00 00 27" = ["40", "38"] } }   # writes for several addresses
```
Without `test.address`, placeholder nibbles become 0 (`30 5p 00` → `30 50 00`, KICK); a whole-byte placeholder
(`nn`, `ss`) needs one.
A plain `write` list is for the first test address. A write uses the first value that differs from the current one, and always restores it.
A reply proves the address is readable, and a passing write proves the command. Neither proves what the value
means: that still needs the device or an ear.

## A message entry

```toml
[[message]]
id = "project.swing"                 # unique, area.name
name = "Swing"
area = "project"                     # system, transport, project, patterns, track, mixer, sound, dx, sampler,
                                     # effects, steps, notes, song, device-state, bulk, midi
kind = "parameter"                   # parameter (SysEx change/request), bulk, cc, note, program, realtime
address = "30 40 7C"                 # parameter/bulk; lowercase letters are placeholders (below)
also = ["..."]                       # optional: more addresses the same entry covers
form = "..."                         # for cc / note / program / realtime: the message form
data = "2 bytes = 128 + offset ..."  # format and encoding
values = { "00" = "..." }            # optional: value table
dir = ["command", "report", "readable"]   # sent to it / sent by it / answers a Parameter Request
status = "verified"
meaning = "Swing of even steps."
guide = "§4.5.2"                     # user guide section, when there is one
evidence = ["App 112-01 ...", "Bridge swing encoder confirmed on hardware ..."]
notes = "..."
```

**Placeholders:** `p` part 0–A (KICK … SAMPLER), `t` drum track 0–6, `e` sampler pad / element, `o` DX operator,
`g` note-list group (0 SYNTH 1, 1 SYNTH 2, 2 DX, 3 SAMPLER), `n` / `ss` / `nn` any value.

**Status** (strongest first; only `verified` counts as proven):

| Status | Means | Needs |
|---|---|---|
| ✅ `verified` | Proven on the hardware: sent and read back, seen on the device, or heard | evidence |
| 📱 `app` | The official SEQTRAK app sends it for that control (click-through captures) | evidence |
| 📗 `official` | In Yamaha's Data List / user guide, not tested by us | |
| 📥 `reported` | The Seqtrak sends it; meaning from context; untested as a command | |
| 🟡 `inferred` | Meaning inferred from evidence; needs a test | |
| ❓ `unknown` | Seen, meaning unknown | |

**Rule:** a message the Seqtrak *sends* can be a report only (`74 7g` is the classic case). Promote an entry to
`verified` only after sending it and reading the result back, or seeing it on the device, and add that test to
`evidence`.

## Where the evidence lives
- Yamaha: `reference files/Yamaha/User Guide/` (guide text), `reference files/Yamaha/Seqtrak Data List V2/`
- SEQTRAK app click-through: `experiments/app-clickthrough/captures/<block>.txt`, write-ups in
  `docs/Seqtrak/APP-CLICKTHROUGH-P0.md`, `-P1.md`
- Device captures and tests: `docs/Seqtrak/STEP-SEQUENCER.md`, `UNDOCUMENTED-MESSAGES.md`,
  `REVERSE-ENGINEERING-LOG-2026-10.md`
