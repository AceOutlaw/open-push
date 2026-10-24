# 2. Reason Bridge

**What**: The Push as a control surface for Propellerhead Reason. A Python bridge talks to the Push, and
Lua codecs tell Reason Remote what the Push controls.

**State**: 🟡 Basics work (Dec 18–23 2025): isomorphic keyboard with scale colours, scale and root
selection, octave shift, in-key/chromatic toggle, transport, velocity curve, Reason auto-detection and
device names on the LCD. Mixer and device control modes are unfinished. Paused since the Seqtrak work began.

## What's here

| Path | What |
|---|---|
| `src/open_push/reason/app.py` | The bridge (`python3 src/open_push/reason/app.py`, `--sim` for the simulator) |
| `src/open_push/reason/protocol.py`, `ports.py` | Push protocol and virtual MIDI ports |
| `src/open_push/reason/codecs/` | Three Reason Remote codecs (Devices, Mixer, Transport) + `install_codecs.sh` |
| `docs/Reason/reason-bridge-reference.md` | Complete integration reference |

## Key facts

- **Channel translation**: the Push sends on channel 0, Reason expects channel 15.
- Virtual port names must match the `.luacodec` descriptions exactly.
- `reason/bridge.py` is dead code (flagged in the July 2026 review).

## Next

Mixer and device modes. The Mackie Control idea (`docs/Research/mcu-emulation-spike.md`) would cover
Logic and most other DAWs in one go.
