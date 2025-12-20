# open-push Master Reference

A comprehensive reference for the open-push project: Ableton Push 1 integration with Reason via middleware bridge.

**Target Hardware:** Ableton Push (Gen 1)
**Target Software:** Reason (via Remote Protocol)
**Architecture:** Middleware Bridge (Python) + Reason Remote Codec (Lua)

---

## Table of Contents

1. [Architecture & Philosophy](#architecture--philosophy)
2. [Push 1 Hardware Reference](#push-1-hardware-reference)
3. [Implementation Architecture](#implementation-architecture)
4. [Encoder Group Modes](#encoder-group-modes)
   - [Track Mode](#track-mode)
   - [Device Mode](#device-mode)
   - [Volume Mode](#volume-mode)
   - [Pan Mode](#pan-mode)
   - [Clip Mode](#clip-mode)
   - [Master Mode](#master-mode)
5. [Transport Controls](#transport-controls)
6. [Right Side Buttons](#right-side-buttons)
7. [Note Mode](#note-mode)
   - [Generic Device Submode (Isomorphic Keyboard)](#generic-device-submode-isomorphic-keyboard)
   - [Kong Submode](#kong-submode)
   - [Redrum Submode](#redrum-submode)
   - [Dr.OctoRex Submode](#droctorex-submode)
8. [Session Mode](#session-mode)
9. [Note Repeat](#note-repeat)
10. [Aftertouch / Pedals](#aftertouch--pedals)
11. [Keycommands](#keycommands)
12. [Reason Remote SDK: Available Parameters](#reason-remote-sdk-available-parameters)
13. [Enhancement Opportunities](#enhancement-opportunities)
14. [Potential New Features](#potential-new-features)
15. [Hard Limits](#hard-limits)

---

## Encoder Group Modes

### Track Mode

**Access:** Track button (SHIFT+Track = show Sequencer view)

**Display:**
- Line 1-2: Track name, patch name, device type, song name
- Line 3-4: Playhead (bars:beats:16th), Left Loop position, Right Loop position, Loop status, Tempo

| Control | Function | SHIFT Function |
|---------|----------|----------------|
| Encoder 1 | Track selection | - |
| Encoder 2 | Playhead (bars) | Playhead (16th steps) |
| Encoder 3 | Patch selection | - |
| Encoder 4 | Left Loop position | - |
| Encoder 5 | Right Loop position | - |
| Encoder 6 | *unused* | - |
| Encoder 7 | *unused* | - |
| Encoder 8 | *unused* | - |
| Top Button 1 | Track prev | - |
| Top Button 2 | Track next | - |
| Top Button 3 | Patch prev | - |
| Top Button 4 | Patch next | - |
| Top Button 5 | Playhead scroll left | Jump to Left Loop |
| Top Button 6 | Playhead scroll right | Jump to Right Loop |
| Top Button 7 | Left Loop adjust left | Move loop brace left |
| Top Button 8 | Left Loop adjust right | Move loop brace right |
| Bottom Button 1 | Right Loop adjust left | Move loop by length left |
| Bottom Button 2 | Right Loop adjust right | Move loop by length right |
| Bottom Button 3 | Loop on/off | - |
| Bottom Button 4 | Track selection | - |
| Bottom Button 5-8 | *unused* | - |
| Mute | Mute selected track | - |
| Solo | Solo selected track | - |

---

### Device Mode

**Access:** Device button (SHIFT+Device = show Rack view)

**Display:**
- Line 1: Parameter names (8)
- Line 2: Parameter values (8)
- Line 3: Device type, selected bank name
- Line 4: Bank names (8 visible of up to 24)

| Control | Function | SHIFT Function |
|---------|----------|----------------|
| Encoder 1 | Parameter (bank slot 1) | - |
| Encoder 2 | Parameter (bank slot 2) | - |
| Encoder 3 | Parameter (bank slot 3) | - |
| Encoder 4 | Parameter (bank slot 4) | - |
| Encoder 5 | Parameter (bank slot 5) | - |
| Encoder 6 | Parameter (bank slot 6) | - |
| Encoder 7 | Parameter (bank slot 7) | - |
| Encoder 8 | Parameter (bank slot 8) | - |
| Master Vol Encoder | Device-level volume (not mixer) | - |
| Top Button 1-8 | Select bank (slot 1-8 of visible banks) | - |
| Bottom Button 1-8 | Toggle parameter (min/max for continuous) | - |
| Prev | Previous 8 banks | - |
| Next | Next 8 banks | - |

**Notes:** Up to 24 banks per device. Toggle buttons useful for on/off parameters; for continuous parameters they jump between min/max.

---

### Volume Mode

**Access:** Volume button (SHIFT+Volume = show Mixer view)

**Display:**
- Line 1: "Level" labels
- Line 2: Volume values (dB)
- Line 3: Metering feedback
- Line 4: Channel names

| Control | Function | SHIFT Function |
|---------|----------|----------------|
| Encoder 1-8 | Channel 1-8 volume | - |
| Master Vol Encoder | Master volume | - |
| Top Button 1-8 | Mute corresponding channel | - |
| Bottom Button 1-8 | Solo corresponding channel | - |
| Prev | Previous 8 channels | Previous 1 channel |
| Next | Next 8 channels | Next 1 channel |
| Mute | Clear all mutes | - |
| Solo | Clear all solos | - |

---

### Pan Mode

**Access:** Pan/Send button (SHIFT+Pan/Send = Width mode)

| Control | Function | SHIFT Function |
|---------|----------|----------------|
| Encoder 1-8 | Channel 1-8 pan | Channel 1-8 width |
| Top Button 1-8 | Mute corresponding channel | - |
| Bottom Button 1-8 | Solo corresponding channel | - |
| Prev | Previous 8 channels | Previous 1 channel |
| Next | Next 8 channels | Next 1 channel |
| Mute | Clear all mutes | - |
| Solo | Clear all solos | - |

---

### Clip Mode

**Access:** Clip button (SHIFT+Clip = open Spectrum Visualizer)

**Display:**
- Line 1: Parameter names
- Line 2: Parameter values
- Line 3: Selected channel name, bank name
- Line 4: Bank names (Comp, Gate, EQ1, EQ2, FXs, Filters, Send1-4, Send5-8)

| Control | Function | SHIFT Function |
|---------|----------|----------------|
| Encoder 1-8 | Parameter (bank dependent) | - |
| Master Vol Encoder | Selected channel volume | - |
| Top Button 1-8 | Select bank | - |
| Bottom Button 1-8 | Toggle parameter | - |
| Prev | Previous channel | Previous 8 channels |
| Next | Next channel | Next 8 channels |
| Mute | Mute selected channel | - |
| Solo | Solo selected channel | - |

**Notes:** Controls full channel strip for selected mixer channel.

---

### Master Mode

**Access:** Master button

| Control | Function | SHIFT Function |
|---------|----------|----------------|
| Encoder 1-8 | Parameter (bank dependent) | - |
| Master Vol Encoder | Master volume | - |
| Top Button 1-8 | Select bank | - |
| Bottom Button 1-8 | Toggle parameter | - |
| Prev | *not used* | - |
| Next | *not used* | - |
| Mute | *not used* | - |
| Solo | *not used* | - |

**Notes:** Controls Master Section - bus compression, insert FX, send/return FX.

---

## Transport Controls

Located on left side of Push.

### Small Encoders (Left Side)

| Control | Default Function | Notes |
|---------|------------------|-------|
| Tempo Encoder | Adjust tempo (1 BPM per tick) | Mappable to other functions |
| Swing Encoder | Metronome volume | Mappable to other functions |

### Transport Buttons

| Control | Function | SHIFT Function |
|---------|----------|----------------|
| Tap Tempo | Tap to set tempo | - |
| Metronome | Metronome on/off | Pre-Count on/off |
| Undo | Undo | Redo |
| Delete | Delete | - |
| Double | Open keycommands page | - |
| Quantize | Quantize during recording on/off | Quantize selected notes |
| Fixed Length | Loop on/off | - |
| Automation | Automation recording on/off | - |
| Duplicate | Duplicate devices/tracks | - |
| New | Alternative Take (new lane, mutes previous) | New Overdub (new lane, keeps previous) |
| Rec | Record on/off | - |
| Play | Play/Stop | Return to start (when stopped) |

---

## Right Side Buttons

| Control | Function | SHIFT Function |
|---------|----------|----------------|
| Browse | Open patch browser | Tab (navigate browser areas) |
| Add Track | Open instruments browser | Create audio track |
| Add Effect | Open effects browser | - |
| Stop (in browse context) | Cancel/close browser | Enter/confirm selection |
| Cursor Up | Navigate up | Previous patch |
| Cursor Down | Navigate down | Next patch |
| Cursor Left | Navigate left | Previous track |
| Cursor Right | Navigate right / open folder | Next track |
| Scale | Open Scale settings page | Open TouchStrip/Layout settings |
| User | Toggle Live/Reason control | - |
| Repeat | Note repeat on/off | - |
| Accent | Fixed velocity on/off | - |
| Octave Down | Octave down | - |
| Octave Up | Octave up | - |
| Note | Enter Note Mode | 64 drum mode (Select+Note) |
| Session | Enter Session Mode | - |
| Select | Modifier (used with pads) | - |
| Shift | Modifier | Sticky shift (Select+Shift) |

---

## Note Mode

**Mode Selection:** Automatically switches submode based on selected device type.

### Generic Device Submode (Isomorphic Keyboard)

**Active for:** Synths, samplers, and all non-drum devices

| Control | Function | SHIFT Function |
|---------|----------|----------------|
| Pad Grid (8x8) | Play notes in isomorphic layout | - |
| Octave Up | Shift octave up | - |
| Octave Down | Shift octave down | - |
| Scale | Open scale selection page | Open layout/TouchStrip settings |
| Accent | Toggle fixed velocity (default 127) | - |
| Repeat | Note repeat on/off | - |
| Select + Note | Enter 64 drum mode | - |
| TouchStrip | Pitch bend (default) | - |

**Scale Settings Page (via Scale button):**
- Row 1-2: Scale type selection (25 scales available)
- Row 3-4: Root note selection (C through B)
- Button: Toggle In-Key / Chromatic mode

**Layout/TouchStrip Settings (via SHIFT+Scale):**

| Control | Function |
|---------|----------|
| Layout buttons | 4ths up, 4ths right, 3rds up, 3rds right |
| Encoder 2 | TouchStrip mode (PitchBend / Linear) |
| Encoder 4 | TouchStrip destination (PitchBend, ModWheel, Expression, Encoder 1-8) |
| Encoder 7 | Accent velocity adjustment |
| Encoder 8 | Pad brightness (Low/High) |

**Notes:** 
- Root note always in bottom-left corner
- Pads light up in response to incoming MIDI
- Default brightness configurable in Settings.json

---

### Kong Submode

**Active for:** Kong Drum Designer

| Control | Function | SHIFT Function |
|---------|----------|----------------|
| Pads 1-16 (bottom left 4x4) | Play 16 Kong pads | - |
| Pads 1-16 + Mute held | Mute corresponding pad | - |
| Pads 1-16 + Solo held | Solo corresponding pad | - |
| Pads 1-16 + Select held | Select drum for editing + assign to velocity pads | - |
| Velocity Pads (bottom right 4x4) | Play selected drum at 16 velocity levels | - |
| Group Pads (top right) Row 1 | Assign to Mute groups | - |
| Group Pads (top right) Row 2 | Assign to Link groups | - |
| Group Pads (top right) Row 3 | Assign to Alt groups | - |
| Mute | Modifier for pad muting | Clear all muted pads |
| Solo | Modifier for pad soloing | Clear all soloed pads |
| Select | Modifier for drum selection | - |

**Notes:** 
- Pads light up in response to sequencer playback
- Velocity pads: bottom-left = softest (1), top-right = loudest (127)

---

### Redrum Submode

**Active for:** Redrum Drum Computer

| Control | Function | SHIFT Function |
|---------|----------|----------------|
| Drum Pads (10 pads, left side) | Play 10 Redrum drums | - |
| Drum Pads + Mute held | Mute corresponding drum | - |
| Drum Pads + Solo held | Solo corresponding drum | - |
| Drum Pads + Select held | Select drum for step sequencing + velocity pads | - |
| Velocity Pads (4x4) | Play selected drum at 16 velocity levels | - |
| Pattern Pads (row of 8) | Select patterns 1-8 | - |
| Bank Pads (row of 4) | Select banks A-D | - |
| Step Sequencer Pads (4x4) | Edit 16 steps for selected drum | - |
| TouchStrip | Set accent level for step entry | - |

**TouchStrip Accent Levels:**
- Top position = Hard
- Middle position = Medium
- Bottom position = Soft

**Step Sequencer Encoders (Bank: Step):**

| Encoder | Parameter |
|---------|-----------|
| 1 | Run |
| 2 | Enable |
| 3 | Steps |
| 4 | Resolution |
| 5 | Drum |
| 6 | Steps (edit range: 1-16, 17-32, 33-48, 49-64) |
| 7 | Accent |
| 8 | Flam |

**Step Sequencer Encoders (Bank: Step2):**

| Encoder | Parameter |
|---------|-----------|
| 1 | Enable |
| 2 | Pattern |
| 3 | Bank |
| 4 | Step |
| 5 | Drum |
| 6 | Shuffle |
| 7 | Accent |
| 8 | Flam |

---

### Dr.OctoRex Submode

**Active for:** Dr.OctoRex Loop Player

| Control | Function | SHIFT Function |
|---------|----------|----------------|
| Slice Pads (left 4x8) | Play first 32 slices of selected loop | Access via SHIFT |
| Loop Trigger Pads (right 2x4) | Trigger loops 1-8 | - |

**Encoders:**

| Encoder | Parameter |
|---------|-----------|
| 1 | Enable |
| 2 | Run |
| 3 | TrigNext (trigger quantization) |
| 4 | LoopLvl (loop level) |
| 5 | LoopTr (loop transpose) |
| 6 | NoteSlot |
| 7 | LopSel (loop selection) |
| 8 | EditLoop |

**Notes:** Loop triggers follow TrigNext quantization setting.

---

## Session Mode

**Access:** Press Session button

| Control | Function | SHIFT Function |
|---------|----------|----------------|
| Section Pads (2 middle rows, 16 pads) | Jump to song section 1-16 | - |
| Beat Indicator (top row) | Visual feedback - illuminates on each beat | - |

**Behavior:**
- Each pad represents a song section
- Section length = loop brace length
- Loop brace must be at least 2 bars
- Pressing pad moves playhead and loop brace to that section
- Jump is quantized to the bar
- Order: top-left = section 1, bottom-right = section 16

**Notes:** Works best with Reason in standalone mode (not Rewire).

---

## Note Repeat

| Control | Function | SHIFT Function |
|---------|----------|----------------|
| Repeat Button | Toggle note repeat on/off | - |
| Rate Pads | Select subdivision | - |

**Available Subdivisions:**
- 1/4, 1/4T
- 1/8, 1/8T
- 1/16, 1/16T
- 1/32, 1/32T

**Behavior:**
- Velocity varies based on pad pressure (aftertouch)
- Polyphonic aftertouch for Kong, Redrum, Dr.OctoRex (each pad independent)
- Channel aftertouch for synths/samplers (last note played)
- Rates sync to Reason tempo
- Works in all Note Mode submodes

---

## Aftertouch / Pedals

| Control | Function |
|---------|----------|
| Pad Aftertouch (Kong, Redrum, Dr.OctoRex) | Poly pressure (per-pad) |
| Pad Aftertouch (synths, samplers) | Channel pressure (last note) |
| Sustain Pedal (Pedal Jack 1) | Sustain (CC64) |
| Expression Pedal (Pedal Jack 2) | Expression (CC11) |

---

## Keycommands

**Access:** Double button (requires Reason in foreground)

**Note:** Requires Java Runtime (32-bit) on Windows.

### Page 1

| Top Row | Function | Bottom Row | Function |
|---------|----------|------------|----------|
| Button 1 | Screens | Button 1 | Arrow/Snap |
| Button 2 | Blocks | Button 2 | Pencil/Follow |
| Button 3 | Edit Mode | Button 3 | Eraser/Copy |
| Button 4 | Tools | Button 4 | Razor/Paste |
| Button 5 | Zoom H | Button 5 | Mute/Select |
| Button 6 | Zoom V | Button 6 | Magnify/Quantize |
| Button 7 | Rec Meter | Button 7 | Hand/Shift |
| Button 8 | Playhead | Button 8 | Speaker/Cmd-Ctrl |

### Page 2 (via Next button)

| Top Row | Function | Bottom Row | Function |
|---------|----------|------------|----------|
| Button 1 | Random | Button 1 | Join Clip |
| Button 2 | Alter | Button 2 | Import Audio |
| Button 3 | ← Shift | Button 3 | New Bus |
| Button 4 | Shift → | Button 4 | New Song |
| Button 5 | Shift ↑ | Button 5 | Open |
| Button 6 | Shift ↓ | Button 6 | Save |
| Button 7 | Cut Pat | Button 7 | Close |
| Button 8 | - | Button 8 | Option |

---

## Enhancement Opportunities

Areas identified for potential improvements in open-push implementation. See [Potential New Features](#potential-new-features) for detailed proposals.

### Unused Controls

**Track Mode:**
- Encoders 6, 7, 8 unused
- Bottom Buttons 5-8 unused

**Master Mode:**
- Prev/Next buttons unused
- Mute/Solo buttons unused

### Behavioral Improvements

**Mute/Solo Consistency:**
- Current: Only functional in Volume Mode
- Proposed: Work on selected track in all modes; Volume Mode retains "clear all" behavior

**Redundant Controls:**
- Some encoder and button functions overlap
- Opportunity to reassign for more functionality

### New Capabilities (from Reason Remote SDK)

**Underutilized in PusheR:**
- Master Bus Compressor full control
- VU Metering (L/R/Gain Reduction) - could visualize on pads
- Control Room Level

See [Reason Remote SDK: Available Parameters](#reason-remote-sdk-available-parameters) for full list.

---

## Configuration

**Settings.json** (located in app Support folder):

```json
{
  "PushIN": "Ableton Push User Port",
  "PushOUT": "Ableton Push User Port",
  "ReasonIN": "from PusheR 1",
  "ReasonOUT": "to PusheR 1",
  "Brightness": "1"
}
```

- Brightness: "1" = Low, "2" = High

---

## Architecture & Philosophy

### The "Dumb Terminal" Concept

Push hardware knows nothing about modes, scales, or state. It simply reports events ("Pad 36 pressed", "Encoder 5 turned") and accepts commands ("Light pad 36 blue", "Display this text").

**The brain is external.** The middleware (open-push) is responsible for:
1. Receiving raw input from Push
2. Deciding what that input means in context (e.g., Pad 36 = "C#3" in current scale)
3. Telling Push how to respond visually (light the pad, update display)
4. Telling Reason what to do (play note, change parameter)

### The Bridge Architecture

```
┌─────────────┐      ┌─────────────────┐      ┌─────────────┐
│   Push 1    │ ──── │   open-push     │ ──── │   Reason    │
│  Hardware   │ MIDI │   (Middleware)  │ MIDI │    DAW      │
└─────────────┘      └─────────────────┘      └─────────────┘
     │                       │                       │
     │ Raw input             │ State machine         │ Remote protocol
     │ (pads, encoders)      │ Scale calculation     │ (parameters, transport)
     │                       │ Display formatting    │
     │ Display commands      │ Sequencer engine      │ Feedback values
     │ (sysex, LEDs)         │                       │ (0-127, strings)
```

### Data Flow Example

**Input flow (user presses pad):**
1. Push sends: "Pad 36 pressed, velocity 100"
2. open-push checks: Current mode? Scale? Octave?
3. open-push calculates: Pad 36 in C Minor = "D#3"
4. open-push sends to Reason: "Note On, D#3, velocity 100"

**Feedback flow (parameter changes):**
1. Reason sends: "Filter Cutoff = 64"
2. open-push converts: 64 → "50%" (or "1.2kHz" if frequency)
3. open-push formats: LCD line with parameter name and value
4. open-push sends to Push: SysEx display command

### Why This Architecture?

**Reason's limitations require it:**
- No file system access (can't browse folders)
- No sequencer data (can't read patterns)
- No waveform data (can't show audio)
- Only exposes: parameter values, device names, transport state

**Push 1's design assumes it:**
- Hardware has no onboard processing
- All state management is host-side
- Display is "write-only" (host sends text, hardware shows it)

**PusheR proved it works:**
- 10+ years of real-world use
- Full Reason integration via this exact approach
- Step sequencer runs entirely in middleware

---

## Push 1 Hardware Reference

### Physical Layout

**Pad Grid:** 8x8 velocity-sensitive pads with RGB LEDs

**Encoders (11 total):**
- 8 main encoders above display (touch-sensitive, endless rotary)
- 1 master volume encoder (right side, above main 8)
- 2 small encoders (left side, near transport):
  - Tempo encoder (BPM adjustment by default)
  - Swing encoder (Metronome volume by default)
- Note: Encoders send nothing by default; behavior is software-defined

**Display:** 4-line character LCD (68 characters total, 4 segments of 17 chars with gaps)
**Touch Strip:** Capacitive strip for pitch bend, modulation, or scrolling
**Buttons:** Mode selectors, transport, navigation, modifiers

### Native Modes (as designed for Live)

**Session Mode:** Grid launches clips (non-linear arrangement)
**Note Mode:** Grid becomes playable instrument
- *Instruments:* Isomorphic scale layout (4th intervals default). Root notes blue, in-key notes white.
- *Drums:* 3-section layout:
  - Bottom-left 4x4: Drum pads (play sounds)
  - Top 4 rows: Step sequencer (visual pattern)
  - Bottom-right: Loop length selector

### Hardware Communication

**MIDI Ports:**
- Port 1: "Live Port" - standard MIDI (notes, CC)
- Port 2: "User Port" - display control, LED control, raw pad data

**Display Protocol:** SysEx messages
- 4 lines × 4 segments = 16 addressable text areas
- Each segment: 17 characters max
- Physical gaps between segments (not continuous text)

**LCD Character Set (0-127):**
- 0-31: Special graphics (NOT control codes on Push LCD!)
- **Character 2 (STX) = solid block █** - Use for VU meters, progress bars
- 32-126: Standard ASCII printable characters
- 127: Special graphic

**LED Control:** Note messages with velocity = color/brightness

### Key Hardware Insight

Push's modes are **software constructs**. The hardware just reports:
- "Pad X pressed at velocity Y"
- "Encoder N turned Z clicks"
- "Button M pressed/released"

The software decides what these mean and how to respond.

---

## Implementation Architecture

Understanding how features are actually implemented - what happens in the middleware vs. what comes from Reason.

### The Core Architecture

The bridge application is the "brain" that sits between Push hardware and Reason. It handles:

1. **MIDI Routing**
   - Virtual Port Creation (IAC on Mac, LoopMIDI on Windows)
   - Separation of "User Port" (Display/Pads) from "DAW Port" (Notes/CC)

2. **State Machine**
   - Tracks: Current Mode, Current Scale, Current Bank, Selected Device
   - Listens for "Device Selected" messages from Reason to update LCD

3. **Display Driver**
   - Formats 4 lines of text (68 chars total, 4 segments of 17 chars)
   - Sends SysEx strings to Push
   - Maintains lookup tables for parameter names (e.g., convert `cc_71` to "Resonance")

4. **Sequencer Engine** (for Kong/Redrum step sequencing)
   - Completely standalone - runs in the middleware, NOT reading Reason's sequencer
   - Syncs to MIDI Clock (Start/Stop/Tick) from Reason
   - Holds sequence in its own memory
   - Fires "Note On" messages when MIDI clock matches the step

### What Happens Where

| Feature | Middleware | Reason Remote |
|---------|------------|---------------|
| Scale/Key selection | ✓ Calculates notes | - |
| Isomorphic layout | ✓ Maps pads to notes | - |
| Step sequencer (Kong/Redrum) | ✓ Runs entire sequence | Receives note triggers |
| LCD text | ✓ Generates all text | - |
| Parameter values | Formats display string | ✓ Sends raw values (0-127) |
| Device selection | Updates display | ✓ Sends device info |
| Transport | Passes through | ✓ Handles play/stop/rec |
| Mixer control | Routes to correct channel | ✓ Processes CC |

### Workarounds for Reason Limitations

**Patch Browsing:**
- Reason does NOT send file lists
- Workaround: Map encoders to `Select Next Patch` / `Select Previous Patch`
- User sees patch name change on LCD *after* it loads
- Functions as a "Blind Browser" - no preview, no folder navigation

**LCD Feedback:**
- Reason sends no graphics, only raw parameter values
- Workaround: Bridge writes all text directly to hardware
- State labels ("Mode: Scale", "Key: Cmin") are middleware-generated
- Parameter formatting: Bridge receives value `64`, converts to "50%" or "-3.2dB"

---

## Reason Remote SDK: Available Parameters

Features confirmed available in the Reason Remote API.

### Transport

| Parameter | Available | Notes |
|-----------|-----------|-------|
| Play | ✓ | |
| Stop | ✓ | |
| Record | ✓ | |
| Rewind | ✓ | |
| Fast Forward | ✓ | |
| Loop On/Off | ✓ | |
| Loop Start | ✓ | |
| Loop End | ✓ | |
| Click On/Off | ✓ | Metronome |
| Pre-Count On/Off | ✓ | |
| Tempo | ✓ | |
| Automation Write | ✓ | |
| New Dub | ✓ | Creates new Note Lane |
| New Alt | ✓ | Alternative Take |
| Input Quantize | ✓ | |
| Undo | ✓ | |
| Redo | ✓ | |

### Track/Device Navigation

| Parameter | Available | Notes |
|-----------|-----------|-------|
| Select Previous Track | ✓ | |
| Select Next Track | ✓ | |
| Target Track | ✓ | |
| Select Previous Patch | ✓ | Blind browsing |
| Select Next Patch | ✓ | Blind browsing |
| Device Parameters | ✓ | Auto-mapped to selected device |
| Device Banking | ✓ | Navigate parameter banks |

### Mixer (SSL)

| Parameter | Available | Notes |
|-----------|-----------|-------|
| Channel Volume | ✓ | |
| Channel Pan | ✓ | |
| Channel Width | ✓ | |
| Channel Mute | ✓ | |
| Channel Solo | ✓ | |
| Sends 1-8 | ✓ | |
| EQ LF Gain/Freq | ✓ | |
| EQ LMF Gain/Freq/Q | ✓ | |
| EQ HMF Gain/Freq/Q | ✓ | |
| EQ HF Gain/Freq | ✓ | |
| Compressor Threshold | ✓ | |
| Compressor Ratio | ✓ | |
| Gate Threshold | ✓ | |
| Insert FX | ✓ | Generic mapping |

### Master Section

| Parameter | Available | Notes |
|-----------|-----------|-------|
| Master Volume | ✓ | |
| Bus Compressor Threshold | ✓ | Underutilized in PusheR |
| Bus Compressor Ratio | ✓ | Underutilized in PusheR |
| Bus Compressor Makeup | ✓ | Underutilized in PusheR |
| Control Room Level | ✓ | |
| VU Meter L | ✓ | Returns 0-127 |
| VU Meter R | ✓ | Returns 0-127 |
| Gain Reduction | ✓ | Returns 0-127 |

### Devices (Native Instruments)

Full Remote support for:
- Subtractor
- Thor
- Malström
- NN-XT
- NN-19
- Kong
- Redrum
- Dr.OctoRex
- Europa
- Grain
- All effects devices
- Rack Extensions (varying support)

---

## Potential New Features

Features that are technically possible but not fully implemented in PusheR.

### VU Metering on Pads

**Source:** Reason exposes VU Meter L, VU Meter R, and Gain Reduction (0-127)

**Potential Implementation:**
- Use a column of pads to visualize meter levels
- Color gradient: Green (low) → Yellow (mid) → Red (high)
- Could show stereo meters (2 columns) or single summed meter
- Gain reduction could be shown as descending meter

**Where to put it:**
- Session Mode has unused pad rows
- Could be a toggle overlay in Volume Mode
- Could use the beat indicator row in Session Mode

### Enhanced Master Section Control

**Source:** Bus Compressor parameters are available but underutilized

**Potential Implementation:**
- Dedicated encoder bank for Master Bus Compressor
- Threshold, Ratio, Attack, Release, Makeup Gain
- Visual feedback for gain reduction on display or pads

### Track Mode Unused Encoders (6, 7, 8)

**Potential assignments:**
- Encoder 6: Tempo (currently only on transport encoder)
- Encoder 7: Time Signature numerator
- Encoder 8: Time Signature denominator
- Or: Swing amount, Click level, Pre-roll bars

### Track Mode Unused Buttons (5-8)

**Potential assignments:**
- Button 5: Tap Tempo
- Button 6: Click On/Off
- Button 7: Pre-Count On/Off
- Button 8: Automation Write toggle

### Global Mute/Solo Behavior

**Current limitation:** Mute/Solo buttons only work in Volume Mode

**Potential enhancement:**
- Mute/Solo work on currently selected track in ALL modes
- Volume Mode: Clear all mutes/solos (current behavior)
- All other modes: Mute/Solo selected track

---

## Hard Limits (Not Possible)

Features that cannot be implemented due to hardware or API limitations.

### Hardware Limits (Push 1)

| Feature | Reason |
|---------|--------|
| Pixel-level waveforms | Character LCD only (but block chars exist for VU meters!) |
| High-resolution graphics | 4 lines × 68 characters max |
| Full-color display feedback | Monochrome amber LCD |

**Note:** Character code 2 (STX) displays as a solid block █, enabling VU meters and progress bars.

### Reason API Limits

| Feature | Reason |
|---------|--------|
| Folder/file tree navigation | Reason doesn't expose file system |
| Patch preview before loading | No audio preview API |
| Device wiring/routing | Cannot create or modify connections |
| Plugin window control | Cannot open/close plugin GUIs |
| Clip/pattern visualization | Sequencer data not exposed |
| Waveform/sample display | Audio data not exposed |
| Real-time spectrum analysis | Not available via Remote |

### Architectural Limits

| Feature | Reason |
|---------|--------|
| True Reason sequencer editing | Step sequencer is middleware-only |
| Reading existing patterns | Reason doesn't expose pattern data |
| Syncing pad lights to sequencer playback | Only note triggers, not position |

---

## Configuration

**Settings.json** (located in app Support folder):

```json
{
  "PushIN": "Ableton Push User Port",
  "PushOUT": "Ableton Push User Port",
  "ReasonIN": "from PusheR 1",
  "ReasonOUT": "to PusheR 1",
  "Brightness": "1"
}
```

- Brightness: "1" = Low, "2" = High

---

## Document Info

- Based on: PusheR Getting Started Guide v1.1.8
- Feasibility Analysis: Reason Remote SDK review
- Target: open-push project
- Purpose: Foundation for implementation planning
