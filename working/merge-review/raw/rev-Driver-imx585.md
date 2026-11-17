# Review: Driver-imx585 (stage 2)

Refs: port = `imx585-v4l2-driver` `cinemate-port` `cd548ef`; baseline = `origin/apertar` `e5b74d3` (will127534 `1644466` + 18 crops of the 1.6.0 image). Upstream Core = `wt/core-upstream` `upstream-1.6.0`. libcamera = `tiramisioux/libcamera` `apertar`.
Files: `/tmp/claude-0/base.c` = `git show origin/apertar:imx585.c`; `/tmp/claude-0/port.c` = `git show cinemate-port:imx585.c`; diff in `/home/user/build/review/imx585.diff`.
Yardstick: `apertar-conventions.md` does not exist yet; `conv-core-*.md` cover Core only. For this driver the "original" is two things: the 1.6.0 image driver (`apertar`) and the driver author's own line (Will Whang, Apertar-Studio driver `main` = `70bdb26`, per `architecture/drivers.md:10`).

## 1. Answers to the hint questions

| Question | Answer | Evidence |
| --- | --- | --- |
| Is every mode Apertar 1.6.0 requests still there? | 18 of 20 exact. 3840x2076 and 1920x1038 are gone (now 3840x2072 / 1920x1036) | requested: `core-upstream src/camera/CameraController.cpp:366-396@upstream-1.6.0`; port enum `port.c:867,918@cinemate-port`; baseline `base.c:817,1007@apertar` |
| What happens to unmodified 1.6.0 Core at those two sizes | 1920x1038: configure fails (confirmed in code, not on hw). 3840x2076: falls back to auto and records 3840x2072 (probable) | see F1 |
| Which controls changed defaults | None of the existing controls. Sync-mode menu labels changed (text only). Colour 12-bit CCMP Clear HDR is now offered without `ccmp` (b6a6f5b) | diff 85-94; `imx585_probe` |
| What a user gains | RAW10 in every mode with its own HMAX table, binned Clear HDR (12/16), 1x1 16-bit HDR crops, 1920/2048 window crops, crop reported in sensor coordinates, Y10 mono | inventory F1-F12 |
| What a user loses | the two 1.85:1 sizes; mono 12-bit HDR without `ccmp` (Will Whang's 70bdb26, not the port); max fps at the two out-of-spec link rates (Will Whang's c0f5404) | |

## 2. Findings

| Id | Sev | Cat | Title |
| --- | --- | --- | --- |
| F1 | blocker | removed-upstream-behaviour | 1.85:1 sizes renamed; unmodified 1.6.0 Core cannot configure 1920x1038 |
| F2 | major | slop | Mode table carries work-package history, "Experimental" labels and stale comments |
| F3 | minor | bug | 1440x1080 has a different field of view in 12-bit (1x1 window) and 10-bit (2x2) |
| F4 | minor | new-ground | 44 entries at 960/1024 wide that Apertar Core hides by default |
| F5 | minor | new-ground | `clearhdr_windowed_binning` module param and the CineMate-based gate kit |
| F6 | minor | new-ground | Probe-time table audit: known warning every boot, predicate copied three times |
| F7 | minor | slop | Redundant per-mode `hmax_table`, unused `min_vmax_default`, two copy-pasted loops |
| F8 | minor | duplication | Core's `Imx585Modes.hpp` hand-copies the four driver tables |
| F9 | minor | slop | README CineMate section, fork URL and branch names in docs |
| F10 | minor | removed-upstream-behaviour | Colour 12-bit CCMP default-on overrides the driver author's opt-in gate |
| F11 | minor | bug | 12-bit Clear HDR offered on 1x1 crops with no hardware validation, 2x2 gated |
| F12 | minor | slop | 55 commits, 22 "experimental:", WP numbers in subjects |
| F13 | nit | new-ground | Read-only geometry controls (+10..+14) have no Apertar consumer |

### F1 blocker, removed-upstream-behaviour: 1.85:1 sizes renamed

- Port: `IMX585_MODE_CROP_3840X2072` crop top 44 (`port.c:1121-1127`), `IMX585_MODE_CROP_BIN_1920X1036` (`port.c:1408-1414`), same in 10-bit (`port.c:2168, 2423`). Confirmed.
- Baseline: `.height = 1038` `IMX585_WIN_CROP_REGS(54, 2076)` (`base.c:667-672, 817`), `.height = 2076` (`base.c:586-591, 1007`). Confirmed.
- Why renamed: VST 54 breaks the multiple-of-4 rule; `imx585_program_window()` rejects `(vst & 3)` (`port.c:2962-2966`). Port Core says so (`Apertar-Core src/camera/CameraController.cpp:441-453@cinemate-port`).
- Original Apertar asks for both: `isImx585FullHdCropResolution` 1920x1038 (`core-upstream CameraController.cpp:366-377`), `isImx585Raw12CropResolution` 3840x2076 (`:385-396`); WebUI `WebControlPage.cpp:5120, 5254, 5268@upstream-1.6.0`; touch UI `ApertarControlBridge.cpp:1842, 1912@upstream-1.6.0`.
- Failure path, 1.6.0 Core + port driver, colour:
  - Core tries explicit `sensorConfig->outputSize = rawSize` first (`core-upstream CameraController.cpp:6010, 6115-6118`).
  - libcamera returns `Invalid` when the best format size differs from `sensorConfig->outputSize` (`libcamera src/libcamera/pipeline/rpi/common/pipeline_base.cpp:226-238@apertar`). Confirmed in code.
  - Auto fallback is allowed only for `isImx585Raw12CropResolution` (`core-upstream CameraController.cpp:5993-5996`). 3840x2076 falls back; 1920x1038 has no fallback and only one candidate (`:2289-2303`, IMX585 adds none). So 1920x1038 fails to configure. Confirmed in code; not run on hardware.
  - 3840x2076 via auto: `findBestFormat` scores 3840x2072 best (height off by 4, AR penalty small; `pipeline_base.cpp:973-1015`). Records 3840x2072. Probable; settle with `ApertarCore` log line "trying ... sensorConfig=auto" on a Pi.
- Port Core migrates (`migratedImx585CropResolution`, `CameraController.cpp:446-453@cinemate-port`), so the driver works only with the port Core. Driver and Core must land together, and an Apertar 1.6.0 image that only updates the driver breaks 2K 1.85:1.
- Rework (preferred, S): keep the old advertised sizes. Window 2076 sensor rows at crop top 40 (VST 52, 52 & 3 = 0, 2076 & 3 = 0): two rows off centre, passes `imx585_program_window()`. Entries `IMX585_MODE_CROP_3840X2076` and `IMX585_MODE_CROP_BIN_1920X1038` in both tables. This also removes the 3840x2072 cross-family duplicate warning (F6). Core `migratedImx585CropResolution` and the WebUI alias map (`WebControlPage.cpp:9078-9085@cinemate-port`) then go away. Alternative: keep 2072/1036 and state in the merge notes that driver and Core release together.
- Deliberate: yes. APERTAR.md "Sizes that changed"; Core comment above.

### F2 major, slop: mode table history and labels

- 54 `WP-585` references and 64 "Experimental" comments in `imx585.c` (grep count on `port.c`). The table entries Apertar ships are labelled "Experimental centered ... crop" (`port.c:1086, 1121`).
- Refers to files that are not in the repo: `INVESTIGATION.md`, `RESULTS.md`, `ASPECT-RATIOS.md`, `WORK-PACKAGES.md`, IDs D1, DEC-1, DEC-2, G1-G4 (`port.c:770`, enum comments `:860-1000`, tools docstrings).
- About 120 lines of history above the enum (`port.c:767-858`), more inside `get_mode_table` (`port.c:3063-3090`).
- Stale or contradictory comments: `imx585_program_window` cites "1920x1120 / 1280x760" (`port.c:2950`; no 1280x760 mode exists); 10-bit 1440x1080 entry says "Everything below 1440 in this table moved to the 1x1 window" (`port.c:2120-2124`), yet 22 2x2 entries at 960/1024 follow; mono Y10 branch says "4K 10-bit" (`port.c:3030`) but hands out all 62.
- Upstream driver style: short register comments, one-line per-mode comments ("1.85:1 2x2 binned, full-width RAW12 crop", `base.c:815`; `get_mode_table` comments `base.c:1384-1387`).
- Rework (M): replace the history block with a 20-line invariant block (table order; the three ranges `get_mode_table` hands out; RAW16 OB rule; crop in sensor coordinates). One comment per entry: ratio and binning. Remove ticket ids and the names of absent files. Move the hardware findings (windowed 2x2 RAW16 = pedestal; mono binned HDR = pedestal) into APERTAR.md "Validation".

### F3 minor, bug: 1440x1080 framing depends on bit depth

- 12-bit: `.binning = 1, .windowed = true`, crop 1440x1080 at (1200, 540) (`port.c:1369-1374`): a 2.67x tele window.
- 10-bit: `.binning = 2`, crop 2880x2160 at (480, 0) (`port.c:2125-2130`): the 4:3 full-height view.
- Failing input: select 1440x1080, switch 12-bit -> 10-bit. Same size, field of view changes by 2x. Core port mirrors it (`Imx585Modes.hpp`: `kS12Modes` `{1440,1080,false}`, `kS10Modes` `{1440,1080,true}`).
- Deliberate: yes (comments WP-585-5 on both entries).
- Rework (S): use the same geometry in both tables (12-bit 2x2 windowed 1440x1080 in SDR only, outside the HDR range, or a 10-bit 1x1 entry), or document in APERTAR.md.

### F4 minor, new-ground: 960/1024-wide families

- 22 entries per SDR table (11 at 960, 11 at 1024) (`port.c` enum `IMX585_MODE_CROP_BIN_960X540..1024X400`), commit 18c1eb2, host checks only.
- Apertar Core hides widths below 1280 unless `APERTAR_IMX585_MIN_MODE_WIDTH` says otherwise (`Apertar-Core src/camera/Imx585Modes.hpp:100-114@cinemate-port`). So the driver advertises 44 modes Apertar does not show, and Core carries an env knob for it.
- Verdict: simplify. Drop the 960/1024 families from the Apertar branch (and the Core env knob with them), or show them in Core and drop the knob. Not both.

### F5 minor, new-ground: hardware-gate switch and kit

- `module_param(clearhdr_windowed_binning, bool, 0444)` (`port.c:1039-1042`), probe warning, `tools/clearhdr-gate/{README.md,pedestal_check.py}`.
- The kit needs CineMate (`settings.jsonc` key `image_capture.hdr.imx585_clear_hdr_12bit`, `cinepi-raw`), README "What you need". The gate has not been run (APERTAR.md "Settings to leave alone").
- No upstream precedent: baseline has no module params and no tools dir.
- Verdict: simplify. Keep the range end at `IMX585_MODE_CROP_1440X1080_HDR12` and its static_assert; remove the param, its probe warning and `tools/clearhdr-gate/` from the Apertar branch. If the gate is ever run, it is a one-line range change.

### F6 minor, new-ground: probe-time table audit

- `imx585_check_mode_table()` (`port.c:4478-4577`) runs at every probe. Its duplicate-size check is table-wide, so 3840x2072 at [5] and [67] (12-bit vs RAW16, different `get_mode_table` ranges) prints one `dev_warn` on every boot. Confirmed by `tools/replay_mode_table_audit.py` (inventory, run).
- The window predicate exists three times: `imx585_program_window` (`port.c:2962-2966`), the audit (`port.c:4498-4503`), and `tools/check_window_alignment.py` plus `replay_mode_table_audit.py` (whose docstring says the copies "must stay identical").
- Verdict: simplify. One `static bool imx585_window_ok(const struct imx585_mode *m)` used by `program_window`; either drop the probe audit (the table is static data; the host tool covers it) or scope the duplicate check per range. Keep one host tool, not two.

### F7 minor, slop: over-built mode fields

- `hmax_table`: all 96 `supported_modes[]` entries point at `HMAX_table_4lane_4K_12bit`, all 62 10-bit entries at `_10bit` (awk count on `port.c`). The pointer is a per-table constant written 158 times.
- `min_vmax_default`: every windowed entry is `0`; the override path in `imx585_update_hmax` (`port.c:3296-3298`) and the audit check never fire. Non-windowed entries set `IMX585_VMAX_DEFAULT`, which the code never reads.
- Literal `.min_hmax`/`.min_vmax` are overwritten at runtime and some are wrong (10-bit 1440x1080 `.min_vmax = 1150`, derived 2230, `port.c:2128`). Baseline also initialised them (`base.c:800` "overwritten at runtime"), so the initialisers alone follow upstream; the wrong values do not.
- `imx585_update_hmax` has two copy-pasted loops (`port.c:3279-3346`).
- Rework (S): `imx585_update_table_limits(imx585, table, n, hmax_table)` called twice; drop `hmax_table` and `min_vmax_default` from `struct imx585_mode`; drop the runtime-computed initialisers or set them to 0.

### F8 minor, duplication: Core hand-copies the driver tables

- `Apertar-Core src/camera/Imx585Modes.hpp:39-98@cinemate-port`: four arrays (62/62/29/34 rows) with binning flags, "as the driver lists it".
- Upstream Core also hard-codes the IMX585 sizes (`core-upstream CameraController.cpp:360-396`), so hard-coding is the upstream pattern; the scale is new. Fork main already probes sensor modes at start (`core-main` `f60e301`).
- Any driver table change needs a matching Core edit; nothing checks that they agree.
- Rework (M, Core unit): keep `Imx585Modes.hpp` for the policy (H16 OB rows, shadowing) and check the arrays against the probed libcamera sensor modes at start (log a mismatch), or add a host test that parses `imx585.c` like `tools/replay_mode_table_audit.py` does. Report to the Core review.

### F9 minor, slop: docs

- README clone URL changed to `-b cinemate-port https://github.com/Tiramisioux/...` (README diff hunk 1). On a merge into the Apertar driver this points to the fork.
- README gains a 120-line "CineMate branch (`cinemate-7modes`)" section with CineMate CLI, settings, Redis layers; APERTAR.md has to say it "is not the mode list of this branch".
- APERTAR.md "Which branch: Use `cinemate-port`".
- Keep: the blend-menu table, the HMAX floor explanation and the "set the blend explicitly" advice are driver facts.
- Rework (S): drop the CineMate layer table and the seven-mode matrix from README; keep the blend table and link-rate notes; branch name and URL to the merge target.

### F10 minor, removed-upstream-behaviour: colour CCMP default-on

- Driver author's 70bdb26 makes 12-bit CCMP Clear HDR opt-in for both variants via `ccmp`. b6a6f5b makes it default-on for colour: `clearhdr_ccmp = !mono || of_property_read_bool(...)`. `ccmp` is now a no-op on colour.
- Against the 1.6.0 image driver nothing changes for colour (baseline offered 12-bit HDR unconditionally, `base.c:1392-1394`). Mono 12-bit HDR now needs `ccmp`: that narrowing is Will Whang's 70bdb26, not the port.
- Deliberate: yes (b6a6f5b message).
- Rework: none in code; state in the merge notes that this departs from the driver author's gate. Unmodified 1.6.0 Core does not use Clear HDR (no WDR or HDR in `core-upstream CameraController.cpp`, grep), so no runtime effect on it.

### F11 minor, bug (probable): validation asymmetry in 12-bit Clear HDR

- 12-bit HDR range covers all 27 1x1 windowed crops incl. the 1920/2048 windows (`get_mode_table`, `port.c:3091-3096`).
- Hardware evidence recorded: 16-bit 1x1 crops (fdd767a), 7 full-field modes (README). None for 12-bit HDR windowed crops; 18c1eb2 is host-only (`check_window_alignment.py` docstring: G1/G4 outstanding).
- The 2x2 windowed crops are held back for lack of the same evidence. Unconfirmed; settle with one 12-bit HDR take at a 1920-window crop on the Pi.

### F12 minor, slop: commit history

- 55 commits; 22 on 2026-09-19 alone, many "experimental:" or fix-of-previous ("fix mode table after low-res removal", "Restore IMX585 12-bit mode table ordering"); `WP-585-n` in subjects; one merge of a PR. Keep the 4 Will Whang commits as they are; squash Patrik's into feature commits (mode families, window programming, RAW10 families, crop reporting, docs).

### F13 nit, new-ground: geometry controls

- `V4L2_CID_IMX585_BINNING`, `CROP_LEFT..HEIGHT` read-only (`diff` 42-50). Consumer: `cinepi-raw cinepi/cinepi_raw.cpp:177-217`. Apertar Core reads only base+0/+1/+5 (`CameraController.cpp:7034-7037@cinemate-port`). Same data via `V4L2_SEL_TGT_CROP`, which the port now reports correctly.
- Verdict: keep (read-only, cheap, branch is shared with Cinemate); say in APERTAR.md who reads them.

## 3. Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `enum imx585_mode_id` + `static_assert`s | keep | Replaces magic `supported_modes[20]`, `[10]`, `num_modes = 20` (`base.c:1389-1434`); a reorder fails the build |
| `imx585_program_window()` | keep | Replaces 18 hand-written register tables (`base.c:586-700`); checks the datasheet alignment; share its predicate (F6) |
| `imx585_check_mode_table()/_tables()` | simplify | F6 |
| helpers `find_mode`, `state_get_mode`, `default_mode`, `default_format_code`, `code_in_table`, `reset_colorspace`, `activate_hdr_controls`, `update_mode_metadata` | keep | Remove repeated inline `get_mode_table` + `v4l2_find_nearest_size`; `activate_hdr_controls` comes from the driver author's 70bdb26 |
| two HMAX tables | keep | Driver author's c0f5404/11178c8 |
| per-mode `hmax_table` pointer, `min_vmax_default` | simplify | F7 |
| module param `clearhdr_windowed_binning` | simplify (remove) | F5 |
| `tools/` Python | simplify | one host audit tool; gate kit out (F5, F6) |
| APERTAR.md | keep | Install, config.txt, families, renamed sizes; fix branch names (F9) |
| read-only geometry controls | keep | F13 |

## 4. Conforms

- Four commits are the driver author's own (Will Whang: 3680bf4, c0f5404, 11178c8, 70bdb26; `git log --format=%an`). HMAX tables, the RAW10 table, the Clear HDR HMAX floor, the `ccmp` gate and format hardening come from upstream's driver line.
- `imx585_program_window()` and the enable path use `cci_write` with error returns, the driver's own register style (`port.c:2968-2988`, `4067-4112`).
- Crop in native sensor coordinates (`port.c:1044-1062`, `imx585_get_selection`) is what V4L2 and libcamera expect; baseline reported the buffer (`base.c:822-827`).
- Overlay param in the existing syntax (`ccmp = <&cam_node>,"sony,clearhdr-ccmp?";` next to `mono = ...`, `imx585-overlay.dts:137-138`).
- No new Kconfig, sysfs, debugfs; `Makefile`, `dkms.*`, `setup.sh` unchanged (`--stat`).
- No existing control default changed; HDR blend stays menu 0 (`common_clearHDR_mode` `0x36e2 = 0x00`), README says so.
- 18 of the 20 sizes 1.6.0 requests are exact in both SDR tables, incl. 10-bit, which the 1.6.0 driver only had through a 12-bit table plus a register fixup.
- APERTAR.md records the renamed sizes and the settings to leave alone.

## 5. Not judged / pre-existing

- `imx585_update_hmax()` writes per-instance limits into the static tables (`port.c:3330-3331`); baseline did the same (`base.c:1497-1505`). Two sensors with different link or HDR state share them. Pre-existing; for the dual-sensor work.
- Pi-compat: timing tuned on Pi 5 / CM5 RP1; Y16 mono needs the rp1-cfe patch; same assumptions in baseline.

## Skeptic

Checked at `imx585-v4l2-driver` `cinemate-port` `cd548ef` (port.c), `origin/apertar` `e5b74d3` (base.c), Will Whang `70bdb26` (ww.c), `wt/core-upstream` `upstream-1.6.0`, `Apertar-Core` `cinemate-port`.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | corrected | Confirmed: base writes VST 54 / 2076 (`base.c:591,672`), port has 2072 at crop top 44, `vst = 12 + crop.top` and `(vst & 3)` reject (`port.c:2962-2966`). 1.6.0 Core: auto fallback for `monochromeSensor_` too (`core-upstream CameraController.cpp:5993`), so the 1920x1038 configure failure is colour-only; mono falls back to auto. Rework checked: crop top 40 -> VST 52, height 2076, both `& 3 == 0`. Deliberate also via Core `900d282` (fork-log). |
| F2 | stands | 54 `WP-585`, 65 lines "experimental" (grep). Stale comments confirmed: `port.c:2950` "1280x760", `:2120-2124` "Everything below 1440 moved", `:3026` "4K 10-bit" with `ARRAY_SIZE(supported_10bit_modes)`. |
| F3 | stands | 12-bit `[28]` 1x1 crop {1200,540,1440,1080} (`port.c:1369-1374`); 10-bit `[2]` 2x2 crop {480,0,2880,2160} (`port.c:2125-2130`). |
| F4 | corrected | Count wrong: per table 11 at 960 and 10 at 1024 (21), so 42 at 960/1024; with the binned 1080x1080 (1:1) 44 entries are under 1280 and hidden. Core knob confirmed (`Imx585Modes.hpp:100-114`). |
| F5 | stands | Param `port.c:1025-1042`, range switch `:3090`, probe warning `:4678-4680`; gate README needs CineMate `settings.jsonc` and `cinepi-raw` (`tools/clearhdr-gate/README.md:25,48`). "Never run" = no run recorded in repo or fork-log. |
| F6 | stands | Only duplicate in either table is 3840x2072 at `supported_modes[5]` and `[67]` (script over port.c). Predicate copied in `imx585_check_mode_table` (`port.c:4493-4506`); `check_window_alignment.py:9` "must stay identical". |
| F7 | corrected | `hmax_table` per mode and the two loops are the driver author's design: `70bdb26` has `const u16 *hmax_table` (`ww.c:371`) and two loops in `imx585_update_hmax` (`ww.c:1210-1248`), the 10-bit loop with its own 1039 MHz rule. Not port slop: dropped from the finding. What remains: `min_vmax_default` override that no windowed entry sets (6 non-windowed entries set it, where it is ignored) plus its audit check, and 2 wrong `min_vmax` literals (one per table, the 1440x1080 2x2 10-bit entry among them). Severity nit. |
| F8 | corrected | Core probes every table row at start (`CameraController.cpp:7158-7189@cinemate-port`) and drops rows the driver refuses with a silent `continue`. So drift is caught for rows the driver lacks (silently), not for rows only the driver has. Rework narrowed to logging the dropped rows. |
| F9 | stands | `README.md:37` clone `-b cinemate-port` Tiramisioux, base and `70bdb26` clone will127534; `README.md:148` "CineMate branch (`cinemate-7modes`)" with a seven-mode matrix that no longer describes the tables; `APERTAR.md:9-15`. |
| F10 | stands | `port.c:4641` `clearhdr_ccmp = !mono || ...`; `b6a6f5b` (Patrik) vs `70bdb26` (Will Whang) messages read. |
| F11 | stands | HDR-12 range = `[0..28]`, i.e. 2 full-field + 27 1x1 crops (`port.c:3086-3094`); base offered 4K only (`base.c:1429-1432`); APERTAR.md "Validation" covers 16-bit only. |
| F12 | corrected | 55 commits incl. 4 Will Whang and 2 merges. 9 `experimental:` subjects plus about 7 fix-ups of earlier commits (`7061c74`, `27c7cb4`, `85555d0`, `475c3ea`, `aa6c723`, `a09ac49`, `c3fafc2`), not 22. WP ids in 13 subjects. |
| F13 | stands | `port.c:44-50`; Core reads only base +0/+1/+5 (`CameraController.cpp:7034@cinemate-port`). |

## Final findings

### Driver-imx585-F1 [removed-upstream-behaviour, blocker] 1.85:1 sizes renamed (3840x2076 -> 3840x2072, 1920x1038 -> 1920x1036); unmodified 1.6.0 Core cannot configure 1920x1038 on a colour sensor
- where: `imx585.c:867, 918, 1121-1127, 1408-1414, 2168-2174, 2423-2429@cinemate-port`; `imx585.c:2962-2966@cinemate-port` (alignment check); `APERTAR.md:145-157@cinemate-port`
- port way: Centred 1.85:1 windows of 2072 sensor rows at crop top 44 (VST 56), advertised 3840x2072 and 1920x1036, in the 12-bit and 10-bit tables. Port Core migrates the old sizes (`migratedImx585CropResolution`, `Apertar-Core CameraController.cpp:441-453@cinemate-port`).
- Apertar way: Baseline advertises 3840x2076 and 1920x1038 with `IMX585_WIN_CROP_REGS(54, 2076)` (`base imx585.c:586-591, 667-672, 817@apertar`). Core 1.6.0 requests both (`core-upstream CameraController.cpp:366-396@upstream-1.6.0`), WebUI (`WebControlPage.cpp:5120,5254,5268`) and touch UI (`ApertarControlBridge.cpp:1842,1912`) offer them. Core tries an explicit `sensorConfig` first (`:6010, :6115-6118`); auto fallback only for mono, IMX294/577 and `isImx585Raw12CropResolution` (`:5993-5996`). libcamera returns Invalid on a sensor size mismatch (`pipeline_base.cpp:226-238@libcamera apertar`).
- why it matters: A 1.6.0 image that updates only the driver loses 2K 1.85:1 on the colour sensor (configure fails for 1920x1038, no fallback). 4K 1.85:1 probably records 3840x2072 via auto (unconfirmed; settle with the Core "sensorConfig=auto" log line on a Pi). Mono goes auto for both. Driver and Core must merge in lockstep; both 1.6.0 UIs list sizes the driver no longer has.
- rework: Keep the old advertised sizes. `IMX585_MODE_CROP_3840X2076` and `IMX585_MODE_CROP_BIN_1920X1038` in `supported_modes[]` and `supported_10bit_modes[]`, crop {0, 40, 3840, 2076} (VST 52, both `& 3 == 0`, two rows off centre, passes `imx585_program_window()`). Then delete Core's `migratedImx585CropResolution` / `migrateImx585LadderRungs` and the WebUI alias entries (`WebControlPage.cpp:9078-9085@cinemate-port`). Removes the 3840x2072 duplicate warning (F6) as a side effect. Fallback: keep 2072/1036 and state in the merge notes that driver and Core release together.
- effort: S
- deliberate: yes. `APERTAR.md` "Sizes that changed"; Core comment `CameraController.cpp:441-445@cinemate-port` (VST-54 alignment); Core commit `900d282` (fork-log row `d44b177`).

### Driver-imx585-F2 [slop, major] Mode table carries work-package history, "Experimental" labels on shipping modes, references to absent files and stale comments
- where: `imx585.c:767-858, 860-1000, 1086, 1121, 2120-2124, 2950, 3026, 3063-3090@cinemate-port`
- port way: 54 `WP-585` references and 65 "experimental" comment lines. About 90 lines of history above the enum citing `INVESTIGATION.md`, `RESULTS.md`, `ASPECT-RATIOS.md`, `WORK-PACKAGES.md`, D1, DEC-1, DEC-2, G1-G4, none in the repo. Stale: `:2950` cites "1280x760" (no such mode); `:2120-2124` says everything below 1440 moved to 1x1, yet 2x2 960/1024 entries follow; mono Y10 `:3026` says "4K 10-bit" but returns all 62.
- Apertar way: Baseline uses one-line per-mode comments ("1.85:1 2x2 binned, full-width RAW12 crop", `base imx585.c:815@apertar`) and short routing comments in `get_mode_table` (`base imx585.c:1384-1387@apertar`). The driver author's longer comments (`70bdb26`, e.g. the Clear HDR HMAX floor) explain hardware, not process.
- why it matters: The original developer cannot follow ticket ids or absent documents; shipping modes labelled "Experimental" read as unfinished; stale comments mislead.
- rework: Replace the history with a ~20-line invariant block (table order, the three ranges `get_mode_table` hands out, RAW16 OB-row rule, crop in sensor coordinates). One comment line per entry: ratio and binning. Strip WP/D/DEC/G ids and absent file names. Fix the three stale comments. Move the hardware findings (windowed 2x2 RAW16 = pedestal, mono binned HDR = pedestal) to `APERTAR.md` "Validation".
- effort: M
- deliberate: no. The comments narrate the work-package process; nothing records a decision to keep them.

### Driver-imx585-F3 [bug, minor] 1440x1080 has a different field of view in 12-bit (1x1 1440 window) and 10-bit (2x2 of a 2880 window)
- where: `imx585.c:1369-1374@cinemate-port` (`supported_modes[28]`); `imx585.c:2125-2130@cinemate-port` (`supported_10bit_modes[2]`); `Apertar-Core src/camera/Imx585Modes.hpp:39-75@cinemate-port`
- port way: 12-bit: 1x1 window crop {1200, 540, 1440, 1080}. 10-bit: 2x2 over {480, 0, 2880, 2160}.
- Apertar way: no precedent (baseline had no 1440x1080 and no 10-bit table).
- why it matters: Select 1440x1080 and switch 12-bit -> 10-bit: same size, framing changes 2x (tele centre crop vs 4:3 full height).
- rework: Same geometry in both tables: a 1x1 1440 window in the 10-bit table, or a 2x2 windowed 1440x1080 in the 12-bit table outside the HDR range. Or name the difference in `APERTAR.md`.
- effort: S
- deliberate: yes. WP-585-5 comments on both entries explain why each table kept its own variant.

### Driver-imx585-F4 [new-ground, minor] 42 entries at 960/1024 wide (44 under 1280) are advertised but hidden by Apertar Core by default
- where: `imx585.c` enum `IMX585_MODE_CROP_BIN_960X540 .. IMX585_MODE_CROP_BIN_1024X400` (and the 10-bit equivalents)`@cinemate-port`; `Apertar-Core src/camera/Imx585Modes.hpp:15, 100-114@cinemate-port`
- port way: Each SDR table has 11 crops at 960 and 10 at 1024 (2x2 of the 1920/2048 windows, commit `18c1eb2`, host-checked only), plus 1080x1080 binned, all under 1280. Core hides widths below 1280 unless `APERTAR_IMX585_MIN_MODE_WIDTH` is set.
- Apertar way: no precedent.
- why it matters: The driver carries data and validation debt for modes Apertar does not offer, and Core gains an env-var knob to hide them.
- rework: Pick one. Drop the 960/1024 families from the Apertar branch and remove the Core env knob, or offer them in Core and remove the knob.
- effort: S
- deliberate: yes. Commit `18c1eb2` (WP-585-10); `Imx585Modes.hpp:15-16` "hidden as in cinemate".

### Driver-imx585-F5 [new-ground, minor] The `clearhdr_windowed_binning` module parameter and the `tools/clearhdr-gate` kit depend on CineMate and have no recorded run
- where: `imx585.c:1025-1042, 3083-3094, 4678-4680@cinemate-port`; `tools/clearhdr-gate/README.md:25-52@cinemate-port`; `tools/clearhdr-gate/pedestal_check.py@cinemate-port`; `APERTAR.md:88-93@cinemate-port`
- port way: A bool module param (0444) widens the 12-bit HDR range to the windowed 2x2 crops for a hardware test. The kit requires CineMate `settings.jsonc` and `cinepi-raw`.
- Apertar way: no precedent (baseline has no module params and no `tools/`).
- why it matters: A test switch and a CineMate procedure in the Apertar driver; `APERTAR.md` has to tell users not to set it.
- rework: Keep the range end at `IMX585_MODE_CROP_1440X1080_HDR12` and its static_assert. Remove the param, its probe warning and `tools/clearhdr-gate/` from the Apertar branch. A later validated change is a one-line range edit.
- effort: S
- deliberate: yes. Comment above the param (`imx585.c:1025-1037`) gives the reason for a module param over DT.

### Driver-imx585-F6 [new-ground, minor] The probe-time table audit prints a known warning on every boot, and the window predicate exists four times
- where: `imx585.c:4478-4586@cinemate-port`; `imx585.c:2962-2966@cinemate-port`; `tools/check_window_alignment.py:9@cinemate-port`; `tools/replay_mode_table_audit.py@cinemate-port`
- port way: `imx585_check_mode_table()` runs at every probe. Its duplicate-size check is table-wide, so 3840x2072 at `supported_modes[5]` (SDR 1.85:1) and `[67]` (RAW16 1.89:1) warns every boot although the two never share a `get_mode_table` range. The alignment predicate is copied in `imx585_program_window()`, the audit and two Python tools ("must stay identical").
- Apertar way: no precedent (baseline has no audit).
- why it matters: A permanent harmless warning in dmesg, and four hand-synced copies of one predicate.
- rework: `static bool imx585_window_ok(const struct imx585_mode *)` used by `imx585_program_window()`. Drop the probe audit (tables are static; the host tool covers them) or check duplicates per `get_mode_table` range. Merge the two Python tools into one.
- effort: S
- deliberate: yes. Commits `74b9b73`, `aa6c723`; `8f508fb` accepts the collision.

### Driver-imx585-F7 [slop, nit] Unused `min_vmax_default` override and two wrong `min_vmax` literals
- where: `imx585.c:384-387@cinemate-port` (field); `imx585.c:3289-3299, 3312-3316@cinemate-port` (`imx585_update_hmax`); audit `imx585.c:4509-4530@cinemate-port`; `imx585.c:2128@cinemate-port`
- port way: `min_vmax_default` is 0 on every windowed entry (the only place it is read) and set to `IMX585_VMAX_DEFAULT` on 6 non-windowed entries where it is ignored; the audit checks the unused override. Runtime-overwritten `min_vmax` literals are consistent except one per table (10-bit 1440x1080 says 1150, derived 2230).
- Apertar way: The driver author's `imx585_mode` has `min_hmax`/`min_vmax` "computed at runtime" and no override (`70bdb26 imx585.c:371-373, 1210-1248`). The per-mode `hmax_table` pointer and the separate 10-bit loop are his design and stay.
- why it matters: An override hook nobody uses plus misleading numbers; small, but more to read.
- rework: Delete `min_vmax_default` from `struct imx585_mode`, its 158 initialisers, the ternaries in `imx585_update_hmax` and the audit's override check. Fix or zero the two wrong literals.
- effort: S
- deliberate: no. Commit `5901dc8` "experimental: add per-mode VMAX default field", no user.

### Driver-imx585-F8 [duplication, minor] Core's `Imx585Modes.hpp` hand-copies the four driver tables; drift is dropped silently
- where: `Apertar-Core src/camera/Imx585Modes.hpp:39-98@cinemate-port`; probe `Apertar-Core src/camera/CameraController.cpp:7158-7189@cinemate-port`
- port way: Four constexpr arrays "as the driver lists it". At start Core configures each row and skips rows the driver refuses with a silent `continue`. Rows only the driver has are never offered.
- Apertar way: Upstream Core also hard-codes IMX585 sizes (`core-upstream CameraController.cpp:360-396@upstream-1.6.0`), on a smaller scale. Fork main probes sensor modes at start (`core-main f60e301`).
- why it matters: Every driver table edit needs a matching Core edit; a mismatch disappears without a log line.
- rework: (Core unit) Keep `Imx585Modes.hpp` for policy (H16 OB rows, hiding). Log each table row the probe drops, and each driver size (`formats.sizes()`) no table row covers. Optional host test that parses `imx585.c` like `tools/replay_mode_table_audit.py`.
- effort: S
- deliberate: yes. `Imx585Modes.hpp:3` names the driver branch it mirrors.

### Driver-imx585-F9 [slop, minor] Docs: README CineMate section, fork clone URL and the branch name `cinemate-port`
- where: `README.md:37, 148-270@cinemate-port`; `APERTAR.md:9-15@cinemate-port`
- port way: Clone line `git clone -b cinemate-port https://github.com/Tiramisioux/...`. A ~120-line "CineMate branch (`cinemate-7modes`)" section with a CineMate CLI/settings/Redis layer table and a seven-mode matrix that no longer describes the tables. `APERTAR.md` says use `cinemate-port`.
- Apertar way: Baseline and `70bdb26` README clone will127534 and cover only install, overlay and link rates.
- why it matters: After a merge the docs point at the fork and at another product's layers.
- rework: Remove the CineMate layer table and the seven-mode matrix. Keep the blend-menu table, HMAX floor and link-rate notes. Set URL and branch to the merge target.
- effort: S
- deliberate: no.

### Driver-imx585-F10 [removed-upstream-behaviour, minor] Colour 12-bit CCMP Clear HDR is default-on, overriding the driver author's opt-in `ccmp` gate
- where: `imx585.c:4641@cinemate-port` (commit `b6a6f5b`)
- port way: `clearhdr_ccmp = !mono || sony,clearhdr-ccmp`; `ccmp` has no effect on colour.
- Apertar way: Will Whang's `70bdb26` requires the `ccmp` param for both variants. The 1.6.0 image driver offered 4K 12-bit HDR unconditionally (`base imx585.c:1392-1394, 1429-1432@apertar`).
- why it matters: Departs from the driver author's design. Mono needing `ccmp` comes from `70bdb26`, not the port. Unmodified 1.6.0 Core does not use Clear HDR, so no runtime effect there.
- rework: No code change. Name the departure in the merge notes and `APERTAR.md`; agree it with the driver author.
- effort: S
- deliberate: yes. `b6a6f5b` message gives the reason.

### Driver-imx585-F11 [bug, minor] 12-bit Clear HDR is offered on 27 1x1 windowed crops with no recorded hardware validation, while the 2x2 crops are gated for the same reason
- where: `imx585.c:3086-3094@cinemate-port`; `APERTAR.md:160-172@cinemate-port`
- port way: The HDR-12 range is `supported_modes[0..28]`: 1080p binned, 4K, and every 1x1 crop including the 1920/2048 windows (`18c1eb2`, host-only). Hardware evidence exists only for 16-bit 1x1 crops (`fdd767a`) and the seven full-field modes.
- Apertar way: Baseline offered 12-bit HDR at 4K only (`base imx585.c:1392-1394, 1429-1432@apertar`).
- why it matters: Inconsistent risk policy; users may get invalid HDR frames at a crop. Unconfirmed.
- rework: Record one 12-bit HDR take at a 3840 crop and one at a 1920-window crop on the Pi. If they fail, end the range after 4K plus the validated crops.
- effort: S
- deliberate: unknown.

### Driver-imx585-F12 [slop, minor] 55 commits, with 9 `experimental:` subjects, about 7 fix-ups of earlier commits and WP numbers in 13 subjects
- where: `git log origin/apertar..cinemate-port` (`imx585-v4l2-driver`)
- port way: 2026-09-19 has nine `experimental:` commits (`b050b7c`..`4949b06`) and fix-ups such as `7061c74` "Fix IMX585 mode enum and array ordering", `27c7cb4` "Restore IMX585 12-bit mode table ordering", `a09ac49` "experimental: fix mode table after low-res removal". WP-585-n in 13 subjects.
- Apertar way: Driver author's commits are one feature each with a plain subject (`3680bf4`, `c0f5404`, `11178c8`, `70bdb26`).
- why it matters: Hard to review or bisect for the original developer.
- rework: Keep the four Will Whang commits. Squash Patrik's into about 6 feature commits: mode families and window programming, RAW10 families, binned Clear HDR, crop reporting and geometry controls, logging, docs.
- effort: M
- deliberate: no.

### Driver-imx585-F13 [new-ground, nit] The read-only geometry controls (+10..+14) have no Apertar consumer
- where: `imx585.c:44-50@cinemate-port`; `imx585_update_mode_metadata imx585.c:3354-3367@cinemate-port`
- port way: Mode Binning and Mode Crop Left/Top/Width/Height are custom read-only controls; their consumer is cinepi-raw (`cinepi_raw.cpp:177-217`).
- Apertar way: Apertar Core reads only base +0/+1/+5 (`CameraController.cpp:7034-7037@cinemate-port`). Standard `V4L2_SEL_TGT_CROP` carries the same data.
- why it matters: Extra custom controls; a maintainer may wonder who reads them.
- rework: Keep them; say in `APERTAR.md` that Cinemate reads them and Apertar uses the selection API.
- effort: S
- deliberate: yes. Commit `b703f46`.
