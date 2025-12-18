"""
Isomorphic Keyboard Layouts
===========================

Provides mapping from Push pad grid to MIDI notes using
isomorphic (shape-preserving) layouts.

In an isomorphic layout, the same fingering pattern produces
the same chord/interval in any key.
"""

from typing import Dict, Optional, Tuple, List
from .scales import SCALES, is_in_scale, is_root_note


# Layout presets: (row_interval, col_interval, name)
LAYOUT_PRESETS = {
    'fourths_up': (5, 1, 'Fourths Up'),      # Standard guitar-like
    'fourths_right': (1, 5, 'Fourths Right'),
    'thirds_up': (4, 1, 'Thirds Up'),
    'thirds_right': (1, 4, 'Thirds Right'),
    'fifths_up': (7, 1, 'Fifths Up'),
    'fifths_right': (1, 7, 'Fifths Right'),
    'octaves_up': (12, 1, 'Octaves Up'),
    'sequential': (8, 1, 'Sequential'),       # Piano-like
}


class IsomorphicLayout:
    """
    Isomorphic keyboard layout for Push pad grid.

    Maps the 8x8 pad grid to MIDI notes using configurable
    row and column intervals. Default is fourths layout
    (row +5 semitones, column +1 semitone).

    Supports two modes:
    - Chromatic: All notes available, scale notes highlighted
    - In-Key: Only scale notes on pads

    Usage:
        layout = IsomorphicLayout(root_note=36)  # C2
        midi_note = layout.get_midi_note(pad_note)

        # Or by position:
        midi_note = layout.get_note_at(row=2, col=3)

        # In-key mode:
        layout.set_in_key_mode(True, root=0, scale='minor')
        midi_note = layout.get_note_at(row=2, col=3)  # Returns scale note
    """

    def __init__(
        self,
        root_note: int = 36,
        row_interval: int = 5,
        col_interval: int = 1
    ):
        """
        Initialize layout.

        Args:
            root_note: MIDI note for bottom-left pad (default 36 = C2)
            row_interval: Semitones between rows (default 5 = fourth)
            col_interval: Semitones between columns (default 1)
        """
        self.root_note = root_note
        self.row_interval = row_interval
        self.col_interval = col_interval

        # In-key mode settings
        self.in_key_mode = False
        self.scale_root = 0  # 0-11, where 0=C
        self.scale_name = 'minor'
        self.scale = SCALES[self.scale_name]
        self.in_key_row_interval = 3  # Scale degrees per row

        # Note map cache (chromatic mode)
        self._note_map: Dict[int, int] = {}
        self._rebuild_map()

    def _rebuild_map(self):
        """Rebuild the chromatic note map."""
        self._note_map.clear()
        for row in range(8):
            for col in range(8):
                pad_note = 36 + (row * 8) + col
                midi_note = self.root_note + (row * self.row_interval) + (col * self.col_interval)
                self._note_map[pad_note] = midi_note

    # =========================================================================
    # ROOT NOTE AND OCTAVE
    # =========================================================================

    def set_root_note(self, root_note: int):
        """Change the root note and rebuild the map."""
        self.root_note = root_note
        self._rebuild_map()

    def shift_octave(self, direction: int) -> int:
        """
        Shift octave up (+1) or down (-1).

        Args:
            direction: +1 for up, -1 for down

        Returns:
            New octave number
        """
        new_root = self.root_note + (direction * 12)
        # Clamp to valid MIDI range (keep playable range)
        if 0 <= new_root <= 96:
            self.root_note = new_root
            self._rebuild_map()
        return self.get_octave()

    def get_octave(self) -> int:
        """Get current octave number (based on root note)."""
        return (self.root_note // 12) - 1

    # =========================================================================
    # LAYOUT CONFIGURATION
    # =========================================================================

    def set_layout(self, preset: str):
        """
        Set layout from a preset name.

        Args:
            preset: One of LAYOUT_PRESETS keys
        """
        if preset in LAYOUT_PRESETS:
            self.row_interval, self.col_interval, _ = LAYOUT_PRESETS[preset]
            self._rebuild_map()

    def set_intervals(self, row_interval: int, col_interval: int):
        """
        Set custom row and column intervals.

        Args:
            row_interval: Semitones per row
            col_interval: Semitones per column
        """
        self.row_interval = row_interval
        self.col_interval = col_interval
        self._rebuild_map()

    # =========================================================================
    # SCALE AND IN-KEY MODE
    # =========================================================================

    def set_scale(self, root: int, scale_name: str):
        """
        Set the scale for highlighting and in-key mode.

        Args:
            root: Root note (0-11, where 0=C)
            scale_name: Scale name from SCALES dict
        """
        self.scale_root = root % 12
        self.scale_name = scale_name
        self.scale = SCALES.get(scale_name, SCALES['chromatic'])

    def set_in_key_mode(self, enabled: bool, root: int = None, scale: str = None):
        """
        Enable/disable in-key mode.

        In in-key mode, pads only produce scale notes.
        The layout uses scale degrees instead of semitones.

        Args:
            enabled: True to enable in-key mode
            root: Optional root note to set (0-11)
            scale: Optional scale name to set
        """
        self.in_key_mode = enabled
        if root is not None:
            self.scale_root = root % 12
        if scale is not None:
            self.scale_name = scale
            self.scale = SCALES.get(scale, SCALES['chromatic'])

    # =========================================================================
    # NOTE MAPPING
    # =========================================================================

    def get_midi_note(self, pad_note: int) -> int:
        """
        Get MIDI note for a pad (by pad note number).

        Args:
            pad_note: Pad MIDI note (36-99)

        Returns:
            Output MIDI note
        """
        if self.in_key_mode:
            row = (pad_note - 36) // 8
            col = (pad_note - 36) % 8
            return self._get_in_key_note(row, col)
        return self._note_map.get(pad_note, pad_note)

    def get_note_at(self, row: int, col: int) -> int:
        """
        Get MIDI note at grid position.

        Args:
            row: Row (0-7, bottom to top)
            col: Column (0-7, left to right)

        Returns:
            MIDI note number
        """
        if self.in_key_mode:
            return self._get_in_key_note(row, col)
        pad_note = 36 + (row * 8) + col
        return self._note_map.get(pad_note, 0)

    def _get_in_key_note(self, row: int, col: int) -> int:
        """
        Calculate MIDI note for in-key mode.

        In this mode, pads map to scale degrees, not semitones.
        This ensures all pads produce in-scale notes.
        """
        scale_len = len(self.scale)

        # Calculate which scale degree this pad represents
        scale_degree = (row * self.in_key_row_interval) + col

        # Calculate octave offset and position within scale
        octave_offset = scale_degree // scale_len
        note_index = scale_degree % scale_len

        # Get the actual semitone offset from the scale
        semitone = self.scale[note_index]

        # Calculate final MIDI note
        base_note = self.root_note + self.scale_root
        midi_note = base_note + (octave_offset * 12) + semitone

        return midi_note

    # =========================================================================
    # GRID INFORMATION
    # =========================================================================

    def is_in_scale(self, pad_note: int) -> bool:
        """Check if a pad's note is in the current scale."""
        midi_note = self.get_midi_note(pad_note)
        return is_in_scale(midi_note, self.scale_root, self.scale)

    def is_root(self, pad_note: int) -> bool:
        """Check if a pad's note is a root note."""
        midi_note = self.get_midi_note(pad_note)
        return is_root_note(midi_note, self.scale_root)

    def get_pad_info(self, row: int, col: int) -> dict:
        """
        Get information about a pad position.

        Args:
            row: Row (0-7)
            col: Column (0-7)

        Returns:
            Dict with note, is_root, is_in_scale, note_name
        """
        from ..core.constants import note_name

        midi_note = self.get_note_at(row, col)
        return {
            'note': midi_note,
            'is_root': is_root_note(midi_note, self.scale_root),
            'is_in_scale': is_in_scale(midi_note, self.scale_root, self.scale),
            'note_name': note_name(midi_note),
        }

    def get_grid_notes(self) -> List[List[int]]:
        """
        Get all MIDI notes for the 8x8 grid.

        Returns:
            8x8 list of MIDI note numbers
        """
        grid = []
        for row in range(8):
            row_notes = []
            for col in range(8):
                row_notes.append(self.get_note_at(row, col))
            grid.append(row_notes)
        return grid
