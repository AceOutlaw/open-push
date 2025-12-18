# Reason Remote Protocol - PusheR Communication

This document describes the communication protocol between Reason DAW and the PusheR bridge application, as implemented in the Lua codec files.

## Table of Contents

1. [Overview](#overview)
2. [Virtual MIDI Ports](#virtual-midi-ports)
3. [Lua Codec Structure](#lua-codec-structure)
4. [Custom SysEx Protocol](#custom-sysex-protocol)
5. [Control Surface Definitions](#control-surface-definitions)
6. [MIDI Message Mapping](#midi-message-mapping)
7. [Translation Requirements](#translation-requirements)

---

## Overview

PusheR uses three Lua codecs to communicate with Reason:

| Codec | File | Purpose |
|-------|------|---------|
| PushTransport | PushTransport.lua | Transport, navigation, global controls |
| PushDevices | PushDevices.lua | Device parameters, encoders |
| PushMixer | PushMixer.lua | Mixer controls, volume, pan |

### Important Distinction

The Reason Remote protocol is **NOT the same as the Push hardware protocol**.

```
┌─────────────┐    Custom SysEx     ┌─────────────┐    Push SysEx    ┌─────────────┐
│   REASON    │ ◄─────────────────► │   BRIDGE    │ ◄──────────────► │    PUSH     │
│   (Codecs)  │   F0 11 22 ...      │    APP      │   F0 47 7F 15    │  HARDWARE   │
└─────────────┘                     └─────────────┘                   └─────────────┘
```

The bridge application must translate between:
- **Reason's custom protocol** (`F0 11 22 ...`)
- **Push hardware protocol** (`F0 47 7F 15 ...`)

---

## Virtual MIDI Ports

### Required Virtual Ports (IAC Driver on macOS)

| Port Name | Direction (from Reason's perspective) |
|-----------|---------------------------------------|
| Push_IN | Reason receives FROM this port |
| Push_OUT | Reason sends TO this port |

### Port Configuration in Settings.json

```json
{
  "PushIN": "Ableton Push User Port",
  "PushOUT": "Ableton Push User Port",
  "ReasonIN": " Push_IN",
  "ReasonOUT": " Push_OUT"
}
```

Note: The space before "Push_IN" and "Push_OUT" appears intentional in the original configuration.

---

## Lua Codec Structure

Each codec follows the Reason Remote SDK structure:

### 1. Surface Definition (.luacodec file)

```lua
function remote_supported_control_surfaces()
  return {
    {
      manufacturer = "RetouchControl",
      model = "PushTransport",
      source = "PushTransport.lua",
      in_ports = { {description = "In Port"} },
      out_ports = { {description = "Out Port", optional = true} },
      has_keyboard = true
    }
  }
end
```

### 2. Item Definitions (remote_init)

```lua
function remote_init(manufacturer, model)
  local items = {
    {name="pot1", input="value", output="value", min=0, max=127},
    {name="button1", input="button", output="value"},
    {name="LCD1", output="text"},
    {name="Keyboard", input="keyboard"},
  }
  remote.define_items(items)
end
```

### 3. Input Patterns (MIDI from bridge to Reason)

```lua
local inputs = {
  {pattern="bf 03 <???y>x", name="pot3"},           -- CC message
  {pattern="bf 2a ?<???x>", name="button1"},        -- Button press
  {pattern="<100x>f yy zz", name="Keyboard"},       -- Note message
}
remote.define_auto_inputs(inputs)
```

### 4. Output Patterns (MIDI from Reason to bridge)

```lua
local outputs = {
  {name="pot1", pattern="bf 01 xx"},                -- CC feedback
  {name="button1", pattern="bf 2a ?<???x>"},        -- Button LED
}
remote.define_auto_outputs(outputs)
```

---

## Custom SysEx Protocol

The PusheR bridge uses a custom SysEx format to communicate LCD text to the bridge application.

### Message Format

```
F0 11 22 [mode] [field] [16 ASCII bytes] F7
```

| Byte(s) | Value | Description |
|---------|-------|-------------|
| F0 | - | SysEx start |
| 11 22 | - | PusheR manufacturer ID (custom) |
| mode | 01, 06, 10, 11 | Codec identifier |
| field | 01-1F | LCD field number |
| data | 16 bytes | ASCII text (padded with spaces) |
| F7 | - | SysEx end |

### Mode Identifiers

| Mode | Hex | Codec |
|------|-----|-------|
| PushMixer | 0x01 | Mixer LCD fields |
| PushTransport | 0x06 | Transport LCD fields |
| PushDevices | 0x10 | Device LCD fields (primary) |
| PushDevices | 0x11 | Device LCD fields (secondary) |

### Field Numbers by Mode

#### PushTransport (Mode 0x06)
| Field | Hex | LCD Position |
|-------|-----|--------------|
| 1-4 | 01-04 | Row 1: 4 fields × 16 chars |
| 5-8 | 05-08 | Row 2: 4 fields × 16 chars |
| 9-12 | 09-0C | Rows 3-4: Additional fields |

#### PushMixer (Mode 0x01)
| Field | Hex | LCD Position |
|-------|-----|--------------|
| 1-8 | 01-08 | Track names (8 channels) |
| 9-16 | 09-10 | Track values |
| 17-32 | 11-1F | Additional mixer info |

#### PushDevices (Mode 0x10, 0x11)
| Field | Hex | LCD Position |
|-------|-----|--------------|
| 1-8 | 01-08 | Parameter names |
| 9-16 | 09-10 | Parameter values |
| 17-32 | 11-1F | Extended parameters |

### Example Messages

**Transport - Display "Master" on field 1:**
```
F0 11 22 06 01 4D 61 73 74 65 72 20 20 20 20 20 20 20 20 20 20 F7
                M  a  s  t  e  r  (spaces to pad to 16 chars)
```

**Mixer - Display "-12.5 dB" on field 9:**
```
F0 11 22 01 09 2D 31 32 2E 35 20 64 42 20 20 20 20 20 20 20 20 F7
                -  1  2  .  5     d  B  (spaces to pad)
```

---

## Control Surface Definitions

### PushTransport Items

| Category | Count | Items |
|----------|-------|-------|
| Pots (encoders) | 41 | pot1-pot41 |
| Buttons | 40 | button1-button40 |
| LCD fields | 11 | LCD1-LCD11 |
| Keyboard | 1 | Keyboard |
| Pitch bend | 1 | pitchbend |

### PushMixer Items

| Category | Count | Items |
|----------|-------|-------|
| Pots | 16+ | Volume, pan per channel |
| Buttons | 32+ | Mute, solo, select per channel |
| LCD fields | 32 | Track names, values |

### PushDevices Items

| Category | Count | Items |
|----------|-------|-------|
| Pots | 16+ | Device parameters |
| Buttons | 98 | Pad grid, function buttons |
| LCD fields | 27+ | Parameter names, values |

---

## MIDI Message Mapping

### Input Messages (Bridge → Reason)

The codecs expect standard MIDI messages on specific channels:

#### Control Change (0xBF = Channel 16)
```
BF [cc#] [value]
```

| CC Range | Purpose |
|----------|---------|
| 0x02-0x29 | Encoder values (pot2-pot41) |
| 0x2A-0x51 | Button states (button1-button40) |

#### Notes (Channel 16)
```
9F [note] [velocity]    // Note on
8F [note] [velocity]    // Note off
```

Used for keyboard input (pads playing notes).

#### Pitch Bend (0xEF = Channel 16)
```
EF [LSB] [MSB]
```

Used for touch strip position.

### Output Messages (Reason → Bridge)

#### Control Change
```
BF [cc#] [value]
```

Sends encoder feedback, button LED states.

#### SysEx (LCD Text)
```
F0 11 22 [mode] [field] [16 chars] F7
```

Sends display text to bridge for rendering on Push LCD.

---

## Translation Requirements

The bridge application must perform these translations:

### 1. MIDI Channel Translation

| Source | Channel | Destination | Channel |
|--------|---------|-------------|---------|
| Push User Port | Any | Virtual Port (Reason) | 16 (0xF) |
| Virtual Port (Reason) | 16 | Push User Port | 1 |

### 2. CC Number Translation

Some CC numbers need remapping between Push hardware and Reason codecs:

| Push CC | Reason CC | Control |
|---------|-----------|---------|
| 71-78 | Custom | Track encoders |
| 102-109 | Custom | Upper row buttons |
| 20-27 | Custom | Lower row buttons |

### 3. SysEx Translation

**Reason → Push:**
```
F0 11 22 06 01 [16 chars] F7  →  F0 47 7F 15 18 00 45 00 [68 chars] F7
     (custom)                          (Push 1 hardware)
```

The bridge must:
1. Receive 16-char chunks from Reason
2. Combine multiple fields into 68-char lines
3. Send as Push 1 LCD SysEx format

### 4. Display Layout Mapping

Push 1 LCD: 4 lines × 68 characters
Reason sends: Multiple 16-character fields

```
Push LCD Line 1: [Field1][Field2][Field3][Field4][4 extra chars]
Push LCD Line 2: [Field5][Field6][Field7][Field8][4 extra chars]
```

The bridge assembles fields into complete LCD lines.

---

## Remote Map Files

In addition to Lua codecs, PusheR uses `.remotemap` files that define default mappings:

- `PushTransport.remotemap` - Transport control assignments
- `PushDevices.remotemap` - Device parameter mappings
- `PushMixer.remotemap` - Mixer control mappings

These are XML-based files that Reason uses to auto-map controls to devices.

---

## Implementation Notes

### Timing Considerations

The Lua codecs track timing for input handling:
```lua
function remote_on_auto_input(item_index)
  if item_index > 0 then
    last_input_time = remote.get_time_ms()
    last_item = item_index
  end
end
```

### State Management

LCD text state is maintained per field:
```lua
lcd1_text = string.format("%-16.16s", " ")      -- Current text
lcd1_changed = false                             -- Dirty flag
```

### Text Formatting

All LCD text is formatted to exactly 16 characters:
```lua
text = string.format("%-16.16s", value)
```

---

## Sources

- PusheR Lua Codecs (reference/remote-files/Lua Codecs/PusheR/)
- Reason Remote SDK Documentation
- Reverse engineering of original PusheR application
