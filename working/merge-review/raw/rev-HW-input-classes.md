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

## Skeptic

Checked at `@cinemate-port` = `/home/user/Apertar-Core` 01f170c, `@upstream-1.6.0` = `/home/user/wt/core-upstream`.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | stands | Confirmed: `ButtonGesture::update` (ButtonGesture.hpp:21-55) counts the wake press; `emitAction` is void (GpioInput.cpp:565-570); App in Standby dispatches `wake` and returns (App:10312-10318). Upstream GpioInput fires Press only (GpioInput.cpp:691-710@upstream), so a wake press there had no follow-up; `StandbyPowerButtonInput.cpp:66-71@upstream` is the consume precedent. Note: `emitAction` skips an empty action, so with no Press mapped the first gesture (Single/Hold) is the wake and must be consumed too |
| F2 | corrected | Code confirmed (Pcf8574Input.cpp:411-433; GpioInput.cpp:742-815 rebuilds RuntimeButton/RuntimeSwitch on reopen). Needs a held button at the exact moment of a read failure: rare. Severity major -> minor. Added: the Controls worker also stops and starts GPIO and PCF on every save of their sections (App:12302-12319), which re-runs the same decisions; that part is a `start()` re-run, see F6 |
| F3 | corrected | eventfd precedent confirmed (StandbyPowerButtonInput.cpp:16-31,50-56@upstream). Upstream GpioInput itself has no stop fd and sleeps `pollMs` (GpioInput.cpp:741@upstream). Timestamp point is weak: within one batch only order matters for encoders and debounce. Deliberate -> no (edges were chosen, the stop/timestamp shape was not discussed) |
| F4 | stands | `process` lambda GpioInput.cpp:618-712 (about 95 lines), `sleepMs` :716-731, `toMs` :612-615. Upstream run() has only the 4-line `addOffset` lambda (GpioInput.cpp:625-628@upstream) |
| F5 | stands | Confirmed GpioInput.cpp:829-847: at most 16 events per read, then the unconditional `readLineValues` at :849. Rising/falling set the bit absolutely, so later stale events move an encoder back in time. Probable, not run on hardware |
| F6 | corrected | Confirmed toggles: `zebra`, `focus_peaking` ... call `toggleSharedUiBoolAction` (App:10638-10676). Added: every Controls save touching `[gpio_buttons]`/`[gpio_switches]`/PCF restarts GpioInput (App:12302-12319), and the start-apply (GpioInput.cpp:660-668) fires again, so a toggle switch flips on each save, not only at Core start |
| F7 | corrected | Setter confirmed (GpioInput.hpp:22, Pcf8574Input.hpp:22, NeoRotary4Input.hpp:24; App:8118-8120). Upstream does use setters for an internal class (`setErrorCallback`, CameraController.cpp:5020-5021@upstream), but every public hardware input class takes its callbacks in the ctor. Severity minor -> nit |
| F8 | stands | GpioChipInfo.cpp:31, TriggerOutput.cpp:195, RecordingIndicatorOutput.cpp:191 @port; upstream has three private copies (GpioInput.cpp:238, TriggerOutput.cpp:201, RecordingIndicatorOutput.cpp:198) |
| F9 | corrected | Upstream App already writes WebUI saves to `editableHardwareConfigPath()` (App:4271-4276,5343@upstream), so the editable-path rule is upstream's; only the IMU used the loader's path. Real hazard is narrower: the store treats a missing file as empty (HardwareConfigStore.cpp:160-163) and creates it with only the IMU keys. Severity minor -> nit; rework changed |
| F10 | stands | Lines confirmed; `grep -i webui src/hardware` at upstream returns nothing |
| F11 | corrected | Three copies confirmed (GpioInput.cpp:643, Pcf8574Input.cpp:458, NeoRotary4Input.cpp:634), but the NeoRotary array starts with "_press" and GPIO swaps index 0 for `pressSuffix`: the helper must return "" for Press and let callers add their press suffix |

## Final findings

### HW-input-classes-F1 [removed-upstream-behaviour, major] Standby wake press seeds click/Hold gestures; upstream consumes the wake press
- where: src/hardware/ButtonGesture.hpp:21-55@cinemate-port ; src/hardware/GpioInput.cpp:641-653,565-570@cinemate-port ; src/hardware/Pcf8574Input.cpp:454-467@cinemate-port ; src/hardware/NeoRotary4Input.cpp:632-650@cinemate-port ; src/ApertarCoreApp.cpp:10312-10318@cinemate-port
- port: ButtonGesture counts every press, including the one App swallowed to wake from Standby. emitAction is void, so the input class never learns of the wake. Single/Double/Triple/Hold fire later, with the camera awake, and run.
- apertar way: StandbyPowerButtonInput.cpp:66-71@upstream-1.6.0 `gesture.consume(); // A wake press cannot seed another sleep.`, callback `std::function<bool(bool)>` (StandbyPowerButtonInput.hpp:8,14); upstream GpioInput fires Press only (GpioInput.cpp:691-710@upstream-1.6.0), so a wake press had no follow-up. Config comment App:4360@upstream-1.6.0: "a button press wakes only".
- why it matters: d17=record_toggle, d17_hold=standby: holding d17 3 s in Standby wakes the camera and puts it back to sleep. d17_double=photo: a double click in Standby wakes and takes a photo.
- rework: Add ButtonGesture::consume() (clear clicks_, set longPress_ and holdFired_ while down). handleHardwareInputAction returns bool (true when it dispatched wake). Button ActionCallback in GpioInput, Pcf8574Input, NeoRotary4Input becomes std::function<bool(const std::string&)>; emitAction returns its result (false for an empty action); on true call gesture.consume(). Rotation callback stays void.
- effort: S. deliberate: no (decisions.md gesture entries and commits 0a98868, c140c4f never mention Standby).

### HW-input-classes-F2 [bug, minor] 1-0-1 inversion and switch start-apply re-run on every device reopen
- where: src/hardware/Pcf8574Input.cpp:409-433@cinemate-port ; src/hardware/GpioInput.cpp:742-815,620-668@cinemate-port
- port: haveSample (PCF) and the rebuilt RuntimeButton/RuntimeSwitch vectors (GPIO) are reset on every reopen after a read or poll failure; invertedMask, RuntimeButton.inverted and switch stable=-2 are decided again. A button held at that moment becomes inverted; a 1-0-1 button held then loses its inversion; every GPIO switch fires its position action again.
- apertar way: Upstream reopen only re-seeds observed/stable state, no polarity state (GpioInput.cpp:643-679,690-697@upstream-1.6.0; Pcf8574Input.cpp:479-505@upstream-1.6.0). decisions.md:39 limits the caveat to "held down while Core starts".
- why it matters: Shared I2C bus (INA219, CFE hat) gives read errors; a held record button then stays inverted until restart and each release toggles recording. Rare (needs a held button at the failing read).
- rework: Keep polarity and "switch applied" in run-scope state outside the reopen block (an array per pin / per button index), decided on the first sample after start() only; reopen re-seeds observed/stable as upstream.
- effort: S. deliberate: no (decision text says "at Core start" only).

### HW-input-classes-F3 [mismatch, minor] Edge-event loop stops via a 250 ms idle wake, not an eventfd as upstream's poll() input does
- where: src/hardware/GpioInput.cpp:714-731 (sleepMs, kIdleWakeMs=250), 818-847@cinemate-port
- port: poll() with timeout at most 250 ms so stop() is noticed; a full readLineValues after every wake; every event in a batch stamped steady_clock::now().
- apertar way: StandbyPowerButtonInput.cpp:16-31,50-56@upstream-1.6.0: eventfd stopFd_ polled next to the device, timeout -1. PowerButtonGesture.hpp:4@upstream-1.6.0 uses evdev timestamps. (Upstream GpioInput polls every pollMs with sleep_for, GpioInput.cpp:741@upstream-1.6.0.)
- why it matters: The commit's aim (no periodic wake) is half met: the thread wakes 4 times a second idle. stop() can lag 250 ms, paid on every Controls save that restarts GPIO. Timestamps matter less (order is kept within a batch).
- rework: Add stopFd_ (eventfd) as in StandbyPowerButtonInput; stop() writes it; run() polls both fds with timeout = next debounce/gesture deadline or -1. Optional: use gpio_v2_line_event::timestamp_ns (CLOCK_MONOTONIC) as nowMs per edge.
- effort: S. deliberate: no (decisions.md:41 and commit 0c49601 choose edge events; the stop and timestamp shape is not discussed).

### HW-input-classes-F4 [mismatch, minor] GpioInput::run() rebuilt around large capturing lambdas
- where: src/hardware/GpioInput.cpp:618-712 (process), 716-731 (sleepMs), 612-615 (toMs)@cinemate-port
- port: A capturing lambda of about 95 lines and two smaller ones inside run().
- apertar way: GpioInput.cpp:621-745@upstream-1.6.0 is one straight loop with only a 4-line addOffset lambda; helpers are private members (readLineValues, emitAction, setLastError).
- why it matters: Reads as foreign, harder to step through; the original developer expects member functions.
- rework: Private members, e.g. void processLevels(uint64_t levels, steady_clock::time_point now) and int wakeTimeoutMs(int64_t nowMs) const, with buttons/encoders/switches in a run-state struct passed in or held as members.
- effort: S. deliberate: no.

### HW-input-classes-F5 [bug, minor] Edge drain applies stale queued edges on top of a fresh full-level read
- where: src/hardware/GpioInput.cpp:829-847, 849@cinemate-port
- port: Each wake reads at most 16 events, then always does a full readLineValues + process. Events 17..N, read on the next loop, set their bits absolutely onto a state that already holds the newer level.
- apertar way: no precedent (upstream polls levels only).
- why it matters: Probable: a fast encoder spin with more than 16 queued edges replays old quadrature states, giving spurious reverse steps. Not run on hardware.
- rework: Drain until read returns fewer than 16 events (poll timeout 0 or non-blocking read); do the catch-up full read only when the wake had no events.
- effort: S. deliberate: no.

### HW-input-classes-F6 [new-ground, minor] Switch positions apply toggle actions at start and on every Controls save; position and state drift
- where: src/hardware/GpioInput.cpp:656-686@cinemate-port ; GpioInput.cpp loadConfig gpio_switches@cinemate-port ; src/ApertarCoreApp.cpp:12302-12319,10638-10676@cinemate-port
- port: [gpio_switches] applies the position action at each GpioInput start and on each change. GpioInput is restarted on every save that touches the GPIO/PCF group. The monitoring vocabulary is toggles (zebra, focus_peaking ... -> toggleSharedUiBoolAction).
- apertar way: no precedent; upstream inputs fire on press edges only (GpioInput.cpp:691-710@upstream-1.6.0). Absolute settings exist only as parametric tokens (iso800, fps24, wb5600).
- why it matters: switch0_on=zebra, switch0_off=zebra, zebra saved on, switch in the on position: zebra turns off at Core start, and flips again on every Controls save of the GPIO group.
- rework: Keep the switches. Enforce in the validator/Controls page that switch positions take absolute actions only; if on/off are wanted, add *_on/*_off handlers in App ending in dispatch. Apply the start position only at Core start, not on Controls-worker restarts.
- effort: S. deliberate: yes (decisions.md:37,42; commit c34f844 "as in Cinemate").

### HW-input-classes-F7 [mismatch, nit] Seen callback injected by setter, not constructor
- where: src/hardware/GpioInput.hpp:21-22@cinemate-port ; src/hardware/Pcf8574Input.hpp:21-22@cinemate-port ; src/hardware/NeoRotary4Input.hpp:23-24@cinemate-port ; src/ApertarCoreApp.cpp:8118-8120@cinemate-port
- port: setSeenCallback(ActionCallback) on three classes, called in App::start() before each start(), comment "// T42 Listen".
- apertar way: Public hardware inputs take callbacks in the ctor (GpioInput.hpp:17@upstream-1.6.0; App:6785-6792@upstream-1.6.0 member-init list). Setters exist only on an internal class (CameraController.cpp:5020-5021@upstream-1.6.0).
- why it matters: A second wiring style; the unsynchronised member is safe only because it is set before start().
- rework: Ctor parameter ActionCallback seenCallback = {} on the three classes; pass [this](const std::string &k){ noteInputSeen(k); } in App's member-init list; delete the setters and the T42 comment.
- effort: S. deliberate: no.

### HW-input-classes-F8 [duplication, minor] gpioChipScore half-shared: one moved, two private copies remain
- where: src/hardware/GpioChipInfo.cpp:31-55@cinemate-port ; src/hardware/TriggerOutput.cpp:195@cinemate-port ; src/hardware/RecordingIndicatorOutput.cpp:191@cinemate-port ; src/hardware/GpioInput.cpp:475@cinemate-port
- port: GpioInput calls hardware::gpioChipScore in GpioChipInfo.cpp; Trigger and LED keep their own copies.
- apertar way: Each GPIO user carries its own gpioChipScore (GpioInput.cpp:238, TriggerOutput.cpp:201, RecordingIndicatorOutput.cpp:198@upstream-1.6.0).
- why it matters: Follows neither convention; a scoring change has to be made in three places, one in a new file.
- rework: Since GpioChipInfo is kept for the Controls chip view (user request), make all three users call hardware::gpioChipScore and delete the two output copies in one commit. Smaller alternative: restore the private copy in GpioInput.cpp and comment GpioChipInfo's copy as the page's mirror.
- effort: S. deliberate: yes (commit 166cc4d moves scoring so GpioInput and the page pick the same chip; outputs not addressed).

### HW-input-classes-F9 [removed-upstream-behaviour, nit] IMU writes can create a sparse ~/apertar-hardware.conf that shadows /boot/firmware
- where: src/hardware/Mpu6050RecordingSession.cpp:603-628@cinemate-port ; src/hardware/HardwareConfigStore.cpp:118-123,160-163@cinemate-port
- port: writeHardwareConfigValues -> configStore().edit(...); store path = env or /home/pi/apertar-hardware.conf; a missing file is treated as empty and created with only the IMU keys.
- apertar way: Upstream IMU wrote the loader's file, falling back to defaultHardwareConfigPath() (Mpu6050RecordingSession.cpp:1297-1300,1360-1362@upstream-1.6.0). Upstream App already writes WebUI saves to editableHardwareConfigPath() (App:4271-4276,5343@upstream-1.6.0), so the editable-path rule itself is upstream's.
- why it matters: Probable, rare: with only /boot/firmware/apertar-hardware.conf present, one calibration creates a /home/pi file holding only [mpu6050] keys; every loader reads the first existing file, so all other settings are lost on next start. The UI first-run template usually creates /home/pi first.
- rework: Keep the store. When the store file does not exist and the loader found another candidate, seed the store file from that file's text before the edit (or refuse with an error naming both paths).
- effort: S. deliberate: yes (commit c509e9f "The store always writes the editable path").

### HW-input-classes-F10 [slop, nit] Comments narrate Cinemate provenance and WebUI features inside src/hardware
- where: src/hardware/ButtonGesture.hpp:2-3@cinemate-port ; src/hardware/GpioInput.cpp:623,662,667,735@cinemate-port ; src/hardware/GpioInput.hpp:21,37,93@cinemate-port ; src/hardware/Pcf8574Input.cpp:425@cinemate-port ; src/hardware/Pcf8574Input.hpp:21,39@cinemate-port ; src/hardware/NeoRotary4Input.hpp:23,34@cinemate-port ; src/hardware/TriggerOutput.hpp:30@cinemate-port
- port: "Like Cinemate", "cinemate src/module/gpio_input.py", "the WebUI's Listen", "the WebUI's Test button".
- apertar way: Upstream hardware comments state behaviour only (PowerButtonGesture.hpp:4,26@upstream-1.6.0); no upstream src/hardware file mentions the WebUI.
- why it matters: The original developer does not know Cinemate; UI feature names leak app knowledge into src/hardware.
- rework: Rewrite each comment to state behaviour and reason; drop project and UI feature names.
- effort: S. deliberate: no.

### HW-input-classes-F11 [duplication, nit] Seen-key suffixes chosen by static_cast of the gesture enum into parallel arrays, three copies
- where: src/hardware/GpioInput.cpp:643-645@cinemate-port ; src/hardware/Pcf8574Input.cpp:458-459@cinemate-port ; src/hardware/NeoRotary4Input.cpp:634-635@cinemate-port
- port: static const char *const suffixes[] indexed by static_cast<size_t>(event), three times; the NeoRotary copy starts with "_press", GPIO replaces index 0 by pressSuffix.
- apertar way: no precedent.
- why it matters: Reordering ButtonGesture::Event silently gives Listen the wrong key.
- rework: One inline const char *gestureSuffix(ButtonGesture::Event) switch in ButtonGesture.hpp returning "" for Press; callers add their own press suffix.
- effort: S. deliberate: no.
