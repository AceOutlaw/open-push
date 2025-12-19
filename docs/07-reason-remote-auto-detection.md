# Reason Remote Auto-Detection Research

## How Auto-Detection Actually Works

Reason's "Auto-detect Surfaces" uses the `remote_probe()` function defined in Lua codecs.

## Current Implementation (OpenPush)

- The OpenPush codecs now return a custom ping/pong `remote_probe()` handshake.
- The Python bridge responds to `SYSTEM_PING` with `SYSTEM_PONG` so Reason can match.
- The bridge must be running before Reason's auto-detect scan.
- Port names are `OpenPush Transport/Devices/Mixer In` and `... Out`.

### The remote_probe() Function

From PusheR's working implementation:

```lua
function remote_probe(manufacturer, model)
    assert(model=="PushDevices")
    return {
        request="f0 7e 7f 06 01 f7",
        response="f0 7e 7f 06 02 56 66 66 01 03 ?? ?? ?? ?? f7"
    }
end
```

### What This Means

1. **Request**: `F0 7E 7F 06 01 F7` is a **Universal MIDI Identity Request** (standard SysEx)
2. **Response**: The pattern Reason expects back from the hardware
   - `F0 7E 7F 06 02` - Identity Reply header
   - `56 66 66` - Manufacturer ID bytes
   - `01 03` - Device family/model
   - `?? ?? ?? ??` - Version (wildcards)
   - `F7` - End of SysEx

### Auto-Detection Flow

```
Reason                          MIDI Port                    Hardware
  |                                |                            |
  |-- Send identity request ------>|                            |
  |   F0 7E 7F 06 01 F7           |---- Forward to hardware --->|
  |                                |                            |
  |                                |<--- Hardware responds -----|
  |<-- Receive response -----------|    F0 7E 7F 06 02 ...      |
  |                                |                            |
  | Compare to remote_probe()      |                            |
  | response pattern               |                            |
  |                                |                            |
  | If match: Surface detected!    |                            |
```

### Why Virtual Ports Don't Auto-Detect

Virtual MIDI ports (created by `mido.open_output(..., virtual=True)`) don't have hardware to respond:

1. Reason sends identity request to our virtual port
2. Our Python app receives it (if we're listening)
3. **But we don't respond** - unless the bridge implements a reply
4. Reason gets no response
5. Auto-detection fails: "No keyboards or control surfaces were auto-detected"

### How PusheR Handles This

PusheR uses **IAC Driver ports** (macOS system-level virtual MIDI):

1. IAC ports also don't respond to identity requests
2. PusheR's `remote_probe()` exists but **never succeeds** with IAC
3. Users add control surfaces **MANUALLY** in Reason preferences
4. Users manually assign the IAC ports
5. Generic port descriptions ("In Port", "Out Port") because any port can be assigned

## Solution Options

### Option A: Implement Identity Response (Enable True Auto-Detection)

Our Python app would need to:

1. Listen for MIDI identity requests on all ports
2. When we receive `F0 7E 7F 06 01 F7`:
3. Reply with the expected response pattern
4. Reason would then auto-detect us

**Pros:**
- True auto-detection like hardware controllers
- Better user experience

**Cons:**
- More complex implementation
- Need to run app BEFORE Reason starts auto-detect
- Still requires timing coordination

### Option B: Manual Setup (Like PusheR)

Accept that auto-detection won't work for virtual ports:

1. Use generic port descriptions: "In Port", "Out Port"
2. User adds control surfaces manually in Reason
3. User assigns our virtual ports manually
4. Works reliably once set up
5. Settings persist in Reason preferences

**Pros:**
- Proven approach (PusheR uses this)
- Simpler implementation
- Works with any virtual port system

**Cons:**
- Requires initial manual setup
- User must start Python app before opening Reason

## Recommendation

Option A is implemented for OpenPush. Keep Option B as a fallback if auto-detect
fails on a given setup.

## Manual Setup Notes (Fallback)

### 1. Update luacodec files to use generic descriptions:

```lua
-- OpenPush Transport.luacodec
in_ports={ {description="In Port"} },
out_ports={{description="Out Port", optional=true}},
```

### 2. User setup instructions:

1. Start OpenPush Python app (creates virtual ports)
2. Open Reason → Preferences → Control Surfaces
3. Click "Add manually"
4. Select OpenPush → Transport
5. Assign "OpenPush Transport In" to "In Port"
6. Assign "OpenPush Transport Out" to "Out Port"
7. Repeat for Devices and Mixer

### 3. Python app must be running first

The virtual ports only exist while the Python app runs. User must:
1. Start Python app
2. Then start Reason
3. Ports persist in Reason's memory until quit

## References

- MIDI Identity Request: Universal SysEx, standard MIDI spec
- PusheR luacodec files: Use generic "In Port"/"Out Port" descriptions
- PusheR Settings.json: Uses IAC Driver ports " Push_IN" and " Push_OUT"
