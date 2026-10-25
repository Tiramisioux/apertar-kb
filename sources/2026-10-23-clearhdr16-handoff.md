# Handoff: implement 16-bit Clear HDR (IMX585) in Apertar

You are the lead engineer for this work. Use worker agents for parallel, well-bounded subtasks (code mapping, drafting a patch to one file region, adversarial diff review, writing a bench script). Keep design decisions, integration, and every hardware-facing step with you. A worker gets: the goal, exact files and line numbers, the constraints below, and what "done" looks like. It returns diffs and findings with file:line evidence, never opinions. Workers never push.

Background research, with sources and the hardware lessons, is in this page: https://claude.ai/artifact/UJGwJF7LWJECj6fWCksMFT. Read it first. This prompt repeats what you need to act; the page carries the evidence.

## 1. Goal

Add Clear HDR support for the Sony IMX585 to Apertar, 16-bit linear mode first. Done means: on an Apertar 1.6.0 image on a Raspberry Pi 5 or CM5, a user can switch Clear HDR on, record a 3840x2200 (3840x2160 active) 16-bit CinemaDNG sequence with correct black and white levels and `ActiveArea`, adjust the four merge knobs live, and switch back to SDR, with every SDR code path byte-for-byte unchanged when Clear HDR is off.

Out of scope for this effort: 12-bit CCMP (companded) Clear HDR, mono IMX585 at 16-bit, Pi 4 / VC4, RP1 overclock, any hardware-input work (NeoRotary, GPIO, LEDs), changes to the kernel driver or libcamera.

## 2. Repositories

| Repo | Role | Clone |
| --- | --- | --- |
| Apertar-Studio/Apertar-Core | C++ libcamera backend. All backend work lands here | `git clone https://github.com/Apertar-Studio/Apertar-Core` |
| Apertar-Studio/Apertar-UI | Qt Quick touch UI. Toggle and controls | `git clone https://github.com/Apertar-Studio/Apertar-UI` |
| Apertar-Studio/imx585-v4l2-driver | Sensor driver. Read only; already has Clear HDR | `git clone https://github.com/Apertar-Studio/imx585-v4l2-driver` |
| Tiramisioux/cinepi-raw | Reference implementation of the WDR write and the knobs (port from here) | `git clone https://github.com/Tiramisioux/cinepi-raw` |
| Tiramisioux/cinemate-handbook | `lessons/hardware-log.md`: the measured failure modes | `git clone --depth 1 https://github.com/Tiramisioux/cinemate-handbook` |
| Tiramisioux/libcamera, branch `cinemate` | Commit `bcdd7e1`: the COMP1 endian-swap fix, in case the image's libcamera lacks it | `git clone --depth 80 --branch cinemate https://github.com/Tiramisioux/libcamera` |

Work on your own fork of Apertar-Core and Apertar-UI. One branch and one pull request per step below. Keep each PR under about 400 changed lines; split if it grows.

## 3. Facts you can rely on (verified 2026-10-23)

- Apertar's driver `main` is upstream Will Whang as of 1 Jun 2026. It contains Clear HDR: `common_clearHDR_mode[]` (`imx585.c:510`), `IMX585_MODE_4K_16BIT_HDR` (`:681`), `codes_clearhdr[]` (`:785`), control activation (`:951`), and six custom controls at `V4L2_CID_USER_BASE + 0x2000` (`:34-39`):
  - `+0` `HDR_DATASEL_TH`: `u16[2]`, each 0..4095. `th[0]` = high threshold (register 0x36D0), `th[1]` = low threshold (0x36D4). The sensor requires `th[0] >= th[1]`.
  - `+1` `HDR_DATASEL_BK`: menu, valid indices 0..7 (`hdr_data_blender_menu[]`, `:337`). Index 8 is prohibited.
  - `+2` `HDR_GRAD_TH`, `+3` `HDR_GRAD_COMP_L`, `+4` `HDR_GRAD_COMP_H`: CCMP only, not used in this effort.
  - `+5` `HDR_GAIN` (gain adder): menu 0..5 (`hdr_gain_adder_menu[]`, `:328`). Writes `EXP_GAIN` (0x3081).
- Clear HDR is switched by the standard `V4L2_CID_WIDE_DYNAMIC_RANGE` on the sensor subdev. Setting it changes the sensor's mode list, so it must be written **before** libcamera configures the camera. On Will's `main`, 16-bit Clear HDR is offered at **4K only**: `MEDIA_BUS_FMT_SRGGB16_1X16` at 3840x2200. The 2200 rows are 2160 active plus 20 optical-black rows above and 20 below. There is no binned 16-bit mode on this driver.
- Analogue gain in Clear HDR is capped at code 80 (`IMX585_ANA_GAIN_MAX_HDR`, `:172`), about ISO 1585. The usable merge window is 9.6 dB <= GAIN + EXP_GAIN <= 29.1 dB (`:166`).
- Kernel: both `rpi-6.12.y` and `rpi-6.18.y` give the four Bayer-16 formats `csi_dt = 0` in `rp1_cfe/cfe_fmts.h` ("Avoid RP1 HW mismatch for 16-bit modes", 4 Jul 2025). Colour 16-bit capture works on any current Pi OS kernel. The CFE may deliver the 16-bit stream either as `SRGGB16` unpacked or as `SRGGB16_PISP_COMP1` (compressed); handle both.
- libcamera: stock raspberrypi/libcamera has no `cam_helper_imx585`, so the Apertar image ships a custom build. Unknown: whether that build gates `Needs16bitEndianSwap` on the CFE format not being PISP1-packed. Without that gate a COMP1 16-bit stream is scrambled into a constant 16-byte fill pattern. Step 1 settles this.
- Apertar-Core already has: `RawBitDepth::Bits16`; `SRGGB16` and `R16` entries in the raw format table (`src/camera/CameraController.cpp:3040-3066`); PISP_COMP1 detection (`:3075-3107`) and a `decodePispRowToMsb16` decoder; a `Bits16` memcpy branch in `writeDngRowBytes` (`src/cdng/CdngEncoder.cpp:1042`); `linearizationTable` written as tag 0xC618 (`:1584`); a working precedent for writing V4L2 controls on the matched subdev, `resetStoppedSensorTiming()` (`CameraController.cpp:5925`), which finds the subdev by `of_node` or name and uses `VIDIOC_QUERY_EXT_CTRL` + `VIDIOC_S_CTRL`.
- Apertar-Core has no HDR concept: `normalizeRawBitDepth()` (`:243`) collapses 16 to 12; `rawPixelFormatForBitDepth()` (`:2181`) returns `SRGGB12_CSI2P` for anything but 8 or 10; `storageRawBitDepthForSettings()` (`:1301`) defaults to `Bits12`; `sensorModeForRequestedResolution()` (`:2244`) maps IMX585 requests to 3840x2160 or 1920x1080; `preparePispCompressedLayout()` (`CdngEncoder.cpp:1815`) accepts a `Bits16` frame but downgrades the layout to 12-bit.
- Apertar-Core has no test suite, no `.clang-format`, and upstream history is large squashed commits. Style to match: 4-space indent, `camelCase`, `kConstant` names, helpers in an anonymous namespace at the top of the file, `std::cerr << "ApertarCore ..."` logging, no new dependencies, settings persisted through the existing `CaptureSettings` parse/serialise pair (`CameraController.cpp:699` and `:766`), commands dispatched in `ApertarCoreApp::handleCommand`, state pushed with `publishEvent`.

## 4. Constraints

1. Default off. With `clear_hdr=false` every existing code path, setting file, and state field must behave exactly as before. Diff SDR behaviour against `main` in review.
2. Never proceed silently past a failed WDR write. Refuse to start the camera with a clear error instead. A silent proceed records black pedestal frames while the app believes HDR is on.
3. The threshold pair is one control. Write both halves together, in the order `{high, low}`, and refuse when `high < low`.
4. The gain adder is written only while Clear HDR is on. The driver resets `EXP_GAIN` to 0 in SDR; re-applying a stored adder there boosts SDR by up to 29 dB.
5. 16-bit is only selectable with Clear HDR on, and Clear HDR 16-bit only with the lossless cDNG recording format. Refuse MLV, ProRes, H.264 and lossy cDNG at 16-bit with a message rather than guessing what those encoders do with 16-bit input.
6. Auto exposure and auto white balance are off in 16-bit Clear HDR (ISP statistics are invalid). Refuse `set_iso_auto`, `set_shutter_auto` and `AwbEnable=true` in that mode.
7. ISO is clamped to 1585 in 16-bit Clear HDR. Land out-of-range requests on the cap and report it in state so the UI can show it, rather than dropping steps.
8. No driver or libcamera changes in these PRs. If step 1 shows the image's libcamera lacks the endian-swap gate, write that up as a blocker with the exact patch reference (`Tiramisioux/libcamera` `bcdd7e1`, `src/libcamera/pipeline/rpi/pisp/pisp.cpp`) and stop until the human resolves it.
9. Hardware steps are run by the human. You write the script and the expected result; you do not assume the result.
10. Keep Apertar's vocabulary: setting key `clear_hdr`, command `set_clear_hdr`, state field `clear_hdr`, knob keys `hdr_threshold_low`, `hdr_threshold_high`, `hdr_blend`, `hdr_gain_adder`.

## 5. Steps

### Step 0: orientation (three workers in parallel, read-only)

Each worker writes a map with file:line references and returns it. Do not start code until all three are back.

- Worker A, configure path in `src/camera/CameraController.cpp`: where `camera_->configure()` is called and what precedes it; how `SensorModeSelection` is built and consumed; where the raw stream's `pixelFormat` and `size` are set; where `validate()` adjusts them; how the resulting `StreamConfiguration` is read back and classified through the table at `:3040` and the COMP1 detection at `:3075`; how the restart-on-resolution-change path works (which function stops and reconfigures); where `controls::SensorBlackLevels` is read; where `FrameDurationLimits` are read; how the imx294 readout-versus-active crop (`imx294ReadoutForActiveResolution`, `:2192`) is applied downstream in the DNG (`DefaultCropOrigin`, `DefaultCropSize`, `ActiveArea`) and in the ISP (`ScalerCrop`).
- Worker B, settings and commands: `CaptureSettings` fields, the parse loop at `:699`, the serialise at `:766`, the `raw_bit_depth` command in `ApertarCoreApp::handleCommand` (find it by grepping `set_raw_bit_depth`), how a setting change decides between a live control write and a full reconfigure, what the state JSON (`get_state`, line ~171 `raw_bit_depth`) contains, how `publishEvent` broadcasts `settings`.
- Worker C, UI touch points: in `Apertar-UI/qml/SettingsPage.qml` the bit-depth picker and the record-format picker (grep `rawBitDepth`, `recordFormat`); in `src/ApertarControlBridge.cpp/.hpp` how a core state field becomes a QML property and how a `set_*` command is sent; in `Apertar-Core/src/web/WebControlPage.cpp` the same two controls for the WebUI. Also list where ISO auto, shutter auto and AWB toggles live in both UIs.

### Step 1: bench proof (you write it, the human runs it)

Produce `bench/step1-clearhdr-probe.sh` for the human. It must:

1. Record `uname -r`, the libcamera library path and version (`ldconfig -p | grep libcamera`, and `strings` the pipeline library for `Needs16bitEndianSwap` and for `imx585`), and `dmesg | grep -i imx585`.
2. Find the IMX585 subdev: `for d in /dev/v4l-subdev*; do v4l2-ctl -d $d --info 2>/dev/null | grep -q imx585 && echo $d; done`.
3. `v4l2-ctl -d $SUBDEV --list-ctrls-menus | grep -i -A2 'wide_dynamic\|hdr'` to show the controls exist and their ranges.
4. `v4l2-ctl -d $SUBDEV --set-ctrl wide_dynamic_range=1`, then `--get-ctrl wide_dynamic_range` to prove the write took, then `--list-subdev-mbus-codes` and `--list-subdev-framesizes`. Expected: `MEDIA_BUS_FMT_SRGGB16_1X16` at 3840x2200.
5. Stop `apertar-core`, set WDR as above, start `apertar-core` and request 3840x2160 (the UI alias) at 12-bit, record 10 frames, and print for the first frame: `BitsPerSample`, `ImageWidth/Length`, `BlackLevel`, `WhiteLevel`, `ActiveArea` (with `exiftool`), and for the strip: unique-value count in a middle row and the md5 of the pixel block of frames 3 and 5. Expected before any code change: this run will most likely fail or produce 12-bit output; the point is to see what libcamera negotiates (`Selected sensor format` / `Selected CFE format` in the journal) and whether a 16-byte repeating motif appears if a 16-bit frame does come out.
6. Reset: `--set-ctrl wide_dynamic_range=0`, restart `apertar-core`.

Decision tree, written into the script's README:
- No `wide_dynamic_range` control: wrong driver on the image; stop and report.
- Control present, SRGGB16 3840x2200 not listed after setting it: driver not on Will's June 2026 main; stop and report.
- Journal shows CFE format `...PISP_COMP1` and frames carry a repeating 16-byte motif: the image's libcamera lacks `bcdd7e1`; blocker per constraint 8.
- SRGGB16 listed, journal shows a 16-bit sensor format, frames vary per pixel and per frame: proceed to step 2.

### Step 2: PR 1, `clear_hdr` setting and the WDR write (Apertar-Core)

Scope: the setting, its persistence, the command, the state field, and the subdev write. No 16-bit yet.

- Add `bool clearHdr = false;` to `CaptureSettings`; key `clear_hdr` in the parse loop and the serialiser, next to `raw_bit_depth`.
- Add `set_clear_hdr` with field `enabled` (`"true"`/`"false"`) to `handleCommand`, using whatever the `set_raw_bit_depth` handler does for validation, persistence, and triggering a reconfigure. A change in `clear_hdr` is a full stop-and-reconfigure, exactly like a resolution change.
- Add `"clear_hdr":true|false` to the state JSON and to the `settings` event.
- New helper in the anonymous namespace of `CameraController.cpp`, modelled on `resetStoppedSensorTiming()`: `bool setSensorWideDynamicRange(const std::string &cameraId, bool enabled, std::string *error)`. Find the subdev the same way (`of_node` canonical path or `name`), `VIDIOC_QUERY_EXT_CTRL` for `V4L2_CID_WIDE_DYNAMIC_RANGE`; if absent and `enabled` is false, return true silently; if absent and `enabled` is true, set `*error = "sensor has no Clear HDR control"` and return false. Otherwise `VIDIOC_S_CTRL`, then `VIDIOC_G_CTRL` to read back; on mismatch sleep 50 ms and retry, four attempts; return false with the error text on the last failure. Port the shape of cinepi-raw `core/options.cpp:141-170` (`set_subdev_hdr_ctrl`).
- Call it in the configure path before `camera_->configure()`, on every configure, with `settings.clearHdr`. Writing 0 when Clear HDR is off is required: it is how the camera returns to the SDR mode list after an HDR session. A false return aborts the start with the error surfaced through the existing error path (`setLastError` or equivalent found in step 0).
- Log one line on success: `ApertarCore Clear HDR: wide_dynamic_range=1 accepted on /dev/v4l-subdevN`.
- Acceptance: builds in Release; `--simulate` unaffected; on hardware (human), toggling `set_clear_hdr` restarts the camera and the journal shows the acceptance line; `v4l2-ctl --get-ctrl wide_dynamic_range` agrees with the setting after each toggle; SDR recording still works with `clear_hdr=false`.

### Step 3: PR 2, the 16-bit raw path (Apertar-Core)

Scope: selecting the 16-bit sensor mode when Clear HDR is on and writing a correct 16-bit DNG.

Workers: one drafts the `CameraController.cpp` changes, one drafts the `CdngEncoder.cpp` changes, a third reviews both diffs adversarially against the constraints before you integrate.

- `normalizeRawBitDepth()` (`:243`): accept 16 only when the caller passes `clearHdr == true`; this needs a second parameter or a sibling function, because the current signature has no settings context. Pick the smaller diff.
- `rawPixelFormatForBitDepth(16)` (`:2181`) returns `libcamera::formats::SRGGB16`.
- `storageRawBitDepthForSettings()` (`:1301`): 16 maps to `RawBitDepth::Bits16`.
- `sensorModeForRequestedResolution()` (`:2244`), `SensorFamily::Imx585`: when `clearHdr && bitDepth == 16`, set `rawResolution = {3840, 2200}` for any request that today resolves to 3840x2160, and set the active window to 3840x2160 at offset (0, 20). Reuse the mechanism Worker A found for imx294 so the DNG carries `DefaultCropOrigin 0 20`, `DefaultCropSize 3840 2160`, `ActiveArea 20 0 2180 3840`, and the ISP preview crops the OB rows. Any other request at 16-bit (1920x1080, crops) is refused with `"16-bit Clear HDR is 3840x2160 only on this driver"`.
- Frame path: with WDR on the CFE delivers either `SRGGB16` unpacked or `SRGGB16_PISP_COMP1`. The table at `:3040` and the detection at `:3075` already classify both. In `preparePispCompressedLayout()` (`CdngEncoder.cpp:1815`) add a real 16-bit layout: `layout.bitDepth = Bits16`, `layout.packing = Unpacked`, `rowBytes = width * 2`, rows decoded with `decodePispRowToMsb16` and written verbatim (in a genuine 16-bit sensor mode the MSB-aligned 16-bit value is the sample). For the unpacked `SRGGB16` input the existing `Bits16` memcpy branch in `writeDngRowBytes` (`:1042`) applies; confirm it is reached, since `storageRawBitDepthForSettings` previously never produced `Bits16`. Remove or correct the comment "supports only 8-bit, 10-bit, and 12-bit storage".
- `BitsPerSample` 16, `WhiteLevel` 65535. `BlackLevel`: take it from `controls::SensorBlackLevels` metadata where Apertar already reads it; expect 3200 (the 16-bit domain pedestal). Do not hardcode unless the metadata is absent, and then use 3200 with a comment.
- Still capture at 16-bit: allowed only if it falls out of the same path with no extra code; otherwise refuse with a message. Record this decision in the PR.
- Recording formats: refuse MLV, ProRes, H.264 and lossy cDNG when `rawBitDepth == 16` (constraint 5).
- Acceptance (human bench, script `bench/step3-16bit-take.sh`): one 4K 16-bit take of a structured, non-clipped scene; `exiftool` shows 3840x2200, 16 bps, BlackLevel 3200, WhiteLevel 65535, `ActiveArea 20 0 2180 3840`; a middle row has hundreds of unique values; frames 3 and 5 have different pixel-block md5s; the preview shows the scene without the OB bands; opening a frame in a DNG converter shows a neutral, non-magenta image.

### Step 4: PR 3, the four merge knobs (Apertar-Core)

- Commands: `set_hdr_threshold_low {value 0..4095}`, `set_hdr_threshold_high {value 0..4095}`, `set_hdr_blend {value 0..7}`, `set_hdr_gain_adder {value 0..5}`. Persist all four in `CaptureSettings` under those keys. State JSON carries them back.
- Helper in the anonymous namespace: `bool setImx585HdrControl(const std::string &cameraId, uint32_t id, int32_t value, const uint16_t *pair, std::string *error)` using `VIDIOC_S_EXT_CTRLS` with `V4L2_CTRL_WHICH_CUR_VAL`, `p_u16` for the pair. Port the shape of cinepi-raw `cinepi/cinepi_controller.cpp:95-121` (`set_imx585_hdr_ctrl`) and `:161-172` (`build_hdr_threshold_pair`), keeping the `{high, low}` order and the `high >= low` refusal. Define the CIDs as `kImx585CidBase = V4L2_CID_USER_BASE + 0x2000` and `kImx585CidHdrDataselTh = kImx585CidBase + 0`, `kImx585CidHdrDataselBk = kImx585CidBase + 1`, `kImx585CidHdrGainAdder = kImx585CidBase + 5`.
- Apply rules: all four are live controls, no reconfigure. They are written only when `clearHdr` is on; a command arriving in SDR is stored and answered `ok:true` with a note that it applies when Clear HDR is on. After every successful configure with Clear HDR on, re-apply the stored values (the driver resets registers on mode start). Threshold writes send the pair; a single-side command uses the stored other side.
- Default values: leave the driver defaults in place (Will's May 2026 commits fixed them) and store `-1`/unset until the user touches a knob. Do not copy Cinemate's blend index 5 as a default without a bench result; put it in the PR description as the value Cinemate measured working.
- Acceptance (human): after each command `v4l2-ctl --get-ctrl hdr_data_selection_threshold` (name as listed in step 1) reads back the written values in the written order; blend and adder read back; a take at blend 0 and at blend 5 differ visibly in highlight rendering.

### Step 5: PR 4, guards (Apertar-Core)

- ISO: in the `set_iso` handler and in `pcfIsoOptions()` (used by hardware-button ISO cycling), clamp to 1585 when `clearHdr && rawBitDepth == 16`. Report `clear_hdr_iso_max` in state. Land an over-range request on 1585 and answer `ok:true` with a note.
- Exposure modes: refuse `set_iso_auto`, `set_shutter_auto`, and any command that sets `AwbEnable` true while in 16-bit Clear HDR; return `ok:false` with `"auto exposure and auto white balance are unavailable in 16-bit Clear HDR"`. On entering the mode with auto active, force manual with the current values and publish the change.
- Frame rate: the driver advertises the halved limits through `FrameDurationLimits`; confirm Apertar's fps options and `maximumPcfFpsForSettings` (`CameraController.cpp:1076`) honour them for the 16-bit mode rather than a hardcoded table. Expected: about 22 fps at stock clocks.
- Acceptance: `set_iso 3200` in HDR reads back 1585 in state; `set_iso_auto` is refused in HDR and accepted in SDR; fps picker in HDR tops out at the driver limit.

### Step 6: PR 5, UI and WebUI (Apertar-UI and Apertar-Core web)

Two workers: one for `qml/SettingsPage.qml` plus `src/ApertarControlBridge.*`, one for `src/web/WebControlPage.cpp`. You integrate.

- Record settings: a `Clear HDR` toggle (use the existing `TogglePill`/`SettingsChoice` components and the `set_clear_hdr` command). It is visible only when the backend reports the sensor family as IMX585.
- Bit-depth picker: `16-bit` appears only when `clear_hdr` is true; switching Clear HDR off while at 16 falls back to 12.
- Record-format picker: non-cDNG formats and lossy cDNG disabled at 16-bit, with the reason shown.
- An `HDR merge` advanced card with the four knobs (use `AdjustNumberTile` for thresholds, a choice for blend and adder), visible only with Clear HDR on.
- ISO auto, shutter auto and AWB controls disabled in 16-bit Clear HDR with the reason; ISO control shows the cap.
- WebUI mirrors all of the above from the same state fields.
- Acceptance: every control round-trips through the backend state (no UI-only state); toggling Clear HDR restarts the camera and the UI shows the restart the same way a resolution change does.

### Step 7: optional, not in this effort

30 fps at 4K 16-bit needs `dtoverlay=rp1-overclock` plus a libcamera IPA pixel-rate bound (`Tiramisioux/libcamera` `3c7b9ab`, `0413c13`). Document as follow-up; do not start.

## 6. Traps, measured on hardware by Cinemate

Carry these into code review. Each one cost days.

- A flat, low-value frame is not always "dark". Check per-pixel and per-frame variance: a repeating byte motif is a format bug (COMP1 scrambled by an endian swap); a constant single value with the scene overexposed is the sensor's black-level pedestal, which means a prohibited sensor state.
- Pedestal causes: WDR write not accepted; `EXP_TH_H < EXP_TH_L`; a cropped binned 16-bit readout; a startup latch of the merge, cleared by a brief shutter change (Cinemate kicks shutter angle to 1 degree and back). Do not build the self-heal in this effort; note it if seen.
- The first WDR write immediately after an SDR session was once rejected and succeeded on retry. Hence the four retries.
- Above the gain window the merge collapses gradually (peak raw code 4095 to 3188 to 2408 in Cinemate's 12-bit sweep) and every knob looks inert. Test knobs at ISO 400, not 3200.
- The gain adder writes `EXP_GAIN`; in SDR the driver holds it at 0. Never apply it outside Clear HDR.
- Identify a sensor mode by its whole shape, bit depth and HDR state, never by height alone; 2200 and 2160 both occur.
- Expect 16.9 MB per 4K 16-bit frame; at 22 fps that is about 370 MB/s. Bench on NVMe or the CFE hat, not SD.
- Do not trust Cinemate's numbers blindly on a 6.18 kernel; they were measured on 6.12.93. Re-measure anything that matters.

## 7. Reference code to port

Check licence compatibility before copying: cinepi-raw derives from rpicam-apps (BSD-2-Clause); Apertar-Core's `LICENSE` must be read. Port the logic, keep attribution in a comment, never paste without reading.

| What | Where |
| --- | --- |
| WDR write with readback and retry | `cinepi-raw/core/options.cpp:141-170` |
| Knob write (`VIDIOC_S_EXT_CTRLS`, `p_u16` pair) | `cinepi-raw/cinepi/cinepi_controller.cpp:78-121` |
| Threshold pair order and refusal | `cinepi-raw/cinepi/cinepi_controller.cpp:123-172` |
| Re-apply stored knobs after launch, gated on HDR | `cinepi-raw/cinepi/cinepi_controller.cpp:353-400` |
| Apertar's own subdev write pattern | `Apertar-Core/src/camera/CameraController.cpp:5925-5965` |
| COMP1 block decode, for cross-checking Apertar's decoder | `cinepi-raw/cinepi/dng_pack.hpp:265-400` |

## 8. Working agreements

- Before each PR: build Release with `cmake -S . -B build -DCMAKE_BUILD_TYPE=Release && cmake --build build -j$(nproc)`; run `./build/apertar-core --simulate` and `get_state` through the socket; grep your diff for any behaviour reachable with `clear_hdr=false` and justify each line.
- Adversarial self-review on every diff: what would make this record a wrong file silently? What happens if the subdev is absent, if libcamera returns a different format than requested, if the user toggles Clear HDR mid-recording?
- PR description: what, why, how it was tested (simulate and bench), bench output pasted, open questions. No model names in commits or PR text.
- Hardware gates are hard stops. Write the script, hand it over, wait for the result, and only then continue.
- Report blockers with the exact file, line, observed output, and the smallest change that would unblock, not with a workaround that widens the scope.

## 9. Definition of done

- [ ] PRs 1 to 5 merged on the fork, each green on build and simulate smoke.
- [ ] Bench scripts for steps 1, 3, 4 and 5 committed under `bench/` with their expected results.
- [ ] A 4K 16-bit Clear HDR take recorded on hardware with correct `BitsPerSample`, `BlackLevel`, `WhiteLevel`, `ActiveArea`, varying per frame, neutral in a DNG converter.
- [ ] Knobs read back from the sensor after each command and survive a camera restart.
- [ ] ISO cap, auto-mode refusals and format refusals verified from the UI and the WebUI.
- [ ] SDR behaviour diffed against `main` and unchanged.
- [ ] A short upstream proposal written for the Apertar maintainer summarising the five PRs, the bench results, and the two follow-ups (12-bit CCMP, overclock).
