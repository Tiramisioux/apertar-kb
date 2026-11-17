# Inventory: Media-buffer-split (stage 1, no judgement)

Refs: port = `cinemate-port` `01f170c` (Apertar-Core), upstream = `upstream-1.6.0` `35dbe67`. Line numbers are @cinemate-port unless marked. Labels: confirmed = read in code; probable = inferred.

## 1. Commits and recorded status

| Commit | What | fork-log status | Tests recorded in the commit |
| --- | --- | --- | --- |
| `d44b177` | "drop-frames" squash of 19 commits (2026-10-31/11-01): trim helper + worker, Log, buffer level/bar, frames/ram switch, safety stop, fps max from probe, storage pre-roll, Settings search, GPIO cards, Clear HDR override | fork-log.md:138 "branch drop-frames, nothing merged"; later "not yet run on the camera" for the squash | Host tests on the Mac; Pi build compiled 23:08. Run on Pi (earlier build): trim at mount, Log 16->12. "Not compiled or run yet: pre-roll and Clear HDR override. Not run yet: ram queue, safety stop, buttons, fps ceilings" |
| `c5db8b2` | record during a safety-stop flush discards the queued frames (`abortSafetyStopFlush`, `buffer_flush_discarded`, `discarded_on_stop`) | fork-log.md:138 "owner decision 2026-11-01" | none recorded in message |
| `d7dd337` | `[storage] frames_per_folder`, `part_NNN/`, `.parts` marker, `FramePath.hpp`, `listFrames` reads parts | fork-log.md:186 fork-only, on GitHub `cinemate-port` | desk: `frame_path_test`, `storage_buffer_conf_test`; Pi: build rc 0 |
| `9ec37b5` | `tools/flatten_clip.py` | fork-log.md:187 fork-only | desk: round trip of 1,234 empty frames at N=500, dry run, planted conflict, partly merged |
| `ba0658d` | merge worker (`ClipMerge.hpp`, `runClipMerge`, `mergeSplitClip`, `waitForClipMerge`), `[storage] clip_merge`, `APERTAR_CLIP_MERGE`, `set_clip_merge` | fork-log.md:188 fork-only | desk: `clip_merge_test`, `storage_buffer_conf_test`; Pi build rc 0, "not yet run on the camera" |
| `68516f1`, `01f170c` | merge worker follow-ups (after-pause rescan; `refreshBufferRequest()` before the worker starts) | fork-log.md:189-190 | verify step 6 on the camera (per fork-log) |
| `00f2327` | trim at mount, after big deletes and after external deletes (pre-roll parts left out) | fork-log.md:156 "fork-only; Pi only, built 2026-11-04"; the trim worker present at HEAD is the d44b177 one | Pi build |

Only d44b177, c5db8b2, d7dd337, 9ec37b5, ba0658d touch the scope files (confirmed: `git log origin/main..cinemate-port -- <scope files>`). Host tests this run (g++ in scratchpad, not the shared build dirs): storage_preroll_test 53 ok, buffer_budget_test 28 ok, storage_buffer_conf_test 64 ok, clip_merge_test 23 ok, frame_path_test 34 ok, media_trim_test.sh all ok (argument-validation paths only). Nothing in the scope has a test of the Core-side mechanism (workers, CameraController queue, safety-stop hook, pre-roll take, merge executor); only the pure headers and the helper's argument checks.

## 2. Features (operator-visible)

| # | Feature | Commits | Operator gets | Relation to upstream |
| --- | --- | --- | --- | --- |
| F1 | Drive trim | d44b177 (+00f2327) | The recording drive is trimmed after a delete that frees >= 1 GiB and at mount; never during a take; System pane switch "media trim" (default on); journal lines `ApertarCore media: trim ... result=` | adds a worker thread and a root helper beside upstream code; entirely new area (upstream has no trim) |
| F2 | Write buffer level and bar | d44b177 | Red buffer bar in the REC pill (option, off by default) on WebUI, touch UI and HDMI monitor; live `buffer` event and `GET /api/buffer` | new area (upstream has no `frameBufferStatus`, grep confirmed empty @upstream) |
| F3 | Frames / RAM write queue | d44b177 | Settings buttons Frames / RAM; RAM queue sized from MemAvailable; refuses to be smaller than the 12-frame queue | extends upstream `DngRecordingQueue` in place (upstream: `maxQueuedFrames_` frame count, env `APERTAR_CDNG_QUEUE_FRAMES`, `CameraController.cpp:3329-3330` @upstream); adds a parallel byte-budget mode |
| F4 | Safety stop | d44b177 | In ram mode the take ends cleanly at 90 % buffer; pill goes green while the buffer empties; READY at zero | new area, hooks the queue's `enqueue` |
| F5 | Record during safety-stop flush | c5db8b2 | Pressing record during the flush discards queued frames of the old clip and starts at once; toast with count | new area |
| F6 | Storage pre-roll | d44b177 | A 2 s raw take at the mode's maximum fps, clip deleted; on Core start, card insert, format and by hand; blue PRE-ROLL pill; WebUI button and On/Off; Settings `[media]` | new area (CineMate "warm-up") |
| F7 | Split takes into part folders | d7dd337 | `frames_per_folder` N (0 = off; 100..100000): frames in `<clip>/part_NNN/`; WebUI field "Frames per folder"; playback and delete read part folders | extends upstream frame-name/path code in place (`frameFilename` + new `framepath::framePath`), new header |
| F8 | Hand merge | 9ec37b5 | `python3 -I tools/flatten_clip.py <clip> [--apply] [--unflatten N]` for Mac/Pi | new helper script; upstream `tools/` has none (upstream has no `tools/` listing in this unit's grep) |
| F9 | Automatic merge worker | ba0658d (+68516f1, 01f170c) | Idle camera moves split clips back into one folder, oldest clip first; WebUI "Merge split clips" On/Off with "pending: N" and last result | worker thread beside the trim worker; new |

## 3. Interface additions (every one)

### 3.1 Socket commands (flat `if (command.name == ...)` chain in `ApertarCoreApp::handleCommand`, same chain as upstream)

| Command | Args | Where | Effect |
| --- | --- | --- | --- |
| `set_buffer_mode` | `value=frames\|ram`, optional `base`, `by` | ApertarCoreApp.cpp:12829 | `store.edit` of `[storage] buffer`; replies `apply=next_take` + `bufferSettingMembers()` |
| `set_frames_per_folder` | `value=0\|100..100000` | :12857 (shared branch with set_clip_merge) | `store.edit` `[storage] frames_per_folder`; `apply=next_take` |
| `set_clip_merge` | `enabled=true\|false\|1\|0` | :12857 | `store.edit` `[storage] clip_merge`; calls `clipMerge("switch")`; `apply=now` |
| `set_storage_preroll` | `value=on\|off\|true\|false\|1\|0` | :12900 | `store.edit` `[media] preroll` |
| `storage_preroll` | optional `seconds` 1..10 | :14603 | manual pre-roll; guard error reply or `storage_preroll_started:true` |
| `set_media_trim` | `enabled` | :13194 | `camera_.setMediaTrimEnabled`, `mediaTrimSetting_` atomic; persists as `media_trim=` in `camera_settings.conf` (CameraController.cpp:889, :976) |
| `record_stop` (changed) | | :14833 | during a pre-roll it only sets `storagePrerollStop_` and replies `storage_preroll_stopped:true` |
| `record_start` (changed) | | :12618, `abortSafetyStopFlushForRecord` (:289) | aborts a safety-stop flush before any lock; waits for trim and merge (`waitForMediaTrim`, `waitForClipMerge`, 5000 ms block) |
| `format_media` (changed) | | :14620 | sets `storagePrerollFormatRunning_`; requests a Format-trigger pre-roll afterwards |
| `help` (changed) | | :12930 | command list gains the 5 new set_ commands |
| gates (changed) | | :12588-12592 | while a pre-roll runs, capture_photo, record_start, timelapse_start, format/eject/mount, speed test, enter_standby, storage_preroll are refused: "Storage pre-roll is running. One moment." |

Command-to-store pattern: the 4 `set_*` buffer/preroll commands copy the same ~20-line block (store.edit, `StoreFlags{backup,trusted}`, `controlsErrors_`, `wakeControlsWorker`, `refreshBufferRequest`) three times in the file (confirmed :12829, :12857, :12900).

### 3.2 HTTP routes

| Route | Where | Notes |
| --- | --- | --- |
| `GET /api/buffer` | ApertarCoreApp.cpp:8419 | lock-free; `bufferMembers()` + `recording` (false once the safety stop is active); polled about 4 Hz by the WebUI while the bar or pre-roll pill is shown (WebControlPage.cpp:16497) |
| `/api/state` (changed) | :9583-9586 | gains `mediaTrimStateJson()`, `clipMergeStateJson()`, `bufferSettingMembers()` members |

### 3.3 State fields (flat JSON, scalars)

| Field | Source |
| --- | --- |
| `buffer_used`, `buffer_capacity`, `buffer_fill`, `buffer_mode` (`frames`/`ram`/`none`), `buffer_unit` (`frames`/`bytes`) | `bufferMembers` (:304-308) |
| `buffer_setting`, `buffer_note`, `buffer_safety_stop`, `buffer_stop_percent`, `buffer_flush_discarded` | `bufferSettingMembers` (:252-259) |
| `storage_preroll_active`, `_auto`, `_auto_env`, `_fps`, `_last` | same, :260-264 |
| `frames_per_folder`, `frames_per_folder_env`, `clip_merge_enabled`, `clip_merge_env_off` | same, :265-268 |
| `clip_merge_pending`, `clip_merge_active`, `clip_merge_last` | `clipMergeStateJson` (:11919) |
| `media_trim_last_result`, `_last_bytes`, `_last_ms`, `_last_unix`, `media_trim_running`, `media_trim_env_off`, `media_trim_enabled` | `mediaTrimStateJson`, :9585 |
| `recording_dropped_frames` in the buffer event | `bufferEventJson`; commit 64bbbaa (other unit) |
| `discarded_on_stop` | record_stop reply, from c5db8b2; counter in the queue |
| UI-side: `frame_buffer_bar_enabled` | `set_frame_buffer_bar_enabled` in `UI.conf` side (:13507, :9664) |

### 3.4 Events

| Event | Where | When |
| --- | --- | --- |
| `buffer` | `runBufferEvents` (:10986 ff), own thread | level change while a take runs or the queue holds frames (max 4/s); also on setting, note, safety flag, stop percent, flush-discarded, pre-roll active/auto/last/fps, or dropped-frame change; one with 0 when drained |
| `recording` (changed) | CameraController.cpp:12442 `announcedEarly` | at a safety stop the `recording=false` event goes out before the drain |

### 3.5 Config keys

| File:[section] key | Values | Parsed by | Default |
| --- | --- | --- | --- |
| `apertar-hardware.conf:[storage] buffer` | frames, ram | `parseBufferConf` | frames |
| `[storage] buffer_ram_fraction` | 0.05..0.9 | same | 0.6 |
| `[storage] buffer_ram_floor_mb` | 0..1048576 | same | 512 |
| `[storage] buffer_ram_max_fraction` | 0.1..0.75 | same | 0.5 |
| `[storage] buffer_stop_percent` | 0 or 50..99 | same | 90 in ram, 0 in frames |
| `[storage] frames_per_folder` | 0 or 100..100000 | same | 0 |
| `[storage] clip_merge` | on, off | same | on |
| `[media] preroll` | on, off | `storagepreroll::parsePrerollConf` | on |
| `[media] preroll_seconds` | 1..10 | same | 2 |
| `camera_settings.conf: media_trim` | true/false | CameraController settings loader (:889) | true |
| `UI.conf` frame_buffer_bar_enabled | bool | `handleUiToggle` | off |

Hardware-file validator: `HardwareConfigText.hpp:802` (storage) and `:811` (media) call `bufferConfProblem` / `prerollConfProblem`, `[storage]` and `[media]` added as known sections with `ValueRule::Raw` (confirmed from diff, `HardwareConfigText.hpp` is new in the port as a whole; other unit). Note in `BufferBudget.hpp:~140`: "Core's Python reader keeps the comment in the value, and the validator says so" (a second reader of the same file exists in Python, in `ApertarCoreApp.cpp` embedded script; the `[storage]` section also carries upstream's `mount_path`, `pcie_controller`).

### 3.6 Environment variables

| Variable | Meaning | Read in |
| --- | --- | --- |
| `APERTAR_CDNG_BUFFER` | frames/ram, wins over file (anything not "ram" = frames; unset-but-empty ignored) | `requestedBufferMode`, `planQueueBuffer` |
| `APERTAR_CDNG_QUEUE_RAM_FRACTION`, `_FLOOR_MB`, `_MAX_FRACTION` | ram plan inputs | CameraController.cpp:5535-5537 |
| `APERTAR_CDNG_BUFFER_STOP_PERCENT` | safety stop, same rules as key | :5515 |
| `APERTAR_CDNG_FRAMES_PER_FOLDER` | wins over file; bad value = 0 with a log line | :4294, `requestedFramesPerFolder` |
| `APERTAR_CLIP_MERGE=0` | forces merge off | `clipMergeEnvOff` |
| `APERTAR_STORAGE_PREROLL=0\|1` | wins over `[media] preroll` for the automatic triggers | `automaticEnabled`, `publishAutomatic` |
| `APERTAR_MEDIA_TRIM=0` | forces trim off | ApertarCoreApp.cpp:6399 `mediaTrimEnvOff` |
| `APERTAR_HARDWARE_CONFIG` | path override; read by the new `loadBufferConf()` | CameraController.cpp:2991 |
| `APERTAR_FPS_LIMIT=table`, `APERTAR_LOSSLESS_FPS_LIMIT` | from the same d44b177 squash, not this unit (fps ceiling) | noted only |

### 3.7 Files on disk

| Path | Written by | Purpose |
| --- | --- | --- |
| `/usr/local/libexec/apertar-media-trim` | manual install of `scripts/apertar-media-trim` (README block) | root fstrim helper |
| `/etc/sudoers.d/apertar-media-trim` | manual install of `config/apertar-media-trim.sudoers` | `pi ALL=(root) NOPASSWD: /usr/local/libexec/apertar-media-trim` |
| `<clip>/part_NNN/` (>= 3 digits) | queue copy side (`ensurePartFolder`, CameraController.cpp:4961) | frames of a split take |
| `<clip>/.parts` | take start when N > 0 (CameraController.cpp:4311) | marker: text `frames_per_folder=N`, `pattern=<clip>_%09d.dng`; removed last by the merge |
| pre-roll clip folder | `startStoragePreroll`, deleted by `finishStoragePreroll` | never persists (part folders are not used on a pre-roll: `prerollTake_` check at :4293) |
| README sections | d44b177, d7dd337, 9ec37b5, ba0658d | "Trim", "Split clips", env table rows |

### 3.8 UI elements

| Element | File | Notes |
| --- | --- | --- |
| Red buffer bar in REC pill | WebControlPage.cpp:16417-16580; UI `RecordingStatusChip`-style QML (`bufferBarVisible`, `frameBufferBarEnabled`), monitoring item "Frame Buffer Bar" | bar option off by default |
| Blue PRE-ROLL pill | WebControlPage.cpp:15391, :15763, :16453; UI `prerollOnly`, `chipLabel` "PRE-ROLL" (width 118) | |
| "Storage pre-roll" button, On/Off auto row, last-result note | WebControlPage.cpp:5769-5778, :15827-15860, :19824 | |
| Settings "media trim" On/Off | WebControlPage.cpp:5800 area, :16179-16186 | |
| "Frames per folder" number input + Apply | :5808-5815, :16192-16200, :20676-20685 | the WebUI field validates 0 or 100..100000 itself |
| "Merge split clips" On/Off + pending/last text | :5822-5826, :16206-16230 | |
| Frames / RAM buttons | :15463-15490 | note line shows plan text |
| Toast on flush discard | `noteBufferSafetyStop` (:16522) | |
| UI (Qt): `ApertarControlBridge.cpp` handles `buffer` event, `buffer_fill`, `buffer_safety_stop`, `storage_preroll_*`; sends `storage_preroll`, `set_storage_preroll`; clip browser reads parts via `ClipFrameFiles.hpp` (UI `7ea9afc`) | other repo, outside this scope; listed for completeness |

## 4. New abstractions

| Name | Kind | Files | Purpose | Upstream does the same job with |
| --- | --- | --- | --- | --- |
| `apertar::bufferbudget` + `BufferPlan`/`planBuffer` | header-only namespace (382 lines) | `src/util/BufferBudget.hpp` | RAM budget math, `[storage]` text parser, safety-stop rule, stop hook, atomics via free functions | upstream: `unsignedEnvValue("APERTAR_CDNG_QUEUE_FRAMES", ...)` (`CameraController.cpp:3329` @upstream); no budget module |
| `bufferbudget::BufferConf` + `parseBufferConf` | second parser of `apertar-hardware.conf` text, hand-written ini loop | same | typed `[storage]` keys | upstream: each hardware class parses its own section (`src/hardware/*.cpp` reading `apertar-hardware.conf`) |
| `loadBufferConf()` (anonymous function in `CameraController.cpp:2989`) | file reader with its own candidate list (`APERTAR_HARDWARE_CONFIG`, `/home/pi/apertar-hardware.conf`, `/boot/firmware/...`, `/boot/...`) | CameraController.cpp | read `[storage]` at each take, not through `hardware::configStore()` | upstream: same candidate-path idiom is repeated in each hardware class (confirmed `/home/pi/apertar-hardware.conf` appears twice in port CC at :2948 and :2994; upstream has it in 8 files) |
| Free-function atomics `safetyStopState()`, `framesPerFolderRequest()`, `clipMergeRequest()`, `bufferSettingSnapshot()`, `flushAbortFunction()`/`flushAbortMutex()`, `safetyStopHook()`, `prerollState()` | process-wide function-local statics | BufferBudget.hpp, StoragePreroll.hpp | lock-free cross-thread state read by events thread, state JSON and queue | upstream: state held as members of `ApertarCoreApp` / `CameraController` and read under `commandMutex_`/controller mutex; for lock-free reads a small struct (`FrameBufferGauge` is new; `RecordingDropWarning.hpp` in `src/util` is the nearest upstream pattern) |
| `bufferbudget::safetyStopHook()` / `std::function` global | callback registry | BufferBudget.hpp:~219 | queue calls ApertarCoreApp from under its mutex | upstream: `RecordingFailure.hpp` / `RecordingDropWarning` callbacks passed by constructor |
| `apertar::storagepreroll` | header-only namespace (273 lines): `PrerollConf`, `GuardInputs`, `decideGuard`, `Trigger`, `MountChange`, `triggerForMountChange`, `measuredFps`, `lastOk`, `PrerollState` | `src/util/StoragePreroll.hpp` | decisions for pre-roll, plus a second hand-written `[media]` ini parser (`parsePrerollConf`, duplicating the trim/lower lambdas of `parseBufferConf`) | none (new ground) |
| `apertar::framepath` | header-only namespace (79 lines) | `src/cdng/FramePath.hpp` | `partDirName`, `isPartDirName`, `framePath`, `.parts` marker name, N validation | none; upstream builds `folderPath_/frameName` inline |
| `apertar::clipmerge` | header-only namespace (182 lines): `Listing`, `Plan`, `Step`, `plan()`, `prefixInvariant()` | `src/cdng/ClipMerge.hpp` | pure rename plan for a merge | none; the executor (`mergeSplitClip`, `listClip`, `renameNoReplace`, `fsyncFolder`) is in ApertarCoreApp.cpp:11620-11890 |
| Media trim worker thread (`runMediaTrim`, `trimMedia`, `waitForMediaTrim`, `mediaTrimMayRun`, `runTrimHelperProcess`) | `std::thread` + cv, ~12 members | ApertarCoreApp.cpp:11433-11620 | trim with back-off (3 failures -> 60 s then 600 s), kill on take | upstream: `mediaSpeedThread_` (`ApertarCoreApp.hpp:176` @upstream) is the only media worker, one-shot per command |
| Clip merge worker thread (`runClipMerge`, `clipMergeMayRun`, `waitForClipMerge`) | `std::thread` at nice 10 | ApertarCoreApp.cpp:11620-11930 | rename loop | none |
| Storage pre-roll thread (`runStoragePreroll`, `requestStoragePreroll`, `runStoragePrerollOnce`, `storagePrerollGuard`) | `std::thread` + cv, coalescing, 3 s settle, 120 s wait for trim | ApertarCoreApp.cpp:11112-11330 | run a pre-roll off the HTTP/watcher thread | none |
| Buffer events thread (`runBufferEvents`) | `std::thread`, 250 ms / 1 s loop | :10986 | `buffer` event | upstream: events are published from the thread that changes state (`publishEvent`); no polling event thread |
| Buffer safety-stop thread (`runBufferSafetyStop`) | `std::thread`, 100 ms backstop wait | :11060 | turns the queue's hook into `record_stop` via `dispatchHardwareInputCommand` | none |
| `CameraController::startStoragePreroll` / `finishStoragePreroll` / `StoragePrerollResult`; `session_->setPrerollFps`, `setPrerollTake`, `waitForFramePeriod`, `prerollMeasure` | members | CameraController.cpp:12040-12190, header :149-160 | the pre-roll take through the real recording path | none; upstream `startRecording` / `stopRecording` only |
| `DngRecordingQueue` additions: `ramMode_`, `queuedBytes_`, `queueBudgetBytes_`, `planQueueBuffer`, `abortSafetyFlush`, `ensurePartFolder`, `partsCreated_`, `framesPerFolder_`, `prerollTake_`, `safetyStopFired_`, `stopPercent_` | members in the existing queue class | CameraController.cpp:4290-5545 | ram mode, safety stop, split | upstream queue: frames-only |
| `scripts/apertar-media-trim` + `config/apertar-media-trim.sudoers` | root POSIX sh helper + sudoers drop-in | scripts/, config/ | fstrim with 5 argument checks, canonical-path check, discard check, 20 s timeout, exit codes 0..4 | upstream: privileged helpers are called as `sudo -n /usr/local/libexec/apertar-standby-usb` (`ApertarCoreApp.cpp:1544` @upstream) with no helper or sudoers file in the repo and no install block in the README (grep `libexec\|sudoers` README @upstream = empty); upstream repo `config/` holds only `apertar-core-capture-priority.conf` |
| `tools/flatten_clip.py` | Python 3.9+ stdlib, `python3 -I` | tools/ | by-hand merge/unmerge, 284 lines | none (upstream has no python tools in Core; Core embeds a Python script string for the hardware file) |
| Five host test programs + `media_trim_test.sh` | stand-alone `g++` tests, own `check()` macro each, not in CMake (probable: no `add_test` for them; unconfirmed, command: `grep -n "_test" CMakeLists.txt`) | tools/ | tests | none; upstream Core has no unit tests (BRIEF) |

## 5. Upstream code regions changed

| Region | Where | Change | Kind |
| --- | --- | --- | --- |
| `DngRecordingQueue::enqueue` | CameraController.cpp:4967-5020 @port | full-check switched on `ramMode_ ? !queueHasRoomForBytes(...) : queue_.size() >= maxQueuedFrames_`; drop log gains `ramQueueText()`; job path uses `framepath::framePath(...)`; safety-stop check after push | extended-in-place |
| `DngRecordingQueue` stop/drain, failure path | :4592-4640, :5430-5445 | clears `queuedBytes_`, resets `safetyStopState().active`; `abortSafetyFlush` added | extended-in-place |
| `recycleRawBuffer`, `preferredRawPoolSize` | :5448-5470, :5560 | ram-mode byte bound and unbounded pool count in ram | behaviour-changed |
| Take start (queue `start`) | :4288-4320 | reads `frames_per_folder` through `loadBufferConf()`, creates `part_000` and writes `.parts` | extended-in-place |
| `CameraController::stopRecording` | :12436-12450 | `announcedEarly`: emits the recording event before the drain on a safety stop | behaviour-changed |
| `CaptureSettings` / settings loader and writer | Types.hpp:140; CC :889, :976, :11349-11368, :11889 | new field `mediaTrimEnabled`, key `media_trim`, kept across format switch | extended-in-place |
| `ApertarCoreApp::handleCommand` gate section | :12580-12625 | pre-roll gate, trim/merge waits before take and media actions | extended-in-place |
| `record_stop`, `format_media` | :14833, :14620 | pre-roll early end; format marks the pre-roll watcher | extended-in-place |
| `runMediaWatcher` | :10930-10960 | on mount: `trimMedia("mount")`, `clipMerge("mount")`, pre-roll trigger decision | extended-in-place |
| media delete handlers | :9030, :9113 | `waitForClipMerge("media_delete", 0)`; `trimMediaAfterDelete(freeBefore)` after the batch | extended-in-place |
| `ApertarCoreApp::start` / `stop` / `stopMediaWatcher` | :8010-8050, :11055 | starts and joins five new threads (trim, merge, pre-roll, buffer events, safety stop) | extended-in-place |
| Constructor | :7988 | sets `safetyStopHook()` | extended-in-place |
| `/api/state` and `settingsBody` | :9583-9586, :309, :393 | new members | extended-in-place |
| `playback::listFrames` | ClipFrames.hpp:~110-160 (file is new in port; the list function reads root, then each `part_*`, names are paths inside the clip) | | new file, logic written with parts in mind |
| `ClipProbe` facts cache key | ClipProbe.hpp | adds last part's mtime when the clip has parts | extended-in-place (file is new in port) |
| delete, zip download, size, pre-roll delete, WebUI frame route | d7dd337 commit text says "already recursive or go through listFrames" | no code change | n/a (probable; commit message, not re-read per rule 5) |
| WebUI Settings page | WebControlPage.cpp (many ranges above) | cards, buttons, polling, pill | extended-in-place |

## 6. Removed, narrowed or hidden (everything upstream had)

| What | Where | Effect |
| --- | --- | --- |
| Nothing removed from the scope files (they are new). In existing files: no upstream line deleted for this unit that I could identify | | |
| Frames-mode behaviour kept as default | `buffer=frames` default | upstream's 12-frame queue behaviour is unchanged unless the operator or the file selects ram (confirmed: `planQueueBuffer` returns early at :5521) |
| Safety stop default narrows nothing in frames mode (off) | :5496 | in ram mode a take is ended at 90 % automatically (new behaviour, not a removal) |
| Pre-roll blocks commands | :12588 | capture, record, timelapse, media actions and standby refused for the pre-roll's ~2 s plus settle; the automatic ones run at Core start, mount, format (default on) |
| Split clips are hidden from tools that expect a flat clip | by design | a clip with `part_*` is not importable by Resolve/Premiere until the merge ran; README says so |
| Trim and merge pause during record, so a 60-s/5-min wait can follow a take | | by design |
| Pre-roll changes live frame rate and shutter for ~2 s via `applySettingsLocked(..., commit=false)` and restores them | `startStoragePreroll` | not saved, no settings event |

## 7. Board and environment assumptions

| Assumption | Where | Board/OS reading |
| --- | --- | --- |
| User `pi` | `config/apertar-media-trim.sudoers:4` | Raspberry Pi OS default user; other users need a different file |
| Paths `/home/pi/apertar-hardware.conf`, `/boot/firmware/...`, `/boot/...` | CameraController.cpp:2989-2999 | Pi OS layout; same list exists elsewhere in the port and upstream |
| Recording drive at `/media/<name>` | `apertar-media-trim` case `/media/*`, `*[!A-Za-z0-9._/-]*` | Core's `mediaRoot` default `/media/RAW` (media unit); a mount outside `/media/` is refused (exit 2) |
| `/usr/sbin/fstrim`, `timeout`, `mountpoint`, `findmnt`, `readlink`, `mktemp` | helper script | util-linux and coreutils on Debian; `/usr/sbin` path hard-coded |
| `/sys/block/<disk>/queue/discard_max_bytes`, partition naming `nvme0n1p2`, `sda1`, `mmcblk0p1` | helper | NVMe, USB and SD handled; no PCIe/RP1 assumption |
| exFAT, NVMe, 0.9 TB before a stall | helper header, `probe-exfat-dir.md`, `runMediaTrim` comment | tuned to the owner's Corsair MP600 Mini on `rpi-6.12.y` (Pi 5, `6.12.75+rpt-rpi-2712` in the probe), not generic; exFAT directory lock (`s_lock`) behaviour measured only on that kernel |
| exFAT create/rename cost: 5 entries per frame file, 63 ns per entry, 158 ns x N^2 per merge | FramePath.hpp, ClipMerge.hpp, ApertarCoreApp.cpp:11624 | measured on the Pi 5 + NVMe card; other filesystems (ext4, NTFS) not measured; `RENAME_NOREPLACE` stated for exFAT |
| `renameat2` via `SYS_renameat2` | merge executor | Linux 3.15+; fallback `lstat` + `rename` otherwise |
| RAM: `MemAvailable`, `MemTotal` from `/proc/meminfo`; fraction 0.6, floor 512 MiB, cap 0.5 x MemTotal; ram mode refuses below the 12-frame queue | BufferBudget.hpp | scales with board RAM; a 4 GB Pi, a 1 GB or 2 GB board give a small budget and fall back to frames; fixed numbers are tuned to 8/16 GB Pi 5 (probable) |
| Frame size hint `frameBytesHint_`, 4K 16-bit 25 fps examples in comments and tests | tests and comments | camera-mode dependent |
| Four cores: merge worker `setpriority(..., 10)` on its tid (`SYS_gettid`); writers `std::max(2u, std::min(4u, hardware_concurrency()))` (existing upstream) | :11640, CC :4318 | the pre-roll and trim need no core count |
| Pre-roll uses the sensor's maximum fps from the probe (`prerollMaximumFps`), `session_->setPrerollFps`; IMX585/IMX283 family via `session_->sensorFamily()` | CC :12040-12190 | sensor-family aware, not board-aware |
| Pre-roll only on raw formats (cDNG, Lossy DNG, MLV) | `StoragePrerollGuard` | |
| No gpiochip, I2C bus, fan, RP1 or PCIe-number reference in the scope (confirmed: grep of the scope files). `pcie_controller=1000110000.pcie` appears only in `tools/storage_buffer_conf_test.cpp:head` as a fixture (Pi 5 RP1 address `1000110000`) | tests | |
| `std::thread` count: this unit adds 5 threads to Core (trim, merge, pre-roll, buffer events, buffer safety stop) | | on a Pi with fewer cores they idle on cvs; the events thread wakes 4/s only while busy |

## 8. Gaps to check in stage 2 (not judged here)

| # | Question | Command |
| --- | --- | --- |
| G1 | Is `tools/*_test.cpp` wired into CMake? | `grep -n "_test\|add_test" /home/user/Apertar-Core/CMakeLists.txt` |
| G2 | Does the second `[storage]` reader (embedded Python configparser in `ApertarCoreApp.cpp`) match `parseBufferConf` on comments and case? | read the Python block near `buffer_ram_fraction=0.6` template (:5055) |
| G3 | Three near-identical `store.edit` blocks | diff :12829-12850, :12857-12895, :12900-12925 |
| G4 | Does `frameBufferGauge()` / `FrameBufferStatus` have an upstream equivalent? | `grep -rn "frameBuffer" /home/user/wt/core-upstream/src` (returned nothing for `frameBufferStatus`) |
| G5 | Pre-roll `Format` trigger and `FormatScope` use `trimNowMs` clock from the trim block | read :14620-14632 |
| G6 | UI side of F2/F6/F7 (`ApertarControlBridge.cpp`, `ClipFrameFiles.hpp`) belongs to a UI-side unit | |
| G7 | README text for trim install block conflicts with `config/apertar-media.sudoers` style (`apertar-media-tune` is also a port helper, other unit) | |
