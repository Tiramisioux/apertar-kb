# The SSD long-take run, re-read from its per-second samples (2026-11-08)

Run: `longtakes-ssd-2026-11-07/` (Samsung PSSD T7 466 GB, exFAT, USB 3.0; Core `cinemate-port` `f4a1393`; 189 takes, 20.1 h recorded,
5.9 TB written). The findings page `findings-longtakes-ssd-2026-11-07.md` read the per-take results. This page reads the 1 Hz samples
and the journal lines the runner stored in `longtakes.db`, with `working/tools/longtakes_fill.py` (every table below is its output).
Labels as in the KB: **measured** (counted in the data), **derived** (arithmetic on measured values, assumptions named),
**probable**, **unconfirmed**. Nothing here ran on the Pi.

## 1. Method: the free-space series is the writers' progress

exFAT allocates a file's clusters at `write()` time (`exfat_get_block` -> `exfat_map_cluster`, rpi-6.12.y `fs/exfat/inode.c`), so the
free space the runner sampled every second falls exactly as Core's writer threads take frames from the RAM write buffer, whatever the
drive does behind the page cache. From that:

- **drain** = bytes written by the writers per second (MB/s), per 5-minute window and per 5 s in the tail of a failed take;
- **implied buffer fill** = frames the sensor delivered (fps x t) minus frames written, against the take's `queue_budget` from the stats
  line. Its sign is off by the 1-3 % error of the per-file size estimate (20 files sampled); the shape is what counts.

Resolution: free space is stored to 0.1 GiB (107 MB), so one 5 s window at 50 MB/s carries a quantisation of about 40 %; 5-minute
windows are exact to about 1 %.

## 2. Three kinds of buffer_full (measured)

Of the 118 takes that ended in Core's 90 % safety stop:

| Kind | Takes | What the samples show | Reading |
| --- | --- | --- | --- |
| **slow** | 78 | the drain never reached the need; the buffer filled within about three budgets of input (6-20 s) | the writer pattern's steady-state capacity on this drive: all 4K takes (drain 77-120 MB/s for 10-12 MB files against 354 MB/s of large direct writes), and the first steps of each 2K walk |
| **late** | 32 | drain equal to the need within 1-3 % for 7-28 minutes, then the buffer filled in less than a minute | not a drive that slows; a cost that grows with the take until it crosses the frame period (section 4) |
| **stop message** | 8 | as "late" or "slow", plus Core's journal line `recording stop: no frame written for 5146 ms, treating the medium as gone` | all 8 came **after** the safety stop, during the drain of the full buffer, with `written == enqueued` in the stats line: a stop-path effect, not a stall during the take (section 5) |

Example (late): `2kSDR12_lossless ... fps38`, 1637 s, 61,806 files. Need 48.2 MB/s. Drain per 5-minute window: 49.8, 49.7, 49.7, 49.8,
49.7, then 45.5 in the last 140 s. Budget 798 MiB = 17.4 s of input. The implied fill stayed near zero for 25 minutes and reached 90 % in
the last two.

The failed 30-minute takes stopped at these file counts (measured): 33,566 / 33,582 / 33,887 / 35,195 (2K Clear HDR at 29-30 fps),
40,540 / 44,891 / 48,162 / 49,428 / 52,329 (28-36 fps), 60,821 / 61,806 (2K SDR 12-bit lossless at 37-38 fps). The 30-minute passes
ended at 45,006-59,412 files. The failing file count rises with the fps and falls with the file size.

## 3. The findings page's "drive slowing over time (heat or cache)" does not match the drain (measured)

In every late failure the drain tracked the need to within 1-3 % for the whole take and the buffer filled only in the last 1-3 minutes.
A drive that slows gradually would show the drain falling for minutes before the stop; a drive that stalls for seconds would show the
free space standing still for seconds (it never did for more than one 5 s sample before the safety stop). The time dependence is real;
its shape is "a growing cost crosses a threshold", and section 4 says what grows.

## 4. Core's CPU doubles over every long take, in proportion to the files in the clip folder (measured; the reading is derived)

The runner sampled Core's CPU (sum over its threads) in the 17 long takes of the Log stage. In every one of them it rose steadily from
0.45-0.62 of a core at the start to 0.80-1.29 at the end, at a constant frame rate, with free memory flat. The busiest thread moved from
libcamera's `CameraManager` (12-14 %) to an unnamed Core thread (17-27 %; Core names none of its threads, so the writers, the copy
worker and the sync thread all read as `apertar-core`).

| Take (fps) | Core CPU, start -> end | Slope per s | Derived c (ns per directory entry) |
| --- | --- | --- | --- |
| 2kHDR16 + Log 25 fps, 30 min | 0.51 -> 1.06 | 3.06e-4 | 98 |
| 2kHDR16 + Log 27 fps, 30 min | 0.54 -> 1.24 | 3.88e-4 | 106 |
| 2kHDR16 + Log 28 fps, 30 min | 0.58 -> 1.29 | 3.98e-4 | 101 |
| 2kHDR12 + Log 25 fps, 30 min | 0.45 -> 1.00 | 3.04e-4 | 97 |
| 2kHDR12 + Log 27 fps, 30 min | 0.51 -> 1.14 | 3.48e-4 | 95 |
| 2kHDR12 + Log 28 fps, 30 min | 0.51 -> 1.26 | 4.13e-4 | 105 |
| the other 11 (10-28 min, 25-30 fps) | 0.53-0.62 -> 0.80-1.26 | 2.9e-4 to 6.0e-4 | 77-133 |
| **median of 17** | | | **99** |

The derivation: on this kernel every file create walks every entry of its folder under the filesystem lock (`exfat_lookup` ->
`exfat_find_dir_entry`, rpi-6.12.y; confirmed in `working/dng-chain/F/V-F4.md` row 16), and Core's 33-character frame names take
5 entries each (row 17). If the whole CPU slope is that walk, extra CPU(t) = fps x c x 5 x N(t) with N(t) = fps x t, so
**c = slope / (fps^2 x 5)**. The 17 takes give 77-133 ns, median **99 ns per entry** (derived; it assumes no other cost grows with the
file count). The KB's estimate was 80-250 ns (V-F4 row 18, never measured) with an upper bound of about 450 ns from A0/A1.

**Measured the same day** by the zero-wear directory probe on the NVMe test card (`../nvme-campaign/probe-exfat-dir.md`): **c = 63.3 ns per
entry** (60,000 empty files, idle machine, warm cache, pure CPU, linear). The CPU slope of a real take is therefore about 1.6 times the walk
alone: the rest is another cost that grows with the folder during a take (probable: the walk misses the cache more often under 100 MB/s of
DNG data than on an idle machine; or futex spinning of the writers that wait for the lock; unconfirmed). Read the 99 ns as the all-in
per-entry cost of a take and the 63 ns as the walk alone.

What the two constants mean for one folder (derived, 5 entries per file; the first figure uses the take's all-in 99 ns, the figure in
brackets the probe's 63.3 ns):

| Files in the folder | Create cost | Share of the frame period at 25 / 30 / 33 / 50 fps |
| --- | --- | --- |
| 15,000 (10 min at 25 fps) | 7.4 ms (4.6) | 19 / 22 / 25 / 37 % (11 / 14 / 15 / 23) |
| 22,500 | 11.1 ms (6.9) | 28 / 33 / 37 / 56 % (17 / 21 / 23 / 35) |
| 45,000 (30 min at 25 fps) | 22.3 ms (14.1) | 56 / 67 / 74 / 111 % (35 / 42 / 46 / 70) |
| 54,000 (30 min at 30 fps) | 26.7 ms (16.9) | 67 / 80 / 88 / 134 % (42 / 51 / 56 / 85) |
| 59,400 (30 min at 33 fps) | 29.4 ms (18.6) | 74 / 88 / 97 / 147 % (47 / 56 / 61 / 93) |
| 90,000 (30 min at 50 fps) | 44.6 ms (28.3) | 111 / 134 / 147 / 223 % (71 / 85 / 93 / 142) |

By the probe prompt's pre-registered rule (a create of at most 25 % of the frame period keeps one folder), every 30-minute target is above
the line with either constant, so `[storage] frames_per_folder` is a prerequisite of the long stages (the probe page says the same).

Against the run: the 38 fps lossless failures came at 61,000 files, where the walk alone (30 ms) exceeds the 26.3 ms frame period; the
2K Clear HDR failures at 29-30 fps came at 34,000-35,000 files (walk 17 ms, about half the period) in modes that already needed 85 % of
the drive's capacity for this write pattern (section 6); the 30-minute passes sat at 56-97 % of the period (2K SDR 10-bit at 33 fps
passed with 59,412 files and a 97 % share, the tightest). Two budgets decide a take: the drive's throughput for the pattern, and the
serialised per-file metadata time, which grows with the folder. A mode near the first fails at a smaller folder. (probable)

The first NVMe run (git `242c0be`, erased) logged the same shape in its long takes: "CPU 49-54 -> 63-64 %" with free RAM flat.

## 5. "Media stopped responding: nothing was written for 5 s" is the stop path, not the drive (measured; mechanism read from code)

All eight messages came 8.6-13.6 s after the safety stop, with `written == enqueued` (every frame reached the file system). In the stop,
Core sets `stopping_` (`CameraController.cpp:4424@f4a1393`), and the once-a-second sync thread ends on that flag (`syncLoop`, `:4711-4714`)
**before** the writers drain the 300-800 MB still queued. Nothing fsyncs during that drain, so dirty pages pile up until the kernel's
writeback throttling slows the writers; the stop waits for them and declares the medium gone when no frame completes for
`APERTAR_WRITE_STALL_MS` (5000 ms, `:4810`; message at `:4446`), marking the take `media_removed`. The recorder stop times of all 118
buffer_full takes were 2-14 s, which is the time to drain the buffer at the measured rate. (probable; the dirty-page part is read
from the code order, not measured: the new sampler columns `dirty_kb` / `writeback_kb` show it next time)

## 6. The 4K ("slow") regime: the writer pattern reaches a third of the drive (measured)

The T7 wrote 354 MB/s in the calibration (60 GiB of 16 MiB direct writes). Core's pattern (4 writers, 480 KiB chunks through the page
cache, one `fsync` per file on the sync thread) drained 77-120 MB/s with 10-12 MB files and 80-110 MB/s with 2.6-4.2 MB files. On this
drive the pattern, not the medium, sets the 4K ceiling. What the pattern costs that a single large direct write does not: one `fsync` per
file, which on exFAT is `__generic_file_fsync` + `sync_blockdev` (every dirty metadata buffer of the device) + a FLUSH command
(`fs/exfat/file.c:518-535`); cluster allocation one cluster at a time under the filesystem lock, interleaved between the four writers
(`exfat_map_cluster` allocates `clu_offset - num_clusters + 1` = 1 cluster per step; a non-adjacent cluster turns the file into a FAT
chain, `exfat_chain_cont_cluster`); and 24,300 lock takes per 12.4 MB file for the 512-byte block mappings (V-F4 row 19). Which of these
carries the loss is not measured; `working/tools/exfat_write_probe.py` switches them one at a time without the camera.

## 7. Trim state during the run: unknown (measured absence)

`trim_events` is 0 in every row and no `media: trim` line exists in any take's journal window. The windows start at `record_start`, so a
trim after the runner's delete would fall outside them, and the sampler read Core's `media_trim_last_*` fields every second but did not
store them. The running build asks for a trim after a delete made outside Core only when the medium gains **1 GiB or more between two
polls** while idle (`ApertarCoreApp.cpp:10863-10869@f4a1393`). The directory probe measured a warm-cache unlink at 5 us per file (60,000
files in 0.5 s), so the runner's deletes freed their 50-150 GB within a second or two and the trigger very probably fired after every
take (probable). What the trim then did is unrecorded: whether the T7 accepts one at all over its USB bridge
(`/sys/block/sda/queue/discard_max_bytes`, checked by `scripts/apertar-media-trim:67-69`) was never read, and `media_trim_last_result`
was never stored. The run cannot say anything about trim either way; the runner now records the trim state per take.

## 8. The RAM budget varied five-fold between takes (measured)

`buffer: ram budget` lines: 250-1283 MiB (median 635) as MemAvailable moved between 1270 and 2991 MiB (fraction 0.60, floor 512 MiB,
`BufferBudget.hpp:31-33`). In seconds of input that is 1.6-17 s, so "time to buffer full" is not comparable between takes and a stall
of 3 s ended some takes that a 17 s budget would have absorbed. The budget should be fixed (or logged and normalised, as
`longtakes_fill.py` now does) before any time-to-failure is compared.

## 9. Corrections to `findings-longtakes-ssd-2026-11-07.md`

| Line there | Status now |
| --- | --- |
| "Long takes slow down ... looks like the drive slowing over time (heat or cache)" (unconfirmed) | the drain did not slow; a per-file cost grew with the folder (section 4). Heat and cache stay unmeasured on the T7 |
| "The SSD's limit is per frame, not per MB/s ... fixed cost per file (one DNG per frame on exFAT over USB)" (probable) | holds for the steady state (section 6) with the cost named: fsync+FLUSH per file, per-cluster allocation under the lock; and it is not fixed: the create walk adds 0.5 us per file already in the folder |
| "Every stop was buffer full; no take stopped on a dropped frame" | holds; eight of them were then marked `media_removed` by the stop path (section 5) |
| "Trim off: 2 takes, no visible effect" | no take can speak for trim: whether Core's trims after the deletes succeeded on the T7 was never recorded (section 7) |

## 10. What this data cannot tell

The writers' progress is known to 0.1 GiB per second, the buffer level never (the runner now samples `buffer_used`); the drive's own
completion latency never (`/sys/block/<disk>/stat` is now sampled); which Core thread grew (Core sets no thread names); dirty pages at
the stop (now sampled); the drive's temperature and trim support (`storage_facts.sh`). The directory-walk constant is derived here (all-in,
99 ns) and measured by the zero-wear probe (63.3 ns, `working/drop-frames/nvme-campaign/probe-exfat-dir.md`).
