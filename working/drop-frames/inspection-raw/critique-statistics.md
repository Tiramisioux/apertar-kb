# Critique of `verdict-draft.md` (section 8): statistical inference and experimental design

Adversarial pass, 2026-11-02, desk only, restarted on Opus (this file replaces the earlier run's). Lens: are the p-values
and power claims right; are order, uptime, drive fill, trim state, process age and UI version handled; does each test
actually discriminate; is the stopping rule sound; is anything claimed from n = 1.

Status words as in the KB: **confirmed** (read in source or record, or arithmetic on recorded numbers), **probable**
(inferred, reason given), **unconfirmed** (the measurement is named). `draft:N` = line N of `verdict-draft.md`.

Arithmetic: `scratchpad/critic/b1sim.py` (pure Python, exact permutation tests with midranks, Monte Carlo for B1 power,
seed 7, 4,000 runs per scenario). I re-ran the statistics examiner's `inspection/stats.py`, and every number the draft
copies from it reproduces (Fisher 8.6e-67, rank-test 0.057 / 0.029, dispersion 66.1, r = 0.65, the 1.2 %/h slope at p = 0.25).

## 0. Verdict

**Needs revision.** The take-level statistics are computed correctly, and the draft is right to call the frame-level
p-values invalid. But four conclusions rest on evidence that does not support them:

1. `min_free_kbytes` as the "probable active ingredient" of #80. #80's own counters show the watermark knob never engaged.
2. A0's boot age "refuted (record)". The record holds a crash and reboot between the two timestamps the draft uses.
3. U1 "closes the regression since A0 in the UI". U1 runs under `sync`, where neither UI version is expected to lose.
4. The boot-1 UI A/Bs called uninterpretable "because of the drift". The draft's own analysis says there was no drift before 21:50.

The decisive tests also have design defects:

- **B1** may null the very effect it tests: a Core restart and a trim before every take is the condition in which
  writer was clean on 11-01. Its p-thresholds assume a randomization the design does not perform. Its primary decision
  can turn on 0 versus 1 lost frame in one take.
- **B3 (a)-(c)** start from a memory state in which no watermark is ever reached. Its decision rule contradicts itself.
- **T1** reproduces #69's position, not A0's.
- **B4** cannot fit on the drive.

## 1. Numbers re-checked

| Draft claim | Draft value | Recomputed / record | Status |
| --- | --- | --- | --- |
| frame-level Fisher, writer vs sync (draft:51) | 8.6e-67, "invalid" | 8.55e-67; invalid (dispersion 66.1) | confirmed |
| take-level rank test 4 vs 3 / 4 vs 4 (draft:32, :51) | 0.057 / 0.029 one-sided | 0.057 (2/35) / 0.029 (2/70) | confirmed arithmetic; the 4 vs 4 is not like-for-like (R9) |
| #78 minute 10 (draft:83) | P(>= 18 \| 0.78) < 1e-12 | Poisson 8.1e-19. With a negative binomial fitted to minutes 1-9 (mean 0.78, var 1.44, k = 0.91): 6.8e-7 per minute, 6.8e-6 for the max of 10 | regime change survives; the stated number uses the independence the draft rejects (R6) |
| `queue_budget` (draft:136) | 1.40-1.70 GB, lines 335-388 | compared takes: #69 1.549, #70 1.474, #71 1.484, #72 1.446, #74 1.531, #75 1.483, #78 1.403 GB (`takes-2026-11-01.raw.txt:335, 341, 347, 353, 364, 369, 384`); max in 335-388 is 1.578 (pre-roll #73, :358); 1.70 is a boot-1 value (:225) | confirmed; 1.70 would imply MemAvailable 3.73 GB, not the stated 3.2-3.5 |
| deletions before #78 (draft:89) | ~140 GB | The draft divides a decimal-GB frame sum by "932 GB". The volume is ~932 GiB, about 1.0e12 bytes: `fstrim` freed 917.4 GiB on 10-30 (`hardware-log.md:710`), "volume size (917 GiB)" (`:725`). 97 % of ~1,000 GB = 970 GB, against the no-deletion sum of 1,043 GB, gives **~70 GB deleted** (one 3-min take). Per-minute fill is 2.49 %, not 2.67 % | probable; `df -B1 /media/RAW` gives the size |
| kswapd separation (draft:21, :62) | "50-70x, no overlap" | true for #74/#75 (47 k, 58 k) vs #70-#72; #78 is 586 k per 10 min = 176 k per 3 min, i.e. 17-20x | confirmed; say which takes |
| writer take = 65-74 % of bytes written (draft:47) | 75.5-76.2 GB per take | #70-#72 wrote 4,349-4,469 frames x 16.6 MB = 72-74 GB; 49.5-56.5 GB of that = 67-76 % (at 16 KiB pages) | minor |

## 2. Refuted or weak claims

**R1. "`min_free_kbytes` 64 MiB did it: probable yes" (draft:53; also :33-34, :80, :366).**
Refuted by the take it is drawn from.

- Raising `min_free_kbytes` raises min, low and high together. WMARK_MIN is set from `pages_min`
  (`mm/page_alloc.c:6127, 6164`), and LOW and HIGH are added on top of MIN (`:6171-6177`). So kswapd wakes **earlier**
  (at ~80 MiB free instead of ~20 MiB), not later.
- #80 recorded `pgsteal_kswapd` = 0 and `kswapd_low_wmark_hit_quickly` = 0 (night report §2, row 80). Free memory
  therefore never fell to the raised low watermark. With stock watermarks it would not have reached the lower ones
  either.
- Every mechanism through which the knob acts was idle in #80: the kswapd wake, direct reclaim below low, and the
  throttle below min/2. The counter the draft cites in support (draft:53) is the evidence that the knob did nothing.
- The probable carrier of #80's zero reclaim is its start state: MemFree 2,758 MB after the 23:13 format freed the old
  clips' cache, against 507-788 MB before #74, #75 and #78. A second carrier is the empty, trimmed drive.
- Status: **probable** (source plus reported counters).
- Fix: rate "`min_free_kbytes` did it" as **not supported by #80; no take isolates it**. Strike "`min_free_kbytes` is the
  knob" from the B3 expectations and the 8.4 default discussion until a take shows it engaging, i.e. `pgsteal_kswapd` > 0
  with the knob at stock.

**R2. B3 cannot discriminate (a), (b) and (c); its decision rule contradicts itself (draft:265-283).**

- Cells (a)-(c) run `sync` on an empty, trimmed drive after `rm`. Under `sync`, a take's own pages are dropped every
  second, and the deletes clear the older cache, so these takes start with MemFree in the GB range, as #80 did.
  By R1, no watermark is reached and all three cells are predicted clean. Then (b) = (a) and (c) = (a) say nothing
  about either knob.
- The rule says "(c) clean and (b) not **(or (b) = (a))**: add only `min_free_kbytes`" and also "Both (b) and (c) clean
  with (a) clean too: the knobs are optional". With all three clean, both branches fire with opposite actions.
- n = 1 per cell, the order is fixed ((a), (c), (b), (d), (e), (f)), and the cells are split across two evenings with
  (a)-(c) on one and (d)-(f) on the other. Fill is therefore confounded with the evening (boot) and with position.
- Overdispersion makes n = 1 classification weak. Under the writer arm's take-level dispersion (k = 1), a cell with a
  true 0.13 % residual (20 per 10 min) passes "clean = <= 5 lost" with probability 1 - (20/21)^6 = **25 %**. At 10 per
  10 min it passes 44 %. Under Poisson it would pass < 0.01 %.
- No cell has `min_free_kbytes` alone at 70 % fill, which is where #78 lost and where the draft expects the knob to matter.
- `fallocate` (and the `dd` fallback) make one contiguous fill file. #78's near-full state came from many written and
  deleted clips, so its free space was fragmented. If the near-full cost is exFAT bitmap search, a contiguous fill
  under-reproduces it (**probable**).
- Fix:
  - Set the start memory state explicitly in every cell: read ~2.5 GB of an existing file into the cache before the take
    (`dd if=/media/RAW/fill.bin of=/dev/null bs=16M count=160`) and record MemFree. That reproduces #74/#75/#78
    (0.5-0.8 GB free).
  - Add (c') = `min_free_kbytes` alone at 70 % fill.
  - Fill with DNG-sized files, deleting every other one.
  - Randomize the cell order within each evening.
  - Two takes per decisive cell.
  - Rewrite the rule as a table keyed on the full ((a), (b), (c)) outcome triple.

**R3. B1 can null the effect it tests, and its thresholds are not design-based (draft:200-240).**

- *Restart and trim before every take.* The mode is a function-static read once per process
  (`adac040:src/cdng/CdngEncoder.cpp:83-96`), so the restart per arm is unavoidable. But a fresh Core start also requests
  a full-drive trim (`adac040:src/ApertarCoreApp.cpp:10904`), and every storage pre-roll ends with one (`:11272`).
  So every B1 take is "first take of a Core process, on a fresh trim, after a 0.7 GB pre-roll". On 11-01 that was the
  position of #69 (writer, 1 lost) and #74 (sync, 0). The losing writer takes (#70-#72) were the 2nd-4th takes without
  a restart (PID 826 throughout, `raw.txt:333-353`).
- *Simulated B1, per-take negative binomial, sync ~ Poisson(0.3):*

  | Scenario | complete separation | one-overlap extension | no separation |
  | --- | --- | --- | --- |
  | writer as on 11-01, i.i.d. NB(64.8, k = 1) | 90 % | 10 % | 1 % |
  | first-after-boot writer take like #69 (mean 1) | 28 % | 64 % | 8 % |
  | restart resets the writer state (every writer take like #69 / A0) | 2 % | 12 % | **85 %** |

  In the last case the rule reads "the 11-01 difference was order, the Core restart or chance" (draft:232-233). That
  reading would be wrong: the restart would be the lever.
- *Ties.* On an empty, trimmed drive, the sync takes will most likely all be 0. With sync = {0, 0, 0, 0}, a writer
  first-after-boot take of **0** gives p = **0.071**; a take of **1** gives p = 0.014 (complete separation). The primary
  decision turns on one frame in one take.
- *Randomization.* The design tosses one coin for the labels on a fixed ABBA | BAAB sequence: 2 possible assignments,
  so the design-based p cannot go below 0.5. The quoted 0.014 assumes all 70 splits are exchangeable, which a fixed
  sequence does not provide under drift. With a balanced random order inside each block (6 per block), the minimum
  one-sided p is 1/36 = **0.028** for 2 blocks and 1/216 = 0.0046 for 3 blocks.
- *Mixed sidedness.* The rule mixes one- and two-sided thresholds (0.014 one-sided, then "6 vs 6 p = 0.0022", which is
  two-sided; one-sided is 0.0011).
- *Extension.* The extension block A B A B gives A the first-after-boot position a second time, and ABAB does not cancel
  a linear drift (A at positions 1 and 3, B at 2 and 4).
- Fix:
  - After each reboot, record one unscored warm-up take.
  - Within each arm, measure a pair: restart, take 1 (scored as position 1), take 2 without restart (position 2).
    This puts restart position into the design rather than fixing it at "always".
  - Randomize the order within each block; analyse with a within-block (stratified) permutation test.
  - State every threshold one-sided.
  - Make the extension block a coin-chosen ABBA or BAAB.
  - Add to the no-separation branch: "check B4's consecutive writer takes before concluding chance".

**R4. "U1 closes the 'regression since A0 in the UI' reading in 35 minutes" (draft:105; U1 at :307-323). Non-discriminating.**

- The regression reading (`hardware-log.md:925-927`) is about losses under `writer`: A0 was writer, and the 11-01 losses
  were writer.
- The draft's own robust finding is an interaction: UI drawing + writer = losses, UI drawing + sync = none (draft:104).
- U1 compares `ea44bd7` and `c13b846` under `sync`, where both are predicted clean (#74, #75 and #80 were clean with
  `c13b846`). Two clean arms therefore cannot close a writer-only regression.
- U1's order (c13b846, ea44bd7, c13b846, ea44bd7) is unbalanced, and n = 2 per arm.
- Fix: the UI half of the A0 question is T2(a), a writer-mode take at a losing position. Run `ea44bd7` vs `c13b846`
  interleaved ABBA under writer at positions 2+. Keep U1 only as the "does the branch cost anything under sync" check,
  and drop the closure claim.

**R5. "Every UI A/B of 19:46-22:20 ... drifted ... without a same-time control" (draft:94-96) contradicts draft:55.**

- The draft finds the 19:09-21:03 baseline flat (slope 1.2 %/h, p = 0.25), with a step only after 21:50. The UI A/Bs
  before 21:50 were therefore taken against a stable baseline.
- #30-#33 were interleaved with baseline takes (#28 20:18, #29 20:20 | #30-#33 20:25-20:34 | #34 20:41, #38 20:55).
- The four GPU-work-reducing takes and the four plane takes each sit below **all ten** pre-step baselines (5.33-10.60 %):
  - #30 preview held 0, #31 12 fps 2.88, #32 aids off 1.67, #44 CPU peaking 3.88 %;
  - #46 0, #48 1.93, #49 3.13, #50 3.42 %.

  Exact one-sided rank p = **0.001** each, exchangeability assumed. There is also a monotone dose-response in preview
  rate: 0 / 12 / 25 fps gives 0 / 2.9 / ~7.5 %.
- The plane "contradicts itself" (#58 aids off 7.22 % vs #47-#50 1.8-3.4 %) only across the step the draft identified.
  #58 is below all three post-step baselines (11.1-18.1 %).
- These are n = 1-per-variant takes, the plane takes are order-confounded, and each one follows a UI restart (a drop-in).
  Still, they are the strongest take-level contrasts of the night: stronger than writer vs sync (0.057), and the cap
  takes are better designed.
- They bear on the open mechanism ("why the UI matters"): under writer, losses scale with the UI's GPU work.
- Fix: reword Q3. Keep the decisions (not needed under sync), but carry an interleaved writer-mode dose-response
  (`APERTAR_UI_PREVIEW_RECORDING_FPS` = 0 / 12 / unset, ABBA) into B2 as the mechanism test. It discriminates
  bus/GPU contention from allocation-driven stalls, alongside M4-M6.

**R6. #78's "P(>= 18 | 0.78) < 1e-12" (draft:83) uses the frame independence the draft rejects at draft:51 and :60.**

- With the negative binomial fitted to minutes 1-9, the tail is 6.8e-7 per minute (6.8e-6 for the max of ten).
- The 18 may be a few multi-frame episodes. The KB's journal extract has no `drop[...]` lines to tell (`raw.txt` has
  none, grep).
- The conclusion "minute 10 differs" survives. The number does not.
- Fix: quote the dispersion-aware tail, and get the gap timestamps for #78 from the Pi:
  `journalctl -u apertar-core -b -1 --since 23:11 --until 23:12:10 | grep 'drop\['`.

**R7. "A0 ran >= 7.4 h into its boot" / "early in the boot: refuted (record)" (draft:36-37, :54). Unconfirmed, not refuted.**

- The UI start stamp is 2026-10-30 01:04:19 (`hardware-log.md:925-926`). The same log records the NVMe dying at 01:43-01:45
  on 2026-10-30, followed by "a reboot brought it back" (`:717-719`). Boot clocks were wrong until NTP (`:797-811`).
- The co-factors examiner concedes that "the two stamps cannot both be right on one boot" (`cofactors.md:88`), yet the
  draft upgrades the reading to refuted.
- The data fit "early in the boot" at least as well as "fresh Core". #64 was the first take after a Core restart, at
  3 h 20 min of uptime, and lost 11.1 %: a counterexample to fresh-Core-protects. The record holds no counterexample to
  fresh-boot-protects (#69 at 1 min: 1 lost; #3 at 14 min lost 6.97 % but was the second take of its process, after #2's
  RAM-buffer safety stop).
- Fix: status **unconfirmed**. Settle with monotonic stamps, which ignore the wall clock:
  `journalctl --list-boots | grep 2026-10-30`, then for each boot
  `journalctl -b <id> -u apertar-core -o short-monotonic | grep 'recording clip'`. A0's line shows seconds since its boot
  (< 1,800 s = early in the boot; > 20,000 s = hours).

**R8. The #72 -> #74 confounder list omits the trim and the pre-roll (draft:63-65, "the only other change").**

- A Core start requests a full-drive trim (`ApertarCoreApp.cpp:10904`), and the pre-roll writes 0.7 GB, deletes it and
  trims again (`:11272`; #73 wrote 704,856,844 bytes, `raw.txt:360`). The hardware log confirms both trims at a Core
  start (`hardware-log.md:909-910`).
- So "first take after a Core restart" = "first take on a freshly trimmed drive after a 0.7 GB write/delete", for #69,
  #74, #64, A0-A2 and, through the format, #80.
- Effect probably small: the 10-30 stalls needed ~0.9 TB without a trim and had a queue-full signature, while #70-#72
  were at 75-300 GB since the 22:27 trim with the queue at 2/12. But the confounder must be named.
- B1's per-take `fstrim` neutralizes it going forward; T1 and B6 do not separate it from the restart.

**R9. "0.029 with #80" (draft:32, :51, :61) pools a different treatment into the sync arm; #74 carries little information.**

- #80 differs from the other sync takes in three sysctls, the format and the empty cache. The draft itself says so at
  :33-34. Using it to halve the p-value double counts.
- By the draft's own observation that a first take after a restart can be clean under writer (#69 1, A0 0, A1 0), #74 is
  the sync take least able to discriminate.
- Like-for-like readings:
  - position-matched pairs: (#69, #74) = (1, 0) and (#70, #75) = (34, 0). Two of two favour sync; sign p = 0.25.
  - excluding the position-1 takes: writer 0.76 / 3.40 / 1.58 % vs sync 0.00 / 0.17 %, rank p = **0.10** one-sided.
- Fix: report 0.057 as the only like-for-like number, with the position-matched reading beside it. Drop 0.029.

**R10. "Uptime and fill ran against sync, which helps the claim" (draft:51, :65-66).**

- This needs uptime and fill to be monotone-harmful. The draft rates a monotone drift "not supported" (#72 < #71) and fill
  below ~94 % harmless.
- A non-monotone within-boot course (rise then partial fall, as #71 -> #72) could favour later takes.
- Fix: "neutral at best".

**R11. "2026-10-26 measured the same pair 5 vs 5: no difference" (draft:52).**

- Those were 10-s **lossless-JPEG** takes on Core `f60e301`, losing 16-40 % at an encoder- and capture-limited 19-22 fps
  (`hardware-log.md:64-71`). That is a different failure regime and a different write path.
- Fix: remove it from the basis of the dirty-limit row. The row stands on the `Dirty` peaks and the source alone.

**R12. Frame-count bounds drive decisions after independence was refuted (draft:70-72, :318, :334-336).**

- Under the writer arm's take-level dispersion (k = 1), P(0 lost) = 1/(1 + mu). A clean take bounds mu < 19 at 95 %:
  - one 3-min take < 0.42 % (not 0.067 %);
  - one 10-min take < 0.13 % (not 0.02 %);
  - two clean 10-min takes (B6) < 0.023 %;
  - U1's two clean 3-min takes per arm < 0.077 % (not "0/9,000 < 0.033 %").
- Status **probable**: k under `sync` is unknown, since #78 is the only losing sync take.
- Fix: state bounds per take and per frame side by side, and size B6 by takes, not frames.

**R13. T1 does not reproduce A0, and its decision rule misses the most likely outcome (draft:285-305).**

- "A0's protocol = first 10-min take after a reboot" contradicts the draft's own claim that A0 was hours into its boot.
  T1 is #69's position (first take after a reboot), lengthened to 10 min.
- #69 already showed today's stack clean for 3 min in that position, and #70 lost from the next take at 5 min of
  uptime. So T1's likeliest result is clean early minutes and losses from minute ~4-5. The rule covers "0-2 lost" and
  "losing from minute 1" only.
- The uptime at T1's start is not fixed, though cooling to 55 C may take minutes, and #69 (1 min) vs #70 (5 min) shows
  that this variable matters.
- Fix: record uptime and start at a fixed one. Add the branch "clean <= 4 min, then losing", which means time since boot,
  not code. Once R7's monotonic check gives A0's uptime, run T1 at that uptime.

**R14. B4 is infeasible as written and confounds build-up with fill (draft:291-294).**

- Four 10-min takes at 16.6 MB x 15,000 frames = **996 GB**. A fully trimmed empty volume offers ~985 GB (917.4 GiB,
  `hardware-log.md:710`), and T1 does not start with a delete.
- Takes 3-4 would run at ~50-100 % fill, into the near-full regime of #78. A loss in take 4 after `drop_caches` would then
  read as "not reclaimable state" when it may be fill.
- Fix: `rm` between B4 takes, but keep the cache: `rm` frees the clip's pages, so emulate the cache by reading an
  equal-size file back before each take. Alternatively, use 3-min takes (75 GB each).

**R15. Mechanisms eliminated or decided from n = 1 or without a base rate (draft:113, :234-238).**

- "SCHED_FIFO 40 did not help, #22, which argues against C": one take at 6.16 %, inside the 5.33-10.60 % baseline spread.
  It cannot exclude even halving. The FIFO confirmation line (`capture scheduling: ... SCHED_FIFO`) is not in the KB's
  journal extract.
- M4/M5 decision rules ("`CameraManager` in `direct_reclaim_begin` with episodes >= 20 ms = A"; "a second with a lost
  frame and >= 40 ms of wait = C") have two gaps:
  - **Timing.** They need loss timestamps at sub-second resolution, but the plan polls `recording_dropped_frames` every
    10 s (draft:194), and the journal logs only the first, every 30th and multi-frame gaps (`statistics.md:296`).
  - **Base rate.** They have no reference: episodes or waits may be just as frequent in seconds without a loss, or
    under `sync`.
- Fix:
  - Enable `events/vb2/vb2_buf_done` in the same trace, so each frame's timestamp and sequence share the trace clock with
    the reclaim events.
  - Compute P(gap within 100 ms after an episode) against P(gap) in the take, and the same under `sync`.
  - Read schedstat per frame-period window, not per second.

**R16. "The drive slowed is contradicted" by `peak_queue=2/12` (draft:82-83). Too strong.**

- The queue grows only when the drive falls below the 415 MB/s stream.
- A partial slowdown (e.g. 550 -> 450 MB/s) keeps the queue at 2 but lengthens writeback and fsync, putting more pages in
  flight. That is consistent with #78's 3x per-minute reclaim (59 k vs 16-19 k).
- Fix: say "not shown". The 1 Hz write-latency log already in B0 step 5 settles it.

**R17. The hardware-log headline is left standing (draft:402-415).**

- `hardware-log.md:1012`, "page-cache pressure ... made ... lose frames; `APERTAR_DNG_DONTNEED=sync` fixes it", was
  "confirmed" after two clean 3-min takes (`:1043`).
- The draft's own take-level p is 0.057, order-confounded. The correction list fixes the mechanism sentence but not the
  causal headline.
- Fix: add a correcting entry. The counters show sync removes the reclaim regime (measured); "fixes the losses" is
  probable pending B1.

## 3. Missing

- **#76 (sync, 29 s, 49 lost, 6.86 %, Patrik editing the ladder in the WebUI; `takes-2026-11-01.md:85`).** This is the
  only `sync` take with a WebUI client, and it lost at writer-like rates. kswapd was not read, and short takes and
  command traffic confound it.
  - The draft's WebUI row says "no compared take had a client" (draft:140) and does not use it.
  - It bears on whether the reclaim regime is *necessary*: completion-thread load alone (the downsample on libcamera's
    thread) may suffice.
  - Settles: one 3-min `sync` take with one passive WebUI tab, after a clean `sync` take, with the vmstat deltas.
- **The night's stopping rule and multiplicity.** About 20 boot-1 interventions were tried one take each, and two of
  them gave a clean take (#30, #46). The plane's 0 did not replicate (#47-#50: 1.8-3.4 %). `sync` was chosen after that
  search, and the session stopped at the first clean 10-min take (#80, three changes at once).
  - Post-hoc p-values over a sequential search overstate the evidence. The draft never names optional stopping.
  - B1's pre-registered rule is the cure: write it into the KB before the first B1 take.
- **A third "fresh process clean, then rising" series.** After the UI restart for the plane: #46 0 -> #47 1.82 ->
  #48 1.93 -> #49 3.13 -> #50 3.42 % (Spearman rho = 1, exact one-sided p = 1/120 = 0.008; #49 also has CPU peaking,
  #47 is 48 s). Together with #69 -> #71 and #74/#75 -> #78, this points at build-up inside a *process*, possibly the
  UI's.
  - B4 records UI RSS, but no test restarts the UI alone.
  - Add: under writer, after losses start, restart only `apertar-ui-direct` and take one more. Clean = the UI process
    carries the build-up.
- **The UI-stopped controls do not separate "drawing" from "footprint".** #5, #17 and #59 also free the UI's RSS and GPU
  buffers. The separating takes are #27 (`SIGSTOP`, memory kept, 1/1450) and #30 (preview held, 0/1498), n = 1 each.
  The conditional claim (draft:50, :104) should cite those, with n = 1.
- **#80 is not in the KB's raw record.** The journal extract ends at 23:13:03 (`raw.txt:390`) and the takes table has 79
  rows. "0 of 15,025" and "kswapd 0" are session-reported.
  - Paste #80's `capture stats` / `recording stats` lines and the `take3.sh` output into the KB before B3 relies on them.
  - The same applies to the `pgscan_direct` / `allocstall_*` deltas (M2).
- **B6 done-means tests the most favourable position.** One 10-min take per fresh boot, on a trimmed, emptied drive,
  is the #69 position. Shooting is consecutive takes without restart or delete.
  - Add one run of three consecutive 10-min takes on one boot from < 30 % fill, with no restart between them.
- **The start memory state is not a controlled factor anywhere.** MemFree before a take ranged from 275 MB to 2,758 MB
  and tracks the arm (writer 275-327, sync 507-788, #80 2,758).
  - Record MemFree, Cached and MemAvailable before every take.
  - Set them in B3 (R2) and report them as a covariate in B1.

## 4. What survives

- Writer vs sync on 11-01: suggestive (take-level p 0.057), order-, restart- and trim-confounded. The kernel counters
  separate cleanly: the mode changed the reclaim regime (measured).
- The frame-level p-values are invalid. The take is the unit; dispersion 66 (confirmed arithmetic).
- No smooth uptime drift in boot 1 before 21:50; a step after (confirmed arithmetic). Fill is excluded as the boot-1
  step's cause (confirmed from the format time).
- #78's minute 10 differs from minutes 1-9 (dispersion-aware tail 7e-7).
- The dirty pair is probably inert for Core (source and `Dirty` peaks, not the 10-26 takes).
- B1's skeleton (interleaving, reboot per block, explicit arm, environ check, per-take trim, a manipulation check on
  `pgsteal_kswapd`) is right. Fix the restart-position, randomization and tie issues in R3.

## 5. Commands that settle the open statistical points (Patrik runs `sudo`; nothing is run from here)

| Point | Command | Reading |
| --- | --- | --- |
| A0's boot age (R7) | `journalctl --list-boots \| grep 2026-10-30`; `journalctl -b <id> -u apertar-core -o short-monotonic \| grep 'recording clip'` | monotonic seconds at A0: < 1,800 = early in the boot (the reading is back on the table); > 20,000 = hours (the draft's refutation stands) |
| #78's 18 losses (R6) | `journalctl -u apertar-core -b -1 --since 23:11:00 --until 23:12:10 --no-pager \| grep -E 'drop\['` | few lines with `dt_us` >> 80,000 = a few episodes (one stall); many single-frame lines = a rate change |
| Did #80's knob engage (R1) | paste #80's `take3.sh` "compaction during take" line into the KB | `pgsteal_kswapd=+0` confirms no watermark crossing; any `allocstall` > 0 contradicts R1 |
| Trim before #74/#78 (R8) | `journalctl -u apertar-core -b -1 --no-pager \| grep -E 'media: trim'` | a `reason=mount` and a `reason=delete` line at 22:46 = #74 ran on a fresh trim; a line between 22:54 and 23:02 = #78 too |
| Volume size (§1) | `df -B1 /media/RAW` | the size in bytes; ~1.0e12 means the fill table and the "~140 GB deleted" figure must be recomputed (~70 GB) |
