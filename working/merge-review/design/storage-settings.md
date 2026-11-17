# Storage and recording settings: where they live and how they travel: design

Final plan. Read at Apertar-Core `core-work` `0d13a6f` and Apertar-UI `ui-work` `ac1fc28` (port plus the fixes so far, including the pre-roll default off `0977dd6` and the Lossy DNG drop `615b48c`), against upstream 1.6.0 Core `35dbe67` and UI `43888e5`. Port line numbers are `@0d13a6f` unless marked `@7dc6f7a` (the first draft's base; those anchors drift by 2-5 lines and are re-grepped before each commit). Upstream line numbers are `@upstream-1.6.0`. The first draft and a second reader's challenge were checked against the code; what changed is in the last section.

## In short

1. Today the port keeps five operator switches (write buffer, frames per folder, clip merge, automatic pre-roll, drive trim) in three stores: `[storage]` and `[media]` of `apertar-hardware.conf`, and `camera_settings.conf`. Each switch also has an `APERTAR_*` env twin that silently wins, and four `*_env` state fields tell the UIs about it.
2. The camera side opens the hardware file by itself: `[storage]` at every take, `[camera]` once, from a candidate list that includes `/boot`, while App's store only knows `/home/pi`. A media tuning file family (two INI files, a 487-line Python editor, a tmpfiles rule) feeds eight write-path knobs. Its env vars still win over it.
3. Live state crosses from the recorder to App through header singletons and two `std::function` globals: the safety stop, the flush abort, the gauge, the buffer note, the pre-roll state, the media root and the media snapshot.
4. In the target, the five switches are `CaptureSettings` fields in `camera_settings.conf`, where `media_trim` already lives (recipe R2). Their setters only store the field (upstream's no-session branch of `setTuningFile`), so they work in standby and before the camera starts. Command names and arguments stay; the command-plane theme owns the argument form.
5. Old hardware-file keys are applied once in `App::start` before any worker starts, and removed from the file in the T37 block after `adopt()`. A `/boot`-only file is applied at every start and gets a validator warning.
6. The RAM budget numbers, the safety-stop percent and the write-path tuning become env knobs only, read where they are used (R8). The Clear HDR ISO caps become constants. The media tuning file family goes if the owner agrees (decision 3).
7. The gauge, the safety-stop latch and the flush abort become members of the write queue, read through `session_` like upstream's `RecordingFailure`. The latch sends one `buffer` event through the session's event callback (upstream's `photoWriter_.setErrorCallback` shape). App's `handleTriggerEvent` wakes `wait()`, and `wait()` stops the take. The safety-stop thread, both globals and every header singleton of this theme go.
8. 24 Core commits, no UI commit. About -2 040 / +435 lines. Most of the removal is the tuning file family and the two hand parsers.

## How it works in the port today

"App" = `src/ApertarCoreApp.cpp`, "CC" = `src/camera/CameraController.cpp`, "CCH" = its header, "WCP" = `src/web/WebControlPage.cpp`, "ACB" = Apertar-UI `src/ApertarControlBridge.cpp`, "BB" = `src/util/BufferBudget.hpp`, "SP" = `src/util/StoragePreroll.hpp`.

### Operator switches and tuning values

| Value | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| Write buffer `frames`/`ram` | `set_buffer_mode` App:12846-12871, via `hardware::configStore().edit(...)` with `flags.trusted`; WebUI Config text save; `set_controls` | 1. App `refreshBufferRequest` App:273-286 parses the store text (`/home/pi` only) and publishes `bufferSettingStorage()` (BB:276-301). 2. CC `planQueueBuffer` opens the file itself through `loadBufferConf` CC:2989-3006 (env path, `/home/pi`, `/boot/firmware`, `/boot`) at each take start. 3. The env twin `APERTAR_CDNG_BUFFER` wins | Command thread under `commandMutex_`; take start under CC `mutex_` and the queue mutex | `apertar-hardware.conf` `[storage] buffer=` | `buffer_setting` in `bufferSettingMembers` App:252-269, appended to `settingsBody` (App:393), the `buffer` event, `/api/buffer`, `/api/state`. WebUI WCP:13847, :15469; touch UI ACB:2676-2684 via `applyBufferState`, fed by `buffer` events (ACB:1345) and by `applyCoreState` (ACB:1732) from settings events and replies |
| Frames per folder | `set_frames_per_folder` App:12875-12911 (one block with `set_clip_merge`), through the store; allowed while recording | 1. App refresh into the static `framesPerFolderRequest()` BB:323-327, for state only. 2. CC `startAtFolder` reads the file again at each take. 3. Env twin `APERTAR_CDNG_FRAMES_PER_FOLDER` | As above | `[storage] frames_per_folder=` | `frames_per_folder`, `frames_per_folder_env` (App:265-266). WebUI WCP:16198, :20758. Touch UI: none |
| Clip merge | `set_clip_merge enabled=` (same block) | App merge worker: `clipMergeMayRun` App:11707 and `runClipMerge` read the static `clipMergeRequest()` BB:335-339; env twin `APERTAR_CLIP_MERGE` | Merge worker thread; atomic | `[storage] clip_merge=on\|off` | `clip_merge_enabled`, `clip_merge_env_off` (App:267-268). WebUI WCP:16217. Touch UI: none |
| Automatic pre-roll | `set_storage_preroll value=on\|off` App:12917-12944 (its own lower-case parse) | 1. `requestStoragePreroll` App:11152-11173 parses the store text at each request. 2. `refreshBufferRequest` publishes `prerollState().automatic` (SP) for state. 3. Env twin `APERTAR_STORAGE_PREROLL` | Watcher or command thread; atomics | `[media] preroll=` (default off since `0977dd6`) | `storage_preroll_auto`, `storage_preroll_auto_env` (App:261-262). WebUI WCP:15842-15847, the 4 Hz `/api/buffer` loop WCP:16515-16518; touch UI ACB:617-630 (`set_storage_preroll value=`), :2736-2750 |
| Pre-roll length | text only | `storagepreroll::effectiveSeconds(seconds, conf)` App:11170 | as above | `[media] preroll_seconds=` | nowhere |
| Drive trim | `set_media_trim` App:13210-13217 calls `camera_.setMediaTrimEnabled` (CC:11887-11893, through `applySettingsLocked`, so refused in standby) **and** stores App's own copy `mediaTrimSetting_` (also set at App:8077) | `trimMedia` App:11445-11447, :11467 read the App copy; the env twin `APERTAR_MEDIA_TRIM` (App:6404) wins | Command thread; atomic copy | `camera_settings.conf` `media_trim=true\|false` (CC:889-890, writer CC:976); carried across formats | `system.media_trim_enabled`, `system.media_trim_env_off` (App:9588-9589). Not in `settingsBody`. WebUI WCP:16190 |
| RAM budget fraction, floor, max fraction | text only | `planQueueBuffer`: env > file > default | Take start | `[storage] buffer_ram_fraction`, `_floor_mb`, `_max_fraction`; the template ships them (App:5057-5059) | journal plan line |
| Safety-stop percent | text only | `planQueueBuffer` `publishStop`: env `APERTAR_CDNG_BUFFER_STOP_PERCENT` > file > 90 (ram) / 0 (frames) | Take start | `[storage] buffer_stop_percent` | `buffer_stop_percent` (App:258); touch UI message |
| Clear HDR ISO caps | text only | `loadCameraSection` CC:2943-2984 (a third INI dialect: strips all whitespace), cached once; `clearHdrIsoCap` | Configure time | `[camera] clear_hdr_iso_max_12bit/16bit`; template App:5078-5083 | `iso_max` (indirectly) |
| Validator rules | - | `hwconf::validate` HardwareConfigText.hpp:830-845 (`bufferConfProblem`, `prerollConfProblem`); section entries `camera` :58, `storage` :66, `media` :67. There is no unknown-key check: `knownKey` (:451) is used only by `checkEdits` (:496) | WebUI Config pane | - | Config pane issues |

The template the port writes for a new camera ships live `buffer=frames` and `buffer_ram_*` lines and commented `frames_per_folder`, `clip_merge`, `[media] preroll` lines (App:5052-5076).

### Live state between the recorder and App

| Value or path | Who writes | Who reads | Thread and lock | Shown where |
| --- | --- | --- | --- | --- |
| Gauge (used, capacity, ram, active, framesMode) | `DngRecordingQueue` through the function static `frameBufferGauge()` CC:4172-4186 | `CameraController::frameBufferStatus` CC:12530-12555 (lock-free, plus a `try_lock` for the mode); `rawTakeActive` CC:12557-12560 | Queue mutex on write; atomics on read | `buffer_used/_capacity/_fill/_mode/_unit` via `bufferMembers` App:300-311; `buffer` event; `/api/buffer` |
| Buffer plan note | `planQueueBuffer` through `publishBufferSetting` (BB) | `bufferSettingMembers` App:252-269 | Static mutex `bufferSettingMutex()` (BB) | `buffer_note` |
| Safety-stop latch | Queue `enqueue` CC:5011-5022 sets the static `bufferbudget::safetyStopState()` and calls the global `safetyStopHook()` under the queue mutex. The hook is assigned in App's constructor body App:7991-7998 and copies `used`, `capacity`, `ram` | App thread `runBufferSafetyStop` App:11087-11115 (cv + 100 ms backstop) logs `safety stop at N % (used/capacity MiB)` and sends `record_stop` through `dispatchHardwareInputCommand` (App:10121-10129, synchronous). `stopRecording` CC:12447 reads the static to send REC-off early. `clipMergeMayRun` App:11710; `/api/buffer` | Queue mutex, atomics, App's own cv | `buffer_safety_stop`, `buffer_stop_percent` |
| Flush abort | The queue registers `[this]{ return abortSafetyFlush(); }` in the global `flushAbortFunction()` (BB) at take start CC:4271 and unregisters at CC:4211, :4594 | `abortSafetyStopFlushForRecord` App:291-299, called first in `dispatchHardwareInputCommand` (App:10123) and before `commandMutex_` | Registry mutex, then the queue mutex. The drain holds `commandMutex_` and CC `mutex_` | `buffer_flush_discarded` |
| Pre-roll live state | `runStoragePrerollOnce` writes `prerollState()` (SP) | `bufferSettingMembers`, `runBufferEvents`, `clipMergeMayRun` App:11709 | Atomics plus a static mutex | `storage_preroll_active/_fps/_last` |
| Buffer events | App thread `runBufferEvents` App:10997-11052 polls everything above every 250 ms (1 s idle) and publishes a full `buffer` event on each change | Touch UI `buffer` event ACB:1345-1349 | Own thread; no controller lock | Buffer bar on touch and HDMI; WebUI polls `/api/buffer` at about 4 Hz |
| Media root | `CameraController::start` sets the static `configuredMediaRoot()` MediaProfile.hpp:214-218 at CC:10545 | `mediaExtraRawBuffersForConfiguredRoot` (:222-225), `mediaTuneForConfiguredRoot` (:230-234); the latter is called at CdngEncoder.cpp:91, CC:1467, :4364, :4718 | None | - |
| Media snapshot | Watcher `updateCachedMediaSnapshot` App:10893 into statics MediaProbe.hpp:257-290 | `rawCameraBufferCount` CC:1458-1470; `recorder_.setMediaProfile(detectMediaProfile(cachedMediaSnapshotOrProbe(mediaRoot)))` CC:7737; App:11328. Before the watcher's first cycle, `cachedMediaSnapshotOrProbe` probes directly (MediaProbe.hpp:285-290) | Static mutex | - |

### Media tuning file family and env knobs

| Value | Who writes | Who reads | File | Default without file |
| --- | --- | --- | --- | --- |
| `dontneed` | `scripts/apertar-tune` (Python, 487 lines) or by hand | `dngPageCacheDrop` CdngEncoder.cpp:84-108: env > file > `sync`, once per process | `/home/pi/apertar-media-tune.conf`, `/run/apertar-media/media-tune.override.conf`, parsed by `src/util/MediaTune.hpp` (318 lines) | `sync` (1.6.0: drop in the writer, CdngEncoder.cpp:1777@upstream) |
| `writeback` | same | CC:4715-4720: env > file > on, once per process | same | on (1.6.0: none) |
| `sync_ms` | same | CC:4363-4377 at each take | same | 1000 (1.6.0: no sync thread) |
| `raw_buffers`, `extra_raw_buffers` | same | `rawCameraBufferCount` CC:1458-1470; `deriveMediaProfile` MediaProfile.hpp:192-203 | same | base + 2 on vfat/NTFS (1.6.0: base) |
| `workers`, `queue` | same | `deriveMediaProfile` into `mediaProfile_.writer`, used CC:4314-4328 | same | 2 / 16 on vfat/NTFS (1.6.0: `max(2, min(4, threads))` / 12) |
| `kernel_tune` | same | `applyMediaTuning` (root helper `apertar-media-tune`) | same | off |
| Template, editor, tmpfiles | repo | - | `config/apertar-media-tune.conf`, `scripts/apertar-tune`, `config/apertar-media.tmpfiles.conf` (also the eject flags and the helper's state dirs); README table of 13 knobs | - |

Also on by default on a stock camera: drive trim (`CaptureSettings::mediaTrimEnabled = true`, `include/apertar/core/Types.hpp:140`).

## How original Apertar does this kind of thing

| Kind of problem | Precedent `@upstream-1.6.0` | What it shows |
| --- | --- | --- |
| A persisted switch that shapes recording | `CaptureSettings` `include/apertar/core/Types.hpp:124-162`; load chain CC:616-735; save CC:745-777; setter `setCdngCompression` CC:7973-7983 (`recording_` refusal, then `applySettingsLocked`); three serialisers (recipe R2) | One field, one setter, one `set_*` command that replies `settingsBody(camera_.settings())`. `CameraController` owns `camera_settings.conf` (CMD-12) |
| A setter that only stores | `setTuningFile`, no-session branch CC:8077-8084: `settings_ = next; ... persistSettingsLocked(); lastError_.clear(); emitSettingsEventLocked(); return true;`; `start` CC:7646-7647 persists the same way | A field the session does not need is assigned, saved and announced without touching the sensor |
| A setting kept across record formats | `setRecordingFormat` CC:7939-7955 carries `tuningFile`, `timecodeMode`, `exposureMetering` by hand (CAM-40) | The port does the same for `mediaTrimEnabled` (CC:11349, :11368@7dc6f7a) |
| A retired key in a settings file | `wb_locked` read into a local (CC:625, :682) and mapped after the loop (CC:726-728); the next whole-file save drops it (CMD-14) | Old values are read where they were and taken over |
| A legacy location of another file | `SettingsBridge.cpp:1943-1957@ui-upstream` reads the old presets directory in place and never moves it | Upstream never rewrites a file unprompted at start |
| App syncs a value into the camera at start | `App::start` App:6845-6856: reads UI.conf, calls `camera_.setStillExposureMode` / `applyCapturePreset` before the control server starts | A start-up takeover is App's job, done with the camera's setters |
| The hardware file's candidate paths | Every hardware class tries the env path, `/home/pi`, `/boot/firmware`, `/boot` (`src/hardware/GpioInput.cpp:67-68`, `TriggerOutput.cpp:80-81`, App:4258-4259) | The first file found is the config. The port keeps this list in `hardwareConfigCandidatePaths()` App:4924-4942 |
| App-side operator switches | `handleUiToggle("set_record_audio_enabled", "recordAudioEnabled")` App:9478-9491, :9642; read at use App:2774; the touch UI writes UI.conf itself (`SettingsBridge.cpp:1288-1297@ui-upstream`) | The other store for switches only App acts on (decision 1) |
| A bench knob | `unsignedEnvValue`, `boolEnvValue` CC:1027-1061; `maxQueuedFrames_ = unsignedEnvValue("APERTAR_CDNG_QUEUE_FRAMES", defaultQueueFrames, 4, 64)` CC:3328-3330 (R8, CAM-24) | Env only, read where used, never in a settings file, the socket API or the README |
| A bench file | `tuningOverride(name)` `src/prores/ProresEncoder.cpp:771-813`: env wins, else `NAME=VALUE` from `/home/pi/.apertar-tuning`, re-read at clip open | Upstream's one tuning file (decision 3 b) |
| A sensor or format limit | `settings.iso = std::min<uint32_t>(settings.iso, 800u);` CC:2483 | Limits are literals |
| Take-scoped state of a worker | `RecordingFailure failure_` is a recorder member (CC:3901), read through `session_->recordingError()` (CC:5891, :8524). `RecordingDropWarning` is a controller member passed to the queue by pointer (CC:7576-7584, :5237) and read lock-free (`CCH:87`) | No globals; `session_` is created once and never reset |
| A worker that sends an event | `photoWriter_.setErrorCallback([this](const std::string &error){ if (exposureEvent_) exposureEvent_(...); })` in the `CameraSession` constructor CC:5245-5250; `markDropped` fires `recording_health` under the queue mutex CC:3535-3536 | A worker reaches the event stream through the session's callback |
| App reacting to a camera event | `publishEvent` -> `handleTriggerEvent` App:10823-10825, :10854-10870 (`still_exposure`, `recording`, `photo_capture` drive the LED and trigger) | App acts on events by content. No new constructor parameter |
| Periodic supervision | `checkRecordingFailure` polled by `wait()` App:7029-7034 and at `handleCommand` entry App:9094; `requestShutdown` App:11016-11023 sets its flag under `waitMutex_` and notifies `waitCv_` | `wait()` is where a background condition ends a take |
| Process-wide statics | `captureSettingsPersister()` CC:884-889 | File-local one-offs in the owner's `.cpp`, never shared mutable state in a header (CAM-27) |
| The media root | `start(const std::string &mediaRoot, ...)` stores `mediaRoot_`; `session_->startRecording(mediaRoot_, settings_, ...)` CC:8247 | The controller passes its member down |
| Page-cache drop | `::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);` after every cDNG (`src/cdng/CdngEncoder.cpp:1777`) and Lossy DNG (`src/lossydng/LossyDngEncoder.cpp:82`) | Unconditional writer-side drop; no sync thread (CAM-37) |
| Scheduling | `config/apertar-core-capture-priority.conf` `LimitNICE=-5`; `scripts/start-apertar-core.sh:21` plain `exec` | No RT (PLT-14) |
| `[storage]` | `mount_path`, `pcie_controller` only (template App:4308-4310) | Wiring for the automounter and the PCIe reset |

No upstream precedent at all: a RAM-sized write queue, a safety stop, a flush abort during a drain, split clip folders and their merge, an automatic test take, a drive trim. See "What stays as new ground".

## The target

### Rule the target follows

- **Operator switches about recording and storage** (write buffer, frames per folder, clip merge, automatic pre-roll, drive trim) are `CaptureSettings` fields in `camera_settings.conf`, like `media_trim` today (decision 1 keeps the alternative open). `CameraController` owns them. Each has one store-only setter (upstream CC:8077-8084 shape), one command, and the three settings serialisers. They are carried across format profiles. New keys are written `<< s.member` and read `std::stoul(value) != 0`, as upstream does for `iso_auto` (CC:749, :659-660).
- **Commands keep their names and arguments.** `set_buffer_mode value=`, `set_frames_per_folder value=`, `set_clip_merge enabled=`, `set_storage_preroll` (argument as the command-plane theme leaves it), `set_media_trim enabled=`. Each now replies `settingsBody(camera_.settings())` (CMD-5).
- **Recorder tuning** is env only, read where used (R8).
- **Driver facts** are constants in CC (the Clear HDR ISO caps).
- **Take-scoped live state** (gauge, plan note, safety-stop latch, flush abort) is write-queue members, read through `session_`. The latch sends one event through the session's event callback; App reacts in `handleTriggerEvent`; `wait()` stops the take.
- **The hardware file** keeps `[storage] mount_path` and `pcie_controller` only, as in 1.6.0.

### Before and after

| Value | Before | After: store and key | Command | Reaches |
| --- | --- | --- | --- | --- |
| Write buffer | `[storage] buffer`; App edits; CC re-reads; env twin | `camera_settings.conf` `buffer_setting=frames\|ram`; `CaptureSettings::writeBuffer` (`enum class WriteBuffer { Frames, Ram }` + `toString`) | `set_buffer_mode value=frames\|ram`: `camera_.setWriteBuffer`, refused while recording (CAM-31) | `buffer_setting` in `settingsBody`, `settingsEvent`, web state settings. Touch UI unchanged (`applyCoreState` -> `applyBufferState`). Leaves `bufferSettingMembers`, so `/api/buffer` and the `buffer` event lose it |
| Frames per folder | `[storage] frames_per_folder`; read twice; env twin | `frames_per_folder=N`; `CaptureSettings::framesPerFolder` (0 or 100..100000) | `set_frames_per_folder value=N`: refused while recording | settings serialisers |
| Clip merge | `[storage] clip_merge`; static atomic; env twin | `clip_merge_enabled=0\|1`; `CaptureSettings::clipMergeEnabled = true` | `set_clip_merge enabled=`; then `clipMerge("switch")` when on | settings serialisers |
| Automatic pre-roll | `[media] preroll`; parsed per request; env twin | `storage_preroll_auto=0\|1`; `CaptureSettings::storagePrerollAuto = false` | `set_storage_preroll` (name and argument as command-plane 12 leaves them) | `storage_preroll_auto` in settings serialisers (touch UI ACB:2736 unchanged) |
| Pre-roll length | `[media] preroll_seconds` | constant `storagepreroll::kDefaultSeconds` (2); `storage_preroll seconds=` stays | - | - |
| Drive trim | `media_trim` + App copy + env twin | unchanged key `media_trim` (existing writer line kept); App reads `camera_.settings().mediaTrimEnabled`; setter becomes store-only | `set_media_trim enabled=` | `media_trim_enabled` moves from `system` into the settings serialisers |
| RAM fraction, floor, max | `[storage]` keys + env | env only `APERTAR_CDNG_QUEUE_RAM_FRACTION`, `_FLOOR_MB`, `_MAX_FRACTION` in `planQueueBuffer` | - | journal plan line |
| Safety-stop percent | `[storage] buffer_stop_percent` + env | env only `APERTAR_CDNG_BUFFER_STOP_PERCENT` | - | `buffer_stop_percent` status field |
| Clear HDR ISO caps | `[camera]` + own parser | `constexpr uint32_t kClearHdrMaxIso12 = 720, kClearHdrMaxIso16 = 1585;` beside `kLosslessMaxIso` | - | `iso_max` |
| Gauge + plan note | static `frameBufferGauge()`, static `bufferSettingStorage()` | `DngRecordingQueue` atomics `levelUsed_`, `levelCapacity_`, `levelRam_`, `levelActive_`; note under a small `noteMutex_`; `CameraSession::bufferLevel()` forwards (zeros without libcamera); `framesMode` cache becomes a CC atomic member | - | same fields through `frameBufferStatus()`, `bufferNote()` |
| Safety-stop latch | static `safetyStopState()` + global hook + App thread | queue atomics `safetyStopActive_`, `flushDiscarded_`, `stopPercent_` (exists), and at fire time `stopUsed_`, `stopCapacity_`, `stopRam_`, `stopFiredMs_`; `CameraController::bufferSafetyStop()` returns them as a struct, lock-free through `session_`. On fire the queue calls a callback the session sets (photoWriter_ shape), which sends `{"event":"buffer","buffer_safety_stop":true,"buffer_stop_percent":N}` | - | same fields |
| Safety-stop reaction | App thread + hook | `handleTriggerEvent`: a `buffer` event with `"buffer_safety_stop":true` sets `bufferSafetyStopPending_` under `waitMutex_` and notifies `waitCv_` (the `requestShutdown` shape). `wait()` wakes, and stops the take only when `camera_.bufferSafetyStop().active && camera_.isRecording()`. It checks that each 1 s tick too | - | journal line with the delay |
| Flush abort | global registry | `CameraController::abortSafetyStopFlush()`: takes **no** controller `mutex_`, forwards through `session_` to `recorder_.abortSafetyFlush()` (queue mutex only) | - | `buffer_flush_discarded` |
| Pre-roll live state | static `prerollState()` | the preroll theme (its commit 10 moves it into CC) | - | - |
| Media profile | statics `configuredMediaRoot()`, `cachedMediaSnapshot*()` | `CameraController::setMediaProfile(const MediaProfile &)` under a small `mediaProfileMutex_` (not `mutex_`). App calls it once before `camera_.start()` and wherever the watcher changes `mediaProfile_` | - | - |
| Media tuning file family | 2 INI files, editor, template, README table | decision 3. With a): env only at each read site (`APERTAR_DNG_DONTNEED`, `APERTAR_DNG_WRITEBACK`, `APERTAR_MEDIA_SYNC_MS`, `APERTAR_RAW_CAMERA_BUFFERS`, `APERTAR_CDNG_UNCOMPRESSED_WORKERS`, `APERTAR_CDNG_QUEUE_FRAMES`, `APERTAR_MEDIA_TUNE`) | - | effective values on the `ApertarCore recording clip:` line |

### Why the setters only store

`applySettingsLocked` refuses in standby (CC:12743-12746, "Wake the camera before changing capture settings."), refuses during the pre-roll (CC:12747-12750), pushes `session_->applyControls` (CC:12766), and sets `state_ = Error` when that fails (CC:12782). Before `camera_.start()` the session has no camera, so `applyControls` fails ("Camera is not open.", CC:7570-7572). Upstream's recorder-only setter `setCdngCompression` does go through it (CC:7973-7983@upstream), but none of the five new fields is read by the session: the queue reads them from the settings it gets at `startRecording`. The store-only shape (CC:8077-8084@upstream) is therefore used:

```cpp
bool CameraController::setWriteBuffer(WriteBuffer mode)
{
    std::lock_guard<std::mutex> lock(mutex_);
    if (recording_) {
        setErrorLocked("Stop recording before changing the write buffer.");
        return false;
    }
    settings_.writeBuffer = mode;
    persistSettingsLocked();
    lastError_.clear();
    emitSettingsEventLocked();
    return true;
}
```

The field survives later session pushes: all seven `settings_ = session_->currentSettings()` sites (CC:10556, :10629, :11553, :11565, :12716, :12778, :12794) follow a `start`, `reconfigure` or `applyControls` that was given a copy of the controller's own `settings_` (or an older controller copy on recovery), and `applyControls` stores the whole sanitised struct (CC:7598). Confirmed by reading; a host check is not possible, the `--simulate` round-trip in commit 3 covers the no-libcamera path.

Reading `camera_.settings()` from App's workers takes `mutex_`, which a RAM drain holds for seconds. This adds no new kind of wait: the watcher and the merge worker already call `camera_.isRecording()` (App:10904, :11708), which takes the same mutex (CC:12631-12635). The comment at App:11700 ("Takes no lock the command path holds") is wrong today and is corrected in commit 6.

### How old files are taken over

- **camera_settings.conf.** New keys are read with the usual `else if (key == ...)` branch. A missing key keeps the `CaptureSettings` default, which is today's default. `media_trim` keeps its key and its writer line.
- **apertar-hardware.conf**, step 1, apply. One block in `App::start` before the first worker starts (before App:8031). Camera settings are already loaded (CC constructor, CC:10510). The block reads the first existing file of `hardwareConfigCandidatePaths()` (App:4924) with `hwconf::valueOf(hwconf::parse(text), section, key)`. For each switch key present (`[storage] buffer`, `frames_per_folder`, `clip_merge`, `[media] preroll`), it calls the store-only setter and logs `ApertarCore settings: [storage] buffer=ram moved to camera settings`. For each tuning key present (`buffer_ram_*`, `buffer_stop_percent`, `[media] preroll_seconds`) it applies nothing and, if the value differs from the default, logs the env var that replaces it. The watcher's Core-start pre-roll request (App:10947-10963) and the merge worker's first scan then already see the moved values.
- **Step 2, remove.** Inside the T37 block, after `store.adopt()` (App:8148), only when step 1's file is `store.path()`: one `store.edit(store.currentRevision(), {Unset ...}, "core", backup = true, trusted = true)` removes the keys it found, and `[media]` when it is left empty. Then `appliedHardwareText_ = store.currentText()`, so the controls worker sees no foreign change (App:8121). The store keeps `<file>.bak` and its history. This is the store's own key edit (HW-8), done once (decision 10).
- **A `/boot`-only file.** The store never looks at `/boot` (`HardwareConfigStore.cpp:118-123`), so Core cannot edit it. Step 1 applies the old values at every start and logs once: `ApertarCore settings: /boot/firmware/apertar-hardware.conf still holds [storage] buffer; delete it there, Core applies it at every start`. The validator warning of commit 10 shows the same keys in the Config pane.
- **A fresh camera** gets the template without these keys (each commit removes its own template lines), so nothing is taken over and nothing is written.

### Who reads what after the change

| Reader | Reads |
| --- | --- |
| `DngRecordingQueue::startAtFolder` | `settings.framesPerFolder` (not for MLV, not for the pre-roll take, as today) |
| `DngRecordingQueue::planQueueBuffer` | `settings_.writeBuffer`; `APERTAR_CDNG_QUEUE_RAM_*` and `APERTAR_CDNG_BUFFER_STOP_PERCENT` at the call |
| App merge worker | `camera_.settings().clipMergeEnabled`; `camera_.bufferSafetyStop().active` |
| App pre-roll request | `camera_.settings().storagePrerollAuto` |
| App trim | `camera_.settings().mediaTrimEnabled` |
| `bufferMembers` (state, `buffer` event, `/api/buffer`) | `camera_.frameBufferStatus()`, `camera_.bufferNote()`, `camera_.bufferSafetyStop()`; pre-roll status until the preroll theme moves it. After commit 15 these are status fields in `get_state` before `settingsBody` |

## Commit plan

Each commit lands with both builds green (`/home/user/build/bin/check_core.sh <tree> <tag> both tests`: libcamera ON and OFF, plus the host tests in `tools/`). `smoke_core.sh <bin> <port>` is diffed against the previous commit: only port-only fields may move or vanish; every 1.6.0 field stays with its type. "Pi" = what only the camera shows. Socket calls on the Pi: `printf '{"id":1,"cmd":"get_state"}\n' | socat - UNIX-CONNECT:/tmp/apertar-core.sock`. Anchors are re-grepped before each commit.

### 1. core, web: the storage switches have no environment twins
- Touches: `App` `refreshBufferRequest` env arguments App:273-286; `bufferSettingMembers` App:262, :266, :268; `mediaTrimEnvOff` App:6404-6409 and its uses (App:11447, :11467, :11947); `requestStoragePreroll` App:11158-11163; `/api/state` App:9589. `BB` env parameters of `requestedBufferMode`, `requestedFramesPerFolder`, `clipMergeEnvOff`, `requestedClipMerge`. `SP` `automaticEnabled`, `publishAutomatic`, `automaticFromEnv`. `CC` env reads in `startAtFolder` and `planQueueBuffer`. `WCP` "Set by APERTAR_..." / "Forced off by ..." texts and their disable logic (around :13859, :15845, :16190, :16198, :16217, :16517). Tests `tools/storage_buffer_conf_test.cpp`, `tools/storage_preroll_test.cpp` env cases; README env rows.
- Deletes `APERTAR_CDNG_BUFFER`, `APERTAR_CDNG_FRAMES_PER_FOLDER`, `APERTAR_CLIP_MERGE`, `APERTAR_STORAGE_PREROLL`, `APERTAR_MEDIA_TRIM` and the fields `frames_per_folder_env`, `clip_merge_env_off`, `storage_preroll_auto_env`, `media_trim_env_off`.
- Lines: -110 / +15.
- Here: builds, host tests; smoke diff shows only the four `*_env` fields gone; headless Chromium on `--simulate`: the Media and Storage cards render, the toggles are enabled.
- Pi: `systemctl cat apertar-core | grep -E 'APERTAR_(CDNG_BUFFER|CDNG_FRAMES|CLIP_MERGE|STORAGE_PREROLL|MEDIA_TRIM)'` prints nothing. If it prints a line, set the same value through the UI before updating.
- Depends on: nothing.

### 2. camera: the Clear HDR ISO caps are constants again
- Touches: CC:2933-2984 and the `cameraSection()` cache: `CameraSection`, `loadCameraSection`, `cameraSection` deleted; two `constexpr` beside `kLosslessMaxIso`; `clearHdrIsoCap` returns them. Template `[camera]` block App:5078-5083 deleted. `HardwareConfigText.hpp:58` `camera` entry deleted, so a leftover `[camera]` gets the existing `unknown_section` warning (:806-811, "no reader uses it"). README `[camera]` text. No takeover: the values were never settings.
- Lines: -65 / +4.
- Here: builds, tests; `--simulate` with `APERTAR_HARDWARE_CONFIG=<tmp>` holding `[camera]`: the Config pane shows the `unknown_section` warning.
- Pi: `set_raw_bit_depth value=12`, `set_clear_hdr enabled=true`, `get_state`: `iso_max` 720. At 16-bit: 1585.
- Depends on: the parallel 12-bit Clear HDR fixes. If they change the 12-bit cap, they change the constant.

### 3. camera, core: the write buffer is a camera setting
- Touches: `Types.hpp` `enum class WriteBuffer { Frames, Ram }`, `toString`, field `writeBuffer`. `CC`: loader branch `buffer_setting` beside `media_trim` (CC:889); writer line `<< toString(s.writeBuffer)` (CC:976); carry-over in `setRecordingFormat`; store-only `setWriteBuffer` (shape above, `recording_` refusal); `settingsEvent` line beside `preview_tdn` (CC:163ff); `planQueueBuffer` reads `settings_.writeBuffer` for the mode, the rest of `loadBufferConf()` stays until commit 9. `App`: `settingsBody` line and web-state settings line; `set_buffer_mode` block App:12846-12871 becomes the CMD-5 shape (value test, `camera_.setWriteBuffer`, reply `settingsBody`); `buffer_setting` leaves `bufferSettingMembers` (so no duplicate in `get_state`); template lines `buffer=frames` and its comment (App:5054-5057). `BB` `requestedBufferMode`, `publishBufferRequest` and the `setting` half of the snapshot deleted. `WCP`: `buffer_setting` is read from the state settings, not from `/api/buffer` (:13847, :15469); the patch `case` (:14034) stays.
- Lines: -55 / +40.
- Here: builds, tests; `--simulate`: `set_buffer_mode value=ram` replies `buffer_setting:"ram"` once; `get_state` holds the key once (`grep -o buffer_setting | wc -l` = 1); restart: still `ram`; `camera_settings.conf` has `buffer_setting=ram`; `enter_standby` then `set_buffer_mode value=frames` succeeds; WebUI pill flips. `check_ui.sh` builds unchanged.
- Pi: `set_buffer_mode value=ram`; a 4K take logs `ApertarCore buffer: ram budget ...`.
- Depends on: 1.

### 4. core: old hardware-file storage switches are taken over at start
- Touches: `App::start`: the apply block before App:8031 and the remove step after `store.adopt()` App:8148 (both described under "How old files are taken over"), with `[storage] buffer` as the only key. A local list `{section, key, setter}` that later commits extend by one row.
- Lines: -0 / +45.
- Here: builds; `--simulate` with `APERTAR_HARDWARE_CONFIG=<tmp>` holding `[storage] buffer=ram`: the log line appears, `get_state` says `ram`, the key is gone from `<tmp>`, `<tmp>.bak` exists, the second start logs nothing. With the file `chmod 444`: the value is applied, the log says it could not be removed.
- Pi: on the owner's camera (`buffer=ram`), the first start logs the takeover line, `get_state` says `buffer_setting:"ram"`, and `grep -n buffer= ~/apertar-hardware.conf` is empty.
- Depends on: 3.

### 5. camera, core: frames per folder is a camera setting
- Touches: `Types.hpp` field `framesPerFolder`. `CC`: loader, writer `<< s.framesPerFolder`, carry-over, store-only `setFramesPerFolder` (refused while recording); `startAtFolder` uses `settings.framesPerFolder` and no longer reads the file. `App`: `set_frames_per_folder` split out of the shared block App:12875-12911 (CMD-5 shape); three serialiser lines; takeover row; `frames_per_folder` leaves `bufferSettingMembers`; template comment lines. `BB` `framesPerFolderRequest`, `requestedFramesPerFolder` deleted. `WCP:16198` reads the settings.
- Lines: -45 / +30.
- Here: builds, tests (`frame_path_test` unchanged); `--simulate`: `set_frames_per_folder value=1000` round-trips through a restart; WebUI field shows 1000; takeover with `frames_per_folder=1000` in a test file.
- Pi: a 1-minute 4K take with 1000 produces `part_000`, `part_001`, ... and `.parts`; the playback list opens it.
- Depends on: 4.

### 6. camera, core: the clip merge switch is a camera setting
- Touches: `Types.hpp` `clipMergeEnabled = true`. `CC`: loader, writer, carry-over, store-only setter (no recording gate; the worker pauses by itself). `App`: `set_clip_merge` block (strict `enabled=` test kept, `camera_.setClipMergeEnabled`, then `clipMerge("switch")` when on, reply `settingsBody`); `clipMergeMayRun` App:11707 and `runClipMerge` read `camera_.settings().clipMergeEnabled`; the comment App:11700 states that `isRecording()` and `settings()` take the controller mutex; the `refreshBufferRequest()` call and comment at App:8036-8038 go; three serialiser lines; takeover row; `clip_merge_enabled` leaves `bufferSettingMembers`; template comment lines. `BB` `clipMergeRequest` deleted. `WCP:16217` reads the settings.
- Lines: -40 / +28.
- Here: builds, tests (`clip_merge_test` unchanged); `--simulate`: toggle off/on, restart, state agrees; a Core start with `clip_merge=off` in a test file never logs `clip merge: start`.
- Pi: record a split clip, switch merge on, idle: journal `ApertarCore clip merge: start ... done`.
- Depends on: 5.

### 7. camera, core: the automatic pre-roll switch is a camera setting
- Touches: `Types.hpp` `storagePrerollAuto = false`. `CC`: loader, writer, carry-over, store-only setter. `App`: the `set_storage_preroll` block App:12917-12944 keeps its name and its argument parse (as it is, or as command-plane 12 left it) and replaces the store edit with `camera_.setStoragePrerollAuto(on)`, reply `settingsBody`; `requestStoragePreroll` App:11152-11173 reads `camera_.settings().storagePrerollAuto` and `kDefaultSeconds`; three serialiser lines; takeover rows `[media] preroll` (applied) and `preroll_seconds` (logged); `storage_preroll_auto` leaves `bufferSettingMembers`; the `[media]` template block App:5071-5076 goes. `SP` `PrerollConf`, `parsePrerollConf`, `effectiveSeconds`' conf parameter, `publishAutomatic`, `prerollAutomatic` deleted. `WCP`: the Automatic pills read the settings (:15842-15847); the `/api/buffer` loop stops reading `storage_preroll_auto` (:16515-16516). `tools/storage_preroll_test.cpp`: conf cases out. The touch UI keeps working unchanged: it sends the same command and reads `storage_preroll_auto` from settings events and replies through `applyCoreState` (ACB:1732).
- Lines: -75 / +28.
- Here: builds, tests; `--simulate`: the toggle round-trips through a restart; with it off, `mount_media` logs `not requested`; with `[media] preroll=on` in a test file, the first start's Core-start request is made (log `reason=start`).
- Pi: switch on from the touch UI, reinsert the CFexpress card: journal `ApertarCore storage preroll: reason=mount ... ok`.
- Depends on: 6; command-plane 12 if it lands first (then only the store part changes here). The preroll theme owns the take.

### 8. core, web: drive trim reads the camera setting; App keeps no copy
- Touches: `CC` `setMediaTrimEnabled` CC:11887-11893 takes the store-only shape (today refused in standby). `App`: `mediaTrimSetting_` (`ApertarCoreApp.hpp`) and App:8077, :13216 deleted; `trimMedia` and the trim worker read `camera_.settings().mediaTrimEnabled`; `media_trim_enabled` moves from `system` App:9588 into the three settings serialisers. `WCP:16190` reads the settings.
- Lines: -12 / +10.
- Here: builds; `--simulate`: toggle, restart; toggle works in standby.
- Pi: `set_media_trim enabled=false`, delete a clip: no `ApertarCore media trim` line.
- Depends on: 1.

### 9. camera: the RAM budget numbers and the safety-stop percent are bench knobs only
- Touches: `planQueueBuffer` no longer opens the file: `APERTAR_CDNG_QUEUE_RAM_FRACTION`/`_FLOOR_MB`/`_MAX_FRACTION` and `APERTAR_CDNG_BUFFER_STOP_PERCENT` only, same defaults and bounds; `loadBufferConf` CC:2986-3006 deleted (its last caller). Takeover rows for the four keys (logged when not the default, removed). Template App:5057-5061 and comments. README.
- Lines: -35 / +12.
- Here: builds; `buffer_budget_test` unchanged; with a test file holding `buffer_stop_percent=50`, the log names `APERTAR_CDNG_BUFFER_STOP_PERCENT`.
- Pi: `journalctl -u apertar-core -b | grep 'ApertarCore settings'` on the owner's camera. If a value was not the default, put the env var in a drop-in.
- Depends on: 4.

### 10. core: the [storage] and [media] readers are gone; moved keys get a warning
- Touches: `BB` `BufferConf`, `bufferConfProblem` (all but what `parseStopPercent` uses), `parseBufferConf`. `App` `refreshBufferRequest` App:273-286 and its calls (the T37 block App:8149 and the other call sites, re-grep). `HardwareConfigText.hpp`: the `media` entry :67 goes (a leftover `[media]` gets `unknown_section`); the `storage` branch :830-838 becomes one warning, `moved_key`, shaped like `unknown_section`: "buffer on line N is a camera setting now; Core ignores it here. Delete the line." for the moved keys; the `media` branch :839-845 goes. The includes of `BufferBudget.hpp`/`StoragePreroll.hpp` in `src/hardware` (HW-config-text-store-F10). `tools/storage_buffer_conf_test.cpp` deleted; its `safetyStopReached` and `effectiveStopPercent` checks move to `tools/buffer_budget_test.cpp`.
- Lines: -260 / +20.
- Here: builds; host tests (one file fewer: 16); WebUI Config pane with `buffer=ram` in `[storage]`: one `moved_key` warning, no error.
- Pi: none beyond 3-9.
- Depends on: 3, 5, 6, 7, 9.

### 11. camera: the write queue's gauge and plan note live in the queue
- Touches: `FrameBufferGauge` and `frameBufferGauge()` CC:4169-4186 deleted; `DngRecordingQueue` gets the four level atomics and `noteMutex_` + `note_`; `CameraSession::bufferLevel()` and `bufferNote()` forward to `recorder_` (zeros and `""` without libcamera, CAM-28); `frameBufferStatus` and `rawTakeActive` read through `session_`; `framesMode` becomes a CC `std::atomic<bool>` member; new `std::string CameraController::bufferNote() const` (no controller mutex). `BB` `bufferSettingStorage`/`publishBufferSetting`/snapshot deleted; `bufferSettingMembers` reads `camera_.bufferNote()` (it becomes an App member function or takes the note as a parameter).
- Lines: -50 / +35.
- Here: both builds; `--simulate` `/api/buffer` shape unchanged.
- Pi: a take with the buffer bar on: the bar rises and falls; `buffer_note` shows the plan line in ram mode.
- Depends on: 10.

### 12. camera: the buffer safety stop is a latch in the queue that sends one event
- Touches: queue atomics `safetyStopActive_`, `flushDiscarded_`, `stopUsed_`, `stopCapacity_`, `stopRam_`, `stopFiredMs_` (steady-clock ms); every `bufferbudget::safetyStopState()` use (CC:4600, :4614, :4621, :5016-5017, :5441, :5490, :5517-5518, :12447) goes to them. `DngRecordingQueue::setSafetyStopCallback(std::function<void(const std::string &)>)`, set in the `CameraSession` constructor next to `photoWriter_.setErrorCallback` (CC:7266): on fire it sends `{"event":"buffer","buffer_safety_stop":true,"buffer_stop_percent":N}` through `exposureEvent_`. The comment CC:5011-5012 says that the callback runs under the queue mutex, as `markDropped` does upstream. `struct BufferSafetyStop` in CCH beside `FrameBufferStatus`; `CameraController::bufferSafetyStop()` (lock-free, through `session_`). App uses (App:255-259, `/api/buffer`, `runBufferEvents` App:11004-11019, `clipMergeMayRun` App:11710, `abortSafetyStopFlushForRecord` App:293) call it. The App hook call in `enqueue` stays until commit 13, fed from the queue values. `BB:222-234` deleted. `runBufferEvents` keeps its flip detection: it also reports the clear after the drain and `flush_discarded`.
- Lines: -40 / +45.
- Here: both builds; `buffer_budget_test`.
- Pi: `APERTAR_CDNG_BUFFER_STOP_PERCENT=50` in a drop-in, `buffer_setting=ram`, 4K 16-bit to a slow card: the take stops by itself; touch UI shows "The write buffer reached 50 %."; WebUI pill shows the flush.
- Depends on: 11.

### 13. core: wait() stops the take on a buffer safety stop
- Touches:
  - `handleTriggerEvent` (App:14928): a `buffer` event containing `"buffer_safety_stop":true` sets `bufferSafetyStopPending_` under `waitMutex_` and calls `waitCv_.notify_all()` (the `requestShutdown` shape, App:15090-15096).
  - `wait()` App:8289-8320: the predicate becomes `!running_ || shutdownRequested_ || bufferSafetyStopPending_`, and the loop breaks only on `!running_.load() || shutdownRequested_.load()` tested after the wait. A true predicate must not break the loop: `main` calls `app.stop()` when `wait()` returns (`src/main.cpp:129-134`). After `lock.unlock()`: `bufferSafetyStopPending_.exchange(false)`; then, on every tick, `if (const auto stop = camera_.bufferSafetyStop(); stop.active && camera_.isRecording())` log `ApertarCore buffer: safety stop at P % (U/C MiB) after D ms` (D = now - `stopFiredMs`) and `dispatchHardwareInputCommand(record_stop)`. The latch is cleared at each take start (CC:5490, :5518), so a stale event never stops a new take.
  - Deleted: `runBufferSafetyStop` App:11081-11115, its start App:8053-8056, its stop and join, the hook assignment App:7991-7998, members `bufferSafetyStopThread_`, `_Running_`, `_Mutex_`, `_Cv_`, `_Used_`, `_Capacity_`, `_Ram_` (the pending flag stays); `BB` `SafetyStopHit`, `safetyStopHook`; the hook call in `enqueue`.
- Lines: -70 / +22.
- Here: both builds; `--simulate` start and SIGTERM stop clean; a hand-sent `buffer` event cannot be injected, so the reaction is a Pi check.
- Pi: as in 12, then `journalctl -u apertar-core -b -o short-precise | grep 'safety stop at'`: one line per stop, pass = `after D ms` with D < 200. Then press REC: a new take starts and is not stopped. Worst case without the event: the 1 s tick.
- Depends on: 12. The preroll theme also adds blocks to `wait()` after `lock.unlock()` (its commits 4 and 6); the second of the two rebases.

### 14. camera: the safety-stop flush abort is a CameraController method
- Touches: `CCH` `int64_t abortSafetyStopFlush();` with the comment "No controller mutex: stopRecording holds it while the queue drains. session_ is never reset." `CC` forwards through `session_` to `recorder_.abortSafetyFlush()` (CC:4611-4624, queue mutex only); `#else` returns -1; `registerFlushAbort`/`unregisterFlushAbort` CC:4626-4636 and their calls CC:4211, :4271, :4594 deleted. `App:291-299` calls `camera_.abortSafetyStopFlush()`. `BB` `flushAbortFunction` deleted.
- Lines: -30 / +14.
- Here: both builds.
- Pi: during the safety-stop flush of 12, press REC: journal `flush aborted by record, N unwritten frames ... discarded`, a new take starts, `buffer_flush_discarded` = N.
- Depends on: 13. The command-plane theme decides whether the call stays before the lock (App-1-F13).

### 15. core: get_state carries the buffer status; settingsBody carries camera settings only
- Touches: `App:393` `<< "," << bufferSettingMembers()` leaves `settingsBody` and goes into the `get_state` body before `settingsBody` (CMD-11), next to `clipMergeStateJson()`. `bufferSettingMembers` is written as an `ostringstream` chain (CMD-9). What is left in it: `buffer_note`, `buffer_safety_stop`, `buffer_stop_percent`, `buffer_flush_discarded`, and the pre-roll status until the preroll theme moves it.
- Lines: -16 / +14.
- Here: smoke diff: `get_state` keeps every field once; `set_iso` replies lose only port status fields; the touch UI is still fed by `get_state` and the `buffer` event (ACB:1345-1349, :1732).
- Pi: none.
- Depends on: 3, 5, 6, 7, 11-14; rebase on preroll 9 if it lands first.

### 16. camera: the camera gets the media profile from App
- Touches: `CCH` `void setMediaProfile(const MediaProfile &profile);`, members `mediaProfileMutex_`, `mediaProfile_`. `App::start` before `camera_.start()` (App:8069): `camera_.setMediaProfile(detectMediaProfile(probeMediaRoot(options_.mediaRoot)))`, the same probe the first configure runs today. `runMediaWatcher` calls it where `mediaProfile_` changes (App:10940-10944). `rawCameraBufferCount(bool clearHdr, unsigned extra)` CC:1458-1470 takes the copy's `writer.extraRawBuffers` from its callers; CC:7737 uses the copy (passed from the controller). Deleted: `mediaExtraRawBuffersForConfiguredRoot` only. `configuredMediaRoot`, `mediaTuneForConfiguredRoot` and the snapshot statics stay until commit 17 (CdngEncoder.cpp:91, CC:1467, :4364, :4718 still call them).
- Lines: -15 / +25.
- Here: both builds; `--simulate` with a tmpfs as `--media`: the profile log line appears once.
- Pi: a FAT32 USB stick as media, cold boot: the first configure's raw buffer count in the journal is base + 2. exFAT CFexpress: `ApertarCore media profile: class=pi-nvme fs=exfat workers=4 queue=12 raw_buffers=+0`; the take-start line shows the same workers.
- Depends on: 11.

### 17. core, cdng: the write-path knobs are environment knobs only
- Gated on decision 3 a). With b) the same read sites call upstream's `tuningOverride` lookup instead of the file; with c) this commit and 18 are dropped and `configuredMediaRoot` stays.
- Touches: `dngPageCacheDrop` CdngEncoder.cpp:84-108: env only, silent fallback, read once; drops the `MediaProfile.hpp` include. CC:4715-4720 `boolEnvValue("APERTAR_DNG_WRITEBACK", true)`; CC:4364-4365 `unsignedEnvValue("APERTAR_MEDIA_SYNC_MS", 1000, 0, 60000)`; `rawCameraBufferCount`: `unsignedEnvValue("APERTAR_RAW_CAMERA_BUFFERS", std::min(16u, base + extra), 3, 16)`. `deriveMediaProfile` MediaProfile.hpp:192-203: no tune merge; `loadMediaTuneLogged`, `configuredMediaRoot`, `mediaTuneForConfiguredRoot` and CC:10545 deleted. MediaProbe.hpp:257-290 statics deleted; App keeps its last snapshot as a member under `mediaStateMutex_` (App:10893, :11328). `applyMediaTuning`: `APERTAR_MEDIA_TUNE=1` only. `tune_override=` leaves the clip line. `src/util/MediaTune.hpp` deleted.
- Lines: -380 / +18.
- Here: both builds; host tests; `grep -rn 'MediaTune\|configuredMediaRoot\|cachedMediaSnapshot' src` empty.
- Pi: before updating, `ls ~/apertar-media-tune.conf /run/apertar-media/media-tune.override.conf`; any value set there becomes a drop-in line. Then a 3-min 4K Clear HDR 16-bit 25 fps take: drops equal to the last campaign baseline.
- Depends on: 16.

### 18. scripts, config, docs: the media tuning file, its editor and the README knob table are gone
- Gated on decision 3 a).
- Touches: delete `scripts/apertar-tune`, `config/apertar-media-tune.conf`; README section; KB link texts. `config/apertar-media.tmpfiles.conf` stays until the boot-config-helpers theme removes the eject flags and the kernel helper.
- Lines: -560 / +0.
- Here: `git grep -n 'apertar-tune\|media-tune.override'` empty.
- Pi: the KB test-night scripts (`b1-arm.sh` and others) go back to drop-ins.
- Depends on: 17.

### 19. cdng: the page-cache drop falls back to the writer when the sync thread is off
- Touches: `dngPageCacheDrop` returns `Writer` when the mode is `Sync` and `APERTAR_MEDIA_SYNC_MS` is 0 (both env, fixed for the process). The one-time warning CC:4370-4377 goes. Lossy DNG already drops in the writer (`615b48c`).
- Lines: -10 / +6.
- Here: both builds; `dng_payload_write_test.sh`.
- Pi: `APERTAR_MEDIA_SYNC_MS=0`, a 1-min take: `free -m` buff/cache does not climb by the clip size.
- Depends on: 17 (with decision 3 c: on the file's read instead).

### 20. core: switches of finished A/B tests are gone
- Touches: `APERTAR_RAW_POOL_WARM` (keeps the warm pool), `APERTAR_RAW_COPY_WORKERS` (1 worker), `APERTAR_AUDIO_BUFFER_MS` `src/audio/AudioRecordingSession.cpp:208-218` (100 ms), `APERTAR_WEB_PREVIEW_RECORDING_FPS` App:83-106 and its use (30 = `kWebPreviewMaxFps`). `APERTAR_DNG_PAYLOAD_COPY` stays: `tools/dng_payload_write_test.sh:13-14` uses it as the byte-identity oracle.
- Lines: -45 / +5.
- Here: builds; host tests; `--simulate` WebUI preview runs.
- Pi: one 4K take, drops at baseline.
- Depends on: nothing.

### 21. core: knobs nobody set are constants
- Touches: `APERTAR_DEAD_MEDIUM_STOP_MS` (2000 ms), `APERTAR_WRITE_STALL_MS` (5000 ms), `APERTAR_PLAYBACK_WORKERS` `src/playback/PlaybackFrames.cpp:82` (2), `APERTAR_PHASE_LOCK_KP/_KI/_DEADBAND_US/_CLAMP_US` (the `FramePhaseLock.hpp:38-41` defaults stay), `APERTAR_MEDIA_MIN_FREE_MB` (1024).
- Lines: -40 / +6.
- Here: builds, tests.
- Pi: none (defaults unchanged).
- Depends on: nothing.

### 22. scripts, config, camera: no real-time scheduling
- Touches: `scripts/start-apertar-core.sh` back to the upstream `exec` (`scripts/start-apertar-core.sh:21@upstream-1.6.0`); `config/apertar-core-capture-priority.conf`: `LimitRTPRIO=80` and its comment out; the `APERTAR_RT_CAPTURE_PRIORITY` block in CC; README rows.
- Lines: -45 / +1.
- Here: `bash -n scripts/start-apertar-core.sh`; builds.
- Pi: reinstall the drop-in into `/etc/systemd/system/apertar-core.service.d/`, `sudo systemctl daemon-reload`, `systemctl show apertar-core -p LimitRTPRIO -p LimitNICE` = `0` / `-5`, `sudo systemctl restart apertar-core`, then `chrt -p $(pidof apertar-core)` reports SCHED_OTHER; a 4K take drops at baseline.
- Depends on: nothing.

### 23. camera, core: conform_fps and the unused writer field directIo are gone
- Touches: `Types.hpp:137`; loader/writer lines; `set_conform_fps` and the `help` entry; three serialiser lines; preset key `cameraConformFps` and its reader; the carry-over line. `MediaProfile.hpp` `directIo` and the 4th value of each `writerSettingsFor` row.
- Lines: -30 / +0.
- Here: builds; smoke diff: `conform_fps` gone (port-only).
- Pi: none.
- Depends on: 3 (same carry-over block).

### 24. cdng, camera: a stock camera writes as 1.6.0 does; the measured values are env knobs
- Gated on decision 4 b).
- Touches: defaults only, each still overridable by its env knob: `APERTAR_DNG_DONTNEED` default `writer`; `APERTAR_MEDIA_SYNC_MS` default 0; `APERTAR_DNG_WRITEBACK` default off; `writerSettingsFor` rows equal 1.6.0 (workers `max(2, min(4, threads))`, queue 12, +0 buffers) for every filesystem; `CaptureSettings::mediaTrimEnabled = false` (an existing `media_trim=` key in `camera_settings.conf` keeps its value). README handoff note with the rig's measured values and the drop-in that restores them.
- Lines: -15 / +12.
- Here: both builds; host tests; `--simulate` clip line shows the 1.6.0 values.
- Pi: on the owner's rig, first add the drop-in (`APERTAR_DNG_DONTNEED=sync`, `APERTAR_MEDIA_SYNC_MS=1000`, `APERTAR_DNG_WRITEBACK=1`), then a 3-min 4K Clear HDR 16-bit 25 fps take: drops equal to the baseline. Without the drop-in the same take shows the campaign's writer numbers (34-153 lost), which confirms the knobs act.
- Depends on: 17 or 19 (the env read sites), 23 (the table rows).

Totals: about -2 040 / +435 with all gated commits. Without 17, 18, 24 (decisions 3 c and 4 a): about -1 090 / +405.

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| RAM-sized write queue (`buffer_setting=ram`) and its plan (`planBuffer`, BB) | One camera setting, pure planning maths in a header (CAM-4), env bench knobs | Upstream has a fixed 12/24-frame queue. The RAM mode refuses itself on small boards ("staying on frames"), so a 1-2 GB Pi keeps 1.6.0 behaviour |
| Safety stop (take ends itself at N % full) | Queue latch, one event through the session callback, `wait()` stops the take | Nearest upstream patterns (`RecordingFailure`, `photoWriter_` callback, `handleTriggerEvent`, `requestShutdown`). No new class, header or constructor parameter |
| Flush abort during the safety-stop drain | One public `CameraController` method that takes no controller mutex, called before the command lock | The drain holds `commandMutex_` and the controller mutex for seconds; no upstream path does that. The lock-order exception is written in the header |
| Live buffer level, `/api/buffer`, `buffer` events thread | Kept as today | Upstream publishes no queue depth. The thread exists because the drain holds the mutex the state path needs (decision 6) |
| Split clip folders and the merge worker | Two camera settings; the merge worker is an App worker with its own state group | No upstream precedent; exFAT directory cost on long takes |
| Automatic storage pre-roll | One camera setting, default off | No precedent; the take itself is the preroll theme's |
| Drive trim | One camera setting; the helper is the boot-config-helpers theme's | No precedent |
| Writer topology per filesystem (`writerSettingsFor`) | C++ table, env overrides only | Upstream has one default per format. Measured on one CM5 only (decision 4) |
| Sync thread and page-cache drop `sync` | Env knobs read where used | Measured on the owner's rig (4K Clear HDR 16-bit 25 fps: 0 lost vs 34-153). Departs from CAM-37; default is decision 4 |
| Store-only setters | `setTuningFile` no-session shape for five fields | Upstream uses this shape only without a session; here it is used always, because the session never reads the fields |
| Takeover that edits the hardware file once | Two blocks in `App::start` | Upstream never rewrites a file unprompted (decision 10) |

## For the owner

| # | Question | Options | Recommendation and cost |
| --- | --- | --- | --- |
| 1 | Where do the three switches only App acts on (clip merge, automatic pre-roll, drive trim) live? | a) `camera_settings.conf`, beside `media_trim` (this plan); b) UI.conf, like `record_audio_enabled` (`handleUiToggle` App:9478-9491, :9642@upstream; HW-10) | a), because the port already put `media_trim` there and b) needs a second takeover of it, from `camera_settings.conf` into UI.conf. Cost of a): `CameraController` persists three values it never reads. Cost of b), the closer precedent: three `handleUiToggle` lines, three `SharedUiSettingsSnapshot` fields and parse lines, three `/api/state` `ui` lines, the WebUI reads them from `ui`; the touch UI pre-roll switch becomes a `SettingsBridge` property writing UI.conf (`SettingsBridge.cpp:1288-1297@ui-upstream` shape, about -40 / +30 in Apertar-UI, and the `storagePrerollAutoKnown` latch goes with it); `media_trim` is taken over once. Commits 6, 7, 8 change; the rest stands |
| 3 | The media tuning file family | a) delete; env knobs only (17, 18); b) a) plus upstream's `/home/pi/.apertar-tuning` for the per-take knobs (move `tuningOverride` from `ProresEncoder.cpp:771-813` into a header; +40 lines); c) keep it, drop the `/run` override and the Python editor, document it | a), or b) if test nights without restarts are still wanted. You asked for the file on 2026-11-02; per-medium sections are lost with a) and b) |
| 4 | A stock camera's write path differs from 1.6.0 in five defaults: cDNG page-cache drop `sync` instead of in the writer; a `syncfs` thread every 1000 ms (CC:4364-4368); per-frame `sync_file_range` writeback (CC:4715-4720); on vfat/NTFS 2 writers, a 16-frame queue and +2 raw buffers instead of 4 / 12 / +0 (MediaProfile.hpp:136-150, CC:4320-4326); drive trim on (Types.hpp:140) | a) keep, with the rig measurement in the handoff; b) 1.6.0 values by default, the measured values as env knobs in your drop-in (commit 24) | b). The brief says a stock camera behaves as 1.6.0 until the operator turns a port feature on, and the vfat/NTFS rows were never measured (Media-fault-tune-F5). Your rig keeps today's behaviour with three drop-in lines. Cost: a stock camera loses whatever the measured defaults would have bought it on Clear HDR 16-bit |
| 6 | Buffer events thread and the 4 Hz `/api/buffer` | a) keep, documented; b) the queue emits `buffer` events on level change, rate-limited, and `runBufferEvents` goes (about -60 / +35, a later series, needs the Pi) | a) now, b) after a Pi test |
| 7 | Command names | Renames (`set_clip_merge_enabled`, `set_storage_preroll_enabled`, `set_media_trim_enabled`) are not in this plan; they are on the command-plane theme's owner list with the other camera switches | If renamed, the KB campaign scripts change: `apertar-kb/working/drop-frames/ssd-campaign/night2/night2.sh:11,26`, `merge-test-after-night2.sh:25,51,72` (`set_clip_merge`), `apertar-kb/working/tools/longtakes.py:1129` (`set_media_trim`), `:1131` (`set_frames_per_folder`) |
| 10 | The takeover removes the moved keys from the hardware file at the first start | a) yes, once, after `adopt()` (`.bak` kept); b) leave them, apply them at every start | a). 1.6.0 never rewrites the operator's file by itself (`SettingsBridge.cpp:1943-1957@ui-upstream` reads an old location in place); a) does it once. b) undoes a later UI change at every restart. A `/boot`-only file gets b) with a log line and a validator warning |

Settled by the code or the conventions (for your information, no decision needed):

| # | Point | Settled by |
| --- | --- | --- |
| 2 | Write buffer and frames per folder are refused during a take ("Stop recording before ..."). Today `set_frames_per_folder` is allowed and applies to the next take | CAM-31: stream and file changes are refused during a take with a sentence |
| 5 | The safety stop reaches App through the existing `buffer` event and `handleTriggerEvent`, with `wait()`'s 1 s tick as the backstop | No new API is needed; both paths cost the same |
| 8 | Storage switches are not in presets | Presets start from `camera_.settings()` (App:14231) and `buildCurrentPresetPayload` lists explicit keys (App:7701ff), so new fields stay out with no code |
| 9 | The safety-stop percent is an env knob only | R8 / CAM-24; set only in tests (`=50`) |
| 11 | `APERTAR_MEDIA_REQUIRE_MOUNT` | Belongs to the record gate, not this theme |

## Risks and what was not determined

- **Store-only setters and session pushes.** The fields survive because every `settings_ = session_->currentSettings()` follows a push of a controller copy (seven sites, read). A future path that copies the session's settings back without pushing first would lose them. Pi check after commit 3: `set_buffer_mode value=ram`, `set_iso value=800`, `set_record_format value=prores`, `set_record_format value=cdng`, `get_state`: still `ram`.
- **The drain on the main thread.** With commit 13, `wait()` runs the safety-stop drain under `commandMutex_`, as `checkRecordingFailure` already does. The idle-standby check and the preroll theme's `wait()` blocks pause meanwhile. Not measured how long a RAM-mode drain takes on the owner's rig (the KB says seconds). A SIGTERM during the drain is served after it, as today.
- **The event under the queue mutex.** The latch's event runs `publishEvent` (`handleTriggerEvent`, `eventMutex_`, a socket broadcast) on the writer thread under the queue mutex. Upstream's `markDropped` does the same. Nothing takes the queue mutex while holding `eventMutex_` or `waitMutex_` (read: `waitMutex_` App:8170, :8291, :15093).
- **Lock-free abort lifetime.** `session_` is created in the constructor and never reset (`grep -n 'session_.reset\|session_ =' src/camera/CameraController.cpp` = 0 hits). A future reset would break commits 11, 12 and 14. The header comment names this.
- **A `/boot`-only hardware file.** Old values are applied at every start and a later UI change of the same switch is undone at restart until the operator deletes the keys. The log line and the `moved_key` warning say so. Not known whether any camera runs with a `/boot`-only file: the Config pane writes `/home/pi` on its first save (App:6193-6205).
- **The owner's drop-ins and files.** Env knobs removed in commits 1, 20 and 21 may be set on the rig. Check `systemctl cat apertar-core` and the two media tuning files before merging.
- **Parallel branches and other themes.**
  - command-plane: `set_storage_preroll`'s argument (its 12/13), the abort before the lock (App-1-F13), `errorReplyBody` in the store blocks that commits 3, 5, 6, 7 delete.
  - preroll: the pre-roll state (its 9, 10; old commit 15 here is dropped), `wait()` blocks (its 4, 6), `decideGuard`'s unused `Trigger`.
  - webui-state: the `system.*` copy loop (WCP-07-F3), the 4 Hz poll.
  - touch-ui: the `storagePrerollAutoKnown` latch and the pre-roll toggle row (its 4) call `applyStoragePrerollAuto` as this plan leaves it (unchanged).
  - boot-config-helpers: the trim and media-tune root helpers, `apertar-media.tmpfiles.conf`, `APERTAR_BOOT_CONFIG`, `APERTAR_MEDIA_TUNE`.
  - hardware-inputs: `hold_ms`/`double_ms` in `knownKey`, the `configStore()` singleton and its `/home/pi`-only path.
  - camera-modes: `APERTAR_FPS_LIMIT`, `APERTAR_LOSSLESS_FPS_LIMIT`, `APERTAR_IMX283_PROBE_FPS`, `APERTAR_IMX585_MIN_MODE_WIDTH`.
- **Host test count.** Commit 10 deletes `storage_buffer_conf_test.cpp` (its useful checks move), so `check_core.sh` reports 16 tests.
- **Pi models.**
  - No commit changes board-specific code. The RAM mode already falls back to frames on small boards; the moved settings keep their defaults; `std::thread::hardware_concurrency()` stays the worker bound.
  - Not checked on a Pi 4 / CM4: how the RAM plan behaves with 2 GB and the desktop UI running. The plan line in the journal shows it.
  - Commit 24 (if chosen) is the only change in write behaviour, and it returns every board to 1.6.0's values.
- **Not determined:** whether the owner's hardware file holds non-default `buffer_ram_*` or `buffer_stop_percent` values (the takeover log will say); the safety-stop reaction time on the rig (commit 13's Pi check).

## Findings covered

| Finding | Commit |
| --- | --- |
| Media-buffer-split-F1 | 3, 5, 6, 7, 9, 10 |
| App-1-F2 | 3, 5, 6, 7, 10, 11, 12, 13, 14; pre-roll state: preroll theme 10 |
| App-1-F3 | 1, 20 (`APERTAR_WEB_PREVIEW_RECORDING_FPS`); `APERTAR_BOOT_CONFIG`: boot-config-helpers theme |
| App-2-F3 | 13 (hook), 14 (`flushAbortFunction`) |
| App-2-F5 | 1, 6, 7, 8 |
| App-5-F1 | 3, 5, 6, 7: the three store blocks are deleted. The finding's "keep in the hardware file" rework is not taken (HW-10; decision 1 for the alternative store) |
| CC-2-F1 | 2 |
| CC-2-F2 | 3, 5, 9 (CC no longer opens the hardware file); 4 reads the candidate list once in App |
| CC-2-F6 | 17, 18 |
| CC-2-F7 | 12, 14 |
| CC-3-F1 | 11, 12, 13, 14 |
| CC-3-F2 | 3, 5, 9, 17 |
| Media-buffer-split-F2 | 11, 12, 13, 14; pre-roll state: preroll theme 10 |
| Media-buffer-split-F3 | 13 (safety-stop thread); the buffer events thread is decision 6 |
| Media-fault-tune-F1 | 17, 18 |
| Media-fault-tune-F3 | 16, 17 |
| Build-scripts-docs-F1 | 17, 18 (decision 3 b keeps `.apertar-tuning`) |
| Build-scripts-docs-F2 | 18 |
| Build-scripts-docs-F3 | 22 |
| Encoders-audio-F1 | 17 |
| Encoders-audio-F2 | 19; Lossy part done (`615b48c`); the cDNG default is decision 4 / 24 |
| X-knobs-6 | 17, 18 |
| X-knobs-7 | 3, 5, 6, 7 |
| X-knobs-8 | 1 |
| X-knobs-9 | 20, 21, 22 for the write path, audio, playback, phase lock, RT. `APERTAR_DNG_PAYLOAD_COPY` kept (host test oracle). Camera-mode knobs: camera-modes theme. `APERTAR_MEDIA_RUN_DIR`, `APERTAR_MEDIA_TUNE`: boot-config-helpers. `APERTAR_MEDIA_REQUIRE_MOUNT`: record gate |
| X-knobs-12 | 23 (`conform_fps`, `directIo`); `hold_ms`/`double_ms`: hardware-inputs theme |
| X-knobs-13 | 2 |
| X-commits-core-2-7 | 1, 17-22 remove the knobs going forward; rewriting history is the commit-clarity task |
| Taken along: App-1-F1, X-state-consistency-7 | 15 |
| Taken along: CC-2-F8 | 11 |
| Taken along: CC-2-F11 | 5 (frames-per-folder parse); the fps knobs: camera-modes theme |
| Taken along: CC-3-F9 | 9, 20; DONTNEED `sync` default: decision 4 |
| Taken along: CC-1-F2, CC-5-F10 | 16, 17 |
| Taken along: App-4-F5 | 1, 21 |
| Taken along: App-4-F6 | 12; pre-roll statics: preroll theme 10; `configStore()`: hardware-inputs theme |
| Taken along: App-4-F9 | decision 6 |
| Taken along: App-4-F17 | 17 |
| Taken along: Media-buffer-split-F9 | 1, 10; `Trigger` parameter: preroll theme |
| Taken along: Media-buffer-split-F10, HW-config-text-store-F14 | 3, 5, 6, 7 (store blocks); frame-number rule copies not covered (playback) |
| Taken along: HW-config-text-store-F10 | 10 |
| Taken along: WCP-07-F7 | 1 |
| Taken along: WCP-07-F3 | 3, 5, 6, 7, 8 move the settings out of `system`; the copy loop: webui-state theme |
| Taken along: App-5-F2 | command-plane 12/13 (the argument); renames: command-plane owner list |
| Taken along: CC-1-F4, X-knobs-19 | 3, 5, 6, 7 write their new keys `<< s.member`. The six existing port booleans (`fps_phase_lock`, `preview_tdn`, `media_trim`, `fps_speed_ramp*`) and fork main's `clear_hdr` keep their text form: not covered here (cosmetic; readers take both) |
| Taken along: Media-fault-tune-F13 | 17 |
| Taken along: App-3-F3 | 20 |
| Taken along: X-state-consistency-14 | settled: presets carry no storage switches (item 8) |
| Taken along: Media-fault-tune-F5, CC-2-F17 | decision 4 / commit 24 returns the rows to 1.6.0; without 24 they stay unmeasured |

## What the challenge changed

Each row was checked in `core-work` `0d13a6f`, `ui-work` `ac1fc28` and the upstream trees.

| # | Point | Decision | Why |
| --- | --- | --- | --- |
| 1 | Commit 13 would shut Core down | Right on the bug, wrong on the fix | A true predicate breaks the loop (App:8293-8296) and `main` then calls `app.stop()` (`main.cpp:129-134`). But `wait_for` with a predicate does not return on a notify unless the predicate is true, so "no predicate change" would wait the full second. The flag goes into the predicate, and the break tests `running_`/`shutdownRequested_` after the wait (commit 13) |
| 2 | No third constructor parameter | Right | `publishEvent` -> `handleTriggerEvent` (App:10823-10870@upstream) already drives App from camera events. The flag is set under `waitMutex_` like `requestShutdown` (App:11016-11023@upstream), so the notify cannot be lost |
| 3 | Journal line loses used/capacity | Right | The line prints them from the hook (App:7991-7998, :11104-11107). The latch keeps them (commit 12) |
| 4 | Storage setters through `applySettingsLocked` | Right | Standby and pre-roll refusals, sensor push, Error state (CC:12743-12782). Decisive: before `camera_.start()` `applyControls` fails ("Camera is not open.", CC:7570-7572), so the takeover needs the store-only shape. Upstream's recorder-only `setCdngCompression` uses `applySettingsLocked`; the shape choice is listed as new ground |
| 5 | Duplicate keys in `settingsBody` | Right | `settingsBody` ends with `bufferSettingMembers()` (App:393), which emits the same keys (App:255-268). Each commit moves its key out; the WebUI stops reading it from `/api/buffer`; the touch UI gets it from settings events via `applyCoreState` (ACB:1411, :1732) |
| 6 | Takeover too late | Right | Workers and watcher start at App:8031-8051, before `camera_.start()` (App:8069); the watcher's first cycle requests the Core-start pre-roll and reads the switch at once (App:10947-10963, :11152-11163). Apply before App:8031; remove after `adopt()` (App:8148); the merge-worker move is no longer needed |
| 7 | `/boot` copies | Right | The store knows only `/home/pi` (`HardwareConfigStore.cpp:118-123`); CC's readers also try `/boot` (CC:2946-2949, :2994-2997). The takeover reads `hardwareConfigCandidatePaths()` (App:4924) and edits only `store.path()` |
| 8 | Precedent for rewriting the old location | Right | Upstream never rewrites a file unprompted; decision 10 now says so and cites both precedents |
| 9 | Commit 10's unknown-key warning does not exist | Right | `knownKey` is used only by `checkEdits` (HardwareConfigText.hpp:451, :496). Commit 10 adds one `moved_key` warning in the existing `storage` branch and drops the `media` entry so `unknown_section` covers it |
| 10 | Commit 17 breaks the build | Right | `mediaTuneForConfiguredRoot` is still called at CdngEncoder.cpp:91, CC:1467, :4364, :4718. Commit 16 removes only `mediaExtraRawBuffersForConfiguredRoot`; the rest goes in 17 |
| 11 | First configure without the profile | Right | `cachedMediaSnapshotOrProbe` probes before the first watcher cycle (MediaProbe.hpp:285-290). App seeds the profile before `camera_.start()` (commit 16) |
| 12 | Commit 6/7 across two repos | Right on the gap; resolved differently | The command-plane theme already plans `set_storage_preroll enabled=` with the name kept (`design/command-plane.md` commits 12-13) and keeps renames on its owner list. This plan renames nothing, so there is no UI commit, no alias and no M1 |
| 13 | Scripts called "not determined" | Right | night2.sh:11,26; merge-test-after-night2.sh:25,51,72; longtakes.py:1129,1131. Listed under item 7 |
| 14 | Decision 1 option b) costed wrong | Right on the cost; recommendation stays a) | One `handleUiToggle` line per switch (App:9478-9491@upstream); the touch UI shows only the pre-roll switch. a) stays recommended because `media_trim` already lives in `camera_settings.conf`; b) is stated as the closer precedent with its real cost. The mutex argument does not decide it: App's workers already take the controller mutex through `isRecording()` (App:10904, :11708; CC:12631-12635) |
| 15 | Template keeps the moved keys | Right | App:5052-5076. Each of 3, 5, 6, 7, 9 removes its own lines |
| 16 | Commit 2 carries two ideas | Right | `[camera]` values were never settings; the `unknown_section` warning covers a leftover (HardwareConfigText.hpp:806-811). The takeover is born in commit 4 |
| 17 | Commit 12 emits twice | Partly right | The extra event is real but harmless (the touch UI takes partial `buffer` events, ACB:2664ff). `runBufferEvents` keeps its detection, because it also reports the clear and `flush_discarded`, which the latch would otherwise have to send. The comment CC:5011-5012 is fixed |
| 18 | Commit 11 needs no new header | Right | `RecordingFailure failure_` is a recorder member read through `session_` (CC:3901, :5891@upstream). Gauge and latch become queue members; the latch's event uses the `photoWriter_.setErrorCallback` shape (CC:5245-5250@upstream). No `RecordingBuffer.hpp` |
| 19 | Stock defaults not on the owner's list | Right, and one more | syncfs thread, writeback, vfat/NTFS writer rows confirmed (CC:4364-4368, :4715-4720, MediaProfile.hpp:136-150). Drive trim is also on by default (Types.hpp:140). Decision 4 covers all five; commit 24 implements option b) |
| 20 | Items the code settles | Right | 2 (CAM-31), 8 (App:14231, :7701ff), 9 (R8), 11 (record gate) moved to the "settled" table; 5 too, since it no longer has a cost difference |
| 21 | Commit 13 Pi check has no second timestamp | Right | The queue logs nothing at fire time (CC:5013-5020). The latch stores the fire time; the existing line prints `after D ms`; pass < 200 ms |
| 22 | Commit 23 Pi check | Right | The drop-in must be reinstalled and reloaded before `chrt` shows anything (now commit 22) |
| 23 | Commit 25 | Right | Readers take both forms (CC:869-890); new keys are written `<< s.member` from the start. CC-1-F4 for the existing keys is listed as not covered |
| 24 | Line drift | Right | `0977dd6` and `615b48c` are merged; anchors in this page are `@0d13a6f` where re-read, and every commit re-greps |
| 25 | Commit 3 too large | Right | Split into 3 (the setting) and 4 (the takeover); 5, 6, 7, 9 each add rows to 4's list |
| - | Old commit 15 (pre-roll live state as App members) | Dropped | The preroll theme's commit 10 moves that state into CC (`design/preroll.md` commit 10) |
| - | Old commit 7 (UI) and the renames | Dropped | See row 12 |

## Checked against the owner's recorded decisions

Checked 2026-11-17 against `owner-recorded-decisions-a.md` (DA-*) and `-b.md` (DB-*), their source pages, and a KB search for every key, env knob and command this plan touches. Code read at `core-work` `56e135c` and `core-upstream` `35dbe67`. The lead's planned change to commit 4 (old hardware-file keys taken over only while `camera_settings.conf` has no such key, read-only) is part of this check.

| commit | touches decision (id, his words) | verdict | what changes in the commit |
| --- | --- | --- | --- |
| 1 env twins gone | No decision asks for the twins. DB-91/DB-93 "each behind its env knob **or setting**", "Core changes stay knob-gated": the setting stays. DB-92 "extend an existing knob or setting before adding one": one switch, not two. DA-84 (dual-sensor plan, "not yet answered by him") puts `APERTAR_STORAGE_PREROLL=0 APERTAR_MEDIA_TRIM=0` on the secondary | fine | None in Core. The secondary sets `XDG_CONFIG_HOME=/home/pi/.config-cam1`, so it has its own `camera_settings.conf` (path rule CC:419-427@core-work, the same at CC:344-352@upstream); the two switches become `storage_preroll_auto=0` / `media_trim=0` there, or the secondary's role gate forces them off at start, like it forces photo mode off (`design-dual-sensor.md:184`). The KB pages that set the twins get the command instead (`set_storage_preroll`, `set_media_trim enabled=false`): `dual-sensor/design-dual-sensor.md:133, :216, :1042-1048`, `design-merged-v1.md:67`, `dng-chain-feasibility.md:153, :200, :364`, `handoff-dng-chain-feasibility.md:94`, `drop-frames/inspection-raw/synthesis-draft.md:272`. The NVMe campaign already dropped `APERTAR_CLIP_MERGE=0` for `set_clip_merge` (`nvme-campaign/build-list.md:18`, H4) |
| 2 Clear HDR ISO caps are constants | DA-90 / DB-19 "Clear HDR ISO caps, as in Cinemate": 16-bit 1585, 12-bit 720 (`ramp-ladder/README.md:61-66`, `hardware-log.md:503-510`). The `[camera]` keys were how it was built (`fork-log.md:61`), not the request | fine | Values unchanged. Add one log line when a leftover `[camera]` key differs from the constant (as commit 9 does for its keys), so a hand-tuned cap is not lost silently. The owner's file of 2026-10-29 has no `[camera]` section (`working/tools/controls_fixture_apertar-hardware.conf:282-285`) |
| 3 write buffer setting; 5 frames per folder setting | DA-6 for hardware-file saves: "Save during a take: allowed; the file is written now and the drivers apply after the take ends (design changed from \"refuse\")". Today both commands are store edits with no take check and apply to the next take (App `set_buffer_mode` block, comment "frames_per_folder applies to the next take"). DB-67 `frames_per_folder` 5000 on his camera, "No Core code default changed" | needs his answer | The plan adds a refusal during a take (CAM-31). Smallest variant that keeps today's behaviour and DA-6's rule: no `recording_` gate in `setWriteBuffer` / `setFramesPerFolder`; the queue reads both at take start (`planQueueBuffer`, `startAtFolder`), so a change mid-take reaches the next take only, as clip merge already does in commit 6. Stock: neither command exists in 1.6.0, so a stock camera is not affected either way. Defaults stay `frames` and 0 |
| 4 takeover (with the lead's read-only change) | DA-3 "Keep `~/apertar-hardware.conf` as the system-controlled file (Core writes it ...)": Core may write it; nothing requires the takeover to. DA-8 "nothing is written automatically" (the detection rule): speaks for read-only. DA-5 "Hand edit over ssh ... applies on Apply / next start": a moved key no longer is a hardware setting; commit 10's `moved_key` warning tells the operator | fine | For the lead's change. Step 2 (the `store.edit` that removes keys) and decision 10 go; the `/boot`-only case becomes the same as `/home/pi`. One code condition: test "key absent" against the keys the **constructor's load** saw, not against the file now. The first takeover setter calls `persistSettingsLocked`, and the whole-file writer then writes all five keys, so a re-read would skip rows 2-5. Shape: the loader records the camera-wide keys it read (upstream reads the retired `wb_locked` into a loader local, CC:625, :682-728@upstream); App asks `camera_.persistedKeyLoaded("buffer_setting")`. The dual-sensor secondary (`APERTAR_HARDWARE_CONFIG=/home/pi/apertar-hardware-cam1.conf`, `[storage] buffer=frames`) is taken over into its own XDG file and its file is not edited |
| 6 clip merge setting | DA-105 / DB-66 clip split and merge folded in, "merge on"; DB-72 "merge after every long take (so we get statistics on that)" | fine | None. Default `clipMergeEnabled = true` changes nothing on a stock camera: with `frames_per_folder` 0 (default) no take is split, so the worker finds nothing |
| 7 automatic pre-roll setting | No recorded decision on the pre-roll default (default off since `0977dd6`) | fine | None |
| 8 trim reads the camera setting | DB-65 "trim with a switch default on"; DB-70 he approved Core trimming by itself | fine | None (the default is commit 24) |
| 9 RAM budget and stop percent env only | DB-101 the shipping RAM fraction "User decides" (`drop-frames/tests-2026-11/preregistration.md:305`): an env knob keeps the choice open | fine | None in Core. `working/tools/longtakes.py --fix-budget` (:4108, :4770-4773) writes `[storage] buffer_ram_fraction=0.9 buffer_ram_floor_mb=256` into the hardware file; after this commit Core ignores them and only logs. The NVMe campaign struck that option (`nvme-campaign/build-list.md:50, :87, :95`); the tool's help text and `storage-slowdown-plan.md:125, :221` get the drop-in form `APERTAR_CDNG_QUEUE_RAM_FRACTION` / `_FLOOR_MB` |
| 10 readers gone, `moved_key` warning | DA-8 (show, do not write) | fine | With the read-only takeover the warning is the only path that tells the operator to delete the lines; keep its text as planned |
| 11, 12, 15, 16 | none | fine | None |
| 13 `wait()` stops the take | none; DB-68 "treat ~95 % as full" is the card, not the queue | fine | None |
| 14 flush abort | DB-61 "Decision (the owner): discard, the old clip is cut short, written frames stay" | fine | None: the commit keeps discard-and-start. The Pi check (`buffer_flush_discarded` = N, a new take starts) is the check of DB-61 |
| 17, 18 tuning file family gone | Request of 2026-11-02 (`drop-frames/media-tune-file.md:3-5`): "the campaign's findings go into a settings file per storage medium, next to the hardware conf, and test nights must be able to override it from the command line". DA-104 / DB-65 "everything back" kept the "media-tune reader". DA-88 `APERTAR_MEDIA_TUNE=1` opt-in | conflict | Decision 3 is answered: keep the file, its `/run` override and `scripts/apertar-tune` (option c without dropping the override and the editor). A stock camera has no file: only `apertar-tune init` or a hand `cp` creates it (`scripts/apertar-tune:6`, `config/apertar-media-tune.conf:3`), so without it the code defaults run, which commit 24 sets to 1.6.0. Commit 18 is dropped. Commit 17 shrinks to the statics: `MediaProfile` carries the resolved `MediaTune` (`deriveMediaProfile` already loads it, MediaProfile.hpp:195), App hands the profile over in commit 16, the four read sites (CdngEncoder.cpp:91, CC:1467, :4364, :4718) read that copy; `configuredMediaRoot`, `mediaTuneForConfiguredRoot` and the snapshot statics go. Env still wins (`media-tune-file.md` precedence). Upstream precedent for a bench file in `/home/pi` that env overrides: `tuningOverride` `src/prores/ProresEncoder.cpp:771-813@upstream`. The README table is kept and says "bench file, not a camera setting" |
| 19 page-cache drop falls back to the writer | DB-60 "I can lose fsync if we need to" (in-take fsync only) | fine | Under the variant of 17 it reads `sync_ms` from the file value as well as from env (the plan's "decision 3 c" form) |
| 20 knobs of finished A/B tests | `APERTAR_AUDIO_BUFFER_MS` is a live lever of the NVMe campaign: the helper arms it (`nvme-campaign/scripts/apertar-campaign-helper.sh:36, :207, :244`), `longtakes.py --audio-ms` reads it back (:2756-2758, :4147), the plan runs the long tiers at 1000 if the audio fix is not in (`nvme-campaign/plan.md:277, :285`; `handoff-nvme-campaign.md:103`). DB-71/DB-72 are his campaign requirements | conflict | Keep `APERTAR_AUDIO_BUFFER_MS` as it is: already env only, read where used (`src/audio/AudioRecordingSession.cpp:208-218`), the R8 shape (`unsignedEnvValue("APERTAR_CDNG_QUEUE_FRAMES", ...)` CC:3328-3330@upstream). The other three go as planned. `APERTAR_WEB_PREVIEW_RECORDING_FPS=0` in the A0 protocol (`dng-chain-feasibility.md:40, :199, :238`) is replaced by the protocol's own alternative, "WebUI closed" |
| 21 knobs nobody set become constants | `APERTAR_PHASE_LOCK_DEADBAND_US=100000` was set: the phase lock used as a meter (`lessons/hardware-log.md:262-263`), and the dual-sensor sync test 1.1 needs it with `APERTAR_PHASE_LOCK_LOG=1` (`dual-sensor/design-dual-sensor.md:1081`, `sync-synthesis.md:210`). DA-82 dual-sensor sync from Cinemate's phase lock "in software"; DA-87 / DB-56 the lock stays, off | conflict | Keep `APERTAR_PHASE_LOCK_KP/_KI/_DEADBAND_US/_CLAMP_US` (read once, CC:8910-8923@core-work, R8 shape). The other knobs become constants as planned. Stock: the lock is off by default, so the knobs change nothing |
| 22 no real-time scheduling | Not his decision. Measured no effect: SCHED_FIFO 40 gave 92 lost vs 113 (`hardware-log.md:954`). His unit carries `LimitRTPRIO=80` (`dual-sensor/r5-pi-hardware.md:28`) and runs without `APERTAR_RT` | fine | None. `dual-sensor/design-dual-sensor.md:224-225` ("if T69 wants RT, use `APERTAR_RT_CAPTURE_PRIORITY`") loses that option; the page gets a line. The Pi step (reinstall the drop-in) is his to run (standing rule: he runs every drop-in and restart) |
| 23 `conform_fps` and `directIo` gone | DA-92 / DB-31 his request 21: "`conform_fps`, the project's timeline rate, default 25" (`ramp-ladder/README.md:48`; `fork-log.md:67`). The dual-sensor design forwards `set_conform_fps` to both Cores (`design-c-risk-first.md:40`) and compares the field (`design-dual-sensor.md:438`) | conflict | Keep `conform_fps` (field, loader/writer lines, `set_conform_fps`, three serialiser lines, preset key, carry-over). Only `directIo` goes. Stock: nothing derives from the field ("nothing derives from it yet", Types.hpp:135-136), so a stock camera records as 1.6.0; it only adds a port field to the state, which the smoke rule allows |
| 24 stock writes as 1.6.0 | DB-65 "everything back": "trim with a switch default on, `APERTAR_DNG_DONTNEED=sync` default". Both change a stock camera (1.6.0 drops in the writer, CdngEncoder.cpp:1777@upstream; has no trim) | conflict | The commit is already the variant the rule asks for: 1.6.0 values by default, his values switched on by him. With the variant of 17 his rig needs no new drop-in: his `~/apertar-media-tune.conf` already holds `[default] dontneed=sync writeback=on sync_ms=1000` and `[exfat] workers=4 queue=12` (`media-tune-file.md`, "The values written"), and his `camera_settings.conf` already holds a `media_trim=` line (the writer writes every field), which keeps its value. The Pi step changes to: `grep -E 'dontneed|writeback|sync_ms' ~/apertar-media-tune.conf` and `grep media_trim ~/.config/apertar-core/camera_settings.conf` before updating |

### Decisions this plan must keep

- DB-61: Record during a safety-stop flush throws away the queued frames and starts the new take at once. The old clip is cut short and the frames already written stay (commit 14).
- 2026-11-02 request, DA-104 / DB-65: keep the per-medium tuning file `~/apertar-media-tune.conf`, its `/run` override for test nights and `scripts/apertar-tune`. Environment variables still win over it.
- DA-92 / DB-31: keep `conform_fps` (default 25, 1-120, persisted, carried across formats, in presets).
- DA-90 / DB-19: Clear HDR ISO caps stay 1585 (16-bit) and 720 (12-bit).
- DA-105 / DB-66 / DB-67: keep clip split and the merge worker. The merge is on by default. `frames_per_folder` stays 0 by default (his camera uses 5000 by its own setting).
- DB-65 / DA-88: trim, the `sync` page-cache drop, the sync thread and writeback stay available to the operator. A stock camera has them off, as in 1.6.0. `APERTAR_MEDIA_TUNE` stays opt-in.
- DB-101: the shipping RAM fraction is his choice. Keep the env knob, and keep the default 0.6 / 512 that every recorded take used.
- Campaign levers: keep `APERTAR_AUDIO_BUFFER_MS`, `APERTAR_DNG_DONTNEED`, `APERTAR_DNG_WRITEBACK`, `APERTAR_MEDIA_SYNC_MS` and `APERTAR_PHASE_LOCK_*`. Their scripts read Core's environ and stop a night when a value does not match.
- Command names and the fields the KB scripts read stay: `set_frames_per_folder value=`, `set_clip_merge enabled=`, `set_media_trim enabled=`; in `get_state`: `frames_per_folder`, `clip_merge_enabled`, `clip_merge_*`, `buffer_setting`; in `/api/state`: `media_trim_running`, `media_trim_last_*` (`longtakes.py:1129-1131, :1186, :1913, :2488-2537, :4444-4468`; `chain-after-night.sh:29-30`; `night2.sh`; `merge-test-after-night2.sh`).
- DA-3: Core stays the writer of `~/apertar-hardware.conf`. With the read-only takeover, Core writes nothing to it for this theme.
- No UI commit is needed. His camera has no touch screen (DA-77), so anything on the touch side can only be compiled and looked at on HDMI.

### Open questions a recorded decision already answers

| question | decision | answer |
| --- | --- | --- |
| Decision 3: the media tuning file family | 2026-11-02 request (`media-tune-file.md:3-5`); DA-104 / DB-65 | Keep it, with the override and the editor. A stock camera has no file. Commit 18 is dropped and commit 17 shrinks to removing the statics |
| Decision 4: stock write-path defaults | DB-65 plus the review rule | b), commit 24. His rig keeps his values through his own media-tune file and `camera_settings.conf`, so no new drop-in |
| Decision 10: remove moved keys from the hardware file | DA-3 (allows, does not require), DA-8 (nothing written automatically), upstream `SettingsBridge.cpp:1943-1957@ui-upstream` | Read-only takeover, keyed on the keys the constructor's load saw. No `store.edit` |
| Settled item 2: refuse write buffer / frames per folder during a take | DA-6 (hardware-file saves during a take are allowed and apply after the take) | Not settled by CAM-31 alone. The decision points to "allowed, applies to the next take", which is today's behaviour. Ask him; the variant costs nothing |
| Are the env twins needed for the dual-sensor secondary? | DA-84 (plan, not answered), DA-83 "with no cam1 configured, nothing changes" | No. The secondary's own XDG `camera_settings.conf`, or its role gate, holds pre-roll and trim off |
| Is `conform_fps` unused and removable? | DA-92 / DB-31 (request 21) | No. It is his request. Keep it |
| Which `APERTAR_*` knobs of commits 20-21 are still in use? | DB-71 / DB-72 (NVMe campaign), DA-82 (dual-sensor sync) | `APERTAR_AUDIO_BUFFER_MS` and `APERTAR_PHASE_LOCK_*`. Keep them |
| Clear HDR ISO caps if the 12-bit fixes move the cap | DB-19 / request 18 "measure" | The measured value becomes the constant (720 today, `hardware-log.md:500-510`) |
