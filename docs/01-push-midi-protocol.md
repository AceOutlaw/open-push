# Ableton Push MIDI Protocol Reference

This document contains the complete MIDI protocol specifications for Ableton Push hardware controllers, with a focus on Push 1 (our primary target) and notes on Push 2/3 compatibility.

## Table of Contents

1. [Protocol Overview](#protocol-overview)
2. [MIDI Ports](#midi-ports)
3. [Pad Grid Mapping](#pad-grid-mapping)
4. [Button Mapping (CC)](#button-mapping-cc)
5. [Encoder Mapping](#encoder-mapping)
6. [Touch Strip](#touch-strip)
7. [LED Color Control](#led-color-control)
8. [Push 1 LCD Display (SysEx)](#push-1-lcd-display-sysex)
9. [Mode Switching](#mode-switching)
10. [Aftertouch](#aftertouch)

---

## Protocol Overview

### Message Types Used

| Message Type | Status Byte | Purpose |
|--------------|-------------|---------|
| Note On | 0x90 | Pad press, LED color, encoder touch |
| Note Off | 0x80 | Pad release, encoder release |
| Control Change | 0xB0 | Button press/release, encoder turn, LED color |
| Pitch Bend | 0xE0 | Touch strip position |
| Channel Pressure | 0xD0 | Global pad aftertouch |
| Poly Key Pressure | 0xA0 | Per-pad aftertouch |
| System Exclusive | 0xF0 | LCD display, mode switch, RGB colors |

### Compatibility Notes

According to Ableton's documentation, **Note and Control Change messages are compatible between Push 1 and Push 2**. The primary differences are:

- **Push 1**: Character-based LCD display via SysEx (4 lines x 68 characters)
- **Push 2/3**: Pixel-based display via USB (960x160, not MIDI)

This means the pad, button, and encoder mappings documented here work across all Push versions.

---

## MIDI Ports

Push exposes two MIDI port pairs:

| Port | Purpose |
|------|---------|
| **Ableton Push Live Port** | Used exclusively by Ableton Live |
| **Ableton Push User Port** | Available for third-party applications |

**Important**: Only one application can access a port at a time. For our bridge application, we use the **User Port**.

---

## Pad Grid Mapping

The 8x8 pad grid sends **Note messages** with note numbers 36-99.

### Layout (Note Numbers)

```
         Col 1   Col 2   Col 3   Col 4   Col 5   Col 6   Col 7   Col 8
        ┌───────┬───────┬───────┬───────┬───────┬───────┬───────┬───────┐
Row 8   │  92   │  93   │  94   │  95   │  96   │  97   │  98   │  99   │  (top)
        ├───────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┤
Row 7   │  84   │  85   │  86   │  87   │  88   │  89   │  90   │  91   │
        ├───────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┤
Row 6   │  76   │  77   │  78   │  79   │  80   │  81   │  82   │  83   │
        ├───────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┤
Row 5   │  68   │  69   │  70   │  71   │  72   │  73   │  74   │  75   │
        ├───────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┤
Row 4   │  60   │  61   │  62   │  63   │  64   │  65   │  66   │  67   │
        ├───────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┤
Row 3   │  52   │  53   │  54   │  55   │  56   │  57   │  58   │  59   │
        ├───────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┤
Row 2   │  44   │  45   │  46   │  47   │  48   │  49   │  50   │  51   │
        ├───────┼───────┼───────┼───────┼───────┼───────┼───────┼───────┤
Row 1   │  36   │  37   │  38   │  39   │  40   │  41   │  42   │  43   │  (bottom)
        └───────┴───────┴───────┴───────┴───────┴───────┴───────┴───────┘
```

### Calculating Note Number

```
note_number = 36 + (row * 8) + column
```

Where `row` and `column` are 0-indexed (row 0 = bottom, column 0 = left).

### Message Format

**Pad Pressed:**
```
0x90 [note] [velocity]    // Note On, velocity 1-127 based on pressure
```

**Pad Released:**
```
0x80 [note] 0x00          // Note Off
```

---

## Button Mapping (CC)

All buttons (except the pad grid) send **Control Change messages**.

### Transport Controls

| Button | CC # | Hex |
|--------|------|-----|
| Tap Tempo | 3 | 0x03 |
| Metronome | 9 | 0x09 |
| Stop | 29 | 0x1D |
| Play | 85 | 0x55 |
| Record | 86 | 0x56 |

### Editing Controls

| Button | CC # | Hex |
|--------|------|-----|
| New | 87 | 0x57 |
| Duplicate | 88 | 0x58 |
| Fixed Length | 90 | 0x5A |
| Quantize | 116 | 0x74 |
| Double Loop | 117 | 0x75 |
| Delete | 118 | 0x76 |
| Undo | 119 | 0x77 |

### Navigation Controls

| Button | CC # | Hex |
|--------|------|-----|
| Left | 44 | 0x2C |
| Right | 45 | 0x2D |
| Up | 46 | 0x2E |
| Down | 47 | 0x2F |
| Page Left | 62 | 0x3E |
| Page Right | 63 | 0x3F |

### Mode Buttons

| Button | CC # | Hex |
|--------|------|-----|
| Select | 48 | 0x30 |
| Shift | 49 | 0x31 |
| Note | 50 | 0x32 |
| Session | 51 | 0x33 |
| User | 59 | 0x3B |
| Mute | 60 | 0x3C |
| Solo | 61 | 0x3D |
| Device | 110 | 0x6E |
| Browse | 111 | 0x6F |
| Mix | 112 | 0x70 |
| Clip | 113 | 0x71 |
| Master | 28 | 0x1C |
| Setup | 30 | 0x1E |

### Upper Button Row (Above Display)

| Position | CC # | Hex |
|----------|------|-----|
| Upper 1 | 102 | 0x66 |
| Upper 2 | 103 | 0x67 |
| Upper 3 | 104 | 0x68 |
| Upper 4 | 105 | 0x69 |
| Upper 5 | 106 | 0x6A |
| Upper 6 | 107 | 0x6B |
| Upper 7 | 108 | 0x6C |
| Upper 8 | 109 | 0x6D |

### Lower Button Row (Below Encoders)

| Position | CC # | Hex |
|----------|------|-----|
| Lower 1 | 20 | 0x14 |
| Lower 2 | 21 | 0x15 |
| Lower 3 | 22 | 0x16 |
| Lower 4 | 23 | 0x17 |
| Lower 5 | 24 | 0x18 |
| Lower 6 | 25 | 0x19 |
| Lower 7 | 26 | 0x1A |
| Lower 8 | 27 | 0x1B |

### Note Length Buttons (if present)

| Button | CC # | Hex |
|--------|------|-----|
| 1/4 | 36 | 0x24 |
| 1/4t | 37 | 0x25 |
| 1/8 | 38 | 0x26 |
| 1/8t | 39 | 0x27 |
| 1/16 | 40 | 0x28 |
| 1/16t | 41 | 0x29 |
| 1/32 | 42 | 0x2A |
| 1/32t | 43 | 0x2B |

### Message Format

**Button Pressed:**
```
0xB0 [cc#] 0x7F           // CC value 127
```

**Button Released:**
```
0xB0 [cc#] 0x00           // CC value 0
```

---

## Encoder Mapping

Push has 11 rotary encoders with touch sensitivity.

### Encoder Assignments

| Encoder | CC # (Turn) | Note # (Touch) |
|---------|-------------|----------------|
| Tempo | 14 | 10 |
| Swing | 15 | 9 |
| Track 1 | 71 | 0 |
| Track 2 | 72 | 1 |
| Track 3 | 73 | 2 |
| Track 4 | 74 | 3 |
| Track 5 | 75 | 4 |
| Track 6 | 76 | 5 |
| Track 7 | 77 | 6 |
| Track 8 | 78 | 7 |
| Master | 79 | 8 |

### Message Format

**Encoder Turn (Relative):**
```
0xB0 [cc#] [delta]        // delta: 1-64 = clockwise, 65-127 = counter-clockwise
```

The encoders use **relative mode** (2's complement):
- Values 1-63: Clockwise rotation (1 = slow, 63 = fast)
- Values 65-127: Counter-clockwise rotation (127 = slow, 65 = fast)

**Encoder Touch:**
```
0x90 [note#] 0x7F         // Touch start (velocity 127)
0x90 [note#] 0x00         // Touch end (velocity 0)
```

---

## Touch Strip

The touch strip sends position data via Pitch Bend and touch detection via Note.

### Messages

**Position (continuous):**
```
0xE0 [LSB] [MSB]          // 14-bit pitch bend value
```

**Touch Detection:**
```
0x90 0x0C 0x7F            // Touch start (Note 12, velocity 127)
0x90 0x0C 0x00            // Touch end (Note 12, velocity 0)
```

---

## LED Color Control

LED colors are set by sending messages TO the Push with velocity/value indicating color.

### Pad LEDs (Note Messages)

```
0x90 [note] [color]       // Set pad LED to color index
```

### Button LEDs (CC Messages)

```
0xB0 [cc#] [color]        // Set button LED to color index
```

### Color Palette (Velocity/Value)

| Color | Index | Variations |
|-------|-------|------------|
| Off/Black | 0 | - |
| Dark Grey | 1 | - |
| Grey | 2 | - |
| White | 3 | - |
| Red | 5, 6, 7 | bright, normal, dim |
| Orange | 9, 10, 11 | bright, normal, dim |
| Yellow | 13, 14, 15 | bright, normal, dim |
| Lime | 17, 18, 19 | bright, normal, dim |
| Green | 21, 22, 23 | bright, normal, dim |
| Spring | 25, 26, 27 | bright, normal, dim |
| Turquoise | 29, 30, 31 | bright, normal, dim |
| Cyan | 33, 34, 35 | bright, normal, dim |
| Sky | 37, 38, 39 | bright, normal, dim |
| Ocean | 41, 42, 43 | bright, normal, dim |
| Blue | 45, 46, 47 | bright, normal, dim |
| Orchid | 49, 50, 51 | bright, normal, dim |
| Magenta | 53, 54, 55 | bright, normal, dim |
| Pink | 57, 58, 59 | bright, normal, dim |

### Push 1 RGB SysEx (Direct Color)

For precise color control on Push 1 pads:

```
F0 47 7F 15 04 00 08 [pad] 00 [rHi] [rLo] [gHi] [gLo] [bHi] [bLo] F7
```

Where:
- `pad` = (row × 8) + column (0-63, bottom-left = 0)
- RGB values are split into 4-bit nibbles (high/low)

---

## Push 1 LCD Display (SysEx)

**This section applies to Push 1 only.** Push 2/3 use USB-based pixel displays.

### Display Specifications

- 4 lines of text
- 68 characters per line
- Character-based (not pixels)
- Orange/amber LED dot matrix

### Physical Segment Layout (IMPORTANT)

The 68 characters per line are physically divided into **4 segments of 17 characters** with visible gaps between them. These gaps align with the encoder pairs above.

```
|----Segment 0----|  |----Segment 1----|  |----Segment 2----|  |----Segment 3----|
    chars 0-16           chars 17-33          chars 34-50          chars 51-67
     17 chars             17 chars             17 chars             17 chars
```

**This means text flows continuously but displays with gaps.** If you write "Hello World" starting at position 14, it will appear as "Hel" in segment 0 and "lo World" in segment 1 with a physical gap between them.

For clean display, format text into 17-character segments or 8-character fields (for encoder labels).

### Text Message Format (77 bytes)

```
F0 47 7F 15 [line] 00 45 00 [68 ASCII bytes] F7
```

**Header breakdown:**
- `F0` - SysEx start
- `47 7F 15` - Ableton/Push manufacturer ID
- `[line]` - Line number (see below)
- `00 45 00` - Command parameters
- `[68 bytes]` - ASCII text (padded with spaces if shorter)
- `F7` - SysEx end

### Line Numbers

| Line | Decimal | Hex |
|------|---------|-----|
| Line 1 (top) | 24 | 0x18 |
| Line 2 | 25 | 0x19 |
| Line 3 | 26 | 0x1A |
| Line 4 (bottom) | 27 | 0x1B |

### Character Set

- Values 32-126: Standard ASCII printable characters
- Values 0-31, 127: Device-specific special characters
- All 128 values (0-127) produce visible characters on the LCD

### Example: Display "Hello World" on Line 1

```python
# Python example
sysex = [0xF0, 0x47, 0x7F, 0x15, 0x18, 0x00, 0x45, 0x00]
text = "Hello World".ljust(68)  # Pad to 68 characters
sysex.extend([ord(c) for c in text])
sysex.append(0xF7)
```

---

## Mode Switching

### Push 1 Mode SysEx

**Switch to User Mode:**
```
F0 47 7F 15 62 00 01 01 F7
```

**Switch to Live Mode:**
```
F0 47 7F 15 62 00 01 00 F7
```

**Important**: You should switch to User Mode when taking control of Push to ensure it accepts custom messages.

---

## Aftertouch

Push supports both global and per-pad aftertouch.

### Channel Pressure (Global Aftertouch)

```
0xD0 [pressure]           // pressure: 0-127
```

### Polyphonic Key Pressure (Per-Pad)

```
0xA0 [note] [pressure]    // note: pad note number, pressure: 0-127
```

---

## Sources

- [Ableton Push 2 MIDI Interface (Official)](https://github.com/Ableton/push-interface)
- [Push 1/2 Compatibility (GitHub Issue)](https://github.com/Ableton/push-interface/issues/19)
- [Push LCD SysEx - Cycling74 Forum](https://cycling74.com/forums/how-to-control-the-push-lcd-with-sysex-messages)
- [Push LCD SysEx - Ableton Forum](https://forum.ableton.com/viewtopic.php?t=193744)
- [Push Color Palette - Ableton Forum](https://forum.ableton.com/viewtopic.php?t=192920)
- [Decompiled Remote Scripts](https://github.com/gluon/AbletonLive9_RemoteScripts)
- [STRUCTURE VOID - Push Scripts](https://structure-void.com/ableton-live-push-and-scripts/)
