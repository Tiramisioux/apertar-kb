# The automatic storage pre-roll: final plan

Read at: Core `/home/user/wt/core-work` `work/improve` `0d13a6f` (port `01f170c` + 10 fixes, among them `0977dd6` "core: the automatic storage pre-roll is off by default"; `0d13a6f` changes 3 lines in `CC` in place, so line numbers equal those at `3650027`), UI `/home/user/wt/ui-work` `ac1fc28`; measuring stick `upstream-1.6.0` (`/home/user/wt/core-upstream` `35dbe67`, `/home/user/wt/ui-upstream` `43888e5`). Line numbers are `@work` unless marked `@upstream`. Every claim was read in code (**confirmed**) unless it says otherwise. This page replaces the first design and its challenge; the table at the end says what the challenge changed.

## In short

- Today the pre-roll (a 2 s raw take written through the real write path and then deleted, to "warm" the drive) is run by an App worker thread. The worker takes the command lock itself, runs its own copy of the busy guards, starts the take outside `handleCommand`, times it every 25 ms, and stops it with no command lock.
- The take is a hidden second take kind in `CameraController` (CC): `recording_` stays false, its fps is pushed past the sanitiser and re-pinned on every request, and its exclusions are split between CC (3 entries) and an App list of 9 command names. `set_tuning_file` and `enter_standby` slip past CC.
- Its state is a header singleton (`storagepreroll::prerollState()`), published inside the camera settings serialiser, `/api/buffer` and the `buffer` event.
- Target: every start and every end goes through `handleCommand` under `commandMutex_`. No worker thread and no CC thread. The manual start is a command. The automatic start is a `ControlCommand` that the 1 Hz `wait()` loop sends, the way the idle timer sends `enter_standby`. The end is a `record_stop` that the same loop sends with an internal field, re-checked under the lock as upstream re-checks `idle_timeout`. Every CC capture entry refuses a running pre-roll. CC owns the state. App publishes it beside `timelapse_active` and in one `storage_preroll` event.
- Operators see what they see today: the blue PRE-ROLL pill in the WebUI, the blue PRE-ROLL chip on the touch screen and the HDMI monitor, the italic fps readout on all three screens, and the sentence "Storage pre-roll is running. One moment." Three things change, all on the owner's list: the run lasts 2-3 s instead of 2.0 s, the WebUI pill updates at 1 Hz instead of 4 Hz, and a refused manual start is answered with a sentence per cause and no "skipped: ..." line.
- The automatic pre-roll is already off by default (`0977dd6`). Where its switch is stored belongs to the storage-settings theme. Its fps (commit 12) waits for owner decision 1. Until then the rig's pre-roll runs at today's rate.
- 11 Core commits and 2 UI commits, plus one held commit. Without the held commit, Core loses about 390 lines and gains about 190.

## How it works in the port today

Short names: `App` = `src/ApertarCoreApp.cpp`, `AppH` = its header, `CC`/`CCH` = `src/camera/CameraController.{cpp,hpp}`, `SP` = `src/util/StoragePreroll.hpp`, `WCP` = `src/web/WebControlPage.cpp`, `ACB` = `Apertar-UI/src/ApertarControlBridge.cpp`, `SP.qml` = `Apertar-UI/qml/SettingsPage.qml`.

| Value or path | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| Automatic switch `[media] preroll`, `preroll_seconds` | `set_storage_preroll` via the hardware store `App:12917-12944`; the operator by hand | `requestStoragePreroll` parses the file at each request `App:11156-11158`; published as atomics `App:261-262` | command thread under `commandMutex_`; the media watcher, no lock | `apertar-hardware.conf [media]` (template `App:5071-5076`); env `APERTAR_STORAGE_PREROLL` beats it `SP:92-99` | WebUI Automatic pills `WCP:15834-15855` (shown only when `storage_preroll_auto` is a boolean `WCP:15836`); touch UI On/Off `SP.qml:5611-5636`. **The storage-settings theme owns this row** |
| Trigger: Core start, card insert | media watcher `App:10950-10964` (pure decision `SP:185-198`) | the request queue | media watcher thread, no lock | none | none |
| Trigger: format | `format_media` block `App:14635-14651` (`FormatScope` sets `storagePrerollFormatRunning_`/`DoneMs_` `AppH:171-172`) | the request queue and the mount decision | command thread, `commandMutex_` | none | none |
| Trigger: manual `storage_preroll` | WebUI button `WCP:19895-19902`, touch UI tile `ACB:621` | `App:14619-14633`: own guard copy, then an async request; reply `storage_preroll_started` | command thread, `commandMutex_` | none | toast "Storage pre-roll started" (no period) |
| Request queue: pending, manual, trigger, seconds, delay (3 s for automatic) | `requestStoragePreroll` `App:11152-11174` | `runStoragePreroll` `App:11188-11210` | `storagePrerollMutex_` + cv `AppH:284-293`; started in `start()` `App:8043-8046`, stopped twice (`App:8189`, `App:11060`) | none | none |
| Settle waits: trim done (up to 2 min), camera Ready or Standby (up to 30 s) | - | `runStoragePrerollOnce` `App:11235-11251`, polling every 200 ms | the worker, `mediaTrimMutex_` briefly | none | none |
| Busy guard (13 inputs) | `storagePrerollGuard` fills `GuardInputs` `App:11125-11148` | `decideGuard` `SP:128-165` | the worker **takes `commandMutex_` itself** `App:11256-11279` and runs `checkRecordingFailure`, the playback yield and `waitForMediaTrim` by hand | none | manual: "Storage pre-roll cannot run now: <reason>." and `storage_preroll_last` "skipped: ..." `App:14626-14630` |
| Take start | `camera_.startStoragePreroll` `CC:12053-12130` | - | worker under `commandMutex_` + CC `mutex_`; waits up to 1 s **with both held** in `waitForFramePeriod` `CC:12111` | none | - |
| Take start refusals | `CC:12061-12075`: "Storage pre-roll needs the camera." (also in `--simulate`), "already running", "Camera is not ready." for recording, time-lapse and every state but Ready | the manual reply never shows them: the guard copy answers first | - | - | - |
| Pre-roll fps | `prerollMaximumFps` (sensor max, past the lossless cap, ladder and ramp limits) `CC:3481-3491` | `setPrerollFps` -> override after the sanitiser `CC:7576-7578` and a `{p,p}` FrameDurationLimits on **every request** `CC:9076-9081`; reset on reconfigure `CC:7507` | session atomics, read on the libcamera thread | none | WebUI fps badge and pills italic `WCP:8682-8705`; touch UI `CameraPage.qml:3057-3059`; HDMI `ExternalMonitorWindow.qml:95-99` |
| `settings_` during the take | `applySettingsLocked(next, false, commit=false)` `CC:12103`, **before** `prerollTake_` is set `CC:12126`; restored from `prerollSaved_` `CC:12183-12194`, **after** `prerollTake_` is cleared `CC:12180` (`applySettingsLocked` refuses while it is set `CC:12747-12750`) | `settings()` `CC:12579` -> `get_state` `fps` | CC `mutex_` | not saved, no `settings` event | `get_state` `fps` reads the pre-roll fps for the run |
| Take kind flags | `prerollTake_` (`std::atomic<bool>` `CCH:226`); `prerollFps_` `CCH:229`; session `setPrerollTake` (safety stop off `CC:5509`, drop warning muted, no frames-per-folder split `CC:4292`) | CC entries | CC `mutex_` for every reader except `storagePrerollError` (no lock) `CC:12133-12139` | none | no REC, no tally, no `recording` event |
| Exclusions | CC: `startRecording` `CC:11995`, `applySettingsLocked` `CC:12747`, `setClipNameTemplate` `CC:11840`; App: 9 names `App:12605-12609`; trim and merge predicates `App:11478`, `App:11709` | - | - | - | "Storage pre-roll is running. One moment." **Missing in CC:** `enterStandby` `CC:10595`, `setTuningFile` `CC:11502` (not in App's list either), `capturePhoto` `CC:12198`, `startTimelapse` `CC:12234` |
| Length and stop | worker polls every 25 ms: clock, `storagePrerollError()`, medium mounted `App:11281-11297`; `record_stop` sets `storagePrerollStop_` and answers at once `App:14849-14852` | `camera_.finishStoragePreroll` `CC:12142-12196`: stop, count bytes, delete folder, restore settings | worker, **no command lock**; CC `mutex_` held during the drain | clip folder deleted | - |
| Idle timer | `wait()` resets `lastUserActivityMs_` on recording, time-lapse, sound only `App:8306-8310` | an expired timer sends `enter_standby` every second during a pre-roll; App's list refuses it each time | - | - | - |
| After: trim | `trimMedia("delete")` `App:11317` | trim worker | - | - | - |
| Status `storage_preroll_active/_fps/_last` (+ `_auto`, `_auto_env`) | the worker writes the singleton `prerollState()` `SP:224-272` | the free function `bufferSettingMembers` `App:252-269` (no `camera_`), called by `bufferMembers` `App:309`, `settingsBody` `App:393` and three replies `App:12869`, `12912`, `12943`; so `get_state`, the `settings` event, `/api/buffer` `App:8423-8430`, web state `system` `App:9591`, `buffer` event; `runBufferEvents` diffs 4 pre-roll values and ticks at 250 ms while active `App:11007-11053` | atomics + a small string mutex, no lock | none | WebUI PRE-ROLL pill from two writers: `renderSnapshot` `WCP:15391` and the 4 Hz `/api/buffer` loop `WCP:16423-16515`, second writer `WCP:15758-15763`; card last text `WCP:5778`. Touch UI reads them in `applyBufferState` `ACB:2726-2766` (from the `buffer` event `ACB:1345` and, through `applyCoreState` `ACB:1732`, from `get_state`); status chip PRE-ROLL `CameraPage.qml:2708` -> `StatusChip.qml:11,26,60`; HDMI `ExternalMonitorWindow.qml:188-198`; Settings tile disabled while active `SP.qml:5598-5606`, last text `SP.qml:5662` |

## How original Apertar does this kind of thing

| Kind of problem | Upstream precedent | What it shows |
| --- | --- | --- |
| Core acts by itself | Idle timer in `wait()` builds `ControlCommand{name "enter_standby", id -1, fields["idle_timeout"]}` and calls `handleCommand` (`App:7041-7047@upstream`, loop `App:7021-7053@upstream`) | Internal work enters through `handleCommand` (CMD-1, CMD-3). Periodic supervision lives in the 1 Hz loop (CMD-21) |
| An internal command that may be stale by the time it gets the lock | The `enter_standby` branch re-checks `idle_timeout` under the lock and answers `okReply` with nothing done when the operator was active meanwhile (`App:9139-9143@upstream`) | An internal field tells the branch to re-check, so a late internal command never undoes an operator's action |
| An App state value written by commands and read by `wait()` | `lastUserActivityMs_`, an atomic App member (read in `wait()` `App:7040-7044@upstream`, written by commands `App:8616`, `App:8650@upstream`) | One atomic, no new lock |
| A take Core runs outside CC | The sound-only take: App starts and stops it inside `record_start`/`record_stop` and publishes `{"event":"recording","active":...,"sound_only":true}` itself (`App:8394`, `App:8406`, `App:10783-10794@upstream`) | App may publish the event of a take it starts in a command branch |
| Telling clients about a run | `timelapse_active` among the status keys of `get_state` `App:9229@upstream` and `/api/state` `App:7845@upstream`; events that leave outside a command reply are in the broadcast list `App:10829-10838@upstream`; the UI applies status events through `applyCoreState` `ACB:1191-1195@upstream-ui` | Capture status = status keys + one event (R4 step 1). Not in `settingsBody` |
| A CC status read by App | `stillExposureStatus()` returns `{active, remainingSeconds}` under `mutex_` (`CCH:22-25`, `CC:8548-8552@upstream`); `photoWriteError()` returns a result string under `mutex_` (`get_state` `App:9234@upstream`) | A small struct and a string, read under the camera lock. No second lock |
| Commands refused while a run is on | Shared guards as `\|\|` lists at the top of `handleCommand`, each with its own sentence (`App:9095-9117@upstream`, CMD-4); each CC capture entry refuses the others (CAM-32: "Stop timelapse before recording." `CC:8224`; "Camera is not ready." for any state but Ready `CC:8229-8230@upstream`; "Wake the camera before capturing." `App:9211@upstream`) | Camera runs are refused in CC for every caller. App-level work is gated in App |
| Stopping whatever runs | `record_stop` stops the sound take first, then the camera take (`App:10783-10794@upstream`) | One stop command; a pre-roll branch fits at its top |
| Shutdown with a run on | `CC::stop()` calls `stopTimelapse()` before it takes `mutex_` (`CC:7651-7653@upstream`; `CC:10571-10575@work`) | CC ends its own runs first at shutdown |
| Slow job outside the command lock | Media speed test: worker thread, state group under `mediaSpeedMutex_`; the next start joins the old thread first (`App:8957-9089`, `joinMediaSpeedTest` `App:8968@upstream`) | A worker exists only for work that must not hold the lock. The pre-roll's 2-3 s take does not need one: the take runs in the camera session, only its start and end are commands |
| Where fps limits come from | Only the sanitise chain, read back as the effective value (`CC:2707-2744`, `CC:8713-8715@upstream`); `controlsForSettings` pins video to `{d, d}` (`CC:2022-2031@upstream`); the only per-request override is for bracket shots (`CC:6515-6530@upstream`) | No write after the sanitiser; one place sets FrameDurationLimits |
| Simulated camera | `record_start` runs without a session in `--simulate`: `!simulateCamera_ && session_ && !session_->startRecording(...)` (`CC:8247@upstream`) | A run can be exercised on a host without frames |

Time-lapse is **not** the precedent for the pre-roll's clock: `timelapseLoop` only queues stills under `mutex_` (`CC:8475-8483@upstream`) and is ended only by `stopTimelapse` from a command or `CC::stop()`. It never stops a take or changes `settings_`.

No precedent at all: a take that is written and then deleted, a take hidden from REC and tally, a run that starts by itself at boot, card insert or format. That is new ground (see below).

## The target

| Value or path | Before | After |
| --- | --- | --- |
| Manual start | `storage_preroll`: own guard copy, async request to the worker | `storage_preroll` (renamed `storage_preroll_start` in commit 13 if the owner agrees). It passes the head gates like `record_start`. The block parses `seconds` (file default as today), refuses during a sound take, calls `camera_.startStoragePreroll`, stores the end time, publishes the event and replies `"storage_preroll_started":true` (the reply field stays). It answers after the start, at most 1 s later (the period wait, see commit 12) |
| Automatic start | worker thread with a queue, a 3 s delay and polling waits | The watcher and `format_media` set one pending request (trigger, due time = now + 3 s, request time) under the existing `storagePrerollMutex_`. `wait()` sends `ControlCommand{"storage_preroll", id -1, fields trigger}` once it is due, the trim is idle and the camera is Ready or in Standby, or 150 s after the request. `wait()` never holds `storagePrerollMutex_` while it calls `handleCommand`. A refusal is logged as `skipped` |
| Lock at start and end | worker takes `commandMutex_` itself; the end has no command lock | `commandMutex_` via `handleCommand`, then CC `mutex_` inside `startStoragePreroll`/`finishStoragePreroll`, for both |
| Busy checks | `storagePrerollGuard` + `decideGuard` (13 inputs) | Head gates of `handleCommand` (media delete, writes pending, media gate, speed test, trim/merge wait, playback yield) + CC `startStoragePreroll` (already running; "Stop recording before a storage pre-roll."; "Stop timelapse before a storage pre-roll."; "Wake the camera before a storage pre-roll."; "Camera is not ready." for the other states; still mode; not raw; pending stills) + one sound-take line in the block. `decideGuard` and `GuardInputs` deleted |
| Exclusions while it runs | CC 3 entries + App 9 names | CC: every capture entry (`startRecording`, `capturePhoto`, `startTimelapse`, `enterStandby`, `setTuningFile`, `applySettingsLocked`, `setClipNameTemplate`) refuses with "Storage pre-roll is running. One moment." App: one head line `if (mediaAction && camera_.storagePrerollActive())` with the same sentence; the sound-only `record_start` branch refuses with it. The 9-name list is deleted |
| Length and end | worker polls every 25 ms and finishes with no command lock | `wait()`, once a second: when a pre-roll is active and its end time has passed, the recorder has latched an error, or the medium is gone, it sends `ControlCommand{"record_stop", id -1, fields["storage_preroll_end"] = "time" \| "error" \| "media_removed"}`. The `record_stop` branch finishes a running pre-roll (stop, count, delete, restore; under both locks), logs, publishes the event and calls `trimMedia("delete")`. With `storage_preroll_end` set and no pre-roll running it answers `okReply` and stops nothing, as `enter_standby` does with a stale `idle_timeout`. An operator's `record_stop` ends a pre-roll the same way and answers after the drain. `CC::stop()` finishes a running pre-roll first, as it stops time-lapse first |
| Fps | sensor maximum, override after the sanitiser, per-request pin | **unchanged until owner decision 1** (commit 12 is held) |
| State | header singleton, App writes | CC: `prerollTake_` becomes a plain `bool` under `mutex_`; the existing `prerollFps_`; a new `prerollLast_` string and the start time. `storagePrerollStatus()` returns `{active, fps, last}` under `mutex_`, shaped like `stillExposureStatus()`. Flag order stays as today: set after the fps apply, cleared before the restore. No new mutex |
| End time | worker's local clock | App atomic `storagePrerollEndMs_`, written by the start block, read by `wait()` (shape of `lastUserActivityMs_`) |
| Idle timer | not reset by a pre-roll | `camera_.storagePrerollActive()` joins the reset list in `wait()` |
| Published | `storage_preroll_active/_fps/_last` in `settingsBody`, `/api/buffer`, `system`, `buffer` event | Status keys after `timelapse_shot_count` in `get_state` and in the `/api/state` status block; event `{"event":"storage_preroll","storage_preroll_active":...,"storage_preroll_fps":...,"storage_preroll_last":"..."}` from the start block and the end, in the broadcast list. `/api/buffer` and the `buffer` event stay lock-free and lose the three keys. `storage_preroll_auto`/`_auto_env` stay where the storage-settings theme puts them |
| WebUI | pill from two writers, 4 Hz `/api/buffer` path | pill, fps italics and card from `renderSnapshot` only (1 Hz `/api/state`); the pre-roll branch of the 4 Hz loop is deleted; the `storage_preroll_` prefix stays in the `system` copy loop while the `_auto` keys live under `system` |
| Touch UI, HDMI | read from the `buffer` event and `get_state` | read from `get_state` and the `storage_preroll` event through `applyCoreState` (`ACB:1191@upstream-ui` shape). Same display: PRE-ROLL chip, italic fps readout, tile disabled, last text |
| `--simulate` | "Storage pre-roll needs the camera." | Runs with no frames (like `record_start`), so the state, event, end and refusals can be checked on a host |

## Commit plan

Order: the default-off commit `0977dd6` is in the tree. Every commit is checked with `/home/user/build/bin/check_core.sh /home/user/wt/core-work work both tests` (both builds and the 17 host tests: 14 `*_test.cpp` + 3 `*_test.sh`) and `/home/user/build/bin/smoke_core.sh <bin> <port> <out>` diffed against the previous commit (no upstream field missing or retyped). UI commits: `/home/user/build/bin/check_ui.sh`. The Pi check is run with the automatic switch on and the owner's rig (CM5, IMX585, CFexpress, cDNG lossless 4K). Watch the log with `journalctl -u apertar-core -f | grep -E 'storage preroll|phase-lock'`.

### 1. core: every capture entry in the camera refuses a running storage pre-roll

- Repo: Core. `CC`: `enterStandby` `CC:10595`, `setTuningFile` `CC:11502`, `capturePhoto` `CC:12198`, `startTimelapse` `CC:12234` get `if (prerollTake_) { setErrorLocked("Storage pre-roll is running. One moment."); return false; }` right after they take `mutex_`, as `startRecording` has it (`CC:11995`).
- Moves nothing, deletes nothing. About -0 / +16.
- Here: both builds; host tests; smoke diff empty.
- Pi: `curl -s -X POST http://<pi>:8000/api/command -d '{"cmd":"storage_preroll"}'`, then within 2 s `curl -s -X POST http://<pi>:8000/api/command -d '{"cmd":"set_tuning_file","path":"<current file>"}'`. Expect "Storage pre-roll is running. One moment." and later `result=ok` in the log. Today the second command reconfigures under the take.
- Depends on: nothing.

### 2. core: --simulate runs a storage pre-roll without frames

- Repo: Core. `CC::startStoragePreroll`: the `simulateCamera_ || !session_` refusal `CC:12061-12062` becomes the upstream `record_start` shape: in `--simulate` the checks run, the fps stays the operator's, `prerollTake_` and `prerollFps_` are set, no session call. `finishStoragePreroll` `CC:12146`: in `--simulate` it clears the flag and returns a zero result. Outside `--simulate` a missing session still refuses.
- About -2 / +10.
- Here: simulate on a port: `curl -s -X POST http://127.0.0.1:<port>/api/command -d '{"cmd":"storage_preroll"}'`, then poll `/api/state` every 250 ms: `system.storage_preroll_active` is true for about 2 s, then false with `storage_preroll_last` "ok: 2.0 s at N fps, 0 frames, ...". During it, `capture_photo` and `enter_standby` answer with the sentence (commit 1).
- Pi: none (no camera code path changes).
- Depends on: 1.

### 3. core: the idle timer waits while a storage pre-roll runs

- Repo: Core. `wait()` `App:8306-8307`: `storagepreroll::prerollActive()` joins the `isRecording() || timelapseActive() || soundRecordingActive()` list (read through `camera_` from commit 10 on).
- About -0 / +1.
- Here: simulate with `standby_timeout_seconds` 1 in `UI.conf`: a manual pre-roll runs to its end and the log shows no refused `enter_standby` during it; the camera enters Standby about 1 s after it.
- Pi: none beyond the simulate check.
- Depends on: nothing.

### 4. core: the 1 Hz loop ends a storage pre-roll through record_stop

- Repo: Core, App and CC.
- `AppH`: `std::atomic<int64_t> storagePrerollEndMs_{0};`. The worker sets it right after `camera_.startStoragePreroll` succeeds (`App:11271`).
- `wait()`, after the `checkRecordingFailure` block: if `storagepreroll::prerollActive()` and (now >= `storagePrerollEndMs_`, or `camera_.storagePrerollError()` is not empty, or `!mediaGateBypassed() && !mediaSnapshot().mounted()`), build `ControlCommand{"record_stop", -1}` with `fields["storage_preroll_end"]` = `time`, `error` or `media_removed`, and call `handleCommand`.
- `record_stop` `App:14849-14852`: a running pre-roll is finished here: `camera_.finishStoragePreroll()`, the result text and log line moved from `App:11299-11312` ("Media was removed during the pre-roll." when the field says `media_removed` and the recorder reports nothing), singleton `fps`/`active` cleared, `trimMedia("delete")`, reply `"recording":false,"storage_preroll_stopped":true` as today. Then, before the sound and camera stops: `if (command.string("storage_preroll_end")) return okReply(command.id);`, so a late internal stop never ends an operator's take (`App:9139-9143@upstream`).
- Worker: `runStoragePrerollOnce` ends after the start; the 25 ms watch loop and the finish block go (`App:11280-11317`). The start log line keeps `reason=<trigger>`; the end log line says `end=<time|error|media_removed|manual> result=...`.
- `CC::stop()` `CC:10573`: `finishStoragePreroll()` before `stopTimelapse()`. It answers "No storage pre-roll is running." when none runs, so the call needs no check. App's `stopStoragePreroll()` in `App::stop()` stays until commit 6 (it joins the worker).
- The sentence "Both calls are made by Core's storage pre-roll thread only." `CC:12051-12052` becomes "Both are called from handleCommand." The rest of the essay comment goes with the comment sweep (CC-6-F6).
- About -45 / +40.
- Here: simulate: a manual pre-roll ends after 2-3 s (`/api/state`), `last` "ok: ..."; an operator `record_stop` during it ends it early; with no pre-roll running, `record_start`, then `curl ... -d '{"cmd":"record_stop","storage_preroll_end":"time"}'` answers ok and `recording` stays true; `kill -TERM` of the simulate Core during a pre-roll: it exits cleanly and the log shows the finish.
- Pi: a manual pre-roll (log `end=time result=ok`, clip folder gone, `fstrim` line after it). A pre-roll with the card pulled mid-run (log `end=media_removed` or `end=error`, `result=failed`, camera Ready afterwards). `record_stop` from the touch UI during a pre-roll (`end=manual`). `sudo systemctl restart apertar-core` during a pre-roll: no leftover clip folder on the card.
- Depends on: 2 (for the host check).

### 5. core: the storage pre-roll starts through handleCommand like any take

- Repo: Core, App and CC.
- Head of `handleCommand`: `storage_preroll` joins the capture-starter names: playback yield `Recording` `App:12594`, `mediaDeleteActive_` `App:12602-12604`, `mediaWritesPending` `App:12610-12612`, `mediaGateError` `App:12613-12617`, speed-test line `App:12628-12630`, trim/merge wait `App:12632-12636`. New line after the `mediaAction` gate: `if (mediaAction && storagepreroll::prerollActive()) return errorReply(command.id, "Storage pre-roll is running. One moment.");`. The 9-name list `App:12605-12609` is deleted: CC now refuses every capture entry (commit 1, `CC:11995`) and a second start ("already running").
- The sound-only branch of `record_start` gets `if (storagepreroll::prerollActive()) return errorReply(command.id, "Storage pre-roll is running. One moment.");`.
- The `storage_preroll` block: `seconds` parse as today, `if (soundRecordingActive()) return errorReply(..., "Stop recording before a storage pre-roll.")`, `camera_.startStoragePreroll`, `storagePrerollEndMs_`, the singleton `active`/`fps` writes moved from the worker, log `reason=<trigger field, or manual>`, reply as today. A refused manual start answers with CC's sentence; it no longer writes "skipped: ..." into `storage_preroll_last` (the toast carries it, as for every upstream refusal).
- `CC::startStoragePreroll` `CC:12065-12066`: "Camera is not ready." splits into "Stop recording before a storage pre-roll.", "Stop timelapse before a storage pre-roll.", "Wake the camera before a storage pre-roll." (Standby) and "Camera is not ready." (any other state, as `CC:8229-8230@upstream`).
- Worker: `runStoragePrerollOnce` no longer locks `commandMutex_`. After its settle waits it builds `ControlCommand{"storage_preroll", -1, fields trigger, seconds}` and calls `handleCommand`, as the idle timer does; a refusal reply is logged `skipped: <sentence>`. Delete `storagePrerollGuard` `App:11124-11148`, `GuardInputs`/`GuardDecision`/`decideGuard` `SP:128-165` and the guard section of `tools/storage_preroll_test.cpp`.
- About -95 / +25.
- Here: simulate: with still mode on the reply is "Leave Still Mode before a storage pre-roll."; in ProRes "Storage pre-roll writes raw frames (cDNG, Lossy DNG or MLV)."; during a `record_start` take "Stop recording before a storage pre-roll."; in Standby "Wake the camera before a storage pre-roll."; `format_media` and `run_media_speed_test` during a run answer "Storage pre-roll is running. One moment."; smoke diff.
- Pi: the automatic trigger after a card insert still runs (log `reason=mount ... result=ok`); `record_start` pressed on the touch UI during the boot pre-roll shows the sentence.
- Depends on: 4.

### 6. core: the automatic pre-roll is sent by the 1 Hz loop as a command

- Repo: Core. Delete the worker: `runStoragePreroll`, `runStoragePrerollOnce`, `stopStoragePreroll`, `storagePrerollThread_`, `storagePrerollRunning_`, `storagePrerollStop_`, `storagePrerollCv_`, `storagePrerollManual_`, `storagePrerollDelayMs_` (`AppH:284-293`), its start `App:8043-8046` and both stop calls `App:8189`, `App:11060`. Keep `storagePrerollMutex_`, `storagePrerollPending_`, `storagePrerollTrigger_`, `storagePrerollSeconds_`; add `storagePrerollDueMs_`, `storagePrerollRequestMs_`.
- `requestStoragePreroll(trigger)` keeps its switch check and its log line, then stores the request (due = now + 3 s) under `storagePrerollMutex_`. A newer request replaces the older one.
- `wait()`, after the idle-timer block: copy and clear the request under `storagePrerollMutex_` when it is due and (`!mediaTrimPending_ && !mediaTrimWorking_` under `mediaTrimMutex_`, and the camera is Ready or in Standby, or 150 s have passed since the request); release the lock; then `handleCommand(ControlCommand{"storage_preroll", -1, {trigger, seconds}})`. A refusal is logged `storage preroll: reason=<trigger> skipped: <sentence>`.
- The manual command is unchanged by this commit: since commit 5 it starts in its own block.
- About -120 / +35.
- Here: simulate with `[media] preroll=on` in the simulate hardware file: Core start runs one pre-roll about 3-4 s after the first watcher cycle (log line, `/api/state`); a second Core start with `preroll=off` runs none; Core stops cleanly 1 s after start (no pending request blocks it). Host tests.
- Pi: cold boot with the switch on (one `reason=start` pre-roll), card insert (`reason=mount`), `format_media` (`reason=format`, and no extra `mount` one). Time from boot to Ready with the switch off is unchanged.
- Depends on: 5. App-2-F4 (worker styles) shrinks by one worker.

### 7. core: a storage_preroll event announces each pre-roll's start and end

- Repo: Core. App publishes `{"event":"storage_preroll","storage_preroll_active":...,"storage_preroll_fps":...,"storage_preroll_last":"..."}` from the `storage_preroll` block after the start and from the `record_stop` finish, as App publishes the sound take's `recording` event (`App:8394`, `App:8406@upstream`). The event joins the broadcast list in `publishEvent` (shape `App:10829-10838@upstream`), so the HDMI process and every client get it, also when the command came from one socket.
- Additive. About -0 / +12.
- Here: simulate: `socat - UNIX-CONNECT:<sim>/core.sock` stays open while `curl` starts a pre-roll; the socket shows one event with `true` and, 2-3 s later, one with `false` and the last text.
- Pi: none beyond commit 8's.
- Depends on: 4, 5.

### 8. ui: the bridge applies the storage_preroll event

- Repo: UI. `ACB:1327-1328`: `storage_preroll` joins the `standby`/`still_exposure`/`timelapse_progress`/`media_write_state` list that calls `applyCoreState(message)`. `applyCoreState` already passes the message to `applyBufferState` (`ACB:1732`), which reads the three keys. No read moves.
- Harmless before commit 7 (an unknown event is ignored) and needed before commit 9 (the `buffer` event stops carrying the keys; the steady poll is 30 s, `ACB:18`).
- About -0 / +1.
- Here: UI build.
- Pi: during a manual pre-roll the touch screen chip and the HDMI status read PRE-ROLL in blue within 1 s and return to READY after it; the fps readout is italic on both while it runs.
- Depends on: 7 (ships in the same merge, CMD-30).

### 9. core: the pre-roll status is published beside timelapse_active

- Repo: Core. `App`: `storage_preroll_active`, `storage_preroll_fps`, `storage_preroll_last` go after `timelapse_shot_count` in `get_state` `App:12968` and in the `/api/state` status block `App:9472` (member code; still read from the singleton). They leave `bufferSettingMembers` `App:260`, `263-264`, so also `settingsBody`, the three replies, `/api/buffer`, `system` and the `buffer` event. `runBufferEvents` loses its 6 pre-roll diff lines and the `sentPrerollActive` 250 ms tick `App:11007-11053` (`storage_preroll_auto` keeps its line there until storage-settings moves it). `/api/buffer` and the `buffer` event stay lock-free (`App:8422`).
- The WebUI keeps working without a change: `renderSnapshot` reads the top-level keys (`WCP:15391`); the 4 Hz branch `WCP:16500` no longer sees a boolean and does nothing. The pill now follows `/api/state` at 1 Hz (owner's list).
- About -25 / +8.
- Here: smoke diff: the three keys appear top-level in `get_state` and `/api/state`, leave `system`, `/api/buffer` and the `settings` reply; every upstream field unchanged. Headless Chromium against simulate: click Storage pre-roll, the PRE-ROLL pill shows within 1 s and READY returns after the run; the fps badge is italic during it; the Automatic pills still show.
- Pi: the same on the rig's WebUI; touch UI and HDMI as in 8.
- Depends on: 8.

### 10. core: the storage pre-roll's state is kept in CameraController

- Repo: Core. `CCH:226`: `std::atomic<bool> prerollTake_` becomes `bool prerollTake_ = false;` under `mutex_` (every reader already holds it except `storagePrerollError`, which now takes `mutex_` like `recordingError()` `CC:12648-12652`). Reuse `prerollFps_` `CCH:229`. New beside them: `std::string prerollLast_;` and the start time. Public `struct StoragePrerollStatus { bool active = false; double fps = 0; std::string last; };` and `StoragePrerollStatus storagePrerollStatus() const;` under `mutex_`, shaped like `stillExposureStatus()`. `bool storagePrerollActive() const` like `isRecording()`.
- `finishStoragePreroll(const std::string &abortReason)` writes `prerollLast_` ("ok: ..." via `storagepreroll::lastOk`, or "failed: ..."); App passes the media-removed reason and logs from the returned result. A failed start writes "failed: ...". Flag order stays: set after the fps apply `CC:12126`, cleared before the restore `CC:12180`.
- `App`: the singleton reads in `wait()` (commits 3 and 4), the head line, `record_start`, `record_stop`, `get_state`, `/api/state`, the event, `mediaTrimMayRun` `App:11478`, `clipMergeMayRun` `App:11709` read `camera_`. The singleton writes go.
- `SP`: delete `active`, `fps`, `lastMutex`, `last` from `PrerollState`, plus `prerollActive()`, `prerollFps()`, `prerollLast()`, `setPrerollLast()`. Keep `automatic`/`automaticFromEnv` for storage-settings. `tools/storage_preroll_test.cpp` loses the checks of the deleted functions.
- About -50 / +35.
- Here: builds; host tests; smoke diff empty (same keys, same types); simulate run as in 4.
- Pi: one manual pre-roll: WebUI pill, touch chip and `storage_preroll_last` as before.
- Depends on: 9.

### 11. web: the PRE-ROLL pill is drawn by renderSnapshot alone

- Repo: Core (`WCP`). Delete the pre-roll branch of the `/api/buffer` handler `WCP:16500-16515`, `applyPrerollPill` `WCP:16441-16456`, `notePrerollRequested` `WCP:16435-16439` and its call `WCP:19898`, `prerollPollWanted` `WCP:16426-16428` and its two uses, `frameBufferBar.preroll*` `WCP:16421`, `WCP:16554`, and the second pill writer `WCP:15758-15763`. The pill and fps italics come from `renderSnapshot` (`WCP:15391`, `WCP:8682-8705`). The `storage_preroll_` prefix stays in the `system` copy loop `WCP:15219` until storage-settings moves the `_auto` keys out of `system`. The toast gets its period: "Storage pre-roll started."
- About -45 / +3.
- Here: headless Chromium against simulate as in 9; the 4 Hz timer runs only for the buffer bar option.
- Pi: the rig's WebUI as in 9.
- Depends on: 9; the webui-state theme does the rest of the 4 Hz loop.

### 12. core: the storage pre-roll runs at the mode's recordable maximum fps (held: owner decision 1)

- Not in the series until the owner answers decision 1. Under option B: `CC::startStoragePreroll` targets `maximumFpsForSettings(settings_, family)`; delete `prerollMaximumFps` `CC:3481-3491`, `setPrerollFps` and its 4 calls (`CC:7507`, `CC:12086`, `CC:12092`, `CC:12179`), `prerollFpsOverride_`, `prerollPinUs_`, the override in `applyControls` `CC:7576-7578` and the pin in `requeueRequest` `CC:9076-9081`; the phase-lock `enabled` condition `CC:8905` gains `&& !prerollMeasuring_.load()`. The 1 s period wait stays (under both locks, only on a pre-roll start). Under option A the fps change, the period wait, `prerollSaved_`, the `commit` parameter and `storage_preroll_fps` go instead (about -120). Under option C the CC-4-F3 rework (a pre-roll input to `sanitizeSettingsForSensor`) is the commit.
- About -40 / +4 (option B).
- Here: both builds (the `#if` branches); fps-ceiling host test.
- Pi: a manual pre-roll in 4K lossless cDNG and in 12-bit uncompressed. Log `requested_fps` equals `fps_max` with the mode ladder off and `fps_take_max` with it on (the ladder overwrites `fps_max` with its ceiling over all rungs `CC:10920`; the running rung's ceiling is `fps_take_max` `CC:10926`); `measured_fps` within 1 % of `requested_fps`; no `phase-lock` push lines during the run; the operator's `fps` back afterwards (`get_state`). If `measured_fps` stays at the old rate, the per-request pin was load-bearing: stop and report.
- Depends on: 10; owner decision 1; the camera-modes theme (lossless limits and fps ceilings decide what `maximumFpsForSettings` returns).

### 13. core, web: the manual pre-roll command is storage_preroll_start

- Repo: Core, in the same merge as 14. Rename in the block, the head lists, `help`, the 1 Hz command builder and `WCP` `requestStoragePreroll` `WCP:19897`. `record_stop` keeps ending it (pairs like `timelapse_start`/`timelapse_stop`, `record_start`/`record_stop`).
- About -6 / +6.
- Here: simulate: `storage_preroll_start` works; `storage_preroll` answers "Unknown command".
- Pi: touch tile after 14.
- Depends on: 11; owner decision 2.

### 14. ui: the Storage Pre-roll tile sends storage_preroll_start

- Repo: UI. `ACB:621`. About -1 / +1.
- Here: UI build.
- Pi: tap the tile; log `reason=manual result=ok`.
- Depends on: 13 (merge together, CMD-30).

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| A raw take that is written and deleted | CC `startStoragePreroll`/`finishStoragePreroll`/`storagePrerollStatus`, both called only from `handleCommand` | It is camera work, so CC owns it; its start and end are commands like every take's (CMD-1) |
| A take hidden from REC and tally (`recording_` false, no `recording` event, safety stop off, drop warning muted) | One flag (`prerollTake_`) that every CC capture entry refuses on, plus the session's per-take `setPrerollTake` | The owner wants no REC and no tally. A real `recording_` take would fire the tally output (`handleTriggerEvent`) and the REC UI |
| Runs that start without an operator (Core start, card insert, format) | Off by default (`0977dd6`); a switch whose storage the storage-settings theme decides; sent from `wait()` as a `ControlCommand` with an internal `trigger` field | `wait()` + `idle_timeout` is the upstream way for Core to act by itself. Off by default because upstream never writes to media without an operator action (`App:9095-9117@upstream`) and the benefit is unmeasured (`working/dng-chain-answer.md:175-186`) |
| A take ended by the 1 Hz loop | `record_stop` with the internal `storage_preroll_end` field, re-checked under the lock | The nearest upstream shapes: the idle timer's `enter_standby` and its `idle_timeout` re-check |
| Settings changed without save or event during the take (`applySettingsLocked(..., commit=false)`, `prerollSaved_`) | Kept for the fps change only | The fps change must not be saved or reach the settings event. Goes away with option A of decision 1 |
| `storage_preroll_last` result text and the measured fps (frame timestamps) | One string in CC, published like `photo_write_error` | It is the only report of what the pre-roll did. Upstream's speed test reports its result the same way (`mediaSpeedLastWriteSpeedMBps_`, `App:10608-10614@upstream`) |
| `[media] preroll_seconds` and the `seconds` argument | Unchanged, 1-10 s | Storage of the key: storage-settings theme |

## For the owner

| # | Question | Options | Recommendation and cost |
| --- | --- | --- | --- |
| 1 | At which fps does the pre-roll write? | A: the operator's own settings (no fps change). B: the highest recordable fps of the mode, through the sanitiser (commit 12). C: the sensor's maximum past the lossless cap and the ladder, as today, carried as a pre-roll input of `sanitizeSettingsForSensor` | Until you answer, today's rate stays and commit 12 waits. **B** removes the bypass and keeps the fps within what the mode records. Cost: the rig's 4K lossless cDNG pre-roll runs at the lossless cap instead of the sensor maximum (`CC:3486-3491` vs `CC:3495-3500`), with no setting to get today's rate back. **A after the KB's E7 A/B** (`working/drop-frames/README.md:330-345`; its WARM arm is a take at the operator's settings): deletes another ~120 lines and the three italic-fps displays, and the 60 fps run that drops frames in 12-bit uncompressed (`dng-chain-answer.md:183`) goes away. **C** keeps today's rate as a sanitiser input: a second ceiling rule in the sanitiser |
| 2 | Rename `storage_preroll` to `storage_preroll_start`? | Rename (commits 13, 14) / keep | Rename: actions are `<noun>_<verb>` (CMD-7) and it pairs with `record_stop`. Cost: both clients change in one merge. **Confirmed** that nothing else sends it: no hardware action names it (`src/hardware/ActionCatalog.hpp` has no pre-roll entry); only `App`, `WCP` and `ACB` contain the name |
| 3 | While a pre-roll runs, may exposure, white balance and focus change, as during a real take? | Keep the refusal of every setter (`CC:12747`) / allow the CAM-31 set | Keep: the run is 2-3 s and the settings are restored from a copy at its end, so a change made during it would be lost. Cost: a dial turned during the boot pre-roll shows the sentence once |
| 4 | Keep the format trigger's own request and its 15 s quiet window (`SP:175-198`, `App:14638-14647`)? | Keep / let the format's remount count as a card insert | Keep for now: whether the watcher sees the format's unmount is not determined here (see Risks). Cost: 2 atomics and a scope struct stay |
| 5 | The run ends on the 1 Hz loop: 2-3 s instead of 2.0 s | Accept / a shorter `wait()` tick while a pre-roll runs | Accept: `storage_preroll_last` reports the real length, and the extra second is up to one more second of raw writing. Cost: up to 50 % more data written per run (about 0.35-0.7 GB more at 4K) |
| 6 | Refused manual start: CC's sentence per cause, no "skipped: ..." line in the card's last-result text | Accept / keep writing "skipped: ..." | Accept: every upstream refusal reaches the operator as the reply sentence (toast). Cost: the last-result line keeps the previous run's result |
| 7 | WebUI PRE-ROLL pill at 1 Hz | Accept / keep the 4 Hz `/api/buffer` path for the pre-roll | Accept: one writer, upstream's 1 Hz state poll. Cost: the pill can appear up to 1 s late on a 2-3 s run |

## Risks and what was not determined

- **The per-request pin (commit 12).** The port pins `{p, p}` on every request "so the take cannot fall back to an older limit" (`CC:9076`). Whether the IMX585 on the qbc libcamera reaches the new period without it is not determined. The Pi check in 12 settles it. If it fails, commits 1-11 and 13-14 land without 12.
- **Drain under the command lock.** After commit 4 the finish (stop, sync, delete, restore) runs under `commandMutex_` and `mutex_`, as upstream's `record_stop` drain does. A command sent meanwhile waits. For a 2-3 s raw take on CFexpress the drain length is **unconfirmed**. Pi: `time curl -s -X POST http://<pi>:8000/api/command -d '{"cmd":"get_state"}'` sent right after the pre-roll's end log line; note the time in the fix log. `/api/state` and `/api/buffer` do not take `commandMutex_` (`App:8422-8436`); `/api/state` takes `mutex_` through `camera_` reads, as it does during a take's drain.
- **The manual start's period wait.** The manual `storage_preroll` now answers after `startStoragePreroll`, which waits up to 1 s for the new frame period under both locks (`CC:12111`). The touch UI and the WebUI send it fire-and-forget (`ACB:621`, `WCP:19897`); a 1 s reply is within their command timeouts (**probable**; the WebUI `sendCommand` has no short timeout, not traced in `ACB`). Option A of decision 1 removes the wait.
- **Card pulled mid-run.** `wait()` keeps the port's mount check and also ends on a latched recorder error. Whether `finishStoragePreroll` with `mediumGone` returns within a second on a pulled CFexpress card is **unconfirmed**; the Pi step in 4 checks it.
- **Format remount.** Whether `format_media` produces a watcher-visible unmount, which would make the format's own request redundant, was not determined (decision 4).
- **The `fps` field during the run.** `settings()` returns the pre-roll fps while it runs (`CC:12579-12582`); the touch UI shows it as the fps value. That it shows it italic and not as the operator's value comes from `CameraPage.qml:3057-3059`; whether the 30 s poll can land between the end and the restore is **unconfirmed**. Option A of decision 1 removes the question.
- **Other Pi models.** No fps path here has a board cap: `Caps`/`recording_capabilities` decide formats, not fps (`include/apertar/core/RecordingCapabilities.hpp:11-21`), so neither today's sensor maximum nor option B's `maximumFpsForSettings` is lowered on a Pi 4 / CM4. The pre-roll checks only that the format is raw, which the board already allows. Whether a Pi 4 keeps up with a 2-3 s raw take at the mode maximum is unrun. Pi step: on a Pi 4 with the automatic switch off, a manual pre-roll in cDNG; the log shows `result=ok` and `dropped` absent or small, and the camera is Ready afterwards. The command and lock changes of commits 1-11 have no board dependence.
- **Overlapping themes.** The switch and `[media]` keys, `set_storage_preroll`, `storage_preroll_auto/_auto_env` and `bufferSettingMembers` belong to storage-settings; commit 9 must be rebased on what it does to `bufferSettingMembers`, and commit 11 keeps the `storage_preroll_` prefix until it moves the `_auto` keys. The 4 Hz loop belongs to webui-state. The card placement and the `*Known` latch belong to touch-ui. The fps ceilings belong to camera-modes. The command plane's error codes (`errorReplyBody`) may change the refusal replies' shape: command-plane.

## Findings covered

| Finding | Commit |
| --- | --- |
| App-4-F2 | 4 (end through `handleCommand`), 5 (start through `handleCommand`, guard copy deleted), 6 (worker deleted) |
| App-4-F4 | done in `0977dd6` (default off); the automatic triggers stay as new ground |
| CC-4-F3 | 12, held for owner decision 1 |
| CC-6-F3 | 1 (setTuningFile, enterStandby, capturePhoto, startTimelapse), 5 (App list deleted), 10 (one CC state); the 1 s wait under `mutex_` follows decision 1 (12) |
| X-knobs-3 | done in `0977dd6`; the env twin `APERTAR_STORAGE_PREROLL` goes with storage-settings |
| X-stock-behaviour-5 | done in `0977dd6`; 5 makes the refusals come from CC |
| Media-buffer-split-F6 | pre-roll half done in `0977dd6`; trim half: not covered (storage-settings / media trim) |
| CC-6-F8 | 10 (plain `bool` under `mutex_`, `storagePrerollError` locks) |
| CC-6-F6 | 4 (the sentence that becomes false); the rest of the essay comment and the T34 line: the comment sweep |
| App-5-F8 | 4 (`record_stop` branch kept, now finishing the pre-roll), 13, 14 (rename) |
| App-4-F12 | 5 deletes `storagePrerollGuard`; the other four predicates: not covered |
| App-2-F4 | 6 removes one worker; the rest: not covered |
| WCP-08-F2 | 11 (pre-roll half); safety-stop pill and timer half: webui-state |
| WCP-10-F13 | 11 |
| WCP-07-F3 | 9 for the three pre-roll fields; the buffer fields: storage-settings |
| App-1-F1, X-state-consistency-7 | 9 for the three pre-roll keys (they leave `settingsBody`); the rest: storage-settings |
| App-5-F2, WCP-07-F8 | not covered: switch shape, storage-settings |
| UI-control-bridge-F9, UI-settings-qml-F5 | not covered: touch-ui (the `*Known` latch, the card of its own) |
| X-commits-core-2-1 | not covered: commit-history work (d44b177 squash) |

## What the challenge changed

| Point | Decision | Why |
| --- | --- | --- |
| a. Time-lapse as the precedent for a CC clock thread | Challenger right. CC thread dropped | `timelapseLoop` only queues stills (`CC:8475-8483@upstream`) and never stops a take or calls `applySettingsLocked`; the pre-roll finish does both (`CC:12178-12193`) |
| a. Self-ending worker must join before restart | Challenger right; moot | With no CC thread there is nothing to join. Upstream's shape is `joinMediaSpeedTest` `App:8968@upstream` |
| a. End through the 1 Hz loop | Challenger right, adopted with one addition | `wait()` already calls `handleCommand` (`App:8289-8320`). Added: the internal `storage_preroll_end` field, re-checked under the lock, so a `record_stop` that waited for the lock never ends an operator's take (`App:9139-9143@upstream`) |
| a. Status struct precedent | Challenger right | `stillExposureStatus()` `CCH:22-25`, `CC:8548-8552@upstream` |
| b. `bufferSettingMembers` is a free function | Challenger right on the defect, partly wrong on the fix | `App:252` has no `camera_`. Writing the keys into `/api/buffer` and the `buffer` event from member code would make those lock-free paths (`App:8422`) take `mutex_` and stall the buffer bar during every drain. The keys leave them; the new event carries the changes (commits 7, 9) |
| b. Duplicate `prerollFps_` | Challenger right | `CCH:229` exists; reused |
| b. New `prerollMutex_` | Challenger right | Every CC reader of `prerollTake_` already holds `mutex_` except `storagePrerollError` `CC:12133-12139`; that one now locks. No new lock, no lock-order risk |
| b. Flag order in start and finish | Challenger right | Apply at `CC:12103` before the flag at `CC:12126`; flag cleared at `CC:12180` before the restore at `CC:12188`; `applySettingsLocked` refuses while it is set `CC:12747`. Today's order is kept and stated in commit 10 |
| b. Idle timer | Challenger right | `App:8306-8310` lacks the pre-roll; commit 3 |
| b. Touch UI and HDMI already show PRE-ROLL | Challenger right | `StatusChip.qml:60`, `ExternalMonitorWindow.qml:198`, `CameraPage.qml:2708`. Old decision 4 removed; Pi checks of 8 and 9 check both chips |
| b. Touch UI event path is one line | Challenger right | `applyCoreState` calls `applyBufferState` `ACB:1732`; commit 8 is one line and lands before commit 9 |
| b. `storage_preroll_` prefix in the `system` copy loop | Challenger right | `_auto` keys stay under `system` (`App:261-262`, `App:9591`); the Automatic row needs a boolean `WCP:15836`. Prefix kept (commit 11) |
| b. Pulled-card check | Challenger right | It is the only end condition independent of the recorder (`App:11292-11295`); kept as a `wait()` condition |
| c. Refusal sentences | Challenger mostly right | Per cause in the CAM-32 form, "Wake the camera ..." as `App:9211@upstream`; "Camera is not ready." stays for the other states, as upstream `startRecording` keeps it (`CC:8229-8230@upstream`). The dropped "skipped:" line is decision 6 |
| c. Rig fps | Challenger right | Commit 12 removes today's rate with no setting (`CC:3486-3491` vs `CC:3495-3500`); held for decision 1 |
| c. `fps_max` is the ladder ceiling | Challenger right | `CC:10920`, `CC:10926`; commit 12's Pi check compares with `fps_max` (ladder off) or `fps_take_max` (ladder on) |
| d. Old commit 3 held several ideas | Challenger right | Split into 2 (`--simulate`), 4 (the end); the essay comment goes to the comment sweep except the one sentence commit 4 makes false |
| d. State and publishing in one commit | Challenger partly right | One move of the keys, but in two commits (9 publishes from member code, 10 moves the state into CC), each under ten minutes of reading |
| d. Old commit 7 (period wait outside the lock) | Challenger right | Dropped; follows decision 1 |
| e. Who emits the event | Changed from the challenge | Start and end both sit in `handleCommand` branches, so App publishes it, as for the sound take (`App:8394`, `App:8406@upstream`); CC stays without event code for the pre-roll |
| e. Media actions during a run | Changed from both | A head line with "Storage pre-roll is running. One moment." instead of joining the "Stop recording, still captures and media tests ..." list: the run ends by itself, so the sentence says to wait (CMD-4: each guard its own sentence) |
| f. Hidden decisions | Challenger right | Decisions 5, 6, 7 added; decision 2 is **confirmed** to touch only the two clients |
| g. Pi check of commit 1 | Challenger right | The field is `path` (`App:13143-13145`) |
| g. Pi check of old commit 7 | Moot | Old 7 dropped; the drain and period-wait latency checks are in Risks |
| g. Pi checks of 8 and 9 | Challenger right | Chip checks added |
| Host checks | Both right | 15 `*_test.cpp` files, of which `check_core.sh` skips `dng_payload_write_test`, plus 3 `*_test.sh`: 17 tests |

## Checked against the owner's recorded decisions

Read 2026-11-17 against `owner-recorded-decisions-a.md` (DA-*) and `owner-recorded-decisions-b.md` (DB-*), plus a KB search for the pre-roll outside `merge-review/` (`working/drop-frames/README.md:82`, `:313-345`; `lessons/hardware-log.md:842-855`, `:354-355`; `working/drop-frames/nvme-campaign/plan.md:102`, `:231`, `:246`, `:307`; `working/dng-chain-answer.md:173-186`; `working/dual-sensor/design-dual-sensor.md:133`, `:216`, `:965`) and the KB's scripts (`working/tools/longtakes.py`, `working/tools/storage_facts.sh`, `working/tools/drop-frames-2026-11-01/e3-unit.sh`, `.../takes_from_journal.py`). Neither collection has a row on the pre-roll itself. What the KB holds instead: the owner confirmed the pre-roll at the sensor maximum on the camera (`hardware-log.md:842-855`, "Confirmed by: the owner"), his campaigns run it "ON as in real use" (`nvme-campaign/plan.md:231`, `:307`; DB-71 "as in real life"), and his campaign runner uses the manual pre-roll as the encoder's capacity reading (`longtakes.py:3194-3205`, plan `:246`). Code facts below read at Core `/home/user/wt/core-work` `7f188a5` (pre-roll code unchanged since `0d13a6f`).

| commit | touches decision (id, his words) | verdict | what changes in the commit |
| --- | --- | --- | --- |
| `0977dd6` (in the tree) default off | Real use runs the automatic pre-roll on: "the pre-roll stays ON as in real use (it runs once per Core start)" (`nvme-campaign/plan.md:231`, `:307`); DB-71 tests "as in real life". The template wrote `# preroll=on` commented out (`git show 0977dd6`, `App:5073`), so a rig file made from it has no key and now falls to off | fine for stock (1.6.0 has no pre-roll); **his rig changes by itself** | No code change. The fix log and the owner page say: on his camera send `set_storage_preroll value=on` once (`App:12928-12934`) or put `preroll=on` under `[media]`. Without it `longtakes.py:2766` voids every take (`storage_preroll_auto` is not True) and `e3-unit.sh:19-20` waits 10 min for `storage preroll: reason=start.*result=` and stops with NOT STARTED |
| 1 capture entries refuse | DB-101 "tuning automatic" (his choice of tuning); DA-31/DA-36 switch "position applied at Core start" | fine | None. Refusal lasts 2-3 s; his rig has no switches (DA-27 table, `[gpio_switches]` absent) |
| 2 `--simulate` | none | fine | None |
| 3 idle timer | DA-57 keep awake while a clip plays (same `wait()` reset list) | fine | None |
| 4 end through `record_stop` | His scripts parse ONE journal line per run: `storage preroll: reason=<trigger> fps= measured_fps= seconds= frames= bytes= result= ms=` (`App:11230-11233`). `e3-unit.sh:19-21` greps `reason=start.*result=` and `result=[a-z]+ ms=[0-9]+`; `takes_from_journal.py:61-62` marks the clip before any `storage preroll: reason` line as the pre-roll | conflict (scripts) | The end line keeps today's text and field order, with `end=<time\|error\|media_removed\|manual>` added after `ms=` (so `result=[a-z]+ ms=[0-9]+` still matches). `ms=` counts from the request as today. No start line that begins `storage preroll: reason`; if a start line is wanted it reads `storage preroll started: trigger=<t> fps=<f>` |
| 4 Pi checks | CFE hat: "a Pi 5 cannot hot-plug the CFE NVMe: a re-inserted card needs a PCIe remove/rescan (remount) or a reboot" (`hardware-log.md:354-355`); "never send format_media, eject_media ... to a Core under test"; the drive is his (DA rules, `dual-sensor/HANDOFF.md:273-277`); he runs every `sudo` | conflict (his camera) | The card-pull step is optional, his call, on the Samsung T7 USB SSD if he wants it (`hardware-log` lists it among his media), not on the CFexpress card. `sudo systemctl restart apertar-core` is a command block for him to run |
| 5 start through `handleCommand` | DA-66 "Deleting media. One moment." (the head gate the plan reuses); DB-61 record during a safety-stop flush (untouched: the safety stop is off for a pre-roll, `CC:5509`) | fine | None. Refusal replies stay `ok:false` + `error`, which `longtakes.py:3198-3199` reads |
| 5, 6 Pi checks "card insert", `format_media` | as row 4: insert needs a PCIe rescan on his rig; formatting is his | conflict (his camera) | `reason=mount`: use his remount commands (as step 0b planned, `drop-frames/README.md:328`, "remount (Patrik)"). `reason=format`: only if he formats; otherwise the `--simulate` check of 6 stands for it |
| 6 automatic start from `wait()` | Trim before pre-roll and a trim after every pre-roll delete (`dng-chain-answer.md:182`, kept by DB-65 "trim with a switch default on"); dual-sensor plan holds "trim and Start pre-roll" while cam1 is unknown (`design-dual-sensor.md:245`, `:517`; plan, not answered, DA-85) | fine | Keep the trim-idle wait in the `wait()` condition and the `trimMedia("delete")` in commit 4. Name the 150 s bound in the dual-sensor page (it replaces "up to 2 min") |
| 7 event | none | fine | None |
| 8 UI bridge | DA-77 "Patrik's Pi has no touch screen, only the WebUI in a browser and the HDMI output" | fine; Pi check changes | Pi step: the touch UI's chip as drawn on the HDMI output (the touch UI runs there) and the HDMI monitor status |
| 9 status keys beside `timelapse_active` | His runner reads `storage_preroll_active`, `_last`, `_auto` top-level from socket `get_state` (`longtakes.py:464`, `:2766`, `:3202-3204`, `:3907`; `storage_facts.sh:26`); `storage_preroll_last` parsed by `measured ([\d.]+)` | fine, with one condition | The three keys stay top-level in `get_state` (the plan does this). `storage_preroll_auto` must stay in `get_state` wherever storage-settings moves it, or the runner voids every take. `lastOk` text unchanged (commit 10) |
| 10 state in CC | same text contract | fine | `storagepreroll::lastOk` stays the only writer of the "ok: ... (measured N)" text |
| 11 WebUI pill | DA-98/DB-33 "system-decided values in italics" (the italic fps readout) | fine | None: italics kept |
| 12 fps (held) | The pre-roll at the sensor maximum was built and confirmed by him on the camera (`hardware-log.md:842-855`); DB-52 "asked for the fps max to be read from the sensor"; DA-94 no `[camera] max_fps`; his runner uses the pre-roll as the encoder's capacity reading per arm (`longtakes.py:3194-3205`, `:3257-3268`, `nvme-campaign/plan.md:102`, `:246`) | needs his answer (decision 1) | Option A breaks the capacity reading (the pre-roll would run at the arm's own fps). Option B keeps it on the IMX585: the lossless ceiling there is the mode maximum (`FpsCeiling.hpp:42`, `CC:3148`), so B differs from today only by the ladder and speed-ramp ceilings, which the runner switches off. Also tell the dual-sensor page: its `{p, p+1}` pre-roll pin (`design-dual-sensor.md:965`) has no pin to change under A or B |
| 13 rename to `storage_preroll_start` | His runner sends `core('storage_preroll', seconds=5)` over the socket (`longtakes.py:3197`); the KB's open items name the command (`drop-frames/README.md:149-150`) | conflict (script) | The plan's "Confirmed that nothing else sends it" (decision 2) is wrong. Upstream has no command aliases (`handleCommand@upstream` has none). Smallest variant: keep `storage_preroll` (decision 2 = keep; commits 13, 14 dropped). If he wants the rename: the same merge changes `longtakes.py:3197`, and he says so |
| 14 UI tile | DA-77 | follows 13 | Dropped with 13. If kept: the Pi step is a mouse click on the tile on the HDMI output, not a tap |
| Risks: Pi 4 run | His camera is a CM5 (DA facts table); no Pi 4 in the KB | fine | The Pi 4 step is "not run" until a Pi 4 exists; it is not a step for his rig |
| Findings X-knobs-3 (env twin goes with storage-settings) | DA-84 dual-sensor secondary runs with `APERTAR_STORAGE_PREROLL=0` (`design-dual-sensor.md:133`, `:216`, `:1042`); DB-91 "each behind its env knob or setting" | needs his answer (storage-settings theme) | Keep `APERTAR_STORAGE_PREROLL` read in `automaticEnabled` (`SP:92-99`). With default off it changes nothing on a stock camera; upstream reads env knobs the same way (`LossyDngEncoder.cpp:325@upstream` `APERTAR_LOSSYDNG_ASYNCWRITE`) |
| Decision 3 (setters refused while it runs) | DA-11 the rig's knobs iso, shutter, wb, fps | fine | None: a knob turned in the boot pre-roll shows the sentence once (already in the cost) |
| Decisions 5, 6, 7 | `longtakes.py` reads only the measured fps and `_active` | fine | None |

Note on row 4: the end line is `... result=<r> ms=<n> end=<e>` (the `end=` field goes after `ms=`, before the optional `dropped=` and `note=`), so both greps in `e3-unit.sh` keep matching.

### Decisions this plan must keep

- Default off for the automatic pre-roll (stock = 1.6.0), and his rig switched on by one command he sends (`set_storage_preroll value=on`), recorded in the fix log and the owner page. His campaigns run it on.
- One journal line per run, beginning `ApertarCore storage preroll: reason=<trigger>`, with today's fields in today's order, `result=<word> ms=<n>` adjacent; no other line with that prefix before the pre-roll's clip line.
- The `storage_preroll` command name, its `seconds` argument (1-10) and its `ok`/`error` reply shape (his runner sends it).
- `storage_preroll_active`, `storage_preroll_last`, `storage_preroll_auto` top-level in socket `get_state`; the `last` text "ok: <s> s at <f> fps (measured <m>), <n> frames, <g> GB written and deleted" from `lastOk`.
- The pre-roll's fps stays what he confirmed (sensor maximum) until he answers decision 1; under any answer the measured fps comes from sensor timestamps (`hardware-log.md:851-852` lesson).
- Trim before an automatic pre-roll and a trim after every pre-roll delete (DB-65).
- `APERTAR_STORAGE_PREROLL=0|1` keeps working (DA-84), whatever storage-settings does with the file key.
- Italic fps readout while it runs (DA-98).
- Pi steps fit his camera: no touch screen (DA-77), CFexpress card is not hot-pluggable (`hardware-log.md:354-355`), formatting and `sudo` are his.

### Open questions a recorded decision already answers

| Question | Decision | Answer |
| --- | --- | --- |
| 2: rename `storage_preroll` to `storage_preroll_start`? | His campaign runner `longtakes.py:3197` sends `storage_preroll`; DB-92 "least intrusive change" | Keep the name; drop commits 13 and 14 unless he asks for the rename and the runner change together |
| 1: which fps? (partly) | `hardware-log.md:842-855` (sensor maximum confirmed by him); DB-52; his runner's capacity reading | Not option A while his campaigns use the pre-roll as the capacity reading. B or C stays his choice |
| Is the automatic pre-roll off on his camera after `0977dd6`? | "ON as in real use" (`nvme-campaign/plan.md:231`) | Yes, unless his file has `preroll=on`; he turns it on with one command |
| Does the env switch go? (X-knobs-3) | DA-84 (dual-sensor secondary), DB-91 | Keep it |
| Should the Pi checks tap the touch tile or pull the card? | DA-77; `hardware-log.md:354-355`; drive and format rules | No: HDMI with a mouse; remount by his commands; card pull optional on the T7 |
