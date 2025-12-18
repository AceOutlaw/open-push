# Ableton Push Hardware Comparison

This document compares Push 1, Push 2, and Push 3 hardware, focusing on the technical differences relevant to building a bridge application.

## Quick Comparison

| Feature | Push 1 | Push 2 | Push 3 |
|---------|--------|--------|--------|
| **Release Year** | 2013 | 2015 | 2023 |
| **Manufacturer** | Akai (for Ableton) | Ableton | Ableton |
| **Display** | Character LCD (4×68) | Pixel LCD (960×160) | Pixel LCD (960×160) |
| **Display Interface** | MIDI SysEx | USB (raw frames) | USB (raw frames) |
| **Pad Grid** | 8×8 RGB | 8×8 RGB | 8×8 RGB |
| **MIDI Protocol** | Compatible | Compatible | Compatible |
| **Connection** | USB | USB | USB / WiFi / Ethernet |
| **Standalone** | No | No | Yes (with Push 3 Standalone) |

---

## Push 1

### Overview

Push 1 was Ableton's first hardware controller, manufactured by Akai Professional. It established the fundamental layout and workflow that continues through all Push versions.

### Display System

**Type**: Character-based LCD
**Resolution**: 4 lines × 68 characters
**Character Size**: 8×5 red LED pixels per character
**Interface**: MIDI System Exclusive (SysEx)

The LCD on Push 1 is controlled entirely through MIDI SysEx messages, making it accessible from any application that can send MIDI.

### SysEx Protocol

**Text Display:**
```
F0 47 7F 15 [line] 00 45 00 [68 ASCII bytes] F7
```

Line values: 0x18 (line 1), 0x19 (line 2), 0x1A (line 3), 0x1B (line 4)

**Mode Switch:**
```
F0 47 7F 15 62 00 01 [mode] F7    // mode: 00=Live, 01=User
```

**RGB Color (per pad):**
```
F0 47 7F 15 04 00 08 [pad] 00 [rHi] [rLo] [gHi] [gLo] [bHi] [bLo] F7
```

### MIDI Ports

- **Ableton Push Live Port** - Used by Ableton Live
- **Ableton Push User Port** - Available for third-party use

### Key Characteristics

- All control via MIDI (including display)
- Character-based display is easy to program
- Full RGB pad colors available
- Mature, well-documented through reverse engineering
- No longer manufactured (discontinued 2015)

---

## Push 2

### Overview

Push 2 introduced a significant upgrade with a high-resolution color display. The MIDI mapping remains compatible with Push 1, but the display requires a completely different approach.

### Display System

**Type**: Pixel-based LCD
**Resolution**: 960 × 160 pixels
**Color Depth**: 16-bit (RGB565)
**Interface**: USB bulk transfer (not MIDI)

The Push 2 display is essentially a small monitor that expects raw pixel data via USB. It cannot render text or graphics itself - the host application must send complete frames.

### Display Protocol

The display connects as a **USB Bulk Transfer endpoint**, not a MIDI device. To update the display:

1. Open USB device (Vendor ID: 0x2982, Product ID: 0x1967)
2. Send 160 scanlines of 960 pixels each
3. Each pixel is 16-bit RGB565 format
4. Frame rate typically 60 FPS for smooth animation

**This is fundamentally different from Push 1** - you cannot simply send text strings. You must:
- Render text/graphics in your application
- Convert to RGB565 pixel format
- Stream frames via USB

### MIDI Compatibility

Despite the display differences, the MIDI mapping for pads, buttons, encoders, and LEDs is **compatible with Push 1**:

- Same note numbers for pads (36-99)
- Same CC numbers for buttons
- Same encoder CC/note assignments
- Same color palette (velocity values)

### MIDI Ports

- **Ableton Push 2 Live Port**
- **Ableton Push 2 User Port**

### Key Characteristics

- MIDI controls compatible with Push 1
- Display requires USB programming (not MIDI)
- Higher quality pads with better velocity response
- Better build quality overall
- Still being manufactured

---

## Push 3

### Overview

Push 3 comes in two versions: a controller version (like Push 1/2) and a standalone version with built-in computer. Both share the same control surface and MIDI protocol.

### Display System

**Type**: Pixel-based LCD (same as Push 2)
**Resolution**: 960 × 160 pixels
**Interface**: USB bulk transfer

The display protocol is essentially the same as Push 2.

### Connection Options

Push 3 adds network connectivity:

| Connection | Description |
|------------|-------------|
| USB | Standard wired connection |
| WiFi | Wireless connection to computer |
| Ethernet | Wired network connection |

### Standalone Version

The Push 3 Standalone includes:
- Intel processor
- Ableton Live built-in
- Audio interface
- Storage for projects

When used standalone, no bridge application is needed for Ableton Live. However, using it with Reason would still require a bridge running on the Push 3 itself or a connected computer.

### MIDI Compatibility

The MIDI protocol remains compatible with Push 1 and Push 2:

- Same pad note numbers
- Same button CC numbers
- Same encoder assignments
- Same color palette system

### Key Characteristics

- MIDI controls compatible with Push 1/2
- Display protocol same as Push 2
- Network connectivity options
- Standalone capability (Standalone version)
- Current flagship product

---

## Comparison Matrix: Bridge Development

### What's the Same (All Versions)

| Feature | Notes |
|---------|-------|
| Pad note numbers | 36-99, same layout |
| Button CC numbers | All button mappings identical |
| Encoder CC/Note | Same assignments |
| LED color palette | Same velocity-based colors |
| Touch strip | Same pitch bend + note touch |
| Aftertouch | Same channel/poly pressure |

### What's Different

| Feature | Push 1 | Push 2 | Push 3 |
|---------|--------|--------|--------|
| Display control | MIDI SysEx (easy) | USB frames (complex) | USB frames (complex) |
| Display text | Send ASCII via SysEx | Render + stream pixels | Render + stream pixels |
| Display graphics | Limited characters | Full pixel control | Full pixel control |
| USB identifiers | Akai VID/PID | Ableton VID/PID | Ableton VID/PID |
| Network | No | No | Yes |

---

## Development Strategy

### Push 1 First (Recommended)

Starting with Push 1 makes sense because:

1. **Simpler display protocol** - Just send text via MIDI SysEx
2. **Fully MIDI-based** - No USB bulk transfer needed
3. **Well-documented** - 10+ years of community reverse engineering
4. **Matches original PusheR** - Can directly compare behavior

### Push 2/3 Display Support

Adding Push 2/3 display support is a significant undertaking:

1. **USB Library Required** - libusb or platform-specific USB APIs
2. **Frame Rendering** - Must render text/graphics to pixel buffer
3. **Color Conversion** - Convert RGB to RGB565 format
4. **Frame Streaming** - Maintain 60 FPS for smooth display
5. **Font Rendering** - Need font library or pre-rendered glyphs

### Abstraction Layer

To support multiple Push versions, create an abstraction:

```
┌─────────────────────────────────────────┐
│          Display Interface              │
│  - show_text(line, text)                │
│  - show_parameter(name, value)          │
│  - clear()                              │
└─────────────────────────────────────────┘
           │                    │
           ▼                    ▼
┌─────────────────┐   ┌─────────────────┐
│  Push1Display   │   │  Push2Display   │
│  (MIDI SysEx)   │   │  (USB Frames)   │
└─────────────────┘   └─────────────────┘
```

The MIDI control layer can be shared, with only the display implementation varying by hardware version.

---

## USB Device Identification

### Push 1
- **Vendor ID**: 0x09E8 (Akai)
- **Product ID**: Varies by firmware

### Push 2
- **Vendor ID**: 0x2982 (Ableton)
- **Product ID**: 0x1967

### Push 3
- **Vendor ID**: 0x2982 (Ableton)
- **Product ID**: Check current firmware documentation

---

## Sources

- [Ableton Push Interface (Official)](https://github.com/Ableton/push-interface)
- [Push 1/2 Compatibility Discussion](https://github.com/Ableton/push-interface/issues/19)
- [Push 2 Display Protocol](https://github.com/Ableton/push-interface/blob/main/doc/AbletonPush2MIDIDisplayInterface.asc)
- [Push 3 Manual](https://www.ableton.com/en/push/manual/)
- Community reverse engineering (Cycling74, Ableton Forums)
