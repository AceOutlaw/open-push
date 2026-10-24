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

**Running it elsewhere**: the image targets the Pi 4 chip family. `ableton-move-lab` runs the Move
software in Docker or on a plain Pi 4 by faking the XMOS with an `LD_PRELOAD` shim. Personal research
only: it's Ableton's proprietary software.

## 4. Open platforms to study

Local clones in `OpenSource/`:

| Project | Why it's interesting |
|---|---|
| **Zynthian** (`zynthian-ui`, `-sys`, `-hw`, `zyncoder`, `-webconf`) | A complete open-source Pi synth platform: custom hardware, RT tuning, many engines, web config. The closest thing to an open Move. |
| **Blokas** (`pisound`, `patchbox-os-gen`, `rpi-kernel-rt`) | Pisound audio/MIDI hat driver, an audio-tuned Raspberry Pi OS build, and real-time kernel builds |
| **Critter & Guitari Organelle** (`Organelle_OS`, `Organelle_Controller`) | A Pi-class instrument running Pure Data patches; the controller repo is the microcontroller side |
| **Ableton `push-interface`** | Ableton's published Push 2 MIDI and display protocol |

## 5. Lessons for open-push

For the bridge now (tracked in Linear as epic KM-244, *Bridge · Architecture & reliability*, KM-254 to KM-258):
1. Never block inside a handler. Turn multi-step reads into operations the main loop advances.
2. Save settings atomically (temp file + `os.replace`). The Pi runs off a battery bank.
3. One owner per surface: modes as pages, LEDs and LCD drawn on a fixed clock.
4. A read-only root filesystem on the Pi, with a small writable data area.

For a standalone instrument: see `standalone-instrument.md`.
