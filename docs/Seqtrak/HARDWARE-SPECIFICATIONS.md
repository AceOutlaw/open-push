# Yamaha Seqtrak Hardware Specifications

**Official Documentation:** [Yamaha USA Specs](https://usa.yamaha.com/products/music_production/music-production-studios/seqtrak/specs.html)

## Overview

The Yamaha Seqtrak is a portable music production workstation with integrated synthesis, sampling, and sequencing capabilities.

---

## Connectivity & Ports

### USB

**Port Type:** USB Type-C (Single port)

**Functions (all via one port):**
- Power input/charging
- MIDI to host
- MIDI to device
- Audio interface (bidirectional)

**USB Audio Specifications:**
- Sample rate: 44.1 kHz
- Bit depth: 24-bit
- Channels: 2 in / 2 out (stereo)

**Important Constraint:**
⚠️ **The Seqtrak has ONLY ONE USB-C port.** It cannot be connected to multiple USB hosts simultaneously. When connected to one device (e.g., Raspberry Pi), it cannot simultaneously connect to another device (e.g., iPad) via USB.

### Audio Connections

**PHONES Output:**
- Type: 3.5mm stereo mini jack
- Function: Headphone output / line output
- Location: Next to USB-C port

**AUDIO IN (AUX In):**
- Type: 3.5mm stereo mini jack
- Function: Line-level input for external audio sources
- Use cases: Sampling external audio, connecting drum machines/synths

**Built-in Audio:**
- Speakers: 2.3 cm drivers, 1W output per speaker
- Microphone: Internal MEMS microphone for sampling

### MIDI Connections

**Physical MIDI:**
- Type: 3.5mm stereo mini jack (proprietary cable included)
- Cable configuration: 3.5mm plug → 2x 5-pin DIN MIDI (IN/OUT)
- Function: Traditional MIDI IN/OUT for hardware connections

**Wireless MIDI:**
- Bluetooth MIDI supported
- Coverage varies by region

### Wireless Connectivity

**Bluetooth:**
- Function: App connectivity, MIDI, audio streaming
- Activation: Hold [ALL] knob + [SWING] button simultaneously

**Wi-Fi:**
- AP Mode: Direct connection to mobile devices
- Client Mode: Network connection
- Function: Project/sample file transfer, app sync

---

## Audio System

### Sound Generation

**Synthesis Engines:**
- **AWM2:** 128-voice polyphony
- **FM:** 8-voice polyphony

**Sample Storage:**
- Preset waves: 800 MB (16-bit equivalent)
- User waves: 500 MB

### Audio Processing

- Internal effects processing
- Real-time performance controls
- Step sequencer with automation

---

## Physical Specifications

| Specification | Value |
|--------------|-------|
| **Dimensions** | |
| Width | 343 mm (13.5") |
| Height | 38 mm (1.5") |
| Depth | 97 mm (3.8") |
| **Weight** | 0.5 kg (1 lb 2 oz) |

---

## Power System

**Battery:**
- Type: Lithium-ion rechargeable
- Capacity: 2,100 mAh (7.6 Wh)
- Battery life: 3-4 hours continuous use
- Charge time: 3-5 hours

**Power Consumption:** 6W

**Charging Specifications:**
- Method: USB Power Delivery via USB-C port
- Voltage: 4.8-5.2V
- Current: 1.5A minimum

---

## USB Driver Requirements

**macOS/Windows:**
- Requires Yamaha Steinberg USB Driver
- Download: [Yamaha Downloads](https://usa.yamaha.com/support/downloads/)

**iOS/Android:**
- Class-compliant USB audio
- No driver required

**Linux (Raspberry Pi):**
- Class-compliant USB audio (ALSA)
- Recognized as `card: SEQTRAK`
- Format: S24_3LE (24-bit, 3-byte little-endian)
- Rate: 44100 Hz

---

## Connection Scenarios

### 1. Computer/Pi via USB
```
Seqtrak USB-C ←→ Computer/Pi
```
- ✅ MIDI bidirectional
- ✅ Audio bidirectional (recording + playback)
- ✅ Power/charging

### 2. iPad via USB
```
Seqtrak USB-C ←→ iPad USB-C (or Lightning with adapter)
```
- ✅ MIDI bidirectional
- ✅ Audio bidirectional
- ⚠️ Requires USB-C to USB-C cable (or Lightning adapter for older iPads)

### 3. External Audio via 3.5mm Jacks
```
External device → 3.5mm cable → Seqtrak AUDIO IN (sampling)
Seqtrak PHONES → 3.5mm cable → Headphones/mixer/recorder
```
- ✅ Can be used simultaneously with USB connection
- ✅ Allows iPad audio input while USB connected to Pi

---

## Multi-Device Connection Constraints

**The Problem:**
The Seqtrak's single USB-C port means it can only connect to **one USB host at a time**.

**Example:**
- ❌ **Cannot:** Seqtrak USB → Pi (MIDI control) AND Seqtrak USB → iPad (audio) simultaneously
- ✅ **Can:** Seqtrak USB → Pi (MIDI/audio) AND iPad → Seqtrak AUDIO IN jack (via 3.5mm)

**Workarounds for Dual-Device Setup:**
1. Use 3.5mm audio jacks for one device's audio while USB handles the other
2. Use Bluetooth for MIDI (if USB needed for audio elsewhere)
3. Use network audio streaming (adds latency)

---

## References

- [Yamaha Seqtrak Official Specs](https://usa.yamaha.com/products/music_production/music-production-studios/seqtrak/specs.html)
- [Connecting Seqtrak Guide](https://yamahasynth.com/learn/seqtrak/connecting-seqtrak/)
- [Intro to Seqtrak](https://yamahasynth.com/learn/seqtrak/intro-to-seqtrak/)
- [Seqtrak Quick Start Guide (PDF)](https://usa.yamaha.com/files/download/other_assets/8/1612748/seqtrak_en_qg_a0.pdf)

---

## Raspberry Pi Bridge Extension

The open-push Raspberry Pi bridge extends Seqtrak's connectivity through USB gadget mode, enabling:

### iPad Bidirectional Audio

**Architecture:**
```
iPad ←USB-C→ Pi (gadget mode) ←USB-A→ Seqtrak (host mode)
                               └USB-A→ Push (host mode)
```

**Capabilities:**
- Sample iPad audio directly into Seqtrak
- Record Seqtrak audio to iPad apps
- Maintains full Push MIDI control simultaneously

**Documentation:** `raspberry-pi-setup/ipad-usb-audio-bridge.md` (local Pi setup guide)

**Technical Details:**
- Pi acts as UAC2 USB audio device to iPad (48kHz, 32-bit)
- ALSA audio routing with sample rate conversion (48kHz ↔ 44.1kHz)
- Requires Pi 4 Model B (dual USB controllers)
- Pi powered via GPIO when iPad connected (USB-C in gadget mode)

**Status:**
- ✅ iPad → Seqtrak: Fully working
- ⏳ Seqtrak → iPad: Requires iPad app actively recording/monitoring

---

**Last Updated:** 2025-12-27
**Relevant to:** open-push Seqtrak bridge development
