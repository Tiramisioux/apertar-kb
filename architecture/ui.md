# Apertar-UI

The Qt 6 QML touch UI, its launcher, and the helper binaries built from the same repo.

Refs are against `upstream-1.6.0` (fork HEAD `66d6d19` only untracks `build/`; `git diff upstream-1.6.0 HEAD -- src qml run_pi_direct.sh` is empty). Paths are repo-relative: `Apertar-UI/...`, `Apertar-Core/...`. Pi facts are from `systemctl cat` on the live Pi (Pi, 2026-10-25).

Related: [overview.md](overview.md) (processes, startup order), [build.md](build.md) (rebuild/restart), [config.md](config.md) (`apertar-hardware.conf`), [core.md](core.md) (the other end of the socket).

## Quick facts

| Fact | Ref |
| --- | --- |
| One binary, two modes: normal UI, or HDMI monitor-only when `APERTAR_MONITOR_ONLY` is set | `Apertar-UI/src/main.cpp:275-276`, `:131-237` |
| QML is compiled in (AOT). Every QML edit needs a rebuild | `Apertar-UI/CMakeLists.txt:184-196` |
| Platform: EGLFS/KMS, no compositor, evdev input, `QSG_RENDER_LOOP=basic` | `Apertar-UI/run_pi_direct.sh:207-221` |
| Talks to Core over the Unix socket `/tmp/apertar-core.sock`, newline-delimited JSON | `Apertar-UI/src/ApertarControlBridge.cpp:1032`, `:1567` |
| UI-side settings live in `~/.config/CinePi/UI.conf` (`QSettings("CinePi","UI")`), shared with Core and the network helper | `Apertar-UI/src/SettingsBridge.cpp:287`, `Apertar-Core/src/ApertarCoreApp.cpp:341-348` |
| Display size/layout come from `[display]` in `apertar-hardware.conf`, read once at start | `Apertar-UI/src/DisplayConfigBridge.cpp:585-652` |
| Started by `apertar-ui-direct.service` → `run_pi_direct.sh /home/pi/ApertarUI/build/Apertar-UI` as `pi` on `/dev/tty1` | Pi, 2026-10-25 |

## Source map

### `src/` (C++)

Line counts from `wc -l`. Big files in bold.

| File | Lines | Responsibility |
| --- | --- | --- |
| `main.cpp` | 521 | Entry point. Screen choice, bridge construction, context properties, readiness files, monitor-only mode |
| `ApertarControlBridge.{hpp,cpp}` | 326 / **2460** | Camera state and `set_*` commands to Core. Event socket + per-command sockets |
| `ApertarPreviewSocketClient.{hpp,cpp}` | 92 / 625 | Raw `AF_UNIX` client; `preview_subscribe`; receives dma-buf fds via `SCM_RIGHTS` |
| `PreviewFrameInfo.hpp` | 27 | Frame descriptor (fds, planes, offsets, pitches, sizes) |
| `CameraPreviewItem.{hpp,cpp}` | 154 / 261 | QML type `Apertar 1.0 CameraPreviewItem`. Holds aid properties; draws nothing itself |
| `PreviewWindowRenderer.{hpp,cpp}` | 285 / **2466** | Imports dma-bufs as EGLImages, GLES2 shaders for zebra/peaking/false colour/LUT/grayscale/SMPTE |
| `PreviewExposureReference.hpp` | 52 | LUT + matrix from Core's `preview_exposure_reference` (aids measure a reference even under log preview) |
| `SettingsBridge.{hpp,cpp}` | 492 / **2314** | ~71 UI settings in `UI.conf`, presets, LUT/tuning-file discovery, section ordering, file-watch sync |
| `DisplayConfigBridge.{hpp,cpp}` | 61 / 654 | Reads `[display]`. Writes a full default `apertar-hardware.conf` if missing |
| `DisplayCalibration.{hpp,cpp}` | 68 / 286 | Per-output colour calibration (builtin/HDMI) as a GL post-pass |
| `DisplayStandbyController.{hpp,cpp}` | 20 / 108 | Hides windows and DPMS-offs HDMI/DPI/DSI in standby |
| `SleepManager.{hpp,cpp}` | 48 / 256 | Global event filter: idle timer, user-activity, input swallow in standby, backlight |
| `ExternalMonitorManager.{hpp,cpp}` | 46 / 313 | In-process HDMI window (same DRM card) |
| `ExternalMonitorRuntimeBridge.{hpp,cpp}` | 99 / 356 | Main UI → monitor-only process state over a local socket |
| `MediaStatusBridge.{hpp,cpp}` | 159 / **1295** | `/media/RAW` mount state, remaining time, drive discovery; eject/format/speed test via Core |
| `Ina219Bridge.{hpp,cpp}` | 69 / 746 | INA219 battery monitor over `/dev/i2c-N`. Second copy of the default config template |
| `GyroConfigBridge.{hpp,cpp}` | 175 / **1746** | `[imu]` config read/write; live IMU polling over I2C for the level overlay |
| `WifiBridge.{hpp,cpp}` | 123 / 916 | NetworkManager via `nmcli`: scan, connect, hotspot, auto-hotspot fallback |
| `AudioDeviceBridge` / `AudioMeterBridge` / `AudioMixerBridge` | 642 / 517 / 224 (cpp) | ALSA device lists (`arecord -l`), level meter (`arecord`), headphone monitor (`aplay`), mixer (`amixer`) |
| `SystemActionBridge.{hpp,cpp}` | 50 / 711 | Reboot/poweroff (login1), time zone/date (timedate1), fan curve in `/boot/firmware/config.txt` |
| `SystemStatsBridge`, `DeviceInfoBridge` | 112 / 398 (cpp) | CPU %, SoC temp; Pi model, OS, IP, RAM, storage |
| `PowerButtonBridge.{hpp,cpp}` | 47 / 186 | evdev `pwr_button` fallback when Core is disconnected |
| `cliplistmodel`, `playbackcontroller` | 642 / **1294** (cpp) | Clip browser model over `/media/RAW`; playback state, WAV sidecar via `aplay` |
| `cdngimageprovider`, `dngdecoder`, `tiffhelper`, `rawframe.h`, `RawPreview.hpp` | 1103 / **1574** / 113 | DNG decode (incl. LJ92 via `third_party/liblj92`), thumbnails, CPU debayer |
| `VideoPlayback.{hpp,cpp}`, `VideoPlaybackApi.h`, `MlvReader` | 187 / 27 / 278 | `image://video` provider; loads the libav plugin; MLV reader |
| `VideoPlaybackLibav.cpp` | 226 | **Separate module** `apertar-video-libav.so` (FFmpeg) |
| `NetworkHelper.cpp` | 32 | **Separate binary** `apertar-network-helper` (headless `WifiBridge`) |
| `CfeAutomounter.cpp` | 781 | **Separate binary** `apertar-cfe-automounter` |
| `StandbyUsbPower.cpp`, `StandbyLowPower.cpp` | 274 / 179 | **Separate root helpers** `apertar-standby-usb`, `apertar-standby-low-power` |
| `DirectProxyStub.{c,map}` | 45 / 9 | **Separate lib** `build/apertar-runtime/libproxy.so.1` |

### `qml/`

| File | Lines | Screen / role |
| --- | --- | --- |
| `Main.qml` | 945 | Root `Window`. Page switching, rotation, settings overlay loader, power/auto-off overlays |
| `CameraPage.qml` | **4160** | Live view: preview, overlays, top stats, quick menu, record button, info lines |
| `SettingsPage.qml` | **9851** | All settings sections and their popups. Overlay on the camera page |
| `ClipBrowserPage.qml` | 1025 | Clip grid over `/media/RAW` |
| `ClipPlayerPage.qml` | 2272 | DNG/MLV/movie playback |
| `ExternalMonitorWindow.qml` | 1347 | HDMI monitor window (both in-process and monitor-only) |
| `SettingsChoice.qml` | 346 | Label + value + dropdown popup |
| `InlineDropdownField.qml` | 349 | Dropdown used inside settings cards |
| `MonitoringRow.qml` | 497 | Settings row: title, toggle (`TogglePill`), up to N `SettingsChoice`s, favourite star |
| `TogglePill.qml` | 65 | On/off pill, emits `toggled(bool)` |
| `AdjustNumberTile.qml` | 133 | Label + value with `decrementRequested()` / `incrementRequested()` |
| `ActionTile`, `SystemSectionCard`, `InfoDataRow`, `AudioLevelCard`, `GyroBubbleLevel`, `DisplayCalibrationPanel`, `TimelapseIntervalDialog`, `SettingsMenuItem` | 60-281 | SettingsPage building blocks |
| `TopDropdownStat`, `RecordButton`, `ClipBrowserButton`, `StatusChip`, `InfoLine`, `AudioMeterOverlay`, `TimelapseIntervalPicker` | 75-241 | CameraPage building blocks |
| `DroppedFrameWarning`, `FalseColorLegend`, `HorizontalLevelOverlay`, `StillExposureOverlay` | 26-201 | Shared by CameraPage and ExternalMonitorWindow |
| `TimelapseIntervals.js` | 40 | Interval list shared by four files |
| `GyroOrientationIndicator.qml` | 334 | Compiled (`CMakeLists.txt:51`) but used nowhere |
| `InlineChoice.qml` | 39 | Not in the build, used nowhere |

QML file list for AOT: `Apertar-UI/CMakeLists.txt:19-52`. Non-AOT list: `qml.qrc`. Icons and fonts: `resources.qrc` (both modes).

## `main.cpp` startup

| Step | What | Ref |
| --- | --- | --- |
| 1 | GLES 2.0 default surface format, `AA_UseOpenGLES`, `AA_ShareOpenGLContexts`; `QSG_RENDER_LOOP=basic` on eglfs if unset | `src/main.cpp:250-265` |
| 2 | Register `CameraPreviewItem`. If `APERTAR_MONITOR_ONLY` → `runMonitorOnly()` and stop here | `:274-276` |
| 3 | Construct `DisplayConfigBridge` (reads `[display]`), log `Apertar display config: path=… size=WxH layout=… hdmi_external_only=…` | `:278-289` |
| 4 | Construct all bridges, wire standby fan-out (standby → stop playback, suspend meters, disconnect preview; wake → reconnect) | `:291-348` |
| 5 | Image providers `cdng`, `cdngthumb`, `cdngplay`, `video`, `videothumb` | `:350-373` |
| 6 | 23 context properties, then load `qrc:/qml/Main.qml` | `:374-400` |
| 7 | **`core-start-ready`**: if `APERTAR_CORE_START_READY_FILE` is set, write `ready\n` to it. This releases Core's start gate | `:405-420` |
| 8 | Screen choice. `hdmi_external_only` → hide the main window. Else `mainUiScreenForNormalMode()`; `windowed` → layout-test viewport | `:428-459` |
| 9 | **`main-ui-ready`**: if `APERTAR_UI_READY_FILE` is set, write it on the first `frameSwapped` (immediately with `hdmi_external_only`). +250 ms: deferred device-info refresh and INA219 monitoring | `:463-499` |
| 10 | `PreviewWindowRenderer` bound to `previewItem`; `ExternalMonitorManager` for a same-card HDMI screen | `:502-518` |

Environment on the Pi: the unit sets `XDG_RUNTIME_DIR=/run/apertar-ui` and `APERTAR_CORE_START_READY_FILE=/run/apertar-ui/core-start-ready` (Pi, 2026-10-25). `APERTAR_UI_READY_FILE` comes from the launcher, `${XDG_RUNTIME_DIR}/main-ui-ready` = `/run/apertar-ui/main-ui-ready` (`run_pi_direct.sh:79`, `:220`).

### Main screen choice (`mainUiScreenForNormalMode`, `main.cpp:90-119`)

1. One screen → that screen.
2. An "internal panel" screen (name has `dpi`/`dsi`/`lcd`/`panel`, or is exactly 720x720, `:61-73`) wins if a touch device is listed in `/proc/bus/input/devices` (`:75-88`) or there is no HDMI.
3. Else first HDMI, else primary.

This runs inside one Qt process. Which **DRM card** that process owns was already decided by `run_pi_direct.sh` (below).

### `hdmi_external_only`

| Effect | Ref |
| --- | --- |
| Main window hidden | `main.cpp:428-429` |
| `main-ui-ready` written at once (no frame needed) | `:496-497` |
| `ExternalMonitorManager` takes the HDMI screen even when it is the primary | `ExternalMonitorManager.cpp:130-141` |
| Forced off when `windowed=true` (`hdmiExternalOnly && !windowed`) | `main.cpp:514` |
| Monitor-only process shows its window regardless of the Settings toggle | `main.cpp:202-203` |

**Probable bug:** `hdmi_external_only=true` with `windowed=true` shows nothing. The main window is hidden (`:428`), the manager gets `false` (`:514`) and no settings bridge (`:517-518`), so `syncWindow()` destroys the window (`ExternalMonitorManager.cpp:162-166`). **Unconfirmed** on hardware.

### Monitor-only process (`runMonitorOnly`, `main.cpp:131-237`)

- Own `DisplayConfigBridge`, `ApertarPreviewSocketClient`, `ApertarControlBridge`, `SettingsBridge`, subscriber-mode `ExternalMonitorRuntimeBridge` (`:133-144`).
- Loads `ExternalMonitorWindow.qml` on the first HDMI screen (`:155`, `:164-172`), direct-window rendering (`:178-181`).
- Visible only when (`hdmi_external_only` or Settings "External monitor") and the main UI is on the camera page and not in standby (`:183-210`).
- **No `gyroConfigBridge`, `mediaBridge` is the runtime bridge, `audioMeterBridge` is null** (`:147-154`). The HDMI horizontal level is therefore unavailable in split-DRM mode.

## C++ bridges exposed to QML

Context property names are from `main.cpp:374-396` (normal) and `:147-154` (monitor-only).

| QML name | Class | Key properties | Key invokables | Talks to |
| --- | --- | --- | --- | --- |
| `apertarControlBridge` | `ApertarControlBridge` (`ApertarControlBridge.hpp:12`) | 43 read-only props: `fps`, `iso`, `shutterAngle`, `shutterSpeed`, `whiteBalance`, `resolution`, `recordingFormat`, `rawBitDepth`, `sensorName`, `recording`, `recordingHasDroppedFrames`, `standby`, `connected`, `lastError`, … (`:16-58`) | `apply*` (27), `setRecording`, `capturePhoto`, `setTimelapseActive`, `enterStandby`, `wakeFromStandby`, `calibrateGyro`, `refresh` (`:98-141`) | Core socket. Command table below |
| `apertarPreviewBridge` | `ApertarPreviewSocketClient` (`.hpp:15`) | `connected`, `statusText`, `frameCounter` (`:18-20`) | `connectToCore(path="/tmp/apertar-core.sock")`, `disconnectFromCore()` (`:30-31`) | Core: `preview_subscribe` |
| `settingsBridge` | `SettingsBridge` (`.hpp:13`) | ~71 R/W props: aids (`zebraEnabled`, `focusPeaking*`, `falseColor*`, `lutPreview*`, guides), `uiOrientation`, `externalMonitor*`, `photo*`, audio, battery, `sleepMode`, section orders, presets (`:17-92`) | `refreshLutPreviewOptions`, `refreshTuningFileOptions`, preset save/load/delete/export/import (`:139-142`, `:299-304`) | `UI.conf` only. Camera part of presets via `ApertarControlBridge::applyCameraPreset` (`SettingsBridge.cpp:2091`, `:2117`) |
| `displayConfigBridge` | `DisplayConfigBridge` (`.hpp:6`) | All CONSTANT: `uiWidth`, `uiHeight`, `uiLayout`, `uiRotationDegrees`, `controlsOpacity`, `zoomToggleFactor`, `windowed`, `hdmiExternalOnly`, layout bools, `configPath` (`:9-23`) | none | `apertar-hardware.conf` `[display]` |
| `powerBridge` | `Ina219Bridge` (`.hpp:7`) | `sensorAvailable`, `busVoltageV`, `currentA`, `powerW`, `batteryPercent` + text variants (`:10-18`) | none | `/dev/i2c-N` directly; default bus 4, addr `0x40` (`Ina219Bridge.cpp:45-46`) |
| `wifiBridge` | `WifiBridge` (`.hpp:10`) | `networks`, `scanning`, `wifiEnabled`, `currentSsid`, `hotspotActive`, `hotspotSsid`, `hotspotPassword`, `lastError` (`:14-26`) | `refresh`, `setWifiEnabled`, `connectToNetwork`, `disconnectCurrent`, `startHotspot`, `stopHotspot` (`:47-52`) | `nmcli` subprocess (`WifiBridge.cpp:541`). No Core command |
| `mediaBridge` | `MediaStatusBridge` (`.hpp:12`) | `mediaMounted`, `mountPath`, `remainingMinutesText`, `remainingStillsText`, `writeSpeed*`, `mountableDrives` (`:15-36`) | `ejectMedia`, `formatMedia`, `startWriteSpeedTest`, `mountDrive`, `refreshMountableDrives` (`:69-75`) | Core: `eject_media` (60 s), `format_media` (360 s), `run_media_speed_test`, `get_media_test_state` (`MediaStatusBridge.cpp:1183-1214`). `sudo -n mount` for manual mount |
| `gyroConfigBridge` | `GyroConfigBridge` (`.hpp:9`) | `driver`, `orientation`, `syncOffsetMs`, live `accel*`/`gyro*`, `levelReference*` (`:12-36`) | `setDriverName`, `setOrientation`, `setSyncOffsetMs`, `setLevelReference`, `setLivePollingRequest` (`:68-83`) | Reads/writes `apertar-hardware.conf`; polls the IMU over `/dev/i2c-N` itself (`GyroConfigBridge.cpp:1100`). Gyro calibration goes through `apertarControlBridge.calibrateGyro` → `calibrate_gyro` |
| `audioDeviceBridge` | `AudioDeviceBridge` (`.hpp:14`) | input/output device options, sample format/rate/channel options (`:18-29`) | `refresh`, `select*`, `*IdForLabel` (`:46-65`) | ALSA tools; Core `audio_capabilities` (`AudioDeviceBridge.cpp:327-347`) |
| `audioMeterBridge` | `AudioMeterBridge` (`.hpp:12`) | `inputLevel`, `inputDeviceAvailable` | `suspendMonitoring`, `resumeMonitoring` | `arecord`/`aplay` subprocesses. Releases ALSA when Core sends `prepare_recording` (`main.cpp:324-327`) |
| `systemActionBridge` | `SystemActionBridge` (`.hpp:7`) | `lastError`, `currentTimeZone`, `fanMode` | `restartCamera` (**reboots the Pi**, `SystemActionBridge.cpp:274-277`), `shutdownCamera`, `applyTimeZone`, `applyDateTime`, `applyFanMode` | D-Bus login1/timedate1, `sudo -n`, `/boot/firmware/config.txt` (`:25`) |
| `statsBridge`, `deviceInfoBridge` | `SystemStatsBridge`, `DeviceInfoBridge` | CPU/temp; model, OS, IP, RAM, storage | `setDynamicPollingEnabled` | `/proc`, `/sys` |
| `sleepManager` | `SleepManager` (`.hpp:9`) | `sleepMode`, `standby` | `restartIdleTimerNow` | Emits `userActivity` (≤1/s, `SleepManager.cpp:200-205`) → `notifyUserActivity` → `user_activity` on the event socket |
| `powerButtonBridge` | `PowerButtonBridge` (`.hpp:9`) | `available`, `pressed`, `devicePath` | none | evdev device named `pwr_button` |
| `displayCalibrationBridge` | `DisplayCalibrationBridge` (`DisplayCalibration.hpp:20`) | `target`, `profile`, `status` | `setValue`, `resetSelected` | `QSettings("CinePi","DisplayCalibration")` (`DisplayCalibration.cpp:49`) |
| `monitorRuntimeBridge` | `ExternalMonitorRuntimeBridge` (`.hpp:15`) | `cameraPageActive`, shutdown popup state, media, `recordingActive`, `timecode` (`:18-30`) | none | `$APERTAR_MONITOR_RUNTIME_SOCKET` (`ExternalMonitorRuntimeBridge.cpp:14-20`) |
| `clipModel`, `playbackController` | `ClipListModel`, `PlaybackController` | clip list; playback state | `refresh`, `removeClip`; `loadClip`, `togglePlayback`, `seekToFrame` | Filesystem |
| `cdngThumbProvider`, `cdngPlayProvider`, `videoProvider` | image providers | | `clearCache`, `prefetchAround`, `setActive` | Filesystem, libav plugin |
| `hdmiExternalOnly` | plain bool | | | `main.cpp:390` |

Not exposed to QML: `AudioMixerBridge`, `DisplayStandbyController`, `ExternalMonitorManager`, `PreviewWindowRenderer`, `DisplayCalibrationRenderer`.

### `ApertarControlBridge`: invokable → Core command

| Invokable | Core command(s) | Ref |
| --- | --- | --- |
| `applyFps` | `set_fps`, then `set_shutter_us` (keeps the angle) | `ApertarControlBridge.cpp:255-289` |
| `applyIso` | `set_iso` / `set_iso_auto` | `:291-316` |
| `applyShutterAngle`, `applyShutterSpeed` | `set_shutter_us` / `set_shutter_auto` | `:318-375` |
| `applyWhiteBalance` | `set_wb {kelvin}` / `set_wb_auto` | `:377-406` |
| `applyResolution` | `set_resolution` | `:408-427` |
| `applyRecordingFormat` | `set_record_format`, `set_lossy_dng_ratio`, `set_prores_profile` | `:429-475` |
| `applyCdngCompression` | `set_record_format` + `set_lossy_dng_ratio` or `set_cdng_compression` | `:516-548` |
| `applyProresProfile`, `applyProresColorProfile`, `applyCdngPreviewColorProfile` | `set_prores_profile`, `set_prores_color_profile`, `set_cdng_preview_color_profile` | `:477-514` |
| `applyTuningFile`, `applyRawBitDepth`, `applyH264Resolution`, `applyTimecodeMode` | `set_tuning_file`, `set_raw_bit_depth`, `set_h264_resolution`, `set_timecode_mode` | `:550-636` |
| `applyAutofocus{Mode,Range,Speed,Window}` | `set_af_mode`, `set_af_range`, `set_af_speed`, `set_af_window` | `:638-710` |
| `applyPhoto*`, `applyCaptureMode` | `set_photo_timelapse`, `set_photo_mode_enabled`, `set_capture_mode`, `set_photo_long_exposure_enabled`, `set_photo_bracketing_{enabled,ev}` | `:712-748`, `:817-820` |
| `setTimelapseActive` | `timelapse_start` / `timelapse_stop` | `:750-775` |
| `setRecording` | `record_start` (audio/gyro args read from `UI.conf`) / `record_stop` | `:777-815` |
| `capturePhoto` | `capture_photo {count, format}` | `:822-830` |
| `calibrateGyro` | `calibrate_gyro {seconds: 2.5}` | `:832-853` |
| `applyExposureCompensation`, `applyExposureMetering` | `set_exposure_compensation`, `set_exposure_metering` | `:1108-1116` |
| `enterStandby`, `wakeFromStandby` | `enter_standby`, `wake` | `:1166-1174` |
| `notifyUserActivity` | `user_activity` (id `-2`, on the event socket, no reply wait) | `:1176-1180` |
| `refresh` / timer | `get_state` (async, event socket) | `:855-873` |

## How the UI talks to Core

### Wire format

- Unix stream socket. Core binds it after the camera has started (`Apertar-Core/src/ApertarCoreApp.cpp:6838`, `:6859`).
- One JSON object per line. Request: `{"cmd":"set_iso","id":7,"value":800}`. Reply: same `id` plus `"ok":true|false`, `"error"` on failure, and state fields (`ApertarControlBridge.cpp:1046-1086`).
- Events: objects with an `"event"` key, sent to **every** connected client (`Apertar-Core/src/ipc/ControlServer.cpp:172-193`, `Apertar-Core/src/ApertarCoreApp.cpp:10823-10852`).
- Core writes with `MSG_DONTWAIT` and drops a client whose buffer is full (`ControlServer.cpp:23-29`, `:176-177`).

### Connections per UI process

| Connection | Lifetime | Used for | Ref |
| --- | --- | --- | --- |
| `ApertarControlBridge::m_eventSocket` | Persistent, `QLocalSocket` | Events; async `get_state` poll; `user_activity` | `ApertarControlBridge.cpp:116-147`, `:1557-1589` |
| `sendCoreCommand` socket | One new socket per command | Every `set_*`, `record_*`, … | `:1013-1106` |
| `ApertarPreviewSocketClient` | Persistent, raw `recvmsg` | `preview_buffer` / `preview_frame` with fds | `ApertarPreviewSocketClient.cpp:32-82` |
| `MediaStatusBridge::coreMediaCommand` | Per command, fixed id `42001` | eject/format/speed test | `MediaStatusBridge.cpp:20-43` |
| `AudioDeviceBridge` | Per probe | `audio_capabilities` | `AudioDeviceBridge.cpp:327-347` |

The monitor-only process opens its own event, command and preview connections.

### Polling and reconnect

| Item | Value | Ref |
| --- | --- | --- |
| `get_state` interval while disconnected | 1 s | `ApertarControlBridge.cpp:17`, `:875-882` |
| `get_state` interval while connected | 30 s (events carry the rest) | `:18` |
| `get_state` timeout | 10 s, then the event socket is aborted | `:867-872` |
| Preview reconnect | 1 s single-shot | `ApertarPreviewSocketClient.cpp:16-22`, `:120-126` |
| Socket path override | `APERTAR_CONTROL_SOCKET` (control, media, audio). **The preview client ignores it**: QML calls `connectToCore()` with the default (`Main.qml:207`) | `ApertarControlBridge.cpp:1032`, `ApertarPreviewSocketClient.hpp:30` |

### `sendCoreCommand` (how a `set_*` is sent)

1. New `QLocalSocket`, connect timeout 350 ms. Failure → `connected=false`, `lastError="Waiting for ApertarCore control socket..."` (`ApertarControlBridge.cpp:1015`, `:1034-1044`).
2. Write `{"cmd":…, "id":N, …args}` + `\n` (`:1045-1058`).
3. **Block the GUI thread** reading lines until the matching `id` arrives. Every line read (including broadcast events) goes through `applyCoreMessage` first (`:1063-1074`).
4. Reply timeout: 3 s default; 10 s for reconfigure commands (`set_resolution`, `set_capture_mode`, `set_raw_bit_depth`, `set_record_format`, `set_tuning_file`, colour profiles, `set_h264_resolution`, `capture_photo`, `timelapse_start`, `wake`, `enter_standby`, `apply_preset`); 8 s `calibrate_gyro`; **60 s `record_stop`** (`:1016-1031`).
5. Timeout → `connected=false`, `lastError="Timed out waiting for ApertarCore reply."` (`:1099-1105`).

**Finding: UI freezes during slow commands.** The touch UI cannot repaint while `sendCoreCommand` waits (up to 60 s for `record_stop`, 360 s for `format_media` in `MediaStatusBridge.cpp:1192`). **Probable side effect:** during a long block the UI's persistent sockets stop draining. Core keeps broadcasting `preview_frame` lines with `MSG_DONTWAIT` and drops the client when the buffer fills (`ControlServer.cpp:25-29`), so the preview and event sockets may reconnect after the block. Settle with `journalctl -u apertar-ui-direct | grep -i 'socket closed\|Waiting for'` after a long `record_stop`.

### How a Core state field becomes a QML property

`applyCoreMessage` (`ApertarControlBridge.cpp:1182-1259`) routes by `event`. `applyCoreState` (`:1261-1555`) reads keys and calls a setter that emits the NOTIFY signal only on change (pattern: `setFps`, `:2230-2237`).

| Core key | Property | Ref |
| --- | --- | --- |
| `fps` | `fps` (formatted) | `:1368-1369` |
| `iso`, `iso_auto` | `iso`, `autoExposureEnabled` | `:1324-1325`, `:1373-1374` |
| `shutter_us`, `shutter_auto` | `shutterAngle`, `shutterSpeed` | `:1327-1328`, `:1383-1384` |
| `wb_kelvin`, `wb_auto`, `wb_available` | `whiteBalance`, `whiteBalanceAvailable` | `:1357-1365`, `:1389-1390` |
| `width`+`height` or `resolution` | `resolution` | `:1395-1406` |
| `sensor` (or `capture.sensor`) | `sensorName` | `:1314-1321` |
| `standby` or `state=="standby"` | `standby` | `:1305-1308` |
| `recording_has_dropped_frames`, `recording_error` | `recordingHasDroppedFrames`, `recordingFailed` signal | `:1269-1284` |
| `recording_capabilities.{raw_compression,raw_recording,prores,h264_hardware,h264_max_width,h264_max_fps}` | capability props | `:1285-1300` |
| `preview_exposure_reference` | `previewExposureReference` → `CameraPreviewItem.exposureReference` | `:1263-1268`; `CameraPage.qml:1994` |

Events with their own handling: `audio_level` → `audioInputLevel`; `recording` → `recording` + `recordingFailed`; `timelapse`, `timelapse_frame`, `photo_capture`, `photo_write_error`; `prepare_recording` → release ALSA; `hardware_action` → `hardwareActionTriggered(action)` (`:1182-1259`). Main.qml acts on `power_button_press`, `standby_power_sleep`, `standby_power_wake`, `zoom_toggle`, `settings`, `clip_browser`, `quick_menu` (`Main.qml:285-332`).

**CameraPage keeps its own copies.** It has `property string iso: "800"` (`CameraPage.qml:341`), refreshed by a `Connections { target: root.controlBridge }` block (`:1824`, e.g. `onIsoChanged` at `:1843-1846`) and set optimistically on selection (`:2940-2944`). A new Core-backed value shown on the camera page needs the same three pieces.

### UI settings that Core also changes (`UI.conf`)

Monitoring aids, photo options, audio options etc. are **not** sent as socket commands by the touch UI. They are written to `UI.conf`:

| Writer | How | Ref |
| --- | --- | --- |
| Touch UI | `SettingsBridge` setter → `m_settings.setValue` + `sync()` | `SettingsBridge.cpp:597-607` (zebra) |
| Core (WebUI `set_zebra_enabled` etc.) | Rewrites `[General]` under a Qt-compatible lock file | `Apertar-Core/src/ApertarCoreApp.cpp:1850-1861` |
| Monitor-only process, network helper | Own `QSettings("CinePi","UI")` | `main.cpp:139`, `WifiBridge.cpp:125-137` |

Readers notice changes via `QFileSystemWatcher` plus a 10 s poll (`SettingsBridge.cpp:411-431`, `pollExternalSettings` at `:502`). The service deletes a stale `UI.conf.lock` before start (Pi, 2026-10-25).

### Preview frame delivery

| Step | What | Ref |
| --- | --- | --- |
| 1 | Client sends `{"cmd":"preview_subscribe","id":0}` | `ApertarPreviewSocketClient.cpp:142-165` |
| 2 | Core replays current buffer registrations (`enqueueCurrentPreviewRegistrations`) | `Apertar-Core/src/ApertarCoreApp.cpp:10796-10799` |
| 3 | `preview_buffer` (once per slot): `slot`, `width`, `height`, `stride`, `capture_*`, `plane_count`, `layout_plane_count`, `planeN_offset/pitch/length`, `fd_attached:true`, plus 1-3 dma-buf fds via `SCM_RIGHTS` | Core `:10903-10940`; UI `:353-451` |
| 4 | `preview_frame` (every frame): `slot`, `frame_id`, `timestamp_us`, no fds. UI looks up the registered slot | Core `:10907-10912`, `:10942`; UI `:453-512` |
| 5 | `previewFrameReady` → `PreviewWindowRenderer` schedules a window update (DirectConnection) | `PreviewWindowRenderer.cpp:428-444` |
| 6 | On `beforeRenderPassRecording`: import fds as `EGLImage` (`DRM_FORMAT_YUV420`, Rec.709 narrow range) into `GL_TEXTURE_EXTERNAL_OES`, cached per dma-buf; draw with the aid shaders **under** the QML scene | `:405-407`, `:1604`, `:1740-1770`, `:2388` |

Parsing is hand-rolled substring search for `"key":` (`ApertarPreviewSocketClient.cpp:585-625`), not a JSON parser. It breaks if Core ever emits whitespace before a colon.

Fallbacks: planar `mmap` upload (`PreviewWindowRenderer.cpp:1294`), CPU conversion (`:1411`); env `APERTAR_PREVIEW_FORCE_{CPU,PLANAR,EGL}`; Pi 3 forces planar (`:295`).

**Finding: every client gets the preview stream.** `broadcast`/`broadcastWithFds` go to all clients (`ControlServer.cpp:172-193`). The control event socket and each short-lived command socket therefore also receive `preview_frame` lines at frame rate and parse them with `QJsonDocument` on the GUI thread (`ApertarControlBridge.cpp:1572-1588`). The dma-buf fds attached to `preview_buffer` are dropped by the kernel for `QLocalSocket` readers (plain `read()`).

**Peaking quirks:** texel size is hard-coded `1/1920 x 1/1080` (`PreviewWindowRenderer.cpp:858`), so peaking sensitivity depends on preview size. Default threshold is `0.08` in `CameraPreviewItem.hpp:137` but `0.04` in `PreviewWindowRenderer.hpp:132` and `CameraPage.qml:1984`.

## QML structure

### `Main.qml`

| Item | Ref |
| --- | --- |
| Root `Window`, size from `displayConfigBridge.uiWidth/uiHeight` | `Main.qml:5`, `:13-14` |
| Page state: `property string currentPage: "camera"` (`"camera"`, `"browser"`, `"player"`). No StackView | `:16` |
| `settingsOpen` flag; CameraPage's `onOpenSettingsRequested` sets it | `:17`, `:506` |
| Layout flags from `displayConfigBridge.uiLayout` | `:41-47` |
| Rotation = Settings `uiOrientation` (Left 90 / Right -90 / Upside Down 180) + `[display] ui_rotation`, applied as a `Rotation` on `uiScene` | `:56-61`, `:474-486` |
| `Component.onCompleted`: `apertarPreviewBridge.connectToCore()` | `:204-211` |
| `hardware_action` handler | `:285-332` |
| `CameraPage` (always instantiated, `settingsState: settingsBridge`) | `:496-517` |
| `SettingsPage` Loader, overlay on the camera page; preloaded after the first preview frame | `:535-578`, `:88-91` |
| `ClipBrowserPage` Loader (`currentPage==="browser"`), back → camera | `:580-607` |
| `ClipPlayerPage` Loader (`currentPage==="player"`), back → browser | `:609-640` |
| Auto-power-off and power-button shutdown cards | `:657-752`, `:774-945` |

Navigation: set `root.currentPage` (`Main.qml:314`, `:321`, `:423`, `:461`, `:509`, `:601`, `:634`).

### `CameraPage.qml` landmarks

| Lines | Item |
| --- | --- |
| `:33-56` | `settingsState`, `displayLayout` and layout flags |
| `:341` | Local copies of Core values (`iso`, …) |
| `:392-443`, `:1052-1191` | Hard-coded per-sensor resolution/crop tables |
| `:1554` | `syncControlValuesFromBridge()` |
| `:1692-1707` | Timecode computed in QML (Free Run = wall clock, Rec Run = frame counter), not from Core |
| `:1824-1897` | `Connections` to `controlBridge` |
| `:1966-2548` | `previewContainer` (objectName `previewContainer`) with `CameraPreviewItem` `previewItem` at `:1973-1997` |
| `:2886`, `:2918`, `:2950`, `:2990` | `TopDropdownStat` FPS / ISO / shutter / WB |
| `:3116` | Quick menu panel |
| `:3578` | `InfoLine`s |
| `:3689`, `:3712`, `:3772` | `ClipBrowserButton`, `AudioMeterOverlay`, `RecordButton` |
| `:3980-4160` | Record-error scrim and warning card |

### `SettingsPage.qml` landmarks

| Lines | Item |
| --- | --- |
| `:15` | `selectedSection: "Monitoring"` |
| `:18-30` | Layout flags and size tokens |
| `:110-225` | Hard-coded imx477 / imx294 / imx585 / H.264 resolution lists |
| `:771-826` | Default item order per section (`defaultMonitoringOrder`, …) |
| `:827` | `defaultSidebarOrder` (Power is shown as "Media", `:1122`) |
| `:2216-2384` | `monitoringComponentForId` and siblings: item id → `Component` |
| `:2385-6110` | One `Component` per settings item (e.g. zebra `:2686-2713`) |
| `:6330-7212` | Layout: header, sidebar `ListView` (`:6416`), section `Flickable` (`:6474`) |
| `:7213-9851` | Popups: favourites, reorder, keyboards, format/eject/power confirms and errors |

### Key components

| Component | Inputs | Outputs | Ref |
| --- | --- | --- | --- |
| `SettingsChoice` | `label`, `value`, `options`, `optionDisplayFormatter`, `popupParent`, `dropdownController`, `openUpwards` | `valueSelected(string)` | `qml/SettingsChoice.qml:6-16`, `:33` |
| `TogglePill` | `checked` | `toggled(bool)` | `qml/TogglePill.qml:6`, `:18` |
| `AdjustNumberTile` | `label`, `value` | `decrementRequested()`, `incrementRequested()` | `qml/AdjustNumberTile.qml:6-7`, `:18-19` |
| `MonitoringRow` | `title`, `titleIconSource`, `description`, `enabled`, `choice1Label/Value/Options`, … | `toggleRequested`, `choice1Selected(v)`, `favoriteToggleRequested`, `pressAndHoldRequested` | signals `MonitoringRow.qml:93-102`; used at `SettingsPage.qml:2689-2712`; `SettingsChoice` at `MonitoringRow.qml:404` |
| `TopDropdownStat` | `value`, `options` | `optionSelected(string)` | `TopDropdownStat.qml:23`; used at `CameraPage.qml:2918-2948` |

Each component derives its own size from `displayConfigBridge.uiLayout` with nested ternaries (`TogglePill.qml:7-21`, `AdjustNumberTile.qml:8-23`).

**Trap: the same flag name means different things in different files.** `standardLandscapeLayout` is `landscape || landscape_large` in `Main.qml:43-44` and `CameraPage.qml:45-46`, but only `landscape` in `SettingsPage.qml:23`. `DisplayConfigBridge` also exports C++ layout bools (`DisplayConfigBridge.hpp:17-22`) that QML mostly ignores.

## `run_pi_direct.sh`

| Lines | What |
| --- | --- |
| `:5-11` | `$1` = UI binary (default `$HOME/ApertarUI/build/Apertar-UI`), rest passed through |
| `:13-39` | **Runtime mirror.** Root `APERTAR_RUNTIME_ROOT` / `APERTAR_NVME_RUNTIME_ROOT` / `~/.cache/apertar-runtime`. Mode `APERTAR_USE_RUNTIME_MIRROR` (default `auto`). `auto` skips a mirror on the same filesystem (`:23-31`). Used only if `stat %s:%Y` of the build binary equals `ui-build.signature` (`:32`); then exports `QT_PLUGIN_PATH`, `QML2_IMPORT_PATH` (`:33-37`) |
| `:41-71` | **Mesa-minimal.** If `mesa-minimal/lib/aarch64-linux-gnu/libgbm.so.1` and `share/glvnd/egl_vendor.d/50_mesa.json` exist: prepend to `LD_LIBRARY_PATH` (plus `build/apertar-runtime` for the libproxy stub), set `GBM_BACKENDS_PATH`, `LIBGL_DRIVERS_PATH`, `__EGL_VENDOR_LIBRARY_FILENAMES`. The libproxy stub is only used inside this branch (`:57-58`) |
| `:78-81` | `DRM_SYSFS`, `MAIN_UI_READY_FILE=${XDG_RUNTIME_DIR:-/tmp}/main-ui-ready`, `headless-ready`; both removed |
| `:83-136` | Enumerate `card*-*/status` (skip Writeback). Internal = `*-DSI-*`, `*-DPI-*`, `*-LVDS-*`, `*-eDP-*`, counted only if `connected`. HDMI = `*-HDMI-A-*`, tracked as connected and as available |
| `:138-166` | **Selection.** (1) Any connected internal → MAIN = first internal; MONITOR = first connected HDMI, else first available HDMI. (2) Else connected HDMI → MAIN = first; MONITOR = second connected, else another available. (3) Else first connected anything |
| `:168-186` | **Headless.** No screen: touch `headless-ready` and `APERTAR_CORE_START_READY_FILE`, poll 1 s, `exec` self when a connector connects |
| `:188-205` | MAIN/MONITOR card = `/dev/dri/<cardN>` from the connector name (override `APERTAR_UI_DRM_DEVICE`, `APERTAR_MONITOR_DRM_DEVICE`). Write `{"device":…,"hwcursor":false}` to `$XDG_RUNTIME_DIR/apertar-display-$UID/main-kms.json`. No per-connector mode or rotation |
| `:207-221` | `QT_QPA_PLATFORM=eglfs`, `eglfs_kms`, KMS config, hotplug on, evdev unless `APERTAR_QT_USE_LIBINPUT=1`, `QSG_RENDER_LOOP=basic`, `APERTAR_MONITOR_RUNTIME_SOCKET`, `APERTAR_UI_READY_FILE`; unset `DISPLAY`, `WAYLAND_DISPLAY` |
| `:223-228` | Log line `Apertar direct display: UI=<connector> (<card>) monitor=…` |
| `:244-322` | **Split DRM** (monitor card ≠ main card). Supervisor loop every 0.5 s: HDMI disconnected → stop child; connected but no `main-ui-ready` → wait; ready → start `APERTAR_MONITOR_ONLY=1` child with input disabled and `monitor-kms.json`; child died → restart |
| `:324-382` | **Same-card hotplug.** UI in background plus a watcher that hashes the same-card HDMI statuses every 0.5 s. On change: touch `restart-for-hdmi-hotplug`, SIGTERM the UI, `exec` self to re-enumerate KMS |
| `:384` | Simple case: run the UI in the foreground |

**Phantom connector trap** (diagnosed 2026-10-23, `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md` §4.5): a DPI overlay with no panel reports `connected`, wins rule (1), and pushes HDMI to the monitor role. The Pi had its DPI overlays disabled on 2026-10-23, so HDMI is now MAIN under rule (2).

**Probable current topology:** HDMI is on the vc4 card and DPI/DSI are separate RP1 DRM devices on a Pi 5, so a DPI rig ran split-DRM and today's HDMI-only rig runs the same-card path with HDMI-A-2 as the waiting monitor. **Unconfirmed.** Settle with `ls /sys/class/drm` and `journalctl -b -u apertar-ui-direct | grep 'direct display'`.

`Restart=on-failure` and `KillMode=control-group` in the unit (Pi, 2026-10-25) cover crashes and the monitor child. The script itself has no crash relaunch loop.

### The unit (Pi, 2026-10-25)

`apertar-ui-direct.service` is not in the repo. On the Pi:

- `User=pi`, `SupplementaryGroups=video render input`, `WorkingDirectory=/home/pi/ApertarUI`.
- `Environment=XDG_RUNTIME_DIR=/run/apertar-ui`, `APERTAR_CORE_START_READY_FILE=/run/apertar-ui/core-start-ready`; drop-in `QT_QPA_EGLFS_HIDECURSOR=1`. `RuntimeDirectory=apertar-ui`.
- `TTYPath=/dev/tty1`, `Conflicts=getty@tty1.service display-manager.service`.
- `ExecStartPre`: remove `/home/pi/.config/CinePi/UI.conf.lock` and both ready files; `plymouth deactivate`.
- `ExecStart=/home/pi/ApertarUI/run_pi_direct.sh /home/pi/ApertarUI/build/Apertar-UI`.
- `ExecStartPost=+/home/pi/ApertarUI/finish_plymouth_handoff.sh /run/apertar-ui/main-ui-ready`. That script waits ≤20 s for `main-ui-ready` or `headless-ready`, then `plymouth quit --retain-splash` (`finish_plymouth_handoff.sh:5-28`).
- `Restart=on-failure`, `KillMode=control-group`, `Nice=-5`.

Outside the unit, the defaults diverge: `run_pi_direct.sh:79` falls back to `/tmp/main-ui-ready`, while `finish_plymouth_handoff.sh:5` and the network gate use `/run/apertar-ui/…`. A manual run without `XDG_RUNTIME_DIR` therefore never releases those waits early.

## External monitor (HDMI)

| Topology | Mechanism | Ref |
| --- | --- | --- |
| HDMI on the main card | `ExternalMonitorManager` creates `ExternalMonitorWindow.qml` on a second `QScreen` in the same process; destroyed when leaving the camera page | `ExternalMonitorManager.cpp:162-186`, `:188-262` |
| HDMI on another card | Separate monitor-only process (above), state over `ExternalMonitorRuntimeBridge` | `run_pi_direct.sh:244-322`, `main.cpp:131-237` |

Feeds: "Clean Feed" vs "Assist Feed" (`SettingsBridge.cpp:289-294`). Assist enables zebra, peaking, false colour, grayscale on HDMI (`ExternalMonitorWindow.qml:366-390`).

## Separate binaries built here

| Binary | Source | Runs as / from | What it does | Ref |
| --- | --- | --- | --- | --- |
| `apertar-network-helper` | `src/NetworkHelper.cpp` + `WifiBridge.cpp` | `apertar-network.service`, `User=pi`, `/home/pi/ApertarUI/build/` (Pi, 2026-10-25) | Headless hotspot fallback. Lock `/run/apertar-network/helper.lock`, marker `/run/apertar-network/managed` | `NetworkHelper.cpp:13-30`; `CMakeLists.txt:156-158` |
| `apertar-cfe-automounter` | `src/CfeAutomounter.cpp` | `apertar-cfe-automounter.service`, `/usr/local/libexec/` (Pi, 2026-10-25) | CFE hat buttons + LED over I2C, mount/eject NVMe at `/media/RAW`, PCIe reset. Writes `/run/apertar-cfe/ready` | below |
| `apertar-standby-usb` | `src/StandbyUsbPower.cpp` | root via `sudo -n` from Core, `/usr/local/libexec/` | Pi 5 onboard USB ports off/on in standby; refuses if USB storage/network/swap is in use | `systemd/apertar-standby-usb.sudoers:1`; `Apertar-Core/src/ApertarCoreApp.cpp:1541-1545` |
| `apertar-standby-low-power` | `src/StandbyLowPower.cpp` | root via `sudo -n` from Core | `cpu`/`nvme`/`bluetooth`/`all`/`restore`: governor, NVMe runtime PM, rfkill. State in `/run/apertar-standby-low-power` | `systemd/apertar-standby-low-power.sudoers:1`; `ApertarCoreApp.cpp:1547-1550` |
| `libproxy.so.1` | `src/DirectProxyStub.c` | `LD_LIBRARY_PATH` from the launcher | Fake libproxy, always `direct://`, keeps Debian's proxy stack out of cold start | `DirectProxyStub.c:18`; `CMakeLists.txt:169-182` |
| `apertar-video-libav.so` | `src/VideoPlaybackLibav.cpp` | `QLibrary` from the UI on first movie | FFmpeg decode for ProRes/H.264 playback. ABI v2, entry `apertar_video_api` | `VideoPlaybackLibav.cpp:222`; `VideoPlayback.cpp:18-36`; `CMakeLists.txt:132-147` |
| `apertar-wait-ui-core-start` | `wait_for_ui_core_start.sh` (script) | `ExecStartPre` of Core (Pi) and of the network gate drop-in | Wait ≤N s for a ready file; skip if no display; always exit 0 | `wait_for_ui_core_start.sh:5-56` |

### `apertar-cfe-automounter`

| Item | Ref |
| --- | --- |
| Config: first of `$APERTAR_HARDWARE_CONFIG`, `/home/pi/…`, `/boot/firmware/…`, `/boot/apertar-hardware.conf`; `[cfexpress_hat] enabled, bus (default 10), address (0x34)`; `[storage] mount_path, pcie_controller` | `CfeAutomounter.cpp:38-39`, `:114-195` |
| `--check-config` prints the parsed config and exits | `:760-771` |
| Button read (`I2C_SMBUS` byte; bit 0 insert, bit 1 eject; `0x69` ignored), LED write with 5 retries | `:402-422`, `:423-445` |
| Main loop every 100 ms: insert edge → `mountPcie`, eject edge → `unmountPcie` | `:520-557` |
| Mount via `mount(2)`: ntfs → `ntfs3`, exfat/vfat with uid/gid 1000, ext4 | `:591-630` |
| PCIe reset: unbind/bind `brcm-pcie`, `pci/rescan` | `:632-648` |
| Ready file `/run/apertar-cfe/ready` written / removed | `:530-531`, `:559` |

It notifies nobody. The UI sees the mount through its 1 s poll (`MediaStatusBridge.cpp:266-274`).

### Network helper vs in-UI Wi-Fi

- Same `WifiBridge` class in both. When `/run/apertar-network/managed` exists, the UI's copy disables its own auto-hotspot (`WifiBridge.cpp:155-157`, `:478-484`).
- Both read hotspot SSID/password from `UI.conf`. Hard-coded defaults `Apertar` / `apertarcam` (`WifiBridge.hpp:116-117`).
- Hotspot delay `[network] hotspot_delay_seconds` (default 60) from `$APERTAR_HARDWARE_CONFIG` or `/home/pi/apertar-hardware.conf` only, no `/boot` fallback (`WifiBridge.cpp:18-34`). Tick 10 s (`:16`).
- NetworkManager connection name `"Apertar Hotspot"` (`:15`). Polkit grants `pi` the needed actions (`systemd/49-apertar-network.rules:1-12`).

## Where to change X

| Change | Files and steps |
| --- | --- |
| **Add a UI-only settings control** (an aid, an overlay option) | 1. `SettingsBridge.hpp`: `Q_PROPERTY` + getter/setter/signal (pattern `:17`). 2. `SettingsBridge.cpp`: load in the constructor (`:395-407` style), setter with `setValue`+`sync` (`:597-607`), add to `pollExternalSettings` (`:502`) so other processes see it. 3. `SettingsPage.qml`: a `Component` (copy zebra `:2686-2713`), an id in `default*Order` (`:771-826`), a branch in `*ComponentForId` (`:2216`). 4. Consume it where needed (e.g. bind on `CameraPreviewItem`, `CameraPage.qml:1973-1997`). 5. If the WebUI must change it too, Core's `set_*` handler writes `UI.conf` (core.md) |
| **Add a control that changes the camera** | 1. Check the Core command exists (`Apertar-Core/src/ApertarCoreApp.cpp:9216` lists them). 2. `ApertarControlBridge`: `Q_INVOKABLE bool applyX(...)` → `sendCoreCommand("set_x", {{"value", v}})` (pattern `:1108-1110`). Add the name to the reconfigure list (`:1016-1028`) if it reconfigures the camera. 3. Call it from QML (`root.controlBridge.applyX(v)`) |
| **Add a QML property backed by Core state** | 1. `ApertarControlBridge.hpp`: `Q_PROPERTY(T x READ x NOTIFY xChanged)` + member + setter. 2. `applyCoreState` (`.cpp:1261-1555`): `if (state.contains("x")) setX(...)`. 3. Make sure Core puts `x` in `get_state` (`ApertarCoreApp.cpp:9218`) or in a `settings` event. 4. QML: bind `apertarControlBridge.x`, or on CameraPage add a local copy + `Connections` handler (`CameraPage.qml:341`, `:1824`, `:1843`) |
| **Add a page** | 1. New `qml/MyPage.qml`. 2. Add it to `APERTAR_QML_FILES` (`CMakeLists.txt:19-52`) **and** `qml.qrc` (non-AOT; note `DroppedFrameWarning.qml` is missing there). 3. `Main.qml`: a `Loader` with `active: root.currentPage === "mine"` (copy `:580-607`) and a way to set `currentPage`. 4. Hide it from `ExternalMonitorManager` logic if needed: the HDMI window only shows on `"camera"` (`ExternalMonitorManager.cpp:111-126`) |
| **Change layout per display size** | `[display] ui_width/ui_height/ui_layout` (config.md). Auto layout thresholds: `DisplayConfigBridge.cpp:478-524`. Per-page flags: `Main.qml:41-47`, `CameraPage.qml:33-56`, `SettingsPage.qml:18-30`. Per-component sizes: ternaries in each component (`TogglePill.qml:20-21`). Restart the UI; `[display]` is CONSTANT |
| **Change which screen gets the touch UI** | `run_pi_direct.sh:138-166` (which DRM card), then `main.cpp:90-119` (which `QScreen` in the process). `hdmi_external_only` for monitor-only HDMI |
| **Change HDMI monitor content** | `qml/ExternalMonitorWindow.qml`. Monitor-only process context: `main.cpp:147-154` |
| **Change preview aids (shaders)** | `PreviewWindowRenderer.cpp` `initializePipeline` (`:678-1220`); properties via `CameraPreviewItem.hpp:11-30` |
| **Change boot-time handoff** | `main.cpp:405-420` (core gate), `:463-499` (first frame), `finish_plymouth_handoff.sh`, `wait_for_ui_core_start.sh` |
| **Change CFE hat behaviour** | `src/CfeAutomounter.cpp`, rebuild, **copy to `/usr/local/libexec`** (build.md) |

## Inconsistencies and dead code

| Item | Ref |
| --- | --- |
| Two different default `apertar-hardware.conf` templates in the UI (`[ina219] bus=4`) plus a third in Core | `DisplayConfigBridge.cpp:41-326`, `Ina219Bridge.cpp:69-341`, `Apertar-Core/src/ApertarCoreApp.cpp:4294` |
| Six config-path implementations; WifiBridge's has no `/boot` fallback | `DisplayConfigBridge.cpp:25-39`, `Ina219Bridge.cpp:48`, `GyroConfigBridge.cpp:195`, `CfeAutomounter.cpp:114-129`, `WifiBridge.cpp:18-24` |
| `[storage] mount_path` honoured by the automounter, but the UI hard-codes `/media/RAW` | `MediaStatusBridge.hpp:136`, `cliplistmodel.cpp:174`, `SettingsBridge.cpp:148` |
| Dead: `startNvmeReinsertWatcher` (embedded Python), `detachNvmeController`, `mountFormattedDevice`, `flushMedia` in `MediaStatusBridge` (declared at `.hpp:115-123`, never called) | `MediaStatusBridge.cpp:711`, `:742-972`, `:1039`, `:1046` |
| `DroppedFrameWarning.qml` in `CMakeLists.txt` but not in `qml.qrc` (non-AOT builds) | `CMakeLists.txt:40`; `grep -c DroppedFrameWarning qml.qrc` = 0 |
| UI polls the IMU over I2C itself while Core records from it | `GyroConfigBridge.cpp:1100`; `Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp` |
| Three `QSettings` org names: `CinePi/UI`, `CinePi/DisplayCalibration`, `Apertar/StandbyBacklights` | `SettingsBridge.cpp:287`, `DisplayCalibration.cpp:49`, `SleepManager.cpp:56` |
| Peaking texel and default threshold (above) | `PreviewWindowRenderer.cpp:858`, `CameraPreviewItem.hpp:137` |

## Unconfirmed

| Claim | Settle with |
| --- | --- |
| Current topology is same-card (single Qt process) | `ls /sys/class/drm; journalctl -b -u apertar-ui-direct \| grep 'direct display'` |
| Long `record_stop`/`format_media` makes Core drop the UI's sockets | Stop a long take, then `journalctl -u apertar-ui-direct --since -2min \| grep -i 'socket\|Waiting'` |
| `hdmi_external_only` + `windowed` shows nothing | Set both in `[display]`, restart the UI, look at HDMI |
| The network start-gate drop-in is installed | `systemctl cat apertar-network` |
| `/usr/local/libexec/apertar-wait-ui-core-start` equals `wait_for_ui_core_start.sh` | `diff /usr/local/libexec/apertar-wait-ui-core-start ~/ApertarUI/wait_for_ui_core_start.sh` |
