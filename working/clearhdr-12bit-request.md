# Request for the Mac-side Claude: the Clear HDR 12-bit (CCMP) linearisation

Written on the Pi 2026-10-25 for the session that has the Cinemate source (`~/Documents/cinemate/cinepi-raw`, `cinemate`, the `Tiramisioux/libcamera` fork). Comparison material only: port the logic, do not copy code (cinepi-raw derives from rpicam-apps, BSD-2-Clause; read Apertar-Core's `LICENSE` first). Context: `working/clearhdr-design.md`.

## What we see on the Pi

Apertar-Core, IMX585, Clear HDR on, `raw_bit_depth=12`. The sensor is in its **companded 12-bit mode** (`SRGGB12_1X12`, 3840x2160, WDR=1). Core writes it as plain linear 12-bit. In a DNG converter the picture is recognisable but has a strong **purple/magenta cast**, green-yellow edge fringes, blown posterised highlights and magenta speckle in transitions. Raw samples: median 1634, p99 4073, max 4086 of 4095, against 468 / 1312 / 1368 for SDR of the same scene (exposure 2700 lines, gain 60 in both). 16-bit Clear HDR (linear) looks right, so only the 12-bit companded path needs the remedy.

## What the driver sets (`imx585.c`, branch `apertar`)

| Register | Meaning | Driver default |
| --- | --- | --- |
| `CCMP1_EXP` 0x36e8 (24 bit) | knee 1, 16-bit domain, control `+2` element 0 | 500 |
| `CCMP2_EXP` 0x36e4 (24 bit) | knee 2, control `+2` element 1 | 11500 |
| `ACMP1_EXP` 0x36ee | slope of the middle segment, 6..11 = 1/64..1/2048, control `+3` | 6 (1/64) |
| `ACMP2_EXP` 0x36ec | slope of the high segment, 0..5 = 1/1..1/32, control `+4` | 4 (1/16) |

Driver comment (`imx585.c:517`): "ACMP2_EXP = 1/16 (high slope; natural inverse spans 16-bit, no LUT stretch needed)". Controls: `hdr_gradient_compression_thresh` (u32[2]), `hdr_gradient_compression_ratio` (two menus). Core does not write them today.

## Questions

1. **The curve.** Where does Cinemate turn the 12-bit companded codes back into linear values: a function, a table, or a decode step in the DNG writer (`options_->hdr` gates "the DNG/CCMP decode")? Give file:line and the formula, as a piecewise function of the three knobs and the black level.
2. **Which values Cinemate uses** for the two thresholds and the two slopes (`config_loader.py`, `cinepi_controller.cpp`), and whether it writes the four controls at all or keeps the driver defaults.
3. **How the result is stored.** DNG `LinearizationTable` (tag 50712 / 0xC618, 4096 entries) with what `WhiteLevel` and `BlackLevel`, or decoded to 16-bit linear before writing (then `BitsPerSample` 16)? Which does Cinemate choose, and why?
4. **The libcamera fork.** `pisp.cpp:1654-1663` logs `ClearHDR 12-bit CCMP stats linearisation enabled`. Does the fork linearise only the ISP statistics, or the image the ISP processes too? That decides whether the preview is right and only the DNG is wrong.
5. **Black level in the companded mode.** The IPA says `BLC: tuning=3200 ... live pixel BLC=3200 (scale=64)`. Is the 12-bit companded black code 200, 0, or something else?

## Where it plugs in on the Apertar side

- `RawFrameView.gradationCompanded` (`include/apertar/core/Types.hpp:221`) exists and nothing sets it for Clear HDR yet; the lossy encoder already reads it.
- `CdngEncoder::Metadata::linearizationTable` (`src/cdng/CdngEncoder.hpp:27`) is written as tag 0xC618 (`CdngEncoder.cpp:1586`); `whiteLevel` then comes from `table.back()` (`:1373`); size must equal `1 << bitsPerSample` (`:1220`).
- MLV has no equivalent yet.
