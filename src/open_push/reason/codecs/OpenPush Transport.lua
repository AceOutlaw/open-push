--[[
OpenPush Transport Codec for Reason
====================================

Handles transport controls, tempo, and global navigation.
Implements event-driven display logic (popups) for parameter feedback.

Communication with the Python bridge uses custom SysEx:
  F0 00 11 22 01 [msg_type] [data...] F7

Port ID: 0x01 (Transport)
]]--

-- Item indices (must match order in remote_init items table)
LCD_ITEM_START = 16  -- LCD1 is at index 16

-- Message types (must match protocol.py MessageType)
MSG_DISPLAY_LINE = 0x40
MSG_REQUEST_LCD = 0x4F

-- SysEx header for OpenPush protocol
SYSEX_HEADER_HEX = "f0 00 11 22 01"

-- State tracking
g_last_input_time = 0
g_last_input_item = 0

-- Debug logging (see docs/18-lua-debugging-and-logging.md)
-- Set to true to enable debug crash dump after 3 Play presses
g_debug_enabled = false
g_log_buffer = "=== OpenPush Transport Debug ===\n"
g_play_press_count = 0

function log(msg)
    if g_debug_enabled then
        g_log_buffer = g_log_buffer .. msg .. "\n"
    end
end

function dump_log()
    if g_debug_enabled then
        error(g_log_buffer)
    end
end

-- Display State (4 Lines)
g_display = {}
for i = 1, 4 do
    g_display[i] = {
        persistent_text = string.rep(" ", 68), -- Default text (e.g. Patch Name)
        popup_text = "",                       -- Temporary text (e.g. "Vol: 100")
        is_popup = false,
        timer = 0,
        last_sent = "",                        -- Cache to avoid redundant MIDI
        dirty = true
    }
end

-- Helper: Pad string to length
local function pad_string(str, length)
    str = str or ""
    if string.len(str) > length then
        return string.sub(str, 1, length)
    else
        return str .. string.rep(" ", length - string.len(str))
    end
end

-- Helper: Create OpenPush SysEx
local function create_sysex(msg_type, line_idx, text)
    local hex = SYSEX_HEADER_HEX .. string.format(" %02x %02x", msg_type, line_idx)
    for i = 1, #text do
        hex = hex .. string.format(" %02x", string.byte(text, i, i))
    end
    hex = hex .. " f7"
    return remote.make_midi(hex)
end

------------------------------------------------------------------------
-- REMOTE SDK CALLBACKS
------------------------------------------------------------------------

function remote_init(manufacturer, model)
    local items = {
        -- Transport controls (using xx pattern for full value capture)
        {name = "Play", input = "button", output = "value", min = 0, max = 127},
        {name = "Stop", input = "button", output = "value", min = 0, max = 127},
        {name = "Record", input = "button", output = "value", min = 0, max = 127},
        {name = "Rewind", input = "button"},
        {name = "Forward", input = "button"},
        {name = "Loop", input = "button", output = "value", min = 0, max = 1},
        {name = "Metronome", input = "button", output = "value", min = 0, max = 1},

        -- Tempo encoder
        {name = "Tempo", input = "delta", output = "value", min = 0, max = 999},

        -- Navigation
        {name = "NavigateUp", input = "button"},
        {name = "NavigateDown", input = "button"},
        {name = "NavigateLeft", input = "button"},
        {name = "NavigateRight", input = "button"},

        -- Browser controls
        {name = "BrowserSelect", input = "button"},
        {name = "BrowserBack", input = "button"},

        -- Keyboard input
        {name = "Keyboard", input = "keyboard"},

        -- LCD fields
        -- We map LCD1 to Line 1 (Track Name) and LCD2 to Line 2 (Device/Doc Name)
        {name = "LCD1", output = "text"},
        {name = "LCD2", output = "text"},
        -- ... add more if needed
    }
    remote.define_items(items)

    local inputs = {
        -- Transport buttons (Push 1 native CCs)
        -- Using xx pattern for full value (0-127) - simpler debugging
        {pattern = "bf 55 xx", name = "Play", value = "x"},     -- CC 85
        {pattern = "bf 1d xx", name = "Stop", value = "x"},     -- CC 29
        {pattern = "bf 56 xx", name = "Record", value = "x"},   -- CC 86
        {pattern = "bf 2c xx", name = "Rewind", value = "x"},   -- CC 44
        {pattern = "bf 2d xx", name = "Forward", value = "x"},  -- CC 45
        {pattern = "bf 75 ?<???x>", name = "Loop"},     -- CC 117
        {pattern = "bf 09 ?<???x>", name = "Metronome"},-- CC 9

        -- Tempo encoder (CC 0x0F = 15, Push tempo encoder)
        {pattern = "bf 0f xx", name = "Tempo", value = "x - 64"},

        -- Navigation
        {pattern = "bf 2e xx", name = "NavigateUp", value = "x"},
        {pattern = "bf 2f xx", name = "NavigateDown", value = "x"},
        {pattern = "bf 2c xx", name = "NavigateLeft", value = "x"},
        {pattern = "bf 2d xx", name = "NavigateRight", value = "x"},

        -- Browser
        {pattern = "bf 30 xx", name = "BrowserSelect", value = "x"},
        {pattern = "bf 33 xx", name = "BrowserBack", value = "x"},

        -- Keyboard
        {pattern = "<100x>f yy zz", name = "Keyboard"},
    }
    remote.define_auto_inputs(inputs)

    local outputs = {
        -- Using xx pattern for LED feedback (value = item state)
        {name = "Play", pattern = "bf 55 xx", x = "value"},
        {name = "Stop", pattern = "bf 1d xx", x = "value"},
        {name = "Record", pattern = "bf 56 xx", x = "value"},
        {name = "Loop", pattern = "bf 75 xx", x = "value"},
        {name = "Metronome", pattern = "bf 09 xx", x = "value"},
    }
    remote.define_auto_outputs(outputs)
end

function remote_on_auto_input(item_index)
    if item_index > 0 then
        g_last_input_time = remote.get_time_ms()
        g_last_input_item = item_index

        -- Debug: Log auto-input events
        local item_name = remote.get_item_name(item_index) or "unknown"
        local item_value = remote.get_item_value(item_index) or -1
        log("AUTO_INPUT: item=" .. item_index .. " name=" .. item_name .. " value=" .. tostring(item_value))

        -- If Play pressed (item 1), count and dump after 3
        if item_index == 1 then
            g_play_press_count = g_play_press_count + 1
            log("PLAY pressed! Count=" .. g_play_press_count)

            -- Also check if item is enabled (mapped)
            local is_enabled = remote.is_item_enabled(item_index)
            log("  is_item_enabled=" .. tostring(is_enabled))

            -- Dump after 3 presses to see what's happening
            if g_play_press_count >= 3 then
                dump_log()
            end
        end
    end
end

function remote_set_state(changed_items)
    -- Handle Persistent Text Updates (LCD1 -> Line 1, LCD2 -> Line 2)
    -- Indices: LCD1=16, LCD2=17
    
    -- Line 1 (Track Name)
    if changed_items[16] then 
        local text = remote.get_item_text_value(16)
        g_display[1].persistent_text = pad_string(text, 68)
        g_display[1].dirty = true
    end

    -- Line 2 (Device/Doc Name)
    if changed_items[17] then
        local text = remote.get_item_text_value(17)
        g_display[2].persistent_text = pad_string(text, 68)
        g_display[2].dirty = true
    end

    -- Handle Popups for Controls (Tempo, etc.)
    -- Tempo is item 8
    if changed_items[8] then
        local val = remote.get_item_text_value(8)
        local name = remote.get_item_name(8)
        
        -- Show "Tempo: 120.00" on Line 1
        g_display[1].popup_text = pad_string(name .. ": " .. val, 68)
        g_display[1].is_popup = true
        g_display[1].timer = remote.get_time_ms() + 1500 -- 1.5s popup
        g_display[1].dirty = true
    end
end

function remote_process_midi(event)
    -- Check for Request LCD SysEx
    local ret = remote.match_midi("f0 00 11 22 01 4f", event)
    if ret then
        -- Mark all lines as dirty to force resend
        for i=1, 4 do
            g_display[i].dirty = true
        end
        return true
    end
    return false
end

function remote_deliver_midi(max_bytes, port)
    local events = {}
    local time = remote.get_time_ms()

    for i = 1, 2 do -- Only checking lines 1 & 2 for now
        local line = g_display[i]

        -- Check Timer Expiry
        if line.is_popup and time > line.timer then
            line.is_popup = false
            line.dirty = true
        end

        -- Determine text to show
        local current_text = line.is_popup and line.popup_text or line.persistent_text

        -- Only send if changed from last sent OR marked dirty
        if line.dirty or current_text ~= line.last_sent then
            table.insert(events, create_sysex(MSG_DISPLAY_LINE, i, current_text))
            
            line.last_sent = current_text
            line.dirty = false
        end
    end

    return events
end

function remote_probe(manufacturer, model, prober)
    return {
        request = "f0 00 11 22 01 f0 f7",
        response = "f0 00 11 22 01 f1 ?? f7"
    }
end

function remote_prepare_for_use()
    return {}
end

function remote_release_from_use()
    return {}
end
