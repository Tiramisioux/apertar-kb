# Feature list: Camera, sensors and modes

What the cinemate port added in this area that original Apertar 1.6.0 could not do. One entry per feature, Core, WebUI, touch and driver parts merged.

| Item | Value |
| --- | --- |
| Built from | inventories CC-1, CC-4, CC-5, CC-6, Camera-headers, Driver-imx585, Driver-imx283 (`raw/inv-*.md`, `raw/FEATURES.json`), re-checked by grep |
| Refs | Core `cinemate-port` `01f170c` (`/home/user/Apertar-Core`), UI `7ea9afc`, imx585 driver `cd548ef`, imx283 driver `68b7dc9`; original = `upstream-1.6.0`; fork main `f60e301` |
| Short names | `CC` = `src/camera/CameraController.cpp`, `App` = `src/ApertarCoreApp.cpp`, `WCP` = `src/web/WebControlPage.cpp` |
| Already fixed, not here | GPIO chip setting back on the Controls page, checks per chip (Core `04fe197`). Not a camera-mode item |
| Tested, in general | `fork-log.md:138`: the whole drop-frames/mode-table block is "Not yet run on the camera". `fork-log.md:180-182`: the camera runs the `cinemate-port` build since 2026-11-08, a statement about the binary, not a feature test. The driver commits have no fork-log row; only their commit texts say anything |

## Table

| # | Feature | Operator gets | Relation to original | Stock camera sees | Needs | Tested |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Mode Ladder | The camera picks sensor mode (size, bit depth, Clear HDR, compression) from the chosen FPS between takes | New area, hooks into six setters | Off. Only the new state fields and a "Mode Ladder" card | none | Pi 2026-10-28 (socket, two takes, presets); Clear HDR over ladder not run |
| 2 | IMX585 modes from tables | 40 SDR sizes per depth, Clear HDR lists, 1:1 and 2.55:1 crops, 10-bit; 1.85:1 crops renamed | Replaces whitelist code | On: new size list, wide modes hidden below 1280, exact-mode refusal | cinemate-port driver | Desk only |
| 3 | IMX585 driver, modes and timing | 187 modes incl. RAW10 4K, crops with real sensor windows, new HMAX/VMAX tables | Replaces driver tables | On, once the driver is installed | DKMS driver, Pi 5/CM5 | Pi: crops listed 2026-10-26, 7-mode pass 2026-08-31; 1920/2048 families host only |
| 4 | IMX585 driver, Clear HDR colour and gate | 12-bit and 16-bit binned 1080p Clear HDR, 12-bit colour default on, mono needs `ccmp`, developer gate for windowed binning | Extends driver functions | On for colour | `dtoverlay=imx585,ccmp` for mono | CM5 link 891 MHz, 7 modes clean; windowed HDR gate never run |
| 5 | IMX283 sensor family | An IMX283 module works, 57 modes, active-area crops | Extends enum and switches, new header, new driver port | Nothing unless an IMX283 is fitted | imx283 driver `cinemate-port`, kernel 6.12+ | Core: desk only. Driver: built, one preview frame, DNGs 2x2 only |
| 6 | Mode geometry controls | `v4l2-ctl` shows binning, crop, active area per mode; libcamera scales correctly | Beside original | On with the new drivers | new drivers; cinepi-raw reads them | Pi 2026-10-26 (585); 283 on CM5 |
| 7 | Sensor-probe FPS ceiling | 4K SDR up to 60 fps, lossless IMX585 no longer capped at 30; `fps_max` in state | Extends fork-main probe, flips rule | On: higher ceilings | startup probe (`APERTAR_SENSOR_PROBE`) | Host test; Pi note for 4K Clear HDR 16 (27 fps real) |
| 8 | Binning and crop per mode | `list_sensor_modes` and state say binning and crop | Extends fork-main probe | On | probe, driver controls | Pi: `list_sensor_modes`, `get_state` |
| 9 | Clear HDR holds ISO and WB, measured ISO | Auto ISO/WB freeze in Clear HDR, return in SDR; `iso_actual`, `iso_max` shown | Extends setters in place | On in Clear HDR only | none | Pi preview 2026-10-28 |
| 10 | Preview temporal denoise switch | Faster preview at 4K Clear HDR 16-bit; DNGs unchanged | Beside original tuning selection | **Changed**: default off, so every camera loses preview TDN | tuning file with `rpi.denoise` | Desk only; Pi build 2026-11-04 |
| 11 | Raw camera buffer count | No control; fewer capture gaps (4 buffers SDR, 8 Clear HDR, +2 FAT/NTFS) | Replaces constant | On, silent | optional `apertar-media-tune.conf` | Pi, 4K Clear HDR 16-bit, gaps 41 to 1; 30 fps not fixed |

## 1. Mode Ladder

| Item | Value |
| --- | --- |
| Operator gets | An ordered list of sizes; the FPS you choose picks the mode between takes, a ceiling per entry holds in a take |
| How used | WebUI Settings > Modes (card "Mode Ladder", "Activated sensor modes", drag rows, Save/Revert, dry-run messages); FPS pills show "Resolution ladder on"; touch UI shows a locked Compression field "set by Mode Ladder" |
| Commands | `get_mode_ladder`, `set_mode_ladder resolutions= enabled= ramp_ready= dry_run=` (`App:14090-14093`) |
| State fields | `fps_take_max`, `ladder_active`, `ladder_resolution`, `ladder_ramp_ready`, `ladder_enabled`, `ladder_override`, `ladder_count`, `ladder_text`, `ladder_tops` (`CC:178-186`, copied in `App:327-334`, `App:9491-9498`) |
| Config | `$XDG_CONFIG_HOME/apertar-core/mode_ladder.conf` (`enabled`, `ramp_ready`, `resolutions`; old key `rungs` still read) |
| Entry format | `WxH:BITS:hdr\|sdr[:FPS[:none\|lossless_jpeg\|lossy_3to1\|lossy_5to1]]` |
| Env | `XDG_CONFIG_HOME`, `HOME` for the file path only |
| Touches original | New `src/camera/ModeLadder.hpp` (pure logic, 344 lines). In `CC` hooks into `setResolution`, `setFps`, `setRecordingFormat`, `setRawBitDepth`, `setClearHdr`, `setStillExposureMode`. While on, `set_resolution`, `set_raw_bit_depth`, `set_cdng_compression`, `set_lossy_dng_ratio` and the format switch refuse with "turn the ladder off"; `set_clear_hdr` becomes an override (`ladder_override`). Presets must match the rung. `modeLadderPath` copies upstream `persistedSettingsPath` (a second store file) |
| Relation | New area plus extends-in-place of the setters |
| Default | `enabled=false` (`ModeLadder.hpp:47`); a broken file leaves it off (`:340`). Stock camera is unchanged until the operator turns it on |
| Needs | Probe of sensor modes (feature 7/8) for "Add from the sensor's modes" |
| Tested | Host test 28/28; Pi 2026-10-28 socket, two takes, presets (`fork-log.md:87`). `e16033e` ladder data for the UI: built, not tested (`:96`). Clear HDR override: not run |
| Commits | `88e644d` `0041ba0` `3cae990` `ab972fe` `09256a7` `a7b6f82` `cdf83cd` `e16033e` `62c1711` `d44b177` (override); UI `c716dec`, WebUI `920beb0` `e6ee751` `854fe43` |
| For development | Any new setter that changes size, depth, HDR or compression must call the ladder's refusal at its top, and any new mode field must go into `ladder_*` state in all three serialisers (`settingsEvent`, `settingsBody`, web block) |

## 2. IMX585 modes from tables

| Item | Value |
| --- | --- |
| Operator gets | Size list per class (SDR 12, SDR 10, Clear HDR 12, Clear HDR 16): 40 SDR sizes per depth, 29 in Clear HDR 12-bit, 33 in 16-bit; modes under 1280 wide hidden; mono recognised. The 1.85:1 crops are 3840x2072 and 1920x1036 (were 3840x2076, 1920x1038) |
| How used | Existing `set_resolution`; WebUI family pills and ratio row; `list_sensor_modes` |
| Commands / state | `set_resolution`, `list_sensor_modes` (both existing; the second came with fork main); state `sensor_mono` (`App:9479`) |
| Config | Existing `resolution_width` / `resolution_height`; old saved values 3840x2076 and 1920x1038 are rewritten at every clamp (`CC:703`) |
| Env | `APERTAR_IMX585_MIN_MODE_WIDTH` (default 1280, 0 shows all; `Imx585Modes.hpp:105`) |
| Touches original | New `src/camera/Imx585Modes.hpp` (254 lines) and `tools/imx585_modes_test.cpp`. Replaces whitelist functions (`CC:366-396` @upstream) and the IMX585 branch of `sensorModeForRequestedResolution` (`CC:2244-2258` @upstream). Every `sanitizeSettingsForSensor` call got a third argument (mono). A driver-adjusted mode is refused, not silently used |
| Relation | Replaces upstream code. Old `isImx585*Resolution` helpers still sit at `CC:435-510` for the migration |
| Default | On. A stock IMX585 sees a different, longer size list and renamed crops |
| Needs | the cinemate-port imx585 driver for the full list |
| Tested | `imx585_modes_test` 44 checks, desk; `900d282` "Not run on a Pi"; `fork-log.md:138` not run on the camera |
| Commits | `caa0153` `900d282` `a47dc28` `8e8ea2e` (preset migration) `f60e301` (fork-main sensor probe) |
| For development | The size list is copied in three places: `Imx585Modes.hpp`, WebUI (`WCP` ~8912) and the driver table. A driver table change drifts silently |

## 3. IMX585 driver: modes and timing

| Item | Value |
| --- | --- |
| Operator gets | 187 modes (12-bit SDR 62, 10-bit SDR 62, Clear HDR 12-bit 29, 16-bit 34) from 960 to 3840 wide at 1x1 and 2x2, where the Apertar branch had 21; RAW10 in 4K; mono gains Y10; new line timing (HMAX 472 for 12-bit, own 10-bit table, VMAX floor = window rows + 70) |
| How used | Install the driver by DKMS (`APERTAR.md`); sizes show up in `list_sensor_modes` |
| Interfaces | No socket or HTTP. See feature 6 for controls |
| Touches original | `imx585.c` on `origin/apertar`: `supported_modes[]` rewritten, the 18 hand-written crop register tables replaced by registers derived from `mode->crop`, `HMAX_table_4lane_4K` and `base_vmax` rewritten, new `supported_10bit_modes[]`. 55 commits ahead of `origin/apertar` |
| Relation | Replaces driver tables, with a parallel 10-bit table |
| Default | On with the driver |
| Needs | Pi 5 / CM5 (RP1), 4 lanes, kernel 6.12 |
| Tested | Crops listed on the Pi 2026-10-26, DKMS install 2026-11-01; 1920/2048-wide families host only; no capture logs in the repo |
| Commits | `e711fc9` `f82d624` `3414768` `b050b7c` `11178c8` `3680bf4` `5901dc8` `c0f5404` `8f508fb` `d47cbd8` `18c1eb2`; merge `6f25d7f`; docs `56de0cc` `cd548ef` |
| For development | A mode table audit runs at probe and warns in dmesg (`74b9b73`, `aa6c723`); host replays `tools/replay_mode_table_audit.py`, `tools/check_window_alignment.py`. Run them after any table edit. `fork-log.md:276` says four Apertar-Studio main commits (`3680bf4` `c0f5404` `11178c8` `70bdb26`) were not taken, yet the inventory lists them among the port driver commits; check which is true before a merge (unconfirmed) |

## 4. IMX585 driver: Clear HDR colour and the windowed gate

| Item | Value |
| --- | --- |
| Operator gets | Colour sensor offers 12-bit and 16-bit binned 1080p Clear HDR and 12-bit HDR without config; mono needs the `ccmp` overlay parameter for 12-bit HDR |
| How used | `dtoverlay=imx585,...,ccmp` in config.txt for mono. Developer: `options imx585 clearhdr_windowed_binning=1` in `/etc/modprobe.d` offers 33 windowed 2x2 crops in 12-bit HDR for a test; `tools/clearhdr-gate/pedestal_check.py` checks DNGs |
| Config | module parameter `clearhdr_windowed_binning` (`imx585.c:1040`), overlay parameter `ccmp` |
| Touches original | `get_mode_table`, `get_format_code`, `enable_streams`, `update_hmax` extended; new gate and kit |
| Relation | Extends in place; the gate is new |
| Default | Gate off; the 33 crops are unvalidated in 12-bit HDR |
| Needs | `imx585_clearHDR.json` tuning file (`fork-log.md:282`, outside the repo, must be in every image) |
| Tested | CM5, kernel 6.12.93, link 891 MHz with `rp1-overclock`, seven original modes clean; 1039.5 MHz not re-tested after the blend fix; gate never run |
| Commits | `70bdb26` `b6a6f5b` `c1350b0` `3fa673c` `c0f5404` `00059f6` `0a99f14` `c3fafc2` `90eef64` |
| For development | The Core side of Clear HDR (merge, 16-bit crop) belongs to fork main's Clear HDR set; this entry is only the driver part |

## 5. IMX283 sensor family

| Item | Value |
| --- | --- |
| Operator gets | An IMX283 (5472x3648) is detected and offers 57 modes (42 at 12-bit, 15 at 10-bit) in seven readout families with 1:1 to 2.55:1 crops; the picture crop skips the optical-black columns |
| How used | Fit the module, install the driver, add `dtoverlay=imx283[,cam0][,always-on][,link-frequency=360000000]`; pick sizes in the WebUI (bases and ratios) or `set_resolution` |
| Commands / state | `set_resolution`, `list_sensor_modes` (existing) |
| Env | `APERTAR_IMX283_PROBE_FPS=1` (probe only, `CC:3389-3418`); driver module parameters `crop_vmax` (default 1, Apertar docs say run 0) and `experimental_modes` (default 0, hides 16 unvalidated rows) |
| Touches original | Core: fifth entry in upstream's `SensorFamily` enum and its per-sensor switches (`detectSensorFamily`, `sensorFamilyName`, `h264CaptureResolutionForSensor`, ScalerCrop in `controlsForSettings`, `sensorModeForRequestedResolution`, candidate list); new `src/camera/Imx283Modes.hpp` (144 lines), `activeAreaScalerCrop` in `ScalerCropGeometry.hpp:66-92`, `tools/imx283_modes_test.cpp`. Exact driver mode with exact bit depth required. Driver: 93 commits on Will Whang's `origin/master`, 8 files, `imx283.c` +1723 |
| Relation | New area that extends upstream functions in place; the facts sit in a header where upstream keeps them in `CC` |
| Default | Inert without an IMX283 |
| Needs | imx283 driver `cinemate-port`, kernel 6.12+, Pi 5/CM5 (4 lanes). With an IMX585 on the same machine the IMX283 needs `always-on` (`hardware-log.md:1077`). Core hard-codes the 57 modes; it does not read them from the driver |
| Tested | Core: desk only, "Not yet run on the camera" (`fork-log.md:138`). Driver: built; UHD 10-bit window on one preview frame; two 2x2 DNGs measured; "not run on hardware" for the last 9 commits; no fork-log row |
| Commits | Core `c48e693` `a47dc28`; driver mode tables `95183c8` `af62354` `773c5bb`, geometry `4ef5277`, window `335781d`, kernel 6.12 `16de05f`, install `fea3d35`, docs `68b7dc9` |
| For development | The Boot Config sensor list has no IMX283 (`sweep-board-support.md:457`). The driver history flips back and forth (window left 236/924, `crop_vmax`), so read `APERTAR.md` "Open questions" before touching a row |

## 6. Mode geometry V4L2 controls

| Item | Value |
| --- | --- |
| Operator gets | `v4l2-ctl` lists read-only controls: Mode Binning, Mode Crop Left/Top/Width/Height; the IMX283 adds Mode Active Left/Top/Width/Height. `get_selection` CROP gives each mode's real window, so libcamera computes scale and binning right |
| Interfaces | imx585 custom ids +10..+14; imx283 base `V4L2_CID_USER_BASE + 0x2100`, ids +0..+8; found by name in cinepi-raw `core/driver_mode_metadata.hpp:328`; Core does not read them |
| Touches original | New controls beside the original; `get_selection` extended |
| Relation | Beside original |
| Default | On |
| Needs | the new drivers; cinepi-raw to use them |
| Tested | 585: Pi 2026-10-26; 283: "measured on a CM5" in comments. The cinepi-raw comment that the 283 lacks Active Width/Height is stale |
| Commits | 585 `b703f46` `24172e6` `97649ba`; 283 `4ef5277` `f46001a` `d810aa7` |
| For development | Core keeps its own tables (features 2, 5), so these controls are the check, not the source |

## 7. Sensor-probe FPS ceiling

| Item | Value |
| --- | --- |
| Operator gets | Max fps comes from the sensor probe, the old table is the fallback: 4K SDR to 60, IMX585 lossless no longer capped at 30; `fps_max` in the state |
| How used | Automatic; WebUI/touch FPS pills cap at `fps_max` |
| State | `fps_max`, `iso_max`, `fps_take_max` |
| Env | `APERTAR_FPS_LIMIT=table` (old `min(table, probe)`), `APERTAR_LOSSLESS_FPS_LIMIT=<n>` (30 restores the old cap), `APERTAR_SENSOR_PROBE` (default on), `APERTAR_IMX283_PROBE_FPS` |
| Touches original | New `src/camera/FpsCeiling.hpp` (std-only, `tools/fps_ceiling_test.cpp`); extends fork main's `probedMaximumFps` (`min(table, probed)`) by flipping it to probe-wins; `maxFps` in `configureAndStart` |
| Relation | Extends fork main in place; fork-main's probe `f60e301` is the base |
| Default | On. A stock camera gets higher ceilings; 16-bit Clear HDR at 4K still reads 30 but runs 27 (`fork-log.md:147`) |
| Needs | the probe at start |
| Tested | Host test only; `fork-log.md:138` not run on the camera. `bcedbe5` removed the `[camera] max_fps` hardware key |
| Commits | `d44b177` `97adea0` `bcedbe5` `6d217c7` `31d5418` `0bac3db` |
| For development | `fps_max` is the mode's ceiling, `fps_take_max` the ceiling inside a take (ladder); the UIs read both |

## 8. Binning and crop per mode

| Item | Value |
| --- | --- |
| Operator gets | `list_sensor_modes` rows carry `crop`, `binning`, `binning_source` (driver, inferred, unknown); state carries the running mode's values |
| State | `sensor_binning`, `sensor_binning_source`, `sensor_crop` (`App:227-229`) |
| Commands | `list_sensor_modes` (`App:12724`) |
| Touches original | Extends fork main's startup probe with two struct fields and `SensorBinning` in `CameraController.hpp` |
| Relation | Extends in place |
| Default | On |
| Needs | probe; driver controls for source "driver" |
| Tested | Pi: `list_sensor_modes` and `get_state` verified (`fork-log.md:36`) |
| Commits | `4ab1057` `3a18db0` |
| For development | `list_sensor_modes` is not in upstream 1.6.0; it came with fork main |

## 9. Clear HDR holds ISO and WB, measured ISO

| Item | Value |
| --- | --- |
| Operator gets | Entering Clear HDR turns auto ISO and auto WB off at the values in use and turns them back on in SDR; `set_iso_auto enabled=false` locks the measured gain; auto is refused in Clear HDR; the UIs show the gain in use and the ISO ceiling |
| Commands | `set_iso_auto` (`App:12995`), `set_wb_auto` (`App:13036`), `set_clear_hdr` (`App:13150`), all existing; `setIsoAuto` now takes a bool |
| State | `iso_actual`, `iso_max`, `iso_auto_after_clear_hdr`, `wb_auto_after_clear_hdr` |
| Config | `camera_settings.conf` `iso_auto_after_clear_hdr`, `wb_auto_after_clear_hdr`; `apertar-hardware.conf [camera] clear_hdr_iso_max_12bit=720`, `clear_hdr_iso_max_16bit=1585` (template `App:5078`, parsed `CC:2976`) |
| Touches original | `setIsoAuto` (signature changed), `setClearHdr`, `setWhiteBalanceAuto`, `CaptureSettings` in `Types.hpp`; touch UI reads `isoMax` (`CameraPage.qml:522`) |
| Relation | Extends in place, on top of fork main's Clear HDR |
| Default | Active whenever Clear HDR is on; SDR cameras only get the new state fields |
| Needs | none |
| Tested | Pi preview 2026-10-28 (caps 720 and 1585, refusals); `d44b177` Clear HDR override not run |
| Commits | `8175273` `646a194` `6d217c7` `e5757d7` |
| For development | The two hold flags are persisted in `camera_settings.conf` (`CC:945`, `CC:956`); check what a restart in Clear HDR restores before changing them (unconfirmed) |

## 10. Preview temporal denoise switch

| Item | Value |
| --- | --- |
| Operator gets | A switch for temporal denoise in the preview ISP. Off: libcamera loads a copy of the tuning file without `rpi.denoise` tdn blocks, the preview gets lighter at 4K Clear HDR 16-bit; DNGs do not change |
| How used | WebUI Settings > Performance card (`WCP:16165`); touch UI none |
| Commands / state | `set_preview_tdn enabled=true\|false` (`App:13205`); `preview_tdn`, `tuning_file_active` (`App:9527`) |
| Config | `camera_settings.conf` `preview_tdn` (default false). Restarts the pipeline on change |
| Touches original | New `src/camera/TuningTdnStrip.hpp` (451 lines, own JSON parser), `tools/tuning_tdn_strip_test.cpp`; `CC:7305-7320` wraps the resolved tuning path; beside upstream `DefaultTuningSelection.hpp` |
| Relation | Sits beside original |
| Default | **Off, so a stock camera loses TDN in the preview** after the update. Carried over format changes (`CC:11348`) |
| Needs | tuning file with `rpi.denoise` |
| Tested | Host test with golden bytes; Pi build 2026-11-04; "desk only (not built)" in the commit |
| Commits | `e625c68` |
| For development | The camera and preview use `activePath`, `tuningPath` stays the resolved file; any tuning-path check must use the resolved one |

## 11. Raw camera buffer count

| Item | Value |
| --- | --- |
| Operator gets | No control. One libcamera request per raw buffer: 4 in SDR, 8 in Clear HDR, 2 more on FAT/NTFS. Fewer capture gaps in Clear HDR takes |
| Env / config | `APERTAR_RAW_CAMERA_BUFFERS` (3-16, wins, `CC:1469`); `/home/pi/apertar-media-tune.conf` keys `raw_buffers`, `extra_raw_buffers`; override `/run/apertar-media/media-tune.override.conf` |
| Touches original | Replaces `kActiveRequestCount` (`CC:1024` @upstream); third helper beside `h264CameraBufferCount` and `proresCameraBufferCount`; new `util/MediaProfile.hpp`, `util/MediaTune.hpp` |
| Relation | Replaces upstream code |
| Default | On, silent |
| Needs | none; the tuning file is optional |
| Tested | `db17860`: Pi, 4K Clear HDR 16-bit, 5 takes per case, lossless 25 fps gaps 41 to 1, 30 fps not fixed. `26da30e` built, not tested; `2edc6d0` "Core not restarted yet" |
| Commits | `db17860` `26da30e` `2edc6d0` |
| For development | The raw copy now runs on a recorder worker holding buffers-2 (`351a3ee` `94ac68d`, recording area), so the buffer count is also the worker's queue depth |

## Left to other areas (main home elsewhere)

One line each: clip name template, CineMate Log, speed ramp and stretched WAV, frame-rate phase lock, conform fps, drive trim, storage pre-roll, media fault survival, RAM write buffer and RT capture priority belong to Recording and Media. Presets carrying operating-mode switches (`8e8ea2e`) and settings carried across recording-format profiles (`CC:11241-11266`) belong to Presets. Build without libcamera (`5f5cea2`) belongs to Build and platform. The raw copy worker (`351a3ee` `d9f00d4` `94ac68d` `43a54f3`) belongs to Recording.
