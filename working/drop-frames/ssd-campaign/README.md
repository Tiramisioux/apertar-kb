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
