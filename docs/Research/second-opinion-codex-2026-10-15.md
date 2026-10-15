# Second opinion: Codex review of the Push 1 → SEQTRAK bridge (2026-10-15)

Produced from `second-opinion-prompt.md`. It reviewed the working tree on skai, including the uncommitted
`requests.py` scheduler. It made no source changes and sent nothing to hardware. Line numbers refer to the tree
as it was then.

**Checked afterwards:** the four bugs in section 1 are confirmed in the code, and so is the empty-step wording in
section 5 (now fixed in `steps.toml`). The reviewer says the `BUTTONS` upper/lower names contradict the hardware
reference. That isn't the case: the user confirmed the names are correct for Push 1. The reviewer was reading the Push 2
map, which the project used as a starting point for Push 1. The two are close, but some buttons moved.

---

**Overall assessment:** the protocol research is ahead of the bridge's reliability architecture. The bridge still
treats cached values, successful sends and confirmed device state too much alike. The reviewer recommends pausing
feature work to strengthen state ownership, operation scheduling and rendering, and keeping the single-process
Python design.

## 1. Concrete failures (code findings)

| Finding | Consequence |
|---|---|
| The blocking note-list reader (`_read_note_list_blocking`) calls `request_note()`, which now only queues the request, and never pumps the queue. | Sampler and melodic deletes time out without sending their read. Push input waits meanwhile. |
| Sampler read completion is checked only when an empty reply arrives. | If the end-of-list replies arrive before a missing earlier note's reply, the list never completes. |
| A project change clears reads but leaves `_timed_sends`. | Scheduled select, copy and paste operations keep running against a different project. |
| Melodic note ownership records the pitch but not the original track, so a release goes to the current track. Session mode ignores pad releases. | Holding a note while changing track or opening Session can send its release to the wrong place, or drop it. |

**Suggested fixes:**
- Replace the blocking reader with an operation the main loop advances.
- For the sampler, remember the end index and re-check completeness after every reply. Keep full note records,
  including velocity.
- Route each release through a record of the voice it started:
  `held[pad] = Voice(track, channel, pitch, owner)`. Handle two pads producing the same pitch.
- Add hardware-free regression tests for all of these.

## 2. Make uncertainty part of the state model

Keep three things separate:
- **observed device state:** the value, its context, when it was observed, and how fresh it is;
- **pending intent:** what the performer asked for, and how that operation is going;
- **local UI state:** page, held modifiers, overlays, layout.

Each field carries `observed`, `desired`, `quality` (unknown / stale / pending / confirmed / failed),
`project_epoch` and `observed_at`.

**On a project load or reconnect:**
1. Advance the epoch.
2. Cancel the old context's reads **and queued writes**, including compound operations.
3. Mark project-dependent values as stale.
4. Wait until the device is responsive, then read the essentials first.
5. Refresh the visible view, then the rest in the background.
6. Show "Syncing" or "Partial sync" on the LCD until the essential fields are confirmed.

**Other points:**
- Read play and record state at startup.
- An epoch can't identify an old reply on the wire, so settling time and revalidation are still needed.
- Don't present a default as if it were the device's value. Relative encoders need a policy for adjusting a value
  that is unknown.

## 3. Schedule complete operations with explicit outcomes

A limit on outstanding requests is not a rate limit.

Use one output scheduler:
- separate limits for outstanding reads and for send rate;
- note releases and transport first;
- foreground edits before background discovery;
- coalescing only where the meaning allows it (for example a volume encoder);
- ordered compound operations (bank select + program change; copy then paste);
- explicit outcomes: success, failure, cancelled, uncertain;
- no blind retry of non-idempotent actions such as "add scene" or undo.

**Specifics:**
- Duplicate shows "DUPLICATED" when its commands are only scheduled. Show "Copying" until it's actually done.
- Note-list edits need a stable snapshot first, and a re-read afterwards.
- Give each input a bounded processing budget, and render once per batch.
- Use monotonic time.
- The rtmidi "unknown MIDI input error" isn't proven to be an overrun: upstream logs `-ENOSPC` separately. Check
  the library version and the actual return value before choosing a remedy.
- Add reconnecting while running, which cancels stale commands rather than replaying them.

## 4. One rendering owner per physical surface

Compose a frame (base view, then overlays from bottom to top) covering the LCD, the pads and the button LEDs, and
send the Push only what changed. Overlays claim the controls they use, and input follows the same ownership rules.
Background MIDI handlers update state and mark it dirty; they don't draw. On a Push reconnect, invalidate the cache
and send a full frame.

## 5. Narrower, executable protocol claims

The statuses mix where a fact came from (provenance) with how well it's proven. Keep the badges, but record
per-capability claims (`claims.read`, `claims.write`, meaning) and scope (firmware tested, tracks tested). Also make
these machine-readable: payload encoding, ranges, placeholder domains, response address, what an empty response
means, prerequisites, side effects, whether a retry is safe, and the verification method.

**Gaps:**
- Empty-step "empty payload" versus "no reply" (fixed).
- Placeholders match any hex value.
- The bridge cross-check checks coverage only, not command validity.
- Evidence is prose rather than run/case IDs.
- Grouped entries hide differences between their addresses.

**For the verify tool:**
- Restore in a `finally` block, and persist the originals first.
- Stop writing if a restore fails.
- Get exclusive control of the device, or go through the bridge's scheduler.
- Record raw transcripts, the firmware, and the spec and tool revisions.

## 6. Refactor around boundaries

**Order:** note ownership and non-blocking operations → state and sync → rendering and input ownership → pure
protocol encode/decode → individual views.

"Views emit intentions. Operations execute them. Incoming messages update observed state. Rendering consumes
state."

Replace the monkey-patched `request_parameter` with dependency injection. Keep the protocol code free of Push UI
imports.

**Parity:** the guide targets OS V2.00, but this unit runs V1. That's deliberate: see the arranger note. Track
protocol support, Push implementation and hardware acceptance separately, per firmware.

## Hardware tests the reviewer would run before adding features

- Rapid project switches (A→B→A) between projects that differ in tempo, scale, patterns and presets.
- Sweeps of the request window and send interval while playing, recording and loading.
- Repeated empty and set step reads, and empty and non-empty sampler lists.
- Pattern changes during step reads.
- Copy and paste interrupted by a project change.
- Held notes across track and view changes and disconnects.
- Which device- or app-side changes are broadcast.
- MIDI clock / start / stop capture.
- Rebooting and reconnecting each device on the mounted rig.
