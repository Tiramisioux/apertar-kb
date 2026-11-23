# Inventory WCP-08: WebControlPage.cpp, new-file lines 16406-16620 (stage 1, no judging)

Diff: /home/user/build/review/diffs/WCP.part08.diff, one hunk, +174 lines, 0 deleted. Read @cinemate-port.

## Region

| Lines @cinemate-port | What | Commit | Status |
| --- | --- | --- | --- |
| 16419-16421 | `const frameBufferBar = {...}` page-level state object (fill, fillAtMs, timer, inFlight, recording, active, safetyStop, stopPercent, stopSeen, discardedSeen, preroll, prerollFps, prerollAtMs, prerollUntilMs) | d44b177 | new |
| 16426-16428 | `prerollPollWanted()` | d44b177 | new |
| 16430-16433 | `startFrameBufferTimer()`, 250 ms setInterval | d44b177 | new |
| 16435-16439 | `notePrerollRequested()`: 5 s poll window after the page's pre-roll button | d44b177 | new |
| 16441-16456 | `applyPrerollPill(active, recording)`: toggles `.preroll` on `.status-pill` and `#statusDot`, sets label "PRE-ROLL", back to "READY" | d44b177 (line 16458 touched by c5db8b2) | new |
| 16458-16471 | `noteBufferSafetyStop(flag, percent, discarded)`: toast "Recording stopped: the write buffer reached N %." and toast "Record pressed during the flush: N unwritten frames ... were discarded." | d44b177 body; discard toast + discardedSeen by c5db8b2 | new |
| 16473-16489 | `applyFrameBufferPillClasses(pill)`: `.buffer-drain` class; after a safety stop removes `recording` from pill and dot, label REC -> READY | d44b177 shell; safetyStop block 16479-16488 by c5db8b2 (fb5801c per fork-log, folded) | new |
| 16491-16539 | `pollFrameBufferBar()`: fetch GET /api/buffer, 800 ms abort, writes `state.snapshot.storage_preroll_*`, calls applyPrerollPill, showPrerollFpsText, noteBufferSafetyStop; self-stops when idle | d44b177; lines 16522-16527 by c5db8b2 | new |
| 16541-16545 | `stopFrameBufferPolling()` | d44b177 | new |
| 16547-16588 | `updateFrameBufferBar(snapshot, pill)`: called from the 1 Hz render (call at 16757 area, `updateFrameBufferBar(snapshot, statusPill)`); decides bar on/off from `ui.frame_buffer_bar_enabled` and `buffer_mode` frames/ram; merges poll and snapshot values; watchStop branch when bar off | d44b177; watchStop 16562-16572 by c5db8b2 | new |
| 16406-16415, 16590-16620 | context lines (upstream fetchState tail, fetchPresetLibrary) | upstream | unchanged |

Blame counts of region (215 lines): d44b177 143, upstream 35dbe67 41, c5db8b2 31.

## Commits

| Commit | Subject | Fork-log status |
| --- | --- | --- |
| d44b177 | drop-frames: trim the recording drive, Log, RAM write buffer with safety stop, buffer bar, fps max, storage pre-roll (squashed, fork-log.md:138) | "Not yet run on the camera" at entry; Pi build and `--simulate` serving WebUI, four Sonnet reviews; fork-only, offered in pieces after Pi tests |
| c5db8b2 | record during a safety-stop flush discards queued frames and starts at once (owner decision 2026-11-01); fb5801c (pill READY green while buffer empties) is folded into the same region | on GitHub, Mac, Pi; camera test not recorded |

## Features (operator-visible)

| Feature | Operator sees |
| --- | --- |
| Frame buffer bar | Red fill inside the REC pill showing the write-buffer level, option off by default; polled at 4 Hz while recording or draining |
| Safety stop pill | At buffer_stop_percent (ram mode, 90 %) pill goes READY green while bar drains; toast "Recording stopped: the write buffer reached N %." Works with bar option off |
| Flush discard toast | Pressing record during the flush discards queued frames; toast with the count |
| Storage pre-roll pill | Blue PRE-ROLL pill in WebUI within a fraction of a second; fps readouts marked as system value; poll window 5 s after page button |

## Interfaces touched by this region (read or written, not defined here)

| Kind | Name | Where defined |
| --- | --- | --- |
| HTTP route | GET /api/buffer (lock-free) | src/ApertarCoreApp.cpp:8419 @cinemate-port; not in upstream (grep of core-upstream src: no hit) |
| payload fields read | buffer_fill, recording, buffer_safety_stop, buffer_stop_percent, buffer_flush_discarded, storage_preroll_active, storage_preroll_fps, storage_preroll_auto, storage_preroll_auto_env | ApertarCoreApp.cpp:235-250 |
| state fields read | snapshot.buffer_mode ("frames"/"ram"), snapshot.buffer_fill, snapshot.buffer_safety_stop, snapshot.buffer_stop_percent, snapshot.buffer_flush_discarded, snapshot.storage_preroll_* , snapshot.recording | state merge at WCP:13843-13858 |
| UI state | uiState.frame_buffer_bar_enabled (set by command set_frame_buffer_bar_enabled, WCP:14241; settings buttons WCP:16143) | UI.conf-style `ui` object |
| Socket commands | none added in this region (storage_preroll sent at WCP:19826, notePrerollRequested at 19827; set_storage_preroll WCP:14030) | other parts |
| Events | none in this region ("buffer" event is Core side) | |
| Config keys / env vars / files | none in this region | [storage] buffer, [media] preroll live elsewhere |
| UI elements | DOM `.status-pill`, `#statusDot`, `#recordingStatus`; CSS classes `buffer-bar`, `buffer-drain`, `preroll` (CSS at WCP:178-236, other part); CSS var `--buffer-fill`; toasts via showToast | |
| Cross-region callers | WCP:14381 (optimistic check of safetyStop), 15389 (bufferStopped), 15757-15759, 15917, 19201 (flushing) read `frameBufferBar` | other WCP parts |

## Original code modified

None. Hunk is pure insertion between upstream `fetchState` finally-block and `fetchPresetLibrary`. Upstream lines 16406-16415 and 16590-16620 unchanged. (Upstream neighbours of the state object: `const state` style and `fetchState` with fetchInFlight/fetchQueued guard, WCP upstream ~10269.)

## New abstractions

| Name | Purpose | Upstream equivalent |
| --- | --- | --- |
| `frameBufferBar` global object | Holds poll timer, fill, safety-stop and pre-roll flags outside `state` | upstream keeps page state in the single `state` object (`state.fetchInFlight`, `state.fetchQueued`, WCP upstream near 10269) and has no second poll loop; probable: no equivalent |
| Second 250 ms poll loop (`pollFrameBufferBar`, own AbortController, own in-flight guard) | Faster lock-free read beside 1 Hz /api/state | upstream: only `fetchState` (1 Hz) and fetch queue; none for /api/buffer |
| Writes into `state.snapshot` from poll | Poll patches snapshot fields so the render path sees fresher values | upstream: snapshot replaced by fetchState only (confirmed pattern at fetchState; not re-grepped for other writers) |
| Direct DOM class edits outside render (`applyPrerollPill`, `applyFrameBufferPillClasses`) | Update pill between 1 Hz renders | upstream: pill classes set in the render function (WCP upstream 9794-9802) |

## Removed, narrowed, hidden

Nothing removed from upstream in this region.

## Board assumptions

None in this region (pure browser JS). Indirect: /api/buffer data and 4 Hz polling rate assume Core serves it without locking; buffer_mode ram/frames comes from a Core-side byte-budget queue (RAM size is Core's concern, not this region).

## Tested

d44b177 message: host tests, Pi build, `--simulate` serving WebUI, four Sonnet reviews. fork-log.md:138: "Not yet run on the camera". c5db8b2: no test statement in the message. No browser or UI test in the repo covers this JS (unconfirmed; settle with `grep -rn frameBufferBar tools tests`).
