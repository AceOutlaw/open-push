# Reason Transport & Display Implementation Guide

This guide outlines how to implement Transport controls and LCD Display support for the OpenPush project. 

**Architectural Note:** Unlike the native Novation Launchkey scripts, OpenPush uses a **Python Bridge** architecture. The Lua codec communicates with the Python bridge using a custom SysEx protocol, which the bridge then translates to native Push hardware commands.

## 1. Transport Control Implementation

### MIDI Mapping (Reason <-> Bridge)

The Lua codec communicates with the Python bridge (`src/open_push/reason/bridge.py`) using specific CCs and SysEx messages.

| Function | Reason CC | Bridge Action |
|----------|-----------|---------------|
| **Play** | 85 | Updates internal state & LED |
| **Stop** | 29 | Updates internal state |
| **Record** | 86 | Updates internal state & LED |
| **Loop** | 117 | Updates internal state & LED |
| **Metronome** | 9 | Updates internal state & LED |

### Lua Codec Setup (`.lua`)

In `remote_init`, define the transport items and map them to the bridge's expected CCs.

```lua
function remote_init(manufacturer, model)
    local items = {
        {name="Play", input="button", output="value"},
        {name="Stop", input="button", output="value"},
        {name="Record", input="button", output="value"},
        {name="Loop", input="button", output="value"},
        {name="Metronome", input="button", output="value"},
        -- ... other items
    }
    remote.define_items(items)

    local inputs = {
        {pattern="bf 55 xx", name="Play"},   -- CC 85
        {pattern="bf 1d xx", name="Stop"},   -- CC 29
        {pattern="bf 56 xx", name="Record"}, -- CC 86
        {pattern="bf 75 xx", name="Loop"},   -- CC 117 (Note: Novation uses 55/0x37, we use 117/0x75)
        {pattern="bf 09 xx", name="Metronome"}, -- CC 9
    }
    remote.define_auto_inputs(inputs)

    local outputs = {
        {name="Play", pattern="bf 55 xx", x="value*127"},
        {name="Record", pattern="bf 56 xx", x="value*127"},
        {name="Loop", pattern="bf 75 xx", x="value*127"},
        {name="Metronome", pattern="bf 09 xx", x="value*127"},
    }
    remote.define_auto_outputs(outputs)
end
```

---

## 2. Advanced Display Logic (The "Missing Piece")

The key feature found in the Novation scripts but missing from basic implementations is **Event-Driven Display Logic** (Popup Values). This allows the screen to temporarily show a parameter value when a knob is touched, then revert to the patch name.

### OpenPush SysEx Protocol

The Lua script sends messages to the Bridge using this custom header:
`F0 00 11 22 [PortID] [MsgType] ... F7`

*   **Port ID:** `0x01` (Transport)
*   **Msg Type:** `0x40` (DISPLAY_LINE)

**Format:**
`F0 00 11 22 01 40 [LineNum] [AsciiChars...] F7`
*   `LineNum`: 1-4

### Lua Implementation Strategy

To achieve the "Popup" behavior, we need to track state in Lua and send updates only when necessary.

#### 1. Define Variables
```lua
local g_lcd_state = {
    line1 = {text="", dirty=false},
    line2 = {text="", dirty=false},
    -- ...
}
local g_last_touched_param = nil
local g_popup_timer = 0
```

#### 2. Track Changes in `remote_set_state`
Instead of mapping `LCD` items directly in `.remotemap`, map the meaningful data (Device Name, Param 1, etc.) to hidden items in Lua, then process them.

```lua
function remote_set_state(changed_items)
    -- Check if a fader/knob changed
    if remote.is_item_changed(g_fader1_index) then
        local val = remote.get_item_text_value(g_fader1_index)
        local name = remote.get_item_name(g_fader1_index)
        
        -- Trigger Popup: Show Value on Line 1, Name on Line 2
        update_display_line(1, "Vol: " .. val)
        update_display_line(2, name)
        
        -- Reset timer to revert screen after 2 seconds
        g_popup_timer = remote.get_time_ms() + 2000
    end
end
```

#### 3. Handle Updates in `remote_deliver_midi`
This function is called repeatedly. Use it to send dirty lines and handle the "revert" logic.

```lua
function remote_deliver_midi(max_bytes, port)
    local events = {}
    
    -- Check Popup Timer
    if g_popup_timer > 0 and remote.get_time_ms() > g_popup_timer then
        -- Revert to default view (e.g., Patch Name)
        update_display_line(1, g_current_patch_name)
        update_display_line(2, "")
        g_popup_timer = 0
    end

    -- Send SysEx for dirty lines
    for i=1, 4 do
        if g_lcd_state["line"..i].dirty then
            local text = g_lcd_state["line"..i].text
            local sysex = create_openpush_sysex(0x40, i, text)
            table.insert(events, remote.make_midi(sysex))
            g_lcd_state["line"..i].dirty = false
        end
    end
    
    return events
end
```

#### 4. Helper Function: `create_openpush_sysex`
```lua
function create_openpush_sysex(msg_type, line_idx, text)
    local hex_text = ""
    for i=1, #text do
        hex_text = hex_text .. string.format("%02X ", string.byte(text, i, i))
    end
    
    -- F0 00 11 22 01 [MsgType] [Line] [Text] F7
    return "F0 00 11 22 01 " .. string.format("%02X", msg_type) .. 
           " " .. string.format("%02X", line_idx) .. " " .. hex_text .. "F7"
end
```

### Summary of Differences from Native

1.  **Protocol:** We send `F0 00 11 22...` (OpenPush) instead of `F0 47 7F...` (Native Push).
2.  **Formatting:** We send one long string for the line. The **Python Bridge** handles splitting it into the 4 physical segments (17 chars each) to account for the gaps between encoders.
3.  **Logic:** The "intelligence" (when to show what) lives in Lua, but the "rendering" (pixels/bytes) lives in Python.