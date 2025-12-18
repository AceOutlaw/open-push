# Hardware Reference Analysis

Analysis of PusheR Remote files for OpenPush development reference.

## File Structure

```
remote-files/
├── Lua Codecs/PusheR/
│   ├── PushTransport.lua/.luacodec
│   ├── PushDevices.lua/.luacodec
│   └── PushMixer.lua/.luacodec
└── Maps/PusheR/
    ├── PushTransport.remotemap
    ├── PushDevices.remotemap
    └── PushMixer.remotemap
```

## Protocol Observations

- **SysEx header**: `F0 11 22 06 XX` for LCD text (line number in XX)
- **Channel**: Uses channel 16 (0xBF for CC, 0x9F/0x8F for notes)
- **Code protection**: Lua files use obfuscated variable names

## Transport Mappings (PushTransport.remotemap)

### Record/Reason Document Scope
| Control | Reason Function |
|---------|-----------------|
| button1/2 | Target Previous/Next Track |
| button3/4 | Select Prev/Next Patch for Target Device |
| button5 | Tap Tempo |
| button6 | Click On/Off |
| button7 | Precount On/Off |
| button8 | New Overdub |
| button9 | New Alternative Take |
| button10 | Auto-quantize |
| button11/12 | Undo/Redo |
| button13 | Loop On/Off |
| button14/15 | Fast Forward/Rewind |
| button16/17/18 | Stop/Play/Record |
| button19/20 | Target Track Mute/Solo |
| button21 | Enable Automation Recording |
| button22 | Automation As Performance Controllers |
| button23-26 | Move Loop Left/Right, One bar |
| button27/28 | Goto Left/Right Locator |
| button29/30 | Tempo BPM Down/Up |
| pot2-5 | Bar/Beat/Sixteenth/Tick Position |
| pot6 | Tempo BPM |
| pot7 | Select Patch (Delta) |
| pot10/11 | Left/Right Loop Bar |
| pot19 | Click Level |

### Device Detection via LCD
| Device | LCD1 Value |
|--------|-----------|
| Kong | "1" |
| Redrum | "2" |
| Dr.REX | "3" |

## Mixer Mappings (PushMixer.remotemap)

### Mode Groups
- Vol, Pan, Master, Ch1-Ch8, Master2-5, Width

### Master Section Scope
- **Vol mode**: Channel 1-8 Level, Mute, Solo, VU Meters
- **Pan mode**: Channel 1-8 Pan, Mute, Solo
- **Width mode**: Channel 1-8 Width
- **Master mode**: Compressor (On/Threshold/Ratio/Attack/Release/Makeup), Ctrl Room
- **Master2**: Rotary 1-4, Button 1-4
- **Master3**: FX1-8 Send Level
- **Master4**: FX1-8 Return Level
- **Master5**: FX1-8 Pan

### Per-Channel Strip (Ch1-Ch8 modes)
- Ch1: Input Gain, Invert Phase, Compressor (On/Peak/FastAtk/Ratio/Threshold/Release)
- Ch2: Gate (On/Expander/FastAtk/Range/Threshold/Release/Hold)
- Ch3: EQ (On/Mode/HF Bell/Gain/Freq, HMF Gain/Freq/Q)
- Ch4: LMF Gain/Freq/Q, LF Bell/Gain/Freq, Insert Pre, Dyn Post EQ
- Ch5: Rotary 1-4, Button 1-4
- Ch6: HPF On/Freq, LPF On/Freq, Bypass/Prev/Next Insert FX
- Ch7: FX1-4 Send On/Level
- Ch8: FX5-8 Send On/Level

## Device Mappings (PushDevices.remotemap)

### Kong Drum Designer Scope
- **16 Drums**: Each with Pitch, Decay, Tone, Variable, Bus FX Send, Aux 1 Send, Pan, Level
- **4 FX groups**: FX1-1 through FX1-4
- **2 Assignment groups**: Ass-1, Ass-2
- **2 Hit groups**: Hit-1, Hit-2
- **16 Pads**: For drum selection (Pads1-16)
- **Hit Indication**: button41-56 for pad trigger feedback
- **LCD27**: Fixed "Kong" identifier

### Structure Pattern
```
Define Group Drums: Drums1-16, FX1-1 to FX1-4, Ass-1/2, Hit-1/2
Define Group Pads: Pads1-16

Per drum (1-16):
  pot1: DM Pitch
  pot2: DM Decay
  pot3: Tone
  pot4: DM Variable
  pot5: Bus FX Send
  pot6: Aux 1 Send
  pot7: Pan
  pot8: Level
```

## Key Differences from OpenPush

| Feature | PusheR | OpenPush |
|---------|--------|----------|
| SysEx header | `11 22 06` | `00 11 22` |
| Port count | 1 shared | 3 separate |
| Device detection | LCD values | Mode state |
| Parameter pages | Groups | Modes |

## Roadmap for OpenPush

Based on PusheR analysis, future enhancements could include:

1. **Transport**: Add bar/beat position, loop manipulation, undo/redo
2. **Mixer**: VU meters, per-channel EQ/dynamics, FX sends
3. **Kong**: Individual drum parameters (not just triggers)
4. **Redrum**: Channel-specific controls
5. **Dr.OctoRex**: Slice parameters, loop controls
6. **Groups**: Multi-page parameter navigation like PusheR

## Notes

- The Lua code is intentionally obfuscated for code protection
- Remotemap files provide clearer documentation of actual mappings
- Reason's Remote SDK uses "Scope" for device-specific behavior
- "Define Group" creates switchable parameter pages
