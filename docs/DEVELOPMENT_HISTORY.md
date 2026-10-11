# Open Push Development History

A comprehensive timeline of the open-push project from inception to present state. This document chronicles the development journey, methodologies, discoveries, and key milestones.

---

## Project Overview

**Goal**: Give Ableton Push 1 hardware a second life as a general MIDI controller that works with any DAW or standalone audio engine.

**Total Commits**: 61
**Development Period**: December 18, 2025 - January 3, 2026 (17 days)
**Primary Integrations Built**: Reason Bridge, Seqtrak Bridge, Generic MIDI Bridge

---

## Phase 1: Foundation (December 18, 2025)

### The Beginning - Initial Commit
**Commit**: `37fe28e` - Initial commit: open-push foundation

The project started with the core discovery work:
- Push 1 wake-up and initialization procedures
- Full LCD display control with segment-aware formatting
- Pad LED colors (velocity-based palette)
- Button LED control
- Isomorphic keyboard layout (fourths, C minor)
- Virtual MIDI port output for DAW connection

**Key Discovery**: Push 1 LCD has 4 segments of 17 chars with physical gaps between them - not a continuous 68-character line.

### Isomorphic Controller - v0.2
**Commit**: `3499bd2` - v0.2: Isomorphic controller with scale settings

Implemented the core playable instrument functionality:
- Isomorphic keyboard layout with configurable intervals
- Scale filtering and coloring
- 40+ scale definitions
- Velocity curve for expressiveness

### Modular Architecture - v0.3
**Commit**: `2bab2af` - v0.3: Modular architecture with Reason bridge foundation

Restructured codebase for multi-DAW support:
- Separated Push hardware layer from application logic
- Created bridge pattern for different DAW integrations
- Established port-based communication architecture

---

## Phase 2: Reason Integration (December 18-23, 2025)

### Lua Codecs for Reason Remote
**Commit**: `9ea45d8` - Add Reason Lua codecs for Remote integration

Created three control surface codecs for Reason:
- **OpenPush Transport**: Play, stop, record, tempo, navigation
- **OpenPush Devices**: 8 encoders, parameter names/values, keyboard
- **OpenPush Mixer**: Volume, pan, mute, solo, track selection

Each codec uses custom SysEx protocol (00 11 22) to communicate with Python bridge.

### Transport Controls (Phases 4-6)
**Commits**: `1dbfd03`, `14df687`

Implemented bidirectional transport control:
- Play/Stop/Record buttons send CC to Reason
- Loop toggle via Fixed Length button
- Metronome toggle
- LED feedback reflects transport state
- Device mode with 8 encoders
- Mixer mode with volume/pan/mute/solo

### Drum Modes for Kong, Redrum, Dr.OctoRex
**Commit**: `802170c` - Add drum modes for Kong, Redrum, and Dr.OctoRex (Phase 7)

Device-specific drum layouts:
- Kong: 16-pad 4×4 grid (orange LEDs)
- Redrum: 10-drum 2-row layout (red LEDs)
- Dr.OctoRex: 8-slice single row (purple LEDs)

### Scale/Layout Selection
**Commit**: `288bea3` - Add layout selection and enhanced scale settings (Phase 8)

8 layout presets:
- Fourths Up/Right (standard guitar-like)
- Thirds Up/Right
- Fifths Up/Right
- Octaves Up
- Sequential (piano-like chromatic)

### Note Repeat and Accent
**Commit**: `07fa1d6` - Add Note Repeat UI and rate selection (Phase 9)

- 6 rate options: 1/4, 1/8, 1/16, 1/32, 1/8T, 1/16T
- Accent mode for full velocity (127)
- UI framework established (timer-based retriggering for future)

### Browse Mode for Reason Browser
**Commit**: `bd93086` - Add Browse mode for Reason browser navigation (Phase 10)

**Milestone**: All 10 Reason implementation phases complete!

### Research and Analysis
**Commits**: `82b2589`, `b97663d`, `d741193`

Significant reverse engineering work:
- PusheR reference analysis (competing product study)
- Lua de-obfuscation techniques
- Remote SDK API reference documentation

### Reason Auto-Detection
**Commits**: `2a2057f`, `50af03d`

Major breakthrough - Reason now auto-detects OpenPush:
- Responds to Reason's MIDI SysEx identity requests
- Dynamic probers in Lua codecs find ports by name
- Eliminates manual port assignment in Reason Preferences

### IAC Driver Support and Fixes
**Commits**: `0da432b`, `b4906c1`, `7f0c903`

Some trial and error with persistent ports:
- Attempted IAC Driver ports (reverted, then re-applied)
- Transport Play/Stop toggle fix
- Changed Lua patterns for proper value capture

---

## Phase 3: Hardware Exploration (December 19-20, 2025)

### Transport Controls Enhancement
**Commit**: `f95440a` - Phase 2 transport controls and hardware exploration tools

New exploration tools created:
- `lcd_explorer.py`: LCD capabilities with Game & Watch style demo
- `hardware_explorer.py`: Latency test, 128-color palette, animations
- `hardware_mapper.py`: CC verification with listen/guided modes

**Discovery**: Character code 2 (STX) produces solid block █ for VU meters.

### Documentation Consolidation
**Commit**: `f95440a`

Created `open-push-master-reference.md` (898 lines) as primary hardware reference.

### Scale Mode Button LED Fixes
**Commits**: `70d58ec`, `ee4b4fe`

Discovered Push 1 button LED quirks:
- Upper row (CC 20-27) uses different values than lower row
- Upper row is red/amber hardware limitation, lower row yellow
- Specific values to avoid blinking: Upper 10/7, Lower 13/11

### Push Simulator
**Commit**: `713f860` - Add Push simulator and Style Translation Engine spec

Created terminal-based Push 1 simulator for testing without hardware.

### Documentation Reorganization
**Commit**: `de4e3ac` - Docs reorganization + feature vision + feel research

Major documentation restructure:
- Foundation/: 21 numbered research docs
- Features/: 9 feature specs
- VISION.md: Core philosophy "Ideas Coming In"

New feature specifications:
- Capture & Feel: 5-part spec for humanization
- Multi-Playhead Sequencer (Fugue Machine-inspired)
- Standalone SBC for Raspberry Pi builds

**Key Insight**: "Embellishments/incidentals: The missing piece in MIDI humanization"

---

## Phase 4: Seqtrak Integration (December 23-27, 2025)

### The Pivot to Seqtrak
**Commit**: `05adb9e` - Seqtrak SysEx integration and transport control

Started reverse engineering Yamaha Seqtrak SysEx protocol:
- Decoded 15+ parameters (tempo, mute, solo, key, scale)
- Discovered undocumented Solo state (value=2 in mute param)
- Transport uses MIDI Realtime (FA/FC), not SysEx

### Seqtrak Module with Official Protocol
**Commit**: `d107efd` - Add Seqtrak module with official MIDI protocol

Full protocol implementation:
- Official MIDI channel mapping (1-11 for 11 tracks)
- CC-based control methods for mute, solo, volume, filter, effects
- Track class with official names (KICK, SNARE, etc.)
- Blog posts documenting the journey

### SysEx Protocol Reference
**Commit**: `26ab1fa` - Add Seqtrak SysEx protocol reference

Comprehensive reverse-engineered documentation:
- General SysEx format: `F0 43 10 7F 1C 0C [addr] [data] F7`
- Transport, global parameters (tempo, scale, key)
- Track parameters (selection, octave, mute)
- Step sequencer data formats for drums and sampler

### Mode Switching and Preset Display
**Commit**: `32effce` - Seqtrak bridge mode switching, transport feedback

- Mode switching (Track/Device/Mixer) matching Reason patterns
- Play button toggles play/stop
- Track selection with CC 20/102
- Transport state feedback from Seqtrak SysEx

### Preset Name Lookup System
**Commits**: `f7e9540`, `b433da5`

Added presets.py with 2424 preset names from Yamaha documentation:
- 855 drum presets
- 1077 synth presets
- 100 DX presets
- 392 sampler presets

### Track-Specific Preset Ranges
**Commit**: `16dc104` - Lock preset cycling to track-specific sound ranges

Intelligent preset cycling:
- Synth tracks (8-9): Only synth presets (856-1932)
- DX track (10): Only DX/FM presets (1933-2032)
- Drum tracks (1-7): Only drum presets (1-855)
- Sampler track (11): Only sampler presets (1-392)

### Track-Type-Aware Pad Modes
**Commit**: `19e7dbd` - Track-type-aware pad modes for Seqtrak bridge

Three distinct pad modes based on track type:
- **DRUM mode** (tracks 1-7): Uniform dim white, chromatic
- **MELODIC mode** (tracks 8-10): Isomorphic keyboard with scales
- **SAMPLER mode** (track 11): 7 pads with unique colors per sample

### Drum Step Sequencer
**Commit**: `47790a2` - Drum step sequencer with verified SysEx protocol

Split grid layout:
- Bottom 2 rows: 8 drum pads (2×4) with per-track colors
- Top 4 rows: Step sequencer showing 32 steps per page
- 4 pages = 128 steps total

SysEx protocol verified from MIDI captures:
- Step add: `address 70 [track-1] 00, data [step, note, vel, gate, prob]`
- Step delete: `address 70 [0x20+track-1] 00, data [step]`

### Mixer Mode UX Redesign
**Commit**: `7bb1841` - Mixer mode UX redesign with DRUM bus

- New track order: melodic first, then drums, DRUM bus, sampler
- Virtual DRUM bus controls all 7 drum tracks together
- Clean display: 2 tracks per segment

### Device Mode, Note Repeat, Sample Recording
**Commit**: `d344a59` - Add device mode, note repeat, and sample recording

- Track-type-aware parameter pages (Drum, Synth, DX, Sampler)
- FM synthesis params for DX track (Algorithm, Mod Amt/Freq/Feedback)
- Tempo-synced note repeat with 8 subdivision rates
- Sample recording mode with Shift+Record

### Implementation Gap Analysis
**Commit**: `6d81c69` - Add Seqtrak Push implementation gap analysis

Compared Seqtrak iOS app features against Push implementation:
- 65% of features implemented (~30 features)
- 35% gap (~15 features missing)
- Top missing: LFO section, Effect browser, Choke groups

### Session Transfer Documentation
**Commit**: `c208095` - Add session transfer strategy and Seqtrak documentation

Created knowledge transfer system:
- NEW_SESSION.md with read order and self-quiz
- QUICK_REF.md one-page cheat sheet
- TERMINOLOGY.md with critical definitions (6 variations, Pattern vs Bar)
- BUGS_AND_ENHANCEMENTS.md tracking known issues

### Bar Length and Variation Fixes
**Commits**: `3c088b7`, `9aeab92`

- Bar length cycles through powers of 2 only (hardware limitation)
- Variation selection via CC 78 encoder (1-6 per track)
- Correct SysEx address offsets discovered

---

## Phase 5: Standalone MIDI Bridge (December 27, 2025 - January 1, 2026)

### Public Release Preparation
**Commit**: `059a98a` - Update README for public release

- Updated README for full project scope (Reason + Seqtrak)
- Documented Raspberry Pi deployment
- Cleaned git history for public sharing

### Generic MIDI Bridge
**Commit**: `641f07e` - Add MIDI bridge for Push 1 standalone controller

Complete MIDI bridge ported from Seqtrak architecture:
- Isomorphic keyboard with scale/root selection
- Drum pad mode with GM mapping
- Encoder banks (Volume, Pan, Filter, FX) configurable via JSON
- Settings menu (Shift+User) for Bluetooth, MIDI, Velocity, Defaults
- Note repeat with configurable subdivisions
- Transport controls (Play/Stop/Record)
- USB gadget and Bluetooth MIDI output support

### Settings Menu and LCD Fixes
**Commit**: `ae7f1c2` - Use segment-based LCD display and add missing settings

Corrections to match architecture:
- Changed all `set_lcd_line()` to `set_lcd_segments()` for 4-segment format
- Added 6 settings categories: Bluetooth, MIDI, Velocity, Defaults, Colors, Encoders
- Configurable pressed pad color

### Bluetooth MIDI Integration
**Commit**: `9726cae` - Integrate Bluetooth MIDI control with settings menu

- Import BluetoothMIDIOutput module (optional, graceful fallback)
- Connect settings menu to actual Bluetooth control
- Display popup feedback for Bluetooth status changes

---

## Phase 6: BLE MIDI Bridge (January 1-3, 2026)

### Working BLE MIDI for Raspberry Pi
**Commit**: `d99abba` - Add working BLE MIDI bridge for Raspberry Pi

Major breakthrough for iOS/macOS wireless MIDI:
- BLE MIDI peripheral forwards USB MIDI via Bluetooth
- Tested working: MPK Mini → Pi Zero 2W → BLE → iPad

Key fixes discovered:
- Add encrypt-read/write/notify flags to force pairing
- Register NoInputNoOutput pairing agent for Just Works mode
- Disable BlueZ built-in MIDI plugin (`--noplugin=midi`)
- Change MAC address to break stale bond cache

### Auto-Detection and Troubleshooting
**Commit**: `15250c3` - Add BLE MIDI auto-detection and troubleshooting docs

- `midi_monitor_thread()` for automatic controller detection
- Auto-reconnects when USB MIDI controllers plugged/unplugged
- Comprehensive troubleshooting documentation

Key pitfalls documented:
- Launchkey Mk4 "Easy Start" mode (hold Play while connecting)
- BlueZ 5.66 requires `--noplugin=midi` on command line
- iOS BLE MIDI only visible from within MIDI apps

### Launchpad X Fix
**Commit**: `9f265e6` - Prefer MIDI In over DAW In ports for Launchpad X

- Launchpad X exposes two ports: DAW In (Ableton-specific) and MIDI In
- Auto-detection was picking wrong port
- Now prefers ports with "MIDI In" for proper MIDI support

### BLE MIDI Integration Plan
**Commit**: `1544340` - Add BLE MIDI integration plan for Open Push

Captured all learnings from BLE MIDI experiment:
- Critical BlueZ configuration requirements
- GATT characteristic encrypt flags for pairing
- BLE-MIDI packet format and UUIDs
- Architecture comparison
- Step-by-step integration roadmap

### Settings Menu and Mode Switching
**Commit**: `024caec` - Add settings menu, mode switching, and bridge improvements

Major feature addition:
- Mode switching architecture (modes/, helpers/)
- Bridge app for standalone operation
- Mode preferences for persistent settings
- BLE GATT output module
- Deploy script updates

### PR Review Fixes
**Commits**: `48f8ae1`, `e68760d`, `8ec7e9c`

Code quality improvements from PR review:
- Fix critical MIDI channel bug
- Refactor nested ternary operators
- Use efficient BLE packet creation
- Replace bare except clauses
- Remove unused constants

---

## Key Technical Discoveries

### Push 1 Hardware
1. **LCD Segments**: 4 segments × 17 chars with physical gaps (not continuous 68 chars)
2. **Button LED Values**: Upper row (CC 20-27) uses different values than lower row (CC 102-109)
3. **Character Code 2 (STX)**: Produces solid block █ for VU meters
4. **Encoder Touch Notes**: Notes 0-10 are touch events, need filtering

### Seqtrak Protocol
1. **SysEx Format**: `F0 43 10 7F 1C 0C [address] [data] F7`
2. **Transport**: Uses MIDI Realtime (FA/FC), not SysEx
3. **Solo State**: Undocumented - value=2 in mute parameter
4. **Bar Length**: Only powers of 2 supported (1, 2, 4, 8)
5. **6 Variations**: Not 4 - critical for correct implementation

### BLE MIDI on Raspberry Pi
1. **Pairing**: encrypt-read/write/notify GATT flags required for pairing initiation
2. **BlueZ Plugin**: Disable built-in MIDI plugin with `--noplugin=midi`
3. **MAC Address**: Changing MAC breaks stale bond cache on reconnect
4. **iOS Visibility**: BLE MIDI only visible from within MIDI apps

### Reason Remote Integration
1. **Channel Translation**: Push uses ch0, Reason expects ch15
2. **Auto-Detection**: Respond to Universal SysEx Identity Request (0x7E)
3. **Port Naming**: Must match luacodec descriptions exactly
4. **Lua Patterns**: Values >=0x80 invalid inside SysEx data

---

## Development Methodology

### AI-Assisted Development
The project was developed using multiple AI assistants:
- **Claude Code**: Primary development partner
- **Gemini**: Code review and suggestions
- **Codex**: Integration improvements

### Reverse Engineering Approach
1. Capture MIDI/SysEx with hardware analyzer
2. Document observed patterns
3. Create minimal test scripts
4. Verify behavior matches documentation
5. Update protocol reference

### Session Transfer Strategy
Due to domain-specific knowledge, established:
- NEW_SESSION.md with startup protocol
- QUICK_REF.md for constant reference
- TERMINOLOGY.md for critical definitions
- LAST_SESSION.md for continuity

---

## Current State Summary

### Working Features
- ✅ Push 1 as isomorphic MIDI controller
- ✅ 40+ scales with encoder selection
- ✅ Reason integration with auto-detection
- ✅ Seqtrak bridge with full track control
- ✅ Step sequencer for drum tracks
- ✅ Mixer mode with virtual DRUM bus
- ✅ Device mode with track-specific parameters
- ✅ Standalone Raspberry Pi deployment
- ✅ BLE MIDI bridge for iOS/macOS
- ✅ Settings menu for configuration

### Hardware Deployments
1. **pibridge** (Raspberry Pi 4/5): Main Seqtrak bridge, auto-start on boot
2. **pimini** (Pi Zero 2W): Compact/portable BLE MIDI bridge

### In Development
- Runtime mode switching (Seqtrak ↔ Generic MIDI ↔ Settings)
- System settings from Push interface
- Safe shutdown and network info display

---

## Repository Statistics

- **Total Commits**: 61
- **Development Days**: 17 (Dec 18, 2025 - Jan 3, 2026)
- **Documentation Files**: 30+
- **Python Modules**: 15+
- **Lua Codecs**: 3

---

*Document generated from git history on January 3, 2026*
