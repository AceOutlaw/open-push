# Lua Codec Debugging & Logging Guide

This document captures advanced debugging techniques for Reason Remote Lua codecs, based on community knowledge and video tutorials. Since Reason does not provide a built-in console or debugger for codecs, we must use specific workarounds to inspect the internal state.

## 1. The "Error Dump" Technique

The most basic way to see what's happening inside a codec is to intentionally crash it using the `error()` function. Reason captures the error message and displays it in the Surface settings (indicated by a red cross).

### Basic Usage
```lua
-- Crash the script and print a message
error("Here is my variable: " .. tostring(my_variable))
```

### Advanced Usage: Building a Log Buffer
To inspect multiple variables or the flow of execution without stopping immediately, you can build a large string buffer and then dump it all at once at a critical point (or when a specific condition is met).

```lua
-- Global log buffer
g_log_buffer = "DEBUG LOG:\n"

-- Helper function to append to buffer
function log(msg)
    g_log_buffer = g_log_buffer .. msg .. "\n"
end

-- Usage throughout your code
function remote_process_midi(event)
    log("Received MIDI: " .. string.format("%02X", event[1]))
    
    if some_condition then
        log("Condition met!")
        -- Dump everything and stop
        error(g_log_buffer)
    end
end
```

**Workflow:**
1.  Add `log()` calls to your functions.
2.  Trigger the specific action on your hardware.
3.  The script crashes.
4.  Open Reason Preferences > Control Surfaces.
5.  Click the Red Cross icon next to your surface.
6.  Copy the error text (which contains your full log) to a text editor to analyze.

## 2. Real-Time Logging (Advanced)

While the `error()` method is static (it stops execution), some advanced developers use a "Print to Loop MIDI" approach if they have a virtual MIDI port monitored by external software (like MIDI Monitor or MIDI-OX).

**Concept:**
*   Map a dummy "output" item in `remote_init`.
*   In your Lua code, format debug text as dummy MIDI messages (e.g., specific SysEx or CCs).
*   Send these messages via `remote.make_midi()` in `remote_deliver_midi()`.
*   Read them in an external MIDI monitor.

*Note: This is more complex to set up but allows seeing data without crashing the surface.*

## 3. Common Errors & Fixes

*   **"Attempting to call a global name a nil value":** You likely missed an `=` sign or misspelled a function name.
*   **"Failed to run":** Check your file paths. The `picture` in `.luacodec` must be in the same folder.
*   **Map File Not Found:** Verify the `manufacturer` and `model` strings in `.remotemap` match the `.luacodec` *exactly* (case-sensitive).

## 4. Key Limitations

*   **No OS Access:** Lua in Reason is sandboxed. You cannot write to files or access the OS directly.
*   **Memory Limits:** There is a limit to how many variables ("upvalues") you can have. Use tables to group variables if you hit this limit.
*   **Lua Version:** Reason uses **Lua 5.1**. Newer Lua features (5.3+) will not work.
