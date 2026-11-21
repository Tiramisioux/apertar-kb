# Review: HW-controls-model (stage 2)

Refs: port = `cinemate-port` `01f170c` (`/home/user/Apertar-Core`), upstream = `upstream-1.6.0` (`/home/user/wt/core-upstream`),
improvement branch = `work/improve` (`04fe197`, `7dc6f7a`). `App` = `src/ApertarCoreApp.cpp`. Rule ids from
`raw/conv-hardware-config.md` (HW-*) and `raw/conv-core-command-plane.md` (C1-*). All claims confirmed (read in code)
unless labelled.

Scope read completely: `ControlsModel.hpp` (390), `ActionCatalog.hpp` (360), `ButtonGesture.hpp` (76),
`GpioChipInfo.hpp/.cpp` (35/110), `I2cProbe.hpp/.cpp` (17/39). Uses: `App:1645-1655`, `:10090`, `:10684`, `:11968-12141`,
`:12391-12415`, `:12420-12450`, `:12486-12560`; `GpioInput.cpp:114,343,463-495,612-652`; `Pcf8574Input.cpp:144,400,452-466`;
`NeoRotary4Input.cpp:125,547,624-642`; `TriggerOutput.cpp:133`; `GroveAnalogInput.cpp:128`; `HardwareConfigText.hpp:22,95,451-480,950-980`.

## Summary table

| Id | Title | Category | Sev | Deliberate | Effort |
| --- | --- | --- | --- | --- | --- |
| F1 | GPIO chip (and poll_ms) dropped from the Controls page | removed-upstream-behaviour | major | yes | S (done on work/improve) |
| F2 | Button wired "the other way" is guessed at start, overriding active_low | removed-upstream-behaviour / bug | major | yes | S |
| F3 | Upstream keys refused or hidden by the Controls path | removed-upstream-behaviour | minor | partly | S |
| F4 | `hold_ms`, `double_ms` accepted, read by nobody | bug / slop | minor | no | S |
| F5 | Alias table as a runtime string table instead of upstream's flat chains | mismatch | minor | yes | M |
| F6 | Trigger events and analog targets moved into the catalog with no consumer | mismatch | minor | yes | S |
| F7 | `classify()` is a second parser of the parametric action grammar | duplication / mismatch | minor | yes | M |
| F8 | `list_actions` serves fields nobody reads; `gestures` is wrong | slop / bug | minor | no | S |
| F9 | JSON built in the hardware header with its own escaper | mismatch | minor | no | S |
| F10 | Settings spec repeats each reader's defaults | duplication | minor | no | S |
| F11 | `remote<N>` keys in `[gpio_buttons]`, a section GpioInput owns | new-ground | minor | yes | M |
| F12 | `gpioChipScore` moved out of one of three files | duplication | minor | no | S |
| F13 | GPIO input sleeps on edge events instead of polling | new-ground | minor | yes | - (keep) |
| F14 | Cinemate references, ticket numbers and history in comments | slop | minor | no | S |
| F15 | Status probes read chips that UI-side readers poll | bug (probable) | minor | no | S |
| F16 | `get_controls` parses the file eight times per call | slop | nit | no | S |

## F1. GPIO chip (and poll_ms) dropped from the Controls page

- Port: `ControlsModel.hpp:257-263@cinemate-port` lists `enabled, active_low, pull, debounce_ms` and says
  `// poll_ms (chips without edge events) and chip stay text-only: the Pi 5's header needs neither`.
  Outputs (`:264-271`) list `enabled, target, line, pcf_pin, active_high`: no `chip`.
- Upstream: `GpioInput.cpp:431-432@upstream-1.6.0` `key == "chip" || key == "gpiochip" || key == "gpio_chip"`,
  shared by `[gpio_buttons]` and `[gpio_encoders]`; `TriggerOutput.cpp:311`, `RecordingIndicatorOutput.cpp:318,345`.
  HW-N3: chip is operator-configurable wiring; HW-I7: `chip=auto` default, explicit path skips the scan.
- History: `166cc4d` had the field ("on, active low, pull, debounce, poll, chip"); `c140c4f` dropped it. KB
  `working/controls/decisions.md:46`: "poll_ms and chip stay text-only (edge events need neither)". Deliberate, wrong premise:
  a pin on an MCU or expander chip needs `chip=`.
- Status: fixed on `work/improve` `04fe197` (fix-log C1): `chip` and `poll_ms` rows back for `gpio_buttons`, `chip`
  for both outputs, `gpioPinsInUse` skips sections on another chip, the card reads `gpioInputChip(doc)` and reads 64
  lines on a non-header chip. Same fix also closes two card bugs present at the port ref: card read `chip` only from
  `[gpio_buttons]` (`App:11987@cinemate-port`) while GpioInput also takes it from `[gpio_encoders]`
  (`GpioInput.cpp:343`); `chip=` empty became `""` and the card said "No GPIO chip found." while GpioInput used auto.
- Remaining (not fixed on improve): free-pin list fixed at 4..27 (`ControlsModel.hpp:381`) and line max 27 for outputs;
  the page lifts the limit in JS (fix-log C1), Core's model still does not know the chip's line count.

## F2. A button that reads pressed at start is inverted for the session

- Port: `GpioInput.cpp:622-629@cinemate-port`:
  `button.inverted = level;` ... `"reads pressed at start; taken as inverted (a 1-0-1 button)."`; same in
  `Pcf8574Input.cpp:425` (`invertedMask`) and NeoRotary (`heldAtStartMask`, inventory).
- Upstream: polarity is the operator's, per section: `active_low` (`GpioInput.cpp:433-434@upstream`,
  `Pcf8574Input.cpp:372`). No guessing. HW-N3 (wiring is stated in the file), HW-N7 (lenient, but never reinterprets).
- Failing input: any `[gpio_buttons] d17=capture`, operator holds the button while Core starts, or presses it while the
  controls worker restarts the GPIO group after a save (`dcf09ee`: saves apply without restart). From then on every
  release fires `capture` and a press does nothing, until the next restart. A stuck-closed contact is silently flipped.
- Deliberate: yes (`0a98868`: "inverts a button that reads pressed when it starts").
- Rework: delete the start-sample inversion in the three drivers (`haveSample`/`inverted`, `invertedMask`,
  `heldAtStartMask`). If normally-closed buttons on the same section as normally-open ones are needed, add a per-pin
  key the Apertar way (recipe R3: field in header `Config`, `else if` in `loadConfig`), e.g. `d17_active_low=false`,
  and a row field on the page.

## F3. Upstream keys refused or hidden by the Controls path

The text editor (Settings > Config) still writes anything, so nothing is lost for an operator who edits text.
But the key-edit path refuses some keys upstream reads, with a message that is wrong:

- `HardwareConfigText.hpp:460-462@cinemate-port` `knownKey("gpio_encoders")` = `enabled` + `encoderN_*` only. Upstream
  GpioInput reads `chip`, `active_low`, `pull`, `poll_ms`, `debounce_ms` in `[gpio_encoders]` too
  (`GpioInput.cpp:431-445@upstream`; the upstream UI template writes `poll_ms=3`, `debounce_ms=40` there,
  conv-hardware-config section 6). `set.gpio_encoders.poll_ms=3` -> "'poll_ms' is not a key of [gpio_encoders] that
  Apertar reads." (`:496-497`). False.
- `[trigger_output]`/`[recording_indicator]` `active_low` (reader `TriggerOutput.cpp:325`, `RecordingIndicatorOutput.cpp:363`)
  is not in `knownKey` (`:476`) and `canonicalKey` does not map it: refused the same way.
- Not on the page at all (text only): outputs `open_drain` (upstream Core template writes `open_drain=true`,
  `App:4382@upstream`), trigger `pulse_ms`, `events` (HW-N3 names "trigger events and pulse length" as operator
  settings), encoder `_invert`, `_steps_per_event`, NeoRotary `reset_on_start`, `max_events_per_poll`, Grove
  `emit_on_start`, and every Grove channel mapping `aN`, `aN_min/max/step/mode/presets`: `controlRows` makes no row for
  `[grove_analog]` (`ControlsModel.hpp:132-201`) although `modelJson` lists the section (`:340`).
- Rework: in `knownKey`, accept the shared keys in `[gpio_encoders]` and `active_low` in the outputs. Add `open_drain`
  (bool) to the outputs' `peripheralSettings`, and `pulse_ms`, `events` to the trigger's; the catalog's
  `kTriggerEvents` labels exist for this (`ActionCatalog.hpp:315`, comment "The Outputs card reads this list", no reader).
  Grove rows: either add them or state on the page that `[grove_analog]` channels are edited in Config.

## F4. `hold_ms`, `double_ms` accepted and ignored

- `HardwareConfigText.hpp:457,466,470@cinemate-port` list `hold_ms`, `double_ms` as known keys of `gpio_buttons`,
  `pcf8574`, `neorotary4`. `grep -rn "hold_ms\|double_ms" src` hits only that file. Timings are
  `ButtonGesture.hpp:16-18` constants.
- Failing input: `[gpio_buttons] hold_ms=1000` saves clean through `set_controls`; Hold still fires at 3 s.
- Rework: remove both from `knownKey` (HW-N3: behaviour timing fixed in code, like upstream `PowerButtonGesture` 80/500 ms).

## F5. Alias table as a runtime string table

- Port: `ActionCatalog.hpp:32-87` `kSpecs[]` with `aliases` as one comma string, matched by `listHas`
  (`:102-113`) in `canonicalAction` (`:123-132`). Drivers: `GpioInput.cpp:114`, `Pcf8574Input.cpp:144`,
  `NeoRotary4Input.cpp:125` `normalizeButtonMapping(action, hardware::actions::canonicalAction)`.
- Upstream: `GpioInput.cpp:108-202@upstream` flat chain
  `if (action == "record" || action == "capture" || action == "camera_button" || action == "take") return "capture";`,
  copied in `Pcf8574Input.cpp:140-242`, `NeoRotary4Input.cpp:121-215`. HW-I1 (aliases in flat `||` chains; violation
  "a lookup table/map of aliases"), HW-I5, HW-S2 ("refactoring the copies away unasked").
- Behaviour: alias sets compared line by line: identical; unknown tokens pass through as upstream. Good.
- Weighing: the sharing itself has an upstream seed (`ButtonActionList.hpp` is already shared by all inputs) and the
  owner's maintainer would likely accept one copy instead of three. The foreign part is the shape: a struct table with
  CSV strings, `Arg` families, `Source` bit flags, `ui` flags and labels in one row.
- Rework (simplify): move one `normalizeSingleAction(std::string)` into `ButtonActionList.hpp` beside
  `normalizeButtonMapping`, written as upstream's flat `if` chain (copy `GpioInput.cpp:108-202@upstream` verbatim),
  and let the three drivers call it (their local copies deleted, as now). Keep `kSpecs` only as the WebUI label list
  `{id, group, label, sources}` (no `aliases`, no `Arg` rows; see F7/F8). Delete `ActionCatalog::normalizeToken`
  (`:89-100`) and give `HardwareConfigText.hpp:22` its own file-local copy, as every hardware file has (HW-S2).

## F6. Trigger events and analog targets moved for no consumer

- Port: `TriggerOutput.cpp:131-143@cinemate-port` `eventFromToken` = `canonicalTriggerEvent(token)` (string id) then
  four `if (event == "...")` to the enum. Upstream `TriggerOutput.cpp:130-148@upstream` maps token -> enum directly,
  same aliases. `GroveAnalogInput.cpp:128` delegates to `canonicalAnalogTarget` (upstream `normalizeTarget`
  `GroveAnalogInput.cpp:125-145@upstream`; App had the second copy `App:8410-8432@upstream`).
- `kTriggerEvents` and `kAnalogTargets` reach the wire only in `list_actions` (`catalogJson`, `:351-355`); the WebUI reads
  only `catalog.actions` (`WebControlPage.cpp:16750,16822,16876,17986,18434`), the touch UI never sends `list_actions`.
- Rework (rework-to-upstream-pattern): restore upstream `eventFromToken` and `normalizeTarget` bodies (zero diff in
  `TriggerOutput.cpp`, `GroveAnalogInput.cpp`); drop `kTriggerEvents`, `canonicalTriggerEvent`, `kAnalogTargets` from the
  catalog unless F3's trigger `events` row is built, then keep only the label list.
  App's `canonicalAnalogTarget` (`App:10090`) may keep calling the Grove copy's twin as upstream did (two copies upstream).

## F7. `classify()` is a second parser of the parametric grammar

- Port: `ActionCatalog.hpp:180-246` re-parses `ev`, `fps`, `resolution`, `iso`, `shutter...s`, `shutter_angle`,
  `shutter_speed`, `shutter`, `wb` and restates Core's rules in text ("Core clamps ... to 2500..8000 K",
  `:240-243`, App clamp at `App:10431-10435`). The executing parser stays in `App:10355-10440`
  (`parseHardwareActionNumber` etc.). Used only by the validator `HardwareConfigText.hpp:965`.
- Upstream: HW-I5 "parametric names are parsed only in the handler"; violation "validating action names at config load".
  HW-N7 lenient: unknown actions are logged at run time (`App:8954@upstream`).
- Risk: the validator marks an unknown action as an error (`add(line.number, true, "unknown_action", ...)`,
  `:967-968`) and a new error blocks a save. When the two parsers drift, a mapping Core would run cannot be saved from
  the page. No diverging input found today (probable equal; compared branch order and suffix handling).
- Also: `App:1645-1655` now wrap `actions::suffixAfter/numberAfter` through `prefixViews`, copying a
  `vector<string>` into `vector<string_view>` per call (also rev-App-1 F21); upstream had the body in App
  (`App:1342-1370@upstream`).
- Rework (simplify): keep the parametric parsers in App as upstream (restore `hardwareActionSuffix` /
  `parseHardwareActionNumber` bodies from `App:1342-1370@upstream`); drop `classify()`, `compact()`, `number()`,
  `numberAfter()`, `suffixAfter()`, `Classified` from the catalog. The validator then flags only tokens that are neither
  a catalog id nor start with a parametric prefix (`iso`, `fps`, `wb`, `ev`, `shutter`, `res`), as a warning, not an
  error (HW-N7).

## F8. `list_actions` serves fields nobody reads; `gestures` is wrong

- `App:12534-12560@cinemate-port`: `values` (six option lists computed from sensor and UI.conf), `values_for`,
  `gestures`, plus catalog `analog_targets`, `trigger_events`, `max_per_mapping`. WebUI caches the reply once
  (`WebControlPage.cpp:18265`: `controlsState.catalog ? Promise.resolve(null) : controlsCall({cmd:"list_actions"})`)
  and reads only `actions`. No reader in Apertar-UI.
- `"gestures":{"button":["press"],...}` is false since `0a98868`: buttons carry single, double, triple, hold.
- Rework: reply `"actions":[...]` only (plus `max_per_mapping` if the page enforces it); delete the `values`,
  `values_for`, `gestures` block. Add `list_actions` to the `commands` list is already done (`:12930`, C1 R2 step 5).

## F9. JSON built in the hardware header with its own escaper

- Port: `ControlsModel.hpp:50-71` `jsonEscape`, `:307-333` `peripheralSettingsJson`, `:336-388` `modelJson`, all
  `std::string +` concatenation. `ActionCatalog.hpp:336-358` `catalogJson` uses `ostringstream`.
- Upstream: C1-I08 "JSON is written by hand with `std::ostringstream`; `escapeJson`" in App (`App:167-215@upstream`).
  The port's own `gpioPeripheralJson` (`App:11993-12014`) follows that rule; ControlsModel does not.
- Rework (rework-to-upstream-pattern): `ControlsModel.hpp` returns data only (`controlRows`, `gpioPinsInUse`,
  `peripheralSettings`). Move `modelJson` and `peripheralSettingsJson` into App's anonymous namespace next to
  `gpioPeripheralJson`, written with `ostringstream` + `escapeJson`; delete `hwconf::jsonEscape`. Same for `catalogJson`.
  ControlsModel also relies on transitive includes (`snprintf`, `std::find`, `std::isdigit` with no `<cstdio>`,
  `<algorithm>`, `<cctype>`).

## F10. Settings spec repeats each reader's defaults

- `ControlsModel.hpp:255-305` `fallback` strings: gpio `60`, neo `0x49`/`30`/`60`, pcf `0x20`/`40`/`60`, grove `0x04`/`32`/`80`,
  trigger line `17`. Readers: `GpioInput.hpp:71-74`, `NeoRotary4Input.hpp:46-48`, `Pcf8574Input.hpp:34-37`,
  `GroveAnalogInput.hpp:56-58`. All equal today. HW-I2: defaults live in the header `Config`.
- Also `trigger_output` `pcf_pin` default `0`, tally `-1`: match headers. `cfexpress_hat` `bus 10`, `0x34` repeats
  `UI/src/CfeAutomounter.cpp:38@upstream` (another process).
- Rework (simplify): make each reader's `struct Config` public (it is a plain struct) and build the fallback from
  `GpioInput::Config{}` etc. in App when serialising (F9 moves serialisation there anyway; HW-S8 forbids hardware headers
  pulling app knowledge, not App reading hardware headers).

## F11. `remote<N>` keys in `[gpio_buttons]`

- Port: `ControlsModel.hpp:141-149`, `:203-207`; `knownKey` `remote` 0..15 (`HardwareConfigText.hpp:459`); GpioInput
  skips the key (`gpioFromDigitalKey` does not match). Run by `test_input` (`App:12404`, no section-on check).
- Upstream: no precedent for a button without wiring. C1-S07: a key of `apertar-hardware.conf` is owned by the class
  that parses that section; `[gpio_buttons]` belongs to GpioInput. HW-N3/HW-S11: the hardware file holds wiring.
- Security cross-ref: `sweep-protocol-security.md` X-protocol-security-2 (LAN runs scripts via `test_input remoteN`).
- Verdict: rework. Own section read by App, e.g. `[remote_buttons]` with `b0=`, `b0_single=`..., listed in `kSections`,
  so GpioInput's section stays wiring only. Apply the X-2 script refusal in `testInputReply`.

## F12. `gpioChipScore` moved out of one of three files

- Port: `GpioChipInfo.cpp:30-54` holds the scorer; `GpioInput.cpp:475` calls it; `TriggerOutput.cpp:195` and
  `RecordingIndicatorOutput.cpp:191` keep their copies. Upstream: three copies (`GpioInput.cpp:238`,
  `TriggerOutput.cpp:201`, `RecordingIndicatorOutput.cpp:198@upstream`); HW-I7 "each GPIO user carries its own".
- Weights identical (rp1 +100, bcm +90, raspberrypi_exp -50, >=28 lines +10). Good.
- Rework (simplify): restore GpioInput's local `gpioChipScore` (upstream body, zero diff there) and keep
  `GpioChipInfo.cpp`'s as the copy the status card and `headerGpioChipPath` use. Either all users share or none; half is
  the worst for a reader.

## F13. GPIO input waits for edge events

- Port: `GpioInput.cpp:735-856` (`0c49601`): lines requested with both edges, thread sleeps in `poll()` until an edge or
  `ButtonGesture::nextWakeMs()`; chips without edge events fall back to `poll_ms`.
- Upstream: HW-I4 (usually) `sleep_for(pollMs)` loop (`GpioInput.cpp:740@upstream`); precedent for `poll()` on a device fd:
  `StandbyPowerButtonInput.cpp:51-56@upstream`.
- Verdict: keep. Reason a maintainer accepts: same thread, same debounce state machine, same retry intervals; only the
  wait changes, and the power key already works this way. Required: a sentence in the handoff, and F1's `poll_ms` row.
  Deliberate: yes (KB `decisions.md:41`, commit text). Not tested on hardware beyond "desk; pi build".

## F14. Comments: Cinemate, ticket numbers, history

- Cinemate references in 10 places: `ButtonGesture.hpp:2-3` ("the way Cinemate's SmartButton counts them (cinemate
  src/module/gpio_input.py)"), `ControlsModel.hpp:32`, `GpioInput.hpp:37`, `GpioInput.cpp:623,662,735`,
  `Pcf8574Input.cpp:425`, `Pcf8574Input.hpp:39`, `NeoRotary4Input.hpp:34`, `NeoRotary4Input.cpp:624` (via "like the GPIO buttons").
- Ticket numbers in the uses: `App:12487` "T40", `App:12459` "T42/T43" (controls_history).
- History narration: `ActionCatalog.hpp:25` "every spelling the old normalizers accept"; `:151` "like App's std::stod".
- Stale: `ButtonGesture.hpp:20` "Call on every poll" (it is called on edges and at `nextWakeMs`, `0c49601`);
  `ActionCatalog.hpp:315` "The Outputs card reads this list" (nothing reads it).
- C1-I14: comments are rare sentences stating a hazard or reason; no ticket numbers.
- Rework: state the timing in Apertar terms ("Press fires at once; releases within 500 ms count as clicks; held 3 s is
  Hold"); delete the rest.

## F15. Status probes read chips that UI-side readers poll

- `I2cProbe.hpp:2-3` promises "Only for addresses no Core driver is using". `cfeHatPeripheralJson` probes bus 10 0x34
  on every `get_controls` (`App:12097`); `scan_i2c` reads every address not held by a Core input (`App:12495-12521`), incl.
  INA219 on bus 4 and the CFexpress hat, which the UI's `Ina219Bridge` (1 s timer) and `CfeAutomounter`
  (`UI/src/CfeAutomounter.cpp`) poll from another process (HW-N5). A one-byte read between their register-pointer write
  and read can return the wrong register. Probable (pointer-register protocol of INA219 is documented; not reproduced).
- Rework: hold the INA219 address (`[ina219]` bus/address, default 4/0x40) and the hat address in `scan_i2c`'s `held`
  set as "ui"; card: report the hat from the automounter's status, not a probe.

## F16. `get_controls` parses the file eight times

- `App:12439-12447`: `hwconf::parse(info.text)` once per peripheral (8 calls), plus `validate` re-parses. Rework: one
  `const hwconf::Document doc = hwconf::parse(info.text);` above (C1-I17 local reuse).

## Not findings here (other units)

- `handleReadOnlyHardwareCommand` / `test_input` before the command lock: rev-App-4 App-4-F1 (C1-S03).
- Hot reload of driver groups by the controls worker (HW-N1): rev-App-4 (controls worker, F7).
- Nested arrays in `get_controls` replies: no protocol break; unmodified UI never sends it; C1-I09 governs request lines,
  which stay flat (`set.<section>.<key>=`).

## Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `hardware::actions` alias table `kSpecs` + `canonicalAction` | simplify | F5: one shared flat-chain normaliser in `ButtonActionList.hpp`; table keeps labels only |
| `classify()`, `Classified`, `number`, `numberAfter`, `suffixAfter` | simplify | F7: one parser, in App |
| `kTriggerEvents` / `canonicalTriggerEvent`, `kAnalogTargets` / `canonicalAnalogTarget` | rework-to-upstream-pattern | F6: restore driver bodies |
| `catalogJson` / `list_actions` | simplify | F8: `actions` only; serialise in App (F9) |
| `suggestion()` ("Did you mean") | keep | Log-only, one line, upstream log text kept |
| `isStepping`, `warnOnTurn` | keep | Feed page filter and validator warnings; small |
| `hwconf::ControlRow`, `ControlLine`, `controlRows`, `gpioPinsInUse` | keep | New ground for the Controls page; reads text, not a second runtime parser |
| `SettingSpec`, `peripheralSettings` | simplify | F10, plus F1/F3 rows |
| `modelJson`, `peripheralSettingsJson`, `hwconf::jsonEscape` | rework-to-upstream-pattern | F9 |
| `remote<N>` rows / `remoteOnly` | rework-to-upstream-pattern | F11 |
| `ButtonGesture` | keep | Shape of upstream `PowerButtonGesture.hpp` (header-only, fed ms timestamps); fix comments F14 |
| `GpioChipInfo`, `readGpioChipInfo`, `headerGpioChipPath` | keep | Read-only chip/line ioctls, raw Linux interface (HW-I6) |
| `gpioChipScore` moved to `GpioChipInfo.cpp` | simplify | F12 |
| `I2cProbe` / `probeI2cAddress` | keep | Raw `I2C_SLAVE` + read (HW-I6); F15 for the callers |
| `ActionCatalog::normalizeToken` | simplify | F5: file-local copy per HW-S2 |

## Conforms

- `ButtonGesture.hpp` follows `PowerButtonGesture.hpp@upstream`: header-only, pure, millisecond input, C1-S06 note.
- `GpioChipInfo.cpp` and `I2cProbe.cpp` use raw `linux/gpio.h` v2 / `I2C_SLAVE` ioctls, no libgpiod or libi2c (HW-I6).
- New `.cpp` files registered by name in `CMakeLists.txt:95-96` (HW-S9).
- Hardware headers include only hardware headers (`ControlsModel.hpp:4`, `ActionCatalog.hpp:4`) (HW-S8).
- `chip=auto` scoring weights and `/dev/gpiochip0..9` scan unchanged (HW-I7); explicit chip path still skips the scan
  (`GpioInput.cpp:465-466`).
- `canonicalAction` keeps upstream's alias sets exactly and passes unknown tokens through (HW-I5 semantics);
  `ButtonActionList.hpp` unchanged, 6-action cap and output-action rule kept.
- `clear_hdr` is one branch in `handleSingleHardwareInputAction` that dispatches `set_clear_hdr` (HW-S3, C1-S11, recipe R2).
- `test_input` runs through `handleHardwareInputAction`, same Standby wake and sequence mutex as a real press.
- I2C defaults match upstream: PCF 1/0x20, NeoRotary 1/0x49, Grove 1/0x04, CFexpress hat 10/0x34 (HW-N4).
- Error sentences in `testInputReply`, `scan_i2c` are operator sentences (C1-I07).

## Skeptic

Stage 3. Every finding re-read on both sides (`cinemate-port` `01f170c`, `upstream-1.6.0`), commits checked with `git show -s`, KB `working/controls/decisions.md`.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | stands | `ControlsModel.hpp:257-263` confirmed; `c140c4f` and `decisions.md:46` confirm intent; upstream reads `chip` in both GPIO sections and both outputs. Fixed on `work/improve` `04fe197`; remainder (fixed 4..27 pin list `:381`, line max 27 `:268`) still open |
| F2 | corrected | GpioInput (`:622-629`) and Pcf8574Input (`:423-432`) do invert. NeoRotary `heldAtStartMask` (`NeoRotary4Input.cpp:611,626-630`) does not invert: it skips a push held at open until it is released, which matches upstream (no event for a push held at start). Removed from the rework. Source is Cinemate `check_initial_state` (`cinemate src/module/gpio_input.py:310-315`) |
| F3 | corrected | Confirmed. Line refs `TriggerOutput.cpp:325`, `RecordingIndicatorOutput.cpp:363` are port lines (upstream `:331`, `:370`). Added: upstream trigger also reads a generic `pin` key (`TriggerOutput.cpp:316@upstream`), also refused by `knownKey`/`canonicalKey` |
| F4 | stands | `grep -rn "hold_ms\|double_ms" src` hits only `HardwareConfigText.hpp`; timings are `ButtonGesture.hpp:16-18` constants |
| F5 | corrected | Mismatch confirmed. Rework changed: upstream `ButtonActionList.hpp:80,113@upstream` takes the normaliser as a parameter, i.e. per-driver copies are the design (HW-I5 always, HW-S2 "refactoring the copies away unasked"). First choice is the three upstream bodies restored verbatim plus the port's new names; one shared flat chain is the fallback |
| F6 | stands | `TriggerOutput.cpp:131-143`, `GroveAnalogInput.cpp:126-129` confirmed; `kTriggerEvents`/`kAnalogTargets` have no reader outside `catalogJson`. Rework also restores App's own target normaliser (`App:10090` calls the catalog; upstream had `App:8410-8432`) |
| F7 | corrected | Confirmed, but "cannot be saved" overstated: a new error blocks a save unless forced (`HardwareConfigStore.cpp:336-340`, `flags.force`) |
| F8 | stands | WebUI reads only `catalog.actions/ok/error` (grep); row gestures come from `get_controls` model, not `list_actions`; `gestures.button=["press"]` false |
| F9 | stands | `ControlsModel.hpp:50-71` own escaper, string `+` JSON; App uses ostringstream + `escapeJson` (C1-I08) |
| F10 | stands | Fallback strings equal reader defaults today; depends on F9 to serialise in App |
| F11 | stands | `9b5ea14` deliberate; `remoteOnly` bypasses the section-on check (`App:12403`) |
| F12 | corrected | Confirmed; severity minor -> nit (no behaviour, weights identical) |
| F13 | stands | `0c49601`, `decisions.md:41`; poll fallback at `GpioInput.cpp:744,856` |
| F14 | corrected | Confirmed; added `HardwareConfigText.hpp:116` "(T44)", `GpioInput.hpp:37`, `Pcf8574Input.hpp:39`, `NeoRotary4Input.hpp:34` |
| F15 | stands | Probable. `scan_i2c` holds only neorotary4/pcf8574/grove (`App:12498-12503`); hat probe per `get_controls` (`App:12097`). Rework adds no lock, so HW-N5 is respected |
| F16 | corrected | Confirmed (8 `hwconf::parse(info.text)` at `App:12439-12447`). C1-I17 is about local lambdas, not this; Apertar way is plain local reuse |

Hint check (other narrowed settings): beyond F1/F3, a `dN=recindicatorled` line (upstream template comment `App:4389-4390@upstream`) is filtered out of a row's actions by `canonicalAction` (`ControlsModel.hpp:81-84`), so the row shows no action. Unconfirmed whether the page then offers to overwrite it (check the page against a file with `d5=recindicatorled`). Folded into F3.

## Final findings

### HW-controls-model-F1 [removed-upstream-behaviour, major] GPIO chip (and poll_ms) dropped from the Controls page
- where: `src/hardware/ControlsModel.hpp:257-271@cinemate-port`; `src/hardware/ControlsModel.hpp:381@cinemate-port`; `src/ApertarCoreApp.cpp:11987-11989@cinemate-port`
- port: `peripheralSettings(gpio_buttons)` lists enabled, active_low, pull, debounce_ms; comment "poll_ms (chips without edge events) and chip stay text-only: the Pi 5's header needs neither". Outputs have no chip row; output line max 27; free-pin list fixed 4..27. Status card read chip only from `[gpio_buttons]`; an empty `chip=` showed "No GPIO chip found."
- Apertar way: `GpioInput.cpp:431-432@upstream-1.6.0` `chip`/`gpiochip`/`gpio_chip` shared by `[gpio_buttons]` and `[gpio_encoders]`; `TriggerOutput.cpp:311`, `RecordingIndicatorOutput.cpp` chip key `@upstream-1.6.0`; empty value means auto (HW-N3, HW-I7)
- why it matters: pins on another chip (an MCU, an I2C/USB GPIO expander, or a DPI rig where the header is taken) cannot be set up from the page. Owner asked for the chip back
- rework: done on `work/improve` `04fe197` (fix-log C1): chip and poll_ms rows for gpio_buttons, chip for both outputs, `gpioPinsInUse` skips non-header chips, card uses `gpioInputChip(doc)`. Remaining: Core's model still uses the fixed free-pin list 4..27 and output line max 27; give the model the chosen chip's line count (`readGpioChipInfo`)
- effort S; deliberate yes (`c140c4f` "The GPIO card's settings drop poll and chip (edge events need neither)"; KB `working/controls/decisions.md:46`)

### HW-controls-model-F2 [removed-upstream-behaviour, major] A button that reads pressed at start is inverted for the whole session, overriding active_low
- where: `src/hardware/GpioInput.cpp:620-629@cinemate-port`; `src/hardware/Pcf8574Input.cpp:423-432@cinemate-port`
- port: on the first sample `button.inverted = level` (GPIO) and `invertedMask` (PCF8574); log "reads pressed at start; taken as inverted (a 1-0-1 button)". Ported from Cinemate `check_initial_state` (`cinemate src/module/gpio_input.py:310-315`)
- Apertar way: polarity is stated by the operator per section with `active_low` (`GpioInput.cpp:433-434`, `Pcf8574Input.cpp:372@upstream-1.6.0`); no guessing (HW-N3, HW-N7)
- why it matters: `d17=capture` held while Core starts, or pressed while the controls worker restarts the GPIO group after a save: every release then fires capture until the next restart. A stuck contact is silently flipped
- rework: delete the start-sample inversion (`haveSample`/`inverted` in GpioInput, `invertedMask` in Pcf8574Input). Keep NeoRotary's `heldAtStartMask` (`NeoRotary4Input.cpp:611,626-630`): it only ignores a push held at open until release, as upstream gave no event for it. If per-pin normally-closed buttons are needed, add a per-pin key in the header `Config` and `loadConfig` (recipe R3), e.g. `d17_active_low=false` / `pin3_active_low=false`, and a row field on the page
- effort S; deliberate yes (`0a98868` "inverts a button that reads pressed when it starts"; `c140c4f` for PCF; `decisions.md` T44 entry)

### HW-controls-model-F3 [removed-upstream-behaviour, minor] Upstream keys refused by set_controls or hidden from the page
- where: `src/hardware/HardwareConfigText.hpp:460-462,476-477,496-497@cinemate-port`; `src/hardware/HardwareConfigText.hpp:174-181@cinemate-port` (canonicalKey); `src/hardware/ControlsModel.hpp:132-201,264-303@cinemate-port`
- port: `knownKey(gpio_encoders)` accepts only enabled and `encoderN_*`, so `set.gpio_encoders.poll_ms=3` is refused with "'poll_ms' is not a key of [gpio_encoders] that Apertar reads". Output `active_low` and the trigger's generic `pin` key are refused the same way. `open_drain`, `pulse_ms`, `events`, encoder `_invert`/`_steps_per_event`, NeoRotary `reset_on_start`/`max_events_per_poll`, Grove `emit_on_start` and every Grove `aN` mapping are not on the page. A `dN=recindicatorled` (upstream tally on a button pin) shows as a row with no action (`ControlsModel.hpp:81-84`; overwrite risk unconfirmed)
- Apertar way: `GpioInput.cpp:431-445@upstream-1.6.0` reads chip, active_low, pull, poll_ms, debounce_ms in `[gpio_encoders]` too; the upstream UI template writes `poll_ms=3`, `debounce_ms=40` there (`UI/src/DisplayConfigBridge.cpp:175-176@upstream-1.6.0`). `TriggerOutput.cpp:316,318,331,333,337@upstream-1.6.0` read `pin`, `open_drain`, `active_low`, `pulse_ms`, `events`; `RecordingIndicatorOutput.cpp:370@upstream-1.6.0` reads `active_low`; Core template writes `open_drain=true` (`App:4382@upstream-1.6.0`)
- why it matters: the page states a falsehood about the reader, and operator settings HW-N3 names (trigger events, pulse length, chip, poll) are not reachable from it
- rework: `knownKey`: accept the shared GPIO keys (chip, active_low, pull, poll_ms, debounce_ms) in `[gpio_encoders]`, `active_low` in both outputs, `pin` in `[trigger_output]` (or map it in `canonicalKey` as upstream does by target). Add `open_drain` to the outputs' `peripheralSettings`, `pulse_ms` and `events` to the trigger's. Either add Grove rows to `controlRows` or say on the page that `[grove_analog]` channels are edited in Config. Show output actions on a button row as read-only text
- effort S; deliberate unknown

### HW-controls-model-F4 [bug, minor] hold_ms and double_ms accepted as known keys, read by nobody
- where: `src/hardware/HardwareConfigText.hpp:457,466,470@cinemate-port`; `src/hardware/ButtonGesture.hpp:16-18@cinemate-port`
- port: the validator lists `hold_ms`, `double_ms` for gpio_buttons, pcf8574, neorotary4; the timings are `constexpr` in ButtonGesture
- Apertar way: behaviour timing fixed in code (`PowerButtonGesture.hpp@upstream-1.6.0`, HW-N3); no dead keys
- why it matters: `[gpio_buttons] hold_ms=1000` saves clean, but Hold still fires at 3 s
- rework: remove `hold_ms` and `double_ms` from `knownKey`
- effort S; deliberate no

### HW-controls-model-F5 [mismatch, minor] Action aliases as a runtime CSV string table instead of flat if-chains
- where: `src/hardware/ActionCatalog.hpp:18-132@cinemate-port`; `src/hardware/GpioInput.cpp:114@cinemate-port`; `src/hardware/Pcf8574Input.cpp:144@cinemate-port`; `src/hardware/NeoRotary4Input.cpp:125@cinemate-port`
- port: `kSpecs[]` rows `{id, group, label, "a,b,c" aliases, sources, ui, Arg, token}`, matched with `listHas`; drivers call `actions::canonicalAction`
- Apertar way: `GpioInput.cpp:108-202@upstream-1.6.0` flat chain `if (action == "record" || action == "capture" || action == "camera_button" || action == "take") return "capture";`, copied in `Pcf8574Input.cpp:140` and `NeoRotary4Input.cpp:121`; `ButtonActionList.hpp:80,113@upstream-1.6.0` takes the normaliser as a parameter, so per-driver copies are the design (HW-I1, HW-I5, HW-S2)
- why it matters: a reader looking for an alias finds a table and a string-split helper, not the chain they wrote. One row mixes aliases, UI labels, parameter families and source flags
- rework: restore the three `normalizeSingleAction` bodies verbatim from upstream, adding the port's new names (clear_hdr, ev_up/ev_down and the like) to each as `||` chains. Fallback if the owner prefers one copy: one flat-chain `normalizeSingleAction` in `ButtonActionList.hpp` beside `normalizeButtonMapping`. Reduce `kSpecs` to `{id, group, label, sources}` for `list_actions`. Delete `ActionCatalog::normalizeToken`; `HardwareConfigText.hpp` gets a file-local copy
- effort M; deliberate yes (`916c1dd` "the same action names lived in three normalizeSingleAction copies ... a new action meant editing six places")

### HW-controls-model-F6 [mismatch, minor] Trigger events and analog targets moved into the catalog with no consumer
- where: `src/hardware/TriggerOutput.cpp:131-143@cinemate-port`; `src/hardware/GroveAnalogInput.cpp:126-129@cinemate-port`; `src/ApertarCoreApp.cpp:10090@cinemate-port`; `src/hardware/ActionCatalog.hpp:298-334@cinemate-port`
- port: `eventFromToken` calls `canonicalTriggerEvent` (token to string id), then four ifs to the enum. Grove's `normalizeTarget` and App's target normaliser delegate to `canonicalAnalogTarget`. Both lists are served only in `list_actions`; the WebUI reads only `catalog.actions`
- Apertar way: `TriggerOutput.cpp:130-148@upstream-1.6.0` maps the token straight to the enum, same aliases; `GroveAnalogInput.cpp:125-145@upstream-1.6.0` `normalizeTarget`; App's own copy `App:8410-8432@upstream-1.6.0`
- why it matters: churn in two upstream driver files for no gain; the comment "The Outputs card reads this list" is false
- rework: restore upstream `eventFromToken`, Grove `normalizeTarget` and App's target normaliser (zero diff in `TriggerOutput.cpp`, `GroveAnalogInput.cpp`). Drop `kTriggerEvents`, `canonicalTriggerEvent`, `kAnalogTargets`, `canonicalAnalogTarget` from the catalog; if F3's trigger `events` row is built, keep only an id/label list for it
- effort S; deliberate yes (`916c1dd`)

### HW-controls-model-F7 [duplication, minor] classify() is a second parser of the parametric action grammar; the validator turns it into save-blocking errors
- where: `src/hardware/ActionCatalog.hpp:134-246@cinemate-port`; `src/hardware/HardwareConfigText.hpp:964-968@cinemate-port`; `src/hardware/HardwareConfigStore.cpp:336-340@cinemate-port`; `src/ApertarCoreApp.cpp:1645-1655@cinemate-port`
- port: `classify` re-parses ev/fps/resolution/iso/shutter/wb and restates Core rules ("Core clamps ... K"). An unknown action is an error issue; a new error blocks the save unless forced. App keeps the executing parser but wraps catalog `suffixAfter`/`numberAfter` via `prefixViews`
- Apertar way: HW-I5: parametric names are parsed only in the handler (`App:1342-1370`, `8660-8955@upstream-1.6.0`). HW-N7: an unknown action is logged at run time (`App:8954@upstream-1.6.0`), never refused
- why it matters: when the two parsers drift, a mapping Core would run is refused on save (only a forced save gets through). No diverging input found yet (probable)
- rework: restore `hardwareActionSuffix` and `parseHardwareActionNumber` bodies in App from upstream. Drop `classify`, `Classified`, `compact`, `number`, `numberAfter`, `suffixAfter` from the catalog. The validator flags only tokens that are neither a catalog id nor start with iso/fps/wb/ev/shutter/res, as a warning
- effort M; deliberate yes (`916c1dd` "a typo in the file was silent")

### HW-controls-model-F8 [slop, minor] list_actions serves fields nobody reads; its gestures list is wrong
- where: `src/ApertarCoreApp.cpp:12534-12554@cinemate-port`; `src/web/WebControlPage.cpp:18265@cinemate-port`
- port: the reply adds `values` (six option lists from sensor and UI.conf), `values_for`, `gestures {button:[press]}`, `analog_targets`, `trigger_events`, `max_per_mapping`. The WebUI caches the first reply and reads only `actions` (row gestures come from `get_controls`); the touch UI never sends `list_actions`
- Apertar way: replies carry what a client uses (C1-I08 hand-written JSON); no precedent for unused reply fields
- why it matters: dead protocol surface computed on every call; `gestures` says buttons only have press, false since `0a98868`
- rework: reply with `"actions"` only (plus `max_per_mapping` if the page enforces it); delete `values`, `values_for`, `gestures`
- effort S; deliberate no

### HW-controls-model-F9 [mismatch, minor] JSON built in the hardware header with string concatenation and its own escaper
- where: `src/hardware/ControlsModel.hpp:50-71,307-388@cinemate-port`; `src/hardware/ActionCatalog.hpp:336-358@cinemate-port`
- port: `hwconf::jsonEscape`; `modelJson` and `peripheralSettingsJson` build JSON with `std::string +`; the header relies on transitive includes for `snprintf`, `std::find`, `isdigit`
- Apertar way: C1-I08: JSON hand-written with `std::ostringstream` and `escapeJson` in App (`App:167-215@upstream-1.6.0`); the port's own `gpioPeripheralJson` (`App:11993`) already does this
- why it matters: a second escaper and a second JSON style next to App's
- rework: keep `ControlsModel.hpp` data only (`controlRows`, `gpioPinsInUse`, `peripheralSettings`). Move `modelJson`, `peripheralSettingsJson`, `catalogJson` into App's anonymous namespace beside `gpioPeripheralJson`, using ostringstream and `escapeJson`. Delete `hwconf::jsonEscape`
- effort S; deliberate no

### HW-controls-model-F10 [duplication, minor] The settings spec repeats each reader's defaults
- where: `src/hardware/ControlsModel.hpp:255-305@cinemate-port`
- port: `SettingSpec` fallback strings: debounce 60, poll 30/40/80, addresses 0x49/0x20/0x04, deadband 32, trigger line 17
- Apertar way: HW-I2: defaults are in-class initialisers of the header Config (`GpioInput.hpp:45-57`, `Pcf8574Input.hpp:28-38`, `TriggerOutput.hpp:46-51@upstream-1.6.0`)
- why it matters: a default changed in the reader is not seen by the page (all equal today)
- rework: make each reader's `Config` struct public and build the fallbacks from `GpioInput::Config{}`, `Pcf8574Input::Config{}` etc. in App during serialisation (with F9)
- effort S; deliberate no

### HW-controls-model-F11 [new-ground, minor] Remote-only buttons stored as remote<N> in [gpio_buttons], a section GpioInput owns
- where: `src/hardware/ControlsModel.hpp:141-149,203-207@cinemate-port`; `src/hardware/HardwareConfigText.hpp:459@cinemate-port`; `src/ApertarCoreApp.cpp:12403-12404@cinemate-port`
- port: `remote0..15` keys sit in `[gpio_buttons]`; GpioInput skips them; App runs them through `test_input` without the section-on check
- Apertar way: no precedent. C1-S07: a key is owned by the class that parses its section; HW-N3/HW-S11: the hardware file holds wiring. App-parsed section has precedent (`[ina219]`, `App:4450@upstream-1.6.0`)
- why it matters: GpioInput's section holds keys it must ignore. With `test_input` this lets a LAN client run scripts (X-protocol-security-2)
- rework: give remote buttons their own section read by App (e.g. `[remote_buttons] b0=`, `b0_single=` ...), registered in `kSections`. Refuse script actions in `testInputReply` (X-2 fix)
- effort M; deliberate yes (`9b5ea14`)

### HW-controls-model-F12 [duplication, nit] gpioChipScore moved out of one of its three copies
- where: `src/hardware/GpioChipInfo.cpp:30-54@cinemate-port`; `src/hardware/GpioInput.cpp:475@cinemate-port`; `src/hardware/TriggerOutput.cpp:195@cinemate-port`; `src/hardware/RecordingIndicatorOutput.cpp:191@cinemate-port`
- port: GpioInput uses the shared copy in `GpioChipInfo.cpp`; TriggerOutput and RecordingIndicatorOutput keep local copies (weights identical)
- Apertar way: HW-I7: every GPIO user carries its own `gpioChipScore` (`GpioInput.cpp:238`, `TriggerOutput.cpp:201`, `RecordingIndicatorOutput.cpp:198@upstream-1.6.0`)
- why it matters: half-shared code is harder to follow; the GpioInput diff grows for no gain
- rework: restore GpioInput's local `gpioChipScore` verbatim from upstream; keep the `GpioChipInfo.cpp` copy for the status card and `headerGpioChipPath`
- effort S; deliberate no

### HW-controls-model-F13 [new-ground, minor] GPIO input waits for kernel edge events instead of polling
- where: `src/hardware/GpioInput.cpp:518,735-856@cinemate-port`; `src/hardware/ButtonGesture.hpp:55-65@cinemate-port`
- port: lines requested with both edges; the thread sleeps in `poll()` until an edge or `ButtonGesture::nextWakeMs`; falls back to `poll_ms` on chips without edge events (`:744,856`)
- Apertar way: HW-I4 (usually) `sleep_for(pollMs)` loop (`GpioInput.cpp:740@upstream-1.6.0`); precedent for `poll()` on a device fd in `StandbyPowerButtonInput.cpp:51-56@upstream-1.6.0`
- why it matters: rewrites an upstream loop; desk-tested plus Pi build, edges confirmed on GPIO 6 and 10
- rework: keep. Mention it in the handoff; keep the `poll_ms` row (F1) for chips without edge events
- effort S; deliberate yes (KB `decisions.md:41`; `0c49601`)

### HW-controls-model-F14 [slop, minor] Comments carry Cinemate references, ticket numbers, history and stale statements
- where: `src/hardware/ButtonGesture.hpp:2-3,20@cinemate-port`; `src/hardware/ControlsModel.hpp:32@cinemate-port`; `src/hardware/GpioInput.hpp:37@cinemate-port`; `src/hardware/GpioInput.cpp:623,662,735@cinemate-port`; `src/hardware/Pcf8574Input.hpp:39@cinemate-port`; `src/hardware/Pcf8574Input.cpp:425@cinemate-port`; `src/hardware/NeoRotary4Input.hpp:34@cinemate-port`; `src/hardware/HardwareConfigText.hpp:116@cinemate-port`; `src/hardware/ActionCatalog.hpp:25,151,315@cinemate-port`; `src/ApertarCoreApp.cpp:12459,12477,12487@cinemate-port`
- port: "the way Cinemate's SmartButton counts them (cinemate src/module/gpio_input.py)", "Like Cinemate", "T40", "T42/T43", "T44", "every spelling the old normalizers accept", "Call on every poll" (stale after `0c49601`), "The Outputs card reads this list" (nothing reads it)
- Apertar way: C1-I14: comments are rare sentences stating a hazard or reason; no ticket numbers
- why it matters: the original developer does not know Cinemate or the ticket numbers; stale comments mislead
- rework: describe the timing in Apertar terms ("Press fires at once; releases within 500 ms count as clicks; held 3 s is Hold"); delete references, ticket numbers and history; fix the two stale comments
- effort S; deliberate no

### HW-controls-model-F15 [bug, minor] Status probes and scan_i2c read chips that the UI process polls (probable)
- where: `src/hardware/I2cProbe.hpp:2-3@cinemate-port`; `src/ApertarCoreApp.cpp:12097,12495-12521@cinemate-port`
- port: `cfeHatPeripheralJson` probes bus 10 0x34 on every `get_controls`; `scan_i2c` holds only neorotary4/pcf8574/grove and reads every other address, including INA219 on bus 4
- Apertar way: HW-N5: the UI's `Ina219Bridge` (1 s timer) and `CfeAutomounter` poll these chips from another process, no lock; upstream Core never probes them
- why it matters: a one-byte read between another reader's register-pointer write and its read can return the wrong register; the header's own promise ("only for addresses no Core driver is using") ignores UI drivers
- rework: add the `[ina219]` and `[cfexpress_hat]` addresses to `scan_i2c`'s held set as "ui". Report the hat from the automounter's state instead of probing it. No lock (HW-N5)
- effort S; deliberate no

### HW-controls-model-F16 [slop, nit] get_controls parses the hardware file eight times per call
- where: `src/ApertarCoreApp.cpp:12439-12447@cinemate-port`
- port: `hwconf::parse(info.text)` once per peripheral
- Apertar way: plain local reuse (no precedent needed; C1-I17 is about local lambdas and does not apply)
- why it matters: wasted work on a command the page polls
- rework: parse once into `const hwconf::Document doc` and pass it to each peripheral
- effort S; deliberate no
