"""
Musical Scale Definitions
=========================

Scale interval patterns for isomorphic keyboard layouts.
All scales are defined as semitone offsets from the root note.
"""

from typing import List, Dict

# Scale definitions (semitones from root)
SCALES: Dict[str, List[int]] = {
    # ===================
    # Western Major Modes
    # ===================
    'major': [0, 2, 4, 5, 7, 9, 11],           # Ionian
    'dorian': [0, 2, 3, 5, 7, 9, 10],
    'phrygian': [0, 1, 3, 5, 7, 8, 10],
    'lydian': [0, 2, 4, 6, 7, 9, 11],
    'mixolydian': [0, 2, 4, 5, 7, 9, 10],
    'aeolian': [0, 2, 3, 5, 7, 8, 10],         # Natural minor
    'locrian': [0, 1, 3, 5, 6, 8, 10],

    # ===================
    # Minor Variants
    # ===================
    'minor': [0, 2, 3, 5, 7, 8, 10],           # Natural minor (same as aeolian)
    'harmonic_minor': [0, 2, 3, 5, 7, 8, 11],
    'melodic_minor': [0, 2, 3, 5, 7, 9, 11],   # Ascending melodic minor

    # ===================
    # Pentatonic Scales
    # ===================
    'major_pentatonic': [0, 2, 4, 7, 9],
    'minor_pentatonic': [0, 3, 5, 7, 10],

    # ===================
    # Blues Scales
    # ===================
    'blues': [0, 3, 5, 6, 7, 10],              # Minor blues (6 notes)
    'minor_blues': [0, 3, 5, 6, 7, 10],        # Same as blues
    'major_blues': [0, 2, 3, 4, 7, 9],         # Major blues

    # ===================
    # Symmetric Scales
    # ===================
    'whole_tone': [0, 2, 4, 6, 8, 10],
    'half_whole_dim': [0, 1, 3, 4, 6, 7, 9, 10],   # Half-whole diminished
    'whole_half_dim': [0, 2, 3, 5, 6, 8, 9, 11],   # Whole-half diminished
    'augmented': [0, 3, 4, 7, 8, 11],

    # ===================
    # Jazz Scales
    # ===================
    'bebop_dominant': [0, 2, 4, 5, 7, 9, 10, 11],
    'bebop_major': [0, 2, 4, 5, 7, 8, 9, 11],
    'altered': [0, 1, 3, 4, 6, 8, 10],         # Super Locrian / Altered dominant
    'lydian_dominant': [0, 2, 4, 6, 7, 9, 10], # Lydian b7

    # ===================
    # World / Ethnic Scales
    # ===================
    # Spanish / Flamenco
    'spanish': [0, 1, 4, 5, 7, 8, 10],         # Phrygian dominant
    'spanish_gypsy': [0, 1, 4, 5, 7, 8, 11],   # Double harmonic

    # Arabic / Middle Eastern
    'arabic': [0, 1, 4, 5, 7, 8, 11],          # Double harmonic major
    'persian': [0, 1, 4, 5, 6, 8, 11],
    'byzantine': [0, 1, 4, 5, 7, 8, 11],       # Same as double harmonic

    # Hungarian
    'hungarian_minor': [0, 2, 3, 6, 7, 8, 11],
    'hungarian_major': [0, 3, 4, 6, 7, 9, 10],

    # Japanese
    'hirajoshi': [0, 2, 3, 7, 8],              # Japanese pentatonic
    'kumoi': [0, 2, 3, 7, 9],                  # Kumoi scale
    'iwato': [0, 1, 5, 6, 10],                 # Iwato scale
    'in_sen': [0, 1, 5, 7, 10],                # In-Sen scale
    'yo': [0, 2, 5, 7, 9],                     # Yo scale (major pentatonic variant)

    # Indonesian
    'pelog': [0, 1, 3, 7, 8],                  # Pelog (Balinese)
    'slendro': [0, 2, 5, 7, 9],                # Slendro (similar to Yo)

    # Indian / Carnatic
    'bhairav': [0, 1, 4, 5, 7, 8, 11],         # Same as double harmonic
    'purvi': [0, 1, 4, 6, 7, 8, 11],

    # Other World
    'egyptian': [0, 2, 5, 7, 10],              # Suspended pentatonic
    'chinese': [0, 4, 6, 7, 11],               # Chinese scale

    # ===================
    # Special / Chromatic
    # ===================
    'chromatic': [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
}

# ===================
# Ordered Scale List for UI
# ===================
# This determines the order scales appear when scrolling with the encoder.
# Organized by category, most useful scales first.

SCALE_NAMES = [
    # Western fundamentals
    'major',
    'minor',
    'harmonic_minor',
    'melodic_minor',

    # Modes
    'dorian',
    'phrygian',
    'lydian',
    'mixolydian',
    'aeolian',
    'locrian',

    # Pentatonic
    'major_pentatonic',
    'minor_pentatonic',

    # Blues
    'blues',
    'minor_blues',
    'major_blues',

    # Symmetric
    'whole_tone',
    'half_whole_dim',
    'whole_half_dim',
    'augmented',

    # Jazz
    'bebop_dominant',
    'bebop_major',
    'altered',
    'lydian_dominant',

    # Spanish / Flamenco
    'spanish',
    'spanish_gypsy',

    # Arabic / Middle Eastern
    'arabic',
    'persian',
    'byzantine',

    # Hungarian
    'hungarian_minor',
    'hungarian_major',

    # Japanese
    'hirajoshi',
    'kumoi',
    'iwato',
    'in_sen',
    'yo',

    # Indonesian
    'pelog',
    'slendro',

    # Indian
    'bhairav',
    'purvi',

    # Other World
    'egyptian',
    'chinese',

    # Full chromatic (last)
    'chromatic',
]

# Extended list with all scales (auto-generated from SCALES dict)
ALL_SCALE_NAMES = list(SCALES.keys())

# Display names for LCD (prettier formatting, max ~15 chars)
SCALE_DISPLAY_NAMES: Dict[str, str] = {
    'major': 'Major',
    'minor': 'Minor',
    'harmonic_minor': 'Harmonic Min',
    'melodic_minor': 'Melodic Min',
    'dorian': 'Dorian',
    'phrygian': 'Phrygian',
    'lydian': 'Lydian',
    'mixolydian': 'Mixolydian',
    'aeolian': 'Aeolian',
    'locrian': 'Locrian',
    'major_pentatonic': 'Major Penta',
    'minor_pentatonic': 'Minor Penta',
    'blues': 'Blues',
    'minor_blues': 'Minor Blues',
    'major_blues': 'Major Blues',
    'whole_tone': 'Whole Tone',
    'half_whole_dim': 'Half-Whole Dim',
    'whole_half_dim': 'Whole-Half Dim',
    'augmented': 'Augmented',
    'bebop_dominant': 'Bebop Dom',
    'bebop_major': 'Bebop Major',
    'altered': 'Altered',
    'lydian_dominant': 'Lydian Dom',
    'spanish': 'Spanish',
    'spanish_gypsy': 'Spanish Gypsy',
    'arabic': 'Arabic',
    'persian': 'Persian',
    'byzantine': 'Byzantine',
    'hungarian_minor': 'Hungarian Min',
    'hungarian_major': 'Hungarian Maj',
    'hirajoshi': 'Hirajoshi',
    'kumoi': 'Kumoi',
    'iwato': 'Iwato',
    'in_sen': 'In-Sen',
    'yo': 'Yo',
    'pelog': 'Pelog',
    'slendro': 'Slendro',
    'bhairav': 'Bhairav',
    'purvi': 'Purvi',
    'egyptian': 'Egyptian',
    'chinese': 'Chinese',
    'chromatic': 'Chromatic',
}

def get_scale_display_name(name: str) -> str:
    """Get the display name for a scale (for LCD)."""
    return SCALE_DISPLAY_NAMES.get(name, name.replace('_', ' ').title())


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
