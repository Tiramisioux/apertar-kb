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

## 2026-10-26: CFE pull test with the HAT slot bit (56d9137): detection works; re-insert breaks the card; stop waited 22.6 s

- Tested: Core `56d9137` (HAT slot bit, bounded dead-medium stop), persistent journal, card pulled three times idle (22:46:09,
  :25, :31) and re-inserted each time, then record (22:47:16), stop pressed during the take.
- Seen: every pull logged `media: state=removed ... nvme_state=- hat_card=out` within the 1 s watcher cycle without touching the
  device; every re-insert `state=mounted ... nvme_state=live hat_card=in`. But the card was unusable after re-insert:
  direct write `Input/output error`, `exFAT ... set read-only`, controller `dead` (dmesg 665 s, `lost async page write`).
  Record at 22:47:16 passed the gate; `drop[queue-full] queue=12/12` after 0.7 s; nothing written; at 22:47:40 the kernel
  failed the I/O: `write_failures=4`, `recorder stop time: 22.631s`, `Audio capture write failed`. The touch UI kept READY
  (it reads the mount table via QStorageInfo, not Core's `media_alive`).
- Why: **confirmed** the HAT bit sees pulls at once. **Confirmed** a Pi 5 cannot hot-plug the CFE NVMe: a re-inserted card needs
  a PCIe remove/rescan (remount) or a reboot. **Confirmed** the stop hang was writers stuck until the NVMe timeout (~24 s).
- Fix: `da48974` (pulled latch per mount id; write-stall detection in the take and in every stop). Touch UI: open (UI repo).
- Confirmed by: Core journal and dmesg on the Pi; Patrik's report on the UI.
- Tutorial: T28 5.2.

## 2026-10-26: CFE card pull and re-insert work end to end (Core da48974+227ea7b, UI 160898c+dc471c1); a stopped take is lost if pulled within ~30 s

- Tested: Pi 5 (4 GB), PCIe Gen 2, Core `cinemate-port` `227ea7b`, UI `cinemate-port` `dc471c1` (automounter installed to
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
  `ffb87db`, T30 `a99691e`, sync `0586273`, then `e2f55a2`), 4K Clear HDR 16-bit 25 fps uncompressed, `takes.sh 1 180`.
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

- Tested: Core `e2f55a2`, Gen 3, freshly formatted exFAT, 16-bit 4K25 uncompressed, ~3 min takes by Patrik.
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

- Tested: Core `775083f` (sync_file_range per DNG), Gen 3, `takes.sh 1 180` (12→16 reconfigure first), 16-bit 4K25.
- Writeback, syncfs off (drop-in): C0004 4494 frames, 0 queue drops, no capture gaps, peak 1/12, stop sync 62 ms.
  Writeback + syncfs 1 s: C0005 3701 written, **782 queue drops**, 12 capture gaps, peak 12/12, stop sync 181 ms.
- Why: **probable** that syncfs waits for all pages already in writeback and the DNG writers block behind it. Next:
  `77867e6` (fsync of the clip folder instead).
- Also: Core answers `record_start` in 0.24 s and emits its `recording` event; the touch UI's apparent delay during these
  tests is `takes.sh`'s 12→16 reconfigure (~11 s) before it records (**probable**; Patrik to check with his own press).
- Audio drift figure with T30's writer still varies take to take (+18, +15, +64, -139, +156 ppm): open.

## 2026-10-26: writeback + folder fsync is clean; the touch UI misses takes started elsewhere

- C0007 (Core `77867e6`: per-DNG `sync_file_range` + 1 s `fsync` of the clip folder; Gen 3; `takes.sh 1 180`): 4495 frames,
  0 missing, no capture gaps, queue peak 2/12, stop syncfs 59 ms, audio writer peak 9 KB.
- Patrik: the tally LED lit "a couple of seconds" before the touch UI showed recording. Cause (code, **confirmed**):
  `ApertarCoreApp::publishEvent` collects events raised during a command into that command's reply unless they are on its
  broadcast list, and `recording` was not, so only the sender heard it; the tally reacts to the same event inside Core
  (`handleTriggerEvent`). The touch UI then learned on its next `get_state` poll (`kSteadyStatePollIntervalMs` 30 s).
  Fix `a070e1b`. Upstream behaviour (**probable**: the list is unchanged from 1.6.0).

## 2026-10-26: pull with writeback + folder fsync: folder and names survive, files are 0 bytes

- Tested: Core `a070e1b` (writeback per DNG, 1 s folder fsync), take C0010 started 23:56:19.1, card pulled 23:56:21.28.
- Seen: automounter `card removed while mounted` + Core `recording failure ... media_removed` within 9 ms; `written=52`;
  `dead-medium stages raw_ms=20 audio_ms=1277`; re-insert remounted in 3.9 s. After: folder C0010 with 48 `.dng` names,
  **all 0 bytes**. C0008/C0009 (stopped normally just before) complete, WAV = frames.
- Why: **probable** that the data blocks reached the card (writeback started per file) but each file's exFAT entry (size,
  first cluster) was still dirty in memory; the folder fsync writes the folder, not the files' entries. Fix `6fee0e4`.
- Confirmed by: the card's contents after re-insert.

## 2026-10-26: pull mid-take with per-file fsync: all frames up to ~0.9 s before the pull are readable

- Tested: Core `6fee0e4` (writeback per DNG; 1 s sync thread fsyncs each finished DNG, then the folder), take C0011 (~11 s),
  card pulled 23:58:57.26.
- Seen: HAT `hat_card=out pulled=1` → `recording failure ... media_removed` 0.6 ms later; automounter `card removed` 10 ms
  later; `written=280`; `dead-medium stages raw_ms=78 audio_ms=608`; re-insert mounted 23:59:08.4. On the card: 281 files,
  **258 full frames (readable, band level steady, max step 0.078 %) and 23 empty** (the last 0.9 s). `audio_capture.raw`
  0 bytes, no WAV (skipped on a dead medium by design).
- Why: **confirmed** that fsyncing each finished file within a second keeps a pulled take readable to ~1 s before the pull.
  Audio raw fix `7a545d9` (fsync once a second); `working/tools/raw2wav.py` turns a recovered raw file into a WAV.
- Confirmed by: the card's contents after re-insert.

## 2026-10-27: pull mid-take keeps picture to ~0.8 s before the pull and all but the last moment of audio

- Tested: Core `7a545d9` (audio raw fsync once a second), take `cDNG_26-10-27_C0001`, pulled 5.4 s in (00:01:53.43).
- Seen: 102 readable DNGs (4.1 s, band level steady, max step 0.058 %) + 21 empty; `audio_capture.raw` 1 445 778 bytes =
  5.02 s s24 stereo 48 kHz, real signal in all 502 sampled 10 ms blocks (peak -44.7 dBFS); `raw2wav.py` made
  `cDNG_26-10-27_C0001.recovered.wav`. Stop: `dead-medium stages raw_ms=2 audio_ms=488`; remount 7.4 s after the pull.
- Why: **confirmed** that a pulled take now keeps its picture to within a second and its audio as raw PCM, recoverable to WAV.
- Confirmed by: the card's contents after re-insert.

## 2026-10-27: 3-minute take with per-file fsync: clean

- Core `7a545d9` (writeback per DNG; 1 s sync thread fsyncs each finished DNG, the folder; audio raw fsync), Gen 3, drive
  38 % full, `takes.sh 1 180`: `cDNG_26-10-27_C0002` 4494 frames, 0 missing, no capture gaps, peak 2/12, stop syncfs 59 ms,
  audio drift -20 ppm. **Confirmed**: the per-file sync costs no frames; with C0011 / 2026-10-27 C0001 a pulled take keeps all
  but its last second, audio included.

## 2026-10-27: T21 time-left estimate and T30's fitted drift on the Pi

- Tested: Core `6ae70b5` (restart 22:19:28), cDNG 12-bit lossless 4K25, 502 GB free.
- T21: `/api/state` `record_time_left_minutes` 36.7, `time_left_label` "cDNG 12-bit lossless estimate (bar: 2 h)",
  `time_left_percent` 30.6; by hand with the touch UI's model 8.69 MiB/frame → 36.7 min (old Core model: 24.9 min).
- T30 (`e9dd6b2`): 70 s take C0013 (socket start/stop, no reconfigure): 1748 frames clean; `audio clock:
  measured_drift_ppm=-15 points=6968 endpoint_ppm=-15 correction=none`. Media-tune helper: no call since the restart.
- HDMI (touch UI) 35 min vs WebUI 36 after the C0013 take: Core 35.96 min from 468 997 MiB free; the WebUI rounds,
  the touch UI truncates whole seconds. **Confirmed**: the two models agree.
- T20 pull while idle (Patrik, 22:24:37): automounter lazy-unmounts in 0.5 s, so Core reports `state=none` and the strip reads
  "No Media Mounted"; "Media Removed" shows only while a dead mount stays (e.g. a USB stick, which the automounter does not
  handle). Re-insert remounted at 22:24:47. Patrik: "yanking works fine".

## 2026-10-27: 16-bit time left: WebUI 37 min (right), HDMI 50 min (touch UI read 16-bit as 12)

- Tested: Core `6ae70b5`, cDNG 16-bit uncompressed Clear HDR 4K25, 997.6 GB free (Patrik's WebUI screenshot + HDMI).
- Core 37.7 min (16.8 MiB/frame; C0101's DNGs are ~17 MB). Touch UI `currentRawBitDepthNumber()` returned 12 for "16-bit"
  → 12.6 MiB/frame → 50.3 min. **Confirmed** by the arithmetic and the code. Fix UI `2d27c46`; rounding `87011d4`.
- After `87011d4` + `2d27c46` (Core and UI restarted 22:35): Core 37.8 min, WebUI and HDMI both 37 (Patrik: done).


## 2026-10-28: T31 speed ramping, first ramp take (1080p uncompressed, 25 → 50 → 25)

- Tested: Core `47d44ff` (T31 without the `ramp_fps` stepper; restart 19:06:45), IMX585 1920x1080 (2×2 binned), cDNG
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

- Tested: Core `28bd441`, driver `cinemate-port` `24172e6`, 4K Clear HDR 12-bit lossless, preview only; `set_iso` then
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

## 2026-10-28: Clear HDR holds ISO/WB and caps ISO (a89a5df), preview test

- Tested: Core `a89a5df` (restart 20:09:09), 4K uncompressed, preview only (`/tmp/hdr-hold-test.sh`), dark desk scene.
- SDR auto ISO + WB (code 60) → Clear HDR 12-bit: `iso_auto`/`wb_auto` false, `iso_auto_after_clear_hdr`/`wb_auto_after_clear_hdr`
  true, ISO held and capped to 720 (code 57), WB held at the measured 2815 K. `set_iso_auto`/`set_wb_auto` refused with the info
  message. `set_iso 1600`: 12-bit → 720 (code 57), 16-bit → 1585 (code 80); 3200 → 1585. A manual ISO in Clear HDR cleared the ISO
  flag, so SDR kept ISO 720 manual while WB went back to auto. Round trip with both auto: held in Clear HDR, auto again in SDR;
  flags persisted. **Confirmed.**
- Seen: while auto ISO runs, the state's `iso` is the stored value (720 after the round trip), not the live gain; request 16.

## 2026-10-28: H.264 on the IMX585 (Core 65b2bb2): 4K capture only, 30 fps cap, x264 has headroom

- `set_record_format h264`: capture stays 3840x2160 (a 1920x1080 `set_resolution` is ignored), output 1920x1080, libx264
  `tune=zerolatency`, `input=staged-yuv`. `set_fps` 50 or 60 → 30.
- 10 s takes: 25 fps 235/235 frames, 30 fps 294/294 (`ffprobe` 294, avg 30/1), `dropped_queue_full=0`, peak queue 1/6;
  Core 69-84 % of one core. **Confirmed**: the encoder is not the limit; Core's H.264 capture choice is.
- The H.264 MP4 and the ProRes MOV are video-only (one stream: `LibavH264EncoderPlugin.cpp:124`, `ProresEncoder.cpp:929`);
  audio is the clip folder's WAV, as for cDNG. Speed ramping in H.264 stays refused (Patrik): 25 → 30 is too little.

## 2026-10-28: experimental stretched WAV (78c980d), camera-wide switches, conform_fps

- Rubber Band: `rubberband-cli` 3.3.0 installed by Patrik (`apt update` first: the image has no apt lists). Click test
  (real 4 s → 4 s, 6 s → 8 s, `-D 12 --timemap`): output 12.0000 s, clicks 1.0 / 5.976 / 10.0002 s. Key frames are exact; inside a
  re-timed stretch Rubber Band smooths by ~25 ms; nothing accumulates. ffmpeg `rubberband`/`atempo` with `asendcmd`: 20-50 ms off
  per change, accumulating. A `0 0` map line makes Rubber Band warn about a NaN ratio (dropped in the follow-up commit).
- Core 78c980d (restart 20:54:18): `conform_fps` 25 by default, 24 accepted, 0 refused. Ramp, stretch and phase lock turned on in
  H.264 stay on after switching to cDNG (84081f7, a56eae7).
- `C0034` 1080p uncompressed 25 → 50 → 25 (set_fps steps): 909 DNGs = 36.36 s at 25; real-time WAV 25.809 s;
  `C0034_stretched.wav` 36.360 s, 48 kHz, written seconds after stop (50 key frames); `fps-ramp.txt` `applied_us` 5038579 for frame
  126 (= 5.04 s at 25). **Confirmed** length and pitch; how it sounds is for Patrik to judge.
