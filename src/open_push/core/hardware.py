"""
Push 1 Hardware Interface
=========================

Low-level hardware control for Ableton Push 1.
Handles port detection, SysEx communication, and LED control.
"""

import mido
import time
from typing import Optional, Tuple, Callable

from .constants import (
    PUSH1_SYSEX_HEADER,
    PUSH1_USER_MODE,
    PUSH1_LIVE_MODE,
    PAD_NOTE_MIN,
    PAD_NOTE_MAX,
    BUTTON_CC,
    color_value,
)


class Push1Hardware:
    """
    Low-level interface to Push 1 hardware.

    Handles:
    - Port detection and connection
    - User/Live mode switching
    - Pad LED control
    - Button LED control
    - Input message handling

    Usage:
        push = Push1Hardware()
        if push.connect():
            push.set_user_mode()
            push.set_pad_color(36, 'blue')
            # ... handle input ...
            push.disconnect()
    """

    def __init__(self):
        self.input_port_name: Optional[str] = None
        self.output_port_name: Optional[str] = None
        self._input_port = None
        self._output_port = None
        self._connected = False

    @property
    def connected(self) -> bool:
        """Check if connected to Push hardware."""
        return self._connected and self._output_port is not None

    def find_ports(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Find Push MIDI ports.

        Returns:
            Tuple of (input_port_name, output_port_name)
        """
        input_name = None
        output_name = None

        # Prefer User ports (allows Push to work outside Live)
        for name in mido.get_input_names():
            if 'Ableton Push' in name and 'User' in name:
                input_name = name
                break
            elif 'Ableton Push' in name and input_name is None:
                input_name = name

        for name in mido.get_output_names():
            if 'Ableton Push' in name and 'User' in name:
                output_name = name
                break
            elif 'Ableton Push' in name and output_name is None:
                output_name = name

        self.input_port_name = input_name
        self.output_port_name = output_name
        return input_name, output_name

    def connect(self) -> bool:
        """
        Connect to Push hardware.

        Returns:
            True if connected successfully
        """
        if self._connected:
            return True

        # Find ports if not already found
        if not self.output_port_name:
            self.find_ports()

        if not self.output_port_name:
            return False

        try:
            self._output_port = mido.open_output(self.output_port_name)
            if self.input_port_name:
                self._input_port = mido.open_input(self.input_port_name)
            self._connected = True
            return True
        except Exception as e:
            print(f"Error connecting to Push: {e}")
            return False

    def disconnect(self):
        """Disconnect from Push hardware."""
        if self._input_port:
            self._input_port.close()
            self._input_port = None
        if self._output_port:
            self._output_port.close()
            self._output_port = None
        self._connected = False

    # =========================================================================
    # SYSEX COMMUNICATION
    # =========================================================================

    def send_sysex(self, data: list):
        """Send a SysEx message to Push."""
        if not self._output_port:
            return
        msg = mido.Message('sysex', data=PUSH1_SYSEX_HEADER + data)
        self._output_port.send(msg)

    def set_user_mode(self):
        """Switch Push to User Mode (away from Live control)."""
        self.send_sysex(PUSH1_USER_MODE)
        time.sleep(0.05)  # Brief delay for mode switch

    def set_live_mode(self):
        """Switch Push back to Live Mode."""
        self.send_sysex(PUSH1_LIVE_MODE)
        time.sleep(0.05)

    # =========================================================================
    # PAD LED CONTROL
    # =========================================================================

    def set_pad_color(self, note: int, color):
        """
        Set a pad's LED color.

        Args:
            note: MIDI note number (36-99)
            color: Color name (str) or velocity value (int)
        """
        if not self._output_port:
            return
        if not (PAD_NOTE_MIN <= note <= PAD_NOTE_MAX):
            return

        velocity = color_value(color)
        msg = mido.Message('note_on', note=note, velocity=velocity)
        self._output_port.send(msg)

    def set_pad_color_xy(self, row: int, col: int, color):
        """
        Set a pad's LED color by grid position.

        Args:
            row: Row (0-7, bottom to top)
            col: Column (0-7, left to right)
            color: Color name (str) or velocity value (int)
        """
        note = PAD_NOTE_MIN + (row * 8) + col
        self.set_pad_color(note, color)

    def clear_all_pads(self):
        """Turn off all pad LEDs."""
        for note in range(PAD_NOTE_MIN, PAD_NOTE_MAX + 1):
            self.set_pad_color(note, 'off')

    def set_all_pads(self, color):
        """Set all pads to a single color."""
        for note in range(PAD_NOTE_MIN, PAD_NOTE_MAX + 1):
            self.set_pad_color(note, color)

    # =========================================================================
    # BUTTON LED CONTROL
    # =========================================================================

    def set_button_color(self, button: str, color):
        """
        Set a button's LED color by name.

        Args:
            button: Button name from BUTTON_CC
            color: Color name (str) or value (int)
        """
        cc = BUTTON_CC.get(button)
        if cc is not None:
            self.set_button_color_cc(cc, color)

    def set_button_color_cc(self, cc: int, color):
        """
        Set a button's LED color by CC number.

        Args:
            cc: Control Change number
            color: Color name (str) or value (int)
        """
        if not self._output_port:
            return
        value = color_value(color)
        msg = mido.Message('control_change', control=cc, value=value)
        self._output_port.send(msg)

    def clear_button(self, button: str):
        """Turn off a button's LED."""
        self.set_button_color(button, 'off')

    def clear_all_buttons(self):
        """Turn off all button LEDs."""
        for cc in BUTTON_CC.values():
            self.set_button_color_cc(cc, 'off')

    # =========================================================================
    # INPUT HANDLING
    # =========================================================================

    def read_message(self, timeout: float = None) -> Optional[mido.Message]:
        """
        Read a single message from Push input.

        Args:
            timeout: Maximum time to wait (seconds), None for non-blocking

        Returns:
            mido.Message or None
        """
        if not self._input_port:
            return None

        if timeout is None:
            # Non-blocking
            return self._input_port.poll()
        elif timeout == 0:
            # Blocking forever
            return self._input_port.receive()
        else:
            # Blocking with timeout
            return self._input_port.receive(block=True)

    def iter_messages(self):
        """
        Iterate over incoming messages (blocking).

        Yields:
            mido.Message objects
        """
        if not self._input_port:
            return
        for msg in self._input_port:
            yield msg

    # =========================================================================
    # CONTEXT MANAGER
    # =========================================================================

    def __enter__(self):
        if not self._connected:
            self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
