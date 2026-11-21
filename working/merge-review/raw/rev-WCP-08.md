# Review WCP-08: WebControlPage.cpp new-file lines 16406-16620 (stage 2)

Scope: one inserted hunk, +174 lines, between upstream `fetchState` and `fetchPresetLibrary`. Commits d44b177 (143 lines), c5db8b2 (31 lines). Nothing upstream modified or removed. Yardstick: `raw/conv-webui.md` (C3 rule ids).

## Summary

The block adds a second, 4 Hz poll of a new lock-free `GET /api/buffer`, a second page-level store `frameBufferBar`, and DOM edits of the status pill outside `renderSnapshot`. It drives the buffer bar, the safety-stop pill and toasts, the flush-discard toast and the storage pre-roll pill. The reason is real and stated in code: `/api/state` blocks while a stopped take drains (WCP:16564-16565 @cinemate-port). The shape is foreign to upstream's single-store, single-poll, render-from-snapshot design (C3-I2, C3-I3, C3-N8). Rework: keep the lock-free route, but put the poll state in `state`, merge the polled fields into `state.snapshot` like a command patch, and let one pill-render path own the classes.

## Findings

| Id | Cat | Sev | Title |
| --- | --- | --- | --- |
| WCP-08-F1 | mismatch | major | Second poll loop + second store + DOM edits outside render |
| WCP-08-F2 | duplication | minor | Pill/pre-roll/safety-stop class logic written twice (poll path and render path) |
| WCP-08-F3 | slop | minor | Narrating comments and three ad-hoc 1000 ms freshness windows |
| WCP-08-F4 | new-ground | minor | 4 Hz poll exists because /api/state blocks during drain (Core cause) |

### F1 mismatch, major. Second poll loop, second store, DOM edits outside render

Port (confirmed @cinemate-port):
- WCP:16419-16421 `const frameBufferBar = { fill: 0, fillAtMs: 0, timer: 0, inFlight: false, recording: false, active: false, safetyStop: false, ... prerollUntilMs: 0 };` 14 fields, own timer and in-flight guard.
- WCP:16430-16433 `frameBufferBar.timer = window.setInterval(pollFrameBufferBar, 250);`
- WCP:16508-16515 poll writes `state.snapshot.storage_preroll_active = ...` etc. into the snapshot between /api/state fetches.
- WCP:16441-16456 `applyPrerollPill` and 16473-16489 `applyFrameBufferPillClasses` toggle `.preroll`, `.recording`, `.writing`, `.buffer-drain` and rewrite `#recordingStatus` text ("READY", "PRE-ROLL") outside `renderSnapshot`.
- Read from five other places: WCP:14381, 15389, 15757-15759, 15917, 19201.

Upstream (confirmed @upstream-1.6.0):
- One store: `const state = {` WCP:4204; timers as `state.<x>Timer` (C3-I2).
- One poll: WCP:11609 `window.setInterval(() => fetchState(true), 1000);` (C3-I3; C3-N8 "1 s polling only").
- Pill classes set only in `renderSnapshot`, WCP:9794-9802, including the post-stop state: `statusDot.classList.toggle("writing", !!snapshot.media_writes_pending && !isRecording && !isTimelapse);`
- Fresher-than-poll values come from `sendCommand` -> `applyCommandSnapshotPatch` -> `renderSnapshot` (WCP:9109-9145), i.e. patch the snapshot, then render.
- C3-I2 / C3-I3 list "a second store" and "per-control polling, DOM-only updates" as counter-examples.

Why it matters: two writers of the pill (render and poll) with timing guards (`fillAtMs`, `prerollAtMs` < 1000 ms) decide who wins; the original developer must read 170 lines to know why the pill says READY while `recording` is true. Every later pill change has to be made in both paths (see F2).

Deliberate: yes. WCP:16416-16418 and 16563-16565 comments; c5db8b2 message ("the WebUI polls /api/buffer also with the bar option off").

Rework (M):
1. Move the fields into `state`: `state.bufferPollTimer`, `state.bufferPollInFlight`, `state.bufferPolledAtMs`, `state.prerollPollUntilMs`, `state.bufferStopToastShown`, `state.bufferDiscardSeen`. Delete `frameBufferBar`.
2. Rename `pollFrameBufferBar` -> `fetchBufferState` (upstream `fetch<X>` naming, C3-I6), keep the lock-free route. On reply: `Object.assign(state.snapshot, payload)` restricted to the flat buffer/preroll keys (a named `applyBufferSnapshotPatch(payload)`, same spirit as `applyCommandSnapshotPatch`), then call one pill render function.
3. Extract the status pill block of `renderSnapshot` (WCP:15752-15771) into `renderRecordingStatus(snapshot)`, called from `renderSnapshot` and from `fetchBufferState`. Delete `applyPrerollPill`, `applyFrameBufferPillClasses`, and the `wasShown`/"READY" label rewrite; the pill text and classes come only from the snapshot (`buffer_safety_stop`, `buffer_fill`, `storage_preroll_active`).
4. Toasts: move into the snapshot-change pattern upstream already uses for `recording_error` (`"Recording stopped: " + snapshot.recording_error`, C3-N5, upstream WCP:9331-9333): compare previous vs new `buffer_safety_stop` / `buffer_flush_discarded` in one place.
5. Start/stop of the 250 ms timer decided in one function from the snapshot (`recording || buffer_safety_stop || buffer_fill > 0 || preroll window`).
Risk: C3-N7 says do not split `renderSnapshot` unasked; extracting only the pill block is a small, justified split. Pre-roll pill latency stays as now.

### F2 duplication, minor

- Pre-roll pill: `applyPrerollPill` WCP:16441-16456 vs render WCP:15758-15763 (`statusPill.classList.toggle("preroll", prerollNow); ... setText("recordingStatus", "PRE-ROLL")`).
- Safety-stop pill: `applyFrameBufferPillClasses` WCP:16479-16488 removes `recording`/`writing` vs render WCP:15752, 15764-15767 (`pillRecording`, `buffer_safety_stop !== true`).
- Timer start: inline `frameBufferBar.timer = window.setInterval(pollFrameBufferBar, 250);` WCP:16587-16588 duplicates `startFrameBufferTimer()` WCP:16430-16433.
Rework: disappears with F1 step 3; standalone fix for the timer is calling `startFrameBufferTimer()` (S).

### F3 slop, minor

- C3-I9: upstream has 2 JS comment lines in 7573. This block has 9 comment lines, several narrating behaviour across Core ("/api/state blocks while a stopped take drains", "the 1 Hz render sets the real text", "also with the bar option off: the safety stop must drop the red pill").
- Three separate `performance.now() - x < 1000` freshness checks (WCP:16555, 16561, 16578) encode the race between the two writers.
Rework: with F1 the race and its comments go; keep one comment at the poll naming why it is lock-free (S).

### F4 new-ground, minor. Why there is a 4 Hz poll at all

No upstream precedent for a faster-than-1 Hz server poll (upstream's 16 ms `startLiveReadoutLoop` WCP:9237 interpolates locally, no fetch). Cause: `/api/state` blocks during a RAM-buffer drain (port Core behaviour, not upstream). Verdict: keep the lock-free route and a fast poll only while recording/draining/pre-roll (it is bounded and self-stopping, WCP:16533-16537), but in the F1 shape. Worth a note in the handoff that the underlying fix would be a non-blocking `/api/state` during drain, which would make the second poll unnecessary for the safety stop.

## Checked, not reported

- `/api/buffer` reply is raw flat JSON without `ok`/`id`: same as upstream `/api/state` (`response.body = buildWebStateJson();` App:7157 @upstream-1.6.0). Conforms. Flat scalars only.
- No socket command added; no change to upstream behaviour when buffer mode is not frames/ram (bar off, poll only runs for pre-roll window).
- Bar option is a UI.conf-style `ui.frame_buffer_bar_enabled`, off by default (C3-R1 pattern, defined elsewhere).
- Toast wording "Recording stopped: ..." mirrors upstream's `"Recording stopped: " + snapshot.recording_error`.
- No tutorial/ticket numbers, no console logging, no env knobs in this block.
- Fetch abort at 800 ms + `.catch(() => {})`: upstream precedent for a silent fetch is `notifyStandbyActivity` (C3-I4 exception).

## Abstraction verdicts

| Name | Verdict | Reason |
| --- | --- | --- |
| `frameBufferBar` global object | rework-to-upstream-pattern | C3-I2: fields belong in `state` |
| Second 250 ms poll loop | simplify | Keep (lock-free need is real), but as `fetchBufferState` in `state.*Timer` style, one start/stop decision |
| Poll writes into `state.snapshot` | rework-to-upstream-pattern | Do it as a named patch function then render, like `applyCommandSnapshotPatch` -> `renderSnapshot` |
| Direct DOM class edits outside render (`applyPrerollPill`, `applyFrameBufferPillClasses`) | rework-to-upstream-pattern | One `renderRecordingStatus(snapshot)` used by render and poll; upstream sets pill classes only in render (WCP:9794-9802) |

## Conforms

- Plain ES2017, no framework, no storage, `fetch` with `cache: "no-store"` (C3-I1).
- Insertion only; upstream `fetchState`, `fetchPresetLibrary` untouched.
- Flat payload, scalar fields; route reply shaped like upstream `/api/state`.
- Toasts through the single `showToast`, error flag for stop events (C3-N5).
- Formatting: 4/2-space indent, double quotes, brace-less single-statement `if` (C3-I8).

## Skeptic

Checked at `cinemate-port` (`git show cinemate-port:src/web/WebControlPage.cpp`) and `/home/user/wt/core-upstream` (`upstream-1.6.0`). All port line numbers in the findings match. Upstream anchors confirmed: `const state = {` WCP:4204, `window.setInterval(() => fetchState(true), 1000);` WCP:11609, pill toggles WCP:9794-9802, `sendCommand` WCP:9109 with `renderSnapshot(state.snapshot)`, `recording_error` toast WCP:9331-9333 inside `renderSnapshot`, `startLiveReadoutLoop` 16 ms WCP:9237. Upstream has exactly three `setInterval` calls (9237, 9311, 11609), none fetches faster than 1 Hz. Core route `/api/buffer` App:8418-8426 @cinemate-port, comment "Lock-free: no commandMutex_, no controller mutex." confirmed. c5db8b2 message confirmed ("the WebUI polls /api/buffer also with the bar option off").

| Id | Verdict | Why |
| --- | --- | --- |
| WCP-08-F1 | stands | Every port line confirmed; upstream sets pill classes only in `renderSnapshot` and keeps all state in `state`. Rework is feasible: `state.snapshot` exists while `/api/state` blocks, so patch + pill re-render works. One caution added: `/api/buffer` `recording` is false during a safety stop (App:8424), so it must not overwrite `snapshot.recording`; merge it as `buffer_recording`. |
| WCP-08-F2 | stands | Confirmed: `applyPrerollPill` (16441-16456) vs render 15758-15763 (they differ: render also gates on `isTimelapse`); `applyFrameBufferPillClasses` 16479-16488 vs render 15752, 15765-15767; inline `setInterval` 16587-16588 duplicates `startFrameBufferTimer()` 16430-16433. |
| WCP-08-F3 | corrected | Rule id wrong: comments are C3-I7 in the rule table (conv-webui.md:322; prose section "I9" at :150). Count wrong: 11 comment lines in the block (16416-16418, 16423-16425, 16455, 16484, 16514, 16564-16565), plus 2 added inside `renderSnapshot` (15758, 15765). Added: the header comment 16416-16418 is stale ("polled ... only while the option is on"), c5db8b2 made it poll with the option off too. |
| WCP-08-F4 | stands | No upstream sub-second fetch loop; the blocking `/api/state` during a drain is port Core behaviour (upstream has no RAM drain). Keep-in-F1-shape verdict is right. |

## Final findings

### WCP-08-F1 [mismatch, major] Second 4 Hz poll loop, second global store and pill DOM edits outside renderSnapshot
- where: src/web/WebControlPage.cpp:16419-16421@cinemate-port ; :16430-16433 ; :16441-16489 ; :16491-16539 ; :16508-16515
- port way: `const frameBufferBar = { fill, fillAtMs, timer, inFlight, recording, active, safetyStop, stopPercent, stopSeen, discardedSeen, preroll, prerollFps, prerollAtMs, prerollUntilMs }` (14 fields); `window.setInterval(pollFrameBufferBar, 250)`; the poll writes `state.snapshot.storage_preroll_*` directly and toggles `.preroll/.recording/.writing/.buffer-drain` and `#recordingStatus` text in `applyPrerollPill` / `applyFrameBufferPillClasses`. 1000 ms freshness guards decide whether the poll or the 1 Hz render wins. `frameBufferBar` is read from 5 other places (WCP:14381, 15389, 15757-15759, 15917, 19201).
- Apertar way: one store `const state = {` WCP:4204@upstream-1.6.0, timers as `state.<x>Timer` (C3-I2). One poll `window.setInterval(() => fetchState(true), 1000)` WCP:11609@upstream-1.6.0 (C3-I3, C3-N8). Pill classes set only in `renderSnapshot` WCP:9794-9802@upstream-1.6.0, incl. `statusDot.classList.toggle("writing", !!snapshot.media_writes_pending && !isRecording && !isTimelapse)`. Fresher values go through `sendCommand` -> `applyCommandSnapshotPatch` -> `renderSnapshot` (WCP:9109-9145@upstream-1.6.0).
- why it matters: the pill has two writers that race, settled by timing guards. The original developer must read about 170 lines to learn why the pill shows READY while `recording` is true, and every later pill change must be made in both paths.
- rework: move the fields into `state` (`bufferPollTimer`, `bufferPollInFlight`, `bufferPolledAtMs`, `prerollPollUntilMs`, `bufferDiscardSeen`) and delete `frameBufferBar`. Rename `pollFrameBufferBar` to `fetchBufferState`, keep the lock-free route. On each reply call `applyBufferSnapshotPatch(payload)`, which merges the flat buffer/preroll keys into `state.snapshot` (the reply's `recording` goes in as `buffer_recording`, never over `snapshot.recording`, since `/api/buffer` reports false during a safety stop, App:8424@cinemate-port). Extract the status-pill block of `renderSnapshot` (WCP:15752-15771) into `renderRecordingStatus(snapshot)` and call it from `renderSnapshot` and `fetchBufferState`. Delete `applyPrerollPill`, `applyFrameBufferPillClasses` and the READY/PRE-ROLL label rewrites. Fire the toasts from a previous-vs-new comparison of `buffer_safety_stop` and `buffer_flush_discarded`, like the `recording_error` toast (WCP:9331-9333@upstream-1.6.0). Start and stop the timer in one function that decides from the snapshot. Update the 5 outside readers to `state.snapshot` fields.
- rework risk: C3-N7 says do not split `renderSnapshot` unasked; extracting only the pill block is a small, justified split. Needs a Pi test of safety stop, flush-discard and pre-roll pill.
- effort: M
- deliberate: yes. Comments WCP:16416-16418 and 16563-16565; c5db8b2 message ("the WebUI polls /api/buffer also with the bar option off"); fork-log `fb5801c` entry.

### WCP-08-F2 [duplication, minor] Pre-roll, safety-stop pill and timer-start logic written twice
- where: src/web/WebControlPage.cpp:16441-16456@cinemate-port ; :15758-15767 ; :16479-16488 ; :16587-16588
- port way: `applyPrerollPill` repeats the render's preroll toggle and PRE-ROLL label code (and differs: render also excludes timelapse). `applyFrameBufferPillClasses` removes the `recording`/`writing` classes that the render also gates through `pillRecording` and `buffer_safety_stop`. The inline `setInterval` at 16587 duplicates `startFrameBufferTimer()`.
- Apertar way: each pill class has one writer, in `renderSnapshot` (WCP:9794-9802@upstream-1.6.0).
- why it matters: a change to the pill states must be made in two places, and the two copies already differ.
- rework: disappears with the F1 rework (`renderRecordingStatus`). Standalone: call `startFrameBufferTimer()` at 16587.
- effort: S
- deliberate: no

### WCP-08-F3 [slop, minor] Narrating and stale comments, three ad-hoc 1000 ms freshness windows
- where: src/web/WebControlPage.cpp:16416-16425@cinemate-port ; :16455 ; :16484 ; :16514 ; :16555 ; :16561 ; :16564-16565 ; :16578 ; :15758 ; :15765
- port way: 11 comment lines in the block plus 2 in `renderSnapshot`, narrating Core behaviour and the render race ("the 1 Hz render sets the real text", "also with the bar option off: the safety stop must drop the red pill"). The header 16416-16418 is stale: it says /api/buffer is polled "only while the option is on", c5db8b2 made it poll with the option off. `performance.now() - x < 1000` is checked three times (16555, 16561, 16578).
- Apertar way: C3-I7 (conv-webui.md:322, prose "I9" :150): 2 JS comment lines in the upstream page (WCP:8474-8475@upstream-1.6.0); comments, when any, give a one-line safety reason.
- why it matters: the comments exist to explain the two-writer race and read as patch history; one is already wrong.
- rework: after F1, keep one comment at `fetchBufferState` saying why it is lock-free (`/api/state` blocks during a drain), drop the freshness guards and the other comments.
- effort: S
- deliberate: no

### WCP-08-F4 [new-ground, minor] Faster-than-1 Hz server poll exists only because /api/state blocks during a RAM drain
- where: src/web/WebControlPage.cpp:16562-16572@cinemate-port ; src/ApertarCoreApp.cpp:8418-8426@cinemate-port
- port way: while recording or draining in frames/ram mode, or for 5 s after the pre-roll button (`notePrerollRequested`, WCP:19827), the page polls `/api/buffer` every 250 ms. The poll stops itself when idle (16533-16537).
- Apertar way: no precedent. Upstream's only sub-second loop is `startLiveReadoutLoop` at 16 ms (WCP:9237@upstream-1.6.0), which interpolates locally without fetching.
- why it matters: new architecture with a real need, but it adds load and a second data path. The root cause is on the Core side.
- rework: keep, in the F1 shape. The handoff should note that a non-blocking `/api/state` during the drain would remove the need for the fast poll for the safety stop (the pre-roll latency would still want it or a command patch).
- effort: S
- deliberate: yes. Code comment WCP:16563-16565, Core comment App:8418, c5db8b2 message.
