# V-H7: skeptic check of H7 (inherent 12-bit CCMP encoding)

Refs: Core `01f170c`, driver `cd548ef`, libcamera `apertar` `6b0b49f`. Host programs:
`/home/user/build/hdr12-numeric/vh7/h7.cpp`, `h7b.cpp` (built with `g++ -std=c++20 -O2 -I/home/user/Apertar-Core`,
both include the real `src/cdng/ClearHdrCcmp.hpp`).

## Verdict

**Not a cause.** The arithmetic of H7 holds. The symptoms it predicts do not follow from that arithmetic,
and they are too small to explain an unprompted "strange output" report. Three parts of H7 are wrong:
the "banding in mid-tones" claim, the "gentler driver slope" fix, and the correction of G6-4.

## 1. What holds (confirmed, read and run)

| Claim | Evidence | Status |
| --- | --- | --- |
| Middle segment = linear 500..11500 above black on codes 701..871 (171 codes) | `ClearHdrCcmp.hpp:39` `knee2Code = knee1 + ((knee2 - knee1) >> slope1)` = 500 + 171; params `:24-30` 500 / 11500 / 6 / 4 / 200 | confirmed |
| Step in that segment 63..64 LSB16 | h7: T[700]=3693, T[701]=3757, T[871]=14505, T[872]=14576 (stretch 62320/63084 = 0.988) | confirmed |
| libcamera sends codes 0..201 to 3200 | `ccmp_unwrap.cpp` (6b0b49f) `in = (out_post_blc <= 0) ? 0u : inverse(...)`; code 201 gives 1 x 0.988 = 0 after integer division. h7: T[0]=T[201]=3200, T[202]=3201 | confirmed |
| Core stores black as code 0, never 1..201 | `ClearHdrCcmp.hpp:76-78` lowest-code search; h7: C[3200]=0 | confirmed |
| Driver defaults match Core | `imx585.c:557-558` ACMP2=0x04, ACMP1=0x06; `:3688` `grad_thresh_def = {500, 11500}`; `:3724` ACMP1 `.def = 6`; `:3735` ACMP2 `.def = 4` @cd548ef | confirmed |

## 2. What does not hold

### 2a. "Banding in mid-tones, including 18 % grey": refuted (numeric, noise model probable)

Step per code as a share of the signal (h7, above-black linear, LSB16):

| Above black | Code | Step | Step % | Stops per code |
| --- | --- | --- | --- | --- |
| 494 (knee 1) | 701 | 63 | 12.8 | 0.173 |
| 1000 | 709 | 64 | 6.4 | 0.090 |
| 2000 | 724 | 63 | 3.2 | 0.045 |
| 3022 (KB 4K scene median, 6222) | 740 | 64 | 2.1 | 0.030 |
| 6000 | 788 | 63 | 1.1 | 0.015 |
| 11000 (18 % of clip, code ~869) | 867 | 63 | 0.6 | 0.008 |
| 20000 (high segment) | 1418 | 16 | 0.08 | 0.001 |

- At 18 % grey the step is 0.6 % (0.008 stop). No converter push makes that a band.
- Coarse steps exist only from about -7 to -5 stops under clip (above-black 500..2000).
- Shot noise dithers them. h7b models the sensor (forward CCMP with truncating shifts, assumed), Gaussian
  noise `sigma^2 = r^2 + y/g`, and decodes through Core's table. Ripple of the local mean (the thing that
  shows as a band) between 1000 and 11400 above black is under 0.1 % of the value for g = 0.5..2 e-/LSB16,
  under 1.1 % even at g = 4. Between 520 and 1000 the ripple of 2..4 % is the knee transition (2c), not
  posterisation.
- Visible effect instead: quantisation noise of 64/sqrt(12) = 18.5 LSB16 adds to the shot noise.
  At 1000 above black and g = 1: 31.6 -> 36.6 LSB16 (+16 %). Deep shadows are slightly grainier, not banded.
- g (e-/LSB16) for this sensor in Clear HDR is **unconfirmed**; settle with a flat-field pair (two frames,
  same exposure, 16-bit Clear HDR) and `var(diff)/2` against mean at three exposures.

### 2b. "One-sided noise floor, lifted tinted blacks": real but tiny (confirmed arithmetic)

- Half-rectified black lift = mean of clipped noise: r = 5 / 10 / 20 / 30 natural units -> +2 / +4 / +8 / +12
  LSB16 (h7). Against 18 % grey at about 11 000 that is -10.5 to -12.5 stops. Needs a push of about +5 EV to see.
- Most converters clip negatives after subtracting BlackLevel 3200 anyway, so a 16-bit DNG shows the same
  half-rectified floor in the same tools (probable; depends on the converter doing NR or demosaic before the clip).
- Whether the sensor emits codes below 200 at all is **unconfirmed** (sensor behaviour, not in code). The
  proposed Pi test "spike at 0, nothing in 1..201" cannot fail: Core's compression LUT makes it true for any
  input (`ClearHdrCcmp.hpp:76-78`). It confirms nothing about visibility.

### 2c. New: half-bin bias at the knee (probable; depends on the sensor rounding)

- libcamera's inverse returns the low edge of each bin: `T1 + ((out - T1) << sL)` (`ccmp_unwrap.cpp`, 6b0b49f);
  Core copies it (`ClearHdrCcmp.hpp:43-44`).
- If the sensor truncates (a hardware shift does), every mid-segment value decodes 32 natural units low,
  every high-segment value 8 low; the 1:1 segment is unbiased. h7b: mean bias -32.0..-32.2 LSB16 for all
  windows above 1000.
- Effect: -0.05 stop at 1000 above black, -0.09 at 600, nil at grey. A small kink at knee 1 (linear 3694 out16).
  Not a "strange output".
- Fix only if the Pi shows it: add half a bin in both places at once, libcamera `inverse()` and Core
  `linearAboveBlack()`, so `expansionTable()[compressionLut()[v]] == v` still holds for every value libcamera emits.
  Core alone must not change; it would break that identity (`ClearHdrCcmp.hpp:67-68`).
- Settle: grey ramp at 12-bit and 16-bit Clear HDR, same exposure; compare region means at 600, 1000, 4000
  above black after the 0.988 scale. A 12-bit deficit of about 32 LSB16 in every region above knee 1 confirms truncation.

### 2d. "Driver slope defaults ... if a gentler curve is wanted": wrong

- ACMP1 (middle) allows only 06h..0Bh = 1/64..1/2048 (`imx585.c:3705-3706@cd548ef`, `.min = 6` at `:3724`).
  1/64 is already the gentlest middle slope. Writing less puts the sensor in a clamped state (`:3709-3710`).
- The only lever is the thresholds (`V4L2_CID_IMX585_HDR_GRAD_TH`, `:3688-3700`, range 0..0x1FFFF) together
  with ACMP2 = 1/32 (05h) to free codes. Example: T1 = 2000, T2 = 11500, ACMP2 = 05h uses 200 + 2000 + 148 +
  (63084 - 11500)/32 = 3960 codes. That moves the 1:1 segment up to -5 stops. Needs a matching libcamera
  rebuild (it reads live controls, `pisp.cpp:2990-3023@6b0b49f`) and Core's fixed `Params` (`ClearHdrCcmp.hpp:24-30`).
  Not worth it before 2a's g is measured.

### 2e. Counter-evidence "G6-4's 6.4 % at linear 4200 is wrong": the correction is wrong

- G6-4 quotes out16 values with the 3200 pedestal included. 4200 out16 = 1000 above black; 64/1000 = 6.4 %.
  Its other rows check too: 6000 -> 2800 above, 2.3 %; 9000 -> 5800 above, 1.1 %; 20000 -> high segment, 0.1 %.
- H7 and DIGEST section 3 ("64/4200 = 1.5 %") divide by the pedestal. G6-4 stands.

## 3. Why it is not the owner's symptom

| Test | Result |
| --- | --- |
| Visible without a strong push | No. Largest effects are at -5..-7 stops (extra grain) and at -10 stops (lift) |
| Visible at grey or in mid-tones | No. Step 0.6 % at grey, dithered |
| Visible in previews | No (H7 says so itself) |
| Would be called "strange" unprompted | Unlikely. Fits "a bit noisier in deep shadows", not "strange" |

Leads with a visible 12-bit-only effect stay ahead of H7 (binned-mode curve G1-F2, cDNG/MLV storage depth G2-F1, Log table G1-F3).

## 4. Remaining for the Pi

1. Which output and mode the owner saw. Decides whether any hypothesis of this size matters.
2. g from a flat-field pair (2a). With g <= 2 e-/LSB16 the posterisation claim is closed.
3. Grey-ramp 12 vs 16-bit region means (2c).
4. Lens-cap frame, 16-bit Clear HDR: share of samples below 3200. If near zero, the sensor already clips and 2b
   is not 12-bit-only.

## 5. Host test if 2c is fixed

`Apertar-Core/tools/ccmp_table_test.cpp`, in the style of `tools/log_curve_test.cpp`: include
`src/cdng/ClearHdrCcmp.hpp`; assert `expansionTable()[compressionLut()[v]] == v` for every table value;
assert pinned entries (today T[0]=T[201]=3200, T[202]=3201, T[700]=3693, T[701]=3757, T[871]=14505,
T[4095]=65520; after the fix, each mid entry above 701 rises by 32 x 0.988 before rounding); assert the table matches
a copy of libcamera's `setParams` loop for the default params. Build: `g++ -std=c++20 -I. tools/ccmp_table_test.cpp`.
