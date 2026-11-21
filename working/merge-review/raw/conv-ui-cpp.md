# C5 conventions: the touch UI's C++ side (Apertar-UI 1.6.0)

Scope: `/home/user/wt/ui-upstream` at tag `upstream-1.6.0` (`43888e5`): `src/*`, `CMakeLists.txt`, `qml.qrc`,
`resources.qrc`, `run_pi_direct.sh`. All refs below are `@upstream-1.6.0` unless marked. Paths are repo-relative
(`src/...`). Core paths are `Core:src/...` at `core-upstream`.

Strength: **always** = no counter-example (search named); **usually** = exceptions named; **once** = single precedent.
Kind: STRUCTURE / IDIOM / INTENT.

---

## 1. Startup and context properties (`src/main.cpp`)

| Fact | Evidence |
| --- | --- |
| Every bridge is a **stack object in `main()`**, constructed in one block, no parent, no singleton, no `qmlRegisterSingletonType` | `src/main.cpp:290-309` |
| Cross-bridge wiring is done in `main()` with plain setter injection (`setControlBridge`, `setSettingsBridge`, `setMediaBridge`) and `QObject::connect` | `src/main.cpp:316-329` |
| Standby fan-out is one lambda in `main()` calling `setStandby(bool)` on each bridge that polls | `src/main.cpp:333-347` |
| Every bridge reaches QML through `engine.rootContext()->setContextProperty("<name>", &obj)`; 23 names | `src/main.cpp:374-396` |
| Only one `qmlRegisterType` in the whole UI: `CameraPreviewItem` as `Apertar 1.0` | `src/main.cpp:274` (grep `qmlRegister` in `src/`: one hit) |
| Context names: `<concern>Bridge` (`statsBridge`, `mediaBridge`, `powerBridge`, `wifiBridge`, `settingsBridge`, `apertarControlBridge`, `apertarPreviewBridge`), plus `sleepManager`, `clipModel`, `playbackController`, image providers, and one bool `hdmiExternalOnly` | `src/main.cpp:374-396` |
| Second entry mode: `APERTAR_MONITOR_ONLY` runs `runMonitorOnly()` with its own, smaller set of bridges and its own context-property list (`mediaBridge` is bound to `monitorRuntimeBridge` there, `audioMeterBridge` to `nullptr`) | `src/main.cpp:131-155`, `:275-276` |
| `AudioMixerBridge` is constructed and wired but **not** exposed to QML | `src/main.cpp:306`, `:328`; no `setContextProperty("audioMixerBridge"` and no `audioMixerBridge` in `qml/` |
| Startup log lines use `qInfo().noquote() << QStringLiteral("Apertar UI startup: ... in %1 ms")` with an elapsed timer | `src/main.cpp:265-268`, `:285-288`, `:311-313`, `:398-400` |
| C++ finds QML items by `objectName` (`previewContainer`, `previewItem`, `externalPreviewItem`) | `src/main.cpp:490-491`, `:178-179` |
| C++ reads Main.qml root properties **by name string** (`currentPage`, `monitorRecordingActive`, `powerButtonShutdown*`) | `src/ExternalMonitorRuntimeBridge.cpp:135-152`, `src/ExternalMonitorManager.cpp:113-121`, `:288-300` |
| Ready markers via env-named files (`APERTAR_UI_READY_FILE`, `APERTAR_CORE_START_READY_FILE`) written after first frame | `src/main.cpp:405-421`, `:450-482` |

## 2. The bridge pattern

Shape of a bridge (`ApertarControlBridge.hpp`, `SettingsBridge.hpp`, `SystemActionBridge.hpp`, `WifiBridge.hpp`, `GyroConfigBridge.hpp`, `MediaStatusBridge.hpp`):

| Element | Form | Evidence |
| --- | --- | --- |
| One class per concern, one `.hpp`/`.cpp` pair, file name = class name, suffix `Bridge` | `SystemStatsBridge`, `WifiBridge`, `Ina219Bridge`, `GyroConfigBridge`, `MediaStatusBridge`... | `CMakeLists.txt:72-109` |
| Read-only state: `Q_PROPERTY(T x READ x NOTIFY xChanged)`; inline getter in header for trivial members | | `src/ApertarControlBridge.hpp:16-58`, `:68-104` |
| Several properties can share one NOTIFY signal (`recordingCapabilitiesChanged` for 6; `exposureCompensationChanged` for 3; `audioCaptureOptionsChanged` for 3) | | `src/ApertarControlBridge.hpp:23-24`, `:34-39`; `src/SettingsBridge.hpp:68-70` |
| UI preference state: `Q_PROPERTY(T x READ x WRITE setX NOTIFY xChanged)`; QML writes it directly | | `src/SettingsBridge.hpp:18-88` |
| Actions: `Q_INVOKABLE bool apply<Thing>(const QString &displayValue)` returning success; failure detail goes to `lastError` | | `src/ApertarControlBridge.hpp:111-141`; `src/SystemActionBridge.hpp:25-27` (`applyTimeZone`, `applyDateTime`, `applyFanMode`) |
| Other invokable verbs: `refresh()`, `set<X>(...)`, `start/stop<X>`, `connectTo<X>`, `calibrate<X>`, `capture<X>`, `enter/wake` | | `src/WifiBridge.hpp:47-52`, `src/GyroConfigBridge.hpp:68-83`, `src/MediaStatusBridge.hpp:69-75`, `src/ApertarControlBridge.hpp:98-99`, `:139-141` |
| Error surface to the operator: `Q_PROPERTY(QString lastError ... NOTIFY lastErrorChanged)` set by `setLastError()` | | `src/ApertarControlBridge.hpp:58`, `src/SystemActionBridge.hpp:10`, `WifiBridge.hpp` (grep: 3 bridges) |
| Private setters `setX(value)` / `setXValue(value)`: compare, assign, emit | `if (m_fps == value) return; m_fps = value; emit fpsChanged();` | `src/ApertarControlBridge.cpp:2230-2237`, `:2239-2246`, `:2353-2363` |
| Per-concern event outputs as signals with arguments (`recordingFailed(QString)`, `gyroCalibrationFinished(bool, QString)`, `hardwareActionTriggered(QString)`) | | `src/ApertarControlBridge.hpp:180-192` |
| Non-QML plumbing on bridges is plain public methods (not invokable): `setControlBridge`, `setStandby`, `cameraPresetSettings`, `applyCameraPreset` | | `src/SettingsBridge.hpp:91-93`; `src/ApertarControlBridge.hpp:142-143`; `src/GyroConfigBridge.hpp:71` |
| File-local helpers in an anonymous `namespace {}` at top of the `.cpp` | | `src/ApertarControlBridge.cpp:15-114`; `src/SettingsBridge.cpp:~20-282`; `src/DisplayConfigBridge.cpp:15-560`; `src/main.cpp:44-247` |
| Display strings are the property values. Bridge parses display text in (`parseFpsValue`), formats Core values out (`formatFpsValue`), so QML passes and shows `"24.000"`, `"180°"`, `"1/48"`, `"5600K"`, `"12-bit"`, `"Match Capture"` | | `src/ApertarControlBridge.hpp:211-243`; defaults `:278-298` |

## 3. ApertarControlBridge and Core

### 3.1 Two connections

| Channel | Use | Evidence |
| --- | --- | --- |
| `m_eventSocket` (persistent `QLocalSocket`) | events, async `get_state` poll, fire-and-forget `user_activity` | `src/ApertarControlBridge.cpp:122-146`, `:855-873`, `:1176-1180`, `:1557-1589` |
| Per-command `QLocalSocket` inside `sendCoreCommand` | every command, opened, written, **blocking** wait for the matching `id` reply, closed | `src/ApertarControlBridge.cpp:1013-1106` |

Socket path: `qEnvironmentVariable("APERTAR_CONTROL_SOCKET", "/tmp/apertar-core.sock")`, written twice
(`:1032`, `:1567`). Wire: compact JSON + `\n`, keys `cmd`, `id`, replies `ok` / `error`, events `event`
(`:1044-1050`, `:1081-1088`, `:1184`).

### 3.2 `sendCoreCommand` timeouts (all on the GUI thread)

| Command class | Reply timeout | Evidence |
| --- | --- | --- |
| connect | 350 ms | `:1015`, `:1036` |
| write | 500 ms | `:1053` |
| `record_stop` | 60 000 ms | `:1029` |
| `calibrate_gyro` | 8 000 ms | `:1030` |
| "reconfigure" list (13 names: `set_resolution`, `set_capture_mode`, `set_raw_bit_depth`, `set_record_format`, `set_tuning_file`, `set_prores_color_profile`, `set_cdng_preview_color_profile`, `set_h264_resolution`, `capture_photo`, `timelapse_start`, `wake`, `enter_standby`, `apply_preset`) | 10 000 ms | `:1016-1028`, `:1031` |
| everything else | 3 000 ms | `:1031` |

- The wait loop is `waitForReadyRead(min(remaining, 250))` (`:1094-1098`). The GUI thread is blocked for the whole
  wait. No `QThread`/`QtConcurrent` in the bridge (grep `QThread|QtConcurrent` in `src/ApertarControlBridge.*`: none).
- Every message read while waiting is fed to `applyCoreMessage()` (`:1075`), so events are not lost.
- The **state poll** is the one async path, with the reason in a comment: "Hardware mode switches can take seconds.
  Poll asynchronously so a status refresh cannot block the GUI thread behind that camera operation." (`:861-862`).
  10 s timeout aborts the event socket (`:866-871`). Poll interval 1 s while disconnected, 30 s steady
  (`:17-18`, `:875-882`).
- Failure paths set `connected=false`, zero the audio level, set a human `lastError`
  ("Waiting for ApertarCore control socket...", "Timed out waiting for ApertarCore reply.") (`:1037-1043`, `:1101-1105`).

### 3.3 Shape of an `apply*` method

Pattern, repeated about 25 times (`:255-850`):

1. Parse display value. Invalid -> `setLastError("Invalid <thing> value.")`, `return false` (`:257-261`, `:624-628`, `:640-644`).
2. Optional capability gate from Core caps -> `setLastError("... requires Raspberry Pi 5-class hardware.")` (`:432-441`, `:496-499`, `:518-521`).
3. `if (!sendCoreCommand("set_<x>", {{"value", v}})) return false;` (`:630`, `:646`, `:662`).
4. On success: `setXValue(format(...))` and `saveCurrentCameraSettings()` (`:648-650`, `:300-303`).
5. `return true;`

Thin variants just `return sendCoreCommand(...)` and rely on the reply/event to update state (`:712-748`, `:817-829`, `:1108-1116`, `:1166-1174`).

Argument values: flat scalars. Booleans are usually sent as the strings `"true"`/`"false"`
(`:727`, `:739`, `:746`, `:791-794`); numbers are sent as JSON numbers (`:270`, `:309`, `:819`).

### 3.4 Core state -> property

`applyCoreMessage(message)` (`:1182-1259`) dispatches on `event`; a known set of events and every reply carrying
`ok` falls through to `applyCoreState(state)` (`:1256-1258`). `applyCoreState` (`:1261-1555`) is one long function:

```cpp
if (state.contains(QStringLiteral("af_mode")))
    setAutofocusModeValue(formatAutofocusModeValue(state.value(QStringLiteral("af_mode")).toString()));
```
(`:1475-1476`; same shape `:1446-1447`, `:1449-1450`, `:1478-1482`). Grouped values (caps object) compare all members and emit one signal (`:1286-1306`).

Core key spelling is `snake_case` (`af_mode`, `raw_bit_depth`, `h264_width`); C++ properties are `camelCase`.

### 3.5 Local cache of camera values

- Camera values are cached under `camera/*` in UI.conf by `saveCurrentCameraSettings()` (`:973-1011`) and read
  back as placeholders by `loadPersistedCameraSettings()` (`:884-971`).
- Intent stated in code: "Cached values are placeholders only. Core owns restart/format restoration." (`:886`).
- `setRecording` reads audio/gyro preferences **directly from UI.conf** (`m_settings.sync()` then `value(...)`) and
  sends them as `record_start` arguments (`:777-814`). UI.conf preferences reach Core at take start, not by a
  separate command.

## 4. SettingsBridge and UI.conf

| Fact | Evidence |
| --- | --- |
| File: `QSettings("CinePi", "UI")` = `~/.config/CinePi/UI.conf`. Opened independently by `SettingsBridge`, `ApertarControlBridge`, `WifiBridge` | `src/SettingsBridge.cpp:287`; `src/ApertarControlBridge.cpp:118`; `src/WifiBridge.cpp:127` |
| Core reads/writes the same file | `Core:src/ApertarCoreApp.cpp:341-348` (`sharedUiSettingsPath`) |
| Other QSettings files: `CinePi/DisplayCalibration`, `Apertar/StandbyBacklights` | `src/DisplayCalibration.cpp:49`; `src/SleepManager.cpp:56` |
| Keys are bare camelCase, equal to the Q_PROPERTY name (`zebraEnabled`, `guidesThickness`, `timecodeMode`), except the control bridge's `camera/*` group | `src/SettingsBridge.cpp:324-407`; `src/ApertarControlBridge.cpp:982-1010` |
| Defaults live inline in the constructor read: `m_settings.value("zebraEnabled", false)` | `src/SettingsBridge.cpp:324-407` |
| Read-time normalization/clamping via file-local helpers or `qBound` | `:346` (`qBound(1, ..., 4)`), `:351-360`, `:396` |
| Setter: compare, assign, `if (!m_externalSettingsSyncing) m_settings.setValue(key, v);`, usually `m_settings.sync(); updateSettingsFileState();`, emit | `src/SettingsBridge.cpp:597-607`, `:1145-1155`; 67 guarded `setValue` vs 32 `sync()` (grep counts): some setters skip `sync()` (`setZebraThreshold` `:614-622`) |
| External change reload: `QFileSystemWatcher` on the UI.conf file and preset directory, plus 10 s poll fallback with a comment saying why | `src/SettingsBridge.cpp:411-432` |
| `pollExternalSettings()` re-reads **every** key by calling each setter with the current value as fallback | `src/SettingsBridge.cpp:502-590` |
| Comment explaining the merge race | `src/SettingsBridge.cpp:471-472` |
| Presets: `serializeCurrentSettings()` lists every key again; `applySettingsObject()` applies it; camera keys go through `ApertarControlBridge::cameraPresetSettings()`/`applyCameraPreset()` -> Core `apply_preset` | `src/SettingsBridge.cpp:2030`, `:2109`; `src/ApertarControlBridge.cpp:1118-1164` |
| Preset I/O status uses `presetStatusText`/`presetStatusError` properties, not `lastError` | `src/SettingsBridge.hpp:86-87`; `src/SettingsBridge.cpp:1721-1729` |

So one UI.conf key appears in up to five places in `SettingsBridge.cpp` (ctor, poll, setter, serialize, apply),
plus the header (Q_PROPERTY, getter, setter, signal, member). That is the Apertar way; there is no key table.

## 5. Duplicated lists and limits (bridge vs QML vs Core)

| List | Copies | Evidence |
| --- | --- | --- |
| Shutter angle presets (11.25 ... 360) | C++ snap table and QML option list | `src/ApertarControlBridge.cpp:92-95`; `qml/CameraPage.qml:497` |
| Shutter speed presets (1/24 ... 1/1000) | C++ snap table and QML option list | `src/ApertarControlBridge.cpp:103-105`; `qml/CameraPage.qml:495` |
| Resolution names | C++ `formatResolutionValue` / 210-line `parseResolutionValue` if-chain; QML per-sensor tables in both pages | `src/ApertarControlBridge.cpp:1646-1663`, `:1797-2005`; `qml/CameraPage.qml:377-490`; `qml/SettingsPage.qml:110-225` (ui-map 1.1/1.2) |
| Timelapse intervals | QML `TimelapseIntervals.js` presets; C++ `normalizePhotoTimelapse` | `qml/TimelapseIntervals.js:3-5`; `src/SettingsBridge.cpp:223` |
| Default hardware config template | written by two UI bridges, the texts have drifted (`[network]`, `[run_script]` only in one) | `src/DisplayConfigBridge.cpp:41-~340`, `src/Ina219Bridge.cpp:69-~360` |
| `hardwareConfigCandidatePaths()` | four copies | `src/DisplayConfigBridge.cpp:25-38`; `src/GyroConfigBridge.cpp:198-211`; `src/Ina219Bridge.cpp:53-66`; `src/CfeAutomounter.cpp:117-121` |
| `lutSearchDirectories` / `tuningFileSearchDirectories` | two near-identical functions | `src/SettingsBridge.cpp:140-162`, `:164-186` |
| Socket path default | two literals in one file | `src/ApertarControlBridge.cpp:1032`, `:1567` |
| QML file list | `CMakeLists.txt` (AOT) and `qml.qrc` (non-AOT), same order | `CMakeLists.txt:19-52`; `qml.qrc:3-33` |
| Env flag parser | two copies | `src/main.cpp:51-59`; `src/PreviewWindowRenderer.cpp:43-50` |

ISO and FPS option lists exist only in QML (`qml/CameraPage.qml:498`, `:511-513`, FPS limit tables `:646-828`), not in the bridge.

## 6. Helper binaries

| Target | Output name | Kind | Install | Evidence |
| --- | --- | --- | --- | --- |
| `ApertarCfeAutomounter` | `apertar-cfe-automounter` | plain C++ + Threads, no Qt, `-Wall -Wextra -Wpedantic` | manual copy to `/usr/local/libexec`; service not in repo | `CMakeLists.txt:149`, `:159-167`; KB `architecture/build.md:139` |
| `ApertarStandbyUsbPower` | `apertar-standby-usb` | plain C++, `check|off|on`, state in `/run/apertar-standby-usb` | `/usr/local/libexec`, `sudoers` with exact args, called by **Core** via `sudo -n` | `CMakeLists.txt:150`, `:154-155`; `src/StandbyUsbPower.cpp:23`, `:246`; `systemd/apertar-standby-usb.sudoers:1`; `Core:src/ApertarCoreApp.cpp:1544` |
| `ApertarStandbyLowPower` | `apertar-standby-low-power` | plain C++, `cpu|nvme|bluetooth|all|restore` | same pattern | `CMakeLists.txt:151-153`; `src/StandbyLowPower.cpp:17`, `:153`; `systemd/apertar-standby-low-power.sudoers:1`; `Core:src/ApertarCoreApp.cpp:1549` |
| `ApertarNetworkHelper` | `apertar-network-helper` | Qt Core, reuses `WifiBridge.cpp` | run from build dir by `systemd/apertar-network.service:14` | `CMakeLists.txt:156-158` |
| `ApertarDirectProxy` | `libproxy.so.1` | C stub to keep QtNetwork's proxy stack off cold start | `build/apertar-runtime`, picked by `run_pi_direct.sh` | `CMakeLists.txt:169-182`; `run_pi_direct.sh:47-68` |
| `apertar-video-libav` | MODULE | FFmpeg kept out of cold boot | the only `install()` rule: `lib/apertar-ui` | `CMakeLists.txt:132-147` |

Shared traits: CMake target `Apertar<Name>`, `OUTPUT_NAME "apertar-<name>"`, `AUTOMOC OFF AUTORCC OFF`, a single
`src/<Name>.cpp`, subcommand as `argv[1]`, usage text on `std::cerr`, state under `/run/apertar-<name>`, fixed
argument whitelist in sudoers. Core's caller comment: "Fixed executable and arguments only; never accept paths from
WebUI/config." (`Core:src/ApertarCoreApp.cpp:1543`).

## 7. Raspberry Pi models and displays

| Fact | Evidence |
| --- | --- |
| The UI does not branch on Pi model for features. It reads Core's `recording_capabilities` (`raw_compression`, `raw_recording`, `prores`, `h264_hardware`, `h264_max_width`, `h264_max_fps`) | `src/ApertarControlBridge.cpp:1286-1306`; props `hpp:34-39` |
| Capability gates in `apply*` give the operator a board message ("requires Raspberry Pi 5-class hardware", "RAW clip recording is not available on this board. Use H.264.") | `src/ApertarControlBridge.cpp:432-441`, `:496-499`, `:518-521` |
| README rule: "Board and sensor restrictions must remain enforced in Core as well as reflected in the interface." | `README.md:324`; board table `README.md:61-65` |
| One model probe in UI code: `/proc/device-tree/model` contains "raspberry pi 3" -> planar YUV preview path (GPU limitation) | `src/PreviewWindowRenderer.cpp:33-41`, `:295` |
| Model string shown on Info page only | `src/DeviceInfoBridge.cpp:65-67` |
| Display choice is name/size heuristics: HDMI by screen name; internal panel by name `dpi|dsi|lcd|panel` or 720x720; touch panel by `/proc/bus/input/devices` text | `src/main.cpp:46-89` |
| Display geometry, layout, rotation, opacity, windowed, `hdmi_external_only` come from `[display]` in `apertar-hardware.conf`, with alias key lists and clamps | `src/DisplayConfigBridge.cpp:575-654` |
| Pi-specific runtime choices live in the launcher script (Mesa VC4/V3D build, runtime mirror), not in C++ | `run_pi_direct.sh:41-68` |
| `grep -n -i "pi 3|pi3|pi 4|pi4|pi 5|pi5|bcm27|model" src/*.cpp run_pi_direct.sh` returns only the hits above (rest are IMU register names, `lsblk MODEL`, list models) | run 2026-11-17 |

## 8. Paths, env overrides

- Fixed Pi paths as literals: `/home/pi/apertar-hardware.conf` (`src/DisplayConfigBridge.cpp:22`, `src/GyroConfigBridge.cpp:195`, `src/Ina219Bridge.cpp:50`, `src/WifiBridge.cpp:23`, `src/CfeAutomounter.cpp:119`), `/home/pi/LUTs`, `/home/pi/Tuning-Files` (`src/SettingsBridge.cpp:143`, `:167`), `/media/RAW` (`src/cliplistmodel.cpp:174`, `src/CfeAutomounter.cpp:109`, `src/MediaStatusBridge.cpp:762`, `src/SettingsBridge.cpp:148`, `:172`).
- Override by an `APERTAR_*` environment variable read next to the literal: `APERTAR_HARDWARE_CONFIG` (6 uses), `APERTAR_CONTROL_SOCKET` (4), `APERTAR_MEDIA_ROOT` (2), `APERTAR_PREVIEW_FORCE_*`, `APERTAR_MONITOR_ONLY` ... (20 distinct names, grep `APERTAR_[A-Z_]*` in `src/*.cpp`).
- Hardware config search order: env, `/home/pi/...`, `/boot/firmware/...`, `/boot/...` (`src/DisplayConfigBridge.cpp:25-38`).
- Media search also scans every `/media/*/<Folder>` (`src/SettingsBridge.cpp:150-153`).

## 9. Errors and logging

| Pattern | Evidence |
| --- | --- |
| Bridges report operator-facing failures through `lastError` / status properties, not logs. `ApertarControlBridge.cpp` has **zero** `qWarning`/`qDebug` (grep count 0) | `src/ApertarControlBridge.cpp:1037-1105`; QML shows it: `qml/CameraPage.qml:1415`, `:1497`, `:1596-1597` |
| Error text is a full English sentence with a period | `src/ApertarControlBridge.cpp:259`, `:438`, `:626`, `:1040` |
| Core error strings are passed through unchanged | `src/ApertarControlBridge.cpp:1084` |
| Logging is sparse and mostly on render/display paths: `qWarning` in 10 files, 15 in `PreviewWindowRenderer.cpp`; prefix `"Apertar <subsystem>: ..."` | `src/PreviewWindowRenderer.cpp` (grep), `src/main.cpp:171`, `:417-419` |
| `qInfo().noquote()` with `QStringLiteral(...).arg()` for one-line startup/config facts | `src/main.cpp:280-288` |
| Standalone helpers use `std::cerr` (no Qt) | `src/CfeAutomounter.cpp` (23), `src/StandbyUsbPower.cpp` (6), `src/StandbyLowPower.cpp` (5) |
| No exceptions in bridges; `bool` returns + early `return false` | `src/ApertarControlBridge.cpp:255-850` |

## 10. Threading

- Bridges live on the GUI thread. Blocking work is done in place with short bounded timeouts: `sendCoreCommand`
  (§3.2), `QProcess::waitForFinished(1500|2000)` (`src/MediaStatusBridge.cpp:498-560`, `src/AudioDeviceBridge.cpp:40-49`,
  `src/AudioMixerBridge.cpp:171-181`), `QThread::msleep(250)` (`src/SystemActionBridge.cpp:211`).
- Worker threads only where image work is heavy: `QThreadPool` in `cdngimageprovider` and `playbackcontroller`
  (`src/cdngimageprovider.h:48`, `src/playbackcontroller.h:146`), one detached `std::thread` for LUT load
  (`src/PreviewWindowRenderer.cpp:582`), results returned with `QMetaObject::invokeMethod(..., Qt::QueuedConnection)`
  (`src/playbackcontroller.cpp:1250-1261`, `src/DisplayCalibration.cpp:192-194`).
- Async is chosen when a comment justifies it (`src/ApertarControlBridge.cpp:861-862`).

## 11. Idiom notes

- `QStringLiteral("...")` for almost all literals in older code; newer code uses bare `"..."` (`src/SettingsBridge.cpp:324-407`, `src/ApertarControlBridge.cpp:1118-1164`). Both occur.
- Braces: single-statement `if` without braces; compact one-line `if (x) return;` in newer code (`src/ApertarControlBridge.cpp:2293-2305`).
- Mixed tab/space indentation in `resources.qrc` and in the config template stream (`src/DisplayConfigBridge.cpp:~70`).
- Comments are rare, one or two lines, and explain **why** (cold boot, GUI thread, race): `CMakeLists.txt:132-133`, `:169-171`, `:244-246`; `src/SettingsBridge.cpp:425-426`, `:471-472`; `src/ApertarControlBridge.cpp:263-266`, `:861-862`, `:886`; `src/main.cpp:174`.
- Giant files are normal: `ApertarControlBridge.cpp` 2460, `SettingsBridge.cpp` 2314, `PreviewWindowRenderer.cpp` 2466, `GyroConfigBridge.cpp` 1746 lines.
- No unit tests in UI (no test target in `CMakeLists.txt`).
- C++17 (`CMakeLists.txt:4`); Core is C++20.

---

## Rules

| ID | Kind | Strength | Rule |
| --- | --- | --- | --- |
| UI-S1 | STRUCTURE | always | New QML-visible C++ object = stack object in `main()`, exposed with `setContextProperty("<concern>Bridge")`, wired with setter injection in `main()`. No singletons, no `qmlRegisterType` (sole exception: `CameraPreviewItem`, a visual item) |
| UI-S2 | STRUCTURE | always | One concern per `<Concern>Bridge.{hpp,cpp}` pair, both listed in `add_executable(ApertarUI ...)` |
| UI-S3 | STRUCTURE | always | Everything that talks to Core's control socket goes through `ApertarControlBridge::sendCoreCommand`; other bridges never open `/tmp/apertar-core.sock` |
| UI-S4 | STRUCTURE | always | Core state reaches QML only via `applyCoreState` -> private `setXValue` -> `NOTIFY` |
| UI-S5 | STRUCTURE | usually | UI preferences live in `SettingsBridge` as `READ/WRITE/NOTIFY` properties backed by UI.conf; exceptions: `ApertarControlBridge` writes `timecodeMode` and `camera/*`, `WifiBridge` opens UI.conf too |
| UI-S6 | STRUCTURE | usually | Board/sensor capability comes from Core (`recording_capabilities`), not from a Pi model probe; one exception: Pi 3 preview path in `PreviewWindowRenderer` |
| UI-S7 | STRUCTURE | always | Privileged work is a separate small helper binary from this repo, fixed subcommands, sudoers whitelist, installed by hand to `/usr/local/libexec`; no `install()` rule |
| UI-I1 | IDIOM | always | Invokables return `bool`; failure sets `lastError` with a full sentence and returns `false` early |
| UI-I2 | IDIOM | usually | Command invokables are named `apply<Thing>(displayValue)`; exceptions: `setRecording`, `setTimelapseActive`, `capturePhoto`, `calibrateGyro`, `enterStandby`, `wakeFromStandby` |
| UI-I3 | IDIOM | always | Properties carry display strings; the bridge owns `parse*Value`/`format*Value` pairs |
| UI-I4 | IDIOM | usually | Command args are flat scalars; booleans as `"true"`/`"false"` strings |
| UI-I5 | IDIOM | always | UI.conf key = property name in camelCase; default inline in the constructor `value(key, default)` |
| UI-I6 | IDIOM | usually | Logging: sparse `qInfo/qWarning` with `"Apertar <subsystem>: "` prefix; helpers use `std::cerr`; bridges do not log command failures |
| UI-I7 | IDIOM | always | Paths: hard-coded Pi literal plus an `APERTAR_*` env override |
| UI-I8 | IDIOM | usually | Lists and file-search helpers are copied, not shared |
| UI-N1 | INTENT | always | The GUI thread may block on Core, bounded by per-command timeouts; long camera ops get a longer timeout, status polling goes async |
| UI-N2 | INTENT | always | Core owns camera truth; UI caches are placeholders |
| UI-N3 | INTENT | usually | Board limits are enforced in Core and repeated in the UI as an operator message |
| UI-N4 | INTENT | always | Cold-start time matters: dependencies kept out of startup |
| UI-N5 | INTENT | always | UI.conf is shared and live (Core/WebUI/HDMI process edit it); every key must be re-read in `pollExternalSettings` |

---

## Recipes

### R1. Expose a new Core state field to QML

1. Core: make sure `get_state`/the relevant event carries a flat snake_case key (C4/C1 topics).
2. `src/ApertarControlBridge.hpp:16-58`: add `Q_PROPERTY(QString fooBar READ fooBar NOTIFY fooBarChanged)`.
3. `src/ApertarControlBridge.hpp:63-108`: getter (inline if trivial); `:145-192`: signal `fooBarChanged()`; `:245-268`: `void setFooBarValue(const QString &)`; `:270-325`: `QString m_fooBar = QStringLiteral("<display default>");`.
4. `src/ApertarControlBridge.cpp:1646-1760`: `formatFooBarValue()` (and `parseFooBarValue()` at `:1761-2216` if QML sends it back).
5. `src/ApertarControlBridge.cpp:2230-2460`: setter in the compare/assign/emit form.
6. `src/ApertarControlBridge.cpp:1261-1555` (`applyCoreState`): `if (state.contains("foo_bar")) setFooBarValue(formatFooBarValue(...));`.
7. Optional cache: `loadPersistedCameraSettings` `:884-971` and `saveCurrentCameraSettings` `:973-1011` under `camera/fooBar`; presets `:1118-1150`.
8. QML: read `controlBridge.fooBar`; for CameraPage add a local mirror and a `function onFooBarChanged()` in `Connections { target: root.controlBridge }` (`qml/CameraPage.qml:1824-1897`, `syncControlValuesFromBridge` `:1555`).

### R2. Add an invokable that sends a command

1. Core: add the `if (command.name == "set_foo")` branch first.
2. `src/ApertarControlBridge.hpp:110-141`: `Q_INVOKABLE bool applyFoo(const QString &displayValue);`.
3. `src/ApertarControlBridge.cpp` next to its siblings (`:622-711`): parse -> invalid `setLastError("Invalid foo value."); return false;` -> optional capability gate -> `if (!sendCoreCommand(QStringLiteral("set_foo"), {{QStringLiteral("value"), v}})) return false;` -> `setFooValue(...)`, `saveCurrentCameraSettings()` -> `return true;`.
4. If the command reconfigures the camera, add its name to the reconfigure list (10 s) in `sendCoreCommand` `:1016-1028`.
5. QML: call `apertarControlBridge.applyFoo(value)`; on `false` show `controlBridge.lastError` (`qml/CameraPage.qml:1415`, `:1596`).

### R3. Add a UI.conf-backed setting

1. `src/SettingsBridge.hpp:18-88`: `Q_PROPERTY(bool fooEnabled READ fooEnabled WRITE setFooEnabled NOTIFY fooEnabledChanged)`.
2. `src/SettingsBridge.hpp:91-305`: getter/setter; `:306-381`: signal; `:404-492`: `bool m_fooEnabled = false;`.
3. `src/SettingsBridge.cpp:324-407` (constructor): `m_fooEnabled = m_settings.value("fooEnabled", false).toBool();` (normalize/clamp here).
4. `src/SettingsBridge.cpp:502-590` (`pollExternalSettings`): `setFooEnabled(m_settings.value(QStringLiteral("fooEnabled"), m_fooEnabled).toBool());`.
5. `src/SettingsBridge.cpp` getter/setter in the `setZebraEnabled` form (`:597-607`): guard with `m_externalSettingsSyncing`, `sync()`, `updateSettingsFileState()`, emit.
6. Presets: `serializeCurrentSettings` `:2030` and `applySettingsObject` `:2109`.
7. If Core needs it for a take, read it in `ApertarControlBridge::setRecording` `:781-801` and pass it as a `record_start` argument; if the WebUI shows it, Core's `sharedUiSettingsPath` reader (`Core:src/ApertarCoreApp.cpp:341`).
8. QML: a `Component` in `qml/SettingsPage.qml` (2385-6109), its id in the section's `default*Order` (`:771-838`) and in the `*ComponentForId` dispatch (`:2216-2384`).

---

## Challenge

Challenger pass against `/home/user/wt/ui-upstream` (tag `upstream-1.6.0`). All lines below are `@upstream-1.6.0`, all confirmed by reading code. Searches: `grep -n` over `src/*.cpp src/*.hpp src/*.h`, `CMakeLists.txt`, `systemd/`, and `core-upstream/src` for helper call sites.

### Verdict per rule

| Id | Verdict | Counter-example / reason |
| --- | --- | --- |
| UI-S1 | weaken to usually | Stack objects + `setContextProperty` + setter injection hold. But: `qmlRegisterType<CameraPreviewItem>("Apertar", 1, 0, "CameraPreviewItem")` at `src/main.cpp:274` (visual QQuickItem, not a bridge, so "no qmlRegisterType for bridges" still holds). Image providers are heap objects (`new CdngImageProvider` `src/main.cpp:351-353`, `new VideoImageProvider` `:357-358`) owned by the engine and also set as context properties `:393-395`. Context names do not always end in `Bridge`: `sleepManager` `:381`, `clipModel` `:391`, `playbackController` `:392`, `hdmiExternalOnly` (a bool) `:390`; `MediaStatusBridge` is exposed as `mediaBridge` `:382`, `Ina219Bridge` as `powerBridge` `:383`, `SettingsBridge` as `settingsBridge` while the C++ variable is `settings` `:389`. Not every bridge is QML-visible: `AudioMixerBridge audioMixerBridge` `:306` is constructed and injected `:328` but never exposed. There is a second construction site, `runMonitorOnly` `:131-154` (see missed rule UI-S8). |
| UI-S2 | weaken to usually | `src/DisplayCalibration.hpp:12,20,51` holds `struct DisplayCalibrationProfile`, `class DisplayCalibrationBridge`, `class DisplayCalibrationRenderer` (file name != class name, three types in one pair). Playback code uses lower-case `.h` files with different class names: `src/cliplistmodel.h:7` `ClipListModel`, `src/playbackcontroller.h:18` `PlaybackController`, `src/cdngimageprovider.h:13` `CdngImageProvider` (`CMakeLists.txt:109-121`). `src/VideoPlayback.hpp:22` holds `VideoImageProvider`. The `Bridge` suffix/one-concern rule holds for the `*Bridge.hpp` files. |
| UI-S3 | wrong | Two other bridges open the Core control socket themselves. `src/MediaStatusBridge.cpp:20-42` `coreMediaCommand()`: own `QLocalSocket`, `qEnvironmentVariable("APERTAR_CONTROL_SOCKET", "/tmp/apertar-core.sock")` `:23`, own `waitForConnected(1000)`, fixed id `42001`, own timeouts (eject 60 s `:1183`, format 360 s `:1192`). `src/AudioDeviceBridge.cpp:327-347`: async `QLocalSocket` for `audio_capabilities`, 4 s `QTimer::singleShot` timeout, reads a non-scalar reply field `modes` (array) `:337`. Replaced by UI-S3' below. |
| UI-S4 | weaken to usually | The `setXValue(formatXValue(...))` shape holds for display-string camera settings. Inline compare/assign/emit inside `applyCoreState` is equally common for bools, counters and objects: `preview_exposure_reference` (an object) `src/ApertarControlBridge.cpp:1263-1269`, `recording_has_dropped_frames` `:1270-1276`, `recording_capabilities` (an object) `:1285-1303`, `standby`/`state` `:1304-1312`, `iso_auto`/`shutter_auto` assigned without emit `:1321-1325`, `media_writes_pending` with revision guard `:1506-1513`, `still_exposure_active` emits without compare `:1514-1519`, photo keys fall back to `m_settings` (UI.conf) and emit one combined signal `:1527-1554`. Also Core state is not all flat: nested objects `preview_exposure_reference`, `recording_capabilities`, `capture` `:1313-1318`. |
| UI-S5 | holds (usually) | Exceptions to name: `ApertarControlBridge` owns its own `QSettings("CinePi","UI")` `src/ApertarControlBridge.cpp:118` and writes a `camera/*` cache group plus `timecodeMode` `:633,914,982-1002`; `WifiBridge` opens the same file `src/WifiBridge.cpp:127`. Other stores exist: `QSettings("CinePi","DisplayCalibration")` `src/DisplayCalibration.cpp:49`, `QSettings("Apertar","StandbyBacklights")` `src/SleepManager.cpp:56,84,123`. |
| UI-S6 | holds (usually) | Exceptions: `src/PreviewWindowRenderer.cpp:33-41` `runningOnRaspberryPi3()` reads `/proc/device-tree/model` to pick a render path; `src/DeviceInfoBridge.cpp:65` reads the model for display; `src/StandbyUsbPower.cpp:59-60` refuses on non-Pi-5. None of these gate a recording format; recording capability always comes from Core. |
| UI-S7 | weaken to usually | Only the two standby helpers match the full shape (sudoers file + `sudo -n` from Core `core-upstream/src/ApertarCoreApp.cpp:1544,1549`). `ApertarNetworkHelper` `CMakeLists.txt:157-159` is a Qt program (links `Qt6::Core`, reuses `WifiBridge.cpp`), no argv subcommands, logs with `qWarning`/`qInfo` `src/NetworkHelper.cpp:18,26,28`, runs as `User=pi` under `systemd/apertar-network.service`, not via sudo. `ApertarCfeAutomounter` has no sudoers file. The UI also does privileged work directly from bridges: `SystemActionBridge::runPrivileged` style `sudo -n <program>` `src/SystemActionBridge.cpp:614-619`; `MediaStatusBridge` runs `sudo` mount/mkdir `src/MediaStatusBridge.cpp:727,978,1015-1036,1057` and spawns an embedded Python script with `sudo -n` calls `:762-963` (`QProcess::startDetached("python3", {"-c", helperScript})` `:963`). |
| UI-I1 | weaken to usually | `bool` return + operator sentence holds for command invokables. The error surface is not always `lastError`: `MediaStatusBridge` uses `lastActionError` `src/MediaStatusBridge.hpp:18`; `SettingsBridge` presets use `presetStatus`/`presetStatusError` `src/SettingsBridge.hpp:92,299-303`; `AudioDeviceBridge` uses `m_capabilityError` and `void` selectors `src/AudioDeviceBridge.hpp:49-51,96`; `GyroConfigBridge` has `bool` invokables `src/GyroConfigBridge.hpp:69-83` and no `lastError`. `NetworkHelper` logs `WifiBridge::lastError` `src/NetworkHelper.cpp:25-27`. "Do not throw" holds outside the std-only helpers (`src/StandbyUsbPower.cpp:60,80` throw). |
| UI-I2 | holds (usually) | Exceptions on `ApertarControlBridge`: `setRecording` `src/ApertarControlBridge.hpp:139`, `setTimelapseActive` `:138`, `capturePhoto` `:140`, `calibrateGyro` `:141`, `enterStandby`/`wakeFromStandby` `:98-99`; some `apply*` take `double`/`bool` `:113,133,135-137`. |
| UI-I3 | holds (always for ApertarControlBridge) | No counter-example in `ApertarControlBridge`. Not a rule for other bridges (they hold native types). |
| UI-I4 | holds (usually) | `AudioDeviceBridge` sends `device` string `src/AudioDeviceBridge.cpp:330-331`; `MediaStatusBridge` sends `filesystem` string `:1192`. Both flat. No counter-example found for booleans sent as JSON bools from `ApertarControlBridge`. |
| UI-I5 | holds (always) | Constructor keys `src/SettingsBridge.cpp:324-407` all equal camelCase property names (67 keys checked by script); 67 `m_settings.setValue` and 67 `if (!m_externalSettingsSyncing)` in `SettingsBridge.cpp`. Note: the `*Order` setters write without `sync()`/`updateSettingsFileState()` (`:1576-1581,1595`); the guard part holds. |
| UI-I6 | holds (usually) | `qWarning/qInfo` count by file: PreviewWindowRenderer 23, main 12, others 1-4, `ApertarControlBridge` 0, `SettingsBridge` 0, `MediaStatusBridge` 0. Exceptions: `WifiBridge` logs config facts `src/WifiBridge.cpp:30,33`; `NetworkHelper` is Qt and logs with `qWarning` (not `std::cerr`). |
| UI-I7 | weaken to usually | App-owned paths get an override (`APERTAR_CONTROL_SOCKET`, `APERTAR_MONITOR_RUNTIME_SOCKET` `src/ExternalMonitorRuntimeBridge.cpp:16-19`, `APERTAR_HARDWARE_CONFIG`, `APERTAR_MEDIA_ROOT`, `APERTAR_BACKLIGHT_DIR` `src/SleepManager.cpp:102`, `APERTAR_PANEL_LED_PATH` `:31`). No override for: kernel paths `/sys/class/thermal/thermal_zone0/temp` `src/SystemStatsBridge.cpp:68`, `/sys/class/rtc` `src/SystemActionBridge.cpp:225`, `/sys/class/input` `src/PowerButtonBridge.cpp:128`; `/run/apertar-cfe/ready` `src/MediaStatusBridge.cpp:747`; `MOUNT_PATH = "/media/RAW"` in the embedded script `:762`; `/home/pi/LUTs`, `/home/pi/Tuning-Files` `src/SettingsBridge.cpp:143,167` (only the media root is overridable). Env access mixes `qEnvironmentVariable` and `qgetenv` (`src/SettingsBridge.cpp:145`, `src/PreviewWindowRenderer.cpp:45`). |
| UI-I8 | holds (usually) | Additional copies found: `coreMediaCommand` duplicates the socket client (`src/MediaStatusBridge.cpp:20-42`); hardware.conf candidate search is also inside the Python string `src/MediaStatusBridge.cpp:777`, and in `src/WifiBridge.cpp:23`. |
| UI-N1 | holds (always), list incomplete | GUI-thread blocking also in `MediaStatusBridge`: `eject_media` 60 s `src/MediaStatusBridge.cpp:1183`, `format_media` 360 s `:1192`, default 5 s `:20`, connect 1 s `:24`. No `QtConcurrent`/worker thread for commands (grep: only `std::thread` in `PreviewWindowRenderer.cpp:582` for LUT loading, `QThreadPool` in `cdngimageprovider.cpp`). |
| UI-N2 | holds (always) | Weak spot only: photo state falls back to UI.conf when Core omits the key `src/ApertarControlBridge.cpp:1531-1548`; Core still wins when present. |
| UI-N3 | holds (usually) | As written. |
| UI-N4 | holds (always) | Intent holds; note `TIFF::TIFF` and `Qt6::DBus` are linked directly `CMakeLists.txt:216-228`, so "heavy" means FFmpeg and libproxy, not every library. |
| UI-N5 | weaken to usually | `pollExternalSettings` `src/SettingsBridge.cpp:502-590` re-reads every key except the seven section order keys `monitoringOrder recordOrder audioOrder powerOrder systemOrder wifiOrder infoOrder sidebarOrder` (constructor `:399-406`); only `favoritesOrder` is polled `:576`. Found by diffing constructor keys against poll keys. |

### Missed rules

| Id | Kind | Strength | Rule | Evidence |
| --- | --- | --- | --- | --- |
| UI-S3' | structure | usually | Send camera/control commands through `ApertarControlBridge::sendCoreCommand`; a bridge with its own long-running Core operation (media, audio probe) may keep a small private socket client in its own `.cpp`, same JSON-line protocol (`cmd`, `id`, newline). | `src/ApertarControlBridge.cpp:1013-1106`; `src/MediaStatusBridge.cpp:20-42`; `src/AudioDeviceBridge.cpp:327-347` |
| UI-S8 | structure | once (only one second entry point) | The HDMI monitor is a second process with its own `main` path `runMonitorOnly`, its own bridge set and its own `QQmlApplicationEngine` loading `ExternalMonitorWindow.qml`; every context property that shared QML touches must exist there too, as a real object or an explicit `nullptr` placeholder. | `src/main.cpp:131-154` (`audioMeterBridge` set to `nullptr` `:153-154`, `mediaBridge` = `monitorRuntimeBridge` `:150`); `src/main.cpp:307-308` Publisher vs `:141-142` Subscriber |
| UI-S9 | structure | usually | Read `apertar-hardware.conf` sections in the bridge that owns the hardware, read-only, with `QSettings(path, QSettings::IniFormat)`; UI-local private state uses its own `QSettings(org, app)` store, not UI.conf. | `src/DisplayConfigBridge.cpp:595`, `src/Ina219Bridge.cpp:505`, `src/WifiBridge.cpp:24`; `src/DisplayCalibration.cpp:49`, `src/SleepManager.cpp:56` |
| UI-S10 | structure | usually | Cache Core camera values in UI.conf under the `camera/` group, written only by `ApertarControlBridge::saveCurrentCameraSettings`, as placeholders until Core answers. | `src/ApertarControlBridge.cpp:982-1002`, `:914`, `:886` |
| UI-I9 | idiom | usually | Write error strings as operator instructions: what failed and what to do next. | `src/MediaStatusBridge.cpp:25` "Connect to Apertar Core before changing media."; `:40` "Core did not confirm the media operation. Check its status before retrying."; `src/AudioDeviceBridge.cpp:345` "Audio capability check timed out. Stop recording and retry."; `src/SystemActionBridge.cpp:578` |
| UI-I10 | idiom | once | Small privileged shell/Python logic may be embedded as a raw string in the bridge and run with `python3 -c` (rough edge; do not copy for new work, do not "fix" unasked). | `src/MediaStatusBridge.cpp:762-963` |

---

## Final rules

| Id | Kind | Strength | Rule | Evidence (@upstream-1.6.0) | A violation looks like |
| --- | --- | --- | --- | --- | --- |
| UI-S1 | structure | usually | Construct QML-facing C++ objects on the stack in `main()`, wire them with setter injection and `QObject::connect` there, expose them with `engine.rootContext()->setContextProperty`; use `qmlRegisterType` only for visual QQuickItems; no singletons. | `src/main.cpp:291-311`, `:316-345`, `:374-396`, `:274` | A bridge as a singleton, `qmlRegisterSingletonType`, `QML_ELEMENT` bridge, or a bridge created inside another bridge |
| UI-S2 | structure | usually | One concern per `<Concern>Bridge.hpp/.cpp` pair (class = file name), both listed in `add_executable(ApertarUI ...)`. Exceptions: `DisplayCalibration.hpp`, playback `.h` files. | `CMakeLists.txt:63-125`; `src/WifiBridge.hpp:10`; `src/DisplayCalibration.hpp:20,51` | A new concern added into an existing bridge, or a file missing from `add_executable` |
| UI-S3' | structure | usually | Camera/control commands go through `ApertarControlBridge::sendCoreCommand(name, flat args, &reply)`; a separate bridge may own a small private socket client for its own long Core operations, same JSON-line protocol and `APERTAR_CONTROL_SOCKET` override. | `src/ApertarControlBridge.cpp:1013-1106`; `src/MediaStatusBridge.cpp:20-42`; `src/AudioDeviceBridge.cpp:327-347` | A generic shared Core client class or a new IPC channel; camera commands sent from another bridge |
| UI-S4 | structure | usually | Bring Core state into QML in `applyCoreState`: display-string settings as `if (state.contains("snake_key")) setXValue(formatXValue(...))`; bools/counters/objects by inline compare/assign/emit. | `src/ApertarControlBridge.cpp:1446-1450,1475-1476`, `:1263-1312`, `:2230-2237` | State read in QML from a raw JSON blob, or a second state-parsing path outside `applyCoreState` |
| UI-S5 | structure | usually | Keep UI preferences and monitoring aids in `SettingsBridge` READ/WRITE/NOTIFY properties backed by UI.conf `QSettings("CinePi","UI")`. Exceptions: `ApertarControlBridge` `camera/*` cache and `timecodeMode`; `WifiBridge`. | `src/SettingsBridge.hpp:18-88`; `src/SettingsBridge.cpp:287`; `src/ApertarControlBridge.cpp:118,633` | A UI preference stored in a new file, in Core's camera_settings.conf, or in QML `Settings` |
| UI-S6 | structure | usually | Take board/sensor recording capability from Core's `recording_capabilities`; local `/proc/device-tree/model` reads are only for render path, display info and helper safety checks. | `src/ApertarControlBridge.cpp:1285-1303,432-441`; `src/PreviewWindowRenderer.cpp:33-41`; README.md:324 | UI C++ probing the Pi model to enable/disable a recording format |
| UI-S7 | structure | usually | Root-only actions: a small helper target in this repo (`Apertar<Name>`, `OUTPUT_NAME apertar-<name>`, fixed argv subcommands, state in `/run/apertar-<name>`) plus a sudoers file naming exact arguments, called by Core with `sudo -n`; or `sudo -n <tool>` from a bridge with a clear error when the rule is missing. Daemons run as systemd services. | `CMakeLists.txt:149-167`; `systemd/apertar-standby-usb.sudoers:1`; `core-upstream/src/ApertarCoreApp.cpp:1544,1549`; `src/SystemActionBridge.cpp:614-622`; `systemd/apertar-network.service` | A setuid binary, a broad `NOPASSWD: ALL` rule, sudo with a password prompt, or privileged code added to the UI process without `-n` |
| UI-S8 | structure | once (only place) | The HDMI monitor process (`runMonitorOnly`) builds its own bridge set; every context property shared QML uses must be provided there too, real or `nullptr`. | `src/main.cpp:131-154`, `:307-308` | QML used on the HDMI path referencing a new context property only exposed in `main()`, giving ReferenceErrors on the monitor |
| UI-S9 | structure | usually | Each hardware bridge reads its own `apertar-hardware.conf` section read-only via `QSettings(path, IniFormat)`; UI-private state gets its own `QSettings(org, app)` store. | `src/DisplayConfigBridge.cpp:595`; `src/Ina219Bridge.cpp:505`; `src/WifiBridge.cpp:24`; `src/DisplayCalibration.cpp:49`; `src/SleepManager.cpp:56` | A central hardware-config parser class, or UI writing apertar-hardware.conf |
| UI-S10 | structure | usually | Cache Core camera values only under UI.conf `camera/*` via `saveCurrentCameraSettings`, as placeholders. | `src/ApertarControlBridge.cpp:886,914,982-1002` | Camera values cached under new top-level UI.conf keys or treated as authoritative |
| UI-I1 | idiom | usually | Command invokables return `bool`; on failure set an error property to a full English sentence and return `false` early; no throw, no logging. The property is usually `lastError`. | `src/ApertarControlBridge.cpp:257-261,624-628`; `src/SystemActionBridge.hpp:10`; `src/MediaStatusBridge.hpp:18` | `void` command invokables, exceptions, `qWarning` instead of a user message, error codes instead of sentences |
| UI-I2 | idiom | usually | Name `ApertarControlBridge` command invokables `apply<Thing>(const QString &displayValue)`; action verbs (`setRecording`, `capturePhoto`, `calibrateGyro`) for actions. | `src/ApertarControlBridge.hpp:111-141`; `src/SystemActionBridge.hpp:25-27` | `setFoo`/`changeFoo`/`updateFoo` for a camera setting |
| UI-I3 | idiom | always (ApertarControlBridge) | Expose camera settings to QML as display strings; keep `parse*Value`/`format*Value` pairs in `ApertarControlBridge`. | `src/ApertarControlBridge.hpp:211-243,278-298`; `src/ApertarControlBridge.cpp:1711-1716` | QML formatting raw Core numbers, or Core values exposed as raw ints |
| UI-I4 | idiom | usually | Send flat scalar arguments; booleans as `"true"`/`"false"` strings from `ApertarControlBridge`. | `src/ApertarControlBridge.cpp:727,739,746,791-794` | Nested JSON objects/arrays in a command |
| UI-I5 | idiom | always | UI.conf key = camelCase property name; default inline in the constructor read; setter writes under `if (!m_externalSettingsSyncing)`. | `src/SettingsBridge.cpp:324-407`, `:597-607`, `:1145-1155`; 67/67 guarded writes | snake_case or grouped keys, defaults in a separate table, unguarded writes |
| UI-I6 | idiom | usually | Sparse logging, `qInfo().noquote()`/`qWarning()` with `"Apertar <subsystem>: "` prefix for startup/display/render facts; command bridges do not log failures; std-only helpers use `std::cerr`. | `src/main.cpp:280-288`; `src/PreviewWindowRenderer.cpp` (23); `ApertarControlBridge.cpp` 0; `src/CfeAutomounter.cpp:249` | `qDebug` chatter per command, a logging framework, log categories |
| UI-I7 | idiom | usually | Write app-owned Pi paths as literals with an `APERTAR_*` env override next to them; kernel `/sys` paths are plain literals. | `src/ApertarControlBridge.cpp:1032`; `src/DisplayConfigBridge.cpp:20-38`; `src/ExternalMonitorRuntimeBridge.cpp:16-19`; `src/SystemStatsBridge.cpp:68` | Paths from a central config class, or a new app socket/file path with no env override |
| UI-I8 | idiom | usually | Copy small lists and file-search helpers where needed; QML holds option lists, the bridge mirrors only what it snaps/parses. | `src/ApertarControlBridge.cpp:92-105`; `hardwareConfigCandidatePaths` in `DisplayConfigBridge.cpp:25-38`, `GyroConfigBridge.cpp:198-211`, `Ina219Bridge.cpp:53-66`; `src/MediaStatusBridge.cpp:20-42` | An unasked shared utility library refactor across bridges |
| UI-I9 | idiom | usually | Error strings tell the operator what failed and what to do next. | `src/MediaStatusBridge.cpp:25,40`; `src/AudioDeviceBridge.cpp:345`; `src/SystemActionBridge.cpp:578` | "Error 3", "Failed", raw errno text alone |
| UI-I10 | idiom | once | Embedded Python helper in a C++ raw string run by `python3 -c` (rough edge, not a pattern to extend). | `src/MediaStatusBridge.cpp:762-963` | n/a; copying it for new work, or removing it unasked |
| UI-N1 | intent | always | The GUI thread blocks on Core commands, bounded per command (350 ms connect, 3 s default, 10 s reconfigure list, 8 s gyro, 60 s record_stop; media: 1 s connect, 5 s default, 60 s eject, 360 s format); only status polling is async. | `src/ApertarControlBridge.cpp:1015-1031,1063-1098,861-862`; `src/MediaStatusBridge.cpp:20-24,1183,1192` | Worker threads/futures for commands, or an unbounded wait |
| UI-N2 | intent | always | Core owns camera truth; UI caches are placeholders overwritten by Core state. | `src/ApertarControlBridge.cpp:886,1256-1258,1159-1161` | UI deciding a camera value and not reconciling with Core's reply |
| UI-N3 | intent | usually | Enforce board/sensor limits in Core and repeat them in the UI as an operator message before sending. | README.md:324; `src/ApertarControlBridge.cpp:432-441,496-499,518-521` | Limit only in UI, or only in Core with a silent UI failure |
| UI-N4 | intent | always | Keep FFmpeg and libproxy off the UI cold-start path (lazy module, stub, `-z,lazy`, AOT QML). | `CMakeLists.txt:127-147,169-182,244-249` | Linking FFmpeg or another large stack directly into `ApertarUI` |
| UI-N5 | intent | usually | UI.conf is shared live state (Core/WebUI/HDMI edit it): re-read each key in `pollExternalSettings` and include it in presets. Exception: section `*Order` keys except `favoritesOrder`. | `src/SettingsBridge.cpp:411-432,502-590,471-472,2030`; `:399-406` vs `:576` | A new UI.conf key read only at construction, so WebUI changes never reach the panel |
