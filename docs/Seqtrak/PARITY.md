# Seqtrak ↔ Push Feature Parity Checklist

**Goal:** everything the Yamaha SEQTRAK can do (per Yamaha's User Guide, OS V2.00) should be doable from
an Ableton Push 1 through the bridge.
**Built:** 2026-10-12, from the user guide text (`reference files/Yamaha/User Guide/SEQTRAK_user_guide_En_D0.txt`),
`src/open_push/seqtrak/app.py` / `protocol.py` (working tree on `integration`, incl. uncommitted changes), and
`STEP-SEQUENCER.md`, `FUNCTIONALITY-MAP.md`, `midi-data-table.md`, `BUGS_AND_ENHANCEMENTS.md`.

**Legend**
- **Guide §** = section and page of the User Guide (the authority for *what* the Seqtrak does).
- **On Push:** ✅ works · 🟡 partial or buggy (what's wrong is in Notes) · ❌ missing · — not applicable
  (physical/app-only, nothing to do on the Push). Every ✅/🟡 cites the app.py function/line that does it.
- **Protocol:** ✅ verified (STEP-SEQUENCER.md "verified", or FUNCTIONALITY-MAP.md "Cap ✅" = confirmed by live
  capture) · 🟡 address documented (Data List / guide CC table) but not tested · ❓ unknown · — none needed.

---

## Summary

### Counts per chapter (On Push column)

| Chapter | ✅ | 🟡 | ❌ |
|---|---|---|---|
| 4. Projects | 0 | 3 | 7 |
| 5. Tracks and Patterns | 4 | 8 | 6 |
| 6. Drum Tracks | 5 | 1 | 4 |
| 7. Synth Tracks | 3 | 3 | 6 |
| 8. SAMPLER Track | 3 | 1 | 9 |
| 9. Sound Design | 1 | 4 | 9 |
| 10. Effects | 3 | 0 | 9 |
| 11. Mixer Mode | 0 | 3 | 5 |
| 12. Mute Mode | 1 | 0 | 1 |
| 13. Song Mode | 0 | 0 | 10 |
| 15. Connections | 0 | 0 | 1 |
| 16. Settings | 1 | 0 | 5 |
| **Device total (ch. 4–13, 15–16)** | **21** | **23** | **72** |
| 14. App-only (optional) | 0 | 0 | 6 |

Rows marked — (physical or automatic) aren't counted.

### BUGS — Push has the feature, but it misbehaves (fix these first)

1. **Drum pattern delete leaves steps 65–128.** Delete menu loops steps 0–127 (`_clear_variation_data`,
   app.py:1232) but `send_drum_delete` silently drops any step > 63 (protocol.py:676). Also ❓ whether
   `70 2t` deletes act on the MIDI-selected variation or the one shown on the Seqtrak (the sampler/synth
   path is verified to follow MIDI; drums untested).
2. **3 ⇔ 6 patterns toggle writes the wrong address.** Shift+encoder 8 (`_toggle_variation_mode`,
   app.py:2704) writes `01 10 18`, which STEP-SEQUENCER §2 shows is a *display-mode* broadcast
   (03/08/00). It is also global, while the guide makes it per track (§5.3). Still open in BUGS #4.
3. **DRUM-bus solo only solos PERC 2.** Solo is one CC 24 value (guide §18.3.3); `_toggle_drum_bus_solo`
   (app.py:3800) sends it seven times, so the last (PERC 2) wins.
4. **Sampler pad sound change probably hits drum tracks.** `_cycle_sampler_pad_preset` (app.py:3976) sends
   Bank/Program Change on MIDI channels 1–7 (= pad index), which are KICK…PERC 2 (guide §18.2). Pad presets
   are local guesses, never read back. Unverified on hardware.
5. **Knob values aren't read from the Seqtrak.** Device-mode params start from hard-coded defaults
   (`DEVICE_PARAMS_*`, app.py:221–328), so the first turn jumps (BUGS #3). Track volumes show 100, and
   mute/solo/swing are never read either (FUNCTIONALITY-MAP "Listen ❌").
6. **Out-of-range values sent.** Device encoders clamp to 0–127 (app.py:2516), but Pitch/EQ are 40–88,
   Arp Type 0–16, Arp Speed 0–9 (guide §18.3.1).
7. **Swing only 0…+28 ticks** (`set_swing`, protocol.py:422); guide range is −58…+58 (§4.5.2). Tempo
   encoder floors at 20 BPM (app.py:2433); guide allows 5–300.
8. **Bar length only cycles 1/2/4/8 bars.** A pattern of any other length (e.g. 3 bars, 24 steps) is reset to
   1 bar on the next press (`_adjust_bar_length`, app.py:2629). Guide allows 1–128 steps (§5.2).
9. **Un-solo doesn't restore the track's previous mute** (`_toggle_track_solo`, app.py:3743 clears it);
   guide §5.8.2 says the mute comes back.
10. **Delete "All (Song)" ≠ DELETE+ALL.** Menu [3] wipes all six patterns of every track
    (`_delete_all_variations_song`, app.py:1204); the guide deletes only the *current* pattern on all tracks (§5.4).
11. **Scale / Key / Octave are Push-only.** They reshape the pads (app.py:1683, 2154) but never set the
    Seqtrak's project scale `30 40 7E`, key `30 40 7F` or track octave `30 5p 0C` (`set_scale`, `set_key`,
    `set_track_octave` in protocol.py are unused). The Seqtrak's own keys and its chords stay on the old values.
12. **Awaiting hardware retest:** session-view row launch (BUGS #4; it also auto-starts playback,
    app.py:1944) and fast track-select desync (BUGS #1).
13. **Live-recorded notes appear late.** The Seqtrak doesn't report them; the bridge polls the visible track
    ~1/s while recording (`_process_record_reads`, app.py:3345) and re-reads everything when recording stops.
14. **Dead code:** Push Mute/Solo buttons (CC 60/61) do nothing; the pad mute grid (`_handle_mute_pad`,
    app.py:3040) is unreachable because nothing sets mode `'mute'`.

### MISSING — biggest gaps (then features)

- **Step sequencer depth:** step input for SYNTH 1/2/DX (protocol verified for SYNTH 1), micro timing, substep,
  probability, per-step note length/velocity, Parameter Lock, Motion Recording.
- **Projects:** switch / delete / temp-save (protocol ❓).
- **Patterns:** copy/paste, reserved (launch-quantized) switching, Launch Quantize, any length 1–128 steps.
- **Effects:** no effect control at all beyond per-track sends/filter/EQ — master, single, send effect types
  and params (CCs 102–115 documented; master CCs 102–106 captured), CLEAR FX.
- **Song mode** (scenes) — entirely missing, protocol ❓.
- **Settings:** metronome, record quantize, sampling source/count-in/normalize — all have captured addresses.
- **Sampler:** start/end/loop, sample mute, cancel sampling, per-sample pattern delete.
- **Track types** (Drum/DrumKit/Synth, §6.7): the bridge hard-codes types (`get_track_type`, app.py:385).

### Recent protocol facts (from STEP-SEQUENCER.md, 2026-10-12/13)

- **Live-recorded notes are not reported at all** — only `01 10 21 01/00` (record on/off). They *are*
  stored and read back with `70 4t [step]`, so the bridge must re-read.
- **Drum readback = `[note] [vel] [substep] [60+micro] [len_hi] [len_lo]`.** Micro timing (4th byte, `3C` = on
  grid, −60…+59) ✅ verified; substep is the 3rd byte (`00` = none) ✅ verified, value→option mapping ❓.
  The device reports edits as `70 [10+t] [param] [step] [value]` (param `00` micro, `03` substep); whether
  that works as a command is ❓. Last two bytes = note length in ticks (🟡).
- **Purple step keys = Parameter Lock** (guide §9.2, p.64). A VOLUME p-lock changes velocity, so
  live-recorded velocity is probably stored as a p-lock. Where p-locks live in SysEx is ❓.
- Sampler/melodic notes: ordered list; read `75 g idx`, remove `74 g idx 00`, add `72 g 00` + 8 bytes;
  length = last two bytes (the Seqtrak stops a sample when its note ends). `74 7x` is a report, not a command.
- Clear track `01 [10+t] 37 00` clears the variation *shown on the Seqtrak*, not the MIDI-selected one.

---

## 4. Projects

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Switch project (1–8) | §4.1 (p.23) | ❌ | ❓ | Bridge only *detects* a load (`01 10 17` → full re-read, app.py:788; meaning 🟡 assumed) |
| Ext-clock project switch (bar-synced stop, MANUAL/AUTO start, on/off) | §4.1.1 (p.23–24) | ❌ | ❓ | AUTO/MANUAL is app-only |
| Save project | §4.2 (p.24) | — | — | Automatic on switch / power-off |
| Back up / restore via app | §4.3 (p.24) | — | ❓ | App-only (ch. 14) |
| Delete project | §4.4 (p.25) | ❌ | ❓ | Bridge re-reads after a device-side delete (STEP-SEQUENCER "Project load / delete") |
| Tempo 5–300 BPM | §4.5.1 (p.26) | 🟡 | ✅ | Tempo encoder CC 14 (`handle_encoder`, app.py:2420) floors at 20; Tap Tempo (app.py:2143). Read at start + followed (app.py:869) |
| Reset tempo to project start value | §4.5.1 (p.26) | ❌ | ❓ | |
| Swing −58…+58 ticks | §4.5.2 (p.27) | 🟡 | ✅ | Swing encoder CC 15 (app.py:2441) → `set_swing` 0…+28 only; not read back |
| Reset swing (DELETE+SWING) | §4.5.2 (p.27) | 🟡 | ✅ | Only by turning the encoder back to 0 |
| Metronome on/off | §4.5.3 (p.27) | ❌ | ✅ | Click Switch `00 00 25`. Push Metronome button (CC 9, app.py:415) is defined but unhandled |
| Metronome sound / volume | §4.5.3 (p.28) | ❌ | ✅ | `00 00 26` / `00 00 27` (app-only on device) |
| Temporary save / restore | §4.6 (p.28) | ❌ | ❓ | |

## 5. Tracks and Patterns

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Switch pattern, one track (instant) | §5.1.1 (p.29) | ✅ | ✅ | Track mode encoder 8 (`_adjust_variation`, app.py:2676); device-side changes followed (`30 5p 0F`, app.py:768) |
| Switch pattern, all 11 tracks | §5.1.1 (p.29) | 🟡 | ✅ | Session view row launch (`_handle_session_row_launch`, app.py:1917): fix awaiting hardware test (BUGS #4), auto-starts playback. Global `01 10 2A` followed (app.py:799) |
| Reserved (launch-quantized) switching | §5.1.1–5.1.2 (p.29–30) | ❌ | ❓ | Push switches instantly only |
| Launch Quantize length | §5.1.3 (p.30) | ❌ | 🟡 | Maybe `30 40 7A` Pattern Master Step (1–128, data table): mapping unconfirmed |
| Pattern length | §5.2, §5.2.1 (p.31–32) | 🟡 | 🟡 | `_adjust_bar_length` (app.py:2609) writes `30 5p 16+2v`: 1/2/4/8 bars only, other lengths reset to 1 bar (bug 8). BUGS #6 complete. Step counts read at start (app.py:778) |
| 3 ⇔ 6 patterns | §5.3 (p.33) | 🟡 | ❓ | `_toggle_variation_mode` (app.py:2704) writes `01 10 18` = display mode (bug 2); guide is per track |
| Delete current pattern (one track) | §5.4 (p.34) | 🟡 | ✅ | Delete menu [1] (`_delete_current_variation`, app.py:1166). Sampler/synth: read list + `74 g idx 00` ✅. Drums: steps > 64 survive (bug 1) |
| Delete current pattern on all tracks | §5.4 (p.34) | 🟡 | ✅ | Menu [3] deletes *all* patterns of every track instead (bug 10) |
| Copy / paste pattern | §5.5 (p.34–35) | ❌ | ❓ | Could be emulated by read + write for notes; p-locks/motion not readable |
| Select track | §5.6 (p.36) | 🟡 | ✅ | Encoder 1 / CC 20·102 (`_select_next_track`, app.py:4015); Shift+Track overlay (`_handle_track_select_button`, app.py:1087); device-side selects followed (app.py:845). BUGS #1 fix awaiting retest |
| Audition track | §5.6 (p.36) | ✅ | ✅ | Drum/sampler/keyboard pads trigger notes (`_handle_drum_pad`, app.py:3058) |
| Change sound (Drum / Synth / DX) | §5.7 (p.36) | ✅ | ✅ | `_cycle_patch` (app.py:3904): Bank MSB/LSB + PC; name read via `01 1p 35` (app.py:859) |
| Change sound of a SAMPLER pad | §5.7 (p.36) | 🟡 | ❓ | `_cycle_sampler_pad_preset` (app.py:3953) sends on channels 1–7 = drum tracks (bug 4) |
| Category jump | §5.7.1 (p.37) | ❌ | ❓ | Shift+patch encoder jumps 128 presets, not categories (app.py:2575) |
| Mute track | §5.8.1 (p.38) | ✅ | ✅ | Mixer lower row (`_toggle_track_mute_simple`, app.py:3711), CC 23. State not read back |
| Unmute all | §5.8.1 (p.38) | ❌ | ✅ | `30 5p 29 00` × 11 (FUNCTIONALITY-MAP §3.6 "mixer reset") |
| Solo track | §5.8.2 (p.38) | 🟡 | ✅ | Mixer upper row (`_toggle_track_solo`, app.py:3731), CC 24. Bugs 3 and 9; not read back |
| Copy / paste track steps | §5.9 (p.39) | ❌ | ❓ | |

## 6. Drum Tracks

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Enter steps on/off | §6.1 (p.40) | ✅ | ✅ | `_toggle_step` (app.py:3385), `70 0t` / `70 2t`. Velocity fixed at 100 |
| Show steps entered on the Seqtrak | §6.1 (p.40) | ✅ | ✅ | Readback `70 4t` + live reports (app.py:806–816). BUGS #7 verified |
| Show live-recorded steps | §6.5 (p.42) | 🟡 | ✅ | Not reported by the device; polled ~1/s (bug 13) |
| Pages (> 16 steps) | §6.2 (p.40) | ✅ | ✅ | 4 pages × 32 steps (page buttons, app.py:2347 / 2384) |
| Step position / playhead | §6.1 (p.40) | ✅ | — | `_process_playhead` (app.py:3197), timed from tempo (no MIDI clock): may drift, ignores swing |
| Micro timing (−60…+59 ticks) | §6.3 (p.41) | ❌ | 🟡 | Readback byte 4 ✅ and device report `70 1t 00` ✅; as a command ❓ |
| Substep (none, ×2, ×3 8T, ×3 16T, ×4) | §6.4 (p.41) | ❌ | 🟡 | Readback byte 3 ✅, report `70 1t 03` ✅; value mapping and command ❓ |
| Real-time input + record | §6.5 (p.42) | ✅ | ✅ | Drum pads (`_handle_drum_pad`, app.py:3058) + Record `01 10 21` (app.py:2135) |
| Step probability (8 levels) | §6.6 (p.43) | ❌ | ❓ | Probably another `70 1t [param]`; not captured |
| Track type Drum / DrumKit / Synth | §6.7 (p.44–45) | ❌ | ❓ | Types hard-coded (`get_track_type`, app.py:385): a DrumKit/Synth drum track still gets the drum UI |

## 7. Synth Tracks (SYNTH 1, SYNTH 2, DX)

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Real-time play + record | §7.1 (p.46) | ✅ | ✅ | Isomorphic keyboard (`_handle_melodic_pad`, app.py:3501) + Record |
| Record quantize on/off | §7.2 (p.47) | ❌ | ✅ | Record Quantize `00 00 1F` (value 1/32…OFF is app-only on device) |
| Octave (+2…−3) | §7.3 (p.48) | 🟡 | ✅ | Octave buttons shift pads (app.py:2154) but don't set `30 5p 0C` (bug 11) |
| Scale (8 per project) | §7.4 (p.48) | 🟡 | ✅ | Push Scale mode (`_handle_scale_mode_button`, app.py:1683) is Push-only; `30 40 7E` not set/read (bug 11) |
| Key | §7.5 (p.49) | 🟡 | ✅ | Root buttons in Scale mode, Push-only; `30 40 7F` not set/read (bug 11) |
| MONO / POLY / CHORD | §7.6 (p.49) | ✅ | ✅ | Device page 1 "Mode", CC 26 (app.py:252) |
| Edit chords | §7.7 (p.50) | ❌ | 🟡 | `30 6p` / `30 7p` seen as broadcasts; writing untested |
| Keyboard input mode | §7.8 (p.51) | ✅ | — | Push pads are always a keyboard (app.py:1486) |
| Step input: notes on/off per step | §7.9 (p.51) | ❌ | ✅ | No melodic step grid. SYNTH 1 add/read/remove verified; SYNTH 2 `10` / DX `20` inferred |
| Step input: add/remove notes, chords per step | §7.9 (p.52) | ❌ | ✅ | Note list holds several notes per position |
| Step input: note length | §7.9 (p.52) | ❌ | ✅ | Last two bytes of the 8-byte note |
| Step input: micro timing | §7.9 note (p.52) | ❌ | ❓ | Presumably an off-grid tick; untested |

## 8. SAMPLER Track

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Real-time play 7 samples + record | §8.1 (p.53) | ✅ | ✅ | `_handle_sampler_pad` (app.py:3601): ch 11, notes 60–66 |
| Sample into a pad (mic / AUDIO IN / USB) | §8.2 (p.53) | ✅ | ✅ | Shift+Record (app.py:2120): `01 10 28` pad + `01 10 22` |
| Sampling source | §8.3 (p.54) | ❌ | ✅ | `00 00 19` (FUNCTIONALITY-MAP §3.7) |
| Resampling | §8.4 (p.54) | ❌ | ✅ | Sampling source = Resampling |
| Cancel sampling | §8.5 (p.54) | ❌ | ❓ | |
| Sampling count-in | §8.6 (p.55) | ❌ | ✅ | `00 00 1B` |
| Monitoring mode (input meter) | §8.7 (p.55) | ❌ | ❓ | |
| Auto-normalize | §8.8 (p.56) | ❌ | ✅ | `00 00 1C` (app-only on device) |
| Delete pattern of one sample | §8.9 (p.56) | ❌ | ✅ | Read list, remove that pad's indexes |
| Step input per pad | §8.10 (p.56) | ✅ | ✅ | `_toggle_sampler_step` (app.py:3445); BUGS #2 solved; pad select both ways (`01 10 28`, app.py:833 / 3668) |
| Step note length | §8.10 (p.57) | 🟡 | ✅ | Automatic only: rings to the pad's next step (`_sampler_ring_length`, app.py:3440); no manual edit |
| Step micro timing | §8.10 note (p.57) | ❌ | ❓ | |
| Mute a sample | §8.11 (p.58) | ❌ | 🟡 | `30 40 63` bitmask (data table) |

## 9. Sound Design

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Parameter pages + advanced pages | §9.1.1 (p.60) | ✅ | — | Device mode pages via page buttons (app.py:2338 / 2375) |
| Drum params (sound, pitch, pan, vol, attack, decay, filter, reso, sends, EQ) | §9.1.2 (p.60) | 🟡 | ✅ | `DEVICE_PARAMS_DRUM` (app.py:221). Bugs 5, 6 (BUGS #3) |
| Synth params incl. porta, arp type/gate/speed | §9.1.3 (p.61) | 🟡 | ✅ | `DEVICE_PARAMS_SYNTH` (app.py:247). Bugs 5, 6 |
| DX params incl. FM algorithm/mod amount/freq/feedback | §9.1.4 (p.62) | 🟡 | ✅ | `DEVICE_PARAMS_DX` (app.py:284). Bug 5 |
| SAMPLER params pages 1–3 | §9.1.5 (p.63) | 🟡 | ✅ | `DEVICE_PARAMS_SAMPLER` (app.py:305): no PITCH (no sampler CC in §18.3); whole track vs selected pad ❓. Bug 5 |
| SAMPLER start / end / loop on-off / loop length | §9.1.5 (p.63) | ❌ | 🟡 | Start/End/Loop length `50 eA 66/6A/60` captured; loop on/off address ❓ |
| SAMPLER pitch EG (PEG) | §9.1.5 (p.63) | ❌ | ❓ | |
| Pitch per step (synth, step input) | §9.1.3 note (p.61) | ❌ | ❓ | |
| Parameter Lock | §9.2 (p.64) | ❌ | ❓ | Purple steps; Push shows every step green (STEP-SEQUENCER §2) |
| Delete Parameter Lock (pattern / step) | §9.2.1 (p.65–66) | ❌ | ❓ | |
| Motion Recording | §9.3 (p.67) | ❌ | ❓ | Untested whether Push CCs during recording become motion |
| Delete Motion | §9.3.1 (p.67) | ❌ | ❓ | |
| Undo / Redo | §9.4 (p.68) | ❌ | ❓ | |
| Save sound (+ favorite) | §9.5 (p.68) | ❌ | ❓ | |
| Delete / import sounds | §9.6–9.7 (p.68–69) | — | ❓ | App-only |

## 10. Effects

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Single (track) effect type | §10.1.1, §10.2.2 (p.70, 73) | ❌ | 🟡 | Insertion A `31 2p 00` (Data List) |
| Single effect parameters 1–3 | §10.2.5 (p.74) | ❌ | 🟡 | CC 107–109 per track (guide §18.3.2) |
| Track LP-HP filter | §10.1.1 (p.70) | ✅ | ✅ | Device Cutoff/Reso, CC 74/71 |
| Track 2-band EQ | §10.1.1 (p.70) | ✅ | ✅ | Device EQ Hi/Lo, CC 20/21 (range bug 6) |
| Reverb / Delay send level per track | §10.1.2 (p.71) | ✅ | ✅ | Device Reverb/Delay, CC 91/94 |
| Master effect type (8 categories × 8) | §10.2.2 (p.73) | ❌ | 🟡 | `30 43 00` type |
| Master effect params (FX LEVEL, page 2) | §10.2.4 (p.74) | ❌ | ✅ | CC 102–104 ch 1; constants in protocol.py:119, not wired |
| HIGH PASS slider | §10.1.3 (p.72) | ❌ | ✅ | Likely CC 105 (master effect 2): mapping inferred |
| REPEATER slider | §10.1.3 (p.72) | ❌ | ✅ | Likely CC 106 (master effect 3): mapping inferred |
| Master compressor | §10.1.3 (p.72) | ❌ | 🟡 | `30 46` (app-only on device) |
| Master 5-band EQ | §10.1.3 (p.72) | ❌ | 🟡 | `30 47` (app-only on device) |
| CLEAR FX | §10.3 (p.74) | ❌ | ❓ | |

## 11. Mixer Mode

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| VOLUME per track | §11.2 (p.75) | 🟡 | ✅ | Mixer encoders (app.py:2533), CC 7. Not read back: shows 100 at start |
| PAN per track | §11.2 (p.75) | 🟡 | ✅ | Only in Device mode, one track at a time |
| REVERB / DELAY SEND per track | §11.2 (p.75) | 🟡 | ✅ | Only in Device mode, one track at a time |
| Project volume (ALL knob) | §11.2 (p.76) | ❌ | 🟡 | `30 40 66` (seen in capture, not tested). Push master knob sets *speaker* volume instead |
| Project pan (ALL knob) | §11.2 (p.76) | ❌ | 🟡 | `30 40 65` |
| Reverb / Delay return level | §11.2 (p.76) | ❌ | ❓ | |
| Send effect type (8 presets each) | §11.3.1 (p.76) | ❌ | 🟡 | `30 41 00` / `30 42 00` |
| Send effect parameters | §11.3.2 (p.76–77) | ❌ | 🟡 | CC 110–115 ch 1 (guide §18.3.2) |

## 12. Mute Mode

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| One-press mute per track | §12.1–12.2 (p.78) | ✅ | ✅ | Mixer lower-row buttons (`_toggle_track_mute_simple`, app.py:3711). Pad mute grid is dead code (bug 14) |
| Unmute all | §12.2 (p.78) | ❌ | ✅ | `30 5p 29 00` × 11 |

## 13. Song Mode

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Enter / exit Song mode | §13.1 (p.79) | ❌ | ❓ | Push Session view is a bridge-only launcher, not stored on the Seqtrak |
| Scene mode (loop one scene) | §13.1.1 (p.79) | ❌ | ❓ | |
| Play / stop scenes in order | §13.2 (p.80) | ❌ | ❓ | |
| Change scene | §13.2.1 (p.80) | ❌ | ❓ | |
| Loop a scene | §13.2.2 (p.81) | ❌ | ❓ | |
| Loop whole song | §13.2.3 (p.81) | ❌ | ❓ | App setting |
| Add scene (up to 16) | §13.3 (p.82) | ❌ | ❓ | |
| Delete scene | §13.4 (p.82) | ❌ | ❓ | |
| Edit scene patterns / mute / solo | §13.5.1 (p.83) | ❌ | ❓ | |
| Scene length (incl. AUTO) | §13.5.2 (p.83–84) | ❌ | ❓ | |

## 14. SEQTRAK App: app-only features (listed separately)

These aren't on the Seqtrak's panel; parity here is optional.

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| LFO per track | §14.1 (p.85) | ❌ | 🟡 | `31 4p` |
| Alternate (choke) groups | §14.1 (p.85) | ❌ | ✅ | Group Number `30 5p 08` |
| All FM engine params (DX) | §14.1 (p.85) | ❌ | 🟡 | `48 09` / `49 o9` |
| Deep sound / element params | §14.1 (p.85) | ❌ | 🟡 | `31 1p`, `41 ep`, `42 ep` |
| Scale editing | §7.4 note (p.48) | ❌ | ✅ | `30 4D` (8 × 7 notes) |
| HIGH PASS / REPEATER effect type | §10.1.3 (p.72) | ❌ | ❓ | |
| Project / sound manager, full backup | §14.2 (p.86) | — | ❓ | Bulk dumps seen; request unknown; puts device in content mode |
| Visualizer | §14.3 (p.87) | — | — | |
| Dynamic tutorial | §14.4 (p.88) | — | — | |
| (Also app-only, tracked in their chapters: metronome sound/volume, AUTO/MANUAL playback, quantize value, auto-normalize, compressor, 5-band EQ, knob sensitivity, MIDI clock/filters/Thru.) | | | | |

## 15. Connections

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Wired USB-C MIDI (host / device) | §15.1.1, §15.2.1, §15.3 (p.89–92) | — | — | The bridge itself (Pi is USB host for Push + Seqtrak) |
| Bluetooth pairing | §15.1.2 (p.90) | — | — | Physical key combo |
| Wi-Fi on/off | §15.1.3 (p.90) | ❌ | 🟡 | Wireless LAN `00 00 16` (FUNCTIONALITY-MAP §4) |
| MIDI conversion cable | §15.2.2 (p.92) | — | — | Physical |

## 16. Settings

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Factory reset | §16.1 (p.93) | — | ❓ | Power-on key combo |
| Track knob sensitivity | §16.2 (p.93) | ❌ | 🟡 | "Pattern select sensitivity", system block (FUNCTIONALITY-MAP §4) |
| MIDI clock (sync, clock out) | §16.3.1 (p.93) | ❌ | 🟡 | `00 00 2A` / `00 00 2D` |
| MIDI output filters | §16.3.2 (p.93) | ❌ | 🟡 | System block transmit filters |
| MIDI Thru | §16.3.3 (p.93) | ❌ | 🟡 | System block |
| Master volume (speaker) | §16.4 (p.94) | ✅ | ✅ | Master encoder CC 79 (app.py:2591) → `00 00 00`; read at start + followed (app.py:819) |
| Headphone master volume | §16.4 (p.94) | ❌ | 🟡 | `00 00 01`: Push only writes the speaker volume |

---

## Push-only extras (not in the guide)

Software arpeggiator and note repeat (app.py:2743–2994; BUGS #5 asks how they should interact), accent /
fixed velocity, DRUM bus (volume, mute, solo; app.py:3751), Session view launcher, iPad audio routing
(Shift+User settings, app.py:1393).
