"""
Encoder Mode
============

CC encoder mode with 4 banks of 8 encoders each (32 total mappable CCs).

Features:
- 4 banks × 8 encoders = 32 mappable CC outputs
- Bank switching via Page Left/Right buttons
- Relative to absolute value tracking
- LCD display shows encoder labels and values
- Configurable CC numbers and channels per encoder
"""

from typing import Dict, Optional, List

from open_push.midi.modes.base import ModeBase
from open_push.midi.push_hardware import (
    BUTTON_CC, ENCODER_CC,
    PAD_NOTE_MIN, PAD_NOTE_MAX,
)


class EncoderMode(ModeBase):
    """
    CC encoder mode with multiple banks.

    Each of the 8 main encoders outputs a configurable CC message.
    4 banks allow 32 different mappings total.
    """

    def __init__(self):
        super().__init__("Encoder")

        # Current bank (0-3)
        self.current_bank = 0

        # Encoder values per bank [bank][encoder] = value (0-127)
        self.values: List[List[int]] = [[64] * 8 for _ in range(4)]

    # =========================================================================
    # MODE LIFECYCLE
    # =========================================================================

    def enter(self):
        """Called when entering encoder mode."""
        super().enter()

        if not self.bridge:
            return

        # Load current bank's values from bridge state if available
        if hasattr(self.bridge, 'encoder_values'):
            self.values = self.bridge.encoder_values

        # Light up the Device button (used for encoder mode)
        self.bridge.push.set_button_color('device', 'green')
        self.bridge.push.set_button_color('note', 'dim_white')
        self.bridge.push.set_button_color('session', 'dim_white')
        self.bridge.push.set_button_color('scale', 'dim_white')

        # Update bank indicators
        self._update_bank_buttons()

        # Update display and pads
        self.update_display()
        self._update_pads()

    def exit(self):
        """Called when leaving encoder mode."""
        super().exit()

        # Save values to bridge
        if self.bridge and hasattr(self.bridge, 'encoder_values'):
            self.bridge.encoder_values = self.values

        # Dim the Device button
        if self.bridge:
            self.bridge.push.set_button_color('device', 'dim_white')

    # =========================================================================
    # MIDI INPUT HANDLING
    # =========================================================================

    def handle_midi(self, msg):
        """Process incoming MIDI from Push."""
        if msg.type == 'control_change':
            self._handle_cc(msg.control, msg.value)
        elif msg.type == 'note_on' and msg.velocity > 0:
            # Pads could be used for quick bank selection
            self._handle_pad_press(msg.note)

    def _handle_cc(self, cc: int, value: int):
        """Handle control change messages."""
        if not self.bridge:
            return

        # Check for encoder rotation (encoders 1-8)
        encoder_ccs = [
            ENCODER_CC['encoder_1'],
            ENCODER_CC['encoder_2'],
            ENCODER_CC['encoder_3'],
            ENCODER_CC['encoder_4'],
            ENCODER_CC['encoder_5'],
            ENCODER_CC['encoder_6'],
            ENCODER_CC['encoder_7'],
            ENCODER_CC['encoder_8'],
        ]

        if cc in encoder_ccs:
            encoder_index = encoder_ccs.index(cc)
            self._handle_encoder(encoder_index, value)
            return

        # Bank switching via page left/right
        if cc == BUTTON_CC['page_left'] and value > 0:
            self._prev_bank()
            return

        if cc == BUTTON_CC['page_right'] and value > 0:
            self._next_bank()
            return

    def _handle_encoder(self, encoder_index: int, raw_value: int):
        """Handle encoder rotation."""
        if not self.bridge:
            return

        # Decode relative value
        delta = self.bridge.push.decode_relative_encoder(raw_value)

        # Update stored value
        current = self.values[self.current_bank][encoder_index]
        new_value = max(0, min(127, current + delta))
        self.values[self.current_bank][encoder_index] = new_value

        # Get encoder config
        bank_config = self.bridge.config.get_encoder_bank(self.current_bank)
        encoders = bank_config.get('encoders', [])

        if encoder_index < len(encoders):
            enc_config = encoders[encoder_index]
            cc_num = enc_config.get('cc', 70 + encoder_index)
            channel = enc_config.get('channel', 0)

            # Send CC
            self.bridge.output.send_cc(cc_num, new_value, channel)

        # Update display
        self._update_encoder_display(encoder_index, new_value)

    def _handle_pad_press(self, pad_note: int):
        """Handle pad press for bank selection."""
        if not self.bridge:
            return

        # Use bottom row pads 0-3 for bank selection
        pos = pad_note - PAD_NOTE_MIN
        if pos < 4:  # Bottom-left 4 pads
            self.current_bank = pos
            self._update_bank_buttons()
            self._update_pads()
            self.update_display()

    # =========================================================================
    # BANK MANAGEMENT
    # =========================================================================

    def _next_bank(self):
        """Switch to next bank."""
        if not self.bridge:
            return

        num_banks = self.bridge.config.num_encoder_banks
        self.current_bank = (self.current_bank + 1) % num_banks
        self._update_bank_buttons()
        self._update_pads()
        self.update_display()
        print(f"Encoder bank: {self.current_bank + 1}")

    def _prev_bank(self):
        """Switch to previous bank."""
        if not self.bridge:
            return

        num_banks = self.bridge.config.num_encoder_banks
        self.current_bank = (self.current_bank - 1) % num_banks
        self._update_bank_buttons()
        self._update_pads()
        self.update_display()
        print(f"Encoder bank: {self.current_bank + 1}")

    def _update_bank_buttons(self):
        """Update page left/right button LEDs."""
        if not self.bridge:
            return

        push = self.bridge.push
        num_banks = self.bridge.config.num_encoder_banks

        # Show page buttons based on current position
        push.set_button_color('page_left', 'white' if self.current_bank > 0 else 'dim_white')
        push.set_button_color('page_right', 'white' if self.current_bank < num_banks - 1 else 'dim_white')

    # =========================================================================
    # DISPLAY
    # =========================================================================

    def update_display(self):
        """Update LCD display with encoder labels and values."""
        if not self.bridge:
            return

        push = self.bridge.push

        # Get bank config
        bank_config = self.bridge.config.get_encoder_bank(self.current_bank)
        bank_name = bank_config.get('name', f'Bank {self.current_bank + 1}')
        encoders = bank_config.get('encoders', [])

        # Line 1: Mode and bank name
        push.set_lcd_line(1, f"  Encoders: {bank_name}".center(68))

        # Line 2: Encoder labels (8 fields)
        labels = []
        for i in range(8):
            if i < len(encoders):
                label = encoders[i].get('label', f'Enc{i+1}')
            else:
                label = f'Enc{i+1}'
            labels.append(label[:8])  # Truncate to fit

        push.set_lcd_fields(2, labels, 'center')

        # Line 3: Current values
        values = []
        for i in range(8):
            val = self.values[self.current_bank][i]
            values.append(str(val))

        push.set_lcd_fields(3, values, 'center')

        # Line 4: Bank indicator
        num_banks = self.bridge.config.num_encoder_banks
        bank_indicator = f"Bank {self.current_bank + 1}/{num_banks}"
        push.set_lcd_line(4, f"  {bank_indicator}  [< Prev | Next >]".center(68))

    def _update_encoder_display(self, encoder_index: int, value: int):
        """Update just one encoder's value on the LCD."""
        if not self.bridge:
            return

        # Update the specific field on line 3
        self.bridge.push.set_lcd_field(3, encoder_index, str(value), 'center')

    def _update_pads(self):
        """Update pad colors for bank selection."""
        if not self.bridge:
            return

        push = self.bridge.push

        # Clear all pads
        push.clear_all_pads()

        # Light up bottom 4 pads for bank selection
        num_banks = self.bridge.config.num_encoder_banks
        bank_colors = ['red', 'green', 'blue', 'purple']

        for i in range(min(num_banks, 4)):
            pad_note = PAD_NOTE_MIN + i
            if i == self.current_bank:
                push.set_pad_color(pad_note, bank_colors[i])  # Bright for selected
            else:
                push.set_pad_color(pad_note, f'{bank_colors[i]}_dim')  # Dim for available

    # =========================================================================
    # VALUE ACCESS
    # =========================================================================

    def get_value(self, encoder_index: int, bank: int = None) -> int:
        """Get current value of an encoder."""
        if bank is None:
            bank = self.current_bank
        if 0 <= bank < len(self.values) and 0 <= encoder_index < 8:
            return self.values[bank][encoder_index]
        return 64

    def set_value(self, encoder_index: int, value: int, bank: int = None):
        """Set value of an encoder (and send CC)."""
        if bank is None:
            bank = self.current_bank
        if 0 <= bank < len(self.values) and 0 <= encoder_index < 8:
            self.values[bank][encoder_index] = max(0, min(127, value))
            if bank == self.current_bank:
                self._update_encoder_display(encoder_index, value)

    def __repr__(self):
        return f"<EncoderMode: Bank {self.current_bank + 1}>"
