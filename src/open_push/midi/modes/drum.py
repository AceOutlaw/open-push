"""
Drum Mode
=========

Chromatic drum pad mode.
All 64 pads output notes chromatically, ideal for drum machines and samplers.

Features:
- 8x8 chromatic grid (notes 36-99 by default)
- Configurable base note and MIDI channel
- Simple color scheme for visual feedback
- Default channel 10 (standard drum channel)
"""

from typing import Dict, Optional

from open_push.midi.modes.base import ModeBase
from open_push.midi.push_hardware import (
    PAD_NOTE_MIN, PAD_NOTE_MAX,
    is_pad_note, note_to_pad, pad_to_note,
    BUTTON_CC,
)


# Note names for display
NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Drum pad colors by row (from bottom to top)
ROW_COLORS = [
    'red',       # Row 0 (bottom) - Kick/Bass
    'orange',    # Row 1 - Snare
    'yellow',    # Row 2 - Claps/Rimshot
    'green',     # Row 3 - Hi-hats
    'cyan',      # Row 4 - Toms
    'blue',      # Row 5 - Cymbals
    'purple',    # Row 6 - Percussion
    'pink',      # Row 7 (top) - FX/Other
]


class DrumMode(ModeBase):
    """
    Chromatic drum pad mode.

    Each pad outputs a unique MIDI note, ideal for triggering
    drum samples or chromatic percussion.
    """

    def __init__(self):
        super().__init__("Drum")

        # Configuration
        self.base_note = 36  # C2 - standard drum kit base
        self.midi_channel = 9  # Channel 10 (0-indexed)

        # Active notes for proper note-off
        self.active_notes: Dict[int, int] = {}  # pad_note -> midi_note

    # =========================================================================
    # MODE LIFECYCLE
    # =========================================================================

    def enter(self):
        """Called when entering drum mode."""
        super().enter()

        if not self.bridge:
            return

        # Load config
        drum_config = self.bridge.config.drum_config
        self.base_note = drum_config.get('base_note', 36)
        self.midi_channel = drum_config.get('midi_channel', 9)

        # Light up the Session button (used for drum mode)
        self.bridge.push.set_button_color('session', 'green')
        self.bridge.push.set_button_color('note', 'dim_white')
        self.bridge.push.set_button_color('device', 'dim_white')
        self.bridge.push.set_button_color('scale', 'dim_white')

        # Update display and grid
        self.update_display()
        self._update_grid()

    def exit(self):
        """Called when leaving drum mode."""
        super().exit()

        # Release all active notes
        self._release_all_notes()

        # Dim the Session button
        if self.bridge:
            self.bridge.push.set_button_color('session', 'dim_white')

    # =========================================================================
    # MIDI INPUT HANDLING
    # =========================================================================

    def handle_midi(self, msg):
        """Process incoming MIDI from Push."""
        if msg.type == 'note_on' and msg.velocity > 0:
            self._handle_pad_press(msg.note, msg.velocity)
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            self._handle_pad_release(msg.note)
        elif msg.type == 'control_change':
            self._handle_cc(msg.control, msg.value)

    def _handle_pad_press(self, pad_note: int, velocity: int):
        """Handle pad press."""
        if not is_pad_note(pad_note):
            return

        if not self.bridge:
            return

        # Calculate MIDI note (chromatic from base)
        offset = pad_note - PAD_NOTE_MIN
        midi_note = self.base_note + offset

        # Apply accent if enabled
        if self.bridge.accent_mode:
            velocity = self.bridge.accent_velocity

        # Store active note
        self.active_notes[pad_note] = midi_note

        # Send note on
        self.bridge.output.send_note_on(midi_note, velocity, self.midi_channel)

        # Start note repeat if active
        if self.bridge.note_repeat_active:
            self.bridge.start_note_repeat(pad_note, midi_note, self.midi_channel)

        # Light up the pad (bright while pressed)
        row = offset // 8
        self.bridge.push.set_pad_color(pad_note, 'white')

    def _handle_pad_release(self, pad_note: int):
        """Handle pad release."""
        if not is_pad_note(pad_note):
            return

        if not self.bridge:
            return

        # Stop note repeat for this pad
        self.bridge.stop_note_repeat(pad_note)

        # Get the note that was playing
        midi_note = self.active_notes.pop(pad_note, None)
        if midi_note is None:
            return

        # Send note off
        self.bridge.output.send_note_off(midi_note, self.midi_channel)

        # Restore pad color
        self._set_pad_color(pad_note)

    def _handle_cc(self, cc: int, value: int):
        """Handle control change messages."""
        # Mode-specific controls can be handled here
        pass

    def _release_all_notes(self):
        """Release all currently active notes."""
        if not self.bridge:
            self.active_notes.clear()
            return

        for pad_note, midi_note in list(self.active_notes.items()):
            self.bridge.output.send_note_off(midi_note, self.midi_channel)
        self.active_notes.clear()

    # =========================================================================
    # DISPLAY
    # =========================================================================

    def update_display(self):
        """Update LCD display."""
        if not self.bridge:
            return

        push = self.bridge.push

        # Line 1: Mode title
        push.set_lcd_line(1, "  Drum Pads".center(68))

        # Line 2: Channel and base note info
        channel_display = self.midi_channel + 1  # 1-indexed for display
        base_name = self._note_name(self.base_note)
        push.set_lcd_line(2, f"  Channel: {channel_display}  Base: {base_name}".ljust(68))

        # Line 3-4: Note range info
        end_note = self.base_note + 63
        end_name = self._note_name(end_note)
        push.set_lcd_line(3, f"  Notes: {base_name} - {end_name} (64 pads)".ljust(68))
        push.set_lcd_line(4, "")

    def _note_name(self, midi_note: int) -> str:
        """Get note name with octave."""
        name = NOTE_NAMES[midi_note % 12]
        octave = (midi_note // 12) - 1
        return f"{name}{octave}"

    def _update_grid(self):
        """Update pad grid colors."""
        if not self.bridge:
            return

        for pad_note in range(PAD_NOTE_MIN, PAD_NOTE_MAX + 1):
            self._set_pad_color(pad_note)

    def _set_pad_color(self, pad_note: int):
        """Set the color of a single pad based on row."""
        if not self.bridge:
            return

        offset = pad_note - PAD_NOTE_MIN
        row = offset // 8

        # Use row-based color scheme
        color = ROW_COLORS[row] if row < len(ROW_COLORS) else 'white'

        # Use dim version for subtle look
        color_dim = f"{color}_dim" if not color.endswith('_dim') else color

        self.bridge.push.set_pad_color(pad_note, color_dim)

    # =========================================================================
    # CONFIGURATION
    # =========================================================================

    def set_base_note(self, note: int):
        """Set the base MIDI note."""
        self.base_note = max(0, min(64, note))  # Keep range reasonable
        self.update_display()

    def set_channel(self, channel: int):
        """Set the MIDI channel (0-15)."""
        self.midi_channel = max(0, min(15, channel))
        self.update_display()

    def __repr__(self):
        return f"<DrumMode: base={self._note_name(self.base_note)} ch={self.midi_channel + 1}>"
