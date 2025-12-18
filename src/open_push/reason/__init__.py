"""
Reason DAW Integration
======================

This module provides integration with Propellerhead Reason via
the Remote protocol using Lua codecs.

Architecture:
- Three separate MIDI ports for Reason control surfaces:
  - OpenPush Transport: Play, stop, record, tempo, loop
  - OpenPush Devices: Encoder parameter control
  - OpenPush Mixer: Volume, pan, mute, solo

The bridge translates between Push hardware messages and
Reason Remote SysEx protocol.

Usage:
    from open_push.reason import ReasonBridge

    bridge = ReasonBridge()
    bridge.connect()
    bridge.run()  # Main loop
"""

from .ports import (
    ReasonPortManager,
    VirtualMIDIPort,
    PORT_TRANSPORT,
    PORT_DEVICES,
    PORT_MIXER,
)

from .protocol import (
    ReasonMessage,
    MessageType,
    PortID,
    REASON_SYSEX_HEADER,
)

from .bridge import ReasonBridge, BridgeState

__all__ = [
    'ReasonBridge',
    'BridgeState',
    'ReasonPortManager',
    'VirtualMIDIPort',
    'ReasonMessage',
    'MessageType',
    'PortID',
]
