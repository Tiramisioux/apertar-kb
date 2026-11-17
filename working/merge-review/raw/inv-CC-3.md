# Inventory CC-3: CameraController.cpp new lines 4584-7264 (DngRecordingQueue tail, H264 recorder, probe, session start)

Diff: `/home/user/build/review/diffs/CC.part03.diff` (origin/main -> cinemate-port). Refs: `@cinemate-port` = `01f170c`, upstream = `@upstream-1.6.0`.
Line numbers are `@cinemate-port` unless stated. Labels: confirmed = read in code. No judging in this stage.

Base note: `origin/main` already holds Clear HDR (`631721d`..`f60e301`) and the sensor probe. Lines blamed to those are not port work.
Of 2681 scope lines, 1684 are still upstream-1.6.0, about 440 are fork main, about 560 are port.

## 1. Regions of the diff and who wrote them

| Hunk (new lines) | Region | Port commits (blame) |
| --- | --- | --- |
| 4584-5220 | `DngRecordingQueue`: stop() tail, abortSafetyFlush, stats, setters, sync thread, writeback, stall watch, raw pool, part folders, enqueue, copy hand-off (PendingCopy, copyLoop), clip folder allocation | `d44b177` (drop-frames), `fc7eb16`, `d9f00d4`, `4abbef0`, `438a342`, `a3ac8da`, `4ce382e`, `441e42a`, `5b68f1f`, `7d9dd60`, `0ed07ea`, `2edc6d0`, `d7dd337`, `c5db8b2`, `faa2958`, `014a2bf`, `26da30e` |
| 5239-5314 | `workerLoop` (DNG): Log into lossy encoder, queuedBytes_, writeback, noteWrittenFile, media fault classification | `d44b177`, `441e42a`, `5b68f1f`, `438a342`, `db17860` (comment only) |
| 5361-5648 | MLV `workerLoop`, `failRecording`, `recycleRawBuffer`, ram helpers, `planQueueBuffer`, pool sizing, member list | `e8bb1b7`, `438a342`, `0b1632f`, `d44b177`, `4abbef0`, `a3ac8da`, `fc7eb16`, `d7dd337` |
| 5939-5944 | `H264PreviewRecorder::setMediumDead` | `438a342` |
| 6465-6487, 6712-6733 | H.264 finalize skips rename on dead medium; member `mediumDead_` | `438a342` |
| 6964-7000 | `imx585SubdevPresent`, `otherSensorSubdevPresent` | `c48e693` (IMX283) |
| 7076-7125 | `binningFromProperties` | `4ab1057` |
| 7142-7236 | `probeSensorModes`: IMX585 table probe, binning per mode, log line | `caa0153`, `4ab1057` (rest is fork main `f60e301`) |
| 7264-7335 | `CameraSession::start`: clear Clear HDR on non-585 bus, Preview TDN tuning copy | `c48e693`, `e625c68` (Preview TDN) |

## 2. Features (operator-visible)

| Feature | What the operator gets | Commits | Tested (fork-log / commit text) |
| --- | --- | --- | --- |
| Survive a pulled/unmounted drive | A take ends with a media fault (`removed`, `Other`...), message in UI; no hang at stop; MLV file left as-is; H.264 `.mp4.writing` left | `438a342`, `e8bb1b7`, `0b1632f`, `a3ac8da` | Pi built 22:27-22:51 on 2026-10-26; pull test C0011 (258/281 frames readable) |
| Write-stall watchdog | Queue full and no frame written for 5 s ends the take as media removed. `APERTAR_WRITE_STALL_MS` (1000-600000) | `a3ac8da` | built on Pi, not separately tested |
| Once-a-second sync thread | fsync of each finished DNG, then folder fsync, so a pulled card keeps all but about 1 s. Full `syncfs` at normal stop | `4ce382e`, `7d9dd60`, `5b68f1f` | C0007 3 min clean; C0010/C0011 pull tests |
| Per-frame writeback | `sync_file_range(WRITE)` after each DNG; `APERTAR_DNG_WRITEBACK=0` off | `441e42a` | C0004 clean alone, C0005 782 drops with syncfs (led to fsync change) |
| Page-cache drop mode | `APERTAR_DNG_DONTNEED` writer/sync/off; `posix_fadvise(DONTNEED)` on sync thread; `dropped_copy_slot` in stats line | `0ed07ea` | Pi built 2026-11-04 |
| Media profile and tuning file | Workers, queue, raw buffers chosen per medium class (NVMe, USB UAS, SD...) and per filesystem; `~/apertar-media-tune.conf` plus `/run/apertar-media` override | `26da30e`, `2edc6d0` | `26da30e` built, not tested; `2edc6d0` built on Pi, Core not restarted yet at the log row |
| RAM write buffer ("ram" mode) | Queue limited by bytes (share of MemAvailable) instead of frames; plan line in log; `buffer` setting | `d44b177` | Pi, per log (campaign branch) |
| Safety stop | At 90 % of the buffer (ram default; off in frames mode) the take ends cleanly from Core's own thread, every queued frame still written; `buffer_safety_stop` flag | `d44b177` | Pi per log; threshold keys in `[storage]` |
| Record during safety-stop flush | Pressing record while the flush drains discards queued frames of the old clip and starts at once; `buffer_flush_discarded`, `discarded_on_stop` | `c5db8b2` | owner decision 2026-11-01 |
| Buffer gauge | `frameBufferGauge()` used/capacity (frames or bytes); feeds state, `GET /api/buffer`, `buffer` event, red bar | `d44b177` | Pi per log |
| Raw copy hand-off | Completion thread hands the request over; copy worker syncs dma-buf, copies, releases the request, queues the frame. `APERTAR_RAW_COPY_WORKERS` 1-2; drops counted as `drop[copy-slot]` | `fc7eb16` (API), `db17860`, `d9f00d4` | `fc7eb16` "not wired in yet"; wiring is outside this slice (CC:8731, 9505) |
| Raw pool warm and kept | Pool survives takes, warmed before writers; trimmed to idle size at stop; `APERTAR_RAW_POOL_WARM=0` restores old rule; allocation outside mutex | `4abbef0` | Pi 2026-11-01 per log |
| Audio follows queued frames | `setFrameQueued` callback after the queue accepts a frame | `d9f00d4` | WAV order-proof per log |
| Log in files (cDNG, lossless, Lossy DNG) | `applyCdngLogFrame` table lookup on the copy; Log tags (linearization table, black levels) | `d44b177` (+ `631721d`, main, for `compressClearHdrFrame`) | Pi per log |
| Split take into part folders | `[storage] frames_per_folder` (env `APERTAR_CDNG_FRAMES_PER_FOLDER`); `part_NNN/`; part folders fsynced; not for MLV or pre-roll | `d7dd337` | built on Pi; `tools/frame_path_test.cpp` |
| Compose clip names | Folder name from a template (default `{format}_{date}_{clip}`), `{sensor}` token | `014a2bf` | host test `tools/clip_name_test.cpp` |
| Speed ramp | `nextFrameIndex(ts, countOnly)`: count numbering for ramping takes | `faa2958` | tested 2026-10-28 C0030-C0032 |
| Lossy DNG failure surfaced | Background lossy write failures end the take one frame late | `438a342` / `d44b177` | not separately recorded |
| Storage pre-roll flag | `setPrerollTake`: pre-roll take ignores safety stop and part folders | `d44b177` | Pi per log |
| Sensor binning | Per-mode `binning`, `binning_source` (table / driver / inferred) in probe log line and mode list | `4ab1057`, `caa0153` | `4ab1057` built and running 21:39, `list_sensor_modes` verified |
| IMX585 modes from tables | Probe configures one mode per table row, 10/12-bit SDR, 12/16-bit Clear HDR | `caa0153` | no fork-log row found (campaign commit) |
| Clear HDR cleared off-585 | Start clears `clearHdr` when another sensor family is positively on the bus; message in log | `c48e693` | desk only (host tests, Pi `-fsyntax-only`) |
| Preview TDN off by default | libcamera loads a copy of the tuning file without `rpi.denoise` tdn blocks unless `previewTdn` | `e625c68` | not read |

## 3. Interfaces added or changed (in this slice)

| Kind | Name | Where | Note |
| --- | --- | --- | --- |
| Env var | `APERTAR_WRITE_STALL_MS` | CC:4859-4861 (`writeStallLimitMs`) | default 5000, range 1000-600000 |
| Env var | `APERTAR_DNG_WRITEBACK` | `startWritebackPerFrame` | default from tune file, else on; read once per process |
| Env var | `APERTAR_DNG_DONTNEED` | `dngPageCacheDrop()` use in `syncLoop` | defined elsewhere |
| Env var | `APERTAR_RAW_POOL_WARM` | `rawPoolWarmEnabled` | default on |
| Env var | `APERTAR_CDNG_BUFFER` (`frames`/`ram`) | `planQueueBuffer` | wins over file; bad value logs and falls to frames |
| Env var | `APERTAR_CDNG_BUFFER_STOP_PERCENT` | `planQueueBuffer` | wins over `[storage] buffer_stop_percent` |
| Env var | `APERTAR_CDNG_QUEUE_RAM_FRACTION`, `_FLOOR_MB`, `_MAX_FRACTION` | `planQueueBuffer` | defaults 0.6, 512, 0.5 |
| Env var | `APERTAR_CDNG_FRAMES_PER_FOLDER` | read in `startAtFolder` (outside slice), used in `enqueue` | |
| Env var | `APERTAR_RAW_COPY_WORKERS` | `startAtFolder` (outside slice) | 1-2 |
| Env var | `APERTAR_MEDIA_SYNC_MS` | `startAtFolder` (outside slice) | 0 turns the sync thread off |
| Config key | `[storage] buffer`, `buffer_stop_percent`, queue-ram fraction/floor/max keys, `frames_per_folder` | `apertar-hardware.conf` via `loadBufferConf()` (CC:2989) | HardwareConfigText.hpp |
| Config file | `/home/pi/apertar-media-tune.conf`, `/run/apertar-media/media-tune.override.conf` | `src/util/MediaTune.hpp:27-28` | `writeback`, `sync_ms`, `dontneed`, ... |
| Config file | `~/.../` `apertar-hardware.conf` `[storage]` | as above | |
| State field | `buffer_safety_stop`, `buffer_flush_discarded`, buffer stop percent | `ApertarCoreApp.cpp:248-259` (fed by `safetyStopState()`) | |
| State field | `sensor_binning`, `sensor_binning_source`, `sensor_crop`; mode list `binning`, `binning_source` | `4ab1057` | |
| State field | `media_alive`, media fault | `ApertarCoreApp.cpp:9556` | fed by `fault()` |
| Event | `buffer` | App | fed by `frameBufferGauge()` |
| Log line | `ApertarCore recording stop: ... discarded_on_failure= skipped_after_failure= dropped_copy_slot= queue_bytes_peak= queue_budget=` | CC:4517-4531 (outside slice) | |
| Log lines | `ApertarCore buffer: ...`, `drop[queue-full] ... bytes=used/budget MiB`, `drop[copy-slot]`, `recording stop: synced to the medium in N ms`, `sensor mode: ... binning=N(source)`, `Clear HDR cleared: no imx585 sensor on the bus`, `preview tdn: ...` | slice | |
| Socket/HTTP | none added inside the slice; consumers in `ApertarCoreApp.cpp`: `set_buffer_mode` (12829), `set_frames_per_folder` / `set_clip_merge` (12857), `set_clip_name_template` (13241), `GET /api/buffer` | | other units |
| Files on disk | `part_NNN/` folders, `.parts` marker (written outside slice), clip folder name from template | | |
| Syscalls | `sync_file_range`, `fsync`, `syncfs`, `posix_fadvise(DONTNEED)`, `DMA_BUF_IOCTL_SYNC`, `setpriority` | | Linux only |
| UI element | none in this slice. Red buffer bar and media state live in UI/WebUI | | |

## 4. Original (upstream-1.6.0) code modified

| Region | Where @cinemate-port | Kind | What changed |
| --- | --- | --- | --- |
| `DngRecordingQueue::stop()` tail | 4584-4612 | behaviour-changed | No longer clears `rawPool_`, `pooledRawBytes_`, `expectedRawBufferSize_`; resets gauge and safety flag; `assert` added; unregister flush-abort before `mutex_` |
| `Stats` | 4195-4205 | extended-in-place | New counters: skippedAfterFailure, discardedOnFailure, ramMode, peakQueueBytes, queueBudgetBytes |
| `nextFrameIndex` | 4670-4680 | extended-in-place | `countOnly` flag |
| `hasCapacityForFrame` | 4787-4825 | extended-in-place | ram mode check, skipped-after-failure count, stall watchdog that fails the take |
| `acquireRawBuffer` | 4846-4870 | rewritten | Allocation moved outside `mutex_` on a pool miss |
| `enqueue` | 4980-5025 | extended-in-place | part folder, queuedBytes_, gauge, safety stop trigger, framepath |
| `allocateClipFolder(settings)` | 5200-5210 | rewritten | 40 lines of name building replaced by `nextClipFolderName` (ClipName.hpp); signature gains `sensor` |
| DNG `workerLoop` | 5239-5314 | extended-in-place | Log in lossy encoder, writeback, written-file list, fault classification, progress mark |
| MLV `workerLoop` | 5361-5410 | extended-in-place | abandon on dead medium, errno propagation |
| `failRecording` | 5420-5445 | rewritten | Signature gains `MediaFault`; sets flags, counts discarded, resets gauge |
| `recycleRawBuffer` | 5448-5470 | extended-in-place | Retain cap guard (4096), ram budget check |
| `preferredRawPoolSize` | 5560-5580 | moved | Old rule renamed `idleRawPoolSize`; new `preferredRawPoolSize` returns `max` in ram mode while active |
| `H264PreviewRecorder::finalizeStop` | 6465-6487 | behaviour-changed | Skips rename/copy when `mediumDead_` |
| `probeSensorModes` | 7142-7236 | rewritten (partly) | Table-driven loop for IMX585; `ScalerCropMaximum` read replaced by `binningFromProperties` |
| `CameraSession::start` | 7274-7345 | extended-in-place | Clear HDR cleared for foreign sensor; Preview TDN tuning path via `loadablePath` |

## 5. New abstractions

| Name | Purpose | Files | Upstream equivalent | Used by |
| --- | --- | --- | --- | --- |
| `bufferbudget` namespace (header-only) | ram plan, stop percent, safety-stop atomics, flush-abort registry, setting snapshot, `[storage]` conf parser | `src/util/BufferBudget.hpp` (382 lines) | none (upstream queue is frames-only, `APERTAR_CDNG_QUEUE_FRAMES`, CC upstream:3330) | CC, App |
| Global singletons via function-local statics | `safetyStopState()`, `flushAbortFunction()`, `safetyStopHook()`, `frameBufferGauge()`, `bufferSettingStorage()` | BufferBudget.hpp, CC:4182 | none found for globals in upstream CC; state is held in `CameraController`/`ApertarCoreApp` members | CC, App |
| `std::function` hook from queue to App | `safetyStopHook` (queue under mutex -> App sets atomic + cv) | BufferBudget.hpp:262, App:7988 | none; upstream callbacks are `setErrorCallback` / `exposureEvent_` style | CC, App |
| Sync thread (`syncLoop`) | fsync files and folder each second | CC:4743 | none (upstream has no fsync call) | queue |
| Copy worker threads (`copyLoop`) | Take frame off libcamera completion thread | CC:5088 | upstream copies in the completion path (CC upstream request handler) | session |
| `spawnWorker` + `liveWorkers_` + `exitCv_` | Count threads that can be left behind after a dead-medium stop | CC:4691 | upstream `workers_` joined in `stop()` | queue |
| `MediaFault` (header) | Fault class from errno / exception | `src/util/MediaFault.hpp` | none | queue, App |
| `MediaProfile` / `MediaTune` | Medium class + tuning per medium | `src/util/MediaProfile.hpp`, `MediaTune.hpp` | none | queue, App |
| `FramePath` (header) | part folder names and paths | `src/cdng/FramePath.hpp` | none | queue, playback |
| `ClipName` (header) | clip name template parser | `src/util/ClipName.hpp` | none (inline prefix code, removed) | CC |
| `CdngLogTake` / `applyCdngLogFrame` | Per-take Log tables | CC:1662-1700 | none | copy worker, lossy encoder |
| `PendingCopy` struct | Hand-off unit | CC:5032 | none | queue |
| `tuning::previewTuningPath` | Strip tdn blocks from a tuning copy | `src/camera/TuningTdnStrip.hpp` | upstream has `tuning::` namespace functions | session |
| `apertar::imx585::offered/classFor/transportFor` | Mode table | `src/camera/Imx585Modes.hpp` | upstream whitelists in CC (see `imx585ModeForResolution`) | probe, session |
| Host tests | `tools/buffer_budget_test.cpp`, `frame_path_test.cpp`, `clip_name_test.cpp`, `storage_buffer_conf_test.cpp`, `tuning_tdn_strip_test.cpp`, `imx585_modes_test.cpp` | `tools/` | upstream Core has none | dev only |

## 6. Removed, narrowed or hidden compared to upstream or main

| What | Where | Effect |
| --- | --- | --- |
| Raw pool clear at take stop/start | stop() 4584+, startAtFolder | Idle pool of raw copies (about workers+2, at least 4, each a full frame, 16.6 MB at 16-bit 4K) stays allocated between takes. RAM held while idle |
| Hand-written clip-folder prefix switch (`cDNG_`, `MLV_`, `H264_`, `cDNG_5to1_`, `cDNG_3to1_`, `ProRes_`) | `allocateClipFolder` | Replaced by template; default must reproduce the same names (claimed, not tested in this stage) |
| `std::string` error path from `failRecording(e.what())` | worker loops | Message now built by `mediaFaultMessage` |
| Probe's per-size loop over `formats.sizes()` for IMX585 | `probeSensorModes` | IMX585 modes now only those in the table; sizes libcamera offers but the table lacks are not probed. 10-bit under Clear HDR and 16-bit SDR skipped |
| `ScalerCropMaximum` crop string in probe | `probeSensorModes` | Now `binning.crop`, same string when present |
| Clear HDR setting kept on non-585 sensor | `start()` | Now cleared in memory at start (saved setting not rewritten, said in a comment) |
| Preview TDN | `start()` | libcamera now loads a stripped copy by default; stock tuning no longer used as loaded |
| Frame drop in the camera while a copy slot is full | `enqueueCopy` | New drop reason `drop[copy-slot]` |

## 7. Board assumptions

| Assumption | Where | Confirmed |
| --- | --- | --- |
| Linux only: `sync_file_range`, `syncfs`, `O_DIRECTORY`, `DMA_BUF_IOCTL_SYNC`, `/sys/class/video4linux`, `/proc/meminfo` | slice | confirmed |
| `/home/pi/apertar-media-tune.conf` and `/run/apertar-media/` | `MediaTune.hpp:27-28` | confirmed |
| Four cores: worker counts `min(4, hardwareThreads)`; one copy worker default | startAtFolder, comments | confirmed (upstream has the same four-core logic) |
| Frame size 16.6 MB (16-bit 4K IMX585) in comments and pool sizing | slice | confirmed |
| RAM size: `MemAvailable` and `MemTotal` drive ram budget, floor 512 MB, max 50 % of MemTotal | `planQueueBuffer` | confirmed; 4/8/16 GB Pi 5 all go through the same plan |
| NVMe / CFexpress / HAT slot bit (`PiNvme`, CFE HAT) | `MediaProfile.hpp`, `CfeHat.hpp` | confirmed in files read, behaviour not read here |
| IMX585 specific: subdev name match "imx585", `wide_dynamic_range`, mode tables | slice | confirmed; other families recognised via `detectSensorFamily` |
| Pi 3/4 H.264 paths untouched in this slice (hardware encoder check in upstream still there) | | n/a |
| No gpiochip, I2C bus, RP1, PCIe or fan references inside this slice | grep | confirmed |

## 8. Open points for later stages (not judged here)

| Point | Command that settles it |
| --- | --- |
| Whether the default template reproduces all old folder prefixes incl. `cDNG_5to1_` | `tools/clip_name_test.cpp` compile and run |
| Whether `acquireRawBuffer` non-locked allocation leaves `expectedRawBufferSize_` coherent | read CC:4846-4870 with `warmRawPool` |
| Whether `copyLoop` path is the only path after wiring (CC:9505) | read the completion handler |
| Fork-log row for `caa0153`, `e625c68`, `c48e693` status | none found by grep; `git show -s` has the text |
