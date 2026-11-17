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

## Challenge

Read at: Core `/home/user/wt/core-work` `3650027`, UI `/home/user/wt/ui-work` `ac1fc28`, upstream `35dbe67` / `43888e5`. Line numbers `@work` unless marked `@upstream`. Every row was read in code (**confirmed**) unless it says otherwise.

| Point | What the design says | What the code says, file:line | What must change |
| --- | --- | --- | --- |
| a. Precedent for the CC thread | `prerollLoop` is "shaped like time-lapse" (`timelapseLoop` `CC:8447-8500@upstream`); finishing under `mutex_` with no command lock is precedented because time-lapse queues stills under `mutex_` alone (Risks, 3rd bullet) | `timelapseLoop` never ends itself, never stops a running take and never calls `applySettingsLocked`: it only calls `queuePhotoCaptureLocked` (`CC:8475-8483@upstream`). It is ended only by `stopTimelapse` from a command or `CC::stop()` (`CC:8390-8409`, `CC:7651-7653@upstream`). Every take stop in 1.6.0 runs under `commandMutex_` (`record_stop` `App:10783-10794@upstream`). The finish here stops the recorder, deletes a folder and restores `settings_` through `applySettingsLocked(saved, false, false)` (`CC:12178-12193`): that is take-stop work, not still queuing | The time-lapse precedent covers "a CC thread queues work under `mutex_`", not "a CC thread stops a take and changes `settings_`". Drop the claim, or take the closer precedent below (point e) |
| a. Precedent for a self-ending worker | Not named | The one upstream run that ends by itself is the media speed test: its thread ends, and the next start joins the old thread first (`joinMediaSpeedTest()` `App:8967@upstream`, join `App:9087-9088@upstream`) | If a CC thread stays: `startStoragePreroll` must join the previous `prerollThread_` before it assigns a new one. As written, the second pre-roll of a Core run assigns to a joinable `std::thread` and `std::terminate` ends Core |
| a. Precedent: periodic supervision | `wait()` sends only the automatic start (commit 5) | CMD-21: "Periodic supervision lives in the 1 Hz loop of `wait()`" (`apertar-conventions.md:68`, `App:7021-7053@upstream`). The port's own safety stop already ends a take by a command through `handleCommand` (`dispatchHardwareInputCommand` -> `record_stop`, `App:11085-11113`), which App-4-F2 calls the right way | See point e: the same 1 Hz loop can also end the take through `handleCommand` |
| a. Status struct | `struct StoragePrerollStatus` in `CCH`, no precedent named | `camera_.stillExposureStatus().active` / `.remainingSeconds` (`App:9229-9230@upstream`, `get_state` `App:12969-12970`) is a CC status struct read by App | Name `stillExposureStatus()` as the precedent. Fine as a shape |
| b. `bufferSettingMembers` is a free function | Commit 2: "`bufferSettingMembers`, `runBufferEvents` ... read `camera_.storagePrerollActive()` / `storagePrerollStatus()`" | `std::string bufferSettingMembers()` is a free function (`App:252`), called from the free functions `bufferMembers` (`App:309`) and `settingsBody` (`App:393`) and from three replies (`App:12869`, `12912`, `12943`). It has no `camera_` | Commit 2 as written does not compile without threading a parameter through `settingsBody` (dozens of callers). Move the three keys out of `bufferSettingMembers` in commit 2 itself and write them from member code: `get_state` after `timelapse_shot_count` (`App:12968`), the `/api/state` status block (`App:9470-9472`), the `/api/buffer` handler (`App:8423-8430`) and the `buffer` event in `runBufferEvents`. The WebUI keeps working: `renderSnapshot` copies from `system` only when the top-level key is undefined (`WCP:15218-15220`), and `/api/buffer` still carries the keys for the 4 Hz path. This is the Core half of commit 9, done once instead of twice |
| b. Duplicate member | Commit 2 adds `double prerollFps_ = 0;` to a new group | `double prerollFps_ = 0;` already exists (`CCH:229`), beside `prerollSaved_` and `prerollFolder_`, all under `mutex_` | Reuse it. No second member |
| b. New mutex | Commit 2 adds `prerollMutex_` (lock order `mutex_` -> `prerollMutex_`) | Every other pre-roll member is already under `mutex_`. CC-6-F8's rework is "a plain bool under `mutex_`". `isRecording()` takes `mutex_` and is read by the same App readers (`mediaTrimMayRun` `App:11477`, the trim and merge predicates). `prerollMutex_` is needed only because the design's CC thread holds `mutex_` through the drain | Without the CC thread (point e), no new lock: `prerollTake_` becomes a plain `bool` under `mutex_` and `storagePrerollActive()` locks `mutex_` like `isRecording()`. That deletes the lock-order risk in "Risks" |
| b. Order inside start and finish | Commit 2: `prerollTake_` "becomes reads of `prerollActive_`"; commit 3: the loop "runs today's finish ... clears `prerollActive_`"; commit 7: start "applies the fps and sets `prerollActive_`" | `applySettingsLocked` refuses while `prerollTake_` is set (`CC:12747-12750`). Today the start applies the fps before setting the flag (`CC:12092-12126`) and the finish clears the flag before the restore (`CC:12180-12193`) | State it in commits 2, 3 and 7: set the flag after the fps apply, clear it before the restore. In the order the design writes it, the fps apply is refused (commit 7) and the operator's fps is never restored (commit 3) |
| b. Idle timer | `wait()` gains the automatic start after the idle-timer block | `wait()` resets `lastUserActivityMs_` only on `isRecording()`, `timelapseActive()`, `soundRecordingActive()` (`App:8306-8310`). During a pre-roll the state stays Ready, so an expired idle timer sends `enter_standby` every second; after commit 1 CC refuses it and writes `lastError_` each time | Add `camera_.storagePrerollActive()` to that `\|\|` list (1 line, upstream's own list). Missing from the plan |
| b. Touch UI and HDMI already show PRE-ROLL | "Operators see ... the blue PRE-ROLL pill in the WebUI"; owner decision 4 asks whether the touch UI and HDMI should show more than italic fps; recommendation "Nothing more (today)" | The touch UI status chip shows "PRE-ROLL" in blue (`CameraPage.qml:2708` -> `StatusChip.qml:11`, `:26`, `:60`); the HDMI monitor too (`ExternalMonitorWindow.qml:188-198`) | Decision 4 is already settled by the code: delete it from the owner's list. The plan must keep both chips working and the Pi steps in 8 and 9 must check them |
| b. Touch UI event path | Commit 8 moves the three reads from `applyBufferState` into `applyCoreState` (about 30 lines) | `applyCoreState` already calls `applyBufferState(state)` (`ACB:1732`), so `get_state` already reaches the reads. The touch UI polls `get_state` every 30 s when settled (`kSteadyStatePollIntervalMs = 30000`, `ACB:18`), so the chip lives on events | Commit 8 is one line: add `storage_preroll` to the event list at `ACB:1327-1328` (upstream shape `ACB:1191-1195@upstream-ui`). No move. It must land before the `buffer` event stops carrying the keys |
| b. WebUI `system` prefix | Commit 9: "the `system.*` copy loop drops the `storage_preroll_` prefix `WCP:15219`" | `storage_preroll_auto` and `storage_preroll_auto_env` stay in `bufferSettingMembers` until storage-settings moves them (`App:261-262`); `/api/state` carries them under `system` (`App:9591`). The Automatic row is shown only when `storage_preroll_auto` is a boolean (`WCP:15836-15837`) | Keep the prefix in the copy loop until storage-settings moves the `_auto` keys. Dropping it hides the Automatic pills on every camera |
| b. Pulled card | Commit 3 deletes the "Media was removed during the pre-roll." check: a pulled card "latches a write error" (**probable**) | The check reads App's mount snapshot every 25 ms (`App:11292-11295`); it is the only end condition that does not depend on the recorder | Keep it until the Pi step in 3 has shown the latch. In the shape of point e it is one line in `wait()` (`mediaGateBypassed() \|\| mediaSnapshot().mounted()`) |
| c. Manual refusal text | Commit 4: refusals "now read as CC's sentences" | CC answers a recording, a time-lapse and Standby all with "Camera is not ready." (`CC:12065-12066`); today the manual reply says "Storage pre-roll cannot run now: recording." and sets `storage_preroll_last` to "skipped: recording" (`App:14626-14630`), shown on the WebUI card (`WCP:5778`) and the touch UI (`SP.qml:5662`) | Per cause, in the CAM-32 form: "Stop recording before a storage pre-roll.", "Stop timelapse before a storage pre-roll.", "Wake the camera before a storage pre-roll." Say in the commit that a refused manual pre-roll no longer writes "skipped: ..." into the last-result line (the toast carries it, as for every upstream refusal) |
| c. Rig fps | Commit 6 makes the target `maximumFpsForSettings`; owner decision 1 recommends B "for the merge" | The rig's 4K lossless cDNG pre-roll runs today past the lossless cap (`prerollMaximumFps` `CC:3486-3491`); `maximumFpsForSettings` = min(mode, lossless) (`CC:3495-3500`) | Requirement 3: the rig must be able to behave as today by a setting. Commit 6 removes today's rate with no setting. It is the owner's answer to decision 1, not a step of the series: hold it until he answers. If he picks C, the CC-4-F3 rework (a pre-roll input to `sanitizeSettingsForSensor`) is the commit |
| c. `fps_max` is not `maximumFpsForSettings` | "`maximumFpsForSettings(settings_, family)` (what the UIs show as `fps_max`)"; Pi check "`requested_fps` = the WebUI's `fps_max`" | With the mode ladder on, `fillLadderFieldsLocked` overwrites `fpsMax` with the ladder ceiling over all rungs (`CC:10920`); the running rung's ceiling is `fps_take_max` (`CC:10893`, `:10926`) | Fix the text, and the Pi check: compare `requested_fps` with `fps_max` with the ladder off, and with `fps_take_max` with the ladder on (it may be lower than `maximumFpsForSettings` when a rung has a user threshold: then say which one the pre-roll should use) |
| d. Commit 3 is several ideas | One commit: CC thread, `stopStoragePreroll`, `record_stop`, trim via `handleTriggerEvent`, broadcast list, `--simulate` runs, essay comment, media check removed; -60 / +75 | Each is a separate behaviour: `--simulate` today refuses ("Storage pre-roll needs the camera." `CC:12061-12062`) | Split: the take's end (point e), then "core: --simulate runs a storage pre-roll without frames", then the comment trim with the comment sweep. The media check stays (row above) |
| d. Commit 2 + Core half of 9 | Two commits touch the same publishers | See the `bufferSettingMembers` row | One commit: CC owns the state and App publishes it from member code. Commit 9 keeps only the WebUI cleanup and the deletion of the `/api/buffer` and `buffer`-event copies |
| d. Commit 7 | Moves the 1 s period wait out of `mutex_` into `prerollLoop`; -10 / +12 | The wait exists only because the fps changes (`CC:12110-12114`). Under option A of decision 1 there is no fps change and no wait | Drop it from the series; it follows decision 1. Under B or C, keep today's wait (it is under both locks, at most 1 s, and only on a command the operator or the 1 Hz loop sent) |
| e. Simpler shape for the end | A CC thread with cv, stop flag, join, self-emitted end event, `handleTriggerEvent` string match for the trim; about +75 | `wait()` already runs every second under no lock and calls `handleCommand` (`App:8289-8320`). `record_stop` already ends a pre-roll (`App:14849-14852`). The trim already runs after the finish in App (`App:11317`) | Keep CC's `startStoragePreroll` / `finishStoragePreroll` (as today, minus the pre-roll fps half). `wait()` ends the take: when `camera_.storagePrerollActive()` and (elapsed >= seconds, or `camera_.storagePrerollError()` non-empty, or the medium is gone), it sends `ControlCommand{"record_stop", -1}`; the `record_stop` branch calls `camera_.finishStoragePreroll()`, writes the last line and calls `trimMedia("delete")`. CC emits the `storage_preroll` event at start and finish (in the broadcast list). No CC thread, no cv, no new mutex, no self-join, every start and stop under `commandMutex_` (CMD-1, CMD-3). Cost: the length is 2-3 s instead of 2.0 s (1 Hz loop): owner's list. App's stop path (`App:8189`) and `CC::stop()` call the finish first, as `CC::stop()` calls `stopTimelapse()` first (`CC:7651-7653@upstream`) |
| e. App's start path in commit 3 | The App worker still starts the take after commit 3 | - | With point e, commits 3, 4 and 5 become: 3 "core: the 1 Hz loop ends a storage pre-roll through record_stop" (deletes the 25 ms watch loop and the finish in the worker), 4 as written, 5 as written (the worker goes) |
| f. Hidden decisions | - | Commit 6 (rig fps), commit 4 (refusal sentences, no "skipped:" line), commit 9 (pill latency 250 ms -> up to 1 s on the WebUI for a 2 s run), point e (2-3 s length) | Put each on the owner's list with its cost. Decision 4 leaves the list (settled by the code). Decision 2: "**probable**" becomes **confirmed**: no hardware action names it (`src/hardware/ActionCatalog.hpp`, no `preroll` entry) and no script or test sends it (grep of Core and UI) |
| g. Pi check of commit 1 | `-d '{"cmd":"set_tuning_file","value":"<current file>"}'` | The field is `path` (`App:13143-13145`); with `value` the reply is "set_tuning_file requires path." whether or not the gate works | `curl -s -X POST http://<pi>:8000/api/command -d '{"cmd":"set_tuning_file","path":"<current file>"}'` within 2 s of `storage_preroll`. Expect "Storage pre-roll is running. One moment." and later `result=ok` |
| g. Pi check of commit 7 | `time curl .../api/state` answers within 100 ms during a pre-roll | `/api/state` is served by `buildWebStateJson` without `commandMutex_` (`App:8432-8436`); the 1 s wait holds `commandMutex_` | If commit 7 stays: `time curl -s -X POST http://<pi>:8000/api/command -d '{"cmd":"get_state"}'` sent right after `storage_preroll`. Today it waits up to 1 s; after, under 100 ms |
| g. Pi check of 8 and 9 | Italic fps on touch screen and HDMI | Both screens also show the blue PRE-ROLL chip (rows above) | Add: during a manual pre-roll the touch UI chip and the HDMI status read "PRE-ROLL" within 1 s and go back to READY after it |
| Host checks | `/home/user/build/bin/check_core.sh ...`, `smoke_core.sh` diffed per commit | Both scripts exist (`/home/user/build/bin/`); `tools/` holds 15 `*_test.cpp` files, not 17 | Fine. After the `--simulate` commit, the simulate run of commit 3 also checks the end through `record_stop` and the idle-timer line (a `standby_timeout_seconds` of 1 must not send `enter_standby` during a run: log) |

### Verdict

| Commit | Verdict | What |
| --- | --- | --- |
| 1 | stands | Fix the Pi command (`path`, not `value`) |
| 2 | changes | CC state as a plain `bool` under `mutex_`, existing `prerollFps_` reused, no `prerollMutex_`; flag set after the fps apply and cleared before the restore. The three keys leave the free `bufferSettingMembers` in this commit and are written from member code (`get_state`, `/api/state`, `/api/buffer`, `buffer` event). Absorbs the Core half of 9 |
| 3 | changes | The end goes through `handleCommand`: the 1 Hz loop sends `record_stop` (id -1) when the time is up, a write error is latched or the medium is gone; no CC thread. CC emits the `storage_preroll` event at start and end (broadcast list). Simulate and the comment trim are split off. If the designer keeps the CC thread: join before restart, flag order, and keep the media check |
| 4 | stands | Per-cause CAM-32 sentences instead of "Camera is not ready."; say that a refused manual run no longer writes "skipped: ..." |
| 5 | stands | Add `camera_.storagePrerollActive()` to the idle-timer reset list in `wait()` |
| 6 | changes | Not in the series until the owner answers decision 1; Pi check compares with `fps_max` (ladder off) or `fps_take_max` (ladder on) |
| 7 | dropped | Follows decision 1: gone under A, today's wait kept under B or C |
| 8 | changes | One line: `storage_preroll` joins the event list at `ACB:1327-1328`; no move of reads. Lands before 9 |
| 9 | changes | WebUI only, plus deleting the `/api/buffer` and `buffer`-event copies; keep the `storage_preroll_` prefix in the `system` copy loop while the `_auto` keys live there |
| 10, 11 | stand | Ship together; decision 2 is **confirmed** to touch only the two clients |
| missing | 2 | "core: --simulate runs a storage pre-roll without frames" (split from 3); the idle-timer line (in 5 or its own one-line commit) |

Owner's list after the challenge: decisions 1, 2, 3, 5 stay; 4 goes (settled); new: the 2-3 s length of the 1 Hz end, the refusal sentences and the dropped "skipped:" line, the WebUI pill at 1 Hz.
