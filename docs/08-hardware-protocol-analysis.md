# Hardware Protocol Analysis

## Overview

This document provides a complete analysis of PusheR's Reason Remote implementation, extracted from studying the obfuscated Lua codec files.

## Architecture: Single Shared Port

**Critical Discovery:** All three PusheR codecs (Transport, Devices, Mixer) share the **SAME physical MIDI port pair**.

```
Push Hardware ←→ PusheR App ←→ IAC Driver Ports ←→ All 3 Lua Codecs
                               " Push_IN"           (read same port)
                               " Push_OUT"          (write same port)
```

Message routing is done via:
1. **MIDI Channel** - Different surfaces use different channels
2. **SysEx Mode Byte** - Different LCD message prefixes

## MIDI Channel Assignments

| Surface | MIDI Channel | Status Byte | Example Pattern |
|---------|--------------|-------------|-----------------|
| Transport | 15 (0xF) | 0xBF | `bf 50 xx` |
| Devices | 14 (0xE) | 0xBE | `be 01 xx` |
| Mixer | 1 | 0xB1 | `b1 01 xx` |
| Keyboard | 7 | 0x97/0x87 | `<100x>7 yy zz` |

### Channel Byte Calculation
- `B0` = CC on channel 0
- `B1` = CC on channel 1 (Mixer)
- `BE` = CC on channel 14 (Devices)
- `BF` = CC on channel 15 (Transport)

## SysEx Protocol

### Header Structure
```
F0 11 22 [mode] [field] [data...] F7
```

### Mode Bytes (Surface Identification)
| Surface | Mode Byte | Notes |
|---------|-----------|-------|
| Mixer | 0x01 | LCD fields 01-1F |
| Transport | 0x06 | LCD fields 01-0C |
| Devices | 0x10 | LCD fields 01-1F (first set) |
| Devices | 0x11 | LCD fields 01-0E (second set) |

### LCD Data Format
- Each LCD field is exactly **16 characters**
- Formatted with `string.format("%-16.16s", text)` (left-justified, truncated to 16)
- ASCII bytes directly in SysEx data

### Example SysEx Messages
```
Mixer LCD field 1:    F0 11 22 01 01 [16 ASCII bytes] F7
Transport LCD field 3: F0 11 22 06 03 [16 ASCII bytes] F7
Devices LCD field 10: F0 11 22 10 0A [16 ASCII bytes] F7
```

## Control Surface Items

### Transport (PushTransport.lua)
- **Pots**: pot2-pot41 (various input types: delta, value)
- **Buttons**: button1-button40 (CC 0x2A-0x51)
- **LCD**: LCD1-LCD11 (12 text output fields)
- **Keyboard**: Standard keyboard input
- **Pitchbend**: Value input/output, range 0-16383

### Devices (PushDevices.lua)
- **Pots**: pot1-pot9 (encoders, CC 0x01-0x09)
- **Extra Pots**: pot10, pot99-pot114 (more encoder mappings)
- **Buttons**: button1-button98 (CC 0x0A-0x6B)
- **LCD**: LCD1-LCD27 (27 text output fields)
- **Keyboard**: Note input on channel 7
- **Pitchbend/Modwheel**: CC 0x7D, 0x7E

### Mixer (PushMixer.lua)
- **Pots**: pot1-pot17 (CC 0x01-0x09, 0x2B-0x32)
- **Buttons**: button1-button38 (CC 0x0A-0x37)
- **LCD**: LCD1-LCD27 (27 text output fields)
- **Keyboard**: Note input on channel 7

## Reason API Functions Used

### remote_init()
Defines all items, auto_inputs, and auto_outputs:
```lua
function remote_init(manufacturer, model)
    local items = { ... }
    remote.define_items(items)

    local inputs = { {pattern="bf 50 xx", name="button1"}, ... }
    remote.define_auto_inputs(inputs)

    local outputs = { {name="button1", pattern="bf 50 ?<???x>"}, ... }
    remote.define_auto_outputs(outputs)
end
```

### remote_probe()
Auto-detection function (probes for actual Push hardware):
```lua
function remote_probe(manufacturer, model)
    return {
        request = "f0 7e 7f 06 01 f7",  -- Universal MIDI Identity Request
        response = "f0 7e 7f 06 02 56 66 66 01 03 ?? ?? ?? ?? f7"
    }
end
```

The response pattern `56 66 66` appears to be Push's manufacturer ID.

### remote_on_auto_input()
Called when matched input is received:
```lua
function remote_on_auto_input(item_index)
    if item_index > 0 then
        last_input_time = remote.get_time_ms()
        last_input_item = item_index
    end
end
```

### remote_set_state()
Called when mapped Reason parameters change:
```lua
function remote_set_state(changed_items)
    for i, item_index in ipairs(changed_items) do
        if remote.is_item_enabled(item_index) then
            local value = remote.get_item_text_value(item_index)
            -- Update LCD variable
        end
    end
end
```

### remote_deliver_midi()
Generates MIDI output when state changes:
```lua
function remote_deliver_midi()
    local ret = {}
    if old_lcd1 ~= new_lcd1 then
        local msg = remote.make_midi("f0 11 22 01 01")
        -- Add text data
        table.insert(ret, msg)
        old_lcd1 = new_lcd1
    end
    return ret
end
```

## Pattern Syntax

### Button Pattern: `?<???x>`
- `?` = wildcard nibble (ignores velocity high nibble)
- `<???x>` = extract last bit into x (0=release, 1=press)

### Keyboard Pattern: `<100x>7 yy zz`
- `<100x>` = match note on (100) or note off (1001), extract into x
- `7` = channel 7 (0x97 for note on, 0x87 for note off)
- `yy` = note number
- `zz` = velocity

### Delta Encoder: `<???y>x`
- Extract sign bit into y, value into x
- Final value: `x * (1 - 2*y)` gives positive or negative delta

## Luacodec Configuration

All three codecs use identical port configuration:
```lua
in_ports = { {description = "In Port"} },
out_ports = { {description = "Out Port", optional = true} },
```

**Key Insight**: The "description" is just a UI label, not a port name to match.
Users manually assign ports when adding control surfaces.

## Implications for OpenPush

### Option 1: Single Shared Port (PusheR approach)
- Create one virtual port pair
- Use channel numbers to differentiate surfaces
- Use SysEx mode bytes for LCD
- Simpler port management
- Requires channel translation in Python

### Option 2: Separate Ports (current OpenPush approach)
- Three virtual port pairs
- Each surface gets dedicated ports
- Simpler Lua codecs (no channel checking needed)
- More complex port assignment in Reason

### Recommendation
Start with Option 2 (current approach) but:
1. Accept manual port assignment (no auto-detect for virtual ports)
2. Use generic port descriptions like PusheR
3. Document setup procedure for users
