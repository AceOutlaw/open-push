"""
System Settings Mode - Configure Pi bridge from Push interface.

Accessible via Shift+User, this mode provides:
- Mode selection (Seqtrak ↔ MIDI)
- iPad audio routing controls
- Network info (IP address, WiFi status)
- System stats (CPU temp, uptime, disk usage)
- System control (shutdown, reboot, restart service)
"""

from .base import ModeBase
from ..helpers import SubprocessManager
import mido


class SystemSettingsMode(ModeBase):
    """
    System settings and configuration mode.

    Entered via Shift+User button. Provides settings pages:
    1. Mode Select - Switch between Seqtrak/MIDI modes
    2. iPad Audio - Configure audio routing
    3. Network Info - IP, WiFi, hostname
    4. System Stats - Temp, uptime, disk, memory
    5. System Control - Shutdown, reboot, restart

    Navigation:
    - Encoders 1-8: Select setting category/page
    - Turn encoder: Adjust value or scroll options
    - Press encoder: Toggle/activate selected option
    - User button: Exit back to previous mode
    """

    def __init__(self, bridge, app):
        """
        Initialize System Settings Mode.

        Args:
            bridge: SeqtrakBridge instance (for accessing push_out)
            app: Main BridgeApp instance (for mode switching)
        """
        super().__init__("System Settings")
        self.bridge = bridge
        self.app = app
        self.current_page = 0  # Which settings page is active (0 = iPad Audio)
        self.previous_mode = None  # Mode to return to on exit
        self.subprocess_mgr = SubprocessManager()  # Manage alsaloop processes
        self.selected_direction = 'ipad_to_seqtrak'  # Which direction is selected

    def enter(self, from_mode=None):
        """
        Enter System Settings Mode.

        Args:
            from_mode: Name of mode we came from (to return to on exit)
        """
        super().enter()
        self.previous_mode = from_mode or 'seqtrak'
        self.show_settings_display()

    def exit(self):
        """Exit System Settings Mode."""
        # Note: alsaloop processes are kept running when exiting settings
        # User must manually stop them if needed
        super().exit()
        # Return to previous mode
        if self.previous_mode:
            self.app.switch_mode(self.previous_mode)

    def handle_midi(self, msg):
        """
        Handle MIDI input for system settings navigation.

        Args:
            msg: mido.Message from Push hardware
        """
        if msg.type == 'control_change':
            # User button (CC 59) - Exit back to previous mode
            if msg.control == 59 and msg.value == 127:
                self.exit()
                return

            # iPad Audio page (current_page == 0)
            if self.current_page == 0:
                # Encoder 1 turn (CC 71) - Select direction
                if msg.control == 71:
                    if msg.value < 64:  # Clockwise
                        self.selected_direction = 'seqtrak_to_ipad'
                    else:  # Counter-clockwise
                        self.selected_direction = 'ipad_to_seqtrak'
                    self.show_settings_display()
                    return

                # Encoder 1 press (CC 20) - Toggle selected direction
                if msg.control == 20 and msg.value == 127:
                    if self.subprocess_mgr.is_running(self.selected_direction):
                        success, msg_text = self.subprocess_mgr.stop(self.selected_direction)
                    else:
                        success, msg_text = self.subprocess_mgr.start_alsaloop(self.selected_direction)
                    self.show_settings_display()
                    return

            # Encoder buttons (CC 20-27) - Select page (future pages)
            if 20 <= msg.control <= 27 and msg.value == 127:
                self.current_page = msg.control - 20
                self.show_settings_display()
                return

    def show_settings_display(self):
        """Display system settings menu on Push LCD."""
        if self.current_page == 0:
            self._display_ipad_audio()
        else:
            # Future pages: Mode Select, Network, System Stats, System Control
            # Placeholder for now
            line1 = "System Settings"
            line2 = f"Page {self.current_page}"
            line3 = "Not implemented yet"
            line4 = "Press User to exit"

            self._send_display(line1, 1)
            self._send_display(line2, 2)
            self._send_display(line3, 3)
            self._send_display(line4, 4)

    def _display_ipad_audio(self):
        """Display iPad audio routing controls."""
        # Line 1: Page title and headers
        line1 = "iPad Audio".ljust(17)
        line1 += "iPad→Seqtrak".center(17)
        line1 += "Seqtrak→iPad".center(17)
        line1 += "Status".center(17)

        # Line 2: Enabled/disabled indicators with selection marker
        i2s_running = self.subprocess_mgr.is_running('ipad_to_seqtrak')
        s2i_running = self.subprocess_mgr.is_running('seqtrak_to_ipad')

        i2s_indicator = "●" if i2s_running else "○"
        s2i_indicator = "●" if s2i_running else "○"

        # Add selection marker (>) to currently selected direction
        i2s_text = f"{i2s_indicator} Enabled" if i2s_running else f"{i2s_indicator} Disabled"
        s2i_text = f"{s2i_indicator} Enabled" if s2i_running else f"{s2i_indicator} Disabled"

        if self.selected_direction == 'ipad_to_seqtrak':
            i2s_text = ">" + i2s_text
        if self.selected_direction == 'seqtrak_to_ipad':
            s2i_text = ">" + s2i_text

        line2 = "".ljust(17)
        line2 += i2s_text.center(17)
        line2 += s2i_text.center(17)
        line2 += "".ljust(17)

        # Line 3: Status details
        i2s_status = self.subprocess_mgr.get_status('ipad_to_seqtrak')
        s2i_status = self.subprocess_mgr.get_status('seqtrak_to_ipad')

        line3 = "".ljust(17)
        line3 += i2s_status.center(17)
        line3 += s2i_status.center(17)
        line3 += "".ljust(17)

        # Line 4: Help text
        line4 = "Turn: Select    Press: Toggle    User: Exit"

        self._send_display(line1, 1)
        self._send_display(line2, 2)
        self._send_display(line3, 3)
        self._send_display(line4, 4)

    def _send_display(self, text, line):
        """
        Send text to Push LCD line.

        Args:
            text: Text string (will be padded/truncated to 68 chars)
            line: Line number (1-4)
        """
        # SysEx format: F0 47 7F 15 [line_cmd] [text bytes] F7
        SYSEX_HEADER = [0x47, 0x7F, 0x15]
        LCD_LINES = {1: 0x18, 2: 0x19, 3: 0x1A, 4: 0x1B}

        # Pad or truncate to 68 chars
        text = text.ljust(68)[:68]

        # Build SysEx message
        sysex_data = SYSEX_HEADER + [LCD_LINES[line]] + [ord(c) for c in text]
        msg = mido.Message('sysex', data=sysex_data)
        self.bridge.push_out.send(msg)
