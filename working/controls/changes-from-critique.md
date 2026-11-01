# Changes from the critiques: design-controls v1 → v2

2026-10-28, designer pass v2. One row per critic point. Each row says whether the point was **accepted**, **changed** (accepted,
but with a different fix or corrected evidence) or **rejected**, why, and where it landed in `design-controls.md` (v2).

I checked every point against the code before accepting it, at Core `0296ed1` (`core-tip`), touch UI `5aab7e2` (`ui-tip`) and
KB `9ddac81`. "Checked" below means I opened the line or ran the command here. Where I ran something, the command or the
sketch check is named.

Sources: `critique-code.md` (`CC`), `critique-operator.md` (`CO`), `design-controls-v1.md` (v1), `design-controls.md` (v2).

## 0. Summary

| | Code critique | Operator critique |
| --- | --- | --- |
| Rows below (points and sub-points, questions, risks, measurements) | 45 | 75 |
| Accepted (3 code rows are "consistent, no change needed") | 41 | 67 |
| Changed (accepted with a different fix, or with corrected evidence) | 4 (A4d, A5, C3, D1) | 7 (P4, P5, P6, P8.3, P9f, Q18, Q19) |
| Rejected | 0 | 1 (P7.1: DRM detection as the gate for the DPI commands) |

What I ran to check them:

- The sketch, fixed for D1-D6 and extended: 78 of 78 checks (v1: 51).
- The critic's own probes `critic-build/t_events.cpp` and `t_ids.cpp`, rebuilt against the v2 sketch: all four reproduced
  bugs are gone.
- `make_old2.sh`, which extracts App's number parser, both analog-target normalizers and the trigger-event parser read-only,
  so they can be compared token by token.
- 56 tutor anchors and 39 plan search strings, each checked to occur once at its line.

**Two critic claims were wrong in their evidence, though their conclusion stands:**

- **D1:** the IMU reader cuts a comment at the first `#` or `;`, not "only after whitespace" (`HW/Mpu6050RecordingSession.cpp:209-221`).
- **C3:** the media gate runs inside the lock, not outside it (`App:9485-9500`). Its conclusion still holds, because
  `buildWebStateJson` calls the same camera getters without the lock (`App:7857-7866`).

**One operator fix was rejected** (P7.1): the claim that DRM `modes` proves a DPI panel is attached. KB `SRC §4.5` records that
the DPI connector reports `connected` with no panel. The box now asks the operator instead.

**v1 → v2 tutorial numbers.** v1's T37 is split in two: the store, and "no silent overwrites". v1's T40 is split too: inputs,
then Listen, outputs and review. The touch UI's mandatory part moves into the I2C tutorial.

| v1 | v2 | What |
| --- | --- | --- |
| T36 | T36 | vocabulary (+ analog targets, trigger events, tally tokens, coverage test) |
| T37 | T37 + T38 | the store and validator / no silent overwrites (`/api/config`, 409, UI template removal, socket limit) |
| T38 | T39 | reload worker, status, merge, apply |
| T39 | T40 | I2C devices, panel part 1, **touch warning chip** |
| T40 | T41 + T42 | inputs editor / Listen, outputs, review, undo |
| T41 | T43 | text editor |
| T42 | T44 | hold and double press |
| T43 | T45 (optional) + T38 + T40 | read-only card and gyro page (optional); template removal moved to T38; status chip moved to T40 |

---

## 1. Code critique (`critique-code.md`)

### A. Live reload: threads and locks

| Point | Verdict | Why (evidence checked here) | v2 |
| --- | --- | --- | --- |
| A1 status accessors race with the reload | **accepted** | `enabled()`/`configPath()` read `config_` unlocked (`HW/NeoRotary4Input.cpp:339-347`, `HW/GpioInput.cpp:357-365`, same in PCF8574 and Grove). `start()` assigns it (`:313`, `:332`, `Pcf8574Input.cpp:276`, `GroveAnalogInput.cpp:204`) | §3.6 "status snapshot": only the worker, the sole caller of `start()`, reads driver config; the state builders read the snapshot under `mutable controlsMutex_` |
| A2 `running()` races for the outputs; running ≠ connected; stale errors | **accepted** | Outputs: `bool running_` under `stateMutex_` (`HW/TriggerOutput.hpp:85-89`, `HW/RecordingIndicatorOutput.hpp:77-80`). The retry loop keeps running (`HW/NeoRotary4Input.cpp:631-638`). `start()` never clears `lastError_` (`:310-329`); it is cleared only after an open (`:640`) | §3.6 driver-change table: locked `running()` for outputs; a `connected_` atomic; `setLastError({})` at the top of `start()` |
| A3 "Saved; Core applied it" vs async apply; a synchronous apply deadlocks | **accepted** | `set_controls` runs under `commandMutex_` (`App:9485`); a driver thread can be blocked on that lock (`App:8636-8644`) while the worker joins it | §0.5, §3.6: the rule "no command handler ever waits on the worker"; `apply:{core:"queued"}`; "Saved. Core is applying it." |
| A4 every store write restarts all drivers (IMU too), and applies outside edits without `force` | **accepted, (d) changed** | Level set = 5 writes, clear = 4 (`HW/Mpu6050RecordingSession.cpp:1363-1367`, `:1376-1379`). Grove re-emits (`HW/GroveAnalogInput.cpp:465-469`). NeoRotary drops movement (`:643-647`). Outside-edit adoption follows from the sketch's semantics | (a) one store call per IMU command (§3.4); (b) restart groups G/N/A only when their sections changed (§3.6); (c) `adopt_outside` (§3.4 step 4); (d) **changed**: instead of "IMU versions don't count", IMU writes from one source within 10 minutes coalesce into one history entry, and `.bak` rotates only on WebUI/`core.py` saves (the operator's P3 fix, which covers the same harm and keeps one undo point for a calibration) |
| A5 gate checked at save, not reload; LED re-sync race | **accepted, changed** | `TriggerOutput::stop()` drives inactive (`HW/TriggerOutput.cpp:429-447`). The LED ignores setters while stopped (`HW/RecordingIndicatorOutput.cpp:491-499`). The tally learns of a take only through `handleTriggerEvent` (`App:11322-11340`) | The worker checks the gate before the stops and defers; the re-sync runs under `commandMutex_` after every join. **Changed:** the critic said the commands publish recording events under that lock. That is true for commands, but `CameraController` can also build a `recording` event (`src/camera/CameraController.cpp:10124`) outside a command. A microsecond race remains, listed as R21 |
| A6 a reload can take ~4 s | **accepted** | Each input's retry sleeps 1 s (`HW/NeoRotary4Input.cpp:637`, `HW/Pcf8574Input.cpp:483`, `HW/GroveAnalogInput.cpp:449`, `HW/GpioInput.cpp:647`). `stop()` is `if (!running_.exchange(false)) return; join()` (`:331-337`), so a plain `requestStop()` would make `stop()` skip the join; the critic's join-always `stop()` is needed | §3.6 two-phase stop; M8 prediction "about 1 s, not 4" |
| A7 false "outside" right after Core's own write; touch-UI gyro noise; inode in the stat key | **accepted** | Pure ordering argument: the worker can stat between the rename and the record. The gyro writer is real (`UI:src/GyroConfigBridge.cpp:1577`, one write per tap at `UI:qml/SettingsPage.qml:3713-3720`) | §3.4 step 9 (`expected_revision` before the rename, under the store mutex); `controls_outside` only for reload sections; banner per section; stat key = size, mtime, inode, ctime |
| PCF8574: no interrupts; every open writes `0xff`; shared chip glitches on every save; add a warning | **accepted** | `HW/Pcf8574Input.cpp:416`, `:426-430`; trigger copies the byte (`HW/TriggerOutput.cpp:640-644`); grep `interrupt|irq|int_gpio` in `src/hardware`: no hits | validator rule `pcf_shared` (sketch check 10); R20 |

### B. Plan rows that do not compile as written

| Point | Verdict | Why | v2 |
| --- | --- | --- | --- |
| B1 `readIna219Snapshot` cannot see a member | **accepted** | free function at `App:4693`, inside the anonymous namespace opened at `App:59` and closed at `App:6919`; its caller `readPowerSupplySnapshot` (`App:4757`) is free too | row 39.6: file-scope `std::atomic<uint64_t> gHardwareConfigGeneration` |
| B2 `CfeHatReader` is not copyable or assignable | **accepted** | `src/util/CfeHat.hpp:32-33` (`= delete`) | row 39.7: `std::optional<CfeHatReader>` + `emplace` |
| B3 `controlsMutex_` locked from `const` methods | **accepted** | `buildWebStateJson() const` (`App:7857`); the header pattern is `mutable std::mutex` (`App.hpp:168`, `:175`, `:189`) | row 39.1 `mutable std::mutex controlsMutex_`; row 37.2 `currentRevision() const` with `mutable` cache and mutex |
| B4 IMU writers cannot reach an App-owned store; they write the loader's path | **accepted** | free functions at `HW/Mpu6050RecordingSession.cpp:604`, `:715`; they write `config.configPath`, which comes from the candidate loop (`:855`) and can be a `/boot` copy (`:1296-1300`) | §3.4: `hardware::configStore()`, a function-local static; always `editableHardwareConfigPath()`; row 37.3 |
| B5 the 38.9 search string occurs twice | **accepted** | `eventJson.find("\"event\":\"still_exposure\"")` at `App:11300` and `App:11324` | row 39.10 uses the `media_write_state` line (`App:11301`, once) |

### C. Commands, protocol, reply style

| Point | Verdict | Why | v2 |
| --- | --- | --- | --- |
| C1 socket lines capped at 64 KiB, silent drop | **accepted** | `CS:261`: `if (line.size() >= 64 * 1024) return;` (no reply; `removeClient` is skipped too) | row 38.4: `kMaxRequestLineBytes = 1024 * 1024`; §3.5. I chose 1 MiB (= HTTP's `WS:23`) over "document the limit" because Patrik's tutorials use `core.py` for text saves |
| C2 a refusal cannot carry `issues[]`; the WebUI helper drops them | **accepted** | `errorReply` writes only `"error"` (`App:122-130`); `sendCommand` throws with `result.error` and re-renders the snapshot (`Web:9148-9180`) | `errorReplyBody` (row 37.4); the panels' own `controlsCommand()` (row 40.5) |
| C3 every command runs under `commandMutex_`, scans included | **changed (evidence)** | The lock is the first line of `handleCommand` (`App:9485`) — CONFIRMED. The critic's "the media gate uses them outside the lock today" is not right: the gate is inside `handleCommand` (`App:9487-9500`). But the web state builder calls the same camera getters without the lock (`App:7857-7866`), so the getters are used lock-free already | §3.5 "Before the lock": read-only hardware commands are handled before `handleCommand`, with their own `i2cMutex_` and a gate check per address. I took the "before the lock" option, not the "own thread + event" one: smaller, and the WebUI has no socket events |
| C4 409 has no reason phrase | **accepted** | `WS:59-73`, `default: return "OK";` | row 38.3 |
| C5 F23 imprecise; the touch UI polls every 30 s | **accepted** | the collecting flag is set only by `handleRequest` and is global (`App:7207-7221`, `:11310-11316`); `kSteadyStatePollIntervalMs = 30000` (`UI:src/ApertarControlBridge.cpp:18`) | F23 rewritten; the touch chip lives on the `controls` event, broadcast via the whitelist (§3.5) |
| Never send `null` | **accepted** | `CP:192-204`: a bare value is kept as text, so `null` → "null" | `parseEdits` refuses it (sketch check 10) |
| "Commands that fit as designed" (field names, bare values, nested reply bodies, lower-cased headers, gate placement) | **accepted** (no change needed) | `CP:181-204`, `CP:120-135`, `App:9612-9631`, `WS:96-111` | §3.4 reads `x-apertar-revision` |

### D. Sketch and validator bugs

| Point | Verdict | Why | v2 |
| --- | --- | --- | --- |
| D1 one comment rule for all sections | **changed (evidence)** | The bug is real: the sketch cut at the first `#`/`;` (`sketch-v1/hardware/HardwareConfigText.hpp:231-235`), and I reproduced it. But the critic's rule table is partly wrong. Trigger and tally cut only after whitespace (`HW/TriggerOutput.cpp:56-66`, `HW/RecordingIndicatorOutput.cpp:53-63`). The **IMU cuts at the first mark anywhere** (`HW/Mpu6050RecordingSession.cpp:209-221`), not "the same as the trigger". `[run_script]` honours quotes (`HW/HardwareScriptRunner.cpp:70-79`). Also, the hat's and INA219's `enabled=` **does** strip comments (`parseConfigBool`, `App:4469-4482`); only their integers do not (`App:4448-4467`) | `ValueRule` per section in `kSections` (FirstMark, SpacedMark, IntegerStrict, Raw, Quoted, Other); `commentMark()`; `effectiveValue()`. Sketch check 10: five cases (trigger `;`, quoted path, IMU `;`, hat `enabled=` comment = warning, hat `bus=` comment = Core uses 10) |
| D2 duplicate sections: model shows the first, edit changes the first, Core uses the later | **accepted** | readers assign in file order (`HW/NeoRotary4Input.cpp:399-436`); `GpioInput` treats `[gpio]` and `[gpio_buttons]` as one section (`HW/GpioInput.cpp:405-413`) | `valueOf` → last occurrence; `checkEdits` refuses key edits into a duplicated section ("Merge the copies"); the easy view locks those rows (§3.2). Sketch check 10 |
| D3 `issueId` keeps "Line N" | **accepted** | the case-sensitive regex (`sketch-v1/…:525-529`); the critic's case reproduced | issue ids are `rule|section|key|detail`; `Issue` gets `rule`, `section`, `key`. Sketch check 10: a key added above an old junk line and an old 7-action line adds 0 new errors |
| D4 reader defaults ignored | **accepted, extended** | INA219 default bus 4 (`App:4284`). And more than the critic said: the INA219 is **enabled by default even with no section** (`App:4283`, loader `App:4492-4545` needs no header). Header-enables: PCF8574, NeoRotary4, Grove (`HW/Pcf8574Input.cpp:348-349`, `HW/NeoRotary4Input.cpp:386-390`, `HW/GroveAnalogInput.cpp:279-280`); hat on with its header (`App:4568-4571`) | `defaultBus`, `onByDefault`, `onWithoutSection` in `kSections`; `deviceOn()`; a warning for a missing `[ina219]` too. Sketch check 10 (two cases) |
| D5 exact `dtparam` match; generate `sed` from names | **accepted** | `sketch-v1/…:763` | `parseConfigTxt` parses comma lists, a bare name, `=1`, comments, and a later `=off`; `dpiCommands()` builds the pattern `sed`. Sketch check 10 runs it with GNU sed on a copy twice: the overlays are commented, `imx585` kept, the second run is a no-op. Side effect noted in §4.4: a same-name line under `[pi4]` is commented too |
| D6 unknown keys accepted; a new section splits a comment block; `std::abs(INT32_MIN)` | **accepted** (abs: noted only, as the critic says) | reproduced | `knownKey()` + `checkEdits()` (text-only sections refused in key edits); insertion above the next header's comment block. Sketch check 10 |

### E. Can the vocabulary really be unified?

| Point | Verdict | Why | v2 |
| --- | --- | --- | --- |
| E1 names yes, behaviour no; analog targets, tally tokens and trigger events left out; Q10 wrong | **accepted** | `App:8588-8610` and `HW/GroveAnalogInput.cpp:125-145`; `HW/ButtonActionList.hpp:57-61` and `HW/RecordingIndicatorOutput.cpp:118-129`; `HW/TriggerOutput.cpp:130-150`; the dispatcher if-chain `App:8838-9148` | all three lists move into the header (rows 36.4-36.6). Sketch check 11: Grove-identical on 44 tokens, App-identical except `none`/`off`/`disabled` (App never receives them; Grove clears them first), trigger events identical on 51 tokens. **The dispatcher coverage test is implemented** (it reads App's source): it passes today. Q10 reworded |
| E2 36.4's "same results" is not what check 2 tests; `std::stod` accepts `inf`/`nan` | **accepted** | `App:914-929`. The comparison also found a difference the critic did not name: `iso1e-999`. `std::stod` throws `out_of_range` on underflow, while the sketch's `strtod` returned 0 | `number()` now refuses `ERANGE` like `stod`, and still refuses non-finite values. Sketch check 11: identical on 20 tokens × 4 prefix sets except `inf`/`nan` |
| E3 `fps`/`resolution` lists depend on the mode | **accepted** | `App:1098-1286` | `values_for` in the reply; the page re-fetches when the state's sensor, resolution or Clear HDR changes (the WebUI has no socket events, so "on a settings event" becomes "when the polled state changes") |

### F. The file and the other processes

| Point | Verdict | Why | v2 |
| --- | --- | --- | --- |
| F1 an in-place editor and the store | **accepted** | nano rewriting in place is PROBABLE, as the critic labels it; the rename-orphans-the-inode reasoning holds | §3.4 step 2: the stable-file check (two stats 100 ms apart, or mtime < 1 s, only when the revision is not Core's own); refusal "The file is being written"; the WebUI retries once. R3 updated |
| F2 absent revision; first save shadows `/boot` | **accepted** | `App:5437` returns the template text when the file is missing | `kAbsentRevision = h0000000000000000` (sketch); the first save starts from the `/boot` text when `~` is missing (§3.4, row 38.1) |
| F3 lock timeout | **accepted** | `SF:65-88`: 2 s deadline, then `operator bool` false | §3.4 step 1 refusal |
| "Restarts still needed by the other processes: correct" | no change | — | — |

### G. WebUI size and approach

| Point | Verdict | Why | v2 |
| --- | --- | --- | --- |
| G1 no pointer-drag code on the tip | **accepted** | `grep -c 'setPointerCapture\|pointercancel' src/web/WebControlPage.cpp` → 0 | T41 brings its own ~60-line helper, or uses T34's if it has landed (§4.1) |
| G2 size; one raw string; mocked-browser tooling only in a scratch folder | **accepted** | `Web:7`, `:11657`; 11,661 lines | one contiguous Controls block with its own state object; row 40.7 ships the extract-and-check script as a KB tool |
| G3 textarea CRLF → LF | **accepted** | browser textarea value normalisation (HTML spec; not re-run here) | validator warning `crlf` (sketch check 10) |
| G4 poll/redraw rules consistent | no change | `Web:11652` (1 s poll) | — |

### H. Measurements and tutorial checks

| Point | Verdict | Why | v2 |
| --- | --- | --- | --- |
| H1 the M4 seesaw loop is not read-only for the camera; scans have the same problem | **accepted** | two-transaction read with `usleep(8000)` (`HW/NeoRotary4Input.cpp:557-570`, `.hpp:56`); a bogus delta fires up to `max_events_per_poll` turns (`:658-662`) | M4 has no seesaw loop. An optional block runs with Core stopped (Patrik). `scan_i2c`/`find_device` skip every driver-held address; combined `I2C_RDWR` for non-seesaw probes. "Driver first" now rests on Core's own ID check at open (`:494-514`) |
| H2 `tutorial.py` refuses the curl checks | **accepted** | `SAFE_CORE_CMDS` at `tutorial.py:48-49`; the refusal at `:188-191` | rows 36.10, 37.10, 43.3 add `list_actions`, `get_controls`, `controls_history` (never the write or scan commands) |
| H3 `text="$(cat …)"` drops the final newline | **accepted** | shell command substitution; sketch check 3 keeps a missing final newline | `core.py` gains `k@=path` (row 37.9); the T37 test uses it and explains the trap |
| H4 M5's `\|\|` tests `head` | **accepted** | pipeline exit status is the last command's | `gpiodetect` first, then `{ gpioinfo -c … \|\| gpioinfo …; } \| head -40` |
| H5 M8 can match several revisions | **accepted** | — | `\| head -1` |
| H6 adapter names do not say cam0 or header | **accepted** | KB `SRC:57-61`: `i2c-10 Synopsys DesignWare I2C adapter`, `i2c-13 107d508200.i2c` | labels from a Pi 5 table by number, checked against the adapter's `device` link (M3 adds `readlink -f`); UNCONFIRMED until M3; HDMI DDC disabled for devices |

### I. T44 (v1 T42)

| Point | Verdict | Why | v2 |
| --- | --- | --- | --- |
| I1 the NeoRotary push may miss quick doubles | **accepted** | 4 delta reads + 1 mask read × 8 ms + `poll_ms` 30 ≈ 70 ms per sample, 60 ms debounce (`HW/NeoRotary4Input.cpp:650-711`) | `double_ms` per source; measured in T44 |
| I2 a slow command delays the gesture | **accepted** | callbacks run on the poll thread and block in `handleCommand` | T44 "Learn" note |

### Checklist (`CC §4`)

Every row of the critic's checklist maps to a v2 change above. None is left open.

---

## 2. Operator critique (`critique-operator.md`)

### Problems

| Point | Verdict | Why (evidence checked here) | v2 |
| --- | --- | --- | --- |
| P1 one save can switch off every GPIO button | **accepted** | one request for all lines (`HW/GpioInput.cpp:554-576`); retry with stored error (`:642-649`) | §1.2 D; the after-save module compare + **Undo last save** (§3.6, §4.1); GPIO 14/15 UART advisory (§3.2, M5b); Q15 per-line requests |
| P1.2 `changed:[…]` in the `controls` event | **accepted** | — | §3.5 event |
| P2 any WebUI save applies an unapplied hand edit, unseen | **accepted** | each `start()` re-reads the file (`HW/NeoRotary4Input.cpp:310-313`) | `adopt_outside` + `outside_diff` + "Save and apply both" (§3.4 step 4). With per-group restarts (CC A4b) it is needed only when the save restarts the group with the hand edit; §3.8 row added |
| P3 gyro taps flood history and `.bak`, and look "not applied" or "outside" | **accepted** | one `adjust_imu_sync_offset` per tap (`Web:11010-11016`); the touch UI's ±1 (`UI:qml/SettingsPage.qml:3713-3720`) | IMU coalescing per 10 minutes; `.bak` only for WebUI/`core.py`; the pinned "Before Controls" version, never pruned; "applied" per group; the outside banner per section, with no Apply for read-on-use sections (§3.1, §3.4) |
| P4 the silent template revert stays until the optional, last T43 | **accepted, changed (detection)** | `UI:src/DisplayConfigBridge.cpp:41-58`, `:297-300`, `:131-135`; the return value is unused at `:587` and `UI:src/Ina219Bridge.cpp:497` | the template removal moved to T38 (row 38.7). The "replaced by a default" detection with Restore (§3.4) is **changed** in how it detects: hashing the UI template in a host test would need its text out of two C++ stream blocks that differ (`diff` of the two writers). Instead: missing/empty, or the file lacks Core's header line while Core's last version had it; the UI's first two lines name the culprit |
| P5 the camera's own screen says nothing | **accepted, changed** | the INA219 hint (`UI:qml/SettingsPage.qml:4526`). The critic says "use the real address the network bridge already knows": `WifiBridge` exposes no address (`UI:src/WifiBridge.hpp:22-25`); `DeviceInfoBridge.ipAddress` does (`UI:src/DeviceInfoBridge.hpp:16`) | the warning chip in T40 (§4.5), in the `DroppedFrameWarning` pattern (`UI:qml/CameraPage.qml:2612-2620`), with the address from `DeviceInfoBridge`; the INA219 hint text changed |
| P6 pending restarts never clear, speak only sudo, appear only after Save | **accepted, changed** | the design text had no clearing rule (v1 §3.5-3.6) | pending is derived from facts and clears by itself; the consequence in operator words; Restart Camera (`Web:3664`, `App:11267-11272`; Q16); `apply` in the dry run. **Changed:** comparing wall-clock `ActiveEnterTimestamp` with history times breaks when the clock jumps, which happens on a Pi without network time. v2 uses `ActiveEnterTimestampMonotonic` + `boot_id`, read with `runShellCommandCapture` (`App:1533`); M2b checks `pi` can read it |
| P7.1 Core reads `/sys/class/drm/card*-DPI-*/modes`; a DPI connector with modes = a real panel | **rejected** | KB `SRC §4.5` (Patrik's rig): "A DPI overlay creates a DPI connector that reports `connected` even with no panel". The panel timings of a DT DPI panel come from the overlay, so a mode list without a panel is PROBABLE. A false "no panel" would black out a camera whose only screen is DPI, which is exactly the harm P7 is about | the box **asks** ("Does this camera use a DPI screen?") and shows the DRM state as information only (§4.4); M3b kept to learn what the Pi reports; Q18 |
| P7.2 pattern `sed` from names, idempotent | **accepted** | — | `dpiCommands()` (same as CC D5) |
| P7.3 timestamped backup and an undo line | **accepted** | — | §4.4 |
| P7.4 the "after the reboot" `[display]` line | **accepted** | `SRC §4.5` (HDMI 720x720; `hdmi_external_only` or `ui_width/ui_height/ui_layout`) | §4.4, §1.2 A |
| P7.5 parse `dtparam` as a list; show only the DPI reason | **accepted** | — | `parseConfigTxt`; the `i2c_arm` text shows only when no DPI reason applies |
| P8.1-8.2 Find on any bus; Use from a scan | **accepted** | `SRC:155` asks for auto-detect | `find_device` (§3.5), **Use** buttons (§4.4) |
| P8.3 Review probes changed devices | **changed** | a dry run must stay traffic-free (it is allowed in a take, probes are not) | the page calls `probe_device` for each changed device before showing Review, outside a take (§4.1 Review) |
| P8.4 hat and INA219 live status | **accepted** | hat card state only in the journal (`App:9344`; grep `hat_card`); `slot` is computed each loop (`App:9319`) | `cfexpress_hat` and `ina219` entries in `hardware_status` (§3.5, §3.6) |
| P8.5 PCF8574A `0x38`-`0x3F` | **accepted** | datasheet knowledge | §4.4, §5, labelled UNCONFIRMED in the KB |
| P8.6 states with a time | **accepted** | Cinemate does it (`Cm …settings_editor.html:7379-7385`, `CO`) | `since` in the snapshot; "lost at 21:20: Remote I/O error" |
| P9a Turn = one select | **accepted** | Cinemate's quad Turn (`Cm …:3541`, `R1 §1.7`) | **Turn adjusts**, with **Separate** keeping the two lines (§4.1) |
| P9b record/toggles allowed on a turn | **accepted** | `ActionCatalog.hpp` `sources = Both` for `capture` etc. | `isStepping`/`warnOnTurn`; stepping first in the menu; validator `turn_starts` (sketch check 10) |
| P9c one `invert_direction` for four knobs | **accepted** | `HW/NeoRotary4Input.cpp:417-418`, `:582` | per-knob **Swap**; device pill "Invert all four knobs" |
| P9d duplicates dropped silently | **accepted** | `HW/ButtonActionList.hpp:103-104` | menu disables a held action; validator `duplicate_action` (sketch) |
| P9e Knob 1-4 vs `encoder0-3` | **accepted** | — | the key and line under each gesture (§3.2, §4.1) |
| P9f Listen | **accepted, changed** | unmapped controls never reach App (`App:8810-8811`, `HW/NeoRotary4Input.cpp:658-665`); a NeoRotary with no actions does not start (`:317-321`) | **Changed:** a polled state field `hardware_last_input`, not an event. The WebUI has no socket events (it polls `/api/state` each second, `Web:11652`), and a per-detent event would be broadcast to every socket client. The NeoRotary starts when enabled even without actions (R22, Q21). In T42 |
| P9g run-script paths | **accepted** | Q2 keeps them ssh-only | the menu item shows the path or "not set (set it over ssh)" |
| P10.1 merge a stale text save per key | **accepted** | — | `textToEdits()` in the sketch (check 10: a value-only text merges with an IMU write; a comment edit does not); Q17 default merge + review |
| P10.2 stale banner from the poll | **accepted** | — | §4.1 redraw rule, §4.2 |
| P10.3 Easy → Text → Easy without trapping the draft | **accepted** | — | §4.3 |
| P10.4 keep other draft changes on a same-key conflict | **accepted** | — | §4.3, `conflicts[]` in refusals (CC C2) |
| P11.1 show effective values | **accepted** | `bus=1  # x` → default 10 (`App:4448-4467`) | `effectiveValue()` (sketch check 10), shown in red on the row |
| P11.2 a duplicated section locks its rows | **accepted** | same as CC D2 | §3.2 |
| P11.3 `section` and `key` in `Issue` | **accepted** | `sketch-v1/…:518-523` | done in the sketch |
| P11.4 Fix buttons | **accepted** | — | T43, four mechanical rules (§4.2); first in the cut order if the budget shrinks |
| P12.1 validate at Core start; counts in state | **accepted** | v1 validated only on the first `get_controls` | row 37.7; `controls_errors`/`controls_warnings` |
| P12.2 409 for a browser POST without the header | **accepted** | `allowedBrowserOrigin` tells browsers from native clients by `Origin` (`WS:156-161`) | row 38.2 |
| P12.3 first-open sheet; warn only about enabled or answering hardware | **accepted** | the image's tally on a PCF8574 at bus 10 · 0x20 with no chip (`HL` 2026-10-25, reopened) | §1.2 E, §4.1 Card 1; the "No [cfexpress_hat]" warning only if the hat answers somewhere |
| P12.4 header only on a WebUI save | **accepted** | — | §3.1 |
| P13.1 rename Revert → Discard changes | **accepted** | Cinemate's Revert loads stock defaults (`Cm …:1405`, `CO`) | §4.1 |
| P13.2 Undo last save | **accepted** | — | §4.1, T42 |
| P13.3 pill "Saved 21:14 · WebUI" | **accepted** | — | §4.1 |
| P13.4 history summaries | **accepted** | — | `summary` in `controls_history`; Core builds it from the diff and catalog labels (row 42.2) |
| P14.1 a test line; optional `test_output` | **accepted (line), not built (command)** | the tally flashes 320 ms on a photo (`HW/RecordingIndicatorOutput.cpp:522`) | the hint in Card 4; `test_output` → Q23 |
| P14.2 open drain + active high | **accepted** | `GPIO_V2_LINE_FLAG_OPEN_DRAIN` (`HW/RecordingIndicatorOutput.cpp:644-645`); the level from `outputPhysicalValue` (`:226-229`); the UI template writes `open_drain=true` with `active_high=false` for the trigger (`UI:src/DisplayConfigBridge.cpp:110-112`), which is consistent, so the trap needs both flipped | validator `open_drain_high` (sketch); wiring hint under the pills |
| P14.3 PCF outputs that do not follow the expander | **accepted** | inheritance only from a `[pcf8574]` above (v1 rule) | "its own setting … [Follow the PCF8574]" |
| P14.4 warn when buttons and an output share one PCF8574 | **accepted** | same as CC's PCF note | `pcf_shared` (sketch) |
| P15 hold/double delay Record without saying so | **accepted** | — | row 44.3 warning; timings shown |
| 16a pinless row | **accepted** | Cinemate drops it (`R1 §1.3`) | Save blocked (§4.1) |
| 16b HDMI DDC buses offered | **accepted** | — | listed, disabled for devices |
| 16c six columns at phone width | **accepted** | — | stacked rows |
| 16d nano half-file banner | **accepted** | — | two equal stats (§3.4) |
| 16e Off devices not dimmed | **accepted** | Cinemate dims them (`Cm …:7494-7498`) | dimmed, "mappings kept" |
| 16f standby behaviour | **accepted** | `App:8820-8826` | one line in Card 3 |
| 16g a section alone enables PCF8574/NeoRotary/Grove | **accepted** | `HW/NeoRotary4Input.cpp:386-390` and siblings | Add a device writes `enabled=false` unless Find/Probe found it |
| 16h T39 test 5.3 cannot pick bus 15 | **accepted** | the select lists only existing buses (v1 §4.4) | T40 test 5.3 uses `core.py` |

### Walkthroughs, verdict table, Cinemate table, Missing

| Point | Verdict | v2 |
| --- | --- | --- |
| W1-W10 | **accepted** | each step maps to P1-P16 above; v2 §1.2 adds walkthroughs D and E and rewrites A-C |
| Verdict §7: "T43's own test triggers the template before T43" | **accepted** | the template removal is in T38; T45's test no longer renames the file; T38's test does, after the removal |
| Cinemate: plain-words remap confirm | **accepted** | Review's `summary[]` (§4.1) |
| Cinemate: search box "not needed" | agreed | — |
| Missing 1-5 | **accepted** | P1, P9, P8, P13, Review summary |
| Missing 6: where each thing lives | **accepted** | §3.1 table |
| Missing 7: an on-set sheet | **accepted** | §4.6 |

### Questions, risks, measurements, order

| Point | Verdict | v2 |
| --- | --- | --- |
| Q15 per-line GPIO requests | **accepted** | Q15 |
| Q16 Restart Camera in the pending card | **accepted** | Q16 |
| Q17 stale text merge | **accepted** | Q17 |
| Q18 move 43.1 into T37 | **changed** | decided in the design: the removal is T38. It is an order question, and the safety argument (P4) settles it. No question for Patrik |
| Q19 touch status line mandatory | **changed** | decided: mandatory in T40. Q19 now asks only where the chip sits |
| Q20 remap knobs on the camera | **accepted** | Q20, default no |
| Q21 Listen worth it | **accepted** | Q21, now about R22 (the NeoRotary runs without actions) |
| Q22 history coalescing | **accepted** | Q22 |
| R16-R19 | **accepted** | R16-R19; R17 is now mitigated by design. New: R20 (reload side effects), R21 (take-start race), R22 (NeoRotary polls without actions), R23 (`systemctl` as `pi`) |
| M2b start times | **accepted** | M2b, as `ActiveEnterTimestampMonotonic` + `boot_id` |
| M3b DRM connectors | **accepted** (as information) | M3b, labelled information only (P7.1) |
| M5b UART pins | **accepted** | M5b |
| Off the Pi: NeoRotary jumper range, PCF8574A range | **accepted** | labelled UNCONFIRMED in §4.4 until read |
| Order table | **accepted, renumbered** | §6 rows; T37 split into T37 + T38 to keep each tutorial at ≤ 3.5 h |
| Budget note: drop drag onto another line first | **accepted** | drag reorders within a line; × and + move (§4.1, §9.4) |

---

## 3. What v2 adds that neither critic asked for

| Addition | Why | Where |
| --- | --- | --- |
| `number()` refuses `ERANGE` | the E2 comparison found the underflow difference | sketch `ActionCatalog.hpp` |
| INA219 "on without a section" warning | found while checking D4 (`App:4283`) | validator, sketch check 10 |
| `%` in `[cfexpress_hat]`/`[storage]` rule (spec) | `configparser`'s interpolation raises on `get` (`App:3480-3494` reads those sections) | §3.7 |
| A cut order for the budget | the size grew from ~5,400 to ~7,450 lines | §6 Size |
| "Minimum path" T36-T40 | useful on its own: the fix, status on both screens, a safe file | §0.12 |
| Groups G/N/A/hat/ina219 | the precise form of CC A4b, and why G is one group (shared lines and chip) | §3.6 |
