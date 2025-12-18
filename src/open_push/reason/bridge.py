"""
Reason Bridge
=============

Main bridge component that connects Push hardware to Reason
via the Remote protocol.

Architecture:
- Push hardware <-> Bridge <-> Virtual MIDI Ports <-> Reason Remote

The bridge translates Push hardware events (button presses, encoder turns,
pad hits) into Reason Remote protocol messages, and vice versa (display
updates, transport state, parameter values).
"""

import mido
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field

from ..core.hardware import Push1Hardware
from ..core.display import Push1Display
from ..core.constants import BUTTON_CC, CC_TO_BUTTON, ENCODER_CC

from .ports import ReasonPortManager
from .protocol import (
    ReasonMessage,
    MessageType,
    PortID,
    build_transport_message,
    build_encoder_message,
    build_mixer_message,
    decode_delta,
)


@dataclass
class BridgeState:
    """Current state of the bridge."""
    # Transport state
    playing: bool = False
    recording: bool = False
    looping: bool = False
    tempo: float = 120.0

    # Mode state
    current_mode: str = 'device'  # device, mixer, transport

    # Device state
    device_name: str = ""
    param_names: list = field(default_factory=lambda: [""] * 8)
    param_values: list = field(default_factory=lambda: [0] * 8)

    # Mixer state
    track_names: list = field(default_factory=lambda: [""] * 8)
    track_volumes: list = field(default_factory=lambda: [100] * 8)
    track_pans: list = field(default_factory=lambda: [64] * 8)
    track_mutes: list = field(default_factory=lambda: [False] * 8)
    track_solos: list = field(default_factory=lambda: [False] * 8)


class ReasonBridge:
    """
    Bridge between Push hardware and Reason Remote protocol.

    Creates three virtual MIDI ports that appear as separate
    control surfaces in Reason:
    - OpenPush Transport: Transport controls
    - OpenPush Devices: Device/parameter controls
    - OpenPush Mixer: Mixer controls

    Each port communicates via SysEx with corresponding Lua codecs
    installed in Reason's Remote folder.

    Usage:
        push = Push1Hardware()
        bridge = ReasonBridge(push)

        if bridge.connect():
            bridge.run()  # Main loop
        bridge.disconnect()
    """

    def __init__(self, push: Push1Hardware = None):
        """
        Initialize bridge.

        Args:
            push: Push1Hardware instance (creates one if not provided)
        """
        self.push = push or Push1Hardware()
        self.display: Optional[Push1Display] = None
        self.ports = ReasonPortManager()
        self.state = BridgeState()
        self._connected = False
        self._running = False

        # Callbacks for custom handling
        self._on_transport: Optional[Callable] = None
        self._on_device: Optional[Callable] = None
        self._on_mixer: Optional[Callable] = None

    @property
    def connected(self) -> bool:
        """Check if bridge is connected."""
        return self._connected

    def connect(self) -> bool:
        """
        Connect to Push hardware and create virtual MIDI ports.

        Returns:
            True if all connections successful
        """
        if self._connected:
            return True

        # Connect to Push hardware
        if not self.push.connect():
            print("Failed to connect to Push hardware")
            return False

        # Create display manager
        self.display = Push1Display(self.push._output_port)

        # Create virtual MIDI ports for Reason
        if not self.ports.open_all():
            print("Failed to create virtual MIDI ports")
            self.push.disconnect()
            return False

        # Set up message callbacks from Reason
        self.ports.set_transport_callback(self._handle_transport_from_reason)
        self.ports.set_devices_callback(self._handle_device_from_reason)
        self.ports.set_mixer_callback(self._handle_mixer_from_reason)

        # Initialize Push to user mode
        self.push.set_user_mode()

        self._connected = True
        print("Reason Bridge connected!")
        return True

    def disconnect(self):
        """Disconnect from Push and close virtual ports."""
        self._running = False

        if self.display:
            self.display.clear()

        self.push.clear_all_pads()
        self.push.clear_all_buttons()
        self.push.disconnect()

        self.ports.close_all()

        self._connected = False
        print("Reason Bridge disconnected")

    # =========================================================================
    # PUSH -> REASON MESSAGE HANDLING
    # =========================================================================

    def handle_push_message(self, msg: mido.Message):
        """
        Handle an incoming message from Push hardware.

        Routes messages to appropriate handlers based on type and current mode.
        """
        if msg.type == 'note_on' and 36 <= msg.note <= 99:
            self._handle_pad(msg.note, msg.velocity)

        elif msg.type == 'note_off' and 36 <= msg.note <= 99:
            self._handle_pad(msg.note, 0)

        elif msg.type == 'control_change':
            cc = msg.control
            value = msg.value

            # Check if it's a button
            if cc in CC_TO_BUTTON:
                if value > 0:  # Button press (not release)
                    self._handle_button(CC_TO_BUTTON[cc])

            # Check if it's an encoder
            elif cc in range(71, 80):  # Encoders 1-8 plus master
                encoder = cc - 71
                delta = decode_delta(value)
                self._handle_encoder(encoder, delta)

            elif cc == 14:  # Tempo encoder
                delta = decode_delta(value)
                self._handle_tempo_encoder(delta)

        elif msg.type == 'sysex':
            # Handle any SysEx from Push (usually identity response)
            pass

    def _handle_pad(self, pad_note: int, velocity: int):
        """Handle pad press/release."""
        # In device mode, pads might trigger drum sounds
        # In mixer mode, pads might select tracks
        row = (pad_note - 36) // 8
        col = (pad_note - 36) % 8

        if self.state.current_mode == 'mixer':
            if velocity > 0 and row == 0:
                # Bottom row selects tracks
                self._select_track(col)

    def _handle_button(self, button: str):
        """Handle button press."""
        # Transport buttons
        if button == 'play':
            self._send_transport(MessageType.TRANSPORT_PLAY, 1)
        elif button == 'record':
            self._send_transport(MessageType.TRANSPORT_RECORD, 1)
        elif button == 'stop':
            self._send_transport(MessageType.TRANSPORT_STOP, 1)

        # Mode selection
        elif button == 'device':
            self._set_mode('device')
        elif button == 'volume':
            self._set_mode('mixer')
        elif button == 'track':
            self._set_mode('transport')

        # Navigation
        elif button == 'left':
            if self.state.current_mode == 'device':
                # Previous device/parameter page
                pass
        elif button == 'right':
            if self.state.current_mode == 'device':
                # Next device/parameter page
                pass

    def _handle_encoder(self, encoder: int, delta: int):
        """Handle encoder turn."""
        if self.state.current_mode == 'device':
            # Send parameter change to Reason
            msg = build_encoder_message(encoder, delta)
            self.ports.devices.send_sysex(msg.to_sysex())

        elif self.state.current_mode == 'mixer':
            # Send mixer change to Reason
            # Volume or pan depending on sub-mode
            msg = build_mixer_message(MessageType.MIXER_VOLUME, encoder, delta + 64)
            self.ports.mixer.send_sysex(msg.to_sysex())

    def _handle_tempo_encoder(self, delta: int):
        """Handle tempo encoder turn."""
        msg = build_transport_message(MessageType.TRANSPORT_TEMPO, delta + 64)
        self.ports.transport.send_sysex(msg.to_sysex())

    def _send_transport(self, msg_type: MessageType, value: int):
        """Send a transport control message to Reason."""
        msg = build_transport_message(msg_type, value)
        self.ports.transport.send_sysex(msg.to_sysex())

    def _set_mode(self, mode: str):
        """Set the current operating mode."""
        self.state.current_mode = mode
        self._update_display()
        self._update_button_leds()

    def _select_track(self, track: int):
        """Select a mixer track."""
        msg = build_mixer_message(MessageType.MIXER_SELECT, track, 1)
        self.ports.mixer.send_sysex(msg.to_sysex())

    # =========================================================================
    # REASON -> PUSH MESSAGE HANDLING
    # =========================================================================

    def _handle_transport_from_reason(self, msg: mido.Message):
        """Handle message from Reason on transport port."""
        if msg.type == 'sysex':
            parsed = ReasonMessage.from_sysex(list(msg.data))
            if parsed:
                self._process_transport_message(parsed)

    def _handle_device_from_reason(self, msg: mido.Message):
        """Handle message from Reason on devices port."""
        if msg.type == 'sysex':
            parsed = ReasonMessage.from_sysex(list(msg.data))
            if parsed:
                self._process_device_message(parsed)

    def _handle_mixer_from_reason(self, msg: mido.Message):
        """Handle message from Reason on mixer port."""
        if msg.type == 'sysex':
            parsed = ReasonMessage.from_sysex(list(msg.data))
            if parsed:
                self._process_mixer_message(parsed)

    def _process_transport_message(self, msg: ReasonMessage):
        """Process a transport message from Reason."""
        if msg.msg_type == MessageType.TRANSPORT_PLAY:
            self.state.playing = msg.data[0] > 0 if msg.data else False
            self._update_transport_leds()

        elif msg.msg_type == MessageType.TRANSPORT_RECORD:
            self.state.recording = msg.data[0] > 0 if msg.data else False
            self._update_transport_leds()

        elif msg.msg_type == MessageType.TRANSPORT_LOOP:
            self.state.looping = msg.data[0] > 0 if msg.data else False
            self._update_transport_leds()

        elif msg.msg_type == MessageType.TRANSPORT_TEMPO:
            if len(msg.data) >= 2:
                # Tempo as BPM * 10 (e.g., 1200 = 120.0 BPM)
                self.state.tempo = (msg.data[0] * 128 + msg.data[1]) / 10.0
                self._update_display()

    def _process_device_message(self, msg: ReasonMessage):
        """Process a device message from Reason."""
        if msg.msg_type == MessageType.DEVICE_NAME:
            # Device name
            self.state.device_name = ''.join(chr(c) for c in msg.data)
            self._update_display()

        elif msg.msg_type == MessageType.DEVICE_PARAM:
            # Parameter update
            if len(msg.data) >= 2:
                param_idx = msg.data[0]
                value = msg.data[1]
                if 0 <= param_idx < 8:
                    self.state.param_values[param_idx] = value
                    # Name follows value
                    if len(msg.data) > 2:
                        name = ''.join(chr(c) for c in msg.data[2:])
                        self.state.param_names[param_idx] = name
                    self._update_display()

    def _process_mixer_message(self, msg: ReasonMessage):
        """Process a mixer message from Reason."""
        if msg.msg_type == MessageType.MIXER_NAME:
            if msg.data:
                channel = msg.data[0]
                name = ''.join(chr(c) for c in msg.data[1:])
                if 0 <= channel < 8:
                    self.state.track_names[channel] = name
                    self._update_display()

        elif msg.msg_type == MessageType.MIXER_VOLUME:
            if len(msg.data) >= 2:
                channel = msg.data[0]
                value = msg.data[1]
                if 0 <= channel < 8:
                    self.state.track_volumes[channel] = value

        elif msg.msg_type == MessageType.MIXER_MUTE:
            if len(msg.data) >= 2:
                channel = msg.data[0]
                muted = msg.data[1] > 0
                if 0 <= channel < 8:
                    self.state.track_mutes[channel] = muted
                    self._update_button_leds()

    # =========================================================================
    # DISPLAY AND LED UPDATES
    # =========================================================================

    def _update_display(self):
        """Update Push LCD based on current mode and state."""
        if not self.display:
            return

        if self.state.current_mode == 'device':
            self.display.set_segments(1, ["OpenPush", self.state.device_name, "", "Device"])
            self.display.set_fields(2, self.state.param_names)
            # Show param values as bars or numbers
            values = [f"{v:3d}" for v in self.state.param_values]
            self.display.set_fields(3, values)
            self.display.set_segments(4, ["<-Params", "", "", "Params->"])

        elif self.state.current_mode == 'mixer':
            self.display.set_segments(1, ["OpenPush", "Mixer", "", f"{self.state.tempo:.1f} BPM"])
            self.display.set_fields(2, self.state.track_names)
            volumes = [f"{v:3d}" for v in self.state.track_volumes]
            self.display.set_fields(3, volumes)
            self.display.set_segments(4, ["<-Tracks", "Mute", "Solo", "Tracks->"])

        elif self.state.current_mode == 'transport':
            status = "Playing" if self.state.playing else "Stopped"
            rec = " [REC]" if self.state.recording else ""
            loop = " [LOOP]" if self.state.looping else ""
            self.display.set_segments(1, ["OpenPush", "Transport", "", f"{self.state.tempo:.1f} BPM"])
            self.display.set_segments(2, [status + rec + loop, "", "", ""])
            self.display.set_segments(3, ["", "", "", ""])
            self.display.set_segments(4, ["Play", "Stop", "Record", "Loop"])

    def _update_transport_leds(self):
        """Update transport button LEDs."""
        self.push.set_button_color('play', 'green' if self.state.playing else 'dim_white')
        self.push.set_button_color('record', 'red' if self.state.recording else 'dim_white')

    def _update_button_leds(self):
        """Update all button LEDs based on state."""
        self._update_transport_leds()

        # Mode buttons
        self.push.set_button_color('device', 'blue' if self.state.current_mode == 'device' else 'dim_white')
        self.push.set_button_color('volume', 'blue' if self.state.current_mode == 'mixer' else 'dim_white')
        self.push.set_button_color('track', 'blue' if self.state.current_mode == 'transport' else 'dim_white')

    # =========================================================================
    # MAIN LOOP
    # =========================================================================

    def run(self):
        """
        Run the bridge main loop.

        Blocks until stopped (Ctrl+C or disconnect).
        """
        if not self._connected:
            if not self.connect():
                return

        self._running = True
        self._update_display()
        self._update_button_leds()

        print("Bridge running. Press Ctrl+C to stop.")

        try:
            for msg in self.push.iter_messages():
                if not self._running:
                    break
                self.handle_push_message(msg)
        except KeyboardInterrupt:
            print("\nStopping bridge...")
        finally:
            self.disconnect()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
        return False
