# 5. Pi Bridge Platform

**What**: The Raspberry Pi that runs the bridge headless on the keyboard stand: OS setup, the auto-start
service, deploys, remote access, USB audio, and the planned runtime mode switching.

**State**: ✅ Running (Dec 2025 → now). Mode switching is partly built and not in use.

## Devices

| Name | Hardware | Role |
|---|---|---|
| pibridge | Raspberry Pi 4 Model B, 4 GB, Debian 13 | Runs the Seqtrak bridge (`open-push-seqtrak` service, ~45 s boot) |
| pimini | Raspberry Pi Zero 2W, Bookworm | Compact rig; ran the BLE MIDI controller (project 6) |

Both are reachable over Tailscale; setup notes are local-only in `raspberry-pi-setup/`.

## What's built

- Auto-start on boot via systemd (`python3 -m open_push.seqtrak.app`).
- Deploys from a committed version, with the commit recorded on the Pi in `.deployed`.
- **iPad USB audio bridge**: the Pi in USB gadget mode passes iPad audio to the Seqtrak (working); the
  other direction needs a recording app on the iPad.
- USB audio with the Seqtrak as the default output.

## Partly built

**Runtime mode switching**: Seqtrak control ↔ generic MIDI ↔ system settings (safe shutdown, network
info, system stats), from the Push via Shift+User. The design is local (`MODE-SWITCHING-DESIGN.md`);
`src/open_push/seqtrak/bridge_app.py` and `modes/` hold an unfinished version that has drifted from the
bridge. Rebuild it on the current bridge rather than reviving it as is.

## Ideas

- A read-only system with a writable data area, so a battery cut can't corrupt it (KM-258).
- A reproducible image built from a git-tracked setup script (working name KaceMusicOS), so every Pi is
  rebuilt from a known version.
- Real-time audio tuning, for the standalone instrument (KM-247).
