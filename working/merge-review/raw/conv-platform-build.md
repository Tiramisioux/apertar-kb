# C7 Conventions: platform, build, install, scripts, supported hardware (upstream 1.6.0)

Scope: how the original developer builds, installs and targets hardware, measured only on
`/home/user/wt/core-upstream` (Core, `35dbe67`) and `/home/user/wt/ui-upstream` (UI, `43888e5`), both tag `upstream-1.6.0`.
All refs below are `@upstream-1.6.0` unless marked. `Core/` = core-upstream, `UI/` = ui-upstream.
KB pages `architecture/build.md` and `architecture/overview.md` were used as a map; every rule was re-read in code.

## 1. What the repos contain (non-source)

| Repo | Item | What | Ref |
| --- | --- | --- | --- |
| Core | `CMakeLists.txt` | 1 executable, 2 MODULE plugins, install rules | `Core/CMakeLists.txt:1-196` |
| Core | `scripts/start-apertar-core.sh` | Service start script, 3 env overrides | `Core/scripts/start-apertar-core.sh:1-21` |
| Core | `config/apertar-core-capture-priority.conf` | systemd drop-in `LimitNICE=-5` | `Core/config/apertar-core-capture-priority.conf:1-3` |
| Core | `.github/FUNDING.yml` | Ko-fi only. No CI workflows | `Core/.github/FUNDING.yml:5` |
| Core | `LICENSE` | GPL-2.0 | `Core/LICENSE:1-2` |
| UI | `CMakeLists.txt` | UI exe, movie plugin, 4 helper exes, proxy stub | `UI/CMakeLists.txt:1-261` |
| UI | `run_pi_direct.sh`, `sync_pi_runtime.sh`, `wait_for_ui_core_start.sh`, `finish_plymouth_handoff.sh` | Launch, runtime mirror, Core start gate, Plymouth handoff | repo root |
| UI | `systemd/` | 1 unit, 1 drop-in, 2 sudoers, 1 polkit rule, 1 udev rule | `UI/systemd/*` |
| UI | `mesa-minimal/` | Checked-in aarch64 Mesa 26.2.0 binaries + headers | `UI/mesa-minimal/lib/aarch64-linux-gnu/pkgconfig/gbm.pc:7` |
| UI | `third_party/liblj92/` | Vendored MIT decoder with notice | `UI/third_party/liblj92/README.apertar.md:1-11` |
| UI | `build/` | **Committed** build tree, 551 files, including the `build/Apertar-UI` binary and Makefiles | `git -C UI ls-files build \| wc -l` = 551 |
| UI | `.github/FUNDING.yml`, `LICENSE` | Same as Core, GPL-2.0 | `UI/LICENSE:1-2` |

No `.gitignore` in either repo (`ls -a`). Core history is one squashed commit (`35dbe67 1.6.0 Release`); UI has 10 commits, the last ones "Updated to version 1.6.0" and README edits. Releases are code drops.

Not in either repo (image-owned, known only from the live Pi, see `architecture/build.md:210-218`): `apertar-core.service`, `apertar-ui-direct.service`, `apertar-cfe-automounter.service`, `media-RAW.service`, the passwordless sudo rule for `pi`, `/usr/local/libexec/*` copies.

## 2. Supported hardware as claimed and as coded

### 2.1 Boards

| Board family | Clip formats (README) | Ref (README) | Code |
| --- | --- | --- | --- |
| Pi 5 / CM5-class | cDNG (uncompressed, lossless, lossy 3:1/5:1), MLV, H.264 (software), ProRes | `Core/README.md:64`, `UI/README.md:61` | `brcm,bcm2712` → `{rawCompression=true, prores=true}` `Core/include/apertar/core/RecordingCapabilities.hpp:25-26` |
| Pi 4 / Pi 400 / CM4-class | uncompressed cDNG, MLV, H.264 (hardware, max 1080p30) | `Core/README.md:65,70`, `UI/README.md:62,65` | `brcm,bcm2711` → `usb3=true`, `legacy=true` `:27-30`; result `{false,false,hardwareH264=true,rawRecording=true}` `:34` |
| Pi 3 / 3A+ / Zero 2 W, "USB 2.0-only" | H.264 only | `Core/README.md:66`, `UI/README.md:63` | `bcm2837/2836/2835` → `legacy`, no `usb3` → `rawRecording=false` `:29-34` |
| Anything else (no DT match) | not claimed | - | default `RecordingCapabilities{}` = all RAW, no compression, no ProRes, software H.264 `:11-16`, `:47` |

Detection: **device-tree `compatible` SoC string**, read from `/sys/firmware/devicetree/base/compatible`, then `/proc/device-tree/compatible`, parsed by a pure function, cached in a function-local `static`. Two independent copies of the same parse:

| Copy | Ref | Output |
| --- | --- | --- |
| Recording capabilities | `Core/include/apertar/core/RecordingCapabilities.hpp:18-50` | format gates |
| Tuning pipeline | `Core/src/camera/DefaultTuningSelection.hpp:18-50` | `Pipeline::PiSP` / `Vc4` / `Unknown` |

Second detection method, **`/proc/device-tree/model` string match**, used in the UI and for features that are not format gates:

| Where | Match | Effect | Ref |
| --- | --- | --- | --- |
| USB power-off helper | `find("Raspberry Pi 5 Model") != 0` → refuse | CM5 is refused (its model string is "Raspberry Pi Compute Module 5...") (**probable**, settle with `cat /proc/device-tree/model` on the CM5 rig) | `UI/src/StandbyUsbPower.cpp:59-60` |
| Preview renderer | `contains("raspberry pi 3")` | planar YUV texture path | `UI/src/PreviewWindowRenderer.cpp:33-41`, `:305` |
| Fan mode (touch UI) | `indexOf("raspberry pi 4") === -1` | fan setting hidden on Pi 4 only; shown on Pi 3, CM4, CM5 | `UI/qml/SettingsPage.qml:97`, `:1765-1766` |
| Fan mode (WebUI) | same string test | same | `Core/src/web/WebControlPage.cpp:4821`, `:7249` |
| Device info (display only) | model + serial | shown, not used for decisions | `Core/src/ApertarCoreApp.cpp:4939-4960`, `UI/src/DeviceInfoBridge.cpp:65-75` |

Places that handle two board families (complete list from the task grep, `icm42688` false positives removed):

| Place | Families | Ref |
| --- | --- | --- |
| Format gates and coercion | Pi 5 / Pi 4 / Pi 3 | `RecordingCapabilities.hpp:64-106` |
| Default tuning folder and JSON target | PiSP (`pisp`) / VC4 (`bcm2835`) | `DefaultTuningSelection.hpp:56-75`, `:105-123` |
| H.264 hardware encoder path | VC4 boards (`bcm2835-codec` V4L2 M2M) / Pi 5 software | `Core/src/camera/CameraController.cpp:3969-3989`; node probe `Core/src/video/H264Hardware.hpp:19`, `:37` |
| H.264 camera buffers | 4 on hardware-H.264 boards, 6 otherwise | `CameraController.cpp:1125-1129` |
| VC4 memory guard in YUV mode search | VC4 | `CameraController.cpp:6001-6004` |
| GPIO chip auto-pick | `rp1` +100, `pinctrl_bcm`/`bcm2711`/`bcm2835` +90, `raspberrypi_exp` -50 | `Core/src/hardware/GpioInput.cpp:238-262`; copies `TriggerOutput.cpp:201-225`, `RecordingIndicatorOutput.cpp:198-222` |
| PiSP compressed RAW packing | format-driven (`PISP_COMP1`), not board-driven | `CameraController.cpp:3075-3107`; `Core/src/lossydng/LossyDngEncoder.cpp:295`, `:434` |
| Preview texture path | Pi 3 planar / others EGL dma-buf | `PreviewWindowRenderer.cpp:296-305`, `:1511` |
| HDMI audio device filtering | `vc4` / `vc4-hdmi` names | `UI/src/AudioDeviceBridge.cpp:103`, `:149`; `UI/src/AudioMeterBridge.cpp:168-169` |
| Fan mode | not Pi 4 | above |
| USB power-off | Pi 5 only | above |

### 2.2 Assumptions about the Pi 5 / CM5 platform

| Assumption | Ref | Configurable? |
| --- | --- | --- |
| PCIe controller `1000110000.pcie` (Pi 5 RP1-side PCIe) for NVMe reset | `Core/src/ApertarCoreApp.cpp:3395`, `:3555-3560`; `UI/src/CfeAutomounter.cpp:110`, `:632-641`; `UI/src/MediaStatusBridge.cpp:763`, `:923-928` | yes, `[storage] pcie_controller` / `[cfexpress_hat] pcie_controller` (`ApertarCoreApp.cpp:3461-3463`, `CfeAutomounter.cpp:176-179`) |
| CFexpress hat on I2C bus 10, address 0x34 | `ApertarCoreApp.cpp:3391-3392`, template `:4305`; `CfeAutomounter.cpp:38` | yes, `[cfexpress_hat] bus` |
| Pi 5 USB host controllers `1f00200000.usb` / `1f00300000.usb`, exactly 4 hubs and 6 ports | `UI/src/StandbyUsbPower.cpp:69-80` | no; refuses otherwise ("Unexpected Pi 5 USB topology; keeping USB powered") |
| Fan via `dtparam=cooling_fan`/`fan_temp*` in `/boot/firmware/config.txt` | `ApertarCoreApp.cpp:2845`, `:3042-3160`; `UI/src/SystemActionBridge.cpp:25`, `:64-72`, `:419-478` | Pi 4 excluded by model string only |
| NVMe recognised by `/dev/nvme` prefix | `ApertarCoreApp.cpp:2009`, `:3720`; `MediaStatusBridge.cpp:76`, `:107` | - |
| CPU temperature `thermal_zone0` | `ApertarCoreApp.cpp:4718`; `UI/src/SystemStatsBridge.cpp:68` | - |
| `mesa-minimal` holds aarch64 VC4/V3D Mesa; `sync_pi_runtime.sh` copies `/usr/lib/aarch64-linux-gnu/qt6` | `UI/run_pi_direct.sh:41-71`; `UI/sync_pi_runtime.sh:36-37` | `APERTAR_MESA_RUNTIME_ROOT`; deleting dir falls back |
| ProRes performance tables measured on "Pi 5, 4x A76 @ 2.8 GHz, 4 frame threads" | `Core/src/prores/ProresEncoder.cpp:1607-1609` | ProRes is Pi 5-only anyway |

**Four cores.** No code hard-codes four cores. Every worker count derives from `std::thread::hardware_concurrency()` and is clamped:

| Ref | Formula |
| --- | --- |
| `CameraController.cpp:3323-3340` | cDNG workers `max(2, min(4, hw))`; lossless `min(8, hw+1)` when `hw >= 4`; queue 24 vs 12 by `hw >= 4` |
| `CameraController.cpp:4448-4451` | H.264 threads `1` if `cores <= 2` else `min(4, cores-1)` |
| `Core/src/prores/ProresEncoder.cpp:1321-1322` | CSC threads `max(1, min(2, hw))` |
| `ApertarCoreApp.cpp:7903` | label `"<hw> cores active"` |

Search: `grep -rn -i "affinity\|nproc\|sched_setscheduler\|SCHED_FIFO" Core/src UI/src` → no hits. Only bounded `nice` is used: camera callback thread `-5` (`CameraController.cpp:6590-6599`, enabled by `LimitNICE=-5`, `Core/config/apertar-core-capture-priority.conf:2-3` "bounded, non-real-time boost"), cDNG/lossy workers `+0/+5` (`CameraController.cpp:3700-3709`).

### 2.3 Sensors, displays, storage, accessories

| Kind | Claimed | Ref |
| --- | --- | --- |
| Sensors | IMX477, IMX577, IMX585, IMX294, plus mono RAW formats | `Core/README.md:76-83`; `UI/README.md:69` |
| Sensor driver / overlay / libcamera / tuning | **not installed by the build** | `Core/README.md:87` |
| Tuning | `/home/pi/Tuning-Files/defaults-pisp` (target `pisp`) or `defaults-vc4` (target `bcm2835`); custom from `/home/pi/Tuning-Files/` or `<media>/Tuning-Files` | `Core/README.md:136-145`; `DefaultTuningSelection.hpp:56-75` |
| Main display | Any connected DSI/DPI/LVDS/eDP connector, else HDMI; layouts 720x720 (default), 640x480, 800x480, 1024x600, 1280x720, 1920x1080 | `UI/run_pi_direct.sh:106-166`; template `ApertarCoreApp.cpp:4313-4329` |
| External monitor | HDMI; second process when on a different DRM card | `UI/run_pi_direct.sh:244-322`; `UI/README.md:122-128` |
| Panel power / backlight | sysfs backlight (udev grants `video` group write), `wittypi_led`, DPI panel timing from DT | `UI/systemd/90-apertar-backlight.rules:1-2`; `UI/src/SleepManager.cpp:31-46`, `:102` |
| Storage | `/media/RAW` (NVMe via CFexpress hat / PCIe, or USB); formats exFAT/FAT32/ext4/NTFS paths | `Core/README.md:263`; `ApertarCoreApp.cpp:3609-3640`, `:3810-3816` |
| IMU | MPU6050, BMI160, BMI270, ICM42688-P | `Core/README.md:112`; `Core/src/web/WebControlPage.cpp:4064` |
| Inputs | GPIO, PCF8574, NeoRotary4, Grove analog, standby power button | `Core/CMakeLists.txt:83-91`; template `ApertarCoreApp.cpp:4291-4400` |
| Outputs | trigger output (GPIO or PCF8574), recording LED | `ApertarCoreApp.cpp:4378-4400` |
| Battery | INA219, default bus 4, 0x40 | template `ApertarCoreApp.cpp:4297-4300` |
| Audio | any ALSA device, formats as exposed | `Core/README.md:106-108` |

## 3. Build

### 3.1 Targets and options

| Repo | Target | Kind | Notes | Ref |
| --- | --- | --- | --- | --- |
| Core | `apertar-core` | exe, C++20, no extensions, `-Wall -Wextra -Wpedantic` | 26 `.cpp` listed by hand | `Core/CMakeLists.txt:21-23`, `:69-96`, `:175-180` |
| Core | `apertar-h264-libav` | MODULE, `PREFIX ""` | only if libav found | `:140-150` |
| Core | `apertar-prores-libav` | MODULE, `PREFIX ""` | optional private FFmpeg prefix | `:152-169` |
| UI | `ApertarUI` → `Apertar-UI` | exe, C++17 | `.cpp` and `.hpp` listed; QML via `qt_add_qml_module` or `qml.qrc` | `UI/CMakeLists.txt:63-130`, `:184-200`, `:256-257` |
| UI | `apertar-video-libav` | MODULE, `PREFIX ""` | not linked to UI "FFmpeg must stay out of the cold-boot dependency graph" | `:132-147` |
| UI | `apertar-cfe-automounter`, `apertar-standby-usb`, `apertar-standby-low-power` | exe, no Qt, AUTOMOC OFF | root-side tools | `:149-155`, `:159-167` |
| UI | `apertar-network-helper` | exe, Qt Core only | | `:156-158` |
| UI | `libproxy.so.1` in `build/apertar-runtime/` | shared stub | keeps proxy discovery out of cold start | `:169-182` |

Options and switches:

| Option | Default | Ref |
| --- | --- | --- |
| `APERTARCORE_ENABLE_LIBCAMERA` | ON | `Core/CMakeLists.txt:17` |
| `APERTARCORE_ENABLE_LIBAV` | ON | `:18` |
| `APERTARCORE_PRORES_FFMPEG_PREFIX` | empty | `:19`, `:46-65` |
| `CMAKE_BUILD_TYPE` forced to Release if unset | - | `:9-15` |
| `-mtune=native` in Release when not cross-compiling | - | `:182-188` |
| `APERTAR_QML_AOT` | ON native, OFF cross | `UI/CMakeLists.txt:54-61` |
| `APERTAR_HAS_DISPLAY_POWER` (derived) | ON if `Qt6::GuiPrivate` headers exist | `:221-242` |
| `-z,lazy` link | GNU/Clang | `:244-249` |
| Host moc/rcc forced, and `OUTPUT_NAME "Apertar-UI"` only if `/usr/lib/qt6/libexec/moc` exists | - | `:251-261` |

### 3.2 Optional dependencies and how absence is handled

| Dependency | Found by | Absent → | Ref |
| --- | --- | --- | --- |
| yaml-0.1, ALSA, Threads | `REQUIRED` | configure fails | `Core/CMakeLists.txt:25-28` |
| TurboJPEG / JPEG | `find_path`/`find_library`, `find_package(JPEG QUIET)` | `APERTARCORE_HAS_TURBOJPEG=0`, `APERTARCORE_HAS_JPEG=0` | `:29-31`, `:120-131` |
| libcamera | `pkg_check_modules(... QUIET ...)` | `APERTARCORE_HAS_LIBCAMERA=0`, no message | `:37-41`, `:133-138` |
| libav (Core) | QUIET | `APERTARCORE_HAS_LIBAV=0`, `message(STATUS "... disabled")`, no plugins | `:43-45`, `:170-173` |
| Private ProRes FFmpeg | `REQUIRED` once the prefix is set | configure fails | `:62` |
| libav + swscale (UI) | QUIET | `message(STATUS "Video playback decoder disabled: install libavcodec-dev ...")` | `UI/CMakeLists.txt:134-147` |
| Qt private headers | target check | `APERTAR_HAS_DISPLAY_POWER=0` + message naming `qt6-base-private-dev` | `:221-242` |
| TIFF, OpenGL, Qt6 modules (UI) | `REQUIRED` | configure fails | `:10-13` |

Runtime side: `#if APERTARCORE_HAS_*` guards (31 in `CameraController.cpp`, 10 in `ApertarCoreApp.cpp`, 1 in `CdngEncoder.cpp`) turn into an error string naming the missing dev package, for example `CameraController.cpp:3990-3995` "In-process H.264 recording requires libavcodec/libavformat development libraries at build time." Plugins that fail to load produce a similar message: `Core/src/prores/ProresRecorder.cpp:48`, `UI/src/VideoPlayback.cpp:36`.

Plugin loader shape, three instances:

| Plugin | Env override | Then | Then | ABI check | Ref |
| --- | --- | --- | --- | --- | --- |
| H.264 | `APERTAR_H264_LIBAV_PLUGIN` | `<exe dir>/apertar-h264-libav.so` | `/home/pi/ApertarCore-build/...`, bare name | symbol set | `Core/src/video/LibavH264EncoderClient.cpp:17-30` |
| ProRes | `APERTAR_PRORES_PLUGIN` | `<exe dir>/apertar-prores-libav.so` | `/home/pi/ApertarCore-build/...` | `apertar_prores_abi() == kApertarProresAbi` | `Core/src/prores/ProresRecorder.cpp:25-50` |
| Movie playback | `APERTAR_VIDEO_PLAYBACK_PLUGIN` | `<app dir>/apertar-video-libav.so` | `<app dir>/../lib/apertar-ui/...` | `entry()->version == 2` | `UI/src/VideoPlayback.cpp:18-37` |

### 3.3 Install rules

| Repo | Rule | Used on the Pi? | Ref |
| --- | --- | --- | --- |
| Core | `bin/apertar-core`, plugins to `lib/apertar-core` | no; service runs from `/home/pi/ApertarCore-build`; Core never searches `lib/apertar-core` | `Core/CMakeLists.txt:190-196`; `architecture/build.md:43` |
| UI | only `apertar-video-libav` to `lib/apertar-ui` | no | `UI/CMakeLists.txt:144` |
| UI | no install for `Apertar-UI` or any helper | helpers copied by hand to `/usr/local/libexec` | `architecture/build.md:142`, `:164` |

READMEs state that building installs nothing system-wide: `Core/README.md:87`, `:132`; `UI/README.md:219`, `:295`, `:305`.

## 4. Privilege: what runs as root and how

| Mechanism | What | Ref |
| --- | --- | --- |
| Dedicated root helper + exact-verb sudoers | `apertar-standby-usb off\|on`, `apertar-standby-low-power cpu\|nvme\|bluetooth\|all\|restore` | `UI/systemd/apertar-standby-usb.sudoers:1`; `UI/systemd/apertar-standby-low-power.sudoers:1`; caller `Core/src/ApertarCoreApp.cpp:1541-1550` ("Fixed executable and arguments only; never accept paths from WebUI/config.") |
| Generic `sudo -n <system tool>` from Core | `systemctl`, `timedatectl`, `hwclock`, `install` (config.txt), `blockdev`, `sh -c echo > /sys/...`, `mkdir`, `mount`, mkfs tools | `ApertarCoreApp.cpp:3031`, `:3157`, `:3205`, `:3239-3292`, `:3353`, `:3373`, `:3609-3636`, `:3810-3816` |
| Generic `sudo -n` from UI | mount/eject/format, privileged commands | `UI/src/MediaStatusBridge.cpp:727`, `:978`, `:1015-1036`, `:1057`; `UI/src/SystemActionBridge.cpp:609-625` |
| Embedded Python watcher | `sudo -n` or direct write if euid 0 | `ApertarCoreApp.cpp:3469-3482`; `MediaStatusBridge.cpp:837-850` |
| polkit | user `pi` may control NetworkManager (6 actions) | `UI/systemd/49-apertar-network.rules:1-12` |
| udev | `video` group write on backlight and `wittypi_led` | `UI/systemd/90-apertar-backlight.rules:1-2` |
| root service | `apertar-cfe-automounter` (unit not in repo; runs as root per Pi check) | `architecture/overview.md:145` |
| timedated over D-Bus | date/time from the UI | `UI/src/SystemActionBridge.cpp:588-603` |

The generic `sudo -n` calls have no sudoers file in either repo. They depend on the image's passwordless sudo for `pi` (**probable**: Raspberry Pi OS default `010_pi-nopasswd`; settle with `sudo -l -U pi` on the Pi). Failure is mapped to an operator sentence: "Shutdown needs a passwordless sudo rule for systemctl or a polkit rule ..." in both repos (`ApertarCoreApp.cpp:3180-3197`, `SystemActionBridge.cpp:570-582`), and power actions retry without sudo (`ApertarCoreApp.cpp:3205-3208`).

User scripts never get root: `Core/README.md:177` "Scripts run as the Core service user, without automatic administrator privileges"; template `ApertarCoreApp.cpp:4334` "Runs as pi, without automatic sudo."

Root helper code shape (both helpers): `Paths` struct with injectable roots, fixed verb whitelist with a usage line, `geteuid() != 0` → error, root-owned `/run/apertar-*` state dir checked with `lstat` (uid 0, not group/other writable), `flock` with `LOCK_NB`, exceptions → `std::cerr` + exit 1, `main` wrapped in `#ifndef APERTAR_*_TEST`. `UI/src/StandbyUsbPower.cpp:15-23`, `:241-273`; `UI/src/StandbyLowPower.cpp:13-17`, `:148-178`. Core undoes a left-over standby at start (`ApertarCoreApp.cpp:6807-6819`).

## 5. Environment variables (all of them)

### 5.1 Core binary

| Variable | Purpose | Ref |
| --- | --- | --- |
| `APERTAR_HARDWARE_CONFIG` | First candidate for `apertar-hardware.conf`; each reader has its own candidate list | `GpioInput.cpp:63`, `GroveAnalogInput.cpp:60`, `Mpu6050RecordingSession.cpp:194`, `NeoRotary4Input.cpp:76`, `Pcf8574Input.cpp:63`, `RecordingIndicatorOutput.cpp:73`, `TriggerOutput.cpp:76`, `ApertarCoreApp.cpp:3407` (Python), `:4254`, `:4273` |
| `APERTAR_MEDIA_ROOT` | Media root inside the embedded Python watcher | `ApertarCoreApp.cpp:3394`, `:3457` |
| `APERTAR_COLOR_PROFILE_CONFIG` | Override `/home/pi/apertar-color-profiles.conf` | `Core/src/color/ColorProfileConfig.cpp:234` |
| `APERTAR_DEFAULT_TUNING_DIR` | Override default tuning folder | `DefaultTuningSelection.hpp:58` |
| `APERTAR_SENSOR_TUNING_FILE` | Set by Core itself: original sensor tuning for RAW calibration | set `CameraController.cpp:1114-1120`, read `ColorProfileConfig.cpp:616` |
| `LIBCAMERA_RPI_TUNING_FILE` | libcamera's variable; Core sets/unsets it at every camera open | `CameraController.cpp:1116-1119`, `:5360`, `:7603`, `:7641`, `:8717` |
| `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME` | settings and UI.conf paths | `grep -rn getenv Core/src` |
| `APERTAR_H264_BACKEND` | `auto`/`libav`/`pipe` | `CameraController.cpp:4406` |
| `APERTAR_H264_ENCODER` | encoder name; must be `h264_v4l2m2m` on Pi 3/4 | `:3981`, `:4333` |
| `APERTAR_H264_PRESET`, `_TUNE`, `_CRF`, `_QP`, `_BITRATE`, `_MAXRATE`, `_BUFSIZE`, `_X264_PARAMS` | x264 tuning | `:4340-4398` |
| `APERTAR_H264_THREADS` | encoder threads, `auto`/`0`/1-16 | `:4435` |
| `APERTAR_H264_PIPE_BYTES`, `APERTAR_H264_QUEUE_FRAMES` | pipe size, queue depth | `:4456`, `:4467` |
| `APERTAR_H264_CAMERA_BUFFERS` | 3-12, default 4/6 by board | `:1127` |
| `APERTAR_H264_SIZE`, `APERTAR_H264_KEEP_RAW_STREAM`, `APERTAR_H264_SINGLE_STREAM` | stream layout experiments | `:2779`, `:2843`, `:2848` |
| `APERTAR_H264_LIBAV_PLUGIN` | plugin path | `LibavH264EncoderClient.cpp:20` |
| `APERTAR_CDNG_QUEUE_FRAMES`, `APERTAR_CDNG_WORKERS`, `APERTAR_LOSSYDNG_WORKERS`, `APERTAR_CDNG_WORKER_NICE` | cDNG worker pool | `CameraController.cpp:3330`, `:3343`, `:3345`, `:3359`, `:3706` |
| `APERTAR_CDNG_TILE_ROWS`, `APERTAR_CDNG_PROFILE_DETAIL` | encoder tiling, profiling log | `Core/src/cdng/CdngEncoder.cpp:55`, `:72` |
| `APERTAR_LOSSYDNG_ASYNCWRITE` (legacy alias `QRAW_LOSSYDNG_ASYNCWRITE`), `APERTAR_LOSSYDNG_WRITER_BYTES` | lossy writer | `LossyDngEncoder.cpp:325-327`, `:100` |
| `APERTAR_RAW_CACHED_DMABUF`, `APERTAR_PRORES_CACHED_DMABUF` | dma-buf cache mode | `CameraController.cpp:6321`, `:6387` |
| `APERTAR_PRORES_CAMERA_BUFFERS` | 8-32, default 12 | `:1133` |
| `APERTAR_PRORES_PLUGIN`, `APERTAR_PRORES_THREADS`, `APERTAR_PRORES_CSC_THREADS`, `APERTAR_PRORES_ODIRECT`, `APERTAR_PRORES_WRITEBACK`, `APERTAR_PRORES_WRITER_THREAD`, `APERTAR_PRORES_WRITER_QUEUE`, `APERTAR_PRORES_WRITER_QUEUE_MB`, `APERTAR_PRORES_WRITER_SLOW_MS` | ProRes plugin and writer | `ProresRecorder.cpp:28`, `:61`; `ProresEncoder.cpp:831`, `:1098`, `:1154`, `:1184-1200`, `:1323` |

None of these is mentioned in either README. They are developer/A-B knobs, not operator settings.

### 5.2 UI binaries

| Variable | Purpose | Ref |
| --- | --- | --- |
| `APERTAR_CONTROL_SOCKET` | Core socket path (default `/tmp/apertar-core.sock`) | `ApertarControlBridge.cpp:1032`, `:1567`; `AudioDeviceBridge.cpp:347`; `MediaStatusBridge.cpp:23` |
| `APERTAR_HARDWARE_CONFIG` | hardware config candidate | `CfeAutomounter.cpp:117`, `DisplayConfigBridge.cpp:29`, `GyroConfigBridge.cpp:201`, `Ina219Bridge.cpp:57`, `WifiBridge.cpp:21` |
| `APERTAR_MEDIA_ROOT` | media root | `SettingsBridge.cpp:145`, `:169` |
| `APERTAR_CORE_START_READY_FILE` | write marker after scene load (set by the image unit) | `UI/src/main.cpp:405-420` |
| `APERTAR_UI_READY_FILE` | write marker after first frame | `main.cpp:463`; exported by `run_pi_direct.sh:220` |
| `APERTAR_MONITOR_ONLY` | run as HDMI monitor-only process | `main.cpp:275`; set `run_pi_direct.sh:273` |
| `APERTAR_MONITOR_RUNTIME_SOCKET` | main→monitor state socket | `ExternalMonitorRuntimeBridge.cpp:16`; exported `run_pi_direct.sh:219` |
| `APERTAR_PREVIEW_FORCE_CPU`, `_PLANAR`, `_EGL` | preview path override | `PreviewWindowRenderer.cpp:296-301` |
| `APERTAR_STANDBY_PANEL_POWER` | panel power in standby | `DisplayStandbyController.cpp:18` |
| `APERTAR_PANEL_LED_PATH`, `APERTAR_BACKLIGHT_DIR` | backlight/LED sysfs override | `SleepManager.cpp:31`, `:102` |
| `APERTAR_VIDEO_PLAYBACK_PLUGIN` | movie plugin path | `VideoPlayback.cpp:24` |
| `APERTAR_NETWORK_HELPER` | set to 1 inside the helper; tells shared `WifiBridge` code it runs headless | `NetworkHelper.cpp:13`; `WifiBridge.cpp:155`, `:162`, `:478` |
| `APERTAR_NETWORK_RUNTIME` | helper runtime dir | `NetworkHelper.cpp:14` |
| `QT_QPA_PLATFORM`, `QSG_RENDER_LOOP`, `QT_QPA_EGLFS_KMS_CONFIG` | Qt; `basic` render loop forced on eglfs | `main.cpp:254-256`; `DisplayStandbyController.cpp:27` |

### 5.3 Scripts

| Variable | Script | Purpose | Ref |
| --- | --- | --- | --- |
| `APERTAR_CORE_BIN`, `APERTAR_MEDIA_ROOT`, `APERTAR_SOCKET_PATH` | start-apertar-core | binary, `--media`, `--socket` | `Core/scripts/start-apertar-core.sh:4-6` |
| `APERTAR_TUNING_FILE` | start-apertar-core | exported as `LIBCAMERA_RPI_TUNING_FILE` (no effect, Core overwrites it: `architecture/build.md:92`) | `:16-18` |
| `APERTAR_RUNTIME_ROOT` (legacy `APERTAR_NVME_RUNTIME_ROOT`) | run_pi_direct, sync_pi_runtime | mirror location | `UI/run_pi_direct.sh:13`; `UI/sync_pi_runtime.sh:7` |
| `APERTAR_USE_RUNTIME_MIRROR` (legacy `APERTAR_USE_NVME_RUNTIME`) | run_pi_direct | `0`/`auto`/other | `run_pi_direct.sh:14` |
| `APERTAR_MESA_RUNTIME_ROOT`, `APERTAR_RUNTIME_LIB_DIR` | both | Mesa and libproxy stub dirs | `run_pi_direct.sh:51`, `:54`; `sync_pi_runtime.sh:9-10` |
| `APERTAR_UI_BIN` | sync_pi_runtime | source binary | `sync_pi_runtime.sh:8` |
| `APERTAR_DRM_SYSFS` | run_pi_direct, wait gate | test hook for `/sys/class/drm` | `run_pi_direct.sh:78`; `wait_for_ui_core_start.sh:23` |
| `APERTAR_UI_READY_FILE`, `APERTAR_HEADLESS_READY_FILE` | run_pi_direct, plymouth | readiness markers | `run_pi_direct.sh:79-80`; `finish_plymouth_handoff.sh:8` |
| `APERTAR_CORE_START_READY_FILE` | run_pi_direct (headless) | release Core gate without a screen | `run_pi_direct.sh:172-175` |
| `APERTAR_MONITOR_HOTPLUG_POLL_SECONDS` | run_pi_direct | poll interval (1 s headless, 0.5 s monitor) | `:178`, `:312`, `:345` |
| `APERTAR_UI_DRM_DEVICE`, `APERTAR_MONITOR_DRM_DEVICE` | run_pi_direct | force DRM card | `:188`, `:191` |
| `APERTAR_QT_USE_LIBINPUT` | run_pi_direct | `1` = libinput, else evdev | `:211-217` |
| `QT_QPA_EGLFS_HOTPLUG_ENABLED`, `QSG_RENDER_LOOP` | run_pi_direct | defaults if unset | `:210`, `:218` |
| `APERTAR_PLYMOUTH_HANDOFF_TIMEOUT_SECONDS`, `APERTAR_PLYMOUTH_BIN` | plymouth handoff | 20 s, `/usr/bin/plymouth` | `finish_plymouth_handoff.sh:6-7` |
| Exported to the UI | run_pi_direct | `QT_QPA_PLATFORM=eglfs`, `QT_QPA_EGLFS_INTEGRATION=eglfs_kms`, `QT_QPA_EGLFS_KMS_CONFIG`, `QT_QPA_EGLFS_NO_LIBINPUT`, `LD_LIBRARY_PATH`, `GBM_BACKENDS_PATH`, `LIBGL_DRIVERS_PATH`, `__EGL_VENDOR_LIBRARY_FILENAMES`, `QT_PLUGIN_PATH`, `QML2_IMPORT_PATH`; unsets `DISPLAY`, `WAYLAND_DISPLAY` | `:35-36`, `:63-66`, `:207-221` |

Rough edge: `LIBGL_DRIVERS_PATH` points to `mesa-minimal/lib/aarch64-linux-gnu/dri`, which is not in the tree (`ls UI/mesa-minimal/lib/aarch64-linux-gnu`: only `gbm/`, `libEGL_mesa*`, `libgallium-26.2.0.so`, `libgbm*`, `pkgconfig/`).

## 6. Services, start order, runtime files

In-repo unit: `UI/systemd/apertar-network.service` (User=pi, `RuntimeDirectory=apertar-network`, runs straight from `/home/pi/ApertarUI/build/`, `Restart=on-failure`) `:1-19`. Drop-in `apertar-network-start-gate.conf` waits on `main-ui-ready` with `-` prefix "Ignore helper errors to preserve recovery SSH" `:2-4`. Core drop-in `LimitNICE=-5`.

Start order is file-based, not unit-based: UI writes `core-start-ready` → Core `ExecStartPre` gate waits ≤ 8 s → UI writes `main-ui-ready` on first frame → Plymouth quits; network gate waits on the same file. All gates exit 0 on timeout, invalid timeout, or no screen (`UI/wait_for_ui_core_start.sh:5-10`, `:30-33`, `:54-56`; `UI/finish_plymouth_handoff.sh:10-12`, `:28-30`). Full table: `architecture/overview.md:83-100`.

Runtime file locations:

| Path | Owner | Ref |
| --- | --- | --- |
| `/tmp/apertar-core.sock` | Core | `Core/README.md:252` |
| `~/.config/apertar-core/camera_settings.conf` | Core | `Core/README.md:267` |
| `~/.config/CinePi/UI.conf` | UI (Core rewrites) | `architecture/overview.md:44` |
| `/home/pi/apertar-hardware.conf` (then `/boot/firmware/`, `/boot/`) | all | `GpioInput.cpp:55-76`; 17 literal copies of the path in Core+UI (`grep -rho '"/home/pi/apertar-hardware.conf'`) |
| `/home/pi/apertar-color-profiles.conf`, `/home/pi/Tuning-Files/`, `/home/pi/LUTs/` | Core / UI | `Core/README.md:145-152`; `UI/README.md:113-116` |
| `/run/apertar-ui/*`, `/run/apertar-network/managed`, `/run/apertar-cfe/ready`, `/run/apertar-standby-usb/`, `/run/apertar-standby-low-power/` | markers and root state | `architecture/overview.md:44-49`; helper `Paths` structs |
| `$XDG_RUNTIME_DIR/apertar-display-$UID/` (mode 700) | run_pi_direct | `run_pi_direct.sh:194-196` |
| `~/.cache/apertar-runtime` | sync_pi_runtime; refuses `/media/RAW` | `sync_pi_runtime.sh:7`, `:16-19` |
| `/media/RAW` | recordings | `Core/README.md:263` |

## 7. Third-party code and licences

| Item | Where | Notice | Ref |
| --- | --- | --- | --- |
| liblj92 (MIT, Andrew Baldwin, via cgohlke/imagecodecs) | `UI/third_party/liblj92/` | `LICENSE` + `README.apertar.md` with upstream commit pin and the local fix | `README.apertar.md:3-11`; built as one source in the UI exe `UI/CMakeLists.txt:123` |
| Mesa 26.2.0 (MIT-family) binaries + EGL/GBM/DRI headers | `UI/mesa-minimal/` | **no** licence file or README; only header comments (`include/EGL/eglmesaext.h:3`, `include/EGL/eglext_angle.h:2-4`); `gbm.pc` prefix is `/home/pi/ApertarUI/mesa-minimal` | `UI/mesa-minimal/lib/aarch64-linux-gnu/pkgconfig/gbm.pc:1-7` |
| Fonts Gotham (5 weights), Inter (6 weights) | `UI/qml/fonts/` | no licence files (Gotham is a commercial typeface; **probable** licence gap, not a code question) | `git ls-files UI/qml/fonts` |
| Lossy 12-bit JPEG encoder | `Core/src/lossydng/LossyJpeg12.cpp`, `.h`, `fastent.h` | no licence header; header says it targets the Blackmagic tile format; `LossyJpeg12.cpp` is tracked but **not in `CMakeLists.txt` and not included anywhere** (dead file) | `Core/src/lossydng/LossyJpeg12.cpp:1-10`; check `for f in $(git ls-files src \| grep .cpp$); do grep -q $f CMakeLists.txt \|\| echo $f; done` |

Core has no `third_party/`. No source file in either repo carries a licence or SPDX header (`grep -rn -i spdx` → none). Both repos: GPL-2.0 `LICENSE` at root.

Docs referenced but not shipped: `Core/README.md:225` (`src/prores/ffmpeg/` build recipe; absent), `UI/README.md:55` (`docs/prores-color-profiles.md` in Core; absent), `ProresEncoder.cpp:1609` (`PRORES-FINDINGS.md`; absent), `LossyJpeg12.cpp:10` (`bench/dct_bench2.c`; absent).

## 8. Rules

Strength key: always = no counter-example found (search named), usually = exceptions named, once = single precedent.

### STRUCTURE

| ID | Rule | Strength | Evidence | Exceptions |
| --- | --- | --- | --- | --- |
| S1 | List every new translation unit by hand in the one `add_executable` of its repo; no globbing; Core lists only `.cpp`, UI lists `.cpp` and `.hpp` | usually | `Core/CMakeLists.txt:69-96`; `UI/CMakeLists.txt:63-130`; `grep file(GLOB` → none | `Core/src/lossydng/LossyJpeg12.cpp` tracked, not built; `UI/qml/InlineChoice.qml` tracked, in neither QML list |
| S2 | Put a new QML file in both `APERTAR_QML_FILES` and `qml.qrc` | usually | `UI/CMakeLists.txt:19-52`; `UI/qml.qrc:3-33` | `DroppedFrameWarning.qml` is in CMake `:40` but missing from `qml.qrc` (AOT-off build lacks it) |
| S3 | Heavy optional libraries (FFmpeg) go into a lazily `dlopen`ed MODULE with `PREFIX ""`, a C entry point with ABI/version check, and an env→exe-dir→fallback search; never link them into the main binary | always (3 of 3 plugins) | `Core/CMakeLists.txt:140-169`; `LibavH264EncoderClient.cpp:17-30`; `ProresRecorder.cpp:25-50`; `UI/CMakeLists.txt:132-147`; `VideoPlayback.cpp:18-37` | - |
| S4 | Optional build deps are found QUIET; absence becomes a `*_HAS_X=0` compile definition plus a `message(STATUS)` naming the package, and code paths return an error string naming the missing dev package | usually | `Core/CMakeLists.txt:120-138`, `:170-173`; `UI/CMakeLists.txt:145-146`, `:236-242`; `CameraController.cpp:3990-3995` | libcamera absence prints no message (`Core/CMakeLists.txt:136-138`); TIFF/yaml/ALSA are REQUIRED |
| S5 | Board capabilities are decided once in Core from the DT `compatible` SoC string, published as `recording_capabilities` in state, enforced in Core and mirrored (not re-derived) by touch UI and WebUI | usually | `RecordingCapabilities.hpp:18-106`; `ApertarCoreApp.cpp:192`, `:7876`; `ApertarControlBridge.cpp:1286-1294`, `:431-440`; `WebControlPage.cpp:5571-5576`; `UI/README.md:324` | non-format features (fan, USB power, Pi 3 preview) use DT `model` strings locally (`SettingsPage.qml:97`, `StandbyUsbPower.cpp:59`, `PreviewWindowRenderer.cpp:33-41`) |
| S6 | Platform detection lives in small header-only inline functions: a pure `...FromCompatible(string)` parser plus a cached reader trying `/sys/firmware/devicetree/base/compatible` then `/proc/device-tree/compatible` | always (2 of 2) | `RecordingCapabilities.hpp:18-50`; `DefaultTuningSelection.hpp:18-50` | the two are copies, not shared |
| S7 | Anything needing root goes into a single-file helper in `UI/src/`, built as its own target `apertar-<name>` (no Qt, AUTOMOC OFF, warnings on), installed by hand to `/usr/local/libexec`, called by Core with `/usr/bin/timeout Ns /usr/bin/sudo -n <abs path> <literal verb>`, with a `systemd/apertar-<name>.sudoers` listing each verb | always (2 of 2) | `UI/CMakeLists.txt:150-155`; `UI/systemd/apertar-standby-*.sudoers:1`; `ApertarCoreApp.cpp:1541-1550` | - |
| S8 | Simple privileged system operations call the system tool directly via `sudo -n` from Core or UI and rely on the image's passwordless sudo; failures map to a human sentence | usually | `ApertarCoreApp.cpp:3031`, `:3157`, `:3205`, `:3239-3292`, `:3609-3636`, `:3810-3816`; `MediaStatusBridge.cpp:978-1057`; `SystemActionBridge.cpp:609-625`; `ApertarCoreApp.cpp:3180-3197` | date/time in the UI goes over timedated D-Bus (`SystemActionBridge.cpp:588-603`); Wi-Fi via polkit (`49-apertar-network.rules`) |
| S9 | System integration files (units, drop-ins, sudoers, polkit, udev) live flat in `UI/systemd/`; Core keeps only `config/` (drop-in) and `scripts/` (start script); no installer script exists, units for Core/UI/automounter are image-owned | always | `git ls-files` both repos (section 1) | - |
| S10 | Launch and deployment scripts live at the UI repo root as bash, configured by `APERTAR_*` env with defaults | always (5 of 5 scripts) | `UI/run_pi_direct.sh:5-14`; `UI/sync_pi_runtime.sh:5-10`; `UI/wait_for_ui_core_start.sh:5-6`; `UI/finish_plymouth_handoff.sh:5-8`; `Core/scripts/start-apertar-core.sh:4-6` | Core start script is in `Core/scripts/` |
| S11 | The image layout is hard-coded: user `pi`, `/home/pi/...` for config, tuning, LUTs and build dirs; config search order env → `/home/pi` → `/boot/firmware` → `/boot` | always | 23 source files contain `/home/pi` (`grep -rl /home/pi`); `GpioInput.cpp:55-76`; `LibavH264EncoderClient.cpp:27`; `ProresRecorder.cpp:32`; `UI/systemd/apertar-network.service:8-14`; sudoers `pi` | - |
| S12 | Each process and each hardware class carries its own copy of shared plumbing (config path list, hardware-config template, gpiochip scorer, fan-mode writer, power-error text, CFE Python watcher) instead of a shared library | always | template: `ApertarCoreApp.cpp:4291`, `UI/src/DisplayConfigBridge.cpp:57`, `UI/src/Ina219Bridge.cpp:85`, `UI/src/GyroConfigBridge.cpp:1588`, `Mpu6050RecordingSession.cpp:624`; gpiochip: `GpioInput.cpp:238`, `TriggerOutput.cpp:201`, `RecordingIndicatorOutput.cpp:198`; fan: `ApertarCoreApp.cpp:3042` vs `SystemActionBridge.cpp:64`; watcher: `ApertarCoreApp.cpp:3385-3590` vs `MediaStatusBridge.cpp:755-960` | - |

### IDIOM

| ID | Rule | Strength | Evidence | Exceptions |
| --- | --- | --- | --- | --- |
| I1 | Name env vars `APERTAR_<AREA>_<KNOB>`, read them at the point of use, parse strictly, clamp to a range and fall back silently to the default; do not document them in the README | usually | `CameraController.cpp:1027-1060`, `:1125-1135`, `:4433-4451`; `ProresEncoder.cpp:1323-1326`; READMEs mention none | legacy aliases kept: `QRAW_LOSSYDNG_ASYNCWRITE` (`LossyDngEncoder.cpp:327`), `APERTAR_NVME_RUNTIME_ROOT`, `APERTAR_USE_NVME_RUNTIME` (`run_pi_direct.sh:13-14`) |
| I2 | Derive thread and worker counts from `hardware_concurrency()` with `min`/`max` clamps; no CPU affinity, no real-time scheduling, only bounded `nice` | always | `CameraController.cpp:3323-3340`, `:4448-4451`; `ProresEncoder.cpp:1321-1322`; `CameraController.cpp:6590-6599`; `apertar-core-capture-priority.conf:2-3`; grep `affinity\|nproc\|SCHED_FIFO` → none | - |
| I3 | Log with a fixed component prefix: Core `std::cerr << "ApertarCore <area> ..."`, UI `qInfo() << "Apertar <area>: ..."`, helpers and scripts `"<Component name>: ..."` with `printf` | usually | Core: 188 `std::cerr` lines, top prefixes `ApertarCore ProRes/gyro/audio/H.264`; `UI/src/main.cpp:245-248`, `:414-416`; `CfeAutomounter.cpp:634`; `run_pi_direct.sh:29`, `wait_for_ui_core_start.sh:31` | some Core lines use `Apertar standby`, `GPIO input`, `Grove analog` (`ApertarCoreApp.cpp:6811`) |
| I4 | Turn on `-Wall -Wextra -Wpedantic` per target | usually | `Core/CMakeLists.txt:148`, `:168`, `:175-180`; `UI/CMakeLists.txt:142`, `:153`, `:155`, `:166` | UI main exe and network helper have no warning flags |
| I5 | Explain each non-obvious build or script decision with a 1-3 line "why" comment above it (cold boot, real-time, cross-build) | usually | `Core/CMakeLists.txt:9-11`, `:47`, `:57`; `UI/CMakeLists.txt:54-55`, `:132-133`, `:169-171`, `:221-222`, `:244-246`; `run_pi_direct.sh:25-26`, `:41-44`; `sync_pi_runtime.sh:62-64` | - |
| I6 | Root helper shape: injectable `Paths` struct, verb whitelist + usage line, `geteuid` check, root-owned `/run/apertar-<name>` state dir verified with `lstat`, `flock(LOCK_NB)`, exceptions → stderr + exit 1, `main` under `#ifndef APERTAR_<NAME>_TEST` | always (2 of 2) | `StandbyUsbPower.cpp:15-23`, `:241-273`; `StandbyLowPower.cpp:13-17`, `:148-178` | - |
| I7 | Scripts: `set -euo pipefail` for launchers; `set -u` and unconditional `exit 0` for gates that must never block boot | always (5 of 5) | `run_pi_direct.sh:3`; `sync_pi_runtime.sh:3`; `start-apertar-core.sh:2`; `wait_for_ui_core_start.sh:3`, `:56`; `finish_plymouth_handoff.sh:3`, `:30` | - |
| I8 | Vendored source goes in `third_party/<name>/` with the upstream `LICENSE` and a `README.apertar.md` naming upstream URL, commit and local changes | once | `UI/third_party/liblj92/README.apertar.md:1-11` | `mesa-minimal/` binaries and `qml/fonts/` have no notice; `LossyJpeg12.*` in Core has none |

### INTENT

| ID | Rule | Strength | Evidence | Exceptions |
| --- | --- | --- | --- | --- |
| N1 | Three board classes are supported (Pi 5/CM5, Pi 4/400/CM4, Pi 3/3A+/Zero 2 W); a format the board cannot sustain is refused with a message naming the board class, and saved settings are coerced to a supported format at load | always | `Core/README.md:60-72`; `UI/README.md:57-67`; `RecordingCapabilities.hpp:64-106`; `CameraController.cpp:7989`, `:8005`, `:8018`; `ApertarControlBridge.cpp:431-440`; `WebControlPage.cpp:5622` | - |
| N2 | On an unrecognised platform do not guess Pi behaviour: leave tuning to libcamera, report `unknown` | usually | `DefaultTuningSelection.hpp:66-69`, `:53` | `RecordingCapabilities{}` default enables RAW recording on unknown boards (`:11-16`, `:47`) |
| N3 | Probe hardware by identity rather than fixed index (DRM connectors by type and status, H.264 encoder node by driver name, gpiochip by label score, IMU by bus scan) | usually | `UI/README.md:126`; `run_pi_direct.sh:83-166`; `H264Hardware.hpp:19`, `:37`; `GpioInput.cpp:238-262`, `:505-535`; `Mpu6050RecordingSession.cpp:1557-1597` | fixed defaults: I2C bus 10/4/1, `1000110000.pcie`, Pi 5 USB controller addresses (`StandbyUsbPower.cpp:69-80`) |
| N4 | Cold-boot time is a design constraint: keep FFmpeg and proxy discovery out of the startup graph, lazy-bind, ship a trimmed Mesa, order services through readiness files | always | `UI/CMakeLists.txt:132-133`, `:169-171`, `:244-246`; `run_pi_direct.sh:41-44`; `UI/systemd/apertar-network-start-gate.conf:2-3`; `architecture/overview.md:100` | - |
| N5 | Startup gates and handoffs never block the camera or recovery: timeouts, skip without a screen, ignore helper errors, always exit 0 | always | `wait_for_ui_core_start.sh:7-10`, `:30-33`, `:54-56`; `finish_plymouth_handoff.sh:10-12`, `:28-30`; `apertar-network-start-gate.conf:2-4` | - |
| N6 | Headless operation is first-class: without a screen Core and WebUI keep working and the launcher waits for a hotplug | always | `run_pi_direct.sh:168-186`; `wait_for_ui_core_start.sh:30-33`; `Core/README.md:5`, `:128`; `UI/README.md:203` | - |
| N7 | Root access is narrow and never data-driven: fixed binaries, fixed arguments, never a path from WebUI/config; user scripts run without sudo | always | `ApertarCoreApp.cpp:1543`; sudoers files; `Core/README.md:177`; template `ApertarCoreApp.cpp:4334` | the generic `sudo -n` calls in S8 build arguments from validated values (device paths, labels) via `shellQuote` |
| N8 | Building does not install drivers, overlays, libcamera, tuning, services, network or permissions; READMEs say so and warn against replacing a working camera stack | always | `Core/README.md:87`, `:132`, `:199`; `UI/README.md:219`, `:244`, `:295`, `:305` | - |
| N9 | Board-specific power features check the exact topology and refuse, keeping the safe state, when anything is unexpected | once | `StandbyUsbPower.cpp:59-80` ("keeping USB powered") | - |
| N10 | Core and UI are versioned and released together as squashed drops; READMEs tell operators to update both together | usually | `Core/README.md:306`; `UI/README.md:21`; Core history = 1 commit `35dbe67` | UI keeps a short history (10 commits) |

## 9. Recipes

### R1 Add a source file

1. Core: create `src/<area>/<Name>.cpp` and `.hpp` (areas: `audio camera cdng color hardware ipc lossydng mlv prores util video web`, `Core/src/`); header-only helpers may live in `include/apertar/core/` (`RecordingCapabilities.hpp`).
2. Core: add the `.cpp` to `add_executable(apertar-core ...)` next to its area (`Core/CMakeLists.txt:69-96`). Do not list headers.
3. Core plugin code instead goes to the MODULE target (`Core/CMakeLists.txt:143-145`, `:152-157`).
4. UI C++: add both `.cpp` and `.hpp` to `add_executable(ApertarUI ...)` (`UI/CMakeLists.txt:63-130`); naming `<Thing>Bridge.cpp` for QML-facing classes.
5. UI QML: add to `APERTAR_QML_FILES` (`UI/CMakeLists.txt:19-52`) **and** `qml.qrc` (`UI/qml.qrc:3-33`); images/fonts to `resources.qrc`.
6. Rebuild; QML is compiled in (`architecture/build.md:114`).

### R2 Add an optional dependency

1. Find it QUIET: `pkg_check_modules(X QUIET IMPORTED_TARGET ...)` inside the existing `if(PkgConfig_FOUND)` blocks (`Core/CMakeLists.txt:43-45`; `UI/CMakeLists.txt:134-137`).
2. If it is large or slows cold boot: build a MODULE with `PREFIX ""`, warnings on, a C ABI header (`Core/src/prores/ProresPluginApi.hpp`, `Core/src/video/LibavH264PluginApi.hpp`, `UI/src/VideoPlaybackApi.h`) and an ABI/version symbol (`Core/CMakeLists.txt:143-149`).
3. Write the loader: env override `APERTAR_<NAME>_PLUGIN`, then exe dir, then the Pi build dir; check the ABI; on failure set an error naming the `.so` and the dev packages (`ProresRecorder.cpp:25-50`; `VideoPlayback.cpp:18-37`).
4. If small: link it and add `target_compile_definitions(... <PROJECT>_HAS_X=1/0)` (`Core/CMakeLists.txt:133-138`) plus `message(STATUS "... disabled: install <pkg>-dev")` (`UI/CMakeLists.txt:146`).
5. Guard code with `#if <PROJECT>_HAS_X` and return an operator-readable error in the `#else` path (`CameraController.cpp:3990-3995`).
6. Add the package to the README requirements and `apt install` line (`Core/README.md:181-197`; `UI/README.md:223-242`).

### R3 Add a helper that needs root

1. Write `UI/src/<Name>.cpp` as one file, no Qt, shaped like `StandbyLowPower.cpp:13-178`: `Paths` struct, verb whitelist, `geteuid` check, `/run/apertar-<name>` state dir with `lstat` checks, `flock`, `#ifndef APERTAR_<NAME>_TEST` around `main`.
2. Add the target: `add_executable(Apertar<Name> src/<Name>.cpp)`, `OUTPUT_NAME "apertar-<name>" AUTOMOC OFF AUTORCC OFF`, `-Wall -Wextra -Wpedantic` (`UI/CMakeLists.txt:150-155`).
3. Add `UI/systemd/apertar-<name>.sudoers`: one line, `pi ALL=(root) NOPASSWD:` followed by every allowed `/usr/local/libexec/apertar-<name> <verb>` (`apertar-standby-low-power.sudoers:1`).
4. Call it from Core with a literal command: `/usr/bin/timeout Ns /usr/bin/sudo -n /usr/local/libexec/apertar-<name> <verb>` (`ApertarCoreApp.cpp:1541-1550`); never pass paths or values from WebUI or config.
5. If it changes system state, restore it at Core start when its `/run` state file exists (`ApertarCoreApp.cpp:6807-6819`).
6. Install is manual (`sudo install -m 755 -o root -g root build/apertar-<name> /usr/local/libexec/`, `architecture/build.md:164`); say so in the README section of the feature.

### R4 Add an environment variable

1. Name it `APERTAR_<AREA>_<KNOB>` (section 5).
2. Core: read at the point of use with `unsignedEnvValue(name, default, min, max)` or `boolEnvValue(name, default)` (`CameraController.cpp:1027-1060`), or a local `std::getenv` with strict parse and clamp (`:4433-4446`). UI: `qgetenv` / `qEnvironmentVariable` (`main.cpp:406`, `VideoPlayback.cpp:24`).
3. Keep a safe default so an unset or invalid value changes nothing.
4. Log the effective value in the existing start-of-recording or startup line, not a new log (`CameraController.cpp:3355-3362`).
5. Scripts: `NAME="${APERTAR_X:-default}"` at the top; when renaming, keep the old name as the inner fallback (`run_pi_direct.sh:13-14`).
6. Values for the service come from the image unit's `Environment=` or from `run_pi_direct.sh` exports (`:207-221`); the repo unit sets only `HOME` and `LC_ALL` (`apertar-network.service:10-11`).

## Challenge

Challenger pass, read-only, all refs `@upstream-1.6.0` (`Core/` = `/home/user/wt/core-upstream`, `UI/` = `/home/user/wt/ui-upstream`). Method: `git ls-files` of both repos, per-rule `grep -rn` over `src/ include/ *.sh systemd/ CMakeLists.txt README.md`, unlisted-source check (every tracked `src/*` grepped against its `CMakeLists.txt`), QML set diff (`qml.qrc` vs `APERTAR_QML_FILES` vs `git ls-files qml`).

| Rule | Verdict | Counter-example / note |
| --- | --- | --- |
| S1 | holds (usually) | UI header-only `src/PreviewExposureReference.hpp` is not listed (`UI/CMakeLists.txt:63-130`; used at `UI/src/PreviewWindowRenderer.cpp:4`). `Core/src/lossydng/LossyJpeg12.cpp` is tracked but in no target and included nowhere: dead file, not a glob. UI has several `add_executable` (helpers `UI/CMakeLists.txt:149-156`); "single" means the main app target. `UI/third_party/liblj92/lj92.c` is listed inline in the app target (`:123`). |
| S2 | holds, keep usually | Sets of `qml.qrc` and `APERTAR_QML_FILES` are identical (diff gives order only). Rough edge: `UI/qml/InlineChoice.qml` is tracked and in neither list (dead). Fonts/icons go in `qml.qrc` only. |
| S3 | holds, widen | Three FFmpeg modules, all lazy, all with ABI/version symbol (`Core/src/video/LibavH264EncoderClient.cpp:112-123`, `Core/src/prores/ProresRecorder.cpp:39`, `UI/src/VideoPlayback.cpp:31`). Search order differs in UI: env -> exe dir -> `../lib/apertar-ui` (no `/home/pi` path) (`UI/src/VideoPlayback.cpp:23-26`). H.264 adds bare-name fallback (`LibavH264EncoderClient.cpp:32`). Missed sibling: ALSA headers are REQUIRED at build (`Core/CMakeLists.txt:28`) but `libasound.so.2` is `dlopen`ed at runtime, not linked (`Core/src/audio/TimestampedAudioCapture.cpp:43-47`). |
| S4 | weaken wording, keep usually | Disabled libcamera and disabled JPEG set `=0` with no `message(STATUS)` (`Core/CMakeLists.txt:134-138`, `:114-117`); libcamera-off error does not name a package: "ApertarCore was built without libcamera support." (`Core/src/camera/CameraController.cpp:5395`). Core ALSA, YAML and UI TIFF are REQUIRED (`Core/CMakeLists.txt:27-28`, `UI/CMakeLists.txt:13`). |
| S5 | holds (usually) | Recording capabilities: Core decides, UI reads `recording_capabilities` (`UI/src/ApertarControlBridge.cpp:1286-1294`) and repeats Core's wording (`:434,439,497,520`). Exception outside recording: UI decides its own Pi 3 preview path from `/proc/device-tree/model` (`UI/src/PreviewWindowRenderer.cpp:33-41,295`). |
| S6 | weaken to usually | Core holds (two header-only parsers). Counter-examples: `UI/src/PreviewWindowRenderer.cpp:33-41` (non-cached, `model` string, anonymous-namespace function in a .cpp); `UI/src/StandbyUsbPower.cpp:20,59` (`model` must start with "Raspberry Pi 5 Model"). Rule = Core uses `compatible`; UI and helpers use `model`. |
| S7 | holds (always, 2 instances) | Only two sudo helpers exist (`apertar-standby-usb`, `apertar-standby-low-power`). Other UI helpers are not root via sudo: `apertar-network-helper` links Qt and runs as `User=pi` from `/home/pi/ApertarUI/build/` (`UI/CMakeLists.txt:156-158`, `UI/systemd/apertar-network.service:7-14`); `apertar-cfe-automounter` is image-owned. Add: Core treats the helper as optional, checks it exists before use (`Core/src/ApertarCoreApp.cpp:9152`). |
| S8 | holds (usually) | Many sites (`Core/src/ApertarCoreApp.cpp:3031,3157,3239-3292,3353,3373,3609-3636,3810-3816`). Add: tries `sudo -n` then the same command unprivileged (`:3205-3207`, once). Embedded Python watcher also uses `sudo -n` (`:3471,3482`; UI copy `UI/src/MediaStatusBridge.cpp:839,850`). |
| S9 | weaken wording, keep always | "No installer" is too strong: CMake `install()` exists for binaries and plugin modules (`Core/CMakeLists.txt:190-196`, `UI/CMakeLists.txt:144`). What holds: nothing installs units, sudoers, polkit, udev, or the sudo helpers. |
| S10 | weaken to usually | `Core/scripts/start-apertar-core.sh` lives in Core, not UI root (`:1-21`). `UI/wait_for_ui_core_start.sh:5-6` is configured by positional args, not `APERTAR_*` env. |
| S11 | weaken to usually, narrow | Holds for `apertar-hardware.conf` (13 copies of env -> `/home/pi` -> `/boot/firmware` -> `/boot`). Settings do not use `/home/pi`: `camera_settings.conf` is `$XDG_CONFIG_HOME` or `$HOME/.config/apertar-core/` (`Core/src/camera/CameraController.cpp:346-350`); UI.conf is `$HOME/.config/CinePi/UI.conf` (`Core/src/ApertarCoreApp.cpp:344-347`). |
| S12 | holds | Confirmed 14 files read `APERTAR_HARDWARE_CONFIG` (`grep -rln` both repos). |
| I1 | holds (usually) | Parse is not always strict: `std::atoi` in `Core/src/prores/ProresRecorder.cpp:62` and `Core/src/prores/ProresEncoder.cpp:1324`. Clamp + fallback holds there too. |
| I2 | weaken to usually | `Core/src/prores/ProresRecorder.cpp:60` fixed `threads = 4` (ProRes is Pi 5 only). Clamp holds everywhere. No affinity/RT found (`grep sched_setaffinity|SCHED_FIFO|SCHED_RR` empty); `setpriority` only at `CameraController.cpp:3708` (positive nice) and `:6595` (-5). |
| I3 | holds (usually), refine | Core: 131 of 186 `std::cerr << "` lines start "ApertarCore". Others use "Apertar standby" (`ApertarCoreApp.cpp:6810-6939,9156`), "Hardware input ..." (`:8464,8605,8954`), device name "NeoRotary4 ..." (`Core/src/hardware/NeoRotary4Input.cpp:318,325,621`). UI `qWarning` messages mostly have no prefix (`UI/src/PreviewWindowRenderer.cpp` shader errors). |
| I4 | weaken to usually | Main UI target `ApertarUI` and `ApertarNetworkHelper` have no `-Wall -Wextra -Wpedantic` (`UI/CMakeLists.txt:156-158,207-219`, no `target_compile_options(ApertarUI`). Core main target and all modules/helpers have them. |
| I5 | holds (usually) | |
| I6 | holds (always, 2 instances) | Scope: sudo helpers only. `CfeAutomounter.cpp:756` and `NetworkHelper.cpp:9` have no Paths/geteuid/flock/test macro. Test macro names are `APERTAR_USB_POWER_TEST` / `APERTAR_LOW_POWER_TEST` (`StandbyUsbPower.cpp:241`, `StandbyLowPower.cpp:148`), not derived from the binary name. |
| I7 | holds | All 5 scripts checked. |
| I8 | holds (once) | Exception: `UI/mesa-minimal/` vendors prebuilt aarch64 `.so` files with no README or LICENSE (git ls-files). |
| N1 | holds | Coercion at load and on set: `Core/src/camera/CameraController.cpp:588,2709,7599-7601,7923,7962,8234,8616,8672`. |
| N2 | holds (usually) | |
| N3 | holds (usually) | Add exception: I2C peripherals default to bus 1, overridable in hardware conf (`Core/src/hardware/Mpu6050RecordingSession.hpp:40`, `Pcf8574Input.hpp:31`, `NeoRotary4Input.hpp:39`, `GroveAnalogInput.hpp:55`, `UI/src/GyroConfigBridge.hpp:138`). gpiochip scan is 0..9 then scored (`GpioInput.cpp:512`). |
| N4 | holds | |
| N5 | holds | |
| N6 | holds | |
| N7 | weaken to usually | WebUI values do reach root commands as quoted arguments to fixed tools: time zone from `apply_time_zone` goes to `sudo -n timedatectl set-timezone <shellQuote(tz)>` with only an empty check (`Core/src/ApertarCoreApp.cpp:3270-3290`); date fields are range-checked first (`:3222-3224`). Paths stay system-derived (`formatMediaAtPath(options_.mediaRoot,...)`, `:10582`). Holds absolutely for libexec helpers (literal verbs). |
| N8 | holds | CMake `install()` exists but README build steps never call it (`Core/README.md:206-207`, `UI/README.md:249-252`). |
| N9 | holds (once) | |
| N10 | holds (usually) | UI history has 3 commits, release commit `8847105 Updated to version 1.6.0`. |

### Missed rules

| Id | Kind | Rule | Strength | Evidence |
| --- | --- | --- | --- | --- |
| S13 | structure | No test targets and no CI in either repo; testability is a compile-time `#ifndef APERTAR_*_TEST` around `main` in sudo helpers only. | always (searched `enable_testing|add_test|ctest`, `git ls-files | grep -i test`, `.github/` holds only `FUNDING.yml`) | `Core/CMakeLists.txt` (no test), `UI/CMakeLists.txt` (no test), `UI/src/StandbyUsbPower.cpp:241`, `UI/src/StandbyLowPower.cpp:148` |
| S14 | structure | UI builds in-tree into `build/` and the repo tracks that output (551 files incl. aarch64 `build/Apertar-UI`) plus prebuilt `mesa-minimal/`; there is no `.gitignore`. Core builds out of tree in `../ApertarCore-build`. Scripts depend on these paths. | once (UI repo) | `git ls-files build | wc -l` = 551; `UI/README.md:249-260`; `UI/sync_pi_runtime.sh:8-10`; `Core/README.md:206-207` |
| S15 | structure | Grant the `pi` user narrow rights with polkit actions and udev group permissions, and run services as `User=pi`, instead of a root process. | usually (sudo helpers are the exception) | `UI/systemd/49-apertar-network.rules:1-12`; `UI/systemd/90-apertar-backlight.rules:1-2`; `UI/systemd/apertar-network.service:7-8` |
| S16 | structure | System libraries a feature needs only at runtime are `dlopen`ed by soname with headers as the only build dependency. | once (ALSA) | `Core/CMakeLists.txt:28` + `Core/src/audio/TimestampedAudioCapture.cpp:43-47` |
| I9 | idiom | Language level differs per repo: Core C++20 with extensions off, UI C++17. | always (one place each) | `Core/CMakeLists.txt:21-23`; `UI/CMakeLists.txt:4-5` |
| I10 | idiom | Keep legacy `CinePi` names for settings storage (`QSettings("CinePi","UI")`, `~/.config/CinePi/UI.conf`); do not rename storage. | always (5 sites) | `UI/src/SettingsBridge.cpp:287`; `UI/src/ApertarControlBridge.cpp:118`; `UI/src/WifiBridge.cpp:127`; `UI/src/DisplayCalibration.cpp:49`; `Core/src/ApertarCoreApp.cpp:344-347` |
| N11 | intent | Real-time build defaults: Release if no build type, `-mtune=native` only for native (non-cross) Release builds. | once | `Core/CMakeLists.txt:10-16,183-188` |
| N12 | intent | No version string in code; project `VERSION 0.1.0` is stale; release identity is the squashed release commit. | once | `Core/CMakeLists.txt:4`; `grep -rn '1\.6' src qml` empty in both repos |

## Final rules

Corrected list. All evidence `@upstream-1.6.0`. `Core/` = Apertar-Core repo root, `UI/` = Apertar-UI repo root.

| Id | Kind | Rule | Strength | Evidence | A violation looks like |
| --- | --- | --- | --- | --- | --- |
| S1 | structure | List every new translation unit by hand in the repo's main target (Core `add_executable(apertar-core` .cpp only; UI `add_executable(ApertarUI` .cpp and .hpp); never glob. | usually (exception: `UI/src/PreviewExposureReference.hpp` unlisted; dead `Core/src/lossydng/LossyJpeg12.cpp`) | `Core/CMakeLists.txt:69-96`; `UI/CMakeLists.txt:63-130` | `file(GLOB ...)`, a new library target for app code, or a new file not in the list |
| S2 | structure | Add a new QML file to both `APERTAR_QML_FILES` and `qml.qrc`. | usually (dead `UI/qml/InlineChoice.qml` in neither) | `UI/CMakeLists.txt:19-52`; `UI/qml.qrc:3-33` | QML in one list only: works with AOT, missing without (or reverse) |
| S3 | structure | Put FFmpeg-based code in a lazily `dlopen`ed MODULE with `PREFIX ""`, a C ABI header, an ABI/version check and env -> exe dir -> fixed path search; never link FFmpeg into a main binary. | always (3 modules) | `Core/CMakeLists.txt:143-170`; `Core/src/prores/ProresRecorder.cpp:29-48`; `Core/src/video/LibavH264EncoderClient.cpp:17-32,105-123`; `UI/CMakeLists.txt:132-147`; `UI/src/VideoPlayback.cpp:16-37` | `target_link_libraries(apertar-core ... avcodec)`; plugin without ABI symbol |
| S4 | structure | Find optional deps QUIET and turn absence into `<PROJECT>_HAS_X=0`; usually add `message(STATUS)` naming the package and return an operator error from the disabled path. | usually (libcamera/JPEG off have no message; libcamera error names no package) | `Core/CMakeLists.txt:114-138,172`; `UI/CMakeLists.txt:146,236-242`; `Core/src/camera/CameraController.cpp:5395` | REQUIRED for an optional feature; `#ifdef` without a `_HAS_X=0` definition |
| S5 | structure | Decide recording capabilities once in Core from the DT compatible string, publish `recording_capabilities` in state, enforce in Core, mirror in touch UI and WebUI. | usually (UI decides its own Pi 3 preview path) | `Core/include/apertar/core/RecordingCapabilities.hpp:18-106`; `Core/src/ApertarCoreApp.cpp:7876`; `UI/src/ApertarControlBridge.cpp:1286-1294`; exception `UI/src/PreviewWindowRenderer.cpp:33-41` | UI or WebUI detecting the board to allow/deny a recording format |
| S6 | structure | In Core, detect the platform with header-only inline functions: pure `...FromCompatible(string)` plus a static-cached reader of `/sys/firmware/devicetree/base/compatible` then `/proc/device-tree/compatible`. | usually (UI and helpers read `/proc/device-tree/model`) | `Core/include/apertar/core/RecordingCapabilities.hpp:18-50`; `Core/src/camera/DefaultTuningSelection.hpp:18-50`; exceptions `UI/src/PreviewWindowRenderer.cpp:33`, `UI/src/StandbyUsbPower.cpp:59` | a new Core board check reading `model` or `/proc/cpuinfo`, uncached in a hot path |
| S7 | structure | Root work goes in a single-file, Qt-free helper `UI/src/<Name>.cpp`, target `apertar-<name>`, copied by hand to `/usr/local/libexec`, called by Core as `/usr/bin/timeout Ns /usr/bin/sudo -n <abs path> <literal verb>`, with a one-line `UI/systemd/apertar-<name>.sudoers` listing every verb; Core checks the helper exists. | always (2 instances) | `UI/CMakeLists.txt:150-155`; `UI/systemd/apertar-standby-*.sudoers:1`; `Core/src/ApertarCoreApp.cpp:1541-1550,9152` | root daemon, `sudo` with a wildcard, helper taking a path argument |
| S8 | structure | Call simple privileged system tools directly with `sudo -n` from Core or UI and map failure to an operator sentence. | usually | `Core/src/ApertarCoreApp.cpp:3031,3205-3212,3239-3292,3609-3636`; `UI/src/MediaStatusBridge.cpp:727,978` | `pkexec`, interactive sudo, raw stderr shown to the operator |
| S9 | structure | Keep system integration files flat in `UI/systemd/`; Core holds only `config/` and `scripts/`; CMake `install()` covers binaries and modules only; units, sudoers, polkit, udev and sudo helpers are installed by the image or by hand. | always | `git ls-files UI/systemd`, `git ls-files Core`; `Core/CMakeLists.txt:190-196`; `UI/CMakeLists.txt:144` | an installer script, `install(FILES ... /etc/systemd)`, unit files in Core |
| S10 | structure | Write launch and deployment scripts in bash at a repo root (UI) or `Core/scripts/`, configured by `${1:-default}` and `APERTAR_*` env vars with `${VAR:-default}`. | usually | `UI/run_pi_direct.sh:5-14`; `UI/sync_pi_runtime.sh:5-10`; `UI/finish_plymouth_handoff.sh:5-8`; `Core/scripts/start-apertar-core.sh:4-6`; `UI/wait_for_ui_core_start.sh:5-6` | Python/other language launcher, hard-coded values without override |
| S11 | structure | Assume the image layout: user `pi`; `apertar-hardware.conf` search env -> `/home/pi` -> `/boot/firmware` -> `/boot`; build dirs and tuning under `/home/pi`; settings under `$XDG_CONFIG_HOME` or `$HOME/.config`. | usually | `Core/src/hardware/GpioInput.cpp:55-76`; `Core/src/video/LibavH264EncoderClient.cpp:29`; `Core/src/camera/CameraController.cpp:346-350`; `UI/systemd/apertar-network.service:7-14` | new config root (`/etc/apertar`), different search order |
| S12 | structure | Each process and hardware class carries its own copy of shared plumbing (config path list, hardware-config template, gpiochip scorer, fan writer, power-error text, CFE watcher); do not consolidate unasked. | always | 14 files read `APERTAR_HARDWARE_CONFIG`; `Core/src/hardware/GpioInput.cpp:238`, `TriggerOutput.cpp:201`, `RecordingIndicatorOutput.cpp:198`; `Core/src/ApertarCoreApp.cpp:3042` vs `UI/src/SystemActionBridge.cpp:64` | a new shared library/header refactor of these copies |
| S13 | structure | No test targets and no CI; test hooks only as `#ifndef APERTAR_*_TEST` around helper `main`. | always | `Core/CMakeLists.txt`, `UI/CMakeLists.txt` (no `enable_testing`); `UI/src/StandbyUsbPower.cpp:241`; `UI/src/StandbyLowPower.cpp:148` | gtest/ctest targets, `.github/workflows` added to the repo build (new ground, must be argued) |
| S14 | structure | UI builds in-tree to tracked `build/` (551 tracked files) and ships prebuilt `mesa-minimal/`, no `.gitignore`; Core builds in `../ApertarCore-build`. Do not commit rebuilt artifacts or remove the tracked ones unasked. | once | `git ls-files build`; `UI/README.md:249-260`; `UI/sync_pi_runtime.sh:8-10`; `Core/README.md:206-207` | a diff full of `build/` churn, or a commit deleting `build/` and adding `.gitignore` |
| S15 | structure | Grant `pi` narrow rights with polkit actions and udev group permissions; services run `User=pi`. | usually (sudo helpers are the exception) | `UI/systemd/49-apertar-network.rules:1-12`; `UI/systemd/90-apertar-backlight.rules:1-2`; `UI/systemd/apertar-network.service:7-8` | running a service as root to reach NetworkManager or sysfs |
| S16 | structure | Runtime-only system libraries are `dlopen`ed by soname; headers are the only build dependency. | once | `Core/CMakeLists.txt:28`; `Core/src/audio/TimestampedAudioCapture.cpp:43-47` | linking a library only one feature uses into the cold-start path |
| I1 | idiom | Name env vars `APERTAR_<AREA>_<KNOB>`, read at the point of use, clamp and silently fall back to the default; developer knobs, not in READMEs. | usually (ProRes code parses with `atoi`) | `Core/src/camera/CameraController.cpp:1027-1060,1125-1135`; `Core/src/prores/ProresEncoder.cpp:1323-1326`; `Core/src/prores/ProresRecorder.cpp:61-62` | central env config object; env var documented as operator setting; unclamped value |
| I2 | idiom | Thread counts are fixed or derived from `hardware_concurrency()`, always clamped; no affinity, no RT scheduling, only bounded nice. | usually (ProRes fixed 4) | `Core/src/camera/CameraController.cpp:3323-3340,4448-4451,3708,6590-6599`; `Core/src/prores/ProresRecorder.cpp:60`; `Core/config/apertar-core-capture-priority.conf` | `SCHED_FIFO`, `pthread_setaffinity_np`, unbounded thread pool |
| I3 | idiom | Log with a component prefix: Core "ApertarCore <area> ..." (hardware classes use device name, standby uses "Apertar standby"), UI "Apertar <area>: ...", helpers/scripts "<Component>: ...". | usually (UI qWarning often unprefixed) | `Core/src/camera/CameraController.cpp:6596`; `Core/src/hardware/NeoRotary4Input.cpp:325`; `UI/src/main.cpp:245-248`; `UI/src/CfeAutomounter.cpp:634` | unprefixed logs, a logging framework, log levels |
| I4 | idiom | Enable `-Wall -Wextra -Wpedantic` per target. | usually (not on `ApertarUI`, `ApertarNetworkHelper`) | `Core/CMakeLists.txt:148,168,175-180`; `UI/CMakeLists.txt:142,153,155,166` | a new target without warnings, or global `add_compile_options` |
| I5 | idiom | Explain each non-obvious build or script choice with a 1-3 line why-comment above it. | usually | `Core/CMakeLists.txt:9-11`; `UI/CMakeLists.txt:132-133,169-171,244-246`; `UI/run_pi_direct.sh:41-44` | unexplained linker flags or env tricks |
| I6 | idiom | Shape sudo helpers as: `Paths` struct, verb whitelist with usage line, `geteuid` check, root-owned `/run/apertar-<name>` checked with `lstat`, `flock(LOCK_NB)`, exceptions -> stderr + exit 1, `main` under `#ifndef APERTAR_*_TEST`. | always (2 instances) | `UI/src/StandbyUsbPower.cpp:15-23,241-273`; `UI/src/StandbyLowPower.cpp:13-17,148-178` | helper without lock or euid check, or with Qt |
| I7 | idiom | `set -euo pipefail` in launchers; `set -u` and unconditional `exit 0` in gates that must never block boot. | always | `UI/run_pi_direct.sh:3`; `Core/scripts/start-apertar-core.sh:2`; `UI/wait_for_ui_core_start.sh:3,56`; `UI/finish_plymouth_handoff.sh:3` | gate that exits non-zero or loops unbounded |
| I8 | idiom | Vendor third-party source under `third_party/<name>/` with LICENSE and `README.apertar.md` naming upstream, commit and local changes. | once (prebuilt `mesa-minimal/` has no README) | `UI/third_party/liblj92/README.apertar.md:1-11` | copied source inline in `src/` without provenance |
| I9 | idiom | Core is C++20 with extensions off; UI is C++17. | always | `Core/CMakeLists.txt:21-23`; `UI/CMakeLists.txt:4-5` | C++20 features in UI code, or raising UI standard unasked |
| I10 | idiom | Keep legacy `CinePi` settings storage names. | always (5 sites) | `UI/src/SettingsBridge.cpp:287`; `UI/src/ApertarControlBridge.cpp:118`; `UI/src/WifiBridge.cpp:127`; `UI/src/DisplayCalibration.cpp:49`; `Core/src/ApertarCoreApp.cpp:344-347` | renaming `CinePi` to `Apertar` in QSettings or paths (loses operator settings) |
| N1 | intent | Support three board classes; refuse a clip format the board cannot sustain with a message naming the board class; coerce saved settings at load. | always | `Core/README.md:60-72`; `UI/README.md:57-67`; `Core/include/apertar/core/RecordingCapabilities.hpp:64-106`; `Core/src/camera/CameraController.cpp:588,2709,7599-7601` | Pi 5-only feature reachable on Pi 4 without refusal |
| N2 | intent | On an unrecognised platform do not guess Pi behaviour; leave tuning to libcamera and report "unknown". | usually | `Core/src/camera/DefaultTuningSelection.hpp:53,66-69` | defaulting to PiSP on unknown boards |
| N3 | intent | Probe hardware by identity, not fixed index (DRM by type/status, H.264 by driver, gpiochip by label score, IMU by bus scan); I2C default bus 1 stays overridable in hardware conf. | usually | `UI/README.md:126`; `Core/src/video/H264Hardware.hpp:37`; `Core/src/hardware/GpioInput.cpp:238-262,512`; `Core/src/hardware/Pcf8574Input.hpp:31` | hard-coded `/dev/video11`, `card1`, `gpiochip4` |
| N4 | intent | Cold-boot time is a design constraint: FFmpeg and proxy discovery out of startup, lazy binding, trimmed Mesa, readiness files. | always | `UI/CMakeLists.txt:132-133,169-171,244-249`; `UI/systemd/apertar-network-start-gate.conf:2-3` | new heavy link dep or blocking probe in UI/Core startup |
| N5 | intent | Startup gates and handoffs never block camera or recovery: bounded timeouts, skip without screen, ignore helper errors, exit 0. | always | `UI/wait_for_ui_core_start.sh:7-10,30-33,54-56`; `UI/finish_plymouth_handoff.sh:10-12,28-30`; `UI/systemd/apertar-network-start-gate.conf:2-4` | `ExecStartPre=` without `-`, unbounded wait |
| N6 | intent | Headless operation is first-class: without a screen Core and WebUI keep working and the launcher waits for hotplug. | always | `UI/run_pi_direct.sh:168-186`; `UI/wait_for_ui_core_start.sh:30-33`; `Core/README.md:5,128` | Core feature that requires the touch UI |
| N7 | intent | Keep root access narrow: sudo helpers take literal verbs only; never a path from WebUI or config; WebUI values reach root only as `shellQuote`d arguments to fixed system tools; user scripts run as `pi` without sudo. | usually (timezone string passed after empty check only) | `Core/src/ApertarCoreApp.cpp:1543,3270-3290,4334`; `Core/README.md:177` | sudo with a WebUI-supplied path or unquoted value |
| N8 | intent | Building installs nothing system-wide; READMEs say so and warn against replacing a working camera stack. | always | `Core/README.md:87,199,206-207`; `UI/README.md:244,295,305` | build step that writes `/etc`, `/boot`, overlays or libcamera |
| N9 | intent | Board-specific power features verify the exact expected topology and refuse, keeping the safe state, when anything differs. | once | `UI/src/StandbyUsbPower.cpp:59-80` | power-off without topology check |
| N10 | intent | Core and UI are released together as squashed version drops; operators update both together. | usually | `Core/README.md:306`; `UI/README.md:21`; Core log `35dbe67 1.6.0 Release`; UI log `8847105 Updated to version 1.6.0` | Core change requiring a UI change shipped alone |
| N11 | intent | Real-time build defaults: Release when no build type; `-mtune=native` only for native Release builds. | once | `Core/CMakeLists.txt:10-16,183-188` | removing the Release default or forcing `-march` |
| N12 | intent | No version string in code; `project(VERSION 0.1.0)` is stale; release identity lives in the release commit. | once | `Core/CMakeLists.txt:4`; `grep -rn '1\.6' src qml` empty | adding a version scheme unasked |

### Recipe (unchanged from reader, with corrections)

R1-R4 above stand. Corrections: R2 step 3, the UI search path is env -> exe dir -> `../lib/apertar-ui` (`UI/src/VideoPlayback.cpp:23-26`); R3 step 4, Core checks `std::filesystem::exists` on the helper before use (`Core/src/ApertarCoreApp.cpp:9152`); add no test target and no CI file (S13); do not commit `UI/build/` churn (S14).
