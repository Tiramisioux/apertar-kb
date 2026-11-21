# Conventions study C2: CameraController and the recorders (original Apertar 1.6.0)

How the original developer builds the camera and recording side of Apertar-Core. Read from the original code only.
This page is the yardstick for the cinemate port and the rule book for later work on these files.

| Item | Value |
| --- | --- |
| Code read | `/home/user/wt/core-upstream` (tag `upstream-1.6.0`, `35dbe67`), `/home/user/wt/ui-upstream` (`43888e5`) for the mirror copies only |
| Scope | `src/camera/*`, `src/cdng`, `src/lossydng`, `src/mlv`, `src/prores`, `src/video`, `src/audio`, `src/color`, `include/apertar/core/Types.hpp`, `RecordingCapabilities.hpp` |
| Short names | `CC` = `src/camera/CameraController.cpp`, `CC.hpp` = `src/camera/CameraController.hpp`, `App` = `src/ApertarCoreApp.cpp`, `WCP` = `src/web/WebControlPage.cpp`, `Types` = `include/apertar/core/Types.hpp`, `Caps` = `include/apertar/core/RecordingCapabilities.hpp` |
| Refs | Every `path:line` below is `@upstream-1.6.0`. Lines came from `grep -n` / `Read` on that tree, 2026-11-17 |
| Status words | Every claim is **confirmed** (read in code) unless it says **probable** or **unconfirmed** |
| History | Upstream Core has one commit (`35dbe67 1.6.0 Release`). There is no history that shows how a feature was added. The rules come from the static shape of the code, from comments and from `README.md` |
| Strength | **always** = no counter-example, search named. **usually** = exceptions named. **once** = one precedent |

Not read whole: `CC` (8834 lines) was read in chunks by anchor. Not read: `CC:891-1016` (photo and timelapse paths),
`CC:1168-1692` (byte writers, RAW unpack, still render), `CC:6684-6852` (private structs, mmap), `CC:6958-7180`
(still capture from a request), `CC:7228-7374` (preview publish), the bodies of `CdngEncoder.cpp`, `MlvEncoder.cpp`,
`LossyDngEncoder.cpp:260-517`, `ProresEncoder.cpp` outside the env code, `AudioRecordingSession.cpp`, `ColorProfileConfig.cpp`.
Rules about those parts rest on `grep` hits only and say so.

---

## 1. The shape in one table

| Layer | Where | What it owns |
| --- | --- | --- |
| Shared types | `Types:14-238` enums and structs, `Types:240-337` `toString` | `CaptureSettings` (`Types:124-162`), per-take option structs (`Types:184-201`), `RawFrameView` (`Types:203-218`) |
| Board capability | `Caps:11-106` (header-only) | What a Pi model may record. Read once from the device tree (`Caps:37-50`) |
| Public class | `CC.hpp:17-133`, bodies `CC:7577-8834` | One mutex, 25 `bool set...` methods, `lastError()`, events through one callback. No libcamera type in the header |
| Free helpers | `CC:93-5228`, one anonymous namespace | Parsers, sensor tables, clamp, persistence, env helpers, controls, three recorder classes |
| Session | `class CameraController::CameraSession`, `CC:5230-7575` | The only libcamera user: open, configure, requests, frame callback |
| RAW take | `class DngRecordingQueue`, `CC:3249-3928` | cDNG, lossy DNG and MLV: bounded queue + worker threads |
| Processed take | `class H264PreviewRecorder`, `CC:3930-5016`; `ProresRecorder`, `src/prores/ProresRecorder.{hpp,cpp}` | H.264 (libav plugin or ffmpeg pipe) and ProRes (libav plugin) |
| Stills | `class PhotoCaptureWriter`, `CC:5018-5224` | DNG/JPEG/PNG/TIFF worker |
| Encoders | `src/cdng`, `src/lossydng`, `src/mlv` (linked in), `src/prores`, `src/video` (plugins) | File formats. Plain classes, hand-written containers |
| Sidecars | `src/audio` (WAV), `src/hardware/Mpu6050RecordingSession` (gyro) | Started and stopped by the session with the take (`CC:5555-5587`, `CC:5672-5676`) |

`src/camera/` holds one `.cpp`. The Core executable is 25 `.cpp` files (`CMakeLists.txt:69-96`).

---

## 2. STRUCTURE rules (where things go, who owns what)

| Id | Rule | Strength | Evidence | Exceptions |
| --- | --- | --- | --- | --- |
| S1 | libcamera is used in exactly one translation unit, `CC`. No header includes a libcamera header | always. Search: `grep -rln '#include <libcamera' src include` gives `CC` only | `CC:69-79` (the includes, inside `#if APERTARCORE_HAS_LIBCAMERA`); `CC.hpp:3-13` (only `Types.hpp`, `RecordingDropWarning.hpp`, std headers); `CC.hpp:90` `class CameraSession;` forward declaration | none |
| S2 | No class hierarchy. No `virtual`, no `override`, no base class, no interface for sensors, recorders or encoders | always. Search: `grep -rnE '\bvirtual\b\|\boverride\b' src include` gives 2 hits, both the English word in a string/comment (`CC:3983`, `ProresEncoder.hpp:99`); the inheritance regex gives 0 | Recorders are concrete members of the session: `CC:7507-7511` `DngRecordingQueue recorder_; H264PreviewRecorder h264Recorder_; ProresRecorder proresRecorder_; ... AudioRecordingSession audioRecorder_;`. Dispatch is an `if` on the format: `CC:5589-5647`, `CC:5895-5897` | The only compile-time seam is `template<class System = NativeH264System> class NativeV4l2H264Encoder` (`src/video/NativeV4l2H264Encoder.hpp:35`) |
| S3 | New camera behaviour goes into `CC` itself: a free helper in the anonymous namespace plus a `CameraSession` member. It does not get its own `.cpp` | usually | `CC` holds the session, three recorder classes, PNG and TIFF encoders (`CC:1797-1880`), the settings persister (`CC:793-883`), timelapse (`CC:8302-8500`), standby (`CC:7668-7709`). `src/camera/` = 1 `.cpp` + 4 small headers | Code that needs another library or is a file format gets its own directory: `src/prores/ProresRecorder.cpp` (dlopen client), `src/cdng`, `src/mlv`, `src/lossydng`, `src/audio`, `src/color` |
| S4 | Pure logic that needs no libcamera type goes in a small header-only file named after the concept, `inline` free functions in `namespace apertar`, plain ints in and out | usually | `src/camera/StillBracketing.hpp:8-19` (20 lines), `ExposureMetering.hpp:8-39` (41), `ScalerCropGeometry.hpp:16-64` (66), `src/cdng/BlackLevel.hpp:12-32` (34), `src/audio/RecordingClock.hpp:13-61` (63), `src/video/H264Hardware.hpp:16-66` (68) | Most pure logic still lives in `CC` (sensor tables `CC:355-532`, fps tables `CC:2493-2683`) |
| S5 | A type lives in `include/apertar/core/` only when it crosses the App / CC boundary or the plugin boundary. Everything else stays in `src/<area>/` | always. 4 files in that folder | `Types.hpp` is included by 10 headers; `RecordingCapabilities.hpp` by `App` and `CC`; `ProresColorProfile.hpp` by the plugin (`ProresEncoder.hpp`, `CMakeLists.txt:158` adds `include` to the plugin); `PreviewExposureReference.hpp` by `App` and `ProresIspProfile.hpp` | none |
| S6 | `src/util/` holds only tiny stateful classes that two or more files share. String and byte helpers are not shared: each `.cpp` keeps its own copy in its anonymous namespace | always. 4 headers in `src/util/` | Shared: `RecordingFailure.hpp` (used by `CC:23`, `ProresRecorder.hpp:3`, `AudioRecordingSession.hpp:6`), `RecordingDropWarning.hpp` (`CC.hpp:4`, `ProresRecorder.hpp:4`). Copied: `writeAll` in `MlvEncoder.cpp:61`, `CdngEncoder.cpp:462`, `LossyDngEncoder.cpp:56`, `CC:4657`, `SettingsFile.hpp:25`; `escapeJson` in `CC:95` and `src/ipc/ControlProtocol.cpp:235`; `setError` in `CC:4302`, `CC:5919`, `ProresRecorder.cpp:15`, `LibavH264EncoderClient.cpp:144`; `lossyDngRatioFromString` in `CC:226` and `App:859` | `AtomicStillFile.hpp` has one user (`CC:11`) |
| S7 | The public surface of the camera is `bool` setters on `CameraController`, one per socket command, plus `lastError()`. `App` parses the command, calls one setter, replies `settingsBody(camera_.settings())` or `camera_.lastError()` | always for camera settings. 25 `bool set...` at `CC.hpp:39-63` | `CC.hpp:41` `bool setIso(uint32_t iso);`, `CC.hpp:85` `std::string lastError() const;`; `App:9242-9249` (`set_iso`), `App:9275-9282` (`set_fps`), `App:9378-9386` (`set_prores_profile`) | `applyCapturePreset` takes a whole `CaptureSettings` (`CC.hpp:64`, `CC:8604`) |
| S8 | One commit path. Every setter ends in `applySettingsLocked(next, requiresReconfigure)`. It applies, reads the effective settings back from the session, persists, clears the error, emits the `settings` event | usually. 27 call sites (`grep -n 'applySettingsLocked(' CC`) | `CC:8659-8723`; `CC:7785` `return applySettingsLocked(next, false);`; `CC:7738` `return applySettingsLocked(next, true);` | `setTuningFile` has its own reconfigure and recovery (`CC:8044-8112`) |
| S9 | Two ways to apply a change, chosen by the setter with a `bool`: `false` = controls for the next request, `true` = full reconfigure (stop + start, CameraManager included) | always | Controls: `CameraSession::applyControls` rebuilds the whole `ControlList` into `pendingControls_` (`CC:5495-5524`), merged into the next requeued request (`CC:6503-6509`). Reconfigure: `CC:5481-5493` `stop(); ... return start(settings, error);`. Forced for photo mode and ISP colour profile changes (`CC:8661-8662`) | none |
| S10 | One function turns settings into libcamera controls: `controlsForSettings`. Start, runtime changes and still capture all call it | always. 5 call sites | `CC:2005-2144`; callers `CC:5511` (runtime), `CC:6345` (start), `CC:6519`, `CC:6533`, `CC:6555` (stills) | Bracket shots add `AnalogueGain`, `AwbEnable`, `ColourGains` on the request after the merge (`CC:6522-6526`) |
| S11 | Sensors are told apart by `enum class SensorFamily` (private to `CC`), set once from a substring of the libcamera camera id. Sensor knowledge is `switch (sensorFamily)` in free functions of `CC` | always. 72 `SensorFamily::` uses, all in `CC` (`grep -rc 'SensorFamily::' src include`) | `CC:1882-1888` enum; `CC:2151-2167` `detectSensorFamily` (`lower.find("imx577")`, 477, 294, 585); `CC:5375` `sensorFamily_ = detectSensorFamily(camera_->id());`; switches at `CC:1892`, `CC:2215`, `CC:2374`, `CC:2430`, `CC:2633`, `CC:2689` | Mono is not a family. It is a flag detected from the CFA property or the RAW format (`CC:5306-5321`) |
| S12 | Sensor names, mode lists, fps caps and ISO lists are not shared between layers. Each layer keeps its own copy and finds the sensor by substring of the name string Core publishes | always | Core publishes `"sensor":"IMX585"` (`CC:2169-2179`, `App:9237`). Copies: `CC:355-532` + `CC:2493-2705`; `App:1076-1260` (`maximumPcfFpsForSettings`, `availablePcfResolutionOptions`), `App:4765-4836`; `WCP:4824-5028`, `WCP:5112-5510`; `Apertar-UI/qml/CameraPage.qml:377-490`, `:672-802`. See section 5.3 | none |
| S13 | Record formats are one flat enum in `Types`, compared inline. Sub-options are their own enum + their own `CaptureSettings` field + their own setter + their own command | always | `Types:45-51` `enum class RecordingFormat { Cdng, Mlv, H264, LossyDng, Prores }`; `Types:53-68` `CdngCompression`, `LossyDngRatio`, `ProresProfile`; `Types:144-153` the fields; `CC.hpp:50-58` the setters; `App:9326-9386` the commands. 54 `RecordingFormat::` uses in `CC` | Grouping predicates exist: `isProcessedVideoFormat` (`CC:221-224`), `isFixedTenBitRecordingFormat` (`CC:238-241`), `settingsProfileFormat` (`CC:605-608`) |
| S14 | What a board may record is decided in one header, from the device tree, and enforced in three places: the setter, the sanitise chain and record start | always | `Caps:18-35` (compatible string to capabilities), `Caps:64-77` `unsupportedRecordingSettings` (returns the sentence), `Caps:79-106` `supportedRecordingSettings`; used at `CC:7923`, `CC:8672`, `CC:8234`, `CC:2709`, `CC:7599-7601` | none |
| S15 | Three sanitise layers, always in this order: board (`supportedRecordingSettings`), absolute ranges (`clampCaptureSettings`), sensor (`sanitizeSettingsForSensor`) | always | `CC:2707-2744`: `settings = supportedRecordingSettings(settings); settings = clampCaptureSettings(settings);` then sensor cases; `CC:534-601`; `Caps:79-106` | none |
| S16 | Each recorder is a self-contained class with the same members: `start...(folder, settings, ..., std::string *error)`, `enqueue...()` returning `bool` (`false` = not taken), `stop()`, `active()`, `error()`. The destructor calls `stop()` | always. 4 frame recorders; the audio session has the same `start` / `stop` / `active` / `error` and `observeVideoFrame` instead of an enqueue | `CC:3268`, `CC:3572`, `CC:3390`, `CC:3494`, `CC:3516`, `CC:3263-3266` (DNG); `CC:3953`, `CC:4239`, `CC:4219`, `CC:4232`, `CC:4229` (H.264); `ProresRecorder.hpp:20-24`; `CC:5045`, `CC:5029`, `CC:5022` (photo); `AudioRecordingSession.hpp:27-36` | `PhotoCaptureWriter` starts its thread at the first enqueue (`CC:5055-5058`) |
| S17 | The clip folder is allocated once, for every format, by `DngRecordingQueue::reserveClipFolder`. The prefix per format is one `switch` | once (one call site) | `CC:5548` `clipFolder = DngRecordingQueue::reserveClipFolder(mediaRoot, settings);`; `CC:3646-3662` (`cDNG_`, `MLV_`, `H264_`, `cDNG_3to1_`/`cDNG_5to1_`, `ProRes_`); `CC:3664-3675` first free `_C0001`..`_C9999` | none |
| S18 | Anything that links libav is a plugin (`MODULE` library) loaded with `dlopen` at the first take that needs it, with an ABI number check. Core itself never links libav. ALSA is loaded the same way | always. 3 lazy loads | `CMakeLists.txt:143-169`; `ProresRecorder.cpp:25-50` (`apertar_prores_abi`, `kApertarProresAbi`), `LibavH264EncoderClient.cpp:97-131`; ALSA `TimestampedAudioCapture.cpp:41-49` and `TimestampedAudioCapture.hpp:17` `// ALSA is loaded only when recording audio` | none |
| S19 | Per-take inputs that are not camera settings travel as option structs built by `App`, not as `CaptureSettings` fields | always. 2 structs | `Types:184-197` `AudioRecordingOptions`, `Types:199-201` `GyroRecordingOptions`; built at `App:10624-10687`; passed at `App:10709` `camera_.startRecording(audioOptions, gyroOptions)`; `CC.hpp:77-78` | none |
| S20 | Camera settings persist in `~/.config/apertar-core/camera_settings.conf`, `key=value` lines, written only by Core. Per record format and for still mode there is a full copy under `profile.<name>.` | always | Path `CC:342-353`; load `CC:616-740`; write `CC:742-778`; prefixes `CC:634-648`, `CC:785-788`; debounced writer thread (25 ms) `CC:793-883`; atomic write `CC:789`; README `README.md:267` | none |
| S21 | A runtime capability (something the pipeline or tuning can or cannot do) is a non-persisted field of `CaptureSettings` with a trailing comment, filled before the settings leave Core | always. 5 fields | `Types:132` `exposureCompensationAvailable = false; // Runtime libcamera capability.`, `Types:134`, `Types:139`, `Types:142`, `Types:150`; filled at `CC:8570-8572`, `CC:8779-8781` | none |
| S22 | The camera side never reads `apertar-hardware.conf` | always. Search: `grep -rn 'apertar-hardware\|APERTAR_HARDWARE_CONFIG\|section ==' src/camera src/cdng src/lossydng/LossyDngEncoder.cpp src/mlv src/prores src/video src/audio src/color include` gives 0 hits | Files the camera side does read: `camera_settings.conf` (`CC:342`), tuning JSON (`DefaultTuningSelection.hpp:56-78`), `/home/pi/apertar-color-profiles.conf` (`ColorProfileConfig.cpp:232-237`) | none |
| S23 | External dependencies are few. A file format is written by hand in the repo rather than through a new library | usually | Required: Threads, libyaml, ALSA headers (`CMakeLists.txt:25-28`). Optional by flag: libcamera, libav, JPEG/TurboJPEG (`CMakeLists.txt:29-45`, `:120-173`). Hand-written: DNG/TIFF (`src/cdng/IfdBuilder.hpp`, `CdngEncoder.cpp`), lossless JPEG (`src/cdng/LosslessJpegEncoder.cpp`), MLV (`src/mlv/MlvEncoder.cpp`), PNG with own CRC/Adler/zlib-stored (`CC:1211-1264`, `CC:1797-1836`), TIFF (`CC:1838-1880`) | JPEG stills use TurboJPEG or libjpeg (`CC:1708-1795`); H.264 and ProRes use libav |
| S24 | Tests, a `third_party/` tree, a formatter config and contributor docs do not exist in upstream Core | always. `git ls-files` = 137 files: no `test`, `tools`, `third_party`, `.clang-format`, `.editorconfig`, `CONTRIBUTING`, `CHANGELOG`, `docs/` | `git -C /home/user/wt/core-upstream ls-files \| grep -i 'test\|third_party\|tools/\|clang\|editorconfig'` gives nothing; `.github/` holds only `FUNDING.yml` | Pure functions split from their I/O, and default parameters for system paths, exist without any test that uses them: `recordingCapabilitiesFromCompatible(std::string_view)` (`Caps:18`), `preselectDefault(..., videoDevices = "/sys/class/video4linux")` (`DefaultTuningSelection.hpp:185-187`), `findRaspberryPiH264Encoder(error, root = "/dev")` (`H264Hardware.hpp:38`). **Probable**: they were tested outside the repo (the shape fits nothing else) |

---

## 3. IDIOM rules (how the code is written)

| Id | Rule | Strength | Evidence | Exceptions |
| --- | --- | --- | --- | --- |
| I1 | A setter is: lock `mutex_`; gate on state with `setErrorLocked("sentence"); return false;`; check the absolute range the same way; if nothing changes `lastError_.clear(); emitSettingsEventLocked(); return true;`; else `CaptureSettings next = settings_; next.x = v; return applySettingsLocked(next, flag);` | usually. 24 of 25 setters | `CC:7774-7786` (`setIso`), `CC:7711-7739` (`setResolution`), `CC:7835-7849` (`setExposureCompensation`), `CC:8114-8148` (`setRawBitDepth`) | `setProresColorProfile` and `setCdngPreviewColorProfile` return `true` on no change without clearing the error or sending the event (`CC:8025`, `CC:8038`); `setTuningFile` (S8) |
| I2 | The setter rejects a value outside the absolute range with a message. Limits of the sensor, board or format are applied silently by the sanitise chain, and the reply carries the effective value | always | Reject: `CC:7777-7780` `"ISO must be between 50 and 51200."`, `CC:7748-7751`, `CC:7895-7898`. Silent: `CC:2740-2741` `if (settings.fps > maxFps) settings.fps = maxFps;`, `CC:7756-7759`, `CC:2483-2490` (lossless caps ISO and fps). Effective value read back: `CC:8713-8715` | none |
| I3 | Functions that can fail return `bool` and take `std::string *error` last (or next to last). A local `setError(error, "...")` helper writes it. The public class turns that into `lastError_` | always in `CC`, plugin clients and audio | `CC:5254` `bool start(const CaptureSettings &settings, std::string *error)`, `CC:3279`, `CC:3953-3958`, `LibavH264EncoderClient.hpp:19-21`, `ProresRecorder.hpp:20`; helper `CC:5919-5923` | none |
| I4 | Encoders and file writers throw `std::runtime_error` / `std::system_error`. The throw is caught at the worker loop or at the public boundary and becomes a latched failure or an error string. Nothing throws across the public class | always | Throws: `CdngEncoder.cpp` 30, `LosslessJpegEncoder.cpp` 16, `MlvEncoder.cpp` 20, `CC:3675`, `CC:2893`. Catches: `CC:3747-3752`, `CC:3838-3843`, `CC:5200-5206`, `CC:5550-5553`, `CC:8682-8687` | Plugins return `int` and fill `char *error, size_t size` (`ProresPluginApi.hpp:22-25`, `LibavH264PluginApi.hpp:29-35`) |
| I5 | Operator-facing errors are full English sentences with a capital and a period, in operator words, often saying what to do. No codes, no identifiers | always. 49 `setErrorLocked("...")` strings read | `CC:7715` `"Resolution changes are blocked while recording."`, `CC:7745` `"Stop recording before changing FPS so video and audio keep the same timeline."`, `CC:7811` `"Enable Long Exposure in Still Mode for shutter times longer than a frame."`, `Caps:70` `"ProRes recording requires Raspberry Pi 5-class hardware."` | none |
| I6 | Logging is `std::cerr <<` only. Every line starts `ApertarCore <area>: ` and continues with `key=value` pairs separated by spaces. No log levels, no logging helper, no `printf` | always in the topic files. Search: `grep -rnE 'std::cerr\s*<<\s*"[^ ]' <topic files>` shows only `"ApertarCore` starts; 131 such starts in Core | `CC:3353` `"ApertarCore recording clip: "`, `CC:6264` `"ApertarCore camera configured: sensor="`, `ProresRecorder.cpp:90`, `AudioRecordingSession.cpp:259`, `ColorProfileConfig.cpp:395` | One `std::fprintf(stderr, "ApertarCore H.264 native ...")` in the plugin (`LibavH264EncoderPlugin.cpp:245`). Outside the topic other prefixes exist (`"PCF8574 input: "`, `"Hardware input action ignored: "`, `"Apertar standby: "`) |
| I7 | What gets a line: take start (one line with every effective knob), take stop (one stats line), a drop (first and every 30th), a write failure, camera configured, tuning file chosen, a fallback taken, an ignored override. What never gets a line: a setter call, a control change, a normal frame | always | Start `CC:3353-3374`, `CC:4191-4215`; stop `CC:3416-3423`, `CC:4794-4805`, `ProresRecorder.cpp:155-156`, `CC:5667-5670`; drops `CC:3538`, `CC:4275`, `CC:7216`, `ProresRecorder.cpp:100`; configured `CC:6264-6293`; fallback `CC:4065-4067`, `CC:6422`. No `std::cerr` between `CC:7609` and `CC:8489` (all setters) | Photo queue drop logs every 10th (`CC:5062`) |
| I8 | Rate limit by counter: `if (n == 1 \|\| (n % 30) == 0)`. One-off warnings use a `bool warned..._` member | always | `CC:3538`, `CC:3582`, `CC:4265`, `CC:4275`, `CC:6571`, `ProresRecorder.cpp:100`; `CC:6858-6861` `warnedMissingWhiteBalance_`, `CC:6869-6870` `warnedUnsupportedRaw_` | none |
| I9 | Internal tuning is an environment variable named `APERTAR_<AREA>_<KNOB>`, read where it is used, with a built-in default and bounds. A missing, malformed or out-of-range value falls back without an error | always. 45 names, section 5.11 | Helpers `CC:1027-1039` `unsignedEnvValue(name, default, min, max)`, `CC:1041-1061` `boolEnvValue`; use `CC:3329-3330`; per-knob getters `CC:4329-4474`; read-once lambdas `CdngEncoder.cpp:51-65`, `LossyDngEncoder.cpp:97-110` | An unsupported `APERTAR_H264_SIZE` logs a line (`CC:2789-2792`). A wrong `APERTAR_H264_ENCODER` on Pi 3/4 fails the take start with a sentence (`CC:3981-3985`) |
| I10 | Names: members end in `_`; file-scope and local-table constants are `k` + PascalCase; functions and locals camelCase; types and enumerators PascalCase; methods that need the caller's lock end in `Locked`; units are a suffix (`Us`, `Ms`, `Seconds`, `Kelvin`); predicates start `is`/`has`/`uses`/`needs`; per-sensor functions end `ForSensor` / `ForResolution` | usually | `CC.hpp:107-132` (members), `CC:1019-1025` (`kPreviewWidth` ...), `CC.hpp:92-102` (`applySettingsLocked`, `setErrorLocked`, `emitSettingsEventLocked`), `Types:129` `shutterUs`, `Types:140` `whiteBalanceKelvin`, `CC:2685` `supportedRawBitDepthForSensor` | `constexpr uint32_t stillPreviewExposureLimitUs` without `k` (`CC:1995`); magic numbers repeated instead of named (280 fps at `CC:558` and `CC:7748`; 51200 at `CC:561` and `CC:7777`) |
| I11 | Wire names are snake_case: JSON keys, persisted keys, enum strings, command names. `toString(Enum)` lives at the bottom of the header that defines the enum. The reverse parser lives in the `.cpp` that needs it, lowercases the input by hand and maps an unknown string to the default | usually | `Types:254-264`, `Types:276-285`; `CC:199-219` `recordingFormatFromString` (unknown gives `Cdng`), `CC:290-340` (four parsers, each with its own lowercase loop); keys `CC:745-777` | `toWireValue(LossyDngRatio)` (`Types:271`); `parseProresColorProfile` sits in the header and returns `bool` (`ProresColorProfile.hpp:20-28`); `App` rejects unknown format strings (`App:824-844`) |
| I12 | JSON is built by hand with `std::ostringstream` or string `+`. An event is `{"event":"name",...}`. A structured value gets an inline `...Json()` helper next to its type | always | `CC:139-185`, `CC:7560-7562`, `CC:7582-7583`, `CC:8791-8795`; helpers `Caps:52-62` `recordingCapabilitiesJson`, `ExposureMetering.hpp:28-39`, `PreviewExposureReference.hpp:14-30` | `emitTimelapseEvent` escapes its path inline instead of calling `escapeJson` (`CC:8809-8818`) |
| I13 | The settings field list exists three times and is edited in all three by hand | always | `settingsEvent` `CC:136-187`; `settingsBody` `App:167-216`; `buildWebStateJson` `App:7835-7884` | none |
| I14 | Defaults are the member initialisers of `CaptureSettings`. Code that needs a default writes `CaptureSettings{}.field` | always | `Types:124-161`; `CC:555`, `CC:559`, `CC:562`, `CC:565`, `CC:577`, `CC:584`, `CC:287` | none |
| I15 | Loading saved settings is one `else if (key == "...")` chain inside `try { } catch (...) { }`. A malformed value keeps the default. A retired key is still read and mapped | always | `CC:650-723`, `CC:722` `// Ignore malformed values and keep defaults for resilience.`; legacy `wb_locked` `CC:681-682`, `CC:726-728` | none |
| I16 | Worker threads are `std::thread` members with one `std::mutex`, one `std::condition_variable`, a `std::deque<Job>` and a `bool stopping_`. Counters are `std::atomic<uint64_t>` with explicit memory orders, reset in `start`, printed in `stop` | always. 5 worker classes | `CC:3922-3927`, `CC:4990-4998`, `CC:5213-5218`, `ProresRecorder.hpp:41-45`, `CC:874-882`; counters `CC:3899-3914`, `CC:4979-4989` | The settings persister and the lossy disk writer are process-lifetime singletons (`CC:885-889`, `LossyDngEncoder.cpp:114-118`) |
| I17 | Process-wide one-off values are function-local statics | always | `CC:885-889` `captureSettingsPersister()`, `Caps:37-50` `recordingCapabilities()`, `CC:2990-2994` `cachedPiSerial()`, `DefaultTuningSelection.hpp:45-49` `nativePipeline()`, `CdngEncoder.cpp:51-65` | none |
| I18 | Build-time options are `#if APERTARCORE_HAS_X` with an `#else` branch that keeps the same signature, casts the arguments to `void` and returns a neutral value. Core must still compile and run with `--simulate` without libcamera | always | `CC:5393-5397`, `CC:5487-5492`, `CC:5519-5523`, `CC:5648-5655`; three bodies for one name `CC:1708-1795` (`encodeProcessedJpeg`: TurboJPEG, libjpeg, stub returning `false`); `simulateCamera_` appears 41 times in `CC` | none |
| I19 | Comments are rare and say why: one to three lines stating a constraint ("must not", "never", "keep"). No Doxygen, no `TODO`/`FIXME`, no ticket numbers, no author or date, no block comments | always in the code upstream wrote itself. `CC`: 78 comment lines in 8834; 0 Doxygen; 0 TODO; 0 `/*` | `CC:6927-6928`, `CC:8248-8250`, `CC:6033-6034`, `CC:5663-5664` | Code brought in from the QRAW project keeps long `/* */` essays with benchmark numbers and one date (`ProresEncoder.hpp:3-42`, `ProresEncoder.cpp:771-786`, `LossyDngEncoder.cpp:322-324`) |
| I20 | Formatting: 4 spaces, no tabs; function braces on their own line; `class X {` and control statements keep the brace on the line; a single-statement `if` puts the statement on the next line without braces; `static_cast<>`; `std::lock_guard<std::mutex> lock(mutex_);`. Lines run long (309 lines over 100 columns, longest 186). No formatter config | usually (the majority style) | Counts in `CC`: `std::lock_guard<std::mutex>` 83 vs CTAD `std::lock_guard lock(` 21; multi-line `if` 343 vs one-line `if (...) stmt;` 79; `static_cast<` 226 vs functional casts 19 | A denser second style exists in the newer parts (stills, standby, ProRes, drop warning): `ProresRecorder.cpp:15`, `CC:8008`, `RecordingFailure.hpp:10-20`, `CC:5635`. Digit separators only there (`CC:564`, `CC:7799`) |
| I21 | Include order: own header first, then project headers by path from `src` (`"cdng/CdngEncoder.hpp"`) or `<apertar/core/...>`, then std, then system headers | usually | `CC:1-24`, `CC:26-56`, `CC:57-90`; `MlvEncoder.cpp:1-18` | `ProresRecorder.cpp:1-11` and `src/prores/*` include siblings without a directory |
| I22 | Namespaces: everything is in `namespace apertar`; file-local helpers in an anonymous namespace inside it; a helper group in a header may use one nested namespace | usually | 75 `namespace apertar`; nested: `apertar::tuning` (`DefaultTuningSelection.hpp:14`), `apertar::settingsFile` (`SettingsFile.hpp:17`), `apertar::tiff`, `apertar::hardware` | The ProRes plugin uses `prores_color` and `prores_repair` |
| I23 | A plugin exports five C functions named `apertar_<plugin>_{abi,create,encode,finish,destroy}`; the config is a POD struct in a `...PluginApi.hpp` shared by both sides; the client class resolves the path as: env override, next to the executable, `/home/pi/ApertarCore-build/` | always. 2 plugins | `ProresPlugin.cpp:13-56`, `ProresPluginApi.hpp:5-25`, `ProresRecorder.cpp:27-32`; `LibavH264EncoderPlugin.cpp:464-522`, `LibavH264PluginApi.hpp:6-35`, `LibavH264EncoderClient.cpp:17-31` | none |

---

## 4. INTENT rules (product decisions the code encodes)

| Id | Rule | Strength | Evidence | Exceptions |
| --- | --- | --- | --- | --- |
| N1 | Core is the source of truth for camera state. Every client goes through the same setter and the same busy checks, and gets the effective value back | always | `README.md:271` "ApertarCore is the source of truth for camera and capture state. Native UI commands, WebUI requests and hardware actions reach the same controller and busy-state checks."; `CC:8713-8715` settings read back from the session; `App:9246-9248` reply with `settingsBody(camera_.settings())` | none |
| N2 | The camera callback thread must never wait for storage or an encoder. Queues are bounded. When a queue is full the frame is dropped before it is copied | always | `CC:6927-6930` "The completion callback is the only producer. If workers are already behind, reject before copying a full RAW frame that cannot be queued."; bounds `CC:3328-3330` (12 or 24 frames), `CC:4465-4474` (6), `ProresRecorder.cpp:64-65` (1 to 4), `CC:5220` (12); `README.md:299` "bounded queues help keep camera requests moving"; `CC:3700-3701`, `CC:6592-6596` (callback thread nice -5, workers nice 5) | none |
| N3 | A dropped frame is reported, not hidden, and does not stop the take. The operator gets one warning per clip, not a counter | always | `README.md:299` "Recording errors and detected dropped frames are reported rather than hidden."; `RecordingDropWarning.hpp:9` "A clip-scoped latch: notify once, not once per frame or per dropped frame."; event `CC:7580-7584`; state `App:9227`; touch UI badge `Apertar-UI/qml/CameraPage.qml:2569-2575`. Counts go to the journal only (`CC:3416-3423`) | The WebUI shows nothing for it (`grep -n -i 'dropped' WCP` gives 0 hits) |
| N4 | A write or encode failure stops the take by itself within about one second and shows the first error. A failure to start a take leaves the camera ready for another try | always | Latch `RecordingFailure.hpp:7-16` (first message wins); supervisor `CC:8519-8534`, polled at `App:7031-7034` (1 s loop) and `App:9094` (every command); `CC:8248-8253` "Keep the controller ready so the user can retry without restarting the whole app." | Lossy DNG disk-write errors are only logged (`LossyDngEncoder.cpp:228-232`) |
| N5 | During a take only exposure, white balance and focus may change. Anything that changes the stream, the file, the frame rate or the colour pipeline is refused with a sentence | always | Gated on `recording_`: `CC:7714` resolution, `CC:7744` fps, `CC:7927` format, `CC:7976` compression, `CC:7992`, `CC:8008`, `CC:8021`, `CC:8034`, `CC:8051` tuning, `CC:8117` bit depth, `CC:8153`, `CC:8607` preset, `CC:8284` photo. Not gated: `setIso` `CC:7774`, `setShutterUs` `CC:7796`, `setExposureCompensation` `CC:7835`, `setWhiteBalanceKelvin` `CC:7888`, `setAutofocusMode` `CC:8184`. Reason given at `CC:7745` | `setTimecodeMode` is not gated (`CC:8176-8182`) |
| N6 | Metadata is measured, never guessed. A RAW frame without measured white balance is not written | always | `CC:6857-6863` "RAW frame missing measured white balance; not writing guessed metadata."; `CC:3182-3202` gain, exposure, colour temperature and gains taken from the request metadata; `README.md:147` "Manual white balance uses the selected tuning's calibration rather than hardcoded sensor gain tables." | Fallback black level per sensor family when neither the frame nor the tuning has one (`CC:2933-2940`, `CC:3161-3176`) |
| N7 | Capabilities are detected at run time, not configured: the board from the device tree, controls from the libcamera control map, white balance and metering from the tuning file, mono from the sensor | always | `Caps:37-50`; `CC:1925-1945`, `CC:5812-5835`; `ColorProfileConfig.hpp:38-39`; `CC:5306-5321`; `README.md:20` "Available settings depend on your board, sensor, camera driver and tuning file." | Sensor modes and fps caps are hard-coded tables (S11), with libcamera's `validate()` as the last word (`CC:6135-6143`) |
| N8 | No silent downgrade of what gets recorded. If the board or pipeline cannot do it, the operator gets a sentence that names the hardware | usually | `Caps:64-77`; `H264Hardware.hpp:62-64` "... CPU encoding was not enabled."; `CC:4061-4063`; `CC:5535-5537` "Monochrome MLV is not supported. Select cDNG or H.264 instead."; `CC:6145-6151` ProRes needs native RGB48 at the selected size | Saved settings that the board cannot do are switched at start with one log line (`CC:7599-7601`). On Pi 5 a missing libav plugin falls back to the `ffmpeg` pipe with one log line (`CC:4064-4068`). Gyro start failure only logs (`CC:5563-5567`) |
| N9 | A failed mode change puts the previous working mode back. Only if that also fails does the camera go to `Error` | always. 3 places | `CC:8692-8709` "Reconfiguration stops capture first. Keep the last working mode usable when the replacement cannot allocate or configure."; `CC:8087-8105` (tuning file); `CC:8642-8656` (preset); `CC:7698` "Keep the wake action available after a failure, rather than showing a dead UI." | none |
| N10 | Media is never overwritten. Stills are made durable (fsync + atomic rename) before they are announced. Clip frames are not synced, for throughput | always | `CC:3667-3673` first free clip number; `AtomicStillFile.hpp:85-88` `RENAME_NOREPLACE` and "Do not replace a previous photo"; `AtomicStillFile.hpp:31-32` "Stills are published only after their data is durable. Keep this out of the continuous recording path: syncing each video frame would destroy throughput."; H.264 writes `.mp4.writing` then renames (`CC:4005-4006`, `CC:4754-4770`) | none |
| N11 | Internal tuning stays out of the files the operator edits. Knobs are undocumented environment variables for bench work | always | 45 env names in the topic (section 5.11); `grep 'APERTAR_' README.md` gives 0 hits; `camera_settings.conf` holds 33 operator settings and no tuning key (`CC:745-777`); `LossyDngEncoder.cpp:322-324` "Knob, not a hardcode: ... an A/B has to stay reachable without a rebuild." | ProRes also reads `/home/pi/.apertar-tuning`, "absent in production" (`ProresEncoder.cpp:771-786`) |
| N12 | The same source must build and run against different libcamera forks, without libcamera, and without libav | always | `CC:3084-3086` "Match by runtime name so ApertarCore builds against both variants."; `CC:2952-2954` frame duration in us or ns; `CC:1947`, `CC:5308` `#if defined(LIBCAMERA_HAS_...)`; only mainline `libcamera::controls::*` names are used (43 distinct, none under `rpi::` or `draft::`); `CMakeLists.txt:133-138`, `:170-173`; `README.md:223` | One direct V4L2 write to the sensor subdevice: reset HBLANK/VBLANK/EXPOSURE after a long exposure, only after streaming stops (`CC:5926-5966`) |
| N13 | What is seen on the monitor is not baked into RAW. The preview colour profile changes monitoring only | always | `README.md:58`, `README.md:155`; `Types:169-176` `activeIspColorProfile`; `CC:1113` "RAW calibration must always read the original sensor tuning, not an ISP log derivative."; `CC:3213-3224` preview gamut removed from the matrix that goes into the DNG; `ProresIspProfile.hpp:7` "Writes an internal derived tuning, never the user's selected source file." | none |
| N14 | Each record format and still mode remembers its own settings. Switching format brings that format's last settings back. Tuning file, timecode mode and metering mode stay global | always | `CC:7939-7955`; `CC:8725-8732`; `CC:8734-8749` (photo/video switch restores resolution, bit depth, fps only); `README.md:18` | Lossy DNG shares the cDNG profile (`CC:605-608`) |
| N15 | Pending stills are protected like a take: no mode change, no standby, no new capture until the writer is idle. The UI shows WRITING | always | `CC:8666-8671`, `CC:7677-7682` "never discard a pending photo", `CC:8243-8246`, `CC:8269-8272`; `App:9095-9097`; `README.md:102` | none |
| N16 | The established RAW capture model is fixed: one YUV monitoring stream plus one RAW stream. Processed formats (H.264, ProRes) are the only ones that change the stream set | once (one configure function) | `CC:6031-6037` "Keep the established Apertar RAW capture model unchanged: one main YUV monitoring stream plus one raw stream."; `CC:6017-6030` | none |

---

## 5. Inventories

### 5.1 Public surface: every setter, its gate and its apply path

`R` = reconfigure flag passed to `applySettingsLocked`. "Blocked" = refused while `recording_`.

| Setter (`CC` line) | Range or capability check | Blocked while recording | R |
| --- | --- | --- | --- |
| `setResolution` 7711 | `validateResolution` table (`CC:8751-8769`) | yes | true |
| `setFps` 7741 | 0 < fps <= 280; then lowered to the mode maximum | yes, if the value changes | false. Keeps the shutter angle (`CC:7768-7769`) |
| `setIso` 7774 | 50..51200 | no | false |
| `setIsoAuto` 7788 | none | no | false |
| `setShutterUs` 7796 | > 0, <= 30 s, <= timelapse interval, <= one frame unless Long Exposure, <= sensor maximum | no | false |
| `setShutterAuto` 7827 | none | no | false |
| `setExposureCompensation` 7835 | -3..+3 EV, pipeline has `ExposureValue` | no | false |
| `setExposureMetering` 7851 | mode in the tuning/pipeline mask | no | false |
| `setStillExposureMode` 7864 | none | yes (also timelapse) | true when photo mode toggles |
| `setWhiteBalanceKelvin` 7888 | tuning has calibrated AWB; 1500..12000 K | no | false |
| `setWhiteBalanceAuto` 7906 | tuning has calibrated AWB | no | false |
| `setRecordingFormat` 7918 | board (`unsupportedRecordingSettings`) | yes | true when a processed stream is involved or size / bit depth change (`CC:7965-7969`) |
| `setCdngCompression` 7973 | board, inside `applySettingsLocked` (`CC:8672`) | yes | false |
| `setLossyDngRatio` 7985 | Pi 5-class | yes | false |
| `setProresProfile` 8001 | Pi 5-class | yes | false |
| `setProresColorProfile` 8014 | Pi 5-class | yes (also timelapse) | true when ProRes is the active format |
| `setCdngPreviewColorProfile` 8031 | none | yes (also timelapse) | true when the active ISP profile changes |
| `setTuningFile` 8044 | exists, regular file, `.json`, readable, right pipeline target (`CC:1080-1109`) | yes (also standby, timelapse, pending stills) | always, own path |
| `setRawBitDepth` 8114 | normalised to 8/10/12, then per sensor | yes | true |
| `setH264Resolution` 8150 | size table (`CC:263-268`) | yes | true when a processed format is active |
| `setTimecodeMode` 8176 | none | no | false |
| `setAutofocusMode/Range/Speed/Window` 8184-8217 | none (window clamped in `clampCaptureSettings`) | no | false |

State of the class: `state_` (`CameraState`, `Types:14-22`), `recording_`, `settings_`, `formatSettings_`, `stillSettings_`, `lastError_`,
`recordingFailureReported_`, `recordingFailureMessage_` (`CC.hpp:113-123`). Events leave through `eventCallback_` while `mutex_` is held
(`CC:8777-8784`).

### 5.2 Sanitising, in order

| Step | Function | What it does | Ref |
| --- | --- | --- | --- |
| 1 | `supportedRecordingSettings` | Board: USB 2-only boards get H.264; no ProRes / lossy / compression without Pi 5; hardware H.264 gets <= 1920x1080 and <= 30 fps | `Caps:79-106` |
| 2 | `clampCaptureSettings` | Absolute ranges. Out of range resets to the `CaptureSettings{}` default (resolution, fps, ISO, shutter, WB, format); EV, bracket EV and AF window are clamped; shutter is limited to one frame unless Long Exposure | `CC:534-601` |
| 3 | `sanitizeSettingsForSensor` | Calls 1 and 2, then: processed formats force 10-bit and their capture size; resolution mapped onto the sensor's set; bit depth per sensor; fps capped per mode; lossless caps | `CC:2707-2744` |
| 4 | at configure | `whiteBalanceAvailable`, `constrainExposureMetering`, fps capped again for the size libcamera really configured | `CC:5971-5973`, `CC:6257-6262` |

Also run when settings are loaded (`CC:729-739`) and written (`CC:744`).

### 5.3 Sensor special-casing: where and how many copies

| Fact | Core, authoritative | Other copies |
| --- | --- | --- |
| Which sensor | `detectSensorFamily` `CC:2151-2167` (substring of camera id); name `CC:2169-2179` | `sensor.find("imx...")` in `App:1082-1243`, `App:4770-4773`; JS `sensorNameLower` `WCP:4810`; QML `imx585Detected` etc. `CameraPage.qml:373-376` |
| Allowed sizes | `isImx585*Resolution` `CC:360-396`, `isImx477Resolution` `CC:398-444`, `isImx294*Resolution` `CC:462-509`; used by `clampCaptureSettings` `CC:542-553` and `validateResolution` `CC:8751-8765` | `availablePcfResolutionOptions` `App:1182-1241`; `sensorResolutionOptions` `WCP:5112`; `CameraPage.qml:377-490` |
| Foreign size to this sensor | `sensorModeForRequestedResolution` `CC:2205-2269`, `normalizedResolutionForSensor` `CC:2372-2422` | none |
| Driver fallback modes | `kImx477Modes` `CC:2309-2335`, `kImx577FallbackModes` `CC:2354-2360` | none |
| Max fps per mode | `maximumSupportedFpsForResolution` `CC:2629-2683`, IMX477 tables `CC:2493-2627` | `maximumPcfFpsForSettings` `App:1076-1148`; `maximumSupportedFpsForSnapshot` `WCP:4928`; `CameraPage.qml:672-733` |
| RAW bit depths | `supportedRawBitDepthForSensor` `CC:2685-2705` (477/577: 8/10/12; 294/585: 10/12); `normalizeRawBitDepth` `CC:243-250` (anything else is 12) | `rawBitDepthOptions` `WCP:4053` |
| ISO range | 50..51200 at `CC:561` and `CC:7777`; lossless cap 800 at `CC:2483` | `pcfIsoOptions` `App:1279-1282`; `isoOptions` `WCP:4040`; `CameraPage.qml:513` |
| Lossless limits | `enforceLosslessCaptureLimits` `CC:2470-2491` | `isLossless*Snapshot` `WCP:4907-4922` |
| H.264 capture size | `h264CaptureResolutionForSensor` `CC:1890-1906` | none |
| Software RAW crop | `shouldUseRequestedActiveRawCrop` `CC:2851-2867` (477, 577, 294) | none |
| Fallback black level | `blackLevelsForSensor` `CC:2933-2940` (256 for 477/577, else 200) | none |
| Configure quirks | `CC:5993-5996` auto sensor config, `CC:6123-6133` log, `CC:6162-6183` readout check | none |
| DNG model string | `selection.dngModel` `CC:2218`, `CC:2222`, `CC:2242`, `CC:2262` | none |
| Built-in colour profile | IMX585 only: `ColorProfileConfig.cpp:239-243`, `:401-404` | none |
| Default tuning | by model name: `<name>.json`, `<name>_mono.json` `DefaultTuningSelection.hpp:130-181` | none |
| Still size estimate | none | `estimatedStillFrameSizeMiB` `App:4765-4836` |

Count: four layers hold sensor tables (CC, App, WebUI JS, touch UI QML). The copies already disagree at this tag: IMX294 3872x2176 is
41.08 / 40.95 fps in `CC:2650-2651` and 44.17 in `App:1133-1135`; IMX477 uses exact per-mode values in `CC:2493-2568` and round caps
(100 / 60 / 30 / 24) in `App:1099-1116`.

### 5.4 Record formats: how they are told apart

| Format | Enum | Settings profile | Stream roles | Writer | Folder prefix |
| --- | --- | --- | --- | --- | --- |
| cDNG (uncompressed, lossless) | `Cdng` + `cdngCompression` | `cdng` | VideoRecording YUV + Raw (`CC:6031-6037`) | `DngRecordingQueue` -> `CdngEncoder` (`CC:3711`, `CC:3744`) | `cDNG_` |
| Lossy DNG 3:1 / 5:1 | `LossyDng` + `lossyDngRatio` | `cdng` (`CC:605-608`) | same | `DngRecordingQueue` -> `LossyDngEncoder` (`CC:3713-3714`, `CC:3742`) | `cDNG_3to1_` / `cDNG_5to1_` (`CC:3655`) |
| MLV | `Mlv` | `mlv` | same | `DngRecordingQueue`, one worker -> `MlvEncoder` (`CC:3340-3341`, `CC:3805-3847`) | `MLV_` |
| H.264 | `H264` + `h264Resolution` | `h264` | Viewfinder + VideoRecording, RAW off by default (`CC:6017-6030`) | `H264PreviewRecorder` -> libav plugin or `ffmpeg` pipe (`CC:4044-4174`) | `H264_` |
| ProRes | `Prores` + `proresProfile` + `proresColorProfile` | `prores` | VideoRecording RGB48 + Viewfinder (`CC:6019-6020`, `CC:6092`) | `ProresRecorder` -> ProRes plugin | `ProRes_` |

Processed formats force 10-bit (`CC:2714-2716`) and a reconfigure when entered or left (`CC:7965-7969`).

### 5.5 Threads and queues

| Thread | Started | Loop | Queue bound | Ref |
| --- | --- | --- | --- | --- |
| libcamera completion callback | `camera_->requestCompleted.connect` | `requestComplete` | none: the only producer | `CC:6362`, `CC:6579-6669` |
| DNG / lossy workers | per take; count = `max(2, min(4, cores))`, lossless `min(8, cores+1)`, lossy `min(4, cores)`, MLV 1 | `dngWorkerLoop`, `mlvWorkerLoop` | 12 frames, 24 for compressed DNG on >= 4 cores | `CC:3323-3350`, `CC:3697`, `CC:3805` |
| Lossy disk writer | process-lifetime singleton | `threadMain` | 512 MiB of bytes; this one blocks the encode worker | `LossyDngEncoder.cpp:97-110`, `:162-173`, `:214-242` |
| H.264 copy worker | per take, 1 | `copyLoop` | 6 frames across copy + encode queues | `CC:4185-4189`, `CC:4832`, `CC:4465-4474` |
| H.264 encode worker | per take, 1 | `encoderLoop` | same | `CC:4902` |
| H.264 finalizer | per stop | `finalizeStop` | n/a | `CC:4728-4731`, `CC:4734` |
| ProRes worker | per take, 1 | `ProresRecorder::run` | `min(4, cameraBuffers - threads - 4)`, at least 1 | `ProresRecorder.cpp:60-65`, `:89`, `:110` |
| Photo writer | at first enqueue | `workerLoop` | 12 jobs | `CC:5055-5058`, `CC:5147`, `CC:5220` |
| Settings persister | at first schedule | `run`, 25 ms debounce | latest snapshot only | `CC:807-808`, `CC:844-872` |
| Timelapse | `startTimelapse` | `timelapseLoop` | n/a | `CC:8386`, `CC:8447` |
| Audio reader | per take | `readerLoop` | n/a | `AudioRecordingSession.hpp:39`, `:67` |

A take starts in this order: clip folder, gyro (failure is logged only), audio (failure aborts), recorder (`CC:5546-5647`).
A take stops in this order: close the frame gate, gyro, H.264, DNG queue, ProRes, audio (`CC:5658-5683`).
Recording frames begin only after the sensor cadence matches the requested fps (`CC:6652-6661`).
The DNG frame index comes from the sensor timestamp, so a dropped frame leaves a gap in the file numbers (`CC:3518-3526`).

### 5.6 How a failure latches and stops a take

| Step | What | Ref |
| --- | --- | --- |
| 1 | A worker catches the exception or gets `false`: `failure_.set(message)` (first message wins), `active_ = false`, `stopping_ = true`, queue cleared, one log line | `CC:3747-3752`, `CC:3849-3859`; `CC:4937-4955`; `ProresRecorder.cpp:122-135`; `RecordingFailure.hpp:11-16` |
| 2 | `CameraSession::recordingError()` returns the audio error first, then the error of the recorder that matches `lastRecordingFormat_` | `CC:5891-5901` |
| 3 | `CameraController::checkRecordingFailure()` runs under `commandMutex_` every second and before every command. On an error it stops the take, sets `Ready`, stores the message, emits `recording` with `active:false` and `error` | `CC:8519-8534`; `App:7031-7034`, `App:9094` |
| 4 | The message is in `get_state` and `/api/state` as `recording_error`; the WebUI shows a toast; the touch UI raises `recordingFailed` | `App:9226`, `App:7842`; `WCP:9331-9333`; `Apertar-UI/src/ApertarControlBridge.cpp:1277-1283` |
| 5 | A normal `stopRecording()` also returns `false` with the message if a failure was latched | `CC:8502-8517` |

There is no check for free space or a mounted drive in `CC`. A full or missing drive shows up through this latch.

### 5.7 How dropped frames are detected and reported

| Detector | Condition | Marks the clip warning | Log | Ref |
| --- | --- | --- | --- | --- |
| RAW queue full, before the copy | `queue_.size() >= maxQueuedFrames_` | yes | `ApertarCore drop[queue-full]: frame= dropped_total= queue=a/b` | `CC:3528-3546`, `CC:3579-3590` |
| H.264 queue full | copy + encode queues >= 6 | yes | `ApertarCore H.264 drop[queue-full]: total=` | `CC:4271-4280`, `CC:4888-4896` |
| ProRes queue full | queue >= capacity | yes | `ApertarCore ProRes drop[queue-full]: total=` | `ProresRecorder.cpp:98-103` |
| Capture gap | sensor timestamp step > 1.5 x the frame time; estimate = round(step / frame) - 1 | yes | `ApertarCore drop[capture-gap]: +n frame(s) estimate dt_us= nominal_us= total_estimate=` | `CC:7181-7226` |
| RAW copy failed (DMA sync) | `copyRawBytes` false | yes | `ApertarCore DMA read sync ... failed` | `CC:6932-6936`, `CC:6426-6436` |
| Requeue failed | `queueRequest < 0` | no | `ApertarCore drop[requeue-failed]: total=` | `CC:6568-6576` |

Reporting: `RecordingDropWarning::markDropped()` fires its callback once per clip (`RecordingDropWarning.hpp:16-19`), reset at take start
(`CC:5634`, `CC:5645`). The callback sends `{"event":"recording_health","recording_has_dropped_frames":true}` (`CC:7580-7584`), which is
always broadcast (`App:10830`). The same boolean is in the `recording` event (`CC:8793`), `get_state` (`App:9227`), `/api/state` (`App:7843`)
and the `record_start` / `record_stop` replies (`App:10712-10713`, `App:10792-10793`). Counts are printed once at stop:
`ApertarCore recording stats: enqueued= written= dropped_queue_full= discarded_on_stop= write_failures= peak_queue=a/b` (`CC:3416-3423`) and
`ApertarCore capture stats: dropped_gap_estimate= requeue_failures=` (`CC:5666-5671`).

### 5.8 Per-format settings profiles

| Fact | Ref |
| --- | --- |
| Storage: `std::map<RecordingFormat, CaptureSettings> formatSettings_` and `std::optional<CaptureSettings> stillSettings_` | `CC.hpp:116-117` |
| Every commit stores the whole active `CaptureSettings` into the profile of the current format, or into the still profile in photo mode | `CC:8725-8732` |
| Lossy DNG uses the cDNG profile | `CC:605-608` |
| Switching format loads the saved profile of the new format, then keeps from the current settings: tuning file, timecode mode, metering mode, and the still flags | `CC:7939-7961` |
| Switching photo / video restores only resolution, bit depth and fps from the saved profile | `CC:8734-8749` |
| File: active settings without prefix, then `profile.<name>.key=value` with name one of `cdng`, `mlv`, `h264`, `prores`, then `profile.still.key=value` | `CC:780-788` |
| Loader: unknown profile names are skipped; a profile starts as a copy of the settings read so far | `CC:634-648` |

A new `CaptureSettings` field is per profile by default. To make it global it must be carried over at `CC:7945-7951`.

### 5.9 Encoders: classes, plugins, header-only

| Piece | Kind | Linked into | Ref |
| --- | --- | --- | --- |
| `CdngEncoder` (+ `Csi2RawConverter`, `LosslessJpegEncoder`, `IfdBuilder.hpp`, `BlackLevel.hpp`) | class, one instance per worker thread, throws | Core | `CdngEncoder.hpp:22-201`, `CC:3711` |
| `LossyDngEncoder` (+ singleton `LossyDngDiskWriter`) | class, wraps a `CdngEncoder` | Core | `LossyDngEncoder.hpp:14-53` |
| `MlvEncoder` | class, `open` / `writeFrame` / `close` with `std::string *error` | Core | `MlvEncoder.hpp:14-71` |
| `ProresRecorder` | class in Core, dlopen client + queue + worker | Core | `ProresRecorder.hpp:16-49` |
| `ProresEncoder`, `ProresColor`, `ProresRepair`, `ProresPlugin.cpp` | plugin `apertar-prores-libav.so` | plugin | `CMakeLists.txt:152-169` |
| `LibavH264EncoderClient` | dlopen client | Core | `LibavH264EncoderClient.hpp:11-36` |
| `LibavH264EncoderPlugin.cpp` (+ header-only `NativeV4l2H264Encoder.hpp`) | plugin `apertar-h264-libav.so` | plugin | `CMakeLists.txt:143-149` |
| `AudioRecordingSession`, `TimestampedAudioCapture` (pimpl, dlopen of `libasound.so.2`) | classes | Core | `AudioRecordingSession.hpp:20-79`, `TimestampedAudioCapture.cpp:24-49` |

Header-only files (no `.cpp`): `Types.hpp`, `RecordingCapabilities.hpp`, `ProresColorProfile.hpp` (one function defined in `ProresIspProfile.cpp:104`),
`PreviewExposureReference.hpp`, `src/camera/{DefaultTuningSelection,ExposureMetering,ScalerCropGeometry,StillBracketing}.hpp`, `src/cdng/{BlackLevel,IfdBuilder}.hpp`,
`src/audio/{AudioSample,RecordingClock}.hpp`, `src/color/{StillColorProcessing,StillSrgbProfile}.hpp`, `src/video/{H264Hardware,NativeV4l2H264Encoder,LibavH264PluginApi}.hpp`,
`src/prores/ProresPluginApi.hpp`, `src/util/*.hpp`.

All encoders take the same frame description, `RawFrameView` (`Types:203-218`), and the same metadata struct, `CdngEncoder::Metadata`
(`CdngEncoder.hpp:24-85`), which MLV and lossy DNG reuse (`MlvEncoder.hpp:18-25`, `LossyDngEncoder.hpp:23-24`).

### 5.10 Events the camera side emits

| Event | Where | When |
| --- | --- | --- |
| `settings` | `CC:139`, sent by `emitSettingsEventLocked` `CC:8777-8784` | every commit and every no-op setter call |
| `recording` | `CC:8786-8796` | take start, stop, failure |
| `recording_health` | `CC:7580-7584` | drop latch set or reset |
| `media_write_state` | `CC:7551-7563` | pending-write edge |
| `still_exposure` | `CC:7565-7574` | long exposure start / end |
| `photo_write_error` | `CC:5246-5250` | first still write error |
| `standby` | `CC:7687-7688`, `CC:7706-7707` | enter / wake |
| `audio_level` | `CC:7587-7596` | during audio capture |
| `timelapse`, `timelapse_frame`, `timelapse_progress` | `CC:8798-8832`, `CC:8440-8445` | timelapse |

### 5.11 Every `getenv` in the topic files

None is documented in `README.md`. "Read" tells when the value is looked at.

| Variable | Purpose | Default; bounds | Read | Ref |
| --- | --- | --- | --- | --- |
| `XDG_CONFIG_HOME`, `HOME` | Folder of `camera_settings.conf` | temp dir if both missing | each call | `CC:344`, `CC:348` |
| `HOME` | Cache folder of the derived ISP tuning (`~/.cache/apertar-prores/<profile>.json`) | required | each reconfigure with a log profile | `ProresIspProfile.cpp:228-230` |
| `LIBCAMERA_RPI_TUNING_FILE` | Seed for the custom tuning when none is saved; in simulate mode decides the metering mask. Core sets and unsets it itself | none | constructor; simulate paths | read `CC:7603`, `CC:7641`, `CC:8717`; set `CC:1116`, `CC:1119`, `CC:5360` |
| `APERTAR_SENSOR_TUNING_FILE` | Set by Core to the original sensor tuning; read by the colour code before `LIBCAMERA_RPI_TUNING_FILE` | none | per calibration lookup (cached by mtime) | set `CC:1114`, `CC:1120`; read `ColorProfileConfig.cpp:616-617` |
| `APERTAR_DEFAULT_TUNING_DIR` | Replaces the default tuning folder | `/home/pi/Tuning-Files/defaults-{pisp,vc4}` | camera start | `DefaultTuningSelection.hpp:58` |
| `APERTAR_COLOR_PROFILE_CONFIG` | Path of the colour profile file | `/home/pi/apertar-color-profiles.conf` | profile load | `ColorProfileConfig.cpp:234` |
| `APERTAR_H264_CAMERA_BUFFERS` | libcamera buffer count in H.264 mode | 4 with hardware H.264, else 6; 3..12 | configure | `CC:1127` |
| `APERTAR_PRORES_CAMERA_BUFFERS` | libcamera buffer count in ProRes mode | 12; 8..32 | configure | `CC:1133` |
| `APERTAR_H264_SIZE` | Force the H.264 encode size `WxH` | off; must be a supported size, else one log line | configure | `CC:2779-2794` |
| `APERTAR_H264_KEEP_RAW_STREAM` | Keep the RAW stream in H.264 mode | false | configure | `CC:2843` |
| `APERTAR_H264_SINGLE_STREAM` | One YUV stream for preview and encode | false | configure | `CC:2848` |
| `APERTAR_RAW_CACHED_DMABUF` | CPU-cached DMA heap for PiSP-compressed RAW | true | configure | `CC:6321` |
| `APERTAR_PRORES_CACHED_DMABUF` | Same for ProRes; `0` turns it off | on | configure | `CC:6387` |
| `APERTAR_CDNG_QUEUE_FRAMES` | RAW queue depth | 12, or 24 for compressed DNG on >= 4 cores; 4..64 | take start | `CC:3329-3330` |
| `APERTAR_CDNG_WORKERS` | Lossless cDNG worker count | `min(8, cores+1)` on >= 4 cores; 1..8 | take start | `CC:3343` |
| `APERTAR_LOSSYDNG_WORKERS` | Lossy DNG worker count | `min(4, cores)`; 1..8 | take start | `CC:3345` |
| `APERTAR_CDNG_WORKER_NICE` | Nice value of compressed-DNG workers | 0 lossless, 5 lossy; 0..19 | take start (per worker) | `CC:3359`, `CC:3706` |
| `APERTAR_CDNG_TILE_ROWS` | Rows per lossless JPEG tile | 128; 16..1024 | once per process | `CdngEncoder.cpp:55` |
| `APERTAR_CDNG_PROFILE_DETAIL` | Detailed lossless timing | off | once per process | `CdngEncoder.cpp:72` |
| `APERTAR_LOSSYDNG_WRITER_BYTES` | Byte cap of the lossy disk-writer queue | 512 MiB; >= 16 MiB | once per process | `LossyDngEncoder.cpp:100` |
| `APERTAR_LOSSYDNG_ASYNCWRITE`, old name `QRAW_LOSSYDNG_ASYNCWRITE` | `0` writes on the encode worker | async | per encoder (per take) | `LossyDngEncoder.cpp:325-328` |
| `APERTAR_H264_ENCODER` | Encoder name | `libx264`; must be `h264_v4l2m2m` on Pi 3/4 | take start | `CC:3981`, `CC:4333` |
| `APERTAR_H264_PRESET` | x264 preset | `ultrafast` | take start | `CC:4340` |
| `APERTAR_H264_TUNE` | x264 tune; `none`/`off`/`false`/`0` clears it | `zerolatency` | take start | `CC:4347` |
| `APERTAR_H264_CRF` | CRF | `18` | take start | `CC:4363` |
| `APERTAR_H264_QP` | Constant QP | unset | take start | `CC:4370` |
| `APERTAR_H264_BITRATE` | Bitrate | `20M` with hardware H.264, else unset | take start | `CC:4377` |
| `APERTAR_H264_MAXRATE`, `_BUFSIZE`, `_X264_PARAMS` | Rate control and raw x264 parameters | unset | take start | `CC:4384`, `CC:4391`, `CC:4398` |
| `APERTAR_H264_BACKEND` | `libav`, `pipe` or `auto` | `auto` | take start | `CC:4406` |
| `APERTAR_H264_THREADS` | Encoder threads; `auto` / `0` leaves it to the encoder | 1 on <= 2 cores, else `min(4, cores-1)`; <= 16 | take start | `CC:4435` |
| `APERTAR_H264_PIPE_BYTES` | Pipe size to `ffmpeg` | 1 MiB; 64 KiB..16 MiB | take start | `CC:4456` |
| `APERTAR_H264_QUEUE_FRAMES` | H.264 queue depth | 6; 2..16 | take start | `CC:4467` |
| `APERTAR_H264_LIBAV_PLUGIN` | Path of the H.264 plugin | next to the executable | first H.264 take | `LibavH264EncoderClient.cpp:20` |
| `APERTAR_PRORES_PLUGIN` | Path of the ProRes plugin | next to the executable | first ProRes take | `ProresRecorder.cpp:28` |
| `APERTAR_PRORES_THREADS` | ProRes frame threads | 4; 1..4 | take start | `ProresRecorder.cpp:61`, `ProresEncoder.cpp:831` |
| `APERTAR_PRORES_CSC_THREADS` | Colour conversion threads | 1 or 2; 1..8 | clip open | `ProresEncoder.cpp:1323` |
| `APERTAR_PRORES_ODIRECT` | `0` selects buffered writes | direct | clip open | `ProresEncoder.cpp:1098` |
| `APERTAR_PRORES_WRITEBACK` | Writeback window in MiB | off; 4..512 | clip open | `ProresEncoder.cpp:1154` |
| `APERTAR_PRORES_WRITER_THREAD`, `_WRITER_QUEUE`, `_WRITER_QUEUE_MB`, `_WRITER_SLOW_MS` | Writer thread on/off, queue depth, queue bytes, slow-write log limit | on; 1..512; 8..1024; 0..60000 | clip open | `ProresEncoder.cpp:1184-1203` |

Four reading styles: the helpers `unsignedEnvValue` / `boolEnvValue` (`CC:1027-1061`); one small getter per knob (`CC:4329-4474`); a read-once
`static const` lambda (`CdngEncoder.cpp:51-76`); the ProRes `tuningOverride(name)`, which looks at the environment first and then at
`/home/pi/.apertar-tuning` (`ProresEncoder.cpp:787-813`).
`src/audio` and `src/mlv` read no environment variable. `APERTAR_MLV_ENABLE_NEON_PACKER` is a compile-time macro (`MlvEncoder.cpp:23`).
`APERTAR_PRORES_TRANSFER`, `_QP_PRED` and `_ISP_FORMAT` appear only in comments and one error text (`ProresEncoder.cpp:875`, `:1004`, `:1375`,
`:1383`); no code reads them at this tag.

### 5.12 Deliberately absent

| Absent | How it was checked |
| --- | --- |
| Unit tests, test harness, CI | `git ls-files` (137 files): no test file; `.github/` = `FUNDING.yml` |
| Interfaces, base classes, factories, dependency injection | S2 |
| A logging framework, log levels, a debug switch | I6: `std::cerr` only; `grep -c 'std::clog\|syslog' <topic files>` = 0 |
| A config file or config section for recorder tuning | S22, N11 |
| Shared string / JSON / INI utility module | S6 |
| A JSON library, `libpng`, `libtiff`, a DNG SDK | S23, `CMakeLists.txt:25-45` |
| Vendor (`rpi::`) or driver-specific libcamera controls | N12: the 43 control names used are all mainline |
| A sensor description table (data-driven modes) or a mode probe | S11: modes and caps are code |
| A check for free space or a mounted drive before a take | `grep -nE 'statvfs\|filesystem::space\|is_mount\|/proc/mounts' CC` gives 0 hits; `CC:8219-8264` |
| Frame counts or queue depth in the socket API | 5.7: only a boolean leaves Core |
| Commit history | one commit, `35dbe67` |
| Formatter config, contributor guide, changelog | S24 |

### 5.13 Rough edges that are part of the Apertar way

A contribution that tidies these without being asked is a mismatch of its own kind.

| # | Rough edge | Ref |
| --- | --- | --- |
| 1 | One 8834-line file holds the session, three recorders, the still pipeline, PNG and TIFF encoders and the persister | `CC` |
| 2 | Sensor tables in four layers, already drifted | 5.3 |
| 3 | Settings JSON field list three times | I13 |
| 4 | Small helpers copied per file | S6 |
| 5 | Names kept from their first use: `H264PreviewRecorder` and `h264Stream_` also serve ProRes (`CC:7377`, `CC:6187`); `h264EncodeBounds` handles ProRes (`CC:2771-2772`); `isImx585LowResolutionAlias` is used to map sizes for IMX477 and IMX577 (`CC:450`, `CC:2228`); the `Pcf` prefix in `App` covers every hardware input (`App:1030-1322`) | as listed |
| 6 | `discardedOnStopFrames_` is never incremented, so `discarded_on_stop` is always 0 | `CC:3304`, `CC:3509` (only uses) |
| 7 | `uniqueCameraModelForSensor` ignores both arguments and returns `"Blackmagic Micro Cinema Camera"` | `CC:3017-3022` |
| 8 | `isSupportedProcessedVideoResolution` ignores `format` | `CC:277-281` |
| 9 | Lossy DNG disk-write errors do not fail the take | `LossyDngEncoder.cpp:228-232` |
| 10 | Frames without measured white balance are skipped with one log line and no drop mark | `CC:6857-6863` |
| 11 | Requeue failures are logged but never reach the operator | `CC:6568-6576` |
| 12 | Timelapse overwrites its own "Previous still is still exposing" message | `CC:8473`, `CC:8478` |
| 13 | Two formatting densities in one file | I20 |
| 14 | Imported QRAW comments, stale knob names, and unused files: `src/lossydng/LossyJpeg12.{h,cpp}` and `fastent.h` are not built or included; `ProresRepair` is compiled but only `recoverySidecarPath` is called | `ProresEncoder.hpp:3-42`; `grep -rn 'LossyJpeg12\|fastent' src CMakeLists.txt` (no user); `ProresEncoder.cpp:1257` |
| 15 | `README.md:225` points to `src/prores/ffmpeg/`, which is not in the tree | `git ls-files \| grep ffmpeg` gives nothing |
| 16 | The WebUI does not show the dropped-frame warning | N3 |
| 17 | Unknown enum strings silently become the default in `CC`, while `App` rejects them | `CC:199-219` vs `App:824-844` |

### 5.14 Closest precedent for common additions

| To add | Copy this | Ref |
| --- | --- | --- |
| A control-only camera setting | exposure compensation | `Types:131-132`, `CC:538-539`, `CC:665-666`, `CC:752`, `CC:2040-2044`, `CC:7835-7849`, `App:9251` |
| A setting that changes the stream | RAW bit depth | `Types:152`, `CC:243-250`, `CC:2685-2705`, `CC:8114-8148` |
| A record-format sub-option | ProRes profile | `Types:63-68`, `Types:147`, `Types:276-285`, `CC:694-696`, `CC:763`, `CC:8001-8012`, `App:9378-9386`, `ProresRecorder.cpp:66-72` |
| A limit that depends on sensor and format | lossless caps | `CC:2470-2491` |
| A runtime capability flag | `whiteBalanceAvailable` | `Types:142`, `CC:5504`, `CC:8780-8781`, `CC:7891-7894` |
| A per-take option that is not a camera setting | `GyroRecordingOptions` | `Types:199-201`, `App:10633-10637`, `CC:5555-5568` |
| A clip-scoped operator warning | `RecordingDropWarning` | `src/util/RecordingDropWarning.hpp`, `CC:7580-7584` |
| A background failure that must stop the take | `RecordingFailure` | `src/util/RecordingFailure.hpp`, `CC:5891-5901`, `CC:8519-8534` |
| Pure maths for one feature | `StillBracketing.hpp` | `src/camera/StillBracketing.hpp:8-19` |
| A bench knob | `APERTAR_CDNG_QUEUE_FRAMES` | `CC:3329-3330` |
| An optional heavy dependency | H.264 plugin | `CMakeLists.txt:143-149`, `LibavH264EncoderClient.cpp:97-131` |

---

## 6. Recipes

### R1. Add a sensor

1. `CC:1882` add the enumerator to `enum class SensorFamily`.
2. `CC:2151` `detectSensorFamily`: one more `if (lower.find("imxnnn") != std::string::npos)`. Order matters only if one name contains another.
3. `CC:2169` `sensorFamilyName`: the display string. It becomes `"sensor"` in `get_state` (`App:9237`) and is what every UI matches on.
4. `CC:355-532` add `isImxNNNResolution(const Resolution &)` as a chain of `resolutionMatches(...) ||`. Add it to both allow-lists: `clampCaptureSettings` `CC:542-553` and `validateResolution` `CC:8751-8765`.
5. `CC:2205` `sensorModeForRequestedResolution`: new `case` that maps foreign sizes onto this sensor and sets `dngModel`.
6. `CC:2372` `normalizedResolutionForSensor`: new `case` with the same mapping.
7. `CC:2289` `sensorModeCandidatesForRequestedResolution`: only if the driver needs fallback candidates (precedents `CC:2309`, `CC:2354`).
8. `CC:2629` `maximumSupportedFpsForResolution`: new `case`, fps per mode as literals.
9. `CC:2685` `supportedRawBitDepthForSensor`: add to the right `case` group.
10. `CC:1890` `h264CaptureResolutionForSensor` and `CC:2424` `isFourKCaptureResolution`: new `case` (these switches have no `default`; `-Wall` flags a missing one).
11. Quirks only where the driver needs them: `CC:2851` software crop, `CC:2933` fallback black level, `CC:5993-5996` auto sensor config, `CC:6123` trying log, `CC:6162` readout check, `CC:2470` lossless caps, `CC:3208` frame colour matrix.
12. Colour: a tuning file `<model>.json` in `/home/pi/Tuning-Files/defaults-pisp/` or `defaults-vc4/` (found by `DefaultTuningSelection.hpp:144-181`; not in the repo). Optional built-in DNG profile like `ColorProfileConfig.cpp:239-243`.
13. `App` copies: `maximumPcfFpsForSettings` `App:1076`, `availablePcfFpsOptions` `App:1150`, `availablePcfResolutionOptions` `App:1182`, `estimatedStillFrameSizeMiB` `App:4765`.
14. WebUI copies: `WCP:4824` (fps tables), `WCP:4928` (max fps), `WCP:5112` (sizes), `WCP:5249` (crop options), `WCP:5452` (command payload).
15. Touch UI copies: `Apertar-UI/qml/CameraPage.qml:377-490` (lists and `...Detected`), `:733` (max fps), `:946` (options per sensor); `SettingsPage.qml`.
16. `README.md:76-81` sensor list.
17. Check on the Pi: `ApertarCore camera configured: sensor=IMXNNN raw=... stream=...` (`CC:6264`).

### R2. Add a resolution or an fps option

Resolution on an existing sensor:
1. The driver must offer the mode. Core does not install drivers (`README.md:87`).
2. `CC`: add the size to the sensor's predicate (IMX585 `CC:366-377` or `CC:385-396`; IMX477 `CC:398-444` and `kImx477Modes` `CC:2309-2335`; IMX294 `CC:462-509`).
3. `CC:2629-2683` (IMX477: `CC:2493-2627`) add the fps cap of the new size.
4. Usually no edit: the allow-lists and mappers call the predicates (`CC:548-553`, `CC:8758-8763`, `CC:2251-2258`, `CC:2410-2415`).
5. `App:1182-1241` (`availablePcfResolutionOptions`) and `App:1076-1148` (`maximumPcfFpsForSettings`).
6. WebUI `WCP:5112`, `WCP:5249`, `WCP:4928`.
7. Touch UI `CameraPage.qml:377-490`, `:733`.
8. H.264 output sizes are a different list: `kSupportedSizes` `CC:263-268`, migration table `Caps:94-95`, `WCP:4054`.

fps:
1. Core has no fps menu. `setFps` takes 0 < fps <= 280 (`CC:7748`) and lowers it to the mode maximum (`CC:2732-2741`). A new menu value needs no Core change unless it is above a cap.
2. Change a cap: `CC:2629` (per mode), `CC:2470-2491` (lossless), `Caps:102-103` (hardware H.264 30 fps).
3. Mirror the cap: `App:1076`, `WCP:4928` and `WCP:4907-4922`, `CameraPage.qml:733`.
4. Menu values: hardware steps `App:1150-1168`; WebUI `fpsPresets` `WCP:4039`; touch UI `availableFpsOptions` `CameraPage.qml:802`.

### R3. Add a record-format option (sub-option of an existing format)

1. `Types:45-68` new `enum class`; `Types:144-153` field with default in `CaptureSettings`; `Types:254-285` `toString`.
2. If only some boards can do it: `Caps:64-77` (the sentence), `Caps:79-106` (the fallback), `Caps:52-62` (flag for the UIs).
3. Persist: load `CC:683-696`, write `CC:760-765`. It is stored per format profile without more code (`CC:8725-8732`).
4. Setter: declaration `CC.hpp:50-58`; body like `setProresProfile` `CC:8001-8012`: capability check, `recording_` gate with "... changes are blocked while recording.", `applySettingsLocked(next, false)`. Pass a condition instead of `false` if the stream changes (`CC:8028`, `CC:8173`).
5. If the option limits fps, ISO or bit depth: `sanitizeSettingsForSensor` `CC:2707-2744`, precedent `CC:2470-2491`.
6. Use it where the take starts: `DngRecordingQueue::startAtFolder` `CC:3279-3376` (worker count and the start log line), `dngWorkerLoop` `CC:3697-3766`, or `ProresRecorder::startAtFolder` `ProresRecorder.cpp:51-93`. Folder prefix only if the operator must tell clips apart: `CC:3646-3662`.
7. JSON three times: `CC:163-168`, `App:193-198`, `App:7877-7882`.
8. Command: `if (command.name == "set_...")` like `App:9378-9386`; add the name to the `help` list `App:9216`; presets `App:6677`, `App:10315`.
9. WebUI: value mapper `WCP:5565`, sender `WCP:9942`, optimistic patch `WCP:8748`.
10. Touch UI: `Q_PROPERTY` + `Q_INVOKABLE` in `Apertar-UI/src/ApertarControlBridge.hpp:29`, `:120`; `.cpp:494`, `:1415`.

A new top-level `RecordingFormat` needs in addition: `Types:254-264`; `recordingFormatFromString` `CC:199-219`; profile name list `CC:639`; format check `CC:579-585`; `settingsProfileFormat` `CC:605-608`; `isProcessedVideoFormat` `CC:221-224`; stream roles `CC:5985-6037`; writer start `CC:5589-5647`; `recordingError` `CC:5891-5901`; folder prefix `CC:3646-3662`; `normalizeRecordingFormatValue` `App:824-857`; `recordFormatOptions` `WCP:4044`; sources in `CMakeLists.txt:69-96` or a `MODULE` plugin like `CMakeLists.txt:152-169`.

### R4. Add a per-frame control

1. `Types:124-162` field with default. If the pipeline may lack the control, add a capability field with the trailing-comment style (`Types:132`).
2. `clampCaptureSettings` `CC:534-601`: clamp, or reset to `CaptureSettings{}` (pattern `CC:538-539`).
3. Persist: load `CC:665-666`, write `CC:752`.
4. `controlsForSettings` `CC:2005-2144`: set the control, guarded by `controlInfoHas` / `intControlSupportsValue` / `controlInfo.find` (pattern `CC:2040-2044`). Nothing else builds controls.
5. Setter: declaration `CC.hpp:45`; body like `CC:7835-7849`: lock, range check with a sentence, capability check, copy `settings_`, `applySettingsLocked(next, false)`. No `recording_` gate if the control is safe during a take.
6. Capability getter on the session if needed (`CC:5812-5819`), filled at `CC:8570` and `CC:8779`.
7. JSON three times: `CC:149-150`, `App:178-179`, `App:7865-7866`.
8. Command like `App:9251-9258`; `help` list `App:9216`.
9. If the value belongs in file metadata, read what the frame really used from the request metadata in `metadataFromRequest` `CC:3182-3202`, not from the settings.
10. WebUI and touch UI controls.

Timing: `applyControls` replaces `pendingControls_` (`CC:5511`); the next request that is requeued carries it (`CC:6503-6509`). No log line is written.

### R5. Add a bench knob (internal tuning)

1. Name it `APERTAR_<AREA>_<KNOB>`.
2. Read it where it is used, at take start or configure, with `unsignedEnvValue(name, default, min, max)` or `boolEnvValue(name, default)` (`CC:1027-1061`); in an encoder `.cpp` use a read-once `static const` lambda (`CdngEncoder.cpp:51-65`).
3. Print the effective value in the take-start log line (`CC:3353-3374`).
4. Do not add it to `camera_settings.conf`, `apertar-hardware.conf`, the socket API or `README.md`.

---

## 7. Note outside topic C2: the GPIO chip key

The request that started this run asks to put the chip definition back, because GPIO lines can come from a chip other than the Pi's own.
Upstream already has that concept, so reinserting it follows the Apertar way. Not part of this topic; one `grep` only.

| Fact | Ref |
| --- | --- |
| `GpioInput` config field `std::string chipPath = "auto";`, key `chip` / `gpiochip` / `gpio_chip`, empty means `auto` | `src/hardware/GpioInput.hpp:48`, `src/hardware/GpioInput.cpp:431-432` |
| `auto` scans `/dev/gpiochipN` and scores the chips; an explicit path is used as given | `src/hardware/GpioInput.cpp:507-535` |
| Same key in the trigger output and the tally LED | `src/hardware/TriggerOutput.hpp:45`, `TriggerOutput.cpp:311-312`; `src/hardware/RecordingIndicatorOutput.hpp:40`, `RecordingIndicatorOutput.cpp:319-320`, `:347-348` |
| Core's config template shows `gpiochip=auto` for the trigger output and the tally LED. It does not show the key in its `[gpio]` section, although the parser takes it | `App:4380`, `App:4394`; `grep -n -i 'chip' src/ApertarCoreApp.cpp` gives only those two lines |
| The touch UI's first-run template does show `chip=auto` in the GPIO sections, and `gpiochip=auto` for trigger and LED. The INA219 copy of the template has the same lines | `Apertar-UI/src/DisplayConfigBridge.cpp:161`, `:172`, `:110`, `:123`; `Apertar-UI/src/Ina219Bridge.cpp:180`, `:191`, `:129`, `:142` |

## 8. Unconfirmed

| Claim | Command that settles it |
| --- | --- |
| The denser second style (I20) is a later hand or a later period | Not answerable from one commit. Ask the original developer, or compare with an older release if one exists |
| Which sensor was added last, and in which order the copies were edited | Same |
| The log lines of 5.7 as they look on a Pi | `sudo journalctl -u apertar-core -b \| grep -e 'drop\[' -e 'recording stats' -e 'capture stats'` after a take that drops |

---

## Challenge

Challenger pass, 2026-11-17, on `/home/user/wt/core-upstream` (`upstream-1.6.0`, `35dbe67`). All refs `@upstream-1.6.0`.
Rule: a rule marked "always" whose own "Exceptions" column names a real counter-example is weakened to "usually".
An exception that is a different kind of thing (not the opposite behaviour) leaves the rule at "always".

### Verdicts per rule

| Id | Verdict | Counter-example or check |
| --- | --- | --- |
| S1 | holds | `grep -rln '#include <libcamera' src include` gives only `CC` |
| S2 | holds | `grep -rnE '\bvirtual\b\|\boverride\b'` gives 2 word hits (`CC:3983` string, `ProresEncoder.hpp:99` comment); inheritance regex `(class\|struct) X : public` gives 0. The template seam is not a hierarchy |
| S3 | holds (usually) | - |
| S4 | holds (usually) | - |
| S5 | holds | `ls include/apertar/core` = 4 files |
| S6 | weaken to usually | Shared byte/file helpers do exist: `src/util/SettingsFile.hpp:25-56` `settingsFile::writeAll` and `atomicWrite` (free functions, no state) used by `CC:789`, `App:1934`, `App:6509`, `App:6740`, `ProresIspProfile.cpp:233`. `escapeJson` is both copied (`CC:95`, used `CC:170`) and shared: `CC:5249`, `CC:7029`, `CC:8794` call `apertar::escapeJson` from `src/ipc/ControlProtocol.hpp:25` |
| S7 | holds | 25 `bool set...` in `CC.hpp`; `applyCapturePreset` is also a `bool` method |
| S8 | holds (usually) | - |
| S9 | holds | `setTuningFile` is still a full reconfigure, on its own path (S8) |
| S10 | weaken to usually | `CC:6522-6526` bracket shots set `AnalogueGain`, `AwbEnable`, `ColourGains` on the request directly. Search: `grep -n 'controls::' CC` outside `CC:2005-2144` gives only these three sets plus enum mappers `CC:1951-1974` and the capability probe `CC:5826-5829` |
| S11 | weaken to usually | Sensor knowledge outside `SensorFamily`: `ColorProfileConfig.cpp:242-243` matches `"imx585"` by substring of the model name; `DefaultTuningSelection.hpp:130-181` picks tuning by model name |
| S12 | holds | - |
| S13 | holds | - |
| S14 | holds | - |
| S15 | holds | - |
| S16 | weaken to usually | `PhotoCaptureWriter` has no `start...(folder, ...)`; its thread starts at the first enqueue (`CC:5055-5058`) |
| S17 | holds (once) | - |
| S18 | holds | `grep -rn dlopen src` = 3: ALSA, H.264 plugin, ProRes plugin |
| S19 | holds | - |
| S20 | holds | `grep -rn camera_settings` in `ui-upstream/src`, `ui-upstream/qml` and `core-upstream/src` outside `CC` gives 0 |
| S21 | holds | `Types:132`, `:134`, `:139`, `:142`, `:150` |
| S22 | holds | grep repeated, 0 hits |
| S23 | holds (usually) | - |
| S24 | holds | `git ls-files` = 137, no test / third_party / tools / formatter file |
| I1 | holds (usually) | - |
| I2 | holds | - |
| I3 | holds | `std::optional` returns exist (`StillBracketing.hpp:8`, `ScalerCropGeometry.hpp:16`, `ColorProfileConfig.cpp:830`) but mean "no value", not "failed with a reason" |
| I4 | holds | - |
| I5 | weaken to usually | Holds for every `setErrorLocked` in `CC` (0 of the setter strings lack a period). Fails deeper down, and these strings reach the operator through the failure latch (`ProresRecorder.cpp:124` `failure_.set(why.data())`): `ProresEncoder.cpp:744` `"ProRes writer: packet alloc"`, `:1435` `"ProRes: frame alloc"`, `:1455` `"ProRes: buffer wrap"`; `CC:5282` `"libcamera CameraManager failed to start, code " + ret` (code, no period); `CC:4774` `"H.264 encoder exited with code "` |
| I6 | weaken to usually | `LibavH264EncoderPlugin.cpp:245` `std::fprintf(stderr, "ApertarCore H.264 native ...")` is in a topic file. Prefix `ApertarCore` holds in every case found |
| I7 | holds | - |
| I8 | weaken to usually | The shape `n == 1 \|\| n % N == 0` holds in all 8 hits. N is 30 in 6; `CC:5062` uses 10; `CC:7216` adds `\|\| droppedEstimate > 1` |
| I9 | weaken to usually | A bad value is not always a silent fallback: `CC:3981-3985` fails the take start; `CC:2789-2792` logs. Not every name is `APERTAR_`: `QRAW_LOSSYDNG_ASYNCWRITE` (`LossyDngEncoder.cpp:325-328`), `LIBCAMERA_RPI_TUNING_FILE` (`CC:1116`) |
| I10 | holds (usually) | Add exception: the ProRes writer state has no `_` suffix (`ProresEncoder.cpp:423-433` `writerThread`, `writerMutex`, `writerStop`) |
| I11 | holds (usually) | - |
| I12 | holds | No JSON library: `grep -rniE 'nlohmann\|rapidjson\|QJson'` gives 0 |
| I13 | holds | - |
| I14 | holds | - |
| I15 | holds | - |
| I16 | weaken to usually | Not one CV and one deque: H.264 recorder has `cv_` + `encodeCv_` and two deques (`CC:4990-4994`); settings persister `cv_` + `flushedCv_` (`CC:875-876`); ProRes writer `writerWork` + `writerRoom` + `writerStop` (`ProresEncoder.cpp:423-433`); `CscPool` is a barrier pool (`ProresColor.cpp:290-296`) |
| I17 | holds | - |
| I18 | holds | Guards counted: LIBCAMERA 23, LIBAV 6, JPEG 8, TURBOJPEG 4, NEON 1 |
| I19 | restate as usually | Block-comment count per file: 0 in `CC`, `ProresRecorder.cpp`, H.264 plugin and client, audio, cDNG, MLV, colour; 20 in `ProresColor.cpp`, 4 in `LossyDngEncoder.cpp`, essays in `ProresEncoder.*`. "Code upstream wrote itself" is an inference about provenance (**probable**), so the rule is "usually" over the tree. 0 TODO/FIXME/HACK anywhere in the topic |
| I20 | holds (usually) | - |
| I21 | holds (usually) | - |
| I22 | holds (usually) | - |
| I23 | holds | - |
| N1 | holds | - |
| N2 | holds | The lossy disk writer blocks an encode worker, never the callback |
| N3 | weaken to usually | The WebUI operator gets no warning: `grep -n -i dropped WCP` gives 0 |
| N4 | weaken to usually | `LossyDngEncoder.cpp:228-232` disk-write errors only logged |
| N5 | weaken to usually | `setTimecodeMode` is not gated (`CC:8176-8182`), and the timecode mode feeds the per-frame DNG metadata (`CC:3150` `out.timecodeMode = settings.timecodeMode;`). That a mid-take change reaches the open clip is **probable** (depends on which settings copy `CC:6918` passes) |
| N6 | weaken to usually | Fallback black level per sensor family (`CC:2933-2940`) is a guessed value written into the file |
| N7 | weaken to usually | Sensor modes and fps caps are hard-coded tables (S11) |
| N8 | holds (usually) | - |
| N9 | holds | - |
| N10 | holds | - |
| N11 | holds | `/home/pi/.apertar-tuning` is a hidden bench file, not an operator file |
| N12 | holds | The V4L2 write is not fork-specific |
| N13 | holds | - |
| N14 | holds | - |
| N15 | holds | - |
| N16 | holds (once) | - |

### Missed rules

| Id | Kind | Rule | Strength | Evidence |
| --- | --- | --- | --- | --- |
| S25 | structure | `CameraController` reaches the rest of Core only through the callbacks given to its constructor, which carry flat JSON event strings. It includes no App, socket, WebUI or hardware-input header and calls nothing outside itself | usually. Search: includes `CC:1-24` | `CC.hpp:19-21` `using EventCallback = std::function<void(const std::string &)>;` + preview + audio-level callbacks; `CC.hpp:31` constructor; `CC:7581-7596`, `CC:7687-7688` events. Exceptions: `hardware/Mpu6050RecordingSession.hpp` (gyro sidecar, `CC:17`), `ipc/ControlProtocol.hpp` for `escapeJson` only (`CC:18`, `CC:8794`) |
| I24 | idiom | Every public `CameraController` method takes `std::lock_guard<std::mutex> lock(mutex_);` first. Private helpers that expect the lock end in `Locked`. Events leave while the lock is held | usually. 63 `lock_guard<std::mutex> lock(mutex_)` in `CC`; scan of methods after `CC:7577` | `CC:8178`, `CC:8228`; `CC:8773` `setErrorLocked`, `CC:8779` `emitSettingsEventLocked`. Exceptions: `startRecording` checks `timelapseActive()` before locking (`CC:8222-8228`); `stop()` calls `stopTimelapse()` first (`CC:7653`) |
| I25 | idiom | A text file Core persists is written with `settingsFile::atomicWrite` (temp file, fsync, rename, directory fsync), not by truncating in place | usually | `SettingsFile.hpp:37-56`; users `CC:789`, `App:1934`, `App:6509`, `App:6740`, `ProresIspProfile.cpp:233`. Exception: `App:1561-1566` `writeTextFileRaw` truncates with `std::ofstream` |
| N17 | intent | Recording, timelapse, a pending still write and standby exclude each other. Each entry point refuses the others with a sentence that tells the operator what to do first ("Stop ... before ...", "Wait for ... to finish before ...", "Wake the camera before ...") | always. Search: `grep -n 'setErrorLocked("Stop\|before\|Camera is not ready' CC` (18 hits, all this shape) | `CC:8224` "Stop timelapse before recording.", `CC:8244`, `CC:8329`, `CC:7680`, `CC:8048`, `CC:8056`, `CC:8608`, `CC:8612`, `CC:8669`, `CC:8677` |

---

## Final rules

Corrected list after the challenge. Refs `@upstream-1.6.0`. Short names as in the header table.

| Id | Kind | Rule | Strength | Evidence | A violation looks like |
| --- | --- | --- | --- | --- | --- |
| S1 | structure | libcamera is used only in `CC`; no header includes a libcamera header | always | `CC:69-79`; `CC.hpp:3-13`, `CC.hpp:90` | A new `.cpp`/`.hpp` that includes `<libcamera/...>` |
| S2 | structure | No class hierarchy: no `virtual`, `override`, base class or interface for sensors, recorders, encoders. Dispatch is an `if`/`switch` on the format | always | `CC:7507-7511`; `CC:5589-5647`; `CC:5895-5897` | `class ISensor { virtual ... }`, a recorder base class, a factory |
| S3 | structure | New camera behaviour goes into `CC`: a free helper in the anonymous namespace plus a `CameraSession` member; only a file format or a new library gets its own directory | usually | `CC:1797-1880`, `CC:793-883`, `CC:8302-8500`; exceptions `src/prores`, `src/cdng`, `src/mlv` | A new `src/camera/Foo.cpp` for logic that needs no new library |
| S4 | structure | Pure logic is a small header-only file named after the concept, `inline` free functions in `namespace apertar` | usually | `StillBracketing.hpp:8-19`, `ScalerCropGeometry.hpp:16-64`, `RecordingClock.hpp:13-61` | A class with state for pure maths; a `utils.cpp` grab bag |
| S5 | structure | A type goes in `include/apertar/core/` only if it crosses the App/CC or plugin boundary | always | 4 files; `Types.hpp`, `RecordingCapabilities.hpp`, `ProresColorProfile.hpp`, `PreviewExposureReference.hpp` | Internal recorder types in `include/` |
| S6 | structure | `src/util/` is small: clip-scoped latches and the atomic settings-file writer. Small string helpers are usually copied per `.cpp`; a shared one exists only where two areas already share it (`escapeJson`, `atomicWrite`) | usually | `RecordingFailure.hpp`, `RecordingDropWarning.hpp`, `SettingsFile.hpp:25-56`; copies `writeAll` `MlvEncoder.cpp:61`, `CdngEncoder.cpp:462`, `CC:4657`; `escapeJson` `CC:95` and `ControlProtocol.cpp:235`, shared use `CC:8794` | A new `src/util/StringUtils.hpp` or a refactor that merges the copies unasked |
| S7 | structure | The camera's public surface is `bool` setters on `CameraController`, one per socket command, plus `lastError()` | always | `CC.hpp:39-64`, `CC.hpp:85`; `App:9242-9249` | A setter returning an error code or struct, or App poking session state |
| S8 | structure | Every setter commits through `applySettingsLocked(next, reconfigure)` (apply, read back, persist, clear error, emit `settings`) | usually | `CC:8659-8723`, 27 call sites; exception `setTuningFile` `CC:8044-8112` | A setter that writes `settings_` and calls the session directly |
| S9 | structure | A change is applied either as controls for the next request (`false`) or by full reconfigure (`true`) | always | `CC:5495-5524`, `CC:6503-6509`; `CC:5481-5493` | A third apply path (direct V4L2 control write, partial restart) |
| S10 | structure | `controlsForSettings` is the one function that turns settings into libcamera controls | usually | `CC:2005-2144`; callers `CC:5511`, `CC:6345`, `CC:6519`; exception bracket shots `CC:6522-6526` | Controls set in several places from settings |
| S11 | structure | Sensors are told apart by the private `SensorFamily` enum, detected by substring of the camera id; sensor knowledge in `CC` is `switch (sensorFamily)` in free functions | usually | `CC:1882-1888`, `CC:2151-2167`, `CC:5375`; exceptions `ColorProfileConfig.cpp:242-243`, `DefaultTuningSelection.hpp:130-181` (by model name) | A sensor table file, a sensor class, sensor ids compared outside these functions |
| S12 | structure | Sensor tables are not shared between layers; each layer keeps its own copy and matches the `"sensor"` name Core publishes | always | `CC:355-532`, `App:1076-1260`, `WCP:4824-5028`, `CameraPage.qml:377-490` | A new shared sensor-capability API replacing the copies unasked, or a new sensor added to only one layer |
| S13 | structure | Record formats are one flat enum; a sub-option is its own enum + field + setter + command | always | `Types:45-68`, `Types:144-153`, `CC.hpp:50-58`, `App:9326-9386` | A format "object" or a generic `set_format_option` command |
| S14 | structure | Board capability is decided in `RecordingCapabilities.hpp` from the device tree and enforced at setter, sanitise and record start | always | `Caps:18-35`, `Caps:64-106`; `CC:7923`, `CC:8672`, `CC:2709` | Pi-model checks inline in setters or in a config file |
| S15 | structure | Sanitise order: board, absolute ranges, sensor | always | `CC:2707-2744`, `CC:534-601`, `Caps:79-106` | A new clamp applied before the board step or outside the chain |
| S16 | structure | A recorder is a self-contained class: `start...(folder, settings, ..., std::string *error)`, `enqueue...() -> bool`, `stop()`, `active()`, `error()`, destructor calls `stop()` | usually | `CC:3268`, `CC:3953`, `ProresRecorder.hpp:20-24`, `AudioRecordingSession.hpp:27-36`; exception `PhotoCaptureWriter` `CC:5055-5058` | A recorder with callbacks into the session, or no `error()` |
| S17 | structure | Clip folders are allocated once for every format by `DngRecordingQueue::reserveClipFolder`, prefix by `switch` | once | `CC:5548`, `CC:3646-3675` | A second folder allocator for a new format |
| S18 | structure | Anything linking libav is a `MODULE` plugin loaded by `dlopen` at first use with an ABI check; ALSA is dlopened too | always | `CMakeLists.txt:143-169`, `ProresRecorder.cpp:25-50`, `LibavH264EncoderClient.cpp:97-131`, `TimestampedAudioCapture.cpp:41-49` | Core linking libav or another heavy library directly |
| S19 | structure | Per-take inputs that are not camera settings travel as option structs built by `App` | always | `Types:184-201`, `App:10624-10709`, `CC.hpp:77-78` | Audio/gyro/take options added to `CaptureSettings` |
| S20 | structure | Camera settings persist only in `camera_settings.conf`, written only by Core, with `profile.<name>.` copies | always | `CC:342-353`, `CC:616-788`; no other writer (grep) | Camera settings in `UI.conf` or `apertar-hardware.conf` |
| S21 | structure | A runtime capability is a non-persisted `CaptureSettings` field with a trailing comment, filled before settings leave Core | always | `Types:132`, `:134`, `:139`, `:142`, `:150`; `CC:8570-8572`, `CC:8779-8781` | A separate capabilities command, or a capability saved to disk |
| S22 | structure | The camera side never reads `apertar-hardware.conf` | always | grep over topic dirs gives 0 | A recorder knob in a hardware-conf section |
| S23 | structure | Few dependencies; file formats are written by hand | usually | `CMakeLists.txt:25-45`; `IfdBuilder.hpp`, `MlvEncoder.cpp`, `CC:1797-1880`; exceptions JPEG, libav | A new library for a container or still format |
| S24 | structure | No tests, `third_party/`, formatter config or contributor docs in Core | always | `git ls-files` = 137 | (Adding them is new ground, not a mismatch; say so) |
| S25 | structure | `CameraController` talks to the rest of Core only through constructor callbacks carrying flat JSON strings | usually | `CC.hpp:19-31`, `CC:7581-7596`, `CC:7687-7688`; exceptions `CC:17` gyro sidecar, `CC:18` `escapeJson` | CC including `ApertarCoreApp`, WebUI, socket or hardware-input headers; a typed observer interface |
| I1 | idiom | Setter shape: lock, gate with `setErrorLocked("..."); return false;`, range check, no-op path clears error and emits, else copy and `applySettingsLocked` | usually | `CC:7774-7786`, `CC:7711-7739`; exceptions `CC:8025`, `CC:8038` | A setter that throws, or returns without a message |
| I2 | idiom | Out-of-absolute-range values are rejected with a sentence; sensor/board/format limits are applied silently and the effective value is returned | always | `CC:7777-7780`; `CC:2740-2741`; `CC:8713-8715` | Rejecting a value that is merely above the mode's fps cap |
| I3 | idiom | A function that can fail returns `bool` and takes `std::string *error` last, filled by a local `setError` | always | `CC:5254`, `CC:3953-3958`, `LibavH264EncoderClient.hpp:19-21`, `CC:5919-5923` | `std::expected`, error enums, exceptions across the class |
| I4 | idiom | Encoders throw; the worker loop or the public boundary catches and latches; plugins return `int` + `char *error` | always | `CdngEncoder.cpp`, `CC:3747-3752`, `CC:8682-8687`, `ProresPluginApi.hpp:22-25` | An exception escaping a `CameraController` method |
| I5 | idiom | Operator-facing setter errors are full English sentences with a period and a next step; deeper encoder errors may be terse "Area: fragment" | usually | `CC:7715`, `CC:7745`, `Caps:70`; exceptions `ProresEncoder.cpp:744`, `:1435`, `CC:5282`, `CC:4774` | A setter error like `"ERR_FPS"` or `"invalid fps"` |
| I6 | idiom | Logging is `std::cerr << "ApertarCore <area>: key=value ..."`; no levels, no logging helper | usually | `CC:3353`, `CC:6264`, `ProresRecorder.cpp:90`; exception `LibavH264EncoderPlugin.cpp:245` `fprintf(stderr, "ApertarCore ...")` | A logger class, log levels, `spdlog`, lines without the `ApertarCore` prefix |
| I7 | idiom | Log take start (all knobs), take stop (stats), drops, write failures, configure, tuning chosen, fallbacks; never setter calls, control changes or normal frames | always | `CC:3353-3374`, `CC:3416-3423`, `CC:6264-6293`; none in `CC:7609-8489` | Per-frame or per-setter log lines |
| I8 | idiom | Repeated warnings are rate-limited by `n == 1 \|\| n % N == 0` (N usually 30); one-offs by a `bool warned..._` | usually | `CC:3538`, `CC:4275`, `ProresRecorder.cpp:100`, `CC:6858-6861`; exceptions `CC:5062` (10), `CC:7216` | Time-based throttling helpers, or unthrottled per-frame warnings |
| I9 | idiom | Bench tuning is an env var `APERTAR_<AREA>_<KNOB>` read where used, with default and bounds; bad values usually fall back silently | usually | `CC:1027-1061`, `CC:3329-3330`, `CdngEncoder.cpp:51-65`; exceptions `CC:3981-3985`, `CC:2789-2792`, `LossyDngEncoder.cpp:325-328` | A tuning config file or socket command for an internal knob |
| I10 | idiom | Names: members `_`, constants `k`Pascal, camelCase functions, `Locked` suffix, unit suffixes, `is/has/uses/needs` predicates, `...ForSensor` | usually | `CC.hpp:92-132`, `CC:1019-1025`, `Types:129`, `Types:140`; exceptions `CC:1995`, `ProresEncoder.cpp:423-433` | `m_member`, `snake_case` functions, unitless time fields |
| I11 | idiom | Wire names are snake_case; `toString` at the foot of the enum's header; reverse parser in the `.cpp`, lowercases by hand, unknown maps to default | usually | `Types:254-285`, `CC:199-219`, `CC:290-340`; exceptions `ProresColorProfile.hpp:20-28`, `App:824-844` | camelCase JSON keys; a generic enum-reflection helper |
| I12 | idiom | JSON is built by hand; events are `{"event":"name",...}`; structured values get a `...Json()` helper | always | `CC:139-185`, `Caps:52-62`, `ExposureMetering.hpp:28-39` | A JSON library, nested objects in events |
| I13 | idiom | The settings field list exists three times and is edited in all three | always | `CC:136-187`, `App:167-216`, `App:7835-7884` | A new field in one list only, or a unification refactor unasked |
| I14 | idiom | Defaults are `CaptureSettings` member initialisers; code uses `CaptureSettings{}.field` | always | `Types:124-161`, `CC:555-584` | A second defaults table |
| I15 | idiom | Loading settings is one `else if (key == ...)` chain in `try/catch(...)`; malformed keeps default; retired keys still read | always | `CC:650-723`, `CC:681-682` | Strict parsing that fails start on a bad line |
| I16 | idiom | Worker threads are `std::thread` members with one `std::mutex`, condition variable(s), `std::deque` job queue(s) and a stop flag; counters `std::atomic<uint64_t>` reset in start, printed in stop | usually | `CC:3922-3927`, `CC:5213-5218`, `ProresRecorder.hpp:41-45`; exceptions `CC:4990-4994`, `CC:875-876`, `ProresEncoder.cpp:423-433`, `ProresColor.cpp:290-296` | A thread-pool library, `std::async`, lock-free queues |
| I17 | idiom | Process-wide one-off values are function-local statics | always | `CC:885-889`, `Caps:37-50`, `CC:2990-2994`, `DefaultTuningSelection.hpp:45-49` | Global singletons with init functions |
| I18 | idiom | Build options are `#if APERTARCORE_HAS_X` with an `#else` that keeps the signature and returns neutral; Core builds without libcamera | always | `CC:5393-5397`, `CC:1708-1795`; guard counts above | Code that only compiles with libcamera or libav |
| I19 | idiom | Comments are rare one-to-three-line "why" notes; no Doxygen, TODO, ticket numbers, author or date; imported QRAW code keeps block essays | usually | `CC:6927-6928`, `CC:8248-8250`; exceptions `ProresEncoder.hpp:3-42`, `ProresColor.cpp` (20 blocks), `LossyDngEncoder.cpp:322-324` | Doxygen headers, `// T33:` or `WP-585-9` tags, `TODO` |
| I20 | idiom | 4 spaces, function braces on own line, `static_cast`, `std::lock_guard<std::mutex>`; long lines; no formatter | usually | counts in `CC`; denser second style `ProresRecorder.cpp:15` | A reformat of untouched lines |
| I21 | idiom | Include order: own header, project headers by path from `src`, std, system | usually | `CC:1-90`, `MlvEncoder.cpp:1-18`; exception `ProresRecorder.cpp:1-11` | Relative `../` includes |
| I22 | idiom | Everything in `namespace apertar`; file-local in an anonymous namespace; at most one nested helper namespace | usually | `DefaultTuningSelection.hpp:14`, `SettingsFile.hpp:17` | New top-level namespaces |
| I23 | idiom | A plugin exports `apertar_<plugin>_{abi,create,encode,finish,destroy}` with a POD config in `...PluginApi.hpp`; path = env, next to exe, `/home/pi/ApertarCore-build/` | always | `ProresPlugin.cpp:13-56`, `LibavH264EncoderPlugin.cpp:464-522` | C++ classes across the plugin boundary |
| I24 | idiom | Every public `CameraController` method locks `mutex_` first; helpers that need the lock end in `Locked`; events go out under the lock | usually | 63 lock lines; `CC:8773-8779`; exceptions `CC:8222-8228`, `CC:7653` | A second mutex for settings, or an unlocked public method |
| I25 | idiom | Persisted text files are written with `settingsFile::atomicWrite` | usually | `SettingsFile.hpp:37-56`; `CC:789`, `App:1934`, `ProresIspProfile.cpp:233`; exception `App:1561-1566` | `std::ofstream(path, trunc)` on a settings file |
| N1 | intent | Core is the source of truth; every client uses the same setter and busy checks and gets the effective value back | always | `README.md:271`; `CC:8713-8715`; `App:9246-9248` | UI-side state that Core does not know |
| N2 | intent | The camera callback never waits for storage or an encoder; queues are bounded; a full queue drops before copying | always | `CC:6927-6930`; `CC:3328-3330`, `CC:4465-4474`, `ProresRecorder.cpp:64-65` | Blocking `push` or unbounded queue in the frame path |
| N3 | intent | Dropped frames are reported once per clip, not hidden, and do not stop the take | usually | `README.md:299`; `RecordingDropWarning.hpp:9`; `CC:7580-7584`; exception: WebUI shows nothing | A per-frame drop counter in the UI, or stopping the take on drop |
| N4 | intent | A write/encode failure stops the take within about a second with the first error; a failed start leaves the camera ready | usually | `RecordingFailure.hpp:7-16`, `CC:8519-8534`, `CC:8248-8253`; exception `LossyDngEncoder.cpp:228-232` | Errors only logged; a failed start that needs a restart |
| N5 | intent | During a take only exposure, white balance and focus change; stream, file, fps and colour-pipeline changes are refused with a sentence | usually | `CC:7714`, `CC:7744`, `CC:7927`, `CC:8051`; exception `setTimecodeMode` `CC:8176-8182` | A new stream/file setting not gated on `recording_` |
| N6 | intent | Metadata is measured, not guessed; a RAW frame without measured WB is not written | usually | `CC:6857-6863`, `CC:3182-3202`, `README.md:147`; exception `CC:2933-2940` | Hard-coded gains or WB written into DNGs |
| N7 | intent | Capabilities are detected at run time (device tree, control map, tuning, CFA) | usually | `Caps:37-50`, `CC:5812-5835`, `CC:5306-5321`; exception sensor tables | A config switch telling Core which board or features it has |
| N8 | intent | No silent downgrade of what is recorded; the operator gets a sentence naming the hardware | usually | `Caps:64-77`, `CC:5535-5537`; exceptions `CC:7599-7601`, `CC:4064-4068`, `CC:5563-5567` | Quietly recording another format or size |
| N9 | intent | A failed mode change restores the previous mode; only then `Error` | always | `CC:8692-8709`, `CC:8087-8105`, `CC:8642-8656` | Reconfigure failure that leaves the camera stopped |
| N10 | intent | Media is never overwritten; stills are durable before announced; clip frames are not synced | always | `CC:3667-3673`, `AtomicStillFile.hpp:31-32`, `:85-88`, `CC:4005-4006` | Fixed clip names, `fsync` per video frame |
| N11 | intent | Internal tuning stays out of operator-edited files and the README | always | section 5.11; `CC:745-777`; `LossyDngEncoder.cpp:322-324` | Bench knobs in `camera_settings.conf`, `apertar-hardware.conf` or settings UI |
| N12 | intent | The same source builds against different libcamera forks, without libcamera, without libav; only mainline controls | always | `CC:3084-3086`, `CC:2952-2954`, `CC:1947`; `CMakeLists.txt:133-173` | `controls::rpi::` or fork-only controls without a guard |
| N13 | intent | Monitoring looks are never baked into RAW | always | `README.md:58`, `CC:1113`, `CC:3213-3224`, `ProresIspProfile.hpp:7` | Preview LUT/profile applied to DNG data or matrix |
| N14 | intent | Each record format and still mode remembers its own settings; tuning, timecode, metering stay global | always | `CC:7939-7955`, `CC:8725-8749` | A new global setting not carried over at `CC:7945-7951`, or one profile for all formats |
| N15 | intent | Pending stills are protected like a take (no mode change, standby or new capture until written) | always | `CC:8666-8671`, `CC:7677-7682`, `CC:8243-8246` | A mode switch that discards a pending photo |
| N16 | intent | The RAW capture model is one YUV monitoring stream plus one RAW stream; only H.264/ProRes change the stream set | once | `CC:6031-6037` | A third stream added for RAW formats |
| N17 | intent | Recording, timelapse, pending still writes and standby exclude each other; each entry refuses with "Stop/Wait/Wake ... before ..." | always | `CC:8224`, `CC:8244`, `CC:8329`, `CC:7680`, `CC:8048`, `CC:8608`, `CC:8677` | A new capture mode that starts while another runs, or refuses without telling what to do |

Recipes R1-R5 in section 6 stand unchanged. Add to R3 and R4: a new mode or capture action must add the mutual-exclusion refusals of N17 at its entry point and in `startRecording` (`CC:8221-8246`) and `startTimelapse` (`CC:8304-8330`).
