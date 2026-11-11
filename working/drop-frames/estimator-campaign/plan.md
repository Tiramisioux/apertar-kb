# Estimator campaign: sustained fps for every format, compression and lever (plan, 2026-11-11)

Written 2026-11-11 02:40 during the NVMe campaign's S2-S6 night. Status: **plan, not started, not built**. Needs Patrik's GO,
a new write cap (§9) and the runner work of §8 first. Rig: Pi 5 (CM5 Lite, Waveshare CM5-IO-BASE-A), IMX585 on CAM0, **no
IMX283** (it capped the IMX585's fps, findings 2026-11-10), Corsair MP600 Mini A936B442006AC2 exFAT, Core `clip-split`
`7e6e2a3`, UI `25eeb47`.

## 1. What the run is for

Three products, from one day of takes:

1. **The estimate table:** the sustained fps for each resolution mode x recording format x compression x lever state on
   this build, with the stage that limits it ("limited by: storage / encoder / back end / Log"). It is what the UI and the
   WebUI would show beside each resolution mode, and what an fps cap switch would hold to.
2. **Ladder thresholds:** the Mode Ladder already has rungs with their own resolution, bit depth, compression (none,
   lossless_jpeg, lossy_3to1, lossy_5to1), Log and an fps `threshold` (`src/camera/ModeLadder.hpp:17`, `set_mode_ladder`).
   A "smart ladder" fills the thresholds from product 1 so an fps change lands on a rung that holds. This run checks that
   with hand-set thresholds (§5 P4); no Core change.
3. **The build self-test:** the smallest set of short probes that, run on a new build, reproduces product 1 for every
   combination within a stated error. The run measures everything, then tests how well a small subset predicts the rest
   (§6), so the self-test's size and error come from data, not a guess.

Not in this run: other drives (the T7 SSD day gives the storage term for USB; §10), two sensors (cam1 is out), Pi 4/3/Zero.

## 2. The model the data has to fit

Sustained fps = min over the stages, each a per-frame time budget (derived from both campaigns; every failure so far was
one stage at its limit):

| Stage | Limit | Depends on | Source of the number |
| --- | --- | --- | --- |
| Sensor mode | `fps_max` | resolution, bit depth, HDR | Core (known) |
| ISP back end | capture gaps above an onset fps | pixels, HDR, **TDN**, memory traffic (Log, a second camera) | this run, P2 gap probes |
| Raw copy / Log worker | per-frame copy + LUT time | bytes, Log on/off (Clear HDR 16-bit only) | this run |
| Encoder | frames per second the workers finish | format, compression, ratio, pixels, picture content (ISO) | this run, P1 capacity probes |
| Storage, bytes | sustained MB/s of the drive | the drive; card fill | NVMe campaign S1/S5/S6 (596-627 MB/s slowest 10 s, measured) |
| Storage, per file | t0 + c x files in the folder (c = 63.3 ns/entry, measured) | the drive, exFAT, frames_per_folder | NVMe campaign |
| RAM buffer | how long a rate above the limit lasts | RAM, frame size | computed (budget 1,592 MiB on this board) |

Fitting assumption to test: each stage's per-frame time is `a + b x pixels` (or `x bytes`), and a lever adds a fixed time
to the stage it loads. If that holds, two sizes per stage are enough and everything else is arithmetic.

## 3. Factors and levels

**Modes (16:9, Patrik 2026-11-10):** 4K SDR12, 4K SDR10, 4K HDR12, 4K HDR16, 2K SDR12 (binned 1920x1080), 2K HDR16, plus
**one crop**, 2880x2160 SDR12, only as the pixel-scaling check (not a product mode).

**Formats and compressions (`include/apertar/core/Types.hpp:46-75`):**

| Family | Levels | Notes |
| --- | --- | --- |
| cDNG | uncompressed, lossless JPEG | |
| cDNG + Log | uncompressed, lossless JPEG | **Clear HDR 16-bit only**; SDR records linear with `cdng_log_applied=false` (R2 §2c) |
| Lossy DNG | 3:1, 5:1 | no Clear HDR (`ModeLadder.hpp` comment) |
| MLV | one file per take | no per-file storage cost |
| ProRes | HQ, Standard, LT, Proxy; colour profile Standard vs ARRI LogC4 (one cell) | ISP RGB48 at the active size |
| H.264 | output 1920x1080 and 3840x2160 | capture is 4K only, Core caps at 30; x264 had headroom (hardware-log 2026-10-28, measured) |

**Levers (on/off):** TDN (`set_preview_tdn`), phase lock (`set_fps_phase_lock`; measured cost before the `{d, d+1}`
fix `69a700e`, never since), WebUI client (the runner's stand-in), audio (`set_record_audio_enabled`), preview aids
(`set_focus_peaking_enabled` + `set_zebra_enabled` together). Held constant: trim on, merge off during probes,
frames_per_folder 5000, speed ramp off, ladder off except in P4.

Full factorial = 7 modes x ~18 format levels x 32 lever states: not runnable. The design below measures the stages, not
the combinations, then checks the combinations on a random sample.

## 4. Measurements

- **Capacity probe (60 s):** a take at the mode's top fps (or 60 if the format allows); the runner's
  `capacity_from_samples` reads the writers' capacity from the buffer's slope (`capacity_how = fit`; `at least` when the
  buffer never filled = the stage is faster than the mode). One probe gives the limit of whichever stage is slowest.
- **Gap probe (60 s):** for the back end, the measure is capture gaps (`dropped_gap_estimate`, index jumps) at a fixed
  fps, not the buffer: HDR16 4K at 28 fps (onset, measured), counted per minute.
- **Cell (3 + 5 min):** the campaign rule (both clean = carried; two concordant drops = out), only for validation.
- **Per format, the drop source:** cDNG / lossy DNG / MLV: `recording_dropped_frames`, the file count or MLV frame count,
  index jumps. ProRes / H.264: Core's count and the frame count of the .mov/.mp4 by `ffprobe -count_frames` (to confirm
  on the Pi at build time), against fps x seconds.
- Every take logs temperatures, CPU per thread, `cma_free`, UI fds (as now) and the lossless/lossy/ProRes bytes per
  frame (needed for the storage term).

## 5. Blocks (one day, ~10 h, unattended; order within each block by die roll, logged in the preregistration)

| Block | What | Count | Time | Writes |
| --- | --- | --- | --- | --- |
| **P0** self-test, candidate set | file-create probe (10,000 empty files, 20 s); capacity probes: LJ HDR16 4K, LJ SDR12 2K, lossy 3:1 SDR12 4K, ProRes HQ 4K, H.264 1080; gap probes: HDR16 4K @28, 2K HDR16 @ top, HDR16 4K Log @28, HDR16 4K TDN on @25 | 9 + 1 | ~25 min | ~0.1 TB |
| **P1** capacity grid | every mode x format/compression of §3, levers at the reference state (TDN off, lock off, WebUI on, audio on, aids on) | 50, n = 2 for the 4K rows, n = 1 for 2K/crop | ~3 h | ~1.1 TB |
| **P2** lever fractional factorial | the five levers, 2^(5-1) = 16 runs (I = ABCDE: main effects and two-way interactions clear) at three anchors, one per bottleneck: back end (HDR16 unc 4K @28, gap probe), encoder (ProRes HQ 4K, capacity probe), storage + CPU (SDR12 unc 4K @ top, capacity probe); the back-end anchor twice | 64 | ~2.2 h | ~1.6 TB |
| **P3** validation | 12 combinations drawn by die from the whole space, stratified so each format family appears; per combination the model's p: a 3-min take at p and at p+1, a 5-min at p for 4 of them | 12 x 2 + 4 | ~1.7 h | ~1.5 TB |
| **P4** ladder check | `set_mode_ladder` with 3-4 rungs and thresholds = the model's estimates (e.g. 4K HDR16 unc to its p, then 4K SDR12 LJ, then 2K SDR12); 60-s takes at fps steps 25, p-1, p, p+1, 35, 40, 45, 50: right rung chosen, clean | ~8 | ~25 min | ~0.2 TB |
| **P5** self-test again | P0 repeated at the end of the day | 10 | ~25 min | ~0.1 TB |
| cooldowns | 10 min about every hour, between takes (as the NVMe campaign) | | ~1.3 h | |

Total ~10.5 h, ~4.6 TB. The two 30-min thermal checks (ProRes HQ 4K and LJ HDR16 at their p) are bought only if time is
left (+1 h, ~0.5 TB): 30-min behaviour of raw cDNG comes from S5/S6 tonight.

## 6. Analysis (pre-registered)

1. Fit the §2 stage model to P1 + P2 (per stage `a + b x pixels/bytes`; lever effects from P2's half-fraction as additive
   per-frame times on the stage they load; two-way interactions kept only where P2 shows them).
2. **Product 1:** predict every combination; the estimate shown is the whole fps below the prediction, with the stage
   that sets it.
3. **Validation (P3):** success = the 3-min take at p clean in >= 10 of 12, and p+1 out in >= 8 of 12 (the estimate is
   neither unsafe nor needlessly low). A miss is reported with its stage.
4. **Product 3, the self-test size:** refit the model from P0's probes only (plus the stored drive profile) and predict
   P1's cells. The self-test is P0 if >= 90 % of the predictions land within +-1 fps of the full fit; if not, add the probe
   that removes the largest error and repeat. P0 vs P5 gives the test-retest error at the start and end of a warm day.
5. **Product 2:** P4's rungs chosen as planned and clean at every step = the thresholds can come from the estimate.

Labels as in the campaign: measured (a take), derived (the model), probable / unconfirmed (a cause).

## 7. Stop rules and constraints (as the NVMe campaign)

- A setup mismatch skips the cell and goes on (since 64a3534 the start fps is clamped to the mode top); a watchdog, the
  write cap or a fill-gate failure ends the day with RESTORE, then power-off.
- During a take nothing else runs on the Pi; between takes `cat status.md` only. WebUI closed (the runner's stand-in is
  the WebUI lever). No sudo, no Core/UI edits or pushes, no defaults-pisp, no timecode mechanics. Clips are deleted only
  through `POST /api/media/delete?kind=folder&id=<name>` for folders the database created.
- Restore at the end: format cdng, compression, Log, ProRes profile, lossy ratio, H.264 size, TDN, lock, audio, aids,
  ladder (enabled and rungs), frames_per_folder 5000, merge on, read back.

## 8. To build first (Claude, in the KB's `working/tools/`, desk tests, then a 15-min smoke on the Pi)

- `longtakes.py`: a `PROBES` stage (capacity and gap probes as data rows); formats `lossydng`, `prores`, `h264` in
  `apply_cfg`/`verify` (`set_record_format`, `set_lossy_dng_ratio`, `set_prores_profile`, `set_prores_color_profile`,
  `set_h264_resolution`); their drop sources and frame counts (`ffprobe` for .mov/.mp4); the lever switches of §3 with
  read-back; the P2 design table and the die-roll orders written into the preregistration before the first take;
  `set_mode_ladder` for P4 (the `resolutions` string's compression field to confirm on the Pi tree); the restore list
  of §7.
- `estimate.py` (new, offline): the §2 fit, the P3/P0 checks, the estimate table as CSV + markdown.
- Rough size: half a day of work before the run starts.

## 9. Write budget

The plan's cap is 10 TB on this card, 2.2 TB used before tonight. Tonight's S2-S6 is estimated at ~7.8 TB (derived from
the fps and tiers), so the cap probably stops S6 part-way (the runner halts cleanly, restores and powers off). This run
adds ~4.6 TB. A new cap of 16 TB covers both; Patrik decides.

## 10. After this run

- The T7 SSD day: the drive profile (S1-lite write + file-create probe) and P0, to see whether the stage table carries
  across drives with only the drive profile changed.
- Two sensors once both Cores record: the shared back end, CPU and memory need their own dual rows (P2-style, ~1-2 h).
- Then the design note: estimator, fps cap switch (`fpsSustainedCap` / `fps_sustained_cap` / `set_fps_sustained_cap`),
  smart ladder thresholds, self-test, dual case.
