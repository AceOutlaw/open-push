"""
Music theory and layout module.

Provides scale definitions and isomorphic keyboard layouts
for the Push pad grid.
"""

from .scales import (
    SCALES,
    SCALE_NAMES,
    ALL_SCALE_NAMES,
    get_scale,
    is_in_scale,
    is_root_note,
    get_scale_degree,
)

from .layout import (
    IsomorphicLayout,
    LAYOUT_PRESETS,
)
