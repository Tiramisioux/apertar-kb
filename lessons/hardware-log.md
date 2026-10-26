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
