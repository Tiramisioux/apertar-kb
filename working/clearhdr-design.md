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
