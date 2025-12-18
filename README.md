# open-push

Open-source tools for using Ableton Push hardware outside of Ableton Live.

## Why?

Ableton Push is incredible hardware - velocity-sensitive pads, endless encoders, a display, RGB LEDs - but it's locked to Ableton Live. Without Live running, Push just shows:

```
"Ableton Push - Please start Live to play..."
```

This means thousands of Push controllers are gathering dust because:
- People switched DAWs
- They want to use Push with other software
- They bought one used but don't have Live

**That's e-waste waiting to happen.**

Push 1 especially - released in 2013, still fully functional hardware, but increasingly abandoned as Ableton focuses on Push 2 and 3.

## What This Project Does

**open-push** wakes up your Push and lets you use it as:
- A general MIDI controller with any DAW or software
- An isomorphic keyboard with customizable layouts
- A controller for Reason (via bridge to PusheR-style codecs)
- Whatever else you can imagine

## Current Status

**Working now:**
- Wake up Push 1 without Ableton
- Full LCD display control (4 lines × 4 segments)
- Pad LED colors (full palette)
- Button LED control
- Isomorphic keyboard layout (C minor, fourths)
- MIDI output to virtual ports (IAC Driver)

**In progress:**
- Reason DAW integration (bridge mode)
- More scale/layout options
- Button functionality

## Quick Start

```bash
# Install dependencies
pip3 install mido python-rtmidi

# Wake up Push and see it light up
python3 src/experiments/push_wakeup.py

# Use Push as an isomorphic MIDI controller
python3 src/experiments/isomorphic_controller.py
```

### Requirements
- macOS (Windows/Linux support planned)
- Python 3.x
- Ableton Push 1 (Push 2/3 support planned)

### Connecting to Your DAW

**No manual MIDI setup required!** When you run open-push, it automatically creates a virtual MIDI port called `open-push`. Just select it as a MIDI input in your DAW.

1. Run `python3 src/experiments/isomorphic_controller.py`
2. In your DAW, select **"open-push"** as MIDI input
3. Play!

## Hardware Support

| Hardware | Status | Notes |
|----------|--------|-------|
| Push 1 | ✅ Working | Character LCD via MIDI SysEx |
| Push 2 | 🔜 Planned | Pixel display requires USB protocol |
| Push 3 | 🔜 Planned | Same as Push 2 |

The MIDI protocol (pads, buttons, encoders, LEDs) is the same across all versions. Only the display differs.

## Project Structure

```
open-push/
├── README.md
├── docs/                           # Protocol documentation
│   ├── 00-project-overview.md
│   ├── 01-push-midi-protocol.md    # Complete Push MIDI reference
│   ├── 02-hardware-comparison.md   # Push 1 vs 2 vs 3
│   ├── 03-reason-remote-protocol.md
│   └── 04-understanding-midi-hardware.md
├── src/
│   └── experiments/                # Working scripts
│       ├── push_wakeup.py          # Wake up + demo
│       ├── push_display.py         # LCD segment handling
│       ├── isomorphic_controller.py # Playable MIDI controller
│       ├── lcd_segment_test.py     # Display testing
│       └── color_explorer.py       # LED color testing
└── reference/                      # Original PusheR files (if available)
```

## Documentation

Detailed protocol docs in `/docs`:

- **Push MIDI Protocol** - Complete reference for pads, buttons, encoders, LEDs, LCD
- **Hardware Comparison** - Differences between Push 1, 2, and 3
- **Reason Integration** - How to bridge Push to Reason DAW

## Key Discovery: LCD Segments

Push 1's display isn't a continuous 68-character line. It's **4 segments of 17 characters** with physical gaps:

```
|----Seg 0----|  |----Seg 1----|  |----Seg 2----|  |----Seg 3----|
   17 chars         17 chars         17 chars         17 chars
```

The `push_display.py` module handles this properly.

## Contributing

This is an open project. Help welcome:
- Test on your hardware
- Add features
- Improve documentation
- Port to other platforms

## License

MIT (TBD)

## Acknowledgments

- Ableton for the Push hardware and publishing Push 2 docs
- RetouchControl for PusheR (inspiration for Reason integration)
- The music tech community for protocol research
