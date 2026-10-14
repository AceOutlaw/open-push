# SEQTRAK app click-through, Phase 0: what the app reads and writes

**Captured 2026-10-14** (`experiments/app-clickthrough/`, blocks `P0-PROBE` and `P0-NAV`). The SEQTRAK macOS app
(firmware shown: 1.21.3) was connected to the Seqtrak by **USB**. Every byte the app sent and every reply was
recorded with MIDI Monitor's spy driver: OUT = app → Seqtrak, IN = Seqtrak → app.
P0-NAV visited every app screen and track **without changing values**, so nearly everything the app sent is a
**Parameter Request** (read), plus a few writes listed below.

- **Full table:** `app-read-map-P0.tsv` (1,138 rows: time, address, the Seqtrak's reply, official name from
  Yamaha's Data List, range, description, default, and which app pages were open in that batch).
- **Names:** taken from the Data List V2 Parameter Change Table (`reference files/Yamaha/Seqtrak Data List V2/md/34–36`)
  by a parser. 578 of 1,138 addresses got a name. The PDF-extracted tables are messy, so a few names may sit in the
  wrong column; check the PDF before building on a single row.

Status: ✅ verified · 🟡 likely, evidence given · ❓ unknown.

## 1. Writes (what changes something)

| Message | Seen when | Meaning |
|---|---|---|
| `30 40 66 [v]` | P0-PROBE, Volume slider 127 → 98 → 127 | ✅ **MASTER > Overview Volume** = Project Common **Volume** (Data List `30 40 66`, 0–127, default 127). Values matched the app's display (`66`=102 → `62`=98 → `7F`=127). This is **not** the speaker volume `00 00 00` that the device's volume buttons change. |
| `30 47 00…12` (all 5 bands' gain / freq / Q) | opening MASTER > COMP & EQ | 🟡 The app re-writes the current master EQ when the page opens (values equal what it had just read). No audible change expected. |
| `30 42 44 60` | SEND page | 🟡 Re-writes the current Delay return (same value as read). |
| `30 40 7A 00 10` | PATTERN page | 🟡 Re-writes Pattern Master Step (16). |
| `00 60 06 55 53` | HOME > SETTINGS > HARDWARE | 🟡 Re-writes the Wi-Fi country ("US", ASCII) shown on that page. |
| `01 1p 50/51/52`, `01 1p 56/57/58` | switching app pages | 🟡 App UI state (which page/sub-tab is open); the Seqtrak echoes them. Not settings. |
| `87–8A 00 00` ×14 each | opening PERFORM > PAD/KEY | Note Off on channels 8–11 (the melodic tracks) — the app's all-notes-off. |

⚠️ So opening some app pages writes values even when the user changes nothing. A Push bridge listening to the
Seqtrak will see these as changes.

## 2. New reads worth building on

| Request | Reply example | What it is |
|---|---|---|
| `01 1p 35` | `00 54 53 5F 52 4E 42 5F 00 6B 69 63 6B 5F 72 6E 00 62 …` | 🟡 **Current sound name of track p**, Yamaha 7-bit packed text (each group = one high-bit byte + 7 chars). KICK = "TS_RNB_kick_rnb", SYNTH 1 = "LO-FI SOUL 1 BASS 01", SYNTH 2 = "Round Saw Phase". The Push could show real sound names with this. |
| `70 [50+t] [step]` | (no reply on any step so far) | ❓ A second per-step table for drum track t (the app reads it for all 128 steps next to `70 4t`). Empty in this project. Candidate: Parameter Locks (§9.2). |
| `70 [60+t] [step]` | `00` on every step that has a note, no reply on empty steps | ❓ A third per-step table, 1 byte per set step. Candidate: probability (§6.6, 8 levels) — the project's steps are all at the default. |
| `70 [40+t] [step]` | `3C 64 02 3C 01 06` (KICK step 12) | ✅ Known drum step read (`STEP-SEQUENCER.md`); 3rd byte `02` = the substep set on that step earlier. |
| `01 00 00` | `01 02 01 03` | 🟡 Firmware version — the app showed 1.21.3. |
| `00 60 06` | `55 53` ("US") | 🟡 Wi-Fi country. `00 60 00/01`, `00 61 02` are nearby HARDWARE settings (❓ which). |
| `71 40 [00–0F]` | 26 bytes, e.g. `00 00 01 01 … 01 00 …` | ❓ Read on the PERFORM pages (song/scene area?). Only 00–02 answered. |
| `01 1p 30`, `01 1p 3C`, `01 1p 53–55`, `01 1p 5C–5E` | small values | ❓ Read each time a track is selected; per-track UI/edit state. |

### Sound list = paged bulk dump (SOUND browser)
Opening a track's SOUND browser made the app send **Bulk Requests** and the Seqtrak answer in pages:
- `F0 43 20 7F 1C 0C 0C 10 00 F7` → 2 pages; `F0 43 20 7F 1C 0C 0C 00 0F F7` → 8 pages;
  later `F0 43 20 7F 1C 0C 0B 00 00 F7` → 1 page (PROJECT/SOUND MANAGER).
- Each page: `F0 43 00 7F 1C [size hi lo] 0C [addr 3 bytes] [total pages hi lo] [page hi lo] … [checksum] F7`
  (up to ~3 KB). The app acknowledges each page with
  `F0 43 00 7F 1C 00 0C 0C 01 22 00 00 [addr 3 bytes] 00 [page] 00 00 [checksum] F7` before the next one comes.
- The pages hold sound entries with readable names and categories ("Consideration-Kick_1" / "Kick",
  "Lo-Fi Closed Hat 9", "AMBIENT SELECTION 1 SNARE 01" / "Acoustic", …). 🟡 This is how the app lists sounds by name.
  ❓ Which list each address is (`0C 10 00` user sounds? `0C 00 0F` presets for this track?) and the entry layout.
- This is the route to browsing sounds by name from the Push (KM-107).

## 3. Readback values vs. what the app showed (spot checks)
- ✅ Tempo `30 40 76` = `00 64` = 100 BPM (app: 100).
- ✅ Pattern 1 step count `30 50 16` = `00 20` = 32 (app: KICK STEPS 32).
- ✅ Track Volume `30 5p 00` = `64`, Pan `30 5p 01` = `40` (centre).
- ✅ Key `30 40 7F` = `40` = C: the Data List range is `40`–`4B` (`midi-data-table.md` said 0–11; corrected). Phase 1 confirmed C# = `41` … B = `4B`.
- ✅ Swing `30 40 7C` = `01 2C` = 128 + 44 ticks; the Data List default `01 00` is no swing. App % = (120 + offset)/240 → 68 %. Confirmed in Phase 1 (`APP-CLICKTHROUGH-P1.md`).

## 4. Blocks the app reads (by page)
Official block names (Data List "Parameter Base Address"). Counts = addresses read in P0-NAV.

| Block | Name | Read | Pages |
|---|---|---|---|
| `00 00` | System | 28 | SETTINGS > MIDI, HOME > SETTINGS > HARDWARE |
| `30 40` | Project Common General | 8 | Overview, SETTINGS > PROJECT |
| `30 41` / `30 42` | Send Reverb / Send Delay | 12 / 12 | MASTER > SEND |
| `30 43–46` | Master Effect 1–4 (❓ which app slot is which: COMP, MASTER EFFECT, EFFECT 1, EFFECT 2) | 45 | MASTER > EFFECT, COMP |
| `30 47` | Master EQ | 15 | MASTER > COMP & EQ |
| `30 4B` / `30 4C` | A/D Part General / USB Audio Input | 3 | SAMPLER record settings |
| `30 4D` | Scale (8 scales × pad notes) | 56 | SETTINGS > SCALES |
| `30 5p` | Project Track General (volume, pan, pattern, step counts) | 62 | all tracks |
| `30 67` | Chord notes (SYNTH 1) | 28 | CHORD |
| `31 0p` / `31 1p` | Sound Name / Sound Common General | 4 / 85 | every track |
| `31 2p` / `31 3p` | Insertion A / B (track effects) | 94 / 22 | track EFFECT |
| `31 4p` / `31 5p` | LFO / Arpeggiator | 7 / 12 | LFO, ARP |
| `41 ep` / `42 ep` | Sound element (drum alternate group = choke) / filter | 23 / 2 | DRUM CHOKE, SAMPLER |
| `48 09` / `49 o9` | DX common / DX operators 1–4 | 13 / 100 | DX SOUND DESIGN |
| `50 eA` | SAMPLER sample | 4 | SAMPLER |
| `70 4t/5t/6t` | Drum step tables (KICK only in this pass) | 384 | DRUMS > PATTERN |
| `75 00`, `75 30` | Melodic / sampler note list | 2 | PATTERN |

## 5. Next
Phase 1 (one control per block) will show the write address for each control, so each `❓` above gets a
capture of the app changing it. Verify each command by readback before marking it ✅.
