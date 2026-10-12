# Seqtrak Functionality Map

**Goal:** map every function of the Yamaha SEQTRAK to the MIDI/SysEx messages behind it, so the
Push (via the Pi bridge) can drive the Seqtrak exactly as its own hardware and app do.

**Started:** 2026-10-11. Companion to `sysex-protocol-reference.md` (the detailed address reference).

---

## 1. Key learning: two kinds of messages

Every Seqtrak message falls into one of two groups. They need different research approaches.

### A. Parameters — Yamaha documents these
Yamaha's **Data List** (`reference files/Yamaha/Seqtrak Data List V2/`, "MIDI Data Table",
pp. 117–161) contains the **official parameter map**: every sound, effect, mixer, project and
system setting, with address, size, range and default. Format:

```
F0 43 1n 7F 1C 0C [addr H] [addr M] [addr L] [data…] F7      (n = device number, usually 0)
```

| Block | Address | What |
|---|---|---|
| System | `00 00 xx` | Master volumes, MIDI settings, Wi-Fi, USB, click, sync, pad velocity… |
| Project Common | `30 40 xx` | Project name, tempo, swing, pattern master step, scale, key, solo, sampler mute |
| | `30 41` / `30 42` | Send Reverb / Send Delay |
| | `30 43`–`30 46` | Master Effect 1–4 |
| | `30 47` | Master EQ |
| | `30 49`–`30 4B` | A/D (audio input) part insertion A/B, general |
| | `30 4C` | USB Audio Input |
| | `30 4D` | Scale definitions |
| Project Track | `30 5p xx` | Per-track volume, pan, octave, **pattern select**, pattern step counts, mute |
| | `30 6p` / `30 7p` | Chord notes of scale 1–4 / 5–8 |
| Sound Common | `31 0p` | Sound name |
| | `31 1p` | Sound general |
| | `31 2p` / `31 3p` | **Track Insertion effect A / B** |
| | `31 4p` | LFO |
| | `31 5p` | Arpeggiator |
| Sound element | `41 ep` | Oscillator / amplitude / pitch (e = element 0–7, p = part) |
| | `42 ep` | Filter / EQ / LFO per element |
| Sound DX | `48 09` / `49 o9` | DX common / operator o (0–3) |
| SAMPLER sample | `50 eA` | Per-pad sample settings (e = pad 0–6) |

`p` = part/track 0–A (0 KICK … 6 PERC2, 7 SYNTH1, 8 SYNTH2, 9 DX, A SAMPLER).

**Method for parameters:** look the address up in the Data List first; only capture to confirm
behavior (e.g. which knob moves which parameter).

### B. Everything else — undocumented, must be captured
Not in Yamaha's table, so only live captures reveal them:

| Range | What |
|---|---|
| `01 1x xx` | **UI state & hardware feedback**: play/record state, selected track, global variation, display mode, master-effect state, preset name |
| `70 xx` / `72 xx` / `74 xx` | Step sequencer note data (drum / sampler / synth+DX), including delete |
| CC on ch 1 | Knob echoes (master effects, etc.) — documented as CCs, but the SysEx they trigger is not |

**Method:** MIDI Monitor capture, one action at a time, with pauses (see §6).

---

## 2. Corrections to `sysex-protocol-reference.md`

Several entries there were educated guesses from captures. Yamaha's official table names them:

| Address | Reference currently says | Official name (Data List) |
|---|---|---|
| `30 40 79` | Loop Enable | **Pattern Select Mode** (0 = normal, 1 = advanced) |
| `30 40 7E` | Scale type list (Chromatic, Major, …) | **Scale slot 1–8**; the scales themselves are defined in `30 4D xx` (the named list may just be the default slots — verify) |
| `30 5x 16` | Track Filter/Cutoff (speculative) | **Pattern 1 step count** (`16`,`18`,`1A`,`1C`,`1E`,`20` = patterns 1–6, 2 bytes, 1–128) |
| `31 2x xx` | "2-byte sound params (possibly modulation)" | **Insertion Effect A** for track x (offset `00` = effect type MSB/LSB) |
| `31 3x xx` | "Envelope/filter params" | **Insertion Effect B** for track x |
| `41 [track*16] 0A` | Per-track effect sends (drums) | **Sound element** block: middle byte = element (high nibble) + part (low nibble). `41 00/10/20…70 0A` = KICK's elements 0–7, not 8 tracks |
| `41 xA xx` | Per-track effect params (synth/DX/sampler) | Sound element block for **part A = SAMPLER**, elements 0–7 |
| `50 0A…6A 66` | Arpeggiator/motion, unknown tracks | **SAMPLER pad 1–7 Start Point** (4 bytes). `50 eA 60` = Loop Length, `50 eA 6A` = End Point |

These also close three items in the reference's **"Remaining"** list:
- *Effect type selection addresses* → master FX `30 43–46 00`, send reverb `30 41 00`, send delay `30 42 00`, track insertion A/B `31 2p 00` / `31 3p 00` (all 2-byte type MSB/LSB, codes in the Effect Type List)
- *Sample start/end points* → `50 eA 66` / `50 eA 6A`
- *Arpeggiator addresses* → `31 5p xx` (not `50 xx xx`)

---

## 3. Findings from 2026-10-11 captures

### 3.1 Master volume (volume buttons)
```
01 10 2E 09        display → volume mode
00 00 00 [vv]      Speaker Master Volume (official, 0–127, default 64)
```
- `00 00 01` = **Headphone Master Volume** (0–127, default 32) — expect it with headphones plugged in.
- ❓ Only values 0–2 were seen. Capture *hold volume-up from silent to max* to learn the step size.

### 3.2 Master effect knobs
Each knob sends a **CC on channel 1** plus the SysEx parameter(s) it drives (one knob can act as a macro):

| Knob | CC | SysEx echoed | Official name |
|---|---|---|---|
| Master FX 1 | 102 | `30 43 15 00 vv` | Master Effect 1 · Parameter 10 |
| Master FX 2 | 105 | `30 44 05 00 vv` + `30 44 15 00 vv` | Master Effect 2 · Parameters 2, 10 |
| Master FX 3 | 106 | `30 45 05 00 vv` + `30 45 03 00 0/1` | Master Effect 3 · Parameters 2, 1 (on/off-like) |

→ The bridge only needs to send **CC 102–106 on ch 1**; the Seqtrak applies the mapping itself.
(Which parameter each knob drives depends on the loaded master effect type — re-check with other types.)

### 3.3 New UI/feedback addresses (undocumented)
| Address | Seen | Hypothesis |
|---|---|---|
| `01 10 2E` | `02`, `03` (new values; `01/09/14/17/1A` already known) | More display modes — likely master-effect screens |
| `01 10 1D` | `01` just before turning Master FX 1 | Master Effect 1 state (selected/on?) |
| `01 10 1E` | `00` | Master Effect 2 state? |
| `01 10 1F` | `01` just before turning Master FX 3 | Master Effect 3 state? |

### 3.4 Variations ✅ (confirmed)
Official name: **Pattern Select**, `30 5p 0F`, data `00–05` = patterns 1–6.

**Global change** (all tracks): the Seqtrak sends 11 per-track messages, then a summary:
```
30 50 0F vv … 30 5A 0F vv     (one per track)
01 10 2A vv                   (global variation indicator)
```
`01 10 2A` then repeats every ~40–80 ms for ~0.5 s (button held / display refresh; no new info).

**Per-track change:** only that track's message, no `01 10 2A`:
```
01 10 27 tt        track selected on the hardware
30 5t 0F vv        that track's pattern
```

**Track selection** on the hardware is broadcast as `01 10 27 tt` (`00`–`0A`).

### 3.5 Bridge status for variations
- **Sending:** ✅ correct. `select_track_variation()` / `select_all_variations()` send exactly what the hardware sends.
- **Listening:** ❌ `handle_seqtrak_sysex()` only handles play, record, sample record, preset name, tempo.
  It ignores `30 5p 0F`, `01 10 2A` and `01 10 27`, so changes made **on the Seqtrak** leave the
  Push's `track_variation` / selected track stale → next Push variation nudge jumps from the wrong value.
- **Dead code with a trap:** `select_variation()` writes `01 10 28` + `01 10 2C`. The hardware never
  sends those for variations, and `01 10 28` is also the **sampler element** address. It's unused —
  remove it before someone wires it up.

### 3.6 App-driven capture (Seqtrak app over USB, 2026-10-11 17:25–17:27)

**Important:** every line was `From SEQTRAK`. MIDI Monitor by default shows what the Seqtrak
**sends back**, not what the app sends **to** it. When the app changes something, the Seqtrak
applies it and **broadcasts the resulting parameters** — that's what we see. For most parameters
the echo is identical to the write (so we can replay it), but app **commands** (load project,
load preset, request dump) are invisible. To see app → Seqtrak traffic, enable MIDI Monitor's
**"Spy on output to destinations"** (needs its spy driver) and select the SEQTRAK destination.

**Track select = full state dump of that track.** Selecting a track makes the Seqtrak send the
track's whole state (all official names):

| Address | Official name |
|---|---|
| `30 5p 00 / 01 / 0F` | Volume / Pan / Pattern Select |
| `31 1p 19 / 1A` | Reverb Send / Delay ("Variation") Send |
| `31 1p 2C / 2D` | AEG Attack / Decay offset |
| `31 1p 46 / 48 / 4B / 4D` | 2-band EQ low freq / low gain / high freq / high gain |
| `31 1p 1F` | Portamento Time · `31 1p 22` Key Assign · `31 1p 23` Mono/Poly/Chord |
| `31 1p 00…05` | AEG release (synth) / DX carrier attack, decay, mod amount, ratio, feedback |
| `31 2p 00` + `31 2p 03…21` | Insertion A **type** (2 B) + its parameters |
| `31 3p 03 / 05` | Insertion B parameters |
| `31 2p 43` | `7F` (side-chain/off-style field, same position as master FX `43`) |
| `31 5p 00 / 08 / 14` | Arpeggiator (synth/DX tracks) — confirms arp lives in `31 5p` |
| `41 ep xx`, `42 ep xx` | Element params (drum elements / sampler pad) |
| `48 09 00` | DX common (seen `02` on DX track) |
| `01 1p 35` (110 B) | **Preset name — per track** (`01 17 35` = SYNTH1 "LO-FI SOUL 1 BASS 01"), not only `01 10 35` |
| `01 1p 53/54/55`, `01 1p 5C/5D/5E` | ❓ Undocumented per-track sound info. `53/54/55` = `09 00 02` (drum/synth), `08` for sampler; `5C/5D/5E` differ per preset → likely bank/program-style IDs of the loaded sound |
| `01 1p 30` / `01 17 30` | ❓ per-track UI value (always `00` so far) |

**Sampler pad state (confirms §2):** `50 0A 66` Start `00 00 00 00`, `50 0A 6A` End `00 01 26 5F`,
`50 0A 60` Loop Length `00 01 26 5F`, `50 0A 5F`, plus `01 10 28 00` (pad 1 selected).

**Project load/settings broadcasts:**
- Scale definitions `30 4D 00…76` (8 scales × 7 notes, MIDI note values) → scale slots are user-definable note sets.
- Key change `30 40 7F 49` (A) also re-sends **chord notes** `30 67 00…1B` for SYNTH1 (28 values) — the Seqtrak recomputes chords when the key changes.
- Swing `30 40 7C 01 00` (= 0), Key `30 40 7F 40`, Scale `30 40 7E 00`, Pattern Select Mode `30 40 79 00`.
- `01 10 16` (110 B, all zero) — 🟡 **Project name** (very likely). All zero because projects created on the device have no name; a name only exists once a project is created/saved from the app. Same 110-byte long-message shape as the preset name block. Official project name lives at `30 40 00…57` (88 chars, UTF-8, 7-bit encoded). Verify: name a project in the app, then load it and capture.
- Master FX types on load: `30 43 00 01 12`, `30 44 00 0C 28`, `30 45 00 0C 7C` (type MSB/LSB → Effect Type List), each with `30 4x 43 7F` (**Side Chain Part = Off**).
- `01 1n 50 / 51 / 52 / 59 / 5A / 5B` for n = 0,1,2 — ❓ undocumented, appears with master FX → likely per-master-effect UI/preset info.
- `30 40 66 7F` — Project Common Volume (official `66`).

**Settings (all official `00 00 xx`, confirmed by app changes):** Click switch/volume/type `25/27/26`;
pad velocity `20`; record quantize `1F`; project resume `1D/1E`; sound design mode `21`;
sampling count-in `1B`; sampling source `19` (`02` = USB Audio In); auto normalize `1C`;
A/D & USB-audio-in params `30 4B 06/16`, `30 4C 16`; pattern master step `30 40 7A 00 10` (16).

**Choke groups:** `30 53…56 08 00` = **Group Number** (official `30 5p 08`, 0 = off) for HAT1, HAT2,
PERC1, PERC2 → closes gap-analysis item 1.3 (Choke Groups).

**Mixer reset:** `30 5p 29 00` (Mute off) + `30 5p 00 64` (Volume 100) for all 11 tracks, then
`30 40 68 00` (Solo off) — the app's "reset mixer" is just parameter writes.

**Transport from app:** Seqtrak echoes MIDI realtime **Start / Stop**.

**Bulk dumps:** after `01 17 33 20 56` and `01 10 00 00`, the Seqtrak sent Yamaha **bulk dump**
messages (`F0 43 00 7F 1C [size] 0C …`, 245 B and 701 B) containing sound names ("LO-FI SOUL 1
BASS 01", "Lo Boy", "Clean", "Sub"). Format = Data List "Bulk Dump Block" (p. 120). Likely the
app reading sound/preset data. ❓ The request that triggered it isn't visible without spy mode.

### 3.7 Spy-mode capture (app ↔ Seqtrak, 2026-10-11 18:07)

Spy mode works (MIDI Monitor 1.5.4 on macOS 26). Both directions are now visible.

**The app reads state with Parameter Requests — and the Seqtrak answers every one.**
```
To SEQTRAK:    F0 43 30 7F 1C 0C [addr] F7          (3n = Parameter Request)
From SEQTRAK:  F0 43 10 7F 1C 0C [addr] [data] F7   (1n = Parameter Change reply)
```
On each track select the app does **not** rely on a push from the device; it **requests** ~30
addresses one by one (the "state dump" seen in §3.6 was these replies). This works for official
addresses **and** undocumented `01 1x xx` ones.

- ✅ **Patch name fix found:** the app requests **`01 1p 35`** for the selected track and gets the
  110-byte name back (`01 10 35` → "TS_RNB_kick_rnb", `01 17 35` → "Brain Bass"). The bridge asks
  for `01 10 35` regardless of track → it must request `01 1p 35` with p = selected track and
  accept the reply on that address.
- Same mechanism can read anything at startup (tempo, volumes, variations, mute, names…) → the
  Push can mirror full state without waiting for the user to change something.

**Step data readback:** at startup the app requests `70 40 ss`, `70 60 ss`, `70 50 ss` for
ss = `2C…7F`; each reply is just the address with **no data** (likely = empty/no event).
❓ Meaning of `40/50/60` (track group? note/velocity/gate layers?) — needs a capture with
steps present.

**Drum steps confirmed (2026-10-11, KICK steps 1/5/9/13 placed on the device, then 5 removed):**
- **Live push from the device:** placing a step sends `70 [t-1] 00 [step] [note] [vel] [gate] [prob]`
  (e.g. `70 00 00 08 3C 64 00 78`); removing one sends `70 [0x20+t-1] 00 [step]`. Same format the
  bridge already sends, so the device announces its own edits unprompted.
- **Readback:** `70 [0x40+t-1] [step]` (t = 1–7) answers with 6 bytes when the step is set
  (`3C 64 00 3C 00 78`, likely note/vel/gate-hi/gate-lo/?/prob) and no data when empty.
  `70 [0x60+t-1] [step]` answered `00` on set steps (❓ flag/micro-timing); `70 5x` stayed empty.
- Only `70 4x/5x/6x` (x = 0–6) answer requests. `72`/`74` (sampler, synth/DX) answered nothing
  → their readback format is still unknown (needs a spy capture with steps present).
- Removing a step also sent `01 10 2D` 00→01 and `01 1p 39` for all tracks (❓ UI/edit state).

**Writes use plain Parameter Change** (`F0 43 10 …`), and the app sends **each value twice**
(~2–25 ms apart). Seen:
| Address | Values | Meaning |
|---|---|---|
| `31 10 1C` | `28…58` (center `40`) | **KICK pitch** — range matches CC 25 Drum Pitch (40–88). Not in Yamaha's table (reserved slot) → SysEx twin of CC 25 |
| `00 00 19` | `01` → `00` → `02` | Sampling Source: Mic/Line In → Resampling → USB Audio In (official) |
| `00 00 1C` | `00` → `01` | Auto Normalize off/on (official) |

**Other reads seen:** `01 10 3C` (requested, no reply captured ❓), `30 40 79` = `01`
(Pattern Select Mode = advanced on this unit), `30 50 0F` = `05` (KICK on pattern 6).

**Next:** systematic, screen-by-screen app captures (planned by the user), ideally saved from
MIDI Monitor and decoded automatically against the Data List.

---

## 4. Coverage map

Status key: ✅ done · 🟡 partial / needs verification · ❌ not yet · — not applicable
"Doc" = in Yamaha's Data List · "Cap" = confirmed by live capture · "Send"/"Listen" = bridge

### Transport & timing
| Function | Message | Doc | Cap | Send | Listen |
|---|---|---|---|---|---|
| Play / stop / continue | MIDI realtime FA/FC/FB | ✅ | ✅ | ✅ | — |
| Play state feedback | `01 10 20` | ❌ | ✅ | — | ✅ |
| Record state feedback | `01 10 21` | ❌ | ✅ | — | ✅ |
| Sample record state | `01 10 22` | ❌ | ✅ | — | ✅ |
| Tempo | `30 40 76` (2 B) | ✅ | ✅ | ✅ | ✅ |
| Swing | `30 40 7C` (2 B, −58…+58) | ✅ | ✅ | ✅ | ❌ |
| Pattern master step | `30 40 7A` (2 B) | ✅ | ✅ | 🟡 | ❌ |
| Tap tempo | ? | ❌ | 🟡 | 🟡 | — |
| Click on/type/volume | `00 00 25–27` | ✅ | ✅ | ❌ | ❌ |
| MIDI sync / clock out | `00 00 2A`, `00 00 2D` | ✅ | ❌ | ❌ | ❌ |

### Tracks & mixer
| Function | Message | Doc | Cap | Send | Listen |
|---|---|---|---|---|---|
| Track select | `01 10 27` | ❌ | ✅ | ✅ | ❌ |
| Track volume | `30 5p 00` / CC | ✅ | ✅ | ✅ | ❌ |
| Track pan | `30 5p 01` / CC | ✅ | ✅ | ✅ | ❌ |
| Track octave | `30 5p 0C` (3E–42) | ✅ | ✅ | ❌ | ❌ |
| Mute | CC 23 · `30 5p 29` (00/7D) | ✅ | ✅ | ✅ | ❌ |
| Choke group | `30 5p 08` (0 = off) | ✅ | ✅ | ❌ | ❌ |
| Solo | CC 24 · `30 40 68` (0 off, 1–11) | ✅ | ✅ | ✅ | ❌ |
| Speaker master volume | `00 00 00` | ✅ | ✅ | ✅ | ❌ |
| Headphone master volume | `00 00 01` | ✅ | ❌ | ❌ | ❌ |

### Patterns / variations
| Function | Message | Doc | Cap | Send | Listen |
|---|---|---|---|---|---|
| Per-track pattern select | `30 5p 0F` | ✅ | ✅ | ✅ | ❌ |
| Global variation | 11× `30 5p 0F` + `01 10 2A` | 🟡 | ✅ | ✅ | ❌ |
| 3 vs 6 variation mode | `01 10 18` (bridge uses) | ❌ | 🟡 | ✅ | ❌ |
| Pattern 1–6 step counts | `30 5p 16…20` | ✅ | 🟡 | 🟡 | ❌ |
| Pattern select mode | `30 40 79` | ✅ | 🟡 | ❌ | ❌ |
| Pattern copy / paste / clear | ? | ❌ | ❌ | ❌ | ❌ |
| Pattern state broadcast | `01 1p 39` | ❌ | 🟡 | — | ❌ |

### Step sequencer
| Function | Message | Doc | Cap | Send | Listen |
|---|---|---|---|---|---|
| Drum step add / delete | `70 0t 00 ss …` / `70 2t 00 ss` | ❌ | ✅ | ✅ | ❌ |
| Sampler step add / delete | `72 30 …` / `72 50 …` | ❌ | ✅ | ✅ | ❌ |
| Synth/DX step add | `74 …` | ❌ | ✅ | 🟡 | ❌ |
| Step velocity / length / micro-timing edit | ? | ❌ | ❌ | ❌ | ❌ |
| Motion sequence (knob recording) | ? | ❌ | ❌ | ❌ | ❌ |

### Sound
| Function | Message | Doc | Cap | Send | Listen |
|---|---|---|---|---|---|
| Preset select | Bank MSB/LSB + Program Change | ✅ | ✅ | ✅ | ✅ |
| Preset name | `01 1p 35` (long, per track, 7-bit packed) — readable on demand via Parameter Request `F0 43 30 … 01 1p 35` | ❌ | ✅ | — | ✅ (fixed 2026-10-11, verified on hardware) |
| Sound design knobs | CCs (per track type) | ✅ | ✅ | ✅ | ❌ |
| Deep sound params | `31 1p`, `41 ep`, `42 ep`, `48/49` | ✅ | 🟡 | ❌ | ❌ |
| LFO | `31 4p` | ✅ | ❌ | ❌ | ❌ |
| Arpeggiator | `31 5p` + CCs | ✅ | 🟡 | 🟡 | ❌ |
| Chord notes of scale | `30 6p` / `30 7p` | ✅ | ❌ | ❌ | ❌ |
| Sampler pad select | `01 10 28` | ❌ | ✅ | ✅ | ❌ |
| Sampler start/end/loop | `50 eA 66/6A/60` | ✅ | ✅ | ❌ | ❌ |
| Sampler element mute | `30 40 63` | ✅ | ❌ | ❌ | ❌ |

### Effects
| Function | Message | Doc | Cap | Send | Listen |
|---|---|---|---|---|---|
| Master FX knobs | CC 102–106 (constants exist in `protocol.py`, not wired in app) | ✅ | ✅ | ❌ | ❌ |
| Master FX type / params / on-off | `30 43–46 00`, `…03–31`, `…47` | ✅ | 🟡 | ❌ | ❌ |
| Master FX state (UI) | `01 10 1D–1F`? | ❌ | 🟡 | — | ❌ |
| Master EQ | `30 47` | ✅ | ❌ | ❌ | ❌ |
| Send reverb / delay type & params | `30 41`, `30 42` | ✅ | 🟡 | 🟡 | ❌ |
| Track insertion effects A/B | `31 2p`, `31 3p` | ✅ | 🟡 | ❌ | ❌ |
| Track reverb / delay sends | CCs | ✅ | ✅ | ✅ | ❌ |

### Scale & key
| Function | Message | Doc | Cap | Send | Listen |
|---|---|---|---|---|---|
| Scale slot | `30 40 7E` (0–7) | ✅ | ✅ | ❌ | ❌ |
| Key | `30 40 7F` (40–4B) | ✅ | ✅ | ❌ | ❌ |
| Scale definitions | `30 4D` (8 × 7 notes) | ✅ | ✅ | ❌ | ❌ |
| Chord notes (recomputed on key change) | `30 6p` / `30 7p` | ✅ | ✅ | ❌ | ❌ |

### System / settings (all documented in `00 00 xx`)
Local switch, MIDI in/out per port (legacy / USB / Bluetooth), MIDI thru, transmit filters,
USB/analog output gain, **Wireless LAN on/off** (`00 00 16`), USB role, sampling source / count-in /
normalize, project resume, record quantize, pad velocity, sound design mode, pattern select
sensitivity. → Covers the "Advanced Settings" gap in `IMPLEMENTATION-GAP-ANALYSIS.md` §5.1 with
no captures needed.

### UI / display
| Function | Message | Doc | Cap | Send | Listen |
|---|---|---|---|---|---|
| Display mode | `01 10 2E` (01,02,03,09,14,17,1A) | ❌ | ✅ | — | ❌ |
| Options page | `01 17 30` | ❌ | 🟡 | — | ❌ |
| Unknown toggles | `01 10 30`, `01 10 2D` | ❌ | 🟡 | — | ❌ |
| Project name (feedback) | `01 10 16` (110 B) · official `30 40 00–57` | 🟡 | 🟡 | — | ❌ |
| Per-track sound info | `01 1p 53–55`, `01 1p 5C–5E` | ❌ | 🟡 | — | ❌ |
| Per-master-FX info | `01 1n 50–5B` (n = 0–2) | ❌ | 🟡 | — | ❌ |

---

## 5. Next actions

**Bridge (small, high value):**
1. Listen for `30 5p 0F`, `01 10 2A`, `01 10 27` → keep Push variation/track state in sync.
2. Remove `select_variation()` (wrong addresses; collides with sampler element).
3. Optionally listen for mute/solo/volume feedback so Push LEDs/LCD follow Seqtrak-side changes.
4. ✅ DONE 2026-10-11 (verified on pibridge). Preset name: **request** `01 1p 35` for the selected track (Parameter Request, `F0 43 30 7F 1C 0C 01 1p 35 F7`) and accept the reply on `01 1p 35` — fixes "name only appears after changing patch".
4b. On startup, request tempo, per-track volume/variation/mute and names the same way the app does (§3.7).
5. Use the **track-select state dump** (§3.6) to populate Push device pages after a track change.

**Docs:**
6. Apply §2 corrections in `sysex-protocol-reference.md`. ✅ done 2026-10-11

**Captures still needed** (one action per capture, see §6):
- [ ] Volume: hold up from silent → max (step size); same with headphones in (`00 00 01`)
- [ ] Master FX: switch effect **type** on each slot; toggle each on/off; turn CC 103/104
- [ ] What `01 10 1D/1E/1F` and `01 10 2E 02/03` mean (press master-effect buttons one at a time)
- [ ] Pattern copy / paste / clear
- [ ] Step edits: velocity, length, micro-timing; motion recording
- [ ] Tap tempo (what is sent, if anything)
- [ ] Scale/key change from hardware; does `30 40 7E` value map to the named list?
- [ ] Sampler: change start/end on hardware → confirm `50 eA 66/6A`
- [x] Settings → `00 00 xx` echoes confirmed via the app (click, pad velocity, quantize, sampling, resume)
- [ ] **Spy mode** (MIDI Monitor → "Spy on output to destinations" → SEQTRAK): load a preset from the app
- [ ] **Spy mode**: load a project from the app (find the load command + what triggers the bulk dumps)
- [ ] Name a project in the app → confirm `01 10 16` / `30 40 00…` carry the name
- [ ] Pattern 1–6 step counts: change pattern length on the hardware → confirm `30 5p 16…20`

---

## 6. Capture protocol

1. Open MIDI Monitor, filter to the SEQTRAK source, clear the log. When driving the Seqtrak from
   the **app**, also enable **"Spy on output to destinations"** for SEQTRAK — otherwise you only see
   the Seqtrak's replies, not the app's commands.
2. Do **one kind of action** per capture. Wait ~3 s between presses so each event stands alone by timestamp.
3. Do it **stopped and playing** if behavior might differ.
4. Note what you physically did, in order, next to the paste.
5. Decode: look the address up in the Data List first (§1A); if it's `01 1x xx` or `7x xx`, it's new — add it here.
6. Test the reverse direction: send the same message from the Pi/Mac and confirm the Seqtrak reacts.
