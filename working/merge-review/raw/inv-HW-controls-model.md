# Inventory: HW-controls-model (stage 1)

Refs: port = `cinemate-port` `01f170c` (Apertar-Core), upstream = `upstream-1.6.0` (`/home/user/wt/core-upstream`). No judging here.
Labels: confirmed = read in code.

## 1. Scope files (all read completely)

| File | Lines | Kind | Commits (git log origin/main..cinemate-port) |
| --- | --- | --- | --- |
| `src/hardware/ActionCatalog.hpp` | 360 | new, header-only, pure | `916c1dd`, `243fe2c` (clear_hdr row) |
| `src/hardware/ControlsModel.hpp` | 390 | new, header-only, pure (no I/O) | `07afbc6`, `166cc4d`, `0a98868`, `c34f844`, `c140c4f`, `dcf09ee`, `9b5ea14` |
| `src/hardware/ButtonGesture.hpp` | 76 | new, header-only, pure | `0a98868`, `0c49601` (edge-event rework), `c140c4f` (reused) |
| `src/hardware/GpioChipInfo.hpp/.cpp` | 35 / 110 | new, in CMake (`CMakeLists.txt:95`) | `166cc4d` |
| `src/hardware/I2cProbe.hpp/.cpp` | 17 / 39 | new, in CMake (`CMakeLists.txt:96`) | `0a98868` |

Fork-log status (`/home/user/apertar-kb/fork-log.md` lines 105-150): all of the above commits "fork-only". `916c1dd` on Pi branch `controls` since 2026-10-29. `0a98868`/`0c49601`/`c140c4f` commit text says "Tested: desk ... pi build" (0c49601). No host test in `tools/` touches ActionCatalog, ButtonGesture or ControlsModel (confirmed: `ls tools`, grep). Nothing here is tested on a sensor-running camera per the logs; only "pi build" and desk.

## 2. Features touching this unit (operator-visible)

| Feature | What the operator gets | Files / regions | Commits | Relation to upstream |
| --- | --- | --- | --- | --- |
| One action vocabulary | Same alias list for GPIO, NeoRotary, PCF pins, Grove target names, trigger events; unknown action logs "Did you mean 'x'?" | `ActionCatalog.hpp` (`kSpecs`, `canonicalAction`, `suggestion`, `canonicalAnalogTarget`, `kTriggerEvents`); callers `GpioInput.cpp:114`, `NeoRotary4Input.cpp:125`, `Pcf8574Input.cpp:144`, `GroveAnalogInput.cpp:128`, `TriggerOutput.cpp:133`, `ApertarCoreApp.cpp:10684` | `916c1dd` | replaces upstream per-class `normalizeSingleAction` (3 copies) |
| `list_actions` command | The WebUI dropdown of actions, groups, labels, valid values for the current sensor/resolution | `ApertarCoreApp.cpp:12534-12560`, `ActionCatalog.hpp:336 catalogJson` | `916c1dd` | new area |
| `clear_hdr` action | Button / knob push toggles Clear HDR (IMX585, CinemaDNG or MLV only; "button only") | `ActionCatalog.hpp:64`; App `handleSingleHardwareInputAction` (diff hunk adds `if (action == "clear_hdr")`, calls `dispatch("set_clear_hdr")`) | `243fe2c` | adds one branch to upstream function |
| Click and hold gestures | Single, double, triple click and Hold on GPIO buttons, NeoRotary pushes, PCF pins, GPIO encoder pushes; Cinemate timing (click window 500 ms, long press 500 ms, hold 3000 ms) | `ButtonGesture.hpp`; `GpioInput.cpp:648-652`; `NeoRotary4Input.cpp:547,624-642`; `Pcf8574Input.cpp:400,452-466` | `0a98868`, `c140c4f` | new; upstream has only `PowerButtonGesture.hpp` (standby button) |
| 1-0-1 (normally closed) buttons | A pin that reads pressed at start is treated as wired the other way round | `Pcf8574Input.cpp` (`invertedMask`, `haveSample`), GpioInput (same idea) | `0a98868`, `c140c4f` | new |
| Edge-event GPIO input | Input thread sleeps in `poll()` on kernel edge events; no 12 ms poll; `poll_ms` only on chips without edge events | `GpioInput.cpp:744,822-856`; `ButtonGesture::nextWakeMs` | `0c49601` | rewrites upstream polling loop |
| `[gpio_switches]` | Two-way (one pin) and three-way (two pins) switches, an action per position, applied at start | `GpioInput.cpp:271,294,317,444,454`; rows in `ControlsModel.hpp:150-172` | `c34f844` | new section; shares chip/pull/active_low/debounce with `[gpio_buttons]` |
| Remote-only buttons | `remote<N>` key in `[gpio_buttons]` with no pin; runs from WebUI Remote controls; GpioInput skips the key | `ControlsModel.hpp:141-149,204`; WCP:17290 | `9b5ea14` | new |
| Controls rows model | `get_controls` returns `model` (sections, rows with lines, `can_add`, `kind`, `keys`, `base`, `gestures`, `gpio_pins` used/free) | `ControlsModel.hpp:132-388` (`controlRows`, `modelJson`, `gpioPinsInUse`); App:12439 | `07afbc6` and later | new |
| Peripheral settings spec | Settings the Controls page edits per peripheral, with default shown when key missing | `ControlsModel.hpp:245-333` (`peripheralSettings`, `peripheralSettingsJson`) | `166cc4d` | new; defaults hard-coded here beside the readers' own defaults |
| Peripheral status cards | "what is detected": GPIO chip + who holds each header line; I2C device found / missing / kernel driver; CFexpress hat + NVMe link summary; tally and trigger status | `ApertarCoreApp.cpp:11969-12186` (`gpioPeripheralJson`, `i2cPeripheralJson`, `nvmeDriveSummary`, `cfeHatPeripheralJson`, `outputPeripheralJson`, `i2cBusesJson`); `GpioChipInfo.*`, `I2cProbe.*` | `166cc4d`, `0a98868`, `c34f844`, `dcf09ee` | new |
| `scan_i2c` | Scan a bus for answering addresses, tag Core-held and kernel-held, guess names | `ApertarCoreApp.cpp:12486-12533` | `dcf09ee` | new |
| Pin map hints | "pins in use / free" 4..27 on the page; pins a DPI display holds greyed | `ControlsModel.hpp:218-242,372-387`; `facts.dpiLines` in get_controls | `07afbc6`, `9b5ea14` | new |
| `test_input`, `test_output`, Listen | Try buttons run a control's saved action; one tally blink / trigger pulse; Listen shows the last control that fired | `ApertarCoreApp.cpp:12380-12411 (testInputReply)`, `12476`, `12745`; seen-callbacks in NeoRotary4Input, `TriggerOutput::testPulse` | `dcf09ee`, `1319967` | new |

## 3. Commands, routes, state, events, config keys, files

| Item | Kind | Where @cinemate-port | Added / changed | Note |
| --- | --- | --- | --- | --- |
| `list_actions` | socket command, read-only hardware | `ApertarCoreApp.cpp:12534`; listed in `commands` reply at `:12930` | added | body = `catalogJson()` members + `values` (iso, shutter_angle, shutter_speed, wb, fps, resolution), `values_for`, `gestures` |
| `get_controls` | socket command | `:12420` | changed (adds `model`, `peripherals`, `i2c_buses`, `apply`, `dpi_lines`) | the `get_controls` command itself is from the earlier Controls work (`f5a61b8`); this unit adds `model` and `peripherals` |
| `set_controls` | socket command | `:12763` | changed: single-key edits `set.<section>.<key>=`, `unset.<section>.<key>`, `unset.<section>` (commit `07afbc6`) | whole-file `text=` path is earlier (`f5a61b8`) |
| `scan_i2c` bus= | socket command | `:12486` | added | refuses during a take |
| `test_input` section= key= | socket command, before command lock | `:12565`, `testInputReply` `:12391` | added | goes through `handleHardwareInputAction(line.raw, wake)` |
| `test_output` which= | socket command | `:12745` | added | `recording_indicator` or `trigger_output` |
| `controls_history`, `controls_last_input` | socket commands | `:12458`, `:12476` | added (earlier Controls units; listed because the model feeds them) | |
| Reply fields in `get_controls.controls.model` | JSON | `ControlsModel.hpp:336` | added | nested arrays / objects (not flat scalars) |
| `peripherals[].status.chip` | JSON | `ApertarCoreApp.cpp:11996-11999` | added | `{ok,path,label,lines,error}` and `pins[]` with `core` flag |
| State fields | `controls_errors`, `controls_warnings` | `:9458`, `:12947` | added by earlier unit (`4d80a35`) | not this unit |
| Events | `hardware_action` event existing upstream (publishEvent at `:10679`) | unchanged | | `ui=true` rows in `kSpecs` mirror it |
| HTTP routes | none in this unit | | | `/api/config` belongs to another unit |
| Config keys read by this unit's code | `[gpio_buttons] chip, enabled, active_low, pull, debounce_ms, dN, dN_single/_double/_triple/_hold, remoteN*`; `[gpio_switches] enabled, switchN_pins, switchN_off/_on, switchN_position0/1/2`; `[neorotary4] encoderN_cw/_ccw/_press/_single/_double/_triple/_hold`; `[pcf8574] pinN, pinN_single/_double/_triple/_hold`; `[gpio_encoders] encoderN_a/_b/_press_gpio/...`; `[cfexpress_hat] bus, address, enabled` | `ControlsModel.hpp`, `GpioInput.cpp`, `Pcf8574Input.cpp`, `NeoRotary4Input.cpp` | added | file is `~/apertar-hardware.conf` (as upstream) |
| Env vars | none | | | confirmed: no `getenv` in the 7 scope files |
| Files on disk | none written by scope files. Reads `/dev/gpiochip0..9`, `/dev/i2c-N`, `/sys/bus/i2c/devices`, `/sys/class/nvme`, `/sys/block/*n1/size` | `GpioChipInfo.cpp`, `I2cProbe.cpp`, App `:12160`, `:12080` | added | writing the config file is `HardwareConfigStore` (another unit) |
| UI elements | rows per GPIO button / switch / knob / PCF pin / encoder; Press/Single/Double/Triple/Hold lines with action dropdowns; "+ Add" for gestures; remove row; Try, Listen, Test buttons; Hardware cards (GPIO, NeoRotary 4, PCF8574, Grove, CFexpress hat, Tally LED, Trigger output); I2C scan | WCP only (a consumer of `get_controls`); `WebControlPage.cpp:17290` mentions ControlsModel. No Qt UI use found in this unit | `166cc4d`, `b74b4aa`, `1319967`, `9b5ea14` | UI side belongs to the WebUI unit |

## 4. Original code regions modified by this unit

| Region (upstream path) | Change | Kind | Commit |
| --- | --- | --- | --- |
| `GpioInput.cpp` `normalizeSingleAction` (upstream :108-202, ~95 lines) | removed; `normalizeAction` calls `hardware::actions::canonicalAction` | removed / moved to `ActionCatalog.hpp` | `916c1dd` |
| `NeoRotary4Input.cpp` `normalizeSingleAction` (upstream :121-215) | same | removed / moved | `916c1dd` |
| `Pcf8574Input.cpp` `normalizeSingleAction` (upstream :140-242) | same; keeps a local `normalizeAction` wrapper | removed / moved | `916c1dd` |
| `GroveAnalogInput.cpp` analog-target normaliser | body replaced by `canonicalAnalogTarget` | rewritten (delegates) | `916c1dd` |
| `TriggerOutput.cpp` event token matching (`record/still/timelapse/...`) | replaced by `canonicalTriggerEvent` | rewritten | `916c1dd` |
| `RecordingIndicatorOutput.cpp` `isRecordingOutputAction` | delegates to `hardware::isOutputAction` (in unchanged `ButtonActionList.hpp`) | extended / delegated | `916c1dd` |
| `GpioInput.cpp` `gpioChipScore` (upstream :244-) | removed; now `hardware::gpioChipScore` in `GpioChipInfo.cpp` | moved (body identical in logic; adds `lowered()` helper) | `166cc4d` |
| `TriggerOutput.cpp:195` and `RecordingIndicatorOutput.cpp:191` `gpioChipScore` | NOT touched: still local copies | unchanged | |
| `GpioInput.cpp` read loop | edge events with `poll()`, `ButtonGesture`, gesture and switch drafts | rewritten | `0a98868`, `0c49601`, `c34f844` |
| `GpioInput.cpp` section parser | adds `[gpio_switches]`, per-pin `buttonDrafts` map | extended in place | `c34f844`, `0a98868` |
| `GpioInput.cpp` start check (`buttons.empty() && encoders.empty()`) | also checks `switches` | behaviour-changed | `c34f844` |
| `NeoRotary4Input.cpp` press handling | edge pressed-mask `changedMask` loop replaced by `ButtonGesture` per knob; `heldAtStartMask`; `seenCallback_` | rewritten | `c140c4f`, `dcf09ee` |
| `Pcf8574Input.cpp` pin parsing | key suffix split `_single/_double/_triple/_hold`; `pinMapped`, `hasMappedAction` take gesture array | extended | `0a98868`, `c140c4f` |
| `TriggerOutput` | adds `testPulse()` | extended | `dcf09ee` |
| `ApertarCoreApp.cpp` `hardwareActionSuffix` / `parseHardwareActionNumber` (upstream :1342-1366) | now 2-line wrappers over `hardware::actions::suffixAfter/numberAfter` | moved; behaviour-changed: `strtod` with ERANGE refusal, inf/nan refused (`ActionCatalog.hpp:146-155`); upstream used `parseDoubleValue` | `916c1dd` |
| `ApertarCoreApp.cpp` `handleSingleHardwareInputAction` (upstream ~:8499-8800) | `clear_hdr` branch added; unknown-action log adds "Did you mean" | extended in place | `243fe2c`, `916c1dd` |
| `ApertarCoreApp.cpp` `handleCommand` (upstream flat chain) | adds `handleReadOnlyHardwareCommand` call before the command lock (`:12562`) and `test_input` before the lock (`:12565`) | extended; adds a path outside the one mutex | `f5a61b8` area, `dcf09ee`, `1319967` |
| `ApertarCoreApp.cpp` `canonicalAnalogTarget` helper (`:10090`) | delegates to catalog | moved | `916c1dd` |

## 5. New abstractions

| Name | Purpose | Upstream equivalent | Used by |
| --- | --- | --- | --- |
| `apertar::hardware::actions` (`ActionCatalog.hpp`) table `kSpecs` with `Spec{id,group,label,aliases,sources,ui,arg,token}`, `Arg` enum, `classify()` (declared, not called by drivers; confirmed grep: only `catalogJson`, `suggestion`, `canonicalAction` etc. used) | one alias table + UI labels + parameter families | per-class `normalizeSingleAction` if-chains (3 copies) and `handleSingleHardwareInputAction` string compares (`ApertarCoreApp.cpp:8499-8800 @upstream`); `ButtonActionList.hpp` holds only token helpers and the 6-action limit | all four input drivers, TriggerOutput, App, HardwareConfigText validator |
| `apertar::hwconf` `ControlRow`, `ControlLine`, `SettingSpec` (`ControlsModel.hpp`) | rows the page draws from file text | none: upstream has no page for hardware file | `get_controls`, `testInputReply` |
| `ButtonGesture` class | click counter state machine, fed with ms clock | `PowerButtonGesture.hpp` (standby button only; different timings) | GpioInput, NeoRotary4Input, Pcf8574Input |
| `GpioChipInfo` / `readGpioChipInfo` / `headerGpioChipPath` | read-only chip and line info; "auto" pick | `gpioChipScore` + `/dev/gpiochip0..9` loop copied in GpioInput, TriggerOutput, RecordingIndicatorOutput | GpioInput (score only), App `gpioPeripheralJson` |
| `I2cProbe` / `probeI2cAddress` | one-byte read probe, EBUSY = kernel driver | none; upstream drivers open their own bus and report errors | App `i2cPeripheralJson`, `cfeHatPeripheralJson`, `scan_i2c` |
| Header-only "pure" modules with JSON built by `std::string +` (`modelJson`, `peripheralSettingsJson`) | JSON for the page | App builds JSON with `ostringstream` / `okReply` strings | App |
| Duplicate: `hwconf::jsonEscape` (`ControlsModel.hpp:50`) | JSON escape | `escapeJson` in App (used on same files) | ControlsModel |
| Duplicate: `normalizeToken` in `ActionCatalog.hpp:89` | token normaliser | `normalizeToken` local per driver; `actionToken` in `ButtonActionList.hpp:42` | catalog, HardwareConfigText (`using`, line 22) |

## 6. Chip definition: upstream vs port (confirmed)

| Aspect | Upstream 1.6.0 | Port |
| --- | --- | --- |
| Config key | `chip=` / `gpiochip=` / `gpio_chip=`, `[gpio_buttons]` and `[gpio_encoders]` (`GpioInput.cpp:431 @upstream`); `[trigger_output]` (`TriggerOutput.cpp:311`), `[recording_indicator]` (`RecordingIndicatorOutput.cpp:319,347`) | same readers (`GpioInput.cpp:343`, `TriggerOutput.cpp:305`, `RecordingIndicatorOutput.cpp:312,340`); validator canonicalises `gpiochip`/`gpio_chip` to `chip` (`HardwareConfigText.hpp:172`); known key (`:457`, `:476`) |
| Default | `auto`; default file text `gpiochip=auto` (`ApertarCoreApp.cpp:4380,4394 @upstream`, `:5168,5182 @port`) | same |
| "auto" | scan `/dev/gpiochip0..9`, sort by score, try each (`GpioInput.cpp:507-535 @upstream`) | same in GpioInput (`:463-495`); `headerGpioChipPath()` (best score only) for the status card |
| Explicit chip | any path string passed to `open()` (`/dev/gpiochipN`) | same |
| Controls page | n/a | `peripheralSettings("gpio_buttons")` has no `chip` row; comment `ControlsModel.hpp:263`: "poll_ms (chips without edge events) and chip stay text-only: the Pi 5's header needs neither" |
| Output sections | | `peripheralSettings("recording_indicator"/"trigger_output")` lists `target, line, pcf_pin, active_high` only: no `chip`, no `open_drain` (both are validator-known keys, `HardwareConfigText.hpp:476`) |
| Status card | n/a | `gpioPeripheralJson` reads `chip` from file (`:11987`), shows chip path/label/line count and used header lines; `readGpioChipInfo(chipPath, 28)` caps at 28 lines |
| Shown chip path | | `chipSetting` is passed to `open()` unchanged; value `gpiochip4` (no `/dev/`) would fail to open in the card and in GpioInput |
| Free-pin list | n/a | fixed 4..27 (`ControlsModel.hpp:381`), independent of the chosen chip; `pin=` values >= 28 or a pin on another chip are not shown |
| Row identity | n/a | button row title is "GPIO <BCM pin>"; pin is not paired with a chip; `gpioPinsInUse` counts pins without chip |

Uncommitted: git status in `/home/user/Apertar-Core` is clean at `01f170c` (confirmed `git status --short` empty), so the chip row in the Controls page does not exist in the repo yet (task list says it is being re-inserted; not in this ref).

## 7. Narrowed, hidden or removed vs upstream

| What | Where | Effect |
| --- | --- | --- |
| `chip` setting not on Controls page for `[gpio_buttons]` (and `[gpio_encoders]`, `[gpio_switches]`, outputs) | `ControlsModel.hpp:263,264-271` | operator cannot pick a GPIO chip (MCU, expander, gpiochip4 on Pi 5) from the page |
| `poll_ms` for `[gpio_buttons]` not on page | same | no UI for chips without edge events |
| `open_drain` for tally and trigger not on page | `ControlsModel.hpp:264-271` | validator knows it, page cannot set it |
| `hold_ms`, `double_ms` accepted by validator (`HardwareConfigText.hpp:457,466,470`) but read by no driver (grep: only that file) | | keys that do nothing; Hold and click timing are constants in `ButtonGesture.hpp:23-25` |
| `[neorotary4] reset_on_start, max_events_per_poll` and `[grove_analog] emit_on_start` known to validator, not on page | `ControlsModel.hpp:278-303` | text-only |
| Action vocabulary: the `Arg` families (`iso{}`, `fps{}`, `wb{}`, `ev{}`, `shutter..`, `resolution..`) are listed but `kSpecs` entries with Arg are skipped for aliases and for `suggestion()` | `ActionCatalog.hpp:130,270` | typo in a family token gets no hint |
| `clear_hdr`, `standby` marked `Button` only (not rotation) | `ActionCatalog.hpp:64,80` | cannot be assigned to a knob turn in the catalog; `warnOnTurn` for record, photo, eject etc. |
| Section aliases `gpio`, `grove_digital`, `grove_buttons`, `grove_encoders` (upstream `GpioInput.cpp:407-410`) | `ControlsModel.hpp:340`, `controlRows` use `gpio_buttons`/`gpio_encoders` only | rows from alias sections: probable not shown (confirm: read `HardwareConfigText.hpp` section alias handling) |
| `NeoRotary4Input` per-poll `changedMask` press path | removed | press now through `ButtonGesture`; Press still fires at once |
| `ButtonActionList.hpp` | unchanged | unchanged: 6-action cap and output-action rule still enforced |

## 8. Board assumptions (confirmed unless noted)

| Assumption | Where | Detail |
| --- | --- | --- |
| Pi 5 RP1 first | `GpioChipInfo.cpp:42-47` | score: rp1 +100, bcm pinctrl +90, raspberrypi_exp -50, >= 28 lines +10. Same weights as upstream copy |
| gpiochip numbering 0..9 | `GpioChipInfo.cpp:60`, `GpioInput.cpp:469` | scan only /dev/gpiochip0..9 |
| 28 header lines | `ApertarCoreApp.cpp:11989` (`readGpioChipInfo(...,28)`), `ControlsModel.hpp:381` (pins 4..27, "2 and 3 are the I2C bus 1 lines") | a chip with more lines, or an MCU chip, is cut at 28 |
| I2C bus 1 default | `ControlsModel.hpp:281,290,299`, `ApertarCoreApp.cpp:12000` | NeoRotary 0x49, PCF 0x20, Grove 0x04 |
| I2C bus 10 for CFexpress hat | `ControlsModel.hpp:275`, `ApertarCoreApp.cpp:12097` | Pi 5 RP1 bus 10, address 0x34 |
| "does not exist on this Pi" text | `I2cProbe.cpp:20` | wording |
| PCIe NVMe | `ApertarCoreApp.cpp:12072 nvmeDriveSummary`: `/sys/class/nvme/*/transport == pcie`, link speed, `n1` partition size | CFexpress hat card |
| Known-address names | `ApertarCoreApp.cpp:12504-12508`: 0x1a "IMX585 / IMX283 sensor", 0x34, 0x40..45 INA219, 0x68/69 gyro | Apertar sensor and parts |
| `/sys/bus/i2c/devices` used because `/sys/class/i2c-adapter` missing "on this kernel" | `:12169` | kernel-specific |
| DPI display lines | `get_controls` `dpi_lines` (`HardwareConfigText` facts) | pins held by `dtoverlay=vc4-kms-dpi...` |
| Four cores, RAM, fan | not referenced in this unit | |
| Pi 4 / CM4 | chip score covers bcm2711 and bcm2835; bus 10 hat default is Pi 5-only (probable: bus 10 absent on Pi 4) | |

## 9. Open items for later stages

| Item | Why |
| --- | --- |
| `gpioChipScore` still copied in `TriggerOutput.cpp:195` and `RecordingIndicatorOutput.cpp:191` | port made a shared one but left two callers on copies |
| Defaults in `peripheralSettings` repeat each reader's own defaults (e.g. poll 30/40/80, debounce 60, bus 10) | change in one place not seen by the other; verify against `NeoRotary4Input.hpp`, `Pcf8574Input.hpp` |
| `ActionCatalog::classify()` and `Arg` families | check whether called outside `HardwareConfigText` validator |
| `hold_ms`, `double_ms` keys accepted, ignored | confirm in `HardwareConfigText.hpp` validator text |
| Non-scalar JSON (`model`, `peripherals`, `values`) in socket replies | brief says upstream replies are flat scalars; compare in stage 2 |
