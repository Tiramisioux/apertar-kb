# Review: HW-input-classes (stage 2)

Scope diff: `git -C /home/user/Apertar-Core diff --minimal origin/main cinemate-port -- <11 files>`, saved at
`/home/user/build/review/HW-input-classes.diff` (1865 lines, read fully). Refs: `@port` = cinemate-port `01f170c`,
`@upstream` = `/home/user/wt/core-upstream` (upstream-1.6.0). Yardstick: `raw/conv-hardware-config.md` (rule ids HW-*);
no `apertar-conventions.md` yet. All claims confirmed in code unless labelled.

## 0. Answers to the stage-1 open points

| Open point | Answer |
| --- | --- |
| Mpu6050RecordingSession.cpp lost 257 lines: where | `writeHardwareConfigValue` (upstream :604-713) and `updateImuBiasConfig` (:715-849), two self-contained line editors with `.tmp` + rename, became `writeHardwareConfigValues` (port :603-640) = one `HardwareConfigStore::edit` with `trusted=true`. The line-edit job moved to `HardwareConfigText.hpp` (1141 lines) + `HardwareConfigStore.cpp` (505 lines), unit HW-config-text-store. Setters lost their `loadConfig()` + `defaultHardwareConfigPath()` path computation. Nothing operator-visible was dropped except the write target (F9) |
| "one history entry per IMU session" vs one edit per call | Both true: the store coalesces IMU entries within 10 minutes (`HardwareConfigStore.cpp:385` comment "IMU writes within 10 minutes of an IMU entry share it") |
| Alias sets lost in the catalog move | None. Host check: every alias of upstream `GpioInput.cpp normalizeSingleAction` (125 alias->id pairs) run through port `hardware::actions::canonicalAction` gives the same id; tally tokens and none/off/disabled give "". Parametric tokens (`iso800`, `fps24`, `wb5600`, `shutter1/48`) and `isoinf` pass through unchanged, as upstream (refusal of `isoinf` is in App, other unit) |
| `isOutputAction` swap in RecordingIndicatorOutput | Same 8 tokens as the deleted body (`ButtonActionList.hpp:57-61 @upstream`); pure dedupe onto an existing upstream helper |

## 1. Findings

| Id | Sev | Cat | Title |
| --- | --- | --- | --- |
| F1 | major | removed-upstream-behaviour | Standby wake press seeds click / Hold gestures: upstream's "wake press is consumed" broken |
| F2 | major | bug | 1-0-1 inversion and switch start-apply re-run on every device reopen, not only at Core start |
| F3 | minor | mismatch | Edge-event loop does not follow the upstream `poll()` input (`StandbyPowerButtonInput`): 250 ms idle wake instead of eventfd stop; wall clock instead of kernel event timestamps |
| F4 | minor | mismatch | `run()` rewritten around two large capturing lambdas (`process`, `sleepMs`) |
| F5 | minor | bug (probable) | Edge drain: a full-level read between two 16-event batches replays old edges onto the new level (encoder back-steps on fast turns) |
| F6 | minor | bug / new-ground | Switches apply toggle actions at start: switch position and toggle state drift |
| F7 | minor | mismatch | `setSeenCallback` setter instead of constructor injection |
| F8 | minor | duplication | `gpioChipScore` half-shared: GpioInput uses `GpioChipInfo.cpp`, Trigger and LED keep private copies |
| F9 | minor | removed-upstream-behaviour | IMU writes always go to `~/apertar-hardware.conf`, no longer to the file the loader read |
| F10 | nit | slop | Code comments narrate Cinemate provenance and WebUI features inside `src/hardware/` |
| F11 | nit | mismatch | Seen-key suffix chosen by `static_cast` of the gesture enum into parallel string arrays, three copies |

### F1 Standby wake press seeds gestures (major, removed-upstream-behaviour)

- Port: `ButtonGesture::update` (`src/hardware/ButtonGesture.hpp:21-55 @port`) counts the press that woke the camera as
  click 1 and starts its Hold timer. The input classes call `emitAction` (void) and never learn that App consumed the
  press for wake (`ApertarCoreApp.cpp:10312-10318 @port`: in Standby a button press dispatches `wake` and returns).
  Later gesture events go through `handleHardwareInputAction` again with the camera awake and run.
- Upstream: `StandbyPowerButtonInput.cpp:66-71 @upstream`:
  `if (action != ... None && pressed_ && pressed_(...)) gesture.consume(); // A wake press cannot seed another sleep.`
  with `std::function<bool(bool)> pressed_` (`StandbyPowerButtonInput.hpp:8,14`) and `PowerButtonGesture::consume()`
  (`PowerButtonGesture.hpp:33`). Intent HW-N2: "in Standby a button press only wakes and is consumed"; `UI/README.md:197`.
- Failing input: `[gpio_buttons] d17=record_toggle`, `d17_hold=standby`; camera in Standby; hold d17 3 s -> Press
  wakes, Hold at 3 s puts it back to Standby. Or `d17_double=photo`: double-click in Standby wakes and takes a photo.
- Rework: give `ButtonGesture` a `consume()` (clear `clicks_`, set `holdFired_`/`longPress_`), the PowerButtonGesture
  way. Make the action callback report consumption: `handleHardwareInputAction` returns `bool consumedForWake`; the
  input classes' `ActionCallback` for buttons becomes `std::function<bool(const std::string &)>` (rotation stays void)
  and on `true` call `gesture.consume()`. Same in GpioInput, Pcf8574Input, NeoRotary4Input.

### F2 Inversion and switch start-apply re-run on reopen (major, bug)

- GpioInput: runtime buttons and switches are rebuilt inside `if (lineFd < 0)` (`GpioInput.cpp` run, diff lines
  587-647) with `haveSample=false` and `stable=-2`; any read/poll failure closes the fd (diff 651-668, 687-692).
  Pcf8574Input: `haveSample = false` on every reopen (`Pcf8574Input.cpp:410 @port`) and `invertedMask` is recomputed
  when `!haveSample` (`:423-431`); any I2C read failure closes the device (`:416-420`).
- The KB decision (`working/controls/decisions.md:39`) limits the caveat to "a button held down while Core starts".
  Code applies it at every reopen. A transient I2C error on a shared bus while the record button is held turns that
  pin inverted until Core restarts: every release then fires Press. Each GPIO reopen also re-fires every switch's
  position action (F6 makes that visible for toggles).
- Upstream had no such state: reopen only re-seeded observed/stable (`Pcf8574Input.cpp:479-505 @upstream`).
- Rework: decide inversion once per `start()` (a member `std::optional<uint8_t> invertedMask_` / per-button flag kept
  across reopen) and apply switch positions only on the first sample after `start()`.

### F3 Edge loop shape vs upstream `poll()` input (minor, mismatch; edges themselves new-ground, keep)

- Upstream precedent for an event-driven input exists: `StandbyPowerButtonInput.cpp:16-31,51-56 @upstream`
  (`eventfd` stop, `poll(..., -1)`) and `PowerButtonGesture.hpp:4` "Use evdev timestamps so delayed/batched reads
  preserve press spacing."
- Port: `kIdleWakeMs = 250` so `stop()` is noticed (diff 555-570): the thread still wakes 4x/s and does a full line
  read each time; every event in a batch gets the same `steady_clock::now()` (diff 674-681) though
  `gpio_v2_line_event::timestamp_ns` is there.
- Rework: add `stopFd_` eventfd like StandbyPowerButtonInput, poll both fds, timeout = gesture/debounce deadline or -1;
  feed `process` with `events[i].timestamp_ns / 1'000'000` (CLOCK_MONOTONIC = steady_clock on Linux).
- Edge events: deliberate (decisions.md:41, commit 0c49601), fallback to `poll_ms` kept, Pi chips report `edges=both`.
  Verdict keep. No hardware test of 0c49601 recorded.

### F4 Lambdas in run() (minor, mismatch)

- Port: `process` (~95 lines) and `sleepMs` capturing lambdas plus `toMs` inside `GpioInput::run()`.
- Upstream: `GpioInput.cpp:620-744 @upstream`, one straight loop; helpers are private members (`readLineValues`,
  `emitAction`). No upstream hardware file uses a lambda of that size.
- Rework: private members `void processLevels(uint64_t levels, steady_clock::time_point now, std::vector<RuntimeButton>&,
  ...)` and `int wakeTimeoutMs(...) const`, or make `buttons/encoders/switches` members of the run state struct.

### F5 Edge drain replays stale edges (minor, bug, probable)

- Port reads at most 16 `gpio_v2_line_event` per wake (diff 672-682), then always does `readLineValues` + `process`
  (diff 687-693). If more than 16 edges were queued (fast encoder spin), the next loop reads edges 17..N and applies
  each as a delta onto `bits` that already hold the current level. A quadrature encoder then sees old single-bit
  transitions on a newer state: valid-looking transitions in the wrong direction.
- Probable (no hardware here). Settle: host test feeding 40 queued edges through the same loop.
- Rework: drain until `read` returns fewer than 16 events (fd is non-blocking or `poll` with 0 timeout), and do the
  catch-up full read only when no events were read.

### F6 Switches apply toggles at start (minor, bug / new-ground)

- `[gpio_switches]` (decisions.md:37,42; commit c34f844) applies the position action at start and on each change.
  The action vocabulary for monitoring is toggles only (`ActionCatalog.hpp`: "Zebra on / off" etc.; upstream
  `App:8660-8955` toggle branches). `switch0_pins=17`, `switch0_on=zebra`, `switch0_off=zebra`, zebra saved on in
  UI.conf, switch in the on position at Core start -> zebra turns off; with F2, every GPIO reopen toggles it again.
- New ground, deliberate. Verdict simplify: document that a switch position should carry an absolute action
  (`iso800`, `fps24`, `wb5600`) or add absolute `*_on`/`*_off` actions in App the upstream way (handler branches
  ending in `dispatch`, HW-S3) before offering toggles on switches in the Controls page.
- Middle position of a three-way switch and "both closed" (-1) are emitted nowhere when unmapped: fine.

### F7 Seen callback by setter (minor, mismatch)

- Port: `setSeenCallback(ActionCallback)` on three classes, set from `ApertarCoreApp.cpp:8118-8120 @port`
  (comment `// T42 Listen`, outside scope), unsynchronised member written before `start()`.
- Upstream: callbacks are constructor arguments (`GpioInput.hpp:17 @upstream`,
  `App:6785-6792 @upstream`; conv section 3 "Callback injected through the constructor").
- Rework: third ctor parameter `ActionCallback seenCallback = {}`; wire it in App's member-init list next to the
  existing lambdas; delete the setter calls.
- The `"section|key"` string is built from the class's own config keys, so HW-S8 holds.

### F8 gpioChipScore half-shared (minor, duplication)

- Port: GpioInput calls `hardware::gpioChipScore` (`GpioChipInfo.cpp:31-55 @port`, with its own `lowered()` copy
  of normalizeToken); `TriggerOutput.cpp:195` and `RecordingIndicatorOutput.cpp:191 @port` keep private copies.
- Upstream HW-I7 (always): each GPIO user carries its own copy (`GpioInput.cpp:238`, `TriggerOutput.cpp:201`,
  `RecordingIndicatorOutput.cpp:198 @upstream`).
- Now neither convention: one moved, two not. Rework (smallest diff, upstream way): restore the private
  `gpioChipScore` in GpioInput.cpp (zero diff in that region) and let `GpioChipInfo.cpp` be the Controls model's own
  copy with a comment naming the three others. Alternative if the owner wants the "same chip" guarantee: all three
  users call `hardware::gpioChipScore`, the two output copies deleted in the same commit.

### F9 IMU write target (minor, removed-upstream-behaviour)

- Upstream: setters write `config.configPath`, the file the IMU loader found (candidates env -> `/home/pi` ->
  `/boot/firmware` -> `/boot`, `Mpu6050RecordingSession.cpp:191-205,855-860,1297-1300 @upstream`); default only
  when none was found.
- Port: always `HardwareConfigStore::defaultPath()` = env or `/home/pi/apertar-hardware.conf`
  (`HardwareConfigStore.cpp:118-123 @port`). Commit c509e9f says so.
- Effect: on a rig whose only file is `/boot/firmware/apertar-hardware.conf`, an IMU calibration creates a sparse
  `/home/pi` file; the outputs, INA219 and IMU use the first file that exists (conv section 2), so on the next start
  they lose their `/boot/firmware` settings. Rare: the UI first-run template creates `/home/pi/...` anyway
  (`UI/src/DisplayConfigBridge.cpp:41-58 @upstream`). Probable, not run.
- Matches HW-S10 "write only the editable path", so the port's choice is defensible; fix is to log a journal line
  when the loader's file differs from the store path, or have the store refuse to create the file when a `/boot`
  copy exists.

### F10 Provenance comments (nit, slop)

`ButtonGesture.hpp:2` "the way Cinemate's SmartButton counts them (cinemate src/module/gpio_input.py)";
`GpioInput.cpp:623,662,735 @port` "Like Cinemate"; `GpioInput.hpp:21,37,93`, `Pcf8574Input.hpp:21,39`,
`NeoRotary4Input.hpp:23,34`, `TriggerOutput.hpp:30` name "the WebUI's Listen" / "Test button". The original developer
does not know Cinemate; `src/hardware/` is app-agnostic (HW-S8). Rework: say what the code does (timing, why invert),
drop project names and UI feature names. No ticket numbers in the 11 files (the `T42` is in App, outside scope).

### F11 Enum-indexed suffix arrays (nit)

`static const char *const suffixes[] = {"", "_single", ...}` indexed by `static_cast<size_t>(event)` in three files
(GpioInput diff 491, NeoRotary4 1440, Pcf8574 1727); reordering `ButtonGesture::Event` silently mislabels Listen.
Rework: one `inline const char *suffix(ButtonGesture::Event)` switch in `ButtonGesture.hpp`.

## 2. Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `hardware::ButtonGesture` (ButtonGesture.hpp) | keep | Same shape as upstream `PowerButtonGesture.hpp`: header-only, pure, fed with ms. Needs `consume()` (F1) and kernel timestamps (F3). Constants fixed in code fit HW-N3 |
| `hardware::actions` / ActionCatalog.hpp | keep (simplify) | Upstream HW-I5 keeps three byte-identical copies, but the developer already started sharing in `ButtonActionList.hpp`; the catalog is the natural next step and needed by `list_actions`. Aliases verified equal. Simplify: `catalogJson()` (nested JSON) and `classify`/`suggestion` serve App only; their place is App (reply building lives there, command-plane unit) |
| `canonicalAnalogTarget`, `canonicalTriggerEvent` | keep | Text moved unchanged; `kTriggerEvents` feeds the Outputs card |
| `GpioChipInfo` (`gpioChipScore`, `headerGpioChipPath`, `readGpioChipInfo`) | simplify | Read-only chip facts are new ground for the Controls page and fine; the half-move of `gpioChipScore` is not (F8) |
| `HardwareConfigStore` + `hwconf::` as IMU writer | keep (conditional on HW-config-text-store unit) | Fixes the non-atomic remove-then-rename the conventions challenge itself flags (HW-S6 challenge row). If the store is reworked away, restore upstream `writeHardwareConfigValue`/`updateImuBiasConfig` and fix only the rename fallback. Note UI `GyroConfigBridge.cpp:373` still writes the same file with `QSaveFile`, outside the store lock (HW-N5 accepted that upstream) |
| `RuntimeSwitch`, `SwitchMapping`, `buttonDrafts`/`switchDrafts` | keep | Header structs with in-class defaults (HW-I2); flat `else if` key parse (HW-I1) |
| `process`/`sleepMs` lambdas | rework-to-upstream-pattern | F4 |
| seen callback + `"section|key"` strings | simplify | Inject via ctor (F7); one suffix helper (F11) |
| `TriggerOutput::testPulse()` | keep | Small, reuses the worker queue and `kMaxQueuedPulses`; called from a command, not recording code, so HW-S4 holds |

## 3. Conforms

- Config parsing stays per class, in each `loadConfig()`, flat `else if (field == ...)` chains, defaults in header
  `Config` structs (HW-S2, HW-I1, HW-I2): `GpioInput.cpp` loadConfig, `Pcf8574Input.cpp:284-303`,
  `NeoRotary4Input.cpp:339-350 @port`.
- New keys are additive suffixes (`dN_single`, `pinN_hold`, `encoderN_double`); old files read the same. `[gpio_switches]`
  reuses `[gpio_buttons]` chip, pull, active_low, debounce rather than new keys.
- Edge events use the raw GPIO v2 uAPI flags, no libgpiod (HW-I6); fallback to `poll_ms` keeps the old path for chips
  without IRQs; one thread per device kept (HW-I4 spirit).
- `RecordingIndicatorOutput` dedupes onto the existing upstream `hardware::isOutputAction`.
- All actions still go through the injected callback to `handleHardwareInputAction` (HW-S3); no app includes in
  `src/hardware/` (HW-S8).
- Errors and the 1-0-1 note are one `std::cerr` line with a device prefix (HW-I3).
- Chip scoring logic unchanged (HW-I7 values), no Pi-model switch.
