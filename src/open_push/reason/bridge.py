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
    metronome: bool = False
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
        # Transport buttons - send CC to Reason via transport port
        if button == 'play':
            self._send_transport_cc(0x50, 127)  # CC 80
        elif button == 'stop':
            self._send_transport_cc(0x51, 127)  # CC 81
        elif button == 'record':
            self._send_transport_cc(0x52, 127)  # CC 82
        elif button == 'tap_tempo':
            # Tap tempo doubles as rewind
            self._send_transport_cc(0x53, 127)  # CC 83 - Rewind
        elif button == 'metronome':
            self._send_transport_cc(0x57, 127)  # CC 87 - Metronome toggle
        elif button == 'fixed_length':
            # Use fixed length as loop toggle
            self._send_transport_cc(0x55, 127)  # CC 85 - Loop

        # Navigation arrows - send to transport for Reason navigation
        elif button == 'up':
            self._send_transport_cc(0x60, 127)
        elif button == 'down':
            self._send_transport_cc(0x61, 127)
        elif button == 'left':
            self._send_transport_cc(0x62, 127)
        elif button == 'right':
            self._send_transport_cc(0x63, 127)

        # Mode selection (local to bridge, not sent to Reason)
        elif button == 'device':
            self._set_mode('device')
        elif button == 'volume':
            self._set_mode('mixer')
        elif button == 'pan_send':
            self._set_mode('mixer_pan')
        elif button == 'track':
            self._set_mode('transport')

        # Octave shift (for note mode)
        elif button == 'octave_up':
            self._handle_octave_shift(+1)
        elif button == 'octave_down':
            self._handle_octave_shift(-1)

        # Upper row buttons (above display) - route based on mode
        elif button.startswith('upper_'):
            btn_num = int(button.split('_')[1]) - 1  # 0-7
            if self.state.current_mode == 'device':
                self._send_device_cc(0x66 + btn_num, 127)
            elif self.state.current_mode in ('mixer', 'mixer_pan'):
                # Could be track select in mixer mode
                self._send_mixer_cc(0x20 + btn_num, 127)

        # Lower row buttons (below display)
        elif button.startswith('lower_'):
            btn_num = int(button.split('_')[1]) - 1  # 0-7
            if self.state.current_mode == 'device':
                self._send_device_cc(0x14 + btn_num, 127)
            elif self.state.current_mode == 'mixer':
                # Mute buttons
                self._send_mixer_cc(0x40 + btn_num, 127)
            elif self.state.current_mode == 'mixer_pan':
                # Solo buttons
                self._send_mixer_cc(0x48 + btn_num, 127)

    def _send_device_cc(self, cc: int, value: int):
        """Send a CC message to Reason via devices port."""
        import mido
        msg = mido.Message('control_change', channel=15, control=cc, value=value)
        self.ports.devices.send(msg)

    def _send_mixer_cc(self, cc: int, value: int):
        """Send a CC message to Reason via mixer port."""
        import mido
        msg = mido.Message('control_change', channel=15, control=cc, value=value)
        self.ports.mixer.send(msg)

    def _send_transport_cc(self, cc: int, value: int):
        """Send a CC message to Reason via transport port."""
        import mido
        msg = mido.Message('control_change', channel=15, control=cc, value=value)
        self.ports.transport.send(msg)

    def _handle_octave_shift(self, direction: int):
        """Handle octave up/down for note mode."""
        # This will be used when we implement note modes
        pass

    def _handle_encoder(self, encoder: int, delta: int):
        """Handle encoder turn - routes to appropriate port based on mode."""
        import mido
        # Encode delta: 64 = no change, >64 = increase, <64 = decrease
        value = max(0, min(127, delta + 64))

        if self.state.current_mode == 'device':
            # Send to Devices port - CC 0x47-0x4E for encoders 1-8
            cc = 0x47 + encoder
            msg = mido.Message('control_change', channel=15, control=cc, value=value)
            self.ports.devices.send(msg)

        elif self.state.current_mode == 'mixer':
            # Send volume change to Mixer port - CC 0x30-0x37
            cc = 0x30 + encoder
            msg = mido.Message('control_change', channel=15, control=cc, value=value)
            self.ports.mixer.send(msg)

        elif self.state.current_mode == 'mixer_pan':
            # Send pan change to Mixer port - CC 0x38-0x3F
            cc = 0x38 + encoder
            msg = mido.Message('control_change', channel=15, control=cc, value=value)
            self.ports.mixer.send(msg)

    def _handle_tempo_encoder(self, delta: int):
        """Handle tempo encoder turn - sends to Reason for tempo adjustment."""
        import mido
        # Send relative CC value (64 = no change, >64 = increase, <64 = decrease)
        value = max(0, min(127, delta + 64))
        msg = mido.Message('control_change', channel=15, control=0x16, value=value)
        self.ports.transport.send(msg)

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
        elif msg.type == 'control_change':
            # Handle CC feedback from Reason for LED states
            self._process_transport_cc(msg.control, msg.value)

    def _handle_device_from_reason(self, msg: mido.Message):
        """Handle message from Reason on devices port."""
        if msg.type == 'sysex':
            parsed = ReasonMessage.from_sysex(list(msg.data))
            if parsed:
                self._process_device_message(parsed)
        elif msg.type == 'control_change':
            # Handle CC feedback from Reason for encoder values
            self._process_device_cc(msg.control, msg.value)

    def _process_device_cc(self, cc: int, value: int):
        """Process device CC feedback from Reason."""
        # Encoder value feedback (CC 0x47-0x4E)
        if 0x47 <= cc <= 0x4E:
            encoder = cc - 0x47
            if 0 <= encoder < 8:
                self.state.param_values[encoder] = value
                self._update_display()
        # Upper button feedback (CC 0x66-0x6D)
        elif 0x66 <= cc <= 0x6D:
            button = cc - 0x66
            # Update button LED on Push
            button_name = f'upper_{button + 1}'
            self.push.set_button_color(button_name, 'blue' if value > 0 else 'dim_white')
        # Lower button feedback (CC 0x14-0x1B)
        elif 0x14 <= cc <= 0x1B:
            button = cc - 0x14
            button_name = f'lower_{button + 1}'
            self.push.set_button_color(button_name, 'blue' if value > 0 else 'dim_white')

    def _handle_mixer_from_reason(self, msg: mido.Message):
        """Handle message from Reason on mixer port."""
        if msg.type == 'sysex':
            parsed = ReasonMessage.from_sysex(list(msg.data))
            if parsed:
                self._process_mixer_message(parsed)
        elif msg.type == 'control_change':
            self._process_mixer_cc(msg.control, msg.value)

    def _process_mixer_cc(self, cc: int, value: int):
        """Process mixer CC feedback from Reason."""
        # Volume feedback (CC 0x30-0x37)
        if 0x30 <= cc <= 0x37:
            channel = cc - 0x30
            if 0 <= channel < 8:
                self.state.track_volumes[channel] = value
                self._update_display()
        # Pan feedback (CC 0x38-0x3F)
        elif 0x38 <= cc <= 0x3F:
            channel = cc - 0x38
            if 0 <= channel < 8:
                self.state.track_pans[channel] = value
                self._update_display()
        # Mute feedback (CC 0x40-0x47)
        elif 0x40 <= cc <= 0x47:
            channel = cc - 0x40
            if 0 <= channel < 8:
                self.state.track_mutes[channel] = value > 0
                # Update lower button LED for mute state
                button_name = f'lower_{channel + 1}'
                self.push.set_button_color(button_name, 'orange' if value > 0 else 'dim_white')
        # Solo feedback (CC 0x48-0x4F)
        elif 0x48 <= cc <= 0x4F:
            channel = cc - 0x48
            if 0 <= channel < 8:
                self.state.track_solos[channel] = value > 0
                # Update lower button LED for solo state (when in pan mode)
                if self.state.current_mode == 'mixer_pan':
                    button_name = f'lower_{channel + 1}'
                    self.push.set_button_color(button_name, 'yellow' if value > 0 else 'dim_white')
        # Select feedback (CC 0x20-0x27)
        elif 0x20 <= cc <= 0x27:
            channel = cc - 0x20
            # Update upper button LED for selected track
            for i in range(8):
                button_name = f'upper_{i + 1}'
                is_selected = (i == channel and value > 0)
                self.push.set_button_color(button_name, 'green' if is_selected else 'dim_white')

    def _process_transport_cc(self, cc: int, value: int):
        """Process transport CC feedback from Reason for LED states."""
        # Map CC numbers to transport state
        if cc == 0x50:  # Play
            self.state.playing = value > 0
            self._update_transport_leds()
        elif cc == 0x51:  # Stop - no LED state, just confirmation
            pass
        elif cc == 0x52:  # Record
            self.state.recording = value > 0
            self._update_transport_leds()
        elif cc == 0x55:  # Loop
            self.state.looping = value > 0
            self._update_transport_leds()
        elif cc == 0x57:  # Metronome
            self.state.metronome = value > 0
            self._update_transport_leds()
        elif cc == 0x16:  # Tempo value feedback
            # Tempo comes as a scaled value
            self.state.tempo = 60 + (value * 1.5)  # Rough mapping
            self._update_display()

    def _process_transport_message(self, msg: ReasonMessage):
        """Process a transport SysEx message from Reason."""
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
            self.display.set_segments(1, ["OpenPush", "Mixer Vol", "", f"{self.state.tempo:.1f} BPM"])
            self.display.set_fields(2, self.state.track_names)
            volumes = [f"{v:3d}" for v in self.state.track_volumes]
            self.display.set_fields(3, volumes)
            self.display.set_segments(4, ["<-Tracks", "Mute", "Pan/Send", "Tracks->"])

        elif self.state.current_mode == 'mixer_pan':
            self.display.set_segments(1, ["OpenPush", "Mixer Pan", "", f"{self.state.tempo:.1f} BPM"])
            self.display.set_fields(2, self.state.track_names)
            # Show pan as L/C/R indicator
            pans = []
            for p in self.state.track_pans:
                if p < 60:
                    pans.append(f"L{64-p:2d}")
                elif p > 68:
                    pans.append(f"R{p-64:2d}")
                else:
                    pans.append(" C ")
            self.display.set_fields(3, pans)
            self.display.set_segments(4, ["<-Tracks", "Solo", "Volume", "Tracks->"])

        elif self.state.current_mode == 'transport':
            status = "Playing" if self.state.playing else "Stopped"
            rec = "[REC]" if self.state.recording else ""
            loop = "[LOOP]" if self.state.looping else ""
            metro = "[METRO]" if self.state.metronome else ""
            self.display.set_segments(1, ["OpenPush", "Transport", "", f"{self.state.tempo:.1f} BPM"])
            self.display.set_segments(2, [status, rec, loop, metro])
            self.display.set_segments(3, ["", "", "", ""])
            self.display.set_segments(4, ["Play/Stop", "Record", "Loop", "Metronome"])

    def _update_transport_leds(self):
        """Update transport button LEDs."""
        self.push.set_button_color('play', 'green' if self.state.playing else 'dim_white')
        self.push.set_button_color('record', 'red' if self.state.recording else 'dim_white')
        self.push.set_button_color('fixed_length', 'blue' if self.state.looping else 'dim_white')
        self.push.set_button_color('metronome', 'cyan' if self.state.metronome else 'dim_white')

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
