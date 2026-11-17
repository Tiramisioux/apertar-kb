# inv-CC-1: inventory of `src/camera/CameraController.cpp`, port lines 1-2732

Stage 1 of 3: inventory. Says what the port added or changed here. No judgement.

Legend: `CC` = `src/camera/CameraController.cpp`. A line number without a ref is @cinemate-port (`01f170c`).
`@up` = @upstream-1.6.0 (`35dbe67`, `/home/user/wt/core-upstream`). `@main` = fork main (`f60e301`, `/home/user/wt/core-main`).
Every row is **confirmed** (read in code at the cited ref) unless marked **P** (probable) or **U** (unconfirmed).
Test entries are what a commit message or the fork-log records. They were not re-verified.

## 0. Scope and method

| Item | Value |
| --- | --- |
| Unit | `/home/user/build/review/diffs/CC.part01.diff`: 1159 lines, 19 hunks. Identical to the first 1159 lines of `git -C /home/user/Apertar-Core diff --minimal -U10 origin/main cinemate-port -- src/camera/CameraController.cpp` (`diff -q`) |
| Port file | CC lines 1-2732 of 12931 |
| Merge target | CC @main lines 1-2373 of 9313 |
| Original | CC @up lines 1-2315 of 8834 |
| Change here | +409 / -50 lines |
| Line origin, port 1-2732 | upstream 2265, fork main 55, port 412 (`git blame -s -L 1,2732 cinemate-port`) |
| Port commits with lines here | 26 of the 68 that touched CC (table 0.1) |
| Chapters covered (names from `llm/core-map.md` 1.2) | includes; `settings` event JSON; persisted-settings path; sensor resolution tables; clamp; settings persistence; clip path helpers; buffer constants and counts; tuning-file checks; `SensorFamily`; ScalerCrop in `controlsForSettings`; sensor detection; sensor-mode selection up to the candidate list's early return |
| Not in this slice | fps limit tables (`tableMaximumFpsForResolution`, :3366+), `normalizedResolutionForSensor` (:2792), the sanitiser. They are in CC.part02 |
| Tuning selection | No changed line in `normalizeTuningFilePath`, `validateTuningFilePath`, `applyProcessTuningFile` (:1382-1440). They only left the libcamera guard (F14). `src/camera/DefaultTuningSelection.hpp` is not changed by the port (`git diff --stat origin/main cinemate-port` on it is empty) |
| Fps limits | None here. Only the state fields `fps_max`, `fps_take_max` (:177-178) and the `camera/FpsCeiling.hpp` include (:2) |

### 0.1 Port commits that wrote lines in this unit

Lines = lines of port 1-2732 that `git blame` gives the commit. Status = fork-log status column, shortened.

| Commit | Lines | Subject (short) | Fork-log | Recorded status |
| --- | --- | --- | --- | --- |
| `014a2bf` | 111 | clip names you can compose | `fork-log.md:138` | host test; WebUI composer and touch card "untested by hand" (`working/drop-frames/README.md:102`) |
| `c48e693` | 64 | add the IMX283 sensor family | `fork-log.md:138` | "Tested: desk only" (commit); "Not yet run on the camera" (row 138) |
| `caa0153` | 56 | imx585 modes from tables, not whitelists | `fork-log.md:138` | "Tested: desk only" (commit); "Not yet run on the camera" (row 138) |
| `d44b177` | 40 | drop-frames squash of 19 commits | `fork-log.md:138` | host tests; Pi build; Log 16 to 12 run on the Pi; "offer (in pieces, after the Pi tests)" |
| `900d282` | 24 | imx585 1.85:1 crops are 3840x2072 and 1920x1036 | `fork-log.md:138` | syntax check only; "Not run on a Pi" (commit) |
| `0041ba0` | 17 | the mode ladder (T34) | `fork-log.md:87` | tested 2026-10-28 (socket, two takes, presets) |
| `e16033e` | 14 | the ladder tells the editor more | `fork-log.md:96` | built 2026-10-28, not tested |
| `5f5cea2` | 14 | build without libcamera again | `fork-log.md:138` | Pi build with libcamera ON and OFF, `--simulate` serving the WebUI |
| `db17860` | 10 | one libcamera request per raw buffer, 8 in Clear HDR | `fork-log.md:31` | Pi, 4K Clear HDR 16-bit, 5 takes per case (commit) |
| `8175273` | 8 | Clear HDR holds ISO and WB | `fork-log.md:61` | tested in preview 2026-10-28 |
| `faa2958` | 8 | speed ramping | `fork-log.md:58` | tested 2026-10-28 (C0030-C0032) |
| `80ddac1` | 6 | frame-rate phase lock | `fork-log.md:37` | "desk only ... not built" (commit); built 22:04 (fork-log) |
| `26da30e` | 6 | profile the recording medium | `fork-log.md:46` | built 23:04, not tested |
| `d7ff071` | 6 | conform_fps | `fork-log.md:67` | "desk only" (commit); tested 2026-10-28 (fork-log) |
| `e625c68` | 5 | Preview temporal denoise switch | `fork-log.md:171` | "desk only (not built)" (commit); Pi only (fork-log) |
| `2edc6d0` | 5 | media tuning file | `fork-log.md:142` | built on the Pi 2026-11-02, Core not restarted yet |
| `ca7b7c2` | 4 | experimental stretched WAV | `fork-log.md:69` | "desk only" (commit); tested 2026-10-28 (fork-log) |
| `dd00206` | 4 | merge of drop-frames PRs #3-#5 | `fork-log.md:138` | merge commit; its 4 lines are `#if` / `#endif` |
| `ce0bd90` | 3 | switch for the drive trim | `fork-log.md:170` | "desk only" (commit); Pi only (fork-log) |
| `d7dd337` | 1 | frames_per_folder | `fork-log.md:186` | host tests; Pi build rc 0 |
| `438a342` | 1 | survive a yanked drive | `fork-log.md:41` | "desk only (not built yet)" (commit); built 22:27 (fork-log) |
| `6ef0ddc` | 1 | APERTAR_RT_CAPTURE_PRIORITY | `fork-log.md:138` | syntax check; "Not run on the Pi" (commit) |
| `646a194` | 1 | iso_actual | `fork-log.md:62` | tested 2026-10-28 |
| `6d217c7` | 1 | iso_max | `fork-log.md:71` | "desk only" (commit); tested 2026-10-28 (fork-log) |
| `97adea0` | 1 | [camera] max_fps; fps_max | `fork-log.md:73` | superseded by `bcedbe5`; `fps_max` stayed |
| `cdf83cd` | 1 | ladder API says resolutions | `fork-log.md:115` | fork-only |

`fork-log.md:180-182` records that the camera runs the `cinemate-port` Core build since the 2026-11-08 13:00 boot. That is a statement about the binary, not a test of any feature below.

## 1. Hunks

| H | Port lines added | Main lines removed | Region | Commits | Feature |
| --- | --- | --- | --- | --- | --- |
| H01 | 1-3, 13-14, 20, 22, 24, 33-37, 43, 63, 74 | none | include block | `80ddac1` (1, 3), `d44b177` (2, 24, 35-36, 43, 63), `c48e693` (13), `caa0153` (14), `e625c68` (20), `d7dd337` (22), `438a342` (33), `26da30e` (34), `014a2bf` (37), `6ef0ddc` (74) | F2-F5, F7, F11, F13, F15 |
| H02 | 153-162, 172, 175-187, 199, 207-210, 229-236 | none | new `ladderTopsJson`; `settingsEvent` | `e16033e`, `d7ff071`, `646a194`, `6d217c7`, `97adea0`, `0041ba0`, `cdf83cd`, `d44b177`, `8175273`, `80ddac1`, `e625c68`, `faa2958`, `ca7b7c2`, `014a2bf` | F1, F4-F11 |
| H03 | 403-416 | none | new `modeLadderPath` | `0041ba0` | F1 |
| H04 | 441-455, 457-461, 471-512, 514-517 | 374, 376-384, 394, 396-404 | IMX585 size helpers | `900d282` (441-463), `caa0153` (471-518) | F2 |
| H05 | 656-687, 696-703, 711-713 | 558-562 | new IMX283 helpers; `clampCaptureSettings` | `c48e693`, `d7ff071`, `014a2bf`, `900d282`, `caa0153` | F2, F3, F4, F8 |
| H06 | 817-818, 823-824, 845-846, 854-855 | none | `loadPersistedCaptureSettings` | `d7ff071`, `8175273`, `d44b177` | F5, F8, F9 |
| H07 | 885-900 | none | `loadPersistedCaptureSettings` | `80ddac1`, `e625c68`, `ce0bd90`, `faa2958`, `ca7b7c2`, `d44b177`, `014a2bf` | F4, F6, F7, F11, F12 |
| H08 | 942, 945, 956, 959, 974-981 | none | `writeCaptureSettings` | same as H06 and H07 | F4-F9, F11, F12 |
| H09 | 1108-1207 | none | new clip-name helpers | `014a2bf` | F4 |
| H10 | 1335-1338, 1355-1356 | 1048 | buffer constants; guard closed | `db17860`, `dd00206` | F13, F14 |
| H11 | 1379-1381 | none | comment above `normalizeTuningFilePath` | `5f5cea2` | F14 |
| H12 | 1443, 1456-1471 | none | guard reopened; new `rawCameraBufferCount` | `5f5cea2`, `db17860`, `26da30e`, `2edc6d0` | F13, F14 |
| H13 | 1660-1681 | none | new `CdngLogTake`, `applyCdngLogFrame` | `d44b177` | F5 |
| H14 | 2268, 2272, 2283-2284 | none | guard closed; `SensorFamily`; `h264CaptureResolutionForSensor` | `5f5cea2`, `c48e693` | F3, F14 |
| H15 | 2309, 2311, 2317 | none | `SensorModeSelection`; guard reopened | `5f5cea2` | F14 |
| H16 | 2486-2501 | 2145-2148 | ScalerCrop block of `controlsForSettings` | `c48e693` | F3 |
| H17 | 2569-2570, 2576, 2581, 2590, 2605, 2624, 2626, 2635-2642 | none | `detectSensorFamily`, `sensorFamilyName`, guards, `sensorModeForRequestedResolution` (IMX283 case) | `c48e693`, `5f5cea2`, `dd00206` | F3, F14 |
| H18 | 2667-2673, 2679, 2687 | 2298-2312, 2316-2319 | `sensorModeForRequestedResolution` (IMX585 case) | `caa0153`, `5f5cea2` | F2, F14 |
| H19 | 2722 | 2363 | `sensorModeCandidatesForRequestedResolution` | `c48e693` | F3 |

No hunk moves code. The 50 removed lines are: two whitelist functions (20), the clamp list (5), one constant (1), the ScalerCrop call (4), the IMX585 case (15 upstream + 4 fork main), one condition (1).

## 2. Features that touch this unit

| # | Feature | What the operator gets | Commits with lines here | What is in this unit | Relation to upstream | Tested (recorded) |
| --- | --- | --- | --- | --- | --- | --- |
| F1 | Mode Ladder | The camera picks the sensor mode (resolution, bit depth, Clear HDR, compression) from the chosen FPS between takes | `0041ba0`, `e16033e`, `cdf83cd`, `d44b177`, `900d282` | `modeLadderPath` (:404-415); `ladderTopsJson` (:153-161); 9 `settings` fields (:178-186); `migrateImx585LadderRungs` (:455-462) | Entirely new area. Here it extends `settingsEvent` in place and adds a copy of `persistedSettingsPath` | `0041ba0` "desk only (ModeLadder host test 28/28)"; `fork-log.md:87` "tested 2026-10-28 (socket, two takes, presets)"; `e16033e` "built, not tested" (`fork-log.md:96`) |
| F2 | IMX585 modes from driver tables | The IMX585 offers the cinemate-port driver's modes (40 SDR sizes per depth, 29 in Clear HDR 12-bit, 33 in Clear HDR 16-bit with the default width policy) where upstream had 2 base modes and 18 crops; the 1.85:1 crops are 3840x2072 and 1920x1036 | `caa0153`, `900d282` | include (:14); `migratedImx585CropResolution` (:446-453); `imx585AliasResolution` (:474-486); `isImx585KnownResolution` (:489-493); `isImx585LegacyCropResolution` (:497-508); `imx585ModeForResolution` (:512-518); clamp (:703, :711); IMX585 case (:2667-2679) | Replaces upstream code (whitelists CC:366-396 @up, if-chain CC:2244-2258 @up) | `caa0153` "desk only (host tests, Pi -fsyntax-only, node --check)"; `900d282` "Not run on a Pi"; `fork-log.md:138` "Not yet run on the camera" |
| F3 | IMX283 sensor family | An IMX283 camera module is recognised and offers 57 modes (42 at 12-bit, 15 at 10-bit) | `c48e693` | include (:13); 4 helpers (:658-686); clamp (:713); enum (:2272); H.264 capture size (:2283-2284); ScalerCrop (:2486-2500); detection (:2569-2570); name (:2581); mode selection (:2635-2642); candidates (:2722) | Extends upstream functions in place (a fifth sensor family in upstream's per-sensor switches) plus a new table header | "Tested: desk only (host tests, Pi -fsyntax-only, node --check)" |
| F4 | Clip name template | The operator composes the clip folder and file name from tokens (date, time, timecode, sensor, resolution, fps, bits, compression, Log, free text); the default is upstream's name | `014a2bf` | include (:37); 2 `settings` fields (:235-236); clamp re-parse (:698-702); persisted key (:899-900, :981); 4 helpers (:1110-1206) | Replaces upstream code (the fixed name in `allocateClipFolder`, CC:3633-3676 @up; the replaced body is at :5202-5209, outside this unit) | host test `tools/clip_name_test.cpp`; "WebUI composer and touch card untested by hand" (`working/drop-frames/README.md:102`) |
| F5 | Log for cDNG and Lossy DNG ("CineMate Log") | One Log On/Off switch stores raw one depth step lower (16 to 12, 12 to 10, 10 to 8 bit) through a log curve | `d44b177` | include (:24); 4 `settings` fields (:207-210); persisted key (:854-855, :959); `CdngLogTake` (:1662-1668); `applyCdngLogFrame` (:1671-1680); `{log}` token (:1185-1186) | Adds a parallel path beside upstream code (Lossy DNG's own companding, `src/lossydng/LossyDngEncoder.hpp:12-13` @up) and beside fork main's `compressClearHdrFrame` (CC:1335 @main) | host test (Log curve); "Log 16 to 12 (12,451,344 bytes a frame)" run on the Pi on an earlier build; "nothing opened in Resolve" (commit `d44b177`) |
| F6 | Speed ramp | FPS can change during a cDNG or MLV take; options for the shutter policy, a stretched WAV and whether the FPS returns after the take | `faa2958`, `ca7b7c2`, `d44b177` | 4 `settings` fields (:231-234); 4 persisted keys (:891-898, :977-980) | Extends upstream functions in place | `faa2958` Pi takes C0030-C0032; `ca7b7c2` "desk only" (commit), tested 2026-10-28 (`fork-log.md:69`); the `after=` option: no test recorded |
| F7 | Frame-rate phase lock | A switch that holds the sensor's frame cadence to the Pi clock so long takes do not drift against the audio | `80ddac1` | includes at the top of the file (:1, :3); `settings` field (:229); persisted key (:885-886, :974) | Entirely new area. Here it extends functions in place | "desk only (servo passes phase_lock_sim.cpp on the Mac; not built)" (commit); built (`fork-log.md:37`) |
| F8 | Conform FPS | A stored project timeline rate (default 25). No control in either UI; nothing reads it | `d7ff071` | `settings` field (:172); clamp (:696-697); persisted key (:817-818, :942) | Extends upstream functions in place | "desk only" (commit); tested 2026-10-28 (`fork-log.md:67`) |
| F9 | Clear HDR holds ISO and WB | Entering Clear HDR turns auto ISO and auto WB off at the measured values and turns them back on in SDR | `8175273` | 2 `settings` fields (:187, :199); 2 persisted keys (:823-824, :845-846, :945, :956) | Extends upstream functions in place (on top of fork main's Clear HDR) | Pi preview (commit; `fork-log.md:61`) |
| F10 | Measured ISO and mode ceilings in the state | The UIs can show the gain in use and the highest ISO and FPS the current mode allows | `646a194`, `6d217c7`, `97adea0` | `settings` fields `iso_actual`, `iso_max`, `fps_max` (:175-177); `fps_take_max` (:178) is counted with F1 | Extends an upstream function in place | `646a194` Pi preview; `6d217c7` "desk only" (commit), tested (`fork-log.md:71`); `97adea0` superseded by `bcedbe5` |
| F11 | Preview temporal denoise switch | A switch for temporal denoise in the preview ISP. Default off: the preview loses it; DNGs do not change | `e625c68` | include (:20); `settings` field (:230); persisted key (:887-888, :975) | Adds a parallel path beside upstream code (a derived tuning file, used at :7311-7316, outside this unit) | "desk only (not built: no libcamera on the Mac)"; host test `tools/tuning_tdn_strip_test.cpp` |
| F12 | Drive trim switch | A switch (default on) for trimming the recording drive after big deletes and at mount | `ce0bd90` | persisted key `media_trim` (:889-890, :976). No `settings` field | Entirely new area. Here it extends functions in place | "desk only" (commit) |
| F13 | Raw camera buffers | No control. Raw takes queue one libcamera request per buffer: 4 in SDR, 8 in Clear HDR, 2 more on FAT and NTFS, or a count from the tuning file or the environment | `db17860`, `26da30e`, `2edc6d0` | `kClearHdrBufferCount` (:1335-1338); `rawCameraBufferCount` (:1458-1470); include (:34); `kActiveRequestCount` removed | Replaces upstream code (`kActiveRequestCount`, CC:1024 @up) and adds a third helper beside `h264CameraBufferCount` and `proresCameraBufferCount` | `db17860` Pi, 4K Clear HDR 16-bit (capture gaps 41 to 1 per take); `26da30e` "built, not tested"; `2edc6d0` "Core not restarted yet" |
| F14 | Build without libcamera | Nothing for the operator. A developer can compile Core with `APERTARCORE_ENABLE_LIBCAMERA=OFF` and run `--simulate` | `5f5cea2`, `dd00206` | 18 guard and comment lines (:1355-1356, :1379-1381, :1443, :2268, :2309, :2311, :2317, :2576, :2590, :2605, :2624, :2626, :2637, :2639, :2687) | Extends upstream code in place (preprocessor guards around upstream helpers) | Pi build with libcamera ON and OFF, `--simulate` serving the WebUI (`fork-log.md:138`); syntax check here, section 11 |
| F15 | Include lines only | Nothing here. The features are in later slices | `438a342`, `d44b177`, `d7dd337`, `6ef0ddc` | `util/MediaFault.hpp` (:33, first use :4249); `camera/FpsCeiling.hpp` (:2, first use :3121); `util/BufferBudget.hpp` (:35, first use :2988); `util/StoragePreroll.hpp` (:36, only use :12157); `cdng/FramePath.hpp` (:22, first use :4294); `<sched.h>` (:74, use :9109-9122); `<cassert>` (:43, one `assert` at :4596); `<memory>` (:63) | Entirely new area | see table 0.1 |

## 3. Interface inventory

### 3.1 `settings` event: 27 fields added, none removed or renamed

Emitted by `settingsEvent` (:163-246), called from :12870. Upstream's function is CC:136-187 @up.
The port added the same 27 keys to both state builders in `ApertarCoreApp.cpp` (2 hits each, `grep -c` per key).

| Field | JSON type | Source | Line | Commit | Persisted |
| --- | --- | --- | --- | --- | --- |
| `conform_fps` | number | `settings.conformFps` | :172 | `d7ff071` | yes |
| `iso_actual` | number | `settings.isoMeasured` | :175 | `646a194` | no (runtime) |
| `iso_max` | number | `settings.isoMax` | :176 | `6d217c7` | no |
| `fps_max` | number | `settings.fpsMax` | :177 | `97adea0` | no |
| `fps_take_max` | number | `settings.fpsTakeMax` | :178 | `0041ba0` | no |
| `ladder_active` | bool | `settings.ladderActive` | :179 | `0041ba0` | no |
| `ladder_resolution` | number | `settings.ladderRung` | :180 | `cdf83cd` | no |
| `ladder_ramp_ready` | bool | `settings.ladderRampReady` | :181 | `0041ba0` | no |
| `ladder_enabled` | bool | `settings.ladderEnabled` | :182 | `e16033e` | no (lives in `mode_ladder.conf`) |
| `ladder_override` | bool | `settings.ladderOverride` | :183 | `d44b177` | no |
| `ladder_count` | number | `settings.ladderCount` | :184 | `e16033e` | no |
| `ladder_text` | string | `escapeJson(settings.ladderText)` | :185 | `e16033e` | no |
| `ladder_tops` | array of numbers | `ladderTopsJson(settings.ladderTops)` | :186 | `e16033e` | no |
| `iso_auto_after_clear_hdr` | bool | `settings.isoAutoAfterClearHdr` | :187 | `8175273` | yes |
| `wb_auto_after_clear_hdr` | bool | `settings.whiteBalanceAutoAfterClearHdr` | :199 | `8175273` | yes |
| `cdng_log` | string `off` or `auto` | `toString(settings.cdngLog)` | :207 | `d44b177` | yes |
| `cdng_log_bits` | number | `cdngLogBits(settings)` | :208 | `d44b177` | no |
| `cdng_log_available` | bool | `cdngLogAvailable(settings.recordingFormat)` | :209 | `d44b177` | no |
| `cdng_log_applied` | bool | `settings.cdngLogApplied` | :210 | `d44b177` | no |
| `fps_phase_lock` | bool | `settings.fpsPhaseLock` | :229 | `80ddac1` | yes |
| `preview_tdn` | bool | `settings.previewTdn` | :230 | `e625c68` | yes |
| `fps_speed_ramp` | bool | `settings.fpsSpeedRamp` | :231 | `faa2958` | yes |
| `fps_speed_ramp_keep_exposure` | bool | `settings.fpsSpeedRampKeepExposure` | :232 | `faa2958` | yes |
| `fps_speed_ramp_stretch_audio` | bool | `settings.fpsSpeedRampStretchAudio` | :233 | `ca7b7c2` | yes |
| `fps_speed_ramp_after` | string `return` or `stay` | `settings.fpsSpeedRampReturn` | :234 | `d44b177` | yes |
| `clip_name_template` | string | `escapeJson(settings.clipNameTemplate)` | :235 | `014a2bf` | yes |
| `clip_name_example` | string | `escapeJson(settings.clipNameExample)` | :236 | `014a2bf` | no |

Upstream facts for comparison:

| Fact | Evidence |
| --- | --- |
| The upstream `settings` event already holds an array and a nested object | `exposure_metering_modes` array, `src/camera/ExposureMetering.hpp:28-39` @up; `recording_capabilities` object, `include/apertar/core/RecordingCapabilities.hpp:52-62` @up |
| Upstream spells the settings JSON out three times | CC:136 @up; `src/ApertarCoreApp.cpp:192` and `:7876` @up (`recording_capabilities` lines) |
| Upstream keeps runtime-only members in `CaptureSettings` | `include/apertar/core/Types.hpp:132, 134, 139, 142-143, 150` @up |
| The port adds 14 runtime members and 12 persisted ones to `CaptureSettings` | `include/apertar/core/Types.hpp:137-192` @cinemate-port (runtime: :157, :177-189) |

### 3.2 `~/.config/apertar-core/camera_settings.conf`: 12 keys added, none removed

Flat `key=value`, repeated with the prefix `profile.<still|cdng|mlv|h264|prores>.` per profile (:794-808, :995-999; same as upstream).
Load = `loadPersistedCaptureSettings` (:776-934; CC:616-740 @up). Write = `writeCaptureSettings` (:936-989; CC:742-778 @up).

| Key | Value form | Load | Write | Default (`Types.hpp` @cinemate-port) | Commit |
| --- | --- | --- | --- | --- | --- |
| `conform_fps` | number, 6 decimals; clamp 1-120 else 25 (:696-697) | :817-818 | :942 | 25.0 (:137) | `d7ff071` |
| `iso_auto_after_clear_hdr` | `0` / `1` (`std::stoul(value) != 0`) | :823-824 | :945 | false (:160) | `8175273` |
| `wb_auto_after_clear_hdr` | `0` / `1` | :845-846 | :956 | false (:174) | `8175273` |
| `cdng_log` | `off` / `auto`; also reads `on`, `12`, `10`, `8` as auto (`Types.hpp` `cdngLogFromString`) | :854-855 | :959 | Off (:192) | `d44b177` |
| `fps_phase_lock` | `true` / `false`; reads `true` or `1` | :885-886 | :974 | false (:138) | `80ddac1` |
| `preview_tdn` | `true` / `false` | :887-888 | :975 | false (:139) | `e625c68` |
| `media_trim` | `true` / `false`; anything but `false` or `0` is true | :889-890 | :976 | true (:140) | `ce0bd90` |
| `fps_speed_ramp` | `true` / `false` | :891-892 | :977 | false (:143) | `faa2958` |
| `fps_speed_ramp_keep_exposure` | `true` / `false` | :893-894 | :978 | false (:146) | `faa2958` |
| `fps_speed_ramp_stretch_audio` | `true` / `false` | :895-896 | :979 | true (:149) | `ca7b7c2` |
| `fps_speed_ramp_after` | `return` / `stay` | :897-898 | :980 | stay (:152) | `d44b177` |
| `clip_name_template` | template text; re-parsed at every clamp, a bad one becomes `{format}_{date}_{clip}` (:698-702) | :899-900 | :981 | `{format}_{date}_{clip}` (:156) | `014a2bf` |

Boolean styles in the file: upstream writes `0` / `1` (`iso_auto`, CC:659-660 and :749 @up). `true` / `false` first appears in fork main (`clear_hdr`, CC:710-711 and :784 @main). The port uses both.

### 3.3 Files on disk

| File | Read or written here | Keys | Evidence |
| --- | --- | --- | --- |
| `$XDG_CONFIG_HOME/apertar-core/mode_ladder.conf`, else `~/.config/apertar-core/mode_ladder.conf`, else `<tmp>/apertar-core-mode_ladder.conf` | Path built here (:404-415). Read in the controller's constructor (:10510-10514), written at :10942-10944 with `settingsFile::atomicWrite` | `enabled`, `ramp_ready`, `resolutions` (reads the old name `rungs` too) | `src/camera/ModeLadder.hpp:317-340` |
| `camera_settings.conf` (same directory) | 12 new keys | table 3.2 | |
| Clip folders under the media root | Name built here by `nextClipFolderName` (:1191-1206) from the template | | `src/util/ClipName.hpp:211-294` |
| `/home/pi/apertar-media-tune.conf` and `/run/apertar-media/media-tune.override.conf` | Read through `mediaTuneForConfiguredRoot()` in `rawCameraBufferCount` (:1466-1468) | `raw_buffers` (3-16), `extra_raw_buffers` (0-8) for this unit | `src/util/MediaTune.hpp:27-28, 34-35`; `src/util/MediaProfile.hpp:222-234` |
| `/sys/class/block/<disk>/device` and its `uevent` | Read through `mediaExtraRawBuffersForConfiguredRoot()` (:1466) | | `src/util/MediaProfile.hpp:110-121` |

Upstream's files for comparison: `camera_settings.conf` (CC:346 @up), `UI.conf` (`sharedUiSettingsPath`, `src/ApertarCoreApp.cpp:341-348` @up, the same XDG rule), `apertar-hardware.conf` (`src/ApertarCoreApp.cpp:3408-3410` @up), `.apertar-preset.json` (`src/ApertarCoreApp.cpp:5163` @up).

### 3.4 Environment variables

| Variable | Where read | Meaning | New |
| --- | --- | --- | --- |
| `APERTAR_RAW_CAMERA_BUFFERS` | :1469 | raw buffer and request count, 3-16; wins over the tuning file and the default | yes (`db17860`) |
| `APERTAR_IMX585_MIN_MODE_WIDTH` | `src/camera/Imx585Modes.hpp:105-114`; reached from :515-517 through the default argument of `find` and `nearest` | IMX585 modes narrower than n are hidden; default 1280; 0 shows all | yes (`caa0153`) |
| `XDG_CONFIG_HOME`, `HOME` | :406-412 | location of `mode_ladder.conf`; same rule as `persistedSettingsPath` | reuse |
| `APERTAR_H264_CAMERA_BUFFERS`, `APERTAR_PRORES_CAMERA_BUFFERS` | :1447, :1453 | unchanged upstream code (CC:1127, :1133 @up) | no |

### 3.5 Socket commands, HTTP routes, UI elements

None is defined in this unit. The commands of the features above are in `ApertarCoreApp::handleCommand` (@cinemate-port):

| Command | App line | Upstream | Reaches this unit through |
| --- | --- | --- | --- |
| `get_mode_ladder`, `set_mode_ladder` | :14090, :14093 | new | `modeLadderPath`, `migrateImx585LadderRungs` |
| `set_clip_name_template`, `preview_clip_name` | :13241, :13258 | new | `nextClipFolderName`, clamp re-parse |
| `set_cdng_log` | :13079 | new | `cdng_log` key and fields |
| `set_fps_speed_ramp` | :13223 | new | 4 keys and fields |
| `set_fps_phase_lock` | :13214 | new | `fps_phase_lock` |
| `set_conform_fps` | :13270 | new | `conform_fps` |
| `set_preview_tdn` | :13205 | new | `preview_tdn` |
| `set_media_trim` | :13194 | new | `media_trim` |
| `set_resolution` | :13042 | exists (App:9314 @up) | `clampCaptureSettings` now accepts table sizes and rewrites 3840x2076 and 1920x1038 |
| `set_iso_auto`, `set_wb_auto` | :12995, :13036 | exist (App:9269, :9308 @up) | `iso_auto_after_clear_hdr`, `wb_auto_after_clear_hdr` |

WebUI senders exist for all of these except `set_conform_fps` (0 hits in `src/web/WebControlPage.cpp`; only the preset key `cameraConformFps` at WCP:19111). Touch UI: 0 hits for `conform_fps`, `fps_phase_lock`, `set_mode_ladder`, `set_preview_tdn`, `set_media_trim`, `set_fps_speed_ramp` (`grep -rn` in `/home/user/Apertar-UI`).

### 3.6 Clip-name token values built in this unit

These end up in folder and file names on the recording medium. Built by `clipNameValues` (:1134-1188).

| Token | Value | Line |
| --- | --- | --- |
| `{format}` | `cDNG`, `cDNG_3to1`, `cDNG_5to1`, `MLV`, `H264`, `ProRes` (upstream's prefixes without the underscore, CC:3646-3659 @up) | :1110-1120 |
| `{res}` | `8K` (width 7000 or more), `4K` (3500 or more), `1080p` (1900-1999 wide, at most 1100 high), `2K` (2000-3499 wide), else `<height>p`. H.264 and ProRes use the encode size when one is set | :1123-1130, :1163-1166 |
| `{fps}` | the rate as a whole number or with up to 3 decimals, then `fps` | :1167-1178 |
| `{bits}` | `<n>bit`; 10 for ProRes; empty for H.264 | :1179-1180 |
| `{comp}` | `lossless` or `none` for cDNG, `lossy3` or `lossy5` for Lossy DNG, empty otherwise | :1181-1184 |
| `{log}` | `Log` when Log is on and the format can carry it | :1185-1186 |
| `{cam}` | the constant `cam0` | :1157 |
| `{sensor}` | the sensor name passed in, at most 12 characters | :1158 |
| `{model}` | the DNG model without the `Apertar ` prefix, at most 16 characters; `Apertar` when empty | :1159-1162 |
| `{date}`, `{time}`, `{tc}` and variants | local wall clock at take start; the `{tc}` frame is the index within the second at the current fps | :1139-1155 |

`nextClipFolderName` (:1191-1206) throws "Could not allocate a unique clip folder." when all 9999 numbers are taken, the same text as upstream (CC:3675 @up).

## 4. Original code changed

Upstream lines are @up. "fm" marks a line that fork main wrote, not upstream.

| # | Region | Upstream lines | Port lines | Change | Kind | Commits |
| --- | --- | --- | --- | --- | --- | --- |
| C1 | include block | CC:1-67 | :1-84 | 16 includes added. Three sit above the file's own header `camera/CameraController.hpp` (:1-3); upstream has the own header first (CC:1 @up) | extended-in-place | 10 commits, see H01 |
| C2 | `settingsEvent` | CC:136-187 | :163-246 | 27 fields inserted between upstream's fields. No upstream field removed, renamed or reordered | extended-in-place | 14 commits, see H02 |
| C3 | `isImx585FullHdCropResolution` | CC:366-377 | gone | Function removed. Its nine heights live on in `isImx585LegacyCropResolution` (:499) with 1038 changed to 1036 | removed | `900d282`, `caa0153` |
| C4 | `isImx585Raw12CropResolution` | CC:385-396 | gone | Function removed. Its nine heights live on in `isImx585LegacyCropResolution` (:503) with 2076 changed to 2072 | removed | `900d282`, `caa0153` |
| C5 | `clampCaptureSettings`, added steps | CC:534-601 | :688-761 | Three steps added at the top: conform fps clamp (:696-697), clip template re-parse (:698-702), IMX585 crop migration (:703) | extended-in-place | `d7ff071`, `014a2bf`, `900d282` |
| C6 | `clampCaptureSettings`, accepted sizes | CC:549-553 | :711-713 | The four IMX585 whitelist calls became `isImx585KnownResolution` (any row of any of the four tables, hidden rows included, plus the low and high alias sizes); `isImx283Resolution` added. Saved 3840x2076 and 1920x1038 are rewritten to 3840x2072 and 1920x1036 for every sensor | behaviour-changed | `caa0153`, `c48e693`, `900d282` |
| C7 | `loadPersistedCaptureSettings` | CC:616-740 | :776-934 | 12 `else if (key == ...)` branches added | extended-in-place | see H06, H07 |
| C8 | `writeCaptureSettings` | CC:742-778 | :936-989 | 12 output lines added | extended-in-place | see H08 |
| C9 | `kActiveRequestCount` | CC:1024 | gone | Constant removed. Upstream configured 4 raw buffers (CC:6079-6081) and queued 3 requests (CC:6460-6461). The port uses `rawCameraBufferCount` for both (:8379-8381, :8846-8848): 4 and 4 in SDR, 8 and 8 in Clear HDR | removed, behaviour-changed | `db17860` |
| C10 | libcamera guard | one block CC:1017-5226 | split | The guard is closed and reopened so that these compile without libcamera: `boolEnvValue`, `normalizeTuningFilePath`, `validateTuningFilePath`, `applyProcessTuningFile` (:1357-1440); `SensorFamily`, `h264CaptureResolutionForSensor`, `processedVideoCaptureResolutionForSensor`, `SensorModeSelection` (:2269-2314); `sensorFamilyName` (:2577-2588); `imx294ReadoutForActiveResolution`, `sensorModeForRequestedResolution` (:2606-2685). No code line moved | extended-in-place | `5f5cea2`, `dd00206` |
| C11 | `struct SensorModeSelection` | CC:1916-1922 | :2306-2314 | The member `rawPixelFormat` is inside `#if APERTARCORE_HAS_LIBCAMERA`; so are its two assignments (:2624-2626, :2637-2639) | extended-in-place | `5f5cea2`, `dd00206` |
| C12 | `enum class SensorFamily` | CC:1882-1888 | :2269-2276 | `Imx283` inserted between `Imx294` and `Imx477`. No cast of the enum to an integer exists in CC | extended-in-place | `c48e693` |
| C13 | `h264CaptureResolutionForSensor` | CC:1890-1906 | :2278-2296 | `case SensorFamily::Imx283` returns 3840x2160 | extended-in-place | `c48e693` |
| C14 | ScalerCrop block in `controlsForSettings` | CC:2082-2102 | :2475-2507 | The single `if (const auto crop = cropFunction(...))` (CC:2093-2096) became a variable plus a branch: IMX283 takes `activeAreaScalerCrop` then `centeredPreviewScalerCrop`; every other sensor takes the upstream call unchanged | extended-in-place | `c48e693` |
| C15 | `detectSensorFamily` | CC:2151-2167 | :2556-2574 | `imx283` substring test added before `imx585` | extended-in-place | `c48e693` |
| C16 | `sensorFamilyName` | CC:2169-2179 | :2577-2588 | `IMX283` | extended-in-place | `c48e693` |
| C17 | `sensorModeForRequestedResolution`, IMX283 | CC:2205-2269 | :2635-2642 | New case: depth forced to 10 or 12; raw size = active size plus the optical-black columns and rows | extended-in-place | `c48e693` |
| C18 | `sensorModeForRequestedResolution`, IMX585 | CC:2244-2258 | :2667-2679 | The if-chain became a table lookup. The class comes from the bit depth alone: `classFor(selection.bitDepth, selection.bitDepth == 16)` (:2670), so 12-bit Clear HDR resolves through the SDR 12-bit table here. A size the class lacks takes the nearest row (:517); upstream fell back to 1920x1080 (CC:2259-2261), which is now reached only when the width policy hides the whole class | rewritten, behaviour-changed | `caa0153` |
| C19 | 16-bit Clear HDR raw size (fm) | CC:2316-2319 @main | :2672-2673 | Fork main's "3840x2160 at 16-bit becomes 3840x2200" is gone. `imx585::transportFor` adds 40 rows at 1x1 and 20 rows binned for every 16-bit row (`src/camera/Imx585Modes.hpp:203-208`) | rewritten | `caa0153` |
| C20 | `sensorModeCandidatesForRequestedResolution` | CC:2305 | :2722 | IMX283 returns after the first candidate, as IMX294 does | extended-in-place | `c48e693` |

Unchanged neighbours worth knowing: `persistedSettingsPath` (:417-428), `isImx585LowResolutionAlias` (:435-439), `isImx585HighResolutionAlias` (:464-469, with fork main's 3840x2200), `isSupportedH264Resolution` still lists 1920x1038 as an encode size (:325).

## 5. New abstractions

| Name | Files | Purpose | What upstream uses for the same job | Used by |
| --- | --- | --- | --- | --- |
| `apertar::imx585` mode tables | `src/camera/Imx585Modes.hpp` (254 lines, header only, std only); host test `tools/imx585_modes_test.cpp` | Four tables of the cinemate-port driver's modes (62, 62, 29, 34 rows), class from depth and Clear HDR, raw size with optical-black rows, width policy, exact and nearest lookup | Whitelist functions in the .cpp: `isImx585FullHdCropResolution`, `isImx585Raw12CropResolution`, CC:366-396 @up; the if-chain CC:2244-2261 @up | :489-518, :2667-2679; 16 uses in CC |
| `apertar::imx283` mode table | `src/camera/Imx283Modes.hpp` (144 lines, header only); host test `tools/imx283_modes_test.cpp` | 57 modes (depth, binning, active size, fps floor), raw size rule, normaliser | Per-sensor functions in the .cpp: `isImx294Resolution` CC:462-477, `normalizedImx294ResolutionForBitDepth` CC:511-532, `imx294ReadoutForActiveResolution` CC:2193-2203 @up | :658-686; 7 uses in CC |
| IMX585 size migration | `migratedImx585CropResolution` :446-453; `migrateImx585LadderRungs` :455-462 | Moves saved or requested 3840x2076 and 1920x1038 to the new driver's sizes | Upstream retires saved selections inside the normaliser: "Retire the small central RAW windows, including saved selections", CC:513-518 @up; `wb_locked`, CC:681-682 and :727-728 @up | :703; :10514, :10648, :11060, :12663 |
| `apertar::clipname` template engine | `src/util/ClipName.hpp` (296 lines, header only); host test `tools/clip_name_test.cpp`; helpers :1110-1206 | Parses and expands a clip-name template with 19 tokens plus `{text:..}`; picks the lowest free clip number | The fixed name built inline in `allocateClipFolder`, CC:3633-3676 @up. Still and timelapse names stay hard-coded (`Still_`, `Timelapse_`, CC:943, :986 @up; unchanged in the port) | :700-701, :1134-1206; :5209, :11828, :11867 |
| `modeLadderPath()` | :404-415 | Path of `mode_ladder.conf` | `persistedSettingsPath()`, CC:342-353 @up. The new function is a copy with the file name changed | :10510, :10942-10944 |
| `apertar::ladder` | `src/camera/ModeLadder.hpp` (344 lines, header only), included by `CameraController.hpp:4` | The Mode Ladder's types and pure logic. Only `ladder::Rung` is used in this unit (:455-457) | None. Upstream derives the sensor mode from the operator's resolution and bit depth only (`sensorModeForRequestedResolution`, CC:2205 @up) | 38 uses in CC |
| `ladderTopsJson` | :153-161 | Prints a vector of doubles as a JSON array | Arrays printed inline: `exposureMeteringJson`, `src/camera/ExposureMetering.hpp:28-39` @up | :186 |
| `rawCameraBufferCount(bool clearHdr)` | :1458-1470 | Raw buffer and request count: env, else tuning file `raw_buffers`, else 4 or 8 plus the medium's extra, capped at 16 | `h264CameraBufferCount` CC:1124-1128 @up, `proresCameraBufferCount` CC:1130-1134 @up; constants CC:1023-1024 @up | :8381, :8736, :8848 |
| Media profile and tuning file | `src/util/MediaProfile.hpp` (236 lines), `src/util/MediaTune.hpp`, both header only | Classify the recording medium (class from sysfs, filesystem) and read per-medium write knobs from an ini file | None for the medium. Upstream buffer counts depend on the format and on `recordingCapabilities()` (CC:1126 @up). Upstream config lives in `apertar-hardware.conf` | :1466-1467; :4364, :4718, :10543 |
| `CdngLogTake`, `applyCdngLogFrame` | :1662-1668, :1671-1680 | One take's Log tables; applies a table to a frame copy row by row | Fork main's `compressClearHdrFrame` (CC:1335-1346 @main) has the same row loop. Upstream's companding lives inside `LossyDngEncoder` (`src/lossydng/LossyDngEncoder.hpp:12-13`, `src/lossydng/LossyDngEncoder.cpp:477` @up) and reaches the DNG through `CdngEncoder::Metadata::linearizationTable` (`src/cdng/CdngEncoder.hpp:27` @up) | :4016-4037, :5045-5125, :7739 |
| `apertar::cdnglog` | `src/cdng/LogCurve.hpp` (205 lines, header only); host test `tools/log_curve_test.cpp` | The Log curve: parameters, forward and inverse tables | as above | 10 uses in CC, 3 here |
| `activeAreaScalerCrop` | `src/camera/ScalerCropGeometry.hpp:66-92` (upstream header, 28 lines added) | ScalerCrop for a frame with optical-black columns on the left and rows at the bottom | `centeredRawWindowScalerCrop`, `centeredPreviewScalerCrop` in the same header @up | :2492 |
| Headers included here, used later | `camera/FramePhaseLock.hpp` (158), `camera/FpsCeiling.hpp` (47), `camera/TuningTdnStrip.hpp` (451), `cdng/FramePath.hpp` (79), `util/MediaFault.hpp` (108), `util/BufferBudget.hpp` (382), `util/StoragePreroll.hpp` (273) | See F7, F11, F15 | Header-only helper modules exist upstream in the same folders: `src/camera/ScalerCropGeometry.hpp`, `src/camera/DefaultTuningSelection.hpp` (`apertar::tuning`), `src/util/SettingsFile.hpp` (`apertar::settingsFile`), `src/cdng/BlackLevel.hpp` @up. Upstream has no `tools/` folder and no tests | later slices |

All 12 headers named in H01 are new files (absent @up and @main). None has a .cpp.

## 6. Removed, narrowed or hidden

| # | What upstream had | Where | Effect in the port |
| --- | --- | --- | --- |
| R1 | IMX585 crops 3840x2076 and 1920x1038 (the 1.85:1 modes) | CC:368, :387 @up; driver `imx585.c:817, 1007` @origin/apertar | Not selectable. Any setting, preset, ladder rung or request with these sizes is rewritten to 3840x2072 or 1920x1036 (:446-453, :703). The stock Apertar driver has no 2072 or 1036 mode (`git grep` on `origin/apertar`: no hit) |
| R2 | `isImx585FullHdCropResolution`, `isImx585Raw12CropResolution` | CC:366-396 @up | Removed. Callers in later slices use the tables or `isImx585LegacyCropResolution` |
| R3 | `kActiveRequestCount = 3`: one of the 4 raw buffers stayed out of the request queue | CC:1024, :6460-6461 @up | Removed. Requests equal buffers |
| R4 | Fallback to 1920x1080 for an unknown IMX585 size | CC:2259-2261 @up | Narrowed to the case where the width policy hides the whole class; otherwise the nearest table row is used (:512-518) |
| R5 | Preview temporal denoise as the tuning file defines it | tuning file loaded unchanged @up | Off by default: `previewTdn = false` (`Types.hpp:139`); with it off libcamera loads a copy of the tuning file without the tdn members (:7311-7316, outside this unit). The key is persisted here (:887-888, :975) |
| R6 | Fork main: 16-bit Clear HDR only as 3840x2200 | CC:2316-2319 @main | Replaced by one raw size per table row |
| R7 | IMX585 modes narrower than 1280 px (driver modes, not upstream ones) | `src/camera/Imx585Modes.hpp:101-114` | Hidden unless `APERTAR_IMX585_MIN_MODE_WIDTH` is set: 22 of 62 SDR rows per depth |

Nothing else from upstream is removed in this slice: no `settings` field, no persisted key, no helper besides R2 and R3.

## 7. Board and driver assumptions

| # | Assumption | Where |
| --- | --- | --- |
| B1 | The IMX585 driver is the `cinemate-port` branch. Core's four tables copy its mode list; the comment says "the new driver has neither" of the old 1.85:1 sizes | :441-445; `src/camera/Imx585Modes.hpp:3-16`; commit `900d282` |
| B2 | The IMX283 driver is `Tiramisioux/imx283-v4l2-driver` `cinemate-port` with `experimental_modes=0`. Mode sizes, optical-black offsets (96x16, 48x4, 32x4) and fps floors are constants in Core | `src/camera/Imx283Modes.hpp:1-10, 32-62` |
| B3 | Clear HDR raw buffers are 16.9 MB each "on the CPU-cached heap" and 8 are allocated (135 MB); up to 16 through the env or the tuning file. No check against RAM, CMA or `recordingCapabilities()` | :1335-1338, :1458-1470 |
| B4 | The comment names the CFE (the Pi 5 camera front end): "the CFE needs more than two left to queue" | :1337 |
| B5 | Media class names assume a Pi NVMe (`MediaClass::PiNvme`); the class is read from `/sys/class/block/<disk>/device`. The class does not change the buffer count today (`writerSettingsFor` ignores it) | `src/util/MediaProfile.hpp:26, 110-121, 136` |
| B6 | The tuning file path is `/home/pi/apertar-media-tune.conf`; the override needs `/run/apertar-media/` from a tmpfiles rule. Upstream hard-codes `/home/pi/apertar-hardware.conf` too (`src/ApertarCoreApp.cpp:3408` @up) | `src/util/MediaTune.hpp:27-28` |
| B7 | One camera per unit: the `{cam}` token is the constant `cam0`; `{model}` comes from the default DNG model string | :1157, :1159-1162 |
| B8 | IMX283 H.264 capture uses the 10-bit 3840x2160 window ("MODE_1C") | :2283-2284 |
| B9 | `<sched.h>` is included for `SCHED_FIFO` on the capture thread (needs `LimitRTPRIO` in the service); the code is at :9109-9122, outside this unit | :74 |
| B10 | No Pi model, core count, RP1, PCIe, fan, I2C bus or gpiochip number appears in lines 1-2732 at either ref (`grep` in section 11) | |

Upstream's own board switches, for the later stages: `recordingCapabilities()` reads the device-tree `compatible` and separates bcm2712, bcm2711 and older (`include/apertar/core/RecordingCapabilities.hpp:18-50` @up); `tuning::nativePipeline()` separates PiSP from VC4 (`src/camera/DefaultTuningSelection.hpp:16-49` @up).

## 8. Internal names in added comments

| Line | Text |
| --- | --- |
| :403 | "T34: the mode ladder lives beside camera_settings.conf" |
| :441-442 | "(cinemate-modes, the cinemate-port driver branch)" |
| :442 | "The Apertar-Beta 1.6.0 driver had 3840x2076 and 1920x1038" |
| :1462 | "as Cinemate's profiles do (8 ext4 / 10 exFAT-NTFS)" |
| :1660 | "One take's CineMate Log" |

## 9. Facts for the next stages (not judged here)

| # | Fact | Evidence |
| --- | --- | --- |
| N1 | `conform_fps` is stored, published and carried across formats. No code reads it and neither UI has a control | `grep -n conformFps` in CC: :172, :696-697, :818, :942, :11354, :11364, :11812; `Types.hpp:135-137` "nothing derives from it yet"; section 3.5 |
| N2 | `media_trim` is persisted with the camera settings but is not in the `settings` event; its state fields are in the App only | :889-890, :976; `src/ApertarCoreApp.cpp:9584-9585` |
| N3 | The comment above `rawCameraBufferCount` says exFAT gets two more buffers. The table gives exFAT 0 | :1461-1463; `src/util/MediaProfile.hpp:142` |
| N4 | `sensorModeForRequestedResolution` has no Clear HDR argument, so the Clear HDR 12-bit table is never used there; `normalizedResolutionForSensor` passes it | :2670; :2832-2833 |
| N5 | `modeLadderPath` repeats `persistedSettingsPath` line for line except the file name | :404-415, :417-428 |
| N6 | `applyCdngLogFrame` repeats the row loop of `compressClearHdrFrame` | :1647-1658, :1671-1680 |
| N7 | `clipNameValues` repeats the local-time block of `allocatePhotoBasePath` and `allocateTimelapseFolder` | :1141-1146; CC:935-940, :978-983 @up |
| N8 | Three includes stand above the file's own header | :1-3 |
| N9 | Namespace spelling differs between the two table users: `imx283::` (:660) and `apertar::imx585::` (:491) | |
| N10 | The JSON key says `ladder_resolution`, the member is `ladderRung` | :180 |
| N11 | `clampCaptureSettings` now parses the clip template on every call; it runs on every persist and every write | :698-702; callers :925, :931, :933, :938, :1016 |
| N12 | Upstream 1.6.0 and fork main do not compile CC with `APERTARCORE_HAS_LIBCAMERA=0`; the port does | section 11 |
| N13 | With the default template the name equals upstream's: `{format}` gives upstream's prefixes without the underscore, `{date}` is `yy-mm-dd`, `{clip}` is `C` plus 4 digits, the lowest free number wins | :1110-1120 against CC:3646-3659 @up; `ClipName.hpp:110-129, 287-294` against CC:3664-3672 @up |
| N14 | **P**: with the stock Apertar IMX585 driver the port asks for 3840x2072 or 1920x1036, which that driver lacks. The driver side is confirmed; the configure path was not read in this unit. Settle with `grep -n SensorConfiguration src/camera/CameraController.cpp` and the IMX585 branch of `configure` | R1, B1 |

## 10. Relayed user request: the GPIO chip definition

The request ("reinsert the definition of the chip, other GPIO chips such as a microcontroller's may be chosen") does not touch this unit.

| Fact | Evidence |
| --- | --- |
| CC has no GPIO or gpiochip code at any ref | `grep -n -i gpio` on CC @cinemate-port and @up: no hit |
| Upstream reads the chip per hardware class with the keys `chip`, `gpiochip`, `gpio_chip` and the value `auto` | `src/hardware/GpioInput.cpp:431`, `src/hardware/TriggerOutput.cpp:311`, `src/hardware/RecordingIndicatorOutput.cpp:319, 347` @up; template `gpiochip=auto`, `src/ApertarCoreApp.cpp:4380, 4394` @up |
| The port touched chip handling in `src/hardware/GpioInput.cpp` (+3 / -5 chip lines), added `src/hardware/GpioChipInfo.hpp`, and reads `[gpio_buttons] chip` in the App | `git diff --minimal origin/main cinemate-port -- src/hardware/GpioInput.cpp src/ApertarCoreApp.cpp`, filtered for `chip` |

The units that hold `GpioInput.cpp`, the App's Controls code and the WebUI Controls page carry this request.

## 11. Checks run

| K | Check | Result |
| --- | --- | --- |
| K1 | Slice equals the real diff | identical |
| K2 | Line origin of port 1-2732 | upstream 2265, fork main 55, port 412 |
| K3 | Removed lines: upstream or fork main | all `35dbe67` except main 2316-2319 (`631721d`) |
| K4 | No-libcamera syntax check of CC | @up: fails, 28 error lines (first: `'SensorFamily' does not name a type`, CC:5913). @main: fails, 33. @cinemate-port: exit 0 |
| K5 | Table sizes, counted by script | IMX585: 62, 62, 29, 34 rows (40, 40, 29, 34 at width 1280 or more; 33 distinct 16-bit sizes). IMX283: 57 rows (42 + 15). Of upstream's 20 IMX585 sizes only 3840x2076 and 1920x1038 are missing from the SDR tables |
| K6 | Driver sizes | `origin/apertar`: 2076 and 1038 only. `cinemate-port`: 2072 and 1036 only |
| K7 | Board words in port 1-2732 | one hit, the comment at :1335 |
| K8 | Host tests of the included modules (existing logs, not re-run) | `imx585_modes_test: ok`; `imx283_modes_test`, `clip_name_test`: "all passed"; `log_curve_test`: "all checks passed" |

Commands (run in `/home/user/Apertar-Core` unless a path is given):

```
K1  git diff --minimal -U10 origin/main cinemate-port -- src/camera/CameraController.cpp | head -1159 | diff -q - /home/user/build/review/diffs/CC.part01.diff
K2  git blame -s -L 1,2732 cinemate-port -- src/camera/CameraController.cpp
    (each sha classified against: git log --format=%h origin/main..cinemate-port ; git log --format=%h upstream-1.6.0..origin/main)
K3  git blame -s -L <range> origin/main -- src/camera/CameraController.cpp      (ranges: column "Main lines removed" of section 1)
K4  g++ -std=c++20 -fsyntax-only -DAPERTARCORE_HAS_LIBCAMERA=0 -DAPERTARCORE_HAS_TURBOJPEG=0 -DAPERTARCORE_HAS_JPEG=0 \
        -DAPERTARCORE_HAS_LIBAV=0 -I src -I include src/camera/CameraController.cpp
    (run in /home/user/wt/core-upstream, /home/user/wt/core-main and /home/user/Apertar-Core; writes nothing)
K5  rows of kS12Modes, kS10Modes, kH12Modes, kH16Modes in src/camera/Imx585Modes.hpp and of kModes in src/camera/Imx283Modes.hpp
K6  git -C /home/user/imx585-v4l2-driver grep -n -E "2076|1038|2072|1036" origin/apertar -- '*.c'     (and the same on cinemate-port)
K7  awk 'NR<=2732' src/camera/CameraController.cpp | grep -n -i -E "hardware_concurrency|affinity|sched_|nice|cpu|i2c|fan|pcie|nvme|rp1|bcm27|meminfo"
K8  tail -2 /home/user/build/host-tests-Apertar-Core/<name>.run.log
```
