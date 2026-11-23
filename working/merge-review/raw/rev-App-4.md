# Review App-4: ApertarCoreApp.cpp, port lines 10813-12620 (workers, media gate, Controls backend)

Stage 2 of 3. Input: `/home/user/build/review/diffs/App.part04.diff` (1822 lines, read completely), inventory
`raw/inv-App-4.md`. Yardstick: `raw/conv-core-command-plane.md` (C1-*), `raw/conv-core-camera.md` (C2 sections).
Port refs `@cinemate-port` `01f170c`; upstream refs `@upstream-1.6.0` `/home/user/wt/core-upstream`.
Port line = diff line + 10807 (checked at `commandMutex_` sites 10921, 11254, 12324, 12571).

## 1. Verdict in one table

| Id | Title | Cat | Sev | Effort | Deliberate |
| --- | --- | --- | --- | --- | --- |
| App-4-F1 | Second dispatcher `handleReadOnlyHardwareCommand` before the lock; `get_controls`/`controls_history` duplicate `GET /api/config` | mismatch | major | M | yes |
| App-4-F2 | Storage pre-roll worker starts and finishes a camera take outside `handleCommand` | mismatch | major | L | yes |
| App-4-F3 | Record gate refuses a `--media PATH` that is not a mount point | removed-upstream-behaviour | major | S | no |
| App-4-F4 | Automatic storage pre-roll on by default: a raw take at every boot, insert and format | new-ground | major | S | yes |
| App-4-F5 | `APERTAR_*` env knobs read in the command plane and workers, env beats the file | mismatch | major | M | yes |
| App-4-F6 | Process-global state in header singletons instead of App member groups | mismatch | major | L | unknown |
| App-4-F7 | Controls worker polls the hardware file every 2 s (a file watcher in Core) | mismatch | minor | S | yes |
| App-4-F8 | Ticket numbers, KB paths, critic ids and 149 comment lines in the slice | slop | major | M | no |
| App-4-F9 | Buffer level pushed by an App polling thread, not emitted by the camera | mismatch | minor | M | yes |
| App-4-F10 | Two `buffer` events in one loop turn | bug | minor | S | no |
| App-4-F11 | Media tuning helper runs `sudo -n` without `/usr/bin/timeout` and absolute paths, on the watcher thread | mismatch | minor | S | no |
| App-4-F12 | Five idle predicates and four clock helpers | duplication | minor | M | no |
| App-4-F13 | `[cfexpress_hat]` parsed by two parsers with defaults in two places; `get_controls` parses the file 8 times | duplication | minor | S | no |
| App-4-F14 | `scan_i2c` and `get_controls` probe I2C lock-free; design's `i2cMutex_` and per-address take check missing | bug | minor | S | no |
| App-4-F15 | `record_start` may wait up to about 4.5 s under the command lock for a trim and a rename | bug | minor | S | yes |
| App-4-F16 | Media watcher also runs playback chores; hold reason round-trips string -> enum | slop | minor | S | no |
| App-4-F17 | Media tuning reads a separate file `~/apertar-media-tune.conf` | mismatch | minor | M | unknown |
| App-4-F18 | Trim root helper and sudoers rule for user `pi` | security | minor | S | yes |
| App-4-F19 | Board assumptions: hat on bus 10, one PCIe NVMe, 28 header lines, Pi 5 bus numbering | pi-compat | minor | S | no |
| App-4-F20 | Small wording and shape nits | slop | nit | S | no |

No protocol break found (section 4).

## 2. Findings

### App-4-F1 Second dispatcher before the lock; Controls reads duplicate `/api/config` (mismatch, major)

| Side | Evidence |
| --- | --- |
| Port | `App:12418` `std::optional<std::string> ApertarCoreApp::handleReadOnlyHardwareCommand(const ControlCommand &command)` with five `if (command.name == ...)` blocks; `App:12562` `if (const auto reply = handleReadOnlyHardwareCommand(command)) return *reply;` and `App:12565` `if (command.name == "test_input") return testInputReply(command);` both before `App:12571` `std::lock_guard<std::mutex> commandLock(commandMutex_);` (confirmed) |
| Port | `get_controls` reply `App:12428-12455`: `"controls":{... "issues":[..], "text":"<whole file>", "replaced":{..}, "model":{..}, "peripherals":[{..,"status":{..,"chip":{..},"pins":[..]}}], "i2c_buses":[..], "apply":{.."pending":[..]}, "dpi_lines":[..]}` (confirmed). Consumers: WebUI only (`WCP:18264`, `:18518`, `:18556`); touch UI has none (`grep` in `Apertar-UI/src`, `qml`: 0) |
| Port | `GET /api/config` and `POST /api/config` still exist (`App:8613`, `:8620`) |
| Upstream | One chain, one lock on the first line: `App:9091-9093@upstream-1.6.0` `std::string ApertarCoreApp::handleCommand(...) { std::lock_guard<std::mutex> commandLock(commandMutex_);`. C1-S02 lists "a second dispatcher function" as a violation; C1-S03 lists "a command body that runs before the lock" |
| Upstream | Lock-free reads of the hardware file are an HTTP route: `App:7168-7173@upstream-1.6.0` `if (request.method == "GET" && request.path == "/api/config") { ... response.body = buildHardwareConfigFileJson();` (C1-S09, 5.7: file work goes through routes, no lock) |

Why it matters: the original developer finds a second command chain, and a socket command that returns the same file
`GET /api/config` returns, in a third JSON shape (deeply nested, against C1-I09 / 5.5's short list of nested reply
members). The design weighed the lock (`working/controls/design-controls.md:112`, `:644-650`), not the existing route.

Rework:
1. Extend `buildHardwareConfigFileJson` (`App` port, upstream `App:5290`) with `revision`, `written_by`, `issues`,
   `replaced`, `model`, `peripherals`, `i2c_buses`, `apply`, `dpi_lines`. Nested members are normal in `/api/state`
   (5.5), so the shape is acceptable there. The WebUI `controlsCall({cmd:"get_controls"})` becomes `fetch("/api/config")`.
2. `controls_history` -> `GET /api/config/history` and `GET /api/config/history?name=` in `handleWebRequest`, same
   route idiom (`queryParameterValue`).
3. `controls_last_input`, `list_actions`, `scan_i2c` -> ordinary blocks inside the `handleCommand` chain under the lock
   (cheap; `scan_i2c` is about 117 single-byte reads, shorter than `format_media` or `calibrate_gyro`, which upstream
   runs under the lock, rough edge 18). Or GET routes if the WebUI is the only reader.
4. `test_input` stays the one pre-lock exception (it re-enters `handleCommand` through `handleHardwareInputAction`;
   the mutex is not recursive). One comment line saying that.
5. Delete `handleReadOnlyHardwareCommand`.

Risk: WebUI Controls page calls change (`WCP:16919-18895`); tested only on desk per `f5a61b8`.

### App-4-F2 Pre-roll worker drives the camera outside `handleCommand` (mismatch, major)

| Side | Evidence |
| --- | --- |
| Port | `App:11254` `std::lock_guard<std::mutex> commandLock(commandMutex_);` inside `runStoragePrerollOnce` (a worker thread), then `App:11268` `camera_.startStoragePreroll(&error, &fps)`; after the clock loop `App:11297` `camera_.finishStoragePreroll()` without any lock (confirmed) |
| Port, same slice, the Apertar way | Safety stop `App:11107-11109`: `command.name = "record_stop"; dispatchHardwareInputCommand(std::move(command));` |
| Upstream | C1-S01 "every change of camera state ... enters through `handleCommand`"; violation listed: "a worker thread that calls `camera_.setX()`". Camera-owned timed work lives in `CameraController` (`timelapseLoop`, `CC:8447@upstream-1.6.0`) |

Why: a third and fourth take-start/stop path besides the command chain; the guards are a separate copy
(`storagePrerollGuard`, `App:11121`) of the command-head guards.

Rework: the worker builds `ControlCommand{name:"storage_preroll", trigger, seconds}` and sends it through
`dispatchHardwareInputCommand` like the safety stop. The `storage_preroll` block (outside this slice) runs the guards
that already sit at the head of `handleCommand` and calls `camera_.startStoragePreroll`. The take's own length and
its finish move into `CameraController` (a timer thread like `timelapseLoop`), which emits the end as an event. App
keeps only the request/coalesce part. Delete `storagePrerollGuard` once the head guards cover it.

### App-4-F3 `--media PATH` must now be a mount point (removed-upstream-behaviour, major)

| Side | Evidence |
| --- | --- |
| Port | `App:12596-12600` gate on `capture_photo`, `record_start`, `timelapse_start`; `App:11373-11374` `case MediaSnapshot::State::None: return "No media mounted at " + options_.mediaRoot + ".";`; `src/util/MediaProbe.hpp:193-195` `if (!entry.found) { snapshot.state = MediaSnapshot::State::None;` (no `/proc/mounts` entry for the exact path). Bypass only `App:11335` `getenv("APERTAR_MEDIA_REQUIRE_MOUNT")` or `simulateCamera` |
| Upstream | README:253@upstream-1.6.0 "`--media PATH` | Recording destination. Default: `/media/RAW`."; no mount or free-space check in CC (conv C2 5.6: "There is no check for free space or a mounted drive in `CC`. A full or missing drive shows up through this latch.") |

Failing input: `apertar-core --media /home/pi/clips` (a plain folder on the SD card) -> `record_start` answers
"No media mounted at /home/pi/clips." Upstream records.

Rework: keep the refusals that carry real value (`Removed`, `Error`, below the floor). For `None`, refuse only when the
folder does not exist or is not writable; a folder that is not a mount point records as upstream. Delete
`APERTAR_MEDIA_REQUIRE_MOUNT`. The same predicate is used by `storagePrerollGuard` (`App:11138`) and
`playbackHoldReason` (`App:11353`); change them together.

### App-4-F4 Automatic pre-roll default on (new-ground, major)

Port: `src/util/StoragePreroll.hpp:98` `return conf.automatic.value_or(true);`; requested at Core start, card insert and
format from the watcher (`App:10945-10960`). While it runs, nine commands answer "Storage pre-roll is running. One moment."
(`App:12588-12592`), including `record_start`, `format_media`, `eject_media`, `enter_standby`. Upstream: no warm-up at all
(no precedent). Deliberate: yes (`d44b177` message "on Core start, card insert, format and by hand").

Why: an unmodified original user gets a raw take written and deleted at every boot, and record refused for its
length plus up to 2 min of trim wait plus 3 s settle. That is a default change the original developer would not accept.

Verdict simplify: default `[media] preroll=off`; keep the manual `storage_preroll` command and the switch.

### App-4-F5 Env knobs in the command plane (mismatch, major)

Port reads in this slice: `APERTAR_MEDIA_REQUIRE_MOUNT` (`App:11335`, on every gate call), `APERTAR_MEDIA_MIN_FREE_MB`
(`App:11379`), `APERTAR_MEDIA_TUNE` (`App:11402`), `APERTAR_STORAGE_PREROLL` (`App:11154`); `APERTAR_MEDIA_TRIM`
(`mediaTrimEnvOff()`, `App:11443`, `:11943`) and `APERTAR_CLIP_MERGE` (`BufferBudget.hpp`) via helpers. 15 `getenv("APERTAR`
in port `App` against 2 upstream (`App:4254`, `:4273@upstream-1.6.0`, both `APERTAR_HARDWARE_CONFIG`). Several "beat the file"
(`App:11113-11117` comment).

Upstream: C1-S24 "a launch option is an `Options` member ... an environment variable switch in the command plane" is the
violation; 0 `APERTAR_*` reads in `handleCommand`. Bench knobs exist in CC (C2 5.11) but none switch a feature against a
saved setting.

Rework: delete the env reads. Each switch has (or gets) one home: `[media] preroll`, `[storage] clip_merge`, the persisted
trim switch (`mediaTrimSetting_`), `[media] min_free_mb` and `[media] kernel_tune` in `apertar-hardware.conf`, parsed once by
their owner. `APERTAR_MEDIA_REQUIRE_MOUNT` goes with F3.

### App-4-F6 Global state in header singletons (mismatch, major)

Port: `BufferBudget.hpp:231-234` `inline SafetyStopState &safetyStopState() { static SafetyStopState state; ...`;
`:330-333` `clipMergeRequest()` static atomic; `StoragePreroll.hpp:234-249` `prerollState()`, `prerollActive()`,
`setPrerollLast`; `playbackYield()` (PlaybackHold); `HardwareConfigStore.cpp:499-501` `static HardwareConfigStore store(...)`.
Used throughout this slice (`App:10886-10905`, `:11266`, `:11703`, `:12421`).

Upstream: C1-S18 "Each group starts with its mutex and ends with its thread" in `AppH`; C1-S19 "no singleton";
violation listed: "a thread stored in a global", "a singleton App pointer". Parts own their state as members
(`AppH:110-176@upstream-1.6.0`).

Rework: move each state block into an App member group (`preroll`, `safety stop`, `playback hold`) or into
`CameraController` where the camera writes it (`safetyStopState` is written by the write queue). `configStore()` becomes
an owned member (`hardwareConfig_`) passed by reference to the parts that need it. Keep the pure functions in the headers.

### App-4-F7 Controls worker polls the file every 2 s (mismatch, minor)

Port: `App:12250` `controlsWake_.wait_for(lock, std::chrono::seconds(2), ...)` then `App:12257` compares the file text
with the applied text, to "look for an edit made outside (Config, ssh)" (`App:12242-12243`). Upstream: C1-S08 lists
"a file watcher in Core" as a violation; C1-S21 no timer thread; after a save upstream says to restart
(`WCP:3869@upstream-1.6.0` "Hardware, input, display, and sensor changes may need ApertarCore or the UI restarted").
Deliberate: yes (`working/controls/decisions.md:47`).

Verdict keep the worker (the join/deadlock reason in `design-controls.md:93-98` is sound) but simplify: wake only on a
save (`set_controls`, `POST /api/config`); drop the 2 s timeout; an ssh edit applies at the next save or restart, as upstream.

### App-4-F8 Slop in comments (slop, major)

In `App:10813-12620`: T39 (`10870`, `12168`, `12242`), T40 (`12487`), T42 (`12125`, `12472`), T42/T43 (`12459`), T47 (`10910`,
`10967`, `11339`, `12572`), T48 (`10978`), "critic S11" (`10922`), "critic Y11" (`11377`), "design §2.7" (`11339`, `12573`),
"kb working/dng-chain, R4" (`10892`), "probe-exfat-dir.md" (`11621`, `11899`), "the NVMe campaign does, for its A/B" (`11627`),
install instructions in a log line (`App:11508-11512`). 149 comment lines in 1808 lines; upstream `App` has 10 comment
lines in 11 025 (C1-I14: "A comment that repeats the code, a ticket number, a banner" is a violation). Banners
`// ---- Storage pre-roll ----` (`App:11113`), `// ---- Media trim ----` (`App:11433`), `// ---- Merge worker ...` (`App:11620`).

Rework: delete ticket, critic, KB and file references and banners; keep one hazard sentence per worker (why a
thread, why not under the lock). Move measurement numbers to the KB.

### App-4-F9 Buffer level from an App polling thread (mismatch, minor)

Port: `runBufferEvents` `App:10993-11052`, 250 ms / 1 s poll of `camera_.frameBufferStatus()`, nine global states.
Upstream: camera-state edges are emitted by `CameraController` through its event callback, e.g. `emitMediaWriteState`
(`CC:7551-7563@upstream-1.6.0`, "Serialize edges"); C1-S12 events are built at the emit site; C1-S21 no polling thread.
Deliberate: yes (comment `App:10986-10992`: avoid the controller mutex during a drain).

Rework: the write queue emits `buffer` on a level change through the existing event callback (rate limit in the
queue, like `emitMediaWriteState`'s edge check). The pre-roll and safety-stop flags travel in the `settings`/`recording`
events or in `get_state`. Delete the thread.

### App-4-F10 Duplicate `buffer` event (bug, minor)

`App:11021-11033` publishes when any watched value changed, without updating `sentUsed`/`sentCapacity`; then
`App:11037-11039` publishes again because `buffer.used != sentUsed`. Input: during a take, a dropped frame and a level
change in the same 250 ms turn -> two identical events to every socket client. Fix: one publish per turn (set
`sentUsed`/`sentCapacity` in the first branch, or merge the branches). Disappears with F9.

### App-4-F11 `sudo -n` without timeout on the watcher thread (mismatch, minor)

Port: `App:11423-11425` `std::string("sudo -n ") + helper + ... shellQuote(profile.rootDisk) ...` then `runShellCommand`.
Upstream: `App:1541-1550@upstream-1.6.0` `"/usr/bin/timeout 6s /usr/bin/sudo -n /usr/local/libexec/apertar-standby-usb "`,
comment "Fixed executable and arguments only". Why: a hung helper stops the media watcher (no more yank detection).
Fix: same shape as upstream: `/usr/bin/timeout 6s /usr/bin/sudo -n <helper> ...`.

### App-4-F12 Five idle predicates, four clocks (duplication, minor)

Predicates: `storagePrerollGuard` (`App:11121`), `playbackHoldReason` (`App:11341`), `mediaTrimMayRun` (`App:11471`),
`clipMergeMayRun` (`App:11697`), `recordingGateActive` (`App:12237`), each listing recording / sound / timelapse / writes
pending / delete / preroll / speed test / standby in a different subset. Clocks: `trimNowMs`, `clipMergeNowMs` (`App:11630`),
`playbackNowMs`, `monotonicMicros` (`App:12219`). Upstream writes such checks inline in the command head (C1-S04) and has
one clock idiom (`std::chrono::steady_clock::now().time_since_epoch()`, `App:9112-9114`).
Fix: one `bool mediaIdle(std::string *why) const` used by trim, merge and pre-roll; one clock helper.

### App-4-F13 `[cfexpress_hat]` parsed twice (duplication, minor)

`loadCfeHatConfig` hand parser (`App:5298`) vs `cfeHatPeripheralJson` through `hwconf` with literal defaults
`"10"`/`"0x34"` (`App:12089-12091`). `get_controls` calls `hwconf::parse(info.text)` eight times (`App:12439-12447`).
Upstream C1-S07: one owner per section. Fix: one `CfeHatConfig` parser, used by both; parse once into a local.

### App-4-F14 Lock-free I2C probing (bug, minor)

`scan_i2c` checks `recordingGateActive()` once (`App:12489`) and then probes 0x03-0x77 without the command lock or a
mutex; `get_controls` probes the hat and every peripheral Core does not run (`App:12037`, `:12097`) also during a take.
The design promised "Scans and probes take their own `i2cMutex_` ... and check the recording gate before each address"
(`design-controls.md:648-650`); `grep i2cMutex` in port `src/`: 0. Input: two WebUI tabs open on Controls -> two
scans interleave on one bus; record pressed during a scan -> the scan continues. Fix comes with F1 (under the lock).

### App-4-F15 Record start waits for trim and merge (bug risk, minor)

`App:12614-12619`: `waitForMediaTrim(name, 5000)` (2 s wait, SIGTERM, 1 s, SIGKILL, 0.5 s: `App:11950-11963`) and
`waitForClipMerge(name, 5000)` (up to 1 s, `App:11914`) run under `commandMutex_` before a take. Worst case about 4.5 s from
button to take. Upstream accepts slow work under the lock (rough edge 18) but not on `record_start`. Fix: kill the trim at
once on `record_start` (no 2 s grace); keep the merge wait (one rename).

### App-4-F16 Watcher does playback chores (slop, minor)

`App:10970-10979`: yield-window renewal and `playback::trimIdleFrameSlots` in the media watcher ("no new thread");
the hold reason is turned into a string by `playbackHoldReason` and back into an enum by five `if (hold == "...")`.
Fix: `playbackHoldReason` returns `playback::Hold`; `holdName` only at the JSON edge; the slot trim belongs to the
playback code's own call sites.

### App-4-F17 Separate media tuning file (mismatch, minor)

`applyMediaTuning` reads `loadMediaTuneLogged(...)` from `kMediaTuneBasePath = /home/pi/apertar-media-tune.conf`
(MediaTune.hpp, outside slice). Upstream stores: `camera_settings.conf`, `UI.conf`, `apertar-hardware.conf`
(BRIEF; C1-S07). Fix: `[media] kernel_tune` in `apertar-hardware.conf`; drop the per-user file.

### App-4-F18 Root helpers (security, minor)

`App:11482-11512`: `/usr/local/libexec/apertar-media-trim` through `sudo -n`; `config/apertar-media-trim.sudoers`
`pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-media-trim` (any argument; "the script itself validates its argument").
Upstream has the same pattern for standby helpers (`App:1544`, `:1549@upstream-1.6.0`) but ships no helper script in the
repo. Keep, but pin the argument form in sudoers or make the helper take no path (trim the mount it finds itself);
script validation not read here (unconfirmed; read `scripts/apertar-media-trim`).

### App-4-F19 Board assumptions (pi-compat, minor)

Hat default bus 10 / 0x34 (`App:12089-12091`, Pi 5 RP1 numbering); `nvmeDriveSummary` takes the first PCIe NVMe
(`App:12059-12081`); `readGpioChipInfo(chipPath, 28)` (`App:11989`); `i2cBusesJson` comment "missing on this kernel"
(`App:12145`). `cfeHatPeripheralJson` probes bus 10 even when the file has no `[cfexpress_hat]` section, so a Pi 4 shows
"Bus 10 does not exist on this Pi." on the card. Fix: show the hat card only when the section exists.

### App-4-F20 Nits (slop, nit)

- `"scan_i2c needs bus= (a bus from Settings > Config > Hardware)."` (`App:12493`): upstream family is "`<name>` requires `<field>`." (C1-I07).
- `"Media is not answering (errno " ... ")"` (`App:11372`): developer detail in an operator sentence (C1-I07).
- `list_actions` strips braces with `body.substr(1, body.size() - 2)` (`App:12541`).
- `stopMediaWatcher` stops six threads (`App:11054-11081`); name says one.
- `get_controls`, a "read-only" command, writes `controlsErrors_`/`controlsWarnings_` (`App:12425-12426`).

## 3. Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| media watcher thread `runMediaWatcher` | keep | A hung `statvfs` must not block the main loop or the lock; precedent C1-S20 (speed-test worker). Takes `commandMutex_` only for `checkRecordingFailure`, as `wait()` does (`App:7032-7033@upstream-1.6.0`). Remove playback chores (F16) |
| `MediaSnapshot`, `probeMediaRoot`, `cachedMediaSnapshotOrProbe` | keep | `Snapshot` naming per C1-I16; pure, host-tested. Change `None` handling (F3) |
| `MediaFault`, `MediaIntent` | keep | The latch follows the CC failure latch (conv C2 5.6); outside slice |
| `CfeHatReader`, `CfeHatConfig` | simplify | One parser for the section (F13); hat off by default is right (`CfeHat.hpp:19`) |
| `MediaProfile`, `MediaTune` | simplify | Profile keep; tuning file -> hardware conf key, helper call shape as upstream (F11, F17) |
| media trim worker + root helper | keep | Measured need (`d44b177`: 0.9 TB stall); off when the helper is missing. Drop env knob (F5), shorten record wait (F15) |
| clip merge worker | keep | Only acts on the port's own split clips; careful ordering and RENAME_NOREPLACE; host test. Drop env knob |
| buffer event thread | rework-to-upstream-pattern | Camera emits edges through its callback (F9) |
| buffer safety stop thread | keep | Stops the take the Apertar way: `record_stop` through `dispatchHardwareInputCommand` (C1-S11). State out of the global (F6) |
| storage pre-roll worker | rework-to-upstream-pattern | Take start/finish through `handleCommand` and CC (F2); default off (F4) |
| controls worker | simplify | Join/deadlock reason is sound; drop the 2 s file poll (F7) |
| `hwconf` (`HardwareConfigText.hpp`, `ControlsModel.hpp`) | simplify | New ground for the editor and validator; must not become a second runtime parser of sections the classes parse (F13, C1-S07) |
| `hardware::HardwareConfigStore` / `configStore()` | rework-to-upstream-pattern | Function-static singleton; make it an owned App member (F6) |
| `hardware::actions::catalogJson` | keep | WebUI needs the list; keep it next to `parseButtonActions` so the two do not drift |
| `probeI2cAddress`, `GpioChipInfo` | keep | Read-only, small; serialise probes (F14) |
| `playback` namespace (`Hold`, `playbackYield()`, `trimIdleFrameSlots`) | simplify | Rule as pure function keep; global `playbackYield()` -> App member (F6); enum not string (F16) |
| `handleReadOnlyHardwareCommand` | rework-to-upstream-pattern | Routes and chain blocks (F1) |
| host tests `tools/*_test.cpp` | keep | Off the build, no harm; upstream has none, document them for the developer |

## 4. Protocol

| Check | Result |
| --- | --- |
| Original UI vs new events `media`, `buffer`, `controls` | Ignored: `ApertarControlBridge.cpp:1184-1259@upstream-1.6.0` matches named events only; the fall-through applies a message only if `event == "settings"` or it has `ok` (confirmed) |
| Original UI vs new commands | It sends none of them (confirmed, grep) |
| Flat command parser | All new commands take scalars (`bus`, `name`, `section`, `key`); no nested input |
| Original commands' replies | Unchanged except the new refusals (F3, F4, delete interlock), which are operator sentences in `error` |
| Event shape | `{"event":"<name>",...}`, key first, no spaces (C1-I20): conforms |

## 5. What conforms

- New guards sit at the head of `handleCommand` as `||` lists of command names, each with its own operator sentence (`App:12585-12600`), C1-S04.
- Refusal sentences "Deleting media. One moment.", "Storage pre-roll is running. One moment.", "Media was removed. Insert or mount media before recording." follow C1-I07.
- Safety stop dispatches `record_stop` through `dispatchHardwareInputCommand` (`App:11107-11109`), C1-S11.
- Watcher abort of a take on a lost medium: fault latch, then `checkRecordingFailure` under `commandMutex_`, as `wait()` does (C1-N05).
- Threads are `std::thread` members started with `std::thread(&ApertarCoreApp::runX, this)`, stopped by flag + notify + join, no `detach` (`App:8026-8051`, `:11054-11081`), C1-S17.
- JSON by hand with `std::ostringstream`, `escapeJson`, `(x ? "true" : "false")` throughout, C1-I08; state fragments with a leading comma spliced into the existing builders.
- Hardware-file restarts call the classes' own `stop()`/`start()` in boot order (`App:12303-12321`) and re-sync the tally under the lock, C1-S25.
- `help` lists the new commands (`App:12930`), 5.6.
- Optional hardware off by default (`CfeHatConfig::enabled = false`), C1-S25.
- Log lines are `std::cerr` with a fixed `ApertarCore <topic>:` prefix, C1-I13 (but many success lines, against "success is silent").

## Skeptic

Every finding re-read on both sides (`/home/user/Apertar-Core` @cinemate-port, `/home/user/wt/core-upstream` @upstream-1.6.0).

| Id | Verdict | Why (one line) |
| --- | --- | --- |
| F1 | stands | Confirmed `App:12418`, `:12562-12565`; upstream lock is line 1 (`App:9093`), `GET /api/config` (`App:7168-7173`) still in the port at `App:8613` and the WebUI uses both (`WCP:18264`, `:18741`). Design `design-controls.md:644-650` weighed the lock, not the route |
| F2 | corrected | Confirmed. Better precedent: the upstream idle timer builds a `ControlCommand` and calls `handleCommand` (`App:7041-7047@upstream`). Rework keeps the pre-roll-only checks (camera ready, still mode, raw format) inside the `storage_preroll` block; `decideGuard` is not fully covered by the head guards |
| F3 | corrected | Confirmed refusal, but upstream already treats an unmounted media root as "no media" (speed test `App:8970-8974@upstream`, library `App:7676@upstream`), and the reviewer's rework would let a take land on the SD card under an empty `/media/RAW`. Plain-folder case was considered (comment `App:11328-11329`): deliberate yes, severity minor; rework is a launch option, not a weaker gate |
| F4 | stands | `StoragePreroll.hpp:98` `value_or(true)`; default format is cDNG (`CC:5562`), so the raw-format guard does not skip it |
| F5 | corrected | Upstream does have developer env knobs outside `HARDWARE_CONFIG`: `LossyDngEncoder.cpp:100`, `:325@upstream`, read once in a `static const` lambda in the owning file, overriding no saved setting. The mismatch is env reads that override a saved setting and are re-read per call in App. Severity minor |
| F6 | corrected | Upstream also uses function-static singletons, but file-local in the owner's .cpp (`CC:885-889@upstream` `captureSettingsPersister()`, `LossyDngEncoder.cpp:114-118@upstream`). `playbackYield()` is file-local in App (`App:6342`) and conforms: removed. Real cases are header-level state shared across parts: `safetyStopState()` (App 10, CC 10 uses), `configStore()` (App 20, `Mpu6050RecordingSession.cpp` 2); `prerollState()`/`clipMergeRequest()` have App as only user. Severity minor |
| F7 | corrected | Confirmed `App:12242-12268`. Rework incomplete: the 2 s poll also retries an apply deferred by a take; without it a wake at take end is needed. Note design-controls.md:93-95 says ssh edits are "never applied on the side", decisions.md:47 says polled every 2 s: the KB contradicts itself |
| F8 | stands | Confirmed all cited lines; 140 full-line `//` comments in `App:10860-12668` (reviewer 149, other counting); upstream App has 10 |
| F9 | stands | Confirmed. Extra upstream precedent: `audio_level` is emitted from the producer's callback (`App:8380-8384@upstream`) |
| F10 | stands | Confirmed `App:11021-11039`: first branch publishes without updating `sentUsed`, busy branch publishes again |
| F11 | corrected | Upstream's general `sudo -n` calls are bare too (`App:3031`, `:3205`, `:3353@upstream`); only the libexec helpers carry `/usr/bin/timeout` and absolute paths (`App:1544`, `:1549@upstream`). The tune helper is a libexec helper, so that shape applies. Runs only when kernel tuning is enabled (default off) |
| F12 | corrected | Confirmed the five predicates and their drift (`mediaTrimMayRun` ignores the safety-stop flush that `clipMergeMayRun` checks). `monotonicMicros` is compared with systemd monotonic timestamps (`App:12343`) and may stay; the three ms helpers are identical |
| F13 | stands | Confirmed `App:5298`, `App:12087-12091` (literal "10", "0x34"), 8 `hwconf::parse(info.text)` calls in `App:12439-12447` |
| F14 | dropped | Each probe opens its own fd and does `I2C_SLAVE` + one `read` (`I2cProbe.cpp:23`, `:34`); the i2c core serialises transfers per adapter, so two scans do not corrupt each other. The remaining point (lock and gate per scan) is fixed by F1 moving `scan_i2c` under `commandMutex_` |
| F15 | stands | Confirmed `App:11941-11964` and `:11904-11916`: 2 s + 1 s + 0.5 s + 1 s worst case under `commandMutex_` |
| F16 | stands | Confirmed `App:10970-10979`, `App:11341-11357` |
| F17 | corrected | Larger than stated: `~/apertar-media-tune.conf` holds eight write-path knobs and is read by CC and `CdngEncoder.cpp:91`, not only `kernel_tune`. Deliberate yes: 2edc6d0 argues for it. Only `kernel_tune` is in this unit; the file as a whole goes to the write-path unit |
| F18 | dropped | The script validates strictly (`scripts/apertar-media-trim`: one arg, under `/media/`, canonical, a mount point, discard capable, 20 s timeout); fstrim only discards free blocks. Upstream needs much wider passwordless sudo (`sudo -n mount`, `mkfs`, `sh -c`, `App:3373`, `:3609`, `:3810@upstream`). Packaging of helpers belongs to the install unit |
| F19 | corrected | Upstream itself defaults the hat to bus 10 / 0x34 and the Pi 5 PCIe controller (`App:3391-3395`, `:4303-4306@upstream`): the board assumption is inherited, not new. `readGpioChipInfo(chip, 28)` is the header line count on every 40-pin Pi: removed. What remains is the Config > Hardware row with "Bus 10 does not exist on this Pi." when no section exists. Severity nit |
| F20 | stands | Confirmed `App:12493`, `:11372`, `:12540-12541`, `stopMediaWatcher` stops six threads (`App:11054-11081`), `get_controls` writes `controlsErrors_`/`controlsWarnings_` (`App:12425-12426`); upstream style `"set_iso requires value."` (`App:9245@upstream`) |

## Final findings

### App-4-F1 [mismatch, major] Second dispatcher before the command lock; get_controls/controls_history duplicate GET /api/config
- where: `src/ApertarCoreApp.cpp:12418@cinemate-port`; `src/ApertarCoreApp.cpp:12562-12565@cinemate-port`; `src/ApertarCoreApp.cpp:12420-12456@cinemate-port`
- port way: `handleReadOnlyHardwareCommand` answers `get_controls`, `controls_history`, `controls_last_input`, `scan_i2c` and `list_actions` before `handleCommand` takes `commandMutex_`. `test_input` is also handled before the lock. `get_controls` returns a deeply nested object holding the whole file text, issues, model, peripherals with status/chip/pins, i2c_buses, apply and dpi_lines. Only the WebUI calls these commands (`WCP:18264`, `:18518`); the same WebUI also still uses `GET /api/config` (`WCP:18741`, route kept at `App:8613`).
- Apertar way: one flat chain under one lock taken on the first line (`src/ApertarCoreApp.cpp:9091-9093@upstream-1.6.0`; C1-S02 "a second dispatcher function", C1-S03 "a command body that runs before the lock"). The WebUI reads the hardware file without the lock through an HTTP route: `src/ApertarCoreApp.cpp:7168-7173@upstream-1.6.0` `GET /api/config` -> `buildHardwareConfigFileJson` (C1-S09, 5.7).
- why it matters: the original developer finds a second command chain, and a socket command that returns the file `/api/config` already returns, in a third JSON shape that breaks the short list of nested reply members (C1-I09, 5.5).
- rework: extend `buildHardwareConfigFileJson` with revision, written_by, issues, replaced, model, peripherals, i2c_buses, apply, dpi_lines (nested is normal in HTTP state). Add `GET /api/config/history[?name=]` in `handleWebRequest`. Move `controls_last_input`, `list_actions`, `scan_i2c` into ordinary blocks of the `handleCommand` chain, under the lock (a scan is about 117 one-byte reads; slow work under the lock has precedent, rough edge 18). Keep `test_input` as the single pre-lock exception with one comment line (it re-enters `handleCommand`). Delete `handleReadOnlyHardwareCommand`. Switch the WebUI `controlsCall({cmd:"get_controls"})` calls to `fetch("/api/config")`.
- effort: M. deliberate: yes. f5a61b8 message ("the read-only hardware commands run before the command lock"); `apertar-kb/working/controls/design-controls.md:112`, `:644-650` (the lock was weighed, `/api/config` was not).

### App-4-F2 [mismatch, major] Storage pre-roll worker starts and finishes a camera take outside handleCommand
- where: `src/ApertarCoreApp.cpp:11254-11275@cinemate-port`; `src/ApertarCoreApp.cpp:11297@cinemate-port`; `src/ApertarCoreApp.cpp:11121-11144@cinemate-port`
- port way: `runStoragePrerollOnce`, on a worker thread, takes `commandMutex_` itself, runs its own guard copy (`storagePrerollGuard` -> `storagepreroll::decideGuard`) and calls `camera_.startStoragePreroll`. It then watches the clock and calls `camera_.finishStoragePreroll` without any lock.
- Apertar way: C1-S01: every camera state change enters through `handleCommand`; "a worker that calls `camera_.setX()`" is the listed violation. The upstream idle timer is the shape for a timed trigger: it builds `ControlCommand enter_standby` and calls `handleCommand` (`src/ApertarCoreApp.cpp:7041-7047@upstream-1.6.0`). Timed camera work belongs to `CameraController` (`timelapseLoop`, `src/camera/CameraController.cpp:8447@upstream-1.6.0`). The port's own safety stop does the same: `record_stop` via `dispatchHardwareInputCommand` (`App:11107-11109@cinemate-port`).
- why it matters: a third and fourth take start/stop path besides the command chain, with a separate copy of the busy guards to keep in step by hand.
- rework: the worker keeps the request/coalesce and settle wait, then builds `ControlCommand storage_preroll` (trigger, seconds) and calls `handleCommand` as the idle timer does. The `storage_preroll` block relies on the head guards and checks only what is pre-roll-specific (camera ready, not still mode, raw format), then calls `camera_.startStoragePreroll`. The length and the finish move into `CameraController` (a timer thread like `timelapseLoop`), which emits the end through the existing event callback. Delete `storagePrerollGuard` and the guard fields the head guards already cover.
- effort: L. deliberate: yes. d44b177 message and comment `App:11113-11118`; no comparison with `handleCommand` found.

### App-4-F3 [removed-upstream-behaviour, minor] Record gate refuses a --media PATH that is not a mount point; the bypass is an env variable
- where: `src/ApertarCoreApp.cpp:11373-11374@cinemate-port`; `src/ApertarCoreApp.cpp:12596-12600@cinemate-port`; `src/ApertarCoreApp.cpp:11327-11337@cinemate-port`; `src/util/MediaProbe.hpp:105-123@cinemate-port`
- port way: `mediaGateError` returns "No media mounted at <root>." when `/proc/mounts` has no exact entry for the media root. `record_start`, `capture_photo` and `timelapse_start` are refused. Bypasses: `simulateCamera` and `APERTAR_MEDIA_REQUIRE_MOUNT=0`.
- Apertar way: `README.md:253@upstream-1.6.0` "`--media PATH` | Recording destination." Recording to any folder works; `CameraController` has no mount check. But upstream already treats an unmounted media root as "no media" for the speed test ("No media is currently mounted.", `src/ApertarCoreApp.cpp:8970-8974@upstream-1.6.0`) and the library (`App:7676@upstream-1.6.0`). Launch options are `Options` members with a `--flag` in `src/main.cpp:52-82@upstream-1.6.0` (C1-S24).
- why it matters: `apertar-core --media /home/pi/clips` now refuses to record where upstream recorded. The gate itself is worth keeping: without it a take under an empty `/media/RAW` lands on the SD card.
- rework: keep the gate. Replace `APERTAR_MEDIA_REQUIRE_MOUNT` with an `Options` member and a `main.cpp` flag (for example `--media-any-folder`), listed in the README options table next to `--media`; `mediaGateBypassed()` reads the member. Same member in `storagePrerollGuard` and `playbackHoldReason`.
- effort: S. deliberate: yes. The comment at `App:11327-11329` names the plain-directory case and gives the env bypass; 438a342 describes the gate.

### App-4-F4 [new-ground, major] Automatic storage pre-roll on by default: a raw take at every boot, card insert and format
- where: `src/util/StoragePreroll.hpp:98@cinemate-port`; `src/ApertarCoreApp.cpp:10945-10960@cinemate-port`; `src/ApertarCoreApp.cpp:12588-12592@cinemate-port`
- port way: `[media] preroll` defaults to on (`conf.automatic.value_or(true)`). The watcher requests a pre-roll at start, on a card insert and after a format. The default format is cDNG (`CC:5562`), so the raw-format guard does not skip it. While it runs, nine commands, `record_start` among them, answer "Storage pre-roll is running. One moment."
- Apertar way: no precedent.
- why it matters: an unmodified install gets a raw take written and deleted at every boot. Record, format, eject and standby are refused for its length, plus up to 2 min of trim wait and a 3 s settle.
- rework: default `[media] preroll=off` (`value_or(false)`). Keep the manual `storage_preroll` command and the switch.
- effort: S. deliberate: yes. d44b177: "on Core start, card insert, format and by hand (storage_preroll)".

### App-4-F5 [mismatch, minor] APERTAR_* environment knobs override saved settings and are re-read per call in App
- where: `src/ApertarCoreApp.cpp:11335@cinemate-port`; `:11379`; `:11402`; `:11154`; `:6402`; `:266-285@cinemate-port`
- port way: `APERTAR_MEDIA_REQUIRE_MOUNT` (every gate call), `APERTAR_MEDIA_MIN_FREE_MB` (every gate call), `APERTAR_MEDIA_TUNE`, `APERTAR_STORAGE_PREROLL`, `APERTAR_MEDIA_TRIM`, `APERTAR_CLIP_MERGE`, `APERTAR_CDNG_BUFFER`, `APERTAR_CDNG_FRAMES_PER_FOLDER`. Several beat the saved `[media]`/`[storage]` setting. 17 `getenv("APERTAR` lines in port App against 2 upstream.
- Apertar way: upstream App reads only `APERTAR_HARDWARE_CONFIG` (`App:4254`, `:4273@upstream-1.6.0`). Developer knobs exist, but in the owning subsystem, read once into a `static const` and overriding no saved setting: `src/lossydng/LossyDngEncoder.cpp:98-105`, `:325@upstream-1.6.0`. Launch options are `Options` members (C1-S24).
- why it matters: hidden switches that silently override what the user saved, invisible in both UIs; left over from A/B experiments.
- rework: delete the env reads that override a saved setting (`APERTAR_STORAGE_PREROLL`, `APERTAR_MEDIA_TRIM`, `APERTAR_CLIP_MERGE`, `APERTAR_CDNG_BUFFER`); each switch keeps one home (`[media] preroll`, `[storage] clip_merge`, the persisted `mediaTrimSetting_`, `[storage] buffer`). `APERTAR_MEDIA_MIN_FREE_MB` becomes a `[media] min_free_mb` key or a fixed constant. `APERTAR_MEDIA_REQUIRE_MOUNT` goes with F3; `APERTAR_MEDIA_TUNE` with F17. A knob that must stay for bench work is read once into a `static const` in its owner, as `LossyDngEncoder.cpp` does.
- effort: M. deliberate: yes. d44b177 and ba0658d messages name the env vars as features.

### App-4-F6 [mismatch, minor] Cross-part state in header-level function-static singletons
- where: `src/util/BufferBudget.hpp:231-234@cinemate-port`; `src/util/BufferBudget.hpp:330-333@cinemate-port`; `src/util/StoragePreroll.hpp:234-249@cinemate-port`; `src/hardware/HardwareConfigStore.cpp:499-501@cinemate-port`
- port way: `safetyStopState()` (written by the write queue in CC, read in App: 10 + 10 uses), `configStore()` (App 20 uses, `Mpu6050RecordingSession.cpp` 2), `prerollState()`/`prerollActive()`/`setPrerollLast` and `clipMergeRequest()` (App only) are `inline` function-static globals in headers, reachable from any file.
- Apertar way: upstream uses function-static singletons too, but file-local in the owner's .cpp: `captureSettingsPersister()` (`src/camera/CameraController.cpp:885-889@upstream-1.6.0`), `LossyDngDiskWriter::instance()` (`src/lossydng/LossyDngEncoder.cpp:114-118@upstream-1.6.0`). State shared between parts is a member of App (`src/ApertarCoreApp.hpp:110-176@upstream-1.6.0`, C1-S18) and crosses parts through constructor callbacks (C1-S19). The port's own `playbackYield()` (`App:6342`, file-local) conforms.
- why it matters: the original developer cannot see from a class which part writes the safety-stop or pre-roll state, or where the hardware store lives.
- rework: safety-stop state becomes a member group of `CameraController` (the write queue sets it), read by App through a getter or the existing event callback. The hardware config store becomes an App member passed by reference to the classes that need it. Pre-roll state and the clip-merge switch become App members (or file-local in App). Keep the pure functions in the headers.
- effort: L. deliberate: unknown.

### App-4-F7 [mismatch, minor] Controls worker polls the hardware file every 2 s (a file watcher in Core)
- where: `src/ApertarCoreApp.cpp:12242-12268@cinemate-port`
- port way: `runControlsWorker` wakes on a save or every 2 s, compares the file text with the applied text, and applies edits made over ssh. The same 2 s turn retries an apply that a take deferred.
- Apertar way: C1-S08 names "a file watcher in Core" as a violation. Upstream applies by restart: `src/web/WebControlPage.cpp:3869@upstream-1.6.0` "Hardware, input, display, and sensor changes may need ApertarCore or the UI restarted".
- why it matters: a background poll upstream does not have. The KB contradicts itself: `design-controls.md:93-95` says ssh hand edits are "never applied on the side", `decisions.md:47` says outside edits are polled every 2 s.
- rework: keep the worker (the deadlock reason is sound). Wake it on `set_controls`, `POST /api/config` and at the end of a take (where `syncRecordingTracking(false)` runs), and drop the 2 s timeout. An ssh edit applies at the next save or restart, as upstream. Fix the design page to match.
- effort: S. deliberate: yes. `apertar-kb/working/controls/decisions.md:47`; `design-controls.md:93-98`.

### App-4-F8 [slop, major] Ticket numbers, critic ids, KB paths, banners and about 140 comment lines in the slice
- where: `src/ApertarCoreApp.cpp:10870@cinemate-port`; `:10897`; `:10927`; `:11113`; `:11339`; `:11377`; `:11433`; `:11620-11627`; `:11904`; `:12572-12573`; `:11508-11512@cinemate-port`
- port way: comments cite T39/T40/T42/T43/T47/T48, "critic S11", "critic Y11", "design §2.7", "kb working/dng-chain, R4", "probe-exfat-dir.md" and "the NVMe campaign"; `// ----` banners; install instructions inside a log line. 140 full-line comments in `App:10860-12668` (about 1800 lines).
- Apertar way: C1-I14: comments are rare and state a hazard or a reason; upstream App has 10 full-line comments in 10 800 lines. A ticket number or a banner is the listed violation.
- why it matters: the references mean nothing to the original developer, and the volume reads as narration.
- rework: delete ticket, critic, KB and file references and the banners. Keep one hazard sentence per worker (why a thread, why not under the lock). Move measurements to the KB and install steps to the README.
- effort: M. deliberate: no.

### App-4-F9 [mismatch, minor] Buffer level pushed by an App polling thread instead of emitted by the camera
- where: `src/ApertarCoreApp.cpp:10986-11052@cinemate-port`
- port way: `runBufferEvents` polls `camera_.frameBufferStatus()` and nine global flags every 250 ms (1 s idle) and publishes `buffer`.
- Apertar way: the producer emits on change through its callback: `emitMediaWriteState` (`src/camera/CameraController.cpp:7551-7563@upstream-1.6.0`, "Serialize edges"), `audio_level` from the recorder's level callback (`src/ApertarCoreApp.cpp:8380-8384@upstream-1.6.0`). C1-S12 builds events at the emit site.
- why it matters: an extra thread and a poll loop where upstream emits on change.
- rework: the write queue emits `buffer` on a level change through the existing camera event callback, rate-limited in the queue and never under the controller mutex (as `emitMediaWriteState`). Pre-roll and safety-stop flags travel in the events that change them or in `get_state`. Delete `runBufferEvents`.
- effort: M. deliberate: yes. Comment `App:10986-10992`.

### App-4-F10 [bug, minor] Two identical buffer events in one loop turn
- where: `src/ApertarCoreApp.cpp:11021-11039@cinemate-port`
- port way: the first branch publishes on any setting/pre-roll/dropped-frame change without updating `sentUsed`/`sentCapacity`; the busy branch then publishes again because `buffer.used != sentUsed`.
- Apertar way: no precedent.
- why it matters: during a take, a dropped frame and a level change in the same 250 ms turn send two identical events to every socket client.
- rework: publish once per turn (set `sentUsed`/`sentCapacity`/`open` in the first branch, or merge the branches). Goes away with F9.
- effort: S. deliberate: no.

### App-4-F11 [mismatch, minor] Media tuning helper runs `sudo -n` without `/usr/bin/timeout` or absolute paths, on the watcher thread
- where: `src/ApertarCoreApp.cpp:11422-11425@cinemate-port`
- port way: `"sudo -n " + helper + " apply " + shellQuote(rootDisk) ...` through `runShellCommand`, no timeout, called from the media watcher (`App:10941`). Runs only when kernel tuning is enabled (default off).
- Apertar way: upstream's libexec root helpers are called as `"/usr/bin/timeout 6s /usr/bin/sudo -n /usr/local/libexec/apertar-standby-usb "` with "Fixed executable and arguments only" (`src/ApertarCoreApp.cpp:1541-1550@upstream-1.6.0`). Upstream's other `sudo -n` calls (hwclock, systemctl, mount) are bare, so the libexec shape is the one that applies.
- why it matters: a hung helper stops the media watcher, and yank detection with it.
- rework: `/usr/bin/timeout 6s /usr/bin/sudo -n /usr/local/libexec/apertar-media-tune apply|restore <disk> <class> <fs>`.
- effort: S. deliberate: no.

### App-4-F12 [duplication, minor] Five idle predicates that drift, three identical ms clocks
- where: `src/ApertarCoreApp.cpp:11121@cinemate-port`; `:11341`; `:11471`; `:11697`; `:12237`; clocks `:6337`, `:6394`, `:11630@cinemate-port`
- port way: `storagePrerollGuard`, `playbackHoldReason`, `mediaTrimMayRun`, `clipMergeMayRun` and `recordingGateActive` each list a different subset of recording/sound/timelapse/writes/delete/preroll/speed test/standby/safety-stop (`mediaTrimMayRun` ignores the safety-stop flush that `clipMergeMayRun` checks). `playbackNowMs`, `trimNowMs`, `clipMergeNowMs` are the same steady_clock ms function.
- Apertar way: busy checks written once as `||` lists at the head of `handleCommand` (`src/ApertarCoreApp.cpp:9095-9110@upstream-1.6.0`, C1-S04). One clock idiom inline: `steady_clock::now().time_since_epoch()` (`App:9112-9114@upstream-1.6.0`).
- why it matters: the subsets drift; a new busy state has to be added in five places.
- rework: one `bool mediaIdle(std::string *why) const` for trim, merge and pre-roll; `playbackHoldReason` and `recordingGateActive` keep their own meaning but call it where they overlap. One ms clock helper. `monotonicMicros` stays (compared with systemd monotonic timestamps, `App:12343`).
- effort: M. deliberate: no.

### App-4-F13 [duplication, minor] [cfexpress_hat] parsed by two parsers with defaults in two places; get_controls parses the file 8 times
- where: `src/ApertarCoreApp.cpp:5298@cinemate-port`; `src/ApertarCoreApp.cpp:12087-12091@cinemate-port`; `src/ApertarCoreApp.cpp:12439-12447@cinemate-port`
- port way: `loadCfeHatConfig` is a hand parser; `cfeHatPeripheralJson` goes through `hwconf` with literal defaults "10" and "0x34" (also in `CfeHat.hpp:20`). `hwconf::parse(info.text)` is called 8 times in one reply.
- Apertar way: C1-S07: one owner per section of `apertar-hardware.conf`.
- why it matters: the defaults can diverge; the work is wasted.
- rework: one `CfeHatConfig` parser used by both. Parse the document once into a local in the builder.
- effort: S. deliberate: no.

### App-4-F15 [bug, minor] record_start may wait about 4.5 s under the command lock for a trim and a rename
- where: `src/ApertarCoreApp.cpp:12614-12619@cinemate-port`; `src/ApertarCoreApp.cpp:11941-11964@cinemate-port`; `src/ApertarCoreApp.cpp:11905-11916@cinemate-port`
- port way: `waitForMediaTrim` waits 2 s, then SIGTERM + 1 s, then SIGKILL + 0.5 s; `waitForClipMerge` waits up to 1 s. Both run under `commandMutex_` before a take.
- Apertar way: rough edge 18 accepts slow work under the lock (format, gyro calibration), but upstream `record_start` does not wait (`src/ApertarCoreApp.cpp:9091-9110@upstream-1.6.0`).
- why it matters: the record button can lag by seconds after an idle trim started.
- rework: on a take command, SIGTERM the trim at once with no 2 s grace (fstrim dies on the fatal signal between ranges). Keep the single-rename wait.
- effort: S. deliberate: yes. Comment `App:11938-11940`; d44b177.

### App-4-F16 [slop, minor] Media watcher runs playback chores; hold reason round-trips string to enum
- where: `src/ApertarCoreApp.cpp:10970-10979@cinemate-port`; `src/ApertarCoreApp.cpp:11341-11357@cinemate-port`
- port way: the watcher renews the playback yield window and calls `trimIdleFrameSlots` ("no new thread"). `playbackHoldReason` returns a string, which five `if (hold == "...")` lines map back to an enum.
- Apertar way: no precedent.
- why it matters: unrelated jobs hidden in the media thread, plus a needless conversion.
- rework: return `playback::Hold`; call `holdName` only at the JSON edge. Move the slot trim to the playback call sites.
- effort: S. deliberate: no.

### App-4-F17 [mismatch, minor] Kernel tuning switch read from a fourth config file ~/apertar-media-tune.conf
- where: `src/ApertarCoreApp.cpp:11400-11408@cinemate-port`; `src/util/MediaTune.hpp:8-28@cinemate-port`
- port way: `applyMediaTuning` reads `kernel_tune` through `loadMediaTuneLogged` from `/home/pi/apertar-media-tune.conf` with a `/run/apertar-media/` override. The same file holds seven more write-path knobs read by CC (`CC:1467`, `:4364`) and `CdngEncoder.cpp:91`.
- Apertar way: three stores only: `camera_settings.conf`, `UI.conf`, `apertar-hardware.conf` (C1-S07; BRIEF).
- why it matters: a fourth config file with a hard-coded home directory.
- rework (this unit): add `[media] kernel_tune` to `apertar-hardware.conf`, parsed once by its owner, and stop reading the tune file in App. The tune file as a whole is reviewed with the write-path unit.
- effort: M. deliberate: yes. 2edc6d0 argues for the file ("one readable file next to the hardware conf ... test nights need an override").

### App-4-F19 [pi-compat, nit] Config > Hardware shows a CFexpress hat row on boards without one
- where: `src/ApertarCoreApp.cpp:12085-12123@cinemate-port`
- port way: `cfeHatPeripheralJson` probes bus 10 / 0x34 even when the file has no `[cfexpress_hat]` section, and Config lists every peripheral.
- Apertar way: upstream also assumes the hat on bus 10 / 0x34 and the Pi 5 PCIe controller (`src/ApertarCoreApp.cpp:3391-3395`, `:4303-4306@upstream-1.6.0`), but shows no status row for it.
- why it matters: on a Pi 4 or CM4 the row says "Bus 10 does not exist on this Pi." for an accessory the user does not have.
- rework: emit the hat row only when the section exists (`in_file` is already computed).
- effort: S. deliberate: no.

### App-4-F20 [slop, nit] Wording and shape nits
- where: `src/ApertarCoreApp.cpp:12493@cinemate-port`; `:11372`; `:12540-12541`; `:11054`; `:12425-12426@cinemate-port`
- port way: "scan_i2c needs bus= (...)"; "Media is not answering (errno N)"; the reply body is built by stripping braces with `substr`; `stopMediaWatcher` stops six threads; the "read-only" `get_controls` writes `controlsErrors_`/`controlsWarnings_`.
- Apertar way: C1-I07: "<name> requires <field>." (`"set_iso requires value."`, `src/ApertarCoreApp.cpp:9245@upstream-1.6.0`), no developer detail in operator sentences.
- why it matters: small departures from house style.
- rework: "scan_i2c requires bus."; drop the errno from the sentence (log it); have `catalogJson` return members only; rename `stopMediaWatcher` to `stopMediaWorkers`; stop writing counters in `get_controls`.
- effort: S. deliberate: no.
