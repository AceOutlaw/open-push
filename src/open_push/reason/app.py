#!/usr/bin/env python3
"""
OpenPush - Bridge application for Ableton Push with Reason
Command-line version
"""

import mido
import threading
import time
import sys
import os

# Ensure we can import core modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from open_push.music.layout import IsomorphicLayout
from open_push.music.scales import SCALES, SCALE_NAMES, is_in_scale, is_root_note
from open_push.core.constants import COLORS, BUTTON_CC, note_name

# Push 1 Constants
SYSEX_HEADER = [0x47, 0x7F, 0x15]

# LCD line addresses and segment formatting
LCD_LINES = {1: 0x18, 2: 0x19, 3: 0x1A, 4: 0x1B}
CHARS_PER_SEGMENT = 17  # LCD has 4 segments of 17 chars with physical gaps

# Pad colors (velocity values)
COLOR_OFF = 0
COLOR_WHITE = 3
COLOR_RED = 5
COLOR_ORANGE = 9
COLOR_YELLOW = 13
COLOR_GREEN = 21
COLOR_CYAN = 33
COLOR_BLUE = 45
COLOR_PURPLE = 49
COLOR_PINK = 57
COLOR_WHITE_DIM = 1
COLOR_OFF = 0

# Button CCs - Complete mapping
BUTTONS = {
    # Navigation
    'up': 46, 'down': 47, 'left': 44, 'right': 45,

    # Octave/Transpose
    'octave_up': 55, 'octave_down': 54,

    # Mode buttons
    'note': 50, 'session': 51, 'scale': 58, 'accent': 57,

    # Transport
    'play': 85, 'record': 86, 'stop': 29,

    # Track controls (upper row)
    'volume': 114, 'pan_send': 115, 'track': 112, 'clip': 113,
    'device': 110, 'browse': 111,
}

# Reverse lookup
CC_TO_BUTTON = {v: k for k, v in BUTTONS.items()}

# Transport CCs to forward to Reason
TRANSPORT_CCS = {85, 86}  # play, record


class OpenPushApp:
    def __init__(self):
        # MIDI ports
        self.push_in_port = None
        self.push_out_port = None
        self.remote_in_ports = {}
        self.remote_out_ports = {}

        # Running state
        self.running = False
        self.midi_thread = None

        # Current mode and state
        self.current_mode = 'note'  # note, device, mixer, transport
        self.playing = False
        self.recording = False
        self.device_name = "No Device"

        # Isomorphic Controller State
        self.layout = IsomorphicLayout()
        self.scale_index = 0
        self.root_note = 0  # C
        self.accent_mode = False
        self.velocity_curve = 1.0
        self.velocity_min = 40
        self.velocity_max = 127
        self.active_notes = {}  # pad -> midi_note

        # Initialize layout
        self.layout.set_scale(self.root_note, SCALE_NAMES[self.scale_index])
        self.layout.set_in_key_mode(True) # Default to in-key

    def create_virtual_ports(self):
        """Create virtual MIDI ports for Reason to connect to."""
        port_names = ["OpenPush Transport", "OpenPush Devices", "OpenPush Mixer"]

        print("Creating virtual MIDI ports...")
        for name in port_names:
            try:
                in_port = mido.open_output(f"{name} In", virtual=True)
                self.remote_out_ports[name] = in_port
                print(f"  Created: {name} In")

                out_port = mido.open_input(f"{name} Out", virtual=True)
                self.remote_in_ports[name] = out_port
                print(f"  Created: {name} Out")

            except Exception as e:
                print(f"  Error creating {name}: {e}")

    def list_ports(self):
        """List available MIDI ports."""
        print("\n=== Available MIDI Ports ===")

        print("\nInput ports:")
        for i, name in enumerate(mido.get_input_names()):
            if "OpenPush" not in name:
                print(f"  [{i}] {name}")

        print("\nOutput ports:")
        for i, name in enumerate(mido.get_output_names()):
            if "OpenPush" not in name:
                print(f"  [{i}] {name}")

    def find_push_ports(self):
        """Auto-detect Push ports."""
        in_ports = [p for p in mido.get_input_names() if "Push" in p and "User" in p and "OpenPush" not in p]
        out_ports = [p for p in mido.get_output_names() if "Push" in p and "User" in p and "OpenPush" not in p]
        return in_ports[0] if in_ports else None, out_ports[0] if out_ports else None

    def connect_push(self, in_name=None, out_name=None):
        """Connect to Push hardware."""
        if not in_name or not out_name:
            in_name, out_name = self.find_push_ports()

        if not in_name or not out_name:
            print("Error: Could not find Push ports")
            return False

        try:
            print(f"\nConnecting to Push...")
            print(f"  IN:  {in_name}")
            print(f"  OUT: {out_name}")

            self.push_in_port = mido.open_input(in_name)
            self.push_out_port = mido.open_output(out_name)

            # Initialize Push
            self._init_push()
            print("  Push initialized!")

            return True

        except Exception as e:
            print(f"Error connecting to Push: {e}")
            return False

    def _init_push(self):
        """Initialize Push - put in User mode and set up display."""
        if not self.push_out_port:
            return

        # Enter User mode
        user_mode = mido.Message("sysex", data=SYSEX_HEADER + [0x62, 0x00, 0x01, 0x01])
        self.push_out_port.send(user_mode)
        time.sleep(0.1)

        # Set up LCD display (4 segments of 17 chars each with gaps)
        self._set_lcd_segments(1, "OpenPush", "Reason", "Bridge", "v0.3")
        self._set_lcd_segments(2, "", "", "", "")
        self._set_lcd_segments(3, "Transport", "Devices", "Mixer", "Scale")
        self._set_lcd_segments(4, "Ready", "Ready", "Ready", "Ready")

        # Light up the pad grid
        self._update_grid()

        # Light up mode buttons (dim = available, bright = active)
        self._set_button_led(BUTTONS['play'], 1)       # Play - dim (not playing)
        self._set_button_led(BUTTONS['record'], 1)     # Record - dim
        self._set_button_led(BUTTONS['volume'], 1)     # Volume/Mixer - dim
        self._set_button_led(BUTTONS['device'], 1)     # Device - dim
        self._set_button_led(BUTTONS['note'], 4)       # Note - bright (default mode)
        self._set_button_led(BUTTONS['scale'], 1)      # Scale - dim

    def _set_lcd_segments(self, line, seg0="", seg1="", seg2="", seg3=""):
        """
        Set text on one LCD line using 4 segments of 17 chars each.

        CRITICAL: Push 1 LCD has 4 physical segments with gaps between them.
        Each segment is 17 characters. Text must be formatted per-segment
        to display correctly.

        Args:
            line: Line number 1-4
            seg0-seg3: Text for each segment (max 17 chars, auto-centered)
        """
        if not self.push_out_port:
            return

        # Center each segment to 17 chars
        parts = [seg0, seg1, seg2, seg3]
        text = ""
        for part in parts:
            text += part[:CHARS_PER_SEGMENT].center(CHARS_PER_SEGMENT)

        line_addr = LCD_LINES[line]
        # SysEx format: header + line_addr + offset(0x00) + length(0x45=69) + null + text
        data = SYSEX_HEADER + [line_addr, 0x00, 0x45, 0x00]
        data.extend([ord(c) for c in text])
        msg = mido.Message("sysex", data=data)
        self.push_out_port.send(msg)

    def _update_grid(self):
        """Update pad grid based on current mode."""
        if not self.push_out_port:
            return

        if self.current_mode == 'note':
            # Isomorphic Layout
            for row in range(8):
                for col in range(8):
                    info = self.layout.get_pad_info(row, col)
                    note = 36 + (row * 8) + col
                    
                    if info['is_root']:
                        color = COLOR_BLUE
                    elif info['is_in_scale']:
                        color = COLOR_WHITE
                    else:
                        color = COLOR_OFF if self.layout.in_key_mode else COLOR_WHITE_DIM
                    
                    self._set_pad_color(note, color)
                    
        elif self.current_mode == 'scale':
            # Scale Selection Mode
            # Clear grid first
            for note in range(36, 100):
                self._set_pad_color(note, COLOR_OFF)
                
            # Root selection (bottom rows)
            for row in range(4, 8):
                for col in range(8):
                    # Not fully implemented UI map, simplified for now
                    # Just replicate logic from bridge.py if needed, 
                    # but for now let's keep it simple or implement fully.
                    pass
            
            # Simple UI for now:
            # Row 0: C D E F G A B
            roots = [0, 2, 4, 5, 7, 9, 11] # C D E F G A B
            for i, root_val in enumerate(roots):
                color = COLOR_GREEN if self.root_note == root_val else COLOR_WHITE_DIM
                self._set_pad_color(36 + i, color)

    def _set_pad_color(self, note, color):
        """Set a pad's color via note-on velocity."""
        if not self.push_out_port:
            return

        # Note on channel 1 with velocity = color
        msg = mido.Message("note_on", note=note, velocity=color, channel=0)
        self.push_out_port.send(msg)

    def _set_button_led(self, cc, value):
        """Set a button LED state."""
        if not self.push_out_port:
            return

        msg = mido.Message("control_change", control=cc, value=value, channel=0)
        self.push_out_port.send(msg)

    def start(self):
        """Start MIDI routing."""
        self.running = True
        self.midi_thread = threading.Thread(target=self._midi_loop, daemon=True)
        self.midi_thread.start()
        print("\nMIDI routing started")

    def stop(self):
        """Stop MIDI routing."""
        self.running = False
        if self.midi_thread:
            self.midi_thread.join(timeout=1.0)
        print("MIDI routing stopped")

    def _midi_loop(self):
        """Main MIDI routing loop."""
        while self.running:
            if self.push_in_port:
                for msg in self.push_in_port.iter_pending():
                    self._handle_push_message(msg)

            for name, port in self.remote_in_ports.items():
                for msg in port.iter_pending():
                    self._handle_reason_message(name, msg)

            time.sleep(0.001)
            
    def apply_velocity_curve(self, velocity):
        """Apply velocity curve."""
        if self.accent_mode:
            return 127
            
        # Normalize
        norm = (velocity - 1) / 126.0
        curved = pow(norm, self.velocity_curve)
        
        # Scale
        val_range = self.velocity_max - self.velocity_min
        out = int(self.velocity_min + (curved * val_range))
        return max(1, min(127, out))

    def _handle_push_message(self, msg):
        """Handle MIDI message from Push, route to Reason."""
        if msg.type == 'control_change':
            self._handle_button(msg)
        elif msg.type == 'note_on' or msg.type == 'note_off':
            self._handle_pad(msg)
        elif msg.type == 'pitchwheel':
             # Touch Strip -> Devices Port (as Pitch Bend)
             if "OpenPush Devices" in self.remote_out_ports:
                 # Forward directly (Push sends pitchwheel, Reason expects pitchwheel)
                 self.remote_out_ports["OpenPush Devices"].send(msg)
        else:
            # print(f"Push: {msg}")
            pass

    def _handle_button(self, msg):
        """Handle button press/release."""
        cc = msg.control
        value = msg.value
        button_name = CC_TO_BUTTON.get(cc, f"CC{cc}")

        if value > 0:  # Button pressed
            print(f"Button: {button_name} (CC {cc}) value={value}")

            # Transport controls
            if cc == BUTTONS['play']:
                if self.playing:
                    stop_msg = mido.Message('control_change', channel=0, control=BUTTONS['stop'], value=127)
                    self._send_to_transport(stop_msg)
                else:
                    self._send_to_transport(msg)

            elif cc == BUTTONS['record']:
                self._send_to_transport(msg)
                
            # Octave Shift
            elif cc == BUTTONS['octave_up']:
                self.layout.shift_octave(1)
                self._update_grid()
                self._update_display()
            elif cc == BUTTONS['octave_down']:
                self.layout.shift_octave(-1)
                self._update_grid()
                self._update_display()
                
            # Accent
            elif cc == BUTTONS['accent']:
                self.accent_mode = not self.accent_mode
                self._set_button_led(BUTTONS['accent'], 4 if self.accent_mode else 1)
                self._update_display()
                
            # Mode switching
            elif cc == BUTTONS['volume']:
                self._set_mode('mixer')
            elif cc == BUTTONS['device']:
                self._set_mode('device')
            elif cc == BUTTONS['note']:
                self._set_mode('note')
            elif cc == BUTTONS['scale']:
                # Toggle scale mode
                if self.current_mode == 'scale':
                    self._set_mode('note')
                else:
                    self._set_mode('scale')
            else:
                pass
                # print(f"  (unhandled button)")
        else:
            # Button released
            pass

    def _handle_pad(self, msg):
        """Handle pad press/release."""
        if self.current_mode == 'note':
            # Isomorphic playing
            if msg.type == 'note_on' and msg.velocity > 0:
                # Calculate note from layout
                midi_note = self.layout.get_midi_note(msg.note)
                
                # Apply velocity
                vel = self.apply_velocity_curve(msg.velocity)
                
                # Store active note
                self.active_notes[msg.note] = midi_note
                
                # Send note on
                out_msg = mido.Message('note_on', note=midi_note, velocity=vel, channel=15)
                if "OpenPush Devices" in self.remote_out_ports:
                    self.remote_out_ports["OpenPush Devices"].send(out_msg)
                    
                # Flash pad
                self._set_pad_color(msg.note, COLOR_GREEN)
                
            elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                # Note off
                if msg.note in self.active_notes:
                    midi_note = self.active_notes.pop(msg.note)
                    out_msg = mido.Message('note_off', note=midi_note, velocity=0, channel=15)
                    if "OpenPush Devices" in self.remote_out_ports:
                        self.remote_out_ports["OpenPush Devices"].send(out_msg)
                        
                # Restore grid color
                self._update_grid()

    def _set_mode(self, mode):
        """Switch to a different mode and update display."""
        self.current_mode = mode
        print(f"Mode: {mode}")

        # Update button LEDs
        self._set_button_led(BUTTONS['volume'], 4 if mode == 'mixer' else 1)
        self._set_button_led(BUTTONS['device'], 4 if mode == 'device' else 1)
        self._set_button_led(BUTTONS['note'], 4 if mode == 'note' else 1)
        self._set_button_led(BUTTONS['scale'], 4 if mode == 'scale' else 1)

        # Update display
        self._update_display()
        self._update_grid()

    def _update_display(self):
        """Update LCD based on current mode."""
        mode_display = self.current_mode.capitalize()
        status = "Playing" if self.playing else "Stopped"
        
        if self.current_mode == 'note':
            root_name = note_name(self.layout.root_note) # Base root note
            scale_name = self.layout.scale_name
            octave = self.layout.get_octave()
            accent = "ON" if self.accent_mode else "OFF"
            
            self._set_lcd_segments(1, "OpenPush", mode_display, f"{root_name}", f"{scale_name}")
            self._set_lcd_segments(2, f"Octave: {octave}", f"Accent: {accent}", "", "")
            self._set_lcd_segments(3, "Transport", "Devices", "Mixer", "Scale")
            self._set_lcd_segments(4, "Volume", "Device", "Note", "Settings")
            
        else:
            self._set_lcd_segments(1, "OpenPush", mode_display, self.device_name, "v0.3")
            self._set_lcd_segments(2, status, "", "", "")
            self._set_lcd_segments(3, "Transport", "Devices", "Mixer", "Scale")
            self._set_lcd_segments(4, "Volume", "Device", "Note", "")

    def _send_to_transport(self, msg):
        """Send message to Reason Transport port with channel translation."""
        if "OpenPush Transport" in self.remote_out_ports:
            try:
                # Translate Push (ch0) → Reason (ch15) - Lua codec expects 0xBF status byte
                if msg.type == 'control_change':
                    reason_msg = mido.Message('control_change',
                        channel=15,  # Reason expects channel 15
                        control=msg.control,
                        value=msg.value)
                    # print(f"  -> Transport: {reason_msg}")
                    self.remote_out_ports["OpenPush Transport"].send(reason_msg)
                else:
                    # print(f"  -> Transport: {msg}")
                    self.remote_out_ports["OpenPush Transport"].send(msg)
            except Exception as e:
                print(f"Transport send error: {e}")
        else:
            print(f"  Transport port not found!")

    def _send_to_devices(self, msg):
        """Send message to Reason Devices port with channel translation."""
        if "OpenPush Devices" in self.remote_out_ports:
            try:
                # Translate Push (ch0) → Reason (ch15)
                if msg.type == 'control_change':
                    reason_msg = mido.Message('control_change',
                        channel=15,
                        control=msg.control,
                        value=msg.value)
                    self.remote_out_ports["OpenPush Devices"].send(reason_msg)
                elif msg.type in ('note_on', 'note_off'):
                    # Notes also need channel translation for keyboard input
                    reason_msg = mido.Message(msg.type,
                        channel=15,
                        note=msg.note,
                        velocity=msg.velocity)
                    self.remote_out_ports["OpenPush Devices"].send(reason_msg)
                else:
                    self.remote_out_ports["OpenPush Devices"].send(msg)
            except Exception as e:
                print(f"Devices send error: {e}")

    def _handle_reason_message(self, port_name, msg):
        """Handle MIDI message from Reason, route to Push with channel translation."""
        # print(f"Reason ({port_name}): {msg}")

        # Update state based on Reason feedback
        if msg.type == 'control_change':
            # Transport feedback - CC numbers now match Push hardware
            if port_name == "OpenPush Transport":
                if msg.control == 85:  # Play state
                    self.playing = msg.value > 0
                    # print(f"  Play state from Reason: {self.playing}")
                    self._set_button_led(BUTTONS['play'], 4 if self.playing else 1)
                elif msg.control == 86:  # Record state
                    self.recording = msg.value > 0
                    # print(f"  Record state from Reason: {self.recording}")
                    self._set_button_led(BUTTONS['record'], 5 if self.recording else 1)

            # Forward CC messages to Push with channel translation (ch15 → ch0)
            if self.push_out_port:
                try:
                    # Translate Reason (ch15) → Push (ch0)
                    push_msg = mido.Message('control_change',
                        channel=0,  # Push expects channel 0
                        control=msg.control,
                        value=msg.value)
                    # print(f"  -> Push LED: {push_msg}")
                    self.push_out_port.send(push_msg)
                except Exception as e:
                    print(f"Push send error: {e}")

    def close(self):
        """Clean up all ports."""
        self.stop()

        # Turn off all pads before closing
        if self.push_out_port:
            for note in range(36, 100):
                self._set_pad_color(note, COLOR_OFF)

        if self.push_in_port:
            self.push_in_port.close()
        if self.push_out_port:
            self.push_out_port.close()

        for port in self.remote_in_ports.values():
            port.close()
        for port in self.remote_out_ports.values():
            port.close()

        print("All ports closed")


def main():
    print("=" * 50)
    print("  OpenPush - Push to Reason Bridge")
    print("=" * 50)

    app = OpenPushApp()
    app.create_virtual_ports()
    app.list_ports()

    if app.connect_push():
        app.start()

        print("\n" + "=" * 50)
        print("  OpenPush is running!")
        print("=" * 50)
        print("\nIn Reason, add control surfaces:")
        print("  Manufacturer: OpenPush")
        print("  MIDI Input:   OpenPush Transport In")
        print("  MIDI Output:  OpenPush Transport Out")
        print("\nCommands: 't' = test LED, 'q' = quit")
        print("Press buttons on Push to test...")

        try:
            import sys
            import select
            while True:
                # Check for keyboard input (non-blocking on Unix)
                if sys.stdin in select.select([sys.stdin], [], [], 0.1)[0]:
                    cmd = sys.stdin.readline().strip().lower()
                    if cmd == 'q':
                        break
                    elif cmd == 't':
                        print("\nTesting LED output...")
                        app._set_button_led(85, 4)  # Play bright
                        time.sleep(0.5)
                        app._set_button_led(85, 1)  # Play dim
                        print("LED test complete")
                    elif cmd == 'p':
                        # Test pad
                        print("\nTesting pad color...")
                        app._set_pad_color(36, COLOR_RED)
                        time.sleep(0.5)
                        app._set_pad_color(36, COLOR_BLUE)
                        print("Pad test complete")
        except KeyboardInterrupt:
            print("\n\nShutting down...")

    else:
        print("\nPush not connected.")
        print("Press Ctrl+C to quit...")

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n\nShutting down...")

    app.close()


if __name__ == "__main__":
    main()