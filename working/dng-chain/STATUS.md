# DNG chain comparison (cinemate/cinepi-raw vs Apertar drop-frames): research in progress

Started 2026-11-01 in a cloud session (Claude Code) at the operator's request: compare the two DNG write chains, find
improvements for Apertar on exFAT / SSD (writing and mounting), explain the residual drops at 4K Clear HDR 16-bit 25 fps
(also with Log) and 4K 50 fps SDR, say whether the drop-frames changes made recording better, and whether the storage
pre-roll has an effect. Sources: Apertar-Core `drop-frames` 92d0970, Apertar-UI `drop-frames` e061be8, cinemate `main`
4990afc (full history), cinepi-raw `main` 63a08d5, cinemate-handbook c99ff77, this KB at 1899e8d, Linux v6.12 source.

Method: nine reader reports (R1..R9, assignments in `assignments/`, rules in `BRIEF.md`), then three syntheses from
different lenses, a merge, adversarial verification of every hypothesis (code, evidence, mechanism), a completeness critic.
The answer page will be `working/dng-chain-answer.md`. Syntheses: S1 (storage), S2 (capture/CPU), S3 (evidence). Code changes made so far: `patches/README.md`.

## State (updated as reports land)

| Report | Topic | State |
| --- | --- | --- |
| R1 | cinepi-raw DNG write chain and history | done |
| R2 | cinemate storage, mounting, kernel tuning, scheduling, pre-roll, docs, history | done |
| R3 | Apertar-Core write chain on drop-frames and history | done |
| R4 | Mounting: Apertar-UI automounter vs cinemate's, exFAT specifics | done |
| R5 | Evidence pass over the kb and the handbook | done |
| R6 | Domain: Linux exFAT internals, NVMe HMB, trim, bandwidth, writeback, libcamera | done |
| R7 | Apertar-Core capture side: completion thread, requeue, capture gaps, previews, pre-roll | done |
| R8 | Apertar-Core encoder path and data-rate model per case | done |
| R9 | What each stack asks libcamera for; the ISP back-end serial cycle; link utilisation | done |

## Findings already firm enough to act on (each has its refs in the report named)

1. The 4K 50 fps SDR take (T34 M3, 2026-10-28) wrote 525 MB/s with the write queue never above 3/12 and lost ~12 % of
   frames as steady single-frame capture gaps: the loss is upstream of Core's writers (libcamera's serial per-frame
   cycle), so no writer-side change (Log, ram buffer, trim, sync policy, mount options) can touch it (R5, R8).
2. Clear HDR 16-bit + Log at 311 MB/s is well inside the drive envelope; Clear HDR 16-bit linear (415 MB/s) ran 10 min
   clean on a trimmed drive (A0, A1). The residual drops in this case are capture-side and short-take (R5, R8).
3. The kb's A1-vs-A2 conclusion ("the per-frame writeback hint keeps the CFE from stalling") does not hold as a mechanism:
   `CdngEncoder.cpp:1780` calls `posix_fadvise(POSIX_FADV_DONTNEED)` after every DNG, and in Linux 6.12 that call itself
   starts asynchronous writeback (`mm/fadvise.c`: `__filemap_fdatawrite_range(WB_SYNC_NONE)`), then `lru_add_drain_all()`
   on every CPU when the dirty pages cannot be invalidated. A2 differed from A1 by one redundant syscall; its 10 % loss is one
   unexplained run (orchestrator + R5).
4. cinemate has no counted take of either operator case. Its only quantified clean 4K 16-bit 25 fps record is eight ~10 s
   takes WITH Log 12 (medium unstated); its only multi-minute 16-bit soak stalled (NTFS/FUSE); cinepi-raw itself dropped
   frames at 4K 16-bit until a preview fix in Sept 2026; nothing at 4K 50 fps exists (R1, R2, R5).
5. cinepi-raw requests 16-bit containers even for SDR (2 B/px on the link, twice Core's COMP1 bytes); Core's writer makes a
   second full copy of each 16-bit frame (row memcpy into a scratch, 491,520-byte write() chunks, ~37 syscalls/frame) where
   cinepi-raw packs once and writes once (R1, R8).
6. Both stacks format exFAT with mkfs.exfat's default 128 KiB clusters (cinemate tried 1 MiB and reverted for macOS); neither
   trims or mounts with discard except Core's new fstrim helper; the Linux exfat driver issues one discard per freed cluster under
   `-o discard` (R2, orchestrator).
7. exFAT writers on Apertar are 4 (MediaProfile {4,12,0} since 0358fcf), not 2 (R8).
8. The WebUI's MJPEG downsample runs on libcamera's completion thread when a browser is attached (ApertarCoreApp.cpp ~9355) (R5).

## How to resume if this session ends

Read `BRIEF.md`, the finished reports, then run the missing readers from `assignments/`, three syntheses, a merge, verification
and the critic as described above; write `working/dng-chain-answer.md` in the kb's answer-page format (see
`working/storage-answer.md`, `working/research-30fps-answer.md`).

### Added with R4 (mounting)
9. The live `/media/RAW` mount comes from the Apertar-UI CFE automounter (`mount(2)` with `uid=1000,gid=1000,umask=0002` + `MS_NOATIME`);
   `noatime` is on the mount. Three other Apertar mount paths (touch-UI Mount button, the Python re-insert watchers in Core and UI) lack
   `noatime`. Mount options are not a plausible cause of the residual drops (R4).
10. Touch-UI clip deletes bypass Core (`cliplistmodel.cpp` removes files directly), so Core's trim-after-delete never fires for them:
    the 0.9 TB stall can come back in a record/delete session driven from the touch UI (R4, lead L1).
11. A `discard` mount is not a substitute for the fstrim helper: the 6.12 exfat driver issues one synchronous discard per freed 128 KB
    cluster under `bitmap_lock` (~1.9 million for a 15000-frame clip) (R4).

### Added with R7 (capture side)
12. A capture gap is pure sensor-timestamp arithmetic (dt > 1.5 periods between recorded frames); the timestamp is the kernel's SOF
    stamp, so a gap always means the CFE did not deliver a frame (no raw buffer queued at SOF, or a CSI-2 discard). Core reads no
    sequence numbers, so it cannot attribute a gap; it only bounds its own share with drop[copy-slot], which never appears in the logs (R7).
13. One blocking hazard on libcamera's thread remains: hasCapacityForFrame takes DngRecordingQueue::mutex_, which the copy worker holds
    while it zero-fills a fresh 16.6 MB vector when the raw pool is cold (first ~6 frames after a reconfigure, or queue depth > 6) (R7).
14. When a browser streams the WebUI preview, a 1280x720 -> 640x360 downsample runs on libcamera's completion thread every frame (R5, R7).
15. No SCHED_FIFO or CPU affinity anywhere in Core; the nice -5 on the callback thread depends on a LimitNICE drop-in that nothing
    installs (whether it is in effect on the Pi is unconfirmed) (R7).
16. The pre-roll is a real take through the same queue; a pre-roll that writes >= 1 GiB (4K 12-bit uncompressed at 60 fps ~1.43 GB)
    queues a full fstrim right before the operator's first take, and record_start kills a trim that runs longer than 2 s (R7).

### Added with R3 (Apertar write chain)
17. Per uncompressed 4K DNG Core makes ~43 syscalls (open, fadvise, 1 + 34 + 1 write()s of 64-row chunks, fadvise DONTNEED, close,
    reopen + sync_file_range + close) and three full copies of the frame (copy worker memcpy, writer scratch pack, kernel copy), four
    with Log; cinepi-raw makes 4 syscalls and two copies. About 99.5 MB of memory traffic per 16-bit frame (2.5 GB/s at 25 fps)
    against cinepi-raw's 66 MB (R3, R8). For 16-bit the writer's scratch pass is a plain memcpy of rows with stride == rowBytes:
    an avoidable full pass.
18. The raw copy pool holds 6 vectors for 4 writers plus a 12-frame queue, so pool misses recur whenever the queue holds more than
    about two frames; each miss zero-fills a fresh 16.6 MB vector while holding the mutex libcamera's thread needs (R3, R7).
19. Swap was on and in use during takes on the Pi (hardware-log 2026-10-26); cinemate's installer disables swap (R3).

### Added with R9 (libcamera configuration and the ISP back end)
20. Both stacks ask libcamera for the same two streams (a 1280x720 YUV420 preview and the raw stream). The decisive difference is
    the tuning file: cinemate's installer overwrites libcamera's imx585.json with a 5-algorithm file that has NO rpi.denoise, so the
    PiSP back end runs without temporal denoise (TDN); Apertar's tuning (not in any repo) probably carries TDN. TDN reads and writes a
    full frame at the CFE format inside the serial per-frame cycle: back-end bytes per 4K SDR frame 29.0 MB (Apertar, COMP1, TDN on)
    against 19.8 MB (cinemate, 16-bit container, no TDN), and 57.6 against 20.0 MB in Clear HDR 16-bit. Bytes-scaled from the one
    measured cycle, Apertar's SDR cycle at 50 fps is 19-23 ms (T34 M3 delivered 44 fps = 22.7 ms); with TDN off 8-11 ms (R9, probable).
21. Link and RP1 are identical on both rigs (891 MHz = 1782 Mbps/lane on the D-PHY's 1500 bin, RP1 overclock) and inside the envelope
    at 4K 50 fps 12-bit (70 % of the link, 80 % of the RP1 pixel rate); they do not separate the stacks (R9).
22. Cheapest test for both residual cases: a tuning copy without the tdn blocks, selected with set_tuning_file / APERTAR_TUNING_FILE,
    measured with working/tools/be_cycle.py and a counted 60 s take (R9).

### Added with R6 (kernel and drive domain)
23. `nvme.max_host_mem_size_mb=0` is Raspberry Pi's own device-tree default on rpi-6.12.y (set after the HMB exhausted the 64 MiB CMA,
    issue #6504); rpi-6.18.y moves the default to 32 MiB and says the 0 default can cost up to 50 % on random reads of DRAM-less drives.
    Any non-zero value works; enabling it on 6.12 needs CMA headroom (cma- overlay parameter) (R6).
24. In the 6.12 exfat driver every cache-miss FAT or directory read is a blocking read on the writer's thread; a create of a new name
    scans every used and deleted directory entry under the superblock lock (O(N^2) per take, estimated 6 to 24 ms per create late in a
    long take); fsync is a whole-device metadata flush plus an NVMe FLUSH; the allocation cursor wraps at the volume end (the 0.9 TB
    mark) and resets to the front at every mount, so later takes become FAT-chain files (R6, mechanics confirmed, costs estimated).
25. fstrim.timer is weekly and Persistent on Debian, so a missed run fires minutes after boot and trims every mount (Core's own trim
    makes it redundant); exfat_trim_fs holds the bitmap lock for the whole walk (0.47 s here) (R6).
26. libcamera's PiSP IPA caps the pixel rate at 390 Mpix/s unless the fork adapts it to the RP1 clock: 4K 50 fps needs 415 Mpix/s.
    Both rigs run the RP1 overclock; whether each fork lifts the constant is to be verified (R6, R9).
