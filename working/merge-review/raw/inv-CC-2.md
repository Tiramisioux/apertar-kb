# inv-CC-2: inventory of `CameraController.cpp`, slice 2

Stage 1 of 3. What the port added or changed here. No verdicts.

## 0. Scope, refs, method

| Item | Value |
| --- | --- |
| Diff read | `/home/user/build/review/diffs/CC.part02.diff`, all 1315 lines, 8 hunks |
| File | `src/camera/CameraController.cpp` |
| New lines covered | 2779-4542 `@port` (the task said 2779-4423; hunk 8 starts at 4423 and runs to 4542) |
| Old lines covered | 2420-3542 `@main` |
| Size | +714 / -73 lines |
| Refs | `@port` = `cinemate-port` `01f170c`; `@main` = fork `origin/main` `f60e301`; `@up` = `upstream-1.6.0` `35dbe67` |
| Short names | `CC` = `src/camera/CameraController.cpp`, `App` = `src/ApertarCoreApp.cpp`, `WCP` = `src/web/WebControlPage.cpp` |
| Blame | `git blame -s` on every added range: 32 port commits (section 9), plus `db17860` for one removal |
| Hint in the task | "CameraSession internals: requests, phase lock, raw copy hand-off". Does not match. No phase-lock code and no `CameraSession` code in this slice (grep `phase` in 2779-4545: no hit). Only the raw copy hand-off's start and stop wiring is here |

What the slice holds: free helpers in the anonymous namespace (resolution normaliser, lossless limits, fps ceilings,
sensor sanitiser, raw crop geometry, Log plan) and the head of `class DngRecordingQueue` (`Stats`, destructor,
`startAtFolder`, `reserveClipFolder`, `stop`).

Who wrote the old side (blame `@main`, confirmed):

| Hunk | Old lines `@main` | Upstream lines | Fork-main lines (earlier Clear HDR / probe work) |
| --- | --- | --- | --- |
| 1 | 2420-2558 | 139 | 0 |
| 2 | 2680-2720 | 21 | 20 (`f60e301`) |
| 3 | 2737-2856 | 92 | 28 (`631721d` 12, `f60e301` 11, `57c8fb0` 3, `9fa7918` 2) |
| 4 | 2949-2996 | 46 | 2 (`631721d`) |
| 5 | 3012-3044 | 33 | 0 |
| 6 | 3226-3245 | 20 | 0 |
| 7 | 3348-3476 | 129 | 0 |
| 8 | 3484-3542 | 59 | 0 |

`CC:2372-2500 @up` is byte-identical to `CC:2430-2558 @main`; `CC:3249-3450 @up` is byte-identical to
`CC:3358-3559 @main` (both checked with `diff`).

## 1. Every changed region

Kinds: E = extended in place, R = rewritten, X = removed, M = moved, B = behaviour changed, N = new code.
Feature ids are in section 2.

| New lines `@port` | Symbol | What changed | Kind | Port commits | Feature |
| --- | --- | --- | --- | --- | --- |
| 2789 | `#endif // APERTARCORE_HAS_LIBCAMERA` | The one big libcamera guard (`CC:1017 @up`) is closed here so the helpers below compile without libcamera | N | `5f5cea2` | F23 |
| 2790-2793 | `normalizedResolutionForSensor` | Two new parameters with defaults: `rawBitDepth = 12`, `clearHdr = false` | E | `caa0153` | F1 |
| 2809-2814 | same, `case Imx283` | New case: a known IMX283 size or generic alias stays, else `normalizedImx283ResolutionForBitDepth(requested, 12)` | E | `c48e693` | F2 |
| 2831-2835 | same, `case Imx585` | 11 lines of alias and whitelist tests (`CC:2405-2415 @up`) replaced by one lookup `imx585ModeForResolution(imx585::classFor(bits, clearHdr), requested)`; `1920x1080` only if the lookup is null | R, B | `caa0153` | F1 |
| 2843-2848 | `isFourKCaptureResolution` | Same two parameters, passed on | E | `caa0153` | F1 |
| 2858-2859 | same, `case Imx283` | `width >= 3840` | E | `c48e693` | F2 |
| 2879 | `isLosslessFourKCapture` | Passes `settings.rawBitDepth`, `settings.clearHdr` | E | `caa0153` | F1 |
| 2892-2893, 2928-2931 | `isoForMeasuredGain` | New: `ceil(gain * 100)`, clamp 50..51200 | N | `e5757d7` | F11 |
| 2894-2926 | `wavSampleRate`, `shellQuote` | New, inside `#if APERTARCORE_HAS_LIBCAMERA` | N | `ca7b7c2`, guard `5f5cea2` | F10 |
| 2933-2984 | `struct CameraSection`, `loadCameraSection` | New reader of `[camera]` in `apertar-hardware.conf` | N | `8175273`, renamed by `97adea0`, comment `bcedbe5` | F3 |
| 2986-3007 | `loadBufferConf` | New reader of the whole hardware file, handed to `bufferbudget::parseBufferConf` (`[storage]`) | N | `d44b177`, guard `5f5cea2` | F14, F16 |
| 3009-3014 | `cameraSection` | New: `static const CameraSection`, read once per process | N | `8175273`, `97adea0` | F3 |
| 3016-3023 | `clearHdrIsoCap` | New: 0 when Clear HDR is off, else the 12-bit or 16-bit cap | N | `6d217c7` | F3, F4 |
| 3025-3032 | `applyClearHdrCompression` | New: Clear HDR on -> uncompressed, off -> lossless JPEG (cDNG only, on a change) | N | `f2ebe6e` | F8 |
| 3034-3049 | `applyRungFormat` | New: writes a ladder rung's compression into `recordingFormat`, `cdngCompression`, `lossyDngRatio` | N | `3cae990` | F9 |
| 3051-3059 | `compressionLabel` | New: "Lossy 5:1", "Lossy 3:1", "MLV", "Lossless JPEG", "Uncompressed" | N | `e16033e` | F9 |
| 3061-3067 | `kLadderOwnsMode`, `kLadderOwnsCompression` | New message constants | N | `09256a7`, `3cae990` | F9 |
| 3069-3096 | `enforceClearHdrExposureRules` | New: in Clear HDR auto ISO and auto WB go off, flags remember them, ISO is capped; in SDR the flags turn auto back on | N | `8175273`, `6d217c7` | F3 |
| 3098-3100 | `kLosslessMaxIso = 1600` | Replaces the literal `800u` (`CC:2483 @up`) | B | `2f43ecc` | F5 |
| 3102-3111 | `losslessCaptureLimited` | The early-return test of `enforceLosslessCaptureLimits` (`CC:2472-2481 @up`) as its own predicate | M | `6d217c7` | F4 |
| 3113 | forward declaration of `modeMaximumFps` | New | N | `d44b177` | F5 |
| 3115-3130 | `losslessFpsOverride` | New: `APERTAR_LOSSLESS_FPS_LIMIT`, read once, logs to stderr | N | `d44b177` | F5 |
| 3132-3144 | `losslessMaximumFps` | The fps part of `enforceLosslessCaptureLimits` (`CC:2485-2489 @up`) as its own function; IMX585 value `30.0` replaced by `fpsceiling::losslessImx585Fps(modeMaximumFps(...), losslessFpsOverride())` | M, B | `97adea0`, `d44b177` | F4, F5 |
| 3146-3158 | `enforceLosslessCaptureLimits` | Body rewritten on the helpers above; `isoAuto = false` only when the sensor is not an IMX585 | R, B | `6d217c7`, `b5b787e`, `97adea0` | F4, F5 |
| 3160-3168 | `maximumIsoForSettings` | New: lower of the Clear HDR cap and the lossless cap, 0 = none | N | `6d217c7` | F4 |
| 3309-3311 | `sensorModesProbed` | Wrapped in `#if APERTARCORE_HAS_LIBCAMERA` (fork-main code, `f60e301`) | E | `5f5cea2` | F23 |
| 3329 | `tableMaximumFpsForResolution` | Passes bit depth and Clear HDR to the normaliser | E | `caa0153` | F1 |
| 3332-3339 | same, `case Imx283` | New case: `imx283::floorFps(bits, w, h)` | E | `c48e693` | F2 |
| 3376-3381 | same, `case Imx585` | `3840x2160` test becomes `height == 2160` (any width); every other size returns 60 (was: two whitelist tests, then `break` to 120) | R, B | `caa0153` | F1 |
| 3389-3395 | `imx283ProbeFpsOnly` | New: `APERTAR_IMX283_PROBE_FPS`, read once | N | `c48e693` | F2 |
| 3397-3408 | `fpsLimitTableOnly` | New: `APERTAR_FPS_LIMIT=table`, read once, logs to stderr | N | `d44b177` | F6 |
| 3410-3423 | `maximumSupportedFpsForResolution` | `probed ? min(table, *probed) : table` (`CC:2769 @main`, fork-main code) replaced by `fpsceiling::resolveSensorMaxFps(probed, table, minWithTable)`: the probe alone by default, `min` for the IMX283 or with the env | B | `d44b177`, `c48e693` | F6, F2 |
| 3425-3434 | `backendMaximumFps` | New hook; returns `std::nullopt` for every input (the 25 fps cap it held was removed) | N | `d44b177`, `31d5418` | F6 |
| 3447 | `supportedRawBitDepthForSensor` | `case Imx283` joins the IMX294 case (10 or 12 bit) | E | `c48e693` | F2 |
| 3464-3479 | `modeMaximumFps` | The fps ceiling lines of the sanitiser (`CC:2732-2739 @up`) as their own function, plus `applyBackendCap` | M | `97adea0`, `d44b177`, `bcedbe5` | F4 |
| 3481-3491 | `prerollMaximumFps` | New: sensor maximum plus back-end cap, no lossless cap | N | `d44b177` | F7 |
| 3493-3500 | `maximumFpsForSettings` | New: `min(mode, lossless)` | N | `97adea0` | F4 |
| 3502-3503 | `sanitizeSettingsForSensor` | New parameter `monochromeSensor = false` | E | `caa0153` | F1 |
| 3526-3531 | same | The normaliser call moves below the bit-depth step (was `CC:2723 @up`, before it); fork-main's "Clear HDR forces 3840x2160" (`CC:2824-2827 @main`) now applies to a monochrome IMX585 only | B | `caa0153` | F1 |
| 3532 | same | Calls `enforceClearHdrExposureRules` | E | `8175273` | F3 |
| 3536-3543 | same | IMX283 block: size per bit depth; ProRes capped to 3840x2160 | E | `c48e693` | F2 |
| 3545 | same | `maxFps` comes from `modeMaximumFps` | M | `97adea0` | F4 |
| 3552 | `#if APERTARCORE_HAS_LIBCAMERA` | Guard reopened before `parseSizeEnv` | N | `5f5cea2` | F23 |
| 3665, 3670-3671 | `shouldUseRequestedActiveRawCrop` | IMX283 added to both family tests | E | `c48e693` | F2 |
| 3692-3697 | `activeRawLeftPixelsForConfiguredStream` | IMX283: left offset = `configuredWidth - width` (not centred) | E | `c48e693` | F2 |
| 3733-3735 | `activeRawTopRowsForConfiguredStream` | IMX283: top offset 0 | E | `c48e693` | F2 |
| 3749-3760 | `dmabufCpuSync` | Body of `CameraSession::syncCpuReadBuffer` (`CC:6426-6436 @up`) as a free function; the member now forwards (`CC:8822 @port`) | M | `43a54f3` | F20 |
| 3963-4014 | `struct CdngLogPlan`, `planCdngLog` | New: decides whether the take can carry Log, and its source depth, target depth, black, white | N | `d44b177` | F12 |
| 4016-4044 | `buildCdngLogTake` | New: builds the take's tables, logs one line | N | `d44b177` | F12 |
| 4168, 4188 | guard closed and reopened | So `FrameBufferGauge` compiles without libcamera | N | `5f5cea2` | F23 |
| 4169-4186 | `struct FrameBufferGauge`, `frameBufferGauge()` | New: five atomics behind a function-local static | N | `d44b177` | F13 |
| 4198-4199 | `DngRecordingQueue::Stats` | `discardedOnFailure`, `skippedAfterFailure` | E | `438a342` | F19 |
| 4202-4204 | same | `ramMode`, `peakQueueBytes`, `queueBudgetBytes` | E | `d44b177` | F14 |
| 4211 | `~DngRecordingQueue` | `unregisterFlushAbort()` | E | `c5db8b2` | F15 |
| 4228-4235 | `startAtFolder` | Refuses the take while writers of the previous take are still blocked | E, B | `0b1632f` | F19 |
| 4238 | same | `cdngLog_ = std::move(nextCdngLog_)` | E | `d44b177` | F12 |
| 4246, 4248-4253 | same | Stall clock and fault latches reset | E | `a3ac8da`, `438a342` | F19 |
| 4269, 4331-4333, 4390 | same | Writes the gauge | E | `d44b177` | F13 |
| 4271 | same | `registerFlushAbort()` | E | `c5db8b2` | F15 |
| (old 3417-3418 `@main`) | same | `pooledRawBytes_ = 0; expectedRawBufferSize_ = 0;` removed | X | `db17860` | F21 |
| 4285-4313 | same | Frames per folder: env, else `[storage]`; makes `part_000` and the `.parts` marker | E | `d7dd337` | F16 |
| 4316-4321 | same | `normalWorkerCount` renamed `formatWorkerCount`; the uncompressed worker count now comes from `APERTAR_CDNG_UNCOMPRESSED_WORKERS`, else `min(profile workers, format count)` | E, B | `26da30e` | F17 |
| 4325-4327 | same | Default queue depth for uncompressed takes: the media profile's, else 12 | E, B | `26da30e` | F17 |
| 4330 | same | `planQueueBuffer()` | E | `d44b177` | F14 |
| 4338 | same | Lossless fallback uses `formatWorkerCount` (keeps the upstream value) | E | `26da30e` | F17 |
| 4352 | same | `warmRawPool()` | E | `4abbef0` | F21 |
| 4353-4377 | same | Sync thread: `APERTAR_MEDIA_SYNC_MS`, else the media tuning file, else 1000; opens the clip folder; warning for `APERTAR_DNG_DONTNEED=sync` without it | E | `4ce382e`, `5b68f1f`, `2edc6d0`, `48f8b8c`, `0ed07ea` | F18 |
| 4378-4379 | same | Writers start through `spawnWorker` (was `workers_.emplace_back(&workerLoop, this)`, `CC:3349-3350 @up`) | R | `4ce382e`, `5b68f1f` | F18, F19 |
| 4380-4388 | same | Copy workers start: `APERTAR_RAW_COPY_WORKERS` (1..2) | E | `351a3ee` | F20 |
| 4397-4405 | same | The `recording clip:` line gains `media_class= media_fs= dontneed= writeback= sync_ms= tune_override= frames_per_folder=` | E | `26da30e`, `48f8b8c`, `2edc6d0`, `d7dd337` | F17, F18, F16 |
| 4433-4436 | `reserveClipFolder` | Third parameter `sensor`, passed to `allocateClipFolder` | E | `014a2bf` | F22 |
| 4439-4449 | `stop` | Signature `stop(bool mediumDead = false)`; sets `mediumGone_` | E | `438a342` | F19 |
| 4452-4453 | same | Gauge off; `stopCopyWorkers()` | E | `d44b177`, `351a3ee` | F13, F20 |
| 4460-4499 | same | `join` of all writers (`CC:3405-3408 @up`) replaced by a bounded wait, a stall test and `detach()` of stuck writers | R, B | `0b1632f`, `a3ac8da` | F19 |
| 4502 | same | `trimRawPoolToIdle()` | E | `4abbef0` | F21 |
| 4503-4506 | same | Closes the sync folder descriptor (only when every thread was joined) | E | `4ce382e` | F18 |
| 4507-4512 | same | `LossyDngEncoder::abandonWrites()` on a gone medium, else `drainWrites()` | E | `438a342` | F19 |
| 4516-4532 | same | The `recording stats:` line gains `discarded_on_failure= skipped_after_failure= dropped_copy_slot= fault=` and, in ram mode, `queue_bytes_peak= queue_budget=` | E | `438a342`, `0ed07ea`, `d44b177` | F19, F20, F14 |

## 2. Features that touch this unit

"Relation" uses the four fixed phrases. "Tested" is what the commit message and the KB record, not a verdict.

| Id | Feature | Operator gets | Relation to upstream | Commits | Tested (source) |
| --- | --- | --- | --- | --- | --- |
| F1 | IMX585 modes from tables | Every size the IMX585 driver offers per class (SDR 12, SDR 10, Clear HDR 12, Clear HDR 16); Clear HDR in crops, not only 4K | replaces upstream code | `caa0153` | Desk only (commit). Fork-log row `d44b177`: "Not yet run on the camera" at merge time |
| F2 | IMX283 sensor family | An IMX283 is recognised and its 57 modes can be chosen | extends an upstream function in place | `c48e693` | Desk only (commit). `lessons/hardware-log.md:1077-1093`: the sensor probes on a CM5; no Core take with it recorded |
| F3 | Clear HDR exposure rules | In Clear HDR auto ISO and auto WB switch off at their measured values and come back in SDR; ISO stops at 720 (12-bit) or 1585 (16-bit) | adds a parallel path beside upstream code | `8175273`, `6d217c7` | Pi preview 2026-10-28 (commit; `hardware-log.md:523`) |
| F4 | `iso_max` and `fps_max` in the state | Both UIs cut their ISO and FPS lists where Core would clamp | extends an upstream function in place | `6d217c7`, `97adea0`, `bcedbe5` | `iso_max` read on the Pi 2026-10-28 (`hardware-log.md:549-551`); `fps_max` "tested 2026-10-28 (Patrik)" (`fork-log.md:74`) |
| F5 | Lossless cDNG limits relaxed | Lossless cDNG takes ISO up to 1600, keeps auto ISO on the IMX585, and runs to the mode's own fps maximum on the IMX585 | replaces upstream code | `2f43ecc`, `b5b787e`, `d44b177` | ISO 1600: "tested 2026-10-28 (Patrik)" (`fork-log.md:80`). Auto ISO: built, "unverified" (`fork-log.md:85`). Fps: host test; 60 fps 4K 12-bit lossless measured in a pre-roll (`hardware-log.md:842-845`) |
| F6 | Max fps from the sensor probe | The highest selectable fps is what the sensor reports (4K SDR 60, was 30) | replaces upstream code (fork-main's `min(table, probed)`) | `d44b177`, `31d5418` | Host test (`tools/fps_ceiling_test.cpp`); `31d5418` desk only, built on the Pi 2026-11-03 (`fork-log.md:147`) |
| F7 | Storage pre-roll | A 2 s test take at the mode's highest fps warms the drive at start, card insert, format, or on demand | entirely new area | `d44b177` | Pi 5, 2026-11-01 (`hardware-log.md:842-853`) |
| F8 | Clear HDR picks the compression | Switching Clear HDR on sets uncompressed cDNG, switching it off sets lossless | adds a parallel path beside upstream code | `f2ebe6e` | Desk only; "built 2026-10-28" (`fork-log.md:89`) |
| F9 | Mode Ladder helpers | With the ladder on, the FPS picks resolution, bit depth, Clear HDR and compression; manual changes of those are refused with a message | entirely new area | `3cae990`, `e16033e`, `09256a7` | Desk only, host test (commits). Ladder core `0041ba0`: "tested 2026-10-28 (socket, two takes, presets)" (`fork-log.md:87`) |
| F10 | Stretched WAV after a speed-ramp take | A second WAV, `<clip>_stretched.wav`, follows the slow motion with its pitch kept | entirely new area | `ca7b7c2` | Pi 2026-10-28 (`hardware-log.md:537-556`) |
| F11 | ISO lock at the measured gain | Switching auto ISO off keeps the picture's brightness (no step down one gain code) | adds a parallel path beside upstream code | `e5757d7` | Pi 2026-10-28 (commit) |
| F12 | Log in the files ("CineMate Log") | One Log switch stores cDNG and Lossy DNG one bit-depth step lower through a log curve (about 25 % smaller at 16 to 12) | entirely new area | `d44b177` | Pi 2026-10-31: 16 to 12, one frame 12,451,344 bytes; not opened in Resolve (`hardware-log.md:813-823`) |
| F13 | Write-buffer level | A red bar in the REC pill shows how full the write queue is | adds a parallel path beside upstream code | `d44b177` | Pi 2026-10-31: state fields present, `/api/buffer` answered (`hardware-log.md:817-819`) |
| F14 | Frames / RAM write queue, safety stop | A large RAM queue can replace the 12-frame queue; at 90 % full the take ends cleanly | extends an upstream function in place | `d44b177` | Pi 5, 2026-11-01: first safety stop at 1289 of 1424 MiB (`hardware-log.md:871-874`) |
| F15 | Record during a safety-stop flush | Pressing record while the buffer empties drops the queued frames and starts the new take at once | adds a parallel path beside upstream code | `c5db8b2` | No `Tested:` line. "read from code, untested on the camera" (`hardware-log.md:875`) |
| F16 | Split takes into part folders | Long takes can be written as `part_000`, `part_001` ... inside the clip folder | extends an upstream function in place | `d7dd337` | Desk (host tests) and Pi build rc 0 (commit); the camera runs with `frames_per_folder=0` (`fork-log.md:181-182`) |
| F17 | Writer tuned per recording medium | Nothing to operate; workers and queue depth follow the filesystem and a tuning file | extends an upstream function in place | `26da30e`, `2edc6d0` | `26da30e`: "built 23:04, not tested" (`fork-log.md:46`). `2edc6d0`: built, "Core not restarted yet" (`fork-log.md:142`) |
| F18 | Take durability (sync thread) | A pulled card or a crash keeps the take up to about one second before it | adds a parallel path beside upstream code | `4ce382e`, `5b68f1f`, `0ed07ea`, `48f8b8c` | Pi pull test C0011: 258 of 281 frames readable (`fork-log.md:53`) |
| F19 | Dead-medium handling in the DNG queue | Pulling the recording card ends the take within seconds instead of hanging Core | replaces upstream code (`stop()`'s join) | `438a342`, `0b1632f`, `a3ac8da` | Pi 5 (4 GB), card pulls 2026-10-26 (`hardware-log.md:327-371`) |
| F20 | Raw copy on a recorder worker | Fewer capture gaps in 16-bit Clear HDR takes | adds a parallel path beside upstream code | `43a54f3`, `351a3ee`, `0ed07ea` | Pi 5 (4 GB), `351a3ee`, 4K Clear HDR 16-bit takes (`hardware-log.md:137`) |
| F21 | Raw copy pool warmed and kept | Nothing to operate | extends an upstream function in place | `db17860`, `4abbef0` | `db17860`: Pi takes (commit). `4abbef0`: syntax check only, "Not built or run on the Pi" (commit); no fork-log row |
| F22 | Composable clip names | The sensor name can be part of the clip folder name | extends an upstream function in place | `014a2bf` | No `Tested:` line; no test recorded for this commit |
| F23 | Build without libcamera | Nothing to operate (developer build, `--simulate`) | extends an upstream function in place | `5f5cea2` | Commit: compiled code unchanged with libcamera. Fork-log row `d44b177`: Pi build with libcamera ON and OFF |

`d44b177` is one squash of 19 commits. Blame cannot split F6, F7, F12, F13, F14 inside it.

## 3. Surface

Evidence is `@port` unless marked. Most of these names are parsed and emitted in other units (`App`, `WCP`, the touch
UI). The last column says which code of this slice they depend on.

### 3.1 Socket commands and HTTP routes

| Name | New or changed | Where | Link to this slice |
| --- | --- | --- | --- |
| `set_iso_auto` | changed (exists `@up`) | `App:12995`, `CC:11146-11174` | `enabled=false` locks at `isoForMeasuredGain` (`CC:11162`); refused in Clear HDR (`CC:11167-11169`) |
| `set_wb_auto` | changed (exists `@up`) | `App:13036`, `CC:11300` | Refused in Clear HDR; the rule is `enforceClearHdrExposureRules` |
| `set_iso` | changed (exists `@up`) | `App:12968` | Clamped by `clearHdrIsoCap` and `kLosslessMaxIso` in the sanitiser |
| `set_clear_hdr` | changed (exists `@main`, not `@up`) | `App:13150`, `CC:11615-11664` | Calls `applyClearHdrCompression` (`CC:11631`) and `isoForMeasuredGain` (`CC:11637`) |
| `set_resolution` | changed (exists `@up`) | `App:13042`, `CC:10643-10646` | Refused with `kLadderOwnsMode` while the ladder is active |
| `set_raw_bit_depth` | changed (exists `@up`) | `App:13135`, `CC:11577-11580` | Same message |
| `set_cdng_compression` | changed (exists `@up`) | `App:13068`, `CC:11400-11403` | Refused with `kLadderOwnsCompression` |
| `set_lossy_dng_ratio` | changed (exists `@up`) | `App:13089`, `CC:11448-11451` | Same |
| `set_record_format` | changed (exists `@up`) | `App:13054`, `CC:11322-11326` | cDNG to or from Lossy DNG refused with `kLadderOwnsCompression` |
| `set_fps` | changed (exists `@up`) | `App:13003` | Ceiling from `modeMaximumFps` and `losslessMaximumFps` |
| `get_mode_ladder`, `set_mode_ladder` | new | `App:14090`, `App:14093` | `applyRungFormat` (`CC:10766, 10838, 10882`), `compressionLabel` (`CC:10911-10935`) |
| `set_cdng_log` | new | `App:13079` | `planCdngLog`, `buildCdngLogTake` |
| `set_buffer_mode` | new | `App:12829` | `loadBufferConf` reads the key at the next take (`CC:5505`) |
| `set_frames_per_folder`, `set_clip_merge` | new | `App:12857-12858` | `loadBufferConf` at take start (`CC:4297`) |
| `storage_preroll`, `set_storage_preroll` | new | `App:12591`, `App:14603`, `App:12900` | `prerollMaximumFps` (`CC:12044, 12078`) |
| `set_fps_speed_ramp audio=real\|stretch` | new | `App:13223` | `wavSampleRate`, `shellQuote` in `launchAudioStretch` (`CC:9939-9999`) |
| `set_clip_name_template`, `preview_clip_name` | new | `App:13241`, `App:13258` | `reserveClipFolder(..., sensor)` (`CC:7642`) |
| `record_start` | changed (exists `@up`) | `CC:4228-4235` | Can now fail with "The previous take's writers are still blocked on the removed medium (N). Try again in a moment." |
| `GET /api/buffer` | new | `App:8419-8422` | `frameBufferGauge()` through `frameBufferStatus()` (`CC:12525-12552`) |

### 3.2 State fields and events

| Field or event | Where emitted | Source in this slice |
| --- | --- | --- |
| `iso_max` | `CC:176`, `App:324`, `App:9488` | `maximumIsoForSettings` (`CC:3162`), called at `CC:12589`, `CC:12863` |
| `fps_max` | `CC:177`, `App:325`, `App:9489` | `maximumFpsForSettings` (`CC:3495`), called at `CC:12590`, `CC:12864` |
| `iso_auto_after_clear_hdr`, `wb_auto_after_clear_hdr` | `CC:187`, `CC:199`, `App:335`, `App:347`; persisted `CC:945`, `CC:956`; loaded `CC:823`, `CC:845` | `enforceClearHdrExposureRules` |
| `cdng_log`, `cdng_log_bits`, `cdng_log_available`, `cdng_log_applied` | `CC:207-210` | `planCdngLog` through `cdngLogApplicable` (`CC:8168-8178`) |
| `buffer_used`, `buffer_capacity`, `buffer_fill`, `buffer_mode`, `buffer_unit` | `App:304-308` | `FrameBufferGauge` |
| `buffer_flush_discarded` | `App:259` | Flush abort registered at `CC:4271` |
| `frames_per_folder`, `frames_per_folder_env` | `App:265-266` | Same keys read at `CC:4293-4297` |
| `media_class`, `media_profile` | `App:9560-9561` | `mediaProfile_` used at `CC:4321`, `CC:4327` |
| `media_state`, `media_alive`, `recording_fault` | `App:9555-9562` | Fault latches reset at `CC:4248-4250`; `stop(mediumDead)` |
| `ladder_text` | `CC:185`, `App:333` | `compressionLabel` |
| `storage_preroll_active`, `storage_preroll_fps`, `storage_preroll_last` | `App:260-264` | `prerollMaximumFps` |
| `fps_speed_ramp_stretch_audio` | `CC:233`, `App:371` | Gate for `launchAudioStretch` |
| event `buffer` | `App:10837`, `App:10986-11009` | `frameBufferStatus()` |
| settings event | `CC:12857-12864` | Now carries `iso_max`, `fps_max` |

### 3.3 Config keys, env vars, files, programs

| Kind | Name | Default and range | Read at | Where | Commit |
| --- | --- | --- | --- | --- | --- |
| Config key | `apertar-hardware.conf:[camera] clear_hdr_iso_max_12bit` | 720; 0..51200, 0 = no cap | Core start (`static`) | `CC:2976-2977`; template `App:5074-5078` | `8175273` |
| Config key | `apertar-hardware.conf:[camera] clear_hdr_iso_max_16bit` | 1585; same range | Core start | `CC:2978-2979`; template `App:5079` | `8175273` |
| Config key | `apertar-hardware.conf:[storage] frames_per_folder` | 0; 0 or 100..100000 | Each take | `CC:4297` through `loadBufferConf`; `src/util/BufferBudget.hpp:99-107` | `d7dd337` |
| Config key | `apertar-hardware.conf:[storage] buffer`, `buffer_ram_fraction`, `buffer_ram_floor_mb`, `buffer_ram_max_fraction`, `buffer_stop_percent`, `clip_merge` | `frames`, 0.6, 512, 0.5, 90 in ram mode and 0 in frames mode (`BufferBudget.hpp:198-199`), `on` | Each take (`CC:5505`) and in the App (`App:276`) | `loadBufferConf` `CC:2989-3006`; template `App:5051-5065` | `d44b177`, `ba0658d` |
| Config key | `apertar-media-tune.conf: sync_ms` | 1000; 0..60000 | Each take | `CC:4364-4365`; `src/util/MediaTune.hpp:27-28` | `2edc6d0` |
| Config key | `apertar-media-tune.conf: workers`, `queue` | per filesystem | Media change | `CC:4321`, `CC:4327` through `mediaProfile_` | `2edc6d0` |
| Env var | `APERTAR_HARDWARE_CONFIG` | upstream variable; two new read sites | Core start, each take | `CC:2946`, `CC:2992` | `8175273`, `d44b177` |
| Env var | `APERTAR_LOSSLESS_FPS_LIMIT` | unset; a number > 0 | Once | `CC:3120` | `d44b177` |
| Env var | `APERTAR_IMX283_PROBE_FPS` | false | Once | `CC:3393` | `c48e693` |
| Env var | `APERTAR_FPS_LIMIT` | unset; `table` | Once | `CC:3401` | `d44b177` |
| Env var | `APERTAR_CDNG_FRAMES_PER_FOLDER` | unset; 0 or 100..100000 | Each take | `CC:4293` | `d7dd337` |
| Env var | `APERTAR_CDNG_UNCOMPRESSED_WORKERS` | profile or format count; 1..8 | Each take | `CC:4320` | `26da30e` |
| Env var | `APERTAR_MEDIA_SYNC_MS` | 1000; 0..60000, 0 = off | Each take | `CC:4365` | `4ce382e` |
| Env var | `APERTAR_RAW_COPY_WORKERS` | 1; 1..2 | Each take | `CC:4386` | `351a3ee` |
| Env var | `APERTAR_DEAD_MEDIUM_STOP_MS` | 2000; 100..600000 | Each stop | `CC:4469` | `0b1632f` |
| Env var | `APERTAR_DNG_DONTNEED` | `sync` | Once (`src/cdng/CdngEncoder.cpp:84-104`) | Used at `CC:4370`, `CC:4399-4401` | `0ed07ea` |
| Env var | `APERTAR_WRITE_STALL_MS` | 5000 | Each test (`CC:4859-4861`) | Used at `CC:4476` | `a3ac8da` |
| Env var | `APERTAR_CDNG_QUEUE_FRAMES`, `APERTAR_CDNG_WORKERS`, `APERTAR_LOSSYDNG_WORKERS`, `APERTAR_CDNG_WORKER_NICE` | upstream, unchanged names | - | `CC:4329`, `CC:4346`, `CC:4348`, `CC:4407` | - |
| File | `<clip>/part_NNN/` folders | - | Take start (`part_000`) | `CC:4299-4310`; `src/cdng/FramePath.hpp:51-57` | `d7dd337` |
| File | `<clip>/.parts` | text: `frames_per_folder=N`, `pattern=<clip>_%09d.dng` | Take start | `CC:4311-4312`; `FramePath.hpp:25` | `d7dd337` |
| File | `<clip>/<clip>_stretched.wav`, `<clip>_stretched.partial.wav`, `<tmp>/apertar-stretch-<clip>.map` | - | After a ramp take | `CC:9953-9974` (uses the slice's helpers) | `ca7b7c2` |
| File | `/home/pi/apertar-media-tune.conf`, `/run/apertar-media/media-tune.override.conf` | - | Each take for `sync_ms` | `MediaTune.hpp:27-28` | `2edc6d0` |
| Program | `rubberband` (package `rubberband-cli`), through `/bin/sh -c`, double fork | - | After a ramp take | `CC:9977-9999` | `ca7b7c2` |
| Log line | `ApertarCore recording clip:` | 7 new fields | Take start | `CC:4397-4405` | several |
| Log line | `ApertarCore recording stats:` | 4 new fields, 2 more in ram mode | Take stop | `CC:4519-4531` | several |
| Log line | `ApertarCore CineMate Log: ...` | new | Take start | `CC:3985`, `CC:4008`, `CC:4041` | `d44b177` |
| Log line | `ApertarCore lossless fps limit: ...`, `ApertarCore fps limit: ...` | new | Once | `CC:3123-3126`, `CC:3404` | `d44b177` |

### 3.4 UI elements that read this slice's values (owned by other units)

| Element | Where | Reads |
| --- | --- | --- |
| WebUI ISO and FPS pills cut at the ceiling | `WCP:7472-7486`, `WCP:8661-8674`, `WCP:13804-13805`, `WCP:13919-13920` | `iso_max`, `fps_max` |
| WebUI buffer mode pills, buffer bar option | `WCP:4919-4924`, `WCP:5280`, poll `WCP:16497` | `buffer_*`, `GET /api/buffer` |
| WebUI Log switch | `WCP:9789-9790`, `WCP:15451` | `cdng_log*`, `set_cdng_log` |
| WebUI Mode Ladder card (pane `modes`) | `WCP:5151-5166`, running line `WCP:8421` | `ladder_text` |
| WebUI frames-per-folder field | `WCP:16192-16193` | `frames_per_folder` |
| Touch UI bridge properties `isoMax`, `fpsMax`, `bufferFill`, `cdngLogBits` | `Apertar-UI/src/ApertarControlBridge.hpp:19-20, 62, 78`; `ApertarControlBridge.cpp:1592-1594, 2696-2698` | `iso_max`, `fps_max`, `buffer` event, `cdng_log_bits` |
| Touch UI buffer bar | `Apertar-UI/qml/CameraPage.qml:2704` | `bufferFill` |

## 4. Original code modified

"Origin" says who wrote the touched code: upstream 1.6.0 or the fork-main commits on top of it.

| # | Region | Origin, where | Change | Kind |
| --- | --- | --- | --- | --- |
| 1 | `normalizedResolutionForSensor` signature | upstream, `CC:2372 @up` | Two defaulted parameters added | extended-in-place |
| 2 | `normalizedResolutionForSensor`, IMX585 case | upstream, `CC:2404-2416 @up` | Alias and whitelist chain replaced by a table lookup in `src/camera/Imx585Modes.hpp`; an unknown size now takes the nearest row of the class, not `1920x1080` | rewritten |
| 3 | `isFourKCaptureResolution`, `isLosslessFourKCapture` | upstream, `CC:2424-2458 @up` | Bit depth and Clear HDR passed through; IMX283 case | extended-in-place |
| 4 | `enforceLosslessCaptureLimits` | upstream, `CC:2470-2491 @up` | Split into `losslessCaptureLimited`, `losslessMaximumFps`, `kLosslessMaxIso`; body rebuilt on them | rewritten |
| 5 | Lossless ISO cap | upstream, `CC:2483 @up` (`800u`) | 1600 | behaviour-changed |
| 6 | Lossless forces manual ISO | upstream, `CC:2484 @up` (`settings.isoAuto = false`) | Not applied on the IMX585 | behaviour-changed |
| 7 | Lossless fps cap on the IMX585 | upstream, `CC:2485-2486 @up` (`30.0`) | The mode's own maximum, or `min(env, mode max)` | behaviour-changed |
| 8 | `tableMaximumFpsForResolution`, IMX585 case | upstream table `CC:2669-2677 @up`, Clear HDR line by fork main `CC:2747-2749 @main` | Keyed on `height == 2160`; fallback 60 instead of 120 | rewritten |
| 9 | `maximumSupportedFpsForResolution` | fork main, `CC:2763-2770 @main` (`f60e301`) | `min(table, probed)` becomes "probe wins"; table only without a probe value, for the IMX283, or with `APERTAR_FPS_LIMIT=table` | behaviour-changed |
| 10 | `supportedRawBitDepthForSensor` | upstream `CC:2685-2705 @up` (Clear HDR parameter by fork main) | IMX283 label | extended-in-place |
| 11 | `sanitizeSettingsForSensor` signature | upstream, `CC:2707 @up` | `monochromeSensor = false` added; 11 of the 13 call sites pass it (`CC:7443 ... 11644 @port`; `CC:10556` and `CC:12784` use `SensorFamily::Unknown` and the default) | extended-in-place |
| 12 | `sanitizeSettingsForSensor`, order | upstream, `CC:2723-2727 @up` | Resolution is normalised after the bit depth (was before) | behaviour-changed |
| 13 | `sanitizeSettingsForSensor`, Clear HDR size | fork main, `CC:2824-2827 @main` (`57c8fb0`) | "Clear HDR forces 3840x2160" kept only for a monochrome IMX585 | behaviour-changed |
| 14 | `sanitizeSettingsForSensor`, fps ceiling | upstream, `CC:2732-2739 @up` | Lines moved into `modeMaximumFps` | moved |
| 15 | `shouldUseRequestedActiveRawCrop`, left and top offsets | upstream `CC:2851-2925 @up` (`imx585Clear16` by fork main) | IMX283 branches | extended-in-place |
| 16 | `CameraSession::syncCpuReadBuffer` | upstream, `CC:6426-6436 @up` | Body moved to the free function `dmabufCpuSync`; member forwards | moved |
| 17 | `DngRecordingQueue::Stats` | upstream, `CC:3252-3261 @up` | 5 fields added | extended-in-place |
| 18 | `~DngRecordingQueue` | upstream, `CC:3263-3266 @up` | Unregisters a process-wide callback | extended-in-place |
| 19 | `DngRecordingQueue::startAtFolder` | upstream, `CC:3279-3376 @up` | About 100 lines added: refusal, fault resets, Log hand-over, part folders, media profile, RAM plan, gauge, pool warm-up, sync thread, copy workers, log fields | extended-in-place |
| 20 | `startAtFolder`, pool counters | upstream, `CC:3308-3309 @up` | Reset of `pooledRawBytes_`, `expectedRawBufferSize_` removed | removed |
| 21 | `startAtFolder`, uncompressed worker count | upstream, `CC:3324 @up` | `max(2, min(4, threads))` can be lowered by the media profile or set by an env var | behaviour-changed |
| 22 | `startAtFolder`, queue depth | upstream, `CC:3328 @up` | The `12` for uncompressed takes comes from the media profile when the medium is known | behaviour-changed |
| 23 | `startAtFolder`, thread start | upstream, `CC:3349-3350 @up` | Through `spawnWorker`, which counts live threads | rewritten |
| 24 | `reserveClipFolder(mediaRoot, settings)` | upstream, `CC:3384-3388 @up` | Third parameter `sensor` | extended-in-place |
| 25 | `DngRecordingQueue::stop` | upstream, `CC:3390-3424 @up` | Parameter `mediumDead`; unconditional `join` replaced by bounded wait, stall test, `detach()`; lossy writes abandoned on a gone medium; stats line longer | rewritten |
| 26 | The libcamera guard | upstream, one block from `CC:1017 @up` | Split: closed at 2789, 2926, 3007, 3311, 4168 and reopened at 2894, 2986, 3309, 3552, 4188 `@port` | extended-in-place |

## 5. New abstractions

| Name | Kind | Where `@port` | Purpose | What upstream uses for the same job | Used by |
| --- | --- | --- | --- | --- | --- |
| `CameraSection`, `loadCameraSection()`, `cameraSection()` | struct, parser, cached accessor | `CC:2937-3014` | Reads `[camera]` of the hardware file once | Each hardware class parses its own section: candidate list `src/hardware/GpioInput.cpp:55-76 @up`, parse loop `GpioInput.cpp:373-500 @up`. Upstream `CameraController.cpp` never reads the hardware file (grep: no hit). Cached value idiom: `cachedPiSerial()` `CC:2990-2994 @up` | `clearHdrIsoCap` |
| `loadBufferConf()` | file reader | `CC:2989-3006` | Reads the hardware file at each take for `[storage]` | Upstream reads `[storage]` (`mount_path`, `pcie_controller`) in an embedded Python reader, `App:3455-3456 @up`. Per-take knobs in the queue are env vars: `unsignedEnvValue("APERTAR_CDNG_QUEUE_FRAMES", ...)` `CC:3329-3330 @up` | `startAtFolder` (`CC:4297`), `planQueueBuffer` (`CC:5505`) |
| `apertar::bufferbudget` (`BufferConf`, `parseBufferConf`, `requestedFramesPerFolder`, flush-abort registry) | header-only namespace | `src/util/BufferBudget.hpp` | `[storage]` parser, RAM budget, process-wide switches | Header-only helpers exist upstream (`src/util/RecordingDropWarning.hpp`, `src/camera/StillBracketing.hpp`), all in `namespace apertar`; none holds process-wide mutable state | This slice at `CC:4297`, `CC:4626-4636` |
| `apertar::fpsceiling` | header-only namespace, 4 functions | `src/camera/FpsCeiling.hpp:10-47` | Probe vs table, back-end cap, lossless override | Inline arithmetic in the function: `probed ? std::min(table, *probed) : table` `CC:2769 @main`; `settings.fps = std::min(settings.fps, maximumFps)` `CC:2490 @up` | `CC:3121`, `CC:3141`, `CC:3422`, `CC:3470`, `CC:3488` |
| `apertar::imx585` mode tables | header-only namespace | `src/camera/Imx585Modes.hpp` | Mode rows per class, nearest lookup | Inline whitelists: `isImx585FullHdCropResolution` `CC:366-377 @up`, `isImx585Raw12CropResolution` `CC:385 @up`, `kImx477Modes` `CC:2309 @up` | `CC:2832-2834` |
| `apertar::imx283` mode table | header-only namespace | `src/camera/Imx283Modes.hpp` | Mode rows, fps floor, aliases | Same inline tables; fps numbers inline, e.g. IMX577 `CC:2657-2668 @up` | `CC:2812`, `CC:3336` |
| `apertar::ladder` (`Rung`, `effectiveCompression`) | header-only namespace | `src/camera/ModeLadder.hpp` | Mode ladder logic | none | `applyRungFormat` `CC:3037-3049` |
| `kLadderOwnsMode`, `kLadderOwnsCompression` | message constants | `CC:3061-3067` | One refusal text for 2 and 3 setters | Inline literal per setter: `setErrorLocked("Resolution changes are blocked while recording.")` `CC:7715 @up`. No `constexpr const char *k...` message in `CC @up`; no "Settings > ..." path in any upstream error text | `CC:10644`, `11578`, `11325`, `11401`, `11449` |
| `losslessFpsOverride()`, `imx283ProbeFpsOnly()`, `fpsLimitTableOnly()` | env switches cached in a function-local `static` | `CC:3117-3130`, `3391-3395`, `3398-3408` | Read an env var once per process | Env read at each call: `h264KeepRawStream()` `CC:2841-2844 @up`, helpers `unsignedEnvValue` `CC:1027 @up`, `boolEnvValue` `CC:1041 @up` | fps ceiling functions |
| `backendMaximumFps()` | hook | `CC:3426-3434` | Place for a non-sensor fps cap; returns `nullopt` today | none | `CC:3470`, `CC:3490`, `CC:8639` |
| `losslessCaptureLimited`, `losslessMaximumFps`, `modeMaximumFps`, `maximumFpsForSettings`, `maximumIsoForSettings`, `prerollMaximumFps` | free helpers | `CC:3103-3168`, `3466-3500` | Share the sanitiser's limits with the state | The limits live inside `enforceLosslessCaptureLimits` `CC:2470-2491 @up` and `sanitizeSettingsForSensor` `CC:2732-2741 @up`; upstream publishes no ceiling | Sanitiser, `settings()`, settings event, pre-roll |
| `enforceClearHdrExposureRules`, `applyClearHdrCompression`, `clearHdrIsoCap` | free helpers | `CC:3017-3096` | Clear HDR policy | none (Clear HDR is fork-main work) | Sanitiser, `setClearHdr` |
| `CdngLogPlan`, `planCdngLog`, `buildCdngLogTake`, `CdngLogTake` | structs and builders | `CC:3966-4044`, `CC:1662-1668` | Per-take Log tables | none | `CC:7739`, `CC:8172` |
| `apertar::cdnglog` | header-only namespace | `src/cdng/LogCurve.hpp` | Log curve and tables | none | `CC:4005`, `CC:4032-4037` |
| `FrameBufferGauge`, `frameBufferGauge()` | struct of 5 atomics behind a function-local static | `CC:4172-4186` | Queue level readable without the controller mutex | `RecordingDropWarning`: an object owned by `CameraController` (`CameraController.hpp:113 @up`) and passed to the queue's constructor (`CC:3251 @up`); `RecordingFailure` member (`CC:3901 @up`). The form "accessor returning a function-local static" exists upstream for process-lifetime objects: `captureSettingsPersister()` `CC:885-889 @up`, `LossyDngDiskWriter::instance()` `src/lossydng/LossyDngEncoder.cpp:112-118 @up`. Upstream publishes no queue depth: only a boolean leaves Core (`conv-core-camera.md` 5.12) | Queue (`CC:4269 ... 5487`), `frameBufferStatus` (`CC:12527`), `rawTakeActive` (`CC:12556`) |
| Flush-abort registry | process-wide `std::function` and mutex | `BufferBudget.hpp:239-252`; registered `CC:4626-4636` | Lets `handleCommand` reach the queue without the controller lock | none; upstream reaches the queue only through `CameraController` under its mutex | `~DngRecordingQueue` (`CC:4211`), `startAtFolder` (`CC:4271`) |
| `spawnWorker` | template member | `CC:4690-4708` | Thread counted in `liveWorkers_` until it returns | `workers_.emplace_back(&DngRecordingQueue::workerLoop, this)` and `join` in `stop()`, `CC:3349-3350`, `CC:3405-3408 @up` | Writers and the sync thread |
| Sync thread (`syncLoop`) | worker thread | started `CC:4366-4369`, body `CC:4743` | fsync finished DNGs, then the folder, once a second | none for cDNG (`posix_fadvise` only, `src/cdng/CdngEncoder.cpp:1756-1777 @up`). Upstream states the intent in a comment: "Keep this out of the continuous recording path: syncing each video frame would destroy throughput." (`src/util/AtomicStillFile.hpp:31-32 @up`). ProRes has its own writeback, `src/prores/ProresEncoder.cpp:257-296 @up` | `startAtFolder` |
| Copy workers (`copyLoop`, `copyThreads_`) | worker threads | started `CC:4386-4388`, stopped `CC:4453` | Copy the raw frame off libcamera's thread | The copy runs on libcamera's completion thread inside `recordRawFrame`: `acquireRawBuffer` then `copyRawBytes`, `CC:6928-6936 @up` ("The completion callback is the only producer") | `startAtFolder`, `stop` |
| `dmabufCpuSync` | free function | `CC:3750-3760` | dma-buf read sync callable from the queue | `static CameraSession::syncCpuReadBuffer`, `CC:6426-6436 @up` | `CC:5107`, `5111`, `8822` |
| `MediaProfile`, `MediaTune`, `MediaFault` | header-only types | `src/util/MediaProfile.hpp`, `MediaTune.hpp`, `MediaFault.hpp` | Medium class and filesystem, tuning file, fault class | none; upstream sizes workers from the recording format and core count only, `CC:3323-3346 @up` | `CC:4321`, `4327`, `4364`, `4249` |
| `apertar::framepath` | header-only namespace | `src/cdng/FramePath.hpp` | Part folder names, marker name | none | `CC:4294-4312` |
| `wavSampleRate` | WAV `fmt` reader | `CC:2896-2917` | Sample rate of the take's WAV | A RIFF/RF64 reader exists in the App: `App:5806-5831 @up` | `CC:9948` |
| `shellQuote` | shell quoting | `CC:2919-2925` | Quote paths for `sh -c` | `shellQuote` in the App: `App:1482-1493 @up`. Upstream `CC` starts one program, ffmpeg, with `fork` and `execv` and no shell: `CC:4154-4161 @up` | `CC:9978-9984` |
| Host tests | `tools/*_test.cpp`, not in CMake | `tools/fps_ceiling_test.cpp`, `storage_buffer_conf_test.cpp`, `frame_path_test.cpp`, `log_curve_test.cpp`, `imx283_modes_test.cpp`, `imx585_modes_test.cpp`, `buffer_budget_test.cpp` | Test the header-only logic | none: upstream Core has no `tools/` and no tests (`ls`, `grep add_test CMakeLists.txt`: no hit) | - |

### 5.1 Pointers into the conventions study

`raw/conv-core-camera.md` was written while this inventory ran. These are its rules that describe the same jobs. A pointer,
not a verdict.

| Job in this slice | Conventions-study rule |
| --- | --- |
| `[camera]` and `[storage]` read in `CC` (`CC:2942-3006`) | S22 "The camera side never reads `apertar-hardware.conf`"; N11 "Internal tuning stays out of the files the operator edits" |
| New env switches and per-take knobs (section 3.3) | I9 and recipe R5: `unsignedEnvValue` / `boolEnvValue` at the point of use, effective value in the take-start line |
| Read-once statics (`cameraSection`, `losslessFpsOverride`, `fpsLimitTableOnly`, `imx283ProbeFpsOnly`) | I17 "Process-wide one-off values are function-local statics" |
| Sync thread, copy workers, `spawnWorker`, detached writers | I16 (worker shape), 5.5 (thread table), N2 (callback never waits), N10 ("Clip frames are not synced, for throughput") |
| `FrameBufferGauge`, `buffer_*` state | 5.12 "Frame counts or queue depth in the socket API" is listed as absent; N3 (one warning per clip, not a counter) |
| Dead-medium handling | 5.6 (failure latch), 5.12 "A check for free space or a mounted drive before a take" is listed as absent |
| IMX283 cases | Recipe R1, steps 6, 8, 9, 10, 11 |
| `Imx585Modes.hpp`, `Imx283Modes.hpp` | S11 (sensor knowledge is `switch` in `CC`), 5.12 "A sensor description table (data-driven modes) or a mode probe" is listed as absent, S4 (pure logic in a small header) |
| `FpsCeiling.hpp`, `FramePath.hpp`, `LogCurve.hpp`, `BufferBudget.hpp` | S4, S6 (`src/util/` holds tiny stateful classes shared by two or more files), I22 (namespaces) |
| Lossless limits and published ceilings | 5.14 "A limit that depends on sensor and format: lossless caps `CC:2470-2491`"; S21 (runtime field of `CaptureSettings`) |
| Messages `kLadderOwnsMode`, `kLadderOwnsCompression` | I1 (setter shape), I5 (operator sentences) |
| Comments with names, dates, ticket and take numbers | I19 |
| Host tests in `tools/` | S24 |
| Guard split for the build without libcamera | I18, N12 |

## 6. Removed, narrowed or hidden

| # | What | Where | Effect |
| --- | --- | --- | --- |
| 1 | IMX585 lossless cDNG fps cap of 30 | `CC:2485-2486 @up` -> `CC:3141 @port` | Gone by default; `APERTAR_LOSSLESS_FPS_LIMIT=30` restores it |
| 2 | Lossless cDNG ISO cap of 800 | `CC:2483 @up` -> `CC:3100 @port` | 1600 |
| 3 | Lossless cDNG forces manual ISO | `CC:2484 @up` -> `CC:3155-3156 @port` | No longer on the IMX585; the comment says "Other sensors are unchecked" |
| 4 | Auto ISO and auto WB in Clear HDR | `CC:3075-3082 @port` (fork main allowed both) | Forced off; `set_iso_auto` and `set_wb_auto` are refused there (`CC:11168`, `CC:11300`) |
| 5 | ISO above 720 (12-bit) or 1585 (16-bit) in Clear HDR | `CC:3084-3085 @port` | Clamped; `[camera]` keys set to 0 lift it |
| 6 | The operator's compression choice across a Clear HDR switch | `CC:3028-3032 @port`, called at `CC:11631` | Overwritten: on -> uncompressed, off -> lossless |
| 7 | Manual `set_resolution`, `set_raw_bit_depth` while the ladder is on | `CC:10643-10646`, `CC:11577-11580 @port` | Refused (the ladder is off by default: `ModeLadder.hpp:47`) |
| 8 | `set_cdng_compression`, `set_lossy_dng_ratio`, cDNG <-> Lossy `set_record_format` while the ladder is on | `CC:11400-11403`, `11448-11451`, `11322-11326 @port` | Refused |
| 9 | Fork-main rule "Clear HDR forces 3840x2160" | `CC:2824-2827 @main` -> `CC:3526-3528 @port` | Monochrome sensor only |
| 10 | Fork-main rule "fps ceiling = min(table, probe)" | `CC:2769 @main` -> `CC:3419-3422 @port` | The table no longer limits a probed mode (except IMX283); `APERTAR_FPS_LIMIT=table` restores it |
| 11 | IMX585: an unknown size falls back to `1920x1080` | `CC:2416 @up` -> `CC:2832-2835 @port` | Nearest row of the class instead |
| 12 | IMX585 table fps fallback 120 for an unlisted size | `CC:2677-2682 @up` -> `CC:3381 @port` | 60 |
| 13 | `stop()` always joins every writer | `CC:3405-3408 @up` -> `CC:4487-4499 @port` | On a gone medium stuck writers are detached after `APERTAR_DEAD_MEDIUM_STOP_MS` |
| 14 | A take can always start on an idle queue | `CC:3279-3281 @up` -> `CC:4228-4235 @port` | Refused while detached writers still run |
| 15 | Raw pool counters reset at each take | `CC:3308-3309 @up` | Removed (`db17860`); the pool is cleared on reconfigure instead |
| 16 | `[camera] max_fps` | added by `97adea0`, removed by `bcedbe5` | Not in the port's final state |
| 17 | 25 fps cap for IMX585 Clear HDR 16-bit | added by `d44b177`, removed by `31d5418` | Not in the port's final state; `backendMaximumFps` stays as an empty hook |

Nothing in this slice hides an upstream socket command, route or config key.

## 7. Board and platform assumptions

| # | Assumption | Where | Note |
| --- | --- | --- | --- |
| 1 | The hardware file is at `/home/pi/apertar-hardware.conf` (user `pi`), then `/boot/firmware/`, then `/boot/` | `CC:2948-2950`, `CC:2994-2996 @port` | Same list as upstream's hardware classes (`GpioInput.cpp:55-68 @up`); two more copies |
| 2 | The media tuning file is at `/home/pi/apertar-media-tune.conf`; the override in `/run/apertar-media/` | `src/util/MediaTune.hpp:27-28`, read from `CC:4364` | Needs the tmpfiles entry `config/apertar-media.tmpfiles.conf` |
| 3 | Core count: writers `max(2, min(4, hardware_concurrency))`, lossless `threads + 1` when `threads >= 4`, "four-core Pi" | `CC:4315-4342 @port` | Upstream code and comment (`CC:3323-3339 @up`); the port keeps it and adds an env override |
| 4 | The recording medium is NVMe on the Pi's PCIe ("NVMe: its I/O timeout and reset") or USB; class name `pi-nvme` | comment `CC:4461 @port`; `src/util/MediaProfile.hpp:26`, `:33`, `:92-93` | Any NVMe root disk is classed `PiNvme` |
| 5 | Filesystem decides the writer count (ext4, exFAT 4; FAT, NTFS 2) | `MediaProfile.hpp:136-148`, applied at `CC:4321`, `CC:4327` | Numbers measured on one rig (exFAT on a CFexpress NVMe, `MediaProfile.hpp:140-142`) |
| 6 | exFAT create cost grows with the folder (reason for part folders) | `src/cdng/FramePath.hpp:9-11`, `CC:4285-4313` | Measured 2026-11-08 on the camera's NVMe (commit `d7dd337`) |
| 7 | IMX585 driver facts: +12 dB `EXP_GAIN`, merge window 29.1 dB, gain code 57 = ISO 720, HDR gain cap code 80 = ISO 1585 | `CC:2933-2941 @port` | Tied to the `cinemate-port` imx585 driver |
| 8 | IMX585 AGC stops at gain 8 in the default tuning, so auto ISO cannot pass the lossless cap | `CC:3152-3156 @port` | Marked "unverified" in `fork-log.md:85` |
| 9 | Lossless encoder capacity "about 69 fps" at 4K 12-bit | `CC:3132-3133 @port` | Probable: measured on the project's rigs (Pi 5, CM5; see below). The code path has no capability check |
| 10 | IMX585 Clear HDR: 30 fps at link 891 MHz, 25 at the driver's default 720 MHz | `CC:3376-3379 @port` | Fork-main comment, kept |
| 11 | The ISP back end limits 4K Clear HDR 16-bit near 28-30 fps | comments `CC:3428-3430`, `CC:3481-3485 @port` | PiSP (Pi 5 / CM5) |
| 12 | IMX283 optical-black columns lead the line; black rows trail the picture; fps floor table with `crop_vmax=0` | `CC:3693-3695`, `CC:3733-3735`, `CC:3333 @port` | Tied to the `cinemate-port` imx283 driver |
| 13 | Log needs an unpacked 16-bit raw stream; PiSP-compressed and CSI-2 packed streams record linear | `CC:3983-3988 @port` | `PixelPacking::PispCompressed1` is an upstream enumerator (`CC:3120-3131 @up`); it names the PiSP (Pi 5 / CM5) compressed raw format |
| 14 | `rubberband` is installed | `CC:9938`, `CC:9977-9984 @port` | Not in the image by default (`hardware-log.md:539`) |
| 15 | A dma-buf of the raw stream can be CPU-synced | `CC:3749-3760 @port` | Upstream code, moved |
| 16 | No use of `recordingCapabilities()` in the slice's new code | grep in 2779-4545: only the upstream H.264 lines 3580-3643 | Upstream gates board differences there: `include/apertar/core/RecordingCapabilities.hpp:18-51 @up` (bcm2712 = Pi 5 / CM5, bcm2711 = Pi 4). The new lossless and Lossy paths rely on `supportedRecordingSettings` at the top of the sanitiser (`CC:3505 @port`) |

Not in this slice: gpiochip numbers, I2C bus numbers, RP1, fan, RAM size (the RAM budget is in `planQueueBuffer`,
`CC:5495`, slice CC-3).

Rigs in the KB's test records: Pi 5 (4 GB) with a CFexpress NVMe HAT (`hardware-log.md:66-380`), later a CM5 Lite on a
Waveshare CM5-IO-BASE-A (`hardware-log.md:1079`). No Pi 4, CM4 or older board appears.

## 8. Recorded tests per commit

Source: the commit's `Tested:` line and `fork-log.md`. Order: date.

| Commit | Subject (short) | Commit says | Fork-log says |
| --- | --- | --- | --- |
| `db17860` | one request per raw buffer; pool survives takes | Pi, 5 takes per case | row `:31`, on GitHub |
| `43a54f3` | dma-buf sync as free helper | desk only | row `:32` |
| `351a3ee` | raw copy on a recorder worker | desk only | row `:34`; Pi takes in `hardware-log.md:137` |
| `438a342` | survive a yanked drive | desk only, not built | row `:41`, built 22:27 |
| `0b1632f` | pulled card seen at once, bounded stop | pi build | row `:43`, built 22:43 |
| `a3ac8da` | pulled latch, write stall | pi build | row `:44`, built 22:51 |
| `26da30e` | media profile | pi build | row `:46`, "not tested" |
| `4ce382e` | sync once a second | pi build | row `:48`, "not tested" |
| `5b68f1f` | fsync each DNG | pi build | row `:53`, pull test 258/281 frames |
| `8175273` | Clear HDR holds ISO and WB | Pi preview | row `:61`, tested 2026-10-28 |
| `e5757d7` | ISO from a measured gain | Pi | row `:64`, tested |
| `ca7b7c2` | stretched WAV | desk only | row `:69`, tested 2026-10-28 |
| `6d217c7` | `iso_max` | desk only | row `:71`, tested (Patrik) |
| `97adea0` | `[camera] max_fps`, `fps_max` | desk only | row `:73`, superseded |
| `bcedbe5` | no `max_fps` | desk only | row `:74`, tested (Patrik) |
| `2f43ecc` | lossless ISO 1600 | desk only | row `:80`, tested (Patrik) |
| `b5b787e` | auto ISO in IMX585 lossless | desk only, "Unverified" | row `:85`, built, unverified |
| `f2ebe6e` | Clear HDR uncompressed | desk only | row `:89`, built |
| `3cae990` | ladder names its compression | desk only, host test | row `:92`, built |
| `09256a7` | ladder blocks manual changes | desk only | row `:95`, built |
| `e16033e` | ladder data for the editor | desk only | row `:96`, built, not tested |
| `d44b177` | drop-frames squash | host tests; Pi: trim and Log 16 to 12 only; "Not run yet: the ram queue, the safety stop, ... the fps ceilings" | row `:138`; later Pi runs in `hardware-log.md:813-959` |
| `c5db8b2` | record during a flush | no `Tested:` line | in row `:138` |
| `014a2bf` | clip names | no `Tested:` line | in row `:138` |
| `4abbef0` | raw pool warm-up | syntax check; not built or run on the Pi | no row |
| `0ed07ea` | `APERTAR_DNG_DONTNEED` | syntax check, shell test; not run on the Pi | named in row `:157` |
| `caa0153` | IMX585 tables | desk only | in row `:138`, "Not yet run on the camera" |
| `c48e693` | IMX283 | desk only | in row `:138` |
| `5f5cea2` | build without libcamera | no `Tested:` line | in row `:138` |
| `48f8b8c` | clip line fields | desk only | row `:141`, "not built on the Pi yet" |
| `2edc6d0` | media tuning file | desk only, host test | row `:142`, built, "Core not restarted yet" |
| `31d5418` | no 25 fps cap | desk only | row `:147`, built on the Pi |
| `d7dd337` | frames per folder | desk, Pi build rc 0 | row `:186` |

`fork-log.md:181-182`: the camera has run this Core branch since 2026-11-08 (`frames_per_folder=0`).

## 9. Blame summary (added lines per commit)

| Lines | Commit | Lines | Commit | Lines | Commit |
| --- | --- | --- | --- | --- | --- |
| 193 | `d44b177` | 21 | `3cae990` | 7 | `4ce382e` |
| 80 | `8175273` | 13 | `43a54f3` | 6 | `48f8b8c` |
| 49 | `c48e693` | 11 | `5b68f1f` | 5 | `b5b787e` |
| 41 | `97adea0` | 11 | `26da30e` | 5 | `31d5418` |
| 32 | `d7dd337` | 10 | `e16033e` | 4 | `2edc6d0` |
| 31 | `ca7b7c2` | 10 | `5f5cea2` | 4 | `09256a7` |
| 29 | `0b1632f` | 10 | `351a3ee` | 3 | `bcedbe5`, `2f43ecc`, `014a2bf` each |
| 27 | `6d217c7` | 9 | `f2ebe6e` | 2 | `c5db8b2`, `4abbef0` each |
| 24 | `caa0153` | 8 | `0ed07ea` | 9 | `35dbe67` (upstream lines the diff shows as moved) |
| 24 | `438a342` | 7 | `e5757d7` | | |
| 21 | `a3ac8da` | | | | |

## 10. Facts a later stage may want (no verdict)

All confirmed by reading `@port` unless marked.

| # | Fact | Where |
| --- | --- | --- |
| 1 | The comment of `isoForMeasuredGain` (2892-2893) is separated from the function (2928) by `#if`, `wavSampleRate` and `shellQuote` | `CC:2892-2931` |
| 2 | `loadBufferConf` sits between `loadCameraSection` and its accessor `cameraSection` | `CC:2986-3014` |
| 3 | The six-line candidate-path block appears twice in the slice, word for word | `CC:2945-2950`, `CC:2991-2996` |
| 4 | The two new readers of the same file parse differently: `loadCameraSection` deletes all whitespace, strips trailing comments, matches `[camera]` exactly; `parseBufferConf` trims, lowercases, and ignores a value with a trailing comment | `CC:2958-2966`; `BufferBudget.hpp:141-177` |
| 5 | `loadCameraSection` stops at the first file that opens; upstream's `GpioInput::loadConfig` goes on to the next candidate when the section is missing | `CC:2985`; `GpioInput.cpp:498-499 @up` |
| 6 | `[storage]` reaches Core by two routes: the App parses the hardware store's text, the queue re-reads the file from disk | `App:276`; `CC:2989-3006` |
| 7 | `backendMaximumFps` returns `nullopt` for every input and casts both parameters to `void`; 3 call sites | `CC:3426-3434`, `3470`, `3490`, `8639` |
| 8 | Comment says "the 16-bit 25 is backendMaximumFps()"; that cap no longer exists | `CC:3378` vs `CC:3428-3433` |
| 9 | Comment on `prerollMaximumFps` says "only the named back-end cap kept"; there is none | `CC:3481-3485` |
| 10 | Comment says "exFAT/NTFS get 2"; the table gives exFAT 4 | `CC:4317-4319` vs `MediaProfile.hpp:140-142` |
| 11 | Both ladder messages send the operator to "Settings > Record > Mode Ladder"; the card is in the `modes` pane | `CC:3062`, `CC:3067` vs `WCP:5151-5166` |
| 12 | Comments carry internal names, dates, take numbers and KB paths: "Patrik's rule" (3025, 3070), "T34" (3034), "temp 753f181 ... C0013" (3098-3099), "(Patrik, 2026-10-28)" (3154), "(User, 2026-11-03)" and two KB paths (3428-3430), "T29 measures" (4318), "C0005" (4357) | lines as listed |
| 13 | Operator-visible log text says "CineMate Log" | `CC:3985`, `CC:4008` |
| 14 | `wavSampleRate` accepts `RIFF` only; Core writes `RF64` above 4 GiB and upstream's reader accepts both | `CC:2900`; `src/audio/AudioRecordingSession.cpp:911-912 @port`; `App:5806 @up` |
| 15 | `buildCdngLogTake` copies the plan into locals, one of them `std::optional<cdnglog::Params>(plan->params)` that is then dereferenced | `CC:4023-4028` |
| 16 | `static bool warned` inside the member `startAtFolder`. Upstream's one-off warnings are `bool warned..._` members (`CC:6858-6861 @up`, `conv-core-camera.md` I8) | `CC:4371-4373` |
| 17 | A forward declaration of `modeMaximumFps` is needed because `losslessMaximumFps` (3134) now calls a function defined at 3466 | `CC:3113` |
| 18 | The sync thread counts as a writer (`spawnWorker`); the copy threads do not (`copyThreads_`) | `CC:4369`, `CC:4387-4388` |
| 19 | `isLosslessTwoKCapture` still calls the normaliser with the default class (12-bit, SDR) | `CC:2886` |
| 20 | `4abbef0` has no fork-log row | `grep 4abbef0 fork-log.md`: no hit |

## 11. The owner's request about the GPIO chip definition

Request relayed with this task: reinsert the definition of the GPIO chip, because GPIOs of another chip (for example a
microcontroller) can be chosen.

| Finding | Evidence |
| --- | --- |
| Not in this unit. `CameraController.cpp` has no GPIO or gpiochip code at any ref | `grep -n -i 'chip\|gpio'` on `CC @port`, `CC @up` and the diff slice: no hit |
| Upstream defines it as a config key: `gpiochip=auto` in the default template; `chip` / `gpiochip` / `gpio_chip` parsed per class | `App:4380`, `App:4394 @up`; `src/hardware/GpioInput.cpp:431-432 @up`; `src/hardware/TriggerOutput.cpp:311-312 @up` |
| The port keeps the key in Core: template and parsers | `App:5168`, `App:5182 @port`; `GpioInput.cpp:343-344`, `TriggerOutput.cpp:305-306`, `RecordingIndicatorOutput.cpp:312-341 @port` |
| Pointer 1 for the unit that owns Controls: the Controls model leaves `chip` out of the settings rows on purpose | `src/hardware/ControlsModel.hpp:263 @port`: "poll_ms (chips without edge events) and chip stay text-only: the Pi 5's header needs neither" |
| Pointer 2: upstream's touch UI wrote a first-run hardware file with `chip=auto` in `[gpio_buttons]` and `[gpio_encoders]` and `gpiochip=auto` for trigger and LED | `Apertar-UI/src/DisplayConfigBridge.cpp:110, 123, 161, 172 @up`; `Apertar-UI/src/Ina219Bridge.cpp:129, 142, 180, 191 @up` |
| Pointer 3: the port removed those UI templates (577 lines), so no default file shows `chip=` in a GPIO input section any more | UI commit `c9d841f` "ui: stop writing a default hardware file when it is missing"; `grep -rn 'gpiochip\|chip=auto' Apertar-UI/src Apertar-UI/qml @port`: no hit |
| Pointer 4: Core's template has `enabled=false` only in `[gpio]` and `[gpio_encoders]`; it names `chip` once, in a comment of `[gpio_switches]` | `App:5137-5151 @port` (upstream Core's template also lacked the key there: `App:4380`, `App:4394 @up` are the only two `chip` lines) |

## 12. Unconfirmed

| Item | What would settle it |
| --- | --- |
| That the sanitiser's reordering (row 12 in section 4) changes nothing for IMX477, IMX577, IMX294 (probable: `supportedRawBitDepthForSensor` does not read the resolution) | A host test that runs both orders over each family's sizes |
| That F5's "auto ISO cannot pass 1600 on the IMX585" holds with every tuning file | Read `AgcChannel` gain limits in the tuning files the camera ships; a take with auto ISO in lossless at low light |
| Which of F6, F7, F12, F13, F14 a given `d44b177` line belongs to, where the code is shared | The 19 pre-squash commits. The commit message says "Squashed from 19 commits"; its earlier id `400dd1f` (`fork-log.md:138`) is not in this container (`git cat-file -e 400dd1f` fails) |
