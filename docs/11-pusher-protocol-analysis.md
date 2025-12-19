# PusheR Protocol & Implementation Analysis

This document analyzes the "PusheR" implementation found in `reference files/Remote/PusheR`, which provides a mature reference for interfacing the Ableton Push with Reason using a custom bridge.

## 1. Architecture Overview

PusheR uses a similar architecture to OpenPush:
1.  **Reason Codec:** Sends custom SysEx/CC messages to a virtual MIDI port.
2.  **Bridge/Translator:** (Presumably Java-based in the original, Python in OpenPush) Receives these messages and translates them for the hardware.

The Codec is heavily obfuscated (variable names like `rxfcccnofueq`, `heffrrfapsb`), but the logic is clear.

## 2. Custom SysEx Protocol

PusheR uses a custom SysEx header: `F0 11 22 06`.

### Message Types
Based on the `remote_deliver_midi` function, the protocol defines several message types (byte 5):

*   `0x01`: LCD Line 1 Update
*   `0x02`: LCD Line 2 Update
*   `0x03`: LCD Line 3 Update
*   `0x04`: LCD Line 4 Update
*   ...
*   `0x0B`: LCD Line 11? (Likely hidden or state data)
*   `0x0C`: LCD Line 12?

**Format:** `F0 11 22 06 [MsgType] [TextData...] F7`

### Helper Functions
The script defines individual helper functions for each message type (e.g., `ayhrqcyqttupgrysoyuqp` for Type 1, `nwqfulvvtglgdbfcononbv` for Type 2). These functions:
1.  Accept a string.
2.  Wrap it in the custom SysEx header.
3.  Append the ASCII bytes.
4.  Append `F7`.

## 3. Display Logic & Optimization

### Fixed-Width Fields
The script hardcodes display fields to **16 characters**:
```lua
uthfxneinxc = string.format("%-16.16s", " ") -- Pad/Truncate to 16 chars
```
This aligns perfectly with a strategy of dividing the 68-character Push line into 4 segments of 17 (or 16+1 spacer).

### Dirty Flag Checking
Every display item has a corresponding state tracking variable (e.g., `fivaiblghpvwxaukuqydp`).
In `remote_deliver_midi`, it checks:
```lua
if fivaiblghpvwxaukuqydp ~= mlfosbar then
    -- Generate SysEx
    table.insert(jrnrgqpsmq, fmvlvagwt)
    -- Update cache
    fivaiblghpvwxaukuqydp = mlfosbar
end
```
This ensures **only changed lines are sent**, preventing bus flooding.

### "Popup" Value Logic (The Missing Piece)
PusheR implements the "popup" behavior using a timer:
```lua
-- In remote_set_state
if (urkrof - dbmqpyafvyhollrks) < 1000 then -- If input within 1 second
    -- Get short name and value
    local mscdrnydeodtf = remote.get_item_short_name_and_value(jdjhorqrbckvmklnt)
    if string.len(mscdrnydeodtf) > 0 then
        oupaaqfolooqmdruuw = true
        -- Overwrite the display string variable
        aujddrqmiclo = string.format("%-16.16s", mscdrnydeodtf)
    end
end
```
It tracks `remote.get_time_ms()` to decide whether to show the persistent "Track Name" or the momentary "Volume: 100" value.

## 4. MIDI Mapping Strategy

### Inputs (Hardware -> Reason)
*   **Encoders:** Delta values are mapped to inputs `pot2`..`pot5` etc.
    *   Pattern: `f0 36 ... <???y>x` suggests it might be reading SysEx directly or a very specific CC pattern.
    *   Wait, looking closely: `{pattern="f0 36 32 32 32 32 00 <???y>x f7", name="pot2", value="x*(1-2*y)"}`
    *   This implies the bridge sends **SysEx** back to Reason for encoder movements! This is unusual but allows higher resolution or specific encoding.
*   **Buttons:** Mapped to `bf 2a ...` (CC 42+).
*   **Transport:** Standard CCs.

### Outputs (Reason -> Hardware)
*   Outputs are defined for `potX` and `buttonX`.
*   Feedback is sent via CCs (`bf 02 ...`).

## 5. Map File Insights

The `.remotemap` reveals the functional scope:
*   **Transport:** Play, Stop, Record, Loop, Fast Forward, Rewind.
*   **Navigation:** Target Next/Prev Track, Select Next/Prev Patch.
*   **Editing:** Undo, Redo, Quantize, New Overdub.
*   **LCD Mapping:** `Target Track Name` and `Document Name` are mapped to LCD fields.

## 6. Key Takeaways for OpenPush

1.  **State Caching is Mandatory:** You must track the previous string state in Lua to avoid flooding the bridge.
2.  **Fixed Widths:** Formatting text to 16 chars in Lua simplifies the Python bridge's job (it just places the chunk).
3.  **Timer-Based Popups:** The "touched" value display is handled entirely in Lua using `remote.get_time_ms()`.
4.  **Custom SysEx is Standard:** Both projects use a custom header to namespace their communication.

## 7. Decoded Variable Map (Partial)
*   `remote_deliver_midi`: Main output loop.
*   `remote_set_state`: State update callback.
*   `g_last_input_time`: `dbmqpyafvyhollrks`
*   `g_last_input_item`: `jdjhorqrbckvmklnt`
*   `LCD1_Text_Cache`: `fivaiblghpvwxaukuqydp`
