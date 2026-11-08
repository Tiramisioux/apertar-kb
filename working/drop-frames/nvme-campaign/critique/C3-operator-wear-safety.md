# C3: operator, wear and safety critique of plan v2 (NVMe 4K campaign on the Corsair cards, 2026-11-08)

Critic: operator, wear and safety. Object: `scratchpad/draft/plan-v2.md` as it stood at 13:07 (sections cited as v2 §n), with
`constraints-and-arithmetic.md` §10-15 (R1-R15), `v2-rules-from-C1.md`, `build-list.md` (incl. §F, A13-A15, A3'), `handoff-nvme-campaign.md`,
the research reports R1/R2/R3/R8/R10, the critique C1, and the KB at `/home/user/apertar-kb` (working tree `e2d2499`, which includes
`nvme-campaign/clip-split-verify.md` and the probe's measured step 4). Branch pages read with `git show origin/claude/practical-johnson-he481b:...`.
Labels are the KB's own (measured / derived / probable / unconfirmed; web for R8's facts); my own arithmetic is marked **critic's model**.
Nothing ran on the camera or the network. `plan-v1.md` was read only for the diff: v2 moved the campaign onto the Corsair, adopted C1's
rules, added §5a (audio), the fill gate's cold-delete budget and the claims table.

## 0. Verdict in one paragraph

v2 is a sound experimental design that is not yet a safe unattended procedure. Its deletion rules protect the owner's clips from the runner,
but nothing protects them from the volume: the campaign card is the same exFAT card the owner shoots on, the rig's record holds 1,535 unsafe
shutdowns, three NVMe controller deaths, a dirty volume with bad checksums after one of them, two Pi resets in the last smoke test, and a
"Volume was not properly unmounted" at the very boot the probe's step 4 ran on; every 30-min take will end at 75-90 % full with the card at
or above its spec temperature. After a Pi reset the `/run` drop-in that defines the campaign (FE depth 4, merge off, pre-roll off) is gone,
and v2's "resume once if the last status was clean" would resume into the wrong environment. The audio fault is already known to end a take
(`fault=write_error … ALSA capture: Broken pipe`, measured), so the Core fix is a prerequisite of the 747-896 GB takes, not an open point.
The runner has no liveness signal and no independent stop if it dies, the root helper the detached runner can call includes `reboot` and
`poweroff`, and a Mac Wi-Fi hiccup counts as a void that can end a night. The wear budget is honest in shape; at the likely edge fps it is
~9.3 TB expected (not 8.3) and ~0.4 TB of it decides nothing. The findings below are ordered by consequence.

## 1. Findings, ranked

### F1. v2 §0/§6/§9: the campaign card carries the owner's footage on an exFAT volume that the rig has already corrupted once; the plan protects his folders only from the runner's own deletes

- What is wrong: v2 says "never the owner's folders" (§6 fill gate, §9) and the handoff forbids globs, but the owner keeps clips on the
  test card (`cDNG_26-11-07_C0001` on 2026-11-08, `probe-exfat-dir.md:26,33`, measured; `cDNG_26_11_04_20322419_C0001` "kept, User:
  perhaps he pressed record", `preregistration.md:784`), and the campaign writes 9-14 TB through that volume unattended. exFAT has no
  journal (`errors=remount-ro` in the mount options, `probe-exfat-dir.md:18`). The rig's record: controller drop while idle with the
  volume left dirty and `fsck.exfat -n` finding bad checksums and stray entries in the folder written a minute before
  (`lessons/hardware-log.md:123-135, 295-317`, measured); `Disabling device after reset failure` under the synthetic load, volume
  read-only, reboot needed (`hardware-log.md:717-720`, measured); 1,535 unsafe shutdowns in the card's own SMART log
  (`night-2026-11-01.md:106-108`, measured); two Pi resets during the 2026-11-06 smoke test (`longtakes-campaign-plan.md:4-6`,
  supply suspected, unconfirmed); "Volume was not properly unmounted" at the 13:16 boot of 2026-11-08 (`probe-exfat-dir.md` step 4,
  measured). None of these is a runner bug; all of them can take the whole volume with it.
- Fix (S0, before any take, Patrik): the campaign card holds NO owner footage: offloaded, verified, and `ls /media/RAW` shows only
  campaign folders; the runner's void list gains "a folder on the card that is not in the database -> stop and ask" (replaces PRESERVE
  as the safety net); `fsck.exfat -n` (read-only, via the helper) in S0 and after every unclean shutdown before the runner may resume.
  Part B cards (the owner's shooting media, F15) the same before their evening. Say in §0 that this is the one irreversible risk the
  campaign carries and that it is the owner's decision.

### F2. v2 §7 "After a Pi reset the runner resumes once on the next boot only if its last status was clean": the resume lands in the wrong environment and on a dirty volume

- What is wrong: everything that defines a campaign take lives in `/run` and dies at reboot: the FE depth 4 YAML drop-in,
  `APERTAR_CLIP_MERGE=0`, the pre-roll setting (v2 §5; build-list D "writes the /run drop-in"; `e4-helper.sh` header: "A reboot also
  undoes all of it (/run and /proc/sys are not persistent)", measured pattern). After a reset Core comes up with depth 2, the merge worker
  ON (default, fork-log `ba0658d`), pre-roll on. A runner that "resumes once" then records scored takes in a state that is not the arm,
  and the merge worker starts flattening the previous boot's split clips while the runner deletes them. "Last status clean" is undefined
  (the status file is written only between takes, so a reset mid-take leaves "take N running", and a reset between takes leaves "clean"
  while the volume may still be dirty, `probe-exfat-dir.md` step 4). The AUTORESUME crontab mechanism of the storage plan (§7.1, branch)
  is not in the build list. The previous boot's clips can only be deleted cold (4.5 min per flat 30-min clip, derived from the measured
  slope, `probe-exfat-dir.md` step 4), so the fill gate may not be able to make room anyway.
- Fix: the resume marker is written by the runner only between takes and consumed once at boot; on resume the runner first checks the
  helper's `status` (drop-in present, Core's environ has `LIBCAMERA_RPI_CONFIG_FILE` and `APERTAR_CLIP_MERGE=0`, `clip_merge_enabled`
  false, `frames_per_folder` as expected) and a clean `fsck.exfat -n`; if anything is missing it writes "WAITING: rearm needed" and
  stops. In practice: after any reboot Patrik re-arms, so say in §10 that a reset ends the night. Add the resume marker and the
  re-arm check to the build list (A5/A6 neighbourhood, ~30 lines).

### F3. v2 §5a + §11.7: the audio fault is already known to end a take; the Core fix is a prerequisite of the long tiers, and "never eliminates an arm" is wrong for the owner's goal

- What is wrong: §5a makes the Core fix conditional ("if an xrun ends a take today") and §11.7 leaves it as an open point, but the KB
  already shows it: `recording failure: fault=write_error … ALSA capture: Broken pipe`, the take ended at 32 s with all frames written
  (`clip-split-verify.md:23`, measured). The rate is unknown and the base differs from the SSD run (0 faults in 189 takes with audio on
  `f4a1393`, `findings-longtakes-ssd-2026-11-07.md:4-5`; 1 fault in 9 verification takes on `ba0658d`): "the split code is unlikely" (§5a)
  rests on "32 s is no part boundary", which excludes the part-boundary path only; the merge worker's scan thread and the new code run
  in the same process (unconfirmed either way, n = 1). Consequence for an unattended night: a fault in a 30-min HDR16 take costs
  747-896 GB and 30 min; "repeated once" (§5a, A13) doubles it; two faults stop the night (A13). A13 also never prunes an arm on audio
  faults, but the owner records with audio: an arm whose CPU load (Log's copy worker, SDR12 lossless at 2.8-4.2 cores,
  `findings-2026-11-04.md:56,64`, measured / derived) starves the capture thread is unusable for him whatever its video count.
- Fix: (1) the Core fix (recover, pad with silence, log `audio discontinuity`, continue) is a hard prerequisite of S4-S6 and Part B;
  S2 may run before it at the real 100 ms ring to measure the fault rate on cheap takes. (2) If the fix is not in by night 2, the long
  tiers run with `APERTAR_AUDIO_BUFFER_MS=1000` as a recorded deviation (the known side effect: the drift figure becomes unreliable,
  `hardware-log.md:389`, measured), never at 100 ms unfixed. (3) Pre-register: audio faults are tabulated per arm and per Core CPU;
  2 of 2 faults = the arm is "out with audio" (its own column), and the final recipe is reported with its audio fault count. (4) A
  fault in a long take does not auto-repeat: the runner writes status and waits for the Opus thread's go.

### F4. v2 §9 / build-list A5-A6: if the runner dies, Core keeps recording until the card is full, and nobody can tell from `status.md`

- What is wrong: A6 puts `record_stop` in a `finally`, which covers exceptions, not SIGKILL, the OOM killer or a hung interpreter;
  R10 §7.5 shows the sampler thread dying silently on `statvfs` with the main loop reading stale samples (measured in code). The status
  file is written only between takes (v2 §9, R8), so at 03:00 "take N running since 01:10, planned until 01:40" and a runner that died at
  01:12 look the same over ssh. Core has no take-length limit of its own in the plan; a stuck take runs to the 6 GiB guard (the runner's,
  so not applied) or to a full card.
- Fix: a heartbeat file on `/run` (`heartbeat`: epoch and take id, every 60 s, from the sampler) that the owner reads next to
  `status.md`; an independent `longtakes-watch` (a second small script or a systemd timer, no sudo) that sends `record_stop` and writes
  "STOPPED: runner heartbeat lost" if the heartbeat is older than 180 s while Core reports `recording`; the status header says "runner
  pid P, heartbeat T s ago". ~40 lines; blocks S2.

### F5. v2 §7 temperature and §6 S5/S6: the plan cannot see the drive throttle or warn, and heat is aliased with mode

- What is wrong: R6 (no gating) is honoured, but: (a) no take longer than 602 s exists and the only long heat datum is 72 C after 10 min
  at 410 MB/s (`findings-2026-11-04.md:57`; R1 §4.7, measured); (b) the card's SMART log already shows 103 thermal T1 transitions
  totalling 7,653 s (`night-2026-11-01.md:107-108`, measured): this card has throttled in this rig before; (c) A12 reads smart-log only at
  the start and end of a night, so `critical_warning` (a stop-the-night condition in §7) set by temperature at 01:30 is seen at 06:00;
  (d) S5 and S6 run HDR16, SDR12, HDR12 back to back in that order, so HDR16 always starts cold and HDR12 always starts hottest: heat is
  100 % aliased with mode in the only 30-min data the campaign produces; (e) v2 §2 says the thermal curve "is measured per card in S1",
  but S1's 100 GB direct write lasts ~2.5 min at the link rate (critic's model: 100 GB / ~700 MB/s) and cannot show a curve that takes
  10 min to reach 72 C.
- Fix: smart-log through the helper between EVERY take (one `sudo -n` call, milliseconds): composite temperature, `critical_warning`,
  the thermal transition counters and total times into the take record; a T1 time increase during a take is a covariate column
  ("throttled s"), not a gate; rotate the mode order between S5 and S6 (and per Part B card) so every mode gets one cold and one hot
  start, pre-registered; drop the "thermal curve" claim for S1 and take the curve from S4's 15-min takes.

### F6. v2 §6 fill gate / build-list A3: the runner deletes with `rmtree` and then hopes Core's trim trigger fires; Core's own delete route does both safely

- What is wrong: A3 deletes the oldest clips with `shutil.rmtree`, waits 60 s for Core's `media: trim` line and otherwise asks the helper
  for `fstrim`. Core's trigger for outside deletes needs >= 1 GiB between two polls (`ApertarCoreApp.cpp:10863-10869@f4a1393`, confirmed;
  "may never fire after a slow delete", `reanalysis §7`, derived), and a merge worker that is ON by mistake would be renaming inside the
  folder being removed. Core's media route does it right: `POST /api/media/delete` pauses the merge, deletes, trims (`paused (media
  delete)` … `delete ok in 0.1 s, trim 479 ms`, `clip-split-verify.md:16`, measured).
- Fix: the runner deletes through Core's media route by the exact clip name from its database, never by path pattern; the trim is then
  part of the call and the 60-s wait and the `fstrim` fallback go; a clip Core does not list is never touched; `--clear-all` and
  `clear_media` are removed from the campaign build (R10 §7.4: PRESERVE can miss the owner's later clips). The end-of-campaign delete
  (R5) uses the same route, one clip at a time, and refuses if any folder on the card is not in the database (F1).

### F7. v2 §11.6 / build-list D: the detached runner can call `sudo -n` on a helper that includes `reboot`, `poweroff`, `restart-core`, `drop-caches`

- What is wrong: A12 and A3 have the runner call the helper with `sudo -n` (smartlog, fstrim). The e4 pattern grants user `pi` every mode
  word of the helper NOPASSWD, including `reboot` and `poweroff` (`e4-sudoers:4-14`). That was acceptable for a supervised night; here
  600+ new lines of runner (A1-A15) run unattended under the same uid. One wrong branch and the Pi reboots mid-take (F2) or Core restarts
  into a warm-up-less take.
- Fix: two aliases. `apertar-campaign-ro` for the runner: `smartlog`, `fstrim`, `status`, `audio-usb`, `fsck-ro`. Everything that changes
  state (`arm`, `disarm`, `restart-core`, `compact0/restore`, `drop-caches`, `reboot`, `poweroff`) in a second helper that refuses when
  stdin is not a tty (`[ -t 0 ] || exit 1`), so only Patrik's interactive shell can run it. The runner never asks for a reboot.

### F8. v2 §7 void rules: a lost WebUI stand-in is a "wrong client count" void, and a second void stops the night

- What is wrong: the stand-in is `webui_remote.py` on the Mac under `caffeinate`, following `web_flag` over one ssh `tail -F`
  (`webui_remote.py:1-40`); `wait_peers` fails the take start after 30 s without a client (`longtakes.py:869-874`, R10 §6b p). A Mac
  sleep, a Wi-Fi roam or an sshd timeout at 02:00 therefore voids a take; §7 repeats a void once and stops the night on the second. The
  stand-in is also not a browser (R1 §4.3: polls + MJPEG, no page rendering): "WebUI on" is a fixed state the campaign can only hold
  approximately.
- Fix: a missing client is a WAIT state, not a void: the runner retries every 2 min for up to 30 min with "WAITING: no WebUI client" in
  the status, then stops the night; the Mac on Ethernet and `ServerAliveInterval` plus a reconnect loop verified in S0 by pulling the
  Mac's network for a minute; the per-take record keeps the stand-in's `mjpeg connected` state as a covariate (as evening 4 did,
  `preregistration.md:624-627`).

### F9. v2 §8 wear budget: ~1 TB low at the likely edge fps, and ~0.4-0.6 TB of the plan decides nothing

- Recomputed with the plan's own take counts and the corrected 16.59 MB file (critic's model, decimal GB, at the record's likely edges
  HDR16 28 fps = 465 MB/s, SDR12 40 fps = 498 MB/s, HDR12 30 fps = 373 MB/s): S0+S1 ~220; S2 ~2,500 (warm-ups 250, walks ~900,
  levers ~730, controls ~400, crops ~220); S3 ~385; S4 ~1,200; S5 ~2,400; S6 ~2,400: **~9.1-9.3 TB expected**, not 8.3; worst (split
  members on late drops +2.4, MLV +2.4, one 30-min crop +0.54) ~14 TB against the 10 TB cap. Per other card 2.4 TB (0.4 % of 600 TBW).
  The campaign card: 29.0 TB after evening 3 (`handoff-drop-frames-tier1.md:185`, measured) plus evening 4 and the erased 11-07 runs
  (unrecorded, R3 §5) -> ~31-33 TB now, ~41 TB after: ~7 % of the 600 TBW rating (web) and, by the drive's own 3 % at 25.3 TB,
  about +1 point of `percentage_used` (derived, loose: an integer percentage; R8 §5 warns the vendor figure can run ahead of host writes).
- The 1 TB/day question (v2 §0 says "about 600 such days"): the remaining rating is ~570 TB -> ~570 days (1.6 years) at exactly 1 TB
  every day; the drive's own estimate (~840 TB implied, derived) says ~2.2 years; the rating is a warranty figure, not a failure point;
  the campaign is ~9-10 of those days. State all three with labels.
- Bytes that decide nothing: S3 (~385 GB; v2 admits "little certainty"); the 100 GB knee probe (the post-cache floor ~800 MB/s, web, is
  above the Gen 3 x1 link ~760 MB/s, web, so the probe measures the link, and 2.5 min show no thermal curve: 30 GB past the ~50 GB knee
  would do, saves 70 GB); the WebUI-off ABBA at HDR16 (~300 GB) answers a question the owner's real use (WebUI on) does not ask: one pair,
  replicate only on a difference (saves ~150 GB); Part B's HDR12 take (672 GB per card) adds no drive-side information (same bytes as
  SDR12, lower rate). Fold S3 into S2: the second concordant take of a clean cell runs at 5 min (the pair is 3 + 5 min), which keeps the
  owner's ladder and removes a stage (~385 GB). The S6 soak as the split variant (2.4 TB) is justified (C1 F7: the second 30-min take is
  the most valuable extra), but the claims table must then say "1 unsplit + 1 split", not "2 of 2 at these settings".

### F10. v2 §5/§6 S0: the merge worker is checked once; real use runs it ON and the campaign never sees a take start during a 4K merge

- What is wrong: `clip_merge` is on by default on the running build (fork-log `ba0658d`); v2 §6 S0 reads `clip_merge_enabled` once and §5
  relies on the drop-in; §7's void list does not include it. A merge of a flat 45,000-frame clip is ~5 min of renames under `s_lock`
  (`probe-exfat-dir.md` step 3b, derived); it pauses 33 ms after `record_start` (`clip-split-verify.md:14`, measured, one 60-s take at
  25 fps). If the split variant wins, the owner will shoot split clips with the merge worker ON and the next take will start during a merge
  of 45,000 files: untested at that size.
- Fix: `clip_merge_enabled` false and `frames_per_folder` as the arm in the per-take `verify()` (void otherwise); one S6 pair with the merge
  ON if the split variant is the recipe (the 30-min split take, then a 3-min take started 10 s into its merge), else the recipe ships with
  an untested interaction.

### F11. v2 §5 "nothing else on the Pi": the systemd timers are not on the list

- What is wrong: Debian's `fstrim.timer` is enabled by default and runs weekly (`working/dng-chain/R4.md:202-206`; "unconfirmed on this
  rig", `R2.md:270`); `apt-daily`, `apt-daily-upgrade`, `man-db`, `logrotate` fire around 00:00 or at random offsets. A trim of the
  campaign card during a 30-min take is exactly the drive-state event the storage plan wants to control (M4), and an `apt` run is CPU and
  I/O on the SD card during a take.
- Fix: S0 records `systemctl list-timers --all`; Patrik masks `fstrim.timer`, `apt-daily*.timer`, `man-db.timer`, `logrotate.timer` for the
  campaign nights (restore list); the runner's gate refuses to start a take while `fstrim` or `apt` runs.

### F12. v2 §9/§10: the status file has no liveness, no "what happens next", and the go/no-go between tiers has no mechanism

- What is wrong: §10 says the go/no-go is "asynchronous through the status file", but nothing in the build list lets the runner receive
  it; night 1 runs S2 and S3 in one go, night 2 S4 and S5: who stops S4 from starting on a bad S2 verdict at 04:00? The status content
  (§9) lacks the plain-words first line ("RUNNING take 23 of ~45, HDR16 28 fps 3 min, ends 02:14; night ends ~05:30"), the decision ahead
  ("pass -> 29 fps; drop -> confirm at 28"), and liveness (F4).
- Fix: `GO-S3`, `GO-S4`, `GO-S5`, `GO-S6` sentinel files written by the Opus thread (or Patrik) after reading the status; the runner waits
  at a tier boundary with "WAITING: go for S4" and a timeout that ends the night cleanly; `status.md` starts with the one-line state, the
  heartbeat age, the next decision, and the expected end of the night. ~30 lines; blocks night 2.

### F13. v2 §1 marks R4 as met; §7 changed it (two concordant takes) without telling the owner

- R4 says eliminate at the first dropped frame; v2 §7 (from C1 F1) stops the take but needs a confirmation take before the cell is out,
  and repeats a single late frame once. Right statistically, but a deviation from the owner's rule; it is not in §11.
- Fix: list it in §11 as a decision for Patrik with the cost (a failing cell costs its time to the drop twice, seconds to minutes).

### F14. v2 §6 Part B: the preconditions of the other cards are missing

- What is missing: (a) the other cards are the owner's shooting media and must have ~750-900 GB free for one 30-min heavy take: his footage
  is offloaded first (time, and F1's risk, for each card); (b) the part number is a gate, not a field: a CORE Mini (CMN, QLC, 250 TBW, web)
  has a dynamic pSLC that a 100 GB probe would not exhaust and a post-cache rate that "would not carry 4K" (R8 §2, web / probable), so the
  heavy takes on such a card test the card, not the camera; (c) trim state: Core trims at mount (`recipe.md:46`, measured), say so, and
  record `media_trim_last_unix` before the first take; (d) the mode order per card is unspecified (F5: pre-register heaviest LAST, the
  hot, real-use case, or the S5 order for comparability, but choose); (e) the adapter per card (brand, pad present) is not in the KB (R8
  §2 item 5, unconfirmed) and is what "the adapter's thermal contact differs per card" (§6) would be read against: a session field.
- Fix: Part B = HDR16 at its edge plus the arm with the highest MB/s (SDR12 at its edge if above HDR16's), two takes per card (~1.7 TB),
  the HDR12 take only if HDR12's recipe differs from SDR12's; the part number, firmware, adapter and `fsck.exfat -n` recorded before the
  first take; refuse a CMN card for heavy arms unless its 30-min floor was measured.

### F15. v2 §7 void list: three fixed-state checks are missing

- The touch UI must be drawing (the 2026-11-01 finding: capture losses need the touch UI drawing AND a high data rate,
  `hardware-log.md:945-975`, measured): a UI crash or a monitor that went to sleep changes the load for the rest of the night without any
  void; Core's PID must equal the PID of the last warm-up (a systemd restart after a crash keeps the `/run` drop-in but needs the 60-s
  warm-up, C1 F2); the mount must be read-write (`errors=remount-ro`: after one I/O error every later take fails as `record_start_failed`
  and the runner's existing rule stops the campaign, but the status should name the cause).
- Fix: per-take `verify()` adds `apertar-ui-direct` active with CPU > 0 in the last 10 s, Core PID unchanged (else warm-up), `statvfs`
  not `ST_RDONLY` (else "STOPPED: volume read-only").

### F16. v2 §6 S1 and §10: a drive-state write between S5 takes, and Patrik "at the start of each night"

- S1's "a 60-s full-speed write … again after the first full-card take and delete" lands between two 30-min takes on night 2: 45 GB of
  direct writes and heat that real use never adds before a take, and a confound for the next take's start state. Move it to the end of
  night 2. §10 needs Patrik "for the sudo steps at the start of each night": once the helper and sudoers are installed and the drop-in is
  armed, nothing per night needs him unless the Pi rebooted (then F2 applies and the night waits anyway); say so, and instead ask for his
  presence for the first hour of night 1 (the first fill-gate delete and the first stop-on-drop are the two code paths B7 cannot test on a
  host with a real card).

### F17. v2 §5 pre-roll OFF for every take: the deviation points the wrong way for the recipe takes

- With the pre-roll off every take starts cold: no primed write path, no pre-roll trim of its own blocks (feasibility lever 3), the
  encoder capacity not estimated. The storage plan wanted it off for storage probes (§5: "the pre-roll consumes prepared blocks; keep it
  off in storage tests"), not for recipe takes; the owner's real takes have it on; the start-up transient is also what the meter takes
  must correct for (C1 F8). The runner's start check today waits for the pre-roll line (R2 §5.16; build-list E3 changes it).
- Fix: pre-roll OFF only for meter takes and S1; ON (as the owner shoots) for S2's scored takes and the long tiers, so the campaign's
  first seconds are real use's first seconds. If Patrik wants it off throughout (§11.4), label every long-tier result "pre-roll off".

## 2. R1-R15: met or not

| # | Requirement | v2 | Gap |
| --- | --- | --- | --- |
| R1 | Unsupervised; the 4K modes | design yes | not safe unattended until F1, F2, F4, F7, F8 are in |
| R2 | Levers | yes (§5) | the WebUI-off pair answers a question real use does not ask (F9); TDN-on reduced to one take, fine |
| R3 | Minimise writes; 3->5->15->30 | yes (§6, §8) | S3 adds little (F9); the budget is ~1 TB low at the likely edges |
| R4 | Eliminate at the first drop, stop the take | the take stops; the cell needs two takes | an undeclared deviation (F13) |
| R5 | Delete only when needed; delete all at the end | yes in words | `rmtree` + trim-trigger hope instead of Core's delete route (F6); no protection of the volume itself (F1) |
| R6 | No cool-down; temperature logged, never gated | yes | smart-log only start/end; heat aliased with mode (F5) |
| R7 | A robust detached runner; the database between takes | ~700 new lines, B7 host tests | no liveness, no independent stop, no resume contract (F2, F4) |
| R8 | ssh monitoring between takes | content yes (§9) | no liveness line, no decision ahead, no go mechanism (F4, F12) |
| R9 | Folder split examined | yes (probe + S5/S6) | - |
| R10 | 75 % rule removed | yes | - |
| R11 | Make the best of the card | yes (A4) | trivial now that the campaign runs on the 1 TB cards |
| R12 | All tests on the Corsair; a check on the other cards | yes (Part B) | preconditions missing (F14) |
| R13 | Does splitting matter | yes, "consistent with" (C1 F4) | the claims table must say "1 unsplit + 1 split" (F9) |
| R14 | 30 min drop-free in all 4K modes; Opus executes | honest claims table | - |
| R15 | Keep an eye on audio | watch yes (§5a, A13) | the fix is a prerequisite, not conditional; arms are never pruned on audio (F3) |

## 3. Unattended failure cases: what v2 says, what it must say

| Case | Record | v2 | Missing |
| --- | --- | --- | --- |
| Card hot, throttling | 72 C after 10 min at 410 MB/s; 103 T1 transitions / 7,653 s in SMART (measured) | log per second, flag > 75 C, signature "heat" | smart-log per take with the thermal counters; `critical_warning` seen within a take, not at dawn; mode order rotated (F5) |
| Hung / dead controller | three `CSTS=0xffffffff` / `Disabling device` events, one needing a reboot (measured) | watchdog stops the night, Pi stays on, Patrik decides | right. Add: the volume is then dirty: `fsck.exfat -n` before anything resumes (F1, F2); the owner's footage is not on the card |
| Full card | capacity guard 6 GiB; fill gate 1.03 x planned + 10 GB | yes | the model replaced by the measured mean after the first take (§3) is right; nothing missing |
| Core crash mid-take | systemd restarts Core; `/run` drop-in survives | "Core error" stops the night | a PID change without a crash (restart by systemd) needs a warm-up and a void check (F15) |
| Pi reset (under-voltage) | 2026-11-06 twice; "Voltage normalised" = a dip below ~4.63 V (web) | S0 power check; under-voltage = stop the night; "resume once if clean" | the `/run` drop-in is gone: never resume into the default environment (F2) |
| Runner dies | sampler thread death seen in code (R10 §7.5) | `finally` with `record_stop` (A6) | SIGKILL / OOM / hang: heartbeat + independent stop (F4) |
| Audio fault | 1 in 9 takes on the new base ends the take (measured) | own outcome, repeat once, two = stop | fix before the long tiers; per-arm tabulation (F3) |
| WebUI client lost | Mac stand-in over Wi-Fi | void; second void stops the night | a WAIT state (F8) |
| A timer fires | `fstrim.timer` weekly (Debian default, unconfirmed here) | - | mask for the nights (F11) |
| Wrong card mounted | the T7 was on `/media/RAW` at the 13:00 boot (measured) | serial check per evening; void | right; add "a folder not in the database -> stop" (F1) |

## 4. Monitoring at 03:00 over ssh

What the owner sees with `cat ~/longtakes/<run>/status.md` is what v2 §9 lists, which is the right content. What he cannot see: whether
the runner is alive (F4), what the runner will do when the current take ends (F12), when the night ends, and whether the card throttled
during the running take (F5: the hwmon series is in the sample CSV, not in the status until the take ends; a "last sample: 68 C, buffer
3 %, 14,200 files" line written every 60 s to `/run/heartbeat` is cheap and does not touch the SD card). The "never during a take" list
(§9) is right; add the shell's own side effects: no tab completion inside `/media/RAW`, no `du`, no `find`; one `cat`, one `ssh` session,
and log out. `decisions.log` is right as designed.

## 5. Real-use fidelity

Fixed and as the owner shoots: peaking + zebra, the touch UI, audio on, WebUI on (via the stand-in: approximate, F8), TDN off (judged
acceptable 2026-11-04 20:26, `findings-evening4-supervised-2026-11-04.md:53`), depth 4, `sync`, 8 buffers, trim on. Deviations: pre-roll
OFF (direction: pessimistic at take start; F17), the merge worker OFF (direction: optimistic between takes if the split variant wins;
F10), the stand-in instead of a browser (R1 §4.3), no libcamera log (right), the 1 Hz sampler (A7 makes it light; the hwmon read per
second is an admin command the owner's shoots do not make, `preregistration.md:615-617`; keep it, record it). The campaign therefore
measures a slightly colder start and a slightly quieter between-takes state than real use: say so in the claims table.

## 6. Time and presence

Critic's model from v2's take counts: S2 ~45 scored takes and ~10 warm-ups at ~4.5 min each with failures shorter: 3.5-4.5 h; S3 0.5 h
(or 0 if folded, F9); S4 ~1.2 h; S5 three 30-min takes with warm deletes (seconds), trims (0.5 s) and the 60-s waits: ~2 h; S6 ~2 h plus
conditional work; Part B ~2 h per card plus the offload of the owner's footage (hours, Patrik). Pi time ~14-18 h plus Part B; v2's
"about 20 h" holds. Patrik: the build evening (~2 h), S0 (~2 h, sudo), the first hour of night 1 (F16), card swaps, any reboot. Not
"the start of each night". The Mac must stay up every night (the stand-in): a wired Mac or a second always-on host.

## 7. What v2 gets right and must not be lost

- The move to the Corsair cards removes the Kingston's unknown post-cache floor (R8: probable 0.4-0.8 GB/s) from the design: every heavy
  long take is now a camera test as long as the card is an MN/MNR2 (TLC) and the link is the ceiling; keep the part-number check.
- Stop-on-drop at every tier, two concordant takes per screening decision, the warm-up after every restart and mode switch, the pooled
  controls and the ABBA replicate, the regime rule, the claims table with the 3/n bound, buffer_full in seconds of input, the budget held
  at the record's 0.6 / 512.
- The physical fill gate with fill as a covariate, the near-full condition tested rather than avoided, clips deleted in the boot that
  wrote them and the cold delete budgeted from the measured slope.
- Temperature logged every second and never gated (R6), with the pre-registered attribution signatures (directory / drive state / heat /
  page cache / capture).
- Unsplit first at 30 min and the soak as the split variant; MLV as a conditional diagnostic only.
- The stop-the-night list (critical_warning, kernel nvme/pcie/exFAT lines, Core error, media_alive, under-voltage, a second void) with
  "restore, write the status, leave the Pi on, Patrik decides": no automatic reboot.
- The audio watch's columns (ring, backlog, discontinuities, drift, errors) and `audio_fault` as its own outcome; the desk read of
  `AudioRecordingSession.cpp` first.
- The wear ledger with the cap and the projection before every take; "never repeat a 30-min take to make sure unless void"; the order
  in which the budget shrinks (S3 first).
- The status file and decision log written atomically only between takes; the one small read from ssh; nothing else on the Pi during a
  take.
- The exact-command sudoers pattern and "Patrik installs every helper from reviewed text" (narrow it per F7, do not drop it).
