# a1-cinepi-writer — THEORY A, part 1: how cinepi-raw writes DNG files to disk

Status: COMPLETE. Reader could not run the camera; every cited line was opened and read.
Repos: cinepi-raw @ 63a08d5 (dev), cinemate @ d6cc93e (dev), cinemate-handbook @ c99ff77.
Cite form: cinepi-raw/<path>:<line>@63a08d5 etc. CONFIRMED unless marked PROBABLE/UNKNOWN.

## Summary (one paragraph)

cinepi-raw never copies a frame on libcamera's completion thread. The main thread only takes a
DMA-buf sync and queues the CompletedRequestPtr plus a raw pointer; one of N encode workers
(Cinemate: 4, pinned to CPUs 1-2) then does the single pass that reads the camera buffer row by
row and writes the finished DNG (header, image, IFD, thumbnail) into one 4096-byte-aligned,
1 MiB-rounded pooled RAM buffer, releases the camera buffer back to libcamera, and hands the RAM
buffer to one of M disk workers (Cinemate: 2 on an NVMe-unknown filesystem, 8 on ext4). The disk
worker opens `O_WRONLY|O_CREAT|O_TRUNC`, gives one `POSIX_FADV_SEQUENTIAL`, does ONE write() of
the exact DNG size, close(), and nothing else: no O_DIRECT, no fsync, no sync_file_range, no
DONTNEED since 2026-03-06. Back-pressure is a RAM permit cap of 90 % of MemAvailable at setup
(~160 frames of 17 MiB on a 4 GB Pi, computed); the encode worker BLOCKS on it, and the main
loop stops recording with "RAM pool exhausted" when 2 permits remain. The writer itself has no
"disk slow" counter; `droppedFrames` is a sensor-timestamp gap counter and `writeFailures`
counts open/short-write/close errors. No MLV anywhere.

## Q1. Open flags of the DNG file

CONFIRMED: `open(filename.c_str(), O_WRONLY | O_CREAT | O_TRUNC, 0644)` — no O_DIRECT, no
O_SYNC/O_DSYNC.
- cinepi-raw/cinepi/dng_encoder.cpp:2351@63a08d5 — comment "Use standard buffered IO instead of O_DIRECT"
- cinepi-raw/cinepi/dng_encoder.cpp:2352@63a08d5 — `O_WRONLY | O_CREAT | O_TRUNC, 0644`
- cinepi-raw/cinepi/dng_encoder.cpp:2356@63a08d5 — `posix_fadvise(fd, 0, 0, POSIX_FADV_SEQUENTIAL)` (the only fadvise in HEAD)
- grep of the whole file for fsync|fdatasync|sync_file_range|ftruncate|fallocate|madvise: no hits (only the fadvise :2356, write :2360, close :2374).

### git history of O_DIRECT (git -C cinepi-raw log -S O_DIRECT -- cinepi/dng_encoder.cpp)
The shallow clone holds 408 commits back to the repo's first commit, so this history is complete
for THIS repository.
- 9748cd0 2025-06-04 21:28:00 +0200 "Initial commit (start fresh)"
- 4c1c66e 2025-07-04 01:48:28 +0200 "dng_encoder: write CinemaDNG FrameRate tag from libcamera metadata if available, else fallback to --framerate"

SURPRISE: both hits are COMMENT text. In 9748cd0 the disk thread ALREADY opened buffered:
`git show 9748cd0:cinepi/dng_encoder.cpp` line 797 "Use standard buffered IO instead of O_DIRECT",
line 798 `O_WRONLY | O_CREAT | O_TRUNC, 0644`, lines 802-803 `POSIX_FADV_SEQUENTIAL` + `POSIX_FADV_NOREUSE`,
line 806 single `write(fd, disk_item.mem_buf, disk_item.size)`, line 810 `close(fd)`. The only other
O_DIRECT string was `#include <sys/mman.h>  // O_DIRECT` (9748cd0 line 26); 4c1c66e's diff deletes just
that include line (diff line 29 `- #include <sys/mman.h> // O_DIRECT`). The compiled encoder never
used O_DIRECT in this repo's lifetime.

The REAL O_DIRECT implementation survives in a dead file, `cinepi/__dng_encoder.cpp` (963 lines),
added f7bc43e 2025-06-10 23:59:00 +0200 "working imx477/585 color but no working wb", deleted
1475f78 2025-06-14 23:23:45 +0200 "fix dual sensor recording". PROBABLE: it is a copy of the
pre-"start fresh" (upstream cinepi-raw) encoder; its own history is outside this repo (UNKNOWN).
What it did (git show f7bc43e:cinepi/__dng_encoder.cpp):
- line 38 `#define BLOCK_SIZE 4096*16` — 64 KiB alignment (HEAD: 4096)
- line 418 `dng_info.buffer_size = ((bytes + ONE_MB - 1) / ONE_MB) * ONE_MB` — 1 MiB rounding
- line 779 `posix_memalign((void **)&buffer, BLOCK_SIZE, dng_info.buffer_size)` — one malloc+free per frame (line 834 `free(buffer)`), no pool
- line 823 `open(filename.c_str(), O_WRONLY | O_CREAT | O_DIRECT, 0644)` — note: NO O_TRUNC
- lines 827-828 `POSIX_FADV_SEQUENTIAL`, `POSIX_FADV_NOREUSE`
- line 829 `write(fd, buffer, dng_info.buffer_size)` — wrote the WHOLE 1 MiB-rounded buffer, padding included (files carried up to 1 MiB of trailing padding)
- line 832 `//ftruncate(fd, memBuf.usedSize);` — commented out, so the padding was never trimmed
- line 833 `close(fd)`
- lines 788-795: image placed at fixed `buffer+1024` after memcpy'd header/offset tables (pack_16bit_to_12bit straight from camera `mem`)

### posix_fadvise history (git log -S on cinepi/dng_encoder.cpp)
- 9748cd0 2025-06-04: SEQUENTIAL + NOREUSE (lines 802-803)
- 0981681 2025-06-23 02:02:49 +0200 "fix flushing of RAM after a take, while writing buffered frames to disk": ADDED `posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);   // drop file pages ASAP` (diff + line; visible as 4c1c66e^ line 836 / 4c1c66e line 844)
- b71ec67 2026-03-06 18:43:41 +0100 "Cache DNG tag strings and streamline disk worker overhead": REMOVED both NOREUSE and DONTNEED (diff lines 170-171) and a per-frame `console->info("Timecode: ...")` (diff line 162). 85 lines changed in dng_encoder.cpp, 6 in the hpp.
=> Since 2026-03-06 cinepi-raw writes through the page cache with NO page-drop hint. (Core at
f60e301 does posix_fadvise(DONTNEED) before close — opposite choice.)

## Q2. Write pattern

All CONFIRMED in diskThread, cinepi-raw/cinepi/dng_encoder.cpp:2314-2403@63a08d5.
- One file per frame. Name: `<mediaDest>/<folder>/<folder>_<index, 9 digits>.dng` (:2337-2341, `oss << options_->mediaDest << '/'` ... `<< ".dng"`).
- Per-frame INFO log BEFORE the open: :2347 `console->info("DNG written: {}", filename)` (spdlog stdout). Cinemate's supervisor regex-scans every stdout line for it: cinemate/src/module/cinepi_multi.py:282@d6cc93e and :332-333 (`_pump`, `dng_rx = re.compile(r'DNG written:...')`). So each frame costs one formatted stdout line in cinepi-raw and one Python regex pass.
- Exactly ONE write() per frame of the whole DNG (header + image + IFDs + thumbnail in one contiguous buffer): :2360 `write(fd, disk_item.mem_buf, disk_item.size)`.
- No partial-write loop: :2361-2362 `write_ok = (bytes_written >= 0 && bytes_written == disk_item.size)`; a short write increments `write_failures_` (:2365) and logs "DNG write FAILED ({}): wrote {} of {} bytes" (:2367); nothing is retried.
- Write length = exact DNG size, not block-aligned: `disk_item.size` is `tiff_size` returned by dng_save, which returns `buf.usedSize` (:2007 `return buf.usedSize;`).
- close() on the same disk worker right after (:2374); a close error is counted only if write looked OK (:2370-2378, comment "close() can surface deferred write-back errors that write() did not report").
- Then: `frames_in_flight_.fetch_sub` (:2389), `releasePooledBuffer` (:2392), RAM permit back `--ram_buffers_` + `ram_cv_.notify_one()` (:2397-2398), debug "Time taken for the disk io" (:2402).
- Buffer alignment: `posix_memalign(..., BLOCK_SIZE, dng_info.buffer_size)` (:2182-2184), `#define BLOCK_SIZE 4096` (:62).
- Buffer size: `frame = ((width * bits + 7) / 8) * height` (:1035); `tail_slack = 64 KiB + log LUT bytes + thumbnail reservation` (:1036-1038); `dng_info.buffer_size = align_up(frame + tail_slack, ONE_MB)` (:1039). Comment :1016-1034: an overflow throws in write_pod and drops the frame "without a pixel of evidence". Thumbnail default: colour at shift 2, ~0.17 MB/frame (:1027-1028).
  Computed illustration (not measured): 3840x2160 16-bit -> frame 16,588,800 B -> buffer 17 MiB (17,825,792 B), write length ~16.8 MB; 12-bit packed -> 12,441,600 B -> buffer 13 MiB.
- The in-memory writer: `struct MemoryBuffer` (cinepi-raw/cinepi/ifd_builder.hpp:165@63a08d5) and `write_pod` (:173-181) = bounds check throwing "MemoryBuffer overflow" (:176) then memcpy.
- No fsync/fdatasync/sync_file_range anywhere; only `POSIX_FADV_SEQUENTIAL` (:2356). The `output/` directory is NOT used for DNG: `Output::Create` returns the vanilla `Output` when `--output` is empty (cinepi-raw/output/output.cpp:102-115@63a08d5, :114 `return new Output(options)`), whose `outputBuffer` is a no-op (:97-100, comment "a vanilla Output gives you an object that outputs no buffers"). It only ever receives the camera pointer via `output_ready_callback_` (dng_encoder.cpp:2305-2308) after the camera buffer has already been released.

## Q3. The RAM pool

- Cap: `max_ram_buffers_ = max(1, 0.90 * MemAvailable / dng_info.buffer_size)`, computed once per setup_encoder from /proc/meminfo (dng_encoder.cpp:1065-1082; :1070 `MemAvailable:`; :1079 `RAM_FRACTION = 0.90`; :1084 log "RAM pool: up to {} frames"). Computed illustration on a 4 GB Pi with ~3 GB available: ~160 x 17 MiB frames ~ 6.4 s at 25 fps. Published to redis key `buffer_size` (cinepi-raw/cinepi/cinepi_controller.cpp:695-696@63a08d5, `maxRamBuffers()`).
- Permits: encode worker BLOCKS until `ram_buffers_ < max_ram_buffers_` (:2174 `ram_cv_.wait`), comment :2167 "RAM back-pressure + aligned allocation". It does not drop. Permit released by the disk worker after close (:2397).
- Pool: `buffer_pool_` is a `std::vector<uint8_t*>` + mutex + `pooled_buffer_size_` (cinepi-raw/cinepi/dng_encoder.hpp:403-405@63a08d5). `acquirePooledBuffer()` (:2407-2432) returns nullptr when the pool is empty (:2426-2427) -> fallback `posix_memalign` at :2182 (a new 4096-aligned buffer; the pool therefore grows lazily to the permit cap, there is no pre-allocation). The pool is flushed (`free`) whenever `pooled_buffer_size_` differs from the current `dng_info.buffer_size` (:2415-2420, :2450-2456). `releasePooledBuffer()` pushes back (:2474). `drainPooledBuffers()` at destruction (:2477-2488, called :316).
- posix_memalign failure: `perror`, permit and `frames_in_flight_` released, `continue` (:2186-2195; comment :2186 "Allocation failed – release the reserved permit; frame is dropped"). No dedicated counter is incremented for this drop.
- dng_save throw: error "dng_save failed for frame {} ... frame dropped" (:2261), same cleanup plus camera-buffer release (:2254-2275).
- Queue bounds: `encode_queue_` (hpp:535) and `disk_buffer_` (hpp:549) are plain `std::queue`, unbounded in code. Encode->disk is bounded only by the permit cap. Main->encode is bounded by the main loop's gate: cinepi-raw/cinepi/cinepi_raw.cpp:442@63a08d5 `if (app.GetEncoder()->buffer_full())` -> `controller.setRecording(false)` and :451 `console->warn("RAM pool exhausted — recording stopped")` (first frame of a new take is let through, :443-450). `buffer_full()` = `ram_buffers_ + 2 >= max_ram_buffers_` (hpp:258-261).
- Counters (hpp:281-292):
  - `dropped_frames_` (hpp:281 "frames with no DNG written (inter-frame gap ≥ 2 periods)") — incremented ONLY at dng_encoder.cpp:2134-2135 from the sensor-timestamp delta of consecutive frames (`raw_elapsed - 1`). It measures frames libcamera never delivered, not writer losses.
  - `write_failures_` (hpp:282) — incremented at :2365 (short write), :2376 (close error), :2382 (open failure).
  - `frames_in_flight_` (hpp:291) — ++ at :480 (EncodeBuffer2), -- at :2188 (alloc fail), :2263 (dng_save throw), :2389 (disk done). Comment hpp:233-237.
  - `buffer_hwm_` (hpp:289) via `noteBufferDepth` (hpp:204, called :2294) = peak `disk_buffer_` depth.
  - Reset per take in `resetFrameCount()` (hpp:141-143); `frames_in_flight_` deliberately not reset (hpp:144-151).
  - Published per frame on the redis stats channel: cinepi_controller.cpp:642-646 (`droppedFrames`, `writeFailures`, `bufferSize`, `bufferSizeMax`, `framesInFlight`); consumed by cinemate/src/module/redis_listener.py:852-854, :870, :880@d6cc93e.
- Architecture note (cinemate-handbook/architecture/cinepi-raw.md:38-46@c99ff77): Cinemate blocks the record trigger while the previous take's RAM buffer drains (`_buffered_frames_flushing()`), the cross-repo interlock behind the comment at cinepi_raw.cpp:414-421 ("Nothing is dropped here ... Cinemate blocks the rec trigger while the green is_writing_buf flush is in progress").

## Q4. Threads

- Defaults: `encode_workers { 2 }`, `disk_workers { 8 }` (cinepi-raw/cinepi/raw_options.hpp:59-60@63a08d5); `encode_affinity`, `disk_affinity`, `encode_nice`, `disk_nice` are std::optional (:61-64).
- Constructor: reads options (dng_encoder.cpp:292-297), `std::max(1, ...)`; no-options fallback 2/8 (:300-301); spawns `encode_worker_count_` x encodeThread and `disk_worker_count_` x diskThread (:303-309); info "DngEncoder started with {} encode worker(s) and {} disk worker(s)" (:311-313). Threads live for the process lifetime (joined in stopThreads :321-353).
- `configureThreadContext()` (:356-441), called first thing in each worker: name `"dng-enc-" + N` (:2015) / `"dng-dsk-" + N` (:2316) via `pthread_setname_np` (:362-366, truncated to 15 chars); audio-core exclusion strips CPU `online_cpus-1` from the requested set when >2 cores (:374-395, comment "cinepi-audio-capture pins itself to the last online core at SCHED_FIFO priority 80"); pin rule: if the safe set has at least as many CPUs as workers, worker i gets ONE CPU `safe[i % n]`, otherwise every worker gets the WHOLE set (:397-404); `pthread_setaffinity_np` (:411); `setpriority(PRIO_PROCESS, 0, nice)` (:432) with warn on failure (:435).
- What Cinemate passes (cinemate/src/module/storage_profiles.py@d6cc93e, `RECORDER_PROFILES` :50; emitted by `recorder_profile_args` :156-171 as `--encode-workers/--disk-workers/--encode-affinity/--disk-affinity/--encode-nice/--disk-nice`; appended in cinepi_multi.py:833):
  - default-safe (:51-60): encode 4, disk 2, encode affinity "1-2", disk affinity "2", nice -10 / -5, buffer_count 8
  - ext4 (:61-72): encode 4, disk 8, encode "1-2", disk "1-2" (comment :66-68: was "2-3", core 3 is the audio core), nice -10 / -5, buffer_count 8
  - exfat (:74-82): 4 / 2 / "1-2" / "2" / -10 / -5 / buffer_count 10
  - ntfs (:84-93): 4 / 2 / "1-2" / "2" / -10 / -5 / buffer_count 10
  - Pi 4 only: disk workers capped at `PI4_MAX_DISK_WORKERS = 4` (:153, :158-163).
  - `--buffer-count` (cinepi_multi.py:845-866; :866 `args += ["--buffer-count", ...]`) -> rpicam_app.cpp:630 default `cfg.bufferCount = 6`, :631-632 override, :657 raw stream takes the same count.
  - Resulting placement with 4 encode workers on "1-2": safe set {1,2} (2 CPUs) < 4 workers -> all four encode workers share the {1,2} mask (:401-404). 2 disk workers on "2" -> both pinned to CPU 2; ext4's 8 disk workers on "1-2" -> all on {1,2}. CPU 0 (all RP1 IRQs) and CPU 3 (audio) are never used by DNG workers.
- Nice is NOT effective on the rig: cinemate-handbook/open-threads.md:340-347@c99ff77 "DNG disk workers cannot set their nice level — deferred 2026-09-22": every take logs `dng-dsk-N: failed to set nice level -5: Permission denied` (:342); cause: service runs as `pi`, needs `RLIMIT_NICE` or `CAP_SYS_NICE` (:352-353). PROBABLE: the encode workers' -10 fails the same way (same syscall, same user; the entry names only the disk workers).

## Q5. Hand-off: who copies the camera buffer, and when libcamera gets it back

Frame path, in order:
1. libcamera completion thread: `RPiCamApp::requestComplete` (cinepi-raw/core/rpicam_app.cpp:1212@63a08d5) wraps the request in a `CompletedRequestPtr` whose deleter is `this->queueRequest(cr)` (:1238) and calls `post_processor_.Process(payload)` (:1255).
2. `PostProcessor::Process` spawns a DETACHED THREAD PER REQUEST for the stages (cinepi-raw/core/post_processor.cpp:136@63a08d5 `.detach()`); the ordered output thread then calls the app callback (:165) which posts `MsgType::RequestComplete` to the main-loop queue (rpicam_app.cpp:255).
   The only stage cinepi-raw inserts is `ccmpPreview` (cinepi_raw.cpp:59 `EnsureFirstPostProcessingStage("ccmpPreview")`). It reads the RAW buffer on that detached thread: gate = ClearHDR ON and (12-bit, or 16-bit linear) (cinepi-raw/cinepi/ccmpPreviewStage.cpp:253-269@63a08d5); `BufferReadSync rr` on raw and `BufferWriteSync lw` on lores (:554-555); in 16-bit it samples row PAIRS from the raw frame for the clamp measurement (`measureClamp` :451, loop :456-461, budget `kSamplesPerFrame = 65536` :207) and then `correctHighlightsInPlace(raw, lores)` (:607); in 12-bit it does a full software `render(raw, lores)` from the raw Bayer (:609). Comments :595-604 ("ONE RENDER PER FRAME ... a second full-frame render ... dropped frames at 4K") and :178-182 ("confirmed on the rig 2026-09-15, 208 drop events") document the September drops the task statement cites. Serialised by a stage mutex (:158-166, "~3 ms against a 20-40 ms frame period"). It logs per-stage cost every 120 frames ("ccmpPreview: cost/frame — ..." :655).
3. Main thread (event_loop): `controller.process(completed_request)` (cinepi_raw.cpp:408) reads metadata only (cinepi_controller.cpp:581-583, `CinePIFrameInfo info(completed_request->metadata)`; no buffer access in that file) and publishes a JSON stats message + redis pipeline per frame (:690-699). Then `app.EncodeBuffer(...)` (:454), then `app.ShowPreview(completed_request, app.LoresStream())` (:462).
4. `CinePIRecorder::EncodeBuffer` (cinepi-raw/cinepi/cinepi_recorder.hpp:49-106@63a08d5): `BufferWriteSync w` on the raw buffer (:68) = `DMA_BUF_IOCTL_SYNC` START|RW on entry and END|RW when `w` leaves scope at the end of EncodeBuffer (cinepi-raw/core/buffer_sync.cpp:19-29, :39-47@63a08d5) — i.e. the cache sync is done on the main thread BEFORE the encode worker reads the buffer, and `BufferReadSync` is a no-op (:54-72). Lores via `BufferReadSync r2` (:71-76). Logs `"Frame Drop!!!!!"` at LOG(1) when measured fps deviates >1 from the setting (:95-96). Pushes the CompletedRequestPtr into `encode_buffer_queue_` (:101-104, "creates a new reference") and calls `EncodeBuffer2` with the raw pointer (:105).
5. `DngEncoder::EncodeBuffer2` (dng_encoder.cpp:455-483) only builds an `EncodeItem` {mem, size, info, lomem, losize, loinfo, metadata, timestamp, index, folder, tc, ceiling_gen} and pushes it to `encode_queue_` (:462-481). NO pixel copy on the main thread or on libcamera's thread.
6. Encode worker (`dng-enc-N`): takes the item (:2025-2034), TC bookkeeping under the mutex (:2039-2138), waits for a RAM permit (:2174), gets a pooled or fresh aligned buffer (:2178-2184), optionally waits <=2 s for the take's WhiteLevel (:2212-2230), then `dng_save(num, mem_buf, encode_item.mem, ...)` (:2232-2243). The copy IS the DNG assembly, one pass: header written first (:1136-1140), then every row is read from the camera buffer and written straight into the pool buffer: 16-bit "copy verbatim, one active row each" (:1425-1433, `write_pod(buf, raw + y * info.stride, rowBytes)`), 12-bit unpacked -> `pack_row_12bit` (:1350-1376), PiSP COMP1 -> `unpack_pisp_comp1_row_*` (:1264-1308), CineMate Log -> LUT + pack (:1226-1263); first frame of a take also samples every 3rd row for the ClearHDR clamp inside the same loop (:1142-1163, :1198-1206). IFDs follow (:1579-1748), thumbnail from the lores buffer (:1844-1978), `return buf.usedSize` (:2007).
7. Right after dng_save the worker pushes the `DiskItem` (:2280-2295) and THEN releases the camera buffer: `input_done_callback_(nullptr)` (:2304) -> `encodeBufferDone` (cinepi_recorder.hpp:158-174) pops the FRONT CompletedRequestPtr (:172 "drop shared_ptr reference") -> deleter `queueRequest` re-queues the request to libcamera (rpicam_app.cpp:1238). So libcamera gets the raw buffer back after one encode (~ one DNG assembly), independent of disk I/O. `output_ready_callback_` (:2305-2308) then goes to the no-op vanilla Output (see Q2).
   PROBABLE hazard (source inference, not observed): `encodeBufferDone` pops the queue FRONT regardless of which frame finished (comment :160-163 "we're just assuming everything is done in order"). With 4 encode workers, a later frame finishing first returns the EARLIER frame's camera buffer to libcamera while another worker may still be reading it. With 8 raw buffers the re-queued buffer is refilled ~8 frames later, so the window is normally not hit, but it is not protected.
8. Disk worker (`dng-dsk-N`): open/fadvise/write/close as in Q1-Q2, then permit back. The camera buffer is not involved.

What else touches the camera buffer before the encode worker: the ccmpPreview stage (step 2, only in ClearHDR 12-bit/16-bit modes), the DMA-buf sync ioctls (step 4), and nothing else — the controller reads metadata only and ShowPreview uses the lores stream (cinepi_raw.cpp:462).

## Q6. Comments/log strings about disk-slow drops; MLV

MLV: CONFIRMED none — `grep -rn -i -E '\bMLV\b|magic lantern|\.mlv'` over cinepi-raw *.cpp/*.hpp/*.md/meson.build (third_party excluded) returns nothing; the only container is per-frame CinemaDNG.

Strings and comments that exist:
- dng_encoder.cpp:2367 "DNG write FAILED ({}): wrote {} of {} bytes - {}"; :2377 "DNG write FAILED on close ({})"; :2384 "DNG write FAILED to open ({})"; :2261 "dng_save failed for frame {}: {} — frame dropped".
- dng_encoder.hpp:222-227: "a storage device that cannot keep up — e.g. NTFS under sustained 4K — loses frames here with NO inter-frame sensor gap, so this is the only live signal for write-stage data loss" (about `getWriteFailures`).
- cinepi_raw.cpp:451 "RAM pool exhausted — recording stopped"; :414-421 comment that nothing is dropped at take start because Cinemate gates on the flush.
- cinepi_recorder.hpp:96 "Frame Drop!!!!!     FPS measured: ... FPS settings: ..." (sensor-timing based).
- Debug-level per-frame timings: "Time taken for the encode: {} ms, disk queue:{}  Size:{}" (dng_encoder.cpp:2300-2301) and "Time taken for the disk io: {} milliseconds" (:2402).
- ccmpPreviewStage.cpp:178-182 (208 drop events on 2026-09-15 from the first clamp-measurement pass), :595-604 (second full-frame render dropped frames at 4K), :655 cost/frame report including delivered fps ("if it reads 22 against a requested 25, three frames a second are going missing somewhere" :644-648).
- Cinemate side: storage_profiles.py:9-14 (NTFS "fail or short-write under sustained 4K DNG throughput ... losing frames at the write() syscall with no inter-frame timing gap"), :33-37 ("More buffers absorb transient disk-write latency spikes that would otherwise starve the sensor and drop a frame"); cinepi_multi.py:836-839 ("visible as a one-tick hole in the DNG timecode").
- Handbook: open-threads.md:340-356 (disk nice EPERM, untested whether it costs throughput).
There is NO code path that drops a frame because the disk is slow: slowness turns into RAM-pool growth (`bufferSize`/`bufferSizeMax`), then a blocked encode worker, then the main loop's "RAM pool exhausted" stop. The writer has no timeout and no per-frame deadline.

## Numbers collected
- open flags: O_WRONLY|O_CREAT|O_TRUNC 0644; fadvise SEQUENTIAL only (since 2026-03-06; DONTNEED existed 2025-06-23..2026-03-06; NOREUSE 2025-06-04..2026-03-06).
- dead O_DIRECT version (f7bc43e, 2025-06-10..06-14): BLOCK_SIZE 4096*16, write of the full 1 MiB-rounded buffer, ftruncate commented out, no O_TRUNC.
- BLOCK_SIZE 4096; buffer_size = align_up(frame + 64 KiB + LUT + thumb, 1 MiB); one write() of usedSize.
- RAM cap 0.90 x MemAvailable / buffer_size; buffer_full at cap-2; encode blocks on permits.
- Workers: defaults 2 encode / 8 disk; Cinemate 4 encode / 2 disk (default, exfat, ntfs) or 4 / 8 (ext4); affinity encode 1-2, disk 2 or 1-2; nice -10 / -5 (EPERM on the rig); Pi 4 disk cap 4; --buffer-count 8 (ext4/default) or 10 (exfat/ntfs); rpicam default 6.
- ccmpPreview: ~3 ms/frame (comment), 65536 samples/frame clamp budget, verdict every 16 frames; 208 drop events 2026-09-15 before the fix.
- WhiteLevel wait bound 2 s (:2214-2216); clamp sampling every 3rd row on the first frame of a take.

## UNKNOWN
- Whether upstream cinepi-raw (before 2025-06-04) shipped O_DIRECT in its compiled encoder: not in this repo's history; only the dead `__dng_encoder.cpp` copy shows it.
- Whether `--encode-nice -10` also fails with EPERM on the rig (PROBABLE yes; handbook names only dng-dsk-N).
- Which Cinemate profile applies to /media/RAW on the Pi (depends on the mounted filesystem; ext4 -> 8 disk workers, otherwise 2).
- Whether the out-of-order camera-buffer release in step 7 of Q5 ever bites on hardware.

## Verification

Adversarial verifier pass (same repos/commits: cinepi-raw 63a08d5, cinemate d6cc93e, cinemate-handbook c99ff77). Every cited line below was re-opened with sed -n / awk on the checkout at the stated commit (or git show <commit>:<path>). Verdicts: CONFIRMED / CORRECTED / REFUTED / UNVERIFIABLE. Written incrementally; see the end for the summary table.

### Pass 1: dng_encoder.cpp HEAD disk-thread and pool lines
- :62 `#define BLOCK_SIZE 4096` CONFIRMED.
- :1027-1028 thumb_reserved_bytes / thumbnail_geometry(...).bytes CONFIRMED.
- :1035 frame formula, :1036-1038 tail_slack = 64*1024 + LUT + thumb, :1039 align_up(frame + tail_slack, ONE_MB) CONFIRMED.
- :1070 "MemAvailable:" CONFIRMED; :1079 `RAM_FRACTION = 0.90` CONFIRMED.
- :2007 `return buf.usedSize;` CONFIRMED.
- :2015 dng-enc- / :2316 dng-dsk- configureThreadContext CONFIRMED.
- :2135 `dropped_frames_ += raw_elapsed - 1;` CONFIRMED.
- :2167 "RAM back-pressure + aligned allocation" CONFIRMED; :2174 ram_cv_.wait predicate CONFIRMED.
- :2182 posix_memalign: the call spans :2182-2184 (`BLOCK_SIZE,` is on :2183). CONFIRMED as :2182-2184.
- :2186-2195 alloc failure: perror, frames_in_flight_ fetch_sub, permit release, notify, continue CONFIRMED (no counter).
- :2214-2216 "WhiteLevel wait bound 2 s": CORRECTED. Those lines are comment text; the bound itself is `clip_ceiling_cv_.wait_for(lk, std::chrono::seconds(2), ...)` at :2222 (predicate :2223-2224).
- :2232-2243 "dng_save call": CORRECTED. :2232-2233 is the ceiling.white take-over; the dng_save(...) call is :2239-2250.
- :2261 "dng_save failed for frame {} ... frame dropped" CONFIRMED; :2263 frames_in_flight_ fetch_sub CONFIRMED.
- :2293 disk_buffer_.push CONFIRMED; :2300-2301 encode timing debug CONFIRMED; :2304 input_done_callback_(nullptr) CONFIRMED; :2305-2308 output_ready_callback_ CONFIRMED.
- :2337-2341 filename composition CONFIRMED; :2347 "DNG written: {}" info BEFORE the open at :2352 CONFIRMED.
- :2351 comment / :2352 open flags / :2356 POSIX_FADV_SEQUENTIAL / :2360 write CONFIRMED.
- :2361 "bytes_written == disk_item.size": CORRECTED to :2361-2362 (the `== disk_item.size` fragment is on :2362).
- :2365 write_failures_ (short write), :2367 "DNG write FAILED ({}): wrote {} of {} bytes - {}", :2370 close comment, :2374 `if (close(fd) != 0 && write_ok)`, :2376, :2377-2378, :2382, :2384 CONFIRMED.
- :2389 frames_in_flight_ fetch_sub CONFIRMED.
- :2402 "Time taken for the disk io": CORRECTED to :2403 (:2402 is the duration computation).

### Pass 2: history, hpp, recorder, main loop, controller, Cinemate, handbook
- grep -n of dng_encoder.cpp@63a08d5 for fsync|fdatasync|sync_file_range|ftruncate|fallocate|madvise|fadvise|O_DIRECT|O_SYNC|O_DSYNC|open(|write(|close(: hits only :2351 (comment), :2352 open, :2356 fadvise, :2360 write, :2370 (comment), :2374 close. Finding 1 CONFIRMED (one fadvise in the whole file: grep -c fadvise = 1).
- git rev-list --count HEAD = 408; oldest commit 9748cd0 2025-06-04 21:28:00 +0200 "Initial commit (start fresh)". CONFIRMED.
- git log -S O_DIRECT -- cinepi/dng_encoder.cpp: exactly 4c1c66e (2025-07-04 01:48:28 +0200, "dng_encoder: write CinemaDNG FrameRate tag ...") and 9748cd0. CONFIRMED. 4c1c66e stat for the file: 20 insertions / 12 deletions CONFIRMED; its diff removes only `#include <sys/mman.h> // O_DIRECT` (diff line 29). CONFIRMED.
- 9748cd0:cinepi/dng_encoder.cpp :26 include comment, :797 "Use standard buffered IO instead of O_DIRECT", :798 O_WRONLY|O_CREAT|O_TRUNC 0644, :802 SEQUENTIAL, :803 NOREUSE, :806 single write, :810 close. ALL CONFIRMED. git show 9748cd0 | grep -n O_DIRECT gives only :26 and :797 — both comments. Finding 2 CONFIRMED.
- f7bc43e (2025-06-10 23:59:00 +0200 "working imx477/585 color but no working wb") adds cinepi/__dng_encoder.cpp, 963 insertions. :38 `#define BLOCK_SIZE 4096*16`, :418 1 MiB rounding, :779 posix_memalign(BLOCK_SIZE, buffer_size), :823 `O_WRONLY | O_CREAT | O_DIRECT, 0644` (no O_TRUNC), :827-828 SEQUENTIAL+NOREUSE, :829 write of dng_info.buffer_size, :832 `//ftruncate(fd, memBuf.usedSize);`, :833 close, :834 free(buffer). ALL CONFIRMED. 1475f78 2025-06-14 23:23:45 +0200 "fix dual sensor recording" deletes __dng_encoder.cpp (963-) and __dng_encoder.hpp (163-). CONFIRMED. Finding 3 CONFIRMED.
- git log -S POSIX_FADV_DONTNEED: b71ec67 (2026-03-06 18:43:41 +0100) and 0981681 (2025-06-23 02:02:49 +0200, "fix flushing of RAM after a take, while writing buffered frames to disk"). git log -S POSIX_FADV_NOREUSE: b71ec67 and 9748cd0. CONFIRMED. 4c1c66e:cinepi/dng_encoder.cpp:844 `POSIX_FADV_DONTNEED ... // drop file pages ASAP` CONFIRMED. 0981681 diff adds DONTNEED at diff line 170; b71ec67 diff removes NOREUSE and DONTNEED at diff lines 170-171 and the per-frame "Timecode: {}" info at diff line 162. CONFIRMED.
  - CORRECTED numbers: per-file stat of 0981681 for cinepi/dng_encoder.cpp is 72+/37- (reader: 79+/41-); b71ec67 for cinepi/dng_encoder.cpp is 37+/48- (reader: 42+/49-). (Whole-commit totals checked below.)
- dng_encoder.hpp :141-143 per-take reset of dropped_frames_/write_failures_/buffer_hwm_, :144-151 frames_in_flight_ intentionally not reset, :204 noteBufferDepth, :226 NTFS comment, :261 `ram_buffers_ + 2 >= max_ram_buffers_`, :281, :282, :291 counters, :535 `std::queue<EncodeItem> encode_queue_;`, :549 `std::queue<DiskItem> disk_buffer_;`. ALL CONFIRMED.
- cinepi_recorder.hpp :68 BufferWriteSync, :96 "Frame Drop!!!!!     FPS measured:", :103 encode_buffer_queue_.push, :105 EncodeBuffer2(...), :161 "assuming everything is done in order", :172 pop. ALL CONFIRMED.
- cinepi_raw.cpp :414 comment, :442 buffer_full(), :451 "RAM pool exhausted — recording stopped", :462 ShowPreview(lores). CONFIRMED. Nuance the reader omitted: the stop fires only when `!justStarted` (:448); the first frame of a new take is let through even with a full pool (:444-447).
  - :59 REFUTED as cited: line 59 is `app.StartEncoder();`, not `app.EnsureFirstPostProcessingStage("ccmpPreview");` (true location found below).
- cinepi_controller.cpp :583 CinePIFrameInfo(metadata), :642 droppedFrames, :646 framesInFlight, :690-699 redis pipeline (publish stats + set ts/tc + buffer_size at :695-696). CONFIRMED.
- raw_options.hpp :59 encode_workers{2}, :60 disk_workers{8}. CONFIRMED.
- dng_encoder.cpp :301-302 defaults 2/8 fallback; spawn loops are :305-311 (reader: :303-309; CORRECTED). :377 SCHED_FIFO 80 comment, :397-404 pin rule (size >= total -> index % size, else whole set), :411 pthread_setaffinity_np, :432 setpriority, :435 "failed to set nice level {}: {}". CONFIRMED.
- :479-480 encode_queue_.push + frames_in_flight_ fetch_add (reader cited :480 for both; the push is :479). CORRECTED to :479-480.
- core/rpicam_app.cpp :255, :630 "6 buffers is better than 4", :657, :1238, :1255; core/buffer_sync.cpp :20 START|RW; core/post_processor.cpp :136 detached thread; output/output.cpp :97-100 no-op outputBuffer, :102-115 Create. ALL CONFIRMED.
- ifd_builder.hpp :173 write_pod, :175-176 overflow throw. CONFIRMED.
- ccmpPreviewStage.cpp :158, :163 "~3 ms against a 20-40 ms frame period", :182 "208 drop events", :207 kSamplesPerFrame 65536, :208 kAccumulations 16, :265, :456, :554 BufferReadSync, :602, :607, :609, :655 cost/frame, :642-644 "22 against a requested 25". ALL CONFIRMED.
- cinemate storage_profiles.py :8-15 NTFS comment (:10 quote exact), :33-37 buffer_count comment (:34 quote exact), :50 RECORDER_PROFILES, default :51-60, ext4 :61-73, exfat :74-83, ntfs :84-94 (reader's ranges off by one at the closing brace; values 4/2/"1-2"/"2"/-10/-5/8, 4/8/"1-2"/"1-2"/-10/-5/8, 4/2/"1-2"/"2"/-10/-5/10, 4/2/"1-2"/"2"/-10/-5/10 ALL CONFIRMED), :153 PI4_MAX_DISK_WORKERS = 4, :156 recorder_profile_args. CONFIRMED.
- cinemate cinepi_multi.py :282 and :333 dng_rx regex, :836-839 "one-tick hole" comment (:838 exact), :866 --buffer-count. CONFIRMED. redis_listener.py :880 writeFailures. CONFIRMED.
- cinemate-handbook open-threads.md :340 heading, :342 log line, :352-353 "runs as `pi` ... needs `RLIMIT_NICE` or `CAP_SYS_NICE`" (reader cited :353; the quote is on :353). CONFIRMED. architecture/cinepi-raw.md :44 CONFIRMED.

### Pass 3: mechanisms behind the claims
- RAM cap: dng_encoder.cpp:1064 comment "Dynamic RAM limit: 90 % of current MemAvailable"; :1066-1077 parse /proc/meminfo MemAvailable (kB -> bytes); :1080-1082 `max_ram_buffers_ = std::max<size_t>(1, RAM_FRACTION * memAvail / dng_info.buffer_size)` inside setup_encoder (so once per encoder setup); :1084 info "RAM pool: up to {} frames (~{} MB)". Finding 7 formula CONFIRMED.
- Permit then pool: :2173-2175 wait for permit and ++ram_buffers_; :2178 `acquirePooledBuffer()`; :2180-2184 posix_memalign fallback when it returns nullptr. CONFIRMED (lazy growth).
- EncodeItem :465-478 stores the raw pointer `mem` (and `lomem`), no copy, on the caller's (main) thread. :479 push, :480 frames_in_flight_ ++. CONFIRMED.
- dropped_frames_ has exactly one increment site in the whole encoder: dng_encoder.cpp:2135 (inside encodeThread, which starts :2013). hpp:141 reset, :221 getter, :281 decl. Finding 8 CONFIRMED.
- Pixel paths: :1236 unpack_pisp_comp1_row_to_16, :1241 unpack_csi2_raw12, :1259 pack_row_12bit (log/LUT path), :1274 unpack_pisp_comp1_row_to_packed12 (COMP1 -> packed12), :1425-1432 16-bit verbatim row copy via write_pod. Finding 11's path names CONFIRMED (section ranges are approximate anchors).
- ClearHDR clamp sampling on the measuring frame: :1154-1155 "Sampling every 3rd row alternates Bayer phase", :1167 `constexpr unsigned kRowStride = 3;`. Reader's ":1142-1163" is the comment block; the constant is :1167. CONFIRMED (anchor widened).
- DMA-buf sync: core/buffer_sync.cpp:20 START|RW in the BufferWriteSync ctor, :39-42 `~BufferWriteSync()` END|RW. The sync object `w` is a local of CinePIRecorder::EncodeBuffer (cinepi_recorder.hpp:68), so START and END both happen on the MAIN thread before EncodeBuffer returns; the encode worker reads the camera buffer AFTER the END sync. Reader's "START|RW then END|RW within EncodeBuffer" CONFIRMED.
- input_done_callback_ is bound to CinePIRecorder::encodeBufferDone at cinepi_recorder.hpp:42. Call sites in dng_encoder.cpp: :450 (older EncodeBuffer path), :2272 (dng_save throw path, releases the camera buffer on failure), :2304 (normal path after disk_buffer_.push at :2293). CONFIRMED: the camera buffer is released before any disk I/O.
- ccmpPreview gating: ccmpPreviewStage.cpp:263 `linear = bit_depth == 16`; :264-266 returns unless hdr is "sensor"/"auto" AND bit depth is 12 or 16; :385 `measure_ = linear;` so 16-bit -> :607 correctHighlightsInPlace, 12-bit -> :609 render. Finding 12 mechanism CONFIRMED. Registration: cinepi_raw.cpp:57 `app.EnsureFirstPostProcessingStage("ccmpPreview");` (reader cited :59 = `app.StartEncoder();` — CORRECTED to :57).
- cinepi_controller.cpp: grep for buffers[/Mmap/mapped_buffers/BufferReadSync/BufferWriteSync returns nothing; the controller never touches pixel buffers. "controller reads metadata only" CONFIRMED.
- Whole-commit stats: 0981681 = 79+/41- over 3 files (dng_encoder.cpp alone 72+/37-); b71ec67 = 42+/49- over 2 files (dng_encoder.cpp alone 37+/48-). The reader's numbers are the whole-commit totals; the label "dng_encoder.cpp 42+/49-" is wrong for the file. CORRECTED (minor).
- f7bc43e __dng_encoder.cpp: `pack_16bit_to_12bit((uint16_t*)mem, (uint8_t*)buffer+1024, ...)` is at :819, not ":788-795" as the reader's markdown says (:788-806 are the header/IFD memcpy's). CORRECTED (markdown-only claim).
- cinemate storage_profiles.py:156-171 recorder_profile_args emits --encode-workers/--disk-workers/--encode-affinity/--disk-affinity/--encode-nice/--disk-nice; :159-163 Pi 4 cap min(disk_workers, 4). CONFIRMED. cinepi_multi.py:845 buffer_count from profile (default 8), :849-853 override from settings `sensors.raw_buffer_count` (the comment at :841 says camera.raw_buffer_count; the code reads the `sensors` key), :866 --buffer-count. CONFIRMED.

### Pass 4: numbers recomputed, open questions settled
- Thumbnail reservation (reader: "default thumbnail colour at shift 2 ~0.17 MB/frame"): CORRECTED.
  - dng_thumbnail.hpp:85-99@63a08d5 `thumbnail_geometry`: width = lores_w >> shift, height = lores_h >> shift, spp = 3 for modes 2/3 else 1, bytes = 0 for mode 0 else w*h*spp (:98); mode 3 (JPEG) reserves the UNCOMPRESSED byte count on purpose (:92-97).
  - cinepi-raw's own defaults: raw_options.hpp:38-39 `thumbnail{}` / `thumbnailSize{}` = 0/0 -> mode 0 -> 0 bytes reserved; the values arrive live from redis keys "thumbnail"/"thumbnail_size" (cinepi_state.hpp:39-40; cinepi_controller.cpp:443, :1055 clamp 0..12).
  - Cinemate's shipped defaults: config_loader.py:398-400 thumbnail default 3 ("jpeg"), :403-412 thumbnail_size default 1 ("half the lores plane, 640x360 from a 1280-wide one"); :414 "691,200 B/frame" at that default; :416 the quarter-size default "shift 2, 172,800 B" had shipped earlier and was replaced by the 2026-09-13 operator decision; :385 JPEG is "roughly 16 KB/frame" actual. settings.jsonc:408 `"thumbnail": "jpeg"`; resources/settings/settings_default.jsonc:183 "jpeg", :186 `"thumbnail_size": 1`. Lores 1280x720 is PROBABLE (sensor_detect.py:176 comment "full lores (~1280x720)"; cinepi_multi.py:617 takes lw/lh from the geometry table).
  - Recomputed buffer_size (align_up(frame + 65,536 + LUT + thumb, 1 MiB), LUT = 0 unless a log LUT is active):
    - 4K 16-bit, Cinemate defaults: 16,588,800 + 65,536 + 691,200 = 17,345,536 -> 17 MiB (17,825,792 B). cinepi-raw defaults (no thumb): 16,654,336 -> 16 MiB (16,777,216 B). Reader's "17 MiB" holds only with Cinemate's thumbnail.
    - 4K 12-bit packed, Cinemate defaults: 12,441,600 + 65,536 + 691,200 = 13,198,336 -> 13 MiB (13,631,488 B); no thumb: 12,507,136 -> 12 MiB (12,582,912 B).
    - Bytes actually written per 4K 16-bit DNG with the JPEG thumbnail: frame 16,588,800 + tags + ~16 KB JPEG ~ 16.6 MB (reader's ~16.8 MB assumed the 172,800 B uncompressed thumb).
  - RAM cap illustration: 0.90 x 3 GiB / 17 MiB = 162 frames (reader "~160": fine as an illustration; MemAvailable on the rig is UNKNOWN). cinepi-raw logs the real number per setup: dng_encoder.cpp:1084 "RAM pool: up to {} frames (~{} MB)".
- Which storage profile applies on the rig (reader: UNKNOWN): PROBABLE exfat or ntfs profile, NOT ext4. cinemate-handbook lessons/hardware-log.md:571@c99ff77 (under the 2026-08-26 entry, :563) "477 GB NVMe, still NTFS from the previous session's format test"; :967 (under 2026-08-27/28, :945) "`/media/RAW` is NTFS via `fuseblk` on NVMe"; :1068 and :1109 (under the two 2026-08-31 entries, :1065/:1106) "exFAT NVMe at `/media/RAW`"; :3101-3102 (2026-09-15 entry, :3081) "filesystem type was not captured; the behaviour is exFAT/NTFS-shaped". No handbook line reports ext4 mounted at /media/RAW. Consequence from storage_profiles.py:74-94: 4 encode workers on CPUs 1-2, 2 disk workers on CPU 2, and `--buffer-count 10` (the task's given "8" is the default/ext4 profile value; cinepi_multi.py:845-853 also allows a settings override `sensors.raw_buffer_count`, so the value on the Pi remains UNKNOWN without its settings.jsonc/log line "Camera raw-buffer headroom: --buffer-count" :860-865).
- Whether --encode-nice -10 also fails (reader: PROBABLE): still PROBABLE, now with the mechanism: both worker kinds call the same setpriority at dng_encoder.cpp:432 through the shared configureThreadContext (:2015 / :2316); cinemate-autostart.service:23 `User=pi`, :27 `LimitRTPRIO=80`, and no LimitNICE/AmbientCapabilities line; the installer's limits.d drop-in grants only `@audio - rtprio 80` (cinemate-install.sh:1889). Not observed in any log, so not CONFIRMED.
- Process-wide launch prefix the reader did not report (ADDED): cinepi_multi.py:297-314@d6cc93e wraps cinepi-raw in `chrt -f 70` when `_rt_permitted()` (:105-114, probes `chrt -f 70 /bin/true`) succeeds, then `ionice -c2 -n0` (:304-306) and `taskset -c 1-3` (:308-310, "Keep the entire process off CPU0"). cinepi-raw itself changes policy only in the audio thread (cinepi_audio_capture.cpp:268 sched_setscheduler SCHED_FIFO). So on a rig where LimitRTPRIO=80 lets chrt succeed, EVERY cinepi-raw thread (main, libcamera, dng-enc-N, dng-dsk-N) inherits SCHED_FIFO 70 and the nice values become moot; PROBABLE, not confirmed — the handbook has no "chrt", "taskset", "ionice" or "RT scheduling not permitted" line either way (grep over *.md: none).
- Upstream O_DIRECT before 2025-06-04: UNKNOWN (outside all repos given). Out-of-order camera-buffer release on hardware: UNVERIFIABLE from source.

### Verdict table (one row per reader finding)
| # | Finding | Verdict | Note |
|---|---------|---------|------|
| 1 | open flags O_WRONLY|O_CREAT|O_TRUNC, one SEQUENTIAL fadvise, nothing else | CONFIRMED | all cites exact; file-wide grep agrees |
| 2 | git -S O_DIRECT hits are comments only; buffered since 9748cd0 | CONFIRMED | 9748cd0:26/:797/:798, 4c1c66e 20+/12-, 408 commits all exact |
| 3 | dead __dng_encoder.cpp (f7bc43e..1475f78) held the real O_DIRECT design | CONFIRMED | :38/:418/:779/:823/:829/:832 exact; md-only "buffer+1024 at :788-795" -> :819 |
| 4 | NOREUSE 2025-06-04, DONTNEED 0981681 2025-06-23, both removed b71ec67 2026-03-06 | CONFIRMED (numbers CORRECTED) | per-file stats 72+/37- and 37+/48-; the reader's 79+/41- and 42+/49- are whole-commit totals |
| 5 | one file per frame, one write() of usedSize, no retry, close on same thread, "DNG written" before open | CONFIRMED (cite CORRECTED) | `== disk_item.size` is :2362 (cite :2361-2362) |
| 6 | posix_memalign BLOCK_SIZE 4096, buffer_size formula, write_pod overflow | CONFIRMED (numbers CORRECTED) | thumb reservation: 0 B (cinepi-raw default) or 691,200 B (Cinemate default jpeg/shift 1); 172,800 B is the superseded shift-2 default; 17 MiB holds only with Cinemate's thumbnail |
| 7 | RAM permit cap 0.90 x MemAvailable, blocking encode worker, lazy pool, unbounded queues, stop at cap-2 | CONFIRMED | add: stop only when !justStarted (cinepi_raw.cpp:444-452); formula :1080-1082 has max(1, ...) |
| 8 | counters dropped_frames_/write_failures_/frames_in_flight_/buffer_hwm_, redis names, no disk-slow counter | CONFIRMED | single increment of dropped_frames_ at :2135 verified by grep |
| 9 | 2/8 defaults, Cinemate 4 enc + 2 or 8 dsk, affinity/nice mechanics, names, --buffer-count | CONFIRMED (cites CORRECTED) | spawn loops :305-311; profile blocks :61-73/:74-83/:84-94; add taskset/ionice/chrt prefix |
| 10 | disk nice -5 EPERM on the rig | CONFIRMED | encode -10 stays PROBABLE |
| 11 | hand-off: main thread syncs + queues, encode worker copies fused with DNG build, releases before disk I/O | CONFIRMED (cites CORRECTED) | :479-480; dng_save call :2239-2250; 2 s bound :2222; kRowStride=3 at :1167; both DMA syncs happen on the main thread before the worker reads |
| 12 | ccmpPreview is the only other raw reader; sampled in 16-bit, full render in 12-bit; 208 drops 2026-09-15 | CONFIRMED (cite CORRECTED) | cinepi_raw.cpp:57 (not :59) registers ccmpPreview; gating :263-266, measure_ = linear :385 |
| 13 | encodeBufferDone front-pop can release the wrong buffer with 4 workers | CONFIRMED as PROBABLE | honest label; :161/:172 exact |
| 14 | no MLV | CONFIRMED | grep empty |
| 15 | no disk-slow drop path; only three FAILED strings; Cinemate attributes holes to latency spikes | CONFIRMED (cite CORRECTED) | disk-io debug string is :2403 |
