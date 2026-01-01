"""
Keyboard Mode
=============

Isomorphic keyboard mode with configurable scales and layouts.
Uses the shared IsomorphicLayout class for pad-to-note mapping.

Features:
- Isomorphic layout (same fingering = same chord in any key)
- 40+ scales with in-key mode
- Octave shifting
- Velocity curve or fixed velocity (accent mode)
- Root and scale note highlighting
"""

from typing import Dict, Optional

from open_push.midi.modes.base import ModeBase
from open_push.music.layout import IsomorphicLayout
from open_push.music.scales import SCALES, SCALE_NAMES, get_scale_display_name
from open_push.midi.push_hardware import (
    PAD_NOTE_MIN, PAD_NOTE_MAX,
    is_pad_note, note_to_pad,
    BUTTON_CC, ENCODER_CC,
)


# Root note names
ROOT_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']


class KeyboardMode(ModeBase):
    """
    Isomorphic keyboard mode.

    Pads play MIDI notes using an isomorphic layout.
    Supports chromatic and in-key modes with 40+ scales.
    """

    def __init__(self):
        super().__init__("Keyboard")

        # Layout instance
        self.layout = IsomorphicLayout(root_note=36)  # Start at C2

        # State
        self.scale_index = 1  # Start with minor
        self.root_note = 0  # C
        self.in_key_mode = True

        # Active notes (for proper note-off)
        self.active_notes: Dict[int, int] = {}  # pad_note -> midi_note

        # Apply initial scale
        self._apply_scale()

    def _apply_scale(self):
        """Apply current scale settings to layout."""
        scale_name = SCALE_NAMES[self.scale_index]
        self.layout.set_scale(self.root_note, scale_name)
        self.layout.set_in_key_mode(self.in_key_mode, self.root_note, scale_name)

    # =========================================================================
    # MODE LIFECYCLE
    # =========================================================================

    def enter(self):
        """Called when entering keyboard mode."""
        super().enter()

        if not self.bridge:
            return

        # Light up the Note button
        self.bridge.push.set_button_color('note', 'green')
        self.bridge.push.set_button_color('session', 'dim_white')
        self.bridge.push.set_button_color('device', 'dim_white')
        self.bridge.push.set_button_color('scale', 'dim_white')

        # Update display and grid
        self.update_display()
        self._update_grid()

    def exit(self):
        """Called when leaving keyboard mode."""
        super().exit()

        # Release all active notes
        self._release_all_notes()

        # Dim the Note button
        if self.bridge:
            self.bridge.push.set_button_color('note', 'dim_white')

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

        # Apply octave offset from bridge
        self.layout.root_note = 36 + (self.bridge.octave_offset * 12)

        # Get MIDI note from layout
        midi_note = self.layout.get_midi_note(pad_note)

        # Apply velocity curve or accent
        if self.bridge.accent_mode:
            velocity = self.bridge.accent_velocity
        else:
            velocity = self._apply_velocity_curve(velocity)

        # Store active note for proper note-off
        self.active_notes[pad_note] = midi_note

        # Send note on
        channel = self.bridge.config.midi_channel
        self.bridge.output.send_note_on(midi_note, velocity, channel)

        # Start note repeat if active
        if self.bridge.note_repeat_active:
            self.bridge.start_note_repeat(pad_note, midi_note, channel)

        # Light up the pad (brighter while pressed)
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
        channel = self.bridge.config.midi_channel
        self.bridge.output.send_note_off(midi_note, channel)

        # Restore pad color
        self._set_pad_color(pad_note)

    def _handle_cc(self, cc: int, value: int):
        """Handle control change messages."""
        # Most global controls are handled by the bridge
        # Mode-specific controls can be handled here if needed
        pass

    def _apply_velocity_curve(self, velocity: int) -> int:
        """Apply velocity curve from config."""
        if not self.bridge:
            return velocity

        kb_config = self.bridge.config.keyboard_config
        curve = kb_config.get('velocity_curve', 1.0)
        vel_min = kb_config.get('velocity_min', 1)
        vel_max = kb_config.get('velocity_max', 127)

        # Normalize to 0-1
        normalized = velocity / 127.0

        # Apply curve (1.0 = linear, <1 = soft, >1 = hard)
        if curve != 1.0:
            normalized = pow(normalized, curve)

        # Scale to output range
        output = int(vel_min + normalized * (vel_max - vel_min))
        return max(vel_min, min(vel_max, output))

    def _release_all_notes(self):
        """Release all currently active notes."""
        if not self.bridge:
            self.active_notes.clear()
            return

        channel = self.bridge.config.midi_channel
        for pad_note, midi_note in list(self.active_notes.items()):
            self.bridge.output.send_note_off(midi_note, channel)
        self.active_notes.clear()

    # =========================================================================
    # SCALE CONTROL
    # =========================================================================

    def set_scale(self, scale_index: int):
        """Set the scale by index."""
        self.scale_index = scale_index % len(SCALE_NAMES)
        self._apply_scale()
        self.update_display()
        self._update_grid()

    def set_root(self, root: int):
        """Set the root note (0-11)."""
        self.root_note = root % 12
        self._apply_scale()
        self.update_display()
        self._update_grid()

    def set_in_key_mode(self, enabled: bool):
        """Enable/disable in-key mode."""
        self.in_key_mode = enabled
        self._apply_scale()
        self.update_display()
        self._update_grid()

    def next_scale(self):
        """Go to next scale."""
        self.set_scale(self.scale_index + 1)

    def prev_scale(self):
        """Go to previous scale."""
        self.set_scale(self.scale_index - 1)

    # =========================================================================
    # DISPLAY
    # =========================================================================

    def update_display(self):
        """Update LCD display."""
        if not self.bridge:
            return

        push = self.bridge.push

        # Line 1: Mode and scale info
        scale_name = SCALE_NAMES[self.scale_index]
        display_name = get_scale_display_name(scale_name)
        root_name = ROOT_NAMES[self.root_note]
        mode_str = "In-Key" if self.in_key_mode else "Chromatic"

        push.set_lcd_line(1, f"  Keyboard: {root_name} {display_name} ({mode_str})".center(68))

        # Line 2: Octave info
        octave = (self.layout.root_note // 12) - 1 + self.bridge.octave_offset
        push.set_lcd_line(2, f"  Octave: {octave}".ljust(68))

        # Lines 3-4: Reserved for mode info or leave blank
        push.set_lcd_line(3, "")

    def _update_grid(self):
        """Update pad grid colors."""
        if not self.bridge:
            return

        # Ensure layout reflects current octave
        self.layout.root_note = 36 + (self.bridge.octave_offset * 12)

        for pad_note in range(PAD_NOTE_MIN, PAD_NOTE_MAX + 1):
            self._set_pad_color(pad_note)

    def _set_pad_color(self, pad_note: int):
        """Set the color of a single pad based on scale position."""
        if not self.bridge:
            return

        push = self.bridge.push

        # Get MIDI note for this pad
        midi_note = self.layout.get_midi_note(pad_note)

        # Determine color based on scale position
        if self.layout.is_root(pad_note):
            # Root notes: bright cyan
            color = 'cyan'
        elif self.layout.is_in_scale(pad_note):
            # In-scale notes: dim cyan
            color = 'cyan_dim'
        else:
            # Out-of-scale: very dim or off
            if self.in_key_mode:
                # In-key mode: all pads are in scale
                color = 'cyan_dim'
            else:
                # Chromatic mode: out-of-scale pads are dim
                color = 'dark_gray'

        push.set_pad_color(pad_note, color)

    # =========================================================================
    # MODE INFO
    # =========================================================================

    def get_scale_name(self) -> str:
        """Get current scale display name."""
        return get_scale_display_name(SCALE_NAMES[self.scale_index])

    def get_root_name(self) -> str:
        """Get current root note name."""
        return ROOT_NAMES[self.root_note]

    def __repr__(self):
        return f"<KeyboardMode: {ROOT_NAMES[self.root_note]} {SCALE_NAMES[self.scale_index]}>"
