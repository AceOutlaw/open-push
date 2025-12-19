# Push 2 Interface Findings & Push 1 Implications

This document analyzes the relevance of the official Ableton Push 2 Interface documentation to our Push 1 project, specifically regarding transport behavior and the Reason Remote SDK.

## 1. Push 1 vs. Push 2: The Critical Differences

While both devices share a similar MIDI CC map for buttons, their architecture differs significantly in areas that affect our "Bridge" design.

| Feature | Push 1 (Our Target) | Push 2 (Reference) | Implication for OpenPush |
| :--- | :--- | :--- | :--- |
| **Display** | SysEx-controlled text segments. Slow bandwidth. | USB Video Class (pixel display). High bandwidth. | We **cannot** use Push 2's display logic. We must stick to our custom `F0 00 11 22...` text protocol. |
| **Transport** | Standard MIDI CCs (Momentary). | Standard MIDI CCs (Momentary). | **Aligns.** The button behavior (Press=127, Release=0) is identical. |
| **Touch Strip** | Pitch Bend (14-bit). | Pitch Bend (14-bit). | **Aligns.** |
| **Encoders** | Relative MIDI CCs. | Relative MIDI CCs. | **Aligns.** |

**Conclusion:** The Push 2 documentation is a valid reference for **Button/Encoder behavior**, but useless for **Display logic**.

## 2. The Play/Pause "Pause" Logic

The user specifically requested "Play starts, Play again pauses, Shift+Play stops (RTZ)".

### Reason Remote SDK Behavior
*   **Item:** `Play`
*   **Behavior:** Toggle. Pressing it toggles between "Playing" and "Stop" (not Pause).
*   **Problem:** Reason's "Stop" command usually performs a "Return to Zero" (RTZ) or moves the playhead to the start of the loop, depending on settings. It does *not* natively support a "Pause" (Halt in place) command via a simple toggle item.

### Achieving "Pause" Behavior
To get true "Pause" (Play -> Halt in place -> Play from halt), we might need to map to specific keyboard shortcuts if the Remote item doesn't support it.

*   **Spacebar:** In Reason, `Spacebar` toggles Play/Stop. If you press it while playing, it stops. If you press again, it plays from where it stopped (unless "Return to Zero on Stop" is enabled in Reason preferences).
*   **Numpad 0:** Stop (RTZ).
*   **Numpad Enter:** Play.

**Strategy:**
If the standard `Play` item triggers RTZ on stop, we might need to use our **Keystroke Macro** feature to send `Spacebar` instead of the MIDI message `Play`.

## 3. Implementation Plan for "True Pause"

1.  **Test Current Fix:** We reverted to the standard `Play` item in `Transport.lua`. We need to see if this behaves as "Play/Stop(RTZ)" or "Play/Pause".
2.  **Fallback to Macros:** If the Remote Item forces RTZ, we will modify `bridge.py` to intercept the Play button and send a `Spacebar` keystroke instead.

## 4. Immediate Action Item
We will stick to the plan of finishing the **Python Bridge Updates** (Phase 1). This is critical because if we need to use Keystrokes for the Play/Pause behavior, the Bridge *must* have the macro system implemented.
