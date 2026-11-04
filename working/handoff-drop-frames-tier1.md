# Handoff: Tier 1 of the drop-frames campaign, evening 3 (Opus lead in VS Code, Sonnet workers)

For: a Claude Code session in VS Code on the Mac, model Opus, with the `apertar-dev` skill, working with Patrik and
driving the Pi over `ssh apertar`. Written 2026-11-03 by the cloud session that did Tier 0 and prepared Tier 1; revised the
same evening after two independent reviews (fidelity, and a walk-through as a fresh lead). It replaces the prompt at the
end of `handoff-drop-frames-tests.md` (that file stays the record of evenings 1 and 2). Paste the block below as the first
message, or say "read `~/Documents/Apertar/apertar-kb/working/handoff-drop-frames-tier1.md` and start".

Before pasting: KB PRs #6-#9 and the PR carrying this revision are merged on GitHub; pull on the Mac
(`git -C ~/Documents/Apertar/apertar-kb pull`) and on the Pi (`git -C ~/apertar-kb pull`, or `apertar_publish.sh kb`).

---

```text
/apertar-dev You are the test lead for evening 3 of the Apertar drop-frames campaign: Tier 1. You decide, drive the Pi
and read every result against the pre-registered rules. You hand bounded, mechanical jobs to Sonnet workers (Agent tool,
model "sonnet") and review everything they return. Patrik decides anything the plan marks as his.

READ FIRST, in this order (Mac: ~/Documents/Apertar/apertar-kb/; on the Pi the KB is ~/apertar-kb/):
1. working/drop-frames/tests-2026-11/tier1-prep-2026-11-03.md, all of it. This is tonight's plan: the copy (section 3),
   selecting and restoring the tuning (section 4), the pre-registration of the TDN block (section 5), the conditional
   27-fps unit (section 6), target 2 (section 7), the checklist (section 8, steps 1-13). Where this prompt and the plan
   disagree, the plan wins; say so.
2. working/drop-frames/tests-2026-11/tier0-2026-11-03.md: why the plan looks like this.
3. working/drop-frames/tests-2026-11/findings-2026-11-03.md; in working/handoff-drop-frames-tests.md the sections "State
   after evening 2" and "Desk analysis after evening 2", and lines 156-168 (the unit loop as it was; /dev/shm there now
   means /run/apertar-media).
4. working/drop-frames/tests-2026-11/preregistration.md: the evening-2 entries (the format you append to) and the restore
   list (lines 64-92); takes.md's column notes (lines 13-23).
5. working/handoff-drop-frames-fable.md, the block after the line: Patrik's rules. They still hold.
6. llm/README.md sections 2 and 5 before reading any code.
Then run ~/.claude/skills/apertar-dev/scripts/apertar_status.sh and report: Core and UI tips on the Mac, the Pi and GitHub
(expected: Core drop-frames on the Pi 31d5418 built, GitHub adac040; UI on the Pi c153c33, GitHub c13b846; the Mac's tips
are not recorded in the KB: report them, they are not a stop condition), what runs on the Pi, the drive fill, the uptime,
and the KB HEAD on the Mac and the Pi (git -C <kb> rev-parse --short HEAD) against GitHub main. Stop and say so if the
Pi's tips or the KB HEADs differ.

THE TARGETS (Patrik's): (1) 4K Clear HDR 16-bit uncompressed cDNG at 25 fps, 0 lost frames, with the touch UI showing the
live picture at full rate with focus peaking and zebra on; (2) 4K SDR 12-bit at 33 fps. Neither is met yet.

WHERE THINGS STAND:
- Every losing take with libcamera's log (8 of 8, 8 raw buffers) is the ISP back end (BE) slowing: frames queue in front of
  it, the 8 raw buffers are held, the CFE drops (measured). Memory contention is the probable cause; two dd memory loads
  reproduce it without recording (measured). At 16 buffers losses came without CFE starvation (a second loss path,
  unconfirmed). Not cured by 16 raw buffers, a 12-fps UI preview or buffer=frames (measured, n = 1 unit each). Sysctls
  were stock in every take: B3's cells are untested and deferred (reclaim is a co-factor, probable).
- Tier 0 (desk, measured): the BE job (S2) is ~13 ms alone and 33-40 ms when the next HDR16 frame's 16-bit byte swap
  (8-10 ms) and RawStats (6-7 ms) run on libcamera's thread during it; no 1 Hz system counter tracks S2 inside a take.
  Probable mechanism: a take tips into saturation once its jobs pass ~23 ms at 25 fps (~20 ms at 27), where the next
  frame's swap begins (the clean take had 11 % of its jobs past it, the saturated ones 95-97 %).
- Patrik: grep -c '"tdn"' on the Clear HDR tuning = 3 (measured), so TDN was on in every HDR16 take (probable, strong; TDN
  is ~37.6 of the BE's ~57.6 MB per frame, a libpisp simulation, probable); the 16-bit swap must stay; 4K Clear HDR
  16-bit tops out at 27 fps on the Pi (the 31d5418 fork-log row says 30: correct it).
- SDR12, measured only in preview at 30 fps (61-63 frames per evening-2 window, never recording): no swap, no software
  stats (dequeue to BE start 0.3-0.4 ms), S2 6-11 ms; so its threshold at 33 fps is near 30 ms (arithmetic). Under 2 x dd
  its BE doubled (23.7 ms) without loss.

TONIGHT: follow tier1-prep section 8, steps 1-13, in order. The points that are easy to get wrong:
- Step 1 is one message to Patrik with every question: design A (2 TDN-off + 2 TDN-on units, ~100 min with the warm-up,
  per the plan) or B (N F N; not estimated in the plan, roughly 80 min), and for A his die roll; whether target 2 runs
  (~0.25 TB for the uncompressed take plus the lossless one, up to ~0.5 TB per the inspection's B7 row; free space and
  formatting are his); when he can reboot; that the test card is in the slot; his three clips of 11-03 21:57-22:00 on it;
  OK to push tonight's KB commits; when the fsck of his Crucial card runs. Run nothing on the Pi beyond the status check
  until he has answered.
- The die's order goes into the entry before its commit; the warm-up runs on the first unit's arm; the 27-fps unit runs
  only if every F unit reads Support with margin.
- Every b1-arm.sh run leaves a b1-trace file that blocks the unit loop: copy it, then rm it by name.
- Delete the warm-up's and every take's own clip folder (exact path from its "recording clip:" line) before the next P1:
  a P1 above 2 % fill voids the unit.
- Run every take in the background (run_in_background with a timeout longer than the unit, or setsid nohup on the Pi); a
  killed take3v3.sh never sends record_stop; if a take script dies, send record_stop at once.
- Per unit: J until the new PID's line, then the switch, then ST and J. Cut the libcamera windows and copy every file off
  /run BEFORE the next Core restart (each b1-arm.sh run, and the final restore).
- Void decisions from the checks alone (W3), before any analysis (W2).
Re-plan only through the rule's outcomes; tell Patrik in one paragraph what changed and why.

AFTER TONIGHT, by outcome (for the next plan, not tonight's work):
- Support with margin: TDN-off is a candidate, a default only after a second block on another evening (stratified,
  minimum p 1/36; Patrik's call: the preview is noisier); then B6-style 10-min takes at 25 fps for target 1 (done-means:
  five 10-min takes on two boots, inspection-2026-11-02.md section 8.3 B6). If the 27-fps unit also meets Support, 27 fps
  with TDN off is a B6 candidate too (n = 1).
- Refute: desk design of the Tier 2 libcamera-fork change that keeps the swap and RawStats off the BE job (RawStats inside
  the swap pass, or a new frame's swap and RawStats held until the running BE job ends); O_DIRECT for the DNG writes (T24).
- Partial: the same Tier 2 change, with TDN-off as its companion.
- BE relieved, losses elsewhere: section 1's queue, S1, S3, S4, cycle and the trace first.
- Inconclusive: no TDN effect shown; the rule decides no next step.
- Deferred whatever happens: B3's sysctl cells, U1, B8, B5, T2; last B6 (unless Support) and B-lossy.

WHAT YOU DO YOURSELF (never a worker):
- Every command on the Pi, including read-only ones, cutting the logs and deleting clip folders. A worker never touches
  the Pi (no ssh, no scp): a worker's ssh during a take breaks "nothing else on the Pi". Copy files to the Mac for them.
- The questions to Patrik, writing the drawn order into the entry, void decisions, whether a conditional unit runs.
- Every reading against the rule, labelled measured / probable / unconfirmed; every message and sudo block to Patrik.
- Reviewing every worker result before it goes into the KB; commits, fork-log rows, pushes.

WORKER JOBS (Sonnet; one job per worker; give each the preamble below, the job's paragraph and the plan section):
W1 Copy check: the whole output of tier1-prep section 3 that you paste (md5sum before and after, the size against
   134,888 B, tdn_strip.py's output, the diff, the grep counts, the target), against section 3's checks; pass/fail per item.
W3 Void checks (before W2): from e3-<unit>.out, the windows, be-cfg-<unit>.json with its mtime and the Pi outputs you paste
   (ST and J after the switch, grep -c '"tdn"' on the copy and on any .cache/apertar-prores profile, the loop's serial,
   warm.bin, NVMe, df and MemFree lines), the section 5 void list item by item; pass/fail with the deciding line (Core's fps
   is the first fps= on the mode: line). You decide, then W2 runs.
W2 Analysis: given a Mac directory holding e3-<unit>.out, take-e3-<unit>-P1/P2.log and <unit>-P1/P2.log, run
   python3 -I ~/Documents/Apertar/apertar-kb/working/tools/be_overlap.py <dir> --prefix e3 and return the full output.
   You read its clock-offset and job-count lines for the back-end-readout void yourself.
W4 Table rows: section 5's table from be_overlap.py's output, the "recording clip:" lines and the .out files (Note column),
   numbers only.
W5 Permutation test (design A): extend working/tools/drop-frames-2026-11-01/b1_test.py (it already does the exact
   one-sided stratified test with a self-test) for F vs N with one block: statistics P2 queued share and P1 + P2 lost;
   complete separation in one block must give p = 1/6; return both p values and every relabeling's statistic.
W6 takes.md rows per its column definitions, from the console and the 1 Hz logs; no interpretation.
W7 Restore check: from the outputs you paste (ST, J, the libcamera line, the settings-file grep against the "before"
   record, Core's environ, the restore list read back), pass/fail per item of tier1-prep section 4 and the restore list.
W8 Archive: from the Mac copies, working/drop-frames/tests-2026-11/raw-<evening date>.tgz with every console, 1 Hz log,
   G1 file, libcamera window, BE config dump and trace; return the listing.

Preamble for every worker:
  You are a worker on the Apertar drop-frames campaign, on the Mac. Repos: ~/Documents/Apertar/Apertar-Core,
  ~/Documents/Apertar/Apertar-UI, ~/Documents/Apertar/apertar-kb. Do exactly the job described, nothing else. Never run
  anything on the Pi (no ssh, no scp), never push, never use sudo, never delete anything outside the paths the job names.
  Commit only if the job says so. Return: the files you touched or read, the full output of what you ran, and anything that
  differed from what the job assumed. No interpretation of results.

RULES THAT MATTER MOST (the full lists: the fable handoff, inspection section 8.3, tier1-prep section 5):
- Patrik runs every sudo command; give him exact blocks and say what changed after each step. After a reboot sudo asks for
  his password. New or changed root scripts go to him for review first.
- Nothing else on the Pi during a take (check cc1plus|gmake|cmake before and after); the WebUI closed (the script refuses).
- 3-min takes in the TDN units, 10-min takes in target 2; [storage] buffer=ram; watch the drive fill, Patrik decides when to
  format.
- Delete only a take's own clip folder, read from its "recording clip:" line; never a cDNG_* glob.
- Never edit defaults-pisp; never use disable_tdn; load or save no presets tonight; the tuning back to automatic before
  target 2 and before the Pi goes back.
- Never write /proc/irq/*/smp_affinity for RP1 interrupts; no hot-unplug of the NeoRotary.
- NVMe at or below 40 C at the start of every scored unit: P1 of each TDN or 27-fps unit (P2 starts hot by design) and
  each target-2 take. Stop on any smart-log critical_warning != 0.
- Pre-register before the takes and never change a rule after seeing data: a change is a listed deviation.
- At the end: the restore list read back, so Patrik's next shoot inherits nothing (ladder on at 30 fps, tuning automatic).
- Commits: "<area>: <imperative>", Why/What/Tested, Co-Authored-By trailer, "User" not names, one per change, a fork-log row
  for every fork commit (Core, UI, libcamera, driver). Push the KB pre-registration commit before the warm-up with
  Patrik's OK (step 1); every other push only when he asks. KB claims labelled confirmed / measured / probable; a
  hardware-log entry only after Patrik confirms. Never put passwords or tokens in the KB or in commits.
- Prefer extending an existing knob or script to adding one.

STOP AND ASK PATRIK: anything outside the plan; a void (tier1-prep section 5, decided from the checks alone); a take that
refuses to start (WebUI client, a build, NVMe not cooling, a b1-trace file left); a set_tuning_file reply that is not
{"ok":true... (an error carries "Could not apply tuning file: ..." and is not logged) or get_state "state": "error"; a
take script that died; smart-log critical_warning != 0; the drive near full; a result you would act on that the rule does
not cover.

OPEN FOR PATRIK (from evening 2): the ladder (rung 2 reads SDR12 <= 50 uncompressed, 11-02 had <= 30 lossless; rung 1
HDR16 lossless encodes at ~17 fps); his three clips on the test card (11-03 21:57-22:00, not test takes): keep, move or
delete, his call, by folder name, never a glob; the two test clips cDNG_26_11_03_20533423_C0001 and
cDNG_26_11_03_20571717_C0001 on his Crucial P310 card (pulled while mounted): delete only those, after a read-only
fsck.exfat -n (sudo, his card unmounted, before the reboot or after the restore, never during the block); the 12-fps UI
drop-in goes with the reboot; whether the preview noise with TDN off is acceptable (ask him to look during the F units).

START: report the status check. Then send Patrik the step-1 message. When he has answered, follow tier1-prep section 8
from step 2.

REPORT TO PATRIK AT THE END: per take lost / enqueued, S2 median, isolated S2, jobs past the threshold, queued and largest
20-s queued share, CPU per frame; the reading against each rule and the tests; what it means for targets 1 and 2; the
state of the Pi after the restore.
```

---

## State after evening 3 (2026-11-04, written by the lead session at ~04:55, unsupervised from ~01:35)

Read first: `drop-frames/tests-2026-11/findings-2026-11-04.md`, then the evening's sections of `preregistration.md`
(from "TDN off by a tuning copy, evening 3"). Raw data: `raw-2026-11-04.tgz` (reproduce with `tools/be_overlap.py <dir>
--prefix e3` per unit directory).

**Result:**
- **TDN off removes the back-end bottleneck at 25 fps** (Support with margin in both F units; permutation p = 1/6 on both
  statistics, probable): TDN on lost 58 + 39 and 115 + 116 (BE job ~37 ms, queued 0.91); TDN off 1 + 0 and 2 + 0 (BE job
  5.9 ms, queued 0.00). Target 1 is close but not met: the TDN-off P1 takes still lost 1-2 single frames each.
- **HDR16 with TDN off: clean to 27 fps (1 + 1 lost), onset at 28 (5 lost)**; the 28-fps losses are a second path: the CFE
  never ran out of buffers, each loss follows one 79-105 ms BE job (probable); its cause is unconfirmed.
- **Target 2 met**: 4K SDR 12-bit 33 fps, 10 min lossless 0 / 19,851 and 10 min uncompressed 0 / 19,857.

**State of the Pi at the end:** restore list read back (`findings` and `preregistration.md`): no `/run` drop-in for Core or
the UI, Core's environ only `LIBCAMERA_LOG_LEVELS=IPARPI:ERROR` from `/etc`, `buffer=ram`, tracefs restored by the helper
(events 0, buffer 1408 KB), sysctls stock, swap on (zram), link frequency 891 MHz, driver checkout `cd548ef`, tuning
automatic (`tuning_file ''`, settings file empty, `(sensor default, pisp)`), ladder on at 30 fps (`Resolution 1 ·
3840×2160 · ClearHDR16 · ≤30 · Lossless JPEG`). Drive: only `warm.bin` (1 %). smart-log `critical_warning` 0, 29.01 TB
written (+1.55 TB tonight). Core `9b5ea14` built and running (not on GitHub; the other session's WebUI commits). The TDN-off
copy stays at `/home/pi/Tuning-Files/imx585_clearHDR_notdn.json` (inert unless selected). **Powered off** at the end
(User's request).

**Open for User:**
- `sudo rm /etc/sudoers.d/apertar-b1-arm /usr/local/libexec/apertar-b1-arm` after booting (before any image is made).
- Look at the preview with TDN off (`set_tuning_file path=/home/pi/Tuning-Files/imx585_clearHDR_notdn.json`, back with
  `path=`): is the temporal noise acceptable? The DNGs do not depend on it.
- The ladder's rung 1 now reads ClearHDR16 ≤ 30 lossless (was ≤ 25 before `31d5418`; lossless HDR16 encodes at ~17 fps):
  your call.
- From evening 2, still open: the Crucial P310's `fsck.exfat -n` and its two test clips; the fork-log rows `fe5d592` /
  `c747f09` were rewritten by the other session as `1319967` / `b64e6f6` plus `9b5ea14` (fork log to fix with the sha).

**Next (by the pre-registered outcome "Support with margin"; to plan with User, nothing run):**
1. A second TDN block on another evening (another die roll, stratified test, minimum p 1/36), with User looking at the
   preview once per arm. If it holds: TDN off for Clear HDR 16-bit, the least intrusive way: a tuning file Core selects
   automatically for HDR16 (DTS), or `[camera]` tuning default, decided with User.
2. B6 at 25 fps TDN off: five 10-min takes on two boots (inspection 8.3 B6); 27 fps TDN off as a second B6 candidate.
3. The second loss path (1-2 frames per 3 min at 25, 5 at 28): log `csi2_errors` LEN / UNMATCHED and CFE frame start /
   end per second, time the CFE interrupt against the rare 80-105 ms BE jobs, and test the 1782 Mbps link question.
4. Deferred as before: B3's sysctl cells, U1, B8, B5, T2; Tier 2's swap/RawStats change is no longer first (the BE is
   relieved); O_DIRECT stays a candidate for the write path's CPU.

**Since evening 3 (User's own takes, 2026-11-04, unscored):** a 10-min 4K Clear HDR 16-bit 25 fps uncompressed take
without a lost frame, **with the WebUI open** (tuning not reported; probably the TDN-off copy); 4K HDR16 25 fps lossless
JPEG still drops frames (expected: the encoder's ~17.5 fps capacity, `README.md` finding 12); 4K SDR 12-bit at about 42
fps without dropped frames. Details and what is unconfirmed: `drop-frames/tests-2026-11/observations-2026-11-04.md`.
