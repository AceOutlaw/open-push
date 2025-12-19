# OpenPush Transport Implementation Plan

This plan outlines the steps to bring OpenPush's transport and display functionality up to par with PusheR, including the "popup" display logic and OS-level keystroke macros.

## Phase 1: Bridge & Protocol Updates (The Plumbing)
**Goal:** Ensure the Python Bridge can receive the new SysEx format and execute OS keystrokes.

1.  **Update `protocol.py`:**
    *   Add `MSG_DISPLAY_LINE = 0x40` (and other 0x4x types if needed).
    *   Add `MSG_KEYSTROKE = 0x50` (New type for triggering macros).

2.  **Update `bridge.py` Dependencies:**
    *   Add `pyautogui` (preferred) or `keyboard` to `requirements.txt`.
    *   Reason: We need to simulate `Cmd+T`, `Cmd+Z` (if not mapped to Undo), etc.

3.  **Implement Display Rendering in `bridge.py`:**
    *   Update `_handle_reason_sysex` to parse the `0x40` message.
    *   The Bridge should *blindly* write the text received from Lua to the Push screen segments. (Lua does the formatting now).

4.  **Implement Macro Handler in `bridge.py`:**
    *   Create a `_handle_macro(command_id)` function.
    *   Map IDs to keystrokes:
        *   `0x01` -> `Cmd+T` (New Audio Track)
        *   `0x02` -> `Cmd+I` (New Instrument Track)
        *   `0x03` -> `Cmd+S` (Save)
        *   `0x04` -> `Cmd+Z` (Undo - if Remote Undo isn't sufficient)

## Phase 2: Lua Transport Codec (The Logic)
**Goal:** Complete the mapping of all transport buttons and implement popup feedback.

1.  **Map Remaining Controls:**
    *   **Metronome:** Map to `Click On/Off`.
    *   **Loop:** Map to `Loop On/Off`.
    *   **New:** Map to a custom output that triggers the `MSG_KEYSTROKE` SysEx (or a specific unused CC).
    *   **Automation:** Map to `Target Track Enable Automation Recording`.
    *   **Fixed Length:** Map to `set_loop_length` (custom logic in Lua to move loop points?).

2.  **Implement "Popup" for Tempo:**
    *   We already have the logic in `OpenPush Transport.lua`.
    *   Verify mapping: `Knob 1` (Tempo) -> `Tempo BPM`.
    *   When Tempo changes: `g_display[1].popup_text = "BPM: " .. val`.

3.  **Implement "Shift" Functionality:**
    *   Modify `remote_process_midi` to track the `Shift` button state.
    *   **Shift + Play:** Triggers `Stop` (Return to Zero) or `Rewind`.
    *   **Shift + Record:** Triggers `New Overdub`.

## Phase 3: Testing & Polish
**Goal:** Verify everything works without crashing Reason or the Bridge.

1.  **Unit Test Lua:**
    *   Use a "mock" bridge (simple script) to print out SysEx messages received from Reason.
    *   Verify `F0 00 11 22 01 40 ...` messages appear when controls are touched.
    *   Verify they stop appearing after 1.5 seconds.

2.  **Latency Check:**
    *   Ensure the "Popup" doesn't lag. If it does, optimize the `pad_string` function or reduce the frequency of updates.


## References

*   `docs/14-reason-remote-knowledge-base.md`: Detailed findings on SDK limitations and patterns.
*   `docs/17-manual-remote-file-editing-guide.md`: foundational guide on `.midicodec` and `.remotemap` file structures.
*   `docs/18-lua-debugging-and-logging.md`: Techniques for inspecting Lua state via error dumps.
*   `docs/19-radio-button-implementation-guide.md`: Logic for mutually exclusive buttons and handling GUI feedback loops.
*   `docs/20-advanced-remote-coding-concepts.md`: Strategies for dynamic indexing, modes, and optimizing state updates.
