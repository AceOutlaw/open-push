"""
Reason MIDI Port Management
===========================

Creates and manages the three separate virtual MIDI ports
used for Reason Remote communication:
- OpenPush Transport: Play, stop, record, tempo, loop markers
- OpenPush Devices: Encoder parameter control
- OpenPush Mixer: Volume, pan, mute, solo

Each port appears as a separate control surface in Reason,
avoiding the reliability issues of shared ports.
"""

import mido
from typing import Optional, Tuple, Callable
from dataclasses import dataclass


@dataclass
class PortConfig:
    """Configuration for a virtual MIDI port."""
    name: str
    description: str
    in_name: str = ""
    out_name: str = ""

    def __post_init__(self):
        if not self.in_name:
            self.in_name = f"{self.name} In"
        if not self.out_name:
            self.out_name = f"{self.name} Out"


# Default port names (different from PusheR to avoid confusion)
PORT_TRANSPORT = PortConfig(
    name="OpenPush Transport",
    description="Transport controls (play, stop, record, tempo, loop)"
)

PORT_DEVICES = PortConfig(
    name="OpenPush Devices",
    description="Encoder parameter control for devices"
)

PORT_MIXER = PortConfig(
    name="OpenPush Mixer",
    description="Mixer controls (volume, pan, mute, solo)"
)


class VirtualMIDIPort:
    """
    A bidirectional virtual MIDI port for Reason communication.

    Creates output (Reason input) and input (Reason output) ports.
    Reason will see this as a control surface it can communicate with.
    """

    def __init__(self, config: PortConfig):
        """
        Initialize virtual port (not yet opened).

        Args:
            config: Port configuration with name and description
        """
        self.config = config
        self._output: Optional[mido.ports.BaseOutput] = None
        self._input: Optional[mido.ports.BaseInput] = None
        self._open = False
        self._message_callback: Optional[Callable] = None

    @property
    def name(self) -> str:
        """Get port name."""
        return self.config.name

    @property
    def in_name(self) -> str:
        """Get Reason-facing input port name."""
        return self.config.in_name

    @property
    def out_name(self) -> str:
        """Get Reason-facing output port name."""
        return self.config.out_name

    @property
    def is_open(self) -> bool:
        """Check if port is open."""
        return self._open

    def open(self) -> bool:
        """
        Open the virtual MIDI port.

        Creates virtual input and output ports that Reason can connect to.

        Returns:
            True if successful
        """
        if self._open:
            return True

        try:
            # Create virtual output (we send, Reason receives)
            self._output = mido.open_output(self.config.in_name, virtual=True)

            # Create virtual input (Reason sends, we receive)
            self._input = mido.open_input(
                self.config.out_name,
                virtual=True,
                callback=self._on_message
            )

            self._open = True
            return True

        except Exception as e:
            print(f"Error opening virtual port '{self.config.name}': {e}")
            self.close()
            return False

    def close(self):
        """Close the virtual MIDI port."""
        if self._output:
            try:
                self._output.close()
            except Exception:
                pass
            self._output = None

        if self._input:
            try:
                self._input.close()
            except Exception:
                pass
            self._input = None

        self._open = False

    def send(self, message: mido.Message):
        """
        Send a MIDI message to Reason.

        Args:
            message: mido Message to send
        """
        if self._output and self._open:
            self._output.send(message)

    def send_sysex(self, data: list):
        """
        Send a SysEx message to Reason.

        Args:
            data: SysEx data bytes (without F0/F7 framing)
        """
        msg = mido.Message('sysex', data=data)
        self.send(msg)

    def set_callback(self, callback: Callable[[mido.Message], None]):
        """
        Set callback for incoming messages from Reason.

        Args:
            callback: Function taking a mido.Message
        """
        self._message_callback = callback

    def _on_message(self, message: mido.Message):
        """Internal callback for incoming messages."""
        if self._message_callback:
            self._message_callback(message)

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False


class ReasonPortManager:
    """
    Manages all three virtual MIDI ports for Reason communication.

    Usage:
        manager = ReasonPortManager()
        if manager.open_all():
            # Ports are ready
            manager.transport.send(...)
            manager.devices.send(...)
            manager.mixer.send(...)
        manager.close_all()
    """

    def __init__(
        self,
        transport_name: str = None,
        devices_name: str = None,
        mixer_name: str = None
    ):
        """
        Initialize port manager.

        Args:
            transport_name: Custom name for transport port
            devices_name: Custom name for devices port
            mixer_name: Custom name for mixer port
        """
        # Allow custom names or use defaults
        transport_config = PortConfig(
            name=transport_name or PORT_TRANSPORT.name,
            description=PORT_TRANSPORT.description
        )
        devices_config = PortConfig(
            name=devices_name or PORT_DEVICES.name,
            description=PORT_DEVICES.description
        )
        mixer_config = PortConfig(
            name=mixer_name or PORT_MIXER.name,
            description=PORT_MIXER.description
        )

        self.transport = VirtualMIDIPort(transport_config)
        self.devices = VirtualMIDIPort(devices_config)
        self.mixer = VirtualMIDIPort(mixer_config)

        self._all_ports = [self.transport, self.devices, self.mixer]

    def open_all(self) -> bool:
        """
        Open all virtual ports.

        Returns:
            True if all ports opened successfully
        """
        success = True
        for port in self._all_ports:
            if not port.open():
                success = False
                print(f"Failed to open port: {port.name}")

        if success:
            print("Virtual MIDI ports created:")
            for port in self._all_ports:
                print(f"  - {port.in_name} / {port.out_name}")
            print()
            print("In Reason, add these as separate Remote devices:")
            print("  Preferences > Control Surfaces > Add")
            print()

        return success

    def close_all(self):
        """Close all virtual ports."""
        for port in self._all_ports:
            port.close()

    def set_transport_callback(self, callback: Callable[[mido.Message], None]):
        """Set callback for transport port messages."""
        self.transport.set_callback(callback)

    def set_devices_callback(self, callback: Callable[[mido.Message], None]):
        """Set callback for devices port messages."""
        self.devices.set_callback(callback)

    def set_mixer_callback(self, callback: Callable[[mido.Message], None]):
        """Set callback for mixer port messages."""
        self.mixer.set_callback(callback)

    @property
    def is_open(self) -> bool:
        """Check if all ports are open."""
        return all(port.is_open for port in self._all_ports)

    def __enter__(self):
        self.open_all()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_all()
        return False
