# BLE MIDI Integration Plan

This document captures the work done in the BLE MIDI experiment and provides a roadmap for integrating it into the Open Push application.

---

## Executive Summary

We built a working BLE MIDI bridge on Raspberry Pi Zero 2W (pimini) that forwards USB MIDI controllers wirelessly to iOS/macOS. This document describes what we learned and how to bring that functionality into the main Open Push codebase.

**Experiment Location:** `experiments/bluetooth/minimal_ble_midi.py`
**Target Integration:** `src/open_push/midi/`

---

## What We Built (Experiment)

### Working Features
- BLE MIDI GATT service that iOS/macOS recognizes as a MIDI device
- Automatic USB MIDI controller detection and reconnection
- Support for multiple controllers (Launchpad X, Launchkey Mini, MPK Mini)
- Pairing agent for seamless "Just Works" Bluetooth pairing
- Proper BLE-MIDI packet formatting

### Tested Controllers
| Controller | Status | Notes |
|------------|--------|-------|
| Novation Launchpad X | ✅ Working | Must use MIDI In port, not DAW In |
| Novation Launchkey Mini Mk4 | ✅ Working | Hold Play while connecting to bypass Easy Start |
| Akai MPK Mini | ✅ Working | Works out of the box |

### Known Limitations
- Connection not instant (takes a few seconds, sometimes multiple attempts)
- macOS connection less reliable than iOS
- MAC address spoofing doesn't persist on Pi Zero 2W

---

## Critical Requirements

These are the things that MUST be true for BLE MIDI to work:

### 1. BlueZ Configuration

**Command-line flags required:**
```bash
/usr/libexec/bluetooth/bluetoothd --experimental --noplugin=midi
```

- `--experimental`: Required for GATT advertisement API
- `--noplugin=midi`: Prevents BlueZ's built-in MIDI plugin from conflicting

**Where to set this:** `/lib/systemd/system/bluetooth.service`
```ini
ExecStart=/usr/libexec/bluetooth/bluetoothd --experimental --noplugin=midi
```

### 2. GATT Characteristic Flags

The MIDI characteristic MUST have encrypt flags to force iOS/macOS to initiate pairing:

```python
'Flags': dbus.Array([
    'read', 'encrypt-read',
    'write-without-response', 'encrypt-write',
    'notify', 'encrypt-notify'
], signature='s'),
```

Without these flags, clients connect but immediately disconnect with "LE Long Term Key Request Negative Reply".

### 3. Pairing Agent

A NoInputNoOutput pairing agent must be registered for "Just Works" pairing:

```python
class PairingAgent(dbus.service.Object):
    CAPABILITY = "NoInputNoOutput"

    @dbus.service.method(AGENT_IFACE, in_signature='o', out_signature='')
    def RequestAuthorization(self, device):
        return  # Auto-authorize

    @dbus.service.method(AGENT_IFACE, in_signature='ou', out_signature='')
    def RequestConfirmation(self, device, passkey):
        return  # Auto-confirm
```

Register with: `agent_manager.RegisterAgent(agent_path, "NoInputNoOutput")`

### 4. BLE-MIDI Packet Format

MIDI bytes must be wrapped with BLE-MIDI headers:

```python
def send_midi(self, midi_bytes):
    # BLE-MIDI format: [timestamp_high, timestamp_low, ...midi_bytes]
    ble_packet = bytes([0x80, 0x80]) + bytes(midi_bytes)
    self.PropertiesChanged('org.bluez.GattCharacteristic1',
                          {'Value': dbus.Array(ble_packet, signature='y')}, [])
```

### 5. BLE-MIDI Service UUIDs

```python
MIDI_SERVICE_UUID = '03b80e5a-ede8-4b33-a751-6ce34ec4c700'
MIDI_CHAR_UUID = '7772e5db-3868-4112-a1a9-f2669d106bf3'
```

These are the official Apple BLE-MIDI UUIDs. Do not change.

### 6. GLib Callback Queue

Use `timeout_add` instead of `idle_add` to prevent callback queue buildup:

```python
# WRONG - causes MIDI note repeating
GLib.idle_add(char.send_midi, midi_bytes)

# CORRECT
GLib.timeout_add(0, char.send_midi, midi_bytes)

# And the callback must return False
def send_midi(self, midi_bytes):
    # ... send notification ...
    return False  # Critical: removes from queue
```

---

## Architecture: Experiment vs Open Push

### Experiment (`minimal_ble_midi.py`)

```
USB MIDI Controller
        │
        ▼
   mido.open_input()
        │
        ▼
  midi_monitor_thread()  ◄── Polls for controllers, auto-reconnects
        │
        ▼
   MIDICharacteristic
        │
        ▼
   BLE Notification
        │
        ▼
   iOS/macOS
```

### Open Push Target Architecture

```
Push Controller (or USB MIDI)
        │
        ▼
   PushMIDI class (existing)
        │
        ├──► Virtual MIDI Port (existing)
        │
        └──► BLEMIDIOutput (NEW)
                │
                ▼
           BLE Notification
                │
                ▼
           iOS/macOS
```

---

## Integration Steps

### Step 1: Create BLE Output Module

Create `src/open_push/midi/outputs/ble_midi.py` with:

```python
# Key components to port from minimal_ble_midi.py:
# - MIDIService class
# - MIDICharacteristic class
# - PairingAgent class
# - Advert class
# - BLE-MIDI packet formatting
```

### Step 2: Modify BlueZ Service on Pi

Ensure `/lib/systemd/system/bluetooth.service` has:
```ini
ExecStart=/usr/libexec/bluetooth/bluetoothd --experimental --noplugin=midi
```

### Step 3: Add BLE Output Option to App

In `src/open_push/midi/app.py` or equivalent:

```python
# Add command-line flag
parser.add_argument('--ble', action='store_true', help='Enable BLE MIDI output')

# Initialize BLE output if enabled
if args.ble:
    from outputs.ble_midi import BLEMIDIOutput
    ble_output = BLEMIDIOutput(name="OpenPush")
    ble_output.start()
```

### Step 4: Wire MIDI Events to BLE

When MIDI events are received from Push:

```python
def on_midi_message(msg):
    # Existing: send to virtual port
    virtual_port.send(msg)

    # New: send to BLE if enabled
    if ble_output and ble_output.has_clients():
        ble_output.send(msg.bytes())
```

### Step 5: Update Systemd Service

Update `open-push-seqtrak.service` or create new service for generic MIDI mode.

---

## Files to Reference

| File | Purpose |
|------|---------|
| `experiments/bluetooth/minimal_ble_midi.py` | Working reference implementation |
| `docs/BLE-MIDI-PI-ZERO-2W.md` | Troubleshooting guide |
| `src/open_push/midi/outputs/ble_gatt.py` | Earlier integration attempt (incomplete) |
| `src/open_push/midi/outputs/bluetooth.py` | Earlier integration attempt (incomplete) |

---

## Testing Checklist

Before considering BLE MIDI integration complete:

- [ ] Service starts without errors on Pi Zero 2W
- [ ] Device appears as "OpenPush" (or configured name) in iOS Bluetooth MIDI
- [ ] Pairing works on first connection attempt
- [ ] Reconnection works after disconnect
- [ ] Multiple controllers can be hot-swapped
- [ ] No MIDI note repeating/glitching
- [ ] Latency is acceptable for playing
- [ ] Works with GarageBand on iPad
- [ ] Works with AUM on iPad
- [ ] Service auto-starts on boot

---

## Open Questions

1. **Bidirectional MIDI?** - Current implementation is Push → iPad only. Do we need iPad → Push?

2. **Multiple BLE Clients?** - Current implementation supports one client. Need to support multiple?

3. **Connection Reliability** - Connection takes multiple attempts sometimes. Investigate or accept?

4. **macOS Support** - macOS connection less reliable than iOS. Priority?

5. **Mode Switching** - How does BLE MIDI mode interact with Seqtrak mode? Runtime switchable?

---

## Dependencies

```bash
# Python packages
pip3 install mido python-rtmidi dbus-python PyGObject

# System packages (Raspberry Pi OS)
sudo apt install python3-dbus python3-gi bluez
```

---

## Quick Reference: Key Code Snippets

### Initialize D-Bus and GATT

```python
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()

# Get adapter
adapter = bus.get_object('org.bluez', '/org/bluez/hci0')
adapter_props = dbus.Interface(adapter, 'org.freedesktop.DBus.Properties')
adapter_props.Set('org.bluez.Adapter1', 'Powered', dbus.Boolean(True))

# Register GATT application
gatt_manager = dbus.Interface(
    bus.get_object('org.bluez', '/org/bluez/hci0'),
    'org.bluez.GattManager1')
gatt_manager.RegisterApplication(app_path, {})

# Register advertisement
ad_manager = dbus.Interface(
    bus.get_object('org.bluez', '/org/bluez/hci0'),
    'org.bluez.LEAdvertisingManager1')
ad_manager.RegisterAdvertisement(ad_path, {})
```

### Send MIDI via BLE

```python
def send_midi(self, midi_bytes):
    if not self.notifying:
        return False

    # BLE-MIDI packet format
    ble_packet = bytes([0x80, 0x80]) + bytes(midi_bytes)

    self.PropertiesChanged(
        'org.bluez.GattCharacteristic1',
        {'Value': dbus.Array(ble_packet, signature='y')},
        [])

    return False  # Remove from GLib callback queue
```

---

## Document History

| Date | Change |
|------|--------|
| 2025-01-03 | Initial version - captured experiment results and integration plan |
