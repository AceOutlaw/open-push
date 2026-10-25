# How Other Instruments Are Built: Firmware, Updates and Architecture

**Purpose**: Notes from studying how other music hardware is put together, so the bridge and a future
standalone instrument can borrow the good ideas. Learning from the implementation, not copying it:
nothing here is vendor code, and none of it goes into this repo.

**Status**: Research notes, 2026-10-23/24. Downloaded files and cloned repos are local-only in
`reference files/` (gitignored); paths below are relative to that folder.

---

## 1. Three ways to ship a firmware update

| | Chase Bliss | teenage engineering | Ableton Move |
|---|---|---|---|
| Updater | Web page (WebUSB) | Web page (Web MIDI) | Move Manager in the browser, or on the device over Wi-Fi |
| File | Raw `.bin` / `.hex`: the exact bytes that go into flash | `.tfw`: 64-byte header + sealed payload | Signed SWUpdate package; the whole OS is also a public recovery image |
| Transport | Standard USB DFU (the chip's built-in ROM bootloader) | TE's own SysEx update protocol over USB MIDI | Linux on the device |
| Who checks the file | Nobody: the ROM bootloader writes whatever it gets | TE's own bootloader on the device | SWUpdate on the device (signature check) |
| Can you read the firmware? | Yes, it's plaintext | No, the payload is compressed or encrypted | Yes, the recovery image is a normal Linux disk image |

**The rule behind all three**: anything a web page uses is downloaded to your browser, so the update
file is always obtainable. What differs is whether the file is useful without the device. Chase Bliss
sends plaintext; TE keeps the secret in the bootloader, so the file is a sealed envelope; Ableton signs
updates (only Ableton can make one the device accepts) and doesn't try to hide the code.

**Why they differ**: the protection matches what's worth stealing.
- **TE**: the firmware is what makes premium hardware on commodity parts worth its price. If it could
  be read or reflashed, a cloner could build cheaper hardware and run the real firmware.
- **Ableton**: the Move leads people into Live, sets and sounds. Copied Move software would be compiled
  programs you can't legally sell, needing custom XMOS hardware. The thing to protect is control of
  updates, and signing does that.
- **Chase Bliss**: small boutique brand with an open, trusted reputation; plaintext is a choice.

### teenage engineering `.tfw` header (from the updater's own parser)

```
0x00  BA BE CA FE      signature; the updater rejects anything else
0x04  1 byte           firmware type (regular firmware vs. content)
0x05  2 bytes          checksum
0x07  8 bytes          version: four 16-bit numbers → major.minor.patch+build
0x0F  …                SKU (which product); must match the connected unit
 …    zero padding to 64 bytes
0x40  BE EF CA FE …    payload (~8 bits/byte entropy: compressed or encrypted)
```

The index of current firmware is `https://teenage.engineering/_software/releases.json`.

## 2. CHOMPI firmware (open source, MIT, Daisy Seed / STM32H750)

Source: `jasmine-granular-pedal/analysis/CHOMPI-main` (released by CHOMPI Club, discontinued product).

**Work runs at fixed priorities, and nothing waits.**

| Tier | Runs | Does | Never does |
|---|---|---|---|
| Audio callback | every audio block (interrupt) | scans controls, makes UI events, starts/stops one queued note, renders audio | touches the SD card |
| Low-priority timer | 1 kHz | one SD-card file request per tick, preset save in 1 KB chunks | blocks |
| Main loop | leftover time | UI redraw, MIDI input, battery/USB | anything time-critical |

Patterns worth borrowing:
- **Tiers talk only through queues** (`KeyRequest`, `FileRequest`, `CopyRequest` FIFOs).
- **Long jobs are state machines**: one bounded step per tick (preset save: open temp → write chunk → … →
  rename).
- **Slow work waits for quiet**: presets are only written while no voices are playing.
- **Atomic save**: write a temp file, then rename it over the real one, so a power cut leaves the old file.
- **Failures go to a debug queue** instead of blocking the queue or being retried forever.
- **UI is a stack of pages** (normal, menu, test, boot, no-SD): whichever page is on top gets the events.
- **Drawing on a clock**: LEDs flush every 16 ms; events only change state.
- **MIDI CC as a button with a dead zone**: above 84 = on, below 42 = off.

Bootloader: modified Electrosmith Daisy bootloader. It loads `.bin` from the SD card, sanity-checks the
stack pointer and entry point, byte-compares with flash to skip identical rewrites, then writes QSPI.
No signature.

## 3. Ableton Move (CM4 + Linux)

Sources: the official recovery image (`Ableton/Move/recovery-image/`, public at
`https://www.ableton.com/download/hardware/latest/move/recovery/`, version 2.1.1) and community
projects (`Ableton/Move/`, especially Schwung, formerly "Move Everything", and `schwung-spi`).

**Hardware**: a Raspberry Pi Compute Module 4 (the same chip as a Pi 4) plus an **XMOS** processor that
handles audio, pads, buttons, LEDs and the display. The CM4 and XMOS exchange one shared 4 KB page over
SPI once per audio block (128 frames): MIDI out, display data, audio out; MIDI in, audio in. Separate
firmware files suggest further small controllers (`.mhc`, `.pmc`: probably hardware and power, unverified).

**The control surface speaks MIDI internally**: pads are notes 68–99 (4×8), step buttons notes 16–31,
knob touch notes 0–7, LEDs set by MIDI/SysEx. Same design idea as the Push 1 (pads notes 36–99).

**The OS** (`AbletonOS abletonos-aarch64-rpi4-v4.1`): a Yocto-style build with sysvinit.
- **Disk layout**: `boot` (FAT) + `primary` + `secondary` (identical 2 GB system copies: **A/B updates**)
  + `data`. An update goes into the copy that isn't running, so a failed update can't brick it.
- **Read-only system** (`read-only-rootfs-hook.sh`); everything writable lives on `data`. Power cuts
  can't corrupt the OS.
- **Many small programs, not one**: `Move` (the app), launcher, web service, control-mode handler,
  firmware updater, SSH key installer, crash reporting… connected over **D-Bus**.
- **Real-time tuning in the startup script**: SPI threads get real-time priority (`chrt`), interrupts
  and work queues are pinned to cores 0–2, and audio-related interrupts get core 3 to themselves.
- **USB-C shows up as a network device** (USB gadget mode); that's how `move.local` works without Wi-Fi.
- **SSH**: key-only, root, offered in the developer settings. Unsupported but deliberately not blocked.
- The SPI driver (`ablspi`) is GPL, so its source was released on request; the community's SPI
  protocol knowledge comes from that.

### How the clip launcher works

Sources: the demo sets in the recovery image's `data` partition (`CoreLibrary/DemoSongs/`), and
Schwung's `docs/MOVE_MODEL.md`, whose author read Move's live model out of the running app's memory
(firmware 2.1.0). Ableton documents none of this.

**The set file** (`Song.abl`) is plain JSON (schema `tech.ableton.com/schema/song/1.8.3`):

```
Song   tempo, timeSignature, rootNote, scale
├── tracks[4]        kind "midi" | "audio", name, color, mixer {volume, pan, speakerOn, solo}
│    └── clipSlots[8]               one per pad in the track's row
│         └── clip (or empty)
│              ├── region {start, end, loop {start, end, isEnabled}}        in BEATS
│              ├── notes [{noteNumber, startTime, duration, velocity, offVelocity}]   MIDI clip
│              └── sampleUri + warping {markers [{seconds, beats}]}        audio clip
├── scenes[8]        name + colour only: a scene is just a column
├── masterTrack      devices (effects)
└── grooves
```

Everything is in **beats**. Notes are absolute in clip time, so a clip whose loop starts later can
still hold notes before it. Audio clips pair seconds with beats in warp markers so the sample stretches
to the tempo.

**In memory it's Live's own data model** (`shared/live-model/FlipModelLib`, built on Ohm Force's
`flip` framework): `live.Song` → `live.Track` → `live.Clips` (8 `ClipSlot`s + one `PlayingState`) →
`live.Clip` (`ClipRegion`, notes). Each track has a **single** `PlayingState` (`mPlayingClipSlot`,
`mSessionClipStartTime`), which is why a track can play only one clip: launching moves that pointer.

**A launch, step by step:**
1. The pad press reaches the CM4 as a MIDI note from the XMOS. In Session Mode the rows descend by
   eight: 92–99 = Track 1, 84–91 Track 2, 76–83 Track 3, 68–75 Track 4.
2. The UI maps the note to (track, slot) and asks the engine to launch it.
3. The engine **queues** the launch. The queue is engine state: it isn't in the set file or the model.
4. The transport keeps a clock in **beats since Play** (reset to 0 on every Play). At the next launch
   boundary the engine sets `mPlayingClipSlot` and `mSessionClipStartTime` to that exact beat.
   Measured: pressed at 4.76 → start 8.0; pressed at 13.5 → start 16.0. The switch happens at the
   boundary, not at the press; the pulsing-green LED is the time in between.

**Playback**: every 128-frame audio block (~2.9 ms) the engine computes each track's position as
`region.start + (song_beats − start_beat)`, wrapped into `[loop.start, loop.end)`, then plays the
notes that fall in the block (or reads the warped sample there). One shared clock plus a start beat
per track keeps every clip on the bar however late it was launched. Shift+Play just resets the start
beats.

**Around it:**
- LEDs (playing, queued, selected) are drawn from the same model and sent back to the XMOS as MIDI.
- A scene launch is several slot launches on the same boundary (a finger slid down a column).
- `Song.abl` is saved about 10 s behind the live model, so the audio thread never waits on the disk.
- `flip` records every change as a transaction, which is where undo comes from.

**Document vs. engine**, the design split worth copying:

| Lives in | What | Why |
|---|---|---|
| Document (flip) | clips, notes, loop regions, playing clip, start beat | saved, undoable, observable by the UI |
| Engine (plain C++) | the launch queue, sample-exact timing | temporary, real-time, owned by the audio thread |

Schwung could read the document because `flip` keeps a runtime registry of class and member names
(it needs them to save, undo and notify). Plain C++ engine objects keep no names after compiling, so
seeing the queue would mean disassembling the 30 MB `Move` binary. Its behaviour is observable from
outside anyway.

**For a launcher of our own**, five pieces: one clock in beats since Play; clips stored in beats with
a loop region; per track, one pointer to the playing clip plus its start beat; launches queued and
committed at the next boundary; the audio thread computing `clock − start`, wrapped into the loop.
The clock, queue and playing state live in the engine; the Push side only requests launches and
reads state for its LEDs.

**Running it elsewhere**: the image targets the Pi 4 chip family. `ableton-move-lab` runs the Move
software in Docker or on a plain Pi 4 by faking the XMOS with an `LD_PRELOAD` shim. Personal research
only: it's Ableton's proprietary software.

## 4. How devices let other software in: offline files vs. a live protocol

A sealed firmware doesn't mean a closed device. What matters is which **door** the device offers
other software, and there are two kinds:

| | Offline: file exchange | Online: live protocol |
|---|---|---|
| Examples | OP-1 field, OP-XY (USB disk/MTP mode); Seqtrak `.Y3P` project export | EP series (SysEx file protocol); Seqtrak parameter/step/note messages; Push |
| How it works | The device stops being an instrument, hands its storage to the computer, then reloads what it finds | The device keeps playing; other software sends **requests** and the firmware carries them out |
| What a tool can do | Build files in the exact format the device expects (e.g. field-arrange for OP-1 Field tapes) | Work alongside the device in real time (companion apps like the third-party EP-133 librarians) |

**Why it's one or the other**: it comes down to who may write the device's storage. In disk/MTP mode the
computer writes directly, so the instrument must step aside (two writers would corrupt the file
system). With a request protocol the device stays the **only writer**: it queues requests and runs them
between its own work, so it can keep playing. Same idea as CHOMPI's queues: one owner of the data,
everyone else asks.

**teenage engineering in practice** (from TE's own EP Sample Tool web app,
`teenage.engineering/apps/ep-sample-tool`, read 2026-10-24):
- The tool's JavaScript names a full **file system over SysEx**: `TE_SYSEX_FILE_INIT`, `_LIST`, `_GET`,
  `_INFO`, `_METADATA`, `_DELETE`, `_EVENT`, capabilities `READ` / `WRITE` / `MOVE` / `DELETE` /
  `PLAYBACK`, file types `DIR` / `FILE`. List folders, read and write samples and projects, read metadata,
  delete, move, even audition a sample.
- It knows only three products: `TE032AS001` EP-133 K.O. II, `TE032AS005` EP-1320, `TE032AS006` EP-40.
  No OP devices.
- The OP-1 field and OP-XY are samplers too, but their file door is **disk/MTP mode** (the OP-1 field
  release notes mention an MTP fix), and live control stops at MIDI notes and CC. The SysEx channel
  exists on them, since TE's updater flashes them over SysEx, but nothing public uses it beyond updates.
- So an OP arranger can only be an **offline file builder**, while EP companion apps can work live.

**How people learn a device's protocol:** read the official tool's code when it's a web page (the
updater's `TE_SYSEX_DFU`, the sample tool's `TE_SYSEX_FILE_*`); record the traffic while the official
tool runs (how the Seqtrak protocol was found); then experiment, starting with read-only requests.

**The Seqtrak has both doors**: the live parameter protocol the bridge already uses, and the `.Y3P`
export (`docs/Seqtrak/Y3P-PROJECT-FILE.md`). A Seqtrak arranger (`seqtrak-arranger.md`) therefore
doesn't have to be offline-only like field-arrange: it could prepare projects as files *and* audition or
adjust them live while the Seqtrak plays.

## 5. Open platforms to study

Local clones in `OpenSource/`:

| Project | Why it's interesting |
|---|---|
| **Zynthian** (`zynthian-ui`, `-sys`, `-hw`, `zyncoder`, `-webconf`) | A complete open-source Pi synth platform: custom hardware, RT tuning, many engines, web config. The closest thing to an open Move. |
| **Blokas** (`pisound`, `patchbox-os-gen`, `rpi-kernel-rt`) | Pisound audio/MIDI hat driver, an audio-tuned Raspberry Pi OS build, and real-time kernel builds |
| **Critter & Guitari Organelle** (`Organelle_OS`, `Organelle_Controller`) | A Pi-class instrument running Pure Data patches; the controller repo is the microcontroller side |
| **Ableton `push-interface`** | Ableton's published Push 2 MIDI and display protocol |

## 6. Lessons for open-push

For the bridge now (tracked in Linear as epic KM-244, *Bridge · Architecture & reliability*, KM-254 to KM-258):
1. Never block inside a handler. Turn multi-step reads into operations the main loop advances.
2. Save settings atomically (temp file + `os.replace`). The Pi runs off a battery bank.
3. One owner per surface: modes as pages, LEDs and LCD drawn on a fixed clock.
4. A read-only root filesystem on the Pi, with a small writable data area.

The bridge's target architecture (modules, separate programs, packaging): `bridge-architecture.md`.

For a standalone instrument: see `standalone-instrument.md`.
