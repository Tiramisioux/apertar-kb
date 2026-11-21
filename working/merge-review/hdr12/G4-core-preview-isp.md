# G4: 12-bit Clear HDR, the preview and ISP side in Core

Assignment G4 of the "12 bit clear HDR shows strange output" investigation. Read-only, no camera.
Refs: Core `HEAD` = `01f170c` (branch `claude/awesome-pasteur-qzsiow` = cinemate-port), fork main `origin/main`;
UI `7ea9afc`; driver `cd548ef` (baseline `origin/apertar`); libcamera fork `6b0b49f`.
`CC` = `src/camera/CameraController.cpp`, `App` = `src/ApertarCoreApp.cpp`, `WCP` = `src/web/WebControlPage.cpp`.
All line numbers are `@01f170c` unless marked.

## 1. Short answer

| Question | Answer | Label |
| --- | --- | --- |
| Tuning file in Clear HDR | `<sensor>_clearHDR.json` beside the default (automatic tuning only). The same file for 12-bit and 16-bit. A user-picked file (or `APERTAR_TUNING_FILE` adopted at start) is used as given, no `_clearHDR` swap | confirmed |
| libcamera controls Core sets for Clear HDR | None that are HDR-specific. No `HdrMode`, no WDR control through libcamera. Exposure, gain, WB and ScalerCrop are the same code as SDR | confirmed |
| Sensor HDR controls Core writes | V4L2 directly on the imx585 subdev: `WIDE_DYNAMIC_RANGE`, `HDR_DATASEL_TH` {4095,0}, `HDR_DATASEL_BK` 5, `HDR_GAIN` 1 (+6 dB). Same values in 12 and 16-bit | confirmed |
| CCMP knee / slope controls | Core never writes `HDR_GRAD_TH`, `HDR_GRAD_COMP_L/H`. Driver defaults apply: knees 500 / 11500, ACMP1 6 (1/64), ACMP2 4 (1/16) | confirmed |
| ISO / WB in Clear HDR | Auto ISO and auto WB forced off and held (port, `8175273`). ISO cap 720 in 12-bit, 1585 in 16-bit. Shutter auto is NOT forced off: AE still runs on exposure time | confirmed |
| Preview stream | One ISP YUV420 Rec709 stream (`VideoRecording` role), shared by HDMI/touch UI and WebUI MJPEG. Nothing in the Core preview path depends on bit depth | confirmed |
| What the ISP is fed in 12-bit | Per Core comments: libcamera's linear 16-bit samples, black 3200, white 65520, expanded in software from the CCMP codes. Same domain as 16-bit | confirmed (comment), probable (behaviour) |
| UI selection mismatch | Touch UI says "4K Clear HDR" but Core (port) no longer forces 4K: Clear HDR keeps the nearest row of the H12 class, e.g. 1920x1080 2x2 binned or a 3840 crop. Touch UI and WebUI enter Clear HDR at 12-bit; the hardware button enters at 16-bit | confirmed |

No Core preview/ISP code path was found that treats 12-bit Clear HDR differently from 16-bit, except: the ISO
cap (720 vs 1585), the H12 vs H16 size tables, and the skipped bit-depth check at configure. The 12-bit-only
difference that reaches the ISP is upstream of Core: libcamera's CCMP unwrap (section 6).

## 2. Tuning file

| Step | Code | Label |
| --- | --- | --- |
| Variant name and reason | `src/camera/DefaultTuningSelection.hpp:183-198@01f170c`: "Clear HDR needs its own tuning: the stock IMX585 file carries an rpi.hdr algorithm that pins exposure and gain to the IPA defaults in Clear HDR, which gives a black-level frame. The variant is the same file without it, named <sensor>_clearHDR.json beside the default. Returns the base path when none exists." | confirmed |
| Applied only to automatic tuning | `CC:7298-7305`: `automaticTuning = settings.tuningFile.empty()`; `automaticTuningPath` returns `clearHdrVariant(path)` only when `settings.clearHdr` | confirmed |
| Bit depth does not enter | `clearHdrVariant(basePath, pipeline)` has no bit-depth argument; 12-bit and 16-bit load the same file | confirmed |
| Missing variant | `CC:7323-7325` logs "Clear HDR tuning variant (<sensor>_clearHDR.json) not found; the default tuning may give a black frame." and carries on with the stock file | confirmed |
| Re-resolved after camera pick | `CC:7383-7403`: default re-resolved from the libcamera `Model`, `automaticTuningPath` applied again | confirmed |
| TDN strip (port, `e625c68`) | `CC:7308-7319`: with `previewTdn` off (default, `Types.hpp:139`) libcamera loads `~/.cache/apertar-core/tuning/<stem>_notdn.json` (`TuningTdnStrip.hpp:409-411`). The stem keeps `_clearHDR`, so the Clear HDR copy is separate from the SDR one | confirmed |
| Log / ProRes preview colour (port) | `CC:7327-7328`, `7405-7426`: `activeIspColorProfile()` (`include/apertar/core/Types.hpp:223-230`) returns `cdngPreviewColorProfile` for cDNG; a non-Standard profile writes a derived tuning `~/.cache/apertar-prores/<profile>.json` from the active file (`src/color/ProresIspProfile.cpp:229`), replacing `rpi.contrast` and turning `rpi.hdr` tonemap off. No bit-depth input | confirmed |
| Custom file disables the swap | `CC:10519-10522`: the constructor adopts `LIBCAMERA_RPI_TUNING_FILE` (exported by `scripts/start-apertar-core.sh:16-17` from `APERTAR_TUNING_FILE`) into `settings_.tuningFile`, which then is "custom" and is never swapped for `_clearHDR` | confirmed |
| Which file the Pi really runs | Core logs it: `CC:7431-7438` "ApertarCore tuning file: ... active=..." and publishes `tuning_file_active` (`App:9527`) | settle: `journalctl -u apertar-core -b \| grep -i "tuning file"` on the Pi, and `get_state` -> `tuning_file_active` |

Implication: the tuning cannot by itself explain "12-bit strange, 16-bit fine", because both depths load the same
file. It would explain "Clear HDR strange in both depths" if the variant is missing or a custom file is set.

## 3. Sensor HDR controls Core writes

| Control | Core value | Where | Driver meaning `@cd548ef` | Label |
| --- | --- | --- | --- | --- |
| `V4L2_CID_WIDE_DYNAMIC_RANGE` | `clearHdr` | `CC:7005-7031`, called `CC:7333` before `CameraManager` starts | selects the Clear HDR mode list | confirmed |
| base+0 `HDR_DATASEL_TH` u16[2] | `{hdrThresholdHigh, hdrThresholdLow}` = {4095, 0} | `CC:7033`, `7076-7084`; defaults `include/apertar/core/Types.hpp:203-204` | `EXP_TH_H/L` HG/LG selection, `imx585.c:3589-3597` | confirmed |
| base+1 `HDR_DATASEL_BK` menu | `hdrBlend` = 5 | `CC:7035`, `Types.hpp:205` | `EXP_BK` 5 = "HG 1/16, LG 15/16" (`imx585.c:344-352`) | confirmed |
| base+5 `HDR_GAIN` menu | `hdrGainAdder` = 1 | `CC:7036`, `Types.hpp:206` | `EXP_GAIN` index 1 = "+6dB" (`imx585.c:335-337`); driver default is index 2 = +12 dB (`imx585.c:536`, `3742-3751`) | confirmed |
| base+2 `HDR_GRAD_TH` (CCMP1/2_EXP) | not written | grep: no `kImx585CidBase + 2/3/4` in Core | driver default {500, 11500} (`imx585.c:3688`, `3907-3908`) | confirmed |
| base+3/4 `HDR_GRAD_COMP_L/H` (ACMP1/2) | not written | same | defaults 6 (1/64), 4 (1/16) (`imx585.c:3716-3740`) | confirmed |

- The same four writes run for 12-bit and 16-bit: `applyImx585HdrControls` has no bit-depth branch (`CC:7076-7084`). confirmed.
- The driver re-applies the cached values at every stream start: `__v4l2_ctrl_handler_setup` after the base tables (`imx585.c:4185-4190`). confirmed.
- The IDs match: Core `kImx585CidBase = V4L2_CID_USER_BASE + 0x2000` (`CC:7033`) = driver `V4L2_CID_USER_IMX585_BASE` (`imx585.c:31-40`); offsets 0, 1, 5 unchanged from `origin/apertar` (`imx585.c:34-39@e5b74d3`). confirmed.
- Not port changes: the Core defaults are identical on fork main (`include/apertar/core/Types.hpp:156-159@origin/main`, added in `631721d`), and the driver defaults are identical on `origin/apertar` (`imx585.c:496,517-518,1798,1822@e5b74d3`). confirmed.
- No WebUI or touch-UI control for these knobs: no `set_hdr_*` in `WCP` or in `Apertar-UI/src`, `qml`. Only socket commands (`App:13159-13166`) and presets (`App:14369-14374`). confirmed.

### 3.1 The gain adder contradicts the ISO-cap comment

`CC:2932-2935` and the shipped conf (`App:5075-5079`): "12-bit: the sensor merges HG and LG only while GAIN + EXP_GAIN <= 29.1 dB,
so with the driver's +12 dB EXP_GAIN up to gain code 57 (17.1 dB), ISO 720." Core itself writes EXP_GAIN +6 dB (index 1), so
the +12 dB premise is false while Core runs. Effects (probable, arithmetic from the driver comment `imx585.c:172-178`, which
gives the window `9.6 dB <= GAIN + EXP_GAIN <= 29.1 dB` for the built-in combination):

| ISO | GAIN (dB, 0.3 dB/code, `cam_helper_imx585.cpp:53-62@6b0b49f`) | GAIN + 6 dB | inside 9.6..29.1? |
| --- | --- | --- | --- |
| 100 | 0 | 6.0 | no, below |
| 150 | 3.5 | 9.5 | no, at edge |
| 200 | 6.0 | 12.0 | yes |
| 720 (cap) | 17.1 | 23.1 | yes |
| ~1400 | 23.0 | 29.0 | yes (the real ceiling with +6 dB) |

- The cap 720 is stricter than needed: harmless (lower ISO ceiling only).
- Below about ISO 150 the sum leaves the window. Whether that window applies to the 12-bit CCMP mode only, to both modes, or at all,
  this machine cannot tell. If it applies to the 12-bit combination only, 12-bit at ISO 100 would misbehave and 16-bit would not.
  unconfirmed. Settle on the Pi: record 12-bit Clear HDR at ISO 100 and ISO 400 (same scene, adjust shutter), and the same with
  `{"cmd":"set_hdr_gain_adder","value":2}`; compare. Also read Sony AppNote section 5 page 18.

## 4. ISO, gain, white balance and AE in Clear HDR (all port, `8175273`)

| Rule | Code | Label |
| --- | --- | --- |
| Auto ISO and auto WB off in Clear HDR; remembered to come back in SDR | `enforceClearHdrExposureRules`, `CC:3069-3096`; called from the sanitiser `CC:3532` | confirmed |
| Reason given | `CC:3069-3072` "the ISP statistics are not valid in the 16-bit mode, and Patrik's rule keeps both depths alike" | confirmed |
| Values held at entry: measured gain and measured Kelvin | `setClearHdr`, `CC:11632-11643` | confirmed |
| ISO cap per depth | `clearHdrIsoCap`, `CC:3017-3023`: `rawBitDepth == 16 ? max16 : max12`; defaults `CC:2936-2939` (720 / 1585); read once from `[camera]` of `apertar-hardware.conf` (`CC:2941-2983`, `3008-3012`) | confirmed |
| `set_iso_auto true` and `set_wb_auto` refused in Clear HDR | `CC:11167-11170`, `11299-11302` | confirmed |
| Shutter auto is not touched | `enforceClearHdrExposureRules` has no `shutterAuto` line; `controlsForSettings` sets `AeEnable = isoAuto \|\| shutterAuto` (`CC:2425`, `2438`) with `AnalogueGainMode` manual (`CC:2443-2446`) | confirmed |
| Manual WB uses `ColourTemperature`, needs a CT curve in the active tuning | `CC:2462-2470`; `whiteBalanceAvailable` from the active tuning (`CC:7577`, `8274`, `8602`) | confirmed |

Effects:
- Switching 16-bit to 12-bit with ISO above 720 drops ISO to 720 (sanitiser). The picture gets darker by up to 1.1 stops and the
  ISO readout changes. Symptom: "12-bit is darker". Expected behaviour, not a bug. confirmed.
- With shutter auto on, the IPA's AGC still drives exposure time in Clear HDR from libcamera's software raw stats. In 12-bit those
  stats are computed on the unwrapped buffer (section 6). If the 12-bit stats read brighter than 16-bit (libcamera's own comment says
  "Clear HDR-16 ~1.1x SDR, Clear HDR-12 ~3x SDR" Lux, `cam_helper_imx585.cpp:74-77@6b0b49f`), AE would pick a shorter shutter in
  12-bit: darker preview and darker file. probable. Settle: Pi, shutter auto, same scene, read `get_state` shutter in 12 and 16-bit.
  With shutter manual (default `shutterAuto = false`, `Types.hpp:162`) this does not apply.

## 5. Preview path

| Item | Code | Bit-depth dependent? | Label |
| --- | --- | --- | --- |
| Roles for raw recording | `CC:8331-8337`: `{VideoRecording, Raw}` | no | confirmed |
| Preview stream config | `CC:8383-8387`: `YUV420`, `previewSizeForSensorMode(activePreviewReference)`, `Rec709`, buffer count `rawCameraBufferCount(clearHdr)` | no (only `clearHdr`) | confirmed |
| Preview size | `previewSizeForSensorMode`, `CC:3626-3637`: aspect of the active size | no | confirmed |
| ScalerCrop | `CC:2474-2504`: centred crop from `ScalerCropMaximum`, same for 12/16 | no | confirmed |
| Frame handed out | `CC:10150-10207`: dmabuf planes, `captureWidth/Height = settings_.resolution` | no | confirmed |
| HDMI/touch and WebUI MJPEG | `App:8207-8235`: one `enqueuePreviewFrame`; MJPEG copies the same frame when clients are connected (`App:8216-8217`) | no | confirmed |
| Raw buffers cached in Clear HDR | `CC:8700-8707`: cached dma-buf when `clearHdr && packing == Unpacked` (both depths) | no | confirmed |
| Bit-depth check at configure skipped in Clear HDR | `CC:8497`: `else if (!sanitized.clearHdr) { // Clear HDR 12-bit reads out linear 16-bit samples` | Clear HDR only; raw size and ScalerCropMaximum still checked (`CC:8495-8496`, `8511-8519`) | confirmed |

The HDMI/touch preview and the WebUI preview show the same ISP output. If one looks wrong in 12-bit, so does the other. A
difference between them would point at the UI renderers, not at Core or the ISP. confirmed.

## 6. What the ISP is fed in 12-bit Clear HDR

Core's own statements:
- `CC:1683-1685`: "Clear HDR: libcamera hands over linear 16-bit samples in both sensor modes (it expands the 12-bit mode in software, black 3200, white 65520)."
- `src/cdng/ClearHdrCcmp.hpp:9-22`: libcamera's `CcmpUnwrap` "expands every raw frame back to linear 16-bit before Core sees it"; the expansion uses the driver defaults (knees 500/11500, slopes 6/4, black 200) and "Core never writes the gradient-compression controls; if it ever does, the table has to follow the live values."
- `CC:8497` (above): no 12-bit depth check, because the stream is 16-bit.

What libcamera does (read only to check Core's comments; libcamera itself is another agent's angle):
- `pisp.cpp:3091-3102@6b0b49f`: the unwrap runs in place on the raw buffer "so both BE rendering AND the stats kernel see the same 16-bit-linear data". So the ISP back end renders the preview from the unwrapped buffer. confirmed in code.
- `ccmp_unwrap.cpp:110-127@6b0b49f`: `LUT[code] = 3200 + inverse(code - blc) * (0xFFF0 - 3200) / inverse(4095 - blc)`. With the driver defaults, `inverse(3895) = 11500 + (3895 - 671) * 16 = 63084`, scale 62320 / 63084 = 0.988. So 12-bit full scale lands at 65520, black at 3200, as Core says. confirmed (arithmetic).
- Params come from the live driver controls (`pisp.cpp:2964-3026@6b0b49f`), BLC from `V4L2_CID_BRIGHTNESS` x 4 (default 50 -> 200). Core hardcodes black 200 and the default knees (`ClearHdrCcmp.hpp:24-30`). Core writes neither, so they agree unless something else changes them. confirmed.

Implications for the preview:

| Aspect | Expected in 12-bit vs 16-bit | Label |
| --- | --- | --- |
| Brightness | Same scale (black 3200, top ~65520) at the same ISO and shutter. Differences come from the ISO cap (section 4) or AE on shutter | probable |
| Colour | Same tuning, same black level, same CCM. A colour difference only in 12-bit would need a per-channel error in the unwrap (wrong BLC, clipped channel), i.e. libcamera, not Core | probable |
| Tonal steps | The 12-bit mode carries 171 codes for linear 500..11500 above black (ACMP1 1/64): one code = 63 linear units in 16-bit. That is 7 to 2.4 stops below clip. At 7 stops under, one step is ~12 %; at 5 stops ~3 %; at mid-grey under 1 %. Possible visible banding / posterisation in deep shadows, in preview and in files. 16-bit has no such quantisation. Driver defaults, unchanged since fork main | probable |
| Auto exposure | Only with shutter auto (section 4) | probable |

Settle the tonal-step claim without a camera if a 12-bit Clear HDR cDNG exists: count distinct raw values in one frame (stored codes
should be <= 4096 values, mapped through the LinearizationTable). With the camera: underexpose a grey ramp by 5-7 stops in 12-bit and
16-bit and compare the preview.

If libcamera did NOT unwrap (for example a different libcamera on the Pi than `6b0b49f`, or the unwrap skipped), the BE would get 12-bit
codes as u16 values 0..4095 instead of a 16-bit range: preview nearly black and wrong colour, recorded cDNG wrong (Core's
`compressClearHdrFrame` would map already-small values through the 65536-entry LUT). The comment on fork main's history says Core was
checked "against every value in a recorded frame" (`ClearHdrCcmp.hpp:15-16`). Settle on the Pi: libcamera log line
"ClearHDR 12-bit CCMP stats linearisation enabled" (`pisp.cpp:1836-1838@6b0b49f`) at Core start in 12-bit Clear HDR, and
`/proc/$(pidof apertar-core)/maps | grep libcamera` for which build is loaded.

## 7. How the UIs label and select 12-bit Clear HDR

### 7.1 Core: what a Clear HDR selection becomes

| Step | Code | Label |
| --- | --- | --- |
| Bit depth in Clear HDR | `supportedRawBitDepthForSensor`, `CC:3452-3453`: `clearHdr ? (bitDepth == 16 ? 16 : 12)`. From SDR 10 or 12 -> 12 | confirmed |
| Size in Clear HDR | `CC:3529-3531`: `normalizedResolutionForSensor(..., rawBitDepth, clearHdr)` -> nearest row of the H12 / H16 class (`src/camera/Imx585Modes.hpp:177-187`, `233-250`). Colour sensors are NOT forced to 4K any more | confirmed |
| Fork main forced 4K | `CC:2824-2827@origin/main`: "Clear HDR exists only at 4K on the driver ... `settings.resolution = Resolution{ 3840, 2160 }`". Replaced in `caa0153` "camera: imx585 modes from tables, not whitelists"; now only mono is forced (`CC:3527-3528`) | confirmed |
| H12 sizes | `Imx585Modes.hpp:78-87`: 29 rows incl. `{1920,1080,binned}`, 3840 crops, 2048 crops, 1920 1x1 crops, `{1440,1080,1x1}` | confirmed |
| Size changes class meaning | SDR 10-bit 1440x1080 is 2x2 binned (`Imx585Modes.hpp:60`); H12 1440x1080 is 1x1 (`:86`). Entering Clear HDR from 10-bit 1440x1080 keeps "1440x1080" but the field of view shrinks to a quarter (centre crop). S12 also lists 1440x1080 as 1x1 (`:48`), so from 12-bit it is unchanged | confirmed |
| Clear HDR refused | `CC:11645-11648`: ProRes/H.264 or non-IMX585 -> error, mode not changed | confirmed |

### 7.2 Touch UI (`Apertar-UI@7ea9afc`)

| Item | Code | Label |
| --- | --- | --- |
| Clear HDR is a resolution choice named "4K Clear HDR" | `qml/CameraPage.qml:3382`, `3457-3458`; `qml/SettingsPage.qml:3294-3302` | confirmed |
| Comment still says Core forces 4K | `qml/CameraPage.qml:453` "Core forces 4K, no crops"; `qml/SettingsPage.qml:106-107`; `src/ApertarControlBridge.cpp:705` "Core restarts the camera, forces 4K and settles the bit depth" | confirmed (stale since `caa0153`) |
| Turning it on sends only `set_clear_hdr` | `src/ApertarControlBridge.cpp:703-714`; `qml/CameraPage.qml:1351-1360` | confirmed |
| Resulting depth: 12-bit (Core rule above) | - | confirmed |
| Crop and size controls disabled in Clear HDR | `qml/CameraPage.qml:458` `cropControlsEnabled: ... !root.clearHdrActive`; `qml/SettingsPage.qml:3333` | confirmed |
| Picking any other size turns Clear HDR off first | `qml/CameraPage.qml:1358-1359`; `qml/SettingsPage.qml:3313-3314` | confirmed |
| Bit depth in Clear HDR: 12 or 16 only | `qml/SettingsPage.qml:658-664` | confirmed |
| Resolution line shows the real size | `qml/CameraPage.qml:544-551`: "3840x2160 · 12-bit · Clear HDR" built from `root.resolution` (Core's) | confirmed |

Consequence: from Full HD SDR (1920x1080, 2x2 binned, the UI's other base choice, `qml/CameraPage.qml:419-422`), tapping
"4K Clear HDR" runs 1920x1080 2x2 binned 12-bit Clear HDR while the quick-menu label says "4K Clear HDR". From a 4K crop
(e.g. 3840x1608) it runs 12-bit Clear HDR at 3840x1608. The touch UI then offers no way to change the size inside Clear HDR.
These binned and crop Clear HDR modes never ran on fork main. confirmed (code); whether the driver/ISP handle CCMP correctly in
binned or crop windows is the driver agent's question. Symptom if this is it: "12-bit Clear HDR" shows a smaller or binned picture
(softer, different framing) than the label says; files at that size. Settle: `get_state` -> `resolution` after tapping "4K Clear HDR",
and the Core log line `ApertarCore ... mode ...` / `list_sensor_modes`.

### 7.3 Hardware button

`App:10452-10463`: `clear_hdr` action sends `set_clear_hdr true` then `set_raw_bit_depth 16`. Its comment says "as the touch UI's
resolution button does"; the touch UI does not (7.2). So the hardware button gives 16-bit Clear HDR, the touch UI and WebUI give
12-bit. If the owner checked 16-bit via the button and 12-bit via the touch UI, the two tests also differ in path (two reconfigures
for the button). confirmed (code), comment stale.

### 7.4 WebUI (`WCP`)

| Item | Code | Label |
| --- | --- | --- |
| Family pills carry "-hdr" ("4K HDR", "Full HD binned HDR", "2K crop HDR", "HD crop HDR") | `WCP:9014-9032`, `8931-8933` | confirmed |
| Target class when turning Clear HDR on: h12 | `WCP:8947-8951` "Clear HDR on is 12-bit from SDR" | confirmed |
| Commands: `set_clear_hdr` then `set_resolution` of the same ratio | `WCP:9059-9069` | confirmed |
| Bit depth options in Clear HDR: 12 and 16 | `WCP:9608-9617` | confirmed |
| Labels: "4K Clear HDR 12-bit", running line "ClearHDR12" | `WCP:7671-7673`, `7694-7706`, `9108-9112` | confirmed |
| Fallback fps table disagrees with Core | `WCP:7456-7458`: "Clear HDR 16-bit stops at 25, as in Core's tableMaximumFpsForResolution()". Core: 25 for Clear HDR (both depths) only when no probe value, else 30 (`CC:3376-3380`); the 16-bit back-end cap was removed (`CC:3424-3430`). Same in touch UI `qml/CameraPage.qml:820-822`. Used only when Core sends no `fps_max` | confirmed, low impact |

The WebUI sizes its pills from the H12 table, so it shows what Core will run. No silent mode change found there.

### 7.5 Can a 12-bit Clear HDR selection end in another mode?

| Path | Result | Label |
| --- | --- | --- |
| ProRes / H.264 active | Refused with an error (`CC:11645-11648`); WebUI greys it (`WCP:9034-9038`) | confirmed |
| Non-IMX585 on the bus | Cleared at start with a log line (`CC:7283-7289`) | confirmed |
| Size not in H12 | Nearest H12 row, no message (`Imx585Modes.hpp:233-250`) | confirmed |
| 10-bit 1440x1080 binned -> Clear HDR | 1440x1080 1x1: same numbers, other field of view (7.1) | confirmed |
| Mode Ladder on | A rung can set `clearHdr` and bits (`CC:10761-10765`, `10878-10881`); an explicit `set_clear_hdr` sets `ladderOverride_` (`CC:11656-11658`) until fps, resolution, format, bit depth or the ladder changes | confirmed; ladder interplay not traced further |
| Silent 12 -> 16 | Only the hardware button (7.3). Nothing else found | confirmed |
| Silent Clear HDR -> SDR | Only by the sanitiser for ProRes/H.264 or another sensor; not found for cDNG/MLV on the IMX585 | confirmed |

## 8. Port changes in this area, and whether they can make 12-bit differ from 16-bit

| Port change | Commit | 12-bit only? |
| --- | --- | --- |
| Clear HDR no longer forced to 4K; H12 / H16 tables | `caa0153` | yes in effect: the touch UI enters Clear HDR at 12-bit and at whatever SDR size was active, including binned HD and crops |
| ISO/WB hold and per-depth ISO cap | `8175273` | the cap differs (720 vs 1585) |
| Preview TDN-stripped tuning copy | `e625c68` | no |
| Log / colour-profile derived preview tuning | (ProresIspProfile) | no |
| HDR knob defaults, gain adder, CCMP params | none (fork main and driver baseline) | n/a |

## 9. Checks for the Pi (five minutes each)

1. `get_state` after selecting 12-bit Clear HDR in the touch UI: `resolution`, `raw_bit_depth`, `clear_hdr`, `iso`, `iso_max`, `shutter_auto`, `tuning_file_active`.
2. `journalctl -u apertar-core -b | grep -Ei "tuning file|Clear HDR tuning variant|CCMP|ClearHDR"`.
3. 12-bit vs 16-bit at the same size (4K), ISO 400, shutter manual: preview and one cDNG each.
4. 12-bit at ISO 100 vs 400 with `set_hdr_gain_adder` 1 and 2 (section 3.1).
5. 12-bit from Full HD SDR via the touch UI: check the running size (section 7.2).
