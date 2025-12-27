# open-push

Open-source tools for using Ableton Push hardware with any DAW or music software.

## Why?

Ableton Push is incredible hardware - velocity-sensitive pads, endless encoders, a display, RGB LEDs - but it's locked to Ableton Live. Without Live running, Push just shows:

```
"Ableton Push - Please start Live to play..."
```

This means thousands of Push controllers are gathering dust because:
- People switched DAWs (Reason, Logic, Bitwig, Cubase...)
- They want to use Push with other software (grooveboxes, samplers, synths)
- They bought one used but don't have Live

**That's e-waste waiting to happen.**

Push 1 especially - released in 2013, still fully functional hardware, but increasingly abandoned as Ableton focuses on Push 2 and 3.

## The Vision

Bring Push's hands-on, tactile control to **any music software**. The physical music-making experience shouldn't be locked to one piece of software.

**open-push** wakes up your Push and lets you use it with:
- Any DAW via MIDI (Reason, Logic, Bitwig, Cubase, Studio One...)
- Standalone hardware (Yamaha Seqtrak, grooveboxes, synths...)
- Custom integrations (your own software)
- Whatever else you can imagine

## Current Integrations

### Reason Bridge
Full integration with Propellerhead Reason Studios via Lua Remote codecs.

**Features:**
- ✅ Isomorphic keyboard with 40+ scales
- ✅ Scale mode with chromatic root selection
- ✅ Octave shifting
- ✅ Transport controls (Play/Stop/Record)
- ✅ Virtual MIDI ports (no IAC Driver setup)
- 🔜 Device control
- 🔜 Mixer mode

**Quick Start:**
```bash
python3 src/open_push/reason/app.py
```

### Seqtrak Bridge
Complete control of Yamaha Seqtrak groovebox from Push. **Deployed on Raspberry Pi for standalone, headless operation.**

**Features:**
- ✅ Full hardware control via MIDI SysEx protocol
- ✅ Step sequencer editing (11 tracks: 7 drum, 3 melodic, 1 sampler)
- ✅ Pattern/variation launching (6 variations per track)
- ✅ Mixer mode (volume, mute, solo per track)
- ✅ Device mode (preset selection and navigation)
- ✅ Note repeat
- ✅ Sample recording via USB audio
- ✅ **Raspberry Pi deployment** (auto-start on boot, headless)

**Quick Start:**
```bash
# Run locally
python3 src/open_push/seqtrak/app.py

# Raspberry Pi - auto-starts on boot, no setup needed
```

**Raspberry Pi Deployment:**
- Headless operation (no monitor/keyboard required)
- Auto-start on boot via systemd service
- USB audio routing (Push → Seqtrak for sampling)
- SSH access for updates and monitoring
- ~45 second startup time
- Portable standalone rig (Push + Seqtrak + Pi)

## Hardware Support

| Hardware | Status | Notes |
|----------|--------|-------|
| **Push 1** | ✅ Full support | Character LCD via MIDI SysEx |
| **Push 2/3** | 🔜 Planned | Pixel display requires USB protocol |
| **Yamaha Seqtrak** | ✅ Full support | Complete SysEx protocol implementation |
| **Reason Studios** | ✅ Working | Lua Remote codec integration |

The MIDI protocol (pads, buttons, encoders, LEDs) is the same across Push 1/2/3. Only the display differs.

## Installation

### Dependencies

```bash
pip3 install mido python-rtmidi
```

### Platform Support
- **macOS** - Full support
- **Linux** - Full support (including Raspberry Pi)
- **Windows** - Planned

### Hardware Requirements
- Ableton Push 1 (Push 2/3 support planned)
- Target device (Yamaha Seqtrak, Reason DAW, etc.)
- For Pi deployment: Raspberry Pi 4 or newer

## Quick Examples

### Basic MIDI Controller
Use Push as an isomorphic keyboard with any DAW:

```bash
python3 src/open_push/reason/app.py
# Select "open-push" as MIDI input in your DAW
```

### Seqtrak Control
Full hands-on control of Yamaha Seqtrak:

```bash
python3 src/open_push/seqtrak/app.py
# Push becomes a dedicated Seqtrak controller
```

### Reason Integration
Deep integration with Reason Studios:

```bash
# Install codecs
./src/open_push/reason/codecs/install_codecs.sh

# Run bridge
python3 src/open_push/reason/app.py
```

## Project Structure

```
open-push/
├── src/open_push/
│   ├── reason/              # Reason Studios bridge
│   │   ├── app.py           # Main application
│   │   └── codecs/          # Lua Remote codecs
│   ├── seqtrak/             # Yamaha Seqtrak bridge
│   │   ├── app.py           # Main application
│   │   ├── protocol.py      # SysEx protocol implementation
│   │   └── presets.py       # Preset name lookups
│   ├── music/               # Shared music theory
│   │   ├── layout.py        # Isomorphic keyboard layouts
│   │   └── scales.py        # Scale definitions
│   └── push/                # Push hardware abstraction
│       ├── display.py       # LCD control
│       └── pads.py          # Pad LED control
├── docs/                    # Documentation
│   ├── Reason/              # Reason-specific docs
│   ├── Seqtrak/             # Seqtrak protocol reference
│   └── *.md                 # General hardware reference
└── README.md
```

## Key Discoveries

### Push 1 LCD Segments
Push 1's display isn't a continuous 68-character line. It's **4 segments of 17 characters** with physical gaps:

```
|----Seg 0----|  |----Seg 1----|  |----Seg 2----|  |----Seg 3----|
   17 chars         17 chars         17 chars         17 chars
```

This affects text layout and alignment - important for clean display formatting.

### Seqtrak SysEx Protocol
Full reverse-engineered MIDI SysEx protocol for Yamaha Seqtrak, documented in `docs/Seqtrak/sysex-protocol-reference.md`. Enables complete hardware control without Seqtrak's iOS app.

## Roadmap

### Near Term
- [ ] Push 2/3 support (USB display protocol)
- [ ] More DAW integrations (Logic, Bitwig, Cubase)
- [ ] Standalone mode (no computer, just Push + synth)
- [ ] Windows support

### Future
- [ ] Deep sampler integration (Elektron, MPC)
- [ ] Modular synth control (VCV Rack, Eurorack)
- [ ] Custom MIDI mapping engine
- [ ] Multi-device support (control multiple devices)

## Contributing

This is an open project. Contributions welcome:
- Test on your hardware
- Add new integrations (DAWs, hardware, software)
- Improve documentation
- Port to other platforms
- Report bugs and request features


## Documentation

- **General**: `docs/open-push-master-reference.md` - Complete Push 1 hardware reference
- **Reason**: `docs/Reason/reason-bridge-reference.md` - Reason integration guide
- **Seqtrak**: `docs/Seqtrak/sysex-protocol-reference.md` - Complete SysEx protocol
- See `docs/` for additional integration guides and protocol documentation

## License

MIT

## Acknowledgments

- **Ableton** for the Push hardware and publishing Push 2 docs
- **Yamaha** for publishing the complete Seqtrak MIDI specification
- **Propellerhead** for the Reason Remote SDK
- **RetouchControl** for PusheR (the original inspiration)
- The music tech community for protocol research and reverse engineering
