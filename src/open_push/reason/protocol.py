"""
Reason Remote Protocol
======================

Defines the SysEx protocol for communication between
open-push and Reason via the Remote system.

Protocol Design:
- Uses manufacturer ID 0x00 0x11 0x22 (placeholder, non-registered)
- Message structure: F0 00 11 22 [port_id] [msg_type] [data...] F7

This module handles encoding/decoding of messages between
the Python bridge and Reason Lua codecs.
"""

from enum import IntEnum
from dataclasses import dataclass
from typing import List, Optional, Tuple


# SysEx header for Reason Remote communication
# Using a unique pattern to distinguish from Push SysEx
REASON_SYSEX_HEADER = [0x00, 0x11, 0x22]


class PortID(IntEnum):
    """Port identifiers for routing messages."""
    TRANSPORT = 0x01
    DEVICES = 0x02
    MIXER = 0x03


class MessageType(IntEnum):
    """Message types for Reason communication."""
    # Transport messages (0x10-0x1F)
    TRANSPORT_PLAY = 0x10
    TRANSPORT_STOP = 0x11
    TRANSPORT_RECORD = 0x12
    TRANSPORT_REWIND = 0x13
    TRANSPORT_FORWARD = 0x14
    TRANSPORT_LOOP = 0x15
    TRANSPORT_TEMPO = 0x16
    TRANSPORT_METRONOME = 0x17
    TRANSPORT_POSITION = 0x18  # Song position

    # Device messages (0x20-0x2F)
    DEVICE_ENCODER = 0x20      # Encoder turn
    DEVICE_ENCODER_TOUCH = 0x21  # Encoder touch
    DEVICE_BUTTON = 0x22       # Device button press
    DEVICE_SELECT = 0x23       # Select device
    DEVICE_PARAM = 0x24        # Parameter value update (from Reason)
    DEVICE_NAME = 0x25         # Device name (from Reason)

    # Mixer messages (0x30-0x3F)
    MIXER_VOLUME = 0x30
    MIXER_PAN = 0x31
    MIXER_MUTE = 0x32
    MIXER_SOLO = 0x33
    MIXER_ARM = 0x34
    MIXER_SELECT = 0x35        # Select track
    MIXER_NAME = 0x36          # Track name (from Reason)
    MIXER_LEVEL = 0x37         # Meter level (from Reason)

    # Display messages (0x40-0x4F)
    DISPLAY_LINE = 0x40        # Set display line text
    DISPLAY_FIELD = 0x41       # Set display field text
    DISPLAY_CLEAR = 0x42       # Clear display
    REQUEST_LCD = 0x4F         # Request LCD text update from Reason

    # System messages (0x70-0x7F) - Must be <=0x7F for valid SysEx data
    SYSTEM_PING = 0x70
    SYSTEM_PONG = 0x71
    SYSTEM_VERSION = 0x72
    SYSTEM_ERROR = 0x7F


@dataclass
class ReasonMessage:
    """A parsed message from/to Reason."""
    port_id: PortID
    msg_type: MessageType
    data: List[int]

    def to_sysex(self) -> List[int]:
        """Convert to SysEx data bytes."""
        return REASON_SYSEX_HEADER + [self.port_id, self.msg_type] + self.data

    @classmethod
    def from_sysex(cls, data: List[int]) -> Optional['ReasonMessage']:
        """
        Parse SysEx data into a ReasonMessage.

        Args:
            data: SysEx data bytes (without F0/F7 framing)

        Returns:
            ReasonMessage or None if invalid
        """
        if len(data) < 5:
            return None

        # Check header
        if data[0:3] != REASON_SYSEX_HEADER:
            return None

        try:
            port_id = PortID(data[3])
            msg_type = MessageType(data[4])
            payload = data[5:] if len(data) > 5 else []
            return cls(port_id, msg_type, payload)
        except ValueError:
            return None


# =============================================================================
# MESSAGE BUILDERS
# =============================================================================

def build_transport_message(msg_type: MessageType, value: int = 0) -> ReasonMessage:
    """Build a transport control message."""
    return ReasonMessage(
        port_id=PortID.TRANSPORT,
        msg_type=msg_type,
        data=[value]
    )


def build_encoder_message(encoder: int, delta: int, touch: bool = False) -> ReasonMessage:
    """
    Build an encoder message.

    Args:
        encoder: Encoder number (0-7)
        delta: Relative change (-64 to +63, encoded as 0-127)
        touch: True for touch event, False for turn event
    """
    # Encode delta: 64 = no change, <64 = negative, >64 = positive
    encoded_delta = max(0, min(127, delta + 64))

    return ReasonMessage(
        port_id=PortID.DEVICES,
        msg_type=MessageType.DEVICE_ENCODER_TOUCH if touch else MessageType.DEVICE_ENCODER,
        data=[encoder, encoded_delta]
    )


def build_mixer_message(msg_type: MessageType, channel: int, value: int) -> ReasonMessage:
    """
    Build a mixer control message.

    Args:
        msg_type: MIXER_VOLUME, MIXER_PAN, etc.
        channel: Mixer channel (0-7)
        value: Control value (0-127 or 0/1 for toggles)
    """
    return ReasonMessage(
        port_id=PortID.MIXER,
        msg_type=msg_type,
        data=[channel, value]
    )


def build_display_line(line: int, text: str) -> ReasonMessage:
    """
    Build a display line message.

    Args:
        line: Line number (1-4)
        text: Text to display (up to 68 chars)
    """
    # Truncate and encode text
    text = text[:68]
    text_data = [ord(c) for c in text]

    return ReasonMessage(
        port_id=PortID.TRANSPORT,  # Display updates go through transport
        msg_type=MessageType.DISPLAY_LINE,
        data=[line] + text_data
    )


# =============================================================================
# MESSAGE PARSERS
# =============================================================================

def parse_param_update(msg: ReasonMessage) -> Optional[Tuple[int, int, str]]:
    """
    Parse a parameter update message from Reason.

    Returns:
        Tuple of (param_index, value, name) or None
    """
    if msg.msg_type != MessageType.DEVICE_PARAM:
        return None

    if len(msg.data) < 2:
        return None

    param_index = msg.data[0]
    value = msg.data[1]
    name = ''.join(chr(c) for c in msg.data[2:]) if len(msg.data) > 2 else ''

    return (param_index, value, name)


def parse_track_name(msg: ReasonMessage) -> Optional[Tuple[int, str]]:
    """
    Parse a track name message from Reason.

    Returns:
        Tuple of (channel, name) or None
    """
    if msg.msg_type != MessageType.MIXER_NAME:
        return None

    if len(msg.data) < 1:
        return None

    channel = msg.data[0]
    name = ''.join(chr(c) for c in msg.data[1:]) if len(msg.data) > 1 else ''

    return (channel, name)


# =============================================================================
# DELTA ENCODING FOR RELATIVE ENCODERS
# =============================================================================

def decode_delta(value: int) -> int:
    """
    Decode a relative encoder delta from MIDI value.

    MIDI CC uses two's complement style for relative values:
    - Values 1-63: positive (clockwise)
    - Values 65-127: negative (counter-clockwise)
    - Value 0 and 64: no change

    Args:
        value: Raw MIDI CC value (0-127)

    Returns:
        Signed delta (-63 to +63)
    """
    if value == 0 or value == 64:
        return 0
    elif value < 64:
        return value  # Positive
    else:
        return value - 128  # Negative (65->-63, 127->-1)


def encode_delta(delta: int) -> int:
    """
    Encode a relative delta to MIDI CC value.

    Args:
        delta: Signed delta (-63 to +63)

    Returns:
        MIDI CC value (0-127)
    """
    if delta >= 0:
        return min(63, delta)
    else:
        return 128 + max(-63, delta)
