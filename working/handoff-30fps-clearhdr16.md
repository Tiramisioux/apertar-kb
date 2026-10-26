# Handoff: why 16-bit Clear HDR 4K tops out near 28 fps on a Pi 5, and what to try next

For: Fable (deep-research session). Written 2026-10-26 by the Mac-side Apertar session (Claude Opus 5.5) after a day of
measurements on the Pi. Your job is **research and ranked suggestions**, not a patch: find where the remaining ~2 fps go, and
propose experiments that Patrik can run on the Pi, each with a prediction and the number that would falsify it.

## 1. The goal and the setup

- **Goal:** record IMX585 Clear HDR, 3840x2160, 16-bit, uncompressed CinemaDNG at **30 fps with 0 lost frames**. 25 fps is
  already clean. Patrik reports similar results with Cinemate (a different recorder on the same sensor and Pi), so treat this
  as a platform limit until shown otherwise.
- **Hardware:** Raspberry Pi 5, 4 GB, IMX585 on the `apertar` driver branch (link 891 MHz = 1782 Mbps/lane, above the RP1
  D-PHY's 1500 Mbps calibrated range, see `working/clearhdr-compare-notes.md`), `/media/RAW` = exFAT on NVMe, kernel
  6.12.75+rpt-rpi-2712, boot args `rp1_cfe.track_csi2_errors=1 nvme_core.default_ps_max_latency_us=0 pcie_aspm=off`.
- **Frame:** sensor readout 3840x2200 16-bit unpacked = 16.9 MB per frame; 30 fps = ~507 MB/s into memory from the CFE, before
  any CPU or back-end pass.

## 2. Code (all public or in this KB)

| What | Where | State |
| --- | --- | --- |
| libcamera the Pi runs (base) | `will127534/libcamera` `qbc-pisp-handler` @ `7e9fef0` (= installed `v0.7.1+qbcfork.20260522-7-7e9fef0b`) | unchanged |
| Our libcamera | `Tiramisioux/libcamera` branch **`apertar`**: `889567a` (L1), `6b0b49f` (L2) | on GitHub |
| Core changes | `Tiramisioux/Apertar-Core` branch **`clearhdr-fixes`** (from `main` `f60e301`): `db17860` T23, `43a54f3`/`fc7eb16`/`351a3ee` T25, `d9f00d4` audio | on GitHub |
| Files that matter | libcamera `src/libcamera/pipeline/rpi/pisp/pisp.cpp` (`cfeBufferDequeue`, `tryRunPipeline`, `processRawStats`, `do16BitEndianSwap`), `raw_stats.cpp`, `common/pipeline_base.cpp` (`handleState`, `checkRequestCompleted`) | |
| Measurement tools | this KB, `working/tools/`: `takes.sh`, `core.py`, `usample.py` (user-space IP sampler), `hwcount.py` (A76 PMU per thread), `libcam_stages.py` (per-stage times from libcamera's RPI debug log), `ipa_rate.py` | read-only |
| Full measurement record | `lessons/hardware-log.md`, entries dated 2026-10-26 (last seven) | |

Core changes in one line each: T23 = one libcamera request per raw buffer, 8 raw buffers in Clear HDR; T25 = the DNG copy
(dma-buf sync + 16.9 MB memcpy) moved off libcamera's completion thread to a recorder worker that requeues the request after the
copy (at most buffers-2 held); `d9f00d4` = audio end follows frames actually queued.

## 3. What was measured (30 fps unless noted, uncompressed, Pi otherwise idle)

| Stage of the work | Missing per 10 s take (~287 frames) | Delivered fps | libcamera CameraManager thread busy |
| --- | --- | --- | --- |
| Core main + T23 | 35-52 | 24.7-26.3 | 71 % |
| + T25 (Core copy off libcamera's thread) | 30-46 | 25.1-26.4 | 61 % (54 % in a later run) |
| + L1: SW raw stats on every 4th row pair | **7, 8, 20** | **27.6-28.8** | 43 % |
| + L2: swap + stats on a worker thread | 27, 31, 14 | 26.3-28.2 | 34 % |

- 25 fps uncompressed: 0 missing in every configuration. 25 fps lossless JPEG: encoder-bound (~18 fps capacity), not this issue.
- **Preview only (not recording) at 30 fps: 30.00 fps delivered, 0 gaps**, thread 41-44 % busy.
- Every loss is on the capture side: `dropped_gap_estimate` = missing, Core's write queue `peak_queue` 1/12, no write failures,
  CSI-2 receiver error counters 0 (T22), no libcamera drop log lines.
- **Gap pattern:** always exactly one frame, every 5-9 frames, first gap only after 27-47 frames. No bursts.
- **PMU on the CameraManager thread** (before L1): same ~47 M instructions and 0.57 M L3 refills per frame idle and recording,
  but cycles per frame 25 M -> 36 M (IPC 1.87 -> 1.30, backend stall 12 % -> 21 %). Memory contention is real.
- **libcamera debug timing** (`LIBCAMERA_LOG_LEVELS=RPI:0`, before L1/L2), medians idle -> recording:
  CFE dequeue -> IPA signalled 13 -> **217 ms** (6-7 frames queued); back end start -> done (as the thread logs it) 13.4 ->
  **34.6 ms**; back end start interval 33.3 -> **36.2 ms**; 78 % of back-end completions logged right after a swap/stats run
  (24 % idle); swap 6.1 -> 9.9 ms, raw stats 5.8 -> 7.1 ms.
- T22 (earlier, lossless): `dd` buffered to the NVMe cost frames, `dd` with O_DIRECT did not; `dd` to tmpfs (pure memory
  traffic) cost frames. Dirty-page tuning changed nothing.

## 4. What is established, and what is not

- **Confirmed:** the RPi PiSP pipeline handler runs one frame at a time through IPA + back end (`tryRunPipeline` only when
  `Idle`), so frames queue in libcamera and the CFE runs out of buffers and skips one whenever it falls a full frame behind.
- **Confirmed:** reducing work on the CameraManager thread helped (L1), but taking almost all of it off (L2) did not help further.
  The thread is not the limit any more.
- **Probable (not measured with L2):** the back end itself takes ~33 ms or more per 4K frame while recording, because it is
  memory-bound and competes with the CFE write (~507 MB/s), the swap (read + write 34 MB per frame), the stats read, Core's
  copy (34 MB per frame) and the NVMe DMA (~507 MB/s). L2 overlaps the swap with the back end in time, which may make the back
  end slower, not faster.
- **Unknown:** the Pi 5's usable DRAM bandwidth under this mix; how long the PiSP back end takes for this configuration in
  isolation; whether the back end even needs to read the full 4K frame for a 1280x720 preview; whether the 1782 Mbps link plays
  any part (CSI-2 counters say no errors, but the RP1 runs outside its calibrated D-PHY range).

## 5. Research questions (please rank and answer)

1. **Back end cost.** What does the PiSP back end do per frame in this mode (read 16-bit Bayer 3840x2200, which blocks, TDN /
   stitch / HDR enabled?, two outputs?) and how many bytes does it read and write? Is there a configuration that renders the
   1280x720 preview from less data (back-end crop/downscale early, a smaller BE input, skip TDN, a lower-res raw for the preview
   only)? Sources: `pisp.cpp` (`prepareBe`, `platformConfigure`), libpisp `backend/`, the Raspberry Pi tuning JSON for imx585.
2. **Can the pipeline overlap frames?** Upstream libcamera RPi pipeline: is the one-frame-at-a-time state machine a hard
   constraint of the PiSP back end, or a simplification? Has anyone pipelined BE jobs?
3. **Memory bandwidth budget.** Sum the bytes per frame (CFE write, swap r/w, stats r, BE r/w, Core copy r/w, NVMe DMA read) and
   compare with what a Pi 5 sustains with these access patterns. Which single pass is the cheapest to remove?
4. **Avoid the swap.** The swap exists because the RP1 CFE cannot byte-swap 16-bit data (`cfe_fmts.h`, `csi_dt = 0` for 16-bit).
   Can the BE or the IMX585 deliver the other byte order (sensor register? a CSI-2 data type the CFE handles with swapping?), or
   can the swap be fused into another pass that reads the frame anyway (stats, Core's copy)?
5. **Avoid Core's copy.** cinepi-raw writes DNGs straight from the camera buffer (no copy) and holds the request until the encode
   worker is done (see `working/clearhdr-compare-notes.md`). With 8 buffers, is that viable here, and what does it save?
6. **The link.** Does 1782 Mbps/lane vs 1440 change anything at 30 fps (frame timing, CFE behaviour), or is it irrelevant once the
   CSI-2 counters read 0?
7. **Cinemate.** Patrik sees similar limits there. What do Cinemate's handbook and hardware log (`Tiramisioux/cinemate`,
   `cinemate-handbook`) record about 4K 16-bit at 30 fps (`docs/sensors.md` says 30.00 fps with the RP1 overclock: under which
   conditions, recording to what, with which preview)?

## 6. Experiments you may propose (the Pi can do these)

Format each as: what to change, the exact read-only measurement, the prediction, and what result would rule the idea out.
Patrik runs anything with `sudo`, restarts and `/boot/firmware`; builds happen on the Pi. Ideas already on the table, for you to
sharpen or reject:

- One `LIBCAMERA_LOG_LEVELS=RPI:0` window with L2 on: does back end start -> done stay >= 33 ms with the thread idle?
- Same with the preview stream made as small as libcamera allows, or with no ISP output buffer in the request while recording.
- Record with Core's copy replaced by a no-op (frames dropped on purpose) to see the delivery ceiling without the copy's traffic.
- Record to `/dev/null` or tmpfs vs NVMe to split NVMe DMA from CPU traffic.
- L1 with row step 8, and stats every second frame.

## 7. Rules for this work

- Read the KB first: `llm/README.md`, then this file, `lessons/hardware-log.md` (2026-10-26 entries),
  `working/clearhdr-compare-notes.md`, `working/cinemate-lessons.md`.
- Label every claim confirmed / probable / unconfirmed, with `path:line@commit`.
- Only the Mac pushes, and only when Patrik asks. Core work is on `Tiramisioux/Apertar-Core` branch `clearhdr-fixes` (not `main`);
  libcamera work on `Tiramisioux/libcamera` branch `apertar` only (never the `cinemate*` branches).
- The Pi is a measurement machine: keep it quiet while measuring, no language servers or agents on it.

## 8. Current Pi state (end of 2026-10-26)

Core `d9f00d4` on branch `clearhdr-fixes`, 25 fps, uncompressed, Clear HDR 16-bit. libcamera from `~/opt/libcamera-apertar`
(`6b0b49f`) via the drop-in `/etc/systemd/system/apertar-core.service.d/libcamera-test.conf` (`LD_LIBRARY_PATH`,
`QBC_RAW_STATS_ROW_STEP=4`, `QBC_RAW_CPU_WORKER` to be set back to 0 by Patrik). System libcamera in `/usr/local` untouched.
Test clips C0001-C0100 on `/media/RAW`, none deleted.
