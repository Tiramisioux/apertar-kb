# Inventory CC-5: CameraController.cpp new-file lines 9732-11567 (diff CC.part05.diff)

Refs: port = `cinemate-port` (01f170c), upstream = `upstream-1.6.0` (`/home/user/wt/core-upstream`). Line numbers are @cinemate-port unless marked. Inventory only, no judgement.
Blame of the 1836 lines: 925 are unchanged upstream lines; the rest are port lines. Commits by size: faa2958 (274), 0041ba0 (229), ca7b7c2 (113), d44b177 (83), e16033e (57), caa0153 (39), 3cae990 (28), 646a194 (18), 8175273 (10), a47dc28, 80ddac1, 5f5cea2, 09256a7, 92b4be3, 3a18db0, 117065d, e625c68, 900d282, 64bbbaa, d7ff071, ce0bd90, b858d04, ab972fe, 014a2bf, e5757d7, a7b6f82, 4f7975f, 4ab1057, 26da30e (1-6 lines each).

Note on the hint: probe, sensor-mode choice and pre-roll appear in this slice only as members and helper calls (pre-roll members 10327-10348; probe via `sensorModes()` in the ladder editor). The bulk is speed ramp (faa2958, ca7b7c2) and the Mode Ladder (0041ba0 and follow-ups). The pre-roll logic itself (`setPrerollFps`, `prerollMeasure`) is at 7839/7875 and 12046-12180, outside this slice.

## 1. Features in this unit

| Feature | Port commits | Lines @port | Operator gets | Fork-log status / tests |
| --- | --- | --- | --- | --- |
| Speed ramping (FPS change during a cDNG/MLV take) | faa2958, 92b4be3, 4f7975f | 9742-9911 (grace, event queue, pairing, log), 10405-10435 (members), 10577-10583 (stop), 10686-10757 (`setFps`/`applyFpsStepLocked`), 10758-10820 (`restoreFpsAfterRampLocked`) | Change FPS while recording raw; shutter keeps angle or exposure; the take ends at its start rate (or stays); `fps-ramp.txt` in the clip folder | fork-log:58 tested 2026-10-28 (C0030-C0032); 92b4be3 tested (hardware-log); 4f7975f built clean |
| FPS ramp "keep exposure" policy and nominal shutter | faa2958 | 10735-10757, 11201, 11211 | `shutter=exposure` keeps exposure time, clamped to the frame, returns to the asked value on ramp down | same as above |
| Experimental stretched WAV after a ramp take | ca7b7c2, b858d04 | 9912-10001 (`launchAudioStretch`), 10416-10424, 10428 | `<clip>_stretched.wav` conformed to the timeline, pitch kept, written in the background after the take | fork-log:69 "Experimental"; tested 2026-10-28 (hardware-log); b858d04 built, needs restart |
| Capture-gap estimator sits out ramp frames | faa2958 | 10013-10020 | No false "dropped frame" warnings during a ramp | tested with faa2958 |
| Dropped-frame count (not only flag) | 64bbbaa | `markDropped(droppedEstimate)` ~10066; ctor lambda ~10494-10496 | `recording_dropped_frames` in the `recording_health` event | fork-log:139 on `drop-frames`, Pi |
| Mode Ladder (FPS picks the sensor mode between takes) | 0041ba0, e16033e, 3cae990, ab972fe, a7b6f82, 09256a7, caa0153, a47dc28 | 10509-10514 (load in ctor), 10640-10666 (`setResolution`), 10823-11062 (ladder functions), 11063-11134 (`setModeLadder`, `applyLadderToPreset`), 11213-11219, 11322-11327, 11370-11403, 11441-11451 | Settings > Record > Mode Ladder: ordered resolutions with bit depth, Clear HDR, compression and FPS ceiling; the camera moves to the rung for the FPS; rung ceiling in a take; presets must match the rung | fork-log:87 tested 2026-10-28 (socket, two takes, presets); 92 built; 96 built not tested; 95 built; a7b6f82 "fork-only" |
| Ladder blocks manual resolution, bit depth, Clear HDR, cDNG compression, lossy ratio, cDNG<->lossy format | 09256a7, 3cae990 | 10643-10646, 11370-11373, 11299-11302(clear HDR override), 11322-11327, 11400-11403, 11448-11451 | Those commands return an error text that tells the operator to turn the ladder off | fork-log:95, 92 built |
| Clear HDR override of the ladder (`ladderOverride_`) | 09256a7 (follow-up in d44b177 "Clear HDR over the Mode Ladder", fork-log:138) | 10667, 11416-11436, 11446 (approximate; see table 3) | Choosing Clear HDR by hand holds the mode until fps, resolution, format, bit depth, Ramp-ready or the ladder change | fork-log:138 "not yet run on the camera" |
| Clear HDR holds ISO and WB; auto refused in Clear HDR | 8175273, e5757d7 | 11075 (`isoAutoAfterClearHdr`), 11167-11170, 11185, 11196-11199, 11409-11424 | Auto ISO/WB switch off at the values in use when Clear HDR starts; they come back in SDR | fork-log:61 tested in preview; 64 tested |
| `set_iso_auto enabled=false` lock at measured gain | 646a194, e5757d7 | 11079-11108 | Turning Auto ISO off keeps the gain the camera is using (`iso_actual`) | fork-log:62 tested 2026-10-28 |
| Log (CineMate Log) switch | d44b177 | 11306-11332 (`setCdngLog`), carry-over 11245-11266 | Log on/off for cDNG and lossy DNG; refused in H.264, ProRes, MLV | fork-log:138, Pi not yet run |
| Settings that carry across recording formats | 92b4be3, 117065d, d44b177, ce0bd90, e625c68, d7ff071, 014a2bf | 11241-11266 (`setRecordingFormat` profile swap) | Speed ramp (switch, policy, stretch, after-take), phase lock, preview TDN, drive trim, Log, conform fps, clip-name template stay on when the format changes | tested for ramp/phase lock/conform (hardware-log); others Pi only |
| Frame-rate phase lock members | 80ddac1, 3a18db0 | 10351-10359 | (members only; logic outside this slice) | fork-log:37, 39 built, no test recorded |
| Storage pre-roll members and frame sampler | d44b177 (squash; "storage pre-roll" 2026-11-01) | 10327-10360 | (members only; operator feature is Storage pre-roll elsewhere) | fork-log:138 not yet run on camera |
| Sensor binning member | 4ab1057 | 10399 | `sensor_binning*` in state | fork-log:36 verified |
| Build without libcamera (`#else` stub members) | 5f5cea2 | 10441-10447 | `--simulate` build works | built with libcamera ON and OFF |
| IMX585 crop size migration (3840x2076 -> 3840x2072, 1920x1038 -> 1920x1036) | 900d282 | 10514, 10569 (`migratedImx585CropResolution`) | Old clients and saved ladders keep working | fork-log:138; driver change |
| IMX585/IMX283 sensor-table checks in `setResolution`, ladder pool | caa0153, a47dc28 | 10574-10588, 10960-10968, 11009-11019 | Resolution must be a mode of the current bit depth / Clear HDR class; error text names it | fork-log:138 not yet run on the camera |
| Monochrome flag to the sanitiser | caa0153 | `session_->monochromeSensor()` at 10586, 10592, 10643, 10730, 10773, 11393, 11439 | Mono sensors get their own limits | same |
| Media root published to a global | 26da30e | 10543 `configuredMediaRoot() = mediaRoot;` | (internal; used by media profile) | fork-log:46 built, not tested |
| Shutdown closes a ramp take | faa2958 | 10577-10583 | `fps-ramp.txt` written and start rate persisted when Core stops mid-take | tested with faa2958 |

## 2. Commands, routes, state fields, events, config, env, files, UI

Socket commands and routes are handled elsewhere (`ApertarCoreApp.cpp`); this slice holds the Camera side. Listed with what the slice implements.

| Kind | Name | Where in slice | Added/changed | Notes |
| --- | --- | --- | --- | --- |
| Socket command | `set_fps_speed_ramp enabled= [shutter=angle|exposure]` (+ stretch audio, after-take) | error text at 10695 | added | App handler @port ApertarCoreApp.cpp:13223; `fps_speed_ramp_keep_exposure`, `_stretch_audio`, `_after` in state (App:370-372, 9532-9534) |
| Socket command | `set_fps` | 10680-10757 | changed: allowed while recording when ramp on and raw | upstream refused any FPS change while recording (@upstream CC:7745) |
| Socket command | `get_mode_ladder`, `set_mode_ladder` (rungs=, enabled=, ramp_ready=, dry_run=) | 11034-11062 | added | App:14090-14107 |
| Socket command | `set_iso_auto enabled=false` | 11079-11108 | changed: new `enabled` parameter, `setIsoAuto(bool)` | upstream `setIsoAuto()` no args (@upstream CC:7788) |
| Socket command | `set_cdng_log` | 11306-11332 | added | App:13079 |
| Socket command | `set_clear_hdr`, `set_wb_auto`, `set_wb`, `set_iso`, `set_shutter_us`, `set_shutter_auto`, `set_resolution`, `set_raw_bit_depth`, `set_record_format`, `set_cdng_compression`, `set_lossy_dng_ratio`, `set_photo_mode_enabled` (still exposure mode) | see regions in table 3 | changed (new refusals, side effects) | |
| Event | `recording_health` gets `recording_dropped_frames` | 10494-10496 | changed | |
| State fields (CaptureSettings, set in `fillLadderFieldsLocked`) | `fps_take_max`, `ladder_active`, `ladder_rung`, `ladder_ramp_ready`, `ladder_enabled`, `ladder_override`, `ladder_count`, `ladder_tops`, `ladder_text`; `fps_max` rewritten by the ladder | 10890-10936 | added | derived, never persisted |
| State fields | `iso_auto_after_clear_hdr`, `wb_auto_after_clear_hdr` | 11075, 11185 | added | |
| State fields | `fps_speed_ramp`, `_keep_exposure`, `_stretch_audio`, `_return`, `conform_fps`, `clip_name_template`, `fps_phase_lock`, `preview_tdn`, `media_trim_enabled`, `cdng_log` carried across formats | 11241-11266 | added | |
| Config file | `~/.config/apertar-core/mode_ladder.conf` (XDG_CONFIG_HOME aware, temp-dir fallback) | `modeLadderPath()` 404-415, read 10509-10514, written 10938-10944 via `settingsFile::atomicWrite` | added | beside `camera_settings.conf` |
| Env vars | `APERTAR_FPS_RAMP_GRACE_FRAMES` (1-200, overrides grace) | 9753-9762 | added | |
| Files on disk | `<clip folder>/fps-ramp.txt` | 9857-9910 | added | columns: requested_frame applied_frame frame_us seen tc_at_base boot_us from_fps to_fps shutter_us applied_us |
| Files on disk | `<clip>_stretched.wav`, `<clip>_stretched.partial.wav`, `/tmp/apertar-stretch-<clip>.map` (temp dir) | 9939-10001 | added | |
| External programs | `rubberband` (package rubberband-cli), `nice`, `/bin/sh` | 9965-9980 | added | double fork, setsid, detached |
| Journal lines | `ApertarCore fps ramp:`, `fps ramp stats:`, `mode ladder:`, `audio stretch (experimental)`, `drop[capture-gap]` | various | added | `lag_frames=` is the number to size the grace on the Pi |
| UI elements | none in this file | | | UI text is the error strings (`kLadderOwnsMode`, `kLadderOwnsCompression` at 3061-3068) and `ladder_text` |

## 3. Original (upstream) regions modified

| Region (@port lines) | Upstream function | What changed | Kind |
| --- | --- | --- | --- |
| 10005-10020 `trackRecordingCadence` | same @upstream | Early return inside ramp grace; keeps timestamp chain | extended in place |
| ~10066 same function | same | `markDropped()` -> `markDropped(droppedEstimate)` (count, not flag) | behaviour-changed (signature in `RecordingDropWarning`) |
| 10317-10360 CameraSession members | same class | Preroll atomics, `noteFrameForPreroll`, phase-lock state, 16-deep pin history, `sensorBinning_`, ramp state (`FpsRampEvent`, `PendingAudioStretch`, `rampMutex_`) | extended in place (members) |
| 10441-10447 `#else` branch | none upstream | libcamera-off stub members | extended in place |
| 10482-10514 ctor | `CameraController::CameraController` | recording-health lambda reports count; loads ladder file after settings | extended in place |
| 10541-10543 `start()` | same | `configuredMediaRoot() = mediaRoot;` | extended in place |
| 10577-10583 `stop()` | same | Closes a ramp take: stopRecording, `restoreFpsAfterRampLocked()` | extended in place |
| 10633-10666 `setResolution` | same | ladder refusal; alias migration; IMX585 table check; mono flag in sanitiser; `ladderOverride_` reset | extended in place |
| 10674-10757 `setFps` | same | Upstream: refuse any FPS change while recording. Port: ramp rules, ladder rung rewrite, ceiling clamp; body split into new `applyFpsStepLocked(effectiveFps, rampingTake, commit, rung)` | rewritten (and split) |
| 11062-11080 `setIso` | same | clears `isoAutoAfterClearHdr` | extended in place |
| 11079-11108 `setIsoAuto` | same | new `enabled` argument, lock-at-gain path, refused in Clear HDR | rewritten |
| 11201, 11211 `setShutterUs`, `setShutterAuto` | same | reset `rampNominalShutterUs_` | extended in place |
| 11213-11219 `setStillExposureMode` | same | leaving stills calls `ladderRewriteLocked` | extended in place |
| 11185 `setWhiteBalanceKelvin`, 11196-11199 `setWhiteBalanceAuto` | same | clears after-Clear-HDR flag; refuse auto in Clear HDR | extended in place |
| 11224-11290 `setRecordingFormat` | same | ladder refusal for cDNG<->lossy; carry-over of 11 settings across the format-profile swap; `ladderOverride_` reset; `ladderRewriteLocked` | extended in place |
| 11297-11304 `setCdngCompression`, 11345-11349 `setLossyDngRatio` | same | refused while ladder active | extended in place |
| 11363-11406 `setRawBitDepth` | same | ladder refusal; mono flag; override reset except 16-bit after Clear HDR | extended in place |
| 11409-11460 `setClearHdr` | same | compression fix, hold auto ISO/WB values, ladder override with rollback | extended in place |
| every `sanitizeSettingsForSensor(...)` call | free function | third argument `monochrome` added at all call sites in this slice | behaviour-changed (signature) |

## 4. New abstractions

| Name | Purpose | Files | Upstream equivalent |
| --- | --- | --- | --- |
| `apertar::ladder` namespace, header-only `ModeLadder.hpp` (344 lines; `Rung`, `Ladder`, `RungState`, `PoolEntry`, `parseFile`, `parseRungs`, `fileText`, `validate`, `chooseRung`, `ladderCeiling`, `rungCeiling`, `toJson`, `label`) | Pure logic of the FPS->mode ladder, host-testable | `src/camera/ModeLadder.hpp`; used from CC | none (upstream picks the mode from resolution/bit depth directly in `sanitizeSettingsForSensor`; `Rung`-like data does not exist) |
| `mode_ladder.conf` + `modeLadderPath()` | Persistence of the ladder | CC:404 | upstream persists only `camera_settings.conf` via `settingsFile` |
| `apertar::imx585` tables (`Imx585Modes.hpp`, 254 lines: `classFor`, `find`, `transportFor`, `activeFor`) | Mode table instead of whitelists | `src/camera/Imx585Modes.hpp` | whitelists in `sanitizeSettingsForSensor` (@upstream) |
| `imx283ActiveForTransport`, `Imx283Modes.hpp` | IMX283 modes | | none (no IMX283 upstream) |
| `FramePhaseLock` (`FramePhaseLock.hpp`) | Frame-rate servo | members only here | none |
| Speed-ramp engine: `FpsRampEvent`, `noteFpsChange`, `inFpsRampGrace`, `stampFpsRampEvents`, `pairFpsRampEvents`, `writeFpsRampLog`, `rampMutex_` | Log and grace for FPS changes in a take | CC:9742-9911 | none |
| Audio stretch: `PendingAudioStretch`, `launchAudioStretch`, `wavSampleRate`, `shellQuote` | Detached child process (double fork + `sh -c`) | CC:2896-2925, 9939-10001 | upstream uses `std::thread` workers; no `fork`/`system` of external tools in the recording path was found in this slice (unconfirmed for the whole file: `grep -n "fork()" ` @upstream would settle it) |
| Pre-roll sampler: `prerollFpsOverride_`, `prerollPinUs_`, `prerollMeasuring_`, `prerollFrames_`, `prerollFirstUs_/LastUs_`, `lastFramePeriodUs_`, `lastEchoedMinUs_`, `completedFrames_`, `noteFrameForPreroll` | Storage pre-roll measurement | CC:10327-10360 | none |
| `fillLadderFieldsLocked`, `ladderStatesLocked`, `ladderRewriteLocked`, `ladderActiveForLocked`, `fillRungExtrasLocked`, `modeLadderJsonLocked`, `modeLadderJson`, `setModeLadder`, `applyLadderToPreset` | CameraController methods for the ladder | CC:10823-11134 | none |
| `applyFpsStepLocked`, `restoreFpsAfterRampLocked` | CameraController methods for ramp | CC:10690-10820 | none (upstream `setFps` is inline) |
| `ladderOverride_`, `rampNominalShutterUs_`, `rampTakeBaseFps_`, `rampTakeChanged_` (header) | Controller state | CameraController.hpp:245-249 | none |
| `configuredMediaRoot()` | global accessor for the media root | CC (declared elsewhere) | none found in this slice |

## 5. Removed, narrowed or hidden versus upstream

| What | Where | Effect |
| --- | --- | --- |
| "Stop recording before changing FPS" is no longer unconditional | CC:10686-10698 | Allowed in raw takes when ramp is on; message changed; H.264/ProRes/photo keep the rule with a different message |
| Manual resolution, raw bit depth, Clear HDR (when ladder on: Clear HDR is allowed but marks override), cDNG compression, lossy ratio, cDNG<->lossy format | 10643, 11370, 11297, 11345, 11220 | Refused while ladder active (default on or off: `modeLadder_.enabled` from file; absent file = off) |
| Auto ISO / auto WB in Clear HDR | 11101-11104, 11196-11199 | Refused; sanitiser also turns them off (upstream allowed them: unconfirmed, grep `isoAuto` in `sanitizeSettingsForSensor` @upstream) |
| `setIsoAuto()` no-arg signature | 11079 | Replaced by `setIsoAuto(bool)`; callers changed |
| Old IMX585 resolutions (3840x2076, 1920x1038, 1332x990, 2028x1080, 4056x2160 ...) | 10569, imx585AliasResolution | Accepted as aliases or migrated; widths < 1280 hidden (fork-log:138) |
| Per-format-profile values of ramp, phase lock, TDN, trim, Log, conform fps, clip name | 11241-11266 | One camera-wide value; a saved profile no longer overrides them |
| Capture-gap drop detection during ramp grace | 10013 | Skipped: real drops inside the grace are not counted |

## 6. Board assumptions

| Assumption | Where | Detail |
| --- | --- | --- |
| Request queue depth by filesystem: 4 on ext4, 6 on exFAT/NTFS, 8-10 with Clear HDR | comment 9751-9756 | Grace = N+6 frames; sized for Pi 5 media profile (26da30e) |
| 16 raw buffers max (`APERTAR_RAW_CAMERA_BUFFERS`), pin history array of 16 | 10351-10359 | Hard cap in `std::array<int64_t,16>` |
| "Lossy cDNG recording requires Raspberry Pi 5-class hardware" | 11267-11270 (`recordingCapabilities().rawCompression`) | Pre-existing upstream check, unchanged |
| Pi 5 / pipeline handler behaviour: `DelayedControls` two-frame delay, IPA `limitExposureTime` | 9744-9760, 10735-10740 | libcamera rpi pipeline assumed (PISP; "PISP_COMP1" is in the configure path outside slice) |
| IMX585 and IMX283 only for the ladder pool / editor (others use the raw probe sizes) | 10960-11019 | Sensor families hard-coded |
| `rubberband-cli` installed, `/bin/sh`, `nice` | 9965 | Not in an install step in this slice |
| `/tmp` (temp_directory_path) for the stretch map | 9963 | |
| No RP1, PCIe, gpiochip, I2C bus, fan or RAM-size reference in this slice | | none found |
| 280 fps ceiling (`fps > 280.0`) | 10705 | Upstream value, unchanged |

## 7. Open points for later stages

| Point | Evidence |
| --- | --- |
| Internal tutorial numbers in source text (T31, T34, T23/T29, T28, "request 19", "decision 9", "Q2/Q10") | comments 9747, 9805, 10402, 10415, 10825, 10890; Patrik-internal per BRIEF |
| Dates and Cinemate commit ids in comments (`ff59dd8`, "measured 2026-10-28") | 10697, 9950 |
| Several ladder commits "built, not tested" or "not yet run on the camera" | fork-log:96, 138 |
| `rubberband` double-fork shell command string built by concatenation | 9965-9980 |
