"""
Core hardware abstraction layer for Push controllers.

This module provides low-level access to Push hardware:
- Port detection and connection
- SysEx communication
- LED control (pads and buttons)
- LCD display management
"""

from .constants import *
from .hardware import Push1Hardware
from .display import Push1Display
