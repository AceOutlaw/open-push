# OpenPush Reason Integration Guide

## Overview

This guide explains how OpenPush integrates with Reason via the **Reason Remote SDK**. It covers the architecture, the specific MIDI mappings required, and how to implement advanced bidirectional communication (SysEx) using Lua codecs.

## Architecture

The integration relies on a "Bridge" architecture because Reason cannot natively talk to Push's complex display and LED matrix.

```
┌─────────────────┐      USB MIDI     ┌─────────────────┐    Virtual MIDI    ┌─────────────────┐
│  Push Hardware  │ ←────────────→    │   Python App    │ ←──────────────→   │  Reason + Lua   │
│  (User Port)    │                   │   (bridge.py)   │    (IAC Bus)       │    Codecs       │
└─────────────────┘                   └─────────────────┘                    └─────────────────┘
```

1.  **Push Hardware:** Sends native MIDI (CCs, Notes, SysEx) to the Python App.
2.  **Python App:**
    *   Reads Push input.
    *   Translates it to a "Reason-compatible" format (matching the Lua codecs).
    *   Sends to Reason via Virtual MIDI Ports.
    *   Receives feedback from Reason (LED states, text) and updates the Push hardware.
3.  **Reason + Lua:**
    *   Receives MIDI from the Python App.
    *   Maps it to Reason functions (Play, Stop, Mixer, Devices).
    *   Sends feedback back to the Python App.

---

## 1. Establishing Communication (The Basics)

For buttons and knobs to work, the Python App and the Lua Codec must agree on **MIDI CC numbers**.

**Current Issue:** The initial implementation of `bridge.py` used arbitrary CC numbers (e.g., 80/0x50 for Play), while the Lua codec expects the *native* Push CC numbers (e.g., 85/0x55 for Play). **These must align.**

### Correct MIDI Mapping Table (Standardized)

We standardize on using the **Native Push 1 CCs** passed through on **MIDI Channel 16 (0x0F)** (which is `0xBF` in status bytes) to avoid conflicts with Note data.

| Function | Push Native CC | Hex (Ch 16) | Python `bridge.py` Value | Lua Pattern |
| :--- | :--- | :--- | :--- | :--- |
| **Play** | 85 | `BF 55` | `0x55` | `bf 55 xx` |
| **Stop** | 29 | `BF 1D` | `0x1D` | `bf 1d xx` |
| **Record** | 86 | `BF 56` | `0x56` | `bf 56 xx` |
| **Loop** | 55 | `BF 37` | `0x37` | `bf 37 xx` |
| **Metronome** | 9 | `BF 09` | `0x09` | `bf 09 xx` |
| **Encoder 1** | 71 | `BF 47` | `0x47` | `bf 47 xx` |
| **...Encoder 8**| 78 | `BF 4E` | `0x4E` | `bf 4e xx` |

### Required Code Changes

**In `src/open_push/reason/bridge.py`:**
Update the constants to match the native hardware:
```python
CC_PLAY = 0x55      # Was 0x50
CC_STOP = 0x1D      # Was 0x51
CC_RECORD = 0x56    # Was 0x52
# ... and so on
```

**In `src/open_push/reason/codecs/OpenPush Transport.lua`:**
Ensure patterns match (which they currently do):
```lua
{pattern="bf 55 xx", name="Play", value="x"}, -- Matches CC 85
```

---

## 2. Advanced Communication (SysEx & Display)

Simple MIDI CCs are not enough for sending text (track names, device parameters) to the Push display. For this, we use **System Exclusive (SysEx)** messages.

### The Protocol (`src/open_push/reason/protocol.py`)

We define a custom SysEx header for Reason communication: `F0 00 11 22 ...`

**Example Message (Python -> Reason):**
*   **Touch Encoder 1:** `F0 00 11 22 02 21 00 7F F7`
    *   `00 11 22`: Header
    *   `02`: Device Port
    *   `21`: Encoder Touch Event
    *   `00`: Encoder Index 0
    *   `7F`: Value (Touched)

**Example Message (Reason -> Python):**
*   **Display Text:** `F0 00 11 22 01 40 01 [ASCII Data] F7`
    *   `01`: Transport Port
    *   `40`: Display Line Message
    *   `01`: Line 1
    *   `...`: Text bytes

### Implementing SysEx in Lua

To handle SysEx in Lua, you must implement the `remote_process_midi` function. This function intercepts incoming MIDI messages before they are processed by the auto-inputs.

**File: `src/open_push/reason/codecs/OpenPush Transport.lua`**

```lua
-- Global variables to store state
g_last_text = ""

function remote_process_midi(event)
    -- 1. Match our custom SysEx header: F0 00 11 22
    -- The '?' wildcard matches any byte, captured in variables x, y, z...
    -- match_midi returns a table {x=..., y=...} if successful, or nil.
    
    -- Example: Match a Display Line message (Type 0x40)
    -- Pattern: F0 00 11 22 [Port] [Type=40] [Line] [Text...] F7
    
    -- NOTE: match_midi has limitations on variable length data.
    -- For simple commands like "Ping" or specific fixed-length updates, it works well.
    local ret = remote.match_midi("f0 00 11 22 ?x ?y ?z f7", event)
    
    if ret ~= nil then
        -- Handle the message based on 'y' (Message Type)
        local port = ret.x
        local msg_type = ret.y
        local data = ret.z
        
        -- Return true to indicate we handled this event
        return true
    end

    -- Return false to let Reason handle it as a normal MIDI event (CC/Note)
    return false
end
```

### Sending SysEx from Lua to Python

To send complex data (like text updates) from Reason *back* to the Python app, you use `remote.make_midi` inside `remote_deliver_midi`.

**Scenario:** sending the name of the currently selected track.

1.  **Define the Item:**
    ```lua
    {name="TrackName", input="noinput", output="text"},
    ```
2.  **Track State Changes:**
    ```lua
    function remote_set_state(changed_items)
        for i, item_index in ipairs(changed_items) do
             if item_index == g_track_name_index then
                 -- Store the new text value
                 g_current_track_name = remote.get_item_text_value(item_index)
                 g_update_needed = true
             end
        end
    end
    ```
3.  **Deliver MIDI:**
    ```lua
    function remote_deliver_midi()
        local events = {}
        
        if g_update_needed then
             -- Construct SysEx: F0 00 11 22 [Port] [Type=Display] [Line] [Text...] F7
             -- Note: You have to manually construct the byte array
             local sysex = {0xF0, 0x00, 0x11, 0x22, 0x01, 0x40, 0x01} -- Header
             
             -- Append text bytes
             for i = 1, string.len(g_current_track_name) do
                 table.insert(sysex, string.byte(g_current_track_name, i))
             end
             
             table.insert(sysex, 0xF7) -- Footer
             
             -- Create the Reason MIDI event
             local event = remote.make_midi(sysex)
             table.insert(events, event)
             
             g_update_needed = false
        end
        
        return events
    end
    ```

## 3. Debugging Tips

*   **Lua `remote.trace`:** You can print debug info to the Reason console (Window > Show Remote Override Mapping > (Right Click) > Copy MIDI Control Surface Log... wait, no, straightforward logging isn't easy).
*   **Better Debugging:** Use the Python App as your debugger. It prints everything it receives.
*   **"Context Compression":** If you are sending too much data (e.g., updating the display 60 times a second), Reason or the MIDI driver might drop bytes.
    *   *Solution:* Only send updates in `remote_deliver_midi` when `remote_set_state` indicates a change.
    *   *Solution:* Use `g_update_needed` flags rather than rebuilding packets constantly.

## Checklist for a Working Script

1.  [ ] **CC Alignment:** Verify `bridge.py` constants match `OpenPush *.lua` patterns.
2.  [ ] **Virtual Ports:** Ensure 3 pairs of IAC/Virtual ports are active.
3.  [ ] **Auto-Inputs:** Ensure `remote.define_auto_inputs` covers all controls you want to control Reason with.
4.  [ ] **Auto-Outputs:** Ensure `remote.define_auto_outputs` covers all LEDs you want Reason to light up.
5.  [ ] **SysEx (Optional):** Implement `remote_process_midi` only if you need advanced non-CC features. Start with CCs first!