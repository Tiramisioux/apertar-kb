# R3: the other readers and writers of Apertar's hardware config, the system files, and the touch UI

This is a reader report for the Apertar "controls" project: the GPIO dropdown and method-assignment port, a
system-controlled config file, and the I2C devices from Patrik's NeoRotary fix. It records what exists today. It does
not design anything. R1 covers Cinemate. Apertar Core's own input drivers are cited here only where they share a
file, a section or a restart rule with the processes below.

**Trees read (read only):**

| Tree | Commit | Prefix used below |
| --- | --- | --- |
| Apertar touch UI and helper binaries: `/tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/controls/ui-tip` | `5aab7e2` | `UI:` (every `UI:` citation is `@5aab7e2`) |
| Apertar Core: `/tmp/claude-0/-home-user-apertar-kb/17fc979d-f346-53ac-97ad-c8caa225a57d/scratchpad/controls/core-tip` | `0296ed1` | `Core:` / `App:` = `Core:src/ApertarCoreApp.cpp` / `Web:` = `Core:src/web/WebControlPage.cpp` (every one is `@0296ed1`) |
| KB: `/home/user/apertar-kb` | `24a00da` | `KB:` (Pi readings are quoted as the KB records them. I did not touch the Pi) |

**Labels:**
- **C** (CONFIRMED): I opened the cited line(s).
- **C-KB**: I opened the KB line. That line records a reading Patrik took on the Pi, which I did not repeat.
- **P** (PROBABLE): derived; the derivation is given.
- **U** (UNCONFIRMED): not checked; the command that settles it is given.

`~` means `/home/pi` throughout.

---

## 0. Short version

1. **Eight processes or code paths read `apertar-hardware.conf` from the UI repo.** Two UI-repo binaries never
   read it: the standby helpers and the runtime mirror scripts. The readers:
   - Apertar-UI's `DisplayConfigBridge` (`[display]`), `Ina219Bridge` (`[ina219]`), `GyroConfigBridge` (`[imu]`
     plus the driver section) and `WifiBridge` (`[network]`).
   - The monitor-only UI process (`[display]`).
   - `apertar-network-helper` (`[network]`).
   - `apertar-cfe-automounter` (`[cfexpress_hat]`, `[storage]`).
   - An embedded Python watcher in `MediaStatusBridge` (`[cfexpress_hat]`, `[storage]`). **It has no caller, so it is
     dead code.**

   All but one use the candidate list `$APERTAR_HARDWARE_CONFIG` → `/home/pi/…` → `/boot/firmware/…` → `/boot/…`,
   and the first file that exists wins even when it lacks the section. **C.** The exception is `WifiBridge`, which
   reads only the env path or `/home/pi`. **C.** Sections in §1.2.
2. **The file is read only at process start, with three exceptions in Core.** No UI-repo process watches it or
   reloads it. **C** (grep: the only `QFileSystemWatcher`s watch UI.conf, DisplayCalibration.conf, audio devices
   and media). In Core, IMU settings are re-read per recording or command, `[run_script]` per action, and the NVMe
   Python watcher per eject.
3. **The UI writes the file in two ways:**
   - **Template:** if `/home/pi/apertar-hardware.conf` is missing at UI start, two classes write a full template.
     `DisplayConfigBridge` does it at once and `Ina219Bridge` 5 s later. Both ignore `$APERTAR_HARDWARE_CONFIG`.
     **C.**
   - **Gyro page:** `GyroConfigBridge` does a line-preserving read-modify-write through `QSaveFile`, with no lock.
     **C.**

   The templates write `[cfexpress_hat] bus=10` and `[neorotary4] enabled=false`. Deleting or moving Patrik's
   file therefore silently reverts his fix at the next UI start. **P**: the template content is C; the revert
   follows from the first-wins candidate order.
4. **Writers to the same file, with no shared lock:** UI template, UI gyro page, Core WebUI raw editor
   (`POST /api/config`), Core IMU commands, and the operator in `nano`. Two Core writers use the same temp name
   `<file>.tmp`. The Core IMU writer deletes the real file if its first rename fails. **C.** §4.1.
5. **The touch UI has no page for buttons, knobs, I2C buses, `[display]`, `[network]`, `[run_script]` or
   `[cfexpress_hat]`.** **C** (grep of all QML). It shows or changes these hardware-related items:
   - IMU driver, orientation, sync offset and level (direct file writes).
   - Gyro calibration (Core command).
   - INA219 battery readout. When the sensor is missing it shows "Check /home/pi/apertar-hardware.conf".
   - Fan mode (writes `/boot/firmware/config.txt` through `sudo -n install`).
   - UI orientation, controls opacity and display calibration, which live in UI.conf and DisplayCalibration.conf,
     not in the hardware file.
6. **Two paths for the same writes.** For the IMU and the fan, the touch UI writes files itself, while the WebUI
   goes through Core socket commands (`set_imu_*`, `calibrate_gyro`, `set_fan_mode`). **C.** That Core path is the
   existing "Apertar API" way to change hardware config.
7. **`~/.config/CinePi/UI.conf` has five owners:** the UI's `SettingsBridge`, `ApertarControlBridge` and
   `WifiBridge`, the network helper (re-reads the hotspot keys every 10 s), the monitor-only process, and Core.
   Core writes `[General]` under a `UI.conf.lock` that cooperates with QLockFile, using
   `settingsFile::atomicWrite`. **C.** That lock-plus-atomic-write is the only cooperative writer pattern in Apertar.
8. **System files in the repos:**
   - UI repo: one unit (`apertar-network.service`), one drop-in that is not installed on the Pi, one polkit rule,
     one udev rule, two sudoers files.
   - Core repo: a systemd drop-in, a sudoers file, a tmpfiles file, and the root helper `apertar-media-tune` (KB:
     "helper not installed").
   - On the Pi only: the core, ui-direct and automounter units, `media-RAW.service`, `/usr/local/libexec/*`.
   **C / C-KB.**
9. **Nothing in either repo writes `dtoverlay`, `dtparam=i2c*` or the DPI lines.** **C.** The only `config.txt`
   writers are the two fan-mode copies (UI and Core). Both append a marked block at the end of the file with
   `sudo -n install -m 644`. **C.** This conflicts with Patrik's house rule; see §3.3.
10. **Migration is constrained by three things.**
    - The live file's provenance is unknown. The KB's tally entry describes image content that matches none of
      the three templates. **P.**
    - The parsers disagree on inline comments, duplicate keys, aliases and section order.
    - Any move of the file away from `/home/pi` regenerates a template there that shadows the new location for
      every reader. §4.4–§4.7.

---

## 1. Who reads Apertar's config, which sections, when, and how they find it

### 1.1 Processes in the UI repo and what they read

Targets are from `UI:CMakeLists.txt:67-138` (ApertarUI), `:156-166` (automounter, standby helpers, network
helper) and `:172-182` (`ApertarDirectProxy` = `apertar-runtime/libproxy.so.1`). **C.**

| Process (binary) | Runs as | Config files read | Hardware-conf sections | When | How it finds the file | Label |
| --- | --- | --- | --- | --- | --- | --- |
| `Apertar-UI` main (`apertar-ui-direct.service` → `run_pi_direct.sh`) | pi | `apertar-hardware.conf`, `~/.config/CinePi/UI.conf`, `~/.config/CinePi/DisplayCalibration.conf`, `~/.config/Apertar/StandbyBacklights.conf`, `/boot/firmware/config.txt` (fan block, sensor-name scan), `/boot/firmware/camera-selection.txt` | `[display]`, `[ina219]`, `[imu]` + driver section, `[network]` | See §1.2 | Candidate list (§1.2) | C (code); runs-as **C-KB** `KB:architecture/overview.md:12` |
| `Apertar-UI` monitor-only (`APERTAR_MONITOR_ONLY=1`, child of `run_pi_direct.sh`) | pi | `apertar-hardware.conf` (`DisplayConfigBridge`), UI.conf (`SettingsBridge`), DisplayCalibration.conf | `[display]` | Process start (`UI:src/main.cpp:131-139`, branch at `:275-276`) | Same as main UI | C |
| `apertar-network-helper` (`apertar-network.service`) | pi, `HOME=/home/pi` (`UI:systemd/apertar-network.service:8-10`) | `apertar-hardware.conf`, UI.conf (`hotspotSsid`, `hotspotPassword`) | `[network]` | Constructor once (`UI:src/WifiBridge.cpp:129`). UI.conf re-synced on every 10 s tick (`:495-503`) | `$APERTAR_HARDWARE_CONFIG` or `/home/pi/…` only (`:21-23`) | C |
| `apertar-cfe-automounter` (`apertar-cfe-automounter.service`, `/usr/local/libexec/`) | root | `apertar-hardware.conf` | `[cfexpress_hat]`, `[storage]` | Daemon start only (`UI:src/CfeAutomounter.cpp:792`) | Candidate list; first file that opens wins (`:114-145`) | C; root **C-KB** `KB:architecture/overview.md:145` |
| `apertar-standby-usb`, `apertar-standby-low-power` (root via `sudo -n` from Core) | root | none (hard-coded `/sys`, `/proc`, `/run/apertar-standby-*`) | — | — | — | C (`UI:src/StandbyUsbPower.cpp:19-23`, `UI:src/StandbyLowPower.cpp:16-17`; no `getenv`/`conf` beyond test-mode env) |
| `apertar-wait-ui-core-start` (= `UI:wait_for_ui_core_start.sh`) | Core's unit (`ExecStartPre`) | `/run/apertar-ui/core-start-ready`, `/sys/class/drm/*/status` | — | Core start | — | C (`:5`, `:23`) |
| Runtime mirror (`run_pi_direct.sh`, `sync_pi_runtime.sh`, `build/apertar-runtime/libproxy.so.1`) | pi | none of the config files; DRM sysfs, `$HOME/.cache/apertar-runtime` | — | UI launch | — | C (`UI:run_pi_direct.sh:13`, `:120-166`; `UI:sync_pi_runtime.sh:7-10`) |
| Embedded Python NVMe watcher in `MediaStatusBridge` (`python3 -c`) | would be pi | `apertar-hardware.conf` | `[cfexpress_hat]`, `[storage]` | **Never.** `startNvmeReinsertWatcher` (`UI:src/MediaStatusBridge.cpp:752`) has no caller (grep `startNvmeReinsertWatcher(` → only the definition). Even if called it would skip itself when `/run/apertar-cfe/ready` exists (`:757-758`) | Candidate list (`:775-791`) | C |

`run_pi_direct.sh` reads **no** `[display]` keys. It picks the main connector from DRM sysfs alone. The first
connected internal connector (DPI, DSI and so on) wins over HDMI (`UI:run_pi_direct.sh:125-166`). **C.** This is
why a DPI overlay with no panel attached took the touch UI away from HDMI (KB source note §4.5).

### 1.2 Each reader of `apertar-hardware.conf` in the UI repo

| Reader | Sections / keys | File selection | Parser | Read when | Re-read? | Ref | Label |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `DisplayConfigBridge::loadConfiguration` | `[display]`: `ui_width`, `ui_height`, `ui_layout`, `ui_rotation` (+aliases), `controls_opacity`, `zoom_toggle_factor`, `windowed`, `hdmi_external_only` | Candidates `UI:src/DisplayConfigBridge.cpp:25-39`. **First existing file wins and the loop breaks, even if it has no `[display]`** (`:589-653`) | `QSettings(path, IniFormat)`, group `display` (`:595-596`) | Constructor (`:569-573`), built at `UI:src/main.cpp:278` (normal) and `:133` (monitor-only) | No. All properties are `CONSTANT` (`UI:src/DisplayConfigBridge.hpp:9-23`). **Restart the UI** | as cited | C |
| `Ina219Bridge::loadConfiguration` | `[ina219]`: `enabled`, `bus` (`channel`, `i2c_bus`), `address` (`addr`) | Candidates `UI:src/Ina219Bridge.cpp:53-67`; first existing file (`:499-536`) | `QSettings` group `ina219` (`:505-506`) | `startDeferredMonitoring` (`:457-468`): 5 s timer (`:449`) or after the first frame (`UI:src/main.cpp:494`), whichever comes first | No. **Restart the UI** | as cited | C |
| `GyroConfigBridge::loadConfiguration` | `[imu]`: `enabled`, `driver`, `sync_mode`, `sync_offset_ms` (+aliases); the active driver section (`[mpu6050]`, `[bmi160]`, `[bmi270]`, `[icm42688p]`): `enabled`, `bus`, `address`, ranges, `orientation`, level reference | First existing candidate (`UI:src/GyroConfigBridge.cpp:919-926`; list `:198-210`) | Own line parser (`:346-361` read, `:927-1075` parse) | Constructor (`:634-642`); after its own driver write (`:691`); `refresh()` (`:668-678`) | `refresh()` is `Q_INVOKABLE` (`UI:src/GyroConfigBridge.hpp:68`), **but no QML calls it** (grep `gyroConfigBridge.refresh` → none). Core's `calibrate_gyro` and WebUI IMU writes are not seen until the UI restarts | as cited | C |
| `WifiBridge::autoHotspotDelayMs` | `[network] hotspot_delay_seconds` (0–86400, default 60) | `$APERTAR_HARDWARE_CONFIG` or `/home/pi/apertar-hardware.conf` only. **No `/boot` fallback** (`UI:src/WifiBridge.cpp:19-35`) | `QSettings`, key `network/hotspot_delay_seconds`, `setFallbacksEnabled(false)` | Constructor (`:129`) in both the UI and the network helper | No. Restart `apertar-network` (the template comment says so: `UI:src/DisplayConfigBridge.cpp:61`) and the UI | as cited | C |
| `apertar-cfe-automounter` `loadConfig` | `[cfexpress_hat]`: `enabled` (default **true**), `bus`/`channel`/`i2c_bus` (default **10**), `address`/`addr` (default `0x34`). `[storage]`: `mount_path` (`/media/RAW`), `pcie_controller` (`1000110000.pcie`) | Candidates `UI:src/CfeAutomounter.cpp:114-129`; first file that `ifstream` opens (`:134-145`) | Own line parser; lower-cases section and key; strips `#`/`;` from values (`:66-77`, `:150-180`) | `main` once (`:792`) | No. **Restart `apertar-cfe-automounter`** (root: Patrik). `--check-config` prints the effective values and exits (`:793-802`) | as cited | C |
| Embedded Python (dead) | Same as the automounter | `:775-791`, `:819` | `configparser`, `optionxform=str.lower`; only `OSError` caught (`:823-826`); integers **not** comment-stripped (`parse_config_int`, `:793-802`) | Never (no caller) | — | as cited | C |

How a bad value behaves:

| Reader | Bad value | Effect | Ref | Label |
| --- | --- | --- | --- | --- |
| `DisplayConfigBridge` | Values outside range | Clamped: width/height 320–3840, opacity 0.15–1.0, zoom 1.0–4.0 | `UI:src/DisplayConfigBridge.cpp:598-638` | C |
| `DisplayConfigBridge` | Unknown layout | Derived from the size | `:474-524` | C |
| `Ina219Bridge` | Bus outside 0–255, address outside `0x03`–`0x77` | Fallback, with a log line | `UI:src/Ina219Bridge.cpp:410-439`, `:510-525` | C |
| Automounter | Bus or address out of range, or a relative `mount_path` | Default | `UI:src/CfeAutomounter.cpp:184-189` | C |
| Automounter | Missing `/dev/i2c-N` (Patrik's original symptom) | Logs "waiting for /dev/i2c-N" once and retries the open every 1 s, then every 5 s after an I/O error | `UI:src/CfeAutomounter.cpp:446-462`, `:474-496` | C |

### 1.3 The UI's template writers, and what they would write over Patrik's fix

| Writer | When | Path | Content relevant to the controls project | Ref | Label |
| --- | --- | --- | --- | --- | --- |
| T-Display `ensureDefaultHardwareConfigFile` | Every UI start (main and monitor-only) **if `/home/pi/apertar-hardware.conf` does not exist**. Ignores `$APERTAR_HARDWARE_CONFIG` | `/home/pi/apertar-hardware.conf` via `QSaveFile` | Sections listed below | `UI:src/DisplayConfigBridge.cpp:41-326`, call `:587` | C |
| T-Ina219 (second copy) | Same condition, 5 s or first frame later. Normally a no-op because T-Display ran first | same | Same content minus `[network]`, `[run_script]` and `display.zoom_toggle_factor` (key-level diff run by me) | `UI:src/Ina219Bridge.cpp:69-342`, call `:497` | C |

Sections T-Display writes:

| Section | Values | Ref (`UI:src/DisplayConfigBridge.cpp`) |
| --- | --- | --- |
| `[network]` | — | `:59` |
| `[run_script]` | — | `:63` |
| `[ina219]` | `bus=4`, `0x40` | `:70-73` |
| `[pcf8574]` | `enabled=false`, `bus=1`, `0x20`, `pin0..7=none` | `:74-100` |
| `[trigger_output]` | gpio line 17 | `:101-116` |
| `[recording_indicator]` | disabled, gpio line 17 / `pcf_pin` 7 | `:117-130` |
| `[neorotary4]` | `enabled=false`, `bus=1`, `0x49`, `poll_ms=30`, encoders 0–3 mapped to iso, shutter, wb and fps/resolution | `:131-155` |
| `[gpio_buttons]` | `enabled=false`, `d5=capture`, `d6=eject` | `:156-167` |
| `[gpio_encoders]` | `enabled=false`, encoder 0 on GPIO 5/6, press 13 | `:168-183` |
| `[grove_analog]` | — | `:184-198` |
| `[imu]` | `enabled=true`, mpu6050 | `:199-205` |
| driver sections (`[mpu6050]`, `[bmi160]`, `[bmi270]`, `[icm42688p]`) | — | `:206-296` |
| `[cfexpress_hat]` | `enabled=true`, **`bus=10`**, `0x34` | `:297-300` |
| `[storage]` | — | `:301-303` |
| `[display]` | 720x720 square | `:304-324` |

Points that matter for the project:
- **Patrik's working values differ from the template on exactly the two keys his fix needed.** His values are
  `[cfexpress_hat] bus=1` and `[neorotary4] enabled=true bus=1 address=0x49` (`KB:lessons/hardware-log.md:25`).
  The template has `bus=10` and `enabled=false`. If anything removes or renames `~/apertar-hardware.conf`, the
  next UI start regenerates the template and the hat and encoder stop working without any error on screen.
  **P**: template C; the regeneration condition at `:44-46` is C; "no error on screen" follows from §2.2, which
  found no QML surface for hardware-input status.
- The template's `[gpio_buttons]` (`d5`, `d6`) and `[gpio_encoders]` (encoder 0 on GPIO 5/6) claim the **same GPIO
  pins**. Both are disabled. **C** (`:166-167` vs `:177-178`). A GPIO dropdown fed from this template would start
  out with a conflict.
- The action catalogue in the template comments (`:76-86`) is a hand-kept copy. It is not generated from Core's
  action list. **C.** For the code side of the action list, see R1/R2.
- The live file on Patrik's Pi is probably **not** T-Display. The KB records the image's file as having
  `[recording_indicator] enabled=true target=pcf8574 bus=10 address=0x20 pcf_pin=7`
  (`KB:lessons/hardware-log.md:42-43`). T-Display has `enabled=false target=gpio`
  (`UI:src/DisplayConfigBridge.cpp:117-130`), and so does Core's WebUI template (`App:4430-4436`, within
  `defaultHardwareConfigTemplate` `App:4333`). **P**: derived from the three texts. **U**: settle with
  `grep -n '^\[' ~/apertar-hardware.conf; head -5 ~/apertar-hardware.conf`.

### 1.4 `~/.config/CinePi/UI.conf` and the other QSettings files

| File | Owner classes (process) | Read / write | Reload | Ref | Label |
| --- | --- | --- | --- | --- | --- |
| `~/.config/CinePi/UI.conf` `[General]` | `SettingsBridge` (UI main and monitor-only) | R/W through QSettings; every `set*` writes unless the external-sync guard is active | `QFileSystemWatcher` on the file and its directory, plus a 10 s poll | `UI:src/SettingsBridge.cpp:285-287`, `:411-431`, e.g. `:603` | C |
| same, `[camera]` placeholder group plus some `[General]` keys (`timecodeMode`, audio, photo keys) | `ApertarControlBridge` (UI) | R/W. The comment says the cached values are placeholders and Core owns restoration | Re-reads on demand (`m_settings.sync()` at `:794`) | `UI:src/ApertarControlBridge.cpp:118`, `:646-647`, `:794-804`, `:897-998` | C |
| same, `hotspotSsid`, `hotspotPassword` | `WifiBridge` (UI and network helper) | W in the UI (`:252`, `:262`); R in the helper every tick | Helper: `sync()` every 10 s (`:495-503`) | `UI:src/WifiBridge.cpp:127`, as cited | C |
| same, `[General]` | **Core** | R with its own line parser; W through `updateSharedUiGeneralSettings` under `settingsFile::QtIniLock` (`UI.conf.lock`, QLockFile-compatible) and `settingsFile::atomicWrite` (mkstemp, fchmod to the old mode, fsync, rename, dir fsync) | Core re-reads on commands | Path `App:359-366`; writer `App:1882-1893`; `Core:src/util/SettingsFile.hpp:36-56` (atomic), `:58-118` (lock) | C |
| `UI.conf.lock` | QSettings (UI) and Core | — | Removed by `apertar-ui-direct` `ExecStartPre` | `KB:architecture/overview.md:87` | C-KB |
| `~/.config/CinePi/DisplayCalibration.conf` | `DisplayCalibrationBridge` (UI main and monitor) | R/W | `QFileSystemWatcher` | `UI:src/DisplayCalibration.cpp:49-56` | C |
| `~/.config/Apertar/StandbyBacklights.conf` | `SleepManager` | R/W (saves backlight levels across a standby crash) | Constructor | `UI:src/SleepManager.cpp:56`, `:84`, `:123` | C |
| `~/.local/share/Apertar-UI/presets/*.apertar-preset.json` (+ legacy `~/.config/CinePi/UI/presets`) | `SettingsBridge`, Core WebUI | R/W | Watcher on the directory | `UI:src/SettingsBridge.cpp:1939-1958`, `:2211` | C |

Neither `UI.conf` nor any preset holds hardware mappings. **C** (property list `UI:src/SettingsBridge.hpp:17-92`).
The `*Order` keys (`monitoringOrder` … `favoritesOrder`) hold the touch UI's own card ordering (§2.4).

UI.conf has five writers (UI main, UI monitor-only, network helper, Core and the ApertarControlBridge path). Only
Core takes the lock explicitly. The UI side relies on QSettings' internal QLockFile. **P**: QSettings uses
`<file>.lock` internally (Qt behaviour); Core's comment says so (`Core:src/util/SettingsFile.hpp:58`).

### 1.5 Other system files the UI reads

| File | Reader | Purpose | Ref | Label |
| --- | --- | --- | --- | --- |
| `/boot/firmware/config.txt` | `SystemActionBridge::refreshFanMode` | Detect the `# BEGIN/END APERTAR FAN MODE` block | `UI:src/SystemActionBridge.cpp:672-683` | C |
| `/boot/firmware/config.txt` | `DeviceInfoBridge::detectSensorName` | Last-resort sensor token scan (first 4096 bytes) | `UI:src/DeviceInfoBridge.cpp:231` | C |
| `/boot/firmware/camera-selection.txt` | `DeviceInfoBridge` | "authoritative" sensor token. **No writer in either repo** (grep) | `UI:src/DeviceInfoBridge.cpp:213-217` | C |
| `/proc/device-tree/panel/*`, `/sys/class/leds/wittypi_led/...` | `SleepManager::panelLedPath` | Detects the Waveshare 720x720 DPI panel, whose backlight is an active-low **GPIO18** LED | `UI:src/SleepManager.cpp:29-50` | C |
| `/sys/class/drm/<card>-DPI-<n>` | `DisplayStandbyController` | DPI connector detection | `UI:src/DisplayStandbyController.cpp:14-33` | C |
| `/sys/class/input/event*/device/name == pwr_button` | `PowerButtonBridge` | Pi power button | `UI:src/PowerButtonBridge.cpp:126-140` | C |
| `/dev/i2c-N` | `Ina219Bridge` | Opens its own bus | `UI:src/Ina219Bridge.cpp:558` | C |
| `/dev/i2c-N` | `GyroConfigBridge` | Opens its own bus; auto-probe described below | `UI:src/GyroConfigBridge.cpp:1100`, `:1146-1216` | C |
| `/dev/i2c-N` | Automounter | Opens its own bus | `UI:src/CfeAutomounter.cpp:393` | C |
| `/run/apertar-cfe/ready`, `/run/apertar-network/managed`, `/run/apertar-ui/*` | various | Readiness markers | `UI:src/CfeAutomounter.cpp:40`, `:530-531`; `UI:src/WifiBridge.cpp:156`, `:479`; `UI:src/main.cpp:408`, `:465` | C |

The gyro auto-probe opens **every** `/dev/i2c-0..32` that exists. On each it selects `0x68`, `0x69` and the
configured address and reads a chip-ID register. It runs at most every 30 s while live polling has no device.
**C** (`UI:src/GyroConfigBridge.cpp:1151-1216`). It never touches `0x49` or `0x34`, so it does not collide with
the NeoRotary or the hat. **P** (from the address list). It does put traffic on the camera bus (10) and on bus 1.

### 1.6 Every reader of `[cfexpress_hat]` at both tips

Patrik's fix moves the hat to bus 1, so every one of these must agree:

| Reader | Default `enabled` | Default bus | Read when | After a change | Ref | Label |
| --- | --- | --- | --- | --- | --- | --- |
| `apertar-cfe-automounter` (root) | **true** | 10 | daemon start | restart the unit (sudo) | `UI:src/CfeAutomounter.cpp:104-112`, `:792` | C |
| Core media watcher thread (`CfeHatReader`, new on Patrik's branch) | **false unless the section exists** | 10 | thread start | restart Core | `App:4550-4598`, `:9310-9314`; `Core:src/util/CfeHat.hpp:18-22` | C |
| Core embedded Python reinsert watcher | true | 10 | each eject | none | `App:3419-3484`, `:3600-3603` | C |
| UI embedded Python watcher | true | 10 | never (no caller) | — | `UI:src/MediaStatusBridge.cpp:769-773` | C |

The defaults disagree. With no `[cfexpress_hat]` section, the automounter polls bus 10 and Core's watcher is off.
**C.** Effect of `bus=1 # comment`: the automounter strips the comment; both Python copies fall back to 10
(integer not comment-stripped). **C** for the UI copy (`UI:src/MediaStatusBridge.cpp:793-802`). **P** for the
Core copy (KB `config.md:62` says the same; I did not reopen `App:3440-3460`).

---

## 2. Touch UI pages that show or change hardware settings

### 2.1 What exists today (`UI:qml/SettingsPage.qml`, 9875 lines)

Section membership comes from the `default*Order` arrays (`:781-847`).

**Record → `gyroData`** (card begins around `:3535`). Effect timing: immediate in the UI's own live view. Core
re-reads IMU config per recording, so it sees the change at the next take. **P** for Core (KB `config.md:48`).
**C** for the UI.

| Item | Shows / changes | Bridge call | Backing store | Ref | Label |
| --- | --- | --- | --- | --- | --- |
| IMU driver dropdown | Changes `[imu] driver` | `gyroConfigBridge.setDriverName` | Direct file write | `:3627-3640` → `UI:src/GyroConfigBridge.cpp:680-697` | C |
| Orientation | Changes the driver section `orientation` | `setOrientation` | Direct file write | `:3697-3706` → `:862-878` | C |
| Sync offset ± / reset | Changes `[imu] sync_offset_ms` | `adjustSyncOffsetMs`, `resetSyncOffset` | Direct file write | `:3712-3740` → `:881-903` | C |
| Set / clear level | Changes the driver section `level_*` | `setLevelReference`, `clearLevelReference` | Direct file write | `:3668`, `:3678` → `:803-860` | C |
| Live sample | Shows readings | `setLivePollingRequest` | UI polls I2C itself | `:2146`, `:2174` | C |
| "Calibrate" | Gyro bias | `apertarControlBridge.calibrateGyro()` → socket `calibrate_gyro`. **Core** writes the bias | Core | `:1409`; `UI:src/ApertarControlBridge.cpp:845-848`; `App:10171` | C |

**Record → `gyroData` toggle:** "Record Gyro Data" changes `recordGyroEnabled` in UI.conf (`:3586-3593`), not
the hardware file. C.

**System → `battery`, `batteryInfo`:**
- Shows INA219 voltage, current, power and percent from `powerBridge.*` (`:245-248`, `:4084`, `:4472-4535`). C.
- When the sensor is missing it reads "INA219 Unavailable / Check /home/pi/apertar-hardware.conf and INA219
  wiring" (`:4507-4526`). C.
- It cannot edit `[ina219]`. Battery type and capacity are UI.conf keys. C.

**System → `thermal`:**
- Shows CPU temperature and has a fan mode dropdown (Silent / Auto / Full Blast).
- It calls `systemActionBridge.applyFanMode(mode)`, which writes `/boot/firmware/config.txt` through
  `sudo -n install` (§3.3) (`:5358-5410`, `:1781`). C.
- The new mode takes effect after a reboot: "Restart the camera to apply the new thermal profile" (`:9452`). C.

**System → `uiOrientation`:** changes `uiOrientation` in UI.conf (`:4637-4662`), **not** `[display] ui_rotation`.
The panel rotation stays file-only (`UI:qml/Main.qml:60`). C.

**System → `cameraControlsOpacity`:** changes UI.conf `cameraControlsOpacity` and `cameraControlsMode`
(`:4682-4727`). `[display] controls_opacity` is only the default (`UI:src/main.cpp:320`). C.

**System → `displayCalibration`:** the panel per screen writes `DisplayCalibration.conf` (`:4664`;
`UI:src/DisplayCalibration.cpp:49`). C.

**System → `cameraStandby`, `autoPowerOff`, `powerActions`:**
- These change UI.conf keys, or call Core `enterStandby` / systemd reboot and poweroff (`:4550-4636`, `:5418-5450`;
  `UI:src/SystemActionBridge.cpp:274-282`). C.
- The standby text says "A hardware button … wakes the camera" (`:4581`). C.

**Wi-Fi → `hotspot` etc.:**
- Calls `wifiBridge.startHotspot`, `stopHotspot` and `setWifiEnabled` (`:5494`, `:5780`, `:5791`). These use
  nmcli and write the UI.conf hotspot keys. C.
- `[network] hotspot_delay_seconds` is not editable here. C.

**Info → `camera`, `sbc`, `systemInfo`, `systemDrive`:** read-only device info, including the sensor name from
`camera-selection.txt` or `config.txt` (`:6017-6130`). C.

**Power → `media`, `formatMedia`, `mediaSpeed`:** media status, format and speed test through Core (`:4969-5357`).
They show no hat bus or address. C.

### 2.2 What does not exist

- No card, dropdown or text for: `[pcf8574]`, `[gpio_buttons]`, `[gpio_encoders]`, `[neorotary4]`,
  `[grove_analog]`, `[trigger_output]`, `[recording_indicator]`, `[run_script]`, `[cfexpress_hat]`, `[storage]`,
  `[display]`, `[network]`. **C**: case-insensitive grep of `UI:qml/*.qml` for `cfexpress|i2c|gpio|pcf|encoder|hardware`
  finds only the INA219 hint (`:4526`), the standby text (`:4581`) and unrelated hits.
- No view of I2C buses, no device probe, and no display of hardware-input errors. Core's input drivers keep
  `lastError()`, but the KB note says nothing reads it (`KB:sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md:156`).
  **C-KB.** Not re-checked at `0296ed1`. **U**: `grep -n lastError App` near `get_state`.
- The UI's only link to physical controls is the `hardware_action` event from Core. `ApertarControlBridge` emits
  `hardwareActionTriggered` (`UI:src/ApertarControlBridge.cpp:1269-1273`). `Main.qml` handles these UI-local
  actions (`UI:qml/Main.qml:288-332`). C.

  | Action | `Main.qml` line |
  | --- | --- |
  | `power_button_press` | `:289` |
  | `standby_power_sleep` | `:297` |
  | `standby_power_wake` | `:301` |
  | `zoom_toggle` | `:307` |
  | `settings` | `:313` |
  | `clip_browser` | `:319` |
  | `quick_menu` | `:325` |

  Core publishes them in these places. C:

  | Publisher | Ref |
  | --- | --- |
  | Toggle actions | `App:8646-8655` |
  | Power button | `App:8790-8801` |
  | Zoom | `App:8845` |
  | Still mode | `App:9097` |
  | `settings` / `clip_browser` / `quick_menu` | `App:9142-9145` |

  A method catalogue for button or knob assignment has to include these UI-handled names.

### 2.3 Two paths for the same writes (touch UI direct vs Core "API")

| Setting | Touch UI path | WebUI / socket path (Core) | Label |
| --- | --- | --- | --- |
| IMU driver | `GyroConfigBridge::setDriverName` → `writeConfigValue` (`UI:src/GyroConfigBridge.cpp:680`, `:1577-1653`) | `set_imu_driver` (`App:10112`) → `Mpu6050RecordingSession::setConfiguredDriver` (`Core:src/hardware/Mpu6050RecordingSession.cpp:1295`) | C |
| IMU orientation | `setOrientation` (`:862`) | `set_imu_orientation` (`App:10122`) | C |
| IMU sync offset | `setSyncOffsetMs` / `adjust…` / `reset…` (`:881-903`) | `set/adjust/reset_imu_sync_offset` (`App:10132-10158`) | C |
| IMU level reference | `setLevelReference` / `clearLevelReference` (`:803-860`) | `set/clear_imu_level_reference` (`App:10159-10170`) | C |
| Gyro bias | via Core only (`calibrate_gyro`) | `calibrate_gyro` (`App:10171`) → `updateImuBiasConfig` (`Mpu6050RecordingSession.cpp:715`) | C |
| Fan mode | `SystemActionBridge::applyFanMode` (`UI:src/SystemActionBridge.cpp:419-480`) | `set_fan_mode` (`App:11034`) → `applyFanMode` (`App:3159-3210`) | C |
| Whole file, raw | none | WebUI "Apertar Config" textarea, `GET/POST /api/config` (`Web:3840-3870`, `Web:10355-10400`; `App:7314-7340`; save `App:5463-5521`; 256 KiB cap `App:66`) | C |

Core already exposes hardware-config writes as socket commands, and the WebUI uses them. The touch UI bypasses
them for the IMU and the fan. **C.** The IMU commands are in Core's `help` list (`App:9634`). **C.**

### 2.4 Touch UI building blocks a hardware page would use

| Need | Existing piece | Ref | Label |
| --- | --- | --- | --- |
| Dropdown | `InlineDropdownField` (`label`, `value`, `options`, `popupParent`, `dropdownController`, `fieldEnabled`, signal `valueSelected`) and `SettingsChoice` (adds `optionDisplayFormatter`, `available`) | `UI:qml/InlineDropdownField.qml:6-32`; `UI:qml/SettingsChoice.qml:6-33`; used for the IMU driver at `SettingsPage.qml:3627-3640` | C |
| ± stepper, hold-to-act button, toggle, card | `AdjustNumberTile` (`decrementRequested`, `incrementRequested`), `ActionTile` (`holdToActivate`), `TogglePill`, `SystemSectionCard` | `UI:qml/AdjustNumberTile.qml:6-19`; `UI:qml/ActionTile.qml:6-12` | C |
| Drag-and-drop | Press-and-hold on any card opens a reorder popup with a drag delegate that calls `reorderListModel.move(...)`. The sidebar has its own drag. The order is saved in UI.conf `*Order` keys | `openReorderPopup` `:1251`; delegate `:6135-6175`; sidebar `:6262-6270`; popup `:7521-7591`; `applySectionOrder` `:1050-1072` | C |
| Favourites | A new card id must be added to `favoriteCandidateOrder` to be pinnable | `:848-888` | C |
| Section placement | A new card id goes in a `default*Order` array and a `*ComponentForId` branch | `:781-847`; KB recipe `KB:llm/change-recipes.md:107` | C / C-KB |
| New QML file | Must be added to **both** `APERTAR_QML_FILES` (AOT) and `qml.qrc` (non-AOT) | `UI:CMakeLists.txt:19-52`; `UI:qml.qrc:1-35` | C |

`UI:qml/InlineChoice.qml` exists but is in neither list and no file uses it, so it is dead. **C.**

---

## 3. System side: units, install files, packaging, ownership, config.txt

### 3.1 Files shipped in the repos

| Repo file | Intended install target (as the file or KB states) | Owner / mode | What it does | Installed on Patrik's Pi? | Label |
| --- | --- | --- | --- | --- | --- |
| `UI:systemd/apertar-network.service` | `/etc/systemd/system/` | root 0644 (P: systemd convention) | `User=pi`, `Group=pi`, `HOME=/home/pi`, `RuntimeDirectory=apertar-network`, `ExecStart=/home/pi/ApertarUI/build/apertar-network-helper`, `Restart=on-failure` (`:1-19`) | yes (`KB:architecture/overview.md:143` shows the unit exists) | C / C-KB |
| `UI:systemd/apertar-network-start-gate.conf` | drop-in for `apertar-network` | — | `ExecStartPre=-/usr/local/libexec/apertar-wait-ui-core-start /run/apertar-ui/main-ui-ready 8` (`:1-4`) | **no** (`KB:architecture/overview.md:143`) | C / C-KB |
| `UI:systemd/49-apertar-network.rules` | polkit rules dir (P: `/etc/polkit-1/rules.d/` from the name) | root | Lets user `pi` control NetworkManager (6 actions) (`:1-12`) | U: `ls /etc/polkit-1/rules.d/` | C (content) |
| `UI:systemd/90-apertar-backlight.rules` | udev rules dir (P: `/etc/udev/rules.d/`) | root | `chgrp video` + `g+w` on backlight `brightness` and on `wittypi_led` `brightness`/`trigger` (`:1-2`) | U: `ls /etc/udev/rules.d/` | C (content) |
| `UI:systemd/apertar-standby-usb.sudoers` | `/etc/sudoers.d/` | root 0440 (P: sudoers convention) | `pi` may run `/usr/local/libexec/apertar-standby-usb off\|on` without a password (`:1`) | P: Core calls it with `sudo -n` (`App:1576`); `KB:architecture/build.md:137-138` lists it | C (content) |
| `UI:systemd/apertar-standby-low-power.sudoers` | `/etc/sudoers.d/` | root 0440 | `pi` may run `apertar-standby-low-power cpu\|nvme\|bluetooth\|all\|restore` (`:1`) | as above (`App:1581`) | C (content) |
| `Core:config/apertar-core-capture-priority.conf` | drop-in for `apertar-core` | — | `LimitNICE=-5` (`:1-3`) | U: `systemctl cat apertar-core` | C (content) |
| `Core:config/apertar-media.sudoers` | `/etc/sudoers.d/apertar-media`, `sudo install -m 0440` (`:1`) | root 0440 | `pi` → `/usr/local/libexec/apertar-media-tune` (`:3`) | **no**: "helper not installed" (`KB:tutorials/README.md:118`) | C / C-KB |
| `Core:config/apertar-media.tmpfiles.conf` | `/etc/tmpfiles.d/apertar-media.conf` (`:1`) | root 0644 | `/run/apertar-media{,/eject}` owned pi:pi 0755, `/run/apertar-media/tune` owned root:root (`:3-5`) | P: not installed (same T29 row) | C |
| `Core:scripts/apertar-media-tune` | `/usr/local/libexec/` | root | Root helper with fixed actions `apply` / `restore`. Saves the originals under `/run/apertar-media/tune`, logs every write (`:1-30`) | no (as above) | C |
| `Core:scripts/start-apertar-core.sh` | `/home/pi/start-apertar-core.sh` (P from the KB) | pi | Env → `--socket`, `--media` (`:1-21`) | yes (`KB:architecture/overview.md:11`) | C / C-KB |
| `UI:wait_for_ui_core_start.sh` | `/usr/local/libexec/apertar-wait-ui-core-start` | root | Core start gate | yes, byte-identical (`KB:architecture/overview.md:144`) | C-KB |
| `UI:finish_plymouth_handoff.sh` | run in place by `ExecStartPost` | pi | Plymouth quit | yes (`KB:architecture/build.md:218`) | C-KB |
| CMake `install()` | Core: `bin`, `lib/apertar-core` (`Core:CMakeLists.txt:190-195`). UI: only the video plugin (`UI:CMakeLists.txt:144`) | — | No `install()` for units, sudoers, the automounter or helpers | — | C |

There is no image recipe or packaging (no `debian/`, no image script) in either repo. **C** (directory listings).
`KB:working/distribution-image.md` is a draft and has not been run (`:3`). It already lists
`~/apertar-hardware.conf`, `~/apertar-hardware.conf.bak` and `/boot/firmware/config.txt` as items to swap or strip
when imaging (`:46-48`). **C-KB.**

### 3.2 On the Pi, not in either repo (from the KB)

| Item | What the KB records | Ref | Label |
| --- | --- | --- | --- |
| `apertar-core.service` | Runs `/home/pi/start-apertar-core.sh`. `HOME=/home/pi` in the running process | `KB:architecture/overview.md:11`, `:148` | C-KB |
| `apertar-ui-direct.service` | `Environment=APERTAR_CORE_START_READY_FILE=…`. `ExecStartPre` removes `UI.conf.lock`. `ExecStartPost=+…finish_plymouth_handoff.sh` | `KB:architecture/overview.md:87`; `KB:architecture/build.md:217-218` | C-KB |
| `apertar-cfe-automounter.service` | `User=` empty, so it runs as **root**. `After/Wants=media-RAW.service` | `KB:architecture/overview.md:15`, `:145` | C-KB |
| `media-RAW.service` | Oneshot `/usr/local/bin/mount-raw.sh` | `KB:architecture/overview.md:146` | C-KB |
| `/usr/local/libexec/*` | root:root 755; must be copied by hand after a rebuild | `KB:architecture/build.md:142`, `:164` | C-KB |
| `pi` and the journal | `pi` cannot read the journal without sudo | `KB:architecture/overview.md:150` | C-KB |

**No unit sets `APERTAR_HARDWARE_CONFIG`.** **P**: the KB lists the environment of core, ui-direct and network,
and none has it (`KB:architecture/config.md:349`; `UI:systemd/apertar-network.service:10-11`). The automounter
unit's environment is not recorded. **U**: `systemctl show -p Environment apertar-core apertar-ui-direct
apertar-network apertar-cfe-automounter`.

The KB contradicts itself on users. `KB:architecture/config.md:20` says "every unit runs as `User=pi`", but
`KB:architecture/overview.md:145` records the automounter as root. **C** (both lines opened). For this project
the automounter is a **root** reader.

### 3.3 `config.txt`, overlays and other boot files

| Item | Reader / writer | How | Ref | Label |
| --- | --- | --- | --- | --- |
| Fan block | **Writer** (UI) | Reads the file, strips the old marked block, appends the new block at the **end**, writes a `QTemporaryFile`, then `sudo -n install -m 644 tmp /boot/firmware/config.txt` | `UI:src/SystemActionBridge.cpp:22-25`, `:64-142`, `:419-480`, `:609-650` | C |
| Fan block | **Writer** (Core, socket/WebUI) | Same algorithm, temp `/tmp/apertar-fan-mode-<pid>.tmp` | `App:2875-2877`, `:3151-3210` | C |
| `dtoverlay`, `dtparam=i2c_arm`, DPI lines, `[pi5]` filters | nobody in either repo | — | grep `dtoverlay\|i2c_arm\|raspi-config\|dtparam=i2c` over both trees: no code hits (only the fan `dtparam=fan_*` lines) | C |
| `camera-selection.txt` | Reader: UI `DeviceInfoBridge`. Writer: not in the repos | — | `UI:src/DeviceInfoBridge.cpp:215` | C |
| Overlay effects the UI depends on | `SleepManager` assumes the Waveshare DPI overlay's GPIO18 LED. `run_pi_direct.sh` prefers any connected DPI connector | — | `UI:src/SleepManager.cpp:35-50`; `UI:run_pi_direct.sh:139-147` | C |

Consequences:
- **The fan writers rely on a passwordless `sudo install` rule.** No sudoers file in either repo grants it. **C**
  (§3.1 list). Whether the image has one is **U**: `sudo -n -l` as pi, look for `install`.
- **Both writers append the block at the end of `config.txt`.** If the last conditional filter in the file is a
  model filter such as `[cm4]` or `[pi4]`, the fan `dtparam`s apply only under that filter. **P**: the code
  appends after `trimmed()` (`UI:src/SystemActionBridge.cpp:439-442`); Pi firmware applies lines under the last
  filter seen.
- **These writers already break Patrik's rule** that he alone edits `/boot/firmware/config.txt`. A
  "system-controlled config" that also wrote the `i2c_arm` or DPI lines would break it further. The DPI and I2C
  part of his fix stays a tutorial step he types; the system can only detect and report (§4.7).

### 3.4 Locations and ownership

| Path | Expected owner | Writers today | Readers | Label |
| --- | --- | --- | --- | --- |
| `/home/pi/apertar-hardware.conf` | pi (created by the UI as pi; replaced by renames from pi processes) | UI template, UI gyro, Core WebUI, Core IMU, operator | UI ×4 classes, network helper, automounter (root), Core (≈10 readers) | P for owner. **U**: `stat -c '%U:%G %a' ~/apertar-hardware.conf` |
| `/home/pi/apertar-hardware.conf.bak` | pi | Core WebUI save (`App:5496-5507`) | nobody | C; it exists on the Pi (`KB:working/distribution-image.md:46`) C-KB |
| `/home/pi/apertar-hardware.conf.tmp` | pi | Core WebUI (`App:5510`) **and** Core IMU (`Core:src/hardware/Mpu6050RecordingSession.cpp:687`, `:816`) | — | C |
| `/home/pi/apertar-hardware.conf.XXXXXX` | pi | `QSaveFile` temps (UI) | — | P: Qt's QSaveFile naming |
| `/boot/firmware/apertar-hardware.conf`, `/boot/apertar-hardware.conf` | root (FAT) | operator from a card reader | every candidate-list reader. Dead once the `/home/pi` file exists, **except** Core readers that fall through when their section is missing (PCF, GPIO, NeoRotary4, Grove) | C for NeoRotary4 (`Core:src/hardware/NeoRotary4Input.cpp:360-443`, `return` only if `configured`); others C-KB (`KB:architecture/config.md:40`) |
| `/boot/firmware/config.txt` | root | Patrik (sudo); UI and Core fan block (`sudo -n install`) | UI fan detect, UI sensor scan, Core fan detect, firmware | C |
| `~/.config/CinePi/UI.conf` (+ `.lock`) | pi | UI, network helper, Core | same | C |
| `/etc/systemd/system/apertar-*.service` | root | Patrik | systemd | C-KB |
| `/etc/sudoers.d/*` | root 0440 | Patrik | sudo | P |
| `/usr/local/libexec/apertar-*` | root:root 755 | Patrik (`sudo install`) | Core (`sudo -n`), systemd | C-KB |
| `/run/apertar-cfe/ready`, `/run/apertar-network/*`, `/run/apertar-ui/*`, `/run/apertar-standby-*`, `/run/apertar-media/*` | root (automounter), pi (others) | the respective process | UI, Core | C |

No code uses `/etc/apertar`, `/var/lib/apertar` or `/usr/share/apertar`. **C** (grep over both trees).

### 3.5 Device access for I2C and GPIO

- **I2C bus owners.** The UI-repo openers of `/dev/i2c-N` are `Ina219Bridge` (pi), `GyroConfigBridge` (pi) and
  the automounter (root). Core opens buses for INA219, PCF8574, NeoRotary4, Grove, IMU, trigger and LED, and the
  hat watcher. Nothing arbitrates between processes. **C** for the UI side (§1.5). The KB says the same for all
  of them (`KB:architecture/overview.md:51`).
- **Groups.** Whether `pi` processes get the `i2c` and `gpio` groups is **U**: `id pi; ls -l /dev/i2c-* /dev/gpiochip*`.
  The KB says the UI runs with groups `video render input` (`KB:architecture/overview.md:12`).
- **INA219 is on two I2C clients.** Core and the UI both open the INA219 and both write its config registers
  (`KB:architecture/config.md:102`). **C-KB.** I confirmed the UI side writes registers (`UI:src/Ina219Bridge.cpp:568-571`). **C.**

---

## 4. What a "system-controlled config file" must respect

### 4.1 Who writes the hardware file today

| Writer | Process / user | Trigger | Mechanism | Lock | fsync | Backup | Ref | Label |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| UI template (T-Display, T-Ina219) | Apertar-UI main **and** monitor-only, pi | `/home/pi/…` missing at start | `QSaveFile` (temp + rename) of the full template | none | P: QSaveFile commit does not fsync | none | `UI:src/DisplayConfigBridge.cpp:41-326`; `UI:src/Ina219Bridge.cpp:69-342` | C |
| UI gyro page | Apertar-UI, pi | each gyro edit | read all lines → replace or insert one key → `QSaveFile` | none | P: none | none | `UI:src/GyroConfigBridge.cpp:346-392`, `:1577-1653` | C |
| Core WebUI raw editor | Core, pi | "Save Config" | copy to `.bak` → write `<file>.tmp` → `rename`. Rejects empty, NUL or > 256 KiB text | none; **no mtime/version check** (the POST body is the text only) | none (`writeTextFileRaw` = `ofstream` + `flush`, `App:1593-1601`) | `.bak` | `App:5463-5521`, `:7321-7340`; `Web:10383-10387` | C |
| Core IMU commands (`set_imu_*`, `calibrate_gyro`) | Core, pi | WebUI or socket command | read lines → edit → `<file>.tmp` → `rename`. **If the rename fails it `remove(path)`s the real file and retries** | none | none | none | `Core:src/hardware/Mpu6050RecordingSession.cpp:604-712`, `:715-840` (`:700-705` for remove-then-rename) | C |
| Operator | pi (`nano`, `sed` over SSH), or root from a card reader for `/boot` copies | by hand | P: an in-place rewrite of the same inode (nano's default) | none | — | none | — | P |
| Image builder | — | image creation | ships its own file (§1.3, last bullet) | — | — | — | `KB:lessons/hardware-log.md:42-43` | P |

**Concurrency hazards that exist now:**

| # | Hazard | Ref | Label |
| --- | --- | --- | --- |
| 1 | Lost update: the UI gyro page and the Core WebUI both read, modify and write the whole file. Whichever saves second drops the other's change. The WebUI textarea can hold minutes-old text | as above | P (no lock or version in any writer: C) |
| 2 | Two Core writers share the temp name `<file>.tmp`. A WebUI save and an IMU command at the same moment can rename each other's half-written temp | `App:5510`; `Mpu6050RecordingSession.cpp:687`, `:816` | C (same name); P (interleaving) |
| 3 | The Core IMU writer deletes the live file before its second rename attempt. A failure there leaves no config, and the next UI start writes the template (§1.3) | `Mpu6050RecordingSession.cpp:700-705` | C (code); P (outcome) |
| 4 | The UI template writer races the operator. If the file is briefly absent (an editor that writes by rename, or a migration step), the UI recreates it from the template | `UI:src/DisplayConfigBridge.cpp:44-46` | C (condition); P (race) |
| 5 | No reader holds a lock while reading. Readers that use `ifstream` can see a half-written file only from an in-place writer (the operator). The rename writers are atomic for readers | — | P |

UI.conf shows the only cooperative pattern in the stack: `settingsFile::QtIniLock` plus `atomicWrite`, which keeps
the mode, fsyncs, renames and fsyncs the directory (`Core:src/util/SettingsFile.hpp:36-118`). **C.** It keeps the
mode but not the owner (`fchmod` only, `:44-46`). **C.**

### 4.2 Restart or reload needed per reader after the file changes

| Reader | Sections | Picks up a change when | Who can do that | Ref | Label |
| --- | --- | --- | --- | --- | --- |
| Apertar-UI `DisplayConfigBridge` (main and monitor) | `[display]` | UI restart | `sudo systemctl restart apertar-ui-direct` (Patrik) | `UI:src/DisplayConfigBridge.hpp:9-23` (CONSTANT) | C |
| Apertar-UI `Ina219Bridge` | `[ina219]` | UI restart | same | `UI:src/Ina219Bridge.cpp:457-468` | C |
| Apertar-UI `GyroConfigBridge` | `[imu]` + driver | UI restart, or the UI's own write | same | §1.2 | C |
| Apertar-UI `WifiBridge` | `[network]` | UI restart | same | `UI:src/WifiBridge.cpp:129` | C |
| `apertar-network-helper` | `[network]` | service restart | `sudo systemctl restart apertar-network` | same | C |
| `apertar-cfe-automounter` | `[cfexpress_hat]`, `[storage]` | service restart | `sudo systemctl restart apertar-cfe-automounter` | `UI:src/CfeAutomounter.cpp:792` | C |
| Core inputs and outputs (PCF8574, NeoRotary4, GPIO, Grove, trigger, REC LED) | their sections | Core restart | `sudo systemctl restart apertar-core` | `App:7026-7038` (single `start()` calls; each `loadConfig()` at `Pcf8574Input.cpp:276`, `NeoRotary4Input.cpp:313`, `GpioInput.cpp:332`, `GroveAnalogInput.cpp:204`, `TriggerOutput.cpp:366`, `RecordingIndicatorOutput.cpp:405`) | C |
| Core INA219 | `[ina219]` | Core restart (`static const`) | same | `App:4695` | C |
| Core media watcher | `[cfexpress_hat]` | Core restart | same | `App:9310` | C |
| Core IMU | `[imu]` + driver | next recording, calibration or command | none needed | `Mpu6050RecordingSession.cpp:1040`, `:1176`, `:1297-1396` | C |
| Core `run_script` | `[run_script]` | each action. **Reads only `$APERTAR_HARDWARE_CONFIG` or `/home/pi/…`** | none needed | `App:8841`; `Core:src/hardware/HardwareScriptRunner.cpp:38-96` | C |
| Core NVMe Python watcher | `[cfexpress_hat]`, `[storage]` | each eject | none needed | `App:3466-3603` | C |
| Firmware | `config.txt` (DPI, `i2c_arm`) | reboot | Patrik | — | P (Pi firmware) |

For Patrik's fix the minimum is a reboot, for the overlay, which also restarts everything else. A bus-only
change to `[cfexpress_hat]` needs **both** the automounter and Core restarted. A `[neorotary4]` change needs Core
only. **C** (rows above). No process offers a reload signal, and Core has no `reload` command (grep `reload|SIGHUP`
in `App`: none). **C.** The WebUI tells the user restarts "may" be needed (`Web:3869`). **C.**

### 4.3 How the file is found

These constraints apply to any new location:
1. **The candidate list is hard-coded in at least 9 places.** **C** for each:

   | Place | Ref |
   | --- | --- |
   | `DisplayConfigBridge` | `UI:src/DisplayConfigBridge.cpp:25-39` |
   | `Ina219Bridge` | `UI:src/Ina219Bridge.cpp:53-67` |
   | `GyroConfigBridge` | `UI:src/GyroConfigBridge.cpp:198-210` |
   | `WifiBridge` (env or `/home/pi` only) | `UI:src/WifiBridge.cpp:19-23` |
   | Automounter | `UI:src/CfeAutomounter.cpp:114-129` |
   | UI Python | `UI:src/MediaStatusBridge.cpp:775-791` |
   | Core `hardwareConfigCandidatePaths` | `App:4293-4311` |
   | Core editable path (env or `/home/pi` only) | `App:4313-4318` |
   | Core Python | `App:3436-3443` |
   | `NeoRotary4Input` (own copy) | `Core:src/hardware/NeoRotary4Input.cpp:73-89` |

   The KB counts about 14 parsers in all (`KB:architecture/config.md:9`). A new path means editing every copy, or
   pointing `$APERTAR_HARDWARE_CONFIG` at it in **every** unit, including the root automounter's.
2. **The env var does not reach the template writers.** Both template writers always test and write
   `/home/pi/apertar-hardware.conf` (`UI:src/DisplayConfigBridge.cpp:43`; `UI:src/Ina219Bridge.cpp:71`). Moving
   the file elsewhere and leaving `/home/pi` empty therefore creates a stray template at `/home/pi` at the next UI
   start. Readers without the env var then use that template, and readers with it use the new file. **C** (code);
   P (outcome).
3. **A symlink at `/home/pi/apertar-hardware.conf` would be broken by Core's writers.** The WebUI and IMU writers
   `rename()` a temp over the path, which replaces the symlink with a regular file (POSIX rename semantics). The
   two copies then fork without notice. **P.** `QSaveFile` behaviour on a symlink is **U**: test on the Pi with a
   throwaway file.
4. **`/boot/firmware` copies are not a safe "system" location.** They are shadowed once `/home/pi` exists, except
   for the Core readers that fall through (§3.4 row). That gives a mixed state in which `[neorotary4]` can come
   from `/boot` while everything else comes from `/home/pi`. **C** (NeoRotary4 code) / C-KB (others).

### 4.4 Format rules a machine writer must keep so that manual editing still works

| Rule | Why (which parser breaks) | Ref | Label |
| --- | --- | --- | --- |
| Never write inline comments after values | Core INA219 and both Python copies do not strip comments from integers (`bus=1 # x` → default). The automounter, NeoRotary4 and PCF8574 do strip them | `UI:src/MediaStatusBridge.cpp:793-802`; KB `config.md:62`; `UI:src/CfeAutomounter.cpp:66-77`; `NeoRotary4Input.cpp:375-377` | C / C-KB |
| No duplicate sections or keys, no `%` in values | Python `configparser` (default `strict=True`, `BasicInterpolation`) raises; only `OSError` is caught, so the Core watcher dies silently | `UI:src/MediaStatusBridge.cpp:820-826` (Core copy per KB `config.md:66`) | C (catch) / P (configparser defaults) |
| Keep section order | `[pcf8574]` must come before `[trigger_output]` and `[recording_indicator]` for bus inheritance. `[gpio_buttons]` and `[gpio_encoders]` share `chip`, `active_low`, `pull`, `poll_ms` and `debounce_ms`, and the later section wins. The `recindicatorled` shorthand inherits from the section above it | KB `config.md:138`, `:155`, `:203`; `KB:lessons/hardware-log.md:44-45` | C-KB |
| Keep comments and unknown keys | Today's line-editing writers (UI gyro, Core IMU) preserve them. Operators and the WebUI template rely on comments as documentation | `UI:src/GyroConfigBridge.cpp:1586-1640` | C |
| Section names exact and lower-case | `[run_script]` must match exactly (`HardwareScriptRunner.cpp:52`); UI QSettings groups are case-sensitive | `Core:src/hardware/HardwareScriptRunner.cpp:52`; `UI:src/DisplayConfigBridge.cpp:596` | C (Core) / P (QSettings case) |
| Aliases: read them, write the canonical name, and never write two spellings of one key | Each parser accepts a different alias set. The automounter accepts `bus\|channel\|i2c_bus`; NeoRotary4 accepts section aliases `[neo_rotary4]` and `[neo_rotary_4]`; `[grove_analog]` uses `channel=` for the **bus** while `channel0..7` are ADC inputs. If a structured writer adds `bus=` next to an existing `channel=`, which one wins depends on the parser | `UI:src/CfeAutomounter.cpp:167`; `NeoRotary4Input.cpp:384-386`; KB `config.md:183` | C / C-KB |
| Keep values unquoted and comma-free in UI-read sections | QSettings INI reads `a,b` as a list and handles quotes and backslashes its own way. `DisplayConfigBridge` unquotes by hand | `UI:src/DisplayConfigBridge.cpp:328-337` | C (unquote) / U (QSettings list and `;` handling: put `ui_width=1280 ; x` and read the startup log, `UI:src/main.cpp:281-289`) |
| `[run_script]` paths are code execution as pi | Any UI that edits `path1..5` lets the editor run arbitrary Bash at the next button press. Only `path`, `path1`–`path5` are allowed; any other `path*` key throws | `Core:src/hardware/HardwareScriptRunner.cpp:59-66`, `:232-238` | C |

### 4.5 Permissions and ownership

1. **Every current writer runs as pi.** The writers are the UI, Core, and the operator over SSH. The only root
   process is the automounter, and it only reads. **C / C-KB.** A root-owned file outside `/home/pi` (e.g. under
   `/etc`) would turn all of these into failures unless writes go through a root helper.
2. **Root ownership inside `/home/pi` protects nothing.** A rename-based writer (Core WebUI, Core IMU,
   `QSaveFile`) needs write permission on the directory, not on the file. A root-owned file in a pi-owned home can
   therefore still be replaced by pi processes, and the owner silently flips to pi. **P** (POSIX). **U**:
   `stat -c '%U %a' /home/pi`.
3. **Apertar already has a pattern for a root-side action with fixed arguments:** a helper in
   `/usr/local/libexec`, a sudoers line naming the exact path and arguments, `sudo -n` from Core, and a tmpfiles
   entry for `/run` state. Examples: `Core:config/apertar-media.sudoers:3`,
   `Core:config/apertar-media.tmpfiles.conf:3-5`, `Core:scripts/apertar-media-tune:1-30`,
   `UI:systemd/apertar-standby-*.sudoers`. **C.**
   - Under the house rules, every one of these files is a step Patrik installs himself.
   - The media helper itself has not been installed yet (`KB:tutorials/README.md:118`). **C-KB.**
4. **I2C and GPIO device access** depends on group membership. It is U (§3.5). A config UI that offers "probe this
   bus" in the touch UI runs as pi.

### 4.6 Migrating from the hand-edited `~/apertar-hardware.conf`

What is known:
- **Patrik's working keys:** `[cfexpress_hat] bus=1`; `[neorotary4] enabled=true bus=1 address=0x49`
  (`KB:lessons/hardware-log.md:25`). His tally LED setup is `[recording_indicator] enabled=true target=gpio
  line=21 active_high=true`, `[trigger_output] enabled=false`, `[pcf8574] enabled=false`, `d21=recindicatorled`
  removed (`KB:lessons/hardware-log.md:39-41`). **C-KB.** A migration must carry all of these over unchanged.
- **The file's origin is unknown.** It is probably the image's own file (§1.3), so a migration cannot assume any
  of the three templates. **P.**
- **Leftovers on the Pi:** `~/apertar-hardware.conf.bak` exists (`KB:working/distribution-image.md:46`), so the
  WebUI save has been used at least once. **C-KB.**
- **The DPI and `i2c_arm` lines are part of the same fix** but live in `config.txt`. They are Patrik's to edit
  (house rule), not a migration step.

What a migration must not do:
- Leave `/home/pi/apertar-hardware.conf` missing, even for a moment, while the UI runs, because of the template
  writer (§4.1 #4). **C** (condition).
- Rewrite or reorder the file in a way that changes what an order-sensitive parser sees (§4.4).
- Assume every reader re-reads the file. Each needs its restart from §4.2.

What to collect before designing, all read-only and runnable as pi:

```bash
grep -n '^\[' ~/apertar-hardware.conf; stat -c '%U:%G %a %y' ~/apertar-hardware.conf ~/apertar-hardware.conf.bak
ls -l /boot/firmware/apertar-hardware.conf /boot/apertar-hardware.conf 2>&1
diff ~/apertar-hardware.conf.bak ~/apertar-hardware.conf
/usr/local/libexec/apertar-cfe-automounter --check-config     # effective [cfexpress_hat]/[storage]
systemctl show -p User,Environment apertar-core apertar-ui-direct apertar-network apertar-cfe-automounter
sudo -n -l     # which passwordless rules exist (install? systemctl?)
id pi; ls -l /dev/i2c-* /dev/gpiochip*
```

### 4.7 config.txt: detect and report only

These are the facts that limit what a system config can do with `config.txt`:
- **Nothing in Apertar reads the overlay lines to explain an I2C failure.** **C** (§3.3).
- **Code to detect a DPI overlay already exists:** `DisplayStandbyController` checks DRM `*-DPI-*` connectors
  (`UI:src/DisplayStandbyController.cpp:19-33`). `SleepManager` recognises the Waveshare panel through device tree
  (`UI:src/SleepManager.cpp:35-50`). **C.** The KB note proposes a `pinctrl get 2,3` or overlay-line check and a
  one-line warning ("bus 1 is unavailable: GPIO 2/3 are taken by the DPI overlay") rather than editing the file
  (`KB:sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md:154`). **C-KB.**
- **A GPIO dropdown must know which lines a DPI overlay holds:** GPIO 0–27 for the Waveshare and HyperPixel
  overlays (`KB:sources/…:86`), GPIO18 for the Waveshare backlight LED (`UI:src/SleepManager.cpp:35-36`), and
  GPIO 2/3 for `i2c_arm` when that is on. **C-KB / C.**

---

## 5. Open items (U), each with the command that settles it

| # | Question | Command |
| --- | --- | --- |
| U1 | Origin and current sections of the live hardware file | `grep -n '^\[' ~/apertar-hardware.conf` |
| U2 | Owner and mode of the file and of `/home/pi` | `stat -c '%U:%G %a' ~/apertar-hardware.conf /home/pi` |
| U3 | Any `/boot` copy present | `ls -l /boot/firmware/apertar-hardware.conf /boot/apertar-hardware.conf` |
| U4 | `APERTAR_HARDWARE_CONFIG` or other env in units | `systemctl show -p Environment apertar-core apertar-ui-direct apertar-network apertar-cfe-automounter` |
| U5 | Passwordless sudo rules (fan `install`, `systemctl`) | `sudo -n -l` |
| U6 | I2C and GPIO device groups for `pi` | `id pi; ls -l /dev/i2c-* /dev/gpiochip*` |
| U7 | polkit and udev rules installed | `ls /etc/polkit-1/rules.d/ /etc/udev/rules.d/ \| grep apertar` |
| U8 | `capture-priority` drop-in installed | `systemctl cat apertar-core` |
| U9 | QSettings handling of `;` / `#` inline in `[display]` | put `ui_width=1280 ; x` in a copy via `APERTAR_HARDWARE_CONFIG` and read the "Apertar display config" log line |
| U10 | `QSaveFile` on a symlinked path (target or link replaced?) | throwaway test on the Pi |
| U11 | Whether Core exposes input `lastError` in `get_state` at `0296ed1` | `grep -n lastError Core:src/ApertarCoreApp.cpp` around `buildStateJson` |

---

## 6. Corrections for the KB found while reading

- `KB:architecture/config.md:20` ("every unit runs as `User=pi`") contradicts `KB:architecture/overview.md:145`
  (automounter is root). **C.**
- The KB line numbers for Core (`App:4251-4269`, `App:3380-3602`, `App:6881-6893`, `App:4602`) were taken at
  `65ccfa8`. At `0296ed1` they are:

  | Item | Old (`65ccfa8`) | New (`0296ed1`) |
  | --- | --- | --- |
  | Candidate list | `App:4251-4269` | `App:4293-4311` |
  | Python watcher | `App:3380-3602` | `App:3419-3603` |
  | Input start | `App:6881-6893` | `App:7026-7038` |
  | INA219 `static` | `App:4602` | `App:4695` |

  **C.** The UI line numbers in `KB:architecture/config.md` still match `5aab7e2` for `DisplayConfigBridge`
  (`:587`, `:575`). **C.**
- `KB:llm/change-recipes.md:80` cites `--check-config` at `CfeAutomounter.cpp:760-771`. It is `:793-802` at
  `5aab7e2`. **C.**
- The KB says the UI's Python watcher is "dead code" in an overview row (`KB:architecture/overview.md:132`). It is
  dead for a stronger reason than the ready-file check: **it has no caller at all**. **C** (grep).
