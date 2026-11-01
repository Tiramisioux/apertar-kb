# Hardware log

Append-only. One entry per finding Patrik confirmed on the Pi. Newest at the bottom.

Entry format:

```
## YYYY-MM-DD: <one-line finding>
- Tested: <rig, image/commit, what was run>
- Worked: <what held>
- Did not work: <what failed, or "n/a">
- Why: <the mechanism, with path:line or command output>
- Confirmed by: Patrik, <how: "now it works", a reading, a take>
- Tutorial: <Obsidian note name, if one was written>
```

---

## 2026-10-23: DPI overlays on the stock image remove `/dev/i2c-1` on an HDMI rig

- Tested: Pi 5, Apertar-Beta 1.6.0, IMX585 on cam0, RPI5-CFE-Hat, Adafruit NeoRotary 4 on the hat's
  Qwiic hub, HDMI display (no DPI panel).
- Worked: commenting out `config.txt` lines 76-78 (`vc4-kms-DPI-4inch`, `waveshare-4dpi`,
  `waveshare-touch-4dpi`) and rebooting. `/dev/i2c-1` appeared; hat `0x34` and encoder `0x49`
  found on bus 1; `[cfexpress_hat] bus=1`, `[neorotary4] enabled=true bus=1 address=0x49`.
- Did not work: `dtparam=i2c_arm=on` alone. The DPI overlay claims GPIO 0-27 whether or not a
  panel is attached (`pinctrl get 2,3` showed `DPI_VSYNC`/`DPI_HSYNC`).
- Why: see `sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md` §3.2-3.4. Side effect: with the DPI
  connector gone, HDMI became the main touch-UI screen at the 720x720 `[display]` size
  (`run_pi_direct.sh:138-166` at upstream-1.6.0; the source note says 135-160); fixed via `[display]` keys (§4.5).
- Confirmed by: Patrik at the rig, "now it works".
- Tutorial: `20261025152945 CINEMATE APERTAR start-tutorials` (the format reference).
- Still open: how the hat reaches `i2c-10` (JP3/JP4?), where the IMU is wired, which overlay gives
  `/dev/i2c-4`.

## 2026-10-25: tally LED on GPIO 21 needs the `[recording_indicator]` section, not `d21=recindicatorled`, with Cinemate wiring

- Tested: Pi 5, Apertar-Beta 1.6.0 (Core fork `main` ed400ba), LED wired as on Cinemate: `GPIO21 -> resistor -> LED -> GND`.
- Worked: `[recording_indicator] enabled=true target=gpio line=21 active_high=true`; `[trigger_output] enabled=false`;
  `[pcf8574] enabled=false`; `d21=recindicatorled` removed; Core restarted. Journal: `recording indicator LED enabled:
  target=gpio active_high=true gpio=/dev/gpiochip0 line=21 open_drain=false`; `gpioinfo`: `apertar-rec-led` on line 21.
- Did not work: (1) the image's template `[recording_indicator] enabled=true target=pcf8574 bus=10 address=0x20 pcf_pin=7`
  won over `d21`, and with no chip at `0x20` Core logged `Could not write PCF8574 recording indicator output: Remote I/O error`.
  (2) Setting `[gpio_buttons] active_low=false` does not change the LED; it flips the d10/d6 button inputs (put back to `true`).
- Why: an enabled section returns before the shorthand counts (`RecordingIndicatorOutput.cpp:382-387`); the shorthand
  has no polarity key and inherits `active_high` from a section above it, default `false` (`:320-326`). `[trigger_output]`
  starts first (`ApertarCoreApp.cpp:6881` vs `:6893`) and would hold line 21. Config is read only at Core start.
- Confirmed by: Patrik at the rig, "now it works".
- Tutorial: `20261025193414 CINEMATE APERTAR tally-gpio21-tutorial` (T17, now in `APERTAR/_archive/`).

## 2026-10-26: `/media/RAW` is exFAT on NVMe; kept for macOS/Windows compatibility

- Tested: Pi 5, Apertar-Core fork `main` f60e301, `findmnt -no SOURCE,FSTYPE,OPTIONS /media/RAW` (T22 step 3.1).
- Worked: n/a (a reading). Result: `/dev/nvme0n1p2 exfat rw,noatime,uid=1000,gid=1000,fmask=0002,dmask=0002,allow_utime=0020,iocharset=utf8,errors=remount-ro`.
  Patrik predicted exFAT before running it.
- Did not work: n/a
- Why: Core's `format_media` defaults to exFAT (`ApertarCoreApp.cpp:10647`). ext4 would likely drop fewer frames
  (Cinemate `a61a589`: exFAT/NTFS have spikier write+metadata latency), but exFAT mounts on macOS and Windows without drivers.
  Both exFAT and ext4 support direct I/O (`fs/exfat/inode.c:492-506`), so T24 stays open. Consequence for T23-T26: work with exFAT
  (buffer count, direct I/O, media profile), do not switch filesystem.
- Confirmed by: Patrik, own `findmnt` reading and "yes, lets keep exfat".
- Tutorial: `T22 clearhdr-drops-measure` (step 3.1).

## 2026-10-26: Clear HDR 16-bit 4K at 25 fps loses 16-40 % of frames; CSI-2 receiver never errors; dirty-page tuning does not help

- Tested: Pi 5 (4 GB), IMX585, Apertar-Core fork main f60e301, kernel 6.12.75+rpt-rpi-2712, /media/RAW = exFAT on
  /dev/nvme0n1p2, rp1_cfe.track_csi2_errors=1 on the kernel command line. 3840x2160, Clear HDR, 16-bit, 25 fps,
  CDNG lossless_jpeg, workers=5, queue=24. T22.
- Worked: counters and measurement setup. dd direct I/O to the NVMe: 733 MB/s with frame delivery clean (24.99/s, 0 gaps).
- Did not work: any 10 s take. 5 baseline takes lost 39-96 of ~243 frames (mean 62.8), 5 takes with dirty_background_bytes=256 MiB,
  dirty_bytes=1 GiB, writeback 150 cs lost 43-92 (mean 66.2): no difference. fps into libcamera 22.4/19.3/22.3/22.1/19.3 baseline.
- Results:

  | run | fps into libcamera | intervals >60 ms | CSI-2 counters |
  | --- | --- | --- | --- |
  | idle, no load | 24.92 | 0 | - |
  | dd buffered (fdatasync) | 24.63 | 3 | all 0 |
  | dd direct | 24.99 | 0 | all 0 |
  | dd tmpfs, 12 x 1 GB | 22.77 | 11 | all 0 |
  | take C0001 | 24.36 | 3 | not read |
  | takes C0002-6 (baseline) | 19.3-22.4 | 19-52 | not read |
  | takes C0007-11 (dirty knobs) | 18.2-22.7 | 19-68 | not read |

  Of the lost frames: capture-side gaps 25-70 per take in C0002-11 (64-69 %), queue-full drops 14-35; in C0001, 6 and 36.
  files + queue-full + capture gaps = last file index + 1, within 1 frame, in all 11 takes.
- Why (what is established): the receiver never overflowed or saw a link error, so theory A (CSI-2 FIFO starvation) is not
  supported. Memory traffic alone (dd to tmpfs, no NVMe) costs frames; direct I/O (no page-cache copy) does not. Throttling
  (get_throttled 0x0, 2.4 GHz, ~63 C), direct reclaim, compaction and write failures were all 0.
  Not established: why takes alternate between ~22 fps and ~19 fps; whether the "no buffer" scheduling line exists on this kernel
  (CONFIG_DYNAMIC_DEBUG is not set); block-queue tuning (not tested); 30 fps (not tested). 89 MB of swap was in use.
- Confirmed by: Patrik, own measurements on the Pi.
- Tutorial: T22 clearhdr-drops-measure.
- **Correction (2026-10-26, see next entry):** every take above was `cdng_compression=lossless_jpeg`, whose encoder tops out near 18 fps
  (Core's own `estimated_capacity_fps` 17.3-18.5). The 25 fps loss is therefore mostly the encoder, not the NVMe or exFAT.
  The "memory traffic costs frames" and "dirty knobs do nothing" results stand; the 16-40 % figure applies to lossless only.

## 2026-10-26: Clear HDR 16-bit 4K, uncompressed vs lossless JPEG, 25 and 30 fps, after T23 (8 buffers, one request per buffer)

- Tested: Pi 5 (4 GB), IMX585, Apertar-Core fork branch `clearhdr-fixes` db17860 (main f60e301 + T23), /media/RAW exFAT on NVMe,
  3840x2160 Clear HDR 16-bit, 10 s takes via `working/tools/takes.sh 5 10`, 5 takes per cell (C0050-C0069), 20:06-20:16.
  Pi otherwise idle: Claude and its VS Code extension removed, no cpptools running, VS Code server up but under 1 % CPU,
  `get_throttled` 0x0. `workers=5`, lossless queue 24, uncompressed queue 12.
- Results (frames missing per take, 5 takes each):

  | fps | compression | missing | dropped_queue_full | dropped_gap_estimate | peak_queue | ipa fps |
  | --- | --- | --- | --- | --- | --- | --- |
  | 25 | none | 0, 0, 0, 0, 0 | 0 | 0 | 1/12 | 24.5-25.0 |
  | 25 | lossless_jpeg | 43, 38, 37, 45, 43 | 23-45 | 0-15 | 24/24 | 23.1-25.0 |
  | 30 | none | 49, 40, 35, 37, 52 | 0 | = missing | 1/12 | 24.7-26.3 |
  | 30 | lossless_jpeg | 90, 88, 89, 89, 91 | 25-50 | 41-65 | 24/24 | 23.2-25.4 |

- Worked: uncompressed 25 fps is clean in 5 of 5 takes (earlier same day: 4 of 5). With T23 the queue never builds when uncompressed.
- Did not work: lossless at 25 fps (queue fills, 20-35 % lost); anything at 30 fps (libcamera delivers about 24.5 fps with recording on,
  so about 50 of ~285 frame indices never arrive, before Core's queue).
- Why: **confirmed** that the 25 fps lossless loss is the queue filling behind the encoder (`dropped_queue_full` large, `peak_queue` 24/24,
  uncompressed on the same build is clean). **Probable** that the 30 fps capture ceiling is the work done on libcamera's completion thread
  (dma-buf sync + 16.9 MB memcpy before `requeueRequest`; T25's estimate ~8 of 33 ms); not yet measured on this build (T25 step 3.2).
  The bimodal 24.5 / 20.6 fps pattern seen after the morning reboot did not recur in these 20 takes; it coincided with `cpptools-srv`
  (about 1 GB, 0.4 core) on the Pi. **Unconfirmed** that this was the cause: not re-run with cpptools loaded.
- Confirmed by: measurements run on the Pi at Patrik's request; interpretation of the 30 fps ceiling awaits T25 step 3.2.
- Tutorial: T22 (correction), T23 (build), T25 (next lever).

## 2026-10-26: unplanned NVMe controller drop at 19:35:32 while idle (`CSTS=0xffffffff`); APST and ASPM disabled

- Tested: Pi 5 (4 GB), NVMe on PCIe, /media/RAW exFAT. Observed during T23, Core idle.
- Worked: recovery by PCIe re-init (no reboot needed at the time); clips on disk intact (C0001-C0049 present).
- Did not work: the drive itself, once: controller status read as all ones, i.e. the device stopped answering on the bus.
- Why: **unconfirmed**. Candidates are NVMe power-state or PCIe ASPM transitions. Boot args added as a precaution:
  `nvme_core.default_ps_max_latency_us=0 pcie_aspm=off` (backup `/boot/firmware/cmdline.txt.bak-20261026`), present in `/proc/cmdline`
  since the 19:43 reboot. About 8 minutes of idle watching plus the 20-take run above (20:06-20:16) with no further drop; far too short to
  call it fixed. exFAT was left marked dirty (fsck.exfat -n by Patrik pending).
- Confirmed by: Pi kernel log (Patrik); the cause is not confirmed.
- Tutorial: T23.

## 2026-10-26: T25 (raw copy off libcamera's thread) removes Core's cost there; 30 fps Clear HDR 16-bit still delivers only ~26 fps

- Tested: Pi 5 (4 GB), Apertar-Core branch `clearhdr-fixes` 351a3ee (T23 + T25), 3840x2160 Clear HDR 16-bit, uncompressed cDNG, exFAT on NVMe,
  Pi otherwise idle, 20:33-20:38.
- Worked: safety pass (3 takes at 25 fps, 0 missing, 12/16-bit switches, `record_stop` under lossless 30 fps load returned in 0.09 s,
  Clear HDR off/on, same PID throughout, no `drop[copy-slot]`, files the same size as before, 16,590,340 bytes). `usample.py` on the
  CameraManager thread while recording at 30 fps: `requestComplete`/`recordRawFrame` no longer on the callchain (21 % before T25).
- Did not work: 30 fps. Takes C0077-C0079 missed 46/30/33 of ~287 (before T25: 35-52), all `dropped_gap_estimate`, `peak_queue` 1/12,
  ipa 25.1-26.4 fps.
- Numbers: CameraManager busy idle at 30 fps 44 % (29.99 fps delivered) = ~14.7 ms per frame for libcamera's swap + stats; recording
  at 30 fps 61 % at ~26 fps = ~23.5 ms per frame with Core's share gone. The same libcamera passes take ~60 % longer while recording.
- Why: **confirmed** that Core's copy is off the thread. **Probable** that the remaining loss is memory-bandwidth contention: recording
  adds the copy (read + write) and the NVMe writes to the CFE DMA and libcamera's two full-frame passes; T22 already showed memory traffic
  alone (dd to tmpfs) costs frames. **Unconfirmed**: why the thread loses frames at 61 % busy rather than 100 %; whether the CFE runs out
  of queued buffers (needs the `has no buffer` line, not printable on this kernel, T22 4.6).
- Confirmed by: measurements run on the Pi at Patrik's request; interpretation pending.
- Tutorial: T25.

## 2026-10-26: 30 fps Clear HDR 16-bit loss is a steady single-frame skip from a ~38 ms serial stage, not storage and not libcamera's thread running out of CPU

- Tested: Pi 5 (4 GB), Apertar-Core `clearhdr-fixes` 351a3ee, 3840x2160 Clear HDR 16-bit, 30 fps, uncompressed cDNG, exFAT on NVMe,
  Pi otherwise idle. New read-only tool `working/tools/hwcount.py` (Cortex-A76 PMU, user-space counts of one thread). 20:41-20:43.
- Results, libcamera's CameraManager thread:

  | | fps delivered | thread busy | IPC | stall_backend | instructions / frame | cycles / frame | L3 refills / frame |
  | --- | --- | --- | --- | --- | --- | --- | --- |
  | preview only | 30.00 | 41 % | 1.87 | 12 % | ~47 M | ~25 M | 0.57 M |
  | recording | 26.45 | 54 % | 1.30 | 21 % | ~47 M | ~36 M | 0.57 M |

  Cores while recording: 59/44/48/38 % (idle 2/1/2/41). Five other Core threads at 18-20 % each. `nr_writeback` ~3 MB.
- Gap pattern (C0077-C0079, from the DNG frame indices): every gap is exactly **one** frame, every 5-9 frames, and the first gap comes
  only after 27-47 frames. No double gaps, no bursts.
- Why: **confirmed** memory contention slows libcamera's passes: the same instructions and the same cache misses take ~45 % more cycles
  while recording (IPC 1.87 -> 1.30). **Confirmed** that this thread is not saturated (54 %, ~20 ms of 33). **Probable**: a serial
  per-frame stage takes ~38 ms (1/26.45 s) while recording; the 8 raw buffers absorb the deficit for the first ~1-1.5 s, then the CFE
  skips one frame each time it falls a full frame behind. Single regular gaps rule out storage stalls (those come in bursts).
  **Unconfirmed**: which stage. Candidates: the CameraManager work plus the PiSP back end (preview) and the IPA run strictly one after the
  other per frame, each slowed by memory traffic. Settles with libcamera's own per-stage timing (`LIBCAMERA_LOG_LEVELS=RPI:0`, needs a
  Core restart with that variable) or by recording without the preview/BE output.
- Confirmed by: measurements run on the Pi at Patrik's request; interpretation pending.
- Tutorial: T25 (follow-up).

## 2026-10-26: the 30 fps limit is libcamera's single CameraManager thread: back-end completions wait behind the next frame's swap + stats

- Tested: Pi 5 (4 GB), Apertar-Core `clearhdr-fixes` 351a3ee, Clear HDR 16-bit 4K, uncompressed, 30 fps, Core started with
  `LIBCAMERA_LOG_LEVELS=RPI:0,RPiStream:0` (drop-in `libcamera-debug.conf`, Patrik). 5 s windows idle and recording, parsed with
  `working/tools/libcam_stages.py`. 20:50.
- Results (medians):

  | stage | preview only | recording |
  | --- | --- | --- |
  | CFE arrival interval | 33.3 ms (p90 33.3) | 33.3 ms (p90 66.6: skips) |
  | software raw stats (libcamera's figure) | 5.8 ms | 7.1 ms |
  | CFE image dequeue handler (swap) | 6.1 ms | 9.9 ms (p90 13.3) |
  | CFE dequeue -> IPA signalled (incl. queue wait) | 13.0 ms | **217 ms** (6-7 frames waiting) |
  | back end start -> back end done (as seen by the thread) | 13.4 ms | **34.6 ms** |
  | back end start interval (pipeline period) | 33.3 ms | **36.2 ms** (= 27.6 fps) |
  | back-end completions logged right after CFE/stats work | 24 % | **78 %** |

  No libcamera drop lines in either window.
- Why: **confirmed** the RPi pipeline runs one frame at a time through IPA + back end, and while recording each cycle takes ~36 ms,
  so frames pile up in the Bayer queue (217 ms), the 8 CFE buffers fill, and the CFE skips one frame whenever it falls a full frame behind
  (matches the single-frame gaps). **Probable** (78 % of completions arrive straight after a swap/stats run): the back end's completion
  event is not handled until the CameraManager thread finishes the next frame's synchronous `rev16` swap and software stats (~17 ms while
  recording), and memory contention makes those passes and the back end itself slower. Core cannot fix this: the fix is in libcamera
  (move the swap and raw stats off the event thread, or let the next frame start while the back end runs).
- Confirmed by: measurements run on the Pi at Patrik's request; interpretation pending.
- Tutorial: T25 follow-up.

## 2026-10-26: libcamera with software raw stats on every 4th row pair: 30 fps Clear HDR 16-bit improves from ~26 to ~28.5 fps, not yet clean

- Tested: Pi 5 (4 GB), Core `clearhdr-fixes` d9f00d4, libcamera `Tiramisioux/libcamera` `apertar` 889567a built into
  `~/opt/libcamera-apertar` and loaded through a drop-in (`libcamera-test.conf`: `LD_LIBRARY_PATH`, `QBC_RAW_STATS_ROW_STEP=4`).
  Confirmed loaded: `/proc/<pid>/maps` shows the private libcamera, libcamera-base and IPA; journal `RawStats row step 4`. 21:01-21:05.
- Results: 25 fps uncompressed C0087 144/144, 0 missing. 30 fps uncompressed C0089-C0091 missed 7/8/20 (before: 30-46), all
  `dropped_gap_estimate`, `peak_queue` 1/12, delivery 28.8/28.7/27.6 fps (before 25.1-26.4). CameraManager thread busy 43 % recording
  (before 54 %).
- Not tested: AE/AWB quality with the sparser stats. ISO, shutter and WB were manual in these takes (800, 20000 us, 4000 K), so the
  stats steered nothing. Also not separated: the private build at row step 1 (same code as the installed library otherwise).
- Why: **confirmed** that less work on the CameraManager thread raises delivery. **Probable** that the remaining loss is the 16-bit
  endian swap (~10 ms per frame under load) still holding the thread when the back end completes.
- Confirmed by: measurements run on the Pi at Patrik's request.
- Tutorial: T25 follow-up (libcamera L1).

## 2026-10-26: libcamera L2 (swap + stats on a worker thread) runs safely but does not raise 30 fps delivery

- Tested: Pi 5 (4 GB), Core d9f00d4, libcamera `apertar` 6b0b49f in `~/opt/libcamera-apertar`, drop-in `QBC_RAW_STATS_ROW_STEP=4`,
  `QBC_RAW_CPU_WORKER=1` (journal: "Raw CPU passes run on a worker thread"). 21:10-21:16.
- Worked: 25 fps uncompressed C0095 144/144; DNG pixel data in the right byte order (median raw 3643 vs 3625 before, same scene);
  Clear HDR off/on, lossless 30 fps stop under load (109 ms), fps changes while running, no errors, same process throughout.
- Did not work: 30 fps uncompressed C0098-C0100 missed 27/31/14 (L1 alone: 7/8/20; before L1: 30-46), delivery 26.3-28.2 fps.
  CameraManager thread 34 % busy while recording (L1: 43 %, before: 54 %).
- Why: **confirmed** the pipeline thread is no longer the limit (34 % busy, still losing frames). **Probable**: the remaining limit is
  the back end itself (hardware, memory-bound): with the swap now overlapping the back end in time, both compete for memory, and the
  per-frame cycle does not shrink. **Unconfirmed**: back end start->done with L2; settles with one more `LIBCAMERA_LOG_LEVELS=RPI:0` window.
  Take-to-take spread is large (C0091 20 vs C0089 7), so 3 takes per setting are a weak comparison.
- Confirmed by: measurements run on the Pi at Patrik's request.
- Tutorial: T25 follow-up (libcamera L2).

## 2026-10-26: imx585 crop rectangles per mode (T26) reach libcamera and Core; binning now readable

- Tested: Pi 5 (4 GB), driver `cinemate-port` `24172e6` via DKMS (module 21:36, after reboot), Core `cinemate-port` `4ab1057`
  (built 21:39), system libcamera `/usr/local` 0.7.1.
- Seen: all 42 probed modes carry the window the WINMODE registers read (`list_sensor_modes`); binning 2 for every 1920-wide
  mode, 1 for every 3840-wide one, all `driver`; current mode (16-bit Clear HDR 4K) `sensor_binning 1`, crop `(0, 0)/3840x2160`.
  Frame-rate limits unchanged in Clear HDR (30). Core started `ready`.
- Not tested: preview framing and recorded pictures per mode class (T26 step 5's picture check).
- Why: **confirmed** that libcamera's `ScalerCropMaximum` is the driver's `.crop` copied into the subdev state.
- Confirmed by: Patrik ("consider T26 finished"), measurements over the socket.
- Tutorial: T26.

## 2026-10-26: the installed libcamera's imx585 lattice changes HMAX for a 1 µs frame-duration change (T27 3.3)

- Tested: Pi 5 (4 GB), system libcamera `7e9fef0` (contains `4cff971` "imx585 exact frame-rate getBlanking"), Core `cinemate-port`
  `4ab1057`, 3840x2160 Clear HDR 16-bit (stream 3840x2200), `set_fps` then `sleep 1`, `v4l2-ctl --get-ctrl=horizontal_blanking,vertical_blanking`.
- Seen: 25 fps (40000 µs) `0 / 3200` = HMAX 550 x VMAX 5400; 24.9993 fps (40001 µs) `217 / 2912` = HMAX 581 x 5112; 24.99 fps
  (40016 µs) `308 / 2802` = HMAX 594 x 5002. Exactly as `phase_lock_sim.cpp` case 6 and `cam_helper_imx585.cpp:119-232` predict.
  Read back without the pause, the subdev still shows the previous values.
- Why: **confirmed** that a pinned non-standard duration re-chooses the line length (up to +8 % here), not only the frame length.
  So a phase lock's ±1-2 µs pushes will alternate HMAX between frames: rolling-shutter skew changes by that much on those frames.
  Exposure is re-fitted by the helper. **Unconfirmed**: whether that is visible (T27's flat-grey and pan check).
- Also: Core truncates the pin (`int64_t(1e6 / fps)`, `CC:2086`), so 24.9994 fps is the same 40000 µs pin as 25.
- Confirmed by: Patrik's readback on the Pi.
- Tutorial: T27 3.3.

## 2026-10-26: imx585 free-running cadence is within ~1.5 ppm of the Pi's crystal; the phase lock would chase NTP (T27)

- Tested: Pi 5 (4 GB), Core `cinemate-port` `114bfb9`, 4K Clear HDR 16-bit 25 fps, preview. The phase lock as a meter:
  `APERTAR_PHASE_LOCK_DEADBAND_US=100000` (no pushes, sensor on Core's own 40000 µs pin), `err_us` every 250 frames; at the same
  time BOOTTIME - MONOTONIC_RAW sampled every 10 s (read-only python). 22:10-22:14.
- Seen: free-running error against BOOTTIME 83 ppm falling to 42 ppm within 3.5 min; BOOTTIME vs MONOTONIC_RAW in the same window
  49 → 39 ppm (`adjtimex`: PLL mode, 12.8 ms offset still being slewed; systemd-timesyncd last offset +22 ms, freq +3.17 ppm).
  Difference, i.e. sensor vs the Pi's raw crystal: **1.2-1.6 ppm, steady** (sensor slightly slow).
- Lock on (deadband 6): phase error within ±22 µs over 5000 frames, pin mostly 40002 µs, a push every 9-10 frames, each switching
  HMAX (lattice, see T27 3.3). The lock holds to BOOTTIME, so it makes the sensor follow NTP slews (tens of ppm after a correction).
- Why: **confirmed** that the large drift was the Pi clock being slewed, not the sensor. **Probable** that C0101's clean result
  (0 holes, WAV = frames) reflects the same: the sensor needs no lock at 25 fps.
- Also fixed on the way: the lock's `saturated` flag fired at every arm (pin history 4 < 8 requests in flight; history not
  seeded with Core's own pin): `3a18db0`, `114bfb9`.
- Left in the code, **off** after the measurement (2026-10-26; Patrik ran the undo) (`fps_phase_lock false`). A future version should reference an
  unslewed clock (MONOTONIC_RAW) or the audio crystal, not BOOTTIME.
- Confirmed by: measurements run on the Pi at Patrik's request.
- Tutorial: T27 5.1 / measurement.

## 2026-10-26: 60 s takes with and without the phase lock: the lock drops frames and makes the picture flicker (T27)

- Tested: Pi 5 (4 GB), Core `cinemate-port` `114bfb9`, system libcamera `7e9fef0` (imx585 lattice), 4K Clear HDR 16-bit 25 fps,
  uncompressed cDNG, ISO 800, 20000 µs, 4000 K manual, static scene. C0102 lock off (22:17:12), C0103 lock on (armed 20 s before,
  22:18:40). Measured with a centre band (rows 1040-1104) of every DNG; script in the session, logic in the T27 note.
- C0102 (off): 1490 frames, 0 holes, 0 dropped, WAV = 1490 frames; band level frame-to-frame step mean 0.017 %, p99 0.058 %,
  max 0.28 %, sd 2.0.
- C0103 (on): 1478 frames, 10 holes = `dropped_gap_estimate=10` (one `drop[capture-gap]` 80 ms), WAV 1488 frames;
  `phase-lock stats: max_abs_err_us=199 duration_pushes=673`; band step mean 0.53 %, p99 2.85 %, **max 8.9 %**, sd 30.1.
- Why: **confirmed** that on this libcamera the lock harms the picture: its pushes change HMAX, the helper's exposure re-fit does not
  hold the level, and period changes cost frames. **Probable**: the drops then kick the phase error and the servo pushes more.
- Note: the `phase-lock stats` line is printed at every record stop from telemetry that only resets there; with the lock off it
  can show leftovers from an earlier lock-on period (C0102 showed 31 pushes from 22:14-22:15).
- Decision: lock off (default). Confirmed by: measurements run on the Pi at Patrik's request.
- Tutorial: T27.

## 2026-10-26: second NVMe controller drop (54 s after a boot), with APST/ASPM off; Core's T28 media watcher reports it

- Tested: Pi 5 (4 GB), CFE HAT NVMe `/dev/nvme0n1p2` exFAT, boot args `nvme_core.default_ps_max_latency_us=0 pcie_aspm=off`,
  Core `cinemate-port` `e8bb1b7` (T28 built 22:27). Boot at 22:28:42 (cause unknown: the journal is volatile).
- Seen: dmesg `[54.53] nvme nvme0: controller is down; will reset: CSTS=0xffffffff`, read I/O errors, then
  `Disabling device after reset failure: -19`; `/sys/class/nvme/nvme0/state` = `dead`; `/media/RAW` still in the mount table,
  every access `Input/output error`. Earlier the same evening `fsck.exfat -n` found bad checksums and stray entries (0xc0/0xc1)
  in `/cDNG_26-10-26_C0030` (folder 19:34, a minute before the 19:35 drop); nothing repaired.
- Core: a hardware record press at 22:29:36 failed with `filesystem error: status: Input/output error` and Core kept running;
  at 22:29:37 the watcher logged `media: state=removed ... nvme_state=dead`; `/api/state` `media_state=removed`,
  `media_alive=false` while `media_mounted=true`.
- Why: **confirmed** that the boot args did not stop the drops. **Probable**: hardware (HAT power or contact, PCIe link, heat);
  not the software. **Confirmed** that T28's probe sees a dead NVMe behind a live mount.
- After a power cycle (22:30): NVMe `live`, writable; `throttled=0x0`, EXT5V 5.02 V, 57 °C; `brcm-pcie 1000110000.pcie: link up,
  8.0 GT/s PCIe x1` = **Gen 3**, from `config.txt:35-36` (`dtparam=pciex1`, `dtparam=pciex1_gen=3`; also `rp1-clk-333mhz`). Gen 3 is
  an overclock on the Pi 5 connector (certified Gen 2) and a known cause of `CSTS=0xffffffff` drops: **probable** cause here.
  Trade-off: 16-bit uncompressed 4K at 25 fps needs ~425 MB/s; Gen 2 x1 gives ~400 MB/s usable, Gen 3 ~800.
- Next (was): power-cycle; check `dmesg` for the link speed and errors after boot; watch whether it recurs idle; then delete C0030 and
  run `fsck.exfat` with repair.
- Confirmed by: dmesg and Core logs read on the Pi.
- Tutorial: T28 (an unplanned 5.x).

## 2026-10-26: PCIe Gen 2 test for the NVMe drops: 437 MB/s, 16-bit uncompressed 4K 25 fps still clean for 30 s

- Tested: Pi 5 (4 GB), `config.txt:36` `dtparam=pciex1_gen=2` (backup `config.txt.bak-gen3`), reboot 22:33; dmesg
  `link up, 5.0 GT/s PCIe x1`; `throttled=0x0`; Core `e8bb1b7`.
- Seen: Core `run_media_speed_test` (1024 MB direct fio, QD32) **437 MB/s**. `takes.sh 1 30`: C0104 742 frames, 0 missing,
  0 dropped, `peak_queue=1/12` (needs ~425 MB/s; 12.6 GB written, > RAM).
- Not yet known: whether the drops stop at Gen 2 (needs hours of idle and recording without `CSTS=0xffffffff`), and whether
  a 10-minute take holds with ~3 % margin. `ipa_rate.py` prints nothing since the `IPARPI:ERROR` drop-in (it counts IPA lines).
- Confirmed by: measurements run on the Pi at Patrik's request.

## 2026-10-26: CFE card pulled with T28 built: record still starts, the take never ends, reboot needed

- Tested: Pi 5 (4 GB), Core `cinemate-port` `e8bb1b7` (T28), PCIe Gen 2, CFE card pulled between 22:34:49 and 22:36:35,
  then record pressed (Patrik).
- Seen (Patrik): recording started; it did not stop by itself; Core could not get out of it; Patrik rebooted (boot 22:36:35).
  Nothing of that take is on the card (newest folder C0104, 22:34:49). Journal lost (volatile).
- Why: **probable** that T28's probe still saw the medium as alive: on a CFE pull the kernel keeps `nvme0n1p2` and the
  controller stays `live` until the first I/O times out (NVMe default 30 s), so the gate passed and the watcher had nothing
  to report; frames went to the page cache. **Probable** that the stop then hung joining writer threads stuck in `write()`
  on the vanished device. The CFE HAT's status byte (`0x34` bus 1, bit 0 = card out; `0x02` with the card seated) is the
  immediate signal, and T28 does not read it.
- Next: T28 follow-up: (1) HAT card-present bit in `MediaProbe` (or a state file written by the automounter, see issue #20);
  (2) when the medium is gone, stop without joining writers blocked in the kernel. Then repeat the pull with a persistent
  journal.
- Confirmed by: Patrik's report; the card's contents.
- Tutorial: T28 5.2 (CFE variant).

## 2026-10-26: CFE pull test with the HAT slot bit (0b1632f): detection works; re-insert breaks the card; stop waited 22.6 s

- Tested: Core `0b1632f` (HAT slot bit, bounded dead-medium stop), persistent journal, card pulled three times idle (22:46:09,
  :25, :31) and re-inserted each time, then record (22:47:16), stop pressed during the take.
- Seen: every pull logged `media: state=removed ... nvme_state=- hat_card=out` within the 1 s watcher cycle without touching the
  device; every re-insert `state=mounted ... nvme_state=live hat_card=in`. But the card was unusable after re-insert:
  direct write `Input/output error`, `exFAT ... set read-only`, controller `dead` (dmesg 665 s, `lost async page write`).
  Record at 22:47:16 passed the gate; `drop[queue-full] queue=12/12` after 0.7 s; nothing written; at 22:47:40 the kernel
  failed the I/O: `write_failures=4`, `recorder stop time: 22.631s`, `Audio capture write failed`. The touch UI kept READY
  (it reads the mount table via QStorageInfo, not Core's `media_alive`).
- Why: **confirmed** the HAT bit sees pulls at once. **Confirmed** a Pi 5 cannot hot-plug the CFE NVMe: a re-inserted card needs
  a PCIe remove/rescan (remount) or a reboot. **Confirmed** the stop hang was writers stuck until the NVMe timeout (~24 s).
- Fix: `a3ac8da` (pulled latch per mount id; write-stall detection in the take and in every stop). Touch UI: open (UI repo).
- Confirmed by: Core journal and dmesg on the Pi; Patrik's report on the UI.
- Tutorial: T28 5.2.

## 2026-10-26: CFE card pull and re-insert work end to end (Core a3ac8da+70e8376, UI 160898c+dc471c1); a stopped take is lost if pulled within ~30 s

- Tested: Pi 5 (4 GB), PCIe Gen 2, Core `cinemate-port` `70e8376`, UI `cinemate-port` `dc471c1` (automounter installed to
  `/usr/local/libexec` 22:59:19, backup `apertar-cfe-automounter.bak-1.6.0`), persistent journal. Boot 22:59:33.
- Idle pull 22:59:56.42: automounter `card removed while mounted` (lazy unmount + PCIe remove); Core `state=none` 0.3 s later;
  touch UI NO MEDIA. Re-insert 23:00:00.07: `insert requested`, `resetting PCIe controller`, mounted 23:00:02.28; Core
  `state=mounted pulled=0` 0.5 s later. Take C0105 (23:00:09.9-11.3): 32/32 written.
- Pull during take C0106 (23:00:15.04): Core `recording failure: fault=media_removed` 0.21 s later; `dead-medium stages gyro_ms=0
  h264_ms=0 raw_ms=0 prores_ms=0 audio_ms=125`; Core responsive throughout. Re-insert 23:00:16.8, mounted 23:00:24.8 (8 s).
- **Data loss:** neither C0105 nor C0106 is on the card afterwards. C0106 is expected. C0105 had stopped cleanly 4 s before the
  pull: its frames were still dirty in the page cache (`vm.dirty_expire_centisecs=3000`, writeback every 5 s) and Core never
  syncs at stop (no `fsync`/`syncfs` in the recorders). **Confirmed**: a take pulled within ~30 s of its stop is lost.
- Why: **confirmed** that the HAT slot bit + automounter surprise-removal path gives clean detection, a bounded stop and a
  working re-insert without reboot (T18 defects 1 and 2 for CFE).
- Next: `syncfs` on the media root at record stop, with `media_writes_pending` (WRITING) held until it returns; then repeat.
- Confirmed by: Patrik ("it works"), Core and automounter journal.
- Tutorial: T28 5.2, T18 step 5.

## 2026-10-26: 3-minute 16-bit takes at Gen 3: a nearly full drive lost the frames, not the sync; capture gaps remain

- Tested: Pi 5 (4 GB), PCIe Gen 3 again (`config.txt.bak-gen3` restored 23:07), Core `cinemate-port` (T28 follow-ups, T29
  `26da30e`, T30 `60ce8e9`, sync `4ce382e`, then `0358fcf`), 4K Clear HDR 16-bit 25 fps uncompressed, `takes.sh 1 180`.
- C0106 (drive ~77 % full, T29 exFAT row 2 writers/queue 16/+2 buffers, sync 1 s): 166 missing, queue full from ~140 s.
  C0107 (81 % full, 4 writers/queue 12, sync 1 s): 676 missing, queue full from ~95 s. Fio burst 818 MB/s (1 GiB, QD32).
  NVMe 55 °C (crit 85). After `format_media` exFAT (no trim): C0001 (Patrik, ~3 min): 4558 written, 0 queue drops,
  peak 1/12, final sync 68 ms, 12 capture gaps from ~113 s, audio drift +18 ppm (`correction=none`), level steady (0.018 %).
- Why: **probable** that the drive's write cache shrinks as it fills (35 % full: C0101 10 min clean; 77-81 %: drops after
  40-60 GB); **confirmed** that the once-a-second syncfs does not limit throughput on an empty drive. **Confirmed** that T30's
  1 s ALSA ring made the drift figure unreliable (+1339 / -201 ppm); the 100 ms ring reads +18.
- Open: 12 capture gaps in 3 min (C0101 had none in 10 min before T28/T29/T30/sync): candidates are the sync thread, the media
  watcher's 250 ms probe + HAT reads while recording, or T30's writer.
- Confirmed by: measurements on the Pi at Patrik's request; format done at Patrik's request (all clips deleted).
- Tutorial: T29, T30.

## 2026-10-26: the once-a-second syncfs costs capture frames; a crash right after a PCIe re-insert at Gen 3

- Tested: Core `0358fcf`, Gen 3, freshly formatted exFAT, 16-bit 4K25 uncompressed, ~3 min takes by Patrik.
  Sync on (`APERTAR_MEDIA_SYNC_MS` 1000): C0001 4558 frames, **12 capture gaps**. Sync off (drop-in `sync-off-test.conf`):
  C0003 4519 frames, **0 holes**, WAV = frames; C0002 (30 s) clean too. Queue peak 1/12 both ways; stop sync 67-68 ms.
- Crash (Patrik: "it was a crash"): card pulled and re-inserted 23:33:28, automounter PCIe controller reset + mount at
  23:33:33.8, C0004 started 23:33:36.31; the journal of that boot ends at 23:33:36.47 with no shutdown and no kernel message
  (hardware watchdog reset or freeze). C0004 is not on the card at all (sync was off).
- Why: **probable** that syncfs's once-a-second writeback burst competes with the memory-bound PiSP back end (capture gaps,
  not disk). **Probable** that the crash is the fresh PCIe link after the controller reset under immediate Gen 3 load; the
  22:28:42 reboot also followed NVMe trouble at Gen 3. **Confirmed** that without the sync a crash loses the running take.
- Next: smoother writeback instead of syncfs bursts (e.g. `sync_file_range` per DNG, or a shorter `vm.dirty_expire`), and
  re-insert tests at Gen 2.
- Confirmed by: Patrik's takes; journal of boot -1.

## 2026-10-26: per-DNG writeback alone is clean; with the 1 s syncfs it stalls the writers

- Tested: Core `441e42a` (sync_file_range per DNG), Gen 3, `takes.sh 1 180` (12→16 reconfigure first), 16-bit 4K25.
- Writeback, syncfs off (drop-in): C0004 4494 frames, 0 queue drops, no capture gaps, peak 1/12, stop sync 62 ms.
  Writeback + syncfs 1 s: C0005 3701 written, **782 queue drops**, 12 capture gaps, peak 12/12, stop sync 181 ms.
- Why: **probable** that syncfs waits for all pages already in writeback and the DNG writers block behind it. Next:
  `7d9dd60` (fsync of the clip folder instead).
- Also: Core answers `record_start` in 0.24 s and emits its `recording` event; the touch UI's apparent delay during these
  tests is `takes.sh`'s 12→16 reconfigure (~11 s) before it records (**probable**; Patrik to check with his own press).
- Audio drift figure with T30's writer still varies take to take (+18, +15, +64, -139, +156 ppm): open.

## 2026-10-26: writeback + folder fsync is clean; the touch UI misses takes started elsewhere

- C0007 (Core `7d9dd60`: per-DNG `sync_file_range` + 1 s `fsync` of the clip folder; Gen 3; `takes.sh 1 180`): 4495 frames,
  0 missing, no capture gaps, queue peak 2/12, stop syncfs 59 ms, audio writer peak 9 KB.
- Patrik: the tally LED lit "a couple of seconds" before the touch UI showed recording. Cause (code, **confirmed**):
  `ApertarCoreApp::publishEvent` collects events raised during a command into that command's reply unless they are on its
  broadcast list, and `recording` was not, so only the sender heard it; the tally reacts to the same event inside Core
  (`handleTriggerEvent`). The touch UI then learned on its next `get_state` poll (`kSteadyStatePollIntervalMs` 30 s).
  Fix `086443c`. Upstream behaviour (**probable**: the list is unchanged from 1.6.0).

## 2026-10-26: pull with writeback + folder fsync: folder and names survive, files are 0 bytes

- Tested: Core `086443c` (writeback per DNG, 1 s folder fsync), take C0010 started 23:56:19.1, card pulled 23:56:21.28.
- Seen: automounter `card removed while mounted` + Core `recording failure ... media_removed` within 9 ms; `written=52`;
  `dead-medium stages raw_ms=20 audio_ms=1277`; re-insert remounted in 3.9 s. After: folder C0010 with 48 `.dng` names,
  **all 0 bytes**. C0008/C0009 (stopped normally just before) complete, WAV = frames.
- Why: **probable** that the data blocks reached the card (writeback started per file) but each file's exFAT entry (size,
  first cluster) was still dirty in memory; the folder fsync writes the folder, not the files' entries. Fix `5b68f1f`.
- Confirmed by: the card's contents after re-insert.

## 2026-10-26: pull mid-take with per-file fsync: all frames up to ~0.9 s before the pull are readable

- Tested: Core `5b68f1f` (writeback per DNG; 1 s sync thread fsyncs each finished DNG, then the folder), take C0011 (~11 s),
  card pulled 23:58:57.26.
- Seen: HAT `hat_card=out pulled=1` → `recording failure ... media_removed` 0.6 ms later; automounter `card removed` 10 ms
  later; `written=280`; `dead-medium stages raw_ms=78 audio_ms=608`; re-insert mounted 23:59:08.4. On the card: 281 files,
  **258 full frames (readable, band level steady, max step 0.078 %) and 23 empty** (the last 0.9 s). `audio_capture.raw`
  0 bytes, no WAV (skipped on a dead medium by design).
- Why: **confirmed** that fsyncing each finished file within a second keeps a pulled take readable to ~1 s before the pull.
  Audio raw fix `b606c4f` (fsync once a second); `working/tools/raw2wav.py` turns a recovered raw file into a WAV.
- Confirmed by: the card's contents after re-insert.

## 2026-10-27: pull mid-take keeps picture to ~0.8 s before the pull and all but the last moment of audio

- Tested: Core `b606c4f` (audio raw fsync once a second), take `cDNG_26-10-27_C0001`, pulled 5.4 s in (00:01:53.43).
- Seen: 102 readable DNGs (4.1 s, band level steady, max step 0.058 %) + 21 empty; `audio_capture.raw` 1 445 778 bytes =
  5.02 s s24 stereo 48 kHz, real signal in all 502 sampled 10 ms blocks (peak -44.7 dBFS); `raw2wav.py` made
  `cDNG_26-10-27_C0001.recovered.wav`. Stop: `dead-medium stages raw_ms=2 audio_ms=488`; remount 7.4 s after the pull.
- Why: **confirmed** that a pulled take now keeps its picture to within a second and its audio as raw PCM, recoverable to WAV.
- Confirmed by: the card's contents after re-insert.

## 2026-10-27: 3-minute take with per-file fsync: clean

- Core `b606c4f` (writeback per DNG; 1 s sync thread fsyncs each finished DNG, the folder; audio raw fsync), Gen 3, drive
  38 % full, `takes.sh 1 180`: `cDNG_26-10-27_C0002` 4494 frames, 0 missing, no capture gaps, peak 2/12, stop syncfs 59 ms,
  audio drift -20 ppm. **Confirmed**: the per-file sync costs no frames; with C0011 / 2026-10-27 C0001 a pulled take keeps all
  but its last second, audio included.

## 2026-10-27: T21 time-left estimate and T30's fitted drift on the Pi

- Tested: Core `3c4f07d` (restart 22:19:28), cDNG 12-bit lossless 4K25, 502 GB free.
- T21: `/api/state` `record_time_left_minutes` 36.7, `time_left_label` "cDNG 12-bit lossless estimate (bar: 2 h)",
  `time_left_percent` 30.6; by hand with the touch UI's model 8.69 MiB/frame → 36.7 min (old Core model: 24.9 min).
- T30 (`ebdcd08`): 70 s take C0013 (socket start/stop, no reconfigure): 1748 frames clean; `audio clock:
  measured_drift_ppm=-15 points=6968 endpoint_ppm=-15 correction=none`. Media-tune helper: no call since the restart.
- HDMI (touch UI) 35 min vs WebUI 36 after the C0013 take: Core 35.96 min from 468 997 MiB free; the WebUI rounds,
  the touch UI truncates whole seconds. **Confirmed**: the two models agree.
- T20 pull while idle (Patrik, 22:24:37): automounter lazy-unmounts in 0.5 s, so Core reports `state=none` and the strip reads
  "No Media Mounted"; "Media Removed" shows only while a dead mount stays (e.g. a USB stick, which the automounter does not
  handle). Re-insert remounted at 22:24:47. Patrik: "yanking works fine".

## 2026-10-27: 16-bit time left: WebUI 37 min (right), HDMI 50 min (touch UI read 16-bit as 12)

- Tested: Core `3c4f07d`, cDNG 16-bit uncompressed Clear HDR 4K25, 997.6 GB free (Patrik's WebUI screenshot + HDMI).
- Core 37.7 min (16.8 MiB/frame; C0101's DNGs are ~17 MB). Touch UI `currentRawBitDepthNumber()` returned 12 for "16-bit"
  → 12.6 MiB/frame → 50.3 min. **Confirmed** by the arithmetic and the code. Fix UI `2d27c46`; rounding `bda2066`.
- After `bda2066` + `2d27c46` (Core and UI restarted 22:35): Core 37.8 min, WebUI and HDMI both 37 (Patrik: done).


## 2026-10-28: T31 speed ramping, first ramp take (1080p uncompressed, 25 → 50 → 25)

- Tested: Core `faa2958` (T31 without the `ramp_fps` stepper; restart 19:06:45), IMX585 1920x1080 (2×2 binned), cDNG
  uncompressed, `fps_speed_ramp` on, shutter `angle`, 24000 µs at 25; pi-nvme exFAT. 25 `set_fps` steps of 1 fps every
  ~0.25 s up to 50, 5 s hold, 25 steps down, 5 s at 25; socket-driven (`/tmp/ramp-take.sh`).
- `cDNG_26-10-28_C0030`: 1107 DNGs, 0 missing, `dropped_queue_full=0`, no `drop[...]` lines; stats `changes=50 base_fps=25
  min_fps=25 max_fps=50`; `fps-ramp.txt` 50 lines, all applied and seen (`superseded=0`).
- `lag_frames=7` on all 50 steps, request to the first frame at the new period. Grace = max(10, N+6) covers it.
  **Confirmed** for this mode and medium (handoff question 2); Clear HDR (more requests) not measured yet.
- DNG `FrameRate` 25 on frames 100, 600 (inside the 50 fps segment), 1100; timecode = frame/25 (`00:00:24:00` at 600);
  ExposureTime 1/42 at 25, 1/83 at 50 (angle kept). WAV 32.8 s real time; picture 1107/25 = 44.3 s on a 25 timeline.
  The settings ended at 25 (no restore needed). **Confirmed**: the T31 mechanics on hardware. Not checked yet: Resolve import,
  the `exposure` policy, MLV, a 2× step in one request.

## 2026-10-28: Clear HDR ISO → gain code; 12-bit cap at ISO 720 (request 18)

- Tested: Core `4f7975f`, driver `cinemate-port` `24172e6`, 4K Clear HDR 12-bit lossless, preview only; `set_iso` then
  `v4l2-ctl -d /dev/v4l-subdev2 --get-ctrl analogue_gain`. SDR ISO 800 → code 60.
- Clear HDR 12-bit: ISO 600 → 51, 640 → 53, 680 → 55, 700/716 → 56, **720 → 57**, 750 → 58, 800 → 60; 900, 1600, 2000 → Core
  clamps to 800 (the lossless ISO cap, `CC:2572`), code 60. Mapping: code = 20·log10(ISO/100) / 0.3 dB. **Confirmed.**
- So Apertar's 12-bit Clear HDR ceiling for the sensor's combine window (GAIN ≤ 17.1 dB = code 57, `imx585.c:164-165`) is
  **ISO 720**; 16-bit's is the driver's code 80 (`IMX585_ANA_GAIN_MAX_HDR`, `imx585.c:169`) = **ISO 1585**. Cinemate's 799/1585
  (`docs/clear-hdr.md`) are the same limits in its ISO scale.
- Apertar writes a fixed DNG WhiteLevel (`CdngEncoder.cpp:1373-1374`: 65535 in 16-bit, the CCMP table's end in 12-bit), so
  Cinemate's reason to hold ISO during a Clear HDR take (WhiteLevel from the first frame) does not apply; no hold. Unmeasured
  here: whether the 16-bit merge clamps below 65535 at high gain, as Cinemate measured (code 80 → ~48600).
- Build note (2026-10-28): g++ 14 warns `-Warray-bounds` in `CdngEncoder::writeRawPayload` (`vld1q_u16` on a `uint16_t[8]`)
  whenever `CdngEncoder.cpp` is rebuilt; existing code, not from the speed-ramp/Clear HDR commits. Probably a false positive; unexamined.

## 2026-10-28: Clear HDR holds ISO/WB and caps ISO (8175273), preview test

- Tested: Core `8175273` (restart 20:09:09), 4K uncompressed, preview only (`/tmp/hdr-hold-test.sh`), dark desk scene.
- SDR auto ISO + WB (code 60) → Clear HDR 12-bit: `iso_auto`/`wb_auto` false, `iso_auto_after_clear_hdr`/`wb_auto_after_clear_hdr`
  true, ISO held and capped to 720 (code 57), WB held at the measured 2815 K. `set_iso_auto`/`set_wb_auto` refused with the info
  message. `set_iso 1600`: 12-bit → 720 (code 57), 16-bit → 1585 (code 80); 3200 → 1585. A manual ISO in Clear HDR cleared the ISO
  flag, so SDR kept ISO 720 manual while WB went back to auto. Round trip with both auto: held in Clear HDR, auto again in SDR;
  flags persisted. **Confirmed.**
- Seen: while auto ISO runs, the state's `iso` is the stored value (720 after the round trip), not the live gain; request 16.

## 2026-10-28: H.264 on the IMX585 (Core ac00fb0): 4K capture only, 30 fps cap, x264 has headroom

- `set_record_format h264`: capture stays 3840x2160 (a 1920x1080 `set_resolution` is ignored), output 1920x1080, libx264
  `tune=zerolatency`, `input=staged-yuv`. `set_fps` 50 or 60 → 30.
- 10 s takes: 25 fps 235/235 frames, 30 fps 294/294 (`ffprobe` 294, avg 30/1), `dropped_queue_full=0`, peak queue 1/6;
  Core 69-84 % of one core. **Confirmed**: the encoder is not the limit; Core's H.264 capture choice is.
- The H.264 MP4 and the ProRes MOV are video-only (one stream: `LibavH264EncoderPlugin.cpp:124`, `ProresEncoder.cpp:929`);
  audio is the clip folder's WAV, as for cDNG. Speed ramping in H.264 stays refused (Patrik): 25 → 30 is too little.

## 2026-10-28: experimental stretched WAV (ca7b7c2), camera-wide switches, conform_fps

- Rubber Band: `rubberband-cli` 3.3.0 installed by Patrik (`apt update` first: the image has no apt lists). Click test
  (real 4 s → 4 s, 6 s → 8 s, `-D 12 --timemap`): output 12.0000 s, clicks 1.0 / 5.976 / 10.0002 s. Key frames are exact; inside a
  re-timed stretch Rubber Band smooths by ~25 ms; nothing accumulates. ffmpeg `rubberband`/`atempo` with `asendcmd`: 20-50 ms off
  per change, accumulating. A `0 0` map line makes Rubber Band warn about a NaN ratio (dropped in the follow-up commit).
- Core ca7b7c2 (restart 20:54:18): `conform_fps` 25 by default, 24 accepted, 0 refused. Ramp, stretch and phase lock turned on in
  H.264 stay on after switching to cDNG (92b4be3, 117065d).
- `C0034` 1080p uncompressed 25 → 50 → 25 (set_fps steps): 909 DNGs = 36.36 s at 25; real-time WAV 25.809 s;
  `C0034_stretched.wav` 36.360 s, 48 kHz, written seconds after stop (50 key frames); `fps-ramp.txt` `applied_us` 5038579 for frame
  126 (= 5.04 s at 25). **Confirmed** length and pitch; how it sounds is for Patrik to judge.

## 2026-10-28: iso_max per mode (Core 6d217c7, UI f1edf96), restart 21:13:18

- `get_state` `iso_max`: SDR lossless 800, SDR uncompressed 0, Clear HDR 12-bit 720 (ISO 800 capped to 720), Clear HDR
  16-bit 1585. **Confirmed.** UI started clean (`qml_aot=true`, no QML errors). The on-screen green values, the ISO lists and
  Lock wait for Patrik's look on the touch screen, HDMI and WebUI.
- Patrik (21:2x): green values, ISO lists, Lock, Clear HDR hold on the touch screen, HDMI and WebUI "work well". **Confirmed.**
- Patrik's hand-driven ramp take `cDNG_26-10-28_C0022` (4K lossless, WebUI block + FPS controls): 25 → 30 → 25 in 1 fps steps,
  10/10 changes applied, 439 DNGs, 0 missing, no drops; `_stretched.wav` 17.56 s (= 439/25), real WAV 16.06 s; back at 25 after
  stop. Patrik: "ramp works". **Confirmed**: T32 from the controls.

## 2026-10-28: T33 Core (b0e90ad), restart 21:35:30

- Socket: `help` lists `set_value_steps`; built-in lists in the web state's `ui` object; `set_value_steps` writes `fpsSteps`,
  `shutterAngleSteps`, `flickerFreeShutterAngles`, `mainsHz`, `fpsFree`, `fpsFreeIncrement` to UI.conf and the state follows;
  refused: no usable values, increment out of range, `mains_hz=55`, unknown name. **Confirmed.**
- Bug seen by Patrik: ISO green in SDR lossless. `iso_max` 800 = the operator's ISO 800, and the UIs' "on the ceiling" rule
  fired. Fix with T33 steps 2-3: green only when the cap is a system-added value (not in the operator's list).

## 2026-10-28: T33 lists, lossless ISO 1600, recording frame and red timecode (Patrik: "now it works")

- Core up to `4d5fdd1`, UI up to `da2a9b5`. Patrik confirmed on the touch screen, HDMI and WebUI: value lists with greyed
  values above the ceiling and green caps / flicker-free angles, the WebUI Value Lists card, ISO up to 1585 in Clear HDR
  16-bit lossless, the recording frame and the red-timecode switches. **Confirmed.**

## 2026-10-28: T34 M1, how long a class switch takes (preview, Standard preview profile)

- Core `4d5fdd1`, 4K, uncompressed; `set_clear_hdr` / `set_raw_bit_depth` timed from command to reply, three rounds, minus
  the ~45 ms `get_state` round trip: HDR16 → SDR12 45-65 ms, SDR12 → HDR12 80-110 ms, HDR12 → HDR16 90-110 ms. Each
  reconfigure logs `camera configured` right after. **Confirmed as a lower bound**: the reply comes when the new mode is
  queued, before its first frame; the visible blink (first frame) is not measured (M2). Far below the ~1 s the design would
  answer with a settle delay.
- Drive at 78 % (727 GB used, 206 GB free) before M3; this morning 65 %.

## 2026-10-28: T34 M3, 12-bit SDR at 50 fps, 60 s (3840x2076)

- Core `4d5fdd1`, NVMe PCIe **Gen 3 x1** (8.0 GT/s), exFAT, drive 78 % → 82 % after; cDNG uncompressed, 3840x2076 (the 12-bit
  crop mode Core allows 60 today; 3840x2160 SDR is still capped at 30, F5), speed ramp off.
- `cDNG_26-10-28_C0025`: 2632 DNGs of ~2987, **355 missing**; `dropped_queue_full=0`, `peak_queue=2/12`, `write_failures=0`;
  `dropped_gap_estimate=355`, 13 `drop[capture-gap]` lines. 30 GB.
- **Confirmed**: storage keeps up (queue never above 2); the frames are lost before the recorder, a back-end/capture limit
  (design §6 rule, F10: 20 ms per frame at 50 vs up to 34.6 ms back-end time while recording). Next per §6: one take with
  `APERTAR_RAW_CAMERA_BUFFERS=8`. Until then a 50 fps rung is not usable at this size.
- Repeat with `APERTAR_RAW_CAMERA_BUFFERS=8` (drop-in `zz-ladder-buffers.conf`, restart 22:20:11): `C0026` 2616 of ~2974,
  **358 missing**, `dropped_queue_full=0`, `peak_queue=3/12`, steady single-frame `capture-gap`s (dt 40 ms) as before.
  **Confirmed: not raw-buffer starvation.** About 6 frames/s never arrive (~44 of 50): probably the sensor/capture side at
  3840x2076 (frame timing or CSI rate) rather than Core; unmeasured. Parked by Patrik for a longer test later (card nearly
  full). 1080p at 50 is clean (`C0030`).

## 2026-10-28: ISO/WB dials to Auto, auto ISO in lossless (Core b5b787e, UI 682a186) — Patrik: "dial works"

- ISO dial below the first value → Auto; WB dial below the lowest → Auto; shutter Auto white. **Confirmed.**
- Auto ISO in IMX585 lossless: highest value seen **767** (gain 7.67), under the lossless cap 1600 and under the tuning's
  gain limit 8. **Confirmed for the default tuning in the scene tried** (`working/unverified-speed-ramp-port.md` #1: a dark
  scene and the `long` exposure mode are still untried).

## 2026-10-28: T34 Core (0041ba0, restart 22:42:48), first tests

- Socket: `get_mode_ladder` lists the probe's 40 modes as the pool; `set_mode_ladder … dry_run=true` with Patrik's ladder:
  rungs HDR16 ≤25 and SDR12 ≤30 (the 4K SDR cap), one warning (the look changes), no errors; bad rung text and falling
  thresholds refused with clear messages. **Confirmed.**
- Ladder on: 25 fps → rung 1 (Clear HDR 16-bit), `set_fps 30` → rung 2 (4K SDR 12-bit) in one reconfigure, 50 → 30, 24 →
  rung 1 again; `fps_max` = ladder ceiling (30), `fps_take_max` 25 / 30; a manual `set_clear_hdr` switches the ladder off
  (journal: "switched off by a manual mode change"). **Confirmed.**
- Take A (rung 1, 24 fps, `set_fps 50` in the take): FPS went 24 → 25 and stopped (`fps_take_max`), restored to 24 at stop.
  **Confirmed.** Take B (Ramp-ready + Speed Ramp, 24 fps): the camera was in rung 2 (SDR12) from the start, 24 → 30 in the
  take, no drops, back to 24. **Confirmed.**
- Seen: take A, Clear HDR 16-bit **lossless**, 24 fps: `dropped_queue_full=20` in ~6 s (149 DNGs). The `temp:` branch made
  Clear HDR imply uncompressed for this reason (T22: lossless was encoder-bound). Not a ladder fault; open: Clear HDR
  should force uncompressed again? (asked of Patrik)
- Power cut while changing the battery (22:43): the Pi rebooted twice, the test script's restore did not run; exFAT on the
  NVMe logged "Volume was not properly unmounted… run fsck"; mounted and readable, 206 GB free. Run `fsck.exfat` when
  convenient (unmount first).
- Correction: the Pi (CM5 + carrier) has a working RTC (`rpi-rtc` set the clock at boot, 22:49:22); journal times are reliable.
- Take A rerun, alone, polled every 0.5 s (Core `0041ba0`): rung 1 (HDR16 lossless) at 24 fps; `set_fps 50` at +4.5 s in the take →
  **25**, the take carried on, restored to 24 at stop. **Confirmed.** Take B (Ramp-ready) and the preset check also passed
  (the matching preset loads; one naming another mode is refused with the message). The first run's take A had ended ~16 ms
  before the request (the request then switched to rung 2, by design); cause unknown, not reproduced; two takes of 3.0 and
  3.85 s ran just before it. Possibly a record/stop pressed on the camera during the run; leave the camera alone during tests.
- Clear HDR 16-bit **lossless** overflows the queue: `dropped_queue_full=19`, `peak_queue=24/24` in a 6.5 s take at 24 fps.

## 2026-10-28: T34 compression per resolution (Core 3cae990 + ab972fe), restart 23:09:36

- `get_mode_ladder` keys: `resolutions`, `resolutions_text`, `running_resolution`, `ceiling`, `enabled`, `ramp_ready`, `pool`, `errors`, `warnings`.
  Ladder `…hdr:25:none,…sdr::lossy_3to1`: dry run no errors, one warning; each resolution carries `compression` and
  `compression_set`. `lossy_5to1` on a Clear HDR resolution is an error. **Confirmed.**
- Ladder on: 24 fps → Clear HDR 16-bit **uncompressed cDNG**; 30 fps → SDR 12-bit **lossy DNG 3:1** (`recording_format`
  `lossydng`, ratio 3to1); back to 24 → cDNG uncompressed. `set_cdng_compression` and `set_lossy_dng_ratio` refused with the
  ladder message; MLV is still allowed with the ladder on. **Confirmed.**
- Short take at 24 fps in Clear HDR 16-bit uncompressed: 137 DNGs, `dropped_queue_full=0`, `peak_queue=2/12` (lossless in the
  same mode dropped 19 in 6.5 s). **Confirmed.**

## 2026-10-28: ladder data for the approved UI (Core e16033e), restart 23:31:36

- `ladder_text`: "Resolution 1 · 3840×2160 · ClearHDR16 · ≤25 · Uncompressed", "Resolution 2 · 3840×2160 · SDR12 · ≤30 · Uncompressed",
  ladder off: "3840×2160 · SDR12 · Uncompressed (ladder off)"; `ladder_tops` [25, 30]; `ladder_enabled`, `ladder_count`. **Confirmed.**
- `get_mode_ladder`: every resolution and all 42 pool modes carry `window_w/window_h/binning` (e.g. 1920x752 SDR 12-bit: window
  3840x1504, binning 2; 4K SDR 12-bit: 3840x2160, binning 1) and `ceilings` per compression (4K SDR: 30 in all four; 1920x752: 60,
  lossless 30; Clear HDR 16-bit: 25, lossy 0). **Confirmed.**
- An active ladder refuses `set_resolution`, `set_raw_bit_depth`, `set_clear_hdr` with the ladder message; with the ladder off they
  work again. **Confirmed.**

## 2026-10-29: WebUI playback (T46-T51), Core `f91fafa`..`4fa0432` (Patrik's Pi, CM5, NVMe exFAT PCIe Gen 3 x1)

Full tables in `working/playback/measurements.md`; the findings Patrik confirmed by trying them ("works well", "sound works"):

- One 4K frame, one worker, 640 w: Clear HDR 16-bit uncompressed 50-64 ms; SDR 12-bit lossless 166-190 ms (the Pi is about as fast as the dev host). A cold
  NVMe read of one 16.6 MB frame: 800 MB/s. **Confirmed.**
- `/api/media` took 6.8 s on every call (41 folders, 105,676 files). A readdir of 105,000 exFAT entries costs 3.7 s, so a cache that counts entries is as slow;
  the exFAT folder mtime moves with its newest entry, so the facts cache keys on it: 4.2 s once after a Core restart, then 20 ms. **Confirmed.**
- The viewer plays Clear HDR 16-bit uncompressed at 24 of 25 fps and lossless SDR at 9-11 fps, the picture within 0-2 frames of the sound (the sound is the clock). **Confirmed.**
- C0016: 4,913 frames in a span of 5,223 (310 missing in 30 holes, 5.9 %); its WAV is 209 s, the span, not the file count. **Confirmed.**
- In a take: `playback_hold` = `recording` within the command; frame, clip and file routes 409; a running download stops within 0.3 s of `record_start`;
  downloads 409, deletes refused; a 5 s take after all that: 90 of 90 frames, 0 dropped. **Confirmed.**
- A frame can be a hole (never written) or 0 bytes: the viewer draws it black (Patrik's requirement R2). Free Run takes carry the time of day as their recorded
  timecode, Rec Run takes 00:00:00:00 (the card shows it). **Confirmed.**

## 2026-10-29: NeoRotary 4 on bus 1 `0x49` (ID `0x87`), hat on bus 1 `0x34` with a card

- Tested: Patrik's Pi, IMX585 on cam0, RPI5-CFE-Hat, Core `4fa0432` (`cinemate-port`), Controls project M4. Core stopped for the seesaw read.
- Worked: `i2cdetect -y 1` lists exactly `34` and `49`. Seesaw hardware ID read at `0x49` (`w2@0x49 0x00 0x01`, then `r1@0x49`): `0x87`. Hat status read twice at `0x34`: `0x02` (a card). Core's start lines: `cfexpress hat on bus=1 address=0x34`, `NeoRotary4 input enabled: /dev/i2c-1 address=0x49`.
- Did not work: n/a
- Why: the file has `[neorotary4] bus=1` and `[cfexpress_hat] bus=1` (the 2026-10-23 DPI fix); read with Core stopped so it cannot fire phantom knob turns.
- Confirmed by: Patrik, a reading (M4 output shown, "yes" to log it).
- Tutorial: none (design `working/controls/design-controls.md` §8 M4).

## 2026-10-29: TMP117 answers on bus 10 `0x48`

- Tested: as above; `i2ctransfer -y 10 w1@0x48 0x0f r2@0x48` with Core running (Core does not poll `0x48`).
- Worked: ID `0x01 0x17`, the TMP117 device ID (datasheet `0x0117`).
- Did not work: n/a
- Why: bus 10 is the camera-side bus (`0x1a` there is held by a kernel driver, PROBABLE the sensor); `i2cdetect -y 10` also shows `0x34`, `0x48`, `0x68`.
- Confirmed by: Patrik, a reading (M4 output shown, "yes" to log it).
- Tutorial: none.

## 2026-10-29: I2C buses on this Pi: 0, 1, 10, 13, 14 (no bus 4)

- Tested: as above; `/dev/i2c-*` and `/sys/bus/i2c/devices/i2c-*`.
- Worked: `i2c-0` `1f00070000.i2c`, `i2c-1` `1f00074000.i2c`, `i2c-10` `1f00088000.i2c` (Synopsys DesignWare, on the RP1 chip); `i2c-13` `107d508200.i2c`, `i2c-14` `107d508280.i2c` (SoC). `/dev/i2c-6` and `-11` are links to `-10` and `-0`. Bus 4 does not exist, so the INA219 default (`bus=4`) points at nothing.
- Did not work: `/sys/class/i2c-adapter` does not exist on this kernel; read the labels from `/sys/bus/i2c/devices`. The i2c tools are in `/usr/sbin`, not on ssh's PATH.
- Why: command output of M3. `pi` is in the `i2c`, `gpio` and `systemd-journal` groups.
- Confirmed by: Patrik, a reading (M3 output shown, "yes" to log it).
- Tutorial: none.

## 2026-10-29: GPIO 6 and 10 are the button inputs, GPIO 21 the tally

- Tested: as above; `gpioinfo -c gpiochip0` and `pinctrl get 2,3,6,10,21`.
- Worked: lines 6 and 10: input, active-low, pull-up, consumer `apertar-gpio-input`; line 21: output, consumer `apertar-rec-led`. GPIO 2 and 3 are `a3` (SDA1/SCL1) in `pinctrl` but show no consumer in `gpioinfo`. GPIO 14 and 15 are `none`, and `config.txt` has no UART lines.
- Did not work: n/a
- Why: `d10=capture`, `d6=eject`, `[recording_indicator] target=gpio line=21` in `~/apertar-hardware.conf`.
- Confirmed by: Patrik, a reading (M5 output shown, "yes" to log it).
- Tutorial: none.

## 2026-10-30: the NVMe stalls after about 0.9 TB of writes without a trim; a trim restores it (Corsair MP600 Mini, exFAT, PCIe Gen 3 x1)

- Tested: Patrik's Pi, kernel 6.12.75+rpt-rpi-2712, Corsair MP600 Mini (firmware ERFM11.1), 932 GB exFAT with 128 KB
  clusters, mounted `rw,noatime` (no `discard`), PCIe Gen 3 x1; boot arguments include `nvme.max_host_mem_size_mb=0`.
  Core stopped. Test program outside Core (`/home/pi/ab-tests/variant2.py single`): 4 writer threads, 25 files/s,
  16.9 MB per file in 491 520-byte writes, one folder, 240 s per run, a frame dropped when 12 are queued. Drive
  temperature read from sysfs every 5 s. 48 runs overnight (single folder, sub-folders of 500, files created ahead)
  with one `fstrim` after run 4; then 23 runs in two arms: B = one trim, then back-to-back runs; A = a trim before
  every run. Core takes from earlier the same day (A0 to A4, stall hunt) ran on a drive in unknown state.
- Worked: after `sudo fstrim -v /media/RAW` (917.4 GiB) 9 runs in a row had 0 dropped, worst file 38 to 242 ms
  (overnight runs 5 to 13, all three layouts). Arm B repeated it: runs 1 to 9 (up to 909 GB written) 0 dropped, worst
  32 to 282 ms. Arm A, trim before every run: 12 of 12 runs 0 dropped, worst 34 to 265 ms, the first straight after
  two bad runs. After the crash below, a reboot plus a trim gave a clean run (0 dropped, worst 26 ms).
- Did not work: past about 0.9 TB without a trim every layout stalled: overnight runs 14 to 32 lost 29 to 77 %, worst
  file 5.5 to 10.2 s; arm B run 10 lost 28.2 % (10.8 s), run 11 43.0 % (9.0 s). Heat is not the cause: clean runs
  peaked at 60 to 72 C, bad ones at 65 to 70 C (the drive's warning limit is 82.9 C). Folder layout, creating files
  ahead and sub-folders (500, 1000, 2500 files) made no difference. At 01:43 to 01:45 (Pi clock, 2026-10-30) four
  256 KB writes got no answer for 30 s, the kernel logged `nvme nvme0: Disabling device after reset failure`, exFAT
  set the volume read-only and `/sys/class/nvme/nvme0/state` read `dead`; a reboot brought it back. No under-voltage
  (`throttled=0x0`), no PCIe error lines.
- Why: observed: Core's writer threads, during the slow seconds of a take, sat in exFAT metadata calls
  (`exfat_alloc_cluster` > `exfat_ent_set` > `__bread_gfp`; `exfat_write_inode` > `__wait_on_buffer`; others queued in
  `exfat_lookup` / `path_openat`) with nothing in flight on the device (23 stack dumps, one 4-minute take); the same
  bytes written into one large file were clean. Inference, not measured: the first bad run comes at about 909 to
  981 GB, close to the volume size (917 GiB), so after one pass the writes land on deleted but never-trimmed areas and
  the drive has to erase before it can write. CineMate has no trim either (`storage-automount.py` mounts exFAT
  `rw,noatime` and ext4 `rw,noatime,nodiratime,commit=60`; no `fstrim` or `discard` in its source or handbook). The
  drive asks for 64 MiB of host memory and gets none (`nvme: min host memory (64 MiB) above limit (0 MiB)`); whether
  that matters is untested.
- Not yet known: whether Core itself drops frames on a trimmed drive (the A0 to A4 takes and the stall hunt ran on a
  drive in unknown state and must be redone); whether a `discard` mount keeps the drive clean without per-take trims.
- Confirmed by: Patrik, ran the two trims, the reboot and the sudoers rule, read the results, and approved these
  readings for the log.
- Tutorial: none.

## 2026-10-30: Core's 10-minute 4K25 16-bit take is clean on a freshly trimmed drive (A0, defaults)

- Tested: Patrik's Pi, Core `a40112a` (binary built 2026-10-30 01:05), Corsair MP600 Mini, 932 GB exFAT,
  `rw,noatime`. `~/ab_matrix.sh` v2: `fstrim -v /media/RAW` (917.1 GiB), Core restarted with the defaults
  (`APERTAR_MEDIA_SYNC_MS=1000`, `APERTAR_DNG_WRITEBACK=1`, `APERTAR_CDNG_QUEUE_FRAMES=12`,
  `APERTAR_RAW_CAMERA_BUFFERS=8`; read back from the unit), drive cooled to 34 C, then `takes.sh 1 600`: one
  10-minute take, 4K, 25 fps, 16-bit Clear HDR, uncompressed cDNG, `media_class=pi-nvme`.
- Worked: 15001 frames written, 0 missing (`files=15001 last=15000`), `enqueued=15001`, `dropped_queue_full=0`,
  no `drop[...]` line of any kind, `write_failures=0`, `fault=` empty, `peak_queue=2/12`, `peak_backlog_kb=16`,
  stop-time `syncfs` 214 ms, peak dirty 11 MB and writeback 8 MB, drive 34 C at the start and 54 C at the end,
  NVMe state `live`. This meets the project's "done means" for the uncompressed case.
- Did not work: n/a for this take. The same defaults lost 31 % of the frames (4479 of 14616 `queue-full`) in the
  first matrix, on a drive that had not been trimmed.
- Why: the earlier drops were the drive's state, not Core's buffer mechanics (see the entry above: stalls after
  about 0.9 TB of writes without a trim). With the drive trimmed the queue never held more than 2 of 12 frames.
- Not yet known: whether the take stays clean on a second and third run (one take only); A1 to A4 on a trimmed
  drive (the matrix was stopped during A1); lossless JPEG, Log, and 50 fps SDR 12-bit on a trimmed drive; behaviour
  after more than one card of writing with Core's own trim (not built on the Pi yet).
- Confirmed by: Patrik, read the A0 result from the matrix summary and approved logging it.
- Tutorial: none.

## 2026-10-30: on a trimmed drive the in-take fsync is not needed; the per-frame writeback hint is (A1, A2)

- Tested: the same rig and test as the A0 entry (Core `a40112a`, 4K 25 fps 16-bit Clear HDR uncompressed cDNG, one 10-minute
  take per run, fresh `fstrim` before each, drive cooled to 55 C or below, service environment read back from the unit).
  A1: `APERTAR_MEDIA_SYNC_MS=0` (no once-a-second fsync). A2: A1 plus `APERTAR_DNG_WRITEBACK=0` (no per-frame
  `sync_file_range`, kernel writeback only).
- Worked: A1: 15000 frames written, 0 dropped in every counter, `peak_queue=1/12`, stop `syncfs` 236 ms, peak dirty 3 MB.
  The once-a-second fsync can go without any cost on a trimmed drive.
- Did not work: A2: only 13503 of about 15000 frames written, `dropped_queue_full=0`, `peak_queue=1/12`, but
  `dropped_gap_estimate=1491`: about 2.5 `capture-gap` events a second, each one frame (`dt_us` about 80 000 against 40 000
  nominal). The writers kept up; the camera front end lost about 10 % of the frames.
- Why: the only difference between A1 and A2 is the per-frame writeback hint, so that hint is what keeps the camera front
  end from stalling; this answers open question 2 of the drop-frames project page (kernel writeback alone does disturb the CFE
  on this board). It is one run; the mechanism inside the kernel is not measured. A bigger queue or buffer cannot help this:
  the frames are lost before they reach the queue.
- Not yet known: a repeat of A2; A3 (queue 64) and A4 (10 camera buffers) were not run (the matrix was stopped during A3).
  Note for every future reading: `takes.sh` reports `missing` from holes in the file numbering, and the numbering counts
  written frames, so capture gaps leave no hole (A2 showed `missing=0`). The check is frames written against fps x seconds,
  plus the `drop[capture-gap]` counter and `dropped_gap_estimate` in the capture stats line.
- Confirmed by: Patrik, read the matrix summary and asked for the results to be documented.
- Tutorial: none.

## 2026-10-31: short takes lose a few frames at capture; the 3-minute and 10-minute takes did not

- Tested: Core `drop-frames` build before the safety stop, defaults (Core restarted by the stop block), takes started from
  the WebUI, Core stopped nothing else, the Pi rebooted a few minutes earlier. Counters from the journal (`recording stats`,
  `capture stats: dropped_gap_estimate`).
- Seen: short takes: 351 frames written with a gap estimate of 2; 263 frames with 9; 145 frames with 4; 117 frames with 10
  (that one with Log on). All with `dropped_queue_full=0`, `peak_queue=2/12`, no write failure. The first `drop[capture-gap]`
  line came 2 to 4 s after the take started, each one frame (`dt_us` about 80 000). A later lossless-JPEG take of about 3
  minutes (4476 frames, queue 24) had no `drop[...]` line at all; the 10-minute A0 and A1 takes had none either.
- Why: not established. The writers are fine, so this is the camera front end. Two things differ from the clean 10-minute
  takes: the WebUI (browser preview) was open during these short takes and nobody had it open during A0 and A1, and the
  takes were short and started soon after a reboot. One of them overlapped with a read-only ssh command of mine (journal
  query), so it is not a clean sample. Log cannot be the cause (the earlier short takes had no Log).
- Not yet known: the two-take test (a 60 s take with every WebUI tab closed, then the same take with the WebUI open and left
  alone) separates the browser preview from the rest; a take during `top -H` would show which thread competes.
- Confirmed by: Patrik, reported "dropped frames after 3 seconds" and asked for the findings to be documented.
- Tutorial: none.

## 2026-10-31: the CM5 RTC exists and reads correctly, yet every boot started at an old fixed time

- Tested: `timedatectl`, `/sys/class/rtc/rtc0` and `sudo hwclock -r` on Patrik's Pi (CM5), NTP active.
- Seen: `rtc0` is `rpi-rtc`; RTC time equals the system time (21:22:51 UTC, `hwclock -r` 22:22:51 +01:00), System clock
  synchronized: yes; `charging_voltage` 0 (no trickle charge, as for a primary cell). The journal's boot list shows every boot
  of the day starting at `Thu 2026-10-29 22:37:32` and the clock stepping forward later (NTP).
- Why: inference, not measured: the RTC is not supplying the boot clock (no battery on the RTC pins, or the OS does not read
  it early). Core's "Apply Date & Time" (`syncHardwareClockIfAvailable` in `ApertarCoreApp.cpp`) sets the system clock with
  `timedatectl` and then runs `sudo -n hwclock --systohc --utc` only if an RTC device exists; an error such as a missing clock
  is swallowed and reported as success; Core never reads the RTC. Effect: until NTP answers, clip folder names, file times and
  Time-of-Day timecode carry a wrong date (the clips of the day are named `26-10-29` and `26-10-30` out of order).
- Not yet known: whether the RTC keeps time across a full power-off (power off, wait, power on, read the clock before NTP:
  `journalctl -k -b | grep -iE "rtc|setting system clock"` and `hwclock -r`).
- Confirmed by: Patrik, ran the commands and asked for the findings to be documented.
- Tutorial: none.

## 2026-10-31: first run of the drop-frames build on the Pi: trim at mount, Log 16 to 12

- Tested: Core and UI `drop-frames` built on the Pi (Core 22:26, UI 22:28), helper and sudoers installed from the README block,
  `systemctl restart apertar-core apertar-ui-direct`.
- Worked: at startup Core trimmed the drive by itself: `ApertarCore media: trim /media/RAW reason=mount result=trimmed
  bytes=927240290304 ms=467` (927 GB in 0.47 s). The state fields `cdng_log*`, `buffer_*`, `media_trim_*` and
  `frame_buffer_bar_enabled` were present and `/api/buffer` answered. With Log on, the journal printed `CineMate Log 16->12
  mu=10000 black=3200 white=65520 footroom=32/487` and one DNG frame was 12,451,344 bytes against about 16.6 MB linear (25 %
  smaller). Not opened in Resolve yet.
- Not yet known: that the frame decodes to the right linear picture in Resolve; Log on SDR modes (packed or PiSP-compressed
  raw streams record linear and the state says so); the buffer switch (`ram`) and the safety stop on the Pi.
- Confirmed by: Patrik, restarted the services and recorded the take.
- Tutorial: none.

## 2026-10-31: the ladder showed "max 30 fps" for 4K SDR; the sensor probe says 60

- Tested: `list_sensor_modes` and `get_mode_ladder` on the Pi (Core drop-frames build of 22:54), nothing recording.
- Seen: the probe lists 3840x2160 SRGGB10 and SRGGB12 at `max_fps` 60.0 (crops 62.85 to 85.66; Clear HDR 12-bit 30; Clear HDR 16-bit
  3840x2200 30), but the ladder's pool entries "4K SDR 10-bit" and "4K SDR 12-bit" had `mode_ceiling` 30 and ceilings 30 in every
  compression (the WebUI card said "max 30 fps"). Right now (Clear HDR 16-bit, ladder on) `fps_max` was 27.
- Why: read from the code: `tableMaximumFpsForResolution` ends its IMX585 4K branch with `return clearHdr && !sensorLimitKnown ? 25.0 : 30.0;`,
  which gives 30 for SDR as well (the comment above it is about Clear HDR), and `maximumSupportedFpsForResolution` returned
  `min(table, probed)`. Fixed on the branch: the probe is authoritative, the table is the fallback (`APERTAR_FPS_LIMIT=table` restores the
  old rule); the 25 fps limit of 16-bit Clear HDR is a named back-end cap; lossless JPEG keeps its encoder limit.
- Not yet known: the ladder's new ceilings and a 60 fps SDR 4K take on the Pi. 4K 12-bit at 60 fps is about 745 MB/s uncompressed, more than
  this drive sustained in the tests, so the practical value is the operator's choice per rung (storage and build), not Core's.
- Confirmed by: Patrik, saw "max 30 fps" on the ladder card, asked whether it was right and asked for the fps max to be read from the sensor.
- Tutorial: none.

## 2026-11-01: storage pre-roll at the sensor maximum: 4K 12-bit lossless measured 60.0 fps, 115 frames, 688 MB

- Tested: Pi 5, Core and UI `drop-frames` (Core `d44b177` build), 4K 12-bit SDR cDNG lossless, `storage_preroll` (manual) after Core start.
- Worked: `storage_preroll_last` = `ok: 2.0 s at 60 fps (measured 60.0), 115 frames, 0.7 GB written and deleted`. The fps is measured from the
  sensor timestamps, not taken from the request: 60.0 fps, 115 frames, 688 MB, clip deleted afterwards.
- Did not work: the first attempt set the frame rate with `applyControls` only. The log said 30 fps, the sensor stayed at about 24 actual fps.
- Why: a controls-only fps change does not reach the sensor at once; libcamera keeps the old frame duration for a while. Fix in
  `CameraSession::setPrerollFps` (pins `FrameDurationLimits {period, period}` on every request) and `waitForFramePeriod` (waits up to 1 s until a
  frame arrives at the new period) before the take starts.
- Lesson: **a controls-only fps change does not reach the sensor immediately: pin the duration and wait for the period, and measure fps from the
  sensor timestamps, never from the request.**
- Not yet known: whether a pre-roll warms the drive (the A/B in `working/drop-frames/README.md` step 0b); a 60 fps long take.
- Confirmed by: the owner, a take on the camera and the state value above.
- Tutorial: none.

## 2026-11-01: Log cannot be applied in SDR lossless: the raw stream is PiSP COMP1

- Tested: Pi 5, 4K SDR 12-bit and 10-bit, Lossless JPEG, Log on (`drop-frames` build); the journal and `cdng_log_applied`.
- Seen: `CineMate Log: pisp_comp1 raw stream cannot be mapped on the copy worker, recording linear`; `cdng_log_applied` false; the files are linear.
- Why: in SDR with Lossless JPEG the raw stream is PiSP COMP1 (compressed, lossy, steps of 16 codes or more; `working/research-30fps/q7-cinemate.md`).
  `planCdngLog` maps only unpacked 2-byte streams, which only Clear HDR 16-bit gives. Read from the code, and the log line seen on the camera.
- Decision (the owner): keep COMP1 for SDR (8.3 MB against 16.6 MB per 4K frame; it is what makes 60 fps possible); do not build Log into the SDR
  lossless path (Log on an uncompressed SDR stream is about 10.4 MB per frame, more than Lossless JPEG's about 7.5 MB; estimates). The UI now says so.
- Also changed: the ladder editor says "Exact, smaller files" for lossless only in Clear HDR (SDR: "Smaller files (SDR is sensor-compressed)"); with the ladder
  off the global Compression setting rules. Open: an HDMI "· Log" that did not follow `cdng_log_applied` (root cause not found in the code; a re-emit of the
  settings event on change is the safety net, untested).
- Confirmed by: the owner, the log line and the decision.
- Tutorial: none.

## 2026-11-01: the first real safety stop on the camera: 1289 of 1424 MiB, flush about 3 s

- Tested: Pi 5, Core `drop-frames` with `buffer=ram`, 4K lossless, a take that filled the write buffer; the pill and the journal.
- Worked: the safety stop fired at 01:00:35 with the buffer at 1289 of 1424 MiB (the 90 % threshold), the take ended cleanly and the queue drained in about 3 s.
- Then built (read from code, untested on the camera): the pill leaves REC at the stop and is READY green while the buffer empties (also with the bar option off); pressing record during the flush discards the queued frames and starts at once (`abortSafetyStopFlush`, `buffer_flush_discarded`, `discarded_on_stop`, a toast). Decision (the owner): discard, the old clip is cut short, written frames stay.
- Confirmed by: the owner, a take on the camera (the journal line at 01:00:35).
- Tutorial: none.

## 2026-11-01: forensics of the 2026-10-28 shooting day: which clips have a Core log, and which do not

- Tested: the Pi's journal against the clips on the SEAGATE disk (`2026-10-28 NORDKAPAREN telefonbojen/RAW`, 38 clips), per-clip tags read from the DNGs (`clips-vs-logs-2026-10-28.csv`).
- Seen: the Pi's journal only goes back to 2026-10-28 20:31 (journald is persistent, 200 MB; older boots were vacuumed). So the night shoot (clips C0001 to C0029, DNG capture times 01:40 to 03:20) and C0030 to C0032 (19:08 to 19:39) have no Core log. Of the 38 clips on the disk only the 4 H.264 clips and C0033 / C0034 match the journal.
- Clip NAMES repeat across cards: the counter restarts when the card is cleared, so the Pi's own C0022 / C0025 / C0026 test takes of 21:17 to 22:52 are other footage than the disk's C0022 / C0025 / C0026. Match by capture time, never by name.
- What can still be recovered per clip: the DNG tags (the CSV above), `fps-ramp.txt` (only C0030, C0031, C0032 and C0034), the ZOOM audio.
- Lesson: **keep the journal that covers a shooting day (copy it off, or raise the journald limit) before the next card is cleared.**
- Confirmed by: the owner, read from the journal and the disk (not re-run since).
- Tutorial: none.

## 2026-11-01: how to check a clip for dropped frames from its DNGs and WAV alone

- Tested: `cDNG_26-10-27_C0001`: 920 frames and a WAV, no Core log.
- Method: count the frames in each wall-clock second with `ExifIFD:DateTimeOriginal`. The DNG stamps each frame with the wall clock computed from the sensor timestamp (`wallClockForSensorTimestamp` in `CameraController.cpp`), so exactly fps frames in every FULL second means no drop (the first and last second are partial). Also compare frames / fps with the WAV duration.
- Not usable: `IFD0:DateTimeOriginal` (the take start, the same in every frame) and `TimeCodes` (a running frame count, which cannot show a gap).
- Result: 36 full seconds of exactly 25 frames, partial seconds of 2 and 18 frames, WAV 36.80 s = 920 / 25: no drops.
- Not yet run over all clips (offered).
- Confirmed by: the owner, the numbers above.
- Tutorial: none.

## 2026-11-01: imx585 `cinemate-port` `cd548ef` on the Pi: the new mode tables load and Core runs on them
- Tested: CM5, kernel 6.12.75+rpt-rpi-2712, IMX585 colour on cam0 at `link-frequency=891000000`; driver `24172e6` → `cd548ef` (`./setup.sh`, DKMS 0.0.1), Core `drop-frames` `4b2eeac` (before the new-mode work), reboot.
- Worked: probe reads the overlay (891 MHz, 4 lanes, CCMP default-on for colour); Core probed 187 sensor modes in about 0.4 s (libcamera 5.59 → 5.98 s) and reached `ready`, no configure refusals; 3840x2072 and 1920x1036 (the 1.85:1 crops of Core `900d282`) are among them at 10 and 12 bit. 891 MHz is still in the driver's link table, so config.txt needed no change.
- Did not work: n/a. One driver audit warning: `supported_modes[5] and [67] both advertise 3840x2072` (`dev_warn`, `imx585.c` table audit); V4L2 lists the size twice and libcamera takes the first. Left for the owner to decide (driver tables are not changed from Core work).
- Why: `/boot/overlays` is a symlink to `firmware/overlays` on this image, so `dkms.postinst` installing to `/boot/overlays/` already reaches the firmware's folder (the handoff's packaging worry does not apply here). DKMS `PACKAGE_VERSION` stays 0.0.1: tell builds apart by `modinfo` srcversion (`29403D42A3919123B7FA091` now, `C7771CBE2AC6D72E964F0C2` before).
- Confirmed by: Patrik, ran `setup.sh` and rebooted; dmesg, the Core journal and `get_state` (`ready`) read by Claude. No takes yet.
- Tutorial: none

## 2026-11-01: the running touch UI costs about 7 % of frames at capture; A0 was clean with it running (regression)

- Tested: Core `drop-frames` `4b2eeac`, UI `drop-frames` `41ff827`, Pi up 10 min, drive trimmed at mount and after the
  pre-roll's delete (`media: trim ... result=trimmed`), `buffer=ram`, env `APERTAR_RAW_CAMERA_BUFFERS=8`. Three 60 s takes,
  4K 25 fps Clear HDR 16-bit uncompressed cDNG, Log off, ladder off for the test, driven over the socket (`core.py
  record_start/record_stop`), no other ssh traffic during a take. WebUI clients counted with `ss` on `:8000`.
- Seen:

  | Take | Touch UI | WebUI | Written / 1500 | `dropped_gap_estimate` |
  | --- | --- | --- | --- | --- |
  | 19:09 | running | closed | 1389 | 104 (6.9 %) |
  | 19:11 | running (restarted 3 to 5 s in) | open, one tab | 1357 | 136 (9.1 %) |
  | 19:13 | stopped | closed | 1500 | 0, no `drop[...]` line |

  All three: `dropped_queue_full=0`, `peak_queue=2/12`, no write failure, stop sync 20 to 22 ms. Every gap is one missing
  frame (`dt_us` about 80 000 at a 40 000 nominal), about 1.7 to 2.3 a second, steady from second 3 to 5 to the end. The
  start-up pre-roll showed the same shortfall (60 requested, 56.8 measured).
- Why: the touch UI running is the main cause; the WebUI preview adds about a third more. The writers and the drive are
  clean. The 10-minute A0 take (2026-10-30, Core `a40112a`) lost 0 of 15001 with the touch UI running (started 2026-10-30
  01:04:19, A0 at 08:30), so this is a regression since then, in the UI (8 commits since `ea44bd7`) or in what Core sends
  it (preview feed, `buffer` events, settings re-emits): not yet split. It replaces the reading of the 2026-10-31 entry
  ("short takes lose a few frames"): it is a steady loss through the whole take, not a start-up effect.
- Not yet known: which side changed (one take with the A0-era UI `ea44bd7` on today's Core splits it); the mechanism.
- Confirmed by: Patrik ("touch ui was running for a0"; confirmed the reading).
- Tutorial: none.

## 2026-11-01: the dropped-frames chip shows the number (Core `64bbbaa`, UI `68e1a41`)

- Tested: Core `drop-frames` `64bbbaa` (on `dd00206`), UI `68e1a41`, both restarted 19:43. One 20 s take, 4K 25 fps Clear HDR
  16-bit uncompressed, ladder off for the take, touch UI running, WebUI closed, no build on the Pi.
- Worked: `recording_dropped_frames` 3 at 10 s, 18 after the stop (kept after the take); journal `dropped_gap_estimate=18`,
  `dropped_queue_full=0`, `dropped_copy_slot=0`; 478 written. The chip on the HDMI screen counted up and showed the number.
- Did not work: n/a. The first UI build failed on an ambiguous `qBound<qint64>` (Qt 6 on the Pi); `std::clamp` fixed it,
  folded into the feature commit.
- Seen in passing: 18 in 20 s is 3.6 %, against about 7 % in the 60 s takes on `4b2eeac`; one short take, not a finding.
- Confirmed by: Patrik ("numbers work").
- Tutorial: none.

## 2026-11-01: capture losses need the touch UI drawing AND a high data rate; not the disk, the HDR log, scheduling or the scan-out

- Tested: Core `drop-frames` `64bbbaa`, UI `68e1a41`, drive trimmed, WebUI closed, no build on the Pi (checked before and
  after each take), 60 s takes over the socket. HDMI 1920x1080@60 (XR24), preview stream 1280x720 YUV420.
- Seen (lost = `dropped_gap_estimate`; all `dropped_queue_full=0`, queue peak 2/12 unless noted):

  | Touch UI | Mode | Data rate | Lost |
  | --- | --- | --- | --- |
  | running | 4K Clear HDR 16, 25 fps | ~415 MB/s | 113 (7.5 %); with the HDMI cable out 77 (5.3 %, the UI kept drawing: CPU 11.5 % either way) |
  | running, camera thread `SCHED_FIFO` 40 (`APERTAR_RT_CAPTURE_PRIORITY`, `LimitRTPRIO=80`) | 4K Clear HDR 16, 25 fps | ~415 MB/s | 92 (6.1 %): no effect |
  | **frozen** (`SIGSTOP` 3 s into the take, 50 s) | 4K Clear HDR 16, 25 fps | ~415 MB/s | **1** in the 50 s |
  | running | 4K Clear HDR 16, **12.5 fps** | ~210 MB/s | 0 |
  | running | **1920x1080** Clear HDR 16, 25 fps | ~104 MB/s | 0 |
  | running | 4K SDR 12 uncompressed, 50 fps | ~620 MB/s | 554 (18.5 %), disk kept up (peak 16 frames) |
  | stopped | 4K SDR 12 uncompressed, 50 fps | ~620 MB/s | 7, but the RAM buffer grew ~67 MiB/s and the safety stop ended the take at ~22 s (1114 frames) |

  `CameraManager` (libcamera's completion thread) is ~40 % of a core with the UI running or stopped. The libcamera "No
  HDR algorithm" per-frame warning is silenced (`LIBCAMERA_LOG_LEVELS=IPARPI:ERROR`); the journal got 10 lines in a 60 s
  take. The CFE logs "DPHY: Datarate 1782 Mbps out of range" at each stream start (891 MHz link above the RP1 PHY's range):
  not the cause here (clean with the UI stopped and at 1080p).
- Why: the losses need the UI's drawing/CPU work (frozen UI: clean; scan-out of the frozen frame continued) together with
  a high raw data rate (half the rate or a quarter of the frame size: clean). Probable mechanism: memory-bandwidth or
  interconnect contention between the UI's 60 Hz redraws and the capture path; not established. Not the disk, the log,
  the UI's state poll (30 s), the camera thread's CPU or its scheduling, or the scan-out. The drive sustains about
  550 MB/s here (derived from the buffer growth, probable), so 4K SDR 50 fps uncompressed is over the drive regardless.
- Side finding (probable): freezing the UI BEFORE `record_start` hung the start at the audio open (the UI holds the shared
  audio input for its meter): no `audio capture` line, a clip folder with 0 DNGs, Core idle and healthy after the UI resumed.
- Not yet known: whether a 30 Hz UI (`QT_QPA_EGLFS_SWAPINTERVAL=2`) removes the losses; which part of a redraw costs.
- Targets (Patrik, 2026-11-01): 4K Clear HDR 16-bit at 25 fps first; 4K SDR 12-bit at 33 fps.
- Confirmed by: Patrik ("ok" to the readings).
- Tutorial: none.

## 2026-11-01: the losses follow the touch UI's GPU preview work, mostly focus peaking; what helped and what did not

- Tested: Core `drop-frames` `64bbbaa` (Core restarted between some runs), UI `drop-frames` `c234d77` to `4724007` with A/B
  environment switches on `apertar-ui-direct` (`/run` drop-ins), 60 s takes over the socket, 4K Clear HDR 16-bit
  uncompressed 25 fps, ladder off for the take, WebUI closed and no build on the Pi (checked before and after each take),
  HDMI 1920x1080@60. UI CPU from `pidstat` during the take.
- Seen (lost = `dropped_gap_estimate`; all `dropped_queue_full=0`, queue peak 2/12):

  | UI setting during the take | Peaking / zebra | UI CPU | Lost |
  | --- | --- | --- | --- |
  | unchanged | on / on | 12 % | 6-10 % (several takes) |
  | unchanged | **on / off** | 13 % | 156 (10.4 %) |
  | unchanged | off / off | 12 % | 25 (1.7 %) |
  | unchanged, audio meter off | on / on | 13 % | 133 (8.9 %) |
  | `QT_QPA_EGLFS_SWAPINTERVAL=2` and `=4` | on / on | 12 % | 130, 95: no effect (eglfs_kms ignores it here) |
  | `APERTAR_UI_PREVIEW_RECORDING_FPS=12` (preview 12/s while recording) | on / on | 9.1 % | 43 (2.9 %) |
  | `APERTAR_UI_PREVIEW_RECORDING_FPS=0` (preview held while recording) | on / on | 4.7 % | **0** (1498 written) |
  | `APERTAR_PREVIEW_PEAKING=fast` (edge from the Y plane, fewer fetches) | on / on | 12 % | 132 (8.8 %): no gain |
  | `fast` + `APERTAR_PREVIEW_DIRECT=1` (no display-size FBO + blit) | on / on | 13 % | 81 (5.4 %): **no-op, read as spread** (correction, same day: with `hdmi_external_only=true` the main window is hidden and the HDMI picture comes from the external-monitor window, whose renderer already draws straight into the window) |
  | `APERTAR_PREVIEW_PEAKING=cpu` (edge mask on the CPU, shader reads it) | on / on | 19.6 % | **58 (3.9 %)**; peaking looks the same |
  | Core `APERTAR_RAW_CAMERA_BUFFERS=12` (UI unchanged) | on / on | - | 158 (10.5 %): no effect |

  Qt render timing (`QSG_RENDER_TIMING=1`, 20 s each, not counted for losses): the UI redraws about 30 times a second;
  aids on: frame 13.6 ms mean, swap 8.7 ms mean / 32 ms p95, 186 of 582 frames >= 20 ms; aids off: 9.7 ms, swap
  6.3 / 29 ms, 96 of 612 frames >= 20 ms.
- Why: the capture losses follow the GPU work of the touch UI's live preview, and focus peaking is most of it (zebra is
  close to free). Less GPU work per camera frame helps in proportion; fewer camera buffers are not the cause (12 changed
  nothing). Probable mechanism: memory-bus contention between the GPU and the capture path; not established. Upstream
  Apertar draws peaking the same way (shader step 1/1920 x 1/1080 on Core's 1280x720 preview, `kPreviewWidth/Height`).
  CineMate shows its preview on a DRM display plane with no GPU per frame (rpicam-apps DRM preview); its capture path
  (two copies, buffered writes) is otherwise the same as Core's.
- Not yet known: the DRM-plane preview (`APERTAR_PREVIEW_PLANE`, being written); whether CPU peaking plus the plane reaches 0.
- Confirmed by: Patrik ("put the results in the hardware log"; peaking with the CPU mask "looks the same").
- Tutorial: none.
