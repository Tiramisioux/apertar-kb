# Upstream issues (Apertar-Studio)

Rough edges found in Apertar-Studio's code or image. Each is a candidate GitHub issue or a small
PR from the fork. Status: `open` (only noted), `fixed-in-fork <sha>`, `reported <url>`.

| # | Area | Issue | Evidence | Status |
| --- | --- | --- | --- | --- |
| 1 | image | DPI overlays enabled by default; HDMI users silently lose GPIO 0-27 and `/dev/i2c-1` | hardware-log 2026-10-23 | open |
| 2 | core/ui | I2C bus defaults disagree between the three templates. The source note had it backwards: `[ina219] bus=4` everywhere; **Core's** WebUI template says `[pcf8574] bus=10` and `[imu] bus=10`, while both UI templates and all parsers default to bus 1 | `ApertarCoreApp.cpp:4346`, `:4363`; `DisplayConfigBridge.cpp:87`; `Ina219Bridge.cpp:106`; `Pcf8574Input.hpp:31`; `architecture/config.md` | open |
| 3 | core | `NeoRotary4Input::lastError()` has no readers; driver errors never reach the WebUI | §6.3 | open |
| 4 | ui | `run_pi_direct.sh` takes any `connected` DPI connector as the touch panel, even with no panel | §6.7 | open |
| 5 | repo | UI repo commits its whole `build/` tree (551 files, 18 MB binary) | fork commit `66d6d19` | fixed-in-fork 66d6d19 |
| 6 | repo | Web uploads drop executable bits and turn symlinks into copies | fork commits `ed400ba`, `29ed99b` | fixed-in-fork |
| 7 | repo | `src/prores/README.md` and `src/prores/ffmpeg/*` ship on the 1.6.0 image but are not in git; the Core README's ProRes FFmpeg recipe points at the missing dir | Pi `~/ApertarCore` untracked; `architecture/build.md` | open |
| 8 | repo | `qml/InlineChoice.qml` is in git but not on the image and not referenced by `qml.qrc` (dead file) | grep, 2026-10-25 | open |
| 9 | repo | Upstream rewrites history on release (`Apertar-Core` has one commit at 1.6.0) | `working/upstream-sync.md` | open (ask maintainer) |
| 10 | core | `APERTAR_TUNING_FILE` in `start-apertar-core.sh` is dead: Core sets/clears `LIBCAMERA_RPI_TUNING_FILE` itself on every camera open | `CameraController.cpp:1111-1121`, called `:5271`; `architecture/drivers.md` | open (desk) |
| 11 | core | IMX585 fps capped in code (4K 30, 1080p/crops 60) regardless of link frequency | `CameraController.cpp:2669-2677`; `architecture/drivers.md` | open (desk) |
| 12 | core/driver | IMX585 crop sizes (e.g. 3840x2076) are not modes in Apertar-Studio's published driver, yet Core requests them. **Explained:** the image's driver has an unpublished local edit adding exactly these 18 crop modes (now fork commit `e5b74d3`). Upstream issue = the published driver doesn't match the image | `architecture/drivers.md`; fork `apertar` `e5b74d3` | confirmed (source) |
| 13 | core/driver | Core offers 10-bit for IMX585, but the image's driver (`1644466` + `e5b74d3`) has no RAW10 4K mode (Apertar-Studio `main` `11178c8` does) | `architecture/drivers.md` | **unconfirmed** on Pi: `v4l2-ctl -d <imx585 subdev> --list-subdev-mbus-codes` |
| 14 | driver | `cam0` overlay override moves the always-on regulator fragment but not the 300 ms startup-delay fragment | `imx585-overlay.dts:36-41`, `:129-135` | open (desk) |
| 15 | ui/build | UI binary is named `Apertar-UI` only if `/usr/lib/qt6/libexec/moc` exists, else `ApertarUI`, and the service won't find it | `Apertar-UI/CMakeLists.txt:252-261` | open (desk) |
| 16 | core/build | `install()` puts plugins in `lib/apertar-core/`, but Core only looks beside its binary and in `/home/pi/ApertarCore-build` | `architecture/build.md` | open (desk) |
| 17 | core | Embedded CFE automount Python helper gives up silently after its 60 s wait | `ApertarCoreApp.cpp:3382-3590` | open (desk) |
| 18 | ui | Touch UI freezes during slow commands: `sendCoreCommand` blocks the GUI thread up to 60 s (`record_stop`), 10 s (reconfigure), 360 s (`format_media`) | `ApertarControlBridge.cpp:1013-1106`, `MediaStatusBridge.cpp:1192` | open (desk) |
| 19 | core/ui | Every client gets every event incl. per-frame `preview_frame`; the UI parses them on the GUI thread. Core drops clients whose buffer fills (`MSG_DONTWAIT`), so #18 may get the UI dropped (**probable**) | `ControlServer.cpp:23-29`, `:172-193`; `ApertarControlBridge.cpp:1572-1588` | open (desk) |
| 20 | core | Eject always starts Core's embedded Python reinsert watcher, even with `apertar-cfe-automounter` running; the UI's guarded copy is dead code | `ApertarCoreApp.cpp:3595`, `:3742`; `MediaStatusBridge.cpp:742-972` | open (desk) |
| 21 | ui | `hdmi_external_only=true` + `windowed=true` probably shows nothing | `main.cpp:428`, `:514-518`; `ExternalMonitorManager.cpp:162-166` | open (desk) |
| 22 | ui | Monitor-only process has no `gyroConfigBridge`, so no horizon level on HDMI in split-DRM mode | `main.cpp:147-154` | open (desk) |
| 23 | ui | Preview socket parser uses substring search for `"key":` and ignores `APERTAR_CONTROL_SOCKET` | `ApertarPreviewSocketClient.cpp:585-625`; `Main.qml:207` | open (desk) |
| 24 | ui | Focus peaking texel size hard-coded to 1/1920 x 1/1080; default threshold 0.08 vs 0.04 in two headers | `PreviewWindowRenderer.cpp:858`; `CameraPreviewItem.hpp:137`; `PreviewWindowRenderer.hpp:132` | open (desk) |
| 25 | qml | `standardLandscapeLayout` includes `landscape_large` in Main/CameraPage but not in SettingsPage | `Main.qml:43`, `CameraPage.qml:45`, `SettingsPage.qml:23` | open (desk) |
| 26 | ui | `DroppedFrameWarning.qml` missing from `qml.qrc`; six config-path lookups (WifiBridge lacks the `/boot` fallback); `/media/RAW` hard-coded despite `[storage] mount_path` | `architecture/ui.md` | open (desk) |
| 27 | ui | `SystemActionBridge::restartCamera()` reboots the whole Pi | `SystemActionBridge.cpp:274-277` | open (desk) |
| 28 | core | `help` command list omits commands the UI uses (`user_activity`, `audio_capabilities`, `enter_standby`, `wake`, …) | `ApertarCoreApp.cpp:9216` | open (desk) |
| 29 | image | `apertar-network-start-gate.conf` drop-in is in the repo but not installed on the image | `systemctl cat apertar-network` (Pi, 2026-10-25) | confirmed on Pi |
| 30 | image | User `pi` can't read the journal (not in `systemd-journal`) | Pi, 2026-10-25 | confirmed on Pi |
| 31 | ui | The UI creates `/home/pi/apertar-hardware.conf` from its own template on start if missing; `/boot/firmware` copies are never read after that | `DisplayConfigBridge.cpp:587` | open (desk) |
| 32 | core | Core's `[imu]` template keys (bus, address, sample_rate_hz, gyro_range_dps…) are read by nobody; `imu.enabled` false in Core's template, true in UI templates and code | `Mpu6050RecordingSession.cpp:939-955` | open (desk) |
| 33 | core | Choosing bmi160/bmi270/icm42688p leaves the IMU off: the driver section's `enabled=false` overrides `[imu]` | `Mpu6050RecordingSession.cpp:946` vs `:957` | open (desk) |
| 34 | config | Templates disagree with code on LED pin (`line` 17 / `pcf_pin` 7 vs -1/-1) and `trigger_output.open_drain`; trigger output and tally LED both default to GPIO17 | `architecture/config.md` | open (desk) |
| 35 | core | INA219 and Python-helper `bus=` values ignore the line if it has a trailing comment | `ApertarCoreApp.cpp:4406-4425`, `:3413-3422` | open (desk) |
| 36 | core | Command event collection is switched on before `commandMutex_` is taken, so two clients can wipe/steal each other's events; `record_start` with audio sleeps 220 ms under the lock | `ApertarCoreApp.cpp:7061` vs `:9093`; `:10692-10706` | open (desk) |
| 37 | web | WebUI has no auth; requests without an `Origin` header pass, so any LAN client can format media or rewrite `[run_script]` | `WebServer.cpp:156-170` | open (desk). Keep the camera on a trusted network |
| 38 | core | Hardware-input errors go only to stderr, never `get_state`/WebUI; config edits need a Core restart | `architecture/core.md` | open (desk) |
| 39 | core | No mount/free-space check before recording; ProRes repair never called; lossy DNG write errors only logged | `architecture/core.md` | open (desk) |

| 40 | core | `discarded_on_stop=` in the recording-stats log is always 0: `discardedOnStopFrames_` is reset (`CameraController.cpp:3304`) and read (`:3509`) but never incremented | grep, upstream-1.6.0; `llm/flows.md` A2 | open (desk) |
| 41 | web | WebUI preset import allow-list (`WebControlPage.cpp:10526-10606`) omits keys Core saves into presets (`cameraExposureCompensation`, `cameraControlsMode`, `photoFormat`, …; Core writes them at `ApertarCoreApp.cpp:6606-6665`), so a preset loaded from the WebUI silently drops them | `llm/core-map.md` §4 | open (desk) |
| 42 | core/web | Favourites id list exists 3 times (`ApertarCoreApp.cpp:727`, `WebControlPage.cpp:4091`, `Apertar-UI/qml/SettingsPage.qml:838`); Core silently drops WebUI ids such as `smpteBars`, `autofocus` (`ApertarCoreApp.cpp:10224`, `:1808`) | `llm/core-map.md` §4 | open (desk) |
| 43 | core | `publishEvent` (`ApertarCoreApp.cpp`, broadcast list) does not broadcast `"event":"recording"`: during a command it is folded into that command's reply, so a take started from the socket, WebUI or a hardware input reaches the touch UI only on its 30 s `get_state` poll; the tally LED (same event, inside Core) lights at once. Seen on the Pi 2026-10-26 | fork fix `086443c` (branch `cinemate-port`) |
| 44 | cdng | Every DNG write ends with `posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED)` right after the write, before `close()` (`src/cdng/CdngEncoder.cpp:1777`, `LossyDngEncoder.cpp:82` @ `upstream-1.6.0` `35dbe67`). The pages are still dirty then: the call frees nothing and drains the per-CPU LRU lists on every core per frame; the page cache fills and kswapd reclaims during the take (~13 GB per 3-minute 4K Clear HDR 16-bit take). With the touch UI running this costs 1-3 % of the frames at capture once the cache is full | hardware-log 2026-11-01 "page-cache pressure, not the UI alone" | fixed-in-fork adac040 (default `sync`: drop after the once-a-second fsync; knob from 0ed07ea); offer upstream |
| 45 | ui/web | Zebra means two things: the WebUI tests the brightest channel when the level is ≥ 95 % (`src/web/WebControlPage.cpp:8039-8043` @ `upstream-1.6.0`, `:13218-13222` @ fork `f4e97e5`), the HDMI/touch shader always tests Rec.601 luma (`Apertar-UI src/PreviewWindowRenderer.cpp:896` @ `upstream-1.6.0`, unchanged in the fork). A tinted blown highlight (16-bit Clear HDR clamp: about (255,233,255)) is striped in the browser and blinks or stays clean on HDMI | code, `working/clearhdr16-preview.md` §2 | open (desk) |

`open (desk)` = found by reading the code, not yet seen on the Pi. Each one could become a tutorial.
