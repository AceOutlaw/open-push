"""
MIDI-Only Bridge for Ableton Push
=================================

A lightweight MIDI controller bridge that outputs pure MIDI
(notes, CCs, transport) without hardware-specific protocols.

Designed for Pi Zero 2W deployment with outputs to:
- USB MIDI gadget (iPad)
- External USB MIDI devices
- Bluetooth MIDI (wireless)

Usage:
    python -m open_push.midi.app
"""

__all__ = ['MIDIBridge']
__version__ = '0.1.0'


def __getattr__(name):
    """Lazy import to avoid import warning when running as module."""
    if name == 'MIDIBridge':
        from .app import MIDIBridge
        return MIDIBridge
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
