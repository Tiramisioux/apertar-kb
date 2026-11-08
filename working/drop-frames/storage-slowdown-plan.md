# Storage campaign, revised: why writes slow down within a take and between takes (exFAT, SSD and NVMe) — 2026-11-08

Asked for (User, 2026-11-08): a revised campaign that focuses on the disk slowing down over time, a smarter way to run it, what was
missed, the levers in Apertar and the storage levers outside it. exFAT is fixed (macOS/Windows reads the cards).

Where this sits: the SSD campaign is done (`tests-2026-11/findings-longtakes-ssd-2026-11-07.md`, re-read in
`tests-2026-11/reanalysis-longtakes-ssd-2026-11-08.md`, the evidence for this page); the NVMe 4K recipe plan (`nvme-4k-recipe-plan.md`)
is written, not started; two pieces of work started 2026-11-08 in other sessions: the zero-wear exFAT directory probe
(`nvme-campaign/probe-exfat-dir.md`) and the clip-split knob `[storage] frames_per_folder` with its merge worker (Core branch
`clip-split`). This page does not repeat them; it says how the campaign should use them and what else it needs. Labels as in the KB:
**measured** / **derived** / **probable** / **unconfirmed**; Core anchors are on `cinemate-port` `f4a1393` (the SSD run's build), kernel
anchors on rpi-6.12.y `fs/exfat/`.

## 1. In one paragraph

"The disk slows down over time" is two different things, and the SSD run shows mostly the second. **Between takes**, the drive's state
changes (untrimmed free space, temperature, the free-block pool the controller has prepared); that is measured on the NVMe (stalls after
about 0.9 TB without a trim) and unmeasured on the T7, whose trim state during the run is unknown. **Within a take**, the writers' progress
stayed equal to the sensor's rate to within 1-3 % for 20-27 minutes and then the buffer filled in under a minute, while Core's CPU rose
from about half a core to more than one core at a constant frame rate: a cost that grows with the number of files in the clip folder.
The mechanism that fits is the exFAT directory walk every file create pays under the filesystem lock (confirmed in the driver; the
per-entry constant derived from the CPU slope is about 99 ns, which puts a 45,000-file folder at 22 ms per create, 56 % of a 25 fps
frame period). Steady-state, Core's write pattern reaches about a third of the T7's raw speed (fsync+FLUSH per file, per-cluster
allocation under the lock by four interleaved writers). The smarter campaign measures these three things separately, with the camera
only where the camera is needed, and uses the write buffer's level as a meter instead of searching for the highest clean fps.

## 2. What the re-analysis established (details and tables in the re-analysis page)

1. 118 buffer_full takes: 78 the writers never kept up (4K), 32 kept up for 7-28 min and then filled the buffer in under a minute, 8 carry
   a stop-path message. (measured)
2. No gradual slowing of the drain in any take; failures end with a sudden fill. (measured)
3. Core's CPU grows linearly with the files written, in all 17 takes that sampled it; derived c = 77-133 ns per directory entry, median 99.
   (measured / derived)
4. Failing file counts: 33,500-35,200 for 2K Clear HDR at 29-30 fps (modes at 85 % of the drive's pattern capacity), 60,800-61,800 for 2K
   SDR 12-bit lossless at 37-38 fps (small files, far from the throughput ceiling). Passes reached 59,412. (measured)
5. "Media stopped responding ... 5 s" came only after the safety stop, with every frame written: the sync thread ends before the drain,
   the stop's stall detector fires. (measured; mechanism from code)
6. The 4K drains were 77-120 MB/s against 354 MB/s raw: the pattern, not the medium. (measured)
7. Trim: never observed, never recorded; the free-space trigger (1 GiB between two polls) may never fire after a slow delete of 50,000
   small files. (measured absence; derived)
8. The RAM budget varied 250-1283 MiB (1.6-17 s of input) with MemAvailable. (measured)

## 3. Mechanisms, each with the test that settles it and the lever it points at

| # | Mechanism | Time scale | Evidence today | Status | Settles it | Lever |
| --- | --- | --- | --- | --- | --- | --- |
| M1 | exFAT create walks every entry of the folder under `s_lock` (`exfat_lookup` -> `exfat_find_dir_entry`); 5 entries per frame file | within a take, grows with N | V-F4 rows 16-17 (source); Core CPU slope in 17 takes; failing file counts | confirmed mechanism; share **probable** | the zero-wear probe (c directly; in progress); `perf top -p <core>` in minute 25 of a take; 3 x 10 min back to back against 1 x 30 min at the same fps | `[storage] frames_per_folder` (in progress); fewer files (MLV, Log, lower fps); shorter names (a 16-char clip prefix saves one entry) |
| M2 | one `fsync` per DNG on the sync thread = `__generic_file_fsync` + `sync_blockdev` + FLUSH, 25-60 per second | steady | `fs/exfat/file.c:518-535`; A1 on the NVMe: no cost at 415 MB/s; on USB unmeasured | confirmed mechanism; cost **unconfirmed** | `exfat_write_probe.py --fsync none` against `tick` at the same size and rate; `sync_ms=0` in the tune override for one take | Core: one FLUSH per tick (per-file `sync_file_range(WAIT_BEFORE\|WRITE\|WAIT_AFTER)`, then one folder `fsync`, which on exFAT flushes the whole device) instead of one per file; the pull-safety stays 1 s |
| M3 | four writers allocate clusters one at a time under `s_lock`; interleaved allocation turns every file into a FAT chain (`exfat_map_cluster`: 1 cluster per step; `exfat_chain_cont_cluster` on the first gap); FAT-chain files write FAT entries per cluster and read FAT sectors synchronously (the 2026-10-30 NVMe stall stack `exfat_alloc_cluster > exfat_ent_set > __bread_gfp`) | steady; stalls when the FAT read waits behind a slow drive | driver source; the stall stack; dng-chain R2 §2.3 | mechanism confirmed; fragmentation **unconfirmed** (never looked) | `sudo filefrag -v` on three DNGs of a fresh take (extents > 1 = chained); `exfat_write_probe.py --workers 1` and `--prealloc` against the default | Core: `ftruncate(fd, final size)` right after open: `exfat_cont_expand` allocates all clusters in one call without zeroing (`file.c:19-82`), so the file is contiguous and the FAT untouched; `workers=1` as the no-code test; one `write()` per file (cinepi-raw's way) |
| M4 | drive state: untrimmed free space, controller GC | between takes, hours | NVMe: stalls after ~0.9 TB (hardware-log 2026-10-30); T7: unknown, never trimmed on record | measured on the NVMe; **unconfirmed** on the T7 | `storage_facts.sh` (discard support), `sudo fstrim -v` timing; `exfat_write_probe.py` 60 s at full speed: trimmed vs after 2 volume passes | Core trims after deletes (fix the 1 GiB-per-poll trigger: accumulate freed bytes since the last trim); the runner records `media_trim_last_*` per take (done); format = full trim |
| M5 | drive temperature | within and between takes | T7 none (no sensor read); NVMe to 72 C with no effect seen (evening 3) | **unconfirmed** | `sudo smartctl -a /dev/sda` once a minute (sudoers line); the fan A/B (a fan on the drive, same take twice) | airflow; idle gaps |
| M6 | USB SSD SLC cache cliff (cinemate's "~90 s") | within a take | 354 MB/s held over 60 GiB of direct writes: not seen | low prior | the probe at full speed for 10 min shows it or not | none needed |
| M7 | page cache and memory: `dontneed=sync` keeps the cache low during a take; at the stop the sync thread ends and the drain runs without fsync | at the stop | section 5 of the re-analysis; MemAvailable flat during takes | **probable** | `dirty_kb`/`writeback_kb` per second (sampled now) across a safety stop | Core: keep the sync pass running until the queue is empty; raise `APERTAR_WRITE_STALL_MS` while draining a full buffer so a healthy drive is not declared gone |
| M8 | RAM budget size and variance | tolerance to everything above | 250-1283 MiB in one run | measured | none needed | `[storage] buffer_ram_fraction 0.9`, `buffer_ram_floor_mb 256` for the campaign (fixed, logged); a fixed-MiB key is a small Core change; an 8 GB CM5 doubles it |
| M9 | USB path: BOT (`usb-storage`, one command at a time) vs UAS; queue depth 30; the mic on the same controller; port power | steady | Core classified the T7 as `usb-storage` (`MediaProfile.hpp:88`): either the BOT driver or the uevent read at the wrong level | **unconfirmed** | `storage_facts.sh` (driver behind the disk, `lsusb -t`, `usb_max_current_enable`) | a UAS enclosure if it is BOT; the mic on the other controller; `usb_max_current_enable=1` |
| M10 | NVMe host memory buffer refused (`nvme.max_host_mem_size_mb=0`; the MP600 Mini asks for 64 MiB: kernel log 2026-10-30) | steady and GC | DRAM-less drive without HMB pages its mapping table from NAND | **probable** (the drive asks for it) | one test boot without the argument, the same 10-min take | the boot argument |
| M11 | capture side at 4K: a growing per-file CPU cost (M1) raises the chance of a capture gap | within a take | first NVMe run: CPU 49-54 -> 63-64 % in long takes, every drop a capture gap | **unconfirmed** | the 30-min 4K take at 25 fps with the split knob on and off | the split knob; everything in `recipe.md` |

TDN, the FE config queue depth, the raw buffer count and the preview switches act on the capture side (recipe rows 7-8): they decide the
4K fps ceiling on the NVMe and have nothing to act on when the limit is storage (every SSD stop was buffer full). They stay fixed at the
recipe's values and are not campaign factors here.

## 4. The smarter method: measure, do not search

The SSD campaign spent 20 hours and 5.9 TB on a pass/fail ladder (5 / 10 / 20 / 30 min) whose outcome depended on a budget that varied
five-fold and on a cost that grows with the folder. Three changes make the same questions cheap:

### 4.1 The write buffer is a meter

Core's RAM buffer level (`GET /api/buffer`, `buffer_used` / `buffer_capacity`; also in `get_state`) is the integral of (delivered minus
written). Sampled once a second (the runner does now), its slope is the writers' deficit in frames per second at every moment of a take:
`drain_fps(t) = fps - d(buffer_used)/dt`. One 90 s take at a frame rate 20-30 % above the expected capacity gives the capacity of that
configuration to about 1 %, and the curve says whether it is steady (the drive) or grows (the folder). No ladder, no bracket search, one
take per configuration. The runner's A/B takes already run to a fixed length without stopping at the first drop (`stop_on_drop=False`); a
meter take is one of those with the fps set above the capacity and `buffer_used` read, nothing else.

### 4.2 Camera-free probes first (minutes, chosen wear)

| Probe | Tool | Answers | Wear |
| --- | --- | --- | --- |
| directory walk: c, create cost vs N, unlink cost | `exfat_dir_probe.py` (other session; empty files) | M1 directly; the pre-registered 25 % rule of that prompt | ~10 MB |
| write pattern, one lever at a time | `working/tools/exfat_write_probe.py`: `--workers 1/2/4`, `--prealloc`, `--fsync none`, `--chunk-kb 0`, `--direct`, `--subdir N`, paced `--fps F --budget-mb B` | M2, M3, M6, and the capacity of each variant in files/s and MB/s with per-file latency and the device's own write latency | files x size: 300 x 12.4 MB = 3.7 GB per variant at 4K; 2 min at 2K rates = 12 GB |
| drive facts | `working/tools/storage_facts.sh` | M4 (discard support), M9 (driver, power), M5 (the smartctl line), cluster size, kernel knobs, Core's trim state | none |
| drive state | the write probe at full speed, 60 s: right after `fstrim`, then after two volume passes of probe writes, then after 30 min idle; with the fan on and off | M4, M5 between takes | 2 passes = 930 GB on the T7 (the one expensive step; skip if `discard_max_bytes` is 0 and the drive cannot be trimmed anyway) |

Order: facts (10 min) -> directory probe (40 min, running) -> write-pattern matrix at 4K size (8 variants x 300 files, about 30 GB,
under an hour) -> paced 2K emulation of a failing configuration (`--size-mb 1.3 --fps 38 --seconds 1800 --budget-mb 800`, 88 GB) with
and without `--subdir 5000`: if the paced probe fails at the same minute as the camera did and passes with sub-folders, M1 is settled
without a sensor in the loop.

### 4.3 Time dependence with the camera (only what the probes cannot answer)

1. **Split test**: at the fps that failed at 25-27 min, three 10-minute takes back to back (no idle, same folder count reset each time)
   against one 30-minute take. Three passes and one failure = a per-folder cost (M1); three failures = drive or memory state carried
   across takes (M4/M5/M7). One hour per mode.
2. **The knob A/B** when `frames_per_folder` exists: the same 30-minute take with 0 and with the probe's N (the other prompt's rule:
   N = 0.25 x frame period / (5 x c); c = 99 ns gives 20,000 at 25 fps and 15,000 at 33 fps; the suggested 5,000 is well inside), the
   merge worker off. Instrumented as below; the buffer curve and the CPU slope are the readings, not only pass/fail.
3. **MLV control**: one 30-minute MLV take at the same fps (one file per clip, no per-file create, no per-file fsync). It passes where
   cDNG fails if, and only if, the per-file costs are the cause. A diagnostic, not a recipe.
4. **One fully instrumented long take per mode at 90 % of the measured capacity**, 30 min: the curves (buffer, Core CPU, device latency,
   dirty pages, temperature) are the deliverable for the KB; a failure is extra information, not the purpose.

### 4.4 What every take records now (runner `longtakes.py`, 2026-11-08)

Per second: `buffer_used`, `buffer_capacity` (the meter), `/sys/block/<disk>/stat` writes, sectors, write ticks and in-flight (the
device's own mean write latency = delta ticks / delta writes; in-flight 0 while the buffer grows = the stall is in the filesystem or
Core, not the drive), `Dirty` and `Writeback`, Core's `media_trim_running` / `media_trim_last_unix`. Per take: `queue_budget_mib`,
`budget_seconds`, `recorder_stop_s`, `stall_msg`, `idle_gap_s`, `core_cpu_slope` (c follows as slope / (fps^2 x 5)), `trim_before`
(Core's last trim result and whether it finished since the previous take). DNGs are counted recursively (`part_*/`). Untested on the Pi:
host-tested for syntax, the dry run and the database ingest; the first run should be a smoke test (`--max-seconds 20 --only 1`).
Analysis: `working/tools/longtakes_fill.py RUN_DIR [--tail 150]`.

Still missing and worth one Core change each: thread names (`pthread_setname_np` on the writers, the copy worker and the sync thread;
until then `core_top_thread` reads `apertar-core` for all of them), and a fixed-MiB budget key.

### 4.5 Rules

- One factor per comparison, interleaved, with the plain baseline repeated every fourth take; "no difference" when the effect is inside
  the baseline's spread (the NVMe plan's rule), measured on the buffer curve, not on pass/fail.
- The RAM budget fixed for the campaign (`[storage] buffer_ram_fraction 0.9`, `buffer_ram_floor_mb 256`) and logged; a result is read in
  seconds of input, never in minutes to the safety stop alone.
- The drive's state fixed and logged: `fstrim` before each stage (if supported), temperature at the start, idle gap recorded; a take
  that starts within 2 min of a 100 GB delete is marked.
- Every claim labelled; the camera is the last instrument, not the first.

## 5. Levers inside Apertar

| Lever | Acts on | How | Status |
| --- | --- | --- | --- |
| `[storage] frames_per_folder` (split; merge worker) | M1 | Core branch `clip-split` (other session) | being built |
| `ftruncate` to the final size after `open` in `writeDngFile` (`CdngEncoder.cpp:1871`, before `:1876`) | M3 | about 10 lines; the total is known before the first write (header + payload + pad + IFD); lossless: truncate down at the end | proposed; `filefrag` decides whether it is needed |
| one FLUSH per sync tick instead of one per file (`syncLoop`, `CameraController.cpp:4711`) | M2 | `sync_file_range(WAIT_BEFORE\|WRITE\|WAIT_AFTER)` per file, one `fsync(dirFd)`; exFAT's directory fsync flushes the device (`fs/exfat/dir.c:311-319`) | proposed; the write probe decides whether M2 costs anything on USB |
| keep the sync pass through the drain; stall limit while draining | M7 | `syncLoop` ends on `stopping_` (`:4714`); the stop waits with the 5 s detector (`:4446`, `:4810`) | proposed |
| trim trigger after an outside delete | M4 | `ApertarCoreApp.cpp:10863-10869`: 1 GiB between two polls; accumulate freed bytes since the last trim instead | proposed |
| fixed RAM budget | M8 | `[storage] buffer_ram_fraction` / `floor_mb` today (`BufferBudget.hpp:31-33`); a `buffer_ram_mb` key is small | conf today; key proposed |
| thread names | diagnosis | `pthread_setname_np` on the recorder's threads | proposed |
| `sync_ms` 0 / `writeback` off / `dontneed` (`~/apertar-media-tune.conf`, override file) | M2, M7 | exist; `sync_ms=0` also switches the page-cache drop off (`:4339`) | A/B instruments |
| `workers` 1 (tune override) | M3 | exists; the A/B tried 2 and 6, never 1 | A/B instrument |
| Log, lossless, 10-bit, lower fps | bytes and files | exist | recipe levers |
| MLV | all per-file costs | exists (one writer, no fsync: pull-unsafe) | diagnostic |
| trim on/off, pre-roll | M4 | exist | the pre-roll consumes prepared blocks; keep it off in storage tests |
| TDN, FE depth 4, `dontneed=sync`, raw buffers | capture side | recipe rows 6-8 | fixed, not factors |

## 6. Levers outside Apertar (exFAT stays)

| Lever | What it does | Check or caveat |
| --- | --- | --- |
| trim: `fstrim` after deletes, format = full trim | restores the controller's free-block pool (NVMe stalls after ~0.9 TB without it) | `discard_max_bytes` 0 on a USB bridge = cannot be trimmed; then keep the volume mostly empty and give the drive idle time; the `discard` mount option trims at unlink (slow deletes of chained files: not recommended) |
| cluster size `mkfs.exfat -c 1M` | 8x fewer allocations and FAT operations per file (R2 §2.3) | no change to the directory walk; macOS compatibility risk (cinemate reverted it); only after `filefrag` shows chains that `ftruncate` does not fix |
| mount options | `noatime` only; nothing else in the driver touches the write path | the automounter's options are outside this repo |
| `vm.dirty_*` | only matters once the per-file fsync goes (then cinemate's `usb_ssd` 256/128 MiB is the starting point) | measured no effect with the fsync in place |
| scheduler, `nr_requests`, `rq_affinity` | none | measured no effect; `nr_requests` could not be raised above 30 on the T7 (2026-11-07) |
| USB: UAS enclosure, separate controller for the mic, `usb_max_current_enable=1` | command queuing, interrupt load, brown-out margin | `storage_facts.sh` |
| drive temperature: airflow, idle gaps | M5 | `smartctl` once a minute; the fan A/B |
| NVMe HMB: remove `nvme.max_host_mem_size_mb=0` | mapping table in host RAM for a DRAM-less drive | one test boot; watch the kernel log |
| drive choice | a drive that reports UNMAP over USB; NVMe for 4K | cinemate recommends the T7; this run says 2K only on it |
| fill | keep below ~75 % (hardware-log 2026-10-26) | log `fill_pct` at the start (done) |

## 7. The ladder, with costs

| Stage | What | Camera | Time | Writes | Decides |
| --- | --- | --- | --- | --- | --- |
| S0 | `storage_facts.sh`; `fstrim` timing (Patrik) | no | 10 min | 0 | M4 testable at all; M9 |
| S1 | directory probe (running) | no | 40 min | 10 MB | c; the 25 % rule; the split knob's N |
| S2 | write-pattern matrix at 4K size: default, `--workers 1`, `--prealloc`, `--fsync none`, `--chunk-kb 0`, `--direct --prealloc`, `--subdir 5000`, cluster-size variant if formatted | no | 1 h | ~30 GB | which of M2/M3 carries the 4K ceiling; the Core patches worth writing |
| S3 | paced 2K emulation of the 38 fps failure, flat vs `--subdir`; drive-state variants if trim works | no | 2 h | ~200 GB | M1 without the camera; M4/M5 between takes |
| S4 | capacity meter takes, 90 s each, every mode and recipe | yes | 1 h | ~50 GB | the capacity table (replaces the 5-min ladder) |
| S5 | split test, knob A/B, MLV control, one instrumented 30-min take per mode | yes | 6-8 h | ~1.5 TB | the time dependence, settled with the camera |
| S6 | Core patches that S2 justified (`ftruncate`, one FLUSH per tick, drain fix), each A/B'd with the meter | yes | 2 h | ~100 GB | the recipe |
| S7 | soak: the recipe twice at 30 min per mode | yes | 3 h | ~1 TB | done means |

About 3 TB in all against 5.9 TB for the SSD ladder, and every stage produces a number, not only a pass or a fail. The NVMe 4K plan's
stages 0-6 stay as written for the capture-side question; its storage group C becomes S2/S3 here.

## 8. What was missed

1. The runner never stored the buffer level, the device's counters, dirty pages or Core's trim state, so the one run that could have
   shown the mechanism showed only the symptom. (fixed in the runner)
2. The directory walk was in the KB (dng-chain F4/V-F4, S1-16) since 2026-11-01 and never became a campaign factor or a Core knob
   until today; the campaign's own Core CPU samples carried its signature all along.
3. Interleaved cluster allocation by four writers (M3) was never checked with `filefrag`; "sub-folders, preallocation, writer count made
   no difference" (2026-10-30) was measured for the NVMe stall, not for this, and the preallocation tried then was `fallocate`, which
   exFAT does not implement (glibc writes zeros instead), so "worse" says nothing about `ftruncate`.
4. Trim on the T7 was assumed, not checked; the trigger for outside deletes needs 1 GiB between two polls.
5. The RAM budget was treated as constant; it varied five-fold.
6. The "stopped responding" takes were read as drive stalls; they are the stop path.
7. `workers=1` was not in the A/B (2 and 6 were); MLV was never used as a control.
8. The T7 ran as `usb-storage` in Core's classification; nobody checked whether that is the BOT driver.

## 9. Open points for Patrik

1. sudoers lines for `smartctl -a /dev/sda`, `filefrag -v` and `fstrim -v /media/RAW` for the runner's account (read-only except
   fstrim), or Patrik runs them by hand at the stage boundaries.
2. Is MLV acceptable as a 30-minute diagnostic take (its clips are not the workflow's)?
3. A fan on the drive for the temperature A/B.
4. Formatting the T7 with `-c 1M` for one S2 variant (macOS caveat), yes or no.
5. The Core patches of section 5, in the order S2 justifies them, after the clip-split branch lands.
6. The NVMe test boot without `nvme.max_host_mem_size_mb=0`.

## 10. Sources

Re-analysis: `tests-2026-11/reanalysis-longtakes-ssd-2026-11-08.md`, `working/tools/longtakes_fill.py` on
`tests-2026-11/longtakes-ssd-2026-11-07/`. Core `cinemate-port` `f4a1393`: `src/camera/CameraController.cpp` (`syncLoop` :4711-4714,
stop :4424-4446, stall limit :4810, `/api/buffer` App:8390), `src/cdng/CdngEncoder.cpp:1871-1898`, `src/ApertarCoreApp.cpp`
(trim :10863-10869, :10911, :11427-11448, :11563, :11588), `src/util/BufferBudget.hpp:31-33`, `src/util/MediaProfile.hpp:88,130`,
`scripts/apertar-media-trim:67-69`. Kernel rpi-6.12.y: `fs/exfat/file.c` (`exfat_cont_expand` :19-82, `exfat_file_fsync` :518-535),
`inode.c` (`exfat_map_cluster`, `exfat_direct_IO`), `fatent.c` (`exfat_alloc_cluster` :320-430), `namei.c:721`, `dir.c:311-319`.
KB: `working/dng-chain/F/V-F4.md` rows 16-20, `working/dng-chain/S1.md` S1-16, `working/dng-chain/R2.md` §2.3, `lessons/hardware-log.md`
2026-10-26 and 2026-10-30, `working/cinemate-lessons.md` §5, `working/port-raw/s1-storage-cinemate.md` §2 and §5. cinemate `4990afc`
and cinepi-raw `63a08d5` re-read 2026-11-08: no storage change since the KB's last read (one `write()` per DNG, no fsync, exFAT
profile 2 disk workers, no trim anywhere).
