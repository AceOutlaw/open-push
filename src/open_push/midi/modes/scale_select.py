"""
Scale Selection Mode
====================

Mode for selecting musical scale and root note.
Uses the 16 LCD buttons for root note selection and encoder for scale scrolling.

Layout (Push 1):
  Upper row (CC 20-27):
    [ScaleUp] [C] [C#] [D] [D#] [E] [F] [InKey]

  Lower row (CC 102-109):
    [ScaleDn] [F#] [G] [G#] [A] [A#] [B] [Chromat]
"""

from typing import Optional

from open_push.midi.modes.base import ModeBase
from open_push.music.scales import SCALES, SCALE_NAMES, get_scale_display_name
from open_push.midi.push_hardware import BUTTON_CC, ENCODER_CC


# Root note names
ROOT_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Button layout for root selection
# Upper row: Scale Up, C, C#, D, D#, E, F, In-Key
# Lower row: Scale Down, F#, G, G#, A, A#, B, Chromatic
UPPER_BUTTONS = [20, 21, 22, 23, 24, 25, 26, 27]  # CC numbers
LOWER_BUTTONS = [102, 103, 104, 105, 106, 107, 108, 109]

# Map CC to root note (None = special function)
CC_TO_ROOT = {
    21: 0,   # C
    22: 1,   # C#
    23: 2,   # D
    24: 3,   # D#
    25: 4,   # E
    26: 5,   # F
    103: 6,  # F#
    104: 7,  # G
    105: 8,  # G#
    106: 9,  # A
    107: 10, # A#
    108: 11, # B
}

# Special function buttons
SCALE_UP_CC = 20
SCALE_DOWN_CC = 102
IN_KEY_CC = 27
CHROMATIC_CC = 109


class ScaleSelectMode(ModeBase):
    """
    Scale selection mode.

    Allows selecting root note and scale for the keyboard mode.
    Uses Push's 16 LCD buttons and encoders.
    """

    def __init__(self):
        super().__init__("Scale Select")

        # Reference to keyboard mode (set by bridge)
        self.keyboard_mode = None

        # Local state (synced from keyboard mode on enter)
        self.scale_index = 1
        self.root_note = 0
        self.in_key_mode = True
        self.scale_scroll_offset = 0  # For encoder scrolling display

    # =========================================================================
    # MODE LIFECYCLE
    # =========================================================================

    def enter(self):
        """Called when entering scale select mode."""
        super().enter()

        if not self.bridge:
            return

        # Get keyboard mode reference
        self.keyboard_mode = self.bridge.modes.get('keyboard')

        # Sync state from keyboard mode
        if self.keyboard_mode:
            self.scale_index = self.keyboard_mode.scale_index
            self.root_note = self.keyboard_mode.root_note
            self.in_key_mode = self.keyboard_mode.in_key_mode

        # Light up the Scale button
        self.bridge.push.set_button_color('scale', 'green')
        self.bridge.push.set_button_color('note', 'dim_white')
        self.bridge.push.set_button_color('session', 'dim_white')
        self.bridge.push.set_button_color('device', 'dim_white')

        # Update display and button LEDs
        self.update_display()
        self._update_button_leds()
        self._update_pad_preview()

    def exit(self):
        """Called when leaving scale select mode."""
        super().exit()

        # Apply settings to keyboard mode
        if self.keyboard_mode:
            self.keyboard_mode.set_scale(self.scale_index)
            self.keyboard_mode.set_root(self.root_note)
            self.keyboard_mode.set_in_key_mode(self.in_key_mode)

        # Dim the Scale button
        if self.bridge:
            self.bridge.push.set_button_color('scale', 'dim_white')

    # =========================================================================
    # MIDI INPUT HANDLING
    # =========================================================================

    def handle_midi(self, msg):
        """Process incoming MIDI from Push."""
        if msg.type == 'control_change':
            self._handle_cc(msg.control, msg.value)
        elif msg.type == 'note_on' and msg.velocity > 0:
            # Pad preview - play notes with current scale
            self._handle_pad_preview(msg.note, msg.velocity)
        elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
            self._handle_pad_release(msg.note)

    def _handle_cc(self, cc: int, value: int):
        """Handle control change messages."""
        if value == 0:  # Only handle button press, not release
            return

        # Check for root note selection
        if cc in CC_TO_ROOT:
            self.root_note = CC_TO_ROOT[cc]
            self._update_button_leds()
            self._update_pad_preview()
            self.update_display()
            return

        # Scale up/down
        if cc == SCALE_UP_CC:
            self.scale_index = (self.scale_index + 1) % len(SCALE_NAMES)
            self.update_display()
            self._update_pad_preview()
            return

        if cc == SCALE_DOWN_CC:
            self.scale_index = (self.scale_index - 1) % len(SCALE_NAMES)
            self.update_display()
            self._update_pad_preview()
            return

        # In-key / Chromatic toggle
        if cc == IN_KEY_CC:
            self.in_key_mode = True
            self._update_button_leds()
            self.update_display()
            self._update_pad_preview()
            return

        if cc == CHROMATIC_CC:
            self.in_key_mode = False
            self._update_button_leds()
            self.update_display()
            self._update_pad_preview()
            return

        # Scale button to exit
        if cc == BUTTON_CC['scale']:
            self.bridge.return_to_previous_mode()
            return

        # Encoder 1 for scale scrolling
        if cc == ENCODER_CC['encoder_1']:
            delta = self.bridge.push.decode_relative_encoder(value)
            self.scale_index = (self.scale_index + delta) % len(SCALE_NAMES)
            self.update_display()
            self._update_pad_preview()
            return

    def _handle_pad_preview(self, pad_note: int, velocity: int):
        """Play a preview note with the current scale settings."""
        if not self.bridge or not self.keyboard_mode:
            return

        # Temporarily apply our settings to the keyboard mode for preview
        old_scale = self.keyboard_mode.scale_index
        old_root = self.keyboard_mode.root_note
        old_in_key = self.keyboard_mode.in_key_mode

        self.keyboard_mode.set_scale(self.scale_index)
        self.keyboard_mode.set_root(self.root_note)
        self.keyboard_mode.set_in_key_mode(self.in_key_mode)

        # Play the note
        self.keyboard_mode._handle_pad_press(pad_note, velocity)

        # Restore (note: we don't restore until exit, so preview uses new settings)

    def _handle_pad_release(self, pad_note: int):
        """Release a preview note."""
        if self.keyboard_mode:
            self.keyboard_mode._handle_pad_release(pad_note)

    # =========================================================================
    # DISPLAY
    # =========================================================================

    def update_display(self):
        """Update LCD display."""
        if not self.bridge:
            return

        push = self.bridge.push

        # Line 1: Title
        push.set_lcd_line(1, "  Scale Selection".center(68))

        # Line 2: Current scale and root
        scale_name = SCALE_NAMES[self.scale_index]
        display_name = get_scale_display_name(scale_name)
        root_name = ROOT_NAMES[self.root_note]
        mode_str = "In-Key" if self.in_key_mode else "Chromatic"

        push.set_lcd_line(2, f"  {root_name} {display_name} ({mode_str})".center(68))

        # Line 3: Instructions
        push.set_lcd_segments(3, ["<Scale", "Root Notes", "Root Notes", "Scale>"], 'center')

        # Line 4: Button labels
        push.set_lcd_segments(4, ["Up/Dn", "C-F", "F#-B", "Key/Chr"], 'center')

    def _update_button_leds(self):
        """Update the 16 LCD button LEDs."""
        if not self.bridge:
            return

        push = self.bridge.push

        # Scale up/down buttons
        push.set_button_color_cc(SCALE_UP_CC, 'yellow')
        push.set_button_color_cc(SCALE_DOWN_CC, 'yellow')

        # Root note buttons - highlight selected root
        for cc, root in CC_TO_ROOT.items():
            if root == self.root_note:
                push.set_button_color_cc(cc, 'cyan')  # Selected
            else:
                push.set_button_color_cc(cc, 'dim_white')  # Available

        # In-key / Chromatic buttons
        if self.in_key_mode:
            push.set_button_color_cc(IN_KEY_CC, 'green')
            push.set_button_color_cc(CHROMATIC_CC, 'dim_white')
        else:
            push.set_button_color_cc(IN_KEY_CC, 'dim_white')
            push.set_button_color_cc(CHROMATIC_CC, 'green')

    def _update_pad_preview(self):
        """Update pad colors to show scale preview."""
        if not self.keyboard_mode:
            return

        # Temporarily apply our settings
        self.keyboard_mode.scale_index = self.scale_index
        self.keyboard_mode.root_note = self.root_note
        self.keyboard_mode.in_key_mode = self.in_key_mode
        self.keyboard_mode._apply_scale()
        self.keyboard_mode._update_grid()

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
        return f"<ScaleSelectMode: {ROOT_NAMES[self.root_note]} {SCALE_NAMES[self.scale_index]}>"
