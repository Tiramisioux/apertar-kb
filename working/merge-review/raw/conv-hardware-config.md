# C4 conventions: hardware inputs, outputs, configuration files (upstream 1.6.0)

Scope: how the original developer builds hardware I/O and `apertar-hardware.conf`. Read from the
`*-upstream` worktrees only. All refs `@upstream-1.6.0` (Core `35dbe67`, UI `43888e5`). `Core/` =
`/home/user/wt/core-upstream/`, `UI/` = `/home/user/wt/ui-upstream/`, `App` = `Core/src/ApertarCoreApp.cpp`.
The upstream worktree is one squashed commit ("1.6.0 Release"), so file history cannot date the two code styles
named below. All claims **confirmed** (read in code) unless labelled otherwise.

## 1. Inventory

| Class / place | Kind | Section(s) it parses | Thread | Ref |
| --- | --- | --- | --- | --- |
| `Pcf8574Input` | I2C button expander, 8 pins | `[pcf8574]`, `[pcf8574_buttons]` | own poll thread | `Core/src/hardware/Pcf8574Input.cpp:318-390`, `:470-527` |
| `GpioInput` | Pi GPIO buttons + quadrature encoders (char-dev v2 ioctl) | `[gpio_buttons]`/`[gpio]`/`[grove_digital]`/`[grove_buttons]`, `[gpio_encoders]`/`[grove_encoders]` | own poll thread | `Core/src/hardware/GpioInput.cpp:373-503`, `:620-744` |
| `NeoRotary4Input` | Adafruit seesaw quad encoder (I2C) | `[neorotary4]`/`[neo_rotary4]`/`[neo_rotary_4]` | own poll thread | `Core/src/hardware/NeoRotary4Input.cpp:355-444`, `:624-715` |
| `GroveAnalogInput` | Grove Base HAT ADC (I2C), potentiometers | `[grove_analog]`/`[grove_adc]`/`[analog_controls]` | own poll thread | `Core/src/hardware/GroveAnalogInput.cpp:260-350` |
| `StandbyPowerButtonInput` + `PowerButtonGesture.hpp` | Pi power key via evdev (`pwr_button`) | none (no config) | own thread, `poll()` + eventfd | `Core/src/hardware/StandbyPowerButtonInput.cpp:12-76` |
| `TriggerOutput` | GPIO or PCF pin pulse (hot shoe, flash) | `[trigger_output]`/`[trigger]`/`[capture_trigger]`/`[hotshoe]`, reads `[pcf8574]` bus/address | worker thread + condvar | `Core/src/hardware/TriggerOutput.cpp:250-360`, `:362-427` |
| `RecordingIndicatorOutput` | tally LED on GPIO or PCF pin | `[recording_indicator]` + 4 aliases; also scans `[pcf8574]` and `[gpio*]` for `recindicatorled` | timer thread | `Core/src/hardware/RecordingIndicatorOutput.cpp:247-399`, `:401-466` |
| `HardwareScriptRunner` | runs user Bash scripts | `[run_script]` (exact line match) | worker thread | `Core/src/hardware/HardwareScriptRunner.cpp:38-96`, `:200-258` |
| `Mpu6050RecordingSession` | IMU (4 drivers), gyro log per clip, calibration | `[imu]`, `[gyro]`, `[mpu6050]`/`[bmi160]`/`[bmi270]`/`[icm42688p]` | per-recording thread | `Core/src/hardware/Mpu6050RecordingSession.cpp:851-1030` |
| `ButtonActionList.hpp` | shared header-only: action token, list split (max 6), script slot | n/a | n/a | `Core/src/hardware/ButtonActionList.hpp:14-119` |
| INA219 (Core) | battery monitor, free functions in `App` | `[ina219]` | none: read on demand, config `static const` | `App:4450-4500`, `:4602` |
| NVMe / CFE watcher (Core) | embedded Python | `[cfexpress_hat]`, `[storage]` | subprocess | `App:3397-3602` |
| `DisplayConfigBridge` (UI) | `[display]` + first-run template writer | `[display]` | UI start | `UI/src/DisplayConfigBridge.cpp:41-286`, `:575-654` |
| `Ina219Bridge` (UI) | battery monitor (second, independent reader of the same chip) | `[ina219]` | QTimer 1 s after a 5 s delay | `UI/src/Ina219Bridge.cpp:449-530` |
| `GyroConfigBridge` (UI) | IMU settings page, live probe, writes the file | `[imu]` + driver section | UI | `UI/src/GyroConfigBridge.cpp:338-388`, `:1577` |
| `CfeAutomounter` (UI repo, own binary) | CFexpress hat automount daemon | `[cfexpress_hat]`, `[storage]` | daemon | `UI/src/CfeAutomounter.cpp:104-191` |

The `config/` directory holds no hardware template: only `config/apertar-core-capture-priority.conf`, a systemd
drop-in (`LimitNICE=-5`). Every hardware-config template lives in a C++ string (section 6).

## 2. File format and file selection

- INI-like text, `[section]`, `key=value`, `#`/`;` comment lines. There is no shared parser. Every class has its
  own `loadConfig()` that loops over lines (`Pcf8574Input.cpp:318`, `GpioInput.cpp:373`, `NeoRotary4Input.cpp:355`,
  `GroveAnalogInput.cpp:~250`, `TriggerOutput.cpp:250`, `RecordingIndicatorOutput.cpp:247`,
  `Mpu6050RecordingSession.cpp:851`, `HardwareScriptRunner.cpp:38`, `App:4450`).
- The UI parses the same file with `QSettings(path, QSettings::IniFormat)` (`UI/src/DisplayConfigBridge.cpp:595-596`,
  `UI/src/Ina219Bridge.cpp:509-510`): a second parser family with other comment and quoting rules.
- Candidate list `$APERTAR_HARDWARE_CONFIG` -> `/home/pi/apertar-hardware.conf` -> `/boot/firmware/...` -> `/boot/...`.
  It is a function copied into every file, not shared: C++ copies at `GpioInput.cpp:60`, `Pcf8574Input.cpp:60`,
  `NeoRotary4Input.cpp:73`, `GroveAnalogInput.cpp:57`, `TriggerOutput.cpp:73`, `RecordingIndicatorOutput.cpp:70`,
  `Mpu6050RecordingSession.cpp:191`, `App:4251`. More copies: Python `App:3397`, Qt `UI/src/DisplayConfigBridge.cpp:25`,
  `UI/src/Ina219Bridge.cpp:51`, std C++ `UI/src/CfeAutomounter.cpp:114`. That is 12 copies, all with the same order.
- Writes always go to the "editable" path, env or `/home/pi/...`, never `/boot` (`App:4271-4276`;
  `Mpu6050RecordingSession.cpp:1297-1300` falls back to `defaultHardwareConfigPath()`).
- Two selection rules (KB `architecture/config.md` 2.1, re-checked): input classes with a `configured` flag keep
  looking at the next candidate while the section is missing (`GpioInput.cpp:498-499`: `if (config.configured) return
  config;`, same in `Pcf8574Input.cpp:385-386`). Outputs, INA219 and the IMU use the first file that exists
  (`TriggerOutput.cpp:334` sets `configPath` before the loop body and returns unconditionally at `:425`; `App:4497`).

## 3. Per-class parser shape (the template every input/output follows)

Every "old-style" hardware class has the same skeleton. It is copied from class to class, not abstracted:

| Element | Shape | Evidence (two or more) |
| --- | --- | --- |
| File-local helpers in an anonymous namespace | `trimAscii`, `lowerAscii`, `normalizeToken` (`-`, space, `.` -> `_`), `defaultHardwareConfigPath`, `hardwareConfigCandidatePaths`, `parseConfigInteger` (`strtol` base 0, so `0x20` works), `parseConfigBool` | `GpioInput.cpp:27-106`, `Pcf8574Input.cpp:27-106`, `NeoRotary4Input.cpp:40-119`, `TriggerOutput.cpp:~30-170` |
| `struct Config` in the header with in-class defaults, plus `configured`, `enabled`, `configPath` | defaults live in the header, not in the parser | `GpioInput.hpp:45-57`, `Pcf8574Input.hpp:28-38`, `TriggerOutput.hpp:40-55`, `GroveAnalogInput.hpp:52-62` |
| `static Config loadConfig()` | parsed fresh in `start()` | `GpioInput.cpp:330-333`, `Pcf8574Input.cpp:273-276`, `TriggerOutput.cpp:362-366` |
| Public API `start()` / `stop()` / `enabled()` / `configPath()` / `lastError()` | identical on all inputs and outputs | `GpioInput.hpp:18-25`, `Pcf8574Input.hpp:17-24`, `GroveAnalogInput.hpp:36-43`, `TriggerOutput.hpp:26-32` |
| Callback injected through the constructor | `std::function<void(const std::string &)>` (action), optional second callback for rotation | `GpioInput.hpp:15-17`, `App:6785-6792` |
| Key aliases in a flat `if / else if` chain | `key == "bus" \|\| key == "channel" \|\| key == "i2c_bus"` | `Pcf8574Input.cpp:366`, `GroveAnalogInput.cpp:297`, `App:4482` |
| Values clamped with `std::clamp` silently, bad values ignored (default kept) | no error for out-of-range or unparsable values | `GpioInput.cpp:441-445`, `Pcf8574Input.cpp:372-377`, `TriggerOutput.cpp:334-336` |
| Section aliases | 2 to 5 names per section, normalised with `normalizeToken` | `GpioInput.cpp:405-413`, `TriggerOutput.cpp:276-279`, `RecordingIndicatorOutput.cpp:273-277` |
| "Section present = enabled" for I2C inputs, "explicit enabled=true" for GPIO and outputs | inconsistent on purpose or by accident; documented by the templates writing `enabled=false` | present=enabled: `Pcf8574Input.cpp:346-350`, `NeoRotary4Input.cpp:385-389`, `GroveAnalogInput.cpp:278-282`. Explicit: `GpioInput.cpp:426-430` + `:482-496`, `TriggerOutput.hpp:42`, `RecordingIndicatorOutput.hpp:36-49` |

Comment stripping differs by class (KB 2.3): inputs strip from the first `#`/`;` anywhere (`GpioInput.cpp:394-396`,
`Pcf8574Input.cpp:338-340`); outputs strip only when the `#`/`;` follows whitespace (`TriggerOutput.cpp:56-66`,
`stripInlineComment`); INA219 does not strip integers (`App:4486-4490`).

A second, newer and denser style exists in the same directory: `ButtonActionList.hpp`, `HardwareScriptRunner.cpp`,
`StandbyPowerButtonInput.cpp`, `PowerButtonGesture.hpp`. It has one-line `if` bodies, braces on one line, exceptions
(`throw std::runtime_error`, `HardwareScriptRunner.cpp:41-96`), and no `lastError()` / `configPath()`
(`StandbyPowerButtonInput.hpp:6-18`). Which one is "current" cannot be dated (single squashed commit). **Probable**:
the dense style is the later one, because it covers the 1.6.0 features (script slots, power button gesture) named in
the README (`Core/README.md:167-177`).

## 4. GPIO chip and I2C keys

| Topic | Rule | Evidence |
| --- | --- | --- |
| Chip key | `chip` with aliases `gpiochip`, `gpio_chip`, value a device path or `auto`; empty value = `auto` | `GpioInput.cpp:431-432`; `TriggerOutput.cpp:311-312` + `gpioChipPathIsAuto` `:195-199`; `RecordingIndicatorOutput.cpp:318`, `:345` |
| `auto` | scan `/dev/gpiochip0..9`, score by chip info: `rp1` +100, `pinctrl_bcm`/`bcm2711`/`bcm2835` +90, `raspberrypi_exp` -50, >=28 lines +10; try in score order, keep the last error | `GpioInput.cpp:238-262` + `:487-520`; `TriggerOutput.cpp:201-228` + `:~547-575`. Function `gpioChipScore` copied, not shared |
| Line numbering | BCM line offset on the chosen chip, keys `dN`, `gpioN`, `pinN`, `bcmN`, `grove_dN`, N 0-63 | `GpioInput.cpp:209-236` |
| Bus | integer N -> `/dev/i2c-N`, key `bus` (aliases `channel`, `i2c_bus`), 0-255 | `Pcf8574Input.cpp:256-259`, `:366-368`; `App:4482-4484`; `UI/src/CfeAutomounter.cpp:167` |
| Address | `address` (alias `addr`), decimal or hex, 0x03-0x77 | `Pcf8574Input.cpp:369-371`; `App:4485-4487`; `UI/src/Ina219Bridge.cpp:519-526` |
| I2C access | raw `open("/dev/i2c-N")` + `ioctl(I2C_SLAVE)` + `read`/`write`; no libi2c, no libgpiod | `Pcf8574Input.cpp:392-424`; `App:4606-4616`; GPIO uses `linux/gpio.h` v2 ioctls `GpioInput.cpp:530-570` |
| Per-device default bus | differs per device: PCF 1, NeoRotary4 1, Grove 1, INA219 4, CFE hat 10, IMU per driver section | `Pcf8574Input.hpp:31`, `NeoRotary4Input.hpp:39`, `GroveAnalogInput.hpp:55`, `App:4242`, `UI/src/CfeAutomounter.cpp:38` |
| Cross-section inheritance | trigger and LED copy `bus`/`address` from `[pcf8574]` when it comes first in the file | `TriggerOutput.cpp:289-298`; `RecordingIndicatorOutput.cpp:293-303` |

## 5. Actions: definition, normalisation, dispatch

### 5.1 Pipeline

1. Config value -> `normalizeAction(value)` in the input class = `hardware::normalizeButtonMapping(value,
   normalizeSingleAction)` (`GpioInput.cpp:203-206`). It splits on `,`, at most 6 (`ButtonActionList.hpp:14`, `:84`),
   lowercases, maps `ev-1` -> `evm1` (`:44-50`), drops `none`/`off`/`disabled`, refuses a list containing the LED
   output name (`:94-98`), deduplicates, and joins back to a comma string. Errors print
   `Hardware input mapping ignored: ...` to stderr and drop the mapping (`ButtonActionList.hpp:114-115`).
2. `normalizeSingleAction` maps aliases to a canonical name (`photo`, `capture`, `iso_up`, ...) and passes unknown
   tokens through unchanged (`GpioInput.cpp:202`: `return action;`). So `iso200`, `wb5000`, `fps24`,
   `resolution4056x2280`, `shutter1/48` are not in any list: the handler parses them.
3. Poll thread fires the callback with the joined string. Buttons use `handleHardwareInputAction(action)`, rotations
   use `handleHardwareInputAction(action, false)` (`App:6785-6792`).
4. `handleHardwareInputAction` (`App:8630-8658`) re-splits with an identity normaliser, takes
   `hardwareInputSequenceMutex_` so one button's sequence is not interleaved with another input's (comment at `:8640`),
   wakes from Standby on a button press and swallows the action (`:8642-8650`), ignores rotations in Standby, skips
   `standby` from a rotation (`:8654`), stops the sequence when Standby is entered (`:8656`).
5. `handleSingleHardwareInputAction` (`App:8660-8955`) is one flat `if (action == ...)` chain. Almost every branch
   builds a `ControlCommand` and runs it through `dispatchHardwareInputCommand` (`App:8458-8466`) =
   `handleCommand` with `id=-1` under `hardwareActionMutex_`; a failed reply is printed to stderr. So a hardware
   button is the same as a socket command; there is no second path to the camera.
6. UI-only actions (`zoom_toggle`, `settings`, `clip_browser`, `quick_menu`) are broadcast as
   `{"event":"hardware_action","action":"..."}` (`App:8667`, `:8949-8951`) and handled in
   `UI/qml/Main.qml:288-330` `onHardwareActionTriggered`. Monitoring toggles do both: command + event
   (`toggleSharedUiBoolAction`, `App:8468-8478`).
7. Unknown name: `Hardware input action ignored: unknown action '<x>'.` (`App:8954`). No startup validation of names.

### 5.2 How many copies of the action list

| Copy | What | Ref |
| --- | --- | --- |
| 1-3 | `normalizeSingleAction` alias table, byte-identical except line wrapping (diffed) | `GpioInput.cpp:108-200`, `Pcf8574Input.cpp:140-242`, `NeoRotary4Input.cpp:121-215` |
| 4 | LED-output alias list `isOutputAction` | `ButtonActionList.hpp:55-60` |
| 5 | LED-output alias list again, inside each `normalizeSingleAction` (copies 1-3) | `GpioInput.cpp:113-117` |
| 6 | LED-output alias list `isRecordingIndicatorAction` | `RecordingIndicatorOutput.cpp:118-128` |
| 7 | Canonical handler chain (the real list of what works) | `App:8660-8955` |
| 8-10 | Human list in comments of three templates | `App:4355-4359`, `UI/src/DisplayConfigBridge.cpp:76-88`, `UI/src/Ina219Bridge.cpp:95-107` |
| 11 | Script action slots `scriptActionSlot`, shared, used by normalisers and handler | `ButtonActionList.hpp:17-28`, `App:8662` |
| analog | target alias table, twice: `GroveAnalogInput.cpp:125-145` `normalizeTarget` and `App:8410-8432` `normalizeHardwareAnalogTarget` | |

The developer started sharing (`ButtonActionList.hpp`, included by all four input files and `App:5`) but kept the
three alias tables. Strength: **always** (all three button inputs carry their own copy; searched with
`grep -n normalizeSingleAction src/hardware/*.cpp`).

## 6. Templates and where they disagree

Three hand-maintained templates, none in a file:

| Template | Used when | Ref |
| --- | --- | --- |
| Core `defaultHardwareConfigTemplate()` | WebUI `GET /api/config` when the editable file does not exist (shown, not written) | `App:4291-4404`, `:5297` |
| UI `ensureDefaultHardwareConfigFile()` in `DisplayConfigBridge` | UI start, writes `/home/pi/apertar-hardware.conf` if missing (ignores env) | `UI/src/DisplayConfigBridge.cpp:41-286`, `:587` |
| UI `ensureDefaultHardwareConfigFile()` in `Ina219Bridge` | 5 s after UI start, same file, same condition (normally a no-op because the display copy ran first) | `UI/src/Ina219Bridge.cpp:69-330`, `:497` |

| Disagreement | Core template | UI templates | Code default |
| --- | --- | --- | --- |
| `[pcf8574] bus` | 10 (`App:4363`) | 1 (`DisplayConfigBridge.cpp:88`) | 1 (`Pcf8574Input.hpp:31`) |
| `[trigger_output] open_drain` | true (`App:4382`) | true | **false** (`TriggerOutput.hpp:47`) |
| `[imu]` keys | `bus`, `address`, `sample_rate_hz`, `gyro_range_dps`, `accel_range_g`, `orientation` in `[imu]` (`App:4343-4352`) | in driver sections | `[imu]` reads only `driver`, `sync_mode`, `enabled`, `sync_offset_ms` (`Mpu6050RecordingSession.cpp:939-955`): the Core template's IMU keys are dead |
| `[imu] enabled` | false | (UI template) | true (`Mpu6050RecordingSession.hpp:96`) |
| `controls_mode=Light`, `rotation=0` | present (`App:4326-4327`) | absent | `controls_mode` parsed by nobody |
| Sections | no `[network]`, `[neorotary4]`, `[gpio_buttons]`, `[gpio_encoders]`, `[grove_analog]`; has `[gpio]` | display copy has all; INA219 copy lacks `[network]`, `[run_script]`, `zoom_toggle_factor` (diff) | |
| `[gpio_encoders]` in UI template | | `poll_ms=3`, `debounce_ms=40` after `[gpio_buttons]` `poll_ms=12`, `debounce_ms=60` | shared keys, later section wins (`GpioInput.cpp:431-445`): enabling buttons alone still gets 3/40 |
| Indentation | spaces | mixed tab + spaces in the stream chain (`DisplayConfigBridge.cpp:70-199`) | |

Rule observed: every new section or key is added to the templates by hand, and the templates drift. Strength:
**always** that there are three; **usually** that they agree (exceptions above).

## 7. When config is read, who writes the file

| Reader | When | Change needs | Ref |
| --- | --- | --- | --- |
| Core inputs and outputs | `ApertarCoreApp::start()` once; order trigger, PCF, NeoRotary4, GPIO, power button (not in simulate mode), Grove, LED | restart `apertar-core` | `App:6881-6898` |
| Core INA219 | first read, then `static const` | restart Core | `App:4602` |
| Core IMU | every recording / IMU command / calibration | none | `Mpu6050RecordingSession.cpp:1040`, `:1176`, `:1297` |
| Core scripts | every script action (`request(editableHardwareConfigPath(), slot)`) | none | `App:8663`; `HardwareScriptRunner.cpp:38` |
| UI `[display]` | UI start | restart UI | `UI/src/DisplayConfigBridge.cpp:575-654` |
| UI `[ina219]` | 5 s after UI start | restart UI | `UI/src/Ina219Bridge.cpp:449-460`, `:490-530` |
| Automounter | daemon start | restart daemon | `UI/src/CfeAutomounter.cpp:131-191` |

The WebUI says it in its own words: "Hardware, input, display, and sensor changes may need ApertarCore or the UI
restarted before they fully apply." (`Core/src/web/WebControlPage.cpp:3868`). No file watcher, no reload command,
no hot restart of input groups exists upstream (searched: `grep -n "inotify\|last_write_time" src/hardware/*.cpp`
finds nothing; `App` inputs are only touched at `:6886-6891` and `:6914-6918`).

Writers:

| Writer | How | Ref |
| --- | --- | --- |
| WebUI Config pane, `POST /api/config` | whole-file replace from a textarea, no validation of content; checks non-empty, <=256 KiB, no NUL; `.bak` copy, write `.tmp`, `rename` | `App:5323-5385`, `:64`, `:7175-7193`; JS `WebControlPage.cpp:10330-10359` |
| WebUI Config pane, `GET /api/config` | JSON `ok, path, display_path, exists, size_bytes, size_text, modified_text, text` | `App:5290-5320`, `:7168-7173` |
| Core IMU commands (`set_imu_driver`, `set_imu_orientation`, sync offset, level reference, `calibrate_gyro`) | one-key line editor that keeps comments and order (`writeHardwareConfigValue`, `updateImuBiasConfig`), `.tmp` + `rename` | `Mpu6050RecordingSession.cpp:604-713`, `:715-849`; commands `App:9646-9725` |
| UI gyro page | its own line editor with `QSaveFile` | `UI/src/GyroConfigBridge.cpp:362-388`, `:1577` |
| UI first-run | template if missing | `UI/src/DisplayConfigBridge.cpp:41-58` |

Note the duplication: Core and UI both write `[imu]` keys with separate code, and Core and UI both open the INA219
and rewrite its config and calibration registers (`App:4618-4626`, `UI/src/Ina219Bridge.cpp`). The original developer
accepted two processes touching the same file and chip.

## 8. Poll threads, debounce, errors

| Topic | Rule | Evidence |
| --- | --- | --- |
| One `std::thread` per device, `std::atomic<bool> running_`, `stop()` = exchange + join | | `GpioInput.cpp:342-347`, `Pcf8574Input.cpp:294-300`, `NeoRotary4Input.cpp:331-337` |
| Polling with `sleep_for(pollMs)`, no interrupts / edge events (except power key: evdev `poll()`) | | `GpioInput.cpp:740`, `Pcf8574Input.cpp:523`, `NeoRotary4Input.cpp:711`, `GroveAnalogInput.cpp:480`; `StandbyPowerButtonInput.cpp:54` |
| Debounce: observed vs stable state, emit on stable press edge after `debounceMs` (default 60) | same algorithm, copied | `GpioInput.cpp:691-710`, `Pcf8574Input.cpp:500-520`, `NeoRotary4Input.cpp:~690-708` |
| Device open retried forever: 1000 ms after open failure, 250 ms after read failure | | `GpioInput.cpp:643-649`, `:684-688`; `Pcf8574Input.cpp:479-494`; `NeoRotary4Input.cpp:634-676`; `GroveAnalogInput.cpp:449` |
| `setLastError`: store under mutex, print to stderr only when the text changes, prefix `"<Device> input: "` | | `GpioInput.cpp:611-619`, `Pcf8574Input.cpp:460-468`, `NeoRotary4Input.cpp:614-622` |
| `lastError()` of inputs is never read by `App`; only trigger and LED `lastError()` are printed after `start()` | errors reach the operator only through `journalctl` | `App:6881-6896`; `grep -n "Input_\.lastError" App` = none |
| Start log line: `"<Device> input enabled: ... config=<path>"` or `"... has no ... ; input disabled."` | | `GpioInput.cpp:336-340`, `Pcf8574Input.cpp:279-290`, `NeoRotary4Input.cpp:316-327` |
| Hardware status is not in the state JSON or WebUI | | `grep -n "\"pcf\|gpio_input\|neorotary" App` finds only template text |

## 9. Intent (product decisions the code encodes)

| Intent | Evidence |
| --- | --- |
| A hardware button is a remote finger on the same commands as the touch UI and WebUI; it never bypasses `handleCommand` | `App:8458-8466`, every branch of `App:8660-8955` |
| Media eject is refused during recording or timelapse; gyro calibration too | `App:8892-8895`; `App:9706-9707` |
| Standby: any button only wakes and the press is consumed; rotation cannot wake or sleep | `App:8642-8656`; `UI/README.md:197` ("The first physical wake press is consumed") |
| One button can run up to six actions; toggles flip independently | `ButtonActionList.hpp:14`; `Core/README.md:167-175` |
| User scripts run as `pi`, no sudo, own process group, stdin `/dev/null`, inherited fds closed, killed on shutdown | `HardwareScriptRunner.cpp:206-241`; `Core/README.md:177` |
| Wiring safety stated in templates: optocoupler for hot shoe; LED wiring `3.3V -> resistor -> LED -> pin` | `App:4374`, `:4391` |
| Boards: Pi 5 / CM5 first (RP1 scored highest), Pi 4/3 BCM still supported; no board key, auto-detect | `GpioInput.cpp:247-253`; `Core/README.md:64-70` |
| Reference rig (probable, from defaults): INA219 on bus 4 with a 4S V-mount battery (SmallRig VB50 comment), CFexpress hat on bus 10, PCF8574 expander, Grove Base HAT, Adafruit NeoRotary4 | `UI/src/Ina219Bridge.cpp:40-46`; `App:4300-4313`; `UI/src/DisplayConfigBridge.cpp:131-198` |
| Operator-configurable: which device, bus, address, chip, pin-to-action map, polarity, pull, poll and debounce, trigger events and pulse length, LED pin, scripts, IMU driver and offsets | sections in section 6 |
| Fixed in code: action names and their behaviour, step lists (`pcfIsoOptions`, `pcfShutterAngleOptions`, ...), INA219 calibration and battery curve, chip scoring, max 6 actions / 5 scripts | `App:8770-8830`; `App:4510-4590`; `ButtonActionList.hpp:14-15` |
| Lenient config: bad values fall back to defaults silently; only mapping errors and unknown actions are logged | section 3; `App:8954` |
| One hand-edited file is the operator's surface for hardware; the WebUI offers a raw text editor, not forms | `WebControlPage.cpp:3840-3870` |

## 10. Rules

See the structured summary for the rule list with strengths. Short form:

- S1 always: each hardware device is one class in `src/hardware/`, one `.hpp` + `.cpp`, owned by value as a member
  of `ApertarCoreApp` (`ApertarCoreApp.hpp:114-121`), started in `start()` and stopped in `stop()`.
- S2 always: each class parses its own section(s) with its own copy of the helpers; no shared INI parser.
- S3 always: hardware actions go through `handleHardwareInputAction` -> `handleSingleHardwareInputAction` ->
  `dispatchHardwareInputCommand` -> `handleCommand`.
- S4 usually: outputs follow camera events from `publishEvent` via `handleTriggerEvent` string matching
  (`App:10825`, `:10854-10889`), not direct calls from recording code.
- I1 always: key and section aliases in flat `||` chains; tokens normalised with `normalizeToken`.
- I2 usually: defaults in header `Config` structs; silent `std::clamp`.
- I3 always: errors to `std::cerr`, one line, device prefix, de-duplicated by `setLastError`.
- N1 always: config read once at start; changes need a service restart; the UI says so.
- N2 always: nothing that changes or interrupts a take runs from hardware without a guard.

## 11. Recipes

### R1. Add an input device class the Apertar way

1. `Core/src/hardware/MyInput.hpp`: copy `Pcf8574Input.hpp:1-57` shape: `ActionCallback` ctor, `start/stop/enabled/
   configPath/lastError`, private `struct Config` with defaults, `static Config loadConfig()`, `run()`,
   `setLastError()`, `std::atomic<bool> running_`, `std::thread thread_`, `stateMutex_`, `lastError_`.
2. `Core/src/hardware/MyInput.cpp`: anonymous-namespace helpers copied from `Pcf8574Input.cpp:27-106`; own
   `normalizeSingleAction` copied from `Pcf8574Input.cpp:140-247` and wrapped with
   `hardware::normalizeButtonMapping` (`ButtonActionList.hpp:110-116`); `loadConfig()` per `Pcf8574Input.cpp:318-390`
   with section aliases; debounce loop per `Pcf8574Input.cpp:470-527`; log `"MyDevice input enabled: ... config=..."`.
3. `Core/CMakeLists.txt:83-91`: add the `.cpp` to `add_executable(apertar-core ...)`.
4. `Core/src/ApertarCoreApp.hpp:5-12` include, `:114-121` member.
5. `App:6785-6792` construct with `[this](const std::string &a) { handleHardwareInputAction(a); }` (and `, false` for
   rotation).
6. `App:6886-6891` `myInput_.start();`, `App:6914-6918` `myInput_.stop();`.
7. Templates: add a commented `[my_device]` with `enabled=false` to `App:4291-4404`,
   `UI/src/DisplayConfigBridge.cpp:41-286`, `UI/src/Ina219Bridge.cpp:69-330`.
8. README hardware paragraph if it is operator-facing (`Core/README.md:157-177`).

### R2. Add an action

1. Handler branch in `App:8660-8955` before the `unknown action` line (`App:8954`): build the command with the
   `dispatch(...)` lambda (`App:8671-8677`) or use `toggleSharedUiBoolAction` (`App:8468-8478`) for a UI.conf toggle.
   Add a recording guard if the action could disturb a take (pattern `App:8892-8895`).
2. If the action exists only in the UI, publish `hardware_action` (`App:8949-8951`) and handle it in
   `UI/qml/Main.qml:288-330`.
3. Aliases only if needed: same new lines in all three `normalizeSingleAction` copies (`GpioInput.cpp:108`,
   `Pcf8574Input.cpp:140`, `NeoRotary4Input.cpp:121`). Parametric names (`iso200`) need no alias: they pass through.
4. Add the name to the comment lists in the three templates (`App:4355-4359`, `DisplayConfigBridge.cpp:76-88`,
   `Ina219Bridge.cpp:95-107`).
5. If the action needs a new socket command, that command also goes into the flat `"commands":[...]` list that
   Core returns (`App:9216`), like every other command.

### R3. Add a config key

1. Owner: the class that owns the section (Core `src/hardware/*`, `App` for `[ina219]`, UI bridge for `[display]`,
   `[network]`, automounter for `[cfexpress_hat]`/`[storage]`).
2. Field with default in the header `Config` (e.g. `Pcf8574Input.hpp:28-38`).
3. `else if (key == "my_key" || key == "alias")` in that class's `loadConfig()` with `parseConfigInteger` /
   `parseConfigBool` and `std::clamp` (pattern `Pcf8574Input.cpp:363-381`).
4. If the key is shared with another process, add it to that process's parser too (INA219: `App:4450` and
   `UI/src/Ina219Bridge.cpp:490-530`).
5. Add the key with its default to the three templates (section 6).
6. Document "restart Core / UI after editing" (it is read once at start).

## Challenge

Challenger pass, read in `*-upstream` worktrees only. All refs `@upstream-1.6.0`. `App` = `Core/src/ApertarCoreApp.cpp`,
`CC` = `Core/src/camera/CameraController.cpp`. Search commands named per row.

| Rule | Verdict | Counter-example / reason |
| --- | --- | --- |
| HW-S1 | weaken to usually; split | Holds for the five inputs (ctor lambdas `App:6785-6792`, `start()` `App:6886-6891`). Outputs and the script runner are default-constructed, no lambda (`App:6781-6792` lists no `triggerOutput_`/`recordingIndicatorOutput_`/`hardwareScriptRunner_`). `hardwareScriptRunner_` has no `start()`, only `stop()` (`App:6919`), works on demand via `request()` (`App:8663`). The IMU is not an `ApertarCoreApp` member: `Mpu6050RecordingSession gyroRecorder_` lives in `CC:7517`, plus static functions called from `App:9652-9712`. INA219 is no class at all: free functions and a struct in `App:4239`, `:4450`, `:4602`. `standbyPowerButton_.start()` is skipped in simulate mode (`App:6889-6890`). |
| HW-S2 | holds for "no shared parser" (always); weaken "static loadConfig + copied helpers" to usually | Helper copies confirmed in 7 files (`grep -n "^std::string trimAscii" src/hardware/*.cpp`: Gpio, Grove, Mpu6050, NeoRotary4, Pcf, RecIndicator, Trigger). Exceptions: `HardwareScriptRunner.cpp:30-96` own `trim()` + free `readScriptPaths()` that throws, exact `[run_script]` match, no `normalizeToken`, no candidate list (path passed in from `App:8663`). INA219 parser is in `App:4450-4500` using `App`'s own helpers. UI side uses `QSettings` (`UI/src/DisplayConfigBridge.cpp:595`, `UI/src/WifiBridge.cpp:24`). |
| HW-S3 | weaken the fixed chain to usually; the end point holds always | Entry points differ: analog enters at `handleHardwareAnalogInput` (`App:8480`) and power key at `handlePowerButtonPress` (`App:8603-8623`), neither via `handleHardwareInputAction`. Script slots go to `hardwareScriptRunner_.request` (`App:8662-8664`) and UI-only actions publish `hardware_action` events (`App:8666-8668`, `:8949-8951`) without `handleCommand`. Holds always: no hardware path mutates `camera_` directly; the handler only reads state (`camera_.isRecording()`, `.settings()`, `.timelapseActive()`), every change ends in `dispatchHardwareInputCommand` (`App:8458-8466`). Searched `awk NR 8480-8960 | grep camera_\.`: getters only. |
| HW-S4 | holds; raise to always | Every output call is in `handleTriggerEvent` (`App:10854-10889`) except the seed after `start()` (`App:6897-6898`), which syncs initial state and is not a recording-code call. `capture_photo` calls `handleTriggerEvent(event)` itself before broadcast (`App:10729-10732`): still the event path. Searched `grep -n "recordingIndicatorOutput_\.\|triggerOutput_\." App`. |
| HW-S5 | holds (always) | `config/` holds only `apertar-core-capture-priority.conf`. Template ranges are wider than stated: `UI/src/DisplayConfigBridge.cpp:41-326`, `UI/src/Ina219Bridge.cpp:69-342`. |
| HW-S6 | holds (always) | Rough edge: on rename failure the writer removes the target and renames again (`Mpu6050RecordingSession.cpp:700-705`): not atomic on that path. No lock between Core and UI writers. |
| HW-I1 | holds for the shape (always); weaken the exact alias set to usually | Different alias sets: IMU `key == "bus" \|\| key == "bus_number"` (`Mpu6050RecordingSession.cpp:959`); trigger and LED own section use `bus`/`pcf_bus`, `address`/`pcf_address` (`TriggerOutput.cpp:320-323`, `RecordingIndicatorOutput.cpp:359-362`); trigger reading `[pcf8574]` accepts only `bus`/`address` (`TriggerOutput.cpp:290-293`). INA219 keys use `lowerAscii(trimAscii())`, not `normalizeToken` (`App:4482`), section `== "[ina219]"` with no alias (`App:4471`). `[run_script]` exact match, no normalisation (`HardwareScriptRunner.cpp:51`). |
| HW-I2 | holds (usually) | Exceptions: INA219 rejects out-of-range values instead of clamping (`App:4493-4498`); `HardwareScriptRunner` throws on bad keys/paths and logs them (`HardwareScriptRunner.cpp:58,67,84-87`); UI `WifiBridge.cpp:28-31` warns on invalid `hotspot_delay_seconds`. |
| HW-I3 | weaken to usually | Holds for the four inputs (`"<Device> input: "` via `setLastError`, `GpioInput.cpp:618`, `GroveAnalogInput.cpp:437`, `NeoRotary4Input.cpp:621`, `Pcf8574Input.cpp:467`). Outputs use prefix `"ApertarCore trigger output: "` / `"ApertarCore recording indicator LED: "` (`TriggerOutput.cpp:695`, `RecordingIndicatorOutput.cpp:748`) and log no "disabled" line themselves (`App:6881-6896` prints only on error). Script runner and IMU print `"ApertarCore run_script: "` / `"ApertarCore gyro ..."` with no `setLastError` dedup (`HardwareScriptRunner.cpp:130-255`, `Mpu6050RecordingSession.cpp:1164-2277`). Holds always: plain `std::cerr`, one line per event, a device prefix, no logging library (`grep -rln "spdlog\|syslog" src` = none in hardware). |
| HW-I4 | weaken to usually | Button and encoder inputs hold. Exceptions: power key is event-driven, evdev + `poll()` + `eventfd` stop (`StandbyPowerButtonInput.cpp:16`, `:51-56`); Grove analog has no debounce, uses a `deadband` on the raw value (`GroveAnalogInput.cpp:306-308`, `:473`); outputs use worker threads + condvar, not polling (`TriggerOutput.cpp:403`, `RecordingIndicatorOutput.cpp:438`). |
| HW-I5 | holds (always) | All three button inputs: `return action;` + `normalizeButtonMapping` (`GpioInput.cpp:201,206`, `Pcf8574Input.cpp:241,246`, `NeoRotary4Input.cpp:214,219`). Grove uses its own `normalizeTarget`, separate concept (targets, not actions). |
| HW-I6 | weaken to usually | C++ holds (Core and UI: `I2C_SLAVE` in 9 places incl. `UI/src/Ina219Bridge.cpp:563`, `UI/src/CfeAutomounter.cpp:459`; IMU also `I2C_RDWR` `Mpu6050RecordingSession.cpp:1886`; no gpiod/wiringPi/pigpio anywhere). Exception: the embedded Python CFexpress/NVMe watchers use `python3-smbus` and `configparser` (`App:3383-3387`, `:3571`; `UI/src/MediaStatusBridge.cpp:755`, `:940`). |
| HW-I7 | holds (always) | Three copies of `gpioChipScore`, one per GPIO user (`GpioInput.cpp:238`, `TriggerOutput.cpp:201`, `RecordingIndicatorOutput.cpp:198`); no other GPIO user in Core or UI (`grep -rln "gpiochip\|GPIO_V2"`: only templates otherwise). |
| HW-N1 | weaken to usually | IMU config is re-read on every recording, IMU command and calibration (`Mpu6050RecordingSession.cpp:1040`, `:1176`, `:1297`); `[run_script]` is re-read on every press (`App:8663`, `HardwareScriptRunner.cpp:38`). Read-once holds for input/output classes (`App:6881-6898`), Core INA219 (`App:4602`) and UI `[display]`/`[ina219]`. The WebUI note (`WebControlPage.cpp:3868`) says "may need", consistent with mixed behaviour. |
| HW-N2 | holds (always) with a corrected mechanism | Guards live mostly in the command layer, so hardware inherits them through S3: `App:9105-9107` media actions, `App:9541` capture mode, `App:9706` gyro calibration, `CC:7715` resolution, `CC:7745` FPS, `CC:7928` format. The hardware eject guard (`App:8892-8895`) duplicates `App:9105`. Note: a hardware button may stop a take on purpose (`capture`/`record_toggle` -> `record_stop`, `App:8855-8868`); the rule is "no side effect on media, calibration or recording parameters", not "no effect". |
| HW-N3 | holds (usually) | Non-wiring keys in the same file: `[network] hotspot_delay_seconds` (`UI/src/WifiBridge.cpp:27`), `[display]` (`UI/src/DisplayConfigBridge.cpp:575-654`), IMU orientation and sync offset written by commands (`App:9646-9690`). |
| HW-N4 | weaken to usually; "all disabled by default" is wrong | Core template `[ina219] enabled=true`, `[cfexpress_hat] enabled=true` (`App:4298-4305`); UI template `[ina219] enabled=true`, `[imu] enabled=true`, `[mpu6050] enabled=true` (`UI/src/DisplayConfigBridge.cpp:70-71`, `:199-209`) while Core template has `[imu] enabled=false` (`App:4343-4344`). Disabled by default: the control and output accessories (pcf8574, gpio, neorotary4, grove_analog, trigger_output, recording_indicator). Pi 5 first is confirmed by `Core/README.md:62-66` board table. |
| HW-N5 | holds (usually) | Both processes write INA219 config and calibration registers (`App:4622-4623`, `UI/src/Ina219Bridge.cpp:568`). No inter-process lock anywhere. |

### Missed rules

| Id | Kind | Rule | Strength | Evidence |
| --- | --- | --- | --- | --- |
| HW-S7 | structure | Put take-protection guards in the command handler or `CameraController` setter, not in the input path; hardware gets them by going through `handleCommand`. | always (searched `grep -n "isRecording()" App` beyond 8960 and `grep -n "while recording" CC`) | `App:9105-9107`; `App:9706-9707`; `CC:7715`, `:7745`, `:8285`, `:8320` |
| HW-S8 | structure | Keep `src/hardware/` free of app knowledge: hardware headers include only standard/Linux headers and each other; the app is reached only through injected callbacks. | always (`grep '#include "' src/hardware/*` finds only hardware headers) | `ApertarCoreApp.hpp:5-12` includes hardware, never the reverse; `GpioInput.hpp:15-17` callback types |
| HW-S9 | structure | Register every new hardware `.cpp` by name in `add_executable(apertar-core ...)`; there is no glob. | always (`grep GLOB CMakeLists.txt` = none) | `Core/CMakeLists.txt:83-91` |
| HW-S10 | structure | Write the hardware file only at the editable path (`$APERTAR_HARDWARE_CONFIG` or `/home/pi/apertar-hardware.conf`), never `/boot`; readers walk the candidate list env -> `/home/pi` -> `/boot/firmware` -> `/boot`, copied per file (13 copies incl. Python in `UI/src/MediaStatusBridge.cpp:765-781`). | usually: `UI/src/WifiBridge.cpp:21-23` reads only env or `/home/pi` | `App:4271-4276`; `Mpu6050RecordingSession.cpp:610`; `UI/src/DisplayConfigBridge.cpp:22`, `:52` |
| HW-S11 | structure | Operator preferences and toggles go to `UI.conf` (`QSettings("CinePi","UI")`), not to `apertar-hardware.conf`; hardware buttons change them through `set_*_enabled` commands. | usually: `[network]`, `[display]` exceptions (HW-N3) | `App:344-347` UI.conf path; `UI/src/WifiBridge.cpp:127`, `:252` hotspot SSID in UI.conf; `App:8468-8478` `toggleSharedUiBoolAction` |
| HW-N6 | intent | Do not surface hardware-input health in the state JSON, WebUI or UI; problems go to the journal only. IMU is the exception (`imuStatusBody`). | usually | `grep -n "Input_\.lastError" App` = none; `App:6881-6896` only to stderr; IMU status `App:9681`, `:132-133` |
| HW-N7 | intent | Be lenient with the operator's file: unknown sections/keys are ignored, bad values keep defaults; only mapping errors, unknown actions and script problems are logged. | usually: script runner throws (`HardwareScriptRunner.cpp:58-87`) | `GpioInput.cpp:441-445`; `App:4489-4498`; `App:8954`; `ButtonActionList.hpp:114-115` |

## Final rules

| Id | Kind | Rule | Strength | Evidence | A violation looks like |
| --- | --- | --- | --- | --- | --- |
| HW-S1 | structure | Put each input device in its own class pair `src/hardware/<Device>.{hpp,cpp}`, held by value in `ApertarCoreApp`, built with a callback lambda in the ctor, `start()` in `ApertarCoreApp::start()`, `stop()` in `stop()`; outputs are default-constructed members fed from `handleTriggerEvent`. | usually (IMU owned by `CameraController` `CC:7517`; INA219 free functions in `App:4450`; script runner on demand, no `start()`) | `ApertarCoreApp.hpp:114-121`; `App:6785-6792`; `App:6881-6898`; `App:6914-6921` | a device manager/registry, a heap-allocated plugin list, a device started from a command handler or from `CameraController` |
| HW-S2 | structure | Each class parses its own section(s) with its own file-local helpers (`trimAscii`, `normalizeToken`, `parseConfigInteger`, `parseConfigBool`, `hardwareConfigCandidatePaths`) in a `static loadConfig()`; no shared INI parser. | always for "no shared parser"; usually for the exact shape (`HardwareScriptRunner.cpp:30-96`, `App:4450`) | `GpioInput.cpp:27-106,373`; `Pcf8574Input.cpp:27-106,318`; `TriggerOutput.cpp:28-130,250` | a new `HardwareConfig` / INI library class all devices call; refactoring the copies away unasked |
| HW-S3 | structure | Every camera or setting change from hardware ends in `dispatchHardwareInputCommand` -> `handleCommand` (id -1); the hardware path only reads camera state. Buttons/encoders enter at `handleHardwareInputAction`, analog at `handleHardwareAnalogInput`, power key at `handlePowerButtonPress`. | always for the end point; usually for the entry chain (scripts -> runner, UI-only -> `hardware_action` event) | `App:8458-8466`; `App:8671-8677`; `App:8480-8495`; `App:8603-8623` | a hardware handler calling `camera_.setFps()` etc. directly, or a second command path |
| HW-S4 | structure | Drive outputs (tally LED, trigger pulse) only from published events in `handleTriggerEvent`; seed initial state once after `start()`. | always (searched all `triggerOutput_.` / `recordingIndicatorOutput_.` calls) | `App:10825`; `App:10854-10889`; `App:10729-10732`; `App:6897-6898` | `setRecordingActive()` or `pulse()` called inside recording start/stop code or `CameraController` |
| HW-S5 | structure | Keep `apertar-hardware.conf` templates as C++ strings (Core WebUI fallback + two UI first-run writers) and add new sections/keys to all three by hand; no template file in `config/`. | always | `App:4291-4404`; `UI/src/DisplayConfigBridge.cpp:41-326`; `UI/src/Ina219Bridge.cpp:69-342` | a new `config/apertar-hardware.conf.example` as source of truth, or a key added to only one template |
| HW-S6 | structure | Programmatic writes edit one key in place (keep comments and order) and replace via `.tmp` + `rename` / `QSaveFile`; the WebUI writes the whole raw text with a `.bak` backup. | always | `Mpu6050RecordingSession.cpp:604-713`; `UI/src/GyroConfigBridge.cpp:362-388`; `App:5323-5385` | regenerating the file from a struct (losing comments), writing in place without temp file |
| HW-S7 | structure | Put take-protection guards in the command handler or `CameraController` setter; inputs inherit them via S3. | always | `App:9105-9107`; `App:9706-9707`; `CC:7715`, `:7745`, `:8285` | a guard only in a hardware branch, leaving UI/WebUI/socket unprotected |
| HW-S8 | structure | Keep `src/hardware/` free of app knowledge: no includes of camera/app headers; reach the app only through injected callbacks. | always | `grep '#include "' src/hardware/*` = hardware headers only; `GpioInput.hpp:15-17`; `App:6785-6792` | a hardware class that includes `CameraController.hpp` or `ApertarCoreApp.hpp` |
| HW-S9 | structure | Register each new hardware `.cpp` by name in `add_executable(apertar-core ...)`. | always | `Core/CMakeLists.txt:83-91`; no `GLOB` in `CMakeLists.txt` | `file(GLOB ...)` or a separate static library for hardware |
| HW-S10 | structure | Write only to the editable path (env or `/home/pi/apertar-hardware.conf`); read via the copied candidate list env -> `/home/pi` -> `/boot/firmware` -> `/boot`. | usually (`UI/src/WifiBridge.cpp:21-23` env or `/home/pi` only) | `App:4251-4276`; `GpioInput.cpp:60`; `Mpu6050RecordingSession.cpp:610`; `UI/src/MediaStatusBridge.cpp:765-781` | writing to `/boot/...`, a new path order, or a new location (`/etc/apertar/`) |
| HW-S11 | structure | Operator preferences and toggles go to `UI.conf`; hardware buttons flip them through `set_*_enabled` commands; the hardware file holds wiring. | usually (`[network]`, `[display]`) | `App:344-347`; `UI/src/WifiBridge.cpp:127,252`; `App:8468-8478` | a new UI preference stored in `apertar-hardware.conf` |
| HW-I1 | idiom | Spell section and key aliases as flat `key == "a" \|\| key == "b"` chains after `normalizeToken`; common sets `bus/channel/i2c_bus`, `address/addr`, `chip/gpiochip/gpio_chip`. | always for the shape; usually for the set (IMU `bus_number`, trigger/LED `pcf_bus`/`pcf_address`, INA219 no `normalizeToken`, `[run_script]` exact) | `Pcf8574Input.cpp:366-371`; `GpioInput.cpp:431`; `TriggerOutput.cpp:276-279,311`; `Mpu6050RecordingSession.cpp:959` | a lookup table/map of aliases, a schema, or a case-sensitive key without aliases on an input |
| HW-I2 | idiom | Defaults as in-class initialisers of a private `struct Config` in the header; clamp parsed numbers with `std::clamp`; keep the default on unparsable input silently. | usually (INA219 range-rejects `App:4493-4498`; script runner throws) | `GpioInput.hpp:45-57`; `Pcf8574Input.hpp:28-38`; `GpioInput.cpp:441-445` | defaults in the parser body, validation errors thrown at start for a bad number |
| HW-I3 | idiom | Report hardware problems as one plain `std::cerr` line with a device prefix (`"<Device> input: "` deduped by `setLastError` for inputs; `"ApertarCore <device>: "` for outputs, IMU, scripts). | usually (prefix and dedup differ by class); always for plain `std::cerr` with prefix | `GpioInput.cpp:611-619`; `Pcf8574Input.cpp:460-468`; `TriggerOutput.cpp:695`; `HardwareScriptRunner.cpp:136` | a logging framework, `printf`, unprefixed messages, a log line per poll iteration |
| HW-I4 | idiom | Poll button/encoder inputs on a dedicated `std::thread` with `sleep_for(pollMs)`, retry open every 1000 ms and reads every 250 ms forever, debounce with the copied observed/stable state machine. | usually (power key evdev `poll()`; Grove deadband; outputs worker + condvar) | `GpioInput.cpp:643-649,684-710,740`; `Pcf8574Input.cpp:479-523`; `NeoRotary4Input.cpp:634-711` | an event loop/async framework, giving up after N failures, a shared debounce class |
| HW-I5 | idiom | Normalise action names per input with that file's `normalizeSingleAction` wrapped by `hardware::normalizeButtonMapping`; unknown tokens pass through; parametric names are parsed only in the handler. | always | `GpioInput.cpp:108-206`; `Pcf8574Input.cpp:140-246`; `NeoRotary4Input.cpp:121-219` | validating action names at config load, an action enum, parametric parsing in the input class |
| HW-I6 | idiom | In C++ talk to hardware through raw Linux interfaces (`/dev/i2c-N` + `ioctl(I2C_SLAVE/I2C_RDWR)`, GPIO char-dev v2 ioctls, evdev); no libgpiod, libi2c, wiringPi, pigpio. | usually (embedded Python watchers use `smbus`: `App:3387`, `UI/src/MediaStatusBridge.cpp:755`) | `Pcf8574Input.cpp:392-424`; `GpioInput.cpp:530-570`; `App:4606-4617`; `UI/src/Ina219Bridge.cpp:563` | `find_package(libgpiod)`, sysfs GPIO, a new C++ dependency for I2C |
| HW-I7 | idiom | Choose the GPIO chip with `chip=auto` by default: scan `/dev/gpiochip0..9`, score rp1 +100, bcm +90, raspberrypi_exp -50, try in order; an explicit path skips the scan. Each GPIO user carries its own `gpioChipScore`. | always | `GpioInput.cpp:238-262,503-535`; `TriggerOutput.cpp:195-228,550-572`; `RecordingIndicatorOutput.cpp:198-220,602-624` | a hard-coded `/dev/gpiochip4`, a board-model key, a Pi-model switch |
| HW-N1 | intent | Read device wiring once at process start and require a Core/UI restart after a change; the WebUI says so. IMU and `[run_script]` are read per use. | usually | `App:6881-6898`; `App:4602`; `WebControlPage.cpp:3868`; per-use `Mpu6050RecordingSession.cpp:1040`, `App:8663` | a file watcher or hot-reload of input groups added unasked |
| HW-N2 | intent | Never let a hardware input cause side effects on media, calibration or recording parameters during a take (guards in the command layer, plus the eject guard); in Standby a button press only wakes and is consumed; a rotation never wakes or sleeps. Start/stop by button is allowed. | always | `App:8892-8895`; `App:9105-9107`; `App:9706-9707`; `App:8642-8656` | a hardware action that changes resolution/format/media or calibrates mid-take; a press in Standby also firing its action |
| HW-N3 | intent | Make `apertar-hardware.conf` the operator's single hand-edited surface for wiring (device, bus, address, chip, pin map, polarity, pull, poll/debounce, trigger events, LED pin, scripts); keep behaviour (action semantics, step lists, battery curve, chip scoring, limits 6 actions / 5 scripts) fixed in code. | usually (`[network]`, `[display]`, IMU offsets) | `Core/README.md:157-177`; `ButtonActionList.hpp:14-15`; `WebControlPage.cpp:3840-3870` | step lists or battery curves moved into config; a forms-based hardware editor replacing the textarea |
| HW-N4 | intent | Design for Pi 5 / CM5 first with Pi 4/3 working via auto-detection; control and output accessories (PCF8574, GPIO, NeoRotary4, Grove, trigger, LED) ship disabled in the templates; INA219 (bus 4) ships enabled, CFexpress hat (bus 10) enabled in Core template, IMU default differs between templates. | usually | `GpioInput.cpp:247-253`; `Core/README.md:62-66`; `App:4298-4305`, `:4343-4344`; `UI/src/DisplayConfigBridge.cpp:70-71`, `:199-209` | a new accessory enabled by default; a Pi-4-only or Pi-5-only code path without auto-detect |
| HW-N5 | intent | Tolerate two processes touching the same hardware: Core and UI each read `[ina219]` and program the chip, and each write `[imu]` keys with their own code; no IPC lock. | usually | `App:4602-4626`; `UI/src/Ina219Bridge.cpp:490-568`; `Mpu6050RecordingSession.cpp:1295-1301`; `UI/src/GyroConfigBridge.cpp:1577` | a contribution that "fixes" this with a lock daemon or moves INA219 into one process unasked |
| HW-N6 | intent | Keep hardware-input health out of the state JSON, WebUI and UI; problems go to the journal (`std::cerr`). IMU status is the exception. | usually | `App:6881-6896`; no `Input_.lastError` reads in `App`; IMU `App:9681` | new `hardware_status` JSON fields or a UI page for input health |
| HW-N7 | intent | Be lenient with the operator's file: unknown keys/sections ignored, bad values keep defaults; log only mapping errors, unknown actions and script problems. | usually (script runner throws) | `GpioInput.cpp:441-445`; `App:4489-4498`; `App:8954`; `ButtonActionList.hpp:114-115` | refusing to start on an unknown key; strict schema validation |

### Recipe (corrected): add a hardware input device

1. `Core/src/hardware/MyInput.hpp`: shape of `Pcf8574Input.hpp:1-57` (callback ctor, `start/stop/enabled/configPath/lastError`, private `struct Config` with defaults, `static Config loadConfig()`). No app includes (HW-S8).
2. `Core/src/hardware/MyInput.cpp`: copy helpers `Pcf8574Input.cpp:27-106`, `normalizeSingleAction` `:140-246`, `loadConfig` `:318-390`, poll/debounce `:470-527`, `setLastError` `:460-468`.
3. `Core/CMakeLists.txt:83-91`: add the `.cpp` by name.
4. `Core/src/ApertarCoreApp.hpp:5-12` include, `:114-121` member.
5. `App:6785-6792` ctor lambda to `handleHardwareInputAction` (`, false` for rotation).
6. `App:6886-6891` `start()`, `App:6914-6918` `stop()`.
7. New actions: branch in `App:8660-8955` that ends in `dispatch(...)`; guards in the command handler (HW-S7), not here.
8. Templates: commented section with `enabled=false` in `App:4291-4404`, `UI/src/DisplayConfigBridge.cpp:41-326`, `UI/src/Ina219Bridge.cpp:69-342`.
9. `Core/README.md:157-177` if operator-facing; note restart needed.

### Recipe (corrected): add an output driven by camera state

1. Class pair in `src/hardware/` shaped like `TriggerOutput.hpp/.cpp` (worker thread + condvar `TriggerOutput.cpp:403`, `"ApertarCore <device>: "` errors `:695`).
2. Default-constructed member `ApertarCoreApp.hpp:120-121`; `start()` with error print `App:6881-6884`; `stop()` `App:6920-6921`.
3. Feed it only in `handleTriggerEvent` `App:10854-10889` by matching an existing event string; seed state after `start()` like `App:6897-6898`.
4. Templates (step 8 above) with `enabled=false` and a wiring-safety comment (`App:4374`, `:4391`).
