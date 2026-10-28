# Where the last ~2 fps go: 16-bit Clear HDR 4K at 30 fps on a Pi 5 (research answer)

For Patrik and the Mac-side Apertar session. Written 2026-10-26 by a cloud research session (Claude Opus 5.5) from the brief
`working/handoff-30fps-clearhdr16.md`. Research, not a patch: nothing here was run on the Pi, and no repo was pushed.

Evidence: seven reader reports, each with an appended adversarial verification, and a completeness critic, all in
`working/research-30fps/` (`q1-backend.md` … `q7-cinemate.md`, `critic.md`; method and sources in its `README.md`). New read-only tool:
`working/tools/be_cycle.py`. Code trees, all read-only: libcamera `apertar` `6b0b49f` (base will127534 `qbc-pisp-handler` `7e9fef0`),
libpisp `v1.3.0`, raspberrypi/linux `rpi-6.12.y` `5bd564a` (the Pi runs 6.12.75), imx585 driver `apertar` `e5b74d3`, cinemate `d6cc93e`,
cinemate-handbook `c99ff77`, cinepi-raw `63a08d5`, Apertar-Core `f60e301` (the Pi's `d9f00d4` is not available here). Labels:
**CONFIRMED** = the line or page was opened and says so; **PROBABLE** = derived, reasoning given; **UNCONFIRMED** = needs the Pi or a source
not available here. Citations are `repo/path:line@commit`, or a report section that carries them.

## 0. Short answer

1. **The loss is a steady per-frame deficit of libcamera's serial cycle: 1.4-2.9 ms per frame with L1** (CONFIRMED arithmetic: L1
   delivered 27.6-28.8 fps, i.e. a 34.72-36.23 ms cycle against 33.33 ms; `lessons/hardware-log.md:210`). A closed-loop model reproduces the
   three L1 takes (7 / 8 / 20 missing) to within 0.2 frames: missing per 10 s take ≈ 287 × (cycle − 33.33)/33.33 − 4.8 buffers of slack
   (PROBABLE model, `research-30fps/q5-copy.md` §3.2 and its verification). Consequence: **a 10 s take cannot show a deficit below 1.7 %**;
   "0 lost frames" has to be judged from the cycle time or a 60 s take.
2. **The best-supported reading: the PiSP back end's hardware time is stretched by DRAM contention that only recording adds** (PROBABLE,
   not measured; critic H1 + H4). L2 freed libcamera's thread (34 % busy) and gained nothing, which leaves the back end as the main serial
   term. Recording adds ~83 MB/frame of CPU and NVMe traffic (2.49 GB/s) to a frame budget of ~195.5 MB = **5.87 GB/s** (PROBABLE,
   `q3-bandwidth.md` §3). The CameraManager thread's IPC fell 1.87 → 1.30 with the same instructions and the same L3 refills, which is the
   signature of slower memory, not more work (CONFIRMED in the log, `lessons/hardware-log.md:161-162`).
3. **The single largest removable pass is the back end's temporal denoise (TDN), and it removes with a tuning-file copy, no build.**
   libcamera gives the TDN reference the 16-bit unpacked CFE format, so the back end reads and writes a full-frame 16-bit image every frame:
   37.6 MB of its 57.6 MB per frame (CONFIRMED code, `libcamera-apertar/src/libcamera/pipeline/rpi/pisp/pisp.cpp:1902-1905@6b0b49f`;
   simulation `q1-backend.md` §2). TDN only shapes the preview; the DNG is the CFE buffer and does not change. Whether TDN is on in the
   Pi's `imx585_clearHDR.json` is PROBABLE (every IMX585 PiSP tuning in every tree has three `tdn` blocks); one grep settles it.
4. **Nobody has measured the back end's hardware time, but the number is already in the logs you took.** The BE interrupt stamps every
   buffer with `ktime_get_ns()` and libcamera prints it as `timestamp:` on "Stream ISP Input buffer complete"
   (`kernel-rpi/drivers/media/platform/raspberrypi/pisp_be/pisp_be.c:637-644@5bd564a`; `pisp.cpp:2277-2279@6b0b49f`; CONFIRMED).
   `libcam_stages.py` ignores it. `working/tools/be_cycle.py` (new) splits each frame into IPA, back-end hardware, done latency and
   completion. **Run it first**: it decides whether the fix is less back-end work (TDN, then decimation) or less software latency (scheduling,
   then pipelining).
5. **Ruled out or closed:** storage stalls as the rate limit (single regular gaps); the CSI-2 link and the RP1 clock (the Pi already runs
   `rp1-clk-333mhz`, the pixel-rate cap is ≥ 518.4 MPix/s, and preview at 30 fps is clean on the same link); cache maintenance as a hidden cost
   in QBUF/DQBUF; a smaller preview (−4 % of back-end bytes); "no preview buffer in the request" (the back end still runs); `disable_tdn`
   (stalls the back end, §2 Q1). Cinemate's "30.00 fps" for this mode is a computed ceiling, not a counted take; no clean 30 fps recording
   of this mode on any Pi 5 was found (§2 Q7).

## 1. The number every experiment has to move

| Build | Delivered | Cycle | Too long by | Source |
| --- | --- | --- | --- | --- |
| Before L1 (T25) | 25.1-26.4 fps | 37.9-39.8 ms | 4.5-6.5 ms | `lessons/hardware-log.md:144` |
| L1 (stats every 4th row pair) | 27.6-28.8 fps | 34.72-36.23 ms | **1.39-2.90 ms** | `:210` |
| L2 (swap + stats on a worker) | 26.3-28.2 fps | 35.46-38.02 ms | 2.13-4.69 ms | `:225` |
| Target | 30.00 fps, 0 lost | ≤ 33.33 ms, better ≤ 32 ms | — | CONFIRMED arithmetic |

The cycle has four serial stages (CONFIRMED from `pisp.cpp:3112-3171, 2363-2389, 2750-2801, 2272-2284@6b0b49f`,
`pipeline_base.cpp:1525-1542@6b0b49f`): **S1** IPA (`Signalling IPA processStats and prepareIsp` → `Input re-queue to ISP`), **S2** back end
(re-queue → BE done interrupt: libpisp `Prepare`, QBUFs, hardware), **S3** done latency (interrupt → the thread handles "Stream ISP Input buffer
complete"), **S4** completion (→ next `Signalling`, includes Core's `requestCompleted` callback). L1 vs L2 (7/8/20 vs 27/31/14 missing) is not a
significant difference (t = 1.86, df = 4, p ≈ 0.14; `q2-pipelining.md` §5): neither "L2 helped" nor "L2 hurt" is established.

## 2. The brief's research questions, ranked by how much they decide

### Q1. Back-end cost — what the BE does, how many bytes, and how to render the preview from less (`q1-backend.md`)

- **What it does (CONFIRMED code + libpisp v1.3.0 simulation).** One job per frame, the hardware walks 10 tiles itself (408-432 px wide,
  2192 rows; re-read factor 1.1085). Bayer: DPC, GEQ, **TDN**, SDN, BLC, WBG, CDN, LSC, demosaic; RGB: CCM, YCbCr, false colour, sharpen,
  gamma, CSC1, downscale + resample to **one** output (1280x720 YUV420). Stitch, CAC, tonemap, debin and output 0 are off. No BE statistics.
  Simulated enables `bayer_enables 0x47075d`, `rgb_enables 0x0925ba`.
- **Bytes per frame (PROBABLE; CONFIRMED that TDN is 16-bit).** Raw read 18.73 + TDN read 18.73 + TDN write 18.73 + output 1.38 =
  **57.6 MB = 1.73 GB/s** (lower bound 53.8 MB). TDN is 65 % of it. The raw buffer is released only when the BE job finishes, so the whole BE
  run is inside the serial cycle (`pisp.cpp:2272-2284@6b0b49f`).
- **Speed.** Idle start→done 13.4 ms is an upper bound on the hardware time (it includes `Prepare`, QBUFs and the thread's wake-up), so the BE
  needs ≤ 40 % of the frame when idle (CONFIRMED arithmetic). To be the limiter alone while recording it must slow ≥ 2.2-2.5x; the CPU passes
  slowed 1.4-1.6x (PROBABLE; unmeasured). Its AXI QoS is 0 (`pisp_be.c:1716-1720@5bd564a`); what the BCM2712 arbiter does with that is
  UNCONFIRMED. The ISP clock is never set by the driver and is unknown (`pisp_be.c:1677-1684`).
- **Less data for the preview:**

| Option | BE MB/frame | Verdict |
| --- | --- | --- |
| **TDN off by a tuning copy without `tdn`** | 20.0 (−65 %) | **Yes, no build.** SDN/CDN switch to their `*_no_tdn` values (`denoise.cpp:55`), so the preview gets a little noisier; DNGs unchanged |
| TDN off by `disable_tdn: true` (pipeline config) | — | **No: probably stalls the back end** (critic C5, every step CONFIRMED): the erase runs before `streams_` is filled and tests `TdnInput` twice (`pisp.cpp:1659-1665`), so TDN output is still streamed with 0 buffers; the IPA does not know the flag and still enables TDN output; `pispbe_prepare_job` then abandons every job (`pisp_be.c:521-566@5bd564a`) |
| TDN kept but compressed (libcamera patch: TDN nodes get `PISP_COMP1`) | 38.8 (−33 %) | Patch at `pisp.cpp:1902-1903`; `configureBe` already handles a compressed TDN format (`:2572-2582`) |
| Smaller preview (640x360) | 55.3 (−4 %) | Not worth a take |
| Request without a preview buffer | 57.6 | **No effect**: the BE runs into an internal buffer (`pipeline_base.cpp:795-808`, `rpi_stream.cpp:124-145@6b0b49f`) |
| BE only every 2nd frame (decimation) | 28.8 avg (10.0 with TDN off) | Works only with a third piece: no ISP output buffer queued for skipped requests, else it stalls (critic C4: buffers are queued at request time, `pipeline_base.cpp:781-807`; the kernel takes them first-in first-out, `pisp_be.c:557-563`); plus a TDN reset through the IPA and Core attaching the preview buffer every 2nd request |
| Bayer-domain downscale in the BE | — | **Does not exist** (downscale/resample are RGB-branch blocks, `pisp_tiling.cpp:56-110@v1.3.0`) |
| PiSP front end makes a downscaled Bayer for the preview | — | **Not at RAW16**: the FE sees byte-swapped data; Raspberry Pi: "RAW16 cannot be byte-swapped in hardware" (github.com/raspberrypi/libcamera/issues/99) and the IPA disables FE downscale at 14/16-bit (`ipa/rpi/pisp/pisp.cpp:697-717@6b0b49f`) |
| Half-size Bayer made by the CPU in the pass that already reads the frame | 15.0 (5.9 with TDN off) | Feasible but a large libcamera patch; frees the raw buffer before the BE |

### Q3. Memory bandwidth budget — and which pass is cheapest to remove (`q3-bandwidth.md`)

| Pass (recording, 30 fps) | MB/frame | Driven by | Label |
| --- | --- | --- | --- |
| Back end (raw read + TDN r/w + output) | 57.6 | DMA | PROBABLE (Q1) |
| 16-bit endian swap (in place, read + write) | 33.8 | CPU | CONFIRMED code |
| Core's copy (T25: 2160 active rows, read + write) | 33.2 | CPU | CONFIRMED at f60e301 |
| DNG `write()` copy into the page cache | 33.2 | CPU | CONFIRMED at f60e301 (buffered; T24 skipped) |
| CFE write | 16.9 | DMA | CONFIRMED |
| NVMe write-back read | 16.6 | DMA | PROBABLE |
| SW raw stats (row step 4) | 4.2 | CPU | PROBABLE |
| **Total** | **195.5 = 5.87 GB/s** | 3.13 GB/s CPU, 2.73 GB/s DMA | PROBABLE |

- Preview only: 3.38 GB/s; 25 fps recording: 4.89 GB/s, and clean (PROBABLE). One calibration exists: 0.57 M L3 refills per frame before L1
  against 528,000 predicted lines (+8 %) (`lessons/hardware-log.md:161`, `q3-bandwidth.md` verification).
- Not counted: HDMI scanout and UI (0.3-3 GB/s by mode, UNCONFIRMED), and up to 16.6-33.2 MB more if the encoder's 491,520 B scratch copy spills
  out of L2 (Core f60e301 copies each row into it before `write()`).
- **Pi 5 capacity:** 17.07 GB/s theoretical, "up to 17 GB/s" in Raspberry Pi's docs (CONFIRMED). Measured single-core memcpy 6.0-6.1 GB/s
  copied (sbc-reviews issues #58/#21, opened by the q3 verifier). A STREAM figure of 5.4-7.8 GB/s counts read + write and is a search summary
  only (critic C3). So the average is 34-58 % of what the Pi sustains: **not saturated on average**. While the back end runs, the passes that
  overlap it ask for roughly 17-21 GB/s for a few milliseconds (PROBABLE), which fits a BE that stretches only while recording.
- **Interleave:** since the 2024-12-07 bootloader, SDRAM bank interleave and fake NUMA are on by default, later `system_heap.max_order=0` and
  (2025-11-05) `iommu_dma_numa_policy=interleave` (CONFIRMED in Raspberry Pi's release notes, `q3-bandwidth.md` §4). Whether this Pi has them
  is UNCONFIRMED (one `/proc/cmdline` read). Raw buffers come from the system heap through IOMMUs, not CMA (CONFIRMED reading,
  `working/clearhdr-design.md:86`).
- **Cache maintenance** costs CPU time, not DRAM bytes: up to 12 whole-buffer walks per frame with L1, 8 with L2, ≤ 0.5 ms each (PROBABLE), and
  QBUF/DQBUF add none (vb2 skips sync for DMABUF queues, `videobuf2-core.c:415-419@5bd564a`; CONFIRMED).
- **Cheapest pass to remove: TDN** (−37.6 MB, −1.13 GB/s, −19 %, config only, and it sits inside the serial stage). **Next: the page-cache copy
  (T24, O_DIRECT)** (−33.2 MB, −1.0 GB/s, Core change), plus −16.6 MB if the scratch copy goes too (for 16-bit the row length equals the stride,
  so one `write()` from Core's copy is enough; `q3-bandwidth.md` verification). Stats tweaks (≤ 2.1 MB) cannot show.

### Q2. Can the pipeline overlap frames? (`q2-pipelining.md`)

- **A software simplification, not a hardware limit (CONFIRMED).** The gate is `state_ != State::Idle` in `tryRunPipeline`
  (`pisp.cpp:3112-3117@6b0b49f`); `Idle` returns only when the oldest request has all its buffers back after the BE finishes
  (`pipeline_base.cpp:1525-1542`). The kernel driver keeps a job list and a two-slot hardware queue (one running, one programmed and waiting;
  `pisp_be.c:239-244, 597-631, 651-701@5bd564a`). libcamera never queues a second job.
- **Origin:** inherited from the 2020 VC4 handler, where the IPA's statistics came out of the ISP; on PiSP the stats come from the front end
  (or SW stats) and are processed inside `prepareIsp`, so no IPA step needs the BE's output (PROBABLE as the reason; the code is CONFIRMED,
  and the verifier read the 2020 origin, `rpl@740fd1b6`, which gives no other reason). No upstream patch or discussion of pipelining it was
  found (UNCONFIRMED: archives unreachable).
- **What it can recover: at most the non-BE part of the cycle, ≤ 2.9 ms at L1** (CONFIRMED arithmetic). If the BE hardware itself takes
  ≥ 33.3 ms while recording, pipelining cannot reach 30 fps: one engine runs jobs in order. The 34.6 ms "start→done" in the hardware log is a
  log interval, not hardware time (CONFIRMED). A depth-2 patch is 150-300+ lines with several traps the verifier listed (`front()`-based buffer
  matching, metadata routing, the 2-config-buffer assert). **Do it only if the cycle split shows ≥ 3 ms outside the BE.**

### Q5. Avoid Core's copy (`q5-copy.md`)

- **The premise is wrong: cinepi-raw is not zero-copy (CONFIRMED).** Its encode worker copies every row into a pooled buffer
  (`cinepi-raw/cinepi/dng_encoder.cpp:1423-1434, 2178-2250@63a08d5`), releases the camera buffer, then a disk thread does one buffered
  `write()` (`:2351-2360`). It moves the same ~83 MB/frame as Core.
- **O_DIRECT straight from the camera buffer is impossible on this kernel (CONFIRMED code path).** Both dma-heaps map with `VM_IO|VM_PFNMAP`
  (`drivers/dma-buf/heaps/system_heap.c:201-221`, `cma_heap.c:178-191@5bd564a`) and direct I/O's page pinning refuses them with `-EFAULT`
  (`mm/gup.c:1277-1278`). A buffered `write()` from the mapping works.
- **Ranking:** (1) **copy + O_DIRECT (T24)**: −33.2 MB/frame, no extra buffer hold, and the only option already measured on this Pi: in T22,
  `dd` to `/media/RAW` with `oflag=direct` ran at 759 MB/s with 0 frame gaps, buffered at 561 MB/s with 19 gaps (T22 tutorial, cited by the q5
  verifier). (2) zero-copy + O_DIRECT through **udmabuf over a memfd** (`CONFIG_UDMABUF=y`): −66.4 MB/frame, but untested,
  `/dev/udmabuf` is probably root-only, and udmabuf hands the IOMMU 1,032 small pages per buffer, which may slow the back end itself (PROBABLE).
  Zero-copy + buffered saves no more than T24 and holds buffers longer.
- **Buffer budget (PROBABLE):** of 8 raw buffers ~2 sit at the CFE, ~1 in libcamera, Core holds ~0.3 today; an O_DIRECT hold of ~22.6 ms adds
  ~0.45. While libcamera is the bottleneck, a longer hold only brings the first gap a few frames earlier; it does not change the loss rate.

### Q4. Avoid the swap (`q4-swap.md`)

- **No switch removes it (CONFIRMED).** The RP1 CSI-2 block has no byte-swap for RAW16 ("an endian-swap was omitted from the hardware
  pipeline", njhollinghurst, raspberrypi/libcamera#99); the PiSP image-format word has no byte-order bit; the BE driver accepts only
  little-endian 16-bit; the IMX585 drivers write no byte-order register and Sony's register map is not public.
- **The real data type 0x2E makes it worse:** kernel `fda4b68` (2025-07-04) set `csi_dt = 0` for Bayer16 to work around a hardware mismatch
  (CONFIRMED, `rp1_cfe/cfe_fmts.h:196-224@5bd564a`); Cinemate's mono rig saw corrupted 16-bit frames with 0x2E until it patched it (CONFIRMED in
  the handbook).
- **Only the back end needs the swapped full frame** (CONFIRMED code). The DNG could be swapped for free inside Core's copy or its scratch copy,
  or written as a big-endian `MM` DNG (the DNG SDK and LibRaw both read it; Resolve UNCONFIRMED). Fusing the SW stats into the swap saves only
  4.2 MB. The large savings need the BE to read something smaller (decimation or a CPU-made half-size Bayer). An ablation (skip the swap,
  accept a broken preview) tells whether the swap's 1.01 GB/s matters at all before anyone builds that.

### Q7. Cinemate (`q7-cinemate.md`)

- **Its "30.00 fps" for this mode is a computed ceiling** (PROBABLE, strong): `cinepi-raw --list-cameras` prints 1e6 / minimum frame duration
  after configuring the mode; VMAX 4500 × HMAX 550 / 74.25 MHz = 33.33 ms. "21.99 fps stock" is the IPA's pixel-rate cap on a stock RP1
  (380 MPix/s: 4500 × 3840 / 380e6 = 45.47 ms). No frames are counted in either number.
- **No counted 30 fps take of this mode exists** in Cinemate's code, docs, handbook or history (CONFIRMED for the trees read). Counted 4K 16-bit
  takes are at 25 fps (clean after the September preview fixes) or 21 fps. Cinemate's own September drops at 25 fps were fixed by removing one
  extra CPU pass over the raw (`cinepi-raw` `ea53b2c`; CONFIRMED by the verifier), which supports the memory-traffic reading.
- **Its per-frame work is about the same as Apertar's** (PROBABLE): the same rev16 swap on libcamera's thread, no SW stats, one 1256x720 BE
  output with TDN on, a preview-correction pass over the raw, a full 16.9 MB copy before releasing the request, a buffered `write()`, 10 buffers
  on exFAT, SCHED_FIFO 70 on CPUs 1-3. ~199.6 MB/frame against Apertar L1's ~191.5. Patrik's "similar limits" is what the code predicts.
- **Its one structural difference:** it can capture this mode compressed (`--mode 3840:2200:16:P` → PISP_COMP1: no swap, half the capture and BE
  reads, −43.6 % of the bytes). That is lossy (16-code steps) and out of scope for 16-bit uncompressed; it is useful only as a Cinemate-side
  diagnostic.

### Q6. The link (`q6-link.md`)

- **The link does not cause the loss** (near CONFIRMED): 25 fps runs the same HMAX 550 rows at the same 1782 Mbps and is clean; preview at 30 fps
  is clean on the same link; and L1, a software-only change, moved the loss (critic H7).
- **1440 Mbps cannot run 30 fps in either driver's table:** HMAX 660 at 720 MHz gives 74.25e6 / (660 × 4500) = 25.00 fps (CONFIRMED
  arithmetic). That table is built for 12-bit SDR; in Clear HDR a 16-bit row probably fits 1440 at HMAX 550 (PROBABLE), so "30 fps needs 1782"
  is a table choice, not link bandwidth.
- **"CSI-2 counters 0" covers FIFO overflow and four discard types, not CRC/ECC/SoT** (the CSI host interrupt is never enabled; CONFIRMED code).
  A raw status bit (`MIPICFG_INTR` bit 2, `rp1-cfe*/regs` in debugfs) is the only read-only host-error signal (verifier).
- **The RP1 clock limits only the IPA's software cap, which does not bind here** (≥ 518.4 MPix/s, proven by the clean 30 fps preview; critic C7),
  and it does not reach the BCM2712 DRAM side, where the contention is.

## 3. Hypotheses for the missing ~2 fps (critic H1-H13, condensed)

| # | Mechanism | Weight | Discriminating read-only measurement |
| --- | --- | --- | --- |
| H1 | BE hardware time stretched by DRAM contention (S2 ≥ ~31 ms while recording) | **High** | S2 per frame (A2): holds if median ≥ 31 ms; ruled out if ≤ 25 ms while the cycle is ≥ 35 ms |
| H3 | TDN traffic as the lever inside H1 (37.6 of 57.6 MB) | **High if H1 and TDN on** | TDN grep (A1), then B1 |
| H4 | Recording-only CPU traffic (copy + page cache + NVMe, 2.49 GB/s) as the source | **High as the source** | Preview-only dose-response (A5) |
| H2 | Software latency in S1 + S3 + S4 (IPA hand-offs, done wake-up, Core callback incl. the web MJPEG downsample, which runs on libcamera's completion thread, `apertar-core/src/ApertarCoreApp.cpp:8119@f60e301`) | Medium | S1 + S3 + S4 ≥ 5 ms median with L2 (A2) |
| H5 | Page cache, write-back, exFAT, reclaim (CPU and latency) | Medium-Low | `/proc/vmstat` kswapd counters over a take (A3) |
| H8 | DRAM setup: NUMA / BANKLOW interleave not active | Low-Medium | `/proc/cmdline`, node count, bootloader date (A1) |
| H9 | HDMI scanout and web preview load | Low-Medium | HDMI mode, viewer count (A1) |
| H10 | Run-queue delay of the CameraManager / IPA / L2 threads | Low-Medium | `schedstat` per thread (A3) |
| H6, H11, H12, H13 | Cache maintenance; IPA time; IOMMU TLB; low ISP clock | Low | strace sync ioctls; S1; none; `vcgencmd measure_clock isp` |
| H7 | Link, RP1 clock, pixel-rate cap, CFE path | Low (cap ruled out) | `sof` stage in A2 within 1 ms of preview; `csi2_errors` |

## 4. Ranked things to try on the Pi

Order: cheap discriminating measurements first, then configuration, then code. "Takes" = `working/tools/takes.sh 3 10` at 30 fps,
uncompressed, Clear HDR 16-bit, manual ISO/shutter/WB, Pi otherwise idle, L2 build unless stated; **add one 60 s take whenever a 10 s take
shows ≤ 5 missing** (§0.1). Patrik runs everything marked sudo, every restart and every drop-in edit. All predictions are PROBABLE.

### A1. Static facts (5 minutes, read-only)

- **Change:** none.
- **Measure:**
  ```
  grep -c '"tdn"' ~/Tuning-Files/defaults-pisp/imx585_clearHDR.json
  journalctl -u apertar-core -b -o cat | grep -iE 'tuning|clearHDR' | tail -3
  pkg-config --modversion libpisp; vcgencmd measure_clock isp
  tr ' ' '\n' < /proc/cmdline | grep -E 'numa|max_order|iommu_dma'; ls -d /sys/devices/system/node/node*; vcgencmd bootloader_version
  sudo cat /sys/kernel/debug/dri/*/state | grep -E 'mode|crtc\['
  sudo cat /sys/kernel/debug/clk/clk_sys/clk_rate; uname -v
  ss -tnp state established | grep apertar-core     # during a take: any browser preview open?
  ```
- **Prediction:** TDN 3 and the `_clearHDR` file loaded; libpisp 1.3.0; NUMA on (`numa=fake=8`, 8 nodes); clk_sys 333333333; no web viewer.
- **Rules out:** TDN 0 → B1 is moot (the BE already moves ~20 MB) and H1 loses its main lever. No NUMA/interleave → update the bootloader
  first and repeat A2 before anything else. A 2160p HDMI mode or an open web viewer → do B2 before B1.

### A2. Split the cycle per frame, with the timestamps the log already has (zero or one restart)

- **Change:** first none: re-parse the 20:50 window if journald still has it. Then one drop-in for new windows (Patrik):
  `LIBCAMERA_LOG_LEVELS=RPI:0,RPiStream:0`, `LIBCAMERA_LOG_FILE=/dev/shm/rpi0.log` (tmpfs, bypasses journald's rate limit and the disk;
  honoured at `libcamera-apertar/src/libcamera/base/log.cpp:614-622@6b0b49f`) and `LIBCAMERA_RPI_PISP_CONFIG_DUMP=/dev/shm/be-cfg.json` (first
  frame's BE configuration, `pisp.cpp:2782-2797`). Windows: 5 s preview, 10 s recording with L2, 10 s recording with L1 (`QBC_RAW_CPU_WORKER=0`),
  and if the restart allows, 10 s recording at 25 fps (dose evidence for free).
- **Measure:**
  ```
  journalctl -u apertar-core --since "2026-10-26 20:49" --until "2026-10-26 20:56" -o cat > /tmp/w.txt
  python3 -I ~/apertar-kb/working/tools/be_cycle.py /tmp/w.txt          # then the same on /dev/shm/rpi0.log
  python3 -c "import json;j=json.load(open('/dev/shm/be-cfg.json'));c={k:v for b in j['config'] for k,v in b.items()};print(hex(c['global']['bayer_enables']),hex(c['global']['rgb_enables']),len(j['tiles']))"
  ```
  `be_cycle.py` prints median/p10/p90 of queue, S1, S2, S3, S4, cycle and SOF→dequeue, and warns when lines look dropped (< 25 CFE dequeues
  per second) or when the log clock and the kernel timestamps disagree.
- **Prediction (H1):** L2 recording S2 median ≥ 31 ms, S3 ≤ 2 ms, cycle 35-38 ms; preview S2 ≤ 13 ms; L1 S2 about the same as L2 with S3 several
  ms; 25 fps recording S2 between the two. Dump: `0x47075d` (or `0x47074d` on frame 0: TDN bits 0x40 and 0x100 set) and 10 tiles.
- **Rules out:** H1 if L2 recording S2 ≤ 25 ms while the cycle is ≥ 35 ms: then ≥ 10 ms per frame is software (go to A3 → B4 → C6). TDN-on if
  `bayer_enables & 0x140 == 0`. A link/CFE-path cause if recording SOF→dequeue is within 1 ms of preview.

### B1. TDN off with a tuning copy (no build; only if A1 shows TDN on)

- **Change:** make the copy from the Clear HDR file (a file you pick is used as given, with no Clear HDR substitution,
  `apertar-core/src/camera/CameraController.cpp:5586-5592@f60e301`), then select it in Core's tuning setting:
  ```
  python3 -I -c "import json,sys;s,o=sys.argv[1:];d=json.load(open(s));[m.pop('tdn',None) for a in d['algorithms'] if 'rpi.denoise' in a for m in a['rpi.denoise'].values() if isinstance(m,dict)];json.dump(d,open(o,'w'),indent=4)" ~/Tuning-Files/defaults-pisp/imx585_clearHDR.json ~/Tuning-Files/imx585_clearHDR_notdn.json
  grep -c '"tdn"' ~/Tuning-Files/imx585_clearHDR_notdn.json      # 0
  ```
  (Tested here on the IMX585 PiSP tuning: only `rpi.denoise` changes, 3 → 0 `tdn` blocks.) Never use `disable_tdn` (Q1).
- **Measure:** one A2 window (S2), takes, one 60 s take; look at the preview noise at the ISO in use.
- **Prediction:** BE 57.6 → 20.0 MB/frame, total 5.87 → 4.74 GB/s. If the BE is memory-bound: recording S2 −40 % or more, cycle ≤ 33.3 ms,
  0 missing in 3 × 10 s and no gap in 60 s. Preview a little noisier (SDN `deviation_no_tdn` 3.2 instead of 0.6); DNGs byte-identical.
- **Rules out:** recording S2 within 15 % of the TDN-on value and ≥ 7 missing per take: then the BE is compute-bound or not the limiter
  (go to C4/C6). Keep the copy anyway if it helped partly.

### A3. Per-thread CPU, run-queue delay, reclaim and IRQs over one take (read-only, no restart)

- **Measure:** snapshot before and after a 10 s take, then diff:
  ```
  PID=$(pidof apertar-core); for t in /proc/$PID/task/*; do echo "$(basename $t) $(tr ' ' _ < $t/comm) $(cut -d' ' -f14,15,39 $t/stat) $(cat $t/schedstat)"; done
  grep -E '^(pgsteal_kswapd|pgsteal_direct|pgscan_kswapd|allocstall_normal|nr_dirtied|nr_written) ' /proc/vmstat
  grep -E 'pispbe|rp1-cfe|nvme' /proc/interrupts; cut -d' ' -f14,15 /proc/$(pgrep -x kswapd0)/stat
  sudo cat /sys/kernel/debug/rp1-cfe*/csi2_errors      # read once before the take to clear it
  ```
- **Prediction:** CameraManager and IPA threads wait < 1 ms per frame on the run queue (schedstat field 2 / frames); DNG writer threads
  mostly system time; `pgsteal_kswapd` < 100,000 pages per take; CSI-2 counts 0.
- **Rules in:** H10 if the run-queue wait is ≥ 1 ms per frame on the CameraManager or IPA thread (then B4). H5 if `pgsteal_kswapd` ≥ 100,000 per
  take with kswapd ≥ 10 % CPU (then C1 first).

### A4. Gap stationarity from the existing clips (read-only)

- **Measure:** per clip C0089-C0100 (adapt the pattern to Core's DNG names):
  `python3 -I -c "import re,sys,glob;ix=sorted(int(re.findall(r'(\d+)\.dng$',f)[0]) for f in glob.glob(sys.argv[1]+'/*.dng'));g=[b for a,b in zip(ix,ix[1:]) if b-a>1];print(len(ix),g[:1],[y-x for x,y in zip(g,g[1:])])" /media/RAW/<clip>`
- **Prediction:** constant intervals between gaps (±2 frames) from the first gap to the end: a steady deficit.
- **Rules in a growing load** (page cache filling, reclaim, heat): intervals shrinking by ≥ 30 % from the first to the last third of a take.

### B2. Remove display and web load during takes (only if A1 flags it)

- **Change:** close any browser preview; set HDMI to 1280x720@60 or unplug it if the UI tolerates that.
- **Measure:** A2 window (S2 and S4) and takes.
- **Prediction:** from a 2160p60 desktop, missing frames fall by a third or more (up to 2 GB/s of scanout less); little change from 1080p. An open
  MJPEG viewer adds work inside S4.
- **Rules out:** no change in S2/S4 or missing frames after a ≥ 1 GB/s cut.

### A5. Preview-only dose-response: does bandwidth alone reproduce the loss? (low cost; Patrik installs `stress-ng`)

- **Change:** preview only at 30 fps, no recording. First, camera stopped: `stress-ng --memrate 1 --memrate-bytes 256M -t 10s --metrics-brief`
  (the DRAM ceiling, settles critic C3). Then inject a read stressor and a write stressor pinned to cores 0-2 (`taskset -c 0-2`, away from the
  CameraManager thread's core; find it with field 39 of its `stat` in A3) at 1000, 2000 and 3000 MB/s each, reading the achieved rate from
  `--metrics-brief`.
- **Measure:** delivered fps (`working/tools/ipa_rate.py`), intervals > 60 ms, and one A2 window at the highest rate.
- **Prediction (H4):** 30.00 fps up to ~1.5 GB/s injected; below 29.5 fps between 2.0 and 3.0 GB/s, with S2 growing.
- **Rules out H4:** 30.00 fps with no long intervals at ≥ 4 GB/s achieved. Then recording's cost is not bandwidth (look at H2/H5/H9/H10).

### C1. T24: copy + O_DIRECT, IFD-first DNG, no scratch pass (Apertar-Core)

- **Change:** the cloud T24 patch (`working/patches/0001-cdng-direct-I-O-...`, compiled on the host) adapted to `d9f00d4`: aligned buffer, payload at
  a 4096-byte file offset, one O_DIRECT `write()` from Core's copy (16-bit rows equal the stride, so the 491,520 B scratch pass is unnecessary),
  no `DONTNEED`, at most 4 writes in flight.
- **Measure:** takes, one 60 s take, an A2 window, A3's `nr_dirtied` (≈ 0 with O_DIRECT).
- **Prediction:** −33.2 MB/frame (−49.8 without the scratch pass), about two thirds less writer CPU; missing per 10 s take 2-10 from L1's 7-20;
  probably not 0 on its own.
- **Rules out:** missing frames and S2 unchanged within the take spread, with `nr_dirtied` confirmed near 0.

### C2. Swap-skip ablation (libcamera test build; preview, stats and DNG colours wrong by design)

- **Change:** an env switch (e.g. `QBC_SKIP_SWAP16=1`) that skips `do16BitEndianSwap` at `pisp.cpp:2219-2220` and `:817-818@6b0b49f` but keeps
  the flag that forces the unpacked format (`:1744-1746`). L2 on. Test only.
- **Measure:** takes, an A2 window, `working/tools/hwcount.py` on the worker.
- **Prediction if CPU-pass traffic binds:** S2 −3 ms or more, ≤ 5 missing.
- **Rules out:** ≥ 14 missing and S2 unchanged: the swap's 1.01 GB/s is not binding, and fusing it (Q4) is not worth building for that.

### B3 / B4. Writers and scheduling (only when A2/A3 point there)

- **B3, 2 DNG writers instead of 5** (Core setting): ~36 ms of CPU per DNG means one writer cannot keep up; two can. Prediction under the burst
  view: −50 % missing without `dropped_queue_full`. Rules out: unchanged, or queue-full drops appear (then 3).
- **B4, real-time priority for the two serial threads only** (only if A3 shows ≥ 1 ms run-queue wait per frame):
  `sudo chrt -f -p 10 <CameraManager tid>; sudo chrt -f -p 10 <IPA tid>` (undo: `sudo chrt -o -p 0 <tid>`). Not Cinemate's whole-process FIFO:
  at one real-time priority a memcpy worker can block the camera thread. Prediction: S1 + S3 fall by the measured wait. Rules out: no change.

### C3-C6. Larger libcamera changes, each conditional on A2 and B1

| # | Change | Do it only if | Gain | Rules out |
| --- | --- | --- | --- | --- |
| C3 | Compressed TDN (TDN nodes get `PISP_COMP1` at `pisp.cpp:1902-1903`) | B1 helps but the noisier preview is not acceptable | BE 57.6 → 38.8 MB, half of B1 | S2 falls < 15 % against TDN-on |
| C4 | BE decimation while recording: skip the BE on alternate frames, **with no ISP output buffer queued for skipped requests**, a TDN reset through the IPA, Core attaching the preview buffer every 2nd request | S2 stays ≥ 31 ms after B1 | BE load per 66.7 ms halves; monitor at 15 fps while recording (Patrik's call) | < 29.5 fps |
| C5 | Half-size Bayer for the BE made in the pass that already reads the frame (q4 O4) | C4's 15 fps monitor is unacceptable | −59.5 MB/frame; the raw buffer frees before the BE | — |
| C6 | Pipelining depth 2 | S1 + S3 + S4 ≥ 3 ms and S2 ≤ 30 ms in A2 | ≤ 2.9 ms per frame at L1's cycle | < 0.5 fps over L2 with the BE idle gap near 0 |

### Not worth a take (CONFIRMED arithmetic or code)

Stats on every 8th row pair or every 2nd frame (−2.1 MB, 1 %); a smaller preview (−4 % of BE bytes); a request without a preview buffer (the BE
still runs); `disable_tdn` (stalls); 1440 Mbps or a stock RP1 (no effect on the deficit); more raw buffers (only delay the first gap, +33.8 MB of
memory per 2 buffers); 29.97 fps (0.033 ms against a 1.4-2.9 ms deficit); udmabuf zero-copy before T24 has been measured; COMP1 raw capture
(lossy; out of scope).

## 5. Decision path

1. A1 and A2 (one session, at most one restart). A4 needs no restart and can run any time.
2. NUMA/interleave off → bootloader update, then A2 again.
3. **S2 ≥ 31 ms and TDN on → B1.** If still short: C1, then C4 (or C3 if preview noise matters).
4. **S2 ≤ 25 ms → the time is software:** A3 → B4; B2 if a web viewer or a big HDMI mode is on; C6 only if S1 + S3 + S4 stays ≥ 3 ms.
5. A5 says bandwidth alone does not reproduce the loss → deprioritise C1/C3/C4 and look at H5/H10 with A3.
6. Judge every fix by the A2 cycle median (≤ 33.3 ms, better ≤ 32 ms) and a 60 s take, not by a 10 s count.

## 6. What is not established

- The back end's hardware time while recording, idle and with L2 (A2). Every "the BE is the limiter" statement above is PROBABLE until then.
- Whether TDN is on in the Pi's `imx585_clearHDR.json` (A1), the Pi's libpisp version and the ISP clock.
- The Pi's DRAM ceiling and interleave state; what the BCM2712 arbiter does with the BE's AXI QoS 0 (no public documentation; the AXI monitor,
  `dtparam=axiperf=on`, needs a reboot and is the only path to a number).
- Whether Core `d9f00d4` keeps `f60e301`'s writer (scratch pass, `DONTNEED`), its `tuning_file` setting, and whether it ever sets
  `NoiseReductionMode` (checked on `f60e301` only).
- What the CameraManager thread spends ~12.6 ms per frame on under L2 (`usample.py` on that thread with L2 on).
- Public PiSP BE throughput figures (the spec PDF was unreachable from here).

## 7. Verification status

- The seven reports were adversarially verified claim by claim: q1 58 claims (41 confirmed, 14 corrected, 1 refuted), q2 55 (42/6/3), q3 71
  (51/14/1), q4 72 (60/7/2; the two refutations narrow the O_DIRECT and E3 conclusions, not the swap answer), q5 66 (56/5/0), q6 72 (58/7, link conclusion upheld and strengthened), q7 79 (60/15/1). The critic settled 11
  contradictions from the code. Where a reader and its verifier disagree, this answer follows the verifier or the critic.
- Checked again for this answer: `denoise.cpp:55` (`tdnEnable = params.contains("tdn")`) and `:76` (default `ColourHighQuality`); the done
  timestamp at `pisp.cpp:2277-2279` and the re-queue line at `:2754-2755`; `LIBCAMERA_LOG_FILE` at `log.cpp:614-622`; Core's Clear HDR tuning
  selection at `CameraController.cpp:5584-5597@f60e301`; the MJPEG work on the completion thread at `ApertarCoreApp.cpp:8119@f60e301`; the
  `disable_tdn` stall path in `pisp_be.c:473-566@5bd564a` and `pisp.cpp:1299, 1659-1665, 2760-2764@6b0b49f`.
- `be_cycle.py` was tested on a synthetic log with known stage times (S1 1.0, S2 30.0, S3 2.0, S4 3.0 ms; reproduced exactly). The TDN-removal
  one-liner was tested on `libcamera-apertar/src/ipa/rpi/pisp/data/imx585.json@6b0b49f` (3 → 0 `tdn` blocks, nothing else changed).
- Web access from this container was partial: Raspberry Pi's datasheet site, forums and LKML archives failed DNS; GitHub pages and
  raw.githubusercontent.com loaded. Claims that rest on search summaries are marked UNCONFIRMED in the reports.
