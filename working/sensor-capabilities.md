# Sensor capabilities at startup (design draft)

Status: **draft 2026-10-26**, asked for by Patrik ("load the capabilities of the sensor at startup, like Cinemate", for the fps limits and so the user can turn crop modes on and off). Nothing implemented. Overlaps T19 (`list_sensor_modes`), which is step A below.

## Why

Core, the touch UI and the WebUI each keep their own hard-coded mode and fps tables (`isImx585Raw12CropResolution`, `sensorModeForRequestedResolution`, `maximumSupportedFpsForResolution` in `CameraController.cpp`; `CameraPage.qml`, `SettingsPage.qml`, WebUI JS). They go wrong when the link frequency, RP1 clock or driver changes. Example (confirmed 2026-10-26): Clear HDR 16-bit can run 30 fps on this image, but Core clamps it to 25.

## How Cinemate does it (read from public source, 2026-10-26)

| Step | Where | What |
| --- | --- | --- |
| Probe at startup, per session, no cache across boots | cinemate `src/module/sensor_detect.py` `detect_camera_model` | runs `cinepi-raw --list-cameras` twice: plain (SDR) and `--hdr sensor` (Clear HDR); kills stale cinepi-raw first (needs the camera) |
| Pixel-rate ceiling | same, `_list_cameras` | passes `--max-pixel-rate <RP1 regime>` -> env `LIBCAMERA_RPI_MAX_PIXEL_RATE` (cinepi-raw `core/options.cpp:246`) |
| Per mode | cinepi-raw `core/options.cpp` `print_modes` | `acquire()`, `generateConfiguration({Raw})`, for every pixel format x size: `sensorConfig` (outputSize, bitDepth), `validate()`, `configure()`, fps = 1e6 / `FrameDurationLimits.min`, crop = `ScalerCropMaximum`, plus driver per-mode metadata (`read_driver_mode_metadata`) |
| Clear HDR state | same, `set_subdev_hdr_ctrl` | `V4L2_CID_WIDE_DYNAMIC_RANGE=1` on whichever `/dev/v4l-subdevN` has it, **re-create the CameraManager** (libcamera caches the sensor's formats), probe again, set WDR back to 0 |
| Menus | `sensor_detect.py` + `settings.jsonc` | whitelists (bit depths, crop factors, Clear HDR, `enabled_modes`) filter the table; survivors are numbered; numbers are not fixed |

Pitfall Cinemate hit (its `_test/test_clearhdr_16bit_modes_survive_the_probe.py`): its text parser dropped every 16-bit line. An in-process probe in Core has no text parsing, so it does not apply.

## Proposal for Core

| Step | What | Gives |
| --- | --- | --- |
| A | At the first `CameraSession::start()`, before the real configure: for WDR 0 (and 1 if the sensor has the control), new CameraManager, acquire, every format x size -> `configure()` -> `SensorModeInfo{format, bitDepth, packing, size, clearHdr, maxFps, crop}`. Keep for the process lifetime. Log one line per mode. `list_sensor_modes` command | the truth, visible |
| B | fps clamp = probed max fps of the mode Core picks; the hard-coded table stays as fallback. Safety net: clamp at configure time to `camera_->controls()` `FrameDurationLimits.min` | 30 fps Clear HDR here, 25 at 720 MHz, automatically |
| C | WebUI and touch UI build resolution / crop / fps menus from the list; a user whitelist (`enabled_modes`) chooses which crop modes are offered | crop modes the user can turn on |

Already in Core: the WDR write + read-back (`CameraController.cpp:5331`), a new CameraManager per `start()` (`:5481`).

## Open before building

- Probe time: ~20 sizes x 2 formats x 2 WDR states of `configure()`. Measure; if it is seconds, probe once and keep it.
- Does `FrameDurationLimits.min` after `configure()` include this libcamera's RP1 cap (`PiSP pixel-rate cap = 646.667 Mpix/s`)? Testable here.
- Crop rectangles: T19 notes this driver reports no `ScalerCropMaximum` crop per mode; Cinemate reads driver metadata. What the `apertar` driver exposes is unchecked.
- Questions for Cinemate (below).

## Question for Cinemate (to send)

Context: Apertar-Core on Pi 5, IMX585 (`apertar` driver branch, link 891 MHz, `rp1-clk-333mhz`), libcamera `v0.7.1+qbcfork.20260522`. We want to copy CineMate's startup sensor probe in-process in C++, and we are chasing intermittent 16-bit Clear HDR frame drops.

1. How long do the two `--list-cameras` probes take on IMX585, and does CineMate run them on every boot?
2. Does `FrameDurationLimits.min` read after `configure()` already include the `LIBCAMERA_RPI_MAX_PIXEL_RATE` bound (your hardware gate G2), or does CineMate apply the ceiling itself? Did the probed fps match the measured fps in `docs/sensors.md` (e.g. 4K ClearHDR 16-bit 21.99 / 30.00)?
3. `read_driver_mode_metadata` (`core/driver_mode_metadata.hpp`): what does the driver expose per mode, through which interface, from which driver commit? Is it needed to offer crop modes correctly, or is `ScalerCropMaximum` enough?
4. After the probe sets `wide_dynamic_range` back to 0, did any sensor state left by the probe (WDR, exposure, gain, mode) ever break the next real start?
5. 16-bit Clear HDR at 25 fps with 4 raw buffers from the system heap: some 10 s takes are clean, others lose ~30 frames as single-frame CFE gaps every 7-10 frames for the whole take. Did CineMate see this pattern? Is that what made you choose 8-10 raw buffers, or was it something else (preview buffer count, IPA latency, BE time)?
