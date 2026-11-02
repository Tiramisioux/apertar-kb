# The kernel mechanism, read from Linux 6.12 (rpi-6.12.y): what `APERTAR_DNG_DONTNEED=writer` actually does, and what can reach the capture thread

Inspection of the 2026-11-01 claim, kernel half. Written 2026-11-02 from source, no Pi. Status words as in the KB:
**confirmed** (read in the source or measured), **probable** (inferred, reason given), **unconfirmed** (the measurement
is named), **refuted** (the source says otherwise; the closing measurement is named).

Sources: `/home/user/tiramisioux/kernel-rpi` = `raspberrypi/linux` `rpi-6.12.y` @ `5bd564a`, Makefile says 6.12.114
(the Pi runs 6.12.75+rpt-rpi-2712; every function quoted below has been stable since 6.6 or earlier, none of the quoted
lines changed between .75 and .114 to my knowledge: **probable**). Only `mm/`, `include/linux/`, `arch/arm64/configs/`
and `Documentation/admin-guide/sysctl/` are checked out: statements about `fs/exfat`, `fs/sync.c`, `kernel/workqueue.c`
and `drivers/media/platform/raspberrypi/rp1-cfe` are from memory and are labelled probable. Core: `Apertar-Core`
`drop-frames` @ `adac040`, and `a40112a` (the A0 build). Line numbers are of the files as checked out.

Two facts from `arch/arm64/configs/bcm2712_defconfig` change the arithmetic of the whole night report and must be
checked on the Pi first (`getconf PAGESIZE`; `zgrep -E "CONFIG_(ARM64_16K_PAGES|LRU_GEN_ENABLED|PSI_DEFAULT_DISABLED|HZ|KPROBES|KPROBE_EVENTS|FUNCTION_TRACER|DYNAMIC_DEBUG)=" /proc/config.gz`):

| Config (bcm2712_defconfig) | Line | Consequence |
| --- | --- | --- |
| `CONFIG_ARM64_16K_PAGES=y` | :50 | **a page is 16 KiB** on the `-2712` kernel. Every `/proc/vmstat` page count of the night is 4x more bytes than the report assumed: `pgsteal_kswapd` 3.0-3.45 M pages = **49-57 GB per 3-min take**, not 12-14 GB (section 3 below). A 16.9 MB frame is 1,031 pages, 25 fps = 25,800 pages/s. (**probable** until `getconf PAGESIZE` says 16384; the `+rpt-rpi-2712` kernel flavour is the 16K one, `kernel8` is 4K) |
| `CONFIG_LRU_GEN=y`, `CONFIG_LRU_GEN_ENABLED=y` | :94-95 | MGLRU is the reclaim path. `shrink_node` hands global reclaim to `lru_gen_shrink_node` and returns before the classic throttling block (`mm/vmscan.c:5959-5962`), so a **direct reclaimer is never put to sleep by `reclaim_throttle`** on this kernel; the only sleep at reclaim entry is `throttle_direct_reclaim` (section 3) |
| `CONFIG_PSI=y`, `CONFIG_PSI_DEFAULT_DISABLED=y` | :17-18 | `/proc/pressure/memory` is **empty/absent on the current boot**; needs `psi=1` in `cmdline.txt` and a reboot |
| `CONFIG_TASK_DELAY_ACCT=y`, `CONFIG_TASKSTATS=y` | :14, :13 | per-thread reclaim-delay accounting exists and can be switched on at run time (`sysctl kernel.task_delayacct=1`); `/proc/<pid>/task/<tid>/schedstat` (run-queue wait) works without it |
| `CONFIG_PREEMPT=y` | :10 | full kernel preemption: a kworker wake-up on CPU0 can preempt the capture thread mid-syscall, but only for as long as the work runs (microseconds, section 2) |
| no `CONFIG_DYNAMIC_DEBUG`, no `CONFIG_KPROBES`, no `CONFIG_FUNCTION_TRACER` in the defconfig | (absent) | `rp1_cfe` `+p` dynamic debug (the 2026-10-26 entry already noted this) and `perf probe`/`bpftrace kprobe:` **probably do not work** on this kernel. Tracepoints (`vmscan:*`, `workqueue:*`, `sched:*`, `vb2:*`) do (`CONFIG_SCHED_TRACER=y` :1783 implies tracing). **unconfirmed** until the `/proc/config.gz` grep above |
| `CONFIG_HZ` not set in the defconfig | - | arm64 default is 250: a jiffy is 4 ms, `HZ/10` = 100 ms, `HZ/50` = 20 ms (**probable**) |

---

## 1. What `posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED)` does on a 16.9 MB file written milliseconds ago

The whole path, in the writer thread that just finished `writeAll`/`writeRawPayload` (Core `adac040`
`src/cdng/CdngEncoder.cpp:1886-1887`: `if (dngPageCacheDrop() == DngPageCacheDrop::Writer) ::posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED);`;
the A0 build `a40112a` has the same call unconditionally at `CdngEncoder.cpp:1780`).

### 1.1 Step 1: it starts writeback of the whole file (confirmed)

`mm/fadvise.c:113-115`
```c
	case POSIX_FADV_DONTNEED:
		__filemap_fdatawrite_range(mapping, offset, endbyte,
					   WB_SYNC_NONE);
```
With `len == 0`, `endbyte = LLONG_MAX` (`:72-74`), so the range is the whole file. `__filemap_fdatawrite_range`
(`mm/filemap.c:421-432`) builds a `writeback_control` with `nr_to_write = LONG_MAX` and calls
`filemap_fdatawrite_wbc` (`:388-402`), which returns at once if the mapping has no dirty tag
(`:393-395 if (!mapping_can_writeback(mapping) || !mapping_tagged(mapping, PAGECACHE_TAG_DIRTY)) return 0;`) and
otherwise runs `do_writepages` (`:398`). For exFAT that is `mpage_writepages` (fs/exfat/inode.c, not in the checkout:
**probable**). The writeback iterator locks each dirty folio, clears its dirty bit, sets `PG_writeback`, builds bios
and submits them (`mm/page-writeback.c` `writeback_get_folio`: `folio_lock(folio)` then `folio_prepare_writeback`; with
`WB_SYNC_NONE` a folio already under writeback is skipped, not waited for). The call returns when the I/O is **queued**,
not done: 16.9 MB at the drive's ~800 MB/s is in flight for the next ~20 ms.

So in `writer` mode the data of every frame leaves the page cache through this call. Consequences:

- Core's per-frame `sync_file_range(fd, 0, 0, SYNC_FILE_RANGE_WRITE)` (`CameraController.cpp:4668-4675`, called right after
  `writeDngFile` at `:5204-5205`) does the same `__filemap_fdatawrite_range(..., WB_SYNC_NONE)` on a mapping whose dirty tag
  is already clear, and returns at `filemap.c:393-395` without work. **In `writer` mode the writeback hint is redundant**
  (fs/sync.c not in the checkout: **probable**; the mm side is confirmed).
- 2026-10-30 A1 -> A2 (`APERTAR_DNG_WRITEBACK=0`, 10 % lost at capture): the A0 build had the unconditional DONTNEED
  (`a40112a:src/cdng/CdngEncoder.cpp:1780`), so A2 still started per-file writeback through fadvise. The A1/A2 difference
  was **not** "no writeback". A2 is one run; with A0 and A1 before it on the same boot it fits the within-boot drift of
  2026-11-01 #69 -> #72 (1, 34, 153, 71). Status of the 2026-10-30 reading "the per-frame writeback hint is needed":
  **refuted by source for the stated reason**; the loss itself is unexplained (one run).

### 1.2 Step 2: it tries to evict, and skips everything that is dirty, under writeback, locked or still referenced (confirmed)

`mm/fadvise.c:144-170`
```c
		if (end_index >= start_index) {
			unsigned long nr_failed = 0;
			/* ... It's common to FADV_DONTNEED right after the read or write that
			 * instantiates the pages, in which case there will be some sitting on
			 * the local LRU cache. Try to avoid the expensive remote drain ... */
			lru_add_drain();

			mapping_try_invalidate(mapping, start_index, end_index,
					&nr_failed);
			/* The failures may be due to the folio being in the LRU cache of a
			 * remote CPU. Drain all caches and try again. */
			if (nr_failed) {
				lru_add_drain_all();
				invalidate_mapping_pages(mapping, start_index,
						end_index);
			}
		}
```
`lru_add_drain()` (`mm/swap.c:729-735`) drains only the **calling CPU's** batches: cheap, local, every call.

`mapping_try_invalidate` (`mm/truncate.c:497-545`) walks the file with `find_lock_entries` (`mm/filemap.c:2101-2155`),
and that walk is where the claim's mechanism breaks:
```c
			if (!folio_trylock(folio))
				goto put;
			if (folio->mapping != mapping ||
			    folio_test_writeback(folio))
				goto unlock;
```
(`mm/filemap.c:2121-2125`). **A folio under writeback, or one that cannot be locked, is never returned to the caller**,
so it is neither evicted nor counted in `nr_failed`. Only the folios that are returned go through `mapping_evict_folio`
(`mm/truncate.c:288-303`):
```c
	if (folio_test_dirty(folio) || folio_test_writeback(folio))
		return 0;
	/* The refcount will be elevated if any page in the folio is mapped */
	if (folio_ref_count(folio) >
			folio_nr_pages(folio) + folio_has_private(folio) + 1)
		return 0;
	if (!filemap_release_folio(folio, 0))
		return 0;
	return remove_mapping(mapping, folio);
```
and only a returned folio that fails here is deactivated and counted (`mm/truncate.c:521-531`):
```c
			ret = mapping_evict_folio(mapping, folio);
			folio_unlock(folio);
			if (!ret) {
				deactivate_file_folio(folio);
				/* Likely in the lru cache of a remote CPU */
				if (nr_failed)
					(*nr_failed)++;
			}
```

Put the two steps together for a fresh 16.9 MB DNG: step 1 has just set `PG_writeback` on every page of the file (the
only dirty pages it could skip are ones already under writeback from an earlier pass, and there is no earlier pass on a
file created a moment ago). Step 2 then finds the file's folios **under writeback and skips them in `find_lock_entries`**.
Result per call:

| Outcome | Status | Why |
| --- | --- | --- |
| frees nothing, or nearly nothing | **confirmed** | every page still under writeback is skipped (`filemap.c:2124`); a page whose I/O already completed in the ~1-3 ms between submission and the walk is clean, unlocked, refcount 3 (cache + our ref + buffer heads) and **is freed** (`truncate.c:293-303`): the first megabytes of the file may go; the bulk stays (**probable** for the fraction) |
| deactivates nothing | **confirmed** | `deactivate_file_folio` runs only for returned-and-refused folios (`truncate.c:527-528`), and the under-writeback folios are not returned |
| `nr_failed == 0`, so **no `lru_add_drain_all()`** and no second walk | **refuted claim** (source) | the drain-all branch (`fadvise.c:166-170`) needs a returned folio that `mapping_evict_folio` refuses: a dirty-but-not-under-writeback folio (none after step 1), a mapped folio (DNGs are not mmapped), or an elevated refcount (a folio still in a remote CPU's `lru_add` batch: at most the last 30 folios of the writer's own CPU, and the writer just drained its own CPU at `:156`). The night report's sentence "drains the per-CPU LRU lists on every core per frame" and night report §8.1 row 2 "confirmed (source)" describe a branch this write pattern does not take. Closing measurement: count executions of `lru_add_drain_per_cpu` during a `writer` take (section 6, M1): the claim predicts ~25/s, this reading predicts ~0 from Core |
| the pages stay where `folio_add_lru` put them when the write created them (`mm/filemap.c:988` -> `mm/swap.c:503-515`: the youngest MGLRU generation / head of the inactive file list), clean once the I/O completes ~20 ms later, with no reclaim hint | **confirmed** | nothing in the call touches them again |

So the per-frame cost of the `writer` call is: one `do_writepages` over 1,031 folios (lock, clear dirty, set writeback,
~5 bios of 4 MiB; a few ms of the writer's own CPU), one local `lru_add_drain`, one xarray walk of 1,031 entries with
`folio_get`/`trylock`/`put` (well under a millisecond). **All of it on the writer's CPU.** The call is not free, but it is
not a cross-CPU event, and `sync_file_range` would have cost the same `do_writepages`.

What the call does **not** do is the thing that matters: it leaves ~1,031 clean pages per frame in the cache. Nothing
frees them until the free-page watermarks are hit (section 3). At 25,800 pages/s the cache is full about 6 s into the first
take of a boot, and from then on every page the writers allocate has to be reclaimed from an older frame by kswapd or by
the allocating thread itself. That is the mechanism the measurements show (`pgsteal_kswapd` 3-3.45 M, low-watermark hits
948-1805), and it is the right reason to prefer `sync` mode.

### 1.3 `sync` mode (confirmed)

`CameraController.cpp:4689-4718` (`syncLoop`): once a second, for each file written since the last tick, `fsync(fd)` then
`posix_fadvise(fd, 0, 0, POSIX_FADV_DONTNEED)`. After `fsync` the file has no dirty tag and nothing under writeback, so
step 1 returns at `filemap.c:393-395`, and step 2 returns every folio from `find_lock_entries`, `mapping_evict_folio`
frees each one (`remove_mapping`), `nr_failed` stays 0, no drain-all. The sync thread frees ~25 x 1,031 pages per tick on its
own CPU, the cache never fills, kswapd stays asleep: #74/#75 `pgsteal_kswapd` 47-58 k, #80 0 (what little there is comes
from watermark boosting after fragmentation events, `mm/page_alloc.c:1920-1952`, which wakes kswapd with free memory
plentiful; it fits "compaction busy in clean takes too"). **The fix works for the right reason; the stated per-frame drain is
not that reason.**

Note (`off`/lossy): with no sync thread (`APERTAR_MEDIA_SYNC_MS=0`, or lossy DNG) nothing drops the pages and the cache
fills exactly as in `writer` mode minus the redundant fdatawrite (Core warns, `CameraController.cpp:4324-4331`).

---

## 2. `lru_add_drain_all()`: what it costs whom (confirmed from source; the quantities are bounds)

`mm/swap.c:792-886`. Serialised by a mutex; a caller that finds a newer generation already scheduled returns without
draining (`:830-840`, "(C) Exit the draining operation if a newer generation ... was already scheduled"), so concurrent
callers coalesce. For each online CPU whose batches are non-empty (`cpu_needs_drain`, `:770-783`: `lru_add`,
`lru_move_tail`, `lru_deactivate_file`, `lru_deactivate`, `lru_lazyfree`, `lru_activate`, mlock, buffer-head LRU) it
queues `lru_add_drain_per_cpu` on `mm_percpu_wq` (`:865-874`), then **the caller sleeps in `flush_work` on every CPU it
queued** (`:876-877`).

What runs on each CPU: `lru_add_and_bh_lrus_drain` (`:744-750`) -> `lru_add_drain_cpu` (`:642-660`), which moves up to
`PAGEVEC_SIZE` = 31 folios per batch (`include/linux/pagevec.h:15`) to the LRU under the per-node `lru_lock` with IRQs
off (`folio_batch_move_lru`, `:189-211`, `folio_lruvec_relock_irqsave`), plus `invalidate_bh_lrus_cpu` (16 buffer heads)
and `mlock_drain_local`. Six batches x 31 folios x roughly a microsecond each: **10-200 us per CPU per drain**, IRQs off
for 31 folios at a time. `mm_percpu_wq` is `alloc_workqueue("mm_percpu_wq", WQ_MEM_RECLAIM, 0)` (`mm/vmstat.c:2179`):
no `WQ_HIGHPRI`, so the kworker is an ordinary nice-0 CFS task; on a CPU running a nice -5 thread (libcamera's completion
thread, `CameraController.cpp:8993` `setpriority(..., -5)`) or a `SCHED_FIFO` one (#22) it runs when the scheduler lets it,
and the **waiting is done by the caller** (the writer), not by the other CPUs.

Quantitative bound: even if every written frame caused a drain (it does not, section 1.2), 25 drains/s x <= 200 us =
<= 5 ms/s = **0.5 % of CPU0**, in slices of <= 200 us. The claim needs a 40 ms hole (one frame period at 25 fps, `dt_us`
about 80,000) in the capture thread's timeline. **A per-frame LRU drain cannot produce that**, with or without the
"4 writers" (on exFAT Core's default is 2 uncompressed writers, `CameraController.cpp:4275-4278`, "ext4 keeps 4,
exFAT/NTFS get 2"; the journal's `workers=` line says which; either way one DONTNEED per file = 25/s, not 100/s). Status:
**refuted as the cause** by arithmetic from the source; the residual uncertainty is lock contention on `lru_lock`
(held by kswapd's and direct reclaim's isolation and by every writer's batch move), which lengthens each hold by
microseconds, not milliseconds.

Who else does cross-CPU drains on this system (so a measurement does not misattribute them to Core):
`lru_add_drain_all` is also called by compaction (`mm/compaction.c:2931`, `:2999`; kcompactd was awake 47-232 times per
take, clean and bad alike), khugepaged, KSM, memory-failure, migration (`lru_cache_disable`, `mm/migrate.c:2308`,
`mm/page_alloc.c:6548` for `alloc_contig_range`/CMA). The per-CPU **page** lists are drained differently in 6.12:
`drain_all_pages` (`mm/page_alloc.c:2607-2610`, reached from the direct-reclaim retry at `:4057` and from compaction at
`mm/compaction.c:3100`) drains remote CPUs' lists **from the caller** under `pcp->lock` (`drain_pages_zone`,
`:2479-2497`), no kworker, no IPI. So under memory pressure the cross-CPU work that does happen is lock traffic from
direct reclaimers and compaction, not from fadvise.

---

## 3. kswapd, watermarks, direct reclaim: what the counters mean on this board

### 3.1 The watermarks (confirmed; numbers computed from the source formula)

`mm/page_alloc.c:6125-6180` (`__setup_per_zone_wmarks`): `pages_min = min_free_kbytes >> (PAGE_SHIFT - 10)` is split
over the lowmem zones in proportion to their managed pages; then per zone
```c
		tmp = max_t(u64, tmp >> 2,
			    mult_frac(zone_managed_pages(zone),
				      watermark_scale_factor, 10000));
		zone->watermark_boost = 0;
		zone->_watermark[WMARK_LOW]  = min_wmark_pages(zone) + tmp;
		zone->_watermark[WMARK_HIGH] = low_wmark_pages(zone) + tmp;
```
(`:6172-6178`). With `watermark_scale_factor` 10 (`:323`) the scale term is 0.1 % of ~3.9 GB = 3.9 MiB, smaller than
`min/4` in both settings, so `min/4` wins. The formula is in kilobytes, so the MiB values do not depend on the page size:

| `vm.min_free_kbytes` | min | low (kswapd wakes below) | high (kswapd sleeps above) | high - min, the whole working window | at 415 MB/s of new page cache |
| --- | --- | --- | --- | --- | --- |
| 16384 (Raspberry Pi OS default, `98-rpi.conf`) | 16 MiB | 20 MiB | 24 MiB | 8 MiB | **low -> min in 10 ms, high -> min in 19 ms** |
| 65536 (#80) | 64 MiB | 80 MiB | 96 MiB | 32 MiB | low -> min in 39 ms, high -> min in 77 ms |

(Zone totals; each zone holds its share, and an allocation for a higher zone also has to clear `lowmem_reserve`,
`:3260`. `watermark_boost` adds up to 150 % of `high` per zone after fragmentation events, `:1933-1950`, in steps of one
pageblock = 32 MiB on 16K pages (`pageblock_order` = `HUGETLB_PAGE_ORDER`, `include/linux/pageblock-flags.h:44`, max
order 11 for 16K, `arch/arm64/Kconfig:1711`): a single mixed pageblock raises the effective watermarks by more than the
whole default window. `/proc/zoneinfo` gives the real per-zone `min`/`low`/`high`/`boost`.)

What this means: with the default, the free-page cushion between "kswapd is woken" and "allocations start reclaiming
for themselves" is **4 MiB = 10 ms of Core's write stream**, and kswapd's whole target is to get 8 MiB ahead. kswapd is a
nice-0 kthread (`mm/vmscan.c:7183-7257`); if it is not scheduled within ~10 ms of its wake-up, or is throttled
(`reclaim_throttle(pgdat, VMSCAN_THROTTLE_WRITEBACK)` sleeps `HZ/10` = 100 ms when it keeps meeting pages under
writeback, `:555-557`, `:6022`; MGLRU's own path has no such sleep but kswapd can still be descheduled), free pages fall
under `min` and every allocation in the system goes to direct reclaim. Raising `min_free_kbytes` to 64 MiB quadruples
every one of these distances; that, not the dirty limits (section 4), is the active kernel-side ingredient of #80
(**probable**; B3(c) in night report §8.3 tests it alone).

### 3.2 Reading the measured counters (16 KiB pages; divide the byte figures by 4 if `getconf PAGESIZE` says 4096)

`pgsteal_kswapd` 3.02-3.45 M pages per 3-min `writer` take (`mm/vmscan.c:4643` under MGLRU, `:1991` classic):
**49.5-56.5 GB freed by kswapd**, against 4,469-4,506 frames x 16.9 MB = 75.5-76.2 GB written = 4.61-4.65 M pages. So
kswapd freed **65-74 %** of the pages the take allocated, at 16.8-19.2 k pages/s = 275-314 MB/s. The remaining
1.2-1.6 M pages per take (20-26 GB) were freed by something else: direct reclaim in the allocating threads
(`pgsteal_direct`, `pgscan_direct`, `allocstall_*`), or the fadvise call's own eviction of pages whose I/O had already
completed (section 1.2), or both. `take3.sh` recorded `pgscan_direct`, `allocstall_normal` and `allocstall_movable` for
every take (its `S()` list); the values are not in the KB. **They are the single most informative numbers already
measured** (M2 in section 6). Night report §8.1 computed this row with 4 KiB pages ("16-18 %", "~60 GB by direct
reclaim"): with 16 KiB pages the kswapd share is 65-74 % and the unexplained remainder 20-26 GB; the conclusion "direct
reclaim must have been running" stands only if `allocstall_*` says so.

`kswapd_low_wmark_hit_quickly` 948-1805 per take: after a `balance_pgdat` run kswapd tries to sleep `HZ/10`
(`mm/vmscan.c:7104-7119` `remaining = schedule_timeout(HZ/10);`) and counts this event when it is woken before that
sleep ends (`:7161-7165`):
```c
	} else {
		if (remaining)
			count_vm_event(KSWAPD_LOW_WMARK_HIT_QUICKLY);
		else
			count_vm_event(KSWAPD_HIGH_WMARK_HIT_QUICKLY);
	}
```
So **5-10 times a second kswapd reached `high`, lay down, and was re-woken within 100 ms** (at 415 MB/s the 4 MiB from
`high` to `low` takes 10 ms). Each `balance_pgdat` aims at the sum of the `high` watermarks (`kswapd_shrink_node`,
`:6776-6782 sc->nr_to_reclaim += max(high_wmark_pages(zone), SWAP_CLUSTER_MAX)`), i.e. ~24 MiB (default) per run. 5-10
runs/s x 24 MiB = 120-240 MB/s if each run reclaimed exactly its target; the measured 275-314 MB/s says runs reclaimed
more than the target (MGLRU evicts in batches) and/or kswapd was mostly awake. `sync` takes: 8-11 hits per take.
Documentation (`Documentation/admin-guide/sysctl/vm.rst`, `watermark_scale_factor`): "A high rate of threads entering
direct reclaim (allocstall) or kswapd going to sleep prematurely (kswapd_low_wmark_hit_quickly) can indicate that the
number of free pages kswapd maintains for latency reasons is too small for the allocation bursts occurring in the
system." That is the kernel's own description of the `writer` regime.

### 3.3 When a user thread enters direct reclaim, and how long it can take (confirmed; durations bounded)

Fast path: `__alloc_pages_noprof` tries with `ALLOC_WMARK_LOW` (`mm/page_alloc.c:4836`); `get_page_from_freelist`
checks `high` first and marks the zone `ZONE_BELOW_HIGH` (`:3508-3516`), then the requested mark (`:3519-3522`). Below
`low` the allocation enters `__alloc_pages_slowpath` (`:4298`): `gfp_to_alloc_flags` lowers the bar to `ALLOC_WMARK_MIN`
(`:4089`), kswapd is woken (`:4374-4375`), and a second try is made (`:4381`). **Between `low` and `min` an allocation
succeeds without reclaiming** (10 ms of write stream with the default). Below `min` (or, for `__GFP_HIGH`, below
`min/2`, `:3231-3243`) the thread calls `__alloc_pages_direct_reclaim` (`:4497`) -> `__perform_reclaim` ->
`try_to_free_pages` (`:4008-4030`), inside `psi_memstall_enter/leave` (`:4042`, `:4062`). `try_to_free_pages`
(`mm/vmscan.c:6496-6540`) first calls `throttle_direct_reclaim` and then `do_try_to_free_pages`, which counts
**`allocstall`** once per entry (`:6274 __count_zid_vm_events(ALLOCSTALL, sc->reclaim_idx, 1)`, per zone index:
`allocstall_movable` for `GFP_HIGHUSER_MOVABLE`, i.e. page-cache pages (`mm/filemap.c:2485 mapping_gfp_mask`) and user
page faults; `allocstall_normal` for `GFP_KERNEL` and for `GFP_HIGHUSER`-without-movable allocations such as GEM shmem
objects, **probable** for the GPU case) and reclaims `SWAP_CLUSTER_MAX` = 32 pages (`:6501`,
`include/linux/swap.h:225`) = 512 KiB. Time: scanning MGLRU's oldest generation for 32 clean unmapped file pages is
tens of microseconds to a few milliseconds; on this kernel there is **no `reclaim_throttle` sleep for a direct
reclaimer** (section 0, MGLRU hand-off at `:5959-5962`). The one long sleep is at the door:

`throttle_direct_reclaim` (`mm/vmscan.c:6416-6494`) / `allow_direct_reclaim` (`:6367-6404`):
```c
	wmark_ok = free_pages > pfmemalloc_reserve / 2;
	...
	if (!(gfp_mask & __GFP_FS))
		wait_event_interruptible_timeout(pgdat->pfmemalloc_wait,
			allow_direct_reclaim(pgdat), HZ);
	else
		/* Throttle until kswapd wakes the process */
		wait_event_killable(zone->zone_pgdat->pfmemalloc_wait,
			allow_direct_reclaim(pgdat));
```
When free pages (zones up to `ZONE_NORMAL`) fall below **half the sum of the `min` watermarks (8 MiB default,
32 MiB tuned)**, a user thread that needs a page **sleeps until kswapd gets free memory back above that line**
(`balance_pgdat` wakes the queue at `:6989-6991`, `prepare_kswapd_sleep` at `:6745-6746`), with **no timeout** for
`__GFP_FS` allocations (page faults, page cache). That is a mechanism that produces exactly the observed symptom shape:
a single thread loses tens of milliseconds, whole frame periods, with no CPU load of its own, only when free memory sits
at the bottom of a window that is 8 MiB deep and refills at kswapd's pace. It counts in `pgscan_direct_throttle`
(`:6471`), and under `allocstall_*` only if the thread then reclaims. Kernel threads are exempt (`:6430`), so
kswapd/kworkers never queue here; **libcamera's completion thread, the UI's render thread and the writers are not
exempt.** Whether the capture thread allocates pages at all during steady state (heap growth or trim-and-regrow in
glibc, `mmap`'d large allocations, stack) is **unconfirmed**; the per-thread counters in section 6 (M4/M5) settle it in
one take.

For completeness, the classic (non-MGLRU) sleeps that do **not** apply here: `reclaim_throttle` `VMSCAN_THROTTLE_WRITEBACK`
`HZ/10`, `CONGESTED`/`NOPROGRESS` 1 jiffy, `ISOLATED` `HZ/50` (`mm/vmscan.c:555-580`; `too_many_isolated`, `:1951-1957`).

### 3.4 What the counters would show if the capture thread (or the UI, or the CFE path) stalled in reclaim

| Counter / file | What a stall writes there | Resolution |
| --- | --- | --- |
| `/proc/vmstat` `allocstall_movable` | +1 per `try_to_free_pages` entry from a page-cache or user-fault allocation (writers **and** any user thread) | system-wide, per take or per minute (take3.sh already has it) |
| `allocstall_normal`, `allocstall_dma32`, `allocstall_dma` | +1 per entry from kernel/GEM/slab allocations (`__count_zid_vm_events` per zone index) | system-wide |
| `pgscan_direct`, `pgsteal_direct` | pages scanned/freed by direct reclaimers; `pgsteal_direct` + `pgsteal_kswapd` should add up to roughly the take's pages (4.6 M) if all freeing is reclaim | system-wide |
| `pgscan_direct_throttle` | +1 per thread put to sleep in `throttle_direct_reclaim` (`:6471`): the unbounded sleep | system-wide, **this one is the smoking gun if > 0** |
| `/proc/pressure/memory` `some`/`full` `total` (us) | time any (`some`) / every (`full`) non-idle task spent in `psi_memstall` (direct reclaim `page_alloc.c:4042`, `balance_pgdat` is kswapd's own and counts only as `some`... compaction `compaction.c:3188`) | per second; **needs `psi=1` + reboot on this kernel** |
| `/proc/<pid>/task/<tid>/schedstat` field 2 | nanoseconds the thread spent runnable but not running (run-queue wait): CPU competition from kswapd/kworkers/IRQ work on CPU0 | per thread, per second, no setup |
| taskstats `RECLAIM count / delay total` (`getdelays -d -t <tid>`) | number and total time of direct-reclaim episodes of that thread (`delayacct_freepages_start`, `mm/vmscan.c:6271`) | per thread; `sysctl kernel.task_delayacct=1` at run time, needs the `getdelays` tool (tools/accounting/getdelays.c) |
| tracepoints `vmscan:mm_vmscan_direct_reclaim_begin`/`_end` (`:6529`, `:6533`) | one pair per direct-reclaim episode with comm and pid; begin-to-end is the stall length (excluding the `throttle_direct_reclaim` sleep, which happens **before** `_begin`, `:6525`) | per episode; tracefs, no packages |
| tracepoints `vmscan:mm_vmscan_throttled` (`:591`), `mm_vmscan_kswapd_wake`/`_sleep` (`:7248`, `:7145`), `mm_vmscan_wakeup_kswapd` (`:7308`) | kswapd's duty cycle and who woke it | per event |

---

## 4. `vm.dirty_bytes` 1 GiB and `vm.dirty_background_bytes` 256 MiB: inert for this writer (confirmed from source)

`mm/page-writeback.c:377-446` (`domain_dirty_limits`): with `vm_dirty_bytes` set, `thresh = DIV_ROUND_UP(bytes,
PAGE_SIZE)` (`:410-411`), else `thresh = vm_dirty_ratio % of available_memory` (`:413`); same for `bg_thresh`
(`:415-418`). `available_memory` = `global_dirtyable_memory()` (`:347-365`) = free pages - `totalreserve_pages` +
inactive file + active file. Throttling starts only above the **freerun ceiling** `(thresh + bg_thresh) / 2`
(`:837-841`, used at `:1769 dtc->freerun = dirty <= dirty_freerun_ceiling(thresh, bg_thresh)`); below it
`balance_dirty_pages` (`:1830`) exits without pausing, and it is entered only from the dirtying task
(`balance_dirty_pages_ratelimited`, `:2144`, called from the buffered write path every `nr_dirtied_pause` pages).

| Regime | dirtyable memory | thresh | bg_thresh | freerun ceiling (throttling starts) |
| --- | --- | --- | --- | --- |
| defaults (`dirty_ratio` 20, `dirty_background_ratio` 10), `writer` steady state: free ~0.3 GB + file ~2.6 GB | ~2.9 GB | ~580 MB | ~290 MB | **~435 MB** |
| defaults, `sync` steady state: free ~2.7 GB + file ~0.5 GB | ~3.2 GB | ~640 MB | ~320 MB | ~480 MB |
| #80: `dirty_bytes` 1 GiB, `dirty_background_bytes` 256 MiB | - | 1024 MiB (**higher** than the default) | 256 MiB (slightly lower) | **640 MiB** |

Core keeps dirty pages tiny: each frame's pages go to writeback within milliseconds (`writer`: the fadvise; `sync`: the
per-frame `sync_file_range`), and A0 measured peak `Dirty` 11 MB and `Writeback` 8 MB (hardware log 2026-10-30). Eleven MB
against a 435 or 640 MB ceiling: **the writers never leave freerun under either setting**, so `balance_dirty_pages`
never pauses them, and it cannot touch the capture thread at all, which dirties nothing. The effective thresholds are
readable on the Pi as `nr_dirty_threshold` and `nr_dirty_background_threshold` in `/proc/vmstat` (in pages). The
2026-10-26 entry measured the same knobs (5 takes vs 5) and saw no difference, which agrees. The one side effect of
`dirty_bytes` worth knowing: the background flusher's `wb_over_bg_thresh` (`:2188`) uses `bg_thresh`, so kernel
writeback would start at 256 MiB instead of ~290 MB of dirty data, which Core never accumulates. **Status: the two
dirty sysctls in #80 did nothing measurable; `min_free_kbytes` is the knob that changed the regime (probable, B3(c)
confirms).** cinemate sets the same pair for `nvme` (`services/storage-automount/storage-automount.py:111-112`,
`:319-335`) plus `dirty_writeback_centisecs` 150 and `dirty_expire_centisecs` 3000, and nothing about
`min_free_kbytes`; cinepi-raw's disk thread writes buffered with only `POSIX_FADV_SEQUENTIAL`, no DONTNEED, no fsync
(`cinepi/dng_encoder.cpp:2351-2370`), so CineMate's page cache fills like `writer` mode minus the fdatawrite, and its
dirty cushion matters there because nothing forces per-file writeback.

---

## 5. Verdict on the mechanism as stated

"frees nothing **and drains the per-CPU LRU lists on every core per frame**; the cache fills and kswapd reclaims during
the take; the UI is the last straw."

| Part | Status | Basis | Cheapest direct measurement (details in section 6) |
| --- | --- | --- | --- |
| the writer-mode DONTNEED frees nothing (or nearly) | **confirmed** | `fadvise.c:114` starts writeback; `filemap.c:2121-2125` skips under-writeback folios; `truncate.c:293-294` refuses dirty/writeback ones | none needed; `pgsteal_kswapd` 3-3.45 M per take already shows the pages were left for reclaim |
| it also starts the file's writeback, making the per-frame `sync_file_range` redundant in `writer` mode and the 2026-10-30 A1/A2 reading wrong for its stated reason | **confirmed** (mm) / **probable** (fs/sync.c) | `fadvise.c:114`, `filemap.c:393-395`; `a40112a:CdngEncoder.cpp:1780` | none for the code; A2's 10 % needs a repeat before it means anything |
| "drains the per-CPU LRU lists on every core per frame" | **refuted** (source) | the branch needs `nr_failed > 0` (`fadvise.c:166`); under-writeback folios are never returned (`filemap.c:2124`) so never counted (`truncate.c:527-531`) | **M1**: count `lru_add_drain_per_cpu` work executions per CPU during a `writer` take via `workqueue:workqueue_execute_start` (tracefs). Claim predicts ~25/s from Core's writers; source predicts ~0 from Core (compaction's calls aside) |
| the drain is what costs capture frames | **refuted** (arithmetic) | <= 200 us per CPU per drain, nice-0 kworker, caller does the waiting (`swap.c:876-877`, `vmstat.c:2179`); 25/s x 200 us = 0.5 % of CPU0, in <= 200 us slices; the symptom is a 40 ms hole | same M1 plus **M6** (`perf sched timehist` on the capture thread: a 40 ms hole, and what ran) |
| the cache fills and kswapd reclaims during the take | **confirmed** (measured, now with the right byte figures) | 65-74 % of the take's pages freed by kswapd at 275-314 MB/s; kswapd re-woken 5-10 times/s within 100 ms of sleeping (`vmscan.c:7119`, `:7162-7163`); the remaining 20-26 GB per take unexplained | **M2**: the `pgscan_direct`/`allocstall_*` deltas take3.sh already printed (transcript), then per minute |
| the memory regime reaches the capture thread (the real "mechanism" question) | **unconfirmed**; the kernel offers exactly one unbounded stall for a user thread, `throttle_direct_reclaim` below `min/2` = 8 MiB (`vmscan.c:6394`, `:6486-6487`), and one bounded one, direct reclaim itself (`page_alloc.c:4497`, `vmscan.c:6531`); either needs the thread to allocate a page | `pgscan_direct_throttle` > 0 in a `writer` take; **M4** (per-thread reclaim episodes: `vmscan:mm_vmscan_direct_reclaim_begin` filtered by comm `CameraManager`) and **M5** (`schedstat` run-queue wait per second) |
| `min_free_kbytes` 64 MiB is what helped in #80, the dirty limits did nothing | **probable** | section 3.1 (window 8 -> 32 MiB, 19 -> 77 ms), section 4 (writers in freerun under both settings) | B3(b) vs B3(c) of night report §8.3; `nr_dirty_threshold` in `/proc/vmstat` shows the inert thresholds |
| the UI is the last straw | **unconfirmed**; the kernel side only says: a UI stall and a Core stall have the same cause available (an allocation below `min`), and the UI's GEM/shmem allocations are the likeliest page allocator in the system besides the writers (**probable**) | M4 with comm `Apertar-UI`; whether a UI stall can block Core's capture thread is a Core question (`publishPreviewFrame`, `CameraController.cpp:9928`: does the hand-off block?) |

### Alternative mechanisms the data fit equally well, and what tells them apart

| Mechanism | Fits because | Measurement that separates it |
| --- | --- | --- |
| **A.** The capture thread allocates a page (heap, stack, mmap) while free pages are below `min` (or `min/2`): direct reclaim (bounded, ms) or `throttle_direct_reclaim` (unbounded until kswapd refills) | one thread, tens of ms, no CPU use, only in the `writer` regime, cured by `sync` (cache never fills) and by `min_free_kbytes` 64 MiB (window 4x) | M4: `mm_vmscan_direct_reclaim_begin` with comm `CameraManager`; `pgscan_direct_throttle` delta; `getdelays` RECLAIM delay of that tid |
| **B.** The UI's render thread stalls the same way (GEM shmem allocations, `allocstall_normal`), and Core's capture thread waits on the UI in the preview hand-off | UI stopped or frozen = clean under `writer`; preview held (`APERTAR_UI_PREVIEW_RECORDING_FPS=0`) = clean; UI running = clean under `sync` | M4 with comm `Apertar-UI` **and** M6: the capture thread's sleep stack at the gap (`perf record -e sched:sched_switch -g` on its tid: a `write`/`sendmsg`/`futex` into the UI vs `try_to_free_pages`/`throttle_direct_reclaim`) |
| **C.** Run-queue competition on CPU0: kswapd (nice 0, awake most of the take in `writer` mode) and reclaim-related kworkers share CPU0 with the nice -5 capture thread and all camera/GPU/display IRQs | fits the same on/off pattern; `SCHED_FIFO 40` for the capture thread (#22) did **not** help, which argues against pure CPU competition | M5: `schedstat` wait time per second of the capture thread; M6 `perf sched timehist` (what ran on CPU0 during the hole); one-take fix test: `taskset -pc 3 $(pgrep kswapd0)` |
| **D.** IRQ-off / lock-hold lengthening on CPU0 (`lru_lock` irqsave in batch moves and isolation, `zone->lock`, `pcp->lock` from remote drains) delaying the rp1-cfe interrupt | all these hold times are microseconds on 16K pages; a late IRQ does not drop a frame unless the buffer requeue misses the next SOF | low prior; `irqsoff` tracer is not in the defconfig; skip unless A-C are excluded |
| **E.** A CFE node other than the raw one starves (stats/config nodes have fewer buffers than the 8 raw ones, so the real requeue deadline may be one frame period, not 7) | the capture-gap counter (`CameraController.cpp:9900-9930`) sees only the sensor-timestamp delta; it cannot say which node lacked a buffer | **M3**: `vb2:vb2_buf_done` / `vb2_qbuf` tracepoints per video node: a hole in `buf_done` sequence numbers on the raw node with no late `qbuf` on it, but a late `qbuf` on `fe_stats`/`fe_config`, names the starved node. Dynamic debug (`has no buffer`) is **unavailable** on this kernel (no `CONFIG_DYNAMIC_DEBUG`) |
| **F.** CSI-2 receiver errors (the 1782 Mbps link above the PHY's 1500 Mbps) | would not correlate with memory state at all; the 2026-10-26 run with `track_csi2_errors=1` saw all-zero counters | `rp1_cfe.track_csi2_errors=1` + `/sys/kernel/debug/rp1-cfe*/csi2_errors` during a losing minute (one reboot) |

Mechanisms A and B are the two the kernel source actually offers for a 40 ms stall of a user thread under this
regime; C is the other thing a full-time kswapd does to CPU0. The measurements M2, M4 and M5 are each one take.

---

## 6. The measurements, exactly (tracefs first: no packages; `perf` where it is cheaper)

Common to all: `S=/sys/kernel/tracing` (mount: `sudo mount -t tracefs nodev /sys/kernel/tracing` if empty);
`T=$(ps -eLo tid,comm | awk '$2=="CameraManager"{print $1}')` for the capture thread (the comm libcamera gives it;
`ps -eLo tid,ni,comm | grep -i camera` if the name differs); `U=$(pgrep -f Apertar-UI | head -1)`.

**M0, config (10 s, no take):** `getconf PAGESIZE; zgrep -E "CONFIG_(ARM64_16K_PAGES|LRU_GEN_ENABLED|PSI_DEFAULT_DISABLED|HZ|KPROBES|KPROBE_EVENTS|FUNCTION_TRACER|DYNAMIC_DEBUG|SCHEDSTATS|BPF_EVENTS)=" /proc/config.gz; grep -E "^(zone|  *(min|low|high|boost|managed))" /proc/zoneinfo; grep -E "nr_dirty_(background_)?threshold" /proc/vmstat; cat /proc/pressure/memory`.
Settles: page size (all byte arithmetic), MGLRU, PSI availability, HZ, whether kprobes/ftrace-function exist, the real
per-zone watermarks and the effective dirty thresholds.

**M1, does Core's writer ever run the cross-CPU drain (one 60 s `writer` take):**
```
sudo sh -c "echo 65536 > $S/buffer_size_kb; echo > $S/trace; echo 1 > $S/events/workqueue/workqueue_execute_start/enable; echo 1 > $S/tracing_on"
# ... take ...
sudo sh -c "echo 0 > $S/tracing_on; grep -c lru_add_drain_per_cpu $S/trace; grep lru_add_drain_per_cpu $S/trace | awk '{print \$2}' | sort | uniq -c"
```
Reading: the claim predicts ~1,500 executions per 60 s (25/s, one per written file, on up to 4 CPUs each); the source
predicts ~0 attributable to Core (any that appear come from compaction/migration and will be there under `sync` too; run
the same 60 s under `sync` to compare). If the count is ~0 under `writer`, section 1.2 is confirmed and the drain is off
the table. (Alternative if `perf probe` works, i.e. kprobes exist: `sudo perf probe -a lru_add_drain_all; sudo perf stat -e probe:lru_add_drain_all -a sleep 60`.)

**M2, the direct-reclaim counters (no take: the 2026-11-01 transcript; then every take):** the `compaction during take:`
line of `take3.sh` already printed `pgscan_direct`, `allocstall_normal`, `allocstall_movable` deltas for #70-#80. Copy
them into the night report §2. Then add `pgsteal_direct pgscan_direct_throttle` to the `S()` list and print the deltas
**per minute** next to the per-minute lost count. Reading: `pgsteal_direct` + `pgsteal_kswapd` ~ 4.6 M per 3-min take
means all freeing was reclaim; `allocstall_*` in the thousands per minute means allocators were reclaiming for
themselves; **`pgscan_direct_throttle` > 0 means some thread slept with no timeout** (mechanism A possible); under
`sync` all of these should be ~0.

**M3, where the frame dies (one 60 s losing take):**
```
sudo sh -c "echo 65536 > $S/buffer_size_kb; echo > $S/trace; echo 1 > $S/events/vb2/enable; echo 1 > $S/events/v4l2/enable; echo 1 > $S/tracing_on"
# ... take ...
sudo sh -c "echo 0 > $S/tracing_on; cp $S/trace /tmp/vb2.trace"
```
Then for each video node (`minor=` / device in the lines; `media-ctl -p` maps them to `csi2_ch0`, `fe_image0`, `fe_stats`,
`fe_config`), list `vb2_buf_done` sequence numbers and look for holes; for each hole, the time of the last `vb2_qbuf` on
each node before the missing SOF. Reading: a hole on all nodes with every node still holding queued buffers = the sensor
or link skipped (F); a node with zero queued buffers at the hole = that node starved (E), and the thread that was late
to `qbuf` it is the one that stalled (then M4-M6 say why). Needs only tracepoints; no dynamic debug.

**M4, who enters direct reclaim and for how long (one 3-min `writer` take):**
```
sudo sh -c "echo 65536 > $S/buffer_size_kb; echo > $S/trace; echo 1 > $S/events/vmscan/mm_vmscan_direct_reclaim_begin/enable; echo 1 > $S/events/vmscan/mm_vmscan_direct_reclaim_end/enable; echo 1 > $S/events/vmscan/mm_vmscan_throttled/enable; echo 1 > $S/events/vmscan/mm_vmscan_kswapd_wake/enable; echo 1 > $S/events/vmscan/mm_vmscan_kswapd_sleep/enable; echo 1 > $S/tracing_on"
# ... take ...
sudo sh -c "echo 0 > $S/tracing_on; awk '/direct_reclaim_begin/{c[\$1]++} END{for(k in c) print c[k], k}' $S/trace | sort -rn | head -20"
```
Reading: the first column is episodes per `comm-pid`; `CameraManager-<tid>` present at all = the capture thread
reclaimed (begin-to-end per pid gives the length: pair the lines by pid); `Apertar-UI-*` present = mechanism B's first
half; only writer threads present = the writers absorb it (fine, they have a queue) and the capture thread's stall is
elsewhere (M5/M6). Note the `throttle_direct_reclaim` sleep happens **before** `_begin` (`vmscan.c:6525`), so a thread
can stall there without a `_begin` line: that case shows as `pgscan_direct_throttle` (M2) and as run-queue-free sleep
in M6. Per-thread totals without tracing: `sudo sysctl kernel.task_delayacct=1`, then after the take
`getdelays -d -t $T` (RECLAIM count and delay, `tools/accounting/getdelays.c`, has to be compiled once).

**M5, run-queue wait of the capture thread, per second (any take, no setup):**
`while :; do echo "$(date +%T) $(cat /proc/$(pgrep -f ApertarCore|head -1)/task/$T/schedstat)"; sleep 1; done`
Fields: ns running, ns waiting on a run queue, timeslices. Reading: a second in which field 2 grows by >= 40 ms is a
second in which the thread was runnable but not scheduled for a frame period (mechanism C: see what ran, M6); a second
with a lost frame and **no** wait growth means the thread was sleeping (A, B or E), not waiting for a CPU.

**M6, the hole itself (one losing take, `linux-perf` from apt):**
`sudo perf sched record -a -- sleep 60` during the take, then `sudo perf sched timehist -p $T` (wait and run per switch;
look for a gap >= 40 ms and whether the thread was sleeping (`sleep` column) or waiting (`wait`)), and
`sudo perf sched timehist --cpu 0` for what ran on CPU0 in that gap. For the sleep stack:
`sudo perf record -e sched:sched_switch -g -t $T -- sleep 60; sudo perf script | grep -B1 -A12 "prev_state=[SD]"` and
read the call chains at the long sleeps (`try_to_free_pages`/`throttle_direct_reclaim` = A; `__sys_sendmsg`/`futex` into
the UI feed = B; `v4l2_ioctl`/`vb2_dqbuf`-type waits = the pipeline itself).

**M7, PSI (one reboot):** `psi=1` appended to `/boot/firmware/cmdline.txt`; then
`while :; do echo "$(date +%T) $(grep -E 'some|full' /proc/pressure/memory | tr '\n' ' ')"; sleep 1; done` during a take.
Reading: `some total` (us) growing by tens of thousands per second while frames are lost, and ~0 under `sync`, is the
whole-system stall budget; it does not name the thread (M4 does).

Order for Patrik: M0 (10 s) and M2-from-transcript (no take) today; then M4 + M5 together on one `writer` take (they
coexist; M5 is a shell loop), and M1 on the same take if the buffer allows (or the next). M3 and M6 only if M4/M5 show
the capture thread neither reclaiming nor waiting for a CPU.

---

## 7. What remains unconfirmed after the source reading

1. Page size on the running kernel (16 KiB from the defconfig; `getconf PAGESIZE`). Everything in section 3.2 scales with it.
2. The `allocstall_*` / `pgscan_direct` deltas of 2026-11-01 (printed, not recorded). They decide whether the `writer`
   regime was a direct-reclaim regime at all, and how much of the 20-26 GB per take that kswapd did not free was freed by
   allocators themselves versus by the fadvise's own eviction of already-written pages.
3. Whether any page allocation happens on libcamera's completion thread in steady state (M4/M5/M6). Without one, the
   kernel's memory regime cannot stall that thread directly, and the path to a lost frame has to go through the UI (B), the
   CPU (C) or a starved CFE node (E).
4. Which CFE node sets the real requeue deadline (E; libcamera's buffer counts for `fe_stats`/`fe_config` are not in the
   checked-out sources).
5. `fs/exfat` `writepages` = `mpage_writepages`, `fs/sync.c` `SYNC_FILE_RANGE_WRITE` = `__filemap_fdatawrite_range(WB_SYNC_NONE)`,
   kworker priority defaults (`kernel/workqueue.c`), HZ = 250: all from memory of the upstream sources, none from this checkout.
6. Whether the Pi kernel has kprobes/function tracing (M0); if not, M1 via the workqueue tracepoint is the only way to count the drains.
