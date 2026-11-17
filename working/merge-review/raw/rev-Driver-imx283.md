# Review: Driver-imx283 (stage 2)

Refs: port = `imx283-v4l2-driver` `cinemate-port` `68b7dc9`; baseline = `origin/master` `7751c32` (Will Whang's driver). Upstream Core/UI = `wt/core-upstream`, `wt/ui-upstream` `upstream-1.6.0`. imx585 Apertar driver baseline `origin/apertar` `e5b74d3` used as the nearest "Apertar driver" yardstick.
Files: port `scratchpad/port283.c` = `git show cinemate-port:imx283.c` (3354 lines); base `scratchpad/base283.c` = `git show origin/master:imx283.c` (1838 lines); diff `/home/user/build/review/imx283.diff`.
Yardstick: `apertar-conventions.md` does not exist. Used `conv-platform-build.md` (N8), the imx585 review (`rev-Driver-imx585.md`) for consistency, `sweep-commits-ui-drivers.md`, `sweep-knobs.md`, `sweep-board-support.md`.

## 1. Answers to the scope questions

| Question | Answer | Evidence |
| --- | --- | --- |
| Does Apertar 1.6.0 support the IMX283? | No. `grep -rn -i imx283` in both upstream worktrees returns nothing. The whole sensor family is new ground | confirmed |
| Sensors 1.6.0 claims | IMX477, IMX577, IMX585, IMX294 | `core-upstream README.md:78-81@upstream-1.6.0` |
| Protocol impact (socket, HTTP, flat JSON) | None in this unit. Driver-only; Core consumption is in the Core unit | inventory section 2 |
| How upstream Core describes a sensor's sizes | Inline helper functions in `CameraController.cpp`, e.g. `isImx585FullHdCropResolution` lists `resolutionMatches(resolution, 1920, 1038) ...` | `core-upstream src/camera/CameraController.cpp:366-377@upstream-1.6.0` |
| How the Apertar imx585 driver adds crops | One explicit register list per crop with a small window macro: `IMX585_WIN_CROP_REGS(54, 2076)` under a one-line comment "VST is centered inside the 2160 active area." | `imx585 origin/apertar imx585.c:563-599` |

## 2. Findings

| Id | Sev | Cat | Title |
| --- | --- | --- | --- |
| F1 | major | slop | Comment mass: ~918 of 1723 added lines are comments; 43 references to work packages and absent `development/` files |
| F2 | major | new-ground | `crop_vmax` defaults to 1 (unmeasured timing on), Apertar itself requires 0 |
| F3 | minor | slop | Residue of the reverted active-only experiment: identity wrappers, hand-rolled nearest-size, stale comment |
| F4 | minor | slop | Dead macros `IMX283_CROP_1X1` / `IMX283_CROPPED_1X1_MODE` and the two-candidate `WINDOW_LEFT` switch |
| F5 | minor | bug | Function-local statics shared by all driver instances (`get_mode_table`, `__imx283_get_pad_crop`) |
| F6 | minor | new-ground | `IMX283_ASPECT_MODE` takes 15 positional arguments, parent timing repeated in 51 rows |
| F7 | minor | new-ground | Probe-time `imx283_check_mode_table` audits static data on every boot |
| F8 | minor | duplication | Core `Imx283Modes.hpp` hand-copies the 57 driver rows and the crop_vmax=0 floors |
| F9 | minor | bug | MODE_1C window: `.top = 852` not centred on the corrected active area (784); `.left = 924` OB unchecked on raw |
| F10 | minor | slop | Docs: stale `EXPERIMENTAL_CROPS.md` shipped, APERTAR.md and README name the fork branch and CineMate |
| F11 | minor | slop | 93 commits with an 11-commit reverted experiment, WP numbers, "Your Name" author |
| F12 | nit | new-ground | Nine read-only "Mode *" geometry controls; only cinepi-raw reads them, Apertar Core does not |
| F13 | nit | removed-upstream-behaviour | Base driver sizes 2784x1548 (MODE_2A) and 5568x3094 (MODE_1A) are gone |
| F14 | nit | slop | Small install and formatting changes (`--force`, `REMAKE_INITRD`, lost final newline) |

### F1 major, slop: comment mass and internal vocabulary

- Comment lines: port 1116, base 198 (`grep -c -E "^\s*(/?\*|//)"`). About 918 of the 1723 added lines are comments. Confirmed (count).
- 43 matches of `WP-283|DEC-4|REBUILD|ROUND2|GAP.md|BRIEF.md|development/|Fact [0-9]|check_mode_table.py|ratio_audit` in `port283.c`; 17 matches of `HISTORY|CINEPI_2|2026-` (DNG file names, dates). None of the cited files is in the repo: `git ls-tree -r --name-only cinemate-port` lists 9 files.
- Examples: `imx283.c:26-30` "(WP-283-5) ... per DEC-4"; `:281` module parameter text "see development/imx283-crop-fps/"; `:420-444` a 25-line HISTORY of a wrong 32-column subtraction that no longer exists; `:752-802` 50-line history of `.left` 236/856/924; `:262` "CineMate's 720-line preview stream" in a kernel driver; `:924` "veff is mainline's value (WP-283-3)".
- Apertar way: imx585 `origin/apertar` crops carry one-line comments ("Full-width RAW12 aspect crops. VST is centered inside the 2160 active area.", `imx585.c:585`); the base imx283 has 198 comment lines in total.
- Rework (M): reduce every block to what the code does and the one non-obvious why (e.g. "OB columns lead, OB rows trail; width/height are transport sizes"). Move measurement history, DNG names and the 236/924 story to the KB (`lessons/hardware-log.md`). Drop all WP/DEC/REBUILD/ROUND2/GAP/`development/` references and the module-parameter pointer to a non-existent directory.
- Deliberate: no (comments narrate the agent rebuild rounds).

### F2 major, new-ground: `crop_vmax` default on

- Port: `static bool crop_vmax = true;` `imx283.c:277`; description "experimental, UNMEASURED ... Default 1 = use the experimental per-crop floor" `:279-281`. Used by `imx283_min_vmax` `:2428-2433`.
- APERTAR.md tells Apertar users to create `/etc/modprobe.d/imx283.conf` with `crop_vmax=0` because "Those floors ... have not been measured on a sensor. Apertar therefore runs with crop_vmax=0" (`APERTAR.md:90-110@cinemate-port`). Core's floor table assumes 0 (`Imx283Modes.hpp:9`).
- Same driver, opposite choice for the other unvalidated feature: `experimental_modes` defaults off (`:269`). The imx585 review records the driver author's convention as opt-in for unvalidated features (`rev-Driver-imx585.md` F10).
- Failing input: user follows `README.md` (no modprobe file), runs `rpicam-vid` or any libcamera app on the 2.55:1 Mode-0 row: VBLANK minimum lets it run at about 35 fps on an unmeasured VMAX floor. Apertar Core is capped by `min(probe, floor)` (`CameraController.cpp:3333-3340@cinemate-port`) so Core itself is safe, which also means the parameter buys Apertar nothing.
- Rework (S): either default `crop_vmax` to false, or (preferred, simpler) delete the parameter, the `crop_min_VMAX` field and the `_crop_vmax` macro argument until floors are measured. `sweep-knobs.md:266` (X-knobs-17) reaches the same conclusion.
- Deliberate: yes (94eb7e2 "enable experimental crop VMAX by default", comment `:271-276` "requiring a manual modprobe argument would make the experiment needlessly fragile"). The reason is about a Cinemate experiment, not Apertar.

### F3 minor, slop: residue of the reverted active-only experiment

- `imx283_output_width/height/crop()` return `mode->width/height/crop` unchanged (`imx283.c:399-412`); 31 call sites. They were added by 4350e3e "experimental: emit IMX283 active-only frames" (`git log -S imx283_output_width`) and survived the revert a852cfe as identities.
- `set_pad_format` comment still says "the driver now emits an active-only frame, so the TRY crop is the effective sensor window" (`:2506-2509`). False since a852cfe.
- `imx283_find_nearest_mode` (`:459-480`) replaces the kernel helper `v4l2_find_nearest_size` that the base used (`base283.c:1121`). Same metric (sum of absolute differences); only tie-breaking differs (kernel keeps the last equal entry, port the first). It exists only because the wrappers hid `width`/`height` from the macro.
- Rework (S): delete the three wrappers and use `mode->width`, `mode->height`, `mode->crop`; restore `v4l2_find_nearest_size(mode_list, num_modes, width, height, ...)`; delete the stale comment sentence. Check no table holds two rows with the same transport size (Core test `tools/imx283_modes_test.cpp` can assert it).

### F4 minor, slop: dead and switch macros

- `IMX283_CROP_1X1` (`:739-742`) has no caller; `IMX283_CROPPED_1X1_MODE` (`:709-721`) is only called by it. The comment says "Unused by either mode table ... Kept correct rather than deleted" (`:732-737`). Confirmed by grep: only definition lines match.
- `IMX283_MODE_1C_WINDOW_LEFT_HW_CONFIRMED 236`, `_CENTRED 924`, `IMX283_MODE_1C_WINDOW_LEFT` (`:804-806`): a compile-time A/B switch.
- Rework (S): delete both crop macros; write `.left = 924` in `imx283_mode_1c_window` with one line ("centred: 108 + (5472 - 3840) / 2"); 236 goes to the KB.

### F5 minor, bug: shared function-local statics

- `get_mode_table()` (`:1926-1945`) lazily fills `static filtered_12bit[]`, `filtered_10bit[]`, `filtered_tables_built` without a lock. Callers hold `imx283->mutex`, which is per instance.
- `__imx283_get_pad_crop()` ACTIVE case returns a pointer to `static struct v4l2_rect output_crop` (`:2544-2547`).
- Failing input: CM5 with two IMX283 (`dtoverlay=imx283` and `dtoverlay=imx283,cam0`); two processes call VIDIOC_SUBDEV_G_SELECTION or S_FMT on the two subdevs at once. Each thread holds its own mutex; the static is written by both. First-call race on the table build; the crop race can return the other sensor's crop. Probable (code reading; not run).
- Apertar way: base returned `&imx283->mode->crop` and the const tables directly (`base283.c` `get_mode_table` / `__imx283_get_pad_crop`).
- Rework (S): `return &imx283->mode->crop;`. For the filter, keep the const tables and skip `.experimental` rows where the list is walked (`enum_frame_size` index mapping and nearest-size), or build the filtered copies once in `imx283_probe` into `struct imx283` members.

### F6 minor, new-ground: 15-argument row macro

- `IMX283_ASPECT_MODE(_mode, _bpp, _w, _h, _hmax, _vmax, _crop_vmax, _dhmax, _dvmax, _shr, _veff, _hb, _vb, _hob, _vob)` (`:694-707`), 51 call sites; e.g. `:1060` `IMX283_ASPECT_MODE(IMX283_MODE_0, 12, 3648, 3648, 887, 3793, 3793, 900, 4000, 12, 3694, 1, 1, 96, 16)`. Ten of the fifteen values are the parent mode's constants, repeated in every row of the family.
- Apertar way: imx585 `origin/apertar` uses an explicit entry per crop with one small register macro taking the two numbers that vary (`imx585.c:563-599`). The port's own `IMX283_ASPECT_MODE_1C(_w, _h)` (`:862-874`) already has the readable shape.
- Verdict: simplify. Keep `CENTERED_RECTANGLE` derivation (inherited from base, `base283.c:429-432`). Add one two/three-argument wrapper per family (`IMX283_ASPECT_MODE_0(w, h)`, `_2(w, h)`, `_2A`, `_3`, `_1`, `_1A`) like `_1C`; after F2 the `_crop_vmax` argument disappears.

### F7 minor, new-ground: probe-time table audit

- `imx283_check_mode_table()` (`:1778-1924`), called from probe for both tables (`:3202-3207`). Warns only; six checks (crop inside active area, binning set, even origin, divisibility, width match, active size).
- No precedent in base or imx585 `apertar`. Same pattern as imx585 port F6 (simplify).
- Verdict: simplify. The tables are const data; one host check (Core's `tools/imx283_modes_test.cpp` or a short script kept in the driver repo) covers it without boot-time code. If kept, cut to the two checks that caught real defects (crop inside active area, binning non-zero), 15 lines.

### F8 minor, duplication: Core copies the driver table

- `Imx283Modes.hpp:14-60@cinemate-port` (Core) holds the 57 active sizes, binning and floor fps; header says "the 57 non-experimental modes of the cinemate-port driver ... experimental_modes=0", floors "with crop_vmax=0" (`:1-10`). No link to the driver at build or run time; a table edit in `imx283.c` drifts silently.
- Upstream: sizes inline in `CameraController.cpp` helpers (`core-upstream CameraController.cpp:366-396`), not a separate header; the imx585 port has the same duplication (`rev-Driver-imx585.md` F8).
- Core already probes sensor modes (`CameraController.cpp:10970-11017@cinemate-port`) and converts transport to active.
- Rework (Core unit, M): derive the size list from the libcamera probe plus the transport rule (OB 96/48/32 x 16/4/4); keep only floors that the probe cannot give. At minimum name the driver commit the header matches, not the branch name. Decision belongs to the Core review.

### F9 minor, bug: MODE_1C window origin

- `imx283_mode_1c_window` `.top = 852, .left = 924` (`:808-835`). The comment states 852 is centred against the old swapped `active_area.top = 108`; against the corrected 40 the centred row is 784 (`:816-826`). `.left = 924` is verified only on an ISP preview, not on raw OB columns (`:766-777`, APERTAR.md "Open questions").
- The vertical crop path now programs `.top` into `VWINPOS` for every mode with `veff` and `vbin_ratio` (`:2632-2652`), so 852 is a live register value. Confirmed in code; correctness unconfirmed (needs one raw 3936x2176 frame at 784 and at 852).
- Rework: hardware test; then a single value with a one-line comment. Until then, document in APERTAR.md only (already done) and drop the in-code history (F1).

### F10 minor, slop: documentation

- `EXPERIMENTAL_CROPS.md` (152 lines) begins "STALE: see the tables in imx283.c" and lists what is wrong in it. Shipping a stale doc to fix later is not a merge state.
- `APERTAR.md:10-14` "Use cinemate-port. It is cinemate-modes (the IMX283 modes of the CineMate stack)"; README clone URL `git clone -b cinemate-port https://github.com/Tiramisioux/imx283-v4l2-driver.git`.
- Apertar way: Core README says drivers are installed separately and names none by fork branch (`core-upstream README.md:87`, N8 in `conv-platform-build.md`).
- Rework (S): delete `EXPERIMENTAL_CROPS.md`; APERTAR.md drops the CineMate/branch lineage paragraph and keeps install, modprobe, modes, open questions; branch name decided at merge.

### F11 minor, slop: commit history

- 93 commits; 4350e3e..bbbd49b (11 commits) reverted by a852cfe; two commits with identical subject (4350e3e, 4612d68); WP-283-n in subjects (773c5bb, 4ef5277, 8f2b230, 835cf14, b67ea62, 7e98970, 1177922); author "Your Name" (289131a, 050e2e3); Kernel 6.12 change done, reverted, redone (289131a, 146d24f, 16de05f).
- Rework: the squash plan in `sweep-commits-ui-drivers.md:185` (one mode-set commit plus the small fixes 4a1662e, d810aa7, d6ec1c7, 4064e88, 257c9cf, one docs commit).

### F12 nit, new-ground: geometry controls

- Nine read-only controls on `V4L2_CID_USER_BASE + 0x2100` (`:32-65`, configs `:2226-2300`). Names match the imx585 port's "Mode Binning/Crop *" (`imx585.port.c:3784-3808`); "Mode Active *" are imx283-only. Consumer: cinepi-raw (`core/driver_mode_metadata.hpp:328-331`). Apertar Core does not read them (`grep -rn "Mode Crop" Apertar-Core/src` none, inventory).
- Verdict: keep only if Apertar Core uses them (F8 could: it would replace the hand-copied OB constants); otherwise drop. Same verdict as imx585 F13.
- Deliberate: yes (4ef5277, f46001a).

### F13 nit, removed-upstream-behaviour (driver base, not Apertar)

- Base MODE_2A 2784x1548 transport (`base283.c:468-479`) is replaced by ten rows 2736x1540..1072 active; MODE_1A 5568x3094 becomes 5568x3092 (even Bayer origin).
- Apertar 1.6.0 never requested these (no IMX283), so no Apertar regression. Third-party apps asking for 2784x1548 get the nearest row. Deliberate: yes (commit text for even origin).

### F14 nit, slop: install and formatting

- `setup.sh` `dkms install ... --force`; `dkms.conf` drops `REMAKE_INITRD=no` (deprecated key); `dkms.postinst` adds `-Wno-unit_address_vs_reg`. All harmless and as on the Pi (hardware log 2026-11-10).
- `MODULE_LICENSE("GPL v2");` lost its final newline (`od -c` of the file tail). `imx283_i2c_driver` whitespace churn.
- Rework: restore the newline; keep the rest, one commit "install: force over the stock kernel module".

## 3. Abstraction verdicts

| Abstraction | Verdict | Reason |
| --- | --- | --- |
| `IMX283_ASPECT_MODE()` | simplify | Per-family 2-arg wrappers, parent timing once (F6) |
| `IMX283_ASPECT_MODE_1C()` | keep | Already the readable shape; template for the others |
| `IMX283_CROPPED_1X1_MODE()`, `IMX283_CROP_1X1()` | simplify (delete) | Dead (F4) |
| `IMX283_MODE_1C_WINDOW_LEFT{,_HW_CONFIRMED,_CENTRED}` | simplify (delete) | One literal, history to KB (F4) |
| `imx283_mode_1c_window` | keep | Reference rectangle replacing the base `imx283_UHD_area`; same idea as base |
| `imx283_output_width/height/crop()` | simplify (delete) | Identity residue of a reverted experiment (F3) |
| `imx283_active_width/height()` + `active_width/height` fields | simplify | Override fields are never set (comment `:418` "Nothing currently sets them"); reduce to `width - horizontal_ob`, drop fields; keep only if F12 controls stay |
| `imx283_find_nearest_mode()` | rework-to-upstream-pattern | Use kernel `v4l2_find_nearest_size` as the base did (F3) |
| `build_filtered_mode_table()` + statics in `get_mode_table()` | rework-to-upstream-pattern | Return const tables as the base did and skip `.experimental` while walking, or build per instance in probe (F5) |
| `imx283_check_mode_table()` | simplify | Host check instead of boot-time audit (F7) |
| `imx283_update_mode_metadata()` + 9 controls | simplify | Keep only with an Apertar consumer (F12) |
| `imx283_min_vmax()` + `crop_vmax` + `crop_min_VMAX` | simplify (delete) | Unmeasured, Apertar runs 0 (F2) |
| `experimental_modes` + `.experimental` | keep | Opt-in gate, default off, matches the driver author's convention |
| VCROP path in `imx283_start_streaming` (`veff`, `vst`, `vct`, `vbin_ratio`) | keep | Needed for real vertical crops; register names follow the datasheet; verified for MODE_1C base on hardware (335781d) |
| Core `Imx283Modes.hpp` | simplify (Core unit) | Hand-copied table (F8) |
| Core `tools/imx283_modes_test.cpp` | Core unit decides | Upstream Core has no tests (S13 in conv-platform-build) |
| Absent `development/*` files and WP/DEC vocabulary | delete | F1 |

## 4. What conforms

- `CROP_DEFAULT` returns the active area, split from the current-mode CROP (`imx283.c:2896-2918`, d810aa7). Standard sensor-driver meaning; fixes negative analogCrop.
- Oops fix: crop is written only to TRY state when `sd_state` exists (`:2497-2516`, 4a1662e).
- `imx283_get_format_code` bounds check (`:1975-1992`, d6ec1c7), as other sensor drivers do.
- Per-stream lines `dev_err` -> `dev_dbg` (4064e88).
- `HTRIMMING_END = left + width` matches mainline (`:2671-2686`).
- Kernel 6.12 API (`<linux/unaligned.h>`, `v4l2_subdev_state_get_*`) matches the imx585 Apertar base (`imx585 origin/apertar :16`); one kernel floor for both drivers.
- Overlay `link-frequency` parameter (`imx283-overlay.dts:110-117`) is the same style as the imx585 `ccmp` overlay parameter; default unchanged.
- Geometry controls use the same names and read-only flags as the imx585 port, so one consumer serves both.
- `experimental_modes` defaults off.
- No socket, HTTP, state-field or UI changes in this unit; nothing for the flat JSON parser.
- `APERTAR.md` "Open questions" states the untested items plainly (MODE_1C OB, ALSC scale 0 in 1x1 modes, per-crop VMAX). The ALSC issue comes from transport sizes including OB, inherited from the base (`base283.c:441-442`), not introduced by the port.

## 5. Notes for the handoff

- The product is the final mode tables plus five small fixes. Everything else in the diff is history (comments, dead macros, wrappers, stale doc).
- After F1-F7 the driver diff should shrink to roughly the tables, the VCROP block, `experimental_modes`, the selection/oops/bounds/log fixes and the overlay parameter.

## Skeptic

Checked at imx283 `cinemate-port` 68b7dc9 (HEAD of the shared checkout), base `origin/master`, Will Whang's `origin/6.12.y`, Core `cinemate-port` 01f170c, Core upstream-1.6.0.

| Id | Verdict | Why |
| --- | --- | --- |
| F1 | corrected | Confirmed: 1116 comment lines vs 198 in base; WP/DEC/REBUILD/ROUND2/GAP/development refs are on 37 lines (not 43). Rework stands. |
| F2 | stands | `static bool crop_vmax = true;` imx283.c:277; APERTAR.md:92-113 tells Apertar users to set 0; Core's table cap is the crop_vmax=0 floor (CameraController.cpp:3332-3337). setup.sh/dkms.postinst install no modprobe.d file. |
| F3 | corrected | Wrappers and hand-rolled nearest confirmed (4350e3e/4123dd2/efe2463 survive revert a852cfe). Added: two more stale comments, imx283.c:58-62 ("overclaims by 32 columns", contradicted by the HISTORY at 420-444) and 1463/1504 citing v4l2_find_nearest_size, which the code no longer calls. Tie-break note fixed: kernel breaks on the first exact match and keeps the last of equal non-exact distances. |
| F4 | stands | IMX283_CROP_1X1 has no caller; IMX283_CROPPED_1X1_MODE is used only by it (grep imx283.c:709-742). |
| F5 | stands | `static struct v4l2_rect output_crop` imx283.c:2541; base returned `&imx283->mode->crop` (base imx283.c:1151). Apertar is one-camera, so exposure is CM5 dual-IMX283 only; fix is one line. |
| F6 | stands | 51 IMX283_ASPECT_MODE rows; imx585 origin/apertar uses `IMX585_WIN_CROP_REGS(vst, vwidth)` (imx585.c:569@apertar). After F2 the varying args are only `_w,_h`. |
| F7 | stands | imx283.c:1778-1924, called at probe 3202-3207, dev_warn only. |
| F8 | corrected | Upstream also hand-codes sensor sizes in Core (isImx585FullHdCropResolution, CameraController.cpp:366@upstream-1.6.0), so a hand table is the Apertar way at larger scale. "Derive from probe" is not possible: the probe gives transport sizes, the OB offset depends on binning, libcamera does not pass the driver's custom Mode controls, and floors must stay. Header is 144 lines. Downgraded to nit; rework reduced to provenance. |
| F9 | stands | .top = 852 imx283.c:835, comment 819-833 says it reaches VWINPOS and is centred on the swapped 108. |
| F10 | stands | EXPERIMENTAL_CROPS.md opens "STALE"; APERTAR.md:12-14 lineage cinemate-modes/CineMate; README.md:32 `clone -b cinemate-port`. |
| F11 | corrected | "Your Name" commits 289131a, 050e2e3 and Will Whang's fea3d35, e8e3d4a, fcbda11 come from `origin/6.12.y` (upstream author's branch; origin/master has its own "Your Name" 71140f4). Not port slop. WP numbers in 7 port subjects. |
| F12 | stands | Only consumer is cinepi-raw (core/driver_mode_metadata.hpp, cinepi/cinepi_raw.cpp); none in Apertar-Core/src. |
| F13 | stands | Base 2A transport 2784x1548 (base imx283.c:467-479) -> port 2784x1544; 1A 5568x3094 -> 5568x3092. |
| F14 | corrected | `--force` (fea3d35) and REMAKE_INITRD removal (e8e3d4a) are Will Whang's commits on origin/6.12.y, `git diff origin/6.12.y HEAD -- setup.sh dkms.conf dkms.postinst` is empty. Only port noise: lost final newline after MODULE_LICENSE (6.12.y has it). |

## Final findings

### Driver-imx283-F1 [slop, major] Comment mass and internal vocabulary
- where: imx283.c:26-30, 61, 262, 281, 360, 420-444, 663, 678, 724-737, 752-802, 924, 1023-1035, 1409, 1453-1479, 1810-1825, 2221, 2387-2417, 2673, 2992 @cinemate-port
- port way: 1116 comment lines (base 198). Long HISTORY blocks with DNG file names and dates; WP-283-n, DEC-4, REBUILD.md, ROUND2 Defect C4, GAP.md and development/... references on 37 lines; development/ is not in the repo (9 files). MODULE_PARM_DESC(crop_vmax) points to development/imx283-crop-fps/.
- Apertar way: imx585 origin/apertar crops carry one-line comments ("Full-width RAW12 aspect crops. VST is centered inside the 2160 active area.", imx585.c:585@apertar); base imx283 has 198 comment lines.
- why it matters: The original developer cannot tell current behaviour from narrated history and cannot follow the references.
- rework: Cut each block to what plus one non-obvious why. Move measurement history (2704-vs-2736 columns, 236/924, 784/852) to KB lessons/hardware-log.md. Delete every WP/DEC/REBUILD/ROUND2/GAP/development reference, including MODULE_PARM_DESC(crop_vmax).
- effort: M. deliberate: no (comments narrate agent rebuild rounds).

### Driver-imx283-F2 [new-ground, major] crop_vmax defaults to 1 (unmeasured per-crop VMAX floors on); Apertar requires 0
- where: imx283.c:271-281, 2428-2433 @cinemate-port; APERTAR.md:92-113 @cinemate-port
- port way: `static bool crop_vmax = true;`, description "experimental, UNMEASURED". APERTAR.md tells Apertar users to create /etc/modprobe.d/imx283.conf with crop_vmax=0. Core's table cap is the crop_vmax=0 floor (Core CameraController.cpp:3332-3337, Imx283Modes.hpp:9-10).
- Apertar way: No precedent in Apertar 1.6.0. The same driver gates its other unvalidated feature opt-in (experimental_modes default off, imx283.c:269).
- why it matters: A user following README (setup.sh installs no modprobe.d file) runs any libcamera app on unmeasured VMAX floors, e.g. about 35 fps on the 2.55:1 Mode-0 row. Apertar caps at the crop_vmax=0 floor anyway, so the parameter brings Apertar nothing.
- rework: Delete crop_vmax, the crop_min_VMAX field and the `_crop_vmax` macro argument until floors are measured (at minimum default false). Drop the modprobe.d crop_vmax instruction from APERTAR.md.
- effort: S. deliberate: yes (94eb7e2 "imx283: enable experimental crop VMAX by default"; comment imx283.c:271-276).

### Driver-imx283-F3 [slop, minor] Residue of the reverted active-only experiment and stale comments
- where: imx283.c:399-412, 459-480, 2506-2509, 58-62, 1463, 1504 @cinemate-port
- port way: imx283_output_width/height/crop return mode fields unchanged (31 call sites), added by 4350e3e/4123dd2/efe2463 and kept after revert a852cfe. imx283_find_nearest_mode replaces v4l2_find_nearest_size. Comments still say "the driver now emits an active-only frame" (2506-2509), "on this sensor's 2x2-binned modes that arithmetic overclaims by 32 columns" (58-62, contradicted by 420-444), and cite v4l2_find_nearest_size (1463, 1504) which is no longer called.
- Apertar way: Base used mode->width/height/crop directly and v4l2_find_nearest_size (base imx283.c:1121@origin/master).
- why it matters: Indirection with no function, and comments describing behaviour that was reverted or disproved.
- rework: Delete the three wrappers and use mode fields; restore v4l2_find_nearest_size; delete or fix the three stale comments. Tie-breaking differs (kernel stops at the first exact match, keeps the last of equal non-exact distances; port keeps the first): assert no duplicate transport sizes per table in a host check.
- effort: S. deliberate: no.

### Driver-imx283-F4 [slop, minor] Dead macros IMX283_CROP_1X1 / IMX283_CROPPED_1X1_MODE and compile-time WINDOW_LEFT switch
- where: imx283.c:709-742, 804-806 @cinemate-port
- port way: IMX283_CROP_1X1 has no caller and IMX283_CROPPED_1X1_MODE is used only by it ("kept correct rather than deleted"). Three macros select between 236 and 924.
- Apertar way: no precedent; base had one imx283_UHD_area rectangle (base imx283.c:223@origin/master).
- why it matters: Dead code and an A/B switch read as unfinished.
- rework: Delete both crop macros; write `.left = 924` with a one-line derivation; 236 history to the KB.
- effort: S. deliberate: yes (comment imx283.c:732-737).

### Driver-imx283-F5 [bug, minor] Function-local statics shared by all driver instances
- where: imx283.c:1926-1945, 2534-2550 @cinemate-port
- port way: get_mode_table lazily builds static filtered tables without a lock; __imx283_get_pad_crop returns a pointer to `static struct v4l2_rect output_crop`.
- Apertar way: Base returned the const tables and `&imx283->mode->crop` (base imx283.c:717-735, 1143-1155@origin/master).
- why it matters: With two IMX283 (CM5 cam0+cam1), concurrent G_SELECTION on the two subdevs hold different mutexes and write the same static; one can return the other sensor's crop. Probable, not run. Apertar runs one camera, so exposure is low; the fix is trivial.
- rework: `return &imx283->mode->crop;`. Keep const tables and skip `.experimental` entries while walking (enum_frame_size, nearest size), or build filtered copies per instance in probe.
- effort: S. deliberate: no.

### Driver-imx283-F6 [new-ground, minor] IMX283_ASPECT_MODE takes 15 positional arguments; parent timing repeated in 51 rows
- where: imx283.c:694-707, 1060-1111, 1466-1474 @cinemate-port
- port way: `IMX283_ASPECT_MODE(IMX283_MODE_0, 12, 3648, 3648, 887, 3793, 3793, 900, 4000, 12, 3694, 1, 1, 96, 16)` per row.
- Apertar way: imx585 origin/apertar uses small macros over the varying numbers, `IMX585_WIN_CROP_REGS(vst, vwidth)` (imx585.c:563-572@apertar); the port's own IMX283_ASPECT_MODE_1C(_w,_h) (imx283.c:862) has that shape.
- why it matters: Unreadable rows; a parent timing change must be repeated in every row.
- rework: One `(_w, _h)` wrapper per family (MODE_0/2/2A/3/1/1A) over the generic macro, as _1C; keep the CENTERED_RECTANGLE derivation. Do after F2 (crop_vmax gone removes the last per-row timing argument).
- effort: S. deliberate: yes (macro comment explains removal of left/top args).

### Driver-imx283-F7 [new-ground, minor] Probe-time imx283_check_mode_table audits static data every boot
- where: imx283.c:1757-1924, 3202-3207 @cinemate-port
- port way: About 150-line six-check audit, dev_warn only, run in every probe.
- Apertar way: no precedent in base or imx585 origin/apertar.
- why it matters: Boot-time kernel code for compile-time data.
- rework: Move to a host check (a small script or test in the driver repo); if kept, only crop-inside-active and binning non-zero.
- effort: S. deliberate: yes (comment imx283.c:1757-1776).

### Driver-imx283-F8 [duplication, nit] Core Imx283Modes.hpp hand-copies the 57 driver rows; provenance is a branch name
- where: Apertar-Core/src/camera/Imx283Modes.hpp:1-144 @cinemate-port; Apertar-Core/src/camera/CameraController.cpp:656-686, 3332-3337 @cinemate-port
- port way: Separate header with the 57 active sizes and crop_vmax=0 floors, host-tested by tools/imx283_modes_test.cpp; header cites "Tiramisioux/imx283-v4l2-driver, branch cinemate-port".
- Apertar way: Upstream hand-codes sensor sizes in Core too, inline (isImx585FullHdCropResolution, CameraController.cpp:366-377@upstream-1.6.0). So a hand table is upstream's pattern at a larger scale; the probe cannot replace it (transport sizes only, OB offset depends on binning, libcamera does not expose the driver's Mode controls, floors still needed).
- why it matters: A driver table edit drifts silently from Core; the branch name will not exist after merge.
- rework: Keep the table. Replace the branch name with the driver commit it matches; add one line in the driver's APERTAR.md that Core's Imx283Modes.hpp must change with the mode tables. The host-test question belongs to the Core test-policy review, not here.
- effort: S. deliberate: yes (header comment states the experimental_modes=0 / crop_vmax=0 contract).

### Driver-imx283-F9 [bug, minor] MODE_1C window .top = 852 not centred on the corrected active area (784); .left 924 OB unchecked on raw
- where: imx283.c:808-835, 2632-2652 @cinemate-port
- port way: `.top = 852` is centred against the old swapped active.top=108 and is programmed into VWINPOS (comment 828-833); 924's columns 0..95 confirmed only on an ISP preview frame.
- Apertar way: no precedent.
- why it matters: UHD window off-centre by 68 rows; DNG ActiveArea may be wrong if columns 0..95 at 924 are not OB.
- rework: One raw 3936x2176 frame at .top 784 and 852 with .left 924; then one value with a one-line comment.
- effort: S. deliberate: yes (APERTAR.md Open questions).

### Driver-imx283-F10 [slop, minor] Docs: stale EXPERIMENTAL_CROPS.md shipped; APERTAR.md and README name the fork branch and CineMate
- where: EXPERIMENTAL_CROPS.md:1-25; APERTAR.md:7-14; README.md:32 @cinemate-port
- port way: Doc marked STALE kept; lineage paragraph about cinemate-modes/CineMate; `git clone -b cinemate-port` of the fork.
- Apertar way: Core README says drivers are installed separately and names no fork branch (core-upstream README.md:87@upstream-1.6.0).
- why it matters: Stale doc and Cinemate lineage confuse the reader.
- rework: Delete EXPERIMENTAL_CROPS.md and its mentions (APERTAR.md:7-8, MODULE_PARM_DESC(experimental_modes), imx283.c:257); trim APERTAR.md to install, config.txt, modprobe, modes, open questions; set the branch name at merge.
- effort: S. deliberate: yes (53ae581 marked it stale instead of deleting).

### Driver-imx283-F11 [slop, minor] Port history: reverted 11-commit experiment, WP numbers in subjects
- where: git log origin/master..cinemate-port: 4350e3e..a852cfe (11 commits), 773c5bb, 4ef5277, 8f2b230 and 4 more WP subjects
- port way: 93 commits; about 87 port commits after the 6 from origin/6.12.y (Will Whang, "Your Name": upstream author's history, not port). Step-by-step history with an experiment and its revert, WP-283-n in 7 subjects.
- Apertar way: conv-style-commits.md; squash plan sweep-commits-ui-drivers.md:185.
- why it matters: The reader cannot tell from the steps which of 236/924 or which table is current.
- rework: Rebase on origin/6.12.y as the baseline; port as one mode-set commit plus 4a1662e, d810aa7, d6ec1c7, 4064e88 and one docs commit (257c9cf is already on 6.12.y).
- effort: M. deliberate: no.

### Driver-imx283-F12 [new-ground, nit] Nine read-only Mode * geometry controls have no Apertar consumer
- where: imx283.c:25-65, 2221-2300, 2387-2426 @cinemate-port
- port way: Custom controls at V4L2_CID_USER_BASE+0x2100, read by name by cinepi-raw (core/driver_mode_metadata.hpp, cinepi/cinepi_raw.cpp); no reader in Apertar-Core/src.
- Apertar way: no precedent in 1.6.0; same names as the imx585 port.
- why it matters: API surface whose only consumer is Cinemate's recorder.
- rework: Drop with the active_width/active_height fields unless an Apertar consumer is planned; if kept, document them in APERTAR.md as a Cinemate interface.
- effort: S. deliberate: yes (4ef5277, f46001a).

### Driver-imx283-F13 [removed-upstream-behaviour, nit] Base sizes 2784x1548 (MODE_2A) and 5568x3094 (MODE_1A) removed
- where: imx283.c:1102-1111, 1168 @cinemate-port; base imx283.c:467-512@origin/master
- port way: MODE_2A full entry replaced by ten 2736-wide rows (1.78:1 = 2784x1544); MODE_1A height 3078 -> 3076 (transport 5568x3092).
- Apertar way: Apertar 1.6.0 never requested these (no IMX283); baseline is Will Whang's driver (95183c8 added 2A, by Patrik).
- why it matters: Third-party apps asking for the old sizes get the nearest row; no Apertar regression.
- rework: None; one line in the driver doc.
- effort: S. deliberate: yes (even Bayer origin, comment imx283.c:1459-1462).

### Driver-imx283-F14 [slop, nit] Lost final newline after MODULE_LICENSE
- where: imx283.c:3354 @cinemate-port
- port way: File ends without newline; origin/master and origin/6.12.y end with one. (`--force` and REMAKE_INITRD are Will Whang's fea3d35/e8e3d4a on origin/6.12.y, not port.)
- Apertar way: no precedent (driver install is outside Apertar).
- why it matters: Noise in the diff.
- rework: Restore the newline.
- effort: S. deliberate: no.
