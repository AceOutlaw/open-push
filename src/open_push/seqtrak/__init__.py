"""
OpenPush Seqtrak Module
=======================
Bridge between Ableton Push and Yamaha Seqtrak.

Uses core Push hardware abstraction and music modules,
with Seqtrak-specific SysEx protocol handling.

MIDI Architecture:
    - Each Seqtrak track has its own MIDI channel (1-11)
    - Transport uses MIDI Realtime (Start/Stop/Continue)
    - Mute/Solo/Volume use standard MIDI CC on track channel
    - SysEx used only for parameters not available via CC
"""

from .protocol import SeqtrakProtocol, Track, CC, MuteState, SYSEX_HEADER

__all__ = ['SeqtrakProtocol', 'Track', 'CC', 'MuteState', 'SYSEX_HEADER']
