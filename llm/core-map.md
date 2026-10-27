# Apertar-Core chapter map

LLM navigation map for the three giant files plus the small dirs. Prose about *how* things work lives in the KB: [architecture/core.md](../architecture/core.md) (process, IPC, events, recording), [config.md](../architecture/config.md) (config keys, template drift), [build.md](../architecture/build.md). This file only says **where**.

- Refs: `upstream-1.6.0` (fork HEAD `ed400ba`, build-only commits on top; `src/` and `include/` identical to the tag). Every line number below came from `grep -n` on that tree, 2026-10-25.
- Paths are repo-relative to `Apertar-Core/`. `App` = `src/ApertarCoreApp.cpp`, `CC` = `src/camera/CameraController.cpp`, `WCP` = `src/web/WebControlPage.cpp`.
- **Use the grep anchor, not the line number**, once anything has been edited. Each anchor is a literal string that occurs exactly once in its file (checked with `grep -cF`).
- How to use: `grep -nF '<anchor>' <file>` → `Read` with `offset`/`limit` over the chapter range.

---

## 1. Chapter maps

### 1.1 `src/ApertarCoreApp.cpp` (11025 lines)

Shape: lines 57–6779 are one anonymous namespace of free helpers (no class state). Lines 6781–11024 are `ApertarCoreApp::` members. `handleCommand` alone is 9091–10821 (1730 lines; sub-chapters below).

| Lines | Chapter | Key functions / types | Grep anchor |
| --- | --- | --- | --- |
| 1–65 | Includes, `#if APERTARCORE_HAS_TURBOJPEG`, WebUI preview constants (640x360, 30 fps, q75), 256 KiB config limit | `kWebPreviewMaxWidth`, `kMaxEditableHardwareConfigBytes` | `constexpr size_t kMaxEditableHardwareConfigBytes` |
| 66–129 | Executable lookup; socket reply builders | `resolveExecutablePath`, `existingExecutablePath`, `okReply`, `errorReply` | `std::string okReply(int id` |
| 130–166 | IMU status reply body (`"imu":{...}`) | `imuStatusBody` | `std::string imuStatusBody(bool includeLiveSample)` |
| 167–217 | **settingsBody** — camera-settings JSON fragment used by every camera `set_*` reply and `get_state` | `settingsBody` | `std::string settingsBody(const CaptureSettings &settings)` |
| 218–278 | Preview dmabuf descriptor dup/close | `closeOwnedPreviewFrame`, `duplicatePreviewFrameDescriptor` | `PreviewFrameDescriptor duplicatePreviewFrameDescriptor(` |
| 279–359 | JSON number/array utils, string trim/lower, UI.conf path, UI bool parse | `jsonNumber`, `trimAscii`, `lowerAscii`, `sharedUiSettingsPath`, `parseUiSettingsBool` | `std::filesystem::path sharedUiSettingsPath()` |
| 360–546 | UI value normalisers I: orientation, timecode, controls mode, AF enums, photo timer/burst/format/timelapse | `normalizeTimecodeModeValue`, `autofocusModeFromCommandValue`, `normalizePhotoFormatValue`, `photoCaptureFormatFromValue` | `std::string normalizePhotoTimelapseValue(` |
| 547–646 | Battery type/capacity/voltage defaults; sleep mode | `normalizeBatteryTypeValue`, `batteryCapacityFitsType`, `normalizeSleepModeValue` | `bool batteryCapacityFitsType(` |
| 647–726 | UI value normalisers II: peaking colour, anamorphic, guides, centre marker, ext. monitor, false colour | `normalizeGuidesTypeValue`, `normalizeFalseColorModeLabel`, `falseColorModeValueFromLabel` | `int falseColorModeValueFromLabel(` |
| 727–823 | **Favourites candidate list** + list encode/decode | `favoriteCandidateOrder`, `normalizeFavoritesOrderList`, `splitSimpleListValue` | `const std::vector<std::string> &favoriteCandidateOrder()` |
| 824–937 | Recording format / lossy ratio / bit depth parsing; generic `parseDoubleValue`/`parseIntegerValue` | `normalizeRecordingFormatValue`, `recordingFormatFromNormalizedValue`, `lossyDngRatioFromString`, `parseRawBitDepthValue` | `std::string normalizeRecordingFormatValue(` |
| 938–1029 | Preset value formatting (shutter angle/speed snap, fps/ISO/WB/res labels) | `snapToNearestPreset`, `formatPresetShutterAngle` | `std::string formatPresetShutterAngle(` |
| 1030–1322 | Hardware step-action option tables: fps caps per sensor, resolutions per sensor, ISO, shutter, WB | `pcfSettingStepMode`, `maximumPcfFpsForSettings`, `availablePcfResolutionOptions`, `pcfIsoOptions`, `pcfWhiteBalanceOptions` | `double maximumPcfFpsForSettings(` |
| 1323–1425 | Parse numeric suffixes of hardware actions (`iso200`, `wb5000`, `shutter1/48`) | `hardwareActionSuffix`, `parseHardwareActionNumber`, `parseHardwareActionShutterSeconds` | `std::optional<std::string> hardwareActionSuffix(` |
| 1426–1481 | UTC timestamp; Sound Recorder folder `Audio/Audio_yy-mm-dd_C####` | `currentUtcIsoTimestamp`, `allocateSoundRecordingFolder` | `std::filesystem::path allocateSoundRecordingFolder(` |
| 1482–1580 | Shell exec + capture; standby helpers (fixed argv); raw text file IO | `runShellCommandCapture`, `standbyUsbPower`, `standbyLowPower`, `writeTextFileRaw` | `ShellCommandResult standbyLowPower(const char *action)` |
| 1581–1936 | **UI.conf read/write** — snapshot struct with defaults, parser, raw map, atomic `[General]` updater | `SharedUiSettingsSnapshot`, `readSharedUiSettings`, `readSharedUiGeneralSettingsMap`, `updateSharedUiGeneralSettings` | `SharedUiSettingsSnapshot readSharedUiSettings()` |
| 1937–2084 | Mount table, volume labels, media-type labels | `isMountedPath`, `mountedDeviceForPath`, `volumeLabelForDevicePath` | `bool isMountedPath(const std::string &mountPath)` |
| 2085–2188 | Format filesystem names/tools/labels (exfat, vfat, ntfs, ext4) | `normalizedFormatFilesystemType`, `formatFilesystemToolPath` | `std::string normalizedFormatFilesystemType(` |
| 2189–2412 | `lsblk` parse → mountable drive list + JSON | `parseLsblkPairs`, `scanMountableMediaDrives`, `jsonMediaDriveArray` | `std::vector<MediaDriveCandidate> scanMountableMediaDrives(` |
| 2413–2461 | WebUI icon dir lookup, small file reads | `webIconsDirectory`, `readBinaryFileString` | `std::optional<std::filesystem::path> webIconsDirectory()` |
| 2462–2842 | ALSA device detection, selection ids, audio options from UI.conf | `parseAlsaHardwareDeviceList`, `resolveAudioDeviceSelection`, `audioRecordingOptionsFromUiSettings`, `detectAudioDevices` | `AudioDeviceSnapshot detectAudioDevices()` |
| 2843–3041 | Fan block constants; time-zone list; local time; timedatectl; hwclock | `availableTimeZones`, `currentTimeZoneId`, `waitForTimedatectlNetworkSync`, `syncHardwareClockIfAvailable` | `const std::vector<std::string> &availableTimeZones()` |
| 3042–3179 | Fan mode as a managed block in `/boot/firmware/config.txt` | `fanModeBlock`, `stripManagedFanBlock`, `detectManagedFanMode`, `applyFanMode` | `bool applyFanMode(const std::string &mode` |
| 3180–3311 | Reboot/poweroff; set date/time; set time zone | `invokeSystemPowerAction`, `applyDateTimeSettings`, `applyTimeZoneSettings` | `bool invokeSystemPowerAction(` |
| 3312–3379 | NVMe parent drive, PCI address, flush, PCI detach | `pciAddressForDevice`, `detachNvmeController` | `bool detachNvmeController(` |
| 3380–3603 | **Embedded Python CFE re-insert watcher** (raw string `R"PY(` … `)PY"` at 3382–3592) | `startNvmeReinsertWatcherAtPath`; Python `read_insert_state`, `reset_pcie_controller`, `mount_partition` | `static const std::string helperScript = R"PY(` |
| 3604–3868 | Mount / eject / format media | `mountMediaDeviceAtPath`, `ejectMediaAtPath`, `formatMediaAtPath` | `bool formatMediaAtPath(const std::string &mountPath,` |
| 3869–3998 | Speed-test result text; byte/uptime formatting; meminfo; socket send helpers | `writeSpeedResultText`, `formatUptimeHuman`, `sendAllBytes` | `std::string writeSpeedResultText(bool mediaMounted,` |
| 3999–4230 | WebUI preview downscale (NEON) + TurboJPEG encoder | `scaledWebPreviewSize`, `downsampleNearestPlane`, `TurboJpegCompressor`, `encodeYuv420ToJpeg` | `struct TurboJpegCompressor {` |
| 4231–4449 | `apertar-hardware.conf` candidate paths, **Core's config template**, INI int/bool parsers | `hardwareConfigCandidatePaths`, `editableHardwareConfigPath`, `defaultHardwareConfigTemplate`, `parseConfigBool` | `std::string defaultHardwareConfigTemplate()` |
| 4450–4715 | INA219 power monitor (config, registers, battery %) | `loadIna219HardwareConfig`, `readIna219Snapshot`, `readPowerSupplySnapshot` | `PowerSupplySnapshot readIna219Snapshot()` |
| 4716–4836 | CPU temp/ticks; record-time and still-size estimates | `readCpuTemperatureC`, `estimatedRawBytesPerSecond`, `estimatedStillFrameSizeMiB` | `uint64_t estimatedRawBytesPerSecond(` |
| 4837–5014 | Network + device (Pi model, OS, uptime) snapshots | `readNetworkSnapshot`, `readDeviceSnapshot` | `NetworkSnapshot readNetworkSnapshot(uint16_t port)` |
| 5015–5156 | Mini JSON string-field extractor; URL encode/decode; query params | `extractJsonStringField`, `urlDecodeComponent`, `queryParameterValue` | `std::optional<std::string> extractJsonStringField(` |
| 5157–5289 | Preset file names, preset dirs (`~/.config/CinePi/UI/presets` …) | `isSafePresetFileName`, `presetDirectoryCandidates`, `preferredPresetDirectory` | `std::vector<std::filesystem::path> presetDirectoryCandidates()` |
| 5290–5387 | `GET/POST /api/config` backends | `buildHardwareConfigFileJson`, `saveHardwareConfigFile` | `bool saveHardwareConfigFile(` |
| 5388–5468 | Preset discovery (builds `/api/presets/download/<file>` urls at 5447) | `discoverPresetFiles` | `std::vector<PresetFileEntry> discoverPresetFiles()` |
| 5469–5666 | Media selection ids, path safety, LUT dirs + allow-list | `mediaSelectionsFromQuery`, `pathIsInsideRoot`, `discoverLutPreviewFiles`, `lutPreviewFileAllowed` | `bool lutPreviewFileAllowed(` |
| 5667–5953 | Media type labels, durations (frames, WAV), size/mtime stats | `clipContainerTypeLabel`, `wavDurationTextForFile`, `mediaStatsForPath` | `std::string wavDurationTextForFile(` |
| 5954–6281 | Still groups, zip entries, deletion targets, file/zip streaming | `stillGroupFilesForId`, `mediaSelectionDeletionTargets`, `streamFileToClient`, `streamZipArchiveToClient` | `void streamZipArchiveToClient(int clientFd,` |
| 6282–6449 | **Clip library scan** (`Photos/`, `Audio/`, `Timelapse_*`, clip folders) | `discoverMediaLibraryItems` | `std::vector<MediaLibraryItem> discoverMediaLibraryItems(` |
| 6450–6778 | Preset import / **build payload** / save / delete | `importPresetFileToCamera`, `buildCurrentPresetPayload`, `saveCurrentPresetToCamera`, `deletePresetFileFromCamera` | `std::string buildCurrentPresetPayload(` |
| 6781–6942 | Ctor (callback wiring), dtor, `start()`, `stop()` | `ApertarCoreApp::ApertarCoreApp`, `start`, `stop` | `bool ApertarCoreApp::start()` |
| 6943–7020 | Preview frame queue; replay of `preview_buffer` registrations | `enqueuePreviewFrame`, `enqueueCurrentPreviewRegistrations` | `void ApertarCoreApp::enqueueCurrentPreviewRegistrations()` |
| 7021–7054 | 1 s main loop (failure supervisor, idle standby) | `wait` | `void ApertarCoreApp::wait()` |
| 7055–7092 | Socket line → parse → `handleCommand` (+ collected events); web variant | `handleRequest`, `handleWebCommand` | `std::string ApertarCoreApp::handleRequest(` |
| 7093–7650 | **HTTP router** (§2.2) | `handleWebRequest` | `WebServer::Response ApertarCoreApp::handleWebRequest(` |
| 7651–7710 | `/api/presets` and `/api/media` JSON | `buildPresetLibraryJson`, `buildMediaLibraryJson` | `std::string ApertarCoreApp::buildMediaLibraryJson() const` |
| 7711–8047 | **`/api/state` JSON** (own copy of settingsBody fields at 7835+, `"system":{` 7901, `"ui":{` 7965, `"audio":{` 8022, `"device":{` 8029) | `buildWebStateJson` | `std::string ApertarCoreApp::buildWebStateJson() const` |
| 8048–8309 | WebUI MJPEG: registration, frame capture, encoder thread, client stream | `captureWebPreviewFrame`, `runMjpegEncoder`, `streamMjpeg` | `void ApertarCoreApp::runMjpegEncoder()` |
| 8310–8409 | Recording elapsed tracking; Sound Recorder start/stop | `syncRecordingTracking`, `startSoundRecording`, `stopSoundRecording` | `bool ApertarCoreApp::startSoundRecording(` |
| 8410–8607 | Grove analog targets → commands | `normalizeHardwareAnalogTarget`, `dispatchHardwareInputCommand`, `toggleSharedUiBoolAction`, `handleHardwareAnalogInput` | `void ApertarCoreApp::handleHardwareAnalogInput(` |
| 8608–8659 | Power button; multi-action split; standby-only-wakes rule | `handlePowerButtonPress`, `handleHardwareInputAction` | `void ApertarCoreApp::handleHardwareInputAction(` |
| 8660–8956 | **Button action vocabulary → commands** | `handleSingleHardwareInputAction` | `void ApertarCoreApp::handleSingleHardwareInputAction(` |
| 8957–9090 | Media speed test (fio or timed write) | `startMediaSpeedTest`, `runMediaSpeedTest`, `joinMediaSpeedTest` | `void ApertarCoreApp::runMediaSpeedTest(` |
| 9091–10821 | **Command dispatcher** (sub-chapters next table; full list §2.1) | `handleCommand` | `std::string ApertarCoreApp::handleCommand(` |
| 10823–10890 | Event routing (always-broadcast list 10829–10841) + tally/trigger substring matcher | `publishEvent`, `handleTriggerEvent` | `void ApertarCoreApp::handleTriggerEvent(` |
| 10891–11024 | `preview_buffer`/`preview_frame` fan-out; publisher thread; shutdown flag | `publishPreviewFrame`, `runPreviewPublisher`, `requestShutdown` | `void ApertarCoreApp::runPreviewPublisher()` |

`handleCommand` sub-chapters:

| Lines | Block | Grep anchor |
| --- | --- | --- |
| 9091–9117 | Gates: pending writes, media actions while busy, speed test, idle-reset list | `const bool mediaAction = command.name == "format_media"` |
| 9118–9211 | Standby: `user_activity`, timeout, USB power, `enter_standby`, `wake`; Standby capture gate 9208 | `if (command.name == "enter_standby") {` |
| 9212–9241 | `ping`, `help` (static list on one line, 9216), `get_state` | `if (command.name == "get_state") {` |
| 9242–9476 | Camera setters → `CameraController::set*`, reply `settingsBody` | `if (command.name == "set_record_format") {` |
| 9477–9512 | `handleUiToggle` lambda + 10 toggles | `auto handleUiToggle = [this, &command]` |
| 9513–9645 | Sound Recorder, capture mode, photo mode/bracketing/long exposure, 3 more toggles | `if (command.name == "set_capture_mode") {` |
| 9646–9728 | IMU/gyro (writes `apertar-hardware.conf`), 2 audio toggles | `if (command.name == "calibrate_gyro") {` |
| 9729–10030 | UI.conf values: monitoring, still timer/burst/format/timelapse, orientation, opacity | `if (command.name == "set_lut_preview_file") {` |
| 10031–10123 | Audio caps/options/devices/volumes | `if (command.name == "audio_capabilities") {` |
| 10124–10229 | Battery, sleep mode, favourites order | `if (command.name == "set_favorites_order") {` |
| 10230–10528 | `apply_preset` (one reconfigure + UI.conf batch) | `if (command.name == "apply_preset") {` |
| 10529–10622 | Date/time, time zone, fan, format/eject/mount, speed test | `if (command.name == "format_media") {` |
| 10623–10795 | `record_start` (audio prep sleep), `capture_photo`, timelapse, `record_stop` | `if (command.name == "record_start") {` |
| 10796–10821 | `preview_subscribe`, reboot, poweroff, `shutdown`, unknown | `"Unknown command: " + command.name` |

### 1.2 `src/camera/CameraController.cpp` (8834 lines)

Shape: free helpers 93–5228 (anonymous namespace), of which 1017–5226 sit inside `#if APERTARCORE_HAS_LIBCAMERA`. Inner classes: `DngRecordingQueue` 3249–3928, `H264PreviewRecorder` 3930–5016, `PhotoCaptureWriter` 5018–5224, `CameraController::CameraSession` 5230–7575 (the libcamera owner). Public `CameraController::` methods 7577–8834 (mutex + `applySettingsLocked`, delegate to the session).

| Lines | Chapter | Key functions / types | Grep anchor |
| --- | --- | --- | --- |
| 1–91 | Includes, feature `#if`s | — | `#include "camera/CameraController.hpp"` |
| 92–188 | JSON escape; **`settings` event JSON** (3rd copy of settings fields) | `escapeJson`, `settingsEvent` | `std::string settingsEvent(const CaptureSettings &settings)` |
| 189–341 | Shutter-angle preserve; string→enum parsers (format, lossy ratio, timecode, AF); bit-depth + H.264 size rules | `recordingFormatFromString`, `isFixedTenBitRecordingFormat`, `normalizeRawBitDepth`, `isSupportedH264Resolution`, `autofocusModeFromString` | `RecordingFormat recordingFormatFromString(` |
| 342–354 | Persisted settings path `~/.config/apertar-core/camera_settings.conf` | `persistedSettingsPath` | `std::filesystem::path persistedSettingsPath()` |
| 355–533 | Sensor resolution tables (IMX585 aliases/crops, IMX477, IMX294) | `isImx585Raw12CropResolution`, `isImx477Resolution`, `normalizedImx294ResolutionForBitDepth` | `bool isImx585Raw12CropResolution(` |
| 534–602 | Clamp all settings | `clampCaptureSettings` | `CaptureSettings clampCaptureSettings(CaptureSettings settings)` |
| 603–890 | **Settings persistence**: per-format profiles `profile.<still/cdng/mlv/h264/prores>.`, load, write, debounced persister thread | `loadPersistedCaptureSettings`, `writeCaptureSettings`, `CaptureSettingsPersister` | `void writeCaptureSettings(std::ostream &output` |
| 891–1016 | Still and timelapse path allocation (`Photos/Still_…`, `Timelapse_…`) | `allocatePhotoBasePath`, `allocateTimelapseFolder`, `timelapseFrameBasePath` | `std::filesystem::path allocateTimelapseFolder(` |
| 1017–1135 | Preview/H.264/buffer constants; env helpers; tuning-file validate/apply; buffer counts | `kPreviewWidth`, `validateTuningFilePath`, `applyProcessTuningFile`, `proresCameraBufferCount` | `void applyProcessTuningFile(const std::string &path)` |
| 1136–1289 | Photo format predicates; LE/BE, PNG CRC/zlib, TIFF entry writers | `photoFormatIsTimelapseSafe`, `writeBytesAtomically`, `appendPngChunk` | `bool photoFormatIsTimelapseSafe(PhotoCaptureFormat format)` |
| 1290–1507 | RAW unpack: CSI-2 packed, PiSP compressed decode | `decodePispStillBlockTo12`, `unpackRawFrameToBayer` | `bool unpackRawFrameToBayer(const RawFrameView &frame,` |
| 1508–1707 | Bayer → RGB still; 16-bit DNG still prep; JPEG ICC embed | `processRawFrameToRgbStill`, `prepare16BitDngStillFrame` | `bool processRawFrameToRgbStill(` |
| 1708–1889 | JPEG (TurboJPEG / libjpeg / none), PNG, TIFF encoders | `encodeProcessedJpeg`, `encodeProcessedPng`, `encodeProcessedTiff` | `bool encodeProcessedTiff(` |
| 1890–2004 | Processed-video capture sizes; `SensorModeSelection`; AF control values + window | `h264CaptureResolutionForSensor`, `afModeControlValue`, `autofocusWindowRectangle` | `Resolution h264CaptureResolutionForSensor(` |
| 2005–2145 | **libcamera ControlList from settings** | `controlsForSettings` | `libcamera::ControlList controlsForSettings(const CaptureSettings &settings,` |
| 2146–2192 | Sensor family detection by id substring; raw pixel format by depth | `detectSensorFamily`, `sensorFamilyName`, `rawPixelFormatForBitDepth` | `SensorFamily detectSensorFamily(const std::string &cameraId)` |
| 2193–2423 | **Sensor-mode selection** + candidate list + foreign-size mapping | `sensorModeForRequestedResolution`, `sensorModeCandidatesForRequestedResolution`, `normalizedResolutionForSensor` | `std::vector<SensorModeSelection> sensorModeCandidatesForRequestedResolution(` |
| 2424–2492 | 4K / lossless detection and lossless caps | `isLosslessFourKCapture`, `enforceLosslessCaptureLimits` | `void enforceLosslessCaptureLimits(` |
| 2493–2706 | **Max fps tables** (IMX477 RAW/uncompressed, all sensors); raw depth per sensor | `imx477MaximumSupportedFpsForResolution`, `maximumSupportedFpsForResolution`, `supportedRawBitDepthForSensor` | `double maximumSupportedFpsForResolution(` |
| 2707–2850 | Sensor sanitise; H.264 encode bounds; preview size; H.264 env toggles | `sanitizeSettingsForSensor`, `h264EncodeBounds`, `previewSizeForSensorMode`, `h264KeepRawStream` | `CaptureSettings sanitizeSettingsForSensor(` |
| 2851–2968 | Software active-RAW crop math; black levels; frame duration | `shouldUseRequestedActiveRawCrop`, `blackLevelsForSensor`, `normalizeFrameDurationToUs` | `bool shouldUseRequestedActiveRawCrop(` |
| 2969–3023 | Pi serial; camera model/label for metadata | `readPiSerial`, `uniqueCameraModelForSensor` | `std::string uniqueCameraModelForSensor(` |
| 3024–3248 | libcamera format → `RawFrameView`; DNG metadata per request | `formatToRawView`, `pixelPackingName`, `metadataFromRequest` | `CdngEncoder::Metadata metadataFromRequest(` |
| 3249–3928 | **`DngRecordingQueue`** (cDNG / lossy DNG / MLV take): start 3268, folder 3279, stop 3390, enqueue 3572, clip prefix 3633–3676, DNG worker 3697, MLV worker 3805 | `startAtFolder`, `allocateClipFolder`, `dngWorkerLoop`, `mlvWorkerLoop` | `class DngRecordingQueue {` |
| 3930–5016 | **`H264PreviewRecorder`** (H.264 + ProRes front-end): start 3953, env knobs 4308–4480, libav 4513–4575, finalize 4734, copy loop 4832, encoder loop 4902 | `startAtFolder`, `h264EncoderName`, `startLibavEncoder`, `finalizeStop`, `encoderLoop` | `class H264PreviewRecorder {` |
| 5018–5227 | **`PhotoCaptureWriter`** (stills worker, DNG/JPEG/PNG/TIFF) | `enqueue`, `writeDngStill`, `writeProcessedStill`, `workerLoop` | `class PhotoCaptureWriter {` |
| 5230–5417 | `CameraSession` ctor + **`start`** (tuning preselect, camera pick, mono, colour-profile tuning) | `CameraSession::start` | `bool start(const CaptureSettings &settings, std::string *error)` |
| 5418–5525 | Session `stop`, `reconfigure` (full restart), `applyControls` (pending controls) | `stop`, `reconfigure`, `applyControls` | `bool reconfigure(const CaptureSettings &settings, std::string *error, bool forPhoto = false)` |
| 5526–5684 | Session **startRecording** / stopRecording (gyro, audio, writer choice) | `startRecording`, `stopRecording` | `bool startRecording(const std::string &mediaRoot,` |
| 5685–5967 | Session `capturePhoto`; getters (EV/metering availability, mono, still exposure range); sensor timing reset | `capturePhoto`, `exposureMeteringModes`, `resetStoppedSensorTiming` | `void resetStoppedSensorTiming()` |
| 5968–6376 | **`configureAndStart`** — stream roles, sensor-mode × config search, validate/configure, buffers, start | `configureAndStart` | `bool configureAndStart(const CaptureSettings &settings, std::string *error)` |
| 6377–6496 | Cached DMA buffers (ProRes / RAW); `makeRequests` | `allocateCachedBuffers`, `syncCpuReadBuffer`, `makeRequests` | `bool makeRequests(std::string *error)` |
| 6497–6578 | Requeue with pending controls | `requeueRequest` | `void requeueRequest(libcamera::Request *request)` |
| 6579–6670 | **libcamera callback**: metadata → still → preview → record → requeue | `requestComplete` | `void requestComplete(libcamera::Request *request)` |
| 6671–6852 | Private structs; map/unmap raw + preview planes; sensor→wall clock | `MappedPlane`, `PendingPhotoCapture`, `mapRawBuffers`, `mapPreviewBuffers` | `bool mapPreviewBuffers(std::string *error)` |
| 6853–6957 | RAW frame → `DngRecordingQueue` | `recordRawFrame` | `void recordRawFrame(libcamera::Request *request` |
| 6958–7180 | Still capture from a request (brackets, long exposure) | `capturePhotoFrame` | `void capturePhotoFrame(libcamera::Request *request` |
| 7181–7227 | Recording cadence / drop detection | `trackRecordingCadence` | `void trackRecordingCadence(int64_t timestampUs` |
| 7228–7374 | **Preview publish** (dmabuf registration + frame) | `publishPreviewFrame` | `void publishPreviewFrame(libcamera::Request *request)` |
| 7375–7576 | YUV/RGB48 → H.264/ProRes recorder; media-write and still-exposure events | `recordProcessedPreviewFrame`, `emitMediaWriteState`, `emitStillExposureEvent` | `bool recordProcessedPreviewFrame(libcamera::Request *request)` |
| 7577–7710 | Public ctor (loads persisted settings), start/stop, standby enter/wake | `CameraController::CameraController`, `enterStandby`, `wakeFromStandby` | `CameraController::CameraController(EventCallback eventCallback` |
| 7711–8218 | **Public setters** (one per socket camera command) | `setResolution` … `setAutofocusWindow` | `bool CameraController::setRecordingFormat(RecordingFormat format)` |
| 8219–8301 | Public record start / photo capture queue | `startRecording`, `capturePhoto`, `queuePhotoCaptureLocked` | `bool CameraController::queuePhotoCaptureLocked(` |
| 8302–8501 | Timelapse thread + progress | `startTimelapse`, `stopTimelapse`, `timelapseLoop`, `emitTimelapseProgressLocked` | `void CameraController::timelapseLoop()` |
| 8502–8603 | Stop, failure supervisor, getters | `stopRecording`, `checkRecordingFailure`, `mediaWriteStatus`, `settings` | `bool CameraController::checkRecordingFailure()` |
| 8604–8776 | **Preset apply + the one settings commit path** (reconfigure vs control-only), persist, geometry restore | `applyCapturePreset`, `applySettingsLocked`, `persistSettingsLocked`, `restoreModeGeometryLocked` | `bool CameraController::applySettingsLocked(` |
| 8777–8834 | Event emitters: settings, recording, timelapse, timelapse_frame | `emitSettingsEventLocked`, `emitRecordingEventLocked`, `emitTimelapseEvent` | `void CameraController::emitRecordingEventLocked()` |

### 1.3 `src/web/WebControlPage.cpp` (11618 lines)

Shape: one C++ function `webControlPageHtml()` returning raw string `R"APERTAR(` … `)APERTAR"` (lines 7–11614). Inside: `<style>` 15–2420, HTML body 2422–4037, `<script>` 4038–11611. No CSS comments and no JS section comments exist: anchors are selectors, element ids and function names. JS is flat (all functions at 4-space indent, no modules).

**CSS (15–2420)**

| Lines | Chapter | Selectors | Grep anchor |
| --- | --- | --- | --- |
| 15–53 | Design tokens | `:root` | `    :root {` |
| 54–89 | Base element styles, settings-open scroll lock | `body`, `button`, `input`, `.page` | `    body.settings-open,` |
| 90–231 | Top bar: brand, status pills, date/time, icon buttons | `.topbar`, `.brand*`, `.status-pill`, `.icon-button` | `    .brand-icon {` |
| 232–258 | Grid and cards | `.main-grid`, `.column`, `.card` | `    .column {` |
| 259–505 | Preview stage: stream, WebGL canvas, grid, SMPTE, false-colour legend, badges, footer | `.preview-stage`, `.preview-processed`, `.false-color*`, `.smpte-row` | `    .smpte-row {` |
| 506–664 | Timecode card + record button | `.time-card`, `.timecode-value`, `.record-button`, `.record-icon` | `    .timecode-value {` |
| 665–816 | Section heads, select blocks, pills, sliders | `.section-head`, `.select-block`, `.pill-grid`, `.pill-button`, `.slider` | `    .pill-grid {` |
| 817–953 | System card telemetry + capture list | `.telemetry-*`, `.progress-*`, `.capture-*` | `    .system-head {` |
| 954–1121 | Settings overlay: shell, sidebar nav, panels | `.settings-overlay`, `.settings-nav*`, `.settings-panel` | `    .settings-overlay {` |
| 1122–1432 | Clip browser overlay | `.media-browser*`, `.media-filter`, `.media-row`, `.media-stat` | `    .media-browser-title-row {` |
| 1433–1712 | Settings cards, fields, selects, config editor, buttons | `.settings-card`, `.settings-field`, `.config-editor`, `.primary-button`, `.danger-button` | `    .config-editor {` |
| 1713–1880 | IMU live visual, readout, sync stepper | `.imu-live-card`, `.imu-axis-visual`, `.imu-readout`, `.imu-stepper` | `    .imu-live-card {` |
| 1881–1947 | Preset library rows | `.preset-*` | `    .preset-list {` |
| 1948–2033 | Favourites, `.hidden`, toast, loading overlay | `.favorite-section`, `.toast`, `.loading-overlay` | `    .loading-overlay {` |
| 2034–2420 | Responsive breakpoints 1120 / 720 / 480 / 560 / 420 px | `@media (max-width: …)` | `    @media (max-width: 1120px) {` |

**HTML (2422–4037)**

| Lines | Panel | Key ids | Grep anchor |
| --- | --- | --- | --- |
| 2422–2455 | Top bar (brand, status, settings / media buttons) | `networkHost` | `<header class="topbar">` |
| 2456–2531 | Preview card (MJPEG img + WebGL canvas, badges, timecode, record) | `previewStream` | `<div class="card preview-card">` |
| 2532–2594 | "Camera settings" card: fps / ISO / shutter / WB / resolution / crop pills | `fpsOptions`, `isoOptions`, `cropRatioBlock` | `id="cropRatioBlock"` |
| 2595–2699 | "System" card (telemetry) | — | `<aside class="column">` |
| 2700–2730 | "Current capture" card | — | `Current capture</h2>` |
| 2731–2795 | Settings overlay + sidebar nav (9 panels) | `settingsOverlay`, `data-panel=` | `<div class="settings-overlay hidden" id="settingsOverlay">` |
| 2796–3074 | Panel **record**: still mode, sound recorder, format/compression/colour, bit depth, EV, gyro, timecode, AF | `settingsRecordFormatOptions`, `settingsCdngCompressionSelect`, `settingsProresColorSelect` | `<section class="settings-panel" data-panel="record">` |
| 3075–3120 | Panel **favorites** | — | `<section class="settings-panel active" data-panel="favorites">` |
| 3121–3358 | Panel **monitoring**: live preview, external monitor, assist tools, framing aids | `settingsFocusPeakingOptions`, `settingsGuidesTypeSelect` | `<section class="settings-panel" data-panel="monitoring">` |
| 3359–3456 | Panel **audio** | `settingsInputVolumeRange`, `settingsHeadphoneVolumeRange` | `<section class="settings-panel" data-panel="audio">` |
| 3457–3672 | Panel **system**: UI orientation, opacity, date/time, media, format, speed, thermal/fan, power actions | `settingsMediaFormatSelect`, `settingsFanModeSelect` | `<section class="settings-panel" data-panel="system">` |
| 3673–3799 | Panel **power**: battery, custom capacity, auto power off, standby | `settingsBatteryTypeSelect`, `settingsSleepModeSelect` | `<section class="settings-panel" data-panel="power">` |
| 3800–3839 | Panel **presets** | — | `<section class="settings-panel" data-panel="presets">` |
| 3840–3873 | Panel **config** (`apertar-hardware.conf` editor) | — | `<section class="settings-panel" data-panel="config">` |
| 3874–3978 | Panel **info**: camera, SBC, system, drive | — | `<section class="settings-panel" data-panel="info">` |
| 3979–4031 | Clip browser overlay | `mediaBrowserOverlay`, `mediaBrowserList` | `id="mediaBrowserOverlay"` |
| 4032–4037 | Loading overlay, toast | `loadingOverlay`, `toast` | `Connecting to ApertarCore...` |

**JS (4038–11611)**

| Lines | Chapter | Key functions | Grep anchor |
| --- | --- | --- | --- |
| 4038–4127 | **Option constant lists** (fps, ISO, shutter, WB, formats, AF, IMU, still, assist, battery, sleep) + `favoriteCandidateOrder` | `isoOptions`, `recordFormatOptions`, `favoriteCandidateOrder` | `const recordFormatOptions = [` |
| 4128–4203 | Favourite item and settings panel metadata | `favoriteItemMeta`, `settingsPanelMeta` | `const settingsPanelMeta = {` |
| 4204–4267 | Global `state` object | `state` | `    const state = {` |
| 4268–4515 | Generic helpers; IMU labels; IMU arrow canvas | `cloneSnapshot`, `ensureSnapshotShape`, `drawImuAxisVisual` | `function drawImuAxisVisual(` |
| 4516–4659 | Assist value ↔ label conversions; false-colour legend; date pill | `zebraLevelToThreshold`, `falseColorModeToInt`, `formatWebDateTimePill` | `function falseColorModeToInt(` |
| 4660–4809 | Time/timecode/shutter formatting; still timer/burst/timelapse helpers | `formatTimecode`, `shutterAngleToUs`, `safeTimelapseStillFormat` | `function shutterAngleToUs(` |
| 4810–5028 | **Sensor + fps caps mirror** (IMX477 tables, lossless 4K/2K, max fps, fps/ISO option filters) | `imx477MaximumSupportedFps`, `maximumSupportedFpsForSnapshot`, `availableFpsOptionsForSnapshot` | `function maximumSupportedFpsForSnapshot(` |
| 5029–5510 | **Resolution / crop options mirror** per sensor; `set_resolution` payload builder | `sensorResolutionOptions`, `imx585CropRatioOptionsForSnapshot`, `resolutionCommandPayload` | `function resolutionCommandPayload(` |
| 5511–5651 | WB slider; record format label ↔ command value; compression / lossy ratio dispatch | `recordingFormatCommandValue`, `availableRecordFormatOptions`, `dispatchCdngCompressionSelection` | `function recordingFormatCommandValue(` |
| 5652–5837 | Bit depth availability; H.264 resolution/crop | `rawBitDepthAvailableForSensor`, `h264ResolutionCommandPayload` | `function h264ResolutionCommandPayload(` |
| 5838–6106 | Labels (codec, timecode, AF); unit formatters; battery model; audio options | `captureCodecLabel`, `batteryProfilePercent`, `currentAudioOptions` | `function batteryProfilePercent(` |
| 6107–6337 | Panel open/close; DOM + select helpers | `setSettingsPanel`, `ensureSelectOptions`, `ensureSelectEntries` | `function ensureSelectEntries(` |
| 6338–6741 | Favourites model + DOM builders | `favoriteItemsFromSnapshot`, `applyFavoritesOrder`, `createFavoriteSelectField` | `function applyFavoritesOrder(` |
| 6742–7314 | **Favourite card controls** (sends ~50 commands) | `renderFavoriteControls`, `dispatchFavoriteCommand` | `function renderFavoriteControls(` |
| 7315–7510 | Favourites panel; preset library list | `renderFavoritesPanel`, `renderPresetLibrary` | `function renderPresetLibrary(` |
| 7511–7794 | Clip browser: filter, sort, selection, render | `sortedMediaItems`, `mediaSelectionQuery`, `renderMediaLibrary` | `function renderMediaLibrary(` |
| 7795–7892 | Metric, toast, preview overlays, processing toggles | `showToast`, `setPreviewOverlay`, `previewProcessingEnabled` | `function setFalseColorLegend(` |
| 7893–8558 | **WebGL preview processing** (peaking, zebra, false colour, exposure LUT) | `ensurePreviewProcessingWebGl`, `renderProcessedPreviewFrameWebGl`, `renderProcessedPreviewFrame` | `function ensurePreviewProcessingWebGl(` |
| 8559–8594 | MJPEG `<img>` stream install; refresh scheduler | `loadPreviewStream`, `installPreviewStream`, `scheduleStateRefresh` | `function installPreviewStream(` |
| 8595–9108 | **Optimistic snapshot patch** — client copy of every command's effect (`switch (cmd)` 8696) | `mergeCameraStateFields`, `applyCommandSnapshotPatch` | `function applyCommandSnapshotPatch(` |
| 9109–9326 | **`sendCommand`** (only `POST /api/command` caller besides 11509); option buttons; timecode; photo sequence | `sendCommand`, `buildOptionButtons`, `beginPhotoCaptureSequence` | `async function sendCommand(payload)` |
| 9327–10206 | **`renderSnapshot`** — whole-page render from `/api/state`; option-button onClick handlers 9875–10171 | `renderSnapshot` | `function renderSnapshot(` |
| 10207–10503 | Fetchers: state, presets, config load/save, media list/delete/download, preset import | `fetchState`, `fetchConfigFile`, `saveConfigFile`, `deleteSelectedMediaItems`, `importPresetFiles` | `async function fetchState(` |
| 10504–10689 | Preset apply payload (key allow-list 10526), save/load/delete | `scalarPresetValue`, `buildPresetApplyPayload`, `loadPresetFromLibrary` | `function buildPresetApplyPayload(` |
| 10690–10790 | Record/timelapse toggle; date input parse | `toggleRecord`, `parseDateTimeInputParts` | `async function toggleRecord(` |
| 10791–11347 | `apply*` / `request*` command senders (select-driven, IMU, date, fan, audio, battery, media, power) | `applySelectCommand`, `calibrateImuBias`, `requestFormatMedia`, `requestStandby` | `async function applySelectCommand(` |
| 11348–11605 | **Event wiring** for every control; idle `user_activity` ping 11503–11515 | `installInteractions` | `function installInteractions() {` |
| 11606–11618 | Bootstrap: wire, stream, readout loop, 1 s `fetchState` poll | — | `window.setInterval(() => fetchState(true), 1000);` |

**JS → HTTP endpoints**

| JS function (line) | Method + path | Call line |
| --- | --- | --- |
| `sendCommand` (9109) | `POST /api/command` | 9123 |
| `installInteractions` → `notifyStandbyActivity` | `POST /api/command` `{cmd:"user_activity"}` (raw fetch, ≤1/s on pointerdown) | 11509 |
| `fetchState` (10207) | `GET /api/state` | 10224 |
| `fetchPresetLibrary` (10246) | `GET /api/presets` | 10252 |
| `fetchConfigFile` (10304) | `GET /api/config` | 10313 |
| `saveConfigFile` (10330) | `POST /api/config` | 10341 |
| `fetchMediaLibrary` (10361) | `GET /api/media` | 10367 |
| `deleteMediaLibraryItem` (10380) | `POST /api/media/delete?kind=&id=` | 10389 |
| `downloadSelectedMediaItems` (10404) | `GET /api/media/download-selected?…` (anchor href) | 10418 |
| `deleteSelectedMediaItems` (10426) | `POST /api/media/delete-selected?…` | 10444 |
| `importPresetFiles` (10457) | `POST /api/presets/import?name=` | 10468 |
| `saveCurrentPreset` (10619) | `POST /api/presets/save?name=` | 10629 |
| `loadPresetFromLibrary` (10649) | `GET` `preset.download_url` (= `/api/presets/download/<file>`, built `App:5447`), then `sendCommand(apply_preset)` | 10656 |
| `deletePresetFromLibrary` (10666) | `POST /api/presets/delete?file=` | 10676 |
| `renderMediaLibrary` (7669) | `GET /api/media/download?kind=&id=` (href from `item.download_url`, built `App:6140`) | 7769 |
| `renderPresetLibrary` (7436) | `GET /api/presets/download/<file>` (href) | 7484 |
| `loadPreviewStream` (8559) | `GET /preview.mjpeg?stream=<nonce>` | 8563 |
| HTML/CSS | `GET /icons/<name>.png` (26 references, first at 13) | — |

**JS function → socket commands it sends** (all through `sendCommand` unless noted)

| JS function | line | sends `cmd` |
| --- | --- | --- |
| `autofocusWindowPayload` | 5888 | set_af_window |
| `resolutionCommandPayload` | 5452 | set_resolution |
| `dispatchCdngCompressionSelection` | 5619 | set_record_format, set_lossy_dng_ratio, set_cdng_compression |
| `h264ResolutionCommandPayload` | 5704 | set_h264_resolution |
| `applyFavoritesOrder` | 6500 | set_favorites_order |
| `renderFavoriteControls` | 6742 | ~50: every monitoring/assist/still/audio/battery/UI command, set_record_format, set_prores_profile, set_lossy_dng_ratio, set_raw_bit_depth, set_record_gyro_enabled, set_timecode_mode, set_af_*, set_fan_mode, apply_date_time, set_sleep_mode … |
| `queueNextPhotoInSequence` | 9268 | capture_photo |
| `renderSnapshot` | 9327 | set_fps, set_iso(_auto), set_shutter_us/_auto, set_wb(_auto), set_record_format, set_prores_profile, set_lossy_dng_ratio, set_raw_bit_depth, set_record_gyro_enabled, set_photo_mode/long_exposure/bracketing_enabled, set_sound_recorder_enabled, set_timecode_mode, set_af_mode/range/speed, 13 `set_*_enabled` toggles |
| `buildPresetApplyPayload` | 10516 | apply_preset |
| `toggleRecord` | 10690 | timelapse_stop, timelapse_start, record_stop, record_start |
| `applySelectCommand` | 10791 | dynamic `commandName` (12 callers 11431–11464: external monitor ×3, peaking ×2, zebra, false colour, LUT, guides ×2, centre marker, anamorphic) |
| `applyUiOrientationSelection` / `applyControlsOpacitySelection` / `applyControlsModeSelection` | 10801 / 10811 / 10820 | set_ui_orientation / set_camera_controls_opacity / set_camera_controls_mode |
| `applyStillTimerSelection` / `applyStillFormatSelection` / `applyStillBurstSelection` | 10829 / 10838 / 10861 | set_photo_timer / set_photo_timelapse + set_photo_format / set_photo_bracketing_ev + set_photo_burst |
| `applyStillTimelapseSelection` / `applyStillTimelapseToggle` | 10872 / 10895 | set_photo_timelapse |
| `applyImuDriverSelection`, `applyImuOrientationSelection`, `adjustImuSyncOffset`, `resetImuSyncOffset`, `setImuLevelReference`, `clearImuLevelReference`, `calibrateImuBias` | 10945–11007 | set_imu_driver, set_imu_orientation, adjust_imu_sync_offset, reset_imu_sync_offset, set_imu_level_reference, clear_imu_level_reference, calibrate_gyro |
| `applyDateTimeSettings` / `applyTimeZoneSelection` / `applyFanModeSelection` | 11035 / 11060 / 11088 | apply_date_time / apply_time_zone / set_fan_mode |
| `refreshAudioCaptureCapabilities` / `applyAudioCaptureOptions` | 11100 / 11144 | audio_capabilities / set_audio_capture_options |
| `applyAudioInputDeviceSelection` / `applyAudioOutputDeviceSelection` | 11152 / 11162 | set_audio_input_device / set_audio_output_device |
| `scheduleInputVolumeCommit` / `scheduleHeadphoneVolumeCommit` | 11171 / 11185 | set_input_volume / set_headphone_volume (debounced) |
| `applyBatteryCapacitySelection`, `applyBatteryTypeSelection`, `adjustCustomBatteryWh`, `adjustCustomBatteryVoltage`, `applySleepModeSelection` | 11199–11252 | set_battery_capacity, set_battery_type, set_custom_battery_wh, set_custom_battery_voltage, set_sleep_mode |
| `requestFormatMedia` / `requestEjectMedia` / `requestMountMediaDrive` / `requestMediaSpeedTest` | 11262 / 11277 / 11289 / 11305 | format_media / eject_media / mount_media / run_media_speed_test |
| `requestStandby` | 11314 | dynamic: `wake` if state is standby, else `enter_standby` (11316) |
| `requestRestartSystem` / `requestPowerOffSystem` | 11324 / 11336 | restart_system / power_off_system |
| `installInteractions` | 11348 | set_photo_timelapse, set_exposure_compensation, set_exposure_metering, set_prores_color_profile, set_cdng_preview_color_profile, user_activity, set_standby_timeout, set_standby_usb_power_off, set_wb |

Commands handled by Core but **never sent by the WebUI**: `ping`, `help`, `get_state`, `preview_subscribe`, `shutdown`, `get_media_test_state`, `set_capture_mode`, `set_tuning_file`, `set_imu_sync_offset` (absolute; WebUI uses adjust/reset). The WebUI sends no command Core lacks.

---

## 2. Dispatch tables

### 2.1 Socket / `/api/command` commands (`App` `handleCommand`, 110 names)

Dispatch idiom: `    if (command.name == "<name>") {` at 4-space indent, plus `handleUiToggle("<name>", "<UI.conf key>")` for 15 toggles. Same function serves the socket (`handleRequest`, `App:7055`), WebUI (`handleWebCommand`, `App:7085`) and hardware inputs (`dispatchHardwareInputCommand`, `App:8458`). "calls" omits the ubiquitous `camera_.settings` / `camera_.lastError`. "help" = listed in the static `help` reply (`App:9216`, 98 names; the 12 marked **no** are missing).

| command | line | calls (first ≤4) | category | Web | help |
| --- | --- | --- | --- | --- | --- |
| `user_activity` | 9118 | — | standby | y | **no** |
| `set_standby_timeout` | 9120 | updateSharedUiGeneralSettings | standby | y | **no** |
| `set_standby_usb_power_off` | 9129 | updateSharedUiGeneralSettings | standby | y | **no** |
| `enter_standby` | 9138 | camera_.enterStandby, standbyLowPower, readSharedUiSettings, standbyUsbPower | standby | y (requestStandby) | **no** |
| `wake` | 9174 | camera_.state, standbyLowPower, standbyUsbPower, camera_.wakeFromStandby | standby | y (requestStandby) | **no** |
| `ping` | 9212 | — | meta | — | **no** |
| `help` | 9215 | static list | meta | — | **no** |
| `get_state` | 9218 | camera_ getters + settingsBody | meta | — | y |
| `set_iso` | 9242 | camera_.setIso | camera (SB) | y | y |
| `set_exposure_compensation` | 9251 | camera_.setExposureCompensation | camera (SB) | y | y |
| `set_exposure_metering` | 9260 | camera_.setExposureMetering | camera (SB) | y | y |
| `set_iso_auto` | 9269 | camera_.setIsoAuto | camera (SB) | y | y |
| `set_fps` | 9275 | camera_.setFps | camera (SB) | y | y |
| `set_shutter_us` | 9284 | camera_.setShutterUs | camera (SB) | y | y |
| `set_shutter_auto` | 9293 | camera_.setShutterAuto | camera (SB) | y | y |
| `set_wb` | 9299 | camera_.setWhiteBalanceKelvin | camera (SB) | y | y |
| `set_wb_auto` | 9308 | camera_.setWhiteBalanceAuto | camera (SB) | y | y |
| `set_resolution` | 9314 | camera_.setResolution | camera (SB) | y | y |
| `set_record_format` | 9326 | camera_.setRecordingFormat | camera (SB) | y | y |
| `set_cdng_compression` | 9340 | camera_.setCdngCompression | camera (SB) | y | y |
| `set_lossy_dng_ratio` | 9351 | camera_.setLossyDngRatio | camera (SB) | y | y |
| `set_cdng_preview_color_profile` | 9360 | camera_.setCdngPreviewColorProfile | camera (SB) | y | y |
| `set_prores_color_profile` | 9369 | camera_.setProresColorProfile | camera (SB) | y | y |
| `set_prores_profile` | 9378 | camera_.setProresProfile | camera (SB) | y | y |
| `set_tuning_file` | 9388 | camera_.setTuningFile | camera (SB) | — | y |
| `set_raw_bit_depth` | 9397 | camera_.setRawBitDepth | camera (SB) | y | y |
| `set_h264_resolution` | 9412 | camera_.setH264Resolution | camera (SB) | y | y |
| `set_timecode_mode` | 9424 | camera_.setTimecodeMode, updateSharedUiGeneralSettings | camera (SB) | y | y |
| `set_af_mode` | 9439 | camera_.setAutofocusMode | camera (SB) | y | y |
| `set_af_range` | 9448 | camera_.setAutofocusRange | camera (SB) | y | y |
| `set_af_speed` | 9457 | camera_.setAutofocusSpeed | camera (SB) | y | y |
| `set_af_window` | 9466 | camera_.setAutofocusWindow, updateSharedUiGeneralSettings | camera (SB) | y | y |
| `set_focus_peaking_enabled` | 9493 | handleUiToggle → UI.conf focusPeakingEnabled | UI.conf toggle | y | y |
| `set_zebra_enabled` | 9495 | handleUiToggle → UI.conf zebraEnabled | UI.conf toggle | y | y |
| `set_false_color_enabled` | 9497 | handleUiToggle → UI.conf falseColorEnabled | UI.conf toggle | y | y |
| `set_lut_preview_enabled` | 9499 | handleUiToggle → UI.conf lutPreviewEnabled | UI.conf toggle | y | y |
| `set_guides_enabled` | 9501 | handleUiToggle → UI.conf guidesEnabled | UI.conf toggle | y | y |
| `set_center_marker_enabled` | 9503 | handleUiToggle → UI.conf centerMarkerEnabled | UI.conf toggle | y | y |
| `set_grayscale_enabled` | 9505 | handleUiToggle → UI.conf grayscaleEnabled | UI.conf toggle | y | y |
| `set_smpte_enabled` | 9507 | handleUiToggle → UI.conf smpteEnabled | UI.conf toggle | y | y |
| `set_anamorphic_desqueeze_enabled` | 9509 | handleUiToggle → UI.conf anamorphicDesqueezeEnabled | UI.conf toggle | y | y |
| `set_external_monitor_enabled` | 9511 | handleUiToggle → UI.conf externalMonitorEnabled | UI.conf toggle | y | y |
| `set_sound_recorder_enabled` | 9513 | camera_.stopTimelapse, camera_.setStillExposureMode, readSharedUiSettings, updateSharedUiGeneralSettings | capture mode / still | y | y |
| `set_capture_mode` | 9537 | camera_.isRecording, camera_.timelapseActive, readSharedUiSettings, camera_.setStillExposureMode | capture mode / still | — | **no** |
| `set_photo_mode_enabled` | 9573 | camera_.stopTimelapse, readSharedUiSettings, camera_.setStillExposureMode | capture mode / still | y | y |
| `set_photo_bracketing_enabled` | 9600 | camera_.applyCapturePreset, updateSharedUiGeneralSettings | capture mode / still | y | y |
| `set_photo_bracketing_ev` | 9612 | camera_.applyCapturePreset, updateSharedUiGeneralSettings | capture mode / still | y | y |
| `set_photo_long_exposure_enabled` | 9623 | readSharedUiSettings, camera_.applyCapturePreset, updateSharedUiGeneralSettings | capture mode / still | y | y |
| `set_date_time_overlay_enabled` | 9640 | handleUiToggle → UI.conf dateTimeOverlayEnabled | capture mode / still | y | y |
| `set_record_audio_enabled` | 9642 | handleUiToggle → UI.conf recordAudioEnabled | capture mode / still | y | y |
| `set_record_gyro_enabled` | 9644 | handleUiToggle → UI.conf recordGyroEnabled | capture mode / still | y | y |
| `set_imu_driver` | 9646 | Mpu6050RS::setConfiguredDriver | IMU | y | y |
| `set_imu_orientation` | 9656 | Mpu6050RS::setConfiguredOrientation | IMU | y | y |
| `set_imu_sync_offset` | 9666 | Mpu6050RS::setConfiguredSyncOffsetMs | IMU | — | y |
| `adjust_imu_sync_offset` | 9676 | Mpu6050RS::configuredSensorSnapshot, Mpu6050RS::setConfiguredSyncOffsetMs | IMU | y | y |
| `reset_imu_sync_offset` | 9687 | Mpu6050RS::setConfiguredSyncOffsetMs | IMU | y | y |
| `set_imu_level_reference` | 9693 | Mpu6050RS::setConfiguredLevelReference | IMU | y | y |
| `clear_imu_level_reference` | 9699 | Mpu6050RS::clearConfiguredLevelReference | IMU | y | y |
| `calibrate_gyro` | 9705 | camera_.isRecording, camera_.timelapseActive, Mpu6050RS::calibrateConfiguredSensor | IMU | y | y |
| `set_live_audio_monitoring_enabled` | 9724 | handleUiToggle → UI.conf liveAudioMonitoringEnabled | UI.conf toggle | y | y |
| `set_audio_meter_enabled` | 9726 | handleUiToggle → UI.conf audioMeterEnabled | UI.conf toggle | y | y |
| `set_focus_peaking_threshold` | 9729 | updateSharedUiGeneralSettings | UI.conf monitor | y | y |
| `set_focus_peaking_color` | 9739 | updateSharedUiGeneralSettings | UI.conf monitor | y | y |
| `set_zebra_threshold` | 9752 | updateSharedUiGeneralSettings | UI.conf monitor | y | y |
| `set_false_color_mode` | 9762 | updateSharedUiGeneralSettings | UI.conf monitor | y | y |
| `set_lut_preview_file` | 9776 | updateSharedUiGeneralSettings | UI.conf monitor | y | y |
| `set_guides_type` | 9802 | updateSharedUiGeneralSettings | UI.conf monitor | y | y |
| `set_guides_thickness` | 9815 | updateSharedUiGeneralSettings | UI.conf monitor | y | y |
| `set_center_marker_type` | 9825 | updateSharedUiGeneralSettings | UI.conf monitor | y | y |
| `set_anamorphic_ratio` | 9838 | updateSharedUiGeneralSettings | UI.conf monitor | y | y |
| `set_external_monitor_mode` | 9851 | updateSharedUiGeneralSettings | UI.conf monitor | y | y |
| `set_external_monitor_info_overlay` | 9864 | updateSharedUiGeneralSettings | UI.conf monitor | y | y |
| `set_external_monitor_orientation` | 9877 | updateSharedUiGeneralSettings | UI.conf monitor | y | y |
| `set_photo_timer` | 9890 | updateSharedUiGeneralSettings | still (UI.conf) | y | y |
| `set_photo_burst` | 9903 | updateSharedUiGeneralSettings | still (UI.conf) | y | y |
| `set_photo_format` | 9916 | readSharedUiSettings, updateSharedUiGeneralSettings | still (UI.conf) | y | y |
| `set_photo_timelapse` | 9946 | readSharedUiSettings, camera_.stopTimelapse, camera_.setStillExposureMode | still (UI.conf) | y | y |
| `set_ui_orientation` | 9998 | updateSharedUiGeneralSettings | UI.conf | y | y |
| `set_camera_controls_opacity` | 10009 | updateSharedUiGeneralSettings | UI.conf | y | y |
| `set_camera_controls_mode` | 10020 | updateSharedUiGeneralSettings | UI.conf | y | y |
| `audio_capabilities` | 10031 | camera_.isRecording, camera_.timelapseActive, readSharedUiSettings | audio | y | **no** |
| `set_audio_capture_options` | 10052 | camera_.isRecording, camera_.timelapseActive, readSharedUiSettings, updateSharedUiGeneralSettings | audio | y | **no** |
| `set_audio_input_device` | 10076 | camera_.isRecording, updateSharedUiGeneralSettings | audio | y | y |
| `set_audio_output_device` | 10091 | updateSharedUiGeneralSettings | audio | y | y |
| `set_input_volume` | 10104 | updateSharedUiGeneralSettings | audio | y | y |
| `set_headphone_volume` | 10114 | updateSharedUiGeneralSettings | audio | y | y |
| `set_battery_type` | 10124 | readSharedUiSettings, updateSharedUiGeneralSettings | battery / UI.conf | y | y |
| `set_battery_capacity` | 10153 | readSharedUiSettings, updateSharedUiGeneralSettings | battery / UI.conf | y | y |
| `set_custom_battery_wh` | 10167 | updateSharedUiGeneralSettings | battery / UI.conf | y | y |
| `set_custom_battery_voltage` | 10178 | readSharedUiSettings, updateSharedUiGeneralSettings | battery / UI.conf | y | y |
| `set_sleep_mode` | 10206 | updateSharedUiGeneralSettings | battery / UI.conf | y | y |
| `set_favorites_order` | 10219 | updateSharedUiGeneralSettings (filtered by `favoriteCandidateOrder`) | battery / UI.conf | y | y |
| `apply_preset` | 10230 | readSharedUiSettings, camera_.applyCapturePreset, updateSharedUiGeneralSettings | preset | y | **no** |
| `apply_date_time` | 10529 | applyDateTimeSettings | system / media | y | y |
| `apply_time_zone` | 10552 | applyTimeZoneSettings | system / media | y | y |
| `set_fan_mode` | 10568 | applyFanMode | system / media | y | y |
| `format_media` | 10579 | formatMediaAtPath | system / media | y | y |
| `eject_media` | 10589 | ejectMediaAtPath | system / media | y | y |
| `mount_media` | 10596 | mountMediaDeviceAtPath | system / media | y | y |
| `get_media_test_state` | 10608 | mediaSpeedMutex_ snapshot | system / media | — | **no** |
| `run_media_speed_test` | 10616 | startMediaSpeedTest | system / media | y | y |
| `record_start` | 10623 | readSharedUiSettings, audioRecordingOptionsFromUiSettings, startSoundRecording, camera_.startRecording | capture / record | y | y |
| `capture_photo` | 10716 | readSharedUiSettings, camera_.capturePhoto, camera_.mediaWriteStatus | capture / record | y | y |
| `timelapse_start` | 10740 | readSharedUiSettings, camera_.timelapseActive, camera_.setStillExposureMode, camera_.startTimelapse | capture / record | y | y |
| `timelapse_stop` | 10775 | camera_.stopTimelapse, camera_.mediaWriteStatus | capture / record | y | y |
| `record_stop` | 10783 | stopSoundRecording, camera_.stopRecording, camera_.recordingHasDroppedFrames | capture / record | y | y |
| `preview_subscribe` | 10796 | enqueueCurrentPreviewRegistrations | system / meta | — | y |
| `restart_system` | 10801 | invokeSystemPowerAction | system / meta | y | y |
| `power_off_system` | 10808 | invokeSystemPowerAction | system / meta | y | y |
| `shutdown` | 10815 | requestShutdown | system / meta | — | y |

Fields per command and reply shapes: KB [core.md §3.2](~/Documents/Apertar/apertar-kb/architecture/core.md).

### 2.2 HTTP routes (`App` `handleWebRequest`, 7093–7650)

Idiom: `if (request.method == "<M>" && request.path == "<p>")` (exact) or `request.path.rfind("<prefix>", 0) == 0` (prefix). Unmatched: 404 for GET/POST, else 405 (`App:7645`).

| Method + path | Line | Does |
| --- | --- | --- |
| `OPTIONS *` | 7095 | 204 |
| `GET /`, `/index.html` | 7102 | `webControlPageHtml()` |
| `GET /preview.mjpeg` | 7109 | MJPEG stream (`streamMjpeg`); 503 without JPEG build |
| `GET /icons/<name>` (prefix) | 7124 | PNG from `webIconsDirectory()` |
| `GET /api/state` | 7154 | `buildWebStateJson` |
| `GET /api/media` | 7161 | `buildMediaLibraryJson` |
| `GET /api/config` | 7168 | `buildHardwareConfigFileJson` |
| `POST /api/config` | 7175 | `extractJsonStringField(text)` → `saveHardwareConfigFile` |
| `GET /api/media/download?kind=&id=` | 7197 | `streamFileToClient` / zip of a folder |
| `GET /api/media/download-selected?…` | 7318 | `mediaSelectionZipEntries` → `streamZipArchiveToClient` |
| `GET /api/presets` | 7360 | `buildPresetLibraryJson` |
| `GET /api/presets/download/<file>` (prefix) | 7367 | `findPresetFileByName` → file |
| `POST /api/presets/import`, `/api/presets/import/<name>` (prefix) | 7392 | `importPresetFileToCamera` |
| `POST /api/presets/save?name=` | 7440 | `saveCurrentPresetToCamera` (`buildCurrentPresetPayload`) |
| `POST /api/presets/delete?file=` | 7477 | `deletePresetFileFromCamera` |
| `POST /api/media/delete?kind=&id=` | 7503 | delete one item (refused while `isRecording()`) |
| `POST /api/media/delete-selected?…` | 7575 | `mediaSelectionDeletionTargets` → delete |
| `POST /api/command` | 7637 | `handleWebCommand` → `handleCommand` |

---

## 3. Small directories

| File | Lines | One line | Entry points |
| --- | --- | --- | --- |
| `src/main.cpp` | 141 | CLI flags, signal self-pipe, start/wait/stop | `main` |
| `src/ApertarCoreApp.hpp` | 179 | App class, options, owned members (110–124) | `start`, `stop`, `wait`, `requestShutdown` |
| `src/cdng/CdngEncoder.{hpp,cpp}` | 203 / 1901 | CinemaDNG writer: uncompressed, packed CSI-2, PiSP, LJ92 tiles | `CdngEncoder::writeDngFile`, `prepareRawLayout`, `writeRawPayload`, `losslessTileRows`; `Csi2RawConverter::unpack10Row/unpack12Row` |
| `src/cdng/LosslessJpegEncoder.{hpp,cpp}` | 46 / 410 | LJ92 (SOF3) encoder | `encode`, `begin`, `appendRow`, `finish` |
| `src/cdng/IfdBuilder.hpp` | 181 | TIFF IFD assembly | `IfdBuilder::add`, `build`, `buildAt` |
| `src/cdng/BlackLevel.hpp` | 34 | Black level per sample bits, CFA indices | `blackLevelForSampleBits`, `blackLevelCfaIndices` |
| `src/mlv/MlvEncoder.{hpp,cpp}` | 73 / 1299 | Magic Lantern MLV single-file writer | `open`, `writeFrame`, `close`, `frameCount` |
| `src/lossydng/LossyDngEncoder.{hpp,cpp}` | 55 / 517 | Lossy DNG 3:1 / 5:1, async writer | `setRatio`, `writeDngFile`, `drainWrites` |
| `src/lossydng/LossyJpeg12.{h,cpp}`, `fastent.h` | 142 / 1684 / 358 | **Not built** (absent from `CMakeLists.txt`) | — |
| `src/prores/ProresRecorder.{hpp,cpp}` | 50 / 159 | In-core dlopen client of `apertar-prores-libav.so` (symbols 36–40) | `startAtFolder`, `enqueueFrame`, `stop` |
| `src/prores/ProresPlugin.cpp` | 56 | Plugin C ABI | `apertar_prores_abi/create/encode/finish/destroy` (13–54) |
| `src/prores/ProresPluginApi.hpp` | 25 | ABI structs, `kApertarProresAbi = 2` | `ApertarProresConfig`, `ApertarProresFrame` |
| `src/prores/ProresEncoder.{hpp,cpp}` | 307 / 1661 | `prores_aw` encode + MOV mux (plugin side) | `openClip`, `writeFrame`, `closeClip`, `sustainableFps` |
| `src/prores/ProresColor.{hpp,cpp}` | 81 / 388 | RGB48 → YUV422P10, log LUTs, CSC thread pool | `rgb48ToYuv422p10`, `buildGpLog2Lut`, `CscPool::convert` |
| `src/prores/ProresRepair.{hpp,cpp}` | 68 / 393 | Recovery-sidecar repair (**never called**) | `needsRepair`, `repair`, `repairAll` |
| `src/video/LibavH264EncoderClient.{hpp,cpp}` | 39 / 151 | In-core dlopen client of `apertar-h264-libav.so` (symbols 112–116) | `open`, `encode`, `finish` |
| `src/video/LibavH264EncoderPlugin.cpp` | 526 | Plugin: libx264 / h264_v4l2m2m | `apertar_libav_h264_abi/create/encode/finish/destroy` (464–522) |
| `src/video/LibavH264PluginApi.hpp` | 36 | Plugin ABI struct | `ApertarLibavH264Config` |
| `src/video/NativeV4l2H264Encoder.hpp` | 382 | Header-only V4L2 M2M encoder (Pi 4) | `NativeV4l2H264Encoder::encode`, `finish` |
| `src/video/H264Hardware.hpp` | 68 | Find Pi hardware H.264 node | `findRaspberryPiH264Encoder`, `hasV4l2Format` |
| `src/audio/TimestampedAudioCapture.{hpp,cpp}` | 32 / 246 | ALSA capture via dlopen'd libasound (`LOAD` macro, 45) | `open`, `probe`, `read`, `close` |
| `src/audio/AudioRecordingSession.{hpp,cpp}` | 81 / 829 | Raw capture file → BWF WAV trimmed to video | `start`, `observeVideoFrame`, `stop` |
| `src/audio/RecordingClock.hpp`, `AudioSample.hpp` | 63 / 30 | Rational fps, wall clock; sample IO | `recordingFrameRate`, `RecordingClock`, `readAudioSample` |
| `src/hardware/GpioInput.{hpp,cpp}` | 99 / 746 | GPIO buttons + encoders (chardev v2) | `start`, `stop`; action normaliser 108 |
| `src/hardware/Pcf8574Input.{hpp,cpp}` | 57 / 529 | PCF8574 expander buttons | `start`, `stop`; action normaliser 140 |
| `src/hardware/NeoRotary4Input.{hpp,cpp}` | 72 / 717 | Adafruit seesaw quad encoder | `start`, `stop`; action normaliser 121 |
| `src/hardware/GroveAnalogInput.{hpp,cpp}` | 80 / 486 | Grove ADC knobs → `AnalogEvent` | `start`, `stop`; `normalizeTarget` 125 |
| `src/hardware/Mpu6050RecordingSession.{hpp,cpp}` | 158 / 2301 | IMU gyro sidecar (.gcsv) + config writers used by IMU commands | `start`, `stop`, `calibrateConfiguredSensor`, `setConfigured*` |
| `src/hardware/StandbyPowerButtonInput.{hpp,cpp}`, `PowerButtonGesture.hpp` | 19 / 76 / 39 | evdev power key; single/double press | `start`; `PowerButtonGesture::event` |
| `src/hardware/TriggerOutput.{hpp,cpp}` | 94 / 698 | Hot-shoe/flash pulse output | `start`, `pulse` |
| `src/hardware/RecordingIndicatorOutput.{hpp,cpp}` | 90 / 751 | Tally LED | `setRecordingActive`, `setStillExposureActive`, `pulseCapture` |
| `src/hardware/HardwareScriptRunner.{hpp,cpp}` | 40 / 258 | `run_scriptN` → `/bin/bash -- <path>` | `request`, `busy`, `stop` |
| `src/hardware/ButtonActionList.hpp` | 121 | Shared action-list parse (≤6 actions), script slots, LED alias check | `parseButtonActions`, `normalizeButtonMapping`, `actionToken`, `isOutputAction` |
| `src/color/ColorProfileConfig.{hpp,cpp}` | 53 / 912 | DNG matrices from `~/apertar-color-profiles.conf` + tuning; tuning metering/black level | `encoderColorProfileForSensor`, `activeTuningExposureMeteringModes`, `dngColorMatrixFromCcm` |
| `src/color/ProresIspProfile.{hpp,cpp}` | 11 / 238 | Derived log ISP tuning JSON | `makeProresIspTuning` |
| `src/color/StillColorProcessing.hpp`, `StillSrgbProfile.hpp` | 78 / 741 | CPU still render; embedded sRGB ICC | `StillColorTransform::render` |
| `src/ipc/ControlProtocol.{hpp,cpp}` | 27 / 254 | **Flat** JSON line parser, `escapeJson` | `parseControlCommand`, `ControlCommand::number/string` |
| `src/ipc/ControlServer.{hpp,cpp}` | 58 / 299 | AF_UNIX server, fd passing | `start`, `broadcast`, `broadcastWithFds`, `clientLoop` |
| `src/web/WebServer.{hpp,cpp}` | 67 / 394 | Minimal HTTP/1.1 server, origin check | `start`, `stop` |
| `src/util/SettingsFile.hpp` | 119 | Atomic write + QLockFile-compatible lock (UI.conf) | `atomicWrite`, `QtIniLock` |
| `src/util/AtomicStillFile.hpp`, `RecordingFailure.hpp`, `RecordingDropWarning.hpp` | 98 / 26 / 30 | `.writing-XXXXXX` + rename; first-error latch; drop latch | `AtomicStillFile::commit`, `RecordingFailure::set` |
| `include/apertar/core/Types.hpp` | 339 | Enums, `CaptureSettings` (124), enum `toString` (240–339) | `toString`, `toWireValue`, `timelapseExposureLimitUs` |
| `include/apertar/core/RecordingCapabilities.hpp` | 108 | Per-board format matrix + JSON | `recordingCapabilities`, `recordingCapabilitiesJson`, `supportedRecordingSettings` |
| `include/apertar/core/ProresColorProfile.hpp` | 79 | Colour-profile enum ↔ string, log encode, gamut | `toString`, `parseProresColorProfile`, `parsePreviewColorProfile` |
| `include/apertar/core/PreviewExposureReference.hpp` | 31 | Exposure reference JSON for the WebUI false colour | `previewExposureReferenceJson` |
| `src/camera/DefaultTuningSelection.hpp` | 207 | Default tuning JSON per sensor/pipeline | `preselectDefault`, `defaultForSensor` |
| `src/camera/ExposureMetering.hpp`, `ScalerCropGeometry.hpp`, `StillBracketing.hpp` | 41 / 66 / 20 | Metering bits/names; crop rectangles; bracket exposures | `normalizeExposureMetering`, `centeredRawWindowScalerCrop`, `stillBracketExposures` |

---

## 4. Duplicated truths

Each row is one fact kept by hand in several places. Change one, change all. "Drift" = copies already disagree in `upstream-1.6.0`.

### 4.1 Command names and their effects

| Truth | Copies | Drift |
| --- | --- | --- |
| The command list | Dispatcher `App:9118-10815`; `help` list `App:9216`; idle-reset/gate lists `App:9095-9116`, `:9208-9210`; WebUI senders (§1.3); WebUI optimistic patch `switch (cmd)` `WCP:8696-9107`; UI `Apertar-UI/src/ApertarControlBridge.cpp` | `help` lacks 12 (§2.1) |
| UI.conf toggle command → key | `handleUiToggle(...)` `App:9493-9511`, `:9640-9644`, `:9724-9726`; hardware toggles `toggleSharedUiBoolAction(action, "set_…", uiSettings.…)` `App:8908-8946` | — |
| Hardware analog target names | `normalizeTarget` `src/hardware/GroveAnalogInput.cpp:125`; `normalizeHardwareAnalogTarget` `App:8410`; consumer `target == "…"` `App:8480-8606` | Copies identical except Grove also maps `none/off/disabled` → empty |

### 4.2 Button action vocabulary

| Truth | Copies |
| --- | --- |
| Action aliases → canonical name | `normalizeSingleAction` in `src/hardware/GpioInput.cpp:108`, `src/hardware/Pcf8574Input.cpp:140`, `src/hardware/NeoRotary4Input.cpp:121` (same logic, only line-wrapping differs) |
| Canonical actions → behaviour | `handleSingleHardwareInputAction` `App:8660-8956`; step actions via `pcfSettingStepMode(action, "fps"/"resolution"/"iso"/"shutter"/"wb")` `App:8770-8831`; numeric suffixes `App:1342-1425` |
| UI-only actions forwarded as `hardware_action` events | `App:8667` (zoom_toggle), `:8904` (still_mode), `:8949-8950` (settings, clip_browser, quick_menu); consumer `Apertar-UI/src/ApertarControlBridge.cpp:1250` |
| Tally-LED alias list (`recindicatorled`, `tally`, …) | `src/hardware/ButtonActionList.hpp:57`; `GpioInput.cpp:113`; `Pcf8574Input.cpp:145`; `NeoRotary4Input.cpp:126`; `RecordingIndicatorOutput.cpp:121` |
| Script slots `run_script`, `run_script1-5` | `ButtonActionList.hpp:17-33`; `HardwareScriptRunner.cpp:38-96` (`path`, `path1`–`path5`) |
| Documentation of actions | Core template comments `App:4355-4390`; UI templates (see [config.md](../architecture/config.md)) |

### 4.3 Enum ↔ string

| Enum | Copies | Drift |
| --- | --- | --- |
| `RecordingFormat` | `toString` `include/apertar/core/Types.hpp:254`; `normalizeRecordingFormatValue` + `recordingFormatFromNormalizedValue` `App:824`, `:846`; `recordingFormatFromString` `CC:199`; JS `recordFormatOptions` `WCP:4044`, `recordingFormatLabel` `WCP:5536`, `recordingFormatCommandValue` `WCP:5549`; clip folder prefixes `CC:3646-3658`; `apply_preset` parse `App:10230+` | App rejects unknown values (`{}`), CC silently maps unknown → `Cdng`; App also accepts `dng`, `prores hq/lt/proxy/422`, CC only `prores` |
| `LossyDngRatio` | `toWireValue` `Types.hpp:271`; `lossyDngRatioFromString` `App:859` **and** `CC:226` (same name, two copies); JS `lossyDngRatioCommandValue` `WCP:5592`, `lossyDngRatioFromCompression` `WCP:5615`; `apply_preset` `App:10331` | — |
| `CdngCompression` | `toString` `Types.hpp:266`; `set_cdng_compression` `App:9342-9344`; `apply_preset` `App:10324-10326`; persisted load `CC:686`; HTML `<select>` `WCP:2905` (`none`/`lossless_jpeg`/`lossy_3to1`/`lossy_5to1`); JS `normalizeCdngCompressionValue` `WCP:5597` | HTML mixes compression and lossy-ratio in one select; JS splits it (`dispatchCdngCompressionSelection` `WCP:5619`) |
| `ProresProfile` | `toString` `Types.hpp:276`; `set_prores_profile` `App:9380-9383`; `apply_preset` `App:10313-10316`; load `CC:695-696`; plugin `ProresEncoder.cpp:1630-1633`; JS `proresProfileCommandValue` `WCP:5565`, `recordingFormatLabel` `WCP:5539` | — |
| `ProresColorProfile` | `toString` / `parseProresColorProfile` `include/apertar/core/ProresColorProfile.hpp:10`, `:20`; HTML selects `WCP:2881-2886`, `:2892-2896`; JS `WCP:9509-9517` | — |
| `TimecodeMode` | `toString` `Types.hpp:301`; `normalizeTimecodeModeValue` `App:380`; `timecodeModeFromString` `CC:290`; `set_timecode_mode` `App:9424-9434`; UI.conf default `App:1605`, `:1723`; JS `timecodeOptions` `WCP:4059`, `timecodeModeLabel` `WCP:5852`, patch `WCP:8785` | — |
| `AutofocusMode/Range/Speed` | `toString` `Types.hpp:310`, `:320`, `:330`; `autofocus*FromCommandValue` `App:394`, `:404`, `:414`; `autofocus*FromString` `CC:302`, `:316`, `:330`; JS options `WCP:4060-4063`, labels `WCP:5856-5870` | — |
| `PhotoCaptureFormat` | `toString` `Types.hpp:287`; `normalizePhotoFormatValue` `App:445`, `photoCaptureFormatFromValue` `App:529`; timelapse-safe `photoFormatIsTimelapseSafeValue` `App:520` vs `photoFormatIsTimelapseSafe` `CC:1154`; JS `stillFormatOptions` / `timelapseStillFormatOptions` `WCP:4072-4073`, `safeTimelapseStillFormat` `WCP:4806` | — |
| Raw bit depth | `normalizeRawBitDepth` `CC:243`; `supportedRawBitDepthForSensor` `CC:2685`; `isFixedTenBitRecordingFormat` `CC:238`; `parseRawBitDepthValue` `App:868`; JS `rawBitDepthOptions` `WCP:4053`, `rawBitDepthAvailableForSensor` `WCP:5671`, `raw8BitAvailableForSensor` `WCP:5679`, `fixedTenBitRecordingFormat` `WCP:5652` | — |
| Exposure metering names | `src/camera/ExposureMetering.hpp:8-32`; `controlsForSettings` `CC:2034-2035`; `ColorProfileConfig.cpp:510` (tuning) | — |
| Format filesystem | `normalizedFormatFilesystemType` `App:2085`; HTML `settingsMediaFormatSelect` `WCP:3589-3592`; JS `requestFormatMedia` `WCP:11264` | — |
| Fan mode `Silent/Auto/Full Blast` | `fanModeBlock` `App:3042`, `detectManagedFanMode` `App:3104`, `applyFanMode` `App:3127`; HTML `WCP:3646-3649` | — |

### 4.4 Settings field sets

| Truth | Copies | Drift |
| --- | --- | --- |
| Camera settings JSON field list (42 keys) | `settingsBody` `App:167-216`; `settingsEvent` `CC:136-188`; inline copy in `buildWebStateJson` `App:7835+`; JS readers `mergeCameraStateFields` `WCP:8595`, `applyCommandSnapshotPatch` `WCP:8678` | Same 42 keys today (grep-diffed) |
| Persisted camera settings keys (33) | write `writeCaptureSettings` `CC:742-779`; read `loadPersistedCaptureSettings` `CC:616-741` | Read also accepts legacy `wb_locked` |
| `CaptureSettings` struct ↔ clamp ↔ sanitize | `Types.hpp:124-162`; `clampCaptureSettings` `CC:534`; `sanitizeSettingsForSensor` `CC:2707`; `supportedRecordingSettings` `RecordingCapabilities.hpp:79` | — |
| UI.conf `[General]` keys | defaults `SharedUiSettingsSnapshot` `App:1581-1639`; parse `readSharedUiSettings` `App:1641-1813`; writers = each `updateSharedUiGeneralSettings` call in `handleCommand`; web state `"ui":{` `App:7965-8021`; `Apertar-UI/src/SettingsBridge.cpp` (e.g. `focusPeakingEnabled` `:327`, `:522`) | — |
| Preset keys (`camera*` + UI.conf keys + `*Order`) | writer `buildCurrentPresetPayload` `App:6522-6697`; reader `apply_preset` `App:10230-10527`; JS allow-list `buildPresetApplyPayload` `WCP:10526+`; the `*Order` key list twice: `App:6691`, `App:10513` | **Drift**: JS allow-list lacks `cameraControlsMode`, `cameraControlsOpacity`, `cameraExposureCompensation`, `cameraExposureMetering`, `dateTimeOverlayEnabled`, `photoFormat`, `photoTimelapse`. A preset loaded from the WebUI library silently drops them; Core would accept them |
| Favourites candidate ids | `favoriteCandidateOrder` `App:727` (filter `isFavoriteCandidateId` `App:765`, applied in `set_favorites_order` `App:10224` and when reading UI.conf `App:1808`; presets pass the raw string); JS `favoriteCandidateOrder` `WCP:4091` + `favoriteItemMeta` `WCP:4128`; QML `Apertar-UI/qml/SettingsPage.qml:838` | **Drift**: all three differ. WebUI ids `smpteBars`, `soundRecorder`, `gyroData`, `autofocus`, `cameraControlsOpacity` (and QML `horizontalLevel`, `tuningFile`, `formatMedia`, `hotspot`) are not in Core's list, so Core **drops them** on `set_favorites_order` and from the favourites it reads back out of UI.conf (`App:1808`) |
| Battery types / capacities / voltages | `normalizeBatteryTypeValue` `App:571`, `batteryCapacityFitsType` `App:618`, `batteryDefaultFullVoltage` `App:593`, `defaultBatteryCapacityForType` `App:607`; JS `batteryTypeOptions` `WCP:4089`, `batteryCapacityOptionsForType` `WCP:5978`, `defaultBatteryFullVoltageForType` `WCP:5998` | Values agree today |
| Assist option labels (guides, centre marker, anamorphic, peaking colour, ext. monitor, false colour, sleep) | normalisers `App:639-726`; JS option arrays `WCP:4076-4090`; JS converters `WCP:4516-4590` | — |

### 4.5 Sensor / mode / fps knowledge (three copies; four with the touch UI)

> Fork `cinemate-port` (2026-10-27): a frame-rate or limit change has to land in **four** places, and each of them filters
> by the *current* mode: Core `tableMaximumFpsForResolution` + `enforceLosslessCaptureLimits` (CC), the hardware list
> `availablePcfFpsOptions` / `maximumPcfFpsForSettings` (App), the WebUI `availableFpsOptionsForSnapshot` /
> `maximumSupportedFpsForSnapshot`, and the touch UI `availableFpsOptions` / `maximumSupportedFpsForResolution`
> (`Apertar-UI/qml/CameraPage.qml`). Tonight 33/50 fps was blocked by four separate 30-fps caps. The IMX585 list is now
> 25/33/50 everywhere (**temp**).

| Truth | Copies |
| --- | --- |
| Max fps per sensor and size | `CC:2493-2683` (`imx477MaximumSupportedFpsForResolution`, `maximumSupportedFpsForResolution`); `maximumPcfFpsForSettings` `App:1076`; JS `imx477MaximumSupportedFps` `WCP:4824`, `maximumSupportedFpsForSnapshot` `WCP:4928` (IMX577 101.68 / 62.81 / 45.19 appear in all three) |
| Lossless 4K/2K caps | `CC:2424-2491`; JS `isLosslessFourKSnapshot` … `isLosslessImx585Snapshot` `WCP:4885-4927` |
| Resolution / crop menus per sensor | `CC:355-533`, `normalizedResolutionForSensor` `CC:2372`; `availablePcfResolutionOptions` `App:1182`; JS `WCP:5029-5510` (`sensorResolutionOptions` 5112, `imx585CropRatioOptionsForSnapshot` 5249, `resolutionCommandPayload` 5452) |
| H.264 sizes | `isSupportedH264Resolution` `CC:252`, `h264CaptureResolutionForSensor` `CC:1890`; `recordingCapabilitiesJson` `h264_max_*` `RecordingCapabilities.hpp:59-61`; JS `h264ResolutionOptions` `WCP:4054-4058`, `forcedH264CaptureResolutionForSnapshot` `WCP:5194` |
| Sensor family by name substring | `detectSensorFamily` `CC:2151`; `lowerAscii(sensorName).find("imx…")` in `App:1076-1260`; JS `sensorNameLower` `WCP:4810` |
| Step-option lists (ISO, shutter angle, shutter speed, WB, fps) | `App:1150-1322`; JS `fpsPresets`…`whiteBalanceOptions` `WCP:4039-4043`, `shutterSpeedOptions` `WCP:4067-4068`. Hardware fps steps are `{24,25,30,50,60[,100]}` (`App:1156-1157`) vs WebUI 27 presets (`WCP:4039`) — by design, not drift |
| Recording capability keys | `recordingCapabilitiesJson` `RecordingCapabilities.hpp:52-61`; JS `recordingFeatureSupported(snapshot, "prores"/"raw_compression"/"h264_hardware")` `WCP:5579`, `:5585`, `:5721` |

### 4.6 Paths, events, plugins, helpers

| Truth | Copies |
| --- | --- |
| `apertar-hardware.conf` search order (`$APERTAR_HARDWARE_CONFIG`, `/home/pi`, `/boot/firmware`, `/boot`) | `App:4246-4270`; embedded Python `App:3397-3411`; `GpioInput.cpp:57-68`, `Pcf8574Input.cpp:57-68`, `NeoRotary4Input.cpp:70-81`, `GroveAnalogInput.cpp:54-65`, `TriggerOutput.cpp:70-81`, `RecordingIndicatorOutput.cpp:67-78`, `Mpu6050RecordingSession.cpp:188-199`; JS fallback label `WCP:4345` |
| INI helpers `parseConfigInteger` / `parseConfigBool` / `trimAscii` / `lowerAscii` / `stripInlineComment` | `App:4406`, `:4427`; one private copy per hardware `.cpp` (e.g. `Pcf8574Input.cpp:27`, `:37`, `:78`, `:98`); `stripInlineComment` only in `TriggerOutput.cpp:56`, `RecordingIndicatorOutput.cpp:53`, `Mpu6050RecordingSession.cpp:209` (comment stripping differs per class) |
| `escapeJson` | `src/ipc/ControlProtocol.cpp:235`; `CC:95` |
| UI.conf path (`$XDG_CONFIG_HOME` / `~/.config/CinePi/UI.conf`) | `App:341-348`; UI side QSettings |
| Event names | emit sites: `App` (`camera_state` 6901/6913, `hardware_action` 8476…8950, `audio_level` 8383, `recording` 8394/8406, `prepare_recording` 10692/10705, `photo_capture` 10730) and `CC` (`settings` 139, `recording_health` 7582, `audio_level` 7592, `media_write_state` 7560, `still_exposure` 7570, `photo_capture` 7177, `photo_write_error` 5248/7029, `standby` 7688/7707, `timelapse_progress` 8443, `recording` 8792, `timelapse` 8804, `timelapse_frame` 8830); substring matchers: always-broadcast `App:10829-10838` (fork: `recording` added, upstream issue #43), tally/trigger `App:10856-10886`; consumer `Apertar-UI/src/ApertarControlBridge.cpp` |
| Media folder names | writers `CC:926` (`Photos`), `CC:943` (`Still_`), `CC:986` (`Timelapse_`), `CC:3646-3658` (`cDNG_`, `MLV_`, `H264_`, `cDNG_3to1_`/`cDNG_5to1_`, `ProRes_`), `App:1444`, `:1459` (`Audio/Audio_`); reader `discoverMediaLibraryItems` `App:6312`, `:6342`, `:6359`, `:6398`; `stillGroupFilesForId` `App:5962-5972` |
| Plugin ABI symbol names | ProRes: `ProresPlugin.cpp:13-54` vs `ProresRecorder.cpp:36-40` (+ `kApertarProresAbi` `ProresPluginApi.hpp:5`); H.264: `LibavH264EncoderPlugin.cpp:464-522` vs `LibavH264EncoderClient.cpp:112-116` |
| Plugin `.so` names / fallback dir `/home/pi/ApertarCore-build/` | `ProresRecorder.cpp:31-32`, `LibavH264EncoderClient.cpp:15`, `:28`; `CMakeLists.txt:143`, `:152`, `:192`, `:195` |
| MOV metadata keys (`apertar_color_profile`, …) | `ProresEncoder.cpp:1392-1395`; `ProresRepair.cpp:281-284` |
| Python watcher config defaults vs C++ | `App:3391-3395` (`I2C_BUS = 10`, `0x34`, PCIe `1000110000.pcie`) vs Apertar-UI copy (`Apertar-UI/src/MediaStatusBridge.cpp`) — see KB core.md §8 |

---

## 5. Grep recipes

Run from `Apertar-Core/`. Use `grep -nF` for literals with quotes/backslashes. **In these tables `\|` is the markdown escape for a plain `|`**: type `|` (ERE alternation or shell pipe).

### Commands and routes

| Want | Command |
| --- | --- |
| Where command X is handled | `grep -nF 'command.name == "X"' src/ApertarCoreApp.cpp` (UI toggles: `grep -nF 'handleUiToggle("X"' src/ApertarCoreApp.cpp`) |
| Every handled command, in order | `grep -nE '^    if \(command\.name == "\|handleUiToggle\("' src/ApertarCoreApp.cpp` (111 hits = 110 commands + the idle-reset gate at 9111) |
| Fields a command reads | `sed -n '<line>,+30p' src/ApertarCoreApp.cpp \| grep -oE 'command\.(string\|number)\("[a-z_]+"\)'` |
| Who sends command X from the WebUI | `grep -nF 'cmd: "X"' src/web/WebControlPage.cpp`; also `grep -nF '"X"' …` for `applySelectCommand` callers |
| Client-side guess of X's effect | `grep -nF 'case "X":' src/web/WebControlPage.cpp` |
| HTTP routes | `grep -nE 'request\.method == "' src/ApertarCoreApp.cpp` |
| WebUI HTTP calls | `grep -nE 'fetch\(\|\.href = \|\.src = ' src/web/WebControlPage.cpp` |
| Hardware action X | `grep -nF 'action == "X"' src/ApertarCoreApp.cpp src/hardware/*.cpp` |

### Settings persistence

| Store | Find writes | Find reads |
| --- | --- | --- |
| Camera settings `~/.config/apertar-core/camera_settings.conf` | `grep -nF '"<key>="' src/camera/CameraController.cpp` (`writeCaptureSettings`) | `grep -nF 'key == "<key>"' src/camera/CameraController.cpp` (`loadPersistedCaptureSettings`). Flow: setter → `applySettingsLocked` → `persistSettingsLocked` → debounced `CaptureSettingsPersister` |
| UI.conf `[General]` (camelCase keys) | `grep -nE '\{ ?"<key>", ' src/ApertarCoreApp.cpp` (pairs passed to `updateSharedUiGeneralSettings`) | `grep -nF 'key == "<key>"' src/ApertarCoreApp.cpp` (inside `readSharedUiSettings`, 1641–1813) |
| `apertar-hardware.conf` | IMU only: `grep -n 'setConfigured' src/hardware/Mpu6050RecordingSession.cpp`; whole file: `saveHardwareConfigFile` | per class: `grep -nE 'section == "\|key == "' src/hardware/<Class>.cpp` |
| Presets (`~/.config/CinePi/UI/presets/*.json`) | `buildCurrentPresetPayload` (`App:6522`) | `apply_preset` (`App:10230`), JS `buildPresetApplyPayload` |

### Events

| Want | Command |
| --- | --- |
| All emit sites of event X | `grep -nF 'event\":\"X' src/ApertarCoreApp.cpp src/camera/CameraController.cpp` (the source holds `\"event\":\"X\"`) |
| All event names emitted | `grep -noE 'event\\":\\"[a-z_]+' src/ApertarCoreApp.cpp src/camera/CameraController.cpp \| sort -t: -k3 -u` |
| Camera-side emitter calls | `grep -n 'eventCallback_(' src/camera/CameraController.cpp` |
| Is X broadcast during a command? | read `App:10829-10838` (substring list) |

### Values and parsing

| Want | Command / note |
| --- | --- |
| Parser quirks | `src/ipc/ControlProtocol.cpp:164-233`: flat object only. Strings and bare values are both stored as **strings** in `fields`; `"800"` and `800` are identical. A bare value runs to the next `,` or `}` (`:120-135`), so nested objects/arrays corrupt the parse. Duplicate keys: last wins. `cmd` required; `id` parsed with `number()` |
| `command.number("k")` | `std::stod` that must consume the whole string (`ControlProtocol.cpp:139-154`): `"1.5x"` → nullopt |
| Booleans | No shared helper in the dispatcher: 7 sites in `handleCommand` test `== "true" \|\| == "1"` (`grep -nF '== "true" \|\|' src/ApertarCoreApp.cpp` → 13 file-wide); UI.conf uses `parseUiSettingsBool` (`App:350`); hardware conf uses per-class `parseConfigBool` |
| Lists in commands | Must be one string: `splitSimpleListValue` (`App:771`) splits on `\|` if present, else `,`. JS flattens arrays with `scalarPresetValue` (`WCP:10504`) |
| POST /api/config body | Not the flat parser: `extractJsonStringField` (`App:5049`) pulls one string field |
| Value normalisers | `grep -nE '^std::string normalize[A-Za-z]+Value\(' src/ApertarCoreApp.cpp` |
| Enum string tables | `grep -nE '^inline const char \*to(String\|WireValue)\(' include/apertar/core/*.hpp` |

### Navigation

| Want | Command |
| --- | --- |
| All top-level functions in App/CC | `grep -nE '^[A-Za-z].*\(' src/ApertarCoreApp.cpp \| grep -v ';$'` |
| `CameraSession` methods | `awk 'NR>=5230 && NR<=7575 && /^    [A-Za-z].*\(/' src/camera/CameraController.cpp` (adjust range via `grep -n 'class CameraController::CameraSession'`) |
| WebUI JS functions | `grep -nE '^    (async )?function ' src/web/WebControlPage.cpp` |
| WebUI CSS / HTML / JS boundaries | `grep -nE '<style>\|</style>\|<script>\|</script>' src/web/WebControlPage.cpp` |
| WebUI settings panels | `grep -nF 'class="settings-panel' src/web/WebControlPage.cpp` |
| Code compiled out without libcamera | `grep -n '^#if APERTARCORE_HAS_LIBCAMERA' src/camera/CameraController.cpp` (1017–5226 is one block) |
