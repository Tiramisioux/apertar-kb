# Review CC-6: CameraController.cpp tail (setters, record start/stop, pre-roll, state, events)

| Item | Value |
| --- | --- |
| Scope | `/home/user/build/review/diffs/CC.part06.diff`, new-file lines 11794-12814 of `src/camera/CameraController.cpp@cinemate-port` (01f170c) |
| Yardstick | `raw/conv-core-camera.md` (rule ids S*, I*, N*), upstream code in `/home/user/wt/core-upstream` (`@upstream-1.6.0`), fork main in `/home/user/wt/core-main` |
| Inventory | `raw/inv-CC-6.md` |
| Related reviews | `rev-CC-4.md` (CC-4-F3 pre-roll side channel in the session, CC-4-F6/F7 phase lock and ramp), `rev-App-4.md` (App-4-F2 pre-roll worker outside handleCommand, App-4-F4 auto pre-roll), `rev-App-2.md` (trim switch home, env knobs) |
| Short names | `CC` = `src/camera/CameraController.cpp`, `App` = `src/ApertarCoreApp.cpp`, `CB` = `Apertar-UI/src/ApertarControlBridge.cpp` |

## Findings

| Id | Title | Category | Severity | Deliberate |
| --- | --- | --- | --- | --- |
| CC-6-F1 | Clip-name example probes the media root on every settings read and every settings event, under `mutex_` | bug | major | no |
| CC-6-F2 | Preview TDN off by default also strips temporal denoise from recorded H.264/ProRes | removed-upstream-behaviour | major | no |
| CC-6-F3 | Storage pre-roll is a hidden second take kind; N17 exclusions split between CC and App; `setTuningFile` is not gated | mismatch | major | yes (shape) / no (gap) |
| CC-6-F4 | Early safety-stop `recording` event carries a stale `lastError_` and raises the touch UI's failure dialog | bug | minor | no |
| CC-6-F5 | `fault` event field and `recordingFaultName()` have no consumer | slop | minor | unknown |
| CC-6-F6 | Ticket and project vocabulary, essay comment, duplicated comment | slop | minor | no |
| CC-6-F7 | Drive trim switch stored as a camera setting | mismatch | minor | yes |
| CC-6-F8 | Lock-free read paths (`try_lock` gauge, process-wide `safetyStopState`, atomic `prerollTake_`, unlocked `session_` read) | new-ground | minor | yes |
| CC-6-F9 | `recording` event carries a dropped-frames count | new-ground | nit | yes |
| CC-6-F10 | `clipNameSensorLocked` duplicates `sensorName` | duplication | nit | no |
| CC-6-F11 | `emitLogAppliedIfChangedLocked` + `lastEmittedLogApplied_` patch for one runtime field | new-ground | nit | yes |

### CC-6-F1 Clip-name example scans the drive on every state read (bug, major)

Port, confirmed:
- `CC:12591@cinemate-port` `fillClipNameExampleLocked(result);` in `settings()`; `CC:12772` same in `emitSettingsEventLocked()`.
- `CC:11826-11833` calls `nextClipFolderName(mediaRootPath(mediaRoot_), out, ...)`.
- `CC:1191-1204` `nextClipFolderName` runs `nextClipNumber`, which calls `std::filesystem::exists(root / name)` for clip 1, 2, ... until a free one (`src/util/ClipName.hpp:287-294`, up to 9999).
- `camera_.settings()` has 75 call sites in App, among them every setter reply and `buildWebStateJson` (`App:9298`), which every WebUI client polls each second (`WCP:20954` `window.setInterval(() => fetchState(true), 1000)`).

Upstream, confirmed: the clip folder is found once, at take start (`CC:5548@upstream-1.6.0` `clipFolder = DngRecordingQueue::reserveClipFolder(mediaRoot, settings);`, S17). `settings()` does no I/O (`CC:8566-8573@upstream-1.6.0`).

Failing input: a drive with 400 takes of today's template, one WebUI open: 401 `stat` calls a second, each with `mutex_` held, also during a take on the drive being written. A yanked or hung USB mount (the case 438a342 adds a watcher for) can block `stat`; then `checkRecordingFailure`, record stop and every setter wait on `mutex_`.

Rework: compute the example only where it is asked for. `previewClipName` already does it on demand (`CC:11857-11876`). Drop `fillClipNameExampleLocked` from `settings()` and `emitSettingsEventLocked()`; fill `clipNameExample` in `setClipNameTemplate` and after take start/stop and media mount changes into a cached member, or let the composer call `preview_clip_name`. Effort S.

### CC-6-F2 Preview TDN default also changes processed recordings (removed-upstream-behaviour, major)

Port, confirmed:
- `include/apertar/core/Types.hpp:139@cinemate-port` `bool previewTdn = false; // ... Off (default) is much faster; the raw DNGs never change.`
- Session start `CC:7309-7318`: `if (!settings.previewTdn) { activePath = tuning::previewTuningPath(...) }` for every recording format, no format check.
- Setter in this slice `CC:11898-11922` restarts the pipeline on the other file.
- Commit `e625c68`: "The recorded DNGs are raw and do not change." H.264 and ProRes are not mentioned.

Upstream, confirmed: libcamera loads the selected or default tuning file as is (`CC:1113-1120@upstream-1.6.0`). H.264 and ProRes record the ISP output (conv section 1, "Processed take"; N16). N8 "no silent downgrade of what gets recorded", N13 "monitoring changes stay out of the recording".

Effect: after the update every H.264 and ProRes take is recorded without the ISP temporal denoise the tuning file asks for. For H.264 this is confirmed by the code path; for ProRes probable (it records the ISP's RGB48; whether the derived ProRes tuning starts from `activePath` was not traced: read `CC:7326-7400@cinemate-port`).

Rework: apply the strip only where it is a monitoring-only change, i.e. when the record format is RAW (`!isProcessedVideoFormat(settings.recordingFormat)`), in the `loadablePath` lambda; or default `previewTdn = true` (upstream behaviour) and let the operator opt out. Either keeps the RAW speed gain. Effort S.

### CC-6-F3 Storage pre-roll: a second take kind inside CameraController (mismatch, major)

Port, confirmed:
- `startStoragePreroll` `CC:12051-12128`: starts a raw take with `recording_` false and `state_` Ready, changes `settings_` with `commit=false`, keeps a copy in `prerollSaved_`, holds `mutex_` up to 1 s in `session_->waitForFramePeriod(..., 1000, ...)`.
- `finishStoragePreroll` `CC:12140-12194`: drains, walks and `remove_all`s the clip folder under `mutex_`, restores settings with `commit=false`.
- Exclusions: CC refuses in `startRecording` (`CC:11993`), `applySettingsLocked` (`CC:12745`), `setClipNameTemplate` (`CC:11838`). App refuses `capture_photo`, `record_start`, `timelapse_start`, `format_media`, `eject_media`, `mount_media`, `run_media_speed_test`, `enter_standby`, `storage_preroll` (`App:12588-12592`).
- Gap: `setTuningFile` has its own reconfigure (`CC:11500-11560`, `session_->reconfigure` at `CC:11545`), does not go through `applySettingsLocked`, and `set_tuning_file` is not in App's list. Failing input: `set_tuning_file` during the 2 s pre-roll window reconfigures the session under a running pre-roll take; `finishStoragePreroll` then stops a recorder the reconfigure already tore down and restores settings onto the new pipeline. Hardware-input standby that does not pass `handleCommand` would hit `enterStandby` (`CC:10593-10616`), which does not check `prerollTake_` (unconfirmed which hardware paths bypass `handleCommand`: grep `camera_.enterStandby` in App).

Upstream, confirmed:
- N17: each capture entry in CC refuses the others with a sentence (`CC:8224`, `CC:8244`, `CC:8329`, `CC:7680`, `CC:8048`, `CC:8608@upstream-1.6.0`); App adds only media-level gates (`App:9099-9103`).
- The storage test is App's `runMediaSpeedTest` (`App:9008-9012@upstream-1.6.0`), `fio` on the mount; the camera is not involved.

Rework (with CC-4-F3 and App-4-F2): one state in CC that every entry checks. Either run the pre-roll as a take (`recording_`-like state, the existing N17 refusals then cover it), or add `prerollTake_` to the refusals of `enterStandby`, `capturePhoto`, `startTimelapse`, `setTuningFile` in CC with "Wait for the storage pre-roll to finish." and delete the App-side list. Drop the 1 s wait under `mutex_` (CC-4-F3 removes the fps override that needs it). Effort M.

### CC-6-F4 Stale error in the early safety-stop event (bug, minor)

Port, confirmed: `CC:12440-12444` `if (announcedEarly) emitRecordingEventLocked();` runs before `lastError_` is set from the session (`CC:12448`). `lastError_` is cleared at take start (`CC:12034`) but any refused setter during the take sets it (`setResolution` `CC:10640` "Resolution changes are blocked while recording.").
Upstream: `stopRecording` assigns `lastError_ = session_->recordingError()` before the event (`CC:8510-8514@upstream-1.6.0`).
Failing input: during a take tap a resolution (refused), then the buffer reaches the safety stop. The early event says `"error":"Resolution changes are blocked while recording."`; `CB:1204-1208@ui-upstream` (same in the port) emits `recordingFailed` with that text.
Rework: in the early branch clear `lastError_` (and `recordingFaultName_`) before `emitRecordingEventLocked()`. Effort S.

### CC-6-F5 `fault` field without a reader (slop, minor)

Port, confirmed: `CC:12891` adds `"fault":"<name>"` to the `recording` event; `recordingFaultName()` `CC:12493-12497` is public. `grep -rn 'fault' Apertar-UI/src Apertar-UI/qml WebControlPage.cpp` and `grep recordingFaultName ApertarCoreApp.cpp` find no consumer.
Rework: delete the event field, the getter and `recordingFaultName_`; keep the fault name in the `ApertarCore recording failure:` log line from a local. Or wire it into a UI in the same commit. Effort S.

### CC-6-F6 Comments (slop, minor)

- `CC:11944` `// T34: Ramp-ready changes the rung with Speed Ramp` (ticket number), and the same sentence as the comment one line above.
- `CC:12040-12051`: 12-line essay starting "CineMate's storage warm-up" (project name, history). I19: one to three lines, why only.
Rework: one line "Pre-roll take: not a take for the UIs; recording_ stays false." Delete the ticket and the duplicate. Effort S.

### CC-6-F7 Trim switch as a camera setting (mismatch, minor; same as rev-App-2)

Port: `setMediaTrimEnabled` `CC:11885-11892` writes `CaptureSettings::mediaTrimEnabled`, persisted as `media_trim` in `camera_settings.conf` (`CC:976`), carried across format profiles by hand (`CC:11349`).
Upstream: storage settings live in `[storage]` of `apertar-hardware.conf` (`App:4308-4310@upstream-1.6.0` `mount_path=`), parsed by App; S20/S22: `camera_settings.conf` holds camera settings, the camera side never reads storage config.
Rework: per rev-App-2: `[storage] trim=` owned by App; drop the `CaptureSettings` field and this setter. Effort M (touches App, WCP).

### CC-6-F8 Lock-free read paths (new-ground, minor)

Port: `frameBufferStatus` `CC:12525-12553` reads a process-wide `FrameBufferGauge` and `try_lock`s `mutex_`; `stopRecording` reads the process-wide `bufferbudget::safetyStopState()` (`CC:12442`); `prerollTake_` is `std::atomic`; `storagePrerollError` `CC:12131-12136` reads `session_` without the lock.
Upstream: I24, every public method locks `mutex_` first; I17 process-wide values are function-local statics.
Verdict: keep the `try_lock` gauge (the drain after a RAM-buffer stop holds `mutex_` for seconds and the gauge is polled at 5 Hz; documented in the comment). Simplify the rest: `safetyStopState` becomes a `CameraSession` accessor (the recorder that sets it is in CC: `CC:4600`, `CC:5017`); `prerollTake_` a plain `bool` under `mutex_`; `storagePrerollError` takes the lock like `recordingError()` (nothing holds `mutex_` during the 2 s window). Effort S.

### CC-6-F9 Dropped-frames count in the `recording` event (new-ground, nit)

Port: `CC:12889` `"recording_dropped_frames":<n>`; consumed by the port UI (`CB:2654@cinemate-port`).
Upstream N3: one warning per clip, counts go to the journal (`RecordingDropWarning.hpp:9`, `CC:3416-3423@upstream-1.6.0`).
Flat scalar, an unmodified UI ignores it. Keep; document as a considered change of N3 (drop-frames work, d44b177).

### CC-6-F10 Two sensor-name getters (duplication, nit)

`clipNameSensorLocked` `CC:11816-11822` repeats `sensorName` `CC:12596-12603` with "Simulated" instead of "Simulated Sensor". Rework: one `sensorNameLocked()`; the clip-name code maps the simulated name if it must differ.

### CC-6-F11 Log-applied re-emit (new-ground, nit)

`emitLogAppliedIfChangedLocked` `CC:12875-12879` and `if (commit) emitLogAppliedIfChangedLocked();` on the reconfigure-failure path (`CC:12778`). Upstream sends no settings event when a failed reconfigure ends in `Error` (`CC:8692-8710@upstream-1.6.0`); S21 runtime fields ride on the next ordinary settings event. Simplify: drop `lastEmittedLogApplied_`; if the Error path must inform UIs, emit `emitSettingsEventLocked()` there once.

## Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `apertar::clipname` (`src/util/ClipName.hpp`) | keep | Header-only pure logic in a nested namespace (S4, I22). Fix only its use in `settings()` (F1) |
| `apertar::storagepreroll` + `StoragePrerollResult` + `prerollTake_` state | rework-to-upstream-pattern | F3 here, CC-4-F3, App-4-F2: one take state in CC with N17 refusals; measure at the sanitised ceiling |
| `bufferbudget`, `FrameBufferGauge`, `frameBufferStatus()` | simplify | Keep the gauge and `try_lock`; move `safetyStopState` from a process-wide singleton to the session (F8) |
| `MediaFault` / `classifyMediaErrno`, `flagMediaFault` | keep | Feeds the upstream supervisor `checkRecordingFailure` (N4) instead of a second stop path. Drop the unused `fault` output (F5) |
| Media watcher thread (App) | keep | Outside this slice; its only CC entry `flagMediaFault` is minimal |
| MediaTune / trim (`setMediaTrimEnabled`) | rework-to-upstream-pattern | Storage setting belongs in `[storage]` (F7) |
| Header-only decision modules with host tests | keep | New ground (S24 says upstream has none); pure headers fit S4 |
| `rampNominalShutterUs_`, `restoreFpsAfterRampLocked`, `ladderOverride_` | keep | Controller members with `Locked` helpers (I10, I24); log lines follow I6. Remove the T34 comment (F6) |
| `try_lock` in `frameBufferStatus` + atomic `prerollTake_` | simplify | Keep the `try_lock`; `prerollTake_` back to a plain member under `mutex_` (F8) |
| `emitLogAppliedIfChangedLocked` / `lastEmittedLogApplied_` | simplify | F11 |

## What conforms

| What | Where | Rule |
| --- | --- | --- |
| New setters `setConformFps`, `setFpsPhaseLock`, `setMediaTrimEnabled`, `setClipNameTemplate`: lock, gate with a sentence, copy `settings_`, `applySettingsLocked` | `CC:11804-11892` | I1, I5, S8 |
| `setConformFps` rejects out-of-range with "Conform FPS must be between 1 and 120." | `CC:11807-11810` | I2 |
| `setClipNameTemplate` refused while recording | `CC:11838-11841` | N5 |
| `setPreviewTdn` copies `setTuningFile`'s gates and restarts via `applySettingsLocked(next, true)`, which brings the N9 recovery | `CC:11898-11922` vs `CC:8044-8058@upstream-1.6.0` | S8, S9, N9 |
| New getters `sensorMono`, `sensorBinning`, `phaseLockStatus`, `activeTuningFile`, `cdngLogApplicable` lock `mutex_` | `CC:12612-12645`, `CC:11919-11925` | I24 |
| Runtime fields `isoMeasured`, `isoMax`, `fpsMax`, `cdngLogApplied` are non-persisted `CaptureSettings` fields with trailing comments, filled in `settings()` and `emitSettingsEventLocked()` | `Types.hpp:177-180@cinemate-port`; `CC:12582-12590` | S21 |
| Yanked-drive path ends the take through `checkRecordingFailure`, with one `ApertarCore recording failure: key=value` line | `CC:12456-12478` | N4, I6, I7 |
| `recording` event stays flat scalars; unmodified UI unaffected | `CC:12883-12893` | I12 |
| Preset push of Clear HDR knobs follows fork main's `commitHdrKnobsLocked` and is under `#if APERTARCORE_HAS_LIBCAMERA` | `CC:12686-12698`; `core-main CC:8532-8546@main` | I18 |
| New global switches carried across format profiles | `CC:11347-11368` | N14 note (`CC:7945-7951@upstream-1.6.0`) |
| `validateResolution` keeps every upstream predicate; old 3840x2076 / 1920x1038 are migrated before lookup by both callers, so an unmodified UI still works | `CC:12822-12848`, `CC:10648`, `CC:12663` | no removed behaviour |
| Pre-roll refusal texts are full sentences | `CC:12060-12074` | I5 |

## Not checked here

- Whether the ProRes derived tuning starts from the TDN-stripped copy (F2): read `CC:7326-7400@cinemate-port`.
- Hardware-input paths that call `camera_.enterStandby()` without `handleCommand` (F3).
- Ordering of the settings event from `restoreFpsAfterRampLocked` before the closing `recording` event at stop; harmless to the bridges read, not traced in the WebUI.

## Skeptic

| id | verdict | why |
| --- | --- | --- |
| CC-6-F1 | stands | Confirmed: `settings()` `CC:12592` and `emitSettingsEventLocked()` `CC:12866` call `fillClipNameExampleLocked` -> `nextClipFolderName` (`CC:1191-1204`) -> `nextClipNumber` (`ClipName.hpp:287-294`), one `filesystem::exists` per taken number, under `mutex_`. Upstream `settings()` does no I/O (`CC:8566-8573@upstream-1.6.0`); folder lookup only at take start (`CC:5548@upstream-1.6.0`). WebUI polls state every 1 s (`WCP:20954`). Hung-mount blocking of record stop keeps it major |
| CC-6-F2 | corrected | Confirmed, and stronger: ProRes is confirmed, not probable. `makeProresIspTuning(activePath, ...)` `CC:7412@cinemate-port` derives the ProRes ISP tuning from the TDN-stripped copy. `loadablePath` `CC:7309-7319` has no format check. Commit `e625c68` mentions only DNGs |
| CC-6-F3 | stands | Confirmed: `setTuningFile` `CC:11500-11560` checks Standby, `recording_`, timelapse, pending stills, not `prerollTake_`, and calls `session_->reconfigure` directly (`CC:11545`). `enterStandby` `CC:10593-10615` has no pre-roll check (state stays Ready). App's list `App:12588-12592` lacks `set_tuning_file`. `setPreviewTdn` is covered (goes through `applySettingsLocked`, gated at `CC:12745`) |
| CC-6-F4 | corrected | Confirmed in CC (`CC:12442-12447` emits before `lastError_` is set at `:12448`; `setErrorLocked` `CC:12851` writes `lastError_`). UI anchor corrected: the event handler is `ApertarControlBridge.cpp:1350-1362@cinemate-port` (`emit recordingFailed(error)` on any non-empty `error`), not `CB:1204-1208` |
| CC-6-F5 | corrected | Getter is NOT dead: `App:9562` and `App:12943@cinemate-port` publish it as state `recording_fault`, listed in commit `438a342` and read by the long-takes rig runner (`working/drop-frames/nvme-campaign/research/R10-longtakes-runner.md:147`). Only the `fault` field of the `recording` event (`CC:12891`) has no reader (grep of App, WCP, UI src/qml). Severity nit; deliberate yes for the state key |
| CC-6-F6 | stands | Confirmed `CC:11943-11944` (duplicate comment, T34) and `CC:12038-12050` ("CineMate's storage warm-up", 12 lines). 22 `T<nn>` tags in CC: fold into the file-wide sweep |
| CC-6-F7 | dropped | Contradicts the cross-unit verdict. Final `App-2-F5` (rev-App-2 Skeptic) says per C1-R2 a command-set persisted switch belongs in `camera_settings.conf` and the hardware file keeps board facts (`mount_path`, `pcie_controller`); it moves the other storage switches INTO `camera_settings.conf`. The trim switch is already where that rework puts it. The "same finding as rev-App-2" claim is false |
| CC-6-F8 | corrected | Half right. `session_` is created once in the constructor (`CC:10495`) and never replaced, so the claimed race does not exist. `safetyStopState()` is a function-local static (`BufferBudget.hpp:231`), which is I17, read by App from six sites; moving it behind CameraSession would put those reads behind `mutex_` during the drain. `try_lock` deliberate. What remains: `storagePrerollError()` (`CC:12131-12136`) is a public unlocked method, the only reason CC's `prerollTake_` (`CameraController.hpp:226`) is atomic. Severity nit |
| CC-6-F9 | corrected | Stands as nit. Deliberate evidence corrected: commit `64bbbaa` ("the user wants the number"; fork-log:139), not `d44b177`. UI reader `CB:2654@cinemate-port` confirmed |
| CC-6-F10 | stands | Confirmed `CC:11816-11822` vs `CC:12596-12603`; upstream `sensorName()` `CC:8576@upstream-1.6.0` |
| CC-6-F11 | corrected | Confirmed; second caller added: `setCdngLog` `CC:11433` (calls it after `applySettingsLocked`). Upstream Error path `CC:8692-8710@upstream-1.6.0` sends no event. Deliberate yes (`d44b177`, comment `CC:12873-12874`) |

## Final findings

### CC-6-F1 [bug, major, deliberate no] Clip-name example probes the media root on every settings read and settings event under mutex_
- where: `src/camera/CameraController.cpp:12592@cinemate-port`; `src/camera/CameraController.cpp:12866@cinemate-port`; `src/camera/CameraController.cpp:11825-11833@cinemate-port`; `src/camera/CameraController.cpp:1191-1204@cinemate-port`; `src/util/ClipName.hpp:287-294@cinemate-port`
- port: `settings()` and `emitSettingsEventLocked()` call `fillClipNameExampleLocked` -> `nextClipFolderName` -> `nextClipNumber`, which calls `std::filesystem::exists` for clip 1..9999 until a free name, with `mutex_` held. `settings()` runs on every setter reply and every state poll (WebUI 1 s per client, `WCP:20954`).
- apertar way: Clip folder looked up once at take start: `CC:5548@upstream-1.6.0` `clipFolder = DngRecordingQueue::reserveClipFolder(mediaRoot, settings);`. `settings()` does no I/O (`CC:8566-8573@upstream-1.6.0`).
- why it matters: 400 takes on the drive and one WebUI open = 401 stat calls per second under `mutex_`, also during a take. On a hung or yanked USB mount stat can block; then `checkRecordingFailure`, record stop and every setter wait on `mutex_`.
- rework: Remove `fillClipNameExampleLocked` from `settings()` and `emitSettingsEventLocked()`. Compute the example into a cached member in `setClipNameTemplate`, after take start/stop and on mount change; or let the composer call `preview_clip_name` (`CC:11857-11876`), which already computes it on demand.
- effort: S. deliberate: no (commit `014a2bf` does not discuss the I/O cost; host test covers only the pure logic).

### CC-6-F2 [removed-upstream-behaviour, major, deliberate no] Preview TDN off by default also strips temporal denoise from recorded H.264 and ProRes
- where: `include/apertar/core/Types.hpp:139@cinemate-port`; `src/camera/CameraController.cpp:7306-7326@cinemate-port`; `src/camera/CameraController.cpp:7412@cinemate-port`; `src/camera/CameraController.cpp:11893-11917@cinemate-port`
- port: `previewTdn` defaults to false. At session start `loadablePath` loads a copy of the tuning file without the `rpi.denoise` tdn blocks for every record format; no format check. The ProRes ISP tuning is derived from that stripped copy (`makeProresIspTuning(activePath, ...)` `CC:7412`). H.264 records the ISP YUV output. Both confirmed.
- apertar way: Upstream loads the selected or default tuning file unchanged (`CC:1113-1120@upstream-1.6.0`). N8: no silent downgrade of what is recorded. N13: monitoring changes stay out of the recording.
- why it matters: After the update every H.264 and ProRes take is recorded without the temporal denoise the tuning asks for, and the operator is not told. The setting is named "Preview".
- rework: In `loadablePath`, strip TDN only when `!isProcessedVideoFormat(settings.recordingFormat)` (`CC:280`); keep the full file for H.264/ProRes and as the base of `makeProresIspTuning`. Or default `previewTdn = true`. Both keep the RAW speed gain.
- effort: S. deliberate: no (commit `e625c68`: "The recorded DNGs are raw and do not change."; processed formats not mentioned; tested desk only).

### CC-6-F3 [mismatch, major, deliberate yes (design) / no (gaps)] Storage pre-roll is a hidden second take kind; N17 exclusions split between CC and App; setTuningFile and enterStandby ungated in CC
- where: `src/camera/CameraController.cpp:12038-12194@cinemate-port`; `src/camera/CameraController.cpp:11993@cinemate-port`; `src/camera/CameraController.cpp:12745@cinemate-port`; `src/camera/CameraController.cpp:11500-11560@cinemate-port`; `src/camera/CameraController.cpp:10593-10615@cinemate-port`; `src/ApertarCoreApp.cpp:12588-12592@cinemate-port`
- port: `startStoragePreroll` starts a raw take while `recording_` stays false and `state_` stays Ready; changes `settings_` with `commit=false`, keeps a copy in `prerollSaved_`, waits up to 1 s in `waitForFramePeriod` with `mutex_` held. Exclusions are split: CC checks `prerollTake_` in `startRecording`, `applySettingsLocked`, `setClipNameTemplate`; App checks a list of 9 command names. `setTuningFile` reconfigures through `session_->reconfigure` (`CC:11545`) with no `prerollTake_` check, and `set_tuning_file` is not in App's list. `enterStandby` in CC has no pre-roll check (only App's list stops `enter_standby`).
- apertar way: N17: each capture entry in CC refuses the others with a sentence (`CC:8224, 8244, 8329, 7680, 8048, 8608@upstream-1.6.0`). The media test is App's `runMediaSpeedTest`, fio on the mount, no camera (`App:9008-9012@upstream-1.6.0`).
- why it matters: `set_tuning_file` during the 2 s pre-roll reconfigures the session under a running pre-roll take; `finishStoragePreroll` then stops a recorder already torn down and restores settings onto the new pipeline. Any `enterStandby` caller that bypasses `handleCommand` stops the session under the pre-roll. The original developer looks for the exclusion in CC and finds it incomplete.
- rework: With CC-4-F3 and App-4-F2: one state in CC that every entry checks. Either run the pre-roll as a `recording_`-like take so the existing refusals cover it, or add the `prerollTake_` refusal ("Storage pre-roll is running. One moment.", the text already used at `CC:11993`) to `enterStandby`, `capturePhoto`, `startTimelapse` and `setTuningFile`, and delete App's command list. Remove the 1 s wait under `mutex_` once the fps override is gone.
- effort: M. deliberate: yes for the design (comment above `startStoragePreroll`, fork-log:138); the `setTuningFile`/`enterStandby` gaps are not mentioned anywhere.

### CC-6-F4 [bug, minor, deliberate no] Early safety-stop recording event carries a stale lastError_
- where: `src/camera/CameraController.cpp:12440-12448@cinemate-port`; UI reader `src/ApertarControlBridge.cpp:1350-1362@cinemate-port` (Apertar-UI)
- port: With the buffer safety stop active, `emitRecordingEventLocked()` runs before `lastError_` is set from the session. A setter refused during the take leaves its sentence in `lastError_` (`setErrorLocked` `CC:12851`).
- apertar way: `stopRecording` assigns `lastError_ = session_->recordingError()` before the event (`CC:8510-8514@upstream-1.6.0`).
- why it matters: During a take a resolution change is refused ("Resolution changes are blocked while recording."); the safety stop fires; the early event carries that sentence and the bridge emits `recordingFailed` with it (`CB:1357-1362`).
- rework: In the `announcedEarly` branch, clear `lastError_` and `recordingFaultName_` before `emitRecordingEventLocked()`.
- effort: S.

### CC-6-F5 [slop, nit, deliberate unknown] `fault` field of the recording event has no consumer
- where: `src/camera/CameraController.cpp:12891@cinemate-port`
- port: The `recording` event gains `"fault":"<name>"`. Grep of App, WCP, Apertar-UI `src` and `qml` finds no reader. The getter `recordingFaultName()` is used: App publishes it as state `recording_fault` (`App:9562`, `App:12943`), named in commit `438a342` and read by the long-takes rig runner.
- apertar way: The upstream `recording` event carries only `active`, `recording_has_dropped_frames`, `error` (`CC:8786-8796@upstream-1.6.0`).
- why it matters: Unused event surface next to a state key that already carries the same value.
- rework: Delete the `fault` field from `emitRecordingEventLocked`. Keep `recordingFaultName_`, the getter and state `recording_fault`.
- effort: S.

### CC-6-F6 [slop, minor, deliberate no] Ticket and project vocabulary, essay comment, duplicated comment
- where: `src/camera/CameraController.cpp:11943-11944@cinemate-port`; `src/camera/CameraController.cpp:12038-12050@cinemate-port`
- port: `// T34: Ramp-ready changes the rung with Speed Ramp` repeats the comment on the line above. A 12-line block starting "CineMate's storage warm-up" precedes `startStoragePreroll`.
- apertar way: I19: comments one to three lines that say why, no ticket numbers (`CC:6927-6928`, `CC:8248-8250@upstream-1.6.0`).
- why it matters: The original developer reads internal tutorial numbers and another project's name. CC carries 22 `T<nn>` tags; fold into the file-wide sweep.
- rework: Delete the T34 comment (keep the line above). Shorten the block to one line: "Pre-roll take: not a take for the UIs; recording_ stays false."
- effort: S.

### CC-6-F8 [new-ground, nit, deliberate unknown] Unlocked public storagePrerollError and the atomic CC prerollTake_ it needs
- where: `src/camera/CameraController.cpp:12131-12136@cinemate-port`; `src/camera/CameraController.hpp:226@cinemate-port`
- port: `storagePrerollError()` is public and reads `prerollTake_` and `session_->recordingError()` without `mutex_`; that is the only reason CC's `prerollTake_` is `std::atomic`. Every other CC use is under the lock. (`session_` is never replaced, `CC:10495`, so no race; `safetyStopState()` is a function-local static per I17 and the `try_lock` in `frameBufferStatus` is deliberate, comment `CC:12522-12524`.)
- apertar way: I24: every public `CameraController` method locks `mutex_` first; `recordingError()` does (`CC:12646-12650@cinemate-port`, same at upstream).
- why it matters: One more concurrency style in the class for a 1 Hz poll that does not need it.
- rework: `storagePrerollError()` takes `mutex_` like `recordingError()`; `prerollTake_` becomes a plain `bool` under `mutex_` (drop `.load()` at `CC:12877`).
- effort: S.

### CC-6-F9 [new-ground, nit, deliberate yes] recording event carries a dropped-frames count
- where: `src/camera/CameraController.cpp:12889@cinemate-port`
- port: Adds `"recording_dropped_frames":<n>`; the port UI reads it (`CB:2654@cinemate-port`).
- apertar way: N3: one warning per clip, counts go to the journal (`RecordingDropWarning.hpp:9`, `CC:3416-3423@upstream-1.6.0`).
- why it matters: A considered change of an upstream product rule. Flat scalar, an unmodified UI ignores it.
- rework: Keep; document for the original developer as a deliberate change to N3.
- effort: S. deliberate: yes, commit `64bbbaa` ("the user wants the number"), fork-log:139.

### CC-6-F10 [duplication, nit, deliberate no] clipNameSensorLocked duplicates sensorName
- where: `src/camera/CameraController.cpp:11816-11822@cinemate-port`; `src/camera/CameraController.cpp:12596-12603@cinemate-port`
- port: A second copy of `sensorName`'s body that returns "Simulated" instead of "Simulated Sensor".
- apertar way: `sensorName()` `CC:8576@upstream-1.6.0` is the single place.
- why it matters: Two copies drift apart.
- rework: Add `sensorNameLocked()` used by both; the clip-name code maps the simulated name if it must differ.
- effort: S.

### CC-6-F11 [new-ground, nit, deliberate yes] emitLogAppliedIfChangedLocked + lastEmittedLogApplied_ for one runtime field
- where: `src/camera/CameraController.cpp:12875-12879@cinemate-port`; `src/camera/CameraController.cpp:12778@cinemate-port`; `src/camera/CameraController.cpp:11433@cinemate-port`; `src/camera/CameraController.hpp:200,225@cinemate-port`
- port: Tracks the last emitted `cdng_log_applied` and sends an extra settings event on the reconfigure-failure path and after `setCdngLog` if it changed.
- apertar way: A failed reconfigure that ends in Error sends no settings event (`CC:8692-8710@upstream-1.6.0`). S21: runtime fields ride on the next ordinary settings event.
- why it matters: Extra state and a helper for one field.
- rework: Delete `lastEmittedLogApplied_` and the helper. If the Error path must inform the UIs, call `emitSettingsEventLocked()` there once; `setCdngLog` already gets its event from `applySettingsLocked` on success.
- effort: S. deliberate: yes (`d44b177`; comment `CC:12873-12874` names the event-driven UIs).
