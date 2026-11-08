# C1: statistics and experimental-design critique of plan v1 (NVMe 4K campaign, 2026-11-08)

Critic: statistics / experimental design. Object: `scratchpad/draft/plan-v1.md` (sections cited as v1 §n) against
`scratchpad/draft/constraints-and-arithmetic.md` (R1-R14), the KB at `/home/user/apertar-kb` (origin/main `89d24e5`; the
brief said `203204a`, which is not a ref in this clone; the difference is one fork-log line), the unmerged branch pages
(`storage-slowdown-plan.md`, `reanalysis-longtakes-ssd-2026-11-08.md`) and the research reports R1, R2. Labels in the
evidence are the KB's own (measured / derived / probable / unconfirmed); my own arithmetic is marked **critic's model**.
Nothing ran on the camera. Findings are ranked by consequence for the campaign's outcome (a wrong recipe, a lost result, or
wear spent on an answer the design cannot give).

## 0. The data model v1 implies, stated once

Every take is one observation of (arm, fps, tier length L, outcome): a failure time T if a drop comes before L, or a
censored observation at L. The estimand per cell is the survival function S(t) = P(no drop by t). v1's ladder is a
survival study with administrative censoring at 180 / 300 / 900 / 1800 s and ONE observation per cell per tier. Two
consequences hold throughout this report:

1. A clean take of n frames bounds the per-frame loss rate only at 3/n (95 %, rule of three; the KB made the same point
   for the evening-3 sweep: "two clean 3-min takes bound the loss rate only at < 0.077 %", `preregistration.md:549`).
   The 30-minute goal needs a rate below 1/45,000 = 2.2e-5 per frame. **Critic's model**, 25 fps:

   | clean exposure | frames | 95 % upper bound on the rate | losses expected in a 30-min take at that bound |
   | --- | ---: | ---: | ---: |
   | one 3-min take | 4,500 | 6.7e-4 | 30 |
   | one 5-min take | 7,500 | 4.0e-4 | 18 |
   | one 15-min take | 22,500 | 1.3e-4 | 6 |
   | one 30-min take | 45,000 | 6.7e-5 | 3 |
   | two 30-min takes | 90,000 | 3.3e-5 | 1.5 |

   A clean 3-min take therefore says nothing about 30 min except "not already hopeless"; the ladder is right to treat it
   as a screen, and v1's prognosis rule (§7) must not dress it up as a prediction.
2. The two failure classes have different statistics. A capture-gap failure is the first event of a point process:
   T is roughly exponential, CV about 100 %, and one T estimates the rate with infinite variance (the MLE 1/T has no
   finite mean). A buffer_full failure is T = budget / deficit: nearly deterministic once the budget is known, dominated by
   the start-up transient (`longtakes.py:278-296` already corrects short takes by 1.15-1.35x). So T is a usable metric for
   buffer_full (normalised by the budget) and a poor one for capture gaps, where the efficient statistic is the loss count
   over the exposure. Every 4K drop on the NVMe so far was a capture gap (`nvme-4k-recipe-plan.md:15`, measured): the
   campaign's main regime is the one where v1's time-to-drop comparisons are weakest.

## 1. Findings, ranked

### F1. v1 §6 S2 + §7: the fps walk is a bracket search with one take per fps; with the record's non-monotone outcomes it will skip the best fps on record

- What is wrong: `bracket_search` (`working/tools/longtakes.py:244-276`) assumes a deterministic threshold: after one
  failure it steps down 3, 6, 12 fps and bisects, and one pass ends the search downward (`nvme-4k-recipe-plan.md:78-82`).
  v1 §6 S2 keeps "mode top downward with the log(T) fit and 3/6/12 steps". On this rig outcomes at a fixed fps are not a
  step function: at 27 fps both 3-min takes lost exactly 1 frame (`findings-2026-11-04.md:41`, measured, n = 1 per
  take), while at 28 fps with depth 4 the take was clean (0 / 5,055, `findings-evening4-supervised-2026-11-04.md:14`,
  measured) and at 28 fps with depth 2 it lost 5 (`findings-2026-11-04.md:42`). Trace v1's walk for HDR16 with the
  record's outcomes: 30 fails (t1: 3 lost at 119 s, e4:16), step 3 to 27, 27 drops (as both recorded takes did), step 6
  to 21 which clamps to the 25 fps floor, 25 passes, bisect 26. **28 fps is never tested** and the campaign reports an
  HDR16 edge of 25-26 while the record already holds a clean 3-min 28-fps take under the same measures.
- Evidence of spread at a fixed fps, which is what breaks a single-take bisection: the earlier board's time to first drop
  at 26 fps ranged 8-213 s and at 25 fps 27-453 s (`nvme-4k-recipe-plan.md:16`, first NVMe run, erased, measured on the
  earlier board); on this board #46 0 % then #47-#50 1.8-3.4 % in one setup (`night-2026-11-01.md:50-51`, "take-to-take
  spread has been large all evening"); TDN-off P1 takes 1, 2, 1 lost against their P2 twins 0, 0 (`findings-2026-11-04.md:
  13-17, 70-72`, measured; the P1 cause "unconfirmed"); 10-min HDR16 25 fps: 4 clean of 7 (R1 §3).
- Fix: the prior sets the start and the step. Walk the record's bracket, not the mode top: HDR16 25-29 fps (start 28),
  SDR12 uncompressed from a meter take at 50 fps (see F8) then the capacity minus 1-2 fps, HDR12 from 30 (no record).
  Step 1 fps inside the bracket. Every verdict at the screening tier needs two concordant takes (2 clean = "clean at
  3 min"; 2 drops = the cell is out; 1-1 = a third take decides). Failures are short, so the second take of a failing cell
  costs its time-to-drop, not 76 GB. Keep the owner's R4 (the take stops at the first drop); only the elimination of the
  cell waits for its confirmation take.

### F2. v1 §5-§7: no warm-up / first-take-discard rule, so the first arm of every evening or Core restart is eliminated on a position artifact

- What is missing: v1 fixes the state per take and restarts Core per evening for the drop-in (§5), but has no rule for
  the first take after a restart, reboot or mode change. The record shows a position effect of the size of the effects
  under test: the first take after a reboot lost 17, 9 and 54 frames in 3 min under `sync` while later takes in the same
  state were clean (R1 rows 155, 164, 191: `takes.md:7` with `preregistration.md:127`, `preregistration.md:123` with `findings-2026-11-02.md:15`, `takes.md:84`; measured, unscored);
  under `sync` one take of each P1/P2 unit lost heavily and the other was near clean, in no fixed order
  (`findings-2026-11-02.md:37-42`, measured: sync 1/47, 0/108, 1/72, 0/80; "what puts a take into the losing state is
  unconfirmed"); with TDN off P1 lost 1-2 and P2 0 (`findings-2026-11-04.md:13-17`). A mode change replaces the
  CameraManager threads (R1 §4.8 citing f02:52), so every mode switch in S2 is a fresh start. The feasibility page lists
  "first-take discard" as a lever of its own (`working/dng-chain-feasibility.md` §4 row 5).
- Consequence under stop-on-drop: the first scheduled cell after every restart or mode switch (in v1 the mode's top fps,
  or a lever pair's first member) carries an extra hazard that has nothing to do with the arm. Over an S2 of ~60 takes
  with 3-4 mode blocks and per-evening restarts, several cells will be decided by position.
- Fix: an unscored 60-s warm-up take (same mode, the arm's fps, ~25 GB at HDR16) after every Core restart, reboot and
  mode switch, recorded in the database as `warmup`; `takes_since_restart` and `uptime_s` as columns on every take; the
  lever pairs never start a block.

### F3. v1 §7 lever verdicts: one pair at the fps where the baseline's own outcome is a coin flip, two controls, a 2x rule, five levers: at least one false "better" is almost certain

- What is wrong: v1 pairs each lever once "at the edge fps (the fps just above the clean one, where outcomes vary)"
  (§6 S2) and reads "clean where the baseline dropped" or "T >= 2x" as better, "drops before the baseline" as worse, and
  "inside the baseline's spread (two control takes per stage)" as no difference (§7). Three calibration problems:
  (a) The edge fps is by construction the point where P(clean) for the baseline is near 0.5, so a null lever reads
  "better" (clean where the baseline dropped) about half the time with n = 1. With n controls and the rule "beats every
  control", the null probability is 1/(n+1): 50 % at n = 1, 33 % at the two controls of v1, 20 % at n = 4.
  (b) The 2x rule (`longtakes.py:197-208`, `compare_scores`: "2x either way counts") is uncalibrated against the spread.
  **Critic's model**: with ln T spread over ~3.3 units at one fps (the 26-fps range above), a lognormal with sigma 0.7-1.0
  makes two same-arm takes differ by >= 2x in 48-62 % of pairs.
  (c) Two control takes estimate the spread with a 76 % relative error on the sd (**critic's model**: n = 2, c4 = 0.80),
  so "inside the baseline's spread" is a yardstick that is itself noise.
  Five levers against two controls: the chance that at least one null lever reads "better" is 1 - (2/3)^5 = 87 %
  (**critic's model**). v1 then carries it into S3-S5 at 127-760 GB per take. The 11-07 plan had 3 repeats per option,
  the median >= 2x AND above the best control, controls at the start of each stage and every 8 takes
  (`nvme-4k-recipe-plan.md:24, 93-97`); v1 cut this to one pair and two controls without changing the verdict words.
- Also: "no difference" is terminal ("dropped from later stages", §7) although it rests on the weakest test in the plan;
  a lever that raises P(clean at the edge) from 0.3 to 0.6 would be read "no difference" most of the time and never
  return.
- Fix: (1) pool every baseline take at the edge fps as a control (the walk already produces them; add one control at the
  end of each mode block so controls bracket the block in time; see F10); (2) "better" = beats every control AND the
  direction matches the lever's pre-registered expectation (v1 §5 table) AND it replicates in a second pair (ABBA);
  (3) "no difference at 3 min" is not terminal: it is "not shown, n = 1 pair"; a lever is carried only by (2), and at most
  one lever variant per mode goes to S4 (v1's own cap of best + runner-up stands); (4) order the lever list by expected
  information, not by the owner's enumeration: a pair whose outcome is known in advance has zero information per GB
  (F11).

### F4. v1 §6 S4/S5 + §7 split verdict: one pair per tier, the order aliased with heat, fill and process age; the 30-min order is anti-conservative; the 15-min pair tests a predicted null

- What is wrong: "frames_per_folder 5000 vs 0, back to back, order alternated per mode" (S4) and "split and unsplit (the
  pair)" at 30 min with U S at 15 and S U at 30 (`constraints-and-arithmetic.md` §9) gives exactly one pair per tier and
  mode. Within a tier the second member starts hotter (drive 39.85 -> 65-72 C after 10 min at 410 MB/s,
  `findings-2026-11-04.md:57`, measured; P2 hot costs 46.4 vs 35.4 ms of recording-thread CPU per frame,
  `preregistration.md:518-522`, measured), later in the Core process (F2), and at a different fill: at 30 min HDR16 the
  first member fills 76-91 % of the card (v1 §3), so the fill gate deletes it before the second member, which then runs on
  an empty, freshly trimmed card. The lever is 100 % aliased with these within each tier; alternating the order across
  tiers does not cancel them because the tiers differ in length and fill. The verdict table (§7) does not even list the
  outcome "split stops first". With S U at 30 min the known confounds (heat, age) work AGAINST the unsplit member, so a
  "directory matters" reading would be inflated exactly where the owner asks the question (R13).
- The 15-min pair tests what the probe already predicts to be small: 22,500 files = 6.9 ms = 17 % of the 25-fps period,
  under the probe's own 25 % rule ("the 15-min stage at 25 fps ... is under the line on its own",
  `nvme-campaign/probe-exfat-dir.md:143-145`, derived from the measured c = 63.3 ns). Cost of the pair: 2 x 380 GB per
  mode at HDR16 (v1 §3), about 2.3 TB over three modes for an effect the model puts at 17 % vs ~1-3 %.
- The directory effect is deterministic and has an in-take meter that needs no pair: Core's CPU slope gives c in the
  live system (`reanalysis-longtakes-ssd-2026-11-08.md:47-70`: 17 takes, c = 77-133 ns, median 99, derived), to be
  matched against the probe's 63.3 ns (measured). A split take must show a flat CPU and the same drain. That reading comes
  from every long take, split or not.
- Fix: (1) drop the 15-min pair; at 15 min run one unsplit take per mode and read the CPU slope and the buffer curve as the
  directory meter. (2) At 30 min run UNSPLIT FIRST; run the split member only if the unsplit take drops after ~minute 10
  with the directory signature (CPU slope at the probe's c, buffer rising in the last minutes, device latency flat) or
  as the S7 soak take of the mode (the soak is a 30-min take of the final recipe anyway, so the split A/B then costs
  nothing extra). Split second is the conservative order: heat and process age work against the hypothesis "splitting
  helps", and the fill is equalised by the forced delete. (3) Pre-register the attribution signatures (which per-second
  series moves before the drop: Core CPU slope -> directory; `/sys/block` write ticks per write rising with fill -> drive
  state; temperature with latency -> heat; dirty/writeback kB -> page cache; none -> capture side) instead of §7's "look
  at the meter, the temperature, the fill". (4) State in the plan that one pair per mode can only ever give "consistent
  with" readings; the strong statement about the directory is the deterministic one from the probe plus the in-take c.

### F5. v1 §5: the "FIXED budget" is not fixed, and 0.9 changes the cushion against the whole record

- What is wrong: v1 §5 fixes `buffer_ram_fraction 0.9`, `buffer_ram_floor_mb 256` and calls the budget fixed. Core's
  budget is fraction x MemAvailable at take start minus the floor, capped at 0.5 x MemTotal (`working/drop-frames/
  README.md:63`, confirmed from code; R2 §2a: measured 1,424 MiB at 0.6 / 512). The SSD run's MemAvailable moved 1,270-
  2,991 MiB (`reanalysis-longtakes-ssd-2026-11-08.md:122-127`, measured), which at 0.9 / 256 gives 0.9-2.0 GB (capped):
  still 2.2x, not fixed. The storage plan says the fixed-MiB key is "a small Core change" and that the budget must be
  fixed or normalised before any time-to-failure is compared (M8, §4.5).
- Second effect: every take on record ran at 0.6 / 512 (~1.4 GB). A 2 GB cushion on a 4 GB board changes the time to
  the safety stop (the outcome variable of storage-limited arms) and, during a stall, how much page cache the buffer
  displaces; memory pressure is the measured capture-gap mechanism (`recipe.md:31-32` citing findings-2026-11-03 §1,
  measured). A budget change can therefore flip a take's failure class between buffer_full and capture gap, and the class
  is v1's regime classifier (§7, "capture levers only against capture gaps ..."). None of the record's survival numbers
  transfer to a different budget.
- Fix: hold the record's 0.6 / 512 unless the budget is itself a lever, or add the fixed-MiB key at ~1,400 MiB before the
  first take; log `queue_budget` per take (the runner does) and report every buffer_full time as seconds of input absorbed
  (budget / rate), never as raw seconds; read the regime from the counters AND the buffer curve, not from the stop reason
  alone.

### F6. v1 §6 S2 + §7 prognosis: the log(T)-vs-fps fit is two points from an erased run on another board, mixes two regimes, and extrapolates 1-3 orders of magnitude

- What is wrong: "fit log(T) = a - b x fps from the first two failures and jump to the fps predicted to reach the target
  time" (`nvme-4k-recipe-plan.md:16, 74-75`; v1 §6 S2, §7 prognosis). (a) Two points fit a line exactly: zero residual
  degrees of freedom, no uncertainty. (b) The model's only support is the erased first run's table on the earlier board
  (30 fps 2 s ... 25 fps 27-453 s, `nvme-4k-recipe-plan.md:16`), whose within-fps spread (17-27x) is larger than the
  between-fps slope near the edge. (c) The regimes differ: at 30 fps the loss is a steady back-end deficit (S2 11.9 /
  24.7 ms, queued 0.27, write queue 11/12, e4:16, 29, 40-44, probable) where T is short and nearly deterministic; at
  27-28 fps the losses are rare single CFE frames, each after one BE job of 79-105 ms (`findings-2026-11-04.md:46-50`,
  probable), where T is exponential. One log-linear curve through both predicts nothing about the stochastic regime the
  long tiers live in. (d) The targets (T = 180-1800 s) are 1-3 orders beyond the fitted points (T = 2-120 s). The fit is
  also not built yet (v1 §9 (h)); the runner only has the buffer_full estimate (`smart_next_fps`).
- The storage-side prognosis (`clean_until(N) = period - 5 x c x N - mapping share`) is a deterministic model with one
  unmeasured term of the same order as the directory term at 15,000 files: the mapping share, 24,300 lock takes per
  12.4 MB file, estimated 3.6-7.3 ms (`working/dng-chain-feasibility.md` §1 table, exFAT row; V-F4 rows 16-19, estimated).
- Fix: no fitted prognosis on the capture side. Set the next fps from the mechanism reading of the failing take: a
  steady deficit gives the capacity directly (fps_c = 1000 / cycle_ms from `be_overlap.py`), rare single frames mean step
  1 fps and require two concordant takes (F1). Report the prognosis per cell as a survival table: clean exposure (frames)
  pooled across tiers, its rate bound (section 0), the model-based expectation with its label and its unmeasured terms
  named. Pooling is valid for the same cell: the 3- and 5-min clean takes are not wasted, they are exposure.

### F7. Missing in v1: what the campaign can and cannot claim at the end, against the project's own standard

- What is missing: v1 has no claims section. With one clean 30-min take per mode (S5) plus one soak (S7), the campaign
  can claim: "a 30-min drop-free take was recorded once (twice) at these settings"; the per-frame rate is below 6.7e-5
  (3.3e-5) at 95 %, i.e. up to 3 (1.5) losses per 30-min take remain compatible; and under a flat prior on exchangeable
  takes the predictive probability that the next 30-min take is clean is 2/3 after one, 3/4 after two, 4/5 after three
  (**critic's model**, rule of succession; optimistic, since a real shoot differs in fill, heat and uptime). It cannot
  claim "30 min drop-free in all 4K modes" as a property (R14), a clean fps finer than the 1-fps step tested, anything at
  30 min for the crops (F9), or transfer to the CFe cards beyond n = 1 per card (F9). Elimination claims have graded
  strength: a steady-deficit failure within seconds is strong; a single frame at minute 2 of one take is weak (F1-F2).
- The project's own pre-registered done-means was B6: five 10-min takes on two boots (`preregistration.md:663-668`);
  O1 did not replace it ("One take: it does not replace B6", `observations-2026-11-04.md:21`). v1's standard (one 30-min
  take, one soak) is weaker in replication and stronger in length; the plan must say so and say why (wear).
- Fix: a pre-registered claims table (claim, evidence needed, label it will carry) in §7, and the status file's prognosis
  written in those terms. The single most valuable extra take of the campaign is the second 30-min take of each mode's
  winning arm (760 GB at HDR16): it is the only way to see repeatability of the fill, heat and file-count covariates at the
  length that matters (no take longer than 602 s exists, R1 §3), and it moves the claim from "happened once" to 2 of 2.

### F8. Storage plan §4.1 as adopted by v1 §0/§5: the meter's "90 s at 20-30 % over capacity gives the capacity to about 1 %" does not hold at 4K rates

- What is wrong: the buffer level is the integral of delivered minus written only up to the budget; at 90 % of it Core
  stops the take. **Critic's model**: HDR16 at 25 fps is 422 MB/s; a 25 % overshoot is a 105 MB/s deficit; 0.9 x 1.4 GB /
  105 MB/s = 12 s (17 s at a 2 GB budget). A "90-s meter take" at 20-30 % over capacity is a 12-17 s take at 4K, of which
  the first seconds are the writers' start-up transient the runner already corrects by 1.15-1.35x. Ten samples at 1 Hz
  with a transient give the drain to maybe 3-5 %, not 1 %. Duration and overshoot must be chosen together: duration ~
  0.9 x budget / (rate x overshoot): 90 s needs an overshoot of about 3 % at HDR16 (10 % gives ~30-40 s).
- Assumptions to state: "written" means handed to the filesystem, not on the device; the device's rate enters only
  through throttling, so the meter must be cross-checked against `/sys/block/<disk>/stat` sectors per second (sampled, per
  storage plan §4.4) and the identity "sum over the take of (fps - drain) = final buffer level" must be verified per take.
  The new sampler columns are "untested on the Pi" (storage plan §4.4); the SSD run's free-space series had a 0.1 GiB
  quantisation (40 % per 5-s window, `reanalysis-longtakes-ssd-2026-11-08.md:19-20`), so the first smoke test must show
  `buffer_used` at byte resolution at 1 Hz before any capacity number is believed.
- Fix: the meter take's fps is set from the budget (overshoot 5-10 %, 30-60 s), the identity check and the device
  cross-check are part of the take record, and the capacity is reported with its window and spread (the SSD drains
  varied 1-3 % per 5-min window, reanalysis §3), not "to 1 %". At 4K on the NVMe the meter applies only if an arm ends in
  buffer_full (v1 says so; SDR12 uncompressed above ~42 fps is the one place, `nvme-4k-recipe-plan.md:35-38`).

### F9. v1 §4 crops and §6 S7 transfer: n = 1 at 3 min for the crops, one max take per CFe card, both reported under R14's "30 min in all 4K modes"

- What is wrong: the crops get "one screening take each at the full-frame winner's settings (+1 fps)" (§4, §6 S2) and no
  long tier (S4/S5 list "the best arm per mode" for three modes). The only counted crop take lost 12 % at 50 fps on an
  old build and an 80 %-full untrimmed drive (R2 §2h, measured). A 3-min clean take bounds the crop's rate at 6.7e-4
  (section 0). On the CFe cards S7 runs one 15-min and one max-length take per mode per card: n = 1, on hardware with no
  record at all, where the drive-side mechanisms (trim state, pSLC, heat) are per card (`constraints-and-arithmetic.md` §7).
- Fix: label the crops' 30-min status "predicted from the full-frame result (fewer bytes, lighter back end), untested
  beyond 3 min" and the CFe result "one take per card"; if the owner wants a crop at 30 min, it costs one 30-min take per
  crop and should replace the 15-min split pair (F4) in the budget.

### F10. v1 §6 S2 order: ~60 takes in one Core process over hours, the fps walk monotone in time, controls not placed to see drift

- What is wrong: the walk runs top fps first, so within a mode block process age and fps fall together; the SSD run
  "drifted by ~3 fps over hours" (`nvme-4k-recipe-plan.md:24`, the lesson that motivated controls); boot 1 of 11-01 held
  ~7 % then stepped to 11-18 % at 21:03 with no change of setup (`night-2026-11-01.md:303`, "not supported" as an uptime
  effect, a step nonetheless); memory fragmentation after ~3 h (no order-8 block, CmaFree 0-0.8 MB, R1 §4.1 citing
  README:205). Two controls "per stage" at an unspecified time cannot separate drift from the lever block.
- Fix: one control at the start and one at the end of every mode block at the block's edge fps (pooled with the walk's
  takes, F3); `takes_since_restart`, `uptime_s`, MemFree and the buddyinfo order-8 count on every take record; if the end
  control differs from the start control by more than the pooled spread, the block's lever verdicts are flagged "drift".

### F11. v1 §5 lever table: two of the five paired takes have a known outcome, so they carry no information; the open TDN question is a different take

- TDN on at the edge fps (27-28) of a TDN-off baseline is a deterministic failure: the TDN job is ~37 ms against a
  35.7 ms period at 28 fps (`findings-2026-11-04.md:11-28`, measured, p = 1/6). Phase lock on is the one lever with a
  measured negative effect and no measured benefit (10 holes per 60 s plus 8.9 % flicker, `lessons/hardware-log.md:
  279-293`, confirmed / measured). A pair whose prior P(fail) is ~1 answers nothing; it only spends the time to the first
  drop. The open TDN question is O1's: a 10-min TDN-on take without instrumentation lost 1 while every instrumented TDN-on
  3-min unit lost 39-116 (`observations-2026-11-04.md:58-61`, unconfirmed hypothesis). HDR16 lossless is out by the
  encoder (17.5 fps, `recipe.md:44`, measured); the encoder capacity of every compression arm is already measured by
  Core's pre-roll (`estimated_capacity_fps`: HDR16 lossless 16.84, SDR12 lossless 48.13 at 33 fps, `findings-2026-11-03.md:
  47`, `findings-2026-11-04.md:64`), a 2-s take of ~1 GB, so compression arms need no 3-min take to find their encoder edge.
- Fix: replace the TDN pair with one 3-min TDN-on take at 25 fps with no debug log or trace (the campaign runs that way
  anyway): 0-2 lost supports the instrumentation hypothesis, >= 10 confirms TDN off for real use. Phase lock: at most one
  60-s probe (25 GB) if the owner wants the 11-04 fix exercised, with no bearing on elimination. Compression: a manual
  `storage_preroll` per compression arm first (the pre-roll is off in the campaign; the command exists, R2 §2a), then
  3-min takes only for the arms whose capacity exceeds the uncompressed edge (SDR12 lossless). A compression arm has its
  own edge; it is not a "variant paired at the baseline's edge".

### F12. v1 §7 "Elimination: an arm that drops at tier length L is out at L and above" is right in direction for the 30-min goal, but the plan does not say why, and so cannot say when it is wrong

- Under every known mechanism the hazard grows with time inside a take (file count, fill, heat, process age), so a drop
  at t < L implies S(1800 s) <= S(t) for the same conditions: early elimination is conservative for the goal. The exception
  is the single-frame background loss that does not grow with time: at the observed 1-2 per 4,500 frames (2-4e-4) it is
  already 10-20x the rate the 30-min goal allows, so such an arm IS out for 30 min unless the loss is a position artifact
  (F2). The plan should state this reasoning in §7 so that the Opus thread reads a single late frame correctly: repeat the
  cell once (F1); if it reproduces, the arm is out for the goal whatever its mechanism; if not, record both and carry.

## 2. The minimum design that still answers the owner's questions within the wear budget

Stages and tiers as the owner set them (R3: 3 -> 5 -> 15 -> 30; R4 stop-on-drop per take; R13 split; R12 transfer).
Costs are HDR16-uncompressed figures from v1 §3 (76 / 127 / 380 / 760 GB at 25 fps); lighter arms cost less.

| Stage | Takes | Rule | Approx. GB (test card) |
| --- | --- | --- | --- |
| S0/S1 as v1, plus: smoke test proves `buffer_used` at 1 Hz and the integral identity (F8); budget held at the record's 0.6 / 512 or a fixed-MiB key (F5); a manual pre-roll per compression arm for the encoder capacity (F11) | 0 camera takes beyond the smoke test | - | ~70 |
| Warm-up: 60-s unscored take after every Core restart, reboot, mode switch (F2) | ~10 | never scored | ~250 |
| S2 walk: per mode the record's bracket (HDR16 25-29 from 28; SDR12 U from one meter take at 50 fps then capacity -1/-2; HDR12 from 30), step 1, two concordant takes per decision (F1) | ~13 | the cell is out after 2 drops; clean after 2 clean | ~800 |
| S2 levers, HDR16 only for the capture-side ones: Log (ABBA = 2 pairs), WebUI off (ABBA), TDN-on unlogged at 25 fps (1 take), phase lock 60-s probe (1); SDR12 lossless own mini-walk (2 takes); HDR12: Log one pair only if its S2 edge is capture-limited; crops 2 x 2 takes (F3, F11) | ~16 | better = beats every pooled control, direction as pre-registered, replicates | ~900 |
| Controls: one at the start and end of each mode block at the edge fps, pooled with the walk (F3, F10) | ~6 | - | ~400 |
| S3 5 min: the owner's tier; one take of the carried arm per mode (statistically it adds little over 3 min: the bound goes 6.7e-4 -> 4.0e-4) | 3-4 | stop-on-drop; a drop sends the runner-up | ~400 |
| S4 15 min: one unsplit take per mode; the CPU slope and buffer curve are the directory meter; the runner-up only if the best drops (F4) | 3-5 | - | ~1,200 |
| S5 30 min or fit: unsplit first per mode; split only on a late drop with the directory signature; MLV only if both drop late (v1's rule) | 3-6 (+0-3 MLV) | pre-registered signatures | ~2,300 (+ up to 2,300) |
| S7 soak on the test card: one 30-min take per mode of the final recipe; where the unsplit S5 take passed, the soak is the SPLIT variant (the A/B in the conservative order, free) (F4, F7) | 3 | - | ~2,300 |
| S7 transfer: per CFe card one 15-min and one max take per mode, labelled n = 1 per card (F9) | 12 | - | on the CFe cards |
| Total on the test card | ~70 | | ~8.5-11 TB (v1: 9.8-15) |

Where an extra take buys the most certainty, in order: (1) a second 30-min take of each mode's winning arm when the soak
ran as the split variant (760 GB each; "happened once" -> 2 of 2, the rate bound halves, the covariates get a repeat at
the only length that matters); (2) the confirmation take at every eliminated cell in S2 (seconds to 76 GB; it protects
380-760 GB tiers from a position artifact or a 50/50 edge outcome); (3) the 60-s warm-up after every restart (25 GB; it
protects the first arm of every evening); (4) a third control per mode block (76 GB; "beats all controls" goes from
p = 1/3 to 1/4 under the null).

## 3. What v1 gets right and must not be lost in v2

- Stop-on-drop as the wear limiter at every tier and "only survivors pay for long takes" (§8); the ladder itself.
- The fixed-state table (§5), the void rules and read-backs (§7: mode, client count, build, card serial), the merge worker
  OFF, the pre-roll off with the deviation recorded, the ladder off for takes.
- The regime rule: a lever is tested only against the limit it can act on (§7), with Log in both regimes.
- buffer_full as a result and the buffer curve as the primary reading for storage-limited arms (§0, §6); the per-second
  covariates (buffer, device counters, dirty pages, trim state, temperature) on every take.
- Fill as a covariate behind a physical gate, temperature logged and never gated (R6, R10), the near-full condition tested
  rather than avoided (§3 rule b).
- Camera-free probes first (S1) and the probe's pre-registered rule carried into the design (§0).
- Pre-registration of the rules before the first take (§7 header); v2 should add the claims table (F7), the attribution
  signatures (F4) and the two-concordant-takes rule (F1) to it before anything runs.
- The runner's status file, decision log and database written only between takes (§9); never a second client or a journal
  query during a take.
- The wear ledger and the 10 TB cap; "a 30-min take is never repeated to make sure unless void" as the default, with the
  one named exception of section 2.
- The MLV take as a conditional diagnostic, not a recipe.
- Treating 15 and 30 min as having no datum at all (R1 §3) and building the record from the bottom.

## Verification (skeptic)

Skeptic pass, 2026-11-08. Every citation above was opened (KB at origin/main `2ba5b1b`; the two branch pages via `git show`; R1, R2, R3,
R10; `longtakes.py`). Default where the evidence could not be found: REFUTED. None had to be. Nothing ran on the camera. `plan-v2.md` was
re-read in its current state (it changed on disk during this pass: clip-split verified, cold unlink measured).

### Per finding

- **F1 — OVERSTATED.** The spread evidence is as cited (f04:41-42, e4:14, recipe-plan:16, night:50-51, R1 §3) and one take per cell with
  a bisection can skip an fps; but the headline trace mixes regimes: both 27-fps takes that "dropped" were evening-3, FE-depth-2 takes
  (`findings-2026-11-04.md` never mentions depth; the depth-4 YAML arrived on evening 4), while the campaign fixes depth 4, under which the
  28-fps single-frame losses vanished (d4, n = 1). Under depth 4 throughout, `bracket_search` from 30 (fail) and 25 (pass) bisects
  27 -> 28 -> 29 and DOES test 28. Also: the code's first step down is 6, not 3 (`step *= 2` runs before `f - step`; the 3-step applies only
  when a prior failure exists) — immaterial to the conclusion; and "failures are short" is false in the single-frame regime: the 27-fps
  losses came in minute 2 and 3 (`takes.md:95-96`), so a confirmation take there costs 25-75 GB, not seconds. The 1-fps step inside the
  record's bracket and two concordant takes remain the right fix.
- **F2 — OVERSTATED.** v1 has no warm-up / first-take rule and the KB flags position (R1 §4.1; feasibility §4 row 5 "First-take discard"),
  so the rule is worth its 25 GB per take; but the 17 / 9 / 54 lost warm-ups (tk:7, pr:123/127, tk:84) were TDN-on, depth-2, `sync` takes —
  a regime the campaign excludes and in which the scored takes lost too (sync P2 47-108; N units 39-116). The only in-regime position
  evidence is TDN-off P1 1-2 vs P2 0 at n = 3 units, cause "not shown" (f04:70-72): an effect of 1-2 frames, not 9-54.
- **F3 — HOLDS.** v1 §7's wording ("2x", "clean where the baseline dropped", "two control takes per stage", terminal "no difference") and
  the cut from the 11-07 plan's 3 repeats + controls (recipe-plan:24, 93-97) are as described; `compare_scores` (197-208) is the 2x rule;
  the arithmetic is right (below). Caveat: TDN on and phase lock are predicted failures (F11), so the "at least one false better" chance
  for the three open levers is 1 - (2/3)^3 = 70 %, not 87 %.
- **F4 — HOLDS on the design, OVERSTATED on the cost and the fill confound.** Within-tier confounds (drive 39.85 -> 65-72 C, f04:57; P2 hot
  46.4 vs 35.4 ms, pr:518-522; process age), the unlisted outcome "split stops first" (v1 §7), the 15-min pair's predicted ~17 % (probe:
  143-145) and the in-take c (reanalysis:47-70) are as cited. But (a) the 15-min saving is one split take per mode (~380 GB HDR16, ~1.1 TB
  over three modes), not 2.3 TB — the unsplit 15-min take stays in both designs; (b) fill is not a confound in either order: each 30-min
  member starts on a card emptied by the fill gate, so what differs is trim/delete history, heat and process age. The attribution
  signatures and "unsplit first, split as the soak" are sound; note the derived c (99 ns) is 50 % above the probe's 63.3 ns, so "CPU slope
  at the probe's c" needs a tolerance band before it can act as a signature.
- **F5 — HOLDS.** README:63 (0.6 x MemAvailable - 512 MiB, cap 0.5 x MemTotal), R2 §2a (1,424 MiB), reanalysis §8 (MemAvailable 1,270-2,991
  MiB), storage plan M8 and §4.5 (0.9 / 256 "fixed"; "a fixed-MiB key is a small Core change") — all as cited; 0.9 x (1,270..2,991) - 256 =
  887..2,436 MiB, capped near 2,000 -> 2.2x. One mislabel: `recipe.md:31-32` is memory TRAFFIC (bandwidth slowing the back end), not
  page-cache pressure; the reclaim mechanism is `findings-2026-11-02.md` §1. The conclusion (hold 0.6 / 512, log the budget, report
  buffer_full in seconds of input) stands.
- **F6 — HOLDS.** recipe-plan:16, 74-75 (fit from two failures; earlier board; within-fps spread 17-27x), e4:29/40-44 vs f04:46-50 (two
  regimes), R10 §6a 9.2 (no fit built; only `smart_next_fps`), feasibility line 75 (mapping share 3.6-7.3 ms, estimated) — as cited.
  "1-3 orders" is loose at the low end (180 s vs a 119-s failure is 0.2 orders). Caveat in the fix: pooling clean exposure across tiers
  into one 3/n bound assumes a constant hazard, which F12 itself denies; the pooled bound is optimistic for 30-min conditions and the
  survival table should say so.
- **F7 — HOLDS.** v1 has no claims section; 3/45,000 = 6.7e-5, 3/90,000 = 3.3e-5, rule of succession 2/3, 3/4, 4/5 — correct; B6
  (pr:663-668) and "One take: it does not replace B6" (obs:21) as cited.
- **F8 — HOLDS.** Storage plan §4.1 (branch, lines 72-73) says exactly "One 90 s take at a frame rate 20-30 % above the expected capacity
  gives the capacity ... to about 1 %"; at 415-422 MB/s and a 1.4 GB budget a 25 % overshoot reaches the 90 % stop in 12 s (17 s at 2 GB),
  90 s needs ~3 % overshoot, 10 % gives 30-43 s — arithmetic correct; §4.4 "Untested on the Pi" (line 110) and the 0.1 GiB quantisation
  (reanalysis:19-20) as cited. Context the critic omits: §4.1 was written for the SSD's 50-120 MB/s drains and 250-1,283 MiB budgets
  (798 MiB = 17.4 s of input), where 90 s was about right; it fails at 4K rates, as the finding says.
- **F9 — HOLDS.** v1 §4 (one crop take each), S4/S5 "the best arm per mode" for three modes, R2 §2h (the only crop take: 12 % lost at 50 fps,
  `4d5fdd1`, 78-82 % full untrimmed), S7 (one 15-min + one max take per card), constraints §7 (drive facts per card) — as cited.
- **F10 — HOLDS.** recipe-plan:24 (SSD drift ~3 fps -> controls), night:303 (a step at 21:03, uptime effect "not supported"), README:205-206
  (no order-8 block, CmaFree 0-0.8 MB), v1 §7 ("two control takes per stage", no placement) — as cited.
- **F11 — HOLDS.** f04:11-28 (TDN job ~37 ms, p = 1/6; the 28-fps period is 35.7 ms), hwlog:279-293 (10 holes / 60 s, 8.9 % flicker,
  confirmed), obs:58-61 + pr:772-773 (the unlogged N take was proposed and never ran), recipe.md:44, f03:47 (16.84), f04:64 (48.13), R2 §2a
  (manual `storage_preroll`, 0.7-1.0 GB) — as cited. The replacement take is the KB's own open item.
- **F12 — HOLDS.** 2-4e-4 against 2.2e-5 is 10-20x; v1 §7 gives the rule without the reasoning. A documentation finding, correctly small.
- Section 0, one overstatement: "Every 4K drop on the NVMe so far was a capture gap (recipe-plan:15)" — the line says every 16-bit drop in
  the FIRST NVMe run; the 2026-10-26 77-81 %-full takes (hwlog:382-383, queue full from ~95-140 s) and the never-trimmed first-matrix A0
  (4,479 queue-full, R1 §3) were 4K NVMe drops of the drive-state class. Immaterial here (trimmed card, fill gate), but it should read
  "every drop on a trimmed, not-full NVMe".

### The critic's own arithmetic

- Rule of three: 3/4,500 = 6.7e-4, 3/7,500 = 4.0e-4, 3/22,500 = 1.3e-4, 3/45,000 = 6.7e-5, 3/90,000 = 3.3e-5; x 45,000 = 30 / 18 / 6 / 3 /
  1.5 losses per 30-min take. **Correct.**
- 1/(n+1): right for "beats every control" under exchangeable continuous outcomes; 1 - (2/3)^5 = 0.868. **Correct**, with the caveat
  above (two levers are not null). The "50 % at n = 1" for the binary reading holds only because the edge fps is by construction the fps
  where the baseline dropped (conditioning), which the text states.
- Lognormal: ln(213/8) = 3.28; P(|ln T1/T2| >= ln 2) = 48.4 % at sigma 0.7, 62.4 % at sigma 1.0. **Correct.**
- c4(2) = 0.798; relative standard error of s at n = 2 = sqrt(1 - c4^2)/c4 = 75.6 %. **Correct.**
- Meter take at 4K: 0.9 x 1,400 MB / (0.25 x 422 MB/s) = 11.9 s; 17.1 s at 2 GB; 90 s needs 3.3 % overshoot; 10 % gives 30-43 s. **Correct.**
- Budget at 0.9 / 256 over MemAvailable 1,270-2,991 MiB: 887-2,436 MiB, cap ~2,000 -> 2.2x. **Correct.**
- 1/T has no finite mean for an exponential T; rule of succession 2/3, 3/4, 4/5; F12's 10-20x. **Correct.**

### The minimum design (section 2) against R1-R15 (constraints §10-15)

1. R1, R3, R5-R11 and R14 (with the claims-table labels) are met; the column sums check (8.6 TB; 10.9 TB with MLV; ~57-66 takes on the
   test card + 12 on the CFe cards; warm-ups 10 x 25 GB = 250 GB).
2. R2: the table silently drops the conditional storage-knob group and the S6 Core patches (v1 §5 rows); §3 keeps the regime rule, so this
   is an omission of the table, not a rejection — v2 restored both rows.
3. R4: "two concordant takes" and "a single late frame is repeated once" turn the owner's "eliminate at the first dropped frame" into
   "eliminate at the second"; stop-on-drop per take is kept. Justified, but it is a deviation from R4 as the owner stated it and neither C1
   nor v2's R4 row flags it for the owner's OK.
4. R12/R13 against constraints §11-14 (test rig = Kingston KC3000 512 GB, CFe = Corsair 1 TB): the costs are 1 TB-card figures and "a
   30-min soak on the test card" does not fit the heavy arms (HDR16 max ~20 min); the split A/B would then run only at the fit length
   (~30,000 files, 23-28 % of the period) while C1's S7 transfer on the CFe cards is unsplit — so R13 would NOT be answered at 30 min where
   the probe says the directory bites (35-61 %). v2 resolves this by running the whole campaign on the Corsair card (R12 reworded), which
   is a requirement change pending Patrik's agreement (v2 open point 1). R15 (audio) post-dates C1 and is v2's §5a.
5. One internal inconsistency: F1 sets the SDR12 meter take at 50 fps while F8 asks for a 5-10 % overshoot of 30-60 s; 50 fps is ~19 % above
   the ~42 fps record and gives a ~13 s take at a 1.4 GB budget. Otherwise the design is sound and cheaper than v1 (8.5-11 vs 9.8-15 TB);
   the warm-ups and confirmation takes are cheap insurance even where F1/F2's evidence is thinner than stated.

### v2's adoption (`plan-v2.md`, `v2-rules-from-C1.md`)

- Adopted correctly: F1 (bracket, step 1, two concordant takes), F3/F10 (pooled controls, start/end controls, ABBA, drift flag, "not shown"
  non-terminal), F4 (15-min unsplit only; 30-min unsplit first; split on a late directory-signature drop or as the soak; signatures),
  F5 (0.6 / 512, budget logged, seconds of input), F6 (no log(T) fit; survival table), F7 (claims table), F8 (meter rule, smoke test),
  F9 (labels), F11 (TDN-on unlogged at 25 fps; phase-lock probe; pre-roll first), F12 (reasoning stated). Stage table and budget match C1 §2
  within rounding (S2 2.2 TB vs 2.35; total 8.3 / 11.4 vs 8.5-11).
- Adopted with a C1 defect carried over: "SDR12 from a meter take at 50 fps" (conflicts with v2's own 5-10 % rule, §7); "failures are short,
  so a confirmation take costs only its time to the drop" (§7; false in the single-frame regime, 25-75 GB); F2's warm-up at the strength
  C1 gave it (fine as insurance; the handoff should not cite 9-54 frames as the in-regime size).
- Skipped: "a lever pair never starts a block" (in v2-rules, implied by the S2 order, absent from v2 §7); F4(4) "one pair per mode gives
  'consistent with' readings only" (v2 §7 reads '= the directory matters at that length'); F7's "most valuable extra take" (a second
  unsplit 30-min take per winning arm) is not offered — v2 §8 says a 30-min take is never repeated unless void; the pooled-exposure
  caveat (F6, constant hazard) is not stated.
- Changed beyond C1: the campaign card is the Corsair (constraints §12-13 said Kingston); Part B replaces the "15-min + max take per mode
  per card" transfer set with one unsplit 30-min take per mode per card; the R4 row does not flag the two-takes deviation. All three are
  defensible; the first two need the owner's word, the third a sentence.
