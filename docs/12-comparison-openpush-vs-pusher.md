# OpenPush vs. PusheR: Transport & Architecture Comparison

This document compares the current state of **OpenPush** against the reference implementation **PusheR**. It specifically focuses on Transport functionality, Display logic, and the "Keystroke" integration strategy.

## 1. Architecture & Protocol

| Feature | OpenPush (Current) | PusheR (Reference) | Implication for Us |
| :--- | :--- | :--- | :--- |
| **Bridge Language** | Python | Java (likely based on Ctrlr/PusheR.jar) | Python is easier to modify for OS integration (keystrokes). |
| **SysEx Header** | `F0 00 11 22 01` | `F0 11 22 06` | We must strictly adhere to our header in both Lua and Python. |
| **Encoders** | Mapped to specific CCs. | Mapped via SysEx/CC combo with delta formulas `x*(1-2*y)`. | PusheR's formula handles 2's complement (relative knobs) directly in Lua. We currently do some of this in Python. |
| **Feedback Loop** | Basic LED toggling. | Full state tracking in Lua. | We need to move logic from Python to Lua to reduce latency. |

## 2. Display Logic (The "Big Difference")

| Feature | OpenPush (Current) | PusheR (Reference) | Gap Analysis |
| :--- | :--- | :--- | :--- |
| **Layout Engine** | **Python-side.** The Bridge decides what goes on Line 1 vs Line 2. | **Lua-side.** The Codec decides layout; the Bridge just renders text. | **Critical:** We must move layout logic to Lua (as done in the new Transport.lua) to support "Popups". |
| **Popup Values** | Non-existent. Static text only. | **Event-Driven.** Touching a knob overrides text for ~1s using `remote.get_time_ms()`. | We have implemented the *code* for this in `Transport.lua`, but need to wire up the specific parameters (Tempo, etc.). |
| **Updates** | Sends text on change. | Caches text; only sends *deltas* (changes) to specific 16-char blocks. | We need to implement the 16-char segmenting in our Lua to match this efficiency. |

## 3. Transport Functionality

| Control | OpenPush Status | PusheR Implementation | Missing Features |
| :--- | :--- | :--- | :--- |
| **Play/Stop** | Basic toggle. | Separate Play vs. Stop logic; Play restarts if stopped. | **Behavioral Polish:** Need to implement "Shift+Play = Return to Zero". |
| **Record** | Basic toggle. | Maps `New Overdub` (Button 8) and `New Alt Take` (Button 9). | **Advanced Rec:** We need to map these extended functions. |
| **Loop** | Basic toggle. | Maps `Loop On/Off`, `Move Loop Left/Right`, `Set Loop Length`. | **Loop Navigation:** We are missing the ability to move the loop braces. |
| **Tempo** | Basic encoder. | Maps `Tempo BPM`, `Tap Tempo` (Button 5), `Click On/Off` (Button 6). | **Click/Pre-count:** We need to map the Click and Pre-count buttons. |
| **Navigation** | Basic Track Next/Prev. | Extensive: `Goto Left/Right Locator`, `Target Track Mute/Solo`. | **Locators:** We lack timeline navigation (jumping to markers). |

## 4. The "Keystroke" Strategy

The user noted that PusheR likely uses keystrokes (e.g., `Cmd+T` for "New Track").

*   **Reason Remote SDK Limitations:** The Remote SDK *cannot* trigger application menu commands like "Create Audio Track", "Save", or "Undo" (global). It only controls the *Document* (Transport) and *Devices*.
*   **PusheR's Trick:**
    1.  The User presses "New" on Push.
    2.  Lua script sends a specific MIDI CC (e.g., CC 87) to the Bridge.
    3.  The **Bridge** detects CC 87.
    4.  The Bridge simulates the OS keystroke `Cmd+T` (macOS) or `Ctrl+T` (Windows).
    5.  Reason receives the keystroke and creates the track.

**Current OpenPush Status:**
*   We handle MIDI routing.
*   We **do not** currently import `pyautogui` or `keyboard` libraries to simulate keystrokes.
*   **Action:** We must add a "Macro" layer to `bridge.py` to handle these non-Remote commands.

## 5. Summary of Gaps

1.  **Lua logic is too simple:** Needs to handle timers and state caching (Fixed in new `Transport.lua`).
2.  **Missing "Macro" layer:** Need to add keystroke simulation to Python.
3.  **Display Segmentation:** Need to align Lua text formatting with Push's 4x17 character grid.
4.  **Encoder Acceleration:** Need to ensure the "Tempo" knob feels right (doesn't jump too fast/slow).
