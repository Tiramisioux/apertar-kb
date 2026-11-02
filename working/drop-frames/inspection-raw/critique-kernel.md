# Critique of `verdict-draft.md` (section 8), kernel-mechanism lens

Critic: adversarial pass, 2026-11-02, desk only. Sources re-read for this pass: `kernel-rpi` @ `5bd564a` (`mm/`,
`include/linux/`, `kernel/latencytop.c`, `kernel/irq/msi.c`, `drivers/mfd/rp1.c`, `drivers/pci/controller/pcie-brcmstb.c`,
`drivers/media/platform/raspberrypi/rp1_cfe/cfe.c`, `arch/arm64/configs/bcm2712_defconfig`), Core `adac040` and `a40112a`,
`take3.sh`/`take3v2.sh`, night report sections 1-7, `hardware-log.md` 2026-10-26/30/31. **Not** in the checkout (so every
statement that depends on them is at most **probable**): `fs/` (exfat, mpage, sync.c, proc), `block/`, `kernel/trace/`,
`kernel/sched/`, `lib/Kconfig.debug`, `include/trace/events/`. Status words: **confirmed** (read in source or measured),
**probable** (inferred, reason given), **unconfirmed** (measurement named), **refuted**.

## 0. Verdict on the draft

**Needs revision.** The draft's corrections of the night report hold (the per-frame drain branch is not taken by a
fully-under-writeback file; the dirty pair is inert; the 16 KiB-page arithmetic). But five of its own kernel statements are
wrong or overstated, two of them load-bearing for the plan:

1. **`min_free_kbytes` "probable: yes" is contradicted by #80's own counters** (K1). #80 never reached even the *raised*
   low watermark, so the knob changed no allocation decision in that take. The B3 cells as written will reproduce that
   condition and cannot separate the knobs.
2. **"Frees nothing (confirmed)"** is only confirmed for folios still under writeback when the walk reaches them; the
   window is milliseconds, not microseconds, and the take's own accounting leaves 20-26 GB unexplained (K2). This row and
   the "drain refuted" row are one timing-dependent hypothesis; the transcript's numbers can test it without a take.
3. **"Exactly one unbounded sleep ... needs that thread to allocate a page"** omits refault/swap-in I/O, direct compaction,
   CMA migration and the 2026-10-26 throughput-deficit mechanism the KB itself measured (K3, missing items 1-3).
4. Two **decision rules misread the source**: a throttled thread *does* emit `mm_vmscan_direct_reclaim_begin` after its
   sleep (K5), and kcompactd does *not* run the cross-CPU LRU drain in 6.12 (K6).
5. The model ignores **fake NUMA** (probably 8 nodes, 8 kswapd threads, per-node watermarks; K7), and B1 allocates a
   **256 MiB** trace buffer on every take of the experiment that measures memory pressure (K8).

---

## 1. Refuted or weak claims

### K1. "`min_free_kbytes` 64 MiB did it: probable yes" (8.1 row; Q2; 8.4 "expect ... `min_free_kbytes` to be the knob")

- What the source says (**confirmed**): kswapd is woken only from the allocation slow path, which is entered when the fast
  path fails at `ALLOC_WMARK_LOW` (`mm/page_alloc.c:4836`, wake at `:4375`). `pgsteal_kswapd` and
  `kswapd_low_wmark_hit_quickly` can only grow after such a wake (`mm/vmscan.c:7119, 7163`, MGLRU eviction counts).
- What #80 measured (**measured**, night report section 2): `pgsteal_kswapd` **0**, low-watermark hits **0**, MemFree at start
  2,758 MB.
- Reading: in #80 free memory stayed above the raised low mark (80 MiB total) for 10 minutes, so it was also above the stock
  low mark (20 MiB). No allocation in #80 consulted a watermark that the sysctl moved. The only live effect of the raised
  value in #80 is the size of the per-CPU free lists (`pcp->high` is derived from the low watermark,
  `mm/page_alloc.c:5697-5701`): a microsecond-scale lock-traffic effect, not a frame-period one (**probable**).
- Why #80 never got near the watermarks (**probable**, from `syncLoop`, `CameraController.cpp:4689-4718`): in `sync` mode the
  take's page-cache footprint is bounded at roughly the files of the last 1-2 sync ticks, about 0.4-0.85 GB at 415 MB/s.
  #74/#75 started at 507-646 MB free and had to reclaim (47-58 k pages); #78 started at 788 MB and reclaimed 586 k pages in
  10 minutes; #80 started at 2,758 MB and never had to. The draft's "the empty cache is worth ~6 s" is `writer`-mode
  arithmetic (cache fill) applied to a `sync` take, where an empty start is worth **the whole take**.
- Consequence: #80 does not discriminate between its three changes. It shows "a `sync` take whose free pool stays far above
  the watermarks is clean", which no one disputes. **Refuted** as support for `min_free_kbytes`; the knob's effect is
  **unconfirmed**.
- Fix: (a) relabel the row "unsupported by #80 (watermarks never reached)"; (b) copy #80's `pageoutrun` and
  `compact_daemon_wake` deltas from the transcript (`take3.sh` prints them in its `S()` list): `pageoutrun` 0 closes the point
  (`count_vm_event(PAGEOUTRUN)` runs once per `balance_pgdat`, `mm/vmscan.c:6870`); (c) B3 must fix the start state, or
  cells (a)-(c) on an "empty" drive repeat #80 by construction. Before every B3 cell: `echo 3 > /proc/sys/vm/drop_caches`,
  then read a fixed amount of clean file data from the SD card (for example `cat /var/tmp/warm.bin > /dev/null`, sized so
  that MemFree is ~300 MB, the `writer`-era level), record MemFree, start. A cell counts for the knob question only if its
  `pageoutrun` delta is > 0 (the watermarks were exercised); otherwise it is void for that question.

### K2. "`writer`-mode DONTNEED frees nothing: confirmed (source) ... only pages whose I/O completed in the microseconds before the walk can go"

- Confirmed part: folios under writeback are skipped by `find_lock_entries` (`mm/filemap.c:2121-2125`) and refused by
  `mapping_evict_folio` (`mm/truncate.c:293`); `__filemap_fdatawrite_range(WB_SYNC_NONE)` runs first (`mm/fadvise.c:113-115`).
- Weak part: the walk starts after `do_writepages` has processed ~1,013 folios (lock, clear dirty, set writeback, bio build;
  kernel.md itself estimates "a few ms"), after `lru_add_drain()` (`fadvise.c:156`), and after any preemption of a nice-0
  writer on a saturated 4-core board. The first bios are in flight for that whole time (plug flushing in `block/` is not in the
  checkout: **probable**). At ~800 MB/s, 2-5 ms complete 1.6-4 MB, i.e. 10-25 % of a 16.6 MB file, before the walk reaches it.
  "Microseconds" is wrong; "nothing" is a timing claim, **unconfirmed**.
- The take's own accounting points the other way (**measured**): `pgsteal_kswapd` 3.02-3.45 M x 16 KiB = 49.5-56.5 GB against
  ~74 GB written, so 18-25 GB per take (24-34 %) were freed by something other than kswapd. Candidates: direct reclaim or the
  fadvise's own frees. `take3.sh` recorded `pgscan_direct` (an upper bound on direct-reclaim frees) but not `pgsteal_direct`.
- Coupling the draft misses: the drain branch (`fadvise.c:166-170`) needs a folio that is *returned* by the walk and refused
  (`truncate.c:527-531`). Returned folios are exactly the ones whose I/O completed before the walk; refused-and-returned ones
  are those still holding an extra reference in a remote CPU's `lru_add` batch (writer migrated during its one 16.6 MB
  `write()`). The more the fadvise frees, the more often the drain branch can fire. Rows 1 and 2 of the 8.1 table stand or
  fall together.
- Fix (no take needed): from the transcript, fadvise frees >= written pages - `pgsteal_kswapd` - `pgscan_direct` -
  delta(Cached). If that lower bound is ~1.1-1.6 M pages per take, "frees nothing" is refuted by measurement and M1 becomes
  important; if `pgscan_direct` covers it, "nearly nothing" stands. Direct per-actor count in one 10 s window of each mode:
  `events/filemap/mm_filemap_delete_from_page_cache` (`mm/filemap.c:231, 341`), counted per comm
  (`awk '{print $1}' | sed 's/-[0-9]*$//' | sort | uniq -c`): writer threads = fadvise frees, `kswapdN` = background
  reclaim, the sync thread = `sync`-mode drops, anything else = direct reclaim by that task. ~25 k events/s: use a 10 s
  window with an 8 MiB per-CPU buffer.

### K3. "the kernel offers exactly one unbounded sleep for a user thread here, `throttle_direct_reclaim` ... and it needs that thread to allocate a page"; "the only kernel mechanisms for a 40 ms stall of a user thread: direct reclaim ... and `throttle_direct_reclaim`"

**Refuted as a complete list.** Other user-thread sleeps that the `writer` regime makes more likely, all in the checkout:

| Mechanism | Source | Needs a malloc on the stalled thread? |
| --- | --- | --- |
| Major fault on an evicted file page (binaries and libraries on the SD card) or swap-in of cold anon (Core's warm raw pool, libcamera/IPA heaps, the UI) | `workingset_refault_*` (`include/linux/mmzone.h:172-174`), `PGMAJFAULT` (`vm_event_item.h:37`) | **no**: an I/O sleep on a page the thread already owns |
| Direct compaction for order > 0 allocations (>= 32 KiB with 16 KiB pages; slab, skb, DMA, GEM) | `__alloc_pages_direct_compact` counts `COMPACTSTALL` (`page_alloc.c:3790`); sync compaction sleeps `HZ/50` per `too_many_isolated` loop (`compaction.c:903`, `vmscan.c:575-576`) | kernel-side allocation |
| CMA / `alloc_contig_range` (dma-heap `linux,cma`, vc4): `lru_cache_disable` = `synchronize_rcu_expedited` + forced drain of every CPU (`swap.c:904-922`, called at `page_alloc.c:6548`), then synchronous migration that waits for writeback of page-cache folios in the CMA area (`mm/migrate.c`, MIGRATE_SYNC) | as cited | kernel-side allocation, by whoever allocates CMA |
| `reclaim_throttle(NOPROGRESS)`, 1 jiffy = 4 ms at HZ 250 (`kernel/Kconfig.hz:8`) | `vmscan.c:6129` via `shrink_zones` `:6223`, outside the MGLRU hand-off | yes |

Also wrong in detail (**confirmed**): `throttle_direct_reclaim` judges only the **first usable node** of the zonelist
(`vmscan.c:6454-6463`), so with fake NUMA the line is that node's `min/2` (~1 MiB at stock with 8 nodes), not 8 MiB.
And it is hard to reach: an ordinary order-0 allocation fails the `min` check and reclaims *before* free pages fall to
`min/2`; only `__GFP_HIGH`/atomic users (`page_alloc.c:3225-3243`) or pcp-refill overshoot (pcp lists are not counted in
`NR_FREE_PAGES`; `pcp->high` is up to the low watermark split over CPUs, `page_alloc.c:5697-5703`) push it there. Prior: low.
`pgscan_direct_throttle` (`vmscan.c:6471`) settles it; it is in `take3v2.sh`.

Fix: replace "exactly one" with the table above; label the throttle "possible, low prior until `pgscan_direct_throttle`".

### K4. "MGLRU on (direct reclaimers never sleep in `reclaim_throttle`, `mm/vmscan.c:5959-5962`)" (8.2 Q5 table)

**Refuted (source).** `shrink_node` hands off to MGLRU at `:5959-5962`, but `shrink_zones` calls
`consider_reclaim_throttle` after the loop (`:6223`), and that throttles a direct reclaimer for one jiffy at priority 1 with
nothing reclaimed (`:6102-6130`; `skip_throttle_noprogress` may skip it, `:494`, `:567`). Small (4 ms), but the sentence is
false. Fix: "direct reclaimers under MGLRU skip the writeback/congestion throttles (`:6022`, `:6050`); the 1-jiffy NOPROGRESS
throttle (`:6129`) still applies".

### K5. B1 decision rule: "`pgscan_direct_throttle` > 0 while it has no `_begin` line = mechanism A" (and kernel.md "a thread can stall there without a `_begin` line")

**Refuted (source).** `try_to_free_pages` emits `trace_mm_vmscan_direct_reclaim_begin` right after `throttle_direct_reclaim`
returns (`vmscan.c:6525-6529`); it skips `_begin` only when a fatal signal arrived during the sleep. A throttled capture
thread therefore shows a normal `_begin`/`_end` pair *after* its sleep, and the sleep itself appears nowhere in the vmscan
events. `pgscan_direct_throttle` is a system-wide counter (`:6471`) and names no thread. The rule as written can never fire
for the case it targets. Fix: per-thread sleep stack: `echo "stacktrace if prev_pid == $T" > $S/events/sched/sched_switch/trigger`
(trigger needs `CONFIG_STACKTRACE`, selected by `CONFIG_STACK_TRACER=y`, defconfig `:1782`: **probable**) and look for
`throttle_direct_reclaim`/`try_to_free_pages` in the stack of a `prev_state=D` switch-out; or LatencyTOP (missing item 6).

### K6. M1 rule: "~0, or the same small count from kcompactd under both = strike the drain"

**Refuted (source).** In 6.12 kcompactd's `compact_zone` does only the local `lru_add_drain()` (`compaction.c:2591-2592`).
The cross-CPU `lru_add_drain_all()` at `:2931` is `compact_nodes`, reached only from the `vm.compact_memory` sysctl (`:2985`);
`:2999` is the per-node sysfs `compact` file. kernel.md's attribution of `:2931/:2999` to kcompactd is a misread. The remote
drains that can appear on this rig: fadvise's `nr_failed` branch (writer threads in `writer`; **the sync thread in `sync`**, when
a just-written file's tail folios still sit in a remote CPU's batch: **probable**), CMA allocations (`page_alloc.c:6548` ->
`swap.c:922`, forced on every CPU), long-term GUP pins (`gup.c:2394`), `move_pages` (`migrate.c:2308`).
Second defect: `workqueue_execute_start` lines are always printed by a kworker, so M1 as specified cannot say who asked
for the drain. Fix: count `events/workqueue/workqueue_queue_work` lines whose `function=lru_add_drain_per_cpu`; the task in
the line header is the caller of `lru_add_drain_all` (**probable**, `include/trace/events` not in the checkout). Better, if the
function tracer exists (K16): `echo 'lru_add_drain_all lru_cache_disable' > $S/set_ftrace_filter; echo function > $S/current_tracer`
for 60 s: one line per call, with the caller's comm-pid. Expected counts: the claim predicts ~1,500 calls per 60 s from writer
threads (each call queues work on 1-4 CPUs, so 1,500-6,000 executions; the draft's "~1,500 executions" mixes the two).

### K7. Watermark, kswapd and throttle figures assume one node (8.1 rows "kswapd re-woken", "`min_free_kbytes`"; B1/B5 "`taskset -pc 3 $(pgrep kswapd0)`")

- Kernel facts (**confirmed**): `CONFIG_NUMA=y`, `CONFIG_NUMA_EMU=y` (defconfig `:54`, `:96`); fake-NUMA code in
  `mm/numa_emulation.c:380-502`; one kswapd and one kcompactd per memory node (`vmscan.c:7361, 7396`; `compaction.c:3241`);
  kswapd bound to its node's CPUs if any, else unbound (`kswapd()` `set_cpus_allowed_ptr`).
- Board facts (KB): the Pi 5/CM5 device tree bootargs carry `numa_policy=interleave` (`working/dng-chain/R6.md:84`,
  `V/H13.md:15`, **confirmed** there from the rpi-6.12.y dtsi); the bootloader adds `numa=fake=<n>` by default since 2024-12-07
  (`working/research-30fps/q3-bandwidth.md:99-102`). The node count on Patrik's board was never read: **probable 8**.
- Consequences if 8 nodes x 512 MB: per-zone min/low/high ~2/2.5/3 MiB (the draft's 16/20/24 MiB are sums);
  **up to 8 kswapd threads** (nice 0) competing for 4 CPUs, not "a full-time kswapd"; `kswapd_low_wmark_hit_quickly`
  948-1805 is a sum over nodes (~0.7-1.3 re-wakes/s per kswapd, not 5-10); `pgrep kswapd0` pins one of eight;
  the throttle line is per node (K3); `watermark_boost` per zone is `max(pageblock, 1.5 x high)` = **32 MiB per
  fragmentation event** (`page_alloc.c:1918-1950`; pageblock = order 11 x 16 KiB), i.e. ~10x a node's whole high mark, which
  makes boost-driven kswapd runs a first-order term on this layout (**probable**).
- Fix: add to M0 `ls -d /sys/devices/system/node/node*; cat /sys/devices/system/node/node*/cpulist; pgrep -l '^kswapd';
  tr ' ' '\n' < /proc/cmdline | grep -E 'numa|max_order|iommu_dma'; grep -E 'numa_(hit|miss|interleave)' /proc/vmstat`;
  express watermarks per node; pin with `for p in $(pgrep '^kswapd'); do sudo taskset -pc 3 $p; done`.

### K8. B1 "Trace on every take: `echo 65536 > $S/buffer_size_kb`"

`buffer_size_kb` is per CPU (ftrace documentation; `kernel/trace` not in the checkout: **probable**): 64 MiB x 4 CPUs =
**256 MiB of unmovable kernel memory** allocated in the middle of an experiment whose stock kswapd window is 8 MiB, on every
take of both arms. It moves the `sync` arm's free pool 256 MiB closer to the watermarks (K1's start-state effect), seeds
unmovable pages into movable pageblocks (fragmentation, boost), and, if all CPUs sit on node 0 (`numa_emu_update_cpu_to_node`,
`numa_emulation.c:502`: **probable**), takes half of one 512 MB node. Fix: 4-8 MiB per CPU, set once right after each reboot
(before block 1's first take) and left alone; check `grep overrun $S/per_cpu/cpu*/stats` after each take; for long windows
stream `$S/trace_pipe` through `awk` that aggregates in memory instead of keeping the buffer.

### K9. M5 "a second with a lost frame and >= 40 ms of wait"; M5/M6 watch only `CameraManager`

- Timing: Core prints `drop[capture-gap]` only for the first gap, every 30th gap or a multi-frame gap
  (`CameraController.cpp:9916-9923` @ `adac040`), and B0's script polls `recording_dropped_frames` every 10 s. Which second
  lost a frame is therefore not known, and M5 cannot be aligned. **Infeasible as specified.** Fix: poll
  `recording_dropped_frames` at 1 Hz in the same loop as `schedstat`, or (better) take the loss times from the CFE sequence
  holes in the same trace buffer as the other events (K10), which timestamps every lost frame in kernel time.
- Scope: the frame dies when **any** enabled CFE node lacks a queued buffer at job time (`cfe.c:613-629`, **confirmed**), and
  `fe_config` needs a fresh buffer every frame from the IPA path; the raw buffer goes back to libcamera only after Core's copy
  worker has copied it (core-code.md 1.8). A 40 ms hole in the IPA thread or the copy worker loses the frame while
  `CameraManager` looks normal. Fix: log `schedstat` (and `majflt`, field 12 of `/proc/<pid>/task/<tid>/stat`) for **every**
  Core thread at 1 Hz (`for t in /proc/$P/task/*; do ...`), not one tid; same for the UI render thread.

### K10. M3 "holes in `vb2_buf_done` sequence numbers ... a node with zero queued buffers"

- `vb2:vb2_buf_done` carries `owner`, `queued`, `owned_by_drv`, `index`, `type`, `bytesused`, `timestamp`: no `sequence`, no
  `minor` (**probable**, `include/trace/events/vb2.h` not in the checkout). Sequence and minor are in `v4l2:vb2_v4l2_buf_done`
  and `v4l2:v4l2_dqbuf`. Check on the Pi: `cat $S/events/vb2/vb2_buf_done/format $S/events/v4l2/vb2_v4l2_buf_done/format`.
- What the driver does (**confirmed**): `vb.sequence = node->fs_count - 1` (`cfe.c:654`), `fs_count` increments at every
  start-of-frame whether or not a job ran (`:690`), and no job is scheduled unless every enabled node has a queued buffer
  (`:613-629`). So a starved node produces a hole on **all** nodes; "holes on all nodes" does not by itself mean sensor/link.
  The discriminator is the starved node's `owned_by_drv` falling to <= 1 (only the frame in flight) just before the hole.
- Also: Core's gap counter uses the sensor timestamp delta. A frame the CFE delivered but libcamera discarded (Bayer-queue or
  request starvation) gives a Core gap with **no** CFE sequence hole. M3 separates "lost before the CFE" from "lost after it":
  say so in the decision rule.

### K11. B0 step 1 `zgrep ... /proc/config.gz`

`CONFIG_IKCONFIG=m` (defconfig `:19`): `/proc/config.gz` exists only after `sudo modprobe configs`. Fix: `sudo modprobe configs`
first, or read `/boot/config-$(uname -r)` (**probable** that Pi OS ships it). Add `UPROBE_EVENTS`, `BPF_EVENTS`, `STACKTRACE`,
`FUNCTION_GRAPH_TRACER`, `LATENCYTOP`, `SCHEDSTATS`, `NUMA_EMU` to the grep.

### K12. M6/B2 `perf` commands

- `perf sched timehist -p <CameraManager tid>`: `-p` filters by process; use `-t <tid>` (or `-p <Core pid>`) (**probable**,
  perf options from memory; check `perf sched timehist -h`). Same check for `--cpu 0`.
- `perf sched record -a` writes `./perf.data` into the current directory (SD card or `/media/RAW`) during the take: page cache
  and I/O inside the measured regime. Use `-o /dev/shm/sched.data` and a 20 s window around a losing minute.
- `sudo apt install linux-perf`: whether Pi OS's package matches `6.12.75+rpt` is **unconfirmed**
  (`apt-cache policy linux-perf` before the evening). The tracefs equivalents (K5 trigger, `sched_stat_*` events,
  LatencyTOP) need no package.

### K13. B3 reset `sudo sysctl ... vm.dirty_bytes=0 vm.dirty_background_bytes=0 ...`

**Refuted (source).** `vm.dirty_bytes` has a minimum of 2 pages (`dirty_bytes_min`, `mm/page-writeback.c:2295, 2330`) and
`vm.dirty_background_bytes` a minimum of 1 (`:2308-2313`, `SYSCTL_LONG_ONE`): both writes return EINVAL. The end state is still
right only because writing `dirty_ratio` (when it changes) zeroes `vm_dirty_bytes` (`:538-548`) and writing
`dirty_background_ratio` zeroes `dirty_background_bytes` (`:509-517`). In a script with `set -e` it aborts before the ratio
writes. Fix: `sudo sysctl vm.dirty_ratio=20 vm.dirty_background_ratio=10 vm.min_free_kbytes=16384`, or better, restore the
values B0 read after the reboot.

### K14. Numbers

- Frame size: the 4K Clear HDR 16-bit uncompressed DNG is **16,590,340 bytes** (`hardware-log.md` 2026-10-26 T25 entry;
  `queue_bytes_peak=33177600` = 2 x 16,588,800 in the raw journal), not 16.9 MB: 1,013 pages of 16 KiB (kernel.md's 1,031 is
  wrong), 415 MB/s at 25 fps (right). A 3-min take of ~4,350-4,470 frames writes 72-74 GB; the kswapd share is 67-76 %, the
  unexplained remainder 18-25 GB. Small, but the 8.1 table states it as confirmed.
- "`low -> min` 4 MiB = 10 ms of stream": true only while kswapd is not reclaiming; with kswapd at 275-314 MB/s the net drain
  is ~100-140 MB/s and the band lasts ~30-40 ms. Both numbers belong in the text.
- `mm/fadvise.c:132-137` for "the partial last page is included": the deciding test is `:131` (`LLONG_MAX` ends on a page
  boundary, so `end_index` is not decremented). Citation nit.

### K15. M2 reading "~0 [`allocstall_*`] under `writer` = ... the stall must be C, E or a UI effect"

Non-sequitur. `allocstall` ~0 still leaves refault/swap-in stalls, direct compaction (`compact_stall`: **not** in `take3.sh`'s
list, so the transcript cannot show it), CMA migration, and the throughput deficit (missing item 1). Also `take3.sh` omits
`allocstall_dma`/`allocstall_dma32` (`ALLOCSTALL` is counted per `reclaim_idx`, `vmscan.c:6274`; GFP_DMA32 driver allocations
land there). Fix: rewrite the reading; add those counters to `take3v3.sh`.

### K16. "Not available on this kernel: ... probably `perf probe`/kprobes ... Tracepoints work" (8.2)

Right for kprobes and uprobes (`# CONFIG_UPROBE_EVENTS is not set`, defconfig `:1786`; no `KPROBES`), which also leaves
`BPF_EVENTS` off, so **bpftrace cannot attach even to tracepoints** (**probable**: the `BPF_EVENTS` dependency is in
`kernel/trace/Kconfig`, not checked out). Missed: `CONFIG_STACK_TRACER=y` and `CONFIG_FUNCTION_PROFILER=y` (`:1781-1782`)
select/depend on `CONFIG_FUNCTION_TRACER`, so the function tracer (and very probably `function_graph`) is built: direct call
counts with the caller for `lru_add_drain_all` (K6) and `function_graph` durations of `try_to_free_pages` per thread
(`set_ftrace_pid`), which include the throttle sleep that the vmscan events omit (**probable**; `grep -w try_to_free_pages
$S/available_filter_functions` confirms in one line). `CONFIG_LATENCYTOP=y` (`:1780`) is built too (missing item 6).
"Tracepoints work" is unlabelled: **probable** (`CONFIG_SCHED_TRACER=y`, `:1783`).

---

## 2. Missing from the draft

1. **The throughput-deficit mechanism the KB already measured.** `hardware-log.md` 2026-10-26 (`:153-202`): libcamera's RPi
   pipeline runs one frame at a time (IPA + back end), the back-end start interval while recording at 30 fps was 36.2 ms (33.3 ms idle), IPC of the
   CameraManager thread fell 1.87 -> 1.30 under recording load, the 8 CFE buffers drain, and the CFE skips **single frames**
   whenever it falls one frame behind ("every gap exactly one frame"); cores were 98-99 % busy on three CPUs while recording
   at 30 fps. At 25 fps the slack is a few ms per frame. A `writer`-mode tax of a few ms per frame on the serial chain (up to 8
   nice-0 kswapd threads, direct reclaim in the writers, allocation slow paths) drains the queue with **no 40 ms hole
   anywhere**. M4-M6 are built to find a hole and would report "nothing found". Discriminating test, all tools already in the
   KB: one `writer` and one `sync` take with `LIBCAMERA_LOG_LEVELS=RPI:0,RPiStream:0` and `working/tools/libcam_stages.py`
   (median and p90 back-end start interval: > 40 ms under `writer`, < 40 ms under `sync` = deficit); `hwcount.py` IPC of
   the thread per arm; kswapd CPU per take (`awk '{print $14+$15}' /proc/<each kswapd pid>/stat`, before/after, in USER_HZ ticks of 10 ms, not jiffies); per-CPU idle at 1 Hz from `/proc/stat`. **Unconfirmed**; prior: high, because it is the only mechanism with a
   measured precedent on this rig and it predicts the single-frame `dt_us ~80,000` signature seen on 10-30 and 11-01.
2. **Refault and swap-in.** Free per take, no package: add `pgmajfault workingset_refault_file workingset_refault_anon
   workingset_activate_file pswpin pswpout` to the per-minute keys, and per-thread `majflt` for all Core and UI threads at 1 Hz.
   Read `swapon --show`, `cat /proc/sys/vm/swappiness /sys/kernel/mm/lru_gen/enabled` once (89 MB of swap was in use on
   2026-10-26; whether it is an SD-card swapfile or zram decides whether a swap-in costs microseconds or tens of ms).
   Decisive one-take test: one `writer` take after `sudo swapoff -a` (restore with `swapon -a`); clean = anon reclaim
   (e.g. a cold warm-pool buffer) is the coupling. Note MGLRU puts new page-cache folios in the oldest or second-oldest
   generation (`include/linux/mm_inline.h:252-262`; kernel.md's "youngest generation" is wrong), which lowers but does not
   remove the risk to other pages. Fits the A0 puzzle as a hypothesis: `64bbbaa`'s warm raw pool keeps long-lived anon
   buffers that `a40112a` did not (draft 8.2 Q5 row 1). **Unconfirmed.**
3. **Direct compaction and CMA.** Add `compact_stall compact_fail compact_success cma_alloc_success cma_alloc_fail`
   (`vm_event_item.h:77, 85-86`) to the keys; in one diagnostic take enable `events/compaction/mm_compaction_begin/_end`
   and `events/cma/*` (**probable** names) to see which comm compacts or allocates CMA and for how long. A CMA allocation in
   the `writer` regime migrates page-cache folios out of the 64 MB CMA area and waits on their writeback, and forces a drain on
   every CPU: the night's "drain on every core" could be real but CMA-driven (K6's attribution fix catches it).
4. **Start-state control** in B1 and B3 (K1): record MemFree, and in B3 set it. In B1 the `rm -rf` before every take frees
   ~2.6 GB after a `writer` take but almost nothing after a `sync` take, so the `sync` arm's start state alternates with the
   ABBA order. Record it per take and report the `sync` arm's `pgsteal_kswapd` against it.
5. **A0 was never measured in kernel terms.** No `pgsteal_kswapd`, low-watermark hits or MemFree were recorded for A0
   (`hardware-log.md:736-756`); "A0 ran the `writer` regime and was clean" is **probable** (same call, `a40112a:CdngEncoder.cpp:1780`),
   not measured. T1 must print the full key list to turn A0 into a data point.
6. **LatencyTOP**, built in (`CONFIG_LATENCYTOP=y`, defconfig `:1780`; `kernel/latencytop.c`): `sudo sysctl kernel.latencytop=1`
   forces schedstats on (`latencytop.c:68-76`) and records, per task, every uninterruptible sleep and every interruptible sleep
   up to 5 ms (`:183`) with a 12-frame kernel backtrace (`include/linux/latencytop.h:19`), up to 32 distinct reasons per task
   (`:18`). `cat /proc/<pid>/task/<tid>/latency` (per-thread file: **probable**, `fs/proc` not in the checkout) after a losing
   minute names the thread, the max sleep in microseconds and the kernel path (`throttle_direct_reclaim`, `folio_wait_bit`
   for a major fault, `migration_entry_wait`, `mutex_lock` ...) without perf. Cost: a stack walk on every wakeup system-wide
   (moderate): diagnostic takes only, not B1's counted takes. The same schedstats switch enables the
   `sched:sched_stat_blocked/_sleep/_wait` events with per-episode durations for M5.
7. **`vm.watermark_boost_factor`.** With 32 MiB pageblocks and (probably) 512 MB nodes, boost (K7) can dominate kswapd's
   targets. Read `boost` per zone in `/proc/zoneinfo` during a `writer` take; if it is non-zero most of the time, one take with
   `vm.watermark_boost_factor=0` is a cleaner kernel knob test than `min_free_kbytes` (**unconfirmed**).
8. **A natural control already exists**: cinepi-raw writes with `POSIX_FADV_SEQUENTIAL` only, no DONTNEED, no fsync
   (`cinepi/dng_encoder.cpp:2356`), i.e. the full page-cache/kswapd regime of `off`. If CineMate has ever recorded the same
   data rate clean on this kernel with its own UI, the regime alone is not sufficient and the Apertar-specific coupling
   (items 1-3) is the question. A one-line KB lookup, not a test.

## 3. The proposed measurements: feasibility and discrimination

| # | Feasible on stock Pi OS 6.12.75 2712 kernel? | Discriminates? | Change |
| --- | --- | --- | --- |
| M0 | yes after `modprobe configs` (K11) | settles page size, config; misses NUMA, MGLRU runtime, swap | add the K7/missing-2 reads |
| M1 | yes (tracefs) | **no**: cannot name the caller; kcompactd premise wrong (K6) | `workqueue_queue_work`, or the function tracer on `lru_add_drain_all`/`lru_cache_disable` |
| M2 | yes (transcript) | partly: gives the K2 bound; cannot show compaction or `pgsteal_direct` | do the K2 arithmetic; add K15 counters for the next takes |
| M3 | yes (tracefs) | yes, if the right events are used (K10) | `v4l2:*` for sequence/minor, `vb2:*` for `owned_by_drv`; run it **in the same buffer** as M4 so every loss is timestamped |
| M4 | yes (tracefs) | yes for "who reclaims"; not for the throttle (K5) | 4-8 MiB buffer (K8); stream through `awk` |
| M5 | yes | **no** as specified: no per-second loss times; one thread only (K9) | all threads, 1 Hz loss poll, or M3 timestamps |
| M6 | **unconfirmed** (`linux-perf` for 6.12.75+rpt) | yes for the sleep stack | `-t`, `-o /dev/shm`; tracefs trigger or LatencyTOP as package-free alternatives |
| M7 | yes after a reboot | system-wide only | fine; note PSI adds per-context-switch accounting for the whole campaign |
| new | yes, no package | refault/swap (missing 2), deficit (missing 1), who frees (K2) | per-thread `majflt`, `libcam_stages.py` per arm, `mm_filemap_delete_from_page_cache` per comm |

## 4. What stands after this critique

- `writer`-mode fadvise starts writeback of the whole file and cannot evict what is still under writeback: **confirmed**.
- The drain branch is not taken for folios still under writeback: **confirmed**; how often it is taken in practice:
  **unconfirmed** (K2, K6).
- The drain costs microseconds per CPU, not a frame period: **probable** (estimate from the code, not a measurement).
- The cache fills and kswapd reclaims 50-57 GB per 3-minute `writer` take at 16 KiB pages: **measured** (page size **probable**).
- The dirty pair is inert for Core: **probable** (source plus 2026-10-26's 5-vs-5).
- `min_free_kbytes` is the active ingredient of #80: **refuted as an inference from #80**; untested (K1).
- Which thread stalls: still open, and the answer may be "none stalls; the serial chain runs a few ms too slow" (missing 1).
