# Architecture pages

Source-derived pages with `path:line` refs against `upstream-1.6.0`. Re-check refs after an upstream merge.

| Page | Covers | Start here when |
| --- | --- | --- |
| [overview.md](overview.md) | Processes, who owns what, socket/WebUI/file channels, startup order and readiness files, "who owns this bug" | You don't know which process is at fault |
| [core.md](core.md) | Apertar-Core: camera controller, recorders, control protocol, WebUI, hardware inputs, standby | Recording, sensor, format, socket command or WebUI behaviour |
| [ui.md](ui.md) | Apertar-UI: source map, `main.cpp` startup, QML bridges, Core client, preview path, QML pages, `run_pi_direct.sh`, helper binaries, "where to change X" | Screen, touch, HDMI, layout, settings page, preview rendering |
| [config.md](config.md) | `apertar-hardware.conf` keys, `UI.conf`, who reads which section | A key does nothing, or two processes disagree |
| [build.md](build.md) | CMake targets, outputs, plugin search paths, rebuild/restart per component, runtime mirror | Rebuilding, a change "did nothing", a missing `.so` |
| [drivers.md](drivers.md) | imx585 driver, overlays, sensor modes, tuning files | Modes, bit depth, link frequency, dtoverlay |

## Where to look for X

| Symptom / area | First file | Page |
| --- | --- | --- |
| Which process does X | — | [overview.md](overview.md#processes) |
| Boot order, Core waits for UI, Plymouth stays up | `Apertar-UI/src/main.cpp:405-499`, `Apertar-UI/wait_for_ui_core_start.sh`, `Apertar-UI/finish_plymouth_handoff.sh` | [overview.md](overview.md#startup-order-and-readiness-files) |
| Touch UI on the wrong screen, HDMI/DPI choice | `Apertar-UI/run_pi_direct.sh:83-186`, `Apertar-UI/src/main.cpp:90-119` | [ui.md](ui.md#run_pi_directsh) |
| UI size or layout wrong for the display | `[display]` in `apertar-hardware.conf`; `Apertar-UI/src/DisplayConfigBridge.cpp:478-652` | [ui.md](ui.md#where-to-change-x), [config.md](config.md) |
| HDMI monitor window | `Apertar-UI/src/ExternalMonitorManager.cpp`, `Apertar-UI/qml/ExternalMonitorWindow.qml`, `main.cpp:131-237` | [ui.md](ui.md#external-monitor-hdmi) |
| A touch control sends the wrong value | `Apertar-UI/src/ApertarControlBridge.cpp` (`apply*`) | [ui.md](ui.md#apertarcontrolbridge-invokable--core-command) |
| A Core value not shown / stale in the UI | `ApertarControlBridge.cpp:1182-1555` (`applyCoreMessage`, `applyCoreState`) | [ui.md](ui.md#how-a-core-state-field-becomes-a-qml-property) |
| What a socket command does in Core | `Apertar-Core/src/ApertarCoreApp.cpp` (`handleRequest`, `:7055`) | [core.md](core.md) |
| Socket protocol, events, broadcast | `Apertar-Core/src/ipc/ControlServer.cpp`, `ControlProtocol.cpp` | [ui.md](ui.md#wire-format), [core.md](core.md) |
| Preview black, slow or wrong colours | `Apertar-UI/src/ApertarPreviewSocketClient.cpp`, `PreviewWindowRenderer.cpp`; Core `publishPreviewFrame` | [ui.md](ui.md#preview-frame-delivery) |
| Zebra, peaking, false colour, LUT preview | `Apertar-UI/src/PreviewWindowRenderer.cpp:678-1220`, `CameraPreviewItem.hpp` | [ui.md](ui.md) |
| WebUI change not reflected on the touch screen | `~/.config/CinePi/UI.conf`; `Apertar-UI/src/SettingsBridge.cpp:411-431` | [ui.md](ui.md#ui-settings-that-core-also-changes-uiconf) |
| Recording, dropped frames, file formats | `Apertar-Core/src/camera/CameraController.cpp`, recorders | [core.md](core.md) |
| Sensor modes, overlays, link frequency | `imx585-v4l2-driver/` | [drivers.md](drivers.md) |
| What key K in `apertar-hardware.conf` does | `DisplayConfigBridge.cpp`, `CfeAutomounter.cpp`, `ApertarCoreApp.cpp` loaders | [config.md](config.md) |
| I2C device not found (encoder, hat, INA219, IMU) | `[<section>] bus=`; `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md` | [config.md](config.md) |
| CFexpress mount, eject button, LED | `Apertar-UI/src/CfeAutomounter.cpp` (runs from `/usr/local/libexec`) | [ui.md](ui.md#apertar-cfe-automounter) |
| Media eject/format/speed test from the UI | `Apertar-UI/src/MediaStatusBridge.cpp:1180-1215` → Core | [ui.md](ui.md), [core.md](core.md) |
| Wi-Fi, hotspot fallback | `Apertar-UI/src/WifiBridge.cpp`, `NetworkHelper.cpp` | [ui.md](ui.md#network-helper-vs-in-ui-wi-fi) |
| Standby, USB/CPU power-down | Core `standbyUsbPower`/`standbyLowPower` (`ApertarCoreApp.cpp:1541-1550`); `Apertar-UI/src/Standby*.cpp` | [core.md](core.md), [ui.md](ui.md#separate-binaries-built-here) |
| Clip browser, playback | `Apertar-UI/src/cliplistmodel.cpp`, `playbackcontroller.cpp`, `VideoPlayback.cpp` | [ui.md](ui.md#source-map) |
| Rebuild and restart a component | — | [build.md](build.md#quick-reference) |
| A change "did nothing" | QML compiled in; runtime mirror; helper not copied to `/usr/local/libexec` | [build.md](build.md) |
