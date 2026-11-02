# Inspection of the 2026-11-01 drop-frames results (2026-11-02)

Section numbers continue the night report ([night-2026-11-01.md](night-2026-11-01.md)), whose section 8 is a summary of this page. The examiner reports, the synthesis draft and the three critiques this text was built from are in [inspection-raw/](inspection-raw/) (`stats.py` and `power_check.py` reproduce every p-value and power figure).

Written from the desk (no Pi). Five examiner passes (statistics and design; kernel 6.12 `mm/`; Core `adac040`; the six UI
commits; co-factors), a synthesis, then three adversarial critiques (statistics and design; kernel mechanism; engineering
and safety). Every critique point was re-read against the source or the record before it was taken in. It replaces the provisional section 8 of the night report.

Sources: sections 1-7 of the night report, `takes-2026-11-01.md` (79 rows) and `takes-2026-11-01.raw.txt` (ends 23:13:03: #80 is not in
it), `lessons/hardware-log.md` 2026-10-26/30/31 and 11-01, Core `drop-frames` @ `adac040` (and `64bbbaa`, `a40112a`), UI
`drop-frames` @ `c13b846`, kernel `raspberrypi/linux` `rpi-6.12.y` @ `5bd564a` (`mm/`, `kernel/irq/`, `kernel/latencytop.c`,
`arch/arm64/configs/bcm2712_defconfig`, `drivers/media/platform/raspberrypi/rp1_cfe`, `drivers/pci/controller/pcie-brcmstb.c`,
`drivers/mfd/rp1.c`), cinemate `storage-automount.py`, cinepi-raw `dng_encoder.cpp`. Not in the kernel checkout, so every
claim resting on them is at most **probable**: `fs/` (exfat, sync.c, proc), `block/`, `kernel/trace/`, `kernel/sched/`,
`include/trace/events/`. Status words as in the KB: **confirmed** (read in source or measured), **measured** (numbers real,
reading not agreed), **probable** (inferred, reason given), **unconfirmed** (the measurement is named), **refuted** (the
source or the record says otherwise). Examiner reports and critiques: [inspection-raw/](inspection-raw/).

## 8.1 Verdict

**`sync` removes the reclaim regime (measured). That it removes the losses is probable, not proven. The stated mechanism
is partly wrong, and how reclaim reaches capture is open.**

- `sync` does what it should: after the once-a-second `fsync` the pages are clean and `posix_fadvise(DONTNEED)` evicts the
  whole file (`mm/truncate.c:288-303`, `CameraController.cpp:4703-4712`; the last page too, `mm/fadvise.c:131`). A take's
  cache footprint is bounded at about 1-2 sync ticks, 0.4-0.85 GB (`syncLoop`, `CameraController.cpp:4689-4718`). kswapd
  reclaimed 47-58 k pages per 3 min against 3.02-3.45 M (#74/#75 vs #70-#72); low-watermark hits 8-11 against 948-1805
  (**measured**, no overlap; #78 at 10 min is 17-20x below writer per 3 min).
- `writer`'s call starts writeback of the whole file (`mm/fadvise.c:113-115`) and then evicts only folios no longer under
  writeback (`mm/filemap.c:2121-2125`, `mm/truncate.c:293`). It frees little. "Nothing" is **probable**, not confirmed: the
  walk starts milliseconds after the submit, and 18-24 GB per take were freed by something other than kswapd.
- "Drains the per-CPU LRU lists on every core per frame" is **refuted for folios still under writeback** (the branch needs
  `nr_failed`, `mm/fadvise.c:166-170`; such folios are never returned to be counted, `mm/truncate.c:521-531`). How often it
  fires on folios that finished early is **unconfirmed** (M1). Its cost, <= 0.2 ms per frame of CPU0, is too small for a
  40 ms hole and for the few-ms per-frame deficit of mechanism G (**probable**, estimate from code).
- The link from reclaim to capture is **unproven**. The strongest candidate has a measured precedent on this rig
  (2026-10-26, `hardware-log.md:153-202`): memory contention slowed libcamera's serial per-frame cycle (IPC 1.87 -> 1.30),
  the 8 CFE buffers drained, and the CFE skipped single frames at a steady rate. The 11-01 losses have that signature
  (single frames, 1.7-2.3/s, steady from second 3-5, `hardware-log.md:922`). It needs no 40 ms stall anywhere (Q4, G).
- `sync` vs `writer` at the take level: one-sided p = **0.057** (4 vs 3), confounded by order, the Core restart with its
  trims, and the start memory state, after a search of ~20 one-take interventions (Q1).
- #80's sysctls have no measured effect: no watermark was reached (`pgsteal_kswapd` 0, low-watermark hits 0), so
  `min_free_kbytes` cannot have acted (**probable**: source plus session-reported counters), and the dirty pair is inert for
  Core (table). The probable carriers of its 0 are the start state (MemFree 2,758 MB after the 23:13 format) and the empty, trimmed drive.
- A0 (2026-10-30: the same per-frame DONTNEED, `a40112a:CdngEncoder.cpp:1780`; UI running; 10 min) lost 0 of 15,001. It was
  the first take of a fresh Core on a freshly trimmed drive, the position of #69 (writer, 1 lost) and #74 (sync, 0). Its
  boot age is **unconfirmed**: the record's stamps conflict.

The claim that holds: **`writer` creates a standing reclaim regime; under it the losses scale with the touch UI's GPU work
(preview held / 12 fps / 25 fps: 0 / 2.9 / ~7.5 %); `sync` removes the regime, and in #74, #75 and #80 the losses with it
(probable).** Which thread is slowed or stalled, or whether none stalls and the per-frame cycle simply runs long, is the
open mechanism.

| Part of the claim | Status | Basis |
| --- | --- | --- |
| `writer` DONTNEED "frees nothing" | **probable** (was "confirmed") | Confirmed part: writeback of the whole file is submitted first (`fadvise.c:113-115`); folios under writeback are skipped (`filemap.c:2121-2125`) and refused (`truncate.c:293-294`). Weak part: the walk starts after `do_writepages` has handled ~1,013 folios, after `lru_add_drain()` (`fadvise.c:156`) and after any preemption: milliseconds, not microseconds. At ~800 MB/s, 10-25 % of a file can finish before the walk (**probable**). The take's accounting leaves 18-24 GB not freed by kswapd. Tests: M2's lower bound (written pages - `pgsteal_kswapd` - `pgscan_direct` - delta `Cached` = minimum fadvise frees), M8 per-comm frees |
| "... and drains the per-CPU LRU lists on every core per frame" | **refuted** for folios under writeback (mm source); frequency **unconfirmed** | The branch at `fadvise.c:166-170` needs `nr_failed > 0`, counted only for folios returned by the walk and refused (`truncate.c:521-531`): folios whose I/O completed before the walk and still sit in a remote CPU's `lru_add` batch, or folios left dirty. Rows 1 and 2 are one timing hypothesis: the more the call frees, the more often the drain can fire. `fs/exfat` (does `writepages` set writeback on every dirty folio?) is not in the checkout. M1 counts calls by caller |
| the drain is what costs capture frames | **probable: no** (estimate from code) | <= 200 us per CPU per drain, nice-0 kworker on `mm_percpu_wq` (`mm/vmstat.c:2179`), caller waits in `flush_work` (`mm/swap.c:876-877`), concurrent calls coalesce (`:830-840`): 25/s gives <= 0.2 ms per frame on CPU0, against ~0.6-3 ms per frame for G or 40 ms for a hole |
| the per-frame `sync_file_range` is redundant in `writer` mode | **confirmed** (mm) / **probable** (`fs/sync.c` not in checkout) | The fadvise already started writeback; the second call returns at `filemap.c:393-395` (no dirty tag). So the 2026-10-30 A1/A2 reading ("the writeback hint is needed") is wrong for its stated reason; A2's 10 % is one unexplained run |
| the page cache fills and kswapd reclaims during the take | **measured**; arithmetic corrected | 16 KiB pages (`bcm2712_defconfig:50`; **probable** until `getconf PAGESIZE`). A DNG is 16,590,340 B (`hardware-log.md:140`) = 1,013 pages. #70-#72 wrote 4,349-4,469 frames = 72-74 GB each; `pgsteal_kswapd` 3.02-3.45 M = 49.5-56.5 GB = **67-76 %**; 18-24 GB per take freed otherwise (direct reclaim or the fadvise itself: M2) |
| kswapd re-woken before it can sleep | **measured**; per-node caveat | `kswapd_low_wmark_hit_quickly` 948-1805 per take (`vmscan.c:7119, 7161-7165`). Stock watermarks sum to min/low/high 16/20/24 MiB (`page_alloc.c:6125-6178`): low -> min is 4 MiB = 10 ms of the stream with kswapd idle, ~30-40 ms with kswapd reclaiming at 275-314 MB/s. `CONFIG_NUMA=y` and `CONFIG_NUMA_EMU=y` (`:54, :96`) and the bootloader's `numa=fake` (KB `working/research-30fps/q3-bandwidth.md:99-101`) make 8 nodes **probable** (never read): then 8 kswapd threads (`vmscan.c:7361`), per-node marks ~2/2.5/3 MiB, the hit count a sum over nodes (~0.7-1.3 re-wakes/s per kswapd), and a watermark boost of up to one 32 MiB pageblock per zone (`page_alloc.c:1918-1950`), ~10x a node's high mark. M0 reads it |
| the memory regime reaches capture | **unconfirmed** | Mechanisms A-H in Q4. G (per-frame cycle deficit) has the measured precedent and needs no stall; the stall paths (direct reclaim, the throttle, the NOPROGRESS sleep, compaction, CMA, major faults) need M4-M6 |
| the touch UI is "the last straw" | **probable** (conditional) | Under `writer`, losses fell with the UI's GPU work: preview held 0/1,498 (#30), 12 fps 2.88 % (#31), aids off 1.67 % (#32), against 5.33-10.60 % baselines; frozen with memory kept 1/1,450 (#27). n = 1 per variant. UI drawing under `sync`: clean in #74, #75, #80. The UI-stopped takes (#5, #17, #59) also free the UI's RSS and GPU buffers, so only #27 and #30 separate drawing from footprint. The feed costs the completion thread a ~200-byte descriptor per frame (`CameraController.cpp:10024-10072`, `ApertarCoreApp.cpp:8175-8221`, non-blocking publisher `ControlServer.cpp:19-36`) |
| `sync` vs `writer` is real, not chance | **suggestive**; confounded | Frame-level Fisher p = 8.6e-67 is **invalid** (per-take counts 1, 34, 153, 71: variance/mean 66). Take level, like for like: 4 vs 3, one-sided **p = 0.057** (two-sided 0.114). Position-matched (#69, #74) = (1, 0), (#70, #75) = (34, 0): sign p = 0.25. Without the first-of-process takes: 3 vs 2, rank p = 0.10. The 0.029 "with #80" is withdrawn: #80 is a different treatment. Confounders in Q1 |
| #80's dirty limits did it | **probable: no** | Defaults give bg ~290-350 MB / hard ~580-700 MB; #80's set 256 MiB / 1 GiB. Core's peak `Dirty` was 11 MB (A0) and 3 MB (A1), far inside the freerun ceiling (`page-writeback.c:377-446, 837-841, 1769`); `balance_dirty_pages` throttles only the dirtying task (`:2144`). (The 2026-10-26 5-vs-5 is not evidence here: 10-s lossless-JPEG takes on `f60e301`, a different regime, `hardware-log.md:64-71`) |
| `min_free_kbytes` 64 MiB did it | **not supported by #80**; untested | Raising it raises min, low and high together (`page_alloc.c:6127, 6164, 6171-6177`), so kswapd wakes earlier (~80 MiB free), never later. kswapd wakes only when the fast path fails at `ALLOC_WMARK_LOW` (`:4836`, wake `:4375`). #80 had `pgsteal_kswapd` 0 and 0 low-watermark hits: free memory never fell to 80 MiB, so no allocation met a watermark the knob moved. Its only live effect was `pcp->high` sizing (`:5697-5703`, microsecond scale). #80's `pageoutrun` delta (in the transcript, `take3.sh` `S()`; counted once per `balance_pgdat`, `vmscan.c:6870`) = 0 closes it |
| "early in the boot, empty cache" explains A0 | split: **refuted** (empty cache) / **unconfirmed** (boot age) | Under `writer` the cache fills in ~6 s, so an empty start cannot carry a take. Boot age: the UI start stamp 01:04:19 and A0 at 08:30 (`hardware-log.md:925-926`) straddle an NVMe death and reboot at 01:43-01:45 (`:717-719`), and boot clocks were wrong until NTP (`:797-811`). The record holds a counterexample to "fresh Core protects" (#64: first take of a new Core at 3 h 20 min uptime, 11.1 %; A2: first take after a restart, 10 %) and none to "fresh boot protects" (#3, 14 min after boot, 6.97 %, was the second take of its process). A0 was never measured in kernel terms (no `pgsteal`, MemFree): that it ran the reclaim regime is **probable** (same call) |
| the drift is monotone with uptime | **not supported** | #69-#72: r = 0.65, p = 0.35 (n = 4, #72 < #71). Boot 1's 19:09-21:03 baseline is flat (1.2 %/h, p = 0.25); the rise is a step to 11-18 % between 21:03 and 22:06, on a freshly formatted 1-35 % drive (fill excluded as its cause) |

## 8.2 The five question groups

**Q1. `sync` vs `writer`: real or chance?** Suggestive, not settled.

- The take is the unit (dispersion 66). Like-for-like evidence: 4 vs 3, one-sided p = 0.057, one overlapping take (#69 0.02 %
  < #78 0.17 %). The kernel counters separate without overlap: the mode changed the reclaim regime (measured). That the
  regime caused the gaps is not shown.
- Confounders in the record:
  - order (writer 22:28-22:43, sync 22:46-23:24);
  - the Core restart at 22:46, which came with Core's mount trim and a 0.7 GB pre-roll, delete and trim
    (`ApertarCoreApp.cpp:10904, 11272`; `raw.txt:360`; `hardware-log.md:909-910`). "First take after a restart" is therefore
    aliased with "first take on a fresh trim" (after a 0.7 GB pre-roll since the pre-roll exists) for #64, #69, #74, A0-A2
    (trimmed by hand; `a40112a` had no pre-roll) and, by the format, #80;
  - the start memory state, which tracks the arm: MemFree writer 275-327 MB, sync 507-788 MB, #80 2,758 MB;
  - the audio meter on from 23:00;
  - uptime and fill: **neutral at best** (no monotone drift is shown, and fill is harmless below ~94 %).
- Multiplicity and stopping: boot 1 tried ~20 interventions one take each; two gave a clean take (#30, #46), and #46 did not
  replicate (#47-#50: 1.8-3.4 %). `sync` was chosen after that search, and the session stopped at the first clean 10-min take
  (#80, three changes at once). Post-hoc p-values overstate the evidence. B1's rule goes into the KB before its first take.
- Not explained by the cache hypothesis: three "fresh process clean, then rising" series. #69 -> #72 (1, 34, 153, 71);
  #46 -> #50 after the plane's UI restart (0, 1.82, 1.93, 3.13, 3.42 %; Spearman rho = 1, exact one-sided p = 0.008; #47-#48
  shorter, #49 with CPU peaking); #74/#75 -> #78. The cache fills in seconds, so this points at build-up inside a process
  (Core's or the UI's) or since a trim (**unconfirmed**; B1's positions and B4).
- The sound A/B is B1: Core restarted per unit in both arms, two consecutive takes per unit (positions 1 and 2), equal start
  memory, randomized order within rebooted blocks, a stratified permutation test fixed in advance.
- What a clean take bounds. Independence is refuted, so per-frame bounds are optimistic. With the writer arm's take-level
  dispersion (k = 1), P(0 lost) = 1/(1 + mu) (**probable**: k under `sync` is unknown, #78 is its only losing take):

  | Clean takes | 95 % bound, k = 1 | 95 % bound, independence |
  | --- | --- | --- |
  | one 3-min | < 0.42 % (19 per take) | < 0.067 % |
  | two 3-min | < 0.077 % | < 0.033 % |
  | one 10-min | < 0.13 % | < 0.02 % |
  | two 10-min | < 0.023 % (3.5 per take) | < 0.01 % |
  | five 10-min (B6) | < 0.0055 % (0.8 per take) | < 0.004 % |

**Q2. #80 changed four things.** The dirty pair, `min_free_kbytes` 16 -> 64 MiB, the drive (formatted 23:13: empty and
trimmed), and the start memory (MemFree 2,758 MB after the format's deletes).

- The dirty pair is very probably inert for Core (8.1). `min_free_kbytes` never engaged in #80 (8.1). It is also Apertar's
  own knob: cinemate sets only `dirty_*` and the writeback intervals (`storage-automount.py:111-112, 319-335`; no
  `min_free` anywhere in `/home/user/cinemate`), and `apertar-media-tune` does not set it (`scripts/apertar-media-tune:73-100`).
- The start state is the probable carrier (**probable**). Under `sync` a take holds ~0.4-0.85 GB of its own pages, so a
  2,758 MB start keeps the whole take off the watermarks; #74/#75 (507-646 MB) and #78 (788 MB) reached them. Under `sync` an
  empty start is worth the whole take, not "~6 s" (that figure is `writer` arithmetic). So #80 shows that a `sync` take which
  never meets the watermarks is clean. It says nothing about the knobs. B3 sets the start state.
- Fill. On this rig fill losses were always **queue-full** before (2026-10-26, 77-81 %: 166-676 drops). #78's 18
  last-minute losses were capture gaps with `peak_queue=2/12`. "The drive slowed" is **not shown**, but not excluded either:
  a slowdown that stays above 415 MB/s keeps the queue at 2 and lengthens writeback and `fsync`, which fits #78's 3x per-minute
  reclaim (59 k vs 16-19 k pages/min). The 1 Hz write-latency log (B0) settles it.
- #78's minute 10 is a regime change. Per-minute losses 0, 0, 3, 0, 0, 0, 2, 0, 2, 18 (the night table lists them
  cumulatively). Minutes 1-9: mean 0.78, variance 1.44; a negative binomial fitted to them (k = 0.91) gives P(>= 18) = 6.8e-7
  per minute, 6.8e-6 for the largest of ten. The "< 1e-12" quoted before assumed independence. Whether the 18 were a few
  multi-frame episodes needs #78's `drop[...]` lines, which the KB extract lacks (B0).
- Deletions before #78: ~70 GB, not ~140 GB. The volume is ~1.0e12 B (`fstrim` freed 917.4 GiB, `hardware-log.md:710`;
  #80 went 1 -> 26 % on 249 GB), so 97 % is ~970 GB against the no-deletion sum of 1,043 GB. #78 started at ~72 %. A Core
  or UI delete >= 1 GiB trims (`ApertarCoreApp.cpp:10856-10861`); the B0 record check says whether #78 ran on clean NAND.
- Fill, NAND state and the sysctls are separable (B3), but the NAND-stall cell is dropped on safety grounds unless Patrik
  explicitly asks for it (B3).

**Q3. Which UI conclusions survive?** For target 1 none is needed: the unmodified GPU preview with peaking and zebra was
clean under `sync` (#74 0/4,505, #75 0/4,509, #80 0/15,025).

- The boot-1 UI A/Bs are better evidence than the draft allowed. The baseline was flat until 21:03 and stepped up only
  between 21:03 and 22:06, and #30-#33 were interleaved with baselines (#28/#29 | #30-#33 | #34/#38).
  - The four GPU-reducing takes (#30 0, #31 2.88, #32 1.67, #44 CPU peaking 3.88 %) and the four plane takes (#46 0,
    #48 1.93, #49 3.13, #50 3.42 %) each lie below all ten pre-step baselines (5.33-10.60 %): exact rank p = 0.001 each
    (exchangeability assumed).
  - Preview rate gives a dose-response: 0 / 12 / 25 fps -> 0 / 2.9 / ~7.5 %.
  - The plane "contradiction" (#58, plane with aids off, 7.22 %) exists only across the step; #58 lies below all post-step
    baselines (11.1-18.1 %).
  - Limits: n = 1 per variant, each after a UI restart, the plane series rising within itself. Still, these are the
    strongest take-level contrasts of the night, stronger than writer vs sync.
  - Reading: under `writer`, losses scale with the UI's GPU work (**measured**, n = 1 per variant). Mechanism test: the
    writer-mode dose-response in B2.
- No gain, as before: `fast` peaking (#34 8.83 %); `PREVIEW_DIRECT` is a confirmed no-op here (`main.cpp:179` already sets
  direct rendering on the external-monitor renderer; `:438-439` hides the main window); zebra off alone (#33 10.45 %).
- The bus arithmetic (display stack ~1 GB/s of a ~17 GB/s LPDDR4X bus, **probable**) rules out saturation only. 2026-10-26
  measured a ~45 % per-instruction slowdown of libcamera's passes from recording traffic of the same order: contention
  without saturation is mechanism G.
- `ea44bd7..c13b846` (13 commits) adds no per-camera-frame work on the default path beyond a few GL calls. The one new periodic
  item is `841d0ed`'s buffer-bar `Behavior` animation that runs with the bar hidden (`StatusChip.qml:104-107`,
  `ExternalMonitorWindow.qml:1121-1125`), bounded by the measured ~30 redraws/s to a few extra redraws a second.
- The one `sync` loss with the UI: #76 (29 s, 49 lost, 6.86 %, `takes-2026-11-01.md:85`) ran while Patrik edited the ladder in
  the WebUI. It is the only `sync` take with a client; kswapd was not read. It suggests the WebUI preview's downsample on
  libcamera's thread (`ApertarCoreApp.cpp:9730-9820`) can lose frames without the regime (**unconfirmed**; B2 tests it).
- Decisions in 8.4. The UI half of "regression since A0" is a `writer` question: T2(a). U1 only checks that the branch
  costs nothing under `sync`.

**Q4. Is the mechanism right, and the cheapest direct measurement?** The measured halves (cache fills, kswapd busy) are
right. The drain is refuted for folios under writeback, with its frequency open (M1). The real question is how the regime
reaches capture.

The draft listed "exactly one unbounded sleep" (`throttle_direct_reclaim`). The full list of ways the regime can cost a
frame:

| | Mechanism | Predicts | Prior | Discriminator |
| --- | --- | --- | --- | --- |
| G | **per-frame cycle deficit**: libcamera's serial IPA + back-end chain runs over 40 ms under memory/cache contention; the buffers drain; single frames skip. No hole anywhere | IPC lower and cycles/frame higher at equal instructions under `writer`; back-end start interval > 40 ms under `writer` + UI, <= 40 ms under `sync`. A loss rate f needs a cycle of 40/(1 - f) ms: 1.4 % = +0.6 ms, 7 % = +3 ms per frame | **high**: measured precedent at 30 fps (`hardware-log.md:153-202`: IPC 1.87 -> 1.30, back-end interval 36.2 ms); fits UI stopped, 12.5 fps, 1080p, the dose-response, 12 buffers no help (#41), FIFO no help (#22) | `hwcount.py`, `libcam_stages.py` (G rows below) |
| A | a Core/libcamera thread (CameraManager, the IPA thread, the copy worker) stalls in direct reclaim (ms, `page_alloc.c:4497`), direct compaction (order > 0 = >= 32 KiB at 16 KiB pages; `COMPACTSTALL` `:3790`, `HZ/50` waits `compaction.c:903`), the 1-jiffy NOPROGRESS throttle (4 ms at HZ 250, `vmscan.c:6129` via `shrink_zones` `:6223`, outside the MGLRU hand-off), or `throttle_direct_reclaim` (unbounded) | `_begin`/`_end` on that tid with >= 20 ms episodes within 100 ms before a hole; the sleep stack | medium. The throttle is hard to reach: judged on the first usable node only (`vmscan.c:6454-6463`, ~1 MiB with 8 nodes), and ordinary order-0 allocations reclaim at `min` before free falls to `min/2` (`page_alloc.c:3225-3243`): low prior until `pgscan_direct_throttle` > 0 | M4, M6 |
| H | major fault or swap-in of a page the thread already owns (evicted library text on the SD card, cold anon such as `64bbbaa`'s warm raw pool): an I/O sleep with no malloc | per-thread `majflt`, `workingset_refault_*`, `pswpin` rising in losing seconds | unknown (89 MB of swap in use on 2026-10-26, `hardware-log.md:90`) | M5; one `writer` take after `swapoff -a` (B2) |
| I | CMA `alloc_contig_range` (dma-heap `linux,cma`, vc4): `lru_cache_disable` = expedited RCU + a forced drain of every CPU (`page_alloc.c:6548`, `swap.c:904-922`), then synchronous migration that waits on writeback | `cma_alloc_*` > 0; drains attributed to the allocator, not to Core's writers | unknown; would make "a drain on every core" real but CMA-driven | M1 attribution, `cma_*` counters |
| C | run-queue competition with up to 8 nice-0 kswapd threads (probable fake NUMA) | `schedstat` wait (field 2) grows >= 40 ms in a losing second | low-medium (#22 FIFO 6.16 % is one take inside the 5.33-10.60 % baseline spread: not excluded) | M5; pin every kswapd (B5) |
| E | another CFE node (`fe_config`, stats) starves: no job runs unless every enabled node has a buffer (`cfe.c:613-629`) | that node's `owned_by_drv` <= 1 just before a sequence hole | low-medium | M3 |
| B | the UI render thread stalls and Core waits on it | `sendmsg`/`futex` in a Core sleep stack | low (the hand-off is non-blocking) | M6 |
| F | CSI-2 receiver FIFO overflow (`csi2.c:79-80, 219-258`) | `OVLF` > 0 comparable to the gap count | low | B5 |

Measurements, cheapest first (all folded into B0-B2):

| # | Measurement | Settles | Cost |
| --- | --- | --- | --- |
| M0 | `getconf PAGESIZE`; `sudo modprobe configs` (`CONFIG_IKCONFIG=m`, defconfig `:19`), then `zgrep -E 'CONFIG_(ARM64_16K_PAGES\|LRU_GEN_ENABLED\|PSI\|NUMA_EMU\|KPROBES\|UPROBE_EVENTS\|BPF_EVENTS\|FUNCTION_TRACER\|FUNCTION_GRAPH_TRACER\|STACKTRACE\|LATENCYTOP\|SCHEDSTATS\|HZ)=' /proc/config.gz` (or `/boot/config-$(uname -r)`); `ls -d /sys/devices/system/node/node*`, `cat /sys/devices/system/node/node*/cpulist`, `pgrep -l '^kswapd'`, `tr ' ' '\n' < /proc/cmdline \| grep -E 'numa\|iommu_dma'`; `/proc/zoneinfo` min/low/high/boost per node; `nr_dirty_threshold`; `swapon --show`, `cat /proc/sys/vm/swappiness /sys/kernel/mm/lru_gen/enabled`; `grep -cw try_to_free_pages /sys/kernel/tracing/available_filter_functions` | page size, node layout and kswapd count, swap, which tracers exist (function tracer **probable** from `STACK_TRACER=y`/`FUNCTION_PROFILER=y`, `:1781-1782`; kprobes/uprobes absent, `:1786`, so bpftrace probably cannot run) | 1 min, no take |
| M2 | copy every `take3.sh` `S()` delta of #70-#80 (`pgscan_direct`, `allocstall_*`, `pageoutrun`, `compact_daemon_wake`, `pgsteal_kswapd`) and #80's journal lines from the 2026-11-01 Mac transcript into section 2 | direct-reclaim regime or not; the lower bound on fadvise frees; #80 `pageoutrun` = 0 closes the `min_free` point | no take |
| M5 | 1 Hz log to `/dev/shm`: `recording_dropped_frames`; `/proc/<pid>/task/*/schedstat` fields 1 (run ns) and 2 (wait ns) and `stat` field 12 (`majflt`) for **every** Core thread and the UI render thread | the second each frame was lost; run time growing (G), wait growing (C), faults (H) | every take |
| G1 | `python3 -I ~/apertar-kb/working/tools/hwcount.py <Core pid> <CameraManager tid> 60` (user-space PMU, no `sudo`, ran here on 2026-10-26) | G: IPC lower and cycles/frame higher under `writer` at equal instructions/frame; equal IPC = a stall mechanism | every B1 take |
| G2 | one unscored take per arm with `LIBCAMERA_LOG_LEVELS=IPARPI:ERROR,RPI:0,RPiStream:0` (merged with the existing `IPARPI:ERROR`, or the per-frame warnings return), parsed with `working/tools/libcam_stages.py` | back-end start interval median > 40 ms under `writer` + UI and <= 40 ms under `sync` = G | 2 takes |
| M4 | tracefs in one buffer (8 MiB per CPU, set once after each reboot; `buffer_size_kb` is per CPU, so 65536 would pin 256 MiB): `vmscan/mm_vmscan_direct_reclaim_begin/_end`, `mm_vmscan_kswapd_wake/_sleep`, `mm_vmscan_throttled`, plus `v4l2/vb2_v4l2_buf_done` (sequence) and `vb2/vb2_buf_done` (`owned_by_drv`; field names **probable**: check each `format` file); `grep overrun per_cpu/cpu*/stats` after | who reclaims directly and how long, against every lost frame on the same clock; P(hole within 100 ms after an episode) vs the take's base rate, and the same under `sync` | every B1 take |
| M1 | function tracer on `lru_add_drain_all lru_cache_disable` for 60 s per arm (`set_ftrace_filter`), or `workqueue_queue_work` lines with `function=lru_add_drain_per_cpu` (the queuer's comm is in the header; `_execute_start` always shows a kworker) | whether Core's fadvise drains: callers = writer threads (`writer`) or the sync thread (`sync`); CMA/GUP callers = not Core's. kcompactd drains only locally (`compaction.c:2591-2592`; the drain-all at `:2931` is the `compact_memory` sysctl and the per-node sysfs `compact` file only, `:2931, :2999`) | 2 x 60 s |
| M8 | `filemap/mm_filemap_delete_from_page_cache` (`filemap.c:231, 341`) counted per comm over 10 s per arm | who frees DNG pages: writer threads = fadvise, `kswapdN`, the sync thread, others = direct reclaim; closes the 18-24 GB gap | 2 x 10 s |
| M6 | `echo 'stacktrace if prev_pid == T && prev_state & 3' > events/sched/sched_switch/trigger` for CameraManager, the IPA thread and the copy worker (needs `STACKTRACE`, M0); or LatencyTOP (`sysctl kernel.latencytop=1`, forces schedstats, `latencytop.c:68-76`; per-task max sleeps with 12-frame stacks) | the sleeping thread and its kernel path: `try_to_free_pages`/`throttle_direct_reclaim` (A), `folio_wait_bit` (H), compaction/migration (A/I), `futex`/`sendmsg` (B) | one unscored losing take; LatencyTOP costs a stack walk per wakeup: diagnostic only |
| M3 | in M4's buffer: per video node (`media-ctl -p`) the sequence holes (`sequence = fs_count - 1`, `cfe.c:654`; `fs_count` counts every SOF, `:690`) and `owned_by_drv` before each hole | a starved node (E); one starved node puts a hole on **every** node, so "holes on all nodes" alone does not mean sensor/link; a Core gap with no sequence hole = lost after the CFE (libcamera or Core) | in M4 |
| M7 | `psi=1` on the cmdline, reboot; `/proc/pressure/memory` at 1 Hz | system-wide memory-stall time per second (names no thread) | one reboot (`CONFIG_PSI_DEFAULT_DISABLED=y`, `:17-18`) |

Not available: `rp1_cfe` dynamic debug ("has no buffer, unable to schedule job" is `cfe_dbg_verbose`, `cfe.c:623-625`; no
`CONFIG_DYNAMIC_DEBUG`); kprobes, uprobes and probably BPF tracing. Tracepoints, the function tracer and LatencyTOP:
**probable** (M0).

**Q5. What was not considered.**

| Item | Finding | Status | Test |
| --- | --- | --- | --- |
| Why A0 was clean | Position: first take of a fresh Core on a fresh trim (as #69, #74). Boot age unknown (8.1). Changed between A0 and 11-01 under the same `writer` path: Core `a40112a` -> `64bbbaa` (warm raw pool kept through the take, one 16.6 MB `write()`, RAM buffer, pre-roll, trim), UI `ea44bd7` -> `c13b846`, the **imx585 driver** `24172e6` -> `cd548ef` (`hardware-log.md:899-906`), drive handling (A0 cooled to 34 C, no back-to-back takes). The 10-31 losses on the old driver with the WebUI open show the driver is not necessary for losses | position and changes **confirmed** (record); boot age **unconfirmed** | B0 monotonic check; T1 at A0's uptime; T2 bisect |
| The RAM write buffer | every 11-01 take ran `buffer=ram` with `queue_budget` 1.40-1.55 GB on the compared takes (`raw.txt:335-384`; 1.70 is a boot-1 value, `:225`), a mode A0 never had; `peak_queue=2/12` throughout. With 0.6 x MemAvailable - 512 MiB, MemAvailable at take start was 3.2-3.5 GB in every take: the arms differed in MemFree, not in what the kernel counted available. The modes are memory-equivalent while the queue stays at 2 (`CameraController.cpp:4791-4816, 5459-5471`) | **measured** / **probable** (formula, equivalence) | run B1 and B3 in `ram` (Patrik's setting); `frames` only in T1 |
| CSI-2 at 1782 Mbps | the D-PHY programs the 1500 Mbps bin and keeps streaming (`dphy.c:99-128`); only a receiver FIFO overflow (`csi2.c:79-80, 219-258`) could correlate with memory state. `csi2_errors` needs `rp1_cfe.track_csi2_errors=1` at boot (`csi2.c:19-21`), zeroes on read (`:189-192`), never read during a losing take. 720 MHz (1440 Mbps) gives 4K Clear HDR 16-bit exactly 25.0 fps with zero margin (`imx585.c:287-302`) | **confirmed** (source) / **unconfirmed** (rig) | B5 |
| CPU0 interrupts | rp1-cfe (154), USB, I2C and probably the NVMe queues cannot be moved from user space (`rp1.c:144-157`; `pcie-brcmstb.c:664-674, 720-724`; `msi.c:663-670`). **Do not write `/proc/irq/154/smp_affinity`.** The draft's "move the RP1's PCIe MSI parent" is withdrawn: `/proc/irq/N` exists only for IRQs present at `init_irq_proc` or requested through `__setup_irq` (`kernel/irq/proc.c:421-437`, `manage.c:1833`), which a chained parent never is, and if it worked it would move ssh, USB, I2C and camera at once | **confirmed** (source) / **probable** (parent) | `taskset` for libcamera's threads (B5) |
| NeoRotary 4 poll (~570 I2C IRQs/s on CPU0) | microseconds each; low prior. Hot-unplugging on a live I2C bus can hang bus 1 | **unconfirmed** / **probable** (hang) | `poll_ms=1000` + service restart, or unplug powered off (B5) |
| WebUI preview | a completion-thread cost while a browser is attached (`ApertarCoreApp.cpp:9730-9820`; encode on `mjpegThread_`, `:9833-9880`). #76 (sync, client, 6.86 % in 29 s) is the only `sync` take with a client | **confirmed** (cost) / **unconfirmed** (size under `sync`) | keep the "no client on :8000" rule; one 3-min `sync` take with a passive tab (B2) |
| Fake NUMA | probably 8 nodes x 512 MB: per-node watermarks, 8 kswapd and 8 kcompactd threads, per-node throttle line, up to 32 MiB boost per zone. Absent from every number of the night | **probable** | M0 |
| Page size, MGLRU, PSI | 16 KiB pages (`:50`); MGLRU on (`:95`): direct reclaimers skip the writeback/congestion throttles (`vmscan.c:6022, 6050`) but **not** the 1-jiffy NOPROGRESS throttle (`:6129`); PSI compiled, disabled (`:17-18`) | **probable** until M0 | M0 |
| Which heap holds the raw buffers | `allocateCachedBuffers` tries `vidbuf_cached`, then `linux,cma`, else libcamera's allocator (`CameraController.cpp:8661-8691`); with CmaTotal 64 MB the 8 x 16.6 MB cannot all be CMA | **unconfirmed** | `journalctl -u apertar-core -b \| grep -E 'RAW buffers\|cached DMA'` (B0) |
| Within-boot state other than page cache | slab (exFAT inodes/dentries, buffer heads), swap, fragmentation (no order >= 8 free at the end of boot 1; kcompactd equally busy in clean takes), Core/UI RSS; none recorded on 11-01 | **unconfirmed** | B4 rows |
| Start memory state | MemFree before a take ranged 275-2,758 MB and tracked the arm; never controlled | **measured** | recorded every take; set in B1 and B3 |
| A natural control | cinepi-raw writes with `POSIX_FADV_SEQUENTIAL` only, no DONTNEED, no `fsync` (`cinepi/dng_encoder.cpp:2356`): the `off` regime. The CineMate handbook holds no clean take at this data rate (grep; **probable**), so the control does not exist yet | **confirmed** (code) | none planned |

## 8.3 Test plan

Rules for every test: Patrik runs `sudo` (one reviewed root script per step, below); nothing else on the Pi during a take
(`cc1plus|gmake|cmake` checked before and after); WebUI closed; 3- or 10-minute takes with 1 Hz counts; `[storage]
buffer=ram` unless a test says otherwise; delete **only the take's own clip folder**, read from its `recording clip:` line
(never a `cDNG_*` glob: it matches every clip Core ever wrote, Patrik's included); restore Patrik's ladder after each take;
NVMe <= 40 C at the start of a scored unit, with 5-10 min of cool-down per 10-min take; `vcgencmd get_throttled` per take.

Overview. About **14 h** of Pi time on the unconditional path (B0, B1, B2's first two rows, B3, B4 + T1, U1, B6, B7, B-lossy) over five evenings, up to ~20 h if every conditional
block runs; ~8-10 TB written (**probable**; cool-down rates unmeasured). B1 and B3 decide.

| # | Test | Question | Takes | Duration | Writes |
| --- | --- | --- | --- | --- | --- |
| B0 | Prerequisites, record checks, installs | facts that fix every number; the transcript's deltas; self-describing builds; the shipping UI; one reboot | none | 1.5-2 h | - |
| B1 | Interleaved `writer` vs `sync`, restart-pair units | is the mode the lever, and is G or a stall present? | 2 blocks x (1 warm-up + 4 units x 2) x 3 min; +1 block | ~2 h 20 min (+70 min) | 1.35 TB (+0.7) |
| B2 | Mechanism takes (unscored, conditional rows) | G vs A/H/I/E; the UI dose-response under `writer`; WebUI under `sync`; swap | 2-12 x 3 min | 1-2 h | 0.15-0.9 TB |
| B3 | #80's changes and drive fill, start state set | does any knob or fill matter once the watermarks are exercised? | 7-9 x 10 min, two evenings | 4-5 h | ~2.2 TB + ~1 TB fill |
| B4 + T1 | A0's position, then within-boot build-up under `writer` | position or regression; what builds and in which process | 1 x 10 + 3-6 x 3 min | ~1.5 h | ~0.7 TB |
| T2 | Bisect since A0 (only if T1 loses from minute 1) | UI, Core or driver | 4-8 x 3 min each | 1-2 h | 0.3-0.6 TB |
| U1 (+U2) | UI branch under `sync` | does the branch cost anything once the regime is gone? | 4 x 3 min + 2 x 20 s | ~1 h (+ a UI build if needed) | 0.3 TB |
| B5 | Co-factors (conditional) | CSI-2 overflow, CPU0 placement, kswapd competition, NeoRotary, the 1440 control | 1-4 x 3-10 min | 1.5-2 h | 0.25-1 TB |
| B6 | Done-means | target 1 on two boots, and as shooting runs | 5 x 10 min | ~1.5 h | 1.25 TB |
| B7 | Target 2 | 4K SDR 12-bit 33 fps, lossless and uncompressed | 2 x 10 min | 30-40 min | 0.5 TB |
| B8 / U3 | UI switches under `sync` (only if B6/U1 show UI-correlated loss) | do the parked mitigations measure anything? | pairs of 3 min | 25-50 min | 0.2-0.4 TB |
| B-lossy | Lossy DNG at SDR | does lossy (no sync thread, behaves as `off`) cost frames? | 1 x 10 min | ~15 min | 0.08 TB |

**B0. Prerequisites (no take).**

1. **Facts** (M0, ~1 min; Patrik pastes the output into section 2). Reading: PAGESIZE 16384 confirms every byte figure
   in 8.1; 4096 means divide by four. The node count fixes the per-node watermarks and the kswapd count. A swap device on
   the SD card makes H plausible; zram makes it cheap.
2. **Record checks** (~2 min). Start with `journalctl --list-boots` (is the journal persistent; which boots hold 10-30 and
   11-01). Then, by date and not `-b -1` (21:50-23:13 spans boots 1 and 2):
   - `journalctl -u apertar-core --since "2026-11-01 21:50" --until "2026-11-01 23:13" --no-pager | grep -E 'media: trim|delete'`:
     a `result=trimmed` line after 22:47 and before 23:02 means #78 ran on clean NAND.
   - `journalctl -u apertar-core --since "2026-11-01 23:11:00" --until "2026-11-01 23:12:10" --no-pager | grep 'drop\['`:
     few lines with `dt_us` >> 80,000 = a few episodes; many single-frame lines = a rate change.
   - A0's boot age: `journalctl -b <10-30 boot id> -u apertar-core -o short-monotonic | grep 'recording clip'`: < 1,800 s =
     early in its boot; > 20,000 s = hours.
   - `journalctl -u apertar-core -b | grep -E 'RAW buffers|cached DMA'` (which heap).
   - `git -C ~/ApertarUI-a0 log --oneline -5` and `git -C ~/ApertarUI-a0 merge-base --is-ancestor ea44bd7 HEAD && echo descends`
     (`1cf98ad` is in no clone; the worktree path already exists, so never `worktree add` there).
   - `ls /etc/systemd/system/apertar-core.service.d/` (`zzz-ab-buffers.conf` gone; `capture-priority.conf` harmless).
   - `df -B1 /media/RAW` (volume size in bytes).
3. **Transcript** (M2, no take): every `take3.sh` "compaction during take" line of #70-#80, and #80's `capture stats` /
   `recording stats` lines, into section 2. Readings: `pageoutrun` 0 in #80 closes the `min_free` point. `allocstall_*` in
   the thousands and `pgscan_direct` in the millions under `writer` = a direct-reclaim regime. Written pages -
   `pgsteal_kswapd` - `pgscan_direct` - delta `Cached` = the minimum the fadvise freed: ~1.1-1.6 M pages per take refutes
   "frees nothing" by measurement and makes M1 important. `allocstall` ~0 does **not** isolate C/E/UI: G, H, compaction and
   CMA remain.
4. **Code** (Patrik decides; one commit, one build, never during a take): add ` dontneed=<mode> writeback=<on|off>
   sync_ms=<N>` to the `recording clip:` line after `media_fs=` (`CameraController.cpp:4346-4356`; the KB parser reads only
   the first fields, `takes_from_journal.py:47-48`). Build `adac040`+1 with `cmake --build ~/ApertarCore-build -j2`, remove
   the old `/run` `dontneed.conf`, restart, confirm the line says `sync`. The knob-text corrections wait for M1 (8.4).
5. **Script** `take3v3.sh` (from `take3v2.sh`, which already has `pgsteal_direct`, `pgscan_direct_throttle`, `pswpin`,
   `pswpout`), **unprivileged**:
   - add to `KEYS`: `allocstall_dma allocstall_dma32 compact_stall compact_fail compact_success cma_alloc_success
     cma_alloc_fail pgmajfault workingset_refault_file workingset_refault_anon workingset_activate_file`;
   - before each take: `MemFree Cached MemAvailable Slab SReclaimable SUnreclaim Buffers`, `VmRSS`/`VmSwap` of Core and UI,
     `df /media/RAW`, uptime in seconds, SoC and NVMe temperature, `vcgencmd get_throttled`, the arm from
     `/proc/$(systemctl show -p MainPID --value apertar-core)/environ` (not `pgrep -f ... | head -1`, which can hit a
     `journalctl -fu` and misses an old UI path);
   - 1 Hz to `/dev/shm/take-N.log` (never `/media/RAW`): the `KEYS`, `MemFree Dirty Writeback`, field 8 of
     `/sys/block/nvme0n1/stat` (write ticks; per-second delta over write-count delta = mean write latency), `boost` per zone
     from `/proc/zoneinfo`, PSI if on, and M5;
   - G1 during minute 2; the Orphanded count from `journalctl -k -b --no-pager | grep -c Orphanded`.
6. **Root script per step** (`b1-arm.sh <writer|sync>`, reviewed by Patrik, run as `sudo sh b1-arm.sh writer`): writes the
   `/run` drop-in, `daemon-reload`, restarts Core, sets the tracefs events (buffer size only after a reboot), reads
   `csi2_errors` once to discard, and prints every value it changed. It replaces ~4 `sudo` blocks per take, and keeps the
   timing realistic after reboots, when `sudo -n` asks for the password (section 6).
7. **One reboot**: `sudo cp /boot/firmware/cmdline.txt /boot/firmware/cmdline.txt.bak-20261102`;
   `sudo sed -i '1 s/$/ psi=1 rp1_cfe.track_csi2_errors=1/' /boot/firmware/cmdline.txt`; `wc -l` must print 1; reboot. Both
   flags are a fixed difference from 11-01 for the whole campaign (PSI adds per-switch accounting). Restore from the backup at
   the end. The reboot also resets the hand `sysctl`.
8. **Installs** (TUNE stays unset): the `apertar-media-tune` helper and `config/apertar-media.sudoers` with the README's trim
   pattern (`README.md:307-313`): `install -m 0755 -o root -g root`, `install -m 0440`, `visudo -cf`, then a `sudo -n` proof.
   No `linux-perf` (tracefs covers M6; if perf is wanted later, `apt-cache policy linux-perf` against `uname -r` first).
9. **UI** (Patrik decides): the four reverts of 8.4 and one UI rebuild now, so every test from B1 on runs the UI that would
   ship. If he declines, keep `c13b846` through B6 and add one confirming 10-min take after the revert. Baseline UI for
   U1/T2(a): the existing `~/ApertarUI-a0` if it descends from `ea44bd7` and is A0-era; otherwise
   `git -C ~/ApertarUI worktree add ~/ApertarUI-ea44bd7 ea44bd7` and build it now (10-20 min, **unconfirmed**).
10. **Drive and state**: ask Patrik once what on `/media/RAW` must be kept. Write `/media/RAW/warm.bin` (2.5 GB, once) for
    the start-state control. `sudo nvme smart-log /dev/nvme0` (baseline `data_units_written`, `percentage_used`, thermal
    counters; any `critical_warning` != 0 = stop).
11. **Pre-register** B1's rule and the evening restore list (below) in the KB before the first B1 take.

**B1. Interleaved `writer` vs `sync` (the claim's core).**

- Question: with the UI drawing (peaking + zebra on, audio meter in one written state), does `writer` lose more frames at
  capture than `sync` on the same boot, in random order, from the same start state; and is the per-frame cycle slower (G)?
- Fixed: Core `adac040`+journal line; mode by the `/run` drop-in in **both** arms (`Environment=APERTAR_DNG_DONTNEED=<arm>`,
  verified in `environ`: Core prints nothing for a valid value, `CdngEncoder.cpp:86-93`); `SYNC_MS` 1000, `WRITEBACK` on;
  stock sysctl; `buffer=ram`; the UI from B0.9 with no switch; 4K Clear HDR 16-bit uncompressed 25 fps; tracefs buffer 8 MiB
  per CPU set once after each reboot.
- Unit (the scored element): `sudo sh b1-arm.sh <arm>` (restart; Core's mount trim and pre-roll follow,
  `ApertarCoreApp.cpp:10904, 11272`) -> `cat /media/RAW/warm.bin > /dev/null` and record MemFree (equalizes the start: on
  11-01 the arms began at 275-327 vs 507-788 MB; this puts `sync` in its least favourable state, that of #74/#75/#78) ->
  **P1**, 3 min -> **P2**, 3 min, no restart, no delete (the #69 -> #70 positions) -> delete the unit's two folders (Core's
  free-space trim follows, `:10856-10861`) -> cool to <= 40 C.
- Block: reboot -> one unscored 3-min `sync` warm-up take (no unit is first after boot) -> 4 units, 2 per arm, in one of the
  6 balanced orders drawn with a die before the block and written into the KB. Two blocks; extension: a third block in a
  freshly drawn order.
- Analysis (fixed in advance, all one-sided, writer > sync): per-unit lost = P1 + P2; exact permutation test stratified by
  block. Attainable minimum p: 1/36 = 0.028 (2 blocks), 1/216 = 0.0046 (3). Manipulation check: `pgsteal_kswapd` >= 10x higher
  in every `writer` take than in every `sync` take, or the run is void (the drop-in did not take). Covariate: MemFree before
  P1 and P2. Also reported: P1 and P2 separately per arm.
- Duration: per unit ~15 min (restart + pre-roll 1.5, preload 0.5, two takes 6 + stats 1, delete 0.5, cool-down 5); per
  block ~70 min with the reboot, the password and the warm-up; **~2 h 20 min**, +70 min for the extension block.
- Decision rule:
  - **p <= 0.05** and the manipulation check holds: the mode is the lever at the take level (Q1 settled).
  - **0.05 < p <= 0.2**: run the third block, then decide on all three.
  - **p > 0.2**: no mode effect shown with a restart per unit. Before calling it chance, compare `writer` P2 here with B4's
    positions 3-4 (no restart): B4 losing and B1 clean = process age or position is the lever, not the mode.
  - **Position**: `writer` P1 clean and P2 losing in both blocks reproduces #69 -> #70.
  - **G** (G1 per take; G2 in B2): IPC lower and cycles/frame higher under `writer` at equal instructions = G present.
  - **Stall** (per losing take, M4/M5 on the 1 Hz loss times and the CFE holes): a Core or libcamera thread in `_begin`
    with >= 20 ms episodes, and P(hole within 100 ms after an episode) above the take's base rate and above the same figure
    under `sync` = A (a `throttle_direct_reclaim` sleep comes before its `_begin` line, `vmscan.c:6525-6529`, and is invisible
    there: M6 sees it; `pgscan_direct_throttle` is system-wide and names no thread). Wait (field 2) growing >= 40 ms in losing seconds = C (B5 pins every kswapd). `majflt` rising in losing
    seconds = H. None of these, with G present = G alone. None, with G absent = B2 (M3, M6).

**B2. Mechanism takes (unscored; rows after the first two only if B1 points at them).**

| Test | Setup | Takes | Decision rule |
| --- | --- | --- | --- |
| G2 libcamera stage timing | one `writer` and one `sync` take with the merged `LIBCAMERA_LOG_LEVELS` drop-in, Core restart, 30 s window, `libcam_stages.py` | 2 x 3 min | back-end start interval median > 40 ms under `writer` + UI and <= 40 ms under `sync` = G; both <= 40 ms = G out |
| M1 + M8 + M6 | one losing `writer` take, one `sync` take: function tracer on `lru_add_drain_all lru_cache_disable` (60 s), `mm_filemap_delete_from_page_cache` per comm (10 s), the `sched_switch` stacktrace trigger on CameraManager, IPA and copy-worker tids; LatencyTOP on the `writer` take only | 2 x 3 min | M1: callers = Core's writer threads at ~25/s = the drain exists (8.1 row 2 wrong); only CMA/GUP callers = not Core's; ~0 = struck. M8: fadvise's share of frees. M6: the sleep path names A, H, I or B |
| UI dose-response under `writer` | one unscored `writer` take, then six 3-min `writer` takes at positions 2+ of one Core process, `APERTAR_UI_PREVIEW_RECORDING_FPS` unset / 0 / 12 / 12 / 0 / unset (UI restart per change) | 7 x 3 min | monotone 0 < 12 < unset again = the GPU work drives the losses; with G1: IPC falling with preview rate = contention (G), IPC flat with a reclaim stall on the UI's threads = allocation-driven (A) |
| WebUI under `sync` (#76) | after one clean `sync` take, one 3-min `sync` take with one passive WebUI tab | 2 x 3 min | losses with flat `pgsteal_kswapd` = the completion-thread downsample loses frames without the regime; keep the client rule as a hard rule and consider `APERTAR_WEB_PREVIEW_RECORDING_FPS=0` while recording |
| Swap (H) | only if M0 shows swap and M5 shows `majflt`/`pswpin` in losing seconds: one `writer` take after `sudo swapoff -a` (restore `swapon -a`) | 1 x 3 min | clean = anon reclaim is the coupling (H) |
| Watermark boost | only if `boost` is non-zero most of a `writer` take: one `writer` take with `vm.watermark_boost_factor=0` (restore 15000) | 1 x 3 min | fewer losses and less kswapd time = boost-driven reclaim matters; a cleaner kernel knob test than `min_free_kbytes` |

**B3. #80's changes and drive fill, with the watermarks exercised.**

- Question: once a `sync` take actually meets the watermarks, does `min_free_kbytes`, the helper's set or fill change the
  losses; what carried #78's minute 10?
- Common: `sync` (the build's default, no drop-in), Core restarted per cell, UI as B1, `buffer=ram`, 10-min takes. **Start
  state set**: `cat /media/RAW/warm.bin > /dev/null`, record MemFree (target 0.3-0.8 GB, as #74/#75/#78). A cell counts for a
  knob question only if its `pageoutrun` delta is > 0; otherwise it is void for that question. Knob cells run **through the
  helper** (`sudo /usr/local/libexec/apertar-media-tune apply nvme0n1 pi-nvme exfat`; `restore` after), so a cell equals what
  would ship; `min_free_kbytes` by hand only where named. Reset: `sudo sysctl vm.dirty_ratio=20 vm.dirty_background_ratio=10
  vm.min_free_kbytes=16384`, then read back all five (`20 10 0 0 16384`); writing 0 to `dirty_bytes` or
  `dirty_background_bytes` returns EINVAL (minimums 2 pages and 1, `page-writeback.c:2295, 2308-2313, 2330`).
- Fill (evening 2, once, reused): write 16.6 MB files to 50 %, delete every other one (Core's free-space trim follows: verify
  the `media: trim` line), then write 16.6 MB files to 72 %, the fill at which #78 started. This leaves fragmented free space
  like #78's on trimmed NAND (~30 min). A single `fallocate` file is the cheap variant but under-reproduces fragmentation
  (**probable**). Remove the fill files at the end of the evening.

| Cell | Evening | Sysctl | Fill at start | Replicates |
| --- | --- | --- | --- | --- |
| (a) | 1 and 2 (anchor) | stock | empty | #74/#75 at 10 min, from their start state |
| (b) | 1 | helper set (dirty pair, scheduler, `nr_requests`, `rq_affinity` 2, writeback 150 / expire 3000 cs, APST 0) | empty | #80 minus `min_free`, as it would ship |
| (c) | 1 | `min_free_kbytes=65536` only | empty | #80 minus the dirty pair |
| (e) | 2 | stock | 72 % | #78's drive state |
| (c') | 2 | `min_free_kbytes=65536` only | 72 % | where the knob would matter |
| (d) | 2 | helper set + `min_free_kbytes=65536` | 72 % | #80's knobs in #78's drive state |

- Order: random within each evening (die), (a) first on evening 2 as the anchor for the evening effect. Two takes for any cell
  whose reading would change a decision: one take classifies weakly (a true 20-per-10-min residual passes "clean" in ~25 % of
  single takes under k = 1).
- "Clean" = <= 5 lost and no minute >= 3. "Near-full effect" = minutes 9-10 carry > 60 % of the losses with NVMe write latency
  rising in the same minutes. "Memory effect" = losses spread across minutes with `pgsteal`/`allocstall`/PSI and flat latency.
- Decision table (evening 1, valid cells only):

  | (a) | (b) | (c) | Reading |
  | --- | --- | --- | --- |
  | clean | clean | clean | `sync` alone suffices on an empty drive; no knob shown to matter; ship none; evening 2 decides near full |
  | loses | clean | loses | the helper's set helps; repeat (b) and (a); if it holds, the whole set is the candidate (which of its knobs: split only if Patrik wants fewer) |
  | loses | loses | clean | `min_free_kbytes` helps; repeat; then the `MINFREE` column (8.4) |
  | loses | clean | clean | both help; prefer the helper set (exists, no new code); (c') decides whether `min_free` is needed near full |
  | loses | loses | loses | a `sync` residual exists at this start state and the knobs do not cure it: B2 for the mechanism |
  | clean | loses | any | the helper set costs frames: never ship it |
  | clean | any | loses | `min_free_kbytes` costs frames: never ship it |

- Evening 2: (e) clean = filesystem fill is innocent at 72-97 %. (e) losing in minutes 9-10 with rising latency and (d) or (c')
  clean = the knob cures the near-full regime. (e), (c'), (d) all losing late = fill beats the knobs: cap usable fill or set a
  format rule (Patrik decides).
- NAND-stall cell (the old (f): >= 0.9 TB untrimmed, `APERTAR_MEDIA_TRIM=0`): **dropped**. It is the state in which the
  controller died on 2026-10-30 (`Disabling device after reset failure`, exFAT read-only, `hardware-log.md:714-720`; exFAT has
  no journal), and its value is low: #78 had no queue-full signature, and Core already trims at mount, after any delete >= 1 GiB
  made outside Core and after every pre-roll (`ApertarCoreApp.cpp:10856-10861, 10904, 11272`; `README.md:305`; the draft's
  "Core trims only on deletes it sees" was wrong). Only with Patrik's explicit OK, nothing of value on the drive and
  `fsck.exfat` at hand: `TRIM=0` and a Core restart **before** the preparation, zero `media: trim` lines verified, stop at the
  first queue-full burst, then remove the drop-in and `fstrim`.
- Duration: (10 rec + 5 set-up + 5-10 cool-down) per take, 7-9 takes, + the ~30 min fill: **4-5 h** over two evenings.

**B4 + T1. A0's position, then within-boot build-up under `writer`.**

- Question: is today's stack clean in A0's position (no regression), and what builds across consecutive `writer` takes, in
  which process?
- T1 setup: reboot; uptime fixed and recorded: A0's from the B0 monotonic check, else 30 min idle after boot; NVMe <= 40 C
  (A0: 34 C); `[storage] buffer=frames` (A0's mode; restore `ram` after); `writer` via `b1-arm.sh` (a Core restart, as A0;
  Core now adds a pre-roll A0 did not have); UI from B0.9 with aids on; **T1 = one 10-min take**, full `take3v3.sh` key list
  (this also makes A0's position a kernel data point).
- T1 rule: **0-2 lost**: today's stack is clean in A0's position; A0's cleanness was position; "regression since A0" closes.
  **Clean for <= 4 min, then losing**: time since boot or process age, not code (as #69 -> #70). **Losing from minute 1** at
  >= 10 per 3 min: a change since A0: T2.
- B4 (same Core process and `frames` setting as T1): three 3-min `writer` takes back to back, no
  restart, no delete (#70-#72's positions; 250 + 225 GB fits). Before every take: `MemFree Cached Slab SReclaimable SUnreclaim
  Buffers`, `pswpin pswpout`, `VmSwap VmRSS` of Core and UI, `/proc/buddyinfo`, `sudo grep -E 'exfat|buffer_head|dentry'
  /proc/slabinfo` (in the root script). If they lose, one take after each step, in this order, stopping at the first clean
  take: (i) restart only `apertar-ui-direct` (clean = the UI process carries the build-up); (ii) restart Core (clean = Core's
  process, or the trim and pre-roll that come with it); (iii) `echo 3 > /proc/sys/vm/drop_caches` (clean = reclaimable state).
  Still losing with `VmSwap`/`pswpin` rising = swap; with `buddyinfo` degraded and RSS flat = fragmentation. n = 1 per step.
- Duration ~1.5 h. Writes up to ~0.7 TB (fill stays <= 70 %).

**T2. Bisect since A0 (only if T1 loses from minute 1).** One change per run, cheapest first; the first clean arm names the
side:

- (a) **UI**: the baseline UI (B0.9) vs the shipping UI under `writer`, at positions 2+ of one Core process (one unscored take
  first), order ABBA with a UI restart per switch, 3 min each. This, not U1, is the UI half of the A0 question.
- (b) **Core**: `a40112a` built in a second build directory with today's UI (20-30 min build, never during a take).
- (c) **Driver**: `24172e6` via `setup.sh` + DKMS + reboot (~2 x 10 min); check `get_state` ready and the mode list; restore
  `cd548ef` the same evening.

**U1 (+U2). The UI branch under `sync`.** Only "does the branch cost anything once the regime is gone"; it cannot close the
A0 question (both arms are predicted clean under `sync`).

- Setup: `adac040` default, stock sysctl (or B3's winner), drive trimmed and below 50 %, `buffer=ram`, peaking + zebra on,
  audio meter as Patrik runs it. Switch `ExecStart` with a `/run` drop-in + `systemctl restart apertar-ui-direct`. Order
  shipping, baseline, baseline, shipping (ABBA), 3 min each, as positions 2+ (one unscored take first). `pidstat -p <ui pid> 1`.
  U2: `QSG_RENDER_TIMING=1` for one 20 s `ram`-mode take per build (not counted); frames logged per second.
- Duration ~1 h (+ the baseline build if B0.9 needed one).
- Rule: both arms 0: the branch adds nothing measurable under `sync` (bound per arm < 0.077 %, k = 1); keep/revert stands on
  code grounds. Baseline clean and shipping >= 3 lost in both its takes: split at `41ff827` and apply the `Behavior` fix first.
  U2: 25-30 frames/s = the preview drives redraws; 50-60 on the shipping UI only = the hidden animation runs: apply the fix.

**B5. Co-factors (only if losses survive B1-B3 under `sync`, or to close B1's `writer` mechanism).**

| Test | Setup | Duration | Decision rule |
| --- | --- | --- | --- |
| CSI-2 receiver | flag from B0.7; one losing `writer` take; `csi2_errors` read by the root script right before `record_start` (discard) and right after `record_stop` | 10 min | `OVLF` > 0 and comparable to the gap count: receiver starvation is a co-cause: run the 1440 pair. `LEN`/`UNMATCHED` > 0: lower the rate regardless. All zero while frames are lost: the loss is behind the receiver |
| 1440 Mbps control (only if OVLF > 0) | `link-frequency=720000000` in `config.txt`, reboot; `dmesg \| grep DPHY` silent; 4K Clear HDR 16-bit at 25 fps listed; one 10-min `writer` take; compare with 891 MHz at equal reclaim deltas; restore 891 MHz the same evening | 2 x 15 min + 2 reboots | clean at 1440 and losing at 1782 under the same memory numbers: the PHY clamp is a co-cause |
| kswapd competition (C) | during a losing `writer` take: `for p in $(pgrep '^kswapd'); do sudo taskset -pc 3 $p; done` (all of them, not `kswapd0` alone) | one 3-min take | losses fall: run-queue competition matters (C) |
| CPU0 placement | `taskset -pc 1` on CameraManager and the IPA thread (tids from `ps -L`); `grep nvme /proc/interrupts` twice 10 s apart. **Never** write `/proc/irq/*/smp_affinity` for RP1 interrupts | one 3-min take | gaps vanish on CPU1: CPU0's load matters. Unchanged: placement is out |
| NeoRotary poll | `poll_ms=1000` in `apertar-hardware.conf` + service restart (no hot-unplug); confirm the I2C rate fell | one 3-min take | a drop larger than the take-to-take spread: the poll costs; otherwise closed |

**B6. Done-means (target 1).** `adac040` default, B3's knobs only if B3 showed one engaging and helping (through the helper),
the shipping UI with peaking + zebra + audio meter on, `buffer=ram`. (i) Two 10-min takes on two boots, emptied and trimmed
drive. (ii) As shooting runs: three consecutive 10-min takes on one boot from an emptied drive (ends at ~75 %; from 30 % it
would overflow), no restart or delete between. Done = 0 lost in all five (per take: mean < 0.8 lost, < 0.0055 %, k = 1).
Anything else: the per-minute profile and the 1 Hz log say fill (B3), the regime (B1) or the UI (U1/B8). Hardware-log entry
after Patrik confirms. ~1.5 h.

**B7. Target 2 (4K SDR 12-bit at 33 fps).** Under the B6 configuration: lossless JPEG (COMP1, encoder cap 43-66 fps at 4K)
10 min at 33 fps; then uncompressed (~410 MB/s) 10 min. Lossless clean and uncompressed not: drive (~550 MB/s derived, #25)
and memory are both near their limit; prefer lossless for 33 fps. Both clean: done. 30-40 min.

**B8 / U3. UI switches under `sync` (only if B6 or U1 show UI-correlated loss).** Interleaved pairs of 3 min:
`APERTAR_UI_PREVIEW_RECORDING_FPS=0` vs unset; peaking off vs on; then, un-parked from `drop-count`/`preview-plane` only if
the first two pairs show a delta: `PEAKING=cpu` vs unset, `PREVIEW_PLANE=1` vs unset. `cap=0` vs unset no delta: the parked
commits stay parked. `cap=0` clean and unset losing: the peaking and plane pairs say which mitigation to un-park, the plane only
if it beats peaking-off. 25-50 min.

**B-lossy (SDR).** Lossy DNG has no Clear HDR in Apertar (`ModeLadder.hpp:227-228`, `CameraController.cpp:3022-3023`, commit
`e1c10cd`). One 10-min 4K SDR 12-bit Lossy 3:1 take at 25 or 33 fps; read `estimated_capacity_fps` first. Under the default
the sync thread gets no lossy files (`noteWrittenFile` is cDNG-only, `CameraController.cpp:5206`; lossy writes on
`LossyDngDiskWriter`'s thread, `LossyDngEncoder.cpp:236-290`), so lossy behaves as `off`. 0 lost: fine for the Lossy + Log
plan. Losses: route lossy files into `noteWrittenFile` and the sync thread (reuses `adac040`'s path and gives lossy the
pull-safety `fsync` it lacks), not a third drop path on the single lossy writer. ~15 min.

**Restore list (end of every evening; Patrik's next shoot inherits none of it):** `[storage] buffer=ram`; the sysctls (B3's
reset, read back); the helper's `restore` if B3 applied it; the fill files and `warm.bin` if Patrik wants the space;
`APERTAR_MEDIA_TRIM` drop-in gone; every `/run` drop-in gone (`dontneed.conf`, `LIBCAMERA_LOG_LEVELS`, UI `ExecStart`);
tracefs events off and `buffer_size_kb` back (or reboot); `link-frequency` 891 MHz; `kernel.latencytop=0`; swap on; the
imx585 driver `cd548ef`; Patrik's ladder. At campaign end: `cmdline.txt` from the backup; the baseline-UI worktree removed
when Patrik agrees. `sudo nvme smart-log /dev/nvme0` after each evening.

| Step | Risk | Change made in this plan |
| --- | --- | --- |
| `rm -rf /media/RAW/cDNG_*` (draft B1, B3, U1) | deletes Patrik's footage | delete only the take's own folder; ask once (B0.10) |
| untrimmed 0.9 TB with `TRIM=0` (draft B3(f)) | NVMe controller death, exFAT read-only (10-30 record) | dropped unless Patrik explicitly asks |
| RP1 MSI parent affinity (draft B5) | moves ssh/USB/I2C/camera IRQs at once | removed |
| `cmdline.txt` edit | unbootable headless camera | backup, single-line `sed`, `wc -l` = 1 |
| sudoers install | broken `sudo` or a root escalation | README pattern with `visudo -cf` |
| 64 MiB per-CPU trace buffer, `perf.data` on disk | 256 MiB pinned / plausibly hundreds of MB of dirty cache (rate **unconfirmed**) inside the regime under test | 8 MiB per CPU; tracefs triggers, no perf |
| hot-unplug of the NeoRotary | I2C bus 1 hang | `poll_ms` |

## 8.4 What to do with the code (recommendations; Patrik decides)

| Item | Recommendation | Why |
| --- | --- | --- |
| Core `adac040` (`sync` default) | build it in B0; keep `writer` reachable for B1; gate `main` on B6 only | The sync-mode drop is correct (`fsync`, then DONTNEED on an `O_RDONLY` fd of a closed, complete file evicts all of it including the last page: `CameraController.cpp:4703-4712`, `fadvise.c:131`, `truncate.c:288-303`). The counters show the regime gone. B1 cannot gate a default that stays right on the counters whatever B1 shows |
| The knob text | after M1: `README.md:324` and the comment at `CameraController.cpp:4707-4708` drop "costs a cross-CPU LRU drain per frame" and say "the pages are still dirty or under writeback then, so the call frees little and the page cache fills until the kernel reclaims during the take"; same for `lessons/upstream-issues.md` #44 | refuted for folios under writeback by mm source; frequency unmeasured; `fs/exfat` not in the checkout. M1 costs one 60 s window in B2 |
| Journal line | add ` dontneed=<mode> writeback=<on\|off> sync_ms=<N>` to `recording clip:` (`CameraController.cpp:4346-4356`) before B1 | every take becomes self-describing; the parser is unaffected (`takes_from_journal.py:47-48`) |
| `APERTAR_MEDIA_SYNC_MS` | leave at 1000 | pull-safety needs the per-file `fsync` (C0010 vs C0011, 2026-10-26); with `0` the drop is off (one warning, `CameraController.cpp:4324-4331`) |
| `APERTAR_DNG_WRITEBACK` | leave on | in `sync` mode it is the only per-frame writeback kick (`CameraController.cpp:4668-4675, 5204-5205`); without it the `fsync` flushes a 415 MB burst per tick (C0005) |
| Small Core items (not before B1) | one `std::cerr` on a failed `open()` of the clip folder (`CameraController.cpp:4321`, the only silent way to lose the drop); fix the stale comments at `:4274-4276` and `:1452-1454` (exFAT gets 4 writers and +0 buffers, `MediaProfile.hpp:139-141`) | hygiene |
| Dirty limits and `min_free_kbytes` | install the helper and sudoers in B0 with `APERTAR_MEDIA_TUNE` **unset**. Run B3's knob cells through the helper. Add **no** `MINFREE` column until a take shows the knob engaging (`pageoutrun` > 0 at stock, and less reclaim or loss with it raised); then the column (65536 for tuned classes, guarded `mem_kb/64` under 2 GB) in `save_once`/`apply`/`restore` and a README row. Keep TUNE opt-in until B6 passes with the exact set. Stop calling the set "CineMate-style" | `TUNE=1` changes eight settings (dirty pair, scheduler `none`, `nr_requests` 512, `rq_affinity` 2, writeback 150 cs, expire 3000 cs, APST 0; `scripts/apertar-media-tune:73-100`), most never tested here; `rq_affinity` 2 moves block completions, which bears on CPU0. The opt-in was deliberate (`ApertarCoreApp.cpp:11357-11359`). #80 shows no knob engaged. `vm.watermark_scale_factor` would be the cleaner single kernel knob, with no precedent or measurement here |
| UI `68e1a41` (count chip) | keep | one `contains()` + compare per `buffer` event (<= 4/s); confirmed on the rig (18 = 18) |
| UI `c234d77` (`APERTAR_UI_PREVIEW_RECORDING_FPS`) | keep as the test instrument, never a default | B2's dose-response and B8 need it; it is the only way to switch the preview pipeline off during a take without `SIGSTOP` (which hangs the start at the audio open). Off = one `false &&` per preview frame (`ApertarPreviewSocketClient.cpp:29, 489`) |
| UI `322d329` (`APERTAR_PREVIEW_DIRECT`) | revert | a confirmed no-op with `hdmi_external_only=true` (`main.cpp:179, 438-439`); its journal line misleads |
| UI `a51c95e` (`PEAKING=fast`), `4724007` (`PEAKING=cpu`) | park on `drop-count`, revert from `drop-frames` | `fast`: no gain (8.83 %). `cpu`: 3.88 % under `writer` (below all baselines, n = 1) but it moves 0.9 MB of dma-buf reads, a 921,600-pixel loop and a 0.9 MB upload per preview frame onto the render thread (UI CPU 19.6 % vs 12 %); not needed under `sync`. Both add a sampler, branches and 4-6 GL calls per draw to the default shader (V3D flattening **unconfirmed**) |
| UI `c13b846` (`APERTAR_PREVIEW_PLANE`, +805 lines) | park on `preview-plane`, revert from `drop-frames`, do not merge | under `writer` the plane takes (0-3.4 %) lay below all baselines (n = 1 each, rising within the series); under `sync` it is not needed. When on it rewrites Qt's KMS env, writes a config file, starts a display thread and issues legacy `drmModeSetPlane` beside Qt's atomic flips (`DrmPreviewPlane.cpp:278-313, 389, 505`); when off it still adds a hard libdrm build dependency (`CMakeLists.txt:15, 226`) the README apt line lacks |
| Mechanics of the park | in B0: per commit `git revert --no-commit <sha>` (newest first: `c13b846`, `4724007`, `322d329`, `a51c95e`; tested clean in a scratch clone, result = `41ff827` + `68e1a41` + `c234d77`), each committed as `ui: <imperative>` with `Why:`/`What:`/`Tested:` and the trailer; four fork-log rows; rebuild the UI (not during a take). Push only when Patrik asks | nothing can be lost: `c13b846` and `4724007` are already in `origin/drop-frames`' history, and a revert keeps them reachable. `--no-edit` would give `Revert "..."` messages against the convention (`fork-log.md:77, 155`) |
| UI hygiene (optional, after U2) | `Behavior on width { enabled: root.bufferBarVisible; ... }` in `StatusChip.qml:106-107` and `ExternalMonitorWindow.qml:1124-1125` | stops the hidden bar animating; hygiene unless U2 shows 50-60 frames/s |
| Not to `main` yet | nothing from `drop-frames` until B6 passes; no `MINFREE` row before a take shows it engaging; the imx585 `cd548ef` driver should clear T1/T2 before anything depends on it | |

## 8.5 Open after this plan, and corrections to the record

Open questions the plan may not close:

1. **How the regime reaches capture**: G (no stall) or a stall (A, H, I, C, E). B1's G1 and M4/M5, then B2. If the cost sits in
   the UI's render thread and still costs capture frames, the coupling (GPU/HVS memory arbitration, L3, a shared lock) is beyond
   tracefs; the dose-response with IPC is the instrument.
2. **The accounting gap**: who freed the 18-24 GB per `writer` take that kswapd did not (M2's bound, M8). A large fadvise share
   turns 8.1's first row from "little" to "a measured fraction" and raises the drain's frequency.
3. **What builds within a process** under `writer` (#69 -> #71, #46 -> #50, A0 -> A2): B4's step order names the process; the
   state (slab, swap, fragmentation, RSS, UI GPU buffers) stays a candidate list.
4. **#78's last minute**: fill or a `sync` residual (B3 evening 2; the B0 trim and drop-line checks). NAND state is not tested
   (dropped cell). The exFAT near-full allocation cost itself (`fs/exfat` not in the checkout).
5. **The residual rate under `sync`**: 25 of 24,037 on 11-01, all in #78; B3 (a) and B6 bound it per take.
6. **A2's 10 %** (2026-10-30): one run, unexplained now that the hint was redundant; cheap repeat, low priority.
7. **Lossy and MLV under `sync`**: lossy behaves as `off` (B-lossy); MLV `fsync`s and walks the whole growing file once a second
   with no per-frame kick (`CameraController.cpp:4699-4700`; `MlvEncoder.cpp:68, 952, 965`), never run at 415 MB/s.
8. **The CSI-2 receiver** has never been read during a losing take (B5).
9. **Target 2** (B7), the Log check in Resolve, the trim acceptance test over a full pass, `nvme.max_host_mem_size_mb=0`, the RTC
   power-off test (section 7 and the project README).

Corrections to the record (new hardware-log entries after Patrik agrees; the log is append-only):

- 2026-11-01 last entry, **headline**: "`APERTAR_DNG_DONTNEED=sync` fixes it" (`hardware-log.md:1012`, confirmed after two clean
  takes, `:1043`) becomes "`sync` removes the reclaim regime (measured); that it removes the losses is probable pending B1
  (take-level p = 0.057, order-confounded)".
- Same entry, mechanism sentence: "frees nothing" -> "frees little (probable)"; "drains the per-CPU LRU lists on every core per
  frame" -> refuted for folios under writeback, frequency unmeasured; "~13 GB per 3-minute take" -> 49.5-56.5 GB at 16 KiB pages
  (M0 confirms the page size).
- 2026-11-01 "A0 was clean with it running (regression)": A0's boot age is unconfirmed (its stamps conflict across a crash and
  reboot); what A0 shares with #69 and #74 is being the first take of a fresh Core on a freshly trimmed drive. T1/T2 decide.
- 2026-10-30 A1/A2: "the per-frame writeback hint is needed" does not follow; `a40112a` had the per-frame DONTNEED
  (`CdngEncoder.cpp:1780`), which starts the file's writeback itself. A2 is one unexplained run.
- Night report section 2 / 8 (provisional): #80's "`min_free_kbytes` is the one that engages" -> not supported (no watermark
  reached); "CineMate's dirty limits" -> cinemate sets `dirty_bytes`/`dirty_background_bytes`/writeback intervals and no
  `min_free_kbytes`; #80's set is Apertar's own.
- Inspection numbers: `queue_budget` 1.40-1.55 GB on the compared takes (not 1.40-1.70); ~70 GB deleted before #78 (not ~140);
  DNG 16,590,340 B (not 16.9 MB); kswapd share 67-76 % (not 65-74 %); the take-level p 0.029 "with #80" withdrawn; #78's tail
  6.8e-7 per minute (not < 1e-12); the 2026-10-26 dirty 5-vs-5 removed as evidence for the dirty pair.
- Withdrawn suggestions: `/proc/irq/154/smp_affinity` (not user-movable); moving the RP1's PCIe MSI parent (probably no
  `/proc/irq` entry, and unsafe if it had one); dynamic debug `rp1_cfe +p` (not on this kernel); "exactly one unbounded sleep"
  (Q4 adds compaction, the NOPROGRESS throttle, CMA, major faults, and G, which needs no sleep); "MGLRU direct reclaimers never sleep in `reclaim_throttle`" (the NOPROGRESS throttle applies).
- `lessons/upstream-issues.md` #44: keep "the hard-coded per-frame DONTNEED frees little and the cache fills"; drop the drain
  clause after M1.
- #80's `capture stats`/`recording stats` lines and its `take3.sh` output go into the KB (the raw extract ends at 23:13:03);
  until then "0 of 15,025" and "kswapd 0" are session-reported.
