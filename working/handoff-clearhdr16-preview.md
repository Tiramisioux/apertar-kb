# Handoff: the 16-bit Clear HDR preview flicker, T55 with Patrik (Opus lead in VS Code, Sonnet workers)

For: a Claude Code session in VS Code **on the Mac** (not Remote-SSH on the Pi), main model Opus, with the `apertar-dev`
skill, working with Patrik and driving the Pi over `ssh apertar`. Written 2026-11-04 by the session that diagnosed the
flicker and wrote T55; revised the same evening after three independent reviews (fidelity, a walk-through as a fresh
lead, workers and safety). 2026-11-08: the project gets its own feature branch (Patrik asked; FEATURE BRANCH in the
block). The Pi has moved since 11-04 (11-06: GitHub `cinemate-port` replaced from the Pi's `f4a1393`, grown from
`controls`; clip-split since then), so the shas in the block are the 11-04 state and its step 1 reads the real ones.
Paste the block below as the first message, or say "read
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
6. working/dual-sensor/HANDOFF.md, only when the branch needs more than its creation (a build, a drop-in, a patch): Q24b,
   SHARED-PI ADAPTATIONS (Drop-ins, Settings, Tools on the Pi), HOW CODE GETS TO THE PI and WHAT YOU DO YOURSELF (the
   pre-ssh check). Where it says ds, read c16. FEATURE BRANCH below wins where they differ.

WHAT CHANGED SINCE T55 WAS WRITTEN (2026-11-03 23:40; the state on 11-04: the Pi has moved since, so plan step 1's
read wins over every sha here)
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

START: plan step 1. Step 1 is clean when ssh apertar answered; the status shows no take, no build and no other
session's measurement (a WebUI client alone is not a stop); the branch preflight printed nothing unexpected; and
`python3 $T refs T55` ran. If clean: create the branch (FEATURE BRANCH), then send ONE message to Patrik: per repo the
parent branch, base sha and path; any tracked-change warning; "no build, drop-in or restart done; the driver and
libcamera have no branch"; then the plan step 2 questions. If not clean, or ssh fails (the Pi is often off): create
nothing. The one message says why, asks who owns the Pi or asks him to power it on, and says you will create the
branch once he says it is free, after running step 1 again. T55 can go on without the branch: most of it changes no
code.

FEATURE BRANCH (Patrik, 2026-11-08: "make this project start its own feature branch".) That is his OK for exactly
these writes: the two `git worktree add` commands below (or, in the alternative, the two `git switch -c`), the Mac
`git fetch pi`, and the KB commits. It is not an OK to build, commit on the branch, scp, `git am`, add or remove a
drop-in, or restart; each needs his ask in chat for that step (Rule 1: in tutorial mode he types the build and the
commits).
This project's code goes on its own local branch `clearhdr16-preview` in Core and the UI, as controls and clip-split
were local Pi branches. Nobody but Patrik moves it off the Pi (he folded clip-split into cinemate-port on 11-08). The
driver and libcamera get a branch only if a step needs a change there; ask Patrik first, since the installed driver
and /usr/local libcamera are shared. Most of T55 changes no code (tuning copies live in ~/Tuning-Files, outside git,
and the aids are settings). The branch is where a code change lands: a Core tuning choice for HDR16 only, the #45
zebra rule, the #24 peaking step (#24 and #45 are UI shader code, PreviewWindowRenderer.cpp; #45 also has a WebUI half
in WebControlPage.cpp), or a T55 follow-up tutorial.
- Where. By default, a second checkout per repo, so the trees, binaries and boots of the other projects on the Pi
  never change. This is dual-sensor's planned Q24b layout, used here for the first time (controls and clip-split were
  branches in the live checkouts).
- The base is what the camera runs: the live checkout's HEAD, if the running binary was built from it. Step 1 shows it
  (branch, HEAD, binary mtime, unit start time). If HEAD's commit date is newer than the binary, or the live HEAD is a
  branch another session is still changing, stop and ask Patrik which base he wants.
- Tracked changes only: test with `git status --porcelain --untracked-files=no`. Core's live tree always has untracked
  src/prores/README.md and src/prores/ffmpeg/ (upstream-issues #7); they are no reason to warn, and a worktree does not
  get them (if a c16 build needs one, copy it from the live tree and say so). If there are tracked changes, cut from
  HEAD anyway and tell Patrik the branch lacks them and the running binary may include them.
- The writes, in a second ssh after the preflight, and nothing else in it:
    A=$(git -C ~/ApertarCore rev-parse HEAD); U=$(git -C ~/ApertarUI rev-parse HEAD); echo $A $U
    git -C ~/ApertarCore worktree add ~/ApertarCore-c16 -b clearhdr16-preview $A &&
    git -C ~/ApertarUI worktree add ~/ApertarUI-c16 -b clearhdr16-preview $U
  Check $A and $U are the shas the preflight showed. If the second add fails, stop and tell Patrik the state; don't
  retry or clean up on your own. Then read back `git -C ~/ApertarCore-c16 log -1 --oneline` and the UI's.
- Alternative, only if Patrik says in chat that no other project uses the live checkouts: `git -C ~/ApertarCore switch
  -c clearhdr16-preview` and the same for the UI (the same HEAD, the tree unchanged). Those are the only switches
  allowed. Then there are no c16 trees, build dirs or drop-ins: read every ~/ApertarCore-c16, ~/ApertarUI-c16 and
  -c16-build path below as the live one, build into the live build dirs only on his ask, and say "plain branch in the
  live checkout" in the Branch line. Otherwise never switch a live checkout.
- The Mac. `git -C ~/Documents/Apertar/Apertar-Core fetch pi`, and the same for Apertar-UI: the pi remote's forced
  refspec gives pi/clearhdr16-preview. Do it only when a worker job needs the branch, and only after a fresh pre-ssh
  check (recording false; no cc1plus, cmake or take scripts). Never create or check out a local clearhdr16-preview on
  the Mac, and never fetch into a local branch: other sessions have branches checked out in their Mac worktrees.
- The KB, committed: a "Branch" line in working/clearhdr16-preview.md (the name, per repo the parent branch and base
  sha, the date, the paths). In fork-log.md, a dated paragraph under the Core header and one under the UI header, worded
  like the clip-split paragraph: "<date> (User): local branch **`clearhdr16-preview`** on the Pi, from `<parent>`
  `<sha>`, worktree ~/ApertarCore-c16 (or ~/ApertarUI-c16); never pushed." Every later commit on it gets a fork-log row
  ending "local branch `clearhdr16-preview`", like the controls rows. fork_log_check.sh does not see the branch (it
  walks the live trees): list its commits by hand with `git -C ~/ApertarCore-c16 log --oneline <base>..HEAD`, and the
  UI's, and check each against fork-log.md.
- With no commit on the branch there is no c16 build and no drop-in, and "which tree runs" is live. T55 §3-§4 always
  run on the live binaries.
- Building, only after a code change on the branch and Patrik's ask; in tutorial mode he types the command. One build
  at a time, never during a take: `cmake --build ~/ApertarCore-c16-build -j2`, UI `cmake --build ~/ApertarUI-c16/build
  -j2`, each dir first configured with the options in the live build's CMakeCache.txt. Never build into
  ~/ApertarCore-build or ~/ApertarUI/build, and never copy a binary there. Never `pkill -f` over ssh, and never wait
  with `pgrep -f "cmake --build"` inside `bash -c`. If WebControlPage.cpp changed: its page is one C++ raw string, so
  extract the script and run `node --check` on it before the build.
- Running a c16 build: named drop-ins in /run only, never /etc, never `systemctl edit`.
    Core: /run/systemd/system/apertar-core.service.d/c16-binary.conf with
      Environment=APERTAR_CORE_BIN=/home/pi/ApertarCore-c16-build/apertar-core. The unit runs
      /home/pi/start-apertar-core.sh, a copy outside git: check `grep -n APERTAR_CORE_BIN /home/pi/start-apertar-core.sh`.
      A change to the repo's scripts/start-apertar-core.sh on the branch does not run.
    UI: /run/systemd/system/apertar-ui-direct.service.d/c16-ui.conf with an empty ExecStart= line, then the live unit's
      ExecStart with the c16 paths (run_pi_direct.sh takes the binary as its argument; copy the argument list from
      `systemctl cat apertar-ui-direct`).
  First, step 1's DropInPaths and Environment must show no other drop-in that sets APERTAR_CORE_BIN or the UI's
  ExecStart (dual-sensor's ds-binary.conf or ds-ui.conf, a test drop-in); drop-ins merge by file name and a later one
  wins. If one is there, stop and ask who owns the Pi. Patrik adds one with
    sudo mkdir -p <dir> && printf '[Service]\n<lines>\n' | sudo tee <file> && sudo systemctl daemon-reload && sudo systemctl restart <unit>
  and removes it with
    sudo rm <file> && sudo systemctl daemon-reload && sudo systemctl restart <unit>
  Before and after, read `systemctl show <unit> -p DropInPaths -p Environment -p ExecStart` and `readlink
  /proc/$(pgrep -nx apertar-core)/exe` (for the UI, the Apertar-UI process), and record which binary actually runs.
  Before the first c16 run, Patrik copies the saved settings (`cp -a ~/.config/apertar-core ~/c16-before-<date>`);
  after going back to the live binary, diff the two and report any difference. A reboot wipes /run, and the live
  binaries run again; at the end of the session the drop-ins are gone and you check the live binaries run.
- Patches and tools on the Pi go to ~/c16-tools/, never into a checkout or ~/apertar-kb (the Pi's KB takes pushes with
  updateInstead, and untracked files there can block the next sync).
- tutorial.py refs and check read the live trees (tutorial.py:40, PI_REPOS), not the c16 ones. A line that exists only
  on the branch gets no `ref` line (refs would report it missing). Its check line is `grep -nF '<text>'
  ~/ApertarCore-c16/<path>` or `git -C ~/ApertarCore show clearhdr16-preview:<path> | grep -n '<text>'`, never `git
  grep` (tutorial.py refuses it). Say so in the note. A tutorial step Patrik types goes in the c16 tree, and says so.
- Never pushed: apertar_publish.sh moves only main/apertar. Never reset, rebase or delete the branch or its worktree
  without showing its state and asking.

PLAN
1. Status, read-only, yourself, in one ssh: `ssh apertar 'bash -s' <<'EOF' ... EOF` with, inside: curl -s -m 3
   http://127.0.0.1:8000/api/state | python3 -m json.tool | grep -E '"(recording|media_writes_pending|buffer_used|
   recording_dropped_frames|clear_hdr|raw_bit_depth|resolution|fps|shutter_us|cdng_compression|tuning_file|ladder_text|
   focus_peaking_enabled|zebra_enabled|zebra_threshold|external_monitor_mode)"' (the aids sit under "ui");
   systemctl show apertar-core apertar-ui-direct -p DropInPaths -p Environment -p ExecStart -p ExecMainStartTimestamp;
   pgrep -af '[c]c1plus|[c]make|[t]ake3v3|[t]akes?\.sh|[l]ongtakes|[b]1-arm|[c]laude' (the brackets stop pgrep
   matching its own command line); ss -tn state established '( sport = :8000 )' (a WebUI client changes the load); who
   (your own ssh is listed too; non-interactive takes are not); git -C ~/drivers/imx585-v4l2-driver log -1 --oneline
   (cd548ef on 11-04); grep imx585 /boot/firmware/config.txt (link-frequency 891000000);
   ls -l --time-style=+%F_%T ~/ApertarCore-build/apertar-core ~/ApertarUI/build/Apertar-UI; and the branch preflight:
     for r in ApertarCore ApertarUI; do
       echo "== $r"; git -C ~/$r branch --show-current
       git -C ~/$r log -1 --date=format:%F_%T --format='%h %cd %s'
       git -C ~/$r status --porcelain --untracked-files=no
       git -C ~/$r branch --list clearhdr16-preview; git -C ~/$r worktree list | grep -E 'c16|clearhdr16'
     done
     for d in ~/ApertarCore-c16 ~/ApertarUI-c16 ~/ApertarCore-c16-build ~/c16-tools; do test -e $d && echo "EXISTS $d"; done
   (after the branch exists, the same loop over ApertarCore-c16 and ApertarUI-c16 instead). Unexpected in the preflight:
   any clearhdr16 branch, c16 worktree or EXISTS line (stop and ask), and tracked changes (the warning above). If a take,
   a build or another session's measurement is running, stop and ask Patrik which session owns the Pi tonight. Then
   `python3 $T refs T55` on the Mac; fix moved lines in the note. With every T55 result, record the Core, UI and driver
   shas of the trees that run (the c16 tip while a c16 drop-in is in; a non-empty status means the result belongs to no
   sha: say so).
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
- code: bounded questions answered with path:line@<sha> against the project branch (for example: how Core could pick a
  tuning for HDR16 only; at 9b5ea14 that was src/camera/DefaultTuningSelection.hpp clearHdrVariant and
  CameraController.cpp:7222-7224, re-grep them). The Mac clones are on other sessions' branches: after `git fetch pi`
  (FEATURE BRANCH), you (never the worker) create each worker's own scratchpad worktree, `git -C <repo> worktree add <scratchpad>/c16-<job>
  -b c16-wip/<job> pi/clearhdr16-preview`, and remove both when done (`git -C <repo> worktree remove <path> && git -C
  <repo> branch -D c16-wip/<job>`). Not the Agent tool's worktree isolation: it cuts a worktree of the wrong repo.
  Questions only, no edits. A code change is a T55 follow-up tutorial Patrik types in the c16 tree (Rule 1). Only if
  he says "you do it": a worker commits a draft in its worktree, you review it, `git format-patch`, scp the patch to
  ~/c16-tools/ on the Pi and `git -C ~/ApertarCore-c16 am ~/c16-tools/<exact file name>` (never a glob), as in working/dual-sensor/HANDOFF.md "HOW
  CODE GETS TO THE PI" steps 2-3.
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
  in tutorials/README.md, llm/tutoring.md §5 and the Obsidian learning-path note; fork-log only for a commit, a
  changed image-level file, or the branch paragraphs in FEATURE BRANCH.

DONE MEANS: Patrik knows which T55 §3 row his flicker is and which stage makes it; he has seen the preview with TDN off
(and with CE or ALSC off if §3 pointed there); the KB records what he saw; and he has your recommendation for the
permanent change, written as input to the drop-frames decision.

REPORT at the end: the §3 row; what each switch or copy changed; the tuning read-back (tuning_file '' and the settings
file); the Core, UI and driver shas; the branch (per repo the parent, base and tip, its commits, whether a c16
drop-in for Core or the UI is still in /run, the settings diff after any c16 run); what you committed; what is still
open.
```
