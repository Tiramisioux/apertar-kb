# SSD campaign on the Samsung T7 (2026-11-09): stage record

Plan: `../storage-slowdown-plan.md` section 7 (stages S0-S7; S4-S7 run unattended by `working/tools/longtakes.py`).
Not the NVMe 4K plan (`../nvme-campaign/plan.md`, the Corsair cards), which has its own S0-S6.

Drive: Samsung PSSD T7 500 GB, serial S5TGNJ0N500019B, exFAT `USB-RAW`, 128 KiB clusters, on the Pi's USB 3 port (5000M).
Core: `clip-split` `c9e7707` (cinemate-port `01f170c` plus the Standard clip-name preset; the campaign binary, User: "do what is
best"); UI `3ebbd23`. Choices (User, 2026-11-09): MLV control yes, the camera-free probes yes, the split test yes, the lead rolls
the dice; modes `2kSDR12,2kHDR16`, budget 3,500 GB (the plan's figures for those two modes); `--fix-budget` not used (the NVMe
build list struck it: the buffer stays at Core's real-use defaults 0.6 / 512).

## S0 drive facts (measured 2026-11-09 01:25)

- Driver **uas** (command queuing), not BOT: settles the plan's section 8 item 8. Core still names the class `usb-storage`.
- **Trim unsupported** through the T7's bridge: `discard_max_bytes=0`, and Core's mount trim says `result=unsupported`. M4 (trim
  between takes) cannot be tested on this drive; S3's trimmed-vs-two-passes variant is dropped, and the S0 delete-then-trim check is moot.
- Core's direct-write speed test: **167 MB/s** (fio, 1,024 MB, QD32, direct).
- Scheduler mq-deadline, nr_requests 60, max_sectors_kb 512, write cache write-back; power clean (throttled 0x0, 5.01 V).
- Root lines not run (no sudoers snippet): `smartctl -a -d sat /dev/sda` (temperature, wear), `fstrim` (moot).
- Raw: `S0-storage-facts-2026-11-09.txt`.

## Smoke tests (2026-11-09)

- Smoke 1 (`--stages m --meter-seconds 20 --no-gate --modes 2kSDR12`, 01:25-01:28): pass. 2kSDR12 uncompressed at 60 fps: capacity
  40.2 fps (fit), drain 104 MB/s; lossless: 59.8 fps, 93 MB/s; 0 dropped; settings restored; `DONE` (all stages done). A WebUI client
  was connected at its start (User closed it after).
- Smoke 2 (`--stages msLMkS --modes 2kSDR12,2kHDR16 --long-seconds 60 --budget-gb 400`), started 01:28: every stage once.

## Night 1 (2026-11-09, unsupervised): `~/ssd-campaign/night1.sh` on the Pi

After smoke 2 ends with "all stages done": S2 (`exfat_write_probe.py --size-mb 12.4 --files 300`: default, `--workers 1`, `--prealloc`,
`--fsync none`, `--chunk-kb 0`, `--chunk-kb 0 --prealloc --direct`, `--subdir 5000`; ~26 GB), S3 (`--size-mb 1.3 --fps 38 --seconds 1800
--budget-mb 800`, flat then `--subdir 5000`; ~180 GB; the trimmed-vs-passes variant dropped: no trim), then the ladder
`longtakes.py --out ~/longtakes/ladder-20261109 --stages msLMkS --modes 2kSDR12,2kHDR16 --budget-gb 3500 --disk-mbps 167`.
Log: `~/ssd-campaign/night1.log`; probe output `~/ssd-campaign/S2|S3/`; ladder `~/longtakes/ladder-20261109/` (`results.md`,
`capacity.md`, `runner.log`, `DONE`). **No reboot resume**: the `@reboot` crontab line of plan 7.1 was not installed (the session's
safety check refused it), so a reboot ends the night; rerunning the ladder line with the same `--out` resumes it.
- Smoke 2 result (01:28-01:41): meter, split and long stages pass (2kSDR12 unc meter 40.3 fps / 97.6 MB/s, lossless 60.0 fps clean;
  2kHDR16 unc 23.9 fps / 100.4 MB/s, below the 25 fps floor so metered only, lossless 30.0 fps clean at the mode max; split 1 x 60 s
  and 3 x 20 s at 38 fps clean; long 60 s at 36 fps clean), then **stopped at the MLV stage: `setup_mismatch: res=3840x2160`**. Cause:
  `apply_cfg` read the state before `set_record_format`; Core loads the MLV profile (4K) on the switch, so the resolution check used
  the stale 2K value and skipped `set_resolution`. Fixed (the state is read again after a format switch).
- Smoke 3 (`--stages MkS --modes 2kSDR12 --long-seconds 60 --split-fps 35 --long-fps 33`, 01:42-01:50): pass. MLV 60 s at 35 fps
  clean; `frames_per_folder` 5000 and 0 clean (2,100 files each), restored to 0 and merge on; soak 2 x 60 s clean.
- Night 1 ran as `night1b.sh` from 01:50 (S2, S3, the ladder; the smoke-2 check replaced by smoke 3's). Power-off watcher
  `poweroff-after-night1b.sh <pid>` (follows the chain's PID; a first version matched by path and would have fired at once: caught and
  killed within a minute).

## Night 1 results (2026-11-09 01:50-06:18; ended "all stages done", Pi powered off by the watcher at 06:18)

Raw: `night1-raw/` (probe outputs, the ladder's `results.md`, `capacity.md`, `runner.log`, per-second `samples/`). Writes: S2 ~26 GB,
S3 ~180 GB, the ladder ~1.07 TB (device counters; derived).

**1. Inside a long take the slowdown is the exFAT folder, not the SSD (probable, strong).**
- S3, camera-free, 2K-size files (1.3 MB) paced at 38 files/s for 30 min: one folder, per-file time p50 5.6 ms at 11,400 files ->
  20.4 ms at 57,000 (~0.32 us per file already in the folder: the directory probe's 317 ns slope, measured on the NVMe); a new folder
  every 5,000 files: 1.4-3.0 ms all the way. The device's own write time stayed ~2.4 ms in both (measured).
- Camera, 2kSDR12 uncompressed at 32 fps (99.5 MB/s), drive at 100 MB/s throughout every 30-min take: Core CPU in the flat takes
  climbs 52-57 % -> 125-131 % over 30 min, and two of the three flat 30-min takes (the soaks) hit the buffer safety stop at 29.5 and
  29.1 min (buffer 87-88 % in the last 5-min window); the third (`knob0`) passed with the buffer at 17 % at most. Split every 5,000
  frames (`knob5000`): Core CPU 50-54 % all through, clean, buffer at most 11 % after the first minute. MLV (one file): 38 %, clean
  (measured; n = 1 split, 3 flat).
- So **splitting long takes (`frames_per_folder`, e.g. 5000) removes the in-take slowdown on the SSD**; at this drive's limit it is
  the difference between a clean 30-min take and a stop near the end (probable: one split take; the probe and the CPU trend agree).

**2. Between takes the drive itself slows after heavy writing (probable).** The T7 cannot be trimmed through its bridge (S0). Right
after S2+S3 wrote ~210 GB, the first five camera takes (03:00-03:27) ran at 84-98 MB/s and filled the buffer in 1-5 min; from 03:28
the same settings ran at a steady 100 MB/s for 2.5 h. The meter also read lower than the smoke tests before the probes (2kSDR12 unc
34.5 vs 40.3 fps; 2kHDR16 unc 18.1 vs 23.9). Mechanism unconfirmed (the drive's cache or garbage collection catching up while idle).

**3. Capacity on this T7 (meter, after the probes; measured).** 2kSDR12: uncompressed ~32 fps sustained (34.5 metered), lossless
53.6 fps metered (clean 90 s at 60). 2kHDR16: uncompressed 18.1 fps (below the 25 fps floor: no long takes), lossless 28.5 fps
metered (clean 90 s at 30). Sustained drive rate during takes ~100 MB/s against 167 MB/s in Core's direct fio test.

**4. Write pattern (S2, 300 x 12.4 MB each, n = 1; weak).** Throughput 116-139 MB/s across the variants: `--fsync none` 139,
`--chunk-kb 0` 131, `--prealloc` 131, `--subdir 5000` 129, default and `--workers 1` 122, `--direct` 116. One writer had the
lowest per-file latency (p50 96 ms against 351) at the same throughput. No variant changes the ceiling by more than ~14 %.

**What to use (probable):** for long takes on the SSD set `frames_per_folder` (5000) with the merge worker on; prefer lossless
compression (more headroom: 2kSDR12 54 fps, 2kHDR16 28.5 fps); keep 2kSDR12 uncompressed at or below ~30 fps on this T7; give the
drive idle time after heavy writing before a long take (no trim).

Not yet: a second split 30-min take (n = 1), HDR16 lossless long takes (the runner meters uncompressed for its floor), the S6 Core
patches, the NVMe card.

## Night 2 (2026-11-09 20:29 - 2026-11-10 01:15, unsupervised)

- **Decision (User, 2026-11-09):** `frames_per_folder` 5000 is the default on the camera. Night 2 leaves it at 5000 and turns
  the merge back on. No Core code default changed.
- **Optional items left out (User):** S6 tune-key patches, the fan A/B and the 1 MB-cluster format.
- Chain: [night2/night2.sh](night2/night2.sh). Run 1 is the split layout at 2kSDR12 unc 32 fps (split30, split10×3, long30,
  soak×2). Run 2 is long 2kSDR12 lossless at 48 fps. Run 3 is long 2kHDR16 lossless at 27 fps. 10 min idle between runs.
- Power-off: [night2/poweroff-after-night2.sh](night2/poweroff-after-night2.sh) `<pid>` follows the chain's PID, waits until
  nothing is recording, then calls Core `power_off_system`.
- Needs first: `longtakes.py` cf0b37e copied to `~/longtakes/bin`, camera idle, WebUI closed, T7 mounted.

**Started 2026-11-09 20:29** (night2.sh pid 6487). Added at 2026-11-09 evening (User): a **merge test** after the chain,
[night2/merge-test-after-night2.sh](night2/merge-test-after-night2.sh) (pid 54605). It waits for night 2, idles 10 min, then
records one 30-min split take at 2kSDR12 unc 25 fps (45,000 frames, 9 parts), turns the merge on, logs the `clip_merge_*`
fields every 10 s (`~/ssd-campaign/merge-test-samples.txt`) and Core's merge lines, deletes that clip through
`/api/media/delete`, and restores the camera settings. The power-off watcher follows the merge test now (pid 54783), not
night2.sh. The merge itself was never timed beyond 4,503 frames before this (0.72 ms per file).

## Night 2 results (ended "all stages done" 00:25; merge test 00:25-01:12; Pi powered off by the watcher at 01:15)

Raw: [night2-raw/](night2-raw/) (`results.md`/`.csv`/`runner.log` per run, the split run's per-take journals, `night2.log`,
`merge-test.log`, `merge-test-samples.txt`). Core b755383 (Pi), every take split at 5,000 frames (`.parts` in each clip).

| run | takes | clean | dropped | Core CPU | RAM buffer peak (after 1 min) | write queue peak |
| --- | --- | --- | --- | --- | --- | --- |
| 2kSDR12 unc 32 fps (split30, split10×3, long30, soak×2) | 7 (4 × 30 min, 3 × 10 min) | 5 | 1 frame (split30), 3 frames (soak 1) | 51-58 %, flat over 30 min | 2.8-7.0 % | 22-54 frames |
| 2kSDR12 lossless JPEG 48 fps, 30 min | 1 | 1 | 0 | n/a | n/a | 28 |
| 2kHDR16 lossless JPEG 27 fps, 30 min | 1 | 1 | 0 | n/a | n/a | 5 |

**1. The split removes the in-take slowdown (confirmed, n = 4 × 30 min at the drive's limit).** Core CPU 51-58 % from the first
to the last 5 minutes of every 30-min take; night 1's flat takes climbed to 125-131 % and two hit the safety stop. The RAM buffer
never went above 7 %. `frames_per_folder` 5000 stays the default.

**2. The four dropped frames are not storage (measured; cause unconfirmed).** In both takes Core's write queue peaked at 54 frames
or fewer of a ~800-frame budget, and `dropped_queue_full` = 0.
- split30 (20:29): Core wrote every frame it got (enqueued = written = 57,605, no drop counter), but one frame number is
  missing from the sequence: the frame never reached the recorder (upstream of the queue: sensor, CFE or ISP side).
- soak 1 (22:02): `dropped_copy_slot` = 3 (`drop[copy-slot]: frame=40007 held=6/6`): all six copy slots were busy when the frame
  arrived, so it was dropped before the queue.
- Rate: 4 frames in ~4 h at 32 fps (~460,000 frames). Both kinds are a separate problem from the drive; next step is to read
  the per-second samples around 40,007 and look for the same kinds at 25 fps.

**3. Lossless JPEG is clean on this drive at 2kSDR12 48 fps and 2kHDR16 27 fps for 30 min (measured, n = 1 each).**

**4. The merge of a 30-min clip (measured, n = 1).** 2kSDR12 unc 25 fps, 45,001 frames in 10 parts (the last holds 1 frame),
0 dropped while recording.
- Merge time **342 s (5.7 min)**, 7.6 ms per file on average; the model (0.1 ms + 0.32 µs per file already in the main folder)
  predicted about 5½ min.
- The per-file time grows straight with the folder size: 0.8 ms per file in the first 5,000, 7.6 ms average by the end
  (Core's journal, `merge-test.log`).
- **The time left shown in the UI was 4-6 % low all the way through** (316 s at 10 s in, actual 333 s; 30 s at 311 s, actual 32 s).
  No change to the constants.
- After the merge: no `part_*` folders, no `.parts`; the clip was deleted through the media route (45,003 files), the settings
  were restored (4K HDR16, 25 fps), `frames_per_folder` 5000, merge on.

## Night 2: the four dropped frames, examined (2026-11-10)

**Soak 1 (22:02), 3 frames: copy-slot drops at the part_008 boundary (probable).** All three fell in one second, t = 1250.8 s
(frames 40007-40025); frame 40000 is the 5000-frame boundary. `ensurePartFolder` runs `mkdir` on the copy worker's own thread
(CameraController.cpp:4966-4981, Pi b755383); the camera keeps 8 raw buffers and Core may hold 6, so a copy-worker stall of
>= 6 periods (190 ms at 32 fps) refuses frames (`enqueueCopy`, 5079). In that second Core's CPU was 35 % against 51 % the rest of
the take (blocked, not busy), dirty 2 MB, writeback 1 MB. The T7 is UAS with queue depth 30: a directory-metadata read behind
30 queued writes can wait hundreds of ms. ~40 other boundaries that night passed (n = 1 event; the timing to the frame is the
evidence). Fix (not built): create the part folder from a writer thread (EEXIST tolerated) or pre-create part k+1 when part k
starts, so nothing on the copy path touches the file system.

**Split30 (20:29), 1 frame: a frame-number jump, not a lost frame (probable).** No counter moved, no `drop[...]` line, the state's
dropped count stayed 0 all take. Frame numbers are `max(count, round((ts - ts0) x fps))` (4686-4694); the audio-sync line
(output_samples = 57,606 periods for 57,605 frames) shows the time index ended exactly one ahead of the count. The cadence
detector (10015-10062, dt > 1.5 periods, resets only at start/stop) checks every frame that reaches the numbering point, so a
frame lost before Core would have left a 2-period gap and a log line. Same signature in two 2kHDR12 25-fps takes on 11-07
(45,007 and 29,999 files). Other long takes end at 0, -1 or -2 (sensor slightly fast, numbering by count). So one sensor
timestamp arrived >= half a period late, or the take's first intervals set the time grid late; which, the logs cannot say.
Proposed (not built): log when the time index jumps ahead of the count (dt, ts, index); consider letting the time index win
only when the cadence detector saw a gap. The runner counts a numbering gap as a drop (`missing`).

## Frame budget vs exFAT folder size (formula; T7 measured, NVMe prognosis)

- Budget per frame T = 1000/fps ms. Directory walk per create W(n) = 0.32 us x n (n files already in the folder; CPU under the
  exFAT lock; measured on the NVMe probe and the T7's S3, same slope). Share of the budget s = W/T = 0.32 us x fps x n; in a
  flat take n = fps x t, so s(t) = 0.32 us x fps^2 x t. The campaign's rule: flat holds below s = 0.6. Hence a flat folder
  lasts t* = 0.6 / (0.32 us x fps^2) = 1.9e6 / fps^2 s: 50 min at 25 fps, 31 min at 32 fps, 14 min at 48 fps, 8.8 min at 60 fps,
  3.2 min at 100 fps. Split at 5000 caps s at 1.6 ms x fps (5 % at 32 fps, 16 % at 100 fps).
- T7 (measured, 2026-11-07 run + nights 1-2): flat 30 min passes at 2kSDR10 33 fps (s = 0.63 at the end), 2kSDR12 lossless
  30 fps, 2kHDR12 28 fps, 2kHDR16 26 fps (bandwidth edge, ~110 MB/s), HDR16+Log 28 fps; 2kSDR12 unc 32 fps flat fails at
  29 min (2 of 3), split passes (4 of 4); the Clear HDR modes fail earlier than the walk predicts (29-30 fps at 19-24 min,
  s = 0.35-0.4; the HDR copy path costs more CPU, cause of the lower threshold unconfirmed). Ceilings: ~105 MB/s, ~40 files/s.
- NVMe (prognosis): 415 MB/s Core-pattern sustained, small per-file cost, so the walk rule alone applies for 2K; 4K HDR16
  uncompressed >= 25 fps (422+ MB/s) is at the drive's limit regardless of folders.
