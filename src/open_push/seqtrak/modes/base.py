"""
Base mode class for Seqtrak bridge mode system.

All modes inherit from ModeBase and implement the required methods.
"""

from abc import ABC, abstractmethod


class ModeBase(ABC):
    """
    Abstract base class for all operating modes.

    Each mode represents a distinct behavior pattern for the Push controller:
    - SeqtrakControlMode: Full Seqtrak hardware control
    - GenericMIDIMode: Push as MIDI controller for iPad apps
    - SystemSettingsMode: System configuration and settings

    Modes are responsible for:
    - Handling incoming MIDI from Push hardware
    - Updating Push display and LED feedback
    - Managing mode-specific state
    - Cleanup when exiting the mode
    """

    def __init__(self, name):
        """
        Initialize mode.

        Args:
            name: Human-readable mode name (e.g., "Seqtrak Control", "MIDI Mode")
        """
        self.name = name
        self.is_active = False

    @abstractmethod
    def enter(self):
        """
        Called when entering this mode.

        Responsibilities:
        - Initialize mode-specific state
        - Update Push display to show mode
        - Set up pad/button LED feedback
        - Load saved preferences (if any)
        """
        self.is_active = True

    @abstractmethod
    def exit(self):
        """
        Called when leaving this mode.

        Responsibilities:
        - Cleanup mode-specific state
        - Send all-notes-off to prevent stuck notes
        - Save mode preferences (if any)
        - Clear Push display/LEDs (optional, next mode will overwrite)
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
        - Send MIDI output (to Seqtrak, iPad, or other targets)
        - Update Push display/LEDs as needed
        """
        pass

    def update_display(self):
        """
        Update Push LCD display (optional to override).

        Called periodically to refresh the display with current state.
        Useful for showing time-based info (tempo, clock, stats).
        """
        pass

    def send_all_notes_off(self):
        """
        Helper: Send all notes off to prevent stuck notes.

        Should be called when exiting a mode that sends MIDI notes.
        """
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__}: {self.name}>"
