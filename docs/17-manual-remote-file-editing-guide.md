# Manual Remote File Editing Guide

This guide is based on historical documentation for Propellerhead's Remote technology. It details how to manually create and edit `.midicodec` and `.remotemap` files to support unsupported MIDI controllers or customize existing ones. This is a foundational reference for the OpenPush project.

## 1. Concept: Remote Codecs & Maps

Remote uses two files to define a controller:

1.  **MIDI Codec (`.midicodec`):** Defines the *physical* controls on your hardware (knobs, faders, buttons) and the raw MIDI messages they send (CC numbers, channels).
2.  **Remote Map (`.remotemap`):** Defines the *logical* connection between those physical controls and Reason's internal device parameters (e.g., "Knob 1 controls Subtractor Filter Freq").

## 2. File Locations

**macOS:**
*   `/Library/Application Support/Propellerhead Software/Remote/Codecs/`
*   `/Library/Application Support/Propellerhead Software/Remote/Maps/`

**Windows:**
*   `%PROGRAMDATA%\Propellerhead Software\Remote\Codecs\`
*   `%PROGRAMDATA%\Propellerhead Software\Remote\Maps\`

**User Locations (Recommended for Dev):**
*   **macOS:** `~/Library/Application Support/Propellerhead Software/Remote/...`
*   **Windows:** `%APPDATA%\Propellerhead Software\Remote\...`

## 3. The Codec File (`.midicodec`)

This text file lists every control on your hardware.

### Header
```text
Item    Play            button  0   1
Item    Fader 1         value   0   127
Item    Knob 1          value   0   127
```
*   **Types:** `value` (knobs/faders), `button` (switches), `keyboard` (keys), `delta` (endless encoders).

### Mapping Definitions
```text
Map     b? 0a xx        Knob 1  x   0   0
```
*   **`b? 0a xx`**: The MIDI pattern.
    *   `b?`: Status byte (Control Change on any channel).
    *   `0a`: Data Byte 1 (Controller Number 10).
    *   `xx`: Data Byte 2 (Variable value).
*   **`Knob 1`**: The name of the Item defined above.
*   **`x`**: The formula for the value sent to Reason (usually just `x`).

## 4. The Map File (`.remotemap`)

This file links Codec items to Reason functions.

### Structure
The file is divided into **Scopes**. Each Scope targets a specific Reason device (e.g., `SubTractor`, `Mixer 14:2`, `Transport`).

```text
Scope   Propellerheads  Reason Document
Map     Play            Play
Map     Stop            Stop

Scope   Propellerheads  SubTractor Analog Synthesizer
Map     Knob 1          Filter Freq
Map     Knob 2          Filter Res
```

### Banking (Groups)
If you have fewer physical controls than software parameters, you can use Groups to create "Banks".

```text
Define Group    Bank    Vol     Pan
Map     Knob 1          Channel 1 Level     Vol
Map     Knob 1          Channel 1 Pan       Pan
```
*   **Switching:** Users switch banks via keyboard shortcuts or mapped buttons.

## 5. Troubleshooting & Tips

*   **Syntax:** Use **Tabs** between columns, not spaces. The format is strict.
*   **Red Cross:** If a red cross appears in Reason's Preferences, click it to see syntax error details.
*   **Templates:** Always start by copying an existing file (e.g., M-Audio Oxygen 8) rather than writing from scratch.
*   **Hex:** MIDI values are in Hexadecimal (0-127 = 00-7F). Use a converter or lookup table.

## 6. Relevance to OpenPush

While OpenPush uses Lua for dynamic behavior, understanding this underlying static mapping is crucial because:
1.  **Fallback:** If Lua fails, the static map defines the baseline behavior.
2.  **Naming:** The Item names in our Lua script (`remote_init`) MUST match the names used in our `.remotemap` file.
3.  **Scope Priority:** Reason prioritizes specific device scopes (Mixer) over global scopes (Document). We must structure our maps to ensure transport controls work even when focused on a synth.

