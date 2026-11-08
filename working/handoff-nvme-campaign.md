# Handoff: the NVMe 4K campaign on the Corsair cards (Opus lead in VS Code on the Mac, Sonnet workers)

For: a Claude Code session in VS Code on the Mac, model Opus, with the `apertar-dev` skill, working with Patrik and driving the Pi over
`ssh apertar`. Written 2026-11-08 by the cloud session that researched the record and wrote `working/drop-frames/nvme-campaign/plan.md`.
Before pasting: the KB PR carrying the plan is merged; pull on the Mac and the Pi (`apertar_publish.sh kb`). Paste the block below, or say
"read `~/Documents/Apertar/apertar-kb/working/handoff-nvme-campaign.md` and start".

---

```text
/apertar-dev You are the lead of the NVMe 4K campaign for Apertar: an unsupervised test campaign on Patrik's Corsair MP600 Mini 1 TB
CFexpress cards, the media he shoots with. Target: the longest drop-free 4K cDNG take per mode and fps, the recipe that produced it, and
whether splitting a clip into folders matters for long takes; 30 minutes is the goal. Patrik decides; he runs every sudo step through a
reviewed root helper. Sonnet workers (Agent tool, model "sonnet") do bounded desk jobs on Mac copies of the data and never touch the Pi.

READ FIRST (Mac ~/Documents/Apertar/apertar-kb/):
1. working/drop-frames/nvme-campaign/plan.md: all of it. Sections 3 (arithmetic), 5 and 5a (fixed state, levers, audio), 6 (stages), 7
   (the pre-registered rules), 8 (wear budget), 9 (runner and monitoring). Where this prompt and the plan disagree, the plan wins; say so.
2. working/drop-frames/nvme-campaign/build-list.md, SECTION H (the consolidated list; it supersedes the numbered items above it): the
   runner's base is the unmerged branch claude/practical-johnson-he481b (49c6f46), which already has the fit gate, the watchdog, the
   budget cap, the lock and the sampler columns the plan reads; H0 is to merge it or build on it; never use its --fix-budget (0.9/256).
   H0-H4, H6 and H18 block the smoke test (S0); H24 blocks S1; H5, H7-H15, H17, H21, H23 and H26 block S2; H22 S5; H25 S6; H16 the long tiers; D is the root helper in two parts, E the Core items. Then working/drop-frames/nvme-campaign/research/R10-longtakes-runner.md (how
   longtakes.py works today and its risks) and working/tools/longtakes.py itself.
3. working/drop-frames/nvme-4k-recipe-plan.md (the capture-side ruling-out rules you inherit), working/drop-frames/storage-slowdown-plan.md
   (the storage mechanisms and the buffer-as-a-meter method), working/drop-frames/nvme-campaign/probe-exfat-dir.md (the measured directory
   cost and its pre-registered rule), working/drop-frames/recipe.md (the measures that made 4K Clear HDR 16-bit run clean).
4. working/drop-frames/nvme-campaign/research/R1-take-ledger.md section 4 (the confounders: position after a restart, instrumentation,
   WebUI, fill, trim, heat, two cards) and R2-lever-inventory.md section 5 (what you must not do; its binary facts are stale: the camera
   runs cinemate-port 01f170c, i.e. ba0658d plus the two merge-worker fixes, since the 2026-11-08 13:00 boot).
5. working/drop-frames/nvme-campaign/critique/ (the critiques and the skeptic's verdicts): what the plan changed and why.
Then run ~/.claude/skills/apertar-dev/scripts/apertar_status.sh and report: Core and UI tips on the Pi and GitHub, the running binary
(expect cinemate-port 01f170c or later; get_state must show frames_per_folder, clip_merge_enabled, cdng_log, buffer_setting, recording_dropped_frames), the mounted card
(model, serial, size, part number: expect a Corsair MP600 Mini; refuse to start on anything else without Patrik's word), helpers
installed, cmdline (FE depth 4 YAML? nvme args?), the media tune file, the ladder, the KB HEAD on the Mac and the Pi against GitHub
main. Stop and say so if anything differs from the plan's section 2.

THE ORDER OF WORK:
Phase 0, desk (one evening, nothing on the Pi but reads):
  - The audio fault of 2026-11-08 (plan 5a; the take C0005 of clip-split-verify.md, `recording failure: fault=write_error ... ALSA capture:
    Broken pipe` at 32 s): it ran with frames_per_folder 200 at 25 fps and stopped with 799 frames written (indices 0-798), within one frame of the
    part_003/part_004 boundary at index 800 (a part boundary every 8 s), so the boundary path (folder creation and its fsync, in the diff f4a1393..01f170c) is the first
    suspect; then pull that take's journal window (the failure line, the stop reason,
    "audio writer: peak_backlog_kb", any usb or compaction line at that second) and read src/audio/AudioRecordingSession.cpp and
    src/audio/TimestampedAudioCapture.cpp at 01f170c (unchanged since ba0658d): does an xrun end the take? If yes, propose the Core fix to Patrik (snd_pcm_recover,
    pad the gap with silence, log "audio discontinuity", continue) as the first Core commit, before the long tiers, with a host test where
    possible. Read the request format of POST /api/media/delete in src/.../WebControlPage.cpp at 01f170c before writing H5.
  - The build list's section H on longtakes.py (branch base first), with host tests (tools/longtakes_test.py, H18), reviewed by a Sonnet
    worker against R10's risk list and C2 section 3; the campaign root helper (D: read-only words for the runner, interactive-only words
    for Patrik) drafted for his review; the pre-registration page (nvme-campaign/preregistration.md) from
    the plan's section 7 with the die rolls Patrik gives you for the ABBA orders.
Phase 1, S0 with Patrik (about 2 h): the clip-split verification is on record (nvme-campaign/clip-split-verify.md), do not repeat it; instead
  one forced-drop check of which journal lines this binary prints per drop (no drop line has been seen yet because no verification take
  dropped; the KB's code reading says they print on a gap); the crop probe (list_sensor_modes and one set_resolution read-back per planned
  crop and bit depth, heights into H17); the tuning back to automatic with Patrik if a manual file is active; the ladder off and read back;
  audio-usb once; the Mac stand-in's reconnect checked by pulling the Mac's network for 60 s; the helper and sudoers
  installed by him; the campaign drop-in armed (ONE line, LIBCAMERA_RPI_CONFIG_FILE to the depth-4 YAML the runner copied to /run/apertar-media; no debug
  log) with a Core restart and an environ read-back; the merge switched off over the socket (set_clip_merge enabled=false) and read back;
  the pre-roll stays on as in real use; Patrik's footage offloaded from the card; fsck.exfat -n; the campaign timers masked by the helper;
  the power check; smart-log baseline;
  fstrim; the smoke test (--max-seconds 20 --only 1) that must show buffer_used at 1 Hz
  in the samples and the audio lines in the take record.
Phase 2, S1 (about 1 h, no camera, Core idle): storage_facts.sh; the 60 GB direct write with a 1 Hz bandwidth log (link-limited on the Pi,
  no knee expected; it confirms the rate and starts the temperature record); the write-pattern matrix; the drive-state writes; the paced
  small-file probe only if Patrik buys it (plan 6 S1).
Phase 3, S2 (one night, unsupervised): start the runner detached for the screening (the fps walk, the ABBA lever pairs, the one stop-on-drop Log take at 30 fps HDR16, the
  TDN-on take; the 5-min confirmation take runs inside each mode block as the second concordant take of a clean cell); read status.md between takes; after S2 write the prognosis page (survival tables per
  cell, lever verdicts, the audio trend) and send Patrik the go/no-go for the long tiers (the runner waits for the GO-S4 sentinel; GO-S5, GO-S6 and GO-PARTB follow, each
  placed in advance only with its pass condition, and an 8-h wait ends the night cleanly).
Phase 4, S4-S6 (two to three nights): the 15-min unsplit takes ordered HDR16 -> heaviest SDR12 -> HDR12 so the second ends near 80-92 % full; the 30-min tier (the gate empties the card only
  when a take does not fit), unsplit first for arms below the 60 % create share and SPLIT FIRST above it (SDR12 at >= 33-42 fps: plan section 3); the soak as
  the split variant; the conditional work. Patrik's OK per tier is a GO file placed BEFORE the night with its pass condition (GO-S5
  before night 2: "if every S4 take passed"; GO-S6 before night 3), else the runner idles after S4 and the night is lost; the survival
  table per cell from status.md goes with each GO decision; on a smaller card a take that does not fit is shortened to
  (free - 10 GB) / (1.03 x rate) and recorded fit-limited.
Phase 5, Part B (one evening per other Corsair card, Patrik swaps the card and has offloaded its footage): the card's part number (a QLC
  CORE Mini is refused), serial, fsck and trim-at-mount recorded; the 60 GB knee probe; one 30-min take of the winning HDR16 arm and one
  15-min take of the heaviest SDR12 arm by default; the other 30-min takes only if Patrik asks.
Phase 6, desk: the findings page, the recipe per mode, the duration-vs-fps table, hardware-log entries after Patrik confirms each reading,
  the end-of-campaign delete and trim, the restore list read back, the helpers removed by Patrik.

RULES (the plan's section 7, and R2 section 5 except its items 1, 6, 17 and 20, which the plan supersedes: the binary is 01f170c, S1
writes probes to the card, there is no 75 % ceiling, a stopped night leaves the Pi on; the ones that bite):
- Patrik runs or installs every sudo command; the helper allows only the exact words he reviewed. Never widen sudoers; never run sudo yourself.
- Never record while a build runs; never build while a take runs; nothing else on the Pi during a take (no journalctl, no top or htop, no ls /media/RAW,
  no second WebUI: the Mac stand-in is the only client); status.md and decisions.log are written between takes and read between takes.
- Never delete with a glob; the runner deletes only folders in its own database, never Patrik's clips; deletes normally in the boot that
  wrote them (a cold delete is budgeted per plan section 6); never format without Patrik.
- Never edit defaults-pisp or the installed pipeline YAML; copies only. Never disable_tdn. Never load or save presets. Ladder off for takes.
- Pre-register before the takes; void decisions from the checks alone; never change a rule after seeing data; never upgrade a label.
- The take stops at its first dropped frame (any counter), at Core's safety stop or at an audio fault; a cell is eliminated after two
  concordant drops (a deviation from "one drop = out" that Patrik confirms or reverts); the 5-min take is the second concordant take of a clean cell;
  a single late frame is repeated once; "better" needs the pooled controls, the pre-registered direction and an ABBA replicate; an audio
  fault is its own outcome and never eliminates an arm alone; a take without an audio capture line is void (audio_missing); if the Core
  audio fix is not in by the long tiers, they run with APERTAR_AUDIO_BUFFER_MS=1000 as a recorded deviation.
- Unsplit first at the 30-min tier for arms below the 60 % create share (the split member only on a late drop with the directory signature,
  or as the soak); split first above it.
- A Pi reset ends the night: the runner resumes only when the helper's status shows the drop-in re-armed, fsck clean and the last status clean (WAITING: re-arm).
- No cool-down; temperature logged and reported, never gated; a take ending above 75 C is flagged.
- The budget: 10 TB on the campaign card, projected before every take; a 30-min take is never repeated to make sure unless void.
- Commits "<area>: <imperative>" with Why / What / Tested and the trailer, "User" not names; KB claims labelled; push only with Patrik's OK;
  Core/UI pushes only when he asks.

STOP AND ASK PATRIK (or stop the night when unsupervised: restore, write the status, leave the Pi on): the mounted card is not the one you
expect; get_state lacks a field the runner needs; a set_* command is refused; Core in error; critical_warning != 0; a kernel nvme/pcie/exFAT
line; media_alive false; an under-voltage event; a second void; a second audio fault in one night; a runner crash; the write budget
reached; any kernel move to 6.18.y before its NVMe fix; anything outside the plan and the pre-registration.

START: the status check, then the Phase 0 plan as one message to Patrik with the questions of plan section 11 (item 8, the two-concordant
deviation from "one drop = out", asked in so many words).
```

## State to fill in at handoff time

- Core / UI tips on the Pi and GitHub; the clip-split verification record (exists? where); the audio-fault take's journal window; helpers
  installed (which); the drop-ins present.
- The campaign card's serial and part number; the other cards' part numbers (CSSD-F1000GBMP600MN / MNR2 / CMN) and labels.
- The dice for the ABBA orders (Patrik rolls, or asks the lead to roll with the method recorded).
