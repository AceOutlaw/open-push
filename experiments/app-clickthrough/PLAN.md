# SEQTRAK App Click-Through — Shared Plan

Two sessions work together:

- **Cowork Claude (the "clicker")** drives the SEQTRAK app on skai and changes one control at a time.
- **Claude Code (the "capturer")** records what the app sends to the Seqtrak (MIDI Monitor spy on output → SEQTRAK, or whatever capture method it chooses), then decodes it into `docs/Seqtrak/`.

The Seqtrak has a **scratch project** loaded. Values can be changed freely.

Parent issue: **KM-101 Protocol discovery**. Blocks are grouped by the Linear epics KM-102…KM-113.

---

## 1. Files (all in `experiments/app-clickthrough/`)

| File | Written by | Purpose |
|---|---|---|
| `PLAN.md` | both | This plan. The block list (section 5) gets filled in after Phase 0. |
| `status` | both | One-line handshake (section 2). |
| `clicklog.md` | clicker | One line per action: time, block ID, control, value **as the app displays it**. |
| `captures/<BLOCK-ID>.txt` | capturer | Raw capture for exactly one block. |
| `screens/` | clicker | Phase 0 screenshots and notes on each app screen. |

## 2. Handshake: one capture per block

`status` always holds a single line, which is the current state:

```
READY <ID>     clicker: about to start block <ID>, waiting for capture
ARMED <ID>     capturer: capture running for <ID>, go ahead
DONE <ID>      clicker: last action of <ID> finished (wait ~3 s after it before writing this)
SAVED <ID>     capturer: captures/<ID>.txt saved. Clicker may begin the next block.
HOLD <reason>  either side: stop. A human checks before anything continues.
```

- The clicker never starts a block until it reads `ARMED <ID>`. The capturer never stops a capture until it reads `DONE <ID>`.
- Both sides poll `status` every few seconds.
- If anything unexpected happens (an app dialog, the device disconnecting, a value that won't change), write `HOLD` and explain in `clicklog.md`.

## 3. Rules for every block

1. **One control per block.** The block ID is the capture file name.
2. **Transport stopped** unless the block says otherwise.
3. **About 3 s between actions** inside a block.
4. **Sequence by control type:**
   - **Continuous** (slider, knob): original → min → max → 3 spaced values in between → original. Log the value the app displays after each move.
   - **Enum** (type, category, scale, etc.): step through **every option in order** and log the name shown for each one. This gives the value → name map. Then go back to the original.
   - **Toggle or button:** on → off, or press once, then back.
   - **Navigation only** (tab, track select, page): one press per target. These may send SysEx too (e.g. track select `01 10 27`), so they are captured as well.
5. **Log format** in `clicklog.md`:
   `- HH:MM:SS | <ID> | <screen> > <control> | <action> | shown: <value>`
6. **Never touched:** factory reset, delete or overwrite project, delete sound or sample, firmware update, Bluetooth/Wi-Fi pairing changes, anything that leaves the app or affects the account.

## 4. Phases

### Phase 0: Screen inventory (block `P0-NAV`, one capture)
The clicker visits every tab, sub-page and track in the app **without changing any values**, and takes a screenshot of each. This produces:
- `screens/` with one image per screen and a list of its controls (name, type, displayed range or options).
- The full block list in section 5, mapped to epics.

The capture of this pass tells us what navigation alone sends.

**Checkpoint:** Ace reviews the block list before Phase 1.

### Phase 1: Blocks by epic
The order runs from the most-blocked and app-only features to the parts that are already mostly mapped:

| Order | Epic | App area (expected; confirm in Phase 0) |
|---|---|---|
| 1 | KM-113 App-only features | LFOs, choke groups, DX/FM engine parameters, advanced mixer/song settings |
| 2 | KM-108 Effects | MASTER > Effect, track single FX, Send (reverb/delay), Comp & EQ |
| 3 | KM-107 Sound Design | DRUMS / SYNTHS / SAMPLER parameter pages (all pages, all track types) |
| 4 | KM-109 Mixer | MASTER > Overview volume / pan / sends; per-track mixer |
| 5 | KM-105 Synth Tracks | Octave, scale, key, arp, quantize, chords |
| 6 | KM-106 SAMPLER | Pad params, start/end/loop, sampling source |
| 7 | KM-104 Drum Tracks | Step edits, micro timing, substeps, probability (if exposed in the app) |
| 8 | KM-103 Tracks & Patterns | Pattern 1–6 select, pattern length, launch quantize |
| 9 | KM-110 Mute / KM-111 Song Mode | Mute, solo, scenes and song |
| 10 | KM-112 Connections & Settings | SETTINGS tab: metronome, MIDI filters, sync, knob sensitivity |
| 11 | KM-102 Projects | HOME / project manager (non-destructive actions only) |

**Checkpoint after each epic:** the capturer confirms every capture file is clean (one block, nothing unrelated). Any block that isn't clean is re-run before the next epic starts.

### Phase 2: Decode (capturer)
Per KM-101's definition of done: decode, verify commands by readback (Parameter Request) or on the device, write the results into `sysex-protocol-reference.md` / `STEP-SEQUENCER.md` with ✅/🟡/❓ status, update `PARITY.md`, and update the blocked Linear issues.

## 5. Block list

Draft written after P0-NAV (2026-10-14 00:28). **Ace reviews this before Phase 1.**
Full screen inventory: `screens/INVENTORY.md`. Status: todo / done / skip.
Unless a row says otherwise, the track is the first of its type (KICK, SYNTH 1, DX, SAMPLER) and the page is the GUI EDITOR.
Where a parameter repeats per track, run one track first; repeat on others only if the capturer asks.

| ID | Epic | Screen > control | Type | Options / range shown | Status |
|---|---|---|---|---|---|
| P0-PROBE | KM-101 | MASTER > Overview > Volume 127→98→127 | continuous | 0–127 | done |
| P0-NAV | KM-101 | All screens, navigation only | nav | — | done |
| **KM-113 App-only** | | | | | |
| 113-01 | KM-113 | DRUMS KICK > SOUND DESIGN > LFO > DEPTH | continuous | 0–127 | todo |
| 113-02 | KM-113 | … LFO > DELAY | continuous | 0–127 | todo |
| 113-03 | KM-113 | … LFO > DESTINATION | enum | all options | todo |
| 113-04 | KM-113 | … LFO > TEMPO SYNC | toggle | off/on | todo |
| 113-05 | KM-113 | … LFO > SPEED (sync off, then sync on) | continuous | 0–63 | todo |
| 113-06 | KM-113 | … LFO > SHAPE | enum | all options | todo |
| 113-07…12 | KM-113 | Repeat 113-01…06 on SYNTH 1 | — | — | todo |
| 113-13 | KM-113 | SETTINGS > DRUM CHOKE > HAT (HAT1–HAT2) | toggle | off/on | todo |
| 113-14 | KM-113 | SETTINGS > DRUM CHOKE > PERC (PERC1–PERC2) | toggle | off/on | todo |
| 113-20 | KM-113 | DX > ALGORITHM | enum | 12 tiles | todo |
| 113-21…28 | KM-113 | DX > OPERATORS OP1: ON/OFF, MODE, FREQ, DETUNE, LEVEL, VEL.S, FEEDBACK, KSC.R | 1 block each | — | todo |
| 113-29…32 | KM-113 | DX OP1 EG: ATTACK/DECAY1/DECAY2/RELEASE TIME + LEVEL (8 controls, 1 block each → 113-29a…h) | continuous | 0–127 | todo |
| 113-33…36 | KM-113 | DX OP1 KSC: L DEPTH, L MODE, R DEPTH, R MODE | — | -127…+127 / LIN-EXP | todo |
| 113-37 | KM-113 | DX OP2–OP4: one control (LEVEL) each, to learn the operator offset | continuous | 0–127 | todo |
| 113-40…48 | KM-113 | DX > PITCH EG: LEVEL1–4, TIME1–4, OP1–OP4 switches | — | ±48 / 0–127 / on-off | todo |
| 113-50…55 | KM-113 | DX > LFO: DELAY, SPEED, PMD, WAVE, PMD per-op switch (OP1), AMD per-op (OP1) | — | — | todo |
| **KM-108 Effects** | | | | | |
| 108-01 | KM-108 | MASTER > EFFECT > MASTER EFFECT > CATEGORY | enum | all | todo |
| 108-02 | KM-108 | … MASTER EFFECT > TYPE (within each category) | enum | all | todo |
| 108-03 | KM-108 | … MASTER EFFECT params, current type (one block per param, pages 1–2) | continuous | — | todo |
| 108-10…13 | KM-108 | Same as 108-01…03 for EFFECT 1 | — | — | todo |
| 108-20…23 | KM-108 | Same for EFFECT 2 (pages 1–3) | — | — | todo |
| 108-30 | KM-108 | SEND 1 REVERB > REVERB TYPE | enum | all | todo |
| 108-31 | KM-108 | … RETURN VOL | continuous | 0–127 | todo |
| 108-32 | KM-108 | … REVERB params (10, one block each) | continuous | — | todo |
| 108-40…42 | KM-108 | SEND 2 DELAY: TYPE, RETURN VOL, params (9) | — | — | todo |
| 108-50…52 | KM-108 | COMP: TYPE, ON/OFF, params (11) | — | — | todo |
| 108-60 | KM-108 | 5 BAND EQ: GAIN/FREQ/Q × 5 bands (15 blocks, 108-60a…o) | continuous | — | todo |
| 108-70…72 | KM-108 | Track effect (DRUMS KICK > EFFECT): CATEGORY, TYPE, params; then check whether PERC2 shares it | — | — | todo |
| 108-73 | KM-108 | Track effect on SYNTH 1, DX, SAMPLER (one param each, to learn the per-track offset) | continuous | — | todo |
| 108-74 | KM-108 | MAP button (any effect) — see what it opens | nav | — | todo |
| **KM-107 Sound Design** | | | | | |
| 107-01…06 | KM-107 | DRUMS KICK overview: PITCH, PAN, VOLUME, ATTACK, DECAY, CHOKE | — | — | todo |
| 107-07…09 | KM-107 | DRUMS KICK FILTER: type icons, FREQ, RES | — | — | todo |
| 107-10…15 | KM-107 | DRUMS KICK EQ SEND: GAIN LOW/HIGH, FREQ LOW/HIGH, SEND 1, SEND 2 | continuous | — | todo |
| 107-20…29 | KM-107 | SYNTH 1: same as above + MONO/POLY, PORTAMENTO ON/OFF + TIME | — | — | todo |
| 107-30 | KM-107 | SAMPLER: FILTER FREQ/RES, SEND 1/2, GUIDE WAVEFORM knob | — | — | todo |
| 107-31 | KM-107 | GUIDE panel knobs (SOUND, PITCH or MONO/POLY, PAN, VOLUME) on KICK | continuous | — | todo |
| **KM-109 Mixer** | | | | | |
| 109-01 | KM-109 | PERFORM > MIXER fader, KICK (then 1 synth track) | continuous | 0–127 | todo |
| 109-02 | KM-109 | PERFORM > SEND faders (SEND1 view, then SEND2 view), KICK | continuous | 0–127 | todo |
| 109-03 | KM-109 | PERFORM > SAMPLER SAMPLE 1 fader + MUTE | — | — | todo |
| 109-04 | KM-109 | HOME > SETTINGS > HARDWARE > MASTER VOLUME SPEAKER | continuous | 0–127 | todo |
| 109-05 | KM-109 | HARDWARE > OUTPUT GAIN SPEAKER/PHONES, USB AUDIO | enum | -6/0/+6/+12 | todo |
| **KM-105 Synth Tracks** | | | | | |
| 105-01…06 | KM-105 | SYNTH 1 ARP: ON, MODE, TYPE (all), SPEED (all), GATE, OCTAVE | — | — | todo |
| 105-07…09 | KM-105 | SYNTH 1 CHORD: MODE, CHORD PACK (all), one chord pad | — | — | todo |
| 105-10 | KM-105 | SETTINGS > KEY | enum | 12 keys | todo |
| 105-11 | KM-105 | SETTINGS > SCALE | enum | 8 slots | todo |
| 105-12 | KM-105 | SETTINGS > SCALES IN THIS PROJECT: assign one slot from SCALE LIST, then restore | enum | — | todo |
| 105-13 | KM-105 | SETTINGS > ADVANCED > LIVE REC QUANTIZATION | enum | all | todo |
| **KM-106 SAMPLER** | | | | | |
| 106-01 | KM-106 | SAMPLER > SAMPLES pad 1–7 select | nav | — | todo |
| 106-02 | KM-106 | RECORD SETTINGS > NORMALIZE | toggle | off/on | todo |
| 106-03 | KM-106 | RECORD SETTINGS > SOURCE | enum | all | todo |
| 106-04 | KM-106 | Find start/end/loop UI (pads, GUIDE WAVEFORM) | nav | — | todo |
| **KM-104 Drum Tracks** | | | | | |
| 104-01 | KM-104 | KICK PATTERN editor: turn one empty step on, then off | toggle | — | todo |
| 104-02 | KM-104 | Step row micro slider (micro timing) | continuous | — | todo |
| 104-03 | KM-104 | BARS / STEPS fields | enum | — | todo |
| 104-04 | KM-104 | Pattern editor page dots / NEXT with steps on later pages | nav | — | todo |
| 104-05 | KM-104 | SYNTH 1 PATTERN > EDIT (piano roll): add one note, remove it | — | — | todo |
| **KM-103 Tracks & Patterns** | | | | | |
| 103-01 | KM-103 | Track PATTERN 1–6 buttons (KICK) | enum | 1–6 | todo |
| 103-02 | KM-103 | PERFORM > PATTERN grid (one cell per track type) | enum | — | todo |
| 103-03 | KM-103 | COPY / PASTE pattern (paste into an empty pattern) | button | — | todo |
| 103-04 | KM-103 | SETTINGS > PATTERNS 3↔6 | toggle | — | todo |
| 103-05 | KM-103 | SETTINGS > ADVANCED > LAUNCH QUANTIZE | enum | all | todo |
| 103-06 | KM-103 | Track TYPE selector DRUM / DRUMKIT / SYNTH on PERC2 (v2.0, KM-34), then restore | enum | 3 | todo |
| **KM-110 Mute / KM-111 Song** | | | | | |
| 110-01 | KM-110 | PERFORM > MIXER MUTE (KICK) | toggle | — | todo |
| 110-02 | KM-110 | PERFORM > MIXER SOLO (KICK) | toggle | — | todo |
| 111-01 | KM-111 | PERFORM > SONG: "+" add scene, then remove it | button | — | todo |
| 111-02 | KM-111 | SONG loop button | toggle | — | todo |
| **KM-112 Connections & Settings** | | | | | |
| 112-01 | KM-112 | BPM field (▲▼ in popup) | continuous | — | todo |
| 112-02 | KM-112 | SWING | continuous | — | todo |
| 112-03 | KM-112 | Metronome popup: CLICK SOUND, VOLUME, TYPE, beat 1–4 select | — | — | todo |
| 112-04…09 | KM-112 | SETTINGS > ADVANCED: ADVANCED SOUND DESIGN, NOISE GATE, COUNT-IN, MASTER FX (MIC/LINE IN), INPUT VELOCITY, PLAYBACK MODE AFTER PROJECT SWITCH, MASTER FX (USB) | — | — | todo |
| 112-10 | KM-112 | MIDI COMMON: CLOCK SEND, SYNC | toggle | — | todo |
| 112-11 | KM-112 | MIDI ADVANCED: START/STOP SEND | toggle | — | todo |
| 112-12 | KM-112 | MIDI ADVANCED per port (MIDI CABLE, then BLUETOOTH; **USB last**): CC / BANK / PC / SysEx send, THRU. Restore at once. | toggle | — | todo |
| 112-13 | KM-112 | HARDWARE: KNOB SENSITIVITY, AUTO POWER OFF | enum | — | todo |
| 112-14 | KM-112 | Transport Play ▶ / stop | button | — | todo |
| **KM-102 Projects** | | | | | |
| 102-01 | KM-102 | PROJECT name field (rename, then restore) | text | — | todo |
| 102-02 | KM-102 | PROJECT/SOUND MANAGER: open PROJECTS (read only; no backup/load/delete) | nav | — | todo |

**Skipped on purpose:** DELETE (pattern / project / sound), LOAD backup project, FULL BACKUP, CREATE PROJECT, MIDI IMPORT/EXPORT, firmware UPDATE, Wi-Fi settings, VISUALIZER, APP settings, docs tiles.

## 6. Capture method (capturer, updated 2026-10-14 00:15)

**Setup:** the Seqtrak is plugged into **skai by USB** (moved off the Pi). It shows up in CoreMIDI as `SEQTRAK`.
The capturer runs its own recorder, `seqspy`, which uses MIDI Monitor's spy driver:
- **OUT** lines = every byte any Mac app sends **to** the Seqtrak (the app's actual commands).
- **IN** lines = everything the Seqtrak sends back (replies and its own reports).
- Log: `spy.log` in this folder (2026-10-14 run kept as `raw-spy-2026-10-14.log`), local time, ms resolution. See `README.md` to run it.
  Clock and Active Sensing are dropped. Verified 00:13: a Parameter Request showed as OUT and its reply as IN.
- MIDI Monitor's window is **not** needed for the capture, so the clicker can ignore it.
- Handshake is automatic: on `READY <ID>` the capturer writes `ARMED <ID>` within ~2 s; on `DONE <ID>` it
  saves that time slice to `captures/<ID>.txt` and writes `SAVED <ID>`.

**The app must talk to the Seqtrak over USB, not Bluetooth.** Over Bluetooth its messages bypass CoreMIDI
and nothing is captured. Before P0-PROBE the clicker checks the app's connection screen and picks the
USB/`SEQTRAK` connection if there is a choice. ❓ If the app only offers Bluetooth, `HOLD`; Ace can turn the
Mac's Bluetooth off so the app falls back to USB.

**Block `P0-PROBE` (run first, before P0-NAV):** in MASTER > Overview change **Volume** 127 → 100 → 127
(3 s apart).
- `captures/P0-PROBE.txt` has OUT lines → capture method works, continue with P0-NAV.
- No OUT lines → the app isn't using USB. Capturer writes `HOLD app not on USB`.

## 7. Known so far
- The SEQTRAK app (macOS) ignores background clicks, so the clicker needs **full screen control** of skai while it runs. Nobody else can use the Mac during a session.
- MIDI Monitor keeps running (hidden) while the clicker has control.
- MASTER tab, visible at start: Overview / Effect / Send / Comp & EQ. Overview shows Pattern 1–6, Volume 127, Send 1 Reverb, Send 2 Delay, Master Effect SPX ROOM (Dry/Wet D63>W), Effect 1 CONTROL FILTER (Cutoff 0), Effect 2 BEAT REPEAT (Combination 0), Comp, EQ, and a Guide panel (Sound, Mono/Poly, Pan, Volume).
