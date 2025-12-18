#!/usr/bin/env python3
"""
Reason Bridge Demo
==================

Demonstrates the virtual MIDI port architecture without
requiring Push hardware connected.

This creates the three virtual MIDI ports that Reason will see.
You can configure these in Reason's Control Surfaces settings.

Usage:
    python3 -m open_push.reason.demo
"""

import sys
import time


def demo_ports_only():
    """
    Demo: Create virtual ports without Push hardware.

    This is useful for testing Reason integration without Push.
    """
    # Add parent to path for imports
    sys.path.insert(0, 'src')

    from open_push.reason.ports import ReasonPortManager

    print()
    print("=" * 60)
    print("  OpenPush Reason Bridge - Virtual Ports Demo")
    print("=" * 60)
    print()

    manager = ReasonPortManager()

    if not manager.open_all():
        print("Failed to create virtual ports!")
        return

    print("Virtual MIDI ports created successfully!")
    print()
    print("Port names:")
    print(f"  - {manager.transport.in_name} / {manager.transport.out_name}")
    print(f"  - {manager.devices.in_name} / {manager.devices.out_name}")
    print(f"  - {manager.mixer.in_name} / {manager.mixer.out_name}")
    print()
    print("To use with Reason:")
    print("  1. Open Reason > Preferences > Control Surfaces")
    print("  2. Click 'Add' for each port")
    print("  3. Select 'OpenPush Transport/Devices/Mixer' as the manufacturer")
    print("  4. Assign each surface's MIDI In/Out to the matching OpenPush ports")
    print("  4. The Lua codecs need to be installed in Reason's Remote folder")
    print()
    print("Press Ctrl+C to close ports and exit...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nClosing ports...")

    manager.close_all()
    print("Done!")


def demo_message_protocol():
    """Demo: Show the message protocol structure."""
    sys.path.insert(0, 'src')

    from open_push.reason.protocol import (
        MessageType,
        PortID,
        build_transport_message,
        build_encoder_message,
        build_mixer_message,
    )

    print()
    print("=" * 60)
    print("  OpenPush Protocol Message Examples")
    print("=" * 60)
    print()

    # Transport play message
    msg = build_transport_message(MessageType.TRANSPORT_PLAY, 1)
    print(f"Transport PLAY message:")
    print(f"  SysEx data: {[hex(b) for b in msg.to_sysex()]}")
    print()

    # Encoder turn message
    msg = build_encoder_message(encoder=3, delta=5)
    print(f"Encoder 4 turn +5 message:")
    print(f"  SysEx data: {[hex(b) for b in msg.to_sysex()]}")
    print()

    # Mixer volume message
    msg = build_mixer_message(MessageType.MIXER_VOLUME, channel=0, value=100)
    print(f"Mixer channel 1 volume message:")
    print(f"  SysEx data: {[hex(b) for b in msg.to_sysex()]}")
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='OpenPush Reason Bridge Demo')
    parser.add_argument('--protocol', action='store_true',
                        help='Show protocol message examples')
    args = parser.parse_args()

    if args.protocol:
        demo_message_protocol()
    else:
        demo_ports_only()
