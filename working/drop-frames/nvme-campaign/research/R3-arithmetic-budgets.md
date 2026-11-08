# R3+R6: arithmetic and budgets of the NVMe campaign draft, checked against the KB (2026-11-08)

Reader: arithmetic/budgets, KB only (`/home/user/apertar-kb` at `origin/main` 2ba5b1b; the unmerged branch
`origin/claude/practical-johnson-he481b` read with `git show` for `storage-slowdown-plan.md` and
`reanalysis-longtakes-ssd-2026-11-08.md`; the erased first long-take run read from git history `242c0be` for two hardware facts only,
marked as such). Labels as the KB uses them: **measured** / **derived** / **probable** / **unconfirmed**; nothing is upgraded.
Owner's message of 2026-11-08 relayed by the harness: "cfe cards are corsair" (the shooting media are Corsair CFexpress cards; the KB
itself never names the CFe cards' model or capacity).

Inputs checked: `scratchpad/draft/constraints-and-arithmetic.md` sections 1, 7, 8, 11, 12 and `scratchpad/calc/capacity.txt` /
`capacity.py`. Scripts for this report: `scratchpad/calc/r3_arith.py`, `scratchpad/calc/r3_tables.py` (decimal GB, 10 GB reserve).

## 0. The three corrections that move numbers

1. **The HDR16 uncompressed file is 16,590,340 B (16.59 MB), not 16.90 MB.** `frame_bytes=16896000` is the RAW BUFFER
   (3840 x 2200 x 2 B, the 20 optical-black rows included; `night-2026-11-01.md:90`). Core writes a 2160-row file:
   3840 x 2160 x 2 = 16,588,800 + 1,540 B header/IFD = **16,590,340 B, measured** (`lessons/hardware-log.md:140` "files the same size
   as before, 16,590,340 bytes"; `inspection-2026-11-02.md:549` already corrects "DNG 16,590,340 B (not 16.9 MB)"; V-F4 row 10 shows the
   three measured sizes 16,590,340 / 12,451,344 / 12,443,140 are mutually consistent). Every HDR16-uncompressed figure in the draft and in
   `capacity.txt` is 1.85 % high: 415 MB/s at 25 fps (not 422), 747 GB per 30 min (not 760), 75 % of the empty Corsair (not 76).
2. **The exFAT per-entry constant is measured, not "unmeasured": c = 63.3 ns** (5-entry names; 62.5 ns with 4-entry names), fit
   `median_ns = -183,673 + 316.64 x files`, 60,000 empty files on the Corsair test card, kernel 6.12.75, Core idle, 2026-11-08
   (`working/drop-frames/nvme-campaign/probe-exfat-dir.md:60-64`, **measured**). The draft's section 8 table (c = 80 / 250 ns) and its
   "largest UNMEASURED risk" sentence are stale; the pre-registered 25 % rule is **exceeded at all three 30-min targets** (35 / 51 / 61 %)
   and met at the 15-min 25-fps stage (17 %) (`probe-exfat-dir.md:148-150`, derived). The clip-split knob the draft lists as a
   prerequisite to build already exists on `cinemate-port` (`[storage] frames_per_folder` d7dd337, `tools/flatten_clip.py` 9ec37b5, merge
   worker ba0658d default on; the camera runs it since the 13:00 boot with `frames_per_folder=0`, merge on; `fork-log.md:175-195`).
3. **The Kingston volume is 477 GiB = 512.0 GB decimal, so its usable space with a 10 GB reserve is about 502 GB, not 490 GB.** The KB
   page says "Kingston SKC3000S512G (477 GB)" (`longtakes-campaign-plan.md:19`); the runner reports `free_gb` as `free / 2**30`
   (`working/tools/longtakes.py:385`, GiB), and the erased run's samples read 475.9 GiB free at 0.2 % fill (git `242c0be`,
   `.../depth2-partial/samples/16b_unc_..._fps25_221054.csv`, **measured in that run; the page is erased from `origin/main`**). So the
   volume is about 476.9 GiB = 512.0e9 B (**derived**); df -B1 of the Kingston's exFAT volume is in no page of the KB (**unconfirmed**).
   The Corsair's volume is 999,960,870,912 B (**measured**, `night-2026-11-01.md:95`, `probe-exfat-dir.md:20`).

## 1. Corrected arithmetic table (deliverable 1)

Decimal MB/GB. Bytes per frame as the KB has them; "measured" only where a file was weighed. fps rows are the ones the KB makes
reachable for the arm (HDR16 4K full frame: the probe's maximum is 30 fps for 3840x2200 16-bit, `sensor-capabilities.md:51`,
`hardware-log.md:830`; measured ceiling 27-28 fps, `findings-2026-11-04.md:35-50`, `findings-evening4-supervised-2026-11-04.md:33-44`;
SDR 10/12-bit 4K: probe 60, crops 62.85-85.66). "max min" = usable bytes / (bytes per frame x fps) / 60. "fits" = 30 min or more. The
last column is the single-folder create cost at the take's final file count from the measured fit (section 2), as a share of the frame
period: a floor on what `s_lock` carries per frame, not the whole lock budget (`probe-exfat-dir.md:135-136`).

| Arm | bytes/frame | MB/frame | label | source | MB/s @24 | MB/s @25 | MB/s @28 | MB/s @30 | MB/s @33 | MB/s @42 | MB/s @50 |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| HDR16 unc 4K (3840x2200 raw, 2160-row file) | 16,590,340 | 16.59 | measured | HL:140 (file 16,590,340 B); V-F4 row 10 | 398 | 415 | 465 | 498 | 547 | 697 | 830 |
| HDR16 Log 16->12 4K | 12,451,344 | 12.45 | measured (one DNG) | HL:820; V-F4 row 10 | 299 | 311 | 349 | 374 | 411 | 523 | 623 |
| SDR12 unc 4K (packed) | 12,443,140 | 12.44 | derived | 12,441,600 + 1,540; V-F4 row 10, F4 2.1 | 299 | 311 | 348 | 373 | 411 | 523 | 622 |
| SDR12 lossless 4K (COMP1 in) | 5,982,609 | 5.98 | measured, one scene | HL:842-846 pre-roll 688 MB / 115 frames | 144 | 150 | 168 | 179 | 197 | 251 | 299 |
| SDR10 unc 4K (packed) | 10,369,540 | 10.37 | derived | F4 2.1 (10,368,000 + 1,540) | 249 | 259 | 290 | 311 | 342 | 436 | 518 |
| Crop 3840x2076 SDR12 unc | 11,959,300 | 11.96 | derived | F4 A'; mode measured at 50 fps (HL:582-596) | 287 | 299 | 335 | 359 | 395 | 502 | 598 |
| Crop 3840x2072 SDR12 unc (1.85:1) | 11,936,260 | 11.94 | derived | mode probed 2026-11-01 (HL:901), no take | 286 | 298 | 334 | 358 | 394 | 501 | 597 |
| Crop 3840x1608 SDR12 unc (2.39:1) | 9,263,620 | 9.26 | derived | driver crop list drivers.md:141; no take | 222 | 232 | 259 | 278 | 306 | 389 | 463 |
| HDR16 height crop (heights unknown) | - | - | unconfirmed | fork-log 31d5418: 16-bit crops at 31.9-42.4 fps; no height in KB | - | - | - | - | - | - | - |

| Arm | fps | GB 3 min | GB 5 min | GB 15 min | GB 30 min | files / 30 min | fill of empty Corsair after 30 min | 990 GB usable: max min | 490 GB (draft): max min | 502 GB (Kingston 477 GiB - 10 GB): max min | create cost at the 30-min file count (share of period) |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| HDR16 unc 4K (3840x2200 raw, 2160-row file) | 24 | 72 | 119 | 358 | 717 | 43,200 | 72 % | 41.4 (fits) | 20.5 | 21.0 | 13.5 ms (32 %) |
| HDR16 unc 4K (3840x2200 raw, 2160-row file) | 25 | 75 | 124 | 373 | 747 | 45,000 | 75 % | 39.8 (fits) | 19.7 | 20.2 | 14.1 ms (35 %) |
| HDR16 unc 4K (3840x2200 raw, 2160-row file) | 28 | 84 | 139 | 418 | 836 | 50,400 | 84 % | 35.5 (fits) | 17.6 | 18.0 | 15.8 ms (44 %) |
| HDR16 unc 4K (3840x2200 raw, 2160-row file) | 30 | 90 | 149 | 448 | 896 | 54,000 | 90 % | 33.2 (fits) | 16.4 | 16.8 | 16.9 ms (51 %) |
| HDR16 Log 16->12 4K | 24 | 54 | 90 | 269 | 538 | 43,200 | 54 % | 55.2 (fits) | 27.3 | 28.0 | 13.5 ms (32 %) |
| HDR16 Log 16->12 4K | 25 | 56 | 93 | 280 | 560 | 45,000 | 56 % | 53.0 (fits) | 26.2 | 26.9 | 14.1 ms (35 %) |
| HDR16 Log 16->12 4K | 28 | 63 | 105 | 314 | 628 | 50,400 | 63 % | 47.3 (fits) | 23.4 | 24.0 | 15.8 ms (44 %) |
| HDR16 Log 16->12 4K | 30 | 67 | 112 | 336 | 672 | 54,000 | 67 % | 44.2 (fits) | 21.9 | 22.4 | 16.9 ms (51 %) |
| SDR12 unc 4K (packed) | 25 | 56 | 93 | 280 | 560 | 45,000 | 56 % | 53.0 (fits) | 26.3 | 26.9 | 14.1 ms (35 %) |
| SDR12 unc 4K (packed) | 28 | 63 | 105 | 314 | 627 | 50,400 | 63 % | 47.4 (fits) | 23.4 | 24.0 | 15.8 ms (44 %) |
| SDR12 unc 4K (packed) | 30 | 67 | 112 | 336 | 672 | 54,000 | 67 % | 44.2 (fits) | 21.9 | 22.4 | 16.9 ms (51 %) |
| SDR12 unc 4K (packed) | 33 | 74 | 123 | 370 | 739 | 59,400 | 74 % | 40.2 (fits) | 19.9 | 20.4 | 18.6 ms (61 %) |
| SDR12 unc 4K (packed) | 42 | 94 | 157 | 470 | 941 | 75,600 | 94 % | 31.6 (fits) | 15.6 | 16.0 | 23.8 ms (100 %) |
| SDR12 unc 4K (packed) | 50 | 112 | 187 | 560 | 1120 | 90,000 | 112 % | 26.5 | 13.1 | 13.5 | 28.3 ms (142 %) |
| SDR12 lossless 4K (COMP1 in) | 25 | 27 | 45 | 135 | 269 | 45,000 | 27 % | 110.3 (fits) | 54.6 (fits) | 56.0 (fits) | 14.1 ms (35 %) |
| SDR12 lossless 4K (COMP1 in) | 30 | 32 | 54 | 162 | 323 | 54,000 | 32 % | 91.9 (fits) | 45.5 (fits) | 46.6 (fits) | 16.9 ms (51 %) |
| SDR12 lossless 4K (COMP1 in) | 33 | 36 | 59 | 178 | 355 | 59,400 | 36 % | 83.6 (fits) | 41.4 (fits) | 42.4 (fits) | 18.6 ms (61 %) |
| SDR12 lossless 4K (COMP1 in) | 42 | 45 | 75 | 226 | 452 | 75,600 | 45 % | 65.7 (fits) | 32.5 (fits) | 33.3 (fits) | 23.8 ms (100 %) |
| SDR12 lossless 4K (COMP1 in) | 50 | 54 | 90 | 269 | 538 | 90,000 | 54 % | 55.2 (fits) | 27.3 | 28.0 | 28.3 ms (142 %) |
| SDR10 unc 4K (packed) | 25 | 47 | 78 | 233 | 467 | 45,000 | 47 % | 63.6 (fits) | 31.5 (fits) | 32.3 (fits) | 14.1 ms (35 %) |
| SDR10 unc 4K (packed) | 30 | 56 | 93 | 280 | 560 | 54,000 | 56 % | 53.0 (fits) | 26.3 | 26.9 | 16.9 ms (51 %) |
| SDR10 unc 4K (packed) | 33 | 62 | 103 | 308 | 616 | 59,400 | 62 % | 48.2 (fits) | 23.9 | 24.5 | 18.6 ms (61 %) |
| SDR10 unc 4K (packed) | 42 | 78 | 131 | 392 | 784 | 75,600 | 78 % | 37.9 (fits) | 18.8 | 19.2 | 23.8 ms (100 %) |
| SDR10 unc 4K (packed) | 50 | 93 | 156 | 467 | 933 | 90,000 | 93 % | 31.8 (fits) | 15.8 | 16.1 | 28.3 ms (142 %) |
| Crop 3840x2076 SDR12 unc | 25 | 54 | 90 | 269 | 538 | 45,000 | 54 % | 55.2 (fits) | 27.3 | 28.0 | 14.1 ms (35 %) |
| Crop 3840x2076 SDR12 unc | 30 | 65 | 108 | 323 | 646 | 54,000 | 65 % | 46.0 (fits) | 22.8 | 23.3 | 16.9 ms (51 %) |
| Crop 3840x2076 SDR12 unc | 33 | 71 | 118 | 355 | 710 | 59,400 | 71 % | 41.8 (fits) | 20.7 | 21.2 | 18.6 ms (61 %) |
| Crop 3840x2076 SDR12 unc | 42 | 90 | 151 | 452 | 904 | 75,600 | 90 % | 32.8 (fits) | 16.3 | 16.7 | 23.8 ms (100 %) |
| Crop 3840x2076 SDR12 unc | 50 | 108 | 179 | 538 | 1076 | 90,000 | 108 % | 27.6 | 13.7 | 14.0 | 28.3 ms (142 %) |
| Crop 3840x2072 SDR12 unc (1.85:1) | 25 | 54 | 90 | 269 | 537 | 45,000 | 54 % | 55.3 (fits) | 27.4 | 28.0 | 14.1 ms (35 %) |
| Crop 3840x2072 SDR12 unc (1.85:1) | 30 | 64 | 107 | 322 | 645 | 54,000 | 64 % | 46.1 (fits) | 22.8 | 23.4 | 16.9 ms (51 %) |
| Crop 3840x2072 SDR12 unc (1.85:1) | 33 | 71 | 118 | 355 | 709 | 59,400 | 71 % | 41.9 (fits) | 20.7 | 21.2 | 18.6 ms (61 %) |
| Crop 3840x2072 SDR12 unc (1.85:1) | 42 | 90 | 150 | 451 | 902 | 75,600 | 90 % | 32.9 (fits) | 16.3 | 16.7 | 23.8 ms (100 %) |
| Crop 3840x2072 SDR12 unc (1.85:1) | 50 | 107 | 179 | 537 | 1074 | 90,000 | 107 % | 27.6 | 13.7 | 14.0 | 28.3 ms (142 %) |
| Crop 3840x1608 SDR12 unc (2.39:1) | 25 | 42 | 69 | 208 | 417 | 45,000 | 42 % | 71.2 (fits) | 35.3 (fits) | 36.1 (fits) | 14.1 ms (35 %) |
| Crop 3840x1608 SDR12 unc (2.39:1) | 30 | 50 | 83 | 250 | 500 | 54,000 | 50 % | 59.4 (fits) | 29.4 | 30.1 (fits) | 16.9 ms (51 %) |
| Crop 3840x1608 SDR12 unc (2.39:1) | 33 | 55 | 92 | 275 | 550 | 59,400 | 55 % | 54.0 (fits) | 26.7 | 27.4 | 18.6 ms (61 %) |
| Crop 3840x1608 SDR12 unc (2.39:1) | 42 | 70 | 117 | 350 | 700 | 75,600 | 70 % | 42.4 (fits) | 21.0 | 21.5 | 23.8 ms (100 %) |
| Crop 3840x1608 SDR12 unc (2.39:1) | 50 | 83 | 139 | 417 | 834 | 90,000 | 83 % | 35.6 (fits) | 17.6 | 18.1 | 28.3 ms (142 %) |

| files in the folder | create ms (fit) | 25 fps (40.0 ms) | 28 fps (35.7 ms) | 30 fps (33.3 ms) | 33 fps (30.3 ms) | 50 fps (20.0 ms) |
|---:|---:|---:|---:|---:|---:|---:|
| 15,000 (10 min at 25; A0/A1/#80 measured clean) | 4.57 | 11 % | 13 % | 14 % | 15 % | 23 % |
| 22,500 (15 min at 25) | 6.94 | 17 % | 19 % | 21 % | 23 % | 35 % |
| 28,500 (draft's fit tier) | 8.84 | 22 % | 25 % | 27 % | 29 % | 44 % |
| 29,535 (fit tier, 490 GB, HDR16 unc) | 9.17 | 23 % | 26 % | 28 % | 30 % | 46 % |
| 30,258 (fit tier, 502 GB, HDR16 unc) | 9.40 | 23 % | 26 % | 28 % | 31 % | 47 % |
| 45,000 (30 min at 25) | 14.07 | 35 % | 39 % | 42 % | 46 % | 70 % |
| 50,400 (30 min at 28) | 15.77 | 39 % | 44 % | 47 % | 52 % | 79 % |
| 54,000 (30 min at 30) | 16.91 | 42 % | 47 % | 51 % | 56 % | 85 % |
| 59,400 (30 min at 33) | 18.62 | 47 % | 52 % | 56 % | 61 % | 93 % |
| 90,000 (30 min at 50) | 28.31 | 71 % | 79 % | 85 % | 93 % | 142 % |

25 % ceiling (create alone <= 0.25 x period), from the fit: 32,161 files at 25 fps, 28,777 files at 28 fps, 26,898 files at 30 fps, 24,505 files at 33 fps, 16,370 files at 50 fps (the probe page rounds these to 31,600 / 26,300 / 23,900 / 15,800 using c = 63.3 ns without the intercept).

Notes on the arms:

- **HDR16 unc / Log above 30 fps in 4K full frame do not exist**: `capacity.txt`'s HDR16 rows at 33 / 42 / 50 fps are unreachable modes
  (probe max 30; `fps_max` 30 in Core's state 2026-11-04; the Pi tops out at 27-28 fps measured). The only 16-bit modes above 30 fps are
  height crops at 31.9-42.4 fps (`fork-log.md:147`, row 31d5418) whose heights are not written anywhere in the KB (**unconfirmed**).
- **HDR16 Log 16->12**: file size measured on one DNG (2026-10-31); no Log take longer than about 5 s exists on the NVMe at 4K
  (`dng-chain-feasibility.md:380`, item 7; lever 13: "the one Log sample had the worst gap rate"). The SSD run has 30-min 2K HDR16+Log passes
  at 25-28 fps (`results.md:624-626`, measured, different drive and mode). In the erased Kingston run "Log on" configs failed within 2-3 s at
  every fps, cause unexplained (git `242c0be`, erased page item 6; **unconfirmed**, not on `origin/main`).
- **HDR16 lossless (with or without Log) is not a >= 25 fps arm**: the Clear HDR 16-bit lossless encoder measured 17.6-18.5 fps of
  capacity (`hardware-log.md:94`, `T23.md:19`); a 25 fps lossless HDR16 take fills the RAM buffer and safety-stops (`README.md:184`,
  measured). Its file size is unmeasured (UI model ~12.1 MB, `R8.md:62`, unconfirmed); the SSD run measured 4K HDR12 lossless + Log at 8.5 MB
  against 6.1 MB without Log (`findings-longtakes-ssd-2026-11-07.md:37`, measured): Log makes lossless files bigger, not smaller. The draft's
  section 7 row "HDR16 Log + lossless ... 30 min probable" should go.
- **SDR12 lossless at 50 fps fits the drive but probably not the CPU**: at 33 fps the encoders cost 84 ms of CPU per frame, 2.81 cores
  (`findings-2026-11-04.md:56, 63`, measured); 50 fps would need about 4.2 cores of 4 (**derived**). The pre-roll's capacity estimates
  (48.13 fps on t2a's pre-roll; 62.9 fps on 2026-11-01) are 2-s figures (measured, short). Label the 50 fps lossless arm **probable:
  encoder-bound**, as the SSD findings page suspects for 4K lossless (`findings-longtakes-ssd-2026-11-07.md:53-55`, unconfirmed there).
- **SDR12 uncompressed** is derived (12,441,600 + 1,540): no SDR12 uncompressed DNG was ever weighed in the KB (V-F4 row 10 labels it
  "derived (checked)"; the task text and R2 call it measured: that is an upgrade). t2b's "~410 MB/s" (`findings-2026-11-04.md:64`) is
  this derivation times 33, not a measurement.
- **Crops**: 3840x2076 SDR12 50 fps was run twice for 60 s on 2026-10-28 (12 % lost as capture gaps, queue 2-3/12, old build, untrimmed
  drive at 78-82 %; `hardware-log.md:582-596`, measured). 3840x2072 (1.85:1) exists at 10/12-bit on driver cd548ef (probed, no take;
  `hardware-log.md:901`). The other 4K crops on this image: 3840x{2024, 1920, 1744, 1728, 1632, 1608, 1536, 1504} at 10/12-bit
  (`architecture/drivers.md:141, 207`). **There is no 3840x1600 mode** (capacity.txt's "4K crop 3840x1600 2 B/px (2.4:1)" is not a KB mode;
  the 2.35:1 / 2.39:1 crops are 1632 and 1608 rows, and at 12-bit they are 1.5 B/px, not 2). File sizes of all crops are derived from
  geometry; none weighed.
- **Lossy 3:1 / 5:1**: no file size anywhere in the KB; `capacity.py` divides 16.9 MB (5.63 / 3.38 MB), R2 divides 12.44 MB (4.1 / 2.5 MB):
  both **unconfirmed**. Lossy DNG is a separate format (`set_lossy_dng_ratio`, `README.md:379`).
- The 10 GB reserve: exFAT metadata is 0.6-0.7 KB per frame (< 0.01 % of the data; F4 §2.1, derived); the clip directory of a 45,000-file
  take is 7.2 MB (45,000 x 160 B, derived); the storage pre-roll writes and deletes about 0.7-0.8 GB (688 MB measured at 60 fps lossless;
  50 x 16.59 MB = 0.83 GB at HDR16 25 fps, derived); the runner's own end rule is "clean until < 6 GiB free" (`longtakes.py:783`,
  `longtakes-test-structure.md:64`) and its gate wants the take's projected writes plus 20 GiB free (slowdown plan 7.1, unmerged branch).

Per-take bytes, HDR16 uncompressed 25 fps (derived from the measured file): 1 min 25 GB, 3 min 75, 5 min 124, 10 min 249, 15 min 373,
30 min 747 GB (the draft: 76 / 127 / 380 / 760).

## 2. exFAT create cost from the measured fit (deliverable 2)

Fit: `median_ns = -183,673 + 316.64 x files` (**measured**, block medians of 60,000 creates, `probe-exfat-dir.md:60`); one create, empty
files, idle machine, cached entries (one core at 100 %, CPU time = wall: the walk is CPU-bound, so the constant transfers between
drives and cards, `probe-exfat-dir.md:61-62`, measured). Periods: 25 fps 40.0 ms, 28 fps 35.7, 30 fps 33.3, 33 fps 30.3, 50 fps 20.0.

| files in the folder | create ms (fit) | 25 fps | 28 fps | 30 fps | 33 fps | 50 fps |
|---:|---:|---:|---:|---:|---:|---:|
| 15,000 (10 min at 25; A0, A1, #80, C0101 clean) | 4.57 | 11 % | 13 % | 14 % | 15 % | 23 % |
| 22,500 (15 min at 25) | 6.94 | 17 % | 19 % | 21 % | 23 % | 35 % |
| 28,500 (draft's fit tier) | 8.84 | 22 % | 25 % | 27 % | 29 % | 44 % |
| 29,535 (fit tier on 490 GB, HDR16 unc) | 9.17 | 23 % | 26 % | 28 % | 30 % | 46 % |
| 30,258 (fit tier on 502 GB, HDR16 unc) | 9.40 | 23 % | 26 % | 28 % | 31 % | 47 % |
| 45,000 (30 min at 25) | 14.07 | **35 %** | 39 % | 42 % | 46 % | 70 % |
| 54,000 (30 min at 30) | 16.91 | 42 % | 47 % | **51 %** | 56 % | 85 % |
| 59,400 (30 min at 33) | 18.62 | 47 % | 52 % | 56 % | **61 %** | 93 % |
| 90,000 (30 min at 50) | 28.31 | 71 % | 79 % | 85 % | 93 % | 142 % |

- The probe's own table (`probe-exfat-dir.md:126-133`) has the same rows at 25/30/33/50 fps; the 28-fps column and the fit-tier rows are
  added here (derived). 25 % ceiling from the fit: 32,161 files at 25 fps, 28,777 at 28, 26,898 at 30, 24,505 at 33, 16,370 at 50
  (the probe page: 31,600 / 26,300 / 23,900 / 15,800 without the intercept).
- Measured floor, not the whole lock: in a take `s_lock` also carries the writers' block mappings (32,400 `exfat_get_block` calls per 16.59 MB
  file at 512-B blocks, or ~4,050 if the block size is 4 KiB; 0.15-0.3 us each, estimated: F4 §2.3 F1-F3, V-F4 row 19, S1 §3.2) and the
  fsync's dentry write. At 25 fps the F4 model's extra term is 4.9-9.7 ms (estimated).
- Fit-tier takes on the Kingston at 28-30 fps end at 26-28 % of the period: **above** the pre-registered 25 % line too (derived), so the
  "milder" reading in the draft's section 11 (5) holds only at 25 fps (23 %).
- What the live system says so far: the SSD run's 30-min passes reached 45,006-59,412 files in one folder with 0 drops (2K SDR10 33 fps
  passed at 59,412 files where the walk alone is 61 % of the period; `reanalysis ... §2, §4`, measured); its "late" failures came at
  33,500-61,800 files, with Core's CPU rising from about 0.5 to 1.0-1.3 cores over each long take (measured) and a derived
  c of 77-133 ns, median 99 (superseded by the probe's 63.3 ns; the gap says other per-file costs grow too, or the slope is not only the walk:
  **probable**). On the NVMe the longest clean single folder is 19,857 files (t2b, 10 min SDR12 33 fps; `takes.md:100`); the draft's
  "longest measured clean folder" sentence should say "on the NVMe".
- Unlink: warm cache 5 us per file, flat (60,000 files in 0.5 s wall; `probe-exfat-dir.md:71-73`, measured). Cold cache (after a reboot):
  **unconfirmed**, step 4 prepared (a 10,000-file probe folder `probe_exfat_dir_125428` is still on the Corsair test card for it,
  `probe-exfat-dir.md:105-114`). Merge of a split clip = create cost at the target size: about 5.2 min for 45,000 files, 7.5 min for 54,000
  (`probe-exfat-dir.md:98-103`, derived); the merge worker is **on by default** on the running build (`fork-log.md:188`), so a split take's
  merge runs between takes unless `[storage] clip_merge` is off (`APERTAR_CLIP_MERGE=0`); the slowdown plan's A/B wants it off
  (unmerged branch, 4.3 item 2).

## 3. Numbers in the draft that are wrong or mislabelled (deliverable 3)

| # | Where | Draft says | KB says | Correction / label |
|---|---|---|---|---|
| 1 | §1 table, §2, §7 table, §11, `capacity.py` | HDR16 unc 16.90 MB/frame "measured frame_bytes 16,896,000" | 16,896,000 is the raw buffer (3840x2200x2); the file is 16,590,340 B (`HL:140`, measured) | 16.59 MB; 415/465/498 MB/s at 25/28/30; 747/836/896 GB per 30 min; 75/84/90 % of the empty Corsair; 3/5/15 min = 75/124/373 GB; 490 GB: 19.7/17.6/16.4 min; 502 GB: 20.2/18.0/16.8 min |
| 2 | §1 bullet 2 | "15-min HDR16 take (380 GB) ... 2 x 380 = 760 GB = 76 %" | 373 GB; 747 GB = 75 % | arithmetic only; moot after §7 |
| 3 | §1 bullet 4, §8 | "exFAT create scan ... estimated 12-38 ms per create at 30,000 files, constant c unmeasured"; "largest UNMEASURED risk" | c = 63.3 ns measured 2026-11-08; 9.3 ms median at 30,000 files; 14.1 ms at 45,000 (`probe-exfat-dir.md:53-60`) | replace the c = 80/250 ns table with the measured fit (section 2); the open part is the live-system share (split A/B), not c |
| 4 | §1 bullet 4 | "The longest measured clean folder is 19,857 files" | on the NVMe yes (t2b); the T7 SSD run passed 30 min with 45,006-59,412 files in one folder, 0 drops (reanalysis §2, measured; same Core and kernel, different drive) | say "on the NVMe"; the SSD passes bound the directory cost alone |
| 5 | §8 | "A0/A1 exclude only c > ~450 ns; the SDR12 33 fps 10-min takes exclude c > ~250 ns (derived)" | the 19,857-file take bounds c < ~290-305 ns (5 x 19,857 x c <= 30.3 ms minus the mapping term) | loose but harmless; moot |
| 6 | §8 | "after a reboot each unlink re-walks the directory: minutes per 45,000-file clip (derived; unmeasured)" | warm unlink 5 us/file flat measured; cold unlink unconfirmed (probe step 4 not run) | keep "unconfirmed" for cold; add the measured warm figure and the rule "delete in the boot that wrote" |
| 7 | §8 recommendation, §9 prerequisite | "a ZERO-WEAR probe first ..."; "Prerequisite (code ...): Core knob `[storage] frames_per_folder`" | both done 2026-11-08: probe page in the KB; knob d7dd337 + flatten 9ec37b5 + merge worker ba0658d on `cinemate-port`, running on the camera (`frames_per_folder=0`, merge on); UI 7ea9afc reads split clips (built, not tried on a touch screen) | rewrite as "done; outcome: above 25 % at all three 30-min targets -> split knob and flatten are prerequisites, split A/B mandatory"; add `clip_merge` off as a campaign setting or budget the merge time |
| 8 | §2 | "smart-log 2026-11-02: 25.28 TB ... +1.34 TB on evening 1, +1.55 TB on evening 3" | 49,380,871 DU (25.28 TB) baseline read 2026-11-02 18:5x; after evening 1 51,995,905 (26.62 TB, +1.34); after evening 2 53,634,400 (27.46 TB, +0.84; `handoff-drop-frames-tests.md:203`); after evening 3 29.01 TB (+1.55; `handoff-drop-frames-tier1.md:185`); after evening 4 only "43 C, 3 % used" (`preregistration.md:783-784`), no DU figure | add evening 2 and the 29.01 TB total; the evening-4 and 11-07 NVMe writes (erased runs) are unrecorded |
| 9 | §2 | "Implied endurance from SMART: 25.28 TB / 0.03 = ~840 TB" | `percentage_used` is an integer (2.5-3.5 %); rated TBW not in the KB (`nvme-4k-recipe-plan.md:58`: "not looked up ... unconfirmed") | derived from a rounded integer: 722-1011 TB; and it is the **Corsair test card's** (A936B442006AC2) counter, not the Kingston's (no Kingston SMART reading on `origin/main`) |
| 10 | §2 | "A campaign of ~8-10 TB (the previous campaign's own estimate for five evenings)" | the B-plan estimate was "~8-10 TB, probable" (`inspection-2026-11-02.md:223`, `night-2026-11-01.md:316`); the NVMe 4K recipe plan says "~4-7 TB expected, hard cap 8 TB" (`nvme-4k-recipe-plan.md:54`); the SSD ladder wrote 5.9 TB on the T7, not the NVMe (`findings-longtakes-ssd-2026-11-07.md:5`) | name the source; the 5.9 TB is T7 wear |
| 11 | §7 table | "1 TB card (990 GB usable)" | 999,960,870,912 - 10e9 = 989.96 GB | fine |
| 12 | §7 table, §11, §12 | "500 GB card (490 GB usable)"; "477 GiB" | KB: "477 GB" (campaign plan); runner unit GiB; volume about 512.0 GB decimal (derived from the erased run's samples); df of the Kingston's exFAT volume unconfirmed | about 502 GB usable; max minutes +2.4 % over the draft's (HDR16 unc 20.2/18.0/16.8 at 25/28/30; SDR12 unc 26.9/22.4/20.4 at 25/30/33; Log12 26.9/22.4; SDR10 unc 32.3/26.9/24.5 at 25/30/33; lossless SDR12 50 fps 28.0) |
| 13 | §7 table | "HDR16 Log + lossless (size unmeasured, model ~9-12 MB/frame) ... 30 min probable" | HDR16 lossless encoder 17.6-18.5 fps (measured); Log + lossless made bigger files (8.5 vs 6.1 MB at 4K HDR12 on the SSD, measured) | not a >= 25 fps arm; drop the row or label "encoder-bound at ~17.5 fps (measured)" |
| 14 | §7 table | "SDR12 lossless 33 / 50 fps ... 30 / 27 min max" | storage: 41.4 / 27.3 min on 490 GB (42.4 / 28.0 on 502); CPU: 2.81 cores at 33 fps measured -> ~4.2 cores at 50 (derived) | add "50 fps lossless probable encoder-bound" |
| 15 | §11 (1) | "HDR16 unc 16-19 min, SDR12/HDR12 unc 20-26, Log12 22-26" | with 502 GB: 16.8-20.2, 20.4-26.9, 22.4-26.9 | small; the 490 GB figures are the lower bound |
| 16 | §11 (5) | "the directory effect is milder (28,500 files = 22 % of the period at 25 fps)" | fit tier = 29,535 (490 GB) or 30,258 (502 GB) frames: 23 % at 25 fps, 26 % at 28, 28 % at 30 | at 28-30 fps the fit tier is above the 25 % line too |
| 17 | §11 (4), §12 | "400 TBW (KC3000 512 GB)", "~110 TBW (P310 500 GB)", "DRAM-equipped", "2280 Gen 4" | not in the KB | web facts for the web reader (label `web` with URL); P310 presence in the KB: `findings-2026-11-03.md:43` (serial 25184FF10656), `handoff-drop-frames-tests.md:208` |
| 18 | §12 | "CFexpress cards are Corsair MP600 Mini 1 TB (the same model as the record's test drive)" | the owner's statement (2026-11-08) names the brand; the KB's test drive is "Corsair MP600 MINI" serial A936B442006AC2, firmware ERFM11.1 (`probe-exfat-dir.md:21-22`, `HL:703`); no KB page names the CFe cards' model or capacity | label the model/capacity identity **unconfirmed** (owner's word on the brand only) |
| 19 | §12 (2) | "a different CM5 board that dropped within 2 s at 30 fps where the C0 board (c041a0) ran clean: a board effect, not the card" | `longtakes-test-structure.md:139`: one take each, "Not repeated here"; `longtakes-campaign-plan.md:11`: "the Pi has a different CPU type now"; the erased run also had audio on and a different UI/WebUI state (confounded) | "a board effect" is **probable at most** (n = 1 + 1); the card is not exonerated by the KB |
| 20 | `capacity.txt` | HDR16 rows at 33 / 42 / 50 fps; "HDR16 lossless JPEG (est. ~9 MB)"; lossy 16.9/3, 16.9/5; "4K crop 3840x1600 2 B/px"; "3840x2072 HDR16-style 2 B/px (est.)" | 16-bit 4K full frame max 30 fps (probe); lossless HDR16 encoder-bound ~17.5 fps and UI model 12.1 MB; lossy sizes unmeasured; 3840x1600 is not a mode; 16-bit crop heights unknown | drop or relabel; the 75 % rule column is void after §7 |
| 21 | §1 header | "smart-log ... on 11-01" (task text) | the baseline was read 2026-11-02 18:5x (`night-2026-11-01.md:97-106`, B0 steps 4, 8, 10) | date only |
| 22 | §7 | "free_bytes >= planned_bytes x 1.03 + 10 GB reserve (exFAT metadata, the WAV, the pre-roll)" | metadata < 0.01 % (derived); pre-roll 0.7-0.8 GB (measured/derived); WAV format and size not in the KB | the 3 % is generous (fine); the runner's existing rules are "< 6 GiB free = drive full" and "projected writes + 20 GiB free" at the gate |

Numbers in the draft that check out: 999,960,870,912 B; 45,000 / 54,000 / 59,400 files per 30 min; 12,451,344 B Log; 5.98 MB lossless (one
scene); 10.37 MB SDR10 (derived); 311 / 374 MB/s Log at 25 / 30; 311 / 373 / 411 / 523 MB/s SDR12 unc at 25 / 30 / 33 / 42; 560 / 672 / 739 /
941 GB; #78 25 of 15,023 with 18 in the last minute at 97 % (`night-2026-11-01.md:22-23`, `README.md:176-181`); #80 0 of 15,025 on the
empty drive; C0106 / C0107 at ~77 / 81 % full lost 166 / 676 in 3 min (untrimmed drive, T29/T30 build, `HL:378-393`); A0 34 -> 54 C;
t2a / t2b 65 / 72 C; evening 4 44-66 C; the 5 dentries per frame file and the O(N) walk under `s_lock` (V-F4 rows 16-17, confirmed in
source); 6,000 files per folder in the 2026-10-30 synthetic single-folder runs (240 s x 25 files/s; sub-folders of 500/1000/2500);
`frames_per_folder` = 5,000 = 25,000 dentries; the 1 MB-file synthetic 30-min run = 45 GB = 6 % of a take.

## 4. What the KB says grows with take length (deliverable 4)

| Quantity | How it grows | KB evidence | Label |
|---|---|---|---|
| Files in the clip folder, and the create cost | linear: 316.64 ns per existing file per create (63.3 ns per entry x 5); 4.6 ms at 15,000, 14.1 ms at 45,000, 18.6 ms at 59,400; no cluster-boundary spikes | `probe-exfat-dir.md:46-69` | measured (probe); the share in a live take is a floor (derived) |
| Core's CPU within a take | 0.45-0.62 -> 0.80-1.29 cores over 17 long SSD takes at constant fps, free memory flat; slope 2.9e-4 to 6.0e-4 per s; the busiest thread moves from CameraManager to an unnamed Core thread | reanalysis §4 (unmerged branch); first NVMe run "CPU 49-54 -> 63-64 %" in long takes (erased, git `242c0be`) | measured (SSD); the reading "it is the directory walk" is derived; c from the slope 99 ns vs 63.3 ns measured: part of the slope is something else (probable) |
| Time to failure in the "late" regime | the drain tracks the need to 1-3 % for 7-28 min, then the buffer fills in under a minute; failing file counts 33,500-61,800, rising with fps and falling with file size | reanalysis §2-3 (118 buffer_full takes on the T7) | measured on the T7; mechanism "a growing cost crosses a threshold" probable; not seen on the NVMe (no NVMe take > 10 min on `origin/main`) |
| Drive fill | HDR16 unc 25 fps: 24.9 GB per min = 2.5 % of the Corsair volume per min (75 % at 30 min); 4.9 % of the Kingston per min (full at ~20 min). Record: untrimmed 77-81 % lost frames (old build); #78 lost 18 of 25 in minute 10 at 94-97 % (trimmed, dirty-limit change pending); #80 empty drive clean; "fill harmless below ~94 %"; the allocation cursor walks the whole volume in 2.5-3.7 ten-minute takes | `HL:378-393`; `night-2026-11-01.md:22-23, 54-57`; `inspection-2026-11-02.md:85, 120`; `dng-chain-feasibility.md:144-146` | fill rate derived; the fill effect at 94-97 % probable; the cursor wrap "harmless after a trim" measured on synthetic runs (12 of 12) |
| NVMe temperature | 10-min takes: 34 -> 54 C at 415 MB/s (A0, cooled start), 39 -> 65 C at 197 MB/s lossless (t2a), 39 -> 72 C at 410 MB/s (t2b): 2.0-3.3 C per min; 3-min takes 40 -> 50-62 C, a second take right after starts at 48-57 C and ends 57-65 C; evening 4 (no gate) 44-66 C; synthetic 240-s runs back to back peaked 60-72 C with no effect on drops; warning limit 82.9 C, crit 85 C; cool-down ~57-62 -> 40 C in 15-20 min; idle 26.9 -> 34.9 C during the 16-min CPU-only probe; nothing longer than 10 min measured on the NVMe; the T7 has no sensor | `HL:745-748, 384, 715-716`; `takes.md:7-11, 84-100`; `findings-2026-11-04.md:56-57`; `findings-evening4-supervised-2026-11-04.md:31`; `findings-2026-11-02.md:56`; `probe-exfat-dir.md:122` | endpoints measured; slopes derived; the 30-min trajectory and the plateau unconfirmed (feasibility §2.4 estimates 60-85 C at 622 MB/s by a linear model) |
| Page cache and reclaim | `dontneed=sync`: footprint bounded at 1-2 sync ticks (0.4-0.85 GB), kswapd 47-58 k pages per 3 min and 586 k pages in #78's 10 min (vs 3.0-3.45 M per 3 min under `writer`); MemAvailable flat during the SSD takes; "free RAM flat (no leak)" in the erased Kingston long takes. At the stop the sync thread ends before the drain, so dirty pages pile up (stop-path effect) | `inspection-2026-11-02.md:24-27`; `README.md:176-181`; reanalysis §4-5; slowdown plan M7 | measured (counters); the stop-path dirty-page part probable (read from code order) |
| Process and boot age | "the drift is monotone with uptime: not supported" (n = 4; the 11-01 rise was a step on a fresh drive); A0 ran clean 9 h 43 min after boot; results on the SSD "drifted by ~3 fps over hours"; the RAM budget at take start varied 250-1283 MiB (1.6-17 s of input) with MemAvailable: a between-takes state | `inspection-2026-11-02.md:67-68, 85`; `night-2026-11-01.md:86-89`; `nvme-4k-recipe-plan.md` table row "Results drifted"; reanalysis §8 | measured facts; "no age effect" is a non-finding (unconfirmed either way) |
| Bytes written (wear) | 24.9 GB per min at HDR16 25 fps; 18.7 at Log/SDR12 25 fps; a 30-min take 747 GB; the record's evenings wrote 0.84-1.55 TB each | section 5 of this report | derived (per take) / measured (SMART deltas) |
| Trim state between takes | Core trims at mount, after Core deletes >= 1 GiB and after an outside delete when free space rises >= 1 GiB between two polls; after a slow unlink of 45,000-62,000 files that trigger may never fire (the SSD run recorded no trim at all) | `fork-log.md` 00f2327; `ApertarCoreApp.cpp:10863-10869@f4a1393` via reanalysis §7 | mechanism confirmed in code; "never fires after slow deletes" derived, unconfirmed; the probe's warm unlink is 5 us/file for EMPTY files (45,000 names in ~0.25 s, derived); a real frame file also frees 127 clusters (FAT-chained with 4 writers, F4 F5: one `sb_bread` per cluster when chained), a cost the probe did not measure (unconfirmed), so whether a clip delete crosses the 1 GiB-per-poll trigger on this kernel is open |
| Audio/picture drift | +18 ppm over 3 min with a 100 ms ALSA ring (`correction=none`): 32 ms over 30 min | `HL:386-389` | measured (3 min); 30-min figure derived |
| Capture-side cost | M11: a growing per-file CPU cost raises the chance of a capture gap at 4K (every drop in the erased NVMe run was a capture gap) | slowdown plan §3 M11 | unconfirmed; the 30-min 4K 25 fps take with the split knob on and off is the named test |

## 5. The wear record, checked

| Reading | Data Units Written | TB (x 512,000 B) | Source | Label |
|---|---:|---:|---|---|
| Corsair test card baseline, read 2026-11-02 18:5x (uptime 1,108 s) | 49,380,871 | 25.28 | `night-2026-11-01.md:106` (`percentage_used` 3 %, 334 power-on hours, 1,535 unsafe shutdowns, 103 thermal T1 transitions) | measured |
| after evening 1 (2026-11-02) | 51,995,905 | 26.62 (+1.34) | `findings-2026-11-02.md:70-71` | measured |
| after evening 2 (2026-11-03) | 53,634,400 | 27.46 (+0.84) | `handoff-drop-frames-tests.md:203` | measured |
| after evening 3 (2026-11-04 early) | (56.66 M implied) | 29.01 (+1.55) | `handoff-drop-frames-tier1.md:185` | measured (TB as written there) |
| after evening 4 (2026-11-04 late) | not recorded | "43 C, 3 % used" | `preregistration.md:783-784` | measured (no DU figure) |
| 2026-11-07 NVMe runs (Corsair and Kingston) | not on `origin/main` | erased | `longtakes-test-structure.md:10` | - |
| T7 SSD ladder (not the NVMe) | - | 5.9 TB, 189 takes, 20.1 h | `findings-longtakes-ssd-2026-11-07.md:5` | measured |

Implied endurance 25.28 / 0.03 = 843 TB (722-1011 TB for 2.5-3.5 %) is arithmetic on an integer percentage (derived, loose); the Corsair's
rated TBW is not in the KB (`nvme-4k-recipe-plan.md:58`). The campaign's test card is the Kingston (draft §12): the KB holds **no SMART
reading of it**. Per-evening cost of the record (0.84-1.55 TB) against the plan: a single 30-min HDR16 take is 0.75 TB; the SSD ladder's
5.9 TB and the slowdown plan's "about 3 TB in all" (unmerged branch, §7) bracket what a measure-not-search campaign costs.

## 6. The long-take budget statements, re-read (feasibility §1 and §2.4; slowdown plan §2-4; reanalysis)

- **Serial cycle** (B, 25 fps): 34.7-38.0 ms measured at 30 fps recording, i.e. +2.0 to +5.3 ms of margin at 40 ms, MARGINAL-INSIDE,
  derived from measured fps, no 25 fps window exists (`dng-chain-feasibility.md:69`). Superseded in part by evening 3: with TDN off the BE
  job is 5.9 ms (was ~37) and 27 fps holds for 3 min, 28 fps shows a second loss path (BE jobs of 79-105 ms), 30 fps ruled out even at FE
  depth 4 (`findings-2026-11-04.md:11-50`, `findings-evening4-supervised-2026-11-04.md:33-44`; measured, n = 1-2). Nothing in this budget
  grows with take length by the record; the SSD run's CPU slope (section 4) is the candidate coupling (M11, unconfirmed).
- **DRAM**: 5.20 GB/s linear (TDN on), 4.27 TDN off, Log 5.83 net against a 7-10 GB/s practical ceiling (estimated): 58-83 % for Log =
  MARGINAL (`:70`, derived/estimated). Log at 4K over a long take is unmeasured.
- **exFAT**: F4's "27-73 % of the period at 15,000 files" (c = 80-250 ns, estimated) is now 11 % + mappings (c measured 63.3 ns): the
  create at 45,000 files is 35 % of a 40 ms period, 51 % of 33.3 ms at 54,000 (derived from the measured fit). The reanalysis's c = 99 ns
  from the CPU slope is superseded by the probe (`probe-exfat-dir.md:63`, `reanalysis §4`).
- **Drive**: need 415 MB/s (HDR16 25 fps), 311 (Log); ceilings on the Corsair 733-759 MB/s direct `dd` for <= 5 s, 556-572 buffered, 525 for
  60 s, 437 at Gen 2 (measured); 3 x 600 s clean at 415 MB/s (C0101, A0, A1) plus #80 (`:73`); the pSLC knee and post-cache plateau never
  measured on this link (`:131`; F4 §4 step 1 asks for a 10-min `fio --direct=1 --size=400G`). For the Kingston every drive figure is
  **unmeasured** (draft §11 (3) says so correctly). A 30-min HDR16 25 fps take on the Corsair writes 747 GB = 75 % of the volume = one pass
  of the allocation cursor (derived): the "2.5-2.7 takes walk the cursor once" statement becomes "one take" at 30 min.
- **Stall cushion**: frames mode 16 x 40 ms = 640 ms at 25 fps; RAM mode 81 frames = 3.2 s at the measured 1,424 MiB budget (90 % stop), the
  budget being `0.6 x MemAvailable - 512 MiB` (`:75`, derived; `HL:871` measured 1289 of 1424 MiB). The SSD run saw budgets of 250-1283 MiB
  (1.6-17 s of input) because MemAvailable moved between 1270 and 2991 MiB (reanalysis §8, measured): fix the budget before comparing
  times to failure (slowdown plan 4.5; `[storage] buffer_ram_fraction 0.9`, `buffer_ram_floor_mb 256`).
- **Slowdown plan §2-4** (unmerged branch): three regimes of buffer_full (78 slow / 32 late / 8 stop-message; measured); the 4K drain on
  the T7 77-120 MB/s against 354 raw (the writer pattern, not the medium; measured); M1-M11 mechanisms with their tests; the "measure, do
  not search" method (the RAM buffer level as a meter: `drain_fps(t) = fps - d(buffer_used)/dt`; one 90-s take per configuration at 20-30 %
  above the expected capacity); camera-free probes first (directory probe ~10 MB, write-pattern matrix ~26 GB, paced 2K emulation 88-180 GB);
  then the split test (3 x 10 min vs 1 x 30 min), the knob A/B, an MLV control, one instrumented 30-min take per mode at 90 % of capacity;
  the unattended rules (gate, watchdog, 20 GiB free, lock file, resume). About 3 TB in all (§7) against 5.9 TB for the SSD ladder.

## 7. Cards and capacities (deliverable 1's denominators)

| Card | Volume bytes | Usable at 10 GB reserve | Source | Label |
|---|---:|---:|---|---|
| Corsair MP600 MINI 1 TB, serial A936B442006AC2, firmware ERFM11.1, exFAT 128 KiB clusters (the record's test drive in the NVMe slot) | 999,960,870,912 (931.3 GiB; "932 GB") | 989.96 GB | `night-2026-11-01.md:95`; `probe-exfat-dir.md:20-23`; `HL:703` | measured |
| Kingston SKC3000S512G ("477 GB" = 477 GiB by the runner's unit) | about 512.0e9 (476.9 GiB from 475.9 GiB free at 0.2 % fill) | about 502 GB | `longtakes-campaign-plan.md:19`; `longtakes.py:385`; erased run samples (git `242c0be`) | derived; df unconfirmed |
| Crucial P310 (owner's card, serial 25184FF10656; seen 2026-11-03) | not in the KB | - | `findings-2026-11-03.md:43`; `handoff-drop-frames-tests.md:208` | - |
| CFexpress shooting cards: Corsair (owner, 2026-11-08) | not in the KB | - | owner's message | unconfirmed in the KB (brand only from the owner) |

## 8. Open questions a 15- or 30-minute take answers for free (deliverable 5)

Each item names the KB page that leaves it open; "free" means the take's existing 1 Hz log and Core's stats line answer it without an
extra take, provided the runner records what the slowdown plan's 4.4 lists (`buffer_used`, `/sys/block/<disk>/stat`, Dirty/Writeback,
`media_trim_last_*`, Core CPU, temperatures).

1. **The NVMe thermal trajectory past 10 minutes and whether it plateaus under 82.9 C** at 410-500 MB/s with no cool-down: nothing longer than
   10 min exists (section 4; `findings-2026-11-04.md:46` "n too small"; feasibility §2.4's 60-85 C is a linear model). On the Kingston every
   temperature is new.
2. **Does the fill effect exist on a trimmed drive?** #78's last minute (94-97 %, before the dirty-limit change) is "fill or a `sync` residual"
   (`inspection-2026-11-02.md:523`); a fit-tier take that ends at 6 GiB free on a trimmed Kingston, and a 30-min HDR16 take ending at 75 % on
   the Corsair, answer it with the drive's own write latency per second.
3. **The allocation-cursor wrap under Core** (feasibility §2.4: "2.5-2.7 takes walk the cursor around the volume once"; the 10-30 stall came
   at 0.9 TB untrimmed): a 30-min HDR16 take on the Corsair writes 747-896 GB, i.e. one full pass, trimmed, in one take.
4. **The residual loss rate under `sync` and the five-take B6 criterion** ("done means" B6 = five 10-min takes on two boots, never run with TDN
   off + depth 4; `findings-2026-11-04.md:72`, `findings-evening4-supervised-2026-11-04.md:63`): one clean 30-min take bounds the per-frame
   rate below 1 in 45,000 and covers three B6 takes' worth of frames in one folder (length, not the boot count).
5. **Log at 4K over a long take** (feasibility §7 item 7; lever 13 "the one Log sample had the worst gap rate"; the erased Kingston run's
   "Log on fails in 2-3 s, unexplained"): a 15-min 4K HDR16+Log take settles whether Log is a 30-min lever on the NVMe, and the copy
   worker's LUT cost shows in Core's CPU.
6. **Whether Core's CPU rises with the folder on the NVMe too** (reanalysis §4 measured it on the T7; the erased NVMe run logged 49-54 ->
   63-64 %): the runner's `core_cpu_slope` on any long take; with the split knob on and off it separates the directory from the rest (M1, M11).
7. **The directory cost in the live system** (section 2: the probe gives the floor; F4's mapping term is estimated): the split A/B at 15 and
   30 min is the test; the one-folder arm's per-second write latency and `peak_queue` in its last 10 minutes are the reading.
8. **The trim trigger after a long clip's delete** (reanalysis §7: the >= 1 GiB-between-polls rule may not fire after slow unlinks; the probe
   says unlinks are 5 us each on this kernel): Core's `media: trim` line after the runner deletes a 45,000-file clip, read before the next take.
9. **Does anything list the live clip folder during a take?** (feasibility §7 item 13; the probe saw a 68 ms create burst from one `ls`
   under the same lock, `probe-exfat-dir.md:37-40`): a long take's per-second create-latency tail shows readdir bursts if the touch UI or
   WebUI walks the folder.
10. **The stop path after a long take**: the sync thread ends before the drain and the stall detector can mark a healthy take `media_removed`
    (reanalysis §5, probable; M7): the stop of every long take, with Dirty/Writeback sampled, confirms or refutes it at no cost.
11. **Audio drift and the WAV-vs-DNG count over 30 min** (`HL:386-389` +18 ppm over 3 min; `HL:889` the DNG+WAV check): every long clip gives
    the 30-min drift and a second drop count for free.
12. **The time-left estimate's accuracy over a long take** (T21/T30 fitted drift, `HL:468-488`; 16-bit time-left corrected to 37 min): the
    clip's planned vs recorded seconds against the pre-take estimate.
13. **Whether A0's result repeats** ("Not yet known: whether the take stays clean on a second and third run; behaviour after more than one
    card of writing with Core's own trim", `HL:751-754`): back-to-back long takes with no cool-down are exactly that.

Not answered by a take: the cold-cache unlink cost (needs a reboot; probe step 4, folder still on the Corsair test card), the drive's
post-pSLC plateau in isolation (fio, Core stopped), the exFAT block size (`blockdev --getss`), `vwc` (FLUSH relevance), the Kingston's SMART
baseline (one `nvme smart-log` before the campaign), and the Kingston volume's df -B1 (one command at S0).

## 9. Sources read

`working/drop-frames/night-2026-11-01.md` (:18-30, 76-118); `lessons/hardware-log.md` (:51-63, 97-122, 136-146, 317-326, 378-393, 582-596,
640-649, 701-778, 813-870, 899-906); `working/drop-frames/README.md` (:119, 150-215, 240-260, 405-416); `working/sensor-capabilities.md`;
`architecture/drivers.md` (:130-145, 200-240); `working/compare-raw/c1-probe-compare.md` (:25-38, 127-131, 139-147, 173, 219); `fork-log.md`
(imx585 rows :25, 85, 119, 135-138, 147, 175-195, 213-215, 252-267); `working/drop-frames/nvme-campaign/probe-exfat-dir.md`;
`working/drop-frames/tests-2026-11/findings-2026-11-04.md`; `.../findings-evening4-supervised-2026-11-04.md`; `.../findings-2026-11-02.md:56, 70-73`;
`.../findings-2026-11-03.md:43`; `.../takes.md`; `.../findings-longtakes-ssd-2026-11-07.md`; `.../longtakes-ssd-2026-11-07/results.md` (:1-27,
pass_30min rows); `working/drop-frames/longtakes-campaign-plan.md`; `working/drop-frames/longtakes-test-structure.md` (:1-32, 52-66, 124-145);
`working/drop-frames/nvme-4k-recipe-plan.md:20-62`; `working/drop-frames/inspection-2026-11-02.md` (:20-50, 60-68, 85, 120, 201-211, 515-530);
`working/dng-chain-feasibility.md` (:60-83, 106-146, 165-168, 255-262, 374-419); `working/dng-chain/F/F4.md` (:18-41, 74-125);
`working/dng-chain/F/V-F4.md` (rows 10, 12, 14, 16-19, E1); `working/dng-chain/S1.md` (:58-73, 83-100, 386-390); `working/dng-chain/R8.md:56-66`;
`working/handoff-drop-frames-tests.md:198-206`; `working/handoff-drop-frames-tier1.md:180-190`; `working/drop-frames/tests-2026-11/preregistration.md:778-790`;
`working/tools/longtakes.py` (:11, 372-392, 783, 905-942); unmerged branch `origin/claude/practical-johnson-he481b`:
`working/drop-frames/storage-slowdown-plan.md` (§1-7) and `working/drop-frames/tests-2026-11/reanalysis-longtakes-ssd-2026-11-08.md`; git
`242c0be` (erased first run): rig line and one samples row only; `scratchpad/research/R2-lever-inventory.md` §3 (as the task named it).
