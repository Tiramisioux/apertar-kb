# Overview: processes and how they talk

Which process owns what, how they connect, and in what order they start. Read this first when a bug could be in more than one place.

Refs are against `upstream-1.6.0` (Apertar-Core HEAD `65ccfa8`, Apertar-UI HEAD `66d6d19`; both add only build/gitignore changes). Unit contents are from `systemctl cat` on the live Pi (Pi, 2026-10-25). Hardware: Pi 5 4 GB, HDMI display (DPI overlays disabled 2026-10-23), IMX585, CFE hat.

## Processes

| Process | Binary / unit | Runs as | Owns | Page |
| --- | --- | --- | --- | --- |
| **Core** | `/home/pi/ApertarCore-build/apertar-core --socket /tmp/apertar-core.sock --media /media/RAW`, via `/home/pi/start-apertar-core.sh`, unit `apertar-core.service` (Pi, 2026-10-25) | see [build.md](build.md) | Camera (libcamera), recording (cDNG, ProRes, H.264, MLV, audio, gyro), preview buffers, control socket, WebUI on `:8000`, hardware inputs (PCF8574, NeoRotary4, GPIO, standby power button, Grove analog), trigger and REC-LED outputs, media eject/format/speed test, standby | [core.md](core.md) |
| **UI** | `/home/pi/ApertarUI/build/Apertar-UI` started by `run_pi_direct.sh`, unit `apertar-ui-direct.service` (Pi, 2026-10-25) | `pi`, groups `video render input`, `/dev/tty1` | Touch UI, preview rendering on the main screen, UI settings (`UI.conf`), INA219 battery readout, live IMU level, Wi-Fi UI, clip playback, display standby/backlight | [ui.md](ui.md) |
| **Monitor-only UI** | Same binary with `APERTAR_MONITOR_ONLY=1`, child of `run_pi_direct.sh` | `pi` | HDMI monitor window, only when HDMI is on a **different DRM card** from the main screen | [ui.md](ui.md#external-monitor-hdmi) |
| **Network helper** | `/home/pi/ApertarUI/build/apertar-network-helper`, unit `apertar-network.service`, `After=NetworkManager` (Pi, 2026-10-25) | `pi` | Hotspot fallback when no Wi-Fi, independent of the display | [ui.md](ui.md#network-helper-vs-in-ui-wi-fi) |
| **CFE automounter** | `/usr/local/libexec/apertar-cfe-automounter`, unit `apertar-cfe-automounter.service`, `After/Wants=media-RAW.service` (Pi, 2026-10-25) | root (**unconfirmed**, `systemctl show -p User apertar-cfe-automounter`) | CFE hat buttons + LED over I2C, NVMe mount/eject at `/media/RAW`, PCIe reset | [ui.md](ui.md#apertar-cfe-automounter) |
| **Root helpers** | `/usr/local/libexec/apertar-standby-usb`, `apertar-standby-low-power` | root via `sudo -n` from Core | USB port power, CPU governor / NVMe PM / Bluetooth in standby | [ui.md](ui.md#separate-binaries-built-here) |
| **Start gate** | `/usr/local/libexec/apertar-wait-ui-core-start` (`ExecStartPre` of Core) | Core's unit | Delays Core until the UI has loaded its scene | below |
| **Python reinsert watcher** | `python3 -c <embedded script>`, spawned by Core after an NVMe eject | Core's user | Waits for the hat's insert button, resets PCIe, remounts | [core.md](core.md) |

`/usr/local/libexec` also holds `libcamera` (Pi, 2026-10-25); see [drivers.md](drivers.md).

### Core start sequence (inside the process)

| Step | Ref |
| --- | --- |
| Undo a left-over standby (low-power `restore`, USB `on`) | `Apertar-Core/src/ApertarCoreApp.cpp:6807-6819` |
| Start the preview publisher thread and the MJPEG thread (for the WebUI) | `:6825`, `:6834` |
| **Open the camera** (`camera_.start`) | `:6838` |
| Bind the **control socket** | `:6859` |
| Start the **WebUI** (`--web-port`, default 8000, bind 0.0.0.0) | `:6869-6879`; `Apertar-Core/src/main.cpp:34-35` |
| Start trigger output, PCF8574, NeoRotary4, GPIO, standby power button, Grove analog, REC LED | `:6881-6896` |
| Publish `camera_state ready` | `:6901` |

**Consequence:** the socket only appears after the camera opened. Until then the UI shows `Waiting for ApertarCore control socket...` (`Apertar-UI/src/ApertarControlBridge.cpp:1040`) and retries every second (`:17`).

## How they talk

| From → to | Channel | What | Ref |
| --- | --- | --- | --- |
| UI → Core | Unix socket `/tmp/apertar-core.sock`, JSON lines | `set_*`, `record_*`, `get_state`, `preview_subscribe`, eject/format, `user_activity` | [ui.md](ui.md#how-the-ui-talks-to-core) |
| Core → all socket clients | Same socket, broadcast | `event` lines: `settings`, `recording`, `standby`, `audio_level`, `hardware_action`, `preview_frame`, … | `Apertar-Core/src/ipc/ControlServer.cpp:172-193` |
| Core → UI | Same socket, `SCM_RIGHTS` | Preview dma-buf fds with `preview_buffer` | `Apertar-Core/src/ApertarCoreApp.cpp:10891-10944` |
| Browser → Core | HTTP `:8000` | WebUI (HTML compiled into Core) and MJPEG preview | `Apertar-Core/src/web/WebControlPage.cpp`; [build.md](build.md#webui-icons) |
| UI ↔ Core ↔ monitor UI ↔ network helper | File `~/.config/CinePi/UI.conf` | UI-side settings (aids, photo, audio, hotspot SSID/password). Core rewrites it for WebUI changes; readers file-watch it | `Apertar-UI/src/SettingsBridge.cpp:411-431`; `Apertar-Core/src/ApertarCoreApp.cpp:341-348`, `:1850-1861` |
| all → all | File `apertar-hardware.conf` (`/home/pi/`, then `/boot/firmware/`, `/boot/`) | Hardware config. Read by Core, UI, automounter; written by the UI (default file, IMU settings) | [config.md](config.md) |
| Main UI → monitor UI | Unix socket `$XDG_RUNTIME_DIR/apertar-display-$UID/monitor-state.sock` | Camera page active, shutdown popup, media, REC, timecode | `Apertar-UI/run_pi_direct.sh:219`; `Apertar-UI/src/ExternalMonitorRuntimeBridge.cpp:14-20` |
| Network helper → UI | File `/run/apertar-network/managed` | "Helper is in charge": the UI's own auto-hotspot stands down | `Apertar-UI/src/NetworkHelper.cpp:21-23`; `Apertar-UI/src/WifiBridge.cpp:478-484` |
| Automounter → UI | File `/run/apertar-cfe/ready`; `/proc/self/mountinfo` | Native automounter present; mount state is polled, not signalled | `Apertar-UI/src/CfeAutomounter.cpp:530-531`; `Apertar-UI/src/MediaStatusBridge.cpp:266-274` |
| Core → root helpers | `sudo -n /usr/local/libexec/…` with fixed args | Standby power | `Apertar-Core/src/ApertarCoreApp.cpp:1541-1550`; sudoers `Apertar-UI/systemd/*.sudoers` |
| UI / network helper → NetworkManager | `nmcli` subprocess, polkit rule for `pi` | Wi-Fi, hotspot | `Apertar-UI/src/WifiBridge.cpp:541`; `Apertar-UI/systemd/49-apertar-network.rules` |
| Core, UI, automounter → I2C | `/dev/i2c-N` directly | Each opens the bus itself; no arbitration between processes | [config.md](config.md), `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md` |

```
                    browser (phone/laptop)
                         | HTTP :8000 (WebUI, MJPEG)
                         v
 +-----------------------------------------------+      sudo -n      +------------------------------+
 | apertar-core  (apertar-core.service)          |------------------>| /usr/local/libexec/          |
 |  libcamera, recorders, WebUI, HW inputs       |                   |  apertar-standby-usb         |
 |  control socket /tmp/apertar-core.sock        |                   |  apertar-standby-low-power   |
 +-----------------------------------------------+                   +------------------------------+
     ^  JSON lines + events      ^  preview fds (SCM_RIGHTS)
     |                           |                    ~/.config/CinePi/UI.conf   (shared settings file)
     |                           |                    ~/apertar-hardware.conf    (shared hardware config)
 +---+---------------------------+---------------+
 | Apertar-UI  (apertar-ui-direct.service)       |  monitor-state.sock   +------------------------------+
 |  run_pi_direct.sh -> Apertar-UI (main screen) |---------------------->| Apertar-UI monitor-only      |
 |  EGLFS/KMS on tty1, evdev touch               |  (split DRM only)     |  (HDMI on another DRM card)  |
 +-----------------------------------------------+                       |  own Core connections        |
        |  /run/apertar-ui/core-start-ready                              +------------------------------+
        |  /run/apertar-ui/main-ui-ready
        v
 apertar-wait-ui-core-start (Core ExecStartPre)     finish_plymouth_handoff.sh (UI ExecStartPost)

 +--------------------------------+  /run/apertar-network/managed   +-------------------------------+
 | apertar-network-helper         |  nmcli -> NetworkManager        | apertar-cfe-automounter       |
 |  hotspot fallback, no display  |                                 |  I2C 0x34 buttons/LED, NVMe   |
 +--------------------------------+                                 |  mount -> /media/RAW          |
                                                                    |  /run/apertar-cfe/ready       |
                                                                    +-------------------------------+
```

## Startup order and readiness files

| # | Who | What | Wait gate | Ref |
| --- | --- | --- | --- | --- |
| 1 | `apertar-ui-direct` `ExecStartPre` | Remove `UI.conf.lock`, `core-start-ready`, `main-ui-ready`; `plymouth deactivate` | none | Pi, 2026-10-25 |
| 2 | `run_pi_direct.sh` | Pick connectors, write KMS config, export env, start `Apertar-UI` | none | `Apertar-UI/run_pi_direct.sh:83-228` |
| 3 | `Apertar-UI` | Load `Main.qml`, then write **`/run/apertar-ui/core-start-ready`** | none | `Apertar-UI/src/main.cpp:397`, `:405-420` |
| 3h | `run_pi_direct.sh` (no screen) | Writes `headless-ready` and `core-start-ready` itself, then polls for a screen | none | `run_pi_direct.sh:168-186` |
| 4 | `apertar-core` `ExecStartPre` | `apertar-wait-ui-core-start /run/apertar-ui/core-start-ready 8` | ≤8 s; skipped if no connected display; always exits 0 | Pi, 2026-10-25; `Apertar-UI/wait_for_ui_core_start.sh:21-56` |
| 5 | `apertar-core` | Camera open → socket → WebUI → HW inputs | none | `ApertarCoreApp.cpp:6838-6901` |
| 6 | `Apertar-UI` | First frame swapped → write **`/run/apertar-ui/main-ui-ready`**; +250 ms deferred device info and INA219 | none | `main.cpp:463-499` |
| 7 | `apertar-ui-direct` `ExecStartPost` | `finish_plymouth_handoff.sh /run/apertar-ui/main-ui-ready` → `plymouth quit --retain-splash` | ≤20 s for `main-ui-ready` or `headless-ready` | Pi, 2026-10-25; `Apertar-UI/finish_plymouth_handoff.sh:5-28` |
| 8 | `run_pi_direct.sh` (split DRM) | Start the monitor-only process | waits for `main-ui-ready`, polls 0.5 s | `run_pi_direct.sh:296-305` |
| 9 | UI bridges | Connect to the socket, `preview_subscribe`, `get_state` | retry every 1 s until step 5 binds | `ApertarControlBridge.cpp:17`, `ApertarPreviewSocketClient.cpp:16-22` |
| 10 | `apertar-network` | Network helper. The repo's drop-in would gate it on `main-ui-ready` (≤8 s) | **unconfirmed** on the Pi (`systemctl cat apertar-network`) | `Apertar-UI/systemd/apertar-network-start-gate.conf:4` |
| – | `apertar-cfe-automounter` | Mount at start if the NVMe is present, then write `/run/apertar-cfe/ready` | `After/Wants=media-RAW.service` | `CfeAutomounter.cpp:520-531` |

Why the gates exist: Core's camera open and Qt's cold start both read a lot from the SD card. Core waits for the UI's scene so the first screen appears sooner (`apertar-network-start-gate.conf:2-3` states the same intent for networking).

Unit-level ordering (`After=`, `Wants=` between `apertar-core` and `apertar-ui-direct`) is **unconfirmed**. Run `systemctl show -p After,Wants,WantedBy apertar-core apertar-ui-direct`.

`media-RAW.service` is not in either repo. **Unconfirmed** what it does: `systemctl cat media-RAW.service`.

## Who owns this bug

| Symptom | First suspect | Look at | Page |
| --- | --- | --- | --- |
| Boot splash stays ~20 s, then black or UI | UI did not present a frame (wrong card, EGL failure) | `journalctl -b -u apertar-ui-direct \| grep 'direct display\|startup'` | [ui.md](ui.md#run_pi_directsh) |
| Touch UI on the wrong screen, HDMI shows the 720x720 layout | Connector selection + `[display]` | `run_pi_direct.sh:138-166`; `[display] ui_width/ui_height/ui_layout/hdmi_external_only` | [ui.md](ui.md#run_pi_directsh), [config.md](config.md) |
| UI says "Waiting for ApertarCore control socket..." | Core not running or camera open failed | `systemctl status apertar-core`, `journalctl -u apertar-core` | [core.md](core.md) |
| Controls work, preview black | Core preview publisher, or UI EGL import | UI log `eglCreateImageKHR failed` (`PreviewWindowRenderer.cpp:1771`); Core log | [ui.md](ui.md#preview-frame-delivery), [core.md](core.md) |
| UI freezes for seconds after Stop or Format | Synchronous socket command on the GUI thread | `ApertarControlBridge.cpp:1013-1106`, `MediaStatusBridge.cpp:1192` | [ui.md](ui.md#sendcorecommand-how-a-set_-is-sent) |
| Recording fails, dropped-frame warning, bad files | Core | `journalctl -u apertar-core` | [core.md](core.md) |
| Sensor mode or bit depth missing | Driver / Core mode table | — | [drivers.md](drivers.md), [core.md](core.md) |
| WebUI not reachable | Core web server, or no network | `curl -sI http://apertar.local:8000/`; `systemctl status apertar-network` | [core.md](core.md) |
| Hotspot never appears | Network helper | `journalctl -u apertar-network`; `[network] hotspot_delay_seconds` | [ui.md](ui.md#network-helper-vs-in-ui-wi-fi) |
| WebUI change (zebra, monitor mode) not shown on the touch screen | `UI.conf` sync | `SettingsBridge.cpp:411-431`; `ls -l ~/.config/CinePi/` | [ui.md](ui.md#ui-settings-that-core-also-changes-uiconf) |
| CFexpress card not mounting / eject button dead | CFE automounter, hat I2C bus | `journalctl -u apertar-cfe-automounter` (prints `bus=`); `[cfexpress_hat] bus` | [ui.md](ui.md#apertar-cfe-automounter), [config.md](config.md) |
| Encoder, buttons, PCF8574 dead | Core hardware inputs, I2C bus number | `i2cdetect -l`; `[neorotary4]`, `[pcf8574]` | [core.md](core.md), [config.md](config.md) |
| Battery % missing on the touch screen | UI `Ina219Bridge` (`[ina219] bus` default 4) | `Ina219Bridge.cpp:45-46` | [ui.md](ui.md), [config.md](config.md) |
| Horizontal level wrong or missing | UI `GyroConfigBridge` (polls the IMU itself) | `GyroConfigBridge.cpp:1100`; `[imu]` | [ui.md](ui.md) |
| HDMI monitor shows nothing | Monitor-only process or `ExternalMonitorManager`, Settings "External monitor", not on camera page | `journalctl -u apertar-ui-direct \| grep 'monitor'` | [ui.md](ui.md#external-monitor-hdmi) |
| Standby does not cut USB/CPU power | Core → sudo helper | `sudo -n -l`; `ls /run/apertar-standby-*` | [core.md](core.md), [build.md](build.md) |
| UI change "did nothing" after rebuild | QML is compiled in; or runtime mirror | `cmake --build`, restart; `run_pi_direct.sh:13-39` | [build.md](build.md) |

## Findings across processes

| Finding | Status | Ref |
| --- | --- | --- |
| After a UI or WebUI eject, Core always spawns its embedded Python reinsert watcher, even when `apertar-cfe-automounter` (which watches the same buttons) is running. The UI's own copy checks `/run/apertar-cfe/ready` first; Core's does not | **probable**. Settle: eject, then `pgrep -af 'python3 -c'` | `Apertar-Core/src/ApertarCoreApp.cpp:3742`, `:3380-3596`; `Apertar-UI/src/MediaStatusBridge.cpp:747` (dead code) |
| Core broadcasts every event, including per-frame `preview_frame`, to every client. Non-preview clients parse them for nothing | confirmed in code | `ControlServer.cpp:172-193`; `ApertarControlBridge.cpp:1572-1588` |
| A client that stops reading is dropped (`MSG_DONTWAIT`); a partial write leaves a broken line | confirmed in code | `ControlServer.cpp:23-29` |
| Up to 32 concurrent socket clients; the 33rd is closed on accept | confirmed in code | `ControlServer.cpp:203-210` |
| Core's `help` list omits commands the UI uses (`user_activity`, `audio_capabilities`, `get_media_test_state`, `enter_standby`, `wake`, `apply_preset`) | confirmed in code | `ApertarCoreApp.cpp:9216` vs `:9111-9174`, `:10031`, `:10230`, `:10608` |
| UI, Core and automounter each parse `apertar-hardware.conf` with their own code and defaults | confirmed in code | [config.md](config.md); `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md` §6.6 |

## Confirmed on the Pi (2026-10-25, read-only checks)

| Question | Answer |
| --- | --- |
| Is the network start-gate drop-in (`systemd/apertar-network-start-gate.conf`) installed? | **No.** `systemctl cat apertar-network` shows only `/etc/systemd/system/apertar-network.service`, so the network helper does not wait for `main-ui-ready` |
| Is `/usr/local/libexec/apertar-wait-ui-core-start` the repo's `wait_for_ui_core_start.sh`? | **Yes**, byte-identical (`cmp`) |
| Which user runs `apertar-cfe-automounter`? | **root** (`User=` empty) |
| What is `media-RAW.service`? | `/etc/systemd/system/media-RAW.service`: oneshot `/usr/local/bin/mount-raw.sh` ("Mount RAW storage (NVME-RAW or USB-RAW)"), not in either repo |
| `After=`/`Wants=` between `apertar-core` and `apertar-ui-direct`? | **None.** Ordering comes only from the readiness file and Core's `ExecStartPre` wait gate (8 s timeout) |
| Does Core run with `HOME=/home/pi` (so it shares the UI's `UI.conf`)? | **Yes**, `HOME=/home/pi` in the running process environment |
| Is `python3-smbus` installed (embedded CFE watcher)? | **Yes**: `python3-smbus 4.4-2`, `python3-smbus2 0.4.3-1` |
| Can user `pi` read the journal? | **No**: `journalctl -u …` says "insufficient permissions". Use `sudo journalctl`, or add `pi` to the `systemd-journal` group once |
| DRM connectors at check time | `card1-HDMI-A-1`, `card1-HDMI-A-2` both `disconnected` (no DPI connector since the overlays were removed) |
