# Apertar config/state files: research notes for `config.md`

Scope: `Apertar-Core` at HEAD 65ccfa8 and `Apertar-UI` at HEAD 66d6d19, plus the three READMEs. I skipped `Apertar-UI/build/`, `mesa-minimal/` and `third_party/`. Every reference below is `repo/path:line`, relative to `~/Documents/Apertar`. "UNCONFIRMED" means I inferred it and did not check it in code (usually Qt/NetworkManager library behaviour or systemd units that are not in the repos).

Three of the brief's assumptions turned out wrong:
- **No shell script parses `apertar-hardware.conf`.** `run_pi_direct.sh`, `wait_for_ui_core_start.sh`, `finish_plymouth_handoff.sh` and `sync_pi_runtime.sh` contain no grep/awk/sed on it. The only `awk` is the ldd parser at `Apertar-UI/sync_pi_runtime.sh:48`.
- **`SettingsBridge.cpp` and `GyroConfigBridge.cpp` embed no full template.** `GyroConfigBridge` only writes a one-line header when the file is empty (`Apertar-UI/src/GyroConfigBridge.cpp:1587-1590`).
- **No README has a full template.** There are fragments only: `Apertar-Beta/README.md:119-122` (`[network]`) and `Apertar-Core/README.md:169-173` (`P0=` examples).

The real full templates are **three**: Core `ApertarCoreApp.cpp`, UI `DisplayConfigBridge.cpp` and UI `Ina219Bridge.cpp` (see §3).

---

## 1. Every config/state file read or written

### 1a. Persistent user/config files

| # | Path (as derived) | Format | Reader(s) | Writer(s) | Key code |
|---|---|---|---|---|---|
| 1 | **`apertar-hardware.conf`**. Candidate order: `$APERTAR_HARDWARE_CONFIG` → `/home/pi/apertar-hardware.conf` → `/boot/firmware/apertar-hardware.conf` → `/boot/apertar-hardware.conf` | INI. Each component has its own hand-written parser; the UI uses QSettings for 3 sections; two embedded Python helpers use `configparser` | Core (8 parsers), UI, cfe-automounter. network-helper reads `[network]` only | Core: WebUI `POST /api/config`, IMU commands. UI: first-run template, gyro UI | Candidate lists: `Apertar-Core/src/ApertarCoreApp.cpp:4251-4269`, `Apertar-Core/src/hardware/Pcf8574Input.cpp:55-76` (copied in every hardware/*.cpp), `Apertar-UI/src/DisplayConfigBridge.cpp:20-39`, `Apertar-UI/src/Ina219Bridge.cpp:48-67`, `Apertar-UI/src/GyroConfigBridge.cpp:193-210`, `Apertar-UI/src/CfeAutomounter.cpp:114-129`. Python: `Apertar-Core/src/ApertarCoreApp.cpp:3397-3411`, `Apertar-UI/src/MediaStatusBridge.cpp:765-780` |
| 1-exc | **Exceptions to the candidate list.** (a) WifiBridge reads only `$APERTAR_HARDWARE_CONFIG` or `/home/pi/...`, with no /boot fallback (`Apertar-UI/src/WifiBridge.cpp:21-23`). (b) The Core "editable" path (WebUI editor and run_script) is env or `/home/pi/...` only (`Apertar-Core/src/ApertarCoreApp.cpp:4271-4276`, used at `:5292`, `:5343` and `:8663`). (c) The UI first-run template is always written to `/home/pi/apertar-hardware.conf`, ignoring env (`Apertar-UI/src/DisplayConfigBridge.cpp:43`, `Apertar-UI/src/Ina219Bridge.cpp:71`) | | | | |
| 2 | **`apertar-hardware.conf.bak`** and **`.tmp`** next to the editable path | copy | — | Core WebUI save | `Apertar-Core/src/ApertarCoreApp.cpp:5359-5377` |
| 3 | **`<hwconf>.tmp`** (same name) | — | — | Core IMU writers | `Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:687-710` and `:816-839` |
| 4 | **`apertar-color-profiles.conf`**: `$APERTAR_COLOR_PROFILE_CONFIG`, else `/home/pi/apertar-color-profiles.conf` | INI, own parser | Core only; reloaded when mtime changes | nobody (no template anywhere) | `Apertar-Core/src/color/ColorProfileConfig.cpp:232-237`, `:312-375`, `:377-405` |
| 5 | **UI shared settings** `UI.conf`: `$XDG_CONFIG_HOME/CinePi/UI.conf`, else `$HOME/.config/CinePi/UI.conf`. Core falls back to `/tmp/CinePi-UI.conf` if HOME is unset | QSettings INI (`[General]` plus a `[camera]` group) | UI (`SettingsBridge`, `ApertarControlBridge`, `WifiBridge`), network-helper (`WifiBridge`), Core (`[General]` only) | UI via QSettings; Core via its own line editor plus a QLockFile-compatible lock | UI: `Apertar-UI/src/SettingsBridge.cpp:287`, `Apertar-UI/src/ApertarControlBridge.cpp:118`, `Apertar-UI/src/WifiBridge.cpp:127`. Core: `Apertar-Core/src/ApertarCoreApp.cpp:341-348` (path), `:1641-1813` (read), `:1815-1848` (raw map), `:1850-1935` (write); lock in `Apertar-Core/src/util/SettingsFile.hpp:58-118` |
| 6 | **`UI.conf.lock`** | QLockFile | — | UI (Qt) and Core | `Apertar-Core/src/util/SettingsFile.hpp:61` |
| 7 | **Core camera settings**: `$XDG_CONFIG_HOME/apertar-core/camera_settings.conf`, else `$HOME/.config/apertar-core/camera_settings.conf`, else `/tmp/apertar-core-camera_settings.conf` | flat `key=value`, no sections. Prefixes `profile.<cdng/mlv/h264/prores/still>.` | Core | Core (async debounced worker, `atomicWrite`) | `Apertar-Core/src/camera/CameraController.cpp:342-353`, `:616-740` (load), `:742-791` (write), `:793-881` (persister), `:8725-8732` |
| 8 | **Display calibration**: `~/.config/CinePi/DisplayCalibration.conf` (QSettings `"CinePi","DisplayCalibration"`) | QSettings INI, groups `[builtin]` and `[hdmi]` | UI | UI | `Apertar-UI/src/DisplayCalibration.cpp:49`, `:115-135`, `:136-154` |
| 9 | **Standby backlight restore**: `~/.config/Apertar/StandbyBacklights.conf` (QSettings `"Apertar","StandbyBacklights"`) | QSettings INI. Key = base64url of the sysfs path; value = saved brightness or trigger | UI | UI | `Apertar-UI/src/SleepManager.cpp:56-61`, `:84-91`, `:123-140` |
| 10 | **Presets** `*.apertar-preset.json`. UI dir: `QStandardPaths::AppDataLocation/presets` = `~/.local/share/Apertar-UI/presets` (app name set at `Apertar-UI/src/main.cpp:271`, no org name), else legacy `~/.config/CinePi/UI/presets`. Core dir: first existing of `$XDG_DATA_HOME/{Apertar-UI,ApertarUI}/presets`, `~/.local/share/{Apertar-UI,ApertarUI}/presets`, `~/.config/CinePi/UI/presets`; default `~/.local/share/Apertar-UI/presets` | JSON `{"type":"apertar-preset","version":1,"name","createdAt","settings":{...}}` | UI and Core | UI (QSaveFile), Core (`atomicWrite`) | UI: `Apertar-UI/src/SettingsBridge.cpp:1937-1958`, `:2000-2004`, `:2195-2215`. Core: `Apertar-Core/src/ApertarCoreApp.cpp:5216-5260`, `:6498-6509` (import), `:6522-6697` (payload), `:6740` (save) |
| 11 | **Preset export/import on media**: `<media>/Apertar Presets/` | JSON | UI | UI | `Apertar-UI/src/SettingsBridge.cpp:1802-1818`, `:1827` |
| 12 | **ProRes ISP tuning cache**: `$HOME/.cache/apertar-prores/<profile>.json` | libcamera tuning JSON (derived) | Core / libcamera | Core (`atomicWrite`) | `Apertar-Core/src/color/ProresIspProfile.cpp:228-234` |
| 13 | **Bench tuning override**: `/home/pi/.apertar-tuning` | `NAME=VALUE`, `#` comments; re-read at every ProRes clip open; the environment wins | Core | nobody (manual) | `Apertar-Core/src/prores/ProresEncoder.cpp:770-800` |
| 14 | **Tuning files**. Default dir `$APERTAR_DEFAULT_TUNING_DIR` or `/home/pi/Tuning-Files/defaults-{pisp,vc4}`, then `/home/pi/Tuning-Files/defaults`, then `/usr/{local/,}share/libcamera/ipa/rpi/<pipeline>`. Custom: `/home/pi/Tuning-Files`, `$APERTAR_MEDIA_ROOT/Tuning-Files`, `/media/RAW/Tuning-Files`, `/media/*/Tuning-Files` | libcamera JSON | Core, UI (listing) | — | `Apertar-Core/src/camera/DefaultTuningSelection.hpp:56-78`, `Apertar-UI/src/SettingsBridge.cpp:164-175`. The selection is persisted as `tuning_file` in file 7 and `camera/tuningFile` in file 5 |
| 15 | **LUTs** (`.cube`): `/home/pi/LUTs`, `$APERTAR_MEDIA_ROOT/LUTs`, `/media/RAW/LUTs`, `/media/*/LUTs` | .cube | UI, Core | — | `Apertar-UI/src/SettingsBridge.cpp:140-162`, `Apertar-Core/src/ApertarCoreApp.cpp:5574`. The selection is persisted as `lutPreviewFile` in file 5 |
| 16 | **`/boot/firmware/config.txt`**: managed block `# BEGIN APERTAR FAN MODE` … `# END APERTAR FAN MODE` | Pi config.txt | Core, UI | Core and UI (identical block generators; installed with `sudo -n install -m 644`) | Core: `Apertar-Core/src/ApertarCoreApp.cpp:2843-2845`, `:3042-3070`, `:3104-3165`. UI: `Apertar-UI/src/SystemActionBridge.cpp:23-25`, `:64-92`, `:431-463`, `:674`. Also scanned read-only for the sensor token at `Apertar-UI/src/DeviceInfoBridge.cpp:231` |
| 17 | **`/boot/firmware/camera-selection.txt`** | text (sensor token scan) | UI | — | `Apertar-UI/src/DeviceInfoBridge.cpp:215` |
| 18 | **NetworkManager profile "Apertar Hotspot"** | NM keyfile. The path `/etc/NetworkManager/system-connections/Apertar Hotspot.nmconnection` is UNCONFIRMED (NM default) | NM | UI / network-helper via `nmcli device wifi hotspot con-name "Apertar Hotspot" ssid … password …`. The profile is deleted before every start | `Apertar-UI/src/WifiBridge.cpp:15`, `:302-319`, `:635-643` |
| 19 | **Per-clip sidecars** (not config): `<clip>_recovery.json`, gyro `.gcsv`, WAV | — | Core | Core | `Apertar-Core/src/prores/ProresRepair.cpp:172`, `Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:2232`, `Apertar-Core/src/audio/AudioRecordingSession.cpp:571` |

### 1b. Runtime/state files (`/run`, `/tmp`, XDG_RUNTIME_DIR)

| Path | Owner | Purpose | Ref |
|---|---|---|---|
| `$APERTAR_NETWORK_RUNTIME` (default `/run/apertar-network`)`/helper.lock` and `/managed` | network-helper | Single-instance lock. The `managed` marker tells the UI process to stop its own auto-hotspot | `Apertar-UI/src/NetworkHelper.cpp:14-23`, `:30`. Directory created by `RuntimeDirectory=` at `Apertar-UI/systemd/apertar-network.service:12-13` |
| `/run/apertar-network/managed` (hard-coded in the UI) | UI reads | Same marker | `Apertar-UI/src/WifiBridge.cpp:155-157`, `:479` |
| `/run/apertar-cfe/ready` | cfe-automounter writes; UI MediaStatusBridge reads | If present, the UI skips its embedded Python watcher | `Apertar-UI/src/CfeAutomounter.cpp:40`, `:245-252`; `Apertar-UI/src/MediaStatusBridge.cpp:747` |
| `/run/apertar-standby-usb/{lock,ports}` | `apertar-standby-usb` (root helper) | Ports powered off during standby | `Apertar-UI/src/StandbyUsbPower.cpp:18-23`, `:183-233`, `:255-261` |
| `/run/apertar-standby-low-power/{lock,settings}` | `apertar-standby-low-power` (root helper) | Saved CPU/NVMe/rfkill state to restore | `Apertar-UI/src/StandbyLowPower.cpp:15-17`, `:89-138`, `:160-166` |
| `$APERTAR_UI_READY_FILE` | UI writes after the first frame | Plymouth / network / Core gates | `Apertar-UI/src/main.cpp:463-475`. Default when the env var is unset: `run_pi_direct.sh` → `${XDG_RUNTIME_DIR:-/tmp}/main-ui-ready` (`Apertar-UI/run_pi_direct.sh:79`); `finish_plymouth_handoff.sh` → `${XDG_RUNTIME_DIR:-/run/apertar-ui}/main-ui-ready` (`:5`); network gate → `/run/apertar-ui/main-ui-ready` (`Apertar-UI/systemd/apertar-network-start-gate.conf:4`) |
| `$APERTAR_CORE_START_READY_FILE` | UI writes once root objects load; `run_pi_direct.sh` writes it when headless | Core start gate | `Apertar-UI/src/main.cpp:405-412`, `Apertar-UI/run_pi_direct.sh:172-175`. Gate default `/run/apertar-ui/core-start-ready` (`Apertar-UI/wait_for_ui_core_start.sh:5`) |
| `headless-ready` (`$APERTAR_HEADLESS_READY_FILE`, default: dir of the ready file + `/headless-ready`) | run_pi_direct.sh | Plymouth handoff | `Apertar-UI/run_pi_direct.sh:80`, `:170-171`; `Apertar-UI/finish_plymouth_handoff.sh:8` |
| `${XDG_RUNTIME_DIR:-/tmp}/apertar-display-$UID/{main-kms.json,monitor-kms.json,monitor-state.sock,restart-for-hdmi-hotplug}` | run_pi_direct.sh | eglfs KMS configs and the monitor IPC socket | `Apertar-UI/run_pi_direct.sh:194-205`, `:219`, `:245-246`, `:357` |
| `$HOME/.cache/apertar-runtime/{bin,lib,qt6,mesa-minimal,apertar-runtime,ui-build.signature}` | sync_pi_runtime.sh writes; run_pi_direct.sh reads | Runtime mirror | `Apertar-UI/sync_pi_runtime.sh:7-10`, `:88`; `Apertar-UI/run_pi_direct.sh:13-38` |
| Control socket `/tmp/apertar-core.sock` | Core (`--socket`), UI (`APERTAR_CONTROL_SOCKET`) | IPC | `Apertar-Core/src/ApertarCoreApp.hpp:33`, `Apertar-Core/scripts/start-apertar-core.sh:6`, `Apertar-UI/src/ApertarControlBridge.cpp:1032`, `:1567` |
| Monitor runtime socket: default `/tmp/apertar-ui-monitor-state.sock` | UI | main ↔ monitor-only UI | `Apertar-UI/src/ExternalMonitorRuntimeBridge.cpp:14-20` |

### 1c. Core CLI flags (Core reads no config file for these)

From `Apertar-Core/src/main.cpp:46-87`, defaults in `Apertar-Core/src/ApertarCoreApp.hpp:32-38`:
- `--socket` (default `/tmp/apertar-core.sock`)
- `--media` (default `/media/RAW`)
- `--web-bind` (default `0.0.0.0`)
- `--web-port` (default `8000`; `0` disables the WebUI)
- `--simulate`

The wrapper `Apertar-Core/scripts/start-apertar-core.sh:4-21` maps env vars onto these flags.

### 1d. When each file is (re)read

- **Core hardware inputs/outputs** (trigger, PCF8574, NeoRotary4, GPIO, Grove, recording LED) are read once, in `start()` at Core start-up (`Apertar-Core/src/ApertarCoreApp.cpp:6881-6893`). There is no reload command; a Core restart is needed.
- **Core INA219**: read once per process (`static const`, `Apertar-Core/src/ApertarCoreApp.cpp:4602`).
- **Core IMU**: read on every recording, calibration or IMU command (`Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:1040`, `:1176`, `:1297`, `:1312`, `:1324`, `:1372`, `:1396`).
- **Core run_script**: read on every request (`Apertar-Core/src/hardware/HardwareScriptRunner.cpp:38-96`).
- **Color profiles**: reloaded when mtime changes (`Apertar-Core/src/color/ColorProfileConfig.cpp:377-405`).
- **UI display config**: at start-up only (`Apertar-UI/src/DisplayConfigBridge.cpp:569-573`).
- **UI INA219**: 5 s after start (`Apertar-UI/src/Ina219Bridge.cpp:449`, `:490`).
- **UI hotspot delay**: in the WifiBridge constructor only (`Apertar-UI/src/WifiBridge.cpp:129`).
- **UI gyro config**: on demand (`Apertar-UI/src/GyroConfigBridge.cpp:905`).
- **UI.conf in the UI**: watched with inotify plus a 10 s poll (`Apertar-UI/src/SettingsBridge.cpp:411-431`).

---

## 2. `apertar-hardware.conf`: sections and keys

### 2.0 How each parser behaves

| Parser | Section match | Key match | Inline comment strip | Bool words | Which file it uses |
|---|---|---|---|---|---|
| Core INA219 `Apertar-Core/src/ApertarCoreApp.cpp:4450-4506` | `lowerAscii(line) == "[ina219]"`, so spaces inside the brackets fail | lower-case | bool: yes (`#`/`;`, `:4427-4448`); integers: **no** (`:4406-4425`), so `bus=4 # x` is ignored | 1/true/yes/on/**enabled**, 0/false/no/off/**disabled** | first existing file; **returns even if the section is absent** |
| Core PCF8574 `Apertar-Core/src/hardware/Pcf8574Input.cpp:318-390` | lower-case, trimmed | lower-case | yes, the whole line is cut at the first `#` or `;` (`:338-340`) | true/yes/on/1 (`:98-106`). No "enabled" | **falls through to the next candidate if the section is absent** (`:385`) |
| Core GPIO `Apertar-Core/src/hardware/GpioInput.cpp:373-503` | `normalizeToken` (lower-case, `-`, space and `.` become `_`) | normalizeToken | yes (`:399-401`) | true/yes/on/1 | falls through (`:498`) |
| Core NeoRotary4 `Apertar-Core/src/hardware/NeoRotary4Input.cpp:355-444` | normalizeToken | normalizeToken | yes (`:375-377`) | true/yes/on/1 | falls through (`:439`) |
| Core Grove `Apertar-Core/src/hardware/GroveAnalogInput.cpp:246-355` | normalizeToken | normalizeToken | yes (`:268-270`) | true/yes/on/1 (`:115-123`) | falls through (`:350`) |
| Core trigger `Apertar-Core/src/hardware/TriggerOutput.cpp:250-360` | normalizeToken | normalizeToken | value only, `#`/`;` after whitespace (`:56-66`) | true/yes/on/1 | first existing file |
| Core recording LED `Apertar-Core/src/hardware/RecordingIndicatorOutput.cpp:247-399` | normalizeToken | normalizeToken | value only (stripInlineComment) | true/yes/on/1 | first existing file |
| Core IMU `Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:851-1033` | normalizeToken | normalizeToken | numbers/bools yes (`:223-271`); the `driver`/`sync_mode` values do **not** have comments stripped (`:888-896`) | true/yes/on/1 (`:263-271`) | first **openable** file; no is_regular_file check (`:855-858`) |
| Core run_script `Apertar-Core/src/hardware/HardwareScriptRunner.cpp:38-96` | **exact `line == "[run_script]"`**, case-sensitive (`:52`) | exact, case-sensitive | value: quote-aware; else cut at `#`/`;` (`:69-79`) | — | **editable path only** (env or /home/pi), `Apertar-Core/src/ApertarCoreApp.cpp:8663` |
| Core embedded Python (NVMe reinsert watcher) `Apertar-Core/src/ApertarCoreApp.cpp:3382-3463` | `configparser` (section names case-sensitive) | lower-case (optionxform) | bool yes, integers no | 1/true/yes/on/enabled… | first existing file |
| UI DisplayConfigBridge `Apertar-UI/src/DisplayConfigBridge.cpp:575-654` | QSettings group `display` (case-sensitive) | case-sensitive, several aliases | none (QSettings itself treats `;` as a comment: UNCONFIRMED) | true/yes/on/1 (`:419-439`) | first existing file |
| UI Ina219Bridge `Apertar-UI/src/Ina219Bridge.cpp:490-548` | QSettings group `ina219` | case-sensitive | bool yes (`:371-405`) | adds enabled/disabled | first existing file |
| UI WifiBridge `Apertar-UI/src/WifiBridge.cpp:19-35` | QSettings key `network/hotspot_delay_seconds` | case-sensitive | none | — | **env or /home/pi only** |
| UI GyroConfigBridge `Apertar-UI/src/GyroConfigBridge.cpp:905-1075` | normalizeToken, which strips comments (`:68-89`) | normalizeToken | yes | true/yes/on/1 (`:240-256`) | first `QFileInfo::exists` candidate (`:919-925`) |
| cfe-automounter `Apertar-UI/src/CfeAutomounter.cpp:131-191` | lower-case | lower-case | yes (`:66-76`) | adds enabled/disabled (`:78-90`) | first openable file (`:135-142`) |
| UI embedded Python (fallback CFE watcher) `Apertar-UI/src/MediaStatusBridge.cpp:750-831` | configparser | lower-case | bool only | as the Core Python helper | first existing file |

### 2.1 `[network]`

| Key | Type | Coded default | Parsed by | Ref |
|---|---|---|---|---|
| `hotspot_delay_seconds` | int seconds, valid 0–86400 (anything else → 60, with a warning) | 60 | UI and network-helper (WifiBridge, QSettings) | `Apertar-UI/src/WifiBridge.cpp:27-32` |

Only the UI DisplayConfigBridge template contains this section (`Apertar-UI/src/DisplayConfigBridge.cpp:59-62`). The Beta README documents it at `Apertar-Beta/README.md:119-126`.

### 2.2 `[display]` (UI only; Core never parses it)

All keys below are parsed in `Apertar-UI/src/DisplayConfigBridge.cpp`.

| Key (aliases) | Type / range | Coded default | Ref |
|---|---|---|---|
| `ui_width` (`uiWidth`, `width`) | int, 320–3840 | 720 | `:598-604`, `:14` |
| `ui_height` (`uiHeight`, `height`) | int, 320–3840 | 720 | `:605-611`, `:15` |
| `ui_layout` (`uiLayout`, `layout`, `profile`) | enum: square, landscape_compact, landscape_medium, landscape, landscape_large, portrait_compact, portrait, portrait_large, plus aliases | "auto", derived from the size | `:612-618`, `:474-524` |
| `ui_rotation` (`uiRotation`, `rotation`, `orientation`) | normal / left / right / upside_down / 90 / -90 / 270 / 180 … | normal (0°) | `:619-625`, `:526-565` |
| `controls_opacity` (`control_opacity`, `controlsOpacity`, `opacity`) | double, 0.15–1.0 | 1.0 | `:626-633`. Used only as the default for UI.conf `cameraControlsOpacity` when that key is absent (`Apertar-UI/src/main.cpp:318`, `Apertar-UI/src/SettingsBridge.cpp:456-467`) |
| `zoom_toggle_factor` | double, 1.0–4.0 | 4.0 | `:634-638`, `:18`. Consumed in `Apertar-UI/qml/CameraPage.qml:528` |
| `windowed` (`ui_windowed`, `uiWindowed`, `debug_windowed`, `debugWindowed`) | bool | false | `:639-645` |
| `hdmi_external_only` (`hdmiExternalOnly`) | bool | false | `:646-649`. Consumed in `Apertar-UI/src/main.cpp:202`, `:279` |
| `controls_mode` | — | **parsed by nobody** | Present only in the Core template (`Apertar-Core/src/ApertarCoreApp.cpp:4326`) |

### 2.3 `[ina219]`

| Key (aliases) | Type / range | Coded default | Parser | Ref |
|---|---|---|---|---|
| `enabled` | bool | true | Core and UI | `Apertar-Core/src/ApertarCoreApp.cpp:4241`, `:4484-4486`; `Apertar-UI/src/Ina219Bridge.cpp:495`, `:507` |
| `bus` (`channel`, `i2c_bus`) | int, 0–255 | 4 | Core and UI | Core `:4242`, `:4493-4495`; UI `:45`, `:509-517` |
| `address` (`addr`) | int, dec or hex, 0x03–0x77 | 0x40 | Core and UI | Core `:4243`, `:4496-4498`; UI `:46`, `:518-525` |

Both Core (`Apertar-Core/src/ApertarCoreApp.cpp:4600-4606`) and UI open the same INA219 device independently. Out-of-range values: the UI falls back to the default (`Apertar-UI/src/Ina219Bridge.cpp:424-433`); Core keeps its previous value.

### 2.4 `[cfexpress_hat]` and `[storage]`

These are parsed by cfe-automounter (`Apertar-UI/src/CfeAutomounter.cpp:164-181`), the Core Python helper (`Apertar-Core/src/ApertarCoreApp.cpp:3449-3463`) and the UI Python helper (`Apertar-UI/src/MediaStatusBridge.cpp:818-831`). The C++ Core binary itself never reads them.

| Section/key (aliases) | Type | Coded default | Ref |
|---|---|---|---|
| `cfexpress_hat.enabled` | bool | true | `Apertar-UI/src/CfeAutomounter.cpp:106`, `:165`; Python `CFE_HAT_ENABLED=True` (Core `:3393`, UI `:761`) |
| `cfexpress_hat.bus` (`channel`, `i2c_bus`) | int (0–255 in the automounter) | 10 | `Apertar-UI/src/CfeAutomounter.cpp:38`, `:167-168`, `:184-185` |
| `cfexpress_hat.address` (`addr`) | int, 0x03–0x77 | 0x34 | `Apertar-UI/src/CfeAutomounter.cpp:39`, `:169-170`, `:186-187` |
| `storage.mount_path` | absolute path | /media/RAW | `Apertar-UI/src/CfeAutomounter.cpp:109`, `:172-175`, `:188-189`. **Core's helper ignores it whenever `APERTAR_MEDIA_ROOT` is set, and Core always sets it** to the `--media` path when spawning the helper (`Apertar-Core/src/ApertarCoreApp.cpp:3457`, `:3594-3595`) |
| `storage.pcie_controller` | string | 1000110000.pcie | `Apertar-UI/src/CfeAutomounter.cpp:110`, `:176-179` |

### 2.5 `[run_script]` (Core)

Parsed in `Apertar-Core/src/hardware/HardwareScriptRunner.cpp`.

| Key | Type | Default | Ref |
|---|---|---|---|
| `path` | absolute path to a Bash script. This is slot 1, but it is ignored if `path1` appears anywhere in the section | empty | `:59-69` |
| `path1` … `path5` | absolute path; may be quoted | empty | `:60-80`. Any other key starting with `path` (for example `path6`) **throws** (`:64`). The file must be ≤ 256 KiB (`:40-41`). Scripts are capped at 5 (`Apertar-Core/src/hardware/ButtonActionList.hpp:15`) |

These are invoked by button actions `run_script` / `script` / `run_scriptN` / `scriptN` (`Apertar-Core/src/hardware/ButtonActionList.hpp:19-32`).

### 2.6 `[pcf8574]` (alias `[pcf8574_buttons]`), Core

Parsed in `Apertar-Core/src/hardware/Pcf8574Input.cpp:318-390`; defaults in `Apertar-Core/src/hardware/Pcf8574Input.hpp:28-38`.

| Key (aliases) | Type / range | Coded default | Ref |
|---|---|---|---|
| (section present) | — | **enabled = true** when the section exists (`:347-351`); false otherwise | |
| `enabled` | bool | see above | `:364-365` |
| `bus` (`channel`, `i2c_bus`) | 0–255 | **1** | `:366-368`, hpp `:31` |
| `address` (`addr`) | 0x03–0x77 | 0x20 | `:369-371` |
| `poll_ms` (`poll_interval_ms`) | clamped 10–1000 | 40 | `:372-374` |
| `debounce_ms` | clamped 0–1000 | 60 | `:375-377` |
| `active_low` | bool | true | `:378-379` |
| `pinN`, `pin_N`, `gpioN`, `gpio_N`, `pN` (N = 0–7; optional suffix `_action`/`_function`) | action list, up to 6 actions (`Apertar-Core/src/hardware/ButtonActionList.hpp:14`) | empty | `:108-138`, `:380-381` |

`recindicatorled` on a pin is also picked up by RecordingIndicatorOutput (`Apertar-Core/src/hardware/RecordingIndicatorOutput.cpp:293-313`). `bus`/`address` are also read by TriggerOutput (`Apertar-Core/src/hardware/TriggerOutput.cpp:289-298`, keys `bus`/`address` only; no aliases, and the `pcf8574_buttons` section alias is not recognised) and by RecordingIndicatorOutput (`:293-303`, with aliases).

### 2.7 `[gpio_buttons]` (aliases `[gpio]`, `[grove_digital]`, `[grove_buttons]`) and `[gpio_encoders]` (alias `[grove_encoders]`), Core

Parsed in `Apertar-Core/src/hardware/GpioInput.cpp:373-503`; defaults in `Apertar-Core/src/hardware/GpioInput.hpp:29-56`.

| Key | Type | Coded default | Ref |
|---|---|---|---|
| `enabled` (one flag per section) | bool | **false** (the section's presence does not enable it) | `:388-389`, `:426-430`, `:482-496` |
| `chip` (`gpiochip`, `gpio_chip`) | path or "auto" | auto | `:431-432`. **Shared** by the buttons and encoders sections; the last one wins |
| `active_low` | bool | true | `:433-434` (shared) |
| `pull` (`bias`) | token | up | `:435-436` (shared) |
| `poll_ms` (`poll_interval_ms`) | 2–1000 | 12 | `:437-439` (shared) |
| `debounce_ms` | 0–1000 | 60 | `:440-442` (shared) |
| Buttons: `gpioN` / `gpio_N` / `pinN` / `bcmN` / `dN` / `d_N` / `grove_dN` (N = 0–63; optional `_action`/`_function` suffix) | action list | — | `:209-236`, `:443-448` |
| Encoders: `encoderN_*` / `encN_*` / `rotaryN_*` (N = 0–7). Fields: `a` / `gpio_a` / `pin_a` / `clk`; `b` / `gpio_b` / `pin_b` / `dt`; `cw` / `clockwise` / `right` / `up` / `plus`; `ccw` / `counter_clockwise` / `counterclockwise` / `left` / `down` / `minus`; `press_gpio` / `button_gpio` / `push_gpio` / `switch_gpio` / `sw`; `press` / `button` / `push` / `click`; `invert` / `invert_direction` / `reverse_direction`; `steps_per_event` / `steps` / `detent_steps` (1–8) | | steps = 4 | `:266-282`, `:449-479`, hpp `:34-43` |

### 2.8 `[neorotary4]` (aliases `[neo_rotary4]`, `[neo_rotary_4]`), Core

Parsed in `Apertar-Core/src/hardware/NeoRotary4Input.cpp:355-444`; defaults in `Apertar-Core/src/hardware/NeoRotary4Input.hpp:36-48`.

| Key | Range | Coded default | Ref |
|---|---|---|---|
| (section present) | | enabled = true | `:386-390` |
| `enabled` | bool | | `:403-404` |
| `bus` (`channel`, `i2c_bus`) | 0–255 | 1 | `:405-407` |
| `address` (`addr`) | 0x03–0x77 | 0x49 | `:408-410` |
| `poll_ms` (`poll_interval_ms`) | 10–1000 | 30 | `:411-413` |
| `debounce_ms` | 0–1000 | 60 | `:414-416` |
| `invert_direction` (`invert`, `reverse_direction`) | bool | false | `:417-418` |
| `reset_on_start` | bool | false | `:419-420` |
| `max_events_per_poll` | 1–32 | 8 | `:421-423` |
| `encoderN_{cw,ccw,press}` (N = 0–3; same field aliases as GPIO) | action | — | `:222-257`, `:424-435` |

### 2.9 `[grove_analog]` (aliases `[grove_adc]`, `[analog_controls]`), Core

Parsed in `Apertar-Core/src/hardware/GroveAnalogInput.cpp:246-355`; defaults in `Apertar-Core/src/hardware/GroveAnalogInput.hpp:39-62`.

| Key | Range | Coded default | Ref |
|---|---|---|---|
| (section present) | | enabled = true | `:278-282` |
| `enabled` | bool | | `:295-296` |
| `bus` (**`channel`**, `i2c_bus`) | 0–255 | 1 | `:297-299` (see bug B12) |
| `address` (`addr`) | | 0x04 | `:300-302` |
| `poll_ms` (`poll_interval_ms`) | 20–2000 | 80 | `:303-305` |
| `deadband` (`deadband_raw`) | 0–2048 | 32 | `:306-308` |
| `emit_on_start` (`sync_on_start`) | bool | false | `:309-310` |
| Channel keys: prefix `channel` / `chan` / `ch` / `analog` / `a` + digit 0–7, then `_field`. Fields: (none) = `target` (also `control`); `min`/`minimum`; `max`/`maximum`; `step`; `deadband`/`deadband_raw`; `invert`/`reverse`; `mode` (preset / presets / stepped); `presets`/`preset` (bool) | | | `:147-182`, `:311-340`. Target aliases at `:125-145` |

### 2.10 `[trigger_output]` (aliases `[trigger]`, `[capture_trigger]`, `[hotshoe]`), Core

Parsed in `Apertar-Core/src/hardware/TriggerOutput.cpp:250-360`; defaults in `Apertar-Core/src/hardware/TriggerOutput.hpp:41-55`.

| Key (aliases) | Coded default | Ref |
|---|---|---|
| `enabled` | false | `:303-304` |
| `target` (`type`, `backend`, `output`): gpio / pin / raspberry_pi_gpio, or pcf / pcf8574 / i2c | gpio | `:305-310` |
| `chip` (`gpiochip`, `gpio_chip`) | "auto". An **empty value is stored as ""**, not "auto" (`:311-312`) | |
| `line` (`gpio`, `gpio_line`) | 17 | `:313-315` |
| `pin` (generic: goes to line or pcf_pin depending on target) | — | `:316-317`, `:346-351` |
| `open_drain` (`gpio_open_drain`) | **false** | `:318-319` |
| `bus` (`pcf_bus`) | 1, or the `[pcf8574]` bus | `:320-322` |
| `address` (`pcf_address`) | 0x20, or the `[pcf8574]` address | `:323-325` |
| `pcf_pin` (`pcf8574_pin`) | 0 | `:326-328` |
| `active_high` / `active_low` | active_high = false | `:329-332` |
| `pulse_ms` (`duration_ms`) | 80, clamped 1–5000 | `:333-336` |
| `events` (`event`): record / recording_start / …, still / photo …, timelapse / timelapse_start, timelapse_frame …, all. Separators `,` `;` `\|` `+` | recording_start, still, timelapse_frame | `:121-176`, `:337-343` |

### 2.11 `[recording_indicator]` (aliases `[rec_indicator]`, `[record_led]`, `[recording_led]`, `[tally_led]`), Core

Parsed in `Apertar-Core/src/hardware/RecordingIndicatorOutput.cpp:247-399`; defaults in `Apertar-Core/src/hardware/RecordingIndicatorOutput.hpp:36-49`.

The keys are the same as trigger_output except there is no `pulse_ms` or `events`. Defaults: enabled = false, target = gpio, chip = auto (empty → auto, `:348`), line = −1, open_drain = false, bus = 1, address = 0x20, pcf_pin = −1, active_high = false (`:339-372`).

Fallbacks:
- If the section is disabled, the first `pinN=recindicatorled` in `[pcf8574]` or `dN=recindicatorled` in `[gpio*]` enables the LED (`:293-334`, `:382-391`).
- This happens **even if those sections are `enabled=false`**.

### 2.12 `[imu]` and the driver sections `[mpu6050]`, `[bmi160]`, `[bmi270]`, `[icm42688p]` (also `[gyro]`): Core and UI

Core: `Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:851-1033`, defaults at `Apertar-Core/src/hardware/Mpu6050RecordingSession.hpp:95-121`. UI: `Apertar-UI/src/GyroConfigBridge.cpp:905-1075`, defaults at `:907-917`.

`[imu]` keys. These are the **only** keys read from `[imu]` by both Core (`:881-904`, `:939-955`) and UI (`:979-998`):

| Key (aliases) | Type | Coded default (Core / UI) |
|---|---|---|
| `enabled` | bool | **true / true** (`Apertar-Core/src/hardware/Mpu6050RecordingSession.hpp:96`; `Apertar-UI/src/GyroConfigBridge.cpp:916`) |
| `driver` | mpu6050 / bmi160 / bmi270 / icm42688p (anything else → mpu6050) | mpu6050 (`Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:124-137`, `:907-909`) |
| `sync_mode` | token | free_run |
| `sync_offset_ms` (`offset_ms`, `gyro_sync_offset_ms`) | double, −2000…2000 | 0. A value in `[imu]` beats one in the driver section (`:1011-1015`) |

Driver-section keys (the section is active when its name equals the canonical driver, or is `gyro`: `Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:171-184`, `Apertar-UI/src/GyroConfigBridge.cpp:123-`):

| Key (aliases) | Core range / default (`Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:957-1022`) | UI (`Apertar-UI/src/GyroConfigBridge.cpp:999-1064`) |
|---|---|---|
| `enabled` | **overwrites** the `[imu]` flag (order-dependent) | same |
| `bus` (`bus_number`) | 0–32 / 1 | 0–32 / 1 |
| `address` (`addr`) | 0x03–0x77 / 0x68 | same |
| `sample_rate_hz` (`sample_rate`) | 25–1000 / 500 | same |
| `gyro_range_dps` (`gyro_range`) | clamp 250–2000 / **1000** | snapped to 250/500/1000/2000 (`:423-432`) |
| `accel_range_g` (`accel_range`) | clamp 2–16 / 8 | snapped to 2/4/8/16 (`:412-420`) |
| `dlpf_hz` (`filter_hz`) | 5–260 / 98 | not parsed |
| `use_fifo` (`fifo`) | bool / true | not parsed |
| `fifo_batch_samples` (`batch_samples`) | 1–64 / 24 | not parsed |
| `orientation` (`imu_orientation`) | XYZ permutation (lower-case = negated) / XYZ | same |
| `auto_calibrate_seconds` (`gyro_auto_calibrate_seconds`) | 0–5 / 0 | not parsed |
| `gyro_bias_{x,y,z}` (`…_raw`) | double / 0 | not parsed |
| `level_reference_set` (`level_set`, `accel_level_set`) | bool / false | parsed |
| `level_reference_orientation` (`level_orientation`) | | parsed |
| `level_accel_{x,y,z}` (`level_{x,y,z}_g`, `accel_zero_{x,y,z}`) | double | parsed |
| `frame_readout_time_ms` (`frame_readout_time`) | 0–100 / 0 | not parsed |
| `frame_readout_direction` (`readout_direction`) | 0–3 / 0 | not parsed |

Writers, Core:
- `set_imu_driver` → `[imu] driver` (`Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:1295-1301`)
- `set_imu_orientation` → driver section `orientation` (`:1303-1320`)
- `set_/adjust_/reset_imu_sync_offset` → `[imu] sync_offset_ms` (`:1322-1333`)
- `set_/clear_imu_level_reference` → driver-section `level_*` (`:1363-1379`)
- `calibrate_gyro` → driver section: `auto_calibrate_seconds=0`, `gyro_bias_*` (`:715-842`, `:1148`)
- Command names are dispatched at `Apertar-Core/src/ApertarCoreApp.cpp:9645-9715`.

Writers, UI (all through `writeConfigValue`, `Apertar-UI/src/GyroConfigBridge.cpp:1577-1653`):
- `[imu] driver` (`:684`)
- driver-section `level_*` (`:825-850`)
- `orientation` (`:871`)
- `[imu] sync_offset_ms` (`:885`)

### 2.13 Keys found only in the templates and parsed by nobody

- `[display] controls_mode` (Core template)
- `[imu] bus`, `address`, `sample_rate_hz`, `gyro_range_dps`, `accel_range_g`, `orientation` (Core template, `Apertar-Core/src/ApertarCoreApp.cpp:4346-4351`). The `[imu]` branch only reads enabled / driver / sync_mode / sync_offset_ms.
- `[storage] mount_path` is effectively dead for Core (see 2.4).

---

## 3. Template copies

| ID | Location | Content | Written when |
|---|---|---|---|
| T-Core | `Apertar-Core/src/ApertarCoreApp.cpp:4291-4404` (`defaultHardwareConfigTemplate`) | `[ina219]`, `[cfexpress_hat]`, `[storage]`, `[display]`, `[run_script]`, `[imu]`, `[pcf8574]`, `[gpio]`, `[trigger_output]`, `[recording_indicator]` | Never written automatically. Returned by `GET /api/config` as the editor text when the editable path is missing (`:5297`). Lands on disk only if the user presses Save in the WebUI (`POST /api/config` → `:5323-5386`, `:7175-7195`) |
| T-UI-Display | `Apertar-UI/src/DisplayConfigBridge.cpp:41-326` (`ensureDefaultHardwareConfigFile`) | `[network]`, `[run_script]`, `[ina219]`, `[pcf8574]`, `[trigger_output]`, `[recording_indicator]`, `[neorotary4]`, `[gpio_buttons]`, `[gpio_encoders]`, `[grove_analog]`, `[imu]`, `[mpu6050]`, `[bmi160]`, `[bmi270]`, `[icm42688p]`, `[cfexpress_hat]`, `[storage]`, `[display]` | At **every UI start** if `/home/pi/apertar-hardware.conf` does not exist (`:587`). This runs first in practice: `DisplayConfigBridge` is constructed before the other bridges (`Apertar-UI/src/main.cpp:278`; monitor-only mode returns earlier at `:275`) |
| T-UI-Ina219 | `Apertar-UI/src/Ina219Bridge.cpp:69-342` | Same as T-UI-Display **minus** `[network]`, `[run_script]` and `display.zoom_toggle_factor`, plus two INA comment lines. Bus/address are inserted from constants 4 / 0x40 (`:45-46`, `:91-92`) | At `loadConfiguration` (5 s after start, `:449`, `:497`) if the file is still missing. Normally T-UI-Display has already created it, so this copy only fires if Display failed (UNCONFIRMED in practice) |
| T-min-Core | `Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:623-626` | `# Apertar hardware configuration` header only | IMU writes when the file is empty or missing |
| T-min-UI | `Apertar-UI/src/GyroConfigBridge.cpp:1587-1590` | same header | Gyro writes when the file is empty or missing |
| Fragment | `Apertar-Beta/README.md:119-122` | `[network] hotspot_delay_seconds=0` (example value 0) | docs |
| Fragment | `Apertar-Core/README.md:169-173` | `P0=iso200,fps24,wb5600`, `P1=focus_peaking,zebra`, `P2=capture` | docs |

**Not templates (verified):** `SettingsBridge.cpp`, `GyroConfigBridge.cpp` (header only), `sync_pi_runtime.sh`, `run_pi_direct.sh`, `wait_for_ui_core_start.sh`, `finish_plymouth_handoff.sh`, `Apertar-UI/README.md` (path only, `:171-177`).

### 3.1 Where the templates disagree with each other

T-UI-Display and T-UI-Ina219 agree on every shared key (checked with a key-level diff).

| Section.key | T-Core | T-UI-Display / T-UI-Ina219 | Coded parser default | Note |
|---|---|---|---|---|
| `[network]` (whole section) | absent | `hotspot_delay_seconds=60` (Display only; absent in Ina219) | 60 | |
| `[run_script]` | present | Display: present; Ina219: absent | — | Comment text differs |
| `display.rotation` / `ui_rotation` | `rotation=0` | `ui_rotation=normal` | normal | Equivalent (alias) |
| `display.controls_mode` | `Light` | absent | — | Dead key |
| `display.zoom_toggle_factor` | 4.0 | Display: 4.0; Ina219: absent | 4.0 | |
| `pcf8574.bus` | **10** | **1** | **1** (`Apertar-Core/src/hardware/Pcf8574Input.hpp:31`) | Conflict |
| `pcf8574.active_low`, `poll_ms`, `debounce_ms`, `pin0..7` | absent | true / 40 / 60 / none | true / 40 / 60 | |
| GPIO section name | `[gpio]`, `enabled=false` only | `[gpio_buttons]` with full keys incl. `d5=capture`, `d6=eject` | false | Both names accepted |
| `[gpio_encoders]`, `[grove_analog]`, `[neorotary4]` | absent | present, `enabled=false` | false (gpio); presence = true (grove / neorotary) | |
| `imu.enabled` | **false** | **true** | **true** | Conflict |
| `imu.bus`, `address`, `sample_rate_hz`, `accel_range_g`, `orientation` | 10, 0x68, 500, 8, XYZ | absent from `[imu]` (they live in `[mpu6050]`: bus=1, 0x68, 500, 8, XYZ) | 1, 0x68, 500, 8, XYZ | T-Core keys are **ignored** (§2.13); T-Core bus=10 vs mpu6050 bus=1 |
| `imu.gyro_range_dps` | **2000** | (`[mpu6050]` 1000) | **1000** | Conflict, and the T-Core value is ignored anyway |
| `imu.sync_mode` | absent | free_run | free_run | |
| `[mpu6050]`, `[bmi160]`, `[bmi270]`, `[icm42688p]` | absent | present: mpu6050 `enabled=true`, bmi*/icm `enabled=false` | — | See bug B5 |
| `trigger_output.open_drain` | true | true | **false** (`Apertar-Core/src/hardware/TriggerOutput.hpp:47`) | Template differs from coded default |
| `trigger_output` commented bus | `# bus=1` | `# bus=1` | 1 | T-Core is internally inconsistent: its `[pcf8574]` says bus=10 |
| `recording_indicator` commented bus | `# bus=10` | `# bus=1` | 1 | |
| `recording_indicator.line` | 17 | 17 | **−1** (`Apertar-Core/src/hardware/RecordingIndicatorOutput.hpp:41`) | Template differs from code |
| `recording_indicator.pcf_pin` | 7 | 7 | **−1** (`:45`) | Template differs from code |
| `gpio_encoders.poll_ms` / `debounce_ms` | — | 3 / 40 | shared with buttons (12 / 60) | See bug B9 |
| `ina219.*` | true / 4 / 0x40 | same | same | OK |
| `cfexpress_hat.*`, `storage.*` | 10 / 0x34, /media/RAW, 1000110000.pcie | same | same | OK |

### 3.2 Template values that differ from the parser's coded fallback

From the table above:
- `pcf8574.bus` (T-Core 10 vs code 1)
- `imu.enabled` (T-Core false vs code true)
- `imu.gyro_range_dps` (T-Core 2000 vs code 1000, and the key is ignored)
- `trigger_output.open_drain` (templates true vs code false)
- `recording_indicator.line` (17 vs −1)
- `recording_indicator.pcf_pin` (7 vs −1)

For files 1 and 5, the hotspot/password defaults also exist in four places, all agreeing ("Apertar" / "apertarcam" / 60 s):
- `Apertar-UI/src/WifiBridge.hpp:116-117`
- `Apertar-UI/src/WifiBridge.cpp:130-136`, `:497-498`
- `Apertar-Beta/README.md:111-115`

---

## 4. `apertar-color-profiles.conf` (Core only)

- **Path:** `$APERTAR_COLOR_PROFILE_CONFIG`, else `/home/pi/apertar-color-profiles.conf` (`Apertar-Core/src/color/ColorProfileConfig.cpp:232-237`). Documented at `Apertar-Core/README.md:149-153` and `Apertar-Beta/README.md:211`.
- **No template or writer exists anywhere.**
- **Reload:** when existence or mtime changes, on every profile lookup (`:377-405`). A built-in `imx585-built-in` profile is always appended **last** (`:239-271`, `:404`).
- **Parse:** `:312-375`.
  - Each line is cut at the first `#` or `;` (`:325-327`).
  - `[name]` starts a profile; the name is lower-cased.
  - Keys are lower-cased. Lines before the first section are ignored.

| Key (aliases) | Type | Default | Ref |
|---|---|---|---|
| `match` (`matches`, `sensor`) | list split on `,` / `;` / whitespace (lower-cased). `*` or `default` = wildcard (score 1); otherwise substring of the sensor model (score = len + 10) | the section name (`:273-277`) | `:352-355`, `:407-419` |
| `illuminant1`, `illuminant2` | uint16 (EXIF LightSource) | 21 (D65) (`:127-128`) | `:356-359` |
| `ccm1_kelvin`, `ccm2_kelvin` | uint32 | 0, treated as 2850 / 5600 during blending | `:360-363`, `:431-433` |
| `color_matrix1` (`colour_matrix1`, `dng_color_matrix1`), `color_matrix2` (…) | 9 floats | — | `:288-293` |
| `forward_matrix1` (`ff_matrix1`), `forward_matrix2` (`ff_matrix2`) | 9 floats | — | `:294-299` |
| `ccm` (`colour_correction_matrix`, `color_correction_matrix`) | 9 floats; wins over ccm1/ccm2 | — | `:300-302`, `:425-429` |
| `ccm1`, `ccm2` | 9 floats; blended by WB kelvin between ccm1_kelvin and ccm2_kelvin | — | `:303-309`, `:430-459` |

- **Selection:** highest score wins. On a tie the earlier profile wins, so a user profile beats the built-in. If nothing matches, the active tuning's CCMs are used (illuminants 17 / 21) (`Apertar-Core/src/color/ColorProfileConfig.cpp:830-856`).
- **Active tuning file for calibration:** `$APERTAR_SENSOR_TUNING_FILE`, else `$LIBCAMERA_RPI_TUNING_FILE` (`:613-628`). Core sets both when a tuning file is selected (`Apertar-Core/src/camera/CameraController.cpp:1111-1121`).
- **Gotcha:** `splitList` accepts `;` as a separator (`:167-181`), but the comment stripper has already cut the line at the first `;`. A `;`-separated matrix therefore always fails to parse ("invalid 3x3 matrix", `:282-285`). Only commas or spaces work.

---

## 5. Other persisted settings

### 5a. `UI.conf` (`~/.config/CinePi/UI.conf`)

QSettings writes ungrouped keys under `[General]`; `camera/*` keys go under `[camera]` (standard Qt behaviour). Core reads and writes **only `[General]`** (`Apertar-Core/src/ApertarCoreApp.cpp:1648-1664`, `:1877-1904`).

The UI side is mostly in `Apertar-UI/src/SettingsBridge.cpp`: read at `:324-407`, re-read on external change at `:520-585`. Setter line numbers per key (`setValue`):

| Key | Setter line | Core snapshot field |
|---|---|---|
| zebraEnabled | 603 | yes |
| zebraThreshold | 620 | yes |
| focusPeakingEnabled | 635 | yes |
| focusPeakingThreshold | 652 | yes |
| focusPeakingColor | 667 | yes |
| grayscaleEnabled | 682 | yes |
| smpteEnabled | 699 | yes |
| anamorphicDesqueezeEnabled | 716 | yes |
| anamorphicRatio | 731 | yes |
| falseColorEnabled | 746 | yes |
| falseColorMode | 763 | yes |
| lutPreviewEnabled | 778 | yes |
| lutPreviewFile | 796 | yes |
| horizontalLevelEnabled | 883 | **no** (presets only, `Apertar-Core/src/ApertarCoreApp.cpp:6620-6621`) |
| horizontalLevelColor | 901 | **no** (presets only) |
| guidesEnabled | 916 | yes |
| guidesType | 933 | yes |
| guidesThickness | 949 | yes |
| centerMarkerEnabled | 964 | yes |
| centerMarkerType | 981 | yes |
| uiOrientation | 1007 | yes |
| cameraControlsOpacity | 1025 | yes |
| cameraControlsMode | 1043 | yes |
| externalMonitorEnabled | 1060 | yes |
| externalMonitorMode | 1080 | yes |
| externalMonitorInfoOverlay | 1099 | yes |
| externalMonitorOrientation | 1119 | yes |
| dateTimeOverlayEnabled | 1134 | yes |
| timecodeMode | 1151 (also `Apertar-UI/src/ApertarControlBridge.cpp:633`, `:1471`) | yes |
| photoModeEnabled | 1168 | yes |
| photoLongExposureEnabled | 1187 | yes |
| photoBracketingEnabled | 1197 | yes |
| photoTimer | 1207 | yes |
| photoBracketingEv | 1216 | yes |
| photoBurst | 1231 | yes |
| photoFormat | 1247 | yes |
| photoTimelapse | 1263 | yes |
| soundRecorderEnabled | 1283 | yes |
| recordAudioEnabled | 1294 | yes |
| recordGyroEnabled | 1310 | yes |
| liveAudioMonitoringEnabled | 1326 | yes |
| audioMeterEnabled | 1342 | yes |
| audioInputDevice | 1362 | yes |
| audioOutputDevice | 1382 | yes |
| audioSampleFormat | 1391 | yes |
| audioSampleRate | 1400 | yes |
| audioChannels | 1410 | yes |
| inputVolume | 1427 | yes |
| headphoneVolume | 1444 | yes |
| batteryType | 1466 | yes |
| batteryCapacity | 1476 | yes |
| customBatteryWh | 1492 | yes |
| customBatteryFullVoltage | 1510 | yes |
| customBatteryEmptyVoltage | 1511, 1529 | yes |
| standbyTimeoutSeconds | 1544 | yes |
| standbyUsbPowerOff | 1554 | yes |
| sleepMode | 1565 | yes |
| monitoringOrder | 1580 | no (presets only) |
| recordOrder | 1595 | no (presets only) |
| audioOrder | 1610 | no (presets only) |
| powerOrder | 1625 | no (presets only) |
| systemOrder | 1640 | no (presets only) |
| wifiOrder | 1655 | no (presets only) |
| infoOrder | 1670 | no (presets only) |
| sidebarOrder | 1685 | no (presets only) |
| favoritesOrder | 1700 | yes |

Defaults: UI `Apertar-UI/src/SettingsBridge.cpp:324-407`; Core struct `Apertar-Core/src/ApertarCoreApp.cpp:1581-1639`.

Other keys:
- `hotspotSsid` (default "Apertar") and `hotspotPassword` (default "apertarcam", stored **in plain text**): written by WifiBridge (`Apertar-UI/src/WifiBridge.cpp:252`, `:262`), read at `:130-136` and `:496-498`.
- `lastPhotoTimelapse`: **Core-only**. Written at `Apertar-Core/src/ApertarCoreApp.cpp:9564-9565`, `:9981`; read at `:9549`. The UI never reads it.
- `[camera]` group (UI-only placeholder cache; "Core owns restart/format restoration", `Apertar-UI/src/ApertarControlBridge.cpp:886`). Load at `:884-971`, save at `:973-1011`. Keys: `camera/hasSaved`, `fps`, `isoAuto`, `iso`, `shutterAuto`, `shutterUs`, `whiteBalanceAuto`, `whiteBalanceKelvin`, `whiteBalanceLocked` (legacy, deleted at `:916`), `resolution`, `recordingFormat` (default cdng), `cdngCompression` (none), `lossyDngRatio` (3to1), `proresProfile` (422), `proresColorProfile` (standard), `cdngPreviewColorProfile` (standard), `tuningFile`, `rawBitDepth` (12), `h264Resolution` ("Match Capture"), `autofocusMode` (continuous), `autofocusRange` (normal), `autofocusSpeed` (normal), `autofocusWindow{X,Y,Width,Height}` (0.25 / 0.25 / 0.5 / 0.5).

Core writes into `UI.conf` (through `updateSharedUiGeneralSettings`): `Apertar-Core/src/ApertarCoreApp.cpp:9125`, `9134`, `9433`, `9487`, `9533`, `9566`, `9594`, `9608-9635`, `9734-10026`, `10070-10225`, `10520`, `10759`.

### 5b. Camera settings (Core): `camera_settings.conf`

Load at `Apertar-Core/src/camera/CameraController.cpp:616-740`, write at `:742-778`. Keys, each optionally prefixed `profile.{cdng|mlv|h264|prores|still}.`; defaults from `Apertar-Core/include/apertar/core/Types.hpp:124-162`:

| Key | Default |
|---|---|
| resolution_width, resolution_height | (0, Resolution{}) |
| fps | 24.0 |
| iso | 800 |
| iso_auto | 0 |
| shutter_us | 20833 |
| shutter_auto | 0 |
| exposure_compensation | 0 |
| exposure_metering | centre-weighted |
| photo_mode_enabled | — |
| long_exposure_enabled | — |
| bracketing_enabled | — |
| bracketing_ev | 1.0 |
| wb_kelvin | 5600 |
| wb_auto | 0 |
| wb_locked | legacy, read-only; forces wb_auto (`:681-682`, `:727-728`) |
| recording_format | cdng |
| cdng_compression | uncompressed / lossless_jpeg |
| lossy_dng_ratio | R3 |
| prores_profile | standard / hq / lt / proxy |
| prores_color_profile | — |
| cdng_preview_color_profile | — |
| raw_bit_depth | 12 |
| h264_width, h264_height | 0 / 0 |
| tuning_file | — |
| timecode_mode | FreeRun |
| af_mode | continuous |
| af_range | normal |
| af_speed | normal |
| af_window_x / y / w / h | 0.25 / 0.25 / 0.5 / 0.5 |

LossyDng settings are saved under the `cdng` profile (`:605-608`).

### 5c. The rest

- **Presets:** §1 #10. The payload keys (UI.conf keys plus `camera*` keys) are listed at `Apertar-Core/src/ApertarCoreApp.cpp:6578-6693`.
- **Favorites:** UI.conf `favoritesOrder` (comma list; Core also accepts `|`, `Apertar-Core/src/ApertarCoreApp.cpp:771-822`). Candidate IDs: Core `:727-769`; QML `Apertar-UI/qml/SettingsPage.qml:838-878` (see bug B3).
- **Display calibration:** §1 #8. Per group: `enabled` (false), `red` / `green` / `blue` (1.0, 0.5–1.5), `gamma` (1.0, 0.5–2.5), `black` (0, −0.1–0.1), `white` (1.0, 0.7–1.3) (`Apertar-UI/src/DisplayCalibration.cpp:121-127`).
- **Wi-Fi / hotspot:**
  - Station connections are created by `nmcli device wifi connect <ssid> password <pw> [ifname]`, so NetworkManager owns their persistence (`Apertar-UI/src/WifiBridge.cpp:208-225`).
  - The hotspot SSID and password live in UI.conf; the NM profile "Apertar Hotspot" is recreated on every start.
  - The delay comes from `[network]`.
  - Polkit grants pi the NM actions (`Apertar-UI/systemd/49-apertar-network.rules`).
  - Unit: `Apertar-UI/systemd/apertar-network.service`, with `HOME=/home/pi` (`:10`).
- **Gyro:** §2.12. Recording on/off is `recordGyroEnabled` in UI.conf.
- **Audio device selection:** UI.conf `audioInputDevice` / `audioOutputDevice` / `audioSampleFormat` / `audioSampleRate` / `audioChannels` / `inputVolume` / `headphoneVolume`. Resolved by Core at `Apertar-Core/src/ApertarCoreApp.cpp:2563-2639`, `:2754-2777`.
- **Power / standby:**
  - UI.conf: `sleepMode`, `standbyTimeoutSeconds` (Core reads it for its idle standby, `:7037`), `standbyUsbPowerOff`.
  - Backlight restore file (§1 #9).
  - `/run` state of the standby helpers (§1b).
  - sudoers files `Apertar-UI/systemd/apertar-standby-*.sudoers`.
  - Fan mode lives in config.txt (§1 #16).
- **External monitor:**
  - UI.conf `externalMonitorEnabled` / `Mode` / `InfoOverlay` / `Orientation`
  - `[display] hdmi_external_only`
  - DisplayCalibration `[hdmi]`
  - Runtime KMS JSON (§1b).
- **Battery:** UI.conf `battery*`. Hardware: `[ina219]`.

---

## 6. Environment variables

### 6a. Paths and IPC

| Var | Read at | Effect |
|---|---|---|
| `APERTAR_HARDWARE_CONFIG` | Core `Apertar-Core/src/ApertarCoreApp.cpp:4254`, `4273`, Python `3407`; every `Apertar-Core/src/hardware/*.cpp` candidate list (e.g. `Pcf8574Input.cpp:63`, `GpioInput.cpp:63`, `NeoRotary4Input.cpp:76`, `GroveAnalogInput.cpp:60`, `TriggerOutput.cpp:76`, `RecordingIndicatorOutput.cpp:73`, `Mpu6050RecordingSession.cpp:194`); UI `Apertar-UI/src/DisplayConfigBridge.cpp:29`, `Ina219Bridge.cpp:57`, `GyroConfigBridge.cpp:201`, `WifiBridge.cpp:21`, `MediaStatusBridge.cpp:775`, `CfeAutomounter.cpp:117` | First config candidate, or the only path for WifiBridge and the Core editor. **Not** honoured by the UI's first-run template writer |
| `APERTAR_COLOR_PROFILE_CONFIG` | `Apertar-Core/src/color/ColorProfileConfig.cpp:234` | Colour profile file |
| `HOME`, `XDG_CONFIG_HOME` | `Apertar-Core/src/ApertarCoreApp.cpp:343-346`; `Apertar-Core/src/camera/CameraController.cpp:344-350`; Qt QSettings (implicit) | UI.conf and camera_settings.conf locations |
| `XDG_DATA_HOME`, `HOME` | `Apertar-Core/src/ApertarCoreApp.cpp:5219-5257`; Qt AppDataLocation (implicit) | Preset directory |
| `HOME` | `Apertar-Core/src/ApertarCoreApp.cpp:4281` (`~` display path), `Apertar-Core/src/color/ProresIspProfile.cpp:228` | ProRes tuning cache |
| `APERTAR_MEDIA_ROOT` | Core Python helper `Apertar-Core/src/ApertarCoreApp.cpp:3394`, `3457` (Core sets it itself at `:3594`); UI `Apertar-UI/src/SettingsBridge.cpp:145`, `169`; start script `Apertar-Core/scripts/start-apertar-core.sh:5` | LUT/Tuning search root; mount path; `--media` |
| `APERTAR_CORE_BIN`, `APERTAR_SOCKET_PATH` | `Apertar-Core/scripts/start-apertar-core.sh:4`, `:6` | Binary path; `--socket` |
| `APERTAR_TUNING_FILE` | `Apertar-Core/scripts/start-apertar-core.sh:16-18` | Exported as `LIBCAMERA_RPI_TUNING_FILE` |
| `LIBCAMERA_RPI_TUNING_FILE` | `Apertar-Core/src/camera/CameraController.cpp:7603`, `7641`, `8717`; `Apertar-Core/src/color/ColorProfileConfig.cpp:617`; set at `CameraController.cpp:1116-1119`, `5360` | Initial tuning when none is saved; calibration source |
| `APERTAR_SENSOR_TUNING_FILE` | `Apertar-Core/src/color/ColorProfileConfig.cpp:616`; set at `CameraController.cpp:1114`, `1120` | RAW calibration tuning (wins over LIBCAMERA_*) |
| `APERTAR_DEFAULT_TUNING_DIR` | `Apertar-Core/src/camera/DefaultTuningSelection.hpp:58` | Overrides `/home/pi/Tuning-Files/defaults-*` |
| `APERTAR_CONTROL_SOCKET` | `Apertar-UI/src/ApertarControlBridge.cpp:1032`, `1567`; `Apertar-UI/src/AudioDeviceBridge.cpp:347`; `Apertar-UI/src/MediaStatusBridge.cpp:23` | Core socket (default `/tmp/apertar-core.sock`) |
| `APERTAR_NETWORK_RUNTIME` | `Apertar-UI/src/NetworkHelper.cpp:14` | network-helper runtime dir (default `/run/apertar-network`) |
| `APERTAR_NETWORK_HELPER` | set at `Apertar-UI/src/NetworkHelper.cpp:13`; read at `Apertar-UI/src/WifiBridge.cpp:155`, `162`, `478` | Puts WifiBridge into helper mode |
| `APERTAR_MONITOR_RUNTIME_SOCKET` | `Apertar-UI/src/ExternalMonitorRuntimeBridge.cpp:16`; set at `Apertar-UI/run_pi_direct.sh:219` | Monitor IPC socket |
| `APERTAR_UI_READY_FILE` | `Apertar-UI/src/main.cpp:463`; `run_pi_direct.sh:79`, `220` | First-frame marker |
| `APERTAR_CORE_START_READY_FILE` | `Apertar-UI/src/main.cpp:406`; `run_pi_direct.sh:172` | Core start gate marker |
| `APERTAR_HEADLESS_READY_FILE` | `run_pi_direct.sh:80`; `finish_plymouth_handoff.sh:8` | Headless marker |
| `APERTAR_PLYMOUTH_HANDOFF_TIMEOUT_SECONDS`, `APERTAR_PLYMOUTH_BIN` | `finish_plymouth_handoff.sh:6-7` | Handoff wait (20 s) and plymouth binary |
| `APERTAR_DRM_SYSFS` | `run_pi_direct.sh:78`; `wait_for_ui_core_start.sh:23` | `/sys/class/drm` override |
| `APERTAR_UI_DRM_DEVICE`, `APERTAR_MONITOR_DRM_DEVICE` | `run_pi_direct.sh:188`, `191` | Force DRM cards |
| `APERTAR_MONITOR_HOTPLUG_POLL_SECONDS` | `run_pi_direct.sh:178`, `312`, `345` | Hotplug poll (1 s / 0.5 s) |
| `APERTAR_QT_USE_LIBINPUT` | `run_pi_direct.sh:211` | libinput instead of evdev |
| `APERTAR_RUNTIME_ROOT`, `APERTAR_NVME_RUNTIME_ROOT`, `APERTAR_USE_RUNTIME_MIRROR`, `APERTAR_USE_NVME_RUNTIME` | `run_pi_direct.sh:13-14`; `sync_pi_runtime.sh:7` | Runtime mirror |
| `APERTAR_MESA_RUNTIME_ROOT`, `APERTAR_RUNTIME_LIB_DIR`, `APERTAR_UI_BIN` | `run_pi_direct.sh:51`, `54`; `sync_pi_runtime.sh:8-10` | Mesa / runtime / UI binary |
| `XDG_RUNTIME_DIR` | `run_pi_direct.sh:79`, `194`; `finish_plymouth_handoff.sh:5` | Runtime base |
| `QT_QPA_*`, `QSG_RENDER_LOOP` | set at `run_pi_direct.sh:207-218`; read at `Apertar-UI/src/main.cpp:254-256`, `Apertar-UI/src/DisplayStandbyController.cpp:27` | Qt platform |

### 6b. UI behaviour switches

| Var | Read at | Effect |
|---|---|---|
| `APERTAR_MONITOR_ONLY` | `Apertar-UI/src/main.cpp:275`; set at `run_pi_direct.sh:273` | HDMI helper process; skips DisplayConfigBridge, so no template is written |
| `APERTAR_BACKLIGHT_DIR` | `Apertar-UI/src/SleepManager.cpp:102` | Backlight sysfs dir |
| `APERTAR_PANEL_LED_PATH` | `Apertar-UI/src/SleepManager.cpp:31` | Panel LED override |
| `APERTAR_STANDBY_PANEL_POWER` | `Apertar-UI/src/DisplayStandbyController.cpp:18` | `0` disables DPI/DSI power-off |
| `APERTAR_VIDEO_PLAYBACK_PLUGIN` | `Apertar-UI/src/VideoPlayback.cpp:24` | Playback .so path |
| `APERTAR_PREVIEW_FORCE_CPU`, `APERTAR_PREVIEW_FORCE_PLANAR`, `APERTAR_PREVIEW_FORCE_EGL` | `Apertar-UI/src/PreviewWindowRenderer.cpp:296-301` | Preview renderer fallbacks |

### 6c. Core encoder and performance knobs

Effects are inferred from names and call sites.

- **H.264** (`Apertar-Core/src/camera/CameraController.cpp`):
  - `APERTAR_H264_ENCODER` (3981, 4333), `APERTAR_H264_PRESET` (4340), `APERTAR_H264_TUNE` (4347), `APERTAR_H264_CRF` (4363), `APERTAR_H264_QP` (4370), `APERTAR_H264_BITRATE` (4377), `APERTAR_H264_MAXRATE` (4384), `APERTAR_H264_BUFSIZE` (4391), `APERTAR_H264_X264_PARAMS` (4398), `APERTAR_H264_BACKEND` (4406), `APERTAR_H264_THREADS` (4435), `APERTAR_H264_PIPE_BYTES` (4456), `APERTAR_H264_QUEUE_FRAMES` (4467)
  - `APERTAR_H264_SIZE` (2779), `APERTAR_H264_CAMERA_BUFFERS` (1127, 3–12), `APERTAR_H264_KEEP_RAW_STREAM` (2843), `APERTAR_H264_SINGLE_STREAM` (2848)
  - `APERTAR_H264_LIBAV_PLUGIN` (`Apertar-Core/src/video/LibavH264EncoderClient.cpp:20`)
- **ProRes:**
  - `APERTAR_PRORES_CAMERA_BUFFERS` (`Apertar-Core/src/camera/CameraController.cpp:1133`, 8–32), `APERTAR_PRORES_CACHED_DMABUF` (6387)
  - `APERTAR_PRORES_PLUGIN` (`Apertar-Core/src/prores/ProresRecorder.cpp:28`), `APERTAR_PRORES_THREADS` (`ProresRecorder.cpp:61`, `Apertar-Core/src/prores/ProresEncoder.cpp:831`)
  - `APERTAR_PRORES_ODIRECT` (1098), `APERTAR_PRORES_WRITEBACK` (1154), `APERTAR_PRORES_WRITER_THREAD` (1184), `APERTAR_PRORES_WRITER_QUEUE` (1187), `APERTAR_PRORES_WRITER_QUEUE_MB` (1192), `APERTAR_PRORES_WRITER_SLOW_MS` (1200), `APERTAR_PRORES_CSC_THREADS` (1323)
  - The `tuningOverride` knobs can also come from `/home/pi/.apertar-tuning`.
- **RAW / CinemaDNG:**
  - `APERTAR_RAW_CACHED_DMABUF` (`Apertar-Core/src/camera/CameraController.cpp:6321`), `APERTAR_CDNG_QUEUE_FRAMES` (3330), `APERTAR_CDNG_WORKERS` (3343), `APERTAR_LOSSYDNG_WORKERS` (3345), `APERTAR_CDNG_WORKER_NICE` (3359, 3706)
  - `APERTAR_CDNG_TILE_ROWS` (`Apertar-Core/src/cdng/CdngEncoder.cpp:55`), `APERTAR_CDNG_PROFILE_DETAIL` (`:72`)
  - `APERTAR_LOSSYDNG_WRITER_BYTES` (`Apertar-Core/src/lossydng/LossyDngEncoder.cpp:100`), `APERTAR_LOSSYDNG_ASYNCWRITE` / legacy `QRAW_LOSSYDNG_ASYNCWRITE` (`:325-327`)

---

## 7. Inconsistencies and likely bugs

- **B1. The UI's first-run template shadows /boot configs.** `ensureDefaultHardwareConfigFile` checks and creates only `/home/pi/apertar-hardware.conf` (`Apertar-UI/src/DisplayConfigBridge.cpp:41-46`, `:587`; `Apertar-UI/src/Ina219Bridge.cpp:69-74`, `:497`). `/home/pi` comes before `/boot/*` in every candidate list, so a config kept only on `/boot/firmware` is silently ignored by every reader once the UI has started. It also ignores `APERTAR_HARDWARE_CONFIG`. Consistent with `Apertar-Beta/README.md:223` ("belongs in /home/pi/, not on the boot partition"), which contradicts the /boot candidates in the code.

- **B2. File-selection rules differ by component.**
  - INA219, trigger, recording LED, display and gyro use the first existing file, even if it lacks the section.
  - PCF8574, GPIO, NeoRotary4 and Grove fall through to later candidates when their section is missing (`Apertar-Core/src/hardware/Pcf8574Input.cpp:385`, etc.).
  - WifiBridge uses only env or /home/pi (`Apertar-UI/src/WifiBridge.cpp:21-23`).
  - run_script and the WebUI editor use only env or /home/pi (`Apertar-Core/src/ApertarCoreApp.cpp:4271-4276`).
  - Result: the WebUI editor can show the template as "Not saved yet" while Core is actually running from /boot (`:5292-5306`).

- **B3. Favorites ID lists diverge.** Core's `favoriteCandidateOrder` (`Apertar-Core/src/ApertarCoreApp.cpp:727-769`) lacks `autofocus`, `cameraControlsOpacity`, `formatMedia`, `gyroData`, `horizontalLevel`, `hotspot`, `smpteBars`, `soundRecorder` and `tuningFile`, and has `lutPreview`. The QML list (`Apertar-UI/qml/SettingsPage.qml:838-878`) has the opposite set. When Core writes `favoritesOrder` (WebUI `set_favorites_order`, `:10224-10225`), it filters out the UI-only favorites and persists the truncated list.

- **B4. IMU defaults conflict.**
  - Coded default enabled=true (`Apertar-Core/src/hardware/Mpu6050RecordingSession.hpp:96`, `Apertar-UI/src/GyroConfigBridge.cpp:916`).
  - T-UI template: `[imu]` and `[mpu6050]` enabled=true. T-Core template: `[imu] enabled=false`.
  - T-Core's `[imu] bus=10 address sample_rate_hz gyro_range_dps=2000 accel_range_g orientation` are ignored: the `[imu]` branch only reads 4 keys (`Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:939-955`, `Apertar-UI/src/GyroConfigBridge.cpp:979-998`).

- **B5. The driver section's `enabled` overrides `[imu] enabled`, depending on order.** One flag is shared (`Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:946-947` vs `:957-958`; UI `:980-981` vs `:1000-1001`). With the UI template, `[bmi160]`, `[bmi270]` and `[icm42688p]` have `enabled=false` and come after `[imu]`. So selecting driver bmi160, bmi270 or icm42688p from the UI or WebUI (which writes only `[imu] driver`: `Apertar-UI/src/GyroConfigBridge.cpp:684`, `Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:1300`) leaves the IMU **disabled** until the user edits that section.

- **B6. PCF8574 `bus` default conflicts.** Code default 1 (`Apertar-Core/src/hardware/Pcf8574Input.hpp:31`); T-UI 1; T-Core 10 (`Apertar-Core/src/ApertarCoreApp.cpp:4363`). T-Core is also self-inconsistent: `[trigger_output] # bus=1` vs `[recording_indicator] # bus=10`.

- **B7. Other template vs code mismatches.**
  - `trigger_output.open_drain` is true in both templates, false in code (`Apertar-Core/src/hardware/TriggerOutput.hpp:47`).
  - `recording_indicator.line` and `pcf_pin` are 17 / 7 in the templates, −1 / −1 in code.

- **B8. PCF inheritance in trigger/LED depends on section order.** The trigger and LED parsers copy `[pcf8574]` bus/address whenever that section is parsed (`Apertar-Core/src/hardware/TriggerOutput.cpp:289-298`, `Apertar-Core/src/hardware/RecordingIndicatorOutput.cpp:293-303`). If `[pcf8574]` comes **after** `[trigger_output]` or `[recording_indicator]` (as it does in neither template, but it can in user files), it overwrites the explicit per-section bus/address override. TriggerOutput also ignores the `pcf8574_buttons` alias and the `channel` / `i2c_bus` / `addr` key aliases that RecordingIndicatorOutput and Pcf8574Input accept.

- **B9. GPIO global keys are shared between `[gpio_buttons]` and `[gpio_encoders]`.** `chip`, `active_low`, `pull`, `poll_ms` and `debounce_ms` are single fields, so the last section wins (`Apertar-Core/src/hardware/GpioInput.cpp:431-442`). In the UI template, the encoder values (poll_ms=3, debounce_ms=40) override the buttons' 12 / 60. The template also maps GPIO 5/6 both as buttons (`d5`, `d6`) and as encoder0 a/b. Both sections are disabled by default.

- **B10. `recindicatorled` is honoured from disabled sections.** It is picked up in `[pcf8574]` / `[gpio*]` even when they are `enabled=false` (`Apertar-Core/src/hardware/RecordingIndicatorOutput.cpp:304-332`). UNCONFIRMED whether this is intended.

- **B11. Inline comment handling is inconsistent.**
  - Core INA219 integers do not strip comments, so `bus=4 # i2c-4` is silently ignored (`Apertar-Core/src/ApertarCoreApp.cpp:4406-4425`, `:4489`).
  - The Python `configparser` helpers have the same problem for `bus` / `address` (`Apertar-Core/src/ApertarCoreApp.cpp:3413-3422`, `Apertar-UI/src/MediaStatusBridge.cpp:782-791`).
  - The Core IMU `driver` value is not comment-stripped, so `driver=bmi160 # x` becomes mpu6050 (`Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:888-893`). The UI strips it.
  - Pcf, GPIO, Neo, Grove and the colour profile parser cut the whole line at `#` or `;`, so values cannot contain them.
  - The UI QSettings readers rely on Qt's INI rules (UNCONFIRMED: `;` starts a comment; `#` lines may become junk keys; read-only, so harmless).

- **B12. `[grove_analog] channel=` is an alias for the I2C bus** (`Apertar-Core/src/hardware/GroveAnalogInput.cpp:297`), while `channel0…7` are ADC channel mappings (`:147-163`). This is a confusing collision.

- **B13. Bool vocabularies differ.** `enabled` / `disabled` are accepted only by the Core INA219 parser (`Apertar-Core/src/ApertarCoreApp.cpp:4441-4446`), the UI Ina219Bridge (`Apertar-UI/src/Ina219Bridge.cpp:393-404`), cfe-automounter (`Apertar-UI/src/CfeAutomounter.cpp:81-87`) and the Python helpers. Every other parser treats them as invalid and keeps its fallback.

- **B14. Case sensitivity differs.**
  - The UI QSettings groups and keys (`display`, `ina219`, `network/hotspot_delay_seconds`) and HardwareScriptRunner (`[run_script]` exact, `Apertar-Core/src/hardware/HardwareScriptRunner.cpp:52`) are case-sensitive.
  - Core INA219 (`== "[ina219]"`) fails on `[ ina219 ]`.
  - The other Core parsers are case-insensitive.

- **B15. The Python `configparser` helpers can crash on valid-looking files.** `parser.read` only catches `OSError` (`Apertar-Core/src/ApertarCoreApp.cpp:3444-3447`, `Apertar-UI/src/MediaStatusBridge.cpp:813-816`). Duplicate sections or keys raise `DuplicateSectionError` / `DuplicateOptionError`, and a stray `%` raises an interpolation error. UNCONFIRMED (standard `configparser` strict/interpolation behaviour); the C++ parsers just let the last value win.

- **B16. `[storage] mount_path` is dead for Core** (§2.4). The UI Python fallback and cfe-automounter honour it but ignore `APERTAR_MEDIA_ROOT`. The UI LUT/tuning scan uses `APERTAR_MEDIA_ROOT` plus a hard-coded `/media/RAW`, not `mount_path`.

- **B17. Writes to `apertar-hardware.conf` have no shared lock.** There are four independent writers:
  - Core WebUI save: `.bak` + `.tmp`, rename, no fsync (`Apertar-Core/src/ApertarCoreApp.cpp:5356-5385`).
  - Core IMU writers: `.tmp` + rename; on rename failure they `remove(path)` and then rename, leaving a window with no file (`Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:700-709`).
  - UI gyro writer (QSaveFile).
  - UI template creation (QSaveFile).
  - The WebUI and IMU writers use the same `<path>.tmp` name. Contrast with UI.conf, where Core takes a QLockFile-compatible lock (`Apertar-Core/src/util/SettingsFile.hpp:58-118`).

- **B18. Core's INI writer for UI.conf does not escape or unescape like QSettings.** Core reads raw text after `=` (`Apertar-Core/src/ApertarCoreApp.cpp:1666-1671`) and writes `key=value` verbatim (`:1920`, `:1927`). UNCONFIRMED (Qt INI escaping from memory; needs a test):
  - QSettings quotes strings containing `,` `;` `=` and parses unquoted `a,b` as a QStringList.
  - Audio device IDs contain commas (`hw:1,0`, `hdmi:CARD=x,DEV=0`; `Apertar-UI/src/AudioDeviceBridge.cpp:109-111`).
  - UI → Core: Core may see `"hdmi:CARD=x,DEV=0"` including the quotes. `resolveAudioDeviceSelection` then fails for HDMI IDs (`:2583-2639`); for `hw:` IDs the regex still finds the device.
  - Core → UI: a Core-written `audioInputDevice=hw:1,0` would be read by QSettings as a list, so `toString()` returns empty.
  - The same risk applies to `lutPreviewFile` paths containing `,` or `;`.

- **B19. `timecodeMode` normalisation is inconsistent inside Core.** `readSharedUiSettings` accepts only the exact string "Rec Run" (`Apertar-Core/src/ApertarCoreApp.cpp:1723`). `normalizeTimecodeModeValue` accepts `rec run` / `rec_run` case-insensitively (`:380-386`), and so does the UI (`Apertar-UI/src/SettingsBridge.cpp:578-584`). Timecode mode is also stored twice: `UI.conf timecodeMode` and `camera_settings.conf timecode_mode`.

- **B20. Duplicate persistence of camera state.** Core's `camera_settings.conf` is authoritative. The UI keeps a parallel `UI.conf [camera]/*` cache (`Apertar-UI/src/ApertarControlBridge.cpp:884-1011`) with its own defaults (e.g. `proresProfile` "422" vs Core enum Standard; `cdngCompression` "none"). Photo mode, bracketing and timelapse live in both `UI.conf` and the camera profiles.

- **B21. `cameraControlsOpacity` can differ between UI and Core.** When `UI.conf` lacks the key, the UI uses `[display] controls_opacity` from hardware.conf (`Apertar-UI/src/main.cpp:318`, `Apertar-UI/src/SettingsBridge.cpp:456-467`). Core does not read that, so it reports 1.0 to the WebUI (`Apertar-Core/src/ApertarCoreApp.cpp:1615`, `:7991`).

- **B22. Keys written but never read, or read but absent from the templates.**
  - Written and never read: `[display] controls_mode` (T-Core).
  - Read only by Core: `lastPhotoTimelapse` (UI.conf).
  - Saved by UI, never consumed for behaviour: `horizontalLevel*` (Core only copies it into presets). Not a bug.
  - Read but absent from every template: `[imu] sync_mode` (only in T-UI); `[gpio_*] bias`; `[trigger_output] pin`; all aliases; driver-section `dlpf_hz`, `use_fifo`, `fifo_batch_samples` (T-UI `[mpu6050]` only; the bmi/icm sections lack `dlpf_hz` and `fifo_batch_samples`).

- **B23. Hard-coded runtime paths do not follow env overrides.**
  - The UI checks `/run/apertar-network/managed` literally (`Apertar-UI/src/WifiBridge.cpp:156`, `:479`) while the helper honours `APERTAR_NETWORK_RUNTIME` (`Apertar-UI/src/NetworkHelper.cpp:14`).
  - The ready-file default differs: `/tmp` in `run_pi_direct.sh:79` vs `/run/apertar-ui` in `finish_plymouth_handoff.sh:5` and `apertar-network-start-gate.conf:4` when `XDG_RUNTIME_DIR` and `APERTAR_UI_READY_FILE` are unset. The UI/Core systemd units are not in the repos (UNCONFIRMED how the image sets these).

- **B24. Core's HOME dependence is unconfirmed.** `start-apertar-core.sh` does not set `HOME` or `APERTAR_HARDWARE_CONFIG`. If the Core service ran without `HOME=/home/pi`, Core would read a different `UI.conf` and preset directory than the UI. UNCONFIRMED: the Core unit file is not in the repo.

- **B25. Preset directory resolution differs.** The UI prefers `~/.local/share/Apertar-UI/presets`, else legacy `~/.config/CinePi/UI/presets` (`Apertar-UI/src/SettingsBridge.cpp:1937-1958`). Core also considers `ApertarUI` (no hyphen) and `$XDG_DATA_HOME` variants in a different order (`Apertar-Core/src/ApertarCoreApp.cpp:5216-5260`). If an `ApertarUI/presets` dir exists, Core and UI can use different folders. There is no lock on preset writes.

- **B26. Hotspot SSID and password are stored in plain text** in `~/.config/CinePi/UI.conf` (`Apertar-UI/src/WifiBridge.cpp:252`, `:262`). The default password `apertarcam` is hard-coded in 3 places (`Apertar-UI/src/WifiBridge.hpp:117`, `Apertar-UI/src/WifiBridge.cpp:136`, `:498`).

- **B27. `trigger_output` with an empty chip value.** `gpiochip=` blank stores "" rather than "auto" (`Apertar-Core/src/hardware/TriggerOutput.cpp:311-312`). RecordingIndicatorOutput maps empty to "auto" (`:348`).

- **B28. Colour profile `;` separator can never work**, because the comment stripper removes everything after the first `;` before the list is split (§4).
