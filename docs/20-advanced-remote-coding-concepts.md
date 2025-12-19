# Advanced Remote Coding Concepts

This document captures advanced techniques and "gotchas" from expert Reason Remote developers (Pooh Bear), focusing on optimizing codecs, handling state, and using modes effectively.

## 1. Item Indexing Strategy

Instead of hardcoding item indices (e.g., `remote.get_item_value(5)`), robust codecs dynamically track indices during initialization.

### The Problem
If you add a new item at the top of your `remote_init` list, all subsequent item indices shift by +1. Hardcoded scripts break immediately.

### The Solution: Dynamic Tracking
Use a table to store indices by name during `remote_init`.

```lua
-- Global table to store indices
g_item_indices = {}

function remote_init(manufacturer, model)
    local items = {
        {name="Button 1", ...},
        {name="Fader 1", ...}
    }
    remote.define_items(items)

    -- Populate lookup table
    for i, item in ipairs(items) do
        g_item_indices[item.name] = i
    end
end

-- Usage
local val = remote.get_item_value(g_item_indices["Fader 1"])
```

## 2. Modes ("OTF" vs "Norm")

You can use the `.remotemap` file to flag specific devices as needing special handling (e.g., "On The Fly" mapping vs "Normal").

### The Map Entry
```text
Scope   Propellerheads  Europa
Map     Device Name     Device Name     OTF
```

### The Codec Logic
1.  Define a "Mode" output for the item in `remote_init`:
    ```lua
    {name="Device Name", output="text", modes={"Norm", "OTF"}}
    ```
2.  Check the mode in `remote_set_state`:
    ```lua
    local mode_idx = remote.get_item_mode(g_device_name_index)
    local is_otf = (mode_idx == 2) -- 2 corresponds to "OTF" in the modes list
    
    if is_otf then
        -- Execute special logic for this device
    end
    ```

## 3. Timing & State "Gotchas"

### `remote_set_state` is NOT Real-Time
*   This function is called *frequently* (several times a second) but not strictly on every event.
*   **Audio Priority:** Reason prioritizes audio processing over control surface feedback. Do not rely on `remote_set_state` for instantaneous logic that affects audio.
*   **The "Double Call" Loop:** If you update an item in Lua (e.g., handling a radio button press), Reason might call `remote_set_state` again to confirm the change. Ensure your logic handles this re-entry without infinite loops.

### Input Handling Latency
*   `remote.handle_input` is a *request*. If you immediately read back the item's value, it will likely still show the *old* value until the next processing cycle.

## 4. Optimization

*   **Expensive Controls:** Faders and Knobs generate flood traffic. Process them first or efficiently in `remote_process_midi`.
*   **Cheap Controls:** Buttons send single events.
*   **Return `true`/`false`:** Always explicitly return `true` if you handled a MIDI message to stop Reason from wasting cycles trying to match it against auto-inputs.

## 5. Device Label vs. Device Name

*   **Device Name:** The type of device (e.g., "SubTractor").
*   **Device Label:** The user-defined name (e.g., "Bass Lead 1").
*   **Tracking:** Track *both*. If the user renames a track (Label changes) but the device stays the same, you still need to update the display.

```lua
if g_cached_label ~= new_label then
    update_display(new_label)
    g_cached_label = new_label
end
```
