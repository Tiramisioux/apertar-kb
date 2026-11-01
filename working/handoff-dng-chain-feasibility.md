# Handoff: drop-free 4K50 SDR and 25 fps Clear HDR 16-bit on Apertar (Mac, Claude Code in VS Code, Opus thread, Sonnet workers)

For: the next `apertar-dev` session on the Mac, in Claude Code inside VS Code, Opus as the thread, Sonnet workers for the
scoped tasks. Written 2026-11-01 in a cloud session that could read code and logs but never reached the Pi. Paste the part
below the line as the first message, or say "read `~/Documents/Apertar/apertar-kb/working/handoff-dng-chain-feasibility.md`
and start".

The verdict page is `working/dng-chain-feasibility.md`; the earlier answer page is `working/dng-chain-answer.md`; the code is
Core PR #3, merged into `drop-frames` on 2026-11-01. This file is the work order.

---

You are driving the next phase of the dng-chain work on Apertar from the Mac. The question is whether Apertar can record
drop-free at (A) 4K SDR 12-bit 50 fps and (B) 4K Clear HDR 16-bit 25 fps, with and without Log. A cloud session has
already done the reading, the budgets and the verification; your job is the measurements, in the order below, and the
decisions they unlock. Nothing from that session has run on the Pi yet.

## Read first, in this order (do not re-derive what is there)

1. `~/Documents/Apertar/apertar-kb/llm/README.md`, then `working/mac-driven-loop.md` (the loop: Claude on the Mac, Pi over
   ssh `apertar`, Patrik runs `sudo`, nothing else on the Pi during a take).
2. `working/dng-chain-feasibility.md` §0 (the verdicts), §6 (the ten tests, with tools, durations and pass criteria),
   §5 (what it corrected in the older page), §7 (open questions). Then `working/dng-chain-answer.md` §0 and §6 (the E-plan
   the tests map to). Detail, only when a number is challenged: `working/dng-chain/F/F1..F6.md` and `V-F1..V-F6.md`.
3. `lessons/hardware-log.md` from 2026-10-25 to the end, so every new entry matches the house style (Tested / Seen / Why /
   Confirmed by) and nothing already measured is repeated.
4. The Core README's "Write-path knobs for A/B tests" table on branch `claude/adoring-euler-n8zi0j` (the nine knob-gated
   commits over `drop-frames` 92d0970; PR #3, draft, unbuilt).

Both PRs were merged by Patrik on 2026-11-01: Core PR #3 into `drop-frames` (its head `6ef0ddc`; PRs #4 and #5 from other
sessions landed on `drop-frames` right after it, so build the `drop-frames` head, not `6ef0ddc`), and kb PR #3 into `main`.
One kb follow-up (the critic's fixes to the feasibility page and this paragraph) is on branch `claude/adoring-euler-n8zi0j` as a
new draft PR; merge or fetch it. On the Mac: `git -C ~/Documents/Apertar/Apertar-Core fetch origin drop-frames` and
`git -C ~/Documents/Apertar/apertar-kb pull origin main`. Then run `~/.claude/skills/apertar-dev/scripts/apertar_status.sh`
and report the Core and kb branch tips on the Mac, the Pi and GitHub before anything else.

## Patrik's rules for this effort

- Patrik runs `sudo`, service restarts, drop-ins, `fio` on the media volume, reboots. Give him the exact command block
  each time, say what it does and what to read back, and wait.
- One thing on the Pi at a time. No build, no VS Code Remote, no second Claude on the Pi while a take or a `fio` run is on.
- Every take records the confounder set before it starts: WebUI clients (`ss -tnp | grep 8080`), `fps_speed_ramp`
  (`get_state`), `storage_preroll_auto`, trim time (`media_trim_last_unix`), pre-roll state, tuning file in use and its
  `tdn` count, first-take-after-reconfigure, loaded libcamera build, raw buffer count, the journal's
  `camera configured ... packing=` line. Judge drops from `dropped_gap_estimate`, `dropped_queue_full`,
  `dropped_copy_slot`, `peak_queue` and frames against WAV seconds x fps. Never from `takes.sh missing` alone: with the speed
  ramp on, numbering is count-based and hides gaps.
- The first take after any reconfigure or reboot is discarded. Three interleaved takes per arm before a number is quoted.
- Every result goes to `lessons/hardware-log.md` as a dated entry, labelled measured / derived / estimated, only after
  Patrik confirms the interpretation. Update `working/dng-chain-feasibility.md` §0 and §6 when a test changes a verdict;
  never silently.
- Core changes stay knob-gated, one change per commit, `<area>: <imperative>` title with Why / What / Tested body. Code
  only when a measurement asks for it (see "Decisions" below). Build on the Pi only (`cmake --build ~/ApertarCore-build
  -j2`), never during a take. Publish to GitHub only when Patrik asks.
- The subject is Apertar. cinemate is a reference the operator raised; it has no counted take of either mode.

## How to use the Sonnet workers

Keep the thread (Opus) for decisions, interpretation, hardware-log entries and page updates. Delegate to a Sonnet worker any
task that has a fixed procedure and a fixed output shape. Each worker gets, in its prompt: the exact commands, the pass
criterion, the confounder checklist, where to write its raw output (`~/Documents/Apertar/apertar-kb/working/dng-chain/F/runs/<date>-<test>.md`,
create the folder), and the return format: a table of measured values with units and the log line or file each came from,
then one line "pass / fail / inconclusive" against the criterion. Workers never run `sudo`, never restart the service,
never start a take while another is running, never interpret beyond the criterion, never write to `hardware-log.md` or the
answer pages. Good worker tasks: test 1 (DNG clock forensics over 38 clips), test 2 (rig read-back), parsing a `be_cycle.py`
run, computing fps and gaps from a journal window, diffing two tuning files, checking a knob's effect in the stats line.
Bad worker tasks: deciding whether a verdict changes, writing the log entry, choosing the next test.

## The tests, in order (full detail in `working/dng-chain-feasibility.md` §6)

1. **DNG clock forensics, zero rig time.** The 38 clips of the 2026-10-28 shooting day on the SEAGATE disk were shot on the
   10-27 temporary build offering 4K lossless at 25/33/50 fps. Per clip: `exiftool` `DateTimeOriginal` counts per full second
   against the clip's fps, plus width, bit depth and compression from one DNG (method: `hardware-log.md:889-897`). Also the
   A2 clip if still on the card. Decides: whether a multi-minute 4K lossless datum above 25 fps already exists.
2. **Rig state, read-only (E0).** `grep -c '"tdn"' /home/pi/Tuning-Files/defaults-pisp/imx585*.json`; the journal's
   `tuning file`, `capture scheduling`, `pixel-rate cap`, `RAW buffers`, `camera configured` lines; which libcamera is
   mapped; `systemctl show apertar-core -p LimitNICE -p LimitRTPRIO -p Environment`; `clk_sys` (expect 333333333);
   `nvme id-ctrl /dev/nvme0 | grep -E 'mn|fr|vwc|hmpre'`; `findmnt /media/RAW`; `df -h /media/RAW` (a 10 min (A) take needs
   373 GB free); `swapon --show`; `get_state` for `fps_speed_ramp`, `storage_preroll_auto`, `ladder_enabled`. Decides: whether
   TDN is on at all, and every later number's preconditions.
3. **Drive sustained-write curve, Core stopped (Patrik runs it).** On the trimmed, cooled drive: `fio --name=w
   --filename=/media/RAW/fio.bin --rw=write --bs=1M --direct=1 --iodepth=32 --numjobs=1 --size=400G --write_bw_log=w
   --log_avg_msec=1000`, with `nvme smart-log` temperature, `/sys/block/nvme0n1/stat` and `lspci -vv` LnkSta logged per
   second, 10 minutes. Pass: plateau >= 700 MB/s for all 600 s, no thermal dip, link at 8 GT/s x1. Decides (A)'s storage
   gate; below ~650-700 MB/s, 10-bit (518.5 MB/s) or 3840x2076 (598 MB/s) is the storage-side fit. Delete `fio.bin` after.
4. **The real file pattern, Core stopped.** `variant2.py` (or a 30,000-file `open(O_CREAT)` loop) at 50 files/s x 12,443,140 B
   in one folder for 10 min, timing each create. Pass: 50 files/s held, per-file latency at file 30,000 no worse than at
   file 1,000 by more than 10 ms. Decides whether exFAT's directory scan overruns the 20 ms period before minute 10.
5. **Build `drop-frames` on the Pi, then stage-1-only idle windows.** Fetch `drop-frames` (which now contains the nine knob
   commits) into the Pi's checkout, build, Patrik restarts. Drop-in `LIBCAMERA_LOG_LEVELS=RPI:0,RPiStream:0` and
   `LIBCAMERA_LOG_FILE=/dev/shm/rpi0.log`; 60 s idle per mode; `python3 -I working/tools/be_cycle.py /dev/shm/rpi0.log`.
   Pass: frame count = 60 x fps +- 1, every dt = period +- 0.05 ms, `csi2_errors` 0. Decides that the sensor/link/CFE stage
   is clean, so any later gap is the cycle or the pool.
6. **(A) 60 s cycle windows.** `APERTAR_STORAGE_PREROLL=0`, WebUI closed, ramp off, ladder off, trimmed. `takes.sh 1 60` at
   3840x2160 12-bit uncompressed 50 fps, then 3840x2076, then lossless, then with `imx585_notdn.json` (copy of the tuning
   without the three `tdn` objects, keep `rpi.denoise`; select with `set_tuning_file`), then one arm with
   `APERTAR_DNG_WRITEBACK=0` and one idle `dd conv=fdatasync` repeat. Parse each with `be_cycle.py`. Pass: gap 0, cycle
   median <= 20 ms. Decides whether M3's 22.7 ms reproduces on this build and whether TDN is the term (S2 falls with the
   copy) or software latency is (S2 small, cycle long) or the back end is compute-bound (S2 unchanged: no configuration
   lever left for (A) at 50 fps).
7. **(B) 60 s cycle windows.** Same instrument at 3840x2200 16-bit 25 fps, A0 protocol, linear and Log, default tuning and
   `imx585_clearHDR_notdn.json` (a picked file gets no `_clearHDR` substitution, so the Clear HDR copy must exist by name).
   Pass: cycle median <= 40 ms; p90 <= 36 ms with the default tuning means the copy is optional. Decides the real (B) margin
   and Log's cycle cost on this build.
8. **(B) 10 min soaks on this build.** `takes.sh 1 600` x 3 linear, x 3 Log, then one with the WebUI open
   (`APERTAR_WEB_PREVIEW_RECORDING_FPS` 30 vs 0). Pass: 0 in every counter, `peak_queue` <= 2/12, stop `syncfs` < 200 ms.
   Decides (B) linear YES on the shipping build, Log's status, whether "WebUI closed" stays a condition.
9. **(A) 10 min acceptance, only after 3 and 6 pass.** Three interleaved 10 min takes in the chosen format, `peak_queue`,
   `/sys/block/nvme0n1/stat`, temperature per second, one with the WebUI open. A queue climb from minute ~2 is the post-cache
   drive rate binding.
10. **Residual arms as needed:** the three-client test (E1), per-thread FIFO `APERTAR_RT_CAPTURE_PRIORITY=70` and
    `APERTAR_DNG_DONTNEED=sync` as separate arms (E6), the A2/A1 repeat (E3), the pre-roll A/B (E7).

Decision rule: (B) moves to YES on the shipping build when test 8's three linear takes are clean. (A) moves to YES UNDER
CONDITIONS only when tests 3 and 6 pass and test 9 confirms. A cycle that does not move with TDN off closes the
configuration path for (A) at 50 fps; the fallbacks are 40 fps, back-end decimation or a raw-only take, each code.

## Decisions that wait for a measurement (do not start them before)

- `NoiseReductionMode=Off` in Core's start controls as a knob (about 10 lines, `controlsForSettings`): only if test 6 or 7
  shows TDN is the term and Patrik prefers a knob to tuning copies. Set at start, not toggled mid-stream.
- Automatic no-tdn tuning derivation in Core (like `makeProresIspTuning`, 80-150 lines): after the knob proves itself.
- Rebase of the kb's O_DIRECT patch (T24) onto the copy worker: if test 6's `APERTAR_DNG_WRITEBACK=0` arm or the idle `dd`
  repeat shows writer-side state costing frames on this build.
- `num_cfe_config_queue: 4` in the pipeline YAML: only if a `CFE Config` starvation shows in test 5 or 6.
- Force-push of the clean eight-commit series over Core PR #3 (same tree; `working/dng-chain/patches/clean-series/`): Patrik's
  call; the cloud session's policy blocked it.

## Report back

After each test: the measured values with their log lines, pass / fail / inconclusive, the confounder set, and whether a
verdict in `working/dng-chain-feasibility.md` §0 changes. At the end of the session: the hardware-log entries written, the
pages updated, the branch tips, and the next test.
