# Answer: Clear HDR 12-bit (CCMP) linearisation, as Cinemate does it

Reply to `clearhdr-12bit-request.md`. Written on the Mac 2026-10-25 from the Cinemate source:

| Repo | Branch | Commit |
| --- | --- | --- |
| `cinepi-raw` | `dev` | `63a08d5` |
| `cinemate` | `dev` | `d6cc93e0` |
| `Tiramisioux/libcamera` | `cinemate` | `bfe0b76a0` |
| `imx585-v4l2-driver` | `cinemate-7modes` | `bd57617` |

What follows is logic and numbers only, with no code. The numbers are measurements. Port the logic. Do not copy the code.

## Read this first: the magenta speckle may be a second, separate bug

The Apertar driver (`apertar` branch, `imx585.c:510`) ships `EXP_BK 0x36e2 = 0x00`, which is blend menu 0. Apertar-Core never writes `hdr_data_blending_mode`.

On Cinemate, **menu 0 caused white/magenta speckle and frames stuck at the pedestal** in every ClearHDR mode. The fix is menu 5 (HG 1/16 + LG 15/16). The operator confirmed it visually on 2026-08-31, in all seven modes.

- Cinemate sends it as V4L2 control `IMX585_CID_BASE + 1` (`V4L2_CID_USER_BASE + 0x2000 + 1`, a menu with values 0..8). See `cinepi-raw/cinepi/cinepi_controller.cpp:73-75` and `:380-386`.
- The default is 5, in `cinemate/src/module/config_loader.py:300` (`hdr_cfg.get("blend", 5)`).
- The driver default stays 0 on purpose. **Anything that isn't Cinemate has to set this control itself.**

Your report has two separate symptoms:

| Symptom | Likely cause | Fix |
| --- | --- | --- |
| Purple/magenta cast that changes with level, worst around codes 700–900 | Companded data decoded as linear | The LinearizationTable below |
| Magenta speckle in transitions | Blend menu 0 | Set blend 5 |

Set blend 5 **before** you judge the table.

## 1. The curve

Cinemate decodes with a **LinearizationTable in the DNG**. The pixels are never rewritten. The generator is `cinepi-raw/cinepi/ccmp_lut.hpp`:

- model: `:24-30`
- forward and inverse: `:256-286`
- table build: `:307-347`

The DNG writer attaches the table in `cinepi/dng_encoder.cpp:689-706` (setup) and `:1655-1657` (tag 0xC618).

### Model

`L` is the linear value above black, in 16-bit ClearHDR LSB. `b` is the binning: 1 at full res, 4 for 2×2 binned. `P` is the pedestal.

```
stored_code = ccmp(b·L)/b + P

ccmp(x) = x                      x ≤ T1
        = T1 + (x−T1)·s1         T1 < x ≤ T2
        = C2 + (x−T2)·s2         x > T2,   C2 = T1 + (T2−T1)·s1
```

### Inverse, which is what the table holds

```
y = b·(C − P)

x = y                            y ≤ T1
  = T1 + (y−T1)/s1               T1 < y ≤ C2
  = T2 + (y−C2)/s2               y > C2

table[C] = floor( x/b + 200 + 0.5 )        C = 0..4095
```

### Constants (`ccmp_lut.hpp:91-95`, `:159-160`)

| Knob | Value |
| --- | --- |
| T2 | 11500 (register) |
| s1 | 1/64 (`ACMP1` index 6, s = 2^−idx) |
| s2 | 1/16 (`ACMP2` index 4) |
| P | 200 |
| T1, b=1 (full res, 3856×2180 readout) | **500.3389** (effective, measured) |
| T1, b=4 (2×2 binned, 1928×1090) | **500.9431** (effective, measured) |

### The parts that change the table if you "clean them up"

1. **Binning goes into the curve.** The compander sees the binned sum, so binned modes put the knees 4× lower in L. Use one table per binning. If the selection is backwards, the error is 2.6× at knee 1, and the picture does not look obviously wrong. Your 3840×2160 test is b=1.
2. **T1 is measured, not the register value.** With register T1 = 500 the mid-tones are 21 L low at b=1 and 15 L low at b=4. The correction does not scale with b, so it is two separate anchors, one per mode. For a mode with no measured anchor, Cinemate refuses to write a table (`ccmp_lut.cpp:47-58`); it does not fall back to 500.
3. **Round with `floor(x + 0.5)`, not round-half-to-even.** Every binned top-segment entry is a half-integer. Ties-to-even would alternate the steps between 15 and 17 and put a ripple in the slope.
4. **Never clamp.** If an entry would fall outside uint16, the build fails.

### Where the knees land, as a check

| | b=1 | b=4 |
| --- | --- | --- |
| Identity up to code | ~700 | ~325 |
| Knee 2 at code | ~872 | ~368 |
| `table[4095]` | 63265 | 62704 |

Below knee 1, `table[C] == C`. A one-line test for that catches binning, pedestal and domain mix-ups.

Golden tables, so you can diff byte for byte: `cinepi-raw/resources/ccmp_luts/ccmp_decode_mode3_fullres.txt` (b=1) and `ccmp_decode_mode2_binned.txt` (b=4).

## 2. Which values Cinemate uses for the four knobs

**Cinemate never writes the threshold or slope controls.** It keeps the driver defaults: 500 / 11500 / index 6 / index 4. A grep of both repos finds no `gradient_compression` and no `ACMP`/`CCMP` register writes. The table hardcodes those values as constants and was validated against a driver readback with ClearHDR live (thresholds 500/11500, slopes 1/64 and 1/16).

If Apertar ever exposes the knobs, the table has to be regenerated from the live values. The measured T1 correction would then no longer be valid either.

The `cinemate-7modes` and `apertar` drivers set the same defaults (`grad_thresh_def = {500, 11500}`, `0x36ec = 0x04`, `0x36ee = 0x06`).

One gotcha: `v4l2-ctl --list-ctrls-menus` prints `default=0` for the threshold control. That is expected. The real values are copied straight into the current value (`memcpy` into `p_cur`/`p_new`), not set through `.def`.

## 3. How the result is stored

**As a LinearizationTable.** The data stays 12-bit `BitsPerSample` and is never decoded to 16-bit.

| Tag | Value |
| --- | --- |
| `BitsPerSample` | 12 |
| 0xC618 `LinearizationTable` | 4096 SHORTs, as above |
| 0xC61A `BlackLevel` | **200** on all four CFA channels |
| 0xC61D `WhiteLevel` | `table.back()`: **63265** (b=1), **62704** (b=4) |

The level tags are in `dng_encoder.cpp:1535-1545` and `:1631-1633`. `WhiteLevel` may be lowered further to a measured ClearHDR clip ceiling, still in the table's output domain.

Why:

- **It keeps file size down.** The data stays 12-bit, and a raw app decodes it with no post step.
- **The pixels are untouched,** so a wrong table can be fixed later without touching any pixels.
- **The output domain is `L + 200` ("KEEP_PEDESTAL")** because it is the only one of the four candidates that fits uint16 at both ends in both modes. The black-referred domain (`L + 0`) underflows below the pedestal. The 16-bit domain (`L + 3200`) overflows at the top: 63065 + 3200 = 66265.
- **Under a LinearizationTable, a reader applies the table before it reads BlackLevel and WhiteLevel.** Both tags therefore describe the table's output, not the stored codes.
- **Do not take BlackLevel from `SensorBlackLevels`.** It reports 3200, which rescales to about 3089, but the table says 200. Write one value on all four channels: the table is per code and has already flattened any per-channel offsets.

This fits your `CdngEncoder` constraints:

- table size `1 << 12` = 4096 ✓
- `whiteLevel` from `table.back()` ✓
- you still have to force `blackLevel = 200` instead of the metadata value

A gate: Cinemate only attaches the table when ClearHDR is on, the mode is 12-bit, and the requested mode matches the configured raw stream (`cinepi/ccmp_gate.hpp:42-46`). The 16-bit ClearHDR mode is linear and gets no table. 12-bit SDR gets none either. A trustworthy depth needs the media-bus code, not the R16 container: on the Pi, a 12-bit request once came back as the real 16-bit mode.

If you log-encode, Cinemate composes the decompand with its 16→10 log curve into one table, for target 10 only. That is Cinemate-specific and you can skip it.

## 4. The libcamera fork and the preview

**The log line is not in our fork.** `ClearHDR 12-bit CCMP stats linearisation enabled` does not appear in any branch of `Tiramisioux/libcamera`, local or on GitHub (`cinemate`, `feature/rp1-clock-autodetect`, the imx283 branches, `docs/…`). Our `pisp.cpp` is also shorter: its only bit-depth gate is at `:1456` (`bitsPerPixel == 16` → "statistics will not be correct"). So the libcamera on the Apertar-Beta image comes from somewhere else. Find its source before you trust the line, for example with `dpkg -S libcamera.so` / `apt-cache policy libcamera0*` on the Pi, or by checking where the Apertar-Beta image takes libcamera from.

What Cinemate does without any such fix:

- **Neither the ISP nor the stats see linear data.** They read companded codes as linear. AE/AWB still run in 12-bit ClearHDR, because the 16-bit gate doesn't trip, but they are approximate. This is why 12-bit is Cinemate's auto-exposure ClearHDR mode and 16-bit is its manual, quality mode.
- **Without a fix, the preview is magenta too.** Cinemate fixes it in cinepi-raw, not in libcamera. A post-processing stage (`cinepi/ccmpPreviewStage.cpp`) takes each frame's raw Bayer, decompands it with the same per-binning table, and writes the result over the lores YUV that HDMI/MJPEG show. That stage needs an unpacked raw (`:12:U`); with a packed one it disables itself and the preview stays magenta.

How to read your line once you have its source:

- **The decompand runs in the PiSP front end, before both stats and BE** (as the stock `rpi.decompand` block would): the preview is right and only the DNG is wrong.
- **It is applied to the stats only:** the preview is wrong too. Expect the same level-dependent magenta on HDMI.
- **Quick hardware check:** look at the live preview of a grey ramp. If R/G and B/G stay flat across levels, the image path is linearised.

## 5. Black level in the companded mode

**200 in stored 12-bit codes, measured.** Lens-cap frames put every 12-bit mode at about 201. The worst deviation across all six modes, 12-bit and 16-bit, was 1.3 codes.

The pedestal sits **outside** the compander: the compander works on black-referred L, and 200 is added afterwards. So you subtract 200 from the stored code **before** the inverse, as in `y = b·(C − 200)` above.

The IPA's `BLC=3200` is the 16-bit-domain value, and 3200/16 = 200. Do not feed 3200 into the 12-bit curve.

An older desk derivation said "companded black ≈ 542". It was wrong, because it took the 16-bit black as the compander's input black.

## A sanity check against your numbers

Your SDR median is 468 and your 12-bit ClearHDR median is 1634 at the same exposure and gain. At b=1, code 1634 decodes to L = 11500 + (1434 − 672.2)·16 ≈ 23690, which is on the top segment. Most of the frame then sits on the 1/16 segment, which is where a linear reading is most wrong. That fits the cast you describe.

Your p99 of 4073 means the highlights really do reach the top codes. That matches `WhiteLevel` near 63265, and the white point needs no clamp.
