# Inventory CC-4: CameraController.cpp, CameraSession (port lines 7391-9614)

Stage 1 (inventory, no judgement). Ref `@cinemate-port` = `01f170c` unless stated. Upstream = `@upstream-1.6.0` in `/home/user/wt/core-upstream`.
Diff read completely: `/home/user/build/review/diffs/CC.part04.diff` (1363 lines, 33 hunks).

Scope note: the HINT (controller setters, sanitising, Clear HDR holds, ISO limits, mode ladder hooks) does not match this slice. The slice is
the middle and end of class `CameraSession` (the libcamera session object inside `CameraController.cpp`): `start()` tail, `stop`/`applyControls`/
`startRecording`/`stopRecording`, new public accessors, `configureAndStart`, `makeRequests`, `requeueRequest`, `requestComplete`, `recordRawFrame`.
The outer `CameraController` setters are not in this slice. Only the Clear HDR hold is touched here indirectly (buffer count, `rawCameraBufferCount(clearHdr)`).

Blame of the 2224 lines in scope: 1650 are `35dbe67` (upstream), 574 from 24 port commits.

## 1. Port commits that wrote lines in this slice

| Commit | Subject | Lines in scope | Fork-log status / tests |
| --- | --- | --- | --- |
| `d44b177` | drop-frames (squash of 19: trim, Log, RAM buffer, 90 % safety stop, fps max from sensor, storage pre-roll) | 134 | fork-log:138 "Not yet run on the camera" for the 2026-11-01 merge set; commit msg: host tests on Mac, compiles on Pi, partial earlier run on Pi |
| `80ddac1` | frame-rate phase lock, off by default | 115 | fork-only; "Tested: desk only (servo passes phase_lock_sim.cpp on the Mac; not built)"; fork-log:37 "built 22:04 with 8f7dc39" |
| `caa0153` | imx585 modes from tables, not whitelists | 50 | "Tested: desk only (host tests, Pi -fsyntax-only, node --check)"; fork-log:138 not run on camera |
| `351a3ee` | copy raw frames on a recorder worker | 41 | "Tested: desk only (build and takes on the Pi next)"; fork-log:34 on GitHub |
| `faa2958` | speed ramping behind `fps_speed_ramp` | 39 | tested on Pi 2026-10-28 (C0030-C0032, 1080p uncompressed 25->50->25); fork-log:58 |
| `c48e693` | IMX283 family | 31 | "Tested: desk only"; fork-log:138 not run on camera |
| `6ef0ddc` | `APERTAR_RT_CAPTURE_PRIORITY=N` SCHED_FIFO capture thread | 24 | "syntax-checks with the libcamera block on... Not run on the Pi" (msg); PR #3-#5 set in fork-log:138 |
| `e625c68` | Preview temporal-denoise switch, off by default | 23 | "desk only (not built: no libcamera on the Mac)"; `tools/tuning_tdn_strip_test.cpp` passes on Mac; fork-log:171 "Pi only" |
| `438a342` | survive a yanked/unmounted recording drive (media fault latch) | 20 | fork-log:41 built 22:27, no take test recorded |
| `0b1632f` | pulled CFexpress card seen at once, bounded dead-medium stop | 17 | fork-log:43 built 22:43 |
| `8f7dc39` | `phaseLockStatus` made public | 16 | fork-log:38 |
| `f4a1393` | phase lock pins `{d, d+1}` | 12 | "Tested: desk only"; fork-log:173 "Pi only" |
| `4ab1057` | binning per sensor mode and for the current mode | 11 | fork-log:36 built and running, `list_sensor_modes` + `get_state` verified |
| `8175273` | Clear HDR holds ISO/WB, ISO cap per mode | 10 | tested in preview on Pi 2026-10-28 |
| `ca7b7c2` | experimental stretched WAV after a ramp take | 8 | tested 2026-10-28 (hardware-log) |
| `db17860` | one libcamera request per raw buffer, 8 buffers in Clear HDR | 4 | tested on Pi, 4K Clear HDR 16-bit 10 s takes |
| `d9f00d4` | audio recorder told about a raw frame once queued | 4 | fork-log:35 |
| `94ac68d` | Clear HDR raw streams CPU-cached buffers | 4 | tested on Pi (idle thread 95 % -> 32 %, 25 fps) |
| `114bfb9` | phase-lock history seeded with Core's own pin | 4 | fork-log:40 |
| `4ce382e` | `syncfs` on the clip folder 1/s and at stop | 2 | built 23:07, not tested |
| `26da30e` | media profile (class + filesystem) tunes writer | 2 | built 23:04, not tested |
| `766aba8`, `43a54f3`, `014a2bf` | DONTNEED fix, dma-buf sync as free helper, clip-name templates | 1 each | see fork-log:32, 157, 138 |

## 2. Features touching this slice

| # | Feature (operator terms) | Commits | Regions (port lines) |
| --- | --- | --- | --- |
| F1 | Frame-rate phase lock: servo nudges requested frame duration so a long take stays in step with the audio clock. Off by default. | `80ddac1`, `8f7dc39`, `114bfb9`, `f4a1393` | 7502-7503, 7589-7593, 7777-7783, 8204-8219, 8884-9081 |
| F2 | Speed ramping: FPS can change during a cDNG/MLV take; frames numbered by count, `fps-ramp.txt` log, FreeRun timecode at clip rate, optional stretched WAV. | `faa2958`, `ca7b7c2` | 7594-7634, 7675, 7801-7807, 8900-8904, 9451-9479 |
| F3 | Raw copy on a recorder worker (libcamera thread no longer copies a frame); request released back by the worker; buffers-2 held. | `351a3ee`, `d9f00d4`, `db17860`, `43a54f3`, `94ac68d` | 8381, 8698-8705, 8729-8739, 8822, 8846-8848, 9199-9435 (recordRawFrame), 9482-9516 |
| F4 | Survive a pulled/unmounted recording drive: bounded stop, per-recorder stage timing, medium-gone flag through every recorder, fault class accessor. | `438a342`, `0b1632f`, `4ce382e` | 7760-7814, 8130-8141 |
| F5 | Media profile and CFexpress/filesystem tuning handed to the raw recorder at take start; `syncfs` once a second. | `26da30e`, `4ce382e` | 7734-7735, 7813-7814 |
| F6 | CineMate Log in the DNG files (take plan built at start; quiet applicability probe). | `d44b177` | 7736-7740, 8167-8179 |
| F7 | Storage pre-roll: a throwaway take at the sensor's maximum fps to measure the card; fps override past the sanitiser, exact `{p,p}` pin on every request, frame/timestamp measurement, muted drop warning. | `d44b177` | 7505, 7574-7576, 7820-7911, 9074-9079, 9104, 9507-9513 |
| F8 | FPS ceiling from the sensor probe, backend cap (`fpsceiling::applyBackendCap`, `backendMaximumFps`). | `d44b177` | 8634-8639 |
| F9 | IMX585 modes from tables: colour IMX585 configured explicitly; driver-adjusted modes rejected (raw size, bit depth, `ScalerCropMaximum`). | `caa0153` | 8273-8296, 8485-8530 |
| F10 | IMX283 family: explicit sensor config and exact-mode check, 57 modes. | `c48e693` | 8531-8560, 7461 |
| F11 | Sensor binning known per mode and for the running mode; logged in the "camera configured" line. | `4ab1057` | 8195-8203, 8582, 8646 |
| F12 | Preview temporal-denoise switch: libcamera loads a tuning copy without `rpi.denoise` tdn blocks; active tuning file reported. | `e625c68` | 7401-7440, 8180-8194 |
| F13 | Clear HDR holds ISO/WB: measured analogue gain exposed from session. | `8175273` | 8152-8161 |
| F14 | RT capture thread: optional SCHED_FIFO for libcamera's completion thread. | `6ef0ddc`, `766aba8` | 9109-9133 |
| F15 | Sanitiser takes `monochromeSensor_` as a third argument at all five call sites. | `caa0153` (signature change outside slice, `CameraController.cpp:3502`) | 7443, 7573, 8273, 9614 |
| F16 | Clip folder naming gets the sensor family name. | `014a2bf` | 7642 |

## 3. Interface table (socket commands, state fields, config keys, env vars, files, events, UI)

This slice contains no `handleCommand` branch, no JSON, no HTTP route and no QML/JS. It is the producer side. Surfaces below are the ones the slice feeds or reads.
Consumer lines `@cinemate-port` `ApertarCoreApp.cpp`.

| Kind | Name | Where in slice | Consumer / source | Commit |
| --- | --- | --- | --- | --- |
| socket command (fed) | `set_fps_phase_lock` | `settings_.fpsPhaseLock` read 8903, 7589 | `ApertarCoreApp.cpp:13214` | `80ddac1` |
| socket command (fed) | `set_fps_speed_ramp enabled= [shutter=...]` | `settings.fpsSpeedRamp`, `fpsSpeedRampStretchAudio` 7618-7632, 9451 | `ApertarCoreApp.cpp:13223` | `faa2958`, `ca7b7c2` |
| socket command (fed) | `set_preview_tdn` | `settings.previewTdn` 7309-7320 region, log 7440 | `ApertarCoreApp.cpp:13205` | `e625c68` |
| socket command (fed) | `storage_preroll` / `set_storage_preroll` | `setPrerollTake`, `setPrerollFps`, `waitForFramePeriod`, `prerollMeasure`, `prerollClipFolder`, `prerollFramesWritten/Dropped` (7820-7911) | `ApertarCoreApp.cpp:14603`, `CameraController::startStoragePreroll` `:12051` | `d44b177` |
| socket command (fed) | `list_sensor_modes` | `sensorBinning()` 8195 | `ApertarCoreApp.cpp:12724` | `4ab1057` |
| socket command (fed) | `set_buffer_mode`, `set_clear_hdr` | `rawCameraBufferCount(clearHdr)` 8381, 8736, 8848 | `ApertarCoreApp.cpp:12829`, `:13150` | `db17860`, `d44b177` |
| state field (fed) | `fps_phase_lock_active`, `_err_us`, `_dur_us`, `_pushes`, `_saturated` | `phaseLockStatus()` 8204-8219 | `ApertarCoreApp.cpp:9460-9464` | `80ddac1` |
| state field (fed) | `tuning_file_active` | `activeTuningFile()` 8180-8194 | `ApertarCoreApp.cpp:9527` | `e625c68` |
| state field (fed) | `preview_tdn` | settings | `ApertarCoreApp.cpp:9530` | `e625c68` |
| state field (fed) | `recording_fault` | `recordingFault()` 8130-8141 | `ApertarCoreApp.cpp:9562`, `:12943` | `438a342` |
| state field (fed) | `sensor_binning*` | `sensorBinning()` | `ApertarCoreApp.cpp:12959` | `4ab1057` |
| state / HTTP (fed) | measured analogue gain for Clear HDR hold | `measuredAnalogueGain()` 8152-8161; set at 9157 outside hunks | `CameraController.cpp:11156`, `:11636`, `:12585` | `8175273` |
| state field (fed) | `cdng_log_applicable` path | `cdngLogApplicable()` 8167-8179 | `CameraController.cpp:12511-12519` | `d44b177` |
| event | none added in slice | | | |
| config key | `[media]`/media tune `raw_buffers`, `extra_raw_buffers` | via `rawCameraBufferCount` (defined `:1458`, outside slice) | media tuning file | `26da30e` |
| config key | `[camera] clear_hdr_iso_max_*` | not read in slice; only gain accessor | | `8175273` |
| env var (new, read in slice) | `APERTAR_PHASE_LOCK_KP`, `_KI`, `_DEADBAND_US`, `_CLAMP_US` | 8906-8921 (read once, `static const`) | | `80ddac1` |
| env var (new, read in slice) | `APERTAR_PHASE_LOCK_LOG` | 8971 | | `80ddac1` |
| env var (new, read in slice) | `APERTAR_RT_CAPTURE_PRIORITY` (0-99, default 0) | 9113 | `LimitRTPRIO` on systemd unit; `scripts/start-apertar-core.sh` `APERTAR_RT` is the older whole-process variant | `6ef0ddc` |
| env var (pre-existing, newly referenced) | `APERTAR_RAW_CAMERA_BUFFERS` | `:1469`, used 8381/8736/8848 | | `db17860` |
| env var (pre-existing) | `APERTAR_RAW_CACHED_DMABUF` | 8706 (context line; condition widened for Clear HDR unpacked, `94ac68d`) | | `94ac68d` |
| file on disk | `fps-ramp.txt` in clip folder (written by `writeFpsRampLog`, `:9857`, called at stop 7801) | 7801, 9454 | | `faa2958` |
| file on disk | `<clip>_stretched.wav` (detached `rubberband --fine --timemap`) via `launchAudioStretch` `:9939` | 7803-7807 | needs `rubberband-cli` | `ca7b7c2` |
| file on disk | tuning copy without tdn (`tuning::previewTuningPath`), derived ProRes/log colour tuning | 7401, 7440 | | `e625c68` |
| file on disk | clip folder name (sensor family argument) | 7642 | `DngRecordingQueue::reserveClipFolder` | `014a2bf` |
| stderr log lines | `phase-lock: armed/released/saturated`, `phase-lock stats`, `recording stop: medium gone`, `dead-medium stages ... _ms`, `preview tdn:`, `capture scheduling: SCHED_FIFO`, `binning=N(source)` in "camera configured", `preview_tdn=on/off active=` in "tuning file" | throughout | | various |
| UI element | none in slice | | | |

## 4. Original (upstream) regions modified

Port line = `@cinemate-port`; upstream line = `@upstream-1.6.0` `CameraController.cpp`.

| Region | Port line | Upstream line | Change | Kind | Commits |
| --- | --- | --- | --- | --- | --- |
| `CameraSession::start` default-tuning retry | 7401 | ~5670 | `applyProcessTuningFile(tuningPath)` -> `applyProcessTuningFile(loadablePath(tuningPath))` | extended-in-place | `e625c68` |
| `start` ProRes/log derived tuning | 7428-7432 | ~5690 | `makeProresIspTuning(tuningPath...)` -> `(activePath...)`; `setActiveTuningFile(derivedPath)` | extended-in-place | `e625c68` |
| `start` tuning log line | 7436-7440 | ~5705 | adds `preview_tdn=on` or `preview_tdn=off active=<file>` suffix | behaviour-changed (log text) | `e625c68` |
| `start` sanitise | 7443 | 5376 | `sanitizeSettingsForSensor(settings, family)` -> adds `monochromeSensor_` | extended-in-place | `caa0153` |
| `start` simulate stub | 7461 | ~5740 | `(void)settings` -> `(void)requestedSettings` (parameter rename) | extended-in-place | `c48e693` |
| `stop`/reconfigure teardown | 7502-7505 | ~5765 | releases phase lock and pin; `setPrerollFps(0.0)` | extended-in-place | `80ddac1`, `d44b177` |
| `applyControls` | 7573-7595 | 5495-5530 | third sanitiser arg; pre-roll fps override after sanitise; releases phase lock on fps/phase-lock/photo-mode change; calls `noteFpsChange` on fps change | extended-in-place | `caa0153`, `d44b177`, `80ddac1`, `faa2958` |
| `startRecording` | 7616-7640 | ~5870 | resets ramp state under `rampMutex_`; `reserveClipFolder(..., sensorFamilyName)`; `resolvedAudioOptions.fpsRamp` | extended-in-place | `faa2958`, `014a2bf`, `ca7b7c2` |
| `startRecording` raw branch | 7734-7745 | ~5950 | sets media profile, frame-bytes hint, CDNG log on `recorder_` before `startAtFolder` | extended-in-place | `26da30e`, `d44b177` |
| `stopRecording()` | 7763-7820 | 5658-5680 | signature `stopRecording()` -> `stopRecording(bool mediumGone=false)`; five-line stop sequence rewritten into a timed lambda chain, `setMediumDead`, `stop(mediumGone)`, `writeFpsRampLog`, `launchAudioStretch`, `syncToMedium`, phase-lock stats | rewritten | `438a342`, `0b1632f`, `80ddac1`, `faa2958`, `ca7b7c2`, `4ce382e` |
| `configureAndStart` sanitise | 8273 | 5970 | third sanitiser arg | extended-in-place | `caa0153` |
| `allowAutoSensorConfigFallback` | 8295-8296 | 5993-5995 | drops the `Imx585 && isImx585Raw12CropResolution(...)` clause and the `Imx577` line break; colour IMX585 no longer gets the auto sensor-config fallback | removed / behaviour-changed | `caa0153` |
| preview buffer count | 8381 | 6081 | `kConfiguredBufferCount` -> `rawCameraBufferCount(sanitized.clearHdr)` | behaviour-changed (was fixed 4) | `db17860`, `26da30e` |
| per-candidate acceptance checks | 8485-8560 | after 6180 | two new reject blocks (IMX585 colour, IMX283) before `configuration_ = std::move(candidateConfig)` | extended-in-place (new blocks inside upstream loop) | `caa0153`, `c48e693` |
| `configuredSensorWidth_` block | 8582 | ~6225 | `sensorBinning_ = binningFromProperties(...)` | extended-in-place | `4ab1057` |
| `maxFps` computation | 8634-8639 | 6257-6261 | `maximumSupportedFpsForResolution(...)` wrapped in `fpsceiling::applyBackendCap(..., backendMaximumFps(...))` | behaviour-changed | `d44b177` |
| "camera configured" log | 8646 | ~6270 | adds ` binning=N(source)` | extended-in-place | `4ab1057` |
| before allocator creation | 8698 | ~6400 | `recorder_.clearRawPool()` | extended-in-place | `db17860` (pool API from `351a3ee`) |
| `cachedRaw` condition | 8701-8705 | ~6405 | widened to Clear HDR unpacked | behaviour-changed | `94ac68d` |
| after `makeRequests` | 8729-8739 | ~6420 | `recorder_.setRequestRelease(...)` lambda and `setFrameQueued(...)` lambda | extended-in-place | `351a3ee`, `d9f00d4` |
| `syncCpuReadBuffer` | 8822 | 6426-6437 | 11-line body replaced by one-liner calling free `dmabufCpuSync` (`CameraController.cpp:3750`) | moved | `43a54f3` |
| `makeRequests` limit | 8846-8848 | 6461 | `kActiveRequestCount` (3) -> `rawCameraBufferCount(clearHdr)`; comment added | behaviour-changed (3 -> 4/8/10+ requests) | `db17860` |
| `requeueRequest` tail | 9034-9079 | after 6540 | new block pinning `FrameDurationLimits` for phase lock and pre-roll, after every merge | extended-in-place | `80ddac1`, `f4a1393`, `d44b177` |
| `requestComplete` entry | 9104 | 6590 | `noteFrameForPreroll(request)` | extended-in-place | `d44b177` |
| `requestComplete` priority | 9106-9133 | 6592-6605 | `LimitNICE` comment moved; adds SCHED_FIFO branch before nice fallback | extended-in-place | `6ef0ddc` |
| `requestComplete` before `capturePhotoFrame` | 9168 | ~6640 | `stepFramePhaseLock(request)` | extended-in-place | `80ddac1` |
| `requestComplete` record branch | 9199 | ~6670 | `recordRawFrame(...)` now returns bool; `return` skips `requeueRequest` (worker requeues) | behaviour-changed (request ownership) | `351a3ee` |
| `recordRawFrame` | 9388-9516 | 6853-6955 | `void` -> `bool`; frame index by count when ramp on; ramp metadata/timecode; raw copy block (`acquireRawBuffer`, `copyRawBytes`, `compressClearHdrFrame`, `enqueue`) replaced by `PendingCopy` hand-off to `recorder_.enqueueCopy`; pre-roll first/last timestamps | rewritten | `351a3ee`, `faa2958`, `d44b177`, `d9f00d4` |
| `capturePhotoFrame` sanitise | 9614 | ~7040 | third sanitiser arg | extended-in-place | `caa0153` |

Referenced but outside this slice (defined elsewhere in `CameraController.cpp` or in new headers): `loadablePath` lambda `:7309`, `rawCameraBufferCount` `:1458`, `dmabufCpuSync` `:3750`, `binningFromProperties` `:7090`, `inFpsRampGrace` `:9788`, `noteFpsChange` `:9768`, `stampFpsRampEvents` `:9796`, `pairFpsRampEvents` `:9815`, `writeFpsRampLog` `:9857`, `launchAudioStretch` `:9939`, `noteFrameForPreroll` `:10341`, `buildCdngLogTake` `:4016`, `planCdngLog` `:3974`, `sanitizeSettingsForSensor` `:3502`.

## 5. New abstractions

| Name | What it is | Files | Used by (this slice) | Upstream equivalent |
| --- | --- | --- | --- | --- |
| `FramePhaseLock`, `PhaseLockStatus` | header-only pure PI servo state machine, no I/O | `src/camera/FramePhaseLock.hpp` | `stepFramePhaseLock`, `phaseLockStatus`, `requeueRequest` | none. Upstream has no frame-rate servo; fps is a static pin in `controlsForSettings`. New ground |
| `stepFramePhaseLock` + `phaseLock_`, `phaseLockDurationUs_`, `recentPhaseLockPins_` (16-deep ring), `phaseLockSaturated_`, `lastPhaseErrorUs_` | per-frame hook on the completion thread, holds `controlsMutex_` | `CameraController.cpp:8887` | `requestComplete` | none |
| `PrerollMeasure`, `setPrerollTake`, `setPrerollFps`, `waitForFramePeriod`, `prerollClipFolder`, `prerollFramesWritten/Dropped`, atomics `prerollFpsOverride_`, `prerollPinUs_`, `prerollMeasuring_`, `prerollFrames_`, `prerollFirstUs_`, `prerollLastUs_`, `lastFramePeriodUs_`, `lastEchoedMinUs_`, `completedFrames_` | session half of storage pre-roll: 8 lock-free atomics plus 6 accessors | `CameraController.cpp:7822-7897`, `:10327-10340` | `CameraController::startStoragePreroll` `:12051` | none. Upstream has no pre-roll; media speed test is a separate path (`run_media_speed_test`) |
| `recorder_.setMediaProfile`, `setFrameBytesHint`, `setCdngLog`, `setRequestRelease`, `setFrameQueued`, `clearRawPool`, `enqueueCopy` (`DngRecordingQueue::PendingCopy`), `setPrerollTake`, `syncToMedium`, `stop(bool)`, `fault()`, `folderPath()`, `stats()` | new API on the DNG recording queue; a copy worker thread inside `DngRecordingQueue` | `CameraController.cpp:5043-5110`, `:5671` | `startRecording`, `recordRawFrame`, `configureAndStart` | upstream queue: `acquireRawBuffer` + `enqueue(std::move(buf), view, metadata)` at `@upstream-1.6.0:3548`, `:6932-6950` (copy on libcamera thread) |
| `MediaFault`, `recordingFault()`, `h264Recorder_.setMediumDead`, `audioRecorder_.stop(finalize)` | media-fault classification, dead-medium flag across recorders | `src/util/MediaFault.hpp` | `stopRecording(bool)` | none. Upstream `stop()` takes no arguments (`:5658`) |
| `MediaProfile`, `cachedMediaSnapshotOrProbe`, `MediaProbe` | filesystem/medium class -> writer tuning | `src/util/MediaProfile.hpp`, `src/util/MediaProbe.hpp` | `startRecording`, `rawCameraBufferCount` | none |
| `fpsceiling` namespace (`applyBackendCap`, `resolveSensorMaxFps`, `losslessImx585Fps`, `parseLosslessFpsLimit`) | pure fps-limit helpers | `src/camera/FpsCeiling.hpp` | `configureAndStart` maxFps | upstream: inline `maximumSupportedFpsForResolution` table `@upstream-1.6.0:2629` |
| `apertar::imx585::classFor`, `find`; `Imx283Modes.hpp` | mode tables (S12/S10/H12/H16; 57 IMX283 modes) | `src/camera/Imx585Modes.hpp`, `src/camera/Imx283Modes.hpp` | `configureAndStart` exact-mode checks | upstream: whitelists in `.cpp` (`isImx585Raw12CropResolution` `@upstream-1.6.0:385`) |
| `SensorBinning`, `binningFromProperties`, `sensorBinning_` | binning per mode and current | `CameraController.hpp:48`, `.cpp:7090` | `configureAndStart`, `sensorBinning()` | none |
| `activeTuningFile_` + `activeTuningMutex_`, `setActiveTuningFile`, `loadablePath` lambda | which tuning file libcamera actually loads | `CameraController.cpp:8180-8194`, `:7309` | `start` | upstream tracks `tuningPath` locally only |
| ramp state: `rampMutex_`, `rampEvents_`, `rampStretchAudio_`, `pendingAudioStretch_`, `rampFirstWallClockUs_`, `rampFirstSensorUs_`, `recordingBaseFps_`, `rampMin/MaxFps_`, `rampFrameCount_`, `inFpsRampGrace`, `noteFpsChange`, `stampFpsRampEvents`, `pairFpsRampEvents`, `writeFpsRampLog`, `launchAudioStretch` | speed-ramp bookkeeping; stretch spawns detached `nice -n 15 rubberband` shell | `CameraController.cpp:9768-9990` | `startRecording`, `stopRecording`, `recordRawFrame`, `applyControls`, `stepFramePhaseLock` | none. Upstream has fixed FPS per take |
| `timed` lambda + `stageTimes` ostringstream in `stopRecording` | stage timing for dead-medium stops | `:7788-7800` | | none |

## 6. Removed, narrowed or hidden versus upstream (this slice)

| What | Where | Effect |
| --- | --- | --- |
| Copy of every raw frame on libcamera's completion thread (`acquireRawBuffer` + `copyRawBytes` + `compressClearHdrFrame` + `view` build + `enqueue`) | `recordRawFrame` `@upstream-1.6.0:6932-6950` | moved to a recorder worker; request ownership transfers (see section 4, record branch). No upstream path remains in this function |
| Direct `requeueRequest` after a recorded raw frame | `requestComplete` | when `recordRawFrame` returns true the callback skips requeue; the worker's release lambda requeues (`std::shared_lock` + `running_` check) |
| `kActiveRequestCount` (3 requests in flight) and `kConfiguredBufferCount` (4) as the raw-path counts | `@upstream-1.6.0:1023-1024`, `:6081`, `:6461` | replaced by `rawCameraBufferCount(clearHdr)`; constants still exist, `kActiveRequestCount` no longer used in this slice. Env override `APERTAR_RAW_CAMERA_BUFFERS` (3-16) |
| IMX585 raw12 crop in `allowAutoSensorConfigFallback` | `@upstream-1.6.0:5993-5995` vs `:8295-8296` | colour IMX585 never falls back to automatic sensor config; the new exact-mode check rejects a driver-adjusted mode instead. Mono IMX585 keeps the fallback via `monochromeSensor_` |
| Upstream raw12 crop whitelist `isImx585Raw12CropResolution` in this function | removed from slice; still defined and used elsewhere in port (`CameraController.cpp:394`, `:561`, `:2311`, `:9242`@main) | not removed from file by this slice |
| `LimitNICE=-5` comment position | `requestComplete` | comment retained, moved below the new SCHED_FIFO block; nice -5 path unchanged when env is 0 |
| 11-line `syncCpuReadBuffer` body | `@upstream-1.6.0:6426` | replaced by delegation (no behaviour change) |
| fps ceiling for the configured mode | `@upstream-1.6.0:6257` | now the min of probed/table value and backend cap; `APERTAR_FPS_LIMIT=table` restores table (fork-log:138) |
| `stopRecording()` stop order | `@upstream-1.6.0:5658-5680` | order is now gyro, h264, raw, fps-ramp log, prores, audio (finalise unless medium gone), audio stretch, syncToMedium. Upstream order: gyro, h264, raw, prores, audio |
| Hidden from the operator: pre-roll take drop warning | `dropWarning_.setMuted(preroll)` 7338 | drops during pre-roll are not shown |
| Hidden: raw frames at start of recording are not copied when `hasCapacityForFrame` false | `recordRawFrame` | unchanged semantics, now returns false so the request is requeued by the caller |

## 7. Board assumptions in this slice

| Assumption | Where (port line) | Evidence |
| --- | --- | --- |
| Pi 5 PISP: requested CSI2P format becomes `PISP_COMP1` and reports 16 bit, so the exact-bit-depth check skips it | 8531-8560 (`PixelPacking::PispCompressed1`), 8508-8512 comment "The Pi 5 turns the requested CSI2P format into PISP_COMP1" | confirmed in code; IMX585 and IMX283 blocks |
| Pi 5 CFE (RP1) buffers are uncached, so Clear HDR unpacked frames need CPU-cached DMA heap | 8701-8705 (`94ac68d`) comment "too slow on the CFE's uncached buffers" | confirmed in comment; measured on Pi 5 per commit |
| 8 raw buffers for Clear HDR, `min(16, base+extra)` otherwise | `:1458` via 8381, 8736, 8848 | RAM size not asserted; 16 cap is a number only. Memory-constrained VC4 still referenced in an upstream comment (`:8372`) |
| CLOCK_BOOTTIME is the SensorTimestamp domain, and audio samples are stamped on it | 8895-8897 (`stepFramePhaseLock` comment) | probable: Pi libcamera + Core's ALSA stamping; not board specific |
| "qbc libcamera's IMX585 helper re-chooses the line length (HMAX) for every single-value pin" and "as on Cinemate's libcamera" | 9024-9032 | assumes the Apertar libcamera fork the Pi runs (`/home/user/tiramisioux/libcamera` branch `apertar`); behaviour on stock Raspberry Pi libcamera unconfirmed |
| `ScalerCropMaximum` equals active size x binning, from the driver | 8499-8504 | assumes the Apertar imx585 driver (`imx585-v4l2-driver` `cinemate-port`) reports the window in native pixels |
| IMX283 optical black would show if the pipeline adjusts the size | 8541-8542 | assumes the `imx283-v4l2-driver` transport frame sizes |
| SCHED_FIFO capture needs `LimitRTPRIO` on the systemd unit | 9109-9133 | systemd, not a board property |
| `rubberband-cli` installed | `launchAudioStretch` `:9939` (outside slice), triggered at 7805 | Debian package assumption |
| Four cores, RAM size, gpiochip, I2C bus numbers, fan | none in this slice | confirmed absent |

## 8. Notes for stage 2 (facts only, not judgement)

- Internal vocabulary in comments inside the slice: `T31` (8898, 9451), `request 19` and `hardware-log 2026-10-26` (9024-9032), `kb working/dng-chain, V/H15` (9112), "Cinemate kept them as live keys" (8906), "as on Cinemate's libcamera" (9029), "as Cinemate's profiles do" (`:1462`). Meaningless to the original developer per BRIEF vocabulary.
- Upstream precedent for env overrides read inside the session exists: `APERTAR_RAW_CACHED_DMABUF`, `APERTAR_H264_BACKEND` (context lines 8706, 7724). Upstream precedent for per-frame tuning keys in `apertar-hardware.conf` or `camera_settings.conf` is not shown in this slice.
- `stopRecording` and `startRecording` now touch ten member groups (phase lock, ramp, pre-roll, media profile, CDNG log, audio ramp, medium-dead, stage timing). Single function length: `stopRecording` 7763-7820 vs upstream 5658-5680.
- `requestComplete` lock order: shared `sessionSettingsMutex_`, then `controlsMutex_` in `stepFramePhaseLock` and `requeueRequest`; `requeueRequest` is also called from the ProRes and H.264 release paths without the session-settings lock (comment 9057-9062).
- This slice has no tests of its own. Host tests named in commits: `tools/phase_lock_sim.cpp` (Mac), `tools/tuning_tdn_strip_test.cpp`, fps-ceiling/pre-roll tests (`d44b177`). Pi evidence exists for `351a3ee`-follow-ups (`db17860`, `94ac68d`), `faa2958`, `ca7b7c2`, `8175273`. Phase lock `f4a1393` and `80ddac1` are desk-only plus later hardware-log observation (C0103 flicker, per commit message). IMX585 table (`caa0153`), IMX283 (`c48e693`), preview TDN (`e625c68`), RT priority (`6ef0ddc`) not run on camera per fork-log:138.
