# Can Apertar record drop-free at (A) 4K SDR 12-bit 50 fps and (B) 4K Clear HDR 16-bit 25 fps? (feasibility answer)

Written 2026-11-01 in a cloud session (Claude Code) for Patrik. Subject: Apertar-Core `claude/adoring-euler-n8zi0j` at `6ef0ddc`
(= `drop-frames` `92d0970` plus nine knob-gated commits) on the Pi 5 / CM5 rig, IMX585 at 891 MHz, CFexpress hat, Corsair MP600 Mini
(FW ERFM11.1) on PCIe Gen 3 x1, exFAT 128 KiB clusters. Sources: the feasibility brief `working/dng-chain/F/FEAS-BRIEF.md`, six analyst
reports `F1`..`F6` and six adversarial verifications `V-F1`..`V-F6` in `working/dng-chain/F/`, the earlier answer page
`working/dng-chain-answer.md` (sections 0, 2, 5, 6) and the kb's hardware log 2026-10-23 to 2026-11-01. Where a verification weakened or refuted a
report, this page carries the corrected number. Every number carries a label: **measured** (a log line), **derived** (arithmetic from measured
values), **estimated** (a model, named), **unverified**, or **web** (a public source), and its source (`F<n> §x`, `V-F<n>`, or `file:line`).
cinemate appears only as the reference point the operator raised, never as a goal.

**Status.** Nothing in this phase ran on the Pi: every verdict below is read from the record (takes up to 2026-11-01), from code at `6ef0ddc`
and upstream libcamera `c682979`, and from models whose weakest assumption is named. The Apertar libcamera fork is not local except as a
scratchpad clone at `6b0b49f` read by F1/V-F1; fork statements elsewhere are the kb's. "Drop-free" means zero capture gaps and zero queue drops
for at least 10 minutes. Mode (A) is 3840x2160 12-bit uncompressed cDNG at 50 fps (622 MB/s; the one counted take, T34 M3, ran the 3840x2076 crop
at 598 MB/s); mode (B) is 3840x2200 unpacked 16-bit at 25 fps (415 MB/s linear, 311 MB/s with Log).

## 0. Short answer

- **(A) 4K SDR 12-bit 50 fps, 10 min: NOT WITH THE CURRENT CONFIGURATION on the record; UNKNOWN for `6ef0ddc`.** The only counted 4K50 takes
  (T34 M3, 2026-10-28, build `4d5fdd1`, 3840x2076, two 60 s takes) lost 12 % as steady single-frame capture gaps with the queue at 2-3 of 12,
  unchanged with 8 raw buffers: a serial cycle of **22.7 ms against 20.0 ms, −2.7 ms** (derived from 44.0 fps delivered, `hardware-log.md:582-595`;
  F2 §1, V-F2 §5, V-F5 §1). No 4K50 take exists at 3840x2160, on a trimmed drive, longer than 60 s, or on any later build; the completion path of
  `6ef0ddc` is byte-identical to `4d5fdd1` apart from pre-roll bookkeeping and an off-by-default RT knob (direct diff, V-F5 row 14). Confidence:
  LOW either way.
- **(A) has two independent gates and both are open.** Cycle: the record brackets it at **−2.7 ms (M3) to ≥ +2.5 ms** (the 2026-11-01 pre-roll:
  115 frames at a measured 60.0 fps, 3840x2160 lossless, `d44b177`, 2 s, probably 8 raw buffers ⇒ mean cycle ≤ 17.5 ms; derived, V-F2 §3.2); the
  two models (F2: 10-14 ms; R9/L2 scaling: 19-20 ms, TDN on) disagree and cannot arbitrate (V-F2 §3.1). Storage: 622 MB/s against **733-759 MB/s**
  direct `dd` for ≤ 5 s inside the pSLC cache (measured, `T22.md:17`, `clearhdr-design.md:130`), **556-572 MB/s** buffered single `dd` (measured),
  **525 MB/s for 60 s** (the most Core has sustained, derived, `hardware-log.md:586-590`): no datum ≥ 600 MB/s longer than 5 s exists (V-F4 row 3);
  the exFAT create scan is estimated at 12-38 ms per file by the 30,000th file under a lock the writers share (F4 §2.3, V-F4: direction
  undetermined). A 10 min (A) take is **373 GB** and needs that much free (V-F6 E4).
- **(A) could become YES UNDER CONDITIONS** only after two measurements pass: a 60 s `be_cycle.py` window at 50 fps on `6ef0ddc` with the cycle
  median ≤ 20 ms (first with the default tuning, then with a tuning copy without `tdn`, the one lever of the deficit's size: estimated −4 to −11 ms,
  model-only), and a 10 min `fio --direct=1` write curve with Core stopped holding ≥ 700 MB/s. If the fio plateau is lower, 10-bit (518.5 MB/s) or
  3840x2076 (598.0 MB/s) is the storage-side fit; if the cycle does not move with TDN off, no configuration lever remains for (A) at 50 fps.
- **(B) 4K Clear HDR 16-bit 25 fps linear, 10 min: YES UNDER CONDITIONS, confidence MEDIUM.** Three of four 10-minute takes on trimmed or lightly
  filled drives were clean on October builds (C0101 15019/15019 on `114bfb9`; A0 15001, A1 15000 on `a40112a`; measured, `hardware-log.md:386,
  736-764`), all with the WebUI closed; the fourth (A2, 1491 one-frame gaps, `APERTAR_DNG_WRITEBACK=0`, speed ramp probably on, WebUI state
  unrecorded) is unexplained. The conditions are the A0 protocol: WebUI closed (or `APERTAR_WEB_PREVIEW_RECORDING_FPS=0`), drive trimmed, speed
  ramp off, first take after any reconfigure or reboot discarded, nothing else running on the Pi. Margin **+2.0 to +5.3 ms** at the A0 load
  (derived from the 30 fps L1/L2 cycle windows 34.7-38.0 ms, `hardware-log.md:210,225`; V-F2 §5), load-dependent: no 25 fps cycle window exists, and
  the four 2026-10-31 short takes with the WebUI open lost 2-10 frames each. **No (B) take of any length exists on `d44b177` or later** (V-F5 §1).
- **(B) with Log: UNKNOWN.** One take: 117 frames, 10 gaps, WebUI open, pre-squash build (`hardware-log.md:782-784`). The LUT runs on the copy worker
  after the camera request is released (code, `CameraController.cpp:4871-4890@6ef0ddc`), so it is neutral on the serial cycle by construction, but it
  adds +0.62 GB/s of DRAM traffic net (derived, V-F3) against a back end measured to stretch 2.6x under such traffic, and that one take had the worst
  gap rate of its evening (6.9 ms/frame after the first gap, V-F6 E6). Storage is not the question (311 MB/s, 42 % of the measured ceiling).
- **The decisive measurement for both modes** is one `LIBCAMERA_LOG_LEVELS=RPI:0,RPiStream:0` window per mode parsed with
  `working/tools/be_cycle.py` on counted 60 s takes, default tuning then the `_notdn` copy, with every confounder read back (section 6). For (B) it
  decides the margin; for (A) it decides whether the 22.7 ms cycle reproduces on the shipping build and whether TDN is the term.
- **Levers, in the order they pay:** the tuning copies without `tdn` (two files, `set_tuning_file`; estimated, the only double-digit lever in (B));
  WebUI preview paused during takes (−0.2 to −0.5 ms/frame, measured on an old build); O_DIRECT for the uncompressed writer, promoted by V-F6 because
  writer-side state produced capture gaps twice (T22's buffered `dd` with Core idle; A2); the rest are jitter absorbers (8 raw buffers, FE config
  queue depth, per-thread FIFO, `DONTNEED=sync`), storage-side fits (10-bit, 2076, Log, RAM mode) or hygiene (trim, ramp off, swap off, first-take
  discard). The reference the operator raised, cinemate, has no counted take of either mode; its own May-2026 table rated 4K 12-bit at 38 fps
  sustainable on CFE/NVMe exFAT (F5 §6 C8, confirmed V-F5).

## 1. The chain as budgets

Period budgets: **20.0 ms** for (A), **40.0 ms** for (B). Stages inside libcamera's serial per-frame cycle must finish inside the period on every
frame (the CFE skips a frame when no raw buffer, stats buffer or config buffer is queued at frame start, kernel `cfe.c`, confirmed V-F1 row 5); stages
off the cycle must keep up on average, with the 12-frame queue (or RAM mode) absorbing jitter. One-off slack figures use the corrected formula
L_max = N·T − R (V-F1 E1), not (N−1)·T − R.

| Stage | (A) budget | (A) estimated use | (A) margin | Label | Source | (B) budget | (B) estimated use | (B) margin | Label | Source |
|---|---|---|---|---|---|---|---|---|---|---|
| Sensor / CSI-2 link / RP1 pixel rate | sensor ceiling 60.0 fps; link 7128 Mbps; RP1 cap 646.7 Mpix/s (with `rp1-clk-333mhz`) | 50 fps; 4.98 Gbps = 69.8 %; 518.4 Mpix/s = 80.2 % | +20 % sensor; 30 % link; 20 % RP1 | measured (probe 60.0, pre-roll 60.0 at this size) / derived (link, RP1; cap from fork code + two config.txt readings, live `clk_sys` unread) | F1 §2.1-2.2; V-F1 rows 3-4b | 30.0 fps; 7128 Mbps; 646.7 Mpix/s | 25 fps; 3.38 Gbps = 47.4 %; 518.4 reported (259 physical average) | +20 %; 53 %; 20 % | measured (A0/A1 clean; 30.00 fps idle) / derived | F1 §2.1; V-F1 §5 |
| CFE raw pool and FE config queue | pool 4 (SDR default, `APERTAR_RAW_CAMERA_BUFFERS` 3..16); config queue 2 | one-off lateness tolerance 64 ms (4 buffers), 144 ms (8); config re-queue must land within 2T − R = 24 ms of EOF | ~2 periods of one-off slack; 0 against a mean deficit (M3: 355 vs 358 lost with 4 vs 8 buffers) | derived (kernel + libcamera code read); M3 measured | V-F1 E1, E2; F1 §2.3; `hardware-log.md:591-594` | pool 8; config queue 2 | 287 ms (8), 607 ms (16); config 47 ms | ~6 periods | derived; 217 ms queue wait at 30 fps reproduced to ~1 ms with N | V-F1 rows 2-2b |
| Serial cycle (IPA + BE incl. TDN + Core callback + requeue) | 20.0 ms | **22.7 ms** (M3, 4d5fdd1, 2076, uncompressed, 60 s); **≤ 17.5 ms** (pre-roll, d44b177, 2160 lossless, 60 fps, 1.9 s, probably 8 buffers); models 10-14 ms (F2) vs 19-20 ms (R9/L2 scaling), TDN on | **−2.7 to ≥ +2.5 ms**; MARGINAL, LOW | derived from measured counts (both ends); estimated (models, disagree) | F2 §1, A.2-A.4; V-F2 §1, §3.1-3.2, §5 | 40.0 ms | 34.7-38.0 ms at 30 fps recording (L1/L2), 36.2 ms pre-L1; no 25 fps window exists | **+2.0 to +5.3 ms** at the A0 load; MARGINAL-INSIDE, MEDIUM; load-dependent (T22: 25 fps cycle exceeded 40 ms under lossless-encoder load on an older build) | derived from measured fps; measured (36.2) | F2 §2.2; V-F2 §3.3, §5; `hardware-log.md:184-233` |
| CPU | 4 cores (80 core-ms per period) | 2.3-3.0 cores (58-75 %); nearest actor the 4 writers at 25-38 ms CPU per DNG (COMP1 decode + 12-bit pack + exFAT) against 80 ms wall each; M3 bounds the writers only loosely (44 files/s, queue ≤ 3/12) | 1.0-1.7 cores | estimated (decode never timed), low-medium | F3 §2.2, §2.4; V-F3 §1, §5 | 4 cores (160 core-ms) | linear 1.7-1.8 cores; CameraManager thread 20-24 ms of 40 with the system libcamera (12-15 with the L1/L2 fork); Log 1.9-2.1 cores, copy worker 10-25 ms of 40 (LUT never timed) | ~2.2 cores (linear), ~1.9-2.1 (Log) | derived from the one 30 fps per-thread measurement (`hardware-log.md:143-144,157-164`); Log estimated, low | F3 §2.2; V-F3 §3 items 6-7, §5 |
| DRAM | 17.07 GB/s interface (web); 7-10 GB/s practical for a mixed stream set (estimated) | 87.1 MB/frame = **4.35 GB/s** (TDN at COMP1); TDN off 3.43; scratch spill 5.60 | 2.6-5.6 GB/s on the average; contention on the BE at 50 fps unmeasured | derived (bytes, reproduced by V-F3) / estimated (ceiling, weakened from F3's 10-12) | F3 §2.1; V-F3 §1, §3 item 5 | same | 208.2 MB/frame = **5.20 GB/s** linear (TDN on); TDN off 4.27; Log **5.83** net (+0.62) | 1.8-4.8 GB/s linear; Log 1.2-4.2 (58-83 % of practical: MARGINAL); the BE stretched 13.4 → 34.6 ms and the thread's IPC 1.87 → 1.30 under this class of load at 30 fps (measured) | derived / measured contention | F3 §2.1; V-F3 §5; `hardware-log.md:157-162, 184-193` |
| Writers and page cache | 4 writers, 12-frame queue; 50 files/s; period 20 ms | 622 MB/s through the COMP1 decode + packed-12 scratch path (34 `write()`s per frame; the direct write path does not apply to COMP1); `DONTNEED` writeback start + cross-CPU `lru_add_drain_all` per file (50/s) | writers kept up at 525 MB/s with queue ≤ 3/12 (M3); nothing measured above that | measured (M3) / confirmed mechanism | F3 §2.1 (A), §2.3; F4 §2.3; V-F3 rows 11-13 | 4 writers; 25 files/s; 40 ms | linear: one `write()` of 16.6 MB from the copy (direct path, default in 6ef0ddc), 415 MB/s; Log: packed-12 scratch path again, 311 MB/s | queue ≤ 2/12 in A0/A1 (measured); Log unmeasured over any long take | measured / confirmed code | F3 §2.1; V-F3 rows 11-12; `hardware-log.md:741-764` |
| exFAT metadata (one folder per clip, 5 dentries per frame file, FAT-chained files with 4 writers) | `s_lock` must carry per frame: one O(N) create scan + 24,300 block mappings + the fsync's dentry write, inside 20 ms | at the 30,000th file: scan 12-38 ms (c = 80-250 ns per dentry, **unmeasured**) + 3.6-7.3 ms mappings = **16-46 ms**; break-even 9,000-30,000 files (minute 3-10) | **80-230 % of the period at minute 10**; direction undetermined (A0/A1 only exclude c ≳ 450 ns) | estimated (c is the weakest assumption of the whole storage section); mechanism confirmed in rpi-6.12.y source | F4 §2.3; V-F4 rows 16-19, E1 | same inside 40 ms | at the 15,000th file: 6-19 + 4.9-9.7 = 11-29 ms | 27-73 %; measured clean three times at this file count | estimated / measured (C0101, A0, A1) | F4 §2.3; V-F4 §1 |
| Drive sustained rate and free space | need **622.2 MB/s** (598.0 at 2076; 518.5 at 10-bit); 10 min = **373 GB** | ceilings on this rig: 733-759 MB/s direct `dd` ≤ 5 s in-cache with the camera streaming; 556-572 buffered `dd`; 525 for 60 s (Core); link class 685-778 (web); E27T post-pSLC ≈ 800 (web snippet, Gen 3 x4 host); pSLC exhausted in < 2 min at this rate | +111 to +156 vs 733-778; −66 vs 556; +178 vs 800; **no datum ≥ 600 MB/s longer than 5 s**; needs ≥ 373 GB free (M3 day: 206 GB free) | measured (dd, Core) / web (link class, drive) / derived | F4 §2.2; V-F4 rows 1-9, §5; V-F6 E3-E4 | need **414.8 MB/s** (Log 311.3); 10 min = 249 GB (Log 187 GB) | same ceilings | +318 vs 733 (43 %); 3 × 600 s clean (C0101, A0, A1); Log +422 (58 %), arithmetic only | measured / derived | F4 §1; V-F4 §1, §5 |
| Stall cushion (complete device stall) | frames mode: 12 queued + 4 in writers' hands = 16 periods = **320 ms**; RAM mode (4 GB board, measured budget 1,424 MiB, stop at 90 %): 162 frames = **3.2 s** | the synthetic worst-file latency on a trimmed drive at 422 MB/s was 26-282 ms (measured) | one 282 ms file is 88 % of the frames-mode cushion; RAM mode covers it 11x; catch-up 5.6 s per stalled second at C = 733 | derived / measured | F4 §2.4; V-F4 rows 13-15 | 16 × 40 = **640 ms**; RAM 81 frames = **3.2 s** | same tail | 2.3x the tail in frames mode | derived | F4 §2.4 |

Reading the table: no stage is OUTSIDE by a measurement for (B); the cycle is the thin one (+2 to +5 ms) and the only one that has produced losses
since the trim fix. For (A), the sensor, link, RP1, CPU and DRAM averages are inside with 20-30 % to spare; the three stages that decide it (serial
cycle, drive sustained rate, exFAT create scan) are each MARGINAL with no measurement longer than 60 s, and two of them have never been measured at
this load at all.

## 2. Mode (A): 4K SDR 12-bit 50 fps

### 2.1 The two gates

(A) has to pass two independent gates, and a lever on one does nothing for the other:

1. **The serial cycle** (IPA + PiSP back end incl. TDN + Core's completion callback + requeue) must average under 20.0 ms with its tail inside the
   raw pool's one-off slack (64 ms with 4 buffers, 144 ms with 8; derived, V-F1 E1). A steady surplus d produces one skipped frame every 20/d frames
   whatever the buffer count (F1 §2.3; measured on M3: 4 vs 8 buffers, 355 vs 358 lost).
2. **Storage over 10 minutes**: 622.2 MB/s (derived from the measured 1,540 B DNG overhead, V-F4 row 10) for 600 s = 373 GB, through four exFAT
   writers, the page cache and a Gen 3 x1 link, with an exFAT directory that grows to 30,000 entries and is scanned in full on every create.

### 2.2 What the record shows

| Datum | What it says | Label | Source |
|---|---|---|---|
| T34 M3, C0025 / C0026 (2026-10-28, `4d5fdd1`, 3840x2076 12-bit uncompressed, 50 fps, 60 s each, untrimmed drive 78-82 % full, speed ramp off, WebUI state and tuning unrecorded) | 2632 of ~2987 and 2616 of ~2974 frames; `dropped_gap_estimate` 355 / 358, `dropped_queue_full` 0, `peak_queue` 2/12 and 3/12, write failures 0; every loss a single-frame gap at dt 40 ms; C0026 ran `APERTAR_RAW_CAMERA_BUFFERS=8`. Delivered 44.0 fps ⇒ cycle **22.7 ms** (V-F6 recomputes 22.8-22.9 from 43.6-43.9 fps; immaterial), surplus 2.7 ms ⇒ one skip per 7.4 frames = 357 in 60 s (matches). 525 MB/s written (2632 × 11.96 MB / 60 s; F5's 500 corrected by V-F5 E1). 1080p50 was clean the same evening | measured; cycle derived | `hardware-log.md:582-596`; F2 A.2; V-F2 row 5; V-F5 rows 1-4 |
| What M3 does not establish | the raw transport (COMP1 vs packed: probable COMP1 from the format rule, unrecorded), copy-slot drops (counter not printed then), WebUI state, tuning, whether 2076 differs from 2160 in anything but rows, behaviour on a trimmed drive or beyond 60 s | unverified | F5 §4.5; V-F5 E4 |
| The 2026-11-01 pre-roll (`d44b177`, 3840x2160 12-bit **lossless**, `FrameDurationLimits` pinned to 60 fps, 2.0 s, trimmed drive, WebUI probably open) | `ok: 2.0 s at 60 fps (measured 60.0), 115 frames, 0.7 GB written and deleted`; `measuredFps` = (n−1)·1e6/(last−first) over the sensor timestamps of accepted frames (`StoragePreroll.hpp:200-205@6ef0ddc`), printed `%.1f`, so one skip or one refused frame would read 59.5 ⇒ **zero skips and zero queue drops over 114 consecutive periods**. Mean cycle bound: ≤ 16.67 × (1 + S/114) with pool slack S: **≤ 17.5 ms** for S ≤ 6 (the unit carried `APERTAR_RAW_CAMERA_BUFFERS=8` since 10-28, read back on 10-30, `hardware-log.md:591,741`, never recorded removed ⇒ probably 8 buffers), ≤ 18.1 ms for any S ≤ 10. Writer load 344 MB/s through the lossless encoder (5.98 MB/frame), i.e. 55 % of (A)'s bytes on a different writer path | measured; bound derived (robust to the slack assumption, V-F5 §4.2) | `hardware-log.md:842-855`; F2 A.3; V-F2 rows 6-7, §3.2; V-F5 rows 6-9 |
| No take at 3840x2160 at 50 fps; none on the current build | confirmed by the complete read of the hardware log and every working/ folder; the 85 commits `4d5fdd1..6ef0ddc` leave the completion path identical except `noteFrameForPreroll` (microseconds), a `FrameDurationLimits` pin active only during a pre-roll, and the off-by-default `APERTAR_RT_CAPTURE_PRIORITY` branch | confirmed (direct diff) | V-F5 row 14, §1 |
| A possible free datum: the 2026-10-28 shooting-day clips (38 clips, C0001-C0032, on the SEAGATE disk, no Core log) | shot on the 10-27 `temp:` build that offered 4K SDR 12-bit lossless at 25/33/50 fps; whether any clip ran above 25 fps is unknown (the per-clip tag CSV is not in the kb). The DNG-clock method (`ExifIFD:DateTimeOriginal` counts per full second against fps, `hardware-log.md:889-897`) would count them at zero rig time and could give the first multi-minute 4K lossless datum above 25 fps under a real writer load | unverified pool; method exists | V-F5 §4 item 1; `handoff-T26-T30.md:104-106` |

### 2.3 The cycle, corrected brackets

- **Measured bracket: −2.7 ms (M3) to ≥ +2.5 ms (pre-roll bound ≤ 17.5 ms).** The two ends come from different configurations (2076 vs 2160;
  uncompressed 525 MB/s vs lossless 344 MB/s; untrimmed 82 % vs trimmed; 60 s vs 1.9 s; `4d5fdd1` vs `d44b177`; 4 vs probably 8 buffers) and the
  record cannot say which difference explains the 5 ms (F2 A.4; V-F2 §3.1). Confidence LOW.
- **The models disagree and the page does not pick one.** F2 scales the idle BE upper bound (13.4 ms for 57.6 MB) by bytes (29.0 MB with TDN at
  COMP1) and applies the CPU passes' measured 1.22-1.62x recording stretch: S2 8-11 ms, cycle **10-14 ms**. V-F2 counters with the L2 datum: with the
  swap and stats moved to a worker (thread 34 % busy) the 30 fps cycle still measured 35.5-38.0 ms, implying a BE recording time of ~34-36 ms that
  scales to 17-18 ms in SDR, i.e. a cycle of **18.7-19.9 ms**, R9's bracket at its low end. Both anchors contain thread time (V-F6 row 5); neither is a
  measurement of the SDR back end, which has never been timed. The earlier page's "19-23 ms, probable" and F2's "R9 over-predicted" are both
  withdrawn in favour of "the two SDR models bracket the budget; only `be_cycle.py` decides" (V-F2 §5).
- **TDN state is unverified.** Every TDN-on figure assumes `rpi.denoise.tdn` is present in `/home/pi/Tuning-Files/defaults-pisp/imx585.json`
  (probable, strongly: every PiSP IMX585 tuning of that size class carries three `tdn` blocks, V/H2); the file is on the Pi only. If TDN is already
  off, the top lever is moot and M3's 22.7 ms is not the back end (F2 A.4).
- **Two IPA facts banked for (A).** At 50 fps the IPA already runs its algorithms on alternate frames by default (`controller_min_frame_duration_us`
  33333, `ipa_base.cpp:480-498@c682979`), so S1 averages ~0.8 ms, not 1.6 (V-F6 E8). And the FE Config queue is 2 deep: a CameraManager-thread
  stall longer than ~24 ms starves the FE_CONFIG node with the same dt = 2T signature as a raw-pool starvation (V-F1 E2); no measurement shows it
  firing (30 fps handlers were 6-13 ms), so it is a candidate for single skips, not a demonstrated one.

### 2.4 Storage over 10 minutes

- **Verdict: MARGINAL, direction undetermined, confidence LOW** (V-F4 §5 overrides F4's "leaning OUTSIDE": the lean rested on two unmeasured
  constants). Facts: 622 MB/s is 85 % of the 733 MB/s direct `dd` (4.9 s, in-cache, camera streaming at 25 fps; `T22.md:17`), 82 % of 759, 112 % of
  the only buffered single-thread `dd` (556), 118 % of the 525 MB/s Core held for 60 s with the queue nearly empty, and ~78 % of the E27T's ≈ 800 MB/s
  post-pSLC steady rate (web snippet from a Gen 3 x4 host; the 1 TB E27T's own cache size is in no reachable source; the 2 TB sibling's is 48 GB).
  Core's four-writer buffered path should land between 556 and 733: never measured above 525.
- **The exFAT create scan is the second storage unknown.** `exfat_lookup` walks every dentry of the folder from 0 on every create (the iversion
  change at each create resets the hint; confirmed in rpi-6.12.y, V-F4 row 16), under `s_lock`, which `exfat_get_block` also takes once per 512-B
  block (24,300 takes per 12.44 MB frame). At c = 80-250 ns per dentry the scan is 12-38 ms at 30,000 files; the lock then carries 16-46 ms of work per
  20 ms period in the last minutes. c has never been measured; A0/A1 (75,000 dentries, clean) only exclude c ≳ 450 ns (V-F4 E1). Break-even between
  minute 3 and minute 10.
- **Thermal and link.** 415 MB/s for 10 min took the drive from 34 to 54 °C (measured, `hardware-log.md:745-748`); at 622 MB/s a cold start lands
  around 60-65 °C and a back-to-back take 75-85 °C against an 82.9 °C warning threshold (estimated, linear-with-rate model). Two unplanned controller
  drops at Gen 3 on 2026-10-26 (idle) and `errors=remount-ro` mean a single I/O error ends the take (F4 §2.2-2.3).
- **The formats that fit by arithmetic** (storage side only; none changes the cycle, since COMP1 is 1 B/px at every SDR depth): 10-bit **518.5 MB/s**
  (71 % of 733; `set_raw_bit_depth 10`, writer path exists); 3840x2076 **598.0 MB/s** (82 %; M3's mode, −3.9 % rows); lossless JPEG **299-455 MB/s**
  (one scene measured at 5.98 MB/frame; encoder ~69 fps estimated, ~57 % of 4 cores at 50 fps). 60 fps uncompressed (746.6 MB/s) does not fit.
- **Free-space precondition:** ≥ 373 GB free for one 10-minute uncompressed take at 2160 (359 GB at 2076, 311 GB at 10-bit); the drive is 932 GB and
  held 206 GB free on the M3 day (V-F6 E4). 2.5-2.7 takes walk the allocation cursor around the volume once; Core's trim (at mount, after ≥ 1 GiB
  deletes, after pre-roll deletes) is what keeps the wrap harmless (12 of 12 trimmed synthetic runs clean, `hardware-log.md:708-712`).

### 2.5 The ordered path to a drop-free (A) take

| Step | Do | Stop criterion |
|---|---|---|
| A.0 Rig state (read-only, E0) | `grep -c '"tdn"' /home/pi/Tuning-Files/defaults-pisp/imx585*.json`; `journalctl -u apertar-core -b \| grep -E 'tuning file\|capture scheduling\|pixel-rate cap\|Adjusting mode minimum\|RAW buffers\|camera configured'`; `grep libcamera /proc/$(pidof apertar-core)/maps`; `systemctl show apertar-core -p LimitNICE -p LimitRTPRIO -p Environment`; `df -h /media/RAW`; `blockdev --getss /dev/nvme0n1p2`; `sudo nvme id-ctrl /dev/nvme0 \| grep -E '^mn\|^fr\|vwc\|hmpre\|hmmin'`; `swapon --show`; `get_state` → `fps_speed_ramp`, `storage_preroll_auto`, `ladder_enabled` | `tdn` = 0 already ⇒ the tuning lever is moot, go to A.3 with the writer-side arms first; < 373 GB free ⇒ no 10-min test is possible until clips are moved off |
| A.1 Storage gate, Core stopped | 10 min `fio --rw=write --bs=1M --direct=1 --iodepth=32 --size=400G --write_bw_log … --log_avg_msec=1000` on the trimmed, cooled drive; then `variant2.py` at 50 files/s × 12,443,140 B for 600 s in one folder (or a 30,000-file `open(O_CREAT)` loop timing each create) | plateau < 650-700 MB/s after the pSLC knee ⇒ uncompressed 2160 is out; switch to 10-bit or 2076 for every later step. Create latency rising by > 10 ms from file 1,000 to 30,000 ⇒ the scan is real: shorter clip-name template (4 dentries), or accept a ≤ 3-5 min take length |
| A.2 Cycle, default tuning | `LIBCAMERA_LOG_LEVELS=RPI:0,RPiStream:0` + `LIBCAMERA_LOG_FILE=/dev/shm/rpi0.log` drop-in, `APERTAR_STORAGE_PREROLL=0`, restart; WebUI closed, ramp off, ladder off, trimmed; one 60 s idle window (stage-1-only, F1) then one counted 60 s take at 3840x2160 12-bit uncompressed 50 fps; `be_cycle.py` medians/p90 of S1-S4 and cycle; the four counters; frames vs 3000. Then the same at 3840x2076, then lossless | gap 0 and cycle median ≤ 20 ms ⇒ the cycle gate is passed on this build; go to A.4. Cycle ≥ 21 ms with S2 ≥ 17 ms ⇒ the BE is the limiter, go to A.3. Cycle > 20 with S2 small ⇒ software latency: per-thread FIFO, WebUI pause, config-queue depth, then pipelining |
| A.3 Cycle, levers | (i) tuning copy without `tdn` (`imx585_notdn.json`) via `set_tuning_file`, repeat A.2; (ii) an arm with `APERTAR_DNG_WRITEBACK=0` and one idle `dd conv=fdatasync` repeat on the current build, so the BE-bytes and writeback suspects are separated in one session (V-F6 §5) | S2 falls roughly with bytes (17 → 6-12 ms) and gap 0 ⇒ keep the copy, build the automatic derivation (3a). S2 within 15 % of TDN-on ⇒ the BE is compute-bound or not the limiter: no configuration lever remains for (A) at 50 fps (fallbacks: 40 fps, BE decimation, raw-only take) |
| A.4 Acceptance | three interleaved 10 min takes in the chosen format, `peak_queue`, `/sys/block/nvme0n1/stat`, drive temperature and `dmesg` per second; one of them with the WebUI open | 0 in every `drop[...]` counter, `peak_queue` ≤ 3/12, stop `syncfs` < 200 ms in 3 of 3 ⇒ (A) is YES UNDER CONDITIONS in that format. `peak_queue` climbing from minute ~2 ⇒ the post-pSLC rate binds: 10-bit / 2076 / RAM mode as the standing cushion |

Every step records: WebUI clients (`ss -tnp state established '( sport = :8080 )'`), `fps_speed_ramp`, `media_trim_last_unix`,
`storage_preroll_last`, the tuning path line and its `tdn` count, first-take-after-reconfigure (discard it), the libcamera build in `/proc/<pid>/maps`,
`APERTAR_RAW_CAMERA_BUFFERS` as read back from the unit, `vcgencmd get_throttled`, drive fill and temperature.

## 3. Mode (B): 4K Clear HDR 16-bit 25 fps

### 3.1 What the record shows

| Take | Build, conditions | Result | Label | Source |
|---|---|---|---|---|
| C0101 (2026-10-26) | `114bfb9`, 4 writers / queue 12 / 8 raw buffers, drive 35 % full, never trimmed, no sync thread yet, WebUI state unrecorded | **10 min, 15019 / 15019 frames, 0 holes**, WAV = frames | measured | `hardware-log.md:386, 389`; `T27.md:12`; V-F4 row 9 (F4 had omitted it) |
| A0 (2026-10-30) | `a40112a`, defaults (`SYNC_MS=1000 WRITEBACK=1 QUEUE=12 BUFFERS=8`), fstrim before, **WebUI closed**, Core restarted before the take, speed ramp probably on (persisted; harmless by code) | **10 min, 15001 frames, no `drop[...]` line of any kind**, `peak_queue=2/12`, dirty 11 MB, stop syncfs 214 ms, drive 34 → 54 °C | measured | `hardware-log.md:736-755`; V-F5 row 11 |
| A1 (2026-10-30) | as A0 with `SYNC_MS=0` | **10 min, 15000 frames, 0 in every counter**, `peak_queue=1/12` | measured | `hardware-log.md:757-764` |
| A2 (2026-10-30) | as A0 with `SYNC_MS=0 WRITEBACK=0`; WebUI state not stated; speed ramp **on (probable)**: `missing=0` beside 1491 timestamp holes is only possible with count-based numbering (`nextFrameIndex`, `CameraController.cpp:4471-4480@6ef0ddc`, V-F5 row 13) | **13503 of ~15000, `dropped_gap_estimate=1491`**, ~2.5 one-frame gaps/s at dt ≈ 80,000 µs, steady, queue 1/12 ⇒ an effective surplus of **4.4 ms/frame** (derived) | measured; cause unexplained | `hardware-log.md:765-777`; V-F2 row 9; V-F6 E2 |
| Four short takes (2026-10-31) | pre-squash `drop-frames` build (not `d44b177`), **WebUI open**, Pi rebooted minutes before, one take overlapped an ssh journal query, drive trimmed at mount | 2/353, 9/272, 4/149, **10/127 (Log on)** frames lost; first gap 2-4 s in; after it 0.14 / 1.6 / 1.6 / 6.9 ms per frame (derived, V-F6 E6: a transient plus a small steady term, not M3's steady overrun) | measured, uncontrolled | `hardware-log.md:779-795` |
| 3-minute takes | C0003 (sync off), C0004 (writeback, syncfs off), C0007 (today's writeback + 1 s folder fsync), 10-27 C0002 (today's default) | 4 of 4 clean without the whole-fs `syncfs` (2 of 2 on today's default policy); C0001 under the old 1 s `syncfs` lost 12 gaps from ~113 s (the one capture-gap case the record explains and closed) | measured | `hardware-log.md:378-422, 461-466`; V-F5 E2 |
| Log | one take, 117 frames, 10 gaps, WebUI open, pre-squash build; one 12,451,344 B frame on `d44b177` | **unverified** over any take longer than ~5 s | measured (one short take) | `hardware-log.md:782-784, 820`; V-F5 §1 |
| On `d44b177`, `92d0970` or `6ef0ddc` | no Clear HDR 16-bit 25 fps take of any length | confirmed by reading `hardware-log.md:813-897` | V-F5 §1 |

Frequency, honestly stated: 3 of 4 ten-minute linear takes clean on trimmed or lightly filled drives, 0 of 0 on the shipping build, 0 of 4 short takes
clean with the WebUI open (V-F5 §5). The only variable with a consistent split for capture gaps is the WebUI state (closed in all three clean 10-minute
takes, open in all four lossy short takes, unknown in A2), and its measured cost (0.3-0.5 ms/frame) is too small to be the whole deficit (V/H4), so
something co-varied (reboot, Log, the ssh query, DRAM bursts).

### 3.2 The margin

- **+2.0 to +5.3 ms at the A0 load (derived, MEDIUM).** The 30 fps recording windows of 2026-10-26 gave cycles of 34.7-36.2 ms (L1) and 35.5-38.0 ms
  (L2), 36.2 ms pre-L1 (`hardware-log.md:184-233`); at 25 fps the same per-frame work has 40.0 ms. F2's "+3.8 by medians" used the pre-L1 window only
  (V-F2 §3.3). No RPI:0 window at 25 fps exists anywhere in the kb.
- **The margin is a property of the configuration, not a constant.** T22 (f60e301, older build, copy still on the thread): the lossless encoder's
  load pulled 25 fps delivery to 19.3-22.4 fps (cycle 45-52 ms) and a `dd` to tmpfs alone, Core idle, gave 22.77 fps (`hardware-log.md:64-78`). Log
  (+0.62 GB/s net), an open WebUI (0.2-0.5 ms/frame on the completion thread plus the MJPEG thread), swap, and the first seconds after a reboot can
  consume it. Which libcamera runs today (system `7e9fef0` with the 16-bit swap and the SW stats on the CameraManager thread, or the L1/L2 fork
  that moves them) is unverified and worth ~10 ms of thread time per frame (V-F6 §4 item 3).
- **Writer-side state has cost capture frames twice** at this mode with everything else fixed: T22's buffered `dd` at 561 MB/s with Core idle
  (19 gaps in 3.4 GB; `oflag=direct` at 759 MB/s none; `clearhdr-design.md:127-135`) and A2 (4.4 ms/frame with `WRITEBACK=0`). The ramp-on inference
  for A2 affects only the `missing` field, not the capture-gap counter (V-F6 E2), so A2 stands as one clean run of a writer-side change producing
  capture gaps; mechanism (DRAM vs fabric/IOMMU vs IRQ) unverified. This is why `APERTAR_DNG_WRITEBACK=1` is a precondition and O_DIRECT is a first-tier
  lever (section 4).

### 3.3 The A0 protocol (the conditions under which (B) is YES)

WebUI closed (or `APERTAR_WEB_PREVIEW_RECORDING_FPS=0`), drive trimmed by Core (`media_trim_last_unix` before the take), `fps_speed_ramp` off and
read back, phase lock off, `APERTAR_STORAGE_PREROLL=0` for the series (else every restart runs a 60 fps burst with its own drops), the first take after
any reconfigure or reboot discarded (3 of 4 first takes were lossy on 2026-10-26), nothing else on the Pi (no ssh journal queries during a take),
defaults otherwise (`SYNC_MS=1000`, `WRITEBACK=1`, `DONTNEED=writer`, 8 raw buffers, 4 writers / queue 12), and every confounder read back as in §2.5.
Judge drops from `dropped_gap_estimate`, `dropped_queue_full`, `dropped_copy_slot` and frames against WAV seconds × fps, never from `takes.sh missing`.

### 3.4 What TDN off would add

- Bytes: the BE moves 57.6 MB per frame with TDN (raw 18.73 + TDN read 18.73 + TDN write 18.73 + YUV 1.38) and 20.0 MB without (confirmed arithmetic
  on the libpisp v1.3.0 simulation, F2 §2.2). TDN is the largest single removable DRAM term in both modes (37.5 of 208 MB; V-F3 §1).
- Cycle gain: **−12 to −23 ms if the BE is memory-bound (probable), 0 if compute-bound** (V-F2 row 18, §3.4: 0.65 × the BE recording time of 19-22
  or 34-36 ms). F6's "cycle ≈ 14-17 ms after T1" dropped its own swap + stats row; with the system or L1 libcamera the cycle is bounded below by swap +
  stats + S1 + S3/S4 ≈ 16-21 ms, so the margin after TDN off is **≈ +19 to +24 ms** (V-F6 E5; +23 to +26 only with the L2 worker build). Estimated;
  one TDN-off `be_cycle.py` window settles it (rule-out: S2 within 15 % of the TDN-on value ⇒ not memory-bound).
- Memory-bound evidence (V-F2 §3.4): the L2 result (BE time inferred 2.5x idle with the thread free, same pixel count, only the DRAM load changed) and
  T22's `dd`-to-tmpfs frames cost both support contention-sensitivity of the serial loop; neither isolates the BE from the thread. Probable, not
  confirmed.
- Cost: a noisier preview (SDN takes its `*_no_tdn` values; the 3.2 vs 0.6 deviation figure is from cinemate's `imx585_mono.json`, Apertar's file
  unverified, V-F6 row 10); DNGs byte-identical (the BE only reads the raw buffer). The file with `rpi.hdr` must keep it: Clear HDR needs the
  `_clearHDR` tuning, so a second copy `imx585_clearHDR_notdn.json` is required (F2 L1; V-F6 row 3).

### 3.5 Log's status

UNKNOWN until a counted 60 s Log take with the WebUI closed exists. Code: neutral on the serial cycle (`copyLoop`: `dmabufCpuSync` → `memcpy` →
`dmabufCpuSync` → `releaseHeldRequest` → `applyCdngLogFrame`, `CameraController.cpp:4862-4892@6ef0ddc`; confirmed V-F1 row 7b, V-F3, V-F6). Cost: the
copy worker carries sync + memcpy 6-8 ms plus a 8.3 M-lookup LUT pass estimated 4-17 ms (V-F3 corrected F3's 8-17: the loop has no loop-carried
dependency and the 128 KiB table sits in L2) = 10-25 ms of 40, single thread; DRAM +24.9 MB/frame net (+33.2 LUT, −4.15 kernel copy, −4.15 NVMe) =
**+0.62 GB/s**, 58-83 % of a 7-10 GB/s practical ceiling (MARGINAL, V-F3 §5); the writer leaves the direct path and packs through the scratch again
(`copy.view.bitDepth` set to 12, V-F3 row 12). Benefit: 311 MB/s instead of 415 on a drive that was not the limit. Log is a cost in every
dimension but storage (V-F3 "Log is a cost, not a lever": confirmed).

### 3.6 The ordered path to a drop-free (B) take

| Step | Do | Stop criterion |
|---|---|---|
| B.0 Rig state | as A.0; in addition `grep -c '"tdn"'` on `imx585_clearHDR.json` and the libcamera build line (`/proc/<pid>/maps`: system vs `~/opt/libcamera-apertar`) | which libcamera runs decides ~10 ms of the margin claim before any take |
| B.1 Transfer to the shipping build | A0 protocol on `6ef0ddc`: 3 × 60 s linear, then **3 × 10 min linear** (E2), every confounder read back | 0 in every counter, `peak_queue` ≤ 2/12, stop `syncfs` < 200 ms in 3 of 3 ⇒ (B) linear is YES UNDER CONDITIONS on the shipping build. Any `dropped_gap_estimate > 0` with `peak_queue ≤ 2` ⇒ A2's class survives: go to B.2 before anything else |
| B.2 Margin and the tuning lever | one RPI:0 window at 25 fps recording with the default tuning (the first 25 fps cycle measurement in the kb), then `set_tuning_file ~/Tuning-Files/imx585_clearHDR_notdn.json` and repeat; `be_cycle.py` S2 and cycle medians/p90 | p90 > 36 ms with TDN on ⇒ the copy is mandatory for (B); S2 falling with bytes ⇒ keep it and build the automatic derivation (3a); S2 unchanged ⇒ compute-bound, look at the writer side (B.4) |
| B.3 Log | 3 × 10 min with Log under the same protocol | clean ⇒ Log is YES UNDER CONDITIONS; lossy with the queue ≤ 2 ⇒ Log's DRAM pass is a cost the margin cannot carry: TDN off first, then O_DIRECT |
| B.4 The operator's use | one 10 min take with the WebUI open and `APERTAR_WEB_PREVIEW_RECORDING_FPS=30` (default), one with `=0`; the three-client test (E1) if they differ | clean with the page open ⇒ the condition "WebUI closed" can be dropped; lossy ⇒ keep `=0` as the standing setting (or 3c: move the downsample off the completion thread) |
| B.5 Belts | `APERTAR_RAW_CAMERA_BUFFERS=12` (+160 ms of one-off slack), `APERTAR_RT_CAPTURE_PRIORITY=70` with the `LimitRTPRIO=80` drop-in reinstalled, `APERTAR_DNG_DONTNEED=sync`, `set_buffer_mode ram` as the standing cushion | each as a separate 60 s arm interleaved with the control; a step that turns residual gaps to 0 stays |

## 4. Levers

Ordered by expected gain per unit cost. "Gain" is per frame inside the serial cycle unless marked off-cycle or storage. "Exists" means present in
`6ef0ddc` and switchable without code. Writer-side figures carry V-F6's correction: their measured effect on capture is 4-10 ms/frame in two takes
(T22 `dd`, A2), not the ≤ 1-3 ms F6 claimed, so the writer-side rows are not second-tier.

| # | Lever | Stage | Expected gain (label) | Cost | Risk | How to apply today | Exists in 6ef0ddc? |
|---|---|---|---|---|---|---|---|
| 1 | **Tuning copies without `tdn`** (two files: `imx585_notdn.json` for SDR, `imx585_clearHDR_notdn.json` for Clear HDR; keep `rpi.denoise` so SDN/CDN take their `*_no_tdn` values, `denoise.cpp:54-69@c682979`, confirmed V-F6 row 1) | BE (serial cycle) | (A) BE bytes 29.0 → 10.6 MB: **−4 to −11 ms** (estimated: F2's model −4 to −7, F6's −5 to −11; both from bounded anchors, V-F6 row 5); (B) 57.6 → 20.0 MB: **−12 to −23 ms if memory-bound (probable), 0 if compute-bound** (V-F2 row 18); DRAM −0.92 / −0.94 GB/s (derived, F3) | one JSON edit per file; a noisier preview (SDN deviation figure unverified for Apertar's file); DNGs byte-identical; the picked file is used as given with **no automatic `_clearHDR` substitution** (`CameraController.cpp:6981-6990@6ef0ddc`), so re-pick when switching class; `set_tuning_file` refused while recording and reconfigures (45-110 ms) | low; "largest removable term" assumes BE time ∝ bytes (unmeasured); TDN presence in the Pi's files unverified (one grep). Never `disable_tdn` in the pipeline YAML (stalls the camera: enabled TdnOutput node with 0 buffers ⇒ `-ENODEV`, V-F2 row 16) | `python3 -I -c "import json,sys;s,o=sys.argv[1:];d=json.load(open(s));[m.pop('tdn',None) for a in d['algorithms'] if 'rpi.denoise' in a for m in a['rpi.denoise'].values() if isinstance(m,dict)];json.dump(d,open(o,'w'),indent=4)" <src> <dst>`, then `{"cmd":"set_tuning_file","path":"/home/pi/Tuning-Files/imx585_notdn.json"}` on the socket, or the UI tuning picker. **`APERTAR_TUNING_FILE` is not dead but conditional (V-F2 §3.6, code read this session, `CameraController.cpp:10077-10088`):** the start script exports it as `LIBCAMERA_RPI_TUNING_FILE`; the constructor adopts that env into `settings_.tuningFile` only when no `tuning_file` is persisted (the default state); the adopted path is then **persisted** at the next settings save and sticks after the variable is removed until "automatic" (empty) is re-selected; and a non-empty `settings.tuningFile` **disables the automatic `_clearHDR` substitution**, so an env-selected `imx585_notdn.json` would be used in Clear HDR too. Check what is in effect: `journalctl -u apertar-core -b \| grep -i tuning` and `grep tuning_file` in the persisted settings file | **yes, no build** (files on the Pi only) |
| 2 | WebUI preview paused while recording | Core callback (serial) | **−0.2 to −0.5 ms** per frame whenever a browser streams (measured idle 0.23 ms on an old build, 0.3-0.5 recording estimated; V/H4); plus the MJPEG thread's 2-5 ms/frame of CPU and the page's polling threads off the box | no browser preview during takes (HDMI unaffected) | nil | drop-in `Environment=APERTAR_WEB_PREVIEW_RECORDING_FPS=0` (or `10`); today: close the tab | yes (fb557e9) |
| 3 | Trim before every series | drive | removes the 0.9 TB post-wrap stall class (queue-full bursts; 12/12 trimmed synthetic runs clean vs 29-77 % lost untrimmed, `hardware-log.md:708-716`); 0 on capture gaps | 0.47 s per trim; never during a take | — | automatic in 6ef0ddc (mount, Core deletes ≥ 1 GiB, free-space jump ≥ 1 GiB, pre-roll deletes); `sudo fstrim -v /media/RAW` before a series; check `media_trim_last_unix` | yes |
| 4 | Speed ramp off (`set_fps_speed_ramp false`) | sensor / bookkeeping | 0 on the mean; removes the confounder that made A2's `missing=0` beside 1491 gaps (count-based numbering only with the ramp on, `CameraController.cpp:4471-4480, 9022@6ef0ddc`) and the period changes that cost frames (phase lock 10 holes/60 s measured) | none | none | socket / UI; read `fps_speed_ramp` from `get_state` before every take | yes |
| 5 | First-take discard | procedure | 3 of 4 first takes after a reconfigure were lossy on 2026-10-26 (`clearhdr-design.md:111-119`); the 2026-10-31 gaps came minutes after a reboot | one wasted take per series | — | discard the first take after any reconfigure, Core restart or reboot; compare first and second | — |
| 6 | 8 raw buffers in SDR (`APERTAR_RAW_CAMERA_BUFFERS=8`; 12 in Clear HDR) | CFE pool | **0 on the mean** (M3: 355 vs 358 lost, measured); one-off lateness tolerance 64 → 144 ms at 50 fps, 287 → 447 ms at 25 fps with 12 (derived, V-F1 E1); hides a transient (first-seconds) deficit entirely | +33 MB (8, SDR) / +68 MB (12, HDR) of cached heap; N frames of preview latency while a backlog drains | none | drop-in `Environment=` (the unit carried 8 since 10-28, state today unverified) | yes |
| 7 | FE config queue depth (`num_cfe_config_queue: 4` in the pipeline handler YAML, `/usr/share/libcamera/pipeline/rpi/pisp/*.yaml`; 12 are allocated, 2 in flight by default, `pisp.cpp:1381-1382@c682979`, same in the fork clone) | CFE config node | CameraManager-thread stall tolerance before a config starvation: 2T − R = **24 → 64 ms** at (A), 47 → 127 ms at (B) (derived, V-F1 E2); 0 on the mean; no measurement shows the node firing | zero memory | the installed YAML's key is unverified; a stage-1-only idle window with `LIBCAMERA_LOG_LEVELS=RPI:0,RPiStream:0` and `grep 'CFE Config'` shows the re-queue latency first | edit the YAML (or `LIBCAMERA_RPI_CONFIG_FILE` to a copy), restart Core | libcamera config only |
| 8 | Per-thread SCHED_FIFO on the completion thread (`APERTAR_RT_CAPTURE_PRIORITY=70`) | scheduling | **0 to −2 ms on tails**, tens-hundreds of µs expected, only when all four cores are busy (≈ 5 % of wake-ups by the independence model, more with the WebUI and with correlated writer wake-ups, V-F3 item 8); 0 on the mean | reinstall `config/apertar-core-capture-priority.conf` (now with `LimitRTPRIO=80`), `daemon-reload`, restart; the IPA proxy thread stays SCHED_OTHER unless `chrt -f -p 70 <tid>` | RT throttling only if a Core thread spins (none found); whole-process `APERTAR_RT=1` is the wrong shape (FIFO writers can block the capture thread) and stays a control arm | drop-in; verify the journal line `capture scheduling: … SCHED_FIFO priority=70`; `/proc/<pid>/task/<tid>/schedstat` for the wait per frame | yes (`CameraController.cpp:8672-8699`) |
| 9 | `APERTAR_DNG_DONTNEED=sync` | writers / page cache | removes 25-50 cross-CPU `lru_add_drain_all` per second and two failed xarray walks per DNG (confirmed mechanism, V/H3); **0-1 ms on the capture thread's tail (estimated)**, never measured | ~415-622 MB more page cache held for ~1 s; needs `APERTAR_MEDIA_SYNC_MS > 0` (default 1000) | none known (`off` instead hands the pages to kswapd: the risk arm) | drop-in `Environment=APERTAR_DNG_DONTNEED=sync` | yes (0ed07ea) |
| 10 | Swap off | system | unmeasured: 89 MB in use during T22, 0.86-1.5 GB during the T23 lossless takes (`T23.md:18-19`), 0 major faults read on 10-26; the reference the operator raised disables it in its installer | RAM mode's budget (`0.6 × MemAvailable − 512 MiB`) may shrink | none | `sudo dphys-swapfile swapoff` (persist `CONF_SWAPSIZE=0`); `vmstat 1` si/so during a take | config only |
| 11 | 10-bit SDR for (A) | storage | **0 on the cycle** (COMP1 is 1 B/px at 10 and 12 bits, `pisp.cpp:1212-1221@c682979`; BE bytes and pool unchanged); disk 622 → **518.5 MB/s** (71 % of 733), link 70 → 58 % | 2 fewer stored bits on top of COMP1's companding | none | `set_raw_bit_depth 10` (`unpackPispCompressedRowToPacked10` exists, `CdngEncoder.cpp:1027`) | yes |
| 12 | 3840x2076 for (A) | sensor / everything | −3.9 % rows: readout 15.38 vs 16.00 ms, BE 27.8 vs 29.0 MB, disk **598.0 MB/s** (82 %), probe ceiling 62.85 fps | a 1.85:1 frame; M3's mode, never run alone at 50 fps | none | `set_resolution 3840x2076` | yes |
| 13 | Log for (B) | storage | **0 on the cycle** (code); disk 415 → **311.3 MB/s** (42 %); 10 min = 187 GB | copy worker +4-17 ms (LUT, estimated), DRAM **+0.62 GB/s net** (derived), writer back on the scratch path; one lossy short take | medium: the one Log sample had the worst gap rate; unverified over any long take | `set_cdng_log auto` | yes (d44b177); not available in SDR (COMP1) |
| 14 | RAM buffer mode | queue / stall cushion | frames-mode cushion 320 ms (A) / 640 ms (B) → **3.2 s** on the 4 GB board (measured budget 1,424 MiB, stop at 90 %); ~9.6 s on an 8 GB board (derived); 0 on capture gaps | ~1.4 GiB of page cache / CMA headroom on a 4 GB board; the take ends by itself at 90 % (a clean stop, drain 3 s measured) | memory pressure with the camera running unmeasured | `[storage] buffer=ram` or `APERTAR_CDNG_BUFFER=ram`; `set_buffer_mode ram` | yes (d44b177) |
| 15 | `NoiseReductionMode = Off` in Core's start controls (`controlsForSettings` → `camera_->start(&initialControls)`, `CameraController.cpp:2293, 8315-8325@6ef0ddc`, behind a knob such as `APERTAR_NOISE_REDUCTION=off`) | IPA / BE | same DMA removal as lever 1 (the IPA emits no `tdn.status`, `applyTdn` never runs, TDN_INPUT/OUTPUT cleared every frame, `denoise.cpp:136-137`, `ipa/rpi/pisp/pisp.cpp:365-368@c682979`) **plus** SDN and CDN off | **~10 lines** (one `controls.set(...)` behind an env check; the control reaches the IPA through `ipa_->start(controls)` → `applyControls` → `handleControls`); a noisier preview than lever 1 (no spatial or colour denoise either) | set from start: **clean** (V-F2 row 15; and the kernel's `pispbe_xlate_addrs()` clears the TDN enable bits when no TDN input address is present, so even a runtime toggle is driver-handled, V-F2 row 14, probable). V-F6's libpisp caveat on a **mid-stream** on → off toggle: `platformPrepareIsp` never clears `PISP_BE_BAYER_ENABLE_TDN`, libpisp `SetGlobal` marks only newly set bits dirty so `finalise_tdn`'s consistency check never runs, and the job is submitted with ENABLE_TDN set and no TDN DMA; a libpisp throw would be fatal (no try/catch around `be_->Prepare`). Set-at-start, session-long only; lever 1 does the same with a better image | code | **no** (Core has 0 hits for `NoiseReductionMode`); inferior to lever 1 |
| 16 | **O_DIRECT for the uncompressed writer** (kb T24 patch `working/patches/0001-cdng-direct-I-O-…`, 208 insertions, never compiled; rebase onto the copy worker and `writeRowsDirect`) | writers / page cache | off-cycle: removes the page-cache copy (−12.44 MB r+w per (A) frame ≈ −1.2 GB/s DRAM; −33 MB per (B) frame), the `DONTNEED` drain and the writeback path; `s_lock` takes per frame ≈ 95 instead of 24,300 (probable, V-F4 row 19); **the one writer-side lever with an isolating measurement**: Core idle, buffered `dd` 561 MB/s ⇒ 19 gaps, `oflag=direct` 759 MB/s ⇒ 0 (`clearhdr-design.md:127-135`); direct vs buffered rate 733 vs 556 (+32 %). Promoted from F6's Path 3d to first tier by V-F6 E1 | medium code (≈ 100 lines of rebase on top of the patch); IFD-first layout written **front to back** (a direct write that starts past `valid_size` zero-fills `[valid_size, pos)` through the buffered page cache, V-F4 row 20); 512-B alignment of offsets, lengths and buffers (`-EINVAL` from `exfat_file_write_iter`); `ftruncate`/`fallocate` not required on rpi-6.12.y (no `i_size_aligned` check, no buffered fallback) but useful for contiguity (one `exfat_alloc_cluster` per file ⇒ no FAT chain, probable) | alignment bugs; the EINVAL fallback masks failures (prove the mode per take with the patch's log line, `/proc/<pid>/io` or `iostat`) | code, `APERTAR_CDNG_DIRECT_IO` | patch only |
| 17 | Pipelining in the fork (depth 2) | libcamera (serial) | ≤ the non-BE part of the cycle, **≤ S1+S3+S4 ≈ 1.6-5 ms; 0 if the BE hardware time ≥ the period** (q2 §5 corrected) | 300+ lines in `pisp.cpp` / `pipeline_base.cpp` (front()-based buffer matching, metadata routing, the 2-config-buffer ASSERT), a fork build on the Pi | highest regression risk of all levers; fork not local | only if a `be_cycle.py` window shows ≥ 3 ms outside S2 with S2 inside the budget, after lever 1 | no (code, fork) |

Not in the table because they do not move either gate: a smaller preview (−0.3 ms), no preview buffer in the request (0: the BE runs into an internal
buffer), `controller_min_frame_duration_us` (already in effect at 50 fps), fewer writers (1 writer gives contiguous files but one thread must carry
622 MB/s; the one buffered `dd` got 556), 1 MiB clusters (8x fewer allocations, no change to the scan or the per-block lock; macOS compatibility),
`APERTAR_MEDIA_SYNC_MS=0` (A1 = A0 at 415 MB/s; pull-safety), the media-tune kernel knobs (T22: no difference), HMB (random reads only), a different
NVMe (the Gen 3 x1 link is the ceiling), a USB SSD (neither mode fits linear; (B) + Log marginal), ext4 (no macOS mount: operator decision 2026-10-26).

## 5. Corrections this phase makes to `dng-chain-answer.md` and `dng-chain/STATUS.md`

Each entry: where, the exact old statement, the new statement, who established it. None of these flips a verdict of the earlier page; several change
numbers or labels that later pages must not repeat.

1. **CFE raw pools are 4 and 8, not 6 and 10.** `dng-chain-answer.md:140`: "unchanged when the raw buffers went from 4 to 8 (CFE pools of 6 and 10
   with libcamera's two internal buffers)". New: "unchanged when the raw buffers went from 4 to 8 (the CFE pool is exactly Core's count: the raw stream is
   flagged External when the app configures it, `queueAllBuffers` skips External streams, and libcamera's two internal raw buffers are queued only for a
   request that carries no raw buffer, which Core never issues; `pisp.cpp:974-989, 1463@c682979`, `pipeline_base.cpp:922-938`, `rpi_stream.cpp:124-161`;
   same in the fork clone `pisp.cpp:1250-1286, 1736@6b0b49f`)". F1 §2.3, confirmed V-F1 row 1; the kb critic (C10) had it right.
2. **The one-off jitter tolerance of the raw pool is N·T − R, not (N−1)·T − R.** F1 §2.3 (and the slack model used by R7/q5): "the pool survives one late
   return of up to L_max = (N − 1) × T − R: 44 ms (4 buffers, 50 fps), 124 ms (8), 247 ms (8 buffers, 25 fps)". New: "L_max = N × T − R: **64 ms** (4), **144
   ms** (8), 304 ms (16) at 50 fps; **287 ms** (8), 607 ms (16) at 25 fps (the buffer serving frame j must be in the DMA queue before SOF_j and the oldest
   in-flight buffer was committed at SOF_(j−N); the measured 217 ms queue wait at 30 fps reproduces with N, not N−1)". V-F1 E1, kernel `cfe.c` read.
3. **The FE Config queue is 2 deep, not 12, and is the shallowest CFE queue.** F1 §2.3-2.4: "CFE Stats and Config buffers: 12 each, internal, all queued at
   start … not binding". New: "12 Config buffers are allocated but only `numCfeConfigQueue = 2` are in flight (`pisp.cpp:1381-1382@c682979`, fork
   `:1630, 2096@6b0b49f`); frame k's Config buffer is re-queued only when the CameraManager thread handles its dequeue, so a thread stall longer than
   2T − R = **24 ms at 50 fps / 47 ms at 25 fps** starves the FE_CONFIG node and skips a frame with the same dt = 2T signature as a raw-pool starvation;
   never observed firing; `num_cfe_config_queue: 4` in the pipeline YAML is a zero-cost lever". V-F1 E2. Add to the answer page's §2 candidate list.
4. **R9's 19-23 ms SDR cycle estimate is contested, not probable.** `STATUS.md:108`: "Bytes-scaled from the one measured cycle, Apertar's SDR cycle at
   50 fps is 19-23 ms (T34 M3 delivered 44 fps = 22.7 ms); with TDN off 8-11 ms (R9, probable)"; `dng-chain-answer.md:146`: "the SDR cycle with TDN on COMP1
   input would be 19 to 23 ms, without TDN 8 to 11 ms (probable …)". New: "the SDR cycle has never been measured; the record brackets it at **−2.7 ms (M3,
   22.7 ms, derived) to ≥ +2.5 ms (pre-roll bound ≤ 17.5 ms, derived)** against 20.0 ms; two models disagree (F2: 10-14 ms from the idle BE bound scaled by
   bytes; R9/L2 scaling: 19-20 ms from the L2 recording window) and both anchors contain thread time; only `be_cycle.py` at 50 fps decides. TDN off:
   probably inside, unmeasured." F2 §1 and A.4, corrected by V-F2 §3.1 and §5 (F2's "R9 over-predicted" is withdrawn too).
5. **`APERTAR_TUNING_FILE` is not dead; it is conditional, and it persists.** `dng-chain-answer.md:35`: "the `APERTAR_TUNING_FILE` variable is dead:
   Core overrides it at start, kb upstream-issues #10"; `:208`: "`APERTAR_TUNING_FILE` is dead, Core overrides it at start"; `STATUS.md:111`:
   "(APERTAR_TUNING_FILE is dead: Core overrides it at start)"; `V/VERDICTS.md` H2 likewise. New: "`APERTAR_TUNING_FILE` (exported as
   `LIBCAMERA_RPI_TUNING_FILE` by `scripts/start-apertar-core.sh:16-17`) selects the tuning when no `tuning_file` is persisted (the default state): the
   constructor adopts it into `settings_.tuningFile` (`CameraController.cpp:10077-10080@6ef0ddc`), validates and applies it; a persisted selection wins
   over it; the adopted path is written by `persistSettingsLocked` at the next save of any setting and sticks after the variable is removed until the
   UI/socket selects automatic again; and because `settings.tuningFile` is then non-empty, the automatic `_clearHDR` substitution is disabled
   (`:6981-6990`), so an env-selected `imx585_notdn.json` is used in Clear HDR too. `set_tuning_file` / the UI picker select at runtime with a reconfigure.
   Check with `journalctl -u apertar-core -b | grep -i tuning` and `grep tuning_file` in the persisted settings." F2 L1, V-F2 §3.6. V-F6 row 11 kept "dead
   in the automatic branch"; this page follows V-F2 because the constructor code (read again this session) makes the env path a non-automatic selection
   before `applyProcessTuningFile` runs.
6. **exFAT direct I/O on rpi-6.12.y has no `i_size_aligned` check and no silent buffered fallback.** `dng-chain-answer.md:214`: "exFAT needs the file
   extended first (`ftruncate` to the final size, block-aligned IFD-first layout) or direct I/O silently falls back to buffered". New: "`exfat_direct_IO`
   on rpi-6.12.y is `blockdev_direct_IO(…, exfat_get_block)` with no `i_size_aligned` test and no fallback branch (removed upstream by `231eb762bb`
   'exfat: do not fallback to buffered write'); a sequential direct write may extend the file. What remains: 512-B alignment of offsets, lengths and user
   buffers (`-EINVAL` from `exfat_file_write_iter` on misalignment), and a direct write that starts **past `valid_size`** first zero-fills `[valid_size, pos)`
   through the buffered page cache, so an IFD-first layout must be written front to back. Preallocation is not required; it remains useful for contiguity
   (one `exfat_alloc_cluster` call ⇒ no FAT chain, probable)". F4 §3 L11 and §5 item 11, confirmed and completed by V-F4 row 20 and E7.
7. **Writer-side levers are not bounded at ≤ 1-3 ms; writer-side state has cost 4-10 ms/frame of capture-side effect twice.** F6 §1, §3.1 D-rows, §5
   (and, as the general stance, `dng-chain-answer.md:23` "No writer-side change in the drop-frames build … can touch that class" and `STATUS.md:45`):
   "everything on the writer side acts only through DRAM contention and is worth at most a few ms"; "worth ≤ 1-2 ms together". New: "writer-side state has
   produced capture gaps with everything else fixed in two measurements: T22 (Core idle at 25 fps 16-bit, buffered `dd` 561 MB/s ⇒ 19 gaps in 3.4 GB,
   `oflag=direct` 759 MB/s ⇒ 0, `taskset` to CPU 0 or 3 unchanged; `clearhdr-design.md:127-135`) and A2 (`APERTAR_DNG_WRITEBACK=0` ⇒ 1491 one-frame gaps in
   10 min, queue 1/12, ≈ 4.4 ms/frame). The mechanism (DRAM vs fabric/IOMMU vs IRQ) is unverified. `APERTAR_DNG_WRITEBACK=1` is a precondition, and
   O_DIRECT (T24) belongs in the first tier beside the tuning copy, since they attack different suspects." V-F6 E1-E2 (A2's ramp-on inference affects
   only the `missing` field, not the capture-gap counter). The earlier page's sentence stays true for Log, RAM buffer, trim and mount options by
   mechanism; it is wrong as a blanket statement about the writeback path.
8. **The drive is the MP600 Mini R2 (Phison E27T) with a small pSLC cache, not the original E21T.** F6 §3.1 H1 and §7 Q6 (and R6's table where it carries
   the figure): "the MP600 Mini (E27T, DRAM-less) is quoted at ≈ 800 MB/s steady state after a ≈ 63-70 GB pSLC cache". New: "FW `ERFM11.1`
   (`hardware-log.md:703`, measured) is the E27T revision (probable, snippets: TechPowerUp and KitGuru 2 TB spec tables; the original 1 TB E21T shipped
   `ELFMB`); its 2 TB sibling's pSLC is **48 GB** ('really tiny SLC cache'), the 1 TB E27T's own size is in no reachable source; post-cache ≈ **800 MB/s**
   steady in PCIe 3 mode (Tom's Hardware E27T review, snippet, Gen 3 x4 host, 15 min Iometer). The ≈ 70 GB / 1.8 GB/s figures belong to the E21T. For a
   10 min (A) take (373 GB) the cache size is moot: only the steady rate and the link matter." V-F6 E3; V-F4 rows 4-5 and §2 #7.
9. **The pre-roll probably ran with 8 raw buffers, so its bound is ≤ 17.5 ms, not 17.** `dng-chain-answer.md:25`: "the 2026-11-01 pre-roll ran 3840x2160
   at 60 fps for two seconds with zero skips (115 frames at a measured 60.0 fps), so the cycle there was at most 17 ms in that mode". New: "… so the mean
   cycle there was at most **17.5 ms** (the unit carried `APERTAR_RAW_CAMERA_BUFFERS=8` since the 10-28 `zz-ladder-buffers.conf` drop-in, read back on
   10-30, `hardware-log.md:591, 741`, never recorded removed ⇒ slack ~5-6 frames; ≤ 18.1 ms for any slack ≤ 10)". V-F2 §3.2, V-F5 §4 item 2.
10. **733 MB/s was a 4.9 s in-cache figure taken with the camera streaming.** `dng-chain-answer.md:149-150`: "sits at 85 % of the drive's once-measured
    direct-write rate (733 MB/s)"; F6 "733 MB/s `dd` direct (measured once)". New: "733 MB/s was one `dd oflag=direct` of ~3.6 GB in 4.9 s (`T22.md:17`),
    inside the pSLC cache, while libcamera streamed Clear HDR 16-bit at 25 fps; a second pair the same day gave 759 direct / 561-572 buffered
    (`clearhdr-design.md:127-133`). **No measurement on this rig writes ≥ 600 MB/s for longer than 5 s**; the highest rate Core has sustained is 525 MB/s
    for 60 s (M3) and the longest clean runs are 415 MB/s for 600 s, three times." F4 §2.2, V-F4 rows 1-3, 8-9.
11. (Addition) **Three, not two, clean 10-minute (B) takes.** `dng-chain-answer.md:111`: "A0, A1 (one take each, `a40112a`), and six earlier long
    takes". New: "C0101 (2026-10-26, `114bfb9`, 35 % full, untrimmed, 15019/15019), A0 and A1 (`a40112a`, trimmed, WebUI closed); 3 of 4 ten-minute takes
    on trimmed or lightly filled drives, A2 the unexplained fourth; 4 of 4 three-minute (B) takes clean without the whole-fs `syncfs` (2 of 2 on today's
    default policy)". V-F4 row 9, V-F5 E2.
12. (Addition) **M3 wrote 525 MB/s, not 500; and `hardware-log.md:775` is wrong as a rule.** F5's "~500 MB/s (11.4 MB/frame)" → 2632 × 11.96 MB / 60 s =
    525 MB/s (V-F5 E1; the brief's figure). The log entry's "the numbering counts written frames, so capture gaps leave no hole" holds only with the speed
    ramp on (`countOnly = settings_.fpsSpeedRamp`, `CameraController.cpp:9022@6ef0ddc`); with it off a gap leaves a numbering hole (V-F5 E5). Also:
    C0016 (2026-10-29, 310 missing in 30 holes) is an SDR 12-bit lossless 25 fps take, not a (B) take (V-F5 E3).

## 6. The decisive tests, in order

Rig-free first, then the read-only rig state, then the storage curve with Core stopped, then the 60 s cycle windows, then the 10-minute soaks. The
E-plan step is the one in `dng-chain-answer.md` §6. Every take records the confounder set of §2.5; drops are judged from `dropped_gap_estimate`,
`dropped_queue_full`, `dropped_copy_slot`, `peak_queue` and frames against WAV seconds × fps, never from `takes.sh missing` alone.

| # | Test | What it measures | Tool | Minimum duration | Pass criterion | What it decides | E-plan |
|---|---|---|---|---|---|---|---|
| 1 | **DNG clock forensics of the 2026-10-28 shooting-day clips** (38 clips on the SEAGATE disk, 10-27 `temp:` build, 4K SDR 12-bit lossless at 25/33/50 fps offered) | per clip: fps and gaps from `ExifIFD:DateTimeOriginal` counts per full second against the clip's fps; `ImageWidth`, `BitsPerSample`, compression from one DNG; the same on the A2 clip if still on the card (mode and ramp state) | `exiftool` per folder, the `hardware-log.md:889-897` method | zero rig time; minutes per card offline | a clip at 33 or 50 fps with full-second counts equal to fps throughout | the first multi-minute 4K lossless datum above 25 fps under a real writer load, or none; whether A2 was in the asserted mode | F5 §8; feeds E4 |
| 2 | **Rig state, read-only (E0)** | `tdn` count in both tuning files; the journal's `tuning file`, `capture scheduling`, `pixel-rate cap`, `Adjusting mode minimum`, `RAW buffers`, `camera configured … packing=` lines; which libcamera is mapped; `LimitNICE`/`LimitRTPRIO`/`Environment`; `clk_sys` (expect 333333333); `nvme id-ctrl` (`mn`, `fr`, `vwc`, `hmpre`); `blockdev --getss`; `findmnt`; `df`; `swapon --show`; governor; HDMI mode; `get_state` → `fps_speed_ramp`, `storage_preroll_auto`, `ladder_enabled`; `/proc/cmdline` for `rp1_cfe.track_csi2_errors` | one shell block | every later number's precondition | all: whether TDN is on at all, which libcamera build runs (≈ 10 ms of (B)'s thread cost), whether the drive can hold 373 GB, whether the priorities are in effect | E0 |
| 3 | **Drive sustained-write curve, Core stopped** | the pSLC knee and the post-cache plateau on this x1 link; temperature; link state; flush counts | `sudo fio --name=w --filename=/media/RAW/fio.bin --rw=write --bs=1M --direct=1 --iodepth=32 --numjobs=1 --size=400G --write_bw_log=… --log_avg_msec=1000` on the trimmed, cooled drive; `/sys/block/nvme0n1/stat`, `nvme smart-log` temperature, `lspci -vv … LnkSta`, `dmesg -w` per second | **10 min** (knee at ~1.5 min, thermal plateau at 5-10 min) | plateau ≥ 700 MB/s for all 600 s, no thermal dip, link at 8 GT/s x1 throughout | (A)'s storage gate for uncompressed 2160 (622 MB/s); below ~650-700 ⇒ 10-bit (518.5) or 2076 (598.0) | E4 storage part (answer §6 item 4) |
| 4 | **The real file pattern, Core stopped** | four-writer exFAT create + write at (A)'s rate; the per-dentry constant c | `/home/pi/ab-tests/variant2.py` at 50 files/s × 12,443,140 B, one folder, 12-deep queue, per-file open/write/close latency vs index; `iostat -x 1 nvme0n1`; or a 30,000-file `open(O_CREAT)` loop with names `cDNG_26-11-01_C0001_%09d.dng` timing each create (slope ÷ 5 = c) | 10 min | 50 files/s held for 600 s, queue never above 6/12, per-file latency at file 30,000 no worse than at file 1,000 by more than 10 ms | whether the O(N) create scan overruns the 20 ms period before minute 10, and whether Core's buffered 4-writer path reaches 622 MB/s at all | F4 §4 step 2; V-F4 §5 |
| 5 | **Stage-1-only idle windows** (Core running, not recording) | CFE frame-start cadence per mode with the pipeline idle; Config re-queue latency | drop-in `LIBCAMERA_LOG_LEVELS=RPI:0,RPiStream:0` + `LIBCAMERA_LOG_FILE=/dev/shm/rpi0.log`; `be_cycle.py` on the `CFE Image buffer dequeue` timestamps; `grep 'CFE Config'`; `csi2_errors` and `dmesg | grep -c Orphanded` before/after (needs `rp1_cfe.track_csi2_errors=1`) | 60 s per mode (3840x2160 50 fps; 3840x2076; Clear HDR 25 fps); one 10 min idle window at 4K50 for D-PHY integrity | frame count = 60 × fps ± 1; every dt = period ± 0.05 ms; counters 0; no Orphanded line | clears the sensor/link/RP1/CFE stage per mode, so any gap while recording is the cycle or the pool | F1 §4; V-F1 §5 |
| 6 | **(A) 60 s cycle windows** | S1-S4 and the cycle per frame while recording; the four counters | same drop-in, `APERTAR_STORAGE_PREROLL=0`, WebUI closed, ramp off, ladder off, trimmed; `takes.sh 1 60` at 3840x2160 12-bit uncompressed 50 fps; `python3 -I working/tools/be_cycle.py /dev/shm/rpi0.log`; then 3840x2076; then lossless; then **with `imx585_notdn.json`**; then one arm with `APERTAR_DNG_WRITEBACK=0` and one idle `dd conv=fdatasync` repeat on this build | 60 s per arm (~3000 cycles; the SDR pool hides ≤ 2-6 frames) | gap 0; cycle median ≤ 20 ms and p90 ≤ 20 + slack (~64 ms with 4 buffers, 144 with 8) | whether M3's 22.7 ms reproduces on `6ef0ddc`; S2 ≥ 17 ms ⇒ BE-bound and TDN off applies (S2 falls with bytes); S2 small with a long cycle ⇒ software latency (FIFO, WebUI pause, config queue, pipelining); S2 unchanged with TDN off ⇒ compute-bound, no configuration lever left; the writeback arm separates the BE-bytes and writeback suspects | E4 → E5 (+ V-F6 §5 arms) |
| 7 | **(B) 60 s cycle windows** | the first 25 fps cycle measurement in the kb, linear and Log, default tuning and `_clearHDR_notdn`; S2 before and after | same instrument at 3840x2200 16-bit 25 fps, A0 protocol | 60 s per arm | cycle median ≤ 40 ms; p90 ≤ 36 ms with the default tuning ⇒ the copy is optional; S2 ≈ 35 → ≈ 12 ms with TDN off ⇒ memory-bound | the real (B) margin; whether TDN off is mandatory; Log's cycle cost on the current build | E5 |
| 8 | **(B) 10-minute soaks on `6ef0ddc`** | the shipping build under the A0 protocol | `takes.sh 1 600` × 3 linear, × 3 Log, then one with the WebUI open (`APERTAR_WEB_PREVIEW_RECORDING_FPS` 30 vs 0); `top -H -b -d 1` and `hwcount.py` on the CameraManager tid during one take (CPU and IPC) | 10 min each (A2's class shows in 60 s, the 10-31 class in 5 s, the drive class needs minutes) | 0 in every counter, `peak_queue` ≤ 2/12, stop `syncfs` < 200 ms in 3 of 3 | (B) linear YES on the shipping build; Log's status; whether "WebUI closed" stays a condition | E2, E1 |
| 9 | **(A) 10-minute acceptance** (only after tests 3 and 6 pass) | the whole chain at 622 MB/s (or 518.5 / 598.0) | three interleaved 10 min takes in the chosen format; `peak_queue`, `/sys/block/nvme0n1/stat`, temperature, `dmesg` per second; one take with the WebUI open | 10 min × 3 | as test 8; `peak_queue` ≤ 3/12 throughout (a climb from minute ~2 is the post-pSLC rate binding) | (A) YES UNDER CONDITIONS in that format, or the storage fallback | E4 acceptance |
| 10 | **Residual arms as needed** | the three-client test; per-thread FIFO and `DONTNEED=sync` as separate arms with `/proc/<pid>/task/<tid>/schedstat` and a `bpftrace` count of `lru_add_drain_all`; A2 twice and A1 once interleaved with `/proc/vmstat` and `top -H` per second; the pre-roll A/B | as the answer page's E1, E3, E6, E7 | 60 s arms, interleaved three times | each arm against its control's spread | which of the small levers to keep | E1, E3, E6, E7 |

Decision rule for the whole page: (B) moves to YES on the shipping build when test 8's three linear takes are clean; (A) moves to YES UNDER CONDITIONS
only when test 3 (storage) and test 6 (cycle) both pass and test 9 confirms; a cycle that does not move with TDN off closes the configuration path for
(A) at 50 fps (fallbacks: 40 fps, BE decimation or a raw-only take, each code).

## 7. Open questions and unverified claims that remain

1. **Does the Pi's tuning carry `tdn`?** `/home/pi/Tuning-Files/defaults-pisp/imx585.json` and `imx585_clearHDR.json` are in no repository; every
   TDN-on number on this page assumes it (probable, strongly). One grep (test 2). If not, the top lever is already in effect and M3's loss is not the back end.
2. **The SDR back end has never been timed**, idle or recording; the whole (A) cycle verdict rests on two measurements in different configurations and
   two models that disagree (10-14 vs 19-20 ms). Memory- or compute-bound at COMP1 input: unmeasured (test 6, S2 with and without TDN).
3. **Why M3 (22.7 ms) and the pre-roll (≤ 17.5 ms) disagree**: crop mode, uncompressed writer path (525 vs 344 MB/s of page-cache traffic), untrimmed
   82 % drive, 60 s vs 1.9 s, build, buffer count, WebUI state (unknown in both), tuning (same file if nothing changed, probable). Unresolvable from the
   record; M3 was never repeated (test 6).
4. **The drive's post-pSLC rate on this x1 link** and **the per-dentry constant c** (80-250 ns estimated; A0/A1 exclude only ≳ 450 ns): the two unknowns
   that decide (A)'s storage gate; neither has ever been measured (tests 3 and 4). The 1 TB E27T's cache size is in no reachable source; the drive-review
   hosts (tomshardware, techpowerup, computerbase, tweaktown, kitguru, storagereview, corsair, pipci) were blocked in every session of this phase and
   every drive figure is a search snippet.
5. **Which libcamera runs on the Pi today**: system qbc `7e9fef0` (16-bit swap + SW raw stats on the CameraManager thread) or the `~/opt/libcamera-apertar`
   L1/L2 fork loaded by drop-in on 2026-10-26. Worth ≈ 10 ms of thread time per frame in (B) and 12.7 MB/frame of DRAM (`grep libcamera /proc/<pid>/maps`).
6. **A2's mechanism** (4.4 ms/frame of capture-side effect from removing a per-file `sync_file_range` that initiates no I/O), its WebUI state, its real
   mode (asserted, never read from a DNG) and what else ran (`~/ab_matrix.sh` is in no repo); and the writer-side mechanism in general (DRAM vs fabric/IOMMU
   vs IRQ) behind T22's buffered-`dd` gaps.
7. **Log over any take longer than ~5 s**; the LUT's real cost on the copy worker (4-17 ms estimated); its DRAM effect on the back end.
8. **The 25 fps cycle itself**: no RPI:0 window at 25 fps exists; the (B) margin is derived from 30 fps windows under the assumption that the per-frame work
   is rate-independent (T22 shows it is load-dependent).
9. **The actual thread priorities on the Pi**: no `capture scheduling` journal line is quoted anywhere in the kb; `LimitNICE=-5` is recorded present from a
   2026-10-25 `systemctl cat` only; the run-queue wait per frame was never measured. The FE Config node (24 ms tolerance at 50 fps) has never been seen
   starving; whether the installed pipeline YAML reads `num_cfe_config_queue` is unverified.
10. **Stage 1 at 50 fps**: live `clk_sys` never read (a mis-built overlay could leave it at 166.7 MHz while the fork reports 646.7 Mpix/s); CSI-2 error
    counters never read at 4K 50 fps or at 30 fps Clear HDR; whether `rp1_cfe.track_csi2_errors=1` survived later reboots; D-PHY integrity at 1782 Mbps
    (the 1500 Mbps bin, programmed out of range) over 10 minutes at 70 % link load; 3840x2076 timing never isolated at 50 fps; the fork's `pixel-rate cap
    = 646.667` journal line described but never captured verbatim.
11. **The raw transport of M3** (COMP1 vs packed: probable COMP1 from the format rule; the journal's `camera configured … packing=` line settles it for the
    current build) and whether the fork keeps upstream's CSI2 → PISP1 rule for 12-bit SDR with WDR off.
12. **Hardware behaviour of a PiSP BE job with `PISP_BE_BAYER_ENABLE_TDN` set and no TDN DMA** (the mid-stream `NoiseReductionMode=Off` case): the kernel
    read says the driver clears the enable bits when the input address is missing (probable, V-F2 row 14); libpisp would not catch it (V-F6 row 2a). Set-at-start
    avoids the state. The BE clock (`clk 7`, never set by the driver) and AXI QoS 0 (confirmed in the register write, effect unverifiable from here).
13. **Whether the writers' 368,640 / 491,520 B scratch stays cache-resident** (moves (A)'s DRAM figure between 4.35 and 5.60 GB/s); the COMP1 row decoder's
    CPU cost (8-20 ms per DNG estimated, the largest unmeasured CPU term in (A)); the kernel-side split of the ~0.4 core of "everything else" at 50 files/s
    with a 30,000-entry directory; the exFAT sector size (512 assumed; 4096 would cut every `s_lock`/FAT count 8x); whether the drive advertises a volatile
    write cache (decides whether the 1 s fsync sends 50 FLUSH/s at (A)); whether anything lists the live clip folder during a take.
14. **The pre-roll's WebUI state and tuning** (unrecorded), the speed-ramp state during A0/A1 (probably on, harmless by code), and which board (4 GB recorded;
    "4 or 8 GB" asked) the next tests run on (RAM-mode cushion 3.2 vs ~9.6 s; swap in use on 2026-10-26).
15. **Practical DRAM ceiling** 7-10 GB/s for a mixed stream set is an estimate from three indirect web figures (single-core memcpy/memset, STREAM snippets);
    openbenchmarking.org was unreachable. The averages stay below either band; the contention effect on the BE at 50 fps is the unmeasured part.
16. **The reference the operator raised**: cinemate's off-repo deliverables (`RATE-MATRIX-RESULTS.md`, the May-2026 workbook) may hold counted takes; none is
    on disk; no counted cinemate take of either mode exists in its docs or handbook (F5 §6, confirmed V-F5).
17. **F5's probability ranges** (5-20 % for (A) as shipped, 65-85 % for (B) under the A0 protocol, etc.) are judgment on n = 2 and n = 4; V-F5 keeps the
    ordering and drops the numbers. This page carries the ordering only.

## 8. Where the detail is

All in `working/dng-chain/F/`. The verifications override the reports where they disagree.

- `FEAS-BRIEF.md`: the question, the budget method, the facts fixed before this phase, the labelling rules.
- `F1.md`: sensor, CSI-2 link, RP1 pixel-rate cap, CFE raw pool and skip mechanism (kernel `cfe.c`), stage-1-only test; `V-F1.md`: pools 4/8 confirmed, L_max
  = N·T − R, the 2-deep FE Config queue, path and cite fixes.
- `F2.md`: the serial cycle stage by stage, both modes, with Appendix A reconciling every cycle measurement and Appendix C on TDN; `V-F2.md`: bracket −2.7 to
  ≥ +2.5 ms, the L2 counter-model, the pre-roll's probable 8 buffers, (B) margin +2.0 to +5.3, the `APERTAR_TUNING_FILE` conditional, the kernel reading of
  the runtime TDN toggle.
- `F3.md`: CPU per thread and DRAM bytes per actor, both modes, scheduling; `V-F3.md`: bytes reproduced, practical ceiling lowered to 7-10 GB/s, the LUT model
  corrected to 4-17 ms, the reclaim attribution removed, Log net +0.62 GB/s.
- `F4.md`: byte rates, the drive and link record, the exFAT driver model (create scan under `s_lock`), stall cushions, storage levers; `V-F4.md`: (A) MARGINAL
  with direction undetermined, C0101 added, the `dd` figures' context, the direct-I/O zero-fill rule.
- `F5.md`: the catalogue of every counted take in both families, the near-misses, the 85-commit build history, the operator's cinemate reference checked,
  a probability assessment; `V-F5.md`: frequencies corrected (525 MB/s, 4 of 4 three-minute takes, C0016 reclassified), the direct diff of the completion path,
  the 2026-10-28 clips as a free datum.
- `F6.md`: the full lever catalogue (sensor to drive), notes on the load-bearing ones, the four-path roadmap, the cinemate comparison table; `V-F6.md`: the
  writer-side 1-3 ms bound refuted, A2 reinstated, the E27T revision, the 373 GB precondition, the (B) post-TDN margin corrected to +19-24 ms, the libpisp
  dirty-flag caveat, IPA alternate-frame skipping at 50 fps.
- Earlier pages this one connects to: `working/dng-chain-answer.md` (§2 residual drops, §5 the nine commits and the recommendations, §6 the E-plan),
  `working/dng-chain/STATUS.md` (the firm findings; items 20 and 22 corrected above), `working/research-30fps-answer.md` (the 30 fps cycle study and
  `be_cycle.py`), `working/storage-answer.md` (the media profile), `working/drop-frames/README.md` (the campaign record and "done means").
- Tools: `working/tools/be_cycle.py` (S1-S4 split from an RPI:0 log), `hwcount.py` (PMU of the CameraManager thread), `libcam_stages.py`, `dngmeasure.py`,
  `takes.sh`, the DNG-clock method at `lessons/hardware-log.md:889-897`.
