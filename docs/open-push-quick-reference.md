# open-push Quick Reference

Push 1 → Python Middleware → Reason integration. Middleware handles all logic; Push is a dumb terminal; Reason receives processed MIDI.

## Architecture

```
Push 1 ────> open-push (state, scales, sequencer, display) ────> Reason
       <────                                               <────
      LED/LCD                                             values
```

**Middleware owns:** Mode state, scale calculation, step sequencer, LCD formatting, LED colors  
**Reason provides:** Parameter values (0-127), device/patch names, transport state  
**Reason cannot provide:** File browsing, sequencer data, waveforms, routing

## Hardware

- **Pads:** 8x8 velocity-sensitive, RGB LEDs
- **Encoders (11 total):**
  - 8 main (above display, touch-sensitive)
  - 1 master volume (right of main 8)
  - 2 small (left side): Tempo, Swing
  - All send nothing by default; behavior is software-defined
- **Display:** 4 lines × 4 segments (17 chars each, with gaps)
- **Ports:** Port 1 (Live/MIDI), Port 2 (User - display/LEDs)

## Critical Technical Notes

1. **Initialization:** Send SysEx "Wake Up" command to unlock from Ableton logo
2. **Feedback Loop:** Use touch-override to prevent encoder jitter (ignore Reason values while encoder touched)
3. **Shift:** Software modifier tracked as `shift_held` state
4. **Step Sequencer:** Runs in middleware, NOT Reason. Syncs to MIDI clock, fires notes on step.

## Modes Overview

| Mode | Encoders | Primary Function |
|------|----------|------------------|
| Track | Track, Playhead, Patch, Loop L/R, +3 unused | Song navigation |
| Device | 8 parameters (banked, up to 24 banks) | Device control |
| Volume | 8 channel volumes | Mixer levels |
| Pan | 8 channel pans (SHIFT=width) | Mixer panning |
| Clip | Channel strip (EQ, Comp, Gate, Sends) | Single channel deep edit |
| Master | Master section, bus compressor | Master control |

## Note Mode Submodes

| Device | Pad Layout |
|--------|-----------|
| Generic | Isomorphic keyboard (scales, root=blue, in-key=white) |
| Kong | 16 pads + 16 velocity + group assign |
| Redrum | 10 drums + velocity + step sequencer (middleware) |
| Dr.OctoRex | 32 slices + 8 loop triggers |

## Key Controls

| Control | Function | +SHIFT |
|---------|----------|--------|
| Mode buttons | Enter mode | Show Reason view |
| Mute (Volume) | Clear all mutes | - |
| Mute (other) | Mute selected track | - |
| Scale | Scale selection | Layout/TouchStrip settings |
| Play | Play/Stop | Return to start |
| New | Alt Take | New Overdub |

## Display Structure

```
|Seg0 17ch|  |Seg1 17ch|  |Seg2 17ch|  |Seg3 17ch|  <- Line 1
|Seg0 17ch|  |Seg1 17ch|  |Seg2 17ch|  |Seg3 17ch|  <- Line 2
(Lines 3-4 same pattern)
```

Physical gaps between segments. Text cannot flow continuously.

## Reason Remote Available

✓ Transport (play, stop, rec, loop, tempo, undo)  
✓ Track navigation, patch selection (blind - no preview)  
✓ Mixer (vol, pan, sends 1-8, EQ, dynamics)  
✓ Master section, bus compressor  
✓ Device parameters (banked)  
✓ VU meters L/R, gain reduction (0-127)

## Hard Limits

✗ File/folder browsing (no file system access)  
✗ Waveform display (LCD is character-only)  
✗ Sequencer pattern data (can't read Reason's sequencer)  
✗ Device routing/cabling  
✗ Plugin windows

## Keystrokes vs Remote API vs Middleware

**Critical distinction for implementation:**

| Implementation | Foreground Required? | Examples |
|----------------|---------------------|----------|
| **KEYSTROKE** | YES - Reason must be focused | Browse, Add Track, SHIFT+Mode (view switch), Delete, cursor nav |
| **Remote API** | NO - Always works | Transport, Mixer, Device params, Mute/Solo, Track nav |
| **Middleware** | NO - Internal only | Scales, pad layout, display, LEDs, step sequencer, mode state |

**Keystroke buttons (require foreground):**
- Browse, Add Track, Add Effect, cursor keys (browser)
- SHIFT+Track/Device/Volume/Clip (view switching)
- Delete, Duplicate
- All Double button (keycommands) pages

**Platform:** macOS native; Windows requires Java Runtime (32-bit)

## Unused Controls (Enhancement Opportunities)

- Track Mode: Encoders 6-8, Buttons 5-8
- Master Mode: Prev/Next, Mute/Solo
- Potential: VU metering on pads, global mute/solo behavior

## Configuration

```json
{
  "VelocityCurve": "Linear|Logarithmic|Fixed",
  "PadThreshold": 0-127,
  "Brightness": 1(USB)|2(AC),
  "GlobalUndo": true|false
}
```

---
*Full details: open-push-master-reference.md*
