# V-H1: refutation attempt, binned 1920x1080 12-bit Clear HDR decoded with the b=1 curve

Verdict: **survives**. I could not refute it. Each part that code can decide holds. The one premise code cannot decide is that the sensor compands the 2x2 binned sum, with the knees 4x lower in delivered-linear terms. That premise comes from Cinemate's hardware measurement, not from Apertar code and not from an Apertar capture. Label: plausible, needs the Pi. Confidence: high.

## What I tried to break, and what the code says

| # | Refutation attempt | Result | Evidence (read myself) | Label |
| --- | --- | --- | --- | --- |
| 1 | Maybe the driver does not offer binned 12-bit Clear HDR | Fails. Colour 12-bit Clear HDR lists start at `IMX585_MODE_1080P_12BIT`. That entry is `.width = 1920, .height = 1080, .binning = 2` | `imx585.c:3063-3091@cd548ef` (`*mode_list = &supported_modes[IMX585_MODE_1080P_12BIT]`), `imx585.c:1065-1074@cd548ef` | confirmed |
| 2 | Maybe this mode existed before the port and was already fine | Fails. The baseline offered only 4K in 12-bit Clear HDR: "WDR=1 therefore exposes only the 4K all-pixel mode", `*mode_list = &supported_modes[10]; /* 4K 12-bit only */`. The binned mode came back in `c1350b0` (2026-08-31), whose message says "Desk-only: the colour-rig gate must include one binned 12-bit CCMP capture" | `imx585.c:1417-1432@e5b74d3`; `git show c1350b0` | confirmed |
| 3 | Maybe Core never asks for it | Fails. `kH12Modes` starts with `{ 1920, 1080, true }`. `find()` returns the binned row. The config check accepts it when ScalerCropMaximum is 3840x2160 (`binning = imx585Row->binned ? 2u : 1u`). Fork main has no `Imx585Modes.hpp` (`git show origin/main:src/camera/Imx585Modes.hpp`: does not exist). The table came in with `caa0153` | `Imx585Modes.hpp:78-79@01f170c`, `:180-190`; `CameraController.cpp:512-518@01f170c`, `:8511-8520@01f170c` | confirmed |
| 4 | Maybe the driver scales the CCMP thresholds for binning | Fails. `GRAD_TH` writes `thr[0]`/`thr[1]` straight to `CCMP1_EXP`/`CCMP2_EXP`. The default is `{ 500, 11500 }` for every mode. `CCMP_EN=1` is set for any 12-bit Clear HDR code. Nothing in it depends on `mode->binning` | `imx585.c:3604-3613@cd548ef`, `:3688`, `:3907-3908`, `:4149-4158` | confirmed |
| 5 | Maybe libcamera reads binning, or skips the unwrap when binned | Fails. The gate is `model == "imx585" && bitsPerPixel == 12 && initCcmpUnwrap()`. `initCcmpUnwrap` reads WDR, GRAD_TH, GRAD_COMP_L/H and BRIGHTNESS only. `CcmpUnwrap::Params` has `thresh1, thresh2, slope_l_idx, slope_h_idx, blc_u12`, with no binning field. `inverse()` is the b=1 curve | `pisp.cpp:1821-1844@6b0b49f`, `:2950-3028`; `ccmp_unwrap.h:57-67@6b0b49f`; `ccmp_unwrap.cpp:63-73@6b0b49f` | confirmed |
| 6 | Maybe libcamera's LUT feeds only stats, so preview and AE would be untouched | Fails. The comment at `pisp.cpp:1825-1831` says "the raw buffer is NOT rewritten", but the code rewrites it in place before the BE and the stats run: `ccmpUnwrap_->process(rawPx + y * strideU16, width)`. The async path does the same. So the BE (HDMI, touch and WebUI preview), the AGC stats and the recorded raw all carry the same decode | `pisp.cpp:3091-3104@6b0b49f`, `:825-829@6b0b49f` | confirmed (the stale comment is a separate finding) |
| 7 | Maybe Core's DNG table corrects what libcamera got wrong | Fails. `ccmp::Params` has no binning. `metadataFromRequest` attaches `ccmp::expansionTable()` (the default b=1 params) whenever `clearHdrStoresCodes12` holds. `compressionLut()` inverts the same b=1 table, so the round trip is exact and the error passes through unchanged | `ClearHdrCcmp.hpp:24-30,47-65,69-83@01f170c`; `CameraController.cpp:4090-4096@01f170c` | confirmed |
| 8 | Maybe binned codes follow the b=1 curve (binning after the compander, or the sensor averages before companding) | Cannot be refuted from code. Cinemate fitted per-mode anchors on two chart sessions. Its b=4 anchor `{ 4.0, 500.9431, 2582 }` places the mid-segment intercept a1 = P + T1(1-s1)/b at about 323 codes. Under b=1 it would be about 692 codes. The binned clip zone sits at 2582, against 2900 at b=1. Both numbers only make sense if the compander sees the binned sum. Its register constants (500/11500/idx6/idx4) match the driver defaults at cd548ef | `cinepi/ccmp_lut.hpp:22-44,91-94,138-161@63a08d5`; `resources/ccmp_luts/ccmp_decode_mode2_binned.txt@63a08d5` header | probable (external measurement; the data files live in the innomaker585 workspace, which is not in this container) |
| 9 | Maybe the driver comment "colour passed binned 12-bit CCMP" proves the binned picture is right | No. That claim and the `c1350b0` gate both talk about the sensor returning a non-BLC image ("not-all-200 verdict"). Neither checks the transfer curve | `imx585.c:3049-3057@cd548ef`; `git show c1350b0` | confirmed (as a reading of the text) |
| 10 | Maybe the size of the error is overstated | No. I reran the numbers myself in a new program, see the next section. Under b=4 the knees sit at codes 325 and 368. Core and libcamera put them at 700 and 871. Codes 326..871 decode at 0.06..0.13x their true level | `/home/user/build/hdr12-numeric/v-h1/fix_sketch.out` | confirmed (arithmetic) |

## Numbers (host, `/home/user/build/hdr12-numeric/v-h1/fix_sketch.cpp`)

Sensor model from `ccmp_lut.hpp:24-28@63a08d5`: `code = ccmp(b*L)/b + P`. "Core decode" is the shipped b=1 table.

| Code | b=1 table (shipped) | b=4 table (sketch) | True L above black at b=4 |
| --- | --- | --- | --- |
| 325 | 3323 | 3324 | 124 |
| 368 | 3365 | 6070 | 2879 |
| 500 | 3496 | 8175 | 4990 |
| 700 | 3693 | 11365 | 8190 |
| 872 | 14576 | 14109 | 10942 |
| 4095 | 65520 | 65520 | 62511 |

For codes 368..871, which run from about 4.6% to 17.5% of white and hold the grey card, the shipped table returns 3365..3693, about 0.05..0.5% above black. At code 872 the output jumps to 14576. The result is a hard step near 17% of white and crushed mids. Because the R, G and B channels of one patch land on different sides of the step, the colour shift depends on level. The sketch's b=4 table decodes the b=4 forward model with a worst error of -0.22 EV at L=220. That is the code quantisation right above knee1: one code is 64 L there. Above L=400 the error is under 0.03 EV. The sketch leaves the b=1 table bit-identical (4096/4096 entries).

## Fix sketch (if the Pi confirms)

The bug sits in two places that must agree: libcamera's LUT (preview, AE, recorded buffer) and Core's table (`compressionLut` inverts libcamera's output; the DNG LinearizationTable). Fixing Core alone breaks the round trip.

**Smallest safe change (Core only, recommended first).** Stop offering the mode until a binned capture checks the curve. Delete `{ 1920, 1080, true },` from `kH12Modes` (`Imx585Modes.hpp:79@01f170c`) and change `imx585_modes_test.cpp:20` to `== 28`. Then `find(H12, 1920, 1080)` returns null and `nearest` answers `{1920, 1040, false}` (distance 40), a 1x1 crop. The driver can keep offering the row. Core simply stops requesting it. The equivalent in the driver is to start the CCMP range at `IMX585_MODE_4K_12BIT`, which reverts c1350b0. That repeats the WP-585-5 history ("silently turned 1920x1080 into a 1x1 centre crop"), so the Core row is the cleaner place.

**Full fix (keeps the mode).** Add one field in the existing style, in both files:

```cpp
// ClearHdrCcmp.hpp, Params
uint32_t binning = 1;    // pixels summed before the compander: 1, or 4 for 2x2 binning

// linearAboveBlack: the sensor compands the binned sum and divides back
if (y <= 0)
    return 0;
const uint32_t value = static_cast<uint32_t>(y) * p.binning;
... (the existing three segments on `value`) ... / p.binning
```

- `expansionTable()` becomes `expansionTable(bool binned)` with two statics.
- `compressionLut()` takes the same flag.
- `CameraController.cpp:4090-4096` and the codes12 mapping at `:9491` pass `imx585::find(Class::H12, w, h)->binned`.
- libcamera `CcmpUnwrap::Params` gets `uint8_t binning` and `inverse(out * b) / b`. `initCcmpUnwrap()` sets it from `sensorInfo.analogCrop.width / sensorInfo.outputSize.width`, squared.

This keeps the register T1 for both binnings. Cinemate's measured anchors (500.34 at b=1 and 500.94 at b=4) are a separate refinement that the port does not use at b=1 either.

**Host test.** New file `tools/clear_hdr_ccmp_test.cpp`, plain `g++ -std=c++20 -I src`, in the style of `imx585_modes_test.cpp` (CHECK macro):
- `buildExpansion({})` is unchanged entry for entry (b=1 regression).
- With `binning = 4`: `table[325] - 3200 < 2`, and `table[700]` lies within 1% of `3200 + 8184 * 62320 / 62511`.
- Feeding codes from the forward model `ccmp(4L)/4 + 200` for L in 400..60000 stays within 0.03 EV.
- `expansion[compressionLut[v]] == v` for every value of the b=4 table.

## What remains for the Pi

| Check | Command or action | Confirms H1 if |
| --- | --- | --- |
| The binned mode is what runs | `journalctl -b -u apertar-core \| grep 'camera configured'` after choosing 12-bit Clear HDR at 1920x1080 | `raw=1920x1080` with binning 2; `journalctl -b \| grep CcmpUnwrap` shows `T1=500 T2=11500`, so the b=1 LUT is live |
| The curve | Same scene, same shutter and ISO: one 12-bit and one 16-bit Clear HDR take at 1920x1080. Decode both through their own tags and compare patch medians on a grey ramp or chart | Patches between about 4.6% and 17.5% of white read about 16x low in 12-bit, with a step at about 17.5%. Patches below about 0.2% and above 18% match within a few % |
| Control | The same pair at 3840x2160 | Matches within 0.3% (as on 2026-10-25) |
| Refutes H1 | If 1920x1080 12-bit matches 16-bit within a few % across the ramp | The compander sees per-pixel values. Cinemate's b=4 model does not apply to this rig and driver |
