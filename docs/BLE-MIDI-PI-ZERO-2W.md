# BLE MIDI Bridge - Raspberry Pi Zero 2W

This document covers the pitfalls, troubleshooting steps, and solutions discovered while setting up BLE MIDI on a Raspberry Pi Zero 2W (pimini).

## Overview

The BLE MIDI bridge allows USB MIDI controllers (MPK Mini, Launchkey Mini, Push) connected to a Pi Zero 2W to send MIDI wirelessly to iOS/macOS devices via Bluetooth Low Energy.

**Architecture:**
```
USB MIDI Controller → Pi Zero 2W → BLE MIDI → iPad/Mac
```

**Key Files:**
- `experiments/bluetooth/minimal_ble_midi.py` - Working BLE MIDI bridge script
- `/etc/systemd/system/ble-midi.service` - Systemd service on Pi

---

## Hardware Pitfalls

### Launchkey Mini Mk4 "Easy Start" Mode

**Problem:** Device receives power (LEDs on) but doesn't appear in `lsusb` or as a MIDI device.

**Cause:** Novation Launchkey Mk4 boots into "Easy Start" mass storage mode by default to show getting-started documentation.

**Solution:** Hold the **Play button** while plugging in the USB cable to force MIDI mode.

**Verification:**
```bash
lsusb | grep -i novation
# Should show: Focusrite-Novation Launchkey Mini MK4 25

aconnect -l
# Should show: client XX: 'Launchkey Mini MK4 25'
```

### Pi Zero 2W USB Ports

- **Left port (USB):** Data - use this for MIDI controllers
- **Right port (PWR):** Power only - cannot transfer data

### OTG Mode Required

Ensure OTG mode is enabled in `/boot/config.txt`:
```
dtoverlay=dwc2
```

---

## BlueZ Configuration Pitfalls

### BlueZ 5.66 Plugin Disable

**Problem:** `DisablePlugins=midi` in `/etc/bluetooth/main.conf` is silently ignored in BlueZ 5.66.

**Solution:** Use command-line flag instead. Edit `/lib/systemd/system/bluetooth.service`:
```ini
ExecStart=/usr/libexec/bluetooth/bluetoothd --experimental --noplugin=midi
```

Then reload:
```bash
sudo systemctl daemon-reload
sudo systemctl restart bluetooth
```

### Minimal `/etc/bluetooth/main.conf`

```ini
[General]
Name = PiBLE
DiscoverableTimeout = 0
JustWorksRepairing = always
FastConnectable = true

[LE]
MinConnectionInterval = 7
MaxConnectionInterval = 9

[Policy]
AutoEnable = true
```

---

## BLE Pairing Pitfalls

### "LE Long Term Key Request Negative Reply" Disconnects

**Problem:** macOS/iOS connects briefly then disconnects. HCI trace shows:
```
LE Long Term Key Request Negative Reply
```

**Cause:** The client expects encryption but the Pi has no stored keys (stale bond cache on client side).

**Solution 1 - Encrypt Flags:** Add `encrypt-*` flags to GATT characteristic to force pairing initiation:
```python
'Flags': dbus.Array([
    'read', 'encrypt-read',
    'write-without-response', 'encrypt-write',
    'notify', 'encrypt-notify'
], signature='s'),
```

**Solution 2 - Pairing Agent:** Register a NoInputNoOutput agent for "Just Works" pairing:
```python
class PairingAgent(dbus.service.Object):
    @dbus.service.method(AGENT_IFACE, in_signature='o', out_signature='')
    def RequestAuthorization(self, device):
        return  # Auto-authorize

    @dbus.service.method(AGENT_IFACE, in_signature='ou', out_signature='')
    def RequestConfirmation(self, device, passkey):
        return  # Auto-confirm
```

### Stale Bond Cache on iOS/macOS

**Problem:** After changing Pi configuration, client won't reconnect - keeps trying old encryption keys.

**Solutions:**
1. **On iOS/Mac:** Settings > Bluetooth > Forget "PiBLE"
2. **On Pi:** Remove paired devices:
   ```bash
   sudo rm -rf /var/lib/bluetooth/*/
   sudo systemctl restart bluetooth
   ```
3. **MAC Address Change** (forces fresh pairing):
   ```bash
   sudo hcitool -i hci0 cmd 0x3f 0x001 0x91 0x68 0x33 0xEB 0x27 0xB8
   ```
   Note: This only persists until Bluetooth restarts on Pi Zero 2W.

---

## iOS Connection Pitfalls

### BLE MIDI Not in Regular Bluetooth Settings

**Problem:** "PiBLE" doesn't appear in iOS Settings > Bluetooth.

**Cause:** BLE MIDI devices are not shown in regular Bluetooth settings on iOS.

**Solution:** Connect from within a MIDI app:
- **GarageBand:** Settings (⚙️) → Advanced → Bluetooth MIDI Devices
- **AUM:** MIDI settings → Bluetooth
- **midimittr:** Dedicated BLE MIDI connection app (free)

### Connection Requires App to Be Open

BLE MIDI connections are managed by the app, not the system. The MIDI app must be open and actively looking for BLE devices.

---

## Code Pitfalls

### GLib Callback Queue Buildup

**Problem:** MIDI notes repeat dozens of times when only pressed once.

**Cause:** Using `GLib.idle_add()` queues callbacks faster than they execute.

**Solution:** Use `GLib.timeout_add(0, callback)` and return `False`:
```python
def send_midi(self, midi_bytes):
    if self.notifying:
        # ... send notification ...
    return False  # Critical: removes from queue after one execution

# Queue the send
GLib.timeout_add(0, char.send_midi, midi_bytes)
```

### BLE-MIDI Packet Format

BLE-MIDI requires a header before MIDI bytes:
```python
ble_packet = bytes([0x80, 0x80]) + bytes(midi_bytes)
```
- First `0x80`: Timestamp high byte (no timestamp)
- Second `0x80`: Timestamp low byte / status

---

## Systemd Service

`/etc/systemd/system/ble-midi.service`:
```ini
[Unit]
Description=BLE MIDI Bridge
After=bluetooth.service
Requires=bluetooth.service

[Service]
ExecStart=/usr/bin/python3 -u /home/pimini/ble_midi/minimal_ble_midi.py
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable ble-midi
sudo systemctl start ble-midi
```

---

## Diagnostic Commands

```bash
# Check USB devices
lsusb

# Check MIDI ports
aconnect -l
python3 -c "import mido; print(mido.get_input_names())"

# Check Bluetooth adapter
hciconfig hci0
sudo bluetoothctl show

# Check service status
sudo systemctl status ble-midi
sudo journalctl -u ble-midi.service -f

# Filter logs (exclude clock spam)
sudo journalctl -u ble-midi.service | grep -v clock | tail -30

# HCI trace for debugging connection issues
sudo btmon
```

---

## Quick Troubleshooting

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Controller has power but no USB detection | Easy Start mode (Launchkey) | Hold Play while plugging in |
| `lsusb` shows only root hub | Wrong USB port or bad cable | Use left (data) port |
| iPad can't find PiBLE | BLE MIDI not in system Bluetooth | Use MIDI app's Bluetooth settings |
| Connects then immediately disconnects | Stale bond cache | Forget device on both sides |
| MIDI notes repeat many times | Callback queue buildup | Use `timeout_add` + return `False` |
| Service won't start | BlueZ MIDI plugin conflict | Add `--noplugin=midi` to bluetoothd |
