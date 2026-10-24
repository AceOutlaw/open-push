# 6. Generic MIDI / BLE Controller

**What**: The Push as a plain MIDI controller for anything: notes, CCs and transport with no
device-specific protocol. Built for a Pi Zero 2W, sending to an iPad over Bluetooth MIDI or USB gadget
MIDI, or to external USB MIDI devices.

**State**: 💤 Worked as an experiment (Jan 2026); dormant since. Its role in the plan is the "generic
MIDI" mode of the Pi's mode switching (project 5).

## What's here

| Path | What |
|---|---|
| `src/open_push/midi/app.py` | The MIDI-only bridge: pads always play; encoder banks (volume, pan, filter…); scale selection as an overlay; settings via Shift+User |
| `src/open_push/midi/modes/` | Drum, keyboard, scale select and encoder modes |
| `src/open_push/midi/outputs/` | Outputs: BLE GATT, Bluetooth, USB gadget |
| `src/open_push/midi/deploy_pimini.sh` | Deploy to the Pi Zero 2W (`--install`, `--status`, `--logs`) |
| `experiments/bluetooth/` | The BLE MIDI experiments it grew from |
| `docs/BLE-MIDI-INTEGRATION-PLAN.md`, `docs/BLE-MIDI-PI-ZERO-2W.md` | Plan, tested controllers, troubleshooting |

## Notes

Use Raspberry Pi OS Bookworm on the Zero 2W; Wi-Fi is broken there on Trixie.
