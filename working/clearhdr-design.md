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

## 12-bit Clear HDR linearisation (2026-10-25, uncommitted in Core)

Source: Mac-side answer from the Cinemate source (`cinepi-raw ccmp_lut.hpp`, commit `63a08d5`). Core now attaches a DNG LinearizationTable (4096 entries) to Clear HDR 12-bit frames: `src/cdng/CcmpLut.hpp`, wired in `metadataFromRequest`. **Confirmed on the Pi:** the DNG carries tag 50712 with 4096 entries (t[700]=700, t[1634]=23889, t[4095]=63265), BlackLevel 200 on all channels, WhiteLevel 63265; SDR and 16-bit DNGs carry no table. **Unconfirmed:** that the picture is now neutral (to be judged in a DNG converter). The blend-0 speckle from the Cinemate answer does not apply: Core writes blend 5 at every start.
Constants are only valid while the driver's gradient-compression controls stay at their defaults (500 / 11500 / 1/64 / 1/16); knee 1 uses Cinemate's measured 500.3389. MLV still has no table; lossy cDNG is refused for all Clear HDR; the live preview is untested.


## Correction 2026-10-25 22:05: no LinearizationTable; the 12-bit mode arrives linear

**Confirmed (bench `bench12.sh`, Core stopped, same scene):** the image's libcamera decompands the 12-bit CCMP stream in the CFE and delivers linear 16-bit samples, black ~3200: 12-bit mode median 6222 / p99 15730 / max 16662 vs 16-bit mode 6242 / 15941 / 16930. Its log line `ClearHDR 12-bit CCMP stats linearisation enabled` means exactly this (Cinemate's libcamera fork has no such line).
**Root cause of the purple 12-bit picture:** Core stored those samples as 12-bit through `Csi2RawConverter::packDng12Row`, which keeps `src & 0x0FFF`: values 3200-16662 wrapped. The LinearizationTable section above is superseded and the table code was removed (it would linearise already-linear data).
**Fix (uncommitted):** `storageRawBitDepthForSettings` returns 16 for any Clear HDR. Both Clear HDR sensor modes now write 16-bit DNGs: 12-bit mode 3840x2160 (CCMP at the sensor, no OB rows), 16-bit mode 3840x2200 cropped to 3840x2160. Confirmed on the Pi (clips C0030, C0031): 12-bit mode DNG 16 bps, median 6286, p99 ~15700, matching the 16-bit mode (C0028: 6294 / 15943).
**Still open:** frame drops in Core in both Clear HDR modes (0-4 frames per 2-3 s; one 12-bit clip had 0), while the rpicam-raw bench delivers 33 frames / 1.5 s in 16-bit and 9 in 12-bit, so Core's capture path loses them.

## Real 12-bit storage (2026-10-25 22:20, uncommitted in Core)

**Confirmed:** this image's libcamera (`v0.7.1+qbcfork.20260522`) expands the 12-bit mode in software, `libcamera::CcmpUnwrap` (`pipeline/rpi/pisp/ccmp_unwrap.cpp`, exported from `libcamera.so.0.7`). Its table, read by calling the real `setParams({500, 11500, 6, 4, 200})` + `process()` on `code << 4` inputs: `y = code - 200`; `L = y` up to knee 500, `((y-500)<<6)+500` up to C2 = 671 (inclusive), `((y-671)<<4)+11500` above; `out = 3200 + L*62320/63084` (integer). t[700]=3693, t[701]=3757, t[871]=14505, t[4095]=65520. Codes 0-200 all give 3200; ~6 of the 500 linear codes merge (scale 0.988). Every value in a recorded frame is in the table and maps back to a unique code.
Cinemate's own table (`L + 200` domain, measured knee 500.3389) does **not** match this libcamera; do not use it here.
Core: `src/cdng/ClearHdrCcmp.hpp` reproduces the table bit for bit (all 4096 entries checked against libcamera). In the 12-bit mode as cDNG, `compressClearHdrFrame` maps each sample back to its code at the recorder hand-off; the DNG carries the table (tag 50712), black 3200, white 65520. MLV in the 12-bit mode keeps the linear 16-bit samples (no table in MLV). Clear HDR forces 4K in both modes (libcamera rejects 1920x1080 in Clear HDR).
Results (clips C0032-C0035): 12-bit uncompressed 12.5 MB, lossless **5.9 MB**, decoded median 6033 / p99 15066 vs 16-bit mode 6053 / 15168 (16.6 MB). ProRes (HQ 1080p, 96 frames / 4 s) and H.264 (1080p30, 120 frames / 4 s) record normally; `set_clear_hdr true` there now returns an error instead of a silent ok:true.

## Frame rate in Clear HDR (2026-10-25 22:40): what is known

- **CMA is not the cause (confirmed).** `/dev/dma_heap/vidbuf_cached -> system` on this image: Core's raw buffers come from the system heap, not the 64 MB CMA. The earlier CMA lead (`working/clearhdr-fps-request.md`) is withdrawn.
- **Pixel-rate bound:** this image's libcamera logs `RP1_PLL_SYS request=333333333 Hz ... PiSP pixel-rate cap = 646.667 Mpix/s`, so it already detects the RP1 overclock (`dtoverlay=rp1-clk-333mhz`) and lifts the bound above Cinemate's 580. The 380-MPix/s ceiling (21.99 fps) Cinemate describes should not apply here. **Probable**; check the advertised 4K Clear HDR fps with `rpicam-hello --list-cameras` (Core stopped).
- The rpicam-raw bench (22 fps at 16-bit) writes every frame synchronously to disk, so it is not a clean ceiling measurement.
- **Cinemate's answer** (Mac, 2026-10-25, cinepi-raw `63a08d5`): 8-10 raw buffers, preview count = raw count, no copy on the completion thread; one copy fused with the format work in 4 encode workers, after which the camera buffer is requeued; disk writes from a RAM pool. Clear HDR preview work on the completion path cost 19-35 ms per 40 ms frame on Cinemate.
- **Core today:** 4 raw buffers; the completion callback copies the whole raw frame (16.9 MB) and, in the 12-bit mode, also runs `compressClearHdrFrame` (8.3 Mpx lookups); libcamera's `CcmpUnwrap` adds another 8.3 Mpx pass in the 12-bit mode. **Probable cause of the drops: completion-path work + too few buffers.** Next: time request-complete to requeue per buffer (needs journal access or a counter in state), then move copy/convert to workers and raise the buffer count.

## Frame drops: cause found (2026-10-25 22:55, Core `9fa7918`, nothing changed yet)

Measured with Core idle (not recording) in Clear HDR **16-bit**, one WebUI client open.

- **Confirmed: the camera thread is saturated.** libcamera's `CameraManager` thread (the one Core sets to nice -5, it also runs `requestComplete`) sits at 93-95 % CPU, **all user time** (475 user / 0 sys ticks in 5 s).
- **Confirmed: the time is in libcamera, not Core** (sampler `working/tools/usample.py`, 4680 samples): 63.6 % `PiSPCameraData::cfeBufferDequeue` = an in-place `rev16` byte swap of the whole raw buffer after `dmabufSyncStart`, when stream flag bit 5 is set (`libcamera.so.0.7.1+0x141c94`); 36.3 % `RawStatsProducer::process` (software stats, via `processRawStats`); **0.1 %** all of Core (`requestComplete`, preview, web preview).
- **Probable: delivery to Core is ~4 fps.** ~240 ms of CPU per frame; the IPA's `ipa_base.cpp:1450 No HDR algorithm available` warning (Core never sends `HdrMode`) comes ~4.0/s in bursts of 3 per ~756 ms, the same rhythm as the recorded frame numbers 0, 14, 15, 19 (3 frames per 19 sensor periods).
- **Probable: the passes are slow because the buffers are CPU-uncached.** Both hot spots are the instruction after a load (`rev16` after `ld1`; `uzp` after `ldr q31`). The swap moves 33.8 MB in ~150 ms (~225 MB/s); a NEON pass over cached RAM would take < 10 ms.
- **Confirmed: in Clear HDR, Core's raw buffers are not the cached heap.** Every 16.9 MB dmabuf in the process (10 distinct) is exported by `videobuf2_dma_contig`, none by `system`. `CameraController.cpp:6522-6525` (upstream 1.6.0) uses cached heap buffers only when `packing == PispCompressed1`. Both Clear HDR modes are `unpacked`, so `allocator_->allocate(rawStream_)` gives the CFE's own buffers. **This corrects "CMA ruled out" above**: it holds for SDR COMP1 only (10 x 16.9 MB > `CmaTotal` 64 MB, so these are probably IOMMU-backed, not CMA; `CmaFree` 496 kB).
- **Not the cause:** the cadence gate (`:6857-6863` clears after the first matching frame and never skips again); Core's completion path (0.1 %).
- **Unexplained:** the `rpicam-raw` bench reached ~22 fps in 16-bit through the same libcamera. Possibly no software stats or no byte swap without an ISP output. Unverified.
- **12-bit mode:** not measured; expected worse (adds `CcmpUnwrap::process` on the same buffers).
- **Next, change 1:** let unpacked Clear HDR raw streams use the cached heap too (`:6523`), then re-measure thread CPU, warning rate, and a 10 s take.
