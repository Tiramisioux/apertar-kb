# Handoff: Tier 1 of the drop-frames campaign, evening 3 (Opus lead in VS Code, Sonnet workers)

For: a Claude Code session in VS Code on the Mac, model Opus, with the `apertar-dev` skill, working with Patrik and
driving the Pi over `ssh apertar`. Written 2026-11-03 by the cloud session that did Tier 0 and prepared Tier 1. It
replaces the prompt at the end of `handoff-drop-frames-tests.md` (that file stays the record of evenings 1 and 2). Paste the
block below as the first message, or say "read `~/Documents/Apertar/apertar-kb/working/handoff-drop-frames-tier1.md` and
start".

Before pasting: KB PRs #6, #7 and #8 are merged on GitHub; `git -C ~/Documents/Apertar/apertar-kb pull` on the Mac and
`git -C ~/apertar-kb pull` on the Pi (or `apertar_publish.sh kb`), so both have `tier1-prep-2026-11-03.md`, `tdn_strip.py`
and the new `be_overlap.py` / `take3v3.sh`.

---

```text
/apertar-dev You are the test lead for evening 3 of the Apertar drop-frames campaign: Tier 1. You decide, drive the Pi
and read every result against the pre-registered rules. You hand bounded, mechanical jobs to Sonnet workers (Agent tool,
model "sonnet") and review everything they return. Patrik decides anything the plan marks as his.

READ FIRST, in this order (Mac: ~/Documents/Apertar/apertar-kb/; on the Pi the KB is ~/apertar-kb/):
1. working/drop-frames/tests-2026-11/tier1-prep-2026-11-03.md, all of it. This is tonight's plan: the copy (section 3),
   selecting and restoring the tuning (section 4), the pre-registration of the TDN block (section 5), the conditional 27-fps
   unit (section 6), target 2 (section 7), the checklist (section 8). Where this prompt and the plan disagree, the plan
   wins; say so.
2. working/drop-frames/tests-2026-11/tier0-2026-11-03.md: why the plan looks like this.
3. working/drop-frames/tests-2026-11/findings-2026-11-03.md and, in working/handoff-drop-frames-tests.md, the sections
   "State after evening 2" and "Desk analysis after evening 2".
4. working/handoff-drop-frames-fable.md, the block after the line: Patrik's rules. They still hold.
5. llm/README.md sections 2 and 5 before reading any code.
Then run ~/.claude/skills/apertar-dev/scripts/apertar_status.sh and report: Core and UI tips on the Mac, the Pi and GitHub
(expected: Core drop-frames on the Pi 31d5418 built, GitHub adac040; UI on the Pi c153c33, GitHub c13b846), what runs on
the Pi, the drive fill, the uptime, and whether the Pi's KB has tier1-prep-2026-11-03.md and working/tools/tdn_strip.py.
Stop and say so if any of it differs.

THE TARGETS (Patrik's): (1) 4K Clear HDR 16-bit uncompressed cDNG at 25 fps, 0 lost frames, with the touch UI showing the
live picture with focus peaking and zebra on; (2) 4K SDR 12-bit at 33 fps. Neither is met yet.

WHERE THINGS STAND (measured unless marked):
- Every losing take is libcamera's ISP back end (BE) slowing under memory contention: frames queue in front of it, the 8
  raw buffers are held, the CFE drops. Not cured by 16 raw buffers, a 12-fps UI preview, buffer=frames or sysctls.
- Tier 0 (desk): the BE job (S2) is ~13 ms alone and 33-40 ms when the next HDR16 frame's 16-bit byte swap (8-10 ms) and
  RawStats (6-7 ms) run on libcamera's thread during it. A take tips into saturation once its jobs pass ~23 ms at 25 fps
  (~20 ms at 27), where the next frame's swap begins (probable mechanism; the clean take had 11 % of its jobs past it, the
  saturated ones 95-97 %). No 1 Hz system counter tracks S2 inside a take.
- Patrik: grep -c '"tdn"' on the Clear HDR tuning = 3, so TDN (temporal denoise, ~65 % of the BE's bytes) is on; the 16-bit
  swap must stay; 4K Clear HDR 16-bit tops out at 27 fps on the Pi (the 31d5418 fork-log row says 30: correct it).
- SDR12 has no swap and no software stats (dequeue to BE start 0.3-0.4 ms, S2 6-11 ms): its threshold at 33 fps is ~30 ms.

TONIGHT (tier1-prep section 8 is the step list; about 3 h without target 2, 4-4.5 h with it):
1. Ask Patrik: design A (2 TDN-off + 2 TDN-on units, order by his die roll, ~100 min with the warm-up) or B (N F N, ~80
   min); whether target 2 runs tonight (it writes ~0.35-0.4 TB: free space, formatting are his); when he can reboot.
2. Patrik reboots (it clears every /run drop-in, including the 12-fps UI one). Then the "before" records and the copy
   (sections 4 and 3, no sudo). Fill the section 5 entry (SDN values, design, order), append it to preregistration.md,
   commit and push it before the warm-up.
3. Patrik: the libcamera-log drop-in and b1-arm.sh sync --trace-buffer (section 8 step 3, exact block).
4. Warm-up, then the units in the pre-registered order (section 8 step 5): per unit b1-arm.sh sync (Patrik), the unit's
   tuning, ST and J on the new PID, the evening-2 loop, P1 + P2 of 3 min. Cut the libcamera windows and copy the files off
   /run BEFORE the next Core restart. Void checks BEFORE the analysis, from the checks alone.
5. be_overlap.py <dir> --prefix e3 on a copy on the Mac; the reading against the rule; the permutation tests (design A).
6. Only after "Support with margin": the 27-fps unit (section 6).
7. Restore the tuning to automatic and read it back against the "before" records (section 4).
8. Target 2 (section 7) if Patrik said yes.
9. Restore list (with the new tuning item) read back, smart-log, then findings-2026-11-04.md, takes.md rows,
   raw-2026-11-04.tgz, and "State after evening 3" at the end of this handoff file.
Re-plan only through the rule's outcomes; tell Patrik in one paragraph what changed and why.

AFTER TONIGHT, by outcome (not tonight's work; for the next plan):
- Support (with margin, and the 27-fps unit holds): TDN-off becomes a candidate default (Patrik's call: the preview is
  noisier); a second block on another evening for the stratified test; then B6-style 10-min takes for target 1 (its
  done-means: five 10-min takes on two boots, inspection-2026-11-02.md section 8.3 B6).
- Refute: desk design of the Tier 2 libcamera-fork change that keeps the swap and RawStats off the BE job (RawStats inside
  the swap pass, or a new frame's swap and RawStats held until the running BE job ends); O_DIRECT for the DNG writes (T24).
- Partial: the same Tier 2 change, with TDN-off as its companion.
- BE relieved, losses elsewhere: section 1's queue, S1, S3, S4, cycle and the trace first.
- Deferred whatever happens: B3's sysctl cells, U1, B8, B5, T2; last B6 (unless Support) and B-lossy.

WHAT YOU DO YOURSELF (never a worker):
- Every command on the Pi, including read-only ones and cutting the logs. A worker never touches the Pi (no ssh, no scp):
  a worker's ssh during a take breaks "nothing else on the Pi". Copy files to the Mac yourself for the workers.
- Asking Patrik for the design and the die roll; writing the order into the entry before the first unit; void decisions
  (from the checks alone, before any analysis); whether a conditional unit runs.
- Every reading against the rule, labelled measured / probable / unconfirmed, and every message and sudo block to Patrik.
- Reviewing every worker result before it goes into the KB; commits, fork-log rows, pushes (Core/UI to GitHub only when
  Patrik asks).

WORKER JOBS (Sonnet; one job per worker; give each the preamble below, the job's paragraph and the plan section):
W1 Copy check: tdn_strip.py's output and the diff you pasted, against tier1-prep section 3's checks; pass/fail per item.
W2 Analysis: given a Mac directory holding e3-<unit>.out, take-e3-<unit>-P1/P2.log and <unit>-P1/P2.log (the windows you
   cut), run python3 -I ~/Documents/Apertar/apertar-kb/working/tools/be_overlap.py <dir> --prefix e3 and return the full
   output and any warning lines.
W3 Void checks: from the .out files, the windows and be-cfg-<unit>.json, the section 5 void list item by item; pass/fail
   with the line that decides each. You decide.
W4 Table rows: section 5's table from be_overlap.py's output and the "recording clip:" lines, numbers only.
W5 Permutation test (design A): exact one-sided test F < N on P2 queued share and on P1 + P2 lost over the 4 units; return
   both p values and every ordering's statistic. Pure Python.
W6 takes.md rows per its column definitions, from the console and the 1 Hz logs; no interpretation.
W7 Restore check: from the outputs you paste (ST, J, the libcamera line, the settings-file grep, Core's environ, the
   restore list readback), pass/fail per item of tier1-prep section 4 and the restore list.
W8 Archive: from the Mac copies, raw-2026-11-04.tgz with every console, 1 Hz log, libcamera window, G1 file, BE config dump
   and trace; return the listing.

Preamble for every worker:
  You are a worker on the Apertar drop-frames campaign, on the Mac. Repos: ~/Documents/Apertar/Apertar-Core,
  ~/Documents/Apertar/Apertar-UI, ~/Documents/Apertar/apertar-kb. Do exactly the job described, nothing else. Never run
  anything on the Pi (no ssh, no scp), never push, never use sudo, never delete anything outside the paths the job names.
  Commit only if the job says so. Return: the files you touched or read, the full output of what you ran, and anything that
  differed from what the job assumed. No interpretation of results.

RULES THAT MATTER MOST (the full lists: the fable handoff, inspection section 8.3, tier1-prep section 5):
- Patrik runs every sudo command; give him exact blocks. After a reboot sudo asks for his password.
- Nothing else on the Pi during a take (check cc1plus|gmake|cmake before and after); the WebUI closed (the script refuses).
- Delete only a take's own clip folder, read from its "recording clip:" line; never a cDNG_* glob.
- Never edit defaults-pisp; never use disable_tdn; load or save no presets tonight; the tuning back to automatic before
  target 2 and before the Pi goes back.
- Never write /proc/irq/*/smp_affinity for RP1 interrupts; no hot-unplug of the NeoRotary.
- NVMe at or below 40 C at P1's start; stop on any smart-log critical_warning != 0.
- Pre-register before the takes and never change a rule after seeing data: a change is a listed deviation.
- At the end: the restore list read back, so Patrik's next shoot inherits nothing (ladder on at 30 fps, tuning automatic).
- Commits: "<area>: <imperative>", Why/What/Tested, Co-Authored-By trailer, "User" not names, one per change, a fork-log row
  per Core/UI commit. KB claims labelled confirmed / measured / probable; a hardware-log entry only after Patrik confirms.
  Never put passwords or tokens in the KB or in commits.
- Prefer extending an existing knob or script to adding one.

OPEN FOR PATRIK (from evening 2, still open): the ladder (rung 2 reads SDR12 <= 50 uncompressed, 11-02 had <= 30 lossless;
rung 1 HDR16 lossless encodes at ~17 fps); the two test clips cDNG_26_11_03_20533423_C0001 and
cDNG_26_11_03_20571717_C0001 on his Crucial P310 card (pulled while mounted): delete only those, after a read-only
fsck.exfat -n; the 12-fps UI drop-in goes with the reboot.

START: report the status check. Then ask Patrik the questions in TONIGHT step 1 and the open items. Run nothing on the Pi
beyond the status check until he has answered; then follow tier1-prep section 8 from step 1 (reboot, then the "before"
records and the copy).

REPORT TO PATRIK AT THE END: per take lost / enqueued, S2 median, isolated S2, jobs past the threshold, queued and largest
20-s queued share, CPU per frame; the reading against each rule and the tests; what it means for targets 1 and 2; the
state of the Pi after the restore.
```

---

## State after evening 3

(The lead writes it here at the end of the evening: result, state of the Pi, open for Patrik, next.)
