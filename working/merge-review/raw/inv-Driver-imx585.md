# Inventory: Driver-imx585 (stage 1, no judging)

Refs: port = `cinemate-port` `cd548ef`; baseline = `origin/apertar` `e5b74d3` (will127534 `1644466` + 18 crop modes of the 1.6.0 image).
Diff: `imx585.c` 2705 -> 4808 lines (+3477 -/ ~ in stat), README +123, APERTAR.md new (183), overlay +1 line, tools/ 4 new files, .gitignore +3.
Read: full `imx585.diff` (3995 lines) outside the 1900 lines of mode-table data (read headers, enum, ordering comments, audit output), APERTAR.md, README diff, overlay diff, tools headers. 55 commits, `git log --reverse origin/apertar..cinemate-port`.
Labels: confirmed = read in code; probable = inferred.

## 1. Operator-visible features

| # | Feature | What the operator gets | Commits | Evidence |
| --- | --- | --- | --- | --- |
| F1 | Mode set grows from 21 table entries to 158 (96 + 62) | 187 offered modes over 4 families (12-bit SDR 62, 10-bit SDR 62, 12-bit Clear HDR 29, 16-bit Clear HDR 34), colour. Aspect-ratio crops at 1x1 and 2x2, 960 to 3840 wide | e711fc9 f82d624 3414768 b050b7c 663449a b46cc47 9a44a4d d3253b5 5901dc8 234cccb a09ac49 4949b06 475c3ea 8917c46 d9c132e 6532d6f ef2ef51 ddf438c d5efe87 7061c74 27c7cb4 5c7fb79 047c8a9 fff39ae ceb7367 d47cbd8 8f508fb fdd767a 18c1eb2(`18c1eb2` is merged via 6f25d7f) | `imx585.c` enum `imx585_mode_id` @port:~859; APERTAR.md "Modes"; `python3 tools/replay_mode_table_audit.py` prints 96 / 62 entries (confirmed, run) |
| F2 | 10-bit SDR as its own table `supported_10bit_modes[]` (62) | RAW10: 4K, binned 1080p, all crops. Baseline had no 10-bit table; 10-bit codes reused the 12-bit table and a runtime register fixup | 11178c8, 3680bf4, d8c..(8917c46, d9c132e, 6532d6f, ef2ef51) | `port.c:2093`; baseline `imx585_apply_normal_bit_depth_regs` removed (diff) (confirmed) |
| F3 | Binned 1080p in Clear HDR | 1920x1080 binned offered in 12-bit CCMP HDR (colour) and 16-bit HDR (1920x1100 transport). Baseline: HDR = 4K only | c1350b0 3fa673c | get_mode_table colour branch (diff ~3050-3100) (confirmed) |
| F4 | 16-bit Clear HDR crops (1x1 only) | 32 crops + 3840x2200 + 1920x1100; windowed 2x2 RAW16 withdrawn (reads OB pedestal on hw) | b050b7c 663449a b46cc47 9a44a4d d3253b5 fdd767a | comment above enum; APERTAR.md "Validation" (confirmed text; hw claim is recorded in commit fdd767a, no logs in repo) |
| F5 | 12-bit CCMP Clear HDR gate: default-on colour, opt-in mono via `ccmp` overlay param | colour gets 12-bit HDR with no config; mono needs `dtoverlay=imx585,mono,ccmp` else 12-bit HDR is not offered and stream-on returns -EINVAL | 70bdb26 b6a6f5b | `imx585_probe` `clearhdr_ccmp = !mono \|\| of_property_read_bool("sony,clearhdr-ccmp")` (confirmed) |
| F6 | Clear HDR HMAX floor 550 (4-lane) at every link rate | 12-bit and 16-bit HDR keep sensor line timing the same at 1782 and 2079 Mbps/lane | c0f5404 | `IMX585_HMAX_MIN_CLEARHDR` (confirmed) |
| F7 | Per-mode HMAX tables (12-bit and 10-bit) | Baseline one table `HMAX_table_4lane_4K`; port two. 1039 MHz row 440 -> 472 (12-bit), 1188 MHz 396 -> 472; 10-bit rows 375/376 and VMAX 2200 at 1039 MHz | c0f5404 11178c8 | diff lines 43-84, update_hmax (confirmed) |
| F8 | VMAX floor derived from the window | Cropped modes get a VMAX floor `window rows + 70` (baseline `height + 72` hard-coded per entry as `base_vmax`); optional per-mode override `min_vmax_default` | 5901dc8 047c8a9 | `IMX585_CROP_VMAX`, `imx585_update_hmax` (confirmed) |
| F9 | Mode geometry as read-only V4L2 controls | `v4l2-ctl` shows Mode Binning, Mode Crop Left/Top/Width/Height | b703f46 85555d0 74ed4c6 951aeee 24172e6 97649ba | cfg structs diff ~3780 (confirmed) |
| F10 | Crop rectangle reported in native sensor coordinates | `get_selection` CROP returns the real sensor window per mode (libcamera derives binning/scale from it). Baseline reported buffer-sized crop | 74ed4c6 951aeee 24172e6 | `imx585_get_selection`, invariant comment @port:1044-1062 (confirmed) |
| F11 | Windowed readout programmed in code | `imx585_program_window()` writes WINMODE/PIX_HST/HWIDTH/VST/VWIDTH from `mode->crop` with alignment checks, instead of one register list per crop. RAW16 adds 20 sensor rows | 8f508fb d47cbd8 5c7fb79 fff39ae | diff ~2900-2960 (confirmed) |
| F12 | Mono Y10 | Mono 10-bit SDR format added (Y10) | 3680bf4 11178c8 | `mono_codes[]` +Y10, `get_mode_table` mono branch (confirmed) |
| F13 | Format-transition hardening | WDR toggle keeps current pixel format when re-picking mode (baseline forced SRGGB12/Y12); pad checks (`pad != 0` -> -EINVAL); enable_streams rejects `streams_mask != BIT(0)`, no-op if already streaming; cci_write errors now abort stream-on; 16-bit codes map to 12-bit in SDR | 3680bf4 | diff ~3400-3770 (confirmed) |
| F14 | Probe-time mode-table audit | Warnings in dmesg for alignment, VMAX floor, crop outside array, RAW16 height, windowed 2x2 RAW16, duplicate advertised size. Warn only | 74b9b73 aa6c723 | `imx585_check_mode_table` (confirmed); host replay finds 1 warning (3840x2072 at [5] and [67], different formats) (run) |
| F15 | Gate module parameter `clearhdr_windowed_binning` (bool, 0444, default off) | Opens the 33 windowed 2x2 crops in 12-bit HDR for a hardware test only | 00059f6 0a99f14 | `port.c:1040` (confirmed) |
| F16 | Sync-mode menu relabelled | "External Sync Leader" -> "Internal Sync Follower", "Follower" -> "External Sync"; register behaviour same, enum names `SYNC_INT_FOLLOWER`/`SYNC_EXTERNAL` already in baseline | (in 3680bf4 / lineage, not checked which) | diff lines 85-94 (confirmed label change only) |
| F17 | Logging | `Update minimum HMAX` summary now prints link freq; per-mode lines moved `dev_info` -> `dev_dbg` (158 lines at debug) | c18f162 | diff ~3290 (confirmed) |
| F18 | Docs | APERTAR.md (install, config.txt, modes, sizes that changed, validation); README clone URL and `/boot/firmware/config.txt`; README "CineMate branch" section (7-mode matrix, Clear HDR blend table, top-link behaviour) | e9d5759 0af0293 bd57617 56de0cc cd548ef | README diff (confirmed) |
| F19 | Hardware-gate and audit tools (host Python) | `tools/clearhdr-gate/{README.md,pedestal_check.py}` (pedestal-vs-image test on DNGs, needs numpy), `tools/check_window_alignment.py`, `tools/replay_mode_table_audit.py` | 0a99f14 c3fafc2 18c1eb2 74b9b73 | files read (confirmed) |

## 2. Interfaces added or changed

| Kind | Name | Change | Where |
| --- | --- | --- | --- |
| V4L2 control (custom) | `V4L2_CID_USER_IMX585_BASE + 10..14`: Mode Binning (1..2), Mode Crop Left/Top/Width/Height | new, `V4L2_CTRL_FLAG_READ_ONLY`, updated by `imx585_update_mode_metadata()` on every `set_framing_limits` | port diff ~3780-3830 |
| V4L2 control | `WIDE_DYNAMIC_RANGE` | now re-picks mode from the current format code; activation of `gdc_*` controls only when CCMP (new helper `imx585_activate_hdr_controls`) | diff ~3420-3460 |
| V4L2 control | HDR blend default | unchanged: control `.def = 0`, `common_clearHDR_mode` writes `0x36e2 = 0x00`. README states menu 5 is the working value and the driver does not set it | README diff; no code change (confirmed no default hunk) |
| V4L2 control | other defaults (gain, black level, HDR threshold, gain adder) | no change found in the diff | confirmed by absence in diff |
| Media bus codes | `MEDIA_BUS_FMT_Y10_1X10` added (mono) | `mono_codes[]`, `enum_mbus_code` | diff ~2764 |
| Media bus codes | `enum_mbus_code` clear HDR | colour without CCMP: 1 code, with: 2 per-colour sets; mono HDR: Y16 only unless `ccmp` | diff ~3940 |
| Device tree overlay | `ccmp = <&cam_node>,"sony,clearhdr-ccmp?"` | new overlay param | `imx585-overlay.dts:138` |
| DT property | `sony,clearhdr-ccmp` (boolean), already read-side added by 70bdb26 | new | `imx585_probe` |
| Module param | `clearhdr_windowed_binning` | new, test switch | `port.c:1040`; documented to go in `/etc/modprobe.d/imx585-gate.conf` |
| Kernel config | none (no Kconfig, no sysfs, no debugfs) | - | - |
| Log lines | `ClearHDR 12-bit CCMP: enabled/disabled (...)` at probe; `clearhdr_windowed_binning=1: ...` warning; table-audit warnings | new | probe |
| Files on disk | `APERTAR.md`, `tools/*`, `.gitignore` (`__pycache__/`) | new | repo |
| Files on disk outside repo | `/etc/modprobe.d/imx585-gate.conf` (gate test only, to be deleted afterwards) | documented, not created by driver | `tools/clearhdr-gate/README.md` |
| Env vars | none in the driver | Core side reads `APERTAR_IMX585_MIN_MODE_WIDTH` (in `Imx585Modes.hpp`, not this unit) | - |
| Socket commands, HTTP routes, state fields, events, UI elements | none in this unit | Core consumers are other units | - |

## 3. Original code modified (region, kind)

| Region (baseline `imx585.c`) | Kind | Note |
| --- | --- | --- |
| `HMAX_table_4lane_4K[]` (l.280) | rewritten, split into `_12bit` and `_10bit` | 440/396 -> 472 at 1039/1188 MHz (12-bit) |
| `struct imx585_mode` (l.340) | extended in place | removed `base_vmax`; added `binning`, `windowed`, `raw16`, `hmax_table`, `min_vmax_default` |
| `sync_mode_menu[]` | behaviour-visible label change | text only |
| `IMX585_WIN_CROP_*` macros + 18 per-crop `cci_reg_sequence` tables | removed and moved to code | replaced by `IMX585_WIN_CROP_REGS(vst,vwidth)` for the 4 full-field tables and `imx585_program_window()` for all crops; `IMX585_CROP_VMAX` 72 -> 70 |
| `supported_modes[]` (21 entries, hard indices 0, 10, 20) | rewritten | 96 entries, enum `imx585_mode_id`, `static_assert` pins order, 12-bit HDR range ends at HDR12 1440x1080 entry |
| 1.85:1 crops 3840x2076, 1920x1038 | behaviour changed (renamed) | now 3840x2072, 1920x1036 |
| `mono_codes[]`, `get_mode_table()` | extended in place + rewritten | magic index 20/10 replaced by enum; mono 12-bit HDR gated on `ccmp`; added Y10 and 10-bit routing |
| `imx585_format_is_10bit`, `imx585_apply_normal_bit_depth_regs` | removed | 10-bit regs now in the 10-bit tables |
| `imx585_update_test_pattern` | rewritten in place (adds error returns; same registers) | |
| `imx585_get_format_code` | extended in place | HDR 16/12 split, mono per-state, 16-bit code folds to 12-bit in SDR |
| `imx585_update_hmax` | rewritten | per-table HMAX, window-derived VMAX, HDR floor, 10-bit loop, `dev_dbg` per mode |
| `imx585_set_framing_limits` | extended in place | calls `imx585_update_mode_metadata` |
| `imx585_set_ctrl` WDR case | rewritten | uses new helpers; `V4L2_CID_IMX585_HMAX` indentation fix |
| `imx585_init_controls` | extended in place | 5 new controls, `imx585_activate_hdr_controls` |
| `enum_mbus_code`, `enum_frame_size`, `set_pad_format`, `get_selection`, `disable_streams` | extended in place | pad checks, HDR/CCMP gating, colourspace helper `imx585_reset_colorspace` |
| `imx585_enable_streams` | extended in place + behaviour changed | error propagation on sync regs and clamp; early return if streaming; `imx585_program_window()` after mode table; CCMP write gated, -EINVAL when 12-bit HDR requested without CCMP |
| `imx585_probe` | extended in place | `clearhdr_ccmp` read, table audit, gate warning |
| `imx585-overlay.dts` | extended in place | 1 param line |
| `README.md` | extended (clone URL, config.txt path, +120-line CineMate section) | |
| `.gitignore`, `dkms.*`, `setup.sh`, Makefile | not changed | confirmed by stat |

## 4. New abstractions

| Name | Purpose | Upstream (will127534 / Apertar baseline) equivalent |
| --- | --- | --- |
| `enum imx585_mode_id` + `static_assert`s | named indices and table-order pins for ranges | baseline: literal `supported_modes[20]`, `[10]`, `num_modes = 20` |
| `imx585_program_window()` | derive WINMODE regs from `mode->crop` | baseline: one `cci_reg_sequence` per crop |
| `imx585_check_mode_table()/_tables()` | probe-time audit | none |
| `imx585_find_mode`, `imx585_state_get_mode`, `imx585_default_mode`, `imx585_default_format_code`, `imx585_code_in_table`, `imx585_reset_colorspace`, `imx585_activate_hdr_controls`, `imx585_update_mode_metadata` | helpers | baseline repeated `get_mode_table` + `v4l2_find_nearest_size` inline |
| `hmax_table` pointer + two HMAX tables | per-mode link-rate table | one table |
| Module param `clearhdr_windowed_binning` | hardware test switch | none |
| `tools/` Python (4 files) | host replay of audit and alignment, DNG pedestal check | none in baseline; kernel driver repo had no tools dir |
| APERTAR.md | install and mode guide | none |

## 5. Removed, narrowed or hidden (vs `apertar`)

| What | Effect | Evidence |
| --- | --- | --- |
| 3840x2076 and 1920x1038 modes | Apertar 1.6.0 Core asks for both (`isImx585Raw12CropResolution`, `isImx585FullHdCropResolution`, `wt/core-upstream CameraController.cpp:366-392`); `v4l2_find_nearest_size` now returns 3840x2072 / 1920x1036, a different width/height than requested. APERTAR.md "Sizes that changed" says saved selections must be moved | confirmed (sizes absent in all 4 tables of `Imx585Modes.hpp`, run) |
| Every other 1.6.0 requested size | present in S12 and S10: 1920x1080, 3840x2160, 3840x2024..1504 (8), 1920x1012..752 (8); alias sizes 1928x1090 and 3856x2180 are Core-side only | confirmed (script over `Imx585Modes.hpp`) |
| Mono 12-bit Clear HDR 4K | was offered unconditionally; now needs `ccmp` overlay param, else absent and stream-on -EINVAL | confirmed; APERTAR.md says so |
| Mono 16-bit | still 4K only; unchanged | |
| Windowed 2x2 RAW16 crops | withdrawn (never in baseline) | fdd767a |
| 33 windowed 2x2 crops in 12-bit Clear HDR | hidden unless gate param on | `get_mode_table` |
| Per-mode `dev_info` lines | now `dev_dbg` | |
| Per-crop register tables | removed (see 3) | |
| 12-bit HMAX 440/396 at 2079/2377 Mbps/lane | raised to 472 (fps ceiling lower, frames clean per commit message) | diff 43-84 |
| WDR toggle forced SRGGB12/Y12 | no longer forced | diff ~3430 |
| Core-side hidden: Core hides modes narrower than 1280 px by default (`APERTAR_IMX585_MIN_MODE_WIDTH`) | 960 and 1024 wide driver modes (18 per SDR class) are advertised but not offered by Core | `Imx585Modes.hpp` comment (not this unit's code) |

## 6. What an Apertar user loses or gains (installing `cinemate-port` over `apertar`)

| Item | Gain/loss |
| --- | --- |
| Gain | RAW10 all modes (baseline RAW10 was the 12-bit table with a bit-depth fixup); binned 1080p Clear HDR (12 and 16-bit); 1x1 16-bit HDR crops; 12-bit HDR crops; 1920/2048-wide window crops; 2x2 960/1024-wide crops; mono Y10; geometry controls; per-mode crop reporting |
| Loss | 3840x2076 and 1920x1038 (renamed 2072 / 1036); mono 12-bit HDR default; slightly lower max fps at the two top link rates in 12-bit |
| Changed defaults | Colour 12-bit CCMP HDR default-on; HMAX floor in HDR; VMAX floor formula; mode names unchanged otherwise. HDR blend default unchanged (0); no control default changed |
| Core dependency | Core (port) reads the 4 mode lists in `Imx585Modes.hpp`; a driver older than this drops 14 + modes silently. Core upstream 1.6.0 stays working except the 2 renamed sizes |

## 7. Commit list grouped by feature (55 commits, oldest first, hash : feature)

| Feature | Commits |
| --- | --- |
| Lineage from Apertar-Studio `main` (not by Patrik) | 3680bf4 (format hardening, 2026-05-22), c0f5404 (HMAX table + HDR floor), 11178c8 (RAW10 4K), 70bdb26 (ccmp gate) |
| Cinemate 7-mode work | b6a6f5b c1350b0 3fa673c (default-on CCMP, binned HDR) ; e9d5759 0af0293 bd57617 (README) |
| Experimental crop modes, 2026-09-19 (22 commits, "experimental:" prefix and untagged) | e711fc9 f82d624 3414768 b050b7c 663449a b46cc47 9a44a4d d3253b5 5901dc8 234cccb a09ac49 4949b06 b703f46 85555d0 74ed4c6 475c3ea 8917c46 d9c132e 6532d6f ef2ef51 ddf438c d5efe87 7061c74 27c7cb4 |
| WP-585 series (2026-09-20 to 09-27), table and geometry cleanup | 5c7fb79 (-3) 951aeee (-1) 047c8a9 (-2) fff39ae (-4) ceb7367 (-5) 74b9b73 aa6c723 (-7) d47cbd8 8f508fb (-6) fdd767a (-8) 00059f6 (-9) 0a99f14 c3fafc2 90eef64 (merge of PR #2) 18c1eb2 (-10) |
| Apertar-side (Patrik, 2026-10-26 to 11-01) | 24172e6 (crop = real sensor window, T26) ; 6f25d7f (merge `cinemate-modes`) ; c18f162 (dev_dbg) ; 97649ba (controls read-only in config) ; 56de0cc cd548ef (docs) |

## 8. fork-log status (apertar-kb/fork-log.md:267-276)

| Row | Recorded status |
| --- | --- |
| `e5b74d3` 18 crop modes as shipped on 1.6.0 image | offer (to upstream) |
| `24172e6` | fork-only; DKMS-installed on Pi 2026-10-26 21:36, crops verified via `list_sensor_modes` |
| `cd548ef` (rolls up 6f25d7f, c18f162, 97649ba, 56de0cc, cd548ef) | fork-only; DKMS-installed on Pi 2026-11-01 18:55 (srcversion `29403D42A3919123B7FA091`); Draft PR #3 -> `apertar` |
| 3680bf4 c0f5404 11178c8 70bdb26 | listed as "Not taken" in fork-log, now taken via merge |

Tested (from commit text and docs, not re-verified): hardware pass 2026-08-31 (CM5, kernel 6.12.93, colour, link 891 MHz, rp1-overclock, seven original modes incl. 16-bit HDR) in README; 1x1 RAW16 crops 2880x2200 and 3840x1648 real, windowed 2x2 RAW16 pedestal (commit fdd767a, kernel not named); 33 windowed 2x2 crops in 12-bit HDR **not validated** (gate kit exists, gate not run per APERTAR.md); 1920/2048 families (18c1eb2) have host-side checks only (G1/G4 hardware gates named in `check_window_alignment.py` docstring as outstanding); no capture logs in the repo (APERTAR.md "Validation"). 16-bit HDR crops validated on kernel 6.12.93 only. Mono untested for the new crop families (mono offers no crops).

## 9. Board assumptions

| Assumption | Where |
| --- | --- |
| Pi 5 / CM5 with RP1 CFE; mode timing tuned to RP1 D-PHY limit 1500 Mbps/lane; link rates 891 and 1039.5 MHz run out of spec | README, APERTAR.md "Settings to leave alone" |
| Default link-frequency 720 MHz (1440 Mbps/lane) in overlay | `imx585-overlay.dts`, unchanged |
| Kernel >= 6.12 (`<linux/unaligned.h>`; in baseline too); 16-bit validated on 6.12.93 only | `imx585.c:17`, APERTAR.md |
| Mono Y16 needs a patched rp1-cfe `csi_dt` (`cfe_fmts.h`) re-applied after every kernel upgrade | README, APERTAR.md |
| "dual-imx585 rigs" and a "runtime dtoverlay try-bind/reprobe loop" (CineMate) are assumed by the comments: mode tables are process-wide and shared, audit deliberately avoids `imx585_update_hmax()` | `imx585_check_mode_table` and probe comments (confirmed text) |
| Note: `imx585_update_hmax()` still writes per-instance `min_hmax/min_vmax` into the shared tables at every mode-select (same as baseline) | confirmed; two sensors with different link/HDR state share state (probable issue, not judged) |
| 4-lane numbers, 2-lane doubles HMAX | `lane_scale`, unchanged |
| No fan, gpiochip, I2C bus number, RAM size or core count assumption in this unit | overlay uses `cam0_reg` / `cam1_reg`, unchanged except `ccmp` line |
| README/APERTAR install path `~/drivers/imx585-v4l2-driver`, Raspberry Pi OS Bookworm `/boot/firmware/config.txt`, DKMS | APERTAR.md |
| APERTAR.md and tools refer to CineMate settings (`settings.jsonc` key `image_capture.hdr.imx585_clear_hdr_12bit`), `cinepi-raw --list-cameras` | `tools/clearhdr-gate/README.md` |

## 10. Style and naming notes (facts only, for stage 2)

| Fact | Where |
| --- | --- |
| WP-585-n, D1, G1-G4, DEC-2 and INVESTIGATION.md / RESULTS.md / ASPECT-RATIOS.md (not in repo) appear in code comments | enum comments, `imx585_check_mode_table`, tools docstrings |
| Mode-table comment block above the enum is ~120 lines of history | `port.c:~760-860` |
| Tools and one README section name "CineMate" branch and `cinemate-7modes`; APERTAR.md says README matrix is not this branch's list | APERTAR.md "Modes" |
| Branch name in installer text `cinemate-port` vs Apertar branch `apertar` | APERTAR.md "Which branch" |
| One whitespace-only trailing-space line kept in `V4L2_CID_IMX585_HMAX` case (`break; ` ) | diff ~3470 |
