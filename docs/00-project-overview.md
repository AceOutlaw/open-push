# Push-to-Reason Bridge Project

## Overview

This project aims to create an open-source MIDI bridge application that enables Ableton Push hardware controllers to work with Propellerhead Reason (now Reason Studios Reason).

### Background

The original PusheR application has served this purpose for nearly 10 years. However, as a niche product with uncertain future development, having an open, maintainable alternative ensures long-term usability of Push hardware with Reason.

### Goals

1. **Push 1 Support** - Primary target, full feature parity with original PusheR
2. **Push 2/3 Compatibility** - Future-proof architecture for newer hardware
3. **Language Agnostic** - Not locked to Max/MSP; use modern, maintainable languages
4. **Open Source** - Community can maintain and extend functionality
5. **Cross-Platform** - macOS initially, with potential for Windows/Linux

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              REASON DAW                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │PushTransport│  │ PushDevices │  │  PushMixer  │  (Lua Codecs)        │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘                      │
│         │                │                │                              │
│         └────────────────┼────────────────┘                              │
│                          │                                               │
│                    ┌─────┴─────┐                                         │
│                    │  Push_IN  │◄──── Virtual MIDI Port (IAC Driver)     │
│                    │  Push_OUT │────►                                    │
│                    └───────────┘                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ MIDI
                                   │
┌─────────────────────────────────────────────────────────────────────────┐
│                         BRIDGE APPLICATION                               │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │                      Message Router                               │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐  │   │
│  │  │  Transport │  │   Device   │  │   Mixer    │  │    Note    │  │   │
│  │  │   Mode     │  │   Mode     │  │   Mode     │  │   Mode     │  │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐             │
│  │ LCD Controller │  │ LED Controller │  │  Pad Manager   │             │
│  │   (Push 1)     │  │                │  │                │             │
│  └────────────────┘  └────────────────┘  └────────────────┘             │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ MIDI
                                   │
┌─────────────────────────────────────────────────────────────────────────┐
│                        ABLETON PUSH HARDWARE                             │
│                                                                          │
│                    ┌───────────────────┐                                 │
│                    │ Ableton Push      │                                 │
│                    │ User Port         │◄──── USB Connection             │
│                    └───────────────────┘                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## How It Works

### MIDI Signal Flow

1. **Push → Bridge**: User presses pad/button/encoder on Push hardware
2. **Bridge → Reason**: Bridge translates the message and sends to virtual MIDI port
3. **Reason Codec**: Lua codec interprets message and controls Reason
4. **Reason → Bridge**: Reason sends feedback (parameter values, track names, etc.)
5. **Bridge → Push**: Bridge updates LCD display and LED colors

### Virtual MIDI Ports

On macOS, we use **IAC Driver** (Inter-Application Communication) to create virtual MIDI ports:

- **Push_IN** - Bridge sends TO this port, Reason receives FROM it
- **Push_OUT** - Reason sends TO this port, Bridge receives FROM it

### Reason Remote Protocol

Reason uses **Lua codecs** to define how it communicates with control surfaces. The existing PusheR codecs define:

| Codec | Purpose |
|-------|---------|
| PushTransport | Transport controls, navigation, global functions |
| PushDevices | Device parameter control, encoders, device selection |
| PushMixer | Mixer control, volume, pan, mute, solo |

These codecs use a **custom SysEx protocol** to communicate with the bridge:

```
F0 11 22 06 [line] [16 ASCII chars] F7
```

This is NOT the Push hardware protocol - it's the protocol between Reason and the bridge application. The bridge must translate between this format and actual Push hardware commands.

---

## Key Components to Build

### 1. MIDI I/O Layer
- Connect to Push User Port (input/output)
- Connect to virtual MIDI ports (input/output)
- Handle SysEx messages
- Low-latency message routing

### 2. Protocol Translator
- Parse Reason's custom SysEx format
- Convert to Push hardware commands
- Handle bidirectional translation

### 3. Mode Manager
- Track current mode (Transport, Device, Mixer, Note)
- Handle mode switching
- Maintain state for each mode

### 4. Display Controller (Push 1)
- Parse 16-character text chunks from Reason
- Format into 68-character LCD lines
- Send SysEx to Push hardware

### 5. LED Manager
- Track LED states for pads and buttons
- Map Reason colors to Push color palette
- Handle blinking/pulsing effects

### 6. Pad/Note Handler
- Chromatic and scale-based layouts
- Velocity sensitivity
- Aftertouch routing

### 7. Configuration
- MIDI port selection
- Brightness settings
- Scale/key preferences
- Layout options

---

## Language Considerations

The original PusheR was built with **Max/MSP**, but we have more options:

| Language | Pros | Cons |
|----------|------|------|
| **Python** | Easy prototyping, good MIDI libraries (mido, python-rtmidi), cross-platform | Performance overhead, requires runtime |
| **Node.js** | Async-friendly, good MIDI packages (easymidi), easy UI with Electron | V8 overhead, large app size with Electron |
| **Rust** | Fast, safe, good MIDI crate (midir), small binaries | Steeper learning curve |
| **C++** | Maximum performance, JUCE framework, industry standard | Complex, longer development time |
| **Go** | Fast compilation, simple deployment, decent MIDI support | Less mature MIDI ecosystem |

### Recommended Approach

1. **Prototype in Python** - Validate the architecture quickly
2. **Production in Rust or C++** - For performance and distribution

---

## Project Structure

```
PusheR 1.1.9 Mac App Files/
├── docs/                           # Project documentation
│   ├── 00-project-overview.md      # This file
│   ├── 01-push-midi-protocol.md    # Push hardware protocol reference
│   ├── 02-hardware-comparison.md   # Push 1 vs 2 vs 3 differences
│   └── 03-reason-remote-protocol.md # Reason codec communication
│
├── reference/                      # Original PusheR files for reference
│   ├── original-app/               # Original PusheR application
│   ├── original-docs/              # Original documentation
│   ├── remote-files/               # Lua codecs and remote maps
│   └── SoftwareLicenseAgreement.pdf
│
├── src/                            # Source code (to be created)
│   ├── core/                       # Core bridge logic
│   ├── protocols/                  # Protocol handlers
│   ├── modes/                      # Mode implementations
│   └── ui/                         # User interface (if needed)
│
└── tests/                          # Test files (to be created)
```

---

## Next Steps

1. [ ] Analyze existing Lua codecs to understand Reason's protocol
2. [ ] Create proof-of-concept Python script for basic MIDI routing
3. [ ] Test Push 1 communication (LCD, LEDs, pads)
4. [ ] Implement Transport mode as first feature
5. [ ] Add Device and Mixer modes
6. [ ] Create configuration UI
7. [ ] Package for distribution

---

## Resources

### Official Documentation
- [Push 2 MIDI Interface](https://github.com/Ableton/push-interface)
- [Reason Remote SDK](https://www.reasonstudios.com/developer)

### Community Resources
- [Decompiled Ableton Scripts](https://github.com/gluon/AbletonLive9_RemoteScripts)
- [STRUCTURE VOID](https://structure-void.com/ableton-live-push-and-scripts/)
- [Push Protocol Forums](https://forum.ableton.com/viewtopic.php?t=193744)

### Reference Implementation
- Original PusheR application (see reference/original-app/)
- PusheR Lua codecs (see reference/remote-files/)
