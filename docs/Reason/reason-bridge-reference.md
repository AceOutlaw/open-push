# Reason Bridge Reference

Complete reference for the OpenPush → Reason integration.

**Last Updated**: 2025-12-26

---

## Overview

The Reason bridge enables Ableton Push hardware to control Propellerhead Reason via custom Lua codecs.

### Architecture
```
Push Hardware <--MIDI--> Python Bridge <--Virtual Ports--> Lua Codec <--Remote--> Reason
  F0 47 7F 15...                            OpenPush                      Functions
```

**Key Insight**: Python handles Push hardware protocol; Lua codecs are simplified because:
- No complex MIDI parsing (Python normalizes to simple CC)
- No display output (Python controls Push LCD directly)
- Auto inputs/outputs handle most routing

---

## Running the Reason Bridge

### Basic Commands

```bash
# Run the Reason bridge app
python3 src/open_push/reason/app.py

# Run with Push Simulator (for testing without hardware)
python3 src/open_push/reason/app.py --sim

# Install Lua codecs to Reason (run from project root)
./src/open_push/reason/codecs/install_codecs.sh
```

### Dependencies

```bash
pip3 install mido python-rtmidi
```

---

## Reason Control Surface Setup

In Reason → Preferences → Control Surfaces:
- **Manufacturer**: OpenPush
- **Model**: Transport / Devices / Mixer
- **MIDI Input**: `OpenPush Transport In` (etc.)
- **MIDI Output**: `OpenPush Transport Out` (etc.)

---

## Codec Files Location

After install, files are at:
- `/Applications/Reason 12.app/Contents/Resources/Remote/DefaultCodecs/Lua Codecs/OpenPush/`
- `/Applications/Reason 12.app/Contents/Resources/Remote/DefaultMaps/OpenPush/`

**CRITICAL**: Files must have Unix LF line endings (not Windows CRLF). Fix with:
```bash
sed -i '' 's/\r$//' *.lua *.luacodec *.remotemap
```

---

## Virtual MIDI Port Pattern

**Port naming MUST match luacodec descriptions exactly** for Reason to auto-assign ports.

### Python Creates Virtual Ports
```python
# We send → Reason receives
transport_in = mido.open_output("OpenPush Transport In", virtual=True)

# Reason sends → We receive
transport_out = mido.open_input("OpenPush Transport Out", virtual=True)
```

### Luacodec Must Match
```lua
-- Matches our output port name
in_ports={{description="OpenPush Transport In"}},

-- Matches our input port name
out_ports={{description="OpenPush Transport Out"}},
```

**If ports are assigned to "Easy MIDI Input"**: The luacodec descriptions don't match the port names. Fix by ensuring exact match between Python port names and luacodec `description` fields.

---

## Push ↔ Reason Channel Translation

**CRITICAL**: Push hardware uses channel 0, but Reason Lua codecs expect channel 15.

| Direction | Channel | Why |
|-----------|---------|-----|
| Push hardware | 0 | Native Push protocol |
| To Reason codec | **15** | Lua patterns use `bf xx xx` (0xBF = CC on ch15) |
| From Reason | **15** | Lua outputs use `bf xx xx` |
| To Push hardware | **0** | Must translate back |

### Implementation Pattern

**Push → Reason (ch0 → ch15)**
```python
def _send_to_transport(self, msg):
    if msg.type == 'control_change':
        reason_msg = mido.Message('control_change',
            channel=15,  # Reason expects ch15
            control=msg.control,
            value=msg.value)
        self.remote_out_ports["OpenPush Transport"].send(reason_msg)
```

**Reason → Push (ch15 → ch0)**
```python
def _handle_reason_message(self, port_name, msg):
    if msg.type == 'control_change':
        push_msg = mido.Message('control_change',
            channel=0,  # Push expects ch0
            control=msg.control,
            value=msg.value)
        self.push_out_port.send(push_msg)
```

---

## Transport Button CC Mapping

These CC numbers must match between Push hardware and Lua codec:

| Button | Push CC | Lua Pattern | Notes |
|--------|---------|-------------|-------|
| Play | 85 | `bf 55 xx` | 0x55 = 85 |
| Stop | 29 | `bf 1d xx` | 0x1D = 29 |
| Record | 86 | `bf 56 xx` | 0x56 = 86 |
| Loop | 55 | `bf 37 xx` | 0x37 = 55 |
| Metronome | 9 | `bf 09 xx` | 0x09 = 9 |

**Reference**: See `docs/open-push-master-reference.md` for complete button CC mapping.

---

## Reason Remote SDK Key Functions

```lua
-- In remote_init(): Define items and auto I/O
remote.define_items(items)
remote.define_auto_inputs(inputs)
remote.define_auto_outputs(outputs)

-- State queries (for display/feedback)
remote.get_item_text_value(index)     -- "-12 dB", "Filter"
remote.get_item_name_and_value(index) -- "Volume: -12 dB"
remote.is_item_enabled(index)         -- true if mapped
remote.get_time_ms()                  -- for timed feedback
```

**Full SDK Reference**: See `docs/Foundation/06-reason-remote-sdk-reference.md`

---

## PusheR Reference

PusheR is a commercial Reason remote codec that provided inspiration and reference patterns.

### Device Detection via LCD

PusheR uses LCD field values to identify devices:

| Device | LCD1 Value |
|--------|-----------|
| Kong | "1" |
| Redrum | "2" |
| Dr.REX | "3" |

### Remotemap Scopes (priority order)

1. Device scopes (Kong, Subtractor, Mixer) - highest
2. "Reason Document" scope (transport, undo, track selection)
3. "Master Keyboard" scope (keyboard, pitch bend) - lowest

### PusheR Transport Mappings

- button5=Tap Tempo, button6=Click
- button16/17/18=Stop/Play/Record
- pot2-5=Bar/Beat/Sixteenth/Tick Position
- pot6=Tempo BPM
- button23-26=Move Loop Left/Right

**Full Analysis**: See `docs/Foundation/04-pusher-reference-analysis.md`

---

## PusheR SysEx Protocol

PusheR uses a custom SysEx format for LCD display updates.

### SysEx Format
`F0 11 22 [mode] [field] [16-char text] F7`

- Header: `11 22` (NOT `00 11 22`)
- Mode byte: `06` = Transport mode
- Field codes specify which LCD field to update

### Field Codes (mode=0x06)

| Field | Code | Purpose | Example |
|-------|------|---------|---------|
| 0x03 | Track/Patch | Left label | "Track Complex-1" |
| 0x04 | Position | Playhead number | "1", "2", "3"... |
| 0x07 | Device | Device name | "Colourform Seque" |
| 0x09 | Patch | Patch name | "Init Patch" |

### Display Button Routing (from MIDI logs)

| Push CC | PusheR Function | Reason CC |
|---------|-----------------|-----------|
| CC 20 | Track ← | Pan (fine) |
| CC 21 | Track → | Expression (fine) |
| CC 102 | Rewind/Playhead ← | CC 56 |
| CC 103 | Forward/Playhead → | CC 55 |

### LCD Layout in PusheR Default State

```
Line 1: << Track >>    Transport      << Playhead >>   1:1:3
Line 2: << Patch >>    Init Patch     << Left Loop >>  1
Line 3: Device         << Right Loop  Tempo            120 BPM
Line 4: [page]         g              Loop             OFF
```

### Track Selection Messages

When pressing CC 21 (Track →):
1. PusheR sends Expression (fine) = 127 to Reason
2. Reason responds with track info via SysEx
3. SysEx contains "Track [device_name]" and "Patch [patch_name]"

Example track names decoded from hex:
- `54 72 61 63 6B 20 43 6F 6D 70 6C 65 78 2D 31` = "Track Complex-1"
- `54 72 61 63 6B 20 43 6F 6C 6F 75 72 66 6F 72 6D` = "Track Colourform"
- `54 72 61 63 6B 20 54 72 61 6E 73 70 6F 72 74` = "Track Transport"

---

## Working Implementation Patterns

**Reference Implementation**: `src/open_push/reason/app.py` has working examples of:
- Push initialization (User Mode SysEx)
- LCD segment-aware display
- Pad color mapping (root=blue, scale=white, other=dim)
- Button LED control
- Octave shifting
- Scale selection UI (chromatic root layout, scrollable scale list)
- In-Key vs Chromatic modes
- Velocity curve processing
- Transport controls (Play/Stop/Record)
- Reason Remote integration

### Velocity Curve (Important for Playability)

Raw Push velocity is inconsistent (light touches = vel 2-10, too quiet). Apply curve:

```python
def apply_velocity_curve(self, velocity):
    if velocity <= 0:
        return 0
    normalized = (velocity - 1) / 126.0
    output_range = self.velocity_max - self.velocity_min  # 127 - 40 = 87
    return int(self.velocity_min + (normalized * output_range))

# Settings: velocity_min=40, velocity_max=127
# Result: vel 10 -> 47, vel 64 -> 84, vel 127 -> 127
```

### Complete Push Initialization Sequence

```python
# 1. Send User Mode SysEx
self._send_sysex([0x62, 0x00, 0x01, 0x01])
time.sleep(0.1)

# 2. Update display FIRST (segments!)
self._set_lcd_segments(1, "Title", "Info", "Mode", "Version")

# 3. Light pad grid with colors
for row in range(8):
    for col in range(8):
        note = 36 + (row * 8) + col
        color = self.get_pad_color(row, col)
        self.push_port.send(mido.Message('note_on', note=note, velocity=color))

# 4. Set button LEDs
self.push_port.send(mido.Message('control_change', control=85, value=4))  # Play
```

### Button Handling Pattern

```python
elif msg.type == 'control_change':
    if msg.value > 0:  # Button pressed (not released)
        if msg.control == BUTTONS['octave_up']:
            self.handle_octave_up()
        elif msg.control == BUTTONS['play']:
            self.handle_play()
```

---

## Key Files

| File | Purpose |
|------|---------|
| `src/open_push/reason/app.py` | **Main bridge application** |
| `src/open_push/reason/codecs/` | Lua codec files for Reason Remote |
| `src/open_push/reason/codecs/install_codecs.sh` | Codec installation script |
| `src/open_push/music/layout.py` | IsomorphicLayout class for pad-to-note mapping |
| `src/open_push/music/scales.py` | Scale definitions and utilities |

---

## Related Documentation

### Foundation Documentation (in docs/Foundation/)
- **03-reason-remote-protocol.md** - SysEx protocol, virtual ports
- **06-reason-remote-sdk-reference.md** - Complete SDK API reference
- **07-reason-remote-auto-detection.md** - Auto-detection mechanism
- **09-reason-integration-guide.md** - Integration overview
- **10-reason-transport-and-display-implementation.md** - Transport and LCD patterns
- **14-reason-remote-knowledge-base.md** - Additional knowledge
- **25-reason-screen-mount-notes.md** - Screen mounting hardware notes

### Push Hardware Reference
- **docs/open-push-master-reference.md** - Complete Push 1 hardware reference
  - Button CC mappings
  - Encoder reference
  - LCD display patterns
  - SysEx protocol

---

## Current Status

### Working Features
- Full isomorphic pad layout with scale coloring
- Scale mode with chromatic root selection (C-B ascending)
- 40+ scales with encoder scrolling
- Octave up/down shifting
- In-Key vs Chromatic mode toggle
- Reason codecs installed and detected (OpenPush manufacturer appears)
- Virtual MIDI ports for Reason bridge
- Transport controls (Play/Stop/Record to Reason)
- Velocity curve for playability

### In Progress
- Device name display on LCD (from Reason)
- Mixer and device control modes
- Full Reason Remote bi-directional integration

---

## Future Development

Planned features from PusheR reference:
- Layout direction options (4ths up, 4ths right, 3rds up, 3rds right)
- Loop point control
- Track/device selection via LCD buttons

---

## Notes

- Always verify channel translation (Push ch0 ↔ Reason ch15)
- Test with Reason open - some features require active Reason session
- Codec changes require Reason restart to take effect
- Virtual port names must match exactly for auto-detection
