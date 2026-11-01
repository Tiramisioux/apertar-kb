# Feasibility brief: can Apertar record drop-free at (A) 4K SDR 12-bit 50 fps and (B) 4K Clear HDR 16-bit 25 fps?

Read `../BRIEF.md` first (repositories, problem statement, labelling rules). This brief adds the question for this phase.

## The question
The operator asks: can we achieve drop-frame-free recording at
- **(A) 4K SDR 12-bit at 50 fps** (3840x2160; the T34 M3 take used 3840x2076), uncompressed DNG, and
- **(B) 4K Clear HDR 16-bit at 25 fps** (3840x2200 unpacked 16-bit), with and without Log,
in takes of at least 10 minutes, to exFAT on the Corsair MP600 Mini NVMe behind the CFexpress hat (PCIe Gen 3 x1) on the Pi 5 / CM5 rig,
on the current build: Apertar-Core `claude/adoring-euler-n8zi0j` at `6ef0ddc` (= `drop-frames` 92d0970 plus nine knob-gated commits,
checked out at /home/user/Apertar-Core). "Drop-free" means zero capture gaps and zero queue drops: every sensor frame lands in a DNG.
If yes: under exactly which configuration, and with how much margin. If no: which stage blocks it, and whether software can fix it.

## How to answer: budgets, not opinions
Every stage of the chain is a budget against the frame period: **20.0 ms for (A)**, **40.0 ms for (B)**.
- Stages INSIDE libcamera's serial per-frame cycle (CFE dequeue, IPA prepare/process, PiSP back end incl. TDN, Core's completion callback with
  preview delivery and any WebUI downsample, request requeue) must finish inside the period on every frame, since the CFE skips a frame when no
  raw buffer is queued at SOF; extra raw buffers hide jitter, not a mean deficit.
- Stages OFF the cycle (copy worker, Log LUT / compressClearHdrFrame, writers, sync thread, kernel writeback, the drive) must keep up on average,
  with the 12-frame queue (or RAM mode) absorbing jitter.
For your dimension, state per mode: budget, estimated usage, margin, and a label for every number: **measured** (cite the log line), **derived**
(arithmetic from measured values; show it), **estimated** (model; name the model and its weakest assumption), or **unverified**. Then say which
single measurement on the Pi would settle it, with the exact tool or command (`working/tools/be_cycle.py`, `hwcount.py`, `libcam_stages.py`,
`dngmeasure.py`, journalctl greps, the stats line fields).

## Repositories and sources (all local unless noted)
- Apertar-Core `6ef0ddc`: /home/user/Apertar-Core (src/camera/CameraController.cpp, src/cdng/CdngEncoder.cpp, src/ApertarCoreApp.cpp, README knob table).
- Apertar-UI: /home/user/tiramisioux/apertar-ui. cinepi-raw: /home/user/tiramisioux/cinepi-raw. cinemate: /home/user/cinemate.
  cinemate handbook: /home/user/tiramisioux/cinemate-handbook (lessons/hardware-log.md and the open-threads).
- Upstream libcamera `c682979`: /home/user/raspberrypi/libcamera (src/ipa/rpi/pisp/pisp.cpp, src/ipa/rpi/controller/rpi/denoise.cpp,
  src/libcamera/pipeline/rpi/pisp/pisp.cpp). **The Apertar libcamera fork is NOT local**; the kb cites fork lines (q2, q7 in
  working/research-30fps/) at 7e9fef0 / 6b0b49f. Say so whenever a conclusion rests on fork behaviour you cannot read.
- Kernel: https://raw.githubusercontent.com/raspberrypi/linux/rpi-6.12.y/<path> (load WebFetch/WebSearch via ToolSearch "select:WebSearch,WebFetch").
- The kb (/home/user/apertar-kb): `lessons/hardware-log.md` (every measurement; read 2026-10-25 to 2026-11-01 fully), `working/drop-frames/README.md`,
  `working/research-30fps/` (q1-backend.md byte model + q1-pisp-be-sim.cpp, q2-pipelining.md, q3-bandwidth.md, q5-copy.md, q6-link.md, q7-cinemate.md,
  critic.md), `working/research-30fps-answer.md`, `working/storage-answer.md`, `working/sensor-capabilities.md`, `working/clearhdr-*.md`,
  `architecture/*.md`, and this study: `../dng-chain-answer.md` (sections 2, 5, 6), `../R6.md` (kernel/drive), `../R7.md` (capture side),
  `../R8.md` (data-rate model), `../R9.md` (libcamera config and the back-end cycle), `../V/VERDICTS.md`.
  Treat every earlier report as evidence to check, not as truth.

## Facts the study already fixed (check them, do not re-derive from scratch)
- T34 M3 (2026-10-28, build 4d5fdd1, 3840x2076 12-bit, two 60 s takes): 2632 and 2616 of ~2980 frames, every loss a steady single-frame
  capture gap (dt 40 ms), queue peak 2-3 of 12, 525 MB/s written, unchanged with 4 or 8 raw buffers; 1080p50 clean. Delivered 44 fps ⇒ cycle ≈ 22.7 ms.
- 2026-11-01 pre-roll on d44b177: 3840x2160 12-bit lossless pinned 60 fps for 2 s, 115 frames, 60.0 fps from sensor timestamps ⇒ zero skips,
  mean cycle ≤ 17 ms in that mode. This is in tension with the TDN-on byte-model estimate of 19-23 ms for the SDR cycle; resolving that tension
  matters for (A).
- Clear HDR 16-bit 30 fps (October, before L1): BE start→done 13.4 ms idle, 34.6 ms recording; cycle 36.2 ms (hardware-log ~185-192) ⇒ outside
  at 30 fps, a few ms inside at 25 fps.
- Clear HDR 16-bit linear at 25 fps (415 MB/s): 10 min clean in A0 and A1 (a40112a, trimmed drive, WebUI closed). A2 lost 1491 one-frame gaps in
  10 min with queue 1-2 of 12 (speed ramp probably ON, unrecorded). Four short takes 2026-10-31 lost 2-10 frames each in the first seconds, WebUI open.
- Back-end bytes per frame (q1 method, R9 §5): SDR COMP1 TDN on 29.0 MB / off 10.6 MB; Clear HDR 16-bit TDN on 57.6 MB / off 20.0 MB.
  TDN is on iff the loaded tuning's `rpi.denoise` has a `tdn` key; Apertar's tuning files live on the Pi only (/home/pi/Tuning-Files/defaults-pisp/)
  and are not in any repo: whether they carry tdn is UNCONFIRMED. cinemate's installed imx585.json has no rpi.denoise at all.
- Link: 891 MHz D-PHY (1782 Mbps/lane, 4 lanes), 70 % used at 4K 50 fps 12-bit. RP1 pixel rate needed 518.4 Mpix/s; the Apertar fork caps at
  646.7 Mpix/s with the 333 MHz RP1 overlay (80 %). Sensor ceiling at 891 MHz is 60 fps at 4K.
- Storage: 4 exFAT writers (MediaProfile {4,12,0}), FAT-chained files on every take, fsync per file every 1 s, direct-write rate of the drive
  measured once at 733 MB/s, 0.9 TB stall when untrimmed (fixed by Core's trim). Writer path now writes 16-bit/8-bit payloads directly (6ef0ddc).
- Residual drops in both modes are capture gaps with the queue nearly empty: upstream of the writers.

## Rules
- Cite `path:line@commit` for code, `file:line` for log lines. Mark every number with its label. Prefer a measured datum over any model.
- Where the mechanism is hardware (drive sustained write and SLC cache, Pi 5 DRAM bandwidth, Gen3 x1 throughput, IMX585 modes), read a primary
  or reputable source on the web and cite the URL; mark it **web**.
- Do not run anything on the Pi (not reachable). Do not change any repository. Write your report FIRST as a skeleton and fill it as you go, so
  work survives if you are cut off.
- Report file: `/home/user/apertar-kb/working/dng-chain/F/F<n>.md` (your number). Structure:
  1. Verdict for (A) and for (B) in your dimension: INSIDE / MARGINAL / OUTSIDE, the margin in ms or MB/s, the confidence label, one sentence why.
  2. Budget table(s) with every row labelled.
  3. Levers in your dimension: each with expected gain (number), cost, risk, how to apply (knob, file, control, code), whether it already exists.
  4. What would settle it on the Pi: the single decisive measurement, tool, minimum duration, what to record alongside (WebUI clients, speed ramp,
     trim state, pre-roll state, tuning file in use, first-take-after-reconfigure).
  5. Open questions and the claims you could not verify.
  6. References.
- Your final text (the return value) is a compact summary under 400 words: verdict A, verdict B, the three most load-bearing numbers with labels,
  the top lever, and the decisive test. The file holds the detail.
