# R2: Apertar Core's hardware inputs, outputs and `apertar-hardware.conf`, read as the target of the port

Reader report for the controls project ("port the GPIO dropdown and method assigning from Cinemate, Apertar style, with a system-controlled config file, the I2C hardware Apertar uses, and the I2C channel settings Patrik's NeoRotary fix needed; dropdown/drag-and-drop for most users, manual editing for advanced users").

Trees read (read only, nothing edited):

- Apertar Core at `eb9cc39` (`.../scratchpad/controls/core-tip`).
- Apertar touch UI repo at `d8098d0` (`.../scratchpad/controls/ui-tip`), only where it reads or writes the same file.
- KB at `dbcbfca` for Patrik's fix (`sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md`).

Citation key. Core paths are relative to the Core tree and pinned `@eb9cc39`; `App` = `src/ApertarCoreApp.cpp`, `Web` = `src/web/WebControlPage.cpp`, `HW/` = `src/hardware/`. UI paths start with `UI/` and are pinned `@d8098d0`. So `App:4333` means `src/ApertarCoreApp.cpp:4333@eb9cc39`. Labels: **CONFIRMED** = I opened the cited lines; **PROBABLE** = derived from cited lines (the derivation is stated); **UNCONFIRMED** = not checked, or needs the Pi.

---

## 0. The short version

1. **One INI-style file, many hand-written parsers.** `/home/pi/apertar-hardware.conf` (or `$APERTAR_HARDWARE_CONFIG`, then `/boot/firmware/…`, then `/boot/…`). Core has 9 separate readers (INA219, CFE hat, embedded Python reinsert helper, script runner, IMU, PCF8574, GPIO, NeoRotary4, Grove analog, trigger, LED) and the UI repo 6 more; each has its own copy of trim/bool/int parsing, and they disagree on inline comments, bool spellings and which candidate file wins. CONFIRMED (§1.1-§1.3).
2. **Read once.** All buttons, encoders, analog inputs, the trigger and the tally LED read the file once in `ApertarCoreApp::start()` (`App:7026-7043`); INA219 is a function-local `static const` (`App:4695`); the CFE hat is read once when the media watcher thread starts (`App:9310`). Only the script runner and the IMU re-read on use. There is no reload command, no SIGHUP handler and no file watcher. CONFIRMED (§1.3, §5).
3. **The WebUI's "Config" tab is a raw textarea.** `GET/POST /api/config` reads and writes the whole file, keeps one `.bak`, writes via `.tmp` + rename, and validates only "not empty, ≤ 256 KiB, no NUL". A save restarts or reloads nothing; the page tells the user to restart Core or the UI. There is no other hardware-mapping UI anywhere (WebUI or touch UI). CONFIRMED (§4).
4. **Three templates disagree.** Core's `defaultHardwareConfigTemplate()` (`App:4333-4446`, shown by `GET /api/config` when no file exists) and two UI copies (`UI/src/DisplayConfigBridge.cpp:41-326`, `UI/src/Ina219Bridge.cpp:69-…`, which *create* the file when missing). Core's lacks `[neorotary4]`, `[gpio_encoders]`, `[grove_analog]`, `[network]` and the IMU driver sections; its `[pcf8574] bus=10` vs the UI's `bus=1`; its `[imu] bus/address/sample_rate_hz/gyro_range_dps/…` keys are **ignored** by the IMU parser. CONFIRMED (§1.5). The KB source's §6.6 has the PCF8574 bus defaults swapped (§1.5).
5. **Inputs only know "pressed".** Every button source (GPIO, PCF8574, NeoRotary4 push, GPIO encoder push) fires one action on the debounced press edge. No hold, release, double or triple click, no chords. Rotation fires per detent/step. The only multi-press gesture is the Pi 5 power button's double press for standby, which is not configurable. CONFIRMED (§2).
6. **Action vocabulary** = 45 canonical names plus parameterised shortcuts (`iso200`, `fps24`, `wb5600`, `resolution4056x2280`, `ev-1`, `shutter180`, `shutter1/48`, `shutter2s`, `run_script3`), up to six per mapping (`P2=iso200,fps24,wb5600`). Every action becomes one or more ordinary socket commands through `handleCommand`, or a `hardware_action` event for the touch UI. Full table in §3. CONFIRMED.
7. **Driver state is invisible.** `enabled()`, `configPath()` and `lastError()` exist on every input module but nothing in Core reads them; a missing `/dev/i2c-1` shows up only as a journal line, retried every second. CONFIRMED (§2.13).
8. **One of each I2C input device.** One PCF8574, one NeoRotary4, one Grove ADC; the PCF8574 can be shared by buttons, trigger and LED, but each keeps its own shadow byte (PROBABLE clobbering, §2.14).
9. **Patrik's fix touches four readers**: `[neorotary4] bus=1` (Core, at start), `[cfexpress_hat] bus=1` (Core media watcher at start, Core's embedded Python reinsert helper on each eject, UI automounter at its own start). So "reboot or restart Core and the automounter" is exactly right; nothing applies live. CONFIRMED (§6).
10. **Live reload is close but not free**: each input/output module already has `start()` = `stop()` + `loadConfig()` + spawn. A reload entry point must run outside `commandMutex_`/`hardwareInputSequenceMutex_` and never on a module's own thread, must re-sync the LED, and INA219/CFE readers must stop caching. PROBABLE (§5.3).

---

## 1. `apertar-hardware.conf`

### 1.1 Candidate paths and which file wins

All Core readers build the same candidate list: `$APERTAR_HARDWARE_CONFIG` (if set and non-empty), `/home/pi/apertar-hardware.conf`, `/boot/firmware/apertar-hardware.conf`, `/boot/apertar-hardware.conf`, de-duplicated. CONFIRMED: `App:4288-4311`, `HW/GpioInput.cpp:55-76`, `HW/Pcf8574Input.cpp:55-76`, `HW/NeoRotary4Input.cpp:68-89`, `HW/GroveAnalogInput.cpp:54-65`, `HW/TriggerOutput.cpp:70-81`, `HW/RecordingIndicatorOutput.cpp:67-78`, `HW/Mpu6050RecordingSession.cpp:186-199`, Python helper `App:3429-3443`. No unit file sets `APERTAR_HARDWARE_CONFIG` in either repo (grep over `*.service`, `*.sh`, `*.conf`): PROBABLE that it is unset on a stock Pi.

But they do not agree on *which* candidate wins:

| Rule | Readers | Cite | Label |
| --- | --- | --- | --- |
| First file that exists, whether or not it has the section | INA219, CFE hat (Core), trigger output, recording LED, IMU (first file that opens), Python reinsert helper, UI automounter | `App:4497-4545`, `App:4557-4597`, `HW/TriggerOutput.cpp:256-356`, `HW/RecordingIndicatorOutput.cpp:252-396`, `HW/Mpu6050RecordingSession.cpp:855-1029`, `App:3472`, `UI/src/CfeAutomounter.cpp:131-145` | CONFIRMED |
| First file that *contains the section*; otherwise keep looking | GPIO, PCF8574, NeoRotary4, Grove analog | `HW/GpioInput.cpp:498-499`, `HW/Pcf8574Input.cpp:385-386`, `HW/NeoRotary4Input.cpp:439-440`, `HW/GroveAnalogInput.cpp:350-351` | CONFIRMED |
| Fixed path: env var or `/home/pi/…`, never `/boot` | WebUI editor (read and write), script runner, UI hotspot delay | `editableHardwareConfigPath()` `App:4313-4318` used at `App:5432`, `App:5483`, `App:8841`; `UI/src/WifiBridge.cpp:19-35` | CONFIRMED |

Consequences (PROBABLE, from the table): a config kept only in `/boot/firmware` drives the inputs but the editor shows (and on save creates) `/home/pi/…`, after which every reader switches to the new file on the next start; scripts are never found from a `/boot` config. Splitting sections across two files gives button sources from one file and INA219/trigger/LED from the other.

### 1.2 Common syntax and validation

| Rule | Detail | Cite | Label |
| --- | --- | --- | --- |
| Comments | Lines starting with `#` or `;` are skipped everywhere | e.g. `App:4509-4511`, `HW/GpioInput.cpp:396` | CONFIRMED |
| Inline comments | GPIO/PCF/NeoRotary/Grove cut the line at the first `#` or `;` anywhere; trigger/LED/IMU cut at `#`/`;` preceded by whitespace; **Core's INA219 and CFE-hat readers do not strip inline comments for integers**: `bus=1  # header` fails `parseConfigInteger` (only trailing whitespace allowed) and the default is kept silently. Bools are stripped there. | `HW/GpioInput.cpp:399-401`; `HW/TriggerOutput.cpp:56-66`; `HW/Mpu6050RecordingSession.cpp:209-220`; `App:4525`, `App:4531-4533`, `App:4580-4587`, `App:4448-4466`, `App:4469-4490` | CONFIRMED |
| Section names | Modules normalise (`lower`, trim, `-`/space/`.` → `_`); INA219/CFE compare the whole bracketed line lowercased (`[ina219]`); the script runner needs exactly `[run_script]`, case and spacing included | `HW/GpioInput.cpp:406`; `App:4513`, `App:4569`; `HW/HardwareScriptRunner.cpp:52` | CONFIRMED |
| Integers | `strtol(…, 0)`, so `0x49`, `73` and `0111` (octal) all parse | `App:4448-4466` and module copies | CONFIRMED |
| Bools | Modules: `true/yes/on/1`, `false/no/off/0`; Core's INA219/CFE also accept `enabled/disabled`; an unknown word keeps the previous value | `HW/GpioInput.cpp:98-106`; `App:4469-4490` | CONFIRMED |
| Ranges | Bus 0-255, address 0x03-0x77 (silently ignored if outside), clamps on poll/debounce etc. (per-section tables below) | per section | CONFIRMED |
| Unknown keys and sections | Silently ignored by every reader | all loaders `continue` on no match | CONFIRMED |
| Errors in mappings | A bad mapping (7+ actions, an empty item in a group, an LED token in a group) drops the whole mapping with one `std::cerr` line | `HW/ButtonActionList.hpp:88-100`, `:113-119` | CONFIRMED |

### 1.3 When each reader runs

| Reader | Reads the file | Applies a change without restart? | Cite | Label |
| --- | --- | --- | --- | --- |
| PCF8574, NeoRotary4, GPIO buttons/encoders, Grove analog | `start()` in `ApertarCoreApp::start()` | No: `start()` is called nowhere else | `App:7031-7036`; grep for `.start()` on these members finds only these lines | CONFIRMED |
| Standby power button | Not configurable; started at `App:7034-7035` unless `--simulate` | n/a | `App:7034-7035` | CONFIRMED |
| Trigger output | `start()` at `App:7026` | No | `App:7026-7029` | CONFIRMED |
| Recording LED | `start()` at `App:7038`, then state re-synced at `:7042-7043` | No | `App:7038-7043` | CONFIRMED |
| INA219 (Core) | first `readIna219Snapshot()` call; `static const` for the process lifetime | No | `App:4695` | CONFIRMED |
| CFE hat (Core media watcher) | once at the top of `runMediaWatcher()` (thread started at `App:6967`) | No | `App:9306-9313` | CONFIRMED |
| CFE hat + `[storage]` (Core's embedded Python NVMe reinsert watcher) | each time it is spawned after an eject | Yes, per eject | `App:3412`, `App:3466-3495`, `App:3600`, `App:3784` | CONFIRMED |
| Script runner `[run_script]` | each run | Yes | `HW/HardwareScriptRunner.cpp:195-205` (`execute` → `readScriptPaths`) | CONFIRMED |
| IMU sections | each recording start, each `configuredSensorSnapshot` (so every `GET /api/state`), each calibration and each `set_imu_*` | Yes | `HW/Mpu6050RecordingSession.cpp:1396`, `:1176`, `:1040`, `:1297`; `App:8206` | CONFIRMED |
| `GET /api/config` | each request | n/a | `App:7314-7319` | CONFIRMED |
| UI `DisplayConfigBridge` (`[display]`) | at construction | UI restart | `UI/src/DisplayConfigBridge.cpp:572-596` | CONFIRMED |
| UI `CfeAutomounter` (`[cfexpress_hat]`, `[storage]`) | process start | automounter restart | `UI/src/CfeAutomounter.cpp:787-799` | CONFIRMED |
| UI hotspot delay (`[network]`) | `autoHotspotDelayMs()`; template says restart `apertar-network.service` | service restart | `UI/src/WifiBridge.cpp:19-35`, `UI/src/DisplayConfigBridge.cpp:61` | CONFIRMED (call timing UNCONFIRMED) |
| UI `Ina219Bridge` | `loadConfiguration()` from the constructor path | UNCONFIRMED | `UI/src/Ina219Bridge.cpp:463`, `:490-500` | CONFIRMED (line), timing UNCONFIRMED |

### 1.4 Section and key reference

Defaults are the code defaults that apply when a key is absent; "Core tpl" and "UI tpl" are the values the two templates write. UI tpl = `UI/src/DisplayConfigBridge.cpp` unless noted.

#### `[ina219]` (battery / input rail monitor). Reader `loadIna219HardwareConfig` `App:4492-4548`; defaults `App:4281-4286`.

| Key (aliases) | Type, range | Default | Core tpl | UI tpl | Label |
| --- | --- | --- | --- | --- | --- |
| `enabled` | bool | true | true (`App:4341`) | true (`:71`) | CONFIRMED |
| `bus` (`channel`, `i2c_bus`) | 0-255 | 4 | 4 | 4 (`:72`; `UI/src/Ina219Bridge.cpp:45`) | CONFIRMED |
| `address` (`addr`) | 0x03-0x77 | 0x40 | 0x40 | 0x40 | CONFIRMED |

#### `[cfexpress_hat]` (RPI5-CFE-Hat MCU, card presence/eject status byte). Core reader `loadCfeHatConfig` `App:4550-4598`; struct `src/util/CfeHat.hpp:18-22`.

| Key (aliases) | Type, range | Default | Core tpl | UI tpl | Label |
| --- | --- | --- | --- | --- | --- |
| *(section present)* | | Core: hat **off** without the section, **on** as soon as the section appears (`App:4569-4571`, `CfeHat.hpp:19`). UI automounter: on by default (`UI/src/CfeAutomounter.cpp:106`) | present | present (`:297`) | CONFIRMED |
| `enabled` | bool | see above | true | true | CONFIRMED |
| `bus` (`channel`, `i2c_bus`) | 0-255 | 10 (`CfeHat.hpp:20`; UI `CfeAutomounter.cpp:38`) | 10 | 10 (`:299`) | CONFIRMED |
| `address` (`addr`) | 0x03-0x77 | 0x34 | 0x34 | 0x34 | CONFIRMED |

Core use: `CfeHatReader::cardPresence()` reads the status byte twice with SMBus receive-byte; bit 0 set = no card, `0x69` = nothing to report; disagreement or error = Unknown (`CfeHat.hpp:35-46`). CONFIRMED. The automounting itself is the UI repo's `ApertarCfeAutomounter` (`UI/CMakeLists.txt:149`), not Core. CONFIRMED.

#### `[storage]`

| Key | Readers | Default | Label |
| --- | --- | --- | --- |
| `mount_path` | Core's Python reinsert helper only (`App:3487-3493`, and only if `APERTAR_MEDIA_ROOT` is unset); UI automounter (`UI/src/CfeAutomounter.cpp:172-175`). Core's own media root comes from `--media` (`src/main.cpp:61`, `scripts/start-apertar-core.sh`), not this key | `/media/RAW` | CONFIRMED |
| `pcie_controller` | same two readers (`App:3494-3495`; `UI/src/CfeAutomounter.cpp:176-179`) | `1000110000.pcie` | CONFIRMED |

#### `[display]` (UI only)

Core never reads it; it only appears in Core's template (`App:4354-4371`). The UI reads `ui_width`, `ui_height`, `ui_layout`, `ui_rotation`/`rotation`/`orientation`, `controls_opacity`, `zoom_toggle_factor`, `windowed`, `hdmi_external_only` and camelCase aliases (`UI/src/DisplayConfigBridge.cpp:596-680`). Core's template key `controls_mode=Light` has **no reader** (grep finds it only at `App:4368`; the controls mode lives in UI.conf as `cameraControlsMode`). CONFIRMED.

#### `[network]` (UI only)

`hotspot_delay_seconds` 0-86400, default 60, read with `QSettings` from `$APERTAR_HARDWARE_CONFIG` or `/home/pi/…` only (`UI/src/WifiBridge.cpp:19-35`). Missing from Core's template. CONFIRMED.

#### `[run_script]` (Bash scripts launched by `run_script*` actions). Reader `readScriptPaths` `HW/HardwareScriptRunner.cpp:38-96`.

| Key | Rule | Cite | Label |
| --- | --- | --- | --- |
| `path` | slot 1, unless `path1` appears (then `path` lines are ignored) | `:59-60` | CONFIRMED |
| `path1`…`path5` | slots 1-5; any other key starting with `path` aborts the run with an error | `:62-68` | CONFIRMED |
| value | optional `'…'`/`"…"` quoting; unquoted values cut at `#`/`;`; must be absolute, a regular readable file | `:69-79`, `:88-90` | CONFIRMED |
| file size | config > 256 KiB → error | `:40-41` | CONFIRMED |

Execution: `/bin/bash -- <script>`, cwd = script's directory, stdin `/dev/null`, fds ≥ 3 closed, own process group, inherits Core's environment and user (`:207-240`). One job at a time; at most 5 queued or running; a pending/running duplicate (same slot, or slot 0 = "all") is dropped; `stop()` sends SIGTERM to the group, SIGKILL after 2 s (`:122-143`, `:151-166`). Core passes `editableHardwareConfigPath()` (`App:8841`). CONFIRMED.

#### `[imu]` and the driver sections `[mpu6050]`/`[bmi160]`/`[bmi270]`/`[icm42688p]`/`[gyro]`. Reader `Mpu6050RecordingSession::loadConfig` `HW/Mpu6050RecordingSession.cpp:851-1033`; defaults `HW/Mpu6050RecordingSession.hpp:95-121`.

| Section | Keys read | Cite | Label |
| --- | --- | --- | --- |
| `[imu]` | `driver` (`mpu6050`, `bmi160`, `bmi270`, `icm42688p` and spellings; anything else → mpu6050), `sync_mode` (default `free_run`), `enabled`, `sync_offset_ms` (`offset_ms`, `gyro_sync_offset_ms`; −2000…2000). **Nothing else.** | `:891-904`, `:939-955`, `:124-137` | CONFIRMED |
| active driver section, or `[gyro]` | `enabled`, `bus`/`bus_number` (0-32, default 1), `address`/`addr` (default 0x68), `sample_rate_hz` (25-1000, 500), `gyro_range_dps` (250-2000, 1000), `accel_range_g` (2-16, 8), `dlpf_hz` (5-260, 98), `use_fifo` (true), `fifo_batch_samples` (1-64, 24), `orientation`, `auto_calibrate_seconds` (0-5), `gyro_bias_x/y/z`, `level_reference_*`, `level_accel_x/y/z`, `sync_offset_ms` (only if `[imu]` has none), `frame_readout_time_ms` (0-100), `frame_readout_direction` (0-3) | `:957-1022`, `:171-184` | CONFIRMED |

So Core's template `[imu] bus=10 address=0x68 sample_rate_hz=500 gyro_range_dps=2000 accel_range_g=8 orientation=XYZ` (`App:4385-4394`) is ignored except `enabled`, `driver`, `sync_offset_ms`: effective gyro range is 1000 dps, not 2000. CONFIRMED. It still finds the sensor because a chip-ID mismatch triggers an auto-probe of every `/dev/i2c-0…32` at the configured address, 0x68 and 0x69 (`:1543-1600`, `:1602-1628`). CONFIRMED. Note `[imu] enabled=false` in Core's template vs `enabled=true` in the UI's (`UI/src/DisplayConfigBridge.cpp:202`). CONFIRMED.

#### `[pcf8574]` (alias `[pcf8574_buttons]`). Reader `Pcf8574Input::loadConfig` `HW/Pcf8574Input.cpp:318-390`; defaults `HW/Pcf8574Input.hpp:28-38`.

| Key (aliases) | Type, range | Default | Core tpl | UI tpl | Label |
| --- | --- | --- | --- | --- | --- |
| *(section present)* | sets `enabled=true` | | | | CONFIRMED `:347-350` |
| `enabled` | bool | true once the section exists | false (`App:4404`) | false (`:87`) | CONFIRMED |
| `bus` (`channel`, `i2c_bus`) | 0-255 | **1** | **10** (`App:4405`) | **1** (`:88`; `UI/src/Ina219Bridge.cpp:107`) | CONFIRMED |
| `address` (`addr`) | 0x03-0x77 | 0x20 | 0x20 | 0x20 | CONFIRMED |
| `poll_ms` (`poll_interval_ms`) | clamp 10-1000 | 40 | — | 40 | CONFIRMED |
| `debounce_ms` | clamp 0-1000 | 60 | — | 60 | CONFIRMED |
| `active_low` | bool | true | — | true | CONFIRMED |
| `pinN`, `pin_N`, `gpioN`, `gpio_N`, `pN` (N 0-7; optional suffix `_action`/`_function`) | action mapping (§3) | none | examples in comments | `pin0…pin7=none` | CONFIRMED `:108-138`, `:380-382` |

The same section's `bus`/`address` (and only those spellings in the trigger's case) are inherited by the trigger and the LED when they target the PCF (`HW/TriggerOutput.cpp:289-298`, `HW/RecordingIndicatorOutput.cpp:293-303`). CONFIRMED.

#### `[gpio]` = `[gpio_buttons]` = `[grove_digital]` = `[grove_buttons]`, and `[gpio_encoders]` = `[grove_encoders]`. Reader `GpioInput::loadConfig` `HW/GpioInput.cpp:373-503`; defaults `HW/GpioInput.hpp:45-56`.

| Key | Scope | Range | Default | Label |
| --- | --- | --- | --- | --- |
| `enabled` | per section (buttons vs encoders); **the section alone does not enable** | bool | false | CONFIRMED `:388-389`, `:426-430`, `:482-496` |
| `chip` (`gpiochip`, `gpio_chip`) | **shared** by both sections, last one wins | path or `auto` | auto | CONFIRMED `:431-432` |
| `active_low` | shared | bool | true | CONFIRMED `:433-434` |
| `pull` (`bias`) | shared | `up`/`down`/`off` | up | CONFIRMED `:435-436`, `:560-566` |
| `poll_ms` (`poll_interval_ms`) | shared | clamp 2-1000 | 12 | CONFIRMED `:437-439` |
| `debounce_ms` | shared | clamp 0-1000 | 60 | CONFIRMED `:440-442` |
| buttons: `dN`, `d_N`, `gpioN`, `gpio_N`, `pinN`, `pin_N`, `bcmN`, `bcm_N`, `grove_dN`, `grove_d_N` (+`_action`/`_function`) | buttons section | N = BCM 0-63 | — | CONFIRMED `:209-236`, `:443-448` |
| encoders: `encoderK_…`/`encK_…`/`rotaryK_…`, K 0-7, fields `a`/`gpio_a`/`pin_a`/`clk`, `b`/`gpio_b`/`pin_b`/`dt`, `cw`/`clockwise`/`right`/`up`/`plus`, `ccw`/`counter_clockwise`/`counterclockwise`/`left`/`down`/`minus`, `press_gpio`/`button_gpio`/`push_gpio`/`switch_gpio`/`sw`, `press`/`button`/`push`/`click`, `invert`/`invert_direction`/`reverse_direction`, `steps_per_event`/`steps`/`detent_steps` (clamp 1-8, default 4) | encoders section | | | CONFIRMED `:266-301`, `:449-479` |

An encoder needs both A and B and at least one action (`:485-494`). CONFIRMED. Because the timing keys are shared, the UI template's `[gpio_encoders] poll_ms=3 debounce_ms=40` (`UI/src/DisplayConfigBridge.cpp:175-176`), coming after `[gpio_buttons] poll_ms=12 debounce_ms=60`, sets 3 ms/40 ms for buttons too. PROBABLE (file order + shared fields).

#### `[neorotary4]` (aliases `[neo_rotary4]`, `[neo_rotary_4]`). Reader `NeoRotary4Input::loadConfig` `HW/NeoRotary4Input.cpp:355-444`; defaults `HW/NeoRotary4Input.hpp:36-48`. **Not in Core's template.**

| Key (aliases) | Range | Default | UI tpl (`UI/src/DisplayConfigBridge.cpp:131-155`) | Label |
| --- | --- | --- | --- | --- |
| *(section present)* | sets enabled | | | CONFIRMED `:386-390` |
| `enabled` | bool | true once present | false | CONFIRMED |
| `bus` (`channel`, `i2c_bus`) | 0-255 | 1 | 1 | CONFIRMED |
| `address` (`addr`) | 0x03-0x77 | 0x49 | 0x49 | CONFIRMED |
| `poll_ms` (`poll_interval_ms`) | clamp 10-1000 | 30 | 30 | CONFIRMED |
| `debounce_ms` | 0-1000 | 60 | 60 | CONFIRMED |
| `invert_direction` (`invert`, `reverse_direction`) | bool, **all four encoders** | false | false | CONFIRMED `:417-418`, `:582-583` |
| `reset_on_start` | bool (seesaw SW reset + 500 ms) | false | false | CONFIRMED `:419-420`, `:470-479` |
| `max_events_per_poll` | clamp 1-32 | 8 | 8 | CONFIRMED |
| `encoderK_cw/ccw/press` (and the `enc`/`rotary` prefixes and field aliases above), K 0-3 | action mapping | none | 0 ISO, 1 shutter, 2 WB, 3 fps (press 3 = resolution) | CONFIRMED `:222-257`, `:424-436` |

#### `[grove_analog]` (aliases `[grove_adc]`, `[analog_controls]`). Reader `GroveAnalogInput::loadConfig` `HW/GroveAnalogInput.cpp:246-355`; defaults `HW/GroveAnalogInput.hpp:52-62`. Not in Core's template.

| Key | Range | Default | Label |
| --- | --- | --- | --- |
| `enabled`, section-present → enabled | bool | true once present | CONFIRMED `:278-282`, `:295-296` |
| `bus` (`channel`, `i2c_bus`) | 0-255 | 1 | CONFIRMED |
| `address` (`addr`) | 0x03-0x77 | 0x04 | CONFIRMED |
| `poll_ms` | clamp 20-2000 | 80 | CONFIRMED |
| `deadband` (`deadband_raw`) | 0-2048 raw counts | 32 | CONFIRMED |
| `emit_on_start` (`sync_on_start`) | bool | false | CONFIRMED |
| `aN`/`chN`/`chanN`/`channelN`/`analogN` (N 0-7) = target; `…_min`, `…_max`, `…_step`, `…_deadband`, `…_invert`/`…_reverse`, `…_mode=preset|presets|stepped`, `…_presets` | target names §3.5 | | CONFIRMED `:147-182`, `:311-339` |

#### `[trigger_output]` (aliases `[trigger]`, `[capture_trigger]`, `[hotshoe]`). Reader `TriggerOutput::loadConfig` `HW/TriggerOutput.cpp:250-360`; defaults `HW/TriggerOutput.hpp:41-55`.

| Key (aliases) | Range | Default | Core tpl | Label |
| --- | --- | --- | --- | --- |
| `enabled` | bool | false | false | CONFIRMED |
| `target` (`type`, `backend`, `output`) | `gpio`/`pin`/`raspberry_pi_gpio`, or `pcf`/`pcf8574`/`i2c` | gpio | gpio | CONFIRMED `:305-310` |
| `chip` (`gpiochip`, `gpio_chip`) | path or auto | auto | auto | CONFIRMED |
| `line` (`gpio`, `gpio_line`) | ≥ 0 | 17 | 17 | CONFIRMED |
| `pin` | generic: becomes `pcf_pin` or `line` depending on target | — | — | CONFIRMED `:316-317`, `:346-351` |
| `open_drain` (`gpio_open_drain`) | bool | **false** | **true** | CONFIRMED (`hpp:47` vs `App:4424`) |
| `bus` (`pcf_bus`), `address` (`pcf_address`) | no range check | from `[pcf8574]` (`bus`/`address` only), else 1 / 0x20 | commented | CONFIRMED `:289-298`, `:320-325` |
| `pcf_pin` (`pcf8574_pin`) | 0-7 (checked at open) | 0 | 0 | CONFIRMED `:615-619` |
| `active_high` / `active_low` | bool | active low | active_high=false | CONFIRMED |
| `pulse_ms` (`duration_ms`) | clamp 1-5000 | 80 | 80 | CONFIRMED |
| `events` (`event`) | list of `recording_start`, `still`, `timelapse_start`, `timelapse_frame`, `all` (+aliases), separators `, ; \| +` | recording_start, still, timelapse_frame | same | CONFIRMED `:121-175` |

#### `[recording_indicator]` (aliases `[rec_indicator]`, `[record_led]`, `[recording_led]`, `[tally_led]`). Reader `RecordingIndicatorOutput::loadConfig` `HW/RecordingIndicatorOutput.cpp:247-399`; defaults `HW/RecordingIndicatorOutput.hpp:36-49`.

Same keys as the trigger minus `pulse_ms`/`events` (`:339-372`), default line −1/pin −1 (must be set). Two ways to enable, in this order: (1) `[recording_indicator] enabled=true` wins; (2) otherwise the **first** `pinN=recindicatorled` in `[pcf8574]` or `dN=recindicatorled` in a GPIO buttons section (LED tokens: `recindicatorled`, `rec_indicator_led`, `recording_indicator`, `recording_indicator_led`, `record_led`, `rec_led`, `tally`, `tally_led`) (`:118-129`, `:293-334`, `:382-393`). The PCF variant inherits that section's bus/address; the GPIO variant inherits its `chip`. CONFIRMED. Both Core's template and the UI's default `line=17` for trigger and LED alike (`App:4423`, `App:4437`), so enabling both with defaults requests GPIO 17 twice; the second request fails at start. PROBABLE (two `GPIO_V2_GET_LINE_IOCTL` on one line → EBUSY).

### 1.5 The three templates

| | Core `defaultHardwareConfigTemplate()` `App:4333-4446` | UI `DisplayConfigBridge.cpp:41-326` | UI `Ina219Bridge.cpp:69-…` |
| --- | --- | --- | --- |
| Used for | Shown by `GET /api/config` when the file is missing (`App:5437`); saving then creates the file from it | Written to `/home/pi/…` when the file is missing, when the UI starts (`:587`) | Same, from the INA219 bridge (`:497`) |
| Sections | ina219, cfexpress_hat, storage, display, run_script, imu, pcf8574, gpio, trigger_output, recording_indicator | network, run_script, ina219, pcf8574, trigger_output, recording_indicator, neorotary4, gpio_buttons, gpio_encoders, grove_analog, imu, mpu6050, bmi160, bmi270, icm42688p, cfexpress_hat, storage, display | ina219, pcf8574, trigger_output, … cfexpress_hat (`:316`), storage, display (no `[network]` found by grep) |
| `[pcf8574] bus` | **10** | **1** | **1** |
| `[imu]` | carries ignored bus/address/rates | only enabled/driver/sync keys | — |

CONFIRMED (lines above; Ina219Bridge's full section list not read line by line beyond the grep, so its tail is PROBABLE). Which UI template wins depends on which bridge is constructed first: UNCONFIRMED.

**Correction for the KB:** `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md` §6.6 says "`[pcf8574] bus=10` in the UI template vs `bus=1` in the Core template". It is the other way round: Core's template has `bus=10` (`App:4405`), both UI templates `bus=1` (`UI/src/DisplayConfigBridge.cpp:88`, `UI/src/Ina219Bridge.cpp:107`). CONFIRMED.

### 1.6 Who writes the file today

| Writer | How | Cite | Label |
| --- | --- | --- | --- |
| WebUI Config tab (Core) | whole file; `.bak` copy; `.tmp` + rename | `App:5463-5526` | CONFIRMED |
| IMU commands (Core) `set_imu_*`, `calibrate_gyro`, level reference | key-level `writeHardwareConfigValue(path, section, key, value)`: reads all lines, replaces the key inside the section (keeps indent and comments), appends the key at the end of the section, or appends a new section; `.tmp` + rename | `HW/Mpu6050RecordingSession.cpp:604-713`, `:715-…`, `:1148`, `:1295-1380` | CONFIRMED |
| UI `GyroConfigBridge` | its own key-level writer with `QSaveFile` | `UI/src/GyroConfigBridge.cpp:363-390`, `:1577` | CONFIRMED |
| UI template creators | only when the file is missing | `UI/src/DisplayConfigBridge.cpp:41-47`, `UI/src/Ina219Bridge.cpp:69-74` | CONFIRMED |
| Fan mode (Core) — writes **`/boot/firmware/config.txt`**, not this file | managed block `# BEGIN/END APERTAR FAN MODE` via `sudo -n install` | `App:2875-2877`, `App:3074-3210` | CONFIRMED |

No writer takes a lock or checks the file's mtime before writing; a WebUI save that started from text loaded before an IMU calibration overwrites the new bias (the `.bak` keeps it once). PROBABLE (no lock in any of the writers above; whole-file replace at `App:5510-5517`).

The key-level writer in `Mpu6050RecordingSession.cpp:604-713` is the existing Apertar precedent for a "system-controlled" file that stays hand-editable. The user-level settings live elsewhere, in `~/.config/CinePi/UI.conf` (`App:359-366`), written by `updateSharedUiGeneralSettings` (`App:1882`). CONFIRMED.

---

## 2. Hardware modules

### 2.1 Overview

| Module | Hardware | Transport | Inputs | Outputs | Thread / retry | Label |
| --- | --- | --- | --- | --- | --- | --- |
| `GpioInput` | Pi GPIO, Grove digital, incremental encoders | GPIO v2 char-dev ioctls, one request for all lines, polled | press edge per button; CW/CCW per N quadrature steps; encoder push = button | — | own thread; line request failure → retry every 1 s; read failure → 250 ms | CONFIRMED `HW/GpioInput.cpp:539-581`, `:621-744` |
| `Pcf8574Input` | one PCF8574 (8 pins) | `/dev/i2c-N`, `I2C_SLAVE`, 1-byte read | press edge per pin | — | 1 s / 250 ms retry | CONFIRMED `HW/Pcf8574Input.cpp:392-527` |
| `NeoRotary4Input` | Adafruit NeoRotary 4 (seesaw ATtiny817) | `/dev/i2c-N`, seesaw register protocol | 4 encoders: CW/CCW per count, push edge | — (NeoPixels not driven) | 1 s / 250 ms retry | CONFIRMED `HW/NeoRotary4Input.cpp:446-715` |
| `GroveAnalogInput` | Grove Base HAT ADC (STM32 0x04 / MM32 0x08 per UI template comment) | `/dev/i2c-N`, register 0x10+ch | 8 channels, 12-bit, deadband | — | 1 s retry | CONFIRMED `HW/GroveAnalogInput.cpp:357-484` |
| `StandbyPowerButtonInput` + `PowerButtonGesture` | Pi 5 power button (`pwr_button` evdev) | `/dev/input/eventN` | press / double press | — | rescans every 1.5 s | CONFIRMED `HW/StandbyPowerButtonInput.cpp:31-76`, `HW/PowerButtonGesture.hpp:1-39` |
| `TriggerOutput` | GPIO line or PCF8574 pin | GPIO v2 output / I2C byte write | — | pulse on capture events | worker thread, ≤ 4 queued pulses | CONFIRMED `HW/TriggerOutput.cpp:362-697` |
| `RecordingIndicatorOutput` | GPIO line or PCF8574 pin | same | — | level: recording/still exposure; 320 ms flash per photo/timelapse frame | worker thread | CONFIRMED `HW/RecordingIndicatorOutput.cpp:401-560` |
| `HardwareScriptRunner` | Bash scripts | `posix_spawn` | — | — | worker thread | CONFIRMED §1.4 |
| `Mpu6050RecordingSession` | MPU6050 / BMI160 / BMI270 / ICM42688-P | I2C | — | `.gcsv` beside each clip | per recording | CONFIRMED `HW/Mpu6050RecordingSession.hpp:16-92`, `.cpp:1382-1434` |
| INA219 (in App) | INA219 power monitor | I2C, opened and closed per read | — | battery/power telemetry | called per `/api/state` | CONFIRMED `App:4693-4755`, `App:7894` |
| CFE hat (in App) | RPI5-CFE-Hat MCU | SMBus receive byte | card presence | — | media watcher thread | CONFIRMED `src/util/CfeHat.hpp:24-73`, `App:9306-9331` |

There is exactly one instance of each module (`App.hpp:121-128`) and each `Config` holds a single bus/address, so two PCF8574s, two NeoRotary4s or two ADCs are not possible. CONFIRMED.

### 2.2 `GpioInput`

- Chip selection `auto`: tries `/dev/gpiochip0…9` sorted by a score: name/label containing `rp1` +100, `pinctrl_bcm`/`bcm2711`/`bcm2835` +90, `raspberrypi_exp` −50, ≥ 28 lines +10 (`HW/GpioInput.cpp:238-264`, `:505-537`). CONFIRMED.
- Request: all configured offsets (buttons, encoder A/B, encoder push) in one `GPIO_V2_GET_LINE_IOCTL`, flags INPUT (+ACTIVE_LOW) (+BIAS_PULL_UP/DOWN/DISABLED), consumer `apertar-gpio-input` (`:554-569`). If any one line is busy (for example GPIO 2/3 while I2C1 is on, or GPIO 0-27 under a DPI overlay), the whole request fails and **no GPIO input works**, retried every second (`:642-649`). CONFIRMED for the all-or-nothing request; the EBUSY cause is PROBABLE (kernel behaviour).
- Buttons: sample every `poll_ms`; a level must be stable for `debounce_ms`; the action fires on the stable transition to pressed only (`:690-710`). CONFIRMED.
- Encoders: Gray-code table (`:303-314`), per-encoder `invert`, `steps_per_event` (default 4, i.e. one event per full quadrature cycle), CW/CCW actions via the *rotation* callback (`:712-738`). Encoder push uses the button path (`:674-677`). CONFIRMED.
- No hold, release, long-press or multi-click. CONFIRMED (only `emitAction` on press at `:706-707`).

### 2.3 `Pcf8574Input`

- Open `/dev/i2c-<bus>`, `I2C_SLAVE <address>`, write `0xff` (quasi-bidirectional inputs), then read one byte per `poll_ms` (`HW/Pcf8574Input.cpp:392-443`). CONFIRMED.
- Pressed mask = `~raw` if `active_low` (`:498`). Debounce is on the whole byte: any pin changing restarts the stable timer for all eight (`:505-521`). CONFIRMED; PROBABLE consequence: a chattering pin delays the others.
- Press edge → `config_.actions[pin]` (`:512-519`); an LED-mapped pin has an empty action and never fires. CONFIRMED.

### 2.4 `NeoRotary4Input` (the device in Patrik's fix)

- Seesaw constants: status base 0x00, HW-ID reg 0x01, expected **0x87**; SW reset reg 0x7f; GPIO base 0x01 (DIRCLR_BULK 0x03, BULK 0x04, BULK_SET 0x05, PULLENSET 0x0b); encoder base 0x11, delta reg 0x40+n; push buttons on seesaw pins **12, 14, 17, 9** for encoders 0-3 (`HW/NeoRotary4Input.cpp:27-38`). CONFIRMED.
- Open: `I2C_SLAVE`, optional reset + 500 ms, verify HW ID (`:446-514`), set the four pins input + pull-up (`:516-542`). Every register read is write-select, sleep 8 ms, read (`HW/NeoRotary4Input.hpp:56`, `.cpp:559-570`). CONFIRMED.
- On (re)open the accumulated deltas are read and discarded (`:643-647`). Each poll reads the four signed 32-bit deltas; for each it fires `min(|delta|, max_events_per_poll)` CW or CCW actions through the rotation callback (`:650-665`). Push buttons are bit-clear = pressed, debounced like the PCF (`:680-709`). CONFIRMED.
- A wrong HW ID (for example the TMP117 at 0x48 that answers 0x12, KB source §2) gives "unexpected hardware ID" in the journal, retried every second (`:503-511`, `:635-638`). CONFIRMED.
- Per poll it does 5 register reads × 8 ms = 40 ms of sleeps plus `poll_ms` 30, so roughly 70 ms per cycle, and holds the bus for each transaction. PROBABLE (arithmetic from `:56`, `:650-711`); relevant if the encoder shares bus 10 with the camera (KB source §5).

### 2.5 `GroveAnalogInput`

Reads raw 12-bit values (write reg `0x10+ch`, read 2 bytes little-endian, clamp 0-4095, `HW/GroveAnalogInput.cpp:384-400`); emits when the change ≥ deadband (`:473-477`), normalised 0-1 with optional invert (`:415-417`), to `ApertarCoreApp::handleHardwareAnalogInput` (`App:8658-8784`). CONFIRMED. Target mapping in §3.5.

### 2.6 `StandbyPowerButtonInput` and `PowerButtonGesture`

Finds the evdev device whose name is `pwr_button` (`HW/StandbyPowerButtonInput.cpp:38-46`), reads `KEY_POWER` (`:66`). The gesture uses kernel timestamps: second press 80-500 ms after the first (with a release in between, within 500 ms) = DoublePress; < 80 ms = bounce (`HW/PowerButtonGesture.hpp:9-30`). App: in standby → `wake`; single press → `hardware_action power_button_press` (the touch UI opens its shutdown hold popup, `UI/qml/Main.qml:289-295`); double press → `enter_standby` (`App:8786-8806`). Not configurable. CONFIRMED.

### 2.7 `ButtonActionList` (shared by all button sources)

`maxButtonActions = 6`, `maxHardwareScripts = 5` (`HW/ButtonActionList.hpp:14-15`); `actionToken` (`:35-55`); `parseButtonActions` (`:79-110`); details in §3.1 and §3.4. CONFIRMED.

### 2.8 `TriggerOutput`

GPIO: line requested as OUTPUT (+OPEN_DRAIN), initial value inactive, consumer `apertar-trigger` (`HW/TriggerOutput.cpp:577-611`). PCF: reads the current byte as its shadow at open (`:640-644`) and writes the full byte on each edge (`:650-668`). Pulses are queued (≤ 4, `:26`, `:450-459`), each `pulse_ms` long (`:479-521`). Fed by `App::handleTriggerEvent` from `publishEvent`: `recording` active → RecordingStart; `photo_capture` → Still; `timelapse_frame` → TimelapseFrame; `timelapse` active → TimelapseStart (`App:11322-11357`). A sound-only recording also publishes `"event":"recording","active":true` (`App:8572`), so it pulses too. CONFIRMED (lines); PROBABLE that this is unintended.

### 2.9 `RecordingIndicatorOutput`

Active while `recordingActive || stillExposureActive || now < capturePulseUntil` (`HW/RecordingIndicatorOutput.cpp:528-559`); 320 ms flash per `photo_capture`/`timelapse_frame` (`:515-526`, `App:11341-11350`). PCF variant starts its shadow at `0xff` on purpose, so it never latches a pressed input low (`:693-695`). CONFIRMED.

### 2.10 `HardwareScriptRunner`

See §1.4 `[run_script]`. Requested from `App:8840-8843` with the fixed editable path. CONFIRMED.

### 2.11 `Mpu6050RecordingSession`

Started per recording only if the shared UI setting `recordGyroEnabled` passes `GyroRecordingOptions.enabled` and the config's `enabled` is true (`HW/Mpu6050RecordingSession.cpp:1388-1402`); writes `<clip>/<clip>.gcsv` (`:1418-1421`). Live readout and calibration are static helpers that build a throwaway session per call (`:1035-1045`, `:1173-1180`). CONFIRMED.

### 2.12 INA219 and the CFE hat

INA219: writes config `0x399F` and calibration 4096 (32 V / 3 A, 0.1 Ω) on every read, reads bus/shunt/current/power, estimates percent from a 4S Li-ion curve 13.2-16.8 V with 0.26 Ω sag compensation; falls back to `/sys/class/power_supply` (`App:4601-4616`, `App:4646-4691`, `App:4693-4800`). CONFIRMED. CFE hat: §1.4.

### 2.13 Status visibility

`enabled()`, `configPath()`, `lastError()` exist on `GpioInput`, `Pcf8574Input`, `NeoRotary4Input`, `GroveAnalogInput`, `TriggerOutput`, `RecordingIndicatorOutput`. The only reads in App are the two `lastError()` calls at start for the trigger and LED (`App:7026-7041`). Nothing goes into `get_state` or `/api/state`. CONFIRMED (grep). `HardwareInputTestAccess` is declared a friend (`HW/GpioInput.hpp:28`, `HW/Pcf8574Input.hpp:27`, `HW/NeoRotary4Input.hpp:35`, `App.hpp:50`) but no test source exists in the tree. CONFIRMED (grep).

### 2.14 Shared-resource hazards

| Hazard | Evidence | Label |
| --- | --- | --- |
| PCF8574 shared by buttons, trigger and LED: three fds, three shadow bytes. The trigger writes its open-time snapshot (which may contain a pressed button as 0 or the LED pin's old state); the LED writes `0xff` except its pin (cutting a trigger pulse short); the input writes `0xff` on every reopen (turning an active-low LED off until the next change) | `HW/TriggerOutput.cpp:640-668`, `HW/RecordingIndicatorOutput.cpp:693-716`, `HW/Pcf8574Input.cpp:426-430`, `:479-488` | PROBABLE |
| Trigger writing a snapshot bit 0 onto an input pin that was pressed at open drives that pin low until something writes 1: a stuck "pressed" button | PCF8574 quasi-bidirectional pins; `HW/TriggerOutput.cpp:640-644` | PROBABLE |
| Trigger and LED both default to GPIO 17 | `App:4423`, `App:4437` | CONFIRMED (defaults); conflict PROBABLE |
| GPIO 2/3 (I2C1) or 0-27 (DPI) requested as button inputs make the whole GPIO request fail | `HW/GpioInput.cpp:571-576`, `:642-649` | PROBABLE |
| I2C devices on bus 10 share the camera's control bus | KB source §3.1, §5 | PROBABLE (from KB) |

---

## 3. The action vocabulary

### 3.1 Pipeline

1. **Load** (module thread, at start): the value string goes through `hardware::normalizeButtonMapping(value, normalizeSingleAction)` (`HW/ButtonActionList.hpp:112-119`), which splits on commas, runs `actionToken` on each item (trim, lowercase, `ev-<digit>` → `evm<digit>`, `ev+<digit>` → `ev<digit>`, then `-`, space, `.` → `_`; `:35-55`), rejects output tokens in groups (`:96-100`), runs the module's `normalizeSingleAction` (alias → canonical; unknown names pass through unchanged), drops `none/off/disabled`, de-duplicates, and joins with commas. CONFIRMED.
2. The three `normalizeSingleAction` copies (`HW/Pcf8574Input.cpp:140-242`, `HW/GpioInput.cpp:108-202`, `HW/NeoRotary4Input.cpp:121-215`) are **identical** once whitespace is collapsed (`cmp` of normalised extracts). CONFIRMED.
3. **Fire**: the module calls `handleHardwareInputAction(joined, buttonPress)` (`App:6926-6932`): rotation callbacks pass `buttonPress=false`. App re-splits with an identity normaliser (`App:8813-8817`), takes `hardwareInputSequenceMutex_` (`:8819`), and if the camera is in standby a *button* press sends `wake` and stops, a rotation does nothing (`:8820-8827`). Otherwise each action runs in order through `handleSingleHardwareInputAction`; `standby` is skipped for rotation; the loop stops once standby is entered (`:8830-8835`). CONFIRMED.
4. **Dispatch**: `dispatchHardwareInputCommand` takes `hardwareActionMutex_`, sets `id=-1` and calls the same `handleCommand` the socket and `/api/command` use (`App:8636-8644`); `{"ok":false…}` replies are logged only. CONFIRMED.

### 3.2 Aliases accepted by `normalizeSingleAction` (identical in all three)

Cite: `HW/GpioInput.cpp:108-202` (equal in the other two). CONFIRMED.

| Canonical | Aliases |
| --- | --- |
| *(nothing)* | `none`, `off`, `disabled`; LED tokens `recindicatorled`, `rec_indicator_led`, `recording_indicator`, `recording_indicator_led`, `record_led`, `rec_led`, `tally`, `tally_led` |
| `capture` | `record`, `capture`, `camera_button`, `take` |
| `record_toggle` | `record_toggle`, `toggle_record`, `rec` |
| `photo` | `still`, `photo`, `take_photo` |
| `timelapse` | `timelapse`, `time_lapse` |
| `eject` | `eject`, `unmount`, `eject_media`, `unmount_media` |
| `still_mode` | `still_mode`, `photo_mode` |
| `settings` | `settings`, `settings_page` |
| `clip_browser` | `clip_browser`, `browser`, `playback` |
| `quick_menu` | `quick_menu`, `quickmenu` |
| `standby` | `standby`, `standby_toggle` |
| `zoom_toggle` | `zoom`, `zoom_toggle`, `preview_zoom` |
| `run_script`, `run_script1`…`run_script5` | `run_script`, `script`, `run_scriptN`, `run_script_N`, `scriptN`, `script_N` (`HW/ButtonActionList.hpp:17-33`) |
| `focus_peaking` | `focus_peaking`, `peaking` |
| `zebra` | `zebra`, `zebras` |
| `false_color` | `false_color`, `falsecolour` |
| `guides` | `guides` |
| `center_marker` | `center_marker`, `centre_marker` |
| `grayscale` | `grayscale`, `greyscale` |
| `smpte` | `smpte`, `smpte_bars`, `color_bars`, `colour_bars` |
| `external_monitor` | `external_monitor`, `external_monitoring`, `hdmi` |
| `date_time_overlay` | `date_time`, `date_time_overlay` |
| `audio_meter` | `audio_meter`, `vu_meter`, `vumeter` |
| `fps` / `fps_up` / `fps_down` | `fps`, `fps_cycle` / `fps_up`, `fps_next`, `fps_plus` / `fps_down`, `fps_prev`, `fps_previous`, `fps_minus` |
| `resolution` / `_up` / `_down` | `resolution`, `resolution_cycle`, `res`, `res_cycle` / `resolution_up/next/plus`, `res_up/next/plus` / `resolution_down/prev/previous/minus`, `res_down/prev/previous/minus` |
| `iso` / `iso_up` / `iso_down` | `iso`, `iso_cycle` / `iso_up/next/plus` / `iso_down/prev/previous/minus` |
| `shutter` / `_up` / `_down` | `shutter`, `shutter_cycle` / `shutter_up/next/plus` / `shutter_down/prev/previous/minus` |
| `wb` / `wb_up` / `wb_down` | `wb`, `white_balance`, `whitebalance`, `wb_cycle`, `white_balance_cycle` / `wb_up`, `white_balance_up`, `whitebalance_up`, `wb_next`, `wb_plus` / `wb_down`, `white_balance_down`, `whitebalance_down`, `wb_prev`, `wb_previous`, `wb_minus` |
| anything else | passed through unchanged; App parses the parameterised forms below; otherwise logged "unknown action" at fire time (`App:9147`) |

`ev_up`, `ev_down` and the numeric forms are not in the normaliser; they pass through. CONFIRMED.

### 3.3 Complete action → command table (`ApertarCoreApp::handleSingleHardwareInputAction`, `App:8838-9148`)

Order matters: the checks run top to bottom, first match wins. Socket form is `{"cmd":"<name>", <fields>}` (`src/ipc/ControlProtocol.cpp:164-230`).

| # | Action (form) | Socket command(s) and fields | Behaviour | Cite | Label |
| --- | --- | --- | --- | --- | --- |
| 1 | `run_script`, `run_script1`…`5` | none: `HardwareScriptRunner::request(editable path, slot)`; slot 0 runs all configured scripts in order | not a socket command | `App:8840-8843` | CONFIRMED |
| 2 | `zoom_toggle` | event `hardware_action zoom_toggle` | touch UI toggles preview zoom on the camera page (`UI/qml/Main.qml:307-311`); WebUI ignores `hardware_action` (no match in `Web`) | `App:8844-8847` | CONFIRMED |
| 3 | `standby` | `enter_standby` | buttons only; while in standby any button wakes instead | `App:8857-8860`, `:8820-8832` | CONFIRMED |
| 4 | `ev_up`, `ev_down` | `set_exposure_compensation value=<current ± 1/3, clamp −3…+3>` | adjusts AE without enabling Auto ISO/shutter (template comment `App:4399-4400`) | `App:8865-8870` | CONFIRMED |
| 5 | `evX`, `evmX` (written `ev1`, `ev-1`, `ev+0.7`, `ev0`) | `set_exposure_compensation value=±X` | `_` read as decimal point; `ev-1/3` is not parsed | `App:8871-8874`, `:1390-1402` | CONFIRMED (`1/3` failure PROBABLE: `parseDoubleValue("1/3")`) |
| 6 | `fpsX` (X > 0, e.g. `fps24`, `fps23.976`) | `set_fps value=X` | no clamp here | `App:8876-8881` | CONFIRMED |
| 7 | `resolutionWxH`, `resWxH`, `res_W_H`, `resolutionW*H` | `set_resolution width height` | not checked against the sensor list here | `App:8883-8889`, `:1404-1422` | CONFIRMED |
| 8 | `isoX` (X > 0) | `set_iso value=round(X)` | | `App:8891-8896` | CONFIRMED |
| 9 | `shutterXs`, `shutter_secondsXs`, `shutter_speedXs`, `shutter_sXs` (0 < X ≤ 30) | `set_shutter_us value=X·10⁶` | e.g. `shutter2s`, `shutter0.5s` | `App:8898-8901`, `:1440-1456` | CONFIRMED |
| 10 | `shutter_angleX`, `shutterangleX` | `set_shutter_us value=X/360 · 10⁶/fps` | | `App:8903-8911` | CONFIRMED |
| 11 | `shutter_speedX`, `shutterspeedX`, `shutter_sX` (also `…1/X`, `…1_X`) | `set_shutter_us value=10⁶/X` | | `App:8913-8921`, `:1424-1438` | CONFIRMED |
| 12 | `shutterX`, `shutter1/X` | `set_shutter_us` | angle X in video; 1/X s if written `1/X`, in photo mode or during timelapse | `App:8923-8937` | CONFIRMED |
| 13 | `wbX`, `white_balanceX`, `whitebalanceX` (trailing `k` allowed) | `set_wb kelvin=clamp(X, 2500, 8000)` | `wb5k` becomes 5 K → 2500 K | `App:8939-8946`, `:1398-1399` | CONFIRMED |
| 14 | `fps`, `fps_up`, `fps_down` | `set_fps value=<next preset>` | cycle wraps; up/down stop at the ends; presets §3.6 | `App:8948-8954` | CONFIRMED |
| 15 | `resolution`, `resolution_up`, `resolution_down` | IMX585, video, CinemaDNG or MLV: `set_clear_hdr enabled=false`, or `set_clear_hdr enabled=true` + `set_raw_bit_depth value=16` (toggle, all three names alike, "temporary" 2026-10-27). Otherwise `set_resolution` to the next preset | | `App:8956-8980` | CONFIRMED |
| 16 | `iso`, `iso_up`, `iso_down` | `set_iso value=…` or `set_iso_auto` | Auto is position 0 in the ring | `App:8982-8993` | CONFIRMED |
| 17 | `shutter`, `shutter_up`, `shutter_down` | `set_shutter_us` or `set_shutter_auto` | Auto is position 0; angles in video, speeds in photo/timelapse | `App:8995-9022` | CONFIRMED |
| 18 | `wb`, `wb_up`, `wb_down` | `set_wb kelvin=<next preset>` | no Auto in the ring | `App:9024-9031` | CONFIRMED |
| 19 | `capture` | timelapse running → `timelapse_stop`; photo mode with a timelapse interval → `timelapse_start value format`; photo mode → `capture_photo format count`; recording (video or sound) → `record_stop`; else `record_start` | the "main button" | `App:9033-9054` | CONFIRMED |
| 20 | `record_toggle` | `record_stop` / `record_start` | | `App:9056-9062` | CONFIRMED |
| 21 | `photo` | `capture_photo format count` (from UI.conf) | | `App:9064-9070` | CONFIRMED |
| 22 | `timelapse` | `timelapse_stop` / `timelapse_start value format` | | `App:9072-9082` | CONFIRMED |
| 23 | `eject` | `eject_media` | ignored while recording or timelapse | `App:9084-9091` | CONFIRMED |
| 24 | `still_mode` | `set_photo_mode_enabled enabled=!current` + event | | `App:9093-9099` | CONFIRMED |
| 25 | `focus_peaking`, `zebra`, `false_color`, `guides`, `center_marker`, `grayscale`, `smpte`, `external_monitor`, `date_time_overlay`, `audio_meter` | `set_<name>_enabled enabled=!current` + event `hardware_action <name>` | groups flip each independently (README) | `App:9101-9140`, `:8646-8656`; `README.md:175` | CONFIRMED |
| 26 | `settings`, `clip_browser`, `quick_menu` | event `hardware_action <name>` only | touch UI opens settings / browser / quick menu (`UI/qml/Main.qml:313-330`) | `App:9142-9145` | CONFIRMED |
| 27 | anything else | none | `Hardware input action ignored: unknown action` | `App:9147` | CONFIRMED |
| — | power button (not mappable) | `wake`, event `power_button_press`, or `enter_standby` | §2.6 | `App:8786-8806` | CONFIRMED |

Not expressible as a hardware action today (no branch): `iso_auto`, `wb_auto`, `shutter_auto` (only via the cycles), `apply_preset`, `format_media`, `mount_media`, sound recorder, `set_fan_mode`, `restart_system`, `power_off_system`, LUT/anamorphic toggles, AF modes. CONFIRMED by the absence of branches in `App:8838-9148` (e.g. `iso_auto` falls through every check to `:9147`).

### 3.4 Groups (`P2=a,b,…`)

- Up to 6 items (`HW/ButtonActionList.hpp:14`, `:88-91`), comma-separated; spaces allowed; an empty item (`a,,b`) rejects the whole mapping (`:92-95`); duplicates are removed (`:103-104`); an LED token may only stand alone (`:96-100`). CONFIRMED.
- Run sequentially, each its own `handleCommand`, under one sequence lock so two buttons' groups do not interleave (`App:8818-8836`). A failure in one item does not stop the next (replies are only logged, `App:8641-8642`). CONFIRMED.
- `standby` should be last: the loop breaks once the camera is in standby (`App:8834`; template advice `App:4402-4403`). CONFIRMED.
- Works for encoder directions too (`encoder0_cw=iso_up,wb_up`), minus `standby`. CONFIRMED (`App:8832`).
- README's example: `P0=iso200,fps24,wb5600`, `P1=focus_peaking,zebra`, `P2=capture` (`README.md:169-173`). CONFIRMED.

### 3.5 Analog targets (`[grove_analog] aN=…`)

Aliases are normalised twice, identically (`HW/GroveAnalogInput.cpp:125-145`, `App:8588-8610`): `white_balance`/`whitebalance` → `wb`; `focus`/`focus_peaking`/`focus_peaking_value` → `focus_peaking_threshold`; `zebra`/`zebras` → `zebra_threshold`; `volume`/`input_gain` → `input_volume`; `headphone(s)` → `headphone_volume`; `opacity`/`controls_opacity` → `camera_controls_opacity`; `res` → `resolution`. CONFIRMED.

| Target | Command | Mapping | Cite | Label |
| --- | --- | --- | --- | --- |
| `iso` | `set_iso` | knob position → ISO preset index | `App:8677-8685` | CONFIRMED |
| `fps` | `set_fps` | fps preset index | `App:8687-8695` | CONFIRMED |
| `resolution` | `set_resolution` | resolution preset index | `App:8697-8708` | CONFIRMED |
| `wb` | `set_wb` | `mode=preset`: WB presets; else linear `min`…`max` (default 2500-8000) rounded to `step` (default 50) | `App:8710-8723` | CONFIRMED |
| `shutter` | `set_shutter_us` | angle or speed presets by mode | `App:8725-8741` | CONFIRMED |
| `focus_peaking_threshold`, `zebra_threshold` | `set_focus_peaking_threshold`, `set_zebra_threshold` | 0-1, step 0.01 | `App:8743-8757` | CONFIRMED |
| `input_volume`, `headphone_volume` | `set_input_volume`, `set_headphone_volume` | 0-100 | `App:8759-8773` | CONFIRMED |
| `camera_controls_opacity` | `set_camera_controls_opacity` | 0.15-1.0 | `App:8775-8781` | CONFIRMED |

`min`/`max`/`step` only affect `wb` (non-preset), thresholds, volumes and opacity; `mode=preset` only affects `wb`. CONFIRMED (the other branches never read them).

### 3.6 Preset lists used by the cycles and the analog knobs

| List | Values | Cite | Label |
| --- | --- | --- | --- |
| ISO | 100, 200, 400, 800, 1600, 3200, 6400, 12800, 25600, 51200 | `App:1311-1314` | CONFIRMED |
| Shutter angles | 11.25 … 360 (20 values) | `App:1316-1322` | CONFIRMED |
| Shutter speeds | 1/24 … 1/1000 (15); long exposure adds 30 s … 1/15 s (17); trimmed to the timelapse exposure limit | `App:1324-1344` | CONFIRMED |
| WB | 2500 … 8000 K (19) | `App:1346-1353` | CONFIRMED |
| FPS | IMX477/577: 24, 25, 30, 50, 60, 100; others: 25, 33, 50 (2026-10-27, temporary); filtered by the sensor/resolution maximum, with 16-bit Clear HDR treated as 12-bit SDR | `App:1174-1200`, `:1098-1172` | CONFIRMED |
| Resolutions | per sensor (IMX577 5, IMX477 25, IMX294 13, IMX585 2, others 2) | `App:1214-1286` | CONFIRMED |

---

## 4. The WebUI Config panel

| Element | Detail | Cite | Label |
| --- | --- | --- | --- |
| Navigation | Settings nav item `config` | `Web:2773` | CONFIRMED |
| Panel | "Apertar Config", copy "Edit the hardware, display, input, media, and IMU config file used by ApertarCore and the native UI."; Path tile; Status tile; `<textarea id=settingsConfigEditor spellcheck=false wrap=off>`; **Reload Config**; **Save Config** (enabled only when dirty); note "Hardware, input, display, and sensor changes may need ApertarCore or the UI restarted before they fully apply." | `Web:3840-3872` | CONFIRMED |
| Load | on opening the panel when not dirty, and on Reload (confirm before discarding edits): `GET /api/config` with `cache: no-store`; shows "Saved/New file • size • modified" | `Web:6203-6204`, `:10330-10370` | CONFIRMED |
| Save | client checks non-empty; `POST /api/config` body = raw text, `Content-Type: text/plain`; toast "Config saved. Backup: ~/apertar-hardware.conf.bak."; silent reload | `Web:10372-10401` | CONFIRMED |
| `GET /api/config` | `{ok, path, display_path (~ for $HOME), exists, size_bytes, size_text, modified_text, text}`; when the file is missing, `text` = Core's template and `exists=false` | `App:7314-7319`, `App:5430-5461` | CONFIRMED |
| `POST /api/config` | rejects empty, > 256 KiB (`App:66`), NUL; creates the parent dir; copies the old file to `<path>.bak` (one generation, overwritten each save); writes `<path>.tmp`, renames; replies `{ok, path, display_path, backup_path, backup_display_path}`; on error HTTP 400 | `App:7321-7341`, `App:5463-5526` | CONFIRMED |
| What a save does | Nothing else: no module is stopped or restarted, no event is published. Effects: scripts and IMU see it at next use (§1.3); everything else needs a Core restart, the display/automounter/network keys a UI-side restart | `App:7321-7341`; §1.3 | CONFIRMED |
| Web server | binds `0.0.0.0:8000` by default, requests ≤ 1 MiB, no authentication, only a same-origin/`Sec-Fetch-Site` check | `App.hpp:36-37`, `src/web/WebServer.cpp:23`, `:156-170` | CONFIRMED |

Other hardware UI in the WebUI:

- **Record → Gyro Data / Gyro Calibration**: IMU driver and orientation selects, live axis canvas, sync offset ±1 ms and reset, Set/Clear Level, Calibrate Gyro Bias, "Config <path>" readout; sends `set_imu_driver`, `set_imu_orientation`, `adjust_imu_sync_offset`, etc. through `/api/command` (`Web:2940-3008`, `:10992-11003`). These write the hardware config (§1.6). CONFIRMED.
- **Power**: battery type/capacity (UI.conf, not the hardware file), Battery Info from INA219 telemetry in `/api/state`, auto power-off, standby (`Web:3673-3800`; `App:8087-8095`). CONFIRMED.
- No page lists GPIO/PCF/NeoRotary/Grove mappings, buses, detected devices or driver errors; grep for `pcf8574|neorotary|grove|gpio` in `Web` finds nothing, and in the touch UI only the two template writers. CONFIRMED.

---

## 5. Commands that touch hardware or config, and live reload

### 5.1 HTTP and socket surface today

| Surface | What | Touches | Cite | Label |
| --- | --- | --- | --- | --- |
| `GET /api/config`, `POST /api/config` | raw file | file only | `App:7314-7341` | CONFIRMED |
| `POST /api/command` | any socket command (JSON `{"cmd":…}`) | as below | `App:7783-7788`, `:7231-7237` | CONFIRMED |
| `GET /api/state` | INA219 read and IMU live sample on every poll | I2C | `App:7894`, `App:8206` | CONFIRMED |
| Unix socket `/tmp/apertar-core.sock` | same `handleCommand`; events broadcast | | `App.hpp:34`, `App:7201-7229`, `:11319` | CONFIRMED |
| `set_imu_driver`, `set_imu_orientation`, `set_imu_sync_offset`, `adjust_imu_sync_offset`, `reset_imu_sync_offset`, `set_imu_level_reference`, `clear_imu_level_reference`, `calibrate_gyro` | write the hardware config (key level) | file + I2C | `App:10112-10189` | CONFIRMED |
| `set_record_gyro_enabled` | UI.conf toggle | | `App:10110-10111` | CONFIRMED |
| `set_fan_mode` | `/boot/firmware/config.txt` managed block via `sudo -n install` | boot config | `App:11034-11043`, `:3159-3210` | CONFIRMED |
| `enter_standby`, `wake`, `set_standby_timeout`, `set_standby_usb_power_off` | standby helpers (`/usr/local/libexec/apertar-standby-low-power`, USB power) | system | `App:9517-9604` | CONFIRMED |
| `eject_media`, `mount_media`, `format_media`, `run_media_speed_test` | media; eject may spawn the Python reinsert helper that reads `[cfexpress_hat]` | I2C, PCIe | `App:11045-11088`, `App:3784` | CONFIRMED |
| `restart_system`, `power_off_system`, `shutdown` | power | | `App:11267-11284` | CONFIRMED |
| Events | `hardware_action` (`power_button_press`, `standby_power_sleep`, `standby_power_wake`, `zoom_toggle`, `still_mode`, toggles, `settings`, `clip_browser`, `quick_menu`) | | `App:8654`, `:8790-8801`, `:8845`, `:9097`, `:9143` | CONFIRMED |

There is no command to reload hardware config, list I2C buses or devices, read driver status, validate a config, or press a virtual button. No SIGHUP handling. CONFIRMED (help list `App:9634`; grep for `SIGHUP|reload` in `src/main.cpp` and `App` is empty).

### 5.2 What already makes reload feasible

- Every input/output module's `start()` begins with `stop()` and then `loadConfig()` (`HW/GpioInput.cpp:329-347`, `HW/Pcf8574Input.cpp:273-292`, `HW/NeoRotary4Input.cpp:310-329`, `HW/GroveAnalogInput.cpp:201-220`, `HW/TriggerOutput.cpp:362-374`, `HW/RecordingIndicatorOutput.cpp:401-413`). `stop()` joins the thread and releases lines/fds (`HW/TriggerOutput.cpp:429-448` drives the output inactive first). CONFIRMED. So `stop(); start();` per module is a reload.
- The script runner and IMU already re-read per use. CONFIRMED (§1.3).

### 5.3 What would have to change (PROBABLE unless stated; derived from the cited lines)

1. **An entry point** (e.g. `reload_hardware_config` command, and/or done by `POST /api/config` after a successful save) that stops and restarts, in Core's start order, trigger → PCF8574 → NeoRotary4 → GPIO → Grove → LED, then re-syncs the LED with `setRecordingActive`/`setStillExposureActive` as `App:7042-7043` do.
2. **Run it outside the locks and off the module threads.** `handleCommand` holds `commandMutex_` (`App:9485`); a module thread inside a callback may be waiting for `hardwareInputSequenceMutex_` (`App:8819`) or `commandMutex_` (via `App:8640`). `stop()` joins that thread, so a reload done inside `handleCommand`, or from a hardware action (self-join), deadlocks. `handleWebRequest` for `/api/config` does not take `commandMutex_` (`App:7321-7341`), so doing it there, or on a dedicated thread, avoids that. Recording state should gate it (no reload of the trigger mid-pulse, or of the GPIO lines while a take runs, if the design wants that).
3. **INA219**: replace the `static const` (`App:4695`) with a reloadable config (member + mutex, or re-read on mtime).
4. **CFE hat in Core**: the media watcher builds its `CfeHatReader` once (`App:9310-9311`); it needs a reload flag or a reader rebuilt per cycle when the config changes. The UI automounter (`UI/src/CfeAutomounter.cpp:792`) still needs its own restart (another repo, another process).
5. **One parser, one template, one schema.** Today 4 module parsers plus App's plus the Python helper plus 5 UI parsers. A structured editor needs a single list of sections/keys/ranges/aliases (this report's §1.4 is that list as the code has it), and a validator Core can run on `POST` (unknown section/key, out-of-range bus/address/pin, pin used twice, trigger/LED on the same line, LED in a group, 7+ actions, `/dev/i2c-N` missing).
6. **Status in state**: add each module's `enabled()`, `configPath()`, `lastError()` (all present, unread) to `/api/state` so the WebUI can say "NeoRotary4: /dev/i2c-1: No such file or directory" (KB source §6.3 asks the same).
7. **Writers**: either route all writes through one Core function with an mtime/etag check (so the raw editor cannot silently overwrite an IMU calibration, §1.6), or accept last-writer-wins and keep the `.bak`.
8. **Bus selection**: every I2C section already has `bus`; only the defaults and the UI need fixing. Probing exists only for the IMU (`HW/Mpu6050RecordingSession.cpp:1543-1600`); the NeoRotary4 `verifyDevice` HW-ID check (`HW/NeoRotary4Input.cpp:494-514`) is a ready per-device probe.
9. **`config.txt`**: Core already knows how to manage a block in `/boot/firmware/config.txt` (`App:3074-3210`, fan mode), which is the mechanism an "enable I2C1 / disable DPI" switch would use. Under Patrik's house rule (only he edits `config.txt`) the port should show the lines to change instead of writing them. Design note, not a code fact.

---

## 6. Patrik's NeoRotary fix, mapped onto the code

KB: `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md` §4 and `lessons/hardware-log.md` (2026-10-23 entry). The fix was `[cfexpress_hat] bus=1` and `[neorotary4] enabled=true bus=1 address=0x49`, after the DPI overlays were disabled so `/dev/i2c-1` exists.

| Setting | Reader | When it applies | Cite | Label |
| --- | --- | --- | --- | --- |
| `[neorotary4] enabled=true bus=1 address=0x49` | `NeoRotary4Input::loadConfig` | Core restart | `HW/NeoRotary4Input.cpp:355-444`; `App:7032` | CONFIRMED |
| `[cfexpress_hat] bus=1` | Core media watcher (card presence during takes) | Core restart | `App:9310` | CONFIRMED |
| same | Core's embedded Python reinsert watcher | next eject | `App:3481-3485`, `:3784` | CONFIRMED |
| same | UI `ApertarCfeAutomounter` | automounter restart | `UI/src/CfeAutomounter.cpp:164-170`, `:792` | CONFIRMED |
| No `[neorotary4]` section in Core's template, so a user who opens the WebUI editor on a Pi without a file sees no hint that the device exists | `App:4333-4446` | | CONFIRMED |
| Writing `bus=1  # header` (with a comment) for the hat is silently ignored by Core's reader (default 10 kept) but parsed by the NeoRotary reader | `App:4580-4587` vs `HW/NeoRotary4Input.cpp:375-377` | | CONFIRMED |
| With `/dev/i2c-1` absent, NeoRotary4 logs `/dev/i2c-1: No such file or directory` once (deduplicated) and retries every second, with no UI trace | `HW/NeoRotary4Input.cpp:451-456`, `:614-622`, `:635-638` | | CONFIRMED |

What a structured editor needs for this case (PROBABLE, from §1.4, §2.4, §5.3): a bus picker per I2C device populated from the `/dev/i2c-*` that exist, a per-device "found / not found / wrong ID" status (HW ID 0x87 for the NeoRotary4, status byte for the hat), and a warning when bus 1 is selected but does not exist (the DPI case), plus the restart scope of each key.

---

## 7. Gaps relative to Cinemate's editor (see R1, `r1-cinemate-gpio.md`)

Derived by comparing this report with R1 §1.4-§1.9 and §2.1; labels are PROBABLE unless the Apertar side is the point.

| Cinemate has (per R1) | Apertar Core today | Label |
| --- | --- | --- |
| Gestures: press, double, triple, hold; rotary press/hold; chords (`combined_actions`) | press only (§2.2-§2.4); groups instead of chords | Apertar side CONFIRMED; comparison PROBABLE |
| Per-button pull-up and debounce | GPIO: shared `pull`/`debounce_ms`/`active_low`/`poll_ms` across all lines and both sections (`HW/GpioInput.cpp:431-442`) | Apertar side CONFIRMED |
| Per-encoder reverse | GPIO encoders: per encoder; NeoRotary4: one flag for all four | CONFIRMED |
| Method dropdown built from a method list with argument schema | No machine-readable action list in Core; the vocabulary exists only as code branches (§3) and template comments | CONFIRMED |
| I2C page with a bus scan | none (§4) | CONFIRMED |
| GPIO OUT page | trigger + tally LED only (§2.8-§2.9) | CONFIRMED |
| JSON settings file written by the editor | INI file, raw editor, IMU key-level writer | CONFIRMED |

---

## 8. Open points (UNCONFIRMED)

1. Which UI bridge writes the missing-file template first on a fresh image (`DisplayConfigBridge` vs `Ina219Bridge`), and therefore whether `[network]`, `[neorotary4]`, `[gpio_*]`, `[grove_analog]` are present on Patrik's Pi.
2. Whether the seesaw encoder delta is one count per detent on the NeoRotary 4 (affects whether `max_events_per_poll` or a `steps_per_event` is needed).
3. Whether `ApertarCore` runs as `pi` (template says scripts run "as pi" (`App:4376`); README says "the Core service user" (`README.md:177`)); the unit file is not in the Core tree.
4. Whether GPIO line requests on 2/3 with I2C1 enabled fail with EBUSY on the Pi 5 kernel in use (needs the Pi).
5. Whether the PCF8574 sharing hazards in §2.14 show up in practice (needs a PCF with a button, the trigger and the LED on one chip).
6. The UI repo's `GyroConfigBridge` writer details and when `Ina219Bridge` and `WifiBridge` read the file were not traced line by line.
