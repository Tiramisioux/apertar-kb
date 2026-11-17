# The automatic storage pre-roll: design

Read at: Core `/home/user/wt/core-work` `work/improve` `3650027` (port `01f170c` + 9 fixes, among them `0977dd6` "core: the automatic storage pre-roll is off by default"), UI `/home/user/wt/ui-work` `work/improve` `ac1fc28`; measuring stick `upstream-1.6.0` (`/home/user/wt/core-upstream` `35dbe67`, `/home/user/wt/ui-upstream` `43888e5`). Line numbers below are `@work` unless marked `@upstream`.

## In short

- Today the pre-roll (a 2 s raw take written through the real write path and deleted, to "warm" the drive) is run by an App worker thread that copies the command lock and the busy guards by hand, starts the take beside `handleCommand`, times it, and stops it with no command lock.
- The take is a hidden second take kind in `CameraController` (CC): `recording_` stays false, its fps is pushed past the sanitiser and re-pinned on every request, and its exclusions are split between CC (3 entries) and an App list of 9 command names. `set_tuning_file` and `enter_standby` slip past CC.
- Its state is a header singleton (`storagepreroll::prerollState()`) published inside the camera settings serialiser and the buffer event.
- Target: shaped like time-lapse. CC owns the take, its clock (a CC thread, like `timelapseLoop`) and its state group. Every CC capture entry refuses it. It starts only through `handleCommand`. The automatic triggers become a `ControlCommand` that the 1 Hz `wait()` loop sends, the way the idle timer sends `enter_standby`. The fps comes from the sanitiser.
- Status is published beside `timelapse_active` and in a `storage_preroll` event. Operators see what they see today: the blue PRE-ROLL pill in the WebUI, the italic fps readout on all three screens, and the refusal sentence.
- The automatic pre-roll is already off by default (`0977dd6`). Where its switch is stored belongs to the storage-settings theme.
- 9 Core commits and 2 UI commits. Core loses about 450 lines and gains about 220.

## How it works in the port today

Short names: `App` = `src/ApertarCoreApp.cpp`, `AppH` = its header, `CC`/`CCH` = `src/camera/CameraController.{cpp,hpp}`, `SP` = `src/util/StoragePreroll.hpp`, `WCP` = `src/web/WebControlPage.cpp`, `ACB` = `Apertar-UI/src/ApertarControlBridge.cpp`.

| Value or path | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| Automatic switch `[media] preroll`, `preroll_seconds` | `set_storage_preroll` via the hardware store `App:12917-12944`; the operator by hand | `requestStoragePreroll` parses the file at each request `App:11156-11158`; `refreshBufferRequest` publishes it as atomics `App:278-279`, `SP:240-245` | command thread under `commandMutex_`; the media watcher, no lock | `apertar-hardware.conf [media]` (template `App:5071-5076`); env `APERTAR_STORAGE_PREROLL` beats it `SP:92-99` | WebUI Automatic pills `WCP:15834-15855`; touch UI On/Off `SP.qml:5611-5636`. **The storage-settings theme owns this row** |
| Trigger: Core start, card insert | media watcher `App:10950-10964` (pure decision `SP:185-198`) | the request queue | media watcher thread, no lock | none | none |
| Trigger: format | `format_media` block `App:14635-14651` (`FormatScope` sets `storagePrerollFormatRunning_`/`DoneMs_` `AppH:171-172`) | the request queue and the mount decision | command thread, `commandMutex_` | none | none |
| Trigger: manual `storage_preroll` | WebUI button `WCP:19895-19902`, touch UI tile `ACB:618-622` | `App:14619-14633`: own guard copy, then a request; reply `storage_preroll_started` | command thread, `commandMutex_` | none | toast "Storage pre-roll started" (no period) |
| Request queue: pending, manual, trigger, seconds, delay (3 s for automatic) | `requestStoragePreroll` `App:11152-11174` | `runStoragePreroll` `App:11188-11210` | `storagePrerollMutex_` + cv `AppH:282-293`; the thread is started in `start()` `App:8043-8046` and stopped twice (`App:8189`, `App:11060`) | none | none |
| Settle waits: trim done (up to 2 min), camera Ready (up to 30 s) | - | `runStoragePrerollOnce` `App:11235-11251`, polling every 200 ms | the pre-roll thread, `mediaTrimMutex_` briefly | none | none |
| Busy guard (13 inputs) | `storagePrerollGuard` fills `GuardInputs` `App:11125-11148` | `decideGuard` `SP:128-165` | the pre-roll thread **takes `commandMutex_` itself** `App:11256-11279` and runs `checkRecordingFailure`, the playback yield and `waitForMediaTrim` by hand | none | manual: refusal "Storage pre-roll cannot run now: <reason>." and `storage_preroll_last` "skipped: ..." |
| Take start | `camera_.startStoragePreroll` `CC:12053-12130` | - | pre-roll thread under `commandMutex_` + CC `mutex_`; waits up to 1 s **with `mutex_` held** in `waitForFramePeriod` `CC:12111`, `CC:7852-7874` | none | - |
| Pre-roll fps | `prerollMaximumFps` (sensor max, past the lossless cap, ladder and ramp limits) `CC:3481-3491` | `setPrerollFps` `CC:7841-7848` -> override after the sanitiser `CC:7576-7578` and a `{p,p}` FrameDurationLimits on **every request** `CC:9076-9081`; reset on reconfigure `CC:7507` | session atomics, read on the libcamera thread | none | WebUI fps badge and pills italic with the pre-roll fps `WCP:8680-8705`; touch UI `CameraPage.qml:3057-3059`, HDMI `ExternalMonitorWindow.qml:95-99` |
| `settings_` during the take | `applySettingsLocked(next, false, commit=false)` `CC:12103`; restored from `prerollSaved_` `CC:12183-12194` | `settings()` `CC:12579` -> `get_state` `fps` | CC `mutex_`; the `commit` parameter `CCH:178` exists only for the pre-roll | not saved, no `settings` event | `get_state` `fps` reads the pre-roll fps for the run (**probable**: the touch UI poll `ACB:990-1005` passes it to its fps value) |
| Take kind flags | `prerollTake_` (atomic) `CCH:226`; session `setPrerollTake` `CC:7824-7838` (safety stop off `CC:5509`, drop warning muted, no frames-per-folder split `CC:4292`) | CC entries | CC `mutex_` except `storagePrerollError` (no lock) `CC:12133-12139` | none | no REC, no tally, no `recording` event |
| Exclusions | CC: `startRecording` `CC:11995`, `applySettingsLocked` `CC:12747`, `setClipNameTemplate` `CC:11840`; App: 9 names `App:12605-12609`; trim/merge predicates `App:11478`, `App:11709` | - | - | - | "Storage pre-roll is running. One moment." **Missing:** CC `enterStandby` `CC:10595-10603`, `setTuningFile` `CC:11502-11516` (not in App's list either), `capturePhoto` `CC:12198-12203`, `startTimelapse` `CC:12234-12252` |
| Length and stop | `runStoragePrerollOnce` polls every 25 ms: clock, `storagePrerollError()`, medium mounted `App:11281-11297`; `record_stop` sets `storagePrerollStop_` `App:14849-14852` | `camera_.finishStoragePreroll` `CC:12142-12196`: stop, count bytes, delete folder, restore settings | pre-roll thread, **no command lock**; CC `mutex_` held during the drain | clip folder deleted | - |
| After: trim | `trimMedia("delete")` `App:11317` | trim worker | - | - | - |
| Status `storage_preroll_active/_fps/_last` (+ `_auto`, `_auto_env`) | App writes the singleton `prerollState()` `SP:224-272` from the pre-roll thread `App:11270-11314` | `bufferSettingMembers` `App:252-269` -> **`settingsBody`** `App:393`, `/api/buffer` `App:8423`, web state `system` `App:9591`, `buffer` event `App:10843`; `runBufferEvents` diffs 4 pre-roll values and ticks at 250 ms while active `App:11007-11053` | atomics + a small string mutex, no lock | none | WebUI PRE-ROLL pill from two writers: `renderSnapshot` `WCP:15391` and the 4 Hz `/api/buffer` loop `WCP:16441-16515`; card last text `WCP:5778`; touch UI reads them in `applyBufferState` `ACB:2726-2766` (buffer event `ACB:1345`, get_state `ACB:1732`); Settings tile disabled while active `SP.qml:5598-5606`, last text `SP.qml:5662` |

## How original Apertar does this kind of thing

| Kind of problem | Upstream precedent | What it shows |
| --- | --- | --- |
| Something internal starts camera work | Idle timer in `wait()` builds `ControlCommand{name "enter_standby", id -1, fields["idle_timeout"]}` and calls `handleCommand` (`App:7041-7047@upstream`, loop `App:7021-7053@upstream`) | Internal work enters through `handleCommand` (CMD-1, CMD-3). An internal-only field (`idle_timeout`) is allowed. The 1 Hz loop is where periodic supervision lives (CMD-21) |
| A timed capture run | Time-lapse is a CC feature: `startTimelapse` `CC:8302-8388@upstream`, its own thread `timelapseLoop` `CC:8447-8500@upstream`, `stopTimelapse` joins `CC:8390-8409@upstream`, a state group `timelapseMutex_`/`Cv_`/`Thread_`/`Active_` `CCH:108-125@upstream`, `CC::stop()` stops it first `CC:7651-7653@upstream` | The clock of a camera run lives in CC on a CC thread. App only starts and stops it. Its active flag has its own small lock, so App reads it from any thread |
| Telling clients about a run | `emitTimelapseEvent` `CC:8798-8820@upstream` (`{"event":"timelapse","active":...}`); `timelapse_active` among the status keys of `get_state` `App:9229@upstream` and `/api/state` `App:7845@upstream`; the UI applies the event `ACB:1218@upstream-ui` and status events go through `applyCoreState` `ACB:1191-1195@upstream-ui` | Capture status = status keys + one event (R4 step 1). Not in `settingsBody` |
| Commands refused while a run is on | Shared guards as `\|\|` lists at the top of `handleCommand` with one sentence each (`App:9095-9110@upstream`, CMD-4); each CC capture entry refuses the others (CAM-32: `CC:8224`, `CC:8244`, `CC:8329@upstream`) | App-level work (media actions, speed test) is gated in App; camera runs are refused in CC, for every caller |
| Stopping whatever runs | `record_stop` stops the sound take first, then the camera take (`App:10783-10794@upstream`) | One stop button; the port's `record_stop` branch fits this |
| Slow job outside the command lock | Media speed test: `startMediaSpeedTest` under the command lock, a worker thread, a state group under `mediaSpeedMutex_`, status in `/api/state` (`App:8957-9089`, `App:7745-7761@upstream`) | A worker exists only for work that must not hold the lock. It is started by the command; it does not take the command lock itself |
| Where fps limits come from | Only the sanitise chain, read back as the effective value (`CC:2707-2744`, `CC:8713-8715@upstream`); `controlsForSettings` pins video to `{d, d}` (`CC:2022-2031@upstream`); the only per-request override is for bracket shots (`CC:6515-6530@upstream`) | No write after the sanitiser; one place sets FrameDurationLimits |
| App reacting to a camera event | `handleTriggerEvent` matches `recording`/`timelapse` events and drives the outputs (`App:10855-10889@upstream`); events leaving outside a command are in the broadcast list `App:10829-10838@upstream` | App reacts to a CC event by string match; no callback interface |
| Simulated camera | `record_start` runs without a session in `--simulate` (`CC:8247@upstream`) | A run can be exercised on a host without frames |

No precedent: a take that is written and then deleted, a take hidden from REC and tally, a run that starts by itself at boot, card insert or format. That is new ground (see below).

## The target

The take is a CC run like time-lapse, started only through `handleCommand`, timed by a CC thread. App keeps the trigger decision and the media gates. Automatic triggers send a command from `wait()`.

| Value or path | Before | After |
| --- | --- | --- |
| Manual start | `storage_preroll`: own guard copy, async request to an App worker | `storage_preroll` (renamed `storage_preroll_start` in commit 10 if the owner agrees). It goes through the head gates like `record_start`; the block calls `camera_.startStoragePreroll(seconds)` and replies `"storage_preroll_active":true` or `errorReply(camera_.lastError())` |
| Automatic start | App worker thread with a queue, a 3 s delay and polling waits | The watcher and `format_media` set one pending request (due time + trigger) under `mediaStateMutex_`. `wait()` sends `ControlCommand{"storage_preroll", id -1, fields trigger=start|mount|format}` once it is due, the trim is idle and the camera is Ready or in Standby, or after 150 s. A refusal is logged as `skipped` (as today: automatic skips never set the last-result text) |
| Lock at start | the worker takes `commandMutex_` itself | `commandMutex_` via `handleCommand`, then CC `mutex_` inside `startStoragePreroll` |
| Busy checks | `storagePrerollGuard` + `decideGuard` (13 inputs) | Head gates of `handleCommand` (media delete, writes pending, media gate, speed test, trim/merge wait, playback yield) + CC `startStoragePreroll`'s own checks (running, recording, time-lapse, not Ready, still mode, not raw, pending stills) + one sound-take line in the block. `decideGuard` and `GuardInputs` deleted |
| Exclusions while it runs | CC 3 entries + App 9 names | CC: every capture entry (`startRecording`, `capturePhoto`, `startTimelapse`, `enterStandby`, `setTuningFile`, `applySettingsLocked`, `setClipNameTemplate`) refuses with "Storage pre-roll is running. One moment." App: `camera_.storagePrerollActive()` joins the `mediaAction` `\|\|` list; the sound-only `record_start` branch refuses. The 9-name list is deleted |
| Length, stop, finish | App thread polls every 25 ms, finishes with no command lock | CC thread `prerollLoop` waits on a cv for `seconds`, a stop request or a write error, then finishes under `mutex_` (stop, count, delete, restore) and emits the end event outside `mutex_`. `record_stop` calls `camera_.stopStoragePreroll()`. `CC::stop()` calls it first |
| Fps | sensor maximum, override after the sanitiser, per-request pin | `maximumFpsForSettings(settings_, family)` (the published `fps_max`), applied by `applySettingsLocked(..., commit=false)`; the sanitiser keeps it; `controlsForSettings` pins `{d, d}`; the phase lock stays released while the take runs. The 1 s period wait moves out of `mutex_` into `prerollLoop`. Owner decision 1 can make this the operator's own fps instead |
| State | header singleton, App writes | CC group `prerollMutex_`: `prerollActive_`, `prerollFps_`, `prerollLast_`, `prerollSeconds_`, thread, cv, stop flag. Public `storagePrerollActive()` and `storagePrerollStatus()` lock `prerollMutex_` only (lock order `mutex_` -> `prerollMutex_`, as with `timelapseMutex_`) |
| Trim after the delete | App thread calls `trimMedia("delete")` | `handleTriggerEvent` sees `{"event":"storage_preroll","active":false` and calls `trimMedia("delete")` |
| Published | `storage_preroll_active/_fps/_last` in `settingsBody`, `/api/buffer`, `system`, `buffer` event | Status keys after `timelapse_shot_count` in `get_state` and at the top of `/api/state`; event `{"event":"storage_preroll","storage_preroll_active":...,"storage_preroll_fps":...,"storage_preroll_last":"..."}` at start and end, in the broadcast list. `storage_preroll_auto`/`_auto_env` stay where the storage-settings theme puts them |
| WebUI | pill from two writers, 4 Hz `/api/buffer` path | pill, fps italics and card from `renderSnapshot` only (1 Hz `/api/state`); the pre-roll branch of the 4 Hz loop is deleted |
| Touch UI, HDMI | read from the `buffer` event and `get_state` | read from `get_state` and the `storage_preroll` event through `applyCoreState` (`ACB:1191@upstream-ui` shape). Same display: italic fps readout, tile disabled, last text |
| `--simulate` | "Storage pre-roll needs the camera." | Runs the clock with no frames (like `record_start`), so the state, event and refusals can be checked on a host |

## Commit plan

Order: the default-off commit `0977dd6` is already in the tree. Every commit is checked with `/home/user/build/bin/check_core.sh /home/user/wt/core-work work both tests` (both builds and the host tests), and `/home/user/build/bin/smoke_core.sh <bin> <port> <out>` diffed against the previous commit (no upstream field missing or retyped). The Pi check is always run with the automatic switch on and the owner's rig (CM5, IMX585, CFexpress, cDNG lossless 4K). Watch the log with `journalctl -u apertar-core -f | grep -E 'storage preroll|phase-lock'`.

### 1. core: every capture entry in the camera refuses a running storage pre-roll

- Repo: Core. `CC`: `enterStandby`, `capturePhoto`, `startTimelapse`, `setTuningFile` get `if (prerollTake_) { setErrorLocked("Storage pre-roll is running. One moment."); return false; }` after their lock, as `startRecording` has it (`CC:11995`).
- Moves nothing, deletes nothing. About -0 / +16.
- Here: both builds; host tests; simulate cannot start a pre-roll yet (commit 3), so only the build proves it.
- Pi: `curl -s -X POST http://<pi>:8000/api/command -d '{"cmd":"storage_preroll"}'`, then within 2 s `-d '{"cmd":"set_tuning_file","value":"<current file>"}'`. Expect the refusal sentence. The log must show `result=ok`. Today the second command reconfigures under the take.
- Depends on: nothing.

### 2. core: the storage pre-roll's state is kept in CameraController

- Repo: Core. `CCH`: new group after the time-lapse group: `mutable std::mutex prerollMutex_; bool prerollActive_ = false; double prerollFps_ = 0; std::string prerollLast_;`; public `bool storagePrerollActive() const;` and `struct StoragePrerollStatus { bool active; double fps; std::string last; }; StoragePrerollStatus storagePrerollStatus() const;`. The `std::atomic<bool> prerollTake_` becomes reads of `prerollActive_` (CC-6-F8). `storagePrerollError()` takes `mutex_` like `recordingError()`.
- `CC::startStoragePreroll`/`finishStoragePreroll` set active, fps and last (the `lastOk` text moves with them).
- `App`: `runStoragePrerollOnce` stops writing `prerollState()`; `bufferSettingMembers`, `runBufferEvents`, `playbackHoldReason`, `mediaTrimMayRun` `App:11478`, `clipMergeMayRun` `App:11709`, the head list `App:12605` read `camera_.storagePrerollActive()` / `storagePrerollStatus()`.
- `SP`: delete `active`, `fps`, `lastMutex`, `last` from `PrerollState`, plus `prerollActive()`, `prerollFps()`, `prerollLast()`, `setPrerollLast()`. Keep `automatic`/`automaticFromEnv` for the storage-settings theme to remove. `tools/storage_preroll_test.cpp` loses its last two checks.
- About -45 / +40.
- Here: builds; host tests; smoke diff (same fields, same types: `storage_preroll_fps` keeps its number form via `jsonNumber`).
- Pi: one manual pre-roll; WebUI pill and `storage_preroll_last` as before.
- Depends on: 1.

### 3. core: the storage pre-roll's length is timed in CameraController

- Repo: Core. `CC`: `startStoragePreroll(unsigned seconds, std::string *error)` starts the take, then `prerollThread_ = std::thread(&CameraController::prerollLoop, this)`. `prerollLoop` waits on `prerollCv_` for `seconds`, `prerollStopRequested_` or a latched `session_->recordingError()` (checked every 100 ms under `mutex_`), then runs today's finish under `mutex_`, sets `prerollLast_`, clears `prerollActive_`, and calls `emitStoragePrerollEvent(false)` outside `mutex_` (as `stopTimelapse` emits outside it, `CC:8390-8409@upstream`). New `stopStoragePreroll()` (sets the flag, notifies, joins), called first in `CC::stop()`. `finishStoragePreroll` becomes private. `storagePrerollError()` is deleted (no reader left). In `--simulate` the loop runs with no session: no frames, `last` = `ok: 2.0 s at N fps, 0 frames, 0.0 GB written and deleted`.
- `App`: `runStoragePrerollOnce` ends after the start (the 25 ms watch loop and the finish block go, `App:11280-11317`). `record_stop` calls `camera_.stopStoragePreroll()` instead of `storagePrerollStop_`. `handleTriggerEvent` gets `if (eventJson.find("\"event\":\"storage_preroll\"") ... "\"storage_preroll_active\":false") trimMedia("delete");`. The `storage_preroll` event joins the broadcast list.
- The 12-line essay comment `CC:12041-12052` becomes one line (CC-6-F6).
- The "Media was removed during the pre-roll." check goes: a pulled card latches a write error, which ends the loop the same way.
- About -60 / +75.
- Here: simulate on a port, `curl -X POST .../api/command -d '{"cmd":"storage_preroll"}'`, poll `/api/state` every 250 ms: `storage_preroll_active` true for about 2 s, then false with `last` "ok: ...". During it, `record_start`, `capture_photo` and `enter_standby` are refused with the sentence. `record_stop` ends it early.
- Pi: a manual pre-roll (log `result=ok`, clip folder gone, `fstrim` line after it). A pre-roll with the card pulled mid-run (log `failed`, camera Ready afterwards). `record_stop` during a pre-roll. Then `sudo systemctl restart apertar-core` during a pre-roll: Core stops cleanly with no leftover clip folder.
- Depends on: 2.

### 4. core: the storage pre-roll goes through the head gates of handleCommand

- Repo: Core. `App` head of `handleCommand`: `storage_preroll` joins the capture-starter names (`mediaDeleteActive_` line, `mediaWritesPending` line, `mediaGateError` block, speed-test line, trim/merge wait, playback yield `Recording`). `camera_.storagePrerollActive()` joins the `mediaAction` `||` list (sentence "Stop recording, still captures and media tests before changing media."). The 9-name list `App:12605-12609` is deleted. The sound-only branch of `record_start` gets `if (camera_.storagePrerollActive()) return errorReply(command.id, "Storage pre-roll is running. One moment.");`.
- The `storage_preroll` block: `seconds` parse, `if (soundRecordingActive()) return errorReply(..., "Stop recording before a storage pre-roll.")`, `camera_.startStoragePreroll(...)`, reply. It logs `reason=<trigger field or manual>`.
- `runStoragePrerollOnce` no longer locks `commandMutex_`. After its settle waits it builds `ControlCommand{name "storage_preroll", id -1, fields["trigger"]}` and calls `handleCommand`, as the idle timer does. Delete `storagePrerollGuard` `App:11124-11148`, `GuardInputs`/`GuardDecision`/`decideGuard` `SP:128-165` and the guard section of `tools/storage_preroll_test.cpp`.
- About -95 / +20.
- Here: simulate: the refusals now read as CC's sentences ("Leave Still Mode before a storage pre-roll." with still mode on, "Storage pre-roll writes raw frames (cDNG, Lossy DNG or MLV)." in ProRes); `format_media` during a run is refused with the media sentence; smoke diff.
- Pi: the automatic trigger after a card insert still runs (log `reason=mount ... result=ok`); `record_start` pressed on the touch UI during the boot pre-roll shows the sentence.
- Depends on: 3.

### 5. core: the automatic pre-roll is sent by the 1 Hz loop as a command

- Repo: Core. Delete the App worker: `runStoragePreroll`, `runStoragePrerollOnce`, `stopStoragePreroll` and their 10 members `AppH:282-293`, its start `App:8043-8046`, and both stop calls `App:8189`, `App:11060`. `requestStoragePreroll(trigger)` keeps its switch check, then stores `storagePrerollDueMs_ = now + 3000`, `storagePrerollTrigger_`, `storagePrerollRequestMs_` under `mediaStateMutex_` (the watcher's own group; `format_media` takes it briefly).
- `wait()`, after the idle-timer block: if a request is due, `!mediaTrimPending_ && !mediaTrimWorking_` (under `mediaTrimMutex_`) and the camera is Ready or in Standby, or 150 s have passed, clear it and `handleCommand(ControlCommand{"storage_preroll", -1, {trigger}})`. A refusal reply is logged (`storage preroll: reason=mount skipped: <sentence>`).
- The manual command no longer goes through a queue: it runs at once, as today (delay 0).
- About -120 / +35.
- Here: simulate with `[media] preroll=on` in the simulate hardware file: Core start runs one pre-roll about 3-4 s after the first watcher cycle (log line, `/api/state`); a second Core start with `preroll=off` runs none. Host tests.
- Pi: cold boot with the switch on (one `reason=start` pre-roll), card insert (`reason=mount`), `format_media` (`reason=format`, and no extra `mount` one). Time from boot to Ready with the switch off is unchanged.
- Depends on: 4. App-2-F4 (worker styles) shrinks by one worker.

### 6. core: the storage pre-roll's fps comes from the sanitiser

- Repo: Core. `CC::startStoragePreroll`: `target = maximumFpsForSettings(settings_, family)` (what the UIs show as `fps_max`). Delete `prerollMaximumFps` `CC:3481-3491`, `setPrerollFps` and its 4 calls (`CC:7507`, `CC:12086`, `CC:12092`, `CC:12179`), `prerollFpsOverride_`, `prerollPinUs_`, the override in `applyControls` `CC:7576-7578`, and the pin in `requeueRequest` `CC:9076-9081`.
- The phase-lock `enabled` condition `CC:8905` gains `&& !prerollMeasuring_.load()`, so `controlsForSettings` alone sets `{d, d}`.
- Keep the shutter-angle carry, `prerollSaved_` and the restore (`commit=false`).
- About -40 / +4.
- Here: both builds (the `#if` branches); fps-ceiling host test.
- Pi: a manual pre-roll in 4K lossless cDNG and in 12-bit uncompressed. Log `requested_fps` = the WebUI's `fps_max`, `measured_fps` within 1 % of it, no `phase-lock` push lines during the run, and the operator's fps back afterwards (`get_state` `fps`). If `measured_fps` stays at the old rate, the per-request pin was load-bearing: stop and report (see Risks).
- Depends on: 3. Target value: owner decision 1, and the camera-modes theme (lossless limits and fps ceilings decide what `maximumFpsForSettings` returns).

### 7. core: the storage pre-roll waits for its frame rate outside the camera lock

- Repo: Core. `startStoragePreroll` applies the fps and sets `prerollActive_`, then returns. `prerollLoop` waits in `session_->waitForFramePeriod` (no `mutex_`), then takes `mutex_` and calls `session_->startRecording`. The CC entries already refuse during the gap, because `prerollActive_` is set.
- About -10 / +12.
- Here: builds; simulate run as in 3.
- Pi: during a pre-roll, `get_state` answers within 100 ms (`time curl .../api/state`); log as in 6.
- Depends on: 6.

### 8. ui: the bridge reads the storage pre-roll from get_state and its event

- Repo: UI. `ACB`: the event list at the `standby`/`still_exposure` line gains `storage_preroll` -> `applyCoreState(message)`. The three `storage_preroll_*` reads move from `applyBufferState` (`ACB:2726-2766`) into `applyCoreState`. The `auto` read stays where the storage-settings theme leaves it.
- It is harmless before commit 9, because `get_state` carries the keys in both places.
- About -0 / +3 (a move of about 30 lines).
- Here: UI build (`/home/user/build/bin/check_ui.sh`).
- Pi: italic fps on the touch screen and HDMI during a pre-roll.
- Depends on: 3 (the event exists).

### 9. core, web: the pre-roll status is published beside timelapse_active

- Repo: Core. `App`: `storage_preroll_active`, `storage_preroll_fps` (`jsonNumber`), `storage_preroll_last` go after `timelapse_shot_count` in `get_state` `App:12966-12968` and the `/api/state` status block `App:9470-9472`, and leave `bufferSettingMembers` (so also `settingsBody`, `/api/buffer`, `system`, the `buffer` event). `runBufferEvents` loses its 8 pre-roll lines and the `sentPrerollActive` 250 ms tick. `prerollFpsText` `SP` is deleted.
- `WCP`: the `system.*` copy loop drops the `storage_preroll_` prefix `WCP:15219`; delete the pre-roll branch of the `/api/buffer` handler `WCP:16500-16515`, `applyPrerollPill`, `notePrerollRequested`, `prerollPollWanted` and the second pill writer `WCP:15758-15763`. The pill and the fps italics come from `renderSnapshot` only. The toast gets its period: "Storage pre-roll started."
- About -75 / +15.
- Here: smoke diff (the three keys move, every upstream field unchanged). Headless Chromium against simulate: click Storage pre-roll and see the PRE-ROLL pill within 1 s and back to READY after about 2 s; the fps badge is italic during the run.
- Pi: the same on the rig's WebUI; touch UI as in 8.
- Depends on: 8, and the webui-state theme for the rest of the 4 Hz loop (only the pre-roll branch is deleted here).

### 10. core, web: the manual pre-roll command is storage_preroll_start

- Repo: Core, with 11 in the same merge. Rename in the block, the head lists, `help`, the 1 Hz command builder and `WCP` `requestStoragePreroll`. `record_stop` keeps ending it (`App-5-F8`: pairs like `timelapse_start`/`timelapse_stop` and `record_start`/`record_stop`).
- About -6 / +6.
- Here: simulate: `storage_preroll_start` works; `storage_preroll` answers "Unknown command".
- Pi: touch tile after 11.
- Depends on: 9; owner decision 2.

### 11. ui: the Storage Pre-roll tile sends storage_preroll_start

- Repo: UI. `ACB:621`. About -1 / +1.
- Here: UI build.
- Pi: tap the tile; log `reason=manual result=ok`.
- Depends on: 10 (merge together: Core and UI ship together, CMD-30).

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| A raw take that is written and deleted | A CC run like time-lapse: `startStoragePreroll`/`stopStoragePreroll`/`storagePrerollActive`, a CC thread, one state group | It is camera work with a clock. Time-lapse is the one upstream run with that shape |
| A take hidden from REC and tally (`recording_` false, no `recording` event, safety stop off, drop warning muted) | One flag (`prerollActive_`) that every CC capture entry refuses on, plus the session's per-take `setPrerollTake` | The owner wants no REC and no tally (CC-6-F3 rework risk). Making it a real `recording_` take would fire the tally output (`handleTriggerEvent`) and the REC UI |
| Runs that start without an operator (Core start, card insert, format) | Off by default (`0977dd6`); a switch whose storage the storage-settings theme decides; sent from `wait()` as a `ControlCommand` with an internal `trigger` field | `wait()` + `idle_timeout` is the upstream way for Core to act by itself. Off by default because upstream never writes to media without an operator action (`App:9095-9117@upstream`) and the benefit is unmeasured (`working/dng-chain-answer.md:175-186`) |
| Settings changed without save or event during the take (`applySettingsLocked(..., commit=false)`, `prerollSaved_`) | Kept for the fps change only | The fps change must not be saved or reach the settings event. Goes away entirely with option A of decision 1 |
| `storage_preroll_last` result text and the measured fps (frame timestamps) | One string in the CC group; measurement kept | It is the only report of what the pre-roll did. Upstream's speed test reports its result the same way (`mediaSpeedLastWriteSpeedMBps_`, `App:10608-10614@upstream`) |
| `[media] preroll_seconds` and the `seconds` argument | Unchanged, 1-10 s | Storage of the key: storage-settings theme |

## For the owner

| # | Question | Options | Recommendation and cost |
| --- | --- | --- | --- |
| 1 | At which fps does the pre-roll write? | A: the operator's own settings (no fps change at all). B: the highest recordable fps of the mode, through the sanitiser (commit 6). C: the sensor's maximum past the lossless cap and the ladder, as today, carried as a pre-roll input of `sanitizeSettingsForSensor` | **B for the merge**: it keeps today's behaviour within the recordable limits, removes the bypass, and respects board caps on other Pi models (the sensor maximum skips them). Cost: on a camera with a ladder or a lossless cap the pre-roll runs slower than today. **A after the KB's E7 A/B** (`working/drop-frames/README.md:330-345`; its WARM arm is a take at the operator's settings): it deletes another ~120 lines (`commit` parameter, `prerollSaved_`, restore, period wait, `storage_preroll_fps` and three italic-fps displays), and the 60 fps run that drops frames in 12-bit uncompressed (`dng-chain-answer.md:183`) goes away. C keeps a second ceiling rule in the sanitiser: not recommended |
| 2 | Rename `storage_preroll` to `storage_preroll_start`? | Rename (commits 10, 11) / keep | Rename: actions are `<noun>_<verb>` (CMD-7) and it pairs with `record_stop`. Cost: both clients change in one merge. Nothing outside the two UIs sends it (**probable**; grep of both repos) |
| 3 | While a pre-roll runs, may exposure, white balance and focus change, as during a real take? | Keep the refusal of every setter (`CC:12747`) / allow the CAM-31 set | Keep: the run is 2-3 s and the settings are restored from a copy at its end, so a change made during it would be lost. Cost: a dial turned during the boot pre-roll shows the sentence once |
| 4 | Should the touch UI and the HDMI monitor show that a pre-roll runs (beyond the italic fps)? | Nothing more (today) / a PRE-ROLL status like the WebUI pill | Nothing more: the operator sees the refusal sentence if he presses record, and the pre-roll is off by default. Cost: none |
| 5 | Keep the format trigger's own request and its 15 s quiet window (`SP:175-198`, `App:14638-14647`)? | Keep / let the format's remount count as a card insert | Keep for now: whether the watcher sees the format's unmount is not determined here (see Risks). Cost: 2 atomics and a scope struct stay |

## Risks and what was not determined

- **The per-request pin (commit 6).** The port pins `{p, p}` on every request "so the take cannot fall back to an older limit" (`CC:9076`). Upstream changes fps through `pendingControls_` once and reads the effective value back. Whether the IMX585 on the qbc libcamera reaches the new period without the pin is not determined. The Pi check in 6 settles it. If it fails, the smallest safe version keeps today's fps behaviour and lands commits 1-5 and 8-11 without 6 and 7.
- **Lock order.** After commit 2, CC takes `mutex_` -> `prerollMutex_`, and `prerollLoop` must never hold `prerollMutex_` while it takes `mutex_`. The end event leaves with no CC lock held, because `handleTriggerEvent` -> `trimMedia` takes `mediaTrimMutex_`. Whether the trim worker ever holds `mediaTrimMutex_` while it calls a `camera_` method was not traced (`App:11445-11480`). Emitting outside `mutex_` makes that question moot.
- **Finish under `mutex_` with no command lock.** It stays as today: the drain holds `mutex_`. A command that arrives meanwhile waits on `mutex_` inside `handleCommand`. Upstream's `stopRecording` drain holds both, but the thread here holds only `mutex_`. Time-lapse queues captures from its own thread under `mutex_` alone (`CC:8475-8483@upstream`), so this is precedented.
- **Card pulled mid-run.** The port also polled App's mount snapshot. After commit 3 only the recorder's latched error ends the loop. That a pulled CFexpress card latches a write error within one second is **probable** (the recorder's `mediaFaultMeansGone` path `CC:12150`); the Pi step in 3 checks it.
- **Format remount.** Whether `format_media` produces a watcher-visible unmount, which would make the format's own request redundant, was not determined (decision 5).
- **The `fps` field during the run.** That the touch UI's poll shows the pre-roll fps as the operator's fps value is **probable** (`ACB:990-1005`, `CC:12579-12582`), not observed. Option A of decision 1 removes the question.
- **Other Pi models.** Commit 6 is safer than today on Pi 4 / CM4 because the sanitiser applies the board caps (`Caps`, CAM-13). It is still unrun there. Pi step: on a Pi 4, a manual pre-roll in cDNG reports `requested_fps` no higher than the WebUI's `fps_max`.
- **Overlapping themes.** The switch and `[media]` keys, `set_storage_preroll`, `storage_preroll_auto/_auto_env` and `bufferSettingMembers` belong to storage-settings. The 4 Hz loop belongs to webui-state. The card placement and the `*Known` latch belong to touch-ui. The fps ceilings belong to camera-modes. Commit 9 must be rebased on whatever storage-settings does to `bufferSettingMembers`.

## Findings covered

| Finding | Commit |
| --- | --- |
| App-4-F2 | 3, 4, 5 |
| App-4-F4 | done in `0977dd6` (default off); the automatic triggers stay as new ground (decision table above) |
| CC-4-F3 | 6, 7 |
| CC-6-F3 | 1 (setTuningFile, enterStandby, capturePhoto, startTimelapse), 2 (one CC state), 4 (App list deleted), 7 (1 s wait under `mutex_`) |
| X-knobs-3 | done in `0977dd6`; the env twin `APERTAR_STORAGE_PREROLL` goes with storage-settings |
| X-stock-behaviour-5 | done in `0977dd6`; 4 makes the refusal list come from CC |
| Media-buffer-split-F6 | pre-roll half: done in `0977dd6`; trim half: not covered (storage-settings / media trim) |
| CC-6-F8 | 2 (status under a lock), 3 (`storagePrerollError` deleted) |
| CC-6-F6 | 3 (essay comment); the T34 line is in the file-wide comment sweep |
| App-5-F8 | 3 (the `record_stop` branch kept, now `camera_.stopStoragePreroll()`), 10, 11 (rename) |
| App-4-F12 | 4 deletes `storagePrerollGuard`; the other four predicates: not covered (one `mediaIdle` helper is its own change) |
| App-2-F4 | 5 removes one worker; the rest: not covered |
| WCP-08-F2 | 9 (pre-roll half); safety-stop pill and timer half: webui-state |
| WCP-10-F13 | 9 |
| WCP-07-F3 | 9 for the three pre-roll fields; the buffer fields: storage-settings |
| App-5-F2, WCP-07-F8, App-1-F1, X-state-consistency-7 | not covered: switch shape and settings serialisers, storage-settings |
| UI-control-bridge-F9, UI-settings-qml-F5 | not covered: touch-ui (the `*Known` latch, the card of its own) |
| X-commits-core-2-1 | not covered: commit-history work (d44b177 squash) |
