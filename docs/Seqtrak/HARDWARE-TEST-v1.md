# Seqtrak Bridge v1.0: Hardware Test

**Goal**: confirm on the real rig everything that is built but untested, then call the bridge v1.0. As of
2026-10-25, 28 Linear issues sit in **In Review** (built, verified from the Pi, never tried by hand), plus 3
fixes that aren't deployed yet. Each line below is one check: do it, tick it, or note what happened.

Afterwards: report the numbers that failed. Passes get closed in Linear; failures become short bugs under
KM-100. When the list is clear, tag `v1.0`.

## Before you start

- [ ] **0.1 Deploy the current commit to pibridge** (adds `2c71b5f`, `4f8ed89`, `ab497a5`; the Pi runs `4280445`).
- [ ] **0.2 Use a project you don't mind changing.** Several checks edit patterns, delete and add scenes.
- [ ] **0.3 Start the service with the Seqtrak on.** The Push shows **SYNCING** until the project is read, then
  the normal view (`2c71b5f`).

## 1. Start-up: the Push shows the Seqtrak's real state (KM-118, KM-141, KM-115, KM-124)

Before starting, set a few values **on the Seqtrak**: one track muted, swing not 0, metronome on, a key other
than C.

- [ ] **1.1** Mixer: track volumes, pans and the muted track match the Seqtrak. *(KM-118)*
- [ ] **1.2** Device mode: turn a knob a little. It moves from the Seqtrak's value, **no jump**. Try volume, pan,
  EQ, a drum pitch. *(KM-118. Not expected to match yet: cutoff, resonance, synth decay, arp, FM macros.)*
- [ ] **1.3** The swing value and the metronome LED match the Seqtrak. *(KM-118, KM-141)*
- [ ] **1.4** The Push pads use the Seqtrak's key and scale. *(KM-124)*
- [ ] **1.5** Change volume, mute and key **on the Seqtrak** while running: the Push follows. *(KM-118, KM-124)*

## 2. Transport and global knobs (KM-141, KM-120, `4f8ed89`)

- [ ] **2.1** Push **Metronome**: the click turns on and off, LED follows. Toggle it on the Seqtrak: the LED follows. *(KM-141)*
- [ ] **2.2** Tempo encoder down to **5 BPM** and up to **300**: the Seqtrak shows the same. *(KM-120; swing already passed)*
- [ ] **2.3** Master, tempo and swing knobs do the same thing in **every** mode (they never change job). *(`4f8ed89`)*

## 3. Mixer: mute and solo (KM-127, KM-122, KM-116)

- [ ] **3.1** Push **Mute** mutes the selected track, **Solo** solos it; the Seqtrak's track LEDs agree. *(KM-127)*
- [ ] **3.2** Mute a track, solo it, un-solo it: it is **muted again**. *(KM-122)*
- [ ] **3.3** **DRUM-bus solo**: all 7 drum tracks play, SYNTH 1/2, DX and SAMPLER are silent. Un-solo: every
  track's earlier mute comes back. *(KM-116)*

## 4. Sound (KM-119, KM-176)

- [ ] **4.1** Turn Pitch, EQ Hi/Lo fully left and right: the LCD stops at **40–88**. Arp Type stops at 0–16,
  Arp Speed at 0–9. *(KM-119)*
- [ ] **4.2** Change a sound parameter, press Push **Undo**: it goes back on the Seqtrak. **Undo** again: redo. *(KM-176)*

## 5. Patterns (KM-115, KM-121, KM-146, KM-123)

- [ ] **5.1** Track mode, **Shift + encoder 8**: 3 ⇔ 6 patterns. The Seqtrak's Drum keys 4–6 change between
  blue and white. Change it on the Seqtrak: the Push follows. *(KM-115; note whether it's per track or for all tracks)*
- [ ] **5.2** Bar length buttons step **1 / 2 / 4 / 8 bars**. The encoder sets **24 steps**; the Seqtrak shows
  24 and the length isn't reset by the next button press. *(KM-121)*
- [ ] **5.3** **Double Loop**: the pattern doubles and the new bars are copies. *(KM-121)*
- [ ] **5.4** **Hold Duplicate**: copy panel. Copy pattern 1 → 2 of one track: pattern 2 now plays the same
  notes and length. Try Drums and All too. *(KM-146)*
- [ ] **5.5** Put different patterns on different tracks, then Delete menu **[3]**: exactly those current
  patterns empty; the other patterns keep their steps. *(KM-123)*

## 6. Step sequencer (KM-149, KM-150, KM-151, KM-114, `ab497a5`)

- [ ] **6.1** Hold a lit drum step pad + **encoder 1**: micro timing. The step audibly moves. Hold two pads:
  both move. *(KM-149)*
- [ ] **6.2** Hold step pad(s) + **encoder 2**: substep off, ×2, ×3 8T, ×3 16T, ×4. Each is audible. *(KM-150)*
- [ ] **6.3** Hold step pad(s) + **encoder 3**: 8 probability levels. The Seqtrak's Global Meter shows the same
  level. *(KM-151)*
- [ ] **6.4** Set micro timing, a substep and probability **on the Seqtrak**: the Push shows them. *(KM-149–151)*
- [ ] **6.5** **Record live** (Push pads and Seqtrak keys): notes appear on the Push grid while recording (about
  once a second) and are all there after stopping. *(KM-114)*
- [ ] **6.6** **Delete a pattern on the Seqtrak**: after Delete is released, the Push grid matches. *(KM-114)*
- [ ] **6.7** A **128-step** drum pattern, Push delete menu: steps 65–128 are cleared too. *(KM-114)*
- [ ] **6.8** SAMPLER track with a parameter lock (e.g. pitch on one step): the lock is **not** shown as an extra
  step. *(`ab497a5`)*

## 7. Projects (KM-136, KM-114)

- [ ] **7.1** Push **Browse** opens the project picker; a top LCD button loads another project. Its Drum key
  lights yellow on the Seqtrak, and the Push re-reads everything (step grid, mixer). *(KM-136, KM-114)*
- [ ] **7.2** Switch project **on the Seqtrak**: the Push re-reads and shows the new project. *(KM-136, KM-114)*

## 8. Song mode (KM-195–KM-204)

Open the Song view (Session).

- [ ] **8.1** Button 1 (or **Shift + Session**) cycles **Normal → Song → Scene**; the Seqtrak's [SONG] light
  agrees. Change it on the Seqtrak: the Push follows. *(KM-195)*
- [ ] **8.2** In Song mode, press the **dim pad under the last scene**: a new scene, a copy of the current one.
  Add up to 16. *(KM-201)*
- [ ] **8.3** Select a scene. **Encoders** set each track's pattern; **hold Mute / Solo + pad** sets per-scene
  mute/solo. Playing that scene uses them. *(KM-203; the Push only shows what it set)*
- [ ] **8.4** **Master encoder** sets the scene length: AUTO, or 1–96 bars. The scene plays for that long.
  Shift + master = master volume. *(KM-204)*
- [ ] **8.5** **Play / Stop** in Song mode: the song plays from the selected scene, in order; the Song view
  follows the playing scene. *(KM-197)*
- [ ] **8.6** **While playing**, press another **scene launch button**: does it queue until the current scene
  ends (Song mode) or start at the Launch Quantize timing (Scene mode)? Note which. *(KM-198)*
- [ ] **8.7** **Double-press** the playing scene's launch button: it loops. Double-press again or pick another to
  cancel. *(KM-199: the command itself is untested; likely to need work)*
- [ ] **8.8** Song view **button 8**: song loop on. The song restarts after the last scene; off, it stops. *(KM-200)*
- [ ] **8.9** **Scene mode**: one scene loops; leaving Scene mode also leaves Song mode, like the device. *(KM-196)*
- [ ] **8.10** **Delete + scene launch button**: the scene goes, later scenes move up. Try the **playing**
  scene: it is refused. *(KM-202)*

## Results

| # | Pass / fail | What happened |
|---|---|---|
| | | |

Related: `PARITY.md` (where each bug came from), `BUGS_AND_ENHANCEMENTS.md`, Linear KM-100 (bugs),
KM-111 (Song mode), KM-104 (step sequencer). KM-132 (copy/paste, undo, CLEAR FX test sheet) overlaps 4.2 and 5.4.
