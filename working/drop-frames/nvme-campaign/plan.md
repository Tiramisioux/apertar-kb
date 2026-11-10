# NVMe 4K campaign on the Corsair cards: the plan (2026-11-08, revised 2026-11-10)

Written in a cloud session for Patrik after a research pass over the KB (the drop-frames campaign, the SSD long-take run and its
re-analysis, the dng-chain feasibility work, the exFAT directory probe, the runner `longtakes.py`) and a critique round (statistics,
rig engineering, operator and wear, a red team on the numbers, an independent challenger design; `nvme-campaign/critique/`). It builds on
three pages that stay authoritative for their parts and are not repeated here: `nvme-4k-recipe-plan.md` (2026-11-07: the capture-side
ruling-out rules and the runner extensions), `storage-slowdown-plan.md` (branch `claude/practical-johnson-he481b`, 2026-11-08: the
storage mechanisms M1-M11 and the buffer-as-a-meter method) and `longtakes-test-structure.md` (how the runner ran the SSD campaign).
Labels as in the KB: **measured** / **derived** / **probable** / **unconfirmed**; **web** for internet facts (URLs in
`nvme-campaign/research/R8-online-sources.md`). Numbers are decimal GB.
Names: Core = the camera recorder (`cinemate-port`); TDN = temporal denoise in the ISP; FE = libcamera's front end (its Config queue);
pSLC = the drive's SLC write cache; CCMP = Core's companding expansion; MLV = Core's Magic Lantern video format; T7 = the Samsung SSD of
the 2026-11-07/08 long-take run and Kingston = the KC3000 test card (both history, not campaign media); the record = the KB's take ledger
(`research/R1-take-ledger.md`). Research pages are cited as R1-take-ledger, R2-lever-inventory etc.; R1-R15 are the requirements of §1.

## 0. In one paragraph

Everything runs on the media Patrik shoots with: Corsair MP600 Mini 1 TB cards in CFexpress Type B adapters in the camera's hat, about
990 GB usable each. One card is the campaign card (the record's test card, serial `A936B442006AC2`, if Patrik agrees: its drive facts
and SMART history are in the KB); the other card(s) get a short check at the end. A detached runner on the Pi (`longtakes.py`,
extended by the build list) records every take, fills a database and rewrites a status page between takes; the Opus thread plans,
installs with Patrik, reads the status and decides between tiers (a `GO-<stage>` sentinel file the runner waits for before each long tier). The ladder is 3 -> 5 -> 15 -> 30 minutes with stop-on-drop at every
tier, two concordant takes per screening decision (a deviation from one-drop-out, to confirm: §11.8), capture-side levers screened at 3 minutes, the folder split tested at 30 minutes (unsplit first below
the 60 % create share, split first above it), no cool-down, no fill rule (only "does it fit"), clips deleted only when the next take needs the space. Audio is
watched on every take after the "ALSA capture: Broken pipe" stop of 2026-11-08. Budget: 10 TB on the campaign card, about 1.7 % of its
600 TBW rating (web); with the ~30-31 TB the card already carries (29.0 TB read on 2026-11-04, plus the unrecorded evening 4 and the 11-08 verification's ~0.33 TB; the erased 11-07 run was on the Kingston; derived), about 570 full-card shooting days remain by that rating now, ~560 after the campaign's 10 TB (the drive's
own SMART estimate is more generous). The campaign writes those ~10 TB through the exFAT volume Patrik shoots on, on a rig with 1,535
unsafe shutdowns and three controller deaths on record: that is the one irreversible risk the campaign carries, and running it on the
shooting card is his decision (§11.1).

## Revision 2026-11-10 (after SSD nights 1-2): what changes; this section wins where it conflicts with the rest

Evidence: `ssd-campaign/README.md` (Night 1 and Night 2 results, "the four dropped frames", "Frame budget vs exFAT folder size").

1. **Split is the default, flat is the control** (User's decision 2026-11-09: `frames_per_folder` 5000 on the camera). Every scored take runs
   split at 5000, as Patrik shoots. On the T7 the split was the difference between a clean 30-min take and a safety stop near minute 29
   (2kSDR12 32 fps: flat 2 of 3 stopped, split 4 of 4 clean, Core CPU flat 51-58 % instead of climbing to 125-131 %; confirmed). The old
   split-first / unsplit-first rule (§3, §6 S5, §11.10) is replaced: R13 on the NVMe is answered by **one flat control per primary mode at
   30 min in S6**, at the mode's winning fps, run after its split take (a flat drop = "split needed on the card too"; flat clean = "split not
   needed at that fps on this card, n = 1"). Prognosis from the formula below: flat holds at 25-30 fps (walk share 36-51 % at 30 min) but the
   T7's Clear HDR takes failed at 35-40 %, so the HDR16 flat control is the informative one.
2. **Folder-budget formula** (in §3's place for the directory part): budget T = 1000/fps ms; create cost W(n) = 0.32 us x n; flat share at
   time t s(t) = 0.32 us x fps^2 x t; flat lasts t* = 0.6 / (0.32 us x fps^2) = 1.9e6/fps^2 s (25 fps 50 min, 30 fps 35 min, 33 fps 29 min,
   42 fps 18 min, 50 fps 13 min); a split at 5000 caps the share at 1.6 ms x fps (4-8 %). Any arm >= 33 fps for 30 min needs the split.
3. **Binary**: Pi `clip-split` at `e298d4a` or later (Core restarted on it; `/proc/<core pid>/exe` built after 2026-11-10 03:00). It carries
   the merge worker and its progress, the Standard clip-name preset, and two night-2 fixes: the part folder is made on a writer, not the
   copy worker (night 2's 3 copy-slot drops at the part_008 boundary), and the "frame index jump" log line plus `index_jumps=` in the
   recording stats. S0's status check reads `index_jumps=` in the first smoke take's stats line; the "binary 01f170c" check of S0 is replaced.
4. **A numbering gap is not a dropped picture.** A take whose `missing` (highest number + 1 - files) equals its `index_jumps` with every
   other Core counter 0 and no `drop[capture-gap]` line is recorded as `numbering_gap` (the time-based index skipped a number after a late
   timestamp; no frame was lost): reported per recipe, never an elimination and never a stop. Any other missing frame stays a drop. Night 2
   had one; 11-07 had two (2kHDR12 25 fps).
5. **Part boundaries are watched.** Per take the runner records every drop with its frame number and flags those within 64 frames after a
   multiple of `frames_per_folder` as `boundary`. A boundary drop on the new binary means the fix did not cover it: the arm's result
   stands, and the lead writes it up before the next night.
6. **The merge stays off during the campaign and goes back on at the end of every night** (as night 2: off before each run, on at the end).
   Measured on the T7 (merge test, night 2): 45,001 files merged in 342 s, the UI's time left 4-6 % low throughout; a 54,000-file clip
   (30 min at 30 fps) is predicted at ~8 min. S6's merge-on real-use check stays (merge pauses within ~30 ms of `record_start`, 0 lost
   frames, n = 1 at 1,503 files; repeat it at 45,000).
7. **Restore list** (§7): `frames_per_folder` **5000** and the merge **on** (not 0), the rest as listed.
8. **The Pi is powered off after every night and after the campaign.** A watcher (`poweroff-after-<night>.sh <pid>`, the night-2 pattern:
   follows the night's last process, waits until nothing records and writes are done, restores the list of item 7, then calls Core's
   `power_off_system` over the socket) ends each night. Consequences, accepted: the drop-in and the runtime timer masks do not survive
   the power-off, so Patrik re-arms the drop-in (and the helper re-masks the timers) at the start of every night, not only after an
   unplanned reboot; clips left on the card are deleted after a boot, which is cheap for split clips (cold unlink ~13.6 s x (5,000/10,000)^2
   = 3.4 s per part, ~30 s per 45,000-frame clip) and the fill gate's cold-delete budget applies to flat controls only. No `@reboot`
   crontab line (the safety classifier denied it on 2026-11-09; do not work around it).
9. **Drive recovery between heavy runs**: 10 min idle between runs within a night (night 2's pattern). On the T7 the first takes after
   ~210 GB of probe writes ran at 84-98 MB/s and the drive recovered while idle (probable); S1's drive-state write measures the NVMe's own.
10. **ssh and scripts** (lessons of nights 1-2): every remote start is `ssh -n apertar '( setsid nohup <cmd> </dev/null > <log> 2>&1 & )'`
   (a plain nohup kept the ssh session open); the Pi has no `bc` (use `python3 -I -c`); never `journalctl` or a listing during a take
   (one low-priority journal read between takes is fine); delete clips only through `POST /api/media/delete?kind=folder&id=<name>`.

## 1. The owner's requirements and where each is met

| # | Requirement (2026-11-08) | Where |
| --- | --- | --- |
| R1 | Unsupervised; 4K Clear HDR 16-bit and SDR 12-bit first; the 4K full-frame and crop modes | §4, §6 |
| R2 | Levers: storage tuning, compression, Log, TDN, phase lock, WebUI on/off (+ FE depth 4, clip split) | §5 |
| R3 | Minimize writes; 3 -> 5 -> 15 -> 30 min | §6, §8 |
| R4 | Prognoses per stage; eliminate at the first dropped frame, stop the take | §7, §11.8; **deviation to confirm**: the take stops at its first drop, but at the 3-min tier a cell is eliminated only after a second concordant take (the record's spread at the edge fps makes one take a coin flip); Patrik can revert to "one drop = out" and accept the position-artifact risk |
| R5 | Clear the card only when the next take needs the space; delete all campaign clips at the end | §6 fill gate and end-of-part delete, §7 |
| R6 | No NVMe cool-down; temperature logged, never gated | §7 (temperature and heat de-aliasing), §6 S0 |
| R7 | A robust detached Pi script; the database filled between takes | §9 |
| R8 | Monitoring from ssh between takes: what, why, progress | §9 |
| R9 | Folder split examined | §2 (the probe), §6 S5/S6 |
| R10 | The 75 % rule removed | §3, §6 |
| R11 | Make the best of the card in use (the runner adapts to any size) | §3, §6 fill gate (fit-limited takes) |
| R12 | All tests on the Corsair cards, as in real life; a check on the other card(s) | §6 Part B |
| R13 | Does splitting matter for long recordings | §6 S5/S6, §7 signatures, §11.10; **deviation to confirm**: no split pair at 15 min (S4 is unsplit only, read as the directory meter); the 30-min pair is S5 unsplit / S6 split on different nights in a fixed order, not alternated back to back; the split-first SDR12 arms get no unsplit control unless bought |
| R14 | 30 min drop-free in all 4K modes; executed by an Opus thread in VS Code | §7 claims, §10 |
| R15 | Keep an eye on audio (the Broken-pipe stop) | §5a |

## 2. What the plan rests on (labelled; detail in `nvme-campaign/research/`)

- **The drive is the record's drive.** Every earlier drive fact was measured on a Corsair MP600 Mini 1 TB (serial `A936B442006AC2`, firmware
  ERFM11.1): 733 MB/s direct writes (measured; "<= 5 s" and "in the pSLC cache" are R3's derived reading), 415 MB/s for 10 min by Core (measured); 525 MB/s for 60 s (derived from a 2026-10-28 crop take on an old build and an untrimmed, 77-82 %
  full card); no Core-pattern datum of 600 MB/s or more longer than 5 s exists on this card, so SDR12 at 42 fps and above is unmeasured
  drive territory and the meter take is its instrument; stalls
  for seconds after ~0.9 TB written without a trim, cured by a trim (measured, synthetic, 2026-10-30); Core trims at mount and after deletes
  >= 1 GiB per poll (confirmed; the trigger can miss slow small-file deletes, derived); 34 -> 54 C in 10 min at 415 MB/s, 72 C after 10 min
  of SDR at 410 MB/s (measured); 25.3 TB written at 3 % used on 2026-11-02, 29.0 TB after evening 3 (measured). Its own SMART thresholds: 82.9 C warning, 85 C critical (measured); 72 C was reached twice with 0 drops (measured). Web: pSLC ~50 GB, post-cache
  ~800 MB/s, throttle ~80 C, 0-65 C spec, 600 TBW; two variants share the name (E21T 2023, E27T R2 2024; the CORE Mini is QLC with 250 TBW):
  the test card's firmware ERFM11.1 points at the E27T R2 (probable); Patrik runs `nvme id-ctrl` once in S0 (model, firmware, `sgls`) and types the part number from the label into the session; the runner
  reads `firmware_rev` from sysfs (no helper word for id-ctrl). Whether the record's temperatures were measured with the card in this same
  adapter and slot is asked in §11.1. The CFe-B adapter shell removes convection and adds mass (probable); the record's temperatures were probably measured in this same
  hat slot and shell (the test card has lived there since October), so they stand; the curve per card comes from the long takes.
- **Capture side, 4K Clear HDR 16-bit uncompressed** (recipe.md rows 1-8; R1-take-ledger): 25 fps clean for 10 min in 4 of 7 takes, all with
  TDN on and the WebUI closed; O1 (owner, 10 min, WebUI open, TDN on) lost 1 by Core's count; TDN off removes the back-end bottleneck (37 ->
  6 ms per frame, measured, p = 1/6); FE Config depth 4 removes the single-frame losses at 28 fps (probable, n = 1 + 1); 30 fps lost ~3
  frames in 2 min even so on the EARLIER board (evening 4's t1; the C0 board's one 30-fps datum is a clean 135 s, measured, n = 1, its drive and build unrecorded on its page; a second limit, memory
  bandwidth suspected, unconfirmed; the revision code `c041a0` was read on both boards and cannot tell them apart, so the runner records the
  CPU serial per evening). **No 4K take longer than 602 s exists on the NVMe** (derived from R1-take-ledger; the SSD run's 7-28-min failures and 30-min passes were 2K on the T7, and its 4K takes never exceeded
  the 5-min SDR10 lossless pass), and
  none of the clean 10-min takes ran with TDN off or depth 4.
  The 10-min takes are older builds: on the current code line (`f4a1393` and its split/merge successors) the longest 4K take is the SSD
  run's 5-min 4K SDR10 lossless pass (7,505 frames, on the T7, with audio) and the longest 4K take on the NVMe is 3 min (the 11-08
  verification), so every tier above 5 min is a first for this binary.
- **4K SDR 12-bit**: 33 fps clean for 10 min, lossless and uncompressed (measured); ~42 fps clean once (owner, unscored). Not every 4K
  drop on this drive was a capture gap: the 77-82 %-full and the never-trimmed takes lost to a full write queue (measured), so the
  campaign reads the counter, never assumes the regime. 4K Clear HDR 12-bit:
  no long take on record (measured: the SSD run's 4K HDR12 takes ran at 5.8-12.6 fps into slow buffer_full on the T7; none on the NVMe).
- **Encoders**: HDR16 lossless 17.6-18.5 fps (measured): out above 17 fps; SDR12 lossless 48 fps capacity at 33 fps, 2.8 cores (measured,
  pre-roll): probably CPU-bound near 50 fps. Log on HDR16 = 12.45 MB per frame (measured, one DNG); Log on HDR12 did not shrink files on the
  SSD and Log + lossless made larger files than lossless alone (measured): no HDR16 Log + lossless arm is assumed.
- **The SSD run re-read**: 32 "late" buffer_full failures kept pace for 7-28 min and then filled the buffer within a minute while Core's CPU
  doubled in proportion to the files written; 78 "slow" ones were the write pattern's steady capacity (the candidates are fsync + FLUSH per file and
  per-cluster allocation under the filesystem lock; which of them carries the loss is not measured: probable); the RAM budget varied
  250-1,283 MiB; the trim state was never recorded (the counts measured / derived).
- **The directory walk, measured** (probe, 2026-11-08, on this card): c = 63.3 ns per directory entry; create cost = -0.18 ms + 316.6 ns x
  files (5 entries per frame file): 14.1 ms at 45,000 files (35 % of a 25 fps period), 16.9 ms at 54,000 (51 % at 30 fps), 18.6 ms at
  59,400 (61 % at 33 fps); a merge's rename costs what a create costs at the target's size (verified live: 0.10-0.45 ms per file at 500-1,503 files, 0.72 ms at
  4,503); warm unlink 5 us per file; **the cold-cache unlink is measured** (probe step 4, on this card): linear in the files already deleted, 52.8 ns per
  entry, 13.6 s for 10,000 files; a flat 45,000-frame clip deleted after a boot costs ~4.5 min (derived), a clip split in the campaign's parts of 5,000 ~30 s (parts of 1,000 ~6 s). The probe's pre-registered rule made the knob a prerequisite of the 15- and 30-min stages and the split A/B mandatory; this plan
  deviates knowingly: the 15-min tier runs unsplit only (the walk is 17-25 % of the period there for the HDR arms and ~50 % for SDR12 at 42-44 fps, below the 60 % rule, so unsplit holds and
  the SDR12 15-min take is the first reading of the directory meter near the threshold; the statistics
  critique F4) and the mandatory A/B lives in the 30-min tier and the soak. The SSD
  run's 30-min passes at 45,006-59,412 files in one folder show single folders surviving those counts when the drive pattern has margin.
- **Core on the camera** (fork-log 2026-11-08): `cinemate-port` `ba0658d` since the 13:00 boot, then the two merge-worker fixes `68516f1` and `01f170c` found by the verification: Log, `buffer=ram` with the safety stop,
  trim, pre-roll, the media tune file, `set_preview_tdn`, `set_fps_phase_lock` ({d, d+1}), `set_media_trim`, `[storage] frames_per_folder`
  (0), `tools/flatten_clip.py`, the merge worker (`clip_merge` on by default; `APERTAR_CLIP_MERGE=0` forces off). UI `7ea9afc` reads split
  clips. **The clip-split knob is verified on the Pi** (`nvme-campaign/clip-split-verify.md`, steps 2-9 all pass: split take 1503 = enqueued, flatten, merge on and off, merge pauses 33 ms after `record_start` and the take during the pause lost 0 frames, restart mid-merge keeps the invariant, delete mid-merge clean). One verification take ended with the audio fault of §5a. The verification takes showed no `dropped_gap_estimate` line, as expected: they had no drops, and Core prints that line only when gaps
  occurred (the KB's code reading; the `drop[kind]` lines are rate-limited). Which per-drop lines this binary prints is therefore still to be
  confirmed by S0's forced-drop check before S2; until then the runner's first-drop time comes from the 1 Hz samples.
- **Board**: CM5 Lite C0 (`c041a0`), the board of the SSD run; recorded per session.

## 3. Arithmetic (derived from measured frame sizes)

Frame bytes: HDR16 uncompressed **16.59 MB** (the 2160-row file; measured), HDR16 Log 12 **12.45 MB** (measured, one DNG), SDR12 and HDR12
uncompressed 12.44 MB (derived), SDR10 10.37 MB (derived), SDR12 lossless ~5.98 MB (measured, one scene), crops 3840x2072/2076 ~11.95 MB
and 3840x1608 9.26 MB at 12-bit (derived). Card: 999,960,870,912 B, 10 GB reserve -> ~990 GB usable.

| Arm | MB/s at 25 / 28 / 30 / 33 fps | GB per 3 / 5 / 15 / 30 min (25 fps) | files per 30 min (25 / 30 / 33 fps) | 30 min: fill of an empty card (of the 999.96 GB raw size) | max minutes (25 / 30 fps) |
| --- | --- | --- | --- | --- | --- |
| HDR16 uncompressed | 415 / 465 / 498 / - (30 is the mode max) | 75 / 124 / 373 / 747 | 45,000 / 54,000 / - | 75 % at 25, 84 % at 28, 90 % at 30 | 39.8 / 33.2 |
| HDR16 Log 12 | 311 / 349 / 374 / - | 56 / 93 / 280 / 560 | same | 56 / 63 / 67 % | 53.0 / 44.2 |
| SDR12 and HDR12 uncompressed | 311 / 348 / 373 / 411 | 56 / 93 / 280 / 560 | 45,000 / 54,000 / 59,400 | 56 / 63 / 67 / 74 %; 42 fps 94 % | 53.0 / 44.2 (33 fps 40.2; 42 fps 31.6) |
| SDR12 lossless | 150 / 168 / 179 / 197 (50 fps 299) | 27 / 45 / 135 / 269 | same (50 fps 90,000) | 27-36 %; 50 fps 54 % | 110 / 92 (50 fps 55) |
| SDR10 uncompressed | 259 / 290 / 311 / 342 | 47 / 78 / 233 / 467 | same | 47-62 % | 63.6 / 53.0 |
| Crop 3840x2072 SDR12 | 298 / 334 / 358 / 394 | 54 / 90 / 269 / 537 | same | 54-71 % | 55.3 / 46.1 |

Create cost at the end of a single-folder take (from the measured fit, as a share of the frame period): 15,000 files 4.6 ms; 22,500
6.9 ms (17 % at 25 fps); 45,000 14.1 ms (35 %); 50,400 15.8 ms (44 % at 28 fps); 54,000 16.9 ms (51 % at 30 fps); 59,400 18.6 ms (61 %
at 33 fps); **75,600 files (42 fps) 23.75 ms = 100 % of the 23.8 ms period; 90,000 (50 fps) 28.3 ms = 142 %**. The 25 % line: 32,161 files
at 25 fps, 28,777 at 28, 26,898 at 30, 24,505 at 33, 19,400 at 42.
**Split-first rule** (the challenger's finding): an arm whose 30-min create share is >= 60 % of its period (SDR12 uncompressed or lossless at
>= 33 fps, anything at >= 42 fps; HDR12's mode maximum is 30 fps = 51 %, so no HDR12 arm reaches the rule) runs its 30-min tier SPLIT FIRST,
because the unsplit take is a predicted failure in minute 19-25 from the directory's all-in in-take cost (the SSD run's 99 ns per entry
crosses the 23.8 ms period at ~48,100 files; the walk alone reaches 100 % only at minute 30); its unsplit control is bought only if the owner wants the failure recorded. Arms
below 60 % (HDR16 at 25-30 fps: 35-51 %) run unsplit first as §6 says. A 30-min SDR12 recipe at >= 42 fps therefore requires the split.
Rules that follow: the fill gate is physical (free >= planned x 1.03 + 10 GB); a 30-min HDR16 uncompressed take needs an empty, trimmed card
and ends at 75-90 % full (the near-full condition is tested, not avoided); the runner reads the card's model, serial and size at the start
of every evening, recomputes this table, and after an arm's first take replaces the model's bytes per frame with the measured mean.

## 4. Modes

Primary: 4K Clear HDR 16-bit (3840x2200 raw, 16-bit unpacked), 4K SDR 12-bit (3840x2160), 4K Clear HDR 12-bit (3840x2160, CCMP).
Secondary (the owner's "4K full-frame cropped options"): the full-width crops Core offers at 10/12-bit (3840x2076 or 2072 for 1.85:1,
whichever the installed driver probes; 3840x1608 for 2.39:1; the others 2024, 1920, 1744, 1728, 1632, 1536, 1504 on request). 16-bit
height crops exist (31.9-42.4 fps) but their heights are not in the KB: S0 probes every crop with `list_sensor_modes` and a `set_resolution`
read-back per bit depth, a refused crop is `skipped_unavailable` (never a campaign stop), and the owner chooses per crop between a
confirmation at the winner's fps + 1 and a short ceiling search (down from the full-frame fps + 3, n = 2 at the final fps). Crops are
predicted from the full-frame result (fewer bytes, a lighter back end) and confirmed as every other cell (a 3-min take and its 5-min take, the S2/S3 rule) at the winner's settings
plus 1 fps; their 30-min status is "predicted, untested beyond 5 min" unless a 30-min crop take is bought (one per crop: 540 GB at 25 fps, the 2072/2076 crop 730-970 GB (fit-limited above 44 fps), the 1608 crop 567-750 GB, at the SDR12 winner's fps + 1, i.e. 34-45 fps).

## 5. Levers: fixed state, screened levers, conditional tests

Fixed for every take (the recipe and the owner's real use): `dontneed=sync`, writeback on, `sync_ms` 1000, 8 raw buffers, FE Config depth 4
(the pipeline YAML copy: `/home/pi/Tuning-Files/pipeline/pisp-depth4.yaml`, `num_cfe_config_queue` 4, md5 `88929ca3...` as R2 §2g
records it, the full value read in S0 and written on the pre-registration page, copied by the runner to `/run/apertar-media/pisp-pipeline.yaml`
and selected via `LIBCAMERA_RPI_CONFIG_FILE`: the campaign drop-in's one standing line, armed once per boot by the root helper with a Core
restart and an environ read-back; the audio-ring line `APERTAR_AUDIO_BUFFER_MS` joins it only while that lever is in use; no libcamera
debug log, unlike the evening-4 helper), `buffer=ram`
at the record's keys (`buffer_ram_fraction 0.6`, `buffer_ram_floor_mb 512`): on this board that gave 250-1,283 MiB, median 635 (the SSD
run, measured; the 1,424 MiB of 2026-11-01 needed ~3.2 GB available), so expect 0.7-1.3 GB = 1.7-3 s of HDR16 input (derived); the budget is logged
per take and every buffer_full is read in seconds of input; a fixed-MiB Core key (`buffer_ram_mb`, small) is the one change that would
make it constant (build list E), trim on, the pre-roll ON as in real use (it runs once per Core start, not per take; the unscored warm-up follows it), the merge worker OFF
(`set_clip_merge enabled=false` over the socket, read back per take, restored after; one mechanism, not the env variable as well), Core's Mode Ladder (`set_mode_ladder`, read back as `ladder_enabled`; not the campaign's tier ladder) switched off by the runner at session start and restored in its `finally` (the pre-take check refuses to start while `ladder_enabled` is true), TDN off
through `set_preview_tdn` only (not the evening-3 tuning copy as well), peaking + zebra on, the touch UI service
active AND drawing (the CPU time of `apertar-ui-direct` advancing over the last 10 s, read from /proc; a frozen UI is a void: the SIGSTOP
case of 2026-11-01 stayed "active"), audio ON as the owner uses it, the WebUI stand-in client CONNECTED (the owner's requirement; `webui_remote.py` on the Mac under
caffeinate), no libcamera debug log and no tracefs (the campaign runs as real use runs; the 1 Hz sampler is the only instrument), the
card's model and serial checked per evening, the Pi's CPU serial (`/proc/cpuinfo`) recorded per evening (the revision code cannot tell the boards apart), nothing else on the Pi.

| Lever | Values | Stage | Expectation (label) | Takes |
| --- | --- | --- | --- | --- |
| fps | the record's bracket per mode (HDR16 25-30 starting at 28: the C0 board's only 4K HDR16 datum is a clean 135 s at 30 fps, n = 1, so 30 stays in; SDR12 from a meter take 5-10 % above the record's clean 42 fps, i.e. 44-46 fps, then capacity -1 / -2; HDR12 from 30), step 1 | S2 | HDR16: 27-28 clean at 3 min (measured); 30 dropped on the earlier board and ran clean for 135 s on the C0 board (n = 1 each), so 30 is in the walk, not pre-judged | the walk |
| Log | off vs on at HDR16 only (16 -> 12 stored). Not an arm for HDR12: Log does not change HDR12's bytes (the LUT is composed with the CCMP expansion: 2K 3.12 MB with and without Log, measured on the SSD run, n = 11 + 8; at 4K only with-Log takes exist, 12.2-12.9 MB at 0.1 GB resolution, so the 4K equality is derived from the code path, not measured) | S2 (ABBA at the edge fps, plus ONE stop-on-drop 3-min Log take at 30 fps in the HDR16 block: the untried byte-reducing lever against the 30-fps limit, <= 67 GB; carried to S4 only if it beats the pooled 28-fps controls or is the only clean arm at 30) | fewer bytes vs copy-worker CPU; untried on the NVMe beyond 5 s (R1-take-ledger) | 5 |
| WebUI client | on (fixed) vs off | S2 (ABBA) | ~2 % more losses with it open under page-cache pressure (measured, one night, 2026-11-01); O1 clean with it open | 4 |
| TDN | off (fixed); ONE TDN-on 3-min take at 25 fps in the HDR16 block after the walk ("unlogged" = no libcamera debug log and no tracefs, as every campaign take; the 1 Hz sampler and stop-on-drop stay on) | S2 | tests the O1 hypothesis (O1's single loss in 10 min with TDN on came from the debug instrumentation, not from TDN): 0-2 lost supports it, 3-9 inconclusive (TDN stays off, not repeated), >= 10 confirms TDN off for real use | 1 |
| phase lock | off (fixed); at most one 60-s probe of the {d, d+1} fix | S2 | drops + flicker on the old build (measured); no bearing on elimination | 0-1 |
| compression | per arm a runner-taken reading first via the socket command `storage_preroll` (the manual pre-roll; `storage_preroll_auto` is the one at Core start; encoder capacity, ~1 GB); a 3-min walk only for arms whose capacity exceeds the uncompressed edge (SDR12 lossless; HDR16 lossless + Log only if its pre-roll says > 25 fps) | S2 | HDR16 lossless out (17.6-18.5 fps, measured); SDR12 lossless 48 fps capacity (measured) | 2-4 |
| storage knobs as one group | base vs {workers 1, queue 24, sync_ms 2000}; `kernel_tune on` joins the group only if Patrik installs the `apertar-media-tune` helper in S0 (it is not installed, so today the knob does nothing and the group would silently be three knobs) | only if a 4K arm ends in buffer_full | no effect on the SSD (measured) | 2 meter takes |
| frames_per_folder | 0 vs 5,000 (the probe's N: <= 25,000 entries per folder) | S5 (30 min): unsplit first below the 60 % create share, split first above it; S6 soak as the split variant | 35-51 % of the period at the HDR targets, 100-110 % at the SDR12 targets of 42-44 fps (§3; derived from the measured fit) | the pair |
| FE depth | 4 (fixed); optional control block: two 3-min depth-2 takes at 28 fps HDR16 against the walk's pooled depth-4 controls (AABB in two Core processes, not ABBA: depth is a restart lever, a true ABBA would need four restarts), up to 167 GB for the pair if both run clean (41-72 GB per take at the record's drop times), two Core restarts with Patrik present, after the warm-up and a control, never at the start of an evening; depth 6 only if late Config buffers appear at the edge | S2, optional | depth 4 removed the 28-fps losses (probable, n = 1 + 1) | 2 (optional) |
| Core patches of the storage plan (ftruncate, one FLUSH per tick, drain fix, trim trigger) | each A/B'd with the meter | S6, conditional | storage-limited arms only | ~100 GB |

### 5a. Audio: what the campaign watches (R15)

Facts: Core captures through a 100 ms ALSA ring with a 10 ms period (`audio capture: buffer_frames=4800 period_frames=480 requested_ms=100/10`
in every SSD-run take that carried audio, 72 of 182; `APERTAR_AUDIO_BUFFER_MS` 100-4000); the T30 writer thread sits between capture and the raw file, which is fsynced
once a second (code reading); in the SSD run the writer's backlog peaked at 30-2,764 KB per take (up to ~9.6 s of audio at 288 KB/s, derived from 48 kHz x 2 ch x 3 B: the raw-file writes stall for
seconds under DNG pressure on the T7, measured; on this card the two recorded peaks were 9 and 16 KB); the KB's old reading says xruns are handled with `snd_pcm_recover`, yet a 3-min take on 2026-11-08
ended after 32 s with `ALSA capture: Broken pipe` (all frames written, merge off). Cinemate's history treats this class with a real-time
capture thread, a 2-s ring and silence fill on an xrun. Candidate causes: **the part boundary first**: the fault take (C0005 of `clip-split-verify.md`) ran with `frames_per_folder` 200 at 25 fps,
so a part folder was created every 8 s; the stop came at 32 s with 799 frames written (indices 0-798), i.e. within one frame of the part_003/part_004 boundary at index 800
(derived from the page's figures). Whatever the boundary does on the copy side or the sync thread (the new folder's creation and its
fsync under the filesystem lock) is the first thing to read in the diff `f4a1393..01f170c`. Then: a kcompactd proactive-compaction burst
(period ~32.8 s, evening 3's analysis) holding the capture thread past 100 ms; the writer backlog pushing back into capture if its queue
is bounded; a USB device hiccup.
- **Every take records**: the `audio capture` line (format, ring), `audio writer: peak_backlog_kb`, `audio discontinuity` events, `audio sync`
  (trim and pad samples), `audio clock` drift and correction, any ALSA error; `peak_backlog_kb` becomes a column and a trend to watch.
- **Outcome `audio_fault`**: Core logs the stop as `recording failure: fault=write_error ... ALSA capture: Broken pipe` (clip-split-verify.md), so the runner reads `ALSA capture` in the failure line, not the fault word, and assigns `audio_fault` before the walk decides anything
  (a fault never steps the arm's fps down). A take that Core ends on an audio error is its own result: not a video drop, never eliminating an arm alone;
  repeated once; the journal window, the vmstat compaction counters and the kernel's usb lines at that second are kept with it.
- **Rate so far**: 1 audio fault in 9 takes on the clip-split build against 0 in the 72 SSD-run takes that actually carried audio (110 of
  its 182 takes recorded none, and the runner never flagged it): suggestive, not significant. The runner therefore also checks that the
  `audio capture` line exists in every take's window (`audio_missing` otherwise, a void for a real-use take) and reads the `audio sync`
  trim/pad samples per take, because audio can under-deliver silently with no xrun at all (Cinemate's lesson 6ccfabd; Core's
  `measured_drift_ppm` is a whole-take ratio that would hide it).
- **The Core fix is required before the long tiers** (S4-S6, Part B) if the desk read shows an xrun ends a take: a real shoot with audio
  must not lose a take to a 100 ms gap. S2 may
  run at the 100 ms ring to measure the fault rate; if the fix is not in by night 2, the long tiers run with `APERTAR_AUDIO_BUFFER_MS=1000`
  as a recorded deviation (a second drop-in line: Patrik runs the interactive helper's `arm 1000` and the Core restart before night 2; the
  runner reads it back from Core's environ, else "WAITING: re-arm"). Two audio faults on one arm = the arm is "out with audio" (reported apart from video eliminations); a faulted
  long take is not repeated automatically.
- **Desk task first**: the Opus thread records the frame index at the fault against the part boundaries (799 files written = indices 0-798, within one frame of the part_003/part_004 boundary at index 800 with N = 200, i.e. 32.0 s: a live candidate, not an exact hit), then pulls that take's journal window (the error line, the stop reason, `peak_backlog_kb`) and reads
  `AudioRecordingSession.cpp` / `TimestampedAudioCapture.cpp` at `01f170c` (the audio files are unchanged since `ba0658d`): if an xrun ends a take today, the Core fix (recover, pad the gap
  with silence, log an `audio discontinuity`, continue) comes before the long tiers, as the previous bullet says (S2 may run without it to
  measure the fault rate), because a real shoot must not lose a take to a 100 ms gap.
- **Levers if it recurs**, in order: `APERTAR_AUDIO_BUFFER_MS` 1000-2000 (no code); `vm.compaction_proactiveness=0` through the helper
  (`compact0` / `compact-restore` exist); the Core fix above. S0 checks once which USB controller the microphone shares.

## 6. Stages

S0-S6 are **Part A** (the campaign card); "the end of each part" below means the end of Part A and the end of each Part B card.

**S0 Preflight** (desk + Pi, Patrik present for sudo; ~2 h): **Patrik's footage is offloaded from the campaign card first** (the
card is his shooting medium; the runner deletes only folders in its database and treats any other folder on the card as "WAITING:
foreign folder" until Patrik moves it, never as something to delete);
`fsck.exfat -n` on the card (the 2026-11-08 mount reported "Volume was not properly unmounted"; the record holds 1,535 unsafe shutdowns
and three controller deaths) and again after any unclean shutdown (whether `fsck.exfat -n` runs on a mounted volume is unconfirmed: S0 records it; if it refuses, the resume guard's
fsck condition becomes Patrik's unmount-and-check and nothing resumes unattended until he has done it); the systemd timers that could run during a take masked for the
campaign (`fstrim.timer`, `apt-daily*`, `man-db`, `logrotate`; the helper masks them with `systemctl mask --runtime`, which a reboot clears, and
unmasks them at the end); status check (binary `01f170c` or later; `get_state` shows `frames_per_folder`,
`clip_merge_enabled`, `cdng_log`, `buffer_setting`, `recording_dropped_frames`; the mounted card's model, serial, size and part number;
helpers; cmdline; media tune file; ladder); the crop probe (`list_sensor_modes` and one `set_resolution` read-back per planned crop and
bit depth; the raw heights go into the runner's MODES table, H17); the tuning set back to automatic with Patrik if a manual tuning file is
active (the runner reads `tuning_file` back per take); the ladder switched off and read back; `audio-usb` once (which xHCI the microphone
shares); the Mac stand-in's resilience (Mac on Ethernet, `ServerAliveInterval` set, the Mac's network pulled for 60 s and the stand-in
seen to reconnect); the clip-split verification is on record (`clip-split-verify.md`): read it, do not repeat it; instead one forced-drop check (HDR16 at 30 fps with TDN on and the WebUI client open, the record's reliable dropper, run to the first drop with a 60 GB cap; no drop within the cap = the parser stays untested, S2 runs on the 1 Hz samples alone, recorded) of which journal lines this binary prints per drop (`drop[kind]`, `recording stats`, `recording failure`) so the runner's classification is tested before S2 (the KB says the gap line prints only when gaps occurred); the audio-fault forensics of §5a; the campaign root
helper and its exact-command sudoers installed by Patrik; the campaign drop-in armed (the FE depth 4 YAML line only; the YAML copied to `/run/apertar-media/` by the runner at start, as pi);
the merge switched off over the socket; the pre-roll stays ON as in real use (it runs at Core start,
not per take; the warm-up take follows it);
the power check (`vcgencmd get_throttled`, `pmic_read_adc`, the kernel log for under-voltage); `sudo nvme id-ctrl /dev/nvme0` by Patrik
(model, firmware, `sgls`) and the label's part number into the H6 session field; smart-log baseline (data units written,
percentage used, temperature); `fstrim`; the probe's step 4 is done (cold delete measured); the runner's
smoke test (`--max-seconds 20 --only 1`) proving `buffer_used` at 1 Hz. Writes: ~20-80 GB (the forced-drop check at 30 fps HDR16 is up to
2 min = 60 GB).

**S1 Camera-free probes** (~1 h, ~135 GB on the evening; ~180 GB with the night-end drive-state write): `storage_facts.sh`; one direct write of 60 GB with a 1 Hz bandwidth log (the runner's S1 stage, H24: a `dd oflag=direct bs=16M status=progress` child of one
file, its progress and the hwmon/smart temperature sampled at 1 Hz into the database; NOT `exfat_write_probe.py`, which writes many small
files; Core idle, not stopped: stopping it needs sudo; trimmed card): on the Pi's Gen 3 x1 link (~760 MB/s) both the
pSLC rate and the post-cache floor of this card (~800 MB/s, web) sit above the link, so no knee is expected; the probe confirms the
link-limited rate and starts the temperature record of the card inside its CFe-B shell (the real thermal curve comes from the long
takes, with smart-log's thermal counters read between takes); the write-pattern matrix at 4K size (`exfat_write_probe.py`: default, workers 1, prealloc, fsync none, direct, subdir 5000; ~30 GB);
a 60-s full-speed write after the trim, and the same write once more at the END of night 2 (S4/S5, the first long night), on the card as the last take
left it (no delete for it; if less than 60 GB is free the write is skipped and recorded; never between takes; the same H24 stage, started
by the lead over ssh): the drive-state comparison. Optional (owner's call,
~150 GB, 1 h): the paced small-file probe (`exfat_write_probe.py`, 1 MB files at 42 files/s for 30 min, flat vs `--subdir 5000`; the
25 files/s pair is predicted to pass at a 35 % share and is not bought; all four runs would be ~240 GB and 2 h), which shows the directory
effect at the real create rate without the camera and would make the SDR12 unsplit control skippable. Every S1 file is a database
deletable the runner removes itself at the end of S1 (its own probe files, not clips: `os.unlink` of database-keyed paths, the one
exception to the rm rule; the drive-state file right after it runs).

**S2 Screening at 3 min** (one night, unsupervised; ~2.2 TB), per mode (HDR16, SDR12, HDR12, then the two crops): an unscored 60-s warm-up
after every Core restart or mode switch; the fps walk inside the record's bracket, step 1, two concordant takes per decision (2 drops = out; a 3-min clean
take is confirmed by its 5-min take in S3 rather than by a second 3-min take; 1-1 = a third 3-min take decides, which for a single late frame is the repeat of §7); the limiter per failure (capture gap / buffer_full / drive event / audio_fault);
controls at the start and end of each mode block at the edge fps; the lever variants paired ABBA at the edge fps, both in the HDR16 block only (Log, 4 takes; WebUI off, 4 takes; §5); one stop-on-drop
3-min Log take at 30 fps in the HDR16 block (§5); the single TDN-on take at 25 fps; the phase-lock probe if Patrik buys it (§11.4); the compression arms via the pre-roll reading first. Output per mode, on `nvme-campaign/prognosis-S2.md`: the clean 3-min
fps, the limiter, the lever verdicts, the prognosis table (§7).

**S3 Confirmation at 5 min** (inside S2's mode block, right after a cell's first clean 3-min take; ~0.7 TB in all, the two crops included): the 5-min take IS
the second concordant take of that cell (the owner's tier, the challenger's economy): 3-min clean + 5-min clean = "clean at 3 and 5 min",
the cell is carried; a 5-min drop = "1 clean, 1 drop": a third 3-min take decides (a drop = the cell is out at that fps and above) and the runner-up fps gets
its own 5-min take; if the third take is clean the cell gets a second 5-min take: clean = carried, and it is the mode's best arm for S4;
drop = out, and the runner-up with its clean 5-min take is the best arm.

**S4 15 min** (~1.5 h, ~1.25 TB): one UNSPLIT take per mode of the best arm, ordered HDR16 first, then the heaviest SDR12 arm, then HDR12, so
that the second take starts on the card the first one filled (no delete between them while they fit: HDR16 at 28 fps 418 GB + SDR12 at
33 fps 370 GB ends near 80 % full, at 42 fps 470 GB near 90 %, at 44 fps 492 GB near 92 %, on a trimmed card; the gate passes at every step of that order and
deletes before the third take in either case; fill as a deliberate covariate); Core's CPU slope and the buffer curve are read as the directory
meter; the runner-up only if the best drops EARLY (the stepped-down cell repeats the 15-min tier; a late drop follows §7's long-tier rule). The survival table per cell from
status.md goes to Patrik with each GO decision (S5, S6, Part B).

**S5 30 min** (~2 h, ~2.4 TB): per mode; the gate empties the card only when the take does not fit (the HDR16 take needs the whole
card; an HDR12 take at 672 GB or a lossless SDR12 take may follow on a partly filled card); the card ends 56-94 % full. Arms below the 60 % create share run
UNSPLIT FIRST; the split member (frames_per_folder 5,000) runs in S5 only if the unsplit take drops after ~minute 10 with the directory
signature (§7), otherwise it is the soak of S6. Arms at or above the 60 % share (§3) run SPLIT FIRST; their unsplit control is the
owner's option. MLV: one diagnostic 30-min take per mode, in S6 or later once both variants of the mode have run, only if both dropped late (owner's call).

**S6 Soak and conditional work** (~2 h, ~2.4 TB): the final recipe per mode once more at 30 min as the SPLIT variant where the unsplit take
passed (the split-first SDR12 arms repeat their split take: their "2 of 2", in the budget; this is the A/B in the conservative order at no
extra bytes, heat and process age working against the split); optionally one real-use check with the merge worker ON (H25: the one arm for which the runner accepts `clip_merge_enabled` true): a
split clip of >= 45,000 files (an S5/S6 split take's folder, left unmerged), the merge started with `set_clip_merge enabled=true`, and a
3-min take of the HDR16 winner (by default) at its edge fps started 2 s after the merge begins; recorded: the merge's pause, the take's drops, while the worker
merges it (the verification measured the pause at 33 ms and 0 lost frames once, n = 1; this repeats it at the campaign's settings); the storage plan's Core patches
only where S1/S5 showed a storage limit at 4K; a 30-min crop take if the owner buys it.

**Part B, the other Corsair card(s)** (one evening per card; Patrik powers the Pi off through the helper's `poweroff` before the swap, never pulls a mounted card, and the
runner records the swap boot): Patrik's footage offloaded; part number (a QLC
CORE Mini is refused), serial and size recorded; `fsck.exfat -n`; the trim at mount seen in the journal; after the swap boot Patrik re-arms the drop-in (`arm`, Core restart, environ
read-back) and the helper re-masks the timers before the runner starts; the adapter noted per card; the runner's
card detection recomputes §3; by default the 60-GB knee probe, one 30-min take of the winning HDR16 arm (the question that matters per card) and one 15-min take of
the heaviest SDR12 arm (~1.4 TB and ~2 h per card); the other modes' 30-min takes as Patrik's option (0.67-0.94 TB each: HDR12 672 GB, SDR12 739-941 GB at 33-42 fps); labelled
"n = 1 per card". Cards of the same model and firmware should behave alike; trim state, fill history and the adapter's thermal contact differ per
card, which is what this check sees. ~1.4 TB per card by default.

**Fill gate (every stage)**: free >= planned x 1.03 + 10 GB, else delete the OLDEST campaign clips (from the database, keyed by card serial, clip name, mtime
and take id, since clip names repeat after every format; never the owner's folders) through Core's media-delete route (`POST /api/media/delete` by exact name: it pauses a running merge, deletes and trims in
~0.5 s, measured in the clip-split verification), never by `rm` and with no `rmtree` fallback (a failed delete = "WAITING: delete failed", Patrik decides); before each delete the runner
re-stats the folder and refuses unless its mtime and frame count match the database record (a mismatch = "WAITING: foreign folder");
re-read df. Clips are deleted in the boot
that wrote them (5 us per file); a delete after a reboot is budgeted by file count, 13.6 s x (files / 10,000)^2 (measured slope, derived total: 4.5 min at
45,000 files, 6.5 min at 54,000, 13 min at 75,600), and never started within that budget plus 10 min of a planned take. A 30-min take that fails the gate even on an empty card (SDR12 uncompressed at >= 43 fps plans 963-985 GB and
needs 1,002-1,025 GB with the margin) is shortened to (free - 10 GB) / (1.03 x rate) and recorded as "fit-limited"; the margin is never waived. At the end of each
part every campaign clip is deleted and one `fstrim` runs.

## 7. Rules, pre-registered before the first take

The pre-registration page `nvme-campaign/preregistration.md` is written before the first scored take from the runner's `--plan-only`
output (H21) plus the die rolls: a d6; one roll per ABBA pair set decides whether its first member is the baseline or the lever (odd = baseline
first); one roll for S5, one for S6 and one per Part B card decides that stage's mode order as the (roll - 1) mod 6 -th permutation of
(HDR16, SDR12, HDR12) in lexicographic order (S4 keeps its fixed fill order; when the roll puts HDR16 later in S5 the gate empties the
card before it); rolls and mapping are written on the page.
Terms: arm = mode x encoding and lever state; cell = arm x fps; variant = the split or unsplit form of a cell. Edge fps = the walk's
start fps per mode (HDR16 28, HDR12 30, SDR12 the meter's capacity - 1), fixed for the block's controls and ABBA pairs. An elimination
applies to the cell and to the arm's higher fps (two concordant drops at 3 min, one drop at 15 or 30 min).

- **A take ends** at its first dropped frame (any Core counter), at Core's safety stop (`buffer_full`, a result), at an audio fault
  (`audio_fault`, a result of its own), at the tier length, or at the capacity guard (6 GiB free: `pass_drive_full`). Recorded: time to the
  first drop (read from the 1 Hz samples of `recording_dropped_frames`, not from journal lines this binary may not print), the limiter
  (from the stats line and the buffer flags), the file count at the stop, the buffer level and Core CPU series, the device's write latency series, the csi2 error counters before and after the take, the audio lines,
  temperatures, fill.
- **Decisions need two concordant takes** at the screening tier (a deviation from "one drop = out", see R4); a confirmation take costs its time
  to the drop, which for the single-frame losses of the record came in minute 2-3, i.e. up to a full 3-min take (25-90 GB at HDR16, 84 GB at the 28 fps start).
  A single late frame is repeated once (this repeat is the third take of the 1-1 rule in §6): reproduced = the arm is out for the goal
  whatever the mechanism; not reproduced = both recorded, the arm carried.
- **Elimination reasoning**: under every known mechanism the hazard grows within a take (files, fill, heat, process age), so a drop at t < L
  puts the arm out at L and above; a clean take of n frames bounds the loss rate only at 3/n (95 %), so a clean 3-min take says "not
  hopeless", never "will hold 30 min".
- **Lever verdicts**: "better" = beats every pooled control at the edge fps AND matches the pre-registered direction AND replicates (ABBA);
  "worse" = drops before every control; otherwise "not shown (n = 1 pair)", not terminal, but the lever does not go to the long tiers; at
  most one lever variant per mode goes forward (best + runner-up); a lever is tested only against the limit it can act on (capture levers
  against capture gaps, storage levers against buffer_full; Log in both regimes).
- **No fitted log(T) prognosis** on the capture side; the next fps comes from the failing take's mechanism (a steady back-end deficit gives
  the capacity; rare single frames mean step 1 fps with two concordant takes). The prognosis per cell is a survival table: clean exposure
  (frames, pooled across tiers; pooling assumes a constant hazard, which the growing costs deny, so the pooled bound is optimistic: the rate under 30-min conditions
  can be higher), the 95 % rate
  bound (3/n), the losses that bound allows in a 30-min take, the model expectation with its
  unmeasured terms named.
- **Buffer_full** is reported as seconds of input absorbed (budget / rate), never raw seconds; the budget is logged per take.
- **Meter takes** (storage-limited arms only): fps from the budget (5-10 % overshoot; the window is ~5-50 s across the record's budgets of 250-1,283 MiB, 12-24 s at the median 635 MiB,
  so the runner computes it from the logged budget before each meter take and prefers the 5 % overshoot; 50 fps only if 46 does not fill
  the buffer), the integral identity (fps minus drain summed
  = final buffer level) and the device cross-check part of the record; capacity reported with its window and spread.
- **Long tiers**: after an EARLY drop (before minute 10, capture gaps, no time-growing signature) in S4 or S5 the arm steps down 1 fps
  and the stepped-down cell REPEATS that tier (S4's runner-up); a 30-min take goes only to a cell that passed 15 min. After a LATE S4 drop
  (after minute 10) with signature (a) the fps stays and the SPLIT cell repeats S4 at that fps, then enters S5 split first; its unsplit
  30-min control is the owner's option. After a late S5 drop the split rule of §6 S5 applies (the split member runs in S5 on signature (a),
  otherwise in S6). A late drop with another signature keeps the fps and the attribution, and the arm follows §6 S5's order.
- **Split verdict**: a late drop is attributed by pre-registered signatures, read in this order: (a) Core's CPU slope (a least-squares fit over the take's second half, in ns per directory entry)
  whose 95 % interval overlaps 63-133 ns (the probe's 63.3 ns, the walk alone, is the floor; the SSD run's 17 long takes gave 77-133 ns
  all-in, median 99) + the buffer rising only in the last 5 min (buffer slope > 50 MiB/min there, < 10 MiB/min before) + flat device
  latency (ticks per write in the last third within 15 % of the first third) -> directory; ticks per write in the last third > 1.3 x the
  first third, tracking fill -> drive state; temperature and ticks per write correlated over 1-min bins (r > 0.7) -> heat; dirty +
  writeback KB in the last third > 2 x the first third -> page cache; none -> capture side. These thresholds are pre-registered choices,
  not measurements, and stand on the pre-registration page. Four readings of the pair: unsplit drops late with signature (a) and split
  holds -> *consistent with* the directory mattering at that length (effect = the time difference and the CPU slope; one pair cannot
  prove it, the strong statement is the probe's c plus the in-take slope); both hold -> no effect seen at that length; both drop at
  similar times -> not the directory; split drops and unsplit holds -> recorded with its heat and age confound, no claim. Split second
  is the conservative order. These four readings apply to the arms that run unsplit first (below the 60 % share). For the split-first arms
  (SDR12 at >= 33 fps) the unsplit control, if bought, runs second, hot and older, so "unsplit drops late, split held" is there a check of
  the directory arithmetic's prediction, not evidence on its own; the attribution signatures still apply to its drop.
- **Position and drift**: a 60-s unscored warm-up after every Core restart, reboot and mode switch; a lever pair never starts a block; `takes_since_restart`, `uptime_s`,
  MemFree, the buddyinfo order-8 count on every record, `storage_preroll_last` (the pre-roll's result) once per Core restart; if a block's end control differs from its start control by more than the pooled
  spread (the min-max range of time-to-first-drop among the pooled controls at that fps OTHER than the block's own pair: the walk's
  concordant takes and other blocks' controls; fewer than two of them = 20 % of the tier length; clean/clean = no drift), the block's lever
  verdicts are flagged "drift".
- **Void** (decided from the checks before any analysis): the mode line differs from the request; `fps_speed_ramp` true; a client lost
  mid-take; a build (`pgrep` make/cmake/ninja) or another pty login session (`who`) active, the stand-in's non-pty `tail -F web_flag`
  ssh whitelisted by name; the card serial wrong; the FE YAML's md5 wrong; `clip_merge` on when it should be off;
  `frames_per_folder` not as the arm says; Core's PID changed under the runner; the card not mounted read-write; any read-back of the
  fixed state wrong (the environ line, `tuning_file`, `preview_tdn`, `storage_preroll_auto`, `ladder_enabled`, the UI drawing); a take
  without an `audio capture` line (`audio_missing`). The runner repeats a void once; a second void in one night, the repeat included, stops the night.
- **WAITING** (the runner holds, retries every 2 min, and ends the night cleanly after 30 min): a missing client BEFORE a take (the Mac
  stand-in); a folder on the card that is not in the database; the drop-in absent ("WAITING: re-arm", no timeout: Patrik must act). A
  `GO-<stage>` wait (the files `~/longtakes/<run>/GO-S4`, `GO-S5`, `GO-S6`, `GO-PARTB`) longer than 8 h ends the night cleanly; a GO file may be placed in advance
  only with its pass condition as its one line: `unconditional`, `if all_passed <stage>` or `if passed <mode> <stage>`; an unparseable or false
  condition keeps the runner WAITING and writes why, never a GO; the condition is echoed on the status page.
- **Stop the night**: `critical_warning` != 0, a kernel `nvme` / `pcie` / exFAT error, Core `error`, `media_alive` false, a runner crash, a
  second void, an under-voltage event, a second audio fault in one night (whatever the arms; two on one arm also put the arm "out with
  audio"), the write budget reached, and a kernel at or above 6.18 (`uname -r`) without `nvme.sgl_threshold=0` in
  /proc/cmdline (the 6.18.y NVMe silent-corruption bug, web: the runner refuses to start on it and a running night stops). Restore, write the status, leave the Pi on, Patrik decides. A Pi reset ends the night: the `/run` drop-in (the FE depth 4 line) is gone with it,
  and the merge is probably on again (switched off over the socket; whether that survives a Core restart is unconfirmed, so the runner
  re-sends `set_clip_merge enabled=false` after any Core restart and reads it back), so the runner resumes only after the helper's status shows the drop-in re-armed, `fsck.exfat -n` clean and the last status
  clean, and writes
  "WAITING: re-arm" to the status until then (mechanism: a resume sentinel plus an `@reboot` line for pi that starts the runner once in
  WAITING mode; it reads `get_throttled` bits 16-19 for the under-voltage history of the boot).
- **Runner liveness**: the runner writes a heartbeat file (`~/longtakes/<run>/heartbeat`, the epoch second) every 60 s, and an `ACTIVE` marker it creates at start and removes in `finally`; an
  independent watcher (`longtakes_watch.py`, relaunched by an every-minute crontab line while `ACTIVE` exists) reads only the heartbeat
  file, opens Core's socket only once the heartbeat is older than 180 s while `ACTIVE` exists and the status names a campaign take in
  progress, then sends `record_stop` and writes the status; it exits when `ACTIVE` is gone and never touches a clip that is not the
  database's current take, so Patrik's own daytime recording is safe from it. A dead runner therefore cannot leave Core recording until the
  card is full unless runner, watcher and cron die together (the full card is the last backstop: Core checks no free space); the status
  carries a liveness line.
- **Temperature and heat de-aliasing**: logged every second, reported per take (start, end, max), never gated; smart-log (temperature,
  thermal transition counters, critical warning) read through the helper between every take, not only at the evening's ends; the mode
  order is rotated between S5 and S6 and per Part B card (pre-registered) so heat is not aliased with mode; a take that ends with the card above 75 C is flagged
  (the MP600 Mini throttles near 80 C, web; its spec range ends at 65 C; the test card's own SMART thresholds read 82.9 C warning and 85 C
  critical, measured, so 75 C sits below both).
- **Restore list** (read back at the end of every night and after any stop): ladder on, merge on, `frames_per_folder` 5000 (revision 2026-11-10), the storage knobs at their defaults, TDN as the
  owner's default, tuning automatic, the drop-in left armed for the campaign's duration (FE depth 4 in Patrik's daytime use is a named
  deviation; he disarms it at the campaign's end), the timers unmasked, `APERTAR_AUDIO_BUFFER_MS` removed, fps / mode / compression / Log and
  the audio format as found at the start, no folder outside the database touched (the end-of-night listing equals the start-of-night listing minus the campaign's own deletes); at the campaign's end also the `@reboot` and watcher
  crontab lines removed, the watcher stopped, the sudoers file and the helper removed by Patrik, all read back.
- **Claims table** (what the campaign can say at the end): one clean 30-min take = "recorded once at these settings; loss rate < 6.7e-5 per
  frame (95 %), up to 3 losses per 30 min still compatible"; S5 + S6 clean = "1 unsplit + 1 split clean at these settings" (two takes of
  different variants, not 2 of 2 of one recipe; the pooled exposure bound < 3.3e-5 applies only if the variants are read as one arm, and
  the claim says so); a bought second take of the same variant = "2 of 2". Every tier above 5 min is a first for this code line (§2), and the claim says so; every recipe is reported with its audio fault count
  per hour of recording. Every claim carries the campaign's fixed state and its named
  deviations from real use: the merge worker off, the Mac stand-in instead of a browser, the ladder off, FE depth 4, no debug log. Never "30 min drop-free in all 4K modes" as a
  property. Crops: "predicted, untested beyond 5 min" unless bought. Other cards: "one take per card". Eliminations carry a graded strength:
  a steady deficit within seconds is strong; a single frame at minute 2 of one take is weak until repeated.

## 8. Wear budget (expected / worst, GB, on the campaign card)

| Stage | GB | Notes |
| --- | --- | --- |
| S0 + S1 | 200 / 300 | S0 ~20-80 GB (the forced-drop check), S1 ~180 GB (the 60 GB write, the ~30 GB matrix, two 60-s writes of ~45 GB); the paced probe (~150 GB, the 42 files/s pair) only if bought |
| S2 | 2,200 / 3,000 | mostly short failures; a clean HDR16 take is 75-90 GB (84 GB at 28 fps) |
| S3 | 700 / 900 | one 5-min take per mode and per crop (+ runner-up on a drop) |
| S4 | 1,250 / 1,500 | one 15-min take per mode at the likely edges (HDR16 28 fps 418 GB, SDR12 42 fps 470, HDR12 30 fps 336) |
| S5 | 2,450 / 3,200 | one 30-min take per mode at the likely edges (HDR16 28 fps 836 + SDR12 42 fps 941 + HDR12 30 fps 672 GB); the split member only on a late drop |
| S6 | 2,450 / 3,200 | the soak as the split variant (same figures); patches conditional |
| **Campaign card** | **~9.3 / ~12.1 TB; ~14 TB with MLV and the second takes; ~17 TB with every option (the crops' long takes, the SDR12 unsplit control, the paced probe, the depth-2 block)** | cap 10 TB (~1.7 % of 600 TBW, web), enforced on smart-log `data_units_written` minus the per-card S0 baseline persisted in the database (the file sum and `dev_w_sectors` as cross-checks; S1's probe bytes count); the card held 29.0 TB on 2026-11-04 and ~30-31 TB now (evening 4 unrecorded, plus the 11-08 verification's ~0.33 TB; the erased 11-07 run was on the Kingston; derived), so about 570 shooting days of 1 TB remain by the rating now, ~560 after the campaign |
| Part B, per other card | 1,400 / 3,000 | knee probe + one 30-min HDR16 + one 15-min SDR12 by default; the other 30-min takes on request |

If the 10 TB cap binds, the cuts in this one order: the bought options first (second 30-min takes, the paced probe, the crops' long
takes, Part B's extras beyond its default), then HDR12's S6 split soak (-0.67 TB; HDR12 is the third mode and its soak buys only the
n = 2 datum), then the SDR12 unsplit 30-min control if it was bought (-0.94 TB); S3 is never cut (it is the confirmation take of every
carried cell). A 30-min take is never repeated "to make sure" unless void; the one exception Patrik may buy is a second 30-min take of each mode's
winning arm in the SAME variant (the statistics critic's most valuable extra: "happened once" becomes 2 of 2 and the rate bound halves),
672-941 GB per mode at the S5 edges (HDR12 / HDR16 / SDR12), ~2.4 TB for all three. The Part B check costs ~1.4 TB per card by default.

## 9. Runner, database, monitoring (R7, R8)

`longtakes.py` is the runner. **Its base is the unmerged branch `claude/practical-johnson-he481b` (49c6f46)**, which since 2026-11-08
already carries the fit gate, the kernel-log watchdog, `--budget-gb` with a projection, a lock, new stages and the sampler columns
(buffer level, device counters, dirty pages, trim state) this plan reads; merge it or build on it first (the build list's item H0). Its
`--fix-budget` default (0.9 / 256) must not be used: the plan keeps 0.6 / 512. What the runner does and lacks against this plan:
`nvme-campaign/research/R10-longtakes-runner.md` (anchored to main) and the rig critique's build-list review
(`nvme-campaign/critique/C2-rig-engineering.md` §3). The build list (`nvme-campaign/build-list.md`) is the work before the first scored
take: its section H (the re-anchored list) supersedes the item numbers above it where they conflict.

The campaign invocation, written once (the flags are the build list's H12 and H21, the detach is the owner's standing form; the runner's
default `--stages 1d2rc` is the SSD run's 64-config design and is never used here; stage N is H12's campaign night; the crops are
appended to `--modes` under the names H17 gives them, with `--start-fps <crop>=<SDR12 winner + 1>`):

```bash
setsid nohup python3 -I ~/longtakes/bin/longtakes.py --out ~/longtakes/<run> --stages N \
  --modes 4kHDR16,4kSDR12,4kHDR12 --tiers 180,300,900,1800 --start-fps 4kHDR16=28,4kSDR12=meter,4kHDR12=30 \
  --disk-mbps <S1 result> --web-remote --budget-gb 10000 </dev/null >/run/apertar-media/<run>.out 2>&1 &
setsid nohup python3 -I ~/longtakes/bin/longtakes_watch.py ~/longtakes/<run> </dev/null >/run/apertar-media/<run>-watch.out 2>&1 &
```

Pages the campaign writes in the KB: `nvme-campaign/preregistration.md` (before the first scored take), `nvme-campaign/prognosis-S2.md`
(after S2; `prognosis-S4.md` and `prognosis-S5.md` with each GO decision), `nvme-campaign/findings.md` (the recipe per mode and the
duration-vs-fps table), and entries in `lessons/hardware-log.md` after Patrik confirms each reading.
Between takes the runner appends one record per take to `~/longtakes/<run>/longtakes.db` on the SD card (never /run, never the card) (takes; 1 Hz samples incl. the buffer level, device counters,
dirty pages, trim state, temperatures, Core CPU; drop events; Core counters; the audio lines; journal lines) and rewrites `status.md` /
`status.json` atomically with: "safe to read until HH:MM" on its first line, the decision ahead on its second ("pass -> 29 fps; drop -> confirm at 28") with the
night's expected end, the liveness line (heartbeat age), the current or next take (arm, fps, planned length and GB, expected end), the stage, progress (takes and GB
done and remaining, hours), the survivors and eliminated arms with their reasons, the prognosis table, the fill, the last temperatures,
the smart-log readings, the audio trend, the last 10 rows, and the tail of `decisions.log`. From ssh: `cat ~/longtakes/<run>/status.md`
(one small read; written only between takes; its first line is the "safe to read until HH:MM" of the next take's planned start; the session
check runs at `record_start` only and ignores an idle ssh shell with no child process). Never during a take: `journalctl`, `top`/`htop` or any process listing, `ls /media/RAW`, builds, a second Core client, a second
WebUI.

## 10. Time frame and the Opus thread's job

Build and verify (one to two evenings of desk work, ~1,600 lines; Patrik present ~2 h at the end for S0) -> S0 and S1 (that evening) -> night 1: S2 and S3 -> night 2: S4 and S5 -> night 3:
S6 -> one evening per other card. About 20 hours of Pi time in all; Patrik is needed for the first hour of night 1 (to watch the first fill-gate delete and the first stop-on-drop,
the two code paths the offline tests cannot exercise; the S0 steps belong to the build evening), after any reboot (re-arm), for the card swaps, and for the go/no-go between tiers (asynchronous through the
status file and the `GO-<stage>` sentinel); the drop-in stays armed for the campaign's duration and survives Core restarts within a boot, so later nights need no sudo unless the Pi
rebooted (Patrik disarms it at the campaign's end). Before night 2 Patrik (or the lead with his word) places `GO-S4` (after the S2 prognosis) and `GO-S5` with its pass condition
(`if all_passed S4`) in `~/longtakes/<run>/`, and `GO-S6` before night 3; without them the runner idles before or after S4 and the night
is lost. The handoff is `handoff-nvme-campaign.md`.

## 11. Open points for Patrik

1. Which card is the campaign card (default: the record's `A936B442006AC2`) and the part numbers of all cards (MN / MNR2 / CMN); the
acceptance that ~10 TB go through the exFAT volume you shoot on (§0); whether the record's temperatures were taken with the card in this
same adapter and slot.
2. Which 4K crops (default 1.85:1 and 2.39:1); per crop, confirmation at the winner's fps + 1 (default: a 3-min and a 5-min take) or a
short ceiling search (down from the full-frame fps + 3, n = 2 at the final fps); a 30-min crop take, yes or no.
3. MLV as a diagnostic take (yes/no). 4. The optional depth-2 control block at 28 fps (two Core restarts with you present) and the paced
small-file probe (~150 GB, the 42 files/s pair) and the 60-s phase-lock probe, yes or no. 5. The 10 TB cap, and whether a second 30-min take per winning arm (672-941 GB each, ~2.4 TB for all three) is bought.
6. The campaign sudoers helper in two parts: an unattended alias the detached runner may call (read-only, reversible, or `fstrim`, which is
irreversible on freed blocks and safe only because deletes are database-keyed: `smartlog`, `status`, `fsck-ro`, `audio-usb`, `fstrim`,
`timers-mask` with `--runtime`, `timers-unmask`; NOPASSWD) and an interactive-only helper that refuses without a tty and asks for your
password (not NOPASSWD, so the runner's `sudo -n` fails closed: `arm`/`disarm` the drop-in, `restart-core`, `compact0`/`compact-restore`,
`reboot`, `poweroff`).
7. The audio fix in Core before the long tiers if §5a's desk read shows an xrun ends a take.
8. The R4 deviation: a 3-min cell is eliminated only after two concordant drops (a failing cell costs its time to the drop twice, up to
90 GB at HDR16) rather than at one drop; confirm, or revert to "one drop = out" and accept the position-artifact risk.
9. Part B's default per other card is one 30-min HDR16 take plus one 15-min SDR12 take (~1.4 TB), not your earlier transfer set of one
15-min and one max-length take per mode (~3.7 TB per card for the three modes at the S4/S5 edges, ~3.4 TB with SDR12 at 33 fps):
confirm or revert.
10. The R13 deviation: no split pair at the 15-min tier (S4 is unsplit only and read as the directory meter); the 30-min pair is S5
unsplit / S6 split on different nights in a fixed order (unsplit first below the 60 % share, split first above it), not alternated back
to back; the split-first SDR12 arms get no unsplit control unless you buy it (~0.94 TB): confirm or revert.
