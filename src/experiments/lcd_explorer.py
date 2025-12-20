#!/usr/bin/env python3
"""
LCD Explorer for Push 1

Explore the capabilities of Push 1's character LCD display.
- Full character set (0-127) - DISCOVERY: Char 2 (STX) = solid block!
- Animation speed testing
- Pseudo-graphics experiments (VU meters, progress bars)
- Segment-aware display (17 chars per segment, no word cutting)

Usage:
    python3 src/experiments/lcd_explorer.py

HARDWARE CONTROLS (Push 1 pads - bottom row):
    Pad 1 (red):    Cycle character set (0-127)
    Pad 2 (orange): Explore special chars (0-31)
    Pad 3 (yellow): VU meter demo
    Pad 4 (green):  Animation speed test
    Pad 5 (cyan):   Scrolling text demo
    Pad 6 (blue):   Grid pattern demo
    Pad 7 (purple): Progress bar demo
    Pad 8 (pink):   Waveform demo

    Note button:    Show segment layout
    Session button: Return to menu

KEYBOARD CONTROLS:
    c: Cycle chars  x: Special chars  b: VU meter  a: Animation
    s: Scroll       g: Grid           p: Progress  w: Waveform
    l: Layout       r: Reset menu     q: Quit
"""

import mido
import time
import math
import sys
import select

# Push 1 SysEx header
SYSEX_HEADER = [0x47, 0x7F, 0x15]

# LCD line addresses
LCD_LINES = {1: 0x18, 2: 0x19, 3: 0x1A, 4: 0x1B}

# Segment configuration
CHARS_PER_LINE = 68
CHARS_PER_SEGMENT = 17
NUM_SEGMENTS = 4

# Hardware button CCs (from Push 2 mapping - same as Push 1)
BUTTONS = {
    # Lower row below LCD (CC 20-27) - Use for demo selection
    'lower_1': 20, 'lower_2': 21, 'lower_3': 22, 'lower_4': 23,
    'lower_5': 24, 'lower_6': 25, 'lower_7': 26, 'lower_8': 27,
    # Upper row below LCD (CC 102-109)
    'upper_1': 102, 'upper_2': 103, 'upper_3': 104, 'upper_4': 105,
    'upper_5': 106, 'upper_6': 107, 'upper_7': 108, 'upper_8': 109,
    # Navigation
    'left': 44, 'right': 45, 'up': 46, 'down': 47,
    'page_left': 62, 'page_right': 63,
    # Mode buttons
    'note': 50, 'session': 51,
    'octave_down': 54, 'octave_up': 55,
}

# Pad grid (Notes 36-99)
PAD_START = 36
PAD_END = 99

# LED colors (velocity values)
COLORS = {
    'off': 0, 'dim_white': 1, 'white': 3,
    'red': 5, 'orange': 9, 'yellow': 13,
    'green': 21, 'cyan': 33, 'blue': 45,
    'purple': 49, 'pink': 57,
}


class LCDExplorer:
    def __init__(self):
        self.push_out = None
        self.push_in = None
        self.running = False
        self.current_char = 32  # Start at space
        self.animation_running = False
        self.current_demo = None  # Track which demo is running

    def connect(self):
        """Connect to Push 1 User Port (input and output)."""
        # Find output port
        for port_name in mido.get_output_names():
            if 'Ableton Push' in port_name and 'User' in port_name:
                self.push_out = mido.open_output(port_name)
                print(f"Output: {port_name}")
                break

        # Find input port
        for port_name in mido.get_input_names():
            if 'Ableton Push' in port_name and 'User' in port_name:
                self.push_in = mido.open_input(port_name)
                print(f"Input: {port_name}")
                break

        if self.push_out and self.push_in:
            print("Connected to Push 1!")
            return True

        print("ERROR: Push 1 User Port not found")
        print("Output ports:", mido.get_output_names())
        print("Input ports:", mido.get_input_names())
        return False

    def send_sysex(self, data):
        """Send SysEx message to Push."""
        if self.push_out:
            self.push_out.send(mido.Message('sysex', data=SYSEX_HEADER + data))

    def set_pad_color(self, note, color):
        """Set pad LED color."""
        if self.push_out and PAD_START <= note <= PAD_END:
            self.push_out.send(mido.Message('note_on', note=note, velocity=color))

    def set_button_led(self, cc, value):
        """Set button LED (0=off, 1=dim, 4=bright)."""
        if self.push_out:
            self.push_out.send(mido.Message('control_change', control=cc, value=value))

    def set_user_mode(self):
        """Switch Push to User Mode."""
        self.send_sysex([0x62, 0x00, 0x01, 0x01])
        time.sleep(0.1)

    def set_lcd_line(self, line, text):
        """Set a full LCD line (68 characters)."""
        if line not in LCD_LINES:
            return

        # Pad or truncate to exactly 68 characters
        text = text[:CHARS_PER_LINE].ljust(CHARS_PER_LINE)

        line_addr = LCD_LINES[line]
        data = [line_addr, 0x00, 0x45, 0x00]
        data.extend([ord(c) if isinstance(c, str) else c for c in text])
        self.send_sysex(data)

    def set_lcd_raw(self, line, char_values):
        """Set LCD line with raw byte values (0-127)."""
        if line not in LCD_LINES:
            return

        # Pad to 68 values
        while len(char_values) < CHARS_PER_LINE:
            char_values.append(32)  # space
        char_values = char_values[:CHARS_PER_LINE]

        line_addr = LCD_LINES[line]
        data = [line_addr, 0x00, 0x45, 0x00]
        data.extend(char_values)
        self.send_sysex(data)

    def set_lcd_segments(self, line, seg0="", seg1="", seg2="", seg3=""):
        """Set LCD line with 4 segments (17 chars each).

        Each segment is padded/truncated to exactly 17 characters.
        Text stays within segment boundaries - no word cutting across gaps.

        Args:
            line: Line number (1-4)
            seg0-seg3: Text for each segment (max 17 chars each)
        """
        if line not in LCD_LINES:
            return

        segments = [seg0, seg1, seg2, seg3]
        text = ""
        for seg in segments:
            # Truncate to 17 chars, left-justify (pad right with spaces)
            text += seg[:CHARS_PER_SEGMENT].ljust(CHARS_PER_SEGMENT)

        line_addr = LCD_LINES[line]
        data = [line_addr, 0x00, 0x45, 0x00]
        data.extend([ord(c) for c in text])
        self.send_sysex(data)

    def set_lcd_segments_centered(self, line, seg0="", seg1="", seg2="", seg3=""):
        """Set LCD line with 4 centered segments (17 chars each)."""
        if line not in LCD_LINES:
            return

        segments = [seg0, seg1, seg2, seg3]
        text = ""
        for seg in segments:
            # Center within 17 chars
            text += seg[:CHARS_PER_SEGMENT].center(CHARS_PER_SEGMENT)

        line_addr = LCD_LINES[line]
        data = [line_addr, 0x00, 0x45, 0x00]
        data.extend([ord(c) for c in text])
        self.send_sysex(data)

    def clear_display(self):
        """Clear all LCD lines."""
        for line in range(1, 5):
            self.set_lcd_line(line, "")

    def show_character_set(self, start=0, count=68):
        """Display a range of the character set."""
        chars = list(range(start, min(start + count, 128)))
        while len(chars) < 68:
            chars.append(32)

        self.set_lcd_line(1, f"Character Set: {start:3d} - {min(start+count-1, 127):3d}")
        self.set_lcd_line(2, "-" * 68)
        self.set_lcd_raw(3, chars)

        # Show hex values below
        hex_line = ""
        for i in range(min(17, count)):
            hex_line += f"{(start + i):02X} "
        self.set_lcd_line(4, hex_line)

    def cycle_character_set(self):
        """Cycle through the entire character set."""
        print("\nCycling through character set (0-127)")
        print("Press Enter to advance, 'q' to stop\n")

        for start in range(0, 128, 17):
            self.show_character_set(start, 17)
            print(f"Showing characters {start} - {min(start+16, 127)}")

            user_input = input("Enter to continue, 'q' to quit: ")
            if user_input.lower() == 'q':
                break

    def explore_special_chars(self):
        """Explore special characters 0-31 one at a time with large display."""
        print("\n=== Special Character Explorer (0-31) ===")
        print("These are the 'control code' range that display as graphics on Push 1")
        print("Press Enter to advance, type a description, or 'q' to quit\n")

        # Known characters so far
        known = {
            2: "SOLID BLOCK █",
        }

        discoveries = {}

        for char_code in range(32):  # 0-31
            # Display the character prominently
            # Line 1: Header
            self.set_lcd_line(1, f"Character {char_code:3d} (0x{char_code:02X})".center(68))

            # Line 2: Show the character repeated many times for visibility
            char_row = [char_code] * 68
            self.set_lcd_raw(2, char_row)

            # Line 3: Show alternating with spaces for comparison
            alt_row = []
            for _ in range(34):
                alt_row.extend([char_code, 32])  # char, space, char, space...
            self.set_lcd_raw(3, alt_row)

            # Line 4: Mix with known solid block for comparison
            compare_row = [2] * 17 + [32] * 2 + [char_code] * 17 + [32] * 2 + [2] * 17 + [32] * 2 + [char_code] * 11
            self.set_lcd_raw(4, compare_row)

            # Console output
            known_desc = known.get(char_code, "???")
            print(f"Char {char_code:2d} (0x{char_code:02X}): {known_desc}")
            print("  Line 2: Character repeated 68x")
            print("  Line 3: Alternating with spaces")
            print("  Line 4: Compared with solid block (char 2)")

            user_input = input("  Description (or Enter to skip, 'q' to quit): ").strip()

            if user_input.lower() == 'q':
                break
            elif user_input:
                discoveries[char_code] = user_input
                print(f"  Recorded: {user_input}")

        # Summary
        print("\n=== Discovery Summary ===")
        print("Known characters:")
        for code, desc in known.items():
            print(f"  {code:2d} (0x{code:02X}): {desc}")
        if discoveries:
            print("\nYour discoveries:")
            for code, desc in sorted(discoveries.items()):
                print(f"  {code:2d} (0x{code:02X}): {desc}")

        return discoveries

    def animation_speed_test(self):
        """Test how fast the display can update."""
        print("\nAnimation Speed Test")
        print("Testing update rates...\n")

        self.animation_running = True

        # Test different update speeds
        test_rates = [0.1, 0.05, 0.02, 0.01, 0.005]

        for rate in test_rates:
            if not self.animation_running:
                break

            print(f"Testing {1/rate:.0f} updates/second (delay: {rate*1000:.0f}ms)")

            frames = 0
            start_time = time.time()

            while time.time() - start_time < 2.0 and self.animation_running:
                # Simple scrolling animation
                offset = frames % 68
                line = " " * offset + ">>>SCROLLING>>>" + " " * 68
                self.set_lcd_line(2, line[:68])
                frames += 1
                time.sleep(rate)

            actual_fps = frames / (time.time() - start_time)
            print(f"  Achieved: {actual_fps:.1f} fps\n")

        self.animation_running = False
        print("Animation test complete")

    def vu_meter_demo(self):
        """Demo VU meter testing raw character codes for solid blocks."""
        print("\nVU Meter Demo - Testing Block Characters")
        print("Press 1-9 to try different block chars, q to quit\n")

        self.animation_running = True

        # DISCOVERY: Character code 2 (STX) is a solid block on Push 1 LCD!
        # Other candidates listed for reference/testing
        block_candidates = [
            (2, "STX (2) SOLID"),    # *** SOLID BLOCK - USE THIS ***
            (1, "SOH (1)"),          # Special char
            (3, "ETX (3)"),          # Special char
            (4, "EOT (4)"),          # Special char
            (5, "ENQ (5)"),          # Special char
            (6, "ACK (6)"),          # Special char
            (7, "BEL (7)"),          # Special char
            (127, "DEL (127)"),      # Often solid in some LCDs
            (35, "# (35)"),          # Hash - fallback
        ]

        current_block_idx = 0  # Start with STX (solid block)
        block_char = block_candidates[current_block_idx][0]
        space_char = 32  # Space for empty part

        frame = 0
        while self.animation_running:
            block_name = block_candidates[current_block_idx][1]
            self.set_lcd_line(1, f"VU Meter - Block: {block_name}".ljust(68))

            # Simulate stereo levels (0-60 to leave room for labels)
            level_l = int(abs(math.sin(frame * 0.1)) * 60)
            level_r = int(abs(math.cos(frame * 0.15)) * 60)

            # Build meter bars using raw bytes
            meter_l = [ord('L'), ord(':')] + [block_char] * level_l + [space_char] * (60 - level_l) + [ord(' ')] * 6
            meter_r = [ord('R'), ord(':')] + [block_char] * level_r + [space_char] * (60 - level_r) + [ord(' ')] * 6

            self.set_lcd_raw(2, meter_l)
            self.set_lcd_raw(3, meter_r)

            # Show values and instructions
            self.set_lcd_line(4, f"L:{level_l:2d} R:{level_r:2d}  [1-9]=chars [n/p]=next/prev [q]=quit")

            frame += 1
            time.sleep(0.05)

            # Auto-cycle through blocks every 3 seconds
            if frame % 60 == 0:
                current_block_idx = (current_block_idx + 1) % len(block_candidates)
                block_char = block_candidates[current_block_idx][0]
                print(f"Trying: {block_candidates[current_block_idx][1]}")

            if frame > 600:  # Auto-stop after ~30 seconds
                break

        self.animation_running = False
        print("\nVU meter demo complete")

    def scrolling_text_demo(self):
        """Demo scrolling text."""
        print("\nScrolling Text Demo")

        text = "    Welcome to Push 1 LCD Explorer! This text scrolls across the display. The Push 1 has a 4-line character LCD with 68 characters per line, divided into 4 segments of 17 characters each.    "

        self.set_lcd_line(1, "=" * 68)
        self.set_lcd_line(4, "=" * 68)

        for i in range(len(text) - 68 + 1):
            self.set_lcd_line(2, text[i:i+68])
            self.set_lcd_line(3, " " * 20 + "SCROLLING TEXT DEMO" + " " * 29)
            time.sleep(0.08)

        print("Scrolling complete")

    def grid_pattern_demo(self):
        """Demo grid/pattern display using characters."""
        print("\nGrid Pattern Demo")

        patterns = [
            # Checkerboard
            ("Checkerboard", lambda x, y: "#" if (x + y) % 2 == 0 else " "),
            # Diagonal
            ("Diagonal Lines", lambda x, y: "/" if (x + y) % 4 == 0 else " "),
            # Dots
            ("Dot Grid", lambda x, y: "." if x % 4 == 0 and y % 2 == 0 else " "),
            # Blocks
            ("Block Pattern", lambda x, y: "#" if x % 8 < 4 else "-"),
        ]

        for name, pattern_func in patterns:
            self.set_lcd_line(1, f"Pattern: {name}".center(68))

            for line in range(2, 5):
                row = ""
                for x in range(68):
                    row += pattern_func(x, line - 2)
                self.set_lcd_line(line, row)

            time.sleep(2)

        print("Pattern demo complete")

    def progress_bar_demo(self):
        """Demo progress bar."""
        print("\nProgress Bar Demo")

        self.set_lcd_line(1, "Progress Bar Demo".center(68))
        self.set_lcd_line(4, "")

        for progress in range(101):
            # Calculate bar width (using 60 chars for the bar)
            bar_width = 60
            filled = int(progress / 100 * bar_width)

            bar = "[" + "=" * filled + ">" + " " * (bar_width - filled - 1) + "]"

            self.set_lcd_line(2, bar.center(68))
            self.set_lcd_line(3, f"{progress}% complete".center(68))

            time.sleep(0.03)

        self.set_lcd_line(3, "COMPLETE!".center(68))
        print("Progress bar complete")

    def waveform_demo(self):
        """Demo waveform-style visualization."""
        print("\nWaveform Visualization Demo")

        # Characters that might represent different heights
        # We'll use simple ASCII art approach
        wave_chars = " ._-~^"

        self.set_lcd_line(1, "Waveform Visualization".center(68))

        for frame in range(200):
            wave_line = ""
            for x in range(68):
                # Generate a wave pattern
                value = math.sin((x + frame) * 0.2) * 0.5 + 0.5
                char_idx = int(value * (len(wave_chars) - 1))
                wave_line += wave_chars[char_idx]

            self.set_lcd_line(2, wave_line)

            # Second wave (different frequency)
            wave_line2 = ""
            for x in range(68):
                value = math.sin((x + frame) * 0.3) * math.cos((x - frame) * 0.1) * 0.5 + 0.5
                char_idx = int(value * (len(wave_chars) - 1))
                wave_line2 += wave_chars[char_idx]

            self.set_lcd_line(3, wave_line2)

            self.set_lcd_line(4, f"Frame: {frame:3d}".center(68))

            time.sleep(0.05)

        print("Waveform demo complete")

    def game_watch_demo(self):
        """Game & Watch style animation demo - treat each segment as a mini screen."""
        print("\nGame & Watch Style Demo")
        print("Watch each segment for different animations!")
        print("Press any pad to exit\n")

        # Character codes
        BLOCK = 2      # Solid block (discovered!)
        SPACE = 32     # Empty
        DOT = ord('.')
        PIPE = ord('|')
        DASH = ord('-')

        def make_runner(frame, width=17):
            """Simple running figure that moves across segment."""
            pos = frame % (width - 3)
            line = [SPACE] * width
            # Simple stick figure: o/\ or o|
            if frame % 4 < 2:
                # Running pose 1
                if pos < width - 1:
                    line[pos] = ord('o')
                if pos + 1 < width:
                    line[pos + 1] = ord('/')
            else:
                # Running pose 2
                if pos < width - 1:
                    line[pos] = ord('o')
                if pos + 1 < width:
                    line[pos + 1] = ord('\\')
            return line

        def make_bouncing_ball(frame, width=17, height=4):
            """Ball bouncing - returns 4 lines for the segment column."""
            # Ball position oscillates
            x = int((math.sin(frame * 0.15) + 1) * (width - 2) / 2)
            y = int((math.sin(frame * 0.2) + 1) * (height - 1) / 2)

            lines = []
            for row in range(height):
                line = [SPACE] * width
                if row == y:
                    line[x] = BLOCK
                    # Add shadow/trail
                    if x > 0:
                        line[x - 1] = DOT
                lines.append(line)
            return lines

        def make_pong(frame, width=17):
            """Simple pong - ball bounces, paddle follows."""
            # Ball position
            ball_x = int((math.sin(frame * 0.1) + 1) * (width - 4) / 2) + 1
            ball_y = int((math.sin(frame * 0.15) + 1) * 2)  # 0, 1, or 2

            # Paddle follows ball roughly
            paddle_y = min(2, max(0, ball_y))

            lines = []
            for row in range(4):
                line = [SPACE] * width
                # Left paddle (always at x=0)
                if row in [paddle_y, paddle_y + 1]:
                    line[0] = BLOCK
                # Ball
                if row == ball_y + 1:
                    line[ball_x] = BLOCK
                # Right paddle
                if row in [paddle_y, paddle_y + 1]:
                    line[width - 1] = BLOCK
                lines.append(line)
            return lines

        def make_rain(frame, width=17):
            """Falling rain drops."""
            lines = []
            for row in range(4):
                line = [SPACE] * width
                for col in range(width):
                    # Each column has rain at different phases
                    drop_phase = (frame + col * 3 + row * 7) % 12
                    if drop_phase < 1:
                        line[col] = PIPE
                    elif drop_phase < 2:
                        line[col] = DOT
                lines.append(line)
            return lines

        def make_heartbeat(frame, width=17):
            """Simple heartbeat/pulse line."""
            line = [DASH] * width
            # Pulse moves across
            pulse_pos = frame % width
            if pulse_pos < width:
                line[pulse_pos] = ord('^')
            if pulse_pos > 0:
                line[pulse_pos - 1] = ord('/')
            if pulse_pos < width - 1:
                line[pulse_pos + 1] = ord('\\')
            return line

        # Title line
        self.set_lcd_segments_centered(1, "GAME & WATCH", "Push 1 LCD", "4 Animations", "Press pad=exit")

        frame = 0
        self.animation_running = True

        while self.animation_running:
            # Check for pad press to exit
            if self.push_in:
                for msg in self.push_in.iter_pending():
                    if msg.type == 'note_on' and msg.velocity > 0:
                        self.animation_running = False
                        break

            if not self.animation_running:
                break

            # Segment 0: Bouncing ball (uses all 4 lines worth but we show line 2)
            ball_lines = make_bouncing_ball(frame)

            # Segment 1: Pong game
            pong_lines = make_pong(frame)

            # Segment 2: Rain
            rain_lines = make_rain(frame)

            # Segment 3: Runner on line 3, heartbeat on line 2
            runner = make_runner(frame)
            heartbeat = make_heartbeat(frame)

            # Compose each line from 4 segments
            # Line 2: ball[1], pong[1], rain[1], heartbeat
            line2_raw = ball_lines[1] + pong_lines[1] + rain_lines[1] + heartbeat[:11]
            self.set_lcd_raw(2, line2_raw)

            # Line 3: ball[2], pong[2], rain[2], runner
            line3_raw = ball_lines[2] + pong_lines[2] + rain_lines[2] + runner[:11]
            self.set_lcd_raw(3, line3_raw)

            # Line 4: Labels
            self.set_lcd_segments(4, "  Bounce", "   Pong", "   Rain", " Run+Pulse")

            frame += 1
            time.sleep(0.08)

            if frame > 500:  # Auto-stop after ~40 seconds
                break

        self.animation_running = False
        print("Game & Watch demo complete")

    def show_segment_layout(self):
        """Show the segment layout clearly."""
        self.set_lcd_line(1, "|-Segment 0---|  |-Segment 1---|  |-Segment 2---|  |-Segment 3---|")
        self.set_lcd_line(2, "   17 chars      17 chars         17 chars         17 chars     ")
        self.set_lcd_line(3, "12345678901234567123456789012345671234567890123456712345678901234567")
        self.set_lcd_line(4, "       ^GAP^            ^GAP^            ^GAP^                   ")

    def init_hardware_ui(self):
        """Initialize hardware UI - light up demo selection buttons."""
        # Light up lower row buttons (CC 20-27) for 8 demos
        demo_buttons = [20, 21, 22, 23, 24, 25, 26, 27]
        colors = [COLORS['red'], COLORS['orange'], COLORS['yellow'], COLORS['green'],
                  COLORS['cyan'], COLORS['blue'], COLORS['purple'], COLORS['pink']]

        for cc in demo_buttons:
            self.set_button_led(cc, 4)  # Bright

        # Light navigation buttons dimly
        for cc in [44, 45, 46, 47]:  # Left, Right, Up, Down
            self.set_button_led(cc, 1)  # Dim

        # Light bottom row pads (1-8) with demo colors
        for i in range(8):
            note = PAD_START + i  # Notes 36-43 (bottom row)
            self.set_pad_color(note, colors[i])

        # Light second row pad 1 (note 44) for Game & Watch demo - white
        self.set_pad_color(PAD_START + 8, COLORS['white'])

    def show_menu(self):
        """Display the main menu on the LCD using segment-aware formatting."""
        # Use segments to keep labels clean within boundaries
        self.set_lcd_segments_centered(1, "LCD Explorer", "Push 1", "Hardware+KB", "Controls")
        self.set_lcd_segments(2, "Pad1: Chars", "Pad2: Special", "Pad3: VU Meter", "Pad4: Animation")
        self.set_lcd_segments(3, "Pad5: Scroll", "Pad6: Grid", "Pad7: Progress", "Pad8: Waveform")
        self.set_lcd_segments(4, "Row2 Pad1: G&W", "Note: Layout", "Session: Menu", "KB: g=G&W q=Quit")

        print("\n" + "=" * 60)
        print("Push 1 LCD Explorer - Hardware + Keyboard Control")
        print("=" * 60)
        print("\nHARDWARE CONTROLS:")
        print("  Bottom row pads (1-8):")
        print("    Pad 1 (red)    - Cycle character set (0-127)")
        print("    Pad 2 (orange) - Explore special chars (0-31)")
        print("    Pad 3 (yellow) - VU meter demo")
        print("    Pad 4 (green)  - Animation speed test")
        print("    Pad 5 (cyan)   - Scrolling text demo")
        print("    Pad 6 (blue)   - Grid pattern demo")
        print("    Pad 7 (purple) - Progress bar demo")
        print("    Pad 8 (pink)   - Waveform demo")
        print("  Second row:")
        print("    Pad 9 (white)  - GAME & WATCH style demo!")
        print("\n  Note button    - Show segment layout")
        print("  Session button - Return to menu")
        print("\nKEYBOARD: c x b a s g p w m l r q (m=Game&Watch)")
        print("=" * 60)

    def handle_midi_input(self, msg):
        """Handle MIDI input from Push hardware."""
        if msg.type == 'note_on' and msg.velocity > 0:
            # Pad pressed - bottom row pads trigger demos
            if PAD_START <= msg.note < PAD_START + 8:
                pad_num = msg.note - PAD_START
                demos = [
                    self.cycle_character_set,      # Pad 1
                    self.explore_special_chars,    # Pad 2
                    self.vu_meter_demo,            # Pad 3
                    self.animation_speed_test,     # Pad 4
                    self.scrolling_text_demo,      # Pad 5
                    self.grid_pattern_demo,        # Pad 6
                    self.progress_bar_demo,        # Pad 7
                    self.waveform_demo,            # Pad 8
                ]
                print(f"\n[Pad {pad_num + 1} pressed]")
                demos[pad_num]()
                self.show_menu()
                self.init_hardware_ui()
                return True

            # Second row pad 1 (note 44) - Game & Watch demo
            elif msg.note == PAD_START + 8:
                print("\n[Pad 9 pressed - Game & Watch demo]")
                self.game_watch_demo()
                self.show_menu()
                self.init_hardware_ui()
                return True

        elif msg.type == 'control_change' and msg.value > 0:
            # Button pressed
            if msg.control == BUTTONS['note']:  # Note button
                print("\n[Note button - Segment layout]")
                self.show_segment_layout()
                return True
            elif msg.control == BUTTONS['session']:  # Session button
                print("\n[Session button - Menu]")
                self.show_menu()
                self.init_hardware_ui()
                return True
            elif msg.control == BUTTONS['left']:
                print("[Left]")
                return True
            elif msg.control == BUTTONS['right']:
                print("[Right]")
                return True

        return False

    def run(self):
        """Main run loop with hardware and keyboard input."""
        if not self.connect():
            return

        self.set_user_mode()
        self.init_hardware_ui()
        self.show_menu()

        self.running = True
        print("\nReady! Use Push pads or keyboard commands...")

        while self.running:
            try:
                # Check for MIDI input from Push (non-blocking)
                if self.push_in:
                    for msg in self.push_in.iter_pending():
                        self.handle_midi_input(msg)

                # Check for keyboard input (with timeout using select on Unix)
                if select.select([sys.stdin], [], [], 0.05)[0]:
                    cmd = sys.stdin.readline().strip().lower()

                    if cmd == 'q':
                        self.running = False
                    elif cmd == 'c':
                        self.cycle_character_set()
                        self.show_menu()
                        self.init_hardware_ui()
                    elif cmd == 'x':
                        self.explore_special_chars()
                        self.show_menu()
                        self.init_hardware_ui()
                    elif cmd == 'a':
                        self.animation_speed_test()
                        self.show_menu()
                        self.init_hardware_ui()
                    elif cmd == 'b':
                        self.vu_meter_demo()
                        self.show_menu()
                        self.init_hardware_ui()
                    elif cmd == 's':
                        self.scrolling_text_demo()
                        self.show_menu()
                        self.init_hardware_ui()
                    elif cmd == 'g':
                        self.grid_pattern_demo()
                        self.show_menu()
                        self.init_hardware_ui()
                    elif cmd == 'p':
                        self.progress_bar_demo()
                        self.show_menu()
                        self.init_hardware_ui()
                    elif cmd == 'w':
                        self.waveform_demo()
                        self.show_menu()
                        self.init_hardware_ui()
                    elif cmd == 'm':
                        self.game_watch_demo()
                        self.show_menu()
                        self.init_hardware_ui()
                    elif cmd == 'l':
                        self.show_segment_layout()
                    elif cmd == 'r':
                        self.show_menu()
                        self.init_hardware_ui()
                    elif cmd:
                        print("Unknown. Try: c x b a s g p w m l r q (or use Push pads)")

            except KeyboardInterrupt:
                print("\nInterrupted")
                self.animation_running = False
                self.running = False

        # Clean up
        self.clear_display()
        self.set_lcd_segments_centered(2, "", "Goodbye!", "", "")
        time.sleep(0.5)

        # Turn off LEDs
        for cc in [20, 21, 22, 23, 24, 25, 26, 27, 44, 45, 46, 47]:
            self.set_button_led(cc, 0)
        # Turn off second row pad too
        self.set_pad_color(PAD_START + 8, 0)
        for note in range(PAD_START, PAD_START + 8):
            self.set_pad_color(note, 0)

        if self.push_out:
            self.push_out.close()
        if self.push_in:
            self.push_in.close()

        print("\nLCD Explorer closed.")


if __name__ == "__main__":
    explorer = LCDExplorer()
    explorer.run()
