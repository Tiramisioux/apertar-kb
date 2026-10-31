# Configuration files

Every file and environment variable the Apertar stack reads, who parses it, and the defaults. Refs are against `upstream-1.6.0` + fork `.gitignore` commits (Core `65ccfa8`). `App` = `Apertar-Core/src/ApertarCoreApp.cpp`, `CC` = `Apertar-Core/src/camera/CameraController.cpp`. Runtime structure is in [core.md](core.md).

## 1. Quick reference

| File | Format | Read by | Written by | When read |
| --- | --- | --- | --- | --- |
| `~/apertar-hardware.conf` | INI, about 14 hand-written parsers | Core, UI, `apertar-cfe-automounter`, `apertar-network-helper`, two embedded Python helpers | UI (first-run template), Core WebUI editor, IMU commands, UI gyro page | Mostly once at process start (§2.2) |
| `~/apertar-color-profiles.conf` | INI | Core only | nobody (hand-made) | On every profile lookup when mtime changed |
| `~/.config/apertar-core/camera_settings.conf` | flat `key=value` | Core | Core (debounced 25 ms) | Core start |
| `~/.config/CinePi/UI.conf` | QSettings INI, `[General]` + `[camera]` | UI, Core (`[General]` only), network helper | UI (QSettings), Core (own line editor + lock) | UI: inotify + 10 s poll. Core: on most commands and every 1 s |
| `~/.config/CinePi/DisplayCalibration.conf` | QSettings | UI | UI | UI start |
| `~/.config/Apertar/StandbyBacklights.conf` | QSettings | UI | UI | standby |
| `~/.local/share/Apertar-UI/presets/*.apertar-preset.json` | JSON | UI, Core | UI, Core WebUI | on demand |
| `/boot/firmware/config.txt` (fan block) | Pi config | Core, UI | Core, UI (`sudo -n install`) | on demand |
| `/home/pi/.apertar-tuning` | `NAME=VALUE` | Core (ProRes) | nobody | every ProRes clip open |
| `$HOME/.cache/apertar-prores/<profile>.json` | libcamera tuning | libcamera | Core | camera open with a log profile |

`~` is `/home/pi`: every unit runs as `User=pi` (Pi, 2026-10-25), and several paths are hard-coded to `/home/pi` anyway.

## 2. `apertar-hardware.conf`

### 2.1 Which file is used

Candidate order, copied into every C++ parser: `$APERTAR_HARDWARE_CONFIG` → `/home/pi/apertar-hardware.conf` → `/boot/firmware/apertar-hardware.conf` → `/boot/apertar-hardware.conf` (`App:4251-4269`; `Apertar-Core/src/hardware/Pcf8574Input.cpp:55-76`; `Apertar-UI/src/DisplayConfigBridge.cpp:20-39`; `Apertar-UI/src/CfeAutomounter.cpp:114-129`).

Exceptions:

| Reader | Uses | Ref |
| --- | --- | --- |
| Core WebUI editor (`GET/POST /api/config`), `run_script` | `$APERTAR_HARDWARE_CONFIG` or `/home/pi/...` only | `App:4271-4276`, `:5292`, `:8663` |
| UI `WifiBridge` (`[network]`) | env or `/home/pi/...` only | `Apertar-UI/src/WifiBridge.cpp:19-35` |
| UI first-run template writer | always `/home/pi/apertar-hardware.conf`, ignores env | `Apertar-UI/src/DisplayConfigBridge.cpp:41-46` |

**Trap: a `/boot/firmware` copy is dead on a running system.** The UI creates `/home/pi/apertar-hardware.conf` from its template at every start when it is missing (`Apertar-UI/src/DisplayConfigBridge.cpp:587`). `/home/pi` comes first in every list, so after the first UI start the `/boot` copy is never read.

Two file-selection rules exist:
- **First existing file wins, even without the section**: Core INA219 (`App:4450-4506`), trigger (`Apertar-Core/src/hardware/TriggerOutput.cpp:250-360`), tally LED (`RecordingIndicatorOutput.cpp:247-399`), IMU, UI display/INA219/gyro, automounter, both Python helpers.
- **Fall through to the next candidate if the section is missing**: PCF8574 (`Pcf8574Input.cpp:385`), GPIO (`GpioInput.cpp:498`), NeoRotary4 (`NeoRotary4Input.cpp:439`), Grove (`GroveAnalogInput.cpp:350`).

### 2.2 When each part is (re)read

| Part | When | Ref |
| --- | --- | --- |
| Core inputs and outputs (PCF, GPIO, NeoRotary4, Grove, trigger, LED) | `ApertarCoreApp::start()` only. **Restart Core after editing** (`sudo systemctl restart apertar-core`) | `App:6881-6893` |
| Core INA219 | once per process (`static const`) | `App:4602` |
| Core `[camera]` (`cinemate-port` `8175273`) | once per process (`static const`, first use). **Restart Core after editing** | `CC` `clearHdrIsoLimits()` |
| Core IMU | every recording, calibration and IMU command | `Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:1040`, `:1176`, `:1297` |
| Core `run_script` | every script action | `Apertar-Core/src/hardware/HardwareScriptRunner.cpp:38-96` |
| Core NVMe watcher (Python) | each NVMe eject | `App:3568` |
| UI `[display]` | UI start | `Apertar-UI/src/DisplayConfigBridge.cpp:575-654` |
| UI `[ina219]` | 5 s after UI start | `Apertar-UI/src/Ina219Bridge.cpp:449`, `:490-530` |
| UI / network helper `[network]` | `WifiBridge` constructor | `Apertar-UI/src/WifiBridge.cpp:129` |
| `apertar-cfe-automounter` | daemon start | `Apertar-UI/src/CfeAutomounter.cpp:131-191` |

### 2.3 Parser differences that bite

| Behaviour | Parsers | Ref |
| --- | --- | --- |
| Inline `# …` / `; …` stripped from the whole line (values cannot contain `#` or `;`) | Core PCF, GPIO, NeoRotary4, Grove; colour profiles | `Pcf8574Input.cpp:338-340`, `NeoRotary4Input.cpp:375-377` |
| Inline comment stripped from the value only after whitespace | Core trigger, LED | `TriggerOutput.cpp:56-66` |
| **Integers not comment-stripped** (`bus=4 # x` is ignored, default kept) | Core INA219, both Python helpers | `App:4406-4425`; `App:3413-3422` |
| `driver=` value not comment-stripped (`driver=bmi160 # x` → mpu6050) | Core IMU | `Mpu6050RecordingSession.cpp:888-893` |
| Section name case-sensitive / exact | `[run_script]` (exact line), UI QSettings groups, Core INA219 (`[ ina219 ]` fails) | `HardwareScriptRunner.cpp:52`, `App:4471` |
| `enabled`/`disabled` accepted as bool words | Core INA219, UI INA219, automounter, Python | `App:4427-4448`; elsewhere only true/yes/on/1, false/no/off/0 |
| Python `configparser` raises on duplicate keys/sections or `%`; only `OSError` caught; output to `/dev/null` | Core NVMe watcher | `App:3444-3447`, `:3594-3595` |

### 2.4 Sections and keys

"Parser" names the binary: **Core** = `apertar-core`, **UI** = `Apertar-UI`, **AM** = `apertar-cfe-automounter` (built from `Apertar-UI/src/CfeAutomounter.cpp`), **NH** = `apertar-network-helper`, **Py** = Python watcher embedded in Core (`App:3380-3602`) and in the UI (`Apertar-UI/src/MediaStatusBridge.cpp:750-831`). Defaults are the parser's coded fallback when the key is absent.

#### `[network]`

| Key | Default | Parser | Ref |
| --- | --- | --- | --- |
| `hotspot_delay_seconds` | 60 (0–86400; invalid → 60 with a warning). Restart `apertar-network` after a change | UI, NH | `Apertar-UI/src/WifiBridge.cpp:19-35` |

#### `[display]` (UI only)

| Key (aliases) | Default | Ref (`Apertar-UI/src/DisplayConfigBridge.cpp`) |
| --- | --- | --- |
| `ui_width` (`uiWidth`, `width`) | 720 (320–3840) | `:598-604` |
| `ui_height` (`uiHeight`, `height`) | 720 (320–3840) | `:605-611` |
| `ui_layout` (`uiLayout`, `layout`, `profile`) | derived from size: square, landscape_compact, landscape_medium, landscape, landscape_large, portrait* | `:612-618` |
| `ui_rotation` (`uiRotation`, `rotation`, `orientation`) | normal (left / right / upside_down / degrees) | `:619-625` |
| `controls_opacity` (`control_opacity`, `controlsOpacity`, `opacity`) | 1.0 (0.15–1.0); only a default for UI.conf `cameraControlsOpacity` | `:626-633`; `Apertar-UI/src/main.cpp:318` |
| `zoom_toggle_factor` | 4.0 (1.0–4.0) | `:634-638` |
| `windowed` (+4 aliases) | false | `:639-645` |
| `hdmi_external_only` (`hdmiExternalOnly`) | false | `:646-649` |
| `controls_mode` | **parsed by nobody** (Core template only, `App:4326`) | — |

The UI logs what it loaded: `Apertar display config: path=… size=WxH layout=…` (`Apertar-UI/src/main.cpp:280`).

#### `[ina219]` (battery monitor)

| Key (aliases) | Default | Parser | Ref |
| --- | --- | --- | --- |
| `enabled` | true | Core, UI | `App:4241`; `Apertar-UI/src/Ina219Bridge.cpp:495-507` |
| `bus` (`channel`, `i2c_bus`) | **4** | Core, UI | `App:4242`; `Apertar-UI/src/Ina219Bridge.cpp:45` |
| `address` (`addr`) | `0x40` | Core, UI | `App:4243`; `Ina219Bridge.cpp:46` |

Core and UI open the chip independently and both rewrite its config/calibration registers (`App:4622-4626`). Core is silent on failure; the UI's settings page says "Check /home/pi/apertar-hardware.conf and INA219 wiring" (`Apertar-UI/qml/SettingsPage.qml:4502`). Which overlay gives `/dev/i2c-4` on the reference rig is **unconfirmed** (`ls /dev/i2c-*; i2cdetect -l`).

#### `[cfexpress_hat]` and `[storage]` (CFexpress hat)

| Key (aliases) | Default | Parser | Ref |
| --- | --- | --- | --- |
| `cfexpress_hat.enabled` | true | AM, Py | `Apertar-UI/src/CfeAutomounter.cpp:106`, `:165`; `App:3393` |
| `cfexpress_hat.bus` (`channel`, `i2c_bus`) | **10** | AM, Py | `CfeAutomounter.cpp:38`, `:167-168`; `App:3391` |
| `cfexpress_hat.address` (`addr`) | `0x34` | AM, Py | `CfeAutomounter.cpp:39`; `App:3392` |
| `storage.mount_path` | `/media/RAW`. Honoured by AM; **ignored by Core's watcher** (Core always sets `APERTAR_MEDIA_ROOT`) and by Core C++ (uses `--media`) | AM, Py | `CfeAutomounter.cpp:172-175`; `App:3457`, `:3594` |
| `storage.pcie_controller` | `1000110000.pcie` | AM, Py | `CfeAutomounter.cpp:176-179`; `App:3395` |
| `storage.buffer` | `frames` (absent = frames); `ram` = the large RAM write queue. Read at the start of each take (a save in the Config pane applies to the next take); the env variable `APERTAR_CDNG_BUFFER` wins; `set_buffer_mode` edits this key | Core (drop-frames) | `BufferBudget.hpp` `parseBufferConf`; `CC` `planQueueBuffer`; validator in `HardwareConfigText.hpp` |
| `storage.buffer_ram_fraction` | `0.6` (0.05 to 0.9): share of `MemAvailable` for the ram queue | Core | same |
| `storage.buffer_ram_floor_mb` | `512` (0 to 1048576): memory kept free | Core | same |
| `storage.buffer_ram_max_fraction` | `0.5` (0.1 to 0.75): ceiling as a share of `MemTotal` | Core | same |
| `storage.buffer_stop_percent` | 0 = never, or 50 to 99; absent = 90 in ram mode, off in frames mode: the take ends by itself (clean stop) when the write buffer reaches this fill | Core | same; `buffer_safety_stop` in the state |

The C++ Core never reads `[cfexpress_hat]` or `storage.mount_path` / `storage.pcie_controller`; it does read the `storage.buffer*` keys (drop-frames branch; a bad value is an error with its line number in the Config pane and Core uses the default). Bus choice per wiring: [the 2026-10-23 hardware note](../sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md) (`bus=1` on an HDMI rig with DPI overlays off).

#### `[camera]` (Core, `cinemate-port` `8175273`, 2026-10-28)

| Key | Default | Ref |
| --- | --- | --- |
| `clear_hdr_iso_max_12bit` | **720**: gain code 57 = 17.1 dB, the top of the sensor's HG/LG combine window with the driver's +12 dB `EXP_GAIN` (`imx585.c:164-165`). 0 = no cap | `CC` `loadClearHdrIsoLimits()` |
| `clear_hdr_iso_max_16bit` | **1585**: gain code 80 = 24 dB, `IMX585_ANA_GAIN_MAX_HDR` (`imx585.c:169`). 0 = no cap | same |

SDR is never capped. Missing section or key = these defaults. Own parser (copy of the per-module pattern): first file found
wins, inline `#`/`;` comments stripped. In the Core template only; the UI first-run template does not have it yet.
Planned in the same section (T33): `max_fps=50`.

#### `[run_script]` (Core)

| Key | Default | Ref (`Apertar-Core/src/hardware/HardwareScriptRunner.cpp`) |
| --- | --- | --- |
| `path` (= slot 1; ignored if `path1` appears) | empty | `:59-69` |
| `path1`–`path5` | empty. Absolute, readable, optionally quoted. Any other `path*` key **throws** | `:60-80` |

Run as `/bin/bash -- <path>`, user pi, own process group, no timeout (`:232-238`). Triggered by actions `run_script`, `run_scriptN`, `script`, `scriptN` (`Apertar-Core/src/hardware/ButtonActionList.hpp:17-33`). Reads only the editable path (§2.1).

#### `[pcf8574]` (alias `[pcf8574_buttons]`, Core)

| Key (aliases) | Default | Ref (`Apertar-Core/src/hardware/Pcf8574Input.{hpp,cpp}`) |
| --- | --- | --- |
| (section present) | enabled | `.cpp:346-351` |
| `enabled` | true if present | `.cpp:364-365` |
| `bus` (`channel`, `i2c_bus`) | **1** | `.hpp:31`, `.cpp:366-368` |
| `address` (`addr`) | `0x20` | `.hpp:32` |
| `poll_ms` (`poll_interval_ms`) | 40 (10–1000) | `.hpp:33` |
| `debounce_ms` | 60 (0–1000) | `.hpp:34` |
| `active_low` | true | `.hpp:35` |
| `pinN` / `pin_N` / `gpioN` / `pN` (N 0–7, optional `_action`) | none; ≤6 comma-separated actions | `.cpp:108-138`, `:380-381` |

No pin mapped → `PCF8574 config in … has no pin actions; input disabled.` (`.cpp:279-283`). `bus`/`address` are also inherited by `[trigger_output]` and `[recording_indicator]` when they target the PCF (`TriggerOutput.cpp:289-298`, `RecordingIndicatorOutput.cpp:293-303`), but only if `[pcf8574]` comes **before** them in the file.

#### `[gpio_buttons]` / `[gpio_encoders]` (Core)

Aliases: `[gpio]`, `[grove_digital]`, `[grove_buttons]`; `[grove_encoders]` (`Apertar-Core/src/hardware/GpioInput.cpp:407-409`).

| Key | Default | Ref (`GpioInput.{hpp,cpp}`) |
| --- | --- | --- |
| `enabled` (one per section) | **false**; presence does not enable | `.cpp:426-430`, `:482-496` |
| `chip` (`gpiochip`, `gpio_chip`) | `auto` (RP1 scored highest) | `.hpp:48`, `.cpp:238-260` |
| `active_low` | true | `.hpp:49` |
| `pull` (`bias`) | up | `.hpp:50` |
| `poll_ms` | 12 (2–1000) | `.hpp:51` |
| `debounce_ms` | 60 | `.hpp:52` |
| Buttons: `dN`, `gpioN`, `pinN`, `bcmN`, `grove_dN` (N = BCM 0–63) | action | `.cpp:209-236` |
| Encoders: `encoderN_{a,b,cw,ccw,press_gpio,press,invert,steps_per_event}` (N 0–7) | steps 4 | `.hpp:34-43`, `.cpp:449-479` |

`chip`, `active_low`, `pull`, `poll_ms`, `debounce_ms` are **shared** between the two sections; the later section wins (`.cpp:431-442`).

#### `[neorotary4]` (aliases `[neo_rotary4]`, `[neo_rotary_4]`, Core)

| Key (aliases) | Default | Ref (`Apertar-Core/src/hardware/NeoRotary4Input.{hpp,cpp}`) |
| --- | --- | --- |
| (section present) | enabled | `.cpp:386-390` |
| `bus` (`channel`, `i2c_bus`) | **1** | `.hpp:39` |
| `address` (`addr`) | `0x49` | `.hpp:40` |
| `poll_ms` | 30 (10–1000) | `.hpp:41` |
| `debounce_ms` | 60 | `.hpp:42` |
| `invert_direction` (`invert`, `reverse_direction`) | false | `.hpp:43` |
| `reset_on_start` | false (seesaw soft reset + 500 ms) | `.hpp:44`, `.cpp:470-479` |
| `max_events_per_poll` | 8 (1–32) | `.hpp:45` |
| `encoderN_{cw,ccw,press}` (N 0–3; also `enc`, `rotary`; field aliases right/left/up/down/plus/minus/push/click) | none | `.cpp:222-257`, `:424-435` |

#### `[grove_analog]` (aliases `[grove_adc]`, `[analog_controls]`, Core)

| Key | Default | Ref (`Apertar-Core/src/hardware/GroveAnalogInput.{hpp,cpp}`) |
| --- | --- | --- |
| (section present) | enabled | `.cpp:278-282` |
| `bus` (**`channel`**, `i2c_bus`) | 1 | `.hpp:55`, `.cpp:297-299` |
| `address` (`addr`) | `0x04` (0x08 on MM32 hats) | `.hpp:56` |
| `poll_ms` | 80 (20–2000) | `.hpp:57` |
| `deadband` | 32 | `.hpp:58` |
| `emit_on_start` (`sync_on_start`) | false | `.hpp:59` |
| `aN` / `channelN` / `chN` / `analogN` (= target), `aN_min`, `_max`, `_step`, `_deadband`, `_invert`, `_mode` (preset) | — | `.cpp:147-182`, `:311-340` |

`channel=` is the **bus** alias while `channel0…7` are ADC channels (`.cpp:297` vs `:147-163`).

#### `[trigger_output]` (aliases `[trigger]`, `[capture_trigger]`, `[hotshoe]`, Core)

| Key (aliases) | Default | Ref (`Apertar-Core/src/hardware/TriggerOutput.{hpp,cpp}`) |
| --- | --- | --- |
| `enabled` | false | `.hpp:42-43` |
| `target` (`type`, `backend`, `output`) | gpio (or pcf / pcf8574 / i2c) | `.cpp:305-310` |
| `gpiochip` (`chip`, `gpio_chip`) | auto; **empty value stored as ""** | `.cpp:311-312` |
| `line` (`gpio`, `gpio_line`) | 17 | `.hpp:46` |
| `pin` | → line or pcf_pin by target | `.cpp:316-317`, `:346-351` |
| `open_drain` | **false** | `.hpp:47` |
| `bus` (`pcf_bus`), `address` (`pcf_address`) | 1 / `0x20`, or `[pcf8574]` values | `.hpp:48-49` |
| `pcf_pin` | 0 | `.hpp:50` |
| `active_high` / `active_low` | active low | `.hpp:51` |
| `pulse_ms` (`duration_ms`) | 80 (1–5000) | `.hpp:52`, `.cpp:333-336` |
| `events` | recording_start, still, timelapse_frame (also timelapse_start, all) | `.cpp:121-176` |

#### `[recording_indicator]` (aliases `[rec_indicator]`, `[record_led]`, `[recording_led]`, `[tally_led]`, Core)

Same keys as `[trigger_output]` minus `pulse_ms` and `events`. Defaults: disabled, gpio, `line` **−1**, `open_drain` false, PCF 1 / `0x20`, `pcf_pin` **−1** (`Apertar-Core/src/hardware/RecordingIndicatorOutput.hpp:36-49`). If the section is not enabled, the first `pinN=recindicatorled` in `[pcf8574]` or `dN=recindicatorled` in a `[gpio*]` section enables the LED, **even when that section has `enabled=false`** (`RecordingIndicatorOutput.cpp:293-334`, `:382-391`). The shorthand copies the parser state at the moment its line is read, so it **inherits `active_high`/`open_drain`/`chip` from a `[recording_indicator]` section earlier in the file, even a disabled one** (default `active_high=false`); it has no polarity key of its own (`:320-326`, confirmed by code reading, fork `main` 2026-10-25).

#### `[imu]` and driver sections (Core and UI)

`[imu]` holds only four keys in both parsers (`Apertar-Core/src/hardware/Mpu6050RecordingSession.cpp:939-955`; `Apertar-UI/src/GyroConfigBridge.cpp:979-998`):

| Key (aliases) | Default | Writers |
| --- | --- | --- |
| `enabled` | **true** (`Mpu6050RecordingSession.hpp:96`) | — |
| `driver` | mpu6050 (bmi160, bmi270, icm42688p; anything else → mpu6050) | `set_imu_driver` (`.cpp:1295-1301`), UI (`GyroConfigBridge.cpp:684`) |
| `sync_mode` | free_run | — |
| `sync_offset_ms` (`offset_ms`, `gyro_sync_offset_ms`) | 0 (−2000…2000); beats the driver section's value | `set/adjust/reset_imu_sync_offset`, UI (`:885`) |

Everything else lives in the section named after the driver (`[mpu6050]`, `[bmi160]`, `[bmi270]`, `[icm42688p]`) or in `[gyro]` (`Mpu6050RecordingSession.cpp:171-184`):

| Key (aliases) | Default (Core, `.hpp:95-121`) |
| --- | --- |
| `enabled` | overwrites the `[imu]` flag (`.cpp:946` vs `:957`) |
| `bus` (`bus_number`) | 1 (0–32). Auto-probe tries every `/dev/i2c-0..32` at 0x68/0x69 when this fails (`.cpp:1543-1600`) |
| `address` (`addr`) | `0x68` |
| `sample_rate_hz` | 500 (25–1000) |
| `gyro_range_dps` | 1000 (250–2000) |
| `accel_range_g` | 8 (2–16) |
| `dlpf_hz`, `use_fifo`, `fifo_batch_samples` | 98, true, 24 |
| `orientation` | XYZ (Gyroflow notation) |
| `auto_calibrate_seconds`, `gyro_bias_{x,y,z}` | 0 |
| `level_reference_set`, `level_reference_orientation`, `level_accel_{x,y,z}` | false, —, 0 |
| `frame_readout_time_ms`, `frame_readout_direction` | 0, 0 |

Recording gyro on/off is UI.conf `recordGyroEnabled`, not this file.

## 3. Template copies and where they disagree

| ID | Location | Written to disk |
| --- | --- | --- |
| T-Core | `App:4291-4404` (`defaultHardwareConfigTemplate`) | Never automatically. Shown by `GET /api/config` when the file is missing (`App:5297`); saved only if the user presses Save in the WebUI |
| T-Display | `Apertar-UI/src/DisplayConfigBridge.cpp:41-326` | **At every UI start if `/home/pi/apertar-hardware.conf` is missing** (`:587`). Runs first: `DisplayConfigBridge` is built at `Apertar-UI/src/main.cpp:278` |
| T-Ina219 | `Apertar-UI/src/Ina219Bridge.cpp:69-342` | Same condition, 5 s later (`:449`, `:497`); normally a no-op because T-Display already wrote the file |
| header only | `Mpu6050RecordingSession.cpp:623-626`, `Apertar-UI/src/GyroConfigBridge.cpp:1587-1590` | IMU writes into an empty file |

So on a fresh image **T-Display is the file you get**. T-Core is only what the WebUI shows before anything exists.

T-Display and T-Ina219 agree on every shared key. T-Ina219 lacks `[network]`, `[run_script]` and `display.zoom_toggle_factor`. Keys that differ (checked with a key-level diff of all three):

| Section.key | T-Core | T-Display / T-Ina219 | Parser default | Effect |
| --- | --- | --- | --- | --- |
| `pcf8574.bus` | **10** (`App:4363`) | **1** (`DisplayConfigBridge.cpp:87`, `Ina219Bridge.cpp:106`) | **1** (`Pcf8574Input.hpp:31`) | WebUI-saved file puts buttons on bus 10 |
| `imu.enabled` | **false** (`App:4344`) | **true** (`DisplayConfigBridge.cpp:201`) | true | |
| `imu.bus`, `address`, `sample_rate_hz`, `gyro_range_dps`, `accel_range_g`, `orientation` | 10, 0x68, 500, **2000**, 8, XYZ (`App:4346-4351`) | not in `[imu]`; `[mpu6050]` bus=1, 0x68, 500, **1000**, 8, XYZ (`DisplayConfigBridge.cpp:209-218`) | 1, 0x68, 500, 1000, 8, XYZ | **T-Core values are dead**: `[imu]` reads only 4 keys |
| `imu.sync_mode` | absent | free_run | free_run | — |
| driver sections `[mpu6050]`, `[bmi160]`, `[bmi270]`, `[icm42688p]` | absent | present; bmi*/icm `enabled=false` | — | Selecting bmi160/bmi270/icm42688p leaves the IMU disabled (driver-section `enabled=false` overrides `[imu]`) |
| GPIO section | `[gpio]` `enabled=false` | `[gpio_buttons]` with `d5=capture`, `d6=eject`; `[gpio_encoders]` on GPIO 5/6 (`poll_ms=3`, `debounce_ms=40`) | disabled | Encoder poll/debounce override the buttons' values (shared keys) |
| `[neorotary4]`, `[grove_analog]` | absent | present, `enabled=false`, bus 1 | bus 1 | |
| `[network]` | absent | `hotspot_delay_seconds=60` (Display only) | 60 | |
| `display.rotation` / `ui_rotation` | `rotation=0` | `ui_rotation=normal` | normal | Same (alias) |
| `display.controls_mode` | `Light` (`App:4326`) | absent | — | Dead key |
| `trigger_output.open_drain` | true | true | **false** (`TriggerOutput.hpp:47`) | Delete the key and you get push-pull |
| `recording_indicator.line` / `pcf_pin` | 17 / 7 | 17 / 7 | **−1 / −1** | Template enables a pin the code would not |
| `recording_indicator` comment `# bus=` | 10 | 1 | 1 | T-Core is self-inconsistent (its trigger comment says 1) |
| `ina219.*` | true / 4 / 0x40 | same | same | Consistent |
| `cfexpress_hat.*`, `storage.*` | true / 10 / 0x34, /media/RAW, 1000110000.pcie | same | same | Consistent |

### Verdict on the earlier note

The 2026-10-23 note (§6.6 of [sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md](../sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md)) says "`[ina219] bus=4` and `[pcf8574] bus=10` in the UI template vs `bus=1` in the Core template". **Refuted as worded; the PCF half is reversed.**

| Claim | Reality |
| --- | --- |
| UI template `[ina219] bus=4` | True, but Core's template and both parsers also say 4. No disagreement |
| UI template `[pcf8574] bus=10` | **False.** Both UI templates say `bus=1` |
| Core template `bus=1` | **False.** Core's template says `[pcf8574] bus=10` and `[imu] bus=10`; Core's *parser defaults* are bus 1 |

The real split: **Core's WebUI template** uses bus 10 for PCF8574 and IMU; **the UI templates and every parser default** use bus 1 (and 4 for the INA219, 10 for the hat).

## 4. `apertar-color-profiles.conf` (Core)

Path `$APERTAR_COLOR_PROFILE_CONFIG`, else `/home/pi/apertar-color-profiles.conf` (`Apertar-Core/src/color/ColorProfileConfig.cpp:232-237`). No template or writer exists. Reloaded when existence or mtime changes (`:377-405`). A built-in `imx585-built-in` profile is appended last (`:239-271`).

| Key (aliases) | Meaning | Ref |
| --- | --- | --- |
| `[name]` | One profile; name lower-cased | `:312-375` |
| `match` (`matches`, `sensor`) | Sensor-model substrings; `*`/`default` = wildcard. Default = the section name | `:352-355` |
| `illuminant1`, `illuminant2` | EXIF LightSource, default 21 (D65) | `:356-359` |
| `ccm1_kelvin`, `ccm2_kelvin` | CCM blend points (0 → 2850 / 5600) | `:360-363` |
| `color_matrix1/2` (`colour_matrix*`, `dng_color_matrix*`), `forward_matrix1/2` (`ff_matrix*`) | 9 floats each | `:288-299` |
| `ccm` (wins), `ccm1`, `ccm2` | 9 floats; ccm1/ccm2 blended by WB kelvin | `:300-309` |

Each line is cut at the first `#` or `;` (`:325-327`), so matrices must be comma- or space-separated. Without a match, the active tuning's CCMs are used. The tuning read for calibration is `$APERTAR_SENSOR_TUNING_FILE`, else `$LIBCAMERA_RPI_TUNING_FILE` (`:613-628`).

## 5. Camera settings: `camera_settings.conf` (Core)

Where `CaptureSettings` is saved.

| Item | Value | Ref |
| --- | --- | --- |
| Path | `$XDG_CONFIG_HOME/apertar-core/camera_settings.conf`, else `$HOME/.config/apertar-core/camera_settings.conf`, else `/tmp/apertar-core-camera_settings.conf` | `CC:342-353` |
| Format | `key=value`, no sections. Active values plus `profile.<cdng\|mlv\|h264\|prores\|still>.<key>`; lossy DNG shares the `cdng` profile | `CC:605-640`, `:742-778` |
| Load | `loadPersistedCaptureSettings` in the `CameraController` constructor | `CC:616-740`, `:7598` |
| Write | `persistSettingsLocked` → `CaptureSettingsPersister` thread, 25 ms debounce, `settingsFile::atomicWrite` (tmp + fsync + rename + dir fsync) | `CC:8725-8732`, `:793-889`; `Apertar-Core/src/util/SettingsFile.hpp:36-56` |
| Keys | `resolution_width/height`, `fps` (24), `iso` (800), `iso_auto`, `shutter_us` (20833), `shutter_auto`, `exposure_compensation`, `exposure_metering`, `photo_mode_enabled`, `long_exposure_enabled`, `bracketing_enabled`, `bracketing_ev` (1.0), `wb_kelvin` (5600), `wb_auto`, `recording_format` (cdng), `cdng_compression`, `lossy_dng_ratio`, `prores_profile`, `prores_color_profile`, `cdng_preview_color_profile`, `raw_bit_depth` (12), `h264_width/height`, `tuning_file`, `timecode_mode`, `af_mode` (continuous), `af_range`, `af_speed`, `af_window_{x,y,w,h}` (0.25/0.25/0.5/0.5); legacy `wb_locked` read only | `CC:742-778`; defaults `include/apertar/core/Types.hpp:124-162` |

To reset camera settings: stop Core, move the file away, start Core.

The UI keeps its own placeholder copy in `UI.conf [camera]` (`Apertar-UI/src/ApertarControlBridge.cpp:884-1011`; comment at `:886`: Core owns restoration). Core ignores it.

## 6. UI settings: `~/.config/CinePi/UI.conf`

| Item | Value | Ref |
| --- | --- | --- |
| UI side | `QSettings("CinePi","UI")` in `SettingsBridge`, `ApertarControlBridge`, `WifiBridge` | `Apertar-UI/src/SettingsBridge.cpp:287`, `ApertarControlBridge.cpp:118`, `WifiBridge.cpp:127` |
| Core path | `$XDG_CONFIG_HOME/CinePi/UI.conf`, else `$HOME/.config/CinePi/UI.conf`, else `/tmp/CinePi-UI.conf` | `App:341-348` |
| Core read | `[General]` only, own line parser | `App:1641-1813` |
| Core write | `updateSharedUiGeneralSettings`: QLockFile-compatible `UI.conf.lock`, atomic rewrite of `[General]` | `App:1850-1935`; `Apertar-Core/src/util/SettingsFile.hpp:58-118` |
| UI reload | `QFileSystemWatcher` plus a 10 s poll | `Apertar-UI/src/SettingsBridge.cpp:411-431` |

`[General]` keys shared with Core (defaults from `App:1580-1639`):

| Group | Keys (default) |
| --- | --- |
| Monitoring | `focusPeakingEnabled` (false), `focusPeakingThreshold` (0.04), `focusPeakingColor` (Red), `zebraEnabled` (false), `zebraThreshold` (0.70), `falseColorEnabled`, `falseColorMode` (0), `lutPreviewEnabled`, `lutPreviewFile`, `guidesEnabled` (true), `guidesType` (Thirds), `guidesThickness` (1), `centerMarkerEnabled` (true), `centerMarkerType` (Circle/Dot), `grayscaleEnabled`, `smpteEnabled`, `anamorphicDesqueezeEnabled`, `anamorphicRatio` (1.33x), `dateTimeOverlayEnabled` |
| External monitor | `externalMonitorEnabled` (false), `externalMonitorMode` (Clean Feed), `externalMonitorInfoOverlay` (On), `externalMonitorOrientation` (Landscape) |
| Stills | `photoModeEnabled`, `photoLongExposureEnabled`, `photoBracketingEnabled` (false), `photoBracketingEv` (1.0), `photoTimer` (Off), `photoBurst` (Single), `photoFormat` (DNG), `photoTimelapse` (Off); Core-only `lastPhotoTimelapse` |
| UI | `uiOrientation` (Landscape), `cameraControlsOpacity` (1.0), `cameraControlsMode` (Light), `timecodeMode` (Free Run; Core accepts only exact `Rec Run`, `App:1723`) |
| Audio | `recordAudioEnabled`, `soundRecorderEnabled`, `recordGyroEnabled` (false), `liveAudioMonitoringEnabled` (true), `audioMeterEnabled`, `audioInputDevice`, `audioOutputDevice`, `audioSampleFormat` (auto), `audioSampleRate` (0), `audioChannels` (auto), `inputVolume` (60), `headphoneVolume` (55) |
| Power | `batteryType` (V-Mount), `batteryCapacity` (150Wh), `customBatteryWh` (150), `customBatteryFullVoltage` (16.8), `customBatteryEmptyVoltage` (13.2), `sleepMode` (Off), `standbyTimeoutSeconds` (0), `standbyUsbPowerOff` (false) |
| Layout | `favoritesOrder` |

UI-only keys: `horizontalLevelEnabled`, `horizontalLevelColor`, `monitoringOrder`, `recordOrder`, `audioOrder`, `powerOrder`, `systemOrder`, `wifiOrder`, `infoOrder`, `sidebarOrder` (Core copies them into presets only); `hotspotSsid` (Apertar) and `hotspotPassword` (apertarcam), **stored in plain text** (`Apertar-UI/src/WifiBridge.cpp:130-136`, `:252`, `:262`).

**Probable bug**: QSettings quotes values containing `,` and reads unquoted `a,b` as a list; Core reads and writes raw text (`App:1666-1671`, `:1920-1927`). Audio IDs like `hw:1,0` can then be mangled in one direction. **Unconfirmed**: set an audio device in the WebUI, then `grep audioInputDevice ~/.config/CinePi/UI.conf` and check what the UI shows.

## 7. Other files

| File | Role | Ref |
| --- | --- | --- |
| Presets `*.apertar-preset.json` | UI: `~/.local/share/Apertar-UI/presets`, legacy `~/.config/CinePi/UI/presets`. Core: first existing of `$XDG_DATA_HOME/{Apertar-UI,ApertarUI}/presets`, `~/.local/share/{Apertar-UI,ApertarUI}/presets`, `~/.config/CinePi/UI/presets` | `Apertar-UI/src/SettingsBridge.cpp:1937-1958`; `App:5216-5262` |
| `~/.config/CinePi/DisplayCalibration.conf` | `[builtin]`/`[hdmi]`: `enabled`, `red/green/blue`, `gamma`, `black`, `white` | `Apertar-UI/src/DisplayCalibration.cpp:49`, `:115-154` |
| `/boot/firmware/config.txt` | `# BEGIN/END APERTAR FAN MODE` block (Silent / Full Blast; Auto removes it) | `App:3042-3178`; `Apertar-UI/src/SystemActionBridge.cpp:23-92` |
| Tuning files | Default `/home/pi/Tuning-Files/defaults-pisp` (Pi 5), then `/home/pi/Tuning-Files/defaults`, `/usr/{local/,}share/libcamera/ipa/rpi/pisp` | `Apertar-Core/src/camera/DefaultTuningSelection.hpp:56-78` |
| LUTs (`.cube`) | `/home/pi/LUTs`, `$APERTAR_MEDIA_ROOT/LUTs`, `/media/RAW/LUTs`, `/media/*/LUTs` | `Apertar-UI/src/SettingsBridge.cpp:140-162`; `App:5571-5600` |
| `/home/pi/.apertar-tuning` | ProRes bench overrides; the environment wins | `Apertar-Core/src/prores/ProresEncoder.cpp:770-800` |

Runtime markers (`/run/apertar-ui/{core-start-ready,main-ui-ready}`, `/run/apertar-cfe/ready`, `/run/apertar-standby-*`, `/run/apertar-network/*`) are covered in [core.md](core.md#24-the-startup-gate).

## 8. Environment variables

How the services set them (Pi, 2026-10-25): `apertar-core.service` runs `/home/pi/start-apertar-core.sh` and sets no `Environment=` that we know of; `apertar-ui-direct.service` sets `APERTAR_CORE_START_READY_FILE=/run/apertar-ui/core-start-ready` and `QT_QPA_EGLFS_HIDECURSOR=1`.

### 8.1 Core

| Variable | Effect | Ref |
| --- | --- | --- |
| `APERTAR_CORE_BIN` | Binary (default `/home/pi/ApertarCore-build/apertar-core`) | `Apertar-Core/scripts/start-apertar-core.sh:4` |
| `APERTAR_MEDIA_ROOT` | `--media` (default `/media/RAW`); also passed to the NVMe watcher; UI uses it for LUT/tuning search | `start-apertar-core.sh:5`; `App:3394`, `:3594`; `Apertar-UI/src/SettingsBridge.cpp:145` |
| `APERTAR_SOCKET_PATH` | `--socket` (default `/tmp/apertar-core.sock`) | `start-apertar-core.sh:6` |
| `APERTAR_TUNING_FILE` | Exported as `LIBCAMERA_RPI_TUNING_FILE`; **overwritten by Core at camera open** | `start-apertar-core.sh:16-18`; `CC:1111-1121` |
| `LIBCAMERA_RPI_TUNING_FILE` | Read once as the custom tuning when none is saved; then always set by Core | `CC:7602-7605`, `:1111-1121`, `:5360` |
| `APERTAR_SENSOR_TUNING_FILE` | Set by Core; colour calibration source | `CC:1114`; `ColorProfileConfig.cpp:616` |
| `APERTAR_DEFAULT_TUNING_DIR` | Replaces `/home/pi/Tuning-Files/defaults-*` | `DefaultTuningSelection.hpp:58` |
| `APERTAR_HARDWARE_CONFIG` | First config candidate; the only path for the WebUI editor and `run_script` | `App:4254`, `:4273` |
| `APERTAR_COLOR_PROFILE_CONFIG` | Colour profile file | `ColorProfileConfig.cpp:234` |
| `HOME`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME` | UI.conf, camera_settings, presets, ProRes cache | `App:343-346`, `:5219`; `CC:344-350` |
| `APERTAR_H264_LIBAV_PLUGIN`, `APERTAR_PRORES_PLUGIN` | Plugin paths | [build.md](build.md#how-core-finds-its-plugins-at-runtime) |
| `APERTAR_H264_*` | `ENCODER`, `PRESET`, `TUNE`, `CRF`, `QP`, `BITRATE`, `MAXRATE`, `BUFSIZE`, `X264_PARAMS`, `BACKEND` (`pipe`), `THREADS`, `PIPE_BYTES`, `QUEUE_FRAMES`, `SIZE`, `CAMERA_BUFFERS`, `KEEP_RAW_STREAM`, `SINGLE_STREAM` | `CC:1127`, `:2779`, `:2843-2848`, `:3981`, `:4333-4467` |
| `APERTAR_PRORES_*` | `CAMERA_BUFFERS`, `CACHED_DMABUF`, `THREADS`, `CSC_THREADS`, `ISP_FORMAT`, `ODIRECT`, `QP_PRED`, `TRANSFER`, `WRITEBACK`, `WRITER_THREAD`, `WRITER_QUEUE`, `WRITER_QUEUE_MB`, `WRITER_SLOW_MS` | `CC:1133`, `:6387`; `Apertar-Core/src/prores/ProresEncoder.cpp:827-1375`; `ProresRecorder.cpp:61` |
| `APERTAR_CDNG_*` | `QUEUE_FRAMES`, `WORKERS`, `WORKER_NICE`, `TILE_ROWS`, `PROFILE_DETAIL` | `CC:3330-3359`; `Apertar-Core/src/cdng/CdngEncoder.cpp:55`, `:72` |
| `APERTAR_CDNG_BUFFER` | Drop-frames: `frames` (default, the original 12-frame queue) or `ram` (byte-budget queue); overrides `[storage] buffer` | `CC` `planQueueBuffer` |
| `APERTAR_CDNG_QUEUE_RAM_FRACTION`, `_FLOOR_MB`, `_MAX_FRACTION` | Drop-frames: the ram budget (0.6, 512, 0.5); override the `[storage] buffer_ram_*` keys; ram refuses itself when the budget is smaller than the frames-mode queue | `BufferBudget.hpp` |
| `APERTAR_CDNG_BUFFER_STOP_PERCENT` | Drop-frames: safety-stop limit (0 or 50 to 99); overrides `[storage] buffer_stop_percent` | `BufferBudget.hpp` |
| `APERTAR_MEDIA_TRIM` | Drop-frames: `0` turns Core's automatic trim of the recording drive off (default on; needs `/usr/local/libexec/apertar-media-trim` and its sudoers rule) | `App` `trimMedia`, `runMediaTrim` |
| `APERTAR_LOSSYDNG_*` | `WORKERS`, `WRITER_BYTES`, `ASYNCWRITE` (legacy `QRAW_LOSSYDNG_ASYNCWRITE`) | `CC:3345`; `Apertar-Core/src/lossydng/LossyDngEncoder.cpp:100`, `:325-327` |
| `APERTAR_RAW_CACHED_DMABUF` | Cached DMA heap for PiSP-compressed RAW (default on) | `CC:6321` |
| `APERTAR_MLV_ENABLE_NEON_PACKER`, `APERTAR_MLV_HAS_NEON` | MLV packer | `Apertar-Core/src/mlv/MlvEncoder.cpp:23-25` |
| `APERTAR_MEDIA_SYNC_MS` | Fork `cinemate-port`: sync-thread interval, default 1000, `0` = off (fsync of files + clip folder) | `CC` `startAtFolder`/`syncLoop` |
| `APERTAR_DNG_WRITEBACK` | Fork: start each DNG's writeback after writing it, default on | `CC` `startWritebackPerFrame` |
| `APERTAR_WRITE_STALL_MS` | Fork: no frame written for this long with a full queue = medium gone, default 5000 | `CC` `writeStallLimitMs` |
| `APERTAR_DEAD_MEDIUM_STOP_MS` | Fork: how long a dead-medium stop waits for writers, default 2000 | `CC` `DngRecordingQueue::stop` |
| `APERTAR_MEDIA_TUNE` | Fork: `1` runs `/usr/local/libexec/apertar-media-tune` on mount (off by default; helper not installed) | `App` `applyMediaTuning` |
| `APERTAR_MEDIA_REQUIRE_MOUNT` | Fork: `0` disables the record gate (development machine) | `App` `mediaGateError` |
| `APERTAR_AUDIO_BUFFER_MS` | Fork: ALSA capture ring, default 100 (100-4000) | `AudioRecordingSession.cpp` `recordCaptureBufferUs` |
| `APERTAR_PHASE_LOCK_LOG`, `_KP`, `_KI`, `_DEADBAND_US`, `_CLAMP_US` | Fork: phase-lock trace and gains (lock itself off by default) | `CC` `stepFramePhaseLock` |
| `APERTAR_SENSOR_PROBE` | `0` skips the startup sensor-mode probe | `CC` `probeSensorModesOnce` |
| `LIBCAMERA_LOG_LEVELS` | On the Pi: `IPARPI:ERROR` via drop-in `apertar-core.service.d/libcamera-log.conf` (the IPA warned every frame in Clear HDR and flooded the journal) | `working/diagnose.md` |

### 8.2 UI and scripts

| Variable | Effect | Ref |
| --- | --- | --- |
| `APERTAR_CONTROL_SOCKET` | Core socket for control, audio and media bridges. **The preview client ignores it** (hard-coded `/tmp/apertar-core.sock`) | `Apertar-UI/src/ApertarControlBridge.cpp:1032`, `:1567`; `ApertarPreviewSocketClient.hpp:30` |
| `APERTAR_CORE_START_READY_FILE` | Core start gate marker | `Apertar-UI/src/main.cpp:406`; `run_pi_direct.sh:172` |
| `APERTAR_UI_READY_FILE`, `APERTAR_HEADLESS_READY_FILE` | First-frame / headless markers (Plymouth, network gate) | `Apertar-UI/src/main.cpp:463`; `run_pi_direct.sh:79-80` |
| `APERTAR_MONITOR_ONLY`, `APERTAR_MONITOR_RUNTIME_SOCKET`, `APERTAR_MONITOR_HOTPLUG_POLL_SECONDS` | HDMI monitor process | `Apertar-UI/src/main.cpp:275`; `run_pi_direct.sh:178`, `:219`, `:273` |
| `APERTAR_DRM_SYSFS`, `APERTAR_UI_DRM_DEVICE`, `APERTAR_MONITOR_DRM_DEVICE`, `APERTAR_QT_USE_LIBINPUT` | Display selection | `run_pi_direct.sh:78`, `:188-211`; `wait_for_ui_core_start.sh:23` |
| `APERTAR_RUNTIME_ROOT`, `APERTAR_NVME_RUNTIME_ROOT`, `APERTAR_USE_RUNTIME_MIRROR`, `APERTAR_USE_NVME_RUNTIME`, `APERTAR_MESA_RUNTIME_ROOT`, `APERTAR_RUNTIME_LIB_DIR`, `APERTAR_UI_BIN`, `APERTAR_UI_ARGS`, `APERTAR_LIB_SOURCE` | Runtime mirror and Mesa ([build.md](build.md#the-runtime-mirror-sync_pi_runtimesh)) | `run_pi_direct.sh:13-54`; `sync_pi_runtime.sh:7-10` |
| `APERTAR_NETWORK_RUNTIME`, `APERTAR_NETWORK_HELPER` | Network helper runtime dir (default `/run/apertar-network`), helper mode | `Apertar-UI/src/NetworkHelper.cpp:13-14`; `WifiBridge.cpp:155` |
| `APERTAR_BACKLIGHT_DIR`, `APERTAR_PANEL_LED_PATH`, `APERTAR_STANDBY_PANEL_POWER` | Standby backlight / panel | `Apertar-UI/src/SleepManager.cpp:31`, `:102`; `DisplayStandbyController.cpp:18` |
| `APERTAR_VIDEO_PLAYBACK_PLUGIN` | Playback `.so` | `Apertar-UI/src/VideoPlayback.cpp:24` |
| `APERTAR_PREVIEW_FORCE_CPU`, `_PLANAR`, `_EGL` | Preview renderer fallbacks | `Apertar-UI/src/PreviewWindowRenderer.cpp:296-301` |
| `APERTAR_QML_AOT_ENABLED` | Startup log only | `Apertar-UI/src/main.cpp:247` |
| `APERTAR_PLYMOUTH_HANDOFF_TIMEOUT_SECONDS`, `APERTAR_PLYMOUTH_BIN` | Plymouth handoff (20 s) | `Apertar-UI/finish_plymouth_handoff.sh:6-7` |
| `APERTAR_LOW_POWER_TEST`, `APERTAR_USB_POWER_TEST` | Standby helper test modes | `Apertar-UI/src/StandbyLowPower.cpp:148`; `StandbyUsbPower.cpp:241` |

## 9. Config bugs and traps

| # | Issue | Ref |
| --- | --- | --- |
| 1 | `/boot` config copies are shadowed by the UI's first-run template | §2.1 |
| 2 | Template defaults disagree (PCF bus 10 vs 1, IMU enabled, gyro range, LED pins, open drain) | §3 |
| 3 | T-Core's `[imu] bus/address/…` keys are parsed by nobody | §3; `Mpu6050RecordingSession.cpp:939-955` |
| 4 | Choosing a non-MPU IMU driver leaves it disabled with the UI template | `Mpu6050RecordingSession.cpp:946`, `:957`; `DisplayConfigBridge.cpp:233-235` |
| 5 | INA219 and Python bus integers are not comment-stripped | §2.3 |
| 6 | `[pcf8574]` must precede `[trigger_output]` / `[recording_indicator]` for bus inheritance; a later `[pcf8574]` overrides their explicit bus | `TriggerOutput.cpp:289-298` |
| 7 | `trigger_output` and `recording_indicator` both on GPIO17 in the templates | `App:4381`, `:4395` |
| 8 | `recindicatorled` in a disabled section still drives the LED | `RecordingIndicatorOutput.cpp:293-334` |
| 9 | Four writers of `apertar-hardware.conf` with no shared lock; WebUI and IMU both use `<path>.tmp`; WebUI save has no fsync | `App:5356-5385`; `Mpu6050RecordingSession.cpp:687-710`, `:816-839` |
| 10 | No reload: Core must restart after `POST /api/config` | `App:6881-6893` |
| 11 | `[storage] mount_path` honoured only by the automounter | §2.4 |
| 12 | Colour-profile matrices cannot use `;` | §4 |
| 13 | Hotspot password in plain text in UI.conf | §6 |

## Unconfirmed

| Claim | Command that settles it |
| --- | --- |
| The live `~/apertar-hardware.conf` was created by T-Display (has `[network]` and `[gpio_buttons]`) | `ssh pi@apertar.local 'grep -n "^\[" ~/apertar-hardware.conf'` |
| No `/boot/firmware/apertar-hardware.conf` that someone expects to be used | `ls -l /boot/firmware/apertar-hardware.conf /boot/apertar-hardware.conf` |
| Core and UI share one `UI.conf` (Core's HOME is `/home/pi`) | `sudo tr '\0' '\n' < /proc/$(pidof apertar-core)/environ \| grep -E '^(HOME\|XDG)'` |
| No `Environment=` in `apertar-core.service` beyond what is listed | `systemctl cat apertar-core` |
| Which overlay creates `/dev/i2c-4` for `[ina219]` | `i2cdetect -l; ls /dev/i2c-*` |
| QSettings comma quoting breaks audio device IDs between UI and Core | see §6 |
