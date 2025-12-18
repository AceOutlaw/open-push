# Reason Remote SDK Reference

Summary of the official Remote Codec Developer Documentation for OpenPush development.

## File Structure

A codec package consists of:

| File | Extension | Purpose |
|------|-----------|---------|
| Index file | `.luacodec` | Lists supported control surfaces |
| Source file | `.lua` | Codec logic and MIDI handling |
| Picture file | `.png` | 96x96 pixel image for Reason UI |
| Map file | `.remotemap` | Maps controls to Reason functions |

### Installation Locations

**macOS:**
- Codecs: `/Library/Application Support/Propellerhead Software/Remote/Codecs/Lua Codecs/<manufacturer>/`
- Maps: `/Library/Application Support/Propellerhead Software/Remote/Maps/<manufacturer>/`

**Windows:**
- Codecs: `C:\Documents and Settings\All Users\Application Data\Propellerhead Software\Remote\Codecs\Lua Codecs\<manufacturer>\`
- Maps: `C:\Documents and Settings\All Users\Application Data\Propellerhead Software\Remote\Maps\<manufacturer>\`

## Luacodec File

The `.luacodec` file contains one function:

```lua
function remote_supported_control_surfaces()
    return {
        {
            manufacturer = "OpenPush",
            model = "Transport",
            source = "OpenPush Transport.lua",
            picture = "OpenPush.png",
            in_ports = { {description = "In Port"} },
            out_ports = { {description = "Out Port", optional = true} },
            has_keyboard = false,
            setup_info_text = "Optional setup instructions"
        },
    }
end
```

### Surface Entry Fields

| Field | Required | Description |
|-------|----------|-------------|
| `manufacturer` | Yes | Manufacturer name |
| `model` | Yes | Model name |
| `source` | Yes | Lua source file name |
| `picture` | Yes | PNG file name (96x96) |
| `in_ports` | Yes | Array of input port definitions |
| `out_ports` | Yes | Array of output port definitions |
| `has_keyboard` | No | True if has keyboard |
| `setup_info_text` | No | Setup instructions shown in preferences |
| `setup_warning_text` | No | Warning shown when adding surface |
| `setup_user_action_text` | No | Instructions shown in setup dialog |

### Port Entry Fields

| Field | Required | Description |
|-------|----------|-------------|
| `description` | Yes | Port description for UI |
| `optional` | No | True if port is optional |

## Callback Functions

### Required Functions

#### `remote_init(manufacturer, model)`
Called when control surface is instantiated. Must define all control surface items.

```lua
function remote_init(manufacturer, model)
    local items = {
        {name = "Play", input = "button", output = "value"},
        {name = "Fader 1", input = "value", output = "value", min = 0, max = 127},
        {name = "Encoder 1", input = "delta", output = "value", min = 0, max = 10},
        {name = "Keyboard", input = "keyboard"},
        {name = "LCD", output = "text"},
    }
    remote.define_items(items)

    local inputs = {
        {pattern = "bf 50 ?<???x>", name = "Play"},
        {pattern = "bf 40 xx", name = "Fader 1"},
    }
    remote.define_auto_inputs(inputs)

    local outputs = {
        {name = "Play", pattern = "bf 50 0<000x>"},
        {name = "Fader 1", pattern = "bf 40 xx"},
    }
    remote.define_auto_outputs(outputs)
end
```

### Optional Functions

#### `remote_probe(manufacturer, model, prober)`
Called during auto-detection. Returns request/response patterns or uses prober object for complex detection.

```lua
function remote_probe(manufacturer, model)
    return {
        request = "f0 7e 7f 06 01 f7",
        response = "f0 7e 7f 06 02 ?? ?? ?? ?? ?? ?? ?? ?? f7"
    }
end
```

#### `remote_prepare_for_use()`
Called when surface is activated. Returns array of setup MIDI events.

```lua
function remote_prepare_for_use()
    return {
        remote.make_midi("f0 00 11 22 01 f7"),  -- Enable message
    }
end
```

#### `remote_release_from_use()`
Called when surface is deactivated. Returns array of cleanup MIDI events.

```lua
function remote_release_from_use()
    return {
        remote.make_midi("f0 00 11 22 00 f7"),  -- Disable message
    }
end
```

#### `remote_process_midi(event)`
Called for each incoming MIDI event. Return `true` if handled, `false` to try auto inputs.

```lua
function remote_process_midi(event)
    local ret = remote.match_midi("f0 00 11 22 xx yy f7", event)
    if ret ~= nil then
        local msg = {
            time_stamp = event.time_stamp,
            item = g_item_index,
            value = ret.x
        }
        remote.handle_input(msg)
        return true
    end
    return false
end
```

#### `remote_set_state(changed_items)`
Called regularly with indexes of items that changed. Use to update machine state.

```lua
function remote_set_state(changed_items)
    for i, item_index in ipairs(changed_items) do
        if item_index == g_lcd_index then
            g_lcd_text = remote.get_item_text_value(item_index)
            g_lcd_enabled = remote.is_item_enabled(item_index)
        end
    end
end
```

#### `remote_deliver_midi(max_bytes, port)`
Called regularly to send MIDI to surface. Returns array of MIDI events.

```lua
function remote_deliver_midi(max_bytes, port)
    local events = {}
    if g_lcd_changed then
        table.insert(events, make_lcd_message(g_lcd_text))
        g_lcd_changed = false
    end
    return events
end
```

#### `remote_on_auto_input(item_index)`
Called after an auto input item is handled. Useful for feedback timing.

```lua
function remote_on_auto_input(item_index)
    g_last_input_time = remote.get_time_ms()
    g_last_input_item = item_index
end
```

## Item Definition

### Input Types

| Type | Description | Min/Max |
|------|-------------|---------|
| `"keyboard"` | MIDI keyboard (note on/off with velocity) | 0-1 (off/on) |
| `"button"` | Button (1=pressed, 0=released) | Always 0-1 |
| `"value"` | Fader/knob (absolute value) | Any range |
| `"delta"` | Encoder (relative +/- changes) | N/A |
| `"noinput"` | Output only (LED, display) | N/A |

### Output Types

| Type | Description | Min/Max |
|------|-------------|---------|
| `"value"` | Fader/knob/LED feedback | Any range |
| `"text"` | Display text | N/A |
| `"nooutput"` | Input only | N/A |

### Item Entry Fields

```lua
{
    name = "Fader 1",           -- Required: unique name
    input = "value",            -- Input type
    output = "value",           -- Output type
    min = 0,                    -- Minimum value
    max = 127,                  -- Maximum value
    modes = {"Dark", "Lit"}     -- Optional: mode names for LED colors, etc.
}
```

## MIDI Pattern Syntax

Patterns are hexadecimal strings with special characters:

| Character | Meaning |
|-----------|---------|
| `?` | Wildcard (match any nibble) |
| `??` | Wildcard byte |
| `x`, `xx` | Extract value into x variable |
| `y`, `yy` | Extract value into y variable |
| `z`, `zz` | Extract value into z variable |
| `<???x>` | Binary pattern: 3 wildcards + x bit |
| `<100x>` | Binary pattern: match 100, extract x |

### Examples

```lua
-- CC message, any channel, extract value
{pattern = "b? 40 xx", name = "Fader 1"}

-- Note on/off detection (bit extraction)
{pattern = "<100x>? yy zz", name = "Keyboard"}  -- x=1 note on, x=0 note off

-- Button press detection (last bit)
{pattern = "b? 60 ?<???x>", name = "Button 1"}  -- x=1 pressed, x=0 released

-- Encoder with sign bit
{pattern = "b? 50 <???y>x", name = "Encoder 1", value = "x*(1-2*y)"}

-- 14-bit pitch bend
{pattern = "e? xx yy", name = "Pitch Bend", value = "y*128 + x"}
```

### Auto Input Entry Fields

```lua
{
    pattern = "b? 40 xx",    -- Required: MIDI pattern
    name = "Fader 1",        -- Required: control surface item name
    value = "x",             -- Optional: value expression (default: "x")
    note = "y",              -- Optional: keyboard note (default: "y")
    velocity = "z",          -- Optional: keyboard velocity (default: "z")
    port = 1                 -- Optional: specific input port
}
```

### Auto Output Entry Fields

```lua
{
    name = "Fader 1",        -- Required: control surface item name
    pattern = "b0 40 xx",    -- Required: MIDI pattern
    x = "value",             -- Optional: x expression (default: "value")
    y = "mode",              -- Optional: y expression (default: "mode")
    z = "enabled",           -- Optional: z expression (default: "enabled")
    port = 1                 -- Optional: specific output port
}
```

Output expressions can use: `value`, `mode`, `enabled` (1 if mapped, 0 if not)

## Utility Functions

### Item Definition (only in remote_init)

| Function | Description |
|----------|-------------|
| `remote.define_items(items)` | Register control surface items |
| `remote.define_auto_inputs(inputs)` | Register auto input patterns |
| `remote.define_auto_outputs(outputs)` | Register auto output patterns |

### State Queries

| Function | Returns |
|----------|---------|
| `remote.get_item_value(index)` | Scaled numeric value |
| `remote.get_item_text_value(index)` | Text value or formatted number |
| `remote.get_item_name(index)` | Remotable item name |
| `remote.get_item_name_and_value(index)` | "Name: Value" string |
| `remote.get_item_short_name(index)` | Short name (max 8 chars) |
| `remote.get_item_shortest_name(index)` | Shortest name (max 4 chars) |
| `remote.get_item_mode(index)` | Current mode number (1-based) |
| `remote.get_item_state(index)` | Table with all state info |
| `remote.is_item_enabled(index)` | True if mapped |
| `remote.get_time_ms()` | Current time in milliseconds |

### MIDI Handling

| Function | Description |
|----------|-------------|
| `remote.make_midi(mask, params)` | Create MIDI event from pattern |
| `remote.match_midi(mask, event)` | Match event against pattern, extract values |
| `remote.handle_input(msg)` | Send input message to Reason |
| `remote.trace(str)` | Debug output (Codec Test only) |

### MIDI Event Structure

```lua
-- Incoming event (in remote_process_midi)
event = {
    [1] = 0xB0,      -- First byte
    [2] = 0x40,      -- Second byte
    [3] = 0x7F,      -- Third byte
    size = 3,        -- Event size in bytes
    port = 1,        -- Input port number
    time_stamp = ... -- High-precision timestamp (don't modify!)
}

-- Input message (for remote.handle_input)
msg = {
    item = 5,                    -- Control surface item index
    value = 127,                 -- Value (0-1 for buttons, range for values)
    note = 60,                   -- For keyboard: note number
    velocity = 100,              -- For keyboard: velocity
    time_stamp = event.time_stamp -- Copy from MIDI event!
}
```

## Bitlib Functions

Bit manipulation library included with Remote:

| Function | Description |
|----------|-------------|
| `bit.bnot(a)` | One's complement |
| `bit.band(w1, ...)` | Bitwise AND |
| `bit.bor(w1, ...)` | Bitwise OR |
| `bit.bxor(w1, ...)` | Bitwise XOR |
| `bit.lshift(a, b)` | Left shift |
| `bit.rshift(a, b)` | Logical right shift |
| `bit.arshift(a, b)` | Arithmetic right shift |
| `bit.mod(a, b)` | Integer remainder |

## Remote Map File Format

Tab-delimited text file with sections:

```
Propellerhead Remote Mapping File
File Format Version	1.0.0

Control Surface Manufacturer	OpenPush
Control Surface Model	Transport

Map Version	1.0.0

Scope	Propellerheads	Reason Document
//	Control Surface Item	Key	Remotable Item	Scale	Mode
Map	Play	 	Play
Map	Stop	 	Stop
Map	Record	 	Record

Scope	Propellerheads	Mixer 14:2
Define Group	Keyboard Shortcut Variations	Ch1-8	Ch9-14
//	Control Surface Item	Key	Remotable Item	Scale	Mode	Group
Map	Fader 1	 	Channel 1 Level	 	 	Ch1-8
Map	Fader 1	 	Channel 9 Level	 	 	Ch9-14
```

### Scope Categories (Priority Order)
1. Device scopes (Subtractor, Mixer, etc.) - highest priority
2. "Reason Document" scope (transport, undo, track selection)
3. "Master Keyboard" scope (keyboard, pitch bend, mod wheel) - lowest priority

### Groups
- `Keyboard Shortcut Variations` - User selects via keyboard shortcuts in Reason
- Custom groups - Surface buttons can select via `Map -> Button -> -> GroupName=Value`

## OpenPush Architecture Notes

Since OpenPush uses Python as a bridge between Push hardware and Reason:

1. **Python handles**: Push MIDI protocol, pad colors, LCD display, mode switching
2. **Lua codec handles**: Receiving translated CC messages, sending to Reason
3. **Virtual MIDI ports**: Python creates ports, Lua codecs connect to them

This means OpenPush Lua codecs can be simpler than typical codecs because:
- No complex MIDI parsing needed (Python normalizes to simple CC)
- No display output needed (Python controls Push LCD directly)
- Auto inputs/outputs handle most message routing

### OpenPush SysEx Header
OpenPush uses `F0 00 11 22 ...` (distinct from Push's `F0 47 7F 15 ...`)

### Port Assignment
- Port 1 (`0x01`): Transport
- Port 2 (`0x02`): Devices
- Port 3 (`0x03`): Mixer

## SDK Utilities

The Remote SDK includes:
- **Codec Test** - Test codecs without running Reason
- **Lua Interpreter** - Interactive Lua for learning
- **MIDI Monitor** - Recommended: [snoize.com/MIDIMonitor](http://www.snoize.com/MIDIMonitor/) (Mac)

## References

- Remote Codec Developer Documentation (RemoteSDK_Mac_1.2.0)
- Reason Remote Support.pdf (lists all Remotable Items)
- Nektar Pacer.lua - Clean reference implementation
- PusheR remotemaps - Feature mapping examples
