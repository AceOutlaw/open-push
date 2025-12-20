#!/usr/bin/env python3
"""
MIDI Feel Analyzer

Analyzes MIDI performances to extract humanization patterns:
- Timing deviations from grid
- Velocity patterns (bass/treble ratio, dynamics)
- Chord spread (stagger timing)
- Approach/grace note detection
- Inversion preferences

Usage:
    python3 midi_feel_analyzer.py <midi_file>
    python3 midi_feel_analyzer.py <directory>  # Analyze all MIDI files

Output:
    Console summary + optional JSON export

Requirements:
    pip3 install pretty_midi numpy pandas
"""

import sys
import os
import json
from pathlib import Path
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from typing import List, Dict, Tuple, Optional

try:
    import pretty_midi
    import numpy as np
    import pandas as pd
except ImportError:
    print("Missing dependencies. Install with:")
    print("  pip3 install pretty_midi numpy pandas")
    sys.exit(1)


# ============================================================================
# Data Extraction
# ============================================================================

def extract_notes(midi: pretty_midi.PrettyMIDI) -> pd.DataFrame:
    """Extract all notes from MIDI file into a DataFrame."""
    events = []

    for i, instrument in enumerate(midi.instruments):
        if instrument.is_drum:
            continue  # Skip drums for now

        for note in instrument.notes:
            events.append({
                'instrument': i,
                'pitch': note.pitch,
                'start': note.start,
                'end': note.end,
                'duration': note.end - note.start,
                'velocity': note.velocity,
            })

    df = pd.DataFrame(events)
    if len(df) == 0:
        return df

    df = df.sort_values('start').reset_index(drop=True)
    return df


# ============================================================================
# Timing Analysis
# ============================================================================

def calculate_timing_deviations(df: pd.DataFrame, tempo: float) -> pd.DataFrame:
    """Calculate timing deviation from nearest 16th note grid."""
    if len(df) == 0:
        return df

    beat_duration = 60.0 / tempo
    grid_16th = beat_duration / 4  # 16th note duration

    df = df.copy()
    df['beat'] = df['start'] / beat_duration
    df['nearest_16th'] = (df['start'] / grid_16th).round() * grid_16th
    df['timing_deviation_ms'] = (df['start'] - df['nearest_16th']) * 1000

    return df


def analyze_swing(df: pd.DataFrame, tempo: float) -> Optional[float]:
    """Detect swing ratio from 8th note patterns."""
    if len(df) < 10:
        return None

    beat_duration = 60.0 / tempo
    eighth = beat_duration / 2

    # Find notes on off-beats (should be around 0.5 beats after downbeat)
    df = df.copy()
    df['beat_phase'] = (df['start'] / beat_duration) % 1.0

    # Notes between 0.4 and 0.7 beat phase are potential off-beats
    off_beats = df[(df['beat_phase'] > 0.4) & (df['beat_phase'] < 0.7)]

    if len(off_beats) < 5:
        return None

    # Average off-beat position
    mean_phase = off_beats['beat_phase'].mean()

    # Convert to swing ratio (0.5 = straight, 0.67 = triplet swing)
    swing_ratio = mean_phase / (1.0 - mean_phase) if mean_phase < 1.0 else 0.5

    return swing_ratio


# ============================================================================
# Velocity Analysis
# ============================================================================

def analyze_velocity(df: pd.DataFrame) -> Dict:
    """Analyze velocity patterns."""
    if len(df) == 0:
        return {}

    # Basic stats
    stats = {
        'mean': float(df['velocity'].mean()),
        'std': float(df['velocity'].std()),
        'min': int(df['velocity'].min()),
        'max': int(df['velocity'].max()),
    }

    # Bass/treble ratio (below/above middle C = 60)
    bass_notes = df[df['pitch'] < 60]
    treble_notes = df[df['pitch'] >= 60]

    if len(bass_notes) > 0 and len(treble_notes) > 0:
        bass_vel = bass_notes['velocity'].mean()
        treble_vel = treble_notes['velocity'].mean()
        stats['bass_treble_ratio'] = float(bass_vel / treble_vel) if treble_vel > 0 else 1.0
    else:
        stats['bass_treble_ratio'] = 1.0

    # Downbeat accent (requires beat info)
    if 'beat' in df.columns:
        df = df.copy()
        df['is_downbeat'] = (df['beat'] % 1.0) < 0.1
        downbeats = df[df['is_downbeat']]
        upbeats = df[~df['is_downbeat']]

        if len(downbeats) > 0 and len(upbeats) > 0:
            stats['downbeat_accent'] = float(
                downbeats['velocity'].mean() / upbeats['velocity'].mean()
            )
        else:
            stats['downbeat_accent'] = 1.0

    return stats


# ============================================================================
# Chord Detection & Analysis
# ============================================================================

def detect_chords(df: pd.DataFrame, threshold_ms: float = 50) -> pd.DataFrame:
    """Group notes into chords based on timing proximity."""
    if len(df) == 0:
        return df

    df = df.copy()
    df = df.sort_values('start').reset_index(drop=True)

    chord_id = 0
    chord_ids = []
    last_start = -1.0

    for _, row in df.iterrows():
        if (row['start'] - last_start) * 1000 > threshold_ms:
            chord_id += 1
        chord_ids.append(chord_id)
        last_start = row['start']

    df['chord_id'] = chord_ids
    return df


def analyze_chord_feel(df: pd.DataFrame) -> Dict:
    """Extract chord spread and velocity patterns within chords."""
    if 'chord_id' not in df.columns or len(df) == 0:
        return {}

    chord_groups = df.groupby('chord_id')

    spreads = []
    velocity_ranges = []
    chord_sizes = []
    directions = {'bottom_up': 0, 'top_down': 0, 'mixed': 0}

    for _, chord in chord_groups:
        if len(chord) < 2:
            continue

        chord_sizes.append(len(chord))

        # Timing spread
        spread = (chord['start'].max() - chord['start'].min()) * 1000
        spreads.append(spread)

        # Velocity range
        vel_range = chord['velocity'].max() - chord['velocity'].min()
        velocity_ranges.append(vel_range)

        # Direction (bottom-up or top-down?)
        chord_sorted = chord.sort_values('start')
        pitches_in_order = chord_sorted['pitch'].tolist()

        if len(pitches_in_order) >= 2:
            # Check if pitches increase or decrease with time
            pitch_diffs = [pitches_in_order[i+1] - pitches_in_order[i]
                           for i in range(len(pitches_in_order)-1)]
            if all(d >= 0 for d in pitch_diffs):
                directions['bottom_up'] += 1
            elif all(d <= 0 for d in pitch_diffs):
                directions['top_down'] += 1
            else:
                directions['mixed'] += 1

    if not spreads:
        return {}

    # Determine dominant direction
    total_dirs = sum(directions.values())
    if total_dirs > 0:
        dominant = max(directions, key=directions.get)
        direction_pct = directions[dominant] / total_dirs
    else:
        dominant = 'mixed'
        direction_pct = 0

    return {
        'mean_spread_ms': float(np.mean(spreads)),
        'std_spread_ms': float(np.std(spreads)),
        'max_spread_ms': float(np.max(spreads)),
        'mean_velocity_range': float(np.mean(velocity_ranges)),
        'mean_chord_size': float(np.mean(chord_sizes)),
        'dominant_direction': dominant,
        'direction_confidence': float(direction_pct),
        'direction_counts': directions,
    }


# ============================================================================
# Approach Note Detection
# ============================================================================

def detect_approach_notes(df: pd.DataFrame, threshold_ms: float = 80) -> List[int]:
    """Identify notes that are likely approach/grace notes.

    Criteria:
    - Short duration
    - Small pitch interval to next note (1-2 semitones)
    - Lower velocity than target note
    """
    if len(df) < 2:
        return []

    df_sorted = df.sort_values('start').reset_index(drop=True)
    approach_indices = []

    for i in range(len(df_sorted) - 1):
        current = df_sorted.iloc[i]
        next_note = df_sorted.iloc[i + 1]

        time_diff = (next_note['start'] - current['start']) * 1000
        pitch_diff = abs(next_note['pitch'] - current['pitch'])

        # Criteria for approach note
        if (time_diff < threshold_ms and
            1 <= pitch_diff <= 2 and
            current['velocity'] < next_note['velocity']):
            approach_indices.append(i)

    return approach_indices


def detect_grace_notes(df: pd.DataFrame, max_duration_ms: float = 50) -> List[int]:
    """Identify very short notes (likely grace notes/ornaments)."""
    if len(df) == 0:
        return []

    grace_indices = []
    for i, row in df.iterrows():
        duration_ms = row['duration'] * 1000
        if duration_ms < max_duration_ms:
            grace_indices.append(i)

    return grace_indices


def detect_ghost_notes(df: pd.DataFrame, velocity_threshold: int = 50) -> List[int]:
    """Identify quiet notes (likely ghost/texture notes)."""
    if len(df) == 0:
        return []

    ghost_indices = []
    for i, row in df.iterrows():
        if row['velocity'] < velocity_threshold:
            ghost_indices.append(i)

    return ghost_indices


# ============================================================================
# Inversion Analysis
# ============================================================================

def analyze_inversions(df: pd.DataFrame) -> Dict:
    """Analyze which inversions are used for chords."""
    if 'chord_id' not in df.columns or len(df) == 0:
        return {}

    inversion_counts = defaultdict(lambda: defaultdict(int))

    for _, chord in df.groupby('chord_id'):
        if len(chord) < 3:
            continue

        pitches = sorted(chord['pitch'].tolist())
        bass_pc = pitches[0] % 12  # Pitch class of bass note

        # Get intervals from bass
        intervals = [(p - pitches[0]) % 12 for p in pitches]
        intervals = sorted(set(intervals))

        # Identify chord type by interval pattern
        chord_type = identify_chord_type(intervals)
        if chord_type == 'unknown':
            continue

        # Identify root
        root_pc = identify_root(pitches, chord_type)
        if root_pc is None:
            continue

        # Determine inversion
        bass_interval = (bass_pc - root_pc) % 12
        if bass_interval == 0:
            inversion = 'root'
        elif bass_interval in [3, 4]:  # 3rd in bass
            inversion = 'first'
        elif bass_interval in [7]:  # 5th in bass
            inversion = 'second'
        elif bass_interval in [10, 11]:  # 7th in bass
            inversion = 'third'
        else:
            inversion = 'other'

        inversion_counts[chord_type][inversion] += 1

    # Convert to percentages
    result = {}
    for chord_type, inversions in inversion_counts.items():
        total = sum(inversions.values())
        result[chord_type] = {
            inv: round(count / total * 100, 1)
            for inv, count in inversions.items()
        }

    return result


def identify_chord_type(intervals: List[int]) -> str:
    """Identify chord type from interval pattern."""
    intervals_set = set(intervals)

    # Common patterns (from bass)
    if {0, 4, 7}.issubset(intervals_set):
        return 'major'
    elif {0, 3, 7}.issubset(intervals_set):
        return 'minor'
    elif {0, 3, 6}.issubset(intervals_set):
        return 'diminished'
    elif {0, 4, 8}.issubset(intervals_set):
        return 'augmented'
    elif {0, 5, 7}.issubset(intervals_set):
        return 'sus4'
    elif {0, 2, 7}.issubset(intervals_set):
        return 'sus2'

    return 'unknown'


def identify_root(pitches: List[int], chord_type: str) -> Optional[int]:
    """Identify the root pitch class of a chord."""
    # Simplified: assume root position for this analysis
    # In reality, you'd need to check all rotations

    bass_pc = pitches[0] % 12

    if chord_type == 'major':
        # Root is likely the bass note in root position
        # or bass + 5 semitones (first inversion)
        # or bass + 8 semitones (second inversion)
        return bass_pc  # Simplified

    elif chord_type == 'minor':
        return bass_pc

    return bass_pc


# ============================================================================
# Summary & Reporting
# ============================================================================

@dataclass
class PerformanceProfile:
    """Summary of a performance's feel characteristics."""
    file_name: str
    total_notes: int
    duration_seconds: float
    tempo_bpm: float

    # Timing
    timing_deviation_mean_ms: float
    timing_deviation_std_ms: float
    swing_ratio: Optional[float]

    # Velocity
    velocity_mean: float
    velocity_std: float
    bass_treble_ratio: float
    downbeat_accent: float

    # Chord feel
    chord_spread_mean_ms: float
    chord_spread_std_ms: float
    chord_direction: str

    # Embellishment
    approach_note_pct: float
    grace_note_pct: float
    ghost_note_pct: float

    # Inversions
    inversion_preferences: Dict


def analyze_midi_file(midi_path: str) -> Optional[PerformanceProfile]:
    """Complete analysis of a MIDI file."""
    try:
        midi = pretty_midi.PrettyMIDI(midi_path)
    except Exception as e:
        print(f"Error loading {midi_path}: {e}")
        return None

    # Basic info
    tempo = midi.estimate_tempo()
    duration = midi.get_end_time()

    # Extract notes
    df = extract_notes(midi)
    if len(df) == 0:
        print(f"No notes found in {midi_path}")
        return None

    # Timing analysis
    df = calculate_timing_deviations(df, tempo)
    swing = analyze_swing(df, tempo)

    # Velocity analysis
    vel_stats = analyze_velocity(df)

    # Chord analysis
    df = detect_chords(df)
    chord_feel = analyze_chord_feel(df)

    # Embellishment
    approach_notes = detect_approach_notes(df)
    grace_notes = detect_grace_notes(df)
    ghost_notes = detect_ghost_notes(df)

    # Inversions
    inversions = analyze_inversions(df)

    return PerformanceProfile(
        file_name=os.path.basename(midi_path),
        total_notes=len(df),
        duration_seconds=round(duration, 2),
        tempo_bpm=round(tempo, 1),

        timing_deviation_mean_ms=round(df['timing_deviation_ms'].mean(), 2),
        timing_deviation_std_ms=round(df['timing_deviation_ms'].std(), 2),
        swing_ratio=round(swing, 3) if swing else None,

        velocity_mean=round(vel_stats.get('mean', 0), 1),
        velocity_std=round(vel_stats.get('std', 0), 1),
        bass_treble_ratio=round(vel_stats.get('bass_treble_ratio', 1.0), 2),
        downbeat_accent=round(vel_stats.get('downbeat_accent', 1.0), 2),

        chord_spread_mean_ms=round(chord_feel.get('mean_spread_ms', 0), 2),
        chord_spread_std_ms=round(chord_feel.get('std_spread_ms', 0), 2),
        chord_direction=chord_feel.get('dominant_direction', 'unknown'),

        approach_note_pct=round(len(approach_notes) / len(df) * 100, 2),
        grace_note_pct=round(len(grace_notes) / len(df) * 100, 2),
        ghost_note_pct=round(len(ghost_notes) / len(df) * 100, 2),

        inversion_preferences=inversions,
    )


def print_profile(profile: PerformanceProfile):
    """Pretty-print a performance profile."""
    print("=" * 60)
    print(f"File: {profile.file_name}")
    print("=" * 60)
    print(f"Notes: {profile.total_notes}")
    print(f"Duration: {profile.duration_seconds}s")
    print(f"Tempo: {profile.tempo_bpm} BPM")
    print()

    print("=== Timing ===")
    print(f"Mean deviation: {profile.timing_deviation_mean_ms:+.2f} ms")
    print(f"Deviation std:  {profile.timing_deviation_std_ms:.2f} ms")
    if profile.swing_ratio:
        swing_pct = (profile.swing_ratio - 0.5) / 0.5 * 100
        print(f"Swing ratio:    {profile.swing_ratio:.3f} ({swing_pct:+.0f}% swing)")
    print()

    print("=== Velocity ===")
    print(f"Mean:           {profile.velocity_mean:.1f}")
    print(f"Std:            {profile.velocity_std:.1f}")
    print(f"Bass/Treble:    {profile.bass_treble_ratio:.2f}x")
    print(f"Downbeat:       {profile.downbeat_accent:.2f}x")
    print()

    print("=== Chord Feel ===")
    print(f"Mean spread:    {profile.chord_spread_mean_ms:.2f} ms")
    print(f"Spread std:     {profile.chord_spread_std_ms:.2f} ms")
    print(f"Direction:      {profile.chord_direction}")
    print()

    print("=== Embellishment ===")
    print(f"Approach notes: {profile.approach_note_pct:.1f}%")
    print(f"Grace notes:    {profile.grace_note_pct:.1f}%")
    print(f"Ghost notes:    {profile.ghost_note_pct:.1f}%")
    print()

    if profile.inversion_preferences:
        print("=== Inversion Preferences ===")
        for chord_type, inversions in profile.inversion_preferences.items():
            inv_str = ", ".join(f"{k}: {v}%" for k, v in inversions.items())
            print(f"  {chord_type}: {inv_str}")
    print()


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    path = sys.argv[1]

    if os.path.isfile(path):
        # Single file
        profile = analyze_midi_file(path)
        if profile:
            print_profile(profile)

            # Export JSON option
            if '--json' in sys.argv:
                json_path = path.rsplit('.', 1)[0] + '_analysis.json'
                with open(json_path, 'w') as f:
                    json.dump(asdict(profile), f, indent=2)
                print(f"Exported to: {json_path}")

    elif os.path.isdir(path):
        # Directory - analyze all MIDI files
        midi_files = list(Path(path).glob('**/*.mid')) + list(Path(path).glob('**/*.midi'))
        print(f"Found {len(midi_files)} MIDI files in {path}\n")

        profiles = []
        for midi_file in midi_files:
            profile = analyze_midi_file(str(midi_file))
            if profile:
                profiles.append(profile)
                print(f"Analyzed: {profile.file_name} ({profile.total_notes} notes)")

        if profiles:
            print("\n" + "=" * 60)
            print("AGGREGATE STATISTICS")
            print("=" * 60)

            # Average timing
            mean_dev = np.mean([p.timing_deviation_mean_ms for p in profiles])
            print(f"Avg timing deviation: {mean_dev:+.2f} ms")

            # Average chord spread
            mean_spread = np.mean([p.chord_spread_mean_ms for p in profiles])
            print(f"Avg chord spread: {mean_spread:.2f} ms")

            # Direction preference
            directions = [p.chord_direction for p in profiles]
            dir_counts = Counter(directions)
            print(f"Direction preferences: {dict(dir_counts)}")

            # Export all to JSON
            if '--json' in sys.argv:
                json_path = os.path.join(path, 'analysis_summary.json')
                with open(json_path, 'w') as f:
                    json.dump([asdict(p) for p in profiles], f, indent=2)
                print(f"\nExported to: {json_path}")

    else:
        print(f"Error: {path} not found")
        sys.exit(1)


if __name__ == '__main__':
    main()
