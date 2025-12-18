# Lua De-obfuscation Guide

Techniques for understanding obfuscated PusheR Lua codecs.

## Obfuscation Type

PusheR uses **variable name randomization** - the simplest form of obfuscation. The code structure, function names, and MIDI patterns remain intact.

## Key Analysis Techniques

### 1. Item Index Mapping

The obfuscated variables at lines 278-289 are **item indices**:

```lua
heffrrfapsb=81      -- Item index 81 (LCD1 in items table)
qoryuhuealyx=12     -- Item index 12
gxiioixmyqlq=83     -- Item index 83
sdcfukgaxofp=4      -- Item index 4 (pot4)
ntdvfklsymqf=5      -- Item index 5 (pot5)
lhfvxcswkjpu=6      -- Item index 6 (pot6)
iywavcwwbwth=85     -- Item index 85
saqackdvrfuh=8      -- Item index 8
vmscdstiggun=9      -- Item index 9
yaogvglwectvc=13    -- Item index 13
mjjuhygll=84        -- Item index 84
```

Cross-reference with the `items` table in `remote_init()`:
- Index 1-41: pots (pot1-pot41)
- Index 42-82: buttons (button1-button40)
- Index 83-93: LCD1-LCD11
- Index 94: Keyboard
- Index 95: pitchbend

### 2. LCD State Variables Pattern

The code uses pairs of variables for LCD state tracking:

```lua
-- Current text     -- Previous text (for change detection)
uthfxneinxc        fivaiblghpvwxaukuqydp    -- LCD field 1
oedvsyurkjpp       vijbeeigughaeadrqqvnop   -- LCD field 2
aujddrqmiclo       hehdtuqwkebilxqmmewkpm   -- LCD field 3
degynwpdbuhk       otkritucheaioobqwuaenv   -- LCD field 4
qiruojrqqjyc       qgcweavqetaaslakyabgkf   -- LCD field 5
sqxiaverbbph       ihhdgwlawcvunrrpjfmllk   -- LCD field 6
tfvajhhhlvct       dqcdsglenwmuhfvbciilju   -- LCD field 7
vlketxcwnxot       vdaylpjuoipmilluamjsvv   -- LCD field 8
```

Each is initialized to 16-space string, previous set to "#" to force initial update.

### 3. SysEx Builder Functions

The functions at lines 412-543 build SysEx messages for LCD lines:

```lua
-- Pattern: F0 11 22 06 [line] [16 chars] F7
local function ayhrqcyqttupgrysoyuqp(text)  -- LCD line 1 (0x01)
    local msg = remote.make_midi("f0 11 22 06 01")
    -- ... copy 16 chars ...
    return msg
end

local function nwqfulvvtglgdbfcononbv(text)  -- LCD line 2 (0x02)
    local msg = remote.make_midi("f0 11 22 06 02")
    -- ...
end
```

### 4. MIDI Pattern Analysis

The `inputs` and `outputs` tables are NOT obfuscated:

```lua
-- Input patterns (from PusheR app to Reason)
{pattern = "bf 50 xx", name = "Play", value = "x"},
{pattern = "bf 51 xx", name = "Stop", value = "x"},
{pattern = "bf 52 xx", name = "Record", value = "x"},

-- Encoder patterns with sign handling
{pattern = "bf 03 <???y>x", name = "pot3"},  -- y=sign bit, x=value
{pattern = "bf 16 xx", name = "Tempo", value = "x - 64"},  -- relative
```

### 5. remote_set_state() Analysis

This function handles feedback FROM Reason. Trace by item index:

```lua
function remote_set_state(changed_items)
    for i, item_index in ipairs(changed_items) do
        if item_index == heffrrfapsb then  -- 81 = LCD1
            -- Get text value and format to 16 chars
            pwtnmdxp = remote.get_item_text_value(item_index)
            uthfxneinxc = string.format("%-16.16s", pwtnmdxp)
        elseif item_index == qoryuhuealyx then  -- 12 = pot12?
            -- ...
        end
    end
end
```

### 6. remote_deliver_midi() Analysis

This sends MIDI TO the PusheR app (LCD updates):

```lua
function remote_deliver_midi()
    local events = {}

    -- Check if LCD1 changed
    if fivaiblghpvwxaukuqydp ~= uthfxneinxc then  -- prev != current
        local sysex = ayhrqcyqttupgrysoyuqp(uthfxneinxc)  -- build msg
        table.insert(events, sysex)
        fivaiblghpvwxaukuqydp = uthfxneinxc  -- update prev
    elseif ...  -- check LCD2, LCD3, etc.

    return events
end
```

## Practical De-obfuscation Steps

### Step 1: Map Item Indices
Count through the `items` table to find what index 81, 84, etc. refer to.

### Step 2: Trace Variable Usage
Search for where each obfuscated variable is used to understand its purpose.

### Step 3: Use Print Statements
If you can run the codec, add `print()` calls to trace execution:
```lua
print("Item " .. item_index .. " = " .. remote.get_item_name(item_index))
```

### Step 4: Compare with Remotemap
The `.remotemap` file shows what each item DOES in Reason - cross-reference with Lua.

## Runtime Analysis

### MIDI Monitoring
Use a MIDI monitor to capture traffic between PusheR and Reason:
- **macOS**: MIDI Monitor app
- **Windows**: MIDI-OX

### What to capture:
1. SysEx messages (LCD text updates)
2. CC messages (button/encoder values)
3. Note messages (pad triggers)

### Example capture:
```
PusheR → Reason: BF 50 7F  (Play button pressed, CC 80 value 127)
Reason → PusheR: BF 50 01  (Play LED on, CC 80 value 1)
PusheR → Reason: F0 11 22 06 01 [16 bytes] F7  (LCD line 1 text)
```

## Key Findings Summary

| Obfuscated | Purpose | Evidence |
|------------|---------|----------|
| `heffrrfapsb=81` | LCD1 item index | Used in remote_set_state for text |
| `mjjuhygll=84` | LCD4 item index | Document name display |
| `uthfxneinxc` | LCD1 current text | 16-char formatted string |
| `fivaiblghpvwxaukuqydp` | LCD1 previous text | Change detection |
| `dbmqpyafvyhollrks` | Last input timestamp | For feedback timeout |
| `ayhrqcyqttupgrysoyuqp()` | LCD1 SysEx builder | Creates F0 11 22 06 01... |

## Conclusion

The obfuscation is shallow - focus on:
1. **Remotemap files** - These tell you what each control does
2. **MIDI patterns** - These are fully readable in inputs/outputs
3. **Item indices** - Count through items table to decode variable names
4. **Runtime tracing** - MIDI monitoring reveals actual protocol
