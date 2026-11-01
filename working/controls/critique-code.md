# Code critique: `design-controls.md` (v1) checked against the code

2026-10-28, code critic pass. Read-only on every tree. The only file written is this one. Scratch builds went to
`scratchpad/critic-build/` (test programs, an extracted page script).

Trees: Core `scratchpad/controls/core-tip` `0296ed1` (`App` = `src/ApertarCoreApp.cpp`, `App.hpp`, `HW/` =
`src/hardware/`, `Web` = `src/web/WebControlPage.cpp`, `WS` = `src/web/WebServer.cpp`, `CS` =
`src/ipc/ControlServer.cpp`, `CP` = `src/ipc/ControlProtocol.cpp`, `SF` = `src/util/SettingsFile.hpp`). Touch UI
`scratchpad/controls/ui-tip` `5aab7e2` (`UI:`). KB `/home/user/apertar-kb` `b47f700` (`tutorial.py` =
`tutorials/tutorial.py`, `core.py` = `working/tools/core.py`). Sketch = `scratchpad/controls/sketch/`.

Labels: **CONFIRMED** = I opened the line or ran the command. **PROBABLE** = derived; the derivation is given.
**UNCONFIRMED** = only the Pi can settle it.

---

## 0. Verdict

- **The decision holds.** Keeping `~/apertar-hardware.conf` with Core as the writer, a reload worker outside
  `commandMutex_`, and one action header all fit the code. The deadlock reasoning in F7 is right. `stop()` joins the
  driver thread (`HW/NeoRotary4Input.cpp:332-337`). A driver thread can be blocked in `dispatchHardwareInputCommand`
  → `handleCommand` → `commandMutex_` (`App:8636-8644`, `App:9485`). CONFIRMED.
- **Citations are good.** All 22 tutor `ref` anchors match their line and occur once. Every §6 search string is
  present. Only one is ambiguous (B5). I spot-checked about 60 `path:line` citations and none was wrong. Details in §3.
- **The design is not ready to hand over yet.** These must change first:
  - Seven problems in the live-reload path (A1-A7). Two of them are data races that would be undefined behaviour.
  - Four plan rows that do not compile as written (B1-B4).
  - Five protocol mismatches (C1-C5). One is a 64 KiB request cap on the socket that makes the text editor fail
    silently.
  - Four sketch or validator bugs I reproduced on the host (D1-D4).
  - One measurement that is not read-only for the camera (H1): it can fire phantom knob turns.
- The vocabulary can be unified only in part: names, yes; behaviour, no. The dispatcher stays a separate if-chain, and
  three more vocabularies are left out of T36 (E1).

---

## 1. What I ran on the host

| Check | Result | Label |
| --- | --- | --- |
| Sketch test, `g++ -std=c++20 -Wall -Wextra -Werror` | `all ok: 51 of 51 checks`; `355 of 355 tokens identical` | CONFIRMED |
| `make_old.sh core-tip` rebuilt against the tree | identical to `old_normalizers.inc` (header line aside) | CONFIRMED |
| `t34/hostcheck-core.sh core-tip` (with libcamera headers) | `CameraController.cpp`, `ApertarCoreApp.cpp`, `WebControlPage.cpp`: 0 errors, 0 warnings | CONFIRMED |
| `g++ -fsyntax-only -Isrc -Iinclude` on `App` (without libcamera) and on 7 `HW/*.cpp` files | 0 errors each | CONFIRMED |
| Page script extracted from `Web` (`<script>`…`</script>`) + `node --check` | OK. Today 7,616 lines and 348 KB of script in a 481 KB file | CONFIRMED |
| `diff <(sed -n 108,202p GpioInput.cpp) <(sed -n 121,215p NeoRotary4Input.cpp)` (T36 3.2) | no differences, as predicted | CONFIRMED |
| Tutor `ref` lines (T36, T37) checked against the trees | 22 of 22 OK (line matches, one occurrence) | CONFIRMED |
| `grep -c 'std::filesystem::remove(path, ec);' HW/Mpu6050RecordingSession.cpp` (T37 check 3.1) | `2` (lines 702, 831) | CONFIRMED |
| New probes of the sketch (`critic-build/t_events.cpp`, `t_ids.cpp`) | four bugs, see D1-D4 | CONFIRMED |

---

## 2. Problems, with evidence and a fix

Severity:
- **Blocker:** wrong behaviour, undefined behaviour, a compile failure, or lost config.
- **Major:** misleading to Patrik, or a tutorial step that fails.
- **Minor:** wording, or a small gap.

### A. Live reload: threads and locks (§3.6, T38)

**A1. Blocker: the driver status accessors race with the reload.**
- **Problem.** `hardware_status` (§3.5) is built on the web thread (`/api/state`) and on the socket thread
  (`get_state`) from `enabled()`, `configPath()` and a new `running()`.
  - For the four input drivers, `enabled()` and `configPath()` read `config_` without any lock: `HW/GpioInput.cpp:357-365`,
    `HW/Pcf8574Input.cpp:302-310`, `HW/NeoRotary4Input.cpp:339-347`, `HW/GroveAnalogInput.cpp:230-238`.
  - The worker's `start()` assigns that same object: `config_ = loadConfig();` (`GpioInput.cpp:332`,
    `Pcf8574Input.cpp:276`, `NeoRotary4Input.cpp:313`, `GroveAnalogInput.cpp:204`).
  - Today this is safe only because `start()` runs once, before any reader exists. After T38, copying a `std::string`
    while it is being assigned is undefined behaviour. CONFIRMED (code); a crash is PROBABLE.
- **Fix.**
  - The worker builds a status snapshot after each reload and stores it under `controlsMutex_`. Per driver it holds
    `enabled`, `bus`, `address` and `configPath`, copied on the worker thread.
  - The state builders read that snapshot, plus `lastError()` (locked) and the running flag.
  - Never call `enabled()` or `configPath()` from another thread.

**A2. Blocker for two drivers: the proposed `running()` is a data race, and "running" does not mean "connected".**
- **The race (38.4).** The plan writes `bool running() const { return running_; }` for all six drivers.
  - The inputs are fine: their `running_` is a `std::atomic<bool>` (`HW/GpioInput.hpp:93` and the same in the other
    three).
  - The outputs are not: `TriggerOutput` and `RecordingIndicatorOutput` keep `bool running_` under `stateMutex_`
    (`HW/TriggerOutput.hpp:85-89`, `HW/RecordingIndicatorOutput.hpp:77-80`).
- **Running is not connected.** An input thread keeps running while it waits in its retry loop on a missing bus
  (`HW/NeoRotary4Input.cpp:631-638`).
- **Stale errors.** The inputs' `start()` never clears `lastError_` (`NeoRotary4Input.cpp:310-329`,
  `GpioInput.cpp:329-347`). A driver you turn off keeps showing its old error. CONFIRMED.
- **Fix.**
  - For the outputs, take `stateMutex_` inside `running()`.
  - Derive "connected" as running, with `lastError()` empty, and after the first good open: add an atomic
    `opened_`, set where `setLastError({})` runs after an open.
  - Clear `lastError_` at the top of each input's `start()`.

**A3. Blocker: "Saved; Core applied it." (§3.7) contradicts the asynchronous apply, and a synchronous apply would
deadlock.**
- **Problem.** `set_controls` runs inside `handleCommand`, under `commandMutex_` (`App:9485`).
  - If the handler waited for the worker, it would wait on a `join()` of a driver thread.
  - That driver thread can itself be waiting for `commandMutex_` (`App:8636-8644`).
  - So the lock graph is a cycle. CONFIRMED (lines); PROBABLE (cycle).
- **Fix.** `set_controls` and `apply_controls` only queue the reload. Reply
  `apply:{core:"queued"}` and "Saved. Core is applying it." The page waits for `controls_applied_revision`, as M8
  already plans. State it as a rule in §3.6: no command handler ever waits on the worker.

**A4. Blocker: every store write restarts all six drivers. That includes IMU writes, and it applies pending outside
edits and their errors without `force`.**
- **Problem.** §3.6 restarts the six drivers "after a save". 37.5 routes the IMU commands through the store. So each
  of these would restart all drivers:
  - a sync-offset click;
  - `set_imu_level_reference`, which is 5 separate writes (`HW/Mpu6050RecordingSession.cpp:1363-1367`);
  - `clear_imu_level_reference`, which is 4 writes (`:1376-1379`).
- **What each restart costs.** CONFIRMED (lines):
  - Buttons go dead for up to ~4 s (A6).
  - The NeoRotary throws away the knob movement it has accumulated (`HW/NeoRotary4Input.cpp:643-647`).
  - With `emit_on_start=true`, the Grove ADC sends every knob position again. That calls `set_iso`, `set_fps` and
    `set_resolution` on each save (`HW/GroveAnalogInput.cpp:465-469`).
  - The 20-version history fills with IMU entries.
- **Outside edits get applied.** A key edit is merged into the current file, which includes any hand edit not yet
  applied. The reload then applies that hand edit. Its errors count as "old" (`newErrors`), so a hand edit with
  errors gets applied without the `force=true` that `apply_controls` requires. CONFIRMED (sketch semantics, §3.4
  step 5).
- **Fix.**
  - (a) Make each multi-key IMU command one store edit.
  - (b) The worker diffs the sections between the applied text and the current text. It restarts only the drivers
    whose sections changed, and restarts none for `imu`, `display`, `network` or `run_script`.
  - (c) While `controls_outside` is true, `set_controls` refuses unless `adopt_outside=true`. The dry-run diff shows
    those lines, and errors among them still need `force`.
  - (d) IMU versions do not count against the 20 kept versions (separate cap or skip).

**A5. Major: the recording gate is checked at save time, not at reload time, and the LED re-sync can lose a take's
tally.**
- **Problem.** The worker runs after the reply, so a take can start in between.
  - The reload then stops the tally and the trigger. `TriggerOutput::stop()` drives the output inactive
    (`HW/TriggerOutput.cpp:429-447`).
- **The re-sync race.** The re-sync reads `camera_.isRecording()`, then calls `setRecordingActive()`.
  - A `record_start` can publish `recording active` between those two calls.
  - The worker's stale `false` then overwrites it, and the tally stays off for the whole take.
  - While stopped, the LED ignores setters (`HW/RecordingIndicatorOutput.cpp:491-499`, `if (!enabled_ || !running_)
    return;`).
  - PROBABLE (narrow window).
- **Fix.**
  - The worker checks the gate right before `stop()`. During a take it marks the reload pending and runs it when
    the take ends.
  - Do the two re-sync lines under `commandMutex_`: the worker holds nothing else and joins nothing there, and the
    commands publish recording events under that lock.

**A6. Major: a reload can take about 4 s, not about 1 s (M8).**
- **Problem.** The six stops run one after another, and each waits out its thread's current 1 s retry sleep:
  - `HW/NeoRotary4Input.cpp:637`;
  - `HW/Pcf8574Input.cpp:483`;
  - `HW/GroveAnalogInput.cpp:449`;
  - `HW/GpioInput.cpp:647`.
- **Example.** With bus 1 missing, the PCF8574, NeoRotary and Grove ADC all sit in that sleep, about 3-4 s in
  total. CONFIRMED (lines); the total is PROBABLE.
- **Fix: stop in two phases.**
  - Give the four inputs `requestStop()` (`running_ = false`).
  - Change `stop()` to `running_.store(false); if (thread_.joinable()) thread_.join();`. Today's `if
    (!running_.exchange(false)) return;` would skip the join after a `requestStop()`.
  - The worker calls `requestStop()` on all of them, then `stop()` on each.
  - Update the M8 prediction.

**A7. Minor: the "outside change" classification.**
- **The race.** The worker can stat the new file after the store's rename but before the store records
  `written_revision`. That gives a false "Changed outside Apertar" banner. PROBABLE.
- **Noise from the touch UI.** Until T43, every orientation or sync tweak on the touch UI's gyro page is an outside
  write (`UI:src/GyroConfigBridge.cpp:1577`, QSaveFile). It would raise "Changed outside … Not applied" for a change
  that needs no apply. CONFIRMED (writer).
- **Fix.**
  - Record the written revision under the store mutex before the rename. The worker classifies under the same
    mutex.
  - Set `controls_outside` only when sections that need a reload changed.
  - Key the stat cache on inode and ctime as well as mtime and size: a rename changes the inode.

PCF8574 "interrupts": none exist. The PCF8574 driver polls every 40 ms and nothing in `src/hardware` uses an INT line
(grep `interrupt|irq|int_gpio`: no hits). CONFIRMED.

What a reload does change for the PCF8574:
- Every open writes `0xff` to the whole chip (`HW/Pcf8574Input.cpp:416`, `:426-430`).
- The trigger copies the live byte at open (`HW/TriggerOutput.cpp:640-644`).
- So with a shared chip, the R2 §2.14 glitches now happen on every save, not only at boot. PROBABLE.

The design's order (LED last, then re-sync) is right. Add a validator warning when inputs and an output share one
PCF8574.

### B. Plan rows that do not compile as written

**B1. Blocker (38.5): `readIna219Snapshot()` cannot see the member `hardwareConfigGeneration_`.**
- **Problem.** It is a free function inside the anonymous namespace: `App:60` opens it, `App:6919` closes it, and the
  function is at `App:4693`. Its caller `readPowerSupplySnapshot()` (`App:4757`) is also free. CONFIRMED.
- **Fix.** Use a file-scope `std::atomic<uint64_t> gHardwareConfigGeneration` in the anonymous namespace, which the
  worker bumps. Or pass the generation in: `readPowerSupplySnapshot(uint64_t generation)` from `buildWebStateJson`.

**B2. Blocker (38.6): `CfeHatReader` is neither copyable nor assignable.**
- **Problem.** See `src/util/CfeHat.hpp:32-33`. "Rebuild `CfeHatReader` in the loop" therefore cannot assign a new
  one to `hat`. CONFIRMED.
- **Fix.** Use `std::optional<CfeHatReader> hat; hat.emplace(loadCfeHatConfig());`. Re-emplace it when the
  generation changes, and log the new bus as `App:9312-9313` does.

**B3. Blocker (38.1): `std::mutex controlsMutex_` is locked from `const` methods.**
- **Problem.** `buildWebStateJson() const` (`App:7857`) would read `appliedRevision_` and the status under it. The
  header's pattern is `mutable std::mutex` (`App.hpp:168`, `:189`). Likewise
  `hardwareConfig_.currentRevision()` is called from that `const` method and updates a stat cache. CONFIRMED.
- **Fix.** Declare `mutable std::mutex controlsMutex_;`. Make `HardwareConfigStore::currentRevision() const` with
  `mutable` cache members and a `mutable std::mutex`.

**B4. Blocker (37.5): the IMU writers cannot reach a store that App owns.**
- **Problem.** `writeHardwareConfigValue` and `updateImuBiasConfig` are free functions in
  `HW/Mpu6050RecordingSession.cpp:604`, `:715`. Static members call them (`setConfiguredDriver`, `:1295-1300`, and
  the rest). They write to `config.configPath`, the path the IMU loader found, which can be a `/boot` copy. CONFIRMED.
- **Fix.** Make the store a single store for the whole process: `apertar::hardware::configStore()`, returning a
  function-local static. App and the IMU code both use it, and it always writes `editableHardwareConfigPath()`.
  Then 37.5's bodies become one call each.

**B5. Minor (38.9): the search string occurs twice.**
- **Problem.** `eventJson.find("\"event\":\"still_exposure\"")` is at `App:11300` (the whitelist) and `App:11324`
  (`handleTriggerEvent`). CONFIRMED.
- **Fix.** Use `eventJson.find("\"event\":\"media_write_state\"")`, which occurs once (`App:11301`).

### C. Commands, protocol, reply style

**C1. Blocker for text mode over the socket: request lines are capped at 64 KiB.**
- **Problem.** `CS:259-261`: `if (line.size() >= 64 * 1024) return;` drops the client, with no reply.
  - So `core.py set_controls text=…` fails silently above about 60 KiB once JSON-escaped.
  - The design promises 256 KiB, and F15 cites only the HTTP limit (`WS:23`, 1 MiB). CONFIRMED.
- **Fix.** Say it in §3.5. The WebUI text mode uses `/api/command` (1 MiB). Either raise the socket limit to
  `kMaxEditableHardwareConfigBytes * 2 + 4096` (one constant in `CS`, added to the plan), or document the limit for
  `core.py`.

**C2. Major: a refusal cannot carry `issues[]` or `conflicts[]`, and the WebUI helper drops them.**
- **Problem.** `errorReply(id, message)` writes only `"error"` (`App:122-130`). The WebUI's `sendCommand`
  (`Web:9148-9180`) throws with `result.error` alone when `!result.ok`. It also patches and re-renders the camera
  snapshot and schedules a state refresh. CONFIRMED.
- **Fix.** Add `errorReplyBody(int id, const std::string &message, const std::string &body)` next to `App:122`. The
  Controls and Config panels use their own `controlsCommand(payload)` fetch, which returns the whole JSON and never
  touches `state.snapshot`.

**C3. Major: every command runs under `commandMutex_`, scans and probes included.**
- **Problem.** `handleCommand` locks on its first line (`App:9485`). `scan_i2c all=true` covers 112 addresses. With
  the seesaw-style 10 ms select→read, or kernel timeouts on a stuck bus, it would hold the camera's command lock for
  a second or more. Every hardware button waits too, because buttons go through `handleCommand`. CONFIRMED (lock);
  the duration is PROBABLE.
- **Fix.** Handle the read-only hardware commands before the lock: `list_actions`, `get_controls`, `scan_i2c`,
  `probe_device`.
  - Add a small branch at the top of `handleRequest` (`App:7201`) and `handleWebCommand` (`App:7231`). The camera
    getters these commands need are already thread-safe; the media gate uses them outside the lock today.
  - Or run the scan on its own thread and publish an `i2c_scan` event.

**C4. Minor: `409` has no reason phrase.**
- **Problem.** `reasonPhrase` (`WS:59-73`) has no case 409, so it falls to `default: return "OK";`. The response reads
  `HTTP/1.1 409 OK`. CONFIRMED.
- **Fix.** Add `case 409: return "Conflict";`. `WebServer.cpp` is missing from the §6 tables.

**C5. Minor: F23 is imprecise.**
- **Problem.** The collection flag is global, and only socket requests set it. `handleRequest` sets it before
  `handleCommand` takes the lock (`App:7207-7221`); `handleWebCommand` never collects (`App:7231-7237`). So an event
  from the worker or the camera thread lands in whichever socket reply is in flight. Whitelisting `controls` is still
  the right fix. CONFIRMED.
- **Also.** The touch UI polls `get_state` only every 30 s when connected (`UI:src/ApertarControlBridge.cpp:18`).
  The T43 card must update from the `controls` event, and it carries `status`; the state poll is too slow for that.

Commands that fit as designed (CONFIRMED):
- Field names like `set.neorotary4.bus`, because `CP:181-204` keeps any key.
- Bare values, because `CP:120-135` stores them as text.
- `okReply` with nested JSON bodies (`list_sensor_modes` already does this, `App:9612-9631`).
- `X-Apertar-Revision`: `WS:96-111` lower-cases header names, so read `x-apertar-revision`.
- The gate placement next to the existing media gate (`App:9495-9500`).

The page must also never send `null`. A bare `null` becomes the text "null" (`CP:192-204`). `parseEdits` should
refuse it.

### D. Sketch and validator: bugs I reproduced (`critic-build/t_events.cpp`, `t_ids.cpp`)

**D1. Blocker: one comment rule for all sections.**
- **Problem.** `parse()` cuts a value at the first `#` or `;` anywhere (`sketch/hardware/HardwareConfigText.hpp:231-235`).
  - `TriggerOutput` cuts only at a `#` or `;` preceded by whitespace (`HW/TriggerOutput.cpp:56-66`). The IMU reader
    does the same.
  - `[run_script]` honours quotes (R2 §1.4).
- **Host run.** `events=recording_start;still` gives the value `recording_start` plus a false warning.
  `path='/home/pi/a;b.sh'` gives a false warning. The Outputs card would show only "Record start", and the next save
  would drop `still`. CONFIRMED (run).
- **Fix.** Add a value rule per section in `kSections`:
  - inputs: the first `#` or `;`;
  - trigger, LED and IMU: only after whitespace;
  - hat and INA219 integers: no stripping;
  - `run_script`: quotes.
  Test each rule.

**D2. Blocker: duplicate sections.**
- **Problem.** `valueOf` returns the first occurrence and `applyEdit` edits the first copy
  (`HardwareConfigText.hpp:271-276`, `:381-389`). Every C++ reader lets the later line win, because it assigns in
  file order (for example `HW/NeoRotary4Input.cpp:399-436`).
- **Host run.** With `[gpio] d10=capture … [gpio_buttons] d10=eject`:
  - the model shows `capture`, while Core uses `eject`;
  - a `set.gpio_buttons.d10=photo` changes the first copy, so it has no effect;
  - the duplicate-section error is "old", so the save passes.
  CONFIRMED (run).
- **Fix.** Refuse key edits into a section that appears twice: "Merge the two [gpio_buttons] copies first (lines 1
  and 5)". Or edit the last copy and show the effective value.

**D3. Major: `issueId` keeps the number in "Line N" messages.**
- **Problem.** The regex `(lines? |line )\d+` is case-sensitive (`HardwareConfigText.hpp:525-529`). Messages that
  start with "Line N" keep N.
- **Host run.** Adding one key above a pre-existing junk line and a 7-action mapping reports **2 new errors**, so the
  save is refused. This breaks the rule that old errors never block the editor. CONFIRMED (run).
- **Fix.** Build ids from (rule, section, key, value), not from the message text, or at least use `std::regex::icase`
  and cover `Line N:`.

**D4. Major: reader defaults are ignored.**
- **Problem.** An enabled `[ina219]` with no `bus=` runs on bus 4 in Core, yet the validator says nothing (0 issues).
  CONFIRMED (run).
- **Fix.** Give each section in `kSections` its default bus, as the readers have it: ina219 4, cfexpress_hat 10;
  pcf8574, neorotary4, grove_analog and the IMU drivers 1.

**D5. Minor: `parseConfigTxt` matches `dtparam=i2c_arm=on` exactly.**
- **Problem.** See `HardwareConfigText.hpp:763`. It misses `dtparam=i2c_arm=on,i2c_arm_baudrate=400000`, `=1`, and a
  trailing comment. The card would then wrongly say "I2C on the header is off".
- **Fix.** Split each `dtparam=` on commas and accept on, true, yes or 1. Base "bus missing" on `/dev/i2c-1`, and use
  `config.txt` only to explain why.
- **Also.** Generate the `sed` from the overlay names, not from line numbers, which shift when Patrik edits the file.
  For example: `sudo sed -i -E 's/^(dtoverlay=(vc4-kms-DPI-4inch|waveshare-4dpi|waveshare-touch-4dpi)([,[:space:]]|$))/#\1/' /boot/firmware/config.txt`.

**D6. Minor: other gaps in the sketch.**
- `set.<section>.<unknown key>` is accepted and written. Easy mode should refuse keys that are not in the schema.
- A new section is inserted directly before the next header. That splits a comment block from the section it
  describes.
- `std::abs(delta)` in the driver (`HW/NeoRotary4Input.cpp:661`) is undefined for `INT32_MIN` (existing code; noted
  only).

### E. Can the action vocabulary really be unified?

**E1. Major: only the names can be unified, not the behaviour.**
- **Names.** The three `normalizeSingleAction` copies are identical. CONFIRMED (355 tokens, and the diff).
- **What T36 leaves out:**
  - **Analog targets:** two copies, `App:8588-8610` and `HW/GroveAnalogInput.cpp:125-145`. `list_actions` would add a
    third with `analog_targets`.
  - **Tally tokens:** after T36 they still live in `HW/ButtonActionList.hpp:57-61` and
    `HW/RecordingIndicatorOutput.cpp:118-129`.
  - **Trigger events:** `HW/TriggerOutput.cpp:121-175`. The Events pills in the Outputs card need that list, so the
    WebUI would keep a copy.
- **Behaviour stays a separate if-chain** (`App:8838-9148`).
  - A catalog entry with no branch there is "known" to the validator, yet still ignored when pressed.
  - So Q10's "one catalog line each" is wrong: a new action is a catalog line plus a dispatcher branch.
  - CONFIRMED.
- **Fix.**
  - T36 moves `canonicalAnalogTarget` and `kTriggerEvents` into the header. Both C++ copies call it, and
    `list_actions` returns both lists.
  - `RecordingIndicatorOutput` calls `hardware::isOutputAction`.
  - Add a host test: every `kSpecs` id has an `action == "<id>"` or family branch in `App:8838-9148`, and every
    `action == "x"` literal there is a catalog id.

**E2. Minor: 36.4's "same results (sketch check 2)" is not what check 2 tests.**
- **Problem.** Check 2 tests `classify`. It does not compare App's parser with the header's. And they differ:
  - App's `parseDoubleValue` uses `std::stod`, which accepts `inf` and `nan` (`App:914-929`);
  - the sketch's `number()` rejects non-finite values. CONFIRMED.
- **Fix.** Extract `App:1374-1456` with `make_old.sh` and compare on the token list, as T36 already does for the
  normalizers.

**E3. Minor: `list_actions.values.fps` and `resolution` depend on the current mode.**
- **Problem.** Both depend on the sensor, the resolution and Clear HDR (`App:1098-1200`, `:1214-1286`). A page that
  caches them shows stale values after a mode change.
- **Fix.** Label them "for the current mode", and re-fetch on a `settings` event.

### F. The file and the other processes that read it

What keeps working (CONFIRMED):
- The path stays the same, and so does the INI.
- `settingsFile::atomicWrite` keeps the mode and renames, so the path is never missing (`SF:36-56`).
- Every reader accepts the canonical keys, `true`/`false` and `0x..` addresses:
  - the automounter (`UI:src/CfeAutomounter.cpp:66-77`, `:150-180`);
  - Ina219Bridge's integer parser (`UI:src/Ina219Bridge.cpp:410-438`);
  - the Python helper's `int(value, 0)` (`App:3445-3453`).
- The template writers fire only when the file is missing (`UI:src/DisplayConfigBridge.cpp:41-47`).

Problems:

**F1. Blocker (rare, costly): an in-place editor and the store.**
- **What happens.** `nano` truncates and rewrites the same inode. A store edit that reads in that window
  (milliseconds) does this:
  - it merges into a truncated text;
  - `newErrors` treats the truncation's errors as old, so the save passes;
  - the rename then orphans the inode `nano` is still writing to.
  The hand edit and the rest of the file are lost. `.bak` holds the truncated copy. PROBABLE.
- **Fix.** Require a stable file before an edit: stat twice 100 ms apart with equal size, mtime and inode, or an
  mtime at least 1 s old. Otherwise refuse with "The file is being written; try again."

**F2. Major: a missing file and the `/boot` copies.**
- **Problem.**
  - The design never defines the revision of an absent file.
  - `GET /api/config` returns the template text when the file is missing (`App:5437`).
  - A first save then creates `~/apertar-hardware.conf` and shadows any `/boot` copy for the seven readers that take
    the first existing file. Patrik loses his `/boot` sections without a word (R2 §1.1). CONFIRMED (code); relevance:
    M1.
- **Fix.**
  - Use a fixed revision for "absent", for example `h0000000000000000`.
  - When `~` is missing and a `/boot` copy exists, the first save starts from the `/boot` text and shows the diff.

**F3. Minor (§3.4 step 1): the lock can time out.**
- **Problem.** `QtIniLock` gives up after 2 s, and then `operator bool` is false (`SF:65-88`).
- **Fix.** The store must refuse in that case: "Another writer holds the lock".

Restarts still needed by the other processes: correct in §3.6 (automounter `UI:src/CfeAutomounter.cpp:792`, UI
bridges at construction, network helper at `UI:src/WifiBridge.cpp:129`). CONFIRMED.

### G. WebUI size and approach

**G1. Major: the tip has no pointer-drag code.**
- **Problem.** `setPointerCapture` and `pointercancel` occur 0 times in `Web@0296ed1`, and once in the unmerged T34
  worktree. CONFIRMED.
- **Fix.** T40 either depends on T34 being on the tip or brings its own ~60-line drag helper. Say which.

**G2. Size.**
- **The numbers.** The page script grows from 7,616 to about 10,300 lines (+35%), inside one raw string
  `R"APERTAR(…)APERTAR"` (`Web:7`, `:11657`).
  - GCC has no limit on that, and `node --check` on the extracted script works today. CONFIRMED.
  - Mocked-browser tooling exists only in `scratchpad/t34/webtest/`, not in the KB.
- **Fix.**
  - Keep all Controls code in one contiguous block with its own `controls` state object. That keeps merges with
    T33-T35 in the same file tractable.
  - Ship the extract-and-check script with T39 as a KB tool.

**G3. Minor: a textarea turns CRLF into LF.**
- **Problem.** A text-mode save of a CRLF file rewrites every line.
- **Fix.** The validator warns about CRLF, and Check says so.

**G4. Minor: the poll and redraw rules are consistent with the code.**
- The rule "rows are rebuilt only after get_controls; the 1 s poll updates only the pills" matches the existing 1 s
  poll (`Web:11652`) and the config fetch (`Web:10345-10370`). CONFIRMED.

### H. Measurements and tutorial checks

**H1. Blocker: M4's seesaw loop is not read-only for the camera.**
- **Why the read can be cut in two.**
  - Core reads the seesaw in two transactions: write the select, `usleep(8000)`, then read
    (`HW/NeoRotary4Input.cpp:559-570`; the default delay is 8000 µs at `.hpp:56`).
  - Each poll spends about 40 ms of a ~70 ms cycle inside those windows.
- **What a collision does.**
  - An interleaved `i2ctransfer -y 1 w2@0x49 0x00 0x01` makes Core's 4-byte delta read return the HW-ID register.
  - `readBigEndianI32` turns `0x87…` into a large negative delta.
  - The driver then fires up to `max_events_per_poll` (8) turn actions in one direction, for example `iso_down` ×8
    (`:572-584`, `:650-665`).
  - With 20 tries, several such collisions are likely. PROBABLE.
- **The scan has the same problem.** `scan_i2c`/`i2cdetect` quick-writes to `0x49` may disturb the seesaw in the
  same way. PROBABLE.
- **Fix.**
  - Drop the loop: the "driver first" rule does not need it. Or run it only with Core stopped (Patrik:
    `sudo systemctl stop apertar-core`).
  - `scan_i2c` must skip, and list in `busy`, every address one of Core's drivers holds, not only `probe_device`.
  - Use combined `I2C_RDWR` transfers for every non-seesaw probe.

**H2. Major: `tutorial.py` refuses T36 check 5.1 and T37 check 5.1.**
- **Problem.** `SAFE_CORE_CMDS` lists only `ping`, `help`, `get_state`, `get_media_test_state`, `audio_capabilities`
  and `list_sensor_modes` (`tutorial.py:48-49`). For a curl check, `unsafe_reason` refuses any other `"cmd"`
  (`:188-191`). CONFIRMED.
- **Fix.** T36 adds `list_actions`, T37 adds `get_controls`, and T41 adds `controls_history` to `SAFE_CORE_CMDS`.
  Never add `set_controls`, `apply_controls`, `scan_i2c` or `probe_device`.

**H3. Major: T37 test 5's "→ empty diff" is wrong.**
- **Problem.** `text="$(cat ~/apertar-hardware.conf)"` strips the final newline. The sketch keeps a missing final
  newline byte for byte (check 3), so the dry run shows one change and a different revision. CONFIRMED (shell + sketch
  check 3).
- **Fix.** Predict one change, or add `text@=<path>` to `core.py`, a KB tool, to send the file's bytes.

**H4. Major: M5's fallback never runs.**
- **Problem.** In `gpioinfo gpiochip0 2>/dev/null | head -30 || gpioinfo -c gpiochip0 | head -30`, the `||` tests
  `head`, so the libgpiod v2 form never runs. And v2 reads `gpiochip0` as a line name. CONFIRMED (shell semantics).
- **Fix.** `{ gpioinfo -c gpiochip0 2>/dev/null || gpioinfo gpiochip0; } | head -40`, after `gpiodetect`: the RP1
  chip's number has changed between kernels. UNCONFIRMED which one Patrik's kernel uses.

**H5. Minor: M8 can pass several revisions.**
- **Problem.** `grep -o '"revision":"h…"'` can match several revisions (history, pending).
- **Fix.** Add `| head -1`.

**H6. Minor: the bus labels in §4.4.**
- **Problem.** `/sys/class/i2c-adapter/i2c-N/name` says "Synopsys DesignWare I2C adapter" for both bus 1 and bus 10,
  and "107d508200.i2c" for HDMI DDC (KB `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md:57-61`). It never says cam0
  or header.
- **Fix.** Label from a Pi 5 table keyed by bus number, with the device-tree node path as a check. Mark it
  UNCONFIRMED until M3.

### I. T42 (hold and double press)

**I1. Major: the NeoRotary knob press may miss quick double presses.**
- **Problem.** The NeoRotary push is sampled about every 70 ms (5 reads × 8 ms + `poll_ms` 30), with a 60 ms debounce.
  Each edge therefore needs at least two samples, about 140 ms. A 350 ms double window can miss quick doubles.
  PROBABLE (arithmetic from `HW/NeoRotary4Input.cpp:650-711`).
- **Fix.** Measure in T42, and allow `double_ms` per source.

**I2. Minor: a slow command delays the gesture.**
- **Problem.** Callbacks run on the poll thread and block on `handleCommand`. A slow command (`set_resolution`)
  delays the next sample, so hold fires late.
- **Fix.** Note it in the T42 "Learn" box.

---

## 3. Verified correct (no need to re-check)

| Design claim | Evidence | Label |
| --- | --- | --- |
| Candidate list; editable path | `App:4293-4311`, `:4313-4318` | CONFIRMED |
| Hat reader: first existing file, no comment strip for integers | `App:4552-4598` (`return config;` inside the loop at `:4596`; `parseConfigInteger` at `:4580`) | CONFIRMED |
| Boot order trigger → PCF → NeoRotary → GPIO → power → Grove → LED, then re-sync | `App:7026-7044` | CONFIRMED |
| INA219 `static const`; hat read once at watcher start | `App:4695`, `App:9310-9313` | CONFIRMED |
| Python helper: `configparser`, catches only `OSError` | `App:3466-3478` | CONFIRMED |
| `/api/config` save: `.bak`, `<file>.tmp`, rename, no fsync; 256 KiB | `App:5463-5526`, `App:66`, `App:7321-7341` | CONFIRMED |
| IMU writer: shared `.tmp`, remove-then-rename | `HW/Mpu6050RecordingSession.cpp:687`, `:700-705`, `:816`, `:831` | CONFIRMED |
| Lock order on a driver thread: sequence → action → command | `App:8819`, `:8638`, `:9485` | CONFIRMED |
| New gesture keys are ignored by today's parsers (a mixed-version file is safe) | `HW/GpioInput.cpp:209-236` (`d10_hold` → digits `10_hold` → rejected), `HW/Pcf8574Input.cpp:108-138`, NeoRotary field match `:424-436` | CONFIRMED |
| `atomicWrite` (mkstemp, fchmod, fsync, rename, directory fsync) and `QtIniLock` | `SF:36-56`, `:59-118` | CONFIRMED |
| Protocol keeps any key; bare values as text | `CP:164-233` | CONFIRMED |
| XDG rule for `~/.config/apertar-core/` | `src/camera/CameraController.cpp:355-366` | CONFIRMED |
| Every §6 search string present (`Web:2773`, `:3840`, `:4165`, `:4240`, `:6186`, `:1887`, `:1562`, `:10307`, `:10372`; `App.hpp:139`, `:187`; T42's three) | grep -nF | CONFIRMED |
| UI template writers and calls; gyro writer; `--check-config` | `UI:src/DisplayConfigBridge.cpp:41`, `:587`; `UI:src/Ina219Bridge.cpp:69`, `:497`; `UI:src/GyroConfigBridge.cpp:1577`; `UI:src/CfeAutomounter.cpp:786-802` | CONFIRMED |
| Cinemate drag only on value chips | `src/module/app/templates/settings_editor.html:4893-4901` (HTML5 `draggable`) | CONFIRMED |

---

## 4. Checklist for the reviser (design section → change)

| § | Change |
| --- | --- |
| 0.7, 3.6 | Asynchronous apply only (A3). Restart only the drivers whose sections changed; IMU, display, network and run_script restart none (A4). Gate the take at reload time (A5). Two-phase stop (A6) |
| 3.4 | Single store for the whole process (B4). Stable-file check (F1). Absent revision and adopting `/boot` (F2). Refuse on lock timeout (F3). Outside edits need `adopt_outside` (A4c) |
| 3.5 | Socket 64 KiB cap (C1). `errorReplyBody` (C2). Read-only hardware commands before `commandMutex_` (C3). Refuse `null` |
| 3.7 | "Saved. Core is applying it." Add the outside-edit refusal and the "file is being written" refusal |
| 3.3, T36 | Analog targets, trigger events and tally tokens into the header. Dispatcher coverage test. Q10 wording. Parser comparison test (E1-E3) |
| 4.4, 39.1 | Skip driver-held addresses in scans. Combined transfers. Bus labels by number (H1, H6). Pattern-based `sed` (D5) |
| 6 (38.1, 38.4-38.6, 38.9, 37.5) | `mutable` mutex. Status snapshot. `running()` for the outputs. Clear `lastError_`. INA219 generation at file scope. `std::optional<CfeHatReader>`. Unique anchor. IMU batching. Add `WebServer.cpp` (409) and `ControlServer.cpp` |
| Sketch / 37.1 | Comment rule per section; duplicate sections; `issueId`; reader default buses; `dtparam` parsing; unknown keys (D1-D6) |
| 7 (tutor blocks) | `SAFE_CORE_CMDS` additions (H2). T37 test 5 prediction (H3) |
| 8 | Remove or restrict M4's seesaw loop (H1). Fix M5 (H4) and M8 (H5). Change M8's prediction to up to ~4 s before the A6 fix |
| 9.1 | Add risks: an in-place editor truncating the file (F1); phantom knob events from bus traffic (H1); Grove `emit_on_start` on every reload (A4) |
