# Handoff: build the dual-sensor port, T56-T70 (Opus lead in VS Code, Sonnet workers)

For: a Claude Code session in VS Code on the Mac, model Opus, with the `apertar-dev` skill, working with Patrik and
driving the Pi over `ssh apertar`. Written 2026-11-04 by the session that wrote plan v2.1 (KB `74f2ce7`), then checked by
four reviewers (safety, commands, orchestration, completeness against the plan). Paste the block below as the first
message, or say "read `~/Documents/Apertar/apertar-kb/working/dual-sensor/HANDOFF.md` and start".

Before pasting:
- The plan must be on the Mac: `git -C ~/Documents/Apertar/apertar-kb log --oneline -1 -- working/dual-sensor` shows
  `74f2ce7` or later.
- Open VS Code on the Mac, not over Remote-SSH on the Pi: Claude and the C++ language server on the Pi cost about 1.5 GB
  and spoil every drop count (`working/mac-driven-loop.md`).
- Earlier sessions' memories live under another project folder and may not load here, so the block below spells out
  the rules they hold.

---

```text
/apertar-dev You are the lead for the Apertar dual-sensor port: two IMX585 on one Apertar, two Cores, synced in software
by the phase lock on one grid (plan v2.1, steps T56-T70). You build it with Patrik, one step at a time. You decide the
code questions the plan already answers, drive the Pi, review every line, and read every Pi check against the plan's
own prediction. You hand bounded jobs to Sonnet workers (Agent tool, subagent_type "general-purpose", model "sonnet")
and review everything they return. Patrik decides what the plan marks as his, and runs every sudo, restart, reboot,
DKMS rebuild, config.txt change and take.

Read first, in this order (all in ~/Documents/Apertar/apertar-kb/):
1. working/dual-sensor/README.md, then plan-summary.md in full.
2. working/dual-sensor/design-dual-sensor.md: §0, §9 and §12 in full. Read §3-§8 and §10 one section at a time, as the
   step that uses it comes up; never the whole file (about 1,200 long lines). Where this prompt and the design disagree,
   the design wins, except where this prompt says it adapts the design to the shared Pi (Q24b below); say so each time.
3. working/dual-sensor/changes-from-critique.md §7 (the last re-check). Earlier sections only when a step points there.
4. llm/README.md §2 and §5 before reading any code (grep anchors; never read ApertarCoreApp.cpp, CameraController.cpp,
   WebControlPage.cpp or SettingsPage.qml whole).
5. working/mac-driven-loop.md and working/playback/HANDOFF-next.md "How to work on it": how code gets from the Mac to
   the Pi, and what went wrong in the last build.
6. working/handoff-drop-frames-tier1.md, its last "State after evening N" section. The drop-frames campaign shares the
   Pi; its state (branch, binary, drop-ins, tuning, ladder, driver, drive) is what you must not disturb.

Then the status check, all read-only:
- ~/.claude/skills/apertar-dev/scripts/apertar_status.sh (it compares only main/apertar).
- Before any ssh, the pre-ssh check (in WHAT YOU DO YOURSELF). Then one ssh block:
  `for r in ApertarCore ApertarUI drivers/imx585-v4l2-driver; do git -C ~/$r log --oneline -1; git -C ~/$r branch --list dual-sensor; git -C ~/$r worktree list; done`,
  `ls -l --time-style=+%F_%T ~/ApertarCore-build/apertar-core ~/ApertarUI/build/Apertar-UI`,
  `systemctl show apertar-core -p DropInPaths -p Environment -p ExecMainStartTimestamp`,
  `systemctl show apertar-ui-direct -p DropInPaths`, `ls ~/apertar-kb/working/dual-sensor`, `df -h /media/RAW`, and the
  link frequency read the way the campaign's checklist reads it (drop-frames/tests-2026-11/preregistration.md).
Expected: on the Pi, Core 9b5ea14 (drop-frames), UI c153c33, driver cd548ef (cinemate-port), no `dual-sensor` branch,
891 MHz. On the Mac, `Apertar-Core` and `Apertar-UI` are on other sessions' branches, and `drop-frames` is checked out in
`~/Documents/Apertar/Apertar-Core-drop`. That is expected and not a stop. Stop and tell Patrik if anything else differs.
The Pi may be powered off (the campaign's last evening ended with a poweroff); if so, say so and ask him to power it on.

Where things stand: planned, nothing built, no second sensor attached. The code refs in the design are at Core 31d5418,
UI c153c33 and driver cd548ef. The Pi runs Core 9b5ea14 (WebUI, controls and test_input changes only), so every ref is
re-grepped before a step's code is written (job R).

PATRIK'S CALLS FIRST (one message, defaults shown; edit nothing until he answers):
- Q25, who types. The plan's default is tutorials per Rule 1 (he types, you tutor). He asked for this lead-and-workers
  handoff, so propose "Claude builds", as for T31-T34 and T47-T51. You edit, commit on the Pi's local branch and build
  over ssh. He decides, and runs sudo, restarts, reboots and takes. Before each step you say what it changes, the first
  command and the risk; after each step you stop for his result or OK. If he picks tutorials, the worker jobs below draft
  tutorials (format: tutorials/README.md) instead of commits, and he types.
- Q24, branches: local, never-pushed `dual-sensor` branches on the Pi. Core cut from what the Pi runs when T57 starts
  (today drop-frames 9b5ea14), UI from c153c33, driver from cd548ef.
- Q24b (new: the design assumed one checkout, but the Pi is shared with the drop-frames campaign), where the branches
  live on the Pi. Default: a second checkout per repo, so the campaign's trees, binaries and boots never change:
    git -C ~/ApertarCore worktree add ~/ApertarCore-ds -b dual-sensor 9b5ea14     (the sha read back first)
    git -C ~/ApertarUI worktree add ~/ApertarUI-ds -b dual-sensor c153c33
    git -C ~/drivers/imx585-v4l2-driver worktree add ~/drivers/imx585-ds -b dual-sensor cd548ef
  Builds go in ~/ApertarCore-ds-build and ~/ApertarUI-ds/build, each configured with the options in the live build's
  CMakeCache.txt. Never build into ~/ApertarCore-build or ~/ApertarUI/build, and never copy a binary there. What this
  changes in the design is listed under SHARED-PI ADAPTATIONS; tell Patrik each one when its step comes.
  Alternative: the campaign is over or paused, and `dual-sensor` is a plain branch in each live checkout.
- Q12, driver fix E on the driver's `dual-sensor` branch, with Patrik's DKMS rebuild. The installed driver is shared
  with the campaign, so ask: after T58's tests, go back to cd548ef, or keep fix E installed and record it in the
  campaign's state section?
- Q1, record policy: follow the preview (default), or both cameras always.
- Q11, the lock in takes: track the grid (default), or hold.
Ask Q6, Q13 and Q14 before T61, because T61, T62 and T64 build them; show the other §12 defaults then too. Ask Q10
before T68. Ask Q20 and Q5 at T68.

SHARED-PI ADAPTATIONS (under the Q24b default; drop them if Patrik picks the alternative):
- Binary path. Every §9 test line, and T59's direct run, uses /home/pi/ApertarCore-ds-build/apertar-core in place of
  /home/pi/ApertarCore-build/apertar-core. Nothing else in those lines changes. Note it in build-log.md.
- Drop-ins. Every dual-sensor drop-in is a named file in /run, never in /etc, and never `systemctl edit`. Read
  `systemctl cat apertar-core apertar-ui-direct` and scripts/start-apertar-core.sh first; the script reads
  APERTAR_CORE_BIN.
    /run/systemd/system/apertar-core.service.d/ds-binary.conf: Environment=APERTAR_CORE_BIN=<the ds binary>. From T59
      on, it also points ExecStart at ~/ApertarCore-ds/scripts/start-apertar-core.sh (an empty ExecStart= line first).
    /run/systemd/system/apertar-ui-direct.service.d/ds-ui.conf: the UI's ExecStart pointed at the ds build (the campaign
      did the same, drop-frames/inspection-2026-11-02.md).
    /run/systemd/system/apertar-core.service.d/ds-test.conf: one §10 test's Environment= line. Use it wherever §10 says
      `sudo systemctl edit apertar-core`.
  Patrik's block: `sudo mkdir -p <dir> && printf '[Service]\n<lines>\n' | sudo tee <file> && sudo systemctl daemon-reload && sudo systemctl restart <unit>`.
  Undo: `sudo rm <file> && sudo systemctl daemon-reload && sudo systemctl restart <unit>`. Read
  `systemctl show <unit> -p DropInPaths -p Environment` before and after each. A reboot wipes /run, so after any reboot
  (T58's DKMS rebuild, T60, T68) Patrik re-adds ds-binary.conf and ds-ui.conf before the next check. At the end of every
  dual-sensor session he removes them, and you check the campaign binaries are the ones running.
- The cam1 install (§3.4, at T60). The new start script goes to /home/pi/start-apertar-core-ds.sh; the live
  /home/pi/start-apertar-core.sh is never overwritten. The cam1 unit's ExecStart is that file, with
  Environment=APERTAR_CORE_BIN=<the ds binary>. Patrik enables it with `sudo systemctl enable --runtime apertar-core-cam1`
  (gone at reboot; undo `sudo systemctl disable --runtime apertar-core-cam1`). The persistent enable, T60's "after a
  boot" checks and all of T68-T69 wait until the campaign is over or paused, or Patrik has merged `dual-sensor` into what
  it runs. Ask him before each.
- The driver. Patches land only in ~/drivers/imx585-ds. Before T58, read `dkms status`, the driver's setup.sh and
  architecture/drivers.md, to learn which tree DKMS builds from. Patrik's DKMS block names the build from the ds tree,
  the reboot, and the way back (the cd548ef tree, its DKMS rebuild, a reboot), as his Q12 answer says.
- Settings. Every setter sent to the running primary changes its saved settings (camera_settings.conf, UI.conf). Before
  the first setter of a session (T56 0.2-0.4, every §10 test, the simulated-cam1 tests, W11's scripts), copy
  ~/.config/apertar-core/ to ~/ds-before/<date>/ and save get_state (fps, resolution, clear_hdr, fps_phase_lock, the mode
  ladder, iso, format) in build-log.md. Afterwards, restore the same values with the same setters and `diff` the files
  against the copy. The campaign left the ladder on at 30 fps.
- Tools on the Pi go to ~/ds-tools/, never into ~/apertar-kb: the Pi's KB takes pushes with updateInstead, so untracked
  files there can block the next sync.

ORDER OF WORK (design §9; hours are the plan's estimates):
- T56 Measure first (3 h, no code): §10 Part 0. You run 0.1 (read-only) and, with Patrik's OK and the settings snapshot,
  0.2 (a listener; it sets 25 and 24 fps) and 0.4 (it turns the lock on and steps set_fps). Patrik runs 0.3, 0.5, 0.6,
  0.7 and 0.8 on test takes. The numbers set the lead, D and σ; write them into build-log.md before T57.
- T57 The lock on one grid (7 h): FPL and the CC sites, lock state in get_state, the KB simulator. Pi tests 1.1, 1.2,
  1.5, 1.8, 1.10, each under its own ds-test.conf.
- T58 Driver fix E (3 h): after T57, because tests 1.3, 1.4, 1.6 and 1.9 need T57's lock and trace.
- T59 Camera by port (3 h). Before any cam1 binary runs, §3.4 install steps 2-3 run early (no sudo; you, with his OK):
  the cam1 hardware file at /home/pi/apertar-hardware-cam1.conf (every input, [imu] and [ina219] with enabled=false) and
  `mkdir /home/pi/.config-cam1`. Without them the cam1 readers fall back to the primary's file and its inputs. T59's
  with-a-line no-sensor check waits for T68 step 1.
- T60 The secondary's role and unit (4 h), then T63 the preview-source setting (4 h). T59, T60 and T63 do not depend on
  T57-T58, but they share App.cpp with them, so they come one at a time.
- T61 The relay (13 h), then T62 One slot (7 h), then T64 Take coordination (12 h). T61-T66 test against the simulated
  cam1 with the Mode Ladder off and manual ISO or a non-lossless format (§9, §4.4).
- T65 The second picture (5 h), T66 HDMI layouts (6 h), T67 WebUI (5 h).
- T68 The second IMX585 (3 h), Patrik's, in the design's order: (1) cam1's config.txt line (891 MHz written out), then
  T59's no-sensor check: `sudo systemctl restart apertar-core-cam1`, the journal shows the 20 s poll and exit 0, the unit
  ends inactive; (2) `sudo poweroff`, unplug; (3) the sensor on MIPI1 (Q20); (4) power on, then re-add the /run drop-ins;
  (5) `systemctl status apertar-core-cam1` is active, and its "Registered camera" line names i2c@70000. Then 2.0, r4-M1,
  r4-M2, 2.1, 2.2, 2.4. A cam1 line and an attached sensor change the campaign's rig (its binary still picks the first
  camera and subdev it finds, §3.2), so T68 starts only when Patrik says the campaign is over or paused.
- T69 Dual takes (4 h, fixes only), T70 Touch UI (optional, build only; there is no touch screen).
Every step's last check: with no cam1 configured, a take, Clear HDR and the WebUI behave as before. After each step,
re-plan from what the Pi showed, and tell Patrik in one paragraph what changed and why.

HOW CODE GETS TO THE PI:
1. Bring the Pi's branches to the Mac: `git -C ~/Documents/Apertar/Apertar-Core fetch pi` (the same for Apertar-UI and
   imx585-v4l2-driver). The `pi` remote's forced refspec puts them at `pi/dual-sensor` and survives the squashes. Never
   create or check out a local `dual-sensor` on the Mac, and never fetch into a local branch (`drop-frames` is checked
   out in another session's worktree).
2. One Mac worktree per worker job, in your scratchpad, with a unique name:
   `git -C <repo> worktree add <scratchpad>/core-T61a -b ds-wip/T61a pi/dual-sensor`. Once its patch has landed on the
   Pi and been fetched back: `git -C <repo> worktree remove <path> && git -C <repo> branch -D ds-wip/<job>`. KB jobs get
   `git -C ~/Documents/Apertar/apertar-kb worktree add <scratchpad>/kb-<job> -b ds-wip/<job> main`, and you bring the
   result into the KB yourself. Do not use the Agent tool's worktree isolation: it cuts a worktree of the wrong repo.
3. The worker commits a draft there. You review it, then `git format-patch -1` (or `-N`), `scp` the patch to ~/ds-tools/
   on the Pi, and `git -C ~/ApertarCore-ds am <exact file name>` (UI ~/ApertarUI-ds, driver ~/drivers/imx585-ds). Never
   a glob in `git am`.
4. Build on the Pi, one build at a time and never during a take: `cmake --build ~/ApertarCore-ds-build -j2`, UI
   `cmake --build ~/ApertarUI-ds/build -j2`. Never `pkill -f` over ssh, and never wait with `pgrep -f "cmake --build"`
   inside `bash -c`.
5. A build error goes back to the same worker with the compiler output (SendMessage; load it with ToolSearch first). If
   the worker cannot be resumed, give a fresh worker the same worktree, the job text, its diff and the output.
6. WebControlPage.cpp's page is one C++ raw string: extract the script and run `node --check` on it before every build.
7. One commit per feature: once the step's checks pass, fold its fix-ups into the step's commit on the Pi, in the ds
   tree only. With D=~/ApertarCore-ds (or the UI or driver tree): `git -C $D branch --show-current` prints dual-sensor,
   and `git -C $D status --porcelain` is empty. Then `N=$(git -C $D commit-tree 'HEAD^{tree}' -p <parent> -F <msg>)`,
   keeping the first commit's dates (GIT_AUTHOR_DATE, GIT_COMMITTER_DATE). Check `git -C $D diff HEAD $N` is empty, then
   `git -C $D reset --soft $N`. Never run reset in ~/ApertarCore, ~/ApertarUI or ~/drivers/imx585-v4l2-driver. Then
   fetch again (step 1) and fix the fork-log shas.

WHAT YOU DO YOURSELF (never a worker):
- Every command on the Pi, read-only ones included, and every fetch from it. A worker never touches the Pi.
- The pre-ssh check, before every ssh: nothing records and nothing builds. Run `python3 ~/apertar-kb/working/tools/core.py
  get_state` (recording false), `pgrep -a 'cc1plus|gmake|cmake'` (empty),
  `ps -eo pid,etimes,args | grep -E 'takes?\.sh|take3v3|b1-arm' | grep -v grep` (empty), and read the :8000 clients and
  the running Core binary's mtime. `who` alone misses the campaign's non-interactive takes. Other Mac sessions (the
  campaign's lead among them) may build, open the WebUI or commit to the KB at the same time. During a campaign evening,
  run nothing on the Pi until Patrik says it is over.
- Design calls the plan leaves open, in its direction: consistent with Apertar, least intrusive, least API change.
  Decide, say why in one line, carry on. The API delta is §8 (23 names, 4 files, one test-only env); a name that is not
  there needs Patrik's OK.
- Reviewing every worker diff line by line against the design section it implements, and rerunning its host checks.
- Patch transfer, `git am`, builds and squashes on the Pi. The fork-log row for every Core, UI and driver commit (status
  fork-only). Before you end a session, run ~/.claude/skills/apertar-dev/scripts/fork_log_check.sh. It does not see the
  dual-sensor branches, so after a fetch also run, per repo,
  `for s in $(git -C <repo> log --format=%h <base>..pi/dual-sensor); do grep -q $s ~/Documents/Apertar/apertar-kb/fork-log.md || echo missing $s; done`
  with base 9b5ea14 (Core), c153c33 (UI) or cd548ef (driver).
- Every Pi check, read against the plan's prediction and marked measured / probable / unconfirmed in
  working/dual-sensor/build-log.md. Create it at T56, with columns step, check id, prediction, result, label, date.
- Every message to Patrik, every sudo block (exact commands, each with its undo), and every decision that is his.
- The llm/tutoring.md §5 row for each step (status "Claude builds", then "built").
- At the end of every session, a "State after session N" section at the bottom of this file:
  - what was done;
  - the Pi's state: branches and checkouts, binaries, every /run and /etc drop-in, enabled units, start scripts,
    ~/.config-cam1 and the cam1 hardware file, the settings diff against ~/ds-before/, tuning, ladder, config.txt,
    driver checkout and the installed module, and the drive (`df`, what is on it);
  - what is open for Patrik, and the next step.

WORKER JOBS (Sonnet; one job per worker). Give each the preamble below, the job's paragraph, its worktree path, and the
design sections it implements by path and § number. Code jobs on the same repo run one at a time, each from the Pi tip
after the last one landed and was fetched back: most steps touch ApertarCoreApp.cpp and CameraController.cpp. A job
marked ∥ may run beside jobs in other repos (UI, driver, KB) or beside read-only jobs; never beside a code job on the
same repo.
R   Ref map (∥, read-only, before each code step). In a detached worktree of the Pi tip (`worktree add --detach`), find
    by its anchor text every file:line ref that the step names, in §9 and in the § it implements. Return a table: design
    ref, anchor, line now, MOVED or GONE. You fix the design or note it in build-log.md before the code job starts.
W1  T56 scripts (∥, KB): 0.2's socket client that logs preview_frame timestamp_us and prints the mean, σ and outliers;
    0.4's frame counter; a parser that turns 0.7's journal lines into press-to-first-frame and press-to-reply numbers.
    Python 3, no third-party modules, read-only on the socket except where the test says, a host self-test on a sample.
W2  T57 simulator (∥, KB): working/tools/phase_lock_sim.cpp gains dead time, jitter, the 2-line step, Q, a grid case and
    a sensor pair (§7; working/dual-sensor/sim/README.md). Host-compiled on the Mac; its checks pass and the new cases
    match sim/'s numbers.
W3  T57 Core: the grid error, quantiser, preview catch-up, anti-windup, `locked`, the trace (marking the arm frame), the
    VBLANK-only pins at three sites, the saturation check, lock state in get_state (§7.2-§7.4, §9 T57).
W4  T58 driver (∥ with W3, another repo): fix E (rewrite SHR when VBLANK changes) and the dev_dbg change in imx585.c.
    Tested only after T57 is running on the Pi.
W5  T59 Core: --camera, the env vars in the start script, both pick sites, the subdev by of_node and its four users,
    the primary's wait for cam0's subdev when config.txt names one, camera_id/camera_port, {cam} from the port, the
    no-sensor exit and its 20 s poll in main(); config/apertar-hardware-cam1.conf (§3.2, §9 T59).
W6  T60 Core: the role gate (photo mode forced off, the preset's photo keys and UI.conf writes), the start line, the
    allowlist, the one 403 reply for every :8001 POST, the start wait and its 30 s timeout,
    config/apertar-core-cam1.service, the syncfs site in CC (§3.3, §3.4, §4.2 for the allowlist).
W7  T63: the previewSource quartet, which copies externalMonitorMode end to end. Core part (App.cpp,
    WebControlPage.cpp), then the UI part (SettingsBridge) as its own job (∥ with the next Core job). §5.1.
W8  T61, three jobs in this order, each landed and built before the next starts:
    (a) src/ipc/ControlClient.hpp/.cpp and CMakeLists.txt (∥ only with UI, driver or KB jobs);
    (b) ControlClient's start before the trim and watcher threads, the wrapper, its lock order and the pending count,
        the relay's own setters in the count and their hand-off with a starting take, command classes, idle, the take
        state, the busy window and its 1 s wait, the CC.cpp site (10417 at 31d5418);
    (c) presets and the three-step resync, the 3-resync cap that pauses the triggers, the shared ladder and an override
        kept across a restart, the compare, the cam1 state (`refused` in the ranking), the link-down and relink lines,
        live skew. §4.1-§4.6; the simulated-cam1 test line in §9 is the bench.
W9  T62: start_us, stop_us and the stop gate, clip_name and its checks, tc_offset_us, takePending_ for every take of the
    Core's own camera and the stretch-landing slot, the first and last slot fields and recording_clip_name, slots.txt,
    exclusive mkdir, timecode from the slot in DNG, MLV, H.264 and ProRes, the safety-stop branch (checked in T64),
    Speed Ramp numbering keyed on start_us, APERTAR_TEST_DROP_FRAME (§6.2, §6.3).
W10 T64: two Core jobs, (i) which cameras, the policy, override, presets, record_cameras, the cam1-only take, the
    published starting take, busy sites and refusals, and (ii) the pending stop, the relink rules, adoption by a
    restarted primary, the secondary's start wait, the trim and pre-roll hold, the stop wait's bound, the safety and
    failure stops, L_cam1 per take, time left. Then one UI job (SettingsBridge), and working/tools/sock_forward.py (∥, KB).
    §6.1, §6.2, §4.3, §4.6, §3.4.
W11 Test scripts (∥, KB; Python 3, no third-party modules). (a) At T60: the 9 POST probes on :8001, each a request its
    handler refuses before writing, or one that writes nothing (§9 T60 lists them). (b) At T64: the set_iso-every-50-ms
    and get_state-every-20-ms script, and the two take loops (20 two-camera, 20 cam1-only) that print L_cam1 per take.
    None of them ever sends format_media, eject_media, set_boot_config without dry_run, or a real delete.
W12 T65, then T66 (UI repo; ∥ with Core jobs, written from §4.5's state shape and §5.2): one job per step.
W13 T67 WebUI (Core repo, WebControlPage.cpp and App.cpp): after the Core jobs that share those files. §5.3.
W14 T70 (optional): CameraPage.qml and SettingsPage.qml; build only.
V   Review (∥, read-only), for every code job before you take it. A second Sonnet worker gets the diff, the design §,
    and the job's worktree path (grep and read only; no edits, no commits). It tries to refute the diff: a missed site,
    a broken lock order, a refusal text that differs from the design, a change to the one-camera path. It returns
    findings with file:line and the design line each one breaks. You judge each finding; a reviewer is not a vote.
Workers draft; you commit. You may reword or squash a worker's draft commits.

Preamble for every worker:
  You are a worker on the Apertar dual-sensor port, on the Mac. Repos: ~/Documents/Apertar/Apertar-Core,
  ~/Documents/Apertar/Apertar-UI, ~/Documents/Apertar/imx585-v4l2-driver, ~/Documents/Apertar/apertar-kb. Work only in
  the worktree path the job names; never check out, reset or fetch anything in the main checkouts. The design is
  ~/Documents/Apertar/apertar-kb/working/dual-sensor/design-dual-sensor.md; read only the sections the job names. If you
  touch code, read ~/Documents/Apertar/apertar-kb/llm/README.md §2 and §5 first: find code with grep anchors, read about
  100 lines around a hit, never read ApertarCoreApp.cpp, CameraController.cpp, WebControlPage.cpp or SettingsPage.qml
  whole. Follow the design's names, texts and numbers exactly, and match the surrounding code's style. Do exactly the
  job, nothing else: no refactors, no settings or commands the design does not name. Never run anything on the Pi (no
  ssh, no scp, no fetch from it), never push, never use sudo, never delete anything outside the paths the job names.
  libcamera code does not compile on the Mac: run the host checks you can (a syntax check of standalone files,
  node --check on the extracted page script, a host build of a simulator or tool), and name the ones you could not run.
  Commit your work in the worktree as a draft: "<area>: <imperative>", Why/What, "Tested: desk only", ending with
  Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>; "User", never a person's name. Return: the worktree and
  commit, the files you touched, the diff, the checks with their output, every design ref you could not find, and
  anything that differed from what the job assumed. A check you did not run is "not run", never "passed".

RULES THAT MATTER MOST (from the plan, the skill and Patrik):
- Patrik runs every sudo command, restart, reboot, DKMS rebuild, config.txt change and take. Give him exact blocks.
- Nothing on the Pi during a take, the campaign's included. One build at a time on the Pi (4 GB).
- Never touch the campaign's checkouts, binaries, /etc drop-ins, tuning files or scripts. Never run `sudo -n`,
  /usr/local/libexec/apertar-b1-arm, apertar-media-tune or any other campaign helper.
- Never send format_media, eject_media, set_boot_config without dry_run, or a real delete to a Core under test (§9).
  Use §9's test lines (with the binary path above): shorter ones can steal the primary's socket or write its config.
- The drive: delete only a test take's own clip folder (cam1's `_cam1` folder too), by the exact path from its
  "recording clip:" line, and only with Patrik's OK. Never a cDNG_* glob, never warm.bin; formatting is his. Note
  `df /media/RAW` before and after each session.
- Never `git checkout .`, `reset --hard` or `clean` on the Pi without showing the diff and asking.
- Nothing is pushed. `dual-sensor` branches never reach GitHub (apertar_publish.sh moves only main/apertar); they get
  there only when Patrik merges them himself. Never push to upstream. The Pi has no GitHub credentials; never add any.
  KB commits need no permission, but ask before any KB push or sync.
- Commits: "<area>: <imperative>", Why/What, a "Tested:" line, the Co-Authored-By trailer; "User", never Patrik's name,
  in any commit message. A fork-log row for each Core, UI or driver commit. One commit per feature (step 7 above).
- Claims in the KB labelled confirmed / measured / probable / unconfirmed. A hardware-log entry only after Patrik
  confirms the reading ("yes, that's it"), not when a command exits 0.
- Apertar's UI rules: values the system decides are shown in italics, not green; Patrik has no touch screen; the rig has
  no gyro.
- Every step leaves the one-sensor rig working; with no cam1 configured, nothing changes.

START: report the reading done and the Mac half of the status check. Send Patrik the calls above in one message. While
he answers, spawn W1 (a KB worktree; it needs neither the Pi nor his answers). Once the Pi is on and the pre-ssh check
passes, run the Pi half of the status check, then `git -C ~/Documents/Apertar/Apertar-Core fetch pi`, check
`git -C ~/Documents/Apertar/Apertar-Core rev-parse --short pi/drop-frames` prints 9b5ea14, and spawn R for T57 on
`git -C ~/Documents/Apertar/Apertar-Core worktree add --detach <scratchpad>/core-R-T57 9b5ea14`. After his answers:
create the Pi checkouts his Q24b answer names (one block, shown to him first), and give him T56's plan: 0.1 (yours,
read-only), then the settings snapshot, 0.2 and 0.4 with his OK, and his blocks for 0.3 and 0.5-0.8.
```

---
