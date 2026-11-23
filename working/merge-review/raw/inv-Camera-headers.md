# Inventory: unit Camera-headers (stage 1, no judgement)

Refs: port = `cinemate-port` `01f170c` (Apertar-Core); main = `origin/main` `f60e301`; upstream = `upstream-1.6.0`.
Read completely: the 7 new headers, the CameraController.hpp and Types.hpp diffs, the 4 test headers (top + check counts).
Labels: confirmed = read in code; probable = inferred.

## 1. Files in scope

| File | Lines | Status vs upstream | Port commits (git log, oldest first) |
| --- | --- | --- | --- |
| src/camera/FpsCeiling.hpp | 47 | new | d44b177 |
| src/camera/FramePhaseLock.hpp | 158 | new | 80ddac1, f4a1393 (comment + pin {d,d+1}) |
| src/camera/Imx283Modes.hpp | 144 | new | c48e693 |
| src/camera/Imx585Modes.hpp | 254 | new | caa0153 |
| src/camera/ModeLadder.hpp | 344 | new | 88e644d, a7b6f82, cdf83cd, 3cae990, e16033e, d44b177, caa0153 |
| src/camera/ScalerCropGeometry.hpp | 94 | exists upstream (2 functions); +28 lines, 1 function | c48e693 |
| src/camera/TuningTdnStrip.hpp | 451 | new | e625c68 |
| src/camera/CameraController.hpp | +103 -1 | modified | many (table 3) |
| include/apertar/core/Types.hpp | +95 | modified | many (table 3) |
| tools/imx283_modes_test.cpp | 218 | new | c48e693 |
| tools/imx585_modes_test.cpp | 105 | new | caa0153 |
| tools/fps_ceiling_test.cpp | 47 | new | d44b177 |
| tools/tuning_tdn_strip_test.cpp | 120 | new | e625c68 |

Upstream has no `tools/` tree and no unit test (confirmed: `git ls-tree upstream-1.6.0 | grep ^tools/` = 0). Main has none either (confirmed, no `_test` in ls-tree origin/main).
No `add_test` / `enable_testing` in CMakeLists.txt at port; tests are hand-built with `g++` (command in each file's header comment). Confirmed.
Mode-ladder test is not in scope: tools/log_curve_test.cpp includes ModeLadder.hpp; the ladder's own host test lives in `working/tools/mode_ladder_test.cpp` (fork-log:86), not in the repo. Confirmed.

## 2. Header-by-header facts

| Header | What it does | Operator-visible effect | Env var / config / file | Used by |
| --- | --- | --- | --- | --- |
| FpsCeiling.hpp (ns `apertar::fpsceiling`) | `resolveSensorMaxFps(probed, table, tableOnly)`: probed fps wins, table is the fallback. `applyBackendCap`. `parseLosslessFpsLimit`, `losslessImx585Fps` | FPS ceiling in 4K SDR rises from table 30 to the sensor's 60; IMX585 lossless cDNG no longer capped at 30 | env `APERTAR_FPS_LIMIT=table` (restores `min(table, probed)`); env `APERTAR_LOSSLESS_FPS_LIMIT=<n>` | CC.cpp:3121, 3141, 3422, 3470, 3488, 8634 |
| FramePhaseLock.hpp (struct `FramePhaseLock`, `PhaseLockStatus`) | Pure PI servo: phase error of frame arrivals vs origin + k/fps on SensorTimestamp (CLOCK_BOOTTIME); requests whole-microsecond FrameDurationLimits; Tuning kp 0.06, ki 0.0015, deadband 6 us, clamp 150 us; sigma-delta between {d, d+1} | Optional cadence lock to the Pi clock so audio and picture do not drift; off by default | state `fps_phase_lock`, `fps_phase_lock_active/_err_us/_dur_us/_pushes/_saturated`; socket `set_fps_phase_lock`; key `fps_phase_lock` in camera_settings.conf | CC.hpp (include + `phaseLockStatus()`), CC.cpp:7502-8212, 8887+ |
| Imx283Modes.hpp (ns `apertar::imx283`) | Table of 57 non-experimental driver modes (bits 12/10, binning 1/2/3, active size, fps floor); active vs transport size (optical-black +(96,16)/(48,4)/(32,4)); `find`, `findTransport`, `normalise`, `floorFps` | IMX283 (5472x3648) works as a fourth sensor family; resolution list; generic 1080p/4K aliases map to 2736x1540 (12-bit) / 3840x2160 (10-bit) | none | CC.cpp:13, 656-713, 2272+ (SensorFamily::Imx283) |
| Imx585Modes.hpp (ns `apertar::imx585`) | Tables for classes S12 (62 rows), S10 (62), H12 (29), H16 (34); transport = active + optical-black rows in H16 (+40 / +20 binned); width policy; `find`, `offered`, `nearest`, `transportFor`, `activeFor` | Which IMX585 sizes are offered per bit depth/Clear HDR; modes narrower than 1280 hidden | env `APERTAR_IMX585_MIN_MODE_WIDTH` (default 1280; 0 shows all) | CC.cpp, WCP.cpp, tests |
| ModeLadder.hpp (ns `apertar::ladder`) | Pure logic: `Rung`, `Ladder`, `RungState`, `chooseRung`, `parseRungs`/`rungsText` (`WxH:BITS:hdr|sdr[:FPS[:COMPRESSION[:log]]]`), `validate`, `toJson` (the get/set_mode_ladder reply, hand-built strings), `fileText`/`parseFile` | FPS picks the sensor mode between takes; per-resolution compression and Log; editor messages; Ramp-ready | file `~/.config/apertar-core/mode_ladder.conf` (keys `enabled`, `ramp_ready`, `resolutions`, old `rungs`); socket `get_mode_ladder`, `set_mode_ladder` | CC.hpp (`ladder::Ladder modeLadder_`, helper decls), CC.cpp, tools/log_curve_test.cpp |
| ScalerCropGeometry.hpp | Adds `activeAreaScalerCrop(out, active, nativeBounds)` beside upstream `centeredRawWindowScalerCrop`, `centeredPreviewScalerCrop` (both unchanged, confirmed by `git diff --stat upstream-1.6.0`: 28 insertions only) | IMX283 preview/raw crop skips the optical-black columns | none | CC.cpp:2492 |
| TuningTdnStrip.hpp (ns `apertar::tuning`) | Text-level JSON parser (own recursive-descent, `Node/Member/Parser`) that removes the `tdn` member from every `rpi.denoise` config; `previewTuningPath()` writes a validated copy and a `.src` sidecar | Preview (HDMI, touch UI, WebUI, zebra, peaking) loses temporal denoise: faster ISP at 4K Clear HDR 16-bit; raw DNGs unchanged | files `$HOME/.cache/apertar-core/tuning/<stem>_notdn.json` and `<stem>_notdn.json.src`; env `HOME` read; key `preview_tdn` | CC.cpp (setPreviewTdn path), includes `camera/DefaultTuningSelection.hpp` (upstream header: `Pipeline`, `compatibleFile`) |

## 3. CameraController.hpp changes (diff --minimal vs main)

| Region | Change | Feature | Commits | Kind |
| --- | --- | --- | --- | --- |
| includes | + FramePhaseLock.hpp, ModeLadder.hpp, `<atomic>` | phase lock, ladder | 80ddac1, 0041ba0 | extended in place |
| `struct SensorMode` | + `binning`, `binningSource` | per-mode binning | 4ab1057 | extended in place (struct from main f60e301 probe) |
| new `struct SensorBinning` | factor/source/crop of the configured mode | binning | 4ab1057 | new, beside SensorMode |
| `setIsoAuto()` | signature `setIsoAuto(bool enabled = true)` | iso auto lock | 646a194 | behaviour changed (default arg keeps old calls) |
| setters added | `setCdngLog`, `setConformFps`, `setClipNameTemplate`, `previewClipName`, `setFpsPhaseLock`, `setMediaTrimEnabled`, `setPreviewTdn`, `activeTuningFile`, `setFpsSpeedRamp(4 bools)`, `setModeLadder(6 args, out json+error)`, `modeLadderJson`, `applyLadderToPreset` | Log, conform fps, clip names, phase lock, trim, preview TDN, speed ramp, ladder | d44b177, 014a2bf, 80ddac1, e625c68, ce0bd90, faa2958, d7ff071, 0041ba0 | extended in place |
| media fault API | `flagMediaFault`, `recordingFaultName` | yanked-drive survival | 438a342 | extended in place |
| buffer bar API | `FrameBufferStatus` struct + `frameBufferStatus()`, `rawTakeActive()`, `cdngLogApplicable()` | RAM write buffer bar | d44b177 | extended in place |
| storage pre-roll | `StoragePrerollResult`, `startStoragePreroll`, `storagePrerollError`, `finishStoragePreroll` | pre-roll speed test | d44b177 | extended in place |
| getters | `sensorBinning()`, `sensorMono()`, `phaseLockStatus()`, `recordingDroppedFrames()` | binning, mono IMX585, phase lock, drop counter | 4ab1057, caa0153, 80ddac1, 64bbbaa | extended in place |
| private | `applyFpsStepLocked`, 8 ladder helpers (`ladderStatesLocked`, `ladderActiveForLocked`, `ladderRewriteLocked`, `fillLadderFieldsLocked`, `saveModeLadderLocked`, `fillRungExtrasLocked`, `modeLadderJsonLocked`), `fillClipNameExampleLocked`, `clipNameSensorLocked`, `restoreFpsAfterRampLocked`, `cdngLogApplicableLocked`, `emitLogAppliedIfChangedLocked` | ladder, ramp, clip names, Log | 0041ba0, faa2958, 014a2bf, d44b177 | extended in place |
| private members | `lastEmittedLogApplied_`, `prerollTake_` (atomic), `prerollSaved_`, `prerollFolder_`, `prerollFps_`, `externalFailureMessage_`, `externalMediumGone_`, `recordingFaultName_`, `rampNominalShutterUs_`, `rampTakeBaseFps_`, `rampTakeChanged_`, `modeLadder_`, `ladderOverride_` | as above | as above | extended in place |

Nothing of the original CameraController.hpp is removed. One original signature changed (setIsoAuto). Class stays one class with one mutex_; the ladder state is members, not a second object. Confirmed.

## 4. Types.hpp changes

| Region | Change | Feature | Commits | Kind |
| --- | --- | --- | --- | --- |
| include | `<vector>` | ladder tops | 62c1711 | extended |
| new `enum class CdngLog {Off, Auto}` | CineMate Log | Log | d44b177 | new, beside CdngCompression |
| `toString(CdngLog)`, `cdngLogFromString`, `cdngLogStoredBits`, `cdngLogAvailable`, `cdngLogBits(CaptureSettings)` | free inline functions in Types.hpp; "12/10/8" legacy values all map to Auto | Log | d44b177 | new; upstream puts enum-to-string helpers in this same header (confirmed pattern at toString(CdngCompression)) |
| `CaptureSettings` persisted fields | `conformFps`, `fpsPhaseLock`, `previewTdn`, `mediaTrimEnabled`, `fpsSpeedRamp`, `fpsSpeedRampKeepExposure`, `fpsSpeedRampStretchAudio`, `fpsSpeedRampReturn`, `clipNameTemplate`, `isoAutoAfterClearHdr`, `whiteBalanceAutoAfterClearHdr`, `cdngLog` | see names | d7ff071, 80ddac1, e625c68, ce0bd90, faa2958, ca7b7c2, 014a2bf, 8175273, d44b177 | extended in place |
| `CaptureSettings` runtime (not persisted) fields | `clipNameExample`, `isoMeasured`, `cdngLogApplied`, `isoMax`, `fpsMax`, `fpsTakeMax`, `ladderActive`, `ladderRung`, `ladderRampReady`, `ladderEnabled`, `ladderOverride`, `ladderCount`, `ladderTops` (vector), `ladderText` | state fields iso_actual, iso_max, fps_max, fps_take_max, ladder_* | 646a194, 6d217c7, 97adea0, e16033e, 0041ba0 | extended in place; CaptureSettings now mixes persisted and runtime fields (upstream already has runtime `whiteBalanceAvailable`, `timelapseExposureLimitUs`) |
| `AudioRecordingOptions` | `fpsRamp` | speed ramp WAV | faa2958 | extended |

## 5. Features touching this unit (operator-visible)

| # | Feature | Operator gets | Socket commands / routes | State fields | Config keys / files | Env vars | UI | Commits | Relation to upstream | Tested (fork-log) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | Sensor probe-driven FPS ceiling | 4K SDR up to 60 fps (was 30); Clear HDR 4K 30 | `list_sensor_modes` (main f60e301) | `fps_max`, `iso_max` | none | `APERTAR_FPS_LIMIT=table`, `APERTAR_LOSSLESS_FPS_LIMIT=<n>` | WebUI FPS pills | d44b177, 97adea0, bcedbe5, 6d217c7 | extends main's `probedMaximumFps` (CC.cpp@main:2692, 2767: `min(table, probed)`) by moving the rule into a header and flipping it to probe-wins | host test fps_ceiling_test (not run here); Pi: "Not yet run on the camera" (fork-log:138) |
| 2 | Frame-rate phase lock | Optional cadence lock, off by default | `set_fps_phase_lock` | `fps_phase_lock`, `fps_phase_lock_active/err_us/dur_us/pushes/saturated` | `fps_phase_lock` in camera_settings.conf | none | WebUI Performance card | 80ddac1, 8f7dc39, 3a18db0, 114bfb9, 117065d, 69a700e -> f4a1393 | new area (no upstream cadence control; upstream CC.cpp:2030 only sets FrameDurationLimits once) | built on Pi 2026-11-04; no host test in repo (sim is `working/tools/phase_lock_sim.cpp`, 17 checks, fork-log/phaselock-answer.md); not measured on the rig (UNKNOWN) |
| 3 | IMX585 modes from tables | Full mode list per class (S12/S10/H12/H16), mono awareness, width policy | `list_sensor_modes` | `sensor_mono`, ladder `raw_width/raw_height` | none | `APERTAR_IMX585_MIN_MODE_WIDTH` | WebUI family pills, ratio row | caa0153 (+ 900d282 crops) | replaces upstream whitelists (`isImx585LowResolutionAlias` etc., CC.cpp@upstream:360-398) in part; the old alias functions still exist at port CC.cpp:435-492 | host test imx585_modes_test (44 CHECKs); desk, Pi probe per table row; not run on the camera |
| 4 | IMX283 sensor family | A third raw sensor (57 modes) | `list_sensor_modes` | none new | none | none | WebUI bases/ratios | c48e693, a47dc28 | extends upstream's `SensorFamily` enum (CC.cpp@upstream:1884: Imx294/Imx477/Imx585) with Imx283; facts in a header instead of in CC.cpp as upstream does (upstream: `kImx477Modes` array at CC.cpp@upstream:2309, `isImx294Resolution` at :462) | host test imx283_modes_test (218 lines, table typed twice); desk only |
| 5 | Mode ladder | FPS picks resolution/bit depth/compression/Log between takes; Ramp-ready | `get_mode_ladder`, `set_mode_ladder` (dry run) | `ladder_enabled`, `ladder_count`, `ladder_text`, `ladder_tops`, `ladder_resolution`, `fps_take_max`, `ladder_*` | `~/.config/apertar-core/mode_ladder.conf` | none | WebUI Modes pane, touch UI `ladderActive` | 88e644d, 0041ba0, a7b6f82, cdf83cd, 3cae990, 09256a7, e16033e, 62c1711 | new area; a separate config file beside camera_settings.conf; hand-built JSON with nested arrays (`resolutions`, `pool`, `ceilings`), unlike upstream's flat scalar replies | socket-tested twice 2026-10-28 (fork-log:87); WebUI not tested (fork-log:94, 96) |
| 6 | CineMate Log | Log curve in cDNG / Lossy DNG | `set_cdng_log` | `cdng_log`, `cdng_log_bits`, `cdng_log_available`, `cdng_log_applied` | `cdng_log` | none | WebUI | d44b177 | extends `CdngCompression` pattern | tools/log_curve_test.cpp; not run on the camera |
| 7 | Preview TDN switch | Faster preview ISP at 4K HDR16 | `set_preview_tdn` | `preview_tdn`, `tuning_file_active` | `preview_tdn`; cache dir above | none | WebUI Performance card | e625c68 (from 6bd002b) | adds a parallel path beside upstream's `DefaultTuningSelection.hpp` / `set_tuning_file`; own JSON parser although CC.cpp has libyaml for tuning checks (test header says libyaml needed for file side) | host test tuning_tdn_strip_test incl. golden-file compare; "Pi only, built 2026-11-04" |
| 8 | Binning per mode | Shows binning and crop of the current mode | `list_sensor_modes` (+binning, binning_source) | `sensor_binning`, `sensor_binning_source`, `sensor_crop` | none | none | WebUI | 4ab1057 | extends main's probe (f60e301) | "built and running 21:39, list_sensor_modes + get_state verified" (fork-log:36) |
| 9 | Speed ramping | FPS can change in a cDNG/MLV take | `set_fps_speed_ramp` | `fps_speed_ramp`, `_keep_exposure`, `_stretch_audio`, `_after` | `fps_speed_ramp*` | none | WebUI Speed Ramp card | faa2958, ca7b7c2 | new area | tested 2026-10-28 (fork-log:63 family) |
| 10 | Clip names, conform fps, media trim, buffer bar, pre-roll, media faults | see names | `set_clip_name_template`, `preview_clip_name`, `set_conform_fps`, `set_media_trim`, `set_buffer_mode`, `set_storage_preroll`, `storage_preroll` | `clip_name_template`, `clip_name_example`, `conform_fps`, buffer fields | `clip_name_template`, `conform_fps`, `media_trim`, `[storage]`, `[media]` | `APERTAR_MEDIA_TRIM=0`, `APERTAR_WEB_PREVIEW_RECORDING_FPS` | WebUI | 014a2bf, d7ff071, ce0bd90, d44b177, 438a342, fb557e9 | only their API surface is in this unit; bodies belong to other units | see fork-log:138, 156 |
| 11 | Clear HDR holds ISO/WB | Auto ISO/WB stop in Clear HDR and return after | `set_iso_auto enabled=false` | `iso_actual`, `iso_auto_after_clear_hdr` | same keys | none | WebUI | 8175273, 646a194 | extends `setIsoAuto` | not stated |

## 6. Upstream code changed (this unit)

| Region | Where | Change | Kind |
| --- | --- | --- | --- |
| `CameraController::setIsoAuto` | CC.hpp | `(bool enabled = true)` | behaviour-changed (signature) |
| `struct SensorMode` | CC.hpp (from main) | + binning, binningSource | extended-in-place |
| `CaptureSettings` | Types.hpp | 12 persisted + 14 runtime fields | extended-in-place |
| `AudioRecordingOptions` | Types.hpp | + fpsRamp | extended-in-place |
| `ScalerCropGeometry.hpp` | whole file | + `activeAreaScalerCrop`; others unchanged | extended-in-place |
| `CameraController` private section | CC.hpp | ~40 new members/helpers | extended-in-place |

## 7. New abstractions

| Name | Purpose | Upstream equivalent |
| --- | --- | --- |
| `apertar::fpsceiling` header-only ns | the min/probe/cap rules | none; main has the same rule inline in `maximumSupportedFpsForResolution` (CC.cpp@main:2767) |
| `FramePhaseLock` + `PhaseLockStatus` | pure servo state machine; `CameraSession` owns it | none; upstream sets FrameDurationLimits once (CC.cpp@upstream:2030) |
| `apertar::imx585` ns (Mode, Class, Rows, `offered`, `find`, `nearest`) | table-driven mode data | free functions + constexpr arrays in CC.cpp (`isImx585*Resolution`, CC.cpp@upstream:360-398; `kImx477Modes` :2309) |
| `apertar::imx283` ns | same for IMX283 | same as above (`isImx294Resolution` :462) |
| `apertar::ladder` ns (Rung, Ladder, RungState, PoolEntry, JSON writer, file parser) | the mode ladder | none |
| `NativeScalerCrop` + `activeAreaScalerCrop` | OB-aware crop | upstream `centered*ScalerCrop` in same file |
| `apertar::tuning` ns, `tdn_detail::Parser/Node/Member`, `TdnStripResult` | JSON text surgery, cached copy | `DefaultTuningSelection.hpp` (reads tuning JSON with libyaml) |
| `CdngLog` + 5 free functions | Log setting and bit math | `CdngCompression` + `toString` in Types.hpp |
| `FrameBufferStatus`, `StoragePrerollResult` | API structs | none |
| `tools/*_test.cpp` (4 files, 3 styles: `check()`, `CHECK` macro, `expectStrip`) | host tests | none (no tests upstream) |

## 8. Removed, narrowed or hidden

| What | Where | Effect |
| --- | --- | --- |
| IMX585 whitelist functions replaced by tables for offering modes | CC.cpp (outside this unit; old `isImx585*` still present at port:435-492) | modes narrower than 1280 px hidden by default (`minModeWidth`); H16 1x1 1920x1080 row not offered (shadowed by binned row) |
| Resolution choice when ladder active | CC.hpp comment on 09256a7 | manual resolution, bit depth and Clear HDR refused while ladder is on |
| Old `fps_max = min(table, probed)` | FpsCeiling.hpp | probe now wins; table only fallback (`APERTAR_FPS_LIMIT=table` restores) |
| Lossless IMX585 30 fps cap | FpsCeiling.hpp | lifted; env restores |
| Log legacy values "12","10","8" | Types.hpp `cdngLogFromString` | all collapse to Auto |
| IMX283 generic aliases | Imx283Modes.hpp `normalise` | 1920x1080 / 3840x2160 requests become other sizes at 12-bit |

Nothing was deleted from upstream headers.

## 9. Board and platform assumptions

| Assumption | Where | Label |
| --- | --- | --- |
| Pi 5 RP1 CFE stamps SensorTimestamp from ktime at CSI-2 start; phase lock uses CLOCK_BOOTTIME domain | FramePhaseLock.hpp comment; phaselock-answer.md:33 | confirmed (comment), hardware basis probable |
| PiSP pipeline (target `pisp`) for the TDN strip; Vc4 yields "expected bcm2835" via `compatibleFile` but `rpi.denoise tdn` strip is meant for PiSP (Pi 5 / CM5) | TuningTdnStrip.hpp:8-10, calls `compatibleFile(.., pipeline)` | confirmed (code), Pi 4 behaviour unconfirmed (run strip on a vc4 tuning) |
| Sensor probe values (link 891 MHz, `rp1-clk-333mhz`) are Pi 5 numbers; IMX585 fps ceilings, 16-bit Clear HDR optical black (+40/+20 rows) | Imx585Modes.hpp, ramp-mode-ladder.md:12 | confirmed |
| `HOME` set; cache under `$HOME/.cache/apertar-core/tuning` (service user), else falls back to source | TuningTdnStrip.hpp:404 | confirmed |
| Ladder file path `$XDG_CONFIG_HOME` or `$HOME/.config/apertar-core/mode_ladder.conf`, else temp dir | CC.cpp:404-414 (same style as camera_settings.conf at :421) | confirmed |
| IMX283 driver is the cinemate-port driver with `experimental_modes=0`; 57 modes | Imx283Modes.hpp:1 | confirmed |
| Phase-lock deadband and `clampUs` tuned on IMX585 at 24/25 fps | FramePhaseLock.hpp Tuning | probable |
| No assumption on core count, RAM size, gpiochip, I2C bus, fan in these headers | n/a | confirmed (grep for these in the 7 headers returned none; `prerollFolder_`, `FrameBufferStatus` carry no sizes) |
| Max 8 resolutions in a ladder; threshold <= 280 fps | ModeLadder.hpp validate/parse | confirmed |

## 10. Open items for the next stages (not judged here)

- Where the port's tests belong (no test dir upstream or on main; no CMake hook).
- Two parallel IMX585 mode sources at port: tables (Imx585Modes.hpp) and the older whitelist functions in CC.cpp.
- `ModeLadder.hpp::toJson` builds nested JSON by string concatenation; upstream replies are flat scalars (BRIEF hint).
- Port-internal tutorial numbers in comments and in the conf header text: T27? (not in these headers), T31, T34 appear in Types.hpp, CC.hpp, ModeLadder.hpp, `fileText()` writes "(T34)" into the user's mode_ladder.conf. Confirmed.
- Co-author attribution `Co-Authored-By: Claude ...` on c48e693 and f60e301 (commit clarity task).
