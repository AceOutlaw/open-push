"""
Seqtrak Control Mode - Full hardware control of Yamaha Seqtrak from Push.

This mode provides complete integration with Seqtrak hardware:
- Step sequencer editing (11 tracks: 7 drum, 3 melodic, 1 sampler)
- Pattern/variation launching (6 variations per track)
- Mixer mode (volume, mute, solo)
- Device mode (preset selection)
- Isomorphic keyboard for melodic tracks
- Transport controls
"""

from .base import ModeBase


class SeqtrakControlMode(ModeBase):
    """
    Full Seqtrak hardware control mode.

    This mode wraps the existing SeqtrakBridge functionality from app.py.
    For now, it delegates to the bridge instance. In the future, we can
    refactor the bridge logic directly into this class.
    """

    def __init__(self, bridge):
        """
        Initialize Seqtrak Control Mode.

        Args:
            bridge: SeqtrakBridge instance (from app.py)
        """
        super().__init__("Seqtrak Control")
        self.bridge = bridge

    def enter(self):
        """Enter Seqtrak Control Mode."""
        super().enter()
        # Bridge will update display when MIDI ports are ready
        # (update_display is called in SeqtrakBridge.run() after ports are opened)
        pass

    def exit(self):
        """Exit Seqtrak Control Mode."""
        # Send all notes off to prevent stuck notes
        self.bridge.send_all_notes_off()
        super().exit()

    def handle_midi(self, msg):
        """Delegate MIDI handling to the bridge."""
        self.bridge.handle_midi(msg)

    def update_display(self):
        """Update display (called periodically)."""
        # Bridge handles its own display updates
        pass
