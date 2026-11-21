# Review: Media-buffer-split (stage 2)

Refs: port = `cinemate-port` `01f170c` (`/home/user/Apertar-Core`), upstream = `upstream-1.6.0` `35dbe67`
(`/home/user/wt/core-upstream`). `App` = `src/ApertarCoreApp.cpp`, `CC` = `src/camera/CameraController.cpp`.
Rule ids from `raw/conv-core-camera.md` (S*, I*, N*), `raw/conv-core-command-plane.md` (C1-*),
`raw/conv-platform-build.md` (S7..S15, N7), `raw/conv-hardware-config.md` (HW-*), `raw/conv-style-commits.md` (C8-*).
`apertar-conventions.md` does not exist yet. Inventory: `raw/inv-Media-buffer-split.md`.

Scope files read whole: `src/util/BufferBudget.hpp`, `src/util/StoragePreroll.hpp`, `src/cdng/FramePath.hpp`,
`src/cdng/ClipMerge.hpp`, `scripts/apertar-media-trim`, `config/apertar-media-trim.sudoers`,
`tools/media_trim_test.sh`; `tools/flatten_clip.py` and the `*_test.cpp` heads. Call sites read in App and CC
(line numbers below).

## Verdict in one paragraph

The pure headers are in the Apertar shape (header-only, std-only, inline free functions, S4). What is foreign is
the plumbing around them: (1) recording and storage behaviour is kept in `apertar-hardware.conf` and read by the
camera side, where upstream keeps such settings in `camera_settings.conf` and the camera never reads the hardware
file; (2) cross-thread state lives in process-wide free-function statics and a global `std::function` hook,
where upstream uses a latch object owned by the controller and passed to the queue; (3) two polling threads do
what upstream does in the 1 Hz `wait()` loop; (4) the root helper is a shell script in Core with a path argument
and a path-only sudoers rule, where upstream calls simple tools with `sudo -n` directly or uses a C++ helper with
literal verbs in the UI repo. The trim and pre-roll are also on by default, which changes stock behaviour.
No socket or HTTP change breaks the unmodified original UI (all additions, flat JSON).

## Findings

| Id | Sev | Cat | Title |
| --- | --- | --- | --- |
| F1 | blocker | mismatch | Recording/storage settings in `apertar-hardware.conf`, read by `CameraController` |
| F2 | major | mismatch | Cross-thread state through free-function statics and a global hook |
| F3 | major | mismatch | Two polling threads (buffer events, safety stop) instead of the 1 Hz `wait()` loop |
| F4 | major | mismatch / security | Root helper `scripts/apertar-media-trim` + path-only sudoers in Core |
| F5 | major | bug (probable) | Ending a trim kills `sudo`/`sh`, not `fstrim` |
| F6 | major | removed-upstream-behaviour | Trim and automatic pre-roll on by default |
| F7 | minor | mismatch | `record_start` and media actions wait up to ~3.5 s under `commandMutex_` |
| F8 | minor | slop | Comments and README narrate history, cite KB paths, other projects and commits |
| F9 | minor | slop | Env override for every file key, `*_env` flags in state, speculative parameter |
| F10 | minor | duplication | Frame-number rule in three copies; three copied `store.edit` blocks |
| F11 | minor | new-ground | Host tests in `tools/`, not in the build |
| F12 | minor | new-ground | `GET /api/buffer` polled at 4 Hz beside `/api/state` |
| F13 | nit | mismatch | Namespace names and file placement |
| F14 | nit | new-ground | `tools/flatten_clip.py` (keep, trim) |

### F1 blocker, mismatch: settings in the hardware file, read by the camera

Port:
- `CC:2986-3006` `loadBufferConf()` opens `$APERTAR_HARDWARE_CONFIG` / `/home/pi/apertar-hardware.conf` /
  `/boot/firmware/...` / `/boot/...` and parses `[storage]` at every take start (`planQueueBuffer`, `CC:5502`
  `const bufferbudget::BufferConf conf = loadBufferConf();`). Confirmed.
- Keys `[storage] buffer`, `buffer_ram_fraction`, `buffer_ram_floor_mb`, `buffer_ram_max_fraction`,
  `buffer_stop_percent`, `frames_per_folder`, `clip_merge`, `[media] preroll`, `preroll_seconds`
  (`BufferBudget.hpp:97-107`, `StoragePreroll.hpp:22-27`). Commands `set_buffer_mode`, `set_frames_per_folder`,
  `set_clip_merge`, `set_storage_preroll` write them through `hardware::configStore().edit` (`App:12829-12925`).
- Same unit, other choice: `media_trim` is a `CaptureSettings` field persisted in `camera_settings.conf`
  (`CC:889`, `:976`, inventory 3.5). So the port uses both stores for the same kind of switch.

Upstream:
- S22 (always): "The camera side never reads `apertar-hardware.conf`". `grep -n "apertar-hardware\|APERTAR_HARDWARE_CONFIG" src/camera/CameraController.cpp` @upstream = 0 hits (confirmed).
- S20 (always): camera settings persist only in `camera_settings.conf`, written by Core. C1-S07: each store has
  one owner.
- N11 (always), I9, C1-I22: internal tuning is an `APERTAR_<AREA>_<KNOB>` env var read where used, not in
  operator-edited files or the README. Upstream queue knob: `CC:3328-3329` @upstream
  `maxQueuedFrames_ = unsignedEnvValue("APERTAR_CDNG_QUEUE_FRAMES", defaultQueueFrames, 4, 64);`.
- S19: per-take inputs that are not camera settings travel as option structs built by App
  (`Types.hpp:184-201` @upstream, `AudioRecordingOptions`, `GyroRecordingOptions`).

Rework:
1. `buffer` (frames/ram) and `frames_per_folder`: `CaptureSettings` fields `bufferMode` (enum + `toString`,
   I11) and `framesPerFolder`, global like timecode (N14 carry-over list `CC:7945-7951`), loader branch
   (I15), the three field lists (I13 / C1-S13), `CameraController::setBufferMode` / `setFramesPerFolder`
   (S7, I1, through `applySettingsLocked`, refused while recording per N5 unless "next take" is wanted, then
   say so), commands reply `settingsBody` (C1-I01).
2. `clip_merge` and automatic `preroll`: same route as `media_trim` already takes in this unit.
3. `buffer_ram_fraction`, `buffer_ram_floor_mb`, `buffer_ram_max_fraction`, `buffer_stop_percent`,
   `preroll_seconds`: env only (`APERTAR_CDNG_QUEUE_RAM_*` and `APERTAR_CDNG_BUFFER_STOP_PERCENT` already
   exist), read at the point of use, not in README.
4. Delete `loadBufferConf`, `BufferConf`, `parseBufferConf`, `bufferConfProblem`, `PrerollConf`,
   `parsePrerollConf`, `prerollConfProblem`, `refreshBufferRequest`, the `[storage]`/`[media]` rules in
   `HardwareConfigText.hpp:802/:811`, the `base`/`by` revision handling of the four commands, and the
   `buffer_*`/`frames_per_folder`/`clip_merge`/`preroll` template lines.
Effort L. Risk: the WebUI and touch UI read `buffer_setting`, `frames_per_folder`, `clip_merge_enabled`,
`storage_preroll_auto` from state; keep those names in `settingsBody` and the UI keeps working.
Deliberate: no evidence (KB `working/drop-frames/README.md:73` states the choice, does not weigh it).

### F2 major, mismatch: free-function statics as cross-thread state

Port: `BufferBudget.hpp:224-334` `safetyStopState()`, `flushAbortMutex()`/`flushAbortFunction()`,
`safetyStopHook()` (global `std::function`), `bufferSettingStorage()`/`bufferSettingMutex()`,
`framesPerFolderRequest()`, `clipMergeRequest()`; `StoragePreroll.hpp:224-271` `prerollState()`.
Writers/readers: `CC:4629` `bufferbudget::flushAbortFunction() = [this] { return abortSafetyFlush(); };`,
`CC:5018` hook called under the queue mutex, `App:7988` sets the hook in the constructor body, `App:252-285`
reads all of them.

Upstream: the same job (queue signals something clip-scoped to Core) is `RecordingDropWarning`
(`src/util/RecordingDropWarning.hpp:10-27` @upstream): a latch class with a constructor-injected callback, a
member of the controller (`CameraController.hpp:113` @upstream `RecordingDropWarning recordingDropWarning_;`),
passed by pointer to the queue (`CC:3251` @upstream `explicit DngRecordingQueue(RecordingDropWarning *warning = nullptr)`).
`RecordingFailure` (`src/util/RecordingFailure.hpp`) is a member of each recorder (`CC:3901`, `:4973` @upstream).
I17 covers function-local statics for one-off constant values (caches), not shared mutable state. C1-S19 / S25:
parts talk to App only through constructor callbacks; no global.

Rework: `src/util/RecordingSafetyStop.hpp` shaped like `RecordingDropWarning` (atomics `active`,
`stopPercent`, `flushDiscarded`, a `changed` callback); member of `CameraController`, pointer into
`DngRecordingQueue`'s constructor; `CameraController::bufferStatus()` / `abortSafetyStopFlush()` public methods
(lock only the queue's mutex, comment why). Pre-roll state (`active`, `fps`, `last`) as App members in a state
group (C1-S18, `std::atomic<T> name_{}`), not a global. `framesPerFolderRequest`, `clipMergeRequest`,
`bufferSettingSnapshot` disappear with F1 (they become settings). Effort M.

### F3 major, mismatch: polling threads

Port: `runBufferEvents` (`App:10993`, 250 ms / 1 s loop) and `runBufferSafetyStop` (`App:11083`, 100 ms backstop
wait, then `dispatchHardwareInputCommand(record_stop)`).
Upstream: C1-S21 (once, but the only precedent): periodic supervision is the 1 Hz loop of `wait()`
(`App:7021-7053` @upstream), which checks `camera_.checkRecordingFailure()` and dispatches `enter_standby` with
`handleCommand(command)`; C1-N05: failure checked before every command and once a second; C1-S12 events built at
the emit site. Rework: check the safety latch in `wait()` next to `checkRecordingFailure` and at the top of
`handleCommand` (same line `App:12584` already does it for failure), dispatch `record_stop` there; publish the
`buffer` event from the latch's `changed` callback for flag flips and from `wait()` for the level. Delete both
threads and their 10 members. Risk: 1 s reaction instead of 100 ms; at 90 % of a GiB-sized budget the 10 % headroom
is several seconds of net fill, but say so in the commit and test with `buffer_stop_percent` low. If 4 Hz level
updates are wanted for the bar, argue it as new ground (F12). Effort M.

### F4 major, mismatch + security: root helper and sudoers

Port: `scripts/apertar-media-trim` (POSIX sh, 90 lines, takes the mount point as argument),
`config/apertar-media-trim.sudoers:4` `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-media-trim` (any
argument), `tools/media_trim_test.sh`, `runTrimHelperProcess` (`App:6415-6447`, fork + `execl("/usr/bin/sudo",
"sudo", "-n", helper, mountPoint)`), README install block (`README.md:303-313`).

Upstream:
- S8 (usually): a simple privileged system tool is called directly with `sudo -n` from Core and relies on the
  image's passwordless sudo: `App:3609` @upstream `runShellCommand("sudo -n mkdir -p " + shellQuote(mountPath), ...)`,
  `:3623-3632` `sudo -n mount ... shellQuote(mountPath)`, `:3810-3816` mkfs, `:3353` `sudo -n blockdev --flushbufs`.
  `fstrim` on `options_.mediaRoot` is exactly this kind.
- S7 / N7 (always for helpers): a root helper is a single-file C++ program in `UI/src/`, sudoers in
  `UI/systemd/`, literal verbs only: `App:1543-1544` @upstream "Fixed executable and arguments only; never accept
  paths from WebUI/config." `/usr/bin/timeout 6s /usr/bin/sudo -n /usr/local/libexec/apertar-standby-usb ` + action.
- C1-S29 / S9: Core ships no helper scripts; `scripts/` holds only the start script, `config/` only the systemd
  drop-in (`git ls-files scripts config` @upstream = 2 files, confirmed).

Rework: delete the script, the sudoers file, `media_trim_test.sh` and the README install block. Run
`/usr/bin/timeout 20s /usr/bin/sudo -n /usr/sbin/fstrim -v <shellQuote(mediaRoot)>` from the trim worker (keep a
fork/exec so the pid of `timeout`, owned by `pi`, can be signalled; see F5). Do the discard check in Core
unprivileged (read `/sys/block/<disk>/queue/discard_max_bytes`; `mountIdForPath` already exists). Map exit
codes to one `ApertarCore media: trim ...` line; on a missing sudo rule say "Trim needs sudo permission." (C1-N13).
Security now: the sudoers rule lets `pi` run a root shell script with any argument; the script validates
(under `/media/`, charset, canonical, mount point), so the risk is low, but it is a wider grant than upstream's
literal-verb rules. Effort M.

### F5 major, bug (probable): ending a trim does not end fstrim

`waitForMediaTrim` (`App:11955-11960`) sends SIGTERM, then SIGKILL, to the pid of `sudo`. sudo relays SIGTERM to
the command, which is `sh` running the helper; `sh` dies, its foreground child `timeout 20 /usr/sbin/fstrim`
(`scripts/apertar-media-trim:75`) gets no signal and runs on. SIGKILL cannot be relayed at all. Failing input:
a trim that runs longer than 2 s (a big drive after a format), then `record_start`: Core logs "ended a trim that
ran longer than 2 s" and starts the take while `fstrim` still holds the filesystem for up to 20 s, which is what
the wait was meant to prevent. Probable, not run (no Pi). Settle on the Pi: start a trim, call
`kill -TERM <sudo pid>`, then `pgrep -a fstrim`. Fix: F4 rework (signal `timeout`), or at least
`exec timeout 20 /usr/sbin/fstrim ...` in the script.

### F6 major, removed-upstream-behaviour: trim and automatic pre-roll on by default

Port: `media_trim` default true (inventory 3.5, `CaptureSettings`), `[media] preroll` default on
(`StoragePreroll.hpp:98` `return conf.automatic.value_or(true);`).
Effect on stock behaviour: (a) after any delete of >= 1 GiB, at every mount and after a format the drive is
trimmed, so deleted takes cannot be recovered (KB `working/drop-frames/README.md:69` "Side effect: no
undelete"); upstream never discards. (b) At Core start, every card insert and every format, a 2 s raw take runs
and `record_start`, `capture_photo`, `timelapse_start`, media actions and standby are refused with "Storage
pre-roll is running. One moment." (`App:12588-12592`), after a 3 s settle and a wait for the mount trim (up to
120 s per inventory). Upstream: camera can record as soon as Ready; media is never touched without an operator
action. Precedent in the port itself: `apertar-media-tune` was made opt-in (`APERTAR_MEDIA_TUNE=1`, `e9dd6b2`,
KB `drop-frames/README.md:259`, `:276`).
Rework: default off for both (`CaptureSettings{}.mediaTrimEnabled = false`, pre-roll auto off), switch in the WebUI
as now. Effort S. Deliberate: yes for trim being on (KB states it), no evidence that the default was weighed
against stock behaviour.

### F7 minor, mismatch: commands wait for trim and merge under the command lock

`App:12610-12614`: `record_start`, `capture_photo`, `timelapse_start`, `format/eject/mount`, speed test call
`waitForMediaTrim(name, 5000)` and `waitForClipMerge(name, 5000)`; the trim wait is up to 2 s + 1 s + 0.5 s
(`App:11950-11961`), inside `handleCommand` under `commandMutex_` (C1-S03), so every client stalls meanwhile.
Upstream refuses instead of waiting: `App:9108-9110` @upstream "Wait for the media speed test to finish first."
(C1-N04, C1-S04). The port chose "record always starts" (KB `drop-frames/README.md:69`): deliberate. Keep the
behaviour if the owner wants it, but make the merge yield (it already pauses between renames) and the trim end
through `timeout` (F4) so the wait is short; document the choice for the original developer.

### F8 minor, slop: narrative and internal references

| Where | Text |
| --- | --- |
| `src/cdng/FramePath.hpp:10-11` | "(apertar-kb working/drop-frames/nvme-campaign/probe-exfat-dir.md)" |
| `src/util/BufferBudget.hpp:6-7` | "follow cinepi-raw's DNG encoder (cinepi/dng_encoder.cpp: RAM_FRACTION, ram_cv_.wait)" |
| `App:11626-11627` | "(probe-exfat-dir.md: ~5 min ...)", "(the NVMe campaign does, for its A/B)" |
| `App:11114` | "CineMate's storage warm-up" |
| `CC:5546` | "the rule since db17860" |
| `README.md:329`, `:333`, `:337-356` | "measured 2026-11-08, Apertar knowledge base `working/...`", "local branch `clip-split`", section "Write-path knobs for A/B tests" (env table) |
Rules: C8-S9 (no other projects' commits, tickets), I19 / C1-I14 (comments are short why-notes), C8-S12 (no env-knob
tables in README). Rework: keep one-line why-notes ("exFAT walks every entry of the target folder on create"),
drop sources, dates, KB paths, campaign names; remove the env table from README. Effort S.

### F9 minor, slop: override layers and speculative generality

- Every file key has an env twin that wins (`requestedBufferMode`, `requestedFramesPerFolder`,
  `requestedClipMerge`, `automaticEnabled`, `effectiveStopPercent`), and state carries which one won
  (`frames_per_folder_env`, `clip_merge_env_off`, `storage_preroll_auto_env`, `media_trim_env_off`,
  `App:262-268`). Upstream env knobs are read where used and are not surfaced to the UI (I9, C1-I22). With F1 the
  operator switch is a setting and the env var either goes or stays as a bench knob not shown in state.
- `StoragePreroll.hpp:148-150` `decideGuard(const GuardInputs &in, Trigger)`: unused parameter "so a future rule
  can differ (and the tests name it)". Remove the parameter.
- `refreshBufferRequest` (`App:278-285`) parses the same text three times.
- `ClipMerge.hpp:219-220` `++remaining; ++remaining;` with a comment that explains the second as "every later
  one": write `remaining += 2` or a bool `kept`.
Effort S.

### F10 minor, duplication

- Frame-number rule: `ClipMerge.hpp:142-151` `detail::frameNumber` ("Same rule as playback/ClipFrames.hpp
  frameNumberFromName"), `ClipFrames.hpp` `frameNumberFromName`, `tools/flatten_clip.py:47-57`. Use the ClipFrames
  function from ClipMerge (one C++ copy); the Python copy is acceptable for a desk tool.
- Three ~20-line `store.edit` blocks (`App:12829-12850`, `:12857-12895`, `:12900-12925`). C1-I17: a shape repeated
  in one function becomes a local lambda. Goes away with F1.
- `parseBufferConf` / `parsePrerollConf` repeat the `trim`/`lower` lambdas; the port also has `hwconf::Document`.
  Upstream copies parsers per owner (HW-S2), so the copy itself is in style; it goes away with F1.

### F11 minor, new-ground: host tests

`tools/buffer_budget_test.cpp`, `storage_preroll_test.cpp`, `storage_buffer_conf_test.cpp`, `clip_merge_test.cpp`,
`frame_path_test.cpp`, `media_trim_test.sh`: standalone, own `check()` each, not in CMake (`grep -n
"_test\|add_test" CMakeLists.txt` = 0 hits, confirmed). Upstream S24 / S13: no tests in Core. New ground, not a
mismatch. Verdict keep (they cost the build nothing, they test the only parts that run off the Pi). Simplify:
`storage_buffer_conf_test.cpp` and `media_trim_test.sh` go with F1/F4; one README line under For Developers lists
the remaining ones with one compile line (README:335 says `-std=c++17`, the test heads say `-std=c++20`: pick one).

### F12 minor, new-ground: `GET /api/buffer`

`App:8419`, lock-free, polled about 4 Hz by the WebUI while the bar or pre-roll pill shows
(`WebControlPage.cpp:16497`). Upstream: WebUI polls `/api/state` at 1 Hz, no push (C1-S26); extra GET routes that
only read are allowed (C1-S09). The same members are already in `/api/state`. Verdict simplify: drop the route if
1 Hz is enough for the bar; else keep it and state the reason (bar smoothness during a take) in the handoff.

### F13 nit, mismatch: names and placement

Nested namespaces `apertar::bufferbudget`, `storagepreroll`, `clipmerge`, `framepath`; upstream nested names are
camelCase or one word: `apertar::settingsFile` (`SettingsFile.hpp:17`), `apertar::tuning`, `apertar::hardware`
(I22). `src/util/` upstream holds clip latches and the settings writer (S6); C1-S06 puts subsystem logic next to
its owner. Move `BufferBudget.hpp` next to the queue (`src/camera/` or `src/cdng/`), `StoragePreroll.hpp` next to
App (`src/`); rename namespaces `bufferBudget`, `storagePreroll`, `clipMerge`, `framePath` or fold the few
functions into `namespace apertar`.

### F14 nit, new-ground: `tools/flatten_clip.py`

284 lines, stdlib, `python3 -I`. Upstream has no Python tools in Core (C1-S29); the Mac-side flatten has no
other home and is useful when a card leaves the camera before the merge worker ran. Verdict keep; drop the
`statistics` timing report and keep `--unflatten` only if the tests use it.

## Protocol

No break found. New commands, a new `buffer` event, new flat scalar members in `get_state` / `/api/state`, a new
read-only route. `record_stop` during a pre-roll replies ok with `storage_preroll_stopped:true`; the original UI
reads `ok` only. The `recording=false` event comes before the drain on a safety stop (`CC:12442`): the original UI
shows READY earlier, harmless. Flat JSON kept (C1-I08, C1-I09).

## Pi compatibility

Nothing board-specific in scope. `ram` mode refuses itself below the frames-mode bytes, so 1-4 GB boards stay on
frames (`BufferBudget.hpp:352-366`). `RENAME_NOREPLACE` is supported by exfat, vfat and ntfs3 on Pi kernels; a
filesystem that returns EINVAL makes the merge stop with "rename failed" (no runtime fallback; compile-time only,
`App` `renameNoReplace`), acceptable. User `pi` in sudoers matches upstream S11.

## Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `bufferbudget` + `BufferPlan`/`planBuffer` | simplify | Keep the pure budget maths (S4, N2 kept: full queue still drops); strip the parsers and globals (F1, F2) |
| `BufferConf` / `parseBufferConf` | rework-to-upstream-pattern | Settings to `camera_settings.conf`, tuning to env (S20, S22, N11) |
| `loadBufferConf()` in CC | rework-to-upstream-pattern | The camera never reads the hardware file (S22); delete |
| Free-function atomics | rework-to-upstream-pattern | Latch member like `RecordingDropWarning`, App members (F2) |
| `safetyStopHook()` global `std::function` | rework-to-upstream-pattern | Constructor-injected callback / latch pointer (C1-S19, S25) |
| `storagepreroll` | simplify | Keep `decideGuard` (drop unused `Trigger`), `triggerForMountChange`, `measuredFps`, `lastOk`; drop parser and `PrerollState` global |
| `framepath` | keep | Small, pure, measured reason, default off, frame names unchanged |
| `clipmerge` | keep | Pure plan, crash-safe order; share the frame-number rule with ClipFrames |
| Media trim worker | simplify | Worker shape fits C1-S17/S20; replace helper process with `timeout` + `sudo -n fstrim` (F4, F5); default off (F6) |
| Clip merge worker | keep | Same worker shape; yields to takes; only acts on split clips |
| Storage pre-roll thread | keep | C1-S20 shape; default off (F6) |
| Buffer events thread | rework-to-upstream-pattern | 1 Hz `wait()` + latch callback (C1-S21) |
| Buffer safety-stop thread | rework-to-upstream-pattern | Check in `wait()` and at command entry like `checkRecordingFailure` |
| CC `startStoragePreroll` / `finishStoragePreroll` | keep | Uses the real record path; judge details in the CC unit review |
| `DngRecordingQueue` additions | simplify | Keep ram mode, safety latch, part folders; take `framesPerFolder`/mode from settings, not the file |
| `scripts/apertar-media-trim` + sudoers | rework-to-upstream-pattern | S8 direct `sudo -n fstrim`; no helper in Core (S7, S9, C1-S29) |
| `tools/flatten_clip.py` | keep | Desk tool with no other home; small trims (F14) |
| Host tests | keep | New ground (S24), outside the build; drop those for deleted code |

## Conforms

- Pure logic as small header-only std-only files with inline free functions in `namespace apertar` (S4):
  `FramePath.hpp`, `ClipMerge.hpp`, `planBuffer` (`BufferBudget.hpp:338-380`).
- Frames mode stays the default and unchanged; ram mode never blocks capture, a full queue still drops
  (`BufferBudget.hpp:8`, N2); ram refuses itself on small boards (`:352`).
- New commands sit in the flat `if (command.name == ...)` chain with `okReply`/`errorReply`, snake_case
  `set_*` names, `value` / `enabled` arguments and operator sentences (C1-S02, C1-I03, C1-I04, C1-I06, C1-I07);
  added to the `help` list (`App:12930`).
- The pre-roll guard is one `||` list with its own sentence at the top of `handleCommand` (C1-S04, N17,
  `App:12588-12592`).
- State and events are flat scalars built by hand (C1-I08, C1-I09, C1-I20).
- `media_trim` persists as a `CaptureSettings` field in `camera_settings.conf` (S20, `CC:889`, `:976`).
- Logging `ApertarCore buffer: ...`, `ApertarCore media: trim ... reason= result= bytes= ms=` (I6, C1-I13).
- Workers are `std::thread` members with mutex, condition variable and stop flag, started in `start()`, joined
  in `stop()` (C1-S17, I16).
- A missing optional helper is probed with `std::filesystem::exists` and logged once (C1-N13, `App:11500-11513`).
- Split clips keep frame names, sidecars stay in the clip root, merge uses `RENAME_NOREPLACE`: media is never
  overwritten (N10).
- Manual install is stated in the README (S9 recipe step 6).

## Skeptic

Re-read at `cinemate-port` `01f170c` and `upstream-1.6.0` `35dbe67`. The host tests `buffer_budget`, `clip_merge`,
`frame_path` and `storage_preroll` compile with `g++ -std=c++20 -I src` and pass on this machine.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | stands | Confirmed: `loadBufferConf` is at `CC:2989-3006` and is called at `CC:4297` (frames per folder) and `CC:5505` (plan). Upstream CC has 0 hits for `apertar-hardware`. Upstream audio options come from UI settings (`App:2754` @upstream), not from the hardware file. Added to the where list: `CC:4297`. The port also has a second CC reader (`loadCameraSection`, `[camera]` ISO caps, `CC:2933-2950`). That reader belongs to another unit but follows the same pattern |
| F2 | stands | All statics confirmed (`BufferBudget.hpp:224-334`). Upstream does have function-local statics (`Mpu6050RecordingSession.cpp:80`, `:1228` @upstream), but each one is private to a single function and none is shared between subsystems. The `RecordingDropWarning` precedent is confirmed (`RecordingDropWarning.hpp:10-27`, `CC:3251`, `CameraController.hpp:113` @upstream) |
| F3 | corrected | The threads are confirmed. Rework gap: `runBufferEvents` also carries pre-roll active/fps/last and the dropped-frames count. Those have to be emitted at their own emit sites (the pre-roll thread, the drop latch callback), or they are lost when the thread goes |
| F4 | stands | Confirmed: script, sudoers line 4, `execl("/usr/bin/sudo","sudo","-n",helper,mountPoint)` (`App:6434`), upstream `App:1543-1544` and `:3609`, and `git ls-files scripts config` @upstream = 2 files. Context: the port ships 3 more helper scripts (`apertar-media-tune`, `apertar-boot-config`, `apertar-tune`), so this is one case of a port-wide pattern |
| F5 | stands | `waitForMediaTrim` (`App:11955-11960`) signals the `sudo` pid. `timeout 20 /usr/sbin/fstrim` (script :76) is not exec'd. GNU `timeout` also moves itself into its own process group, so even a relay to the group of `sh` does not reach it. Probable; settle it on the Pi as described |
| F6 | stands, evidence added | Trim default on is deliberate (`ce0bd90` "default on"). The pre-roll default contradicts the KB's own plan: `working/drop-frames/README.md:341` "the port is a setting (`storage_preroll`, default off at first), never a hidden step". `StoragePreroll.hpp:98` `value_or(true)` |
| F7 | corrected | The merge wait is at most 1 s (`App:11914`). `blockMs=5000` holds the merge worker off for 5 s and does not block the command, so it must stay. Worst-case stall: about 3.5 s for the trim plus 1 s for the merge |
| F8 | corrected | The quotes are confirmed. Most of the README section "Write-path knobs" (`README.md:337-356`) belongs to other units (media tune, DNG chain). This unit owns rows `:355-356` and the narrative at `:329`, `:333` |
| F9 | corrected | Confirmed, but the lines are wrong: `++remaining; ++remaining;` is at `ClipMerge.hpp:212-213`, and `decideGuard` is at `StoragePreroll.hpp:150` |
| F10 | corrected | `detail::frameNumber` is at `ClipMerge.hpp:61-63`, not :140-151. Both C++ copies are port code (`src/playback` does not exist @upstream). Better rework: both headers already include `cdng/FramePath.hpp`, so the rule belongs there. That avoids a `cdng` -> `playback` include |
| F11 | corrected | The flag mismatch is between the test heads themselves: `frame_path_test.cpp` and `clip_merge_test.cpp` say `-std=c++17` (matching the README), and `buffer_budget_test.cpp` says `-std=c++20`. The host-test pattern runs through the whole port (20 files in `tools/`). Severity lowered to nit |
| F12 | corrected | Upstream `/api/state` builds the full state (`buildWebStateJson`, `App:7154` @upstream, via `camera_.state()` / `settings()`). A small lock-free read route at 4 Hz during a take therefore has a real reason. Lean keep, and document it |
| F13 | corrected | Upstream naming is itself mixed: `prores_color`, `prores_repair` (snake_case), `settingsFile` (camelCase), `tuning`, `hardware`. The rename is optional; the placement point stands |
| F14 | stands | Confirmed: 284 lines, `statistics` at :27/:184, `--unflatten` at :196. No test calls the script |

## Final findings

### Media-buffer-split-F1 [mismatch, blocker] Recording/storage settings kept in apertar-hardware.conf and read by CameraController
- where: `src/camera/CameraController.cpp:2986-3006`, `:4297`, `:5505` @cinemate-port; `src/util/BufferBudget.hpp:97-194`; `src/util/StoragePreroll.hpp:22-89`; `src/ApertarCoreApp.cpp:12829-12925`; `src/hardware/HardwareConfigText.hpp:802,811` @cinemate-port
- port way: these are hardware-file keys: `[storage] buffer`, `buffer_ram_fraction`, `buffer_ram_floor_mb`, `buffer_ram_max_fraction`, `buffer_stop_percent`, `frames_per_folder`, `clip_merge`, and `[media] preroll`, `preroll_seconds`. Two hand-written parsers read them. `CameraController::loadBufferConf` opens the hardware file at every take start, in two places. Commands write the keys through `hardware::configStore().edit`. In the same unit, `media_trim` is a `CaptureSettings` field in `camera_settings.conf`.
- Apertar way: the camera never reads `apertar-hardware.conf` (S22): grep in `CameraController.cpp` @upstream-1.6.0 gives 0 hits. Camera settings persist only in `camera_settings.conf` (S20). Bench knobs are env vars read where they are used (`CameraController.cpp:3328-3329` @upstream-1.6.0 `unsignedEnvValue("APERTAR_CDNG_QUEUE_FRAMES", ...)`). Per-take inputs travel as option structs built by App (`Types.hpp:184-201` @upstream-1.6.0). The audio options come from UI settings (`ApertarCoreApp.cpp:2754` @upstream-1.6.0).
- why it matters: the strict three-way split breaks: hardware file, camera_settings.conf, env. The camera gains a reader of the hardware file, and operator switches gain a second persistence route. `media_trim` and `clip_merge`, switches of the same kind, end up in different stores. The port also adds a second CC reader (`loadCameraSection`, `CC:2933-2950`, another unit).
- rework:
  1. `buffer` mode and `frames_per_folder` become `CaptureSettings` fields. That means an enum with `toString`, a loader branch, the three field lists and the global carry-over at `CC:7945-7951` @upstream. Add CC setters through `applySettingsLocked`; the commands reply `settingsBody`.
  2. `clip_merge` and automatic `preroll` take the `media_trim` route.
  3. The ram fraction, floor, max fraction, `buffer_stop_percent` and `preroll_seconds` become env-only, read at the point of use, and leave the README.
  4. Delete `loadBufferConf`, `BufferConf`, `parseBufferConf`, `bufferConfProblem`, `PrerollConf`, `parsePrerollConf`, `prerollConfProblem` and `refreshBufferRequest`. Also delete the `[storage]`/`[media]` validator rules, the base/by revision handling and the template lines.
  5. Keep the state member names (`buffer_setting`, `frames_per_folder`, `clip_merge_enabled`, `storage_preroll_auto`).
- effort: L
- deliberate: no. KB `working/drop-frames/README.md:73` states where the keys live and does not weigh the choice.

### Media-buffer-split-F2 [mismatch, major] Cross-thread state through free-function statics and a global std::function hook
- where: `src/util/BufferBudget.hpp:221-334`; `src/util/StoragePreroll.hpp:221-271`; `src/camera/CameraController.cpp:4629,4635,5018`; `src/ApertarCoreApp.cpp:7988-7995`, `:252-285` @cinemate-port
- port way: these are process-wide mutable statics: `safetyStopState()`, `flushAbortMutex()`/`flushAbortFunction()`, `safetyStopHook()`, `bufferSettingStorage()`/`bufferSettingMutex()`, `framesPerFolderRequest()`, `clipMergeRequest()` and `prerollState()`. CC registers `flushAbortFunction() = [this]{ return abortSafetyFlush(); }`, and App assigns the global hook in its constructor body.
- Apertar way: a clip-scoped latch with a callback injected through the constructor: `src/util/RecordingDropWarning.hpp:10-27` @upstream-1.6.0. It is a controller member (`CameraController.hpp:113`) and is passed to the queue (`CameraController.cpp:3251` `explicit DngRecordingQueue(RecordingDropWarning *warning = nullptr)`). `RecordingFailure` is a recorder member (`CameraController.cpp:3901`). The upstream function-local statics (`Mpu6050RecordingSession.cpp:80`, `:1228`) are private to one function and never shared.
- why it matters: ownership is hidden. The controller calls into App through a global instead of a callback.
- rework: add `src/util/RecordingSafetyStop.hpp` shaped like `RecordingDropWarning`, with atomics `active`, `stopPercent`, `flushDiscarded` and a `changed` callback. Make it a CC member, passed to the `DngRecordingQueue` constructor. Add `CameraController::bufferStatus()` and `abortSafetyStopFlush()`, which take only the queue mutex; comment why. Pre-roll active/fps/last become App atomic members. `framesPerFolderRequest`, `clipMergeRequest` and `bufferSettingSnapshot` go with F1. Delete the statics.
- effort: M
- deliberate: unknown. The comments name lock-freedom as the reason (`BufferBudget.hpp:221`, `:254`); a latch member gives the same lock-freedom.

### Media-buffer-split-F3 [mismatch, major] Buffer events and safety-stop threads poll instead of the 1 Hz wait() supervision
- where: `src/ApertarCoreApp.cpp:10993-11050`, `:11083-11110` @cinemate-port
- port way: `runBufferEvents` loops every 250 ms or 1 s and emits `buffer` events, including the pre-roll and dropped-count changes. `runBufferSafetyStop` waits on a cv with a 100 ms backstop, then dispatches `record_stop`. Two extra threads, about 10 members.
- Apertar way: periodic supervision is the 1 Hz `wait()` loop (`ApertarCoreApp.cpp:7021-7053` @upstream-1.6.0). It checks `camera_.checkRecordingFailure()` and dispatches `enter_standby` via `handleCommand`. Events are emitted at their source, for example the `audio_level` callback (`ApertarCoreApp.cpp:8380-8384` @upstream-1.6.0).
- why it matters: two more threads with their own synchronisation, one of them a backstop for a lost wake-up, for checks that fit next to `checkRecordingFailure`.
- rework: check the safety latch in `wait()` and at `handleCommand` entry (next to `App:12584`), and dispatch `record_stop` there. Publish the `buffer` event from the latch's `changed` callback for flag flips and from `wait()` for the level. Emit the pre-roll changes from the pre-roll thread and the dropped count from the drop latch callback. Delete both threads and their members. A 1 s reaction leaves seconds of headroom at 90 % of a GiB-sized budget; say so in the commit. If the bar needs 4 Hz, see F12.
- effort: M
- deliberate: unknown. KB `drop-frames/README.md:74` describes the thread and weighs no alternative.

### Media-buffer-split-F4 [mismatch, major] Root fstrim helper as shell script in Core with path argument and path-only sudoers
- where: `scripts/apertar-media-trim:1-90`; `config/apertar-media-trim.sudoers:4`; `tools/media_trim_test.sh`; `src/ApertarCoreApp.cpp:6415-6447`, `:11484-11513`; `README.md:303-313` @cinemate-port
- port way: a POSIX sh root helper validates a mount-point argument and runs `timeout 20 /usr/sbin/fstrim -v`. The sudoers line `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-media-trim` allows any argument. Core runs `execl("/usr/bin/sudo","sudo","-n",helper,mountPoint)`. This is one of 4 port helper scripts in `scripts/`.
- Apertar way: simple privileged tools are called directly with `sudo -n` and `shellQuote`: `ApertarCoreApp.cpp:3609` @upstream-1.6.0 `runShellCommand("sudo -n mkdir -p " + shellQuote(mountPath), ...)`, and likewise mount, mkfs and `blockdev --flushbufs`. Real helpers are C++ in UI/src with UI sudoers and literal verbs only (`ApertarCoreApp.cpp:1543-1544` @upstream-1.6.0: "Fixed executable and arguments only; never accept paths from WebUI/config."). Core ships no helper scripts: `git ls-files scripts config` @upstream-1.6.0 gives 2 files.
- why it matters: it adds another way to get root, a shell script in Core that takes a data argument. The sudoers grant is wider than upstream's literal-verb rules, and the README gains a manual install of two files for one fstrim call.
- rework: delete the script, the sudoers file, `tools/media_trim_test.sh` and the README install block. Fork/exec `/usr/bin/timeout 20s /usr/bin/sudo -n /usr/sbin/fstrim -v <mediaRoot>` and keep the pid of `timeout` (owned by pi) for the kill. Check discard support in Core without privilege (`/sys/block/<disk>/queue/discard_max_bytes`). Map a missing sudo rule to "Trim needs sudo permission."
- effort: M
- deliberate: yes. Comment `App:11435` "(sudo -n, like apertar-media-tune)" copies the port's own helper, not upstream.

### Media-buffer-split-F5 [bug, major] Ending a running trim signals sudo/sh, fstrim keeps running into the take
- where: `src/ApertarCoreApp.cpp:11955-11963`; `scripts/apertar-media-trim:75-78` @cinemate-port
- port way: `waitForMediaTrim` sends SIGTERM and then SIGKILL to the `sudo` pid. sudo relays SIGTERM to `sh` only. The foreground child `timeout 20 /usr/sbin/fstrim` is not exec'd and runs in its own process group (GNU timeout), so it gets no signal. SIGKILL is never relayed.
- Apertar way: no precedent. Upstream wraps `sudo` in `/usr/bin/timeout` (`ApertarCoreApp.cpp:1544` @upstream-1.6.0), so the process it would signal is `timeout`, which forwards the signal.
- why it matters: start a trim that runs longer than 2 s (a mount trim on a slow card), then send `record_start`. Core logs "ended a trim that ran longer than 2 s" and starts the take while fstrim holds the filesystem for up to 20 s, the stall the wait exists to prevent. Probable, not run here. To settle it on the Pi: `kill -TERM <sudo pid>` during a trim, then `pgrep -a fstrim`.
- rework: fixed by the F4 rework (signal `timeout`). Minimum stop-gap: `exec timeout 20 /usr/sbin/fstrim -v "$MNT"` in the script.
- effort: S
- deliberate: no

### Media-buffer-split-F6 [removed-upstream-behaviour, major] Drive trim and automatic storage pre-roll on by default change stock behaviour
- where: `src/util/StoragePreroll.hpp:91-99`; `src/camera/CameraController.cpp:889,976`; `src/ApertarCoreApp.hpp:299`; `src/ApertarCoreApp.cpp:12588-12592` @cinemate-port
- port way: `media_trim` defaults to true. It trims after any delete of 1 GiB or more, at every mount and after a format, so deleted takes cannot be recovered (KB `drop-frames/README.md:69` "no undelete"). `[media] preroll` defaults to on (`value_or(true)`). At Core start, every card insert and every format, a 2 s raw take runs. Meanwhile record, photo, timelapse, media actions and standby are refused with "Storage pre-roll is running. One moment."
- Apertar way: upstream never discards free space and never writes to the media without an operator action. It records as soon as it is Ready. It refuses commands only for work the operator started (`ApertarCoreApp.cpp:9095-9117` @upstream-1.6.0).
- why it matters: two stock behaviours change silently: deleted clips become unrecoverable, and the camera is unavailable for seconds after boot or a card insert. The KB's own plan said the pre-roll should be "a setting (`storage_preroll`, default off at first), never a hidden step" (`drop-frames/README.md:341`). The port made `apertar-media-tune` opt-in for a similar reason (`e9dd6b2`).
- rework: set both defaults off: `CaptureSettings{}.mediaTrimEnabled = false`, `mediaTrimSetting_{false}`, automatic pre-roll off. Keep the WebUI switches. The README says what turning trim on costs (no undelete).
- effort: S
- deliberate: yes for trim (`ce0bd90` "default on"). The pre-roll default contradicts the documented plan.

### Media-buffer-split-F7 [mismatch, minor] Capture and media commands wait for trim and merge under commandMutex_
- where: `src/ApertarCoreApp.cpp:12614-12619`, `:11905-11916`, `:11941-11963` @cinemate-port
- port way: `record_start`, `capture_photo`, `timelapse_start` and the media actions call `waitForMediaTrim(name, 5000)` and `waitForClipMerge(name, 5000)` inside `handleCommand`. The trim wait is up to about 3.5 s (2 s + 1 s + 0.5 s) and the merge wait up to 1 s. In both calls, 5000 holds the worker off and does not block the command.
- Apertar way: upstream refuses with a sentence instead of waiting on a background media job (`ApertarCoreApp.cpp:9108-9110` @upstream-1.6.0, "Wait for the media speed test to finish first."). One lock serialises all commands.
- why it matters: while a trim winds down, every socket, WebUI and button command waits behind `commandMutex_`, for up to about 4.5 s.
- rework: keep "record always starts" if the owner wants it. After F4 the trim ends through `timeout`, so the wait shortens. Keep the 5 s hold-off of both workers. Document the choice for the original developer.
- effort: S
- deliberate: yes. KB `drop-frames/README.md:69`.

### Media-buffer-split-F8 [slop, minor] Comments and README narrate history and cite KB paths, campaigns, other projects, commits
- where: `src/cdng/FramePath.hpp:9-11`; `src/util/BufferBudget.hpp:6-7`; `src/ApertarCoreApp.cpp:11114`, `:11626-11627`; `src/camera/CameraController.cpp:5546`; `README.md:329`, `:333`, `:355-356` @cinemate-port
- port way: examples are "(apertar-kb working/drop-frames/nvme-campaign/probe-exfat-dir.md)", "follow cinepi-raw's DNG encoder (cinepi/dng_encoder.cpp ...)", "(the NVMe campaign does, for its A/B)", "CineMate's storage warm-up", "the rule since db17860", "measured 2026-11-08", "local branch `clip-split`", plus this unit's env rows in the README table "Write-path knobs for A/B tests". Most of that table belongs to other units.
- Apertar way: no tickets or other projects' commits in source (C8-S9). Comments are rare one-line why-notes (C1-I14), e.g. `ApertarCoreApp.cpp:1543` @upstream-1.6.0. No env-knob tables in the README (C8-S12).
- why it matters: these references mean nothing to the original developer, and they age badly.
- rework: keep one-line technical reasons ("exFAT walks every entry of the target folder on create"). Drop KB paths, campaign names, dates, hashes and other-project references. Remove rows `:355-356`; the rest of the table is for the units that own it.
- effort: S
- deliberate: no

### Media-buffer-split-F9 [slop, minor] Env twin for every file key, *_env flags in state, unused speculative parameter
- where: `src/util/BufferBudget.hpp:303-329`; `src/util/StoragePreroll.hpp:91-99`, `:148-150`; `src/ApertarCoreApp.cpp:262-285`; `src/cdng/ClipMerge.hpp:212-213` @cinemate-port
- port way: env > file > default chains for buffer, frames_per_folder, clip_merge, preroll and stop percent. State exposes `frames_per_folder_env`, `clip_merge_env_off`, `storage_preroll_auto_env` and `media_trim_env_off`. `decideGuard(const GuardInputs &, Trigger)` ignores the Trigger, "so a future rule can differ". `refreshBufferRequest` parses the same text three times. And `++remaining; ++remaining;`.
- Apertar way: env knobs are read where they are used and not shown to clients (`CameraController.cpp:3328-3329` @upstream-1.6.0). Comments state a present reason.
- why it matters: these are experiment leftovers and generality built ahead of need; they double the precedence logic.
- rework: after F1, at most one bench env var per knob, read at the point of use. Drop the `*_env` state members and the `Trigger` parameter. Parse once. Write `remaining += 2`.
- effort: S
- deliberate: no

### Media-buffer-split-F10 [duplication, minor] Frame-number rule in three copies; three copied store.edit command blocks
- where: `src/cdng/ClipMerge.hpp:61-63`; `src/playback/ClipFrames.hpp:96`; `tools/flatten_clip.py:47-57`; `src/ApertarCoreApp.cpp:12829-12850`, `:12857-12895`, `:12900-12925` @cinemate-port
- port way: `detail::frameNumber` is commented "Same rule as playback/ClipFrames.hpp frameNumberFromName". Both C++ copies are port code, and a Python copy exists too. There are three ~20-line `store.edit`/`StoreFlags`/`controlsErrors_`/`wakeControlsWorker`/`refreshBufferRequest` blocks.
- Apertar way: a shape repeated inside one function becomes a local lambda (C1-I17; `ApertarCoreApp.cpp:9478`, `:8671` @upstream-1.6.0).
- why it matters: two C++ copies of one parsing rule can drift, and so can the copied command blocks.
- rework: move the rule into `cdng/FramePath.hpp`, which both headers already include, and call it from both. The Python copy is fine for a desk tool. The `store.edit` blocks go away with F1; otherwise use one local lambda.
- effort: S
- deliberate: no

### Media-buffer-split-F11 [new-ground, nit] Host unit tests in tools/, outside the build
- where: `tools/buffer_budget_test.cpp`, `tools/storage_preroll_test.cpp`, `tools/storage_buffer_conf_test.cpp`, `tools/clip_merge_test.cpp`, `tools/frame_path_test.cpp`, `tools/media_trim_test.sh`; `README.md:335` @cinemate-port
- port way: standalone g++ programs, each with its own `check()` and a compile line in a comment. None of them is in `CMakeLists.txt`. The compile lines disagree: `frame_path` and `clip_merge` say `-std=c++17`, `buffer_budget` says `-std=c++20`. The four `.cpp` tests here compile with c++20 and pass. The same pattern runs through the whole port (20 files in `tools/`).
- Apertar way: no precedent. Upstream Core has no tests and no `tools/`.
- why it matters: it is new ground, not a mismatch. The tests cost the build nothing.
- rework: keep them. Drop `storage_buffer_conf_test.cpp` and `media_trim_test.sh` with F1/F4. Use one compile command (c++20, matching Core) and one README line under For Developers.
- effort: S
- deliberate: yes. Commits `d7dd337` and `ba0658d` record desk test runs.

### Media-buffer-split-F12 [new-ground, minor] GET /api/buffer polled at 4 Hz beside /api/state
- where: `src/ApertarCoreApp.cpp:8418-8425`; `src/web/WebControlPage.cpp:16490-16500`, `:20363` @cinemate-port
- port way: a lock-free read-only route returns the buffer and pre-roll members. The WebUI polls it about 4 times a second while the bar or the pre-roll pill shows.
- Apertar way: the WebUI polls `GET /api/state` at 1 Hz, with no push channel (C1-S26). `/api/state` builds the full state through controller calls (`ApertarCoreApp.cpp:7154` @upstream-1.6.0). Extra read-only GET routes exist (`/api/media`, `/api/config`, `/api/presets`).
- why it matters: the bar gets a second state endpoint and a second polling rate. Polling the full state at 4 Hz during a take would cost more.
- rework: keep the route and state its reason (a smooth bar during a take, without the controller lock) in the handoff. Drop it only if 1 Hz from `/api/state` is enough.
- effort: S
- deliberate: unknown

### Media-buffer-split-F13 [mismatch, nit] Namespace names and src/util placement differ from upstream
- where: `src/util/BufferBudget.hpp:45`; `src/util/StoragePreroll.hpp:16`; `src/cdng/FramePath.hpp:18`; `src/cdng/ClipMerge.hpp:21` @cinemate-port
- port way: `apertar::bufferbudget`, `storagepreroll`, `clipmerge`, `framepath`. `BufferBudget.hpp` and `StoragePreroll.hpp` sit in `src/util`.
- Apertar way: upstream nested names are mixed: `apertar::settingsFile` (`SettingsFile.hpp:17`), `apertar::tuning`, `apertar::hardware`, `prores_color`, `prores_repair`. `src/util` @upstream holds only `AtomicStillFile`, `RecordingDropWarning`, `RecordingFailure` and `SettingsFile`. Subsystem logic sits next to its owner (`src/camera/StillBracketing.hpp`).
- why it matters: small reading frictions.
- rework: move `BufferBudget.hpp` next to the queue (`src/camera` or `src/cdng`) and `StoragePreroll.hpp` next to App. Optionally rename to camelCase (`bufferBudget`, ...) to match `settingsFile`.
- effort: S
- deliberate: no

### Media-buffer-split-F14 [new-ground, nit] tools/flatten_clip.py desk tool
- where: `tools/flatten_clip.py` @cinemate-port
- port way: a 284-line stdlib Python script with dry run, `--apply` and `--unflatten N`. It reports timing statistics (`statistics` at :27, :184-189).
- Apertar way: no precedent. Core ships no helper scripts (C1-S29), and upstream has no `tools/`.
- why it matters: it is useful when a card leaves the camera before the merge worker has run, and nothing else covers that case on a computer.
- rework: keep it. Drop the statistics report. Keep `--unflatten` only if a test uses it; no test does now.
- effort: S
- deliberate: yes. Commit `9ec37b5` and `README:331`.
