# Research brief for the NVMe 4K campaign (cloud session, 2026-11-08; a dated working note)

> Read with its date: sections 1-10 were written before the readers reported and before the owner's later decisions; sections 11-15
> carry the corrections (the HDR16 file is 16.59 MB, not 16.90; the campaign runs on the Corsair cards, not on a Kingston; the 75 %
> rule is removed; the audio watch). The plan itself is `plan.md`; this file is the trail of how it was derived.


Labels: measured / derived / probable / unconfirmed, as in the KB.

## 1. The drive's size bounds the 30-minute target (derived from measured frame sizes)

Drive: 999,960,870,912 bytes (df -B1, night-2026-11-01.md B0 step 2; "932 GB" in GiB). Owner's rule: stay well below ~75 % full
(hardware-log 2026-10-26: 77-81 % full lost 166-676 frames in 3 min; night-2026-11-01 #78: 18 of 25 losses in the last minute at 97 % full).

| Mode, storage path | MB/frame | fps | MB/s | GB per 30 min | fill of an EMPTY drive |
| --- | --- | --- | --- | --- | --- |
| HDR16 uncompressed (3840x2200x2 B) | 16.90 (measured frame_bytes 16,896,000) | 24 | 406 | 730 | 73 % |
| | | 25 | 422 | 760 | **76 %** |
| | | 28 | 473 | 852 | **85 %** |
| | | 30 | 507 | 912 | **91 %** |
| HDR16 Log 12 (16->12 stored) | 12.45 (measured one DNG, 2026-10-31) | 25 | 311 | 560 | 56 % |
| | | 28 | 349 | 628 | 63 % |
| | | 30 | 374 | 672 | 67 % |
| SDR12 uncompressed (packed 12-bit) | 12.44 (derived) | 25 | 311 | 560 | 56 % |
| | | 30 | 373 | 672 | 67 % |
| | | 33 | 411 | 739 | 74 % |
| | | 42 | 523 | 941 | 94 % |
| SDR12 lossless JPEG (COMP1 in) | ~5.98 (measured, one scene) | 33 | 197 | 355 | 36 % |
| | | 50 | 299 | 538 | 54 % |
| SDR10 uncompressed | 10.37 (derived) | 33 | 342 | 616 | 62 % |

Consequences (derived):
- A single 30-min 4K HDR16 uncompressed take at 25 fps needs the drive EMPTY and still ends at 76 % full; at 28 or 30 fps it does not fit
  under the rule at all (85 %, 91 %). The 30-minute HDR16 target above 25 fps is reachable on this 1 TB drive only with Log 12
  (63-67 %) or a bigger drive. This must be said to the owner before the campaign starts.
- A 15-min HDR16 uncompressed take (380 GB at 25 fps) can follow at most one other 15-min clip left on the drive (2 x 380 = 760 GB = 76 %).
- The "delete only when needed" policy therefore is a fill gate: a take may start only if used_bytes + planned_bytes <= 0.70 x drive
  (0.70 leaves a margin under 75 % for the clip's own metadata); otherwise delete the oldest campaign clips first (Core trims after
  deletes >= 1 GiB; the clean drop-frames branch also trims after deletes made outside Core: fork-log 00f2327).
- File count per 30-min take: 45,000 DNGs at 25 fps, 54,000 at 30 fps, 59,400 at 33 fps, in ONE exFAT folder. The longest measured
  clean folder is 19,857 files (SDR12 33 fps 10 min). The exFAT create scan is O(N) per file (feasibility 2.4, estimated 12-38 ms per
  create at 30,000 files, constant c unmeasured). This is the largest UNMEASURED risk specific to the 30-minute target.

## 2. Wear budget (derived; smart-log 2026-11-02: 25.28 TB written, percentage_used 3 %; +1.34 TB on evening 1, +1.55 TB on evening 3)

- Each HDR16 uncompressed 3-min take = 76 GB; 5 min = 127 GB; 15 min = 380 GB; 30 min = 760 GB.
- Implied endurance from SMART: 25.28 TB / 0.03 = ~840 TB (720-1010 TB for 2.5-3.5 %); rated TBW to confirm online (R8).
- A campaign of ~8-10 TB (the previous campaign's own estimate for five evenings) is ~1-1.5 % of the implied endurance.
  Cost per decision is what matters: a 3-min screening take costs 1/10 of a 30-min take and answers the same yes/no at the fps ceiling,
  but NOT the questions that only length answers (file count, heat, fill, page-cache age). So: screen at 3 min, confirm at 30 min only
  the few survivors, never repeat a 30-min take to "make sure" unless the first was void.
- Wear ledger: `nvme smart-log` data_units_written before and after every evening and per take from /sys/block/nvme0n1/stat
  (sectors written, field 7 of /sys/block/nvme0n1/stat; the 1 Hz logger already reads fields 5 and 8).

## 3. The owner's rules for THIS campaign (2026-11-08)

1. Unsupervised: an Opus session in VS Code on the Mac drives the Pi over ssh through a reviewed root helper (the evening-3/4 pattern).
2. Levers: storage tuning settings, compression modes, Log, TDN, phase lock, WebUI on/off (also: FE Config depth 4, which evening 4 found).
3. Minimize bytes written: 3-min screening first, then 5, 15, 30 min for the survivors; prognoses after each stage.
4. Stop a take at its first dropped frame and eliminate that option/combination (TAKE_STOP_ON_DROP=1 exists since evening 4).
5. Do not clear the drive after every take; clear only when the next take needs the space; at the end delete all campaign clips.
6. **No NVMe cool-down between takes** (owner, 2026-11-08): takes run back to back as in a real shoot; temperature is logged every second
   (take_logger.py `temp nvme_mC`) and reported per take, never gated (NVME_GATE=off, the evening-4 deviation made permanent).
   Stop conditions keep only the drive's own `critical_warning != 0` and the kernel's thermal/controller errors.
7. Target: 30 min without a dropped frame in all modes, this campaign = the 4K modes (full frame 3840x2160/2200 and the 4K crops).

## 4. Fixed state for every take (so results transfer to real use)

Peaking + zebra on, the touch UI drawing, audio meter as the owner uses it, `buffer=ram` (the safety stop as the backstop), DONTNEED=sync
(the build default since adac040 / f5ac28b), writeback on, sync_ms 1000, 8 raw buffers, the ladder OFF for the take and restored after,
the trim on, the pre-roll on, nothing else running on the Pi (no builds, no second session), the test card's serial checked.
Varied by design: compression, Log, TDN, phase lock, WebUI client, FE Config depth, fps, mode.

## 5. Runner architecture (owner, 2026-11-08): a robust script on the Pi, a database filled between takes

- **Everything runs from a detached script on the Pi** (as evening 3/4: `setsid nohup bash ... </dev/null &`, output to
  `/run/apertar-media/<campaign>-<unit>.out`), never from an interactive ssh loop on the Mac. The Mac/VS Code Opus session plans,
  installs (with the owner for sudo), starts the runner, reads the database and decides the next stage; it does not drive takes by hand.
- **Between takes the runner takes its time to collect**: after `record_stop` + settle, before the next take, it appends ONE record
  per take to a persistent database on the SD card (not tmpfs, not /media/RAW), e.g. `~/nvme-campaign/takes.jsonl` + a CSV view,
  with: take id, stage (3/5/15/30), arm (every lever value: mode, fps, compression, log, tdn, phase lock, webui, depth, dontneed,
  writeback, sync_ms, raw_buffers, buffer mode), Core commit/PID/uptime, the `recording clip:` line fields (format, compression,
  media_fs, dontneed, writeback, sync_ms, tune_override), `capture stats` (dropped_gap_estimate), `recording stats` (enqueued,
  dropped_queue_full, dropped_copy_slot, peak_queue, write_failures, syncfs ms), `lossless timing` (estimated_capacity_fps) when
  present, `tuning file` line, `media tune` line, `media: trim` lines in the window, planned vs recorded seconds, time to the first
  drop, frames written (ls count of the clip), bytes written (clip du; nvme stat sectors delta), drive fill before/after, NVMe and
  SoC temperature start/end/max (from the 1 Hz log), SoC throttled flags, MemFree before/after, csi2 counters, the 1 Hz log path,
  the libcamera log cut (if logging on), the BE config dump id, and the verdict (clean / dropped at t / void: reason).
- The previous campaign's pieces to reuse: `take3v3.sh` (one take, 1 Hz log, stop-on-drop, mode set, ladder restore),
  `take_logger.py`, `e3-unit.sh` (unit loop, gates, OFF offsets), `e3-collect.sh` (cut/clips/delete), `takes_from_journal.py`
  (journal parsing), `be_overlap.py` (post-hoc classification), `webui_client.py` (WebUI stand-in on the Mac),
  `b1-arm.sh` / `e4-helper.sh` + exact-command sudoers (root steps).
- New pieces the runner needs: a stage/arm queue file the Mac session writes and the runner consumes in order; a fill gate
  (used + planned <= 70 % of the drive, else delete the oldest campaign clips listed in the database and wait for Core's trim line);
  per-take Log / phase-lock / TDN / compression / fps / mode setting through `core.py` with read-back from `get_state`;
  the collect step above; a wear ledger (nvme smart-log data_units_written via the helper at evening start/end; per take from
  /sys/block/nvme0n1/stat sectors); a stop-the-night rule set (critical_warning != 0, Core error state, a take script that died,
  the card serial wrong, a second void); the end-of-campaign delete of all campaign clips (only the folders in the database).
- Temperature is logged, never gated (no cool-down between takes).

## 6. Monitoring from an ssh session (owner, 2026-11-08): report between takes, never during one

- The runner keeps a **status file** on the SD card (`~/nvme-campaign/status.md`, plus `status.json` for tools), rewritten
  atomically (write to a temp file, `mv`) at every state transition BETWEEN takes: before a take starts (take id, stage, the arm with
  every lever value, why this arm now, planned seconds and GB, expected end time), after the collect step (verdict, lost frames and time
  to the first drop, temperatures, fill, bytes written; the prognosis it drew), at gates (waiting: fill, deleting clip X, Core restart,
  stop condition met). During a take the file does not change; its header says "take N running since HH:MM, planned until HH:MM".
- Contents: progress (stages done / remaining, takes done / planned, GB written so far / estimated remaining, hours elapsed /
  estimated), the queue ahead in order with the reason each item is still in, the eliminated arms with the take that eliminated them,
  the surviving arms per stage, the last 10 database rows, the drive (fill, temperature at the last take's end, smart-log last reading),
  the current Core PID/commit, and the decision log tail (`decisions.log`: timestamped "chose / eliminated / waiting / stopped because").
- Reading it is one small file read: `ssh apertar cat ~/nvme-campaign/status.md` (or `watch -n 60` on the Pi, low cadence). Rules
  for the watcher: no `journalctl`, no `top`, no `ls /media/RAW`, no builds during a take (the 2026-10-31 confound: a read-only
  journal query overlapped a take); the status file and `decisions.log` are the only things to read while a take runs.
- The same status file is what the Mac/VS Code session reads to decide the next stage, and what goes into the KB findings page.

## 7. Changes from the owner (2026-11-08, later messages)

- **The 75 % rule is removed.** Fill is a measured covariate, not a gate. The only fill gate is physical: free_bytes >= planned_bytes x 1.03
  + 10 GB reserve (exFAT metadata, the WAV, the pre-roll). A take that ends near full is wanted: it tests the "nearly full card" condition
  the record left open (2026-10-26: 77-81 % full lost frames on an UNTRIMMED drive; #78: 18 of 25 losses in the last minute at 97 % full,
  before the dirty-limit change; #80 on an empty drive clean; no trimmed-drive, high-fill, 30-min datum exists).
- **A 500 GB card must work too; make the best of whatever card is in.** The runner reads the card (model, serial, size from
  /sys/class/nvme/nvme0/{model,serial} and df -B1 /media/RAW) and derives per arm the longest take that fits:
  max_seconds = (free_bytes - reserve) / bytes_per_second(arm), where bytes_per_second is the model until the arm's first 3-min take has
  measured it (du of the clip / recorded seconds; the measured value replaces the model in the database). The stage ladder per arm is
  3 -> 5 -> 15 -> min(30, fit) minutes. Examples (empty card, 10 GB reserve):

  | Arm | 1 TB card (990 GB usable) | 500 GB card (490 GB usable) |
  | --- | --- | --- |
  | HDR16 uncompressed 25 fps (422 MB/s) | 30 min fits (760 GB, ends 76 % full) | 19 min max |
  | HDR16 uncompressed 28 / 30 fps (473 / 507 MB/s) | 30 min fits (852 / 912 GB, ends 85 / 91 % full) | 17 / 16 min max |
  | HDR16 Log 12 at 25 / 30 fps (311 / 374 MB/s) | 30 min (560 / 672 GB) | 26 / 22 min max |
  | SDR12 uncompressed 25 / 30 / 33 fps (311 / 373 / 411 MB/s) | 30 min (560 / 672 / 739 GB) | 26 / 22 / 20 min max |
  | SDR12 lossless 33 / 50 fps (~197 / ~299 MB/s, one scene) | 30 min (355 / 538 GB) | 30 / 27 min max |
  | HDR16 Log + lossless (size unmeasured, model ~9-12 MB/frame) | 30 min | 30 min probable |

  On a 500 GB card the heavy arms' "fit" stage is their 30-minute stage; the 30-minute result for them comes from the 1 TB card.
- **The recipe is for the 1 TB CFexpress cards.** Core-side levers transfer as settings. Drive-side findings (sustained rate, heat,
  fill behaviour, trim, pSLC) are per card: the plan ends with a transfer set per CFe card: the winning arm per mode, one 15-min take
  and one max-length take, no cool-down, stop-on-drop, the same database. The runner's card detection makes the same scripts run there.

## 8. Division of a take into sub-folders (examined 2026-11-08; the owner asked)

Facts (KB, labels as given): every create in an exFAT folder walks all its entries from 0 under `s_lock` (confirmed in rpi-6.12.y source,
dng-chain/F/V-F4.md row 16); 5 dentries per frame file (confirmed, row 17); the per-dentry constant c is UNMEASURED, estimated 80-250 ns
(F4 §2.3); A0/A1 (15,000 files, 25 fps) exclude only c >~ 450 ns; the SDR12 33 fps 10-min takes (19,857 files, 30.3 ms period) exclude
roughly c >~ 250 ns (derived here); the 2026-10-30 synthetic sub-folder test reached 6,000 files per folder under drive stalls and says
nothing about this regime (S1.md §3.2). Deletion: unlink is O(1) while the dentries are cached (same boot); after a reboot each unlink
re-walks the directory (hint reset by iversion): minutes per 45,000-file clip (derived from the same source reading; unmeasured).

Predicted create cost at the end of a take (5 x N x c):

| Take | Files N | c = 80 ns | c = 250 ns | Frame period |
| --- | --- | --- | --- | --- |
| 10 min 25 fps (measured clean) | 15,000 | 6 ms | 19 ms | 40 ms |
| 15 min 25 fps | 22,500 | 9 ms | 28 ms | 40 ms |
| 30 min 25 fps | 45,000 | 18 ms | 56 ms | 40 ms |
| 30 min 30 fps | 54,000 | 22 ms | 68 ms | 33 ms |
| 30 min 33 fps (SDR) | 59,400 | 24 ms | 74 ms | 30 ms |

Reading: unless c is at the bottom of its range, a single-folder 30-min take saturates the filesystem lock in its last 10-15 minutes,
independent of the drive and of every lever under test; 15-min takes are inside the period at any c in the range. This is the first
thing the campaign must measure, because it decides whether 15/30-min single-folder takes test the drive or the directory.

Options: (a) keep one folder (no change) if c is small; (b) Core writes sub-folders of N frames (`[storage] frames_per_folder`, default
0 = off; the WAV and the clip root unchanged; numbering continues; a flatten script on the Mac for NLE import, since Resolve/Premiere
import one folder as one clip); (c) Core auto-splits the clip every M minutes (new folder + WAV, as cinepi-raw does on reconfigure):
no flatten, but separate clips; (d) a 4-dentry clip-name template (19 chars): -20 %, not a fix.

Recommendation: a ZERO-WEAR probe first (Core idle, nothing recording): create 60,000 empty files in one folder of the card with Core's
name pattern, timing each `open(O_CREAT|O_EXCL)`+close (empty files allocate no cluster: the only bytes written are ~10 MB of directory),
then time `unlink` of all of them in creation order (same boot), report latency vs index (slope / 5 = c), then a second run after
`drop_caches` or a reboot for the cold-cache delete cost. Pre-registered rule: create cost at N_target <= 25 % of the frame period ->
one folder, no code; above -> option (b) built as a knob and tested at 15 and 30 min against one-folder controls (same arm). Also:
the runner deletes clips in the boot that wrote them, never after a reboot, and budgets the delete time (measured by the probe).

## 9. Split A/B at the long stages (owner, 2026-11-08: "we also need to know if splitting a clip makes a difference for long recordings")

- The zero-wear probe (section 8) measures the create cost in isolation; it does not show the effect in the live system (4 writers, the
  per-block mapping lock, the fsync thread, the RAM queue). So the campaign measures BOTH: the probe first (prediction), then paired long
  takes: for the top surviving arm per mode at the 15-min stage and again at the 30-min (or fit) stage, one take with one folder and one
  with sub-folders (`frames_per_folder` = 5,000, i.e. <= 25,000 dentries per folder), same arm, back to back, order alternated between the
  two stages (U S at 15 min, S U at 30 min), no cool-down, stop-on-drop. Outcome: time to the first drop (survival), lost frames,
  Core's `peak_queue` / RAM-buffer peak, the nvme write-latency tail from the 1 Hz log, and the writer stall signature. With stop-on-drop
  the pair is read as: unsplit stops before split = the directory matters (the effect size is the time difference); both clean = no
  effect at this length; both stop at similar times = not the directory.
- Prerequisite (code, before the long stages; in the Opus handoff): Core knob `[storage] frames_per_folder` (0 = off, default; else N)
  and env `APERTAR_CDNG_FRAMES_PER_FOLDER`: frame files go to `<clip>/part_NNN/<frame name>` (the clip root keeps the WAV, the
  sub-folder is created when the writer reaches the boundary); the sync thread's folder fsync covers the part folder; the time-left
  and file counting read recursively; `collect` counts DNGs recursively; a flatten script for the Mac (`mv part_*/* .`, then rmdir).
  Verification before use: a 60-s take with N = 500 shows the folders, the frame count equals fps x seconds, Core's counters 0.
- Cheaper complement if the Core change slips: the 2026-10-30 synthetic writer (`/home/pi/ab-tests/variant2.py`, 4 writers, real
  cadence, one folder vs sub-folders) with 1 MB files at 25 files/s for 30 min (45 GB, 45,000 files) isolates the directory cost at the
  real file rate with ~6 % of a take's wear; it does not reproduce the mapping-lock pressure of 16.9 MB files.

## 10. The owner's requirements for this plan (consolidated 2026-11-08; every design must cover each)

| # | Requirement |
| --- | --- |
| R1 | Unsupervised campaign exploring the NVMe for drop-free cDNG; mainly 4K 16-bit Clear HDR and 4K 12-bit SDR; this campaign = the 4K full-frame and 4K crop modes |
| R2 | Levers: Apertar storage tuning settings, compression modes, Log, TDN, phase lock, WebUI on/off (plus FE Config depth 4 from evening 4) |
| R3 | Minimize bytes written (drive wear); smart order: screen at 3 min, then 5, 15, 30 min for the fuller picture |
| R4 | Prognoses after each stage: what is worth pursuing; eliminate an option/combination at its first dropped frame and stop that take |
| R5 | Do not clear the drive after every take; clear only when the next take needs the space; at the end delete all campaign clips |
| R6 | No NVMe cool-down between takes (a real shooting environment); temperature logged, not gated |
| R7 | A robust detached script on the Pi runs everything (as the previous campaign) and, between takes, takes its time to add all relevant log data to the database |
| R8 | Monitoring from an ssh session: what is going on and why, progress; the runner reports between takes, never during one |
| R9 | Examine whether a take should be divided into new folders (section 8) |
| R10 | The 75 % fill rule is removed (fill is measured, the only gate is physical fit) |
| R11 | Adapt to a 500 GB card; make the best of whatever card is in |
| R12 | The best recipe transfers to the 1 TB CFexpress cards (a transfer set per card) |
| R13 | Measure whether splitting a clip makes a difference for long recordings (section 9) |
| R14 | Target: 30 min without a dropped frame in all (4K) modes; the plan is executed by an Opus thread in VS Code on the Mac |

## 11. The test rig is the owner's 500 GB NVMe (owner, 2026-11-08, later message)

- The campaign runs on the 500 GB test NVMe, NOT the 1 TB Corsair MP600 Mini the record's drive numbers come from. Candidates named in
  the KB: Kingston SKC3000S512G (477 GiB; the erased first long-take run, longtakes-campaign-plan.md "Decisions") and the owner's
  Crucial P310 (seen in the slot 2026-11-03, two void takes; R1 confounder 16). Which one: ask; the runner reads model/serial/size.
- Consequences: (1) heavy arms' top tier = fit length (HDR16 unc 16-19 min, SDR12/HDR12 unc 20-26, Log12 22-26; lossless SDR12 and the
  light crops fit 30 min); every fit-tier take ends with the card full (pass_drive_full at 6 GiB free): the full-card condition is
  exercised on every long take. (2) The 30-min verdict for the heavy arms comes from the CFe transfer stage (S7), which becomes
  mandatory and is the actual 30-min test. (3) Drive-specific facts do not transfer (733 MB/s, the 0.9 TB stall, 34 -> 54 C, pSLC);
  S1's probes (60 s direct write, write-pattern matrix, trimmed vs untrimmed, temperature trajectory) run on this card first (~60 GB).
  The directory constant c transfers (CPU-bound on cached entries). (4) Wear: 10 TB = ~2.5 % of a 400 TBW rating (KC3000 512 GB) but
  ~9 % of ~110 TBW (P310 500 GB, DRAM-less, HMB denied by nvme.max_host_mem_size_mb=0): if P310, cap the test-card writes at ~4-5 TB
  (screen at 3 min, meter takes, one long take per mode and tier, heavy long takes on the CFe cards). (5) The split pair at the fit tier
  ends at equal fill, so the comparison holds; the directory effect is milder (28,500 files = 22 % of the period at 25 fps) than at
  30 min on the 1 TB cards, where it bites hardest.

## 12. The cards, confirmed (owner, 2026-11-08): test NVMe = Kingston KC3000 512 GB; CFe cards = Corsair (MP600 Mini 1 TB)

- Test rig: Kingston SKC3000S512G (477 GiB; DRAM-equipped; rated ~400 TBW, to confirm by the web reader; 2280 Gen 4 at the Pi's Gen 3 x1).
  10 TB of campaign writes = ~2.5 % of its rating: the default budget stands. Its drive-side facts are unmeasured in the KB: S1 runs on it
  first (60 s direct write, write-pattern matrix, trimmed vs untrimmed, temperature trajectory).
- Shooting media: the CFexpress cards are Corsair MP600 Mini 1 TB (the same model as the record's test drive): 733 MB/s direct writes,
  the ~0.9 TB untrimmed stall and Core's trim, 34 -> 54 C in 10 min at 415 MB/s, and the clean 10-min 4K HDR16 25 fps takes all transfer.
  S7 on these cards is the actual 30-min test for the heavy arms (which do not fit on 490 GB).
- Caveats from the KB for the Kingston: (1) 2026-11-06: two Pi resets during the smoke test, kernel "Voltage normalised", EXT5V 4.78 V at
  idle; power supply suspected (unconfirmed), the owner tried another supply (longtakes-campaign-plan.md). S0 checks `vcgencmd get_throttled`,
  `vcgencmd pmic_read_adc` (EXT5V), the kernel log for under-voltage; the runner resumes after a reboot only if its last status was clean
  and at most once (a resume marker), else it waits for the owner. (2) The erased first run on the Kingston ("none clean to 25 fps at
  16-bit") was on a different CM5 board that dropped within 2 s at 30 fps where the C0 board (c041a0) ran clean: a board effect, not the
  card; the session records /proc/device-tree/model and the revision (the runner already does).

## 13. Rig confirmations (owner, 2026-11-08 afternoon)

- Test rig board: CM5 Lite **C0** (revision `c041a0`), the board of the SSD run and of the clean 135-s 30 fps baseline; the erased first
  Kingston run's "none clean to 25 fps" was on another board and is not evidence about this rig. The runner records
  `/proc/device-tree/model` and the revision per session; a different revision = a different rig in the database.
- Cards: test NVMe = Kingston KC3000 512 GB (rated ~400 TBW, from memory, web reader to confirm); CFe cards = Corsair MP600 Mini 1 TB
  (rated ~600 TBW; the record's drive). Campaign cost: ~10 TB on the KC3000 (~2.5 %), ~2.5 TB per CFe card (~0.4 %).
- Core on the camera since the 13:00 boot (fork-log 2026-11-08 later): cinemate-port fast-forwarded to clip-split, Core `ba0658d`
  (frames_per_folder=0, clip_merge on by default), UI `7ea9afc` reads split clips. At that boot the Samsung T7 was on /media/RAW:
  S0 must confirm the mounted medium (model, serial, size) before any take; the probe's step 4 (cold-cache delete of
  `probe_exfat_dir_125428`, 10,000 empty files) is still on the Kingston and is a zero-wear S0 item.

## 14. Corrections from the arithmetic reader (R3) and the web reader (R8), 2026-11-08 afternoon

- HDR16 uncompressed FILE = 16,590,340 B = 16.59 MB (measured, hardware-log:140; V-F4 row 10): Core writes the 2160 active rows; 16,896,000 is
  the raw buffer (3840x2200x2). Every HDR16-unc figure above is 1.85 % high. Corrected: 415 / 465 / 498 MB/s at 25 / 28 / 30 fps;
  75 / 124 / 373 / 747 GB per 3 / 5 / 15 / 30 min at 25 fps; 836 / 896 GB per 30 min at 28 / 30; 75 / 84 / 90 % of the empty Corsair.
- Kingston KC3000 512 GB volume ~477 GiB = ~512.0 GB decimal (derived from the erased run's samples; df unconfirmed): ~502 GB usable with the
  10 GB reserve. Max minutes: HDR16 unc 20.2 / 18.0 / 16.8 at 25 / 28 / 30; SDR12 unc 26.9 / 22.4 / 20.4 at 25 / 30 / 33; Log12 26.9 / 22.4
  at 25 / 30; SDR10 unc 32.3 / 26.9 / 24.5; SDR12 lossless 50 fps 28.0. Fit-tier HDR16 unc = 29,500-30,300 files: 23 % of the period at 25
  fps, 26 % at 28, 28 % at 30 (above the 25 % line at 28-30 fps).
- 25 % ceiling from the measured fit (with intercept): 32,161 files at 25 fps, 28,777 at 28, 26,898 at 30, 24,505 at 33, 16,370 at 50.
- HDR16 Log + lossless is NOT a >= 25 fps arm on the record (HDR16 lossless encoder 17.6-18.5 fps measured; Log made lossless files bigger
  at 4K HDR12 on the SSD): at most a pre-roll capacity reading (the 12-bit encoder path is a code reading, probable, unmeasured).
- SDR12 lossless at 50 fps is probably CPU-bound (2.81 cores at 33 fps measured -> ~4.2 cores derived).
- The KB's 4K crops: 3840x{2076, 2072, 2024, 1920, 1744, 1728, 1632, 1608, 1536, 1504} at 10/12-bit; 16-bit height crops exist (31.9-42.4 fps,
  heights not in the KB). 3840x1600 is not a mode. Only 3840x2076 has a take (12 % lost at 50 fps, old build, 80 % full untrimmed drive).
- "Longest clean folder 19,857 files" holds on the NVMe only; the T7 SSD run passed 30 min with 45,006-59,412 files in one folder, 0 drops
  (measured): single-folder passes exist at the 30-min file counts when the drive pattern has margin.
- Wear record: 25.28 TB (11-02 baseline), +1.34 (evening 1), +0.84 (evening 2), 29.01 TB after evening 3; evening 4 and the 11-07 NVMe runs
  unrecorded; all SMART numbers are the Corsair test card's; no Kingston SMART reading exists in the KB.
- Board effect (erased Kingston run vs C0): probable at most (n = 1 + 1, confounded); the owner has since moved the test rig to a C0 board.

### Web facts (R8; label web unless noted)
- Kingston KC3000 512 GB: Phison E18, DRAM yes, 7,000 / 3,900 MB/s, **400 TBW**, 5 years, 0-70 C operating; rated 0.34 W avg, 4.1 W max write;
  measured idle ~1.1-1.2 W (2 TB) with APST off; thermal: the 2 TB throttles after 60-90 s of multi-GB/s writes, SMART limit 84 C.
  **pSLC ~176 GB on the 512 GB model (single source); post-cache TLC write for 512 GB unconfirmed, probable 0.4-0.8 GB/s (derived from the
  2 TB's ~1.5-1.6 GB/s and the die count)**, i.e. at or below the Pi's Gen 3 x1 link and possibly below HDR16's 415-498 MB/s. The cache is
  dynamic (~1/3 of FREE TLC), so it shrinks as the card fills. => A long HDR16 take on the Kingston leaves the pSLC window after ~7 min
  (176 GB / 415 MB/s) and then runs at the unknown TLC floor: a Kingston-specific drive limit that does NOT transfer to the Corsair.
  S1 must measure it: one direct-write run of >= 250 GB with a 1 Hz bandwidth log (fio or dd, Core stopped), trimmed card; cost ~250 GB,
  once. If the floor is below ~420 MB/s, the heavy-arm long tiers on the Kingston measure the drive, not the camera: run them on the Corsair.
- Corsair MP600 Mini 1 TB: two drives share the name: CSSD-F1000GBMP600MN (2023, Phison E21T, DRAM-less, HMB 64 MB, Micron 176L TLC,
  4,800 / 4,800) and CSSD-F1000GBMP600MNR2 (2024, E27T, Kioxia 162L TLC, 7,000 / 6,200); both **600 TBW**, 5 years, 0-65 C spec; pSLC ~50 GB;
  **post-cache ~800 MB/s**; throttle ~80 C; idle 1.4 W. NOT to be confused with the MP600 CORE Mini (CSSD-F1000GBMP600CMN, E21T + QLC,
  250 TBW): the owner's CFe cards' exact part number is unconfirmed and matters (QLC post-cache would not carry 4K). Sold in DIY CFe-B
  adapters (ZITAY, JEYI): the shell removes convection and adds mass (probable: later throttle onset, higher steady temperature); contact
  pad quality dominates; the Pi's Gen 3 x1 halves write power vs in-camera Gen 3 x2.
- Pi 5 / CM5: Gen 3 x1 practical ~760 MB/s write, ~820-890 read; the 6.12.y device tree sets nvme.max_host_mem_size_mb=0 (the Pi default,
  not the owner's choice; 6.18.y sets 32), so DRAM-less drives run without HMB; under-voltage flag below 4.63 V +-5 %; FFC 5 V budget 1 A;
  the official HAT+ gives "up to 3 A" to M.2; 2280 drives not officially supported; "Voltage normalised" is the hwmon under-voltage poll.
- exFAT 6.12 (source): lookups linear with rewind; iversion bump per create resets hint_stat (full negative scan per create; 2026 patches
  address it, not in 6.12); hint_femp makes the empty-slot search O(1); discard mount = one discard per freed cluster (81,920 commands per
  10 GB at 128 KB) vs fstrim coalescing; directory limit 8,388,608 entries.
- SMART percentage_used is the vendor's estimate, may exceed 100, and is not a failure indicator; compare DU x 512,000 / TBW.
- LPDDR4X: 17.07 GB/s interface; measured memcpy ~6.0 GB/s, memset 9.4-13.9 GB/s (Pi 5 / CM5).

## 15. Audio (owner, 2026-11-08: a 3-min take ended itself after 32 s with "ALSA capture: Broken pipe"; all frames written; merge off)

Facts from the KB: ALSA ring 100 ms / 10 ms period (`audio capture: buffer_frames=4800 period_frames=480 requested_ms=100/10` in every
SSD-run take; `APERTAR_AUDIO_BUFFER_MS` 100-4000, config.md:461); T30's writer thread between capture and the raw file (fork-log 60ce8e9,
0358fcf: ring back to 100 ms because 1 s made the drift figure unreliable; b606c4f: the raw file fsynced once a second); `peak_backlog_kb`
in the SSD run 340-1,437 KB per take (= up to ~5 s of s24 stereo 48 kHz): the raw-file writes stall for seconds under DNG pressure;
"xruns are handled with snd_pcm_recover" (sources/research-2026-10-25/core-internals-notes.md:583, old read); discontinuities > 10 ms
padded (p2-phaselock-core.md:41). Cinemate: SCHED_FIFO capture, 2 s ring, silence fill on EPIPE, wall-clock reconciliation
(cinemate-lessons §3, fed2ede, 6ccfabd); Pi 4 xHCI sharing stalls ALSA (s1-storage-cinemate.md:99). The SSD run: 189 takes with audio,
0 faults. Candidates for the 32-s fault: (a) a kcompactd proactive-compaction burst (period ~32.8 s, tier2-plan §1) holding the capture
thread > 100 ms; (b) the writer backlog pushing back into capture if its queue is bounded; (c) a USB device hiccup; the split code is
unlikely (32 s is no part boundary; all frames written). Whether Core treats EPIPE as fatal on ba0658d: unconfirmed (read the source).

Plan additions: per-take audio columns (ring, peak_backlog_kb, discontinuities, trim/pad, drift, errors); outcome `audio_fault` (not a
video drop, never eliminates an arm alone; repeated once; the journal window, vmstat compaction and usb lines at that second kept);
levers if it recurs: `APERTAR_AUDIO_BUFFER_MS` 1000-2000, `compaction_proactiveness=0` via the helper, the Core fix (recover + pad +
log, continue); S0 checks the mic's USB controller. First desk task for the Opus thread: that take's journal window and stop reason.
