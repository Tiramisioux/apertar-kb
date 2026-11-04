# Handoff: Tier 2 of the drop-frames campaign, evening 4 (Opus lead in VS Code, Sonnet workers)

For: a Claude Code session in VS Code on the Mac, model Opus, with the `apertar-dev` skill, working with Patrik and driving
the Pi over `ssh apertar`. Written 2026-11-04 by the cloud session that analysed evening 3. The plan is
`drop-frames/tests-2026-11/tier2-plan-2026-11-04.md`; this file is the prompt for its 2 supervised hours, which hand over
to the unsupervised night of the plan's section 5. Before pasting: the KB PR carrying this file and the plan is merged;
pull on the Mac and the Pi. Paste the block, or say "read `~/Documents/Apertar/apertar-kb/working/handoff-drop-frames-tier2.md`
and start".

---

```text
/apertar-dev You are the test lead for evening 4 of the Apertar drop-frames campaign: Tier 2. Patrik is with you for the
first 2 hours; after that you continue unsupervised (up to 6 hours) through the root helper he installs. You decide, drive
the Pi and read every result against the pre-registered rules. Sonnet workers (Agent tool, model "sonnet") do bounded
jobs on Mac copies of the data and never touch the Pi.

READ FIRST (Mac ~/Documents/Apertar/apertar-kb/, Pi ~/apertar-kb/):
1. working/drop-frames/tests-2026-11/tier2-plan-2026-11-04.md, all of it: the basis (section 1), the priorities (2), the
   preparation (3), the 2 supervised hours (4), the unsupervised night (5), the pre-registration (6). Where this prompt and
   the plan disagree, the plan wins; say so.
2. working/drop-frames/tests-2026-11/findings-2026-11-04.md and observations-2026-11-04.md (Patrik's own takes).
3. working/handoff-drop-frames-tier1.md: the rules block, the "State after evening 3" section, and how evening 3 ran the
   units (working/tools/drop-frames-2026-11-01/e3-unit.sh, e3-collect.sh, the root helper and its sudoers file).
4. working/drop-frames/tests-2026-11/tier1-prep-2026-11-03.md section 4 (selecting and restoring a tuning file: ST, J).
Then run ~/.claude/skills/apertar-dev/scripts/apertar_status.sh: Core and UI tips on the Pi and GitHub, what runs, the
drive, the uptime, the KB HEAD on the Mac and the Pi against GitHub main, and whether the sudo helper from evening 3 is
still installed (/etc/sudoers.d/apertar-b1-arm, /usr/local/libexec/apertar-b1-arm). Stop and say so if anything differs.

WHAT TONIGHT IS FOR (from evening 3's analysis, measured unless marked):
- TDN off removed the back-end bottleneck. Every remaining TDN-off loss (11 of 11) is FE Config starvation: libcamera keeps
  2 FE Config buffers in flight, hands one back only after the 16-bit swap of the same frame, and the swap stretches from
  ~8 to 46-81 ms during kcompactd bursts (~every 33 s); the CFE then skips a frame silently. be_overlap.py section 7
  replays the queue: depth 2 reproduces every loss, depth 3-4 predicts 0 (probable effect).
- So tonight, in priority order: (1) num_cfe_config_queue = 4 by a pipeline-YAML copy and LIBCAMERA_RPI_CONFIG_FILE, A/B
  at 28 fps; (2) TDN off in every scored take; (3) B6, five 10-min takes at 25 fps; (4) Patrik's preview choice among TDN on
  (N), TDN off (F) and no denoise (Z); (5) vm.compaction_proactiveness=0 only as the fallback.
- The preview aids (peaking, zebra) are GPU shaders on the YUV preview, not the raw: denoise changes what peaking sees.

THE 2 SUPERVISED HOURS (plan section 4; times are targets):
0:00-0:15 One message to Patrik with every question: the die rolls (the depth A/B order: one of the 6 balanced orders of 2
  D2 + 2 D4; the N/F/Z order for the night), may you reboot overnight (B6's second boot), his clips on the test card, OK to
  push tonight's KB commits. Then: reboot (Patrik), and the root helper for tonight, drafted by you, reviewed and installed
  by him: exact commands for the drop-in (LIBCAMERA_LOG_LEVELS=IPARPI:ERROR,RPI:0,RPiStream:0,
  LIBCAMERA_LOG_FILE=/run/apertar-media/libcamera-e4.log, LIBCAMERA_RPI_PISP_CONFIG_DUMP=/run/apertar-media/be-cfg.json,
  LIBCAMERA_RPI_CONFIG_FILE=/run/apertar-media/pisp-pipeline.yaml), b1-arm.sh sync/save/restore, the reboot and re-arm if
  he allows it, and vm.compaction_proactiveness set 0 / restore (fallback only). The /run YAML must exist before any Core
  start that has the drop-in (copy it first; after a reboot both are gone and the drop-in comes back only with the re-arm).
0:15-0:30 Preparation (plan section 3, no sudo):
  - Does this libcamera read the knob? strings <the installed libcamera .so> | grep num_cfe_config_queue, and find the
    installed PiSP pipeline YAML. No hit: item 1 cannot run; tell Patrik, and pre-register vm.compaction_proactiveness=0
    (item 5) as tonight's A/B in its place (same 28-fps design).
  - /home/pi/Tuning-Files/pipeline/pisp-depth2.yaml (the installed file) and pisp-depth4.yaml (num_cfe_config_queue: 4).
  - Z: imx585_clearHDR_nodenoise.json, the Clear HDR tuning without its tdn, sdn and cdn blocks (a worker extends
    working/tools/tdn_strip.py with a --blocks option on the Mac, tested there; never edit defaults-pisp). Its check is
    the BE config dump: TDN, SDN and CDN enable bits clear; otherwise Z is "not this route" tonight.
  - The "before" records; the pre-registration (plan section 6, with the drawn orders), committed and pushed.
0:30-0:50 Preview look, not scored: N, F and Z with peaking and zebra on, a few minutes each. Patrik picks F or Z for B6.
0:50-2:00 Item 1, the depth A/B at 28 fps, TDN off, 4 takes of 3 min in the drawn order, each its own unit: copy the arm's
  YAML to /run/apertar-media/pisp-pipeline.yaml, b1-arm.sh sync through the helper (copy and rm its b1-trace file), the
  tuning and ST/J on the new PID, TAKE_FPS=28 with the unit loop (e3-unit.sh pattern), cut and copy the windows before the
  next Core restart, delete the take's clip folder. Read each take with be_overlap.py --prefix e4 (sections 1, 4 and 7).
2:00 Tell Patrik where the A/B stands, then continue unsupervised with plan section 5 (finish the A/B, B6, the N/F/Z units,
  27 fps, the lossless reading, the restore, push, power off).

RULES (all of them in handoff-drop-frames-tier1.md; the ones that bite tonight):
- Patrik runs or installs every sudo command; the helper allows only the exact commands he reviewed.
- Never edit the installed pipeline YAML or defaults-pisp; copies only. Never disable_tdn. No presets loaded or saved.
- Nothing else on the Pi during a take; WebUI closed; NVMe <= 40 C at each scored unit's start; fill <= 2 % at P1; delete
  only a take's own clip folder.
- Pre-register before the takes; void decisions from the checks alone, before any analysis; never change a rule after
  seeing data.
- Restore at the end: drop-in gone, /run YAML gone, tuning automatic, sysctl back if changed, the restore list read back,
  smart-log; the Pi as Patrik left it (ladder on).
- Commits "<area>: <imperative>", Why/What/Tested, the trailer, "User" not names; KB claims labelled; push only with
  Patrik's OK; Core/UI pushes only when he asks.

STOP AND ASK PATRIK (while he is there): the knob missing, a set_tuning_file error, Core in "error", a void, critical_warning
!= 0, anything outside the plan. Unsupervised: stop the night (restore, push what you have, power off) on any of these.

START: the status check, then the 0:00 message to Patrik.
```

## State after evening 4 (2026-11-04, written by the lead at ~21:05; the campaign is paused)

Read first: `drop-frames/recipe.md` (the whole campaign in one table), then
`drop-frames/tests-2026-11/findings-evening4-supervised-2026-11-04.md` and the end of `preregistration.md`.

- **Result**: at 28 fps the remaining single-frame losses are the FE Config queue running dry, and depth 4 removes them
  (probable, n = 1 + 1; Inconclusive by the rule). 30 fps loses ~3 frames in 2 min even at depth 4, from a second limit
  (the back end slows, its queue grows; memory bandwidth suspected, unconfirmed). User stopped the campaign at ~21:00.
- **The Pi**: restored and read back (list in `preregistration.md`, "Evening 4 ends"); left on. The helpers
  (`/etc/sudoers.d/apertar-e4`, `apertar-e4-helper`, `apertar-b1-arm`) are still installed: User removes them.
- **Next (User's request at the end)**: a clean Core branch with only the proven measures, merged into the local
  `cinemate-port`. Not started at this writing.
- **If the campaign resumes**: a second clean D4 take at 28 fps settles the A/B; then B6 at 28 fps with D4 and TDN off.
  For 30 fps, the untried levers are Log (16 -> 12 bit), direct I/O for the DNG writes, a smaller ISP preview output.
