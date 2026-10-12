# Seqtrak Bridge - Bugs and Enhancements

**Status**: Active tracking document for standalone Pi bridge testing
**Last Updated**: 2025-12-26
**Hardware**: Raspberry Pi headless deployment

**Important**: These are **app issues**, not Raspberry Pi hardware issues. The Pi bridge hardware is working correctly. These bugs and enhancements apply to the Seqtrak bridge app itself and would exist whether running on Mac or Pi.

---

## Known Bugs

### 1. Encoder Track Switching Desync
**Severity**: Medium
**Description**: When turning the track selection encoder too quickly, the track name display gets out of sync with the actual selected instrument.

**Steps to Reproduce**:
1. Turn track selection encoder rapidly
2. Observe track name on LCD
3. Play a note and listen to which instrument actually plays

**Expected**: Display matches active instrument
**Actual**: Display shows wrong track name

**Investigation Needed**: Check encoder handling rate limiting, track state update timing

**Update (2026-10-11):** the bridge now listens for track changes made on the Seqtrak
(`01 10 27`) and ignores echoes for 0.5 s after its own selects, so a fast turn can't be
pulled back to an older track. Retest on hardware.

---

### 2. Sampler Step Sequencer - Cannot Remove Steps
**Severity**: High
**Description**: On the sampler track, steps can be added to the step sequencer pads, but they cannot be removed.

**Steps to Reproduce**:
1. Switch to sampler track
2. Enter step sequencer mode
3. Add a step by pressing a pad
4. Try to remove the step by pressing the same pad again

**Expected**: Step is removed (pad turns off)
**Actual**: Step remains active (cannot remove)

**Technical Note**: Delete command is documented in `sysex-protocol-reference.md`:
- Sampler delete: `72 50 00 [tick_hi] [tick_lo]` (line 1088-1130)
- May not be implemented in `app.py`

**Root cause (2026-10-11):** not the delete message. A device capture of sampler Step Input
showed add `72 30 00` / delete `74 73 00` + `[tick_hi] [tick_lo] 00 [3C+pad] 64 00 00 78`,
byte-identical to what the bridge sends (since 7bb1841). The bug is state: the Push only knew
steps pressed on the Push since the bridge started, so a step placed on the device (or before a
restart) got a second "add" instead of a delete. Fix: the bridge now follows sampler step
edits made on the device. Remaining gap: sampler steps can't be read back, so steps that
existed before the bridge started still aren't known.

---

### 3. Missing Parameters on Display
**Severity**: Medium
**Description**: Not all effect/sound parameters are being displayed or utilized on the instruments/device page.

**Investigation Needed**:
- Which specific parameters are missing?
- Are they not implemented, or just not displayed?
- Cross-reference with `IMPLEMENTATION-GAP-ANALYSIS.md`

---

### 4. Session View Not Launching Clips
**Severity**: High
**Description**: Session view sometimes doesn't work at all - pressing pads to launch patterns/variations does not trigger playback.

**Steps to Reproduce**:
1. Enter session view mode
2. Press pads to launch patterns
3. Observe whether playback starts

**Expected**: Pattern launches and plays
**Actual**: Nothing happens (intermittent)

**Investigation Needed**:
- Is this related to variation state?
- MIDI message logging during failed launch attempts
- Check SysEx pattern launch commands

**Root causes found (2026-10-11)** — fix on `integration`, awaiting hardware test:
1. Every session row defaulted to pattern 1 (`[[1]*6 ...]`), so all six launch buttons
   re-selected variation 1 → looked like nothing happened. Now row N defaults to pattern N.
2. A row launch only sent the 8 tracks on the visible page (skipped PERC1/PERC2/SAMPLER or
   the other half). Now every track is sent.
3. Launch didn't update `track_variation`, and the bridge ignored variation feedback from the
   Seqtrak, so display/encoder state drifted. Now launches update state, the launched row is
   highlighted blue, and the bridge listens for `30 5p 0F`, `01 10 2A`, `01 10 27`.
4. Delete-all-variations helpers left tracks on variation 6. They now restore the previous one.
5. Startup now reads each track's current pattern (`30 5p 0F`) so state starts correct.

Still open: the bridge's 3/6 variation toggle writes `01 10 18`, but the device reported
`01 10 18 = 0` while Pattern Select Mode `30 40 79 = 1` (advanced) and a track was on
pattern 6. Capture toggling 3/6 on the hardware to confirm which address is the real switch.

---

### 5. Arpeggio + Note Repeat Interaction
**Severity**: Low (needs clarification)
**Description**: Arpeggios are running while note repeat is also active.

**Question**: Is this unexpected behavior, or just an observation? Need to clarify:
- Should arpeggio disable when repeat is active?
- Or should they work together?
- What does the Seqtrak hardware/iOS app do?

---

### 6. Melodic Track Bar Length Not Working - **Complete**
**Severity**: High
**Description**: Cannot adjust bar length for melodic tracks (SYNTH 1, SYNTH 2, DX, SAMPLER - channels 8-11). Pattern length adjustment works for drum tracks but not bar length for melodic tracks.

**Terminology**:
- **Pattern** = step sequence for drum tracks (channels 1-7)
- **Bar** = step sequence for melodic tracks (channels 8-11)

**Steps to Reproduce**:
1. Select a melodic track (SYNTH 1, SYNTH 2, DX, or SAMPLER)
2. Attempt to adjust bar length
3. Observe that bar length does not change

**Expected**: Bar length can be adjusted for melodic tracks (1-128 steps)
**Actual**: Bar length adjustment does not work for melodic tracks

**Technical Note**:
- SysEx addresses for pattern/bar length: `30 5[track] 16-21` (per-variation step count)
- Global pattern master step: `30 40 7A`
- Same addresses used for both drum patterns and melodic bars
- Implementation may not be sending/receiving SysEx for melodic track bar length

**Investigation Needed**:
- Check if SysEx is being sent when adjusting melodic track length
- Verify SysEx address calculation for melodic tracks (channels 8-11)
- Test if Seqtrak hardware responds to bar length SysEx for melodic tracks
- Compare with working pattern length implementation for drum tracks

**Reference**: See `docs/Seqtrak/TERMINOLOGY.md` for pattern vs bar distinction

---

### 7. Step Sequencer Doesn't Show Steps Entered on the Seqtrak
**Severity**: High
**Description**: Steps entered on the Push reach the Seqtrak, but steps entered on the Seqtrak
never appear on the Push step grid. The grid was only a local memory of Push presses; the
bridge never read step data. A Push press on a step already set on the device sent "add"
instead of "delete".

**Fix (2026-10-11, drum tracks 1-7)** — `integration` 4ffd6f7, **verified on hardware** (drum steps entered on the Seqtrak show on the Push):
- Listens for the device's own step edits: add `70 [t-1] 00 [step] ...`, delete `70 [0x20+t-1] 00 [step]`.
- Reads stored steps with `70 [0x40+t-1] [step]` (data = set, no data = empty) at startup and
  whenever a drum track's pattern changes; reads are throttled to one per 3 ms.
- Verified on hardware that both messages exist (KICK steps 1/5/9/13, then 5 removed); the
  decode was checked offline against the captured bytes.

**Sampler (2026-10-11):** live add/delete from the device is now followed (see bug #2).
**Still open**: sampler steps (`72`) don't answer read requests, so they can't be loaded at startup. SYNTH 1/SYNTH 2/DX
have no step grid on the Push (or a step view in the Seqtrak app), so they don't need step sync. Also
confirm the readback reflects the newly selected pattern when a variation change is queued
while playing.

---

## Enhancement Requests

### 1. Direct Track Selection
**Priority**: High
**Description**: Need a way to jump directly to a specific track without cycling through all 11 tracks with the encoder.

**Current Behavior**: Must turn encoder through tracks 1→2→3...→11 to reach desired track

**Proposed Solutions**:
- Option A: Use upper/lower LCD buttons as direct track select (1-11 + DRUM bus)
- Option B: Shift + encoder for faster scrolling (jump by track group)
- Option C: Shift + pad grid shows track selection overlay

**User Preference**: TBD

---

### 2. Variation Selector for Recording **Complete**
**Priority**: High
**Description**: Need a way to select which variation (1-6) to record into, especially when adding new parts without switching all tracks.

**Current Behavior**: Recording goes to currently active variation for that track

**Proposed Solution**:
- Use encoder **CC78** as variation selector knob
- Display current variation on LCD (1-6)
- When recording, new data goes to selected variation
- Independent of global variation state

**Documentation Reference**:
- Per-track variation selection: `30 5[track] 0F` (data 00-05 = Variations 1-6)
- Source: `sysex-protocol-reference.md` lines 872-886

**Implementation Notes**:
- Each track can have independent variation (1-6)
- Current code may only support global variation switching
- Need per-track variation state tracking

---

### 3. Encoder Resolution Adjustment
**Priority**: Medium
**Description**: Track selection encoder needs smoother, more predictable feel - ideally one encoder click equals one track change.

**Current Behavior**:
- Encoder resolution feels inconsistent
- Sometimes jumps multiple tracks
- Difficult to land on desired track precisely

**Desired Behavior**:
- Smooth, notch-like feel (one click = one track)
- Consistent response regardless of turn speed

**Technical Challenge**:
- Push encoders are endless (no physical detents)
- Need to tune encoder delta threshold in code
- May need acceleration curve adjustment

**Investigation Needed**:
- Current encoder CC value delta threshold
- Test different threshold values
- Consider separate thresholds for slow vs fast turns

---

### 4. Standalone Mode Control Improvements
**Priority**: Medium
**Description**: Since the Pi bridge runs standalone (no keyboard, no CLI access), need better ways to control and recover from issues without SSH.

**Specific Needs**:

#### 4.1 Service Restart
- **Current**: Must SSH in and run `sudo systemctl restart open-push-seqtrak.service`
- **Desired**: Button combination to restart app (e.g., Shift + Stop + Play held for 3 seconds)

#### 4.2 Error Recovery
- **Current**: If app freezes/crashes, no way to recover without SSH
- **Desired**: Watchdog or graceful error handling with auto-recovery

#### 4.3 Status Indicators
- **Current**: No visual indication if app is running vs stuck
- **Desired**:
  - Heartbeat LED pattern (breathing effect on a button)
  - Error state indication (red flashing)
  - Boot progress indicator during 45-second startup

#### 4.4 Safe Shutdown
- **Current**: Unplugging Pi could corrupt SD card
- **Desired**: Button combo to trigger safe shutdown (e.g., Shift + Stop held for 5 seconds, then LCD shows "Safe to unplug")

**Implementation Notes**:
- May need systemd modifications
- Could use subprocess calls for restart/shutdown
- Need careful handling to avoid accidental triggers

---

## Testing Checklist

When fixing bugs or adding enhancements, test these workflows:

- [ ] Track switching (all 11 tracks + DRUM bus)
- [ ] Step sequencer add/remove on all track types (Drum, Synth, DX, Sampler)
- [ ] Variation switching (all 6 variations)
- [ ] Session view pattern launching
- [ ] Arpeggiator on/off with various repeat settings
- [ ] Encoder responsiveness at different turn speeds
- [ ] Standalone operation (no SSH, keyboard, or monitor)
- [ ] Boot-to-operational cycle (~45 seconds)
- [ ] Recovery from app freeze/crash

---

## Documentation Cross-Reference

Before implementing fixes, consult these documents for accurate specs:

| Document | Purpose |
|----------|---------|
| `sysex-protocol-reference.md` | Complete SysEx protocol (variations, step sequencer, etc.) |
| `IMPLEMENTATION-GAP-ANALYSIS.md` | Feature comparison vs iOS app |
| `CLAUDE.md` (root) | Pi bridge deployment workflow |
| `raspberry-pi-setup/PI_BRIDGE_SETUP_NOTES.md` | Pi hardware setup (local only) |

**Critical**: Always verify against documentation before making assumptions. Check:
- Number of variations (6, not 4)
- SysEx address formats
- Track numbering (1-11 vs 0-10 indexing)
- Encoder CC numbers

---

## Notes

- This document tracks issues discovered during standalone Pi bridge testing
- Priority levels: High = affects core functionality, Medium = usability issue, Low = nice-to-have
- All bugs should be reproducible and documented with steps
- Enhancements should include clear use case and proposed solution
- Update this document as bugs are fixed or new issues discovered
