# Handoff prompts for the storage-slowdown campaign (2026-11-08)

Two prompts for the Pi-side `/apertar-dev` sessions (VS Code, Claude Code on the Mac), written so that nobody has to answer a
question while they run. Plan: [../storage-slowdown-plan.md](../storage-slowdown-plan.md) (sections 4 and 7); the runner's
unattended rules: its section 7.1. Prompt A is the camera-free part (facts, the runner's smoke tests, the write-pattern probes);
prompt B is the camera ladder with the runner. The directory probe (plan S1) is done: [probe-exfat-dir.md](probe-exfat-dir.md),
c = 63.3 ns per directory entry (measured). The numbers in the prompts (budgets, modes, hours) are the plan's defaults; Patrik
changes them before pasting.

## Prompt A: camera-free stages, unsupervised

```text
/apertar-dev Run the storage-slowdown camera-free stages (facts, runner smoke tests, write-pattern probes) from apertar-kb main
(or the branch claude/practical-johnson-he481b if its PR has not merged) completely unsupervised: nobody answers questions during
the run. Every decision below is pre-made; anything not covered is recorded and skipped, never asked.

WHY: the SSD run's samples (working/drop-frames/tests-2026-11/reanalysis-longtakes-ssd-2026-11-08.md) show the late failures are a
cost that grows with the files in the clip folder (Core's CPU doubles in 30 min; the directory probe measured the exFAT walk at
63.3 ns per entry, working/drop-frames/nvme-campaign/probe-exfat-dir.md), the 4K ceiling on the T7 is Core's write pattern
(77-120 MB/s vs 354 raw), trim on the T7 was never recorded and the RAM budget varied five-fold. The revised campaign
(working/drop-frames/storage-slowdown-plan.md, sections 4 and 7) measures this without the camera first. Another session owns the
Core branch clip-split: do not duplicate it, do not touch Core source, and yield to it (the gate below).

PRE-APPROVED (by starting this prompt): writes of at most 220 GB on /media/RAW in probe_exfat_write_* folders that the probes delete
themselves; the runner smoke tests (a few 20-60 s takes, their clips deleted by the runner); ~/longtakes/bin/ on the Pi overwritten
with the KB's tools; results committed on the Mac to the KB. NOT approved: sudo, pushing, editing Core, touching any other folder
on the drive.

READ FIRST (Mac ~/Documents/Apertar/apertar-kb/): working/drop-frames/storage-slowdown-plan.md (all), the re-analysis page above
(sections 2-8), working/mac-driven-loop.md, the header docstrings of working/tools/longtakes.py, longtakes_fill.py,
exfat_write_probe.py, storage_facts.sh. Then ~/.claude/skills/apertar-dev/scripts/apertar_status.sh.

GATE (before every Pi step; poll every 2 min with one ssh line, give up and record after 6 h): no python process running an
exfat_*_probe.py or longtakes.py; ps -eo cmd | grep -cE "^[^ ]*(cc1plus|cc1|g\+\+|gcc|ld|collect2|make|cmake|ninja) " is 0;
get_state (python3 -I ~/apertar-kb/working/tools/core.py get_state) says state ready, standby false, recording false,
storage_preroll_active false, media_state mounted, ladder_enabled false; no /run/apertar-media/*.lock whose pid is alive and not
yours; no probe_exfat_* folder under /media/RAW younger than 10 min; vcgencmd get_throttled 0x0. While your own step runs, keep
/run/apertar-media/handoff-storage.lock with "pid=<pid> what=<step> planned_end=<time>" and remove it afterwards (the runner's gate
reads that convention). Detach every step longer than a minute with setsid nohup ... </dev/null & and poll its .out file.

STEP 1 (Mac): git fetch origin; check out the KB revision to use; scp working/tools/{longtakes.py,longtakes_fill.py,
exfat_write_probe.py,storage_facts.sh,webui_client.py} to pi:~/longtakes/bin/. Create the result page
working/drop-frames/nvme-campaign/write-pattern-probe.md now with a "status" line you update after each step.

STEP 2 (Pi, read-only, 2 min): bash ~/longtakes/bin/storage_facts.sh /media/RAW > /run/apertar-media/facts.out 2>&1; paste it into
the page. Root-only facts (smartctl temperature, filefrag extents, nvme id-ctrl) are recorded as "needs root: <command>" and the run
goes on. Then Core's own direct-write test instead of fio by hand: core.py run_media_speed_test, wait until core.py
get_media_test_state says running false, record mbps and used_fio.

STEP 3 (Pi, gate, ~10 min): the runner's smoke tests, one at a time, each detached and polled:
  a) python3 -I ~/longtakes/bin/longtakes.py --out ~/longtakes/smoke-$(date +%Y%m%d)-a --stages m --meter-seconds 20 --no-gate \
       --modes 2kSDR12
     Expect: capacity.md with two rows (unc, lossless), capacity_fps filled (how = fit, at least or stats), a DONE file, and
     get_state afterwards showing fps, format, compression, bit depth, resolution as before the run. Check samples/*.csv has the 23
     columns with buffer_used, buffer_capacity, dev_w_ios, dev_w_ticks, dirty_kb and trim_last_unix filled, and results.csv has
     queue_budget_mib, budget_seconds, recorder_stop_s, idle_gap_s, core_cpu_slope, trim_before, buffer_unit, capacity_fps,
     capacity_how, drain_mbps. If buffer_used is empty: curl -s http://127.0.0.1:8000/api/buffer, note Core's field names, fix only
     buffer_level() in longtakes.py (on the Pi and in the KB), rerun, at most three attempts; then record the gap and go on.
  b) the same --out again: expect it to exit at once with "already ended"; remove its DONE and run it again: expect every meter
     take skipped and a new DONE within a minute.
  c) python3 -I ~/longtakes/bin/longtakes.py --out ~/longtakes/smoke-$(date +%Y%m%d)-c --stages msLMkS --meter-seconds 20 \
       --long-seconds 60 --modes 2kSDR12 --no-gate --fix-budget
     Expect: one row per stage (meter x2, split30, split101-103, long30, mlv30, knob5000 and knob0 if Core has the knob, soak1-2),
     outcomes ab_clean or ab_dropped, the [storage] keys of /home/pi/apertar-hardware.conf as before (diff against a copy you take
     before), frames_per_folder and clip_merge as before, no cDNG_*/MLV_* folder of the run left on the drive, a DONE file.
  d) python3 -I ~/longtakes/bin/longtakes.py --out ~/longtakes/smoke-$(date +%Y%m%d)-d --stages 1 --max-seconds 20 --only 1 \
       --modes 2kSDR12 (the old fps ladder still works).
  Record each as measured. python3 -I ~/longtakes/bin/longtakes_fill.py <out> must run on every out dir.

STEP 4 (Pi, gate, ~10 min, ~26 GB): the write-pattern matrix on /media/RAW, 4K size, 300 files, one variant at a time, each detached:
  default | --workers 1 | --prealloc | --fsync none | --chunk-kb 0 | --chunk-kb 0 --prealloc --direct | --subdir 5000
  (all: python3 -I ~/longtakes/bin/exfat_write_probe.py --size-mb 12.4 --files 300 <variant> > /run/apertar-media/probe-<variant>.out)
Record per variant: the SUMMARY line (files/s, MB/s, p50/p90/p99/max ms), the device write ms from the last window line, whether
O_DIRECT was refused. 30 s after each folder deletion read curl -s http://127.0.0.1:8000/api/state and record
media_trim_last_result/bytes/ms/unix: that is the trim test (the delete frees >= 1 GiB at once, so Core requests a trim; result
"unsupported" means the T7 cannot be trimmed over its bridge). These fields are not in get_state.

STEP 5 (Pi, gate, ~1 h, ~180 GB): the paced 2K emulation of the 38 fps failure, flat then split:
  exfat_write_probe.py --size-mb 1.3 --fps 38 --seconds 1800 --budget-mb 800
  exfat_write_probe.py --size-mb 1.3 --fps 38 --seconds 1800 --budget-mb 800 --subdir 5000
Record the per-10 s lag curve (frames behind) of both and the minute the flat run reached BUFFER FULL, next to the camera's 1637 s.

STEP 6 (Mac): finish write-pattern-probe.md (facts, smoke results, the matrix table, the two lag curves, what each lever changed and
by how much, the trim result, labels measured/derived/unconfirmed, the raw .out and .csv names copied under nvme-campaign/raw/,
gzipped). Update storage-slowdown-plan.md section 3 rows M2/M3/M4 with the measured status. Commit: "drop-frames: write-pattern
probe and runner smoke tests on the T7" with Why/What/Tested and the usual trailer. Do not push. Leave a one-screen summary at the
top of the page for Patrik: what ran, what it changed, what still needs root.

RULES: never sudo; never a take or probe while anything else runs on the Pi (the gate); only probe_exfat_* and the runner's own clip
folders are ever deleted; do not edit Core, Tuning-Files, /etc or apertar-hardware.conf by hand (the runner's --fix-budget is the
one allowed edit, and it undoes it); if a step fails twice, record it and move on; if the runner stops with "needs a human" or
"watchdog" in runner.log, write it at the top of the page and stop. Label every claim.
```

## Prompt B: the camera ladder, unattended

```text
/apertar-dev Run the storage-slowdown camera ladder (plan section 7, stages S4, S5 and S7) unattended with the campaign runner from
apertar-kb (working/tools/longtakes.py, the revision Prompt A smoke-tested). Nobody answers questions during the run; the runner's
gate, watchdog and budget decide; a stop that needs a human is written to runner.log and the result page, and the session ends.

PRE-APPROVED: writes up to --budget-gb 3500 on /media/RAW in the runner's own clip folders (deleted after each take); the modes
2kSDR12 and 2kHDR16 (about 9 h and 3.5 TB in all); MLV takes as a diagnostic (stage M); the two [storage] RAM-budget keys set for the
run (--fix-budget; put back at the end); frames_per_folder and clip_merge switched by the knob stage and put back; one line in pi's
own crontab for the resume after a reset (removed at the end). NOT approved: sudo, pushing, Core changes, the Mode Ladder switch
(if it is on, the runner stops with needs_human: turn it off in the WebUI before starting), drive swaps, other modes.

PRECONDITIONS (check once, record): the Mode Ladder off (get_state ladder_enabled false), WebUI closed (ss -tn state established
'( sport = :8000 )' shows no remote client), the eight modes activated as in the SSD run (ladder_count 8), audio as configured,
/media/RAW mounted with >= 250 GB free (a 30-min 2K take writes ~210 GB), Core on cinemate-port 01f170c or newer (record the
commit; the knob stage needs set_frames_per_folder), Prompt A's smoke tests passed, ~/longtakes/bin/ holds the smoke-tested tools.

RUN (Pi, detached, resumable):
  cd ~/longtakes && touch AUTORESUME && (crontab -l 2>/dev/null; echo '@reboot sleep 120 && cd ~/longtakes && [ -f AUTORESUME ] && [ ! -f ladder/DONE ] && python3 -I bin/longtakes.py --out ~/longtakes/ladder --stages msLMkS --modes 2kSDR12,2kHDR16 --budget-gb 3500 --fix-budget >> ladder.out 2>&1') | crontab -
  setsid nohup python3 -I bin/longtakes.py --out ~/longtakes/ladder --stages msLMkS --modes 2kSDR12,2kHDR16 --budget-gb 3500 --fix-budget >> ladder.out 2>&1 </dev/null &
Stages: m = capacity meter (90 s per mode and variant; capacity.md), s = split test (1 x 30 min vs 3 x 10 min at 0.95 x capacity),
L = one 30-min take per mode at 0.9 x capacity, M = MLV control, k = frames_per_folder 5000 vs 0 (skipped by the runner when Core
lacks the knob), S = soak (the best clean 30-min fps twice). A mode whose capacity x 0.95 is below 25 fps is metered only. The runner
stops itself at the budget, on the watchdog, on a gate timeout (6 h) and on the Mode Ladder; it deletes only its own clips, holds
/run/apertar-media/longtakes.lock while a take runs, and writes ~/longtakes/ladder/DONE with the reason when it ends.
Poll ~/longtakes/ladder/runner.log and the DONE file no more than every 10 minutes (one ssh line). DONE with "all stages done" =
go to AFTER THE RUN. DONE with anything else ("needs a human", "watchdog", "budget", "gate_timeout") = record the reason, remove
AUTORESUME and the crontab line, write it at the top of the result page, stop. A reboot in between resumes the run by itself
(no DONE is written for SIGTERM); do not restart the runner by hand.

AFTER THE RUN: remove AUTORESUME and the crontab line; python3 -I bin/longtakes_fill.py ~/longtakes/ladder --tail 150 > fill.txt;
copy ladder/{results.csv,results.md,capacity.md,runner.log,longtakes.db,fill.txt,DONE} and samples/ journal/ (gzipped) to the Mac
KB under working/drop-frames/nvme-campaign/ladder-<date>/; write working/drop-frames/nvme-campaign/ladder-<date>.md: the capacity
table per mode and variant (and how it was read: fit, at least, stats); the split test's verdict per mode (3 x 10 clean and 1 x 30
failed = per-folder cost; both failed = drive or memory state; both clean = no time dependence at that fps); the long takes' buffer
and CPU curves (c from the CPU slope, compare with the directory probe's 63.3 ns); MLV vs cDNG at the same fps; the knob A/B if it
ran; soak repeatability; every claim labelled. Update storage-slowdown-plan.md section 3 statuses and section 9. Commit
"drop-frames: unattended storage ladder on <drive>" with Why/What/Tested and the trailer. Do not push; hardware-log entries only
after Patrik confirms the readings.

RULES: never sudo; nothing else on the Pi while the runner runs (its gate yields to builds and probes it can see; keep your own ssh
use to the poll); the runner restores Core's settings, the two [storage] keys and the knobs at the end; if it stopped mid-way, do
not restart it by hand; record and end.
```
