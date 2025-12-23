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
from open_push.music.scales import SCALES, SCALE_NAMES, is_in_scale, is_root_note, get_scale_display_name
from open_push.core.constants import COLORS, BUTTON_CC, note_name
from open_push.reason.protocol import ReasonMessage, MessageType

# Root note names for display
ROOT_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

# Chromatic layout for root selection buttons
# Push 1: Upper row (CC 20-27) closer to LCD, Lower row (CC 102-109) closer to pads
#
# Scale mode button layout (chromatic ascending left-to-right, top-to-bottom):
#   Upper row: [ScaleUp] [C] [C#][D] [D#][E] [F] [InKey]
#              CC 20     21  22  23  24  25  26    27
#   Lower row: [ScaleDn] [F#][G] [G#][A] [A#][B] [Chromat]
#              CC 102    103 104 105 106 107 108  109
#
# LCD line 3 shows: [scale] | C  C# D | D# E  F | In Key
# LCD line 4 shows: [scale] | F# G G# | A  A# B | Chromat

# Middle 6 buttons per row for root selection
# Push 1: CC 20-27 is upper row (closer to LCD), CC 102-109 is lower row (closer to pads)
ROOT_UPPER_BUTTONS = [21, 22, 23, 24, 25, 26]        # Upper row CC numbers
ROOT_LOWER_BUTTONS = [103, 104, 105, 106, 107, 108]  # Lower row CC numbers
ROOT_UPPER_NOTES = [0, 1, 2, 3, 4, 5]    # C, C#, D, D#, E, F (semitones)
ROOT_LOWER_NOTES = [6, 7, 8, 9, 10, 11]  # F#, G, G#, A, A#, B (semitones)

# Outer buttons for mode/navigation
# Push 1: CC 20 is upper left, CC 102 is lower left
SCALE_UP_CC = 20       # Upper left (scroll up = previous scale)
SCALE_DOWN_CC = 102    # Lower left (scroll down = next scale)
IN_KEY_CC = 27         # Upper right
CHROMAT_CC = 109       # Lower right

# Push 1 Constants
SYSEX_HEADER = [0x47, 0x7F, 0x15]

# LCD line addresses and segment formatting
LCD_LINES = {1: 0x18, 2: 0x19, 3: 0x1A, 4: 0x1B}
CHARS_PER_SEGMENT = 17  # LCD has 4 segments of 17 chars with physical gaps

# Pad colors (velocity values)
COLOR_OFF = 0
COLOR_WHITE = 3
COLOR_WHITE_DIM = 1
COLOR_RED = 5
COLOR_ORANGE = 9
COLOR_YELLOW = 13
COLOR_YELLOW_DIM = 15
COLOR_GREEN = 21
COLOR_CYAN = 33
COLOR_BLUE = 45
COLOR_PURPLE = 49
COLOR_PINK = 57

# Button CCs - Complete mapping
BUTTONS = {
    # Navigation arrows
    'up': 46, 'down': 47, 'left': 44, 'right': 45,
    'page_left': 62, 'page_right': 63,

    # Octave/Transpose
    'octave_up': 55, 'octave_down': 54,

    # Mode buttons
    'note': 50, 'session': 51, 'scale': 58, 'accent': 57,
    'select': 48, 'shift': 49, 'user': 59,
    'mute': 60, 'solo': 61,

    # Transport
    'play': 85, 'record': 86, 'stop': 29,
    'tap_tempo': 3, 'metronome': 9,

    # Editing
    'new': 87, 'duplicate': 88, 'quantize': 116,
    'double_loop': 117, 'delete': 118, 'undo': 119,

    # Track controls
    'volume': 114, 'pan_send': 115, 'track': 112, 'clip': 113,
    'device': 110, 'browse': 111, 'master': 28,

    # 16 Buttons Below LCD
    # Upper row (closer to LCD) = CC 20-27
    # Lower row (closer to pads) = CC 102-109
    'upper_1': 20, 'upper_2': 21, 'upper_3': 22, 'upper_4': 23,
    'upper_5': 24, 'upper_6': 25, 'upper_7': 26, 'upper_8': 27,

    'lower_1': 102, 'lower_2': 103, 'lower_3': 104, 'lower_4': 105,
    'lower_5': 106, 'lower_6': 107, 'lower_7': 108, 'lower_8': 109,
}

# Track mode encoder/button mappings (Push 1 encoders above display)
# Matches PusheR layout: Enc1=Track, Enc2=Playhead, Enc3=Patch, Enc5=LeftLoop, Enc6=RightLoop
TRACK_ENCODER_CCS = {
    'track_select': 71,    # Encoder 1 (CC 71)
    'playhead_bars': 72,   # Encoder 2 (CC 72) - Shift+Turn = 16ths
    'patch_select': 73,    # Encoder 3 (CC 73)
    'left_loop': 75,       # Encoder 5 (CC 75)
    'right_loop': 76,      # Encoder 6 (CC 76)
}
# Virtual CC for Shift+Playhead (fine control) - sent to Lua as different item
PLAYHEAD_FINE_CC = 81  # Sent when Shift+Encoder2 for 16th step control
# Note: Encoder 4 (CC 74) and Encoders 7-8 (CC 77-78) are unused in Track mode
TRACK_BUTTON_CCS = set(range(20, 28)) | set(range(102, 110))

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
        self.current_mode = 'welcome'  # welcome, note, track, device, mixer, scale
        self.previous_mode = 'track'   # Mode to return to after scale mode
        self.playing = False
        self.recording = False
        self.shift_held = False

        # Debug verbosity (set to True for full SysEx logging)
        self.verbose_sysex = False

        # Display data from Reason (updated via SysEx)
        # Don't overwrite these - Reason controls this content
        self.reason_lcd_lines = ["", "", "", ""]  # 4 lines of 68 chars each
        self.device_param_names = [""] * 8
        self.device_param_values = [""] * 8
        self.device_name = ""
        self.mixer_track_names = [""] * 8
        self.mixer_volume_values = [""] * 8
        self.mixer_levels = [0] * 8

        # Isomorphic Controller State
        self.layout = IsomorphicLayout()
        self.scale_index = 0
        self.scale_scroll_offset = 0  # Which scale is at top of visible list
        self.root_note = 0  # C (0-11 semitones)
        self.in_key_mode = True  # True = In Key, False = Chromatic
        self.accent_mode = False
        self.velocity_curve = 1.0
        self.velocity_min = 40
        self.velocity_max = 127
        self.active_notes = {}  # pad -> midi_note

        # Initialize layout
        self.layout.set_scale(self.root_note, SCALE_NAMES[self.scale_index])
        self.layout.set_in_key_mode(self.in_key_mode)

    def create_virtual_ports(self, use_iac=True):
        """Create or connect to MIDI ports for Reason.

        Args:
            use_iac: If True, try to connect to IAC Driver ports first.
                     Falls back to virtual ports if IAC ports not found.
        """
        port_names = ["OpenPush Transport", "OpenPush Devices", "OpenPush Mixer"]

        # Check for IAC Driver ports
        available_inputs = mido.get_input_names()
        available_outputs = mido.get_output_names()

        if use_iac:
            # Look for IAC ports (check both with and without leading space)
            iac_found = False
            for name in port_names:
                # IAC port naming: "IAC Driver OpenPush Transport" or just "OpenPush Transport"
                iac_in = None
                iac_out = None

                for port in available_inputs:
                    if name in port and "IAC" in port:
                        iac_in = port
                        break
                for port in available_outputs:
                    if name in port and "IAC" in port:
                        iac_out = port
                        break

                if iac_in and iac_out:
                    iac_found = True
                    break

            if iac_found:
                print("Found IAC Driver ports - using persistent connections")
                print("(Configure these once in Reason → Preferences → Control Surfaces)")
                for name in port_names:
                    try:
                        # Find the matching IAC ports
                        iac_in_port = None
                        iac_out_port = None
                        for port in available_outputs:  # Our output → Reason's input
                            if name in port and "IAC" in port:
                                iac_in_port = port
                                break
                        for port in available_inputs:  # Reason's output → Our input
                            if name in port and "IAC" in port:
                                iac_out_port = port
                                break

                        if iac_in_port:
                            in_port = mido.open_output(iac_in_port)
                            self.remote_out_ports[name] = in_port
                            print(f"  Connected: {iac_in_port}")

                        if iac_out_port:
                            out_port = mido.open_input(iac_out_port)
                            self.remote_in_ports[name] = out_port
                            print(f"  Connected: {iac_out_port}")

                    except Exception as e:
                        print(f"  Error connecting to IAC {name}: {e}")
                return

        # Fall back to virtual ports
        print("Creating virtual MIDI ports...")
        print("(Note: These disappear when app closes. For persistence, set up IAC Driver ports.)")
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

    @staticmethod
    def print_iac_setup_instructions():
        """Print instructions for setting up IAC Driver ports."""
        print("""
╔══════════════════════════════════════════════════════════════════════╗
║                     IAC Driver Setup Instructions                     ║
╚══════════════════════════════════════════════════════════════════════╝

To create persistent MIDI ports that don't disappear when this app closes:

1. Open "Audio MIDI Setup" (search in Spotlight or find in /Applications/Utilities)

2. Press Cmd+2 or Window → Show MIDI Studio

3. Double-click "IAC Driver" (the red icon)

4. Check "Device is online"

5. In the Ports section, click "+" to add these ports:
   • OpenPush Transport
   • OpenPush Devices
   • OpenPush Mixer

6. Click "Apply" and close

7. Restart this app - it will automatically detect the IAC ports

8. In Reason → Preferences → Control Surfaces:
   • Add surface: OpenPush Transport
   • MIDI In: "IAC Driver OpenPush Transport"
   • MIDI Out: "IAC Driver OpenPush Transport"
   • Repeat for Devices and Mixer

Once configured, Reason will remember these settings permanently!
""")

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

    def find_push_ports(self, use_simulator=False):
        """Auto-detect Push ports.

        Args:
            use_simulator: If True, look for 'Push Simulator' port instead of real hardware.
        """
        if use_simulator:
            # Look for simulator port
            in_ports = [p for p in mido.get_input_names() if "Push Simulator" in p]
            out_ports = [p for p in mido.get_output_names() if "Push Simulator" in p]
            if in_ports and out_ports:
                print("Using Push Simulator (virtual hardware)")
                return in_ports[0], out_ports[0]
            print("Push Simulator not found. Run push_simulator.py first.")
            return None, None

        # Look for real Push hardware
        in_ports = [p for p in mido.get_input_names() if "Push" in p and "User" in p and "OpenPush" not in p]
        out_ports = [p for p in mido.get_output_names() if "Push" in p and "User" in p and "OpenPush" not in p]

        # If no real Push found, check for simulator as fallback
        if not in_ports or not out_ports:
            sim_in = [p for p in mido.get_input_names() if "Push Simulator" in p]
            sim_out = [p for p in mido.get_output_names() if "Push Simulator" in p]
            if sim_in and sim_out:
                print("Real Push not found, using Push Simulator")
                return sim_in[0], sim_out[0]

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

        # Show welcome screen
        self._update_welcome_display()

        # Light up the pad grid
        self._update_grid()

        # Light up mode buttons (dim = available, bright = active)
        self._set_button_led(BUTTONS['play'], 1)       # Play - dim (not playing)
        self._set_button_led(BUTTONS['record'], 1)     # Record - dim
        self._set_button_led(BUTTONS['volume'], 1)     # Volume/Mixer - dim
        self._set_button_led(BUTTONS['device'], 1)     # Device - dim
        self._set_button_led(BUTTONS['note'], 4)       # Note - bright (default mode)
        self._set_button_led(BUTTONS['scale'], 1)      # Scale - dim
        self._set_button_led(BUTTONS['tap_tempo'], 4)  # Tap Tempo - bright
        self._set_button_led(BUTTONS['metronome'], 1)  # Metronome - dim (off)
        self._set_button_led(BUTTONS['double_loop'], 1) # Loop - dim (off)

    def _set_lcd_segments(self, line, seg0="", seg1="", seg2="", seg3="", align="center"):
        """
        Set text on one LCD line using 4 segments of 17 chars each.

        CRITICAL: Push 1 LCD has 4 physical segments with gaps between them.
        Each segment is 17 characters. Text must be formatted per-segment
        to display correctly.

        Args:
            line: Line number 1-4
            seg0-seg3: Text for each segment (max 17 chars)
            align: "center", "left", or "right" for all segments
        """
        if not self.push_out_port:
            return

        # Format each segment with specified alignment
        parts = [seg0, seg1, seg2, seg3]
        text = ""
        for part in parts:
            segment = part[:CHARS_PER_SEGMENT]
            if align == "left":
                text += segment.ljust(CHARS_PER_SEGMENT)
            elif align == "right":
                text += segment.rjust(CHARS_PER_SEGMENT)
            else:  # center
                text += segment.center(CHARS_PER_SEGMENT)

        line_addr = LCD_LINES[line]
        # SysEx format: header + line_addr + offset(0x00) + length(0x45=69) + null + text
        data = SYSEX_HEADER + [line_addr, 0x00, 0x45, 0x00]
        data.extend([ord(c) for c in text])
        msg = mido.Message("sysex", data=data)
        self.push_out_port.send(msg)

    def _set_lcd_line_raw(self, line, text):
        """
        Set LCD line with raw 68-char string (for custom formatting).

        Use when you need different alignment per segment.
        """
        if not self.push_out_port:
            return

        # Pad or truncate to exactly 68 chars
        text = text[:68].ljust(68)

        line_addr = LCD_LINES[line]
        data = SYSEX_HEADER + [line_addr, 0x00, 0x45, 0x00]
        data.extend([ord(c) for c in text])
        msg = mido.Message("sysex", data=data)
        self.push_out_port.send(msg)

    @staticmethod
    def _clean_reason_text(text):
        """Normalize Reason text by stripping nulls/control chars."""
        cleaned = []
        for ch in text or "":
            code = ord(ch)
            if code == 0:
                continue
            if 32 <= code < 127:
                cleaned.append(ch)
            else:
                cleaned.append(" ")
        return "".join(cleaned).strip()

    @staticmethod
    def _format_8x8_line(fields):
        """Format 8 fields of 8 chars into a 68-char LCD line."""
        padded = [str(f or "")[:8].ljust(8) for f in fields]
        seg0 = padded[0] + " " + padded[1]
        seg1 = padded[2] + " " + padded[3]
        seg2 = padded[4] + " " + padded[5]
        seg3 = padded[6] + " " + padded[7]
        return seg0 + seg1 + seg2 + seg3

    def _update_grid(self):
        """Update pad grid based on current mode."""
        if not self.push_out_port:
            return

        # Update grid for note mode AND scale mode (so user sees changes live)
        if self.current_mode in ('note', 'scale'):
            # Isomorphic Layout with scale highlighting
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
        last_lcd_request = 0
        LCD_REQUEST_INTERVAL = 0.5  # Request LCD updates every 500ms

        while self.running:
            try:
                if self.push_in_port:
                    for msg in self.push_in_port.iter_pending():
                        try:
                            self._handle_push_message(msg)
                        except Exception as e:
                            print(f"ERROR handling Push message: {e}")
                            import traceback
                            traceback.print_exc()

                for name, port in self.remote_in_ports.items():
                    for msg in port.iter_pending():
                        try:
                            self._handle_reason_message(name, msg)
                        except Exception as e:
                            print(f"ERROR handling Reason message: {e}")
                            import traceback
                            traceback.print_exc()

                # Periodically request LCD updates from Reason (not in scale mode)
                if self.current_mode != 'scale':
                    now = time.time()
                    if now - last_lcd_request > LCD_REQUEST_INTERVAL:
                        self._request_lcd_update()
                        last_lcd_request = now

            except Exception as e:
                print(f"ERROR in MIDI loop: {e}")
                import traceback
                traceback.print_exc()

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

    def _normalize_encoder_delta(self, value, max_delta=1):
        """Normalize relative encoder value to capped delta.

        Push encoders send relative values:
        - 1-63: clockwise (1=slow, 63=fast)
        - 65-127: counter-clockwise (127=slow, 65=fast)
        - 64: no change

        This function caps the delta to max_delta and re-encodes.

        Args:
            value: Raw encoder CC value (0-127)
            max_delta: Maximum step size (default 1 for single-step)

        Returns:
            Normalized CC value with capped delta
        """
        if value == 0 or value == 64:
            return 64  # No change
        elif value < 64:
            # Clockwise - cap positive delta
            delta = min(value, max_delta)
            return 64 + delta  # e.g., 65 for +1
        else:
            # Counter-clockwise - cap negative delta
            delta = min(128 - value, max_delta)
            return 64 - delta  # e.g., 63 for -1

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

        # Track Shift key state (handled in Python for Play/Stop behavior)
        if cc == BUTTONS['shift']:
            self.shift_held = (value > 0)
            return

        # Tempo/Click encoders should always route to Transport (all modes).
        if cc in (14, 15):
            max_delta = 3 if cc == 14 else 5
            normalized = self._normalize_encoder_delta(value, max_delta=max_delta)
            if normalized != 64:
                out_msg = mido.Message('control_change', channel=0, control=cc, value=normalized)
                self._send_to_transport(out_msg)
                delta = normalized - 64
                if cc == 14:
                    print(f"  -> Tempo {delta:+d} BPM")
                else:
                    print(f"  -> Click Level {delta:+d}")
            return

        if value > 0:  # Button pressed
            print(f"Button: {button_name} (CC {cc}) value={value}" + (" [SHIFT]" if self.shift_held else ""))

            # Handle scale mode buttons FIRST (before other handlers can intercept)
            # 16 buttons below LCD: CC 102-109 (upper row), CC 20-27 (lower row)
            # Plus CC 71 (encoder) for scale scrolling
            if self.current_mode == 'scale':
                scale_mode_ccs = [102, 103, 104, 105, 106, 107, 108, 109,
                                  20, 21, 22, 23, 24, 25, 26, 27, 71]
                if cc in scale_mode_ccs:
                    self._handle_scale_mode_button(cc, value)
                    return

            # Track mode encoders (route to Reason Transport)
            if cc in range(71, 79):
                if self.current_mode == 'track':
                    if cc == TRACK_ENCODER_CCS['playhead_bars'] and self.shift_held:
                        # Shift+Playhead = fine control (16th steps)
                        fine_msg = mido.Message('control_change', channel=0, control=PLAYHEAD_FINE_CC, value=value)
                        self._send_to_transport(fine_msg)
                    elif cc == TRACK_ENCODER_CCS['track_select']:
                        # Track select: normalize to single step (+1/-1 per click)
                        normalized = self._normalize_encoder_delta(value, max_delta=1)
                        track_msg = mido.Message('control_change', channel=0, control=cc, value=normalized)
                        self._send_to_transport(track_msg)
                    elif cc in (TRACK_ENCODER_CCS['left_loop'], TRACK_ENCODER_CCS['right_loop']):
                        # Loop locators: jump by bars (single step per click)
                        normalized = self._normalize_encoder_delta(value, max_delta=1)
                        loop_msg = mido.Message('control_change', channel=0, control=cc, value=normalized)
                        self._send_to_transport(loop_msg)
                    elif cc == TRACK_ENCODER_CCS['playhead_bars']:
                        # Playhead: move by single bars per click (not raw encoder value)
                        normalized = self._normalize_encoder_delta(value, max_delta=1)
                        playhead_msg = mido.Message('control_change', channel=0, control=cc, value=normalized)
                        self._send_to_transport(playhead_msg)
                    elif cc in TRACK_ENCODER_CCS.values():
                        self._send_to_transport(msg)
                    return
                elif self.current_mode == 'device':
                    self._send_to_devices(msg)
                    return
                elif self.current_mode == 'mixer':
                    self._send_to_mixer(msg)
                    return

            # Transport controls
            if cc == BUTTONS['play']:
                if self.shift_held:
                    # Shift+Play = Stop (return to zero)
                    stop_msg = mido.Message('control_change', channel=0, control=BUTTONS['stop'], value=127)
                    self._send_to_transport(stop_msg)
                    self.playing = False
                    self._update_display()
                    print(f"  -> Sent Stop (Shift+Play = return to zero)")
                elif self.playing:
                    stop_msg = mido.Message('control_change', channel=0, control=BUTTONS['stop'], value=127)
                    self._send_to_transport(stop_msg)
                    self.playing = False
                    self._update_display()
                    print("  -> Sent Stop (toggle)")
                else:
                    # Play toggles play/pause in Reason
                    self._send_to_transport(msg)
                    self.playing = True
                    self._update_display()
                    print(f"  -> Sent Play (currently {'playing' if self.playing else 'stopped'})")

            elif cc == BUTTONS['record']:
                self._send_to_transport(msg)
            elif cc == BUTTONS['stop']:
                self._send_to_transport(msg)
                self.playing = False
                self._update_display()
                
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
                    self._exit_scale_mode()
                else:
                    self._enter_scale_mode()
            elif cc == BUTTONS['track']:
                self._set_mode('track')
            elif cc == BUTTONS['clip']:
                self._set_mode('clip')
            elif cc == BUTTONS['browse']:
                self._set_mode('browse')

            # Track mode buttons (16 buttons below LCD)
            elif self.current_mode == 'track' and cc in TRACK_BUTTON_CCS:
                self._send_to_transport(msg)
                return

            # Track mode mute/solo buttons
            elif self.current_mode == 'track' and cc in (BUTTONS['mute'], BUTTONS['solo']):
                self._send_to_transport(msg)
                return

            # Phase 2: Loop/Metronome/Tap Tempo
            elif cc == BUTTONS['double_loop']:  # CC 117 - using Double Loop button for Loop On/Off
                self.loop_on = not getattr(self, 'loop_on', False)
                self._send_to_transport(msg)
                self._send_to_devices(msg)
                self._set_button_led(BUTTONS['double_loop'], 4 if self.loop_on else 1)
                print(f"  -> Loop {'ON' if self.loop_on else 'OFF'}")

            elif cc == BUTTONS['metronome']:  # CC 9
                if self.shift_held:
                    # Shift+Metronome = Pre-count toggle
                    self.precount_on = not getattr(self, 'precount_on', False)
                    # Send pre-count CC to Reason (we'll need to add this to Lua)
                    precount_msg = mido.Message('control_change', channel=0, control=10, value=127 if self.precount_on else 0)
                    self._send_to_transport(precount_msg)
                    print(f"  -> Pre-count {'ON' if self.precount_on else 'OFF'}")
                else:
                    self.metronome_on = not getattr(self, 'metronome_on', False)
                    self._send_to_transport(msg)
                    self._set_button_led(BUTTONS['metronome'], 4 if self.metronome_on else 1)
                    print(f"  -> Metronome {'ON' if self.metronome_on else 'OFF'}")

            elif cc == BUTTONS['tap_tempo']:  # CC 3
                self._send_to_transport(msg)
                print(f"  -> Tap Tempo")

            # Note: Scale mode buttons are handled at TOP of this function
            # (before other handlers can intercept CC 102-109, 20-27, 71)

            else:
                pass
                # print(f"  (unhandled button)")
        else:
            # Button released
            pass

    def _handle_pad(self, msg):
        """Handle pad press/release."""
        # Filter out non-pad notes (encoder touches are notes 0-10, pads are 36-99)
        if msg.note < 36 or msg.note > 99:
            return

        # Pads always play notes (including in scale mode - user can play while selecting)
        # Scale/root selection is handled by the 16 buttons below LCD, not pads
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

            # Restore single pad color (more efficient than updating whole grid)
            pad_note = msg.note
            row = (pad_note - 36) // 8
            col = (pad_note - 36) % 8
            info = self.layout.get_pad_info(row, col)

            if info['is_root']:
                color = COLOR_BLUE
            elif info['is_in_scale']:
                color = COLOR_WHITE
            else:
                color = COLOR_OFF if self.layout.in_key_mode else COLOR_WHITE_DIM

            self._set_pad_color(pad_note, color)

    def _set_mode(self, mode):
        """Switch to a different mode and update display."""
        # Track previous mode for returning from scale mode
        # Only track non-scale, non-welcome modes
        if self.current_mode in ('track', 'device', 'mixer', 'note'):
            self.previous_mode = self.current_mode

        self.current_mode = mode
        print(f"Mode: {mode}")

        # Update button LEDs for mode buttons
        self._set_button_led(BUTTONS['volume'], 4 if mode == 'mixer' else 1)
        self._set_button_led(BUTTONS['device'], 4 if mode == 'device' else 1)
        self._set_button_led(BUTTONS['note'], 4 if mode == 'note' else 1)
        self._set_button_led(BUTTONS['scale'], 4 if mode == 'scale' else 1)
        self._set_button_led(BUTTONS['track'], 4 if mode == 'track' else 1)
        self._set_button_led(BUTTONS['clip'], 4 if mode == 'clip' else 1)
        self._set_button_led(BUTTONS['browse'], 4 if mode == 'browse' else 1)

        # Update LCD display for new mode
        self._update_display()

        # Request LCD data from Reason (may override our display)
        self._request_lcd_update()

        # Update grid (isomorphic layout, etc.)
        self._update_grid()

    def _update_display(self):
        """Update LCD based on current mode."""
        if self.current_mode == 'welcome':
            self._update_welcome_display()
        elif self.current_mode == 'scale':
            self._update_scale_display()
        elif self.current_mode == 'track':
            self._update_track_display()
        elif self.current_mode == 'note':
            self._update_note_display()
        elif self.current_mode == 'device':
            self._update_device_display()
        elif self.current_mode == 'mixer':
            self._update_mixer_display()
        else:
            self._update_default_display()

    def _update_welcome_display(self):
        """Show welcome screen on initial load."""
        self._set_lcd_segments(1, "", "OpenPush", "", "")
        self._set_lcd_segments(2, "", "Reason Bridge", "", "")
        self._set_lcd_segments(3, "", "", "", "")
        self._set_lcd_segments(4, "Track", "Device", "Mixer", "to start")

    def _update_track_display(self):
        """Update LCD for Track mode - shows track/position/loop/tempo from Reason.

        The Lua codec formats 4 complete display lines:
        - Line 1: Track name + Patch name
        - Line 2: Device name + Song name
        - Line 3: Position | Left Loop | Right Loop | BPM
        - Line 4: Loop state

        We pass these through directly since Lua already formats them
        with proper segment alignment.
        """
        # Check if we have any data from Reason
        has_data = any(line.strip() for line in self.reason_lcd_lines)

        if has_data:
            # Pass through the pre-formatted lines from Lua codec
            for i in range(4):
                line = self.reason_lcd_lines[i] if i < len(self.reason_lcd_lines) else ""
                if line.strip():
                    self._set_lcd_line_raw(i + 1, line)
                else:
                    self._set_lcd_segments(i + 1, "", "", "", "")
        else:
            # No data yet - show waiting message
            self._set_lcd_segments(1, "Track Mode", "", "", "")
            self._set_lcd_segments(2, "Waiting for", "Reason", "data...", "")
            self._set_lcd_segments(3, "", "", "", "")
            self._set_lcd_segments(4, "", "", "", "")

    def _update_note_display(self):
        """Update LCD for note/play mode.

        Always show scale info on line 1. Pass through Reason data on other lines.
        """
        root_name = ROOT_NAMES[self.root_note]
        scale_name = get_scale_display_name(SCALE_NAMES[self.scale_index])
        octave = self.layout.get_octave()
        mode_str = "In-Key" if self.in_key_mode else "Chromatic"
        status = "Playing" if self.playing else "Stopped"

        # Line 1: Always show our scale info
        self._set_lcd_segments(1, f"{root_name} {scale_name}", f"Octave {octave}", mode_str, status)

        # Check if Reason has sent any display data
        has_reason_data = any(line.strip() for line in self.reason_lcd_lines)

        if has_reason_data:
            # Lines 2-4: Reason's display data if available
            # Map Reason Line 0 (Track Name) -> Physical Line 2
            # Map Reason Line 1 (Doc Name)   -> Physical Line 3
            # Map Reason Line 2              -> Physical Line 4
            for i in range(0, 3):
                line = self.reason_lcd_lines[i] if i < len(self.reason_lcd_lines) else ""
                if line.strip():
                    self._set_lcd_line_raw(i + 2, line)
                else:
                    self._set_lcd_segments(i + 2, "", "", "", "")
        else:
            # No Reason data - clear remaining lines
            self._set_lcd_segments(2, "", "", "", "")
            self._set_lcd_segments(3, "", "", "", "")
            self._set_lcd_segments(4, "", "", "", "")

    def _update_default_display(self):
        """Update LCD for other modes (device, mixer, etc.).

        Always show mode info on line 1. Pass through Reason data if available.
        """
        mode_display = self.current_mode.capitalize()
        status = "Playing" if self.playing else "Stopped"

        # Check if Reason has sent any display data
        has_reason_data = any(line.strip() for line in self.reason_lcd_lines)

        if has_reason_data:
            # Line 1: Mode name + status (always show our info)
            self._set_lcd_segments(1, mode_display, "", "", status)
            # Lines 2-4: Reason's display data if available
            # Map Reason Line 0 (Track Name) -> Physical Line 2
            for i in range(0, 3):
                line = self.reason_lcd_lines[i] if i < len(self.reason_lcd_lines) else ""
                if line.strip():
                    self._set_lcd_line_raw(i + 2, line)
                else:
                    self._set_lcd_segments(i + 2, "", "", "", "")
        else:
            # No Reason data - show mode name only
            self._set_lcd_segments(1, mode_display, "", "", status)
            self._set_lcd_segments(2, "Waiting for", "Reason", "data...", "")
            self._set_lcd_segments(3, "", "", "", "")
            self._set_lcd_segments(4, "", "", "", "")

    def _update_device_display(self):
        """Update LCD for device mode using Reason parameter data."""
        status = "Playing" if self.playing else "Stopped"
        device_name = self.device_name.strip() or "Device"

        self._set_lcd_segments(1, "Device", device_name, "", status)
        self._set_lcd_line_raw(2, self._format_8x8_line(self.device_param_names))
        self._set_lcd_line_raw(3, self._format_8x8_line(self.device_param_values))
        self._set_lcd_segments(4, "", "", "", "")

    def _update_mixer_display(self):
        """Update LCD for mixer mode using Reason track data."""
        status = "Playing" if self.playing else "Stopped"

        self._set_lcd_segments(1, "Mixer", "", "", status)
        self._set_lcd_line_raw(2, self._format_8x8_line(self.mixer_track_names))
        self._set_lcd_line_raw(3, self._format_8x8_line(self.mixer_volume_values))
        self._set_lcd_segments(4, "", "", "", "")

    def _update_scale_display(self):
        """Update LCD for scale selection mode.

        Button layout matches LCD (chromatic ascending):
          Upper: [ScaleUp] [C] [C#][D] [D#][E] [F] [InKey]
          Lower: [ScaleDn] [F#][G] [G#][A] [A#][B] [Chromat]

        LCD Layout:
        - Segment 0: 4 scales visible (scrollable list), > marks current
        - Segments 1-2: Root note labels matching buttons
        - Segment 3: In Key / Chromat toggle
        """
        # Get 4 visible scales based on scroll offset
        total_scales = len(SCALE_NAMES)

        # Keep current scale visible (adjust scroll if needed)
        if self.scale_index < self.scale_scroll_offset:
            self.scale_scroll_offset = self.scale_index
        elif self.scale_index >= self.scale_scroll_offset + 4:
            self.scale_scroll_offset = self.scale_index - 3

        # Build scale list for segment 0 of each line (LEFT-aligned)
        scale_texts = []
        for i in range(4):
            idx = self.scale_scroll_offset + i
            if idx < total_scales:
                name = get_scale_display_name(SCALE_NAMES[idx])
                # Add > marker for current selection
                if idx == self.scale_index:
                    scale_texts.append(f">{name[:15]}")
                else:
                    scale_texts.append(f" {name[:15]}")
            else:
                scale_texts.append("")

        # Build root display strings with current selection marked
        def format_roots(roots_list):
            """Format 3 root notes for a segment, mark selected with brackets."""
            parts = []
            for r in roots_list:
                label = ROOT_NAMES[r]
                if r == self.root_note:
                    parts.append(f"[{label}]")
                else:
                    parts.append(f" {label} ")
            return "  ".join(parts)

        # Root segments matching button layout
        upper_seg1 = format_roots(ROOT_UPPER_NOTES[:3])  # C G D
        upper_seg2 = format_roots(ROOT_UPPER_NOTES[3:])  # A E B
        lower_seg1 = format_roots(ROOT_LOWER_NOTES[:3])  # F Bb Eb
        lower_seg2 = format_roots(ROOT_LOWER_NOTES[3:])  # Ab Db Gb

        # Mode toggle (RIGHT-aligned in segment 3)
        in_key_mark = ">" if self.in_key_mode else " "
        chromat_mark = ">" if not self.in_key_mode else " "

        # Build each line with mixed alignment
        # Segment 0: left-aligned scale name (17 chars)
        # Segments 1-2: centered root notes (17 chars each)
        # Segment 3: right-aligned mode toggle (17 chars)

        def build_line(scale_text, root_seg1, root_seg2, mode_text):
            seg0 = scale_text[:17].ljust(17)
            seg1 = root_seg1[:17].center(17)
            seg2 = root_seg2[:17].center(17)
            seg3 = mode_text[:17].rjust(17)
            return seg0 + seg1 + seg2 + seg3

        # Lines 1-2: Scale names only (rest empty)
        self._set_lcd_line_raw(1, scale_texts[0].ljust(17) + " " * 51)
        self._set_lcd_line_raw(2, scale_texts[1].ljust(17) + " " * 51)

        # Lines 3-4: Scale + roots + mode
        self._set_lcd_line_raw(3, build_line(scale_texts[2], upper_seg1, upper_seg2, f"{in_key_mark}In Key"))
        self._set_lcd_line_raw(4, build_line(scale_texts[3], lower_seg1, lower_seg2, f"{chromat_mark}Chromat"))

    def _update_scale_button_leds(self):
        """Update button LEDs for scale selection mode.

        Button layout (chromatic ascending):
          Upper: [ScaleUp] [C] [C#][D] [D#][E] [F] [InKey]
                 CC 20     21  22  23  24  25  26    27
          Lower: [ScaleDn] [F#][G] [G#][A] [A#][B] [Chromat]
                 CC 102    103 104 105 106 107 108  109

        The 16 buttons below LCD use pad color values (like pads), not button LED values.
        Yellow colors: 13 = bright yellow, 15 = dim yellow
        """
        if self.current_mode != 'scale':
            return

        # Upper row (CC 20-27) has different LED behavior - some values blink
        # Tested values that DON'T blink on upper row: 7, 10, 13
        UPPER_BRIGHT = 10  # Selected (yellow, no blink)
        UPPER_DIM = 7      # Unselected (dimmer, no blink)

        # Lower row (CC 102-109) works with standard color palette
        LOWER_BRIGHT = 13  # Selected (yellow)
        LOWER_DIM = 11     # Unselected (dim yellow/orange)

        # Check scroll limits
        at_top = self.scale_index == 0
        at_bottom = self.scale_index >= len(SCALE_NAMES) - 1

        # Scale Up (CC 20, upper row)
        self._set_button_led(SCALE_UP_CC, UPPER_DIM if at_top else UPPER_BRIGHT)
        # Scale Down (CC 102, lower row)
        self._set_button_led(SCALE_DOWN_CC, LOWER_DIM if at_bottom else LOWER_BRIGHT)

        # Upper row root selection (CC 21-26)
        for i, cc in enumerate(ROOT_UPPER_BUTTONS):
            root_val = ROOT_UPPER_NOTES[i]
            if root_val == self.root_note:
                self._set_button_led(cc, UPPER_BRIGHT)  # Selected
            else:
                self._set_button_led(cc, UPPER_DIM)  # Unselected

        # Lower row root selection (CC 103-108)
        for i, cc in enumerate(ROOT_LOWER_BUTTONS):
            root_val = ROOT_LOWER_NOTES[i]
            if root_val == self.root_note:
                self._set_button_led(cc, LOWER_BRIGHT)  # Selected
            else:
                self._set_button_led(cc, LOWER_DIM)  # Unselected

        # In Key (CC 27, upper row)
        self._set_button_led(IN_KEY_CC, UPPER_BRIGHT if self.in_key_mode else UPPER_DIM)
        # Chromatic (CC 109, lower row)
        self._set_button_led(CHROMAT_CC, LOWER_BRIGHT if not self.in_key_mode else LOWER_DIM)

    def _enter_scale_mode(self):
        """Enter scale selection mode.

        Only the LCD and 16 buttons below LCD change.
        Pad grid stays active for playing while selecting scale.
        """
        self.current_mode = 'scale'
        print("Entering Scale mode")

        # Update button LEDs (only mode buttons and scale selection buttons)
        self._set_button_led(BUTTONS['scale'], 4)  # Scale button bright
        self._set_button_led(BUTTONS['note'], 1)   # Note button dim
        self._update_scale_button_leds()

        # Update display only - pads remain active for playing
        self._update_display()

    def _apply_scale_changes(self):
        """Apply current scale settings to layout and update grid immediately."""
        self.layout.set_scale(self.root_note, SCALE_NAMES[self.scale_index])
        self.layout.set_in_key_mode(self.in_key_mode)
        self._update_grid()

    def _exit_scale_mode(self):
        """Exit scale selection mode and return to previous mode."""
        print(f"Exiting Scale mode -> {ROOT_NAMES[self.root_note]} {get_scale_display_name(SCALE_NAMES[self.scale_index])}")

        # Clear the 16 buttons below LCD (turn off scale selection LEDs)
        for cc in ROOT_UPPER_BUTTONS + ROOT_LOWER_BUTTONS:
            self._set_button_led(cc, 0)
        self._set_button_led(SCALE_UP_CC, 0)
        self._set_button_led(SCALE_DOWN_CC, 0)
        self._set_button_led(IN_KEY_CC, 0)
        self._set_button_led(CHROMAT_CC, 0)

        # Return to previous mode (track, device, mixer, or note)
        return_mode = self.previous_mode if self.previous_mode else 'track'
        print(f"  Returning to: {return_mode}")
        self._set_mode(return_mode)

    def _handle_scale_mode_button(self, cc, value):
        """Handle button press in scale mode.

        Button layout (chromatic ascending):
          Upper: [ScaleUp] [C] [C#][D] [D#][E] [F] [InKey]
                 CC 20     21  22  23  24  25  26    27
          Lower: [ScaleDn] [F#][G] [G#][A] [A#][B] [Chromat]
                 CC 102    103 104 105 106 107 108  109
        """
        # CC 71 = Track 1 encoder - scroll through scales
        if cc == 71:
            # Relative encoder: 1-63 = CW (scroll down), 65-127 = CCW (scroll up)
            if value < 64:
                self._scroll_scale(1)  # Clockwise = down
            else:
                self._scroll_scale(-1)  # Counter-clockwise = up
            return

        # Scale Up button (CC 20 - upper row, closer to LCD)
        # Top button scrolls UP the list (previous scale, lower index)
        if cc == SCALE_UP_CC:
            self._scroll_scale(-1)  # Up = previous scale
            print("  Scale Up (prev)")
            return

        # Scale Down button (CC 102 - lower row, closer to pads)
        # Bottom button scrolls DOWN the list (next scale, higher index)
        if cc == SCALE_DOWN_CC:
            self._scroll_scale(1)  # Down = next scale
            print("  Scale Down (next)")
            return

        # In Key button (upper right)
        if cc == IN_KEY_CC:
            self.in_key_mode = True
            print("  Mode: In Key")
            self._apply_scale_changes()
            self._update_scale_display()
            self._update_scale_button_leds()
            return

        # Chromatic button (lower right)
        if cc == CHROMAT_CC:
            self.in_key_mode = False
            print("  Mode: Chromatic")
            self._apply_scale_changes()
            self._update_scale_display()
            self._update_scale_button_leds()
            return

        # Upper row root selection: C, C#, D, D#, E, F
        if cc in ROOT_UPPER_BUTTONS:
            idx = ROOT_UPPER_BUTTONS.index(cc)
            self.root_note = ROOT_UPPER_NOTES[idx]
            print(f"  Root: {ROOT_NAMES[self.root_note]}")
            self._apply_scale_changes()
            self._update_scale_display()
            self._update_scale_button_leds()
            return

        # Lower row root selection: F#, G, G#, A, A#, B
        if cc in ROOT_LOWER_BUTTONS:
            idx = ROOT_LOWER_BUTTONS.index(cc)
            self.root_note = ROOT_LOWER_NOTES[idx]
            print(f"  Root: {ROOT_NAMES[self.root_note]}")
            self._apply_scale_changes()
            self._update_scale_display()
            self._update_scale_button_leds()
            return

    def _scroll_scale(self, direction):
        """Scroll through scale list.

        Args:
            direction: +1 to go down (higher index), -1 to go up (lower index)
        """
        total_scales = len(SCALE_NAMES)
        new_index = self.scale_index + direction

        # Clamp to valid range
        if new_index < 0:
            new_index = 0
        elif new_index >= total_scales:
            new_index = total_scales - 1

        if new_index != self.scale_index:
            self.scale_index = new_index
            scale_name = get_scale_display_name(SCALE_NAMES[self.scale_index])
            print(f"  Scale: {scale_name}")
            self._apply_scale_changes()
            self._update_scale_display()
            self._update_scale_button_leds()  # Update scroll limit indicators

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

    def _request_lcd_update(self):
        """Send SysEx to Reason requesting current LCD text values."""
        # Request from Transport (port 0x01)
        if "OpenPush Transport" in self.remote_out_ports:
            # SysEx: F0 00 11 22 01 4F F7 (request LCD update, msg_type=0x4F)
            request_sysex = mido.Message('sysex', data=[0x00, 0x11, 0x22, 0x01, 0x4F])
            try:
                self.remote_out_ports["OpenPush Transport"].send(request_sysex)
            except Exception as e:
                print(f"Transport LCD request error: {e}")

        # Request from Devices (port 0x02)
        if "OpenPush Devices" in self.remote_out_ports:
            # SysEx: F0 00 11 22 02 4F F7 (request LCD update, msg_type=0x4F)
            request_sysex = mido.Message('sysex', data=[0x00, 0x11, 0x22, 0x02, 0x4F])
            try:
                self.remote_out_ports["OpenPush Devices"].send(request_sysex)
            except Exception as e:
                print(f"Devices LCD request error: {e}")

    def _handle_reason_message(self, port_name, msg):
        """Handle MIDI message from Reason, route to Push with channel translation."""
        # Handle messages from Reason
        if msg.type == 'sysex':
            if self.verbose_sysex:
                print(f"Reason SysEx ({port_name}): {' '.join(f'{b:02x}' for b in msg.data)}")
            if self._handle_reason_sysex(port_name, msg):
                return
        elif msg.type == 'control_change':
            if self.verbose_sysex:
                print(f"Reason CC ({port_name}): ch={msg.channel} cc={msg.control} val={msg.value}")

        # Update state based on Reason feedback
        if msg.type == 'control_change':
            # Transport feedback - CC numbers now match Push hardware
            # Handle these specially with correct LED values (don't forward raw)
            if port_name == "OpenPush Transport":
                if msg.control == 85:  # Play state
                    self.playing = msg.value > 0
                    print(f"  Play state: {self.playing} -> LED {4 if self.playing else 1}")
                    self._set_button_led(BUTTONS['play'], 4 if self.playing else 1)
                    return  # Don't forward - we handled it with correct LED value
                elif msg.control == 86:  # Record state
                    self.recording = msg.value > 0
                    print(f"  Record state: {self.recording} -> LED {5 if self.recording else 1}")
                    self._set_button_led(BUTTONS['record'], 5 if self.recording else 1)
                    return  # Don't forward - we handled it with correct LED value

            # Forward other CC messages to Push with channel translation (ch15 → ch0)
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

    def _handle_reason_sysex(self, port_name, msg):
        """Handle SysEx from Reason (ping/pong and display updates)."""
        if port_name not in self.remote_out_ports:
            print(f"  SysEx from unknown port: {port_name}")
            return False

        reason_msg = ReasonMessage.from_sysex(list(msg.data))
        if not reason_msg:
            print(f"  SysEx parse failed (not our format)")
            return False

        if self.verbose_sysex:
            print(f"  Parsed: port={reason_msg.port_id.name} type={reason_msg.msg_type.name}")

        # Handle Ping (Auto-detect)
        if reason_msg.msg_type == MessageType.SYSTEM_PING:
            response = ReasonMessage(
                port_id=reason_msg.port_id,
                msg_type=MessageType.SYSTEM_PONG,
                data=[0x01],
            )
            try:
                self.remote_out_ports[port_name].send(
                    mido.Message('sysex', data=response.to_sysex())
                )
            except Exception as e:
                print(f"Reason probe response error: {e}")
                return False
            return True

        # Handle Display Line Update
        elif reason_msg.msg_type == MessageType.DISPLAY_LINE:
            if len(reason_msg.data) < 1:
                return False

            # Don't let Reason overwrite LCD in scale mode
            if self.current_mode == 'scale':
                return True

            line_idx = reason_msg.data[0]  # 1-4
            text_bytes = reason_msg.data[1:]
            text = "".join(chr(c) for c in text_bytes)

            if self.verbose_sysex:
                print(f"  LCD Update: line {line_idx} = '{text}'")

            # Store Reason's display data (0-indexed internally)
            if 1 <= line_idx <= 4:
                self.reason_lcd_lines[line_idx - 1] = text.ljust(68)[:68]

            # Update display based on current mode
            self._update_display()
            return True

        # Handle Device Param Updates (names/values)
        elif reason_msg.msg_type == MessageType.DEVICE_PARAM:
            if len(reason_msg.data) < 2:
                return False

            param_index = reason_msg.data[0]  # 1-8
            field_type = reason_msg.data[1]  # 0=name, 1=value
            text = "".join(chr(c) for c in reason_msg.data[2:]).rstrip()

            if 1 <= param_index <= 8:
                idx = param_index - 1
                if field_type == 0:
                    self.device_param_names[idx] = text
                elif field_type == 1:
                    self.device_param_values[idx] = text

            if self.current_mode == 'device':
                self._update_display()
            return True

        # Handle Device Name Updates
        elif reason_msg.msg_type == MessageType.DEVICE_NAME:
            text = "".join(chr(c) for c in reason_msg.data).rstrip()
            if self.verbose_sysex:
                print(f"  Device: '{text}'")
            self.device_name = text

            if self.current_mode in ('device', 'track'):
                self._update_display()
            return True

        # Handle Mixer Track Names
        elif reason_msg.msg_type == MessageType.MIXER_NAME:
            if len(reason_msg.data) < 1:
                return False

            channel = reason_msg.data[0]
            text = "".join(chr(c) for c in reason_msg.data[1:]).rstrip()
            if 0 <= channel < 8:
                self.mixer_track_names[channel] = text

            if self.current_mode == 'mixer':
                self._update_display()
            return True

        # Handle Mixer Volume Display Values
        elif reason_msg.msg_type == MessageType.MIXER_VOLUME:
            if len(reason_msg.data) < 1:
                return False

            channel = reason_msg.data[0]
            text = "".join(chr(c) for c in reason_msg.data[1:]).rstrip()
            if 0 <= channel < 8:
                self.mixer_volume_values[channel] = text

            if self.current_mode == 'mixer':
                self._update_display()
            return True

        # Handle Mixer Meter Levels
        elif reason_msg.msg_type == MessageType.MIXER_LEVEL:
            if len(reason_msg.data) < 2:
                return False

            channel = reason_msg.data[0]
            level = reason_msg.data[1]
            if 0 <= channel < 8:
                self.mixer_levels[channel] = level
            return True

        return False

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
    import argparse
    parser = argparse.ArgumentParser(description="OpenPush - Push to Reason Bridge")
    parser.add_argument('--sim', action='store_true', help="Use Push Simulator instead of real hardware")
    parser.add_argument('-v', '--verbose', action='store_true', help="Enable verbose SysEx logging")
    args = parser.parse_args()

    print("=" * 50)
    print("  OpenPush - Push to Reason Bridge")
    if args.sim:
        print("  (SIMULATOR MODE)")
    if args.verbose:
        print("  (VERBOSE LOGGING)")
    print("=" * 50)

    app = OpenPushApp()
    app.verbose_sysex = args.verbose
    app.create_virtual_ports()
    app.list_ports()

    # Find Push ports (real hardware or simulator)
    use_simulator = args.sim
    in_port, out_port = app.find_push_ports(use_simulator=use_simulator)

    if app.connect_push(in_port, out_port):
        app.start()

        print("\n" + "=" * 50)
        print("  OpenPush is running!")
        print("=" * 50)
        print("\nIn Reason, add control surfaces:")
        print("  Manufacturer: OpenPush")
        print("  MIDI Input:   OpenPush Transport In")
        print("  MIDI Output:  OpenPush Transport Out")
        print("\nCommands: t=test LED, p=test pad, i=IAC setup, h=help, q=quit")
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
                    elif cmd == 'i':
                        OpenPushApp.print_iac_setup_instructions()
                    elif cmd == 'h' or cmd == '?':
                        print("\nCommands: t=test LED, p=test pad, i=IAC setup, q=quit")
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
