# UNFINISHED / NOT RUNNING: part of the planned runtime mode switching (Seqtrak / generic MIDI /
# system settings, see raspberry-pi-setup/MODE-SWITCHING-DESIGN.md, local only). The Pi service runs
# src/open_push/seqtrak/app.py directly; this code is not used and has drifted from it (it calls
# bridge methods that no longer exist). Rebuild on the current bridge rather than reviving it as is.
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
