"""
OpenPush Reason Bridge
======================

Connects Push 1 hardware to Reason via the OpenPush Remote codecs.

This bridge:
1. Creates 3 virtual MIDI ports (Transport, Devices, Mixer)
2. Reads Push hardware input (pads, buttons, encoders)
3. Translates to CC messages the Lua codecs expect
4. Receives feedback from Reason and updates Push LEDs/display

Usage:
    python3 -m open_push.reason.bridge
"""

import mido
import time
import threading
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional, Callable, Dict, List

# Import our core modules
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from open_push.core.hardware import Push1Hardware
from open_push.core.display import Push1Display
from open_push.core.constants import COLORS, BUTTON_CC, note_name
from open_push.music.scales import SCALES, SCALE_NAMES, is_in_scale, is_root_note
from open_push.music.layout import IsomorphicLayout, LAYOUT_PRESETS


class BridgeMode(Enum):
    """Current operating mode of the bridge."""
    NOTE = auto()       # Isomorphic keyboard
    DRUM = auto()       # Drum pad mode (Kong/Redrum/Rex)
    DEVICE = auto()     # Device parameter control
    MIXER = auto()      # Mixer volume/pan
    TRANSPORT = auto()  # Transport controls
    SCALE = auto()      # Scale/root selection
    BROWSE = auto()     # Browser navigation


@dataclass
class BridgeState:
    """Tracks the current state of the bridge."""
    mode: BridgeMode = BridgeMode.NOTE
    playing: bool = False
    recording: bool = False
    looping: bool = False
    metronome: bool = False
    tempo: float = 120.0

    # Scale settings
    scale_index: int = 0
    root_note: int = 0  # 0=C, 1=C#, etc.
    in_key_mode: bool = True
    layout_preset: int = 0
    
    # Velocity settings
    accent_mode: bool = False
    velocity_min: int = 40
    velocity_max: int = 127
    velocity_curve: float = 1.0

    # Drum mode
    drum_device: str = "kong"  # kong, redrum, dr_octo_rex

    # Mixer state
    mixer_bank: int = 0  # 0=ch1-8, 1=ch9-16, etc.
    mixer_mode: str = "volume"  # volume, pan

    # Active notes for note-off tracking
    active_notes: Dict[int, int] = field(default_factory=dict)


class ReasonBridge:
    """
    Main bridge between Push hardware and Reason.
    """

    # CC numbers for Transport codec
    # Aligned with Push 1 Hardware CCs (Channel 0 -> 15)
    CC_PLAY = 0x55       # CC 85
    CC_STOP = 0x1D       # CC 29
    CC_RECORD = 0x56     # CC 86
    CC_REWIND = 0x2C     # CC 44
    CC_FORWARD = 0x2D    # CC 45
    CC_LOOP = 0x37       # CC 55
    CC_METRONOME = 0x09  # CC 9
    CC_TEMPO = 0x0F      # CC 15
    CC_NAV_UP = 0x2E     # CC 46
    CC_NAV_DOWN = 0x2F   # CC 47
    CC_NAV_LEFT = 0x2C   # CC 44 (Shared with Rewind)
    CC_NAV_RIGHT = 0x2D  # CC 45 (Shared with Forward)
    CC_BROWSE_SELECT = 0x30 # CC 48 (Select)
    CC_BROWSE_BACK = 0x33   # CC 51 (Shift)

    # CC numbers for Devices codec (encoders)
    CC_ENCODER_BASE = 0x47  # Encoders 1-8 are 0x47-0x4E
    CC_UPPER_BUTTON_BASE = 0x66  # Upper buttons 1-8
    CC_LOWER_BUTTON_BASE = 0x14  # Lower buttons 1-8

    # CC numbers for Mixer codec
    CC_VOLUME_BASE = 0x30  # Volume 1-8
    CC_PAN_BASE = 0x38     # Pan 1-8
    CC_MUTE_BASE = 0x40    # Mute 1-8
    CC_SOLO_BASE = 0x48    # Solo 1-8
    CC_SELECT_BASE = 0x20  # Select 1-8
    CC_MASTER = 0x07

    # Push button to bridge action mapping
    BUTTON_ACTIONS = {
        BUTTON_CC['play']: 'play',
        BUTTON_CC['record']: 'record',
        BUTTON_CC['automation']: 'loop',
        BUTTON_CC['metronome']: 'metronome',
        BUTTON_CC['stop']: 'stop',
        BUTTON_CC['note']: 'mode_note',
        BUTTON_CC['session']: 'mode_drum',
        BUTTON_CC['device']: 'mode_device',
        BUTTON_CC['browse']: 'mode_browse',
        BUTTON_CC['volume']: 'mode_mixer',
        BUTTON_CC['scale']: 'mode_scale',
        BUTTON_CC['accent']: 'accent',
        BUTTON_CC['left']: 'nav_left',
        BUTTON_CC['right']: 'nav_right',
        BUTTON_CC['up']: 'nav_up',
        BUTTON_CC['down']: 'nav_down',
        BUTTON_CC['octave_up']: 'octave_up',
        BUTTON_CC['octave_down']: 'octave_down',
    }

    def __init__(self):
        self.state = BridgeState()
        self.push: Optional[Push1Hardware] = None
        self.display: Optional[Push1Display] = None
        self.layout = IsomorphicLayout()
        
        # Initialize default scale settings
        self.layout.set_in_key_mode(self.state.in_key_mode)
        self.layout.set_scale(self.state.root_note, SCALE_NAMES[self.state.scale_index])

        # Virtual MIDI ports for Reason
        self.port_transport: Optional[mido.ports.BaseOutput] = None
        self.port_devices: Optional[mido.ports.BaseOutput] = None
        self.port_mixer: Optional[mido.ports.BaseOutput] = None

        # Input ports from Reason (for feedback)
        self.port_transport_in: Optional[mido.ports.BaseInput] = None
        self.port_devices_in: Optional[mido.ports.BaseInput] = None
        self.port_mixer_in: Optional[mido.ports.BaseInput] = None

        self.running = False
        self._feedback_thread: Optional[threading.Thread] = None

    def start(self):
        """Start the bridge."""
        print("OpenPush Reason Bridge")
        print("=" * 40)
        print()

        # Create virtual MIDI ports
        print("Creating virtual MIDI ports...")
        try:
            self.port_transport = mido.open_output('OpenPush Transport', virtual=True)
            self.port_devices = mido.open_output('OpenPush Devices', virtual=True)
            self.port_mixer = mido.open_output('OpenPush Mixer', virtual=True)
            print("  ✓ OpenPush Transport")
            print("  ✓ OpenPush Devices")
            print("  ✓ OpenPush Mixer")
        except Exception as e:
            print(f"  ✗ Failed to create virtual ports: {e}")
            return False

                # Connect to Push hardware
                print()
                print("Connecting to Push hardware...")
                try:
                    self.push = Push1Hardware()
                    self.push.connect()
                    self.push.set_user_mode()  # CRITICAL: Take control of hardware (stops rainbow mode)
                    self.display = Push1Display(self.push)
                    print("  ✓ Push 1 connected")
                except Exception as e:
                    print(f"  ✗ Failed to connect to Push: {e}")
                    print()
                    print("Running in virtual-only mode (no hardware)")
                    self.push = None
                    self.display = None
        
                # Initialize display
                self._update_display()
                self._update_grid()
                self._update_button_leds()
        
                self.running = True
        
                print()
                print("Bridge running! Press Ctrl+C to stop.")
                print()
                print("In Reason:")
                print("  1. Go to Preferences > Control Surfaces")
                print("  2. Add OpenPush Transport, Devices, and Mixer")
                print("  3. Assign each to matching 'OpenPush ...' MIDI port")
                print()
        
                return True
        
            def stop(self):
                """Stop the bridge."""
                self.running = False
        
                # Close ports
                if self.port_transport:
                    self.port_transport.close()
                if self.port_devices:
                    self.port_devices.close()
                if self.port_mixer:
                    self.port_mixer.close()
        
                # Disconnect Push
                if self.push:
                    self.push.disconnect()
        
                print("Bridge stopped.")
        
            def run(self):
                """Main run loop."""
                if not self.start():
                    return
        
                try:
                    if self.push:
                        # Main Event Loop for Hardware
                        for msg in self.push.iter_messages():
                            if not self.running:
                                break
        
                            if msg.type == 'note_on' or msg.type == 'note_off':
                                # Pads (36-99)
                                if 36 <= msg.note <= 99:
                                    self._handle_pad(msg.note, msg.velocity if msg.type == 'note_on' else 0)
                                # Touch Strip (sometimes mapped to note? No, typically pitchwheel)
        
                            elif msg.type == 'control_change':
                                # Buttons & Encoders
                                # Encoders are CCs 71-79, 14, 15
                                if (71 <= msg.control <= 79) or msg.control in [14, 15]:
                                    # Encoder delta: 1-63 = cw, 65-127 = ccw
                                    delta = 0
                                    if msg.value < 64:
                                        delta = msg.value
                                    else:
                                        delta = msg.value - 128
                                    
                                    # Normalize encoder index
                                    encoder_idx = -1
                                    if 71 <= msg.control <= 78:
                                        encoder_idx = msg.control - 71
                                    elif msg.control == 79: # Master
                                        encoder_idx = 8
                                    elif msg.control == 14: # Tempo
                                        encoder_idx = 0 # Map tempo to encoder 0 in transport mode?
                                    
                                    if encoder_idx >= 0:
                                        self._handle_encoder(encoder_idx, delta)
                                    elif msg.control == 14:
                                        # Special case for tempo
                                        self._handle_encoder(0, delta)
        
                                else:
                                    # Standard Buttons
                                    self._handle_button(msg.control, msg.value)
        
                            elif msg.type == 'pitchwheel':
                                # Touch Strip
                                # Pitch wheel value is -8192 to 8191
                                # Map to 0-127 or similar
                                self._handle_touch_strip(msg.pitch)
        
                    else:
                        # Virtual mode fallback
                        while self.running:
                            time.sleep(0.1)
        
                except KeyboardInterrupt:
                    print("\nShutting down...")
                finally:
                    self.stop()
                    
            # -------------------------------------------------------------------------
            # Helper Methods
            # -------------------------------------------------------------------------
        
            def _handle_touch_strip(self, pitch_val: int):
                """
                Handle touch strip input (Pitch Wheel).
                pitch_val: -8192 to 8191
                """
                # Example: Map to modulation or pitch bend for Devices port
                # Map -8192..8191 -> 0..16383 for standard MIDI pitch bend
                midi_val = pitch_val + 8192
                
                # Send to Devices port on channel 0 (or 15)
                msg = mido.Message('pitchwheel', pitch=pitch_val, channel=0)
                if self.port_devices:
                    self.port_devices.send(msg)    
    def apply_velocity_curve(self, velocity: int) -> int:
        """
        Apply velocity curve to input velocity.
        
        Args:
            velocity: Input velocity (0-127)
            
        Returns:
            Curved velocity (0-127)
        """
        if velocity <= 0:
            return 0
            
        if self.state.accent_mode:
            return 127
            
        # Normalize to 0.0-1.0
        norm = (velocity - 1) / 126.0
        
        # Apply curve (currently linear 1.0, but supports adjustment)
        curved = pow(norm, self.state.velocity_curve)
        
        # Scale back to range with min floor
        val_range = self.state.velocity_max - self.state.velocity_min
        output = int(self.state.velocity_min + (curved * val_range))
        
        return max(1, min(127, output))

    # -------------------------------------------------------------------------
    # Push Input Handlers
    # -------------------------------------------------------------------------

    def _handle_pad(self, pad: int, velocity: int):
        """Handle pad press/release from Push."""
        if velocity > 0:
            self._handle_pad_press(pad, velocity)
        else:
            self._handle_pad_release(pad)

    def _handle_pad_press(self, pad: int, velocity: int):
        """Handle pad press."""
        row = pad // 8
        col = pad % 8
        
        # Apply velocity curve
        out_velocity = self.apply_velocity_curve(velocity)

        if self.state.mode == BridgeMode.NOTE:
            # Isomorphic keyboard mode
            note = self.layout.get_midi_note(pad)
            
            if note is not None and 0 <= note <= 127:
                self.state.active_notes[pad] = note
                # Send note to Devices port (has keyboard)
                msg = mido.Message('note_on', note=note, velocity=out_velocity, channel=15)
                if self.port_devices:
                    self.port_devices.send(msg)
                    
            # Flash pad
            if self.push:
                self.push.set_pad_color(row, col, COLORS['green'])

        elif self.state.mode == BridgeMode.DRUM:
            # Drum mode - send directly as note
            note = 36 + pad  # Map pads to notes 36-99
            self.state.active_notes[pad] = note
            msg = mido.Message('note_on', note=note, velocity=out_velocity, channel=15)
            if self.port_devices:
                self.port_devices.send(msg)
                
            # Flash pad
            if self.push:
                self.push.set_pad_color(row, col, COLORS['green'])

        elif self.state.mode == BridgeMode.SCALE:
            # Scale selection mode
            if row >= 4:
                # Bottom 4 rows: root note selection
                root = (row - 4) * 8 + col
                if root < 12:
                    self.state.root_note = root
                    self.layout.set_root_note(36 + root) # Base C2
                    self.layout.set_scale(root, SCALE_NAMES[self.state.scale_index])
                    self._update_display()
                    self._update_grid()
            elif row <= 3:
                # Top 4 rows: scale selection
                scale_idx = row * 8 + col
                if scale_idx < len(SCALE_NAMES):
                    self.state.scale_index = scale_idx
                    self.layout.set_scale(self.state.root_note, SCALE_NAMES[scale_idx])
                    self._update_display()
                    self._update_grid()
            
            # Additional controls on side?
            # Implemented via buttons for now

        elif self.state.mode == BridgeMode.MIXER:
            # Mixer mode - pad press selects channel
            if row == 7:  # Bottom row
                channel = col + 1
                cc = self.CC_SELECT_BASE + col
                msg = mido.Message('control_change', control=cc, value=127, channel=15)
                if self.port_mixer:
                    self.port_mixer.send(msg)

    def _handle_pad_release(self, pad: int):
        """Handle pad release."""
        row = pad // 8
        col = pad % 8
        
        if pad in self.state.active_notes:
            note = self.state.active_notes.pop(pad)
            msg = mido.Message('note_off', note=note, velocity=0, channel=15)
            if self.port_devices:
                self.port_devices.send(msg)
        
        # Restore pad color on release
        if self.push:
            if self.state.mode == BridgeMode.NOTE:
                info = self.layout.get_pad_info(row, col)
                if info['is_root']:
                    color = COLORS['blue']
                elif info['is_in_scale']:
                    color = COLORS['white']
                else:
                    color = COLORS['off'] if self.state.in_key_mode else COLORS['white_dim']
                self.push.set_pad_color(row, col, color)
            elif self.state.mode == BridgeMode.DRUM:
                # Restore drum color
                if self.state.drum_device == "kong" and pad < 16:
                    color = COLORS['orange']
                elif self.state.drum_device == "redrum" and pad < 10:
                    color = COLORS['red']
                elif self.state.drum_device == "dr_octo_rex" and pad < 8:
                    color = COLORS['purple']
                else:
                    color = COLORS['off']
                self.push.set_pad_color(row, col, color)

    def _handle_button(self, cc: int, value: int):
        """Handle button press/release from Push."""
        if value == 0:  # Only act on press
            return

        action = self.BUTTON_ACTIONS.get(cc)
        if not action:
            return

        # Transport actions
        if action == 'play':
            self.state.playing = not self.state.playing
            self._send_transport_cc(self.CC_PLAY, 127 if self.state.playing else 0)
            self._update_button_leds()

        elif action == 'stop':
            self.state.playing = False
            self._send_transport_cc(self.CC_STOP, 127)
            self._update_button_leds()

        elif action == 'record':
            self.state.recording = not self.state.recording
            self._send_transport_cc(self.CC_RECORD, 127 if self.state.recording else 0)
            self._update_button_leds()

        elif action == 'loop':
            self.state.looping = not self.state.looping
            self._send_transport_cc(self.CC_LOOP, 127 if self.state.looping else 0)
            self._update_button_leds()

        elif action == 'metronome':
            self.state.metronome = not self.state.metronome
            self._send_transport_cc(self.CC_METRONOME, 127 if self.state.metronome else 0)
            self._update_button_leds()
            
        elif action == 'accent':
            self.state.accent_mode = not self.state.accent_mode
            self._update_button_leds()
            self._update_display()

        # Mode switching
        elif action == 'mode_note':
            self.state.mode = BridgeMode.NOTE
            self._update_display()
            self._update_grid()
            self._update_button_leds()

        elif action == 'mode_drum':
            self.state.mode = BridgeMode.DRUM
            self._update_display()
            self._update_grid()
            self._update_button_leds()

        elif action == 'mode_device':
            self.state.mode = BridgeMode.DEVICE
            self._update_display()
            self._update_grid()
            self._update_button_leds()

        elif action == 'mode_mixer':
            self.state.mode = BridgeMode.MIXER
            self._update_display()
            self._update_grid()
            self._update_button_leds()

        elif action == 'mode_scale':
            # Toggle logic similar to experiments/isomorphic_controller.py
            if self.state.mode == BridgeMode.SCALE:
                # Toggle back to previous mode (Note)
                self.state.mode = BridgeMode.NOTE
            else:
                self.state.mode = BridgeMode.SCALE
            self._update_display()
            self._update_grid()
            self._update_button_leds()

        elif action == 'mode_browse':
            self.state.mode = BridgeMode.BROWSE
            self._update_display()
            self._update_grid()
            self._update_button_leds()

        # Navigation
        elif action == 'nav_left':
            self._send_transport_cc(self.CC_NAV_LEFT, 127)
        elif action == 'nav_right':
            self._send_transport_cc(self.CC_NAV_RIGHT, 127)
        elif action == 'nav_up':
            self._send_transport_cc(self.CC_NAV_UP, 127)
        elif action == 'nav_down':
            self._send_transport_cc(self.CC_NAV_DOWN, 127)

        # Octave shift
        elif action == 'octave_up':
            if self.state.mode == BridgeMode.NOTE:
                self.layout.shift_octave(1)
                self._update_display()
                self._update_grid()
                self._update_button_leds()
        elif action == 'octave_down':
            if self.state.mode == BridgeMode.NOTE:
                self.layout.shift_octave(-1)
                self._update_display()
                self._update_grid()
                self._update_button_leds()

    def _handle_encoder(self, encoder: int, direction: int):
        """Handle encoder turn from Push."""
        # direction: positive = clockwise, negative = counter-clockwise

        if self.state.mode == BridgeMode.DEVICE:
            # Send encoder value to Devices port
            # Use relative encoding: 64 + delta
            cc = self.CC_ENCODER_BASE + encoder
            value = 64 + direction
            msg = mido.Message('control_change', control=cc, value=value, channel=15)
            if self.port_devices:
                self.port_devices.send(msg)

        elif self.state.mode == BridgeMode.MIXER:
            if self.state.mixer_mode == "volume":
                cc = self.CC_VOLUME_BASE + encoder
            else:  # pan
                cc = self.CC_PAN_BASE + encoder
            value = 64 + direction
            msg = mido.Message('control_change', control=cc, value=value, channel=15)
            if self.port_mixer:
                self.port_mixer.send(msg)

        elif self.state.mode == BridgeMode.TRANSPORT:
            # Tempo encoder
            if encoder == 0:
                self._send_transport_cc(self.CC_TEMPO, 64 + direction)

    # -------------------------------------------------------------------------
    # MIDI Output Helpers
    # -------------------------------------------------------------------------

    def _send_transport_cc(self, cc: int, value: int):
        """Send CC message to Transport port."""
        if self.port_transport:
            msg = mido.Message('control_change', control=cc, value=value, channel=15)
            self.port_transport.send(msg)

    def _send_devices_cc(self, cc: int, value: int):
        """Send CC message to Devices port."""
        if self.port_devices:
            msg = mido.Message('control_change', control=cc, value=value, channel=15)
            self.port_devices.send(msg)

    def _send_mixer_cc(self, cc: int, value: int):
        """Send CC message to Mixer port."""
        if self.port_mixer:
            msg = mido.Message('control_change', control=cc, value=value, channel=15)
            self.port_mixer.send(msg)

    # -------------------------------------------------------------------------
    # Display & LED Updates
    # -------------------------------------------------------------------------

    def _update_display(self):
        """Update Push LCD display based on current mode."""
        if not self.display:
            return

        self.display.clear()

        mode_names = {
            BridgeMode.NOTE: "NOTE",
            BridgeMode.DRUM: "DRUM",
            BridgeMode.DEVICE: "DEVICE",
            BridgeMode.MIXER: "MIXER",
            BridgeMode.TRANSPORT: "TRANSPORT",
            BridgeMode.SCALE: "SCALE",
            BridgeMode.BROWSE: "BROWSE",
        }

        # Line 1: Mode
        self.display.set_line(0, f"OpenPush - {mode_names[self.state.mode]}")

        if self.state.mode == BridgeMode.NOTE:
            scale_name = SCALE_NAMES[self.state.scale_index]
            root = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'][self.state.root_note]
            octave = self.layout.get_octave()
            self.display.set_line(1, f"Scale: {root} {scale_name}")
            
            accent_str = "ON" if self.state.accent_mode else "OFF"
            self.display.set_line(2, f"Octave: {octave}  Accent: {accent_str}")
            
            mode_str = "In-Key" if self.state.in_key_mode else "Chromatic"
            self.display.set_line(3, f"Mode: {mode_str}")

        elif self.state.mode == BridgeMode.DRUM:
            self.display.set_line(1, f"Device: {self.state.drum_device.upper()}")
            self.display.set_line(2, "Pads trigger drums")
            self.display.set_line(3, "")

        elif self.state.mode == BridgeMode.MIXER:
            self.display.set_line(1, f"Mode: {self.state.mixer_mode.upper()}")
            self.display.set_line(2, f"Bank: {self.state.mixer_bank + 1}")
            self.display.set_line(3, "Turn encoders")

        elif self.state.mode == BridgeMode.SCALE:
            self.display.set_line(1, "Top: Select scale")
            self.display.set_line(2, "Bottom: Select root")
            self.display.set_line(3, "Use Note mode to play")

        elif self.state.mode == BridgeMode.DEVICE:
            self.display.set_line(1, "Turn encoders to")
            self.display.set_line(2, "control device params")
            self.display.set_line(3, "")

        elif self.state.mode == BridgeMode.BROWSE:
            self.display.set_line(1, "Use arrows to")
            self.display.set_line(2, "navigate browser")
            self.display.set_line(3, "")

        self.display.update()

    def _update_grid(self):
        """Update pad grid colors based on current mode."""
        if not self.push:
            return

        if self.state.mode == BridgeMode.NOTE:
            # Isomorphic keyboard colors
            for row in range(8):
                for col in range(8):
                    info = self.layout.get_pad_info(row, col)
                    # Colors: Blue=Root, White=Scale, Off/Dim=Other
                    if info['is_root']:
                        color = COLORS['blue']
                    elif info['is_in_scale']:
                        color = COLORS['white']
                    else:
                        color = COLORS['off'] if self.state.in_key_mode else COLORS['white_dim']
                    self.push.set_pad_color(row, col, color)

        elif self.state.mode == BridgeMode.DRUM:
            # Drum pad colors
            for row in range(8):
                for col in range(8):
                    pad = row * 8 + col
                    if self.state.drum_device == "kong" and pad < 16:
                        color = COLORS['orange']
                    elif self.state.drum_device == "redrum" and pad < 10:
                        color = COLORS['red']
                    elif self.state.drum_device == "dr_octo_rex" and pad < 8:
                        color = COLORS['purple']
                    else:
                        color = COLORS['off']
                    self.push.set_pad_color(row, col, color)

        elif self.state.mode == BridgeMode.SCALE:
            # Scale selection grid
            for row in range(8):
                for col in range(8):
                    if row >= 4:
                        # Root selection (bottom 4 rows)
                        root = (row - 4) * 8 + col
                        if root < 12:
                            if root == self.state.root_note:
                                color = COLORS['green']
                            else:
                                color = COLORS['white_dim']
                        else:
                            color = COLORS['off']
                    else:
                        # Scale selection (top 4 rows)
                        scale_idx = row * 8 + col
                        if scale_idx < len(SCALE_NAMES):
                            if scale_idx == self.state.scale_index:
                                color = COLORS['cyan']
                            else:
                                color = COLORS['white_dim']
                        else:
                            color = COLORS['off']
                    self.push.set_pad_color(row, col, color)

        elif self.state.mode == BridgeMode.MIXER:
            # Mixer mode - show channel colors on bottom row
            for row in range(8):
                for col in range(8):
                    if row == 7:
                        color = COLORS['blue']  # Channel select
                    else:
                        color = COLORS['off']
                    self.push.set_pad_color(row, col, color)

        else:
            # Clear grid for other modes
            for row in range(8):
                for col in range(8):
                    self.push.set_pad_color(row, col, COLORS['off'])

    def _update_button_leds(self):
        """Update button LEDs based on current state."""
        if not self.push:
            return

        # Transport LEDs
        self.push.set_button_led(BUTTON_CC['play'],
                                  COLORS['green'] if self.state.playing else COLORS['green_dim'])
        self.push.set_button_led(BUTTON_CC['record'],
                                  COLORS['red'] if self.state.recording else COLORS['red_dim'])
        self.push.set_button_led(BUTTON_CC['automation'],
                                  COLORS['yellow'] if self.state.looping else COLORS['off'])
        
        # Accent LED
        self.push.set_button_led(BUTTON_CC['accent'],
                                  COLORS['white'] if self.state.accent_mode else COLORS['white_dim'])

        # Mode LEDs
        mode_buttons = {
            BridgeMode.NOTE: BUTTON_CC['note'],
            BridgeMode.DRUM: BUTTON_CC['session'],
            BridgeMode.DEVICE: BUTTON_CC['device'],
            BridgeMode.MIXER: BUTTON_CC['volume'],
            BridgeMode.SCALE: BUTTON_CC['scale'],
            BridgeMode.BROWSE: BUTTON_CC['browse'],
        }

        for mode, button_cc in mode_buttons.items():
            if self.state.mode == mode:
                self.push.set_button_led(button_cc, COLORS['white'])
            else:
                self.push.set_button_led(button_cc, COLORS['white_dim'])


def main():
    """Main entry point."""
    bridge = ReasonBridge()
    bridge.run()


if __name__ == '__main__':
    main()