# Answer: Apertar vs Cinemate on Clear HDR frame drops, 30 fps and the sensor probe

Written 2026-10-26 in a cloud session (Fable 5.1) from source only; the camera was not run. Reply to `handoff-mac-cinemate-compare.md`. Every citation below was opened at the stated commit, first by me and then by an adversarial verifier pass (19 agents, 0 claims refuted, corrections were line offsets). Rule kept: logic and numbers, no Cinemate code.

| Repo (cite as) | Commit | Note |
| --- | --- | --- |
| `apertar-core` (ours) | `f60e301` main | |
| `cinepi-raw` | `63a08d5` dev | |
| `cinemate` | `d6cc93e` dev | |
| `cinemate-handbook` | `c99ff77` | Cinemate's numbers are from a CM5 / CM5 Lite 4 GB at 25 fps or the 21.99 fps cap, not a Pi 5 at 30 fps; its camera runs a libcamera working tree with uncommitted edits (`open-threads.md:358-388`) |
| `libcamera(cinemate)` = Tiramisioux/libcamera `cinemate` | `bfe0b76` | |
| `libcamera(qbc)` = will127534/libcamera `qbc-pisp-handler` | `7e9fef0` | **probable** base of our `v0.7.1+qbcfork.20260522`: raw-stats/CCMP commits 2026-05-17, RP1-clock cap `ae4d154` 2026-05-17, last commit before 05-22 is `33a17ea` 05-21; a binary at that tag lacks `4cff971` (imx585 exact-frame-rate getBlanking) and `401ba97` (16x gain). Not confirmed against the Pi's binary. |
| `imx585(apertar)` / `imx585(cinemate-7modes)` / `imx585(cinemate-modes)` | `e5b74d3` / `bd57617` / `18c1eb2` | |
| `kernel` = raspberrypi/linux `rpi-6.12.y`, `drivers/media/platform/raspberrypi/rp1_cfe/` and mm/ | `5bd564a` | the Pi runs a 6.12 kernel; same files, build may differ slightly |

## 1. Verdicts

| # | Theory | Verdict | One line |
| --- | --- | --- | --- |
| A | Page-cache writeback starves the CFE (Open A) | **probable**: mechanism class confirmed (Pi `dd` pair + kernel source), SoC-level cause unknown | Core's `posix_fadvise(DONTNEED)` per DNG starts async writeback of each 16.6 MB file at frame rate (`kernel mm/fadvise.c:113-115`), so a take *is* the buffered-`dd` load that reproduces the gaps; `oflag=direct` does not. Cinemate writes buffered too, never shipped O_DIRECT (a 4-day trial in June 2025 was deleted), and has no record of this symptom; it runs with dirty-byte cushions, SCHED_FIFO 70 and the whole process off CPU0. |
| A2 | (unasked) CSI-2 link 1782 Mbps/lane is above the RP1 D-PHY's 1500 Mbps table | **unknown**, one-run test | `kernel dphy.c:119-129` warns and programs the 1500 bin; both Cinemate's handbook and the driver README call >1440 out of spec. The CSI-2 error counters (below) separate A from A2. |
| B | 30 fps: completion-thread work + buffer loop (Open B) | **probable**: every component confirmed from source, the sum not yet timed on the Pi | Our libcamera does 2 full-buffer passes per 16-bit frame (swap + unconditional software stats) vs Cinemate's 1 (0 in 12-bit); Core adds sync + 16.9 MB copy (+ 12-bit mapping, + web-preview downsample when a client is attached) on the same thread; Core circulates **3** requests, Cinemate 8. |
| B2 | (unasked) Extra raw buffers never reach libcamera | **confirmed** | `makeRequests` caps requests at 3 for cDNG/MLV whatever the buffer count (`apertar-core/src/camera/CameraController.cpp:1048, 6796-6800@f60e301`); the 4th buffer is mmapped but idle (`:7082-7086`). The "8 buffers changed nothing" test probably still ran 3 requests. |
| B3 | (unasked) Cold pool at every take start | **confirmed** | `rawPool_.clear()` in `stop()` (`:3596-3598`): the first ~6 frames of every take allocate and zero-fill 16.6 MB on the completion thread. Fits "first takes after a reconfigure were lossy". |
| C1 | Core's probe misses something cinepi-raw does | **mostly ruled out** | Same configure-per-mode core and fps formula; `LIBCAMERA_RPI_MAX_PIXEL_RATE` is unnecessary (qbc derives the cap from the RP1 clock). Real difference: Core skips `validate()`-adjusted sizes, cinepi-raw keeps and dedups them. |
| C2 | Crop rectangles need driver metadata | **confirmed: root cause is the `apertar` driver's `.crop` table values** | `ScalerCropMaximum` = subdev `V4L2_SEL_TGT_CROP` relative to the active area; the `apertar` table fills every `.crop` with the *output* size at (0,0). Cinemate's "Mode Crop *" controls are a cinepi-raw-only channel; its driver had the same defect and fixed it in `951aeee` (2026-09-20). Values-only port, no new controls. |

## 2. Theory A: disk writes and the CFE

### What Cinemate does

| Item | Cinemate | Where |
| --- | --- | --- |
| DNG open flags | buffered `O_WRONLY + O_CREAT + O_TRUNC`; comment "Use standard buffered IO instead of O_DIRECT" present since the repo's first commit | `cinepi-raw/cinepi/dng_encoder.cpp:2351-2352@63a08d5`; `9748cd0:cinepi/dng_encoder.cpp:797-798` |
| O_DIRECT history | one trial, in a dead file: `cinepi/__dng_encoder.cpp` added `f7bc43e` 2025-06-10, deleted `1475f78` 2025-06-14; 64 KiB-aligned buffer, `open(O_WRONLY + O_CREAT + O_DIRECT)`, one whole-buffer write, `ftruncate` commented out; no reason recorded | `git show f7bc43e:cinepi/__dng_encoder.cpp:38, 779, 823, 832` |
| fadvise / fsync | `POSIX_FADV_SEQUENTIAL` only; DONTNEED added `0981681` 2025-06-23, **removed** `b71ec67` 2026-03-06; no fsync/sync_file_range | `dng_encoder.cpp:2356@63a08d5` |
| Write pattern | one file per frame, **one `write()`** of the whole assembled DNG (~16.6 MB) from a `posix_memalign(4096)` pool buffer sized up to 1 MiB; short write = `write_failures_`, no retry; `close()` on the disk thread | `:2182-2184, :1039, :2360-2365, :2374` |
| RAM pool | 90 % of `MemAvailable` at start (173 frames ≈ 2.9 GB on their 4 GB CM5); encode worker **blocks** when permits are gone (camera buffers then held → one-frame hole); recording stops when full | `:1078-1082, :2174`; `cinepi-raw/cinepi/cinepi_raw.cpp:437-447`; `cinemate-handbook/lessons/hardware-log.md:966-968@c99ff77` |
| Threads | 4 encode + 8 disk workers (ext4 profile) on CPUs 1-2; the requested nice -10/-5 **fail with EPERM** on their rig and are moot because the whole process is SCHED_FIFO 70 | `cinemate/src/module/storage_profiles.py:61-73@d6cc93e`; `cinemate-handbook/open-threads.md:340-356` |
| Process | `chrt -f 70`, `ionice -c2 -n0`, `taskset -c 1-3` (**off CPU0**); unit `LimitRTPRIO=80` | `cinemate/src/module/cinepi_multi.py:294-313@d6cc93e`; `services/cinemate-autostart/cinemate-autostart.service:27` |
| Camera buffers | `--buffer-count 8` (10 on exFAT/NTFS); rpicam-apps base 6 | `storage_profiles.py:59,72,82,93`; `cinepi_multi.py:866`; `cinepi-raw/core/rpicam_app.cpp:630` |
| Kernel, at RAW mount on an NVMe | `vm.dirty_bytes` 1 GiB, `vm.dirty_background_bytes` 256 MiB, `dirty_ratio` 0, `dirty_background_ratio` 0, `dirty_writeback_centisecs` 150, `dirty_expire_centisecs` 3000; queue `scheduler` none, `rq_affinity` 2, `nr_requests` 512; ext4 `rw,noatime,nodiratime,commit=60`; NVMe APST latency 0 attempted; restored at unmount; introduced `2294d25` 2025-10-14 with no stated reason or measurement | `cinemate/services/storage-automount/storage-automount.py:140-148, 285-336, 364-380@d6cc93e` |
| Kernel cmdline | `isolcpus=managed_irq,domain,3 nohz_full=3 rcu_nocbs=3 irqaffinity=0-2` **for audio**; nothing targets rp1-cfe/pispbe; no udev, sysctl.d or irqbalance | `cinemate/cinemate-install.sh:1257-1275@d6cc93e` |
| "Frames drop when the disk is busy"? | Yes, as **application-level buffer starvation**: "RAM permits momentarily exhausted → camera buffers held → starve the sensor for a single frame period" (→ `--buffer-count 8`), "Frame drops are disk-write-latency-bound ... ext4 drops less"; no measurement. Their 16-bit soaks stalled when the RAM pool filled on NTFS-over-FUSE. The handbook never mentions dirty_bytes, writeback, page cache or O_DIRECT. | cinemate `31126f2` (2026-05-31), `a61a589` (2026-06-01); `hardware-log.md:964-982` |
| Headroom at 25 fps 16-bit 4K | 22.2-26.3 ms encode/frame, 317-334 MB/s, "never dropped a frame, never failed a write, and never let the disk queue past two" | `cinemate/docs/settings-json.md:333-338@d6cc93e` |

### What Apertar does

| Item | Core | Where |
| --- | --- | --- |
| cDNG uncompressed | open `O_WRONLY + O_CREAT + O_TRUNC + O_CLOEXEC`; fadvise SEQUENTIAL; `write()` 8-byte header, payload in 491,520 B chunks (64 rows; ~34 writes), 0-3 pad bytes, IFD **at the end** (1.3-1.7 KB, so no DNG is a 4096 multiple); fadvise **DONTNEED**; close; ~40 syscalls per frame | `apertar-core/src/cdng/CdngEncoder.cpp:1748-1786, 1861-1912, 1387-1392@f60e301` |
| cDNG lossless | 8-byte placeholder, strips streamed as encoded, header `pwrite()` at the end, same DONTNEED | `CdngEncoder.cpp:1272-1277, 1760-1766, 1779` |
| MLV | same flags; 9 header blocks at open; per frame a 32-byte VIDF (`frameSpace` 0) + payload in the same chunks | `apertar-core/src/mlv/MlvEncoder.cpp:949-990, 1020-1033, 862-884@f60e301` |
| Queue / pool | 12 frames (24 compressed); `dropped_queue_full` when full; raw-copy pool of `workers+2` vectors, **cleared at every stop** | `CameraController.cpp:3436-3456, 3596-3598, 3637-3700, 3994, 4029` |
| Process | `LimitNICE=-5`; nice -5 on the callback thread; lossy/lossless workers nice +5/0; no affinity, RT, sysctl or IO tuning anywhere in the repo | `apertar-core/config/apertar-core-capture-priority.conf`; `CameraController.cpp:6926-6935, 3809-3817`; `scripts/start-apertar-core.sh` |
| Kernel defaults (verify with `sysctl`) | `dirty_background_ratio` 10, `dirty_ratio` 20, writeback 5 s, expire 30 s | `kernel mm/page-writeback.c:74,91,102,109@5bd564a` |
| Filesystem of `/media/RAW` | **never established**; Core's `format_media` defaults to exFAT | `apertar-core/src/ApertarCoreApp.cpp:10647@f60e301`; check `findmnt /media/RAW` |

### The difference that matters

- `POSIX_FADV_DONTNEED` starts **asynchronous writeback of the dirty range** before dropping pages (`kernel mm/fadvise.c:113-115@5bd564a`). Core therefore emits one 16.6 MB writeback burst per frame at 25-30 Hz: the same kernel-driven page-cache writeback as the idle `dd conv=fdatasync` test (gaps start 0.6-1 s in, when ~350 MB = 10 % of RAM is dirty and background writeback begins). Cinemate's writer has had no DONTNEED since March; its writeback is paced by cushions (256 MiB background / 1 GiB hard, 1.5 s flush) and written once per frame instead of 40 times.
- Neither stack ships O_DIRECT. The only direct-IO datapoint is our `dd oflag=direct` at 759 MB/s with 0 gaps. Cinemate's tuning is not a proven cure for our symptom; it is the cheaper first experiment.
- What actually loses the frame (kernel): the CFE skips a frame when **any** enabled node (image, stats, FE config, embedded) has no buffer queued ("has no buffer, unable to schedule job", `kernel cfe.c:615-631`), and the CSI-2 receiver has **hardware overflow and discard counters** (`kernel csi2.c:19-21, 175-258`). With `rp1_cfe.track_csi2_errors=1` the file `/sys/kernel/debug/rp1-cfe:<dev>/csi2_errors` prints "Overflows N" and per-VC discards (OVLF / LEN / UNMATCHED / INACTIVE), resetting on read (`csi2.c:582, 189-196`). It separates memory-write starvation (OVLF), link corruption (UNMATCHED/LEN = theory A2) and a late requeue (nothing counted; "no buffer" in the debug log with `verbose_debug=1` + dynamic debug, `cfe.c:52-53`).

### Proposed change for Core

Stage 0, no code, one evening, in this order:

1. `rp1_cfe.track_csi2_errors=1` in `cmdline.txt`, reboot. Read `csi2_errors` to zero it; run the idle `dd conv=fdatasync`; read again. Repeat with `oflag=direct`, then with a lossy 16-bit take. Prediction under A: Overflows/OVLF count the gaps in runs 1 and 3, 0 in run 2.
2. Same `dd` to tmpfs (`/dev/shm`): memcpy + page cache, no NVMe DMA. Gaps = memory-side; none = writeback/NVMe-side.
3. `grep -E 'nr_dirty|nr_writeback' /proc/vmstat` every 100 ms during the NVMe `dd`; line the first gap (`ipa_rate.py`) up with the first non-zero `nr_writeback`.
4. Cinemate's knobs: `vm.dirty_background_bytes=268435456 vm.dirty_bytes=1073741824 vm.dirty_ratio=0 vm.dirty_background_ratio=0 vm.dirty_writeback_centisecs=150`; `echo none > /sys/block/nvme0n1/queue/scheduler`; `rq_affinity=2`; repeat the `dd` pair and 5 `takes.sh` takes. Plus one build with the DONTNEED call removed, to see whether per-frame bursts are worse than the kernel's own pacing. Also `findmnt /media/RAW` (ext4 vs exFAT decides step 1 below).

Stage 1, O_DIRECT in both writers (if stage 0 points at page-cache writeback):

- **Alignment:** O_DIRECT needs file offset, length and memory aligned to the device's logical block size (512 or 4096); use 4096 everywhere. `posix_memalign(4096)` for the raw-copy pool and the payload scratch (491,520 B = 120 pages already). ext4 and kernel exFAT support direct IO; FUSE/NTFS-3g may not → on `EINVAL` at open or first write, fall back to buffered IO for the clip and log once.
- **cDNG uncompressed, IFD-first layout:** page 0 = 8-byte header + IFD + zero padding (`StripOffsets` = 4096), then the payload straight from the aligned raw copy. 3840x2160 16-bit = 16,588,800 B = exactly 4050 pages; the 2200-row readout is cropped to 2160 rows of 7680 B first. Heights not divisible by 8 (1038, 1504 ...) leave a tail: write the last page from a zeroed buffer and `ftruncate()` to the real size after the last write (metadata only, allowed on an O_DIRECT fd). No fadvise. This also removes the 34 payload writes (one or a few large writes instead) and the per-frame scratch memset (`CdngEncoder.cpp:1201, 1207`).
- **cDNG lossless:** strips into an aligned staging buffer, flushed in page multiples; final partial page padded + `ftruncate`; page 0 (header + IFD) written **last** instead of the 8-byte `pwrite`, which is illegal under O_DIRECT. Lower priority: lossless at 25 fps loses 0-2 frames at ~130 MB/s.
- **MLV:** one aligned staging ring per file; all blocks appended and flushed in page multiples; set VIDF `frameSpace` so frame data starts page-aligned (that field exists for this); on close pad + `ftruncate`, and rewrite page 0 from its in-memory copy for the frame-count patch.
- **Error handling:** keep `write_failures`; retry a short direct write once with the remainder; `ENOSPC` ends the clip as today; log the IO mode in the "recording clip" line.
- **Pool:** pre-allocate the aligned raw pool at `start()` instead of clearing it at `stop()` (B3), so no take begins with 16.6 MB zero-fills on the completion thread.

### Pi measurement that confirms A

`takes.sh 5` in 16-bit at 25 fps after each step; target 5/5 takes with 0 missing and `ipa intervals>60ms=0`; `csi2_errors` 0 across each take; `nr_writeback` ≈ 0 during an O_DIRECT take. Keep the `dd` pair as the control: if `dd conv=fdatasync` still produces gaps while Core's takes are clean, Core is fixed and the kernel-level cause stays documented, not solved.

## 3. Theory B: 30 fps, the completion thread and the buffer loop

### What Cinemate does (cinepi-raw at 4K Clear HDR)

| Item | Cinemate | Where |
| --- | --- | --- |
| Which thread copies the raw frame | an **encode worker**: the DNG is assembled straight from the camera buffer into the pool buffer (copy fused with assembly); the main thread only does the dmabuf read-sync and queues | `cinepi-raw/cinepi/cinepi_recorder.hpp:49-105, 158-174@63a08d5`; `dng_encoder.cpp:455-483, 2239-2250, 2304` |
| libcamera's completion thread | posts the request to a message queue; the post-processor runs its stages in a detached thread per frame | `cinepi-raw/core/rpicam_app.cpp:255, 1212-1241@63a08d5`; `hardware-log.md:2366-2372` |
| When the buffer goes back | when the encode worker's copy is done (`input_done_callback` pops the `CompletedRequestPtr`), not after the disk write; the pop assumes FIFO completion (a porting caution, not a bug seen) | `cinepi_recorder.hpp:158-174` |
| Buffers | video (= lores alias) and raw share the count: 6 default, **8 with Cinemate**, 8 requests in flight; 8 × 16.9 MB raw + 8 × 1280x720 lores ≈ 146 MB | `rpicam_app.cpp:630-632, 657-658`; `storage_profiles.py:59,72` |
| Per-frame budget they measured | 16-bit 4K: 21.9 ms median / 27.7 max for the (since removed) software re-render; 12-bit 4K 35.2 / 45.1, still shipped on "a thinner margin than is comfortable"; encode 22.2-26.3 ms/frame at 25 fps. Their Sept 4K 16-bit drops were that second render per frame; a suspected 0.38 ms/frame pass was timed and exonerated | `hardware-log.md:2240-2247, 3184-3209@c99ff77`; `docs/settings-json.md:333-338` |
| libcamera, 16-bit | **the same `rev16` swap**, flag bit 5, in `cfeBufferDequeue` between dmabuf sync start/end on the pipeline-handler thread; COMP1 excluded (`bcdd7e1`). The swap dates from upstream's first Pi 5 pipeline commit (`ed57f65`, 2023-06-19): a Raspberry Pi design, not a fork quirk | `libcamera(cinemate)/src/libcamera/pipeline/rpi/pisp/pisp.cpp:373-389, 1449-1459, 1724-1738@bfe0b76`; `rpi_stream.h:89` |
| libcamera, stats at 16-bit | **no software stats**; "statistics will not be correct. You must use manual camera settings". Cinemate runs 16-bit with manual exposure, gain **and** white balance (`--awb auto --awbgains` → `ColourGains` → AWB auto off) | `pisp.cpp:1456-1458@bfe0b76`; `cinemate/docs/clear-hdr.md:10`; `cinepi_multi.py:633-635, 702-703`; `libcamera(cinemate)/src/ipa/rpi/common/ipa_base.cpp:1075-1089` |
| libcamera, 12-bit CCMP | no CPU pass in libcamera; the ISP sees companded codes; cinepi-raw's own stage corrects the preview (31-35 ms, detached thread) | `hardware-log.md:2226-2247` |

### What Apertar does

| Item | Core / our libcamera | Where |
| --- | --- | --- |
| Why the swap exists | "we must endian swap the buffer contents to account for the HW missing this feature": the RP1 passes 16-bit raw with `csi_dt = 0` "to avoid RP1 HW mismatch for 16-bit modes" and cannot reorder bytes; no CFE byte-order bit exists in the driver | `libcamera(qbc)/.../pisp.cpp:1553-1562@7e9fef0`; `kernel cfe_fmts.h:197-227`, `cfe.c:855-856`, `csi2.c:346` |
| Second pass | `RawStatsProducer` engages **unconditionally** whenever the 16-bit swap (or 14-bit unpack) flag is set ("CFE statistics engine has a known bug at ≥14-bit unpacked raw"); no env var or config key disables it; 12-bit CCMP: `CcmpUnwrap` rewrites the buffer in place (the comment saying otherwise is stale), then stats; one black-level ioctl per frame | `pisp.cpp:1616-1660, 1963-1975, 2010-2013, 2817-2854@7e9fef0`; `raw_stats.h:1-15`; `ccmp_unwrap.h:43` |
| Passes per frame, pipeline thread | 16-bit 3840x2200 (33.8 MB): swap (r+w) + stats (r) = 2 passes ≈ 15 ms measured; 12-bit 3840x2160: unwrap (r+w) + stats (r). Cinemate: 1 / 0 | above |
| Core on the same thread | metadata; preview = fd registration once per slot then a descriptor; **web preview**: nearest downsample 1272x720 → 636x360 inside the preview callback when an MJPEG client is attached; DMA_BUF sync (~4 ms) + 16.6-16.9 MB memcpy (~4 ms); 12-bit cDNG: LUT over 8.3 Mpx; first ~6 frames of a take: fresh 16.6 MB zero-filled allocation; `requeueRequest` only after all of it | `CameraController.cpp:6915-7008, 7189-7287, 6779-6786, 7567-7660, 1335, 3596-3598, 3670@f60e301`; `ApertarCoreApp.cpp:7002, 8111-8189` |
| Requests and buffers | **3 requests** (`kActiveRequestCount`), 4 raw + 4 preview buffers, buffer 4 mapped but never attached; no runtime override | `CameraController.cpp:1047-1048, 6788-6831, 7082-7086` |
| Worker side (12-bit cDNG) | a second 16→12 pack pass per frame on the worker, plus a 491,520 B scratch memset per frame | `CdngEncoder.cpp:1054-1060, 1201, 1207` |
| Sum at 30 fps 16-bit | 15 (libcamera) + 8 (Core) ≈ 23 of 33 ms ≈ 70 % on one thread; measured 52-72 % | |

### The difference that matters

At 30 fps the single libcamera thread spends ~70 % of each frame in bulk memory work, and it is also the thread that services every CFE/BE V4L2 event, prepares the next FE config buffer and talks to the IPA. With 3 requests the CFE holds at most 2 frames (66 ms) of slack, and the kernel skips a frame when **any** of its four nodes lacks a queued buffer. Cinemate has 8 requests, a thread that only posts to a queue, one or zero libcamera passes, SCHED_FIFO 70, and no CPU0 IRQ competition.

### Proposed change for Core (in order; measure after each)

1. **Requests = buffers.** Let the in-flight request count follow the configured buffer count and raise Clear HDR buffers to 6, then 8 (16.9 MB raw + 1272x720 preview each). This re-runs the 8-buffer experiment properly. Measure: `ipa_rate.py` while recording at 30 fps (target 30.00, `intervals>40ms=0`), `takes.sh` at 30 fps (target 291/291), rp1_cfe `verbose_debug=1` + dynamic debug to count "has no buffer" lines per take and which node.
2. **Pre-allocate the raw pool at `start()`** (aligned, size = buffers + queue); stop clearing it at `stop()`. Measure: first-take vs later-take loss.
3. **Copy off the completion thread.** Hand the `libcamera::Request*` to the recorder queue; a worker does the dmabuf sync, the memcpy into the aligned pool buffer and the 12-bit mapping, then requeues. Core's H.264 path already releases from a copy worker (`releasePreviewJob`/`job.release()`, `CameraController.cpp:4799-4805`): reuse that pattern. `queueRequest` is thread-safe; `requeueRequest` merges pending controls under its own mutex and its photo-bracket logic must stay single-threaded. Hold at most N-3 requests in workers so the CFE always has ≥2 queued; count-and-drop instead of holding when workers are behind. Measure: `usample.py` on the CameraManager tid (Core's share → ~0, thread → ~45 % at 30 fps 16-bit).
4. **One libcamera pass instead of two (our fork).** Either a pipeline-config key (the handler already reads `disable_tdn`/`disable_hdr`) that skips `RawStatsProducer` when the application runs manual exposure (Cinemate's 16-bit model), or fuse swap and stats into one read-swap-accumulate-write pass. Expected: 7 ms/frame back. Measure: `usample.py` share of `RawStatsProducer::process`.
5. **Scheduling, as Cinemate:** `LimitRTPRIO` in the unit and SCHED_FIFO for the CameraManager thread, or at least `taskset` the process to CPUs 1-3 so it never shares CPU0 with the RP1 IRQs. Measure as in 1.

## 4. Theory C: the sensor probe and crop modes

### Probe comparison

| Step | cinepi-raw `--list-cameras` | Core `probeSensorModes` |
| --- | --- | --- |
| Per mode | `sensorConfig{outputSize,bitDepth}` → `validate()` → `configure()` → fps = 1e6 / `FrameDurationLimits.min` → `ScalerCropMaximum` (`cinepi-raw/core/options.cpp:401-417@63a08d5`) | identical core (`CameraController.cpp:5485-5504@f60e301`); 42 modes = 20 sizes × 2 SDR codes + 1 × 2 Clear HDR codes (`imx585(apertar)/imx585.c:794-1226`) |
| Pixel-rate ceiling | `--max-pixel-rate` → env `LIBCAMERA_RPI_MAX_PIXEL_RATE` (`options.cpp:236-247`), read by its IPA, default 380 MPix/s (`libcamera(cinemate)/src/ipa/rpi/controller/controller.cpp:82, 116-138@bfe0b76`), because that fork cannot detect the overclock | **not needed**: the qbc IPA derives the cap from the DT `RP1_PLL_SYS` request ("PiSP pixel-rate cap = 646.667 Mpix/s"), with a sanity clamp to stock 380 outside 0.5-4× of 200 MHz (`libcamera(qbc)/src/ipa/rpi/controller/controller.cpp:40-143@7e9fef0`) |
| WDR states | `set_subdev_hdr_ctrl(0)` before the CameraManager; `--hdr sensor` sets 1 and re-creates it; Cinemate runs the binary twice (`options.cpp:258-259`; `cinemate/src/module/sensor_detect.py:23-24, 844-845`) | both states in one process, new CameraManager per state, then WDR set to the session's value (`:5455-5466, 5603`); the WDR pass is skipped silently when no imx585 subdev is found (`:5450-5457`) |
| `validate()` adjustments | keeps the adjusted size, dedups by size/binning/crop signature (`:446-459`) | **skips** a mode whose size changed (`:5493-5495`) |
| Driver metadata | `read_driver_mode_metadata` per mode (`:426`) | none (not in our driver) |
| Retries / failure | WDR failure in list mode is a stderr note, listing continues (`:556-560`) | `acquire()` failure (another process holds the media device, `lockf`) → "no camera to acquire", no retry (`:5512`) |
| Mono / packing | mono via libcamera formats; 16-bit lists only as SRGGB16 (no packed variant exists, `pipeline_base.cpp:57-63`) | same |
| Pitfalls Cinemate hit | text parser dropped 16-bit lines; EBUSY from another process; stale RP1 regime from `config.txt` mtime capping 16-bit at 21 fps (`hardware-log.md:3135-3182`) | none apply to an in-process probe with a clock-derived cap |

### Crop metadata

| | Finding | Where |
| --- | --- | --- |
| How libcamera gets `ScalerCropMaximum` | = `sensorInfo.analogCrop` = subdev `V4L2_SEL_TGT_CROP`, x/y relative to `V4L2_SEL_TGT_CROP_DEFAULT`; the imx585 (one source pad) goes through `CameraSensorLegacy` | `libcamera(qbc)/src/libcamera/pipeline/rpi/common/pipeline_base.cpp:562-568@7e9fef0`; `src/libcamera/sensor/camera_sensor_legacy.cpp:410, 878-893`; `camera_sensor_raw.cpp:196-215` |
| What all three drivers return | `TGT_CROP` = the subdev state's crop (set from `mode->crop`); `CROP_DEFAULT`/`BOUNDS` = (0,0,3840,2160); `NATIVE` = 3856x2180. **Identical functions.** | `imx585(apertar)/imx585.c:2374-2400@e5b74d3`; `imx585(cinemate-modes)/imx585.c:4298-4332@18c1eb2` |
| Root cause of Open C | the `apertar` table sets `.crop = {0, 0, <output w>, <output h>}` in all 21 entries: 1920x1080 2x2-binned → 1920x1080 (should be 3840x2160); 1920x1038 → 1920x1038; 3840x1504 → (0,0)/3840x1504 (should be top 328); 16-bit 3840x2200 → (0,0)/3840x2160 (right). The WINMODE register table already holds the true window starts (VST 54/80/132/220/228/276/288/324/340 → native tops 42/68/120/208/216/264/276/312/328) | `imx585(apertar)/imx585.c:795-830, 1160-1195, 607, 688@e5b74d3` |
| Cinemate's rule, and history | "mode->crop ... is in NATIVE SENSOR-PIXEL coordinates ... what libcamera reads to derive its own binning": non-RAW16 binning b → crop = output × b; RAW16 1x1 → height - 40; left/top = 0 full-field, centred offset when windowed; a script checks the invariant. Cinemate's driver had the **same output-domain defect** until `951aeee` (2026-09-20, "report sensor crop in sensor coordinates"); the custom controls came the day before (`b703f46`, `74ed4c6`) | `imx585(cinemate-modes)/imx585.c:1044-1060@18c1eb2`; `tools/check_window_alignment.py` |
| What `read_driver_mode_metadata` reads | five read-only V4L2 controls found **by name** over `/dev/v4l-subdev0..31`: "Mode Binning", "Mode Crop Left/Top/Width/Height" (`V4L2_CID_USER_BASE + 0x2000 + 10..14`), optional "Mode Active *" (imx283); updated by the driver on every mode change; used for cinepi-raw's DNG active-area tags, preview crop and mode signature, **not** by libcamera | `cinepi-raw/core/driver_mode_metadata.hpp:14-15, 161-168, 307-372@63a08d5`; `imx585(cinemate-modes)/imx585.c:45-50, 3354-3366, 3783-3805, 3872-3877`; `cinepi-raw/cinepi/ifd_builder.hpp:25-35` |
| Which branches have them | `cinemate-modes` only; `cinemate-7modes` and `apertar` do not | grep |

### Smallest driver change for Core

Fill `.crop` in the `apertar` table with the sensor-domain window per entry (left/top centred, width/height = output × binning), rebuild the module, and Core's existing probe reports real rectangles with no Core or libcamera change: 1920x1080 binned → (0,0)/3840x2160 (crop factor 1, binning 2); 1920x1038 binned → (0,42)/3840x2076; 3840x1504 → (0,328)/3840x1504. Binning = crop width / output width. Two things to expect: libcamera's preview `ScalerCrop` range and the IPA's sensor geometry change with it (the 2120-vs-2160 preview oddity may move), and the 16-bit 3840x2200 entry stays at 2160 rows (Cinemate's rule), which makes the IPA's integer `scaleY` 0 in both stacks (`libcamera(qbc)/src/ipa/rpi/common/ipa_base.cpp:592`), a latent ALSC-resampling oddity currently masked (probable). Cinemate's `cinemate-modes` also rejects windows whose start row is not a multiple of 4, hence its 2072-row 1.85:1 crop where ours is 2076 (`imx585(cinemate-modes)/imx585.c:2964-2969`); hardware effect of our 2076 unknown.

Pi check: `v4l2-ctl -d /dev/v4l-subdevN --get-selection target=crop` after a mode switch; `list_sensor_modes` then shows `crop=` per mode.

## 5. Surprises not asked for

1. **Only 3 requests circulate in Core** regardless of buffer count (`CameraController.cpp:1048, 6796-6800@f60e301`); buffers 4+ are mapped but never attached.
2. **Core's `fadvise(DONTNEED)` starts writeback immediately** (`kernel mm/fadvise.c:113-115`): a Clear HDR take is a 420 MB/s page-cache writeback stream in 16.6 MB bursts, the same class of load as the `dd` that reproduces the gaps.
3. **The raw pool is emptied at every stop**, so each take starts with ~6 fresh 16.6 MB zero-filled allocations on the completion thread (`:3596-3598, 3670`).
4. **Our link rate is outside the receiver's table**: 1782 Mbps/lane vs the D-PHY code's 1500 cap, programmed with the 1500 bin (`kernel dphy.c:99-129`). Cinemate verified 1782 "all seven modes clean" on a CM5 but recommends 1440 and calls >1440 "out of spec by design" (`imx585(cinemate-7modes)/README.md:243-255@bd57617`; `hardware-log.md:741-748, 985`).
5. **CSI-2 error counters exist** but only with `rp1_cfe.track_csi2_errors=1` at module load (`kernel csi2.c:19-21, 582`); `csi2_regs`/`regs`/`pisp_regs` dumps are always there.
6. **Any late CFE node drops the frame**, not just the image buffer (`kernel cfe.c:615-631`).
7. **qbc fork comment vs code:** "the raw buffer is NOT rewritten" (`pisp.cpp:1640-1646@7e9fef0`) vs the in-place unwrap at `:2843-2852` and `ccmp_unwrap.h:43`. The software stats pass has no off switch.
8. **Cinemate tried O_DIRECT for four days** (June 2025) in a file since deleted, never in the live writer; its dirty-byte profiles carry no stated reason or measurement; its recorded drop causes are a second software render per frame, RAM-pool exhaustion on NTFS/FUSE, and app-level buffer starvation attributed to disk latency.
9. **Cinemate runs cinepi-raw at SCHED_FIFO 70 on CPUs 1-3**; its requested worker nice values fail with EPERM and do not matter. Core's only scheduling change is nice -5 on one thread.
10. **The two libcamera forks bound the pixel rate differently**: Cinemate's needs the env var (default 380 MPix/s); ours reads the RP1 clock from the device tree. Cinemate's `rp1_regime` mtime guard is a workaround we do not need.
11. **When a web client is attached, Core downsamples the preview on the completion thread** (`ApertarCoreApp.cpp:8184-8189`); the KB measurements had one WebUI client open.
12. **Core's media speed test** uses `fio --direct=1` and falls back to a buffered `dd conv=fdatasync` when fio is missing (`ApertarCoreApp.cpp:9036-9052`): running it while the camera is live is the Open-A stimulus.
13. **Core's `format_media` defaults to exFAT** (`ApertarCoreApp.cpp:10647`); if `/media/RAW` is exFAT, Cinemate's "ext4 drops less" observation and the O_DIRECT path (exFAT does support direct IO) both apply differently. `findmnt` first.
14. cinepi-raw's `encodeBufferDone` returns buffers in FIFO order on the assumption that encode workers finish in order (`cinepi_recorder.hpp:158-174`): when porting worker-side release, key the release on the buffer, not on order.

## Method and residual unknowns

Nine reader agents + nine adversarial verifiers + a completeness critic over the clones; all citations re-opened. Unknown and only measurable on the Pi: the SoC-level mechanism of A (fabric, IOMMU, IRQ), whether A2 contributes at all, the exact libcamera commit of the Pi binary, the actual `/media/RAW` filesystem and `sysctl vm.dirty_*` values, and the measured per-step gains of the B plan. Raw per-topic findings with their verification sections: `working/compare-raw/*.md`; running notes: `working/clearhdr-compare-notes.md`.
