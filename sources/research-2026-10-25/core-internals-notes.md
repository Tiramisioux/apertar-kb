# Apertar-Core developer notes (read-only research)

These notes cover the Apertar-Core repository at HEAD `65ccfa8`, read-only (nothing edited, no git state changed).
- **Paths** are written as `Apertar-Core/...`. Apertar-UI paths say so explicitly.
- **Sources**: I read sections 1–4 myself. Sections 5–9 merge reports from three research sub-agents with my own spot-checks.
- **Spot-checks done**:
  - `LossyJpeg12` is not compiled.
  - The NVMe Python watcher is embedded in Core.
  - `repairAll` is never called.
  - The two plugin loaders' search paths.
  - The timelapse `queueError` overwrite.
- **UNCONFIRMED** marks inferences.

Notable bugs are listed at the end (§11).

---

## 1. Source map

There are no TODO, FIXME or XXX comments anywhere in `src/` or `include/`.

| Dir | Responsibility | Key classes / files |
|---|---|---|
| `src/` (root) | Entry point and app orchestrator | `main.cpp` (CLI, signals); `ApertarCoreApp.{hpp,cpp}` (11k lines: command dispatch, web API handlers, media mount/eject/format, preview fan-out, MJPEG, standby, hardware action mapping) |
| `src/camera/` | libcamera session, mode selection, controls, recording frame path, stills, timelapse | `CameraController` (public API) with inner `CameraController::CameraSession` (`CameraController.cpp:5230`), `DngRecordingQueue` (`:3249`), `H264PreviewRecorder` (`:3930`), `PhotoCaptureWriter` (`:5018`). Headers: `DefaultTuningSelection.hpp` (tuning auto-pick), `ScalerCropGeometry.hpp`, `ExposureMetering.hpp`, `StillBracketing.hpp` |
| `src/cdng/` | CinemaDNG writer (uncompressed and LJ92 lossless) | `CdngEncoder`, `Csi2RawConverter` (`CdngEncoder.hpp:13,22`), `LosslessJpegEncoder`, `IfdBuilder.hpp` (TIFF IFD), `BlackLevel.hpp` |
| `src/lossydng/` | Lossy cDNG (3:1, 5:1): quantise then SOF3 | `LossyDngEncoder`. `LossyJpeg12.{cpp,h}` and `fastent.h` are DEAD: not in `CMakeLists.txt:69-96` and never included |
| `src/mlv/` | Magic Lantern MLV single-file writer | `MlvEncoder` |
| `src/video/` | H.264 | `LibavH264EncoderClient` (dlopen client, in core); `LibavH264EncoderPlugin.cpp` (built as module `apertar-h264-libav.so`); `LibavH264PluginApi.hpp` (C ABI); `NativeV4l2H264Encoder.hpp` (Pi 4 bcm2835-codec, compiled into the plugin); `H264Hardware.hpp` (encoder probe) |
| `src/prores/` | ProRes | `ProresRecorder` (dlopen client, in core); `ProresPlugin.cpp`, `ProresEncoder`, `ProresColor`, `ProresRepair` (all in module `apertar-prores-libav.so`); `ProresPluginApi.hpp` |
| `src/color/` | Colour | `ColorProfileConfig` (DNG matrices, tuning parsing); `ProresIspProfile` (derived log tuning JSON); `StillColorProcessing.hpp` (CPU still rendering); `StillSrgbProfile.hpp` (sRGB ICC bytes) |
| `src/audio/` | ALSA capture and WAV/BWF | `TimestampedAudioCapture` (dlopens libasound), `AudioRecordingSession`, `RecordingClock.hpp`, `AudioSample.hpp` |
| `src/hardware/` | Physical I/O | `GpioInput`, `Pcf8574Input`, `NeoRotary4Input`, `GroveAnalogInput`, `Mpu6050RecordingSession` (multi-IMU gyro sidecar), `StandbyPowerButtonInput` with `PowerButtonGesture.hpp`, `TriggerOutput`, `RecordingIndicatorOutput`, `HardwareScriptRunner`, `ButtonActionList.hpp` |
| `src/ipc/` | Unix-socket control protocol | `ControlServer` (AF_UNIX stream, thread per client, `SCM_RIGHTS` fd passing `ControlServer.cpp:66,105,139,215`), `ControlProtocol` (`ControlCommand`, `ParseResult`) |
| `src/web/` | HTTP server and embedded WebUI | `WebServer` (AF_INET, thread per client `WebServer.cpp:194,276`), `WebControlPage.cpp` (11.6k-line embedded page), `icons/*.png` |
| `src/util/` | Small helpers | `AtomicStillFile.hpp`, `SettingsFile.hpp` (`atomicWrite`), `RecordingDropWarning.hpp`, `RecordingFailure.hpp` |
| `include/apertar/core/` | Public shared types | `Types.hpp` (enums, `CaptureSettings`, `Resolution` with default 3840x2160 `:102-110`), `RecordingCapabilities.hpp`, `ProresColorProfile.hpp`, `PreviewExposureReference.hpp` |
| `scripts/` | `start-apertar-core.sh` | §10 |
| `config/` | `apertar-core-capture-priority.conf` (systemd drop-in) | §10 |

**Build** (`Apertar-Core/CMakeLists.txt`):
- C++20, Release by default (`:12-21`).
- Required: yaml-0.1 and ALSA headers (`:27-28`). Optional: libcamera (`:37-41,133-138` → `APERTARCORE_HAS_LIBCAMERA`), turbojpeg or jpeg (`:120-131`), libav (`:43-45`).
- Executable source list: `:69-96`.
- Plugin modules: `:143-169`.
- Install: binary to `bin`, plugins to `lib/apertar-core` (`:190-196`).
- Option `APERTARCORE_PRORES_FFMPEG_PREFIX` for a private FFmpeg (≥62) used only by ProRes (`:19,46-65`).

---

## 2. `src/main.cpp`

### CLI

| Option | Effect | Ref |
|---|---|---|
| `--socket PATH` | Control socket. Default `/tmp/apertar-core.sock` | `main.cpp:32,56-58`; default in `ApertarCoreApp.hpp:33` |
| `--media PATH` | Media root. Default `/media/RAW` | `main.cpp:33,60-62`; `ApertarCoreApp.hpp:34` |
| `--web-bind ADDR` | Default `0.0.0.0` | `main.cpp:34,64-66`; `ApertarCoreApp.hpp:35` |
| `--web-port PORT` | Default 8000; `0` disables the web server; >65535 exits 2 | `main.cpp:35,68-81`; `ApertarCoreApp.hpp:36` |
| `--simulate` | Do not open the camera | `main.cpp:36,52-54` |
| `--help` | Print usage, exit 0 | `main.cpp:48-51` |
| anything else | Print usage, exit 2 | `main.cpp:84-86` |

### Signals: self-pipe pattern
1. `pipe2(O_CLOEXEC)` with the write end non-blocking (`main.cpp:91-96`).
2. `sigaction` for SIGINT and SIGTERM with SA_RESTART. The handler only writes one byte (errno is preserved) (`:13-25,98-104`). The comment explains why: shutdown takes locks and joins threads, so it must not run in the handler (`:89-90`).
3. A `signalThread` blocks on `read()`, then calls `app.requestShutdown()` (`:113-120`).

### Startup and exit sequence
1. Parse options.
2. Construct `ApertarCoreApp` (`:106`).
3. Call `app.start()`; on false, exit 1 (`:108-111`).
4. Start the signal thread.
5. Print the socket and web URLs (`:122-128`).
6. `app.wait()` (`:129`).
7. Write a byte to the pipe to release the signal thread, join it (`:130-133`).
8. `app.stop()`, close the pipe (`:134-137`).

SIGPIPE is not ignored in main. UNCONFIRMED whether the socket code uses `MSG_NOSIGNAL`; the other agent covers the socket code.

---

## 3. `ApertarCoreApp`

### Members (`Apertar-Core/src/ApertarCoreApp.hpp`)
- **Options**: `Options` (`:32-38`).
- **Owned objects, in declaration order (= construction order)** (`:110-124`): `camera_` (CameraController), `controlServer_`, `webServer_`, `gpioInput_`, `standbyPowerButton_`, `groveAnalogInput_`, `neoRotary4Input_`, `pcf8574Input_`, `hardwareScriptRunner_`, `recordingIndicatorOutput_`, `triggerOutput_`, `soundRecorder_` (AudioRecordingSession, for audio-only recordings).
- **Locks**:
  - `waitMutex_` / `waitCv_` (main loop).
  - `commandMutex_`: serialises every `handleCommand` (`ApertarCoreApp.cpp:9093`).
  - `hardwareActionMutex_` and `hardwareInputSequenceMutex_`.
  - `eventMutex_` with `collectingCommandEvents_` / `pendingCommandEvents_`: events emitted while a socket command runs are appended to that command's reply.
- **Preview fan-out**: `previewMutex_`/`previewCv_`, `pendingPreviewRegistrations_` (deque), `pendingPreviewFrame_` (latest only), `registeredPreviewFrames_` (slot → DMABUF descriptor), `previewThread_` (`:140-147`).
- **MJPEG web preview**: `mjpegThread_`, `webPreviewSlots_`, `latestMjpegFrame_`, `mjpegClientCount_` (`:149-159`).
- **Telemetry and media speed test**: `mediaSpeedThread_` (`:161-176`).

### Constructor (`ApertarCoreApp.cpp:6781-6794`)
It wires callbacks:
- camera → `publishEvent` and `enqueuePreviewFrame`;
- GPIO and NeoRotary → `handleHardwareInputAction(action)` for presses, and `(action, false)` for rotations;
- power button → `handlePowerButtonPress`;
- Grove → `handleHardwareAnalogInput`;
- PCF8574 → `handleHardwareInputAction`.

The `CameraController` constructor runs first (member order). It:
1. loads persisted settings;
2. coerces them to board capabilities;
3. adopts `LIBCAMERA_RPI_TUNING_FILE` from the environment if no tuning file is saved;
4. validates it;
5. sets the process env (`CameraController.cpp:7577-7614`).

### Startup: `ApertarCoreApp::start()` (`ApertarCoreApp.cpp:6801-6903`)
1. Guard re-entry with `running_.exchange(true)` (`:6803`).
2. **Standby crash recovery** (not in simulate mode):
   - If `/run/apertar-standby-low-power/settings` exists, run `sudo -n /usr/local/libexec/apertar-standby-low-power restore` with an 8 s timeout. Failure aborts start (`:6807-6814`; helper `:1547-1550`).
   - If `/run/apertar-standby-usb/ports` exists, run `apertar-standby-usb on` with a 6 s timeout. Failure is only logged (`:6815-6819`; helper `:1541-1545`).
3. Start `previewThread_` → `runPreviewPublisher` (`:6821-6825`).
4. If built with JPEG and the web port is non-zero, start `mjpegThread_` → `runMjpegEncoder` (`:6827-6836`).
5. **`camera_.start(mediaRoot, simulate)`**; on failure stop the threads and return false (`:6838-6843`).
6. Read `~/.config/CinePi/UI.conf` `[General]` (`sharedUiSettingsPath` `:341-347`, `readSharedUiSettings` `:1641`). Reconcile still mode, long exposure, timelapse interval and bracketing into the camera (`:6845-6857`).
7. `controlServer_.start(socketPath, handleRequest)` (`:6859-6867`).
8. `webServer_.start(bind, port, handleWebRequest)` if the port is non-zero (`:6869-6879`).
9. `triggerOutput_.start()`; failure is only logged (`:6881-6884`).
10. `pcf8574Input_`, `neoRotary4Input_`, `gpioInput_`, `standbyPowerButton_` (not in simulate mode), then `groveAnalogInput_` (`:6886-6891`).
11. `recordingIndicatorOutput_.start()`; seed its recording and still-exposure state (`:6893-6898`).
12. `syncRecordingTracking` (`:6899`).
13. Publish `{"event":"camera_state","state":"ready"}` (`:6901`).

Hardware classes read `apertar-hardware.conf` only inside their own `start()`. Saving through `POST /api/config` (`:7175-7195`) does not restart them, so a Core restart is needed (UNCONFIRMED; no reload path found).

### Main loop: `wait()` (`:7021-7053`)
A 1 s `wait_for` tick until `running_` is false or shutdown is requested. Each tick:
1. Under `commandMutex_`, calls `camera_.checkRecordingFailure()` (the supervisor for asynchronous writer failures) (`:7031-7034`).
2. Re-reads `UI.conf` every second to get `standbyTimeoutSeconds` (`:7037`).
3. While recording, during timelapse, during sound recording, or when the timeout value changed, resets idle time (`:7038-7042`).
4. If idle ≥ timeout and the camera is Ready, synthesises an `enter_standby` command with `idle_timeout` (`:7043-7050`).

There are no other timers: every other loop is a dedicated thread.

### Threads (app level)

| Thread | Ref |
|---|---|
| main (wait loop) | `main.cpp:129` |
| signal thread | `main.cpp:113` |
| preview publisher | `ApertarCoreApp.cpp:6825` |
| MJPEG encoder | `:6834` |
| ControlServer accept, plus one thread per client | `ControlServer.cpp:139,215` |
| WebServer accept, plus one thread per client | `WebServer.cpp:228,276` |
| media speed test | `ApertarCoreApp.cpp:9008` |
| one thread per hardware class | §8 |

Camera-side threads are listed in §4 and §5.

### Event and preview plumbing
- **`publishEvent`** (`:10823-10852`):
  1. Always calls `handleTriggerEvent` first (LED and trigger, using substring matching, `:10854-10889`).
  2. These events are broadcast immediately, even during a command, so the separate HDMI process receives them: `settings`, `recording_health`, `standby`, `still_exposure`, `media_write_state`, `photo_write_error`, `timelapse_progress`, and the power-button actions (`:10829-10841`).
  3. Other events are collected into the reply of the in-flight socket command (`handleRequest` `:7055-7083`), or broadcast if no command is in flight.
- **Preview**:
  - The camera dup()s the preview DMABUF plane fds once per request slot. These go out as a `"preview_buffer"` registration with fds over `SCM_RIGHTS` (`broadcastWithFds`).
  - Each frame after that is a small `"preview_frame"` JSON with slot and frame id (`publishPreviewFrame` `:10891-10944`; camera side `CameraController.cpp:7248-7372`).
  - Only the latest frame is kept: the previous pending one is dropped (`:6977-6987`).
  - Registrations are cached and replayed to new clients (`enqueueCurrentPreviewRegistrations` `:6994-7019`).
- **MJPEG**:
  - Only when web clients are connected, frames are copied, scaled to at most 640x360 at ≤30 fps, and JPEG-encoded at quality 75 (`:60-63,6951-6953,8095,8194-8236`).

### Shutdown: `stop()` (`:6905-6941`)
1. Publish `camera_state: stopping`.
2. Stop, in order: pcf8574 → standby power button → neoRotary → gpio → grove → script runner → recording LED → trigger → `stopSoundRecording` → `camera_.stop()` (which stops timelapse first, then the session; `CameraController.cpp:7651-7666`) → MJPEG → preview publisher → web server → control server.
3. `syncRecordingTracking(false)`, `joinMediaSpeedTest`.
4. Run the low-power and USB standby restore helpers again.
5. Destructors then run: `~CameraController` calls `stop()` and flushes the settings persister (`CameraController.cpp:7616-7620`).

### Command gating in `handleCommand` (`:9091-9117`)
- Every command first runs `checkRecordingFailure`.
- `capture_photo`, `record_start` and `timelapse_start` are refused while media writes are pending.
- Media actions (`format_media`, `eject_media`, `mount_media`, `run_media_speed_test`) are refused while busy.
- `user_activity`, `wake`, `set_*`, capture, record and timelapse commands reset the idle timer.

### Media speed test (`:8957-9090`)
- Needs ≥96 MiB free. Test size is 64–1024 MiB depending on free space.
- Uses `fio` if available, otherwise a timed write fallback.
- Parses `WRITE: bw=...MiB/s`.

### Standby (`:9134-9190`)
`enter_standby` runs `apertar-standby-low-power all`, and optionally `apertar-standby-usb off`, through `sudo -n` with timeouts. `CameraController::enterStandby` releases the camera entirely (`CameraController.cpp:7668-7690`).

---

## 4. `CameraController` / `CameraSession` (`Apertar-Core/src/camera/CameraController.cpp`)

### Layering
- `CameraController` holds `mutex_`, the user-facing settings, the per-format profiles (`formatSettings_`), the still profile (`stillSettings_`), state, and timelapse (`CameraController.hpp:107-132`).
- `CameraSession` owns libcamera and the writers (members `CameraController.cpp:7476-7549`).
- **States**: Offline, Starting, Ready, Standby, Recording, Error, Stopping (`include/apertar/core/Types.hpp:14-22`).

### Persisted settings
- **File**: `$XDG_CONFIG_HOME/apertar-core/camera_settings.conf`, else `~/.config/apertar-core/camera_settings.conf` (`:342-353`).
- **Format**: `key=value` lines, with a `profile.<still|cdng|mlv|h264|prores>.` prefix for each profile (`:616-640,742-791`).
- **Writes**: a debounced background thread `CaptureSettingsPersister` waits 25 ms before writing (`:793-889`), using `settingsFile::atomicWrite`.
- **LossyDng shares the cdng profile** (`settingsProfileFormat` `:605-608`).

### CameraManager setup and camera selection: `CameraSession::start` (`:5254-5398`)
1. **Tuning pre-selection**:
   - If no custom tuning file is set, `tuning::preselectDefault()` scans `/sys/class/video4linux/v4l-subdev*/name` before the IPA loads.
   - It is chosen only if exactly one candidate matches.
   - Mono is detected by the existence of `device/of_node/mono-mode` (`DefaultTuningSelection.hpp:185-205`).
   - Then `applyProcessTuningFile`: sets `LIBCAMERA_RPI_TUNING_FILE` and `APERTAR_SENSOR_TUNING_FILE` (`CameraController.cpp:1111-1121`).
2. **Up to 3 attempts** (`:5279-5368`). Each attempt: `make_unique<CameraManager>()` → `start()` → `cameras()`.
   - **Selection**: the first camera whose id does not contain `/usb`, else `cameras.front()` (`:5295-5298`). There is no user camera choice.
   - **Mono detection**: the draft `ColorFilterArrangement == MONO` property if available (`:5308-5313`). Otherwise the Raw-role default pixel format (`R8`/`R10`/`R12`/`R16`/`*_CSI2P`/`MONO*`) (`:5314-5321`, format table `:3024-3118`).
   - **Tuning mismatch**: if automatic tuning is on and the default for the selected camera's `properties::Model` differs from the preselected one, it tears down the CameraManager, sets the new env and retries. A second mismatch is an error (`:5322-5341`).
   - **Log or ProRes ISP profile**: `makeProresIspTuning` writes a derived JSON (§7). The env is pointed at it and the CameraManager is restarted (`:5347-5366`).
3. Log the tuning file in use (`:5370-5373`).
4. `sensorFamily_ = detectSensorFamily(camera_->id())`, then `sanitizeSettingsForSensor` (`:5375-5376`).
5. `camera_->acquire()` → `configureAndStart` (`:5378-5390`).

`reconfigure()` is a full `stop()` + `start()`. Every mode change destroys and recreates the CameraManager (`:5481-5493`).

### Sensor detection (`detectSensorFamily` `:2151-2167`)
A case-insensitive substring match on the libcamera camera id, checked in this order:

| Order | Substring | Family |
|---|---|---|
| 1 | `imx577` | Imx577 |
| 2 | `imx477` | Imx477 |
| 3 | `imx294` | Imx294 |
| 4 | `imx585` | Imx585 |
| — | anything else | Unknown (passes settings through, no mode tables) |

- **IMX585 mono** is not a separate family. It is Imx585 plus `monochromeSensor_`, chosen by property or pixel format as above.
- Mono effects:
  - mono tuning file `<model>_mono.json` (no colour fallback; `DefaultTuningSelection.hpp:158-174`);
  - AWB off with gains 1,1 (`:2063-2068`);
  - MLV refused (`:5535-5538`);
  - DNG written as LinearRaw.
- **IMX492 is not recognised** (grep: no imx492/imx462/imx290/imx708/imx283 anywhere).
- DNG model strings: "IMX294", "IMX477", "IMX577", "IMX585-AAQJ1", "Generic" (`:2213-2262`).
- `uniqueCameraModel` "Apertar <model> [Monochrome]" (`:3203-3204`).

### Sensor modes: resolution, bit depth, crop

**Allowed raw bit depths** (`normalizeRawBitDepth` `:243-250`) are 8, 10 and 12 only. 16 maps to 12.

| Sensor | Bit depths | Ref |
|---|---|---|
| IMX477 / IMX577 | 8, 10, 12 | `:2685-2705` |
| IMX294 / IMX585 | 10, 12 | `:2685-2705` |
| Unknown | any | `:2685-2705` |
| H.264 and ProRes (not still mode) | forced 10 | `:2714-2716,2724-2725` |

**Resolution tables**:
- IMX585:
  - `1920x1080` / `1928x1090` (low alias)
  - `1920x{1038,1012,960,872,864,816,804,768,752}` (FHD crops)
  - `3840x2160` / `3856x2180` (high alias)
  - `3840x{2076,2024,1920,1744,1728,1632,1608,1536,1504}` (12-bit crops) (`:360-396`)
- IMX477: 1332x990, 2028x1520, 2028x1080, 4056x3040, 4056x2160, plus 2028x{1140…796} and 4056x{2280…1592} crops (`:398-444`).
- IMX294:
  - `4144x2176` (10-bit), `4176x2176` (12-bit), `3872x2176`
  - `4096x{2048,1844,1744,1716,1640}`
  - `3792x2824`, `3792x2528`, `3392x2824`
  - `2048x1080` / `1920x1080`, retired and redirected (`:462-532`)
- **Normalisation** (`normalizedResolutionForSensor` `:2372-2422`) maps foreign resolutions onto a sensor's native set, e.g. IMX585 2028x1080 → 1920x1080.
- **`validateResolution`** rejects anything not in the union of the tables (`:8751-8769`). `clampCaptureSettings` duplicates that list (`:542-556`).

**Sensor mode for a requested resolution** (`sensorModeForRequestedResolution` `:2205-2269`):
- IMX585:
  - FHD or 4K aliases → 1920x1080 or 3840x2160;
  - crop modes are passed through as the raw size, i.e. the driver/sensor does the crop (`isImx585FullHdCropResolution` / `Raw12Crop`).
- IMX577: fixed set. Bit depth is overridden to 12 here, with 10 and 8 fallback candidates added later.
- IMX294: derived windows are read out at full size (3792x2824, or 4144/4176x2176) and cropped in software and the ISP, because the driver's partial vertical readout is broken (`imx294ReadoutForActiveResolution` `:2193-2203`).

**Candidate list** (`sensorModeCandidatesForRequestedResolution` `:2289-2370`):
- IMX477 tries same-width taller modes, then shorter modes, then other widths (25-mode table, `:2309-2335`).
- IMX577 tries 5 modes × {12, 10, 8} bit.

**Software RAW crop** applies to IMX477, IMX577 and IMX294 when the requested size is smaller than the configured stream (`shouldUseRequestedActiveRawCrop` `:2851-2867`):
- the crop is centred, with left and top offsets aligned to 2 (`:2878-2924`);
- the byte offset must align to the CSI-2 pack group or the PiSP compression block, otherwise it throws (`activeRawLeftBytes` `:2888-2902`).

**Default black levels**: 256 for IMX477/IMX577, 200 otherwise (`blackLevelsForSensor` `:2933-2940`).

### Stream configuration (`configureAndStart` `:5968-6375`)
**Mode flags**:
- `proresMode`: not still mode, ProRes, and no photo override.
- `processedYuvMode`: H.264 or ProRes.
- `hardwareH264Mode`: processed YUV, not ProRes, and `recordingCapabilities().hardwareH264`.
- Refs: `:5985-5987`.

**Stream roles**:

| Mode | Roles | Ref |
|---|---|---|
| RAW formats and stills | `{VideoRecording (YUV420 preview/monitor), Raw}`, the "established Apertar model" | `:6031-6037` |
| ProRes | `{VideoRecording (BGR161616 = RGB48 at the exact selected resolution, else rejected), Viewfinder (preview)}` | `:6019-6020,6092,6145-6151` |
| H.264 | `{Viewfinder, VideoRecording}`. With `APERTAR_H264_SINGLE_STREAM=1`: a single VideoRecording stream. A Raw stream is added only with `APERTAR_H264_KEEP_RAW_STREAM=1` | `:6021-6030,2841-2849` |

**Search loop** (`:5999-6303`), over sensor mode × raw-stream preference × {explicit `SensorConfiguration` (outputSize + bitDepth), auto}:
- explicit sensor config is skipped for mono;
- auto is allowed only for mono, IMX294, IMX577, or IMX585 12-bit crops (`:5993-5996,6010-6015`).
- Each candidate goes through `generateConfiguration` → `validate()` (Invalid rejects) → `configure()`.
- IMX477/IMX577/IMX294 also reject a configured raw size smaller than requested (`:6162-6183`).
- All rejections are accumulated into the error text (`:5997,6305-6309`).

**Stream parameters**:
- Preview: YUV420, Rec709, longest side ≤1280x720 with aspect preserved (`kPreviewWidth/Height` `:1019-1020`, `previewSizeForSensorMode` `:2819-2830`).
- Raw pixel format: `SRGGB{8, 10_CSI2P, 12_CSI2P}` (`:2181-2191`). Mono picks `R8`/`R10_CSI2P`/`R12_CSI2P`/`R16` if offered (`:6101-6108`). The R16 branch is unreachable because bit depth is never 16 (UNCONFIRMED practical impact).
- Effective settings get the active raw resolution, and fps is clamped to the sensor maximum (`:6250-6262`).
- The PiSP compressed RAW (`PispCompressed1`) storage depth is set to the requested depth (`:6238-6246`).

**Buffers and requests**:
- `kConfiguredBufferCount = 4`, `kActiveRequestCount = 3` (RAW) (`:1023-1024`).
- H.264: 4 with hardware encode, else 6 (env `APERTAR_H264_CAMERA_BUFFERS` 3–12, `:1124-1128`).
- ProRes: 12 (env 8–32, `:1130-1134`).
- Optional CPU-cached DMA-heap buffers (`/dev/dma_heap/vidbuf_cached`, then `linux,cma`):
  - for ProRes (`APERTAR_PRORES_CACHED_DMABUF`, default on);
  - for PiSP-compressed RAW on Pi 5 (`APERTAR_RAW_CACHED_DMABUF`, default on);
  - bracketed with `DMA_BUF_IOCTL_SYNC` (`:6317-6450`).
- `makeRequests` uses `cookie = slot index` (`:6452-6495`).
- Initial controls are passed to `camera_->start()`, then all requests are queued, with `requestCompleted` connected to `requestComplete` (`:6345-6373`).

### Controls (`controlsForSettings` `:2005-2144`)
- **Frame rate**: `FrameDurationLimits = {1e6/fps, max}` µs (`:2022-2031`).
  - Still mode with manual shutter: max = exposure + 100 ms.
  - Long-exposure preview: the preview shutter is limited to 66,667 µs (`stillPreviewExposureLimitUs` `:1995-2001`).
- **AE**:
  - `AeEnable = isoAuto || shutterAuto`.
  - `ExposureTimeMode` and `AnalogueGainMode` are Auto or Manual independently.
  - `ExposureTime` = shutterUs. `AnalogueGain` = ISO / 100 (minimum 1.0).
  - `ExposureValue` (EV comp, only while AE is on; clamped to the control range).
  - `AeMeteringMode` CentreWeighted / Spot / Matrix if supported (`:2032-2061`).
- **Metering availability** = mask of tuning `rpi.agc` modes ∩ libcamera-supported values (`exposureMeteringModes` `:5821-5835`; `ExposureMetering.hpp:8-39`). Aliases: average → matrix, center → centre.
- **AWB**:
  - mono: gains 1,1;
  - uncalibrated or NoIR tuning (`whiteBalanceAvailable` false): nothing is sent;
  - auto: `AwbEnable` true;
  - manual: `AwbEnable` false, `ColourGains` {0,0} (release) plus `ColourTemperature` = K (`:2063-2080`).
- **Log/ISP profile**: forces Contrast 1, Brightness 0, Saturation 1 (`:2014-2018`).
- **ScalerCrop**: computed from `properties::ScalerCropMaximum` in native pixels (`:2082-2102`).
  - IMX294 (not hardware H.264): `centeredRawWindowScalerCrop` (the crop window maps to the raw window).
  - Everything else: `centeredPreviewScalerCrop`, which keeps the full active area unless an aspect crop is needed. Results are even-aligned (`ScalerCropGeometry.hpp:16-64`).
  - Hardware H.264 crops to the encode size.
  - The applied crop is logged (`:6350-6354`).
- **Autofocus** (only if libcamera exposes AfMode): AfMode/Range/Speed, `AfMetering=Windows`, a single `AfWindows` rectangle from normalised settings, and `AfTrigger=Start` whenever mode is Auto (`:2104-2138`). AfTrigger is re-sent on every control update.
- **Runtime changes**:
  - `applyControls` merges into `pendingControls_` (`:5495-5524`). The next `requeueRequest` attaches them (`:6497-6509`).
  - Settings with `requiresReconfigure` use `reconfigure()` instead.
- **What forces a reconfigure** (`applySettingsLocked` `:8659-8723`; setters `:7711-8216`):
  - resolution;
  - raw bit depth;
  - recording format (if processed↔raw, or if geometry or bit depth changes);
  - photo mode;
  - ISP colour profile;
  - tuning file;
  - H.264 resolution and presets (`applyCapturePreset` `:8604-8657`).
  - FPS, ISO, shutter, WB, EV, metering and AF are control-only.
  - If a reconfigure fails, the previous settings are reconfigured back; if that also fails, state becomes Error (`:8689-8710`).
  - A format switch loads that format's saved profile (`:7939-7961`).
- **FPS change** keeps the shutter angle (`shutterUsForPreservedAngle` `:189-197`, `setFps` `:7741-7772`). It is refused while recording.

### FPS limits (`maximumSupportedFpsForResolution` `:2629-2683`)
- **IMX477**: per-mode tables by bit depth (`:2493-2568`), e.g. 2028x1080 → 181.42 / 148.77 / 125.55 fps at 8 / 10 / 12-bit; 4056x3040 → 35.28 / 28.60 / 24.04. Uncompressed cDNG caps are lower (`:2570-2627`).
- **IMX577**: 101.68 / 62.81 / 45.19 / 16.39 / 11.72 fps.
- **IMX585**: 4K = 30, crops and FHD = 60.
- **IMX294**: 34.70–41.08.
- **Unknown**: 120.
- **Global clamp**: 0 < fps ≤ 280 (`:558-559,7748`).
- **Lossless cDNG limits** (`enforceLosslessCaptureLimits` `:2470-2491`): ISO ≤800 with ISO-auto disabled; fps ≤ 30 (IMX585) / 60 (2K) / 24 (4:3 4K) / 30 (other 4K).
- **Hardware H.264**: ≤30 fps at ≤1080p (`RecordingCapabilities.hpp:88-104`).

### Tuning file selection (`Apertar-Core/src/camera/DefaultTuningSelection.hpp`)
**Pipeline**: from `/sys/firmware/devicetree/base/compatible` or `/proc/device-tree/compatible` (`:18-49`):
- `brcm,bcm2712` → PiSP;
- `bcm2711`, `bcm2837`, `bcm2836`, `bcm2835` → Vc4.

**Search directories, in order** (`:56-78`); none on Unknown:
1. `$APERTAR_DEFAULT_TUNING_DIR`, else `/home/pi/Tuning-Files/defaults-pisp` (Pi 5) or `defaults-vc4`
2. the same `/home/pi/Tuning-Files/defaults-{pisp,vc4}` again (duplicate when no override)
3. `/home/pi/Tuning-Files/defaults` (legacy)
4. `/usr/local/share/libcamera/ipa/rpi/<pisp|vc4>`
5. `/usr/share/libcamera/ipa/rpi/<pisp|vc4>`

**File name** `<lowercased first word of the model>.json` (mono: `<name>_mono.json`) (`:130-181`).

**Validation** (`compatibleFile` `:80-128`):
- size 1 byte to 4 MiB, parsed with libyaml;
- a top-level `target` must be `pisp` or `bcm2835` (missing → bcm2835) and must match the pipeline.

**Custom tuning**: `set_tuning_file` normalises the path (trim, `file://`, weakly_canonical), requires `.json` and readability, then runs `compatibleFile` (`CameraController.cpp:1063-1109,8044-8112`).

**Environment variables**:
- `LIBCAMERA_RPI_TUNING_FILE`: read at construction as the custom path (`:7602-7605`) and written by Core before each CameraManager start.
- `APERTAR_SENSOR_TUNING_FILE`: always the original sensor tuning, so ColorProfileConfig reads it even when the ISP uses a derived log JSON (`:1111-1121`).
- `APERTAR_TUNING_FILE`: only used by the start script (§10).

### Callback path (`requestComplete` `:6579-6669`)
Runs on libcamera's thread.
1. Ignore cancelled requests and anything while not running.
2. Take `sessionSettingsMutex_` (shared lock).
3. On first entry, raise this thread to nice −5 (`setpriority`, allowed by `LimitNICE=-5`; logged) (`:6590-6600`).
4. Read WB (ColourTemperature, ColourGains), ExposureTime, AnalogueGain and the CCM (for bracketing) into the measured state (`:6602-6632`).
5. `capturePhotoFrame` (stills, §6).
6. Publish the preview unless a long still exposure is active (`:6634-6649`).
7. Under `recordingFrameMutex_`, if recording is enabled, wait for the first frame with timestamp ≥ record-start BOOTTIME and FrameDuration within max(500 µs, 2%) of nominal (`:6650-6661`). Then:
   - `recordProcessedPreviewFrame`: returns true when the buffer was borrowed, and that path requeues later (`:7375-7474`);
   - otherwise `recordRawFrame` (`:6853-6956`).
8. `requeueRequest`. This merges pending controls and still/bracket one-shot controls (`:6497-6577`) and counts `requeue_failures`.

**FrameDuration** metadata is normalised for µs or ns ambiguity (`normalizeFrameDurationToUs` `:2942-2967`).

---

## 5. Recording pipeline

### Board capabilities (`Apertar-Core/include/apertar/core/RecordingCapabilities.hpp`)
Detected from the devicetree compatible string (`:37-50`). The Pi 3 row covers Pi 3, Zero 2 and Pi 1/2.

| Board | rawCompression | prores | hardwareH264 | rawRecording | Allowed formats |
|---|---|---|---|---|---|
| Pi 5 / CM5 `bcm2712` (`:25-26`) | yes | yes | no (libx264 / libav) | yes | cDNG (uncompressed, lossless), LossyDNG 3:1 / 5:1, MLV, H.264 (software, ≤2560x1440), ProRes |
| Pi 4 / 400 / CM4 `bcm2711` | no | no | yes (`h264_v4l2m2m`, ≤1080p30) | yes (USB3) | cDNG uncompressed, MLV, H.264 |
| Pi 3, Zero 2, Pi 1/2 (`bcm2837`, `bcm2836`, `bcm2835`) | no | no | yes | **no** | H.264 only (`:67-68`) |
| Unknown / non-Pi (`:34`) | no | no | no | yes | cDNG uncompressed, MLV, H.264 (software) |

- `unsupportedRecordingSettings` holds the error strings (`:64-77`).
- `supportedRecordingSettings` coerces settings. It includes a 1440→1080 crop migration table and the 30 fps cap (`:79-106`).
- JSON for the UI: `recordingCapabilitiesJson` (`:52-62`).

### Recording start (`CameraSession::startRecording` `CameraController.cpp:5526-5656`)
1. Reconfigure back if the photo stream override is active.
2. Reject mono + MLV.
3. Reset `RecordingClock`.
4. `reserveClipFolder` + `create_directories` (`:5546-5553`).
5. Gyro: optional; failure is non-fatal (`:5555-5568`).
6. Audio: optional; failure aborts (`:5570-5587`).
7. Processed formats: start the ProRes or H.264 recorder on the encode stream. H.264 audio requires the timestamped libav backend (`:5589-5637`).
8. RAW formats: `DngRecordingQueue::startAtFolder` (`:5639-5647`).
9. Set `recordingFramesEnabled_` and the cadence wait.

**Not checked by Core**: mount state and free space for camera recording or stills. Only the UI gates them, and only the Sound Recorder checks the mount (`ApertarCoreApp.cpp:8351`).

### Recording stop (`:5658-5683`)
1. Close the frame gate first, so video cannot grow past the WAV endpoint.
2. Log `dropped_gap_estimate` and `requeue_failures`.
3. Stop in order: gyro → H.264 → DNG queue → ProRes → audio.

### Clip naming (`DngRecordingQueue::allocateClipFolder` `:3633-3676`)
- Folder: `<mediaRoot>/<PREFIX><yy-mm-dd>_C####`, with the first free number 0001–9999, counted per prefix and per local date. Prefixes:

  | Prefix | Used for |
  |---|---|
  | `cDNG_` | uncompressed and lossless (cannot be told apart by name) |
  | `cDNG_3to1_`, `cDNG_5to1_` | LossyDNG |
  | `MLV_` | MLV |
  | `H264_` | H.264 |
  | `ProRes_` | ProRes |

- There is a TOCTOU gap between `exists` and `create`.
- File names inside the clip folder:

  | Content | Name | Ref |
  |---|---|---|
  | DNG frames | `<clip>_%09d.dng`; the index comes from the timestamp, so drops leave gaps | `:3678-3685,3518-3526` |
  | MLV | `<clip>.MLV` | `:3316` |
  | H.264 | `<clip>.mp4`, written as `.mp4.writing` then renamed | `:4005-4006` |
  | ProRes | `<clip>.mov` + `_recovery.json` | — |
  | Audio | `<clip>.wav` | — |
  | Gyro | `<clip>.gcsv` | — |

- Sound-only recordings: `<root>/Audio/Audio_yy-mm-dd_C####/` (`ApertarCoreApp.cpp:1442-1480`).

### RAW frame path
- `recordRawFrame` (`:6853-6956`):
  1. Requires measured WB; otherwise it skips the frame with one warning (`:6857-6863`).
  2. Computes the active crop offset and size.
  3. Builds metadata (`metadataFromRequest` `:3134`) before the capacity check (wasted work on a drop).
  4. `hasCapacityForFrame`, then memcpy from the mapped buffer into a pooled vector (DMA sync for the cached heap).
  5. Enqueue → `audioRecorder_.observeVideoFrame`.
  6. Frame 0 anchors the gyro.
  7. The whole copy runs under `recordingFrameMutex_` on the callback thread.
- `DngRecordingQueue` (`:3249-3928`):

  | Format | Workers | Env | Nice |
  |---|---|---|---|
  | lossless | min(8, cores+1) | `APERTAR_CDNG_WORKERS` | 0 |
  | lossy | min(4, cores) | `APERTAR_LOSSYDNG_WORKERS` | 5 |
  | MLV | 1 | — | — |
  | other | max(2, min(4, cores)) | — | — |

  - Worker counts: `:3323-3350`. Nice is set via `APERTAR_CDNG_WORKER_NICE` (`:3699-3710`).
  - Queue depth 12, or 24 for compressed formats on ≥4 cores (env `APERTAR_CDNG_QUEUE_FRAMES` 4–64, `:3328-3330`).
  - Each worker has its own encoder.
  - Stop drains the queue, then joins the workers, then calls `LossyDngEncoder::drainWrites` (`:3390-3411`).

### Processed frame path
- **ProRes**: zero-copy. The ISP RGB48 dmabuf is borrowed with DMA sync START. The request is requeued when the encoder releases it. Cadence is tracked before enqueue (`:7413-7434`).
- **H.264**: the YUV420 buffer is borrowed. One copy worker de-strides it into I420. The request is requeued on release (`:7437-7473`). Cadence is tracked after a successful enqueue (inconsistent with ProRes). Queue depth 6 (env `APERTAR_H264_QUEUE_FRAMES` 2–16, `:4465-4474`).

### Drop detection and failure
- **`RecordingDropWarning`** (`Apertar-Core/src/util/RecordingDropWarning.hpp`): a latch per clip. The first drop emits `{"event":"recording_health","recording_has_dropped_frames":true}` (`CameraController.cpp:7580-7584`). The `recording` event also carries the flag (`:8792-8794`). Reset at record start (`:5634,5645`).
- **What marks a drop**:
  - DNG queue full (`:3536-3537,3579-3581`)
  - RAW copy or DMA sync failure (`:6934`)
  - capture gap: timestamp delta >1.5× nominal; estimate = round(Δ/nominal) − 1 (`trackRecordingCadence` `:7181-7226`)
  - ProRes queue full (`ProresRecorder.cpp:98-103`)
  - H.264 queue full (`CameraController.cpp:4271-4280`)
  - Drop logs print on the first drop and every 30th.
- **`RecordingFailure`** (`Apertar-Core/src/util/RecordingFailure.hpp`): the first message wins. It is set by DNG/MLV `failRecording` (`:3849-3859`), ProRes, H.264 (including encoder exit), and audio capture. `recordingError()` precedence: audio first, then the active format (`:5891-5901`). It is polled by `checkRecordingFailure` (`:8519-8534`) every 1 s from `wait()` and on every command; that stops recording and emits `recording active:false` with the error.

### Formats

**CinemaDNG** (`src/cdng/`)
- Classic little-endian TIFF. Layout: header → payload → IFD → Exif IFD. Payload <4 GiB.
- DNG 1.4 / backward 1.3. CFA (32803) or LinearRaw (34892, mono).
- Tags (main IFD `CdngEncoder.cpp:1527-1625`; Exif `:1642-1651`):
  - CinemaDNG TimeCodes 0xC763, FrameRate 0xC764, ReelName 0xC789 (= clip name), CameraLabel 0xC7A1;
  - per-CFA BlackLevel; AsShotNeutral = 1/gains; Color/ForwardMatrix 1 and 2; Orientation fixed to 1.
- Packing: MSB-first DNG 10/12-bit, 8-bit, or 16-bit (`:1153,1171,1839-1849`). CSI-2 packed and PiSP COMP1 input are decoded (`:1815-1837`).
- Uncompressed mode reuses a cached IFD template and patches per-frame fields (`:1505-1518,1712-1736`).
- **Lossless LJ92** (`LosslessJpegEncoder.cpp`):
  - SOF3, predictor 1, 2 components interleaved (1 for mono), fixed Huffman tables;
  - tiles of 128 rows (env `APERTAR_CDNG_TILE_ROWS` 16–1024);
  - the header is written last with `pwrite`.
- I/O: `open`/`write` with `POSIX_FADV_SEQUENTIAL`/`DONTNEED`. No fsync, no `O_DIRECT`. The file is unlinked on failure (`:1746-1785`).

**LossyDNG** (`src/lossydng/LossyDngEncoder.cpp`)
- Square-root companding to a 0–4094 domain → rate-controlled quantise (max step 64 for 3:1, 128 for 5:1; correction √(bytes/budget) clamped 0.8–1.25) → CdngEncoder SOF3 with the compact Huffman table and a LinearizationTable carrying the inverse curve (`:26-48,412-417,469-506`).
- Write path: encode to a memfd → pread into an aligned pool buffer → a process-wide singleton async writer thread (queue capped at 512 MiB, env `APERTAR_LOSSYDNG_WRITER_BYTES`; `APERTAR_LOSSYDNG_ASYNCWRITE=0` makes it synchronous) (`:97-256,483-515`).
- **Writer errors are only logged** (`:230-233`), never raised as a RecordingFailure (see §11).

**MLV** (`src/mlv/MlvEncoder.cpp`)
- Single file. `fileNum` 0, `fileCount` 1; no spanning (`:1065-1066`).
- Blocks at open: MLVI, VERS, RTCI, INFO, IDNT, RAWI, DEBG "APCM" (CCM), EXPO, WBAL (`:975-982`).
- Per frame: VIDF, plus DEBG/WBAL when values change (`:1004-1029`).
- Uncompressed only; 10/12-bit MLV packing (or 8/16); mono rejected.
- No audio blocks; the WAV is a sidecar (`:36,1069-1071`).
- The frame count is patched only at `close()` (`:1273-1285`).
- NEON packer env `APERTAR_MLV_ENABLE_NEON_PACKER` (`:23`).

**H.264** (`src/video/`; `H264PreviewRecorder` `CameraController.cpp:3930-5016`)
- **Encoder**: hardware boards force `h264_v4l2m2m`. Otherwise `APERTAR_H264_ENCODER` or `libx264` ultrafast at CRF 22 (`:4329-4342`; `LibavH264EncoderPlugin.cpp:180-192`). GOP = fps, no B-frames.
- **Container**: MP4 via libav, video stream only, no audio track (`LibavH264EncoderPlugin.cpp:118,124`). Not fragmented.
- **Pi 4 path**: `NativeV4l2H264Encoder` uses bcm2835-codec. The encoder device is probed over `/dev/video*` by driver name and M2M_MPLANE caps (`H264Hardware.hpp:16-61`). DMA-heap input buffers are filled by memcpy; libav only muxes (`NativeV4l2H264Encoder.hpp:53,106-185`).
- **Plugin**: `apertar-h264-libav.so` is a CMake MODULE (`CMakeLists.txt:143-149`), with ABI version 2 (`LibavH264PluginApi.hpp:6-25`).
  - Exported symbols: `apertar_libav_h264_{abi,create,encode,finish,destroy}` (`LibavH264EncoderPlugin.cpp:464-526`).
  - Loaded with `dlopen(RTLD_NOW|RTLD_LOCAL)`, and unloaded on ABI mismatch (`LibavH264EncoderClient.cpp:97-131`).
- **dlopen search order** (`LibavH264EncoderClient.cpp:17-31`):
  1. `$APERTAR_H264_LIBAV_PLUGIN`
  2. `<dir of /proc/self/exe>/apertar-h264-libav.so`
  3. `/home/pi/ApertarCore-build/apertar-h264-libav.so`
  4. the bare name (system linker path)
- **Fallback backend**: an `ffmpeg` subprocess fed through a pipe (`-an`, no timestamps). It is used if libav fails on software boards, or when `APERTAR_H264_BACKEND=pipe` is set. Audio is then refused; hardware boards refuse the pipe backend (`CameraController.cpp:3977-3980,4054-4100,4403-4410,5627-5631`).
- **Other environment variables**: `APERTAR_H264_SIZE`, `_BITRATE`, `_CRF`, `_QP`, `_PRESET`, `_TUNE`, `_MAXRATE`, `_BUFSIZE`, `_X264_PARAMS`, `_THREADS`, `_PIPE_BYTES` (`CameraController.cpp:2779,4340-4456`).
- **Resolutions**: 1920x{1080…752} or 2560x{1440…1004} crop sets (`:252-275`). Default 2560x1440 in software, 1920x1080 in hardware (`:2768-2797`).
- **Capture resolution forced per sensor**: IMX294 4144x2176, IMX585 3840x2160, IMX577 4056x2160, IMX477 2028x1080 (`:1890-1906`).

**ProRes** (`src/prores/`)
- **Plugin**: `apertar-prores-libav.so` (MODULE, `CMakeLists.txt:152-169`), ABI 2 (`ProresPluginApi.hpp:5-25`). Symbols `apertar_prores_{abi,create,encode,finish,destroy}` (`ProresPlugin.cpp:13-56`).
- **dlopen search order** (`ProresRecorder.cpp:25-50`):
  1. `$APERTAR_PRORES_PLUGIN`
  2. exe dir
  3. `/home/pi/ApertarCore-build/apertar-prores-libav.so`
  - No bare-name fallback, and `dlerror` is not reported.
- **Encoder**: software libavcodec `prores_aw`, `mov` container (`ProresEncoder.cpp:917-926`).
  - Profiles Proxy, LT, 422 (Standard), HQ; no 4444 (`ProresPlugin.cpp:17`).
  - Input is ISP RGB48. A NEON + thread-pool CSC converts to yuv422p10 BT.709 limited range, or a "fused" path is used with a patched libavcodec (`ProresEncoder.cpp:940-1015`; `ProresColor.cpp`).
  - Log gamma is applied in the ISP (§7).
- **Recorder**: 4 frame threads; zero-copy borrow of camera buffers; an encode failure latches `RecordingFailure` (`ProresRecorder.cpp:59-143`).
- **I/O**: `AVIO_FLAG_DIRECT` with a large `pkt_size`, optional `sync_file_range`, and a writer thread (`APERTAR_PRORES_*` env vars, `ProresEncoder.cpp:1086-1200`).
- **Recovery sidecar**: `_recovery.json` is written and fsync'd at open (`:1243-1290`).
- **`ProresRepair`** rebuilds a missing moov from `icpf` frame headers (`ProresRepair.cpp:132-389`). **Nothing ever calls it** (verified by grep), despite the sidecar text promising repair "on the next start" (`ProresEncoder.cpp:1275`).

### Audio (`src/audio/`)
- **Capture**:
  - libasound is dlopened only when recording (`TimestampedAudioCapture.cpp:41-49`).
  - Device is the user's choice, default `"default"`; `plughw:` is rewritten to `hw:` (`:69`).
  - Formats S16, S24_3LE, S24, S32, FLOAT (`:93-97`); 48 kHz preferred.
  - `SND_PCM_NONBLOCK`, 100 ms latency, MONOTONIC timestamps (`:188-196`).
  - First-sample time is converted to BOOTTIME (`:217-228`).
  - xruns are handled with `snd_pcm_recover`.
- **`RecordingClock.hpp`**:
  - Offset REALTIME − BOOTTIME, captured once per take (`:34-48`).
  - fps 23.976 / 29.97 / 59.94 / 119.88 are mapped to n/1001 (`:13-19`).
  - Timecode: RecRun = 00:00:00:00; FreeRun = wall-clock time of day (`:50-61`).
- **`AudioRecordingSession`**:
  - Captures to `<clip>/audio_capture.raw`, then builds `<clip>/<clip>.wav` at stop: RIFF or RF64, with `bext` (TimeReference = samples since midnight) and `iXML` (`:233-235,739-819`).
  - Live monitoring through a forked `aplay` (`:267-287`).
- **A/V sync**:
  - Video frames report their sensor timestamps (`observeVideoFrame`).
  - At finalize, audio is trimmed or padded to the first video frame and cut at the video end.
  - Gaps are filled with silence.
  - Drift of 20–2000 ppm is resampled on takes ≥10 s (`:342-356,427-439,523-635`).
  - **The raw file is deleted even if building the WAV fails** (`:368-376,566-575`).

### Gyro sidecar (`src/hardware/Mpu6050RecordingSession.cpp`)
- Supported IMUs: MPU6050/6500, BMI160, BMI270, ICM42688P over `/dev/i2c-N`. Defaults: 500 Hz, FIFO for MPU only.
- Output: Gyroflow GCSV v1.3 `<clip>/<clip>.gcsv`.
  - t is in µs relative to the first video frame's sensor timestamp, plus `sync_offset_ms` (`:1418-1465,2242-2272`).
- **All samples stay in RAM until stop**; a crash means no file (`:1991,2196-2285`).
- A gyro failure does not abort the recording (`CameraController.cpp:5555-5568`).

---

## 6. Stills

- **Source**:
  - Frames are taken from the RAW stream of the normal VideoRecording + Raw configuration.
  - Photo mode is a full reconfigure.
  - In H.264/ProRes modes, `capturePhoto` reconfigures with `photoStreamOverride_` (`CameraController.cpp:5693-5700,5985`), and the next recording reconfigures back (`:5533`).
- **Flow**: `capturePhoto` (count 1–10; forced to 3 when bracketing) → `queuePhotoCaptureLocked` → `CameraSession::capturePhoto` (pending descriptors, max 12, `:7538`) → `capturePhotoFrame` (RAW copy in the callback, `:6958-7179`) → `PhotoCaptureWriter` thread (`:5018-5224`).
  - The busy guard refuses new captures while anything is pending (`:5400-5410`).
- **Formats**: `Dng`, `Jpeg`, `Png`, `Tiff`, `DngJpeg`, `DngPng`, `DngTiff` (`Types.hpp:70-78`).
  - **DNG stills are always 16-bit unpacked and uncompressed** (`prepare16BitDngStillFrame` `:1641-1691`).
  - **Processed stills** are rendered on the CPU from RAW, not from the ISP:
    1. bilinear demosaic, single-threaded (`processRawFrameToRgbStill` `:1532-1639`);
    2. black level subtraction, WB gains, CCM (from request metadata or the bracket lock), then the tuning `rpi.contrast` gamma curve as a 64K LUT, with sRGB as fallback (`StillColorProcessing.hpp:18-70`; `:7152-7163`).
  - JPEG: 8-bit, quality 92 (`kPhotoJpegQuality` `:1025`), turbojpeg or libjpeg, sRGB ICC embedded.
  - PNG: 16-bit, stored-zlib (uncompressed), sRGB/gAMA chunks.
  - TIFF: 16-bit uncompressed with ICC (`:1693-1880`).
  - DNG+X writes the DNG first (`:5172-5207`).
- **`AtomicStillFile.hpp`**:
  1. `mkostemp("<final>.writing-XXXXXX")`;
  2. 1 MiB write loop;
  3. size check, `fchmod 0644` (errors ignored on FAT), fsync;
  4. `renameat2(RENAME_NOREPLACE)`;
  5. directory fsync;
  6. unlink on failure (`:18-98`).
  - Orphan `.writing-*` files are never cleaned up.
- **Naming**:
  - Stills: `<root>/Photos/Still_yy-mm-dd_C####.<ext>`, with an in-memory counter plus an existence check (`:924-966`).
  - Brackets: `_BRm`, `_BR0`, `_BRp` suffixes. The legacy `_EVm1/_EV0/_EVp1` are still checked (`:913`).
  - Timelapse: `<root>/Timelapse_yy-mm-dd_C####/<folder>_#########.<ext>` (`:968-1015`).
- **Timelapse** (`startTimelapse` `:8302-8388`, `timelapseLoop` `:8447-8500`):
  - Interval 0.1–86400 s, rounded to 0.1 s; also caps the shutter (`timelapseExposureLimitUs`).
  - The loop queues a shot (or skips it while the previous one is busy), then waits the interval after queuing, so timing is not wall-clock anchored and drifts.
  - Formats must be single-file (`photoFormatIsTimelapseSafe` `:1154`).
- **Long exposure** (up to 30 s or the sensor maximum, `:5879-5889`):
  - "Long" means photo mode + long exposure + manual shutter >66.667 ms (`:1995-2001`).
  - The preview stays at ≤66.7 ms. The long shutter goes on exactly one request, then preview controls are restored (`:6545-6563`).
  - Frame matching ±max(1 ms, 1%). Timeout max(10 s, 3×shutter+5 s). Preview is hidden during the exposure (`:6636-6649`).
  - Normal still mode caps the shutter at 1/min(24, fps) (`:569-574`).
- **Bracketing** (`StillBracketing.hpp:8-19`):
  - Exposures {base/2^EV, base, base×2^EV}; EV between 1/3 and 3, rounded to 1/3; must fit within the sensor's exposure limits.
  - AE gain, WB and CCM are locked from preview, then settled, then a one-request pulse is taken per shot (`:6508-6563`).
  - Disabled whenever a timelapse interval is saved (`usesStillBracketing` `Types.hpp:164-167`).
- The self-timer exists only in the UI's QML. Core stores the setting but ignores it.

---

## 7. Colour (summary)

- **`ColorProfileConfig`** (`src/color/ColorProfileConfig.cpp`):
  - Reads `$APERTAR_COLOR_PROFILE_CONFIG`, else `/home/pi/apertar-color-profiles.conf` (`:232-237`), and reloads when the file's mtime changes.
  - INI format, one `[section]` per profile. Keys: `match`/`sensor`, `illuminant1/2`, `ccm1_kelvin`/`ccm2_kelvin`, `color_matrix1/2`, `forward_matrix1/2`, `ccm`, `ccm1`, `ccm2` (`:279-363`).
  - Built-in IMX585 fallback (`:239-271`).
  - Also parses the active sensor tuning (YAML; `APERTAR_SENSOR_TUNING_FILE` or `LIBCAMERA_RPI_TUNING_FILE`, `:613-657`): `rpi.agc` metering modes, `rpi.contrast` gamma, `rpi.black_level`, `rpi.awb` ct_curve plus a calibrated check, and `rpi.ccm`.
  - Derives DNG ColorMatrix/ForwardMatrix from these (`:743-856`).
  - Feeds `activeTuningHasCalibratedWhiteBalance` and `activeTuningExposureMeteringModes` (`:887-894`).
- **`ProresIspProfile`** (`src/color/ProresIspProfile.cpp:118-237`):
  - For non-Standard profiles it writes `$HOME/.cache/apertar-prores/<profile>.json`: CCMs × gamut matrix, flat saturation, `rpi.contrast` replaced by the log OETF (257 points), HDR tonemap off.
  - Fills `PreviewExposureReference` (decode/display curves and `toRec709`), which is sent in settings JSON.
  - Used for both ProRes recording and cDNG preview colour (`activeIspColorProfile` `Types.hpp:169-176`). Still mode is always Standard.
- **Profiles** (`include/apertar/core/ProresColorProfile.hpp:8-76`): Standard (Rec709 / tuning gamma), ArriLogC4, SonySLog3, DavinciIntermediate, P3D60Linear.
- **`src/prores/ProresColor`**: RGB48 → yuv422p10 CSC. The GpLog2 / BmdFilmGen5 CPU LUT paths are dead, because the plugin always passes `Display` (`ProresPlugin.cpp:24`).

---

## 8. Hardware I/O (`src/hardware/`)

### Common to all classes
- **GPIO** goes through the raw kernel GPIO chardev uAPI v2 (`linux/gpio.h`, `GPIO_V2_GET_LINE_IOCTL`). **No libgpiod is used.**
- **I2C** is raw `/dev/i2c-N` with `I2C_SLAVE`. Only the MPU uses `I2C_RDWR`.
- **Config file**: the first existing of `$APERTAR_HARDWARE_CONFIG`, `/home/pi/apertar-hardware.conf`, `/boot/firmware/apertar-hardware.conf`, `/boot/apertar-hardware.conf`. That list is copy-pasted into every class, the app (`ApertarCoreApp.cpp:4251-4269`) and the embedded Python (`:3397-3411`).
- **Default template sections** (`ApertarCoreApp.cpp:4291-4403`): `[ina219] [cfexpress_hat] [storage] [display] [run_script] [imu] [pcf8574] [gpio] [trigger_output] [recording_indicator]`.
- **Input pattern**: a polling thread per class; open retried every 1 s; reopen after 250 ms on error.
- **Callbacks** run synchronously on the poll thread and take `hardwareActionMutex_` (`ApertarCoreApp.cpp:8458-8466`). A slow command stalls polling.

### Per-class summary

| Class | Hardware / bus | Defaults | Config section(s) | Notes / ref |
|---|---|---|---|---|
| `GpioInput` | Pi GPIO buttons and quadrature encoders via `/dev/gpiochipN`. `chip=auto` scores rp1 +100, bcm +90 | active_low, pull-up, poll 12 ms, debounce 60 ms; encoder steps 4 | `[gpio_buttons]`/`[gpio]`/`[grove_digital]`/`[grove_buttons]` (keys `gpio_N`, `dN`, …); `[gpio_encoders]`/`[grove_encoders]` (`encoderN_a/b/cw/ccw/press`). `enabled` defaults false | Actions fire on the press edge; encoders are polled (can miss steps). `GpioInput.cpp:209-301,388-496,505-581,691-738` |
| `Pcf8574Input` | PCF8574 I2C 8-bit expander buttons; writes 0xFF, then reads a byte | bus 1 / 0x20 in code (template bus 10), poll 40 ms | `[pcf8574]`/`[pcf8574_buttons]`; the section's presence enables it; `pinN` | Whole-byte debounce. `Pcf8574Input.cpp:108-138,346-443,498-521` |
| `NeoRotary4Input` | Adafruit seesaw quad rotary (ATtiny817); HW ID 0x87; encoder delta registers 0x11/0x40+i; button pins {12,14,17,9} | bus 1, 0x49, poll 30 ms, 8 ms register delay, max 8 events per poll (excess dropped) | `[neorotary4]`/`[neo_rotary4]`/`[neo_rotary_4]`; `encoderN_cw/ccw/press` | About 70 ms per cycle. `NeoRotary4Input.cpp:27-38,383-435,470-585,650-711` |
| `GroveAnalogInput` | Grove Base Hat ADC, 12-bit (reg 0x10+ch) | bus 1, 0x04, poll 80 ms, deadband 32 | `[grove_analog]`/`[grove_adc]`/`[analog_controls]`; `aN=target`, min/max/step/presets | App maps targets iso/fps/resolution/shutter/wb/focus_peaking_threshold/zebra_threshold/volumes/opacity (`ApertarCoreApp.cpp:8480-8606`). `GroveAnalogInput.cpp:125-182,276-339,384-477` |
| `Mpu6050RecordingSession` | IMU (several drivers) | see §5 | `[imu]` plus `[gyro]` or `[<driver>]` | Auto-probes every `/dev/i2c-0..32` at 0x68/0x69 (`:1543-1600`) |
| `StandbyPowerButtonInput` + `PowerButtonGesture` | Pi 5 on-board power button, evdev `pwr_button` (`KEY_POWER`) | — | none; started only when not simulating | Single press fires immediately; repeat <80 ms = bounce; double = release ≤500 ms + second press 80–500 ms (`PowerButtonGesture.hpp:5-31`). App: in Standby → wake; single → `power_button_press` event (UI); double → `enter_standby` (`ApertarCoreApp.cpp:8608-8628`) |
| `TriggerOutput` | One GPIO line (consumer `apertar-trigger`, optional open-drain) or a PCF8574 pin | GPIO17, active-low, 80 ms pulse; events record_start, still, timelapse_frame | `[trigger_output]`/`[trigger]`/`[capture_trigger]`/`[hotshoe]`; needs `enabled=true` | One pulse per recording **start**, not per frame, and no stop pulse; up to 4 queued pulses (`TriggerOutput.cpp:121-175,276-343,450-521`). Driven from `handleTriggerEvent` substring matching |
| `RecordingIndicatorOutput` | Tally LED on GPIO (`apertar-rec-led`) or a PCF pin | — | `[recording_indicator]` (+ aliases), or auto-detected from `pinN=`/`dN=` set to an LED alias in the button sections | Steady on while recording or during a still exposure; 320 ms flash per photo or timelapse frame (`RecordingIndicatorOutput.cpp:118-129,274-387,491-560`) |
| `HardwareScriptRunner` | Runs user shell scripts | — | `[run_script]` `path`/`path1`..`path5` in `editableHardwareConfigPath()` (env or `/home/pi/...` only) | Absolute readable file, exec bit not needed. `posix_spawn("/bin/bash","--",path)`; cwd = script dir; stdin `/dev/null`; fds ≥3 closed; own process group; full environment inherited; no args. **No per-script timeout.** Stop: SIGTERM, 2 s, SIGKILL. At most 5 jobs (`HardwareScriptRunner.cpp:38-255`) |

**Security note**: `POST /api/config` can rewrite `[run_script]` paths. The web server binds 0.0.0.0 and no auth was found (UNCONFIRMED; the other agent covers the web server).

### `ButtonActionList.hpp`
- At most 6 actions per mapping (comma-separated), at most 5 scripts (`:14-15`).
- Script actions: `run_script`/`script` (slot 0 = all), `run_scriptN`/`scriptN`/`run_script_N` (`:17-33`).
- Token normalisation: lowercase; `ev-N` → `evmN`, `ev+N` → `evN`; `-`, space and `.` become `_` (`:35-55`).
- LED aliases, which must be mapped alone (`:57-62`): `recindicatorled`, `rec_indicator_led`, `recording_indicator`, `recording_indicator_led`, `record_led`, `rec_led`, `tally`, `tally_led`.
- Disable tokens: `none`, `off`, `disabled` (`:102`).

### Canonical action names
Alias normalisation is copy-pasted in `GpioInput.cpp:108-202`, `Pcf8574Input.cpp:140-242` and `NeoRotary4Input.cpp:121-215`. Canonical names:

| Group | Actions |
|---|---|
| Capture and mode | `capture`, `record_toggle`, `photo`, `timelapse`, `eject`, `still_mode`, `standby` |
| UI pages (publish a `hardware_action` event only) | `settings`, `clip_browser`, `quick_menu`, `zoom_toggle` |
| Monitoring toggles | `focus_peaking`, `zebra`, `false_color`, `guides`, `center_marker`, `grayscale`, `smpte`, `external_monitor`, `date_time_overlay`, `audio_meter` |
| Stepping | `fps`/`fps_up`/`fps_down`, `resolution`/`resolution_up`/`resolution_down`, `iso`/`iso_up`/`iso_down`, `shutter`/`shutter_up`/`shutter_down`, `wb`/`wb_up`/`wb_down` |
| Scripts | `run_script[N]` |

**Extra actions parsed in the app** (`ApertarCoreApp.cpp:8660-8955`):
- `ev_up`/`ev_down` (±1/3 EV), `ev<N>`, `evm<N>`;
- `fps<N>`, `resolution<W>x<H>`, `iso<N>`;
- `shutter…<N>s`, `shutter_angle<N>`, `shutter_speed<N>`, `wb<N>` (2500–8000 K).

**What the main actions do**:
- `capture`: stops a running timelapse; in photo mode, starts a timelapse or takes a photo; otherwise toggles recording.
- In Standby, any press only wakes; rotations are ignored (`:8642-8657`).

---

## 9. CFexpress automount and the media path

### How Core learns the media path
Only from `--media` (default `/media/RAW`). `start-apertar-core.sh` passes `$APERTAR_MEDIA_ROOT` or `/media/RAW`.
- Core's C++ never reads `[storage] mount_path`.
- Presence: scans `/proc/mounts` (`isMountedPath` `ApertarCoreApp.cpp:2014-2046`).
- Free space: `std::filesystem::space`, shown in state only, never enforced (`:7781-7813`).

### Core and `apertar-cfe-automounter`
Core does not embed, install, spawn or talk to it. A grep finds no automounter references in Apertar-Core.

### Core's own media operations
- **Drive scan**: `lsblk -P -b -o NAME,PATH,TYPE,SIZE,FSTYPE,LABEL,MODEL,TRAN,RM,RO,MOUNTPOINT,PKNAME`, excluding `/` and `/boot*` disks, cached 3 s (`:2254-2390`).
- **Labels**: `CFE-RAW`/`RAW` → CFExpress, `SSD-RAW`/`NVME-RAW` → NVMe, `USB-RAW` or `/dev/sd*` → USB (`:1983-2012`).
- **`mount_media`**: `sudo -n mkdir -p` + `sudo -n mount` (`:3604-3708`).
  - exfat/vfat: `uid=1000,gid=1000,umask=0002`.
  - ntfs: `ntfs3` with the same options, with an `ntfs-3g` fallback.
- **`eject_media`** (`:3710-3761`):
  1. `sync -f`, `sudo blockdev --flushbufs` (`:3346-3355`).
  2. `udisksctl unmount`, plus `udisksctl power-off` for non-NVMe; fallback is plain `umount` without sudo.
  3. For NVMe: `sudo sh -c "echo 1 > /sys/bus/pci/devices/<addr>/remove"` (the PCI address is taken from `udevadm info`) (`:3325-3378`).
  4. Then **`startNvmeReinsertWatcherAtPath`**. This is an **embedded Python script** launched as `APERTAR_MEDIA_ROOT=<path> python3 -c '<script>' &` (`:3380-3602`). The script:
     - reads `[cfexpress_hat]` (`enabled`, `bus` (default 10), `address` (default 0x34)) and `[storage]` (`mount_path`, overridden by the env var, and `pcie_controller`, default `1000110000.pcie`);
     - polls the HAT's insert bit over smbus for up to 60 s (wait for insert, then for the bit to clear);
     - resets PCIe (brcm-pcie unbind/bind, then `/sys/bus/pci/rescan`);
     - mounts the highest `nvmeXnYpZ` partition by `blkid` type: ntfs3/exfat with uid/gid (no umask), ext4 plain, no vfat.
- **`format_media`**: exFAT/FAT32/NTFS only; ext4 is rejected (`:3763-3867`).

### Apertar-UI `src/CfeAutomounter.cpp` (781 lines, no header)
- **Build**: `add_executable(ApertarCfeAutomounter)` with output name `apertar-cfe-automounter`, linking only Threads (`Apertar-UI/CMakeLists.txt:149,159-167`).
- **No `install()` rule and no systemd unit in either repo.** The `/usr/local/libexec` install and the service are manual or Pi-only (apertar-kb says so; UNCONFIRMED).
- **Config**: the same candidate list. `[cfexpress_hat]` `enabled`/`bus`/`address`; `[storage]` `mount_path`/`pcie_controller`. Defaults: bus 10, 0x34, `/media/RAW`, `1000110000.pcie`. `--check-config` prints and exits (`CfeAutomounter.cpp:38-191,756-780`).
- **Must run as root**: it calls `mount(2)` / `umount2` directly and writes sysfs.
- **Detection**: polling only, no udev or netlink.
  - HAT I2C byte read every 100 ms: bit0 = insert, bit1 = eject, 0x69 = invalid, 5 s backoff after errors.
  - Insert falling edge → `mountPcie`; eject falling edge → `unmountPcie`.
  - `/proc/self/mountinfo` read every 500 ms drives the HAT LED.
  - Partitions are found by scanning `/sys/class/block` for the highest `nvmeXnYpZ` (`:282-329,402-421,484-555`).
- **Mount**: `blkid` type; `MS_NOATIME`; ntfs3 with uid/gid (no umask); exfat/vfat with uid/gid/umask 0002; ext4 plain (`:591-630`).
- **Eject**: `syncfs`, `BLKFLSBUF`, `umount2`, then PCI remove (the canonical sysfs address, or the last class-0x0108 device), then `udevadm settle` (`:674-723`).
- **Ready file**: `/run/apertar-cfe/ready` is written after the startup mount attempt and removed on SIGTERM; no unmount on stop (`:530-560`).
- Only the UI's `MediaStatusBridge` checks the ready file, and that code path is never called (`Apertar-UI/src/MediaStatusBridge.cpp:742-748`).
- The UI hardcodes `/media/RAW` (`MediaStatusBridge.hpp:136`) and mounts by itself with `sudo mount`; it delegates eject and format to Core.

---

## 10. Scripts and config

### `Apertar-Core/scripts/start-apertar-core.sh` (21 lines)
- `set -euo pipefail` (`:2`).
- `CORE_BIN=${APERTAR_CORE_BIN:-/home/pi/ApertarCore-build/apertar-core}` (`:4`): runs straight from the build directory, which is why the plugin exe-dir lookup works.
- `MEDIA_ROOT=${APERTAR_MEDIA_ROOT:-/media/RAW}` (`:5`); `SOCKET_PATH=${APERTAR_SOCKET_PATH:-/tmp/apertar-core.sock}` (`:6`).
- Exits 1 if the binary is not executable (`:8-11`).
- If `APERTAR_TUNING_FILE` is set, it exports `LIBCAMERA_RPI_TUNING_FILE` from it. The comment says saved custom selections win; otherwise Core picks `defaults-pisp` or `defaults-vc4` under `/home/pi/Tuning-Files` (`:13-18`).
- `mkdir -p` the socket directory (`:20`).
- `exec "$CORE_BIN" --socket "$SOCKET_PATH" --media "$MEDIA_ROOT"` (`:21`). No `--web-*` flags, so defaults are 0.0.0.0:8000.

### `Apertar-Core/config/apertar-core-capture-priority.conf` (3 lines)
It is a systemd unit drop-in:
```
[Service]
# Permit only a bounded, non-real-time boost for the camera callback thread.
LimitNICE=-5
```
This lets the libcamera callback thread `setpriority(-5)` without `CAP_SYS_NICE` (`CameraController.cpp:6590-6600`). The service unit itself is not in this repo (UNCONFIRMED where it lives).

### Environment variables Core reads (first reference)

| Area | Variable(s) | Ref |
|---|---|---|
| cDNG | `APERTAR_CDNG_{QUEUE_FRAMES,WORKERS,WORKER_NICE}` | `CameraController.cpp:3330,3343,3359` |
| cDNG | `APERTAR_CDNG_{TILE_ROWS,PROFILE_DETAIL}` | `CdngEncoder.cpp:55,72` |
| LossyDNG | `APERTAR_LOSSYDNG_{WORKERS,ASYNCWRITE,WRITER_BYTES}` | — |
| H.264 | `APERTAR_H264_*` (§5) | — |
| Plugins | `APERTAR_H264_LIBAV_PLUGIN`, `APERTAR_PRORES_PLUGIN` | — |
| ProRes | `APERTAR_PRORES_{CAMERA_BUFFERS,CACHED_DMABUF,CSC_THREADS,ISP_FORMAT,ODIRECT,QP_PRED,THREADS,TRANSFER,WRITEBACK,WRITER_THREAD,WRITER_QUEUE,WRITER_QUEUE_MB,WRITER_SLOW_MS}` | — |
| Camera | `APERTAR_RAW_CACHED_DMABUF` | — |
| MLV | `APERTAR_MLV_ENABLE_NEON_PACKER`, `APERTAR_MLV_HAS_NEON` | — |
| Colour | `APERTAR_COLOR_PROFILE_CONFIG` | — |
| Tuning | `APERTAR_DEFAULT_TUNING_DIR`, `APERTAR_SENSOR_TUNING_FILE`, `LIBCAMERA_RPI_TUNING_FILE` | — |
| Config / media | `APERTAR_HARDWARE_CONFIG`, `APERTAR_MEDIA_ROOT` (embedded Python only) | — |
| Paths | `XDG_CONFIG_HOME`, `HOME` | — |
| Overrides | `/home/pi/.apertar-tuning` file (ProRes overrides) | `ProresEncoder.cpp:782-818` |

---

## 11. Bugs, inconsistencies and dead code

### Concurrency and control flow
1. **Command-event capture is process-global.** `handleRequest` sets `collectingCommandEvents_` before taking `commandMutex_` (`ApertarCoreApp.cpp:7061-7075` vs `:9093`). With two socket clients:
   - B's request clears A's pending events, and one client's reply can carry the other's events;
   - camera events that fire during any command go only to that requester's reply, not as a broadcast (except the allow-listed types).
2. **`UI.conf` is re-read every second** by `wait()` (`:7037`), and on many commands and hardware actions. That is file I/O on hot-ish paths.
3. **TOCTOU in `CameraController::startRecording`**: `timelapseActive()` is checked before taking `mutex_` (`CameraController.cpp:8222-8228`).
4. **The H.264 audio-sync hook is in a different place from RAW and ProRes**: a recorder callback (`:5619-5621`) instead of `recordProcessedPreviewFrame`. Cadence is tracked after enqueue for H.264 but before enqueue for ProRes (`:7415` vs `:7468`).
5. **`recordRawFrame` builds metadata before the capacity check**, and does the full memcpy while holding `recordingFrameMutex_` on the libcamera thread (`:6918-6936`, `:6651`).
6. **Hardware callbacks run synchronously** on the poll threads under `hardwareActionMutex_`, so encoder steps can be lost during slow reconfigures.

### Logic bugs
7. **Timelapse loses the skip reason**: `queueError = lastError_;` overwrites "Previous still is still exposing" (`:8473` then `:8478`). The cadence also drifts (wait after queue, `:8493-8496`).
8. **`setErrorLocked` contains a no-op state self-assignment** (`:8774`).
9. **`sanitizeSettingsForSensor` repeats itself**: the processed-format check appears twice in a row, and `rawBitDepth = 10` is set three times (`:2711-2716`, `:2724-2725`).
10. **The mono `R16` branch is unreachable**, because `normalizeRawBitDepth` never yields 16 (`:243-250`, `:6102-6105`).
11. **`makeRequests` computes `processedYuvMode` without `!photoStreamOverride_`**, inconsistent with `configureAndStart` (`:6459` vs `:5986`). So in still-override mode, a processed format sizes requests by the H.264/ProRes limits.
12. **`AfTrigger=Start` is re-sent with every control update** in AF Auto mode (`:2132-2138`), so any ISO/WB change re-triggers a focus scan (UNCONFIRMED effect).
13. **`DefaultTuningSelection::defaultDirectories` lists the same `defaults-pisp`/`-vc4` directory twice** when no override is set (`DefaultTuningSelection.hpp:70-73`).
14. **Board detection is duplicated**: `tuning::detectPipeline` and `recordingCapabilities` each parse `compatible` separately. `recordingCapabilities` stops at the first readable file even if it contains no match (`RecordingCapabilities.hpp:40-46` vs `DefaultTuningSelection.hpp:33-43`).
15. **Camera selection is "first non-USB"** with no user choice. Sensor family is a substring of the camera id; there is no IMX492 support.

### Media and automount
16. **No mount or free-space check in Core** before record, capture or timelapse. With nothing mounted, writes land in `/media/RAW` on the root filesystem. Only the UI gates this.
17. **Two remount mechanisms race**:
    - Core's NVMe eject always spawns its embedded Python watcher, while the separately installed `apertar-cfe-automounter` reacts to the same HAT insert edge. Both reset PCIe and mount.
    - Mount options differ across Core C++, Core Python, the automounter and the UI (umask, vfat, ntfs-3g fallback).
    - The eject error string in `lower` is never lowercased (`ApertarCoreApp.cpp:3748`); the fallback `umount` has no sudo.
    - If the watcher fails to spawn, eject is reported as failed even though the media is already detached (`:3742-3745`).
18. **`[storage] mount_path` is honoured by the automounter but ignored by Core and the UI**, so changing it splits the system.

### Formats
19. **ProRes repair is never invoked**; the `_recovery.json` sidecar is never deleted after a clean close.
20. **Plugin search paths omit the CMake install directory** `lib/apertar-core`. They only work because the binary runs from `/home/pi/ApertarCore-build` (`LibavH264EncoderClient.cpp:17-31`, `ProresRecorder.cpp:25-50`).
21. **LossyDNG async writer errors never become a RecordingFailure** (`LossyDngEncoder.cpp:230-233`), so a full card (ENOSPC) in lossy mode is silent.
22. **Audio**: the raw capture is deleted even if building the WAV failed (`AudioRecordingSession.cpp:368-376`).
23. **MLV frame count is patched only at close.** The gyro sidecar is RAM-only until stop. H.264 MP4 is non-fragmented. A crash therefore leaves broken or empty files.
24. **Black level defaults disagree**: 200 vs 206 (`CdngEncoder.cpp:40` vs `.hpp:47`). LossyDNG and MLV use the red channel's black level for all CFA sites.
25. **Stats are mislabeled**: `discardedOnStopFrames_` is never incremented (`CameraController.cpp:3304,3509,3898`), and the ProRes stats labels are swapped (`ProresRecorder.cpp:155-156`).
26. **Record and still time-left estimates ignore** compression, bit depth, 16-bit DNG stills and uncompressed PNG/TIFF (`ApertarCoreApp.cpp:4743-4781`).

### Hardware
27. **GPIO17 is used twice in the default template**: by `[trigger_output]` and by `[recording_indicator]`, so the second fails with EBUSY.
28. **Three objects share PCF8574 shadow registers**: input, trigger and LED each keep their own cache and can clobber each other.
29. **Code defaults differ from the template**: PCF/IMU bus 1 vs 10, IMU enabled, gyro range, trigger open_drain.
30. **`run_script` reads only `editableHardwareConfigPath()`**, while the inputs may have loaded a `/boot/firmware` file.
31. **Grove config issues**: the `channel=` key collides with the bus alias; per-channel deadband is reset whenever another key for that channel is parsed.
32. **Section headers with inline comments break** TriggerOutput, RecordingIndicatorOutput and the MPU class.
33. **Hardware config changes need a Core restart**: there is no reload.

### Duplication and dead code
34. **Duplicated logic**:
    - the config path list (about 9 copies, including Python);
    - `normalizeSingleAction` (3 copies);
    - the LED alias list (5 copies);
    - `gpioChipScore` (3 copies);
    - folder allocators (Photos, Timelapse, clip, Audio);
    - PiSP COMP1 decode (cDNG vs MLV);
    - `writeAll` (3 copies);
    - the resolution whitelist (`clampCaptureSettings` vs `validateResolution`);
    - the 1080p30 hardware H.264 limit (4 places).
35. **Dead code**:
    - `src/lossydng/LossyJpeg12.{cpp,h}` and `fastent.h` are not built;
    - unused `CdngEncoder::Metadata` fields (`asShotNeutralGains`, `colourMatrix2`, `rotationDegrees`);
    - the unused `IfdBuilder::build()`, which double-counts the offset (`IfdBuilder.hpp:108-117`);
    - the ProRes GpLog2 / BmdFilm LUTs;
    - the unused `Mpu6050RecordingSession::output_`;
    - `HardwareInputTestAccess` friend declarations with no tests in the repo;
    - stale QRAW comments and the `QRAW_LOSSYDNG_ASYNCWRITE` alias.
