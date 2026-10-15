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
python3 tools/seqtrak_protocol.py bridge    # which SysEx addresses the bridge uses, vs. the spec
```
`tests/test_seqtrak_protocol.py` runs the check and fails if the bridge uses a SysEx address the spec doesn't have.

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
