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

