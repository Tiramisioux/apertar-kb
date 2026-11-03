# Handoff: run the drop-frames test plan (Opus lead in VS Code, Sonnet workers)

For: a Claude Code session in VS Code on the Mac, model Opus, with the `apertar-dev` skill, working with Patrik and
driving the Pi over `ssh apertar`. Written 2026-11-02 by the cloud session that wrote the inspection. Paste the block below
as the first message, or say "read `~/Documents/Apertar/apertar-kb/working/handoff-drop-frames-tests.md` and start".

Before pasting: the inspection must be on the Mac. It is KB PR #5 (`claude/drop-frames-inspection`); merge it, then run
`apertar_publish.sh kb` (or `git -C ~/Documents/Apertar/apertar-kb pull`) so the Mac and the Pi have it.

---

```text
/apertar-dev You are the test lead for the Apertar drop-frames campaign, running the test plan of the 2026-11-02 inspection
on the Pi with Patrik. You decide, drive the Pi and read every result against the plan's own decision rules. You hand the
bounded, mechanical jobs to Sonnet workers (Agent tool, model "sonnet") and review everything they return. Patrik decides
anything the plan marks as his.

Read first, in this order (all in ~/Documents/Apertar/apertar-kb/):
1. working/drop-frames/inspection-2026-11-02.md: section 8.1 (verdict) and 8.3 (the test plan) in full; 8.4 and 8.5 when
   you reach code or the hardware log. This is the plan. Where this prompt and the plan disagree, the plan wins; say so.
2. working/drop-frames/night-2026-11-01.md sections 2, 5 and 6 (the takes, the Pi's runtime state, the traps).
3. working/handoff-drop-frames-fable.md, the block after the line: Patrik's rules for this work. They still hold.
4. llm/README.md §2 and §5 before reading any code (grep anchors; never read the 8-12k-line files whole).
Then run ~/.claude/skills/apertar-dev/scripts/apertar_status.sh and report: Core and UI branch tips on the Mac, the Pi and
GitHub (expected: Core drop-frames adac040, UI drop-frames c13b846, main untouched), what is running on the Pi, the drive
fill, and whether the KB on the Pi has inspection-2026-11-02.md. Stop and say so if any of it differs.

The targets (Patrik's): 4K Clear HDR 16-bit uncompressed cDNG at 25 fps with 0 lost frames while the touch UI shows the
live picture with focus peaking and zebra on (first); 4K SDR 12-bit at 33 fps (second).

Where things stand: sync mode (adac040) removes the page-cache reclaim regime (measured); that it removes the losses is
probable, not proven (take-level p = 0.057, order-confounded). The likeliest mechanism is G: memory contention lengthens
libcamera's serial per-frame cycle until the camera skips single frames. The plan's job is to settle the mode (B1), the
start state and drive fill (B3), and then confirm the targets (B6, B7).

ORDER OF WORK (from 8.3; durations are the plan's estimates, about 14 h over five evenings):
- Evening 0, B0 (1.5-2 h, no takes): facts (M0), record checks, the transcript numbers, the journal-line commit and the
  adac040 build, take3v3.sh, the root scripts, one reboot with psi=1 and rp1_cfe.track_csi2_errors=1, the helper and
  sudoers install with APERTAR_MEDIA_TUNE unset, the UI reverts if Patrik agrees, warm.bin, smart-log baseline,
  pre-registration of B1's rule and the restore list in the KB.
- Evening 1: B1 (two blocks, about 2 h 20 min), then B2's first two rows if B1 points at them.
- Evening 2: B3 evening 1 cells (a) (b) (c).
- Evening 3: B3 evening 2 cells (a) (e) (c') (d) with the fill, then T1 and B4.
- Evening 4: U1, B6, B7, B-lossy; T2, B5 and B8 only if their conditions hold.
Re-plan after each evening from what the decision rules said; tell Patrik in one paragraph what changed and why.

WHAT YOU DO YOURSELF (never a worker):
- Every command on the Pi, including read-only ones. A worker never touches the Pi: an ssh from a worker during a take
  breaks "nothing else on the Pi".
- Test design calls: drawing B1's order (ask Patrik to roll the die, or use one documented random draw, written into the KB
  before the block), whether a take is valid or void, when to extend a block, when a conditional test runs.
- Reading every result against the plan's decision rules, and every interpretation that leads to a mechanism (G, A, H, C,
  E, B, F in 8.2 Q4). Mark each reading measured / probable / unconfirmed.
- Every message to Patrik, every sudo block you give him, and every decision he has to make.
- Reviewing every worker diff and script line by line before it is committed or copied to the Pi; rerunning the host checks
  yourself. Root scripts additionally go to Patrik for review before he runs them.
- Commits, the fork-log row for each, pushes to the Pi's staging branch (working/mac-driven-loop.md), and GitHub pushes only
  when Patrik asks.

WORKER JOBS (Sonnet; one job per worker; give each the preamble below, the job's paragraph from here, and the plan section
it implements):
W1 Transcript numbers (B0 step 3, no take). Find the 2026-11-01 Mac session transcript (~/.claude/projects/, the session
   that ran takes #69-#80; grep for "compaction during take:"). Extract, per take #70-#80, every delta that line printed
   (pgscan_direct, allocstall_normal, allocstall_movable, pgsteal_kswapd, pageoutrun, compaction counters) and #80's
   "capture stats" / "recording stats" lines and take3.sh output. Return a markdown table plus the raw lines. You put them
   into the night report section 2 and read them against B0 step 3's readings.
W2 Journal line (B0 step 4). In Apertar-Core on drop-frames, add " dontneed=<mode> writeback=<on|off> sync_ms=<N>" to the
   "recording clip:" stderr line after media_fs= (CameraController.cpp, anchor `media_fs=`), values from dngPageCacheDrop(),
   startWritebackPerFrame() and the SYNC_MS value the take uses. Nothing else. Return the diff and confirm
   working/tools/drop-frames-2026-11-01/takes_from_journal.py still parses the line (run it on a sample line).
W3 Root scripts (B0 step 6, B4's readings, B5's csi2 read). Draft b1-arm.sh <writer|sync> exactly as step 6 describes, and
   a b0-readings.sh for the root-only readings (slabinfo rows, csi2_errors, smart-log). POSIX sh, set -eu, prints every value
   it changes, idempotent, no rm outside /run/systemd/system/apertar-core.service.d/, no glob deletes, a --dry-run mode.
   Return the scripts and a list of every file they write. You review; Patrik reviews; Patrik runs them with sudo.
W4 UI reverts (B0 step 9, only after Patrik agrees). In Apertar-UI on drop-frames: git revert --no-commit c13b846, commit as
   "ui: <imperative>" with Why/What/Tested and the trailer; then 4724007, 322d329, a51c95e the same way, newest first. Return
   the four commits' messages and `git diff 41ff827..HEAD --stat` (expected: only 68e1a41 and c234d77 remain). Draft the four
   fork-log rows. You review, then the UI rebuild happens on the Pi (you, not during a take).
W5 Pre-registration page (B0 step 11). Write working/drop-frames/tests-2026-11/preregistration.md: B1's unit, blocks,
   stratified exact permutation test, attainable p, manipulation check, decision rule, copied from 8.3 B1 word for word;
   the restore list from 8.3; an empty table per test for results. No interpretation.
W6 Analysis script (before B1's first block). working/tools/drop-frames-2026-11-01/b1_test.py: input a CSV (block, unit,
   arm, P1_lost, P2_lost, P1_memfree, P2_memfree, P1_pgsteal_kswapd, P2_pgsteal_kswapd); output the exact one-sided
   permutation p stratified by block for per-unit lost = P1 + P2, the manipulation check (writer pgsteal >= 10x sync in
   every take), and P1/P2 per arm. Pure Python, no numpy. Include a self-test: two blocks with complete separation must give
   p = 1/36, three blocks 1/216. Return the script and the self-test output.
W7 After each take: give the worker the take3v3.sh output and the /dev/shm 1 Hz log you copied to the Mac. It returns one
   row for working/drop-frames/tests-2026-11/takes.md (take id, test, arm or cell, start MemFree, lost per minute, total
   lost, the whole-take deltas, G1 IPC and cycles, peak NVMe latency, drive fill before and after, valid or void with the
   reason) and the minute-by-minute table. It does not interpret. You check the row against the raw output before it goes in.
W8 B3 fill script (before B3 evening 2). A script that writes 16.6 MB files into /media/RAW/fill-2026-11/ to 50 % of the
   volume, deletes every other one, then writes to 72 %, printing progress and stopping at the target from df; it deletes only
   inside /media/RAW/fill-2026-11/. Return it with a --dry-run that prints the plan. You review and run it.
W9 Text corrections (only after M1 has counted the drain, 8.4 and 8.5). Draft the README knob row, the comment in
   CameraController.cpp, lessons/upstream-issues.md #44 and the new hardware-log entries listed in 8.5, using the wording
   there and the measured numbers you give the worker. Hardware-log entries go in only after Patrik confirms each reading.
W10 Code follow-ups the plan names, only when their test says so: the one-line std::cerr for a failed open() of the clip
   folder and the stale exFAT comments (8.4, after B1); the MINFREE column in scripts/apertar-media-tune (only if B3 shows
   min_free_kbytes engaging and helping); routing lossy files through noteWrittenFile (only if B-lossy loses frames).
   One worker per change; one commit per change.

Preamble for every worker:
  You are a worker on the Apertar drop-frames campaign, on the Mac. Repos: ~/Documents/Apertar/Apertar-Core,
  ~/Documents/Apertar/Apertar-UI, ~/Documents/Apertar/apertar-kb. Read ~/Documents/Apertar/apertar-kb/llm/README.md §2
  and §5 first if you touch code: find code with grep anchors, read about 100 lines around a hit, never read
  CameraController.cpp or ApertarCoreApp.cpp whole. Do exactly the job described, nothing else. Never run anything on the
  Pi (no ssh, no scp), never push, never use sudo, never delete anything outside the paths the job names. Commit only if the
  job says so. Return: the files you touched, a unified diff or the full new file, the checks you ran with their output,
  and anything that differed from what the job assumed.

RULES THAT MATTER MOST (from the plan and Patrik; the full lists are in 8.3 and the fable handoff):
- Patrik runs every sudo command. Give him exact blocks; after a reboot sudo asks for his password.
- Nothing else on the Pi during a take: check `cc1plus|gmake|cmake` before and after; WebUI closed (the script refuses).
- Delete only the take's own clip folder, read from its "recording clip:" line. Never a cDNG_* glob. Ask Patrik once in
  B0 what on /media/RAW must be kept.
- Never write /proc/irq/*/smp_affinity for RP1 interrupts. No hot-unplug of the NeoRotary (poll_ms instead).
- The NAND-stall cell (untrimmed 0.9 TB) is dropped; run it only on Patrik's explicit OK with nothing of value on the drive.
- NVMe at or below 40 C at the start of a scored unit; stop on any smart-log critical_warning != 0.
- At the end of every evening: the restore list in 8.3, read back, so Patrik's next shoot inherits nothing.
- Commits: "<area>: <imperative>", Why/What/Tested, Co-Authored-By trailer, "User" not names, one per change, a fork-log
  row each. KB claims labelled confirmed / measured / probable; a hardware-log entry only after Patrik confirms the reading.
- Prefer extending an existing knob or script to adding one.

START: report the status check, then B0 step 1 (M0) as one read-only ssh block, and spawn W1 and W6 in parallel while it
runs (neither touches the Pi). Then ask Patrik the three B0 questions he has to answer: the UI reverts (yes/no), what on
/media/RAW must be kept, and when he can do the reboot.
```

---

## State after evening 1 (2026-11-02, written by the lead session at 23:2x)

Read first: `drop-frames/tests-2026-11/preregistration.md` (B1 rule, orders, every unit's row, the result),
`drop-frames/tests-2026-11/findings-2026-11-02.md` (the starvation finding, method notes, re-plan),
`drop-frames/media-tune-file.md` (the new tuning file), night report §2.1 (B0's facts and record checks).

**Done:** B0 (all 11 steps) and B1 (both blocks, the plan's evenings 0 and 1 in one night).
- **B1 result:** writer units 407, 320 | 252, 232 lost vs sync 48, 108 | 73, 80; p = 1/36, manipulation check PASS:
  the mode is the lever (Q1 settled). Position not reproduced; G probable (CameraManager IPC lower under writer);
  A and H not supported.
- **Mechanism (measured, 8 of 8 takes):** every lost frame is a moment when the CFE raw node had no buffer
  (`vb2_buf_done` `owned_by_drv = 0` count = lost count). A take is clean (driver holds ~5-6.5 of 8 raw buffers on
  average) or losing (~2). writer lowers it by ~1. Under sync one take per unit fell into the losing state
  (47-108 lost) without reclaim, and both warm-ups lost (17, 9). What flips a take is open. "The second take of a
  Core process loses" was said and is **refuted** (block 2 unit 3: 225 then 7).

**State of the Pi at the end:** restore list read back (findings §6). Core `drop-frames` `46d0e8c` **built, not yet
running** (the running Core is `48f8b8c` until Patrik restarts it). UI `c153c33`. `~/apertar-media-tune.conf`
created (`apertar-tune init`): the B1 values (sync, writeback on, sync_ms 1000, raw_buffers 8, kernel_tune off;
exfat/ext4 workers 4, queue 12, extra 0). `/etc` drop-ins unchanged: `zz-ladder-buffers.conf`
(`APERTAR_RAW_CAMERA_BUFFERS=8`) still wins over the file's `raw_buffers` until Patrik removes it. `warm.bin` on the
drive (2.5 GB, keep for B3). Installed in B0: `apertar-media-tune` helper + sudoers (TUNE unset), nvme-cli (pulled
util-linux 2.41.5: a fixed difference from 11-01; its two nvmf boot units disabled). cmdline `psi=1` (backup
`cmdline.txt.bak-20261102`).

**Tools as they are now** (`working/tools/drop-frames-2026-11-01/`):
- `b1-arm.sh <writer|sync|restore|save> [--trace-buffer]`: per arm it saves the previous trace to
  `/dev/shm/b1-trace-<HHMMSS>.txt` (owned by the sudo user: copy it to the Mac and delete it, or the unit loop waits),
  writes the `/run` dontneed drop-in, restarts Core, filters `vb2_buf_done` to the raw node
  (`type == 1 && bytesused > 10000000`). `--trace-buffer` once per boot. Patrik runs it once per unit; twice is
  harmless (the second restart is the unit's), the wrong arm before any take is harmless.
- `take3v3.sh`: picks the CameraManager thread with the most run time over 2 s right before `record_start` (a mode
  change replaces those threads); clears `csi2_errors` before the take (the file is cleared on every read; the 1 Hz
  logger is its only reader during a take); NVMe temperature from `/sys/class/nvme/nvme0/hwmon*/temp1_input`.
- The unit loop the lead ran: wait for Core's pre-roll delete, then for no `/dev/shm/b1-trace-*` file and the NVMe
  <= 40 C (up to 30 min, else NOT STARTED), `cat warm.bin`, P1, P2. Cool-down from ~60 C takes 15-20 min.
- `scripts/apertar-tune` (Core repo): `set raw_buffers=16` etc. into `/run/apertar-media/media-tune.override.conf`;
  `clear` at the end of every evening (restore list).

**Next (agreed with Patrik 2026-11-02):**
1. Patrik: `sudo rm /etc/systemd/system/apertar-core.service.d/zz-ladder-buffers.conf`, `sudo systemctl
   daemon-reload`, `sudo systemctl restart apertar-core`; check the journal for `ApertarCore media tune: file=...`
   and `RAW buffers: ... count=8`.
2. The 16-raw-buffer try (Patrik's request, outside the plan, unscored): `apertar-tune set raw_buffers=16`, arm
   sync with `--trace-buffer` after a reboot, one unit (P1 + P2) with the raw-node trace; compare with B1's four sync
   units (48-108 lost, one losing take each). If both takes are clean with no `owned_by_drv = 0`, repeat before
   writing 16 into the base file. Precedent: 12 buffers under writer on 11-01 (#41) had no effect.
3. B2's first rows under sync on losing takes: G2 (libcamera stage timing) and M6 (stacks of the thread holding the
   buffers), the raw-node trace on.
4. B3 as planned (its `pageoutrun > 0` validity rule decides whether the knobs can speak under sync).
5. T1 needs ~35,000 s of uptime (A0's position): boot the Pi ~9.7 h before.
6. `takes.md` has rows up to block 1 unit 2: a W7 for block 1 units 3-4 and block 2, from
   `drop-frames/tests-2026-11/raw-2026-11-02.tgz` (every 1 Hz log, console output, G1 file and block 2's filtered
   traces; block 1's unfiltered traces, 90 MB and partial, are not kept).

---

## State after evening 2 (2026-11-03, written by the lead session at 22:0x)

Read first: `drop-frames/tests-2026-11/findings-2026-11-03.md` (the mechanism, what did not cure it, next), then the
evening's sections of `preregistration.md`.

**Result:** a losing take is libcamera's ISP back end slowing to >= ~40 ms per frame under memory contention (measured
with libcamera's debug log, and reproduced without any recording by two `dd` memory loads: back end 11 -> 95 ms). Not
cured by 16 raw buffers, a 12-fps UI preview or `buffer=frames`; the preview-off unit was clean (0 + 0) but the
dose-response is not monotone. B3's knobs are unlikely to help (reclaim is a co-factor, not the cause).

**State of the Pi at the end (22:0x):** restore list done and read back: no `/run` drop-in for Core, no override
(`/run/apertar-media` empty but the tmpfiles dirs), `buffer=ram`, trace events off, buffer 1408 KB, Core on its
defaults (`IPARPI:ERROR` from `/etc`). **On User's request:** the UI runs with `APERTAR_UI_PREVIEW_RECORDING_FPS=12` from
`/run/systemd/system/apertar-ui-direct.service.d/zz-preview-fps.conf` until the next reboot (the evening's data does not
support it as a fix: 12 fps lost 330 in a P2). New since evening 1: `/etc/tmpfiles.d/apertar-media.conf` installed.
smart-log: `critical_warning` 0, 41 C, Data Units Written 53,634,400 (0.84 TB tonight), unsafe shutdowns 1,538.
Drive: `warm.bin` and three clips of User's (21:57-22:00, not test takes).

**Open for User:** the ladder (rung 2 SDR12 <= 50 uncompressed vs 11-02's <= 30 lossless; rung 1 HDR16 lossless at ~17 fps
encoder capacity); the two test clips `cDNG_26_11_03_20533423_C0001` and `cDNG_26_11_03_20571717_C0001` on User's
Crucial P310 card (pulled while mounted): delete only those, after a read-only `fsck.exfat -n`.

**Next:** plan the memory-traffic step with User (findings-2026-11-03 section 4): first measure which part of a take's
write path carries the traffic, then the candidates (O_DIRECT writes, the raw copy, the back end's preview output).
