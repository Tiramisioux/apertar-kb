## 8. Inspection (2026-11-02, cloud session): does the page-cache claim hold, and what to test next

Written from the desk (no Pi) after five examiner passes (statistics and design; kernel 6.12 `mm/` source; Core `adac040`
code; the six UI commits; co-factors) and a synthesis that re-read every disputed source line. This section replaces the
provisional 8.1-8.5 of the same date: three of its rows were wrong (the per-frame LRU drain marked "confirmed (source)",
the kswapd arithmetic at 4 KiB pages, and the `/proc/irq/154/smp_affinity` suggestion). Sources: sections 1-7 above,
`takes-2026-11-01.md` (79 rows) and the raw journal, `lessons/hardware-log.md` 2026-10-26/30/31 and 11-01, Core
`drop-frames` @ `adac040` (and `64bbbaa`, `a40112a`), UI `drop-frames` @ `c13b846`, kernel `raspberrypi/linux`
`rpi-6.12.y` @ `5bd564a` (`mm/`, `arch/arm64/configs/bcm2712_defconfig`, `drivers/media/platform/raspberrypi/rp1_cfe`,
`drivers/pci/controller/pcie-brcmstb.c`, `drivers/mfd/rp1.c`, `kernel/irq/msi.c`), cinemate `storage-automount.py`,
the imx585 driver `cd548ef`. Status words as in the KB: **confirmed** (read in source or measured), **measured** (numbers
real, reading not agreed), **probable** (inferred, reason given), **unconfirmed** (the measurement is named), **refuted**
(the source or the record says otherwise). The examiner reports are in the cloud session's scratchpad
(`inspection/statistics.md`, `kernel.md`, `core-code.md`, `ui-commits.md`, `cofactors.md`).

### 8.1 Verdict

**The fix is right. The stated mechanism is half right and half refuted. The proof is not finished.** `sync` mode does
what it should: after the once-a-second `fsync` the pages are clean, `posix_fadvise(DONTNEED)` evicts the whole file
(`mm/truncate.c:288-303`, `CameraController.cpp:4703-4712`), the cache never fills, kswapd stays nearly idle
(47-58 k pages per 3 min against 3.0-3.45 M; low-watermark hits 8-11 against 948-1805: **measured**, no overlap). The
`writer`-mode call frees nothing (**confirmed**, but for a different reason than stated: it first *starts* writeback of the
whole file, `mm/fadvise.c:113-115`, and the eviction walk then skips every folio under writeback, `mm/filemap.c:2121-2125`),
so the cache fills in about 6 s and the rest of the take runs at the low watermark with kswapd re-woken 5-10 times a
second (`mm/vmscan.c:7104-7119, 7161-7165`). The sentence "drains the per-CPU LRU lists on every core per frame" is
**refuted by source**: the drain branch needs `nr_failed > 0` (`mm/fadvise.c:166`), and under-writeback folios are never
returned to the caller, so they are never counted (`mm/truncate.c:521-531`); even if it ran, 25 drains/s of <= 200 us of
nice-0 kworker time each (`mm/swap.c:865-877`, `mm/vmstat.c:2179`) cannot make a 40 ms hole. What is **unproven**: that
the memory regime reaches libcamera's completion thread at all (nothing recorded names the stalled thread; the kernel
offers exactly one unbounded sleep for a user thread here, `throttle_direct_reclaim` below `min/2`, `mm/vmscan.c:6394,
6486-6487`, and it needs that thread to allocate a page); that `sync` beat `writer` by more than order and chance (every
writer take preceded every sync take; the exact take-level test gives one-sided p = 0.057, 0.029 with #80); and which of
#80's three changes carried its 0 of 15,025 (the two dirty sysctls are very probably inert for Core, `min_free_kbytes`
64 MiB is the probable active ingredient, and it is Apertar's own knob, not CineMate's). Two further points weaken the
claim as a *sole* cause: A0 (2026-10-30, the same per-frame DONTNEED hard-coded at `a40112a:CdngEncoder.cpp:1780`, UI
running, 10 min) lost 0 of 15,001, and A0 was not "early in its boot" (the UI had run since 01:04, A0 ran at 08:30:
`hardware-log.md:925-926`); and the UI stopped under `writer` was clean at any uptime (#5, #17, #59). The claim that can
hold is: **`writer` mode creates a standing reclaim regime, and the touch UI's drawing turns that regime into capture
gaps; `sync` removes the regime.** Who stalls, and why the UI matters, is the open mechanism.

| Part of the claim | Status | Basis |
| --- | --- | --- |
| `writer`-mode DONTNEED "frees nothing" | **confirmed** (source) | `mm/fadvise.c:113-115` starts `__filemap_fdatawrite_range(WB_SYNC_NONE)` on the whole file; `find_lock_entries` skips folios under writeback (`mm/filemap.c:2121-2125`); `mapping_evict_folio` refuses dirty/writeback ones (`mm/truncate.c:293-294`). Only pages whose I/O completed in the microseconds before the walk can go |
| "... and drains the per-CPU LRU lists on every core per frame" | **refuted** (source) | the branch at `mm/fadvise.c:166-170` needs `nr_failed > 0`; skipped folios are not returned, not deactivated, not counted (`mm/truncate.c:521-531`). Residual case: a folio whose I/O already completed and that still sits in a remote CPU's `lru_add` batch (elevated refcount): rare. Closing measurement: M1 in B1 (count `lru_add_drain_per_cpu` executions; the claim predicts ~1,500 per 60 s of `writer`, the source ~0 from Core) |
| the drain is what costs capture frames | **refuted** (arithmetic) | <= 200 us per CPU per drain, nice-0 kworker on `mm_percpu_wq` (`WQ_MEM_RECLAIM` only, `mm/vmstat.c:2179`), the caller does the waiting in `flush_work` (`mm/swap.c:876-877`), concurrent callers coalesce (`:830-840`); 25/s x 200 us = 0.5 % of CPU0 in sub-millisecond slices against a 40 ms symptom |
| the per-frame `sync_file_range` is redundant in `writer` mode | **confirmed** (mm) / **probable** (`fs/sync.c` not in checkout) | the fadvise already started writeback; the second call returns at `mm/filemap.c:393-395` (no dirty tag). Consequence: the 2026-10-30 A1/A2 reading ("the writeback hint is needed") is wrong for its stated reason; A2's 10 % is one unexplained run |
| the page cache fills and kswapd reclaims during the take | **confirmed** (measured), arithmetic corrected | `bcm2712_defconfig:50` `CONFIG_ARM64_16K_PAGES=y`: a page is 16 KiB on the `-2712` kernel (**probable** until `getconf PAGESIZE`). `pgsteal_kswapd` 3.02-3.45 M pages = **49-57 GB = 65-74 %** of the 75.5-76.2 GB a 3-min writer take writes (not 12-14 GB / 16-18 % as the provisional 8.1 computed at 4 KiB). 20-26 GB per take were freed by something else (direct reclaim and/or fadvise's partial frees): `allocstall_*`/`pgscan_direct` were printed by `take3.sh` and never recorded (**unconfirmed**) |
| kswapd re-woken before it can sleep | **confirmed** | `kswapd_low_wmark_hit_quickly` 948-1805 per take = re-woken 5-10 times/s within 100 ms (`HZ/10`, `mm/vmscan.c:7119, 7161-7165`); default watermarks min/low/high = 16/20/24 MiB (`mm/page_alloc.c:6125-6178`, `min_free_kbytes` 16384): low -> min is 4 MiB = **10 ms** of the 415 MB/s stream |
| the memory regime reaches the capture thread | **unconfirmed** | the only kernel mechanisms for a 40 ms stall of a user thread: direct reclaim (bounded, ms, `mm/page_alloc.c:4497`) and `throttle_direct_reclaim` (unbounded until kswapd refills, below `min/2` = 8 MiB, `mm/vmscan.c:6394, 6486-6487`; kernel threads exempt `:6430`). Both need the thread to allocate a page. Core's own per-frame work on that thread is ~3 small mallocs served from the arena (`CameraController.cpp:4033-4060, 3833-3838, 4979-4997`: **probable** no page faults); kernel-side allocations in its syscalls can (M4/M5/M6 in B1-B2) |
| the touch UI is "the last straw" | **probable** (conditional) | UI stopped: clean under `writer` (#5 0, #17 0, #59 2); UI running: clean under `sync` (#74 0, #75 0, #80 0). Its feed costs the completion thread only a ~200-byte descriptor per frame (`CameraController.cpp:10024-10072`, `ApertarCoreApp.cpp:8175-8221`; publisher thread non-blocking, `ControlServer.cpp:19-36`), so the UI's share is its GPU/display work under the regime, not a Core-side wait (the hand-off is already non-blocking) |
| `sync` vs `writer` is real, not chance | **measured, confounded by order** | frames: 259/18,013 (1.44 %) vs 25/24,037 (0.104 %), Fisher p = 8.6e-67, **invalid** (per-take counts 1, 34, 153, 71: variance/mean = 66). Takes: exact rank test 4 vs 3 one-sided p = **0.057** (two-sided 0.114); with #80 4 vs 4 p = 0.029 (0.057); arms overlap (#69 0.02 % < #78 0.17 %). Every writer take preceded every sync take; the Core restart at 22:46 and the audio meter at 23:00 are confounded with the arm; uptime and fill ran *against* sync |
| #80's dirty limits did it | **probable: no** | defaults give bg ~290-350 MB / hard ~580-700 MB; #80's set 256 MiB / 1 GiB (the hard limit *raised*); Core's peak `Dirty` was 11 MB (A0) and 3 MB (A1), far inside the freerun ceiling either way (`mm/page-writeback.c:377-446, 837-841, 1769`); `balance_dirty_pages` touches only the dirtying task (`:2144`), never the capture thread. 2026-10-26 measured the same pair 5 vs 5: no difference |
| `min_free_kbytes` 64 MiB did it | **probable: yes** | min/low/high 64/80/96 MiB: the kswapd band grows 4 MiB -> 16 MiB (10 -> 39 ms of stream), the throttle line 8 -> 32 MiB; #80's `kswapd_low_wmark_hit_quickly` = 0. B3 separates (c) from (b) |
| "early in the boot, empty cache" explains A0 and #69 | **refuted** (record) | A0 ran >= 7.4 h into its boot after the overnight drive test; the cache fills in ~6 s anyway (first kswapd wake 0.7 s from MemFree 300 MB, 6.6 s from 2.7 GB). A0 and #69 share only "first take of a freshly started Core process"; A1/A2 were also first takes of restarted Cores and A2 lost 10 %, so position alone protects nothing |
| the drift is monotone with uptime | **not supported** | within #69-#72 r = 0.65, p = 0.35 (n = 4, #72 < #71); boot 1's 19:09-21:03 baseline is flat (1.2 %/h, p = 0.25), the evening's rise is a **step** to 11-18 % at 22:06-22:19 on a freshly formatted 1-35 % drive (fill excluded as the cause) |

### 8.2 The five question groups

**Q1. `sync` vs `writer`: real or chance?** Suggestive, not settled, and confounded by order. The take is the unit (the
frame-level p-values assume independence that the data refute, dispersion 66). At the take level the evidence is 4 vs 3
(or 4 vs 4) with one-sided p 0.057 (0.029) and one overlapping take. The kernel counters are the strong part: they
separate 50-70x without overlap and prove the mode changed the kernel's reclaim behaviour; they do not prove that reclaim
caused the gaps. Confounders in the record: order (writer 22:28-22:43, sync 22:46-23:24), the Core restart at 22:46 (the
only other change between #72 and #74; in boot 1 a fresh Core at 22:15 did *not* help: #64 11.1 % after #62 18.1 %, n = 1),
the audio meter on from 23:00, #80's empty start cache (MemFree 2,758 MB). Uptime and fill ran against `sync` (the sync takes
were later and on a fuller drive), which helps the claim. What the night's own hypothesis cannot explain: #69 (writer,
1 min uptime, 1 lost): the cache fills in seconds, so what builds over 5-13 minutes is not identified (**unconfirmed**; B4).
The sound A/B is B1: interleaved, same boot, reboot per block, Core restarted and the arm written explicitly before
*every* take (Core prints nothing for a valid value, `CdngEncoder.cpp:86-93`; verify from `/proc/<MainPID>/environ`),
drive deleted and trimmed before every take, 8 takes in ABBA | BAAB with an extension rule. Power: 0 lost in 4,500 frames
(3 min) bounds the rate below 0.067 %, in 15,000 (10 min) below 0.02 %; telling 0.17 % from 0.05 % needs ~12,000 frames
per arm at 80 % power under independence; take-level complete separation 4 vs 4 gives two-sided p = 0.029, 6 vs 6 0.0022.
At the 11-01 effect size (65 vs 4.7 expected events per 3-min take) 3-minute takes separate the arms; the residual-rate
question needs 10-minute takes (B3, B6).

**Q2. #80 changed two things.** Three, plus a fourth: the dirty limits, `min_free_kbytes` 16 -> 64 MiB (a different knob,
Apertar's own: cinemate's automounter sets only `dirty_*` and `dirty_writeback/expire_centisecs`,
`storage-automount.py:111-112, 319-335`; Core's `apertar-media-tune` likewise, `scripts/apertar-media-tune:73-100`), the
drive (formatted 23:13: empty and trimmed), and the starting cache (MemFree 2,758 MB from the format's deletes). The
dirty pair is very probably inert for Core (8.1); `min_free_kbytes` is the probable active ingredient; the empty cache is
worth ~6 s. On fill: fill losses on this rig have always been **queue-full** (2026-10-26, 77-81 %: 166-676 drops); #78's 18
last-minute losses were **capture gaps with `peak_queue=2/12`**, so "the drive slowed" is contradicted. #78's minute 10 is
a regime change (minutes 1-9 flat at 0.78/min, P(>= 18 | 0.78) < 1e-12) at 94-97 % fill and ~0.9-1.0 TB written since the
21:50 format (the 10-30 NAND stall zone, but without that stall's queue-full signature); per-minute reclaim in #78 was 3x
that of #74/#75 (59 k vs 16-19 k pages/min). Fill as exFAT near-full allocation work (bitmap/FAT reads = more allocation
under a tight regime) remains a plausible *amplifier*; filesystem fill, NAND state and the sysctls are separable because
fill can be set without writing NAND (`fallocate`) and NAND can be written without filling (write, `rm` without a Core/UI
delete, `APERTAR_MEDIA_TRIM=0`): B3. One record check first: the no-deletion frame sum puts #78's end at 1,043 GB on a
932 GB drive against the reported 97 %, so ~140 GB were deleted between 21:50 and 23:02 and a Core/UI delete >= 1 GiB trims
(`ApertarCoreApp.cpp:10856-10861, 11386-11433`): `journalctl -u apertar-core -b -1 | grep -E 'media: trim|delete'` says
whether #78 ran on clean NAND.

**Q3. Which UI conclusions survive?** For target 1, none is needed: the unmodified GPU preview with peaking and zebra on
was clean under `sync` (#74 0/4,505, #75 0/4,509, #80 0/15,025). Every UI A/B of 19:46-22:20 was taken under the `writer`
regime that drifted from 7 % to 18 %, without a same-time control; the plane series contradicts itself (plane with aids
off 7.22 %, #58, worse than plane with aids on 1.8-3.4 %, #47-#50; render 0.7 ms yet losses continued, #60), which is
what a drifting regime looks like. `fast` peaking gave no gain even in its own regime (8.83 %, #34). `PREVIEW_DIRECT` is a
confirmed no-op on this rig (`main.cpp:179` already sets direct rendering on the external-monitor renderer; `:438-439`
hides the main window). The bandwidth arithmetic does not support "the GPU saturates the bus": the display stack is
~1 GB/s of a ~17 GB/s LPDDR4X bus, the plane saves ~0.5 GB/s (**probable**, from the formats). Nothing in
`ea44bd7..c13b846` (13 commits) adds per-camera-frame work on the default path beyond a handful of GL calls; the one new
periodic item is `841d0ed`'s buffer-bar `Behavior` animation that runs even with the bar hidden (`StatusChip.qml:104-107`,
`ExternalMonitorWindow.qml:1121-1125`), bounded by the measured 29 redraws/s to a few extra redraws a second. The robust
UI finding is conditional: UI drawing + `writer` regime = losses; UI stopped or frozen = none; UI drawing + `sync` = none.
Decisions in 8.4; U1 closes the "regression since A0 in the UI" reading in 35 minutes.

**Q4. Is the mechanism right, and the cheapest direct measurement?** Half right (8.1). The two halves that are
measured (cache fills, kswapd full-time) are correct; the per-frame drain is refuted by source and does not need a
measurement, but one 60 s tracefs count closes it for good (M1). The question that matters is **which thread stalls and
how**. The kernel offers four candidates that fit the data equally (A: the capture thread allocates a page below `min` and
reclaims or sleeps in `throttle_direct_reclaim`; B: the UI's render thread stalls the same way and Core waits on it
(unlikely: the hand-off is non-blocking); C: run-queue competition on CPU0 with a full-time nice-0 kswapd (`SCHED_FIFO 40`
did not help, #22, which argues against); E: a CFE node other than the raw one starves, so the real requeue deadline is
one frame period). Measurements, cheapest first, all folded into B0-B2:

| # | Measurement | Settles | Cost |
| --- | --- | --- | --- |
| M0 | `getconf PAGESIZE`; `zgrep` on `/proc/config.gz`; `/proc/zoneinfo` watermarks; `nr_dirty_threshold`; `/proc/pressure/memory` | every byte figure (16 vs 4 KiB), MGLRU, PSI, kprobes availability, the real low-min band, the inert dirty thresholds | 10 s, no take |
| M2 | copy `pgscan_direct`, `allocstall_normal`, `allocstall_movable` deltas of #70-#80 from the Mac transcript (`take3.sh` printed them) | whether `writer` was a direct-reclaim regime (who freed the 20-26 GB kswapd did not) | no take |
| M4 | tracefs `vmscan:mm_vmscan_direct_reclaim_begin/_end`, `mm_vmscan_throttled`, `kswapd_wake/_sleep`; awk per comm-pid; add `pgscan_direct_throttle` to the per-minute keys | **the stalled thread**: `CameraManager` in `_begin` with >= 20 ms episodes = A; `pgscan_direct_throttle` > 0 = the unbounded sleep happened; only writers = elsewhere | one take, no packages |
| M5 | `/proc/<core pid>/task/<CameraManager tid>/schedstat` at 1 Hz (field 2 = run-queue wait ns) | a second with a lost frame and >= 40 ms of wait = C; a lost frame with no wait growth = the thread was asleep (A, B or E) | shell loop, any take |
| M1 | tracefs `workqueue:workqueue_execute_start`, `grep -c lru_add_drain_per_cpu` over 60 s, `writer` then `sync` | the drain claim: ~1,500 per 60 s = the claim; ~0 (or equal small counts from kcompactd under both) = refuted | 2 x 60 s windows |
| M6 | `perf sched record -a -- sleep 60`; `perf sched timehist -p <tid>` and `--cpu 0`; `perf record -e sched:sched_switch -g -t <tid>` for the sleep stack | the 40 ms hole itself: sleeping vs waiting, and the call chain (`try_to_free_pages`/`throttle_direct_reclaim` = A; `sendmsg`/`futex` = B; kswapd on CPU0 during a wait = C; a V4L2 wait = E) | one take, `linux-perf` (apt) |
| M3 | tracefs `events/vb2`, `events/v4l2`; per video node (`media-ctl -p`) holes in `vb2_buf_done` sequence numbers and the last `vb2_qbuf` per node before each hole | where the frame dies: a node with zero queued buffers at the hole = E and names the late thread; a hole on all nodes with buffers queued everywhere = sensor/link (F) | one 60 s take |
| M7 | `psi=1` on the cmdline, reboot; `/proc/pressure/memory` `some`/`full` total at 1 Hz | system-wide memory-stall time per second (does not name the thread) | one reboot (`bcm2712_defconfig:17-18` `CONFIG_PSI_DEFAULT_DISABLED=y`) |

Not available on this kernel: `rp1_cfe` dynamic debug ("has no buffer, unable to schedule job" is a `dev_dbg` behind
`verbose_debug`, `cfe.c:52-61`; no `CONFIG_DYNAMIC_DEBUG` in the defconfig, as the 2026-10-26 entry found), and
probably `perf probe`/kprobes (no `CONFIG_KPROBES` line in the defconfig; **unconfirmed**, M0 says). Tracepoints work.

**Q5. What was not considered.**

| Item | Finding | Status | Test |
| --- | --- | --- | --- |
| Why A0 was clean | not boot age (refuted, 8.1). Four things changed between A0 and 11-01 under the same `writer` path: Core `a40112a` -> `64bbbaa` (warm raw pool kept through the take, one 16.9 MB `write()`, RAM buffer, pre-roll, trim), UI `ea44bd7` -> `c13b846`, the **imx585 driver** `24172e6` -> `cd548ef` installed 11-01 (3,637 insertions, new mode tables; `hardware-log.md:899-906`), drive handling (A0 cooled to 34 C, no back-to-back takes). The 10-31 losses on the old driver with the WebUI open show the driver is not necessary for losses. No take isolates any one of them | **confirmed** (record) | T1 (A0's protocol on today's stack, first 10-min take after a reboot, `buffer=frames`), then T2 bisect only if T1 loses from minute 1 |
| The RAM write buffer | every 11-01 take, writer and sync, ran with `queue_budget=1.40-1.70 GB` (raw journal lines 335-388), a mode A0 never had; `peak_queue=2/12` throughout. From the budget formula (0.6 x MemAvailable - 512 MiB) MemAvailable at take start was 3.2-3.5 GB in **every** take: the arms differed in MemFree, not in what the kernel counted available | **measured** / **probable** (formula) | not the discriminator; T1 runs `frames`; T3 (frames vs ram interleaved) only if T1/B4 point at it |
| CSI-2 at 1782 Mbps | the D-PHY programs the 1500 Mbps calibration bin and keeps streaming (`dphy.c:99-128`); link errors (LEN/UNMATCHED discards) cannot correlate with memory or UI state; only a receiver FIFO **overflow** (OVLF, `csi2.c:79-80, 219-258`) could. `csi2_errors` needs `rp1_cfe.track_csi2_errors=1` at boot (perm 0, `csi2.c:19-21`), **zeroes on read** (`:189-192`), was all-zero under `dd` loads on 2026-10-26 and has never been read during a losing take. Control at 720 MHz (1440 Mbps, in spec) gives 4K Clear HDR 16-bit exactly 25.0 fps (HMAX 660 vs 550, `imx585.c:287-302`; Clear HDR halves the rate) with zero margin | **confirmed** (source) / **unconfirmed** (rig) | read `csi2_errors` before and after every losing take once the flag is on (B0's reboot); the 1440 pair only if OVLF > 0 |
| CPU0 interrupts | rp1-cfe (154), USB, I2C and (probably) the NVMe queues **cannot be moved from user space**: RP1 children forward affinity to the brcmstb MSI domain (`rp1.c:144-157`) declared `MSI_FLAG_NO_AFFINITY` with no `irq_set_affinity` on the bottom chip (`pcie-brcmstb.c:664-674, 720-724`); `msi_domain_set_affinity` calls the missing handler unconditionally (`msi.c:663-670`). **Do not write `/proc/irq/154/smp_affinity`** (the provisional 8.2 suggested it: withdrawn). Movable: v3d (done, no gain), libcamera's thread (`taskset`), the NeoRotary poll | **confirmed** (source) | `taskset -pc 1 <CameraManager tid>` for one losing take (B5) |
| NeoRotary 4 poll (~570 I2C IRQs/s on CPU0) | microseconds each, no memory interaction; low prior | **unconfirmed** | unplug or `poll_ms=1000` for one losing take (B5) |
| WebUI preview | a genuine completion-thread cost while a browser is attached: 1280x720 -> 640x360 downsample on libcamera's thread (`ApertarCoreApp.cpp:9730-9820`; encode on `mjpegThread_` `:9833-9880`); magnitude inconsistent in the record (#61 open 14.3 % vs #62 closed 18.1 %); no compared take (#69-#80, A0) had a client | **confirmed** (cost) / **measured** (magnitude unclear) | keep the "no client on :8000" rule as a confound control |
| Page size, PSI, dynamic debug | 16 KiB pages (`bcm2712_defconfig:50`), MGLRU on (`:95`; direct reclaimers never sleep in `reclaim_throttle`, `mm/vmscan.c:5959-5962`), PSI compiled but disabled (`:17-18`), no dynamic debug or kprobes in the defconfig | **probable** until M0 | M0 |
| Which heap holds the raw buffers | `allocateCachedBuffers` tries `vidbuf_cached`, then `linux,cma`, else libcamera's allocator (`CameraController.cpp:8661-8691`); with CmaTotal 64 MB the 8 x 16.9 MB cannot be CMA, so the fallback is probably in effect (fragmentation contributor) | **unconfirmed** | `journalctl -u apertar-core -b \| grep -E 'RAW buffers\|cached DMA'` (B0) |
| Within-boot state other than page cache | slab (exFAT inodes/dentries: 15,000 files per 10-min take; FAT ~29 MB of buffer heads), swap (89 MB in use on 2026-10-26), fragmentation (no order >= 8 free at the end of boot 1; kcompactd equally busy in clean takes), Core/UI RSS; none recorded on 11-01 | **unconfirmed** | B4 rows: `Slab SReclaimable SUnreclaim Buffers`, `pswpin pswpout`, `VmSwap VmRSS` of Core and UI, `/proc/buddyinfo`, `slabinfo` for `exfat\|buffer_head\|dentry` |

### 8.3 Test plan (in order; Patrik runs `sudo`; nothing else on the Pi; WebUI closed; 3- or 10-minute takes with per-minute counts; delete the clip and `fstrim` between takes; restore Patrik's ladder after each take)

Overview (details below the table; about 9-10 hours of Pi time over three or four evenings; B1 and B3 are the two that decide):

| # | Test | Question | Takes | Duration |
| --- | --- | --- | --- | --- |
| B0 | Prerequisites and record checks | facts that fix every number (page size, watermarks, PSI); the transcript's reclaim deltas; build `adac040` with a self-describing journal line; the take script; one reboot for `psi=1` + `rp1_cfe.track_csi2_errors=1` | none | ~1 h incl. the build |
| B1 | Interleaved A/B `writer` vs `sync` with the stall-thread trace on every take | is the mode the lever, and who stalls under `writer`? | 8 x 3 min (ABBA \| BAAB, reboot per block), extension to 12 | ~75 min (+40 min if extended) |
| B2 | The hole itself (only if B1's M4/M5 did not name the thread) | sleeping or waiting, and the sleep stack; which CFE node starves | 1-2 x 3 min `writer` | ~25 min |
| B3 | Separate #80's changes and the drive's state | which of `min_free_kbytes`, the dirty pair, fill, NAND state carried #78's tail and #80's 0 | 6 x 10 min, two fills | ~3 h (split over two evenings if needed) |
| B4 + T1 | Within-boot state under `writer`, starting with A0's protocol | regression since A0 or drift; what builds between takes | 4 x 10 min, one boot | ~55 min |
| U1 (+U2) | UI branch `ea44bd7` vs `c13b846` under `sync` | does the UI branch cost anything once the regime is gone? | 6 x 3 min + 2 x 20 s | ~40 min |
| B5 | Co-factors (only if losses survive B1-B3 under `sync`, or to close B1's `writer` mechanism) | CSI-2 overflow, CPU0 placement, NeoRotary, the 1440 Mbps control | 1-4 x 3-10 min | 1-1.5 h |
| B6 | Done-means | target 1 with the final configuration on two boots | 2 x 10 min | ~30 min |
| B7 | Target 2 | 4K SDR 12-bit at 33 fps, lossless and uncompressed | 2 x 10 min | ~30 min |
| B8 / U3 | UI switches under `sync` (only if B6/U1 show UI-correlated loss) | do any of the parked mitigations still measure anything? | pairs of 3 min | 25-50 min |
| B-lossy | Lossy DNG under the default | does `off`-like behaviour cost frames? | 1 x 10 min | ~15 min |

**B0. Prerequisites (no take).**

1. Facts (10 s, Patrik pastes the output into section 2): `getconf PAGESIZE`;
   `zgrep -E 'CONFIG_(ARM64_16K_PAGES|LRU_GEN_ENABLED|PSI|PSI_DEFAULT_DISABLED|HZ|KPROBES|KPROBE_EVENTS|FUNCTION_TRACER|DYNAMIC_DEBUG|SCHEDSTATS)=' /proc/config.gz`;
   `grep -E '^(Node|  *(min|low|high|boost|managed))' /proc/zoneinfo`; `grep -E 'nr_dirty_(background_)?threshold' /proc/vmstat`;
   `cat /proc/pressure/memory /proc/cmdline`; `cat /proc/sys/vm/{min_free_kbytes,dirty_ratio,dirty_bytes,dirty_background_bytes}`
   (stock after a reboot). Reading: PAGESIZE 16384 confirms the 65-74 % kswapd share and every byte figure in 8.1; 4096 means
   divide by four and the provisional 16-18 % stands. The zoneinfo `low` - `min` sum in MiB is the headroom before direct
   reclaim; use it to size `min_free_kbytes`. An empty `/proc/pressure/memory` means M7 needs the reboot below.
2. Record checks (1 min): `journalctl -u apertar-core -b -1 --no-pager | grep -E 'media: trim|delete'` (a `result=trimmed`
   line between 21:51 and 23:01 means #78 ran on clean NAND); `journalctl -u apertar-core -b | grep -E 'RAW buffers|cached DMA'`
   (which heap holds the raw buffers); `git -C ~/ApertarUI-a0 log -1 --oneline` (which commit the A0-era worktree holds:
   `1cf98ad` is not in the Mac clone, `ea44bd7` is the last branch commit before A0); `ls /etc/systemd/system/apertar-core.service.d/`
   (`zzz-ab-buffers.conf` must be gone; `capture-priority.conf` with `LimitRTPRIO=80` is harmless).
3. Transcript (M2, no take): copy the `compaction during take:` deltas of `take3.sh` for #70-#80 (`pgscan_direct`,
   `allocstall_normal`, `allocstall_movable`, `pgsteal_kswapd`) from the 2026-11-01 Mac session into section 2.
   Reading: `allocstall_*` in the thousands and `pgscan_direct` in the millions under `writer` = a standing direct-reclaim
   regime (allocators reclaimed for themselves); ~0 under `writer` = all freeing was kswapd plus fadvise's partial frees and
   the stall must be C, E or a UI effect; ~0 under `sync` as expected.
4. Code before the A/B (Patrik decides; one commit, one build, never during a take): add `dontneed=`, `writeback=`, `sync_ms=`
   to the "recording clip:" journal line (`CameraController.cpp:4346-4356`, after `media_fs=`; three `<<` operators) so
   every take is self-describing (the journal never records the mode today: `git grep -i dontneed adac040 -- src`). Then
   `cmake --build ~/ApertarCore-build -j2` of `adac040`(+1), remove `/run/systemd/system/apertar-core.service.d/dontneed.conf`,
   restart, confirm the knob line says `sync`.
5. Script `take3v3.sh` (from `take3v2.sh`): add `pgsteal_direct pgscan_direct_throttle pswpin pswpout` to `KEYS`; before each
   take print `Slab SReclaimable SUnreclaim Buffers` from `/proc/meminfo`, `VmSwap`/`VmRSS` of Core and the UI, `df /media/RAW`,
   `uptime -p`, SoC and NVMe temperature (`/sys/class/nvme/nvme0/device/hwmon*/temp1_input`; start only below 55 C), the arm
   from `tr '\0' '\n' < /proc/$(systemctl show apertar-core -p MainPID --value)/environ | grep APERTAR_DNG_DONTNEED`; a 1 Hz
   background log to `/dev/shm/take-N.log` (never to `/media/RAW`) of the `KEYS` counters, `MemFree Dirty Writeback`,
   `/proc/pressure/memory` and `io` if present, field 8 of `/sys/block/nvme0n1/stat` (write ticks: its per-second delta over
   the write-count delta is the mean write latency), and `/proc/<core pid>/task/<CameraManager tid>/schedstat` (M5);
   `recording_dropped_frames` every 10 s (60 points per 10-min take); `csi2_errors` read once before `record_start`
   (discarded) and once after `record_stop` when the flag is on; `sudo dmesg | grep -c Orphanded` before and after.
6. Packages: `sudo apt install linux-perf` (M6; `trace-cmd` optional, tracefs suffices for M1/M3/M4).
7. One reboot (Patrik): append `psi=1 rp1_cfe.track_csi2_errors=1` to `/boot/firmware/cmdline.txt`. Both are harmless and
   make M7 and the CSI-2 reading available for the whole campaign. The reboot also resets the hand `sysctl` to stock.

**B1. Interleaved A/B `writer` vs `sync` (the claim's core), with the stall trace on every take.**

- Question: with the UI drawing (peaking + zebra on, audio meter in one fixed state for all takes: write which), does
  `APERTAR_DNG_DONTNEED=writer` lose more frames at capture than `sync`, on the same boot, in alternating order, with the drive
  reset before every take; and under `writer`, which thread enters reclaim or waits?
- Fixed: Core `adac040` build, mode set *explicitly* by the `/run` drop-in in **both** arms (`Environment=APERTAR_DNG_DONTNEED=<writer|sync>`),
  `APERTAR_MEDIA_SYNC_MS` default 1000 (the sync thread carries the drop, `CameraController.cpp:4320-4323`), `APERTAR_DNG_WRITEBACK`
  default on, stock sysctl (`min_free_kbytes` 16384, ratios 20/10: the limits are B3's factor), `[storage] buffer=frames`, UI
  `c13b846` with no switch, 4K Clear HDR 16-bit uncompressed 25 fps, ladder off for the take (the script does it), WebUI closed,
  no build (checked before and after).
- Order: toss a coin for which mode is A. Block 1: A B B A. Block 2: B A A B. **Reboot before each block** (each arm gets one
  first-after-boot position; ABBA/BAAB cancels a linear drift within a block).
- Before **every** take, both arms, in this order: `rm -rf /media/RAW/cDNG_*` then `sudo fstrim -v /media/RAW` (Core's own trim
  runs only on deletes it sees); write the drop-in, `sudo systemctl daemon-reload && sudo systemctl restart apertar-core`
  (restart in both arms so the restart is not confounded with the arm, as it was on 11-01); wait for the pre-roll; verify the
  arm from `/proc/<MainPID>/environ`; record meminfo, `df`, `uptime`, temperatures (NVMe < 55 C), `ss -tnH state established '( sport = :8000 )' | wc -l` = 0,
  no `cc1plus|gmake|cmake`. Do not `drop_caches` (the delete already frees the clip's pages; shooting never has that step).
- Trace on every take (tracefs, no packages; `S=/sys/kernel/tracing`): `echo 65536 > $S/buffer_size_kb`; enable
  `events/vmscan/mm_vmscan_direct_reclaim_begin`, `_end`, `mm_vmscan_throttled`, `mm_vmscan_kswapd_wake`, `mm_vmscan_kswapd_sleep`;
  after the take `awk '/direct_reclaim_begin/{c[$1]++} END{for(k in c) print c[k], k}' $S/trace | sort -rn | head` and pair
  begin/end per pid for durations (M4). The 1 Hz `schedstat` log is M5. On one `writer` and one `sync` take add
  `events/workqueue/workqueue_execute_start` for a 60 s window and `grep -c lru_add_drain_per_cpu $S/trace` (M1).
- Takes: 3 minutes (`take3v3.sh 180`). At the 11-01 rates a 3-min take expects 65 (writer) vs 4.7 (sync) events, enough for
  the mode contrast; it cannot bound the residual (that is B3/B6). Upgrade to 10-min takes (8 x 15 min = 2 h 10 min with the
  reboots) only if a residual bound is wanted in the same evening.
- Duration: per take ~8 min (drop-in + restart + pre-roll 1, set-up 0.5, record 3, stats 0.3, delete + trim 1-2, cool-down 1-2);
  8 takes + 2 reboots = **about 75 min**; a 4-take extension adds ~40 min.
- Decision rule (fixed in advance): exact one-sided permutation test on per-take lost counts after 8 takes.
  **Complete separation** (p = 0.014 one-sided / 0.029 two-sided) **and** `pgsteal_kswapd` >= 10x higher in `writer`: stop,
  the mode is the lever; the claim's effect holds. **One overlapping take** (a writer take <= the best sync take or a sync take
  >= the worst writer take): add one block A B A B after a reboot (6 vs 6: complete separation p = 0.0022) and report the
  overlapping take with its counters (a clean writer take with 3 M `pgsteal` says reclaim alone does not lose frames).
  **No separation** (or both arms clean): the 11-01 difference was order, the Core restart or chance; keep `sync` for the
  lower reclaim alone and go to B4/T1 for what the losses are. **`pgsteal_kswapd` does not separate**: the drop-in did not
  take, the run is void. Secondary (M4/M5, read per losing take): `CameraManager` in `direct_reclaim_begin` with episodes
  >= 20 ms or `pgscan_direct_throttle` > 0 while it has no `_begin` line = mechanism A (the memory regime reaches the capture
  thread; `min_free_kbytes` is the right kernel-side guard beside `sync`); only writer threads and `Apertar-UI` reclaim = look
  at the UI's GEM allocations and at B2; `schedstat` wait growing by >= 40 ms in a losing second = C (then one take with
  `sudo taskset -pc 3 $(pgrep kswapd0)`); neither = B2/M3 for the CFE node. M1 ~1,500 per 60 s under `writer` = the drain
  exists after all (8.1 row 2 would be wrong); ~0, or the same small count from kcompactd under both = strike the drain from the
  mechanism, the README knob text and upstream issue #44.

**B2. The hole itself (only if B1's M4/M5 did not name the thread).**

- Setup: one 3-min `writer` take as in B1; during a losing minute `sudo perf sched record -a -- sleep 60`; afterwards
  `sudo perf sched timehist -p <CameraManager tid>` (look for a gap >= 40 ms and whether it is `sleep` or `wait`) and
  `sudo perf sched timehist --cpu 0` (what ran on CPU0 in that gap). For the sleep stack: `sudo perf record -e sched:sched_switch -g -t <tid> -- sleep 60; sudo perf script | grep -B1 -A12 'prev_state=[SD]'`.
  If the thread is neither reclaiming nor waiting: a second take with `events/vb2` and `events/v4l2` enabled (M3), then per
  video node (`media-ctl -p` maps minors to `csi2_ch0`, `fe_image0`, `fe_stats`, `fe_config`) list `vb2_buf_done` sequence
  holes and the last `vb2_qbuf` per node before each hole.
- Duration: ~25 min.
- Decision rule: chain through `try_to_free_pages`/`throttle_direct_reclaim` = A. Through `sendmsg`/`write`/`futex` toward the
  UI feed = B (a Core-side fix: check `enqueuePreviewFrame`'s mutex, `ApertarCoreApp.cpp:8175-8221`). A 40 ms `wait` with
  kswapd/kworker on CPU0 = C (pin kswapd or the capture thread for one take). A node with zero queued buffers at the hole = E
  and the thread late to `qbuf` it is the one that stalled. Holes on all nodes with buffers queued everywhere = sensor/link (B5).

**B3. Separate #80's changes from the drive's state.**

- Question: which of `sync` alone, `min_free_kbytes` 64 MiB, the dirty pair, filesystem fill and NAND state carried #78's
  18-in-the-last-minute and #80's 0 of 15,025?
- Common: `sync` mode (default of the `adac040` build, no drop-in), Core restarted and the arm verified before each cell, UI
  drawing as in B1, 10-minute takes with `take3v3.sh 600`, per-minute `Dirty` peak and `nr_dirty_threshold` recorded, the 1 Hz
  NVMe write latency log (a near-full or untrimmed drive should show it; a memory effect should not). Sysctl set by hand for
  the cell and reset to stock after (`sudo sysctl vm.min_free_kbytes=16384 vm.dirty_bytes=0 vm.dirty_background_bytes=0 vm.dirty_ratio=20 vm.dirty_background_ratio=10`).

| Cell | Sysctl | FS fill at start | NAND | Replicates | What the result means |
| --- | --- | --- | --- | --- | --- |
| (a) = F0 | stock | empty | trimmed | #74/#75 at 10 min | **clean** (<= 5, no minute >= 3, flat): #78's 18 were the drive's state. 20+ spread evenly: a `sync` residual exists on its own |
| (c) | `min_free_kbytes=65536` only | empty | trimmed | #80 minus the dirty pair | clean where (a) was not: `min_free` is the knob to make permanent |
| (b) | `dirty_bytes=1073741824 dirty_background_bytes=268435456` only (ratios 0) | empty | trimmed | #80 minus `min_free` | `Dirty` peak stays in the tens of MB and the result equals (a): the dirty pair is inert, as the source says; cleaner than (a): the report's dirty-limit reading is wrong somewhere (check `nr_dirty_threshold` and the per-minute `Dirty`) |
| (d) = F3 | all three of #80 | 70 % (`sudo fallocate -l 650G /media/RAW/fill.bin`; if exFAT refuses, `dd if=/dev/zero of=/media/RAW/fill.bin bs=16M count=40000 oflag=direct` ~20 min then `fstrim`) | trimmed | #80's knobs in #78's drive state | clean through 97 %: the limits cure the near-full regime (make them permanent). Minutes 9-10 spike with rising NVMe write latency: fill beats the limits; cap the usable fill or set a format policy |
| (e) = F1 | stock | 70 % as (d) | trimmed | #78's drive state without knobs | spike in minutes 9-10: exFAT near-full cost (or the residual grows with fill); flat: filesystem fill is innocent |
| (f) = F2 | stock | empty | **>= 0.9 TB written since the last trim, then `rm` (not through Core or the UI), with `Environment=APERTAR_MEDIA_TRIM=0` in the drop-in so the pre-roll delete does not trim; verify no `media: trim` line** | the 10-30 stall zone under Core | losses with rising NVMe latency and/or queue growth: the NAND effect reaches capture through writeback; Core's trim policy must also cover `rm` deletes. Clean: Core's auto-trim is enough and the 10-30 stall needs the old write path |

- Order: (a), (c), (b), (d), (e), (f); (f) last because its preparation writes 0.9 TB and leaves the drive untrimmed; format
  afterwards (a format also trims). Repeat any cell whose reading would change a decision ((c) and (d) above all) before acting.
- Duration: 6 x 15 min + the fills (seconds with `fallocate`, 2 x 20 min with `dd`) + ~30 min of writing for (f):
  **about 3 h**; natural split: (a)-(c) one evening, (d)-(f) the next.
- Decision rule, summary: "clean" = <= 5 lost and no minute >= 3; "near-full effect" = minutes 9-10 carry > 60 % of the losses
  with the NVMe write latency rising in the same minutes; "memory effect" = losses spread across minutes with `pgsteal`/
  `allocstall`/PSI deltas and flat drive latency. (c) clean and (b) not (or (b) = (a)): add only `min_free_kbytes` to
  `apertar-media-tune` and make `APERTAR_MEDIA_TUNE=1` the install default. Both (b) and (c) clean with (a) clean too: the
  knobs are optional at low fill; (d) decides whether they are needed near full. (a) itself clean at 10 min: the 25 of #78
  were fill/NAND, not a `sync` residual.

**B4 + T1. Within-boot state under `writer`, starting with A0's protocol.**

- Question: was A0 clean because of its position (first take of a process/boot) or has the stack regressed since `a40112a`;
  and what builds across takes on one boot under `writer`?
- Setup: reboot; `sudo fstrim -v /media/RAW`; drive <= 55 C; `[storage] buffer=frames` (A0 had no RAM mode);
  `APERTAR_DNG_DONTNEED=writer` via the `/run` drop-in, Core restarted, arm verified; UI `c13b846` running, peaking + zebra on;
  WebUI closed. **T1 = the first take of the boot, 10 min** (`take3v3.sh 600`). Then **two more 10-min takes without deleting**
  (B4), then `echo 3 | sudo tee /proc/sys/vm/drop_caches` and a fourth. Before every take record `MemFree Cached Slab SReclaimable SUnreclaim Buffers`,
  `pswpin pswpout`, `VmSwap VmRSS` of Core and the UI, `cat /proc/buddyinfo`, `sudo grep -E 'exfat|buffer_head|dentry' /proc/slabinfo`.
  Delete + trim + format after the fourth take (the drive will be at ~100 %: watch `df` and stop the third take early if needed).
- Duration: ~55 min (reboot, 4 x 10 min, stats).
- Decision rule: T1 **0-2 lost**: A0's cleanness was its position and the problem is the within-boot drift (the "regression
  since A0" reading of the 2026-11-01 hardware-log entry is closed); the B4 takes then say what carries it. T1 **losing from
  minute 1 at the 11-01 rate** (>= 10 per 3 min): a code or driver change since A0 shifted the regime: T2 bisect (same protocol,
  one change per run, cheapest first: (a) the A0-era UI worktree, hash verified; (b) Core `a40112a` built into a second build
  dir with today's UI, 20-30 min build, never during a take; (c) driver `24172e6` via `setup.sh` and a reboot); the first clean
  arm names the side. B4: losses only from the second take and the fourth clean after `drop_caches` = reclaimable state (page
  cache or slab) carries it; the fourth still loses with `VmSwap`/`pswpin` rising = swap is the term; with `buddyinfo` degraded
  and RSS flat = fragmentation; with RSS growing = process growth. Optional T3 afterwards: four 3-min `writer` takes
  frames/ram/frames/ram (edit `[storage] buffer`, Core restart between); a difference larger than the 11-01 writer spread
  (34-153 per 3 min) keeps buffer mode in the matrix, otherwise drop it.

**U1 (+U2). The UI branch under `sync`.**

- Question: does `ea44bd7..c13b846` (13 commits, all switches off) cost any frames under `sync` compared with the A0-era UI?
- Setup: Core `adac040` default (`sync`), no drop-in; sysctl the same for every take (stock, or the B3 winner); drive trimmed
  and below 50 %; WebUI closed; peaking + zebra on; audio meter as Patrik runs it; `buffer=frames`. Old UI in a worktree
  (`git -C ~/ApertarUI worktree add ~/ApertarUI-a0 ea44bd7` unless B0's check shows it already is), built outside takes;
  switch the service's `ExecStart` with a `/run` drop-in + `systemctl restart apertar-ui-direct`. Order c13b846, ea44bd7,
  c13b846, ea44bd7, 3 min each; then one pair in `ram` mode (the 19:09 regime, where the bar level changes every 250 ms).
  `pidstat -p <ui pid> 1` during each take. U2: `QSG_RENDER_TIMING=1` on the UI service for one 20 s `ram`-mode take per build
  (not counted for losses); count frames logged per second.
- Duration: ~40 min.
- Decision rule: both arms 0 (or <= 1 per 9,000 frames; 0/9,000 bounds the rate below 0.033 %): the UI branch adds nothing
  measurable under `sync`; the keep/revert decision stands on code grounds. `ea44bd7` clean and `c13b846` >= 3 lost in both its
  takes: something in the branch costs; split with a build at `41ff827` (before the six switch commits) and apply the
  `Behavior { enabled: bufferBarVisible }` fix first. Both arms lose: the UI is not the variable, back to B1-B4. U2: 25-30
  frames/s = the preview drives the redraws and the animation is irrelevant; 50-60 on `c13b846` only = the invisible animation
  runs continuously; apply the fix in `StatusChip.qml` and `ExternalMonitorWindow.qml` and re-run U1.

**B5. Co-factors (only if losses survive B1-B3 under `sync`, or to close the `writer` mechanism after B1).**

| Test | Setup | Duration | Decision rule |
| --- | --- | --- | --- |
| CSI-2 receiver | the flag from B0's reboot; one losing `writer` take; `sudo cat /sys/kernel/debug/rp1-cfe*/csi2_errors` right before `record_start` (discard) and right after `record_stop` (the file zeroes on read); `sudo dmesg \| grep -c Orphanded` before/after | 10 min | `Overflows`/`OVLF` > 0 and comparable to the gap count: receiver starvation at the memory bus is a co-cause: run the 1440 pair. `LEN`/`UNMATCHED` > 0: link corruption, lower the rate regardless. All zero while frames are lost: the loss is behind the receiver (the CFE job not scheduled: libcamera/Core late), the link is out |
| 1440 Mbps control (only if OVLF > 0) | `link-frequency=720000000` in `config.txt`, reboot; `dmesg \| grep DPHY` silent; the probe lists 4K Clear HDR 16-bit at 25 fps (use 24 if it says 24.x); one 10-min `writer` take with the UI running; compare with the same take at 891 MHz with equal reclaim deltas | 2 x 15 min + 2 reboots | clean at 1440 and losing at 1782 under the same memory numbers: the PHY clamp is a co-cause (or the cause). Losing at both: the link is out |
| CPU0 placement | during a losing `writer` take: `tid=$(ps -L -o tid,comm -p $(pidof apertar-core) \| awk '$2=="CameraManager"{print $1}'); sudo taskset -pc 1 $tid` (and any IPA thread); `grep nvme /proc/interrupts` twice 10 s apart for the completion rate and CPU column. **Never write `/proc/irq/154/smp_affinity`** | one 3-min take, no restart | gaps vanish on CPU1: CPU0's interrupt load matters (then, as a one-shot experiment with a reboot as the undo, the PCIe "msi" parent SPI of the whole RP1 could be moved; procedure in `cofactors.md` §3.1). Unchanged: CPU0 placement is out |
| NeoRotary poll | unplug the board (or `poll_ms=1000` in `apertar-hardware.conf`) for one losing `writer` take; confirm the I2C line's rate fell in `/proc/interrupts` | one 3-min take | a drop larger than the take-to-take spread: the poll costs; otherwise closed (low prior) |

**B6. Done-means (target 1).** `adac040` default, the sysctl chosen by B3 made permanent through `APERTAR_MEDIA_TUNE=1` +
the helper (8.4), UI as shipped with peaking + zebra + audio meter on, drive trimmed and below 50 %: two 10-min takes on two
boots. 0 and 0: target 1 met; hardware-log entry after Patrik confirms. Anything else: the per-minute profile and the 1 Hz
log say whether it is fill (B3), the regime (B1) or the UI (U1/B8). ~30 min.

**B7. Target 2 (4K SDR 12-bit at 33 fps).** Under the B6 configuration: lossless JPEG (COMP1, encoder cap 60 at 4K)
10 min at 33 fps; then uncompressed unpacked (~410 MB/s) 10 min at 33 fps. Lossless clean and uncompressed not: the drive
(~550 MB/s derived, #25) and memory are both near their limit; prefer lossless for 33 fps. Both clean: done. ~30 min.

**B8 / U3. UI switches under `sync` (only if B6 or U1 show UI-correlated loss).** Interleaved pairs of 3 min:
`APERTAR_UI_PREVIEW_RECORDING_FPS=0` vs unset (`c234d77`, kept for this); peaking off vs on; then, un-parked from
`drop-count`/`preview-plane` only if the first two pairs show a delta: `PEAKING=cpu` vs unset, `PREVIEW_PLANE=1` vs unset.
`cap=0` vs unset no delta: the preview is not a cost under `sync`, the parked commits stay parked. `cap=0` clean and unset
losing: the GPU preview costs at this data rate; the peaking and plane pairs then say which mitigation to un-park, the plane
only if it beats peaking-off. 25-50 min.

**B-lossy.** One 10-min Lossy 3:1 take at 4K Clear HDR 16-bit 25 fps, UI on with aids, WebUI closed, `take3v3.sh` counters.
Under the default the sync thread runs but receives no lossy files (`noteWrittenFile` is cDNG-only, `CameraController.cpp:5206`;
the lossy write is on `LossyDngDiskWriter`'s thread, `LossyDngEncoder.cpp:236-290`), so lossy behaves as `off` at ~140 MB/s.
0 lost: acceptable for the Lossy + Log plan. Losses: add `sync_file_range(WAIT_BEFORE|WRITE|WAIT_AFTER)` + `posix_fadvise(DONTNEED)`
after `writeFile` in `LossyDngDiskWriter::threadMain` behind the same `APERTAR_DNG_DONTNEED=sync` reading and retest. ~15 min.

### 8.4 What to do with the code

| Item | Decision | Why |
| --- | --- | --- |
| Core `adac040` (`sync` default) | **build it** (B0); keep `writer` reachable through the knob for B1 | the sync-mode drop is correct (fsync, then DONTNEED on an `O_RDONLY` fd of a closed complete file evicts the whole file including the partial last page: `CameraController.cpp:4703-4712`, `mm/fadvise.c:132-137`, `mm/truncate.c:288-303`); the counters say the regime is gone; the writer-mode call is confirmed useless (8.1) |
| The knob text | **correct the wording** in `README.md:324` (`APERTAR_DNG_DONTNEED` row) and the comment at `CameraController.cpp:4707-4708`: drop "costs a cross-CPU LRU drain per frame"; say "the pages are still dirty or under writeback then, so the call frees nothing and the page cache fills until the kernel reclaims during the take". Same correction for `lessons/upstream-issues.md` #44 | the drain is refuted by source (8.1 row 2); the rest of the sentence is right |
| Journal line | add ` dontneed=<mode> writeback=<on\|off> sync_ms=<N>` to the "recording clip:" line (`CameraController.cpp:4346-4356`) before B1 | every take becomes self-describing; the A/B table no longer depends on session notes to map takes to modes |
| `APERTAR_MEDIA_SYNC_MS` | leave at 1000 | pull-safety needs the per-file fsync regardless of the drop (C0010 0-byte files vs C0011 readable, 2026-10-26); with `0` the drop is off (one warning per process, `CameraController.cpp:4324-4331`). A1's "fsync not needed" was about frames only |
| `APERTAR_DNG_WRITEBACK` | leave on | in `sync` mode it is the only per-frame writeback kick (`CameraController.cpp:4668-4675, 5204-5205`); without it the sync thread's fsync flushes a 415 MB burst per tick (the C0005 shape) |
| Small Core items (optional, not before B1) | one `std::cerr` on a failed `open()` of the clip folder (`CameraController.cpp:4321`: the only silent way to lose the drop); fix the stale comments at `:4274-4276` and `:1452-1454` (exFAT gets 4 writers and +0 buffers, `MediaProfile.hpp:139-141`, not 2 and +2) | hygiene |
| The dirty limits and `min_free_kbytes` | **the Apertar way is `APERTAR_MEDIA_TUNE=1` + the root helper `scripts/apertar-media-tune`**, which already sets #80's `dirty_bytes` 1 GiB / `dirty_background_bytes` 256 MiB for `pi-nvme` (plus `dirty_writeback_centisecs` 150, block queue `none`/512/`rq_affinity` 2, APST 0) but **not** `min_free_kbytes` (`scripts/apertar-media-tune:73-100`). Least intrusive change: a `MINFREE` column in the class table (65536 for the tuned classes), `min_free_kbytes` in the `save_once`, `apply` and `restore` loops, guarded for boards under 2 GB (`mem_kb/64`; the sysctl documentation warns that too high a value OOMs the machine); README row `APERTAR_MEDIA_TUNE`: "dirty-page cushion, free-memory floor (`vm.min_free_kbytes`), scheduler, queue depth". Install the helper to `/usr/local/libexec/`, `config/apertar-media.sudoers` to `/etc/sudoers.d/`, and a drop-in `Environment=APERTAR_MEDIA_TUNE=1`. **Decide the default after B3** ((c) vs (b)); expect the dirty pair to be inert and `min_free_kbytes` to be the knob. Stop calling the set "CineMate-style": cinemate sets no `min_free_kbytes` | extends an existing knob; no new mechanism; `vm.watermark_scale_factor` would be the kernel-cleaner single knob but has no precedent or measurement here (a note, not a recommendation) |
| UI `68e1a41` (count chip) | **keep** | one `contains()` + compare per `buffer` event (<= 4/s); confirmed on the rig (18 = 18) |
| UI `c234d77` (`APERTAR_UI_PREVIEW_RECORDING_FPS`) | **keep as the test instrument, never a default** (the provisional 8.4 said park; the UI examiner's reason to keep is that B8/U3 need it: it is the only way to switch the UI's preview pipeline off during a take without `SIGSTOP`, which hangs the record start at the audio open). Off = one `false &&` per preview frame (`ApertarPreviewSocketClient.cpp:29, 489`); a dropped frame cannot lose a slot registration (registrations are a separate `preview_buffer` event) and the UI sends no ack to Core. Patrik decides | |
| UI `322d329` (`APERTAR_PREVIEW_DIRECT`) | **revert** | a confirmed no-op with `hdmi_external_only=true` (`main.cpp:179, 438-439`); its journal line misleads |
| UI `a51c95e` (`PEAKING=fast`), `4724007` (`PEAKING=cpu`) | **park on `drop-count`, revert from `drop-frames`** | no measured gain even under `writer` (8.83 %); `cpu` moves 0.9 MB of dma-buf reads + a 921,600-pixel loop + a 0.9 MB upload per preview frame onto the render thread (UI CPU 19.6 % vs 12 %); both add a sampler, uniform branches and 4-6 GL calls per draw to the default shader (whether V3D flattens the branches is **unconfirmed**: `V3D_DEBUG=shaderdb` at `41ff827` vs `c13b846`) |
| UI `c13b846` (`APERTAR_PREVIEW_PLANE`, +805 lines) | **park on `preview-plane`, revert from `drop-frames`, do not merge** | not needed at target 1 under `sync`; when on it rewrites Qt's KMS env, writes a config file, starts a display thread and issues legacy `drmModeSetPlane` beside Qt's atomic flips (`DrmPreviewPlane.cpp:278-313, 389, 505`); when off it still adds a **hard build dependency** (`pkg_check_modules(LIBDRM REQUIRED)`, `CMakeLists.txt:14-15, 226`) that the README's apt line does not list; measured 0 then 1.8-3.4 %, and 7.22 % with the aids off (#58): the plane did not control the losses |
| Mechanics of the park | **push the parked tips first**: `preview-plane` @ `c13b846` and `drop-count` @ `4724007` exist only as Mac worktrees (`git branch -a` lists only `origin/drop-frames` and `origin/main`). Then on `drop-frames`: `git revert --no-edit c13b846 4724007 322d329 a51c95e` (newest first, applies cleanly; `c234d77` and `68e1a41` untouched); rebuild the UI on the Pi (not during a take), restart `apertar-ui-direct`; fork-log rows for the reverts and where each parked commit lives | the park is one laptop away from loss until pushed |
| UI hygiene (optional, after U2) | `Behavior on width { enabled: root.bufferBarVisible; ... }` in `StatusChip.qml:106-107` and `ExternalMonitorWindow.qml:1124-1125` | stops the invisible buffer bar from animating; measured effect bounded to a few redraws/s, so it is hygiene unless U2 shows 50-60 frames/s |
| What must **not** go to `main` yet | nothing from `drop-frames` until B6 passes on two boots. In particular: `adac040` not before B1 confirms the mode is the lever (its default change is still right on the counters alone, but the text that justifies it is wrong); the `min_free_kbytes` row not before B3; the UI reverts not before the parked branches are pushed; the imx585 `cd548ef` driver is outside Core/UI but T1/T2 should clear it before anything depends on it | |

### 8.5 Open after this plan, and corrections to the record

Open questions the plan may not close:

1. **Which thread stalls, and how.** B1's M4/M5 and B2's M6 name it if it is a reclaim sleep, a run-queue wait or a V4L2 wait on
   libcamera's thread. If the hole is in the UI's render thread and still costs capture frames, the coupling (GPU/HVS memory
   arbitration, a shared lock, IRQ latency on CPU0) is beyond what `perf sched` shows; the 1440 Mbps pair and the OVLF counter
   are the next instruments.
2. **The accounting gap**: who freed the 20-26 GB per writer take that kswapd did not (M2 from the transcript; then `pgsteal_direct`
   per minute). If `allocstall_*` was ~0, the fadvise freed more than the source reading predicts (pages whose I/O completed
   before the walk), which would change 8.1's first row from "nothing" to "the first MBs of each file".
3. **What builds within a boot under `writer`** (#69 1 -> #70 34 -> #71 153 in 13 min; A0 0 -> A1 0 -> A2 10 % in 30 min two days
   earlier): the cache fills in 6 s, so it is not the cache. B4's rows (slab, swap, fragmentation, RSS) are candidates, not an answer.
4. **#78's last minute**: filesystem fill, NAND state or a `sync` residual; the B0 journal check (was the drive trimmed before
   #78) and B3 (d)-(f) separate them. Also open: the exFAT near-full allocation cost itself (`fs/exfat` is not in the checkout).
5. **The residual rate under `sync`**: pooled 25 of 24,037 (0.104 %) on 11-01, all in #78; whether 0 at 10 min is reproducible
   without any sysctl (B3 (a)) and on a second boot (B6).
6. **A2's 10 %** (2026-10-30, no `sync_file_range`): one run, now unexplained since the hint was redundant; a repeat is cheap but
   low priority.
7. **Lossy DNG and MLV under `sync`**: lossy behaves as `off` (B-lossy); MLV fsyncs and walks the whole growing file once a second
   with no per-frame writeback kick (`CameraController.cpp:4699-4700`; `MlvEncoder.cpp:68, 952, 965`), never run at 415 MB/s.
8. **The CSI-2 receiver** has never been read during a losing take (B5); the 1782 Mbps clamp remains a magnitude factor nobody has
   bounded.
9. **Target 2** (B7), the Log check in Resolve, the trim acceptance test over a full drive pass, `nvme.max_host_mem_size_mb=0`, the
   RTC power-off test (section 7 and the project README's open items).

Corrections to the record (new hardware-log entries after Patrik agrees; the log is append-only):

- 2026-10-30 A1/A2: "the per-frame writeback hint is needed" does not follow; `a40112a` had the per-frame DONTNEED hard-coded
  (`CdngEncoder.cpp:1780`), which starts the file's writeback itself, so A2 removed a redundant kick. A2 is one unexplained run.
- 2026-11-01 "A0 was clean with it running (regression)": A0 was not early in its boot; what it shares with #69 is being the first
  take of a freshly started Core. Whether anything regressed is T1's question.
- 2026-11-01 last entry, the mechanism sentence: "frees nothing" stands; "drains the per-CPU LRU lists on every core per frame" is
  refuted by source; "~13 GB per 3-minute take" is 49-57 GB at 16 KiB pages (M0 confirms the page size).
- "CineMate's dirty limits" (sections 1, 2, 7, the hardware log): cinemate sets `dirty_bytes`/`dirty_background_bytes`/
  `dirty_writeback_centisecs` 150/`dirty_expire_centisecs` 3000 and no `min_free_kbytes`; #80's set is Apertar's own.
- The provisional 8.2 Q5 suggestion `/proc/irq/154/smp_affinity`: withdrawn (not user-movable; may oops). Its M6 half "dynamic
  debug `rp1_cfe +p`": unavailable on this kernel; only tracepoints and `csi2_errors`.
- `lessons/upstream-issues.md` #44: keep the finding (the hard-coded per-frame DONTNEED frees nothing and fills the cache), drop
  the drain clause.
