# Clear HDR: design decision (T16)

Status: **decided 2026-10-25 by Patrik**. Supersedes the "Clear HDR = 16-bit, one state" rule in the T16 workbook (Step 4 and the intro).

## Goal

Clear HDR works in **both** its modes, and the user picks the mode in the **WebUI** (and touch UI):

| Mode | Sensor format | Sensor size | Storage |
| --- | --- | --- | --- |
| Clear HDR 12-bit (companded) | `SRGGB12_1X12` | 3840x2160 | 12-bit DNG/MLV |
| Clear HDR 16-bit (linear) | `SRGGB16_1X16` | **3840x2200** (20 OB rows on top, 20 margin rows below) | 16-bit DNG/MLV, cropped to 3840x2160 |

So `clear_hdr` (on/off) stays one setting, and `raw_bit_depth` (12 or 16) is the user's second choice while it is on. Core must **not** force 16 when Clear HDR turns on (this replaces Step 4 edit 2 of the workbook).

## Why the workbook rule was wrong for this driver

**Confirmed 2026-10-25** (`v4l2-ctl -d /dev/v4l-subdev2 --list-subdev-framesizes`, WDR=1): the `apertar` branch driver (`e5b74d3`) offers `SRGGB12` at 3840x2160 and `SRGGB16` at 3840x2200. The workbook assumed only 16-bit exists with WDR on. With only Step 3 in, a normal 12-bit 4K request therefore succeeds in the companded mode.

## What the system has to handle

1. **Different readout size for 16-bit.** 3840x2200 vs 3840x2160: `sensorModeForRequestedResolution()` (Imx585 block) picks 3840x2200 when `rawBitDepth == 16`; `shouldUseRequestedActiveRawCrop()` returns true for Imx585 at 16-bit so the 20 OB rows are cropped (workbook Step 4 edits 6 and 8, unchanged).
2. **Frame rate.** Both Clear HDR modes halve the 4K rate (25 fps at the default link); `maximumSupportedFpsForResolution()` must clamp for Clear HDR at 12 **and** 16 bit.
3. **Legal depths.** `supportedRawBitDepthForSensor()`: with Clear HDR on, 12 and 16 are legal; with it off, 10 and 12 (16 only with Clear HDR).
4. **12-bit companded needs linearising.** **Probable** (not yet confirmed): the companded mode gave a very dark preview on 2026-10-25 because Core reads its values as linear. Showing it correctly needs the CCMP linearisation table (the workbook's "later project"). Until then the 12-bit Clear HDR option is either marked experimental or hidden in the UI.
5. **UI.** The bit-depth picker offers 12-bit and 16-bit while Clear HDR is on (workbook Step 7 changes: it no longer jumps to 16-bit by itself).

## Open

- Does 12-bit Clear HDR look right with blend 5 and gain adder 1 (Step 5), or is the linearisation table unavoidable? Settle on the bench after Step 5.

## Decisions added 2026-10-25 (during T16 Step 4)

- **16-bit is 4K only.** The only 16-bit sensor mode is 3840x2200. `sanitizeSettingsForSensor` sets the resolution to 3840x2160 whenever an IMX585 runs at 16-bit; `isImx585HighResolutionAlias` counts 3840x2200 as 4K, so the encoders only ever see 3840x2160 (cropped from the 3840x2200 readout). 12-bit Clear HDR keeps every resolution. Core is the authority; the UI pickers should grey out sub-4K sizes at 16-bit (Step 7).
- **Frame rate.** `maximumSupportedFpsForResolution(..., clearHdr)` returns 25.0 for 4K with Clear HDR on, 30.0 off. 25 is the safe figure, **not yet measured**. The driver's probe table prints `mode 3840x2200 -> VMAX=2250 HMAX=550`; with VMAX doubled in Clear HDR that is 74.25e6 / (4500 x 550) = 30.0 fps. **Unconfirmed**: read the `dmesg` timing line while streaming in 16-bit and raise the clamp if it allows 30.
- **COMP1 at 16-bit.** `CdngEncoder::preparePispCompressedLayout` and `MlvEncoder::prepareRawLayout` keep Bits16 (unpacked, `width * 2` bytes per row) and decode via `CdngEncoder::decodePispRowToMsb16`. Unpacked 16-bit input already took a memcpy branch.
- **Open:** black level at 16-bit (3201 from `BlackLevel.hpp:17` vs 3200); lossy cDNG with a 16-bit source (it quantises to 12-bit: refuse or document).

## Open problem 2026-10-25: 16-bit Clear HDR delivers only the black pedestal

**Confirmed on the Pi** (raw DNG samples, clips C0011-C0016): every 16-bit frame is noise around the black level (median ~3222, max ~3330, white 65535) on a lit scene. Not the preview or ISP.

**Confirmed: the sensor's exposure and gain are stuck in Clear HDR.** With `set_shutter_us 20000` and `set_iso 400`: SDR gives `exposure=2700` (20 ms at 7.4 us/line), `analogue_gain=60`; Clear HDR gives `exposure=135`, `analogue_gain=0`. Changing Core's shutter (200 / 10000 / 20000 / 30000 us) and ISO (200 / 1600) leaves the HDR registers at 135 and 0. Writing `exposure=2700,analogue_gain=40` with `v4l2-ctl` is overwritten at once. The driver's handler (`imx585.c:1612`) writes SHR = VMAX - exposure with no scaling, so the values come from libcamera's IPA (Tiramisioux fork `v0.7.1+qbcfork.20260522`) or from what Core sends. Journal: `pisp.cpp:1563 The sensor is configured for a 16-bit output, statistics will not be correct. You must use manual camera settings.`

**Ruled out:** WDR write (reads back 1); threshold order (4095/0 and 3000/500 both pedestal); blend 5; gain adder 1 and 2 (adder 2 only raised the noise); the shutter "kick" (the registers never moved); encoder speed (same frames dropped uncompressed); `rp1-cfe DPHY Datarate 1782 Mbps out of range` (logged on every start, SDR too).

**Probable:** exposure ~1/20 of the request at gain 0 is too dark to rise above the noise, matching the pedestal.

**Also seen, unexplained:** only 4 frames (nos. 0, 14, 15, 19) are written per 2 s clip, every time; preview crop height is 2120 where 2160 is expected.

**Next (Mac side, has the Cinemate source):** find how cinepi-raw sets ExposureTime / AnalogueGain / AeEnable in 16-bit Clear HDR (`cinepi_controller.cpp`), and what the libcamera fork's imx585 helper and ClearHDR code do with them; compare with what Core sends in `CameraController.cpp` (search `ExposureTime`, `AnalogueGain`, `AeEnable`). Bench option with Core stopped: `rpicam-raw` at 16-bit with `--shutter` and `--gain` set.


## SOLVED 2026-10-25: the black 16-bit frame was Core's tuning file, not Core's code

**Confirmed.** `/home/pi/Tuning-Files/defaults-pisp/imx585.json` (the file Core selects, 3 Oct) contains an `rpi.hdr` algorithm that libcamera's default `/usr/local/share/libcamera/ipa/rpi/pisp/imx585.json` (23 Aug) does not have. With it present, the IPA pins the sensor to exposure 135 / gain 0 in Clear HDR whatever Core sends, giving the flat black-level pedestal.

Evidence chain:
- Bench with Core stopped: `rpicam-raw --mode 3840:2200:16:U --shutter 20000 --gain 4` gives a real image with libcamera's default tuning (sensor registers follow: 2700 / 40) and a pedestal-only frame with `--tuning-file /home/pi/Tuning-Files/defaults-pisp/imx585.json`.
- Not the cause (each tried, each left the registers at 135 / 0): thresholds, blend, gain adder, shutter "kick", per-request exposure/gain, and dropping any or all of AWB / metering / EV / frame duration / scaler crop / colour-profile controls.
- Fix test: a copy of Core's file with the `rpi.hdr` entry removed, selected with `set_tuning_file`: registers 2700 / 60 in Clear HDR 16-bit and raw samples median 6469, p99 16134, ~3280 distinct values (clip C0017).

**Open:** (1) the permanent fix: remove `rpi.hdr` from the shipped tuning, or ship a Clear HDR tuning and let Core pick it when `clear_hdr` is on (SDR effect of removing it is unmeasured); (2) only 4 frames per 2 s clip (nos. 0, 14, 15, 19, `dropped_gap_estimate` 16-18) still unexplained; (3) preview ScalerCrop height 2120 instead of 2160.
