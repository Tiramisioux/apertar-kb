# SSD campaign on the merged build (Core clip-split 05fb8f1): plan, 2026-11-21

Status: **proposal**, not built, not started. Written after the NVMe pre-analysis
(`../estimator-campaign/pre-analysis.md`), whose T7 column is derived for every 4K row. The 2K T7 results are from the
older build (SSD nights 1-2, `README.md`).

## Question

Which modes hold **30 min drop-free on the Samsung T7** (500 GB, S5TGNJ0N500019B) on today's build, at the fps the
pre-analysis recipes (5a) give for the T7? And do the old 2K results still hold on the merged build?

## Conditions (as the NVMe estimator day)

- IMX585 only: Patrik runs `sudo systemctl stop apertar-core-cam1` after boot; Dual sensor off.
- USB mic on `hw:2,0`.
- Split at 5000 frames, merge off during the night and back on at the end.
- Levers at the reference (TDN off, lock off, WebUI on, audio on, aids on).
- The T7 on `/media/RAW`, checked by serial before any write. The NVMe must not be the recording card that night.
- No trim through the T7's bridge (S0). The runner's fill gate deletes its own clips through the media route when it
  needs space: 500 GB holds two 30-min takes at ~100 MB/s.

## Blocks

| Block | What | Takes | Time |
| --- | --- | --- | --- |
| T1 | 60-s probes at the recipe fps p and at p+1, for each of the 12 rows below: is the derived fps right? | 24 | ~1 h |
| T2 | one **30-min take** per row at p (stops at the first drop). A row that drops gets one more at p-2 at the end, if time remains | 12 (+ retries) | ~6.6 h |
| | restore, read back, power off | | ~5 min |

**About 8 h in all.** Started at 22:30, it ends around 06:30.

| Row | Format | T7 fps p | Flow at p | Why |
| --- | --- | --- | --- | --- |
| 1 | 4K SDR12 lossy 5:1 | 41 | ~85 MB/s | the best 4K on the T7 (derived) |
| 2 | 4K SDR12 lossy 3:1 | 28 | ~95 MB/s | derived |
| 3 | 4K SDR12 lossless | 18 | ~90 MB/s | derived |
| 4 | 4K HDR16 lossless | 9 | ~105 MB/s | the only 4K HDR16 on the T7 (derived) |
| 5 | 4K SDR10 lossy 5:1 | 43 | ~85 MB/s | derived |
| 6 | 2880x2160 crop SDR12 lossless | 24 | ~100 MB/s | derived |
| 7 | 4K ProRes HQ | 22 | ~100 MB/s | 4.5 MB/frame (measured on NVMe), so the T7 sets ~22 |
| 8 | 4K ProRes 422 | 40 | ~72 MB/s | the encoder's limit; the T7 should not matter |
| 9 | H.264 2560x1440 | 45 | < 1 MB/s | the encoder's limit (control: storage plays no part) |
| 10 | 2K HDR16 lossless | 27 | ~70 MB/s | regression: passed 30 min on the older build |
| 11 | 2K SDR12 lossless | 48 | ~95 MB/s | regression: passed 30 min on the older build |
| 12 | 2K SDR12 uncompressed | 32 | ~100 MB/s | regression: passed 30 min 4 of 4 on the older build (split) |

The T2 order is rows 1-12. The 4K questions come first, so a night cut short still answers them.

## What the runner needs first (build, desk + one smoke take)

1. **Card facts for a USB drive.** `card_facts()` reads only `/sys/class/nvme/nvme0`. For the T7 it must read
   `/sys/block/sdX/device/model`, and the serial from `udevadm info --query=property` (`ID_SERIAL_SHORT`, no sudo).
   Then `--expect-serial S5TGNJ0N500019B` works as it does for the NVMe.
2. **A `T7` block** in `--est-blocks` (T1 and T2 above), reusing `est_cell` with its own records (`t7.jsonl`). It
   would run under its own set name, `--night EST-05fb8f1-t7`.
3. **No drive temperature on the T7** without `smartctl -d sat` (sudo). The samples' `nvme_c` stays empty; that is
   accepted.
4. The settings dry run (`est_settings_check.py`) once with the T7 mounted, as before the NVMe day.

## What Patrik does

- After the NVMe night's power-off: attach the T7 so it mounts on `/media/RAW` (offload or move anything he wants to
  keep; the runner only touches its own folders).
- Boot, stop `apertar-core-cam1`, attach the mic, then say GO in the session.

## Results go to

- `../nvme-campaign/run-20261110/est-05fb8f1-t7/`: the same run folder and ledger.
- A T7 section in the pre-analysis's tables (the T7 column becomes measured where T2 passed).
