--[[
OpenPush Transport Codec for Reason
====================================

Handles transport controls, tempo, and global navigation.

Communication with the Python bridge uses custom SysEx:
  F0 00 11 22 01 [msg_type] [data...] F7

Port ID: 0x01 (Transport)

Install: Copy to Reason's Codecs folder:
  macOS: /Library/Application Support/Propellerhead Software/Remote/Codecs/
  Windows: %PROGRAMDATA%\Propellerhead Software\Remote\Codecs\
]]--

-- Item name constants
g_lcd_names = {}
for i = 1, 16 do
    g_lcd_names[i] = string.format("LCD%d", i)
end

-- Message types (must match protocol.py MessageType)
MSG_TRANSPORT_PLAY = 0x10
MSG_TRANSPORT_STOP = 0x11
MSG_TRANSPORT_RECORD = 0x12
MSG_TRANSPORT_REWIND = 0x13
MSG_TRANSPORT_FORWARD = 0x14
MSG_TRANSPORT_LOOP = 0x15
MSG_TRANSPORT_TEMPO = 0x16
MSG_TRANSPORT_METRONOME = 0x17
MSG_DISPLAY_LINE = 0x40

-- SysEx header for OpenPush protocol
SYSEX_HEADER = "f0 00 11 22 01"

-- State tracking
g_last_input_time = 0
g_last_input_item = 0
g_lcd_state = {}

for i = 1, 16 do
    g_lcd_state[i] = {text = string.rep(" ", 16), changed = false}
end

------------------------------------------------------------------------
-- REMOTE SDK CALLBACKS
------------------------------------------------------------------------

function remote_init(manufacturer, model)
    -- Define all control surface items
    local items = {
        -- Transport controls
        {name = "Play", input = "button", output = "value", min = 0, max = 1},
        {name = "Stop", input = "button", output = "value", min = 0, max = 1},
        {name = "Record", input = "button", output = "value", min = 0, max = 1},
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

        -- Keyboard input (for pads)
        {name = "Keyboard", input = "keyboard"},

        -- LCD display fields (16 chars each)
        {name = "LCD1", output = "text"},
        {name = "LCD2", output = "text"},
        {name = "LCD3", output = "text"},
        {name = "LCD4", output = "text"},
        {name = "LCD5", output = "text"},
        {name = "LCD6", output = "text"},
        {name = "LCD7", output = "text"},
        {name = "LCD8", output = "text"},
        {name = "LCD9", output = "text"},
        {name = "LCD10", output = "text"},
        {name = "LCD11", output = "text"},
        {name = "LCD12", output = "text"},
        {name = "LCD13", output = "text"},
        {name = "LCD14", output = "text"},
        {name = "LCD15", output = "text"},
        {name = "LCD16", output = "text"},
    }

    remote.define_items(items)

    -- Define input patterns (MIDI from bridge)
    -- Using channel 16 (0xBF for CC, 0x9F/0x8F for notes)
    local inputs = {
        -- Transport buttons (CC 0x50-0x57)
        {pattern = "bf 50 xx", name = "Play", value = "x"},
        {pattern = "bf 51 xx", name = "Stop", value = "x"},
        {pattern = "bf 52 xx", name = "Record", value = "x"},
        {pattern = "bf 53 xx", name = "Rewind", value = "x"},
        {pattern = "bf 54 xx", name = "Forward", value = "x"},
        {pattern = "bf 55 xx", name = "Loop", value = "x"},
        {pattern = "bf 57 xx", name = "Metronome", value = "x"},

        -- Tempo encoder (CC 0x16, relative)
        {pattern = "bf 16 xx", name = "Tempo", value = "x - 64"},

        -- Navigation (CC 0x60-0x63)
        {pattern = "bf 60 xx", name = "NavigateUp", value = "x"},
        {pattern = "bf 61 xx", name = "NavigateDown", value = "x"},
        {pattern = "bf 62 xx", name = "NavigateLeft", value = "x"},
        {pattern = "bf 63 xx", name = "NavigateRight", value = "x"},

        -- Browser controls (CC 0x64-0x65)
        {pattern = "bf 64 xx", name = "BrowserSelect", value = "x"},
        {pattern = "bf 65 xx", name = "BrowserBack", value = "x"},

        -- Keyboard (notes on channel 16)
        {pattern = "<100x>f yy zz", name = "Keyboard"},
    }

    remote.define_auto_inputs(inputs)

    -- Define output patterns (MIDI to bridge)
    local outputs = {
        -- Transport LED feedback
        {name = "Play", pattern = "bf 50 xx"},
        {name = "Stop", pattern = "bf 51 xx"},
        {name = "Record", pattern = "bf 52 xx"},
        {name = "Loop", pattern = "bf 55 xx"},
        {name = "Metronome", pattern = "bf 57 xx"},

        -- Tempo display
        {name = "Tempo", pattern = "bf 16 xx"},
    }

    remote.define_auto_outputs(outputs)
end

function remote_on_auto_input(item_index)
    -- Track timing for input handling
    if item_index > 0 then
        g_last_input_time = remote.get_time_ms()
        g_last_input_item = item_index
    end
end

function remote_set_state(changed_items)
    -- Handle LCD text updates via SysEx
    for i = 1, 16 do
        local lcd_name = g_lcd_names[i]
        if changed_items[lcd_name] then
            local text = remote.get_item_text_value(remote.get_item_index(lcd_name))
            text = string.format("%-16.16s", text or "")

            if text ~= g_lcd_state[i].text then
                g_lcd_state[i].text = text
                g_lcd_state[i].changed = true
            end
        end
    end
end

function remote_deliver_midi(max_bytes, port)
    -- Send any pending LCD updates as SysEx
    local events = {}

    for i = 1, 16 do
        if g_lcd_state[i].changed then
            -- Build SysEx: F0 00 11 22 01 40 [field] [16 chars] F7
            local sysex = {0xf0, 0x00, 0x11, 0x22, 0x01, MSG_DISPLAY_LINE, i}

            for j = 1, 16 do
                local char = string.byte(g_lcd_state[i].text, j) or 0x20
                table.insert(sysex, char)
            end

            table.insert(sysex, 0xf7)
            table.insert(events, remote.make_midi(table.unpack(sysex)))

            g_lcd_state[i].changed = false
        end
    end

    return events
end

function remote_probe(manufacturer, model, prober)
    -- Auto-detection: send identity request, check for response
    -- For now, just return false (manual setup required)
    return false
end

function remote_prepare_for_use()
    -- Called when Reason is ready to use this surface
end

function remote_release_from_use()
    -- Called when disconnecting
end
