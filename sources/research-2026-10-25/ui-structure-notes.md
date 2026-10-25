
# Apertar-UI: UI structure notes for ui.md

All paths are relative to the repo root `Apertar-UI/`. I made no edits and ran no git commands that change anything. Anything marked UNCONFIRMED was inferred from code and not checked at runtime.

## 0. Repo layout and non-source dirs
- `build/` is **not tracked in this fork**. `.gitignore:1-4` says so ("Upstream commits its build/ tree; this fork does not"), and `git ls-files build` returns 0. A local build tree exists on disk.
- `mesa-minimal/` is a prebuilt, trimmed Mesa: libEGL_mesa, libgbm, `libgallium-26.2.0.so`, gbm backend, `share/glvnd/egl_vendor.d/50_mesa.json`. It is tracked (18 files). Its purpose (`run_pi_direct.sh:41-44`) is to load only the VC4/V3D drivers instead of the LLVM-enabled system Gallium. Deleting the directory falls back to system Mesa.
- `third_party/liblj92/` is a vendored lossless-JPEG decoder from cgohlke/imagecodecs@07b0383, with one local fix: the zero diff-category shift (`third_party/liblj92/README.apertar.md`). It is compiled into ApertarUI (`CMakeLists.txt:123`) and used by `src/dngdecoder.cpp:16,54-63`.
- `.github/` holds only `FUNDING.yml`. There is no CI.
- Neither `apertar-ui-direct.service` (named in `README.md:284`) nor `apertar-core.service` is in this repo. The only unit here is `systemd/apertar-network.service`.

## 1. Source map

### CMake targets
| CMake target | Output file | Sources | Notes |
|---|---|---|---|
| `ApertarUI` | `Apertar-UI` | `CMakeLists.txt:63-130` | Main Qt app. **`OUTPUT_NAME "Apertar-UI"` is set only inside `if(EXISTS "/usr/lib/qt6/libexec/moc")` (`CMakeLists.txt:252-260`).** On a host without that path, the binary is named `ApertarUI`, but `run_pi_direct.sh:5` and `sync_pi_runtime.sh:8` expect `build/Apertar-UI`. |
| `apertar-video-libav` | `apertar-video-libav.so` (MODULE, `PREFIX ""`) | `src/VideoPlaybackLibav.cpp` (`CMakeLists.txt:139-144`) | Built only when pkg-config finds libavcodec/format/util/swscale. ApertarUI does not link it; it only depends on it being built (`:143`). It is `dlopen`ed at runtime. Installs to `lib/apertar-ui`. |
| `ApertarCfeAutomounter` | `apertar-cfe-automounter` | `src/CfeAutomounter.cpp` (`:149,159-167`) | Plain C++17 plus Threads. No Qt. |
| `ApertarStandbyUsbPower` | `apertar-standby-usb` | `src/StandbyUsbPower.cpp` (`:150,154-155`) | Root helper invoked via sudoers. |
| `ApertarStandbyLowPower` | `apertar-standby-low-power` | `src/StandbyLowPower.cpp` (`:151-153`) | Root helper invoked via sudoers. |
| `ApertarNetworkHelper` | `apertar-network-helper` | `src/NetworkHelper.cpp` + `src/WifiBridge.cpp` (`:156-158`) | QtCore-only daemon. Reuses the WifiBridge class. |
| `ApertarDirectProxy` | `build/apertar-runtime/libproxy.so.1` (SHARED, `SOVERSION 1`) | `src/DirectProxyStub.c` + `.map` (`:172-182`) | Stub that replaces libproxy (see below). |

**What `ApertarDirectProxy` is:**
- It is a fake `libproxy.so.1`. It exports the 4 `px_proxy_factory_*` symbols under the `LIBPROXY_0.4.16` version tag (`src/DirectProxyStub.map:1-9`) and always returns `"direct://"` (`src/DirectProxyStub.c:18-35`).
- Rationale (`CMakeLists.txt:169-171`): QtNetwork pulls in Debian's desktop proxy-discovery stack. Putting this stub first on `LD_LIBRARY_PATH` keeps that dependency tree off the cold-boot path.
- `run_pi_direct.sh` puts `build/apertar-runtime` on `LD_LIBRARY_PATH` (`:57-58`), but only inside the mesa-minimal branch (`:55`). Without mesa-minimal the stub is never used.

**Build options and linking:**
- `APERTAR_QML_AOT`: ON for native builds, OFF when cross-compiling (`:56-61`).
  - ON: `qt_add_qml_module` with URI `Apertar.UI` and prefix `/` (`:184-196`).
  - OFF: the `qml.qrc` resource file is used instead (`:197-200`).
- `APERTAR_HAS_DISPLAY_POWER=1` when the Qt6::GuiPrivate headers exist (`:221-242`). This enables DPMS through the private `QPlatformScreen` API.
- The main app links with `-z,lazy` to defer PLT binding (`:244-249`).
- External libraries: Qt6 Core, DBus, Gui, Network, Qml, Quick, QuickControls2, plus GL, EGL, GLESv2 and TIFF (`:207-219`).

### src/ files (one line each)
| File | Responsibility |
|---|---|
| `main.cpp` | Process entry. Two modes: normal UI and `APERTAR_MONITOR_ONLY` (HDMI helper process). Picks screens, exposes bridges, writes ready markers. |
| `ApertarControlBridge.{hpp,cpp}` | JSON-lines control and state client to Core on `/tmp/apertar-core.sock`. Holds camera state properties, `apply*` commands, the event socket and polling. |
| `ApertarPreviewSocketClient.{hpp,cpp}` | Raw `AF_UNIX` client. Subscribes to preview and receives DMA-BUF fds via `SCM_RIGHTS`. |
| `PreviewFrameInfo.hpp` | POD frame descriptor: fds, planes, offsets, pitches, sizes, slot, sequence (`src/PreviewFrameInfo.hpp:5-27`). |
| `CameraPreviewItem.{hpp,cpp}` | QQuickItem with no content of its own (`ItemHasContents=false`, `.cpp:9`). Holds the preview-aid properties and geometry. Registered as the QML type `Apertar 1.0 CameraPreviewItem`. |
| `PreviewWindowRenderer.{hpp,cpp}` | Imports DMA-BUFs as EGLImages and renders with GLES2 shaders (zebra, peaking, false colour, LUT, grayscale, SMPTE, desqueeze) into the window, beneath the QML scene. |
| `PreviewExposureReference.hpp` | Builds a 1D LUT and a 3×3 matrix from Core's `previewExposureReference` map. Used so aids measure a Rec709/tuning reference even under log preview. |
| `RawPreview.hpp` | Declares `renderRawFramePreview()` (CPU debayer to QImage). Implemented at `cdngimageprovider.cpp:832`. Used by MlvReader and the cDNG provider. |
| `rawframe.h` | `RawFrame` struct for decoded RAW. |
| `tiffhelper.{h,cpp}` | TIFF/IFD helpers for DNG parsing (used by cliplistmodel, cdngimageprovider, dngdecoder, playbackcontroller). |
| `dngdecoder.{h,cpp}` | DNG decode (uncompressed and LJ92), fps detection, histogram (`dngdecoder.h:11-14`). |
| `cdngimageprovider.{h,cpp}` | `QQuickImageProvider` for DNG frames and thumbnails, with cache and a prefetch thread pool. |
| `cliplistmodel.{h,cpp}` | `QAbstractListModel` over `/media/RAW` (`.cpp:174`): DNG folders, stills, MLV, movies. |
| `playbackcontroller.{h,cpp}` | Playback state and timer, frame stepping, histogram. Plays WAV sidecar audio via an `aplay` subprocess (`.cpp:996`). |
| `VideoPlayback.{hpp,cpp}`, `VideoPlaybackApi.h` | `VideoImageProvider`. Loads `apertar-video-libav.so` through QLibrary (ABI version 2, `VideoPlayback.cpp:18-36`). MLV goes through MlvReader. |
| `VideoPlaybackLibav.cpp` | FFmpeg plugin. `extern "C" apertar_video_api()` at `:222`. |
| `MlvReader.{hpp,cpp}` | Reader for Apertar single-file uncompressed MLV. |
| `SettingsBridge.{hpp,cpp}` | ~71 UI-setting properties persisted in `QSettings("CinePi","UI")`. Presets, LUT and tuning-file discovery, section ordering. Watches the settings file to sync between processes. |
| `DisplayConfigBridge.{hpp,cpp}` | Reads `[display]` from `apertar-hardware.conf`. All properties are CONSTANT. Writes a full default config file if it is missing. |
| `DisplayCalibration.{hpp,cpp}` | `DisplayCalibrationBridge` (profile store) and `DisplayCalibrationRenderer` (post-pass colour curve using framebuffer fetch). |
| `DisplayStandbyController.{hpp,cpp}` | Hides windows and DPMS-offs HDMI/DPI/DSI screens in standby. |
| `SleepManager.{hpp,cpp}` | App-wide event filter: idle timer, user-activity signal, input swallowing in standby, sysfs backlight off/restore. |
| `SystemStatsBridge` | CPU % from `/proc/stat` (`.cpp:35`). SoC temperature from `thermal_zone0` (`.cpp:68`). |
| `DeviceInfoBridge` | Pi model, serial, OS, kernel, IP, RAM, storage. Sensor-name heuristics (camera-selection.txt, i2c, device tree, config.txt; `.cpp:213-231`). |
| `SystemActionBridge` | Reboot/poweroff (login1 D-Bus, then sudo systemctl, then systemctl). Timezone and time (timedate1 D-Bus, then sudo timedatectl/hwclock). Fan curve in `/boot/firmware/config.txt` (`.cpp:25,72-99`). |
| `PowerButtonBridge` | Watches the evdev device named `pwr_button` (`.cpp:128-140`) for `KEY_POWER` (`:85`). Rescans every 1.5 s (`:30`). |
| `MediaStatusBridge` | Mount state of `/media/RAW`, remaining time and stills, drive discovery (lsblk), mount via `sudo mount`. Eject, format and speed test are delegated to Core. |
| `Ina219Bridge` | INA219 battery monitor over `/dev/i2c-N` (default bus 4, addr 0x40, `.cpp:45-46`). Also writes its own default hardware.conf. |
| `GyroConfigBridge` | `[imu]` / driver-section config read and write. Live IMU polling over I2C (`I2C_RDWR`, `.cpp:171-180`) for the level overlay and the settings bubble. |
| `WifiBridge` | NetworkManager control via the `nmcli` subprocess: scan, connect, hotspot, auto-hotspot fallback. |
| `NetworkHelper.cpp` | `main()` for `apertar-network-helper`. Runs WifiBridge headless with `APERTAR_NETWORK_HELPER=1`. |
| `AudioDeviceBridge` | ALSA device enumeration (`arecord -l`, `aplay -l`, `/proc/asound`). Capture-capability probe via Core `audio_capabilities` (`.cpp:327-347`). |
| `AudioMeterBridge` | Level meter from an `arecord` raw S16 subprocess. Live headphone monitoring via an `aplay` subprocess (`.cpp:360-398`). |
| `AudioMixerBridge` | Applies input and headphone volume via `amixer` (`.cpp:171-219`). **Not exposed to QML.** |
| `ExternalMonitorManager` | In-process HDMI window manager, used when HDMI is on the same DRM card. |
| `ExternalMonitorRuntimeBridge` | Main-UI to monitor-only-process state sync over a QLocalServer/QLocalSocket JSON line protocol. |
| `CfeAutomounter.cpp` | Standalone CFexpress-HAT daemon: I2C buttons and LED, NVMe mount/eject, PCIe reset. |
| `StandbyLowPower.cpp` | Root helper with modes `cpu|nvme|bluetooth|all|restore`: powersave governor, NVMe runtime PM, Bluetooth rfkill. State in `/run/apertar-standby-low-power` (`.cpp:16-17,44-71,149-153`). |
| `StandbyUsbPower.cpp` | Root helper with modes `check|off|on`. Pi 5 only. Writes `1` to the 6 onboard port `disable` files under hubs `1f00200000.usb` / `1f00300000.usb` (`.cpp:60-80`). Guards: refuses if USB storage, a USB-backed filesystem, swap or a USB network device is in use (`:86-155`). State in `/run/apertar-standby-usb/ports` (`:23,181-205`). |
| `DirectProxyStub.c/.map` | libproxy replacement stub (see above). |

**Who calls the standby helpers:** nothing in UI `src/` or `qml/` invokes `apertar-standby-low-power` or `apertar-standby-usb`. The caller is presumably Core (UNCONFIRMED). The UI only exposes the `standbyUsbPowerOff` setting (`src/SettingsBridge.hpp:80`).

## 2. src/main.cpp startup, step by step

**Before QGuiApplication:**
1. Start a timer and log `qml_aot` (`:243-248`).
2. Set `AA_UseOpenGLES`, `AA_ShareOpenGLContexts` and `QQuickWindow::setGraphicsApi(OpenGL)` (`:250-252`).
3. If `QT_QPA_PLATFORM==eglfs` and `QSG_RENDER_LOOP` is unset, set `QSG_RENDER_LOOP=basic` (`:254-256`). The launcher sets this too (`run_pi_direct.sh:218`).
4. Default surface format: GLES 2.0, double buffer, swap interval 1 (`:258-265`).

**Application setup:**
5. Create `QGuiApplication` and set the application name to "Apertar-UI" (`:267-272`).
6. `qmlRegisterType<CameraPreviewItem>("Apertar",1,0,"CameraPreviewItem")` (`:274`). This is the **only registered QML type**. There are no singletons.
7. If `APERTAR_MONITOR_ONLY` is truthy, branch to `runMonitorOnly()` (`:275-276`; described below).
8. Create `DisplayConfigBridge` and read `hdmiExternalOnly`. Log path, size, layout, rotation, opacity, windowed and HDMI-only (`:278-289`).
9. Create the bridges as stack objects (`:291-310`): ApertarPreviewSocketClient, SystemStatsBridge, DeviceInfoBridge, SystemActionBridge, PowerButtonBridge, SleepManager, MediaStatusBridge, Ina219Bridge, GyroConfigBridge, WifiBridge, AudioDeviceBridge, ApertarControlBridge, SettingsBridge, AudioMeterBridge, DisplayCalibrationBridge, AudioMixerBridge, ExternalMonitorRuntimeBridge (Publisher), ClipListModel, PlaybackController.

**Wiring (`:316-348`):**
- `settings.setControlBridge(control)`.
- `monitorRuntimeBridge.setMediaBridge(media)`.
- Default controls opacity comes from DisplayConfig.
- Audio bridges are linked to settings and control.
- `externalRecordingPreparationRequested` → `AudioMeterBridge::releaseInputForRecording`.
- `SleepManager::userActivity` → `ApertarControlBridge::notifyUserActivity`.
- `DisplayStandbyController` follows `control.standby`.
- On `standbyChanged`: set standby on sleepManager, gyro, stats and media; on enter, stop playback, suspend meters and disconnect preview; on exit, reconnect preview.

**Engine and image providers (`:350-373`):**

| Provider id | Class and constructor args | Line |
|---|---|---|
| `cdng` | `CdngImageProvider(false,false,false)` | `:351,354` |
| `cdngthumb` | `CdngImageProvider(true,true,false,96,8,24 MiB)` | `:352,355` |
| `cdngplay` | `CdngImageProvider(false,true,true,32,8,32 MiB)` | `:353,356` |
| `video` | `VideoImageProvider` (starts inactive, `:361`) | `:357,359` |
| `videothumb` | `VideoImageProvider(true)` | `:358,360` |

- `video` signals `frameDecoded` and `decodeFailed` go to PlaybackController (queued) (`:362-365`).
- On standby, all three cdng caches are cleared and the video provider is deactivated (`:366-373`).

**Context properties (`:374-396`):**
`apertarPreviewBridge`, `statsBridge`, `deviceInfoBridge`, `displayConfigBridge`, `systemActionBridge`, `displayCalibrationBridge`, `powerButtonBridge`, `sleepManager`, `mediaBridge`, `powerBridge` (Ina219), `gyroConfigBridge`, `wifiBridge`, `audioDeviceBridge`, `audioMeterBridge`, `apertarControlBridge`, `settingsBridge`, `hdmiExternalOnly` (bool), `clipModel`, `playbackController`, `cdngThumbProvider`, `cdngPlayProvider`, `videoProvider`, `monitorRuntimeBridge`.

**Load and ready markers:**
- `engine.load("qrc:/qml/Main.qml")` (`:397`).
- After load, write `"ready\n"` to `$APERTAR_CORE_START_READY_FILE` (`:405-420`). This releases Core's start gate.

**Window setup (`:422-501`):**
- Attach `DisplayCalibrationRenderer(window, …, hdmi=false)` (`:424`).
- `monitorRuntimeBridge.setMainWindow` (`:425`).
- Persistent graphics and scene graph (`:426-427`).
- If `hdmiExternalOnly`, `window->hide()` (`:428-429`).
- Otherwise move to `mainUiScreenForNormalMode()` (`:90-119`):
  - If there is a single screen, use it.
  - Otherwise prefer the first internal panel when a touch device is present or no HDMI exists.
  - Internal panel means the name contains dpi/dsi/lcd/panel, or the screen is 720×720 (`:61-73`).
  - Touch present means `/proc/bus/input/devices` mentions touch, goodix, ep0110, hyperpixel or waveshare (`:75-88`).
  - Otherwise first HDMI, then primary, then first screen.
- Windowed mode: still full screen on that screen, plus a re-raise after 250 ms (`:435-454`). QML draws the configured-size viewport with a 1 px border (`qml/Main.qml:474-494`).
- Accept touch events on the content item (`:460-461`).
- `APERTAR_UI_READY_FILE` is written on the first `frameSwapped`, or immediately if HDMI-only (`:463-500`). 250 ms later it starts `deviceInfoBridge.startDeferredRefresh()` and `powerBridge.startDeferredMonitoring()` (`:488-493`).

**Preview renderer and external monitor:**
- Find `previewContainer` and `previewItem` by objectName (`:502-508`).
- `new PreviewWindowRenderer(&engine)->setPreviewItem(previewItem)` (`:510-511`). Normal mode is not direct-window (it uses an FBO, then a blit).
- `ExternalMonitorManager(&engine)` (`:513-518`):
  - `setHdmiExternalOnly(hdmiExternalOnly && !windowed)`.
  - `setMainWindow`.
  - Calibration bridge.
  - `setSettingsBridge` **only if not windowed**.
- `app.exec()` (`:520`).

**`runMonitorOnly()` (`:131-237`):**
- Minimal bridge set: DisplayConfig, PreviewSocketClient, ControlBridge, DisplayStandbyController, SettingsBridge, ExternalMonitorRuntimeBridge (Subscriber), DisplayCalibrationBridge.
- Context properties (`:147-154`):
  - `mediaBridge` is aliased to `monitorRuntimeBridge`.
  - `audioMeterBridge` is null.
  - **There is no `gyroConfigBridge`**, so the HDMI horizontal level is unavailable in the split-DRM topology. QML guards it with `typeof` checks.
- Loads `qrc:/qml/ExternalMonitorWindow.qml` (`:155`).
- Uses the first HDMI QScreen (`:121-129,164-168`). `setScreen` happens before show, as EGLFS requires (`:170-174`).
- `PreviewWindowRenderer` with `setDirectWindowRendering(true)` (`:178-180`). Calibration renderer with `hdmi=true` (`:181`).
- `syncVisibility()` (`:183-210`) shows full screen only when not in standby, HDMI is present, `hdmiExternalOnly || settings.externalMonitorEnabled`, and `monitorRuntimeBridge.cameraPageActive`. It is re-run on settings, standby, page and screen add/remove (`:212-226`).
- Connects preview (`:228`).

## 3. QML page structure

### qml/Main.qml (945 lines). Root is `Window` (`:5`), not ApplicationWindow
- **Page switching** uses the string property `currentPage` with values `"camera"`, `"browser"`, `"player"` (`:16`), plus Loaders. There is no StackView and no states.
- `CameraPage` is always instantiated (`:496-517`).
- `SettingsPage` is an overlay on the camera page, not a separate page:
  - `Loader settingsPageLoader` (`:535-578`), `active: currentPage==="camera" && settingsPageRetained` (`:539`).
  - Opacity, y and scale are animated by `settingsOpen` (`:541-543`).
  - It is preloaded 750 ms after the first preview frame (`:88-91,104-110,334-344`).
  - It is hidden 420 ms after close (`:353-362`).
  - `releaseSettingsBackgroundWork()` stops gyro, audio, drive-discovery and device-info polling (`:93-102`).
  - Scrim at `:519-533`.
- `ClipBrowserPage`: `Loader` (`:580-607`), `active: currentPage==="browser"` (`:584`). Back goes to camera (`:601`).
- `ClipPlayerPage`: `Loader` (`:609-640`), `active: currentPage==="player"` (`:613`). Back goes to browser (`:634`). `selectClip()` sets the page to player (`:417-424`).
- **Rotation** is a QML `Rotation` transform on `Item uiScene` (`:474-486`). The angle is `effectiveUiRotationDegrees = settings uiOrientation (Left Side 90 / Right Side −90 / Upside Down 180) + [display] ui_rotation` (`:56-61`). `uiScene` is hidden in standby (`:476`).
- Properties read by C++ through `QObject::property`/`SIGNAL`:
  - `currentPage`, `standbyActive` (= `sleepManager.standby`, `:27`), the `powerButtonShutdown*` properties (`:30-35`), `monitorRecordingActive`, `monitorTimelapseActive`, `monitorTimecode` (`:36-38`).
  - Consumers: `ExternalMonitorRuntimeBridge.cpp:56-87,131-153` and `ExternalMonitorManager.cpp:111-126,280-313`.
- `Component.onCompleted`: copy sleep mode, `clipModel.stillMode`, call `apertarPreviewBridge.connectToCore()` (default path), start the services timer (`:204-211`).
- Handlers:
  - `apertarControlBridge.onHardwareActionTriggered` (`:285-332`): `power_button_press`, `standby_power_sleep`, `standby_power_wake`, `zoom_toggle`, `settings`, `clip_browser`, `quick_menu`.
  - `powerButtonBridge` local fallback, active only when Core is disconnected (`:262-283`).
  - `sleepManager.onSleepTriggered` shows the auto-power-off warning (`:241-260`).
- Overlays:
  - Auto-power-off warning card (`:657-752`), with a 10 s countdown (`:364-388`).
  - Power-button shutdown card (`:774-945`). The hold timers are `:390-415`; confirm calls `systemActionBridge.shutdownCamera()` (`:162-180`).

### qml/CameraPage.qml (4160 lines; 106 functions; ~294 properties; mixed tab/space indentation)

**Lines 1-1964: properties, functions and timers.**
- Hard-coded per-sensor resolution and crop tables at `:392-443` and `:1052-1191`.
- Timecode is **computed locally in QML**, not taken from Core (`:1692-1707`). Free Run uses wall clock, Rec Run uses a frame counter. Toggle at `:1709-1715`.
- Record path: `requestRecordingState()` → `controlBridge.setRecording()`, suspending and resuming meters (`:1583-1600`).
- Photo: `capturePhoto()` (`:1447`). Timelapse: `setTimelapseActive()` (`:1633`).

**Sections:**

| Lines | Item | What it is |
|---|---|---|
| 1965-2548 | `previewContainer` (objectName `previewContainer`) | Holds the preview and all on-image overlays. |
| 1973-1997 | `CameraPreviewItem preview` (objectName `previewItem`) | Binds all aid properties from `settingsState`. `exposureReference` comes from `controlBridge.previewExposureReference`. `displayRotation: uiPreviewRotation - sceneRotationDegrees`. |
| 1999 | `StillExposureOverlay` | Long-exposure blackout and countdown. |
| 2006-2078 | Photo flash, frame pulse, feedback animation | |
| 2079 | Self-timer countdown bubble | |
| 2116-2299 | `MultiPointTouchArea previewTouchArea` | 1-2 points; pinch zoom (`:2135-2185`). |
| 2300 | `DragHandler` | Pan. |
| 2332 | `TapHandler` | |
| 2351-2505 | `guideOverlay` | **QML** frame guides by `guidesType` (e.g. 2.39:1, `:2380`). Center marker Circle/Dot or Crosshair (`:2466-2497`). |
| 2506-2527 | `HorizontalLevelOverlay` | **QML**, fed by `gyroConfigBridge` accel properties. |
| 2528 | `FalseColorLegend` | **QML** legend only. |
| 2549 | `StatusChip` | REC / timelapse / writing / media. |
| 2569 | `DroppedFrameWarning` | `controlBridge.recordingHasDroppedFrames`. |
| 2579-2727 | Still-mode controls column | Timer, burst, bracketing; `TimelapseIntervalPicker` at `:2675`. |
| 2728-2850 | `staticOverlay` | Background bars. |
| 2851-3577 | `dynamicOverlay` (z 100) | See rows below. |
| 2877-3040 | Top stat row | 4× `TopDropdownStat`: FPS (`:2886`), ISO (`:2918`), shutter (`:2950`), WB (`:2990`). |
| 3041 | Quick-menu edge swipe zone | `Canvas` at `:3058`. |
| 3116-3566 | `quickMenuPanel` | |
| 3578-3665 | `InfoLine`s | FORMAT / MEDIA / CPU / POWER. |
| 3672+ | `bottomControlsRow` | `ClipBrowserButton` (`:3689`), `AudioMeterOverlay` (`:3712`), `RecordButton` (`:3772`), capture-mode menu (`:3832`). |
| 3900 | Compact `AudioMeterOverlay` | QML; `audioMeterBridge.inputLevel`. |
| 3927 | Date/time chip | |
| 3980-4160 | Record-error scrim and `recordWarningCard` | |

**Where each preview aid is implemented:**

| Aid | Implementation | Ref |
|---|---|---|
| Focus peaking | GLSL edge detect; color uniform mapped Red/Green/Blue/Yellow | `PreviewWindowRenderer.cpp:854-907, 2124, 2352` |
| Zebra | GLSL animated stripes over threshold | `:895-899` |
| False colour (4 modes: Exposure/Skin/Highlight/Shadow) | GLSL | `:883-892`; mode mapping in `CameraPage.qml:1717-1723` |
| Legend | QML | `FalseColorLegend.qml` |
| LUT preview (.cube → 2D atlas texture, async load) | GLSL + C++ parser | `:187-287, 541-641, 880` |
| Grayscale, SMPTE bars | GLSL | `:874-893` |
| Anamorphic desqueeze | C++ geometry (aspect rect) | `PreviewWindowRenderer.cpp:1857-1891` (UNCONFIRMED exact use) |
| Guides, center marker | QML | `CameraPage.qml:2351-2505` |
| Horizontal level | QML | `HorizontalLevelOverlay.qml`; `GyroBubbleLevel.qml` uses a Canvas (`:102`) |
| Audio meters | QML | `AudioMeterOverlay.qml`, `AudioLevelCard.qml` |
| Display calibration | GLSL post-pass on the whole window | `DisplayCalibration.cpp:195-228` |

There is no QML `ShaderEffect` anywhere.

### qml/SettingsPage.qml (9851 lines)
- `selectedSection` defaults to "Monitoring" (`:15`).
- Sidebar order (`:827-837`): Favorites, Monitoring, Record, Audio, **Power (shown as "Media", `:1122-1123`)**, System, Presets, Wi-Fi, Info.
- Default per-section item orders (`:771-826`); favourite candidates from `:838`.
- Item-to-component dispatch functions (`:2216-2384`): `monitoringComponentForId`, `recordComponentForId`, `audioComponentForId`, `powerComponentForId`, `systemComponentForId`, `wifiComponentForId`, `infoComponentForId`, `favoriteComponentForId`.
- Hard-coded sensor resolution tables: imx477 (`:110-142`), imx294 (`:143-150`), imx585 (`:151-183`), h264 (`:220-225`).

**Component definitions:**

| Section | Component (start line) |
|---|---|
| Monitoring | externalMonitor 2385, lutPreview 2428, focusPeaking 2650, zebra 2686, falseColor 2715, guides 2749, smpte 2785, centerMarker 2807, horizontalLevel 2836, greyscale 2865, anamorphic 2887 |
| Record | stillMode 2915, soundRecorder 3027, exposureCompensation 3067, format 3118, tuningFile 3322, gyro 3500, timecode 3753, autofocus 3784 |
| Audio | audioOptions 3862, audioLevels 4016 |
| System (battery, power) | powerBattery 4055, powerBatteryInfo 4443, powerAutoPowerOff 4521, systemCameraStandby 4550 |
| System | uiOrientation 4608, displayCalibration 4636 (→ `DisplayCalibrationPanel`), controlsOpacity 4653, dateTime 4699 |
| Power ("Media") | systemMedia 4940, systemFormatMedia 5120, systemMediaSpeed 5192 |
| System | systemThermal 5329, systemPowerActions 5387 |
| Wi-Fi | toggle 5454, current 5474, hotspot 5589, available networks 5795 |
| Info | camera 5988, sbc 6021, system 6058, systemDrive 6088 |
| Reorder | reorder delegates 6111 / 6221 |

**Layout and popups:**
- Main layout (`:6330-7212`): header at `:6334`, sidebar ListView at `:6416-6470`, `sectionFlick` Flickable at `:6474`. Presets content is inline (`:6747,6894`).
- Popups (`:7213-9851`), each identified by its `visible:` flag:

| Popup | Line |
|---|---|
| favoriteManager | 7213 |
| reorder | 7479 |
| power confirm scrim | 7688 |
| presetName keyboard | 7748 |
| presetDelete | 8016 |
| hotspotEdit keyboard | 8152 |
| wifiPassword keyboard | 8438 |
| formatConfirm | 8711 |
| formatSuccess | 8847 |
| ejectConfirm | 8948 |
| mediaMountError | 9081 |
| powerConfirm | 9180 |
| powerError | 9315 |
| thermal success / error | 9391 / 9468 |
| time success | 9545 |
| ejectError | 9622 |
| formatError | 9699 |
| timeApplyError | 9776 |

### qml/ClipBrowserPage.qml (1025) and qml/ClipPlayerPage.qml (2272)
- Browser:
  - Signals `backRequested` and `clipOpened` (`ClipBrowserPage.qml:51-52`).
  - `clipModel.browserOpen` follows visibility (`:60,78`).
  - Refresh (`:286-300`), sort toggle (`:123`), multi-select delete via `clipModel.removeClip` (`:111`).
  - Clears the thumbnail cache on hide (`:65-76,151`).
- Player:
  - Signals back, previous, next, delete (`ClipPlayerPage.qml:64-67`).
  - `videoProvider.setActive(enabled && visible && playbackController.videoClip)` (`:70-76`).
- Image URLs are built in C++:
  - `image://cdngthumb/thumb?path64=…` (`cliplistmodel.cpp:68`)
  - `image://cdng/frame?path64=…&token=` (`playbackcontroller.cpp:494`)
  - `image://cdngplay/frame?path64=` (`:505`)
  - `image://video|videothumb/frame?path64=&frame=` (`VideoPlayback.cpp:94`)

### qml/ExternalMonitorWindow.qml (1347)
- Root is a separate `Window` (`:5`).
- Shutdown popup and capture state come from `monitorRuntimeBridge`, with a fallback to `apertarControlBridge` (`:9-31`).
- `externalMonitorMode` (Clean/Assist Feed), info overlay, and orientation (Portrait Left/Right/Upside Down → rotation, `:49-61`).
- `monitorSurface`, rotated in QML (`:351-358`).
- `CameraPreviewItem` with objectName `externalPreviewItem`. Peaking, zebra, false colour and grayscale are only on in Assist Feed (`:366-390`). LUT, desqueeze and SMPTE apply in both modes.
- On standby it connects and disconnects the preview bridge (`:283-293`). This duplicates `main.cpp:344-346` when it runs in-process.
- Also contains `HorizontalLevelOverlay` (`:741`), `FalseColorLegend` (`:763`), `DroppedFrameWarning`.

### Small components
| File | Used by |
|---|---|
| ActionTile, AdjustNumberTile, AudioLevelCard, InfoDataRow, InlineDropdownField, MonitoringRow, SettingsMenuItem, SystemSectionCard, GyroBubbleLevel, DisplayCalibrationPanel, TimelapseIntervalDialog | SettingsPage |
| SettingsChoice | MonitoringRow |
| TogglePill | Calibration panel, MonitoringRow, SettingsPage |
| RecordButton, ClipBrowserButton, StatusChip, TopDropdownStat, InfoLine, TimelapseIntervalPicker, AudioMeterOverlay | CameraPage |
| DroppedFrameWarning, FalseColorLegend, HorizontalLevelOverlay, StillExposureOverlay | CameraPage and ExternalMonitorWindow |
| `TimelapseIntervals.js` | CameraPage, SettingsPage, TimelapseIntervalDialog, TimelapseIntervalPicker |
| `GyroOrientationIndicator.qml` | **Nothing.** Compiled but unused. |
| `InlineChoice.qml` | **Nothing**, and it is in neither `CMakeLists.txt` nor `qml.qrc`. Dead file. |

## 4. Bridge table (C++ classes exposed to QML)

| Class (file:line) | QML name | Key properties / invokables | Talks to |
|---|---|---|---|
| `ApertarControlBridge` (`ApertarControlBridge.hpp:12`) | `apertarControlBridge` | 43 props: fps, iso, shutterAngle/Speed, whiteBalance(+Available), exposureCompensation, metering, resolution, recordingFormat, prores*, cdng*, previewExposureReference, capabilities (raw/prores/h264*), tuningFile, rawBitDepth, sensorName, autofocus*, recording, recordingHasDroppedFrames, standby, timelapse*, stillExposure*, mediaWritesPending, audioInputLevel, connected, lastError (`:16-58`). 35 invokables: `apply*`, `setRecording`, `capturePhoto`, `setTimelapseActive`, `enterStandby`/`wakeFromStandby`, `notifyUserActivity`, `calibrateGyro`, `refresh` (`:98-141`). Signals: recordingFailed, photoCaptured, hardwareActionTriggered, etc. (`:180-192`). | Core socket `$APERTAR_CONTROL_SOCKET` or `/tmp/apertar-core.sock`. `QSettings("CinePi","UI")` (`.cpp:118`). |
| `ApertarPreviewSocketClient` (`.hpp:15`) | `apertarPreviewBridge` | connected, statusText, frameCounter; `connectToCore(path="/tmp/apertar-core.sock")`, `disconnectFromCore()` (`:18-31`) | Core socket, raw `SOCK_STREAM` + `SCM_RIGHTS` |
| `CameraPreviewItem` (`.hpp:8`) | QML type `Apertar 1.0` | bridge, zoom, panX/Y, zebra*, focusPeaking*, grayscale, smpte, anamorphic*, falseColor*, lutPreview*, exposureReference, displayRotation, previewAspectRatio (`:11-30`) | Consumed by PreviewWindowRenderer |
| `SettingsBridge` (`.hpp:13`) | `settingsBridge` | ~71 props (`:17-92`): monitoring aids, guides, uiOrientation, controls opacity/mode, externalMonitor*, timecodeMode, photo*, audio*, battery*, sleepMode, standby*, section orders, presets. Invokables: `refreshLutPreviewOptions`, `refreshTuningFileOptions` (`:139,142`), presets save/load/delete/export/import (`:299-304`). | `QSettings("CinePi","UI")` (`.cpp:287`) watched with QFileSystemWatcher plus a 10 s poll (`:411-428`). LUT dirs `/home/pi/LUTs`, `$APERTAR_MEDIA_ROOT/LUTs`, `/media/RAW/LUTs`, `/media/*/LUTs` (`:143-153`). Tuning dirs `/home/pi/Tuning-Files` etc. (`:167-177`). Presets `*.apertar-preset.json` in AppData or legacy `~/.config/CinePi/UI/presets` (`:1937-1944`). Camera part of a preset goes through `ApertarControlBridge::applyCameraPreset` (`:2091,2117`). |
| `DisplayConfigBridge` (`.hpp:6`) | `displayConfigBridge` | All CONSTANT: uiWidth/Height, uiLayout(+layout bools), uiRotationDegrees, controlsOpacity, zoomToggleFactor, windowed, hdmiExternalOnly, configPath (`:9-23`) | `apertar-hardware.conf` [display] (see §6) |
| `DisplayCalibrationBridge` (`DisplayCalibration.hpp:20`) | `displayCalibrationBridge` | target (Built-in/HDMI), profile, status; `setValue(key,val)`, `resetSelected()` (`:22-34`) | `QSettings("CinePi","DisplayCalibration")` groups builtin/hdmi (`.cpp:49,140-150`). File-watched so the main and monitor-only processes stay in sync (`:53-58,153-160`). |
| `SystemStatsBridge` (`.hpp:6`) | `statsBridge` | cpuPercent, socTempC, cpuText | `/proc/stat`, `/sys/class/thermal/thermal_zone0/temp` |
| `DeviceInfoBridge` (`.hpp:6`) | `deviceInfoBridge` | 15 info props; `setDynamicPollingEnabled` (`:9-29`) | `/proc`, device tree, `/boot/firmware/camera-selection.txt`, `config.txt`. 5 s refresh (`.cpp:25-27`). |
| `SystemActionBridge` (`.hpp:7`) | `systemActionBridge` | lastError, currentTimeZone, availableTimeZones, fanMode; `restartCamera` (reboots the Pi), `shutdownCamera`, `applyTimeZone`, `applyDateTime`, `applyFanMode` (`:10-27`) | D-Bus login1 and timedate1; `sudo -n` systemctl/timedatectl/hwclock/install; writes `/boot/firmware/config.txt` (`.cpp:25,276-282,480-525,614-619`) |
| `PowerButtonBridge` (`.hpp:9`) | `powerButtonBridge` | available, pressed, devicePath; signals buttonPressed/Released | evdev `/dev/input/eventN` named `pwr_button` |
| `SleepManager` (`.hpp:9`) | `sleepManager` | sleepMode (Off/1/2/5/10 min, `.cpp:229-240`), standby (R/W); `restartIdleTimerNow` | Global event filter. `/sys/class/backlight/*` (or `$APERTAR_BACKLIGHT_DIR`) and `wittypi_led` (`.cpp:35-48,95-151`). Saves levels in `QSettings("Apertar","StandbyBacklights")` (`:56`). |
| `MediaStatusBridge` (`.hpp:12`) | `mediaBridge` (in monitor-only: `monitorRuntimeBridge`) | mediaMounted, mountPath (const `/media/RAW`, `.hpp:136`), remaining*, writeSpeed*, mediaType/Prompt, mountableDrives; `ejectMedia`, `formatMedia`, `startWriteSpeedTest`, `mountDrive*`, `refreshMountableDrives`, `setDriveDiscoveryActive` (`:15-75`) | 1 s timer (`.cpp:266-274`). QStorageInfo. `lsblk`. `sudo -n mount`/mkdir (`:974-1036`). Core commands `eject_media`, `format_media` (360 s timeout), `run_media_speed_test`, `get_media_test_state` via its own one-shot socket helper `coreMediaCommand` (`:20-43,1183-1215`). |
| `Ina219Bridge` (`.hpp:7`) | `powerBridge` | sensorAvailable, busVoltageV, currentA, powerW, batteryPercent + text variants | `/dev/i2c-N` ioctl. Hardware conf `[ina219]`. Deferred start (`.cpp:449-457`). |
| `GyroConfigBridge` (`.hpp:9`) | `gyroConfigBridge` | driver, syncMode, orientation, syncOffsetMs, sampleRate, live accel/gyro, levelReference*; `setDriverName`, `setLivePollingRequest`, `setLevelReference`, `setOrientation`, `setSyncOffsetMs` etc. (`:12-83`) | `/dev/i2c-N` (`I2C_RDWR`, `I2C_SLAVE`). Reads and writes hardware conf `[imu]` and driver sections (`.cpp:684,828-885`). |
| `WifiBridge` (`.hpp:10`) | `wifiBridge` | networks, scanning, connecting, wifiAvailable/Enabled, statusText, currentSsid, wifiDevice, hotspotActive/Ssid/Password/StatusText, lastError; `refresh`, `setWifiEnabled`, `connectToNetwork`, `disconnectCurrent`, `startHotspot`, `stopHotspot` (`:14-52`) | `nmcli` QProcess (`.cpp:541-547`), polkit (§9) |
| `AudioDeviceBridge` (`.hpp:14`) | `audioDeviceBridge` | input/output device options, sample format/rate/channel options and labels, capabilitiesBusy; select*/resolve*/normalize* (`:18-65`) | `arecord -l` / `aplay -l` (`.cpp:453-454`), `/proc/asound/*`, `/dev/snd` watch (`:261`). Core `audio_capabilities` with a 4 s timeout (`:327-347`). |
| `AudioMeterBridge` (`.hpp:12`) | `audioMeterBridge` (null in monitor-only) | inputLevel, inputDeviceAvailable; `suspendMonitoring`, `resumeMonitoring` | `arecord` S16_LE raw / `aplay` (`.cpp:360-398`) |
| `ExternalMonitorRuntimeBridge` (`.hpp:15`) | `monitorRuntimeBridge` | cameraPageActive, shutdown*, mediaMounted, remaining*, captureStateAvailable, recordingActive, timelapseActive, timecode (`:18-30`) | QLocalServer/QLocalSocket at `$APERTAR_MONITOR_RUNTIME_SOCKET` or `/tmp/apertar-ui-monitor-state.sock` (`.cpp:14-20`) |
| `ClipListModel` (`cliplistmodel.h:7`) | `clipModel` | rootPath (`/media/RAW`), stillMode, sortMode, browserOpen, count, loading, statusText; `refresh`, `pathAt`, `removeClip`, etc. (`:10-55`) | Filesystem |
| `PlaybackController` (`playbackcontroller.h:18`) | `playbackController` | currentClip*, frameCount, currentFrameIndex, playing, fps, frameSource/fastFrameSource, histogramBins, clipMetadata, videoClip; `loadClip`, `togglePlayback`, `stop`, `nextFrame`, `previousFrame`, `seekToFrame` (`:21-62`) | Filesystem, `aplay` for WAV sidecars (`.cpp:877-888,996`) |
| `CdngImageProvider` (`cdngimageprovider.h:13`) | `cdngThumbProvider`, `cdngPlayProvider` (also image ids `cdng*`) | `clearCache()`, `prefetchAround()` (`:27-32`) | DNG files |
| `VideoImageProvider` (`VideoPlayback.hpp:22`) | `videoProvider` (image ids `video`, `videothumb`) | `setActive()` (`:29`) | plugin `.so`, MlvReader |
| (bool) | `hdmiExternalOnly` | context bool (`main.cpp:390`) | n/a |

Not exposed to QML: `AudioMixerBridge`, `DisplayStandbyController`, `ExternalMonitorManager`, `PreviewWindowRenderer`, `DisplayCalibrationRenderer`.

## 5. How the UI talks to Core

### ApertarControlBridge
- **Protocol:** newline-delimited JSON. Requests carry `{"cmd":…, "id":N, …args}`. Replies carry the matching `id` and `ok`/`error`. Events carry `"event"` (`.cpp:1047-1050,1182-1259`).
- **Persistent event socket** `m_eventSocket` (QLocalSocket, `.hpp:277`):
  - Connects on construction (`.cpp:116-147,1557-1568`).
  - Reads lines in `processEventSocketMessages` (`:1570-1589`).
  - **Polling:** `refreshFromCore()` sends an async `get_state` on the event socket. Only one request is outstanding at a time. A 10 s timeout aborts the socket (`:855-873`).
  - The retry timer runs every 1 s while disconnected and every 30 s once connected (`:17-18,875-882`).
  - `notifyUserActivity()` writes `{"cmd":"user_activity","id":-2}` (`:1176-1180`), throttled to 1/s by SleepManager (`SleepManager.cpp:200-205`).
- **Commands:** `sendCoreCommand()` opens a **new QLocalSocket per command and blocks the GUI thread** (`:1013-1105`):
  - Connect timeout 350 ms.
  - Reply timeout 3 s by default.
  - 10 s for reconfigure commands (`set_resolution`, `set_capture_mode`, `set_raw_bit_depth`, `set_record_format`, `set_tuning_file`, `set_prores_color_profile`, `set_cdng_preview_color_profile`, `set_h264_resolution`, `capture_photo`, `timelapse_start`, `wake`, `enter_standby`, `apply_preset`).
  - 8 s for `calibrate_gyro`.
  - **60 s for `record_stop`** (`:1015-1031`).
  - A timeout marks the bridge disconnected (`:1099-1104`).
- **Events handled** (`:1182-1259`): `photo_write_error`, `standby`, `still_exposure`, `timelapse_progress`, `media_write_state`, `audio_level`, `recording`, `recording_health`, `timelapse`, `timelapse_frame`, `photo_capture`, `prepare_recording` (→ release the ALSA input), `hardware_action`, `settings`.
- **Other Core socket clients** (each opens its own connection):
  - MediaStatusBridge `coreMediaCommand` uses a fixed `id 42001` (`MediaStatusBridge.cpp:20-43`).
  - AudioDeviceBridge `audio_capabilities` (`AudioDeviceBridge.cpp:327-347`).
  - The preview client (below).

### ApertarPreviewSocketClient
- Plain BSD `socket(AF_UNIX, SOCK_STREAM|SOCK_NONBLOCK)` with a QSocketNotifier (`.cpp:32-82`). 1 s single-shot reconnect (`:15-22,120-126`).
- **The default path is hard-coded** `/tmp/apertar-core.sock` (`.hpp:30`), and QML calls it with no argument (`Main.qml:207`), so it **ignores `APERTAR_CONTROL_SOCKET`**. The other clients honour that variable.
- Sends `{"cmd":"preview_subscribe","id":0}` (`.cpp:142-165`).
- Receives with `recvmsg` and collects `SCM_RIGHTS` fds (`:167-215`). Fds are matched to messages in `takePendingFdsForMessage` (`:239`).
- JSON is parsed with **hand-rolled substring scanners**, not QJsonDocument (`jsonStringValue`/`jsonIntegerValue`, `:585-625`). It assumes compact `"key":value` with no whitespace before the colon.
- **Event `preview_buffer`** (`:353-451`): registers a slot. Fields: `slot`, `width`, `height`, `stride`, optional `capture_width`, `capture_height`, `layout_plane_count` (1-3), `planeN_offset`, `planeN_pitch`. The slot keeps the dmabuf fds.
- **Event `preview_frame`** (`:453-583`):
  - Without fds, it refers to a registered slot by `frame_id` and `slot` (zero-copy ring).
  - With fds, it carries per-frame `width`, `height`, `stride`, `plane_count`, `planeN_*`; the client owns those fds.
  - It emits `frameArrived` and `previewFrameReady`.
- `duplicateProducerFd()` `dup()`s an fd for the renderer (`:135-140`).

### CameraPreviewItem + PreviewWindowRenderer
- `CameraPreviewItem` draws nothing itself (`ItemHasContents=false`, `CameraPreviewItem.cpp:9`). Its property setters call `window()->update()`.
- The renderer hooks `QQuickWindow::beforeSynchronizing` (syncState) and `beforeRenderPassRecording` (render) with DirectConnection (`PreviewWindowRenderer.cpp:384-408`). It therefore draws **underneath** the QML scene each frame, inside `beginExternalCommands`/`endExternalCommands` (`:2388-2465`).
- It is **not** a direct DRM plane. It uses the GL texture path:
  - `eglCreateImageKHR(EGL_LINUX_DMA_BUF_EXT)` with `DRM_FORMAT_YUV420` 3-plane, `EGL_ITU_REC709_EXT`, narrow range.
  - Bound as `GL_TEXTURE_EXTERNAL_OES` (`:1703-1810`).
  - Imported buffers are cached by dmabuf `st_dev`/`st_ino` key (`:462-474`).
- **Fallback paths:**
  - Planar YUV upload via `mmap` of the dmabufs into 3 GL_TEXTURE_2D (`:1294-1409`).
  - CPU RGBA conversion (`:1411-1580`).
  - Pi 3 is detected from `/proc/device-tree/model` (`:32-40`) and forces the planar path plus direct-window rendering unless `APERTAR_PREVIEW_FORCE_EGL` is set (`:295-306`).
  - Environment overrides: `APERTAR_PREVIEW_FORCE_CPU`, `APERTAR_PREVIEW_FORCE_PLANAR`, `APERTAR_PREVIEW_FORCE_EGL`.
- **Shader programs:** process and passthrough programs for each of external, 2D and planar sources (`.hpp:156-161`). Shader source is at `:678-1220`.
- **Two draw modes:**
  - Main UI: `renderProcessedPreview` into an FBO, then `blitPreviewToWindow` (`:1969-2192`).
  - HDMI windows and Pi 3: `renderDirectToWindow` (`:2194-2386`), enabled by `setDirectWindowRendering(true)` (`.hpp:36`).
- Redraw is requested on `previewFrameReady` (DirectConnection, `:428-444`), coalesced through `m_updatePending` (`:342-355`).

### PreviewFrameInfo.hpp and RawPreview.hpp
See §1. RawPreview is unrelated to live preview; it is the playback/RAW CPU render.

## 6. Display configuration

**Config file search order** (first existing file wins): `$APERTAR_HARDWARE_CONFIG`, then `/home/pi/apertar-hardware.conf`, then `/boot/firmware/apertar-hardware.conf`, then `/boot/apertar-hardware.conf` (`DisplayConfigBridge.cpp:20-39,589-653`).

**Default file creation:** if `/home/pi/apertar-hardware.conf` is missing, a full default file is written. That includes `[network]`, `[run_script]`, `[ina219]`, `[pcf8574]`, `[trigger_output]`, `[recording_indicator]`, `[neorotary4]`, `[gpio_buttons]`, `[gpio_encoders]`, `[grove_analog]`, `[imu]`, `[mpu6050]`, `[bmi160]`, `[bmi270]`, `[icm42688p]`, `[cfexpress_hat]`, `[storage]` and `[display]` (`:41-326`). The `[display]` template is at `:304-325`.

**[display] keys, read-only** (all CONSTANT; restart needed):

| Key (aliases) | Default | Range / values | Effect | Ref |
|---|---|---|---|---|
| `ui_width` (`uiWidth`, `width`) | 720 | 320–3840 | Window and QML size; viewport when windowed or rotated | `:598-604`; `Main.qml:13-14,478-479` |
| `ui_height` (`uiHeight`, `height`) | 720 | 320–3840 | as above | `:605-611` |
| `ui_layout` (`uiLayout`, `layout`, `profile`) | file: `square`; code fallback `auto` | square, landscape_compact/medium/large, landscape, portrait_compact/portrait/portrait_large, plus aliases; `auto` is derived from size | Selects QML layout branches | `:612-618, 478-524` |
| `ui_rotation` (`uiRotation`, `rotation`, `orientation`) | normal | normal/left(90)/right(−90)/upside_down(180) plus numeric aliases | Added to the Settings uiOrientation in the QML Rotation | `:619-625, 526-566`; `Main.qml:56-61` |
| `controls_opacity` (`control_opacity`, `controlsOpacity`, `opacity`) | 1.0 | 0.15–1.0 | Default for `settingsBridge.cameraControlsOpacity` | `:626-633`; `main.cpp:318` |
| `zoom_toggle_factor` | 4.0 | 1.0–4.0 | Zoom button magnification | `:634-638`; `CameraPage.qml:528` |
| `windowed` (`ui_windowed`, `uiWindowed`, `debug_windowed`, `debugWindowed`) | false | bool | Layout-test viewport with a border; disables the in-process external monitor | `:639-645`; `main.cpp:435-454,514-518` |
| `hdmi_external_only` (`hdmiExternalOnly`) | false | bool | Main window hidden; UI on HDMI only | `:646-649`; `main.cpp:428-429,514` |

**Other display pieces:**
- **Rotation** is pure QML (`Main.qml:474-486`). The preview renderer gets `displayRotation = uiPreviewRotation - sceneRotationDegrees` (`CameraPage.qml:1995`). The HDMI window rotates its own surface (`ExternalMonitorWindow.qml:57-61,357,388`).
- **DisplayCalibration:**
  - Profile fields: `enabled`, `red`, `green`, `blue`, `gamma`, `black`, `white` (`DisplayCalibration.hpp:12-18`), with separate builtin and HDMI profiles.
  - The renderer runs on `afterRenderPassRecording` (`.cpp:165-170`). It needs `GL_EXT_shader_framebuffer_fetch` and reads `gl_LastFragData[0]` through a 256-entry curve texture (`:195-228`). Without that extension it reports "Unavailable" (`:201-203`).
  - It is attached to the main window (`main.cpp:424`), the in-process HDMI window (`ExternalMonitorManager.cpp:211-212`) and the monitor-only window (`main.cpp:181`).
- **DisplayStandbyController:**
  - Applies to screens named HDMI, DPI or DSI. A `UNKNOWN<n>` screen is mapped to `/sys/class/drm/cardX-DPI-n` using the KMS config's `device` (`DisplayStandbyController.cpp:13-33`).
  - `APERTAR_STANDBY_PANEL_POWER=0` exempts panels (`:18`).
  - On standby it hides the visible windows on those screens, then calls `QPlatformScreen::setPowerState(PowerStateOff)`. It restores on wake and handles screens hot-added during standby (`:39-108`).
- **Backlight:**
  - SleepManager writes `0` to `/sys/class/backlight/*/brightness`, and also to the `wittypi_led` brightness/trigger. That LED is only touched when the device tree matches a Waveshare 720×720 panel-dpi on GPIO18 active-low (`SleepManager.cpp:31-48,95-151`).
  - It restores saved levels at the next start (`:55-60`).
  - The UI user needs group write access. `systemd/90-apertar-backlight.rules:1-2` is a udev rule that `chgrp video` + `chmod g+w` on backlight brightness and on the `wittypi_led` brightness/trigger.
- **SleepManager standby behaviour:** in standby every touch, mouse or key event is swallowed (touch does not wake), and a held gesture is consumed past wake (`SleepManager.cpp:176-211`).
- **Two sources of truth for standby:** `standby` is set from C++ (`main.cpp:335-337`) and also written from QML (`Main.qml:271`).

## 7. run_pi_direct.sh (384 lines)

**Arguments and runtime mirror:**
- `$1` is the UI binary (default `$HOME/ApertarUI/build/Apertar-UI`); the remaining arguments are passed through (`:5-11`).
- Runtime mirror (`:13-39`):
  - Root is `APERTAR_RUNTIME_ROOT` or `APERTAR_NVME_RUNTIME_ROOT`, default `~/.cache/apertar-runtime`.
  - Mode is `APERTAR_USE_RUNTIME_MIRROR` or `APERTAR_USE_NVME_RUNTIME`, default `auto`.
  - In `auto`, the mirror is **skipped when it is on the same filesystem as the source binary** (`:23-31`).
  - It is used only if `stat '%s:%Y'` of the source equals `ui-build.signature` (`:32`). When active it exports `QT_PLUGIN_PATH` and `QML2_IMPORT_PATH` into the mirror (`:33-37`).

**mesa-minimal (`:41-71`):**
- Used if `mesa-minimal/lib/aarch64-linux-gnu/libgbm.so.1` and `50_mesa.json` exist.
- Then it prepends the Mesa lib dir, `build/apertar-runtime` (when `libproxy.so.1` exists) and `$mirror/lib` to `LD_LIBRARY_PATH`.
- It also exports `GBM_BACKENDS_PATH`, `LIBGL_DRIVERS_PATH` and `__EGL_VENDOR_LIBRARY_FILENAMES`.

**Ready-file paths:**
- `DRM_SYSFS` comes from `APERTAR_DRM_SYSFS`, default `/sys/class/drm` (`:78`).
- `MAIN_UI_READY_FILE` defaults to `${XDG_RUNTIME_DIR:-/tmp}/main-ui-ready`. `HEADLESS_READY_FILE` is `…/headless-ready`. Both are removed at start (`:79-81`).

**Connector enumeration (`:83-136`):**
- Reads `card*-*/status`, skipping Writeback connectors.
- Internal: `*-DSI-*`, `*-DPI-*`, `*-LVDS-*`, `*-eDP-*`, counted only when connected.
- HDMI: `*-HDMI-A-*`. Connected ones are tracked separately from all available ones.

**Selection (`:138-166`):**
1. If any internal connector is connected: MAIN = first internal. MONITOR = first connected HDMI, else first available HDMI even if disconnected (so the supervisor can wait for hotplug).
2. Else if HDMI is connected: MAIN = first connected HDMI. MONITOR = second connected HDMI, else another available HDMI.
3. Else: MAIN = any connected connector.

**Headless (`:168-186`):**
- Touch the headless-ready file and `APERTAR_CORE_START_READY_FILE`.
- Poll every `APERTAR_MONITOR_HOTPLUG_POLL_SECONDS` (default 1 s). When a connector connects, `exec` itself again.

**DRM card and KMS config:**
- Card is `/dev/dri/<cardN>` taken from the connector prefix. It can be overridden with `APERTAR_UI_DRM_DEVICE` / `APERTAR_MONITOR_DRM_DEVICE` (`:188-192`).
- Runtime dir is `${XDG_RUNTIME_DIR:-/tmp}/apertar-display-$UID`, mode 700 (`:194-196`).
- KMS JSON (`:198-205`): `{"device": "/dev/dri/cardN", "hwcursor": false}` written to `main-kms.json`. There is **no per-output config**: no connector names, no mode, no rotation.

**Environment exported (`:207-221`):**
- `QT_QPA_PLATFORM=eglfs`, `QT_QPA_EGLFS_INTEGRATION=eglfs_kms`, `QT_QPA_EGLFS_KMS_CONFIG=main-kms.json`.
- `QT_QPA_EGLFS_HOTPLUG_ENABLED` defaults to 1.
- Input is evdev by default via `QT_QPA_EGLFS_NO_LIBINPUT=1`. `APERTAR_QT_USE_LIBINPUT=1` switches to libinput.
- `QSG_RENDER_LOOP=basic`.
- `APERTAR_MONITOR_RUNTIME_SOCKET=$RUNTIME_BASE/monitor-state.sock`, `APERTAR_UI_READY_FILE`.
- Unsets `DISPLAY` and `WAYLAND_DISPLAY`.

**Cleanup:** trap kills the monitor supervisor and the hotplug watcher (`:230-242`).

**Split topology (HDMI on a different DRM card, typical on Pi 5: DSI/DPI on one card, HDMI on another) (`:244-319`):**
- Writes `monitor-kms.json`.
- A background `monitor_helper_supervisor` polls every 0.5 s:
  - HDMI disconnected: stop the child.
  - Connected but the main UI ready file is missing: wait. This keeps the HDMI process from competing with the cold start.
  - Connected and ready: start the child with `APERTAR_MONITOR_ONLY=1`, `QT_QPA_DISABLE_INPUT=1`, `QT_QPA_EGLFS_DISABLE_INPUT=1` and the monitor KMS config.
  - If the child dies, restart it.
- Otherwise it logs "single Qt process owns all required outputs" (`:321`).

**Same-card HDMI (`:324-382`):**
- Runs the UI in the background with `watch_same_card_hotplug`. That watcher computes a signature over the same-card HDMI connectors' status every 0.5 s.
- When the signature changes, it touches `restart-for-hdmi-hotplug` and sends SIGTERM to the UI. The script then **re-execs itself** to re-enumerate KMS outputs (`:377-380`).

**Simple case:** run the binary in the foreground (`:384`).

**Things the script does not do:**
- **There is no other relaunch loop**: a crash exits, and restart is left to systemd (UNCONFIRMED; the unit is not in the repo).
- **Logging** is only `printf` to stdout/stderr, presumably captured by journald (UNCONFIRMED).
- The re-exec passes the possibly mirror-rewritten `$APERTAR_UI_BIN` back as `$1` (`:182,379`). On the second pass the mirror check compares the mirror binary to itself. It works only because the exported env vars are inherited (UNCONFIRMED edge case).

**Plymouth handoff:** `finish_plymouth_handoff.sh` is **not called** by `run_pi_direct.sh`. It is presumably an `ExecStartPost` in the UI unit (UNCONFIRMED; see §11).

## 8. External monitor (HDMI)

**Two mechanisms, chosen by the launcher's DRM topology:**

**A. Same DRM card: one Qt process, second EGLFS QScreen.**
- `ExternalMonitorManager` reacts to `screenAdded`, `screenRemoved` and `primaryScreenChanged` (`ExternalMonitorManager.cpp:27-43`) and to `externalMonitorEnabledChanged`, `currentPageChanged` and `screenChanged` on the main window (`:61-109`).
- `syncWindow()` (`:162-186`) destroys the window unless all of these hold:
  - The main window exists and the settings bridge is set.
  - `standbyActive` is false and `currentPage=="camera"` (`:111-126`).
  - `hdmiExternalOnly || externalMonitorEnabled`.
  - An HDMI screen other than the main one exists (`:128-160`).
- `ensureWindow()` (`:188-262`):
  - Creates `qrc:/qml/ExternalMonitorWindow.qml` with `QQmlComponent` in the main engine's root context.
  - Adds a calibration renderer (hdmi=true) and a `PreviewWindowRenderer` with direct-window rendering, bound to `externalPreviewItem`.
  - Then `setScreen`, `setGeometry` and `showFullScreen`.
- Shutdown-popup state is pushed by `setProperty` on a 33 ms timer (`:31,280-313`).
- The window is **destroyed and recreated** on every page change away from and back to the camera page (`:166-172`). The monitor-only process hides instead.
- HDMI hotplug on the same card actually restarts the whole UI through the launcher (§7), so the QScreen hotplug handlers mostly matter at startup.

**B. Split DRM cards: separate `APERTAR_MONITOR_ONLY` process** (`main.cpp:131-237`).
- Own EGLFS KMS device and no input. Same QML file.
- Receives main-UI state through `ExternalMonitorRuntimeBridge`:
  - Publisher in the main UI listens on the socket (`ExternalMonitorRuntimeBridge.cpp:24-46`).
  - It serialises `cameraPageActive`, shutdown popup state, `mediaMounted`, remaining texts, recording, timelapse and timecode as one JSON line (`:246-263`) and pushes it to all clients (`:265-282`).
  - The subscriber reconnects every 500 ms (`:41,208-226,348+`).
- Preview: its own `ApertarPreviewSocketClient` subscription to Core, so it is a second consumer.
- Settings: its own `SettingsBridge` re-reads the shared `~/.config/CinePi/UI.conf` via file watching.
- Calibration: synced through the `CinePi/DisplayCalibration.conf` file watch.
- Camera state: its own `ApertarControlBridge` (third connection).

**Feeds:** "Clean Feed" vs "Assist Feed" (`SettingsBridge.cpp:289-294`). Assist enables zebra, peaking, false colour and grayscale on HDMI (`ExternalMonitorWindow.qml:375-385`).

## 9. Network helper and WifiBridge

**No direct IPC between the helper and the UI.** Coordination is through:
1. The marker file `/run/apertar-network/managed`, created by the helper (`NetworkHelper.cpp:14,21-23`) and removed on exit (`:30`). When it exists, the in-UI WifiBridge **disables its own auto-hotspot** (`WifiBridge.cpp:155-157,478-484`).
2. The shared `QSettings("CinePi","UI")` keys `hotspotSsid` and `hotspotPassword` (`WifiBridge.cpp:125-137`). The helper re-syncs them on every tick (`:494-502`).
3. Both processes talk to NetworkManager independently through `nmcli`.

**Helper process:**
- `QCoreApplication`, `APERTAR_NETWORK_HELPER=1`.
- Runtime dir from `APERTAR_NETWORK_RUNTIME` (default `/run/apertar-network`).
- Single instance via `QLockFile helper.lock` (`NetworkHelper.cpp:9-32`).

**nmcli usage:**
- All operations run through `startProcess` → `QProcess("nmcli")` (`WifiBridge.cpp:541-547`).
- Some status queries are synchronous: `queryWifiRadioEnabled` (`:592-620`), `updateDeviceStatus` (`:663-756`), `cleanupHotspotProfile` = `nmcli connection delete "Apertar Hotspot"` with a 3 s wait (`:635-643`).
- Hotspot start: `nmcli --wait 20 device wifi hotspot con-name "Apertar Hotspot" ssid <ssid> password <pw> [ifname <dev>]` (`:266-321`).
- Hotspot stop: `nmcli --wait 15 connection down "Apertar Hotspot"` (`:323-338`).
- The connection name is `"Apertar Hotspot"` (`:14`). The defaults are **hard-coded**: SSID `Apertar`, password `apertarcam` (`WifiBridge.hpp:116-117`). The password is stored in plaintext in QSettings.

**Hotspot fallback logic (`handleAutoHotspotTick`, `:476-539`):**
- Tick every 10 s (`:15,147-157`). Status refresh at most every 30 s (`:16,490-492`).
- First run 1.5 s after construction (`:158-166`).
- If there is no normal Wi-Fi connection (`hasNormalWifiConnection`: enabled, not hotspot, SSID set and status "Connected", `:627-633`) and the adapter is ready, start `m_noWifiTimer`.
- After `hotspot_delay_seconds` with no Wi-Fi, re-check status and then `startHotspot`. A precise single-shot timer covers the remainder (`:518-538`).
- An established Wi-Fi connection is never replaced.
- **Delay:** `[network] hotspot_delay_seconds` from `$APERTAR_HARDWARE_CONFIG` or `/home/pi/apertar-hardware.conf` only. There is no `/boot` fallback, unlike the other readers. Default 60, allowed 0–86400 (`:18-34`). The template comment says to restart `apertar-network.service` after changes (`DisplayConfigBridge.cpp:60-62`).

**systemd and permissions:**
- `systemd/apertar-network.service`:
  - `After`/`Wants` NetworkManager; `Type=simple`; `User`/`Group` pi.
  - `RuntimeDirectory=apertar-network` (0755).
  - **`ExecStart=/home/pi/ApertarUI/build/apertar-network-helper`**, a hard-coded build-tree path.
  - `Restart=on-failure`, 5 s; `WantedBy` multi-user.
- `systemd/apertar-network-start-gate.conf`: drop-in containing `ExecStartPre=-/usr/local/libexec/apertar-wait-ui-core-start /run/apertar-ui/main-ui-ready 8`. It is `wait_for_ui_core_start.sh` installed under another name, waiting for the UI's **first-frame** marker for up to 8 s. Which unit it is dropped into is UNCONFIRMED; the comment suggests a networking service.
- `systemd/49-apertar-network.rules` is a **polkit** JS rule. For user `pi` it grants NetworkManager `network-control`, `enable-disable-wifi`, `wifi.scan`, `settings.modify.system`, `wifi.share.protected` and `wifi.share.open` (`:1-12`).
- Sudoers files are not network-related:
  - `apertar-standby-low-power.sudoers`: NOPASSWD for `/usr/local/libexec/apertar-standby-low-power {cpu,nvme,bluetooth,all,restore}`.
  - `apertar-standby-usb.sudoers`: NOPASSWD for `… apertar-standby-usb {off,on}`. `check` is not listed.
- **Missing from the repo:** no sudoers entry covers the UI's `sudo -n mount`/`mkdir` (MediaStatusBridge), `sudo -n systemctl`/`timedatectl`/`install` (SystemActionBridge), or `sudo -n sh -c "echo 1 > …/remove"`. They must come from the image (UNCONFIRMED).

## 10. CfeAutomounter.cpp
- **Purpose:** daemon for the CFexpress HAT (Pi 5 PCIe NVMe card reader). It reads two buttons and drives a LED over I2C, and mounts or ejects the NVMe at the mount path.
- **Config** (`:107-195`):
  - Hand-parsed INI. First readable file of `$APERTAR_HARDWARE_CONFIG`, `/home/pi/…`, `/boot/firmware/…`, `/boot/…` (`:114-129`).
  - `[cfexpress_hat]`: `enabled`, `bus`/`channel`/`i2c_bus` (default 10), `address` (default 0x34).
  - `[storage]`: `mount_path` (default `/media/RAW`), `pcie_controller` (default `1000110000.pcie`).
  - `--check-config` prints the config and exits (`:770-771`).
- **Device detection is polling, not udev:**
  - Scans `/sys/class/block` for `nvme(\d+)n(\d+)p(\d+)` and picks the first partition (`:310-341`).
  - Gets the PCI address from sysfs (`:343-375`).
  - Gets the filesystem type from `blkid` (`:377-390`).
- **Main loop** (`:521-557`):
  - Mount state from `/proc/self/mountinfo` every 500 ms (`:282-308,575-590`).
  - HAT buttons via an `I2C_SMBUS` byte read every 100 ms. Bit 0 is insert, bit 1 is eject, both active-low edges. Byte 0x69 is ignored (`:400-417`).
  - Insert falling edge while unmounted triggers `mountPcie`. Eject falling edge triggers `unmountPcie`.
  - LED write is a byte 1/0 with 5 retries (`:419-441`).
- **Mount** (`mountPartition`, `:592-631`): direct `mount(2)` with `MS_NOATIME`.
  - ntfs → `ntfs3` with `uid=1000,gid=1000`.
  - exfat/vfat with `uid=1000,gid=1000,umask=0002`.
  - ext4 with no options.
  - Anything else is rejected.
  - It needs root. The unit is not in the repo (UNCONFIRMED).
- **Insert** (`mountPcie`, `:651-673`): try the existing partition. Otherwise reset the PCIe controller by unbinding and binding `/sys/bus/platform/drivers/brcm-pcie`, wait 2 s, then write `/sys/bus/pci/rescan` and wait 3 s (`:632-649`).
- **Eject** (`unmountPcie`, `:693-731`): `syncfs` + `BLKFLSBUF`, wait 500 ms, `umount2`, write `1` to `/sys/bus/pci/devices/<addr>/remove`, `udevadm settle`.
- **Startup:** mount if a partition or controller exists, otherwise probe PCIe once (`:733-747`). Then write `/run/apertar-cfe/ready` (`:40,527-528`). The ready file is removed on SIGTERM (`:558-560`).
- **Notification:** it does not notify Core or the UI directly. They observe the mount via mountinfo/QStorageInfo (MediaStatusBridge 1 s poll). The UI checks `/run/apertar-cfe/ready` (`MediaStatusBridge.cpp:747`).

## 11. Helper scripts

**`sync_pi_runtime.sh` (92 lines)** builds and refreshes the runtime mirror.
- Arguments: `PROJECT_ROOT` (default script dir) and `DESTINATION` (default `APERTAR_RUNTIME_ROOT`, `APERTAR_NVME_RUNTIME_ROOT` or `~/.cache/apertar-runtime`) (`:5-10`).
- Refuses a destination that is relative or under `/media/RAW` (`:16-19`).
- Copies:
  - The UI binary to `bin/Apertar-UI` (`:21-22`).
  - `mesa-minimal/` (`:24-28`).
  - `build/apertar-runtime/` (the libproxy stub) (`:29-33`).
  - **All** of `/usr/lib/aarch64-linux-gnu/qt6/plugins` and `/qml` into `qt6/` (`:35-37`). The aarch64 path is hard-coded.
  - `ldd`-resolved dependencies of the UI into `lib/`, resolved with the mesa and stub dirs on `LD_LIBRARY_PATH` (`:39-51`).
  - `apertar-video-libav.so` and its dependencies (`:53-60`).
  - Dependencies of the platforms, egldeviceintegrations, generic and imageformats plugins and the QtQml/Models, QtQuick/Controls, QtQuick/Window and QtQuick/*.so QML modules (`:62-80`).
- Strips the mirror binary (`:84-86`).
- Writes `stat '%s:%Y'` of the **source** binary to `ui-build.signature` (`:88`). This is what `run_pi_direct.sh:32` compares.
- README context: `README.md:299-305`.

**`wait_for_ui_core_start.sh` (56 lines)** is a start gate, installed as `/usr/local/libexec/apertar-wait-ui-core-start` (per `systemd/apertar-network-start-gate.conf:4`).
- Arguments: `READY_FILE` (default `/run/apertar-ui/core-start-ready`) and `TIMEOUT` (default 8 s) (`:5-11`).
- Exits immediately if no DRM connector is connected (`:21-33`) or the file already exists (`:35-38`).
- Otherwise polls every 25 ms against a `/proc/uptime` monotonic clock (`:40-52`).
- Always exits 0, including on timeout (`:54-56`), so it never blocks the dependent unit.
- The UI writes `core-start-ready` via `APERTAR_CORE_START_READY_FILE` after `Main.qml` loads (`main.cpp:405-420`). The network gate instead points it at `main-ui-ready` (first frame).
- Its use by `apertar-core.service` is UNCONFIRMED (the unit is not in the repo).

**`finish_plymouth_handoff.sh` (30 lines)** ends the boot splash.
- `READY_FILE` defaults to `${XDG_RUNTIME_DIR:-/run/apertar-ui}/main-ui-ready`. Timeout is `APERTAR_PLYMOUTH_HANDOFF_TIMEOUT_SECONDS` (default 20). Binary is `APERTAR_PLYMOUTH_BIN` (default `/usr/bin/plymouth`). There is also a headless-ready file (`:5-8`).
- No-op if plymouth is absent (`:10-12`).
- Polls every 50 ms for the main-UI or headless marker (`:14-25`).
- Then `plymouth quit --retain-splash` (`:28`). The splash is kept until Qt's framebuffer has presented, which avoids a black flash.
- Its caller is not in the repo; UNCONFIRMED, probably an `ExecStartPost` of `apertar-ui-direct.service`.

## 12. Playback (brief)
- **ClipListModel** scans `rootPath` (default `/media/RAW`, `cliplistmodel.cpp:174`):
  - DNG sequences (`*.dng`).
  - Stills: dng, jpg, png, tif, tiff (`:24-35`).
  - MLV (`:600`) and movies.
  - Thumbnails go through `image://cdngthumb` (`:68`).
- **PlaybackController:**
  - Timer-driven frame advance (`playbackcontroller.cpp:386,1097`).
  - DNG frames go through `cdng` (exact frame) and `cdngplay` (prefetching, `previewOnly`) (`:490-505`).
  - Movies are fed from `VideoImageProvider::frameDecoded` (`main.cpp:362-365`).
  - Audio: WAV sidecar `<clip>.wav`, `<dir>.wav`, `audio.wav` or any `*.wav` (`:877-888`), streamed to an `aplay` subprocess (`:996`). Only PCM16 sidecars are supported (`README.md:144`).
  - Histogram from `DngDecoder::decodeHistogramBins`.
- **CdngImageProvider:** LRU-ish image cache with byte and count limits, prefetch on a `QThreadPool` (`cdngimageprovider.h:18-48`). `renderRawFramePreview` CPU debayer is at `cdngimageprovider.cpp:832`.
- **DngDecoder:** TIFF/DNG parse, uncompressed or LJ92 (`dngdecoder.cpp:16-63,653`). `PhotometricLinearRaw` = 34892 (`:21`).
- **MlvReader:** Apertar single-file uncompressed MLV: block scan, raw info, white balance, preview matrix, frame index (`MlvReader.hpp:13-40`).
- **VideoPlayback:** `isMovie` = mov/mp4/mlv (`VideoPlayback.cpp:39-43`). For mov/mp4 it loads the plugin from `APERTAR_VIDEO_PLAYBACK_PLUGIN`, `<appdir>/apertar-video-libav.so` or `<appdir>/../lib/apertar-ui/…` and requires `version==2` (`:18-36`). The ABI is probe/open/read/close (`VideoPlaybackApi.h:6-27`). The plugin entry point is `VideoPlaybackLibav.cpp:222`.

## 13. Bugs, inconsistencies, duplicate paths, dead code, hard-coded paths

### Bugs and risks
1. **Binary name depends on the moc path.** `OUTPUT_NAME "Apertar-UI"` is only set when `/usr/lib/qt6/libexec/moc` exists (`CMakeLists.txt:252-260`). Otherwise the build produces `build/ApertarUI` and the scripts (`run_pi_direct.sh:5`, `sync_pi_runtime.sh:8`) fail.
2. **Synchronous Core commands block the GUI thread.** `sendCoreCommand` blocks for up to 60 s on `record_stop`, 10 s on reconfigures and 3 s by default (`ApertarControlBridge.cpp:1013-1105`). It opens a new socket per command. MediaStatusBridge's `format_media` waits up to **360 s** (`MediaStatusBridge.cpp:1192`) and also blocks.
3. **Fragile preview JSON parsing.** It uses substring scanning (`ApertarPreviewSocketClient.cpp:585-625`). Spaces after the colon in the key (`"key" :`) or nested keys with the same name would break it, and so would key prefixes (searching `"slot":` is safe, but `"width":` would also match inside `"capture_width":`?). **Check:** the pattern is `"\"" + key + "\":"`, so `"width":` does not match `"capture_width":` (the quote precedes the key). That case is OK. Spacing before the colon is still unhandled.
4. **Focus-peaking texel size is hard-coded** to `1/1920 × 1/1080` regardless of the real preview texture size (`PreviewWindowRenderer.cpp:858`). Peaking sensitivity changes with preview resolution.
5. **Default peaking threshold mismatch:** 0.08 in `CameraPreviewItem.hpp:137`, but 0.04 in the renderer cache (`PreviewWindowRenderer.hpp:132`) and the QML fallbacks (`CameraPage.qml:1985`, `ExternalMonitorWindow.qml:379`).
6. **`hdmi_external_only=true` with `windowed=true` shows nothing (likely; UNCONFIRMED at runtime).** `main.cpp:428-429` hides the main window, while `:514` passes `hdmiExternalOnly && !windowed` = false and `:517-518` skips `setSettingsBridge`. `ExternalMonitorManager::syncWindow` then returns early (`ExternalMonitorManager.cpp:164-167`).
7. **Ready-file path mismatch.** Without `XDG_RUNTIME_DIR` or `APERTAR_UI_READY_FILE`, the launcher writes `/tmp/main-ui-ready` (`run_pi_direct.sh:79`). The network gate and Plymouth defaults use `/run/apertar-ui/main-ui-ready` (`apertar-network-start-gate.conf:4`, `finish_plymouth_handoff.sh:5`). They then fall back to their 8 s / 20 s timeouts. The service file that sets the env is not in the repo.
8. **Monitor-only process lacks `gyroConfigBridge`** (`main.cpp:147-154`), so the HDMI horizontal level is always "unavailable" in the split-DRM topology.
9. **Wi-Fi hotspot defaults** `Apertar`/`apertarcam` are hard-coded and the password is stored in plaintext in `~/.config/CinePi/UI.conf` (`WifiBridge.hpp:116-117`, `WifiBridge.cpp:131-137`).
10. **`SystemActionBridge::restartCamera()` reboots the whole Pi** (`SystemActionBridge.cpp:274-277`), despite its name.

### Duplicate code paths and multiple sources of truth
- **Two different default hardware.conf templates:** `DisplayConfigBridge.cpp:41-326` and `Ina219Bridge.cpp:69-341`. Whichever runs first wins; DisplayConfig is constructed first (`main.cpp:278`).
- **Five separate hardware.conf candidate-path implementations:** DisplayConfigBridge (`:25-39`), Ina219Bridge (`:48-66`), GyroConfigBridge (`:195-207`), CfeAutomounter (`:114-129`), and the dead embedded Python in MediaStatusBridge (`:771-781`). WifiBridge has a sixth variant with no `/boot` fallback (`:18-24`).
- **Mount path:** `[storage] mount_path` is honoured by CfeAutomounter, but the UI hard-codes `/media/RAW` in MediaStatusBridge (`.hpp:136`), ClipListModel (`.cpp:174`) and the SettingsBridge LUT and tuning dirs (`:148,172`).
- **Many separate Core connections per process:** the control event socket, a per-command socket, preview, media and audio-capabilities. The monitor-only process repeats them.
- **Preview connect/disconnect on standby** happens in C++ (`main.cpp:344-346`) and in QML (`ExternalMonitorWindow.qml:283-291`, which also runs in-process).
- **Standby state** is written from C++ (`main.cpp:337`) and QML (`Main.qml:271`).
- **External-monitor shutdown-popup state** is pushed by `ExternalMonitorManager` via `setProperty` (`:299-303`), which breaks the QML bindings to `monitorRuntimeBridge` in the same window (`ExternalMonitorWindow.qml:9-23`).
- **Peaking colour mapping** is duplicated in the renderer (`PreviewWindowRenderer.cpp:2124` and `:2352`).
- **Resolution and crop tables are hard-coded** in QML for imx477, imx294 and imx585 (`SettingsPage.qml:110-225`, `CameraPage.qml:392-443,1052-1191`). They duplicate Core's capability knowledge.
- **Inconsistent QSettings org/app names:** `CinePi/UI` (control, settings, wifi), `CinePi/DisplayCalibration`, `Apertar/StandbyBacklights`. There are many concurrent writers to `~/.config/CinePi/UI.conf`: the main UI, the monitor-only process and the network helper.
- **The local power-button path** (`PowerButtonBridge` + `Main.qml:262-283`) runs only when Core is disconnected. Otherwise Core's `hardware_action power_button_press` is used (`Main.qml:288-295`).

### Dead or unused code
- In `MediaStatusBridge.cpp`, these functions are defined but never called (grep finds only their definitions):
  - `startNvmeReinsertWatcher` (`:742-972`), which contains an embedded ~200-line **Python** I2C/PCIe watcher launched with `python3 -c`.
  - `detachNvmeController` (`:711`).
  - `mountFormattedDevice` (`:1039`).
  - `flushMedia` (`:1046`).
  - `formatFilesystemToolPath` (`:206`) and `volumeLabelForFormat` (`:236`).
  - Format and eject have moved to Core (`:1183-1196`).
- `qml/GyroOrientationIndicator.qml` is compiled (`CMakeLists.txt:51`, `qml.qrc:33`) but never used.
- `qml/InlineChoice.qml` is not in the build and is unused.
- `qml/DroppedFrameWarning.qml` is in `CMakeLists.txt:40` but **missing from `qml.qrc`**. The non-AOT build (`APERTAR_QML_AOT=OFF`, the cross-compile default) would fail to resolve it in CameraPage and ExternalMonitorWindow (UNCONFIRMED at runtime).
- Unused fonts: Gotham Black/Light/Medium/Thin and Inter Black/Thin are on disk but not in `resources.qrc`.
- `ApertarControlBridge::loadPersistedCameraSettings()` only calls `m_settings.sync()` (`:884-887`), a vestigial name.

### Hard-coded paths
| Path | Where |
|---|---|
| `/tmp/apertar-core.sock` | `ApertarControlBridge.cpp:1032,1567`; `ApertarPreviewSocketClient.hpp:30`; `MediaStatusBridge.cpp:23`; `AudioDeviceBridge.cpp:347` |
| `/home/pi/apertar-hardware.conf` | DisplayConfig, Ina219, Gyro, Wifi, CfeAutomounter |
| `/home/pi/LUTs`, `/home/pi/Tuning-Files` | SettingsBridge |
| `/media/RAW` | MediaStatusBridge, ClipListModel, SettingsBridge, sync script guard |
| `/home/pi/ApertarUI/build/apertar-network-helper` | `apertar-network.service:14` |
| `$HOME/ApertarUI/build/Apertar-UI` | `run_pi_direct.sh:5` |
| `/usr/lib/aarch64-linux-gnu/qt6` | `sync_pi_runtime.sh:36-37` |
| `/boot/firmware/config.txt`, `/boot/firmware/camera-selection.txt` | SystemAction, DeviceInfo |
| `/run/apertar-network/managed`, `/run/apertar-cfe/ready`, `/run/apertar-standby-*` | WifiBridge/NetworkHelper, CfeAutomounter/MediaStatusBridge, standby helpers |
| `1000110000.pcie`, I2C bus 10 / 0x34 (CFE), bus 4 / 0x40 (INA219) | CfeAutomounter, Ina219Bridge |
| Pi 5 USB hub addresses `1f00200000.usb` / `1f00300000.usb` | `StandbyUsbPower.cpp:69-70` |

### Environment variables
`APERTAR_MONITOR_ONLY`, `APERTAR_UI_READY_FILE`, `APERTAR_CORE_START_READY_FILE`, `APERTAR_HEADLESS_READY_FILE`, `APERTAR_CONTROL_SOCKET`, `APERTAR_MONITOR_RUNTIME_SOCKET`, `APERTAR_HARDWARE_CONFIG`, `APERTAR_MEDIA_ROOT`, `APERTAR_BACKLIGHT_DIR`, `APERTAR_PANEL_LED_PATH`, `APERTAR_STANDBY_PANEL_POWER`, `APERTAR_PREVIEW_FORCE_{CPU,PLANAR,EGL}`, `APERTAR_VIDEO_PLAYBACK_PLUGIN`, `APERTAR_NETWORK_HELPER`, `APERTAR_NETWORK_RUNTIME`, `APERTAR_RUNTIME_ROOT`, `APERTAR_NVME_RUNTIME_ROOT`, `APERTAR_USE_RUNTIME_MIRROR`, `APERTAR_USE_NVME_RUNTIME`, `APERTAR_MESA_RUNTIME_ROOT`, `APERTAR_RUNTIME_LIB_DIR`, `APERTAR_DRM_SYSFS`, `APERTAR_UI_DRM_DEVICE`, `APERTAR_MONITOR_DRM_DEVICE`, `APERTAR_MONITOR_HOTPLUG_POLL_SECONDS`, `APERTAR_QT_USE_LIBINPUT`, `APERTAR_PLYMOUTH_BIN`, `APERTAR_PLYMOUTH_HANDOFF_TIMEOUT_SECONDS`, `APERTAR_UI_BIN` (sync script).
