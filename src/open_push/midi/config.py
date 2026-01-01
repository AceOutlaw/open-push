"""
MIDI Bridge Configuration
=========================

Loads and manages configuration from JSON files.
Default config is created on first run.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional


# Default configuration directory
DEFAULT_CONFIG_DIR = Path.home() / '.config' / 'open-push-midi'


# Default main configuration
DEFAULT_CONFIG = {
    'version': 1,

    # Output settings
    'output_type': 'auto',  # 'auto', 'usb_gadget', 'external', 'bluetooth'
    'output_device': None,  # Specific device name (or None for auto-detect)
    'midi_channel': 0,      # Default MIDI channel (0-15)

    # Default mode on startup
    'default_mode': 'keyboard',

    # Keyboard mode settings
    'keyboard': {
        'default_scale': 'minor',
        'default_root': 0,      # 0=C, 1=C#, 2=D, etc.
        'default_octave': 2,    # Octave offset (-2 to +4)
        'in_key_mode': True,    # Start in in-key mode
        'layout': 'fourths_up', # Isomorphic layout preset
        'velocity_curve': 1.0,  # 0.5=soft, 1.0=linear, 2.0=hard
        'velocity_min': 1,      # Minimum output velocity
        'velocity_max': 127,    # Maximum output velocity
    },

    # Drum mode settings
    'drum': {
        'base_note': 36,        # Bottom-left pad note (C2 = kick)
        'midi_channel': 9,      # Drum channel (0-indexed, so 9 = channel 10)
    },

    # Accent (fixed velocity) settings
    'accent': {
        'enabled_by_default': False,
        'fixed_velocity': 127,  # Velocity when accent is on
    },

    # Pad colors (customizable)
    'pad_colors': {
        'scale_note': 'white',      # Notes in scale
        'root_note': 'blue',        # Root/octave notes
        'chromatic_note': 'gray',   # Out-of-scale notes in chromatic mode
        'off_note': 'off',          # Out-of-scale notes in in-key mode
        'pressed': 'white',         # Color when pad is pressed
    },

    # Global controls (persist across modes)
    'global_controls': {
        'master_volume': {
            'enabled': True,
            'cc': 7,
            'channel': 0,
        },
        'tempo_knob': {
            'enabled': True,
            'cc': 80,
            'channel': 0,
        },
        'swing_knob': {
            'enabled': True,
            'cc': 81,
            'channel': 0,
        },
    },

    # Transport buttons
    'transport': {
        'play': {'type': 'midi_start'},     # Send MIDI Start (0xFA)
        'stop': {'type': 'midi_stop'},      # Send MIDI Stop (0xFC)
        'record': {'type': 'cc', 'cc': 117, 'channel': 0},
        'tap_tempo': {'type': 'cc', 'cc': 82, 'channel': 0},
        'metronome': {'type': 'cc', 'cc': 83, 'channel': 0},
    },
}


# Default encoder bank mappings
DEFAULT_ENCODER_MAPPINGS = {
    'banks': [
        {
            'name': 'Volume',
            'encoders': [
                {'cc': 7, 'channel': 0, 'label': 'Ch 1', 'min': 0, 'max': 127},
                {'cc': 7, 'channel': 1, 'label': 'Ch 2', 'min': 0, 'max': 127},
                {'cc': 7, 'channel': 2, 'label': 'Ch 3', 'min': 0, 'max': 127},
                {'cc': 7, 'channel': 3, 'label': 'Ch 4', 'min': 0, 'max': 127},
                {'cc': 7, 'channel': 4, 'label': 'Ch 5', 'min': 0, 'max': 127},
                {'cc': 7, 'channel': 5, 'label': 'Ch 6', 'min': 0, 'max': 127},
                {'cc': 7, 'channel': 6, 'label': 'Ch 7', 'min': 0, 'max': 127},
                {'cc': 7, 'channel': 7, 'label': 'Ch 8', 'min': 0, 'max': 127},
            ],
        },
        {
            'name': 'Pan',
            'encoders': [
                {'cc': 10, 'channel': 0, 'label': 'Ch 1', 'min': 0, 'max': 127},
                {'cc': 10, 'channel': 1, 'label': 'Ch 2', 'min': 0, 'max': 127},
                {'cc': 10, 'channel': 2, 'label': 'Ch 3', 'min': 0, 'max': 127},
                {'cc': 10, 'channel': 3, 'label': 'Ch 4', 'min': 0, 'max': 127},
                {'cc': 10, 'channel': 4, 'label': 'Ch 5', 'min': 0, 'max': 127},
                {'cc': 10, 'channel': 5, 'label': 'Ch 6', 'min': 0, 'max': 127},
                {'cc': 10, 'channel': 6, 'label': 'Ch 7', 'min': 0, 'max': 127},
                {'cc': 10, 'channel': 7, 'label': 'Ch 8', 'min': 0, 'max': 127},
            ],
        },
        {
            'name': 'Filter',
            'encoders': [
                {'cc': 74, 'channel': 0, 'label': 'Cutoff', 'min': 0, 'max': 127},
                {'cc': 71, 'channel': 0, 'label': 'Reso', 'min': 0, 'max': 127},
                {'cc': 73, 'channel': 0, 'label': 'Attack', 'min': 0, 'max': 127},
                {'cc': 75, 'channel': 0, 'label': 'Decay', 'min': 0, 'max': 127},
                {'cc': 76, 'channel': 0, 'label': 'Sustain', 'min': 0, 'max': 127},
                {'cc': 72, 'channel': 0, 'label': 'Release', 'min': 0, 'max': 127},
                {'cc': 91, 'channel': 0, 'label': 'Reverb', 'min': 0, 'max': 127},
                {'cc': 93, 'channel': 0, 'label': 'Chorus', 'min': 0, 'max': 127},
            ],
        },
        {
            'name': 'FX/Mod',
            'encoders': [
                {'cc': 1, 'channel': 0, 'label': 'Mod', 'min': 0, 'max': 127},
                {'cc': 11, 'channel': 0, 'label': 'Expr', 'min': 0, 'max': 127},
                {'cc': 5, 'channel': 0, 'label': 'Porta', 'min': 0, 'max': 127},
                {'cc': 64, 'channel': 0, 'label': 'Sustain', 'min': 0, 'max': 127},
                {'cc': 65, 'channel': 0, 'label': 'Porta Sw', 'min': 0, 'max': 127},
                {'cc': 84, 'channel': 0, 'label': 'Ctrl 84', 'min': 0, 'max': 127},
                {'cc': 85, 'channel': 0, 'label': 'Ctrl 85', 'min': 0, 'max': 127},
                {'cc': 86, 'channel': 0, 'label': 'Ctrl 86', 'min': 0, 'max': 127},
            ],
        },
    ]
}


# Default button mappings (buttons that send CCs)
DEFAULT_BUTTON_MAPPINGS = {
    'buttons': {
        # Mode switching (internal actions)
        'note': {'action': 'mode_switch', 'mode': 'keyboard'},
        'session': {'action': 'mode_switch', 'mode': 'drum'},
        'device': {'action': 'mode_switch', 'mode': 'encoder'},
        'scale': {'action': 'mode_switch', 'mode': 'scale_select'},

        # Transport
        'play': {'action': 'transport', 'transport': 'play'},
        'stop': {'action': 'transport', 'transport': 'stop'},
        'record': {'action': 'transport', 'transport': 'record'},

        # Keyboard controls
        'octave_up': {'action': 'internal', 'function': 'octave_up'},
        'octave_down': {'action': 'internal', 'function': 'octave_down'},
        'accent': {'action': 'internal', 'function': 'accent_toggle'},
        'note_repeat': {'action': 'internal', 'function': 'note_repeat_toggle'},

        # Encoder bank switching
        'page_left': {'action': 'internal', 'function': 'encoder_bank_prev'},
        'page_right': {'action': 'internal', 'function': 'encoder_bank_next'},

        # Configurable buttons (can send CCs)
        'tap_tempo': {'action': 'send_cc', 'cc': 82, 'channel': 0, 'value': 127},
        'metronome': {'action': 'send_cc', 'cc': 83, 'channel': 0, 'value': 127},
    }
}


class MIDIConfig:
    """
    Configuration manager for MIDI bridge.

    Loads config from JSON files, creates defaults if missing.
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize configuration.

        Args:
            config_dir: Custom config directory (default: ~/.config/open-push-midi/)
        """
        self.config_dir = Path(config_dir) if config_dir else DEFAULT_CONFIG_DIR

        # Config file paths
        self.config_file = self.config_dir / 'config.json'
        self.encoder_file = self.config_dir / 'encoder_mappings.json'
        self.button_file = self.config_dir / 'button_mappings.json'

        # Load configs
        self.config = self._load_or_create(self.config_file, DEFAULT_CONFIG)
        self.encoder_mappings = self._load_or_create(self.encoder_file, DEFAULT_ENCODER_MAPPINGS)
        self.button_mappings = self._load_or_create(self.button_file, DEFAULT_BUTTON_MAPPINGS)

    def _load_or_create(self, path: Path, defaults: Dict) -> Dict:
        """Load config file or create with defaults."""
        if path.exists():
            try:
                with open(path, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults (keeps new default keys)
                    return self._deep_merge(defaults, loaded)
            except (json.JSONDecodeError, IOError) as e:
                print(f"Warning: Could not load {path}: {e}")
                return defaults.copy()
        else:
            # Create config directory and file
            self._ensure_dir()
            self._save(path, defaults)
            return defaults.copy()

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _ensure_dir(self):
        """Ensure config directory exists."""
        self.config_dir.mkdir(parents=True, exist_ok=True)

    def _save(self, path: Path, data: Dict):
        """Save config to file."""
        self._ensure_dir()
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def save(self):
        """Save all config files."""
        self._save(self.config_file, self.config)
        self._save(self.encoder_file, self.encoder_mappings)
        self._save(self.button_file, self.button_mappings)

    # =========================================================================
    # Config Accessors
    # =========================================================================

    @property
    def output_type(self) -> str:
        return self.config.get('output_type', 'auto')

    @property
    def output_device(self) -> Optional[str]:
        return self.config.get('output_device')

    @property
    def midi_channel(self) -> int:
        return self.config.get('midi_channel', 0)

    @property
    def default_mode(self) -> str:
        return self.config.get('default_mode', 'keyboard')

    @property
    def keyboard_config(self) -> Dict:
        return self.config.get('keyboard', DEFAULT_CONFIG['keyboard'])

    @property
    def drum_config(self) -> Dict:
        return self.config.get('drum', DEFAULT_CONFIG['drum'])

    @property
    def accent_config(self) -> Dict:
        return self.config.get('accent', DEFAULT_CONFIG['accent'])

    @property
    def transport_config(self) -> Dict:
        return self.config.get('transport', DEFAULT_CONFIG['transport'])

    @property
    def global_controls(self) -> Dict:
        return self.config.get('global_controls', DEFAULT_CONFIG['global_controls'])

    @property
    def pad_colors(self) -> Dict:
        return self.config.get('pad_colors', DEFAULT_CONFIG['pad_colors'])

    def get_encoder_bank(self, bank_index: int) -> Dict:
        """Get encoder mapping for a specific bank."""
        banks = self.encoder_mappings.get('banks', [])
        if 0 <= bank_index < len(banks):
            return banks[bank_index]
        return {'name': f'Bank {bank_index + 1}', 'encoders': []}

    def get_encoder_mapping(self, bank_index: int, encoder_index: int) -> Optional[Dict]:
        """Get mapping for a specific encoder in a specific bank."""
        bank = self.get_encoder_bank(bank_index)
        encoders = bank.get('encoders', [])
        if 0 <= encoder_index < len(encoders):
            enc = encoders[encoder_index].copy()
            enc['name'] = enc.get('label', f'Enc {encoder_index + 1}')
            enc['enabled'] = True
            return enc
        return None

    @property
    def num_encoder_banks(self) -> int:
        return len(self.encoder_mappings.get('banks', []))

    def get_button_mapping(self, button_name: str) -> Optional[Dict]:
        """Get mapping for a specific button."""
        return self.button_mappings.get('buttons', {}).get(button_name)
