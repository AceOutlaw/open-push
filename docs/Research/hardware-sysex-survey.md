# Hardware SysEx Survey

*Research compiled December 24, 2024*

This document surveys hardware devices that use SysEx protocols, ranked by how accessible they are for the OpenPush "Universal Hardware Decoder" approach.

---

## Viability Tiers

### Tier 1: Well-Documented / Already Decoded

These devices have official or community-decoded SysEx protocols.

---

### Novation Circuit / Circuit Tracks

**Status: Excellent - Official Documentation**

Novation provides an official [Programmer's Reference Guide](https://fael-downloads-prod.focusrite.com/customer/prod/s3fs-public/downloads/Circuit%20Programmers%20Reference%20Guide%20v1-1_0.pdf) with complete SysEx documentation.

**Available:**
- Synth Patch SysEx Message Formats
- Replace Patch / Patch Dump Request
- Full sample manipulation via SysEx
- [midi.guide documentation](https://midi.guide/d/novation/circuit/)

**Key Quote:** *"Novation has a history of giving users 'hackable hardware' by building devices with pervasive and well-documented external control."* — [Cycling '74](https://cycling74.com/articles/hardware-reoverview-novation-circuit)

**Notes:**
- SysEx works best over USB (faster, more reliable)
- Messages need 20ms gaps between them
- Python modules exist for sample manipulation

**Viability for OpenPush:** HIGH - Official docs make this straightforward.

---

### Korg Volca FM

**Status: Good - Community Decoded**

The Volca FM has extensive SysEx control, especially with custom firmware.

**Available:**
- [Nora Patches SysEx Editor](https://norapatches.com/devices/volcafm/) - Max 4 Live device
- Requires custom firmware v1.09 (by Reddit user pajen)
- Sends MIDI CC and SysEx for all parameters

**Other Volcas:**
- Volca Keys has a [third-party editor](https://korg-volca-keys-editor.jimdofree.com/)
- Volca Sample uses MIDI CC on channels 1-10 (one per part)
- [Official MIDI Implementation Charts](http://i.korg.com/uploads/Support/USA_volcakeys_MIDI_Chart_E.pdf) available

**Notes:**
- Volcas only have MIDI IN (no MIDI out for state feedback)
- 5-pin DIN only, need adapter for USB

**Viability for OpenPush:** MEDIUM - Volcas are limited by one-way MIDI.

---

### Yamaha Seqtrak

**Status: Decoded - OpenPush Project**

See: `docs/Features/open-push-seqtrak-integration.md`

We've decoded:
- Tempo, Scale, Key, Swing
- Track Mute/Solo states
- Pattern variations
- Master volume
- Many internal parameters

**Viability for OpenPush:** HIGH - Already done!

---

### Roland TR-8 / TR-8S

**Status: Good - Official MIDI + Community SysEx Investigation**

Roland provides official MIDI documentation, and community is actively decoding SysEx.

**Official Resources:**
- [MIDI Implementation Chart (PDF)](https://static.roland.com/assets/media/pdf/TR-8S_MIDIImpleChart_eng01_W.pdf)
- All front panel knobs transmit MIDI CC (Tune, Decay, CTRL, Global FX, Master FX)
- Pattern and Kit channels independently configurable
- Per-track MIDI note number assignment

**Community SysEx Work:**
- [compuphonic/TR-8S-SysEx](https://github.com/compuphonic/TR-8S-SysEx) - Active investigation project
- Users have extracted SysEx for parameters like Filter Cutoff
- SysEx ID visible in Utility settings (confirms SysEx is implemented)

**Key Quote:** *"Understanding the SysEx implementation opens the door to the creation of a potential editor for the TR-8S."*

**Bidirectional:** Yes - TR-8S transmits knob changes as MIDI, can read state back.

**Viability for OpenPush:** HIGH - Official MIDI docs + active community investigation.

---

## Tier 2: Reverse Engineered / Community Projects

These require work but have community projects to reference.

---

### Elektron Digitakt / Digitone / Syntakt

**Status: Partially Decoded by Community**

Official Elektron stance: Limited documentation. SysEx used mainly for backup/restore.

**Community Resources:**
- [Kompanion](https://github.com/tomduncalf/kompanion) - Uses "unpublished SysEx commands" from libanalogrytm
- [Elektroid](https://github.com/dagargo/elektroid) - FLOSS sample manager, reverse-engineered filesystem commands
- [midi.guide for Digitakt](https://midi.guide/d/elektron/digitakt/) - MIDI CC and NRPN documentation

**Key Quote:** The Kompanion project implements kit functionality "using unpublished SysEx commands."

**Challenges:**
- Protocol not officially documented
- Need to capture and decode like we did with Seqtrak
- Community has done some of this work already

**Viability for OpenPush:** MEDIUM-HIGH - Community groundwork exists, would need capture session.

---

### Roland MC-101 / MC-707

**Status: Reverse Engineered - Hidden Protocol**

Roland officially claims no SysEx support, but this is false.

**Key Discovery:**
*"The two Roland grooveboxes do not officially support MIDI SysEx messages... In reality, the MC-101/707 are able to receive and send such messages."* — [Benis67's Editor Project](https://roland-mc707-mc101-editor.jimdofree.com/)

**Technical Details:**
- MC-101 Model ID: `00 00 00 5E`
- MC-707 Model ID: `C0 00 00 00 C0h`
- Uses Roland-standard DT1 requests
- Example clip launch: `F0 41 11 00 00 00 C0 12 10 00 08 0D 00 5B F7`

**Quirks:**
*"When you ask for a zen-core tone with MIDI SysEx, the MC-101 and MC-707 send the wrong SysEx messages but in the correct order."*

**Resources:**
- [Awesome-MC-707 GitHub](https://github.com/ricardofeynman/Awesome-MC-707) - Tips, tricks, SysEx tools
- [Benis67 ZEN-Core Editor](https://roland-mc707-mc101-editor.jimdofree.com/) - Commercial editor using reverse-engineered SysEx
- [Roland MIDI Implementation Chart (PDF)](https://static.roland.com/assets/media/pdf/MC-707_MIDIImpleChart_eng03_W.pdf)

**Viability for OpenPush:** MEDIUM - Decoded but quirky, needs careful implementation.

---

## Tier 3: Limited / CC-Only / Needs Research

---

### Teenage Engineering OP-1 / OP-Z

**Status: MIDI CC Only (No SysEx Found)**

These devices have good MIDI CC control but SysEx documentation is absent.

**OP-Z:**
- Each of 16 tracks sends/receives MIDI
- Custom CC assignment per track
- [Official MIDI Guide](https://teenage.engineering/guides/op-z/midi)
- [midi.guide OP-Z](https://midi.guide/d/teenage-engineering/op-z/)

**OP-1 / OP-1 Field:**
- Controller mode for external VSTs
- Internal sequencers can drive external MIDI
- Bluetooth MIDI on Field version
- [midi.guide OP-1](https://midi.guide/d/teenage-engineering/op-1/)

**Viability for OpenPush:** LOW for deep control - MIDI CC only, no SysEx for internal parameters.

---

### Arturia DrumBrute / MicroFreak

**Status: Poor Documentation**

**MicroFreak:**
- [midi.guide MicroFreak](https://midi.guide/d/arturia/microfreak/) - CC documentation exists
- MIDI Control Center app for presets/firmware
- Full SysEx documentation NOT publicly available

**User Frustration:**
*"When do we get full MIDI and SYSEX implementation details for this machine? There's really no excuse we don't have these docs yet."* — [Gearspace Forum](https://gearspace.com/board/electronic-music-instruments-and-electronic-music-production/1247338-arturia-microfreak-experimental-hybrid-synthesizer-69.html)

**DrumBrute Impact:**
- Receives Song/Bank/Pattern changes via MIDI
- Clock sync works (internal/external)
- Limited deep control

**Viability for OpenPush:** LOW-MEDIUM - Would need full reverse engineering.

---

## Tier 4: Proprietary / Locked Down

---

### Native Instruments Maschine

**Status: Not Viable**

As discussed earlier, Maschine uses HID protocol (not MIDI) for display and advanced features.

**Why It's Different:**
- 480×272 pixel displays require proprietary protocol
- Not SysEx-based
- NI has not opened the protocol

**Viability for OpenPush:** NOT VIABLE with current approach.

---

## Summary Matrix

| Device | SysEx Docs | Community Work | Bidirectional | OpenPush Viability |
|--------|------------|----------------|---------------|-------------------|
| Novation Circuit | Official | Extensive | Yes | HIGH |
| Yamaha Seqtrak | Decoded | OpenPush | Yes | HIGH (Done) |
| Roland TR-8/TR-8S | Official MIDI + SysEx | compuphonic project | Yes | HIGH |
| Elektron Digitakt/Digitone | Unofficial | Kompanion, Elektroid | Yes | MEDIUM-HIGH |
| Roland MC-101/707 | Hidden | Benis67 Editor | Yes (quirky) | MEDIUM |
| Korg Volcas | Partial | Various | No (MIDI In only) | MEDIUM |
| TE OP-1/OP-Z | CC only | Limited | Yes | LOW |
| Arturia MicroFreak | Poor | None | Yes | LOW-MEDIUM |
| NI Maschine | None (HID) | None | N/A | NOT VIABLE |

---

## Recommended Priority

1. **Roland TR-8/TR-8S** - User has hardware, official MIDI docs, community SysEx work exists
2. **Novation Circuit** - Official docs, easy win
3. **Elektron Digitakt** - High demand, community groundwork exists
4. **Roland MC-707** - Interesting challenge, hidden but decoded
5. **Korg Volca FM** - Fun project, limited by one-way MIDI

---

## Capture Methodology

For any device, apply the Seqtrak methodology:

1. Connect MIDI monitor
2. Systematically activate every control
3. Log all SysEx with timestamps
4. Pattern match: address structure, value ranges, timing
5. Correlate physical actions to addresses
6. Document in repository
7. Build Python control class

See: `docs/DEVLOG.md` section "2024-12-24: Seqtrak SysEx Reverse Engineering"

---

## Resources

### General MIDI/SysEx

- [midi.guide](https://midi.guide/) - Crowdsourced MIDI CC/NRPN documentation for many devices
- [MIDI Association](https://www.midi.org/) - Official MIDI specifications

### Device-Specific

- [Elektroid](https://github.com/dagargo/elektroid) - Elektron device manager
- [Kompanion](https://github.com/tomduncalf/kompanion) - Elektron kit functionality
- [Awesome-MC-707](https://github.com/ricardofeynman/Awesome-MC-707) - Roland MC tips/tricks
- [Circuit Programmer's Guide (PDF)](https://fael-downloads-prod.focusrite.com/customer/prod/s3fs-public/downloads/Circuit%20Programmers%20Reference%20Guide%20v1-1_0.pdf)

---

## Notes

- Devices with bidirectional SysEx are more valuable (can read state, not just send commands)
- One-way MIDI (like Volcas) limits display capabilities
- HID-based devices (Maschine) require completely different approach
- Community projects are goldmines for undocumented protocols
