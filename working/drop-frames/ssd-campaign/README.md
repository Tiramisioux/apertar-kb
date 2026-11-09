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

## Night 2 (planned 2026-11-09, waiting for the Pi)

- **Decision (User, 2026-11-09):** `frames_per_folder` 5000 is the default on the camera. Night 2 leaves it at 5000 and turns
  the merge back on. No Core code default changed.
- **Optional items left out (User):** S6 tune-key patches, the fan A/B and the 1 MB-cluster format.
- Chain: [night2/night2.sh](night2/night2.sh). Run 1 is the split layout at 2kSDR12 unc 32 fps (split30, split10×3, long30,
  soak×2). Run 2 is long 2kSDR12 lossless at 48 fps. Run 3 is long 2kHDR16 lossless at 27 fps. 10 min idle between runs.
- Power-off: [night2/poweroff-after-night2.sh](night2/poweroff-after-night2.sh) `<pid>` follows the chain's PID, waits until
  nothing is recording, then calls Core `power_off_system`.
- Needs first: `longtakes.py` cf0b37e copied to `~/longtakes/bin`, camera idle, WebUI closed, T7 mounted.
