# 4. Seqtrak Protocol

**What**: Working out what the Yamaha Seqtrak says and accepts over MIDI (CC, SysEx, step data, device
reports, project files), and documenting it with its evidence. It's kept as its own deliverable: useful to
anyone, not only to the bridge.

**State**: 🔄 Active (Dec 2025 → now).

## What's here

| Path | What |
|---|---|
| `docs/Seqtrak/protocol/spec/*.toml` | **The source of truth**: every message with a status (✅ verified … ❓ unknown) and evidence |
| `docs/Seqtrak/protocol/PROTOCOL.md` | Generated from the spec (`python3 tools/seqtrak_protocol.py render`) |
| `docs/Seqtrak/sysex-protocol-reference.md` | What every message and parameter does |
| `docs/Seqtrak/STEP-SEQUENCER.md` | The verified step protocol in full |
| `docs/Seqtrak/Y3P-PROJECT-FILE.md` | Decoding the app's `.Y3P` project export (`tools/y3p_diff.py`) |
| `docs/Seqtrak/REVERSE-ENGINEERING-LOG-2026-10.md` | What was learned and how |
| `docs/Seqtrak/UNDOCUMENTED-MESSAGES.md`, `midi-data-table.md`, `midi-data-format.md` | Unknowns and Yamaha's official tables |
| `tools/seqtrak_protocol.py`, `tools/seqtrak_verify.py` | Spec tooling and hardware verification |
| `scripts/debug/` | Hardware test scripts (sampler delete, variations, steps) |
| `experiments/app-clickthrough/` | Captures of the Seqtrak app's own messages, driven screen by screen |
| `docs/dev-notes/` | Debugging sessions (sampler delete, session mode, step sequencer) |

## Method

1. Read Yamaha's guide and data lists first.
2. Capture: what the Seqtrak app sends (spy recorder), what the Seqtrak reports (Pi capture).
3. Verify on hardware by readback or by eye. A message the Seqtrak sends may be a report, not a command.
4. Write the finding into the spec immediately. The tests fail if the bridge uses an address the spec
   lacks.

## Scope

The unit runs OS 1.21.3. Yamaha's OS 2.0 guide describes features this unit may not have; verify first.
