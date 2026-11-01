# M — merged hypotheses to verify (from S1 storage, S2 capture/CPU, S3 evidence; readers R1..R9)

Each hypothesis is a claim the final answer page would rest on. Verifiers refute if they can. Report ids: R1 cinepi-raw writer,
R2 cinemate storage stack, R3 Apertar writer, R4 mounting, R5 evidence pass, R6 kernel/drive domain, R7 Apertar capture side,
R8 encoder/data rates, R9 libcamera config/back end; S1..S3 syntheses. All in this directory.

## H1 — 4K 50 fps SDR frames are lost upstream of Core's writers (libcamera's serial per-frame cycle), not in storage
Claim: T34 M3 (kb hardware-log 2026-10-28, lines ~582-597; 3840x2076 12-bit uncompressed, 60 s x2, untrimmed drive 78-82 %) lost ~12 % of
frames as steady single-frame capture gaps (dt 40 ms) with the write queue never above 3/12, 0 queue-full, 0 write failures, unchanged with 8
raw buffers; the writer sustained ~525 MB/s. Mechanism: libcamera runs one frame at a time through IPA -> PiSP back end -> completion; when the
cycle exceeds the 20 ms period the CFE finds no raw buffer at SOF and skips a frame. Implication: no writer-side change in the drop-frames build
(Log, ram buffer, trim, sync policy, mount options) can touch this case. Sources: R5 Q5/Q9, R8 (data-rate model), R9 §5-6, S2-1, S3-4, S1-8.
Also check: R6 says libcamera's IPA caps the pixel rate at 390 Mpix/s (1 us/390 in src/ipa/rpi/controller/controller.cpp HardwareConfigMap) so 4K
maxes at ~44 fps unless the fork raises it with the RP1 overclock; R9 says the operator's rig runs rp1-clk-333mhz and the kb's research-30fps
read a pixel-rate cap >= 518.4 MPix/s on the Pi, and that an IPA clamp would give uniform 22.7 ms periods rather than 20 ms periods with 40 ms
gaps. Settle which reading fits the logged pattern and what the forks do (Tiramisioux/libcamera and the Apertar fork; kb architecture/drivers.md,
working/research-30fps/*.md; cinemate-handbook mentions an 'RP1 regime' log line).

## H2 — cinemate runs the PiSP back end without temporal denoise; Apertar probably with it; TDN is the largest removable term of the serial cycle
Claim: cinemate's installer overwrites libcamera's imx585.json with resources/tuning_files/imx585.json (5 algorithms, no rpi.denoise, so no
TDN/SDN/CDN) and cinepi-raw is started with that tuning; libcamera enables TDN iff the tuning has a tdn block; the TDN reference is read and written
at the CFE raw format inside the serial back-end stage (bytes per 4K SDR frame 29.0 MB with TDN on COMP1 input vs 10.6 off; 57.6 vs 20.0 in Clear
HDR 16-bit); Apertar's /home/pi/Tuning-Files/defaults-pisp/imx585[_clearHDR].json is in no repo (TDN presence unknown, probable on). A tuning copy
without the tdn blocks, selected with set_tuning_file / APERTAR_TUNING_FILE, is the cheapest test for both operator cases. Sources: R9 §3-5, S2-1,
S2-I1, S3-5. Check the installer lines (cinemate-install.sh ~1551-1585, tuning_files.py ~96-118, cinepi_multi.py ~634), the tuning file content,
libcamera denoise.cpp:55 and pisp.cpp 'TDN' format rule (upstream tree at /home/user/raspberrypi/libcamera), and the byte arithmetic.

## H3 — The kb's A1-versus-A2 conclusion does not hold as a mechanism: Core's per-frame POSIX_FADV_DONTNEED already starts writeback and costs a cross-CPU LRU drain
Claim: CdngEncoder::writeDngFile calls posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED) after writing every DNG (src/cdng/CdngEncoder.cpp ~1780),
before close; in Linux 6.12 mm/fadvise.c that case runs __filemap_fdatawrite_range(WB_SYNC_NONE), then lru_add_drain(), mapping_try_invalidate(),
and on failures (dirty/writeback pages cannot be evicted) lru_add_drain_all() + invalidate_mapping_pages(); so the pages are not freed and every
DNG costs a drain on every CPU (queue_work_on + flush_work on mm_percpu_wq). The sync_file_range(SYNC_FILE_RANGE_WRITE) in startWriteback
(CameraController.cpp ~4504-4510, called at ~4978) then finds the writeback already started. Therefore run A2 (APERTAR_DNG_WRITEBACK=0) differed
from A1 by one redundant syscall, and 'the per-frame writeback hint keeps the CFE from stalling' (hardware-log 2026-10-30, drop-frames README
finding 5) is unsupported; A2's 10 % capture loss is one unexplained run (WebUI state unrecorded). cinepi-raw's removed DONTNEED (b71ec67) sat
before its write, on an empty file. Sources: orchestrator (kernel source read), R3 §4, R5 Q7, R6 e1-e4, S1-2/S1-3, S2-9, S3-3.

## H4 — With a browser on the WebUI preview, a per-frame downsample runs on libcamera's completion thread inside the serial cycle; it is the first candidate for the short-take capture gaps
Claim: ApertarCoreApp::captureWebPreviewFrame (ApertarCoreApp.cpp ~9347-9444) runs on libcamera's completion thread when mjpegClientCount_ > 0,
rate-limited to 30 fps (every frame at 25 fps): three downsampleNearestPlane passes 1280x720 -> <=640x360 reading ~0.7 MB from an mmap of the
preview dma-buf (probably non-cacheable memory); JPEG encode is on mjpegThread_. The four 2026-10-31 short takes that lost 2-10 frames at capture
2-4 s in had the WebUI open; the clean 10-minute takes did not; cinepi-raw's MJPEG runs on a detached thread off the serial cycle. Cost estimated
0.2-3 ms, never profiled. Test: the kb's two-take test (60 s closed vs open). Sources: R5 Q8, R7, R9, S2-2, S3-1.

## H5 — The copy worker allocates a fresh 16.6 MB zero-filled vector while holding DngRecordingQueue::mutex_, which libcamera's thread takes every frame
Claim: acquireRawBuffer (CameraController.cpp ~4623-4645) allocates std::vector<uint8_t>(size) under mutex_ on a pool miss; hasCapacityForFrame
(~4570) on the completion thread takes the same mutex; the pool keeps min(queue 12, max(workers 4 + 2, 4)) = 6 vectors and is cleared on every
(re)configure (~8191), so misses happen in the first frames of the first take after a reconfigure and whenever more than ~6 copies circulate
(recycleRawBuffer frees the excess, ~5140-5150). Estimated 1-8 ms per miss, inside the serial cycle. Sources: R3, R7, S1-4, S2-3.

## H6 — Clip deletes from the touch UI bypass Core, so no trim follows them; the ~0.9 TB stall can return in a touch-UI-driven session
Claim: Apertar-UI ClipListModel::removeClip (src/cliplistmodel.cpp ~382-440) removes files with QDir::removeRecursively / QFile::remove and never
tells Core; Core's trimMediaAfterDelete fires only from its WebUI delete handlers (/api/media/delete, delete-selected) and after the pre-roll when its
clip was >= 1 GiB; the pre-roll's usual 0.7 GB delete is below the threshold. Debian's fstrim.timer is no backstop for /media/RAW: util-linux 2.38.1
fstrim.service uses --listed-in /etc/fstab:/proc/self/mountinfo, which stops at the first non-empty file. (R6 disagrees: it says the timer trims
every mount; R4 read the fstrim.8 text. Settle it.) Sources: R4 L1, R5 Q6, R7, S1-9, S3-11.

## H7 — A 'discard' mount is not a substitute for fstrim on exFAT
Claim: the 6.12 exfat driver issues one synchronous sb_issue_discard per freed 128 KiB cluster inside __exfat_free_cluster under bitmap_lock, so a
15000-frame clip delete becomes ~1.9 million discards in the deleting process; FITRIM (exfat_trim_fs) issues one discard per free run (927 GB in
0.47 s measured); an unsupported discard option is logged and cleared. Sources: R4 §6, R6 a15, S1-12. Check fs/exfat/balloc.c and fatent.c
(raw.githubusercontent.com, v6.12 or rpi-6.12.y).

## H8 — Core moves each 16-bit frame through memory one more time than cinepi-raw (3 copies vs 2; 4 with Log) and uses ~43 syscalls per DNG against 4
Claim: copy worker memcpy (16.6 MB), writer row memcpy into a 491,520-byte scratch (writeDngRowBytes is a plain memcpy for unpacked 16-bit; chunk
= max(rowBytes, min(4 MiB, max(256 KiB, rowBytes*64))) = 64 rows -> 34 payload writes + header + IFD), kernel copy_from_user; Log adds an in-place
LUT pass on the copy worker. cinepi-raw: one row pass into a pooled aligned buffer with LUT/pack folded in, one write(). ~99.5 MB vs 66 MB of memory
traffic per frame (2.5 vs 1.7 GB/s at 25 fps). The kb measured libcamera's thread losing IPC (1.87 -> 1.30) while recording and that buffered dd
costs frames while dd oflag=direct does not: DRAM contention is the best-supported route from the writers to the back end. Writers on exFAT are 4
(MediaProfile {4,12,0} since 0358fcf), not 2. Sources: R3, R8, S1-6, S2-5, S3-9.

## H9 — The operator's cinemate baseline does not exist in writing; cinemate's chain is not drop-free in these cases by any record
Claim: cinemate's only quantified clean 4K Clear HDR 16-bit 25 fps record is eight ~10 s takes WITH Log 12 (docs/settings-json.md ~329-338),
medium unstated; its only multi-minute 16-bit soak stalled (handbook 2026-08-27/28, NTFS/FUSE, RAM pool full after 15-22 s); cinepi-raw dropped
frames at 4K 16-bit until the ccmpPreview fix ea53b2c (handbook ~3184-3203, 2026-09-15); nothing at 4K 50 fps exists anywhere; cinemate 3.3.1 left
4K above 25 fps to HD on SSD; cinemate's SDR path moves twice Core's link bytes (12:U = 16-bit container). Sources: R1 F1/F2, R2 §7, R5 Q1, R8, R9 §7,
S1-1, S2-7, S3-6.

## H10 — The storage pre-roll has no stated mechanism and no measured effect in either stack; Apertar's port has small code-grounded side effects
Claim: cinemate's storage_preroll.py says only 'warmed up' / 'priming', the origin commit e577437 has an empty body, zero handbook entries; Apertar's
pre-roll ran once at 60.0 fps (115 frames, 688 MB, deleted) and the planned COLD/WARM/SECOND A/B (drop-frames README step 0b) never ran. Code-grounded
possible benefits: the raw copy pool is warm for the next take (only without a reconfigure), exFAT metadata cached. Side effects: the deleted 0.7 GB is
below the 1 GiB delete-trim threshold (ApertarCoreApp.cpp ~10869-10870); a >= 1 GiB pre-roll queues a full fstrim right before the take and
record_start kills a trim running > 2 s; the gap counter is blind for max(10, N+6) frames after each fps change. Sources: R2 §4, R5 Q6, R7 §7,
S1-18, S2 assessment, S3-7.

## H11 — Core's per-file fsync on exFAT is a whole-device metadata flush plus an NVMe FLUSH per file (26/s at 25 fps, 51/s at 50); A1 showed it removable on a trimmed NVMe
Claim: syncLoop (CameraController.cpp ~4525-4549) fsyncs every file written in the last second then the folder; fs/exfat/file.c exfat_file_fsync =
__generic_file_fsync + sync_blockdev + blkdev_issue_flush. A0 (on) and A1 (off) were both clean for 10 minutes at 25 fps. It exists for pull-safety
(0-byte files after a pull with only the folder fsync, C0010). Sources: R3, R4 §5, R6 a8, S1-5, S3-10.

## H12 — Link and RP1 are identical on both rigs and inside the envelope at 4K 50 fps 12-bit; the drive/link envelope makes uncompressed 4K 50 fps marginal even if capture is fixed
Claim: both rigs run link-frequency=891000000 (1782 Mbps/lane, on the D-PHY's 1500 Mbps calibration bin, 'clamps instead of refusing') with the RP1
overclock; 4K 12-bit at 50 fps is ~70 % of the link and ~80 % of the RP1 pixel rate at 333 MHz; HMAX 550 at 891 MHz gives a 60 fps sensor ceiling.
Storage: 622 MB/s (4K 12-bit 50 fps uncompressed) is ~85 % of the measured dd-direct 733 MB/s at Gen 3 x1 and above anything sustained so far (525);
746 MB/s at 60 fps exceeds it; 415 MB/s (16-bit 25 fps) and 311 (Log) fit; no USB SSD on a Pi 5 carries 415 for 10 minutes. Sources: R6 d, R8, R9 §6,
S1-8, S2 comparison. Check the handbook 2026-08-27 entry (~line 731) and the arithmetic.

## H13 — nvme.max_host_mem_size_mb=0 is Raspberry Pi's own device-tree default on rpi-6.12.y; the drive's HMB minimum is 64 MiB; HMB mainly speeds small random reads
Claim: bcm2712-rpi.dtsi bootargs carry nvme.max_host_mem_size_mb=0 (after issue #6504: HMB exhausted the 64 MiB CMA); rpi-6.18.y (PR #7314) moves to
32 MiB with CMA-free allocation and cites up to 50 % random-read loss on DRAM-less drives at 0; the kb's kernel line 'min host memory (64 MiB) above
limit (0 MiB)' means only >= 64 MiB enables it on this drive (FW ERFM11.1 = MP600 Mini R2, Phison E27T, DRAM-less, per S1); an HMB caches the L2P
table, so it helps the exFAT metadata reads, not sequential writes; enabling it on 6.12 needs CMA headroom. Sources: R6 b, S1-14. Check the dtsi and
the PRs (github.com/raspberrypi/linux).

## H14 — exFAT metadata costs that grow with a take and with volume age: FAT-chain writes after the allocation cursor wraps, synchronous FAT/directory reads, O(N) directory lookups per create
Claim: in 6.12 exfat the allocation cursor (clu_srch_ptr) walks the volume and wraps at the end (~917 GiB written) and resets to the front at every
mount; a non-contiguous allocation converts the file to a FAT chain with one FAT entry per cluster written and the FAT sector read synchronously
(sb_bread) when cold (the 2026-10-30 stall stacks exfat_alloc_cluster > exfat_ent_set > __bread_gfp); every create of a new name scans every used
and deleted directory entry under the superblock lock (negative dentries are not reused for LOOKUP_CREATE): 4-5 entries per frame file, 60k-150k
entries late in a long take, estimated 6-30 ms per create; both stacks keep one folder per clip. A trim restores the drive but does not defragment.
Sources: R2 §2.3, R4 §4, R6 a, S1-10, S1-16. Check fs/exfat/dir.c, namei.c, fatent.c, balloc.c (v6.12) and whether the estimate is plausible.

## H15 — Scheduling: cinepi-raw runs SCHED_FIFO 70 on cores 1-3 with ionice; Core's only boost is a nice -5 on the callback thread that depends on an uninstalled drop-in
Claim: cinemate's cinepi_multi.py run() prefixes chrt -f 70, ionice -c2 -n0, taskset -c 1-3 (unit LimitRTPRIO=80; the installer sets isolcpus etc. on
4-core boards); cinepi-raw's own encode/disk nice calls fail EPERM. Core: no SCHED_FIFO, no affinity anywhere in src/, scripts/, config/; setpriority(-5)
on the completion thread succeeds only with LimitNICE=-5 from config/apertar-core-capture-priority.conf, which nothing installs or documents. Whether
the Pi's callback thread runs at nice -5 is unconfirmed. Sources: R2 §3, R7, S2-4, S3-16.

## H16 — 'Did the drop-frames changes make recording better': yes for the untrimmed-drive queue-full class, unmeasured for both operator cases
Claim: the trim finding rests on 71 synthetic runs plus one Core take each on an untrimmed (31 % lost) and a trimmed (0 lost) drive; A0/A1/A2 and the
short-take finding are one run each; no take longer than ~14 s of 4K 25 fps Clear HDR 16-bit and no 4K 50 fps take exists on the drop-frames build
(d44b177 and later); its only short takes lost 2-10 frames at capture with the WebUI open; nothing in the build runs on libcamera's thread or shortens
the serial cycle (Log adds a copy-worker pass; the ram buffer changes only the queue-full behaviour; trim and pre-roll act on the drive). Also: the kb's
finding 'takes.sh missing cannot see capture gaps' is conditional on the speed-ramp setting (frame numbering counts frames unless fpsSpeedRamp is on,
CameraController.cpp ~4462-4470, ~8922). Sources: R5 Q2-Q4, S3-2, S3 assessments, S1/S2 assessments.
