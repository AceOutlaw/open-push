"""
open-push: Open-source tools for Ableton Push hardware
========================================================

This package provides hardware control for Push 1/2/3 outside of Ableton Live,
with DAW-specific integrations for Reason, Logic, and others.

Modules:
- core: Hardware abstraction (ports, LEDs, display)
- music: Scales and isomorphic layouts
- reason: Reason DAW integration (Phase 2+)
"""

__version__ = "0.3.0"
__author__ = "open-push contributors"

# Core hardware
from .core import Push1Hardware, Push1Display

# Music theory and layouts
from .music import IsomorphicLayout, SCALES, SCALE_NAMES

__all__ = [
    'Push1Hardware',
    'Push1Display',
    'IsomorphicLayout',
    'SCALES',
    'SCALE_NAMES',
]
