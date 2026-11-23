# G7: how Cinemate treats 12-bit Clear HDR, and what Apertar-Core does differently

Scope: Cinemate `main` 4990afc, cinepi-raw 63a08d5, cinemate-handbook c99ff77, compared with
Apertar-Core `cinemate-port` 01f170c, imx585 driver `cinemate-port` cd548ef, libcamera fork `apertar`
6b0b49f. Read-only. No camera run.

## 1. Does Cinemate offer 12-bit Clear HDR today? No. It is hidden, deliberately.

| Fact | Evidence | Status |
| --- | --- | --- |
| Default is off | `resources/settings/settings_default.jsonc:146@4990afc` `"imx585_clear_hdr_12bit": false`; `settings.jsonc:312`; `src/module/config_loader.py:669` | confirmed |
| The switch decides whether 12-bit Clear HDR modes exist at all | `src/module/sensor_detect.py:1266@4990afc` `if bool(hdr_cfg.get("imx585_clear_hdr_12bit", legacy)): depths.add(12)` | confirmed |
| No switch on the settings page | commit `39034ae` "Take the 12-bit ClearHDR switch off the settings page" | confirmed |
| Shipped imx585 table has 5 modes, no 12-bit Clear HDR | `docs/sensors.md:32-38@4990afc` (0 4K SDR10, 1 HD SDR12, 2 4K SDR12, 3 HD HDR16 1920x1100, 4 4K HDR16 3840x2200) | confirmed |

Why (commit `d606429`, 2026-09-15, "Hide the 12-bit ClearHDR modes; keep every line of code that serves them"):

> ClearHDR's extra range is the ratio between the sensor's high- and low-gain reads, and that ratio only
> survives inside the sensor's documented combination window. ... Past gain code ~60 the merge stops
> reaching the top of the container -- at code 80 it reaches 59% of it ... So the 12-bit pair asks for
> the compander, a full-frame CPU preview re-render and the clamp artefacts that come with both, and
> returns less than SDR at the ISOs people shoot. ... Nothing is removed. The driver keeps the modes,
> cinepi-raw keeps the CCMP decompand, the measured per-binning tables and the preview path.

Test docstring, `_test/test_clearhdr_12bit_hidden_renumbering.py:1-17@4990afc`: hiding the pair renumbers
16-bit HD/4K from 5/6 to 3/4; startup re-resolves a stored mode from the capture shape, and a camera parked
on 12-bit Clear HDR lands on 16-bit Clear HDR at the same size (`test_4k_12bit_clearhdr_lands_on_4k_16bit_clearhdr`,
`test_hd_12bit_clearhdr_lands_on_hd_16bit_clearhdr`). Its fixture marks the 12-bit pair as 3840x2160 and 1920x1080.

Earlier doc wording (`git show e8c8af3^:docs/clear-hdr.md:34-39`): "12-bit ClearHDR is off by default because on this
sensor it does not earn its place ... The 12-bit modes also carry the compander and a full-frame CPU preview
re-render." The operator's last verdict on the 12-bit preview: "12 bit doesnt really work now"
(`cinemate-handbook/lessons/hardware-log.md:2823-2834@c99ff77`). It was parked, not solved.

## 2. How cinepi-raw writes a 12-bit Clear HDR DNG

Source: `cinepi/ccmp_lut.hpp@63a08d5`, `cinepi/dng_encoder.cpp@63a08d5`, `cinepi/ccmp_gate.hpp`.

| Item | cinepi-raw | Evidence |
| --- | --- | --- |
| Stored samples | the sensor's 12-bit codes, as delivered (Cinemate's libcamera does not unwrap) | `cinepi/cinepi_raw.cpp:49-57` ("12-bit ClearHDR reaches the ISP still companded") |
| BitsPerSample | 12 | `dng_encoder.cpp:697` `dng_info.bits = 12;` |
| LinearizationTable | 4096 entries, `table[C] = floor(ccmp_inv(b*(C-200))/b + 200 + 0.5)` | `ccmp_lut.hpp:24-30, 307-347` |
| Model | `stored = ccmp(b*L)/b + P`; b = 1 full res, b = 4 for 2x2 binned | `ccmp_lut.hpp:22-30, 276-286` |
| BlackLevel | 200 (table output domain, "KEEP_PEDESTAL") | `ccmp_lut.hpp:66-72, 358`; `dng_encoder.cpp:1535-1545` |
| WhiteLevel (table) | last entry: 63265 full res, 62704 binned | `ccmp_lut.hpp:74-75, 359` |
| WhiteLevel (written) | replaced by the clamp measured on the take's first frame, latched for the take | `docs/clear-hdr.md` (pre-e8c8af3) lines 48-51, 109-112; `cinepi/clip_ceiling.hpp`; hardware-log.md:2858-2900 |
| With Log | CCMP decode composed with the 16-bit log curve; BlackLevel 3200; table = log inverse | `log_lut.hpp:237-265`; `dng_encoder.cpp:1499-1533` |
| Gate | ClearHDR on AND a *trusted* 12-bit sensor mode; untrusted -> no table, loud warning | `dng_encoder.cpp:689-718`; `ccmp_gate.hpp:10-14, 42` |
| Unknown binning | refuses to build a table (no fallback to the register curve) | `ccmp_lut.hpp:59-64, 234-252`; `ccmp_lut.cpp:47-56` |
| No clamp in the table | build fails rather than clip | `ccmp_lut.hpp:53-57, 329-338` |

Curve constants (`ccmp_lut.hpp:91-96, 159-160`):

| Constant | Value | Source |
| --- | --- | --- |
| T1 register (CCMP1_EXP) | 500 | read back from the driver with Clear HDR live |
| T2 register (CCMP2_EXP) | 11500 | same |
| ACMP1 index | 6 -> s1 = 1/64 | same |
| ACMP2 index | 4 -> s2 = 1/16 | same |
| Pedestal P | 200 ("BlackLevel, all 6 modes") | measured |
| T1 effective, b=1 | 500.3389 | measured on two chart sessions (a1 anchor) |
| T1 effective, b=4 | 500.9431 | measured, per mode, "not derivable" |
| Preview clip anchor | 2900 (b=1, measured), 2582 (b=4, derived then confirmed in place) | `ccmp_lut.hpp:139-160` |

Single source of truth named in the header: `innomaker585/ccmp12-lut/tools/ccmp_decode.py` (not in this
container); `tests/ccmp_lut_test.cpp` asserts byte-identical golden tables (`ccmp_lut.hpp:32-35`).

## 3. Artefacts Cinemate saw in 12-bit Clear HDR, and the outcome

| Artefact | What was seen | Cause found | Resolution | Evidence |
| --- | --- | --- | --- | --- |
| Mid-tones crushed magenta | DNG written with companded codes as linear | transfer curve, not gains | LinearizationTable (CCMP decompand) | `ccmp_lut.hpp:8-14`; `handbook/architecture/cinepi-raw.md:229-242` |
| Wrong curve per binning | "Getting the selection backwards is wrong by 2.6x at knee1 and does not look obviously wrong" | compander runs on the binned (summed) signal | two tables, selected on binning; refuse unknown binning | `ccmp_lut.hpp:39-44, 59-64` |
| Mid-segment offset 21 L | register T1 curve short by 0.33 codes (b=1) / 0.23 (b=4) | anchor error, not derivable | measured `kT1Effective` | `ccmp_lut.hpp:98-120` |
| Magenta blown highlights (preview, MJPEG, thumbnail) | equal-code quads at the merge clamp go magenta under WB+CCM | clamp zone floor 2900 (b=1), 2582 (b=4); trigger was unreachable | `desaturateHighlight()` anchored per binning (`f804ee1`); later judged "cosmetics" | hardware-log.md:1667-1732, 2482-2521 |
| Magenta blown highlights in the DNG | "every one of the nine ClearHDR takes is clamped and magenta in the DNG itself", 54.8-89.3% of declared white | WhiteLevel declared at container top; clamp lower | per-take measured WhiteLevel latch (cinepi-raw `96b6811`); ISO held during a take | hardware-log.md:2858-2955 |
| Highlight range collapse at higher ISO | ceiling 4095 up to gain code 60, 3188 at 71, 2408 at 80 | `9.6dB <= GAIN + EXP_GAIN <= 29.1dB` combination window | ISO cap 799 (12-bit), 1585 (16-bit), commit `bbb23e0`; then 12-bit hidden (`d606429`) | hardware-log.md:2523-2578; commit bbb23e0 |
| Hard ceiling ~0.55-0.59 of container in binned | all controls inert at ISO 3200 | measured inside the broken gain region | explained by the row above | hardware-log.md:2426-2480 |
| White/magenta speckles, flat black-pedestal frames | on any Clear HDR mode | shipped HDR blend default (EXP_BK index 0) | blend 5 default | hardware-log.md:1106-1178 |
| Flat black pedestal at launch | still listed as known issue | not found | manual "kick": underexpose briefly | `docs/clear-hdr.md:25-27@4990afc` |
| Binned 12-bit on mono | constant 200 = BLC across the frame | sensor (mono variant) | driver mono path offers 4K only | hardware-log.md:843, 1172; `imx585.c:3004-3021@cd548ef` |
| Windowed 2x2 crops in Clear HDR | 16-bit: OB pedestal instead of image (98.8-99.5% at 3200); 12-bit windowed 2x2 1440x1080 "invalid colour data" | sensor will not window a binned Clear HDR readout | removed from 16-bit (WP-585-8); kept out of 12-bit range (WP-585-9) | hardware-log.md:41-114; `imx585.c:1353-1367@cd548ef` |
| 12-bit "came back on" | settings-editor save deleted keys | editor bug | per-depth switches, settings merge | hardware-log.md:2957-3019; commits 3114014, 7de3065 |
| 12-bit preview cost | ~33 ms/frame CPU re-render | ISP gets companded data | none; parked | hardware-log.md:2322-2377 |

## 4. WP-585-9 (the driver gate)

- Purpose: keep the twelve *windowed 2x2* crops out of the 12-bit Clear HDR mode range until a hardware
  test proves the sensor reads them out. `tools/clearhdr-gate/README.md:1-21@cd548ef`: "Can the IMX585 read a
  sensor-windowed, 2x2-binned window out correctly in 12-bit Clear HDR (CCMP), or does it return the
  optical-black pedestal the way it does at RAW16?" Confirmed.
- Mechanism: table position. `get_mode_table()` hands out `[IMX585_MODE_1080P_12BIT .. IMX585_MODE_CROP_1440X1080_HDR12]`
  for 12-bit Clear HDR (`imx585.c:3086-3091@cd548ef`); static_asserts pin the order (`imx585.c:1017-1024`). Module
  parameter `clearhdr_windowed_binning` reopens the range for the test only (`imx585.c:1026-1042`).
- Handbook: `working/changing-the-sensor-mode-table.md:17-33@c99ff77` ("WP-585-9 exploited this deliberately: the
  windowed 2x2 crops were moved to sit after the HDR-12 crop, which is what keeps them out of Clear HDR").
- What the gate does NOT cover: the full-field 2x2 1920x1080 and the 27 windowed **1x1** crops stay in the
  12-bit Clear HDR range. No hardware-log entry records a 12-bit Clear HDR take in a windowed 1x1 crop
  (grep of `lessons/`, `working/` for 1x1 12-bit HDR crop takes: none). Cinemate hid 12-bit (2026-09-15)
  before the crop family landed (2026-09-20/21), so its operators were never offered them. Probable.
- No gate result is recorded in the handbook. Unconfirmed; settle by `grep -rn "clearhdr-gate\|pedestal_check" cinemate-handbook/lessons`.

## 5. Apertar-Core's approach

`src/cdng/ClearHdrCcmp.hpp@cinemate-port` is identical to `@main` (`git diff origin/main cinemate-port -- src/cdng/ClearHdrCcmp.hpp` empty).

- libcamera fork unwraps the companded raw buffer in place to linear 16-bit, BE and stats both see it
  (`libcamera@apertar:src/libcamera/pipeline/rpi/pisp/pisp.cpp:3092-3104`). Params read live from the subdev:
  GRAD_TH, GRAD_COMP_L/H, BLC from V4L2_CID_BRIGHTNESS x4 (`pisp.cpp:2950-3027`). LUT: `blc16 + inverse(u12-blc12) * (0xFFF0-blc16)/inverse(4095-blc12)` (`ccmp_unwrap.cpp:44-129`).
  No binning parameter: `CcmpUnwrap::Params` = thresh1, thresh2, slope_l_idx, slope_h_idx, blc_u12 (`ccmp_unwrap.cpp:31-40`).
- Core re-packs the linear samples to 12-bit codes with `ccmp::compressionLut()` (`CameraController.cpp:1646-1657@cinemate-port`)
  and attaches `ccmp::expansionTable()` (same formula, constants 500/11500/6/4/200 hard-coded, `ClearHdrCcmp.hpp:24-58`) as
  LinearizationTable, BlackLevel 3200 (`CameraController.cpp:4090-4096`), WhiteLevel = `table.back()` = 65520
  (`CdngEncoder.cpp:1490-1491@cinemate-port`).
- Port offers 29 H12 rows including binned 1920x1080 (row 0) and windowed 1x1 crops
  (`src/camera/Imx585Modes.hpp:78-86@cinemate-port`, `offered()` :169-177 keeps every row >= 1280 px).
- ISO cap 12-bit 720 (`CameraController.cpp:2933-2940`); auto ISO is turned off in Clear HDR (`:3076-3078`).
- Merge knobs: blend 5, gain adder 1, thresholds 4095/0 (`include/apertar/core/Types.hpp:203-206@cinemate-port`), pushed
  at configure (`CameraController.cpp:7076-7084, 7335`). Same operating point as Cinemate.

## 6. Differences that could show as strange output

| # | Difference | 12-bit only? | Symptom and where | Status |
| --- | --- | --- | --- | --- |
| D1 | **Binned HD (1920x1080) decoded with the full-res curve.** cinepi-raw: `L = ccmp_inv(4*(C-200))/4`. libcamera unwrap and Core's table: `L = ccmp_inv(C-200)`, no binning. Codes 325..872 (y 125..672) decode up to ~17x too low; above ~872 the two agree within 5%. Computed: code 400 -> Apertar 200, cinepi b=4 3384; code 700 -> 500 vs 8184; code 2412 -> 36156 vs 35576. | yes | HD 12-bit Clear HDR only. Shadows to mid-tones squashed into L 125..500 then a steep ramp: dark, contrasty, posterised mids with colour casts (WB applied to non-linear data). Same distortion in the cDNG (table matches libcamera), MLV (libcamera samples), HDMI/WebUI preview (BE gets the unwrapped buffer) and AE (stats from the same buffer: under-read mids -> AE pushes exposure up if shutter is auto). 4K and 1x1 crops unaffected. | probable (code confirmed; the b=4 model is cinepi-raw's hardware-measured claim, `ccmp_lut.hpp:22-44`). Settle: record HD 12-bit Clear HDR and HD 16-bit Clear HDR of one static grey-step chart, same ISO/shutter; plot DNG linear (after table) vs 16-bit per patch. Needs the Pi. |
| D2 | **WhiteLevel at container top (65520), no clamp latch.** Cinemate found every Clear HDR take magenta in the DNG until it latched the measured clamp. | no (16-bit Core also writes container white) | Raw converter: blown highlights magenta/pink; converter skips highlight reconstruction. Worse in binned (clamp 54.8% of container). | confirmed difference (`CdngEncoder.cpp:1490-1491`). Weak as the explanation for a 12-bit-only report, because 16-bit should show it too. Settle: open a 12-bit and a 16-bit DNG of a blown lamp in a converter; read raw max per channel vs WhiteLevel tag (`exiftool -WhiteLevel`, `rawpy`). |
| D3 | **Windowed 1x1 crops offered in 12-bit Clear HDR.** Never offered by Cinemate; no hardware record of a 12-bit Clear HDR 1x1 crop take. WP-585-9 gates only windowed 2x2. | yes | Mode-level: a crop that may return pedestal/invalid data or wrong colour; operator sees black/flat or odd-coloured frame in a 12-bit HDR crop. | unconfirmed. Settle: on the Pi, record 3840x1920 and 1440x1080 in 12-bit Clear HDR and run `python3 tools/clearhdr-gate/pedestal_check.py <takes>` (driver repo). |
| D4 | **Table attached on settings alone.** `metadataFromRequest` attaches the 4096-entry table and black 3200 when `clearHdrStoresCodes12(settings)` (`CameraController.cpp:4090`); the code mapping runs only if the stream is unpacked 16-bit-container 12-bit (`:9491-9492`). Storage depth is 12 regardless (`:1682-1687`). cinepi-raw learned to refuse the table when the mode is not trusted ("a 12-bit request landing on the real 16-bit sensor mode", `handbook/architecture/cinepi-raw.md:239-242`). | yes | If the stream is packed or 16-bit while settings say 12-bit Clear HDR: linear 16-bit samples truncated to 12 bits under a CCMP table -> wrapped highlights / noise-like garbage in the cDNG. Preview fine. | unconfirmed (reachability). Settle: log `rawInfo.packing`/`bitDepth` at take start in 12-bit Clear HDR; check DNG with `exiftool -BitsPerSample -LinearizationTable`. Cross-check with G2. |
| D5 | **Fixed constants vs live controls.** Core's table hard-codes 500/11500/6/4/200; libcamera reads them live (`pisp.cpp:2994-3023`). Cinemate also hard-codes but uses measured T1 (500.34/500.94). | yes | Only if something writes GRAD_TH/COMP or BRIGHTNESS: Core's compressionLut no longer inverts libcamera's LUT -> banding/steps in the cDNG. Core writes neither (`git grep` finds only DATASEL_TH, blend, gain adder: `CameraController.cpp:7034-7084`). The 21 L T1 offset vs cinepi is negligible. | confirmed: not triggered by Core today. |
| D6 | **Preview path.** Cinemate re-renders 12-bit preview on CPU from raw (ISP got companded data); Apertar's ISP gets libcamera-unwrapped data. | yes | Apertar preview should look like 16-bit preview (pink clamped highlights only), except in binned HD (D1). | probable. |
| D7 | **ISO window.** Cinemate cap 799, Apertar 720; both inside the combination window derived for +12 dB EXP_GAIN. Both actually ship gain adder 1 (+6 dB, `imx585.c:3627-3628` writes the menu index to 0x3081). | yes | None expected: cap is conservative. Above the cap (if `clear_hdr_iso_max_12bit` raised in apertar-hardware.conf) highlights flatten and go pink. | confirmed values; effect probable. |
| D8 | **Flat black-pedestal launch.** Still an open known issue in Cinemate for any Clear HDR mode. | no | Whole frame flat at black level after entering Clear HDR, in every output; fixed by briefly underexposing. | confirmed in Cinemate docs; whether Apertar hits it: unconfirmed. Settle: switch into 12-bit Clear HDR 10 times, record 1 s each, check DNG mean vs 3200. |

## 7. Open questions

- Is cinepi-raw's b=4 model right? Its only independent cross-check in the handbook (2412 code vs 35968 in 16-bit
  binned, hardware-log.md:2440-2444) sits on the top segment, where b=1 and b=4 agree within 2%; it does not
  discriminate. The low/mid segment is where D1 lives. The measurement source `innomaker585/ccmp12-lut` is not in this container.
- Was the libcamera claim "Lux within ~5% of 16-bit" (`ccmp_unwrap.cpp:73-76`) taken at 4K or binned HD?
- Which Clear HDR depth was EXP_GAIN at during Cinemate's 2026-09-14 ISO sweep: the entry says +12 dB (0x02),
  the shipped default is adder 1 (+6 dB).
- Which mode was the owner in? D1 and D3 depend on HD or crop modes; D2 and D8 are not 12-bit specific.
