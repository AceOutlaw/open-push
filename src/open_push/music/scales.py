"""
Musical Scale Definitions
=========================

Scale interval patterns for isomorphic keyboard layouts.
All scales are defined as semitone offsets from the root note.
"""

from typing import List, Dict

# Scale definitions (semitones from root)
SCALES: Dict[str, List[int]] = {
    # Major modes
    'major': [0, 2, 4, 5, 7, 9, 11],
    'dorian': [0, 2, 3, 5, 7, 9, 10],
    'phrygian': [0, 1, 3, 5, 7, 8, 10],
    'lydian': [0, 2, 4, 6, 7, 9, 11],
    'mixolydian': [0, 2, 4, 5, 7, 9, 10],
    'aeolian': [0, 2, 3, 5, 7, 8, 10],  # Natural minor
    'locrian': [0, 1, 3, 5, 6, 8, 10],

    # Minor scales
    'minor': [0, 2, 3, 5, 7, 8, 10],  # Natural minor (same as aeolian)
    'harmonic_minor': [0, 2, 3, 5, 7, 8, 11],
    'melodic_minor': [0, 2, 3, 5, 7, 9, 11],

    # Pentatonic scales
    'pentatonic_major': [0, 2, 4, 7, 9],
    'pentatonic_minor': [0, 3, 5, 7, 10],
    'pentatonic': [0, 3, 5, 7, 10],  # Alias for minor pentatonic

    # Blues and jazz
    'blues': [0, 3, 5, 6, 7, 10],
    'bebop_dominant': [0, 2, 4, 5, 7, 9, 10, 11],
    'bebop_major': [0, 2, 4, 5, 7, 8, 9, 11],

    # World scales
    'spanish': [0, 1, 4, 5, 7, 8, 10],  # Phrygian dominant
    'arabic': [0, 1, 4, 5, 7, 8, 11],
    'hungarian_minor': [0, 2, 3, 6, 7, 8, 11],
    'japanese': [0, 1, 5, 7, 8],

    # Symmetric scales
    'whole_tone': [0, 2, 4, 6, 8, 10],
    'diminished': [0, 2, 3, 5, 6, 8, 9, 11],  # Half-whole
    'augmented': [0, 3, 4, 7, 8, 11],

    # Special
    'chromatic': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
}

# Ordered list for UI selection (most common scales first)
SCALE_NAMES = [
    'major',
    'minor',
    'dorian',
    'pentatonic',
    'blues',
    'mixolydian',
    'lydian',
    'phrygian',
    'harmonic_minor',
    'melodic_minor',
    'whole_tone',
    'chromatic',
]

# Extended list with all scales
ALL_SCALE_NAMES = list(SCALES.keys())


def get_scale(name: str) -> List[int]:
    """
    Get scale intervals by name.

    Args:
        name: Scale name (case-insensitive)

    Returns:
        List of semitone offsets from root
    """
    return SCALES.get(name.lower(), SCALES['chromatic'])


def is_in_scale(note: int, root: int, scale: List[int]) -> bool:
    """
    Check if a MIDI note is in the given scale.

    Args:
        note: MIDI note number
        root: Root note (0-11, where 0=C)
        scale: List of scale intervals

    Returns:
        True if note is in scale
    """
    degree = (note - root) % 12
    return degree in scale


def is_root_note(note: int, root: int) -> bool:
    """
    Check if a MIDI note is a root note (any octave).

    Args:
        note: MIDI note number
        root: Root note (0-11, where 0=C)

    Returns:
        True if note is a root
    """
    return (note - root) % 12 == 0


def get_scale_degree(note: int, root: int, scale: List[int]) -> int:
    """
    Get the scale degree of a note (1-based).

    Args:
        note: MIDI note number
        root: Root note (0-11)
        scale: List of scale intervals

    Returns:
        Scale degree (1-7 for 7-note scales) or 0 if not in scale
    """
    semitone = (note - root) % 12
    try:
        return scale.index(semitone) + 1
    except ValueError:
        return 0
