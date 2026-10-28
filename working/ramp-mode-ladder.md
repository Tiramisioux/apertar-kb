# Speed ramp from the lowest fps to 50 fps, switching mode only at thresholds (assessment)

2026-10-27, cloud session (Claude Opus 5.5). Patrik's plan: "We will go from the lowest possible FPS up to 50 FPS, and we will switch resolution
when we reach the threshold values, aiming at keeping the resolution throughout the FPS change." This note turns that into thresholds for the
IMX585 on Apertar and says what Core does at a threshold today. Builds on T31 (speed ramping, `working/ramp-answer.md` in the speed-ramping
package) and `working/research-30fps-answer.md`. Nothing here was run on the Pi. Labels: CONFIRMED / PROBABLE / UNCONFIRMED.

## 1. The ceilings (link 891 MHz, `rp1-clk-333mhz`)

| Mode family | Sizes | Sensor ceiling (Pi probe) | Core ceiling today | Label |
| --- | --- | --- | --- | --- |
| Clear HDR 16-bit | 3840x2200 (2160 active) | 30 | 30 (clean today: 25; 30 delivers ~28, see the 30 fps research) | CONFIRMED probe `working/sensor-capabilities.md:51`; Core `tableMaximumFpsForResolution`, `CameraController.cpp@f60e301` |
| Clear HDR 12-bit | 3840x2160 | 30 | 30 | same |
| SDR 10/12-bit 4K | 3840x2160 | **60** | **30** (the table returns 30 for 3840x2160 whether Clear HDR is on or not) | CONFIRMED probe and code |
| SDR 3840-wide crops | 3840x2076 … 3840x1504 (9 sizes) | 62.85-85.66 | 60 | CONFIRMED probe; `isImx585Raw12CropResolution@f60e301` |
| SDR 2x2 binned | 1920x1080 and 9 crops 1920x1038 … 1920x752 | 60-85.66 | 60 | same |

- **No Clear HDR mode exists above 4K full frame**, so none goes above 30 fps on this link (PROBABLE: the driver has 10 SDR sizes x 2 bit depths = 40 SDR
  modes, plus the 2 Clear HDR 4K modes = 42, exactly the Pi probe's count; `imx585-apertar/imx585.c:797-1160@98b9862`).
- **Lowest fps:** Core accepts any fps > 0 (`clampCaptureSettings`, `CameraController.cpp@f60e301`). The sensor's longest frame is VMAX 0xFFFFF
  (`imx585.c:110`): 74.25 MHz / (550 x 1,048,575) = **0.129 fps** at 4K, 0.194 fps for the binned modes (HMAX 366) (PROBABLE arithmetic; whether
  libcamera's IPA accepts a frame that long is UNCONFIRMED: `set_fps value=0.5` in preview settles it). With T31's stepper (one fps per step) a ramp
  from 1 to 50 fps is 49 steps.

## 2. Ladders that keep the resolution as long as possible

| Ladder | Switch points | Resolution kept? | What changes at the switch |
| --- | --- | --- | --- |
| **A. 4K SDR 12-bit the whole way** | none | **yes, 3840x2160 from the lowest fps to 50 (sensor up to 60)** | nothing. Needs Core's 4K table cap raised from 30 to the probed 60, and the storage and pipeline to carry 50 fps (§3) |
| B. Clear HDR 16-bit → 4K SDR 12-bit | at 25 (clean) or 30 (ceiling) | yes | dynamic range and bit depth: the look changes visibly at the switch |
| C. 4K SDR → 3840-wide crop | at 30 (Core today) or wherever 4K stops keeping up | width kept, height shrinks | aspect ratio, e.g. 3840x1608 = 2.39:1 (framing) |
| D. → 1920x1080 binned | at the 4K/crop ceiling | no (half resolution) | resolution; last resort |

Ladder A is the only one that keeps the resolution throughout, and it needs no mode switch during the take.

## 3. What 50 fps costs (PROBABLE arithmetic)

| Mode | DNG bytes/frame | at 25 fps | at 50 fps |
| --- | --- | --- | --- |
| 4K Clear HDR 16-bit | 16.59 MB | 415 MB/s | — (not possible) |
| 4K SDR 12-bit (DNG `BitsPerSample` 12, `CdngEncoder.cpp:1355@f60e301`) | 12.44 MB | 311 MB/s | **622 MB/s** |
| 3840x2076 12-bit | 11.96 MB | 299 MB/s | 598 MB/s |
| 3840x1608 12-bit | 9.26 MB | 232 MB/s | 463 MB/s |
| 1920x1080 12-bit | 3.11 MB | 78 MB/s | 156 MB/s |

Measured on this Pi's NVMe/exFAT (T22): `dd` with O_DIRECT 733-759 MB/s with 0 frame gaps, buffered 561 MB/s with gaps (CONFIRMED,
`lessons/hardware-log.md` 2026-10-26, T22 tutorial). So **4K at 50 fps needs T24 (O_DIRECT)**: buffered writes top out below 622 MB/s, and O_DIRECT
leaves ~15-18 % headroom. The pipeline side is unmeasured: 4K at 50 fps gives the PiSP back end 20 ms per frame. 12-bit SDR has no endian swap and no
software raw stats, and its TDN reference follows the CFE format (`pisp.cpp:1902-1905@6b0b49f`), so it is much lighter per frame than 16-bit Clear
HDR (PROBABLE). Preview at 50 fps settles it (§5).

## 4. What Core does at a threshold today

- **Resolution, Clear HDR and bit-depth changes are refused during a take** (CONFIRMED: "Resolution changes are blocked while recording.",
  "Clear HDR changes ...", "Raw bit depth changes ...", `CameraController.cpp:8050, 8489, 8453@f60e301`). With T31, `setFps` during a ramp take
  is clamped to the running mode's ceiling and the `ramp_fps` stepper stops with "fps ramp stopped: <x> fps is this mode's limit".
- A mode switch is a full camera reconfigure (stop, configure, reallocate raw buffers: 8 in Clear HDR, 4 otherwise, start). Cinemate measured
  such a stall at **~186 ms** (`cinepi-raw` `e74e3e4`, `working/cinemate-lessons.md:44`), i.e. ~6 frames at 30 fps and ~9 at 50. Core's own
  reconfigure time is UNCONFIRMED and probably longer (it reallocates more buffers).
- The DNG format changes at the switch (size, bit depth, black level, Clear HDR's linearisation table), so one DNG folder cannot hold both
  sides: editors expect one format per sequence. Cinemate ends the clip and starts a new clip folder and a new WAV at a mid-take reconfigure
  (`cinepi-raw/cinepi/cinepi_raw.cpp:68-76, 365-375@63a08d5`).

So ladders B-D need new Core work: at the threshold, close the clip (DNGs, WAV, `fps-ramp.txt`), reconfigure, open the next clip in the same
take, and keep T31's conform rules across the clips (every clip's `FrameRate` and RecRun timecode at the take's start rate, timecode continuing,
the lost frames written to the ramp log).

## 5. Measurements before building anything (read-only, or a one-line Core change for A)

1. **Is 4K SDR at 50 fps sustainable at all?** Raise Core's 4K SDR table cap to the probed value (one line in `tableMaximumFpsForResolution`), then
   preview at 50 and 60 fps 4K SDR 12-bit: delivered fps (`working/tools/ipa_rate.py`) and one `be_cycle.py` window. Prediction: 50.00 fps with
   back-end S2 ≤ 15 ms. Rules ladder A out: preview below 49.5 fps.
2. **Record 4K SDR 12-bit at 50 fps for 60 s**, once buffered and once after T24. Prediction: buffered loses frames, O_DIRECT clean. If O_DIRECT also
   loses frames with `peak_queue` filling, storage is the limit: use ladder C at a lower switch point.
3. **Time a mode switch** in preview: switch Clear HDR off and on and read the gap between the last frame before and the first frame after
   (`LIBCAMERA_LOG_LEVELS=RPI:0`, CFE dequeue lines). That is the frame cost of every threshold in ladders B-D.
4. **The lowest fps:** `set_fps value=1`, then `0.5`, in preview; read back `get_state` and the frame interval.
