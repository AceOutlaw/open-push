#!/usr/bin/env python3
"""
Minimal test app: Just sampler step add/delete on Push.

Only features:
- Connect to Push and Seqtrak
- 8x8 pad grid for 16 steps × 7 samples
- Press pad = toggle step
- Show which command we're sending vs what Seqtrak sends back
"""

import mido
import sys
import time

# Find Push
push_ports = [p for p in mido.get_output_names() if 'Ableton Push' in p and 'User' in p]
if not push_ports:
    print("❌ Push not found!")
    sys.exit(1)

push_out = mido.open_output(push_ports[0])
push_in = mido.open_input([p for p in mido.get_input_names() if 'Ableton Push' in p and 'User' in p][0])
print(f"✓ Push: {push_ports[0]}")

# Find Seqtrak
seqtrak_ports = [p for p in mido.get_output_names() if 'SEQTRAK' in p]
if not seqtrak_ports:
    print("❌ Seqtrak not found!")
    sys.exit(1)

seqtrak_out = mido.open_output(seqtrak_ports[0])
seqtrak_in = mido.open_input([p for p in mido.get_input_names() if 'SEQTRAK' in p][0])
print(f"✓ Seqtrak: {seqtrak_ports[0]}")

# Seqtrak SysEx header
SYSEX_HEADER = [0x43, 0x10, 0x7F, 0x1C, 0x0C]

# Push control
PUSH_SYSEX_HEADER = [0x47, 0x7F, 0x15]

# State tracking
step_states = {}  # {(pad_idx, step_idx): bool}

# Colors
COLOR_OFF = 0
COLOR_DIM = 1
COLOR_WHITE = 3
COLOR_RED = 5
COLOR_GREEN = 21
COLOR_BLUE = 45

def send_sysex_to_seqtrak(command_bytes, data_bytes):
    """Send SysEx to Seqtrak and log it."""
    sysex = SYSEX_HEADER + command_bytes + data_bytes
    hex_str = " ".join(f"{b:02X}" for b in sysex)
    print(f"→ SEND: F0 {hex_str} F7")
    seqtrak_out.send(mido.Message('sysex', data=sysex))

def init_push():
    """Initialize Push to User Mode."""
    print("\nInitializing Push...")
    # User mode
    push_out.send(mido.Message('sysex', data=PUSH_SYSEX_HEADER + [0x62, 0x00, 0x01, 0x01]))
    time.sleep(0.1)

    # Light up all pads dim white
    for note in range(36, 100):
        push_out.send(mido.Message('note_on', note=note, velocity=COLOR_DIM))

    print("✓ Push initialized (all pads dim white)")

def toggle_step(pad_index, step_index):
    """Toggle a sampler step."""
    key = (pad_index, step_index)
    current_state = step_states.get(key, False)
    new_state = not current_state
    step_states[key] = new_state

    # Calculate pad note for LED feedback
    row = step_index // 8  # Steps 0-7 = row 0, steps 8-15 = row 1
    col = step_index % 8
    pad_note = 36 + (row * 8) + col

    # Update Push LED
    if new_state:
        push_out.send(mido.Message('note_on', note=pad_note, velocity=COLOR_GREEN))
    else:
        push_out.send(mido.Message('note_on', note=pad_note, velocity=COLOR_DIM))

    # Build SysEx
    sample_note = 0x3C + pad_index  # C4 + pad offset
    tick = 0x00

    print(f"\n{'='*60}")
    print(f"Sample {pad_index + 1}, Step {step_index + 1}: {new_state}")
    print(f"{'='*60}")

    # Select sampler element
    print(f"1. SELECT element {pad_index}")
    send_sysex_to_seqtrak([0x01, 0x10, 0x28], [pad_index])
    time.sleep(0.05)

    if new_state:
        # ADD: 72 30 00
        print(f"2. ADD step")
        cmd = [0x72, 0x30, 0x00]
        data = [step_index, tick, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]
        send_sysex_to_seqtrak(cmd, data)
    else:
        # DELETE: 74 73 00
        print(f"2. DELETE step")
        cmd = [0x74, 0x73, 0x00]
        data = [step_index, tick, 0x00, sample_note, 0x64, 0x00, 0x00, 0x78]
        send_sysex_to_seqtrak(cmd, data)

def handle_seqtrak_message(msg):
    """Log incoming Seqtrak messages."""
    if msg.type == 'sysex':
        hex_str = " ".join(f"{b:02X}" for b in msg.data)
        print(f"← RECV: F0 {hex_str} F7")

def handle_push_message(msg):
    """Handle Push pad presses."""
    if msg.type == 'note_on' and msg.velocity > 0:
        note = msg.note
        if 36 <= note < 52:  # First 2 rows only (16 steps)
            step_index = note - 36  # 0-15
            pad_index = 0  # Default to sample 1 for now
            toggle_step(pad_index, step_index)

# Main loop
print("\n" + "="*60)
print("MINIMAL SAMPLER TEST")
print("="*60)
print("\nSetup:")
print("- Switch Seqtrak to SAMPLER track (track 11)")
print("- Press pads in rows 1-2 on Push (16 steps for sample 1)")
print("- Watch SEND/RECV messages")
print("\nPress Ctrl+C to exit\n")

init_push()

print("\nListening for pad presses...")
print("(Also logging ALL messages from Seqtrak)\n")

try:
    while True:
        # Check for Push messages
        for msg in push_in.iter_pending():
            handle_push_message(msg)

        # Check for Seqtrak messages
        for msg in seqtrak_in.iter_pending():
            handle_seqtrak_message(msg)

        time.sleep(0.01)

except KeyboardInterrupt:
    print("\n\nShutting down...")
    # Turn off all pads
    for note in range(36, 100):
        push_out.send(mido.Message('note_on', note=note, velocity=0))

    push_out.close()
    push_in.close()
    seqtrak_out.close()
    seqtrak_in.close()
    print("✓ Closed")
