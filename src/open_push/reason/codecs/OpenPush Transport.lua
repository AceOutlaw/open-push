--[[
OpenPush Transport Codec for Reason
====================================

Handles transport controls, tempo, and global navigation.
Implements event-driven display logic (popups) for parameter feedback.

Communication with the Python bridge uses custom SysEx:
  F0 00 11 22 01 [msg_type] [data...] F7

Port ID: 0x01 (Transport)
]]--

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
g_debug_enabled = true
g_log_buffer = "=== OpenPush Transport Debug ===\n"
g_track_state = {
    track = "",
    patch = "",
    device = "",
    song = "",
    bars = "",       -- Bar position (separate for proper formatting)
    beats = "",      -- Beat position (separate for proper formatting)
    position = "",   -- Combined bars:beats
    left_loop = "",
    right_loop = "",
    loop_state = "",
    tempo = "",
}

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

local function build_segments(seg0, seg1, seg2, seg3)
    return pad_string(seg0, 17) .. pad_string(seg1, 17) .. pad_string(seg2, 17) .. pad_string(seg3, 17)
end

local function set_display_line(line_idx, text)
    local padded = pad_string(text, 68)
    if g_display[line_idx].persistent_text ~= padded then
        g_display[line_idx].persistent_text = padded
        g_display[line_idx].dirty = true
    end
end

local function update_track_display()
    local line1 = pad_string(g_track_state.track, 34) .. pad_string(g_track_state.patch, 34)
    local line2 = pad_string(g_track_state.device, 34) .. pad_string(g_track_state.song, 34)
    -- Format position as "Bar:Beat", loop points as bar numbers
    local pos_display = g_track_state.position ~= "" and g_track_state.position or "--"
    local left_display = g_track_state.left_loop ~= "" and g_track_state.left_loop or "--"
    local right_display = g_track_state.right_loop ~= "" and g_track_state.right_loop or "--"
    local tempo_display = g_track_state.tempo ~= "" and g_track_state.tempo or "--"
    local line3 = build_segments(
        "Pos " .. pos_display,
        "Loop L " .. left_display,
        "Loop R " .. right_display,
        tempo_display .. " BPM"
    )
    local line4 = build_segments("Loop " .. g_track_state.loop_state, "", "", "")

    set_display_line(1, line1)
    set_display_line(2, line2)
    set_display_line(3, line3)
    set_display_line(4, line4)
end

local function get_changed_indices(changed_items)
    local indices = {}
    for k, v in pairs(changed_items) do
        if type(k) == "number" and type(v) == "number" then
            table.insert(indices, v)
        elseif type(k) == "number" and v == true then
            table.insert(indices, k)
        end
    end
    return indices
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
        {name = "Loop", input = "button", output = "value", min = 0, max = 127},
        {name = "Metronome", input = "button", output = "value", min = 0, max = 127},
        {name = "Precount", input = "button", output = "value", min = 0, max = 127},
        {name = "TapTempo", input = "button"},

        -- Tempo encoder (delta input + value output for display, Scale in remotemap defines units)
        {name = "Tempo", input = "delta", output = "value", min = -127, max = 127},
        {name = "ClickLevel", input = "delta", output = "value", min = -127, max = 127},

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
        {name = "LCD4", output = "text"},
        {name = "LCD5", output = "text"},

        -- Track mode controls (encoder inputs + text output for display)
        {name = "Track Select", input = "delta"},
        {name = "Patch Select", input = "delta"},
        {name = "Playhead Bars", input = "delta", output = "text"},   -- Bar Position (control + display)
        {name = "Playhead Beats", input = "delta", output = "text"},  -- Beat Position (control + display)
        {name = "Left Loop", input = "delta"},                        -- Left Loop (control only)
        {name = "Right Loop", input = "delta"},                       -- Right Loop (control only)

        -- Track mode display (text outputs from distinct Reason remotables)
        {name = "Left Loop Bar Display", output = "text"},            -- Left Loop Bar (separate remotable)
        {name = "Right Loop Bar Display", output = "text"},           -- Right Loop Bar (separate remotable)
        {name = "Track Prev", input = "button"},
        {name = "Track Next", input = "button"},
        {name = "Patch Prev", input = "button"},
        {name = "Patch Next", input = "button"},
        {name = "Goto Left", input = "button"},
        {name = "Goto Right", input = "button"},
        {name = "Move Loop Left", input = "button"},
        {name = "Move Loop Right", input = "button"},
        {name = "Track Mute", input = "button", output = "value", min = 0, max = 1},
        {name = "Track Solo", input = "button", output = "value", min = 0, max = 1},
        {name = "Song Position", output = "text"},
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
        {pattern = "bf 75 xx", name = "Loop", value = "x"},        -- CC 117 (Double Loop button)
        {pattern = "bf 09 xx", name = "Metronome", value = "x"},  -- CC 9
        {pattern = "bf 0a xx", name = "Precount", value = "x"},   -- CC 10 (Shift+Metronome)
        {pattern = "bf 03 xx", name = "TapTempo", value = "x"},   -- CC 3

        -- Encoders (left side - relative values: 1-63=CW, 65-127=CCW)
        -- Tempo encoder (CC 14) - 1 click = 1 BPM
        {pattern = "bf 0e xx", name = "Tempo", value = "x - 64"},

        -- Click Level encoder (CC 15) - metronome volume (Scale=10 in remotemap)
        {pattern = "bf 0f xx", name = "ClickLevel", value = "x - 64"},

        -- Navigation (CC 0x60-0x63)
        {pattern = "bf 2e xx", name = "NavigateUp", value = "x"},
        {pattern = "bf 2f xx", name = "NavigateDown", value = "x"},
        {pattern = "bf 2c xx", name = "NavigateLeft", value = "x"},
        {pattern = "bf 2d xx", name = "NavigateRight", value = "x"},

        -- Browser
        {pattern = "bf 30 xx", name = "BrowserSelect", value = "x"},
        {pattern = "bf 33 xx", name = "BrowserBack", value = "x"},

        -- Track mode encoders (Push 1 encoders above display)
        -- Matches PusheR layout: Enc1=Track, Enc2=Playhead, Enc3=Patch, Enc5=Left, Enc6=Right
        {pattern = "bf 47 xx", name = "Track Select", value = "x - 64"},   -- CC 71 (Enc 1)
        {pattern = "bf 48 xx", name = "Playhead Bars", value = "x - 64"},  -- CC 72 (Enc 2)
        {pattern = "bf 51 xx", name = "Playhead Beats", value = "x - 64"}, -- CC 81 (Shift+Enc2)
        {pattern = "bf 49 xx", name = "Patch Select", value = "x - 64"},   -- CC 73 (Enc 3)
        {pattern = "bf 4b xx", name = "Left Loop", value = "x - 64"},      -- CC 75 (Enc 5)
        {pattern = "bf 4c xx", name = "Right Loop", value = "x - 64"},     -- CC 76 (Enc 6)

        -- Track mode buttons (16 buttons below LCD)
        {pattern = "bf 14 xx", name = "Track Prev", value = "x"},          -- CC 20
        {pattern = "bf 15 xx", name = "Track Next", value = "x"},          -- CC 21
        {pattern = "bf 16 xx", name = "Patch Prev", value = "x"},          -- CC 22
        {pattern = "bf 17 xx", name = "Patch Next", value = "x"},          -- CC 23
        {pattern = "bf 18 xx", name = "Goto Left", value = "x"},           -- CC 24
        {pattern = "bf 19 xx", name = "Goto Right", value = "x"},          -- CC 25
        {pattern = "bf 1a xx", name = "Move Loop Left", value = "x"},      -- CC 26
        {pattern = "bf 1b xx", name = "Move Loop Right", value = "x"},     -- CC 27
        {pattern = "bf 66 xx", name = "Track Prev", value = "x"},          -- CC 102
        {pattern = "bf 67 xx", name = "Track Next", value = "x"},          -- CC 103
        {pattern = "bf 68 xx", name = "Patch Prev", value = "x"},          -- CC 104
        {pattern = "bf 69 xx", name = "Patch Next", value = "x"},          -- CC 105
        {pattern = "bf 6a xx", name = "Goto Left", value = "x"},           -- CC 106
        {pattern = "bf 6b xx", name = "Goto Right", value = "x"},          -- CC 107
        {pattern = "bf 6c xx", name = "Move Loop Left", value = "x"},      -- CC 108
        {pattern = "bf 6d xx", name = "Move Loop Right", value = "x"},     -- CC 109

        -- Track mute/solo buttons (dedicated hardware buttons)
        {pattern = "bf 3c xx", name = "Track Mute", value = "x"},          -- CC 60
        {pattern = "bf 3d xx", name = "Track Solo", value = "x"},          -- CC 61

        -- Keyboard
        {pattern = "<100x>f yy zz", name = "Keyboard"},
    }
    remote.define_auto_inputs(inputs)

    local outputs = {
        -- Using xx pattern for LED feedback (value = item state)
        {name = "Play", pattern = "bf 55 xx", x = "value"},
        {name = "Stop", pattern = "bf 1d xx", x = "value"},
        {name = "Record", pattern = "bf 56 xx", x = "value"},
        {name = "Loop", pattern = "bf 75 xx", x = "value"},        -- CC 117
        {name = "Metronome", pattern = "bf 09 xx", x = "value"},  -- CC 9
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

    end
end

function remote_set_state(changed_items)
    local changed = get_changed_indices(changed_items)
    local track_dirty = false
    local track_name_items = {
        ["LCD1"] = true,
        ["LCD5"] = true,
        ["Target Track Name"] = true,
    }
    local song_name_items = {
        ["LCD2"] = true,
        ["LCD4"] = true,
        ["Document Name"] = true,
    }
    local device_name_items = {
        ["Device Name"] = true,
        ["Target Device Name"] = true,
    }
    local patch_items = {
        ["Patch Select"] = true,
        ["Select Patch for Target Device (Delta)"] = true,
        ["Select Patch for Target Device"] = true,
    }
    local bars_items = {
        ["Playhead Bars"] = true,        -- Control surface item name
        ["Bar Position"] = true,         -- Reason remotable name
    }
    local beats_items = {
        ["Playhead Beats"] = true,       -- Control surface item name
        ["Beat Position"] = true,        -- Reason remotable name
    }
    local left_loop_items = {
        ["Left Loop Bar Display"] = true,  -- Control surface item name
        ["Left Loop Bar"] = true,          -- Reason remotable name
    }
    local right_loop_items = {
        ["Right Loop Bar Display"] = true, -- Control surface item name
        ["Right Loop Bar"] = true,         -- Reason remotable name
    }
    local tempo_items = {
        ["Tempo"] = true,
        ["Tempo BPM"] = true,
    }

    for _, idx in ipairs(changed) do
        local name = remote.get_item_name(idx)
        if name then
            log(string.format("CHANGED idx=%d name=%s", idx, name))
        end

        if name and track_name_items[name] then
            g_track_state.track = remote.get_item_text_value(idx) or ""
            log(string.format("ITEM %s idx=%d text='%s'", name, idx, g_track_state.track or ""))
            track_dirty = true
        elseif name and song_name_items[name] then
            g_track_state.song = remote.get_item_text_value(idx) or ""
            log(string.format("ITEM %s idx=%d text='%s'", name, idx, g_track_state.song or ""))
            track_dirty = true
        elseif name and device_name_items[name] then
            g_track_state.device = remote.get_item_text_value(idx) or ""
            log(string.format("ITEM %s idx=%d text='%s'", name, idx, g_track_state.device or ""))
            track_dirty = true
        elseif name and tempo_items[name] then
            local val = remote.get_item_text_value(idx) or ""
            local tempo_name = name == "Tempo BPM" and "Tempo" or name
            log(string.format("ITEM %s idx=%d text='%s'", tempo_name, idx, val or ""))
            g_display[1].popup_text = pad_string(tempo_name .. ": " .. val, 68)
            g_display[1].is_popup = true
            g_display[1].timer = remote.get_time_ms() + 1500 -- 1.5s popup
            g_display[1].dirty = true
            g_track_state.tempo = val
            track_dirty = true
        elseif name and patch_items[name] then
            g_track_state.patch = remote.get_item_text_value(idx) or ""
            log(string.format("ITEM %s idx=%d text='%s'", name, idx, g_track_state.patch or ""))
            track_dirty = true
        elseif name and bars_items[name] then
            g_track_state.bars = remote.get_item_text_value(idx) or ""
            log(string.format("ITEM %s idx=%d text='%s'", name, idx, g_track_state.bars or ""))
            -- Update combined position
            if g_track_state.beats ~= "" then
                g_track_state.position = g_track_state.bars .. ":" .. g_track_state.beats
            else
                g_track_state.position = g_track_state.bars
            end
            track_dirty = true
        elseif name and beats_items[name] then
            g_track_state.beats = remote.get_item_text_value(idx) or ""
            log(string.format("ITEM %s idx=%d text='%s'", name, idx, g_track_state.beats or ""))
            -- Update combined position
            if g_track_state.bars ~= "" then
                g_track_state.position = g_track_state.bars .. ":" .. g_track_state.beats
            else
                g_track_state.position = g_track_state.beats
            end
            track_dirty = true
        elseif name == "Song Position" then
            -- Fallback: Song Position returns formatted position
            g_track_state.position = remote.get_item_text_value(idx) or ""
            log(string.format("ITEM %s idx=%d text='%s'", name, idx, g_track_state.position or ""))
            track_dirty = true
        elseif name and left_loop_items[name] then
            g_track_state.left_loop = remote.get_item_text_value(idx) or ""
            log(string.format("ITEM %s idx=%d text='%s'", name, idx, g_track_state.left_loop or ""))
            track_dirty = true
        elseif name and right_loop_items[name] then
            g_track_state.right_loop = remote.get_item_text_value(idx) or ""
            log(string.format("ITEM %s idx=%d text='%s'", name, idx, g_track_state.right_loop or ""))
            track_dirty = true
        elseif name == "Loop" then
            local loop_val = remote.get_item_value(idx) or 0
            g_track_state.loop_state = loop_val > 0 and "On" or "Off"
            log(string.format("ITEM %s idx=%d value=%s", name, idx, tostring(loop_val)))
            track_dirty = true
        end
    end

    if track_dirty then
        update_track_display()
    end
end

function remote_process_midi(event)
    -- Manual debug dump on CC117 (Loop/Double Loop button on Push)
    local trigger = remote.match_midi("bf 75 xx", event)
    if trigger and trigger.x > 0 then
        log("DEBUG dump triggered by CC117")
        dump_log()
        return true
    end

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

    for i = 1, 4 do
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
