# Inventory CC-6: CameraController.cpp new-file lines 11794-12814 (tail: setters, record start/stop, state, events)

Diff read: /home/user/build/review/diffs/CC.part06.diff (809 lines, 8 hunks). Read at `@cinemate-port` (01f170c) against `@upstream-1.6.0`.
Blame of the 1021-line scope: 565 lines are upstream (`^35dbe67`), 456 are port lines in 20 commits (d44b177 = 215).
Status of every commit: fork-log.md. All are fork-only, none offered upstream yet except as listed.

## Commits in this slice

| Commit | Subject | Lines in scope | fork-log status / Tested line |
| --- | --- | --- | --- |
| d44b177 | drop-frames (trim, Log, RAM buffer, safety stop, buffer bar, fps max, storage pre-roll); 19 commits squashed | 215 | fork-log:138 "Not yet run on the camera"; Pi build, host tests, 4 Sonnet reviews |
| 014a2bf | clip names you can compose | 62 | fork-log:138 (part of the drop-frames line); host test tools/clip_name_test.cpp |
| e625c68 | Preview temporal denoise switch | 34 | fork-log:171 Pi only; commit: "desk only, not built (no libcamera on Mac); tuning_tdn_strip_test passes" |
| 438a342 | survive a yanked drive (media fault latch, probe, watcher) | 30 | fork-log:41 built 22:27 with e8bb1b7; commit: "desk only (not built yet)" |
| faa2958 | speed ramping behind fps_speed_ramp | 19 | fork-log:58 tested on Pi 2026-10-28 (C0030-C0032, 1080p 25->50->25) |
| 80ddac1 | frame-rate phase lock, off by default | 16 | fork-log:37, built 22:04 with 8f7dc39 |
| 8e8ea2e | presets carry every operating-mode switch | 13 | fork-log:63 tested 2026-10-28 |
| d7ff071 | conform_fps | 12 | fork-log:67 tested 2026-10-28 (hardware-log) |
| ce0bd90 | set_media_trim switch | 8 | fork-log:170 Pi only; commit "desk only" |
| 4ab1057 | binning per sensor mode | 8 | fork-log:36 list_sensor_modes + get_state verified |
| c5db8b2 | record during safety-stop flush discards queue | 7 | fork-log:138 owner decision 2026-11-01 |
| f60e301 | sensor-mode probe at startup (fork main, Clear HDR set) | 6 | fork-log:30 (contributor's earlier work, already on origin/main) |
| caa0153 | imx585 modes from tables | 6 | fork-log:138 (imx585-modes merge) |
| 766aba8 | review fixes of seven commits | 5 | fork-log:157 |
| 646a194 | iso_actual in state | 4 | fork-log:62 tested 2026-10-28 |
| 97adea0 | [camera] max_fps, fps_max in state | 3 | fork-log:73 superseded by bcedbe5 |
| 900d282 | imx585 1.85:1 crops 3840x2072/1920x1036 | 3 | fork-log:138 |
| 0041ba0 | mode ladder (T34) | 3 | fork-log:87 tested 2026-10-28 |
| ca7b7c2 | stretched WAV after ramp take | 1 | fork-log:69 tested 2026-10-28 |
| 631721d | Clear HDR (on fork main) | 1 | fork-log:25 |

## Feature to region

| Feature | Port commits | New-file lines | Kind |
| --- | --- | --- | --- |
| Conform FPS | d7ff071 | 11804-11815 `setConformFps` | new setter |
| Composable clip names | 014a2bf | 11816-11876 `clipNameSensorLocked`, `fillClipNameExampleLocked`, `setClipNameTemplate`, `previewClipName`; 12592, 12769-ish `fillClipNameExampleLocked` in `settings()` and `emitSettingsEventLocked` | new setters, state field filled on every read and event |
| Frame-rate phase lock | 80ddac1 | 11877-11884 `setFpsPhaseLock`; 12638-12645 `phaseLockStatus()` | new setter, new getter |
| Drive trim switch | ce0bd90 | 11885-11892 `setMediaTrimEnabled` | new setter (worker is in other units) |
| Preview temporal denoise | e625c68 | 11893-11926 `setPreviewTdn`, `activeTuningFile()` | new setter; restarts pipeline on another tuning file like `setTuningFile` |
| FPS speed ramp | faa2958, ca7b7c2, 0041ba0 | 11928-11947 `setFpsSpeedRamp`; 12026-12027 `rampTakeBaseFps_`/`rampTakeChanged_` set at take start; 12447 and 12473 `restoreFpsAfterRampLocked()` at stop/failure | new setter + hooks in start/stop/failure |
| Storage pre-roll | d44b177 | 11993-11996 and 12039-12195 `startStoragePreroll`, `storagePrerollError`, `finishStoragePreroll`; `prerollTake_` guards in `startRecording` (11992), `checkRecordingFailure` (12460), `applySettingsLocked` (12745-12778 area), `emitLogAppliedIfChangedLocked` | new subsystem, driven by a Core thread (ApertarCoreApp::runStoragePreroll) |
| Media fault (yanked drive) | 438a342 | 12030-12032 reset of `externalFailureMessage_`, `externalMediumGone_`, `recordingFaultName_` at take start; 12449, 12462-12470 `checkRecordingFailure` fault path; 12480-12498 `flagMediaFault`, `recordingFaultName()`; event field `fault` | extends take lifecycle; watcher thread in App calls `flagMediaFault` (ApertarCoreApp.cpp:10920) |
| RAM/frames write buffer, 90 % safety stop | d44b177, c5db8b2 | 12440-12444 `announcedEarly` in `stopRecording`; 12511-12553 `cdngLogApplicable(Locked)`, `frameBufferStatus()` (try_lock, lock-free gauge), `rawTakeActive()` | new getters, early recording event |
| Log On/Off applied flag | d44b177 | 12582 `result.cdngLogApplied`; 12769+ `lastEmittedLogApplied_`, `emitLogAppliedIfChangedLocked`, 12745-12778 `if (commit) emitLogAppliedIfChangedLocked()` on error path | new state field + extra event emission |
| ISO measured / ISO max / FPS max | 646a194, 97adea0, d44b177 | 12583-12590 `isoMeasured`, `isoMax`, `fpsMax` in `settings()`; same in `emitSettingsEventLocked` | state fields |
| Mode ladder fields | 0041ba0 | 12591 `fillLadderFieldsLocked`; `ladderRewriteLocked` call in `setFpsSpeedRamp` (T34 comment); `ladderOverride_` reset | state fields; ladder logic outside slice |
| Sensor modes: mono, binning | caa0153, 4ab1057 | 12612-12625 `sensorMono()`, `sensorBinning()` | new getters |
| Resolution validation per sensor | f60e301, caa0153, 900d282 | 12794-12814 area `validateResolution` | rewrites upstream function body |
| Preset load | 8e8ea2e, 900d282, 0041ba0 | 12686-12698 and 12727 `applyCapturePreset` | extended in place |
| Recording event | d44b177, 438a342 | `emitRecordingEventLocked`: new fields | event grows two fields |

## Socket commands / routes / events / state / config / env / files touched by this slice

The setters here are the controller side. The command entry is in `ApertarCoreApp.cpp` (other units): `set_conform_fps` (:13270), `set_clip_name_template` (:13241), `preview_clip_name` (:13258), `set_fps_phase_lock` (:13214), `set_media_trim` (:13194), `set_preview_tdn` (:13205), `set_fps_speed_ramp` (:13223), `storage_preroll` (:14603, also blocked while recording at :12591).

| Kind | Items (all confirmed in this slice unless noted) |
| --- | --- |
| Socket commands (via setters here) | set_conform_fps, set_clip_name_template, preview_clip_name, set_fps_phase_lock, set_media_trim, set_preview_tdn, set_fps_speed_ramp (enabled, keep_exposure, stretch_audio, return), storage_preroll |
| HTTP routes | none in this slice. `frameBufferStatus()` serves `GET /api/buffer` (route in App/WCP, other unit; fork-log:138) |
| `CaptureSettings` fields filled or set | conformFps, clipNameTemplate, clipNameExample (derived), fpsPhaseLock, mediaTrimEnabled, previewTdn, fpsSpeedRamp, fpsSpeedRampKeepExposure, fpsSpeedRampStretchAudio, fpsSpeedRampReturn, cdngLogApplied (derived), isoMeasured, isoMax, fpsMax, ladder fields (via fillLadderFieldsLocked), whiteBalanceMeasured (upstream) |
| Controller state members added (header) | prerollTake_ (atomic), prerollSaved_, prerollFolder_, prerollFps_, rampNominalShutterUs_, rampTakeBaseFps_, rampTakeChanged_, ladderOverride_, externalFailureMessage_, externalMediumGone_, recordingFaultName_, lastEmittedLogApplied_ |
| Events | `recording` event gains `recording_dropped_frames` (count) and `fault` (name); `settings` event gains the fields above; early `recording active=false` on safety stop; extra settings event when `cdng_log_applied` flips (emitLogAppliedIfChangedLocked) |
| Config keys (persisted in camera_settings.conf by code outside the slice, confirmed at CameraController.cpp:817-981) | conform_fps, fps_phase_lock, preview_tdn, media_trim, fps_speed_ramp, fps_speed_ramp_keep_exposure, fps_speed_ramp_stretch_audio, fps_speed_ramp_after, clip_name_template |
| Config keys in apertar-hardware.conf used by helpers called here | `[media] preroll`, `[media] preroll_seconds` (StoragePreroll.hpp:22-30); `[storage]` keys (BufferBudget.hpp:97) |
| Env vars | APERTAR_CDNG_BUFFER* / APERTAR_CDNG_QUEUE_RAM_MAX_FRACTION (BufferBudget.hpp:35); others named in fork-log (APERTAR_MEDIA_TRIM, APERTAR_FPS_LIMIT, APERTAR_LOSSLESS_FPS_LIMIT) are outside this slice |
| Files on disk | pre-roll clip folder written under the media root then `remove_all`'d (12186-12192); `fps-ramp.txt` and `_stretched.wav` (ramp take, other units); stderr log lines "ApertarCore storage preroll:", "ApertarCore recording failure:" |
| UI elements | none in this unit (WebUI / UI repos). Features above feed: buffer bar, REC/tally off on early event, clip-name pill composer, Performance card, Preview TDN switch |

## Original upstream code modified

| Region | Where (new-file / upstream) | Change | Kind |
| --- | --- | --- | --- |
| `startRecording` | 11983-12028 / upstream 8219 | pre-roll guard; ramp base fps; reset of fault/external-failure members | extended in place |
| `stopRecording` | 12430-12446 / upstream 8502 | early `recording` event when the buffer safety stop is active; `restoreFpsAfterRampLocked`; `recordingFaultName_`; closing event only on error if announced early; `session_->stopRecording()` unchanged signature here | extended in place, behaviour changed (event timing: upstream always emits after stop) |
| `checkRecordingFailure` | 12452-12478 / upstream 8519 | skip while pre-roll; external (watcher) failure message; `session_->stopRecording(mediumGone)` (signature changed); fault name; stderr log; ramp restore | rewritten in part, behaviour changed |
| `settings()` | 12572-12590 / upstream 8566 | adds cdngLogApplied, isoMeasured, isoMax, fpsMax, ladder fields, clipNameExample; braces added | extended in place |
| `applyCapturePreset` | 12600-12698 / upstream 8604 | imx585 legacy crop migration, `rampNominalShutterUs_ = 0`, `next.resolution = presetResolution`, `#if APERTARCORE_HAS_LIBCAMERA` push of Clear HDR knobs when no reconfigure | extended in place |
| `applySettingsLocked` | 12735-12778 | refuses while `prerollTake_`; `emitLogAppliedIfChangedLocked` on error | extended in place |
| `validateResolution` | 12814 area / upstream 8751 | sensor-family gate; IMX283 and generic IMX585 tables; upstream whitelist entries `isImx585FullHdCropResolution`, `isImx585Raw12CropResolution` replaced by `isImx585LegacyCropResolution` and `isImx585KnownResolution` | rewritten |
| `emitSettingsEventLocked` | 12830 area / upstream 8777 | recomputes isoMax, fpsMax, ladder, clip example, log applied; records last emitted log-applied | extended in place |
| `emitRecordingEventLocked` | 12850 area / upstream 8786 | two new JSON fields | extended in place |

## New abstractions

| Name | Files | Purpose | Upstream equivalent |
| --- | --- | --- | --- |
| `apertar::clipname` | src/util/ClipName.hpp (296 lines), tools/clip_name_test.cpp | parse/normalise clip-name template, build folder name | none (upstream names clips with a fixed pattern in the session; not compared in this slice, unconfirmed: read `nextClipFolderName` in unit that holds it) |
| `apertar::storagepreroll` + `StoragePrerollResult` + prerollTake_ state machine | src/util/StoragePreroll.hpp, App thread `runStoragePreroll` (ApertarCoreApp.cpp:11115) | warm up storage with a 2 s raw take at max fps, delete it | none; new ground |
| `bufferbudget` namespace, `FrameBufferGauge`, `frameBufferStatus()` | src/util/BufferBudget.hpp (382 lines) | frames/ram write queue sizing, safety stop, lock-free gauge for 5 Hz polling | none; upstream has a fixed queue |
| `MediaFault` / `classifyMediaErrno`, MediaProbe, MediaIntent | src/util/MediaFault.hpp, MediaProbe.hpp, MediaIntent.hpp | classify write errors; media watcher flags yanked drive via `flagMediaFault` | upstream `src/util/RecordingFailure.hpp` holds only a message (the port changed it, see util diff, 13 lines in RecordingDropWarning.hpp) |
| Media watcher thread (calls `flagMediaFault`) | ApertarCoreApp.cpp:10920 | detects mount going away | none |
| MediaTune / MediaProfile / trim worker | src/util/MediaTune.hpp, MediaProfile.hpp, scripts/apertar-media-trim | drive trim (called here only via `setMediaTrimEnabled`) | none |
| Header-only "decision" modules with host tests | tools/*_test.cpp | testable pure logic | upstream Core has no tests |
| `rampNominalShutterUs_`, `restoreFpsAfterRampLocked`, `ladderOverride_` | CameraController.hpp:192,245,249 | ramp and ladder bookkeeping inside the controller | none |
| try_lock read path in `frameBufferStatus` + `std::atomic prerollTake_` | CameraController.cpp:12511-12553 | read state without taking `mutex_` | upstream takes `std::lock_guard<std::mutex>` in every getter; the port also adds lock-free atomics (new pattern) |

## Removed, narrowed or hidden

| What | Where | Effect |
| --- | --- | --- |
| `isImx585FullHdCropResolution`, `isImx585Raw12CropResolution` in `validateResolution` | 12794-12814 | replaced by table lookups; 3840x2076 / 1920x1038 migrated to 3840x2072 / 1920x1036 on preset load (900d282) |
| IMX283 sizes | `validateResolution` | accepted only on IMX283 or unknown sensor |
| IMX585 table sizes (2880x2160, 2048x1152...) | `validateResolution` | accepted only on IMX585 or unknown; upstream accepted without a family check |
| `recording` event always emitted after a stop | `stopRecording` | suppressed when the safety stop already announced it and no error |
| Recording or settings change while pre-roll runs | `startRecording`, `applySettingsLocked` | "Storage pre-roll is running. One moment." |
| FPS ramp on/off during a take | `setFpsSpeedRamp` | blocked while recording |
| Ladder override | `setFpsSpeedRamp` | ramp toggle clears Clear HDR override |

## Board assumptions in this slice

| Assumption | Where | Note |
| --- | --- | --- |
| RAM size | `frameBufferStatus` mode "ram", BufferBudget reads `/proc/meminfo` MemTotal, fraction 0.5 (BufferBudget.hpp:35,83) | Linux generic, no Pi model check; sized by MemTotal |
| Sensor family names: IMX283, IMX477, IMX294, IMX585 | `validateResolution`, binning, mono | sensor-specific, not board |
| libcamera build flag | `#if APERTARCORE_HAS_LIBCAMERA` (12647) | port added the macro in other units |
| Pre-roll max fps vs write speed | `prerollMaximumFps` (CameraController.cpp:3486) | measures sustained write; storage speed unknown, unconfirmed |
| Four cores, RP1, PCIe, gpiochip, I2C, fan | none found in this slice | confirmed by reading the diff and the scope |
| `rubberband` binary | stretched WAV (ca7b7c2) in other units | not in this slice |

## Open points for stage 2 (not judged here)

- Whether upstream has a precedent for `nextClipFolderName` building (clip naming) and `RecordingFailure.hpp` use.
- `setPreviewTdn` / `setFpsSpeedRamp` call `applySettingsLocked(..., true)` with extra preconditions that duplicate `setTuningFile`; compare in stage 2.
- Untested on camera: d44b177 and children (fork-log:138), 438a342 and e625c68 (desk only).
