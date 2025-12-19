# Research Knowledge Base (2025)

Comprehensive findings from web research on Reason Remote scripts, MIDI bridge development, and Ableton Push 2 technical specifications.

---

## 1. Reason Remote Script Development

### 1.1 Overview

**Remote** is Reason Studios' protocol for communication between hardware control surfaces and Reason. Introduced in Reason 3.0 (2005), it provides:
- Automatic device detection
- Dynamic parameter mapping
- Bidirectional communication (LEDs, displays)
- Multiple banks/pages of controls

### 1.2 File Structure

A complete Remote implementation consists of:

| File Type | Extension | Purpose |
|-----------|-----------|---------|
| **Lua Codec** | `.luacodec` | Index file listing supported surfaces |
| **Lua Source** | `.lua` | Control logic, MIDI handling |
| **Remote Map** | `.remotemap` | Parameter-to-control mappings |
| **Image** | `.png` | 96×96 icon for Reason UI |

### 1.3 Installation Locations

**macOS:**
```
/Library/Application Support/Propellerhead Software/Remote/Codecs/Lua Codecs/<manufacturer>/
/Library/Application Support/Propellerhead Software/Remote/Maps/<manufacturer>/
```

**Windows:**
```
C:\ProgramData\Propellerhead Software\Remote\Codecs\Lua Codecs\<manufacturer>\
C:\ProgramData\Propellerhead Software\Remote\Maps\<manufacturer>\
```

**User-specific (recommended for custom scripts):**
- macOS: `~/Library/Application Support/Propellerhead Software/Remote/`
- Windows: `%APPDATA%\Propellerhead Software\Remote\`

### 1.4 Lua Codec Structure

#### Minimal Codec Example
```lua
function remote_init(manufacturer, model)
    local items = {
        {name="Rotary1", input="value", output="value", min=0, max=127},
        {name="Rotary2", input="value", output="value", min=0, max=127},
        {name="Button1", input="button", output="value"},
        {name="Keyboard", input="keyboard"},
    }
    remote.define_items(items)
    
    local inputs = {
        {pattern="b? 47 xx", name="Rotary1"},
        {pattern="b? 48 xx", name="Rotary2"},
        {pattern="b? 50 ?<???x>", name="Button1"},
    }
    remote.define_auto_inputs(inputs)
    
    local outputs = {
        {pattern="b? 47 xx", name="Rotary1"},
        {pattern="b? 50 0<000x>", name="Button1"},
    }
    remote.define_auto_outputs(outputs)
end
```

#### Item Input Types
| Type | Description | Values |
|------|-------------|--------|
| `keyboard` | Note on/off with velocity | 0-1 |
| `button` | Momentary press | 0-1 |
| `value` | Absolute (fader/knob) | Custom range |
| `delta` | Relative encoder | +/- changes |
| `noinput` | Output only (LED/display) | N/A |

#### Item Output Types
| Type | Description |
|------|-------------|
| `value` | Numeric feedback (LED brightness, fader position) |
| `text` | Display text |
| `nooutput` | Input only |

### 1.5 MIDI Pattern Syntax

Patterns are hex strings with wildcards:

| Character | Meaning |
|-----------|---------|
| `?` | Match any nibble (4 bits) |
| `??` | Match any byte |
| `xx` | Extract value into x |
| `yy` | Extract into y |
| `zz` | Extract into z |
| `<100x>` | Binary: match 100, extract 4th bit to x |
| `<???x>` | Binary: 3 wildcards + extract bit |

**Examples:**
```lua
-- CC on any channel, controller 32, extract value
{pattern="b? 20 xx", name="Fader1"}

-- Note on/off detection
{pattern="<100x>? yy zz", name="Keyboard"}  -- x=1 note on, x=0 note off

-- Button press (last bit = pressed state)
{pattern="b? 60 ?<???x>", name="Button1"}

-- Encoder with sign bit (relative)
{pattern="b? 50 <???y>x", name="Encoder1", value="x*(1-2*y)"}

-- 14-bit pitch bend
{pattern="e? xx yy", name="PitchBend", value="y*128 + x"}
```

### 1.6 Callback Functions

#### Required
```lua
function remote_init(manufacturer, model)
    -- Define items, auto_inputs, auto_outputs
end
```

#### Optional
```lua
function remote_probe(manufacturer, model)
    -- Auto-detection request/response
    return {
        request = "f0 7e 7f 06 01 f7",
        response = "f0 7e 7f 06 02 ?? ?? ?? ?? f7"
    }
end

function remote_prepare_for_use()
    -- Send initialization MIDI
    return { remote.make_midi("f0 00 11 22 01 f7") }
end

function remote_release_from_use()
    -- Send cleanup MIDI
    return { remote.make_midi("f0 00 11 22 00 f7") }
end

function remote_process_midi(event)
    -- Manual MIDI handling
    local ret = remote.match_midi("f0 00 11 22 xx yy f7", event)
    if ret then
        remote.handle_input({
            time_stamp = event.time_stamp,
            item = g_item_index,
            value = ret.x
        })
        return true
    end
    return false
end

function remote_set_state(changed_items)
    -- React to Reason state changes
    for i, item_index in ipairs(changed_items) do
        if item_index == g_lcd_index then
            g_lcd_text = remote.get_item_text_value(item_index)
        end
    end
end

function remote_deliver_midi(max_bytes, port)
    -- Send MIDI to controller
    local events = {}
    if g_update_needed then
        table.insert(events, remote.make_midi("..."))
        g_update_needed = false
    end
    return events
end

function remote_on_auto_input(item_index)
    -- Called after auto input handled
    g_last_input_time = remote.get_time_ms()
end
```

### 1.7 Remote SDK Utility Functions

```lua
-- State queries
remote.get_item_value(index)        -- Scaled numeric value
remote.get_item_text_value(index)   -- Text or formatted number
remote.get_item_name(index)         -- Remotable item name
remote.is_item_enabled(index)       -- True if mapped
remote.get_time_ms()                -- Current time in ms

-- MIDI handling
remote.make_midi(pattern, params)   -- Create MIDI event
remote.match_midi(pattern, event)   -- Match and extract
remote.handle_input(msg)            -- Send to Reason
remote.trace(str)                   -- Debug output (Codec Test only)
```

### 1.8 Remote Map Format

Tab-delimited text file:
```
Propellerhead Remote Mapping File
File Format Version	1.0.0

Control Surface Manufacturer	OpenPush
Control Surface Model	Transport

Map Version	1.0.0

Scope	Propellerheads	Reason Document
//	Control Surface Item	Key	Remotable Item	Scale	Mode
Map	Play	 	Play
Map	Stop	 	Stop
Map	Record	 	Record

Scope	Propellerheads	Mixer 14:2
Define Group	Keyboard Shortcut Variations	Bank1	Bank2
//	Control Surface Item	Key	Remotable Item	Scale	Mode	Group
Map	Fader 1	 	Channel 1 Level	 	 	Bank1
Map	Fader 1	 	Channel 9 Level	 	 	Bank2
```

**Scope Priority:**
1. Device scopes (Subtractor, Mixer, etc.) - highest
2. "Reason Document" (transport, undo)
3. "Master Keyboard" - lowest

### 1.9 Remote SDK Limitations

**What Remote CAN do:**
- Transport (Play, Stop, Record, Loop, Tempo)
- Device parameters (Filter, Volume, Pan)
- Track selection (Next/Prev)
- Patch selection (Next/Prev)
- Undo/Redo

**What Remote CANNOT do:**
- Create new tracks
- Save project
- Delete tracks
- Open/close browser
- Access file menu functions

**Workaround:** Use OS-level keystrokes via Python bridge (`pyautogui`)

### 1.10 Resources

- **Reason Studios Developer Portal:** https://developer.reasonstudios.com
- **Sound On Sound Tutorial:** https://www.soundonsound.com/techniques/hacking-remote-files-reason
- **Reason Studios Blog:** https://www.reasonstudios.com/blog/tutorials/control-remote/
- **ReasonTalk Forums:** https://forum.reasontalk.com (search for "Lua codec")
- **GitHub Examples:** https://github.com/topics/reason?l=lua

---

## 2. Software-to-Hardware MIDI Bridge Development

### 2.1 Architecture Pattern

```
┌─────────────┐    USB MIDI    ┌─────────────┐   Virtual MIDI   ┌─────────────┐
│  Hardware   │ ◄────────────► │   Python    │ ◄──────────────► │    DAW      │
│ Controller  │                │   Bridge    │                  │  (Reason)   │
└─────────────┘                └─────────────┘                  └─────────────┘
                                     │
                                     ▼
                              ┌─────────────┐
                              │   Display   │
                              │   LEDs      │
                              │   Logic     │
                              └─────────────┘
```

### 2.2 Python MIDI Libraries

#### mido + python-rtmidi (Recommended)
```bash
pip install mido python-rtmidi
```

```python
import mido

# List ports
print(mido.get_input_names())
print(mido.get_output_names())

# Open ports
inport = mido.open_input('Ableton Push User Port')
outport = mido.open_output('Ableton Push User Port')

# Create virtual ports
virtual_in = mido.open_input('MyBridge', virtual=True)
virtual_out = mido.open_output('MyBridge', virtual=True)

# Send/receive
for msg in inport:
    print(msg)
    if msg.type == 'note_on':
        outport.send(msg)

# SysEx
sysex = mido.Message('sysex', data=[0x47, 0x7F, 0x15, 0x18, ...])
outport.send(sysex)
```

#### Key Features of mido
- Cross-platform (macOS, Windows, Linux)
- Virtual port creation
- SysEx support
- Multiple backend support (rtmidi, portmidi)
- Message parsing and creation

### 2.3 Bridge Design Patterns

#### Event-Driven Architecture
```python
class MIDIBridge:
    def __init__(self):
        self.hardware_in = mido.open_input('Hardware Port')
        self.hardware_out = mido.open_output('Hardware Port')
        self.daw_in = mido.open_input('DAW Bridge', virtual=True)
        self.daw_out = mido.open_output('DAW Bridge', virtual=True)
        
    def run(self):
        # Non-blocking with callbacks
        self.hardware_in.callback = self.handle_hardware
        self.daw_in.callback = self.handle_daw
        
    def handle_hardware(self, msg):
        # Translate hardware → DAW
        translated = self.translate_to_daw(msg)
        self.daw_out.send(translated)
        
    def handle_daw(self, msg):
        # Translate DAW → hardware
        translated = self.translate_to_hardware(msg)
        self.hardware_out.send(translated)
```

#### Thread-Based Polling
```python
import threading

class MIDIBridge:
    def __init__(self):
        self.running = False
        
    def start(self):
        self.running = True
        self.hw_thread = threading.Thread(target=self.poll_hardware)
        self.daw_thread = threading.Thread(target=self.poll_daw)
        self.hw_thread.start()
        self.daw_thread.start()
        
    def poll_hardware(self):
        while self.running:
            for msg in self.hardware_in.iter_pending():
                self.process_hardware_message(msg)
            time.sleep(0.001)  # 1ms polling
```

### 2.4 SysEx Handling

```python
def parse_sysex(msg):
    """Parse custom SysEx protocol."""
    if msg.type != 'sysex':
        return None
    
    data = msg.data
    # Check header: F0 00 11 22 ...
    if len(data) < 5:
        return None
    if data[0:3] != (0x00, 0x11, 0x22):
        return None
        
    port_id = data[3]
    msg_type = data[4]
    payload = data[5:]
    
    return {'port': port_id, 'type': msg_type, 'data': payload}

def build_sysex(port_id, msg_type, data):
    """Build custom SysEx message."""
    sysex_data = [0x00, 0x11, 0x22, port_id, msg_type] + list(data)
    return mido.Message('sysex', data=sysex_data)
```

### 2.5 Display Updates

```python
def update_lcd(outport, line, text):
    """Update Push 1 LCD line."""
    # Push 1 LCD SysEx: F0 47 7F 15 [line] 00 45 00 [68 chars] F7
    line_addresses = {1: 0x18, 2: 0x19, 3: 0x1A, 4: 0x1B}
    
    # Pad text to 68 chars
    text = text.ljust(68)[:68]
    text_bytes = [ord(c) for c in text]
    
    sysex_data = [0x47, 0x7F, 0x15, line_addresses[line], 0x00, 0x45, 0x00] + text_bytes
    outport.send(mido.Message('sysex', data=sysex_data))
```

### 2.6 Resources

- **mido Documentation:** https://mido.readthedocs.io/
- **python-rtmidi:** https://github.com/SpotlightKid/python-rtmidi
- **MIDI Toolkit (mdevtk):** https://github.com/oscaracena/mdevtk

---

## 3. Ableton Push 2 Technical Specifications

### 3.1 Physical Specifications

| Spec | Value |
|------|-------|
| **Width** | 380 mm / 14.96 in |
| **Depth** | 318 mm / 12.52 in |
| **Height (body)** | 29 mm / 1.14 in |
| **Height (with encoders)** | 44.5 mm / 1.75 in |
| **Weight** | 3.1 kg / 6.8 lbs |

### 3.2 Display Specifications

| Spec | Value |
|------|-------|
| **Resolution** | 960 × 160 pixels |
| **Color Depth** | 16-bit RGB (RGB565) |
| **Diagonal** | ~6.7 inches |
| **Interface** | USB 2.0 bulk transfer |
| **Frame Rate** | Up to 60 fps |
| **Timeout** | 2 seconds (goes black) |

### 3.3 USB Interface

| Spec | Value |
|------|-------|
| **Connection** | USB 2.0 |
| **Vendor ID** | 0x2982 (Ableton) |
| **Product ID** | 0x1967 (Push 2) |
| **MIDI Ports** | 2 (Live Port + User Port) |
| **Display Interface** | USB bulk transfer (libusb) |

### 3.4 Controls

| Control | Count | Interface |
|---------|-------|-----------|
| **Pads** | 64 (8×8 grid) | Note messages, RGB LEDs |
| **Encoders** | 11 touch-sensitive | CC + Note (touch) |
| **Buttons** | ~50 | CC messages |
| **Touch Strip** | 1 | Pitch bend / Mod wheel |

### 3.5 MIDI Protocol

**Pads:** Note 36-99 (velocity-sensitive, aftertouch)
```
Note On:  0x90 [note] [velocity]
Note Off: 0x80 [note] 0x00
```

**Buttons:** Control Change
```
Press:   0xB0 [cc] 0x7F
Release: 0xB0 [cc] 0x00
```

**Encoders:** Relative mode (2's complement)
```
Turn: 0xB0 [cc] [delta]  // 1-63 = CW, 65-127 = CCW
Touch: 0x90 [note] 0x7F/0x00
```

### 3.6 Display Protocol (USB)

#### Frame Structure
```
Frame Header (16 bytes):
  { 0xFF, 0xCC, 0xAA, 0x88, 0x00, 0x00, 0x00, 0x00,
    0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 }

Pixel Data:
  - 640 buffers × 512 bytes = 327,680 bytes
  - 160 lines × 2048 bytes per line
  - Each line: 1920 bytes pixels + 128 bytes padding
```

#### Pixel Encoding (RGB565)
```
Bit layout: [b4 b3 b2 b1 b0 g5 g4 g3 g2 g1 g0 r4 r3 r2 r1 r0]
Little endian (LSB first)
```

#### XOR Signal Shaping
Before sending, XOR each 4 bytes with `0xFFE7F3E7`:
```python
pattern = [0xE7, 0xF3, 0xE7, 0xFF]
for i, byte in enumerate(line_buffer):
    line_buffer[i] ^= pattern[i % 4]
```

### 3.7 SysEx Commands

**Manufacturer ID:** `0x00 0x21 0x1D 0x01 0x01`

| Command | ID | Purpose |
|---------|----|---------|
| Set LED Brightness | 0x06 | Global LED brightness (0-127) |
| Get LED Brightness | 0x07 | Query current brightness |
| Set Pad Sensitivity | 0x28 | Adjust pad response curve |
| Set Aftertouch Mode | 0x1E | Channel or poly aftertouch |
| Set Touch Strip Config | 0x17 | Configure touch strip behavior |

**Example: Set LED Brightness**
```
F0 00 21 1D 01 01 06 40 F7  // Set to 64 (50%)
```

### 3.8 LED Animation

Animations triggered via MIDI channels 1-15:

| Channel | Transition | Duration |
|---------|------------|----------|
| 0 | Stop animation | - |
| 1-5 | One-shot fade | 24th to half note |
| 6-10 | Pulsing | 24th to half note |
| 11-15 | Blinking | 24th to half note |

```python
# Set initial color (channel 0)
outport.send(mido.Message('note_on', channel=0, note=36, velocity=21))  # Green
# Start pulsing animation (channel 9 = quarter note pulse)
outport.send(mido.Message('note_on', channel=9, note=36, velocity=5))   # To red
```

### 3.9 Python Libraries for Push 2

#### push2-python (Recommended)
```bash
pip install git+https://github.com/ffont/push2-python
```

**Requirements:**
- `pyusb` (for display)
- `libusb` (system library)
- `numpy` (for frame buffers)
- `cairo` / `PIL` (for rendering)

**Basic Usage:**
```python
import push2_python

push = push2_python.Push2()

# Pad handler
@push.on_pad_pressed()
def on_pad(push, pad_n, pad_ij, velocity):
    print(f"Pad {pad_n} pressed with velocity {velocity}")

# Set pad color
push.pads.set_pad_color(pad_n, 'green')

# Display frame
import numpy as np
frame = np.zeros((160, 960), dtype=np.uint16)
push.display.display_frame(frame)
```

### 3.10 Resources

- **Official Ableton Push Interface Docs:** https://github.com/Ableton/push-interface
- **push2-python Library:** https://github.com/ffont/push2-python
- **Pysha (Standalone Controller):** https://github.com/ffont/pysha
- **Push 2 JUCE Display:** https://github.com/Ableton/push2-display-with-juce

---

## 4. Key Findings for OpenPush Development

### 4.1 Architecture Decisions

1. **Use Python bridge** for hardware abstraction and protocol translation
2. **Use Lua codecs** for Reason integration (Remote SDK)
3. **Use mido + python-rtmidi** for MIDI I/O
4. **For Push 2 display:** use `push2-python` or implement USB bulk transfer with `pyusb`

### 4.2 Channel Translation

| Source | MIDI Channel | Destination |
|--------|--------------|-------------|
| Push hardware | 0 (default) | Bridge |
| Bridge → Reason | 15 (0x0F) | Lua codecs expect channel 16 |
| Reason → Bridge | 15 | Bridge translates to Push |

### 4.3 SysEx Protocol Strategy

- **OpenPush header:** `F0 00 11 22 ...` (custom, avoids conflicts)
- **Push 1 LCD:** `F0 47 7F 15 ...`
- **Push 2 display:** USB bulk transfer (not MIDI SysEx)

### 4.4 Display Strategy by Hardware

| Push Model | Display Type | Implementation |
|------------|--------------|----------------|
| Push 1 | Character LCD (68×4) | MIDI SysEx |
| Push 2/3 | Pixel (960×160) | USB via libusb/pyusb |

### 4.5 Remote SDK Workarounds

For functions not supported by Remote SDK:
1. Map button to unused CC
2. Bridge detects CC and triggers OS keystroke
3. Use `pyautogui.hotkey('command', 't')` for "New Track", etc.

---

---

## 5. Official Reason Remote SDK Reference (from PDFs)

### 5.1 Reason Document Scope - Remotable Items

The **Reason Document** scope contains transport and global controls. These are the official item names from `Reason Remote Support.pdf`:

| Remotable Item | Min | Max | Input | Output | Notes |
|----------------|-----|-----|-------|--------|-------|
| **Click On/Off** | 0 | 1 | Toggle | Value | Metronome |
| **Click Level** | 0 | 127 | Value | Value | |
| **Tempo** | 1000 | 999999 | Value | Value | In 1/1000 BPM |
| **Tempo BPM** | 1 | 999 | Value | Value | Integer BPM |
| **Tempo BPM Up** | 0 | 0 | Trig | Text | |
| **Tempo BPM Down** | 0 | 0 | Trig | Text | |
| **Play** | 0 | 1 | Trig | Value | |
| **Stop** | 0 | 1 | Trig | Value | |
| **Rewind** | 0 | 1 | Hold | Value | |
| **Fast Forward** | 0 | 1 | Hold | Value | |
| **Record** | 0 | 1 | Toggle | Value | |
| **Loop On/Off** | 0 | 1 | Toggle | Value | |
| **Undo** | 0 | 1 | Trig | Value | |
| **Redo** | 0 | 1 | Trig | Value | |
| **Return To Zero** | 0 | 1 | Trig | Value | |
| **Tap Tempo** | 0 | 1 | Trig | Value | |
| **Precount On/Off** | 0 | 1 | Toggle | Value | |
| **Auto-quantize** | 0 | 1 | Toggle | Value | |
| **New Overdub** | 0 | 1 | Trig | Value | |
| **New Alternative Take** | 0 | 1 | Trig | Value | |

#### Track Targeting

| Remotable Item | Min | Max | Input | Output |
|----------------|-----|-----|-------|--------|
| **Target Track (Delta)** | 0 | 0 | Delta | Text |
| **Target Previous Track** | 0 | 0 | Trig | Text |
| **Target Next Track** | 0 | 0 | Trig | Text |
| **Target Track Name** | 0 | 0 | V | Text |
| **Target Track Solo** | 0 | 1 | Toggle | Value |
| **Target Track Mute** | 0 | 1 | Toggle | Value |
| **Any Track Solo** | 0 | 1 | Trig | Value |
| **Any Track Mute** | 0 | 1 | Trig | Value |

#### Patch Selection

| Remotable Item | Min | Max | Input | Output |
|----------------|-----|-----|-------|--------|
| **Select Patch for Target Device (Delta)** | 0 | 0 | Delta | Text |
| **Select Prev Patch for Target Device** | 0 | 0 | Trig | Text |
| **Select Next Patch for Target Device** | 0 | 0 | Trig | Text |

#### Position & Locators

| Remotable Item | Min | Max | Input | Output |
|----------------|-----|-----|-------|--------|
| **Song Position** | 0 | 2147483647 | Value | Value |
| **Bar Position** | 0 | 0 | Delta | Text |
| **Beat Position** | 0 | 0 | Delta | Text |
| **Left Loop** | 0 | 2147483647 | Value | Value |
| **Right Loop** | 0 | 2147483647 | Value | Value |
| **Goto Left Locator** | 0 | 0 | Trig | Text |
| **Goto Right Locator** | 0 | 0 | Trig | Text |
| **Move Loop Left** | 0 | 1 | Trig | Value |
| **Move Loop Right** | 0 | 1 | Trig | Value |

#### Display Items

| Remotable Item | Min | Max | Input | Output |
|----------------|-----|-----|-------|--------|
| **Document Name** | 0 | 0 | V | Text |
| **Target Track Name** | 0 | 0 | V | Text |

#### Input Types Explained

| Type | Description |
|------|-------------|
| **Value** | Absolute continuous value (fader, knob) |
| **Delta** | Relative change (+/-) from encoder |
| **Toggle** | On/off state that alternates |
| **Trig** | Momentary trigger (button press) |
| **Hold** | Active while held (rewind/forward) |
| **V** | Read-only value (meters, status) |

### 5.2 Master Keyboard Scope

| Remotable Item | Min | Max | Input | Output |
|----------------|-----|-----|-------|--------|
| **Keyboard** | 0 | 127 | Note | V |
| **Pitch Bend** | -8192 | 8191 | Value | V |
| **Mod Wheel** | 0 | 127 | Value | V |
| **Breath** | 0 | 127 | Value | V |
| **Channel Pressure** | 0 | 127 | Value | V |
| **Expression** | 0 | 127 | Value | V |
| **Damper Pedal** | 0 | 127 | Value | V |

### 5.3 Combinator Scope

| Remotable Item | Min | Max | Input | Output |
|----------------|-----|-----|-------|--------|
| **Mod Wheel** | 0 | 127 | Value | Value |
| **Rotary 1-4** | 0 | 127 | Value | Value |
| **Button 1-4** | 0 | 1 | Toggle | Value |
| **Enabled** | 0 | 2 | Value | Value |

---

## 6. SDK Sample Codecs & PusheR Analysis

### 6.1 SDK Sample Codecs (from RemoteSDK_Mac_1.2.0)

The SDK includes ACME sample codecs demonstrating best practices.

#### Basic Codec (InControl.lua)
```lua
function remote_init(manufacturer, model)
    local items={
        {name="Keyboard", input="keyboard"},
        {name="Pitch Bend", input="value", min=0, max=16383},
        {name="Modulation", input="value", min=0, max=127},
        {name="Fader 1", input="value", output="value", min=0, max=127},
        {name="Encoder 1", input="delta", output="value", min=0, max=10},
        {name="Button 1", input="button", output="value"},
    }
    remote.define_items(items)

    local inputs={
        {pattern="b? 40 xx", name="Fader 1"},
        {pattern="e? xx yy", name="Pitch Bend", value="y*128 + x"},
        {pattern="b? 01 xx", name="Modulation"},
        {pattern="9? xx 00", name="Keyboard", value="0", note="x", velocity="64"},
        {pattern="<100x>? yy zz", name="Keyboard"},
        {pattern="b? 50 <???y>x", name="Encoder 1", value="x*(1-2*y)"},
        {pattern="b? 60 ?<???x>", name="Button 1"},
    }
    remote.define_auto_inputs(inputs)

    local outputs={
        {name="Fader 1", pattern="b0 40 xx"},
        {name="Encoder 1", pattern="b0 50 0x", x="enabled*(value+1)"},
        {name="Button 1", pattern="b0 60 0<000x>"},
    }
    remote.define_auto_outputs(outputs)
end
```

#### Deluxe Codec with LCD & Popup (InControlDeluxe.lua)
```lua
-- Global state tracking
g_last_input_time = -2000
g_last_input_item = nil
g_is_lcd_enabled = false
g_lcd_state = string.format("%-16.16s", " ")
g_delivered_lcd_state = string.format("%-16.16s", "#")
g_feedback_enabled = false

function remote_on_auto_input(item_index)
    if item_index > 3 then
        g_last_input_time = remote.get_time_ms()
        g_last_input_item = item_index
    end
end

function remote_set_state(changed_items)
    for i, item_index in ipairs(changed_items) do
        if item_index == g_lcd_index then
            g_is_lcd_enabled = remote.is_item_enabled(item_index)
            new_text = remote.get_item_text_value(item_index)
            g_lcd_state = string.format("%-16.16s", new_text)
        end
    end

    -- Popup logic: show parameter value for 1 second after input
    local now_ms = remote.get_time_ms()
    if (now_ms - g_last_input_time) < 1000 then
        if remote.is_item_enabled(g_last_input_item) then
            local feedback_text = remote.get_item_name_and_value(g_last_input_item)
            if string.len(feedback_text) > 0 then
                g_feedback_enabled = true
                g_lcd_state = string.format("%-16.16s", feedback_text)
            end
        end
    elseif g_feedback_enabled then
        g_feedback_enabled = false
        if g_is_lcd_enabled then
            old_text = remote.get_item_text_value(g_lcd_index)
        else
            old_text = " "
        end
        g_lcd_state = string.format("%-16.16s", old_text)
    end
end

-- SysEx LCD message builder
local function make_lcd_midi_message(text)
    local event = remote.make_midi("f0 11 22 33 10")
    start = 6
    stop = 6 + string.len(text) - 1
    for i = start, stop do
        sourcePos = i - start + 1
        event[i] = string.byte(text, sourcePos)
    end
    event[stop + 1] = 247  -- 0xF7
    return event
end

function remote_deliver_midi()
    local ret_events = {}
    local new_text = g_lcd_state
    if g_delivered_lcd_state ~= new_text then
        assert(string.len(new_text) == 16)
        local lcd_event = make_lcd_midi_message(new_text)
        table.insert(ret_events, lcd_event)
        g_delivered_lcd_state = new_text
    end
    return ret_events
end
```

#### Device Probe (Auto-Detection)
```lua
function remote_probe(manufacturer, model)
    return {
        request = "f0 7e 7f 06 01 f7",  -- MIDI Identity Request
        response = "f0 7e 7f 06 02 56 66 66 01 03 ?? ?? ?? ?? f7"
    }
end
```

### 6.2 PusheR Reference Implementation Analysis

The original PusheR codec (from RetouchControl) provides a complete Push-to-Reason integration.

#### PusheR SysEx Protocol
```
Header: F0 11 22 06 [field_id] [16 ASCII bytes] F7
```

| Field ID | Purpose |
|----------|---------|
| 0x01 | LCD Field 1 (Line 1, Segment 1) |
| 0x02 | LCD Field 2 (Line 1, Segment 2) |
| 0x03 | LCD Field 3 (Line 1, Segment 3) |
| 0x04 | LCD Field 4 (Line 1, Segment 4) |
| 0x05-0x08 | LCD Fields 5-8 (Line 2) |
| 0x09-0x0C | LCD Fields 9-12 (Lines 3-4) |

#### PusheR Item Structure
```lua
-- 41 pots + 40 buttons + 11 LCD fields + keyboard + pitchbend = 94 items
local items = {
    -- Pots (encoders/faders)
    {name="pot2", input="delta", output="text"},  -- Relative encoder
    {name="pot6", input="value", output="value", min=0, max=127},  -- Absolute
    
    -- Buttons (normalized to 0/1)
    {name="button1", input="button", output="value"},
    
    -- LCD outputs (text only)
    {name="LCD1", output="text"},
    
    -- Keyboard
    {name="Keyboard", input="keyboard"},
    {name="pitchbend", input="value", output="value", min=0, max=16383},
}
```

#### PusheR MIDI Patterns
```lua
local inputs = {
    -- Relative encoders with sign bit
    {pattern="bf 03 <???y>x", name="pot3"},  -- CC 3, channel 16
    
    -- Absolute values
    {pattern="bf 06 xx", name="pot6"},
    
    -- Buttons (extract press state from LSB)
    {pattern="bf 2a ?<???x>", name="button1"},  -- CC 42
    
    -- Keyboard (note on/off)
    {pattern="<100x>f yy zz", name="Keyboard"},  -- Channel 16
    
    -- Pitch bend (14-bit)
    {pattern="ef xx yy", name="pitchbend", value="y*128 + x"},
}

local outputs = {
    -- Encoder LED feedback
    {name="pot3", pattern="bf 03 <???y>x"},
    
    -- Button LED
    {name="button1", pattern="bf 2a ?<???x>"},
}
```

**Key insight:** PusheR uses **MIDI Channel 16 (0xBF/0xEF/0x9F)** for all messages to avoid conflicts with note data.

#### PusheR LCD SysEx Builder
```lua
local function make_lcd_field_message(field_id, text)
    -- Format: F0 11 22 06 [field] [16 chars] F7
    local event = remote.make_midi("f0 11 22 06 " .. string.format("%02x", field_id))
    local start = 6
    local stop = 6 + string.len(text) - 1
    for i = start, stop do
        local sourcePos = i - start + 1
        event[i] = string.byte(text, sourcePos)
    end
    event[stop + 1] = 247  -- F7
    return event
end
```

### 6.3 SDK Utility Functions Reference

From the SDK documentation and sample codecs:

| Function | Description | Example |
|----------|-------------|---------|
| `remote.get_item_value(idx)` | Get scaled numeric value | `local val = remote.get_item_value(5)` |
| `remote.get_item_text_value(idx)` | Get text representation | `"120.00 BPM"` |
| `remote.get_item_name(idx)` | Get Remotable item name | `"Tempo"` |
| `remote.get_item_short_name(idx)` | Short name (≤8 chars) | `"Tempo"` |
| `remote.get_item_name_and_value(idx)` | Combined string | `"Tempo: 120.00"` |
| `remote.get_item_short_name_and_value(idx)` | Short combined | `"Tmp:120"` |
| `remote.is_item_enabled(idx)` | Check if mapped | `true` or `false` |
| `remote.get_time_ms()` | Current time in ms | `1234567` |
| `remote.make_midi(pattern)` | Create MIDI event | See examples |
| `remote.match_midi(pattern, event)` | Match and extract | Returns table or nil |
| `remote.handle_input(msg)` | Send to Reason | See examples |

### 6.4 .luacodec File Structure

```lua
version = {0, 0, 1}  -- Codec version

function remote_supported_control_surfaces()
    return {
        {
            manufacturer = "OpenPush",
            model = "Transport",
            source = "OpenPush Transport.lua",
            picture = "OpenPush.png",  -- 96x96 PNG
            in_ports = { {description = "In Port"} },
            out_ports = { {description = "Out Port", optional = true} },
            has_keyboard = true,
            setup_info_text = "Connect OpenPush bridge before adding."
        },
    }
end
```

### 6.5 Key SDK Patterns for OpenPush

**1. Encoder with Sign Bit (Relative Mode)**
```lua
{pattern = "b? 50 <???y>x", name = "Encoder 1", value = "x*(1-2*y)"}
-- y=0: positive (CW), y=1: negative (CCW)
-- x = magnitude (1-63)
-- Result: -63 to +63
```

**2. Button Press Detection**
```lua
{pattern = "b? 60 ?<???x>", name = "Button 1"}
-- Extracts last bit: x=1 pressed, x=0 released
```

**3. 14-bit Pitch Bend**
```lua
{pattern = "e? xx yy", name = "Pitch Bend", value = "y*128 + x"}
-- xx = LSB, yy = MSB
-- Range: 0-16383, center = 8192
```

**4. Keyboard Note On/Off**
```lua
{pattern = "<100x>? yy zz", name = "Keyboard"}
-- x=1: note on (0x9?), x=0: note off (0x8?)
-- yy = note number, zz = velocity
```

**5. Note Off via Velocity 0**
```lua
{pattern = "9? xx 00", name = "Keyboard", value = "0", note = "x", velocity = "64"}
-- Some controllers send note-on with velocity 0 for note-off
```

---

*Compiled: December 2025*
*Sources: Ableton, Reason Studios, GitHub, Sound On Sound, ReasonTalk, RemoteSDK_Mac_1.2.0*
