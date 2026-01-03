"""
Mode preference manager for Seqtrak bridge.

Handles saving and loading of mode preferences to persist across reboots.
"""

import json
from pathlib import Path


class ModePreferences:
    """
    Manage mode preferences stored in config file.

    Config file location: ~/.open-push-mode
    Format: JSON with keys:
        - default_mode: Mode to use if auto_restore_mode is False
        - last_mode: Last active mode before shutdown
        - auto_restore_mode: Whether to restore last mode on boot
    """

    def __init__(self, config_path=None):
        """
        Initialize mode preferences manager.

        Args:
            config_path: Path to config file (default: ~/.open-push-mode)
        """
        if config_path is None:
            config_path = Path.home() / '.open-push-mode'
        self.config_path = Path(config_path)

        # Default preferences
        self.defaults = {
            'default_mode': 'seqtrak',
            'last_mode': 'seqtrak',
            'auto_restore_mode': True
        }

    def load(self):
        """
        Load mode preferences from config file.

        Returns:
            dict: Preferences dict with keys (default_mode, last_mode, auto_restore_mode)
                  Returns defaults if file doesn't exist or is invalid.
        """
        if not self.config_path.exists():
            return self.defaults.copy()

        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            # Validate and merge with defaults
            return {
                'default_mode': config.get('default_mode', self.defaults['default_mode']),
                'last_mode': config.get('last_mode', self.defaults['last_mode']),
                'auto_restore_mode': config.get('auto_restore_mode', self.defaults['auto_restore_mode'])
            }
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Could not load mode preferences: {e}")
            return self.defaults.copy()

    def save(self, mode_name):
        """
        Save current mode as last_mode preference.

        Args:
            mode_name: Name of current mode ('seqtrak', 'midi', etc.)
        """
        # Load current preferences
        prefs = self.load()

        # Update last_mode
        prefs['last_mode'] = mode_name

        # Write to file
        try:
            with open(self.config_path, 'w') as f:
                json.dump(prefs, f, indent=2)
        except OSError as e:
            print(f"Warning: Could not save mode preferences: {e}")

    def get_boot_mode(self):
        """
        Get the mode to use on boot.

        Returns:
            str: Mode name ('seqtrak', 'midi', etc.)
                 Returns last_mode if auto_restore_mode is True,
                 otherwise returns default_mode.
        """
        prefs = self.load()

        if prefs['auto_restore_mode']:
            return prefs['last_mode']
        return prefs['default_mode']

    def set_auto_restore(self, enabled):
        """
        Enable or disable auto-restore mode.

        Args:
            enabled: True to auto-restore last mode, False to always use default
        """
        prefs = self.load()
        prefs['auto_restore_mode'] = enabled
        try:
            with open(self.config_path, 'w') as f:
                json.dump(prefs, f, indent=2)
        except OSError as e:
            print(f"Warning: Could not save auto-restore preference: {e}")

    def set_default_mode(self, mode_name):
        """
        Set the default boot mode (used when auto_restore is disabled).

        Args:
            mode_name: Mode name ('seqtrak', 'midi', etc.)
        """
        prefs = self.load()
        prefs['default_mode'] = mode_name
        try:
            with open(self.config_path, 'w') as f:
                json.dump(prefs, f, indent=2)
        except OSError as e:
            print(f"Warning: Could not save default mode preference: {e}")
