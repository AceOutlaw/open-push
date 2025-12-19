--[[
OpenPush Devices Codec for Reason
==================================

Handles device/instrument parameters via the 8 encoders.

Communication with the Python bridge uses custom SysEx:
  F0 00 11 22 02 [msg_type] [data...] F7

Port ID: 0x02 (Devices)

Features:
- 8 encoders for parameter control
- 8 buttons above encoders for parameter selection
- LCD display for parameter names and values
- Pad grid for note input or drum triggering

Install: Copy to Reason's Codecs folder:
  macOS: /Library/Application Support/Propellerhead Software/Remote/Codecs/
  Windows: %PROGRAMDATA%\Propellerhead Software\Remote\Codecs\
]]--

-- Message types (must match protocol.py MessageType)
MSG_DEVICE_ENCODER = 0x20
MSG_DEVICE_ENCODER_TOUCH = 0x21
MSG_DEVICE_BUTTON = 0x22
MSG_DEVICE_SELECT = 0x23
MSG_DEVICE_PARAM = 0x24
MSG_DEVICE_NAME = 0x25
MSG_DISPLAY_LINE = 0x40

-- State tracking
g_last_input_time = 0
g_encoder_touch = {}
g_lcd_state = {}

for i = 1, 8 do
    g_encoder_touch[i] = false
end

for i = 1, 24 do
    g_lcd_state[i] = {text = string.rep(" ", 8), changed = false}
end

------------------------------------------------------------------------
-- REMOTE SDK CALLBACKS
------------------------------------------------------------------------

function remote_init(manufacturer, model)
    local items = {
        -- 8 Encoders for device parameters (relative mode)
        {name = "Encoder 1", input = "delta", output = "value", min = 0, max = 127},
        {name = "Encoder 2", input = "delta", output = "value", min = 0, max = 127},
        {name = "Encoder 3", input = "delta", output = "value", min = 0, max = 127},
        {name = "Encoder 4", input = "delta", output = "value", min = 0, max = 127},
        {name = "Encoder 5", input = "delta", output = "value", min = 0, max = 127},
        {name = "Encoder 6", input = "delta", output = "value", min = 0, max = 127},
        {name = "Encoder 7", input = "delta", output = "value", min = 0, max = 127},
        {name = "Encoder 8", input = "delta", output = "value", min = 0, max = 127},

        -- Encoder touch detection
        {name = "Encoder Touch 1", input = "button"},
        {name = "Encoder Touch 2", input = "button"},
        {name = "Encoder Touch 3", input = "button"},
        {name = "Encoder Touch 4", input = "button"},
        {name = "Encoder Touch 5", input = "button"},
        {name = "Encoder Touch 6", input = "button"},
        {name = "Encoder Touch 7", input = "button"},
        {name = "Encoder Touch 8", input = "button"},

        -- Upper row buttons (above display, for parameter page selection)
        {name = "Upper Button 1", input = "button", output = "value"},
        {name = "Upper Button 2", input = "button", output = "value"},
        {name = "Upper Button 3", input = "button", output = "value"},
        {name = "Upper Button 4", input = "button", output = "value"},
        {name = "Upper Button 5", input = "button", output = "value"},
        {name = "Upper Button 6", input = "button", output = "value"},
        {name = "Upper Button 7", input = "button", output = "value"},
        {name = "Upper Button 8", input = "button", output = "value"},

        -- Lower row buttons (below display)
        {name = "Lower Button 1", input = "button", output = "value"},
        {name = "Lower Button 2", input = "button", output = "value"},
        {name = "Lower Button 3", input = "button", output = "value"},
        {name = "Lower Button 4", input = "button", output = "value"},
        {name = "Lower Button 5", input = "button", output = "value"},
        {name = "Lower Button 6", input = "button", output = "value"},
        {name = "Lower Button 7", input = "button", output = "value"},
        {name = "Lower Button 8", input = "button", output = "value"},

        -- Device navigation
        {name = "Device Left", input = "button"},
        {name = "Device Right", input = "button"},
        {name = "Device Lock", input = "button", output = "value"},

        -- Keyboard for pad input
        {name = "Keyboard", input = "keyboard"},

        -- LCD fields for parameter names (8 fields, ~8 chars each)
        {name = "Param Name 1", output = "text"},
        {name = "Param Name 2", output = "text"},
        {name = "Param Name 3", output = "text"},
        {name = "Param Name 4", output = "text"},
        {name = "Param Name 5", output = "text"},
        {name = "Param Name 6", output = "text"},
        {name = "Param Name 7", output = "text"},
        {name = "Param Name 8", output = "text"},

        -- LCD fields for parameter values
        {name = "Param Value 1", output = "text"},
        {name = "Param Value 2", output = "text"},
        {name = "Param Value 3", output = "text"},
        {name = "Param Value 4", output = "text"},
        {name = "Param Value 5", output = "text"},
        {name = "Param Value 6", output = "text"},
        {name = "Param Value 7", output = "text"},
        {name = "Param Value 8", output = "text"},

        -- Device name display
        {name = "Device Name", output = "text"},
    }

    remote.define_items(items)

    -- Input patterns from bridge
    local inputs = {
        -- Encoders (CC 0x47-0x4E, relative mode: 64=center)
        {pattern = "bf 47 xx", name = "Encoder 1", value = "x - 64"},
        {pattern = "bf 48 xx", name = "Encoder 2", value = "x - 64"},
        {pattern = "bf 49 xx", name = "Encoder 3", value = "x - 64"},
        {pattern = "bf 4a xx", name = "Encoder 4", value = "x - 64"},
        {pattern = "bf 4b xx", name = "Encoder 5", value = "x - 64"},
        {pattern = "bf 4c xx", name = "Encoder 6", value = "x - 64"},
        {pattern = "bf 4d xx", name = "Encoder 7", value = "x - 64"},
        {pattern = "bf 4e xx", name = "Encoder 8", value = "x - 64"},

        -- Encoder touch (CC 0x57-0x5E)
        {pattern = "bf 57 xx", name = "Encoder Touch 1", value = "x > 0"},
        {pattern = "bf 58 xx", name = "Encoder Touch 2", value = "x > 0"},
        {pattern = "bf 59 xx", name = "Encoder Touch 3", value = "x > 0"},
        {pattern = "bf 5a xx", name = "Encoder Touch 4", value = "x > 0"},
        {pattern = "bf 5b xx", name = "Encoder Touch 5", value = "x > 0"},
        {pattern = "bf 5c xx", name = "Encoder Touch 6", value = "x > 0"},
        {pattern = "bf 5d xx", name = "Encoder Touch 7", value = "x > 0"},
        {pattern = "bf 5e xx", name = "Encoder Touch 8", value = "x > 0"},

        -- Upper row buttons (CC 0x66-0x6D)
        {pattern = "bf 66 xx", name = "Upper Button 1", value = "x"},
        {pattern = "bf 67 xx", name = "Upper Button 2", value = "x"},
        {pattern = "bf 68 xx", name = "Upper Button 3", value = "x"},
        {pattern = "bf 69 xx", name = "Upper Button 4", value = "x"},
        {pattern = "bf 6a xx", name = "Upper Button 5", value = "x"},
        {pattern = "bf 6b xx", name = "Upper Button 6", value = "x"},
        {pattern = "bf 6c xx", name = "Upper Button 7", value = "x"},
        {pattern = "bf 6d xx", name = "Upper Button 8", value = "x"},

        -- Lower row buttons (CC 0x14-0x1B)
        {pattern = "bf 14 xx", name = "Lower Button 1", value = "x"},
        {pattern = "bf 15 xx", name = "Lower Button 2", value = "x"},
        {pattern = "bf 16 xx", name = "Lower Button 3", value = "x"},
        {pattern = "bf 17 xx", name = "Lower Button 4", value = "x"},
        {pattern = "bf 18 xx", name = "Lower Button 5", value = "x"},
        {pattern = "bf 19 xx", name = "Lower Button 6", value = "x"},
        {pattern = "bf 1a xx", name = "Lower Button 7", value = "x"},
        {pattern = "bf 1b xx", name = "Lower Button 8", value = "x"},

        -- Device navigation (CC 0x2C-0x2E)
        {pattern = "bf 2c xx", name = "Device Left", value = "x"},
        {pattern = "bf 2d xx", name = "Device Right", value = "x"},
        {pattern = "bf 2e xx", name = "Device Lock", value = "x"},

        -- Keyboard notes
        {pattern = "<100x>f yy zz", name = "Keyboard"},
    }

    remote.define_auto_inputs(inputs)

    -- Output patterns to bridge
    local outputs = {
        -- Encoder value feedback
        {name = "Encoder 1", pattern = "bf 47 xx"},
        {name = "Encoder 2", pattern = "bf 48 xx"},
        {name = "Encoder 3", pattern = "bf 49 xx"},
        {name = "Encoder 4", pattern = "bf 4a xx"},
        {name = "Encoder 5", pattern = "bf 4b xx"},
        {name = "Encoder 6", pattern = "bf 4c xx"},
        {name = "Encoder 7", pattern = "bf 4d xx"},
        {name = "Encoder 8", pattern = "bf 4e xx"},

        -- Button LED feedback
        {name = "Upper Button 1", pattern = "bf 66 xx"},
        {name = "Upper Button 2", pattern = "bf 67 xx"},
        {name = "Upper Button 3", pattern = "bf 68 xx"},
        {name = "Upper Button 4", pattern = "bf 69 xx"},
        {name = "Upper Button 5", pattern = "bf 6a xx"},
        {name = "Upper Button 6", pattern = "bf 6b xx"},
        {name = "Upper Button 7", pattern = "bf 6c xx"},
        {name = "Upper Button 8", pattern = "bf 6d xx"},

        {name = "Lower Button 1", pattern = "bf 14 xx"},
        {name = "Lower Button 2", pattern = "bf 15 xx"},
        {name = "Lower Button 3", pattern = "bf 16 xx"},
        {name = "Lower Button 4", pattern = "bf 17 xx"},
        {name = "Lower Button 5", pattern = "bf 18 xx"},
        {name = "Lower Button 6", pattern = "bf 19 xx"},
        {name = "Lower Button 7", pattern = "bf 1a xx"},
        {name = "Lower Button 8", pattern = "bf 1b xx"},

        {name = "Device Lock", pattern = "bf 2e xx"},
    }

    remote.define_auto_outputs(outputs)
end

function remote_on_auto_input(item_index)
    if item_index > 0 then
        g_last_input_time = remote.get_time_ms()
    end
end

function remote_set_state(changed_items)
    -- Handle LCD parameter name updates
    for i = 1, 8 do
        local name_item = string.format("Param Name %d", i)
        if changed_items[name_item] then
            local text = remote.get_item_text_value(remote.get_item_index(name_item))
            text = string.format("%-8.8s", text or "")
            if text ~= g_lcd_state[i].text then
                g_lcd_state[i].text = text
                g_lcd_state[i].changed = true
            end
        end
    end

    -- Handle LCD parameter value updates
    for i = 1, 8 do
        local value_item = string.format("Param Value %d", i)
        if changed_items[value_item] then
            local text = remote.get_item_text_value(remote.get_item_index(value_item))
            text = string.format("%-8.8s", text or "")
            local idx = i + 8
            if text ~= g_lcd_state[idx].text then
                g_lcd_state[idx].text = text
                g_lcd_state[idx].changed = true
            end
        end
    end

    -- Handle device name
    if changed_items["Device Name"] then
        local text = remote.get_item_text_value(remote.get_item_index("Device Name"))
        text = string.format("%-16.16s", text or "")
        if text ~= g_lcd_state[17].text then
            g_lcd_state[17].text = text
            g_lcd_state[17].changed = true
        end
    end
end

function remote_deliver_midi(max_bytes, port)
    local events = {}

    -- Send parameter name updates (fields 1-8)
    for i = 1, 8 do
        if g_lcd_state[i].changed then
            local sysex_str = string.format("f0 00 11 22 02 %02x %02x 00", MSG_DEVICE_PARAM, i)
            for j = 1, 8 do
                local char = string.byte(g_lcd_state[i].text, j) or 0x20
                sysex_str = sysex_str .. string.format(" %02x", char)
            end
            sysex_str = sysex_str .. " f7"
            table.insert(events, remote.make_midi(sysex_str))
            g_lcd_state[i].changed = false
        end
    end

    -- Send parameter value updates (fields 9-16)
    for i = 9, 16 do
        if g_lcd_state[i].changed then
            local sysex_str = string.format("f0 00 11 22 02 %02x %02x 01", MSG_DEVICE_PARAM, i - 8)
            for j = 1, 8 do
                local char = string.byte(g_lcd_state[i].text, j) or 0x20
                sysex_str = sysex_str .. string.format(" %02x", char)
            end
            sysex_str = sysex_str .. " f7"
            table.insert(events, remote.make_midi(sysex_str))
            g_lcd_state[i].changed = false
        end
    end

    -- Send device name update (field 17)
    if g_lcd_state[17].changed then
        local sysex_str = string.format("f0 00 11 22 02 %02x", MSG_DEVICE_NAME)
        for j = 1, 16 do
            local char = string.byte(g_lcd_state[17].text, j) or 0x20
            sysex_str = sysex_str .. string.format(" %02x", char)
        end
        sysex_str = sysex_str .. " f7"
        table.insert(events, remote.make_midi(sysex_str))
        g_lcd_state[17].changed = false
    end

    return events
end

function remote_probe(manufacturer, model, prober)
    return {
        request = "f0 00 11 22 02 f0 f7",
        response = "f0 00 11 22 02 f1 ?? f7"
    }
end

function remote_prepare_for_use()
    return {}
end

function remote_release_from_use()
    return {}
end
