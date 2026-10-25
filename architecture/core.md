# Apertar-Core

How the `apertar-core` process is built inside: threads, the control socket, the WebUI, the camera, recording, hardware I/O and the CFE watcher.

Refs are against `upstream-1.6.0` plus the fork's `.gitignore` commit (`65ccfa8`). Paths are repo-relative (`Apertar-Core/...`); `App` = `Apertar-Core/src/ApertarCoreApp.cpp`, `CC` = `Apertar-Core/src/camera/CameraController.cpp`. Config keys are in [config.md](config.md), build and plugin lookup in [build.md](build.md).

## 1. Source map

| Path | Lines | Responsibility |
| --- | --- | --- |
| `src/main.cpp` | 141 | CLI flags, signal self-pipe, start/wait/stop |
| `src/ApertarCoreApp.{hpp,cpp}` | 179 / **11025** | Orchestrator: socket dispatcher `handleCommand`, WebUI routes, UI.conf read/write, media mount/eject/format, preview fan-out, MJPEG, standby, hardware action mapping, INA219, embedded CFE Python helper |
| `src/camera/CameraController.{hpp,cpp}` | 135 / **8834** | Public camera API; inner `CameraSession` (`CC:5230`) owns libcamera; `DngRecordingQueue` (`CC:3249`), `H264PreviewRecorder` (`CC:3930`), `PhotoCaptureWriter` (`CC:5018`); settings persistence |
| `src/camera/DefaultTuningSelection.hpp` | 207 | Picks the default tuning JSON per sensor and pipeline |
| `src/camera/{ScalerCropGeometry,ExposureMetering,StillBracketing}.hpp` | 66 / 41 / 20 | Crop rectangles, metering modes, bracket exposures |
| `src/cdng/` | 1901 (`CdngEncoder.cpp`) + 410 | CinemaDNG writer, uncompressed and LJ92 lossless (`LosslessJpegEncoder.cpp`), `IfdBuilder.hpp`, `BlackLevel.hpp` |
| `src/lossydng/` | 517 (`LossyDngEncoder.cpp`) | Lossy DNG 3:1 / 5:1. `LossyJpeg12.{cpp,h}` (1684) and `fastent.h` are **not built** (absent from `CMakeLists.txt:69-96`) |
| `src/mlv/MlvEncoder.cpp` | 1299 | Magic Lantern MLV writer |
| `src/video/` | 526 (plugin) + 151 (client) + 382 | H.264: dlopen client (in core), `LibavH264EncoderPlugin.cpp` (built as `apertar-h264-libav.so`), `NativeV4l2H264Encoder.hpp` (Pi 4), `H264Hardware.hpp` |
| `src/prores/` | 1661 (`ProresEncoder.cpp`) + 393 + 388 + 159 | ProRes: `ProresRecorder` (dlopen client, in core); encoder, colour, repair in `apertar-prores-libav.so` |
| `src/color/` | 912 (`ColorProfileConfig.cpp`) + 741 | DNG matrices from `~/apertar-color-profiles.conf` and tuning; derived log ISP tuning (`ProresIspProfile.cpp`); still sRGB profile |
| `src/audio/` | 829 + 246 | ALSA capture (`TimestampedAudioCapture`), WAV/BWF writer (`AudioRecordingSession`), `RecordingClock.hpp` |
| `src/hardware/` | 2301 (`Mpu6050RecordingSession.cpp`), 751, 746, 717, 698, 529, 486, 258, 76 | GPIO, PCF8574, NeoRotary4, Grove ADC, IMU gyro sidecar, power button, trigger output, tally LED, script runner |
| `src/ipc/` | 254 + 299 | `ControlProtocol` (flat JSON parser), `ControlServer` (AF_UNIX, fd passing) |
| `src/web/` | **11618** (`WebControlPage.cpp`) + 394 | HTTP server; the whole WebUI is one raw string literal; `icons/*.png` served from disk |
| `src/util/` | 98 + 119 + 30 + 26 | `AtomicStillFile.hpp`, `SettingsFile.hpp` (atomic write, QLockFile-compatible lock), drop and failure latches |
| `include/apertar/core/` | 339 (`Types.hpp`) + 108 + 79 + 31 | `CaptureSettings`, enums, `RecordingCapabilities.hpp` (per-board format matrix), ProRes colour profiles |
| `scripts/start-apertar-core.sh` | 21 | Service launcher. Byte-identical to `/home/pi/start-apertar-core.sh` (Pi, 2026-10-25) |
| `config/apertar-core-capture-priority.conf` | 3 | systemd drop-in `LimitNICE=-5`. Installed on the Pi (Pi, 2026-10-25) |
| `src/prores/README.md`, `src/prores/ffmpeg/*` | — | **On the Pi image, missing from git** (Pi, 2026-10-25): `README.md`, `apertar-prores-ffmpeg8.patch`, `build-private-ffmpeg.sh`, `PROVENANCE.md` |

No TODO/FIXME/XXX comments exist in `src/` or `include/`.

## 2. Process structure

### 2.1 `main()`

| Flag | Default | Ref |
| --- | --- | --- |
| `--socket PATH` | `/tmp/apertar-core.sock` | `src/main.cpp:56-58`, `src/ApertarCoreApp.hpp:33` |
| `--media PATH` | `/media/RAW` | `src/main.cpp:60-62`, `.hpp:34` |
| `--web-bind ADDR` | `0.0.0.0` | `src/main.cpp:64-66`, `.hpp:35` |
| `--web-port PORT` | `8000`; `0` disables the WebUI; >65535 exits 2 | `src/main.cpp:68-81`, `.hpp:36` |
| `--simulate` | off; no camera, no power button, no standby helpers | `src/main.cpp:52-54` |

The Pi passes only `--socket` and `--media` (`scripts/start-apertar-core.sh:21`), so the WebUI is on `0.0.0.0:8000`.

Signals: SIGINT/SIGTERM write one byte to a self-pipe (`src/main.cpp:13-25`, `:91-104`). A `signalThread` reads it and calls `requestShutdown()` (`:113-120`). Shutdown never runs in the handler (comment `:89-90`). Then `app.wait()` (`:129`), join, `app.stop()` (`:134`).

### 2.2 Owned objects (construction order)

`camera_`, `controlServer_`, `webServer_`, `gpioInput_`, `standbyPowerButton_`, `groveAnalogInput_`, `neoRotary4Input_`, `pcf8574Input_`, `hardwareScriptRunner_`, `recordingIndicatorOutput_`, `triggerOutput_`, `soundRecorder_` (`src/ApertarCoreApp.hpp:110-124`). The constructor wires callbacks (`App:6781-6794`):

| Source | Callback |
| --- | --- |
| camera events / preview frames | `publishEvent` / `enqueuePreviewFrame` |
| GPIO, NeoRotary4 | press → `handleHardwareInputAction(a)`; rotation → `handleHardwareInputAction(a, false)` |
| PCF8574 | `handleHardwareInputAction(a)` |
| power button | `handlePowerButtonPress(double)` |
| Grove ADC | `handleHardwareAnalogInput` |

The `CameraController` constructor loads persisted settings and adopts `LIBCAMERA_RPI_TUNING_FILE` when none is saved (`CC:7577-7614`).

### 2.3 Startup sequence: `start()` (`App:6801-6903`)

1. Standby crash recovery, not in simulate mode: if `/run/apertar-standby-low-power/settings` exists run `sudo -n /usr/local/libexec/apertar-standby-low-power restore`; **failure aborts start** (`:6806-6814`). If `/run/apertar-standby-usb/ports` exists run `apertar-standby-usb on`; failure only logged (`:6815-6819`). Helpers: `:1541-1550`.
2. Start the preview publisher thread (`:6821-6825`).
3. Start the MJPEG thread if built with JPEG and the port is non-zero (`:6827-6836`).
4. `camera_.start(mediaRoot, simulate)`; failure stops threads and returns false (`:6838-6843`).
5. Read `~/.config/CinePi/UI.conf` and push still mode, long exposure, timelapse interval and bracketing into the camera (`:6845-6857`).
6. `controlServer_.start(socketPath, handleRequest)` (`:6859-6867`). **The socket appears only after the camera opened.**
7. `webServer_.start(bind, port, handleWebRequest)` (`:6869-6879`).
8. `triggerOutput_`, `pcf8574Input_`, `neoRotary4Input_`, `gpioInput_`, `standbyPowerButton_` (not simulate), `groveAnalogInput_`, `recordingIndicatorOutput_` (`:6881-6898`). Each reads `apertar-hardware.conf` only here: **config edits need a Core restart**.
9. Publish `{"event":"camera_state","state":"ready"}` (`:6901`).

Core writes no PID, ready or status file. `ApertarCore failed to start.` on stderr (`src/main.cpp:109`) plus exit 1 is the failure signal; systemd restarts it (`Restart=on-failure`, Pi, 2026-10-25).

### 2.4 The startup gate

Core does not implement the gate. systemd does, before Core starts:

| Piece | What | Ref |
| --- | --- | --- |
| Core drop-in | `ExecStartPre=/usr/local/libexec/apertar-wait-ui-core-start /run/apertar-ui/core-start-ready 8` | Pi, 2026-10-25 |
| Gate script source | `Apertar-UI/wait_for_ui_core_start.sh`. Args `READY_FILE` (default `/run/apertar-ui/core-start-ready`), `TIMEOUT` (default 8) | `:5-6` |
| No screen | Exits 0 at once if no `/sys/class/drm/card*-*/status` reads `connected` (writeback ignored; override `APERTAR_DRM_SYSFS`) | `:21-33` |
| Already ready | Exits 0 if the file exists | `:35-38` |
| Wait | Polls every 25 ms | `:40-52` |
| Timeout | Logs `timed out after 8 seconds; starting Core anyway.` and **exits 0** | `:54-56` |
| Writer (normal) | UI writes `ready\n` to `$APERTAR_CORE_START_READY_FILE` right after `Main.qml` loads | `Apertar-UI/src/main.cpp:405-420` |
| Writer (headless) | `run_pi_direct.sh` touches the file when no connector is connected | `Apertar-UI/run_pi_direct.sh:170-175` |
| Env + dir | `apertar-ui-direct.service`: `Environment=APERTAR_CORE_START_READY_FILE=/run/apertar-ui/core-start-ready`, `RuntimeDirectory=apertar-ui` | Pi, 2026-10-25 |

Purpose: keep Core's camera open from racing Qt's cold SD reads. The gate can only delay Core, never block it. **Confirmed** (Pi, 2026-10-25, `cmp`): `/usr/local/libexec/apertar-wait-ui-core-start` is byte-identical to `wait_for_ui_core_start.sh`.

Journal lines to look for: `Apertar Core startup gate: UI scene ready after N ms.` / `no screen` / `timed out`.

### 2.5 Threads

| Thread | Started at | Loop |
| --- | --- | --- |
| main | `src/main.cpp:129` | `wait()` (below) |
| signal | `src/main.cpp:113` | blocks on the self-pipe |
| preview publisher | `App:6825` | `runPreviewPublisher` (`App:10946-10986`) |
| MJPEG encoder | `App:6834` | `runMjpegEncoder` (`App:8194-8236`), only while web viewers exist |
| control accept + 1 per client (max 32) | `src/ipc/ControlServer.cpp:139`, `:215` | `clientLoop` |
| web accept + 1 per client (max 32) | `src/web/WebServer.cpp:228`, `:276` | `clientLoop` |
| media speed test | `App:9008` | one-shot |
| one poll thread per hardware class | each `start()` | §7 |
| libcamera callback | libcamera | `CameraSession::requestComplete` (`CC:6579`), boosted to nice −5 (`CC:6590-6600`) |
| DNG workers, H.264, ProRes writers, persister, timelapse | `CC` | §6 |

### 2.6 Main loop: `wait()` (`App:7021-7053`)

1 s tick until shutdown. Each tick:
1. Under `commandMutex_`: `camera_.checkRecordingFailure()`, the supervisor for asynchronous writer failures (`:7031-7034`).
2. Re-read UI.conf for `standbyTimeoutSeconds` (`:7037`).
3. Reset idle time while recording, timelapse, sound recording, or when the timeout changed (`:7038-7042`).
4. When idle ≥ timeout and the camera is Ready, synthesise `enter_standby` with `idle_timeout` (`:7043-7050`).

### 2.7 Shutdown: `stop()` (`App:6905-6941`)

Publish `camera_state: stopping`, then stop inputs → script runner → LED → trigger → sound recorder → camera → MJPEG → preview → web → control socket; run the standby restore helpers again.

## 3. Unix socket IPC (`/tmp/apertar-core.sock`)

### 3.1 Framing

| Rule | Ref |
| --- | --- |
| `AF_UNIX`, `SOCK_STREAM`; stale socket file is unlinked before bind; backlog 8 | `src/ipc/ControlServer.cpp:105-136` |
| One request = one line of JSON ending `\n`; `\r` ignored | `:246-264` |
| Line > 64 KiB: connection closed, no reply | `:261-262` |
| Client 33+: accepted, then silently closed | `:208-209` |
| Requests run on the client's own thread; `handleCommand` serialises them on `commandMutex_` | `App:9093` |
| All sends are `MSG_DONTWAIT`; a client that does not drain is dropped | `ControlServer.cpp:24-29`, `:176-177` |

Request shape: `{"cmd":"set_iso","id":7,"value":800}`. The parser is **flat** (`src/ipc/ControlProtocol.cpp:164-233`): every value is stored as a string; nested objects or arrays break it (a bare value runs to the next `,` or `}`, `:120-135`). `cmd` is required; `id` optional.

Reply: `{"ok":true,"id":7,...}` or `{"ok":false,"id":7,"error":"..."}` (`App:108-128`). `id` is echoed only when ≥0. Events raised while the command ran are appended **as extra lines after the reply** (`App:7055-7083`).

### 3.2 Commands handled in `handleCommand` (`App:9091-10821`)

Gating before dispatch (`App:9094-9117`, `:9208-9211`):
- `capture_photo`, `record_start`, `timelapse_start` fail while media writes are pending.
- `format_media`, `eject_media`, `mount_media`, `run_media_speed_test` fail while recording, writing or testing.
- Capture commands fail in Standby (`Wake the camera before capturing.`).
- `user_activity`, `wake`, every `set_*`, capture, record and `timelapse_*` reset the idle timer.

"SB" = reply carries `settingsBody` (`App:167-216`). "UI.conf" = Core writes the key into `~/.config/CinePi/UI.conf [General]` via `updateSharedUiGeneralSettings` (`App:1850-1935`); no event is emitted for those.

**Session, standby, meta**

| Command | Fields | Does | Ref |
| --- | --- | --- | --- |
| `user_activity` | — | Reset idle timer | `:9118` |
| `set_standby_timeout` | `value` 0–86400 s, integer | UI.conf `standbyTimeoutSeconds` | `:9120` |
| `set_standby_usb_power_off` | `enabled` true/false/1/0 | UI.conf `standbyUsbPowerOff` | `:9129` |
| `enter_standby` | `idle_timeout` (internal) | Release camera, stop preview/MJPEG, `apertar-standby-low-power all`, optional USB off | `:9138` |
| `wake` | — | Restore helpers, restart preview/MJPEG, reopen camera | `:9174` |
| `ping` | — | `"pong":true` | `:9212` |
| `help` | — | Static list (**stale**, 12 commands missing) | `:9215-9216` |
| `get_state` | — | §3.3 | `:9218` |
| `preview_subscribe` | — | Re-broadcast cached `preview_buffer` registrations + last frame | `:10796` |
| `restart_system` / `power_off_system` | — | `sudo -n systemctl reboot/poweroff`, fallback without sudo | `:10801`, `:10808`, `:3202-3230` |
| `shutdown` | — | Stop Core only | `:10815` |

**Exposure, white balance, AF** (all reply SB; CameraController setters `CC:7741-8216`)

| Command | Fields | Ref |
| --- | --- | --- |
| `set_iso` | `value` | `:9242` |
| `set_iso_auto` | — | `:9269` |
| `set_exposure_compensation` | `value` EV (finite) | `:9251` |
| `set_exposure_metering` | `value` | `:9260` |
| `set_fps` | `value` (keeps shutter angle; refused while recording) | `:9275` |
| `set_shutter_us` | `value` 1–30 000 000 | `:9284` |
| `set_shutter_auto` | — | `:9293` |
| `set_wb` | `kelvin` | `:9299` |
| `set_wb_auto` | — | `:9308` |
| `set_af_mode` / `set_af_range` / `set_af_speed` | `value` | `:9439`, `:9448`, `:9457` |
| `set_af_window` | `x`, `y`, `width`, `height` (normalised) | `:9466` |

**Format, codec, geometry** (reply SB; most force a camera reconfigure)

| Command | Fields | Ref |
| --- | --- | --- |
| `set_resolution` | `width`, `height` | `:9314` |
| `set_record_format` | `value` (cdng, lossydng, mlv, h264, prores + aliases, `:824-857`) | `:9326` |
| `set_cdng_compression` | `value` `none` / `lossless_jpeg` | `:9340` |
| `set_lossy_dng_ratio` | `value` 3to1 / 5to1 | `:9351` |
| `set_cdng_preview_color_profile`, `set_prores_color_profile` | `value` standard / arri_logc4 / sony_slog3 / davinci_intermediate / p3_d60_linear | `:9360`, `:9369` |
| `set_prores_profile` | `value` proxy / lt / 422 / hq | `:9378` |
| `set_tuning_file` | `path` (empty = automatic) | `:9388` |
| `set_raw_bit_depth` | `value` 8/10/12 (anything else → 12) | `:9397` |
| `set_h264_resolution` | `width`, `height` (0,0 = match) | `:9412` |
| `set_timecode_mode` | `value`; only exact `rec_run` = RecRun, else FreeRun; also UI.conf `timecodeMode` | `:9424` |

**Capture mode, stills, timelapse, recording**

| Command | Fields | Does | Ref |
| --- | --- | --- | --- |
| `set_capture_mode` | `value` clip / still / timelapse | Sets still mode + interval; UI.conf | `:9537` |
| `set_photo_mode_enabled` | `enabled` | Still mode on/off (reconfigure) | `:9573` |
| `set_photo_bracketing_enabled` | `enabled` | | `:9600` |
| `set_photo_bracketing_ev` | `value` 1/3–3 | Rounded to 1/3 | `:9612` |
| `set_photo_long_exposure_enabled` | `enabled` | | `:9623` |
| `set_photo_timer` / `set_photo_burst` / `set_photo_format` | `value` | UI.conf only (timer is UI-side; Core ignores it) | `:9890`, `:9903`, `:9916` |
| `set_photo_timelapse` | `value` 0.1–86400 s or Off; optional `format` | | `:9946` |
| `capture_photo` | optional `format`, `count` 1–10 (3 when bracketing) | Queue still(s) | `:10716` |
| `timelapse_start` | optional `value`, `format` | | `:10740` |
| `timelapse_stop` | — | | `:10775` |
| `record_start` | optional `sound_only`, `gyro_enabled`, `audio_enabled`, `audio_monitoring_enabled`, `audio_input_volume`, `audio_output_volume`, `audio_input_device`, `audio_output_device` | Start clip or Sound Recorder. With audio it broadcasts `prepare_recording` and **sleeps 220 ms holding `commandMutex_`** | `:10623`, `:10692-10706` |
| `record_stop` | — | Stop clip or Sound Recorder | `:10783` |

**UI.conf toggles** (`handleUiToggle`, `App:9477-9491`): field `enabled`; reply SB (not the toggled value).

| Command | UI.conf key | Ref |
| --- | --- | --- |
| `set_focus_peaking_enabled`, `set_zebra_enabled`, `set_false_color_enabled`, `set_lut_preview_enabled`, `set_guides_enabled`, `set_center_marker_enabled`, `set_grayscale_enabled`, `set_smpte_enabled`, `set_anamorphic_desqueeze_enabled`, `set_external_monitor_enabled` | `<name>Enabled` (camelCase) | `:9493-9511` |
| `set_date_time_overlay_enabled`, `set_record_audio_enabled`, `set_record_gyro_enabled` | idem | `:9640-9644` |
| `set_live_audio_monitoring_enabled`, `set_audio_meter_enabled` | idem | `:9724-9726` |
| `set_sound_recorder_enabled` | `soundRecorderEnabled`; refuses without an input device; turns off still mode | `:9513` |

**UI.conf values** (field `value` unless noted; reply echoes the value)

| Command | Ref |
| --- | --- |
| `set_focus_peaking_threshold` (0–1), `set_focus_peaking_color` | `:9729`, `:9739` |
| `set_zebra_threshold` (0–1), `set_false_color_mode` | `:9752`, `:9762` |
| `set_lut_preview_file` (empty clears; must be in an allowed LUT dir) | `:9776` |
| `set_guides_type`, `set_guides_thickness` (1–4), `set_center_marker_type`, `set_anamorphic_ratio` | `:9802`, `:9815`, `:9825`, `:9838` |
| `set_external_monitor_mode`, `_info_overlay`, `_orientation` | `:9851`, `:9864`, `:9877` |
| `set_ui_orientation`, `set_camera_controls_opacity` (0.15–1), `set_camera_controls_mode` (reply SB) | `:9998`, `:10009`, `:10020` |
| `set_battery_type`, `set_battery_capacity`, `set_custom_battery_wh` (10–500), `set_custom_battery_voltage` (`full`, `empty`) | `:10124`, `:10153`, `:10167`, `:10178` |
| `set_sleep_mode`, `set_favorites_order` | `:10206`, `:10219` |

**Audio**

| Command | Fields | Ref |
| --- | --- | --- |
| `audio_capabilities` | optional `device` → `modes[]` (format, rate, channels) | `:10031` |
| `set_audio_capture_options` | `format`, `rate` (0–192000), `channels` | `:10052` |
| `set_audio_input_device` / `set_audio_output_device` | `value` | `:10076`, `:10091` |
| `set_input_volume` / `set_headphone_volume` | `value` 0–100 | `:10104`, `:10114` |

**IMU / gyro** (write `apertar-hardware.conf`, reply = IMU status, `App:130-165`)

| Command | Fields | Writes | Ref |
| --- | --- | --- | --- |
| `set_imu_driver` | `value` | `[imu] driver` | `:9646` |
| `set_imu_orientation` | `value` | `[<driver>] orientation` | `:9656` |
| `set_imu_sync_offset` / `adjust_imu_sync_offset` / `reset_imu_sync_offset` | `value` / `delta` / — | `[imu] sync_offset_ms` | `:9666`, `:9676`, `:9687` |
| `set_imu_level_reference` / `clear_imu_level_reference` | — | `[<driver>] level_*` | `:9693`, `:9699` |
| `calibrate_gyro` | optional `seconds` (default 2.5) | `[<driver>] gyro_bias_*` | `:9705` |

**System, media, presets**

| Command | Fields | Does | Ref |
| --- | --- | --- | --- |
| `apply_preset` | Any `camera*` key (`cameraIso`, `cameraFps`, `cameraResolution`, `cameraRecordingFormat`, …) plus UI.conf keys; `presetName` | Applies everything in one reconfigure, then UI.conf | `:10230-10527` |
| `apply_date_time` | `year`, `month`, `day`, `hour`, `minute`, `time_zone` | timedatectl + hwclock | `:10529` |
| `apply_time_zone` | `time_zone` | | `:10552` |
| `set_fan_mode` | `value` Silent / Auto / Full Blast | Rewrites a managed block in `/boot/firmware/config.txt` (`:3042-3178`) | `:10568` |
| `format_media` | `filesystem` (default exfat; fat32, ntfs; ext4 refused) | `:3763-3867` | `:10579` |
| `eject_media` | — | §8 | `:10589` |
| `mount_media` | `device_path` | `sudo -n mount` | `:10596` |
| `run_media_speed_test` / `get_media_test_state` | — | fio or timed write | `:10616`, `:10608` |

Anything else: `Unknown command: <name>` (`:10821`).

### 3.3 `get_state` reply (`App:9218-9240`)

| Field | Meaning |
| --- | --- |
| `state` | Offline / Starting / Ready / Standby / Recording / Error / Stopping (`include/apertar/core/Types.hpp:14-22`) |
| `standby`, `recording` (camera or sound), `recording_error`, `recording_has_dropped_frames`, `sound_recording` | Recording status |
| `timelapse_active`, `timelapse_interval_seconds`, `timelapse_shot_count` | Timelapse |
| `still_exposure_active`, `still_exposure_remaining_seconds`, `photo_write_error` | Stills |
| `media_writes_pending`, `media_write_revision` | Write-behind state |
| `sensor` | libcamera sensor name |
| `settingsBody` fields | `resolution`, `width`, `height`, `fps`, `iso`, `iso_auto`, `shutter_us`, `shutter_auto`, `exposure_compensation`, `exposure_compensation_available`, metering, `photo_mode_enabled`, `photo_long_exposure_enabled`, `photo_bracketing_enabled`, `photo_bracketing_ev`, `wb_kelvin`, `wb_auto`, `wb_available`, `wb_measured`, `wb_actual_kelvin`, `wb_actual_red_gain`, `wb_actual_blue_gain`, `recording_capabilities`, `recording_format`, `cdng_compression`, `lossy_dng_ratio`, `prores_profile`, `prores_color_profile`, `cdng_preview_color_profile`, `preview_exposure_reference`, `tuning_file`, `raw_bit_depth`, `h264_resolution`, `h264_width`, `h264_height`, `timecode_mode`, `af_mode`, `af_range`, `af_speed`, `af_window_{x,y,w,h}` (`App:167-216`) |

Not in `get_state`: hardware input status. Every `lastError()` of the inputs is only logged to stderr; nothing reads it (grep of `App` shows only `start()`/`stop()` calls, `:6881-6918`).

### 3.4 Events (`publishEvent`, `App:10823-10852`)

Delivery rule:
1. `handleTriggerEvent` first: drives tally LED and trigger pulse by substring match (`App:10854-10889`).
2. **Always broadcast immediately**: `settings`, `recording_health`, `standby`, `still_exposure`, `media_write_state`, `photo_write_error`, `timelapse_progress`, and `hardware_action` with `standby_power_wake` / `standby_power_sleep` / `power_button_press` (`:10829-10841`).
3. Anything else, while a socket command is running: appended to **that** command's reply (`:10842-10848`). Otherwise broadcast.

| Event | Fields | Emitted at |
| --- | --- | --- |
| `camera_state` | `state` ready / stopping | `App:6901`, `:6913` |
| `settings` | `recording_capabilities` + settingsBody-like fields | `CC:136-191`, `CC:8777-8784` |
| `recording` | `active`, `recording_has_dropped_frames`, `error`; sound-only: `sound_only`, `folder` | `CC:8786-8796`; `App:8394`, `:8406` |
| `recording_health` | `recording_has_dropped_frames` | `CC:7580-7584` |
| `prepare_recording` | — (sent before audio starts) | `App:10692`, `:10705` |
| `audio_level` | `input_level` 0–100 | `CC:7588-7595`; `App:8383` |
| `standby` | `standby` true/false | `CC:7688`, `:7707` |
| `still_exposure` | `still_exposure_active`, `still_exposure_remaining_seconds` | `CC:7565-7575` |
| `media_write_state` | `media_writes_pending`, `media_write_revision` | `CC:7551-7563` |
| `photo_capture` | — | `CC:7177`; `App:10730` |
| `photo_write_error` | `photo_write_error` | `CC:5248`, `:7029` |
| `timelapse` | `active`, `interval_seconds`, `folder` | `CC:8798-8822` |
| `timelapse_frame` | `index` | `CC:8824-8832` |
| `timelapse_progress` | `timelapse_shot_count` | `CC:8440-8445` |
| `hardware_action` | `action` (zoom_toggle, still_mode, settings, clip_browser, quick_menu, a toggle name, power-button actions) | `App:8476`, `:8612-8623`, `:8667`, `:8904`, `:8950` |
| `preview_buffer` | `slot`, `frame_id`, `timestamp_us`, `width`, `height`, `stride`, `capture_width`, `capture_height`, `size`, `fourcc`, `plane_count`, `layout_plane_count`, `planeN_{offset,pitch,length}`, `fd_attached`; **dmabuf fds via SCM_RIGHTS** | `App:10891-10944` |
| `preview_frame` | `slot`, `frame_id`, `timestamp_us` | same |

Preview model: the camera `dup()`s each request slot's dmabuf plane fds once and sends them as `preview_buffer` (`CC:7248-7260`). After that each frame is a small `preview_frame` naming the slot. Only the newest pending frame is kept (`App:6977-6987`). Registrations are cached and replayed on `preview_subscribe` (`App:6994-7019`).

## 4. WebUI (`src/web/*`)

| Item | Value | Ref |
| --- | --- | --- |
| Server | `AF_INET`, `SO_REUSEADDR`, backlog 16, thread per client, max 32 | `src/web/WebServer.cpp:194-228`, `:270-271` |
| Timeouts | 5 s send/recv per socket; 10 s to read a request | `:265-267`, `:304` |
| Max request | 1 MiB (413) | `:23`, `:346`, `:360` |
| HTTP | `Connection: close`; no chunked bodies (400) | `:133`, `:332` |
| Origin check | `Sec-Fetch-Site: cross-site` → 403; an `Origin` must equal `http://<Host>`; **no `Origin` passes** | `:156-170`, `:372-375` |
| Auth | **none**. Anyone on the LAN or hotspot can `format_media`, `power_off_system`, rewrite `apertar-hardware.conf` (incl. `[run_script]` paths) | — |
| Page | One raw string, `webControlPageHtml()`; rebuild Core to change it | `src/web/WebControlPage.cpp:5-11617` |
| State poll | `fetch("/api/state")` every 1 s | `WebControlPage.cpp:11609`, `:10224` |
| Commands | `POST /api/command` with the same JSON as the socket | `WebControlPage.cpp:9123-9127` |

Endpoints (`handleWebRequest`, `App:7093-7649`):

| Method + path | Does | Ref |
| --- | --- | --- |
| `OPTIONS *` | 204, no CORS headers | `:7095` |
| `GET /`, `/index.html` | The page | `:7102` |
| `GET /preview.mjpeg` | `multipart/x-mixed-replace`; 640x360 max, ≤30 fps, JPEG q75 (`App:60-63`); 503 without JPEG support | `:7109` |
| `GET /icons/<name>` | PNG from disk (search order in [build.md](build.md#webui-icons)) | `:7124` |
| `GET /api/state` | `buildWebStateJson` (`App:7711-8046`): get_state fields + UI.conf + network, device, power (INA219), CPU, media, audio devices, time zones | `:7154` |
| `GET /api/media` | Clip library | `:7161` |
| `GET /api/config` | `apertar-hardware.conf` text; **Core template if the file is missing** | `:7168`, `:5290-5321` |
| `POST /api/config` | Save config (`.bak` + `.tmp` + rename, ≤256 KiB) | `:7175`, `:5323-5386` |
| `GET /api/media/download?kind=&id=`, `/api/media/download-selected` | File or zip download | `:7197`, `:7318` |
| `POST /api/media/delete`, `/api/media/delete-selected` | Delete clips (checks `isRecording()` only) | `:7503`, `:7575` |
| `GET /api/presets`, `/api/presets/download/<file>` | Preset list / file | `:7360`, `:7367` |
| `POST /api/presets/import[/<name>]`, `/api/presets/save?name=`, `/api/presets/delete?file=` | Preset files | `:7392`, `:7440`, `:7477` |
| `POST /api/command` | `handleWebCommand` → `parseControlCommand` → `handleCommand` | `:7637`, `:7085-7091` |

WebUI commands go through the same `handleCommand`, so they obey the same gates. Unlike the socket path they never collect events into the reply (`handleWebCommand` skips `collectingCommandEvents_`, `App:7085-7091`), so their events are broadcast to socket clients.

`/api/state` per tab per second shells out to `lsblk`, scans ALSA, re-reads UI.conf and reprograms the INA219 (`App:7711-7740`, `:4600-4662`).

## 5. Camera and libcamera (`CameraController`)

### 5.1 Open and select (`CameraSession::start`, `CC:5254-5398`)

1. Automatic tuning: `tuning::preselectDefault` scans v4l subdev names before the IPA loads (`src/camera/DefaultTuningSelection.hpp`). `applyProcessTuningFile` sets `LIBCAMERA_RPI_TUNING_FILE` and `APERTAR_SENSOR_TUNING_FILE` (`CC:1111-1121`). This is why `APERTAR_TUNING_FILE` in the start script has no lasting effect ([build.md](build.md#the-start-script-and-service)).
2. Up to 3 attempts: new `CameraManager`, `start()`, pick **the first camera whose id has no `/usb`**, else the first (`CC:5279-5298`). No user choice.
3. Mono: draft `ColorFilterArrangement == MONO`, else the Raw-role default format (`CC:5308-5321`).
4. If the model's default tuning differs from the preselected one: tear down, set env, retry once (`CC:5322-5341`).
5. Log/ProRes colour profile: write a derived tuning JSON (`makeProresIspTuning`), point the env at it, restart the manager (`CC:5343-5366`).
6. `detectSensorFamily(camera->id())`: substring `imx577`, `imx477`, `imx294`, `imx585`, else Unknown (`CC:2151-2167`).
7. `acquire()`, then `configureAndStart` (`CC:5378-5390`).

`reconfigure()` is a full stop + start, CameraManager included (`CC:5481-5493`). Changes to resolution, bit depth, format class, photo mode, colour profile, tuning or H.264 size reconfigure. FPS, ISO, shutter, WB, EV, metering, AF are control-only (`applySettingsLocked`, `CC:8659-8723`).

### 5.2 Configure path (`configureAndStart`, `CC:5968-6375`)

Mode flags (`CC:5985-5996`):
- `proresMode`: not still mode and format ProRes.
- `processedYuvMode`: H.264 or ProRes.
- `hardwareH264Mode`: processed, not ProRes, board has hardware H.264 (not Pi 5).

Stream roles:

| Mode | Roles | Ref |
| --- | --- | --- |
| RAW formats (cDNG, lossy DNG, MLV) and stills | `{VideoRecording (YUV420 preview), Raw}` | `CC:6031-6037` |
| ProRes | `{VideoRecording = BGR161616 (RGB48) at exactly the selected size, Viewfinder}`; anything else is rejected | `CC:6019-6020`, `:6145-6151` |
| H.264 | `{Viewfinder, VideoRecording}`; `APERTAR_H264_SINGLE_STREAM=1` → one stream; Raw only with `APERTAR_H264_KEEP_RAW_STREAM=1` | `CC:6021-6030`, `:2841-2849` |

Search loop: for each sensor-mode candidate × raw-stream preference × {explicit `SensorConfiguration` (outputSize + bitDepth), auto}: `generateConfiguration` → set formats → `validate()` → `configure()` (`CC:5999-6303`). Auto sensor config only for mono, IMX294, IMX577 or IMX585 12-bit crops (`CC:5993-5996`). Every rejection is appended to the error string `libcamera rejected camera configurations: …` (`CC:6305-6309`). Success logs `ApertarCore camera configured: sensor=… raw=… preview=… stream=… format=… storage_bits=… packing=…` (`CC:6264-6290`).

| Stream | Setting | Ref |
| --- | --- | --- |
| Preview | YUV420, Rec709, fits 1280x720 keeping aspect (`kPreviewWidth/Height`) | `CC:6083-6087`, `:1019-1020`, `:2819-2830` |
| Raw (colour) | `SRGGB8` / `SRGGB10_CSI2P` / `SRGGB12_CSI2P` by bit depth | `CC:2181-2191` |
| Raw (mono) | `R8` / `R10_CSI2P` / `R12_CSI2P` / `R16` if offered (R16 unreachable: depth is never 16) | `CC:6100-6108`, `:243-250` |
| Packing | PiSP `PispCompressed1` storage depth = requested depth | `CC:6238-6246` |
| Buffers | 4 (RAW), H.264 4/6 (`APERTAR_H264_CAMERA_BUFFERS`), ProRes 12 (`APERTAR_PRORES_CAMERA_BUFFERS`) | `CC:1023`, `:1124-1134` |
| Cached dmabuf | ProRes and PiSP-compressed RAW use CPU-cached DMA heap (`APERTAR_PRORES_CACHED_DMABUF`, `APERTAR_RAW_CACHED_DMABUF`, default on) | `CC:6317-6325`, `:6384-6450` |
| Start | Initial controls go to `camera_->start()`, then all requests are queued | `CC:6338-6373` |

### 5.3 Sensor-mode selection

| Step | Ref |
| --- | --- |
| Allowed raw depths: 8, 10, 12 (16 → 12) | `CC:243-250` |
| Per sensor: IMX477/577 8/10/12; IMX294/585 10/12; H.264 and ProRes forced 10 | `CC:2685-2705`, `:2707-2745` |
| Resolution tables (IMX585: 1920x1080, 3840x2160 and 1920/3840 crop heights) | `CC:360-532` |
| Foreign sizes are mapped onto the sensor's set (e.g. IMX585 2028x1080 → 1920x1080) | `CC:2372-2422` |
| Candidate list per requested size | `sensorModeCandidatesForRequestedResolution`, `CC:2289-2370` |
| Max fps per mode; IMX585 4K = 30, FHD and crops = 60 | `CC:2629-2683` |
| Lossless cDNG caps (ISO ≤ 800, fps by size) | `CC:2470-2491` |
| Software RAW crop for IMX477/577/294 | `CC:2851-2924` |

Driver-side modes and link rates are in [drivers.md](drivers.md).

### 5.4 Controls (`controlsForSettings`, `CC:2005-2144`)

`FrameDurationLimits` from fps; `AeEnable = isoAuto || shutterAuto`; `AnalogueGain = ISO/100`; `ExposureValue` only while AE is on; AWB auto, manual `ColourTemperature`, or mono gains 1,1; ScalerCrop from `ScalerCropMaximum`; AF `AfWindows` + `AfTrigger=Start` on every update in Auto mode. Runtime changes are merged into `pendingControls_` and attached on the next requeue (`CC:5495-5524`, `:6497-6509`).

### 5.5 Preview delivery and the callback

`requestComplete` (`CC:6579-6669`) on the libcamera thread: read WB/exposure/CCM metadata → still capture (`capturePhotoFrame`) → publish preview unless a long still exposure is active (`publishPreviewFrame`, `CC:7228-7372`) → record frame (`recordProcessedPreviewFrame` / `recordRawFrame`) → requeue. The UI maps the dmabufs it got through `preview_buffer`; the WebUI gets a scaled JPEG copy only while `/preview.mjpeg` has viewers (`App:6951-6953`, `:8095-8192`).

## 6. Recording

Per-board format matrix: `include/apertar/core/RecordingCapabilities.hpp`. Pi 5 (`brcm,bcm2712`): RAW compression yes, ProRes yes, hardware H.264 **no** (software libx264) (`:25-26`).

Start: `CameraSession::startRecording` (`CC:5526-5656`): reserve clip folder → gyro (failure non-fatal) → audio (failure aborts) → ProRes or H.264 recorder, or `DngRecordingQueue`. Stop (`CC:5658-5683`): close the frame gate, then gyro → H.264 → DNG queue → ProRes → audio. **Core checks neither mount state nor free space before recording**; with nothing mounted, files land in `/media/RAW` on the root filesystem. Only the Sound Recorder checks the mount (`App:8351`).

Asynchronous failures latch a `RecordingFailure` (first message wins, `src/util/RecordingFailure.hpp`); `checkRecordingFailure` (`CC:8519-8534`) stops the take on the next 1 s tick or command.

| Format | Folder / file | Writer | Notes | Ref |
| --- | --- | --- | --- | --- |
| cDNG uncompressed / lossless | `<media>/cDNG_yy-mm-dd_C####/<clip>_#########.dng` | `DngRecordingQueue` → `CdngEncoder` | Lossless = LJ92 SOF3, 128-row tiles (`APERTAR_CDNG_TILE_ROWS`). Workers min(8, cores+1) (`APERTAR_CDNG_WORKERS`). Frame index from timestamp, so drops leave gaps | `CC:3633-3685`, `:3320-3352`; `src/cdng/LosslessJpegEncoder.cpp` |
| Lossy DNG 3:1 / 5:1 | `cDNG_3to1_…` / `cDNG_5to1_…` | `LossyDngEncoder` | Async writer; **write errors only logged, never fail the take** | `src/lossydng/LossyDngEncoder.cpp:228-233` |
| MLV | `MLV_…/<clip>.MLV` | `MlvEncoder` | Single file, uncompressed; frame count patched at close; mono rejected | `src/mlv/MlvEncoder.cpp` |
| H.264 | `H264_…/<clip>.mp4` (`.mp4.writing` then rename) | `H264PreviewRecorder` → `apertar-h264-libav.so` | Pi 5: libx264 ultrafast CRF 22; Pi 4: `h264_v4l2m2m`. No audio track (WAV sidecar). Fallback: `ffmpeg` pipe (`APERTAR_H264_BACKEND=pipe`) | `CC:3930-5016`, `:4325-4345` |
| ProRes | `ProRes_…/<clip>.mov` + `_recovery.json` | `ProresRecorder` → `apertar-prores-libav.so` | `prores_aw`, Proxy/LT/422/HQ, zero-copy RGB48. **`ProresRepair` is never called**, though the sidecar promises repair "on the next start" | `src/prores/ProresEncoder.cpp:1257-1290` |
| Stills | `<media>/Photos/Still_yy-mm-dd_C####.<ext>`; brackets `_BRm/_BR0/_BRp` | `PhotoCaptureWriter` | DNG stills always 16-bit uncompressed; JPEG/PNG/TIFF rendered on the CPU from RAW; atomic `.writing-XXXXXX` + rename | `CC:924-966`, `:5018-5224`; `src/util/AtomicStillFile.hpp` |
| Timelapse | `<media>/Timelapse_yy-mm-dd_C####/<folder>_#########.<ext>` | same | Interval 0.1–86400 s; waits after queuing, so it drifts | `CC:968-1015`, `:8302-8500` |
| Audio (with clip) | `<clip>/<clip>.wav` via `<clip>/audio_capture.raw` | `AudioRecordingSession` | BWF `bext` + `iXML`; trimmed/padded to video. **Raw capture deleted even if the WAV build fails** | `src/audio/AudioRecordingSession.cpp:231-235`, `:366-376` |
| Sound Recorder | `<media>/Audio/Audio_yy-mm-dd_C####/` | same | Needs mounted media | `App:1442-1480`, `:8337-8397` |
| Gyro | `<clip>/<clip>.gcsv` (Gyroflow) | `Mpu6050RecordingSession` | Samples held in RAM until stop: a crash leaves no file | `src/hardware/Mpu6050RecordingSession.cpp:2230-2234` |

Plugin loading (lazy dlopen, ABI check) is in [build.md](build.md#how-core-finds-its-plugins-at-runtime).

## 7. Hardware inputs and outputs (`src/hardware/*`)

Common pattern:
- Config: first existing of `$APERTAR_HARDWARE_CONFIG`, `/home/pi/apertar-hardware.conf`, `/boot/firmware/…`, `/boot/…`; the list is copied into every class (e.g. `src/hardware/Pcf8574Input.cpp:55-76`). Read once in `start()`.
- I2C: raw `/dev/i2c-N` + `I2C_SLAVE`. GPIO: kernel chardev uAPI v2 (`GPIO_V2_GET_LINE_IOCTL`), no libgpiod (`src/hardware/GpioInput.cpp:544-590`).
- One poll thread per class. Open retried every 1 s, reopen 250 ms after an I/O error.
- **Errors**: `setLastError()` prints `<Class> input: <error>` to stderr once per distinct message (e.g. `NeoRotary4Input.cpp:614-622`). `journalctl -u apertar-core | grep -i 'input:'` is the only place to see them.
- Actions run synchronously on the poll thread through `dispatchHardwareInputCommand` → `handleCommand` (`App:8458-8466`). A slow command (reconfigure) stalls polling.
- Action vocabulary: `src/hardware/ButtonActionList.hpp` (≤6 comma-separated actions, LED aliases must be alone) and `App:8630-8955` (`capture`, `record_toggle`, `photo`, `timelapse`, `eject`, `still_mode`, `standby`, toggles, `fps/iso/shutter/wb/resolution[_up|_down]`, `iso200`, `wb5000`, `fps24`, `ev_up`, `ev-1`, `shutter1/48`, `run_scriptN`, UI-only `settings`/`clip_browser`/`quick_menu`/`zoom_toggle`). In Standby any press only wakes; rotations are ignored (`App:8642-8657`).

| Class | Section (aliases) | Bus / address default (code) | Enabled when | Startup log | Ref |
| --- | --- | --- | --- | --- | --- |
| `NeoRotary4Input` (Adafruit seesaw quad encoder) | `[neorotary4]` (`neo_rotary4`, `neo_rotary_4`) | 1 / `0x49` | section present, unless `enabled=false`; needs ≥1 mapped action | `NeoRotary4 input enabled: /dev/i2c-N address=0x49 config=…` | `src/hardware/NeoRotary4Input.hpp:36-48`, `.cpp:310-330`, `:355-444` |
| `Pcf8574Input` (8-pin expander buttons) | `[pcf8574]` (`pcf8574_buttons`) | 1 / `0x20` | section present; needs ≥1 pin action | `PCF8574 input enabled: …` | `Pcf8574Input.hpp:28-38`, `.cpp:273-291`, `:318-390` |
| `GpioInput` (buttons, quadrature encoders) | `[gpio_buttons]` (`gpio`, `grove_digital`, `grove_buttons`), `[gpio_encoders]` (`grove_encoders`) | chip `auto` (RP1 preferred) | only `enabled=true` | — | `GpioInput.hpp:29-56`, `.cpp:238-260`, `:373-503` |
| `GroveAnalogInput` (Grove Base HAT ADC) | `[grove_analog]` (`grove_adc`, `analog_controls`) | 1 / `0x04` | section present | — | `GroveAnalogInput.hpp:52-62`, `.cpp:246-355`; mapping `App:8480-8606` |
| INA219 (in `ApertarCoreApp`) | `[ina219]` | **4** / `0x40` | `enabled=true` (default) | none; failures silent, values just missing | `App:4239-4244`, `:4450-4506`, `:4600-4662` |
| `Mpu6050RecordingSession` (MPU6050/6500, BMI160, BMI270, ICM42688-P) | `[imu]` + `[<driver>]` or `[gyro]` | 1 / `0x68`; **auto-probes every `/dev/i2c-0..32` at 0x68/0x69** | code default enabled | `logAutoProbeSuccessOnce` | `Mpu6050RecordingSession.hpp:94-121`, `.cpp:851-1033`, `:1543-1600` |
| `StandbyPowerButtonInput` | none | evdev device named `pwr_button`, `KEY_POWER` | always (not simulate) | — | `StandbyPowerButtonInput.cpp:31-75`; gesture `PowerButtonGesture.hpp:9-30` |
| `TriggerOutput` (hot shoe / flash pulse) | `[trigger_output]` (`trigger`, `capture_trigger`, `hotshoe`) | GPIO17, or PCF pin 0 at the `[pcf8574]` bus/address | `enabled=true` | `ApertarCore trigger output disabled: …` on failure | `TriggerOutput.hpp:41-55`, `.cpp:250-360`; `App:6881-6884` |
| `RecordingIndicatorOutput` (tally LED) | `[recording_indicator]` (`rec_indicator`, `record_led`, `recording_led`, `tally_led`), or `pinN=recindicatorled` / `dN=recindicatorled` | line −1, PCF 1 / `0x20` | `enabled=true` or an LED alias anywhere | `ApertarCore recording indicator LED disabled: …` | `RecordingIndicatorOutput.hpp:36-49`, `.cpp:247-399`; `App:6893-6896` |
| `HardwareScriptRunner` | `[run_script]` `path`, `path1`–`path5` | — | on a `run_script[N]` action | `ApertarCore run_script …` | `HardwareScriptRunner.cpp:38-96`; `/bin/bash -- <path>` at `:232-238` |

NeoRotary4 specifics: seesaw HW ID must be `0x87` (`NeoRotary4Input.cpp:37`, `:494-515`); 8 ms between register select and read (`.hpp:56`); encoder delta reg `0x11/0x40+i`, buttons on seesaw pins 12, 14, 17, 9 (`.cpp:35-38`); more than `max_events_per_poll` steps per poll are dropped (`:661`). Typical errors: `/dev/i2c-1: No such file or directory` (bus missing, see [sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md](../sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md)), `NeoRotary4 unexpected hardware ID 0x12 at address 0x48` (wrong device).

Power button: single press → event `power_button_press` (UI shows the shutdown hold); double press (release ≤500 ms, second press 80–500 ms) → `enter_standby`; any press in Standby → wake (`App:8608-8628`).

Hardware gotchas:
- `[trigger_output]` and `[recording_indicator]` both default to GPIO17 in the templates; enabling both makes the second request fail (`App:4381`, `:4395`).
- Input, trigger and LED each open the same PCF8574 with their own shadow byte (`Pcf8574Input.cpp:426-430` writes `0xFF`; `TriggerOutput.cpp:640-663`; `RecordingIndicatorOutput.cpp:695-714`). Two writers on one expander can clobber each other's pins. **Unconfirmed** on hardware.
- Core's INA219 and the UI's `Ina219Bridge` both reprogram the same chip's config/calibration registers (`App:4622-4626`; `Apertar-UI/src/Ina219Bridge.cpp`).

## 8. The embedded CFE automount Python helper (`App:3380-3602`)

`startNvmeReinsertWatcherAtPath` holds a Python script as a C++ raw string and runs it after an NVMe eject:

```
APERTAR_MEDIA_ROOT=<--media> python3 -c '<script>' >/dev/null 2>&1 &
```
(`App:3594-3601`)

When: `eject_media` on an `/dev/nvme*` device, after `udisksctl unmount` (or `umount`) and PCI remove of the controller (`App:3710-3761`, `:3357-3378`).

| Step | Ref |
| --- | --- |
| Defaults: `I2C_BUS = 10`, `I2C_ADDR = 0x34`, `CFE_HAT_ENABLED = True`, `PCIE_CONTROLLER = "1000110000.pcie"` | `App:3391-3395` |
| Config: first existing candidate; `configparser`; `[cfexpress_hat] enabled/bus/address`, `[storage] pcie_controller` (`mount_path` ignored because Core always sets `APERTAR_MEDIA_ROOT`) | `App:3397-3463` |
| `enabled=false` → exit | `App:3568-3570` |
| `smbus.SMBus(I2C_BUS)`; poll the hat byte (`0x69` = invalid, bit0 = insert) up to 60 s for 1, then up to 60 s for 0 | `App:3484-3495`, `:3573-3585` |
| Reset PCIe: brcm-pcie unbind/bind, then `/sys/bus/pci/rescan` (via `sudo -n` when not root) | `App:3555-3566` |
| Mount the highest `nvmeXnYpZ` partition: exfat/ntfs3 with uid/gid 1000, ext4 plain, nothing else | `App:3506-3553`, `:3589-3591` |

Problems:
- **All output goes to `/dev/null`.** A crash (missing `python3-smbus`, bad bus, `configparser` `DuplicateOptionError`) is invisible. Debug by running the script by hand with output visible.
- Integers are not comment-stripped: `bus=1 # hat` → falls back to 10 (`App:3413-3422`).
- `read_insert_state` returns `True` on I2C failure (`default_state=True`, `App:3484-3495`). With a dead bus the first wait passes at once and the second spins about 6 minutes.
- **It races `apertar-cfe-automounter`**, which runs on the Pi (`apertar-cfe-automounter.service`, Pi, 2026-10-25) and reacts to the same insert edge. The UI's copy of this watcher skips itself when `/run/apertar-cfe/ready` exists (`Apertar-UI/src/MediaStatusBridge.cpp:741-747`); Core's copy has no such check. Both reset PCIe and mount.
- If spawning fails, eject reports failure although the drive is already detached (`App:3742-3745`).
- The bit0 polarity (1 = card present or switch released) is **unconfirmed**: check against `Apertar-UI/src/CfeAutomounter.cpp` edge handling and `i2ctransfer -y 1 r1@0x34` with the card in and out.

## 9. Known bugs and rough edges

| # | Issue | Ref |
| --- | --- | --- |
| 1 | `collectingCommandEvents_` is set **before** `commandMutex_` is taken. With two socket clients, B clears A's pending events; asynchronous camera events during a command go only to that requester | `App:7061-7065` vs `:9093` |
| 2 | `recording` and `timelapse` start/stop are not on the always-broadcast list; a UI-started take reaches other clients only through their next poll | `App:10829-10841` |
| 3 | `help` lists 98 of ~110 commands | `App:9216` |
| 4 | `record_start` with audio sleeps 220 ms under `commandMutex_` | `App:10692-10706` |
| 5 | WebUI has no auth; requests without `Origin` pass | `src/web/WebServer.cpp:156-170` |
| 6 | Core never checks mount or free space before recording | §6 |
| 7 | Core's NVMe watcher races the CFE automounter and logs nothing | §8 |
| 8 | Hardware errors never reach `get_state` or the WebUI | §3.3 |
| 9 | ProRes repair never invoked; lossy DNG write errors silent | §6 |
| 10 | Template defaults disagree with each other and with parser defaults | [config.md](config.md#3-template-copies-and-where-they-disagree) |
| 11 | Config edits need a Core restart; `POST /api/config` does not reload inputs | `App:6881-6893` |

## 10. Where to change X

| Change | Edit | Then |
| --- | --- | --- |
| Add a socket command | New `if (command.name == "...")` in `handleCommand` (`App:9091-10821`); add to the `help` list (`:9216`); reply with `okReply`/`errorReply` (`:108-128`) | WebUI caller in `src/web/WebControlPage.cpp` (`sendCommand`), UI caller in `Apertar-UI/src/ApertarControlBridge.cpp` |
| Add a field to `get_state` | `App:9218-9240`, or `settingsBody` (`:167-216`) if it is a camera setting. The `settings` event (`CC:136-191`) and `/api/state` (`App:7711-8046`) are separate copies | Keep all three in sync |
| Add a new event | `publishEvent("{\"event\":\"x\",...}")`; add it to the always-broadcast list (`App:10829-10841`) if other processes must see it during a command | UI consumer in `ApertarControlBridge` |
| Add a persisted camera setting | Field in `CaptureSettings` (`include/apertar/core/Types.hpp:124-162`); load/write in `CC:616-791`; clamp in `clampCaptureSettings` (`CC:534`); setter + `applySettingsLocked` (`CC:8659`) | `settingsBody`, `settings` event, `/api/state` |
| Add a persisted UI setting Core must read | Field + default in `SharedUiSettingsSnapshot` (`App:1580-1639`); parse in `readSharedUiSettings` (`:1641-1813`); write with `updateSharedUiGeneralSettings` | Same key in `Apertar-UI/src/SettingsBridge.cpp` |
| Add a recording format | `RecordingFormat` enum (`Types.hpp:45-51`) + `toString`; `normalizeRecordingFormatValue` (`App:824-857`); `RecordingCapabilities.hpp`; stream roles in `configureAndStart` (`CC:5985-6037`); writer in `CameraSession::startRecording` (`CC:5526-5656`); clip prefix (`CC:3633-3676`); profile key (`CC:605-608`) | New sources in `CMakeLists.txt:69-96` or a plugin target |
| Add a hardware input | New class in `src/hardware/` modelled on `Pcf8574Input` (config loader, `start/stop`, poll thread, `setLastError`); member + callback in `ApertarCoreApp.hpp:110-124` / `App:6781-6794`; `start()`/`stop()` calls (`App:6886-6891`, `:6914-6918`) | Add to `CMakeLists.txt:69-96`; add a template section in all three templates ([config.md](config.md)) |
| Add a button action | `normalizeSingleAction` in each input class (`GpioInput.cpp`, `Pcf8574Input.cpp`, `NeoRotary4Input.cpp` ~`:120-220`) and `handleSingleHardwareInputAction` (`App:8660-8955`) | Template comment lists |
| Add a WebUI endpoint | `handleWebRequest` (`App:7093-7649`) | Page JS in `WebControlPage.cpp` |
| Change a `apertar-hardware.conf` default | Parser default in the class header **and** all three templates | See [config.md](config.md) |
| Change sensor modes / fps caps | Tables `CC:360-532`, `:2629-2683`; candidates `:2289-2370` | Check [drivers.md](drivers.md) |

## Unconfirmed

| Claim | Command that settles it |
| --- | --- |
| `/usr/local/libexec/apertar-wait-ui-core-start` = `wait_for_ui_core_start.sh` | `cmp /usr/local/libexec/apertar-wait-ui-core-start /home/pi/ApertarUI/wait_for_ui_core_start.sh` |
| Core runs with `HOME=/home/pi` (systemd sets HOME for `User=`), so it shares the UI's `UI.conf` | `sudo tr '\0' '\n' < /proc/$(pidof apertar-core)/environ \| grep -E '^(HOME\|XDG)'` |
| `python3-smbus` is installed (needed by the §8 watcher) | `python3 -c 'import smbus'` |
| Core's watcher and the automounter really double-mount after an eject | eject in the WebUI, reinsert, then `journalctl -u apertar-cfe-automounter -n 50` and `ps aux \| grep 'python3 -c'` |
| PCF8574 clobbering when input + LED share an expander | wire both, record, watch the button pins with `i2cget -y <bus> 0x20` |
