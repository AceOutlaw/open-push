"""
Base mode class for MIDI bridge mode system.

All modes inherit from ModeBase and implement the required methods.
"""

from abc import ABC, abstractmethod


class ModeBase(ABC):
    """
    Abstract base class for all operating modes.

    Each mode represents a distinct behavior pattern for the Push controller:
    - KeyboardMode: Isomorphic keyboard with scales
    - DrumMode: Chromatic drum pad layout
    - EncoderMode: CC output with 4 banks
    - ScaleSelectMode: Scale and root selection

    Modes are responsible for:
    - Handling incoming MIDI from Push hardware
    - Updating Push display and LED feedback
    - Sending MIDI output (notes, CCs)
    - Managing mode-specific state
    """

    def __init__(self, name: str):
        """
        Initialize mode.

        Args:
            name: Human-readable mode name (e.g., "Keyboard", "Drum")
        """
        self.name = name
        self.is_active = False
        self.bridge = None  # Set by MIDIBridge when registering

    def set_bridge(self, bridge):
        """Set reference to parent bridge."""
        self.bridge = bridge

    @abstractmethod
    def enter(self):
        """
        Called when entering this mode.

        Responsibilities:
        - Initialize mode-specific state
        - Update Push display to show mode
        - Set up pad/button LED feedback
        """
        self.is_active = True

    @abstractmethod
    def exit(self):
        """
        Called when leaving this mode.

        Responsibilities:
        - Cleanup mode-specific state
        - Send all-notes-off to prevent stuck notes
        """
        self.is_active = False

    @abstractmethod
    def handle_midi(self, msg):
        """
        Process incoming MIDI message from Push hardware.

        Args:
            msg: mido.Message object (note_on, note_off, control_change, etc.)

        This is the main event handler for the mode. It should:
        - Parse the message type and value
        - Update internal state
        - Send MIDI output via self.bridge.output
        - Update Push display/LEDs as needed
        """
        pass

    def update_display(self):
        """
        Update Push LCD display (optional to override).

        Called periodically to refresh the display with current state.
        """
        pass

    def send_all_notes_off(self):
        """
        Helper: Send all notes off to prevent stuck notes.

        Should be called when exiting a mode that sends MIDI notes.
        """
        if self.bridge and self.bridge.output:
            for channel in range(16):
                # All Notes Off (CC 123)
                self.bridge.output.send_cc(123, 0, channel)

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"
