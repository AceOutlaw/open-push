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

**Solved (2026-10-12)** — the real cause *was* the delete message. The sampler stores an indexed
note list: read `75 30 [index]`, remove `74 30 [index] 00`. `74 73 00 …` is only the Seqtrak's report
of a removal and is ignored as a command; the bridge's full-step note length (`… 78`) also made every
add remove the next step. Fixed on `integration`: the sampler grid is read from the Seqtrak (including
steps placed before the bridge started), removes use the note index, adds use length 0, and the list
is re-read after every edit. Details: `docs/Seqtrak/STEP-SEQUENCER.md`. Awaiting hardware test.

**Earlier analysis (2026-10-11, superseded):** not the delete message. A device capture of sampler Step Input
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

### 5. Copy a Sample from One Sampler Pad to Another
**Priority**: Low (the sampler is parked)
**Linear**: KM-227
**Description**: Put the sample on one SAMPLER pad onto another pad from the Push, e.g. to play the same
sample trimmed, pitched or looped differently on two pads.

**Current Behavior**: Not possible from the Push. The Seqtrak itself has no sample copy either: the guide
only copies patterns (§5.5) and steps (§5.9), and each pad picks its sound from the library with Sound Design
knob 1 (§5.7).

**Ways it might work (none verified)**:
- Preset or imported sample: set the target pad to the same library sound. Needs the message that picks a
  pad's sound, which isn't known yet (the picker list `bulk.toml` is only ❓ inferred).
- Recorded sample: the guide doesn't say whether recordings appear in the sound list. Saving a sound (hold
  [ALL], press Sound Design knob 1, §9.5) adds it as a favourite, which another pad could pick (§5.7.1);
  untested on the SAMPLER track.
- Bulk dump of the sampler element (`bulk.toml`, official) sent back to another pad: untested, risky.

**Investigation Needed**:
- On the device: does save-as-favourite work for a recorded sample? If yes, can another pad select it?
- App click-through capture while changing a pad's sample, to find the pad sound-select message.
- Then a Push action like Duplicate (hold a button, press From pad, press To pad).

---

### 6. Split Outputs (Drums Left, Synths Right)
**Priority**: Medium
**Linear**: KM-228
**Description**: The Seqtrak has one stereo output (the PHONES stereo mini jack; guide, Specifications). A "Split outputs"
switch on the Push pans all drum tracks hard left and the synth tracks hard right, so a splitter cable (TRS
to two mono jacks) gives two separate outputs: drums to one channel of a mixer or interface, synths to another.

**Current Behavior**: Possible today only by panning every track by hand.

**Proposed Behavior**:
- One switch in a menu: **Split outputs ON/OFF**.
- ON: drums (KICK … PERC 2, tracks 1–7) hard left (pan 1), SYNTH 1, SYNTH 2, DX (8–10) hard right (pan 127).
  SAMPLER (11) goes with the synths (decided 2026-10-15; no setting for now).
- Project pan (ALL knob) set to centre (64) so it doesn't shift the split.
- OFF: restore every track's pan to what it was before ON.
- Show it on the LCD (e.g. `SPLIT L|R`) so it's clear why the mix is one-sided.
- Remember it across restarts? (TBD) Re-apply after a project switch, since pans are saved per project.

**Protocol** (✅ verified 2026-10-15, `spec/track.toml`, `spec/project.toml`):
- Track pan `30 5p 01`, data 1–127, 64 = centre (p = track − 1). Same as CC 10.
- Project pan `30 40 65`, data 1–127, 64 = centre.

**Unknowns to check on the hardware (not in the guide)**:
- REVERB and DELAY are shared send effects (§11.3). Their returns are probably stereo, so reverb/delay from
  the drums may leak into the synth side and the other way round. Option: a "dry split" that also turns the
  sends down, or accept the bleed.
- The master effect and any stereo sound (stereo delay, chorus, wide presets) may also leak across.
- Check with the splitter: solo the drums with Split ON and listen to the right channel for leakage.

---

### 7. Sample Keyboard (Play One Sample Chromatically Across the Pads)
**Priority**: Medium
**Linear**: KM-229
**Description**: The Seqtrak plays each SAMPLER pad as a one-shot at a fixed pitch; you can change a pad's PITCH
but not play it like an instrument. In software: a Push mode where the 8×8 grid is a keyboard and every pad
press retunes a SAMPLER pad, then triggers it.

**How**:
- Per press: pad PITCH `41 eA 4F` (✅ verified writable, 40 = 0) to the pad's note, then note-on ch 11,
  note 60 + (pad − 1).
- Polyphony: if retuning bends a ringing note, put the same sample on all 7 pads and rotate (needs KM-227
  for recorded samples; presets/imports can be selected on each pad already).
- Alternative: MIDI pitch bend on ch 11, if the SAMPLER responds (not documented).

**Recording (✅ solved 2026-10-17)**: a note recorded while the pad is retuned stores only the pad (test 5:
four notes at 0/+4/+7/+12 played back as the same note). But the pitch can be stored per step as a
**Parameter Lock event** in the same note list (`72 30 00 [tick] 03 41 1A 4F [value] 00`, written at the step
and 60 ticks before it, `spec/steps.toml` steps.param_lock). A lock written from the Pi on step 10 (+12)
played an octave up. So recording from the Push = add the note **and** its pitch lock.

**Tests (hardware, with ears), 2026-10-17, pad 2**:
1. ✅ PITCH +4 / +7 / ±12 played at those pitches. Range −48…+48 semitones (writes clamp to `10`–`70`).
2. ✅ Retuning while a note rings does **not** change that note: the pitch is fixed at note-on (heard twice).
3. ✅ Pitch bend on ch 11 bends the sample (not in Yamaha's docs). Bend range not measured.

**What that means for the design**:
- Retune-then-trigger works, and a ringing note keeps its pitch, so fast melodies on one pad are fine.
- 4. 🟡 Two overlapping notes on one pad (pad 2, gate mode; root then +7 on top, both held): Ace didn't
  think both sounded together, but the vocal sample made it hard to tell ("it did sound good"). Treat one
  pad as **one voice** (a new note-on cuts the ringing one) until a clearer test (a plain sustained tone)
  says otherwise. Design for chords: rotate notes across pads that hold the same sample.
- Pitch bend can add bends on top (a touch strip). It moves every sounding SAMPLER note, so it isn't a way
  to play chords.

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
