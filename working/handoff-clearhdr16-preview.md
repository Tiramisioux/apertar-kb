# Handoff: the 16-bit Clear HDR preview flicker, T55 with Patrik (Opus lead in VS Code, Sonnet workers)

For: a Claude Code session in VS Code **on the Mac** (not Remote-SSH on the Pi), main model Opus, with the `apertar-dev`
skill, working with Patrik and driving the Pi over `ssh apertar`. Written 2026-11-04 by the session that diagnosed the
flicker and wrote T55; revised the same evening after three independent reviews (fidelity, a walk-through as a fresh
lead, workers and safety). Paste the block below as the first message, or say "read
`~/Documents/Apertar/apertar-kb/working/handoff-clearhdr16-preview.md` and start".

Before pasting:
- Pick Opus for the session: click the model name under the prompt box, or type `/model`. Enter saves it as the default
  (`"model"` in `~/.claude/settings.json`, which the CLI and the VS Code extension share; it says `"opus"` today).
- Sonnet workers: the block tells the lead to pass `model: "sonnet"` on every Agent call, as in
  `handoff-boot-config.md`. That is best effort: Opus can still pass another model or use a fork (forks always run on
  the main model). The only setting Opus cannot override is the forced pair in the `env` block of
  `~/.claude/settings.json`: `"CLAUDE_CODE_SUBAGENT_MODEL": "claude-sonnet-5-5"` and
  `"CLAUDE_CODE_SUBAGENT_MODEL_FORCE": "1"` (Claude Code 2.1.257 or later; merge it into the file, don't replace it). It
  applies to every project on this Mac, workflow agents and Explore included, so add it only if you want that
  everywhere, and open a new conversation afterwards. Check with `/tasks`: each worker's row shows its model. (From the
  Claude Code docs, 2026-11-04; not tried here.)
- Type `/apertar` in the prompt box first to see the skill is offered. The docs don't say for certain that personal
  skills show in the VS Code `/` menu; if it isn't there, say "use the apertar-dev skill" in the first line instead.
- Why the Mac: Claude Code, the VS Code server and the C++ language server on the Pi take about 1.7 GB, the language
  server alone ~40 % of a core (`working/mac-driven-loop.md`): a confound for any preview or take judgement. T55 is also
  not in the Pi's `~/apertar-tutorials` mirror (`deploy_to_pi.sh` did not run on 11-03); the lead uses it from the Mac.

---

```text
/apertar-dev You lead the next round of the 16-bit Clear HDR preview work with Patrik: tutorial T55, "A steady 4K 16-bit
Clear HDR preview". Patrik watches the camera and runs the steps; you tutor (llm/tutoring.md §7: one step at a time, his
prediction first, hints before answers), check every result and keep the KB true. Hand bounded jobs to Sonnet workers
(Agent tool, model "sonnet", one worker per independent job, in parallel when independent) and review everything they
return before you rely on it or commit it. Patrik decides anything that changes the camera.

THE QUESTION. On HDMI the 4K Clear HDR 16-bit preview flickers and shows distortions; Cinemate's is calm on the same rig.
It is fixable in Apertar (every candidate cause sits in a tuning file, a UI setting or shader, a drop-in or the libcamera
fork), but nobody has seen yet which kind of flicker it is. T55 §3 names it with switches that already exist; §4 then
changes only the stage that makes it.

READ FIRST (Mac: ~/Documents/Apertar/apertar-kb/; never read the 8-12k-line source files whole, llm/README.md §2):
1. working/clearhdr16-preview.md: the diagnosis (10 causes, verdicts, what is confirmed, the Pi state on 11-03).
2. The T55 note: T=~/Documents/Apertar/apertar-kb/tutorials/tutorial.py; `python3 $T show T55` prints its Obsidian
   path, outline and checks. Read all of it.
3. working/drop-frames/tests-2026-11/findings-2026-11-04.md §1, §2 and §4, and working/handoff-drop-frames-tier1.md,
   section "State after evening 3" (its "Open for User" and "Next" lists).
4. working/drop-frames/tests-2026-11/tier1-prep-2026-11-03.md §3-§4 (how a tuning copy is made with
   working/tools/tdn_strip.py, and selected and restored with working/tools/core.py) and tier0-2026-11-03.md:72-76 (the
   back-end threshold is the next frame's swap, not the frame period).
5. llm/README.md §5, traps 18-20 (set_tuning_file applies in every mode, the WebUI draws its own aids, /run drop-ins).

WHAT CHANGED SINCE T55 WAS WRITTEN (2026-11-03 23:40)
| Fact | Numbers | Label |
| --- | --- | --- |
| Evening 3 (drop-frames Tier 1, 4K HDR16 25 fps uncompressed, recording, peaking and zebra on): TDN off | BE job ~37 -> 5.9 ms; lost 97 and 231 -> 1 and 2 per unit | probable (p = 1/6, one block) |
| HDR16 with TDN off, fps sweep, 3-min takes | 26 and 27 fps lost 0-1 per take, 28 lost 5; 29-30 not run | measured, n = 1 per step |
| The TDN-off copy | /home/pi/Tuning-Files/imx585_clearHDR_notdn.json, only the three "tdn" blocks removed, inert unless selected | confirmed |
| UI CPU per frame with TDN off | -20 to -24 % | measured |
| The preview with TDN off | nobody has looked at it: open for Patrik in both projects | - |
| Core on the Pi | 9b5ea14 on drop-frames (another session rebased its WebUI commits on 11-04: fe5d592/c747f09 are now 1319967/b64e6f6 plus 9b5ea14; fork-log rows still to fix, not yours). T55's refs follow it (21 OK) | confirmed |
| The camera since Core's start at 19:00 on 11-04 | ladder rung 1: 4K HDR16 at 30 fps, shutter 1/60 s (16667 us), Lossless JPEG, tuning automatic | confirmed (/api/state) |
| New tutorial numbers | the dual-sensor plan took T56-T70; read llm/tutoring.md §5 and tutorials/README.md before numbering | confirmed |
What it means (inference): for a flicker or judder that shows only during takes, H4 (late delivery under memory load) is
now the lead candidate and TDN off its likely cure, unconfirmed for the preview. At 30 fps a take saturates sooner than
at 25 (the swap threshold is ~23 ms at 25 fps, near 16 ms at 30), and 30 fps Lossless JPEG loses frames to the encoder
anyway (~17 fps for HDR16): so judge takes at 25 fps uncompressed, the setting evening 3 measured, and name the encoder
as its own cause, not a T55 row. At 1/60 s under 50 Hz mains lamps, banding or pumping can simply be mains flicker
(T55 3.3 has the row): one look at 1/50 or 1/100 s rules it out before any tuning copy.

START: plan step 1, then one message to Patrik with the plan step 2 questions.

PLAN
1. Status, read-only, yourself, in one ssh: `ssh apertar 'bash -s' <<'EOF' ... EOF` with, inside: curl -s -m 3
   http://127.0.0.1:8000/api/state | python3 -m json.tool | grep -E '"(recording|media_writes_pending|buffer_used|
   recording_dropped_frames|clear_hdr|raw_bit_depth|resolution|fps|shutter_us|cdng_compression|tuning_file|ladder_text|
   focus_peaking_enabled|zebra_enabled|zebra_threshold|external_monitor_mode)"' (the aids sit under "ui");
   systemctl show apertar-core apertar-ui-direct -p DropInPaths -p Environment -p ExecStart;
   pgrep -af '[c]c1plus|[c]make|[t]ake3v3|[t]akes\.sh|[b]1-arm|[c]laude' (the brackets stop pgrep matching its own
   command line); ss -tn state established '( sport = :8000 )' (a WebUI client changes the load); who (your own ssh is
   listed too); git -C ~/ApertarCore log -1 --oneline; git -C ~/drivers/imx585-v4l2-driver log -1 --oneline (cd548ef);
   grep imx585 /boot/firmware/config.txt (link-frequency 891000000). If a take, a build or another session's
   measurement is running, stop and ask Patrik which session owns the Pi tonight. Then `python3 $T refs T55` on the Mac;
   fix moved lines in the note. Record the Core, UI and driver shas with every T55 result.
2. Ask Patrik what he saw: idle or in a take; the fps, shutter and compression; mains lamps or daylight; HDMI only or the
   WebUI too; a still scene or pans. Then T55 3.1-3.3 with him, and route by the 3.3 row: only in takes -> 3.6, then the
   _notdn look in a 25 fps uncompressed take; idle speckles or blinking stripes -> 3.4; whole-picture pumping -> mains
   check first, then the CE copy; rolling bands under lamps -> the mains check. Open the WebUI (3.5) only when the row
   needs it: it adds load. Run `python3 $T check T55 <step>` while his switch is still on (3.4, 3.5, 3.7 and 3.8 test the
   switched state; a FAIL after he switches back is expected). 3.3 and 3.6 have no check line: verify those by hand,
   read-only, and add a check line to the note. Then `python3 $T log T55 <step> done "<what he saw>"` and commit
   tutorials/progress/T55.md.
3. Before he reaches §4, rewrite T55 §4 in the note (tutoring.md §7 allows it) and show Patrik the diff first:
   - 4.2-4.4: the existing _notdn copy first (unless 3.3 said pumping: then CE first). Only if it does not cure it, a
     copy with CE off, then one with ALSC off, one change per copy. Fix the tutor block's check 4.2-4.4 lines for those
     files (_notdn: '"tdn"' 0, '"ce_enable": 1' present, rpi.alsc present) and for tuning_file back to ''.
   - Patrik switches on the Pi with T55's curl line or `python3 -I ~/apertar-kb/working/tools/core.py set_tuning_file
     path=<file>`, back with `path=`. You read back from the Mac in one `ssh apertar 'bash -s' <<'EOF'` with tier1-prep
     §4's ST and J defined inside it, plus `grep -n tuning_file= ~/.config/apertar-core/camera_settings.conf`. Skip its
     libcamera-e3.log line: that debug log existed only on evening 3.
   - 4.5 (editing imx585_clearHDR.json) is deferred, marked as such in the note. A permanent TDN-off is the drop-frames
     handoff's "Next 1": a second TDN block first, then the least intrusive form (a tuning Core selects for HDR16 only,
     or a [camera] tuning default), decided with Patrik. imx585_clearHDR.json also serves 12-bit Clear HDR and Clear HDR
     stills. You do not run the second TDN block; takes here are not block units and go in no pre-registration table.
     Offer T55's look as Next 1's "User looks at the preview once per arm".
4. If §3 points at the aids (3.4): T55 4.6 is settings only (zebra 0.90; peaking 0.20 or off). The code follow-ups
   (upstream-issues #45 zebra rule, #24 peaking step) become a tutorial only if Patrik wants one.
5. If §3 points at HDMI-only damage with the aids off, at the raw, or at nothing: T55 §7. Root-only reads (rp1-cfe
   csi2_errors, /sys/kernel/debug/dri) are Patrik's: give him exact commands and ask first; if he reads csi2_errors, note
   the counts and the time for drop-frames Next 3.

SONNET WORKERS. Workers never touch the Pi: no ssh, no scp, no tutorial.py refs or check, no sudo, no push. You run
every Pi command yourself, after the step-1 status shows no take or measurement, and copy what they need into your
session scratchpad. Brief each fully (it sees only its prompt): the files, the goal, what is done, how to check its
work, what not to touch.
- tool: `working/tools/tuning_variant.py --ce-off | --alsc-off SRC DST`, a sibling of tdn_strip.py with its refusals
  and atomic write, comparing algorithms by name, not by list index (tdn_strip.py's leaves() keys list items by index,
  so dropping rpi.alsc would look like changes everywhere). You first copy the source: scp
  apertar:Tuning-Files/defaults-pisp/imx585_clearHDR.json <scratchpad>/ (134,888 B, md5 f53de0fe...). Checks: --ce-off
  changes only the ce_enable line; --alsc-off removes only the rpi.alsc entry (13 -> 12 algorithms, every other one
  deep-equal by name); strict JSON, "target": "pisp", version kept, source md5 unchanged; tdn_strip.py on the same
  source still gives the _notdn file. You review it and commit it in the KB before Patrik runs it on the Pi.
- dng (only if §3 ends at "the raw" or "nothing helps", or Patrik asks): you copy two consecutive mid-take DNGs to the
  scratchpad only when /api/state shows "recording":false, "media_writes_pending":false and "buffer_used":0 (takes are
  /media/RAW/<clip>/; the clip name is in the take's `ApertarCore recording clip:` journal line). The worker decodes with
  rawpy (installed on the Mac; raw_image, not raw_image_visible; shape (2160, 3840); raw_pattern against the CFAPattern
  tag and black_level_per_channel against BlackLevel, read with exiftool) in a new read-only script in the scratchpad
  (dngmeasure.py measures only a centre band of uncompressed DNGs). It reports per row and per CFA channel (row parity x
  column parity), steps between same-colour rows (n and n+2), and rows 0-31 and 2128-2159 against the median row (a band
  near the ~3200 black level means OB or margin rows in the DNG: a finding). For Apertar's own merge clamp (open H2
  item, Cinemate's was 47,808-55,381 at 4K): per channel the max code, the count at it and within 16 codes, and the 20
  highest distinct codes with counts; a pile-up below 65535 in both frames is the clamp (WhiteLevel 65535 is not). Ask
  Patrik for a take with something blown in frame if he wants the clamp.
- journal: you run `journalctl -b -u apertar-core --no-pager | grep -E 'ApertarCore (recording clip:|recording stats:|
  drop\[|camera configured:|tuning file:)' | tail -200` and give the worker the lines between the take's `recording
  clip:` and its `recording stats:`, plus the last configured and tuning lines before it. It returns a table: lost
  frames from the last `total_estimate=` plus `dropped_queue_full=` (grep -c 'drop\[' counts lines, not frames: Core
  logs a gap at its first loss, every 30th, or more than one frame at once, CameraController.cpp:9922-9937@9b5ea14).
- code: bounded questions answered with path:line@9b5ea14 (for example: how Core could pick a tuning for HDR16 only;
  src/camera/DefaultTuningSelection.hpp clearHdrVariant, CameraController.cpp:7222-7224). The Mac clones are not at
  9b5ea14: first fetch the Pi's branch into the Mac clone (git -C ~/Documents/Apertar/Apertar-Core fetch
  ssh://apertar/home/pi/ApertarCore drop-frames) and give the worker a scratchpad worktree at 9b5ea14, as in
  working/dual-sensor/HANDOFF.md "HOW CODE GETS TO THE PI" step 1. No edits.
- kb: drafts of findings, progress notes and index rows from your notes; you review and commit.
Keep for yourself: talking with Patrik; every Pi command; anything that changes the camera (in tutor mode Patrik sends
set_* and set_tuning_file; you only if he says so, one command at a time, announced, never during a take); reading the
results; the labels (confirmed / probable / unconfirmed, with path:line@sha); every KB commit.

RULES THAT BITE HERE (the skill has the rest)
- Read-only on the Pi unless Patrik asked for the change. No sudo; never type a password.
- Nothing that changes the camera while a take or another session's measurement runs. Never overlap with a dual-sensor
  T56 or T57 test. Don't save or load presets during a tuning test: a preset stores and applies cameraTuningFile.
- After every tuning test: back to automatic (path=), then read back tuning_file '', the `ApertarCore tuning file:`
  line and the settings file.
- Never disable_tdn (tier1-prep §3). Grep or tail the big logs under /run/apertar-media; never read them whole.
- Record each look in working/clearhdr16-preview.md and T55's progress. In the drop-frames pages add only one
  cross-reference line under findings-2026-11-04.md §1 "Not assessed tonight" ("User looked on <date>: see
  clearhdr16-preview.md §<n>"), in that project's "User" wording. Don't edit the drop-frames or dual-sensor files
  otherwise.
- KB: house commit format with the Co-Authored-By trailer; a hardware-log entry only after Patrik confirms; T55 status
  in tutorials/README.md, llm/tutoring.md §5 and the Obsidian learning-path note; fork-log only for a commit or a
  changed image-level file.

DONE MEANS: Patrik knows which T55 §3 row his flicker is and which stage makes it; he has seen the preview with TDN off
(and with CE or ALSC off if §3 pointed there); the KB records what he saw; and he has your recommendation for the
permanent change, written as input to the drop-frames decision.

REPORT at the end: the §3 row; what each switch or copy changed; the tuning read-back (tuning_file '' and the settings
file); the Core, UI and driver shas; what you committed; what is still open.
```
