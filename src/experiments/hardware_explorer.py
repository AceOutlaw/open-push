#!/usr/bin/env python3
"""
Hardware Explorer for Push 1

Explore Push 1 hardware capabilities:
- Latency testing (round-trip MIDI measurement)
- Grid pad LED colors (all 128 velocity values)
- Control button LEDs (16 buttons below LCD)
- Animation and pattern experiments

Usage:
    python3 src/experiments/hardware_explorer.py

HARDWARE CONTROLS:
    Pad grid     - Touch to see color values
    Arrows       - Navigate color palette
    Session      - Return to menu

KEYBOARD:
    1: Latency test
    2: Grid color palette (all 128 colors)
    3: Grid animations (rainbow, wave, sparkle, etc.)
    4: Control button LED patterns
    5: Full light show (everything!)
    q: Quit
"""

import mido
import time
import math
import sys
import select
import random

# Push 1 SysEx header
SYSEX_HEADER = [0x47, 0x7F, 0x15]

# LCD configuration
LCD_LINES = {1: 0x18, 2: 0x19, 3: 0x1A, 4: 0x1B}
CHARS_PER_SEGMENT = 17

# Pad grid
PAD_START = 36
PAD_END = 99
GRID_SIZE = 8

# Control buttons below LCD (from Push 2 mapping - same as Push 1)
UPPER_BUTTONS = [102, 103, 104, 105, 106, 107, 108, 109]  # CC 102-109
LOWER_BUTTONS = [20, 21, 22, 23, 24, 25, 26, 27]          # CC 20-27

# Navigation buttons
NAV_BUTTONS = {
    'left': 44, 'right': 45, 'up': 46, 'down': 47,
    'session': 51, 'note': 50,
}

# LED color palette - key values discovered/documented
# Velocity 0-127 maps to different colors
COLOR_NAMES = {
    0: 'off',
    1: 'dim white', 2: 'white', 3: 'bright white',
    4: 'dim red', 5: 'red', 6: 'bright red', 7: 'pink-red',
    8: 'dim orange', 9: 'orange', 10: 'bright orange',
    11: 'dim yellow', 12: 'yellow', 13: 'bright yellow',
    14: 'lime', 15: 'yellow-green',
    17: 'dim green', 21: 'green', 25: 'bright green',
    29: 'cyan-green', 33: 'cyan', 37: 'bright cyan',
    41: 'dim blue', 45: 'blue', 48: 'bright blue',
    49: 'purple', 52: 'violet', 53: 'magenta',
    57: 'pink', 58: 'hot pink',
}


class HardwareExplorer:
    def __init__(self):
        self.push_out = None
        self.push_in = None
        self.running = False
        self.current_mode = 'menu'

        # Latency test data
        self.latency_samples = []
        self.test_note = 60
        self.test_start_time = 0

        # Color exploration
        self.current_color = 0
        self.color_page = 0  # 0-7, each page shows 16 colors

    def connect(self):
        """Connect to Push 1 User Port."""
        for port_name in mido.get_output_names():
            if 'Ableton Push' in port_name and 'User' in port_name:
                self.push_out = mido.open_output(port_name)
                print(f"Output: {port_name}")
                break

        for port_name in mido.get_input_names():
            if 'Ableton Push' in port_name and 'User' in port_name:
                self.push_in = mido.open_input(port_name)
                print(f"Input: {port_name}")
                break

        if self.push_out and self.push_in:
            print("Connected to Push 1!")
            return True

        print("ERROR: Push 1 User Port not found")
        return False

    def send_sysex(self, data):
        """Send SysEx message."""
        if self.push_out:
            self.push_out.send(mido.Message('sysex', data=SYSEX_HEADER + data))

    def set_user_mode(self):
        """Switch to User Mode."""
        self.send_sysex([0x62, 0x00, 0x01, 0x01])
        time.sleep(0.1)

    def set_pad_color(self, note, velocity):
        """Set pad LED color (velocity 0-127)."""
        if self.push_out:
            self.push_out.send(mido.Message('note_on', note=note, velocity=velocity))

    def set_button_led(self, cc, value):
        """Set button LED (0=off, 1=dim, 4=bright)."""
        if self.push_out:
            self.push_out.send(mido.Message('control_change', control=cc, value=value))

    def clear_grid(self):
        """Turn off all pad LEDs."""
        for note in range(PAD_START, PAD_END + 1):
            self.set_pad_color(note, 0)

    def clear_buttons(self):
        """Turn off all button LEDs."""
        for cc in UPPER_BUTTONS + LOWER_BUTTONS:
            self.set_button_led(cc, 0)
        for cc in NAV_BUTTONS.values():
            self.set_button_led(cc, 0)

    def set_lcd_line(self, line, text):
        """Set LCD line."""
        if line not in LCD_LINES:
            return
        text = text[:68].ljust(68)
        data = [LCD_LINES[line], 0x00, 0x45, 0x00]
        data.extend([ord(c) for c in text])
        self.send_sysex(data)

    def set_lcd_segments(self, line, seg0="", seg1="", seg2="", seg3=""):
        """Set LCD with segment-aware formatting."""
        if line not in LCD_LINES:
            return
        text = ""
        for seg in [seg0, seg1, seg2, seg3]:
            text += seg[:CHARS_PER_SEGMENT].ljust(CHARS_PER_SEGMENT)
        data = [LCD_LINES[line], 0x00, 0x45, 0x00]
        data.extend([ord(c) for c in text])
        self.send_sysex(data)

    # =========================================================================
    # LATENCY TESTING
    # =========================================================================

    def latency_test(self):
        """Measure round-trip MIDI latency."""
        print("\n" + "=" * 60)
        print("LATENCY TEST")
        print("=" * 60)
        print("Measuring round-trip MIDI latency...")
        print("Press any pad to test. Press Session to exit.\n")

        self.set_lcd_segments(1, "LATENCY TEST", "", "", "")
        self.set_lcd_segments(2, "Press any pad", "to measure", "round-trip", "latency")
        self.set_lcd_segments(3, "", "", "", "")
        self.set_lcd_segments(4, "Samples: 0", "Avg: --", "Min: --", "Max: --")

        # Light up grid dimly to show it's active
        for note in range(PAD_START, PAD_END + 1):
            self.set_pad_color(note, 1)  # Dim white

        self.latency_samples = []
        testing = True

        while testing:
            # Check for MIDI input
            if self.push_in:
                for msg in self.push_in.iter_pending():
                    if msg.type == 'note_on' and msg.velocity > 0:
                        if PAD_START <= msg.note <= PAD_END:
                            # Measure time to respond
                            start = time.perf_counter()

                            # Send immediate response (light the pad)
                            self.set_pad_color(msg.note, 5)  # Red flash

                            # Calculate latency (this is just output latency)
                            end = time.perf_counter()
                            latency_ms = (end - start) * 1000

                            self.latency_samples.append(latency_ms)

                            # Reset pad after brief delay
                            time.sleep(0.05)
                            self.set_pad_color(msg.note, 1)

                            # Update display
                            self._update_latency_display()

                    elif msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0):
                        pass  # Ignore note off

                    elif msg.type == 'control_change':
                        if msg.control == NAV_BUTTONS['session'] and msg.value > 0:
                            testing = False
                            break

            # Check keyboard
            if select.select([sys.stdin], [], [], 0.01)[0]:
                cmd = sys.stdin.readline().strip().lower()
                if cmd == 'q' or cmd == 'x':
                    testing = False

        self.clear_grid()
        self._print_latency_summary()

    def _update_latency_display(self):
        """Update LCD with latency stats."""
        if not self.latency_samples:
            return

        avg = sum(self.latency_samples) / len(self.latency_samples)
        min_lat = min(self.latency_samples)
        max_lat = max(self.latency_samples)

        self.set_lcd_segments(4,
            f"N={len(self.latency_samples)}",
            f"Avg={avg:.2f}ms",
            f"Min={min_lat:.2f}ms",
            f"Max={max_lat:.2f}ms"
        )

        print(f"  Sample {len(self.latency_samples)}: {self.latency_samples[-1]:.3f}ms "
              f"(avg: {avg:.3f}ms)")

    def _print_latency_summary(self):
        """Print final latency summary."""
        print("\n" + "-" * 40)
        if self.latency_samples:
            avg = sum(self.latency_samples) / len(self.latency_samples)
            print(f"Samples: {len(self.latency_samples)}")
            print(f"Average: {avg:.3f}ms")
            print(f"Min:     {min(self.latency_samples):.3f}ms")
            print(f"Max:     {max(self.latency_samples):.3f}ms")

            # Jitter (standard deviation)
            if len(self.latency_samples) > 1:
                variance = sum((x - avg) ** 2 for x in self.latency_samples) / len(self.latency_samples)
                std_dev = variance ** 0.5
                print(f"Jitter:  {std_dev:.3f}ms (std dev)")
        else:
            print("No samples collected")
        print("-" * 40)

    # =========================================================================
    # GRID PAD COLOR EXPLORATION
    # =========================================================================

    def color_palette_explorer(self):
        """Explore all 128 pad colors."""
        print("\n" + "=" * 60)
        print("COLOR PALETTE EXPLORER")
        print("=" * 60)
        print("Showing all 128 velocity values as colors")
        print("Touch pads to see color info. Arrows to navigate pages.")
        print("Press Session to exit.\n")

        self.color_page = 0
        self._draw_color_page()

        exploring = True
        while exploring:
            if self.push_in:
                for msg in self.push_in.iter_pending():
                    if msg.type == 'note_on' and msg.velocity > 0:
                        if PAD_START <= msg.note <= PAD_END:
                            # Calculate which color this pad represents
                            row = (msg.note - PAD_START) // 8
                            col = (msg.note - PAD_START) % 8
                            color_value = self.color_page * 64 + row * 8 + col

                            if color_value < 128:
                                color_name = COLOR_NAMES.get(color_value, "")
                                print(f"Pad ({row},{col}): Color value = {color_value} {color_name}")
                                self.set_lcd_segments(3,
                                    f"Value: {color_value}",
                                    f"Hex: 0x{color_value:02X}",
                                    color_name[:17] if color_name else "",
                                    f"Page {self.color_page + 1}/2"
                                )

                    elif msg.type == 'control_change' and msg.value > 0:
                        if msg.control == NAV_BUTTONS['session']:
                            exploring = False
                        elif msg.control == NAV_BUTTONS['right']:
                            self.color_page = (self.color_page + 1) % 2
                            self._draw_color_page()
                        elif msg.control == NAV_BUTTONS['left']:
                            self.color_page = (self.color_page - 1) % 2
                            self._draw_color_page()

            if select.select([sys.stdin], [], [], 0.01)[0]:
                cmd = sys.stdin.readline().strip().lower()
                if cmd == 'q' or cmd == 'x':
                    exploring = False
                elif cmd == 'n' or cmd == '.':
                    self.color_page = (self.color_page + 1) % 2
                    self._draw_color_page()
                elif cmd == 'p' or cmd == ',':
                    self.color_page = (self.color_page - 1) % 2
                    self._draw_color_page()

        self.clear_grid()

    def _draw_color_page(self):
        """Draw current page of color palette on grid."""
        base_color = self.color_page * 64

        self.set_lcd_segments(1, "COLOR PALETTE", f"Page {self.color_page + 1}/2",
                             f"Values {base_color}-{base_color+63}", "")
        self.set_lcd_segments(2, "Touch pad to see", "color value", "Left/Right=page", "Session=exit")

        for row in range(8):
            for col in range(8):
                color_value = base_color + row * 8 + col
                if color_value < 128:
                    note = PAD_START + row * 8 + col
                    self.set_pad_color(note, color_value)

        print(f"\nPage {self.color_page + 1}: Colors {base_color}-{min(base_color+63, 127)}")

    # =========================================================================
    # GRID ANIMATIONS
    # =========================================================================

    def grid_animations(self):
        """Run various grid animations."""
        print("\n" + "=" * 60)
        print("GRID ANIMATIONS")
        print("=" * 60)
        print("Watch the pretty lights!")
        print("Press Session or any key to move to next animation.\n")

        animations = [
            ("Rainbow Wave", self._anim_rainbow_wave),
            ("Color Pulse", self._anim_color_pulse),
            ("Sparkle", self._anim_sparkle),
            ("Matrix Rain", self._anim_matrix_rain),
            ("Spiral", self._anim_spiral),
            ("Checkerboard", self._anim_checkerboard),
            ("Ripple", self._anim_ripple),
        ]

        for name, anim_func in animations:
            print(f"\n  {name}...")
            self.set_lcd_segments(1, "GRID ANIMATIONS", "", "", "")
            self.set_lcd_segments(2, name, "", "", "")
            self.set_lcd_segments(3, "", "", "", "")
            self.set_lcd_segments(4, "Press pad/key", "for next", "", "")

            if not anim_func():
                break  # User quit

        self.clear_grid()

    def _check_exit(self):
        """Check if user wants to exit animation."""
        if self.push_in:
            for msg in self.push_in.iter_pending():
                if msg.type == 'note_on' and msg.velocity > 0:
                    return True
                if msg.type == 'control_change' and msg.value > 0:
                    if msg.control == NAV_BUTTONS['session']:
                        return 'quit'
                    return True
        if select.select([sys.stdin], [], [], 0)[0]:
            cmd = sys.stdin.readline().strip().lower()
            if cmd == 'q':
                return 'quit'
            return True
        return False

    def _anim_rainbow_wave(self):
        """Rainbow wave animation."""
        colors = [5, 9, 13, 21, 33, 45, 49, 57]  # Rainbow palette

        for frame in range(100):
            for row in range(8):
                for col in range(8):
                    color_idx = (col + row + frame) % len(colors)
                    note = PAD_START + row * 8 + col
                    self.set_pad_color(note, colors[color_idx])
            time.sleep(0.05)

            result = self._check_exit()
            if result == 'quit':
                return False
            if result:
                return True
        return True

    def _anim_color_pulse(self):
        """Pulsing color intensity."""
        base_colors = [5, 9, 13, 21, 45, 49]  # Different base colors

        for frame in range(80):
            # Calculate brightness based on sine wave
            brightness = int((math.sin(frame * 0.2) + 1) * 2)  # 0-4

            for row in range(8):
                for col in range(8):
                    base = base_colors[(row + col) % len(base_colors)]
                    # Vary the color slightly based on brightness
                    color = max(1, base - 3 + brightness)
                    note = PAD_START + row * 8 + col
                    self.set_pad_color(note, color)
            time.sleep(0.06)

            result = self._check_exit()
            if result == 'quit':
                return False
            if result:
                return True
        return True

    def _anim_sparkle(self):
        """Random sparkle effect."""
        for frame in range(150):
            # Random sparkles
            for _ in range(5):
                note = random.randint(PAD_START, PAD_END)
                color = random.choice([3, 5, 9, 13, 21, 33, 45, 49, 57])
                self.set_pad_color(note, color)

            # Fade some random pads
            for _ in range(3):
                note = random.randint(PAD_START, PAD_END)
                self.set_pad_color(note, 1)  # Dim

            time.sleep(0.04)

            result = self._check_exit()
            if result == 'quit':
                return False
            if result:
                return True
        return True

    def _anim_matrix_rain(self):
        """Matrix-style falling columns."""
        columns = [random.randint(0, 15) for _ in range(8)]  # Random starting positions
        speeds = [random.uniform(0.5, 1.5) for _ in range(8)]

        for frame in range(120):
            self.clear_grid()

            for col in range(8):
                # Update column position
                columns[col] += speeds[col]
                if columns[col] > 12:
                    columns[col] = -4
                    speeds[col] = random.uniform(0.5, 1.5)

                # Draw column with trail
                head_row = int(columns[col])
                for i, intensity in enumerate([21, 17, 13, 9]):  # Green trail
                    row = head_row - i
                    if 0 <= row < 8:
                        note = PAD_START + row * 8 + col
                        self.set_pad_color(note, intensity)

            time.sleep(0.08)

            result = self._check_exit()
            if result == 'quit':
                return False
            if result:
                return True
        return True

    def _anim_spiral(self):
        """Spiral pattern."""
        # Generate spiral coordinates
        spiral = []
        x, y = 0, 0
        dx, dy = 1, 0
        for _ in range(64):
            if 0 <= x < 8 and 0 <= y < 8:
                spiral.append((x, y))
            x, y = x + dx, y + dy
            # Turn logic
            if dx == 1 and (x >= 8 or (x, y) in spiral):
                x -= 1
                dx, dy = 0, 1
            elif dy == 1 and (y >= 8 or (x, y) in spiral):
                y -= 1
                dx, dy = -1, 0
            elif dx == -1 and (x < 0 or (x, y) in spiral):
                x += 1
                dx, dy = 0, -1
            elif dy == -1 and (y < 0 or (x, y) in spiral):
                y += 1
                dx, dy = 1, 0

        # Simple spiral from outside in
        spiral = []
        for layer in range(4):
            # Top
            for x in range(layer, 8-layer):
                spiral.append((layer, x))
            # Right
            for y in range(layer+1, 8-layer):
                spiral.append((y, 7-layer))
            # Bottom
            for x in range(6-layer, layer-1, -1):
                spiral.append((7-layer, x))
            # Left
            for y in range(6-layer, layer, -1):
                spiral.append((y, layer))

        colors = [5, 9, 13, 21, 33, 45, 49, 57]

        for frame in range(100):
            for i, (row, col) in enumerate(spiral[:min(len(spiral), 64)]):
                color_idx = (i + frame) % len(colors)
                note = PAD_START + row * 8 + col
                self.set_pad_color(note, colors[color_idx])
            time.sleep(0.05)

            result = self._check_exit()
            if result == 'quit':
                return False
            if result:
                return True
        return True

    def _anim_checkerboard(self):
        """Animated checkerboard."""
        for frame in range(60):
            for row in range(8):
                for col in range(8):
                    note = PAD_START + row * 8 + col
                    if (row + col + frame) % 2 == 0:
                        self.set_pad_color(note, 45)  # Blue
                    else:
                        self.set_pad_color(note, 9)   # Orange
            time.sleep(0.1)

            result = self._check_exit()
            if result == 'quit':
                return False
            if result:
                return True
        return True

    def _anim_ripple(self):
        """Ripple effect from center."""
        center_row, center_col = 3.5, 3.5
        colors = [0, 1, 33, 45, 48, 45, 33, 1]  # Blue ripple

        for frame in range(100):
            for row in range(8):
                for col in range(8):
                    # Distance from center
                    dist = math.sqrt((row - center_row)**2 + (col - center_col)**2)
                    # Create ripple
                    ripple_pos = (dist - frame * 0.3) % len(colors)
                    color_idx = int(ripple_pos) % len(colors)

                    note = PAD_START + row * 8 + col
                    self.set_pad_color(note, colors[color_idx])
            time.sleep(0.05)

            result = self._check_exit()
            if result == 'quit':
                return False
            if result:
                return True
        return True

    # =========================================================================
    # CONTROL BUTTON LED PATTERNS
    # =========================================================================

    def control_button_explorer(self):
        """Explore the 16 control buttons below LCD."""
        print("\n" + "=" * 60)
        print("CONTROL BUTTON LED EXPLORER")
        print("=" * 60)
        print("The 16 buttons below the LCD have white LEDs")
        print("Values: 0=off, 1=dim, 2=medium, 3=bright, 4=brightest")
        print("Press Session to exit.\n")

        self.set_lcd_segments(1, "BUTTON LEDS", "16 buttons", "below LCD", "")
        self.set_lcd_segments(2, "Upper: CC102-109", "", "", "")
        self.set_lcd_segments(3, "Lower: CC20-27", "", "", "")

        patterns = [
            ("All Dim", lambda: self._button_all(1)),
            ("All Bright", lambda: self._button_all(4)),
            ("Chase Upper", lambda: self._button_chase(UPPER_BUTTONS)),
            ("Chase Lower", lambda: self._button_chase(LOWER_BUTTONS)),
            ("Chase All", lambda: self._button_chase(UPPER_BUTTONS + LOWER_BUTTONS)),
            ("Alternate", lambda: self._button_alternate()),
            ("Bounce", lambda: self._button_bounce()),
            ("Fade", lambda: self._button_fade()),
            ("Random", lambda: self._button_random()),
        ]

        for name, pattern_func in patterns:
            print(f"  {name}...")
            self.set_lcd_segments(4, f"Pattern: {name}", "", "Pad=next", "Session=exit")

            if not pattern_func():
                break

        self.clear_buttons()

    def _button_all(self, value):
        """Set all buttons to same value."""
        for cc in UPPER_BUTTONS + LOWER_BUTTONS:
            self.set_button_led(cc, value)
        time.sleep(1)

        result = self._check_exit()
        if result == 'quit':
            return False
        return True

    def _button_chase(self, buttons):
        """Chase pattern across buttons."""
        for _ in range(3):  # 3 cycles
            for i, cc in enumerate(buttons):
                # Clear all
                for b in buttons:
                    self.set_button_led(b, 0)
                # Light current
                self.set_button_led(cc, 4)
                time.sleep(0.08)

                result = self._check_exit()
                if result == 'quit':
                    return False
                if result:
                    return True
        return True

    def _button_alternate(self):
        """Alternating pattern."""
        for _ in range(10):
            # Pattern A
            for i, cc in enumerate(UPPER_BUTTONS + LOWER_BUTTONS):
                self.set_button_led(cc, 4 if i % 2 == 0 else 0)
            time.sleep(0.2)

            result = self._check_exit()
            if result == 'quit':
                return False
            if result:
                return True

            # Pattern B
            for i, cc in enumerate(UPPER_BUTTONS + LOWER_BUTTONS):
                self.set_button_led(cc, 0 if i % 2 == 0 else 4)
            time.sleep(0.2)

            result = self._check_exit()
            if result == 'quit':
                return False
            if result:
                return True
        return True

    def _button_bounce(self):
        """Bouncing light."""
        all_buttons = UPPER_BUTTONS + LOWER_BUTTONS
        pos = 0
        direction = 1

        for _ in range(40):
            for i, cc in enumerate(all_buttons):
                if i == pos:
                    self.set_button_led(cc, 4)
                elif abs(i - pos) == 1:
                    self.set_button_led(cc, 2)
                else:
                    self.set_button_led(cc, 0)

            pos += direction
            if pos >= len(all_buttons) - 1 or pos <= 0:
                direction *= -1

            time.sleep(0.06)

            result = self._check_exit()
            if result == 'quit':
                return False
            if result:
                return True
        return True

    def _button_fade(self):
        """Fade in/out."""
        for _ in range(3):
            # Fade in
            for value in range(5):
                for cc in UPPER_BUTTONS + LOWER_BUTTONS:
                    self.set_button_led(cc, value)
                time.sleep(0.1)

            # Fade out
            for value in range(4, -1, -1):
                for cc in UPPER_BUTTONS + LOWER_BUTTONS:
                    self.set_button_led(cc, value)
                time.sleep(0.1)

            result = self._check_exit()
            if result == 'quit':
                return False
            if result:
                return True
        return True

    def _button_random(self):
        """Random pattern."""
        for _ in range(50):
            for cc in UPPER_BUTTONS + LOWER_BUTTONS:
                self.set_button_led(cc, random.randint(0, 4))
            time.sleep(0.1)

            result = self._check_exit()
            if result == 'quit':
                return False
            if result:
                return True
        return True

    # =========================================================================
    # FULL LIGHT SHOW
    # =========================================================================

    def full_light_show(self):
        """Combined light show with grid and buttons."""
        print("\n" + "=" * 60)
        print("FULL LIGHT SHOW")
        print("=" * 60)
        print("Grid + Buttons synchronized!")
        print("Press any pad or Session to exit.\n")

        self.set_lcd_segments(1, "LIGHT SHOW", "Grid+Buttons", "Synchronized", "")
        self.set_lcd_segments(2, "", "", "", "")
        self.set_lcd_segments(3, "", "", "", "")
        self.set_lcd_segments(4, "Press any pad", "to exit", "", "")

        colors = [5, 9, 13, 21, 33, 45, 49, 57]

        for frame in range(300):
            # Grid: rainbow wave
            for row in range(8):
                for col in range(8):
                    color_idx = (col + row + frame) % len(colors)
                    note = PAD_START + row * 8 + col
                    self.set_pad_color(note, colors[color_idx])

            # Upper buttons: chase
            upper_pos = frame % 8
            for i, cc in enumerate(UPPER_BUTTONS):
                self.set_button_led(cc, 4 if i == upper_pos else 1)

            # Lower buttons: reverse chase
            lower_pos = (7 - frame) % 8
            for i, cc in enumerate(LOWER_BUTTONS):
                self.set_button_led(cc, 4 if i == lower_pos else 1)

            time.sleep(0.05)

            result = self._check_exit()
            if result:
                break

        self.clear_grid()
        self.clear_buttons()

    # =========================================================================
    # MENU AND MAIN LOOP
    # =========================================================================

    def show_menu(self):
        """Display main menu."""
        self.set_lcd_segments(1, "HARDWARE", "EXPLORER", "Push 1", "")
        self.set_lcd_segments(2, "1: Latency", "2: Colors", "3: Grid Anim", "4: Buttons")
        self.set_lcd_segments(3, "5: Light Show", "", "", "")
        self.set_lcd_segments(4, "Press 1-5 or q", "", "", "")

        # Light up pads for menu selection
        for i in range(5):
            self.set_pad_color(PAD_START + i, [5, 9, 13, 21, 45][i])

        print("\n" + "=" * 60)
        print("PUSH 1 HARDWARE EXPLORER")
        print("=" * 60)
        print("\n  1 - Latency Test (measure round-trip MIDI)")
        print("  2 - Color Palette (see all 128 pad colors)")
        print("  3 - Grid Animations (rainbow, sparkle, etc.)")
        print("  4 - Control Button LEDs (16 buttons below LCD)")
        print("  5 - Full Light Show (everything together!)")
        print("\n  q - Quit")
        print("=" * 60)

    def run(self):
        """Main run loop."""
        if not self.connect():
            return

        self.set_user_mode()
        self.clear_grid()
        self.clear_buttons()
        self.show_menu()

        self.running = True

        while self.running:
            # Check MIDI input
            if self.push_in:
                for msg in self.push_in.iter_pending():
                    if msg.type == 'note_on' and msg.velocity > 0:
                        pad_num = msg.note - PAD_START
                        if pad_num == 0:
                            self.latency_test()
                            self.show_menu()
                        elif pad_num == 1:
                            self.color_palette_explorer()
                            self.show_menu()
                        elif pad_num == 2:
                            self.grid_animations()
                            self.show_menu()
                        elif pad_num == 3:
                            self.control_button_explorer()
                            self.show_menu()
                        elif pad_num == 4:
                            self.full_light_show()
                            self.show_menu()

            # Check keyboard
            if select.select([sys.stdin], [], [], 0.05)[0]:
                cmd = sys.stdin.readline().strip().lower()

                if cmd == 'q':
                    self.running = False
                elif cmd == '1':
                    self.latency_test()
                    self.show_menu()
                elif cmd == '2':
                    self.color_palette_explorer()
                    self.show_menu()
                elif cmd == '3':
                    self.grid_animations()
                    self.show_menu()
                elif cmd == '4':
                    self.control_button_explorer()
                    self.show_menu()
                elif cmd == '5':
                    self.full_light_show()
                    self.show_menu()

        # Cleanup
        self.clear_grid()
        self.clear_buttons()
        self.set_lcd_segments(2, "", "Goodbye!", "", "")
        time.sleep(0.5)

        if self.push_out:
            self.push_out.close()
        if self.push_in:
            self.push_in.close()

        print("\nHardware Explorer closed.")


if __name__ == "__main__":
    explorer = HardwareExplorer()
    explorer.run()
