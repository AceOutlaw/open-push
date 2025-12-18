# open-push

Open-source tools for using Ableton Push hardware outside of Ableton Live.

## Why?

Ableton Push is incredible hardware - velocity-sensitive pads, endless encoders, a display, RGB LEDs - but it's locked to Ableton Live. Without Live running, Push just shows:

```
"Ableton Push - Please start Live to play..."
```

This means thousands of Push controllers are gathering dust because:
- People switched DAWs (Reason, Logic, Bitwig, Cubase, Studio One...)
- They want to use Push with other software
- They bought one used but don't have Live

**That's e-waste waiting to happen.**

Push 1 especially - released in 2013, still fully functional hardware, but increasingly abandoned as Ableton focuses on Push 2 and 3.

## The Vision

Bring the hands-on, tactile experience of Push to **any DAW**. The physical music-making process shouldn't be locked to one piece of software. Whether you use Reason, Logic, Bitwig, Cubase, Studio One, or anything else - Push should work for you.

**open-push** wakes up your Push and lets you use it as:
- A playable isomorphic keyboard with any DAW
- A general MIDI controller
- A deep DAW integration (Reason bridge mode, more DAWs planned)
- Whatever else you can imagine

## Current Features

### Isomorphic Controller (v0.2)
A fully playable MIDI instrument with Push.

- **Isomorphic layout** - Fourths-based (row +5, col +1 semitones)
- **6 scales** - Major, Minor, Dorian, Pentatonic, Blues, Chromatic
- **12 root notes** - C through B
- **In-Key mode** - All pads play scale notes (collapsed layout)
- **Chromatic mode** - Traditional layout with dim out-of-scale notes
- **Octave Up/Down** - Full range with LED feedback at limits
- **Accent mode** - Toggle fixed velocity (127)
- **Velocity curve** - Consistent response from light to hard touches
- **Plug-and-play** - Virtual MIDI port, no IAC Driver setup needed

### Display & LEDs
- Full LCD control (4 lines × 4 segments of 17 chars)
- Pad LED colors (velocity-based palette)
- Button LED control with proper solid/dim states

## Quick Start

```bash
# Install dependencies
pip3 install mido python-rtmidi

# Use Push as an isomorphic MIDI controller
python3 src/experiments/isomorphic_controller.py
```

### Connecting to Your DAW

**No manual MIDI setup required!** open-push automatically creates a virtual MIDI port.

1. Run `python3 src/experiments/isomorphic_controller.py`
2. In your DAW, select **"open-push"** as MIDI input
3. Play!

### Controls

| Button | Function |
|--------|----------|
| Octave Up/Down | Shift octave (LEDs off at limits) |
| Accent | Toggle fixed velocity (127) |
| Scale | Open scale settings page |

**Scale Settings Page:**
- Row 1-2: Select root note (C through B)
- Row 4: Select scale type
- Row 6: Toggle In-Key / Chromatic mode
- Press Scale again to exit

## Requirements

- macOS (Windows/Linux support planned)
- Python 3.x
- Ableton Push 1 (Push 2/3 support planned)

## Hardware Support

| Hardware | Status | Notes |
|----------|--------|-------|
| Push 1 | ✅ Working | Character LCD via MIDI SysEx |
| Push 2 | 🔜 Planned | Pixel display requires USB protocol |
| Push 3 | 🔜 Planned | Same as Push 2 |

The MIDI protocol (pads, buttons, encoders, LEDs) is the same across all versions. Only the display differs.

## DAW Support Roadmap

| DAW | Status | Notes |
|-----|--------|-------|
| Any (MIDI) | ✅ Working | Virtual port works with any DAW |
| Reason | 🔜 Planned | Deep integration via bridge mode |
| Logic Pro | 🔜 Planned | |
| Bitwig Studio | 🔜 Planned | |
| Cubase | 🔜 Planned | |
| Studio One | 🔜 Planned | |

## Project Structure

```
open-push/
├── README.md
├── docs/
│   ├── DEVLOG.md                  # Development history
│   ├── 00-project-overview.md
│   ├── 01-push-midi-protocol.md   # Complete Push MIDI reference
│   ├── 02-hardware-comparison.md  # Push 1 vs 2 vs 3
│   ├── 03-reason-remote-protocol.md
│   └── 04-understanding-midi-hardware.md
├── src/
│   └── experiments/
│       ├── isomorphic_controller.py  # Main playable controller
│       ├── push_wakeup.py            # Wake up + demo
│       ├── push_display.py           # LCD segment handling
│       ├── lcd_segment_test.py       # Display testing
│       └── color_explorer.py         # LED color testing
└── reference/                        # Reference files
```

## Key Discovery: LCD Segments

Push 1's display isn't a continuous 68-character line. It's **4 segments of 17 characters** with physical gaps:

```
|----Seg 0----|  |----Seg 1----|  |----Seg 2----|  |----Seg 3----|
   17 chars         17 chars         17 chars         17 chars
```

## Contributing

This is an open project. Help welcome:
- Test on your hardware
- Add features
- Improve documentation
- Port to other platforms
- Add DAW-specific integrations

## License

MIT

## Acknowledgments

- Ableton for the Push hardware and publishing Push 2 docs
- RetouchControl for PusheR (the original inspiration)
- The music tech community for protocol research
