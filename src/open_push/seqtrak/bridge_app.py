"""
Main bridge application with mode switching support.

This module provides the BridgeApp class which manages:
- Multiple operating modes (Seqtrak Control, MIDI, System Settings)
- Mode switching triggered by button combinations
- Mode preference saving/loading
- Delegation of MIDI handling to active mode
"""

from .app import SeqtrakBridge
from .modes import SeqtrakControlMode, SystemSettingsMode
from .mode_preferences import ModePreferences


class BridgeApp:
    """
    Main bridge application with mode switching.

    Manages multiple operating modes and delegates MIDI handling
    to the currently active mode.

    Modes:
    - seqtrak: Full Seqtrak hardware control (SeqtrakControlMode)
    - system: System settings configuration (SystemSettingsMode)
    - midi: Generic MIDI controller (future: GenericMIDIMode)
    """

    def __init__(self):
        """Initialize bridge application and modes."""
        print("Initializing OpenPush Seqtrak Bridge with mode switching...")

        # Initialize the existing Seqtrak bridge
        # This creates the bridge instance which will be wrapped by SeqtrakControlMode
        self.seqtrak_bridge = SeqtrakBridge()

        # Initialize mode preference manager
        self.mode_prefs = ModePreferences()

        # Initialize all modes
        # Note: Modes will access push_out from the bridge when needed (not during init)
        self.modes = {
            'seqtrak': SeqtrakControlMode(self.seqtrak_bridge),
            'system': SystemSettingsMode(self.seqtrak_bridge, self),
            # 'midi': GenericMIDIMode(...),  # TODO: Phase 4
        }

        # Load boot mode preference
        boot_mode = self.mode_prefs.get_boot_mode()
        print(f"Boot mode preference: {boot_mode}")

        # Validate boot mode exists
        if boot_mode not in self.modes:
            print(f"Warning: Invalid boot mode '{boot_mode}', defaulting to 'seqtrak'")
            boot_mode = 'seqtrak'

        self.current_mode_name = boot_mode
        self.active_mode = self.modes[self.current_mode_name]

        # Track shift key state (for mode switching triggers)
        self.shift_held = False

        print(f"Starting in {self.active_mode.name} mode")

    def switch_mode(self, mode_name):
        """
        Switch to a different operating mode.

        Args:
            mode_name: Name of mode to switch to ('seqtrak', 'system', 'midi')

        Returns:
            bool: True if mode switch successful, False if mode doesn't exist
        """
        if mode_name not in self.modes:
            print(f"Warning: Unknown mode '{mode_name}'")
            return False

        if mode_name == self.current_mode_name:
            # Already in this mode
            return True

        print(f"Switching mode: {self.current_mode_name} → {mode_name}")

        # Exit current mode
        self.active_mode.exit()

        # Switch to new mode
        previous_mode = self.current_mode_name
        self.current_mode_name = mode_name
        self.active_mode = self.modes[mode_name]

        # Enter new mode (pass previous mode name for system settings)
        if hasattr(self.active_mode, 'enter'):
            if mode_name == 'system':
                # System settings needs to know where to return
                self.active_mode.enter(from_mode=previous_mode)
            else:
                self.active_mode.enter()

        # Save mode preference
        self.mode_prefs.save(mode_name)

        return True

    def handle_mode_switch_triggers(self, msg):
        """
        Check for mode switching button combinations.

        Triggers:
        - Shift + User (CC 59) → System Settings Mode

        Args:
            msg: mido.Message to check

        Returns:
            bool: True if mode switch was triggered, False otherwise
        """
        if msg.type != 'control_change':
            return False

        # Track Shift key state (CC 49)
        if msg.control == 49:
            self.shift_held = (msg.value == 127)
            return False

        # Shift + User → System Settings
        if msg.control == 59 and msg.value == 127 and self.shift_held:
            if self.current_mode_name != 'system':
                self.switch_mode('system')
                return True

        return False

    def run(self):
        """
        Main event loop.

        Delegates MIDI handling to active mode, but intercepts
        mode switching triggers.
        """
        # Enter initial mode
        self.active_mode.enter()

        # Delegate to seqtrak_bridge's run() method
        # but intercept MIDI for mode switching
        try:
            import time
            print("Bridge running. Press Ctrl+C to quit.")
            print(f"Mode switching: Shift+User → System Settings")

            # Hook into the bridge's MIDI handling
            original_handle = self.seqtrak_bridge.handle_midi

            def handle_with_mode_switching(msg):
                # Check for mode switch triggers first
                if self.handle_mode_switch_triggers(msg):
                    return

                # Delegate to active mode
                self.active_mode.handle_midi(msg)

            # Replace bridge's handle_midi temporarily
            self.seqtrak_bridge.handle_midi = handle_with_mode_switching

            # Run the bridge's event loop
            self.seqtrak_bridge.run()

        except KeyboardInterrupt:
            print("\nShutting down...")
            # Exit current mode
            self.active_mode.exit()
            # Let the bridge clean up
            if hasattr(self.seqtrak_bridge, 'cleanup'):
                self.seqtrak_bridge.cleanup()
