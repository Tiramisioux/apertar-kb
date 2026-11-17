# Feature list: Controls, hardware, system and configuration

What the cinemate port added in this area that original Apertar 1.6.0 could not do. One entry per feature; the Core, WebUI and touch parts of a feature are merged.

| Item | Value |
| --- | --- |
| Built from | inventories App-2, App-4, App-5, HW-config-text-store, HW-controls-model, HW-input-classes, Boot-config, Build-scripts-docs (`raw/inv-*.md`, `raw/FEATURES.json`), `fork-log.md`, commit messages. Command names, routes, keys and env vars re-checked by grep in `/home/user/Apertar-Core` @cinemate-port `01f170c` and `/home/user/Apertar-UI` @`7ea9afc` |
| Original | `upstream-1.6.0` (Core `35dbe67`, UI `43888e5`) |
| Short names | `App` = `src/ApertarCoreApp.cpp`, `WCP` = `src/web/WebControlPage.cpp`, `hwconf` = `src/hardware/HardwareConfigText.hpp` |
| "Stock camera" | a camera running `cinemate-port` with no config edit and no helper installed |
| Already fixed, not listed as open | The GPIO chip setting is back on the Controls page and its checks are per chip (Apertar-Core `04fe197`, worktree `/home/user/wt/core-work`). This repairs feature 3's "narrowed" part (`166cc4d` had hidden `chip`, `poll_ms`, `open_drain`) |
| "Tested" | `pi build` in a commit text means "compiled on the Pi", not "run on the camera". "Desk" = host test or Mac, no camera. The fork log has no feature-test row for most Controls commits ("fork-only") |
| Relation words | extends in place / beside upstream / replaces upstream / new area |

## Table

| # | Feature | Default for a stock camera | Relation to 1.6.0 | Tested |
| --- | --- | --- | --- | --- |
| 1 | One writer for the hardware file (revision, merge, history, Undo, restore) | on; changes the Config page save | replaces `saveHardwareConfigFile`, beside the readers | Pi: store test, live `mv` restore; page desk only |
| 2 | Hardware file checker and error counts (WebUI, touch chip) | on; logs at start | new area | desk; Pi build |
| 3 | Controls page backend (`get_controls`, `set_controls`, rows, detection) | on | new area, beside the readers | Pi: real chip read; page against a mock |
| 4 | Saves apply without a restart | on | new area; extends `start()`/`stop()` | desk; Pi build |
| 5 | Listen, I2C scan, output test | on, WebUI only | new area | desk (mock); Pi build |
| 6 | Remote-only buttons and Try | on, WebUI only | new area | Pi, used in drop-frames tests |
| 7 | One action vocabulary and `list_actions` | on | replaces three normalizers | host test 20/20; Pi build |
| 8 | `clear_hdr` button action | off until mapped | extends in place | desk |
| 9 | Click and Hold gestures on buttons, knob pushes, PCF pins | off until `_single`/`_double`/`_triple`/`_hold` set | extends in place | desk; Pi build |
| 10 | 1-0-1 (normally closed) buttons | **on, changes behaviour** | extends in place | desk |
| 11 | Edge events instead of GPIO polling | **on, replaces the poll loop** | replaces `GpioInput::run` loop | desk; Pi build |
| 12 | Two- and three-way GPIO switches | off (`enabled` absent) | new section, beside buttons | desk; Pi build |
| 13 | Default hardware template, no file written by the touch UI | **on, changes first start** | extends template; removes UI code | desk |
| 14 | IMU config writes through the store | on | replaces two line editors | Pi builds; no gyro on rig |
| 15 | Boot Config card (`config.txt`), review, text edit, helper | card on; saving needs the helper | new area | desk and mock server; never on a Pi |
| 16 | Fan mode through Core's writer | on | extends `applyFanMode`; removes UI code | Pi build only |
| 17 | Real-time scheduling switches (`APERTAR_RT`) | off | extends start script and drop-in | no result recorded |
| 18 | Value lists, free stepping, flicker-free angles | lists off (built-in lists) | new area (UI.conf) | desk; Patrik 2026-10-28 |
| 19 | Four recording-indicator switches | frame off, buffer bar off, red timecode on, audio outline on (`App:1904-1907`) | extends `handleUiToggle` chain | Patrik 2026-10-28 (two of four) |
| 20 | UI timecode and file timecode set apart | both (as before) | extends `set_timecode_mode` | Pi build, not tested |
| 21 | Integrator files: sudoers, install steps, host tests | none installed | beside upstream standby helpers | helper tests on desk |

## 1. One writer for the hardware file

| Item | Value |
| --- | --- |
| Operator gets | A save from the Config page, the Controls page or the IMU no longer overwrites a newer file by accident. A stale page is refused (409) and keeps its text. The last 20 versions are kept with an Undo. A file replaced by a default (for example by the touch UI) is detected and put back with one button |
| How used | WebUI Config > Hardware: the editor sends `X-Apertar-Revision`; Undo and history list; banner "file was replaced" with Restore. Socket: `set_controls restore=true`, `controls_history name=` |
| Socket / HTTP | `GET /api/config` (adds `revision`, `boot_copy`; a missing file shows the `/boot` copy or the template), `POST /api/config` (header `X-Apertar-Revision`; 400 with `issues[]`, 409 with `code` = `old_page`, `merge_review`, `stale`, `conflict`, `being_written`, `locked`), `controls_history`, `set_controls` (`base`, `text`, `restore`, `dry_run`, `force`, `confirm_merge`, `by`); socket line limit 64 KiB to 1 MiB (`ControlServer.cpp:16`) |
| State fields | reply objects `issues[]` `{line,error,rule,section,key,message}`, `conflicts[]`, `replaced {replaced,reason,saved_at,source,restore_revision}` |
| Config / files | `~/.config/apertar-core/hardware-history/`, `hardware-state.conf` (`written_revision`, `written_at`, `written_by`), a last-written copy and a pinned adopted copy; history `kHistoryKept = 20` (`HardwareConfigStore.cpp:22`) |
| Env | `APERTAR_HARDWARE_CONFIG` (existing), `XDG_CONFIG_HOME`, `HOME` for the notes path |
| Touches in 1.6.0 | Replaces `saveHardwareConfigFile` (`App`, upstream `:5323-5386`: empty / 256 KiB / NUL checks, `.bak`, `.tmp` + rename; the three checks live on as `checkHardwareConfigText`). Changes `buildHardwareConfigFileJson` and the `/api/config` handler in place. New `HardwareConfigText.hpp` (text model, key edits, merge) and `HardwareConfigStore.{hpp,cpp}`. The per-class readers (`GpioInput::loadConfig` and the others) are untouched: they still parse their own section |
| Needs | nothing |
| Tested | `3526e4b` Pi: text model 84/84, store test 39/39; `014fa22` Pi: store test 52/52, live `mv` test restored byte for byte; `5395fa4` and `effb804` desk only. Fork log: fork-only, branch `controls` on the Pi from 2026-10-29. The store's own tests are not in the Core tree (KB sketch, 78 checks) |
| Commits | `3526e4b` `5395fa4` `effb804` `014fa22` `f5a61b8` `4d80a35` `07afbc6` |
| For development | There is now a second source of truth for the file's syntax (`hwconf`) beside each reader's own parsing; a new key needs both. Every writer must go through `configStore()`; a plain `std::ofstream` on the file bypasses the revision and history. A stock Config page from an older browser tab now gets a 409 |

## 2. Hardware file checker and error counts

| Item | Value |
| --- | --- |
| Operator gets | At start Core checks `apertar-hardware.conf` and logs errors and warnings with line numbers (junk lines, duplicate sections or keys, missing I2C bus, a GPIO pin claimed twice, pins held by a DPI display, unknown actions, inline comments, PCF sharing). The Config page lists them; the touch UI camera page shows "Controls: N errors" |
| How used | WebUI Config > Hardware (Check button, issue list); touch UI camera page chip and Settings > Info > Controls card (counts and the WebUI address) |
| Socket / HTTP | `get_controls` (`issues`, `errors`, `warnings`), `get_state` fields below; event `controls` |
| State fields | `controls_errors`, `controls_warnings` in `get_state` (`App:12947-12948`) |
| Config | none; validates every section in `kSections` (21), including the new `[storage] buffer`, `[media] preroll`, `[gpio_switches]`, `[gpio_buttons] dN_*` and `remoteN` keys |
| Env | `APERTAR_BOOT_CONFIG` (read to learn DPI-held pins; see 15) |
| Touches in 1.6.0 | Beside the readers. Upstream's rule is "a reader keeps its default and ignores unknown keys silently" (HW-12); the port reports instead. In `start()` it validates, adopts and pins the file. A save that adds new errors is refused by the store (the Config page used to write anything) |
| Needs | nothing |
| Tested | host tests `tools/storage_buffer_conf_test.cpp`, `storage_preroll_test.cpp` cover the buffer and pre-roll rules only; `4d80a35` desk 88/89 (the miss needs GNU sed); UI `ea44bd7` "pi build, qmllint, not seen on a touch screen" |
| Commits | Core `3526e4b` `0a98868` `c34f844` `9b5ea14` `d44b177` `4d80a35`; UI `ea44bd7` |
| For development | The checker is advisory in the design but the store treats "new error" as a refusal (design note `design/hardware-inputs.md`): the checker can reject a file the readers accept, and its alias rules have drifted from the readers once already. Change a reader's accepted keys and the checker in the same commit |

## 3. Controls page backend

| Item | Value |
| --- | --- |
| Operator gets | Config > Hardware shows one row per button, knob, PCF pin, encoder and switch with its actions, what can still be added, which BCM pins are used or free, and the live state of GPIO, NeoRotary 4, PCF8574, Grove ADC, CFexpress hat, tally LED and trigger output, including which GPIO chip Core uses, who holds each header line and the NVMe model, size and PCIe link on the CFexpress hat card |
| How used | WebUI Config > Hardware cards (one per device, gesture dropdowns, add buttons). Edits go as single keys, so every other byte, comment and order of the file stays. Socket: `get_controls`, `set_controls set.<section>.<key>=`, `unset.<section>[.<key>]` |
| Socket / HTTP | `get_controls` (adds `model`, `peripherals`, `i2c_buses`, `apply`, `dpi_lines`; answered before the command lock, `App:12420`), `set_controls` (`App:12763`) |
| State fields | none in `get_state` beyond feature 2 |
| Config | canonical key names the page writes: `bus`, `address`, `poll_ms`, `chip`, `dN`, `pinN`, `aN`, `target`, `line`; peripheral specs repeat the readers' defaults in a second place |
| Touches in 1.6.0 | Beside the readers: new `ControlsModel.hpp`, `GpioChipInfo.{hpp,cpp}` (`gpioChipScore` moved out of `GpioInput.cpp`, so `chip=auto` and the card choose the same chip), `I2cProbe.{hpp,cpp}`, five helper functions in `App` (`4965-5029`). A second, read-only dispatcher runs ahead of the command mutex in `handleCommand` (upstream has one flat chain under one mutex). CFexpress status: a fourth reader of the HAT status byte (see Recording and media list, feature 1) |
| Needs | I2C access for probes; the CFexpress card needs the hat on I2C |
| Tested | `166cc4d` Pi: real chip and pins read, page against a mock 26/26; `07afbc6` desk, 98 checks; fork log fork-only. No unit test in `tools/` |
| Commits | `07afbc6` `166cc4d` `0a98868` `c34f844` `c140c4f` `dcf09ee` `9b5ea14` `f5a61b8`; WebUI `d282de9` `f5fe41b` `fa3a798` |
| For development | The page is data-driven from `ControlsModel`: a new input class must add a peripheral spec and a row builder or it will not appear. The GPIO chip, `poll_ms` and `open_drain` keys are back on the page (`04fe197`); the Grove and PCF cards still hold only some keys |

## 4. Saves apply without a restart

| Item | Value |
| --- | --- |
| Operator gets | Saving the hardware file restarts only the drivers whose sections changed, waits until a take ends, and lists outside services that still need a restart |
| How used | automatic after Save; WebUI shows the apply state |
| Socket / HTTP | `get_controls` field `apply` `{state, detail, pending[]}`; event `controls {applied, groups}` (`App:12346`) |
| State fields | none |
| Config / env | none |
| Touches in 1.6.0 | New controls worker thread (`controlsWorkerRunning_`, started in `start()` `App:8156`, stopped before the drivers in `stop()` `App:8172`). Upstream reads each section once at start and has no restart path for a driver group |
| Needs | nothing |
| Tested | `dcf09ee` "desk (host 120/121, only the GNU sed check); pi build". No Pi run recorded |
| Commits | `dcf09ee` `8be1ab5` (WebUI) |
| For development | The worker owns driver restarts; code that opens a hardware class outside `start()` races it. The worker thread is one of seven long-lived threads the port adds to `start()` (upstream: two) |

## 5. Listen, I2C scan and output test

| Item | Value |
| --- | --- |
| Operator gets | The page shows the last control that fired, so the operator learns which physical control is which; scans an I2C bus with device-name guesses; blinks the tally LED once or pulses the trigger output once |
| How used | WebUI Config > Hardware: Listen, Scan, Test buttons |
| Socket / HTTP | `controls_last_input` (`App:12476`), `scan_i2c bus=` (`:12486`), `test_output` (`:12745`); `scan_i2c` and `test_output` are refused during a take |
| State fields | none |
| Config / env | none |
| Touches in 1.6.0 | A third callback on `GpioInput`, `Pcf8574Input`, `NeoRotary4Input`, `GroveAnalogInput` beside the action callback and the rotation callback; new method beside `TriggerOutput::pulse()`. Beside upstream, which has none of it |
| Needs | I2C bus for the scan |
| Tested | WebUI page test 60/60 against a mock (`8be1ab5`); Pi build; no camera run recorded |
| Commits | `dcf09ee` `8be1ab5` |
| For development | The input classes now report to App in three ways; a new input class must feed the Listen callback or its controls stay silent on the page |

## 6. Remote-only buttons and Try

| Item | Value |
| --- | --- |
| Operator gets | A "button" with no GPIO pin that runs from the WebUI Remote controls card; Try buttons run a control's saved action. Works when a DPI display holds the GPIO header (those pins are greyed) |
| How used | WebUI Config > Hardware > Remote controls; config `[gpio_buttons] remoteN`, `remoteN_single/_double/_triple/_hold` |
| Socket / HTTP | `test_input section= key=` (`App:12565`) through the hardware-input path |
| State fields | none |
| Touches in 1.6.0 | New area; reuses the action dispatcher in `App` |
| Tested | Pi, used in the drop-frames tests (`1319967`, `9b5ea14`) |
| Commits | `9b5ea14` `1319967` |
| For development | Remote controls bypass the pin layer, so the gesture timing is not applied to them |

## 7. One action vocabulary and `list_actions`

| Item | Value |
| --- | --- |
| Operator gets | The same action names work on every button, knob, PCF pin and Grove target. A typo logs "Did you mean ...". The WebUI shows an action dropdown with labels, groups and the values valid for the current sensor |
| How used | WebUI action dropdowns; config values as before |
| Socket / HTTP | `list_actions` (`App:12534`) |
| Touches in 1.6.0 | Replaces three `normalizeSingleAction` copies, the Grove target body and the trigger-event list with `hardware/ActionCatalog.hpp`; `isoinf`/`isonan` refused. Upstream keeps flat `parseHardwareAction*` helpers inline |
| Tested | `916c1dd` desk, host test 20/20, then "358 tokens identical to the old normalizers" (`243fe2c`) |
| Commits | `916c1dd` `243fe2c` `d282de9` |
| For development | The catalog is now the only place to add an action; add the dispatcher branch and the catalog row together |

## 8. `clear_hdr` button action

| Item | Value |
| --- | --- |
| Operator gets | A button or knob push toggles Clear HDR on the IMX585 in CinemaDNG or MLV |
| How used | any action key may hold `clear_hdr` (button-only in the catalog) |
| Touches in 1.6.0 | New branch in `handleSingleHardwareInputAction` |
| Tested | desk (`243fe2c`); not recorded on a camera |
| Commits | `243fe2c` |
| For development | The action calls the same setter as the WebUI; Mode Ladder can refuse it (see Camera and modes list) |

## 9. Click and Hold gestures

| Item | Value |
| --- | --- |
| Operator gets | Each push can run up to five actions: Press, Single, Double, Triple click, Hold. Timing follows Cinemate: click window 500 ms, long press 500 ms, Hold 3 s (`ButtonGesture.hpp:16-18`) |
| How used | config `[gpio_buttons] dN_single/_double/_triple/_hold`, `[neorotary4] encoderN_*`, `[pcf8574] pinN_*`, `[gpio_encoders] encoderN_*`; WebUI gesture dropdowns |
| Touches in 1.6.0 | Extends the button branch of `GpioInput::loadConfig/run` and the same in `NeoRotary4Input`, `Pcf8574Input`; new `ButtonGesture.hpp`, `ButtonActionList.hpp`. Upstream has only `PowerButtonGesture` for the standby button |
| Tested | `0a98868` desk (click counter 8 checks); `c140c4f` desk host 120/121; Pi build. No hardware run recorded |
| Commits | `0a98868` `c140c4f` `0c49601` |
| For development | A button with a click action waits out the click window before it can fire; a plain Press action stays immediate. Gesture timing constants are fixed in the header |

## 10. 1-0-1 (normally closed) buttons

| Item | Value |
| --- | --- |
| Operator gets | A button, encoder push or PCF pin that reads pressed at start is treated as wired the other way round; one journal line says so |
| Touches in 1.6.0 | Extends the GPIO and PCF read loops (`GpioInput.cpp:620-631`, `Pcf8574Input.cpp:424-441`). **Behaviour change**: upstream ignores a button held at start until released (first sample seeds state, `GpioInput.cpp:693-697`); the port inverts it for the session. The design note proposes to restore the upstream rule |
| Tested | desk only |
| Commits | `0a98868` `c140c4f` |
| For development | Polarity should come from `active_low`; the auto rule also catches a wake press and a press held while the camera starts |

## 11. Edge events instead of polling

| Item | Value |
| --- | --- |
| Operator gets | The input thread sleeps until a kernel edge or a gesture timer is due instead of waking every 12 ms; chips without edge events fall back to `poll_ms` |
| Config | `[gpio_buttons] poll_ms` (now a fallback) |
| Touches in 1.6.0 | Replaces the poll loop in `GpioInput::run` with a `poll()`/read loop |
| Tested | `0c49601` desk plus Pi build; no hardware run |
| Commits | `0c49601` |
| For development | Stock cameras run this path with no switch to go back; a chip that lacks edge support needs a Pi 4 or CM4 check (board-support sweep) |

## 12. Two- and three-way GPIO switches

| Item | Value |
| --- | --- |
| Operator gets | Switch positions run actions; the position at start is applied once |
| Config | `[gpio_switches] enabled`, `switchN_pins`, `switchN_on`, `switchN_off`, `switchN_position0/1/2`; shares `chip`, `pull`, `active_low`, `debounce_ms` with `[gpio_buttons]` |
| Touches in 1.6.0 | New section parsed in `GpioInput::loadConfig`; new runtime state in the input thread |
| Tested | `c34f844` desk (host 118/119), Pi build |
| Commits | `c34f844` `fa3a798` |
| For development | A switch flipped in Standby wakes the camera and the new position is never applied (design note) |

## 13. Default hardware template and no UI-written file

| Item | Value |
| --- | --- |
| Operator gets | A missing hardware file starts as an HDMI 1080p monitor (`ui_width=1920`, `ui_height=1080`, `ui_layout=landscape_large`, `hdmi_external_only=true`; was 720, 720, `square`, false). The template lists NeoRotary, GPIO encoders, GPIO switches, Grove analog and the new `[storage]`, `[media]`, `[camera]` keys; `[pcf8574] bus` 10 to 1; six `[imu]` keys removed |
| Touches in 1.6.0 | Extends `defaultHardwareConfigTemplate` (`App:5035`). In the UI, `DisplayConfigBridge` and `Ina219Bridge` lose their `ensureDefaultHardwareConfigFile` writers (-578 lines) and the display fallback becomes 1920x1080 (`7c41a27`). Upstream: the touch UI wrote its own larger template at every start when the file was missing |
| Needs | nothing |
| Tested | `7af9f13` desk; `c9d841f` `7c41a27` desk, "UI build on the Pi not yet run" |
| Commits | Core `4d80a35` `7af9f13` `c34f844` `d44b177` `d7dd337` `ba0658d` `8175273`; UI `c9d841f` `7c41a27` |
| For development | A fresh camera has no hardware file until Core is told to write one; design note proposes Core writes its template once. The template carries live port keys (`[storage] buffer*`, `[camera] clear_hdr_iso_max_*`) that belong to other areas' features |

## 14. IMU config writes through the store

| Item | Value |
| --- | --- |
| Operator gets | Level reference, gyro calibration, driver, orientation and sync offset saves are serialised, atomic and in the history; setting and clearing the level reference is one edit |
| Touches in 1.6.0 | Replaces `writeHardwareConfigValue` and `updateImuBiasConfig` (about 230 lines) in `Mpu6050RecordingSession.cpp` |
| Tested | Pi: Core builds; no gyro on the rig, nothing tried |
| Commits | `c509e9f` |
| For development | IMU writes within 10 minutes share one history entry |

## 15. Boot Config card (`config.txt`)

| Item | Value |
| --- | --- |
| Operator gets | Pick the sensor per camera connector, link frequency, RP1 overclock, I2C/I2S/SPI/onboard audio and the display (HDMI, Waveshare 4", Hyperpixel 4") in the WebUI System pane; review the lines that will change; save and reboot. A save that would not do what was asked is refused with the deciding line. Edit file as text works too, and italics mark the lines the card or fan mode may rewrite |
| How used | WebUI System pane > Boot Config: Save & Reboot (dry run first), Edit file / Use This Text, View, Download, Upload. A display change needs a tick naming the cost. After the save the page waits until the camera answers |
| Socket / HTTP | `get_boot_config`, `set_boot_config` (`cam0_sensor`, `cam1_sensor`, `cam0_link_frequency`, `cam1_link_frequency`, `i2c`, `i2s`, `spi`, `audio`, `rp1`, `display`, `dry_run`, `confirm_display`, `revision`, `text`; `App:14586-14589`), `GET /api/boot-config`, `POST /api/boot-config` (header `X-Apertar-Revision`, 409 stale), `POST /api/boot-config/parse`. Error codes `invalid`, `unreadable`, `stale`, `old_page`, `refused`, `confirm_display`, `permission`, `write_failed` |
| State fields | none in `get_state`; `get_boot_config` returns `boot_config {path, readable, revision, helper, backup_path, state, drm, text, state.managed}` |
| Config / env | `APERTAR_BOOT_CONFIG` (path override for tests), file `/boot/firmware/config.txt`, backup `config.txt.apertar.bak` |
| Touches in 1.6.0 | New area: `BootConfigText.hpp` (engine, board-aware `[pi5]`/`[pi4]`/`[all]`), `App` boot-config functions (`3502-3700`), WebUI card. Upstream only writes the fan block of `config.txt` (`set_fan_mode`) with `sudo -n install` |
| Needs | The root helper `apertar-boot-config` and its sudoers rule (feature 21) for a save; without them the card reads but a save is refused with an install hint |
| Tested | Host: `tools/boot_config_test.cpp` 75 checks, `boot_config_helper_test.sh` 10 checks; card driven in Chromium against a mock server using the real engine. `b3e7f52` found a link-frequency bug on the dev Pi (two saves, journal and diff). Never run on a Pi camera as a whole (handoff note, fork log has no row for these commits) |
| Commits | `f19b245` `2955ef8` `8a56545` `afa00e8` `496817f` `3b87d99` `2a4266e` `b3e7f52` `dda1713` `4581a69` (merge) |
| For development | `config.txt` has two writers in Core (card, fan mode) and one lock; no other code may rewrite the file. Sensor lists live in the engine, not in the Apertar DKMS drivers: adding a sensor needs both |

## 16. Fan mode through Core's writer

| Item | Value |
| --- | --- |
| Operator gets | Fan mode changes no longer race a Boot Config save; the touch UI and the WebUI both use Core |
| Socket | `set_fan_mode` (`App:14592`, interface unchanged) |
| Touches in 1.6.0 | Extends `applyFanMode` in `App`; in the UI `SystemActionBridge::applyFanMode` now sends `set_fan_mode` over the Core socket (-103 lines; the config block builder and the write path are removed) |
| Tested | UI `41ff827` "pi build only, not tried by hand"; Core path through the helper not verified on a Pi |
| Commits | Core `2955ef8`; UI `41ff827` |
| For development | The UI now needs Core running to change the fan; before it wrote the file itself |

## 17. Real-time scheduling switches

| Item | Value |
| --- | --- |
| Operator gets | An A/B lever for dropped frames: run Core under SCHED_FIFO on cores 1-3, or put only libcamera's completion thread on SCHED_FIFO |
| How used | environment, not a setting |
| Env | `APERTAR_RT=1`, `APERTAR_RT_PRIORITY` (70), `APERTAR_RT_CPUS` (`1-3`; empty = no pinning), `APERTAR_RT_CAPTURE_PRIORITY` (1-99, completion thread only; recording area) |
| Touches in 1.6.0 | Extends the `exec` line of `scripts/start-apertar-core.sh` (`chrt -f`, `ionice -c2 -n0`, `taskset`; falls back with one stderr line when `chrt` is refused). `config/apertar-core-capture-priority.conf` gains `LimitRTPRIO=80`; its old stated policy was "only bounded non-real-time" |
| Needs | `LimitRTPRIO` on the unit (the drop-in) |
| Tested | no result in the fork log; the script comment says the A/B decides whether it stays |
| Commits | `c57c284` `6ef0ddc` |
| For development | Whole-process FIFO can starve the WebUI threads (`6ef0ddc` says so); treat as a test lever, not a default |

## 18. Value lists, free stepping, flicker-free angles

| Item | Value |
| --- | --- |
| Operator gets | Custom ISO, shutter angle, fps and white-balance lists, free stepping with an increment, and flicker-free shutter angles for 50 or 60 Hz mains; pots, encoders and buttons use them and stop at `iso_max` / `fps_max` |
| How used | WebUI Controls pane > Value Lists card (moved there by `6777ebe`) |
| Socket | `set_value_steps name=iso|shutter_angle|fps|wb values= free= increment=` (+ `flicker_free=`, `mains_hz=` for shutter angle; `App:14110`) |
| Config | `UI.conf`: `isoSteps`, `isoFree`, `isoFreeIncrement`, `shutterAngleSteps`, `shutterAngleFree`, `shutterAngleFreeIncrement`, `fpsSteps`, `fpsFree`, `fpsFreeIncrement`, `wbSteps`, `wbFree`, `wbFreeIncrement`, `flickerFreeShutterAngles`, `mainsHz`; web `ui` state carries the lists |
| Touches in 1.6.0 | New area in `App` command chain and the UI.conf reader (the file the touch UI watches); the touch UI reads the lists |
| Tested | commit "desk only"; fork log: tested by Patrik 2026-10-28 |
| Commits | `b0e90ad` `6777ebe` |
| For development | The ranges live in a static table inside the handler; the touch UI and WebUI must stay in step with it |

## 19. Four recording-indicator switches

| Item | Value |
| --- | --- |
| Operator gets | Switches for the recording frame (red border), the frame buffer bar, red timecode while recording and the audio recorded outline |
| Socket | `set_recording_frame_enabled`, `set_frame_buffer_bar_enabled`, `set_recording_red_timecode_enabled`, `set_audio_recorded_outline_enabled` (`App:13505-13511`) |
| Config | `UI.conf`: `recordingFrameEnabled` (false), `frameBufferBarEnabled` (false), `recordingRedTimecodeEnabled` (true), `audioRecordedOutlineEnabled` (true); also stored in presets |
| Touches in 1.6.0 | Four more entries in the `handleUiToggle` chain (same pattern as `set_zebra_enabled`) |
| Tested | `f4fb084` Patrik 2026-10-28 (frame, red timecode); buffer bar and outline came with `d44b177` and `92d0970` |
| Commits | `f4fb084` `92d0970` `d44b177` |
| For development | Follows the upstream toggle pattern; the buffer bar only moves when the write buffer feature is on |

## 20. UI timecode and file timecode set apart

| Item | Value |
| --- | --- |
| Operator gets | The timecode written into the files can differ from the one the screens show |
| Socket | `set_timecode_mode value=rec_run|free_run target=ui|files|both` (no target = both; `App:13279`) |
| Touches in 1.6.0 | Extends `set_timecode_mode`; a preset's `cameraTimecodeMode` no longer overwrites the UI copy |
| Tested | Pi build 2026-10-29, not tested |
| Commits | `909aaa5` |
| For development | The UI copy lives in UI.conf (`timecodeMode`), the file copy in `camera_settings.conf` |

## 21. Integrator files

| Item | Value |
| --- | --- |
| Operator gets | Nothing visible. An integrator gets install files for the root helpers and their README steps |
| Files | `scripts/apertar-boot-config` (root helper, stdin to `config.txt`, 64 KiB max, no NUL, needs a `[pi5]`/`[pi4]`/`[all]` header, `.bak`, atomic rename), `config/apertar-boot-config.sudoers` (pins the helper path, no arguments). The media helpers (`apertar-media-trim`, `apertar-media-tune`) and their sudoers and tmpfiles files belong to Recording and media. Install: `sudo install -m 0755 ... /usr/local/libexec/...`, `sudo install -m 0440 ... /etc/sudoers.d/...`, `sudo visudo -cf` (README `:202-204`) |
| Touches in 1.6.0 | Beside the upstream standby helpers (`apertar-standby-usb`, `apertar-standby-low-power`). CMake adds `LANGUAGES C CXX`, the new hardware sources and a `third_party/liblj92` include dir; no test target and no `enable_testing`, so the host tests in `tools/*_test.cpp` and `*.sh` are run by hand |
| Tested | helper test on a scratch copy (10 checks) on the desk; not installed or run on a Pi |
| Commits | `dda1713` `496817f` |
| For development | The README now carries a 14-row env table and five new sub-sections; upstream has none. The helper is new ground: root, fixed path, no arguments |

## Seen in these units, main home is another area

- Media watcher, pulled-drive survival, CFexpress slot-bit detection, drive trim, media tuning file and kernel tune, RAM write buffer and safety stop, storage pre-roll, split takes and merge worker, direct DNG write, write-path env knobs, `set_media_trim`, `set_buffer_mode`, `set_frames_per_folder`, `set_clip_merge`, `set_storage_preroll`, `APERTAR_RT_CAPTURE_PRIORITY`: Recording and media list.
- Clip Browser facts (`/api/media/clip`, `/api/media/file`, `/api/media/frame`), playback hold, yielding downloads and deletes, sound in the viewer, vendored `liblj92`, time-left estimate and IMX283 still estimate: Recording and media list.
- CineMate Log, speed ramp, conform fps, phase lock, clip name templates, presets carrying more settings (`buildCurrentPresetPayload`), preview TDN, Mode Ladder, sensor binning and ISO lock, Clear HDR ISO keys (`[camera] clear_hdr_iso_max_*`): Camera and modes list and the Presets area.
- Touch UI buffer bar, pills and toasts, `MediaStatusBridge`, `CfeAutomounter`: touch UI area (only the Core contract is above).
