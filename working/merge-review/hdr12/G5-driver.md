# G5: imx585 driver, 12-bit Clear HDR, `apertar` vs `cinemate-port`

Refs: `@ap` = `origin/apertar` `e5b74d3` (driver the fork-main Clear HDR work was written against, shipped on Apertar-Beta
1.6.0). `@cp` = `cinemate-port` `cd548ef` (HEAD). Line numbers are `imx585.c` unless named. Read with
`git show origin/apertar:imx585.c` and the checked-out file. 52 commits in `origin/apertar..cinemate-port`.

## Verdict in one table

| Item | `@ap` | `@cp` | Changed |
| --- | --- | --- | --- |
| 12-bit Clear HDR modes (colour) | **1**: 3840x2160 all-pixel | **29**: 1920x1080 2x2 binned, 3840x2160, 27 windowed 1x1 crops | **yes** |
| 12-bit Clear HDR modes (mono) | 1: 3840x2160, always | 1: 3840x2160, **only with `ccmp` overlay param** | **yes** |
| CCMP enable gate | none (12-bit + WDR always CCMP) | `clearhdr_ccmp` = colour default on, mono opt-in | **yes** |
| Bus codes in Clear HDR | SRGGB16..SBGGR16, SRGGB12..SBGGR12; mono Y16, Y12 | same list; mono Y12 only with `ccmp` | mono only |
| Depth registers for HDR-12 | ADBIT 0x02, MDBIT 0x01, CCMP_EN 0x01 | same (MDBIT 0x01 also rewritten at stream on) | no |
| CCMP1_EXP / CCMP2_EXP default | 500 / 11500 | 500 / 11500 | no |
| ACMP1_EXP / ACMP2_EXP default | menu 6 (1/64) / menu 4 (1/16) | same | no |
| EXP_TH_H / EXP_TH_L | 0x0FFF / 0x0000 | same | no |
| Blend (EXP_BK) default | menu 0 (HG 1/2, LG 1/2) | same | no |
| Gain adder (EXP_GAIN) default | menu 2 (+12 dB) | same | no |
| BLKLEVEL (V4L2_CID_BRIGHTNESS) | 50 (= 200 at 12 bit) | same | no |
| Analogue gain range in HDR | 0..80 | same | no |
| Exposure range | 2 .. VMAX-16 | same | no |
| HMAX floor in Clear HDR | none; table 440 at 1039.5 MHz, 396 at 1188 MHz | floor 550 x lane_scale | yes (only above 891 MHz link) |
| VMAX in Clear HDR | x2 (4500 full field; crops (h+72)x2) | x2 (4500 full field; crops (h+70)x2) | crops only, 2 rows |
| Windowed 2x2 crops in HDR-12 | n/a (did not exist in HDR) | off; module param `clearhdr_windowed_binning` opens 33 | new |

Every register default that a fixed linearisation table depends on (knees, slopes, pedestal) is **unchanged**. What changed
is **which sensor modes exist** in 12-bit Clear HDR (1 -> 29 on colour), and the mono gate.

## 1. Modes offered in 12-bit Clear HDR

### `@ap`: one mode

- `get_mode_table()` colour, 12-bit codes, `clear_hdr` set: `*mode_list = &supported_modes[10]; /* 4K 12-bit only */`
  `*num_modes = 1;` (`imx585.c:1419-1434@ap`). Comment there: "the 1920x1080 binning mode in Clear HDR only supports
  16-bit output ... the part returns BLC if asked". **Confirmed.**
- 10-bit codes in Clear HDR also route to that 4K 12-bit entry (`imx585.c:1425-1431@ap`). **Confirmed.**
- Mono Y12 + WDR -> `supported_modes[10]`, no gate (`imx585.c:1391-1394@ap`). **Confirmed.**
- Origin of the restriction: commit `bb53099` "Hide 12-bit binned mode in Clear HDR - sensor doesn't support it", in
  `@ap` history.

### `@cp`: 29 modes on colour

- Range `[IMX585_MODE_1080P_12BIT, IMX585_MODE_CROP_1440X1080_HDR12]` (`imx585.c:3062-3094@cp`):

  ```c
  *mode_list = &supported_modes[IMX585_MODE_1080P_12BIT];
  *num_modes = clearhdr_windowed_binning ?
      IMX585_MODE_4K_16BIT_HDR - IMX585_MODE_1080P_12BIT :
      IMX585_MODE_CROP_1440X1080_HDR12 - IMX585_MODE_1080P_12BIT + 1;
  ```
- Table entries 0..28 (parsed from `supported_modes[]`, `imx585.c:1064@cp` on; order pinned by
  `static_assert`s `imx585.c:1016-1023@cp`). **Confirmed.**

| idx | Advertised | Binning | Sensor window (left, top, w x h) | Reg list |
| --- | --- | --- | --- | --- |
| 0 | 1920x1080 | 2x2 | full 3840x2160 | `mode_1080_regs_12bit` (ADDMODE 0x01, DIG_CLP_VSTART 0x02) |
| 1 | 3840x2160 | 1x1 | full | `mode_4k_regs_12bit` (identical to `@ap` apart from macro spelling) |
| 2-4 | 2880x2160, 2160x2160, 2976x2160 | 1x1 | (480,0), (840,0), (432,0) | `mode_window_12bit_1x1_regs` + `imx585_program_window()` |
| 5-14 | 3840x2072, 2032, 2024, 1920, 1744, 1728, 1632, 1608, 1536, 1504 | 1x1 | full width, top 44..328 | same |
| 15-17 | 1920x1040, 1920x1008, 1920x800 | 1x1 | left 960, centred | same |
| 18-27 | 2048x1152, 1104, 1080, 1024, 928, 920, 872, 856, 816, 800 | 1x1 | left 896, centred | same |
| 28 | 1440x1080 | 1x1 | (1200, 540) | same |

- Mono: Y12 + WDR -> 4K only, and only if `clearhdr_ccmp` (`imx585.c:3015-3024@cp`). **Confirmed.**
- 10-bit codes in Clear HDR now return no modes on colour (`imx585.c:3101-3108@cp`). **Confirmed.**
- `clearhdr_ccmp = !mono || of_property_read_bool(..., "sony,clearhdr-ccmp")` (`imx585.c:4641-4643@cp`); overlay adds
  `ccmp = <&cam_node>,"sony,clearhdr-ccmp?";` (`imx585-overlay.dts:138@cp`, the only overlay change). Probe logs
  `ClearHDR 12-bit CCMP: enabled (colour: default-on)`. **Confirmed.**
- APERTAR.md's count (29 modes for 12-bit Clear HDR, "1920x1080 (2x2 binned), 3840x2160 and the 27 crops at 1x1; no 2x2
  crops") matches the code. **Confirmed.**

### The four named commits

| Commit | What it did to HDR-12 |
| --- | --- |
| `70bdb26` gate 12-bit CCMP behind a dtoverlay param | Added `sony,clearhdr-ccmp` / `clearhdr_ccmp`; HDR-12 needed the param on both variants |
| `b6a6f5b` default 12-bit CCMP on for colour | Colour no longer needs `ccmp`; message: "Desk-only: needs the colour-rig gate ... before this branch is pinned anywhere" |
| `c1350b0` offer the binned 1080p mode in colour HDR-12 | Reverses `@ap`'s `bb53099` for colour, on the strength of "2026-08-10 golden captures"; message: "Desk-only: the colour-rig gate must include one binned 12-bit CCMP capture ... before this branch is pinned" |
| `00059f6` keep HDR-12 off the windowed 2x2 crops | Range ends at the 1x1 1440x1080 entry; the 2x2 crops had silently been HDR-12 modes since WP-585-6 |

README (`README.md:162-170@cp`, the `cinemate-7modes` matrix) records a hardware pass on 2026-08-31 of "all seven modes clean"
at blend menu 5, which includes binned 1920x1080 12-bit Clear HDR + CCMP on colour (`README.md:167`, `:250-255`). That is the
only hardware record for binned HDR-12. **No record exists for any windowed 1x1 crop in 12-bit Clear HDR**: `fdd767a`
validated 1x1 crops at RAW16 only (APERTAR.md "Validation"); `00059f6` infers 12-bit from RAW16 ("The 12-bit CCMP path reads
the same pixels through the same window"). **Confirmed** (absence of record in repo and commit messages).

## 2. Media bus code and bit depth

- `codes_clearhdr[]` order unchanged: four 16-bit Bayer codes, then four 12-bit Bayer codes; mono Y16, Y12 (`imx585.c:1215-1230@ap`,
  `imx585.c:2746-2762@cp`). `imx585_get_format_code()` returns the requested code unchanged, no flip adjustment, both branches.
  Colour falls back to `codes_clearhdr[0]` = SRGGB16 for any code not listed. **Confirmed, unchanged.**
- 12-bit Clear HDR: format height 2160 (no OB rows advertised), RAW12 on the wire; ADBIT 0x02, MDBIT 0x01 from the mode
  table, CCMP_EN 0x01 written after `common_clearHDR_mode` (`imx585.c:4154-4158@cp`; `@ap` writes CCMP_EN only,
  `imx585.c:2243-2245@ap`, MDBIT already 0x01 from the table). Same register result. **Confirmed.**
- New in `@cp`: if Clear HDR is on, the code is 12-bit and `clearhdr_ccmp` is false (mono without `ccmp`), stream on fails
  with `-EINVAL` and dmesg `12-bit ClearHDR CCMP requested without ccmp overlay flag (mono is opt-in)` (`imx585.c:4159-4162@cp`).
  `imx585_get_format_code()` coerces mono Y12 + WDR to Y16 in that case (`imx585.c:3135-3141@cp`). **Confirmed.**

## 3. CCMP, blend, gain adder: registers and V4L2 controls

`common_clearHDR_mode[]` is byte-identical between the branches (`imx585.c:484-519@ap` vs `524-559@cp`, diffed). It writes
WDMODE 0x10, COMBI_EN 0x02, EXP_GAIN 0x3081 = 0x02, EXP_TH_H 0x0FFF, EXP_TH_L 0, EXP_BK 0x00, ACMP2 0x04, ACMP1 0x06.
It does **not** write CCMP1_EXP / CCMP2_EXP; those come only from the control.

At stream on, `__v4l2_ctrl_handler_setup()` runs after the base tables (`imx585.c:4186@cp`, `2271@ap`), so the control
values below are what the sensor runs with, whatever the table wrote. Control configs (`imx585.c:3646-3756@cp`) diff
empty against `1780-1890@ap`; menus diff empty.

| Control (CID = `V4L2_CID_USER_BASE + 0x2000 + n`) | n | Register | Default | Active when | Who writes it on Apertar |
| --- | --- | --- | --- | --- | --- |
| HDR Data Selection Threshold (u16[2]) | 0 | EXP_TH_H 0x36d0 / EXP_TH_L 0x36d4 | {0x0FFF, 0} (`hdr_thresh_def`, memcpy at `imx585.c:3905@cp`) | WDR | Core `applyImx585HdrControls` (4095 / 0) |
| HDR Data Blending Mode (menu 0..7) | 1 | EXP_BK 0x36e2 | 0 | WDR | Core (default 5) |
| HDR Gradient Compression Threshold (u32[2]) | 2 | CCMP1_EXP 0x36e8 / CCMP2_EXP 0x36e4 (24-bit) | {500, 11500} (`grad_thresh_def`, `imx585.c:3688`, memcpy `3907`) | WDR and ccmp (`@cp`); WDR (`@ap`) | nobody: driver default governs |
| HDR Gradient Compression Ratio Middle (ACMP1) (menu 6..11) | 3 | ACMP1_EXP 0x36ee | 6 = 1/64 | same | nobody |
| HDR Gradient Compression Ratio High (ACMP2) (menu 0..5) | 4 | ACMP2_EXP 0x36ec | 4 = 1/16 | same | nobody |
| HDR Gain Adder (dB) (menu 0..5) | 5 | EXP_GAIN 0x3081 | 2 = +12 dB | WDR | Core (default 1 = +6 dB) |
| HCG Enable | 6 | FDG_SEL | 0, forced 0 in WDR | not WDR | - |
| `V4L2_CID_WIDE_DYNAMIC_RANGE` | std | selects tables | 0 | always | Core `set_clear_hdr` via libcamera |
| `V4L2_CID_BRIGHTNESS` | std | BLKLEVEL 0x30dc | 50 | always | nobody found |

All **confirmed** unchanged. The only control change is activation: `@cp` marks the three gradation controls inactive when
`clearhdr_ccmp` is false (`imx585_activate_hdr_controls`, `imx585.c:2921-2933@cp`). Inactive controls are still readable and
still re-applied by the handler setup.

Cross-check against the fixed curves (read only to compare numbers, other agents own these files):

| Consumer | Knees | Slopes | Pedestal | Source of values |
| --- | --- | --- | --- | --- |
| Driver default | 500 / 11500 | ACMP1 6, ACMP2 4 | BLKLEVEL 50 -> 200 @12 bit | `imx585.c@cp` as above |
| Core `src/cdng/ClearHdrCcmp.hpp@cinemate-port` | 500 / 11500 (`:25-26`) | 6 / 4 (`:27-28`) | 200 (`:29`) | hard-coded |
| libcamera `pisp.cpp@apertar` | read live from CID n=2 | read live from n=3, n=4 (fallback 2 / 6 if unreadable, `:3003-3004`) | `V4L2_CID_BRIGHTNESS x 4` (`:3023`) | sensor controls |

They agree. No driver commit in `origin/apertar..cinemate-port` changes a knee, slope or pedestal. **Confirmed.**
(The libcamera fallback slopes 2 / 6 are the pre-fix prohibited values; they apply only if the controls cannot be read.)

Note: commit `479117e` ("valid CCMP gradation-compression ratios") is in neither branch; the same fix reached `@ap` as
`1ac3cec` / `30ec768`, which both branches share. **Confirmed** (`git merge-base --is-ancestor`).

## 4. Black level

- `IMX585_BLKLEVEL_DEFAULT 50` (`imx585.c:159@cp`, `149@ap`), written at stream on (`imx585.c:4071@cp`, `2164@ap`) and again
  via `V4L2_CID_BRIGHTNESS` (default 50, range 0..0xFFFF, clamped to 4095 on write). Unchanged. **Confirmed.**
- Digital clamp off (0x3458 = 0) in both. **Confirmed.**
- The "Known issue: ClearHDR mode leaves ~19 OB rows at the top of the cropped buffer, regardless of PIX_VST" comment is in
  both branches (`imx585.c:2223-2232@ap`, `4138-4147@cp`). On `@ap` it could only touch the 4K HDR-12 mode. On `@cp` it applies
  to 28 more HDR-12 modes, 27 of them sensor-windowed by `imx585_program_window()` (`vst = 12 + crop.top`,
  `imx585.c:2962@cp`). **Confirmed** that the comment exists; whether the OB band appears is **unconfirmed**.

## 5. Exposure, gain, timing limits

| Limit | `@ap` | `@cp` |
| --- | --- | --- |
| Analogue gain max in WDR | 80 (`IMX585_ANA_GAIN_MAX_HDR`) | 80 |
| Gain min in WDR | 0 (HCG forced off) | 0 |
| Exposure | 2 .. VMAX - 16 (`IMX585_SHR_MIN_HDR`) | same |
| VMAX full field, WDR | 2250 x 2 = 4500 | 4500 (4K and binned 1080) |
| VMAX windowed crop, WDR | (h + 72) x 2 | (sensor rows + 70) x 2 (`imx585.c:618`, `3283-3292`) |
| HMAX, 4-lane, 720 MHz (overlay default) | 660 | 660 (`HMAX_table_4lane_4K_12bit`) |
| HMAX at 891 MHz | 550 | 550 |
| HMAX at 1039.5 / 1188 MHz, WDR | 440 / 396 | 550 (floor `IMX585_HMAX_MIN_CLEARHDR`, `imx585.c:121`, `3313-3314`) |

- The 2x2 binned 1080p entry uses the same HMAX as 4K in Clear HDR (`.min_hmax = 366` is overwritten by the table, hmax_div 1),
  so binned HDR-12 does not run faster than 4K HDR-12.
- At the overlay default link (720 MHz, `imx585-overlay.dts:77-78`), full-field Clear HDR max frame rate is
  74.25 MHz / (660 x 4500) = 25.0 fps, both branches. **Confirmed** by arithmetic from `IMX585_PIXEL_RATE 74250000`
  (`imx585.c:221@cp`).
- Sensor rule in the driver's own comment (`imx585.c:171-178@cp`, sum rule at `:174`): `9.6 dB <= GAIN + EXP_GAIN <= 29.1 dB` for built-in
  combination. The driver does not enforce it. With Core's default adder +6 dB (`include/apertar/core/Types.hpp:206@cinemate-port`,
  same on fork main), GAIN codes 0..11 (ISO 100..~150) are below the lower bound and codes above 77 above the upper. With the
  driver default +12 dB the window is codes 0..57. Unchanged between branches and unchanged between fork main and the port.
  **Confirmed** (code); effect on the picture **unconfirmed**.

## 6. The WP-585-9 gate (`tools/clearhdr-gate/`)

- Built to detect: a **sensor-windowed, 2x2-binned** readout in 12-bit Clear HDR returning the optical-black **pedestal**
  instead of an image (WP-585-8 showed that failure at RAW16: 98.8-99.5 % of pixels at one value, flat row means).
  `pedestal_check.py` reads cinepi-raw DNGs (12-bit packed or 16-bit), skips the top 24 rows (reported separately as "top rows"),
  and prints `PEDESTAL` / `REAL` / `UNCLEAR` per frame. **Confirmed** (README, script header).
- Passed: **no**. No commit after `90eef64` records takes; the module parameter is still in HEAD (`imx585.c:1039-1042@cp`);
  the static_assert comment says the crops stay out "until tools/clearhdr-gate/ clears it" (`imx585.c:1018-1022`); APERTAR.md:
  "nobody has validated them there". **Confirmed.**
- So in the default configuration the gate keeps windowed 2x2 out of HDR-12, and it is not a cause unless the module
  parameter is set on the camera. The gate README lists 12 crops; WP-585-10 (`18c1eb2`) later grew the 2x2 block to 33, and the
  parameter opens all 33 (APERTAR.md says 33). README not updated. **Confirmed.**
- The gate does not test the 27 windowed **1x1** crops that are HDR-12 modes by default. Its take 3 (3840x1920 1x1 HDR-12) is
  only a control. No test exists for them.

## 7. Findings that could produce "strange output" in 12-bit Clear HDR

| ID | Claim | Status | Symptom and where | Settle with |
| --- | --- | --- | --- | --- |
| D1 | `@cp` offers 28 new HDR-12 sensor modes (binned 1080p + 27 windowed 1x1 crops); `@ap` offered only 4K. Fork main's Clear HDR work was only ever run against the 4K mode. | confirmed | Any requested HDR-12 size other than 3840x2160 now runs a different sensor readout: tighter FOV for 1x1 crops (e.g. 1920x1040 is a centred 1920-pixel window, half the FOV of SDR 1920x1036 binned), binned readout for 1920x1080. Seen in file, preview and clip player alike. | On the Pi: `cinepi-raw --list-cameras` or `libcamera-hello --list-cameras` with WDR on; `v4l2-ctl -d /dev/v4l-subdevN --get-ctrl=mode_binning,mode_crop_left,mode_crop_top,mode_crop_width,mode_crop_height` while recording HDR-12 |
| D2 | No hardware record exists for any windowed 1x1 crop in 12-bit Clear HDR; the related "~19 OB rows at top in ClearHDR crop" note is unresolved in both branches. | confirmed (no record); effect unconfirmed | Dark/black band at the top of the frame, or a flat/pedestal frame, only in HDR-12 crop modes; visible in the DNG and in every preview of it. 16-bit is unaffected (it uses its own RAW16 OB allowance). | Record one 12-bit HDR crop (e.g. 3840x1608) and run `python3 tools/clearhdr-gate/pedestal_check.py <take>`; read its "top rows" line |
| D3 | Binned 1920x1080 in 12-bit Clear HDR is re-enabled for colour; `@ap` removed it as "returns BLC". Evidence for colour is one README pass (2026-08-31, Cinemate, blend 5). | confirmed (code), probable (works only at blend 5) | If Core ever applies blend 0, or on a different unit: flat pedestal frame or white/magenta speckle in 1920x1080 HDR-12 only. | Record 1920x1080 HDR-12 on Apertar and run `pedestal_check.py`; `v4l2-ctl --get-ctrl=hdr_data_blending_mode` during the take |
| D4 | Mono: HDR-12 exists only with `dtoverlay=imx585,...,mono,ccmp`; otherwise the format is coerced to Y16 or stream on fails with `-EINVAL`. On `@ap` mono HDR-12 needed no param. | confirmed | Mono only: 12-bit Clear HDR selection yields 16-bit data, no stream, or Core falls back to another mode. | `dmesg | grep 'ClearHDR 12-bit CCMP'`; `grep imx585 /boot/firmware/config.txt` |
| D5 | Driver blend default is menu 0, which the driver README says produces "white/magenta speckle and flat black-level-pedestal frames"; correct output depends on Core writing menu 5 through `applyImx585HdrControls` before stream on. | confirmed (driver), unchanged | If the write is skipped or fails (e.g. subdev not found), HDR-12 and HDR-16 both show speckle or pedestal. Because 16-bit is reported fine, this is unlikely to be the cause. | `v4l2-ctl -d /dev/v4l-subdevN --get-ctrl=hdr_data_blending_mode,hdr_gain_adder_db` during an HDR-12 take |
| D6 | GAIN + EXP_GAIN window (9.6..29.1 dB) is not enforced; Core's adder default +6 dB puts ISO 100..~150 below it and lets HDR codes 78..80 above it. Same as fork main. | confirmed (code), unconfirmed (effect) | Exposure-dependent artefacts in HDR at low or very high ISO, in file and preview. Not branch-specific. | Record HDR-12 at ISO 100 and ISO 400, compare `pedestal_check.py` and visual |
| D7 | `clearhdr_windowed_binning=1` left on the camera would add 33 unvalidated windowed 2x2 crops to HDR-12. | confirmed (mechanism) | Pedestal frames or invalid colour only in 2x2 crop sizes (960- to 1920-wide) in HDR-12. | `cat /sys/module/imx585/parameters/clearhdr_windowed_binning`; `ls /etc/modprobe.d/` |
| D8 | CCMP knees/slopes/pedestal defaults are identical in both branches and match Core's and libcamera's tables. | confirmed | Rules the driver out as the cause of a wrong tone curve, unless something writes the gradation controls (nothing found). | `v4l2-ctl --get-ctrl=hdr_gradient_compression_threshold_16_bit,...` during a take |
| D9 | HDR frame rate ceiling is 25 fps at the default 720 MHz link, both branches. | confirmed | Requesting 30 fps or more in Clear HDR gives a slower actual rate; not branch-specific. | `dmesg | grep Framing` after selecting HDR-12 |

## 8. What the driver authors say (APERTAR.md, README.md)

- APERTAR.md: use `cinemate-port`; `ccmp` is "Mono only: enables 12-bit Clear HDR (CCMP). The colour sensor has it on already";
  HDR-12 family = 29 modes, no 2x2 crops; mono HDR-12 = 1 mode, only with `ccmp`; leave `clearhdr_windowed_binning` off.
  Validation section lists RAW16 crops and the seven original modes only.
- README: blend menu 5 is "the recommended setting"; the driver default stays 0 "deliberately"; "If you are writing against this
  driver, set the blend explicitly." Clear HDR halves the frame rate (`README.md:121`). 12-bit Clear HDR at the top link rate needs
  no further driver change (`README.md:239-241`).

## Open questions for the owner

1. Colour or mono sensor? The `config.txt` overlay line?
2. Which resolution was selected for the 12-bit HDR take? 3840x2160 behaves as on `@ap`; any other size is a new sensor mode.
3. `dmesg | grep imx585` from the camera (CCMP line, gate warning, Framing lines).
