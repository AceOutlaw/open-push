# OpenPush Reason Codecs

Lua codec files for Reason Remote integration.

## Installation

### macOS

Copy all `.lua` and `.luacodec` files to:
```
/Library/Application Support/Propellerhead Software/Remote/Codecs/
```

Or use the install script:
```bash
./install_codecs.sh
```

### Windows

Copy all `.lua` and `.luacodec` files to:
```
%PROGRAMDATA%\Propellerhead Software\Remote\Codecs\
```

## Configuration in Reason

1. Start the OpenPush bridge application (creates virtual MIDI ports)
2. Open Reason
3. Go to **Preferences > Control Surfaces**
4. Click **Add** and configure each surface:

| Manufacturer | Model | MIDI In | MIDI Out |
|--------------|-------|---------|----------|
| OpenPush | Transport | OpenPush Transport | OpenPush Transport |
| OpenPush | Devices | OpenPush Devices | OpenPush Devices |
| OpenPush | Mixer | OpenPush Mixer | OpenPush Mixer |

5. Click **OK** to save

## Files

| File | Purpose |
|------|---------|
| `OpenPush Transport.lua` | Transport controls (play, stop, record, tempo) |
| `OpenPush Transport.luacodec` | Transport surface manifest |
| `OpenPush Devices.lua` | Device parameter control (8 encoders) |
| `OpenPush Devices.luacodec` | Devices surface manifest |
| `OpenPush Mixer.lua` | Mixer controls (volume, pan, mute, solo) |
| `OpenPush Mixer.luacodec` | Mixer surface manifest |

## Protocol

Communication uses custom SysEx messages:
```
F0 00 11 22 [port_id] [msg_type] [data...] F7
```

Port IDs:
- `01` = Transport
- `02` = Devices
- `03` = Mixer

See `protocol.py` for message type definitions.
