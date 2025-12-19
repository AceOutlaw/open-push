# Python Bridge Update Proposal (Phase 1)

This document outlines the specific code changes proposed for `src/open_push/reason/protocol.py` and `src/open_push/reason/bridge.py`. These updates are necessary to support the new "PusheR-style" architecture we have adopted in the Lua codecs.

## 1. Updates to `protocol.py`

**Goal:** Define the custom SysEx protocol used by the new Lua codecs.

### Proposed Changes

1.  **SysEx Header:**
    *   Confirm header matches Lua: `[0x00, 0x11, 0x22, 0x01]` (Port 1 / Transport).
    *   *Note: PusheR used `F0 11 22 06`, but we are sticking to our own namespace `F0 00 11 22` to avoid conflicts.*

2.  **New Message Types:**
    *   Add `MSG_DISPLAY_LINE = 0x40`: For receiving text lines from Lua.
    *   Add `MSG_KEYSTROKE = 0x50`: For triggering OS keystrokes (Macros).

3.  **Data Structures:**
    *   Ensure `ReasonMessage` class can parse these new types.

## 2. Updates to `bridge.py`

**Goal:** Implement the logic to render display text and execute keystrokes.

### Proposed Changes

1.  **Dependencies:**
    *   Import `pyautogui` (for keystrokes).
    *   *Constraint:* Must handle `ImportError` gracefully if the library isn't installed (fallback to no-op).

2.  **Display Rendering Logic (`_handle_reason_sysex`):**
    *   **Input:** Received `MSG_DISPLAY_LINE` with `Line Index` (1-4) and `Text String`.
    *   **Processing:**
        *   The string from Lua is now pre-formatted (padded to 68 chars).
        *   Bridge needs to split this 68-char string into the 4 physical segments of 17 chars each.
        *   `seg1 = text[0:17]`, `seg2 = text[17:34]`, etc.
    *   **Output:** Send native Push SysEx `F0 47 7F 15 ...` to update the hardware screen.

3.  **Keystroke Macro Logic:**
    *   Create `_handle_macro(command_id)` function.
    *   **Input:** Received `MSG_KEYSTROKE` with `Command ID`.
    *   **Mapping:**
        *   `0x01` (New Track) -> `pyautogui.hotkey('command', 't')` (Mac) or `('ctrl', 't')` (Win).
        *   `0x02` (Undo) -> `pyautogui.hotkey('command', 'z')`.
        *   *Safety:* Add a check to ensure we don't spam keys if the bridge receives a flood of messages.

4.  **Transport Feedback Fix:**
    *   Ensure the bridge correctly parses the Transport LED feedback from Reason (which we fixed in Lua to use `bf 55 ?<???x>`) and updates the Push button LEDs accordingly.

## 3. Verification Plan

After applying these changes, we will verify by:

1.  **Transport Test:** Pressing Play on Push -> Logic in Lua -> Reason Plays -> Feedback to Bridge -> Play button lights up green.
2.  **Display Test:** Touching "Tempo" knob -> Lua sends "Tempo: 120" via SysEx -> Bridge parses and renders "Tempo: 120" on Push screen.
3.  **Macro Test:** Pressing "New" (mapped to CC 87) -> Bridge triggers `Cmd+T` -> Reason creates a new track.

## Questions for Review

*   **Keystrokes:** Are you comfortable with adding `pyautogui` as a dependency? It requires accessibility permissions on macOS.
*   **Protocol:** Do you agree with keeping our `F0 00 11 22` header instead of exactly cloning PusheR's `F0 11 22 06`? (Keeping ours is safer to avoid conflicts if the user *also* has PusheR installed).
