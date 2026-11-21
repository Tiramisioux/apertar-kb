# Review CC-3: CameraController.cpp new lines 4584-7264 (queue tail, copy hand-off, sync, safety stop, probe, session start)

| Item | Value |
| --- | --- |
| Diff | `/home/user/build/review/diffs/CC.part03.diff` (origin/main -> cinemate-port), read whole |
| Refs | port `@cinemate-port` `01f170c` (`/home/user/Apertar-Core`); upstream `@upstream-1.6.0` (`/home/user/wt/core-upstream`) |
| Yardstick | `raw/conv-core-camera.md` (rule ids S*, I*, N*, section 5.12/5.13); `apertar-conventions.md` does not exist yet |
| Inventory | `raw/inv-CC-3.md` |
| Checks run | `tools/clip_name_test.cpp` compiled with g++ and run: all passed (default template gives `cDNG_`, `MLV_`, `H264_`, `ProRes_`, `cDNG_3to1_`, `cDNG_5to1_` names) |

Line numbers without a ref are `@cinemate-port`, file `src/camera/CameraController.cpp` (CC). Upstream lines are `CC@upstream-1.6.0`.

## Findings

| Id | Title | Cat | Sev | Deliberate |
| --- | --- | --- | --- | --- |
| CC-3-F1 | Safety stop, flush abort and buffer gauge are process-wide globals and `std::function` registries shared by CC and App | mismatch | major | yes |
| CC-3-F2 | Camera side reads `apertar-hardware.conf [storage]` each take; operator settings and tuning in hardware conf and a tune file | mismatch | major | yes |
| CC-3-F3 | Sync thread waits on the writers' `cv_`; `enqueue`'s `notify_one` can wake it instead of a writer | bug | minor | no |
| CC-3-F4 | Detached writers outlive the queue: destructor does not wait for `liveWorkers_` | bug | minor | no |
| CC-3-F5 | Raw copy pool kept between takes (upstream frees it at stop) | removed-upstream-behaviour | minor | yes |
| CC-3-F6 | Per-frame writeback + 1 s fsync thread + syncfs at stop reverse upstream's "clip frames are not synced" | new-ground | minor | yes |
| CC-3-F7 | Preview TDN default off: stock tuning no longer loaded as-is on any sensor | removed-upstream-behaviour | major | yes |
| CC-3-F8 | Write-stall watchdog classifies a slow but alive medium as Removed | bug | minor | partly |
| CC-3-F9 | A/B and experiment env knobs left in the recorder | slop | minor | yes |
| CC-3-F10 | Comments with ticket numbers, clip ids, dates, commit shas; misplaced comment; `assert` | slop | minor | no |
| CC-3-F11 | Probe tells IMX585 by `properties::Model` substring, not `SensorFamily`; probe narrowed to table rows | mismatch | minor | yes |
| CC-3-F12 | Safety stop ends the take; record during flush discards queued frames | new-ground | minor | yes |
| CC-3-F13 | `otherSensorSubdevPresent` copies the sysfs walk of `openImx585Subdev` | duplication | nit | no |

### CC-3-F1 Globals and registries instead of the controller surface (mismatch, major)

Port:
- `CC:4182` `FrameBufferGauge &frameBufferGauge() { static FrameBufferGauge gauge; ... }`, written by the queue under its mutex, read by `CameraController::frameBufferStatus()`.
- `src/util/BufferBudget.hpp:224-300`: `safetyStopState()`, `flushAbortMutex()`, `flushAbortFunction()`, `safetyStopHook()`, `bufferSettingStorage()`; all function-local statics holding mutable state.
- Queue writes them: `CC:5016-5022` (enqueue fires `bufferbudget::safetyStopHook()` under `mutex_`), `CC:4626-4636` (`registerFlushAbort` stores `[this]` in a global).
- App writes/reads them directly: `App:7988` `bufferbudget::safetyStopHook() = [this](...)`, `App:291-295` `bufferbudget::abortSafetyStopFlush()`, `App:10119`, `App:12570`.
- Lock-order comment needed to keep it safe: `CC:4594` "before mutex_: abortSafetyFlush takes the registry mutex first, then mutex_".

Upstream:
- App reaches the camera only through `CameraController` methods (S7). `CC.hpp@upstream-1.6.0:19-21` callbacks are passed in the constructor (`EventCallback`, `PreviewCallback`); `CC.hpp:111-112` held as members.
- A background condition that must end a take is latched in the recorder and polled: `RecordingFailure.hpp:7-16`, supervisor `CC@upstream:8519-8534`, polled by App's 1 s loop `App@upstream:7031-7034` and on every command `App@upstream:9094` (N4).
- I17 allows function-local statics for process-wide one-off values (`captureSettingsPersister()`, `cachedPiSerial()`), not for per-take mutable state.

Why it matters: the queue state now lives in three places (queue members, gauge, `bufferbudget` statics). App pokes the recorder without the controller lock, behind the controller's back. The original developer cannot see from `CC.hpp` that the safety stop or flush abort exist.

Rework:
1. Move `FrameBufferGauge` into `DngRecordingQueue` members (atomics). `CameraSession::frameBufferStatus()` reads them; `CameraController::frameBufferStatus()` (already in `CC.hpp:129`) forwards.
2. Latch the safety stop like `RecordingFailure`: `std::atomic<bool> safetyStopRequested_` in the queue; `CameraController::takeSafetyStopRequest()` (or a field of the existing recording supervision) polled by App's existing supervisor loop. If 1 s is too slow, pass a `std::function<void()>` into the controller constructor beside `EventCallback`, not a global.
3. `CameraController::abortSafetyFlush()` public method forwarding to `session_->recorder_.abortSafetyFlush()`; delete `flushAbortMutex/Function`, `registerFlushAbort`, `unregisterFlushAbort`.
4. `bufferSettingStorage()` becomes a controller member returned in the state; keep only pure math (`planBuffer`, `effectiveStopPercent`, `safetyStopReached`) in `BufferBudget.hpp` (S4).

Risk: abort-during-flush runs while `stop()` holds the controller's `recording` path; the new method must not take the controller mutex (same constraint as today, now visible in the header).

### CC-3-F2 Hardware conf and tune file on the camera side (mismatch, major)

Port: `planQueueBuffer` `CC:5505` calls `loadBufferConf()` (`CC:2989-3006`), which opens `APERTAR_HARDWARE_CONFIG` / `/home/pi/apertar-hardware.conf` / `/boot/...` and parses `[storage] buffer`, `buffer_stop_percent`, ram fraction/floor/max, `frames_per_folder` (`startAtFolder` `CC:4297`). `startWritebackPerFrame` `CC:4718` reads `mediaTuneForConfiguredRoot()` (`~/apertar-media-tune.conf` + `/run/apertar-media/...override.conf`, `MediaTune.hpp:27-28`). Precedence chains env > file > default at every site (`CC:5500-5536`).

Upstream: S22 "The camera side never reads `apertar-hardware.conf`" (0 hits in `src/camera`). S20: operator camera settings live in `camera_settings.conf`, written only by Core, through a setter per command (S7, I1, S8). N11 + 5.12: recorder tuning is env-only; "A config file or config section for recorder tuning" is listed as deliberately absent. Closest precedent for a per-take option that is not a camera setting: `GyroRecordingOptions` built by App (`Types@upstream:199-201`, S19).

Why it matters: buffer mode (Frames/RAM buttons), stop percent and frames per folder are operator choices, but they are saved in the hardware file and re-read from disk inside the recorder at each take. A second, third and fourth config source for the recorder (env, `[storage]`, tune file, tune override) with three-way precedence.

Rework: `CaptureSettings::bufferMode` (enum + `toString`), `bufferStopPercent`, `framesPerFolder` persisted in `camera_settings.conf` (not per-format profile), setters `setBufferMode` / `setFramesPerFolder` gated on `recording_` with `applySettingsLocked(next, false)`; `planQueueBuffer(settings_)` takes them from `settings_`. Ram fraction/floor/max stay env-only (I9). Delete `loadBufferConf`, `bufferbudget::parseBufferConf` and the `[storage]` keys in `HardwareConfigText.hpp`. Drop `MediaTune.hpp`'s file layer (other unit owns the file): its values become env defaults per medium class in `MediaProfile`.

### CC-3-F3 Sync thread shares the writers' condition variable (bug, minor)

`syncLoop` `CC:4743-4746`: `std::unique_lock lock(mutex_); while (!cv_.wait_for(lock, interval, [this]{ return stopping_; }))`. Writers wait on the same `cv_` (`CC:5256`, `CC:5366`). `enqueue` `CC:5010` does `cv_.notify_one()`.
Failing input: all writers idle, sync thread waiting; a frame is queued; `notify_one` wakes the sync thread, whose predicate is false, and it sleeps again. The frame stays queued until the next enqueue (one frame period later), so the queue carries one extra frame whenever this happens. Confirmed in code; effect probable.
Fix: a `syncCv_` of its own (I16: one cv per worker set), notified in `stop()`/`failRecording`; or `notify_all` in enqueue.

### CC-3-F4 Detached writers outlive the queue (bug, minor)

`stop()` `CC:4492-4500` detaches writers still blocked on a dead medium. `spawnWorker` `CC:4691-4707` captures `this`; the `Exit` destructor later locks `queue->exitMutex_`. `~DngRecordingQueue` `CC:4208-4212` calls `stop()` (returns early: nothing active) and does not wait for `liveWorkers_ == 0`.
Failing input: pull the card mid-take, stop, then quit Core (or destroy the session) before the kernel fails the I/O: the detached thread returns into freed memory. Probable (needs teardown inside the I/O timeout).
Fix: destructor waits on `exitCv_` for `liveWorkers_ == 0` with a bound, then `std::quick_exit`-free path: at minimum log and leak the queue (`new`-allocated state block shared via `shared_ptr` captured by the thread).

### CC-3-F5 Raw pool kept between takes (removed-upstream-behaviour, minor)

Upstream `stop()` `CC@upstream:3486-3489`: `queue_.clear(); rawPool_.clear(); pooledRawBytes_ = 0; expectedRawBufferSize_ = 0;`. Port `stop()` tail (diff lines 16-30, `CC:4594-4608`) no longer clears; `trimRawPoolToIdle` keeps `idleRawPoolSize()` = `min(queue, max(workers+2, 4))` copies; `warmRawPool` allocates them before the take. Comment: "The raw copy pool survives the take".
Effect: about 6 x 16.6 MB = 100 MB held while idle at 16-bit 4K; on 1-2 GB Pi 4/CM4/Pi 3 boards (lower frame sizes, but also less RAM) it competes with preview and the UI. Pi-compat: probable.
Rework: keep `warmRawPool` (start-of-take allocation outside the lock is the real fix), clear the pool at stop as upstream does; or trim only when the session stays configured and MemTotal >= 4 GB. Drop `APERTAR_RAW_POOL_WARM` (F9).

### CC-3-F6 Durability path (new-ground, minor, deliberate)

Port: `startWriteback` `CC:4722-4729` `sync_file_range(SYNC_FILE_RANGE_WRITE)` after each DNG; `syncLoop` fsyncs each written file, the part folders and the clip folder every `APERTAR_MEDIA_SYNC_MS`; `syncToMedium` `syncfs` at stop.
Upstream intent: N10, `src/util/AtomicStillFile.hpp@upstream-1.6.0:31-32` "Keep this out of the continuous recording path: syncing each video frame would destroy throughput." Upstream has no `fsync` in the take path.
Deliberate: yes. Commits `4ce382e`, `7d9dd60`, `441e42a` record pull tests (C0010/C0011) and the throughput A/B (782 drops with syncfs, none with writeback alone).
Verdict: keep, simplify. The mechanism reverses a stated upstream intent; it must be documented for the original developer as a decision with the measurements. Simplify: one sync mode (writeback per frame + folder fsync tick), no `DONTNEED=sync` branch in `syncLoop`, own cv (F3).

### CC-3-F7 Preview TDN off by default (removed-upstream-behaviour, major)

Port `CameraSession::start` `CC:7306-7320`: unless `settings.previewTdn`, `loadablePath` loads `tuning::previewTuningPath(...)`, a copy of the tuning without `rpi.denoise` tdn blocks. Default off (`e625c68`: "a persisted setting preview_tdn (default off)").
Upstream: the resolved tuning file is loaded as is (`CC@upstream` `applyProcessTuningFile(tuningPath)`, diff line 1428). Derived tunings exist only for ProRes ISP log (`ProresIspProfile.hpp:7`, N13).
Why it matters: every user on every sensor and board gets a noisier monitor after the merge, to fix a 16-bit 4K Clear HDR IMX585 load problem. Commit marks the measurement "probable".
Rework: default `previewTdn = true` (upstream look); the operator or the IMX585 Clear HDR 16-bit path turns it off. The derived-file shape (cache copy, validation fallback, `tuning_file_active`) follows the ProRes precedent and stays.

### CC-3-F8 Stall watchdog classifies slow as removed (bug, minor)

`hasCapacityForFrame` `CC:4834-4845` and `stop()` `CC:4476-4484`: full queue and no frame written for `APERTAR_WRITE_STALL_MS` (5000) -> `failRecording(..., MediaFault::Removed)`. `failRecording` `CC:5424-5432` sets `mediumGone_` for Removed. Consequences of `mediumGone_`: MLV `encoder.abandon()` skips the header patch (`CC:5372-5377`), `syncToMedium` is skipped, lossy writes abandoned.
Failing input: an untrimmed NVMe that stalls 5-10 s (`d44b177` message: "the NVMe stalls for seconds") on a live drive: the take ends with "Media stopped responding", and the MLV keeps the frame count it had at open.
Fix: a distinct `MediaFault::Stalled` that ends the take (N4) but does not set `mediumGone_`; leave `Removed` to the mount watcher.

### CC-3-F9 Experiment knobs (slop, minor)

In slice: `APERTAR_RAW_POOL_WARM` (`CC:4892-4899`, "restores the old pool rule for the A/B"), `APERTAR_DNG_WRITEBACK` (`CC:4715-4719`), `APERTAR_DNG_DONTNEED` three modes (`CC:4763-4764`), `APERTAR_WRITE_STALL_MS`, `APERTAR_DEAD_MEDIUM_STOP_MS` (`CC:4469`), `APERTAR_CDNG_BUFFER_STOP_PERCENT` (duplicates a conf key), `APERTAR_CDNG_QUEUE_RAM_FRACTION/_FLOOR_MB/_MAX_FRACTION`.
Upstream: I9 bench knobs read where used with default and bounds: the form conforms. But each knob here exists for one A/B (commit text says so) and doubles a file key.
Rework: remove `APERTAR_RAW_POOL_WARM`, `APERTAR_DNG_DONTNEED=sync`, `APERTAR_CDNG_BUFFER_STOP_PERCENT`; keep `APERTAR_DNG_WRITEBACK`, `APERTAR_WRITE_STALL_MS`, `APERTAR_DEAD_MEDIUM_STOP_MS` and the ram fraction knobs env-only (F2).

### CC-3-F10 Comment slop (slop, minor)

I19: comments are rare, say why, no ticket numbers, dates or authors. In slice:
- `CC:4674` "for the ramp log (T31)", `CC:4678` "A ramping take (T31)".
- `CC:4714` "(C0001, 2026-10-26)", `CC:4734` "(C0010, 2026-10-26)".
- `CC:4888` "(kb dng-chain, R3/R7)".
- `CC:5546` "(the rule since db17860)".
- `CC:4892-4894` "for the A/B".
- Diff line 496 "CineMate Log tables" (foreign product name for the Log feature).
- Member `writtenFiles_` (diff line 1035): `// written since the last sync tick   // steady_clock, last frame written (or the take's start)`; the second comment belongs to `lastWriteProgressNs_`.
- `assert(!queue_.empty() || queuedBytes_ == 0)` (`CC:4596`): upstream Core has 0 `assert(` calls.
- Many 3-6 line comments narrating measurements (`CC:4710-4714`, `CC:4730-4734`).
Rework: strip ids, dates, shas; keep one line of constraint each; move measurements to the KB / commit messages; delete the assert.

### CC-3-F11 Probe sensor test and table narrowing (mismatch, minor)

Port `probeSensorModes` `CC:7152-7158`: `camera->properties().get(properties::Model)`, lowercased, `find("imx585")`. Same file uses `detectSensorFamily` for subdev names (`CC:6996`).
Upstream S11: sensors are told apart by `SensorFamily` from `detectSensorFamily(camera->id())` (`CC@upstream:5375`).
Also removed: for IMX585 only table rows are configured; sizes libcamera advertises that the table lacks, 10-bit Clear HDR and 16-bit SDR are not probed (N7: libcamera is the last word).
Rework: `const bool tableProbe = detectSensorFamily(camera->id()) == SensorFamily::Imx585;`. Optional: probe advertised sizes too and log those missing from the table, so a driver change is visible.

### CC-3-F12 Safety stop and flush discard (new-ground, minor)

Upstream N3: a dropped frame is reported and does not stop the take. Port: in ram mode, at 90 % the take ends (`CC:5016-5022`); record during the flush discards queued frames of the finished take (`abortSafetyFlush` `CC:4611-4624`).
Deliberate: yes (`d44b177`, `c5db8b2` "owner decision 2026-11-01"). Default frames mode keeps upstream behaviour.
Verdict: keep (opt-in, operator-visible, logged). Shape: rework per F1. Document that the abort loses written-but-queued frames of the previous clip.

### CC-3-F13 Subdev walk copied (duplication, nit)

`otherSensorSubdevPresent` `CC:6985-7002` repeats the `/sys/class/video4linux/v4l-subdev*/name` loop of `openImx585Subdev` `CC:6955-6972`. One `subdevSensorFamilies()` helper returning the families found serves both and `imx585SubdevPresent`.

## Abstraction verdicts (inventory section 5)

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `bufferbudget` namespace (`BufferBudget.hpp`) | simplify | Pure plan math fits S4. Global state, registries and the `[storage]` parser go (F1, F2) |
| Global singletons (`safetyStopState`, `flushAbortFunction`, `safetyStopHook`, `frameBufferGauge`, `bufferSettingStorage`) | rework-to-upstream-pattern | Per-take mutable state crossing App/CC: queue members + controller methods + latch polled by supervisor (F1) |
| `std::function` hook queue -> App | rework-to-upstream-pattern | Constructor-passed callback or RecordingFailure-style latch (F1) |
| Sync thread `syncLoop` | keep | Deliberate, measured; own cv (F3), document N10 reversal (F6) |
| Copy workers `copyLoop` | keep | Same shape as I16 (mutex, cv, deque, stopping flag); keeps N2 (never blocks, bounded held requests, drop logged with I8 rate) |
| `spawnWorker` + `liveWorkers_` + `exitCv_` | simplify | Needed for the bounded dead-medium stop; destructor must wait (F4); RAII `Exit` struct could be a plain decrement at the end of each loop |
| `MediaFault` | keep | Small header, errno -> class; feeds `RecordingFailure` first-wins latch (N4). Add `Stalled` (F8) |
| `MediaProfile` / `MediaTune` | rework-to-upstream-pattern | Tune file is a recorder config file (N11, 5.12). Medium-class defaults in code, env override only |
| `FramePath` | keep | Header-only pure logic named after the concept (S4); host test |
| `ClipName` | keep | Header-only (S4); default reproduces upstream names (test run passes); replaces S17 switch by an operator feature |
| `CdngLogTake` / `applyCdngLogFrame` | keep | Free helper in CC (S3), applied on the copy only (N13) |
| `PendingCopy` | keep | Plain struct inside the queue; libcamera type stays in CC (S1) |
| `tuning::previewTuningPath` | keep | Follows the derived-tuning precedent (`ProresIspProfile.hpp`), nested `tuning` namespace (I22); default is the problem (F7) |
| `apertar::imx585` tables (`Imx585Modes.hpp`) | keep | Pure header (S4); detection should use `SensorFamily` (F11) |
| Host tests in `tools/` | keep | S24: upstream has none; dev-only, not built by CMake; say so in the handoff |

## Conforms

| What | Where |
| --- | --- |
| Copy hand-off keeps N2: `enqueueCopy` never blocks, bounded held requests, drop logged first and every 30th (I8) and marked on `RecordingDropWarning` (N3) | `CC:5067-5085` |
| `failRecording` keeps the first-wins latch and adds the fault class with `compare_exchange_strong` | `CC:5424-5444` |
| Lossy DNG background failures now fail the take (closes rough edge 5.13 #9, N4) | `CC:5280-5290` |
| Log lines keep `ApertarCore <area>: key=value` form (I6) | `CC:4806-4808`, `CC:5992`, `CC:7349-7353` |
| H.264 dead-medium flag is one atomic and one log line; `.mp4.writing` is left, not renamed (N10) | `CC:5939-5944`, `CC:6465-6487` |
| Clear HDR cleared at start when another sensor is on the bus, one log line, saved setting untouched (N8 exception pattern) | `CC:7277-7291` |
| `binningFromProperties` is a free helper in CC reading mainline properties only (S3, N12) | `CC:7090-7113` |
| Default clip template gives the upstream names | `tools/clip_name_test.cpp` run 2026-11-17 |
| New worker sets follow I16 (mutex + cv + deque + stopping flag, atomics with explicit orders) | `CC:5040-5055` members |
| Protocol: no socket or HTTP change inside this slice | inventory section 3 |

## Skeptic

Checked at `@cinemate-port` `01f170c` (`/home/user/Apertar-Core`) and `@upstream-1.6.0` (`/home/user/wt/core-upstream`), each finding read on both sides, commits read with `git show -s`, `fork-log.md:138`.

| Id | Verdict | Why |
| --- | --- | --- |
| CC-3-F1 | corrected | Code confirmed (`CC:4182`, `BufferBudget.hpp:224-300`, `App:7988`, `App:291-295`, lock comment `CC:4594`). Upstream path fixed: `src/util/RecordingFailure.hpp`, not `src/camera/`. Upstream does keep function-local statics with mutable state (`Mpu6050RecordingSession.cpp:1228-1229@upstream-1.6.0` `liveConfiguredKey`), but never a callback registry or a `[this]` pointer in a global; the finding holds for the registry/hook part. |
| CC-3-F2 | corrected | `loadBufferConf()` per take confirmed (`CC:2988-3006`, `CC:4297`, `CC:5505`); 0 hits for `apertar-hardware.conf` in `src/camera@upstream-1.6.0`. Half wrong on the tune file: `startWritebackPerFrame` (`CC:4718`) reads it once per process (`static const`); per take it is read at `CC:4364` (`sync_ms`), plus `CC:1467` (raw buffers) and `CdngEncoder.cpp:91`. Rework note: `MediaProfile.hpp` is itself port code (`26da30e`), not upstream. |
| CC-3-F7 | corrected, stands major | Confirmed (`CC:7306-7320`, `CC:7326`, `CC:7401`). Worse than stated: the stripped tuning is also what the ISP uses for recorded H.264 (`H264PreviewRecorder`) and is the base for the derived ProRes ISP tuning (`makeProresIspTuning(activePath, ...)` `CC:7412`). `e625c68` says "the recorded DNGs are raw and do not change"; H.264 and ProRes takes do change. |
| CC-3-F5 | stands | `trimRawPoolToIdle` (`CC:4502`, `CC:4935-4944`) runs before `workerCount_ = 0`, so keep = min(queue, max(workers+2,4)); upstream clears at stop (`CC:3486-3489@upstream-1.6.0`). `4abbef0` confirms intent. |
| CC-3-F3 | stands | Writers wait on `cv_` with `stopping_ || !queue_.empty()` (`CC:5256`, `CC:5366`); `syncLoop` waits on the same `cv_` (`CC:4746`); `enqueue` uses `notify_one` (`CC:5010`). A wake can land on the sync thread. MLV (one writer) is the worst case. |
| CC-3-F4 | stands | Detach path `CC:4489-4500`; a second `stop()` returns early (`CC:4443-4446`: `active_` false, `workers_` cleared, `stopping_` reset); `~DngRecordingQueue` (`CC:4208-4212`) does not wait on `liveWorkers_`; `spawnWorker`'s `Exit` dereferences `this` (`CC:4691-4707`). The writer loop also takes `mutex_` after its `write()` returns. Use-after-free is probable (needs a dead medium plus session teardown). |
| CC-3-F8 | stands | Both stall sites (`CC:4834-4842` queue full, `CC:4476-4483` user stop) pass `MediaFault::Removed`; `failRecording` sets `mediumGone_` (`CC:5428-5429`); MLV `abandon()` (`CC:5375-5376`). `a3ac8da` designs for a pulled card; `d44b177` documents multi-second NVMe stalls on an untrimmed drive. Deliberate stays unknown. |
| CC-3-F6 | corrected | Confirmed; upstream CC has no `fsync`/`syncfs`. Wording: the port does not sync each frame on the writer path; it starts writeback per file and fsyncs the written files in a 1 s sweep off the writer thread. Clip ids in the evidence corrected to the ones the commits name (C0105, C0001, C0004, C0005). |
| CC-3-F11 | corrected | Confirmed `CC:7152-7158`. Upstream also reads `properties::Model`, but only to pick the default tuning (`CC:5323@upstream-1.6.0`); sensor identity is `detectSensorFamily` (`CC:5375@upstream-1.6.0`). The table-row probe itself is a deliberate design (`caa0153`) and each row still goes through `validate()`, so N7 is not broken; the finding narrows to the identity check plus an optional log line. |
| CC-3-F12 | stands | `CC:5011-5022`, `CC:4611-4624`; `fork-log.md:138` records "owner decision 2026-11-01" for `c5db8b2`. Default frames mode never sets `stopPercent_` (`effectiveStopPercent`), so upstream behaviour is the default. |
| CC-3-F9 | stands | All knobs present (`CC:4896`, `CC:4718`, `CC:4763`, `CC:4468`, `CC:5502-5536`); `4abbef0` names `APERTAR_RAW_POOL_WARM` "for the A/B". |
| CC-3-F10 | corrected | Comments confirmed at `CC:4674`, `4678`, `4714`, `4734`, `4888`, `5546`. The misplaced member comment is at `CC:5591` (`writtenFiles_` carries `lastWriteProgressNs_`'s comment), added to where. Upstream has 0 runtime `assert(` in Core (2 `static_assert` only). |
| CC-3-F13 | stands | `CC:6955-6972` vs `CC:6985-7002`; `openImx585Subdev` comes from fork main (`CC:5340@main`), the second walk is port. |

## Final findings

### CC-3-F1 Safety stop, flush abort, buffer gauge and buffer setting are process-wide globals and std::function registries shared by CC and App
- Category: mismatch. Severity: major. Effort: M. Deliberate: yes (`d44b177`, `c5db8b2` describe the safety stop and flush abort; the global shape is not discussed).
- Where: `src/camera/CameraController.cpp:4182`, `:4594`, `:4611-4636`, `:5011-5022`; `src/util/BufferBudget.hpp:224-300`; `src/ApertarCoreApp.cpp:291-295`, `:7988` (all `@cinemate-port`).
- Port way: `frameBufferGauge()`, `bufferbudget::safetyStopState()`, `flushAbortFunction()` (holds the queue's `[this]`), `safetyStopHook()` (assigned by App), `bufferSettingStorage()`: function-local statics with per-take mutable state. App assigns the hook and calls `abortSafetyStopFlush()` without the controller. A lock-order comment keeps it safe ("before mutex_: abortSafetyFlush takes the registry mutex first").
- Apertar way: App reaches the camera only through `CameraController` methods (S7). Callbacks go into the constructor and live as members (`CameraController.hpp:19-21`, `:111-112@upstream-1.6.0`). A background condition that ends a take is latched in the recorder and polled by App's 1 s supervisor (`src/util/RecordingFailure.hpp`, `CameraController.cpp:8519-8534`, `ApertarCoreApp.cpp:7031-7034@upstream-1.6.0`; N4). Upstream function-local statics hold caches or one-off values (`captureSettingsPersister()`, `cachedPiSerial()`, `Mpu6050RecordingSession.cpp:1228`), never a callback registry or an object pointer.
- Why it matters: queue state lives in three places; App changes the recorder outside the controller lock; `CameraController.hpp` does not show that a safety stop or flush abort exist. The original developer reads it as hidden coupling.
- Rework: move the gauge atomics into `DngRecordingQueue` members, read through `CameraSession` and the existing `CameraController::frameBufferStatus()`. Latch `safetyStopRequested_` in the queue and expose `CameraController::takeSafetyStopRequest()`, polled by App's supervisor loop; if 1 s is too slow, pass a `std::function<void()>` into the `CameraController` constructor beside `EventCallback`. Add public `CameraController::abortSafetyFlush()` that forwards to the recorder without the controller mutex (document that in the header). Delete `flushAbortMutex`/`flushAbortFunction`/`registerFlushAbort`/`unregisterFlushAbort`/`safetyStopHook`. `bufferSettingStorage` becomes a controller member. `BufferBudget.hpp` keeps only the pure planning math (S4).
- Rework risk: the abort runs while `stop()` drains; the new method must not take `CameraController::mutex_`.

### CC-3-F2 Recorder reads apertar-hardware.conf [storage] per take and a media tune file
- Category: mismatch. Severity: major. Effort: M. Deliberate: yes (`2edc6d0` "the camera's tuning per storage medium belongs in one readable file next to the hardware conf"; the upstream rule was not weighed).
- Where: `src/camera/CameraController.cpp:2988-3006`, `:4297`, `:4364`, `:4718`, `:1467`, `:5498-5536`; `src/util/MediaTune.hpp:27-28`; `src/cdng/CdngEncoder.cpp:91` (`@cinemate-port`).
- Port way: `loadBufferConf()` opens `APERTAR_HARDWARE_CONFIG`, `/home/pi/` or `/boot/` `apertar-hardware.conf` at each take and parses `[storage]` `buffer`, `buffer_stop_percent`, ram fraction/floor/max and `frames_per_folder`. `mediaTuneForConfiguredRoot()` reads `~/apertar-media-tune.conf` plus a `/run` override: per take for `sync_ms` (`:4364`), once per process for `writeback` (`:4718`, `static const`), and for raw buffer count and DONTNEED elsewhere. Every site has env > file > default.
- Apertar way: S22: the camera side never reads `apertar-hardware.conf` (0 hits in `src/camera@upstream-1.6.0`). S20/S7/I1/S8: operator camera settings persist in `camera_settings.conf` through one setter per command, gated on recording. N11 and 5.12: recorder tuning is env-only (`APERTAR_CDNG_QUEUE_FRAMES`, `CameraController.cpp:3329-3330@upstream-1.6.0`); a config file for recorder tuning is deliberately absent.
- Why it matters: Frames/RAM, stop percent and frames per folder are operator choices from the UI but are stored in the hardware file and re-read from disk inside the recorder. The recorder has four config sources.
- Rework: add `CaptureSettings::bufferMode` (enum with `toString`), `bufferStopPercent`, `framesPerFolder`, persisted in `camera_settings.conf`; setters `setBufferMode`/`setFramesPerFolder`, refused while recording, ending in `applySettingsLocked(next,false)`. `planQueueBuffer` and `startAtFolder` read `settings_`. Ram fraction/floor/max stay env-only. Delete `loadBufferConf`, `bufferbudget::parseBufferConf` and the `[storage]` keys in `HardwareConfigText.hpp`. Replace the MediaTune file layer with per-class defaults in the (port-new) `MediaProfile.hpp` plus env overrides.

### CC-3-F7 Preview temporal denoise off by default: the stock tuning is no longer loaded as is, also for recorded H.264 and ProRes
- Category: removed-upstream-behaviour. Severity: major. Effort: S. Deliberate: yes (`e625c68` "a persisted setting preview_tdn (default off)"; its measurement is marked probable).
- Where: `src/camera/CameraController.cpp:7306-7320`, `:7326`, `:7401`, `:7412` (`@cinemate-port`).
- Port way: unless `settings.previewTdn` is set (default off), `loadablePath()` loads `tuning::previewTuningPath()`, a cached copy of the resolved tuning without the `rpi.denoise` tdn blocks, on every sensor and board. The ProRes ISP tuning is derived from that stripped copy (`makeProresIspTuning(activePath, ...)`), and H.264 is encoded from the same ISP output.
- Apertar way: `applyProcessTuningFile(tuningPath)` loads the resolved file unchanged (`CameraController.cpp` `start()`, `:5350@upstream-1.6.0` derives ProRes from `tuningPath`). Derived tunings exist only for the ProRes ISP log (`ProresIspProfile.hpp:7`, N13).
- Why it matters: after the merge every user gets a noisier monitor image and noisier H.264/ProRes recordings, to fix a load problem measured on IMX585 Clear HDR 16-bit 4K. The commit claims only DNGs are unaffected, which is true, but does not mention H.264/ProRes.
- Rework: default `previewTdn=true` (the upstream look). Turn it off by operator choice, or automatically only for the IMX585 Clear HDR 16-bit path and only when the format is raw (cDNG/MLV). Keep the derived-file mechanism.

### CC-3-F5 Raw copy pool kept between takes; upstream freed it at stop
- Category: removed-upstream-behaviour. Severity: minor. Effort: S. Deliberate: yes (`4abbef0` and the in-code comment).
- Where: `src/camera/CameraController.cpp:4502`, `:4596-4606`, `:4892-4899`, `:4935-4944`, `:5547-5550` (`@cinemate-port`).
- Port way: `stop()` no longer clears `rawPool_`; `trimRawPoolToIdle` keeps min(queue, max(workers+2,4)) full-frame copies (6 x 16.6 MB at 16-bit 4K with 4 writers); `warmRawPool` tops up before each take.
- Apertar way: `stop(): queue_.clear(); rawPool_.clear(); pooledRawBytes_ = 0; expectedRawBufferSize_ = 0;` (`CameraController.cpp:3486-3489@upstream-1.6.0`).
- Why it matters: about 100 MB held while idle at 16-bit 4K; on 1-2 GB Pi 4/CM4/Pi 3 this competes with preview and the UI (pi-compat, probable).
- Rework: keep `warmRawPool` (allocates outside the lock at take start); restore the upstream clear at stop, or keep the idle pool only when `MemTotal >= 4 GB`. Remove `APERTAR_RAW_POOL_WARM`.

### CC-3-F3 Sync thread waits on the writers' cv_; enqueue's notify_one can wake it instead of a writer
- Category: bug. Severity: minor. Effort: S. Deliberate: no.
- Where: `src/camera/CameraController.cpp:4743-4746`, `:5010`, writer waits `:5256`, `:5366` (`@cinemate-port`).
- Port way: `syncLoop` runs `cv_.wait_for(lock, interval, [this]{return stopping_;})` on the `cv_` the writers wait on; `enqueue` calls `cv_.notify_one()`.
- Apertar way: I16, one cv per worker set, each waiter's predicate matches what is notified (`CameraController.cpp:3922-3927@upstream-1.6.0`).
- Why it matters: all writers idle and a frame is queued; `notify_one` wakes the sync thread, which sleeps again; the frame waits for the next enqueue. Worst with MLV (one writer). The queue runs one frame deeper than needed.
- Rework: give `syncLoop` its own `syncCv_`, notified in `stop()` and `failRecording`; or `notify_all` in `enqueue`.

### CC-3-F4 Detached writers outlive the queue: the destructor does not wait for liveWorkers_
- Category: bug. Severity: minor. Effort: S. Deliberate: no.
- Where: `src/camera/CameraController.cpp:4208-4212`, `:4441-4446`, `:4489-4500`, `:4691-4707` (`@cinemate-port`).
- Port way: a dead-medium stop detaches blocked writers. A second `stop()` (from `~DngRecordingQueue`) returns early. `spawnWorker`'s `Exit` destructor and the writer loop later dereference `this` (`exitMutex_`, `mutex_`).
- Apertar way: every writer is joined in `stop()` (`CameraController.cpp:3404-3409@upstream-1.6.0`).
- Why it matters: pull the card mid-take, stop, then quit Core or reconfigure before the kernel fails the I/O; the thread returns into freed memory (probable).
- Rework: in the destructor wait on `exitCv_` for `liveWorkers_==0` with a bound and log if it expires; or move the state the threads touch into a `shared_ptr` block captured by each thread.

### CC-3-F8 Write-stall watchdog classes a slow but live medium as Removed
- Category: bug. Severity: minor. Effort: S. Deliberate: unknown (`a3ac8da` chose Removed after a pull test; the slow-drive case is not discussed, though `d44b177` documents multi-second NVMe stalls).
- Where: `src/camera/CameraController.cpp:4834-4842`, `:4476-4483`, `:5424-5432`, `:5372-5377` (`@cinemate-port`).
- Port way: a full queue with no write for 5 s (`APERTAR_WRITE_STALL_MS`), or the same stall during a user stop, calls `failRecording(..., MediaFault::Removed)`. That sets `mediumGone_`: MLV header patch skipped (`abandon()`), `syncToMedium` skipped, writers may be detached.
- Apertar way: N4, a write failure ends the take with its first error. No "medium gone" state upstream.
- Why it matters: an untrimmed NVMe that is alive but stalls 5-10 s ends the take as removed; the MLV keeps the frame count it had at open.
- Rework: add `MediaFault::Stalled` that ends the take but does not set `mediumGone_`; `Removed` stays for the mount watcher.

### CC-3-F6 Per-file writeback, a 1 s fsync sweep and syncfs at stop reverse upstream's "clip frames are not synced"
- Category: new-ground. Severity: minor. Effort: S. Deliberate: yes (`441e42a`, `4ce382e`, `7d9dd60`: C0105 pull lost a stopped clip; C0001 12 gaps with syncfs; C0005 782 drops with syncfs plus writeback; C0004 none with writeback alone).
- Where: `src/camera/CameraController.cpp:4715-4729`, `:4743-4790`, `:4795-4809` (`@cinemate-port`).
- Port way: `sync_file_range(WRITE)` after each DNG; a sync thread fsyncs each written file, part folders and the clip folder every `APERTAR_MEDIA_SYNC_MS`, with an optional DONTNEED; `syncfs` at a normal stop.
- Apertar way: no precedent in the take path; upstream CC has no `fsync`/`syncfs`. N10: `AtomicStillFile.hpp:31-32@upstream-1.6.0` "Keep this out of the continuous recording path: syncing each video frame would destroy throughput."
- Why it matters: reverses a stated upstream intent. Keep it (the measurements support it; it is off the writer path), but the original developer must be told why.
- Rework: keep and document as a decision with the pull-test and A/B numbers. Simplify to one mode (writeback per frame plus the folder fsync tick); drop the DONTNEED=sync branch; give the thread its own cv (F3).

### CC-3-F11 Probe identifies IMX585 by a properties::Model substring instead of SensorFamily
- Category: mismatch. Severity: minor. Effort: S. Deliberate: yes (`caa0153` "imx585 modes from tables, not whitelists").
- Where: `src/camera/CameraController.cpp:7152-7158` (`@cinemate-port`).
- Port way: `modelName = lowercase(properties::Model)`; `tableProbe = modelName.find("imx585")`. For IMX585 only `Imx585Modes` table rows are configured (each still validated); advertised sizes not in the table are never seen.
- Apertar way: S11, `sensorFamily_ = detectSensorFamily(camera_->id())` (`CameraController.cpp:5375@upstream-1.6.0`), `switch (family)` in free functions. Upstream reads `properties::Model` only to pick the default tuning (`:5323@upstream-1.6.0`).
- Why it matters: a second way to tell sensors apart in the same file (`otherSensorSubdevPresent` uses `detectSensorFamily`). A driver mode missing from the table leaves no trace.
- Rework: `tableProbe = detectSensorFamily(camera->id()) == SensorFamily::Imx585`. Optionally log advertised sizes that are not in the table. The table-row probe itself stays.

### CC-3-F12 Safety stop ends the take; record during the flush discards queued frames
- Category: new-ground. Severity: minor. Effort: S. Deliberate: yes (`d44b177`; `c5db8b2`, owner decision 2026-11-01 per `fork-log.md:138`).
- Where: `src/camera/CameraController.cpp:5011-5022`, `:4611-4624` (`@cinemate-port`).
- Port way: in ram mode at 90 % of the budget the take ends cleanly; record during the drain discards the remaining queued frames of the previous clip.
- Apertar way: no precedent. N3: a dropped frame is reported and does not stop the take.
- Why it matters: intent change, but opt-in: frames mode (default) keeps upstream behaviour. The discard loses frames already captured.
- Rework: keep the feature; re-shape per F1; document the discard in the handoff.

### CC-3-F9 A/B and experiment env knobs left in the recorder
- Category: slop. Severity: minor. Effort: S. Deliberate: yes (`4abbef0`, `0ed07ea`).
- Where: `src/camera/CameraController.cpp:4892-4899`, `:4715-4719`, `:4763-4764`, `:4468`, `:5500-5536` (`@cinemate-port`).
- Port way: `APERTAR_RAW_POOL_WARM` ("restores the old pool rule for the A/B"), `APERTAR_DNG_WRITEBACK`, `APERTAR_DNG_DONTNEED` (three modes), `APERTAR_WRITE_STALL_MS`, `APERTAR_DEAD_MEDIUM_STOP_MS`, `APERTAR_CDNG_BUFFER`, `APERTAR_CDNG_BUFFER_STOP_PERCENT` (shadows a conf key), `APERTAR_CDNG_QUEUE_RAM_FRACTION/_FLOOR_MB/_MAX_FRACTION`.
- Apertar way: I9, one env knob per tuning value, read where used, with default and bounds (`APERTAR_CDNG_QUEUE_FRAMES`, `CameraController.cpp:3329-3330@upstream-1.6.0`). Form conforms; count and A/B purpose do not.
- Why it matters: knobs kept only to A/B one change make the recorder harder to read; some shadow file keys.
- Rework: remove `APERTAR_RAW_POOL_WARM`, the DONTNEED=sync mode and `APERTAR_CDNG_BUFFER_STOP_PERCENT`; keep the rest as env-only knobs (after F2).

### CC-3-F10 Comments with ticket numbers, clip ids, dates and a commit sha; misplaced member comment; assert
- Category: slop. Severity: minor. Effort: S. Deliberate: no.
- Where: `src/camera/CameraController.cpp:4674`, `:4678`, `:4714`, `:4734`, `:4888`, `:5546`, `:5591`, `:4596` (`@cinemate-port`).
- Port way: "(T31)", "(C0001, 2026-10-26)", "(C0010, 2026-10-26)", "(kb dng-chain, R3/R7)", "(the rule since db17860)", "for the A/B", "CineMate Log". `writtenFiles_` (`:5591`) also carries `lastWriteProgressNs_`'s comment. `assert(!queue_.empty() || queuedBytes_ == 0)`. Many 3-6 line comments narrate measurements.
- Apertar way: I19, rare one-to-three-line comments stating a constraint; no ticket numbers, dates or authors. Upstream Core has 0 runtime `assert(` (2 `static_assert`).
- Why it matters: ids and dates mean nothing to the original developer; comments read as history.
- Rework: strip ids, dates and shas; one constraint line per comment; move measurements to the KB and commit messages; fix the misplaced comment; delete the assert.

### CC-3-F13 otherSensorSubdevPresent copies openImx585Subdev's sysfs walk
- Category: duplication. Severity: nit. Effort: S. Deliberate: no.
- Where: `src/camera/CameraController.cpp:6955-6972`, `:6985-7002` (`@cinemate-port`).
- Port way: two loops over `/sys/class/video4linux/v4l-subdev*/name`; `imx585SubdevPresent` opens and closes the device just to test it.
- Apertar way: no precedent (`openImx585Subdev` exists only from fork main, `CameraController.cpp:5340@main`).
- Why it matters: small duplication in sensor detection.
- Rework: one helper returning the `SensorFamily` values found on subdevs, used by both checks.
