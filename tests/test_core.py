#!/usr/bin/env python3
"""
Test core modules without hardware connected.
Run with: python3 tests/test_core.py
"""

import sys
sys.path.insert(0, 'src')


def test_constants():
    """Test constants module."""
    print("Testing constants...")

    from open_push.core.constants import (
        PUSH1_SYSEX_HEADER,
        PAD_NOTE_MIN,
        PAD_NOTE_MAX,
        BUTTON_CC,
        COLORS,
        pad_to_note,
        note_to_pad,
        color_value,
        note_name,
        name_to_note,
    )

    # SysEx header
    assert PUSH1_SYSEX_HEADER == [0x47, 0x7F, 0x15]

    # Pad range
    assert PAD_NOTE_MIN == 36
    assert PAD_NOTE_MAX == 99

    # Grid conversion
    assert pad_to_note(0, 0) == 36  # Bottom-left
    assert pad_to_note(7, 7) == 99  # Top-right
    assert note_to_pad(36) == (0, 0)
    assert note_to_pad(99) == (7, 7)

    # Colors
    assert color_value('off') == 0
    assert color_value('blue') == 45
    assert color_value(127) == 127

    # Note names
    assert note_name(60) == 'C4'  # Middle C
    assert note_name(36) == 'C2'
    assert name_to_note('C4') == 60
    assert name_to_note('A4') == 69

    print("  Constants OK")


def test_scales():
    """Test scales module."""
    print("Testing scales...")

    from open_push.music.scales import (
        SCALES,
        SCALE_NAMES,
        get_scale,
        is_in_scale,
        is_root_note,
        get_scale_degree,
    )

    # Scale definitions
    assert 'major' in SCALES
    assert 'minor' in SCALES
    assert len(SCALES['major']) == 7
    assert len(SCALES['chromatic']) == 12

    # Get scale
    assert get_scale('major') == [0, 2, 4, 5, 7, 9, 11]
    assert get_scale('MAJOR') == [0, 2, 4, 5, 7, 9, 11]  # Case insensitive

    # In-scale checks (C major)
    c_major = SCALES['major']
    assert is_in_scale(60, 0, c_major)  # C4 in C major
    assert is_in_scale(62, 0, c_major)  # D4 in C major
    assert not is_in_scale(61, 0, c_major)  # C#4 not in C major

    # Root note check
    assert is_root_note(60, 0)  # C4 is root in C
    assert is_root_note(48, 0)  # C3 is root in C
    assert not is_root_note(62, 0)  # D4 is not root in C

    # Scale degree
    assert get_scale_degree(60, 0, c_major) == 1  # C is 1st degree
    assert get_scale_degree(64, 0, c_major) == 3  # E is 3rd degree
    assert get_scale_degree(67, 0, c_major) == 5  # G is 5th degree
    assert get_scale_degree(61, 0, c_major) == 0  # C# not in scale

    print("  Scales OK")


def test_layout():
    """Test isomorphic layout."""
    print("Testing layout...")

    from open_push.music.layout import IsomorphicLayout, LAYOUT_PRESETS

    # Create layout
    layout = IsomorphicLayout(root_note=36)  # C2

    # Check fourths layout (default)
    assert layout.row_interval == 5
    assert layout.col_interval == 1

    # Bottom-left pad (0,0) should be C2 = 36
    assert layout.get_note_at(0, 0) == 36

    # Moving right adds 1 semitone
    assert layout.get_note_at(0, 1) == 37

    # Moving up adds 5 semitones (fourth)
    assert layout.get_note_at(1, 0) == 41

    # By pad note
    assert layout.get_midi_note(36) == 36  # Bottom-left
    assert layout.get_midi_note(37) == 37  # One right
    assert layout.get_midi_note(44) == 41  # One up

    # Octave shift
    assert layout.get_octave() == 2  # C2 is octave 2 (MIDI note 36)
    layout.shift_octave(+1)
    assert layout.get_octave() == 3
    assert layout.get_note_at(0, 0) == 48  # C3
    layout.shift_octave(-1)
    assert layout.get_octave() == 2

    # Layout presets
    assert 'fourths_up' in LAYOUT_PRESETS
    assert 'thirds_up' in LAYOUT_PRESETS

    # In-key mode
    layout.set_in_key_mode(True, root=0, scale='major')
    assert layout.in_key_mode == True
    # In-key mode should give scale notes
    note = layout.get_note_at(0, 0)
    assert note % 12 == 0  # Should be a C (root)

    print("  Layout OK")


def test_display_buffer():
    """Test display buffer without hardware."""
    print("Testing display buffer...")

    # Test the buffer logic without actually sending to hardware
    from open_push.core.constants import LCD_CHARS_PER_LINE, LCD_CHARS_PER_SEGMENT

    assert LCD_CHARS_PER_LINE == 68
    assert LCD_CHARS_PER_SEGMENT == 17

    # Simulate buffer
    buffer = [' '] * LCD_CHARS_PER_LINE
    text = "Test".center(LCD_CHARS_PER_SEGMENT)
    start = 0 * LCD_CHARS_PER_SEGMENT  # Segment 0

    for i, char in enumerate(text):
        buffer[start + i] = char

    result = ''.join(buffer[0:17])
    assert "Test" in result
    assert len(result) == 17

    print("  Display buffer OK")


def test_button_mappings():
    """Test button CC mappings."""
    print("Testing button mappings...")

    from open_push.core.constants import BUTTON_CC, CC_TO_BUTTON

    # Forward lookup
    assert BUTTON_CC['play'] == 85
    assert BUTTON_CC['record'] == 86
    assert BUTTON_CC['octave_up'] == 55
    assert BUTTON_CC['octave_down'] == 54

    # Reverse lookup
    assert CC_TO_BUTTON[85] == 'play'
    assert CC_TO_BUTTON[86] == 'record'

    # Upper and lower row buttons
    assert BUTTON_CC['upper_1'] == 102
    assert BUTTON_CC['upper_8'] == 109
    assert BUTTON_CC['lower_1'] == 20
    assert BUTTON_CC['lower_8'] == 27

    print("  Button mappings OK")


def run_all_tests():
    """Run all tests."""
    print()
    print("=" * 50)
    print("open-push Core Module Tests")
    print("=" * 50)
    print()

    try:
        test_constants()
        test_scales()
        test_layout()
        test_display_buffer()
        test_button_mappings()

        print()
        print("=" * 50)
        print("All tests passed!")
        print("=" * 50)
        return 0

    except AssertionError as e:
        print(f"\n  FAILED: {e}")
        return 1
    except ImportError as e:
        print(f"\n  IMPORT ERROR: {e}")
        print("  Make sure you're running from the project root:")
        print("    cd /path/to/open-push && python3 tests/test_core.py")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
