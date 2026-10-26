# y2-yank-core — Media yank, Apertar-Core side at f60e301: what exists, what is missing

Reader: y2 (Core side). Repos read: `apertar-core @ f60e301` (extracted with `git show f60e301:<path>`;
the worktree HEAD is 6853891 on `clearhdr-fixes`, three commits later — all line numbers below are
f60e301), `cinemate @ d6cc93e`, `cinepi-raw @ 63a08d5`, `apertar-kb @ c99ff77` working tree.
Status words: CONFIRMED = line opened and read; PROBABLE = inferred, reason given; UNKNOWN = not
derivable here. The Apertar-UI repo (touch UI, `apertar-cfe-automounter`) is **not** on this machine;
anything about it comes from the KB and is marked PROBABLE. The "y1 brief" is not in
`working/port-raw/` (only `p1-phaselock-cinemate.md`, `p2-phaselock-core.md` exist), so the Cinemate
side of question 5 is sketched from Cinemate source I opened, not from y1.

---

## 1. What Core does today when the drive disappears mid-take

### 1.1 Mount bookkeeping (App layer)

- `isMountedPath()` re-reads `/proc/mounts` on every call and compares the normalised mount point
  (`apertar-core/src/ApertarCoreApp.cpp:2023-2038@f60e301`); `mountedDeviceForPath()` does the same and
  returns the device column (`:2040-2055`). There is no cached flag, no statvfs, no udev/inotify
  listener anywhere in the App (grep `inotify|netlink|libudev|udev_monitor` in
  `src/ApertarCoreApp.cpp` at f60e301: no hits; the only `udevadm` uses are `udevadm info`/`settle` in
  the eject helpers `:3374`, `:3385`, `:3569`). CONFIRMED.
- `std::filesystem::space()` is only evaluated when `isMountedPath()` is true, on
  `nearestExistingPath(mediaRoot)` (`:7792-7800`; `nearestExistingPath` walks up to the first existing
  parent, `:320-326`). On error the free/total bytes become 0 (`:7799-7800`). CONFIRMED.
- Consequence (PROBABLE, kernel behaviour not read here): a yanked USB/NVMe mount normally stays
  listed in `/proc/mounts` until something unmounts it, so `media_mounted` stays `true` with a dead
  filesystem behind it. Cinemate treats exactly this case with a statvfs watchdog that issues
  `umount -l` on EIO (`cinemate/services/storage-automount/storage-automount.py:836-856@d6cc93e`), which
  is evidence the mount does not vanish by itself. Core has no equivalent → `/proc/mounts` presence is
  the only "alive" signal Core has today.

### 1.2 The raw writers (cDNG lossless/uncompressed, MLV) — `DngRecordingQueue`

- Class at `apertar-core/src/camera/CameraController.cpp:3358@f60e301`; `Stats` has `enqueued`,
  `written`, `droppedQueueFull`, `discardedOnStop`, `writeFailures`, queue depths (`:3361-3370`).
- Start: `startAtFolder()` only does `create_directories(folderPath_)` inside a try (`:3420-3430`) —
  **no mount check, no free-space check**. Worker count: MLV 1; lossless `min(8, threads+1)`
  (`APERTAR_CDNG_WORKERS`); lossy `min(4, threads)`; otherwise `max(2, min(4, threads))`; queue depth
  12 by default, 24 for compressed DNG on >= 4 threads, env `APERTAR_CDNG_QUEUE_FRAMES` 4..64
  (`:3433-3460`, member default 12 at `:4029`). CONFIRMED.
- Per-frame write, DNG: `encoder.writeDngFile(job.path, ...)` in `dngWorkerLoop()` (`:3806`, call
  `:3850-3853`). The encoder throws `std::system_error(errno, ...)` on open failure
  ("Failed to open DNG for writing", `apertar-core/src/cdng/CdngEncoder.cpp:1758-1759@f60e301`) and on
  write/close failure ("Failed to write DNG", `:1800-1801`; errno captured at `:1778`, close() error
  folded in at `:1780-1783`); the half-written file is `unlink`ed when the write failed (`:1786-1787`).
  So the message carries `strerror`, e.g. "Failed to write DNG: <path>: Input/output error", but the
  queue catches `std::exception` (`:3856`), so the errno *number* is not inspected anywhere. CONFIRMED.
- Per-frame write, MLV: `mlvWorkerLoop()` (`:3914`); `MlvEncoder::writeFrame` returns false with the
  exception text (`apertar-core/src/mlv/MlvEncoder.cpp:999-1046@f60e301`; low-level `writeAll` turns a
  zero-length write into `EIO`, `:62-78`); the worker throws `runtime_error` with that text (`:3936-3943`
  of CameraController.cpp). On close, `patchFrameCount()` (seek+write of the frame count into the
  header, `MlvEncoder.cpp:1281-1292`) is wrapped in try/catch and only logs "MLV finalize warning"
  (`:1050-1062`) — on a dead drive the `.MLV` keeps the frame count it had at open. CONFIRMED.
- **Failure handling, both loops**: first exception → `++writeFailures_`, `failRecording(e.what())`,
  log "ApertarCore DNG write failed for <path>: ..." / "ApertarCore MLV write failed for ..."
  (`:3856-3861`, `:3947-3952`). `failRecording()` (`:3958-3968`) latches the message in a
  `RecordingFailure` (first message wins, empty → "Recording write failed.",
  `apertar-core/src/util/RecordingFailure.hpp:8-25@f60e301`), sets `active_ = false`,
  `stopping_ = true`, **clears the queue** and wakes all workers, which then exit (`:3831-3836`, `:3924-3929`). So the
  take effectively stops writing after the *first* failed frame; the other queued frames are thrown
  away without being counted (they are neither `written`, `write_failures` nor `discarded_on_stop` —
  the latter is never incremented, KB `lessons/upstream-issues.md:48` #40). CONFIRMED.
- After `failRecording`: the completion thread's `recordRawFrame()` returns at once because
  `!recorder_.active()` (`:7189-7191`), and `hasCapacityForFrame()` also returns false silently when
  `stopping_ || !active()` (`:3637-3642`) — no counter, no drop warning. Frames keep being requeued to
  libcamera (`:6986-7004`), so the camera itself is unaffected. Audio and gyro recorders keep running
  until the supervisor acts (below). CONFIRMED.
- Lossy DNG (`RecordingFormat::LossyDng`) is different: `LossyDngEncoder::writeDngFile` hands the
  encoded buffer to a singleton background disk writer when `asyncWrite_` is on
  (`apertar-core/src/lossydng/LossyDngEncoder.cpp:508-511@f60e301`), and that writer only **logs**
  "ApertarCore LossyDng write failed for <path>: <strerror>" (`:230-232`) — nothing reaches
  `failRecording`. Async is the default unless `APERTAR_LOSSYDNG_ASYNCWRITE=0`
  (`:325-328`); only the synchronous fallback throws (`:512-515`). So **a yanked drive does not stop a
  lossy-DNG take**: workers keep encoding, the writer keeps failing, and the take runs until the
  operator presses stop. `DngRecordingQueue::stop()` calls `LossyDngEncoder::drainWrites()`
  (`CameraController.cpp:3520-3521`), which waits for the writer queue. CONFIRMED.
- Stats summary line at stop (`:3522-3532`): "ApertarCore recording stats: enqueued= written=
  dropped_queue_full= discarded_on_stop= write_failures= peak_queue=N/M"; after a yank it reads
  `write_failures=1` for cDNG/MLV (first failure latches and clears), `written` = frames on disk before
  the pull. A slow stop (> 0.20 s) logs "ApertarCore recorder stop time" (`:3585-3593`). CONFIRMED.
- Files left behind (CONFIRMED from the write paths; what the dead medium actually keeps is PROBABLE):
  cDNG — the clip folder `cDNG_yy-mm-dd_C####` (`:3775-3786`) with every DNG written before the
  pull, the failing DNG unlinked if the FS still answered; MLV — one `<clip>.MLV` with a stale header
  frame count; lossy DNG — folder plus whatever the async writer managed.

### 1.3 H.264 (`H264PreviewRecorder`, `:4039`)

- Start creates the clip folder (`:4111-4116`), writes to `<clip>.mp4.writing` and renames to
  `<clip>.mp4` only at finalize (`:4121`, `:4863-4879`); queue depth default 6 (`:5119`).
- Copy failure → `writeFailures_++`, `failure_.set("Could not copy the H.264 recording frame.")`,
  `active_=false`, copy loop exits (`:4991-4996`). Encode/write failure (libav or pipe `writeAll`,
  `:4781-4792`) → `writeFailures_++`, `failure_.set("H.264 encoding or media writing failed.")`,
  `active_=false`, `stopping_=true`, both queues cancelled and frame buffers released back to
  libcamera, loop exits (`:5042-5063`). `enqueueFrame` then counts "skip[stopping]" instead of drops
  (`:4370-4379`). Finalize: if the temp file exists and is > 0 bytes it is renamed, else copied; a
  failure sets "Could not finalize the H.264 clip" (`:4863-4879`); child encoder exit code / signal set
  the failure too (`:4882-4890`); stats line "ApertarCore H.264 recording stats: queued= written=
  dropped_queue_full= skipped_stopping= write_failures= peak_queue= max_copy_ms= ..." (`:4903-4915`).
  Finalization runs on a detached `finalizer_` thread (`:4812-4841`); while it runs
  `hasPendingPhotoCaptures()` is true (`:5733-5740`) so `record_start`/`capture_photo` are refused
  with "Wait for the current capture to finish writing to media." (`ApertarCoreApp.cpp:9111-9113`).
  CONFIRMED.

### 1.4 ProRes (`ProresRecorder`, `apertar-core/src/prores/ProresRecorder.cpp@f60e301`)

- Encode failure in `run()`: `++failures_`, `failure_.set(why)`, `accepting_=false`, queue cancelled
  (frames released), log "ApertarCore ProRes encode failure", loop breaks (`:110-137`); then
  `finish_()` is still attempted and its failure latched too (`:139-144`). `active()` is `accepting_`
  (`ProresRecorder.hpp:23-24`). Repair of the `.mov` + `_recovery.json` is never invoked (KB
  `architecture/core.md:429`, `lessons/upstream-issues.md:46` #39). CONFIRMED (repair claim: KB).

### 1.5 Audio / gyro

- Audio raw capture writes through an `std::ofstream`; a failed write sets
  `failure_.set("Audio capture write failed.")` and leaves the loop
  (`apertar-core/src/audio/AudioRecordingSession.cpp:472-473@f60e301`). `recordingError()` reports the
  audio error *first*, before the video recorder's (`CameraController.cpp:6223-6230`). Gyro start
  failures are non-fatal (`:5894-5899`); its runtime failures were not read (UNKNOWN).

### 1.6 Session → controller → App → UI

- `CameraSession::recordingError()` = audio error, else the active format's recorder error
  (`:6223-6230`). `CameraController::checkRecordingFailure()` (`:8990-9003`, declared
  `CameraController.hpp:80`) is the **supervisor**: if a failure is latched and not yet reported it
  calls `session_->stopRecording()`, sets `recording_=false`, `state_=Ready`, `lastError_`,
  `recordingFailureMessage_`, and emits the `recording` event. It is driven from two places only: the
  App's `wait()` loop every **1 s** under `commandMutex_` (`ApertarCoreApp.cpp:7032-7046`) and the
  head of every `handleCommand()` (`:9110`). So detection latency is "first failed write + up to 1 s".
  CONFIRMED.
- Stop ordering in `CameraSession::stopRecording()` (`:5990-6013`): `recordingStopInProgress_=true`,
  `emitMediaWriteState()`, close the frame gate (`recordingFramesEnabled_=false`, `:5997`), log
  "ApertarCore capture stats: dropped_gap_estimate= requeue_failures=" (`:5998-6003`), then
  gyro → H.264 → `recorder_` (DNG/MLV) → ProRes → audio (`:6004-6008`), flag cleared (`:6012`). Every
  one of those stops touches the medium again (MLV header patch, H.264 rename/copy, lossy drain, WAV
  finalize that reopens `rawPath_`, `AudioRecordingSession.cpp:567-573`). Nothing distinguishes
  "medium gone" from "ordinary stop". CONFIRMED.
- Event: `emitRecordingEventLocked()` sends
  `{"event":"recording","active":false,"recording_has_dropped_frames":..,"error":"<message>"}`
  (`:9265-9275`). The App's `publishEvent()` broadcasts it unless a command is collecting events
  (`ApertarCoreApp.cpp:10890-10918`; `recording` is **not** in the always-broadcast list `:10896-10907`),
  and `handleTriggerEvent()` turns the tally/recording indicator off on `"active":false`
  (`:10921-10937`). The App also drops its elapsed-time tracking (`syncRecordingTracking(false)`,
  `:7044`, `:8326-8336`). CONFIRMED. (PROBABLE: when the supervisor fires from inside
  `handleCommand` while `collectingCommandEvents_` is set, the event goes into that command's reply
  instead of the broadcast — KB `lessons/upstream-issues.md:43` #36 describes the collection race.)
- State: `recording_error` and `recording_has_dropped_frames` appear in `/api/state` (`:7852-7854`)
  and `get_state` (`:9261`); the controller keeps `recordingFailureMessage_` until the next
  `startRecording` clears it (`:8730-8731`). WebUI polls `/api/state` every 1000 ms
  (`apertar-core/src/web/WebControlPage.cpp:11643@f60e301`, plus 80/140 ms after a command, `:9144`)
  and toasts "Recording stopped: <recording_error>" when the string changes (`:9363-9365`). The HDMI UI
  consumes the `recording` event through `ApertarControlBridge` (KB `llm/core-map.md:563`; repo not
  local → PROBABLE).

### 1.7 Deliberate eject (udisks / NVMe path)

`ejectMediaAtPath()` (`ApertarCoreApp.cpp:3719-3770`): `mountedDeviceForPath` (error "No media is
currently mounted." if none); `flushMediaPath` = `sync -f <mount>` (fallback `sync`) and
`sudo -n blockdev --flushbufs <dev>` (`:3355-3364`); `udisksctl unmount -b <dev>
--no-user-interaction`; for non-NVMe also `udisksctl power-off -b <parent drive>`; fallback plain
`umount <mount>`; for `/dev/nvme*`: `detachNvmeController()` = `udevadm info -q path` → PCI address →
`sudo -n sh -c 'echo 1 > /sys/bus/pci/devices/<addr>/remove'` + `udevadm settle` (`:3366-3387`), then
`startNvmeReinsertWatcherAtPath()` (`:3389-3611`) launches an **embedded Python helper in the
background** (`python3 -c ... &`, `:3603-3604`): smbus on bus 10 / 0x34 (overridable from
`[cfexpress_hat]`, `:3400-3404`, `:3458-3462`), bit 0 of the status byte = card present
(`read_insert_state`, `:3487-3497`), waits up to 600 × 0.1 s = 60 s for "present", then 60 s for
"absent", exits silently on either timeout (`:3582-3594`; KB #17), then unbind/bind `brcm-pcie`
`1000110000.pcie`, `/sys/bus/pci/rescan`, waits up to 2 + 3 s for an `nvmeXnYpZ` partition
(`:3558-3569`), and mounts the highest partition as ntfs3 / ext4 / exfat with `sudo -n`
(`:3539-3556`). Error texts mention polkit ("Add a UDisks polkit rule for this user") and sudo
(`:3757-3767`). Core itself runs unprivileged and reaches root only through `sudo -n` one-liners and the
two `/usr/local/libexec/apertar-standby-*` helpers (`:1553`, `:1558`, `:9168`). CONFIRMED.

---

## 2. Record-start and hardware-eject gates that exist

| Gate | Where | What | Status |
| --- | --- | --- | --- |
| `record_start` socket/Web command | `ApertarCoreApp.cpp:10690-10781` | No `isMountedPath` check at all; `camera_.startRecording()` at `:10776`. The only mount gate on this path is the **sound-only** branch → `startSoundRecording()` → "Sound Recorder needs mounted media." (`:8367-8371`) | CONFIRMED |
| `CameraController::startRecording` | `CameraController.cpp:8690-8738` | Ready-state, unsupported settings, still-mode, pending photo writes; comment says start failures are "usually media/audio setup problems" (`:8719-8721`). No mount/space check | CONFIRMED |
| `CameraSession::startRecording` | `:5858-5882` | `reserveClipFolder` + `create_directories` — with nothing mounted the clip lands on the SD card under `/media/RAW` (also KB `architecture/core.md:419`) | CONFIRMED |
| `handleCommand` preamble | `:9108-9126` | `checkRecordingFailure` (`:9110`); `record_start`/`capture_photo`/`timelapse_start` refused while `mediaWritesPending()` (`:9111-9113`); `format_media`/`eject_media`/`mount_media`/`run_media_speed_test` refused while recording, sound-recording, timelapse, pending writes or speed test ("Stop recording, still captures and media tests before changing media.", `:9114-9122`); `record_start` refused during a speed test (`:9124-9126`) | CONFIRMED |
| Hardware `eject` action | `:8907-8913` | Ignored (stderr "Hardware input eject ignored while recording or timelapse is active.") when recording, sound recording or timelapse; else dispatches `eject_media` | CONFIRMED |
| Hardware `record`/`record_toggle` | `:8870-8885` | Dispatch `record_start`/`record_stop` through `handleCommand` — no media check of their own | CONFIRMED |
| `mount_media` | `:3666-3675` | Refused while something is mounted ("Eject the currently mounted media before mounting another drive."); device must be in `scanMountableMediaDrives` | CONFIRMED |
| Speed test | `:8986-9003` | Needs mount and >= 96 MB free; test size ladder 64/128/256/512/1024 MiB (`:9005-9014`); fio `--direct=1 --bs=1M --iodepth=32`, dd fallback (`:9030-9050`) | CONFIRMED |
| WebUI record button | `WebControlPage.cpp:9836-9838` | Disabled only for pending writes / in-flight commands — **not** for missing media; `toggleRecord` toasts "No media mounted." client-side (`:10742-10744`, `:10756-10758`, `:10768-10771`) | CONFIRMED |
| Touch UI | KB `llm/flows.md:63` | `RecordButton.onClicked` → `showNoMediaWarning` when no media | PROBABLE (repo not local) |

---

## 3. State fields and events the UIs already consume for media

`/api/state` (`buildWebStateJson`, `ApertarCoreApp.cpp:7722`; `GET /api/state` at `:7165-7170`):

- Top level: `recording`, `recording_error`, `recording_has_dropped_frames` (`:7852-7854`);
  `media_mounted` (`:7914`).
- `system{}`: `media_free_bytes`, `media_total_bytes`, `media_used_percent` (`:7934-7936`),
  `media_label` = mount path or "Mount /media/RAW to manage media" (`:7937`), `media_drives[]` from
  `scanMountableMediaDrives` (`lsblk -P -b ...`, cached 3 s, `:2275-2300`; emitted `:7938`),
  `record_time_left_minutes`, `record_stills_left`, `time_left_percent`, `time_left_label`
  (`:7939-7942`), `write_speed_running`, `write_speed_result_text`, `write_speed_detail_text`,
  `write_speed_error` (`:7947-7964`).
- `capture.storage` = media type label: "CFExpress Type B" / "NVMe M.2 SSD" / "External USB" from the
  volume label (`CFE-RAW`, `SSD-RAW`/`NVME-RAW`, `USB-RAW`, `RAW`) or the device prefix (`/dev/sd`,
  `/dev/nvme`), "No Media Mounted" when unmounted (`:1992-2020`, `:7732-7737`, `:7973`).
- `/api/media` (`buildMediaLibraryJson`, `:7685-7696`): `mounted`, `media_root`, `items[]`; the
  listing is skipped entirely when not mounted.
- `get_state` socket reply carries `recording_error` (`:9261`); `mount_media` replies
  `media_mounted:true`, `eject_media` replies `media_ejected:true` (`:10656-10673`).

Events (`publishEvent`, `:10890`): `recording` {active, recording_has_dropped_frames, error}
(`CameraController.cpp:9265-9275`; sound-only variants `ApertarCoreApp.cpp:8410`, `:8422`),
`recording_health` {recording_has_dropped_frames} from the clip-scoped `RecordingDropWarning` latch
(`CameraController.cpp:7916-7923`, `src/util/RecordingDropWarning.hpp:10-28`), `media_write_state`
{media_writes_pending, media_write_revision} (`:7890-7902`), `photo_write_error`, `prepare_recording`
(`ApertarCoreApp.cpp:10759`, `:10772`), `hardware_action`. **There is no media event**: no
`media_mounted` / `media_state` / mount-changed event is emitted; UIs learn media state only by polling
(`WebControlPage.cpp:11643`). No `recording_stats` or `drop_warning` event exists (grep): drops reach
the UI as the single `recording_health` latch; the numeric stats exist only in stderr. CONFIRMED.

WebUI consumption (`WebControlPage.cpp`): `hasMedia = !!snapshot.media_mounted` drives the status
pill/dot "no-media" classes (`:9830-9834`), the record button's `recording` class (`:9840`), format /
eject / speed-test buttons (`:9887-9894`), favourites text "Media mounted"/"No media mounted"
(`:6433-6435`), and after a successful `eject_media` the client sets `media_mounted=false` and
`capture.storage="No Media Mounted"` optimistically (`:9128-9132`). Touch UI: `MediaStatusBridge`
properties `mediaMounted`, `freeBytes`, `totalBytes`, `mediaTypeLabel`, `mountableDrives` (KB
`llm/ui-map.md:407`, PROBABLE).

---

## 4. The KB's T18 plan items vs f60e301

T18 row: `apertar-kb/llm/tutoring.md:94` ("Core (`mediaRootAlive`, record gates, abort), CFE
automounter (surprise removal), USB remount"; "Step 5 needs the `/usr/local/libexec` install");
`tutorials/README.md:107` ("`media_mounted` = alive, record gates, abort on removal, CFE surprise
removal, USB remount"); T20 (WebUI half: honest record button, `media_state`) `llm/tutoring.md:96`,
`tutorials/README.md:109`. The tutorial text itself is an external workbook (Downloads) — not here.

| T18 item | At f60e301 | Evidence |
| --- | --- | --- |
| `mediaRootAlive` / `media_mounted` = alive (statvfs probe) | **Not implemented** | `git grep -i 'mediaRootAlive\|media_state\|mediaAlive\|mountAlive\|media_alive' f60e301 -- src include` → no hits (also none at HEAD 6853891). `media_mounted` is `/proc/mounts` presence only (`:2023-2038`, `:7732`, `:7914`) |
| Record gates on media | **Not implemented** for camera recording; exists for Sound Recorder only (`:8367-8371`) and for the speed test (`:8986-8990`) | `record_start` `:10690-10781`; `startRecording` `:5876-5882` |
| Abort on removal | **Partially present by accident**: cDNG/MLV/H.264/ProRes/audio stop on the first failed write via `RecordingFailure` + the 1 s supervisor (`:3958-3968`, `:8990-9003`, `:7043-7046`); lossy DNG does **not** abort (`LossyDngEncoder.cpp:230-232`, `:508-511`); no errno classification, no mount-alive trigger, stop path still touches the dead medium | §1 |
| CFE automounter surprise removal | **Not in Core**; the automounter is a separate UI-repo binary (`apertar-cfe-automounter`, installed to `/usr/local/libexec`, 100 ms I2C loop, insert edge → `mountPcie`, eject edge → `unmountPcie`; KB `architecture/ui.md:391`, `:402-408`). Core only reacts after its *own* NVMe eject with the embedded Python watcher (`:3751`, `:3389-3611`), which races the automounter (KB `lessons/upstream-issues.md:27` #20) | KB → PROBABLE for the automounter; Core side CONFIRMED |
| USB remount | **Manual only**: `mount_media` with a device from `media_drives[]` (`:3666-3714`, `sudo -n mkdir -p` + `sudo -n mount -t ...`, `:3613-3660`); no device-event listener, no auto-remount, `udisksctl power-off` on eject kills the USB port power path (`:3738-3742`) | CONFIRMED |
| T20 `media_state` / honest WebUI record button | **Not implemented**: no `media_state` string in Core or WebUI; record button disabled rule ignores `hasMedia` (`WebControlPage.cpp:9836-9838`) | CONFIRMED |

---

## 5. Gaps vs Cinemate's sequence

y1's brief is unavailable; the Cinemate side below is what I opened (CONFIRMED where cited).

| Step | Cinemate (d6cc93e / 63a08d5) | Core (f60e301) | Gap |
| --- | --- | --- | --- |
| Detection | Root automounter: udev `remove` for partition/disk (`storage-automount.py:913-919`) **and** a 3 s statvfs watchdog with `YANK_ERRNOS = {EIO, ENOENT, ENODEV, ENOTCONN, ESTALE}` (`:97-103`, `:836-866`), skipping `mmcblk` because statvfs can block 30 s+ on bad SD mounts (`:840-843`). Python `SSDMonitor`: `os.path.ismount` every 1 s (`src/module/ssd_monitor.py:98-99`, `:322-343`), statvfs free-space probe with the same errno set → forced lazy unmount + `_handle_unmount` (`:731-770`, `:773-808`). cinepi-raw refuses to start a take unless `disk_mounted()` (`cinepi/cinepi_controller.hpp:211-215`, `cinepi/utils.cpp:34-36`) | Only the write failure itself (cDNG/MLV/H.264/ProRes) seen by the 1 s supervisor; nothing while idle; lossy DNG never notices | No statvfs/ismount probe, no errno classification, no udev source, no idle detection |
| Stop | cinepi-raw counts `write_failures_` and continues (`cinepi/dng_encoder.cpp:2351-2386`); the automounter promotes a standby RAW drive "so recording can continue" (`storage-automount.py:760-770`, `:850-852`); the Python layer gates `rec` on `is_mounted` and free space (`cinepi_controller.py:2352-2364`). I found no subscriber to `SSDMonitor.unmount_event` in `src/module` (grep) → PROBABLE that Cinemate does not actively stop a take on unmount either | Latched failure stops the take within ~1 s (except lossy DNG) | Core actually stops sooner than Cinemate; what it lacks is a *clean* stop (no medium access, errno-aware message) |
| Cleanup | Automounter `umount -l` + sysctl restore (`:853-858`), standby promotion, removes stale mount points (`:410`); `SSDMonitor._handle_unmount` resets Redis (`is_mounted=0`, `space_left=0`, profile defaults) and switches the CFE HAT LED off (`:391-431`) | Stop path re-touches the dead FS (MLV header patch `MlvEncoder.cpp:1050-1062`, H.264 rename `CameraController.cpp:4863-4879`, lossy drain `:3520-3521`, WAV finalize `AudioRecordingSession.cpp:567-573`); stale mount stays in `/proc/mounts` (PROBABLE) so `media_mounted` stays true | No lazy unmount (needs root), no "skip finalisation" mode, no state reset |
| UI | Redis `is_mounted` → GUI (`simple_gui.py:1003`) | `recording_error` toast after the 1 s poll; `media_mounted` keeps lying until an unmount happens | No media event, no alive flag |
| Re-insert | Automounter: udev `add` → mount (RAW pool / standby), CFE latch messages (`storage-automount.py:1001`), eject flag cleared on real `remove` (`:66-67`, `:919`) | NVMe: only after a *deliberate* Core eject, via the embedded Python helper (60 s give-up, races `apertar-cfe-automounter`); USB: manual `mount_media` | No surprise-removal → re-insert path at all in Core |
| Eject-intent race | cinemate touches `/run/cinemate-storage/eject/<devname>` **before** unmounting; the automounter leaves flagged devices alone and clears the flag on a real udev `remove` (`storage-automount.py:55-72`) | `ejectMediaAtPath` has no intent signal; Core's own watcher and the automounter both react to the same insert edge (#20); the UI's copy of the watcher checks `/run/apertar-cfe/ready` but Core's does not (KB `architecture/core.md:494`) | No shared flag directory |

---

## 6. What a port needs in Core

1. **A media-alive watcher** (the `mediaRootAlive` of T18). Natural home: a small dedicated thread
   owned by `ApertarCoreApp` (next to `previewThread_`/`mjpegThread_`/`mediaSpeedThread_`,
   `ApertarCoreApp.hpp:147`, `:157`, `:176`) rather than the `wait()` tick, because the probe can block
   on a hung USB device (Cinemate skips SD for that reason, `storage-automount.py:840-843`) and the
   tick holds `commandMutex_` (`:7043-7046`). Checks per cycle: `isMountedPath()` (`/proc/mounts`),
   `statvfs(mediaRoot)` classifying `EIO/ENODEV/ENXIO/ENOTCONN/ESTALE/ENOENT` as "removed", device
   identity via `mountedDeviceForPath()` (standby swap), free bytes. Publish the result as atomics that
   `buildWebStateJson`/`get_state` read instead of re-parsing `/proc/mounts` and running `lsblk` per
   request (`:7732-7738`, `:2275-2300`). Interval: 1 s idle (matches Cinemate's SSDMonitor), 250-500 ms
   while `camera_.isRecording()`. On "removed" while recording: call a new
   `CameraController::abortRecording(reason)` that reuses `checkRecordingFailure`'s stop path
   (`:8990-9003`) with a pre-set message so the UI text says "Media removed", not "Input/output error".
2. **Fail fast and errno-aware in the recorders.** cDNG/MLV already latch on the first failed frame;
   change the catch sites (`CameraController.cpp:3856`, `:3947`) to catch `std::system_error` first
   and classify `code().value()`: `ENOSPC` → "media full" (orderly stop, keep files), the removal set
   above → "media removed" (stop without touching the medium), `EACCES/EPERM/EROFS` → permission
   message. Lossy DNG must stop lying: give `LossyDngDiskWriter` a failure sink (count + first message)
   that `dngWorkerLoop` polls after each `writeDngFile`, or make the queue own a `RecordingFailure*`
   the writer sets (`LossyDngEncoder.cpp:215-243`). Also count frames discarded after `failRecording`
   (`:3637-3642`, `:3831-3836`) so `discarded_on_stop` (#40) finally means something.
3. **Stop ordering for a removal.** Add a "medium dead" flag to `CameraSession::stopRecording()`
   (`:5990-6013`) so the recorders skip finalisation that re-opens the medium: MLV `patchFrameCount`
   (`MlvEncoder.cpp:1050-1062`), H.264 rename/copy_file (`CameraController.cpp:4863-4879`), lossy
   `drainWrites` (drop the queue instead, `:3520-3521`), audio WAV finalize (`AudioRecordingSession.cpp:567-573`).
   Order stays gate → gyro → video → audio, but with a bounded wait; the stop runs under
   `CameraController::mutex_` and `commandMutex_`, so a hung `close()` on a dead FUSE/NTFS mount would
   freeze every command — finalise on a detached thread as the H.264 recorder already does
   (`:4812-4841`) and keep `hasPendingPhotoCaptures()` true meanwhile (`:5733-5740`).
4. **Events and fields for the UIs.** Add `media_state` (e.g. `mounted` / `removed` / `none` /
   `full`) and `media_alive` next to `media_mounted` (`:7914`), and a new broadcast event
   `{"event":"media", ...}` emitted by the watcher on any transition; put it in the always-broadcast
   list of `publishEvent` (`:10896-10907`) so the HDMI process gets it without polling. Keep
   `recording_error` (`:7852`) as the human text; WebUI already toasts it (`WebControlPage.cpp:9363-9365`)
   and should gate the record button on `hasMedia` (`:9836-9838`, T20).
5. **Record gates.** One gate in `handleCommand` for `record_start`, `capture_photo`,
   `timelapse_start` (`:10690`, next to the existing `mediaWritesPending` gate `:9111-9113`): mounted
   **and** alive **and** free bytes above a per-format threshold; the hardware record actions already
   route through `handleCommand` (`:8870-8885`) so one gate covers socket, WebUI and buttons. Mirror it
   inside `CameraSession::startRecording` before `reserveClipFolder` (`:5876-5882`) as the last line of
   defence (today a take with no media lands on the SD card).
6. **Eject intent.** Before `udisksctl unmount` in `ejectMediaAtPath` (`:3734-3736`) write an intent
   flag the automounter can honour (Cinemate's `/run/cinemate-storage/eject/<dev>` pattern,
   `storage-automount.py:55-72`), and skip Core's embedded Python watcher (`:3751`) when
   `/run/apertar-cfe/ready` exists (KB `architecture/core.md:494`).
7. **What cannot be done without the root automounter helper.** Core is unprivileged and only has
   `sudo -n` one-liners (`mount`, `mkdir`, `blockdev --flushbufs`, `sh -c 'echo 1 > .../remove'`,
   `:3362`, `:3380`, `:3613-3620`) plus polkit for `udisksctl`: (a) lazy unmount of the dead mount
   (`umount -l`) — needs root or a sudoers rule; (b) PCIe remove / rescan / `brcm-pcie` unbind-bind for a
   surprise-removed CFE card (`:3558-3569` does it today via `sudo -n sh -c`, from an un-supervised
   background process); (c) udev event delivery (netlink monitor) — possible unprivileged with
   libudev, but mounting the re-inserted device is not; (d) the per-device sysctl/scheduler profile that
   Cinemate applies at mount. All of these belong in the `apertar-cfe-automounter`
   (`/usr/local/libexec`, T18 Step 5) with a small file/socket contract back to Core (ready file, intent
   flags, "mounted <dev> at <path>" notifications) — Core should then only *observe* mounts, never own
   them.

## UNKNOWN / not derivable here

- The T18 tutorial text (external workbook) — only its row and README summary were readable.
- The y1 brief's Cinemate sequence — not present in `working/port-raw/`.
- Whether the kernel keeps a yanked USB/NVMe mount in `/proc/mounts` on this image (PROBABLE yes, from
  Cinemate's design, not read in kernel source).
- Touch-UI (`Apertar-UI`) and `apertar-cfe-automounter` behaviour on surprise removal — repo not local;
  only KB summaries (`architecture/ui.md:402-408`).
- Gyro recorder runtime write-failure handling (not read).
- `cinemate-handbook/lessons/hardware-log.md` has no dated entry about yanking media (grep
  `yank|surprise removal|hot-?unplug` → no hits).

---

## Verification

Verifier: adversarial pass over every finding above. Method: every Apertar-Core citation was opened
in the `git show f60e301:<path>` text of the file (worktree HEAD is no longer f60e301, see below),
anchored with `grep -n`, then read as a window; Cinemate/cinepi-raw citations were read in the
checkouts (`cinemate @ d6cc93e`, `cinepi-raw @ 63a08d5` confirmed with `rev-parse`). Nothing was run
on hardware. Verdicts: CONFIRMED = line and content exact; CORRECTED = claim stands, citation or a
detail fixed (given); REFUTED = source shows otherwise; UNVERIFIABLE = not derivable here.

Repository state at verification time (differs from the reader's header):

- `apertar-core` worktree HEAD is now **`2715569` on `clearhdr-fixes`** ("media: survive a yanked or
  unmounted recording drive"), five commits past `f60e301` (`f60e301` → `2f5a880` → `d3c1b17` →
  `6853891` → `2a6f114` → `2715569`). All f60e301 line numbers above still hold because they were
  taken from `git show f60e301:`; but the reader's "none at HEAD 6853891" statements are stale —
  `2715569` adds `src/util/MediaProbe.hpp`, `MediaFault.hpp`, `MediaIntent.hpp`, `media_state` /
  `media_alive` fields (`HEAD:src/ApertarCoreApp.cpp:7932-7933`) and a media watcher thread
  (`HEAD:src/ApertarCoreApp.hpp:183`). The port described in §6 has started landing; this file stays
  a description of f60e301.
- `apertar-kb` HEAD is `0afcb31`, not `c99ff77`; KB line numbers below are the working tree's.
- `working/port-raw/y1-yank-cinemate.md` **exists** (written 08:14, before this file's 08:18). The
  reader's "y1 brief unavailable" is stale; see F16 and "Added".

### Per-finding verdicts

| # | Finding | Verdict | Evidence |
| --- | --- | --- | --- |
| F1 | `/proc/mounts` is the only alive signal; no statvfs/udev/inotify | **CONFIRMED** | `isMountedPath` `App:2023-2038`, `mountedDeviceForPath` `:2040-2055`, `nearestExistingPath` `:320-326`, `space()` `:7792-7798`, zero-on-error `:7799-7800` all exact. `grep -nE 'inotify\|netlink\|libudev\|udev_monitor\|statvfs'` over `App.cpp`, `App.hpp`, `CC.cpp` at f60e301: no hits. Minor: the markdown's `udevadm` lines are wrong — `udevadm info` is `:3340` (in `pciAddressForDevice`, not `:3374`), `udevadm settle` `:3385`, Python `:3575` (not `:3569`), plus `:3850`, `:3859` in the format path. |
| F2 | cDNG/MLV stop after the first failed frame; discarded frames uncounted | **CONFIRMED** | Catch blocks `CC:3856-3861` (`++writeFailures_` :3857, message :3859) and `:3947-3952` exact; `failRecording` `:3958-3967` (sets `failure_`, `active_=false`, `stopping_=true`, `queue_.clear()`, `notify_all`); `RecordingFailure.hpp:8-25` (first message wins :13, default text :14); `hasCapacityForFrame` `:3637-3642` returns false silently on `stopping_ \|\| !active() \|\| workers_.empty()` :3640-3641; `recordRawFrame` early return `:7189-7192`. Numbers exact: default queue 12 / 24 for compressed DNG on ≥ 4 threads `:3437`, env `APERTAR_CDNG_QUEUE_FRAMES` 4..64 `:3438-3439`, member default `:4029`; workers MLV 1, lossless `min(8, threads+1)` env 1..8 `:3442-3455`, lossy `max(1, min(4, threads))` env `APERTAR_LOSSYDNG_WORKERS` `:3449`, `:3454`. Stats line `:3525-3532` prints only when some counter > 0 (`:3523-3524`). `discardedOnStopFrames_` declared `:3365`/`:4007`, reset `:3413`, read `:3618`, never incremented (#40 holds). |
| F3 | Encoders throw `system_error` with errno; MLV returns false; queue never inspects errno | **CORRECTED** (one range) | "Failed to open DNG for writing" is `CdngEncoder.cpp:1755-1756`, not `:1758-1759` (`:1758` is `posix_fadvise(SEQUENTIAL)`). `writeErrno` `:1778`, close-error fold `:1780-1783`, `unlink` `:1786-1787`, "Failed to write DNG" `:1800-1801` exact. `MlvEncoder.cpp` `writeAll` `:62-78` (zero write → `EIO` `:72-75`), `writeFrame` `:999-1046`, `close()` `:1048-1062` ("MLV finalize warning" `:1055-1058`), `patchFrameCount` `:1280-1292` exact. Addition: the MLV payload failure *is* a `std::system_error` with errno (`:1036-1037`) but `writeFrame`'s own catch flattens it to a string (`:1041-1045`), so the errno number is lost one level below the queue. |
| F4 | Lossy DNG never stops: async writer only logs | **CONFIRMED** | `LossyDngEncoder.cpp:229-232` (log only, `strerror(errno)`), `:325-328` env (also honours `QRAW_LOSSYDNG_ASYNCWRITE` as fallback `:326-327`; async unless the value starts with `0`), `:508-515` (submit vs throwing sync path), `CC:3519-3520` `drainWrites()` exact. |
| F5 | H.264 failure paths, finalize, detached finalizer | **CORRECTED** (ranges) | Copy failure is `CC:4979-4983` (not `:4991-4996`, which is the encode-queue push). Encode/write failure `:5046-5063` (cited `:5042-5063`, fine); `wroteFrame` comes from `encodeLibavFrame` or `writeAll(writeFd_, …)` at `:5032-5038` (the markdown's `:4781-4792` is `closeWriteFd()`); libav flush failure also counts a write failure without latching `failure_` `:5072-5074`. Paths `.mp4` / `.mp4.writing` are `:4114-4115` (not `:4121`); folder `create_directories` `:4105-4109` (not `:4111-4116`). `skip[stopping]` `:4372-4378`, finalize rename/copy `:4863-4878`, exit code/signal `:4881-4889`, stats `:4903-4914`, `stopInternal` `:4812-4841` (finalizer thread `:4838`), `finalizing()` in `hasPendingPhotoCaptures` `:5738` exact. Queue depth: member default 6 `:5119` but overwritten by `h264QueueDepth()` `:4574-4583` = env `APERTAR_H264_QUEUE_FRAMES` clamped 2..16, else 6. |
| F6 | ProRes latches, stops accepting, releases queue; repair never invoked | **CONFIRMED** (repair claim is KB-derived) | `ProresRecorder.cpp:110` `run()`, encode failure `:123-136` (log `:134`), `finish_()` failure `:139-143`; `ProresRecorder.hpp:23-24` (`active()` = `accepting_`, `error()`). "Repair never called" rests on `apertar-kb/architecture/core.md:429` only — label it KB, not source-verified here. |
| F7 | Audio write failure latches; audio error reported first | **CONFIRMED** | `AudioRecordingSession.cpp:472-473` exact; `CC:6223-6230` (`audioRecorder_.error()` first `:6226`). |
| F8 | Supervisor `checkRecordingFailure` from 1 s tick + `handleCommand` head | **CONFIRMED** | `CC:8990-9003` (function runs to ~`:9005`), `CameraController.hpp:80`, `App:7032-7046` (`wait_for(1 s)` `:7037`, `commandMutex_` `:7043`, call `:7044`), `App:9109-9110` exact. |
| F9 | Stop ordering touches the medium again; no "medium gone" distinction | **CONFIRMED** | `CC:5990-6013` exact (flag `:5993`, `emitMediaWriteState` `:5994`, gate `:5997`, capture stats `:5998-6003`, gyro → H.264 → recorder → ProRes → audio `:6004-6008`, flag cleared `:6012`); WAV finalize reopen `AudioRecordingSession.cpp:565-573`. |
| F10 | `recording` event → `publishEvent` → tally; `/api/state` + 1000 ms poll + toast | **CONFIRMED**; PROBABLE part settled (see Added A3) | `CC:9265-9275`, `App:10890-10918` (always-broadcast list `:10896-10905`, collection `:10911-10914`), `handleTriggerEvent` `:10921-10937` (recording branch `:10928-10937`), `:7852-7854`, `:9261`, `WebControlPage.cpp:11643`, `:9363-9365`, `:9144` (80 ms after `record_start`, 140 ms otherwise) exact. |
| F11 | Deliberate eject path, NVMe detach, embedded Python reinsert watcher | **CORRECTED** (bit0 polarity inverted; several ranges) | Exact: `flushMediaPath` `:3355-3364`, `detachNvmeController` `:3366-3387`, `startNvmeReinsertWatcherAtPath` `:3389-3611`, constants `:3400-3404`, config override `:3458-3462`, waits `:3582-3594`, launch `:3603-3604`, `ejectMediaAtPath` `:3719-3770`, `udisksctl unmount` `:3735`, `power-off` `:3741`, detach `:3748`, watcher `:3751`, error texts `:3757-3767`, helpers `:1553`, `:1558`, `:9168`. Off: `read_insert_state` is `:3493-3504` (not `:3487-3497`), `wait_for_nvme_partition` `:3536-3543`, `mount_partition` `:3545-3562` (not `:3539-3556`), `reset_pcie_controller` `:3564-3575` (not `:3558-3569`). **Polarity**: `read_insert_state` returns `(byte & 0x01) == 0x01` (`:3502`) and the main flow waits for True, then False, then resets PCIe and mounts (`:3582-3599`) — a remove-then-reinsert sequence only if True = latch open. Cinemate reads the same hat byte with bit0 = 1 as "REMOVED (latch opened)" and bit0 = 0 as "INSERTED (latch closed)" (`storage-automount.py:999-1001`, `:1026-1027`), and `apertar-kb/architecture/core.md:496` lists Core's polarity as unconfirmed. So "bit0 = card present" and "waits for present then absent" are inverted: PROBABLE bit0 = 1 is latch open / card out. **Timing**: 600 × 0.1 s = 60 s is the *minimum* per wait; `read_insert_state` itself blocks up to 0.5 s per call on I2C errors (`:3494-3504`), so a dead bus gives ≈ 600 × 0.6 s ≈ 360 s for the second wait (KB `core.md:493` "about 6 minutes"), and `default_state=True` lets the first wait pass at once. PCIe: 2 s + 3 s inside `reset_pcie_controller` (`:3570`, `:3574`) **plus** another 3 s at `:3599` = up to 8 s; partition poll 0.15 s `:3536`. "Core runs unprivileged": no systemd unit exists in the Core repo at f60e301 (`git ls-tree`), so this is PROBABLE from the `sudo -n` pattern (`:3362`, `:3380`, `:3618`, `:3632`) and KB `architecture/ui.md:391-393`. |
| F12 | No mount/space gate on camera recording; only Sound Recorder and speed test check | **CONFIRMED** | `record_start` `App:10690-10781` (`camera_.startRecording` `:10776`), `CC:8690-8738` (comment `:8719-8721`), `CameraSession::startRecording` `:5878-5882`, `startAtFolder` `create_directories` `:3420-3422`, "Sound Recorder needs mounted media." `:8367-8369`, speed test `:8986-9002` (`freeMiB < 96`), `core.md:419` exact. Missed gate added below (A5). |
| F13 | Other gates (pending writes, media actions, hardware eject, mount_media, WebUI button) | **CONFIRMED** | `App:9109-9126`, `:8907-8913`, `:8870-8885`, `:3666-3673`; `WebControlPage.cpp:9837-9838` (the `disabled` expression has no `hasMedia` term), `:10742-10744`, `:10756-10758`, `:10768-10771` exact. |
| F14 | State fields and events for media; no media event; no `recording_stats`/`drop_warning` | **CONFIRMED** | `media_mounted` `:7914`, `media_free/total/used` `:7934-7936`, `media_label` `:7937`, `media_drives` `:7938`, time-left `:7939-7942`, `write_speed_*` `:7947-7964`, `storage` `:7973`, type label `:7732-7737` + `:1992-2020` (two functions), `lsblk` 3 s cache `:2287`/`:2294`, `buildMediaLibraryJson` `:7684-7697`, `recording_health` `CC:7919-7921`, `media_write_state` `:7890-7902`, Web `:9830-9833`, `:9891`, `:9130-9131`, `:6434` exact. `grep -rnE 'recording_stats\|drop_warning' src` at f60e301: none. Addition: an unrecognised label on a device that is neither `/dev/sd*` nor `/dev/nvme*` is reported as "CFExpress Type B" (fallbacks `:2003-2004`, `:2019`). |
| F15 | T18 items not implemented at f60e301 | **CONFIRMED** (for f60e301; HEAD note above) | `git grep -iE 'mediaRootAlive\|media_state\|mediaAlive\|mountAlive\|media_alive\|statvfs' f60e301 -- src include`: no hits. KB rows `llm/tutoring.md:94`/`:96`, `tutorials/README.md:107`/`:109`, `architecture/ui.md:391`, `:402-408`, `lessons/upstream-issues.md:27` exact. At HEAD `2715569` the same grep hits `MediaProbe.hpp`, `media_state`, `media_alive`, `statvfsErrno` — the items are now in flight in the worktree, not at f60e301. |
| F16 | Cinemate sequence (automounter, SSDMonitor, cinepi-raw) | **CONFIRMED** | `storage-automount.py:97-103` (5 errnos), `:836-864` (`time.sleep(3)` `:864`, "device yanked, unmounting" `:848`, mmcblk skip `:839-842`, promote "so recording can continue" `:850-851`, `umount -l` `:853-857`), `_handle_raw_gone` `:759-769`, `_on_block_removed` `:771-786`, udev remove `:913-919`, eject flag `:55-72`, stale mountpoints `:405-412`; `ssd_monitor.py:98-99`, `:322-343`, `:391-431` (`unmount_event.emit` `:431`), `:731-769`, `:773-808`; `cinepi_controller.py:2352`/`:2364`; `simple_gui.py:1003`; `cinepi-raw/cinepi/cinepi_controller.hpp:211-215`; `utils.cpp:34-36`; `dng_encoder.cpp:2351-2386` (`write_failures_` `:2364`, `:2375`, `:2382`) exact. `grep -rn unmount_event cinemate/src/module` outside `ssd_monitor.py`: none — and y1 §1.4 reaches the same conclusion from the Python side ("Does cinemate stop the take? No.", `y1-yank-cinemate.md:52-54`). |

Port-needs and surprises cross-check: every line they cite was opened (`App.hpp:147`, `:157`, `:176`
thread members exact; `:7043-7046`, `:8990-9003`, `:3856`/`:3947`, `LossyDngEncoder.cpp:215-243`,
`:3637-3642`, `:5990-6013`, `MlvEncoder.cpp:1048-1062`, `CC:4863-4878`, `:3519-3520`,
`AudioRecordingSession.cpp:565-573`, `:4812-4841`, `:5738`, `:7914`, `:10896-10905`, `:7853`,
`WebControlPage.cpp:9365`, `:9837-9838`, `:10690`, `:9111-9113`, `:8870-8885`, `:5878-5882`,
`:3734-3736`, `:3751`, `:3362`, `:3380`, `:3618`/`:3632`, `:3564-3575`). Only the two surprises that
mention "HEAD 6853891 / three commits" need the update above (now `2715569`, five commits; the
`6853891` commit message does say the raw copy moves off libcamera's completion thread).

### Added (settled from source during verification; nothing observed on hardware)

- **A1. The y1 brief exists** (`working/port-raw/y1-yank-cinemate.md`, 08:14) and its Q1 timeline,
  §1.6 latency table (udev remove immediate; statvfs watchdog ≤ 3 s; NVMe `state=dead` ≤ 0.5 s; CFE
  latch 0.05 s; SSDMonitor ≤ 1 s; lazy-unmount retry ≤ 20 × 0.2 s; promotion wait ≤ 2 s; cooldown
  30 s), §1.7 re-insert and Q2 eject-intent agree with §5 above. Two y1 points §5 should carry: the
  CFE *latch* path is the hat's button, not a surprise card pull (y1 §1.1(f)), and a hung device
  (no fast errno) ends a Cinemate take only via the 90 % RAM-pool watchdog or cinepi-raw's own
  `buffer_full()` (y1 §1.5).
- **A2. The kernel keeps a yanked mount mounted** (mechanism CONFIRMED from kernel source; match to
  the Pi image's kernel PROBABLE): block device removal calls `bdev_mark_dead()`
  (`kernel-rpi block/bdev.c:1209-1226@5bd564a`), which calls the holder's `mark_dead` →
  `fs_bdev_mark_dead()` (`fs/super.c:1419-1435`): skip sync on surprise, shrink dcache, invalidate
  inodes, `s_op->shutdown(sb)` (ext4: `ext4_force_shutdown`, `fs/ext4/super.c:1488-1491`), then
  `invalidate_bdev`. Nothing in that path detaches the mount; the superblock stays in `/proc/mounts`
  with I/O returning errors until userspace unmounts. So `media_mounted` keeps reading true after a
  pull, as F1 inferred.
- **A3. The event-swallow race is real (CONFIRMED, was PROBABLE).** `handleRequest()` sets
  `collectingCommandEvents_ = true` at `App:7074` *before* `handleCommand()` at `:7078`;
  `handleCommand` runs `checkRecordingFailure()` at `:9110`; its `recording` event is not in the
  always-broadcast list (`:10896-10905`), so it is pushed to `pendingCommandEvents_` (`:10911-10914`)
  and appended to that one requester's reply (`:7080-7089`). Only the 1 s `wait()` tick (`:7044`)
  broadcasts, and only if no other client's request is being collected at that instant (#36). The
  WebUI is unaffected (it polls `recording_error`); an event-driven consumer such as the HDMI process
  can miss the stop.
- **A4. Gyro recorder on a dead medium is silent.** Samples are buffered and exported at stop; only
  the `ofstream` open failure is reported (`setLastError("Could not create gyro sidecar …")`,
  `Mpu6050RecordingSession.cpp:2232-2235@f60e301`); the sample loop and `output.flush()`
  (`:2268-2275`) never check the stream state, and "gyro sidecar exported" is logged regardless
  (`:2277-2284`). Start failures are non-fatal (`CC:5894-5898`).
- **A5. One more record gate exists**: in Standby, `record_start` / `capture_photo` /
  `timelapse_start` are refused with "Wake the camera before capturing." (`App:9224-9227`).
- **A6. `cinemate-handbook/lessons/hardware-log.md`** has no entry matching
  `yank|surprise removal|hot-?unplug|pulled the (card|drive|ssd)` (grep, confirmed).
- **A7. T18 workbook**: still not on this machine — `grep -rl media-yank apertar-kb` finds only the
  two index rows (`llm/tutoring.md`, `tutorials/README.md`); no `~/Downloads`.

### Still UNKNOWN after verification

- The T18 tutorial text itself (external workbook).
- Touch-UI / `apertar-cfe-automounter` behaviour on surprise removal (Apertar-UI repo not local).
- The actual errno sequence Core's writers see on a pulled USB vs NVMe device (no hardware log in any
  repo; y1 lists the same gap).
- Core's service user (no unit file in the Core repo at f60e301).
- The hat's bit0 polarity as measured (`i2ctransfer` with the card in and out, KB `core.md:496`) —
  the inversion above is from Cinemate's reading of the same byte and Core's own control flow.

### Net effect on "What a port needs"

Items 1-7 stand. Add: (a) classify `std::system_error` at the MLV level too, or stop flattening it in
`MlvEncoder::writeFrame` (`:1041-1045`), otherwise the errno never reaches the queue; (b) put the new
`media` event in the always-broadcast list *and* fix A3 for `recording`, since a stop detected at
the head of a command today reaches only that command's requester; (c) the gyro sidecar export needs
a stream-state check or a "medium dead" skip like the others (A4); (d) if Core keeps its own
reinsert watcher, read the latch as "1 = open" and verify once on the rig (F11), and bound the I2C
retry so a dead bus cannot turn 60 s into 6 min; (e) HEAD `2715569` already carries
`MediaProbe.hpp` / `MediaFault.hpp` / `MediaIntent.hpp` — the tutorial should be written against
that commit's shape, not re-invent it from f60e301.
