# Storage and recording settings: where they live and how they travel: design

Read at Apertar-Core `core-work` `7dc6f7a` and Apertar-UI `ui-work` `ac1fc28` (port plus the fixes so far), against upstream 1.6.0 Core `35dbe67` and UI `43888e5`. Port line numbers are `@7dc6f7a` / `@ac1fc28`; upstream line numbers are `@upstream-1.6.0`.

## In short

1. Today the port keeps five operator switches (write buffer, frames per folder, clip merge, automatic pre-roll, drive trim) in three stores: `[storage]` and `[media]` of `apertar-hardware.conf`, and `camera_settings.conf`. Each switch also has an `APERTAR_*` env twin that silently wins, and four `*_env` state fields tell the UIs about it.
2. The camera side opens the hardware file by itself: `[storage]` at every take, `[camera]` once. A media tuning file family (two INI files, a 487-line Python editor, a tmpfiles rule) feeds eight write-path knobs. Its env vars still win over it.
3. Live state crosses from the recorder to App through header singletons and two `std::function` globals. These carry the safety stop, the flush abort, the gauge, the buffer note, the pre-roll state, the media root and the media snapshot.
4. In the target, the five switches are `CaptureSettings` fields in `camera_settings.conf`, where `media_trim` already lives. Each has one `CameraController` setter, one command and the three settings serialisers (recipe R2). Old hardware-file keys are taken over once at start and then removed from the file.
5. The RAM budget numbers, the safety-stop percent and all write-path tuning become env knobs only, read where they are used (R8). The Clear HDR ISO caps become constants. The media tuning file family is deleted (the owner decides; see "For the owner").
6. The gauge, the safety stop and the flush abort become controller-owned objects passed to the queue by pointer. This is the shape of upstream's `RecordingDropWarning`. The safety stop reaches App through a constructor callback, and App's 1 Hz `wait()` loop stops the take. The safety-stop thread and every header singleton go.
7. The plan has 25 commits (24 Core, 1 UI). Roughly 2 000 lines are removed and 450 added. Most of the removal is the tuning file family and the two hand parsers.

## How it works in the port today

"App" = `src/ApertarCoreApp.cpp`, "CC" = `src/camera/CameraController.cpp`, "WCP" = `src/web/WebControlPage.cpp`, "ACB" = Apertar-UI `src/ApertarControlBridge.cpp`, "BB" = `src/util/BufferBudget.hpp`, "SP" = `src/util/StoragePreroll.hpp`. All are `@7dc6f7a` / `@ac1fc28`.

### Operator switches and tuning values

| Value | Who writes | Who reads | Thread and lock | File it is saved in | Shown where |
| --- | --- | --- | --- | --- | --- |
| Write buffer `frames`/`ram` | `set_buffer_mode` App:12846-12871, via `hardware::configStore().edit(...)` with `flags.trusted` (bypasses the store's text-only rule); WebUI Config text save; `set_controls` | 1. App `refreshBufferRequest` App:273-286 parses the file text and publishes `bufferSettingStorage()` (BB:276-301). 2. CC `planQueueBuffer` CC:5495-5545 opens the file itself through `loadBufferConf` CC:2989-3006 at each take start. 3. The env twin `APERTAR_CDNG_BUFFER` (App:276, CC:5503) wins | Command thread under `commandMutex_`; the take-start read runs under CC `mutex_` and the queue mutex | `apertar-hardware.conf` `[storage] buffer=` | `buffer_setting` in `bufferSettingMembers` App:252-269, which goes into `settingsBody` (App:393), the `buffer` event, `/api/buffer` and `/api/state` `system`. WebUI WCP:15463-15475; touch UI ACB:2676-2684, `qml/SettingsPage.qml:3421-3453` |
| Frames per folder | `set_frames_per_folder` App:12874-12915 (one block with `set_clip_merge`), through the store | 1. App refresh into the static `framesPerFolderRequest()` BB:323-327, for state only. 2. CC `startAtFolder` CC:4287-4298 reads the file again at each take. 3. Env twin `APERTAR_CDNG_FRAMES_PER_FOLDER` (App:266, :283; CC:4293) | As above | `[storage] frames_per_folder=` | `frames_per_folder`, `frames_per_folder_env` (App:265-266), in `system` of `/api/state`. WebUI WCP:16192-16204. Touch UI: none |
| Clip merge | `set_clip_merge` (same block) | App merge worker: `clipMergeMayRun` App:11707 and `runClipMerge` App:11753, :11782 read the static `clipMergeRequest()` BB:335-339; env twin `APERTAR_CLIP_MERGE` | Merge worker thread; atomic | `[storage] clip_merge=on\|off` | `clip_merge_enabled`, `clip_merge_env_off` (App:267-268). WebUI WCP:16206-16218 |
| Automatic pre-roll | `set_storage_preroll value=on\|off` App:12917-12942 (its own lower-case parse) | 1. `requestStoragePreroll` App:11156-11162 parses the file text at each request. 2. `refreshBufferRequest` publishes `prerollState().automatic` (SP:234-245) for state. 3. Env twin `APERTAR_STORAGE_PREROLL` | Watcher thread or command thread; atomics | `[media] preroll=` | `storage_preroll_auto`, `storage_preroll_auto_env` (App:261-262). WebUI WCP:15836-15850; touch UI ACB:617-630, :2736-2750, `SettingsPage.qml:5628-5635` |
| Pre-roll length | text only | App:11170 `effectiveSeconds` | as above | `[media] preroll_seconds=` | nowhere |
| Drive trim | `set_media_trim` App:13207-13216 calls `camera_.setMediaTrimEnabled` (CC:11887-11893) **and** stores App's own copy `mediaTrimSetting_` (`ApertarCoreApp.hpp:299`, also set at App:8077) | Trim worker App:11447, :11467, :11947 read the App copy; the env twin `APERTAR_MEDIA_TRIM` (App:6403-6408) wins | Command thread; atomic copy | `camera_settings.conf` `media_trim=true\|false` (CC:889-890, :976); carried across formats CC:11349, :11368 | `system.media_trim_enabled`, `system.media_trim_env_off` (App:9588-9589). It is not in `settingsBody` or `settingsEvent`. WebUI WCP:16179-16190 |
| RAM budget fraction, floor, max fraction | text only | CC `planQueueBuffer` CC:5534-5537: env > file > default | Take start | `[storage] buffer_ram_fraction`, `_floor_mb`, `_max_fraction`; the template ships them at the defaults (App:5059-5061) | nowhere (plan line in the journal) |
| Safety-stop percent | text only | CC `publishStop` CC:5509-5519: env `APERTAR_CDNG_BUFFER_STOP_PERCENT` > file > 90 (ram) / 0 (frames) | Take start | `[storage] buffer_stop_percent` | `buffer_stop_percent` (App:258); touch UI message ACB:2701-2722 |
| Clear HDR ISO caps | text only | CC `loadCameraSection` CC:2942-2984, a third INI dialect (strips all whitespace), cached once in a function static CC:3010-3014; used by `clearHdrIsoCap` CC:3017-3023 | Configure time | `[camera] clear_hdr_iso_max_12bit/16bit`; template App:5078-5083 | `iso_max` (indirectly) |
| Validator rules for the above | - | `hwconf::validate` HardwareConfigText.hpp:830-845 (`bufferConfProblem`, `prerollConfProblem`); section table entries `camera`, `storage`, `media` :58, :66-67 | WebUI Config pane | - | Config pane issues |

### Live state between the recorder and App

| Value or path | Who writes | Who reads | Thread and lock | File | Shown where |
| --- | --- | --- | --- | --- | --- |
| Gauge (used, capacity, ram, active) | `DngRecordingQueue` through the function static `frameBufferGauge()` CC:4169-4186 (e.g. CC:4331-4333, :5487) | `CameraController::frameBufferStatus` CC:12527-12553 (lock-free, plus a `try_lock` for the mode); `rawTakeActive` CC:12554-12557 | Queue mutex on write; atomics on read | - | `buffer_used/_capacity/_fill/_mode/_unit` via `bufferMembers` App:301-311; `buffer` event; `/api/buffer` App:8421-8430 |
| Buffer plan note | CC `planQueueBuffer` through `publishBufferSetting` BB:289-294 | `bufferSettingMembers` App:252-269 | Tiny static mutex `bufferSettingMutex()` BB:281-285 | - | `buffer_note` |
| Safety stop latch | Queue `enqueue` CC:5011-5022 sets the static `bufferbudget::safetyStopState()` BB:222-234 and calls the global `safetyStopHook()` BB:262-266 under the queue mutex. The hook is assigned in App's constructor body App:7992-7998 | App thread `runBufferSafetyStop` App:11087-11118 (cv + 100 ms backstop) sends `record_stop` through `dispatchHardwareInputCommand`. `stopRecording` CC:12442 reads the static to send REC-off early. `clipMergeMayRun` App:11710; `/api/buffer` App:8428 | Queue mutex, atomics, App's own cv | - | `buffer_safety_stop`, `buffer_stop_percent` |
| Flush abort | The queue registers `[this]{ return abortSafetyFlush(); }` in the global `flushAbortFunction()` BB:238-252 at take start CC:4271, and unregisters at CC:4211 and :4594 | `abortSafetyStopFlushForRecord` App:291-299, called before `hardwareActionMutex_` (App:10123) and before `commandMutex_` (App:12583) | Registry mutex, then the queue mutex. The drain holds `commandMutex_` and CC `mutex_`, so the abort must take neither | - | `buffer_flush_discarded` |
| Pre-roll live state | `runStoragePrerollOnce` App:11212ff writes `prerollState()` SP:224-271 (active, fps, last) | `bufferSettingMembers`, `runBufferEvents`, `clipMergeMayRun` App:11709 | Atomics plus a static mutex | - | `storage_preroll_active/_fps/_last` |
| Buffer events | App thread `runBufferEvents` App:10997-11052 polls everything above every 250 ms (1 s idle) | Touch UI `buffer` event ACB:1345-1349 | Own thread; no controller lock | - | Buffer bar on touch and HDMI; WebUI polls `/api/buffer` at about 4 Hz |
| Media root | `CameraController::start` sets the static `configuredMediaRoot()` MediaProfile.hpp:214-218 at CC:10543 | `mediaExtraRawBuffersForConfiguredRoot`, `mediaTuneForConfiguredRoot` MediaProfile.hpp:222-234 | None | - | - |
| Media snapshot | App watcher `updateCachedMediaSnapshot` App:10893 into statics MediaProbe.hpp:257-290 | CC `rawCameraBufferCount` CC:1458-1470 (configure, under CC `mutex_`); `recorder_.setMediaProfile(detectMediaProfile(cachedMediaSnapshotOrProbe(mediaRoot)))` CC:7737; App:11328 | Static mutex | - | - |

### Media tuning file family and env knobs

| Value or path | Who writes | Who reads | Thread and lock | File | Shown where |
| --- | --- | --- | --- | --- | --- |
| `dontneed` | `scripts/apertar-tune` (Python, 487 lines) or by hand | `dngPageCacheDrop` `src/cdng/CdngEncoder.cpp:84-108`: env > file > `sync`, once per process; used per frame CdngEncoder.cpp:1897, LossyDngEncoder.cpp:104, sync thread CC:4763 | Function static | `/home/pi/apertar-media-tune.conf` and `/run/apertar-media/media-tune.override.conf`, parsed by `src/util/MediaTune.hpp` (318 lines, 4-level section lookup) | journal `ApertarCore media tune:` (first resolution only) |
| `writeback` | same | CC:4715-4720: env > file > on, once per process | Function static | same | - |
| `sync_ms` | same | CC:4364-4365 at each take | Take start | same | - |
| `raw_buffers`, `extra_raw_buffers` | same | `rawCameraBufferCount` CC:1458-1470; `deriveMediaProfile` MediaProfile.hpp:195-202 | Configure; watcher | same | - |
| `workers`, `queue` | same | `deriveMediaProfile` into `mediaProfile_.writer`, used CC:4318-4328 | Take start | same | - |
| `kernel_tune` | same | `applyMediaTuning` App:11402-11410 (root helper `apertar-media-tune`) | Watcher | same | - |
| Template, editor, tmpfiles | repo | - | - | `config/apertar-media-tune.conf` (54 lines, `[default] raw_buffers = 8`), `scripts/apertar-tune`, `config/apertar-media.tmpfiles.conf` (also holds the eject flags and the helper's state dirs) | `README.md:337-358` table of 13 knobs |
| `APERTAR_WEB_PREVIEW_RECORDING_FPS` | systemd drop-in | App:88-106 (read once), App:9784 | Preview publisher | - | README:352 |

## How original Apertar does this kind of thing

| Kind of problem | Precedent `@upstream-1.6.0` | What it shows |
| --- | --- | --- |
| A persisted operator switch that shapes recording | `CaptureSettings` `include/apertar/core/Types.hpp:124-162`; load chain `CC:650-723`; save `CC:745-777`; setter `CC:7774-7786`; three serialisers `App:167-216`, `CC:136-187`, `App:7857-7897` (recipe R2) | One field, one setter that ends in `applySettingsLocked`, one `set_*` command that replies `settingsBody(camera_.settings())`. `CameraController` owns `camera_settings.conf` (CMD-12) |
| A setting kept across record formats | `setRecordingFormat` `CC:7939-7955`: `tuningFile`, `timecodeMode`, `exposureMetering` are saved before the profile swap and restored after (CAM-40) | Camera-wide fields are carried by hand. The port already does this for `mediaTrimEnabled` (CC:11349, :11368) |
| A retired key in a settings file | `wb_locked` is still read into a local `legacyWhiteBalanceLock` (`CC:625`, `:682`) and mapped to the new meaning after the loop (`CC:726-728`). The next save writes only new keys (CMD-14, whole-file save) | Old keys are read, their meaning is taken over, and they vanish at the next write (CAM-25) |
| App syncs a value from one store into the camera at start | `App::start` `App:6845-6856`: reads UI.conf, then calls `camera_.setStillExposureMode` / `camera_.applyCapturePreset` directly, before the control server starts | A one-time start-up takeover between stores is App's job, done with the camera's own setters |
| Writing one hardware-file key from a command | `set_imu_driver` `App:9646-9655` calls `Mpu6050RecordingSession::setConfiguredDriver`, which edits `[imu] driver` in place (`src/hardware/Mpu6050RecordingSession.cpp:604-713`, `:1295-1300`) | Only for wiring of a device class, and only through the class that owns the section (HW-8, HW-10) |
| App-side operator switches | `record_audio_enabled`, `record_gyro_enabled`, `sleep_mode` in UI.conf (`App:1618-1620`, `:1752-1757`; `handleUiToggle` `App:9642-9645`; read at use `App:2774`, `:7037`, `:10634`) | The alternative store for switches only App acts on (see "For the owner" 1) |
| A bench knob | `unsignedEnvValue`, `boolEnvValue` `CC:1027-1061`; used at take start `CC:3329-3330` `maxQueuedFrames_ = unsignedEnvValue("APERTAR_CDNG_QUEUE_FRAMES", defaultQueueFrames, 4, 64)`; an encoder reads once into a static, falling back silently (`src/cdng/CdngEncoder.cpp:51-66`, `src/lossydng/LossyDngEncoder.cpp:96-108`) (R8, CAM-24) | Env only, read where used, never in a settings file, the socket API or the README. The take-start line prints the effective value |
| A bench file for A/B arms without a restart | `tuningOverride(name)` `src/prores/ProresEncoder.cpp:771-813`: env wins, else `NAME=VALUE` from `/home/pi/.apertar-tuning`, re-read at clip open, absent in production | Upstream already has one tuning file, with the env names, for exactly the job the media tuning file does |
| A sensor or format limit | `settings.iso = std::min<uint32_t>(settings.iso, 800u);` `CC:2483` | Limits are literals in the sanitiser, not config |
| A clip-scoped signal from a worker to the controller | `RecordingDropWarning` `src/util/RecordingDropWarning.hpp:10-27`: an atomic latch with a `changed` callback. It is a controller member (`CCH:113`), built in the controller's initialiser list with a lambda that emits an event (`CC:7580-7584`), and passed to the queue by pointer (`CC:3251` `explicit DngRecordingQueue(RecordingDropWarning *warning = nullptr)`). It is read lock-free by `recordingHasDroppedFrames()` (`CCH:87`) | The shape for the gauge, the safety stop and the flush abort: controller-owned, passed by pointer, no globals |
| A background condition that ends a take | `RecordingFailure` `src/util/RecordingFailure.hpp:7-24`, latched by workers; `CameraController::checkRecordingFailure` `CC:8519-8534`; polled by App's 1 Hz `wait()` loop `App:7031-7034` and at `handleCommand` entry `App:9094` | Periodic supervision is `wait()`. It already drains the recorder on the main thread under `commandMutex_` |
| Callbacks from the camera to App | `camera_([this](const std::string &eventJson){ publishEvent(eventJson); }, ...)` `App:6783-6785`; `CameraController(EventCallback, PreviewCallback)` `CCH:31` (CMD-18) | A new camera-to-App path is a constructor callback, never a global |
| Process-wide statics | `captureSettingsPersister()` `CC:885-889`, `LossyDngDiskWriter::instance()` `src/lossydng/LossyDngEncoder.cpp:114-118` | Statics are file-local one-offs in the owner's `.cpp`, never shared mutable state in a header (CAM-27) |
| The media root | `start(const std::string &mediaRoot, ...)` stores `mediaRoot_`; `session_->startRecording(mediaRoot_, settings_, ...)` `CC:8247` | The controller passes its own member down. There is no global |
| Page-cache drop | `::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);` after every cDNG (`src/cdng/CdngEncoder.cpp:1777`) and Lossy DNG (`src/lossydng/LossyDngEncoder.cpp:82`) | Unconditional writer-side drop. No setting |
| Scheduling | `config/apertar-core-capture-priority.conf`: `LimitNICE=-5` under "Permit only a bounded, non-real-time boost"; `scripts/start-apertar-core.sh:21` plain `exec` | No RT, no affinity (PLT-14) |
| Hardware-file sections | `[storage]` holds `mount_path` and `pcie_controller` only (template `App:4308-4310`; readers `UI/src/CfeAutomounter.cpp:172-176`, Core's Python `App:3458-3463`) | `[storage]` belongs to the CFE automounter and the PCIe reset. It is wiring |

There is no upstream precedent for these: a lock-free command path into a draining recorder, a RAM-sized write queue, a safety stop, split clip folders, a merge worker, an automatic test take, or a drive trim. They are listed under "What stays as new ground".

## The target

### Rule the target follows

- **Operator switches about recording and storage** (write buffer, frames per folder, clip merge, automatic pre-roll, drive trim) are `CaptureSettings` fields in `camera_settings.conf`. This is the store `media_trim` already uses. `CameraController` owns them. Each has one setter and one `set_*` command (R2). They are camera-wide: they are carried across format profiles like `mediaTrimEnabled`. They reach the clients through `settingsBody`, `settingsEvent` and the settings block of `/api/state`, next to `preview_tdn`.
- **Recorder tuning** is env only, read where used, and not shown in state (R8). This covers the RAM budget numbers, the safety-stop percent and the write-path knobs.
- **Driver facts** are constants in `CC`. This covers the Clear HDR ISO caps.
- **Live per-take state** sits in objects the controller owns and passes to the queue by pointer, like `RecordingDropWarning`. This covers the gauge, the plan note, the safety-stop latch and the flush abort. App reaches them only through `CameraController` methods and one constructor callback. App-only live state is App members (the pre-roll state).
- **The hardware file** keeps only `[storage] mount_path` and `pcie_controller`, as in 1.6.0.

### Before and after

| Value | Before (store, owner, writer) | After: store and key | Owner | Command | Reaches |
| --- | --- | --- | --- | --- | --- |
| Write buffer | `[storage] buffer`; App edits the file; CC re-reads it; env twin | `camera_settings.conf` `buffer_setting=frames\|ram`; `CaptureSettings::writeBuffer` (enum `WriteBuffer { Frames, Ram }` + `toString` in `Types.hpp`) | `CameraController` | `set_buffer_mode value=frames\|ram` (name kept): `camera_.setWriteBuffer`, refused while recording | `buffer_setting` in the three settings serialisers. The touch UI reads it through `applyCoreState` -> `applyBufferState` (ACB:1411-1412, :2676) unchanged; WebUI top level |
| Frames per folder | `[storage] frames_per_folder`; read twice; env twin | `frames_per_folder=N`; `CaptureSettings::framesPerFolder` (0 or 100..100000, `framepath::parseFramesPerFolder`) | `CameraController` | `set_frames_per_folder value=N` (kept): `camera_.setFramesPerFolder`, refused while recording | `frames_per_folder` in the settings serialisers; WebUI reads the top level |
| Clip merge | `[storage] clip_merge`; static atomic; env twin | `clip_merge_enabled=0\|1`; `CaptureSettings::clipMergeEnabled = true` | `CameraController` stores it; App's merge worker reads `camera_.settings()` | `set_clip_merge_enabled enabled=` (renamed, CMD-7) | `clip_merge_enabled` in the settings serialisers |
| Automatic pre-roll | `[media] preroll`; parsed per request; env twin | `storage_preroll_auto=0\|1`; `CaptureSettings::storagePrerollAuto = false` (the parallel default-off fix) | `CameraController` stores it; App reads it at each trigger | `set_storage_preroll_auto_enabled enabled=` (replaces `set_storage_preroll value=on\|off`, App-5-F2) | `storage_preroll_auto` (name kept: ACB:2736 unchanged) |
| Pre-roll length | `[media] preroll_seconds` | constant `storagepreroll::kDefaultSeconds` (2); the `storage_preroll seconds=` argument stays | App | - | - |
| Drive trim | `camera_settings.conf media_trim` + App copy + env twin | unchanged key `media_trim` (written `0\|1`, read both); App reads `camera_.settings().mediaTrimEnabled` | `CameraController` | `set_media_trim enabled=` (kept; rename is an owner question) | `media_trim_enabled` moves from `system` into the settings serialisers |
| RAM fraction, floor, max | `[storage]` keys + env | env only: `APERTAR_CDNG_QUEUE_RAM_FRACTION`, `_FLOOR_MB`, `_MAX_FRACTION`, read in `planQueueBuffer` | CC | - | journal plan line |
| Safety-stop percent | `[storage] buffer_stop_percent` + env | env only: `APERTAR_CDNG_BUFFER_STOP_PERCENT` (default 90 in ram, 0 in frames) | CC | - | `buffer_stop_percent` stays a status field (the threshold of the active or last take) |
| Clear HDR ISO caps | `[camera]` + own parser | `constexpr uint32_t kClearHdrMaxIso12 = 720, kClearHdrMaxIso16 = 1585;` beside `kLosslessMaxIso` (CC:3100) | CC | - | `iso_max` |
| Gauge + plan note | static `frameBufferGauge()`, static `bufferSettingStorage()` | `RecordingBufferGauge frameBufferGauge_` member of `CameraController`, passed to `DngRecordingQueue` by pointer; the note under the gauge's own small mutex | CC | - | same fields through `frameBufferStatus()` and a new `bufferNote()` |
| Safety stop | static `safetyStopState()` + global `safetyStopHook()` + App thread | `RecordingSafetyStop recordingSafetyStop_` member (latch: `active`, `stopPercent`, `flushDiscarded`), passed to the queue by pointer. Its `changed` callback calls the new third constructor callback `SafetyStopCallback`. App's callback sets `bufferSafetyStopPending_` and notifies `waitCv_`. `wait()` sends `record_stop` | CC (latch), App (the stop) | - | `buffer_safety_stop`, `buffer_stop_percent`, `buffer_flush_discarded` via `camera_.bufferSafetyStop()` (lock-free, like `recordingHasDroppedFrames()`) |
| Flush abort | global registry | `CameraController::abortSafetyStopFlush()`. Public, takes **no** controller `mutex_` (the drain holds it; the header comment says so). It forwards to `session_->recorder_.abortSafetyFlush()`, which takes the queue mutex only | CC | - | App calls it where it does today (before the locks; the command-plane theme decides that spot) |
| Pre-roll live state | static `prerollState()` | App members `storagePrerollActive_` (atomic), `storagePrerollFps_` (atomic), `storagePrerollLast_` under `storagePrerollMutex_` (exists, `ApertarCoreApp.hpp`) | App | - | unchanged fields |
| Media root and media profile | statics `configuredMediaRoot()`, `cachedMediaSnapshot*()` | `CameraController::setMediaProfile(const MediaProfile &)`, called by `runMediaWatcher` where `mediaProfile_` changes (App:10935-10940). Stored under a small `mediaProfileMutex_`, not `mutex_`. `rawCameraBufferCount(clearHdr, extra)` and `recorder_.setMediaProfile` use that copy. App keeps its own last snapshot as a member | App writes, CC reads | - | - |
| Media tuning file family | 2 INI files, Python editor, template, README table | gone (owner decision). Each knob is env only at its read site: `APERTAR_DNG_DONTNEED` (encoder, read once, silent fallback), `APERTAR_DNG_WRITEBACK`, `APERTAR_MEDIA_SYNC_MS`, `APERTAR_RAW_CAMERA_BUFFERS`, `APERTAR_CDNG_UNCOMPRESSED_WORKERS`, `APERTAR_CDNG_QUEUE_FRAMES`, `APERTAR_MEDIA_TUNE`. The per-filesystem defaults stay as the C++ table `writerSettingsFor` | CC / encoder | - | effective values on the `ApertarCore recording clip:` line |

### How old files are taken over

- **camera_settings.conf.** New keys are read with the usual `else if (key == ...)` branch. A missing key keeps the `CaptureSettings` default, which is today's default. `media_trim` keeps its key. The reader accepts `true/false` and `0/1`, and the writer switches to `<< s.member` (commit 25).
- **apertar-hardware.conf.** One block in `App::start`, after `camera_.start()` and the still-settings sync (App:8077-8089), before the control server starts (App:8092). It follows the shape of upstream `App:6845-6856`. A local lambda reads one key with the store's own parser, `hwconf::valueOf(hwconf::parse(hardware::configStore().currentText()), section, key)`. For each old key that is present:
  - Switch keys (`[storage] buffer`, `frames_per_folder`, `clip_merge`, `[media] preroll`): the value is applied with the camera setter, which saves `camera_settings.conf`. One line is logged: `ApertarCore settings: [storage] buffer=ram moved to camera settings`.
  - Tuning keys (`buffer_ram_*`, `buffer_stop_percent`, `[media] preroll_seconds`, `[camera] clear_hdr_iso_max_*`): nothing is applied. If the value differs from the default, one line names the env var that replaces it.
  - Then one `store.edit(..., by "core", backup = true, trusted = true)` removes all those keys, and `[media]` / `[camera]` when they are left empty. The value then lives in one place only, and a later UI change is not overwritten at the next start. The store keeps `<file>.bak` and its history. This is the store's own key-in-place edit (HW-8), done once.
- If the edit fails (a read-only `/boot` copy, a lock), the setter is applied again at each start and the log line says the key could not be removed. See Risks.
- The clip-merge worker start (App:8036-8042) moves below this block. Its current position exists only because `refreshBufferRequest` had to publish the switch first (comment App:8037-8038).

### Who reads what after the change

| Reader | Reads |
| --- | --- |
| `DngRecordingQueue::startAtFolder` | `settings.framesPerFolder` (not for MLV, not for the pre-roll take, as today) |
| `DngRecordingQueue::planQueueBuffer` | `settings_.writeBuffer`; `APERTAR_CDNG_QUEUE_RAM_*` and `APERTAR_CDNG_BUFFER_STOP_PERCENT` through `unsignedEnvValue` / `bufferbudget::parseDouble` at the call |
| App merge worker | `camera_.settings().clipMergeEnabled`; `camera_.bufferSafetyStop().active` |
| App pre-roll triggers | `camera_.settings().storagePrerollAuto` |
| App trim worker | `camera_.settings().mediaTrimEnabled` |
| `bufferMembers` (state, `buffer` event, `/api/buffer`) | `camera_.frameBufferStatus()`, `camera_.bufferNote()`, `camera_.bufferSafetyStop()`, App pre-roll members. These are status fields, so they appear in `get_state` before `settingsBody` and in `/api/state`, not in `settingsBody` (commit 16) |

## Commit plan

Each commit lands with both builds green (`/home/user/build/bin/check_core.sh <tree> <tag> both tests`: libcamera ON and OFF, plus the host tests in `tools/`). `smoke_core.sh <bin> <port>` is diffed against the previous commit: only port-only fields may move or vanish, and every 1.6.0 field stays with its type. "Pi" = what only the camera shows. Socket calls on the Pi use `printf '{"id":1,"cmd":"get_state"}\n' | socat - UNIX-CONNECT:/tmp/apertar-core.sock`.

### 1. core, web: the storage switches have no environment twins
- Repo: Apertar-Core.
- Touches:
  - `App`: `refreshBufferRequest` env arguments App:273-286; `bufferSettingMembers` App:262, :266, :268; `mediaTrimEnvOff` App:6403-6408 and its three uses (:11447, :11467, :11947); `requestStoragePreroll` App:11157-11161; `/api/state` App:9589.
  - `BB`: `requestedBufferMode`, `requestedFramesPerFolder`, `clipMergeEnvOff`, `requestedClipMerge` env parameters.
  - `SP`: `automaticEnabled`, `publishAutomatic`, `automaticFromEnv`.
  - `CC`: :4290-4297 (env read and its stderr line) and :5501-5503, :5524-5528 (env branch of `planQueueBuffer`).
  - `WCP`: "Set by APERTAR_..." and "Forced off by ..." texts and their disable logic (:15839-15849, :16179-16183, :16193-16204, :16206-16210, :13853-13854, :16511-16512, :5818).
  - Tests `tools/storage_buffer_conf_test.cpp:81-82, :97, :121-125`, `tools/storage_preroll_test.cpp` env cases; `README.md:305`, :355-356.
- Deletes `APERTAR_CDNG_BUFFER`, `APERTAR_CDNG_FRAMES_PER_FOLDER`, `APERTAR_CLIP_MERGE`, `APERTAR_STORAGE_PREROLL`, `APERTAR_MEDIA_TRIM` and the state fields `frames_per_folder_env`, `clip_merge_env_off`, `storage_preroll_auto_env`, `media_trim_env_off`.
- Lines: -110 / +15.
- Here: builds, host tests; smoke diff shows only the four `*_env` fields gone; headless Chromium on `--simulate`: Settings > storage card renders, the toggles are enabled.
- Pi: `systemctl cat apertar-core | grep -E 'APERTAR_(CDNG_BUFFER|CDNG_FRAMES|CLIP_MERGE|STORAGE_PREROLL|MEDIA_TRIM)'` must print nothing. If it prints a line, set the same value through the UI first.
- Depends on: nothing.

### 2. core: the Clear HDR ISO caps are constants again
- Repo: Apertar-Core.
- Touches:
  - `CC:2933-3023`: deletes `CameraSection`, `loadCameraSection`, `cameraSection`; adds two `constexpr` beside `kLosslessMaxIso` CC:3100; `clearHdrIsoCap` returns them.
  - `App:5078-5083` template `[camera]` block deleted; `HardwareConfigText.hpp:58` `camera` section entry deleted.
  - `App::start`: the takeover block is born here, with its local lambda and its first lines (log non-default `[camera]` values, unset the section).
  - README text of `[camera]`.
- Lines: -65 / +30.
- Here: builds, tests. With a test hardware file in `--simulate` (`APERTAR_HARDWARE_CONFIG=<tmp>`), `[camera] clear_hdr_iso_max_12bit=600` gives the log line, and the section is gone from the file afterwards (`.bak` kept).
- Pi: `set_raw_bit_depth value=12`, `set_clear_hdr enabled=true`, then `get_state`: `iso_max` 720. At 16-bit: 1585.
- Depends on: the parallel 12-bit Clear HDR fixes. If they change the 12-bit cap (hdr12 G2-X1, G4-3: the cap assumes a +12 dB gain adder), they change the constant, not a key.

### 3. core: the write buffer is a camera setting
- Repo: Apertar-Core.
- Touches:
  - `Types.hpp`: `enum class WriteBuffer { Frames, Ram }` + `toString`; field `writeBuffer`.
  - `CC`: loader branch `buffer_setting` (beside `media_trim`, CC:889); writer line (CC:976); carry-over in `setRecordingFormat` (CC:11349, :11368); setter `setWriteBuffer` beside `setMediaTrimEnabled` (CC:11887), with `recording_` gate "Stop recording before changing the write buffer."; `settingsEvent` line beside `preview_tdn` CC:230; `planQueueBuffer` CC:5495-5545 reads `settings_.writeBuffer` instead of `loadBufferConf()` for the mode.
  - `App`: `settingsBody` line App:368 and the web-state settings line App:9534; `set_buffer_mode` block App:12846-12871 becomes six lines, CMD-5 shape; takeover line for `[storage] buffer`.
  - `BB`: `requestedBufferMode`, `publishBufferRequest` deleted.
  - `WCP`: `mergeCameraStateFields` accepts `buffer_setting`; the patch `case` stays.
- Lines: -45 / +40.
- Here: builds, tests; `--simulate`: `set_buffer_mode value=ram` reply carries `buffer_setting:"ram"`; restart Core: still `ram`; `camera_settings.conf` has `buffer_setting=ram`; WebUI pill flips. Touch UI build (`check_ui.sh`) unchanged: it already reads `buffer_setting` from replies and events.
- Pi: on the owner's camera (file says `buffer=ram`), the first start logs the takeover line, `get_state` says `buffer_setting:"ram"`, and a 4K take logs `ApertarCore buffer: ram budget ...`.
- Depends on: 2 (takeover block).

### 4. core: frames per folder is a camera setting
- Repo: Apertar-Core.
- Touches:
  - `Types.hpp` field `framesPerFolder`.
  - `CC`: loader, writer, carry-over, setter `setFramesPerFolder` (refused while recording); `startAtFolder` CC:4287-4298 uses `settings.framesPerFolder`.
  - `App`: `set_frames_per_folder` split out of the shared block App:12874-12915; three serialiser lines; takeover line; `bufferSettingMembers` loses `frames_per_folder`.
  - `BB`: `framesPerFolderRequest`, `requestedFramesPerFolder` deleted.
  - `WCP:16192-16204`: reads the top level.
- Lines: -40 / +35.
- Here: builds, tests (`frame_path_test` unchanged); `--simulate`: `set_frames_per_folder value=1000` round-trips through a restart; WebUI field shows 1000.
- Pi: a 1-minute 4K take with 1000 produces `part_000`, `part_001`, ... and `.parts`; the playback list opens it.
- Depends on: 3.

### 5. core, web: the clip merge switch is a camera setting
- Repo: Apertar-Core.
- Touches:
  - `Types.hpp` `clipMergeEnabled = true`.
  - `CC`: loader, writer, carry-over, setter (no recording gate; the worker pauses by itself).
  - `App`: `set_clip_merge_enabled` block (CMD-5 shape, then `clipMerge("switch")` when on); `clipMergeMayRun` App:11707 and `runClipMerge` App:11753, :11782 read `camera_.settings().clipMergeEnabled`; the merge worker start App:8036-8042 moves below the takeover block; three serialiser lines; `help` literal; takeover line for `[storage] clip_merge`.
  - `BB`: `clipMergeRequest` deleted.
  - `WCP:16211-16213`: command name and top-level read.
- Lines: -35 / +30.
- Here: builds, tests; `--simulate`: toggle off/on, restart, state agrees; `clip_merge_test` unchanged.
- Pi: record a split clip, switch merge on, idle: journal `ApertarCore clip merge: start ... done`.
- Depends on: 4.

### 6. core, web: the automatic pre-roll switch is a camera setting
- Repo: Apertar-Core.
- Touches:
  - `Types.hpp` `storagePrerollAuto = false`.
  - `CC`: loader, writer, carry-over, setter.
  - `App`: `set_storage_preroll_auto_enabled` (strict `enabled=` test, CMD-8) replaces `set_storage_preroll` App:12917-12942; `requestStoragePreroll` App:11156-11162 reads `camera_.settings().storagePrerollAuto` and `kDefaultSeconds`; three serialiser lines; `help`; takeover lines for `[media] preroll` (applied) and `preroll_seconds` (logged).
  - `SP`: `PrerollConf`, `parsePrerollConf`, `effectiveSeconds`' conf parameter, `publishAutomatic` deleted.
  - `WCP:15841-15849`, :14030-14032.
  - `tools/storage_preroll_test.cpp`: conf cases out.
- Lines: -70 / +30.
- Here: builds, tests; `--simulate`: the toggle round-trips; with it off, a `mount_media` gives no pre-roll log line.
- Pi: switch on, reinsert the CFexpress card: journal `ApertarCore storage preroll: reason=mount ... ok`.
- Depends on: 5; the parallel "pre-roll default off" branch (merge it first, so the default here is `false`); the preroll theme owns the take itself.

### 7. ui: the storage pre-roll switch sends set_storage_preroll_auto_enabled
- Repo: Apertar-UI.
- Touches: `ApertarControlBridge::applyStoragePrerollAuto` ACB:624-630 sends `enabled=true|false`.
- Lines: -3 / +3.
- Here: `check_ui.sh` build; drive with a fake Core socket if the touch-ui theme provides one, else Pi.
- Pi: Settings > Media > pre-roll toggle flips; `get_state` follows.
- Depends on: 6. Core and UI ship together (CMD-30). The touch-ui theme removes the `storagePrerollAutoKnown` latch (UI-control-bridge-F9).

### 8. core, web: drive trim reads the camera setting; App keeps no copy
- Repo: Apertar-Core.
- Touches:
  - `App`: `mediaTrimSetting_` (`ApertarCoreApp.hpp:299`) and App:8077, :13214 deleted; trim worker reads `camera_.settings().mediaTrimEnabled` (:11447, :11467, :11947); `media_trim_enabled` moves from `system` App:9588 into the three settings serialisers.
  - `WCP:16184`: top-level read.
- Lines: -10 / +8.
- Here: builds; `--simulate` toggle.
- Pi: `set_media_trim enabled=false`, delete a clip: no `ApertarCore media trim` line.
- Depends on: 1.

### 9. core: the RAM budget numbers and the safety-stop percent are bench knobs only
- Repo: Apertar-Core.
- Touches:
  - `CC:5505-5537` `planQueueBuffer` no longer opens the file: `APERTAR_CDNG_QUEUE_RAM_FRACTION`/`_FLOOR_MB`/`_MAX_FRACTION` and `APERTAR_CDNG_BUFFER_STOP_PERCENT` only, with the same defaults and bounds.
  - Takeover lines log non-default values with the env name.
  - Template App:5051-5063: the four keys and their comments go.
  - `README.md` text.
- Lines: -30 / +12.
- Here: builds; `buffer_budget_test` unchanged; the takeover log appears with a test file.
- Pi: `journalctl -u apertar-core -b | grep 'ApertarCore settings'` on the owner's camera. If a value was not the default, set the env var in a drop-in.
- Depends on: 3.

### 10. core: the [storage] and [media] readers are gone
- Repo: Apertar-Core.
- Touches:
  - `BB`: `BufferConf`, `bufferConfProblem` (all but the stop-percent rule `parseStopPercent` uses), `parseBufferConf`.
  - `CC:2986-3006` `loadBufferConf`.
  - `App:273-286` `refreshBufferRequest` and its calls App:8038, :8149, :8668, :12824.
  - `HardwareConfigText.hpp:830-845` rules and the `storage`/`media` entries' special handling (`storage` stays `Raw` for `mount_path`).
  - The includes of `BufferBudget.hpp`/`StoragePreroll.hpp` in `src/hardware` (HW-config-text-store-F10).
  - `tools/storage_buffer_conf_test.cpp`: deleted. Its `safetyStopReached` and `effectiveStopPercent` checks move to `tools/buffer_budget_test.cpp`.
- Lines: -260 / +15.
- Here: builds; host tests (one file fewer); WebUI Config pane: a file with `buffer=ram` now shows an unknown-key warning, not an error.
- Pi: none beyond 3-9.
- Depends on: 3-6, 9.

### 11. core: the write queue's gauge and plan note are controller members
- Repo: Apertar-Core.
- Touches:
  - New `src/util/RecordingBuffer.hpp`. Precedent: `src/util/RecordingDropWarning.hpp`, `RecordingFailure.hpp`, clip latches in `src/util` (CAM-6). It holds `struct RecordingBufferGauge` (moved from CC:4169-4180, plus `std::mutex noteMutex; std::string note;`).
  - `CCH` member `RecordingBufferGauge frameBufferGauge_;` beside `recordingDropWarning_`.
  - `DngRecordingQueue(RecordingDropWarning *, RecordingBufferGauge *)` at CC:4191; `CameraSession` constructor CC:7252-7257 passes it on.
  - `frameBufferStatus`/`rawTakeActive` read the member; new `std::string bufferNote() const` (gauge mutex only).
  - `BB:276-301` `bufferSettingStorage`/`publishBufferSetting` deleted; `bufferSettingMembers` reads `camera_.bufferNote()`.
- Lines: -45 / +40.
- Here: both builds (the struct must stay outside `#if APERTARCORE_HAS_LIBCAMERA`, as today); `--simulate` `/api/buffer` shape unchanged.
- Pi: a take with the buffer bar on: the bar rises and falls; `buffer_note` shows the plan line in ram mode.
- Depends on: 10.

### 12. core: the buffer safety stop is a latch the controller owns
- Repo: Apertar-Core.
- Touches:
  - `RecordingBuffer.hpp`: `class RecordingSafetyStop`, shaped like `RecordingDropWarning`: atomics `active`, `stopPercent`, `flushDiscarded`, plus `fire()`, `clear()`, `setThreshold()` and a `changed` callback.
  - `CCH` member; built in the CC initialiser list (CC:10486-10495) with a lambda that emits `{"event":"buffer","buffer_safety_stop":...,"buffer_stop_percent":...}` through `eventCallback_`.
  - Queue gets a pointer; every `bufferbudget::safetyStopState()` use (CC:4600, :4614, :4621, :5016-5017, :5441, :5490, :5517-5518, :12442) goes to the member.
  - New `CameraController::bufferSafetyStop()` (lock-free struct getter, like `recordingHasDroppedFrames()` CCH:172).
  - App uses (App:255-259, :8428, :11004-11019, :11710) call it.
  - `BB:222-234` deleted.
- Lines: -40 / +45.
- Here: both builds; `buffer_budget_test`.
- Pi: `APERTAR_CDNG_BUFFER_STOP_PERCENT=50` drop-in, `buffer_setting=ram`, 4K 16-bit to a slow card: the take stops by itself; touch UI shows "The write buffer reached 50 %."; WebUI pill shows the flush.
- Depends on: 11.

### 13. core: the safety stop reaches App through a constructor callback; wait() stops the take
- Repo: Apertar-Core.
- Touches:
  - `CCH:23-25, :54`: `using SafetyStopCallback = std::function<void()>;`, a third constructor parameter, member `safetyStopCallback_`; the latch's `changed` lambda calls it when the latch rises.
  - `App` initialiser list App:7980-7982 passes `[this]{ bufferSafetyStopPending_.store(true); waitCv_.notify_all(); }`; the constructor body App:7991-7998 goes.
  - `wait()` App:8289-8320: the predicate also wakes on the pending flag, and the loop body runs `dispatchHardwareInputCommand(record_stop)` with the journal line now at App:11108-11111.
  - `runBufferSafetyStop` App:11087-11118, its start, its stop block App:11076-11079 and members `ApertarCoreApp.hpp:271-280` (except the pending flag) deleted.
  - `BB:254-266` `SafetyStopHit`, `safetyStopHook` deleted.
- Lines: -70 / +25.
- Here: both builds; `--simulate` start/stop clean (no thread left; `valgrind --tool=helgrind` optional).
- Pi:
  - Same as 12, and the journal shows `ApertarCore buffer: safety stop at` within about 0.1 s of the event. The worst case is 1 s (a lost notify falls to `wait()`'s 1 s tick, upstream's supervision cadence).
  - `journalctl -o short-precise` gives the two timestamps.
  - Unsafe without the Pi: the reaction time. The smallest safe version keeps the 1 s tick as the backstop, which is never slower than 1.6.0's failure supervision.
- Depends on: 12.

### 14. core: the safety-stop flush abort is a CameraController method
- Repo: Apertar-Core.
- Touches:
  - `CCH`: `int64_t abortSafetyStopFlush();` with a one-line comment: "No controller mutex: stopRecording holds it while the queue drains."
  - `CC`: forwards through `session_` (never reset) to `recorder_.abortSafetyFlush()` CC:4610-4624 (queue mutex only); `#else` branch returns -1 (CAM-28); `registerFlushAbort`/`unregisterFlushAbort` CC:4626-4636 and their calls CC:4211, :4271, :4594 deleted.
  - `App:291-299` calls `camera_.abortSafetyStopFlush()`.
  - `BB:236-252` deleted.
- Lines: -30 / +15.
- Here: both builds.
- Pi: during the safety-stop flush of 12, press REC: journal `flush aborted by record, N unwritten frames ... discarded`, a new take starts, `buffer_flush_discarded` = N.
- Depends on: 13. The command-plane theme decides whether the call stays before the lock (App-1-F13).

### 15. core: the storage pre-roll's live state is App members
- Repo: Apertar-Core.
- Touches:
  - `SP:224-271`: `PrerollState`, `prerollState`, `prerollActive`, `prerollFps`, `prerollLast`, `setPrerollLast` move to App members under the existing `storagePrerollMutex_`, plus two atomics; `prerollFpsText` stays pure.
  - Uses in `runStoragePrerollOnce`, `bufferSettingMembers`, `runBufferEvents`, `clipMergeMayRun`, `storagePrerollGuard`.
- Lines: -45 / +30.
- Here: both builds; `storage_preroll_test`.
- Pi: a manual `storage_preroll`: `storage_preroll_active` true then false, `_last` "ok: ...".
- Depends on: 6. If the preroll theme's rework of the pre-roll take (CC-6-F3, App-4-F2) lands first and already removes these statics, drop this commit.

### 16. core: get_state carries the buffer status; settingsBody carries camera settings only
- Repo: Apertar-Core.
- Touches:
  - `App:393` `<< "," << bufferSettingMembers()` leaves `settingsBody` and goes into the `get_state` body before `settingsBody` (CMD-11), next to `clipMergeStateJson()`.
  - `bufferSettingMembers` is rewritten as an `ostringstream` chain (CMD-9).
- Lines: -16 / +14.
- Here: smoke diff: `get_state` keeps every field; `set_iso` replies lose only port status fields; touch UI still fed by `get_state` and the `buffer` event (ACB:1345-1349, :1732).
- Pi: none.
- Depends on: 3-6, 11-15.

### 17. core: the camera gets the media profile from App
- Repo: Apertar-Core.
- Touches:
  - `CCH`: `void setMediaProfile(const MediaProfile &profile);` and a member pair `mediaProfileMutex_`, `mediaProfile_`.
  - `App::runMediaWatcher` calls it where `mediaProfile_` changes (App:10935-10940).
  - `rawCameraBufferCount(bool clearHdr, unsigned extra)` CC:1458-1470; its callers CC:8381, :8736, :8848 pass the copy's `writer.extraRawBuffers`; CC:7737 uses the copy.
  - `MediaProfile.hpp:214-234` (`configuredMediaRoot`, `mediaExtraRawBuffersForConfiguredRoot`, `mediaTuneForConfiguredRoot`) and CC:10543 deleted.
  - `MediaProbe.hpp:257-290` statics: App keeps its last snapshot as a member under `mediaStateMutex_` (App:10893, :11328).
- Lines: -55 / +35.
- Here: both builds; `--simulate` with a mounted tmpfs as `--media`: the profile log line appears once.
- Pi:
  - exFAT CFexpress: `ApertarCore media profile: class=pi-nvme fs=exfat workers=4 queue=12 raw_buffers=+0`; the take-start line shows the same workers.
  - Before the first watcher cycle the profile is empty: upstream defaults, safe.
- Depends on: 11.

### 18. core, cdng: the write-path knobs are environment knobs only
- Repo: Apertar-Core. Gated on owner decision 3.
- Touches:
  - `CdngEncoder.cpp:84-108` `dngPageCacheDrop`: env only, silent fallback to `sync`, read once (the `configuredLosslessTileRows` shape); drops the `MediaProfile.hpp` and `<iostream>` includes.
  - `CC:4715-4720` `boolEnvValue("APERTAR_DNG_WRITEBACK", true)`; `CC:4364-4365` `unsignedEnvValue("APERTAR_MEDIA_SYNC_MS", 1000, 0, 60000)`.
  - `rawCameraBufferCount`: `unsignedEnvValue("APERTAR_RAW_CAMERA_BUFFERS", std::min(16u, base + extra), 3, 16)`.
  - `deriveMediaProfile` MediaProfile.hpp:192-203: no tune merge; `loadMediaTuneLogged` MediaProfile.hpp:170-181 deleted.
  - `applyMediaTuning` App:11402-11410: `APERTAR_MEDIA_TUNE=1` only.
  - `tune_override=` leaves the clip line.
  - Delete `src/util/MediaTune.hpp`.
- Lines: -360 / +12.
- Here: both builds; host tests; `grep -rn MediaTune src` empty.
- Pi:
  - The owner's rig without the files: `ls ~/apertar-media-tune.conf /run/apertar-media/media-tune.override.conf`. If one exists, its values become a drop-in.
  - A 3-min 4K Clear HDR 16-bit 25 fps take: drops equal to the last campaign baseline.
- Depends on: 17.

### 19. scripts, config, docs: the media tuning file, its editor and the README knob table are gone
- Repo: Apertar-Core. Gated on owner decision 3.
- Touches: delete `scripts/apertar-tune`, `config/apertar-media-tune.conf`; `README.md:337-358` section; KB link texts. `config/apertar-media.tmpfiles.conf` stays until the boot-config-helpers theme removes the eject flags and the kernel helper (it still makes their directories).
- Lines: -560 / +0.
- Here: `git grep -n 'apertar-tune\|media-tune.override'` empty.
- Pi: test-night scripts (`b1-arm.sh` and others in the KB) go back to drop-ins.
- Depends on: 18.

### 20. cdng: the page-cache drop falls back to the writer when the sync thread is off
- Repo: Apertar-Core.
- Touches:
  - `dngPageCacheDrop` returns `Writer` when the mode is `Sync` and `APERTAR_MEDIA_SYNC_MS` is 0 (both env, both fixed for the process).
  - The one-time warning CC:4370-4377 goes.
  - Lossy DNG is already back to upstream's unconditional drop on the parallel branch.
- Lines: -10 / +6.
- Here: both builds; `dng_payload_write_test.sh`.
- Pi: `APERTAR_MEDIA_SYNC_MS=0`, a 1-min take: `free -m` buff/cache does not climb by the clip size.
- Depends on: 18; the parallel Lossy DNG page-cache fix.

### 21. core: switches of finished A/B tests are gone
- Repo: Apertar-Core.
- Touches:
  - `APERTAR_RAW_POOL_WARM` CC:4892-4899 (keeps the warm pool).
  - `APERTAR_RAW_COPY_WORKERS` CC:4386 (1 worker).
  - `APERTAR_AUDIO_BUFFER_MS` `src/audio/AudioRecordingSession.cpp:208-218` (100 ms constant).
  - `APERTAR_WEB_PREVIEW_RECORDING_FPS` App:83-106, :9784 (30 = `kWebPreviewMaxFps`, so with the env unset nothing changes).
- `APERTAR_DNG_PAYLOAD_COPY` stays: `tools/dng_payload_write_test.sh:13-14` uses it as the byte-identity oracle.
- Lines: -45 / +5.
- Here: builds; host tests; `--simulate` WebUI preview runs.
- Pi: one 4K take, drops at baseline.
- Depends on: nothing.

### 22. core: knobs nobody set are constants
- Repo: Apertar-Core.
- Touches:
  - `APERTAR_DEAD_MEDIUM_STOP_MS` CC:4469 (2000 ms).
  - `APERTAR_WRITE_STALL_MS` CC:4861 (5000 ms).
  - `APERTAR_PLAYBACK_WORKERS` `src/playback/PlaybackFrames.cpp:82` (2).
  - `APERTAR_PHASE_LOCK_KP/_KI/_DEADBAND_US/_CLAMP_US` CC:8910-8921 (the `FramePhaseLock.hpp:38-41` defaults stay).
  - `APERTAR_MEDIA_MIN_FREE_MB` App:11383 (1024).
- Lines: -40 / +6.
- Here: builds, tests.
- Pi: none (defaults unchanged).
- Depends on: nothing.

### 23. scripts, config, camera: no real-time scheduling
- Repo: Apertar-Core.
- Touches:
  - `scripts/start-apertar-core.sh:20-44` back to the upstream `exec` (`scripts/start-apertar-core.sh:21@upstream-1.6.0`).
  - `config/apertar-core-capture-priority.conf`: `LimitRTPRIO=80` and its comment out.
  - CC:9109-9127 `APERTAR_RT_CAPTURE_PRIORITY` block; README rows.
- Lines: -45 / +1.
- Here: `bash -n scripts/start-apertar-core.sh`; builds.
- Pi: `systemctl restart apertar-core`; `chrt -p $(pidof apertar-core)` reports SCHED_OTHER; the capture thread still gets nice -5 (`ps -eLo tid,ni,comm | grep -i apertar`).
- Depends on: nothing.

### 24. core: conform_fps and the unused writer field directIo are gone
- Repo: Apertar-Core.
- Touches:
  - `Types.hpp:137`; `CC:696-697` loader/writer; `set_conform_fps` and the `help` entry; three serialiser lines; preset key `cameraConformFps` App:7851 and its reader; the carry-over line CC:11360.
  - `MediaProfile.hpp:133` and the 4th value of each `writerSettingsFor` row.
- Lines: -30 / +0.
- Here: builds; smoke diff: `conform_fps` gone (port-only).
- Pi: none.
- Depends on: 3 (same carry-over block).

### 25. core: port booleans in camera_settings.conf are written 0/1
- Repo: Apertar-Core.
- Touches: `CC:974-979` and the new keys of 3-6 write `<< s.member`; the reader keeps accepting `true/false` (CC:885-898).
- Lines: -8 / +8.
- Here: a host round-trip of `writeCaptureSettings`/load in `--simulate` (set, restart, `get_state`).
- Pi: none.
- Depends on: 3-6.

Totals: about -2 000 / +450. Optional commit 26 (owner decision 6): the write queue emits the `buffer` event on level change, rate-limited to 4/s in the queue, and `runBufferEvents` goes. That is -60 / +35 and needs the Pi.

## What stays as new ground

| Feature | Shape it keeps | Why that shape |
| --- | --- | --- |
| RAM-sized write queue (`buffer_setting=ram`) and its plan (`planBuffer`, BB) | One camera setting, pure planning maths in a header (CAM-4), env bench knobs for the numbers | Upstream has a fixed 12/24-frame queue. The RAM mode refuses itself on small boards ("staying on frames"), so a 1-2 GB Pi keeps 1.6.0 behaviour |
| Safety stop (take ends itself at N % full) | A clip latch shaped like `RecordingDropWarning`; one constructor callback; `wait()` stops the take as it does for `RecordingFailure` | Nearest upstream patterns. The callback exists only to stop in about 0.1 s rather than 1 s; at 90 % of a small buffer, 1 s can be too slow |
| Flush abort during the safety-stop drain | One public `CameraController` method that takes no controller mutex, called before the command lock | The drain holds `commandMutex_` and the controller mutex for seconds. No upstream path does that, so no upstream shape exists. The lock-order exception is written in the header |
| Live buffer level in state, `/api/buffer`, `buffer` events thread | Kept as today (commit 26 optional) | Upstream publishes no queue depth (conventions section 5). The thread exists because the drain holds the mutex the state path needs. A lock-free read route is the smallest way |
| Split clip folders and the merge worker | Two camera settings; the merge worker is an App worker with its own state group (CMD-21 shape) | No upstream precedent; exFAT directory cost on long takes |
| Automatic storage pre-roll | One camera setting, default off | No precedent; the take itself is the preroll theme's |
| Drive trim | One camera setting; the helper is the boot-config-helpers theme's | No precedent |
| Writer topology per filesystem (`writerSettingsFor`) | C++ table, env overrides only | Upstream has one default per format |
| Sync thread and page-cache drop `sync` | Env knobs, read where used; default `sync` for cDNG pending owner decision 4 | Measured on the owner's rig (4K Clear HDR 16-bit 25 fps: 0 lost vs 34-153). Departs from CAM-37 "clip frames are not synced one by one" |
| Shared header `src/util/RecordingBuffer.hpp` | Two small types, no logic beyond atomics | Precedent `RecordingDropWarning.hpp`, `RecordingFailure.hpp` |

## For the owner

| # | Question | Options | Recommendation and cost |
| --- | --- | --- | --- |
| 1 | Where do the switches App acts on (clip merge, automatic pre-roll, drive trim) live? | a) `camera_settings.conf`, beside `media_trim`; b) UI.conf like `record_audio_enabled`, `sleep_mode` (App:9642, :7037@upstream); c) the hardware file through an owner function (App-5-F1) | a). One store for the whole family, no touch-UI rework, no second migration for `media_trim`; the touch UI already gets the fields from settings events. Cost: `CameraController` stores three values it never uses itself. b) is the closer upstream precedent for "App acts on it" but needs a `SettingsBridge` property per switch in the touch UI (R3, about 40 lines each) and moves `media_trim` again. c) keeps operator preferences in the wiring file (HW-10 says no) |
| 2 | May the write buffer and frames per folder change during a take? | a) refuse "Stop recording before ..." (CAM-31); b) allow, apply at the next take (today) | a). One sentence; matches every other stream-shaping setter |
| 3 | The media tuning file family | a) delete; env knobs only (commits 18-19); b) a) plus upstream's `/home/pi/.apertar-tuning` for the per-take knobs (move `tuningOverride` from `ProresEncoder.cpp:771-813` into a header, read `SYNC_MS`, `RAW_CAMERA_BUFFERS`, workers, queue at take start: +40 lines); c) keep it, drop the `/run` override and the Python editor, document it | a), or b) if test nights without restarts are still wanted. You asked for the file on 2026-11-02; per-medium sections are lost either way |
| 4 | cDNG page-cache drop default | a) `sync` (measured on Clear HDR 16-bit); b) `writer` (1.6.0) | a), with the measurement in the handoff, because the rig numbers favour it. Cost: a stock camera differs from 1.6.0 here (Lossy DNG is back to 1.6.0 already) |
| 5 | Safety-stop reaction | a) constructor callback + `wait()` (about 0.1 s); b) `wait()` poll only (up to 1 s) | a). +1 constructor parameter |
| 6 | Buffer events thread and the 4 Hz `/api/buffer` | a) keep, documented; b) commit 26, queue-emitted events | a) now, b) after a Pi test |
| 7 | Command names | Rename `set_clip_merge` -> `set_clip_merge_enabled`, `set_storage_preroll` -> `set_storage_preroll_auto_enabled` (done in 5, 6); also `set_media_trim` -> `set_media_trim_enabled`? | Rename all three: one shape (CMD-7). Cost: your campaign scripts change one word |
| 8 | Storage switches in presets? | a) no, with a one-line comment in `buildCurrentPresetPayload`; b) add `camera<Name>` keys | a). A preset is a look, not drive maintenance |
| 9 | Safety-stop percent | a) env knob only (commit 9); b) a camera setting with a UI | a). Nobody set it outside tests (`=50` twice) |
| 10 | Takeover writes the hardware file once at first start | a) yes, remove moved keys (`.bak` kept); b) leave them and re-apply each start | a). b) would undo a later UI change at every restart |
| 11 | `APERTAR_MEDIA_REQUIRE_MOUNT` (record gate opt-out) | a) keep as a developer env; b) fold into `--simulate` | a) for now; this belongs to the record gate, outside this theme |

## Risks and what was not determined

- **Takeover on a read-only file.** If the only hardware file is under `/boot/firmware`, the store may not be able to unset keys. Then the old value is applied again at every start. The log says so. Not checked: what `HardwareConfigStore` does when it found the file under `/boot`. Settle with `--simulate` and `APERTAR_HARDWARE_CONFIG` pointing to a read-only file.
- **The owner's drop-ins.** Env knobs removed in commits 1, 21 and 22 may be set on the rig. Check `systemctl cat apertar-core` before merging. The same applies to the media tuning files before commit 18.
- **The drain on the main thread.** With commit 13, `wait()` drains the queue under `commandMutex_`. Upstream's `checkRecordingFailure` already does this, but the idle-standby check pauses for the drain. Not measured how long a RAM-mode drain takes on the owner's rig. The KB says seconds.
- **Lock-free abort lifetime.** `session_` is created in the constructor and never reset (`grep session_.reset` = 0 hits), so forwarding without `mutex_` is safe today. A future `session_` reset would break it. The header comment names this.
- **Parallel branches.** These touch the same lines: pre-roll default off (`SP`, template), Lossy DNG page-cache drop (`LossyDngEncoder.cpp:104`), the 12-bit Clear HDR fixes (`clearHdrIsoCap`), and `test_input`/preview TDN (App near :12583). Rebase order: those first, then this series.
- **Other themes.**
  - command-plane: the abort before the lock (App-1-F13); `errorReplyBody` in the deleted store blocks.
  - webui-state: the `system.*` copy loop (WCP-07-F3), the 4 Hz poll.
  - touch-ui: the `storagePrerollAutoKnown` latch, the six void invokables.
  - preroll: the take, `decideGuard`'s unused `Trigger`.
  - boot-config-helpers: the trim and media-tune root helpers, `apertar-media.tmpfiles.conf`, `APERTAR_BOOT_CONFIG`, `APERTAR_MEDIA_TUNE`.
  - hardware-inputs: `hold_ms`/`double_ms` in `knownKey`, the `configStore()` singleton.
  - camera-modes: `APERTAR_FPS_LIMIT`, `APERTAR_LOSSLESS_FPS_LIMIT`, `APERTAR_IMX283_PROBE_FPS`, `APERTAR_IMX585_MIN_MODE_WIDTH`.
- **Host test count.** Commit 10 deletes `storage_buffer_conf_test.cpp` (its useful checks move), so `check_core.sh` reports one test fewer.
- **Pi models.**
  - No commit here changes board-specific behaviour. The RAM mode already falls back to frames on small boards, and the moved settings keep their defaults.
  - Not checked on a Pi 4 / CM4: how the RAM plan behaves with 2 GB and the desktop UI running. The plan line in the journal shows it.
  - The per-filesystem writer table (Media-fault-tune-F5, CC-2-F17) was measured on one CM5 only and is not changed here.
- **Not determined:**
  - whether the owner's hardware file holds non-default `buffer_ram_*` or `buffer_stop_percent` values (the takeover log will say);
  - whether any of his scripts send `set_storage_preroll value=` or `set_clip_merge` (grep the KB test scripts before commit 5).

## Findings covered

| Finding | Commit |
| --- | --- |
| Media-buffer-split-F1 | 3, 4, 5, 6, 9, 10 |
| App-1-F2 | 3, 4, 5, 6, 10, 11, 12, 13, 14, 15 |
| App-1-F3 | 1, 21 (`APERTAR_WEB_PREVIEW_RECORDING_FPS`); `APERTAR_BOOT_CONFIG` not covered: boot-config-helpers theme |
| App-2-F3 | 13 (hook), 14 (`flushAbortFunction`) |
| App-2-F5 | 1, 5, 6, 8 |
| App-5-F1 | 3, 4, 5, 6: the three store blocks are deleted. The finding's "keep in the hardware file" rework is not taken (owner decision 1, HW-10) |
| CC-2-F1 | 2 |
| CC-2-F2 | 3, 4 |
| CC-2-F6 | 18, 19 |
| CC-2-F7 | 12, 14 |
| CC-3-F1 | 11, 12, 13, 14 |
| CC-3-F2 | 3, 4, 9, 18 |
| Media-buffer-split-F2 | 11, 12, 13, 14, 15 |
| Media-buffer-split-F3 | 13 (safety-stop thread); the buffer events thread is owner decision 6 / optional 26 |
| Media-fault-tune-F1 | 18, 19 |
| Media-fault-tune-F3 | 17 |
| Build-scripts-docs-F1 | 18, 19 (owner decision 3 option b keeps `.apertar-tuning`) |
| Build-scripts-docs-F2 | 19 |
| Build-scripts-docs-F3 | 23 |
| Encoders-audio-F1 | 18 |
| Encoders-audio-F2 | 20; Lossy part done on the parallel branch; the cDNG default is owner decision 4 |
| X-knobs-6 | 18, 19 |
| X-knobs-7 | 3, 4, 5, 6 |
| X-knobs-8 | 1 |
| X-knobs-9 | 21, 22, 23 for the write path, audio, playback, phase lock, RT. `APERTAR_DNG_PAYLOAD_COPY` kept (host test oracle). Camera-mode knobs: camera-modes theme. `APERTAR_MEDIA_RUN_DIR`, `APERTAR_MEDIA_TUNE`: boot-config-helpers. `APERTAR_MEDIA_REQUIRE_MOUNT`: owner decision 11 |
| X-knobs-12 | 24 (`conform_fps`, `directIo`); `hold_ms`/`double_ms`: hardware-inputs theme |
| X-knobs-13 | 2 |
| X-commits-core-2-7 | 1, 18-23 remove the knobs going forward; rewriting the history is the commit-clarity task |
| Taken along: App-1-F1, X-state-consistency-7 | 16 |
| Taken along: CC-2-F8 | 11 |
| Taken along: CC-2-F11 | 4 (frames-per-folder parse); the fps knobs: camera-modes theme |
| Taken along: CC-3-F9 | 9, 21; DONTNEED `sync` mode is owner decision 4 |
| Taken along: CC-1-F2, CC-5-F10 | 17, 18 |
| Taken along: App-4-F5 | 1, 22 |
| Taken along: App-4-F6 | 12, 15; `configStore()`: hardware-inputs theme |
| Taken along: App-4-F9 | owner decision 6 / 26 |
| Taken along: App-4-F17 | 18 |
| Taken along: Media-buffer-split-F9 | 1, 10; `Trigger` parameter: preroll theme |
| Taken along: Media-buffer-split-F10, HW-config-text-store-F14 | 3-6 (store blocks); frame-number rule copies not covered (playback) |
| Taken along: HW-config-text-store-F10 | 10 |
| Taken along: WCP-07-F7 | 1 |
| Taken along: WCP-07-F3 | 3-6 move the settings to the top level; the copy loop: webui-state theme |
| Taken along: App-5-F2 | 6; owner decision 7 for the other renames |
| Taken along: CC-1-F4, X-knobs-19 | 25 |
| Taken along: Media-fault-tune-F13 | 18 |
| Taken along: App-3-F3 | 21 |
| Taken along: X-state-consistency-14 | owner decision 8 |
| Not covered: Media-fault-tune-F5, CC-2-F17 (writer table without measurement) | needs Pi measurements on vfat/NTFS; outside this theme's moves |

## Challenge

Checked against Apertar-Core `core-work` `0d13a6f` (seven commits after the design's `7dc6f7a`: pre-roll default off `0977dd6`, Lossy DNG drop `615b48c`, preview TDN x3, `test_input`, `media_state`), Apertar-UI `ui-work` `ac1fc28`, upstream 1.6.0 `35dbe67` / `43888e5`. Port lines are `@0d13a6f`, upstream lines `@upstream-1.6.0`. All rows **confirmed** (read in code) unless marked.

| # | Point | What the design says | What the code says, file:line | What must change |
| --- | --- | --- | --- | --- |
| 1 | b, d: commit 13 stops Core | `wait()`: "the predicate also wakes on the pending flag" | `App:8293-8296` `if (waitCv_.wait_for(lock, 1s, pred)) break;` - a true predicate leaves the loop. `src/main.cpp:129-134`: after `app.wait()` returns, `main` calls `app.stop()`. Done as written, every safety stop shuts Core down | The pending flag must not enter the `break` predicate. Wake with `wait_for` and no predicate change, then test `bufferSafetyStopPending_.exchange(false)` after `lock.unlock()`, next to `checkRecordingFailure` (`App:8299-8301`) |
| 2 | e, a: commit 13 adds a constructor parameter that upstream does not need | New `SafetyStopCallback` third constructor parameter (owner decision 5 cost "+1 parameter") | Upstream App already reacts to camera events by their content: `publishEvent` -> `handleTriggerEvent` (`App:10823-10825`, `:10854-10870@upstream`: `still_exposure`, `recording`, `photo_capture` drive the LED and trigger). Commit 12 already sends `{"event":"buffer","buffer_safety_stop":true,...}` through `eventCallback_` | Drop the third parameter. In `handleTriggerEvent`, a `buffer` event with `"buffer_safety_stop":true` sets `bufferSafetyStopPending_` and notifies `waitCv_`. Zero new API; owner decision 5 becomes "0.1 s via the event, or the 1 s poll" at no cost difference |
| 3 | b: commit 13 loses the journal numbers | Latch holds `active`, `stopPercent`, `flushDiscarded`; the callback is `std::function<void()>` | The stop line `App:11104-11107` prints `used/capacity` and `MiB`/`frames` from the hook's `SafetyStopHit` (`App:7992-7998`, `CC:5019-5020`) | The latch also stores `used`, `capacity`, `ram` (three atomics) when it fires, or the line loses them |
| 4 | b, c: storage setters go through `applySettingsLocked` | "setter beside `setMediaTrimEnabled`" ending in `applySettingsLocked` (commits 3-6, 8) | `applySettingsLocked` refuses in standby (`CC:12743-12746` "Wake the camera before changing capture settings.") and during the pre-roll (`CC:12747-12750`), pushes `session_->applyControls` (`CC:12766`) and on failure sets `state_ = Error` (`CC:12782`). Today `set_buffer_mode`, `set_clip_merge`, `set_storage_preroll` are file edits and work in standby (`App:12846-12943`). Upstream has a setter that skips the session: `setTuningFile` no-session branch `settings_ = next; persistSettingsLocked(); emitSettingsEventLocked();` (`CC:8077-8084@upstream`) | The five storage setters use that shape: assign the field in `settings_`, `persistSettingsLocked()`, `emitSettingsEventLocked()`, under `mutex_`; `setWriteBuffer`/`setFramesPerFolder` add the `recording_` refusal (CAM-31). No sensor call, no standby refusal. `setMediaTrimEnabled` (`CC:11887-11893`) moves to the same shape in commit 8 (today it is refused in standby) |
| 5 | b, c: duplicate keys in `settingsBody` during commits 3-15 | Commits 3, 5, 6 add `buffer_setting`, `clip_merge_enabled`, `storage_preroll_auto` lines to `settingsBody`; only commit 4 says `bufferSettingMembers` loses its key; commit 16 moves the rest later | `settingsBody` ends with `<< "," << bufferSettingMembers()` (`App:393`), which already emits `buffer_setting`, `storage_preroll_auto`, `clip_merge_enabled`, `frames_per_folder` (`App:255-268`). Each of commits 3, 5, 6 would print its key twice in `get_state` and every `set_*` reply | Each commit removes its key from `bufferSettingMembers` in the same commit. Then `/api/buffer` and the `buffer` event lose it too: the WebUI poll reads `storage_preroll_auto` there (`WCP:16509-16512`) and must stop in commit 6; the touch UI is fed by settings events and replies (`ACB:1411-1412` -> `applyCoreState` -> `applyBufferState`), so it is unaffected |
| 6 | b, c: the takeover runs too late and in the wrong place | One block after `camera_.start()` and the still sync (`App:8077-8089`), before the control server (`App:8092`); "the clip-merge worker start moves below this block" | The trim worker, merge worker, pre-roll thread and media watcher all start before `camera_.start()` (`App:8031-8051`). The watcher's first cycle requests the Core-start pre-roll (`App:10947-10963`), which reads the switch at once (`App:11152-11162`): on the first start after the upgrade a rig with `[media] preroll=on` misses it. The T37 block "validate the hardware file once ... Nothing is changed" adopts the file as found at `App:8148`, after the design's spot, so the takeover edit would land before the "Before Controls" pin. Camera settings are already loaded in the constructor (`CC:10510`) | Two steps. (1) Apply: before `App:8031`, with the direct setters of row 4 (they need no running session). (2) Remove: inside the T37 block after `store.adopt()`, one `store.edit(...)`, then `appliedHardwareText_ = store.currentText()` (`App:8121`) so the controls worker sees no foreign change. The merge-worker move is then not needed |
| 7 | b: `/boot` copies | Risk: "Not checked: what `HardwareConfigStore` does when it found the file under `/boot`" | Settled: the store never looks there. `HardwareConfigStore::defaultPath` = `APERTAR_HARDWARE_CONFIG` else `/home/pi/apertar-hardware.conf` (`HardwareConfigStore.cpp:118-123`). The camera's readers also try `/boot/firmware/` and `/boot/` (`CC:2946-2949`, `:2994-2997`). On a `/boot`-only camera App's `refreshBufferRequest` already disagrees with the recorder today | The takeover reads with the same candidate list (upstream keeps such per-file lists, CC-2-F2). It edits only when the file found is `store.path()`; otherwise it applies the old values at every start and logs once that the file is not Core's to edit |
| 8 | a: precedent for the old location | Takeover writes the hardware file once (owner decision 10) | Upstream never rewrites a file unprompted at start. Its one legacy location is read in place and never moved: `SettingsBridge.cpp:1943-1957@ui-upstream` (old presets dir). `wb_locked` (`CC:625`, `:682`, `:726-728@upstream`) is a key in the same file, dropped by the next whole-file save | Keep decision 10 on the owner's list, citing both precedents. Say plainly that a) makes Core write the operator's wiring file once by itself, which 1.6.0 never does, and that b) costs a revert of a later UI change at every restart |
| 9 | b: commit 10 claims a warning that does not exist | "a file with `buffer=ram` now shows an unknown-key warning, not an error" | `hwconf::validate` has no unknown-key check. `knownKey` is used only by `checkEdits` (`HardwareConfigText.hpp:496`); `[storage]` is `ValueRule::Raw` (`:66`). After commit 10 a leftover `buffer=ram` (a `/boot` file, row 7) is silently ignored | Either say "silently ignored" or keep one warning line in the existing `storage` branch (`:830`) naming the moved keys, shaped like `unknown_section` (`:806-811`). The second is the honest one for a `/boot`-only camera |
| 10 | b, d: commit 17 breaks the build | Commit 17 deletes `MediaProfile.hpp:214-234` (`configuredMediaRoot`, `mediaExtraRawBuffersForConfiguredRoot`, `mediaTuneForConfiguredRoot`) and the snapshot statics | `mediaTuneForConfiguredRoot` is still called at `CdngEncoder.cpp:91`, `CC:1467`, `CC:4364`, `CC:4718` until commit 18, which is gated on owner decision 3. It needs `configuredMediaRoot` and `cachedMediaSnapshotOrProbe` (`MediaProfile.hpp:232`) | Commit 17 removes only `mediaExtraRawBuffersForConfiguredRoot` and the `CC:7737` use. `configuredMediaRoot`, `mediaTuneForConfiguredRoot` and the snapshot statics go in commit 18. If the owner keeps the file (decision 3c), the encoder's read stays and 17 says so |
| 11 | c: commit 17 first configure | "Before the first watcher cycle the profile is empty: upstream defaults, safe" | Today the first configure probes when no snapshot is cached (`MediaProbe.hpp:285-290`). With an empty copy the first session on vfat/NTFS media runs without the `+2` raw buffers (`MediaProfile.hpp:143-145`) until the next reconfigure | Before `camera_.start()`, App probes once and calls `setMediaProfile` (the watcher's own code path). Pi: FAT32 USB stick as media, cold boot, journal shows the raw buffer count of the first configure = base + 2 |
| 12 | d: commit 6/7 across two repos | Commit 6 replaces `set_storage_preroll`; commit 7 (UI) follows; "Core and UI ship together" | Between the two commits the touch UI still sends `set_storage_preroll value=on\|off` (`ACB:627`), which Core then refuses as unknown | Commit 6 keeps the old name as an accepted alias in the same `if`. A new Core commit after 7 removes it (missing commit M1) |
| 13 | f: scripts the plan calls "not determined" | "whether any of his scripts send `set_storage_preroll value=` or `set_clip_merge`" | Settled: `apertar-kb/working/drop-frames/ssd-campaign/night2/night2.sh:11,26` and `merge-test-after-night2.sh:25,51,72` send `set_clip_merge enabled=`; `apertar-kb/working/tools/longtakes.py:1129` sends `set_media_trim`, `:1131` `set_frames_per_folder` | Put these file:lines into owner decision 7. The renames break them |
| 14 | a, f: owner decision 1, option b) is costed wrong | "b) needs a `SettingsBridge` property per switch in the touch UI (R3, about 40 lines each)" | Upstream's UI.conf switch is one line per command: `handleUiToggle("set_record_audio_enabled", "recordAudioEnabled")` (`App:9478-9491`, `:9642@upstream`), read at use (`App:2774@upstream`). HW-10: "operator preferences go to UI.conf and buttons flip them with `set_*_enabled`". The touch UI shows only the pre-roll switch (`ACB:617-630`); trim and merge have no touch control (0 hits in `ui-work`). CMD-11 keeps UI.conf values out of `get_state` and the settings event, so the touch UI would read that one key from UI.conf itself | Restate b): three `handleUiToggle` lines, three `UiSettingsSnapshot` fields, three `/api/state` `ui` lines, one `SettingsBridge` property (pre-roll), a takeover of `media_trim`. Restate a)'s cost: `CameraController` persists three values it never reads (CMD-12 owner, but no consumer). The choice stays the owner's; b) is the precedent |
| 15 | b, c: the template keeps the moved keys | Commit 9 removes the four tuning keys from the template; commits 3-6 do not mention it | The template the port writes for a new camera ships live `buffer=frames` and commented `frames_per_folder`, `clip_merge`, `[media] preroll` lines (`App:5052-5076`). Each fresh camera would be written by the template, then edited by the takeover at its first start | Each of commits 3-6 deletes its own template lines and comments. Then a fresh file has nothing to take over and no write happens |
| 16 | d, e: commit 2 carries two ideas | Constants **and** "the takeover block is born here", which logs non-default `[camera]` values and unsets the section | `[camera]` values are never applied, so removing them only buys a file write. A leftover `[camera]` already shows the `unknown_section` warning once the table entry goes (`HardwareConfigText.hpp:58`, `:806-811`), with "no reader uses it" | Commit 2 = constants, delete `CameraSection`/`loadCameraSection`/`cameraSection`, the template block, the table entry, the README text. No takeover. The block is born in commit 3 with the first switch key; tuning keys ride in the same single edit (commit 9 adds them to its list) |
| 17 | b: commit 12 emits twice | The latch's `changed` lambda emits a `buffer` event | `runBufferEvents` already emits on every flip of the same three fields (`App:11004-11019`). Emitting under the queue mutex has upstream precedent (`markDropped` under the queue mutex, `CC:3530-3537@upstream`), although the port comment says only a lock-free hook runs there (`CC:5011-5012`) | Same commit: drop the flip detection of those fields from `runBufferEvents`; rewrite the `CC:5011-5012` comment |
| 18 | e: commit 11 needs no new header | New `src/util/RecordingBuffer.hpp` with the gauge, held by the controller, passed by pointer | Upstream's other take-scoped state is a recorder member read through the session: `RecordingFailure failure_` (`CC:3901@upstream`), read via `session_->recordingError()` (`CC:8524@upstream`). `session_` is never reset (0 hits for `session_.reset` / `session_ =`), the same argument the design uses for commit 14 | The gauge atomics become `DngRecordingQueue` members; `frameBufferStatus()` reads them through `session_`. No new file, no pointer plumbing. The header is then needed only if the latch of commit 12 stays a controller member; as a queue member like `failure_` it needs none either |
| 19 | f, c: stock defaults that differ from 1.6.0 are not on the owner's list | Decision 4 names only the cDNG DONTNEED default | On a stock camera the port also runs: a `syncfs` thread every 1000 ms by default (`CC:4364-4368`), per-frame `sync_file_range` writeback on by default (`CC:4715-4720`), and on vfat/NTFS 2 writers and a 16-frame queue instead of 4 and 12 (`MediaProfile.hpp:143-145`, `CC:4320-4326`). Requirement 3 says stock behaves as 1.6.0 until the operator turns a port feature on | Decision 4 covers all four write-path defaults as one question, with the rig measurement. Media-fault-tune-F5 / CC-2-F17 stay "not covered", but the owner must see that the plan keeps these defaults |
| 20 | f: owner items the code settles | Items 2, 8, 9, 11 | 2: CAM-31 refuses stream and file changes during a take with a sentence. 8: presets start from `camera_.settings()` (`App:14231`) and `buildCurrentPresetPayload` lists explicit keys (`App:7701ff`), so new fields stay out of presets with no code. 9: R8/CAM-24, nobody set it. 11: outside the theme | Inform the owner of 2, 8, 9; move 11 to the record-gate theme. The list keeps 1, 3, 4 (widened, row 19), 5, 6, 7, 10 |
| 21 | g: commit 13 Pi check | "the journal shows `safety stop at` within about 0.1 s of the event" | The queue logs nothing when the latch fires (`CC:5013-5020`); the only journal line is App's (`App:11104`). There is no second timestamp to compare | Store a steady-clock ms in the latch when it fires and print the delay in the existing line (`... safety stop at 91 % (... MiB) after 3 ms`). Pi: `journalctl -u apertar-core -b -o short-precise | grep 'safety stop at'`; pass = delay < 200 ms |
| 22 | g: commit 23 Pi check | `chrt -p $(pidof apertar-core)` reports SCHED_OTHER | The drop-in is installed under `/etc/systemd/system/apertar-core.service.d/`; the repo change reaches the rig only by reinstalling it | Pi: reinstall the drop-in, `sudo systemctl daemon-reload`, `systemctl show apertar-core -p LimitRTPRIO -p LimitNICE` = `0` / `-5`, then the `chrt` check |
| 23 | d, e: commit 25 | Port booleans written `0/1` | The reader already takes both (`CC:869-890`). Upstream writes booleans as `<< s.member` (`iso_auto`, `CC:745-777@upstream`). The rewrite also changes fork main's `clear_hdr=` line (`core-main CC:784`) for no behaviour | Write the new keys of 3-6 as `<< s.member` from the start; drop the rewrite of the existing writers. Commit 25 goes |
| 24 | b: line drift | Line numbers `@7dc6f7a` | Examples: `configuredMediaRoot()` set at `CC:10545` (design 10543), `stopRecording` static read `CC:12444` (12442), `set_media_trim` `App:13210-13217` (13207-13216). `0977dd6` and `615b48c` are merged, so the dependencies of commits 6 and 20 are met | Re-grep every anchor before each commit |
| 25 | d: commit 3 size | `-45 / +40` | With rows 4, 5, 6, 7, 15 commit 3 also carries the takeover block (candidate list, apply step, single edit after `adopt()`), about +40 more | Split: 3a "core: the write buffer is a camera setting" (field, loader, writer, carry-over, setter, command, `planQueueBuffer`, template lines); 3b "core: old hardware-file storage keys are taken over at start" (the block, with `[storage] buffer` only). 4, 5, 6, 9 each add one line to 3b's list |

Checked and holding: the upstream precedents of the "How original Apertar does this" table open where cited (`CC:1027-1061`, `:3328-3330`, `:2483`, `:7939-7955`, `:625/682/726-728`, `:884-889`, `:8247`, `:8519-8534`, `CCH:87`, `:113`, `RecordingDropWarning.hpp:10-27`, `App:6845-6856`, `:7029-7034`, `:9094`, `:9642`, `ProresEncoder.cpp:771ff`, `CdngEncoder.cpp:1777`, `LossyDngEncoder.cpp:82`). Profile swaps carry camera-wide fields by hand (`CC:11343-11371`) and the photo-mode switch only restores geometry (`CC:12806-12823`), so carrying the new fields like `mediaTrimEnabled` is enough. The queue already holds `settings_` (`CC:4321`), so `planQueueBuffer` can read `writeBuffer` there. The touch UI tolerates partial `buffer` events (`ACB:2676-2761`, every field behind `contains`). The env names in commits 9 and 18 exist today (`CC:5534-5536`, `:1469`, `:4365`, `:4718`, `CdngEncoder.cpp:86`). `kernel_tune` is off without the file and the env (`App:11404-11410`), so commit 18 changes nothing there.

### Verdict

- **Stand (11):** 1, 9, 14, 15, 16, 18, 19, 20, 21, 22, 24.
- **Change (13):**
  - 2: constants only, no takeover (row 16).
  - 3: split into 3a / 3b; direct-store setter; remove `buffer_setting` from `bufferSettingMembers`; template lines; takeover in two steps with the `/boot` rule (rows 4-7, 15, 25).
  - 4, 5, 6: direct-store setters; each removes its key from `bufferSettingMembers` and the template; 6 keeps `set_storage_preroll` as an alias and stops the WebUI reading `storage_preroll_auto` from `/api/buffer` (rows 4, 5, 12, 15).
  - 7: lands after 6's alias; unchanged otherwise.
  - 8: `setMediaTrimEnabled` takes the direct-store shape (row 4).
  - 10: drop the false warning claim, or add the one `moved` warning line (row 9).
  - 11: gauge as queue members read through `session_`, no new header (row 18).
  - 12: remove the second emitter in `runBufferEvents`; fix the comment (row 17).
  - 13: no third constructor parameter, the event reaches App through `handleTriggerEvent`; the pending flag stays out of `wait()`'s `break` predicate; the latch keeps `used/capacity/ram` and the fire time (rows 1-3, 21).
  - 17: removes only `mediaExtraRawBuffersForConfiguredRoot` and the `CC:7737` use; App seeds the profile before `camera_.start()` (rows 10, 11).
  - 23: Pi check reinstalls the drop-in (row 22).
- **Dropped (1):** 25 (row 23).
- **Missing (1):** M1 "core: set_storage_preroll is gone; the touch UI sends set_storage_preroll_auto_enabled" after commit 7 (row 12).
- **Owner's list:** widen 4 (row 19); restate 1 (row 14), 5 (row 2), 7 (row 13), 10 (row 8); inform on 2, 8, 9; move 11 out.
