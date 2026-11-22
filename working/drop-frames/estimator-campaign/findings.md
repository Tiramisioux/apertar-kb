# Estimator campaign: findings

Plan: `plan.md`. Runner `working/tools/longtakes.py` (EST blocks), model `working/tools/estimate.py`. Records in the NVMe
campaign's run folder, `../nvme-campaign/run-20261110/`: `est/` (clip-split 7e6e2a3, 2026-11-11, 56 probes, stopped
twice by runner bugs) and `est-05fb8f1-a/` (this set). Labels: measured / derived / probable / unconfirmed.

## Set EST-05fb8f1-a, 2026-11-21 11:22-16:27 (merged build, single sensor)

Setup (measured): Core clip-split 05fb8f1 (dual-sensor branch merged), IMX585 on CAM0 only (`apertar-core-cam1`
stopped by Patrik, Dual sensor switch off), Corsair MP600 Mini A936B442006AC2 freshly formatted (988 GB free at the
start), USB mic (`hw:2,0`, USB PnP Sound Device) so the audio lever is real; the mic refused the configured audio
format and ran on auto. 167 takes, 1830 GB written, 0 voids, 0 audio faults, drive 25-49 C, critical_warning 0.

Done: P0, P1, P2, P1b, P3 (143 probes, 12 validation combinations). Not done: P4 (ladder) and P5 (closing repeat), see
"Stops" below.

### Capacity table (60-s probes, cold drive, reference levers) - measured, estimate = floor(0.97 x limit)

| what | estimate fps | limited by |
| --- | --- | --- |
| 4K HDR16 uncompressed | 27 | measured cell (28 out) |
| 4K HDR16 uncompressed + Log | 24 | back end |
| 4K HDR16 lossless | 14 | encoder |
| 4K HDR12 uncompressed / lossless / MLV | 25 / 28 / 24 | back end |
| 4K SDR12 uncompressed / lossless | 39 / 40 | back end / encoder |
| 4K SDR12 lossy 3:1 / 5:1 | 37 / 41 | encoder |
| 4K SDR10 uncompressed / lossless | 43 / 45 | back end / encoder |
| 2880x2160 crop SDR12 uncompressed / lossless | 51 / 56 | storage / encoder |
| 4K ProRes HQ / 422 / LT / Proxy | 27 / 40 / 43 / 45 | encoder |
| 4K ProRes HQ ARRI LogC4 | 41 | encoder |
| H.264 1080p / 2560x1440 | 60 / 45 | sensor / encoder |
| every 2K mode, cDNG/lossy/MLV/ProRes | 57-60 (HDR 29-30) | sensor, mostly |

Full table: `est-05fb8f1-a/estimate.md`, every lever state in `estimate-table.csv` (1408 rows).

Same probes against the clip-split set (`est/`, 7e6e2a3): 4K SDR12 unc 38 -> 39, lossless 41 -> 40, HDR16 unc 27 -> 27,
HDR16 lj 15 -> 14, ProRes HQ 29 -> 27, lossy 3:1 37 -> 37 (derived: within one fps; no sign the merge changed throughput).

Not to be used (probable artefacts, to check): 4K SDR10 MLV 10 fps and 4K SDR12 MLV 25 fps come from probes that stopped
on Core's safety stop within seconds (MLV fills the buffer fast; the capacity reading from delivered frames over a
stopped take is not a sustained rate). ProRes HQ ARRI LogC4 (41) above ProRes HQ standard (27): unconfirmed whether the
colour profile changes the encoder's load that much or one of the two probes is off.

### Levers (P2, 2^(5-1) on three anchors) - derived

- TDN is by far the largest lever: on the back-end anchor (HDR16 unc at 28) about +288 capture gaps per minute, twice
  over (be and be2 agree). On the encoder and storage anchors its effect is the largest too (0.25-0.32 on log capacity);
  the sign convention of the capacity effects (mean(same) - mean(diff)) is to be checked against the raw probes before
  it is read as a gain or a cost.
- Phase lock +24-31 gaps/min on the back end; preview aids -47 to -58 gaps/min (aids on = fewer gaps, unconfirmed why);
  audio and the WebUI client small (+4 to +39, at or below 3 SE).
- TDN x aids is the largest interaction everywhere (-39 to -62 on gaps, -0.06 on the encoder).

### Validation (P3) - measured

12 random combinations at the model's estimate p: clean at p in **6 of 12**, out at p+1 in 5 of 6. The pre-registered
success was >= 10 of 12 clean at p: **not met**. The estimate is too high for half the combinations (probable: the
cold 60-s probes, see the NVMe findings' warm-drive write pauses, and the lever interactions the fit carries only as
main effects). P3 rows: `est-05fb8f1-a/validation.jsonl`.

### P6, the warm-drive 15-min takes (2026-11-21 18:39-19:35; 4 of 12) - measured

| Take | Drive at the start | First event | Temp at the event | Written up to it | Rate | Outcome |
| --- | --- | --- | --- | --- | --- | --- |
| 4K HDR16 unc 27 | 39 C | 426 s | 68.8 C | 190 GB | 446 MB/s | 1 dropped at 432 s |
| 4K HDR16 unc 26 | 52 C | 714 s | 74.8 C | 307 GB | 430 MB/s | 1 dropped at 788 s |
| 4K SDR12 unc 39 | 58 C | 663 s | 77.8 C | 321 GB | 484 MB/s | buffer full at 750 s |
| 4K SDR12 unc 38 | 57 C | 231 s | 72.8 C | 108 GB | 468 MB/s | buffer full at 269 s |

- None of the four held 15 min. Neither did the estimate (27, 39) or one below it (26, 38).
- Two of the four failed **earlier than every take before**: 4K HDR16 27 at 190 GB and 69 C, and 4K SDR12 38 at 108 GB
  and 73 C. So the 265-375 GB band of the pre-analysis (2c-0) is not a floor. A pause can come after ~110 GB on a drive
  already at ~57 C from the take before. The 4K SDR12 38 take started 2 min after the 39 take ended.
- 4K SDR12 37 still holds the only clean 15 min (S4). 4K HDR16 has no clean 15-min fps yet: 25, 26 and 27 have all
  failed (10-13 min, and now 7 min).
- **Stopped 19:35-22:43 by a runner bug.** The fill gate before a take sized the next one (4K SDR12 lossless) smaller
  than the quiet gate did. Nothing was deleted, and the quiet gate waited for space ("only 415 GiB free, the take needs
  427"). Fixed in the runner (the fill gate now runs before the quiet gate waits). Stopped by hand, RESTORE OK, the Pi
  stayed on. The remaining 8 takes ran on 21-22 November (below).

### P6, the rest (2026-11-21 22:45 - 2026-11-22 14:27) and P6b, the Log takes (14:29-15:59) - measured

The 15-min warm takes at the estimate p and at p-1; a take that fails at p-1 is not retried lower. Reference levers,
split 5000, the drive warm from the take before (a 600-s cooldown when it passed 64 C).

| Take | fps | Drive start -> max | Written | Outcome |
| --- | --- | --- | --- | --- |
| 4K SDR12 lossless | 40 | 37 -> 67 C | 222 GB (247 MB/s) | **passed 15 min** |
| 4K SDR12 lossless | 39 | 37 -> 68 C | 239 GB | **passed 15 min** |
| 4K SDR12 lossy 3:1 | 37 | 49 -> 57 C | 108 GB (120 MB/s) | **passed 15 min** |
| 4K SDR12 lossy 3:1 | 36 | 49 -> 56 C | 105 GB | **passed 15 min** |
| 4K ProRes HQ | 27 | 40 -> 42 C | - | 1 dropped at 12 s (capture gap) |
| 4K ProRes HQ | 26 | 40 -> 46 C | - | **passed 15 min** |
| H.264 2560x1440 | 45 | 48 C | - | 7 dropped at 1.3 s (capture gap) |
| H.264 2560x1440 | 44 | 45 C | - | 2 dropped at 0.8 s (capture gap) |
| 4K HDR16 unc + Log (P6b) | 25 | 47 -> 69 C | 280 GB (311 MB/s) | **passed 15 min** |
| 4K HDR16 unc + Log (P6b) | 24 | 51 -> 66 C | 269 GB | **passed 15 min** |
| 4K HDR16 lossless + Log (P6b) | 14 | 53 -> 54 C | 100 GB | **passed 15 min** |
| 4K HDR16 lossless + Log (P6b) | 13 | 41 -> 52 C | 94 GB | **passed 15 min** |
| 4K ProRes HQ ARRI LogC4 (P6b) | 41 | 48 C | - | 4 dropped at 0.8 s (capture gap) |
| 4K ProRes HQ ARRI LogC4 (P6b) | 40 | 45 C | - | 3 dropped at 0.8 s (capture gap) |

- **Every take under ~320 MB/s passed 15 min** at its estimate or one below: lossless, lossy 3:1, ProRes HQ 26, and
  HDR16 + Log at 25. No warm-drive pause in any of them: the pauses (P6 first part, 2c-0) only came at 414-484 MB/s.
- **4K HDR16 + Log 25 held 15 min with 280 GB written**, where HDR16 without Log failed at 25-27 (414-446 MB/s). Log
  writes ~25 % less per second at the same fps (311 against 415 MB/s), so the drive stays under the pause rate. This
  is the first 4K HDR16 setting with a clean 15 min (measured, one take each at 25 and 24).
- **4K HDR16 lossless + Log holds 14** (the encoder's wall): the P3 reading of 30 was wrong, as section 4 of the
  pre-analysis said.
- **ProRes HQ: 26, not 27.** 27 dropped one frame at 12 s from a capture gap; 26 held 15 min.
- **H.264 2560x1440 and ProRes HQ LogC4 failed within the first second at every fps tried** (45/44 and 41/40), each
  with a single capture gap. The estimates (45, 41) were read from delivered frames over 60-s probes that dropped; the
  real limit is lower and not found. ProRes LogC4 does **not** beat standard HQ (the suspicion in the capacity table
  above): probable that it is near HQ's 26, unconfirmed until a take at <= 30 runs.
- 4K SDR12 lossless 39 ran twice: the first (23:08 on 21 November) was stopped at 396 s, clean so far; the second
  passed.

Stops on the way: 23:16 on 21 November the runner was stopped by a signal mid-take (clean at 396 s), and the restore's merge
check found the interrupted clip not intact. 12:46-12:50 on 22 November four takes were voided because the automatic storage pre-roll
was off on the new build (`storage_preroll_auto=False`); the runner now turns it on for the night and back at the end.
Patrik's own clip `cDNG_26-11-21_23371407_C0005_cam0` was kept with `--preserve`. RESTORE OK at 15:59, Pi powered off.

### Stops and fixes

- 11:18 the runner waited on its own folder: the mic's audio format was refused after Core had made the clip folder, the
  retry recorded into the next one; fixed (6acca51, own_clips.txt counts as known).
- 16:26 P4 ended the run: the runner's quiet gate called the ladder P4 had turned on a needs-a-human condition; the
  restore read back lossy_dng_ratio 5to1 (Core refuses the ratio while the ladder is on, and the switch back to cDNG
  reloads the shared DNG profile's ratio), so the Pi stayed on. 17:47 P4 again: the ladder takes left Log on auto, which
  applies Log in HDR16 (setup_mismatch). All fixed in 3d32d3e; restore by hand read back OK at 17:48.
- Earlier the same day: the first start (00:54) ran two probes without a mic (none attached) and the Pi went down at
  about 01:00; those probes are not in this set.

### Next

- The measured limits per cell, longest clean duration first: `../measured-limits.md` (`scripts/measured_limits.py`).
  These, not the estimate, go into Core's limits table.
- H.264 2560x1440 and ProRes HQ LogC4: find the real limit (start-of-take capture gaps at 40-45; try 30 and 26).
- 30-min takes for the rows that passed 15 min (SDR12 lossless 40, lossy 3:1 37, ProRes HQ 26, HDR16 + Log 25,
  HDR16 lossless + Log 14).
- P4 (Dynamic resolution) and P5 (the closing repeat of P0) as takes `P4r3-*`.
- The validation miss: compare P3's failures with their P1/P2 neighbours; probably the estimate needs the warm-drive
  pause and the TDN interactions before it goes in the UI.
