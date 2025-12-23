--[[
OpenPush Mixer Codec for Reason
================================

Handles mixer controls: volume, pan, mute, solo, track selection.

Communication with the Python bridge uses custom SysEx:
  F0 00 11 22 03 [msg_type] [data...] F7

Port ID: 0x03 (Mixer)

Features:
- 8 channel strips (volume, pan, mute, solo)
- Track selection via pads or buttons
- Master volume encoder
- LCD display for track names and values

Install: Copy to Reason's Codecs folder:
  macOS: /Library/Application Support/Propellerhead Software/Remote/Codecs/
  Windows: %PROGRAMDATA%\Propellerhead Software\Remote\Codecs\
]]--

-- Message types (must match protocol.py MessageType)
MSG_MIXER_VOLUME = 0x30
MSG_MIXER_PAN = 0x31
MSG_MIXER_MUTE = 0x32
MSG_MIXER_SOLO = 0x33
MSG_MIXER_ARM = 0x34
MSG_MIXER_SELECT = 0x35
MSG_MIXER_NAME = 0x36
MSG_MIXER_LEVEL = 0x37

-- State tracking
g_last_input_time = 0
g_lcd_state = {}
g_track_meters = {}

for i = 1, 24 do
    g_lcd_state[i] = {text = string.rep(" ", 8), changed = false}
end

for i = 1, 8 do
    g_track_meters[i] = 0
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

------------------------------------------------------------------------
-- REMOTE SDK CALLBACKS
------------------------------------------------------------------------

function remote_init(manufacturer, model)
    local items = {
        -- Channel volume encoders (8 channels)
        {name = "Volume 1", input = "delta", output = "value", min = 0, max = 127},
        {name = "Volume 2", input = "delta", output = "value", min = 0, max = 127},
        {name = "Volume 3", input = "delta", output = "value", min = 0, max = 127},
        {name = "Volume 4", input = "delta", output = "value", min = 0, max = 127},
        {name = "Volume 5", input = "delta", output = "value", min = 0, max = 127},
        {name = "Volume 6", input = "delta", output = "value", min = 0, max = 127},
        {name = "Volume 7", input = "delta", output = "value", min = 0, max = 127},
        {name = "Volume 8", input = "delta", output = "value", min = 0, max = 127},

        -- Channel pan encoders
        {name = "Pan 1", input = "delta", output = "value", min = 0, max = 127},
        {name = "Pan 2", input = "delta", output = "value", min = 0, max = 127},
        {name = "Pan 3", input = "delta", output = "value", min = 0, max = 127},
        {name = "Pan 4", input = "delta", output = "value", min = 0, max = 127},
        {name = "Pan 5", input = "delta", output = "value", min = 0, max = 127},
        {name = "Pan 6", input = "delta", output = "value", min = 0, max = 127},
        {name = "Pan 7", input = "delta", output = "value", min = 0, max = 127},
        {name = "Pan 8", input = "delta", output = "value", min = 0, max = 127},

        -- Mute buttons
        {name = "Mute 1", input = "button", output = "value", min = 0, max = 1},
        {name = "Mute 2", input = "button", output = "value", min = 0, max = 1},
        {name = "Mute 3", input = "button", output = "value", min = 0, max = 1},
        {name = "Mute 4", input = "button", output = "value", min = 0, max = 1},
        {name = "Mute 5", input = "button", output = "value", min = 0, max = 1},
        {name = "Mute 6", input = "button", output = "value", min = 0, max = 1},
        {name = "Mute 7", input = "button", output = "value", min = 0, max = 1},
        {name = "Mute 8", input = "button", output = "value", min = 0, max = 1},

        -- Solo buttons
        {name = "Solo 1", input = "button", output = "value", min = 0, max = 1},
        {name = "Solo 2", input = "button", output = "value", min = 0, max = 1},
        {name = "Solo 3", input = "button", output = "value", min = 0, max = 1},
        {name = "Solo 4", input = "button", output = "value", min = 0, max = 1},
        {name = "Solo 5", input = "button", output = "value", min = 0, max = 1},
        {name = "Solo 6", input = "button", output = "value", min = 0, max = 1},
        {name = "Solo 7", input = "button", output = "value", min = 0, max = 1},
        {name = "Solo 8", input = "button", output = "value", min = 0, max = 1},

        -- Track select buttons
        {name = "Select 1", input = "button", output = "value", min = 0, max = 1},
        {name = "Select 2", input = "button", output = "value", min = 0, max = 1},
        {name = "Select 3", input = "button", output = "value", min = 0, max = 1},
        {name = "Select 4", input = "button", output = "value", min = 0, max = 1},
        {name = "Select 5", input = "button", output = "value", min = 0, max = 1},
        {name = "Select 6", input = "button", output = "value", min = 0, max = 1},
        {name = "Select 7", input = "button", output = "value", min = 0, max = 1},
        {name = "Select 8", input = "button", output = "value", min = 0, max = 1},

        -- Record arm buttons
        {name = "Arm 1", input = "button", output = "value", min = 0, max = 1},
        {name = "Arm 2", input = "button", output = "value", min = 0, max = 1},
        {name = "Arm 3", input = "button", output = "value", min = 0, max = 1},
        {name = "Arm 4", input = "button", output = "value", min = 0, max = 1},
        {name = "Arm 5", input = "button", output = "value", min = 0, max = 1},
        {name = "Arm 6", input = "button", output = "value", min = 0, max = 1},
        {name = "Arm 7", input = "button", output = "value", min = 0, max = 1},
        {name = "Arm 8", input = "button", output = "value", min = 0, max = 1},

        -- Master volume
        {name = "Master Volume", input = "delta", output = "value", min = 0, max = 127},

        -- Bank navigation
        {name = "Bank Left", input = "button"},
        {name = "Bank Right", input = "button"},

        -- LCD track names (8 fields)
        {name = "Track Name 1", output = "text"},
        {name = "Track Name 2", output = "text"},
        {name = "Track Name 3", output = "text"},
        {name = "Track Name 4", output = "text"},
        {name = "Track Name 5", output = "text"},
        {name = "Track Name 6", output = "text"},
        {name = "Track Name 7", output = "text"},
        {name = "Track Name 8", output = "text"},

        -- LCD volume values
        {name = "Volume Display 1", output = "text"},
        {name = "Volume Display 2", output = "text"},
        {name = "Volume Display 3", output = "text"},
        {name = "Volume Display 4", output = "text"},
        {name = "Volume Display 5", output = "text"},
        {name = "Volume Display 6", output = "text"},
        {name = "Volume Display 7", output = "text"},
        {name = "Volume Display 8", output = "text"},

        -- Meter levels (for visual feedback)
        {name = "Meter 1", output = "value", min = 0, max = 127},
        {name = "Meter 2", output = "value", min = 0, max = 127},
        {name = "Meter 3", output = "value", min = 0, max = 127},
        {name = "Meter 4", output = "value", min = 0, max = 127},
        {name = "Meter 5", output = "value", min = 0, max = 127},
        {name = "Meter 6", output = "value", min = 0, max = 127},
        {name = "Meter 7", output = "value", min = 0, max = 127},
        {name = "Meter 8", output = "value", min = 0, max = 127},
    }

    remote.define_items(items)

    -- Input patterns from bridge
    local inputs = {
        -- Volume encoders (CC 0x30-0x37, relative)
        {pattern = "bf 30 xx", name = "Volume 1", value = "x - 64"},
        {pattern = "bf 31 xx", name = "Volume 2", value = "x - 64"},
        {pattern = "bf 32 xx", name = "Volume 3", value = "x - 64"},
        {pattern = "bf 33 xx", name = "Volume 4", value = "x - 64"},
        {pattern = "bf 34 xx", name = "Volume 5", value = "x - 64"},
        {pattern = "bf 35 xx", name = "Volume 6", value = "x - 64"},
        {pattern = "bf 36 xx", name = "Volume 7", value = "x - 64"},
        {pattern = "bf 37 xx", name = "Volume 8", value = "x - 64"},

        -- Pan encoders (CC 0x38-0x3F, relative)
        {pattern = "bf 38 xx", name = "Pan 1", value = "x - 64"},
        {pattern = "bf 39 xx", name = "Pan 2", value = "x - 64"},
        {pattern = "bf 3a xx", name = "Pan 3", value = "x - 64"},
        {pattern = "bf 3b xx", name = "Pan 4", value = "x - 64"},
        {pattern = "bf 3c xx", name = "Pan 5", value = "x - 64"},
        {pattern = "bf 3d xx", name = "Pan 6", value = "x - 64"},
        {pattern = "bf 3e xx", name = "Pan 7", value = "x - 64"},
        {pattern = "bf 3f xx", name = "Pan 8", value = "x - 64"},

        -- Mute buttons (CC 0x40-0x47)
        {pattern = "bf 40 xx", name = "Mute 1", value = "x"},
        {pattern = "bf 41 xx", name = "Mute 2", value = "x"},
        {pattern = "bf 42 xx", name = "Mute 3", value = "x"},
        {pattern = "bf 43 xx", name = "Mute 4", value = "x"},
        {pattern = "bf 44 xx", name = "Mute 5", value = "x"},
        {pattern = "bf 45 xx", name = "Mute 6", value = "x"},
        {pattern = "bf 46 xx", name = "Mute 7", value = "x"},
        {pattern = "bf 47 xx", name = "Mute 8", value = "x"},

        -- Solo buttons (CC 0x48-0x4F)
        {pattern = "bf 48 xx", name = "Solo 1", value = "x"},
        {pattern = "bf 49 xx", name = "Solo 2", value = "x"},
        {pattern = "bf 4a xx", name = "Solo 3", value = "x"},
        {pattern = "bf 4b xx", name = "Solo 4", value = "x"},
        {pattern = "bf 4c xx", name = "Solo 5", value = "x"},
        {pattern = "bf 4d xx", name = "Solo 6", value = "x"},
        {pattern = "bf 4e xx", name = "Solo 7", value = "x"},
        {pattern = "bf 4f xx", name = "Solo 8", value = "x"},

        -- Select buttons (CC 0x20-0x27)
        {pattern = "bf 20 xx", name = "Select 1", value = "x"},
        {pattern = "bf 21 xx", name = "Select 2", value = "x"},
        {pattern = "bf 22 xx", name = "Select 3", value = "x"},
        {pattern = "bf 23 xx", name = "Select 4", value = "x"},
        {pattern = "bf 24 xx", name = "Select 5", value = "x"},
        {pattern = "bf 25 xx", name = "Select 6", value = "x"},
        {pattern = "bf 26 xx", name = "Select 7", value = "x"},
        {pattern = "bf 27 xx", name = "Select 8", value = "x"},

        -- Arm buttons (CC 0x28-0x2F)
        {pattern = "bf 28 xx", name = "Arm 1", value = "x"},
        {pattern = "bf 29 xx", name = "Arm 2", value = "x"},
        {pattern = "bf 2a xx", name = "Arm 3", value = "x"},
        {pattern = "bf 2b xx", name = "Arm 4", value = "x"},
        {pattern = "bf 2c xx", name = "Arm 5", value = "x"},
        {pattern = "bf 2d xx", name = "Arm 6", value = "x"},
        {pattern = "bf 2e xx", name = "Arm 7", value = "x"},
        {pattern = "bf 2f xx", name = "Arm 8", value = "x"},

        -- Master volume (CC 0x07)
        {pattern = "bf 07 xx", name = "Master Volume", value = "x - 64"},

        -- Bank navigation (CC 0x5F, 0x60)
        {pattern = "bf 5f xx", name = "Bank Left", value = "x"},
        {pattern = "bf 60 xx", name = "Bank Right", value = "x"},
    }

    remote.define_auto_inputs(inputs)

    -- Output patterns to bridge
    local outputs = {
        -- Volume feedback
        {name = "Volume 1", pattern = "bf 30 xx"},
        {name = "Volume 2", pattern = "bf 31 xx"},
        {name = "Volume 3", pattern = "bf 32 xx"},
        {name = "Volume 4", pattern = "bf 33 xx"},
        {name = "Volume 5", pattern = "bf 34 xx"},
        {name = "Volume 6", pattern = "bf 35 xx"},
        {name = "Volume 7", pattern = "bf 36 xx"},
        {name = "Volume 8", pattern = "bf 37 xx"},

        -- Pan feedback
        {name = "Pan 1", pattern = "bf 38 xx"},
        {name = "Pan 2", pattern = "bf 39 xx"},
        {name = "Pan 3", pattern = "bf 3a xx"},
        {name = "Pan 4", pattern = "bf 3b xx"},
        {name = "Pan 5", pattern = "bf 3c xx"},
        {name = "Pan 6", pattern = "bf 3d xx"},
        {name = "Pan 7", pattern = "bf 3e xx"},
        {name = "Pan 8", pattern = "bf 3f xx"},

        -- Mute LED feedback
        {name = "Mute 1", pattern = "bf 40 xx"},
        {name = "Mute 2", pattern = "bf 41 xx"},
        {name = "Mute 3", pattern = "bf 42 xx"},
        {name = "Mute 4", pattern = "bf 43 xx"},
        {name = "Mute 5", pattern = "bf 44 xx"},
        {name = "Mute 6", pattern = "bf 45 xx"},
        {name = "Mute 7", pattern = "bf 46 xx"},
        {name = "Mute 8", pattern = "bf 47 xx"},

        -- Solo LED feedback
        {name = "Solo 1", pattern = "bf 48 xx"},
        {name = "Solo 2", pattern = "bf 49 xx"},
        {name = "Solo 3", pattern = "bf 4a xx"},
        {name = "Solo 4", pattern = "bf 4b xx"},
        {name = "Solo 5", pattern = "bf 4c xx"},
        {name = "Solo 6", pattern = "bf 4d xx"},
        {name = "Solo 7", pattern = "bf 4e xx"},
        {name = "Solo 8", pattern = "bf 4f xx"},

        -- Select LED feedback
        {name = "Select 1", pattern = "bf 20 xx"},
        {name = "Select 2", pattern = "bf 21 xx"},
        {name = "Select 3", pattern = "bf 22 xx"},
        {name = "Select 4", pattern = "bf 23 xx"},
        {name = "Select 5", pattern = "bf 24 xx"},
        {name = "Select 6", pattern = "bf 25 xx"},
        {name = "Select 7", pattern = "bf 26 xx"},
        {name = "Select 8", pattern = "bf 27 xx"},

        -- Arm LED feedback
        {name = "Arm 1", pattern = "bf 28 xx"},
        {name = "Arm 2", pattern = "bf 29 xx"},
        {name = "Arm 3", pattern = "bf 2a xx"},
        {name = "Arm 4", pattern = "bf 2b xx"},
        {name = "Arm 5", pattern = "bf 2c xx"},
        {name = "Arm 6", pattern = "bf 2d xx"},
        {name = "Arm 7", pattern = "bf 2e xx"},
        {name = "Arm 8", pattern = "bf 2f xx"},

        -- Master volume feedback
        {name = "Master Volume", pattern = "bf 07 xx"},
    }

    remote.define_auto_outputs(outputs)
end

function remote_on_auto_input(item_index)
    if item_index > 0 then
        g_last_input_time = remote.get_time_ms()
    end
end

function remote_set_state(changed_items)
    local changed = get_changed_indices(changed_items)

    for _, item_index in ipairs(changed) do
        local item_name = remote.get_item_name(item_index)
        if item_name then
            local track_index = string.match(item_name, "^Track Name (%d+)$")
            if track_index then
                local text = remote.get_item_text_value(item_index) or ""
                text = string.format("%-8.8s", text)
                local idx = tonumber(track_index)
                if text ~= g_lcd_state[idx].text then
                    g_lcd_state[idx].text = text
                    g_lcd_state[idx].changed = true
                end
            else
                local volume_index = string.match(item_name, "^Volume Display (%d+)$")
                if volume_index then
                    local text = remote.get_item_text_value(item_index) or ""
                    text = string.format("%-8.8s", text)
                    local idx = tonumber(volume_index) + 8
                    if text ~= g_lcd_state[idx].text then
                        g_lcd_state[idx].text = text
                        g_lcd_state[idx].changed = true
                    end
                else
                    local meter_index = string.match(item_name, "^Meter (%d+)$")
                    if meter_index then
                        local value = remote.get_item_value(item_index)
                        g_track_meters[tonumber(meter_index)] = value or 0
                    end
                end
            end
        end
    end
end

function remote_deliver_midi(max_bytes, port)
    local events = {}

    -- Send track name updates via SysEx
    for i = 1, 8 do
        if g_lcd_state[i].changed then
            local sysex_str = string.format("f0 00 11 22 03 %02x %02x", MSG_MIXER_NAME, i - 1)
            for j = 1, 8 do
                local char = string.byte(g_lcd_state[i].text, j) or 0x20
                sysex_str = sysex_str .. string.format(" %02x", char)
            end
            sysex_str = sysex_str .. " f7"
            table.insert(events, remote.make_midi(sysex_str))
            g_lcd_state[i].changed = false
        end
    end

    -- Send volume display updates
    for i = 9, 16 do
        if g_lcd_state[i].changed then
            local channel = i - 9
            local sysex_str = string.format("f0 00 11 22 03 %02x %02x", MSG_MIXER_VOLUME, channel)
            for j = 1, 8 do
                local char = string.byte(g_lcd_state[i].text, j) or 0x20
                sysex_str = sysex_str .. string.format(" %02x", char)
            end
            sysex_str = sysex_str .. " f7"
            table.insert(events, remote.make_midi(sysex_str))
            g_lcd_state[i].changed = false
        end
    end

    -- Send meter updates for visual feedback
    for i = 1, 8 do
        if g_track_meters[i] > 0 then
            local sysex_str = string.format("f0 00 11 22 03 %02x %02x %02x f7", MSG_MIXER_LEVEL, i - 1, g_track_meters[i])
            table.insert(events, remote.make_midi(sysex_str))
        end
    end

    return events
end

function remote_probe(manufacturer, model, prober)
    -- Dynamic prober: find our specific port by name and verify with ping/pong
    local port_name = "OpenPush Mixer"
    local request = "f0 00 11 22 03 70 f7"
    local response = "f0 00 11 22 03 71 ?? f7"

    -- Find input port (we receive from this = Reason's output)
    local in_port = nil
    for i = 1, prober:num_midi_outputs() do
        local name = prober:midi_output_name(i)
        if name and string.find(name, port_name) then
            in_port = i
            break
        end
    end

    -- Find output port (we send to this = Reason's input)
    local out_port = nil
    for i = 1, prober:num_midi_inputs() do
        local name = prober:midi_input_name(i)
        if name and string.find(name, port_name) then
            out_port = i
            break
        end
    end

    if not in_port or not out_port then
        return nil  -- Port not found
    end

    -- Send probe and check response
    prober:send_midi(out_port, remote.make_midi(request))
    local received = prober:receive_midi(in_port, 200)  -- 200ms timeout

    if received and remote.match_midi(response, received) then
        return {
            in_ports = {in_port},
            out_ports = {out_port}
        }
    end

    return nil
end

function remote_prepare_for_use()
    return {}
end

function remote_release_from_use()
    return {}
end
