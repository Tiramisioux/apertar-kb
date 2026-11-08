# Long-take campaign on the USB SSD: what the system can do (2026-11-07/08)

Rig: CM5 Lite (C0, `c041a0`), Core `f4a1393`, FE config queue depth 4, media tune file (workers 4, queue 12, raw buffers 8),
Samsung PSSD T7 (466 GB, exFAT, USB 3.0 5 Gbps, 354 MB/s direct write), audio on in every take.
Run: 189 takes, 20.1 h recorded, 5.9 TB written, 2026-11-07 03:29 to 2026-11-08 02:58. No throttling, Pi at most 62 C.
Data: `longtakes-ssd-2026-11-07/longtakes.db` (every take, per-second samples, Core counters, journal lines), workbook
`../longtakes-ssd-results-2026-11-07.xlsx`, builder `working/tools/make_results_xlsx.py`.

## Highest clean fps (no drop, no buffer full)

| Mode | Variant | File MB | 5 min | 10 min | 20 min | 30 min |
| --- | --- | --- | --- | --- | --- | --- |
| 2K SDR 10-bit | uncompressed | 2.6 | 44 | 38 | 37 | **33** |
| 2K SDR 12-bit | lossless | 1.3 | 60 | 38 | 38 | **30** |
| 2K SDR 12-bit | uncompressed | 3.1 | 35 | - | - | - (only the 5-min round) |
| 2K Clear HDR 16-bit | uncompressed + Log | 3.1 | 30 | 30 | 30 | **28** |
| 2K Clear HDR 16-bit | uncompressed | 4.2 | 27 | 26 | 26 | **26** |
| 2K Clear HDR 12-bit | uncompressed (Log the same) | 3.1 | 30 | 30 | 29 | **28** |
| 4K SDR 10-bit | lossless | 4.3 | 25 (1 of 3) | - | - | - |
| 4K SDR 10/12-bit, 4K Clear HDR 12-bit | all other variants | 5.8-12.6 | - | - | - | - |

4K: only 4K SDR 10-bit lossless reached 25 fps for 5 min, once; it also stopped after 4.3 min and after 12 s (26 fps held 2 min in
all 24 A/B takes). Every other 4K variant stopped within 8-20 s at 25 fps. 4K Clear HDR 16-bit was not run (16.6 MB files).

## Minutes above the 30-minute limit (until buffer full)

- 2K SDR 10-bit: 34 fps 24 min, 38 fps 16 min, 39 fps 7 min, 40-44 fps 0.3-2 min.
- 2K SDR 12-bit lossless: 31 fps 28 min, 36-38 fps 21-28 min, 45-60 fps 3-10 min (scattered).
- 2K Clear HDR 16-bit + Log: 29 fps 19.5 min, 30 fps 19 min. Without Log, 27 fps: 1 min (it held 5 min once).
- 2K Clear HDR 12-bit: 29 fps 23.5 min (with Log 27.8), 30 fps 19-20 min.

## Levers

- **2K binned is the only way to 30 min at 25 fps or more on this SSD.** (measured)
- **Log pays off in Clear HDR 16-bit only:** files 25% smaller (4.2 -> 3.1 MB), +2 fps at 30 min, +4 fps at 10 and 20 min. In Clear HDR
  12-bit, Log leaves the files the same size and the result the same. In SDR, Core does not apply it ("cannot be mapped on the copy
  worker, recording linear"). At 4K, it made things worse: lossless + Log made 8.5 MB files against 6.1 MB for lossless alone. (measured)
- **Lossless** (2K SDR 12-bit) cuts files by 58% (3.1 -> 1.3 MB) and gives the best short takes (60 fps for 5 min, 38 fps for 20 min).
  For 30 min it held 30 fps, less than 2K SDR 10-bit uncompressed (33). At 4K it is the only variant that reached 25 fps. (measured)
- **No effect:** the storage-tuning A/B (workers 2/6, queue 24/48, sync 500/2000 ms, the CineMate kernel dirty tuning; 24 paired takes).
  Not tested, ruled out in theory because every limit was the drive: preview TDN, phase lock, WebUI. Trim off: 2 takes, no visible
  effect. (measured / theory)

## Limiter

- **Every stop was buffer full; no take stopped on a dropped frame.** Two passes are one file short (of 45,000 and 30,000) with no Core
  drop counter moving. (measured)
- **The SSD's limit is per frame, not per MB/s.** At the 30-minute limits the drive carried only 40-110 MB/s (2K SDR 12-bit lossless at
  30 fps is ~40 MB/s), against 354 MB/s for large direct writes. A fixed cost per file (one DNG per frame on exFAT over USB) is the
  probable cause. (probable)
- **Long takes slow down:** the takes that failed the 30-minute round at a given fps had passed 20 min at that fps, and failed after 19-28
  min. That looks like the drive slowing over time (heat or cache); the T7 has no readable temperature. (unconfirmed)
- **4K lossless may be encoder-limited, not drive-limited:** 6.1 MB files should be writable at ~27 fps by the model, yet the drive
  wrote only 11-17 fps; Core used about one core on average, up to 2.8 cores at peak, busiest thread `CameraManager`. The check is step 0b of
  `../nvme-4k-recipe-plan.md`. (unconfirmed)

## Recipe for this SSD

- 30-min takes: 2K SDR 10-bit uncompressed up to 33 fps; 2K Clear HDR with Log (16-bit) or 12-bit up to 28 fps.
- Short high-fps takes: 2K SDR 12-bit lossless (60 fps for 5 min, 38 fps for 20 min).
- 4K: not on this SSD; use the NVMe.
