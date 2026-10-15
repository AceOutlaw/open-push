# UNFINISHED / NOT RUNNING: part of the planned runtime mode switching (Seqtrak / generic MIDI /
# system settings, see raspberry-pi-setup/MODE-SWITCHING-DESIGN.md, local only). The Pi service runs
# src/open_push/seqtrak/app.py directly; this code is not used and has drifted from it (it calls
# bridge methods that no longer exist). Rebuild on the current bridge rather than reviving it as is.
"""
Helper utilities for Seqtrak bridge.

Provides system-level helpers for mode switching and settings management.
"""

from .subprocess_manager import SubprocessManager

__all__ = ['SubprocessManager']
