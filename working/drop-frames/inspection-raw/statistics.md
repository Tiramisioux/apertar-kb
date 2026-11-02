# Drop-frames 2026-11-01: statistics and experimental design

Inspection part "statistics and experimental design", written 2026-11-01 from the KB files only (nothing run on the Pi).
Status words: **confirmed** (read in source / journal, or arithmetic on recorded numbers), **measured** (numbers real,
reading not agreed), **probable** (inferred, reason given), **unconfirmed** (the measurement that settles it is named).

Sources: `working/drop-frames/takes-2026-11-01.md` (79 rows), `takes-2026-11-01.raw.txt` (390 journal lines),
`night-2026-11-01.md` §2-§3 (take -> configuration map, #80), `lessons/hardware-log.md` 2026-10-30 (trim, A0-A2) and
2026-11-01 (six entries), `working/tools/drop-frames-2026-11-01/take3.sh`, Apertar-Core `adac040` / `64bbbaa`,
cinemate `services/storage-automount/storage-automount.py`. The arithmetic is in `stats.py` next to this file
(pure Python, exact tests implemented by hand: no scipy on this machine).

## 0. Verdict in six lines

1. `sync` beat `writer` in every post-reboot take, and the kernel counters say the mode really changed what the kernel did
   (pgsteal_kswapd 3.0-3.45 M vs 47-58 k pages per 3 min, no overlap). **Measured.**
2. The frame-level tests (Fisher p = 9e-67) are not valid evidence: losses are clustered (variance/mean = 66 within the
   writer takes), so the unit is the take. At the take level the comparison is 3 vs 4 (or 4 vs 4 with #80) and the exact
   one-sided p is 0.057 (0.029 with #80); two-sided 0.11 (0.057). **Suggestive, not settled. Confirmed arithmetic.**
3. Every writer take preceded every sync take, so the comparison is also an order/uptime/Core-restart/fill comparison.
   Uptime and fill both ran *against* sync (sync takes were later and on a fuller drive), which helps the claim; the
   Core restart at 22:46, the audio-meter change at 23:00 and #80's empty cache do not. **Confirmed from the records.**
4. A smooth drift with uptime is **not supported**: inside the writer takes r = 0.65, p = 0.35 (n = 4, #72 < #71); across
   the first boot the 19:09-21:03 baseline takes are flat (1.2 %/h, p = 0.25) and the rise is a step to 11-18 % at
   22:06-22:19, right after the 21:50 format (drive 12-35 % full), so it is not fill either. **Confirmed arithmetic.**
5. #78's last minute (18 of 25) is a regime change (P < 1e-12 under the first nine minutes' rate), coincident with
   94-97 % fill and about 0.9-1.0 TB written since the 21:50 format: the 2026-10-30 stall zone, but without that stall's
   signature (queue 2/12, all losses capture gaps). Fill vs cumulative-writes-since-trim vs reclaim is not separable
   from this one take. **Measured; the per-second log settles it.**
6. The A0 take (2026-10-30: writer, UI running, trimmed drive, 10 min, 0 lost) remains the strongest counter-example to
   "writer mode loses frames"; the mode is at most one factor in an interaction with the UI's drawing (UI stopped under
   writer: 0, 0, 2 lost at 19:13, 19:51, 22:00). **Confirmed from the records.**

## 1. Dataset of comparable takes

Inclusion: 3840x2160 Clear HDR 16-bit uncompressed cDNG at 25 fps (journal `format=SRGGB16 storage_bits=16`,
`compression=none`), duration >= 60 s, touch UI running and drawing the live picture, WebUI closed, no build on the Pi.
Excluded with the reason: #4 (WebUI open), #6/#7 (another session compiled on the Pi), #35/#36/#60 (`QSG_RENDER_TIMING`
takes, 24 s), #37 (aids off by mistake, WebUI connected), #47 (48 s), #61 (WebUI open), #76 (29 s, Patrik editing the
ladder in the WebUI), the 20-31 s takes #11, #16, #52, #56, #57, and the 12.5 fps / 1080p takes #18, #19 (other data rate).

Column notes. *Up* = minutes since the boot (boot 1: Core's first journal line is 18:55:36, hardware log says "up 10 min"
at 19:09, so boot 18:55-18:59; boot 2: 22:27). *Fill* = estimate from the journal's `enqueued` counts at 16.6 MB per
4K 16-bit frame (3840 x 2160 x 2 bytes; stride 7680, `camera configured` lines), lossless taken as 8 MB, COMP1 12.4 MB,
1080p 4.15 MB, pre-roll clips deleted; boot 1's start fill is unknown (the drive had been trimmed, not necessarily
emptied), so boot-1 fill is written as "+GB since 18:55". The two formats are in the journal as pre-rolls with
`reason=format` at 21:50:55 and 23:13:03 (**confirmed**). *Lost* = `dropped_gap_estimate` (capture gaps, each one
frame; CameraController.cpp 9896-9924 in `adac040`: a sensor-timestamp gap > 1.5 periods counts round(dt/period) - 1).
All rows: `dropped_queue_full=0`, `peak_queue=2/12` (journal `recording stats` lines).

### 1a. Boot 1 (18:55-22:26), `APERTAR_DNG_DONTNEED` = `writer` (the default of `64bbbaa`, CdngEncoder.cpp:93)

| # | Clock | Up (min) | UI switches / setup | Dur s | Written | Lost | Lost % | Fill (est.) | Comparable to baseline? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 3 | 19:09 | 14 | baseline (Core `4b2eeac`, UI `41ff827`), peaking + zebra on | 60 | 1389 | 104 | 6.97 | +7 GB | strict |
| 15 | 19:46 | 51 | baseline, new build (Core `64bbbaa`, UI `68e1a41`) | 60 | 1381 | 113 | 7.56 | +150 GB | strict |
| 20 | 20:01 | 66 | HDMI cable out, UI kept drawing | 58 | 1367 | 77 | 5.33 | +190 GB | loose |
| 22 | 20:04 | 69 | camera thread `SCHED_FIFO` 40 | 60 | 1402 | 92 | 6.16 | +213 GB | loose (no effect found) |
| 28 | 20:18 | 83 | `QT_QPA_EGLFS_SWAPINTERVAL=2` (ignored) | 60 | 1363 | 130 | 8.71 | +296 GB | loose |
| 29 | 20:20 | 85 | `QT_QPA_EGLFS_SWAPINTERVAL=4` (ignored) | 60 | 1400 | 95 | 6.35 | +319 GB | loose |
| 30 | 20:25 | 90 | `APERTAR_UI_PREVIEW_RECORDING_FPS=0` (preview held) | 60 | 1498 | 0 | 0.00 | +342 GB | no (UI not drawing the picture) |
| 31 | 20:28 | 93 | `APERTAR_UI_PREVIEW_RECORDING_FPS=12` | 60 | 1452 | 43 | 2.88 | +367 GB | no |
| 32 | 20:31 | 96 | peaking + zebra off | 61 | 1470 | 25 | 1.67 | +391 GB | no |
| 33 | 20:34 | 99 | peaking on, zebra off | 60 | 1337 | 156 | 10.45 | +416 GB | near |
| 34 | 20:41 | 106 | `APERTAR_PREVIEW_PEAKING=fast` | 60 | 1363 | 132 | 8.83 | +438 GB | loose (no gain found) |
| 38 | 20:55 | 120 | audio meter off | 60 | 1362 | 133 | 8.90 | +478 GB | loose |
| 39 | 20:58 | 123 | `fast` + `APERTAR_PREVIEW_DIRECT=1` (a no-op) | 60 | 1413 | 81 | 5.42 | +500 GB | loose |
| 41 | 21:03 | 128 | Core `APERTAR_RAW_CAMERA_BUFFERS=12` | 60 | 1332 | 158 | 10.60 | +524 GB | loose (no effect found) |
| 44 | 21:12 | 137 | `APERTAR_PREVIEW_PEAKING=cpu` | 61 | 1437 | 58 | 3.88 | +546 GB | no |
| 46 | 21:36 | 161 | `APERTAR_PREVIEW_PLANE=1` | 60 | 1500 | 0 | 0.00 | +608 GB | no |
| 48 | 21:39 | 164 | plane | 110 | 2688 | 53 | 1.93 | +653 GB | no |
| 49 | 21:42 | 167 | plane + `cpu` | 180 | 4362 | 141 | 3.13 | +697 GB | no |
| 50 | 21:46 | 171 | plane | 180 | 4348 | 154 | 3.42 | +770 GB (-> 841 GB, 90 % if empty at 18:55) | no |
| *format 21:50:55* | | | | | | | | 0 | |
| 58 | 21:56 | 181 | plane, peaking + zebra off | 181 | 4179 | 325 | 7.22 | 1 -> 9 % | no |
| 62 | 22:10 | 195 | v3d IRQs 173/174 on CPU2, WebUI closed | 181 | 3686 | 816 | 18.13 | 19 -> 26 % | loose |
| 64 | 22:15 | 200 | fresh Core (restart 22:14), IRQs back on CPU0-3 | 180 | 4003 | 500 | 11.10 | 26 -> 33 % | strict |
| 65 | 22:19 | 204 | the same, vmstat counters read | 61 | 1237 | 256 | 17.15 | 33 -> 35 % | strict |

Controls, UI not drawing, same mode and boot (writer): #5 19:13 UI stopped 0/1500; #17 19:51 UI stopped 0/749 (31 s);
#27 20:14 UI frozen with `SIGSTOP` for 50 of 58 s: 1/1450; #59 22:00 UI stopped 2/1493 (0.13 %). **Confirmed** from the
takes table and night report §3.

### 1b. Boot 2 (22:27-), `take3.sh`, UI `c13b846` with no switch, peaking + zebra on, audio meter off until 23:00 then on

| # | Clock | Up (min) | Mode | Dur s | Written | Lost | Lost % | MemFree before | pgsteal_kswapd | low-wmark hits | Fill (est., no deletions) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 69 | 22:28 | 1 | writer | 181 | 4506 | 1 | 0.02 | fresh boot | not read | - | 35 -> 43 % |
| 70 | 22:32 | 5 | writer | 180 | 4469 | 34 | 0.76 | 300 MB | 3.45 M | 1805 | 43 -> 51 % |
| 71 | 22:36 | 9 | writer | 180 | 4349 | 153 | 3.40 | 275 MB | 3.04 M | 948 | 51 -> 59 % |
| 72 | 22:40 | 13 | writer | 181 | 4430 | 71 | 1.58 | 327 MB | 3.02 M | 990 | 59 -> 67 % |
| *Core restart 22:46 with the `/run` drop-in; pre-roll #73 (its delete triggers a trim: Core README "Trim the recording drive")* | | | | | | | | | | | |
| 74 | 22:46 | 19 | sync | 181 | 4505 | 0 | 0.00 | 646 MB | 47 k | 8 | 67 -> 75 % |
| 75 | 22:50 | 23 | sync | 181 | 4509 | 0 | 0.00 | 507 MB | 58 k | 11 | 75 -> 83 % |
| 78 | 23:02 | 35 | sync, audio meter on | 602 | 14998 | 25 | 0.17 | 788 MB | 586 k (10 min) | 78 | reported ~70 -> 97 %; no-deletion sum 85 -> 112 % |
| *format 23:13:03 (trimmed); sysctl 23:14* | | | | | | | | | | | 0 |
| 80 | ~23:14 | 47 | sync + dirty_bytes 1 GiB, dirty_background_bytes 256 MiB, min_free_kbytes 64 MiB | ~600 | 15025 | 0 | 0.00 | 2758 MB | 0 | 0 | 1 -> 26 % (reported) |

Fill inconsistency (**measured**): the no-deletion sum puts #78's end at 1,043 GB on a 932 GB drive, so about 140 GB of
clips (two 3-minute takes' worth) were deleted between 21:50 and 23:02 without a journal trace in the grep'd lines; the
report's "97 %" implies #78 started near 70 %. A delete through Core or the touch UI of >= 1 GiB triggers a trim (README),
so the drive's trim state at 23:02 is **unconfirmed**: `journalctl -u apertar-core -b -1 --no-pager | grep -E "media: trim|delete"`
on the Pi settles it (a `result=trimmed` line between 21:51 and 23:01 means the NAND was clean going into #78).

#80's MemFree of 2,758 MB (vs 300-800 MB for every other take) is the 23:13 format: deleting the files freed their page
cache. So #80 differed from #78 in three ways at once: the dirty limits, the empty drive, and an empty cache at the start
(**confirmed** from the table; the cache fills again within seconds of a 415 MB/s take, so this third difference is
probably small, **probable**).

## 2. `sync` vs `writer`: the tests, and why they are not the answer

### 2a. Frame-level exact tests (the unit is a frame)

| Comparison | writer | sync | Fisher two-sided | Fisher one-sided W > S | Poisson conditional (binomial) one-sided | Rate ratio (95 % CI) |
| --- | --- | --- | --- | --- | --- | --- |
| #69-#72 vs #74, #75, #78 | 259 / 18,013 (1.44 %) | 25 / 24,037 (0.104 %) | 8.6e-67 | 7.4e-67 | 1.9e-66 | 13.8 (9.2-20.8) |
| the same + #80 | 259 / 18,013 | 25 / 39,062 (0.064 %) | 2.2e-99 | - | 7.1e-99 | 22.5 (14.9-33.9) |

These p-values assume that each frame is an independent Bernoulli trial with one rate per arm. They are not: within the
four writer takes the per-take counts are 1, 34, 153, 71 (mean 64.8, variance 4,279, dispersion var/mean = **66**; a
Poisson take with mean 64.8 gives 1 or fewer with probability 5e-27). A moment-fit negative binomial has size k = 1.0,
i.e. a nearly geometric spread: the take, not the frame, is the sampling unit. **Confirmed arithmetic.**

### 2b. Take-level exact test (Mann-Whitney / permutation on lost % per take)

| Arms | writer takes (lost %) | sync takes (lost %) | rank sum (sync) | one-sided p | two-sided p | arrangements |
| --- | --- | --- | --- | --- | --- | --- |
| 4 vs 3 | 0.02, 0.76, 3.40, 1.58 | 0.00, 0.00, 0.17 | 7.0 (min 6) | **0.057** | 0.114 | 35 |
| 4 vs 4 (+#80) | the same | 0.00, 0.00, 0.17, 0.00 | 11.0 (min 10) | **0.029** | 0.057 | 70 |

The arms are not completely separated: #69 (writer, 0.02 %) sits below #78 (sync, 0.17 %). With complete separation the
smallest two-sided p is 0.10 for 3 vs 3, 0.029 for 4 vs 4, 0.0079 for 5 vs 5, 0.0022 for 6 vs 6. Sensitivity: under the
writer takes' own negative binomial, two clean 3-minute takes have probability 2e-4 and a 10-minute take with <= 25 lost
0.11 (joint 3e-5), but a k fitted to four points has no useful confidence interval, and the empirical "clean writer
take" rate is 1 in 4 (#69), under which two clean sync takes are 1 in 16. **Confirmed arithmetic; reading: suggestive.**

### 2c. Why even a significant p would not be the whole answer

- **Order.** Every writer take came before every sync take (22:28-22:43 vs 22:46-23:24). Any monotone change in the
  system (uptime, Core restart at 22:46, drive fill, drive and SoC temperature, the audio meter switched on at 23:00)
  is perfectly confounded with the mode. Under the night's own hypothesis (pressure builds with uptime) the later takes
  should have been *worse*; they were better, so uptime cannot be the alternative explanation for the sync result. But
  the Core restart at 22:46 is: it is the only other thing that changed between #72 and #74. In boot 1 a fresh Core
  (#64, 22:15) did not help (11.1 % after #62's 18.1 %, then #65 17.2 %), which argues against the restart, with n = 1.
- **Fill ran the other way too.** By the no-deletion count the writer takes ran at 35-67 % fill and the clean sync takes
  at 67-83 %; #80 ran at 1-26 %. Fill below ~85 % did not help writer and did not hurt sync. (Boot 1: #46-#50 at an
  estimated 65-90 % fill lost 0-3.4 %, less than the baseline, with the plane switch on.) **Probable** (estimates).
- **#69.** The first writer take lost 1 frame in 4,507 at 1 minute of uptime, with no vmstat read. Writer mode is not
  sufficient for losses; something has to build up first. The report reads that as the cache filling, which takes
  seconds at 415 MB/s, not minutes; what builds over 5-13 minutes is not identified (**unconfirmed**: the per-second
  vmstat/meminfo log of a writer take from a fresh boot shows whether MemFree, nr_file_pages or pgsteal cross a level
  between minutes 1 and 5).
- **A0.** 2026-10-30, Core `a40112a` (per-frame DONTNEED hard-coded, the same call), touch UI running, trimmed drive,
  10 minutes, 0 of 15,001 lost, the UI up for hours (hardware-log 2026-11-01 first entry; the 2026-10-31 RTC entry says
  boot-time clocks were wrong, so the exact uptime is **unconfirmed**). Whatever makes writer lose frames on 11-01 was
  absent on 10-30 with the same write path. The mode can only be a factor in an interaction with something that changed
  since (UI commits since `ea44bd7`, Core's preview feed), not the root cause on its own.
- **UI stopped under writer is clean at any uptime**: #5 (19:13) 0, #17 (19:51) 0, #59 (22:00, 3 h) 2 lost. So the
  kswapd activity of writer mode (3 M pages per take, presumably present in those takes too: **unconfirmed**, vmstat was
  not read then) does not lose frames by itself. The claim that holds is "writer-mode reclaim AND the UI drawing", and
  the test in §4 is a test of that interaction with the UI held constant.
- **The kernel counters are the strong part.** pgsteal_kswapd 3.02-3.45 M (writer) vs 47-58 k (sync) and low-watermark
  hits 948-1805 vs 8-11 do not overlap and differ 50-70x; three takes per arm with that gap would be significant under
  any reasonable noise model. **Measured.** They prove the mode changed the kernel's reclaim behaviour, not that reclaim
  caused the capture gaps. Note also the accounting gap: a 3-minute take writes ~18 M pages but kswapd stole ~3.4 M; who
  freed the rest (direct reclaim by the writer threads, or the writer-mode DONTNEED succeeding on pages already clean)
  is **unconfirmed**; take3.sh read `pgscan_direct` and `allocstall_*` but the report does not give them.

### 2d. Drift with uptime: is it supported?

Within the writer takes after the reboot (uptime 1, 5, 9, 13 min; lost 1, 34, 153, 71): Pearson r = 0.65, slope 8.2
lost per minute of uptime per 3-minute take, t-test p = 0.35, exact permutation p = 0.33; Spearman rho = 0.80, p = 0.33.
Not monotone (#72 < #71). **Not supported** at n = 4 (**confirmed arithmetic**).

Across boot 1, baseline-equivalent takes (strict #3, #15, #64, #65; loose #20, #22, #28, #29, #34, #38, #39, #41, #62):

| Set | n | Pearson r | slope | p |
| --- | --- | --- | --- | --- |
| all 13, 19:09-22:19 | 13 | 0.80 | 3.3 %/h | 0.001 (t) |
| strict 4 | 4 | 0.85 | 2.4 %/h | 0.125 (exact) |
| 19:09-21:03 only | 10 | 0.40 | 1.2 %/h | 0.25 (t) |

Means: 19:09-21:03 7.5 % (range 5.3-10.6); 22:10-22:19 15.5 % (11.1-18.1). The significant slope over the whole evening
is carried by the last three takes: the data show a **step** between 21:03 (#41, 10.6 %) and 22:06 (#61, 14.3 % with the
WebUI open; #62 18.1 %), not a smooth drift. **Confirmed arithmetic.** What sits in that gap: Patrik's own takes (#52-#57),
the 21:50 format (page cache of the deleted clips freed, drive emptied and trimmed), the plane takes with the UI restarted
under drop-ins, a Core restart at 22:14. The step happened on a 1-35 % full, freshly trimmed drive, so **fill is excluded
as the cause of the boot-1 rise** (**confirmed** from the format time). Compare #32 (20:31, aids off, no plane) 1.67 %
with #58 (21:56, aids off, plane) 7.22 %: the whole level moved up by 5-8 points. A monotone drift with uptime is at most
**probable**; a regime change around 21:50-22:06 fits the numbers as well, and the within-boot-2 data cannot tell them apart.

## 3. Take #78: is the last-minute rise fill alone?

Per-minute increments (from the cumulative 0, 0, 3, 3, 3, 3, 5, 5, 7, 25): **0, 0, 3, 0, 0, 0, 2, 0, 2, 18**.

| Minute | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lost | 0 | 0 | 3 | 0 | 0 | 0 | 2 | 0 | 2 | 18 |
| fill at end (from 70 %, +2.67 %/min) | 73 | 75 | 78 | 81 | 83 | 86 | 89 | 91 | 94 | 97 |
| written since 21:50 format at end (no-deletion count, GB) | 819 | 844 | 869 | 894 | 919 | 943 | 968 | 993 | 1018 | 1043 |

- Minutes 1-9: 7 lost, 0.78 per minute, no trend (Spearman rho = 0.26, p = 0.59). Minute 10: 18. P(>= 18 | Poisson 0.78)
  < 1e-12; even under the take's overall 2.5/min, P(some minute >= 18) = 2e-9. The last minute is a different regime,
  not the tail of a gradual rise. **Confirmed arithmetic.**
- A linear fill effect would show minutes 7-9 (89-94 %) well above minutes 1-3; they are 2, 0, 2 against 0, 0, 3. If fill
  matters, it is a threshold above ~94 % (or about 0.9-1.0 TB written since the last trim), not a slope. **Probable.**
- The 2026-10-30 prior says the NVMe stalls once about 0.9 TB has been written since the last trim, with the filesystem
  mostly empty (files deleted between runs): a NAND state, not a filesystem-fill effect; its signature was writer threads
  stuck 5-10 s in exFAT metadata calls and 28-77 % **queue-full** drops. #78 shows the opposite signature: `peak_queue=2/12`,
  `dropped_queue_full=0`, all 25 losses capture gaps (journal 23:12:03). So the 10-30 stall as such did not happen. But A2
  (10-30) showed the kernel's writeback behaviour alone can cost 10 % at capture with the queue at 1/12, so "drive slows
  near full -> pages stay dirty/under writeback longer -> more reclaim while the UI draws -> capture gaps" is a plausible
  chain and the counters support pressure growing during #78: pgsteal_kswapd 586 k over 10 min = 59 k/min against 16-19 k/min
  in #74/#75 (3x per minute), low-watermark hits 78 against 8-11. **Probable**; whether the reclaim was concentrated in the
  last minute is **unconfirmed** (the take's counters are totals).
- exFAT near-full allocation cost (bitmap scans for free clusters get longer as free space shrinks) is a second candidate
  for a > 94 % threshold; the exfat driver is not in the local kernel checkout, so **unconfirmed**.
- #80 does not separate anything: it changed the dirty limits, the fill (1-26 %), the trim state (format 23:13) and the
  starting cache (MemFree 2,758 MB) at once, and its 0 of 15,025 is consistent with "sync on an empty drive is clean"
  (as #78's minutes 1-2 and #74/#75 already were) with or without the limits.

What separates fill from the mode and from the limits (details in §5): run `sync` without limits on an empty trimmed
drive for 10 minutes (if 0-5 lost and flat: #78's 18 were the drive's state, not the mode's residual); run `sync` with the
#80 limits starting at 70 % fill (if minute 10 spikes again: the limits do not cure the near-full regime); fill the
filesystem without writing the NAND (`fallocate`, if exFAT accepts it) to split filesystem fill from NAND state; log
vmstat and the NVMe's write latency per second so the spike's cause is seen, not inferred.

## 4. Power, and the interleaved A/B

### 4a. Frames (assuming independent frames: the optimistic bound)

| Question | Frames | Minutes at 25 fps |
| --- | --- | --- |
| 0 lost bounds the rate below 0.05 % at 95 % (rule of three: 3/n; exact ln 0.05 / ln(1 - p)) | 5,990 (6,000) | 4.0 |
| 0 lost bounds below 0.02 % | 14,977 | 10.0 |
| 0 lost bounds below 0.01 % | 29,956 | 20.0 |
| tell 0.17 % from 0.05 %, alpha 0.05 two-sided, power 80 % (two proportions) | 11,977 per arm | 8.0 per arm |
| the same, power 90 % | 16,033 per arm | 10.7 per arm |

What one take buys: a 10-minute take expects 25.5 events at 0.17 % and 7.5 at 0.05 %; a cut at 12.5 misclassifies 0.2 %
of 0.17 %-takes and 4.3 % of 0.05 %-takes (Poisson). A 3-minute take expects 7.6 vs 2.2; a cut at 3.5 misclassifies 5 %
and 19 %: 3-minute takes cannot answer the residual-rate question. For writer vs sync at the observed rates a 3-minute
take expects 65 vs 4.7 events and a 10-minute take 216 vs 16: either length separates the arms when the arms behave as
on 11-01. A single 3-minute take with 0 lost bounds the rate at 0.067 % (not 0.05 %), a single 10-minute take at 0.02 %.

Caveat that overrides the table: losses are clustered in time (dispersion 66; 18 of #78's 25 in one minute), so frames
are not independent and the honest unit is the take, with the minute as the within-take profile. Take-level power: with
complete separation, 4 vs 4 takes gives exact two-sided p = 0.029, 5 vs 5 0.0079, 6 vs 6 0.0022; one overlapping take
(a #69) costs about a factor 2-3 in p. The design below therefore has 8 takes with an extension rule to 12.

### 4b. The interleaved A/B that settles writer vs sync in one evening

**Question.** With the UI drawing (peaking + zebra on, audio meter in one fixed state), does `APERTAR_DNG_DONTNEED=writer`
lose more frames at capture than `sync`, on the same boot, in alternating order, with the drive reset to the same state
before every take?

**Fixed for all takes.** Core: the running binary, mode set *explicitly* by a `/run` drop-in in both arms (never rely on
the default: it is `writer` in `64bbbaa` and `sync` in `adac040`, CdngEncoder.cpp:86-94), `APERTAR_MEDIA_SYNC_MS` at its
default 1000 (sync needs the sync thread, CameraController.cpp:4324-4328), `APERTAR_DNG_WRITEBACK` default, stock sysctl
(`dirty_ratio` 20, `dirty_background_ratio` 10, `min_free_kbytes` 16384: the limits are §5's factor, not this test's). UI
`c13b846` with no switch, peaking + zebra on, audio meter in one state for all 8 takes (write which). 4K Clear HDR 16-bit
uncompressed 25 fps, ladder off for the take (`take3.sh` does this), WebUI closed (the script refuses otherwise), no build
on the Pi (checked before and after). 10-minute takes.

**Order.** Toss a coin for which mode is A. Block 1: A B B A. Block 2: B A A B. Reboot before each block (so each block's
first take is at ~1-2 minutes of uptime, once per arm). ABBA/BAAB cancels a linear drift inside each block and the
first-position effect across blocks (#69 was a first-after-boot take).

**Reset between takes (every take, both arms, in this order).**
1. Delete the previous clip and trim: `rm -rf /media/RAW/cDNG_*` then `sudo fstrim -v /media/RAW` (Core's own trim runs
   only on deletes it sees, so trim by hand; 0.5 s for the whole drive per the README), `df /media/RAW` -> record.
   Every take then starts on an empty, trimmed drive and ends at ~27 %: fill is removed as a factor here.
2. Write the mode drop-in and restart Core: `/run/systemd/system/apertar-core.service.d/dontneed.conf` with
   `[Service]\nEnvironment=APERTAR_DNG_DONTNEED=<writer|sync>`, `sudo systemctl daemon-reload && sudo systemctl restart apertar-core`.
   Restart Core before **every** take, including when the mode does not change, so the restart is not confounded with the
   arm (it was, on 11-01). Wait for the start pre-roll to finish (~5 s; its delete triggers Core's trim, harmless here).
3. Verify the arm from the process, because Core logs nothing on a valid value:
   `tr '\0' '\n' < /proc/$(systemctl show apertar-core -p MainPID --value)/environ | grep APERTAR_DNG_DONTNEED`.
4. Cache: the delete in step 1 already frees the clip's cached pages, so every take starts with MemFree in the GB range
   (as #80 did). Record `grep -E '^(MemFree|Cached|Dirty|Writeback)' /proc/meminfo`; do not `drop_caches` (not needed, and
   it adds a step Patrik's shooting never has). Since a 415 MB/s take fills the cache in seconds, the within-take
   dynamics are what the test measures.
5. Temperature: `vcgencmd measure_temp` and the NVMe (`cat /sys/class/nvme/nvme0/device/hwmon*/temp1_input` or
   `sudo nvme smart-log /dev/nvme0 | grep temperature`); start only below 55 C on the drive (10-30 practice: 34 -> 54 C
   over a 10-minute take).
6. `uptime -p`, `ps -eo cmd | grep -E 'cc1plus|gmake|cmake'`, `ss -tnH state established '( sport = :8000 )' | wc -l`.

**Record during the take**, at 1 Hz to tmpfs (`/dev/shm/take-N.log`, never to `/media/RAW`), from `/proc` only (cheap):
`nr_file_pages nr_dirty nr_writeback pgsteal_kswapd pgscan_kswapd pgsteal_direct pgscan_direct allocstall_normal
allocstall_movable kswapd_low_wmark_hit_quickly kswapd_high_wmark_hit_quickly pageoutrun` from `/proc/vmstat`;
`MemFree Dirty Writeback` from `/proc/meminfo`; the `some` and `full` lines of `/proc/pressure/memory` and
`/proc/pressure/io` (if the kernel has PSI: `test -r /proc/pressure/memory`); the write-ticks field of
`/sys/block/nvme0n1/stat` (field 8; its per-second delta divided by the write-count delta is the mean write latency,
which shows a slowing drive); and every 10 s `recording_dropped_frames` from `get_state` (take3.sh does this per minute;
10 s gives 60 points per take and costs one socket call). The journal gives the gap events too, but only the first, every
30th and multi-frame ones (CameraController.cpp:9916-9917), so the poll is the per-minute source.

**Primary endpoint.** Lost frames at capture per take (`dropped_gap_estimate` from the journal's `capture stats` line,
cross-checked against written vs 25 x seconds). Secondary: per-take delta of pgsteal_kswapd, pgscan_direct, allocstall_*,
low-watermark hits, PSI `full total`; the per-10-s loss profile; the NVMe latency profile.

**Analysis and stopping rule, fixed in advance.**
- After 8 takes: exact permutation test on the per-take counts (4 vs 4), one-sided (sync < writer). Complete separation
  gives p = 0.014 one-sided / 0.029 two-sided: **stop, the claim holds** if in addition pgsteal_kswapd separates by >= 10x
  (the mechanism marker must move with the mode; if it does not, the drop-in did not take and the run is void).
- One overlapping take (a writer take <= the best sync take, or a sync take >= the worst writer take): **extend by one
  block of 4** (A B A B after a reboot) to 6 vs 6 (complete separation then p = 0.0022; one overlap still < 0.02). Report
  the overlapping take with its counters: a clean writer take with 3 M pgsteal says reclaim alone does not lose frames.
- No separation (median sync >= median writer, or both arms clean): stop at 8; the 11-01 difference was order, the Core
  restart, or chance, and the DONTNEED default change stands on the counters alone (less reclaim is still worth having).
- Residual rate under sync: pool the sync takes' frames (4 x ~15,000 = 60,000; 0 events bounds the rate below 0.005 %,
  independence assumed; report also "clean takes of n" and the per-minute maximum).

**Wall clock.** Per take: mode drop-in + restart + pre-roll 1 min, take3.sh mode set-up 0.5 min, record 10 min, stop and
stats 0.3 min, delete + fstrim 1-2 min, cool-down to 55 C 1-2 min: about 15 min. 8 takes = 2 h, plus two reboots (3 min
each with sudo tickets) = **about 2 h 10 min**; the 12-take extension adds 1 h. With 3-minute takes (enough for writer vs
sync at the 11-01 effect size, useless for the residual) 8 takes are about 65 min.

## 5. A separate design: drive fill and trim state vs the DONTNEED mode vs the dirty limits

Three things are tangled in #78/#80: filesystem fill (exFAT near full), NAND state (bytes written since the last trim: the
2026-10-30 stall zone at ~0.9 TB), and the kernel knobs (mode; dirty limits). They are separable because fill and NAND
state can be set independently of each other:

- **FS full, NAND clean:** `sudo fallocate -l 650G /media/RAW/fill.bin` (allocates clusters without writing: seconds, no
  NAND writes; **unconfirmed** that the 6.12 exfat driver supports fallocate: the command's return says; fallback
  `dd if=/dev/zero of=/media/RAW/fill.bin bs=16M count=40000 oflag=direct` ~20 min, then `fstrim` so the *free* space is
  clean). Then a 10-minute take runs the fill from 70 % to 97 %, as #78 did.
- **FS empty, NAND dirty:** write >= 0.9 TB since the last trim (e.g. `dd` 900 GB ~28 min, or three 10-minute takes), then
  delete with `rm` (not through Core or the touch UI, whose deletes trigger Core's trim), with `APERTAR_MEDIA_TRIM=0` in the
  Core drop-in for this cell (otherwise the pre-roll's delete at the Core restart trims the drive). Verify no trim ran:
  `journalctl -u apertar-core -b | grep "media: trim"`.
- **Both:** the dirty-NAND state, then `fallocate`/`dd` to 70 % without a trim.
- Reset to clean: `rm`, `sudo fstrim -v /media/RAW` (0.5 s), or a format (also trims).

Cells, all 10 minutes, UI drawing as in §4, Core restarted and arm verified before each, same recording as §4 (the
per-second NVMe write latency is the key extra here: a near-full or untrimmed drive should show it, a memory effect not):

| Cell | Mode | Limits | FS fill at start | NAND | Question / what the result means |
| --- | --- | --- | --- | --- | --- |
| F0 | sync | off | empty | trimmed | baseline; replicates #74/#75 at 10 min. Clean (<= 5, flat): #78's 18 were the drive's state. 20+ spread evenly: a sync residual exists independent of fill |
| F1 | sync | off | 70 % (fill.bin) | trimmed | FS fill alone. Spike in minutes 9-10: exFAT near-full cost (or the sync residual grows with fill). Flat: filesystem fill is innocent |
| F2 | sync | off | empty | >= 0.9 TB written, untrimmed | NAND state alone under Core. Losses with high NVMe write latency and/or queue growth: the 10-30 effect reaches capture through writeback. Clean: Core's auto-trim is enough and 10-30's stall needs the old write path |
| F3 | sync | **on** (#80's) | 70 % | trimmed | the #80 knobs in #78's drive state. Clean through 97 %: the limits cure the near-full regime (then make them permanent via `APERTAR_MEDIA_TUNE`). Spike: fill beats the limits; cap the usable drive or trim/format policy instead |
| F4 | sync | on | empty | trimmed | #80 replicate; with F0 it isolates the limits on an empty drive (the two should agree if F0 is clean) |
| F5 | writer | off | empty | trimmed | A0 replicate on today's UI (A0 was this cell with the 10-30 UI and Core, 0 lost). Losses: the regression is on today's stack; clean: the §4 result was order/chance |

Order: F0, F3, F1, F4, F2, F5 (the two near-full cells not adjacent to each other; F2 last because its preparation
writes 0.9 TB and leaves the drive untrimmed: format afterwards). Each cell once first (6 x 15 min = 1.5 h plus F1/F3
fills 2 x 20 min with dd or seconds with fallocate, plus F2's 30 min of writing: **about 3 h**); repeat any cell whose
reading would change a decision (F3 above all) before acting on it. Decision rule per cell: "clean" = <= 5 lost and no
minute >= 3; "near-full effect" = minutes 9-10 carry > 60 % of the losses (as in #78: 18 of 25) with the NVMe write
latency rising in the same minutes; "memory effect" = losses spread across minutes with pgsteal/allocstall/PSI deltas
and flat drive latency.

Note on "CineMate-style" limits: cinemate's automounter sets, for NVMe, `vm.dirty_bytes` 1 GiB and
`vm.dirty_background_bytes` 256 MiB and also `vm.dirty_writeback_centisecs` 150 and `vm.dirty_expire_centisecs` 3000, and
does not touch `vm.min_free_kbytes` (storage-automount.py:111-112, 328-333; **confirmed** by grep). #80 used the two byte
limits plus a 64 MiB `min_free_kbytes` that is Apertar's own; if F3/F4 keep the limits, test the writeback/expire pair
and `min_free_kbytes` separately before making them permanent, or copy cinemate's set exactly and say so.

## 6. Measurements that would settle the open points (none run here)

| Open point | Command on the Pi | Reading |
| --- | --- | --- |
| Was the drive trimmed between 21:50 and 23:02 (did clips get deleted through Core/UI)? | `journalctl -u apertar-core -b -1 --no-pager \| grep -E "media: trim\|delete"` | a `result=trimmed` line after 21:51 means #78 ran on a clean NAND and its minute 10 is fill/exFAT, not the 10-30 zone |
| Does the reclaim in #78 concentrate in the last minute? | re-run F1 with the 1 Hz vmstat log | pgsteal/allocstall deltas per minute vs the loss profile |
| Does the drive slow near full / untrimmed? | 1 Hz `/sys/block/nvme0n1/stat` write ticks and count | mean write latency per second rising in minutes 9-10 (F1) or throughout (F2) |
| Who frees the 15 M pages per take that kswapd does not? | 1 Hz `pgsteal_direct pgscan_direct allocstall_*` in a writer take | large direct-reclaim deltas = the writer threads reclaim synchronously in `write()`; small = the DONTNEED call succeeds on already-clean pages |
| What builds between minute 1 and minute 5 after boot under writer (#69 vs #70)? | 1 Hz `MemFree nr_file_pages nr_dirty` from boot through two takes | the level that MemFree settles at and when; whether take 2 starts from a different state than take 1 |
| Is the arm what we think? | `tr '\0' '\n' < /proc/$(systemctl show apertar-core -p MainPID --value)/environ \| grep DONTNEED` | the value; Core prints nothing for a valid one (CdngEncoder.cpp:93 prints only on an invalid value) |
