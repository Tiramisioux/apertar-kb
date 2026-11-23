# Inventory: HW-input-classes (stage 1, no judging)

Scope diff: `git -C /home/user/Apertar-Core diff --minimal origin/main cinemate-port -- <11 files>`, saved at `/home/user/build/review/HW-input-classes.diff` (1865 lines, read fully). Refs: `@main` = origin/main, `@port` = cinemate-port `01f170c`, `@upstream` = upstream-1.6.0 worktree. All claims confirmed in code unless marked.

Commits touching the scope (`git log --reverse origin/main..cinemate-port -- <file>`), fork-log status (all "fork-only"; fork-log.md lines 105-129):

| Commit | Subject | Fork-log status / tested |
| --- | --- | --- |
| `916c1dd` | T36 ActionCatalog.hpp, list_actions | fork-only; commit: "desk only (host test 20 of 20); Pi build not yet run" |
| `c509e9f` | T37 part 2: IMU config writes through the store | fork-only; "pi (apertar.local) Core builds; nothing to try on the camera (no gyro on this rig)" |
| `166cc4d` | Controls part 3: GPIO buttons as peripheral (GpioChipInfo moves chip scoring) | fork-only; "pi: real chip and pins in get_controls; page in Chrome mock 26/26" |
| `0a98868` | T44 clicks and hold on GPIO buttons, 1-0-1, I2C detected | fork-only; "desk only (click counter 8 checks...); Pi build is first compile" |
| `0c49601` | GPIO inputs wait for edge events | fork-only; "desk (gesture fed only at edges); pi build" |
| `c34f844` | `[gpio_switches]` two/three-way switches | fork-only; "desk (host 118/119); pi build" (compile only) |
| `c140c4f` | T44 clicks/hold on NeoRotary pushes, PCF pins, GPIO encoder pushes | fork-only; "desk (host 120/121); pi build" |
| `dcf09ee` | T39/T40/T42 apply without restart, Listen, history, scan_i2c, test_output | fork-only; "desk (host 120/121); pi build" |

No commit says it was tested on real buttons, switches, a PCF8574 or a NeoRotary. Only 166cc4d reports reading the real GPIO chip on a Pi. Edge-event mode (0c49601) has no reported hardware test.

## 1. Per-file change map

| File | Diff size | What changed | Feature | Commits |
| --- | --- | --- | --- | --- |
| GpioInput.cpp | +~290/-~220 (508 lines) | `normalizeSingleAction` (98 lines) and `gpioChipScore` removed; config parse for gesture suffixes, `[gpio_switches]`; `run()` rewritten from poll loop to edge-event loop with `process` lambda, `sleepMs` lambda, `RuntimeSwitch`; 1-0-1 inversion; seen callback | gestures, switches, edge events, 1-0-1, Listen, shared catalog | 916c1dd, 166cc4d, 0a98868, 0c49601, c34f844, c140c4f, dcf09ee |
| GpioInput.hpp | +48 | `ButtonMapping` gets single/doubleClick/triple/hold; `SwitchMapping`; `EncoderMapping` gets pressSingle/Double/Triple/Hold, index; `RuntimeButton` gets gpio, inverted, seenKey, pressSuffix, observedChangedAt, ButtonGesture; `RuntimeSwitch`; `setSeenCallback`; `requestLines(..., bool edges, ...)` | same | 0a98868, 0c49601, c34f844, c140c4f, dcf09ee |
| Pcf8574Input.cpp | 184 | local `normalizeSingleAction` (~100 lines) removed, `normalizeAction` routes to catalog; `pinN_single/_double/_triple/_hold` keys; 1-0-1 invert mask; per-pin ButtonGesture; seen callback | gestures, 1-0-1, Listen, catalog | 916c1dd, c140c4f, dcf09ee |
| Pcf8574Input.hpp | +7 | `gestureActions[8][4]`, `setSeenCallback`, `seenCallback_` | same | c140c4f, dcf09ee |
| NeoRotary4Input.cpp | 146 | local `normalizeSingleAction` removed; `encoderN_single/_double/_triple/_hold`; per-push ButtonGesture; `heldAtStartMask`; seen callback for turns and pushes | gestures, Listen, catalog | 916c1dd, c140c4f, dcf09ee |
| NeoRotary4Input.hpp | +7 | `EncoderActions` gains single/doubleClick/triple/hold; `setSeenCallback` | same | c140c4f, dcf09ee |
| GroveAnalogInput.cpp | 20 | `normalizeTarget` body replaced by `hardware::actions::canonicalAnalogTarget` (same alias list moved) | shared catalog | 916c1dd |
| TriggerOutput.cpp | 29 | `eventFromToken` alias lists replaced by `canonicalTriggerEvent`; new `testPulse()` | catalog, output test | 916c1dd, dcf09ee |
| TriggerOutput.hpp | +1 | `void testPulse()` | output test button | dcf09ee |
| RecordingIndicatorOutput.cpp | 11 | `isRecordingIndicatorAction` body replaced by `hardware::isOutputAction(...)` (function already in `ButtonActionList.hpp` @main) | shared catalog | 916c1dd |
| Mpu6050RecordingSession.cpp | +46/-257 net -257 | two file-rewriting helpers replaced by store calls; see section 5 | IMU config through store | c509e9f |

## 2. Operator-visible features touching this unit

| # | Feature | What the operator gets | Files | Commits |
| --- | --- | --- | --- | --- |
| F1 | Click and hold gestures on GPIO buttons | `dN_single`, `dN_double`, `dN_triple`, `dN_hold` besides `dN` (press fires at once). Single/Double/Triple fire 0.5 s after last release; a press held 0.5 s is no click; Hold at 3 s. Cinemate SmartButton timing | GpioInput, ButtonGesture.hpp | 0a98868 |
| F2 | Gestures on GPIO encoder pushes | `encoderN_single/_double/_triple/_hold` in `[gpio_encoders]` | GpioInput | c140c4f |
| F3 | Gestures on NeoRotary4 pushes | `encoderN_single/...` in NeoRotary4 section | NeoRotary4Input | c140c4f |
| F4 | Gestures on PCF8574 pins | `pinN_single/_double/_triple/_hold` | Pcf8574Input | c140c4f |
| F5 | 1-0-1 (normally closed) buttons | A GPIO button, encoder push or mapped PCF pin that reads pressed at start is taken as inverted; journal line on stderr | GpioInput, Pcf8574Input | 0a98868, c140c4f |
| F6 | Edge events instead of polling | GPIO input sleeps in `poll()` until an edge, a debounce settling or a gesture timer; falls back to `poll_ms` reading if the chip gives no edges | GpioInput | 0c49601 |
| F7 | Two- and three-way switches | `[gpio_switches]`: `switchN_pins=17` + `switchN_off/_on` (or `_position0/_position1`); `switchN_pins=22,23` + `_position0/1/2`. Position applied once at start and on each debounced change | GpioInput | c34f844 |
| F8 | Listen (what is this control) | every press, click, hold, turn and switch move calls `seenCallback_("section|key")`; App turns it into `controls_last_input` for the WebUI | GpioInput, NeoRotary4Input, Pcf8574Input | dcf09ee |
| F9 | One action vocabulary | Same aliases, now served by `ActionCatalog.hpp`; an unknown action logs a "Did you mean" line; `isoinf`/`isonan` refused (commit text) | all input classes, Grove, Trigger, tally | 916c1dd |
| F10 | Trigger output Test button | `TriggerOutput::testPulse()`: one pulse regardless of `events=`; only if enabled and running | TriggerOutput | dcf09ee |
| F11 | IMU config saves serialised and versioned | level reference set/clear, gyro calibration, driver, orientation, sync offset writes now go through `HardwareConfigStore`: one lock, one atomic write, one history entry per call; always write the editable path | Mpu6050RecordingSession | c509e9f |
| F12 | Chip choice shared | `chip=auto` scoring moved to `GpioChipInfo.cpp` so GpioInput and the Controls page pick the same chip | GpioInput, GpioChipInfo | 166cc4d |

## 3. Interfaces, config keys, state, files (as touched in this unit)

Socket commands, HTTP routes, state fields and UI elements are not defined in these 11 files. They are reached through callbacks. The classes expose callbacks; App/web code wires them (outside scope).

| Kind | Name | Defined where | Note |
| --- | --- | --- | --- |
| callback | `GpioInput::setSeenCallback`, `NeoRotary4Input::setSeenCallback`, `Pcf8574Input::setSeenCallback` | GpioInput.hpp, NeoRotary4Input.hpp, Pcf8574Input.hpp | wired `ApertarCoreApp.cpp:8118-8120 @port` to `noteInputSeen(key)`; feeds socket `controls_last_input` (`ApertarCoreApp.cpp:12476 @port`) |
| callback key format | `gpio_buttons\|dN`, `...\|dN_single/_double/_triple/_hold`, `gpio_encoders\|encoderN_cw/_ccw/_press/_single...`, `gpio_switches\|switchN_on/_off/_positionP`, `neorotary4\|encoderN_cw/_ccw/_press/...`, `pcf8574\|pinN[...]` | GpioInput.cpp, NeoRotary4Input.cpp, Pcf8574Input.cpp | pipe-joined string; section and key |
| class method | `TriggerOutput::testPulse()` | TriggerOutput.hpp/.cpp | called by socket `test_output` (App, outside scope; `test_output` listed in command list `ApertarCoreApp.cpp:12930 @port`) |
| socket commands touched indirectly | `get_controls`, `set_controls`, `list_actions`, `controls_last_input`, `controls_history`, `scan_i2c`, `test_output` | App (outside scope) | all added by commits above; belong to other inventory units |
| config key (apertar-hardware.conf) | `[gpio_buttons]` `dN_single`, `dN_double`, `dN_triple`, `dN_hold` | GpioInput.cpp loadConfig | gesture suffix stripped from key, merged per GPIO into one `ButtonMapping` |
| config key | `[gpio_encoders]` (alias `grove_encoders`) `encoderN_single/_double/_triple/_hold` | GpioInput.cpp | alongside existing `_press` |
| config section + keys | `[gpio_switches]`: `enabled`, `switchN_pins` (1 or 2 pins, 0-63), `switchN_off`/`_position0`, `switchN_on`/`_position1`, `switchN_position2` | GpioInput.cpp | N up to 2 digits; switches reuse chip, pull, active_low and debounce of `[gpio_buttons]` |
| config key | NeoRotary4 section `encoderN_single/_double/_triple/_hold` | NeoRotary4Input.cpp | |
| config key | PCF8574 section `pinN_single/_double/_triple/_hold` | Pcf8574Input.cpp | |
| config keys written by IMU code (through store) | section `imu`: `driver`, `sync_offset_ms`; driver section (`mpu6050` etc.): `orientation`, `level_reference_set`, `level_reference_orientation`, `level_accel_x/y/z`, `auto_calibrate_seconds`, `gyro_bias_x/y/z` | Mpu6050RecordingSession.cpp | same keys as @upstream; writer differs |
| files on disk | `~/apertar-hardware.conf` (default `/home/pi/apertar-hardware.conf`, override `APERTAR_HARDWARE_CONFIG`) written by IMU code; store history and notes dir `~/.config/apertar-core` (or `XDG_CONFIG_HOME`) | HardwareConfigStore.cpp:118-133 @port | IMU code previously wrote whichever path the loader found, plus `<path>.tmp` |
| env vars | none new in these files (store reads `APERTAR_HARDWARE_CONFIG`, existing name) | | |
| state fields | none defined here | | `controls_last_input`, applied/needs-restart etc. live in App |
| UI elements | none in these files | | WebUI Listen, Test, gesture dropdowns, Add switch are other units (commits 8be1ab5, fa3a798, b74b4aa) |

## 4. Regions of ORIGINAL code modified

| Where (@port, file:approx line) | What | Kind | Upstream reference |
| --- | --- | --- | --- |
| GpioInput.cpp:108-206 @upstream (`normalizeSingleAction`, `normalizeAction`) | 98-line alias chain deleted; `normalizeAction` calls `hardware::actions::canonicalAction` | moved (to ActionCatalog.hpp, shared) | upstream had one copy each in GpioInput.cpp:108, NeoRotary4Input.cpp:121, Pcf8574Input.cpp:140 |
| Pcf8574Input.cpp:140 and NeoRotary4Input.cpp:121 @upstream | same deletion | moved | |
| GpioInput.cpp:238 `gpioChipScore` @upstream | deleted, now `hardware::gpioChipScore` in GpioChipInfo.cpp | moved | copies remain in TriggerOutput.cpp:195 and RecordingIndicatorOutput.cpp:191 @port (not deduplicated); upstream had three copies (GpioInput:238, TriggerOutput:201, RecordingIndicatorOutput:198). One-line change: GpioChipInfo's copy normalises names with its own `lowered()` instead of `normalizeToken` (tiny behaviour-equal change; unconfirmed whether `normalizeToken` differs for the ids matched, probable no) |
| GpioInput.cpp `loadConfig` buttons branch | `config.buttons.push_back({gpio, action})` per `dN` key replaced by `buttonDrafts` map keyed by GPIO, pushed after the loop in GPIO order | rewritten; behaviour changed: buttons now ordered by GPIO number not file order; a GPIO with only gesture keys now counts as mapped |
| GpioInput.cpp `loadConfig` end | `config.enabled = buttonsEnabled \|\| encodersEnabled \|\| switchesEnabled`; empty-config check also counts switches | extended in place | |
| GpioInput.cpp `loadConfig` encoders | mapping index set; encoder with only gesture pushes now kept | extended in place | |
| GpioInput.cpp `requestLines`/`requestLinesFromChip` | new `bool edges` parameter, adds `GPIO_V2_LINE_FLAG_EDGE_RISING/FALLING` | extended in place | |
| GpioInput.cpp `run()` (about 640 lines region) | the 12 ms `sleep_for(pollMs)` polling loop replaced by `poll()` + `read(gpio_v2_line_event)` loop; button debounce moved into a `process` lambda; run-time table built before first sample; button press now flows through `ButtonGesture` (Press event) instead of direct `emitAction` on stable press | rewritten; behaviour changed: `poll_ms` used only when chip has no edge events; thread wakes on edge or timer; `stop()` noticed within 250 ms (`kIdleWakeMs`) instead of one poll; encoders step per edge in order, then an extra full-line read after every wake | `@upstream GpioInput.cpp:740` `sleep_for(pollMs)` |
| GpioInput.cpp `run()` button start sample | `observedPressed/stablePressed` seeded from first sample as "not pressed"; pressed-at-start now sets `inverted` and the button reads as released | behaviour changed: @upstream a button held at start with active level counted as already stable-pressed and never fired; @port it is treated as wired inverted | |
| GpioInput.cpp `run()` encoder block | variable `bits` renamed `levels`; adds seen callback on the accumulated step | extended in place | |
| GpioInput.cpp encoder push | encoder push became a `RuntimeButton` with gestures (before: `{lineIndex, press}` button) | extended in place; push now also emits Press through ButtonGesture | |
| Pcf8574Input.cpp `loadConfig` last else-if | `config.actions[pin] = ...` now strips gesture suffix, fills `gestureActions` | extended in place | |
| Pcf8574Input.cpp `run()` | `pressedMask` edge loop replaced by per-pin `ButtonGesture`; inversion mask computed on first sample | rewritten; behaviour changed (inverted pins; Press now through ButtonGesture) | |
| Pcf8574Input.cpp `hasMappedAction` | signature gains `gestureActions`; new `pinMapped` | extended in place | |
| NeoRotary4Input.cpp `hasMappedAction`, `loadConfig`, `run()` | gesture keys; edge loop replaced by per-push ButtonGesture; `heldAtStartMask` skips pushes held at open until released | rewritten (push block), extended (rest); behaviour changed: a push held at start no longer fires on release | |
| NeoRotary4Input.cpp turn handler | seen callback added; unconditional | extended in place | |
| GroveAnalogInput.cpp:125 `normalizeTarget` | body delegated to catalog | moved | |
| TriggerOutput.cpp:130 `eventFromToken` | alias lists delegated to catalog; result string compared to 4 ids | moved | |
| RecordingIndicatorOutput.cpp:118 `isRecordingIndicatorAction` | body delegated to `ButtonActionList.hpp::isOutputAction` (existing helper) | moved to an existing upstream helper | |
| Mpu6050RecordingSession.cpp:604-1000 `writeHardwareConfigValue`, `updateImuBiasConfig` | file read/modify/write bodies (~230 lines) replaced by store edits | rewritten | see section 5 |
| Mpu6050RecordingSession.cpp `calibrateConfiguredSensor`, `setConfiguredDriver/Orientation/SyncOffsetMs/LevelReference`, `clearConfiguredLevelReference` | signatures of helpers lose `configPath`; callers no longer compute config path; level set/clear are 1 store edit instead of 5 and 4 separate file rewrites | extended in place / behaviour changed: `result->configPath` reports store path, not loader path | |

## 5. Mpu6050RecordingSession.cpp: 257 lines lost, where they went

| Removed (@upstream lines) | Replaced by | Where it lives now |
| --- | --- | --- |
| `writeHardwareConfigValue(path, section, key, value, error)` (604-713): read lines, find section, replace or insert key, create dir, write `<path>.tmp`, rename, on failure `remove` then rename | `writeHardwareConfigValues(section, vector<pair>, error)` building `hwconf::Edit` list and calling `HardwareConfigStore::edit(currentRevision(), edits, "imu", flags{trusted=true})`; single-key `writeHardwareConfigValue` is a thin wrapper | Mpu6050RecordingSession.cpp:603-640 @port; the line-edit logic is `HardwareConfigText.hpp` (new, 1141 lines) and lock, revision, history, atomic write are `HardwareConfigStore.cpp` (new, 505 lines) |
| `updateImuBiasConfig(path, ...)` (715-~890): same file rewrite again, four keys | `writeHardwareConfigValues(section or "mpu6050", 4 pairs, error)` | same |
| per-call `Config config = loadConfig(); if (path.empty()) path = defaultHardwareConfigPath()` in 5 setters (`@upstream :1299, :1314` etc.) | removed; store owns the path | HardwareConfigStore::defaultPath |
| level set: 5 sequential `writeHardwareConfigValue` calls, level clear: 4 | one batch each | store |

Lines moved, not lost: the same job (edit one key in an INI-like file) is now done in `HardwareConfigText.hpp` + `HardwareConfigStore.cpp`, about +1650 lines new in the tree. Upstream `defaultHardwareConfigPath()` (Mpu6050RecordingSession.cpp:186) still used by the loader (lines 197, 1048, 1178 @upstream; unconfirmed that all still exist @port, run `grep -n defaultHardwareConfigPath` to settle).

Behaviour differences of the IMU write path:
- Always writes `~/apertar-hardware.conf` (store default path); upstream wrote whichever file the loader found (`/boot/firmware/apertar-hardware.conf`, `/boot/apertar-hardware.conf` or `/home/pi/...`, candidates at GpioInput.cpp:66-72 style list). If a Pi has the file in `/boot/firmware`, IMU writes @port go to `/home/pi`. Confirmed by commit text: "The store always writes the editable path, not whichever file the loader found."
- Trusted flag: IMU writes skip `checkEdits` validation.
- Each call makes one history entry (one per call, not "one per session" as commit text says; `store.edit(currentRevision(), ...)` per call). Commit text and code differ: unconfirmed which is right; read HardwareConfigStore history coalescing to settle.
- Error text changed: "Could not update hardware config <store path>: <result.error>".
- No `.bak` created. Passes `currentRevision()` read just before edit, so a concurrent write between the two can fail (not tested).
- Key written lowercased through `hwconf::canonicalKey`/`canonicalSection`: sections are now canonicalised (e.g. `imu` section name via `canonicalSection`), upstream used `normalizeToken` of the section name.

## 6. New abstractions seen from this unit

| Name | Kind | Purpose | Upstream equivalent | Used by |
| --- | --- | --- | --- | --- |
| `hardware::ButtonGesture` (`ButtonGesture.hpp`, 76 lines, header-only, pure) | class | click counter, long press, Hold, `nextWakeMs()` | none; upstream buttons fire press only. Cinemate `SmartButton` (`cinemate src/module/gpio_input.py`) is the model | GpioInput, Pcf8574Input, NeoRotary4Input |
| `hardware::actions` namespace (`ActionCatalog.hpp`, 360 lines at that commit, header-only, `Spec` table, `kSpecs[]`, `canonicalAction`, `canonicalAnalogTarget`, `canonicalTriggerEvent`, `suggestion` (edit distance), `catalogJson`) | header-only module | one alias table and parameterised-token classifier; serves `list_actions` | per-class `normalizeSingleAction` copies (GpioInput.cpp:108, NeoRotary4Input.cpp:121, Pcf8574Input.cpp:140 @upstream); Grove `normalizeTarget` (GroveAnalogInput.cpp:125); Trigger `eventFromToken` (TriggerOutput.cpp:130); App suffix parsers | all hardware classes, App |
| `hardware::gpioChipScore`, `headerGpioChipPath`, `readGpioChipInfo` (`GpioChipInfo.cpp/.hpp`) | free functions | chip scoring and read-only chip facts | `gpioChipScore` private copy in GpioInput.cpp:238, TriggerOutput.cpp:201, RecordingIndicatorOutput.cpp:198 | GpioInput, Controls model; Trigger and Recording still have private copies @port |
| `hardware::HardwareConfigStore` + `configStore()` singleton (`HardwareConfigStore.cpp/.hpp`) | class + global accessor | one writer for apertar-hardware.conf: lock, revision, history, atomic write | per-class write helpers (Mpu6050RecordingSession.cpp:604, :715) and App/other writers; no shared writer | IMU session, App, `/api/config` |
| `hwconf::` text module (`HardwareConfigText.hpp`, header-only, 1141 lines): `Edit`, `canonicalSection`, `canonicalKey`, validator | header-only module | line-based file edit and validation | none | store, IMU session |
| `GpioInput` internals: `RuntimeSwitch`, `process` lambda, `sleepMs` lambda, `buttonDrafts`/`switchDrafts` maps | local structures | edge loop plumbing | the fixed-interval loop with `RuntimeButton` | GpioInput only |
| seen-callback (`std::function<void(const std::string&)>`, `"section\|key"` string protocol) | callback pattern on three input classes | Listen | none; upstream callbacks are `actionCallback_`, `rotationCallback_` (GpioInput.hpp:17) | App `noteInputSeen` |
| Unit-test access `friend struct HardwareInputTestAccess` | already in @main (GpioInput.hpp:28 @main, not new) | | |

No new worker thread in these classes: GpioInput keeps its single thread (`thread_`), the edge loop runs on it. No helper script. The "controls worker" thread from dcf09ee is in App, outside scope.

## 7. Removed, narrowed or hidden compared to upstream

| What | Where | Effect |
| --- | --- | --- |
| `poll_ms` no longer used when chip supports edge events | GpioInput.cpp run | key kept in parse; still read in fallback (`config_.pollMs`). Commit c140c4f text: GPIO card settings drop poll and chip (WebUI hides them) |
| Button press ordering and a button held at start | GpioInput.cpp run | see section 4: held-at-start now becomes inverted button; upstream held-at-start counted pressed, no event |
| Button list ordered by GPIO, not file order | loadConfig | matters only for multi-action firing order across buttons; minor, probable no effect |
| Encoder push held at start (NeoRotary) | NeoRotary4Input.cpp | `heldAtStartMask`: no event on release; upstream emitted on next press only (equal), but now gesture counts differ |
| `gpioChipScore` use of `normalizeToken` | GpioChipInfo.cpp | replaced by local `lowered`; same results for the tested name fragments (unconfirmed for odd label characters) |
| Per-file action alias chains | three input classes | gone; any alias present in the old chains but missing from `kSpecs` would now pass through as unknown. Fork test claims 20/20 on the alias set; not re-verified here (unconfirmed; settle with a diff of all aliases against `kSpecs`) |
| `isoinf`, `isonan` | ActionCatalog | refused now (commit 916c1dd) |
| IMU writes to the file the loader found (`/boot/firmware/apertar-hardware.conf`) | Mpu6050RecordingSession.cpp | now only `~/apertar-hardware.conf` (see section 5) |
| `.tmp` sibling file and remove-then-rename write | Mpu6050RecordingSession.cpp | gone, store atomic write instead |
| Per-take stop of config rewrite | n/a | not changed in this unit |

## 8. Board and platform assumptions seen in this unit

| Assumption | Where (@port) | Evidence |
| --- | --- | --- |
| `chip=auto` scoring prefers labels containing `rp1` (+100) then `pinctrl_bcm`/`bcm2711`/`bcm2835` (+90), penalises `raspberrypi_exp` (-50), +10 for 28+ lines | GpioChipInfo.cpp:31-51; copies in TriggerOutput.cpp:195, RecordingIndicatorOutput.cpp:191 | code; same logic as @upstream, moved; covers Pi 5/CM5 (RP1) and Pi 4 style; chip numbers not hard-coded (loop `/dev/gpiochip0..9`, GpioInput.cpp:471 style) |
| `GPIO_V2` uAPI (kernel 5.10+) with edge flags | GpioInput.cpp requestLinesFromChip | code; a chip failing the edge request falls back to polling |
| pull-up/pull-down via uAPI flags per config `pull` | GpioInput.cpp:521 | existing |
| Debounce and gesture timing wall-clock (`steady_clock`), 500 ms / 3000 ms constants | ButtonGesture.hpp | Cinemate constants; fixed, not configurable |
| I2C bus numbers: from config `busNumber` and `address`, device path `/dev/i2c-N` | Pcf8574Input.cpp:275-278, NeoRotary4Input.cpp:314-317, TriggerOutput.cpp:626 | read from config; defaults not changed by the port; no bus number hard-coded in the diff |
| Config path `/home/pi/apertar-hardware.conf` (user `pi`) | HardwareConfigStore.cpp:122 | hard-coded default; override env `APERTAR_HARDWARE_CONFIG`; @upstream loader candidates also include `/boot/firmware/` and `/boot/` |
| Linux-only headers (`linux/gpio.h`, `poll.h`) | GpioInput.cpp | same as before |
| Pi 5 / CM5 only, four cores, PCIe, RAM size, fan | none in these files | not present |
| Input threads: one per class | unchanged | no change in core count assumption |

## 9. Open points for stages 2 and 3 (facts, not verdicts)

- Edge-event loop and gesture engine are tested "desk" plus Pi build only (compile). No hardware run recorded in fork-log for 0c49601, c34f844, c140c4f.
- Commit 916c1dd says Pi build "not yet run" at commit time; later commits report pi builds.
- `gpioChipScore` still exists in three places @port (one moved, two kept).
- Commit message of c509e9f says "one history entry per IMU session"; code makes one `store.edit` per helper call. Unconfirmed which history behaviour results.
- Three-way switch middle position and "both pins closed" (`-1`) are emitted nowhere (no action).
- Switch at start applies its action once without Listen; documented in a code comment.
- The hardware card/Listen/Test UI pieces in other units depend on `seenCallback_` strings defined here.
