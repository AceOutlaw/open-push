# Radio Button & Advanced State Implementation Guide

This guide is based on community knowledge (Pooh Bear's tutorials) regarding advanced Reason Remote scripting. It focuses on implementing "Radio Button" behavior (mutually exclusive buttons) and handling the feedback loop between Reason's internal state (mouse clicks) and hardware controllers.

## 1. The Challenge: Mutually Exclusive Buttons

By default, Reason's Remote protocol treats buttons as independent toggles or momentaries. If you have a set of buttons (e.g., "Select Track 1-8") where only one should be active at a time, you must implement "Radio Button" logic manually in Lua.

### The Logic
1.  **Detect Press:** When a button is pressed (`value > 0`).
2.  **Turn Off Others:** Loop through all *other* buttons in the group and explicitly send a `0` (off) value to them.
3.  **Turn On Self:** Ensure the pressed button remains `1` (on).

## 2. Handling Input Sources (Mouse vs. Controller)

A critical complexity in Remote scripting is distinguishing between:
*   **Controller Input:** User presses a physical button.
*   **Mouse Input:** User clicks a button in the Reason Rack (GUI).

### The Feedback Loop Problem
When you click a button in the GUI:
1.  Reason updates the device state.
2.  Reason calls `remote_set_state()` to tell the codec "Hey, this item changed!".
3.  Your codec might try to send MIDI back to the controller to update LEDs.
4.  If not careful, this can trigger a loop where the codec thinks the controller sent a new message.

### Solution: The "Loop Back" Trick
To handle GUI clicks effectively (e.g., making a GUI click trigger the Radio Button logic in Lua), some advanced scripts use a **MIDI Loopback**.

1.  **Detect GUI Change:** In `remote_set_state()`, detect that a button changed value.
2.  **Send Fake MIDI:** Instead of just updating an internal variable, send a specific MIDI message (e.g., on Channel 15) *out* to a virtual loopback port.
3.  **Receive Fake MIDI:** The script receives this message in `remote_process_midi()`.
4.  **Process Logic:** The script treats it like a physical button press, running the same Radio Button logic to turn off neighbors.

*Note: For OpenPush, we might not need the full loopback if we handle state centrally in Python, but it's a powerful pattern for pure Lua codecs.*

## 3. Global Pages & "Shift" States

The transcript highlights using "Keyboard Shortcut Variations" in the `.remotemap` file to create "Global Pages".

```text
Define Group    Page    Default    Shifted
Map    Button 1    Play           Default
Map    Button 1    Stop           Shifted
```

*   **Concept:** You can map the *same* physical button to different items based on a global "Page" variable.
*   **Application:** This is how we implement `Shift` functionality without complex Lua `if/else` chains for every single control. We just change the "Page" group.

## 4. Key Takeaways for OpenPush

1.  **State Tracking:** We must track the state of every item to know if it needs to be turned off.
2.  **Manual Logic:** Auto-inputs are insufficient for Radio Buttons. We need manual handling in `remote_process_midi`.
3.  **Performance:** `remote_set_state` is called frequently. Logic here must be efficient to avoid lagging the UI.

## 5. Implementation Pattern (Lua)

```lua
function handle_radio_button(pressed_index, group_indices)
    -- Turn off everyone else
    for _, idx in ipairs(group_indices) do
        if idx ~= pressed_index then
            -- Send '0' to Reason for this item
            remote.handle_input({
                item = idx,
                value = 0,
                time_stamp = remote.get_time_ms()
            })
        end
    end
    
    -- Turn on self
    remote.handle_input({
        item = pressed_index,
        value = 1,
        time_stamp = remote.get_time_ms()
    })
end
```
