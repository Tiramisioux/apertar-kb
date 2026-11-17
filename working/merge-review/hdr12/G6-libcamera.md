# G6: what the libcamera fork hands Core in IMX585 12-bit Clear HDR

Scope: libcamera fork `/home/user/tiramisioux/libcamera`, branch `apertar` `6b0b49f` (base `7e9fef0`).
Cross-checked against driver `cinemate-port` `cd548ef` and Core `cinemate-port` `01f170c`.
Refs below: `@6b0b49f` (libcamera), `@cd548ef` (driver), `@01f170c` (Core).

## Answer in one table

| Question | Answer | Status |
| --- | --- | --- |
| Does Core get companded codes or linear values? | Linear (de-companded, then stretched) values. libcamera rewrites the raw buffer in place before it reaches Core | confirmed in code |
| Container | Unpacked 16-bit, little-endian u16, one sample per u16. Pixel format reported after `configure()` = 16-bit unpacked Bayer (`SRGGB16` for colour) even though Core asked for `SRGGB12_CSI2P` | confirmed in code |
| Value range | Black 3200 (with BLKLEVEL 50), white 65520 (0xFFF0). All codes <= 201 map to 3200 | confirmed (code + host test) |
| Curve constants | Read once at `configure()` from the sensor's V4L2 controls (GRAD_TH, GRAD_COMP_L/H, BRIGHTNESS). Not per frame | confirmed in code |
| Core's assumption | Core assumes exactly this (linear 16-bit, black 3200, white 65520) and re-compresses to 12-bit codes + LinearizationTable for cDNG | confirmed in code |
| Curve applied twice or never? | Neither, at driver defaults. Core's table is bit-identical to libcamera's LUT (host test, 4096/4096 entries) | confirmed (host test) |

The libcamera/Core boundary is consistent. The suspects are further out: the curve geometry itself (G6-6),
what happens to black (G6-7, G6-8), and consumers that skip the LinearizationTable (G6-7).

## 1. When the unwrap is armed

`pisp.cpp:1821-1823@6b0b49f`:

```
} else if (!qbc_ && sensor_->model() == "imx585" &&
	   MediaBusFormatInfo::info(rpiConfig->sensorFormat_.code).bitsPerPixel == 12 &&
	   initCcmpUnwrap()) {
```

| Condition | Where | Note |
| --- | --- | --- |
| Not the 14/16-bit branch (no `Needs14bitUnpack`/`Needs16bitEndianSwap`) | `pisp.cpp:1813-1815`, flags set `1744-1759` from sensor bpp | 16-bit Clear HDR takes the other branch: SW stats only, endian swap, no unwrap |
| No QBC | `1813`, `1821` | IMX585 has no QBC control |
| Sensor model name `imx585` | `1821` | |
| Sensor mbus code is 12 bpp | `1822` | Driver: 12-bit Clear HDR = `MEDIA_BUS_FMT_S*12_1X12` with WDR=1, `imx585.c:2907-2918@cd548ef` |
| `wide_dynamic_range` = 1 at configure time | `initCcmpUnwrap()` `2975-2988` | Core writes WDR before CameraManager starts, `CameraController.cpp:7003-7004@01f170c` |
| All four controls exist: WDR, `0x00982902` GRAD_TH, `0x00982903` GRAD_COMP_L, `0x00982904` GRAD_COMP_H | `2974-2979` | Driver ids `V4L2_CID_USER_BASE+0x2000+2..4`, `imx585.c:30-39` |

No env var arms it. `QBC_RAW_CPU_WORKER=1` (`pisp.cpp:878-890`) only moves the same work to a worker
thread (`RawCpuWorker::process`, `814-834`). Core's tree does not set that variable (grep, no hit).
`LIBCAMERA_RPI_PISP_CONFIG_DUMP` and `QBC_STATS_DUMP_PREFIX` are debug dumps only.

## 2. It rewrites the application's raw buffer (comments say it does not)

| Fact | Evidence |
| --- | --- |
| `Cfe::Output0` is the app's raw stream (External flag) | `pisp.cpp:1735-1736@6b0b49f` `rawStreams[0].cfg->setStream(&cfe_[Cfe::Output0]); ... setFlags(StreamFlag::External)` |
| Output0 is the FE image node | `pisp.cpp:1364,1378` `rp1-cfe-fe_image0` |
| Non-worker path: in place, on Output0 | `pisp.cpp:3100-3104` `ccmpUnwrap_->process(rawPx + y * strideU16, width);` called from `cfeBufferDequeue` `2262-2266` |
| Worker path: same, on the same buffer | `pisp.cpp:825-829`, job filled in `submitRawCpuJob` `2124,2141` |
| `process()` writes back | `ccmp_unwrap.cpp:157-166@6b0b49f` (`vst1q_u16(buf + i, ...)`, `buf[i] = lut_[...]`) |
| Runs before the BE and before the request completes | `tryRunPipeline` waits for the job, `3116`; worker path waits on `cpuPending`, `1105-1112` |
| Runs once per frame | job rotates when Output0+Stats are present, `1087-1102`, `2188-2191`; IMX585 has no embedded data, so no third buffer re-triggers it |

Stale comments that say the raw buffer is NOT rewritten: `ccmp_unwrap.h:22-26`, `ccmp_unwrap.cpp:5-6`,
`pisp.cpp:1042-1048`, `1824-1831`, `3064-3067`. The header's own last paragraph (`ccmp_unwrap.h:42-44`) and
`pisp.cpp:3091-3099` say the opposite and match the code. Core's comment matches the code:
`ClearHdrCcmp.hpp:9-13@01f170c` "expands every raw frame back to linear 16-bit before Core sees it".
Cleanup item for the fork, not a bug in itself.

## 3. Format and value range the app sees

`pisp.cpp:1870-1898@6b0b49f`: CFE forced to `mbusCodeUnpacked16()` (`125-131`, same Bayer order, 16 bit,
no packing), then the app's `StreamConfiguration` is overwritten after `configure()`:
`pixelFormat = cfeFormat.fourcc.toPixelFormat(); stride = ...bpl; frameSize = ...size`.

Core reads that after `configure()` (`CameraController.cpp:8584-8623@01f170c`): `formatToRawView` gives
`Bits16 / Unpacked`; `storageRawBitDepthForSettings` gives `Bits12` for Clear HDR 12 + cDNG
(`1682-1688`), so `rawStreamInfo_.bitDepth = Bits12`, 2 bytes per sample (`8618-8622`), and
`copy.mapCodes12` becomes true (`9491-9492`). Consistent.

LUT (`ccmp_unwrap.cpp:214-227`): `LUT[c] = 3200 + inverse(c - 200) * (65520 - 3200) / inverse(3895)`.
Host test (driver defaults, see section 5):

| Code | Linear out |
| --- | --- |
| 0..201 | 3200 |
| 700 / 701 / 702 | 3693 / 3757 / 3820 (knee 1 in out domain: 3694) |
| 870 / 871 / 872 | 14442 / 14505 / 14576 (knee 2: 14562) |
| 4095 | 65520 |

The "natural scale" wording in the log line (`ccmp_unwrap.cpp:229`) and the `u12 << 4` claim
(`ccmp_unwrap.h:33-35`) are stale: the table is stretched by 62320/63084 = 0.988 everywhere.

## 4. Curve constants: from the sensor, once

`initCcmpUnwrap()` `pisp.cpp:2990-3026@6b0b49f`:

| Param | Source | Fallback |
| --- | --- | --- |
| thresh1, thresh2 | GRAD_TH u32[2] | 0, 0 if the array read fails |
| slope_l_idx (middle segment) | GRAD_COMP_L menu index | 2 |
| slope_h_idx (high segment) | GRAD_COMP_H menu index | 6 |
| blc_u12 | `V4L2_CID_BRIGHTNESS` x 4 | 50 x 4 = 200 |

Driver defaults `@cd548ef`: GRAD_TH `{500, 11500}` (`imx585.c:3688`, copied in at `3907-3908`),
COMP_L def 6 = 1/64 (`3719-3727`), COMP_H def 4 = 1/16 (`3730-3738`), BRIGHTNESS def 50 (`159`, `3847-3848`).
Stream start also writes ACMP2=0x04, ACMP1=0x06 from the table (`imx585.c:557-558`) and then
`__v4l2_ctrl_handler_setup` (`4186`). Slope semantics `slope = 2^-idx` match the driver's menu labels
(`imx585.c:355-358`).

The fallbacks (2 and 6) are the old, swapped values the driver comment calls prohibited (`imx585.c:3712-3714`).
They only apply if the controls exist but cannot be read. Low risk, cleanup item.

The LUT is not rebuilt during streaming. `updateSensorBlackLevel()` (`2927-2948`) updates only the stats BLC.
A change of BRIGHTNESS or of the gradient controls after `configure()` leaves the unwrap on the old curve.

## 5. Core versus libcamera: bit-exact at defaults, drifts otherwise

Core hard-codes the defaults: `ClearHdrCcmp.hpp:24-30@01f170c` (knee1 500, knee2 11500, slope1 6,
slope2 4, black 200). Core writes none of these controls (grep of `Apertar-Core/src`, `tools`, `scripts`,
`Apertar-UI/src` for `BRIGHTNESS`, `BLKLEVEL`, `GRAD_TH`, `0x00982902`, `gradient_compression`: no hit).

Host test (scratchpad `g6/t.cpp`, copy of `ccmp_unwrap.cpp:151-227` vs `ccmp::expansionTable()`):

| Case | Values Core's table cannot reproduce | Max error (u16) |
| --- | --- | --- |
| Driver defaults | 0 of 4096 (round trip exact) | 0 |
| BRIGHTNESS 40 | 3831 | 640 |
| BRIGHTNESS 60 | 3835 | 65 |
| BRIGHTNESS 64 | 3906 | 63 |
| ACMP1 7 | 3183 | 63 |
| ACMP2 5 | 3196 | 66 |

So "applied twice / never" does not happen at defaults. If anything on the Pi changes BLKLEVEL or the
gradient controls (a script, `v4l2-ctl`, an overlay, another app), Core's re-compression picks wrong codes:
tone steps and a black offset in the cDNG. Settle on the Pi:
`journalctl -b | grep -E "CcmpUnwrap: rebuilt LUT|CCMP stats linearisation"` must show
`T1=500 T2=11500 slope_L=1/64 slope_H=1/16 blc_u12=200 ... LUT[4095]=65520`.

## 6. Code allocation: the curve has almost no codes in the mid-tones

Read directly from the shared curve (libcamera and Core agree):

| Segment (linear above black) | Codes | Stops (approx) | Step per code |
| --- | --- | --- | --- |
| 0..494 (below -7 stops from clip) | 200..701 | ~9 | 1 LSB |
| 494..11362 (-7 to -2.5 stops) | 701..872 = 171 codes | ~4.5 | 63-64 LSB |
| 11362..62320 (top 2.5 stops) | 872..4095 = 3223 codes | ~2.5 | 16 LSB |

Host test step sizes: linear 4200 = 6.4 % of signal per code, 6000 = 2.3 %, 9000 = 1.1 %, 20000 = 0.1 %.
The middle segment is compressed 4x harder than the highlights (1/64 vs 1/16). About 38 codes per stop
from -7 to -2.5 stops below clip. Normal skin and mid-grey land in that band.

If the sensor really applies these slopes: posterisation/banding in lower mid-tones and shadows-to-mids
transitions of the recorded file and of the preview; the 16-bit mode has none of this. If the sensor's
real ACMP encoding or knee units differ from the driver's menu (for example knee units are 17-bit input
while libcamera treats the identity segment as output codes 1:1), both libcamera and Core invert the wrong
curve: tonal kinks near linear 3694 and 14562, hue shifts where R/G/B cross a knee at different levels.
Neither is checked against the sensor's transfer curve anywhere I found; the KB's "validated against a
driver readback" (`working/clearhdr-12bit-answer.md:99`) is a readback of control values.

Settle (needs the Pi): record the same static scene (step chart or a slow ramp, fixed exposure, fixed
gain) in 16-bit and 12-bit Clear HDR, linearise both, scatter-plot pixel by pixel. A straight line means
the model is right; kinks at the two knees mean it is not. A histogram of raw 12-bit codes (before libcamera,
e.g. with the unwrap disabled) showing pile-ups at 701 and 872 also tells it.

## 7. Black: sub-black noise is clipped, black is stored as code 0

| Fact | Evidence |
| --- | --- |
| Every code below the pedestal maps to the black value | `ccmp_unwrap.cpp:218-219` (`out_post_blc <= 0 ? 0`) |
| With the 0.988 stretch, codes 200 and 201 also map to 3200 | host test `LUT[201]=3200` |
| Core's inverse maps 3200 to code 0 (lowest code reaching 3200) | `ClearHdrCcmp.hpp:69-80`; host test `comp[3200]=0`, `comp[3201]=202` |
| cDNG black tag is 3200 on the table's output scale | `CameraController.cpp:4090-4096@01f170c` |

Effects:

- Read correctly (with LinearizationTable): the noise floor is half-rectified. Mean black sits above 3200,
  so blacks look lifted and flat compared with SDR 12-bit, which keeps sub-black noise. Probable,
  visible in the raw converter.
- Read without the table: stored codes run 0..4095 with black at 0 while the BlackLevel tag says 3200 and
  white is 65520. Any consumer that decodes the samples but skips tag 50712 (a thumbnail or preview
  generator, the clip player, the port's WebUI player, a converter that ignores the table) shows an almost
  black frame, or with an assumed 12-bit black of 200 a flat, crushed-shadow image. Code fact confirmed;
  whether a player skips the table belongs to the playback agents. Settle: `exiftool -LinearizationTable
  -BlackLevel -WhiteLevel` on a 12-bit Clear HDR cDNG, then check each renderer for tag 50712.
- Per-channel pedestals: tuning `imx585.json:6-10@6b0b49f` R 3301, G 3321, B 3240 (u16 of 12-bit,
  i.e. +6.3 / +7.6 / +2.5 codes above 200). After unwrap they become about 3206 / 3207.5 / 3202.5.
  The cDNG claims 3200 for all four. A 2-7 LSB colour offset at the very bottom: slight green lift in
  deep shadows. Probable, small. Valid only if the tuning's per-channel values hold in Clear HDR, unconfirmed.

## 8. Preview (BE): per-channel black over-subtracted after the unwrap

IPA gate `src/ipa/rpi/pisp/pisp.cpp:695-726@6b0b49f`: in IMX585 12-bit with HDR mode set, FE BLA/BLC are
zeroed and BE BLC subtracts the tuning per-channel values (3301 / 3321 / 3240). The BE input is the
unwrapped buffer, whose black is about 3206 / 3207.5 / 3202.5 (section 7). BE therefore over-subtracts
about 95 (R), 114 (G), 37 (B) linear LSB.

| Symptom | Where |
| --- | --- |
| Crushed deep shadows; remaining shadows tinted toward blue/magenta (G removed most, B least) | HDMI / touch preview, WebUI preview, anything rendered from the ISP output (ProRes/H.264 if those use it) |
| Not in the cDNG | the raw buffer is copied, the BE does not write it |

Status: probable (code read; magnitude depends on which tuning file Core hands libcamera: Core sets
`LIBCAMERA_RPI_TUNING_FILE` itself, `CameraController.cpp:1430-1439`, `7422`). Settle: cap the lens, compare
preview black in 12-bit vs 16-bit Clear HDR; or read `black_level` in the active tuning file and the
`CcmpUnwrap` log line.

## 9. First frames: FE BLA runs on the codes before the gate is on

| Fact | Evidence |
| --- | --- |
| At configure the IPA applies the default black level with `requestedHdrMode_` still empty, i.e. the SDR shape with FE BLA enabled | `src/ipa/rpi/pisp/pisp.cpp:1070-1082` |
| `requestedHdrMode_` is set only when a request carries `HdrMode`; the pipeline injects it per frame | `ipa_base.cpp:1429-1446`, `pipeline pisp.cpp:3191-3192` |
| Output0 is the FE output, so FE BLA alters the raw codes before the unwrap | `pisp.cpp:1364,1378` |
| `requestedHdrMode_` is never cleared | grep `requestedHdrMode_`: set once, read once |

Effect: the first frame(s) after start carry an R/G/B shift of a few codes before the unwrap; one frame
is hidden by the helper (`cam_helper_imx585.cpp:84-94`). Low. After leaving Clear HDR on the same IPA
instance, SDR 12-bit keeps the HDR black routing (BE-only BLC); output is equivalent. Low.

## 10. Stats and exposure

AGC/AWB stats are computed in software on the linearised buffer (`pisp.cpp:3106`, `830`), so AE sees
highlights correctly. Cam helper keeps mode sensitivity 1.0 and notes Lux reads ~3x SDR in 12-bit Clear HDR
versus ~1.1x in 16-bit (`cam_helper_imx585.cpp:64-82`). Auto exposure in 12-bit can therefore differ from
16-bit at the same scene. Probable "exposure looks different from 16-bit", not "strange". Gain code range
0..0xf0 (`cam_helper_imx585.cpp:53-57`), not keyed on HDR.

## 11. Boundary notes for other agents (not traced to the end)

| Note | Evidence | Status |
| --- | --- | --- |
| Lossy DNG + Clear HDR 12: `sampleBits = settings.rawBitDepth` = 12 while the samples are linear 16-bit; the encoder treats them as 12-bit MSB-justified (black from `SensorBlackLevels/16`), dropping 4 LSB, i.e. the whole 1-LSB shadow segment | `CameraController.cpp:9498`, `3989-3991`; `LossyDngEncoder.cpp:450-458`; `LossyJpeg12.cpp:1043` | probable |
| MLV keeps linear 16-bit samples; its black/white must be 3200/65520, not 12-bit values | `CameraController.cpp:1636-1638` | for the MLV agent |
| Raw stream is 16-bit unpacked (2 B/px) instead of 12-bit packed (1.5 B/px): +33 % per frame, which matters for buffer count, copy time and fps ceilings | `pisp.cpp:1870-1898` | probable |
| ~19 OB rows at the top in Clear HDR, known driver issue | `imx585.c:4139-4148@cd548ef` | for the mode agent |

## Commands that settle the open points (all need the Pi)

| Point | Command |
| --- | --- |
| Unwrap armed and its parameters | `journalctl -b -u apertar-core \| grep -E "CcmpUnwrap\|CCMP stats\|Selected CFE format"` |
| Live control values | `v4l2-ctl -d $(media-ctl -e imx585 ...) -l` (look at `wide_dynamic_range`, `brightness`, gradient controls) |
| Raw buffer is linear 16-bit | dump one raw frame from Core, check min 3200, max 65520, values only in the LUT's image |
| Curve matches the sensor | 12-bit vs 16-bit Clear HDR scatter plot, section 6 |
| Players read the table | `exiftool -a -G1 -LinearizationTable -BlackLevel -WhiteLevel clip_000000.dng`, then grep each renderer for 50712 / LinearizationTable |
