"""
Mode system for Seqtrak bridge.

Modes represent different operating states with distinct behaviors:
- SeqtrakControlMode: Full hardware control of Seqtrak
- GenericMIDIMode: Use Push as MIDI controller for iPad/other devices
- SystemSettingsMode: Configure Pi bridge system settings
"""

from .base import ModeBase
from .seqtrak_control import SeqtrakControlMode
from .system_settings import SystemSettingsMode

__all__ = ['ModeBase', 'SeqtrakControlMode', 'SystemSettingsMode']
