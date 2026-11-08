# Long-take campaign: test structure (design of 2026-11-07)

Runner: `working/tools/longtakes.py` (runs on the Pi), Mac side `working/tools/webui_remote.py` (real WebUI client).
Plan and decisions: `longtakes-campaign-plan.md`. Labels: **measured** / **probable** / **unconfirmed**.

## Rig this structure was made for

CM5 Lite (revision `c041a0`, the C0 type), IMX585, Samsung PSSD T7 466 GB on USB 3.0 (5 Gbps, UAS driver), exFAT. Core classifies
it as `usb-storage`. **Sustained write 354 MB/s** (60 GiB of 16 MiB O_DIRECT writes in 182 s, 343-363 MB/s per GiB, no cache cliff;
measured). The NVMe runs of the same evening (Corsair MP600 Mini 932 GB, Kingston before that) were erased; their pattern
(every drop a capture gap, queue peak 2 of 12) is in the recipe's reading, not repeated here.

## 1. Which modes run: only what the storage can carry

DNG bytes per frame = width x raw height x bits / 8 (4K 16-bit Clear HDR frames are 2200 lines). A mode runs only if its rate at the
lowest fps tried (25) fits 98 % of the measured disk speed. Each mode also starts at the fps its data rate allows.

| Mode | MB/frame | MB/s at 25 fps | vs 354 | Highest fps by storage |
| --- | --- | --- | --- | --- |
| 4K SDR 12-bit | 12.44 | 311 | 88 % | 27 |
| 4K SDR 10-bit | 10.37 | 259 | 73 % | 33 |
| 4K Clear HDR 12-bit | 12.44 | 311 | 88 % | 27 |
| 2K binned SDR 12 / SDR 10 / Clear HDR 12 / Clear HDR 16 | 3.11 / 2.59 / 3.11 / 4.22 | 65-106 | 18-30 % | the mode's own limit |
| 4K Clear HDR 16-bit | 16.90 | 422 | 119 % | **excluded** |

All eight modes are activated in Apertar (Mode Ladder list, `ladder_count` 8, ladder off; backup `mode_ladder.conf.bak-before-2k-10bit`).

## 2. Factors per mode (64 combinations before pruning)

Compression (uncompressed / lossless), Log, preview TDN, frame-rate phase lock, drive trim, WebUI client (a real client on the Mac).
Baseline = uncompressed, Log off, TDN off, lock off, trim on, no client. fps steps down by 1 from the mode's top to **25**.

## 3. Ruling out options (so nothing is tried that cannot have an effect)

1. **By cause.** The baseline's failures say what limits the mode: *buffer full* (Core's RAM write buffer reached its 90 % safety stop,
   so the drive fell behind) = storage; *capture gap* = camera/ISP/memory; none (clean at the highest fps) = nothing to improve.
   Only switches that act on that limit are tried: storage -> compression, Log, trim and the storage tuning A/B; capture -> TDN,
   phase lock, WebUI, Log. A clean baseline prunes everything else. (rule; the mapping is a judgement)
2. **By result.** A switch whose single-switch config did not beat the baseline is never combined with others; combinations are made
   only from switches that helped ("better" = a higher clean fps, or a 2x longer time to failure).
3. **Data-rate frontier (same frame size only).** When an uncompressed take fills the RAM buffer at R MB/s, every uncompressed config
   of a mode with the same frame size (+-3 %) at or above 0.98 R is skipped (so 4K Clear HDR 12-bit, same bytes as 4K SDR 12-bit, is
   skipped once that one fails). Fixed 2026-11-07: the first version compared across frame sizes, and a 2K failure at 118 MB/s pruned 4K
   configs; the drive's limit is per file as well as per MB/s, so rates of different frame sizes are not comparable.
3b. **Smart step.** After a buffer-full failure the walk jumps to the fps the drive actually wrote in that take
   (`fps x (enqueued - queued at the stop) / enqueued`, +10-35 % headroom); if that is below 20 fps the config is ruled out without
   testing 25 ("ruled out in theory"). The walk starts at the fps the storage can theoretically carry (`--start-at-mode-max` overrides).
4. **No difference.** In every later round, if a simpler config (fewer switches) reached the same fps, the config with the extra
   switch is dropped and the log names it.
5. A take stops at the **first dropped frame** or at **buffer full**; failing takes are short, only passes cost recording time.

## 4. Duration ladder (successive elimination)

| Round | Take length | Who goes in |
| --- | --- | --- |
| 0 | 5 min | every config that survives the pruning above, walked down from the top fps to its first clean fps |
| 1 | 10 min | per mode the configs at the best clean fps of round 0 (at most 3, simplest first) |
| 2 | 20 min | the same from round 1 (at most 2) |
| 3 | 30 min, or until the 466 GB drive is full | the best of round 2 (1) |

A config that fails a round does not step down one fps at a time (a failed 30-minute take costs 27 minutes): it goes down 3, 6, 12 fps
until a take passes, then bisects between the highest pass and the lowest failure (`bracket_search`, tested offline: 8 takes instead
of 17 for a limit 16 fps below the start; one extra take when the limit is within a fps or two). Failures already recorded are reused
after a restart. A pass at 30 minutes, or a clean take until the drive is full (below 6 GiB free), counts as the top result.

## 5. Order of the run

1 baseline of each mode -> d the single-switch configs -> 2 storage A/B on the best config of each mode that the storage limited
(plus the plain baseline) -> r combinations of switches that helped -> c rounds 1-3. Clips are cleared before every take (only the
runner's own, unless `--clear-all`).

## 6. Storage tuning A/B (only where storage limited the mode)

Interleaved, 3 repeats, 120 s each, no stop at the first drop (metric = frames dropped, queue peak, time to buffer full). Variants:
base, `workers` 2 and 6, `queue` 24 and 48, `sync_ms` 500 and 2000, `kernel_tune`. The override file is
`/run/apertar-media/media-tune.override.conf` (via `scripts/apertar-tune`); Core re-reads it when a take starts.
`kernel_tune` is applied by calling the root helper `apertar-media-tune` directly (Core's account may, `sudo -n`), with the
dirty-page, scheduler and queue values read back from `/proc` and `/sys` for every take (column `tune_readback`).

## 7. What is logged

Per take: `results.csv`, `results.md`, and the SQLite file `longtakes.db` (takes, per-second samples, drop events, Core counters, the
raw journal lines), filled while the next take is set up. New columns: `buffer_peak_pct` (queue bytes peak against its budget),
`buffer_setting`, `buffer_safety_stop`, `buffer_flush_discarded`, `media_class`, `variant`, `tune_readback`. Pi temperature per
second; the USB SSD has no temperature sensor Core can read (column empty).

## 8. Results so far (2026-11-07, run `run-20261107-ssd4`, 9 hours in, 30-minute round running)

**Final results: `tests-2026-11/findings-longtakes-ssd-2026-11-07.md`** (run finished 2026-11-08 02:58; the table below is the 9-hour snapshot).

| Mode | Best config | 5 min | 10 min | 20 min | 30 min |
| --- | --- | --- | --- | --- | --- |
| 4K SDR 12-bit | none | no clean fps, buffer full even at 25 | | | |
| 4K SDR 10-bit | lossless | 25 fps | failed (259 s) | | |
| 2K SDR 12-bit | lossless | 60 fps | 38 fps | 38 fps | failed at 38 and 37 fps after 27 min |
| 2K SDR 10-bit | uncompressed | 44 fps | 38 fps | 37 fps | not yet |
| 2K Clear HDR 16-bit | uncompressed | 27 fps | 26 fps | 26 fps | not yet |
| 2K Clear HDR 12-bit | uncompressed | 30 fps | 30 fps | 29 fps | not yet |
| 4K Clear HDR 12-bit | - | skipped (same bytes as 4K SDR 12-bit) | | | |

- **Storage tuning A/B changed nothing** (4K SDR 12-bit at 25 fps, 4K SDR 10-bit at 25 and 26 fps; `workers` 2/6, `queue` 24/48,
  `sync_ms` 500/2000, `kernel_tune`; 3 repeats each): all variants filled the buffer in 7-20 s at 25 fps, all stayed clean 120 s at
  26 fps. (measured)
- **The limit is per file as well as per MB/s:** 12.4 MB frames top out near 18 fps (220 MB/s), 3.1 MB frames near 38 fps (115 MB/s),
  both far below the 354 MB/s of large direct writes. Lossless wins because the files are smaller. Per-file overhead of exFAT is the
  probable cause. (probable)
- **30-minute failures at 38 and 37 fps both came at about 27 minutes** (1637 s, 1652 s): looks time-based (drive slowing after
  about 25 minutes, e.g. throttling) not a steady deficit; the SSD has no temperature Core can read. (unconfirmed)

## 8b. Log follow-up (stage F, added 2026-11-07, runs after the main run)

Log stores 16 -> 12 bit (Clear HDR 16-bit) or 12 -> 10 bit (12-bit modes): 17-25 % smaller files. The main run had pruned it. Core's code
maps Log only on unpacked 16-bit raw streams (Clear HDR); the User says it also applies to the SDR modes, so **Core decides per mode** and
a 4 s probe take keeps Core's own reason where it says no. Stage F tries Log wherever a smaller file can matter:

- **Parents:** every config of a mode that ended a take in buffer full (the storage limit), plus the winner. Each gets a Log twin (same switches,
  Log on). A twin's 5-minute walk starts at 1.4 x its parent's 5-minute fps; it gets the 10, 20, 30 min ladder only if it gained at 5 min, or if it
  is the winner's twin. A mode with no parent (4K Clear HDR 12-bit, ruled out earlier) tries lossless, lossless + Log, and Log.
- **4K first** (4K Clear HDR 12-bit, 4K SDR 10-bit, 4K SDR 12-bit), because the question is whether Log (alone or with lossless) can make 4K work on this
  SSD. A rough model fitted to the runs: frame write time = 19 ms + size / 345 MB/s, so 25 fps needs files of at most about 7 MB; 4K 12-bit with Log is
  10.4 MB (about 20 fps) and 4K SDR 10-bit lossless held 25 fps for 5 min but not 10, so lossless + Log is the plausible route. (probable, a model of two points)
- **CPU:** Core's CPU use (sum over threads, busiest thread) is logged per second and per take, so the cost of Log shows next to its gain.

## 9. Findings while building it (2026-11-07)

- **Core's own stop is a result.** On the SSD at 27 fps 4K SDR 12-bit three takes ended after 15-23 s with `peak_queue` 101-117
  frames and the queue at 90 % of its budget (`queue_bytes_peak=655257600 queue_budget=724811776`). Core stopped them (RAM-buffer safety
  stop at 90 %). The first runner version read that as someone stopping the take; the `buffer_safety_stop` flag falls as soon as the
  queue drains, so the runner now classifies it from the stats line (`buffer_full`). (measured)
- **4K SDR 12-bit at 27 fps needs 336 MB/s, 95 % of the 354 MB/s the drive sustains with large direct writes**; Apertar's writer
  (one file per frame, 4 workers) did not keep up. The file-per-frame overhead on exFAT is the probable reason. (probable)
- **`kernel_tune` on a USB drive** set `dirty_bytes` 256 MiB, `dirty_background_bytes` 128 MiB, writeback 150, scheduler `none` and
  `rq_affinity` 2; **`nr_requests` could not be set to 256** (it reads 30 under `none`). Restore gave back `mq-deadline`, 60. (measured)
- **`eject_media` powers a USB drive off.** The SSD vanished from the bus (no `sda`) and needed a replug; never use eject to
  re-apply tuning. `mount_media device_path=/dev/sda1` works once the drive is back. (measured)
- **The automounter mounts only drives labelled `CFE-RAW`, `NVME-RAW`, `RAW` or `USB-RAW`** (`/usr/local/bin/mount-raw.sh`). (measured)
- **Audio:** the USB PnP microphone (S16 mono only) rejected Core's s24 setting, which made `record_start` fail; the runner switches
  the format to Auto only when the device rejects it, and restores it at the end. (measured)
- **The earlier board** (different CM5 Lite) dropped within 2 s at 30 fps on the baseline; the **C0 board** ran the same baseline
  clean for 135 s until stopped. Not repeated here. (one take each)
