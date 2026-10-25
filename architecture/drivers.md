# Sensor drivers (imx585)

The kernel driver, its dtoverlay, and how Core picks a sensor mode and tuning file.

Paths: `imx585-v4l2-driver/...` is the local clone at `~/Documents/Apertar/imx585-v4l2-driver` (remote `origin` = Apertar-Studio/imx585-v4l2-driver, branch `main`, HEAD `70bdb26`).

## Which driver is on the Pi

| Fact | Status |
| --- | --- |
| Pi runs will127534's `qbc-pisp-handler` branch with a local modification, built via DKMS from `/home/pi/drivers/imx585-v4l2-driver` | from the live Pi (given) |
| Other DKMS drivers on the Pi: `/home/pi/drivers/imx294-imx492-v4l2-driver`, `/home/pi/drivers/imx477-v4l2-driver` | from the live Pi; no source here |
| Apertar-Studio `main` (`70bdb26`) is a separate line | local clone |
| The Apertar-Studio clone also has `origin/qbc-pisp-handler` at `1644466` | `git branch -a` |
| `origin/qbc-pisp-handler` is an ancestor of `main`. `main` adds 4 commits: `3680bf4` harden format transitions, `c0f5404` per-mode HMAX table + Clear HDR floor, `11178c8` RAW10 4K mode, `70bdb26` `ccmp` overlay param | `git log main..origin/qbc-pisp-handler` = 0, reverse = 4 |
| Whether Apertar-Studio's `qbc-pisp-handler` equals will127534's | **unconfirmed** |
| What the Pi's local modification changes | **unconfirmed**. Run `cd /home/pi/drivers/imx585-v4l2-driver && git status && git diff` |

Consequences of running `qbc-pisp-handler` instead of `main` (from the 4-commit diff, `git diff main origin/qbc-pisp-handler --stat`: 106+ / 417-):

- No RAW10 4K mode (`supported_10bit_modes[]` is a `main`-only addition, `imx585-v4l2-driver/imx585.c:751-771`). Core still offers 10-bit for IMX585 (`Apertar-Core/src/camera/CameraController.cpp:2695-2698`).
- No `ccmp` overlay param (`imx585-v4l2-driver/imx585-overlay.dts:138` exists only on `main`).
- The single `HMAX_table_4lane_4K` without the Clear HDR floor.

Line numbers below are for `main`. Check the Pi's tree before trusting a line on it.

## Modes on `main`

All modes are 4-lane numbers; 2-lane doubles HMAX (`imx585-v4l2-driver/imx585.c:1203`).

| Index | Size | Bit depth | Readout | Ref |
| --- | --- | --- | --- | --- |
| `IMX585_MODE_1080P_12BIT` | 1920x1080 | 12 | 2x2 binned | `imx585.c:686-704` |
| `IMX585_MODE_4K_12BIT` | 3840x2160 | 12 (SDR, or Clear HDR 12-bit CCMP) | all-pixel | `imx585.c:705-723` |
| `IMX585_MODE_4K_16BIT_HDR` | 3840x2200 (2160 active + 2x20 OB) | 16, Clear HDR only | all-pixel | `imx585.c:724-748` |
| `supported_10bit_modes[0]` | 3840x2160 | 10, SDR only | all-pixel | `imx585.c:751-771` |

Native array 3856x2180; active 3840x2160 at left offset 8 (`imx585.c:217-221`). Fixed pixel clock constant 74.25 MHz (`imx585.c:214`).

Format codes:

| Table | Codes | Ref |
| --- | --- | --- |
| `codes_normal` | SRGGB/SGRBG/SGBRG/SBGGR 12 then 10 | `imx585.c:774-783` |
| `codes_clearhdr` | Bayer 16 first, then Bayer 12 | `imx585.c:785-796` |
| `mono_codes` | Y16, Y12, Y10 | `imx585.c:798-802` |

Mode table routing, `get_mode_table()` (`imx585.c:965-1046`):

| Request | SDR (`clear_hdr=0`) | Clear HDR (`clear_hdr=1`) |
| --- | --- | --- |
| 16-bit | none | 4K 16-bit only |
| 12-bit | binned + 4K | 4K 12-bit only if `ccmp` is set, else none |
| 10-bit | 4K 10-bit | none |

Size choice is `v4l2_find_nearest_size()` (`imx585.c:1146-1147`). A request for a size that is not a mode gets the nearest mode, not an error.

## Timing and frame rate

- Min HMAX per mode comes from a link-frequency table (`HMAX_table_4lane_4K_12bit`, `imx585.c:280-295`; 10-bit table follows). 2079 Mbps/lane uses HMAX 472, not the 440 that produced broken frames on Pi 5 (`imx585.c:287-292`).
- `imx585_update_hmax()` recomputes HMAX/VMAX for lane count and Clear HDR (`imx585.c:1199-1245`). Clear HDR doubles VMAX and floors HMAX at `IMX585_HMAX_MIN_CLEARHDR` = 550 (`imx585.c:114`, `:1213-1225`).
- `imx585_set_framing_limits()` sets `PIXEL_RATE = width * 74.25 MHz / min_hmax`, HBLANK and VBLANK ranges, and exposure max `VMAX - 16` (`imx585.c:1251-1287`). libcamera derives `FrameDurationLimits` from these.
- README fps table per link frequency: `imx585-v4l2-driver/README.md:110-118`. RP1 limit ~400 Mpix/s ≈ 43.8 fps at 4K without overclock (`README.md:120`).

## V4L2 controls

Standard: `PIXEL_RATE` (RO), `LINK_FREQ` (RO), `VBLANK`, `HBLANK`, `BRIGHTNESS` (= black level), `EXPOSURE` (2..49865 lines), `ANALOGUE_GAIN` (0..240, 0..80 in Clear HDR), `HFLIP`, `VFLIP`, `WIDE_DYNAMIC_RANGE` (Clear HDR on/off), `TEST_PATTERN` (`imx585.c:1680-1730`; limits `:129-174`).

Custom, base `V4L2_CID_USER_BASE + 0x2000` (`imx585.c:30-43`):

| Offset | Name (as `v4l2-ctl` shows it) | Type | Notes |
| --- | --- | --- | --- |
| +0 | HDR Data Selection Threshold | u16 array | Clear HDR |
| +1 | HDR Data Blending Mode | menu 0..7 | Clear HDR; menu text `imx585.c:336-345` |
| +2 | HDR Gradient Compression Threshold (16-bit) | u32 | CCMP only |
| +3 | HDR Gradient Compression Ratio Middle (ACMP1) | menu, min 6 | CCMP only |
| +4 | HDR Gradient Compression Ratio High (ACMP2) | menu 0..5, def 4 | CCMP only |
| +5 | HDR Gain Adder (dB) | menu 0..5, def 2 | `+0dB` .. `+29.1dB` (`imx585.c:328-330`) |
| +6 | HCG Enable | bool | forced off in Clear HDR (`imx585.c:1313-1315`) |
| +7 | VMAX | int | direct register |
| +8 | HMAX | int | direct register |
| +9 | SHR | int | direct register |

Control definitions: `imx585.c:1546-1672`. Activation per mode: `imx585.c:951-962`.

`WIDE_DYNAMIC_RANGE` changes the mode list and re-picks the active format (`imx585.c:1307-1340`). It must be set before libcamera configures the camera.

## dtoverlay

Source: `imx585-v4l2-driver/imx585-overlay.dts`. Built and installed by `dkms.postinst` (`imx585-v4l2-driver/dkms.postinst:3-5`).

| Param | Effect | Ref |
| --- | --- | --- |
| (default) | cam1 port, 4 lanes, I2C addr `0x1a`, 24 MHz clock, link 720 MHz, `sony,sync-mode = "internal-leader"` | `imx585-overlay.dts:8-120` |
| `cam0` | Retarget I2C, CSI, clock and regulator to cam0 | `:129-135` |
| `2lane` | 2 data lanes | `:123` |
| `always-on` | Keep `cam1_reg` (camera power) always on | `:124`, fragment `:43-48` |
| `rotation=<n>`, `orientation=<n>` | DT rotation/orientation properties for libcamera | `:125-126` |
| `sync-mode=<str>` | `internal-leader` (default), `internal-follower`, `external` | `:127`; parsed `imx585.c:2335-2342` |
| `media-controller` | Toggle `brcm,media-controller` on the CSI node | `:128` |
| `link-frequency=<Hz>` | One of 297000000, 360000000, 445500000, 594000000, 720000000, 891000000, 1039500000, 1188000000 | `:136`; table `imx585.c:269-278`; validated `imx585.c:2256-2271` |
| `mono` | Sets DT property `mono-mode` → Y formats, `BIN_MODE=1` | `:137`; `imx585.c:2327`, `:1928` |
| `ccmp` (`main` only) | Sets `sony,clearhdr-ccmp` → allow 12-bit CCMP Clear HDR | `:138`; `imx585.c:2330-2333` |

README omits `rotation`, `orientation`, `media-controller` and `ccmp` (`imx585-v4l2-driver/README.md:68-143`).

**Possible bug:** the `cam0` override retargets `reg_alwayson_frag` to `cam0_reg` but not `reg_frag`, so the 300 ms `startup-delay-us` still lands on `cam1_reg` (`imx585-overlay.dts:36-41`, `:129-135`). **Unconfirmed** whether this matters on Pi 5 hardware.

The live rig uses `dtoverlay=imx585,cam0,link-frequency=891000000` (`apertar-kb/sources/2026-10-23-i2c-dpi-cfe-hat-neorotary.md`, config.txt line 42).

## How Core uses the sensor

Core has **no Clear HDR support**. Nothing in Core writes `WIDE_DYNAMIC_RANGE` or any custom CID (no `hdr`/`wdr` hits in `Apertar-Core/src/camera/CameraController.cpp` or `Apertar-Core/src/ApertarCoreApp.cpp` besides PNG `IHDR`). `rawPixelFormatForBitDepth()` only returns 8/10/12-bit formats (`Apertar-Core/src/camera/CameraController.cpp:2181-2191`). The only direct subdev write is `resetStoppedSensorTiming()` (below).

### Sensor family

`detectSensorFamily()` lowercases the libcamera camera id and substring-matches `imx577`, `imx477`, `imx294`, `imx585` in that order (`Apertar-Core/src/camera/CameraController.cpp:2150-2167`). The id is the DT path, so the node name `imx585@1a` from the overlay (`imx585-overlay.dts:57`) is what matches. DNG model for IMX585 is `IMX585-AAQJ1` (`CameraController.cpp:2262`).

The first non-USB camera wins (`CameraController.cpp:5304-5307`).

### Mono

Detected from libcamera's `ColorFilterArrangement == MONO`, else from the raw format's Bayer pattern (`CameraController.cpp:5309-5323`). Before libcamera starts, the tuning preselect checks `/sys/class/video4linux/v4l-subdev*/device/of_node/mono-mode` (`Apertar-Core/src/camera/DefaultTuningSelection.hpp:198`), i.e. the overlay's `mono` param.

### Resolution → sensor mode

`sensorModeForRequestedResolution()` (`CameraController.cpp:2203-2268`), IMX585 branch `:2244-2262`:

| Requested | Raw stream size asked for |
| --- | --- |
| 1332x990, 2028x1080, 2028x1520, 1920x1080, 1928x1090 | 1920x1080 |
| FullHD crops: 1920x {1038, 1012, 960, 872, 864, 816, 804, 768, 752} | as requested (`:366-377`) |
| 4056x2160, 4056x3040, 3840x2160, 3856x2180 | 3840x2160 |
| 4K crops: 3840x {2076, 2024, 1920, 1744, 1728, 1632, 1608, 1536, 1504} | as requested (`:385-396`) |
| anything else | 1920x1080 |

Bit depth for IMX585: 10 or 12 only (`CameraController.cpp:2695-2698`). Processed formats (H.264/ProRes) force 10 (`:2723-2724`).

Configure loop (`CameraController.cpp:5985-6140`): roles `VideoRecording` + `Raw` for RAW recording (`:6033-6038`); explicit `SensorConfiguration{outputSize=rawSize, bitDepth}` first (`:6119-6122`), then an auto fallback only if `allowAutoSensorConfigFallback` (`:5993-5996`). For IMX585 the fallback is allowed only for the 4K crop sizes.

**Crop sizes and the driver.** The IMX585 crop sizes are not modes on Apertar-Studio `main`. The driver returns the nearest mode (`imx585.c:1146`), so an explicit `SensorConfiguration` with `outputSize=3840x2076` should fail `validate()`. 4K crops then fall back to auto config; FullHD crops have no fallback. Core's DNG-side active-window crop (`shouldUseRequestedActiveRawCrop`) excludes IMX585 (`CameraController.cpp:2850-2857`). **Unconfirmed** how crops actually behave on the Pi. The Pi's local driver modification may add these sizes. Check with:

```bash
for d in /dev/v4l-subdev*; do v4l2-ctl -d $d --info | grep -q imx585 && v4l2-ctl -d $d --list-subdev-framesizes pad=0,code=0x3008; done
journalctl -u apertar-core | grep -E 'camera configured|trying IMX585|rejected'
```

The success log line is `ApertarCore camera configured: sensor=... raw=... stream=... format=... storage_bits=...` (`CameraController.cpp:6263-6276`). Rejections accumulate in `rejectionLog` (`:5997`, `:6078-6082`, `:6135-6139`).

### Frame-rate caps (hardcoded)

`maximumSupportedFpsForResolution()` IMX585 branch (`CameraController.cpp:2669-2677`): 3840x2160 → 30.0, 4K crops → 60.0, 1920x1080 and FullHD crops → 60.0. Applied in `sanitizeSettingsForSensor` (`:2732-2741`) and after configure (`:6257-6261`).

These caps ignore the link frequency. At `link-frequency=891000000` the driver allows ~60 fps at 4K 12-bit (`README.md:117`), but Core caps it at 30. Lossless cDNG on IMX585 also caps at 30 fps and ISO 800 (`CameraController.cpp:2470-2491`).

### Black level

`blackLevelsForSensor()` returns 200 for IMX585 (256 for IMX477/577) (`CameraController.cpp:2944-2951`). **Unconfirmed** whether `SensorBlackLevels` metadata overrides it in the DNG.

### Long-exposure timing reset

`resetStoppedSensorTiming()` finds the subdev by `device/of_node` or `name` and writes the minimum of `HBLANK`, `VBLANK`, `EXPOSURE` after streaming stops (`CameraController.cpp:5926-5966`). Called from `stop()` only after a long exposure (`:5428-5429`). This is the template to copy for any new direct V4L2 control write.

## Tuning file selection

Code: `Apertar-Core/src/camera/DefaultTuningSelection.hpp`, used in `CameraController.cpp:5267-5375`.

1. Pipeline from DT `compatible`: `brcm,bcm2712` → PiSP; bcm2711/2837/2836/2835 → VC4 (`DefaultTuningSelection.hpp:18-43`).
2. Default dirs, in order (`:65-78`): `$APERTAR_DEFAULT_TUNING_DIR` or `/home/pi/Tuning-Files/defaults-{pisp,vc4}`; the same fixed path; `/home/pi/Tuning-Files/defaults` (legacy); `/usr/local/share/libcamera/ipa/rpi/<pipeline>`; `/usr/share/libcamera/ipa/rpi/<pipeline>`.
3. File name = first word of the sensor model, lowercased, + `.json`. Mono sensors only accept `<name>_mono.json`, never a colour file (`:130-181`).
4. Each candidate is parsed with libyaml; `target` must be `pisp` on Pi 5 or `bcm2835` on VC4; files over 4 MB are rejected (`:80-128`).
5. Before `CameraManager` starts, `preselectDefault()` reads every `v4l-subdev*/name` and picks a file only if exactly one candidate exists (`:185-205`).
6. After the camera is selected, the real model is checked. If it differs, CameraManager is torn down and restarted with the right file (`CameraController.cpp:5324-5341`), up to 3 attempts (`:5276`).
7. Log preview / ProRes log profiles generate a derived tuning file and restart CameraManager once more (`CameraController.cpp:5346-5370`).
8. Result is logged: `ApertarCore tuning file: <path> (sensor default|custom, pisp)` (`:5372-5375`).

`applyProcessTuningFile()` sets or clears `LIBCAMERA_RPI_TUNING_FILE` and `APERTAR_SENSOR_TUNING_FILE` (`CameraController.cpp:1111-1121`). It overrides anything set in the environment, including `APERTAR_TUNING_FILE` from the start script (see [build.md](build.md#the-start-script-and-service)).

A custom tuning file is the saved `settings.tuningFile`; empty means automatic (`CameraController.cpp:5266`). Custom files may live in `/home/pi/Tuning-Files/` or `<media>/Tuning-Files/` (`Apertar-Core/README.md:145`).

For IMX585 on Pi 5 the expected default is `/home/pi/Tuning-Files/defaults-pisp/imx585.json` (mono: `imx585_mono.json`).

libcamera itself: stock raspberrypi/libcamera has no `cam_helper_imx585`, so the image must carry a custom build (`apertar-kb/sources/2026-10-23-clearhdr16-handoff.md` §3). **Unconfirmed** which build and which commit.

## Diagnosing a sensor problem

| Symptom | First check |
| --- | --- |
| No camera | `dmesg | grep -i imx585` (probe logs `Data lanes`, `Link speed`, `sync-mode`, `ClearHDR 12-bit CCMP` at `imx585.c:2273`, `:2333`, `:2342`); `cam -l` |
| Wrong tuning / colour | `journalctl -u apertar-core | grep 'tuning file'` |
| Mode rejected | `journalctl -u apertar-core | grep -E 'rejected|trying IMX585'` |
| fps lower than expected | Core cap table above; then driver `Framing: VMAX= HMAX= pixel_rate=` in `dmesg` (`imx585.c:1285-1286`) |
| Mono shows colour options | `ls /sys/class/video4linux/v4l-subdev*/device/of_node/mono-mode`; overlay needs `,mono` |

## Update 2026-10-25: what the Pi actually runs

- `~/drivers/imx585-v4l2-driver` is now on branch **`apertar`** of `Tiramisioux/imx585-v4l2-driver`:
  will127534 `qbc-pisp-handler` `1644466` + `e5b74d3`.
- `e5b74d3` is the image's previously uncommitted `imx585.c` edit (582+/41-), committed unchanged. It
  adds 9 full-width RAW12 crops (3840x2076/2024/1920/1744/1728/1632/1608/1536/1504) and 9 binned crops
  (1920x1038 … 1920x752), per-mode `base_vmax`, `IMX585_CROP_VMAX(h) = h + 72`, and
  `imx585_apply_normal_bit_depth_regs()`. This is why Core's crop requests work on this image.
- The installed module `/lib/modules/6.12.75+rpt-rpi-2712/updates/dkms/imx585.ko.xz` was built
  2026-08-25 18:18, three minutes after the source edit (18:15): **probable** that it was built from it.
  Loaded `srcversion` `ED83F0A8968DC6BEF03779D`.
- Not merged: Apertar-Studio `main` `3680bf4`, `c0f5404`, `11178c8`, `70bdb26` (format-transition
  hardening, per-mode HMAX table + Clear HDR floor, RAW10 4K, `ccmp` overlay param). Merging them onto
  the crop edit will conflict in the mode tables. Good tutorial material.
