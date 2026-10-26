---
datum: 2026-10-26 04:30:00
kontext: CINEMATE
projekt: "#APERTAR"
fritext: T26 driver-crop-rectangles
typ: digital anteckning
---

# T26. Make the driver report each mode's sensor window, so Core gets real crop rectangles

Status: written 2026-10-26 (cloud session; reference patch `working/patches/0001-imx585-report-each-mode-s-sensor-window-as-its-crop-.patch` on branch `apertar` @ `e5b74d3`, not built). Independent of T23-T25. Builds **M7** (driver mode table → libcamera → Core).

**You will learn**
- Where `ScalerCropMaximum` really comes from (the subdev's `V4L2_SEL_TGT_CROP`, made relative to the active area) and why every one of our 21 modes reported `(0,0)/<mode size>`.
- The one invariant a mode's crop rectangle has to satisfy, borrowed from Cinemate's driver, which had and fixed the same defect.
- How to rebuild and reinstall the DKMS driver and verify a mode's geometry with `v4l2-ctl`.

**Risk:** driver rebuild via DKMS and a **reboot**; a wrong table can mean "no camera" until you revert (`git checkout`, `./setup.sh`, reboot). The crop values do not touch register programming. Side effects to watch: libcamera's preview `ScalerCrop` range and the IPA's binning scale change (the "2120 instead of 2160" preview height may move). **Time:** 1.5 h + reboot.

## 1. The problem

Core's startup probe (`f60e301`) prints `crop=(0, 0)/1920x1080` for the binned Full HD mode and `(0, 0)/3840x1504` for a 2.55:1 crop (`working/sensor-capabilities.md`): no offsets, no binning factor, so menus cannot tell a crop from a full-field mode. Cinemate reads the same geometry through five custom controls ("Mode Crop Left" ...), which our driver does not have; it turns out libcamera's own path is enough.

## 2. How this part works

```
 driver supported_modes[i].crop  --set_pad_format-->  subdev state crop  --get_selection(TGT_CROP)-->  libcamera analogCrop
 (imx585.c:794-1200)                (imx585.c:2129)      (imx585.c:2374-2381)              (camera_sensor_legacy.cpp:878-893, minus activeArea origin)
                                                                                           --> properties::ScalerCropMaximum (pipeline_base.cpp:562-568) --> Core probe
```

The `apertar` table fills every `.crop` with `{0, 0, <output width>, <output height>}` (`imx585.c:803-808` binned 1080p: 1920x1080; `:1164-1169` 3840x1504 at (0,0)). libcamera takes that rectangle as the sensor window: a 2x2-binned mode looks like an un-binned 1920x1080 window at the top-left corner.

Cinemate's `cinemate-modes` branch states the rule (`imx585.c:1044-1060@18c1eb2`): the crop is in **native sensor pixels**, full width, the window's start row, and the height **before** binning; full-field entries report the whole active area. Its driver had our exact defect until `951aeee` (2026-09-20). Only `set_pad_format` (`:2129`) and `init_state` (`:2425`) read `mode->crop`; the WINMODE registers come from the static `mode_*_regs` tables, so this change is table values only.

The window start row is already in the register tables: `IMX585_WIN_CROP_REGS(vst, vwidth)` with `PIX_VST = 12` for the full field (`imx585.c:560`), so the native top of a windowed mode is `vst - 12`, which is also the centred value `(2160 - rows) / 2`.

Reading assignments: `drv/imx585.c:560-578` (macros), `:586-600` (two windowed register tables), `:794-830` (first two table entries), `:2120-2131` (`set_pad_format` copies the crop), `:2374-2400` (`get_selection`).

## 3. Find it yourself

**3.1 What does the subdev say right now?** (Pi, Core running in a binned Full HD mode, read-only)

```bash
for d in /dev/v4l-subdev*; do grep -q imx585 /sys/class/video4linux/${d##*/}/name && v4l2-ctl -d $d --get-subdev-selection pad=0,target=crop && v4l2-ctl -d $d --get-subdev-fmt pad=0 | grep Width; done
```

A subdev needs `--get-subdev-selection` (`VIDIOC_SUBDEV_G_SELECTION`); plain `--get-selection` is for video nodes and fails with
"Inappropriate ioctl for device" on every subdev. The second command prints the mode's output size, so you know which entry you are
looking at. In the 16-bit Clear HDR mode (`3840/2200`) you get `0, 0, 3840, 2160`: one of the two entries T26 leaves unchanged, so
the defect only shows in a binned or windowed mode.

Prediction: `Selection: crop, Left 0, Top 0, Width 1920, Height 1080` for the imx585 subdev. What should a 2x2-binned full-field mode report?

> [!tip]- Answer
> `Left 0, Top 0, Width 3840, Height 2160`: the window before binning. libcamera divides window width by output width to get the binning factor (`scaleX = analogCrop.width / outputSize.width`).

**3.2 Where do VST and the crop disagree?** (Pi)

```bash
grep -n 'IMX585_WIN_CROP_REGS(54, 2076)' /home/pi/drivers/imx585-v4l2-driver/imx585.c
grep -n -A14 '1.85:1 full-width RAW12 crop' /home/pi/drivers/imx585-v4l2-driver/imx585.c | grep -E 'top|height'
```

Prediction: the registers put a 2076-row window at VST 54 (native row 42), the table says top 0. Three hits: the first `.height` is the mode's output size, the indented `.top`/`.height` pair is the crop.

**3.3 Does anything program registers from `.crop`?** (Pi)

```bash
grep -n -- '->crop\|\.crop;' /home/pi/drivers/imx585-v4l2-driver/imx585.c
```

Prediction: two hits, both copy it into the subdev state. Safe to change.

## 4. Make the change

File: `/home/pi/drivers/imx585-v4l2-driver/imx585.c`, table `supported_modes[]` (`:794`). Branch `apertar` @ `e5b74d3`. For every entry, replace the four lines inside `.crop = { ... }`:

| Entry (output) | New `.crop` (`left, top, width, height`) | Why |
| --- | --- | --- |
| 1920x1080 (binned full field) | `0, 0, IMX585_PIXEL_ARRAY_WIDTH, 2160` | whole active area before 2x2 binning |
| 1920x1038 | `0, 42, IMX585_PIXEL_ARRAY_WIDTH, 2076` | VST 54 - 12, height × 2 |
| 1920x1012 | `0, 68, …, 2024` | |
| 1920x960 | `0, 120, …, 1920` | |
| 1920x872 | `0, 208, …, 1744` | |
| 1920x864 | `0, 216, …, 1728` | |
| 1920x816 | `0, 264, …, 1632` | |
| 1920x804 | `0, 276, …, 1608` | |
| 1920x768 | `0, 312, …, 1536` | |
| 1920x752 | `0, 328, …, 1504` | |
| 3840x2160 (4K) | unchanged `0, 0, …, IMX585_PIXEL_ARRAY_HEIGHT` | |
| 3840x2076 | `0, 42, …, 2076` | VST 54 - 12 |
| 3840x2024 | `0, 68, …, 2024` | |
| 3840x1920 | `0, 120, …, 1920` | |
| 3840x1744 | `0, 208, …, 1744` | |
| 3840x1728 | `0, 216, …, 1728` | |
| 3840x1632 | `0, 264, …, 1632` | |
| 3840x1608 | `0, 276, …, 1608` | |
| 3840x1536 | `0, 312, …, 1536` | |
| 3840x1504 | `0, 328, …, 1504` | |
| 3840x2200 (16-bit) | unchanged `0, 0, …, IMX585_PIXEL_ARRAY_HEIGHT` | the 40 extra rows are OB and margin (Cinemate's rule: height - 40) |

**4.1 Binned full field** (`:803-808`, search `/* 1080p60 2x2 binning, 12-bit */`)

```c
		.crop = {
			/* sensor window before 2x2 binning: 2160 rows at row 0 */
			.left = 0,
			.top = 0,
			.width = IMX585_PIXEL_ARRAY_WIDTH,
			.height = 2160,
		},
```

**4.2 The nine binned crops** (`:822-978`; pattern for 1920x1038, search `/* 1.85:1 2x2 binned, full-width RAW12 crop */`)

```c
		.crop = {
			/* sensor window before 2x2 binning: 2076 rows at row 42 */
			.left = 0,
			.top = 42,
			.width = IMX585_PIXEL_ARRAY_WIDTH,
			.height = 2076,
		},
```

Repeat with the table's numbers. Invariant to check for every entry: `top + height <= 2160`, `height == 2 * output height`, `top == (2160 - height) / 2`.

**4.3 The nine full-width crops** (`:1013-1180`; pattern for 3840x2076, search `/* 1.85:1 full-width RAW12 crop */`)

```c
		.crop = {
			/* sensor window: 2076 rows at row 42 (PIX_VST 54) */
			.left = 0,
			.top = 42,
			.width = IMX585_PIXEL_ARRAY_WIDTH,
			.height = 2076,
		},
```

Invariant: `top == vst - 12` where `vst` is the first argument of that mode's `IMX585_WIN_CROP_REGS(vst, height)`.

**Check:** a one-liner that prints every crop with its entry (Pi):

```bash
awk '/\.crop = \{/{c=1} c&&/\.top =/{t=$3} c&&/\.height =/{h=$3} c&&/\},/{print NR": top "t" height "h; c=0}' /home/pi/drivers/imx585-v4l2-driver/imx585.c | sed 's/,//g'
```

Expect 21 lines; the tops 0, 42, 68, 120, 208, 216, 264, 276, 312, 328, 0, 42, 68, 120, 208, 216, 264, 276, 312, 328, 0.

## 5. Build, deploy, test

```bash
cd /home/pi/drivers/imx585-v4l2-driver && ./setup.sh 2>&1 | tail -5     # DKMS build + install (recipe B6 step 4)
dkms status | grep imx585
sudo reboot
```

After the reboot, with Core running:

```bash
journalctl -u apertar-core -b --no-pager | grep 'ApertarCore sensor mode' | grep -E '1920x1080|1920x1038|3840x1504' | head -3
journalctl -u apertar-core -b --no-pager | grep 'preview crop: native_max='
for d in /dev/v4l-subdev*; do grep -q imx585 /sys/class/video4linux/${d##*/}/name && v4l2-ctl -d $d --get-subdev-selection pad=0,target=crop && v4l2-ctl -d $d --get-subdev-fmt pad=0 | grep Width; done
```

Expected: `crop=(0, 0)/3840x2160` for 1920x1080, `(0, 42)/3840x2076` for 1920x1038, `(0, 328)/3840x1504` for the 2.55:1 crop; `v4l2-ctl` agrees for the current mode. Then look at the picture: preview framing in a crop mode and in binned Full HD; record one clip per class (binned, 4K crop, 16-bit) and open a frame.

What success looks like: Core's `list_sensor_modes` output carries a usable crop per mode (binning = crop width / output width), and the pictures are unchanged.

## 6. Commit and push

```bash
git -C ~/drivers/imx585-v4l2-driver add imx585.c
git -C ~/drivers/imx585-v4l2-driver commit -m "imx585: report each mode's sensor window as its crop rectangle

Why: every entry said crop = (0,0)/output size, so libcamera's analogCrop and
Core's ScalerCropMaximum could not tell a binned or windowed mode from a
full-field one. The crop is now the window in native sensor pixels (full
width, PIX_VST - 12, height before binning); 4K and 16-bit unchanged.
Register programming does not read .crop.
Tested: v4l2-ctl --get-subdev-selection per mode; Core sensor-mode log; pictures
unchanged in binned, cropped and 16-bit modes."
git -C ~/drivers/imx585-v4l2-driver push -u origin apertar
```

Add a row to `fork-log.md` (driver section) and update `architecture/drivers.md` ("ScalerCropMaximum now per mode").

## 7. If it went wrong

| You see | It means | Do |
| --- | --- | --- |
| no camera after reboot (`No libcamera cameras are available.`) | the module did not build/load | `dkms status`, `dmesg | grep imx585`; `git checkout -- imx585.c && ./setup.sh && sudo reboot` |
| libcamera rejects a mode (`camera configured:` shows a different `stream=`) | a crop larger than the active area (`top + height > 2160`) | re-check the invariant in 4.2/4.3 |
| the preview of a crop mode is framed differently than before | expected: libcamera's `ScalerCrop` default now follows the real window | note it in the hardware log; the DNG content is unaffected |
| 16-bit preview height changes from 2120 | the IPA scale for the 2200-row mode | note it; the table for that entry is unchanged on purpose |
| `v4l2-ctl --get-subdev-selection` still shows the old values | an old module is loaded (`/lib/modules/.../updates/dkms/imx585.ko.xz`) | `modinfo imx585 | grep srcversion` vs the build; reboot again |

## 8. What you learned, going further

- `ScalerCropMaximum` is the driver's crop selection; there is no magic in libcamera.
- A mode's geometry has three numbers that must agree: the WINMODE registers, the crop rectangle, the output size.
- Exercise: write `tools/check_crop_table.py` for our branch, like Cinemate's `tools/check_window_alignment.py`, and run it before every driver commit.
- Upstream: offer the table to Apertar-Studio with the `v4l2-ctl` evidence; mention that Cinemate's `cinemate-modes` also rejects windows whose start row is not a multiple of 4 (hence its 2072-row 1.85:1 window where ours is 2076, `imx585.c:2964-2969@18c1eb2`): unknown whether that matters on hardware.

## 9. Sources

- `working/clearhdr-compare-answer.md` §4; `working/patches/0001-imx585-report-each-mode-s-sensor-window-as-its-crop-.patch`.
- `imx585-v4l2-driver` `apertar` @ `e5b74d3`: `imx585.c:560-578, 586-760, 794-1200, 2120-2131, 2374-2400, 2424-2425`.
- `imx585-v4l2-driver` `cinemate-modes` @ `18c1eb2`: `imx585.c:1044-1060, 4298-4332`; commits `b703f46`, `74ed4c6`, `951aeee`.
- libcamera (qbc @ `7e9fef0`): `src/libcamera/sensor/camera_sensor_legacy.cpp:410, 878-893`; `src/libcamera/pipeline/rpi/common/pipeline_base.cpp:562-568`.
- `llm/change-recipes.md` B6 (DKMS build, the `v4l2_find_nearest_size` trap).

%% tutor
ref drv imx585.c 560 #define IMX585_WIN_CROP_ACTIVE_VST   12U
ref drv imx585.c 586 static const struct cci_reg_sequence mode_3840x2076_regs_12bit[] = {
ref drv imx585.c 794 static struct imx585_mode supported_modes[] = {
ref drv imx585.c 815 /* 1.85:1 2x2 binned, full-width RAW12 crop */
ref drv imx585.c 2129 *v4l2_subdev_state_get_crop(sd_state, 0) = mode->crop;
ref drv imx585.c 2374 static int imx585_get_selection(struct v4l2_subdev *sd,
check 3.3 | grep -c -- '->crop\|\.crop;' /home/pi/drivers/imx585-v4l2-driver/imx585.c | ^2$
check 4.2 | grep -c 'top = 42,' /home/pi/drivers/imx585-v4l2-driver/imx585.c | ^2$
check 4.3 | grep -c 'top = 328,' /home/pi/drivers/imx585-v4l2-driver/imx585.c | ^2$
check 5 | journalctl -u apertar-core -b --no-pager | grep 'ApertarCore sensor mode' | grep -c 'crop=(0, 42)/3840x2076' | ^[1-9]
%%

#CINEMATE
#APERTAR
