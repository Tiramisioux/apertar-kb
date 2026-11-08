# C5: challenger design for the NVMe 4K campaign, then the comparison with plan v2 (2026-11-08)

Critic: challenger. Written in two passes as the brief asks: sections 1-11 were written from `constraints-and-arithmetic.md`
(all sections, R1-R15), the KB pages named in the brief, the research reports R1, R2, R3, R8, R10 and C1 **before** reading
`plan-v2.md` or `v2-rules-from-C1.md`; sections 12-14 compare afterwards. Labels are the KB's own (measured / derived /
probable / unconfirmed / web); my own arithmetic is marked **C5 derived**. Nothing ran on the camera or the network.

Rig for this design (brief update of 2026-11-08 afternoon): one card, the owner's Corsair MP600 Mini 1 TB (the record's test
card, serial `A936B442006AC2`, firmware ERFM11.1, 999,960,870,912 B = ~990 GB usable with a 10 GB reserve; 600 TBW, pSLC
~50 GB, post-cache ~800 MB/s: all three **web**, R8 §2), CM5 Lite C0, Core `cinemate-port` `ba0658d` since the 13:00 boot
(`frames_per_folder=0`, `clip_merge` ON by default; fork-log 175-195), UI `7ea9afc`. A short check on the other Corsair
card(s) at the end.

## 1. The one idea: pay long bytes only where the question is open

Every take is paid in bytes (R3) and in hours. A take buys information only if (a) its outcome is uncertain before it runs and
(b) the outcome changes a decision. Three consequences shape everything below:

1. **Two questions, two instruments.** The fps ceiling of a mode is a capture-side question that short takes answer (the
   record's drops at 27-30 fps come within 4-170 s: `findings-2026-11-04.md:42`, e4 rows t1/t2, measured). Whether a clean fps
   survives 30 minutes is a time-growth question (file count, fill, heat, process age) that **only** a long take at ONE fps
   answers. So: a 3-min screen decides the fps; every long tier runs once, at that fps, and never refines fps by long takes.
2. **Predicted outcomes are not recorded.** TDN on at the edge (BE job 37 ms vs a 35.7 ms period, measured p = 1/6), phase
   lock on (10 holes per 60 s, measured), HDR16 lossless (encoder 17.5 fps, measured), SDR12 uncompressed at 50 fps (#25:
   safety stop at ~22 s, drive-bound, measured): a pair on any of these answers nothing and spends the time to the first drop.
   Each gets at most one short probe, and only where the probe tests a *different* hypothesis (section 4).
3. **Meters instead of ladders where a meter exists.** Core's RAM-buffer level (`buffer_used`, 1 Hz) gives a storage-limited
   arm's capacity in one short take (`drain_fps = fps - d(buffer)/dt`, storage-slowdown plan §4.1, with C1 F8's duration
   correction); the storage pre-roll gives every compression arm's encoder capacity in 2 s (`estimated_capacity_fps`,
   measured on the camera: HDR16 lossless 16.84, SDR12 lossless 48.13 at 33 fps); Core's CPU slope over a long take is the
   directory walk's in-take signature (reanalysis §4: c = 77-133 ns derived from 17 SSD takes; the probe's direct c = 63.3 ns
   measured). These replace fps walks for storage-limited arms and replace one member of every split pair with a reading.

## 2. The arms and what the record already says (the priors the design is built on)

File sizes: HDR16 uncompressed 16.59 MB (measured, `hardware-log.md:140`); HDR16 Log 12.45 MB (measured, one DNG); SDR12 and
HDR12 uncompressed 12.44 MB (derived); SDR12 lossless ~5.98 MB (measured, one scene). Card: 990 GB usable. Create cost in one
folder from the probe's fit `median_ns = -183,673 + 316.64 x files` (measured, `probe-exfat-dir.md:60`).

| Arm | Record (label) | Open question the campaign must answer | Fits 30 min on 990 GB? | 30-min files; create as share of the period (C5 derived from the fit) |
| --- | --- | --- | --- | --- |
| HDR16 unc 25 fps | 10 min clean 4 of 7, all TDN on, WebUI closed (R1 §3); 3-min TDN-off 1+0, 2+0 (measured) | 30 min at 25 is the floor target; needs no screen | yes: 747 GB (75 %) | 45,000; 14.1 ms = 35 % |
| HDR16 unc 28 fps | d4: 180 s / 5,055, 0 lost, TDN off + FE depth 4, WebUI stand-in (measured, n = 1); depth 2 lost 1-5 (measured) | second concordant clean take (the registered rule), then 15 and 30 min | yes: 836 GB (84 %) | 50,400; 15.8 ms = 44 % |
| HDR16 unc 29-30 fps | 30: t1 3 lost at 119 s with depth 4, BE slows, write queue 11/12 (measured); 29 never run | 29 is one 3-min take away; 30 is out unless Log moves the back end | 30: 896 GB (90 %) | 54,000; 16.9 ms = 51 % |
| HDR16 + Log 28 / 30 fps | one 117-frame take, 10 lost, old build, WebUI open (measured, uncontrolled); +0.62 GB/s DRAM net (derived), -25 % NVMe bytes | the only byte-reducing lever for 30 fps; sign unknown (R2 §2c) | yes: 628 / 672 GB | as above |
| SDR12 unc 33 fps | t2b 601 s / 19,857, 0 lost, 72 C at the end (measured) | nothing at 33; the question is the ceiling (O3 ~42 fps unconfirmed; #23 50 fps 554 lost; #25 drive-bound ~550 MB/s derived) | yes: 739 GB | 59,400; 18.6 ms = 61 % |
| SDR12 unc 42-44 fps | none | the storage/capture frontier between 33 and 50 | 42: 941 GB (fits, 1 % spare); 44: 985 GB (does **not** fit: 29.9 min) | 75,600 at 42; 23.8 ms = **100 %** of 23.8 ms |
| SDR12 lossless 33 / 42 fps | t2a 601 s / 19,851, 0 lost, 2.81 cores (measured); pre-roll capacity 48.13 at 33, 62.9 at 30 (measured, 2 s) | the CPU ceiling (~4.2 cores derived at 50: out); 42 is the candidate | yes: 452 GB at 42 | 75,600; 100 % |
| HDR12 unc 30 fps | **no NVMe take at all** (the SSD run skipped it) | everything; same bytes as SDR12 | yes: 672 GB | 54,000; 51 % |
| 4K crops (3840x{2076/2072, 1608} at 12-bit; 16-bit heights unknown) | one take: 2076 at 50 fps lost 12 % at capture, old build, untrimmed 80 % card (measured) | their fps ceilings; a 16-bit crop list first (`list_sensor_modes`) | 2076 at 44: 947 GB; 1608 at 42: 700 GB | 75,600-79,200; 100-115 % |

Reading: on this card every HDR arm fits 30 min; the SDR12 arms above ~42 fps and the 1.85:1 crop above ~44 fps run "until
the card is full" (the owner's `pass_drive_full` rule, minutes logged) and that **is** their 30-min answer. And at every
SDR12 arm above 33 fps the single-folder create cost at the 30-min file count is at or above the frame period: a single-folder
30-min SDR12 take at 42 fps is predicted to fail by the directory walk alone, before any drive or camera limit (C5 derived from
the measured fit; the live-system share is the open part, section 5).

## 3. Stages, in order, with what each decides

Every stage below runs unattended from the Pi runner (R7) except where "owner" is written. Bytes are the test card's; "take"
means a camera take with stop-on-drop (R4) unless marked meter/probe/warm-up.

| Stage | What runs | Camera | Decides | Bytes (C5 derived) | Hours |
| --- | --- | --- | --- | --- | --- |
| **S0 facts** (owner present ~30 min) | card model/serial/size/firmware (`/sys/class/nvme`, `df -B1`), `nvme smart-log` baseline (owner, sudo), `vcgencmd get_throttled` + `pmic_read_adc` EXT5V, kernel log since boot, Core binary (`/proc/<pid>/exe`, `get_state` has `frames_per_folder`/`clip_merge_*`), `list_sensor_modes` (the 16-bit crop heights the KB lacks), the FE depth-4 drop-in + ONE Core restart (owner, sudo), pre-roll line, `set_clip_merge enabled=false` read back, ladder off, ramp off, phase lock off, tuning read-back, WebUI stand-in reachable. (The probe's step 4, the cold-cache delete, was measured at 13:16 while this was being written: 52.8 ns per entry, 13.6 s for 10,000 files, a flat 45,000-frame clip ~4.5 min after a boot, derived; `probe-exfat-dir.md` step 4. Nothing of it is left to run.) | no | the rig is the one the record describes | 0 | 0.5 |
| **S1 camera-free probes** (Core idle, not stopped) | (a) one direct-write run, 100 GB, O_DIRECT 16 MiB blocks, 1-s bandwidth log (`exfat_write_probe.py --direct --chunk-kb 0`): the pSLC knee (~50 GB, web) and the TLC floor on this Gen 3 x1 link, plus the drive's own temperature slope at full rate; (b) paced small-file probe for the directory effect at the two real create rates: 1 MB files, 4 workers, 25 files/s for 30 min in ONE folder (45,000 files, 45 GB) and 42 files/s for 30 min (75,600 files, 75 GB), each once flat and once `--subdir 5000`: the create-latency-vs-N curve in a live write pattern at ~6 % of a take's wear; (c) smoke test: `--max-seconds 20` take with the new sampler columns (`buffer_used` at byte resolution at 1 Hz, `/sys/block/nvme0n1/stat`, dirty/writeback, trim state, audio columns) and the integral identity sum(fps - drain) = buffer level checked | (c) only | whether anything ≥ 500 MB/s sustained is drive-limited on this card (SDR12 unc ≥ 42 fps, HDR16 30 fps); whether the directory walk shows up at the real create rate without the camera; that the meter works | ~250 GB | 2.5 |
| **S2 screen, HDR16 block** (one Core process; warm-up first) | 60-s unscored warm-up at 28; **28 fps: 3-min take, then the confirmation as a 5-min take** (two concordant clean = clean at 3 and 5 min: the owner's 3 -> 5 tiers in one pair); **29 fps**: one 3-min take, a second only if clean; 30 fps: not run (ruled out 11-04) except as the Log probe below. Levers at 28: Log ABBA (4 x 3 min); WebUI-off ABBA (4 x 3 min); one TDN-on 3-min take at 25 fps with NO debug log or trace (O1's instrumentation hypothesis, `observations-2026-11-04.md:58-61`); one 60-s phase-lock probe at 25 (the 11-04 `{d, d+1}` fix, `fork-log.md` 69a700e); Log at 30 fps: one 3-min take (stop-on-drop: cheap if it fails, decisive if it does not). Controls: the plain 28-fps baseline at the block's start and end, pooled with the walk | yes | the HDR16 fps for the long tiers; whether Log is carried as a second HDR16 arm; the TDN and WebUI real-use costs | ~1.1 TB | 3 |
| **S2 screen, SDR12 block** (owner-free) | warm-up; **meter take** uncompressed at 50 fps (safety stop in ~13-18 s at a 1.4 GB budget, C1 F8; 11 GB) -> capacity C_u; screen uncompressed at floor(0.97 C_u) with the 3 + 5 min pair, one step down on a drop; manual `storage_preroll` for lossless (encoder capacity, 1 GB); lossless 3 + 5 min pair at 42 fps, then 45 only if 42 is clean twice; storage stack (`workers 2`, `queue 24`, `sync_ms 2000` as ONE variant vs base) as two meter takes each, only if C_u < 50 fps (storage-limited) | yes | the SDR12 recipe fps for uncompressed and lossless; whether any storage knob moves the capacity at 4K on the NVMe (never measured under `sync`) | ~0.7 TB | 2 |
| **S2 screen, HDR12 block** | warm-up; 30 fps 3 + 5 min pair; 29 on a drop. Log: not run (12-bit Log leaves the file the same size, SSD measured) | yes | HDR12's recipe fps (no record exists) | ~0.3 TB | 1 |
| **S2 screen, crops** (last; optional per the owner) | the 1.85:1 (2076 or 2072) and 2.39:1 (1608) crops in HDR16 (if the probe lists 16-bit heights) and SDR12 uncompressed: start at the full-frame clean fps + 3, step down 3 on a drop, up 1 on a clean take, 3-min takes, two concordant at the final fps; 4 arms x ~3 takes | yes | each crop's fps ceiling (3-min, n = 2) | ~0.6 TB | 2 |
| **S4 15 min** (the fill tier) | one 15-min take per carried arm at its screen fps, **without deleting between takes until the physical gate forces it**: HDR16 28 (418 GB, card 0 -> 42 %), then SDR12 unc at C_u-1 (481 GB at 43 fps, -> **91 %**: the near-full trimmed-card condition the record never had, R10; the gate admits it: 481 x 1.03 + 10 = 505 < 572 free), then delete all + Core trim, HDR12 30 (336 GB), SDR12 lossless 42 (226 GB), Log 28 if carried (314 GB, -> 88 %); crops only if the owner asks (one each). Single folder (22,500-37,800 files = 17-57 % of the period): the CPU slope and buffer curve are read as the directory meter; no split pair here | yes | survival to 15 min at the screen fps under rising fill and heat; the live directory signature at 22,500-38,000 files; the runner-up replaces an arm that drops early (capture gaps) | ~1.8 TB | 2.5 |
| **S5 30 min** | one 30-min take per carried arm; the card is emptied + trimmed before each heavy take (forced by the gate: a 30-min HDR take alone is 75-90 % of the card). Folder policy per section 5: HDR16 and HDR12 **unsplit first**; SDR12 arms **split (5,000) first** because their single-folder create cost is ≥ 100 % of the period; SDR12 unc at ≥ 43 fps runs to `pass_drive_full` (29.9 min) | yes | the 30-min verdict per arm (n = 1), the attribution signature of any late drop | ~3.1 TB | 3 |
| **S6 the split member / repeat** | for each HDR arm whose unsplit 30-min take passed or dropped late: the same take split (5,000 per part); for SDR12 unc: the unsplit control ONLY if the paced probe of S1 did not already show the directory failure at 42 files/s (else skipped as predicted); SDR12 lossless: no unsplit (predicted 100 %). The split member is also the arm's second 30-min datum (repeatability of fill, heat, file count) and starts hot (no cool-down) | yes | R13: whether splitting changes a 30-min take (pair, conservative order for the HDR arms); the "happened twice" claim | ~2.1 TB (HDR16 + HDR12 + SDR12 lossless split; +0.94 TB if the SDR12 unc control runs) | 2.5 |
| **S7 other card(s) check** (owner swaps) | S0 facts on the card (part number: MN vs MNR2 vs CORE Mini, R8 §2), the 100 GB direct-write knee/floor, then one 15-min take of the HDR16 recipe and one of the heaviest SDR12 recipe, same database; compare the per-second temperature slope, device write latency and buffer curve with the test card's | yes | per-card drive facts (pSLC, floor, heat) that do not transfer; n = 1 per card | ~1.0 TB per card (on that card) | 1.5 per card |

Total on the test card: **~9.9 TB** (= 1.65 % of 600 TBW, web rating; C5 derived), about 17 h of runner time (three evenings
or one weekend). The optional extras are named where they sit: the SDR12 unc unsplit control (+0.94 TB), a crop at 15 min
(+0.3-0.5 TB each), a third 30-min take of the HDR16 winner (+0.84 TB).

## 4. How each lever is tested (R2)

| Lever | State in the campaign | Test | Why this and not a pair at the edge |
| --- | --- | --- | --- |
| Storage tuning (`dontneed`, `writeback`, `sync_ms`, `workers`, `queue`, `kernel_tune`) | fixed: `sync`, on, 1000, 4, 12 (the record's state; `media-tune-file.md`); `kernel_tune` not installed (R2 §4) | ONE combined stack vs base as meter takes, only in a storage-limited arm (SDR12 unc above C_u); dropped at once if the capacity does not move by more than the meter's spread | the SSD A/B showed nothing in 24 takes (measured); on the NVMe the record's limits were never storage at ≤ 33 fps (`nvme-4k-recipe-plan.md:15`) |
| Compression | per arm (uncompressed; lossless for SDR12 only) | the storage pre-roll first (2 s, ~1 GB): `estimated_capacity_fps` is the encoder edge; a 3 + 5 min pair only for arms whose encoder capacity exceeds the uncompressed edge (SDR12 lossless) | HDR16 lossless is out by the encoder (measured); Log + lossless made 4K files bigger on the SSD (measured) |
| Log (HDR16 only) | off by default; carried as a second HDR16 arm if it wins | ABBA at 28 (4 x 3 min) vs the baseline, read as time-to-drop AND Core CPU (copy worker) AND the drop class; one 3-min probe at 30 fps; carried into S4/S5 only if it beats every pooled control at 28 or is the only clean arm at 30. Owner's desk task before adoption: open one Log DNG in Resolve | the one untried byte-reducing lever for 30 fps (`recipe.md:68-70`); its DRAM cost may cancel the gain (R2 §2c): sign unknown = information |
| TDN | off (the recipe's row 7, p = 1/6 + the 28-fps d4 take) | one 3-min TDN-on take at 25 fps with no debug log / trace (O1 lost 1 in 10 min with TDN on unlogged; the instrumented units lost 39-116) | TDN on at 27-28 is a predicted failure (37 ms job vs 35.7 ms period); the open question is O1's, not the edge |
| Phase lock | off | one 60-s probe at 25 fps on the `{d, d+1}` build; never a factor in elimination | measured negative on 2026-10-26; the 11-04 fix is unmeasured; 25 GB buys that reading |
| WebUI | ON (real use) via the Mac stand-in; held constant | one ABBA pair OFF vs ON at 28 fps HDR16 (4 x 3 min) | no clean 10-min take with the WebUI open exists except O1 (1 lost); the cost of the owner's own setting is worth 4 short takes |
| FE Config depth | 4 (the recipe's row 8; the drop-in set once per evening by the owner) | the second clean depth-4 take at 28 fps is S2's first pair (the registered rule, `preregistration.md:750-752`); a depth-2 replicate = 2 x 3-min takes at 28 at the START of evening 2 while the owner is there for the two restarts (depth-2 takes fail in 44-77 s: ~40 GB) | n = 1 + 1 today; a Core restart with sudo per switch makes it an owner-present block, not a runner lever |
| Clip split (`frames_per_folder`) | 0 in the screen and S4; 5,000 where section 5 says; merge worker OFF (`set_clip_merge enabled=false`) for the whole campaign, restored at the end | section 5 | |
| fps | the screen's verdict; long tiers never refine it | 1-fps steps inside the record's bracket; two concordant takes per verdict (C1 F1) | |

## 5. The 30-minute question and the split question (R9, R13, R14)

1. **Where the directory cost crosses the line.** From the measured fit (c = 63.3 ns, 5 entries per file): the 25 %
   ceiling is 32,161 files at 25 fps, 28,777 at 28, 26,898 at 30, 24,505 at 33, 19,400 at 42 (C5 derived). So the 15-min
   tier is under the line for every HDR arm (22,500-27,000 files, 17-27 %) and the 30-min tier is over it everywhere: 35-51 %
   for the HDR arms, **100 % or more for every SDR12 arm at ≥ 42 fps**. The split question is therefore a 30-min question only
   (no 15-min pair), and it has two regimes:
   - HDR arms (≤ 30 fps, 44-51 % at 30 min): genuinely open. The SSD run passed 30 min in one folder at 56-97 % shares
     where the write pattern had margin (reanalysis §4, measured) and failed at 33,500-62,000 files where it did not. On the
     NVMe nothing above 19,857 files exists. Order: **unsplit first**, the split member second (C1 F4's conservative order:
     heat and process age work against "splitting helps"), on an emptied card both times (the gate forces it: fill is
     equalised by construction).
   - SDR12 arms at ≥ 42 fps (≥ 100 %): the single-folder take is a predicted failure in minute ~20 (when 5cN plus the
     mapping share reaches the period; C5 derived). Order: **split first** (it is the real 30-min test); the unsplit
     control only if S1's paced probe at 42 files/s did not already fail in one folder and pass with `--subdir 5000`.
2. **The in-take meter replaces the second member where it can.** Every long take records Core's CPU slope (expected
   5 x c x fps^2 per second for the walk alone = 0.25 cores per 1,000 s at 28 fps; C5 derived from c = 63.3 ns), the buffer
   level, the device write latency (`/sys/block/nvme0n1/stat` ticks per write) and temperature. A split take must show a
   flat Core CPU; an unsplit take's slope gives the live c. A late drop is attributed by the pre-registered signatures
   (section 8) before any pair is read.
3. **Camera-free first.** S1(b) measures create latency vs N at the real create rates with 1 MB files (45-75 GB per run):
   if the paced probe fails in one folder at ~45,000-75,000 files and passes split, the mechanism is confirmed at 6 % of a
   take's wear; the live pairs then measure the size of the effect with 16.6 MB files and four writers, not its existence.
4. **The fit-tier arms.** SDR12 unc at 44 fps (985 GB) and the 1.85:1 crop at 50 fps (1,076 GB) do not fit 30 min on 990 GB:
   they run to `pass_drive_full` (< 6 GiB free) and the minutes reached are the answer (R11). The near-full condition is
   thereby exercised on a trimmed card at every such take; the per-second device latency in the last minutes is the
   reading for "does fill matter when trimmed" (#78's open question, `inspection-2026-11-02.md:523`).
5. **The 30-min verdict per arm is n = 1 (unsplit) + 1 (split)** and is stated that way: "a 30-min drop-free take was
   recorded at these settings, once unsplit and once split" bounds the per-frame rate at 3.3e-5 (95 %; C1 §0), i.e. up to 1.5
   losses per 30-min take remain compatible. R14's "30 min in all 4K modes" is reported as this table, not as a property.

## 6. Ordering so that fill and temperature are exercised on purpose (R5, R6, R10)

- **No cool-down anywhere; temperature logged every second** (the `nvme` hwmon, no sudo; `critical_warning` via the owner's
  `smartlog` at evening start/end). The second member of every pair and every S6 take starts hot by design.
- **Delete only when the gate says so**: `free >= planned x 1.03 + 10 GB`, else delete the oldest campaign clips listed in the
  database (never anything else; never the owner's `cDNG_26-11-07_C0001`), wait for Core's `media: trim` line or 60 s. S4's
  order (HDR16 -> SDR12 uncompressed) fills the card 0 -> 42 -> 91 % across two takes before the first delete, and (HDR12 ->
  SDR12 lossless -> Log) 0 -> 34 -> 57 -> 88 % after it: the high-fill-trimmed condition at 15 min for free (a third 15-min take
  never fits beside two under the gate's 3 % + 10 GB margin: C5 checked). S5/S6 take the card to 75-95 % in every heavy take.
- **Process age**: one Core process per screening block (the FE depth-4 drop-in makes a restart an owner step anyway), a
  60-s warm-up after every restart, reboot or mode switch (C1 F2), `uptime_s` and `takes_since_restart` on every row.
- **Resume**: after a reboot (the 2026-11-06 under-voltage resets) the runner resumes once (sentinel + the watchdog first);
  a second reset stops the campaign.

## 7. Runner, status file and database (R7, R8, R15)

Built on `working/tools/longtakes.py` (R10: stages, resume, DB, sampler, WebUI stand-in, audio format fallback, Log probe)
plus the unmerged branch's telemetry (`buffer_used`, `/sys/block` stat, dirty/writeback, trim state, `core_cpu_slope`).
What is new, in build order (sizes are C5 estimates in lines of Python):

| # | Piece | Lines | Blocks |
| --- | --- | --- | --- |
| 1 | `--disk-mbps` from S1's measured floor; `--modes` with the 4K crops (fix `mode_size_mb` for 16-bit crop heights read from `list_sensor_modes`); `DISK_MBPS=354` never used on the NVMe | 40 | S2 |
| 2 | status.md / status.json rewritten atomically at every transition **between** takes (take id, arm, why now, planned s/GB/end; after: verdict, lost, first drop s, temps, fill, GB, prognosis; queue ahead; eliminated arms; last 10 rows; `decisions.log` tail); the header "take N running since HH:MM until HH:MM" during a take | 120 | S2 |
| 3 | fit gate + delete-when-needed from the DB's own clip list; Core trim wait; never a glob | 60 | S4 |
| 4 | warm-up stage `w` (unscored), the 3 + 5 min concordant pair, pooled controls at block start/end, ABBA lever pairs | 120 | S2 |
| 5 | meter stage `m` with the duration from the budget (`0.9 x budget / (rate x overshoot)`), the integral identity check, `capacity_fps` with spread | 60 | S2 |
| 6 | split control: `set_frames_per_folder`, `set_clip_merge enabled=false` at start (restored at end), `verify()` of both, `parts` counted | 40 | S5 |
| 7 | watchdog before/after every take: kernel log (`nvme`, `pcie`, `exfat`, `I/O error`, `Undervoltage`), `media_alive`, Core `error`, `critical_warning` where readable; never retry; `record_stop` in `finally` and on SIGINT | 60 | S2 |
| 8 | write budget: cumulative GB per card, projection before each take, `--budget-gb`, the ledger (`/sys/block/nvme0n1/stat` sectors per take; smart-log DU at evening start/end from the owner) | 40 | S2 |
| 9 | audio columns (`buffer_frames/period_frames`, `peak_backlog_kb`, discontinuities, pad/trim, drift, errors) and outcome `audio_fault`: the take ended by itself with all frames written -> repeated once, never eliminates an arm; twice in a row -> stop the night; the journal window, `vmstat` compaction and USB lines at that second kept | 50 | S2 |
| 10 | pre-registered attribution signatures computed per long take (CPU slope vs the walk's prediction, buffer rising, device latency trend vs fill, temperature) written into the row as `attribution` | 60 | S4 |
| 11 | claims table and survival table in `results.md` (exposure frames pooled per arm, 3/n bound) | 40 | end |

Database: the existing `longtakes.db` on the SD card (`~/longtakes/<run>/`), one row per take with the arm (every lever
value, mode, fps, `frames_per_folder`, `clip_merge`, FE depth from the YAML md5, `dontneed/writeback/sync_ms` from the
`recording clip:` line, `tune_override`), Core commit/pid/uptime, the counters (`dropped_gap_estimate`, `dropped_queue_full`,
`dropped_copy_slot`, `peak_queue`, `queue_bytes_peak/budget`, `write_failures`), frames written vs fps x s, files and parts,
GB (du and sectors delta), fill before/after, NVMe and SoC temperature start/max/end, throttled flags, MemFree, audio columns,
the 1 Hz samples, the journal window, verdict and `attribution`. Filled between takes only (`join_ingest` before the next
`record_start`); the status file is the only thing a watcher reads (`ssh apertar cat ~/longtakes/<run>/status.md`); no
`journalctl`, `top`, `ls /media/RAW` or builds during a take.

## 8. Pre-registered rules (before the first take) and the claims table

1. A take stops at the first dropped frame (`recording_dropped_frames` > 0 at 1 Hz), at Core's safety stop (`buffer_full`:
   its own result), at the gate's `pass_drive_full`, or at its planned length. `audio_fault` is a third class (rule 9).
2. A screening verdict needs two concordant takes (the 3-min and the 5-min take): 2 clean = clean at 3 and 5 min; 2 drops =
   the cell is out at that fps; 1-1 = a third 3-min take decides.
3. A lever is "better" only if it beats every pooled control of its block AND replicates in the second pair (ABBA) AND the
   direction was pre-registered; otherwise "not shown (n = 2 pairs)" and it is not carried to S4; never "no difference".
4. The long tiers run at the highest fps with two concordant clean screen takes. After an **early** drop (capture gaps,
   no time-growing signature) the arm steps down 1 fps for the next tier; after a **late** drop (> 10 min) with a signature
   the fps stays and the attribution plus the split rule apply.
5. Attribution signatures, read per long take in this order: (a) Core CPU slope within 50 % of 5 x c x fps^2 (c = 63.3 ns)
   and the buffer rising only in the last minutes with flat device latency -> directory; (b) device write ticks per write
   rising with fill and the buffer rising -> drive state / fill; (c) temperature plateau > 75 C with latency rising ->
   heat; (d) dirty/writeback kB rising -> page cache; (e) none of these, with `recording_dropped_frames` > 0 and written < enqueued (this Core base prints no `dropped_gap_estimate` line, `clip-split-verify.md`; the per-drop journal lines it does print are listed by one forced-drop take before S2) -> capture side.
6. Split verdict (one pair per arm at 30 min): unsplit drops late with signature (a) and split passes -> the directory
   matters (effect = time difference, CPU slope); both pass -> no effect at this length; both drop at similar times -> not
   the directory; split drops and unsplit passes -> recorded with its heat/age confound, no claim.
7. Fill gate physical only (section 6); fill is a covariate on every row.
8. Voids (decided from the checks before any analysis): mode line differs from the request, `fps_speed_ramp` true, a
   client connected or lost mid-take, a build or another session's process, the card serial wrong, the FE YAML md5 wrong,
   `clip_merge` on when it should be off.
9. Stop the night: `critical_warning != 0`, any kernel `nvme`/`pcie`/exFAT error, under-voltage, Core `error`, a dead take
   script (`record_stop` at once), a second void, `audio_fault` twice in a row, the budget.
10. Labels: every number carries measured / derived / probable / unconfirmed and the n of its cell.

Claims table (what the campaign can say at the end): per arm, "clean 3 + 5 min (n = 2)", "clean 15 min (n = 1)", "clean
30 min unsplit (n = 1) / split (n = 1)", the pooled exposure in frames and its 3/n rate bound, the levers carried with their
pair results, the eliminated cells with the tier and class of their drop, and for the other card(s) "15 min, n = 1 per card".

## 9. Wear and time per stage (test card; C5 derived)

| Stage | GB | Hours | Share of 600 TBW |
| --- | --- | --- | --- |
| S0 + S1 | 250 | 3 | 0.04 % |
| S2 HDR16 / SDR12 / HDR12 / crops | 1,100 / 700 / 300 / 600 | 3 / 2 / 1 / 2 | 0.45 % |
| S4 15 min | 1,800 | 2.5 | 0.30 % |
| S5 30 min | 3,100 | 3 | 0.52 % |
| S6 split / repeat | 2,100 (+940 optional) | 2.5 | 0.35 % |
| **Total** | **~9,950** | **~19** | **1.65 %** |
| S7 per other card | 1,000 on that card | 1.5 | 0.17 % of that card |

Against the record's own spend: the four drop-frames evenings wrote 0.84-1.55 TB each (R3 §5, measured); the SSD ladder 5.9 TB
on the T7. Where to cut if the owner wants fewer bytes, in order: the crops' screen (-0.6 TB), HDR12's split member (-0.67 TB,
keep unsplit only unless it drops late), the SDR12 unc unsplit control (already optional).

## 10. The other card(s) check (R12)

Core-side levers transfer as settings; drive-side facts do not (pSLC size and post-cache floor, heat in the CFe-B shell,
trim behaviour, the part number: MN / MNR2 / CORE Mini differ in controller and NAND, R8 §2). Per card: S0 facts with the
part number, the 100 GB direct-write knee/floor and temperature slope, one 15-min HDR16 take at the recipe fps and one
15-min take of the heaviest SDR12 recipe, same database, same gate; compare the per-second series with the test card's
(temperature slope, device latency, buffer curve). ~1 TB and 1.5 h per card. No 30-min take on a shooting card unless the
owner asks (0.84 TB each). Labelled "n = 1 per card".

## 11. The very first evening

1. Owner present (30 min): S0 facts, `nvme smart-log` baseline, the FE depth-4 drop-in and one Core restart, `set_clip_merge`
   off read back, the WebUI stand-in started on the Mac, the ladder off, the first desk task
   for the Opus thread (R15: the 32-s `Broken pipe` take's journal window and whether `ba0658d` treats EPIPE as fatal).
2. Runner, unattended: S1(a) direct-write 100 GB -> S1(c) smoke test -> S1(b) paced probes (1 h) -> S2 HDR16 block (3 h).
3. The owner reads `status.md` once before bed; the HDR16 block's result (28 fps clean twice or not; Log's pairs) sets
   evening 2's queue, which starts with the depth-2 block while the owner is there for the two restarts.

## 12. Comparison with plan v2 (`plan-v2.md`, 13:00) and `v2-rules-from-C1.md`

Read after sections 1-11 were written. v2 already carries C1's rules (F1-F12), so most of my design's statistics (record's
bracket, two concordant takes, pooled controls + ABBA, warm-ups, the 0.6 / 512 budget, no log(T) fit, unsplit-first for the
HDR arms, the meter's duration from the budget, the claims table) coincides with v2. The differences that matter are below,
ranked by consequence for the campaign's outcome (bytes, hours, or a result read wrongly).

### 12.1 Where my design is better than v2

| # | v2 section | What v2 does | What my design does | Why mine is better (evidence) | Consequence |
| --- | --- | --- | --- | --- | --- |
| 1 | §3, §5 table, §6 S5 ("UNSPLIT FIRST per mode") | the 25 % line and the create shares are computed only up to 33 fps (24,505 files; 61 %); the SDR12 arms are screened "from a meter take at 50 fps, then capacity -1 / -2" (42-44 fps) and then run the 30-min tier **unsplit first**, the split member "only if the unsplit take drops late with the directory signature" | section 2 and 5: at 42 fps a 30-min clip is 75,600 files and the single-folder create is 23.75 ms against a 23.81 ms period (**99.7 %**); at 44 fps 110 %. For the SDR12 family (uncompressed and lossless alike, the walk is per file) the unsplit 30-min take is a **predicted failure** in minute ~21-25 (when 5cN plus the mapping share reaches the period; C5 derived, probable), not an open question. My rule: at any arm whose single-folder create cost at the tier's final file count is >= 60 % of the period, the **split member runs first**; the unsplit control is optional and is first checked camera-free (S1(b)) | the probe's fit is measured (`probe-exfat-dir.md:60`, c = 63.3 ns, linear to 60,000 files, CPU-bound on one core); the walk runs under `s_lock` for every create (V-F4 row 16, confirmed in source), so at 42 creates/s x 23.8 ms the lock is 100 % busy walking before any write happens. v2's own §3 stops at 33 fps and so never sees it | v2 spends the SDR12 uncompressed unsplit take (21-25 min at 523 MB/s = **660-785 GB**) and the SDR12 lossless one (316-377 GB) to confirm a certainty, then runs the split members anyway (941 + 452 GB): ~1.0-1.2 TB and ~50 min of the 10 TB cap on two takes whose outcome is known; and the 30-min SDR12 verdict is delayed by a night. Also a finding v2 should state up front: **an SDR12 recipe at >= 42 fps for 30 min requires the split (or a Core change) on this kernel**, whatever the drive does |
| 2 | §6 S2 + S3 (a separate 5-min confirmation tier, ~400-600 GB, ~1 h) | two concordant 3-min takes per cell (C1 F1), then one 5-min take per carried arm in S3 | section 3 S2: the confirmation take of a clean cell **is** the 5-min take (3 + 5 min = two concordant takes of two lengths); S3 disappears | the second concordant take is required anyway; making it 5 min long satisfies R3's tiers (3 -> 5) and C1's rule with no extra take; C1 itself says the 5-min tier "adds little over 3 min (the bound goes 6.7e-4 -> 4.0e-4)" (C1 §2) | per carried cell 223 GB (84 + 139 at HDR16 28) instead of v2's 307 GB (84 + 84 + 139); over ~5 carried cells ~0.4 TB and about an hour saved, same statistical content |
| 3 | §6 S1 (write-pattern matrix at 300 files per variant; the 100 GB direct write; "drive-state writes") | no camera-free test of the directory effect at the real file counts (300 files cannot show a walk of 0.1 ms) | section 3 S1(b): the paced small-file probe (`exfat_write_probe.py`, 1 MB files, 4 workers) at the two real create rates, 25/s and 42/s for 30 min, flat and `--subdir 5000` (45 + 75 GB per pair, 120 GB in all) | it is the storage-slowdown plan's own paced-emulation step (§4.2, 88 GB on the T7) applied to the NVMe at the campaign's file rates; it measures create latency vs N inside a live four-writer pattern at ~6 % of a take's wear, and it is what lets the SDR12 unsplit control of item 1 be skipped | the directory mechanism is confirmed or refuted on the campaign card before any 30-min take, for 120 GB instead of ~1 TB |
| 4 | §4 crops ("two 3-min takes each at the winner's settings plus 1 fps; 30-min status predicted") | confirms a floor (full-frame winner + 1 fps) | section 3 S2 crops: a short down-walk from the full-frame fps + 3 (3-fps steps down on a drop, 1 up on a clean take, two concordant takes at the final fps), ~3 takes per arm | the crops' question in R1 is their own ceiling: a 2.39:1 crop reads 74 % of the rows and the 16-bit crops are probed at 31.9-42.4 fps (fork-log 31d5418); the only crop take lost 12 % at 50 fps (M3, old build, untrimmed 80 % card: measured) so the ceiling is unknown in both directions; v2's +1 take answers "at least as good as full frame" only | the campaign's crop answer becomes "clean at X fps for 3 + 5 min (n = 2)" instead of "clean at winner + 1"; cost ~0.15 TB per crop arm (0.6 TB for four), the owner's choice |
| 5 | §6 fill gate (correct) but S4 unordered | "one UNSPLIT take per mode" with the gate deleting when needed; the fill condition is reached by accident, if at all | section 3 S4 and section 6: the order is chosen so that the second take of the tier ends at ~91 % and a later one at ~88 % on a trimmed card, and the row records `fill_start/fill_end` | #78 lost 18 of 25 frames in its last minute at 94-97 % before the dirty-limit change (`night-2026-11-01.md:22-23`, probable); no trimmed-card high-fill datum exists (R3 §8 item 2); the gate's margin means three 15-min takes never coexist, so the order decides whether the condition is tested at all | the owner's R10 question (fill as a covariate) gets a deliberate datum at 15 min for zero extra bytes |
| 6 | §6 Part B (one 30-min take of the winning arm per mode per other card, ~2.2-2.4 TB per card) | three 30-min takes per shooting card | section 10: facts + part number, the 100 GB knee/floor probe with the temperature slope, one 15-min HDR16 and one 15-min SDR12 take (~1 TB per card) | what differs per card is drive-side (pSLC knee at ~50 GB = 2 min, the TLC floor, the shell's heat path, trim state: R8 §2, probable); all of it is visible inside 15 min and in the knee probe; the directory count and the capture side are card-independent (CPU) | 1.0 vs 2.4 TB and 1.5 vs 2.5 h per card; **but** v2's version tests "the recipe as it will be shot" on the actual shooting card, which the owner may want (see 12.2 item 5 and the hybrid) |
| 7 | §5 FE depth "4 (fixed)" | no depth-2 replicate | section 4: an optional 2 x 3-min depth-2 block at 28 fps at the start of evening 2 while the owner is there for the two restarts (~40 GB) | the registered 28-fps A/B is "Inconclusive" (`preregistration.md:750-752`); v2's S2 walk supplies the second clean D4 take, and the record already holds two depth-2 losses at 28 (d3, s28), so this is marginal: offered, not pressed | closes the evening-4 question the owner named, for 40 GB |

### 12.2 Where v2 is better than my design

| # | Topic | v2 | My design | Why v2 is better |
| --- | --- | --- | --- | --- |
| 1 | Runner and build list (`build-list.md` A1-A15, B1-B7, C, D, E, F) | a complete, anchored list against R10's risks: the NVMe speed constant (A1), deletion policy (A3), card detection (A4), watchdog (A5), signals (A6), sampler load (A7), kernel_tune disk name (A8), take ids (A9), split control (A10), status (A11), ledger (A12), audio (A13), the forced-drop check of which journal lines this binary prints (A15), the cold-delete budget (A3'), the root helper (D), Core prerequisites (E) | section 7's eleven items, no anchors, nothing on A6-A9, nothing on the helper | v2 had C2's review; A15 in particular is essential and my sections 7-8 assumed `dropped_gap_estimate` until the correction above |
| 2 | Audio (R15, v2 §5a) | the fault line's actual format (`recording failure: fault=write_error ... ALSA capture: Broken pipe`), the desk task of reading `AudioRecordingSession.cpp` / `TimestampedAudioCapture.cpp` at `ba0658d`, the Core fix proposed before the campaign, the levers in order, the USB-controller check | the columns, the `audio_fault` outcome and the levers, less detail | v2's reading of `clip-split-verify.md` gives the parser the right line; the "fix before the campaign" rule is right: a shoot must not lose a take to a 100 ms gap |
| 3 | Facts current at 13:00 | the cold-cache delete measured (52.8 ns per entry; a flat 45,000-frame clip ~4.5 min after a boot; split parts of 1,000 ~6 s) and budgeted in the gate ("never started within 10 min of a planned take"); the clip-split knob verified on the Pi (steps 2-9), the merge pause 33 ms after `record_start`, the two merge fixes `68516f1` / `01f170c` | written before those pages landed: my S0 had the cold delete as an item still to run (corrected above) and did not budget cold deletes | v2 is simply more current; the gate's cold-delete budget matters for a resume after a Pi reset |
| 4 | S1 write-pattern matrix at 4K size (~30 GB) | present | dropped in favour of the directory probe | it decides whether the storage plan's Core patches (ftruncate, one FLUSH per tick) are worth writing (M2/M3) and costs 30 GB; both probes belong in S1 |
| 5 | Part B's fidelity (R12 "as in real life") | one 30-min take per mode on the shooting card | 15-min takes | a 30-min take on the card that will be shot is the only reading the owner can take to a shoot without an inference step; my version is cheaper but inferential for the second half of a take |
| 6 | Pre-roll OFF during the campaign (a recorded deviation) | off | on (real use), absorbed by the warm-up | off removes one uncontrolled 60-fps event per Core start (its own drops, 0.7-1 GB written and deleted); with one Core process per evening either choice is defensible; v2's is the cleaner record |
| 7 | Stage sizing | S2 ~2.2 TB, S4 ~1.1 TB, S5 ~2.2 TB, S6 ~2.2 TB (best + runner-up cap per mode) | S4 1.8 TB and S5 3.1 TB because I carry up to five arms (HDR16, HDR16 + Log, SDR12 unc, SDR12 lossless, HDR12) | v2's "at most one lever variant per mode goes to the long tiers" (C1 F3) is the stricter wear rule; my carrying both SDR12 compressions and Log is only right if each wins its screen |

### 12.3 Same in both (so neither claims it)

The record's bracket at 1 fps with two concordant takes; warm-ups after restarts; pooled controls and ABBA; the TDN-on unlogged take
and the one phase-lock probe; the pre-roll reading per compression arm; the meter take for SDR12 uncompressed with its duration from the
budget; the budget at 0.6 / 512; the in-take directory meter (Core CPU slope, buffer curve, device latency) and the attribution
signatures; unsplit first for the HDR arms with the split member as the soak; the physical fill gate with delete-when-needed from the
database; the merge worker off; no cool-down; the status file written between takes only; the claims table with the 3/n bound.

### 12.4 Corrections made to my own sections 1-11 after re-checking (for transparency)

(a) the 25 % line at 42 fps is 19,400 files, not 18,500 (arithmetic); (b) the S4 sequence: three 15-min takes never coexist under
the gate's margin, so the fill is exercised to ~91 % by the second take, not 99 % by a third; (c) the probe's step 4 is done, not an S0
item; (d) attribution signature (e) reads `recording_dropped_frames` and written vs enqueued, since this base prints no
`dropped_gap_estimate` line (`clip-split-verify.md`).

## 13. The hybrid I recommend (v2 as the base, seven changes)

1. **Split-first rule for the SDR12 family** (v2 §6 S5, §7 split verdict): add the arithmetic column "single-folder create cost at
   the tier's final file count" to v2 §3 for every arm up to 50 fps (42 fps: 100 %, 44: 110 %, 50: 142 %), and the pre-registered
   rule: **>= 60 % of the period -> the split member (5,000 per part) runs first; the unsplit take is optional** and is run only if S1's
   paced probe did not show the single-folder failure at that create rate. Unsplit-first stays for the HDR arms (44-51 %). State in
   v2 §0 that an SDR12 recipe at >= 42 fps for 30 min requires the split on this kernel. Saves ~1.0-1.2 TB and ~50 min; removes two
   predicted failures from the long tiers.
2. **Fold S3 into S2**: the confirmation take of every clean screening cell is 5 min long; S3 is deleted; the 3 -> 5 tiers are met
   by the pair. Saves ~0.4 TB and ~1 h.
3. **S1 gets both probes**: v2's write-pattern matrix (30 GB) **and** the paced small-file directory probe at 25/s and 42/s, flat vs
   `--subdir 5000` (120 GB). Together with item 1 they decide the SDR12 unsplit control camera-free.
4. **S4 ordered for fill**: HDR16 first, the heaviest SDR12 arm second (ends ~91 % on a trimmed card), delete + trim, then the rest;
   `fill_start/fill_end` and the device latency in the last minutes read against #78's open question.
5. **Crops as the owner chooses**: v2's two confirmation takes at winner + 1 (cheap) or the ceiling down-walk (~0.15 TB per crop arm,
   n = 2 at the final fps); the plan names both prices.
6. **Part B per shooting card**: facts with the part number, the 100 GB knee/floor probe with the temperature slope, **one 30-min
   HDR16 take** (the owner's primary mode, as it will be shot) and one 15-min take of the heaviest SDR12 recipe: ~1.4 TB per card
   instead of 2.4, with the 30-min fidelity kept where it matters most.
7. **Optional, owner-present**: the 2 x 3-min depth-2 block at 28 fps at the start of evening 2 (~40 GB) to close the registered
   28-fps A/B.

Everything else stays as v2 has it: the build list A1-A15 with A15 before S2, §5a audio with the Core fix first, the pre-roll off, the
merge worker off, the budget at 0.6 / 512, the C1 rules, the claims table, the 10 TB cap. Hybrid cost on the campaign card: about
**8.0-9.0 TB** expected (v2: 8.3-11.4; my design: 9.9), about 16-18 h.

## 14. Summary for the machine reader

Design (10 lines): one card, the Corsair test card; S0 facts + one owner-present restart; S1 camera-free (100 GB write floor, 120 GB
paced directory probe, smoke test); S2 screening per mode inside the record's bracket with the confirmation take as the 5-min tier,
meter takes for storage-limited arms, levers as ABBA pairs only where the outcome is open (Log, WebUI off), single probes for TDN-on
unlogged and phase lock; S4 one unsplit 15-min take per carried arm, ordered to end near full; S5 one 30-min take per arm, unsplit first
for HDR arms, split first for SDR12 arms at >= 42 fps (single-folder create = 100 % of the period); S6 the split member as the repeat;
S7 a short per-card check; status file between takes, SQLite on the SD card, pre-registered rules and a claims table; ~9.9 TB, ~19 h.
Mine beats v2 on: the SDR12 directory arithmetic and split-first (saves ~1 TB, removes two predicted failures), the 5-min tier folded
into the confirmation take (~0.4 TB, 1 h), the camera-free paced directory probe, the crops' ceiling search, the deliberate fill order,
a cheaper per-card check. v2 beats mine on: the build list (A15 forced-drop check, the helper, Core prerequisites), the audio watch,
currency (cold delete measured, clip-split verified), the write-pattern matrix, Part B's 30-min fidelity, pre-roll off, the stricter
"one lever variant per mode" wear rule. Hybrid: v2 plus the seven changes of section 13, ~8-9 TB.
