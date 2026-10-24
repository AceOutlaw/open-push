# 1. Push 1 Foundation

**What**: Learning the Ableton Push 1 well enough to drive it without Ableton Live: waking it up, its pads,
buttons and encoders, LED colours, the 4-line LCD, and the musical layouts played on the pads.

**State**: ✅ Done (Dec 2025). Every other project builds on it.

## What's here

| Path | What |
|---|---|
| `src/open_push/core/` | Hardware constants, display (LCD) and hardware helpers |
| `src/open_push/music/` | Isomorphic pad layout (`layout.py`) and 40+ scales (`scales.py`) |
| `src/experiments/` | Explorers used to map the hardware: buttons, colours, LCD segments, pad feel, a Push simulator, wake-up |
| `docs/open-push-master-reference.md` | Full Push 1 hardware reference: buttons, encoders, LCD |
| `docs/open-push-quick-reference.md` | One-page cheat sheet |

## Key facts

- 8×8 velocity-sensitive pads (MIDI notes 36–99); 11 encoders; 4-segment, 68-character LCD.
- Buttons below the LCD: CC 20–27 (upper row) and CC 102–109 (lower row) on the Push 1.
- Button LEDs have a maximum brightness level; higher values blink.

## Related

Used by projects 2, 3 and 6, and the planned standalone instrument.
