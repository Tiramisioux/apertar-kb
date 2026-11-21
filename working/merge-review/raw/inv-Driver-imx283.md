# Inventory: Driver-imx283 (stage 1, no judging)

Read at: imx283 driver `cinemate-port` `68b7dc9` against `origin/master` `7751c32` ("add UHD mode"). 93 commits, 8 files, +1993/-110, `imx283.c` +1723. Core side read at `cinemate-port` `01f170c`. Upstream 1.6.0 (`/home/user/wt/core-upstream`, `/home/user/wt/ui-upstream`): `grep -rn -i imx283` returns nothing in both. Original Apertar 1.6.0 has no IMX283 support (confirmed). The driver baseline `origin/master` is Will Whang's driver, not an Apertar branch (there is no Apertar IMX283 driver branch; the imx585 driver has `origin/apertar`).

Diff file used: `/home/user/build/review/imx283.diff` (2101 lines). Commit authors: Patrik Eriksson 79, Claude 9 (d810aa7..68b7dc9), Will Whang 3, "Your Name" 2. 84 of 93 are on `origin/cinemate-modes`; the 9 above it are the port fixes and docs.

## 1. Features touching this unit

| # | Feature | What the operator gets | Files | Commits | Tested (per commit text) |
| - | ------- | ---------------------- | ----- | ------- | ------------------------ |
| F1 | Mode set: 57 default modes (42 at 12 bit, 15 at 10 bit) in seven families (Mode 0, 2, 2A, 3 at 12 bit; Mode 1, 1A, 1C at 10 bit), each with centred aspect-ratio crops 1:1 to 2.55:1 | Resolution ladder on the IMX283 of 57 sizes | `imx283.c` tables `supported_modes_12bit[]`, `supported_modes_10bit[]`, macros `IMX283_ASPECT_MODE`, `IMX283_ASPECT_MODE_1C`, `IMX283_CROPPED_1X1_MODE`, `IMX283_CROP_1X1` | 95183c8 (1C, 2A), 0700acd, 4eb1bea, 8648db4 (18 fixed crops, later dropped), be25442 (2A), af62354 (all modes), 773c5bb (WP-283-6 ratio family), 7b4614c, 2070416, bbedfb3, cf61fe8, 2ef4151, 07b1aab, 06890e5, 4948e70 (rebuild), 05d1493, d1763e0, ad7082b, 2947d23, c3fae40 | Built; MODE_1C base entry verified on a Pi preview frame (335781d, cb925e5). Aspect rows: no hardware stream recorded except the two 2x2 DNGs (4761af3). Commit text of d810aa7..68b7dc9: "not run on hardware" |
| F2 | Per-mode sensor crop reported to libcamera (CROP, CROP_DEFAULT, TRY crop) | libcamera shows right analogCrop, binning, ScalerCropMaximum | `imx283.c` `imx283_get_selection`, `__imx283_get_pad_crop`, `imx283_set_pad_format`, `imx283_open` | f162db7, 835cf14, 4a1662e (oops fix), d810aa7 (CROP_DEFAULT = active area), 6f6410d, 5d1c193 | d810aa7, 4a1662e: built on x86 copy; oops found on CM5 kernel 6.12.93 |
| F3 | Read-only mode-geometry V4L2 controls (9): Mode Binning, Mode Crop Left/Top/Width/Height, Mode Active Left/Top/Width/Height | cinepi-raw reads real binning/crop/active area, DNG ActiveArea | `imx283.c` `V4L2_CID_IMX283_*`, `imx283_cfg_mode_*`, `imx283_update_mode_metadata`, `imx283_active_width/height` | 4ef5277 (WP-283-5), f46001a (Active Left/Top), e8c7093, d9915be, 4761af3 | Active Left/Top "measured on a CM5" (comment); 2x2 shortfall measured on 2 DNGs then overturned |
| F4 | Vertical crop via sensor VCROP registers (MDSEL3/4 VCROP_EN, VWIDCUT, VWINPOS, Y_OUT_SIZE, WRITE_VSIZE) for every mode with `veff` and `vbin_ratio` | Cropped aspect rows scan fewer lines | `imx283.c` `imx283_start_streaming` | 0700acd (Mode 0 only, per EXPERIMENTAL_CROPS.md), widened to every mode with veff later (commit not pinned, probable), 58fdcaf, 335781d (veff 2176 for 1C) | 335781d verified on Pi (preview frame, 638 vs 642 lines predicted) |
| F5 | Module parameter `crop_vmax` (default 1): per-crop VMAX floor `crop_min_VMAX` lowers VBLANK minimum, so higher fps than parent mode | Higher advertised fps on crops (values UNMEASURED) | `imx283.c` `imx283_min_vmax`, field `crop_min_VMAX`, `MODULE_PARM_DESC` | 134455d, b549b0d, 94eb7e2 (default on), 8315435, 2d4f0f0, bbedfb3, cf61fe8, 2ef4151 | Not measured; APERTAR.md says Apertar runs `crop_vmax=0` |
| F6 | Module parameter `experimental_modes` (default 0): hides 16 unvalidated entries (1S, 4, 5, 6 and twelve MODE_1C aspect rows) | Unvalidated modes off unless asked | `imx283.c` `build_filtered_mode_table`, `get_mode_table`, field `.experimental` | 8f2b230 (WP-283-4), d21243e, 2070416 (opened aspect rows), c3fae40 | Gate not hardware-tested |
| F7 | Added readout modes: Mode 3 (3x3, 12 bit), 1S (3000x3000), 4, 5, 6 (the last four experimental) | 1824x1216 60 fps class mode (enabled), others hidden | `imx283.c` | af62354, e1f1921, 0700acd.. | Mode 3 floor from Sony max fps; no hardware |
| F8 | Probe-time mode-table self-check (`imx283_check_mode_table`), `dev_warn` only | dmesg warnings for bad table rows | `imx283.c` | 4ef5277 chain, 4948e70 chain | x86 syntax check only |
| F9 | MODE_1C window origin: `.left` 924 (centred), 236 kept as `IMX283_MODE_1C_WINDOW_LEFT_HW_CONFIRMED`; `.top` 852 (NOT centred vs corrected active.top 40; centred would be 784) | UHD 4K 10-bit window position | `imx283.c` macros and `imx283_mode_1c_window` | c20c603, 5828d5b, 3c2310e, 812c058, de6693c, cb925e5 (value flips 236/924/236/924) | 924: one ISP preview frame OK; raw OB margins not checked (APERTAR.md "Open questions") |
| F10 | Active-area origin corrected: `imx283_active_area` was .top=108 .left=40, now .top=40 .left=108 | Right crop origin in every row | `imx283.c` | 4948e70, 05d1493, 4761af3 | Measured 2784x1828 frame, OB 0-47, picture 48-2783 |
| F11 | HTRIMMING_END = crop.left + crop.width (was +1) | One column less at the right edge | `imx283.c` `imx283_start_streaming` | WP-283-3 b67ea62 / 7e98970 | no hardware record |
| F12 | Overlay parameter `link-frequency` (`dtoverlay=imx283,link-frequency=360000000`) | Choose 360 MHz link (720 Mbps per lane) | `imx283-overlay.dts` | 257c9cf | not tested on hardware (commit text) |
| F13 | Kernel 6.12 port: `<linux/unaligned.h>`, `v4l2_subdev_state_get_format/crop` in place of `*_get_try_*`; README says 6.12 or newer | Builds on Pi OS Bookworm 6.12 | `imx283.c`, `README.md` | 289131a, 24f7bf0 -> 146d24f (revert), 16de05f, 6f6410d, 5d1c193, 235a58c | Built on Pi (6.12.93) |
| F14 | Install flow: `setup.sh` `dkms install --force`; `dkms.conf` drops `REMAKE_INITRD`; `dkms.postinst` adds `-Wno-unit_address_vs_reg` | Module replaces kernel's stock imx283; no dtc warning | `setup.sh`, `dkms.conf`, `dkms.postinst` | fea3d35, fcbda11, e8e3d4a, 15515f1 | on Pi (hardware-log 2026-11-10) |
| F15 | Docs: `APERTAR.md` (new, 207 lines: branch, install, config.txt, modprobe, mode table, open questions), `EXPERIMENTAL_CROPS.md` (new 152 lines, marked STALE), README (kernel version, clone URL `-b cinemate-port`, `/boot/firmware/config.txt`) | Apertar user install guide | docs | 83bdbb7, 30554d5, e1f1921, d21243e, 235a58c, 53ae581, 805a773, 68b7dc9 | docs only |
| F16 | Log noise: per-stream lines moved from `dev_err` to `dev_dbg` | Quiet dmesg at stream start | `imx283.c` | 4064e88 | built only |
| F17 | Bounds check in `imx283_get_format_code` for unsupported code | No read past `codes[]` | `imx283.c` | d6ec1c7 | built only |

## 2. Interfaces (all kernel/dtoverlay side; no socket, HTTP or UI in this unit)

| Kind | Name | Where | New or changed |
| ---- | ---- | ----- | -------------- |
| Socket commands | none | | |
| HTTP routes | none | | |
| State fields | none (Core state is in the Core unit) | | |
| Events | none | | |
| Module parameter | `crop_vmax` (bool, 0444, default 1) | `imx283.c` (after `IMX283_FORMAT` block, port line ~103-117) | new |
| Module parameter | `experimental_modes` (bool, 0444, default 0) | same | new |
| Overlay parameter | `link-frequency` -> `link-frequencies#0` of `cam_endpoint` | `imx283-overlay.dts:110-117` | new |
| V4L2 controls (read-only, custom base `V4L2_CID_USER_BASE + 0x2100`) | "Mode Binning" id +0, "Mode Crop Left" +1, "Mode Crop Top" +2, "Mode Crop Width" +3, "Mode Crop Height" +4, "Mode Active Left" +5, "Mode Active Top" +6, "Mode Active Width" +7, "Mode Active Height" +8 | `imx283.c` | new; discovered by name (not id) by cinepi-raw `core/driver_mode_metadata.hpp:328-331` |
| V4L2 control count | `v4l2_ctrl_handler_init(..., 16)` -> 21 | `imx283.c` `imx283_init_controls` | changed |
| Subdev ops | `get_selection` CROP_DEFAULT answers `imx283_active_area` (was current mode crop, fell through with BOUNDS); `set_pad_format` writes TRY crop; `enum_frame_size`, `get_pad_format`, `open` use wrappers | `imx283.c` | behaviour changed |
| Env var | none in the driver. Core side: `APERTAR_IMX283_PROBE_FPS=1` (Core `CameraController.cpp:3389-3420`) | Core | new, Core unit |
| Config keys | `/etc/modprobe.d/imx283.conf` `options imx283 crop_vmax=0 experimental_modes=0` (user-created, documented in APERTAR.md); `config.txt` `dtoverlay=imx283[,cam0][,always-on][,link-frequency=360000000]` | docs | new documented keys |
| Files on disk | `/usr/src/imx283-0.0.1`, `/boot/overlays/imx283.dtbo` (dkms.postinst), `/sys/module/imx283/parameters/{crop_vmax,experimental_modes}` (read) | | unchanged paths; `--force` new |
| UI elements | none (WebUI/touch UI offer the 57 sizes via Core `Imx283Modes.hpp`) | | |

## 3. Original code modified (baseline = `origin/master`, Will Whang's driver)

| Region | Where @cinemate-port | Change | Kind |
| ------ | -------------------- | ------ | ---- |
| `#include <asm/unaligned.h>` | `imx283.c:10` | `<linux/unaligned.h>` | behaviour-changed (kernel floor 6.12) |
| `imx283_active_area` | `imx283.c` ~290-300 | .top/.left swapped (108/40 -> 40/108) | behaviour-changed (comment: origin was wrong) |
| `imx283_UHD_area` rectangle (236,0,3840x2160) | removed | replaced by `imx283_mode_1c_window` (.top 852, .left 924) | removed/rewritten |
| `struct imx283_mode` | | added `crop_min_VMAX`, `veff`, `vst`, `vct`, `hbin_ratio`, `vbin_ratio`, `active_width`, `active_height`, `experimental` | extended-in-place |
| `supported_modes_12bit[]` | | MODE_0/MODE_2 gain veff/binning; old MODE_2A entry (2784x1548, 3088+8 rows) replaced by family rows 2736 wide x 1540..1072; MODE_3, 4, 5 added; 13+3+10+13 aspect rows added | rewritten + extended |
| `supported_modes_10bit[]` | | MODE_1 gain veff/binning; MODE_1A height 3078 -> 3076; MODE_1S, 6 added; MODE_1C rewritten (veff 2176, window, ob); 3+9+12 aspect rows | rewritten + extended |
| `get_mode_table()` | `imx283.c` ~1444 | returns static filtered copies (function-local static arrays, built once) instead of the const tables | rewritten |
| `v4l2_find_nearest_size()` in `imx283_set_pad_format` | | replaced by `imx283_find_nearest_mode()` (sum of absolute width and height differences) | replaced |
| `imx283_start_streaming` vertical block | | old: `Y_OUT_SIZE = height - vob`, `WRITE_VSIZE = height`; new: `veff` path with VCROP enable, `v_widcut`, `v_pos` (vflip aware) else `crop.height/vbin` | rewritten |
| HTRIMMING_END | | `+1` removed | behaviour-changed |
| `imx283_set_framing_limits`, `imx283_init_controls` vblank | | min VBLANK from `imx283_min_vmax()`; calls `imx283_update_mode_metadata` | extended-in-place |
| `imx283_set_ctrl`, `enum_frame_size`, `update_image_pad_format`, `open` | | `mode->width/height` -> `imx283_output_width/height()` (identity wrappers) | moved (wrapped) |
| `imx283_open` try crop | | `imx283_active_area` -> mode crop; `v4l2_subdev_state_get_*` | behaviour-changed |
| `imx283_get_selection` CROP_DEFAULT | | split from BOUNDS; returns active area | behaviour-changed |
| `__imx283_get_pad_crop` ACTIVE | | returns pointer to a function-local `static struct v4l2_rect` copy | rewritten |
| `imx283_get_format_code` | | bound check | extended-in-place |
| `imx283_standby_cancel`, start_streaming logs | | `dev_err` -> `dev_dbg` | behaviour-changed |
| `imx283_probe` | | calls `imx283_check_mode_table` for both tables | extended-in-place |
| Formatting | `imx283_i2c_driver`, trailing space, blank lines | tabs; `MODULE_LICENSE` line lost its final newline | noise |
| `imx283-overlay.dts` | | `link-frequency` override added | extended-in-place |
| `setup.sh` | | `--force` | extended-in-place |
| `dkms.conf` | | `REMAKE_INITRD=no` deleted | removed |
| `dkms.postinst` | | `-Wno-unit_address_vs_reg` | extended-in-place |
| `README.md` | | kernel 6.12, clone URL of the fork branch, `/boot/firmware/config.txt` | edited |

## 4. New abstractions

| Name | Purpose | Upstream equivalent | Used by |
| ---- | ------- | ------------------- | ------- |
| `IMX283_ASPECT_MODE()` macro (15 args) | Generates one aspect-ratio row from delivered size, derives crop from `imx283_active_area` | none (no IMX283 in 1.6.0). The only Apertar driver precedent is the imx585 tables in the imx585 repo (separate unit) | tables |
| `IMX283_ASPECT_MODE_1C()`, `IMX283_CROPPED_1X1_MODE()`, `IMX283_CROP_1X1()` | per-family row macros. The last two: `IMX283_CROP_1X1` is unused, `IMX283_CROPPED_1X1_MODE` is only reachable through it (so unused) | none | tables (dead) |
| `IMX283_MODE_1C_WINDOW_LEFT{,_HW_CONFIRMED,_CENTRED}` macros | compile-time choice between two candidate origins | none | `imx283_mode_1c_window`, base 1C entry |
| `imx283_mode_1c_window` rectangle | reference rectangle for MODE_1C crops | none | 1C rows |
| `imx283_output_width/height/crop()` | identity wrappers (return `mode->width/height/crop`) | none | ~15 call sites |
| `imx283_active_width/height()` | delivered picture size with optional override fields | none | controls, self-check |
| `imx283_find_nearest_mode()` | mode lookup (replaces `v4l2_find_nearest_size`) | `v4l2_find_nearest_size()` (kernel helper, used by base driver) | `set_pad_format` |
| `build_filtered_mode_table()` + function-local statics in `get_mode_table()` | hide experimental entries | none (base returned the const tables) | `get_mode_table` |
| `imx283_check_mode_table()` | probe-time `dev_warn` consistency checks (crop inside active area, binning set, even origin, divisibility, width match, active size) | none | probe |
| `imx283_update_mode_metadata()` / 9 `mode_*_ctrl` members | publish geometry through custom read-only controls | imx585 driver in the same campaign has the same control names | `set_framing_limits` |
| `imx283_min_vmax()` | selects `crop_min_VMAX` or `min_VMAX` | none | limits |
| Core `src/camera/Imx283Modes.hpp` (144 lines, header-only, namespace `apertar::imx283`) | Core's own copy of the 57-row mode table (active size, binning, floor fps), `normalise`, `transportOf`, `findTransport`, `activeOfTransport`, `floorFps` | upstream Core has no IMX283 and no per-sensor mode-table header; its sensor sizes are inline in `CameraController.cpp` (separate Core unit decides) | `CameraController.cpp:13, 656-690, 2272-2640, 3332, 3536, 10970-11017, 12824` |
| Core host test `tools/imx283_modes_test.cpp` | tests the header | upstream Core has no tests | host build |
| Referenced but absent from this repo: `development/imx283-active-size/{BRIEF,REBUILD,ROUND2,GAP}.md`, `development/imx283-crop-fps/`, `check_mode_table.py`, `ratio_audit.py` | cited in code comments (`imx283.c` many places) | | the comments point to files that do not exist in `git ls-tree cinemate-port` (9 files only) |
| Internal vocabulary in comments | WP-283-1..6, DEC-4, REBUILD.md section 7, "Fact 2", "Round 2 Defect C4" | | meaningless to the original developer |

## 5. Removed, narrowed or hidden vs baseline

| What | Where | Effect |
| ---- | ----- | ------ |
| Old MODE_2A 2784x1548 entry | tables | replaced by 10 rows 2736x1540..1072 (no full-frame 2A entry); old size gone |
| MODE_1A 5568x3094 (3078) | table | now 5568x3092 (3076, even Bayer origin) |
| `imx283_UHD_area` (236,0) | | gone; 1C base entry window .left now 924 (was 236), .top 852 (was 0) |
| Kernel < 6.12 | `<linux/unaligned.h>` | module does not build on 6.6 (README states 6.12 or newer) |
| Unvalidated entries (1S, 4, 5, 6, twelve 1C rows) | `experimental_modes=0` | built but hidden |
| `REMAKE_INITRD=no` | `dkms.conf` | line removed (deprecated key) |
| `v4l2_find_nearest_size()` exact-then-nearest semantics | `set_pad_format` | replaced by a different distance metric (sum of absolute differences) |
| Error-level log lines | | dmesg shows less by default |
| Stock kernel `imx283` | `setup.sh` `--force` | DKMS copy always overrides |
| Any IMX283 in Apertar 1.6.0 | | none existed; the whole family is new ground |

## 6. Board assumptions

| Assumption | Where | Note |
| ---------- | ----- | ---- |
| Pi 5 / CM5 with RP1 (Core's text and APERTAR.md "Raspberry Pi 5 or CM5"); overlay targets `csi1`/`csi0` with `cam0_clk`, `cam0_reg` | `imx283-overlay.dts`, `APERTAR.md:3` | overlay inherited from base; not Pi 5 specific by itself |
| 4 CSI-2 lanes (`data-lanes = <1 2 3 4>`) | overlay `:68`, `:91` | Pi 4B, Pi 3, Zero 2 W have 2-lane connectors: unusable there (sweep-board-support.md:329) |
| 720 MHz default link (1440 Mbps per lane), 360 MHz allowed | overlay, `link_frequencies[]` | |
| I2C address 0x1a, bus per CAM connector | Core `ApertarCoreApp.cpp:12507` | |
| gpiochip numbering, fan, RAM size, core count | none in this unit | |
| Kernel 6.12 or newer | `imx283.c:10`, README | Pi OS Bookworm with 6.12 kernel |
| `/boot/overlays/` install path (dkms.postinst) while README now says `/boot/firmware/config.txt` | `dkms.postinst` | on Bookworm `/boot/overlays` is a compatibility path (probable) |
| IMX283 + IMX585 same machine: IMX283 needs `always-on` or the IMX585 probe fails | KB `lessons/hardware-log.md:1077-1093` | seen on a CM5 rig |
| 72 MHz pixel clock hardcoded (`72000000`) | `imx283.c` | inherited |

## 7. How Core depends on the driver

| Dependency | Evidence |
| ---------- | -------- |
| Core hardcodes the 57 modes (active size, bits, binning, floor fps with `crop_vmax=0`) and optical black (96,16 / 48,4 / 32,4) | `Imx283Modes.hpp:14-60, 63-71` @cinemate-port. Not read from the driver. A driver table change with no change to this header drifts silently |
| Transport = active + OB; picture leads from the left, OB rows trail | `CameraController.cpp:3693-3694, 3733-3734`; `ScalerCropGeometry.hpp:67` |
| fps = min(probe, driver floor); `APERTAR_IMX283_PROBE_FPS=1` = probe only | `CameraController.cpp:3333-3340, 3389-3420` |
| Exact driver mode required (else rejected "adjusted by the pipeline") | `CameraController.cpp:8531-8556` |
| Core does not read the 9 "Mode *" controls (grep finds none in `src`); cinepi-raw does (`core/driver_mode_metadata.hpp:14-15, 328-331`, `cinepi/cinepi_raw.cpp:177, 267, 307`) | cinepi-raw comments at `driver_mode_metadata.hpp:123-125` say the imx283 lacks "Mode Active Width/Height"; the driver has them (`imx283.c` `imx283_cfg_mode_active_width`). Comment is stale (probable; settled by running cinepi-raw on an IMX283) |
| `crop_vmax=0` assumed by Core; driver default is 1 | APERTAR.md "modprobe.d"; `CameraController.cpp:3333`. A user who skips the modprobe file gets lower floors than Core's table; Core takes `min(probe, floor)` so the floor is only a ceiling |
| Boot Config card sensor list has no IMX283 | sweep-board-support.md:457 |
| Branch name `cinemate-port` hard-coded in Core comment | `CameraController.cpp:441-442`, `Imx283Modes.hpp:1-2` |

## 8. Port history shape (facts for stage 2)

| Fact | Evidence |
| ---- | -------- |
| Back-and-forth: Kernel 6.12 fix done, reverted, redone (24f7bf0, 146d24f, 16de05f, 6f6410d, 5d1c193) | git log |
| 18 fixed Mode-0 crops added then replaced by ratio family (0700acd.. then 773c5bb) | git log |
| `experimental_modes` gate opened for aspect rows (8f2b230 then 2070416) | git log |
| `crop_vmax` default flipped (134455d, 94eb7e2, 8315435, 2d4f0f0) | git log |
| 11-commit active-only-frames experiment 4350e3e..bbbd49b ended by a852cfe revert | git log |
| MODE_1C `.left` 236 -> 856 -> 236 -> 924 -> 236 -> 924 | comments `imx283.c` |
| Table rebuilt four times 2026-09-26 (e8c7093 .. 2947d23); 2704 correction added and removed | git log |
| Two identical-subject commits 4350e3e and 4612d68 | git log |
| Authors "Your Name" (050e2e3, 289131a) | git log |
| Fork-log.md has no row for any driver commit; recorded status of driver commits is only in each commit message ("Tested:" lines: built on x86 copy; "not run on hardware") | grep of `/home/user/apertar-kb/fork-log.md` |
| Comment mass: a large share of the 1723 added `imx283.c` lines are comments (history, measurements; share not counted); several comments describe code that changed later (c3fae40, 4e36c37, 1375c57 repaired some) | diff |
| Dead or odd code: unused `IMX283_CROP_1X1`/`IMX283_CROPPED_1X1_MODE`; identity wrappers; `static struct v4l2_rect output_crop` in `__imx283_get_pad_crop` shared across callers; static filtered tables in an inline function; `imx283_check_mode_table` warns but never fails | diff |
| Open hardware questions (APERTAR.md): MODE_1C OB at 924 on a raw frame; lens shading broken in all 1x1 modes (IPA integer scale 5472/5568 = 0); per-crop VMAX unmeasured | `APERTAR.md` "Open questions" |
