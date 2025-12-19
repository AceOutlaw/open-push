# Reason Remote Knowledge Base

This document consolidates findings from the official Reason Remote SDK documentation, Developer Guides, and analysis of reference implementations (Novation Launchkey, PusheR, Nektar Pacer). It serves as the "source of truth" for OpenPush development.

## 1. Transport Control Implementation (The "Play/Stop" Pattern)

### The Problem
Simply mapping a button to "Play" often results in inconsistent behavior (e.g., it toggles Play/Pause but doesn't return to zero on Stop, or the LED doesn't update correctly).

### The Solution: "Toggle vs. Return to Zero" Logic
Official implementations (like Novation's) use specific logic in `remote_process_midi` to handle this, rather than relying solely on auto-inputs.

**Correct Implementation Pattern:**

1.  **Play Button (Pressed):**
    *   If `Shift` is OFF: Send `127` to the **Play** item. This toggles Play/Pause.
    *   If `Shift` is ON: Send `127` to the **Stop** item. This performs "Return to Zero" (Stop twice).

2.  **Stop Button (Pressed):**
    *   Send `127` to the **Stop** item.

**Lua Code Example:**
```lua
if event[1] == 0xB0 and event[2] == CC_PLAY then
    if shift_status == 1 then
        -- Shift+Play = STOP (Return to Zero)
        local msg = {time_stamp=event.time_stamp, item=g_stop_item_index, value=event[3]}
        remote.handle_input(msg)
    else
        -- Play = Toggle Play/Pause
        local msg = {time_stamp=event.time_stamp, item=g_play_item_index, value=event[3]}
        remote.handle_input(msg)
    end
    return true -- We handled it manually
end
```

**Why Auto-Input Fails Here:**
Auto-input simply maps `CC -> Item`. It cannot handle the conditional logic of "If Shift is held, do X instead of Y".

## 2. Remote SDK Limitations & Workarounds

### What Remote SDK CAN Do
*   Control Transport (Play, Stop, Loop, Click, Tempo).
*   Control Device Parameters (Filter Freq, Volume, Pan).
*   Select Tracks (Next/Prev).
*   Select Patches (Next/Prev).
*   Undo/Redo (Document scope).

### What Remote SDK CANNOT Do (Critical)
*   **Create New Tracks:** There is no Remotable Item for "Create Audio Track" or "Create Instrument".
*   **Save Project:** No access to "File > Save".
*   **Delete Tracks:** No access to "Edit > Delete Track".
*   **Open/Close Browser:** No direct control over the Browser window visibility (only navigation within it).

### The Workaround: OS-Level Keystrokes
Reference implementations like **PusheR** solve this by sending a "Macro" MIDI message to the Bridge software, which then triggers an OS keystroke.

*   **Logic:** Push Button -> Lua (sends CC 87) -> Python Bridge (detects CC 87) -> `pyautogui.hotkey('command', 't')` -> Reason (Create Track).

## 3. Feedback & LED State

### The "Auto-Output" Trap
`remote.define_auto_outputs()` is great for simple feedback, but often fails for complex states (like blinking LEDs or "dim" states).

### Correct Pattern: `remote_deliver_midi()`
For robust feedback, you must generate MIDI messages manually in the `remote_deliver_midi()` callback.

1.  **Check State:** `remote.is_item_enabled(index)` tells you if a track/device is selected.
2.  **Get Value:** `remote.get_item_value(index)` gives the current parameter value.
3.  **Generate Message:** `table.insert(events, remote.make_midi("..."))` sends the update.

**Example (Play LED):**
```lua
-- In remote_deliver_midi
if remote.is_item_enabled(g_play_index) then
    local val = remote.get_item_value(g_play_index)
    local velocity = (val > 0) and 127 or 0 -- 127=Green, 0=Off
    -- Send Note/CC to hardware
end
```

## 4. Display "Popups" (Event-Driven Text)

### The Challenge
Reason only sends text updates when the *target* changes (e.g., you select a new track). It does **not** automatically send the *value* of a parameter (e.g., "-3.5 dB") as text when you turn a knob.

### The Solution: Timer-Based Overrides
Implementations like **PusheR** and **Novation** use Lua's `remote.get_time_ms()` to implement a temporary "popup".

1.  **Detect Change:** In `remote_set_state()`, detect if a specific item (e.g., Volume Fader) changed value.
2.  **Set Popup:** Store the value string (e.g., "Vol: -3.5") in a variable and set a timer (e.g., `now + 1000ms`).
3.  **Render Loop:** In `remote_deliver_midi()`, check the timer.
    *   **If Timer Active:** Send the Popup string.
    *   **If Timer Expired:** Send the Default string (Track Name).

## 5. Summary of Required Architecture

To fully control Reason with Push, we need:

1.  **Lua Codec:** Handles the "Business Logic" (Shift states, Popups, Timers).
2.  **Python Bridge:** Handles the "Hardware Abstraction" (Rendering text to pixels, handling colors, Keystrokes).
3.  **Custom Protocol:** A dedicated SysEx language (e.g., `F0 00 11 22...`) for high-bandwidth data like text, separate from standard MIDI CCs.
