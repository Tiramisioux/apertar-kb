# Core code review, branch `drop-frames` @ `adac040`: the DNG write path, the three commits, the capture-gap accounting, the knobs

Written 2026-11-02 from the desk (no Pi). Sources read: `git -C /home/user/Apertar-Core show adac040` (whole diff), `adac040:src/cdng/CdngEncoder.cpp`, `adac040:src/camera/CameraController.cpp` (the regions named below), `adac040:src/lossydng/LossyDngEncoder.cpp`, `adac040:src/mlv/MlvEncoder.cpp`, `adac040:src/util/MediaProfile.hpp`, `adac040:src/ApertarCoreApp.cpp` (media tune, web preview, buffer events, publishEvent), `adac040:src/ipc/ControlServer.cpp`, `adac040:scripts/apertar-media-tune`, `adac040:config/*`, `adac040:README.md:318-330`; commits `64bbbaa`, `6ef0ddc`, `a40112a` (the A0 build); kernel `rpi-6.12.y` @ `5bd564a` (`mm/fadvise.c`, `mm/truncate.c`, `mm/swap.c`, `mm/filemap.c`, `mm/vmscan.c`, `mm/page_alloc.c`, `mm/page-writeback.c`, `Documentation/admin-guide/sysctl/vm.rst`, `arch/arm64/configs/bcm2712_defconfig`); cinepi-raw `cinepi/dng_encoder.cpp:2314-2385`; cinemate `services/storage-automount/storage-automount.py`; KB: night report, takes table, hardware-log 2026-10-26/30/31/11-01.

Status words: **confirmed** (read in source, or measured on the Pi), **probable** (inferred; the reason is given), **unconfirmed** (the measurement is named). All Core line numbers are in `adac040` unless a commit is named. Kernel line numbers are in the `rpi-6.12.y` checkout at `/home/user/tiramisioux/kernel-rpi`. `fs/` is not in that checkout; the few claims that need `fs/sync.c` or `fs/exfat` are labelled probable and say so.

**Page size.** The Pi 5 kernel `6.12.75+rpt-rpi-2712` normally runs 16 KiB pages. Where a page count matters below, both are given: a 16.9 MB frame is 1,031 pages of 16 KiB or 4,126 pages of 4 KiB. `getconf PAGESIZE` on the Pi settles it (one command, before any other reading).

## 0. Findings in one table

| # | Claim | Status | Evidence |
| --- | --- | --- | --- |
| 1 | The `sync`-mode drop is correct: `fsync(fd)` then `posix_fadvise(fd, 0, 0, DONTNEED)` on an `O_RDONLY` fd of a closed, complete file evicts the whole file including its partial last page | confirmed | `CameraController.cpp:4703-4712`; `mm/fadvise.c:113-170`, `mm/truncate.c:288-303`; `fsync` on a read-only fd has worked on this rig since 2026-10-26 (C0011: 258 of 281 frames readable after a pull) |
| 2 | `writer` mode's call frees nothing and ends in `lru_add_drain_all()` per file (25/s), plus a second page-cache walk per file | confirmed | `CdngEncoder.cpp:1886-1887` runs before `close()`, `sync_file_range` runs after (`CameraController.cpp:5204-5206`); `mm/fadvise.c:113-114, 152-168`; `mm/truncate.c:297-298, 521-531` |
| 3 | In `writer` mode the per-frame `sync_file_range` is redundant (the DONTNEED call already started writeback of the whole file); in `sync` mode it is the only per-frame writeback kick and is load-bearing | confirmed (mm side) / probable (`fs/sync.c` not in checkout) | `mm/fadvise.c:113-114`; `CameraController.cpp:4658-4675, 5204-5205` |
| 4 | Consequence for 2026-10-30: A0/A1/A2 ran with the hard-coded per-frame DONTNEED (`a40112a:src/cdng/CdngEncoder.cpp:1780`), i.e. today's `writer`. A2 removed a redundant kick; its 10 % capture loss is not explained by the missing hint. A0, A1, A2 were the first, second and third 10-minute takes of one boot: the same within-boot drift as #69 to #72 | confirmed (code) / probable (reading of A2) | `git show a40112a:src/cdng/CdngEncoder.cpp` line 1780; hardware-log 2026-10-30 (A1, A2) |
| 5 | `APERTAR_MEDIA_SYNC_MS=0` under the default silently turns the drop off except for one warning line per process; a failed `open()` of the clip folder does the same with no warning at all | confirmed | `CameraController.cpp:4320-4332` |
| 6 | MLV: the whole growing file is fsynced and DONTNEED-walked once a second. The walk is over present pages only (xarray `find_lock_entries`), so its cost is O(pages written since the last tick), not O(file size): about the same work as 25 cDNG files. The pre-existing risk is the fsync itself: MLV has no per-frame `sync_file_range`, so each tick flushes a full second of data (415 MB at 16-bit 4K) in one burst, the C0005 pattern | confirmed (code) / unconfirmed (cost at 415 MB/s: never run) | `CameraController.cpp:4699-4700, 5270-5330`; `mm/truncate.c:497-545` |
| 7 | Lossy DNG: the sync thread does run during a lossy take but gets no files (`noteWrittenFile` is only on the cDNG branch; the lossy write is asynchronous on `LossyDngDiskWriter`'s own thread). Under the default `sync`, lossy behaves as `off`: the cache fills at about 140 MB/s (3:1) and kswapd reclaims steadily, with no drain. Untested | confirmed (code) / unconfirmed (frames) | `LossyDngEncoder.cpp:96-113, 236-290`; `CameraController.cpp:4320-4323, 5190-5206` |
| 8 | The sync thread's 25 fsyncs/s on exFAT are a plausible but, on a trimmed drive, measured-harmless writer stall source: each exFAT fsync writes the directory entry synchronously and issues a device FLUSH, under exFAT's superblock lock the writers also take for cluster allocation; `peak_queue=2/12` in every fsync-on take (A0, #78, #80) says the writers never noticed | probable (fs/exfat not in checkout) / measured (queue) | `CameraController.cpp:4689-4718`; hardware-log 2026-10-30 (A0 stacks: `exfat_write_inode > __wait_on_buffer`) |
| 9 | `startWriteback` and `noteWrittenFile` run on the writer threads (`dngWorkerLoop`), right after `writeDngFile` returns, cDNG only; the requeue of a camera request runs on the copy worker, not on libcamera's thread | confirmed | `CameraController.cpp:5200-5206, 8603-8608, 5026, 5063-5074` |
| 10 | Leaner shape: keep as is. The fsync is there for pull-safety (C0010 vs C0011), not for the drop, so it cannot be removed; moving the drop to the writer thread would add a writeback wait to the writers' critical path. One optional 6-line change gives `APERTAR_MEDIA_SYNC_MS=0` a working drop (`sync_file_range(WAIT_BEFORE\|WRITE\|WAIT_AFTER)` instead of `fsync` on the same thread) if the A/B ever needs a "no fsync" arm | recommendation | section 2 |
| 11 | `64bbbaa` adds no per-frame work on the capture thread: one `fetch_add` per gap event; the `buffer` event rides on its own 250 ms thread (at most 4/s, to every socket client). The once-per-take `recording_health` broadcast on the first drop runs on the capture thread, as before | confirmed | `RecordingDropWarning.hpp` (64bbbaa), `ApertarCoreApp.cpp:10945-11005, 14416-14449`, `ControlServer.cpp:175-182` |
| 12 | `6ef0ddc` calls `sched_setscheduler(gettid(), SCHED_FIFO, N)` on the thread that runs `requestComplete`, which is libcamera's CameraManager thread (`requestCompleted.connect` at 8630): the right thread. Without `LimitRTPRIO` it logs the `EPERM` and falls back to `nice -5`. Values above 99 clamp to 99 | confirmed | `CameraController.cpp:8967-8999`, `1332-1345` |
| 13 | A SCHED_FIFO capture thread cannot help a thread that sleeps in direct reclaim or I/O inside a syscall; #22's null result (6.2 % with FIFO 40 vs about 7 %) is consistent with the memory mechanism and against CPU competition from Core's own threads | probable | night report §3 #22; `mm/page_alloc.c:4484-4500` |
| 14 | `dropped_gap_estimate`: `dt_us` about 80 000 at a 40 000 nominal gives exactly `(80000 + 20000) / 40000 - 1 = 1` frame. The count is exact for single skips with a monotonic SOF-timestamp chain; it understates losses inside an fps-ramp grace window (N + 6 frames, at least 10) and before the cadence gate opens; it can overstate when Core itself skips a frame before the cadence call (white balance invalid, raw info invalid), rare | confirmed | `CameraController.cpp:9873-9926, 9052-9068, 9254-9314, 9609-9657` |
| 15 | The journal cannot tell a late requeue from a CFE skip: both leave the same two-period gap; Core logs `drop[requeue-failed]` only when `queueRequest()` returns an error (never seen: `requeue_failures=0` in every take) and `drop[copy-slot]` only when Core itself holds too many requests (`dropped_copy_slot=0` in every take). Two debug switches tell them apart (section 7, M6) | confirmed | `CameraController.cpp:8947-8955, 4979-4997`; takes raw lines |
| 16 | Core's own per-frame work on libcamera's thread is small and allocates about three heap blocks per frame (`uniqueCameraModel` 30 chars, `serial` 16 chars, one deque node for `PendingCopy`), all freed by other threads a frame later: steady-state glibc arena traffic, no new pages. The 16.9 MB copy, the `enqueue` and the requeue are on the copy worker (T25). With a WebUI client attached, the MJPEG downsample (about 0.35 MB output, buffer reused) runs on libcamera's thread | confirmed (code) / probable (no page faults in steady state: `minflt` of the thread, section 7, M8, is the measurement) | `CameraController.cpp:4033-4060, 3833-3838, 9322-9375, 5000-5060`; `ApertarCoreApp.cpp:8175-8225, 9730-9830` |
| 17 | The exFAT writer profile is `{4 workers, queue 12, +0 raw buffers}`; the comments at `CameraController.cpp:4274-4276` ("exFAT/NTFS get 2") and `1452-1454` ("two more buffers") are stale. Default `APERTAR_RAW_CAMERA_BUFFERS` for Clear HDR on exFAT is 8; `maxHeldRequests` = 6 | confirmed | `MediaProfile.hpp:134-147`, `CameraController.cpp:1450-1457, 8608` |
| 18 | The sync thread shares `cv_` and `mutex_` with the writers; `enqueue`'s `notify_one` can wake the sync thread instead of an idle writer, delaying a frame's write by up to one frame period. Pre-existing (since 2026-10-26), harmless at `peak_queue` 2/12, but it may be why the peak is 2 and not 1 | confirmed (code) / probable (effect) | `CameraController.cpp:4691-4692, 4922, 5168-5170` |
| 19 | The journal never records the DONTNEED mode of a take (only the `writer`-era default had no line either). The "recording clip:" line prints workers/queue only for lossless and lossy | confirmed | `CameraController.cpp:4346-4373`; `git grep -i dontneed adac040 -- src` |
| 20 | `apertar-media-tune` (pi-nvme) sets `dirty_bytes` 1 GiB, `dirty_background_bytes` 256 MiB, `dirty_ratio`/`dirty_background_ratio` 0, `dirty_writeback_centisecs` 150, `dirty_expire_centisecs` 3000, block queue `none`/512/`rq_affinity` 2, `nvme_core` APST 0. It does **not** set `min_free_kbytes`. It runs only with `APERTAR_MEDIA_TUNE=1`, when the media root is mounted, through `sudo -n`, and needs the helper and the sudoers file installed. Cinemate's automounter does not set `min_free_kbytes` either: that knob was the 2026-11-01 session's own addition, not CineMate-style | confirmed | `scripts/apertar-media-tune:73-100`; `ApertarCoreApp.cpp:11352-11386`; `storage-automount.py:319-336`; `grep -rn min_free /home/user/cinemate` empty |
| 21 | The dirty limits of #80 are very probably inert for this writer: with per-frame `sync_file_range` the measured peak `Dirty` was 11 MB (A0) and 3 MB (A1), against thresholds of 256 MiB / 1 GiB (hand) or about 350 / 700 MB (kernel default, 10 % / 20 % of dirtyable memory). Of the three things #80 changed, `min_free_kbytes` is the only memory-side one that engages during a clean take: it moves the kswapd band (low to min) from about 4 MiB to 16 MiB, i.e. from about 10 ms to 40 ms of page-cache allocation at 415 MB/s | probable (arithmetic from source; the exact zone figures are in `/proc/zoneinfo`) | `mm/page-writeback.c:347-366, 377-440`; `mm/page_alloc.c:6125-6180`; hardware-log 2026-10-30 (A0, A1 peak dirty) |

## 1. `adac040`: the diff and the write path around it

### 1.1 What the commit changes

Three files, 10 lines (`git -C /home/user/Apertar-Core show adac040 --stat`). `CdngEncoder.cpp:83-96` swaps the default of the parser:

```cpp
DngPageCacheDrop dngPageCacheDrop()
{
    static const DngPageCacheDrop mode = []() {
        const char *text = std::getenv("APERTAR_DNG_DONTNEED");
        if (!text || !*text || std::strcmp(text, "sync") == 0)
            return DngPageCacheDrop::Sync;
        if (std::strcmp(text, "writer") == 0 || std::strcmp(text, "1") == 0)
            return DngPageCacheDrop::Writer;
        if (std::strcmp(text, "off") == 0 || std::strcmp(text, "0") == 0 || std::strcmp(text, "false") == 0)
            return DngPageCacheDrop::Off;
        std::cerr << "ApertarCore cdng: APERTAR_DNG_DONTNEED=" << text << " is not sync|writer|off: using sync\n";
        return DngPageCacheDrop::Sync;
    }();
    return mode;
}
```

The two call sites were already there (commit `0ed07ea`, PR #4): the writer-mode call and the sync-mode call. The commit does not touch them. `CdngEncoder.hpp:13-17` and the README rows (`README.md:324, 326`) follow. Nothing else in the diff. **Confirmed.**

### 1.2 The sync-mode drop: `fsync` then `DONTNEED` on an `O_RDONLY` fd

`CameraController.cpp:4689-4718`:

```cpp
    void syncLoop(int dirFd, std::chrono::milliseconds interval)
    {
        std::unique_lock<std::mutex> lock(mutex_);
        while (!cv_.wait_for(lock, interval, [this] { return stopping_; })) {
            lock.unlock();
            std::vector<std::string> files;
            {
                std::lock_guard<std::mutex> filesLock(writtenFilesMutex_);
                files.swap(writtenFiles_);
            }
            if (recordingFormat_ == RecordingFormat::Mlv)
                files.push_back(mlvPathString_);
            for (const std::string &path : files) {
                if (mediumGone_.load(std::memory_order_acquire))
                    break;
                const int fd = ::open(path.c_str(), O_RDONLY | O_CLOEXEC);
                if (fd >= 0) {
                    ::fsync(fd);
                    // APERTAR_DNG_DONTNEED=sync: the pages are clean now, so this call frees them without
                    // the cross-CPU drain the writer's call pays on dirty pages.
                    if (dngPageCacheDrop() == DngPageCacheDrop::Sync)
                        ::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);
                    ::close(fd);
                }
            }
            if (!mediumGone_.load(std::memory_order_acquire))
                ::fsync(dirFd);
            lock.lock();
        }
    }
```

Correctness, point by point:

- **The file is complete and closed when it gets here.** `noteWrittenFile(job.path)` (`:4681-4687`) is called at `:5206`, after `encoder.writeDngFile()` returned, which closes the fd at `CdngEncoder.cpp:1888-1891`. So `fsync` never races a writer on the same inode. Confirmed.
- **`fsync` on an `O_RDONLY` fd.** Linux's `fsync(2)` does not require write access (the VFS path checks only that the fd is open and has an `fsync` op; `fs/sync.c`, not in the checkout, so probable from the API), and the rig has exercised this exact code since 2026-10-26: C0011's pull test found 258 full frames on the card with this `syncLoop` (hardware-log 2026-10-26, "pull mid-take with per-file fsync"). Measured.
- **After `fsync` the pages are clean and not under writeback**, so `mapping_evict_folio` (`mm/truncate.c:288-303`) succeeds for each one:

```c
	if (folio_test_dirty(folio) || folio_test_writeback(folio))
		return 0;
	/* The refcount will be elevated if any page in the folio is mapped */
	if (folio_ref_count(folio) >
			folio_nr_pages(folio) + folio_has_private(folio) + 1)
		return 0;
```

  The only way a folio can still fail is the refcount line: a folio sitting in a remote CPU's `lru_add` batch (`mm/swap.c:503-515`, batches of up to 15 folios, drained when full or on that CPU's next `lru_add_drain`). A writer that wrote 1,031 (or 4,126) pages of a frame flushed its batch about 70 (275) times during the write; only the last partial batch can linger, and it is flushed by that writer's next frame about 160 ms later. One second later it is gone. So `nr_failed` is 0 for almost every file and the expensive branch (`mm/fadvise.c:165-168`, `lru_add_drain_all()` plus a second walk) runs about 0 to 1 times per tick, not 25 times per second. Probable; M5 in section 7 measures it.
- **Whole-file range.** `len = 0` makes `endbyte = LLONG_MAX` (`mm/fadvise.c:71-75`). The partial-page guard at `:132-137` is `if ((endbyte & ~PAGE_MASK) != ~PAGE_MASK && endbyte != inode->i_size - 1)`: `LLONG_MAX`'s low bits are all ones, so the condition is false and `end_index` is not decremented: the last, partial page of the DNG is evicted too. Confirmed.
- **Cost on the sync thread per tick:** 25 opens, 25 fsyncs, 25 fadvise walks of about 1,031 (4,126) present entries each via `find_lock_entries` in batches of 15 (`mm/truncate.c:510-543`), 25 closes, one directory fsync. The walk is roughly 26k (103k) folio lock/unlock/`remove_mapping` operations per second: tens of milliseconds of CPU per second on one thread. Fine for the writers (different thread) and the capture (different thread). Probable.

One thing the comment on `:4707-4708` says that is slightly too strong: "frees them without the cross-CPU drain" is true for clean, unreferenced folios; a folio in a remote batch still costs one `lru_add_drain_all` for that file. The difference from `writer` is the count (0-1/s against 25/s), not zero.

### 1.3 `APERTAR_MEDIA_SYNC_MS=0`: the warning, and a path without one

`CameraController.cpp:4320-4332`:

```cpp
        if (const unsigned int syncMs = unsignedEnvValue("APERTAR_MEDIA_SYNC_MS", 1000, 0, 60000); syncMs > 0) {
            mediaDirFd_ = ::open(folderPathString_.c_str(), O_RDONLY | O_DIRECTORY | O_CLOEXEC);
            if (mediaDirFd_ >= 0)
                spawnWorker([this, syncMs, fd = mediaDirFd_] { syncLoop(fd, std::chrono::milliseconds(syncMs)); });
        } else if (dngPageCacheDrop() == DngPageCacheDrop::Sync) {
            static bool warned = false;
            if (!warned) {
                warned = true;
                std::cerr << "ApertarCore recording: APERTAR_DNG_DONTNEED=sync needs the sync thread (APERTAR_MEDIA_SYNC_MS > 0); "
                             "written frames stay in the page cache until the kernel reclaims them\n";
            }
        }
```

- With `=0` the drop is off and the take behaves as `off`: the cache fills in about 6 s at 415 MB/s (2.6 GB free) and the kernel reclaims the rest of the take (kswapd plus, when it falls behind, direct reclaim by whoever allocates). No drain per frame. Whether `off` loses frames is untested; the `writer` takes showed that reclaim regime plus the drain loses 1-3 %. Confirmed (code) / unconfirmed (frames).
- **Is the warning enough?** For an A/B knob nobody runs in production: yes, with two reservations. (a) It prints once per process, so a session that restarts Core sees it once in the journal and never again for later takes. (b) If `::open()` of the clip folder fails (`:4321`), there is no sync thread and **no warning**: `noteWrittenFile` silently returns (`:4683-4684`, `mediaDirFd_ < 0`). Unlikely after `create_directories` succeeded, but it is a silent `off`. A one-line `std::cerr` on the failed open would close it.
- The night report's decision to leave `MEDIA_SYNC_MS` at 1000 (§8.4) is right for a second reason the 2026-10-30 A1 result does not touch: the per-file fsync is what keeps a pulled take readable (C0010: 0-byte files with folder fsync only; C0011: readable with per-file fsync). The fsync was never there for the drop or for drop-free recording.

### 1.4 MLV under `sync`

`syncLoop` pushes `mlvPathString_` every tick (`:4699-4700`), so the whole growing `.MLV` is `fsync`ed and then DONTNEED-walked once a second. `mlvWorkerLoop` (`:5270-5330`) is one thread that appends with `::write` (`MlvEncoder.cpp:68, 952, 965`: `O_WRONLY|O_CREAT|O_TRUNC`, `FADV_SEQUENTIAL`, no `sync_file_range`, no `fsync`).

- **Cost as the file grows.** `mapping_try_invalidate` walks the xarray with `find_lock_entries` (`mm/truncate.c:510`), which visits present entries only. After each tick's drop, the file's cache holds only the pages written since (about 1 s = 415 MB = 25k or 101k pages) plus the dirty pages of the frame in flight. So the walk is O(data per tick), the same as 25 cDNG files, however large the file gets. The frame being appended is dirty, so `nr_failed > 0` and the tick pays one `lru_add_drain_all` and a second pass over the present entries: once a second, fine. Confirmed (code), cost figures probable.
- **The real MLV risk is older than `adac040`:** there is no per-frame `sync_file_range` for MLV (`startWriteback` is only on the cDNG branch, `:5204-5205`), so the once-a-second `fsync` does `file_write_and_wait_range` over a whole second of dirty data in one burst, with the MLV writer still appending to that inode (the metadata half of the fsync takes the inode lock the writer's `write` also needs). This is the C0005 shape ("writeback + syncfs 1 s: 782 queue drops", hardware-log 2026-10-26) on a single file. At 16-bit 4K 25 fps it has never been run. Unconfirmed. If MLV is ever used at that rate, the least intrusive fix is one line in `mlvWorkerLoop` after `writeFrame`: `if (startWritebackPerFrame()) startWriteback(job.path);` under the existing `APERTAR_DNG_WRITEBACK` knob (`sync_file_range(fd, 0, 0, SYNC_FILE_RANGE_WRITE)` on the growing file starts writeback of its dirty pages only).

### 1.5 Lossy DNG under `sync`: behaves as `off`, and why

`LossyDngEncoder.cpp:96-113`:

```cpp
    const int fd = ::open(path.c_str(), flags, 0644);
    ...
    ::posix_fadvise(fd, 0, 0, POSIX_FADV_SEQUENTIAL);
    bool ok = writeAll(fd, data, size);
    const int writeErrno = errno;
    // The same knob as the cDNG writer (APERTAR_DNG_DONTNEED); lossy takes have no sync thread, so "sync" leaves
    // the pages to the kernel like "off".
    if (dngPageCacheDrop() == DngPageCacheDrop::Writer)
        ::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);
```

This `writeFile` runs on `LossyDngDiskWriter`'s own thread (`:236-290`, `threadMain`), fed by `writeDngFile` which encodes into a `memfd` (`:550-557`) and hands the bytes over. Two corrections to the comment and the README:

- The sync thread **does** run during a lossy take: `start()` spawns it for every format (`:4320-4323`), and it fsyncs the clip folder every second. It just never receives a lossy file, because `noteWrittenFile` is called only on the cDNG branch (`:5206`) and the lossy write completes asynchronously, so `dngWorkerLoop` cannot note it. The effect is as described (`off`), the reason is not "no sync thread".
- In `writer` mode the standard encoder's own DONTNEED (`CdngEncoder.cpp:1886`) is also issued on the `memfd` (`destinationFd` borrowed, `:1861-1862`): `generic_fadvise` ignores advice on a `noop_backing_dev_info` mapping (`mm/fadvise.c:50-63`), so that one is harmless.

**Is `off` acceptable for the "Lossy + Log" plan?** As an interim, yes: lossy 3:1 writes about 140 MB/s, so the cache fills in about 20 s and kswapd then reclaims about 35k (16 KiB) pages per second with no drain; whether that regime alone costs capture frames is the open question the night report lists (§8.5). Decide after one 10-minute lossy take with the UI on (section 7, B-lossy). If it loses frames, the least intrusive fix is inside `LossyDngDiskWriter::threadMain`, which is a background thread and may wait: after `writeFile`, `sync_file_range(fd, 0, 0, SYNC_FILE_RANGE_WAIT_BEFORE | SYNC_FILE_RANGE_WRITE | SYNC_FILE_RANGE_WAIT_AFTER)` then `posix_fadvise(DONTNEED)`, behind the same `APERTAR_DNG_DONTNEED=sync` reading ("after the data is on its way"). Lossy has no pull-safety fsync today either, so this changes nothing on that side. Routing lossy paths to `noteWrittenFile` through a completion callback would work too but is more plumbing.

### 1.6 `APERTAR_DNG_WRITEBACK` against the two DONTNEED sites

The writer path per frame, in order (`CameraController.cpp:5200-5206`, writer thread):

```cpp
                    encoder.writeDngFile(job.path, job.frame, job.metadata);
                    if (startWritebackPerFrame())
                        startWriteback(job.path);
                    noteWrittenFile(job.path);
```

Inside `writeDngFile` (`CdngEncoder.cpp:1856-1891`): open `O_WRONLY|O_CREAT|O_TRUNC`, `FADV_SEQUENTIAL` (`:1865`), the writes, then

```cpp
    if (dngPageCacheDrop() == DngPageCacheDrop::Writer)
        ::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);
    if (!output.borrowed && ::close(fd) != 0 && ok) {
```

Then `startWriteback` (`:4668-4675`) reopens `O_RDONLY` and calls `::sync_file_range(fd, 0, 0, SYNC_FILE_RANGE_WRITE)`.

The kernel's DONTNEED begins with (`mm/fadvise.c:113-114`):

```c
	case POSIX_FADV_DONTNEED:
		__filemap_fdatawrite_range(mapping, offset, endbyte,
					   WB_SYNC_NONE);
```

which is `filemap_fdatawrite_wbc` with `nr_to_write = LONG_MAX` over the whole file (`mm/filemap.c:421-432`): asynchronous writeback of every dirty page of the file is started right there. `sync_file_range(..., SYNC_FILE_RANGE_WRITE)` does the same `__filemap_fdatawrite_range(mapping, offset, endbyte, WB_SYNC_NONE)` (`fs/sync.c`, not in the checkout: probable from the upstream source). So:

- **`writer` mode: the hint is redundant.** The DONTNEED call already started writeback of all pages a few microseconds earlier; the second call finds them under writeback and skips them. Confirmed for the mm half, probable for `fs/sync.c`.
- **`sync` mode: the hint is load-bearing.** It is the only per-frame kick. Without it dirty pages wait for the flusher (background threshold about 350 MB at the kernel default, 256 MiB with the helper; `dirty_writeback_centisecs` 500 default / 150 helper) or for the sync thread's `fsync` a second later, which then flushes a 415 MB burst per tick: the C0005 shape again. Keep `APERTAR_DNG_WRITEBACK` on. Confirmed (code) / probable (effect, from C0004 vs C0005).

**What this does to the 2026-10-30 entry.** `a40112a` (the A0 build) has the unconditional call at `src/cdng/CdngEncoder.cpp:1780`:

```cpp
    ::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);
```

plus `startWriteback` at `:4113-4118` and the per-file `fsync` at `:4151`. So A0, A1 and A2 all ran what is now `writer`. A2 (no `sync_file_range`) removed a redundant writeback kick and nothing else, and still lost 10 % at capture. The reading "the per-frame writeback hint is what keeps the camera front end from stalling" therefore does not follow from A1 vs A2. What does fit: A0, A1, A2 were the first, second and third 10-minute takes of one boot (clean, clean, 10 %), the pattern of #69 to #72 on 2026-11-01. The entry is append-only; a new entry with this correction is due once Patrik agrees. Confirmed (code) / probable (reading).

### 1.7 Twenty-five `fsync`s a second on exFAT: a writer stall source?

What one `fsync` of a finished DNG costs, in order: `file_write_and_wait_range` (short: the data was kicked by `sync_file_range` right after the write), then the inode's metadata. exFAT's `fsync` is `__generic_file_fsync` followed by a device flush (`blkdev_issue_flush`), and its `write_inode` updates the directory entry set synchronously under the superblock mutex `s_lock` (`fs/exfat`, not in the checkout: probable). The writers take the same `s_lock` for every cluster they allocate (128 KB clusters: about 130 allocations per 16.9 MB frame), so each of the 25 fsyncs per second plus the folder fsync is a short serialisation point and a FLUSH command in the NVMe queue. On a trimmed drive these are sub-millisecond to a few milliseconds each.

Measured answer: the writers have not noticed. Every take with the fsync on and a trimmed drive shows `peak_queue=2/12` (A0 15,001 frames; #78 14,998; #80 15,025), and A1 (fsync off) was also `peak_queue=1/12` with 0 lost; there is no queue-side difference to attribute to the fsync. The 2026-10-30 stack dumps that showed writers waiting in `exfat_write_inode > __wait_on_buffer` were on an untrimmed drive, where every metadata write could take seconds. So: plausible in theory, harmless in practice on a trimmed drive, and not a capture-side mechanism in any case (different thread, no shared lock with libcamera's thread). If anyone wants the number: section 7, M9.

### 1.8 Who runs where (the thread map of one frame)

| Step | Thread | Where |
| --- | --- | --- |
| `requestComplete`: metadata, white balance, phase lock, pre-roll note, `publishPreviewFrame`, `recordRawFrame` (cadence, `metadataFromRequest`, `PendingCopy`, `enqueueCopy`) | libcamera's CameraManager thread (`camera_->requestCompleted.connect(this, &CameraSession::requestComplete)`, `:8630`) | `:8958-9070, 9254-9375` |
| dma-buf sync, 16.9 MB `memcpy` into a warm-pool buffer, Log table, `enqueue` into the write queue, `releaseHeldRequest` → `requeueRequest` → `camera_->queueRequest` | copy worker (1 by default, `APERTAR_RAW_COPY_WORKERS`) | `:5000-5060, 5063-5074, 8603-8608, 8880-8956` |
| `writeDngFile` (one 16.9 MB `write()` for unpacked 16-bit), `startWriteback` (`sync_file_range`), `noteWrittenFile` | writer threads (4 on exFAT, `MediaProfile.hpp:139-141`) | `:5200-5206, 4662-4687` |
| `fsync` + DONTNEED of the files written since the last tick, folder `fsync` | sync thread (`syncLoop`) | `:4689-4718` |
| `buffer` event (queue level, `recording_dropped_frames`), at most every 250 ms | `runBufferEvents` thread | `ApertarCoreApp.cpp:10945-11005` |
| MJPEG encode for the WebUI | `runMjpegEncoder` thread; **the downsample feeding it is on libcamera's thread** when a client is attached | `ApertarCoreApp.cpp:9730-9830, 9833-` |

### 1.9 Small findings on the way

- `MediaProfile.hpp:139-141` gives exFAT `{4, 12, 0, true}` (4 writers, queue 12, no extra raw buffers), with the comment "Cinemate's {2, 16, +2} dropped frames at 16-bit 4K25 on the CFE NVMe (C0106); 4/12 held 10 min (C0101)". The comments at `CameraController.cpp:4274-4276` ("exFAT/NTFS get 2") and `:1452-1454` ("two more buffers of cushion") describe the older table. Default raw buffers for Clear HDR on exFAT: 8 (`:1450-1457`), `maxHeldRequests_` 6 (`:8608`). Confirmed.
- The sync thread waits on the writers' `cv_` with the writers' `mutex_` (`:4691-4692`); `enqueue` wakes one waiter (`:4922`). When both idle writers and the sync thread wait, a third of the wake-ups go to the sync thread, whose predicate (`stopping_`) is false, so it resumes its timed wait and the frame waits for the next `notify_one` (40 ms later) or a writer finishing its job. Pre-existing since the sync thread was added (2026-10-26). At `peak_queue` 2/12 it costs nothing; it may be the reason the peak reads 2 rather than 1. A separate `syncCv_` would remove it (not needed now). Confirmed (code) / probable (effect).
- The journal records neither the DONTNEED mode nor `MEDIA_SYNC_MS` nor `DNG_WRITEBACK` per take (`git grep -i dontneed adac040 -- src` finds only the parse error line and the `=0` warning). The takes table already notes that the journal does not record Core settings. For the interleaved A/B (B1) a `dontneed=sync|writer|off writeback=on|off sync_ms=N` suffix on the existing "recording clip:" line (`:4346-4373`, after `media_fs=` at `:4352`) would make every take self-describing. Three `<<` operators, no new knob.
- `dngPageCacheDrop()` is a process-wide `static` (`CdngEncoder.cpp:85`): a change of the environment needs a Core restart, which the night's `/run` drop-in procedure already does.

## 2. A leaner shape? Recommendation: keep as is

Candidates judged against "least intrusive change consistent with Apertar's existing code (extend an existing knob before adding one)" and against the two things the sync thread is for (pull-safety and, since `adac040`, the drop):

| Shape | Pages leave the cache when | Pull-safety | New work on a hot thread | Verdict |
| --- | --- | --- | --- | --- |
| **As is**: writer `sync_file_range(WRITE)`; sync thread `fsync` + DONTNEED (`adac040`) | about 1-2 s after the write, clean | kept (C0011) | none; 25 fsync + 25 walks/s on the sync thread | **keep** |
| Sync thread: `sync_file_range(WAIT_BEFORE\|WRITE\|WAIT_AFTER)` + DONTNEED, no `fsync` | same | **lost** (C0010: 0-byte files) | none | only as the "no fsync" A/B arm; see below |
| Writer thread: `sync_file_range(WAIT_AFTER)` on the **previous** file, then DONTNEED | about 1 frame after the write | kept (fsync stays) | a writeback wait (tens of ms) on each writer's critical path; cross-writer ordering | no: it spends the writers' slack for nothing the sync thread does not already do |
| Writer thread: DONTNEED after `sync_file_range(WAIT_AFTER)` on its **own** file | right after the write | kept | the writer waits for its own 16.9 MB to reach the drive every frame (about 30-40 ms at 415-550 MB/s): halves the writers' headroom | no |
| `off` plus kernel reclaim (`vm.*` only) | when kswapd gets to them | kept | none | this is the lossy situation today; untested, and the `writer` takes say a full cache under reclaim is the regime to avoid |

The A1 result ("fsync not needed") is about frames, not about data on the card; the fsync stays for C0010/C0011 reasons whatever the drop does. So the only lean variant worth having is the one that makes the knob pair self-consistent: when `APERTAR_MEDIA_SYNC_MS=0` and the mode is `sync`, spawn the thread anyway and do `sync_file_range(fd, 0, 0, SYNC_FILE_RANGE_WAIT_BEFORE | SYNC_FILE_RANGE_WRITE | SYNC_FILE_RANGE_WAIT_AFTER)` in place of `fsync` (the pages are then clean, DONTNEED succeeds, no metadata flush). It is about six lines in `start()`/`syncLoop` (`:4320-4332, 4706`), extends two existing knobs, adds none, and replaces the warning with working behaviour. It is only needed if the test plan wants a "drop without fsync" arm (the A1-style question). Otherwise: keep `adac040` exactly as it is, build it, and spend the effort on the measurements in section 7.

## 3. `64bbbaa` and `6ef0ddc`: anything per frame on the capture thread?

### 3.1 `64bbbaa` (count the take's dropped frames)

`src/util/RecordingDropWarning.hpp` after the commit:

```cpp
    void markDropped(uint64_t frames = 1) {
        if (muted_.load(std::memory_order_acquire))
            return;
        frames_.fetch_add(frames, std::memory_order_acq_rel);
        if (!dropped_.exchange(true, std::memory_order_acq_rel) && changed_)
            changed_(true);
    }
```

- Per **gap event** (not per frame) on the capture thread: one atomic `fetch_add` more than before (`CameraController.cpp:9915`). Nothing per frame. Confirmed.
- The first drop of a take still runs `changed_(true)` on the capture thread, which builds a JSON string with `std::to_string(recordingDropWarning_.droppedFrames())` (`:10353-10358`) and calls `publishEvent` → `controlServer_.broadcast` (`ApertarCoreApp.cpp:14422-14437`, `ControlServer.cpp:175-182`): a synchronous `sendLine` to every socket client under each client's `writeMutex`. Once per take, as before `64bbbaa`; the commit adds one `to_string`. Confirmed.
- The number reaches the UIs through the existing `buffer` event (`ApertarCoreApp.cpp:10945-11005`): its own thread wakes every 250 ms, reads `camera_.recordingDroppedFrames()` (one atomic load) and sends the event when the value changed. While frames are being lost at 2/s that is up to 4 events per second to the touch UI and the HDMI process, each parsed by Qt on the UI side. Not on the capture thread; a small UI-side cost during a losing take only. Confirmed.
- `recording_dropped_frames` in `get_state`, the web state and the record replies are on request only. Confirmed.

### 3.2 `6ef0ddc` (`APERTAR_RT_CAPTURE_PRIORITY`)

`CameraController.cpp:8967-8999` (inside `requestComplete`, once per session):

```cpp
            const int tid = static_cast<int>(::syscall(SYS_gettid));
            const unsigned int rtPriority = unsignedEnvValue("APERTAR_RT_CAPTURE_PRIORITY", 0, 0, 99);
            bool realtime = false;
            if (rtPriority > 0) {
                sched_param param{};
                param.sched_priority = static_cast<int>(rtPriority);
                if (::sched_setscheduler(tid, SCHED_FIFO, &param) == 0) {
                    realtime = true;
                    ...
                } else {
                    std::cerr << "ApertarCore capture scheduling: SCHED_FIFO refused (" << std::strerror(errno)
                              << "); is LimitRTPRIO set on the unit? falling back to nice\n";
                }
            }
            if (!realtime) {
                if (::setpriority(PRIO_PROCESS, static_cast<id_t>(tid), -5) == 0)
```

- **Right thread.** `requestComplete` is the slot connected to `camera_->requestCompleted` (`:8630`), which libcamera emits on its CameraManager thread; `gettid()` there is that thread, and `sched_setscheduler` with a TID acts on that thread alone on Linux. Confirmed.
- **Without `LimitRTPRIO`:** `sched_setscheduler` fails with `EPERM`, the line above is logged, and the old `nice -5` path runs (needs `LimitNICE=-5`, `config/apertar-core-capture-priority.conf:3`; without it `EACCES` and "normal priority retained"). Confirmed.
- `unsignedEnvValue` clamps values above the maximum rather than rejecting them (`:1332-1345`: `std::min<unsigned long>(parsed, maximumValue)`), so `=120` means 99. Cosmetic.
- Per frame: nothing (`capturePriorityAdjusted_` gate). Confirmed.
- What it can and cannot do: SCHED_FIFO makes the thread win the CPU against Core's SCHED_OTHER threads and the UI. It does nothing for a thread that sleeps inside the kernel in direct reclaim (`mm/page_alloc.c:4484-4500`, `__alloc_pages_direct_reclaim` at `:4034-4046` with `psi_memstall_enter`) or in I/O. #22 (FIFO 40: 6.2 % lost against about 7 % at nice -5, night report §3) is therefore consistent with the memory mechanism and against CPU competition from Core's own threads. Probable. A side effect worth knowing for M5: a FIFO thread on a CPU delays that CPU's `mm_percpu_wq` kworker, i.e. the `lru_add_drain_per_cpu` work a writer's `lru_add_drain_all()` waits for (`mm/swap.c:859-870`), so in `writer` mode RT on the capture thread makes the writers' drains slower, not the capture faster.

## 4. The capture-gap accounting

`CameraController.cpp:9873-9926` (called from `recordRawFrame` at `:9314`, on libcamera's thread, for every frame that reaches the recording path):

```cpp
        const int64_t deltaUs = timestampUs - lastRecordingSensorTimestampUs_;
        lastRecordingSensorTimestampUs_ = timestampUs;

        int64_t nominalFrameUs = frameDurationUs;
        if (nominalFrameUs <= 0) {
            const double safeFps = std::max(1.0, settings_.fps);
            nominalFrameUs = static_cast<int64_t>(1000000.0 / safeFps);
        }
        ...
        if (deltaUs > (nominalFrameUs * 3) / 2) {
            const int64_t estimate = (deltaUs + (nominalFrameUs / 2)) / nominalFrameUs - 1;
            if (estimate <= 0)
                return;

            const uint64_t droppedEstimate = static_cast<uint64_t>(estimate);
            recordingGapEstimate_ += droppedEstimate;
            dropWarning_.markDropped(droppedEstimate);
            if (recordingGapEstimate_ == 1 || (recordingGapEstimate_ % 30) == 0 || droppedEstimate > 1) {
                std::cerr << "ApertarCore drop[capture-gap]: +" << droppedEstimate
                          << " frame(s) estimate" << " dt_us=" << deltaUs
                          << " nominal_us=" << nominalFrameUs
                          << " total_estimate=" << recordingGapEstimate_ << "\n";
```

- **What `dt_us` about 80 000 means.** `timestampUs` is libcamera's `SensorTimestamp` (the CSI-2 start-of-frame time stamped by the CFE driver, CLOCK_BOOTTIME) with the buffer timestamp as fallback (`:9300-9304`); `nominalFrameUs` is the frame's own `FrameDuration` metadata normalised to microseconds (`:9306-9310`, `normalizeFrameDurationToUs` at `:3758-3772`), 40 000 at 25 fps. A delta of 80 000 means one sensor period passed with no frame delivered to Core: `(80000 + 20000) / 40000 - 1 = 1`. 120 000 would count 2. The threshold `3/2` means a delta must exceed 60 000 to count at all; SOF timestamps carry microsecond jitter, so a late-but-delivered frame cannot trip it. Confirmed.
- **Can it overstate?** Only when Core itself skips a frame *before* the cadence call and the next frame is tracked: `recordRawFrame` returns before `trackRecordingCadence` when the recorder is inactive, the white balance is invalid (`:9257-9264`), the raw stream info is invalid or unsupported, or the buffer is not mapped (`:9266-9290`). The chain keeps the last timestamp, so the next tracked frame shows a two-period delta and is counted as a capture gap. With AWB metadata on every frame this is rare; it is not what the losing takes show (steady single gaps at 2/s for minutes). The cadence call runs before the capacity check (`:9348-9349`) and before `enqueueCopy`, so a `queue-full` or `copy-slot` drop is **not** double-counted in `dropped_gap_estimate` (it is counted once more in the UI total through `markDropped`, by design: "every kind of drop"). A `requeue-failed` (`:8947-8955`) is counted in `requeue_failures_` and would also appear as a gap; it has been 0 in every take. Confirmed.
- **Can it understate?** Yes, in three places: (a) inside an fps-ramp grace window (`inFpsRampGrace`, `:9653-9657`; `fpsRampGraceFrames` = N + 6 frames of the slower rate, at least 10, `:9631-9640`), where every delta only advances the chain (`:9878-9884`): a real loss during a ramp is invisible. The night's takes ran at a fixed 25 fps (ladder off), so no window was open after the first frames; `noteFpsChange` is called by `applyControls` on every fps change, including the scripts' `set_fps value=25` seconds before `record_start`, and the window is about 14 frames at 25 fps (0.56 s), well before the take. (b) Before the cadence gate opens (`waitingForRecordingCadence_`, `:9052-9064`): frames whose timestamp precedes `recordingStartBootUs_` or whose duration is off by more than 2 % are not recorded and not tracked. (c) A non-monotonic timestamp resets the chain without counting (`:9890-9893`). None of these affects a steady-state 25 fps take. Confirmed.
- **During a reconfigure** the take is not running (`startRecording` resets `recordingGapEstimate_` and the chain at `:7507, 7522`; a reconfigure mid-take is refused by the busy checks), so the counter does not see it. Confirmed.
- **Late requeue (Core) or CFE skip (kernel)?** The journal cannot tell. Both leave the identical two-period hole in the SOF chain. Core's two "its own fault" counters were 0 in every take of the evening: `requeue_failures=0` (every `capture stats` line in `takes-2026-11-01.raw.txt`) and `dropped_copy_slot=0` (every `recording stats` line), i.e. `queueRequest()` never failed and Core never held more than 6 of the 8 requests. What remains is (i) libcamera's own thread not re-queueing in time (the request is handed back to libcamera by the copy worker within a few ms of completion; libcamera queues the buffer to the CFE from its CameraManager thread, the same thread that was found at 40 % of a core and that a stall in reclaim would freeze), or (ii) the CFE/CSI-2 receiver dropping a frame on its own (link errors at 1782 Mbps). Two debug switches separate them: `rp1_cfe` dynamic debug prints "has no buffer, unable to schedule job" at every frame start without a queued buffer, and `LIBCAMERA_LOG_LEVELS=RPI:0` prints libcamera's own frame drops (section 7, M6 and M7). Confirmed (code) / unconfirmed (which one happens).

## 5. What Core allocates per frame on libcamera's thread today

Per frame, with a cDNG take running and no WebUI client (after T25: the copy, the enqueue and the requeue are on the copy worker):

| Site | What | Heap? |
| --- | --- | --- |
| `requestComplete` `:8966` | `std::shared_lock settingsLock` | no |
| white balance, exposure (`:9001-9031`) | metadata `get`s into locals | no |
| `stepFramePhaseLock`, `noteFrameForPreroll` (`:8759`, `:10206-10213`) | atomics, one mutex | no |
| `publishPreviewFrame` (`:9928-10073`) | `frame.fourcc = config.pixelFormat.toString()` ("YUV420": fits the 15-char SSO); `previewCallback_` → `enqueuePreviewFrame` (`ApertarCoreApp.cpp:8175-8225`): descriptor copies, `previewMutex_`, `std::optional` assignment | no in steady state |
| `metadataFromRequest` (`:4033-4060`) | `out.make = "Apertar"` (SSO), `out.model = "Apertar D1"` (SSO), `out.sensorModel = "imx585"` (SSO), **`out.uniqueCameraModel = uniqueCameraModelForSensor()`** returning `"Blackmagic Micro Cinema Camera"` (`:3833-3838`, 30 chars: one malloc), **`out.serial = cachedPiSerial()`** (16 hex chars: one malloc), `out.cameraLabel` ("Apertar D1-xxxx", 15 chars: SSO) | 2 small mallocs |
| `PendingCopy` push into `copyQueue_` (`std::deque<PendingCopy>`, `:4979-4997`) | `PendingCopy` holds a `CdngEncoder::Metadata` (eight `std::string`s and the arrays) and is well over 512 bytes, so libstdc++'s deque allocates one node per element | 1 malloc (probable: `sizeof` not computed) |
| `frameFilename` (ostringstream) and `metadata.frameFileName`/`clipName`/`reelName` | in `enqueue` (`:4902-4908`) | on the **copy** thread |
| `acquireRawBuffer(copy.size)` 16.9 MB | warm pool (`warmRawPool()` at `:4308`, `APERTAR_RAW_POOL_WARM`) | copy thread, no malloc in steady state |
| the stats lines (`:4465-4485`, `:7658-7662`) | at stop only | n/a |
| `drop[capture-gap]` line | first gap, every 30th, or a multi-frame gap: one `write(2)` to stderr/journald | rare |

So about three mallocs and two frees per frame on libcamera's thread, each a few hundred bytes, freed by the copy worker one frame later. glibc serves these from the thread's arena bins without touching the kernel once the arena has warmed up; no new pages, no page faults, so Core's own user-space allocation on that thread cannot enter direct reclaim in steady state. Probable; the thread's `minflt` counter is the one-line check (M8).

What **can** put libcamera's thread into direct reclaim is kernel-side allocation inside the syscalls it makes: V4L2 `QBUF`/`DQBUF`, dma-buf fence and sync ioctls, the eventfd/epoll loop, and libcamera's own `new`/`delete` traffic (`ControlList` copies per request, posted messages for `queueRequest`). Any `GFP_KERNEL` allocation that finds the zone below `WMARK_MIN` takes the slow path and reclaims in the caller's context (`mm/page_alloc.c:4298-4500`; `do_try_to_free_pages` counts it in `allocstall_*`, `mm/vmscan.c:6262-6274`). Slab allocations mostly come from per-CPU slabs and only occasionally need a new page, so the rate is low but the duration of one such stall is unbounded in the tens of milliseconds while kswapd is behind. This is not Core's code and only the per-thread trace (M3) can show whether it happens. Unconfirmed.

**With a WebUI client attached** (`mjpegClientCount_ > 0`), `captureWebPreviewFrame` runs on libcamera's thread for every preview frame up to 30/s (`ApertarCoreApp.cpp:8222-8223, 9730-9830`): rate limit under `mjpegMutex_`, then a nearest-neighbour downsample of three planes into a reused `std::vector<uint8_t>` of 640x360x1.5 = 345,600 bytes (`yuv.resize`, buffer recycled from `pendingMjpegFrame_`/`recycledMjpegYuv_`, `:9793-9798`), then a notify to the MJPEG thread. 0.2-0.5 ms per frame on that thread (README); the first frames of a connection allocate the buffer. The scripts' refusal to run with a client on `:8000` is the right rule; `APERTAR_WEB_PREVIEW_RECORDING_FPS=0` is the knob when a browser must stay open. Confirmed.

## 6. The knobs for the A/B, and the media-tune helper

### 6.1 Defaults at `adac040` and where each is read

| Knob | Default at `adac040` | Range / values | Read at | Notes |
| --- | --- | --- | --- | --- |
| `APERTAR_DNG_DONTNEED` | `sync` | `sync` / `writer` (`1`) / `off` (`0`, `false`); unknown → `sync` + one stderr line | `CdngEncoder.cpp:86` (`dngPageCacheDrop`), used at `CdngEncoder.cpp:1886`, `CameraController.cpp:4324, 4709`, `LossyDngEncoder.cpp:104` | process-wide static; a change needs a Core restart |
| `APERTAR_MEDIA_SYNC_MS` | `1000` | 0 to 60000 (`0` = no sync thread, and no drop under `sync`) | `CameraController.cpp:4320` | `unsignedEnvValue` |
| `APERTAR_DNG_WRITEBACK` | on | `0`/`false`/`no`/`off` turns it off | `CameraController.cpp:4664` (`startWritebackPerFrame`), used at `:5204` | cDNG only; `boolEnvValue` at `:1348` |
| `APERTAR_RAW_CAMERA_BUFFERS` | `min(16, base + extra)`: base 8 (Clear HDR, `kClearHdrBufferCount` `:1329`) or 4; extra 0 on exFAT (`MediaProfile.hpp:139-141`) → **8** on this rig | 3 to 16 | `CameraController.cpp:1456` | `maxHeldRequests_` = buffers − 2 = 6 (`:8608`) |
| `APERTAR_RT_CAPTURE_PRIORITY` | `0` (off) | 1 to 99 (`SCHED_FIFO`); above 99 clamps | `CameraController.cpp:8978` | needs `LimitRTPRIO` (drop-in `config/apertar-core-capture-priority.conf:7` sets 80); falls back to `nice -5` |
| `APERTAR_MEDIA_TUNE` | off | exactly `1` turns it on (`env[0] != '1'` → return) | `ApertarCoreApp.cpp:11360` | runs `sudo -n /usr/local/libexec/apertar-media-tune apply\|restore <rootdisk> <class> <fs>` on mount/unmount of the media root (`:11364-11385`); needs the helper installed (`scripts/apertar-media-tune` → `/usr/local/libexec/`) and `config/apertar-media.sudoers` → `/etc/sudoers.d/` (user `pi`); one journal line when the helper is missing |
| also relevant | | | | |
| `APERTAR_CDNG_QUEUE_FRAMES` | 12 (profile) | 4 to 64 | `:4303-4304` | |
| `APERTAR_CDNG_UNCOMPRESSED_WORKERS` | 4 on exFAT (profile) | 1 to 8 | `:4273-4274` | |
| `APERTAR_RAW_COPY_WORKERS` | 1 | 1 to 2 | `:4341` | |
| `APERTAR_WEB_PREVIEW_RECORDING_FPS` | 30 | 0 to 30 | `ApertarCoreApp.cpp:91` | downsample on libcamera's thread when a client is attached |
| `APERTAR_FPS_RAMP_GRACE_FRAMES` | N + 6, at least 10 | 1 to 200 | `CameraController.cpp:9633` | the grace window that mutes the gap counter after an fps change |

### 6.2 What the helper sets, against the hand `sysctl` of #80

`scripts/apertar-media-tune:73-100` (class `pi-nvme`):

```sh
    pi-nvme)     DIRTY=$((1024*1024*1024)); BG=$((256*1024*1024)); SCHED=none;        NR=512; RQ=2; APST=0 ;;
    ...
        for k in dirty_bytes dirty_background_bytes dirty_ratio dirty_background_ratio dirty_writeback_centisecs dirty_expire_centisecs; do
            save_once "vm_$k" "/proc/sys/vm/$k"
        done
        write_sys "$QUEUE/scheduler" "$SCHED"
        write_sys "$QUEUE/nr_requests" "$NR"
        write_sys "$QUEUE/rq_affinity" "$RQ"
        # the ratios must be 0 before the byte values take effect
        write_sys /proc/sys/vm/dirty_ratio 0
        write_sys /proc/sys/vm/dirty_background_ratio 0
        write_sys /proc/sys/vm/dirty_background_bytes "$BG"
        write_sys /proc/sys/vm/dirty_bytes "$DIRTY"
        write_sys /proc/sys/vm/dirty_writeback_centisecs 150
        write_sys /proc/sys/vm/dirty_expire_centisecs 3000
```

| Knob | Kernel default on the Pi (night report §5) | #80 by hand | helper `pi-nvme` |
| --- | --- | --- | --- |
| `vm.dirty_bytes` / `dirty_ratio` | 0 / 20 % → about 700 MB of dirtyable memory | 1 GiB | 1 GiB (ratios set to 0 first) |
| `vm.dirty_background_bytes` / `_ratio` | 0 / 10 % → about 350 MB | 256 MiB | 256 MiB |
| `vm.dirty_writeback_centisecs` | 500 | unchanged | 150 |
| `vm.dirty_expire_centisecs` | 3000 | unchanged | 3000 |
| `vm.min_free_kbytes` | 16384 (Raspberry Pi OS; the kernel's own formula `int_sqrt(lowmem_kbytes * 16)`, `mm/page_alloc.c:6236-6248`, would give about 8,000) | **65536** | **not set** |
| `/sys/block/nvme0n1/queue/scheduler`, `nr_requests`, `rq_affinity` | none, device default, 1 | unchanged | none, 512, 2 |
| `nvme_core.default_ps_max_latency_us` | boot args already disable APST | unchanged | 0 |

The dirtyable figure: `global_dirtyable_memory()` = free pages − reserves + inactive file + active file (`mm/page-writeback.c:347-366`), and the thresholds are `ratio × available` or the byte values (`:377-440`). On this board with the page cache full that is about 3.3-3.6 GB, so the defaults are about 350 / 700 MB; the hand values are 256 MiB / 1 GiB: the background flusher starts a little earlier, the hard throttle a little later. Neither engages in a clean take: with the per-frame `sync_file_range` the measured peak `Dirty` was 11 MB in A0 and 3 MB in A1 (hardware-log 2026-10-30). `balance_dirty_pages` throttles only the task that dirties (`:2074-2130`, `current->nr_dirtied`), i.e. the writers, and only above the thresholds. So the dirty half of #80 is very probably inert for the frames (it still matters for how much a drive stall can pile up before the writers block, and for a pulled card); `min_free_kbytes` is the memory-side ingredient that is active throughout a take. Probable.

What `min_free_kbytes` does, from `mm/page_alloc.c:6125-6180`: `WMARK_MIN` for each zone is its share of `min_free_kbytes`; `WMARK_LOW = MIN + max(MIN/4, managed × watermark_scale_factor / 10000)` (0.1 % of the zone at the default 10), `WMARK_HIGH = LOW + the same`. On a 4 GB board: 16 MiB → about 16 / 20 / 24 MiB; 64 MiB → about 64 / 80 / 96 MiB (per zone proportionally; exact figures in `/proc/zoneinfo`, M0). kswapd is woken when an allocation finds the zone below LOW and sleeps at HIGH (`mm/vmscan.c:7140-7166`; `kswapd_low_wmark_hit_quickly` counts the times it was re-woken before it could sleep); an allocation that finds the zone below MIN reclaims itself (`mm/page_alloc.c:4484-4500`). The band between LOW and MIN is what kswapd has to work with before allocators start stalling: 4 MiB is about 10 ms of page-cache allocation at 415 MB/s; 16 MiB is about 40 ms. That is the arithmetic behind #80's `kswapd_low_wmark_hit_quickly = 0` and the night report's B3(c). Confirmed (formula) / probable (effect on frames).

### 6.3 Adding `min_free_kbytes` to the helper: the least intrusive shape

One row in each of the three lists of `scripts/apertar-media-tune`, behind the same `APERTAR_MEDIA_TUNE=1`:

- Class table (`:73-77`): a `MINFREE` column, `65536` for `pi-nvme`, `usb-uas`, `usb-storage`, `sd-card` (it is a memory knob, so the same value for every tuned class), empty for `other`.
- `apply` (`:86-88`): add `min_free_kbytes` to the `save_once "vm_$k"` loop, and `write_sys /proc/sys/vm/min_free_kbytes "$MINFREE"` after the dirty lines. Guard for small boards (the sysctl documentation: "Setting this too high will OOM your machine instantly", `Documentation/admin-guide/sysctl/vm.rst:520-533`): `mem_kb=$(awk '/^MemTotal:/{print $2}' /proc/meminfo); [ "$mem_kb" -lt 2000000 ] && MINFREE=$((mem_kb / 64))` (a 512 MB board gets about 8 MiB, close to its default; a 4 GB board keeps 64 MiB, 1.6 % of memory).
- `restore` (`:104-106`): add `min_free_kbytes` to the restore loop (`save_once` keeps the first value seen, so a reboot-less re-apply does not lose the original 16384).
- README row `APERTAR_MEDIA_TUNE` (`README.md:330`): "dirty-page cushion, free-memory floor (`vm.min_free_kbytes`), scheduler, queue depth"; and the helper's header comment table (`scripts/apertar-media-tune:11-17`).

Then install the helper and the sudoers file (the README has the pattern for `apertar-media-trim`, `README.md:303-311`; the tune helper has no install block yet) and `Environment=APERTAR_MEDIA_TUNE=1` in a drop-in. Whether it becomes the default is B3's call. An alternative with one knob instead of raising MIN is `vm.watermark_scale_factor` (e.g. 100 = 1 % → a 38 MiB band without touching the OOM-relevant MIN); it is cleaner in kernel terms but has no CineMate precedent and no measurement yet, so it is a note, not a recommendation.

Two things to correct in the KB on the way: the night report calls the three sysctls "CineMate's dirty limits", but `storage-automount.py:319-336` sets only `vm.dirty_*` and `dirty_writeback/expire_centisecs`; `min_free_kbytes` appears nowhere in cinemate or its handbook. And the hardware-log 2026-11-01 entry's "the once-a-second sync's bound on what a pulled card loses" comment in `ApertarCoreApp.cpp:11357-11359` (why the tune is opt-in) is moot since the per-file fsync: the dirty limits cannot undo a per-file `fsync`.

## 7. Measurements that settle the open points (none can be run from here)

| # | Question | Command (Patrik runs `sudo`) | Read | Meaning |
| --- | --- | --- | --- | --- |
| M0 | page size and exact watermarks | `getconf PAGESIZE; grep -E 'Node|^  *(min|low|high|managed)' /proc/zoneinfo` | the page size; per-zone min/low/high in pages | fixes every page count in this report and in §8 of the night report; the low−min band in MiB is the headroom before direct reclaim |
| M1 | did the `writer` takes run in direct reclaim | copy the `pgscan_direct`, `allocstall_normal`, `allocstall_movable` deltas of #70-#80 from the Mac transcript (`take3.sh` printed them) | `allocstall_* > 0` and `pgscan_direct` in the millions under `writer`, about 0 under `sync` | confirms a standing direct-reclaim regime; says nothing yet about which thread |
| M3 | which thread stalls | during a losing `writer` take: `sudo trace-cmd record -e vmscan:mm_vmscan_direct_reclaim_begin -e vmscan:mm_vmscan_direct_reclaim_end sleep 60; trace-cmd report \| awk '{print $1}' \| sort \| uniq -c` (or `perf trace -e 'vmscan:mm_vmscan_direct_reclaim_*' -a`) | the comm of each stall and begin→end durations | `CameraManager` with stalls of 20 ms or more: the memory regime reaches the capture thread directly. Only writers and `Apertar-UI`: the capture loss comes through the CFE/libcamera side (M6) or the UI's GPU allocations |
| M5 | the drain claim | `sudo perf probe -a lru_add_drain_all; sudo perf stat -e probe:lru_add_drain_all -a sleep 60` during a `writer` take, then a `sync` take | calls per second | about 25/s under `writer`, 0-1/s under `sync` confirms 1.2 and section 1.6; `perf trace -e probe:lru_add_drain_all --duration 1` for call lengths |
| M6 | late requeue or CFE skip | `echo 'module rp1_cfe +p' \| sudo tee /sys/kernel/debug/dynamic_debug/control` for one losing minute; `journalctl -k --since -2min \| grep -c 'no buffer'`; separately one 60 s take with `LIBCAMERA_LOG_LEVELS=RPI:0` in a `/run` drop-in | CFE "has no buffer, unable to schedule job" lines at the gap times; libcamera drop lines | CFE lines present: the buffer was not queued in time (libcamera's thread or Core's copy worker late); absent while gaps count: the receiver lost the frame (link, 1782 Mbps). `rp1_cfe.track_csi2_errors=1` on the cmdline (reboot) adds `/sys/kernel/debug/rp1-cfe*/csi2_errors` |
| M7 | the capture thread's timeline | `tid=$(grep -l CameraManager /proc/$(pidof apertar-core)/task/*/comm \| cut -d/ -f5); sudo perf sched record -p $(pidof apertar-core) sleep 30; sudo perf sched timehist -p $tid` | wait time vs run time per wake-up; 40 ms holes | a hole with wait ≫ run: CPU starvation; a hole with neither: the thread slept in the kernel (reclaim, I/O) |
| M8 | does libcamera's thread page-fault during a take | `tid` as above; `while sleep 1; do awk '{print $10, $12}' /proc/$(pidof apertar-core)/task/$tid/stat; done` during a take | minor/major faults per second | flat: Core's user-space allocation on that thread cannot be entering reclaim (section 5); rising: find the allocator with `perf record -e page-faults -t $tid` |
| M9 | the sync thread's fsync cost on exFAT | `sudo perf trace -e syscalls:sys_enter_fsync,syscalls:sys_exit_fsync --duration 20 -p $(pidof apertar-core)` for 60 s of a take | fsyncs longer than 20 ms, with their tid | only the sync thread's tid appears and rarely: section 1.7 holds; writers appear: they are blocked behind it (then look at `s_lock`) |
| B-lossy | lossy under the default | one 10-minute Lossy 3:1 take, UI on, aids on, `take3v2.sh` style counters | lost per minute, `pgsteal_kswapd`, `allocstall_*` | 0 lost: `off`-like behaviour is acceptable for Lossy + Log; losses: add the in-thread `sync_file_range(WAIT_AFTER)` + DONTNEED to `LossyDngDiskWriter` (section 1.5) |
| B-journal | per-take bookkeeping | after the three-operator addition to the "recording clip:" line (section 1.9) | `dontneed=… writeback=… sync_ms=…` on every take's first line | the takes table can be regenerated with the mode per take |

PSI: `/proc/pressure/memory` would give whole-system memory-stall time per minute, but `arch/arm64/configs/bcm2712_defconfig:17-18` has `CONFIG_PSI=y` and `CONFIG_PSI_DEFAULT_DISABLED=y`: it needs `psi=1` on the cmdline and a reboot.

## 8. Kernel facts used, with lines (rpi-6.12.y @ 5bd564a)

- `mm/fadvise.c:50-63`: advice on a `noop_backing_dev_info` (memfd/shmem) mapping is accepted and ignored. `:71-75`: `len == 0` → `endbyte = LLONG_MAX`. `:113-114`: `POSIX_FADV_DONTNEED` starts with `__filemap_fdatawrite_range(mapping, offset, endbyte, WB_SYNC_NONE)`. `:120-137`: first/last page math; the partial last page is kept only when `endbyte` is not page-aligned and not EOF. `:152`: local `lru_add_drain()`. `:154-155`: `mapping_try_invalidate(..., &nr_failed)`. `:165-168`: `if (nr_failed) { lru_add_drain_all(); invalidate_mapping_pages(...); }`.
- `mm/truncate.c:288-303`: `mapping_evict_folio` returns 0 for dirty, under-writeback or extra-referenced folios. `:497-545`: `mapping_try_invalidate` walks present entries with `find_lock_entries` in `PAGEVEC_SIZE` batches, `deactivate_file_folio` + `nr_failed++` on each failure, `cond_resched()` per batch.
- `mm/swap.c:503-515`: `folio_add_lru` batches new folios per CPU (`folio_batch_add_and_move`). `:686-693`: `deactivate_file_folio`. `:729-735`: `lru_add_drain` (local CPU). `:792-886`: `__lru_add_drain_all`: a mutex, a generation counter so concurrent callers coalesce, `queue_work_on` for every CPU with pending batches, `flush_work` on each.
- `mm/filemap.c:421-432`: `__filemap_fdatawrite_range` builds a `writeback_control` with `nr_to_write = LONG_MAX`.
- `mm/page_alloc.c:320`: `min_free_kbytes` default 1024 before `calculate_min_free_kbytes` (`:6236-6248`, `int_sqrt(lowmem_kbytes * 16)`, clamped 128..262144, user value preferred). `:6125-6180`: `__setup_per_zone_wmarks`: MIN from `min_free_kbytes` per zone; LOW = MIN + `max(MIN/4, managed × watermark_scale_factor / 10000)`; HIGH = LOW + the same. `:4298-4500`: the slow path: `wake_all_kswapds` (`:4381`), then `__alloc_pages_direct_reclaim` (`:4497`; `:4034-4046` with `psi_memstall_enter`).
- `mm/vmscan.c:6262-6274`: `do_try_to_free_pages` counts `ALLOCSTALL` (the `allocstall_*` counters). `:7140-7166`: `kswapd_try_to_sleep`: `KSWAPD_LOW_WMARK_HIT_QUICKLY` when kswapd is re-woken during its short sleep. `:7268-7300`: `wakeup_kswapd`.
- `mm/page-writeback.c:347-366`: `global_dirtyable_memory`. `:377-440`: `domain_dirty_limits` (byte values win over ratios; `bg_thresh` forced below `thresh`). `:2074-2130`: `balance_dirty_pages_ratelimited_flags` throttles `current` after `nr_dirtied` pages.
- `Documentation/admin-guide/sysctl/vm.rst:149-185` (`dirty_*`), `:520-533` (`min_free_kbytes`: "Setting this too high will OOM your machine instantly").
- `arch/arm64/configs/bcm2712_defconfig:17-18`: `CONFIG_PSI=y`, `CONFIG_PSI_DEFAULT_DISABLED=y`.
- Not in the checkout, cited from upstream knowledge and labelled probable above: `fs/sync.c` (`sync_file_range` with `SYNC_FILE_RANGE_WRITE` → `__filemap_fdatawrite_range(..., WB_SYNC_NONE)`; `fsync` accepted on a read-only fd), `fs/exfat/file.c` (`exfat_file_fsync` → `__generic_file_fsync` + `blkdev_issue_flush`), `fs/exfat/inode.c` (`__exfat_write_inode` under `sbi->s_lock`, synchronous dentry-set update on `WB_SYNC_ALL`).

## 9. Code decisions this review supports

| Item | Decision | Why |
| --- | --- | --- |
| `adac040` | build and keep; `writer` stays available through the knob for B1 | the sync-mode drop is correct (1.2); the writer-mode call is confirmed useless-and-costly (1.6) |
| `APERTAR_MEDIA_SYNC_MS` | leave at 1000 | pull-safety (C0010/C0011) needs the per-file fsync regardless of the drop; A1 was about frames only |
| `APERTAR_DNG_WRITEBACK` | leave on | the only per-frame writeback kick in `sync` mode (1.6) |
| "recording clip:" journal line | add `dontneed=… writeback=… sync_ms=…` (three `<<`) | the takes table has no per-take mode today; B1 needs it |
| failed `open()` of the clip folder at `:4321` | one `std::cerr` line | the only silent way to lose the drop (1.3) |
| stale comments `:4274-4276`, `:1452-1454` | fix wording to match `MediaProfile.hpp:139-141` | they say exFAT gets 2 writers and +2 buffers; it gets 4 and +0 |
| lossy under `sync` | test (B-lossy) before changing; if needed, `sync_file_range(WAIT_AFTER)` + DONTNEED in `LossyDngDiskWriter::threadMain` under the same knob | background thread, may wait; no new knob (1.5) |
| MLV at 415 MB/s | not needed for the targets; if ever used, one `startWriteback(job.path)` after `writeFrame` under `APERTAR_DNG_WRITEBACK` | the burst fsync is the C0005 shape (1.4) |
| `apertar-media-tune` | add the `min_free_kbytes` row (6.3), install helper + sudoers, decide the default after B3 | the helper already carries #80's dirty values; the dirty values are very probably inert for the frames; `min_free_kbytes` is the active ingredient |
| hardware-log 2026-10-30 (A1/A2) | a new entry correcting the reading, after Patrik agrees | `a40112a:1780` already had the per-frame DONTNEED; A2 removed a redundant kick (1.6) |
| hardware-log 2026-11-01 / night report wording | "CineMate's dirty limits" → "CineMate's dirty limits plus `min_free_kbytes`" | cinemate does not set `min_free_kbytes` (6.2) |
