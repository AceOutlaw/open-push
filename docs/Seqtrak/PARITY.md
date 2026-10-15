# Seqtrak ↔ Push Feature Parity Checklist

**Goal:** everything the Yamaha SEQTRAK can do (per Yamaha's User Guide, OS V2.00) should be doable from
an Ableton Push 1 through the bridge.

**Firmware scope (Ace, 2026-10-15):** the target is the firmware this unit runs, **1.21.3**, until it works
fully. The guide is written for OS V2.00, so a guide feature may not exist or may behave differently on 1.21.3.
§6.7 track types (Drum / DrumKit / Synth) is 2.0-only. Moving to 2.0 is a later, separate project (Linear
KM-34): it changes what the drum keys mean, so drum tracks are no longer fixed KICK / SNARE / …
**Updated:** 2026-10-15 (after the KM-100 fixes, new buttons, song mode and the app click-through). **Built:** 2026-10-12, from the user guide text (`reference files/Yamaha/User Guide/SEQTRAK_user_guide_En_D0.txt`),
`src/open_push/seqtrak/app.py` / `protocol.py` (working tree on `integration`, incl. uncommitted changes), and
`STEP-SEQUENCER.md`, `FUNCTIONALITY-MAP.md`, `midi-data-table.md`, `BUGS_AND_ENHANCEMENTS.md`.

**Legend**
- **Guide §** = section and page of the User Guide (the authority for *what* the Seqtrak does).
- **On Push:** ✅ works (hardware-tested) · 🔵 built and deployed, awaiting hardware test · 🟡 partial or buggy (what's wrong is in Notes) · ❌ missing · — not applicable
  (physical/app-only, nothing to do on the Push). Every ✅/🟡 cites the app.py function/line that does it.
- **Protocol:** ✅ verified (STEP-SEQUENCER.md "verified", or FUNCTIONALITY-MAP.md "Cap ✅" = confirmed by live
  capture or readback) · 📱 sent by the official app for that control (APP-CLICKTHROUGH-P1.md) · 📥 reported by the device · 🟡 address documented (Data List / guide CC table) but not tested · ❓ unknown · — none needed.

---

## Summary

### Counts per chapter (On Push column)

| Chapter | ✅ | 🔵 | 🟡 | ❌ |
|---|---|---|---|---|
| 4. Projects | 1 | 3 | 1 | 5 |
| 5. Tracks and Patterns | 5 | 6 | 2 | 5 |
| 6. Drum Tracks | 5 | 3 | 1 | 0 |
| 7. Synth Tracks | 4 | 2 | 0 | 6 |
| 8. SAMPLER Track | 3 | 0 | 1 | 9 |
| 9. Sound Design | 1 | 3 | 2 | 8 |
| 10. Effects | 3 | 0 | 0 | 9 |
| 11. Mixer Mode | 0 | 1 | 2 | 5 |
| 12. Mute Mode | 1 | 0 | 0 | 1 |
| 13. Song Mode | 0 | 10 | 0 | 0 |
| 15. Connections | 0 | 0 | 0 | 1 |
| 16. Settings | 1 | 0 | 0 | 5 |
| **Device total (ch. 4–13, 15–16)** | **24** | **28** | **9** | **54** |
| 14. App-only (optional) | 0 | 0 | 0 | 6 |

Rows marked — (physical or automatic) aren't counted.

**Progress:** audit 2026-10-13 = 21 ✅ · 23 🟡 · 72 ❌. Now 2026-10-15 = 24 ✅ · 28 🔵 · 9 🟡 · 54 ❌
(track type moved to — : needs firmware 2.0). Of the 54 missing, about 36 have a known command (📱/✅ in the Protocol
column) and are build work; the rest (❓) need a capture of the Seqtrak's own keys. Bug 14 (dead Mute/Solo buttons) is
fixed too (`bb115a8`).

### BUGS — Push has the feature, but it misbehaves (fix these first)

> **Status 2026-10-14 (code fixed, not yet tested on hardware):** 1 (`42d6679`); 2, 3, 5 (partly), 6, 7, 8,
> 9, 10, 11 (key + scale; octave left alone — the Seqtrak's octave only shifts its own keys, guide §7.3) in the
> KM-100 bug-fix commit. 4 is **not a bug**: the pad sound change already sends what the SEQTRAK app sends
> (Bank MSB 62 on the pad's channel, capture 106-16). 5 now reads volume, pan, sends, EQ, drum pitch/attack/
> decay, mono/poly and portamento back; cutoff/resonance, synth decay, arp and FM have no known 1:1 SysEx value.
> New: the bridge waits for the Push and Seqtrak instead of exiting when one isn't plugged in.


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
| Switch project (1–8) | §4.1 (p.23) | 🔵 | ✅ | Push Browse button → project picker, top LCD buttons 1–8 load a project: Bank MSB 64 / LSB 0 / PC (Data List; the app sends it). Current project read from `01 10 15`; the Push re-reads after a switch |
| Ext-clock project switch (bar-synced stop, MANUAL/AUTO start, on/off) | §4.1.1 (p.23–24) | ❌ | ❓ | AUTO/MANUAL is app-only |
| Save project | §4.2 (p.24) | — | — | Automatic on switch / power-off |
| Back up / restore via app | §4.3 (p.24) | — | ❓ | App-only (ch. 14) |
| Delete project | §4.4 (p.25) | ❌ | ❓ | Bridge re-reads after a device-side delete (`01 10 00` burst end) |
| Tempo 5–300 BPM | §4.5.1 (p.26) | 🔵 | ✅ | Tempo encoder CC 14 now 5–300 (`dcfc4b3`); Tap Tempo; read at start + followed |
| Reset tempo to project start value | §4.5.1 (p.26) | ❌ | ❓ | |
| Swing −58…+58 ticks | §4.5.2 (p.27) | ✅ | ✅ | Swing encoder CC 15: full −58…+58 (128 + ticks), also to the synth arps like the app; read back; LCD popup (`dcfc4b3`, `2474f4d`). Confirmed by Ace 2026-10-14 |
| Reset swing (DELETE+SWING) | §4.5.2 (p.27) | 🟡 | ✅ | Only by turning the encoder back to 0 |
| Metronome on/off | §4.5.3 (p.27) | 🔵 | ✅ | Push Metronome button CC 9 → `00 00 25`, read + followed, LED (`bb115a8`) |
| Metronome sound / volume | §4.5.3 (p.28) | ❌ | 📱 | `00 00 26` type A–E / `00 00 27` volume (app capture 112-03) |
| Temporary save / restore | §4.6 (p.28) | ❌ | ❓ | |

## 5. Tracks and Patterns

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Switch pattern, one track (instant) | §5.1.1 (p.29) | ✅ | ✅ | Track mode encoder 8 (`_adjust_variation`, app.py:2676); device-side changes followed (`30 5p 0F`, app.py:768) |
| Switch pattern, all 11 tracks | §5.1.1 (p.29) | 🟡 | ✅ | Track mode per track; all tracks at once only via Song view scenes now (Session view is the song, `83b9230`) |
| Reserved (launch-quantized) switching | §5.1.1–5.1.2 (p.29–30) | ❌ | ❓ | Push switches instantly only |
| Launch Quantize length | §5.1.3 (p.30) | ❌ | 📱 | `30 40 7A` (app LAUNCH QUANTIZE: 1 / 4 / 16 / 32, capture 103-05) |
| Pattern length | §5.2, §5.2.1 (p.31–32) | 🔵 | ✅ | Buttons 1/2/4/8 bars, encoder 1–128 steps (Shift = a bar), LCD shows steps (`dcfc4b3`); Double Loop doubles (`8ed2c21`). Lengthening copies bars (verified) |
| 3 ⇔ 6 patterns | §5.3 (p.33) | 🔵 | 📱 | Shift + encoder 8 writes `30 40 79` 00/01 (app capture 103-04), read at start (`dcfc4b3`). Global setting in the app |
| Delete current pattern (one track) | §5.4 (p.34) | 🔵 | ✅ | Delete menu [1]; drums now clear all 128 steps (`42d6679`); drum deletes follow the MIDI-selected pattern (verified) |
| Delete current pattern on all tracks | §5.4 (p.34) | 🔵 | ✅ | Delete menu [3] = current pattern on every track, like DELETE+ALL (`dcfc4b3`) |
| Copy / paste pattern | §5.5 (p.34–35) | 🔵 | ✅ | Duplicate (hold): Track / Drums / All, from → to (`8ed2c21`). `77 01 20/21 [track] [pattern]` verified on PERC 2 |
| Select track | §5.6 (p.36) | 🟡 | ✅ | Encoder 1 / CC 20·102 (`_select_next_track`, app.py:4015); Shift+Track overlay (`_handle_track_select_button`, app.py:1087); device-side selects followed (app.py:845). BUGS #1 fix awaiting retest |
| Audition track | §5.6 (p.36) | ✅ | ✅ | Drum/sampler/keyboard pads trigger notes (`_handle_drum_pad`, app.py:3058) |
| Change sound (Drum / Synth / DX) | §5.7 (p.36) | ✅ | ✅ | `_cycle_patch` (app.py:3904): Bank MSB/LSB + PC; name read via `01 1p 35` (app.py:859) |
| Change sound of a SAMPLER pad | §5.7 (p.36) | ✅ | 📱 | Was flagged as a bug; it already sends what the app sends (Bank MSB 62 on the pad's channel, capture 106-16) |
| Category jump | §5.7.1 (p.37) | ❌ | ❓ | Shift+patch encoder jumps 128 presets, not categories (app.py:2575) |
| Mute track | §5.8.1 (p.38) | ✅ | ✅ | Mixer lower row + Push Mute button (`bb115a8`); read back (`30 5p 29`, 7D = muted) |
| Unmute all | §5.8.1 (p.38) | ❌ | ✅ | `30 5p 29 00` × 11 |
| Solo track | §5.8.2 (p.38) | 🔵 | ✅ | One soloed track like the Seqtrak (`30 40 68` / CC 24), un-solo restores mute, DRUM-bus solo mutes the others, read back; Push Solo button (`dcfc4b3`, `bb115a8`) |
| Copy / paste track steps | §5.9 (p.39) | ❌ | ❓ | |

## 6. Drum Tracks

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Enter steps on/off | §6.1 (p.40) | ✅ | ✅ | `_toggle_step` (app.py:3385), `70 0t` / `70 2t`. Velocity fixed at 100 |
| Show steps entered on the Seqtrak | §6.1 (p.40) | ✅ | ✅ | Readback `70 4t` + live reports (app.py:806–816). BUGS #7 verified |
| Show live-recorded steps | §6.5 (p.42) | 🟡 | ✅ | Not reported by the device; polled ~1/s (bug 13) |
| Pages (> 16 steps) | §6.2 (p.40) | ✅ | ✅ | 4 pages × 32 steps (page buttons, app.py:2347 / 2384) |
| Step position / playhead | §6.1 (p.40) | ✅ | — | `_process_playhead` (app.py:3197), timed from tempo (no MIDI clock): may drift, ignores swing |
| Micro timing (−60…+59 ticks) | §6.3 (p.41) | 🔵 | ✅ | Hold a step pad + encoder 1 → `70 [10+t] 00 [step] [60+offset]`; verified from the Pi 2026-10-15; shown from readback byte 4 |
| Substep (none, ×2, ×3 8T, ×3 16T, ×4) | §6.4 (p.41) | 🔵 | ✅ | Hold a step pad + encoder 2 → `70 [10+t] 03` (order none, ×2, ×3 8T, ×3 16T, ×4); verified from the Pi |
| Real-time input + record | §6.5 (p.42) | ✅ | ✅ | Drum pads (`_handle_drum_pad`, app.py:3058) + Record `01 10 21` (app.py:2135) |
| Step probability (8 levels) | §6.6 (p.43) | 🔵 | ✅ | Hold a step pad + encoder 3 → `70 [10+t] 04` (8 levels); stored in `70 [60+t] [step]`, read back; verified from the Pi |
| Track type Drum / DrumKit / Synth | §6.7 (p.44–45) | — | ❓ | Needs firmware 2.0; this unit runs 1.21.3 (skipped, Ace 2026-10-14) |

## 7. Synth Tracks (SYNTH 1, SYNTH 2, DX)

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Real-time play + record | §7.1 (p.46) | ✅ | ✅ | Isomorphic keyboard (`_handle_melodic_pad`, app.py:3501) + Record |
| Record quantize on/off | §7.2 (p.47) | ❌ | 📱 | `00 00 1F`: 00 off, 01 1/32, 02 1/16T, 03 1/16, 04 1/8T, 05 1/8 (capture 105-13) |
| Octave (+2…−3) | §7.3 (p.48) | ✅ | ✅ | Push octave = pad layout; the Seqtrak's octave only shifts its own keys (guide §7.3), so not linked on purpose |
| Scale (8 per project) | §7.4 (p.48) | 🔵 | ✅ | Sent to the Seqtrak (matched by intervals to the project's 8 slots) and followed (`dcfc4b3`) |
| Key | §7.5 (p.49) | 🔵 | ✅ | `30 40 7F` = 0x40 + semitone, sent and followed (`dcfc4b3`) |
| MONO / POLY / CHORD | §7.6 (p.49) | ✅ | ✅ | Device page 1 "Mode", CC 26 (app.py:252) |
| Edit chords | §7.7 (p.50) | ❌ | 📱 | `30 6p 00–1B` chord notes (capture 105-08) |
| Keyboard input mode | §7.8 (p.51) | ✅ | — | Push pads are always a keyboard (app.py:1486) |
| Step input: notes on/off per step | §7.9 (p.51) | ❌ | ✅ | No melodic step grid yet. Add / read / remove verified (SYNTH 1); find `76`, replace `73` from the app (LE-03) |
| Step input: add/remove notes, chords per step | §7.9 (p.52) | ❌ | ✅ | Note list holds several notes per position |
| Step input: note length | §7.9 (p.52) | ❌ | ✅ | Last two bytes of the 8-byte note |
| Step input: micro timing | §7.9 note (p.52) | ❌ | ❓ | Presumably an off-grid tick |

## 8. SAMPLER Track

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Real-time play 7 samples + record | §8.1 (p.53) | ✅ | ✅ | `_handle_sampler_pad` (app.py:3601): ch 11, notes 60–66 |
| Sample into a pad (mic / AUDIO IN / USB) | §8.2 (p.53) | ✅ | ✅ | Shift+Record (app.py:2120): `01 10 28` pad + `01 10 22` |
| Sampling source | §8.3 (p.54) | ❌ | 📱 | `00 00 19` 00 USB, 01 MIC/LINE, 02 RESAMPLING (sampler parked until after core) |
| Resampling | §8.4 (p.54) | ❌ | ✅ | Sampling source = Resampling |
| Cancel sampling | §8.5 (p.54) | ❌ | ❓ | |
| Sampling count-in | §8.6 (p.55) | ❌ | 📱 | `00 00 1B` |
| Monitoring mode (input meter) | §8.7 (p.55) | ❌ | ❓ | |
| Auto-normalize | §8.8 (p.56) | ❌ | 📱 | `00 00 1C` |
| Delete pattern of one sample | §8.9 (p.56) | ❌ | ✅ | Read list, remove that pad's indexes |
| Step input per pad | §8.10 (p.56) | ✅ | ✅ | `_toggle_sampler_step` (app.py:3445); BUGS #2 solved; pad select both ways (`01 10 28`, app.py:833 / 3668) |
| Step note length | §8.10 (p.57) | 🟡 | ✅ | Automatic only: rings to the pad's next step (`_sampler_ring_length`, app.py:3440); no manual edit |
| Step micro timing | §8.10 note (p.57) | ❌ | ❓ | |
| Mute a sample | §8.11 (p.58) | ❌ | 📱 | `30 40 63` bit mask (capture 109-03) |

## 9. Sound Design

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Parameter pages + advanced pages | §9.1.1 (p.60) | ✅ | — | Device mode pages via page buttons (app.py:2338 / 2375) |
| Drum params (sound, pitch, pan, vol, attack, decay, filter, reso, sends, EQ) | §9.1.2 (p.60) | 🔵 | ✅ | Ranges clamped to the guide (§18.3.1); values read back and followed from the Seqtrak's knobs (`dcfc4b3`, `2474f4d`) except cutoff/reso |
| Synth params incl. porta, arp type/gate/speed | §9.1.3 (p.61) | 🔵 | ✅ | Ranges clamped; vol/pan/sends/EQ/mono-poly/porta read back; arp/filter not |
| DX params incl. FM algorithm/mod amount/freq/feedback | §9.1.4 (p.62) | 🟡 | ✅ | FM macros CC 116–119 have no readable SysEx; full engine is in the app capture (113-2x) |
| SAMPLER params pages 1–3 | §9.1.5 (p.63) | 🟡 | ✅ | `DEVICE_PARAMS_SAMPLER` (app.py:305): no PITCH (no sampler CC in §18.3); whole track vs selected pad ❓. Bug 5 |
| SAMPLER start / end / loop on-off / loop length | §9.1.5 (p.63) | ❌ | 📱 | `50 eA 66/6A/5F/60` (4×7-bit frames); length readable at `01 1[e] 40` (sampler parked) |
| SAMPLER pitch EG (PEG) | §9.1.5 (p.63) | ❌ | 📱 | `41 eA 58–64` (sampler parked) |
| Pitch per step (synth, step input) | §9.1.3 note (p.61) | ❌ | ❓ | |
| Parameter Lock | §9.2 (p.64) | ❌ | ❓ | Purple steps; Push shows every step green (STEP-SEQUENCER §2) |
| Delete Parameter Lock (pattern / step) | §9.2.1 (p.65–66) | ❌ | ❓ | |
| Motion Recording | §9.3 (p.67) | ❌ | ❓ | Untested whether Push CCs during recording become motion |
| Delete Motion | §9.3.1 (p.67) | ❌ | ❓ | |
| Undo / Redo | §9.4 (p.68) | 🔵 | ✅ | Push Undo (CC 119) → `01 10 1F 01`, verified from the Pi (`2474f4d`) |
| Save sound (+ favorite) | §9.5 (p.68) | ❌ | 🟡 | Favourite = bulk write `10 01 03` (capture EX-18); save ❓ |
| Delete / import sounds | §9.6–9.7 (p.68–69) | — | ❓ | App-only |

## 10. Effects

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Single (track) effect type | §10.1.1, §10.2.2 (p.70, 73) | ❌ | ✅ | `31 2p 00` (MSB LSB = Data List effect type list, matched in capture 108-70) |
| Single effect parameters 1–3 | §10.2.5 (p.74) | ❌ | 📱 | `31 2p 03, 05, …` (capture 108-71) |
| Track LP-HP filter | §10.1.1 (p.70) | ✅ | ✅ | Device Cutoff/Reso, CC 74/71 |
| Track 2-band EQ | §10.1.1 (p.70) | ✅ | ✅ | Device EQ Hi/Lo, CC 20/21 (range bug 6) |
| Reverb / Delay send level per track | §10.1.2 (p.71) | ✅ | ✅ | Device Reverb/Delay, CC 91/94 |
| Master effect type (8 categories × 8) | §10.2.2 (p.73) | ❌ | ✅ | `30 43 00`; every type the app picked matched the Data List (108-01) |
| Master effect params (FX LEVEL, page 2) | §10.2.4 (p.74) | ❌ | ✅ | CC 102–104 ch 1; constants in protocol.py:119, not wired |
| HIGH PASS slider | §10.1.3 (p.72) | ❌ | ✅ | Likely CC 105 (master effect 2): mapping inferred |
| REPEATER slider | §10.1.3 (p.72) | ❌ | ✅ | Likely CC 106 (master effect 3): mapping inferred |
| Master compressor | §10.1.3 (p.72) | ❌ | 📱 | `30 46` (type, ON/OFF `30 46 47`, params; capture 108-5x) |
| Master 5-band EQ | §10.1.3 (p.72) | ❌ | 📱 | `30 47 00–14` gain/freq/Q per band (capture 108-60) |
| CLEAR FX | §10.3 (p.74) | ❌ | ❓ | |

## 11. Mixer Mode

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| VOLUME per track | §11.2 (p.75) | 🔵 | ✅ | Mixer encoders; read back at start and followed (`dcfc4b3`, `2474f4d`) |
| PAN per track | §11.2 (p.75) | 🟡 | ✅ | Only in Device mode, one track at a time |
| REVERB / DELAY SEND per track | §11.2 (p.75) | 🟡 | ✅ | Only in Device mode, one track at a time |
| Project volume (ALL knob) | §11.2 (p.76) | ❌ | ✅ | `30 40 66` (P0-PROBE). Push master knob sets the speaker volume |
| Project pan (ALL knob) | §11.2 (p.76) | ❌ | 🟡 | `30 40 65` |
| Reverb / Delay return level | §11.2 (p.76) | ❌ | 📱 | `30 41 44` / `30 42 44` (captures 108-31, 108-41) |
| Send effect type (8 presets each) | §11.3.1 (p.76) | ❌ | ✅ | `30 41 00` / `30 42 00` (matched the Data List, 108-30/40) |
| Send effect parameters | §11.3.2 (p.76–77) | ❌ | 📱 | `30 41 03…`, `30 42 03…` (108-32, 108-42) |

## 12. Mute Mode

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| One-press mute per track | §12.1–12.2 (p.78) | ✅ | ✅ | Mixer lower row + Push Mute button for the selected track (`bb115a8`) |
| Unmute all | §12.2 (p.78) | ❌ | ✅ | `30 5p 29 00` × 11 |

## 13. Song Mode

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Enter / exit Song mode | §13.1 (p.79) | 🔵 | ✅ | Song view (Session) button 1 / Shift+Session: `01 10 17` 02/00, verified from the Pi (`83b9230`) |
| Scene mode (loop one scene) | §13.1.1 (p.79) | 🔵 | ✅ | `71 50 00` 01/00, verified (leaving it also leaves Song mode) |
| Play / stop scenes in order | §13.2 (p.80) | 🔵 | ✅ | Play/Stop in Song mode; playing scene followed (`71 10 04`) |
| Change scene | §13.2.1 (p.80) | 🔵 | ✅ | Launch buttons → `71 10 04`, verified stopped; while playing untested |
| Loop a scene | §13.2.2 (p.81) | 🔵 | 📥 | Double-press a launch button → `71 10 07` (device report; untested as a command) |
| Loop whole song | §13.2.3 (p.81) | 🔵 | 📱 | Song view button 8 → `71 10 06` |
| Add scene (up to 16) | §13.3 (p.82) | 🔵 | ✅ | Dim pad under the last scene → `71 00 00 [scene]`, verified |
| Delete scene | §13.4 (p.82) | 🔵 | ✅ | Delete + launch button → `71 20 00 [scene]`, verified |
| Edit scene patterns / mute / solo | §13.5.1 (p.83) | 🔵 | 📱 | Encoders → `71 [10+t] 01`; hold Mute/Solo + pad → `71 [10+t] 02` / `71 10 03` |
| Scene length (incl. AUTO) | §13.5.2 (p.83–84) | 🔵 | ✅ | Master encoder in Song view: AUTO or 1–96 bars (`71 10 00`), verified |

## 14. SEQTRAK App: app-only features (listed separately)

These aren't on the Seqtrak's panel; parity here is optional.

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| LFO per track | §14.1 (p.85) | ❌ | 📱 | `31 4p 01–0C` (captures 113-01…12) |
| Alternate (choke) groups | §14.1 (p.85) | ❌ | ✅ | Group Number `30 5p 08` |
| All FM engine params (DX) | §14.1 (p.85) | ❌ | 📱 | `48 09` / `49 o9` (captures 113-2x…5x) |
| Deep sound / element params | §14.1 (p.85) | ❌ | 🟡 | `31 1p`, `41 ep`, `42 ep` |
| Scale editing | §7.4 note (p.48) | ❌ | 📱 | `30 4D [16*slot + n]` (capture 105-12) |
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
| Wi-Fi on/off | §15.1.3 (p.90) | ❌ | 🟡 | Wireless LAN `00 00 16` (FUNCTIONALITY-MAP §4); not captured |
| MIDI conversion cable | §15.2.2 (p.92) | — | — | Physical |

## 16. Settings

| Feature | Guide § (page) | On Push | Protocol | Notes |
|---|---|---|---|---|
| Factory reset | §16.1 (p.93) | — | ❓ | Power-on key combo |
| Track knob sensitivity | §16.2 (p.93) | ❌ | 📱 | `00 00 2F` 01 fast / 02 normal / 03 slow (capture 112-13a) |
| MIDI clock (sync, clock out) | §16.3.1 (p.93) | ❌ | 📱 | `00 00 2A` / `00 00 2D` (capture 112-07) |
| MIDI output filters | §16.3.2 (p.93) | ❌ | 📱 | Per port `00 00 0A–14` (capture 112-08…10) |
| MIDI Thru | §16.3.3 (p.93) | ❌ | 🟡 | System block |
| Master volume (speaker) | §16.4 (p.94) | ✅ | ✅ | Master encoder CC 79 (app.py:2591) → `00 00 00`; read at start + followed (app.py:819) |
| Headphone master volume | §16.4 (p.94) | ❌ | 🟡 | `00 00 01`: Push only writes the speaker volume |

---

## Push-only extras (not in the guide)

Software arpeggiator and note repeat (app.py:2743–2994; BUGS #5 asks how they should interact), accent /
fixed velocity, DRUM bus (volume, mute, solo; app.py:3751), Session view launcher, iPad audio routing
(Shift+User settings, app.py:1393).
