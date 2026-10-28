# Critic: 30 fps Clear HDR 16-bit, completeness pass over q1-q7

Critic: completeness pass (Claude Opus 5.5, cloud subagent), 2026-10-26. Inputs: the brief
(`working/handoff-30fps-clearhdr16.md`), `lessons/hardware-log.md:51-233`, and the seven reports with their Verification sections
(`q1-backend.md` … `q7-cinemate.md`). Where a reader and its verifier disagree, the verifier wins unless this file says otherwise.
Code checked here (read-only, at the cited commits): libcamera-apertar `6b0b49f`, libpisp `v1.3.0` (`9ba67e6`), kernel-rpi `5bd564a`,
apertar-core `f60e301` (`git show` only). One web page opened (STREAM source, C3 below).

Labels: **CONFIRMED** = I opened the line or the page and it says so. **PROBABLE** = derived, reasoning given. **UNCONFIRMED** = needs the
Pi or a source not available here. Report citations are `qN-file.md:line` (this folder). Hypothesis weights (High / Medium / Low) are my
judgement of how likely the mechanism is a main part of today's deficit; they are PROBABLE by construction.

## The number every experiment has to move (arithmetic, used throughout)

- Sensor period T = 1000 / 30 = 33.33 ms (CONFIRMED arithmetic; VMAX 4500 x HMAX 550 / 74.25 MHz, `working/clearhdr-design.md:120`).
- Delivered cycle Pp = 1000 / fps. L1: 1000/28.8 = 34.72 ms to 1000/27.6 = 36.23 ms, i.e. **1.39-2.90 ms too long**. L2: 1000/28.2 = 35.46 to
  1000/26.3 = 38.02 ms, i.e. 2.13-4.69 ms too long (CONFIRMED arithmetic on `lessons/hardware-log.md:210,225`).
- Closed-loop model (Q5 §3.2, strengthened by its verifier, `q5-copy.md:388,423`): missing per 10 s take ≈ 287 x (Pp - T)/T - 4.8 buffers
  of slack. It reproduces L1 C0089/C0091: 287 x 0.0417 - 4.8 = 7.2 and 287 x 0.087 - 4.8 = 20.2 against 7 and 20 measured (PROBABLE model,
  CONFIRMED arithmetic). Consequences: **0 missing in a 10 s take needs Pp < 33.33 x (1 + 4.8/287) = 33.89 ms; 0 missing in a take of any
  length needs Pp <= 33.33 ms plus jitter margin.** A target of Pp <= 32 ms means cutting 2.7-4.2 ms from L1 (PROBABLE target).
- Therefore every "missing per 10 s take" prediction below is weak below ~5 missing; the stronger readout is the gap interval in a 60 s
  take (one gap every T/(Pp - T) frames) or Pp itself from the timing windows (PROBABLE, follows from the model).
- 29.97 fps does not help: 1000/29.97 - 1000/30 = 0.033 ms against a 1.4-2.9 ms deficit (CONFIRMED arithmetic).

Cycle stages used below, when frames are backlogged (CONFIRMED from `pisp.cpp:3112-3171, 2363-2389, 2750-2801, 2272-2284@6b0b49f` and
`pipeline_base.cpp:1525-1542@6b0b49f`): **S1** "Signalling IPA processStats and prepareIsp" -> "Input re-queue to ISP" (IPA thread + two
hand-offs); **S2** "Input re-queue" -> BE hardware done (libpisp `Prepare` + QBUFs + hardware); **S3** hardware done -> "Stream ISP Input buffer
complete" log (done latency on the CameraManager thread); **S4** that log -> next "Signalling" (request completion incl. Core's
`requestCompleted` callback). Pp = S1 + S2 + S3 + S4. The hardware done time is already in the log: the BE ISR stamps every buffer of the job
with `ktime_get_ns()` (`kernel-rpi/drivers/media/platform/raspberrypi/pisp_be/pisp_be.c:637-644@5bd564a`) and the "Stream ISP Input buffer
complete" line prints it (`libcamera-apertar/src/libcamera/pipeline/rpi/pisp/pisp.cpp:2277-2279@6b0b49f`) (CONFIRMED, as q1/q2 verifiers found).

## Contradictions

**C1. Back-end bytes per frame: 57.6 MB (q1, q3, q4) vs 18.3 MB (q7 reader) vs 52.1 MB (q7 verifier).**
- q1's 57.6 MB = raw read 18.73 + TDN read 18.73 + TDN write 18.73 + YUV 1.38 (`q1-backend.md:26,125`), reproduced by its verifier
  (`q1-backend.md:285`). q7's reader counted one Bayer read + YUV (`q7-cinemate.md:170`); its verifier added TDN at 16.9 MB each but no tile
  re-read (`q7-cinemate.md:406`).
- Settled from code: the TDN nodes are given the 16-bit unpacked CFE format (`libcamera-apertar/src/libcamera/pipeline/rpi/pisp/pisp.cpp:1902-1905@6b0b49f`),
  and libpisp addresses TDN input and output at the tile **input** offsets (`libpisp/src/libpisp/backend/backend_prepare.cpp:914-919@v1.3.0`),
  so the 1.1085 re-read factor applies to the TDN read (CONFIRMED) and probably to the write (PROBABLE). **Use 57.6 MB (lower bound 53.8)**,
  valid only if TDN is on in the Pi's tuning file (C5) and the Pi's libpisp tiles like v1.3.0 (UNCONFIRMED; `pkg-config --modversion libpisp`).

**C2. Total traffic: 163 MB/4.9 GB/s (q1) vs 195.5 MB/5.87 GB/s (q3) vs ~196 MB (q5) vs 157.7 -> 191.5 MB (q7).**
- q1 omitted the buffered `write()` copy into the page cache (`q1-backend.md:317`); q7 used 2200 rows for Core's passes and no tile
  re-read (`q7-cinemate.md:182,406`). q3's per-pass table (`q3-bandwidth.md:55-76`) uses the 2160-row payload Core copies
  (`apertar-core/src/camera/CameraController.cpp:7224-7236@f60e301`, CONFIRMED by q3's verifier) and q1's simulated BE.
- Settled: **195.5 MB/frame = 5.87 GB/s at 30 fps** (PROBABLE; arithmetic CONFIRMED at `q3-bandwidth.md:320`). It is consistent with the one
  calibration in the log: 0.57 M L3 refills per frame before L1 against 528,000 predicted lines (+8 %) (`lessons/hardware-log.md:161`,
  `q3-bandwidth.md:305`). Error band (PROBABLE): -37.5 MB if TDN is off on the Pi; +16.6 to +33.2 MB if the 491,520 B encoder scratch spills out
  of L2 (`q3-bandwidth.md:313`); plus HDMI scanout and UI render 0.3-3 GB/s, unmeasured (`q3-bandwidth.md:128-134`).

**C3. What a Pi 5 sustains: "10.2-12.2 GB/s of traffic" (q3) vs "STREAM Copy 5.4-7.8 GB/s" (q5).**
- The two are not in the same unit. STREAM counts both the read and the write: `bytes[] = {2 * sizeof(STREAM_TYPE) * STREAM_ARRAY_SIZE, …}` for
  Copy (CONFIRMED, https://raw.githubusercontent.com/jeffhammond/STREAM/master/stream.c, a mirror of McCalpin's stream.c). tinymembench
  `memcpy` reports bytes copied, so q3 doubled it (`q3-bandwidth.md:96`). Hence q5's 7.8 GB/s STREAM figure means ~3.9 GB/s copied, while
  the opened tinymembench results say 6.0-6.1 GB/s copied (`q3-bandwidth.md:325`). They disagree by 1.5x (PROBABLE; q5's figure is a search
  summary, `q5-copy.md:386`, UNCONFIRMED).
- It matters: 5.87 GB/s is 49-58 % of a 10-12 GB/s ceiling but 75 % of 7.8 (CONFIRMED arithmetic). Settles on the Pi with one benchmark,
  camera stopped, after the NUMA check in M2: `tinymembench` or `stress-ng --memrate 1 --memrate-bytes 256M -t 10s --metrics-brief` (package
  install by Patrik; UNCONFIRMED availability).

**C4. Can the back end be skipped on some frames?**
- Agreed (CONFIRMED): a request without a preview buffer still runs the BE into an internal buffer (`pipeline_base.cpp:795-808@6b0b49f`), and
  a raw-only configuration sets `beEnabled_ = false` and completes the raw without the BE (`pisp.cpp:2033, 2377-2384@6b0b49f`).
- Disagreement: q1 X4 (`q1-backend.md:253-257`), q2 E5 (`q2-pipelining.md:261-268`) and q4 O5/E4 (`q4-swap.md:149,273-280`) propose skipping the
  BE on alternate frames. The q1 and q2 verifiers found that this stalls as written (`q1-backend.md:337`, `q2-pipelining.md:353`); the q4
  verifier did not flag it. Settled from code: the request's ISP output buffer, internal or external, is queued to the BE node when the
  request is queued (`pipeline_base.cpp:781-807@6b0b49f`), and the kernel takes the first ready buffer of each node FIFO
  (`pisp_be.c:557-563@5bd564a`). A skipped frame leaves a stale output buffer at the head of the queue, so **every BE-decimation design
  (q1 X4, q2 E5, q4 O5/E4) needs a third piece: no ISP output buffer queued for skipped requests** (PROBABLE stall, same mechanism for all
  three). Also Core f60e301 puts a preview buffer in every request (`q1-backend.md:337`), and the TDN reset is private IPA state
  (`q2-pipelining.md:353`).

**C5. Is `disable_tdn: true` a safe no-build lever?** q1: risky, `start()` fails (`q1-backend.md:195`); q1 verifier: `start()` passes but no BE
job forms (`q1-backend.md:332`); q2: check first (`q2-pipelining.md:290`); q7 verifier: recommends it as the cheapest lossless lever
(`q7-cinemate.md:457-464`).
- Settled from code, **do not use it** (PROBABLE stall, every step CONFIRMED): the config is loaded before `platformRegister` fills
  `streams_` (`pipeline_base.cpp:855` vs `:916@6b0b49f`), so the erase (which also tests `TdnInput` twice, `pisp.cpp:1659-1665`) removes nothing;
  `TdnOutput` gets no buffers (`pisp.cpp:1299-1301`) but is still streamed on (`pipeline_base.cpp:732-738`); `prepareBe` queues no TDN buffers
  (`pisp.cpp:2760-2764`); the IPA does not know about the flag (no `disableTdn` under `src/ipa`, grep) and still sets `TDN | TDN_OUTPUT`
  (`src/ipa/rpi/pisp/pisp.cpp:846@6b0b49f`); the kernel then finds the streaming TDN-output node enabled and empty and abandons the job
  (`pisp_be.c:521-566@5bd564a`). q7's Missed 1 is wrong for this tree.
- The safe route is the tuning file: with no `tdn` key, `tdnEnable` is false (`src/ipa/rpi/controller/rpi/denoise.cpp:55@6b0b49f`), no TDN
  enables are set, and the kernel ignores and returns the queued TDN buffers (`pisp_be.c:533-552@5bd564a`) (CONFIRMED code). Saving 37.6 MB,
  not q7's 33.8 (`q1-backend.md:347`).

**C6. Is TDN on during the Pi takes?** q1 reader: CONFIRMED; q1/q3 verifiers: PROBABLE only, because Core loads `<sensor>_clearHDR.json`
(`q1-backend.md:304`, `q3-bandwidth.md:308`).
- What I can add (CONFIRMED): the Pi's file is `~/Tuning-Files/defaults-pisp/imx585_clearHDR.json`, 134,888 B, = that directory's
  `imx585.json` minus `rpi.hdr` (`working/distribution-image.md:66`, `fork-log.md:67`, `working/clearhdr-design.md:56`); it is in no tree here.
  Every PiSP imx585 tuning in every tree carries three `tdn` blocks (`normal`, `hdr`, `night`; `libcamera-apertar/src/ipa/rpi/pisp/data/imx585.json@6b0b49f`,
  40,339 B; Cinemate's `libcamera/src/ipa/rpi/pisp/data/imx585.json@bfe0b76`, 42,802 B; checked by grep and a JSON parse). Core never sets
  `NoiseReductionMode` (`q1-backend.md:331`) and the default denoise mode is `ColourHighQuality` (`denoise.cpp:76@6b0b49f`).
- So TDN on: **PROBABLE**. Settles with `grep -c '"tdn"' ~/Tuning-Files/defaults-pisp/imx585_clearHDR.json` (expect 3) plus
  `journalctl -u apertar-core -b -o cat | grep -iE 'tuning|clearHDR'` to confirm that is the file loaded, or the BE config dump in M1
  (`bayer_enables & 0x140` non-zero: TDN 0x40 + TDN_OUTPUT 0x100, `libpisp/src/libpisp/backend/pisp_be_config.h:41,43@v1.3.0`).

**C7. RP1 clock / pixel-rate cap.** q6 calls the overlay and the 646.667 cap "nearly CONFIRMED" (`q6-link.md:264`); the KB itself labels the
log line Probable/Unconfirmed (`working/clearhdr-design.md:88`, `working/handoff-clearhdr-buffering.md:29`), and `working/compare-raw/c1-probe-compare.md:127`
says no log line was captured; q7's verifier downgraded it (`q7-cinemate.md:366`).
- Settled: **the cap is >= 518.4 MPix/s on the Pi (CONFIRMED by measurement + code)**. The cap is unconditional for PiSP
  (`src/ipa/rpi/controller/controller.cpp:215`, `src/ipa/rpi/common/ipa_base.cpp:620-639@7e9fef0`); at 380 MPix/s the minimum frame is
  4500 x 3840 / 380e6 = 45.47 ms, so preview could not deliver 30.00 fps, yet it does (`lessons/hardware-log.md:161`). The live `clk_sys`
  (333 / 200 / 166.7 MHz, `q6-link.md:309-317`) is UNCONFIRMED and matters only for the CFE drain, where even 166.7 MHz carries 2H rows
  (`q6-link.md:604-607`, PROBABLE). Pi: `sudo cat /sys/kernel/debug/clk/clk_sys/clk_rate`.

**C8. Back-end hardware time while recording: "about 34-36 ms" (q2 reader) vs "19-22 ms if it slows like the CPU" (q1) vs "upper bound,
cannot rank" (q2 verifier).** `q2-pipelining.md:27-29`, `q1-backend.md:178`, `q2-pipelining.md:343`.
- Not settleable from code. 34-36 ms assumes S1+S3+S4 = 1.6 ms under L2 (a difference of two medians from a pre-L1 window, not a per-frame
  measurement). Settles with M0/M1 below: per-frame S2 = hardware-done timestamp minus the "Input re-queue" log time (CONFIRMED method).

**C9. Why L2 did not help: "the swap now overlaps the BE and slows it" (hardware log, `lessons/hardware-log.md:227-229`) vs "it overlapped under
L1 too; L1 vs L2 is noise" (`q3-bandwidth.md:340`, `q2-pipelining.md:144-146`, p ≈ 0.14).**
- Partly settled from code (PROBABLE): under L1 the swap of a later frame ran on the CameraManager thread while BE job N was in hardware (the
  78 % finding, `lessons/hardware-log.md:192`), so they overlapped in both builds. But under L1 the swap also delayed `prepareIspComplete`, so
  BE job N+1 could not start until the swap ended (`pisp.cpp:2363-2389`, single thread); under L2 job N+1 starts at once. So L2 raises the
  overlap of the two largest memory streams; the size of the effect is unknown. With p ≈ 0.14 neither reading may steer the ranking. Settles
  with M1 run once with L1 and once with L2 (S2 per frame).

**C10. Internal CFE raw buffers: "2 internal buffers on top of Core's 8" (q1, `q1-backend.md:94`) vs "the CFE pool is exactly Core's 8"
(q5, `q5-copy.md:152-154`).** Settled from code (CONFIRMED): the 2 are allocated (`pisp.cpp:1270-1277@6b0b49f`) but `queueAllBuffers` skips
External streams (`pipeline_base.cpp:961-962@6b0b49f`) and internal raw buffers are queued only for requests without a raw buffer
(`rpi_stream.cpp:124-161@6b0b49f`). They add 33.8 MB of memory, no slack.

**C11. Smaller levers judged differently.**
- "One DNG writer needs 6-12 ms" (q3 X4) vs "~36 ms of CPU per DNG across 5 threads" (q3 §5, q5 §4.1): settled by the measurement,
  0.95 core / 26.45 fps = 36 ms (CONFIRMED arithmetic on `lessons/hardware-log.md:164`; thread identity PROBABLE). One writer cannot keep up;
  use 2 (`q3-bandwidth.md:353`).
- "BE AXI QoS 0 = lowest priority" (q1/q2/q3 readers) vs "QoS 0 = not participating" (`q3-bandwidth.md:360`): unsettleable here; only the
  comment exists (`pisp_be.c:1716-1720@5bd564a`). The BCM2712 AXI monitor (`dtparam=axiperf=on`, `q3-bandwidth.md:205-209`) is the only path to a
  number (UNCONFIRMED bus mapping).
- "E3 (swap-skip + TDN-off) is an upper bound for O4/O5" (q4) — refuted by its verifier (`q4-swap.md:402`); keep O4/O5 alive after a failed E3.
- q5's linear loss guess vs its closed-loop model: use the model (`q5-copy.md:388`).

## Hypotheses for the missing ~2 fps

Common ground (CONFIRMED in the log and code): the loss is a steady per-frame deficit of the serial libcamera stage; 25 fps recording and 30 fps
preview are clean; recording adds ~83 MB/frame of CPU and NVMe traffic (`q3-bandwidth.md:84`); the CameraManager thread's IPC drops 1.87 -> 1.30
at constant instructions and L3 refills (`lessons/hardware-log.md:161-162`). The hypotheses below are candidate contents of S1-S4 (H1-H2, H10-H13)
and candidate sources of the contention (H3-H9). They can add up.

**H1. BE hardware time stretched by DRAM contention (S2 grows from <= 13.4 ms idle to >= ~31 ms).** Weight: **High**.
- For: L2 freed the CameraManager thread (34 % busy) without raising delivery (`lessons/hardware-log.md:225-229`), which leaves S2 as the main
  remaining term (PROBABLE); the BE is the largest pass (57.6 MB, C1) and reads in strided 864 B bursts (`q1-backend.md:151`); preview-only runs
  the same BE bytes clean, so the stretch must come from recording traffic (PROBABLE).
- Against: it needs S2 ≈ 33.9-36.4 ms under L2 (`q2-pipelining.md:343`), i.e. 2.5-2.7x the idle upper bound, while the CPU passes slowed only
  1.22-1.62x (`q1-backend.md:329`). Never measured.
- Discriminator (read-only): **M1 S2 per frame** with L2 while recording. H1 holds if median S2 >= 31 ms; ruled out if <= 25 ms while Pp >= 35 ms.

**H2. Software latency in the serial loop (S1 + S3 + S4).** Weight: **Medium**.
- For: L1 removed ~5 ms of thread work per frame and gained 1.5-2.5 fps (`lessons/hardware-log.md:209-212`); before L1, 78 % of BE completions were
  handled only after a swap/stats run (`:192`); under L2 the thread still spends 0.34 x ~37 = 12.6 ms per frame on unnamed work
  (`q2-pipelining.md:147-149`); Core's whole `requestCompleted` callback runs inside S4 (`pipeline_handler.cpp:584-603@6b0b49f`, `q2-pipelining.md:51`),
  including the web MJPEG downsample from the preview mapping when a browser viewer is open (`apertar-core/src/ApertarCoreApp.cpp:6961-7002,
  8111-8190@f60e301`, comment "This runs on libcamera's completion thread", CONFIRMED); the IPA and L2 worker threads run at normal priority;
  only the callback thread is set to nice -5 (`CameraController.cpp:6926-6935@f60e301`, CONFIRMED).
- Against: L2 removed the largest blocker (~10 ms swap) and gained nothing; pre-L1 S1+S4 ≈ 1.6 ms by medians.
- Discriminator: **M1 S3 and S1+S4 per frame**. H2 holds if S1+S3+S4 >= 5 ms median under L2.

**H3. TDN traffic (37.6 MB/frame, 65 % of the BE's bytes), as the main lever inside H1.** Weight: **High if H1 holds and TDN is on**
(TDN on: PROBABLE, C6).
- For: largest configuration-only cut (-1.13 GB/s, -19 % of 5.87 GB/s; `q3-bandwidth.md:344`); it sits inside S2 (CONFIRMED, raw buffer returns
  only on BE input dequeue, `pisp.cpp:2272-2284@6b0b49f`).
- Against: if the BE is compute-bound, S2 barely moves; it does not touch S1/S3/S4.
- Discriminator: M2 tuning grep (presence, read-only), then B1 (TDN-off tuning copy): S2 falls with bytes if memory-bound (13.4 x 20.0/57.6 =
  4.6 ms idle by bytes alone, `q1-backend.md:347`).

**H4. Recording-only CPU traffic as the source of the contention (Core copy 33.2 + page-cache copy 33.2 + NVMe 16.6 MB; 2.49 GB/s).**
Weight: **High as the source, not as a separate stage.**
- For: preview-only is clean; T22 `dd` to tmpfs cost frames and `dd` O_DIRECT did not (`lessons/hardware-log.md:75-79`); IPC 1.87 -> 1.30.
- Against: T22 ran a different build (copy on the completion thread, lossless); average traffic is 34-75 % of the ceiling depending on C3.
- Discriminator: M6, the preview-only dose-response (stress-ng on cores 0-2, separate read and write instances, achieved rate,
  `q3-bandwidth.md:351`): if ~2.5 GB/s injected stretches preview Pp past 33.3 ms (or S2 in an M1 window), bandwidth alone is enough.

**H5. Page-cache, writeback and exFAT kernel work, and reclaim (CPU and latency, not only bytes).** Weight: **Medium-Low**.
- For: ~36 ms of CPU per DNG (C11), most of it probably kernel (buffer heads at 512 B sectors: 32,400 per frame, `q5-copy.md:204-206`);
  `POSIX_FADV_DONTNEED` drops only clean pages, so pages under writeback go to kswapd (`q5-copy.md:201-203`, PROBABLE); T22 buffered `dd` cost frames.
- Against: gaps are single and regular, `peak_queue` 1/12, no write failures (`lessons/hardware-log.md:165-170,210`).
- Discriminator: **M3** `/proc/vmstat` (`pgsteal_kswapd`, `pgscan_kswapd`, `allocstall_*`) and kswapd and writer-thread stime over one take.
  Holds if `pgsteal_kswapd` rises >= 100,000 pages per take and kswapd shows >= 10 % CPU (`q5-copy.md:280-284`).

**H6. Cache maintenance (dma-buf sync walks over 16.9 MB, 2 attachments).** Weight: **Low**.
- For: 8 walks per frame with L2, 12 with L1 (`q3-bandwidth.md:68,318`); the swap's 6.1 -> 9.9 ms includes them (`q3-bandwidth.md:338`).
- Against: bounded at <= 0.41-0.54 ms per walk by the idle thread budget (`q3-bandwidth.md:319`); under L2 none are on the serial path (worker,
  Core worker). **New, CONFIRMED from code:** there is no hidden maintenance in QBUF/DQBUF: vb2 skips cache sync for DMABUF queues
  (`kernel-rpi/drivers/media/common/videobuf2/videobuf2-core.c:415-419@5bd564a`), keeps the mapping when the same dma-buf returns to the same index
  (`:1421-1423`), DQBUF does not unmap (`:2118-2128`), and libcamera's buffer cache returns the same index for the same buffer
  (`libcamera-apertar/src/libcamera/v4l2_videodevice.cpp:236-247@6b0b49f`).
- Discriminator: `strace -f -T -y -e trace=ioctl` on the SYNC ioctls split by fd (`q3-bandwidth.md:354`). Holds only if > 2 ms per ioctl.

**H7. RP1 clock, pixel-rate cap, CSI-2 link, CFE write path.** Weight: **Low** (cap: ruled out).
- For: the D-PHY runs above its calibrated band (`q6-link.md:134-142`); no counter covers CRC/ECC (`q6-link.md:157-161`).
- Against: cap ruled out (C7, CONFIRMED); 25 fps runs the same row bursts at the same link and is clean (`q6-link.md:126`); preview at 30 fps is
  clean; a software-only change (L1) moved the loss (`q6-link.md:600-603`); PCIe x4 to the RP1 runs at 25-50 % (`q6-link.md:329-332`).
- Discriminator: **M1 SOF -> CFE dequeue minimum** (recording within 0.5 ms of preview; `q6-link.md:436-445`, regex fix `q6-link.md:589-591`), plus
  `csi2_errors` read before (clears) and after a 30 fps take and bit 2 of `MIPICFG_INTR` in `rp1-cfe*/regs` (`q6-link.md:609-612`).

**H8. DRAM configuration: NUMA/BANKLOW interleave, SDRAM refresh state; CMA placement.** Weight: **Low-Medium** (CMA: ruled out for raw buffers).
- For: the bootloader docs say performance is "adversely affected" without NUMA (`q3-bandwidth.md:101`); a reported 5.4 -> 7.8 GB/s STREAM jump
  with `SDRAM_BANKLOW` (`q5-copy.md:386`, UNCONFIRMED); "same L3 refills, more cycles" fits higher DRAM latency (PROBABLE).
- Against: nothing measured; raw buffers come from the system heap, not CMA (`/dev/dma_heap/vidbuf_cached -> system`, `working/clearhdr-design.md:86`,
  CONFIRMED reading); TDN/preview buffers are IOMMU-remapped pages, not CMA (`q3-bandwidth.md:42`, PROBABLE).
- Discriminator: **M2** `/proc/cmdline` (`numa=fake=`, `numa_policy=`, `system_heap.max_order=`, `iommu_dma_numa_policy=`), node count, bootloader date.

**H9. Display and web preview load (HDMI scanout + QML render; MJPEG downsample).** Weight: **Low-Medium**, unknown.
- For: 2160p60 scanout alone is 1.99 GB/s (`q3-bandwidth.md:131`); the MJPEG downsample sits inside S4 (H2).
- Against: the same load exists in preview-only, which is clean (PROBABLE); the HDMI mode and browser state are simply unrecorded.
- Discriminator: **M2** current HDMI mode and MJPEG viewer count.

**H10. Scheduling latency / CPU contention for the CameraManager, IPA and L2-worker threads.** Weight: **Low-Medium**.
- For: 4 cores at 59/44/48/38 % while recording, five Core threads at 18-20 % (`lessons/hardware-log.md:164`); two thread hand-offs per frame in
  S1 and one wake-up in S3; no SCHED_FIFO (Cinemate uses it, `q7-cinemate.md:156`).
- Against: average CPU headroom exists (1.89 of 4 cores busy).
- Discriminator: **M3** `/proc/<pid>/task/<tid>/schedstat` field 2 (ns waiting on a run queue) per frame for those three threads; available with
  `CONFIG_TASK_DELAY_ACCT=y` (`kernel-rpi/arch/arm64/configs/bcm2712_defconfig:14@5bd564a`; that it selects `SCHED_INFO` is PROBABLE). Holds if
  >= 1 ms per frame on the CameraManager or IPA thread.

**H11. IPA time on the serial path (S1).** Weight: **Low**. Before L1, S1+S4 ≈ 36.2 - 34.6 = 1.6 ms by medians (`q2-pipelining.md:125-126`).
`libcam_stages.py` already prints "IPA signalled -> back end start" (`working/tools/libcam_stages.py:58`), but the log entry did not record it.
Discriminator: M1 S1 median. Lever if >= 3 ms: `controller_min_frame_duration_us: 66666` (`q7-cinemate.md:420`).

**H12. IOMMU translation cost for the BE and CFE.** Weight: **Low**, UNCONFIRMED. The BE sits behind `iommu2` and the TDN buffers are 16 KB-page
remaps (`q3-bandwidth.md:40-42`); q5's verifier raised the TLB question for udmabuf (`q5-copy.md:416-422`). No read-only discriminator found;
the AXI monitor is the closest (config + reboot).

**H13. BE clock lower than assumed.** Weight: **Low**. The driver never sets the ISP clock rate (`pisp_be.c:1677-1684@5bd564a`, CONFIRMED); the rate is
unknown. Discriminator: `vcgencmd measure_clock isp` idle and while recording (or `sudo grep -i isp /sys/kernel/debug/clk/clk_summary`).

**Ruled out or closed (do not spend takes on them):** storage stalls as the rate limit (single regular gaps, `peak_queue` 1/12; CONFIRMED
record); the pixel-rate cap (C7); per-frame libpisp retiling (tiles are recomputed only when a setter flags `retile_`,
`libpisp/src/libpisp/backend/backend_prepare.cpp:692-698@v1.3.0`, and the ScalerCrop path only calls `SetCrop` on change,
`pipeline_base.cpp:1404-1406@6b0b49f`; CONFIRMED); a software downscale in `beOutputDequeue` (only when the output is beyond the BE's max
downscale, `pisp.cpp:716-728,1963-1966@6b0b49f`; 3840 -> 1280 is 3x, PROBABLE no); more raw buffers as a fix (they only delay the first gap,
`q5-copy.md:175-176`, PROBABLE); a smaller preview (-4 % BE bytes, `q1-backend.md:197`).

## Gaps

None of the reports answered these, and each changes the ranking.

1. **The 20:50 RPI:0 windows may be truncated by journald.** At RPI:0 + RPiStream:0 the handler logs on the order of 15-25 lines per frame (PROBABLE,
   count of `LOG(RPI, Debug)` sites on the per-frame path), i.e. ~450-750 lines/s, above journald's default burst limit of 10,000 per 30 s
   (UNCONFIRMED on the Pi). Check: `journalctl -u systemd-journald --since "2026-10-26 20:45" --until "2026-10-26 21:00" -o cat | grep -i suppress`
   and the "frames traced" count that `libcam_stages.py` prints (expect ~150 per 5 s). For new windows, use `LIBCAMERA_LOG_FILE=/dev/shm/…`
   (honoured at `libcamera-apertar/src/libcamera/base/log.cpp:614-622@6b0b49f`, CONFIRMED), which bypasses journald.
2. **The per-frame decomposition S1-S4 was never computed**, although the log already carries all four boundaries (see the header). Every report
   defers to it. Where: M0/M1.
3. **What the CameraManager thread does for ~12.6 ms per frame under L2**, and its user/kernel split. Where: `usample.py` on that tid with L2
   on, and fields 14/15 of `/proc/<pid>/task/<tid>/stat`.
4. **Run-queue delay of the CameraManager, IPA and L2-worker threads** (H10). No report proposed `schedstat`. Where: M3.
5. **Whether a browser MJPEG viewer was open during C0077-C0100.** Flagged UNKNOWN in `working/compare-raw/b3-core-completion.md:77,226`, never checked;
   it puts work inside S4. Where: Patrik's memory, or `ss -tnp state established | grep apertar-core` during the next takes.
6. **HDMI mode, NUMA/BANKLOW state, bootloader date, ISP clock, live clk_sys, installed libpisp version.** All one-line reads (M2); none recorded.
7. **The Pi's practical DRAM ceiling** (C3). One benchmark with the camera stopped.
7a. **Whether TDN is on** (C6). One grep.
8. **Gap stationarity inside a take.** A constant gap interval means a steady deficit; shrinking intervals late in a take mean growing load
   (page cache filling, reclaim, heat). Can be read from the existing clips without the Pi (M4).
9. **The 25 fps recording cycle.** No timing window exists at 25 fps recording; it would show S2 at 4.89 GB/s against 5.87 GB/s (dose evidence for
   H1 at no extra cost if run in the same restart as M1).
10. **IRQ placement** of `pispbe`, `rp1-cfe` and `nvme` relative to the CameraManager thread's CPU (`/proc/interrupts`, field 39 of the thread's
    `stat`).
11. **Core `d9f00d4`'s writer** (scratch pass, DONTNEED, T25 hold cap) is not available here; T24's and the scratch-removal savings assume f60e301's
    writer (`q5-copy.md:312-313`).
12. Kept open, low impact: the TDN write width (18.73 vs 16.83 MB, `q1-backend.md:271-272`); whether the 2H-row model holds (`q6-link.md:478`).

## Draft ranking

Score = (expected gain toward 30.00 fps with 0 drops) x (probability) / (cost and risk for Patrik). Measurements first, then configuration, then code.
Standard take: `working/tools/takes.sh 3 10` at 30 fps, uncompressed, Clear HDR 16-bit, manual ISO/shutter/WB, Pi otherwise idle; add one 60 s take
whenever the 10 s count is <= 5 (header). All predictions are PROBABLE; all "rules out" thresholds are mine unless cited.

### A. Measurements that discriminate cheaply (no code change)

**A1 (M0). Re-parse the 20:50 windows, if still on the Pi.** Cost: zero, read-only, no restart. Sources: q2 M1, q2 verifier Missed 3, q6 E3.
- Change: none.
- Measure: `journalctl -u apertar-core --since "2026-10-26 20:49" --until "2026-10-26 20:56" -o cat > /tmp/w.txt; wc -l /tmp/w.txt`; the journald
  check of Gap 1; `python3 -I ~/apertar-kb/working/tools/libcam_stages.py /tmp/w.txt` (tool path on the Pi UNCONFIRMED) for S1 ("IPA signalled ->
  back end start"); q2's M1 parser (`q2-pipelining.md:178-193`) for S2 ("BE hw upper") and S3 ("done latency"); S4 = next "Signalling" log time
  minus "Stream ISP Input buffer complete" log time; SOF -> CFE dequeue = log time minus `timestamp:` of "Stream CFE Image buffer dequeue"
  (`pisp.cpp:2199-2201@6b0b49f`).
- Prediction (pre-L1 recording): S3 median >= 5 ms (the 78 % finding), S2 22-30 ms, S1 + S4 <= 2 ms; preview S2 <= 13 ms.
- Rules out H2 for the pre-L1 build if S3 median < 2 ms; rules out H1 if recording S2 <= preview S2 + 3 ms. If journald suppressed lines (Gap 1),
  treat the medians as indicative only.

**A2 (M1). One timing window per build, to a file.** Cost: one Core restart via the existing drop-in (Patrik), read-only otherwise. Sources: brief §6,
q1 X1/X3, q2 E1, q6 E3. **Highest information per effort.**
- Change: drop-in `libcamera-debug.conf` with `LIBCAMERA_LOG_LEVELS=RPI:0,RPiStream:0`, `LIBCAMERA_LOG_FILE=/dev/shm/rpi0.log` (tmpfs, avoids journald and
  disk I/O) and `LIBCAMERA_RPI_PISP_CONFIG_DUMP=/dev/shm/be-cfg.json` (`pisp.cpp:2782-2797@6b0b49f`, dumps the first frame). Windows: 5 s preview and
  10 s recording at 30 fps with L2; the same with L1 (`QBC_RAW_CPU_WORKER=0`); optionally 10 s recording at 25 fps (Gap 9). Logging itself adds
  thread work; it did so in the 20:50 windows too.
- Measure: the A1 parsers on `/dev/shm/rpi0.log`; q1 X3's one-liner on the dump (`q1-backend.md:248`).
- Prediction under H1: L2 recording S2 median >= 31 ms, S3 <= 2 ms, start interval 35-38 ms; L1 S2 about the same, S3 several ms. Dump:
  `bayer_enables` 0x47074d (TDN on), 10 tiles of 408/432 px.
- Rules out H1: L2 recording S2 <= 25 ms with Pp >= 35 ms (then H2/H10 own >= 10 ms per frame; go to A4 and B4/C5). Rules out H7's CFE-path variant:
  recording SOF -> CFE dequeue minimum within 1 ms of preview. Rules out C6 (TDN on): `bayer_enables & 0x140 == 0`.
- Fallback without a restart: q2's ftrace M2 (`q2-pipelining.md:197-223`, start IRQ may precede the qbuf event, `q2-pipelining.md:351`).

**A3 (M2). Static facts, one session, ~5 min (sudo where marked).** Cost: zero. Sources: q1 X0, q3 X0/§7, q4 E0, q5 E1/E7, q6 E1. Each result re-weights
a hypothesis.
- `grep -c '"tdn"' ~/Tuning-Files/defaults-pisp/imx585_clearHDR.json; journalctl -u apertar-core -b -o cat | grep -iE 'tuning|clearHDR'` (C6; expect 3).
- `pkg-config --modversion libpisp; vcgencmd measure_clock isp` (C1, H13).
- `cat /proc/cmdline | tr ' ' '\n' | grep -E 'numa|max_order|iommu_dma'; ls -d /sys/devices/system/node/node*; vcgencmd bootloader_version` (H8;
  expect `numa=fake=8` and 8 nodes; if absent, Patrik updates the bootloader before any further take).
- `sudo cat /sys/kernel/debug/dri/*/state | grep -E 'mode|crtc\['` (H9); `ss -tnp state established | grep apertar-core` during a take (Gap 5).
- `sudo cat /sys/kernel/debug/clk/clk_sys/clk_rate; sudo dmesg | grep "couldn't set"` (C7); `uname -v` (q4 E0 becomes unnecessary if the build date
  is after 2025-07-04, `q4-swap.md:404`).
- Prediction: TDN 3, libpisp 1.3.0, NUMA on, clk_sys 333333333, no MJPEG viewer. Any other value moves that hypothesis up (or, for TDN 0, B1 out).

**A4 (M3). Per-thread CPU, run-queue delay, reclaim and IRQs over one take.** Cost: zero, read-only, no restart. Sources: q3 §7, q5 E3/E4, new.
- Measure, before and after a 10 s take (diff the two snapshots):
  `PID=$(pidof apertar-core); for t in /proc/$PID/task/*; do echo "$(basename $t) $(tr ' ' _ < $t/comm) $(cut -d' ' -f14,15,39 $t/stat) $(cat $t/schedstat)"; done`;
  `grep -E '^(pgsteal_kswapd|pgsteal_direct|pgscan_kswapd|allocstall_normal|nr_dirtied|nr_written) ' /proc/vmstat`;
  `grep -E 'pispbe|rp1-cfe|nvme' /proc/interrupts`; `cut -d' ' -f14,15 /proc/$(pgrep -x kswapd0)/stat`; `sudo cat /sys/kernel/debug/rp1-cfe*/csi2_errors`
  (read once before to clear, `q6-link.md:154`).
- Prediction: CameraManager and IPA run delay < 1 ms per frame; writer threads stime > utime; `pgsteal_kswapd` < 100,000; csi2 counts 0.
- Rules H10 in: run delay >= 1 ms per frame on the CameraManager or IPA thread. Rules H5 in: `pgsteal_kswapd` >= 100,000 per take with kswapd >= 10 % CPU.

**A5 (M4). Gap stationarity from existing clips (no Pi).** Cost: zero. Source: new.
- Measure, per clip C0089-C0100 (file-name pattern UNCONFIRMED; adapt the regex):
  `python3 -I -c "import re,sys,glob;ix=sorted(int(re.findall(r'(\d+)\.dng$',f)[0]) for f in glob.glob(sys.argv[1]+'/*.dng'));g=[b for a,b in zip(ix,ix[1:]) if b-a>1];print(len(ix),g[:1],[y-x for x,y in zip(g,g[1:])])" <clip dir>`.
- Prediction (steady deficit): intervals between gaps constant within ±2 frames from the first gap to the end. Rules in a growing load (H5, H8
  thermal refresh): intervals shrink by >= 30 % from the first to the last third of the take.

**A6 (M6). Preview-only dose-response and DRAM ceiling.** Cost: low (Patrik installs `stress-ng`; no Core change). Sources: q3 X1 corrected
(`q3-bandwidth.md:351`), C3.
- Change: preview only at 30 fps; inject reads and writes on cores 0-2 (not the CameraManager thread's core) at R = 0, 1000, 2000, 3000 MB/s,
  one read-method and one write-method instance; first one run with the camera stopped to get the ceiling.
- Measure: delivered fps (`working/tools/ipa_rate.py`) and the stressor's achieved rate; ideally one A2 window at the highest R.
- Prediction under H4: preview stays at 30.00 fps up to ~1.5 GB/s injected and falls below 29.5 fps between 2.0 and 3.0 GB/s.
- Rules H4 out: 30.00 fps with 0 intervals > 60 ms at >= 4 GB/s achieved. Then recording's cost is not bandwidth (H2/H5/H9/H10).

**A7. Cinemate's own 30 fps count (q7 X1).** Cost: medium (boot a Cinemate card), information only; predicted 27-29 fps (`q7-cinemate.md:264-265`).
Do it only if Patrik wants "similar limits" as a number.

### B. Configuration changes

**B1. TDN off via a tuning copy (only if A3 shows TDN on).** Score: **highest of all levers** (gain 1-3+ fps if H1/H3; probability Medium-High;
cost: one file, a restart, preview slightly noisier, DNGs unchanged). Sources: q1 X2, q3 X2. **Never use `disable_tdn` (C5).**
- Change: `python3 -I -c "import json,sys;s,o=sys.argv[1:];d=json.load(open(s));[m.pop('tdn',None) for a in d['algorithms'] if 'rpi.denoise' in a for m in a['rpi.denoise'].values() if isinstance(m,dict)];json.dump(d,open(o,'w'),indent=4)" ~/Tuning-Files/defaults-pisp/imx585_clearHDR.json ~/Tuning-Files/imx585_clearHDR_notdn.json`,
  then select that file in Core's tuning setting (or `LIBCAMERA_RPI_TUNING_FILE` in the drop-in, adopted only while Core's saved setting is empty,
  `CameraController.cpp:7941-7944@f60e301`). Start from the `_clearHDR` file: a user-picked file gets no Clear HDR substitution (`CameraController.cpp:5586-5592@f60e301`).
- Measure: `grep -c '"tdn"'` on the copy (0); one A2 window; takes plus one 60 s take.
- Prediction: BE 57.6 -> 20.0 MB/frame, total 5.87 -> 4.74 GB/s; if memory-bound, recording S2 drops by >= 40 % and Pp <= 33.3 ms: 0 missing in 3 x 10 s
  and no gap in 60 s.
- Rules out: recording S2 within 15 % of the TDN-on value and >= 7 missing per take. Then the BE is compute-bound or not the limit; go to C4/C5.

**B2. Remove display and web load during takes (only if A3 flags it).** Gain: up to 1-2.7 GB/s from 2160p60 (`q3-bandwidth.md:357`), plus S4 time if
an MJPEG viewer was open. Cost: zero to low. Source: q3 X3, Gap 5.
- Change: close any browser preview; set HDMI to 1280x720@60 or unplug it if the UI tolerates it.
- Measure/predict: A2 S2 and S4 fall; missing drops by >= a third from 2160p60, little from 1080p60. Rules out: no change after a >= 1 GB/s cut.

**B3. Fewer concurrent DNG writers (5 -> 2).** Gain: small unless bursts matter. Cost: a Core setting. Source: q3 X4 corrected (`q3-bandwidth.md:353`).
- Prediction under the burst view: missing -50 % with no `dropped_queue_full`. Rules out: unchanged missing, or queue-full drops (then 3).

**B4. Real-time priority for the two serial threads only (only if A4 shows run delay >= 1 ms per frame).** Cost: low, reversible, no restart; Patrik:
`sudo chrt -f -p 10 <CameraManager tid>; sudo chrt -f -p 10 <IPA tid>` (undo with `sudo chrt -o -p 0 <tid>`). New; narrower than q7 X3, whose whole-process
FIFO can starve the camera thread behind a FIFO memcpy worker (`q7-cinemate.md:419`).
- Prediction: S1 and S3 fall by the measured run delay. Rules out: no change in S1 + S3.

**B5. IPA on alternate frames (`controller_min_frame_duration_us: 66666`, q7 X4), only if A2 S1 >= 3 ms.** Low gain otherwise.

**B6 (optional, needs a reboot). AXI monitor** (`dtparam=axiperf=on`, `q3-bandwidth.md:205-209`): the only way to see the BE's bus waits (C11 QoS).
Do it only if A2 says H1 and B1 does not fix it.

Not worth a take (CONFIRMED arithmetic or code): stats row step 8 or every 2nd frame (-2.1 MB, 1 %, `q3-bandwidth.md:347`); a smaller preview (-4 %);
no preview buffer in the request (BE still runs); 1440 Mbps or stock RP1 (q6 E4/E5; no effect on the deficit, `q6-link.md:604-607`); more raw buffers
(moves the first gap only; +33.8 MB per 2 buffers); `disable_tdn` (stalls, C5).

### C. Code changes (libcamera branch `apertar`, Apertar-Core branch `clearhdr-fixes`)

**C1. Swap-skip ablation build (libcamera, test only; q4 E1).** Cost: trivial patch and a Pi build; preview, stats and DNGs garbage by design.
- Change: `QBC_SKIP_SWAP16=1` skips `do16BitEndianSwap` at `pisp.cpp:2219-2220` and `:817-818@6b0b49f`; keep the flag at `:1744-1746`. Run with L2.
- Measure: takes + one A2 window + `hwcount.py` on the worker.
- Prediction if CPU-pass traffic matters: S2 -3 ms or more, missing <= 5. Rules out: missing >= 14 and S2 unchanged: the swap's 1.01 GB/s is not binding,
  and O3/O4/O5 are not worth building for the swap's sake.

**C2. T24: copy + O_DIRECT, IFD-first DNG, and no scratch pass (Core).** Gain: -33.2 MB/frame (-1.0 GB/s) and ~2/3 of the writer CPU; -16.6 MB more if the
scratch pass goes too, since 16-bit rows equal the stride (`q3-bandwidth.md:389-391`). Probability Medium (backed by T22: `dd` O_DIRECT 0 gaps,
buffered 19 gaps, `q5-copy.md:382`). Cost: medium Core work. Sources: q3 X7, q5 E5.
- Change: as `q5-copy.md:290-293` (aligned buffer, payload at offset 4096, one O_DIRECT write, no DONTNEED, in-flight writes capped at 4).
- Measure: takes + one 60 s take; A2 window; A4 counters (`nr_dirtied` ≈ 0).
- Prediction (closed-loop model with excess scaling with Core traffic, `q5-copy.md:388`): 2-10 missing per 10 s take from L1's 7-20; alone, probably not 0
  (PROBABLE). Rules out: missing and S2 unchanged within the take spread with `nr_dirtied` confirmed near 0.

**C3. Compressed TDN (libcamera), only if B1 helps but the noisier preview is not acceptable.** Change: give the TDN nodes a PISP_COMP1 format
instead of `cfeFormat` at `pisp.cpp:1902-1903@6b0b49f`; `configureBe` already enables TDN compress/decompress for a compressed format (`pisp.cpp:2572-2582`),
and the BE driver lists COMP1 formats (`pisp_be_formats.h:502-532@5bd564a`; acceptance on the TDN nodes PROBABLE). Gain: BE 57.6 -> 38.8 MB
(`q1-backend.md:196`), half of B1's. Rules out: S2 falls < 15 % against TDN-on.

**C4. BE decimation while recording (libcamera + Core), only if A2/B1 leave S2 >= 31 ms.** Change: q2 E5 plus the C4 fix (no ISP output buffer queued for
skipped requests), a TDN reset through the IPA interface, and Core attaching the preview buffer to every 2nd request (`q1-backend.md:337`,
`q2-pipelining.md:353`). Gain: BE load per 66.7 ms halves; monitor at 15 fps while recording (Patrik's call). Cost: medium-large, stall risk.
Prediction: 30.00 fps, 0 gaps in 60 s. Rules out: < 29.5 fps.

**C5. Pipelining depth 2 (libcamera), only if A2 shows S1 + S3 + S4 >= 3 ms and S2 <= 30 ms.** Change: q2 E4 plus its verifier's items (`front()`-based
buffer matching, metadata routing, the 2-config-buffer ASSERT; `q2-pipelining.md:390-392`). Gain: at most Pp - max(S2, 33.33), i.e. <= 2.9 ms at L1's
cycle (`q2-pipelining.md:371-372`). Cost: large, 300+ lines, highest regression risk. Rules out: < 0.5 fps over L2 with the BE idle gap near 0.

**Later or rejected.** O1 fused stats (q4 E2: -4.2 MB, restores row step 1 at no DRAM cost; small gain, do it with C1's build if convenient);
O4 half-resolution BE input (q4, -59.5 MB, large patch; only if C4's 15 fps monitor is unacceptable); udmabuf zero-copy O_DIRECT (q5 B2,
-66.4 MB, large, root-only `/dev/udmabuf`, IOMMU TLB risk, `q5-copy.md:416-429`); COMP1 raw capture (lossy, 16-code steps, out of scope; q7 X2 as a
Cinemate-side diagnostic only, `q7-cinemate.md:442-444`).

### Decision path after A1-A4 (PROBABLE)

- S2 >= 31 ms and TDN on -> B1 -> if still short, C2 then C4 (or C3 if preview quality matters).
- S2 <= 25 ms -> the time is in S1/S3/S4: A4 run delay -> B4; Core callback (B2 MJPEG) -> C5 only if the software gap stays >= 3 ms.
- NUMA off (A3) -> bootloader update first, then repeat A2 before anything else.
- A6 says bandwidth alone does not reproduce the loss -> deprioritise C2/C3/C4 and look at H5/H10 with A4.
