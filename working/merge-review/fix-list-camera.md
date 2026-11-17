# Fix list: Camera controller, sensor modes, drivers

Editor's list for the merge review. Units: CC-1, CC-4, CC-5, Camera-headers, Driver-imx585, Driver-imx283; plus this domain's findings from the sweeps board-support, stock-behaviour, state-consistency and knobs. Port refs `@cinemate-port` (Core `01f170c`, UI `7ea9afc`, imx585 `cd548ef`, imx283 `68b7dc9`). Upstream refs `@upstream-1.6.0` (`/home/user/wt/core-upstream`); `@main` is fork main `f60e301`; driver baselines `@origin/apertar` (imx585 `e5b74d3`) and `@origin/master` (imx283). `CC` = `src/camera/CameraController.cpp`, `App` = `src/ApertarCoreApp.cpp`, `WCP` = `src/web/WebControlPage.cpp`.

Rule ids from `apertar-conventions.md` are written `rule CAM-n`, `STY-n`, `R<n>` (recipe) so they do not clash with the item ids `CAM-<n>` of this list. `check_core.sh` and `smoke_core.sh` are in `/home/user/build/bin/`. APP-n ids are the core-app list (`fix-list-core-app.md`); where an item is split between the two lists, both halves go in one commit.

## Already done on the improvement branch

| Commit | What | Closes |
| --- | --- | --- |
| Core `04fe197` | GPIO chip setting back on the Controls page; claims and checks per chip | Hardware domain (HW-controls-model-F1, X-board-support-1). Nothing in this domain is fixed yet |

## Summary

| Id | Sev | Kind | Rec | Effort | Title |
| --- | --- | --- | --- | --- | --- |
| CAM-1 | blocker | removed | ask-owner | M | IMX585 1.85:1 crops renamed in the driver and rewritten by Core; colour crop sizes lost the auto-config fallback |
| CAM-2 | major | stock | ask-owner | S | FPS ceilings come from the probe alone and the IMX585 lossless 30 fps cap is lifted by default |
| CAM-3 | major | stock | ask-owner | S | Preview temporal denoise off by default also strips TDN from H.264, ProRes and processed stills |
| CAM-4 | major | mismatch | fix-now | M | TDN strip: a 451-line header with its own JSON parser, atomic writer, sidecar and cache folder |
| CAM-5 | major | mismatch | fix-now | M | DNG copy worker returns requests through a set-once setRequestRelease(libcamera::Request*) callback |
| CAM-6 | major | mismatch | fix-now | M | Storage pre-roll writes fps after the sanitiser and re-pins FrameDurationLimits on every request |
| CAM-7 | major | mismatch | ask-owner | M | Raw buffer and request count: kActiveRequestCount gone, a process-global media root, three evaluations per configure, no board cap |
| CAM-8 | major | mismatch | ask-owner | M | Mode ladder persists in its own mode_ladder.conf, with a copied path function |
| CAM-9 | major | knob | fix-now | S | Camera bench knobs: restore switches, never-set gains and an RT priority knob measured with no effect |
| CAM-10 | major | knob | fix-now | S | IMX283 driver turns on unmeasured per-crop VMAX floors by default; Core caps them away again |
| CAM-11 | major | slop | fix-later | M | Ticket numbers, Cinemate history, KB paths, dates and banners in Core camera comments and in a written file |
| CAM-12 | major | slop | fix-later | M | Driver comments and docs: work-package history, 'Experimental' on shipping modes, absent files, stale lines, Cinemate sections |
| CAM-13 | minor | bug | fix-now | S | Speed ramp: a mid-ramp FPS can be saved as the operator's FPS; the keep-exposure shutter leaks into another format's profile |
| CAM-14 | minor | stock | fix-now | S | Lossless ISO cap raised to 1600 on every sensor; auto ISO kept in IMX585 lossless with any tuning |
| CAM-15 | minor | mismatch | fix-now | S | Clear HDR ISO caps read from a [camera] section of apertar-hardware.conf by the camera controller |
| CAM-16 | minor | mismatch | fix-now | S | Ladder and clip-name methods return errors and data through out-parameters |
| CAM-17 | minor | new-ground | fix-now | S | ladder_text: Core composes a UTF-8 display line; ladderCount repeats ladder_tops |
| CAM-18 | minor | slop | fix-now | S | conform_fps: persisted, settable, published and in presets, with no reader and no control |
| CAM-19 | minor | board | fix-now | S | Ladder editor ignores recording_capabilities: every compression reads usable on a board without raw compression |
| CAM-20 | minor | mismatch | fix-now | S | Six new booleans written as true/false in camera_settings.conf |
| CAM-21 | minor | mismatch | fix-now | S | Speed ramp writes a journal line per set_fps and per transition; the refusal names a socket command |
| CAM-22 | minor | duplication | fix-now | S | Core mirrors the driver mode tables by hand; rows the driver refuses vanish without a log line; provenance is a branch name |
| CAM-23 | minor | docs | fix-now | S | Tested scope not stated: sensor paths run on a CM5 only; drivers need kernel 6.12 |
| CAM-24 | minor | bug | fix-now | S | imx283: function-local statics shared by all sensor instances |
| CAM-25 | minor | new-ground | ask-owner | M | Speed-ramp audio stretch: undeclared rubberband started as a detached double fork of sh -c, default on |
| CAM-26 | minor | mismatch | ask-owner | S | set_resolution refuses an IMX585 size the current class lacks; upstream sanitises silently |
| CAM-27 | minor | new-ground | ask-owner | S | imx585 driver: 960/1024-wide families hidden by Core, and a Clear HDR test module parameter with a CineMate test kit |
| CAM-28 | minor | new-ground | keep-and-document | S | Frame-rate phase lock: keep the servo, cut the socket telemetry and fix its comments |
| CAM-29 | minor | new-ground | keep-and-document | S | Deliberate departures from stated upstream intents: tell the original developer |
| CAM-30 | minor | new-ground | keep-and-document | S | Camera host tests: four tests in three styles with build lines in comments |
| CAM-31 | minor | new-ground | fix-later | S | Mode-ladder override: one flag set by setClearHdr and cleared by hand in six setters; lost at restart |
| CAM-32 | minor | duplication | fix-later | S | IMX585 and IMX283 exact-mode checks repeat the bit-depth and PISP_COMP1 logic |
| CAM-33 | minor | new-ground | fix-later | S | Both drivers audit their static tables at every probe; imx585 warns about a known duplicate on every boot |
| CAM-34 | minor | slop | fix-later | S | Driver dead code: an unused VMAX override, identity wrappers, dead crop macros |
| CAM-35 | minor | bug | fix-later | S | imx585 1440x1080 frames differently at 12-bit (1x1 window) and 10-bit (2x2 of 2880) |
| CAM-36 | minor | bug | fix-later | S | imx585 12-bit Clear HDR offered on 27 1x1 crops without a recorded take |
| CAM-37 | minor | bug | fix-later | S | imx283 MODE_1C window .top = 852 is centred on the old active area; .left 924 OB unchecked on raw |
| CAM-38 | minor | commit | fix-later | M | Driver histories: experiments, reverts, fix-ups and WP numbers in subjects |
| CAM-39 | minor | new-ground | fix-later | S | imx283 IMX283_ASPECT_MODE takes 15 positional arguments; parent timing repeated in 51 rows |
| CAM-40 | minor | bug | fix-later | S | {res} clip-name token labels by width only |
| CAM-41 | minor | mismatch | fix-later | S | Rung::compression is a free string mixing record format and compression |
| CAM-42 | nit | new-ground | keep-and-document | S | Read-only Mode geometry controls in both drivers have no Apertar consumer |
| CAM-43 | nit | removed | keep-and-document | S | imx283 base sizes 2784x1548 (MODE_2A) and 5568x3094 (MODE_1A) replaced |
| CAM-44 | nit | slop | fix-later | S | CdngLog accepts spellings that never shipped; CdngLog::Auto means On |
| CAM-45 | nit | mismatch | fix-later | S | Small CameraController nits: include order, public data members, namespace spelling, lone assert, repeated mono expression, duplicated row loop |

## Owner questions in this list

| Item | Question (short) | Recommendation |
| --- | --- | --- |
| CAM-1 | Driver back to 3840x2076 / 1920x1038 (A) or keep 2072/1036 and let Core accept both (B)? | Recommend A |
| CAM-2 | Restore the 1.6.0 ceilings as the default (min(table, probe) and lossless 30) or keep the probe-only ceilings? | Recommend restore |
| CAM-3 | Same question as APP-6: default preview TDN back to on (1.6.0) or keep it off for raw formats only? | Recommend on plus the format test |
| CAM-6 | Pre-roll at the recordable maximum (maximumFpsForSettings, what a take can reach) or at the sensor maximum past the lossless and ladder caps? | Recommend the recordable maximum |
| CAM-7 | Keep one request per buffer in SDR raw takes (measured only in 4K Clear HDR 16-bit on a CM5) or go back to upstream's 3 requests of 4 buffers there? | Recommend upstream's 3 of 4 for SDR, 8 of 8 for Clear HDR |
| CAM-8 | Fold the ladder into camera_settings.conf (recommended: one camera settings file, the persister covers it, R2 recipe; cost: a one-time migration read of the owner's mode_ladder.conf) or keep the separate file (cost: the original developer learns a second camera settings file with its own writer; only the path copy and T34 get fixed)? | The first option (recommended) |
| CAM-25 | Keep the stretched WAV in Core (fixed as above, default on as you chose in ca7b7c2) or move it to an offline script? | Recommend keep in Core with the waited argv launch and the install check |
| CAM-26 | Let set_resolution take the nearest IMX585 row silently, like every other limit (recommended; cost: a client that sends a wrong size gets another size back instead of an error), or keep the refusal (cost: an IMX585-only exception to rule CAM-21 the original developer must learn)? | The first option (recommended) |
| CAM-27 | Drop the 960/1024-wide crop families from the Apertar driver (recommended: no hidden modes, no Core filter, less table to validate; cost: Cinemate-side use needs its own branch) or offer them in Apertar (cost: 42 unvalidated modes on the menus)? | The first option (recommended) |

## CAM-1. IMX585 1.85:1 crops renamed in the driver and rewritten by Core; colour crop sizes lost the auto-config fallback

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | blocker | M | yes | ask-owner | CC-1-F1, Driver-imx585-F1, CC-4-F2, X-stock-behaviour-4, X-board-support-14, Driver-imx585-F6, X-state-consistency-3 |

**Where.** `Core src/camera/CameraController.cpp:441-462@cinemate-port`; `CC:703, :10514, :10648, :11060, :12663@cinemate-port`; `CC:8295-8296@cinemate-port`; `CC:8485-8530@cinemate-port`; `CC:7166-7190@cinemate-port`; `src/camera/Imx585Modes.hpp:39-98@cinemate-port`; `imx585-v4l2-driver imx585.c:867, :918, :1121-1127, :2962-2966@cinemate-port`

**Problem.** The port driver advertises 3840x2072 and 1920x1036 where the Apertar driver (origin/apertar e5b74d3) and 1.6.0 Core use 3840x2076 and 1920x1038. Port Core rewrites the old sizes unconditionally in clampCaptureSettings, set_resolution, presets and ladder rungs (confirmed, CC:446-462), and dropped the IMX585 clause from allowAutoSensorConfigFallback (confirmed, CC:8295-8296). On the stock driver a saved 1.85:1 crop is moved to a size that driver lacks and the explicit configure has no fallback (probable; not run on a Pi). Core and driver can only merge together, and both 1.6.0 UIs list sizes the port driver no longer has.

**Apertar way.** isImx585FullHdCropResolution / isImx585Raw12CropResolution list 1038 and 2076 (src/camera/CameraController.cpp:366-396@upstream-1.6.0), matching the driver (imx585.c:817, :1007@origin/apertar). The fallback clause '|| (sensorFamily_ == SensorFamily::Imx585 && isImx585Raw12CropResolution(sanitized.resolution))' is at CC:5993-5996@upstream-1.6.0. Sizes are retired only in the per-sensor normaliser (CC:511-532@upstream-1.6.0); capabilities are detected at run time (rule CAM-35); recipe R6 step 1: the driver must offer the mode.

**Rework.**

1. Both answers: delete migratedImx585CropResolution and migrateImx585LadderRungs (CC:441-462) and their five calls (CC:703, :10514, :10648, :11060, :12663) with the comment block.
2. Both answers: restore the fallback in CameraSession::configureAndStart (CC:8295-8296) by copying CC:5993-5996@upstream-1.6.0, with the port's isImx585LegacyCropResolution (CC:497) as the predicate. Run the colour exact-mode rejection block (CC:8485-8530) only for a candidate that used the explicit sensorConfig.
3. Both answers: isImx585LegacyCropResolution lists 1038 and 2076 again, beside 1036 and 2072.
4. Answer A (recommended), driver: in supported_modes[] and supported_10bit_modes[] replace IMX585_MODE_CROP_3840X2072 and IMX585_MODE_CROP_BIN_1920X1036 by 3840x2076 and 1920x1038 with crop {0, 40, 3840, 2076} (VST 52; passes imx585_program_window()). This also ends the 3840x2072 duplicate-size warning (Driver-imx585-F6). Delete 'Sizes that changed' in APERTAR.md.
5. Answer A, Core: in Imx585Modes.hpp change the 1.85:1 rows back to 2076 / 1038. A camera that saved 2072/1036 resolves through imx585::nearest() in the normaliser; no migration code.
6. Answer B: the driver keeps 2072/1036. Imx585Modes.hpp lists both heights for the 1.85:1 row; the start probe (CC:7166-7190) keeps the row the driver accepts; imx585ModeForResolution maps 2076<->2072 and 1038<->1036 to the probed row; README names the driver requirement.
7. Either answer: the WebUI alias entries (WCP:9078-9085) go (WCP editor). The touch UI lists keep 2076/1038 (X-state-consistency-3; adding the new modes there is the UI editor's).

**Owner decision.** Driver back to 3840x2076 / 1920x1038 (A) or keep 2072/1036 and let Core accept both (B)? Recommend A: Core and driver merge independently, the 1.6.0 UIs stay valid, Core carries no alias pair; cost one take at each size on the Pi to confirm the VST-52 window. B costs a permanent size alias in Core and a 'needs driver X' line in the README.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; tools/imx585_modes_test.cpp updated for the rows; --simulate: {"cmd":"set_resolution","value":"3840x2076"} replies 3840x2076; A: python3 /home/user/imx585-v4l2-driver/tools/replay_mode_table_audit.py shows no duplicate.

**Needs the Pi.** Stock driver e5b74d3: resolution=3840x2076 and 1920x1038 in camera_settings.conf, restart, journalctl -u apertar-core | grep 'camera configured' shows the size. A: one 12-bit take at each size with the changed driver; DNG width/height and framing centred.

**Risk.** VST 52 is two rows off centre; only a take shows whether the image is clean.

## CAM-2. FPS ceilings come from the probe alone and the IMX585 lossless 30 fps cap is lifted by default

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| stock | major | S | yes | ask-owner | Camera-headers-F3, Camera-headers-F4, X-stock-behaviour-3, CC-4-F4, Camera-headers-F16 |

**Where.** `src/camera/FpsCeiling.hpp:1-47@cinemate-port`; `src/camera/CameraController.cpp:3112-3144@cinemate-port`; `CC:3398-3423@cinemate-port`; `CC:3426-3434, :3470, :8634-8639@cinemate-port`; `tools/fps_ceiling_test.cpp@cinemate-port`

**Problem.** maximumSupportedFpsForResolution returns the probed fps whenever the probe has one (resolveSensorMaxFps, tableOnly only with APERTAR_FPS_LIMIT=table; confirmed). IMX585 4K SDR rises from 30 to about 60 on a stock camera, and the IMX477 ceilings become whatever its driver reports. losslessMaximumFps gives the IMX585 the mode maximum instead of 30 unless APERTAR_LOSSLESS_FPS_LIMIT is set (confirmed, CC:3134-3144). The only on-camera datum is one 2 s 4K 60 fps lossless pre-roll. backendMaximumFps returns nullopt and applyBackendCap wraps it (dead indirection with a KB-citing comment).

**Apertar way.** Hard-coded tables with validate() as the last word: IMX585 3840x2160 = 30.0 (CC:2669-2671@upstream-1.6.0); lossless 'const double maximumFps = imx585 ? 30.0 : ...' in enforceLosslessCaptureLimits (CC:2470-2490@upstream-1.6.0). Fork main added the probe as min(table, probed) (CC:2763-2770@main). Pure rules stay in CC beside their callers (rule CAM-3, rule CAM-4).

**Rework.**

1. maximumSupportedFpsForResolution (CC:3412-3423): return probed ? std::min(table, *probed) : table, as CC:2763-2770@main. Delete fpsLimitTableOnly() and imx283ProbeFpsOnly() (CAM-10).
2. losslessMaximumFps (CC:3136-3144): IMX585 lossless returns 30.0 again (CC:2485-2486@upstream-1.6.0). Delete losslessFpsOverride() and the comment that calls 30 a policy.
3. Delete backendMaximumFps and fpsceiling::applyBackendCap; restore the plain maximumSupportedFpsForResolution call at CC:8634, CC:3470 and in prerollMaximumFps; delete the comment at CC:3378.
4. Delete src/camera/FpsCeiling.hpp, its include at CC:2 and tools/fps_ceiling_test.cpp.
5. To raise a ceiling later, edit the row in tableMaximumFpsForResolution after counted takes, as upstream does per mode (recipe R6 step 2).

**Owner decision.** Restore the 1.6.0 ceilings as the default (min(table, probe) and lossless 30) or keep the probe-only ceilings? Recommend restore: a stock camera offers only rates Apertar has shown to record; cost: 4K SDR 60 and lossless above 30 come back as table edits once takes prove them. Keeping probe-only costs a stated product change the original developer must accept with one 2 s pre-roll as evidence, and the restore switches still go.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; --simulate has no sensor probe, so check by reading maximumSupportedFpsForResolution and losslessMaximumFps against CC:2763-2770@main and CC:2485-2486@upstream-1.6.0; /home/user/build/bin/smoke_core.sh /home/user/build/core-work-nolc/apertar-core 8011 before/after.

**Needs the Pi.** IMX585 4K 12-bit SDR uncompressed and lossless: get_state shows fps_max 30; set_fps 60 replies 30.

**Risk.** The owner's rig loses 60 fps until the table row is raised.

**Depends on.** CAM-10

## CAM-3. Preview temporal denoise off by default also strips TDN from H.264, ProRes and processed stills

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| stock | major | S | yes | ask-owner | Camera-headers-F2, X-stock-behaviour-6, X-knobs-4, X-board-support-15 |

**Where.** `include/apertar/core/Types.hpp:139@cinemate-port`; `src/camera/CameraController.cpp:7302-7318@cinemate-port`; `CC:7411-7412@cinemate-port`; `src/camera/TuningTdnStrip.hpp:3-6@cinemate-port`

**Problem.** bool previewTdn = false. The loadablePath lambda (CC:7309-7318, confirmed) loads a copy of the tuning file without rpi.denoise tdn for every record format and photo mode, and makeProresIspTuning derives the ProRes/log tuning from that copy (CC:7411). For H.264, ProRes and JPEG/PNG/TIFF stills the ISP output is the recording, so a stock Pi 5 records them without temporal denoise. The strip also hits a tuning file the user picked, against the comment at CC:7302. Same change as APP-6 in the core-app list; this list holds the CC/Types half, one commit.

**Apertar way.** libcamera loads the resolved tuning file unchanged for every stream (CC:5265-5268, :5347-5361@upstream-1.6.0). Monitoring aids never change footage (rule CAM-39); a derived tuning never replaces the user's file (src/color/ProresIspProfile.hpp:7@upstream-1.6.0).

**Rework.**

1. loadablePath (CC:7309-7318): strip only when 'automaticTuning && !settings.previewTdn && !isProcessedVideoFormat(settings.recordingFormat) && !settings.photoModeEnabled'. isProcessedVideoFormat exists (CC:280, and upstream).
2. Confirm setRecordingFormat and setPhotoMode reconfigure (applySettingsLocked(next, true), CC:11390) so the right file loads after a switch.
3. Answer A: Types.hpp:139 previewTdn = true; the owner's rig sets preview_tdn=0 in camera_settings.conf. Answer B: keep false; README and handoff say the DNG preview of a stock camera is without TDN.
4. Correct the comments at Types.hpp:139 and TuningTdnStrip.hpp:3-6.

**Owner decision.** Same question as APP-6: default preview TDN back to on (1.6.0) or keep it off for raw formats only? Recommend on plus the format test: costs the rig one settings line. Off keeps a faster, noisier DNG preview on every stock camera, which the original developer must be told with the single measurement behind it.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; tools/tuning_tdn_strip_test.cpp (or its CAM-4 successor) gains a case: H.264, ProRes and a picked file keep tdn.

**Needs the Pi.** Record H.264 and ProRes with defaults: journalctl -u apertar-core | grep -i tuning names the original file, not the _notdn copy.

**Risk.** None for stock; the rig's preview gets slower if A and the line is forgotten.

## CAM-4. TDN strip: a 451-line header with its own JSON parser, atomic writer, sidecar and cache folder

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | fix-now | Camera-headers-F1 |

**Where.** `src/camera/TuningTdnStrip.hpp:43-249, :350-378, :380-449@cinemate-port`; `tools/tuning_tdn_strip_test.cpp@cinemate-port`

**Problem.** A recursive-descent JSON parser (tdn_detail::Parser/Node/Member) cuts tdn members by byte offset, writes with its own temp+rename, keeps a .src sidecar with size and mtime, and caches in $HOME/.cache/apertar-core/tuning. Upstream already edits tuning JSON with libyaml for the same purpose. The KB had recommended the libyaml derivation (dng-chain/F/F6.md:243); the port did not follow it.

**Apertar way.** makeProresIspTuning: '#include <yaml.h>' (src/color/ProresIspProfile.cpp:13@upstream-1.6.0), algorithm()/member() at :72-87, byte-range Edit applied back to front at :89-90 and :221, cache $HOME/.cache/apertar-prores at :230, 'if (previous!=text && !settingsFile::atomicWrite(path,text))' at :233. Header comment ProresIspProfile.hpp:7: 'Writes an internal derived tuning, never the user's selected source file.' libyaml is REQUIRED already (rule CAM-20).

**Rework.**

1. Add bool makePreviewTuning(const std::string &source, std::string &destination, std::string &error) to src/color/ProresIspProfile.cpp, reusing its libyaml algorithm("rpi.denoise"), member() and Edit helpers. Replace each rpi.denoise mapping with its content minus tdn (one Edit per node), so no comma surgery is needed.
2. Write to $HOME/.cache/apertar-prores/preview-<name>.json with settingsFile::atomicWrite only when the text changed (copy :230-233). No sidecar.
3. loadablePath calls makePreviewTuning instead of tuning::previewTuningPath; keep the fall-back-to-source rule and its log line.
4. Delete src/camera/TuningTdnStrip.hpp. Turn tools/tuning_tdn_strip_test.cpp into a check of makePreviewTuning or delete it (CAM-30).
5. Do not use the pipeline disable_tdn option: it stalls the PiSP back end (pisp.cpp:1659-1663@libcamera 6b0b49f).

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; compare the derived file for imx585.json and imx477.json from defaults-pisp: rpi.denoise has no tdn member, the rest parses (python3 -c 'import json,sys; json.load(open(sys.argv[1]))' <file>).

**Needs the Pi.** Preview with preview_tdn=0: journalctl shows the derived path; libcamera loads rpi.denoise with sdn/cdn at their *_no_tdn values (denoise.cpp:54-69); preview frame rate as before.

**Risk.** Output is no longer byte-identical to the KB tool's _notdn files.

**Depends on.** CAM-3

## CAM-5. DNG copy worker returns requests through a set-once setRequestRelease(libcamera::Request*) callback

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | fix-now | CC-4-F1 |

**Where.** `src/camera/CameraController.cpp:8731-8739@cinemate-port`; `CC:5032-5065, :5151-5162@cinemate-port`; `CC:9498-9516@cinemate-port`

**Problem.** After makeRequests the session installs recorder_.setRequestRelease([this](libcamera::Request *r){...requeueRequest(r);}, buffers-2) and recorder_.setFrameQueued(audio observe). PendingCopy carries a libcamera::Request*, and the worker calls back through the stored function. The recorder now knows libcamera and holds two session-wide callbacks plus a hold limit set from outside.

**Apertar way.** Per-frame std::function<void()> closures; the recorder never sees a Request: ProRes '[this, request, cachedFd]{ ... requeueRequest(request); }' (CC:7419-7425@upstream-1.6.0), H.264 'releaseRequest = [this, request]{ requeueRequest(request); }' (:7456-7465), job field 'std::function<void()> release' (:3937). Audio is observed on the completion thread after enqueue (:7428-7430). rule CAM-1: libcamera stays in the session; rule CAM-14: a recorder does not call back into the session.

**Rework.**

1. DngRecordingQueue::enqueueCopy(PendingCopy copy, std::function<void()> release); PendingCopy drops its Request* member.
2. recordRawFrame builds the closure '[this, request]{ if (!running_.load()) return; requeueRequest(request); }' and passes it.
3. Pass the hold limit (buffers - 2) to startAtFolder as an argument.
4. Delete setRequestRelease, setFrameQueued, releaseRequest_, frameQueued_.
5. Audio: call observeVideoFrame on the completion thread after enqueueCopy accepts, as ProRes does (:7428-7430@upstream-1.6.0).
6. Keep the shared_lock on sessionSettingsMutex_ only if the closure needs it, with a one-line reason; the ProRes closure takes none.

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests (lc build compiles the session); tools/frame_path_test.cpp still passes.

**Needs the Pi.** 4K Clear HDR 16-bit and 4K 12-bit SDR takes of 60 s: stop stats line shows no drop[copy-slot], no new gaps; stop during a take returns all buffers (no 'request not returned' in the log).

**Risk.** Release order at stop: the closure must no-op once running_ is false.

## CAM-6. Storage pre-roll writes fps after the sanitiser and re-pins FrameDurationLimits on every request

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | fix-now | CC-4-F3 |

**Where.** `src/camera/CameraController.cpp:7574-7576, :7505@cinemate-port`; `CC:7839-7897@cinemate-port`; `CC:9074-9079@cinemate-port`; `CC:12040-12110@cinemate-port`; `CC:3486-3491@cinemate-port`

**Problem.** applyControls sanitises and then sets 'sanitized.fps = prerollFps' past the lossless and ladder caps. requeueRequest sets a second FrameDurationLimits {p, p} from prerollPinUs_ on every request, which also overrides the phase-lock pin. startStoragePreroll waits up to 1 s under mutex_. During a pre-roll settings_ no longer holds what the sanitiser allowed. The automatic trigger (APP-2) and the App worker (APP-12) are in the core-app list.

**Apertar way.** Limits come only from the sanitise chain and the effective values are read back (CC:2707-2744, :8713-8715@upstream-1.6.0). controlsForSettings pins video to {d, d} (CC:2022-2031@upstream-1.6.0); the only per-request override is the bracket shot (CC:6515-6530@upstream-1.6.0). rule CAM-8, rule CAM-9.

**Rework.**

1. The pre-roll runs at maximumFpsForSettings(settings, sensorFamily) through the normal setter path: copy settings_, set fps, applySettingsLocked(next, false), restore after. No override after the sanitiser.
2. Suspend the phase lock while the pre-roll runs, so controlsForSettings alone sets {d, d}.
3. Delete prerollFpsOverride_, prerollPinUs_, setPrerollFps, the override in applyControls (CC:7574-7576), the pin in requeueRequest (CC:9074-9079) and the reset at CC:7505.
4. Keep the frame and timestamp measurement (prerollMeasuring_, prerollFrames_, first/last).
5. Do not hold mutex_ across waitForFramePeriod; take it for the apply, release, wait, take it for the restore.
6. Answer 'sensor maximum': add a pre-roll flag to the settings passed to sanitizeSettingsForSensor that uses prerollMaximumFps as the ceiling; the rest stays as above.

**Owner decision.** Pre-roll at the recordable maximum (maximumFpsForSettings, what a take can reach) or at the sensor maximum past the lossless and ladder caps? Recommend the recordable maximum: no new flag, the sanitiser keeps the last word; cost: the pre-roll writes a little less on lossless modes. The sensor maximum costs a pre-roll input to the sanitiser.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; --simulate: storage_preroll then get_state: fps equals the value before; /home/user/build/bin/smoke_core.sh /home/user/build/core-work-nolc/apertar-core 8011 before and after, diff.

**Needs the Pi.** storage_preroll on a CM5 at 4K lossless and 4K uncompressed: journal 'preroll' line shows frames and fps; a take straight after has fps as set.

**Risk.** Pre-roll results change; the owner compares against earlier runs.

**Depends on.** CAM-2

## CAM-7. Raw buffer and request count: kActiveRequestCount gone, a process-global media root, three evaluations per configure, no board cap

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | ask-owner | CC-1-F3, CC-1-F2, CC-4-F9, CC-5-F10, X-board-support-7 |

**Where.** `src/camera/CameraController.cpp:1334-1338, :1456-1471@cinemate-port`; `CC:8379-8381, :8736, :8846-8848@cinemate-port`; `CC:10543@cinemate-port`; `src/util/MediaProfile.hpp:126-150, :214-234@cinemate-port`; `src/cdng/CdngEncoder.cpp:91@cinemate-port`

**Problem.** Every raw take now runs one request per buffer (4/4 SDR, 8/8 Clear HDR = 135 MB at 4K 16-bit); upstream keeps one buffer out of the queue. rawCameraBufferCount reads the env var, the media tune file and a per-filesystem extra through configuredMediaRoot(), a mutable global written by CameraController::start, and is evaluated three times per configure (buffers, requests, hold limit), so a mount event between calls gives different numbers. The comment says exFAT gets +2, the table gives 0 (MediaProfile.hpp:142). Clear HDR is not gated by board (RecordingCapabilities.hpp:66-81). Only 4K Clear HDR 16-bit on a CM5 was measured (db17860).

**Apertar way.** kConfiguredBufferCount = 4, kActiveRequestCount = 3 (CC:1023-1024@upstream-1.6.0), used at CC:6460-6461@upstream-1.6.0. h264CameraBufferCount / proresCameraBufferCount are one unsignedEnvValue line each, the H.264 default picked by board (CC:1124-1134@upstream-1.6.0). The media root is a member passed as an argument (start(const std::string &mediaRoot, ...) CC:3268@upstream-1.6.0); function-local statics only for one-off process values (rule CAM-27).

**Rework.**

1. CameraSession::configureAndStart computes the count once into a member rawBufferCount_; makeRequests (CC:8381, :8848) and the hold limit (CC:8736) read it.
2. rawCameraBufferCount(bool clearHdr, const std::string &mediaRoot); pass mediaRoot_ through CameraSession::start/reconfigure. Delete configuredMediaRoot() and its writer at CC:10543; the encoder gets its media settings at construction (CdngEncoder.cpp:91).
3. If APP-14 removes MediaTune, the function shrinks to 'return unsignedEnvValue("APERTAR_RAW_CAMERA_BUFFERS", clearHdr ? kClearHdrBufferCount : kConfiguredBufferCount, 3, 16);' like CC:1124-1134@upstream-1.6.0. Keep a filesystem extra only if measured.
4. Requests: SDR raw takes go back to kActiveRequestCount = 3 of 4 buffers; Clear HDR keeps 8 of 8 (measured). One-line comment without a board name.
5. Fix or delete the exFAT +2 comment; MediaWriterSettings::directIo goes with the media editor's list.

**Owner decision.** Keep one request per buffer in SDR raw takes (measured only in 4K Clear HDR 16-bit on a CM5) or go back to upstream's 3 requests of 4 buffers there? Recommend upstream's 3 of 4 for SDR, 8 of 8 for Clear HDR: SDR behaves as 1.6.0 on every board; cost: none known. Keeping 4 of 4 needs one SDR measurement and a line for the original developer.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; grep -n configuredMediaRoot src returns nothing.

**Needs the Pi.** CM5: 60 s 4K 12-bit SDR and 4K Clear HDR 16-bit, stop stats unchanged against the port. Pi 4: Clear HDR 4K start, dmesg shows no CMA allocation failure (settles CC-4-F9's open point).

**Risk.** SDR drop behaviour may differ from the port's last runs.

## CAM-8. Mode ladder persists in its own mode_ladder.conf, with a copied path function

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | major | M | yes | ask-owner | Camera-headers-F5, CC-1-F5, X-knobs-14 |

**Where.** `src/camera/ModeLadder.hpp:316-342@cinemate-port`; `src/camera/CameraController.cpp:403-415@cinemate-port`; `CC:10508-10514, :10939-10945, :11096@cinemate-port`; `src/camera/CameraController.hpp:248@cinemate-port`

**Problem.** A second Core-written camera file, ~/.config/apertar-core/mode_ladder.conf (enabled, ramp_ready, resolutions, the legacy rungs key), with its own parser and writer (ladder::fileText / parseFile), held in modeLadder_ outside CaptureSettings and written synchronously by setModeLadder. modeLadderPath() is a line-for-line copy of persistedSettingsPath(). The header it writes carries '(T34)'. The sweeps disagree: Camera-headers keeps it a major mismatch, knobs calls a file per concern acceptable.

**Apertar way.** Camera settings live in camera_settings.conf as key=value, written only by the debounced persister (CC:742-889@upstream-1.6.0); camera-wide keys are carried across format profiles like tuning_file (CC:7939-7955@upstream-1.6.0; rule CAM-25, rule CAM-40, recipe R2). The port already does this for preview_tdn, cdng_log and clip_name_template (CC:11338-11372@cinemate-port). Upstream keeps one file per owner process, not per feature (UI.conf, camera_settings.conf, apertar-hardware.conf).

**Rework.**

1. Answer fold-in (recommended): add CaptureSettings fields modeLadderEnabled, modeLadderRampReady, modeLadderResolutions (the existing comma text) with member initialisers.
2. Load them in the else-if chain (CC:817-900) and write them in the writer (CC:936-989) as mode_ladder_enabled=0/1, mode_ladder_ramp_ready=0/1, mode_ladder_resolutions=<text>; carry them across formats in the block at CC:11338-11372.
3. setModeLadder commits through applySettingsLocked like any setter, so the persister writes it.
4. On start, if camera_settings.conf has no mode_ladder_ key and mode_ladder.conf exists, read it once and persist; then never read it again.
5. Delete fileText, modeLadderPath, saveModeLadderLocked, the rungs key and parseFile once the migration line is in.
6. Answer keep-file: replace modeLadderPath() by persistedSettingsPath().parent_path() / "mode_ladder.conf", drop T34 from the written header, and document the file in the README beside camera_settings.conf.

**Owner decision.** Fold the ladder into camera_settings.conf (recommended: one camera settings file, the persister covers it, R2 recipe; cost: a one-time migration read of the owner's mode_ladder.conf) or keep the separate file (cost: the original developer learns a second camera settings file with its own writer; only the path copy and T34 get fixed)?

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; host: tools for ModeLadder pass; --simulate: set_mode_ladder resolutions=... then restart Core: get_mode_ladder returns the same; camera_settings.conf holds mode_ladder_ keys.

**Needs the Pi.** Owner's camera: after the update get_mode_ladder equals the old mode_ladder.conf; the file is no longer rewritten.

**Risk.** The owner's live ladder must survive the migration.

**Depends on.** CAM-20

## CAM-9. Camera bench knobs: restore switches, never-set gains and an RT priority knob measured with no effect

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| knob | major | S | yes | fix-now | X-knobs-9, Camera-headers-F11, CC-4-F11 |

**Where.** `src/camera/CameraController.cpp:3112-3127, :3393, :3401@cinemate-port`; `CC:8909-8922@cinemate-port`; `CC:9109-9133@cinemate-port`; `src/camera/Imx585Modes.hpp:105-114@cinemate-port`; `src/camera/FpsCeiling.hpp:29-38@cinemate-port`

**Problem.** The camera side adds APERTAR_FPS_LIMIT, APERTAR_LOSSLESS_FPS_LIMIT, APERTAR_IMX283_PROBE_FPS and APERTAR_IMX585_MIN_MODE_WIDTH (switches back to upstream behaviour or constants nobody set), APERTAR_PHASE_LOCK_KP/KI/DEADBAND_US/CLAMP_US (never set) and APERTAR_RT_CAPTURE_PRIORITY (measured: no effect, lessons/hardware-log.md:954; needs LimitRTPRIO). They use three parsers (getenv/strtoll in a default argument read on every lookup, strtod, a lambda) beside upstream's helpers. The App side, the start script and LimitRTPRIO are APP-9 and APP-15.

**Apertar way.** A bench knob is APERTAR_<AREA>_<KNOB> read at the point of use with unsignedEnvValue / boolEnvValue (CC:1027-1061@upstream-1.6.0), printed in the take-start line, not in the README (rule CAM-24, recipe R8). Per-thread nice -5 on the callback thread (CC:6589-6600@upstream-1.6.0).

**Rework.**

1. APERTAR_FPS_LIMIT and APERTAR_LOSSLESS_FPS_LIMIT go with CAM-2; APERTAR_IMX283_PROBE_FPS with CAM-10.
2. Imx585Modes.hpp: minModeWidth() becomes 'inline constexpr uint32_t kMinModeWidth = 1280;'; drop the default argument that reads the environment (or follow CAM-27's answer).
3. CC:8909-8922: delete the four phase-lock gain reads; FramePhaseLock.hpp keeps its defaults as constants.
4. CC:9109-9133: delete the APERTAR_RT_CAPTURE_PRIORITY block; keep upstream's nice -5 (APP-15 step 3, one commit).
5. Keep as developer-only, upstream form: APERTAR_RAW_CAMERA_BUFFERS, APERTAR_FPS_RAMP_GRACE_FRAMES, APERTAR_PHASE_LOCK_LOG. Not in the README (APP-18).

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; grep -n 'getenv("APERTAR' src/camera shows only the kept names; README has no camera APERTAR_ row.

**Needs the Pi.** None beyond a start: journalctl shows no ignored-knob lines.

**Risk.** A campaign script that set these variables loses them.

**Depends on.** CAM-2, CAM-10

## CAM-10. IMX283 driver turns on unmeasured per-crop VMAX floors by default; Core caps them away again

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| knob | major | S | yes | fix-now | Driver-imx283-F2, X-knobs-17 |

**Where.** `imx283-v4l2-driver imx283.c:271-281, :2428-2433@cinemate-port`; `imx283-v4l2-driver APERTAR.md:92-113@cinemate-port`; `Core src/camera/CameraController.cpp:3332-3337, :3388-3395@cinemate-port`; `src/camera/Imx283Modes.hpp:138@cinemate-port`

**Problem.** 'static bool crop_vmax = true;' turns on floors the driver itself calls 'experimental, UNMEASURED' (confirmed). APERTAR.md tells Apertar users to add a modprobe.d file with crop_vmax=0, which setup.sh and dkms.postinst do not install. Core then caps fps at the crop_vmax=0 floor table unless APERTAR_IMX283_PROBE_FPS=1. Any other libcamera app on a stock install runs the unmeasured floors (about 35 fps on the 2.55:1 Mode-0 row).

**Apertar way.** No IMX283 in 1.6.0. The same driver makes its other unvalidated feature opt-in: 'static bool experimental_modes;' default off (imx283.c:269). Core caps with min(table, probe) (CC:2763-2770@main).

**Rework.**

1. imx283.c: 'static bool crop_vmax;' (default off), or delete crop_vmax, crop_min_VMAX and the _crop_vmax macro argument until the floors are measured (preferred; it also simplifies CAM-39).
2. Fix MODULE_PARM_DESC(crop_vmax): no development/ path.
3. APERTAR.md: drop the modprobe.d instruction.
4. Core: delete imx283ProbeFpsOnly() and its use in maximumSupportedFpsForResolution; the crop_vmax=0 floor stays as the IMX283 table row and CAM-2's min(table, probe) applies as for every sensor.

**Owner decision.** None.

**Check here.** Read the driver diff; /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; tools/imx283_modes_test.cpp passes.

**Needs the Pi.** modinfo imx283 shows crop_vmax default 0 (or no parameter); cat /sys/module/imx283/parameters/crop_vmax = N; Core fps_max on the 2.55:1 row equals the table floor.

**Risk.** None for Apertar; the experiment needs an explicit module parameter.

## CAM-11. Ticket numbers, Cinemate history, KB paths, dates and banners in Core camera comments and in a written file

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | major | M | no | fix-later | CC-1-F7, CC-4-F5, CC-5-F11, Camera-headers-F12 |

**Where.** `src/camera/CameraController.cpp:403, :441-445, :1108, :1461-1463, :1660, :8167, :8902, :8907, :9063-9068, :9112, :9451, :9742, :9931, :10726, :10823, :10900, :12039@cinemate-port`; `include/apertar/core/Types.hpp:141, :181-189@cinemate-port`; `src/camera/CameraController.hpp:102, :180, :243, :248@cinemate-port`; `src/camera/ModeLadder.hpp:1, :319@cinemate-port`; `src/camera/FramePhaseLock.hpp:9-26, :48@cinemate-port`; `src/camera/Imx283Modes.hpp:1-2; Imx585Modes.hpp:3, :16@cinemate-port`

**Problem.** About 30 comment lines in CC and more in the headers carry T23/T28/T29/T31/T34, 'request 19', 'decision 9', 'Cinemate ff59dd8', 'as on Cinemate's libcamera', 'qbc libcamera', 'hardware-log 2026-10-26', '(kb working/dng-chain, V/H15)', 'CineMate Log', branch names and four '// ----' banners. ModeLadder fileText writes '# Apertar mode ladder (T34).' into the user's file. FramePhaseLock's Decision::pushDuration says {d, d} while the controller pins {d, d+1} (CC:9069).

**Apertar way.** STY-8 and STY-9: comments are rare one- to three-line statements of a constraint; no ticket numbers, other projects' hashes, authors, dates or banners (0 '// ----' in CC@upstream-1.6.0; example CC:6927-6928@upstream-1.6.0).

**Rework.**

1. Run: grep -nE 'T[0-9]{2}\b|request [0-9]+|decision [0-9]+|[Cc]ine[Mm]ate|qbc|hardware-log|[Kk][Bb] working|cinemate-port|// ----' src/camera include/apertar/core.
2. For each hit keep the constraint as one line of why and drop the reference. Example CC:9063-9068: 'A range, not a single value: a single-value pin makes the IMX585 helper re-choose the line length, which steps the exposure.'
3. Name the feature 'Log' as the cdng_log key does.
4. Delete the four banners and the 'T34' in the written ladder header (moot if CAM-8 folds the file).
5. FramePhaseLock.hpp: {d, d} -> {d, d+1}; move the overview comment above struct FramePhaseLock.
6. Imx283Modes.hpp / Imx585Modes.hpp provenance: the driver commit, not the branch name (CAM-22).

**Owner decision.** None.

**Check here.** The grep above returns nothing in src/camera and include/; /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests

**Needs the Pi.** Nothing.

**Risk.** Comment-only.

## CAM-12. Driver comments and docs: work-package history, 'Experimental' on shipping modes, absent files, stale lines, Cinemate sections

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | major | M | no | fix-later | Driver-imx585-F2, Driver-imx585-F9, Driver-imx283-F1, Driver-imx283-F10, Driver-imx283-F14 |

**Where.** `imx585.c:767-1000, :1086, :1121, :2120-2124, :2950, :3026, :3063-3090@cinemate-port`; `imx585 README.md:37, :148-270; APERTAR.md:9-15@cinemate-port`; `imx283.c:26-30, :61, :262, :281, :420-444, :678, :724-737, :752-802, :924, :1023-1035, :2387-2417, :3354@cinemate-port`; `imx283 EXPERIMENTAL_CROPS.md; APERTAR.md:7-14; README.md:32@cinemate-port`

**Problem.** imx585.c: 54 WP-585 references, 65 'experimental' lines, a 90-line history block citing INVESTIGATION.md, RESULTS.md, WORK-PACKAGES.md, D1, DEC-1/2, G1-G4 (none in the repo), and three stale comments (a '1280x760' mode that does not exist; 'everything below 1440 moved' above 2x2 960/1024 entries; mono Y10 '4K 10-bit' while all 62 modes return). imx283.c: 1116 comment lines (base 198), 37 lines with WP-283/DEC-4/REBUILD/ROUND2/GAP/development refs, including MODULE_PARM_DESC(crop_vmax); the file lost its final newline. READMEs clone the fork's cinemate-port branch and carry a 120-line CineMate layer section; EXPERIMENTAL_CROPS.md is marked STALE but shipped.

**Apertar way.** Baseline imx585 per-mode one-liners ('1.85:1 2x2 binned, full-width RAW12 crop', imx585.c:815@origin/apertar) and short routing comments (imx585.c:1384-1387@origin/apertar); the driver author's long comments (70bdb26) explain hardware, not process. Baseline imx283 has 198 comment lines. STY-9.

**Rework.**

1. imx585.c: replace the history block with a ~20-line invariant block (table order, the three get_mode_table ranges, the RAW16 OB-row rule, crop in sensor coordinates); one comment line per entry (ratio, binning); strip WP/D/DEC/G ids and absent file names; fix the three stale comments.
2. imx283.c: cut each block to what it does plus one non-obvious why; move the measurement history (2704 vs 2736 columns, 236/924, 784/852) to the KB hardware log; delete every WP/DEC/REBUILD/ROUND2/GAP/development reference including MODULE_PARM_DESC(crop_vmax); restore the final newline.
3. imx585 README: delete the CineMate layer table and the seven-mode matrix; keep the blend table, the HMAX floor and link-rate notes. Move hardware findings (windowed 2x2 RAW16 = pedestal, mono binned HDR = pedestal) to APERTAR.md 'Validation'.
4. imx283: delete EXPERIMENTAL_CROPS.md and its mentions (APERTAR.md:7-8, MODULE_PARM_DESC(experimental_modes), imx283.c:257); trim APERTAR.md to install, config.txt, modprobe, modes and open questions.
5. Both READMEs and APERTAR.md: clone URL and branch name of the merge target, set at merge time.

**Owner decision.** None.

**Check here.** grep -cE 'WP-|DEC-|REBUILD|ROUND2|GAP\.md|development/|INVESTIGATION|[Cc]ine[Mm]ate' imx585.c imx283.c README.md APERTAR.md returns 0 (CineMate may stay only where CAM-42 documents the geometry controls); tail -c1 imx283.c is a newline.

**Needs the Pi.** Nothing.

**Risk.** Comment-only; keep any line that states a register constraint.

## CAM-13. Speed ramp: a mid-ramp FPS can be saved as the operator's FPS; the keep-exposure shutter leaks into another format's profile

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-now | CC-5-F2, CC-5-F3 |

**Where.** `src/camera/CameraController.cpp:10751-10755, :10777-10780, :10812-10815@cinemate-port`; `CC:11356@cinemate-port`; `CC:12795@cinemate-port`

**Problem.** Ramp steps apply with commit=false, but any other setter during the take (set_iso, set_wb) commits through persistSettingsLocked and writes the current mid-ramp fps; a crash or power loss in the take leaves that fps on disk. rampNominalShutterUs_ is set at the first step and not reset when setRecordingFormat loads a saved profile, so a later set_fps overwrites that profile's shutter (e.g. a cDNG 20000 us nominal lands in an MLV 10000 us profile).

**Apertar way.** The commit flag conforms: applySettingsLocked(..., bool commit = true) (CameraController.hpp:92@upstream-1.6.0); applyCapturePreset passes false and persists/emits after (CC:8627-8638@upstream-1.6.0). Each format remembers its own settings (rule CAM-40).

**Rework.**

1. persistSettingsLocked: while recording_ && rampTakeChanged_, write rampTakeBaseFps_ as fps. Then delete the 'write once more' branch in restoreFpsAfterRampLocked.
2. setRecordingFormat: 'rampNominalShutterUs_ = 0;' where the saved profile is loaded (next = saved->second, CC:11356). Better: make the nominal take-scoped (set in the take, cleared in restoreFpsAfterRampLocked).

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; --simulate: set_fps_speed_ramp on, record_start, set_fps 30, set_iso 1600, read camera_settings.conf: fps is the take's start rate. Format case: as in the problem, then get_state shutter_us for mlv is 10000.

**Needs the Pi.** One ramp take with a dial sweep and an ISO change, then kill -9 apertar-core: camera_settings.conf fps is the start rate.

**Risk.** Low.

## CAM-14. Lossless ISO cap raised to 1600 on every sensor; auto ISO kept in IMX585 lossless with any tuning

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| stock | minor | S | yes | fix-now | X-stock-behaviour-9, X-stock-behaviour-10 |

**Where.** `src/camera/CameraController.cpp:3097-3100@cinemate-port`; `CC:3146-3170@cinemate-port`

**Problem.** kLosslessMaxIso = 1600 applies to every lossless mode, including IMX477 4K/2K (confirmed), measured on the IMX585 only. enforceLosslessCaptureLimits keeps isoAuto on the IMX585 because the default tuning's AGC stops at gain 8; a user-picked tuning is unchecked ('Unverified', b5b787e). The touch UI and WebUI offering Auto everywhere is the UI and WCP editors' half (UI-camera-qml-F11).

**Apertar way.** 'settings.iso = std::min<uint32_t>(settings.iso, 800u)' and manual ISO forced in lossless on every sensor (CC:2483-2484@upstream-1.6.0). Sensor quirks are per SensorFamily in the sanitiser (rule CAM-11, recipe R5 step 5).

**Rework.**

1. constexpr uint32_t kLosslessMaxIso = 800; constexpr uint32_t kImx585LosslessMaxIso = 1600; a free helper losslessMaxIso(SensorFamily) used in enforceLosslessCaptureLimits and maximumIsoForSettings.
2. Keep auto ISO in IMX585 lossless only when settings.tuningFile.empty(); otherwise settings.isoAuto = false as upstream.
3. Comment: one line of why, no name or temp commit.

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; --simulate does not emulate a sensor family, so check losslessMaxIso by reading.

**Needs the Pi.** IMX477 4K lossless: set_iso 1600 replies 800. IMX585 lossless with a picked tuning: iso_auto false after set_tuning_file.

**Risk.** None for stock.

## CAM-15. Clear HDR ISO caps read from a [camera] section of apertar-hardware.conf by the camera controller

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | yes | fix-now | X-knobs-13 |

**Where.** `src/camera/CameraController.cpp:2933-2981@cinemate-port`; `src/ApertarCoreApp.cpp:5074-5079@cinemate-port`

**Problem.** loadCameraSection parses apertar-hardware.conf (four candidate paths, its own parser) for clear_hdr_iso_max_12bit / _16bit, read once, with no command and no UI. The values come from the driver's gain codes (720, 1585). Port-new: not on fork main.

**Apertar way.** rule CAM-19 (always): the camera side never reads apertar-hardware.conf; limits are constants in the sanitiser ('settings.iso = std::min<uint32_t>(settings.iso, 800u)', CC:2483@upstream-1.6.0).

**Rework.**

1. Add constexpr uint32_t kClearHdrMaxIso12 = 720 and kClearHdrMaxIso16 = 1585 beside kLosslessMaxIso, with the two-line gain-code why.
2. clearHdrIsoCap uses them. Delete CameraSection and loadCameraSection.
3. Delete the [camera] lines in defaultHardwareConfigTemplate (App:5074-5079) and any [camera] entry in the hwconf key tables (hardware editor's list).

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; grep -n 'loadCameraSection\|\[camera\]' src returns nothing.

**Needs the Pi.** Clear HDR 12-bit: get_state iso_max 720; 16-bit: 1585.

**Risk.** A rig that set the keys loses them (none recorded).

## CAM-16. Ladder and clip-name methods return errors and data through out-parameters

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | unknown | fix-now | CC-5-F5, Camera-headers-F7 |

**Where.** `src/camera/CameraController.hpp:92, :102-109@cinemate-port`; `src/camera/CameraController.cpp:11045-11102, :11835-11856@cinemate-port`; `src/ApertarCoreApp.cpp:14093-14107@cinemate-port`

**Problem.** bool setModeLadder(optional rungs, optional enabled, optional rampReady, bool dryRun, std::string *json, std::string *error) writes errors to *error and never sets lastError_; applyLadderToPreset(..., std::string *error) const and previewClipName(value, std::string *example, std::string *error) const do the same; setClipNameTemplate(value, std::string *stored) has a redundant out-parameter. App needs a special reply path.

**Apertar way.** rule CAM-7: bool setters plus setErrorLocked("..."); return false; and lastError(); App replies settingsBody(camera_.settings()) or camera_.lastError() (App:9242-9249@upstream-1.6.0). Read-only data has its own getter (sensorModes()). CameraController.hpp@upstream-1.6.0 has no std::string *error parameter.

**Rework.**

1. bool setModeLadder(const std::string &resolutions, bool enabled, bool rampReady) with setErrorLocked; multiple validation errors joined into one sentence.
2. Dry run: std::string modeLadderPreviewJson(const std::string &resolutions, bool enabled, bool rampReady) const; App calls it for dry_run and replies with it.
3. After a successful set App replies with modeLadderJson() plus settingsBody.
4. previewClipName and applyLadderToPreset: return std::optional<std::string>; the error goes to a mutable lastError_ under the lock, or the functions become non-const.
5. setClipNameTemplate(const std::string &value): App reads camera_.settings().clipNameTemplate (APP-38 removes the App-side parse; one commit).

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; /home/user/build/bin/smoke_core.sh /home/user/build/core-work-nolc/apertar-core 8011 before/after: set_mode_ladder and preview_clip_name replies keep their shape; an invalid ladder answers with error and get_state last error.

**Needs the Pi.** Nothing.

**Risk.** The WebUI ladder editor reads the dry-run reply; keep its fields.

**Depends on.** CAM-8

## CAM-17. ladder_text: Core composes a UTF-8 display line; ladderCount repeats ladder_tops

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | fix-now | CC-1-F9, Camera-headers-F9 |

**Where.** `include/apertar/core/Types.hpp:181-189@cinemate-port`; `src/camera/CameraController.cpp:185, :10911-10935@cinemate-port`; `WCP:8392, :8421, :13911, :15920@cinemate-port`

**Problem.** The settings event carries 'Resolution 1 · 3840×2160 · ClearHDR16 · ≤25 · Uncompressed' with non-ASCII glyphs; only the WebUI reads it. ladderCount equals ladder_tops.size(). Each field is kept in three hand-written serialisers.

**Apertar way.** Upstream's settings event carries values only (CC:136-187@upstream-1.6.0); each client formats them (rule CAM-11 'each layer keeps its own tables'). Runtime state in CaptureSettings is fine (Types.hpp:139-150@upstream-1.6.0); display sentences are not.

**Rework.**

1. Delete ladderText and ladderCount from Types.hpp, the CC writer (CC:185, :10911-10935) and both App serialisers.
2. WebUI builds the line from ladder_rung, ladder_tops and the get_mode_ladder reply it already holds (WCP editor).
3. Keep the other ladder runtime fields.

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; /home/user/build/bin/smoke_core.sh /home/user/build/core-work-nolc/apertar-core 8011 diff shows only ladder_text and ladder_count gone; browser on --simulate: the ladder line still shows.

**Needs the Pi.** Nothing.

**Risk.** The WebUI must land the same commit.

## CAM-18. conform_fps: persisted, settable, published and in presets, with no reader and no control

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | minor | S | yes | fix-now | CC-1-F6, Camera-headers-F13, X-knobs-12, X-state-consistency-9 |

**Where.** `include/apertar/core/Types.hpp:135-137@cinemate-port`; `src/camera/CameraController.cpp:172, :696-697, :817-818, :942, :11354-11364, :11806-11812@cinemate-port`; `src/ApertarCoreApp.cpp:320, :7851, :9484, :13270, :14353-14357@cinemate-port`; `WCP:19111@cinemate-port`

**Problem.** A CaptureSettings field 'nothing derives from it yet' (Types.hpp:135-137), a persisted key, a clamp with the literal 25.0, a carry across formats, set_conform_fps, state keys and the preset key cameraConformFps. No reader in src, no control in either UI; a preset can change it unseen.

**Apertar way.** Every upstream setting drives behaviour; recipe R2 adds a setting together with its consumer. Defaults come from CaptureSettings{}.field (rule CAM-25).

**Rework.**

1. Delete the field, its load/save lines, the clamp, the carry, setConformFps, the App command and its help entry, both state keys, the preset writer/reader key and the WCP allow-list entry.
2. App half is in APP-34; one commit.

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; grep -rn 'conform' src include returns nothing; /home/user/build/bin/smoke_core.sh /home/user/build/core-work-nolc/apertar-core 8011 diff shows only conform_fps gone.

**Needs the Pi.** Nothing.

**Risk.** Old settings files keep a conform_fps= line, which the loader ignores.

## CAM-19. Ladder editor ignores recording_capabilities: every compression reads usable on a board without raw compression

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| board | minor | S | unknown | fix-now | X-board-support-9 |

**Where.** `src/camera/CameraController.cpp:10838-10843, :10949-10958@cinemate-port`; `src/camera/ModeLadder.hpp:41-44@cinemate-port`; `WCP:8155-8166@cinemate-port`

**Problem.** fillRungExtrasLocked probes each compression through sanitizeSettingsForSensor, which clamps the compression, then compares only fps, bit depth and Clear HDR. On a Pi 4 every compression reads usable with the uncompressed ceiling; the SDR default is lossless_jpeg, so the card shows Lossless JPEG and records uncompressed with no sentence. Pi 3 / Zero 2 W get raw-only cards.

**Apertar way.** Board capability decided once in RecordingCapabilities, enforced at setter, sanitise and start; UIs hide what the board cannot do (rule CAM-13; WCP:9524-9529@upstream-1.6.0). No silent downgrade (rule CAM-36).

**Rework.**

1. fillRungExtrasLocked: if !recordingCapabilities().rawCompression, set state.ceilingBy[1..3] = 0.
2. The default rung compression is none on such a board (where ModeLadder defaults are applied).
3. WebUI hides the ladder card when raw_recording is false (WCP editor, WCP:9488-9496 pattern).

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; --simulate reports Pi 5 capabilities, so check by code reading or a unit call with RecordingCapabilities{}.

**Needs the Pi.** Pi 4: get_mode_ladder shows ceiling 0 for lossless and lossy.

**Risk.** Low.

## CAM-20. Six new booleans written as true/false in camera_settings.conf

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | no | fix-now | CC-1-F4, X-knobs-19 |

**Where.** `src/camera/CameraController.cpp:885-898, :974-980@cinemate-port`

**Problem.** fps_phase_lock, preview_tdn, media_trim, fps_speed_ramp, fps_speed_ramp_keep_exposure and fps_speed_ramp_stretch_audio are written 'true'/'false' and read by string compare; media_trim reads anything but false/0 as true; fps_speed_ramp_after is 'return'/'stay' over a bool. The port's own iso_auto_after_clear_hdr uses 0/1 (CC:945).

**Apertar way.** 'output << prefix << "iso_auto=" << s.isoAuto' writes 0/1 (CC:749@upstream-1.6.0); 'settings.isoAuto = std::stoul(value) != 0' (CC:659-660@upstream-1.6.0) inside the try (rule CAM-25).

**Rework.**

1. Writer: '<< s.field' for the six booleans; fps_speed_ramp_return=0/1 replaces fps_speed_ramp_after.
2. Reader: std::stoul(value) != 0, and also accept 'true'/'false' and the old fps_speed_ramp_after key, because the owner's file has them (retired keys are still read, CAM-25).
3. media_trim uses the same rule as the others.

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; --simulate: toggle each switch, restart, values survive; an old file with true/false loads.

**Needs the Pi.** Nothing.

**Risk.** Low.

## CAM-21. Speed ramp writes a journal line per set_fps and per transition; the refusal names a socket command

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | yes | fix-now | CC-5-F8, CC-5-F12 |

**Where.** `src/camera/CameraController.cpp:10772-10775, :9847-9850@cinemate-port`; `CC:10691-10697@cinemate-port`

**Problem.** Every set_fps in a ramp take logs 'fps ramp: a -> b fps shutter_us= policy='; every applied transition logs a frame/delta/lag line, so a dial sweep floods the journal with data already in fps-ramp.txt and the stop stats line. The refusal 'Stop recording before changing FPS, or enable FPS ramping (set_fps_speed_ramp) for cDNG/MLV takes.' comes before the format check, so an H.264 operator is told to enable a feature H.264 cannot use.

**Apertar way.** rule CAM-23: no line per setter call or control change; take start and stop lines; repeats rate-limited by n == 1 || n % N == 0. STY-10: sentences without identifiers; 'Stop recording before changing FPS so video and audio keep the same timeline.' (CC:7744@upstream-1.6.0).

**Rework.**

1. Delete the setter line at CC:10772-10775.
2. Rate-limit the transition line with 'n == 1 || n % 30 == 0', or print it only with APERTAR_PHASE_LOCK_LOG.
3. setFps: check the format first; keep the upstream sentence for processed formats and when ramp is off; for cDNG/MLV with ramp off: 'Stop recording before changing FPS, or turn on Speed Ramp.'

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; --simulate h264 take: set_fps reply carries the upstream sentence.

**Needs the Pi.** One ramp take with a sweep: journalctl lines for the take fit on one screen.

**Risk.** The lag_frames tuning data moves to the rate-limited line.

## CAM-22. Core mirrors the driver mode tables by hand; rows the driver refuses vanish without a log line; provenance is a branch name

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | minor | S | yes | fix-now | Driver-imx585-F8, Driver-imx283-F8, Camera-headers-F10, X-state-consistency-3 |

**Where.** `src/camera/Imx585Modes.hpp:3, :34-38, :39-98, :236-252@cinemate-port`; `src/camera/Imx283Modes.hpp:1-2, :19-22, :114-135@cinemate-port`; `src/camera/CameraController.cpp:7158-7189@cinemate-port`

**Problem.** Imx585Modes.hpp holds four constexpr tables 'as the driver lists it' and Imx283Modes.hpp 57 rows, citing 'Tiramisioux/...-v4l2-driver, branch cinemate-port'. The start probe configures each IMX585 row and skips a refused row with a silent continue (CC:7187); a driver size no row covers is never offered and never reported. Each header has its own Size type and its own distance rule (Euclidean vs Manhattan). The WebUI and QML hold further copies (X-state-consistency-3; the QML update is the UI editor's).

**Apertar way.** Hand-coded sensor sizes in Core are the upstream pattern (CC:355-396@upstream-1.6.0; rule CAM-11; kImx477Modes CC:2309-2335@upstream-1.6.0). Fallbacks and configure results are logged (rule CAM-23). Sensor facts use Resolution from Types.hpp.

**Rework.**

1. Probe (CC:7166-7190): collect refused table rows and driver sizes (formats.sizes()) that no row covers; print one 'ApertarCore sensor probe:' line with both lists.
2. Replace the branch names in both headers by the driver commit each table matches; add one line to each driver's APERTAR.md: 'Core's src/camera/Imx*Modes.hpp must change with this table.'
3. Use Resolution in both headers instead of imx283::Size / imx585::Size; one distance rule (Manhattan, as imx585::nearest) for both.
4. In Imx585Modes.hpp name the copies: WCP imx585ClassModes (WCP:8915), CameraPage.qml:418, SettingsPage.qml:161.

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; tools/imx585_modes_test.cpp and imx283_modes_test.cpp pass with Resolution.

**Needs the Pi.** Start on the stock imx585 driver: the probe line lists the port-only rows as refused.

**Risk.** Nearest-mode answers may change where the two rules disagree; the tests show it.

**Depends on.** CAM-1

## CAM-23. Tested scope not stated: sensor paths run on a CM5 only; drivers need kernel 6.12

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| docs | minor | S | yes | fix-now | X-board-support-14, X-board-support-16 |

**Where.** `src/camera/Imx585Modes.hpp:40-98@cinemate-port`; `src/camera/CameraController.cpp:7119-7239, :8295-8296@cinemate-port`; `src/camera/FramePhaseLock.hpp:9-25@cinemate-port`; `imx283-v4l2-driver imx283.c:10; README.md:9@cinemate-port`

**Problem.** The IMX585 tables, Clear HDR buffers (8 x 16.9 MB), the start-up table probe and the phase lock ran on PiSP (CM5) only, while upstream's README lists the IMX585 for Pi 3 and Pi 4 (README.md:143@upstream-1.6.0). imx283 now includes <linux/unaligned.h>, so a 6.6 kernel cannot build it; the Apertar imx585 base already needs 6.12.

**Apertar way.** README states honest limits per board (STY-14; Core/README.md:60-72@upstream-1.6.0); drivers are installed separately (README.md:87@upstream-1.6.0).

**Rework.**

1. Core README, sensor section: one sentence each on what was run on a CM5 only (IMX585 mode tables and probe, Clear HDR buffers, phase lock) and that Pi 4 / Pi 3 are untested for them.
2. Core README, drivers: 'The imx585 and imx283 drivers need kernel 6.12 or later.'
3. Run board-support tests T3-T6 and T8 before claiming more (sweep-board-support.md).

**Owner decision.** None.

**Check here.** Read the README diff.

**Needs the Pi.** T3-T6, T8 of sweep-board-support.md on a Pi 4.

**Risk.** None.

**Depends on.** CAM-1

## CAM-24. imx283: function-local statics shared by all sensor instances

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-now | Driver-imx283-F5 |

**Where.** `imx283.c:1926-1945, :2534-2550@cinemate-port`

**Problem.** get_mode_table builds static filtered tables lazily without a lock, and __imx283_get_pad_crop returns a pointer to 'static struct v4l2_rect output_crop'. With two IMX283 sensors (CM5 cam0 + cam1) concurrent G_SELECTION calls hold different mutexes and write the same static, so one sensor can report the other's crop (probable, not run).

**Apertar way.** The base returned the const tables and &imx283->mode->crop (imx283.c:717-735, :1143-1155@origin/master).

**Rework.**

1. __imx283_get_pad_crop: return &imx283->mode->crop.
2. Keep the const tables; skip .experimental rows where the list is walked (enum_frame_size index mapping, nearest size), or build the filtered copies once in imx283_probe into struct imx283 members.

**Owner decision.** None.

**Check here.** Read the diff; no kernel build here.

**Needs the Pi.** Build with dkms; cam --list-properties on one IMX283 shows the same crop as before.

**Risk.** Low.

## CAM-25. Speed-ramp audio stretch: undeclared rubberband started as a detached double fork of sh -c, default on

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | M | yes | ask-owner | CC-5-F7, CC-4-F7 |

**Where.** `src/camera/CameraController.cpp:9933-10007@cinemate-port`; `CC:9938-9984@cinemate-port`; `include/apertar/core/Types.hpp:149@cinemate-port`

**Problem.** fpsSpeedRampStretchAudio = true. After a ramped take launchAudioStretch builds a shell string (nice, rubberband, mv, rm, echo), double-forks, calls setsid and execl('/bin/sh','sh','-c',...), and nothing waits for the grandchild. rubberband-cli is in no install step, README line or check (git grep hits CC only). On a stock install every ramp take with FPS changes logs a rubberband failure the operator never sees, and the process can outlive a stop or an unmount.

**Apertar way.** External programs run as waited children with an argv: ffmpeg fork+execv (CC:4154-4161@upstream-1.6.0), aplay execvp (src/audio/AudioRecordingSession.cpp:287@upstream-1.6.0), zip (App:6227-6258); shell strings only through popen with the output read (App:1501-1505). Nothing upstream is detached. Worker threads are std::thread members (rule CAM-27). A missing tool gets a sentence (rule CAM-36).

**Rework.**

1. Answer keep-in-Core: launch rubberband with fork + execvp and an argv vector, no shell; a std::thread member waits for the child, then renames and cleans up; stop() joins it.
2. Answer keep-in-Core: setFpsSpeedRampStretchAudio(true) checks for an executable rubberband in PATH and refuses with 'Install rubberband-cli to stretch the sound of ramped takes.'; README install line.
3. Answer move-out: delete launchAudioStretch, pendingAudioStretch_ and the setting; a script reads fps-ramp.txt and the WAV offline.

**Owner decision.** Keep the stretched WAV in Core (fixed as above, default on as you chose in ca7b7c2) or move it to an offline script? Recommend keep in Core with the waited argv launch and the install check: the operator still gets the file; cost: about 60 lines rewritten and a package line. Moving it out costs the in-camera file.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; --simulate ramp take with rubberband absent: set_fps_speed_ramp_stretch_audio true is refused with the sentence.

**Needs the Pi.** Ramp take with sweep: <clip>_stretched.wav appears; ps shows no orphaned sh/rubberband after stop.

**Risk.** Low.

## CAM-26. set_resolution refuses an IMX585 size the current class lacks; upstream sanitises silently

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | yes | ask-owner | CC-5-F6 |

**Where.** `src/camera/CameraController.cpp:10656-10664@cinemate-port`

**Problem.** When apertar::imx585::find(classFor(bits, clearHdr), w, h) fails, setResolution answers '<size> is not a mode of the IMX585 at N-bit.', while bit-depth and Clear HDR changes still map to the nearest row in the sanitiser. Two size policies for one sensor.

**Apertar way.** rule CAM-21: out-of-absolute-range values are refused with a sentence; sensor, board and format limits are applied silently and the effective value is returned. validateResolution rejects only unknown sizes ('Unsupported resolution.', CC:8767@upstream-1.6.0).

**Rework.**

1. Answer sanitise (recommended): delete the refusal; sanitizeSettingsForSensor maps the size to imx585::nearest() of the class as it does for bit depth; the reply carries the effective size.
2. Answer keep: one comment line at the refusal and one handoff line naming it as the IMX585-only rule.

**Owner decision.** Let set_resolution take the nearest IMX585 row silently, like every other limit (recommended; cost: a client that sends a wrong size gets another size back instead of an error), or keep the refusal (cost: an IMX585-only exception to rule CAM-21 the original developer must learn)?

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; host test of the nearest row in imx585_modes_test.

**Needs the Pi.** Nothing.

**Risk.** Low.

## CAM-27. imx585 driver: 960/1024-wide families hidden by Core, and a Clear HDR test module parameter with a CineMate test kit

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | ask-owner | Driver-imx585-F4, Driver-imx585-F5 |

**Where.** `imx585.c enum IMX585_MODE_CROP_BIN_960X540..IMX585_MODE_CROP_BIN_1024X400 and 10-bit twins@cinemate-port`; `imx585.c:1025-1042, :3083-3094, :4678-4680@cinemate-port`; `tools/clearhdr-gate/@cinemate-port`; `Core src/camera/Imx585Modes.hpp:15, :100-114@cinemate-port`

**Problem.** Each SDR table has 11 crops at 960 wide and 10 at 1024 wide (2x2 crops checked on the host only); Core hides widths below 1280 unless APERTAR_IMX585_MIN_MODE_WIDTH is set. clearhdr_windowed_binning (bool, 0444) widens the 12-bit HDR range for a hardware test; tools/clearhdr-gate needs CineMate settings.jsonc and cinepi-raw; APERTAR.md has to tell users not to set it.

**Apertar way.** No precedent: the baseline driver has no module parameters and no tools folder; Core offers what the driver offers (recipe R6 step 1).

**Rework.**

1. Answer drop (recommended): delete the 960/1024 families from both tables and their enum entries; Core's width filter becomes unnecessary (delete kMinModeWidth handling, CAM-9).
2. Answer offer: keep the families and remove Core's width filter so they are offered.
3. Either answer: delete clearhdr_windowed_binning, its probe warning and tools/clearhdr-gate/; the HDR-12 range ends at IMX585_MODE_CROP_1440X1080_HDR12 with its static_assert.

**Owner decision.** Drop the 960/1024-wide crop families from the Apertar driver (recommended: no hidden modes, no Core filter, less table to validate; cost: Cinemate-side use needs its own branch) or offer them in Apertar (cost: 42 unvalidated modes on the menus)?

**Check here.** python3 /home/user/imx585-v4l2-driver/tools/replay_mode_table_audit.py passes; /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests

**Needs the Pi.** Driver load: dmesg has no clearhdr parameter warning; cam -l lists no 960/1024 modes (answer drop).

**Risk.** Cinemate shares this branch today.

## CAM-28. Frame-rate phase lock: keep the servo, cut the socket telemetry and fix its comments

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | keep-and-document | CC-4-F6 |

**Where.** `src/camera/FramePhaseLock.hpp@cinemate-port`; `src/camera/CameraController.cpp:8887-8971, :9054-9070, :8204-8219@cinemate-port`; `src/ApertarCoreApp.cpp:9460-9464@cinemate-port`

**Problem.** A header-only PI servo, stepped per frame on the completion thread, pins {d, d+1} after each merge; off by default. It publishes fps_phase_lock_active, _err_us, _dur_us, _pushes and _saturated in get_state; only the KB test rig reads the last four.

**Apertar way.** No precedent for a frame-rate servo (upstream fps is a static pin in controlsForSettings). The pieces match: pure header logic (StillBracketing.hpp, rule CAM-4), a per-request override after the merge (bracket shot CC:6515-6530@upstream-1.6.0), read-once env (CdngEncoder.cpp:51-65). Frame health leaves Core as booleans (recording_has_dropped_frames, App:7843@upstream-1.6.0).

**Rework.**

1. Keep FramePhaseLock and stepFramePhaseLock.
2. get_state publishes fps_phase_lock_active only; err/dur/pushes/saturated stay in the APERTAR_PHASE_LOCK_LOG trace line.
3. Gains become constants (CAM-9); comments per CAM-11.
4. Handoff: one paragraph on why (sensor crystal drift against the audio clock, 80ddac1) and that it is off by default.

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; /home/user/build/bin/smoke_core.sh /home/user/build/core-work-nolc/apertar-core 8011 diff: four fps_phase_lock_* fields gone.

**Needs the Pi.** Nothing new; the owner's long-take drift check stands.

**Risk.** The KB rig reads the removed fields from the log instead.

**Depends on.** CAM-9, CAM-11

## CAM-29. Deliberate departures from stated upstream intents: tell the original developer

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | keep-and-document | CC-5-F9, CC-4-F10, CC-4-F7, Driver-imx585-F10 |

**Where.** `src/camera/CameraController.cpp:10490-10493, :10050@cinemate-port`; `CC:7813-7814, :4795-4809@cinemate-port`; `CC:9451-9479, :7589-7593, :7801-7807@cinemate-port`; `imx585.c:4641@cinemate-port`

**Problem.** Four changes are worth keeping but go against a sentence upstream states: recording_health adds recording_dropped_frames:N (upstream: one warning per clip, not a counter); stopRecording calls syncfs on the clip folder (upstream: 'Keep this out of the continuous recording path'); with fps_speed_ramp on, DNG frames are numbered by count and fps changes during a take (upstream: index from the sensor timestamp, fps refused in a take); colour 12-bit CCMP Clear HDR is on without the driver author's ccmp overlay parameter (b6a6f5b).

**Apertar way.** rule CAM-33 'Dropped frames are reported once per clip'; src/util/AtomicStillFile.hpp:31-32@upstream-1.6.0; CC:3518-3526 and CC:7745@upstream-1.6.0 ('Stop recording before changing FPS so video and audio keep the same timeline.'); Will Whang's 70bdb26 ccmp gate.

**Rework.**

1. No code change.
2. Handoff notes: one line each with the reason (user asked for the count, 64bbbaa; C0105 lost after a card pull, 4ce382e; speed ramp is opt-in, faa2958; colour CCMP rationale, b6a6f5b).
3. imx585 APERTAR.md names the ccmp departure; agree it with the driver author before the driver merge.

**Owner decision.** None.

**Check here.** Read the handoff text.

**Needs the Pi.** Nothing.

**Risk.** None.

## CAM-30. Camera host tests: four tests in three styles with build lines in comments

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | keep-and-document | Camera-headers-F15 |

**Where.** `tools/fps_ceiling_test.cpp, tools/imx283_modes_test.cpp, tools/imx585_modes_test.cpp, tools/tuning_tdn_strip_test.cpp@cinemate-port`

**Problem.** Each test is built by hand from a comment line, with check(), a CHECK macro or expectStrip. The phase-lock simulator sits in the KB (apertar-kb/working/tools/phase_lock_sim.cpp), not beside the header. All four compile and pass here.

**Apertar way.** No precedent: upstream Core has no tests and no tools/ folder (conventions section 5, STY-12).

**Rework.**

1. Follow the port-wide decision in APP-42 (one tests/ folder, one check helper, an opt-in APERTARCORE_BUILD_TESTS option OFF, one README line).
2. For this domain: delete fps_ceiling_test with CAM-2 and tuning_tdn_strip_test with CAM-4 (or replace by a makePreviewTuning test); bring imx283/imx585 mode tests into that style; move the phase-lock simulator in as a test.

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests

**Needs the Pi.** Nothing.

**Risk.** None.

**Depends on.** CAM-2, CAM-4

## CAM-31. Mode-ladder override: one flag set by setClearHdr and cleared by hand in six setters; lost at restart

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | fix-later | CC-5-F1, CC-5-F4 |

**Where.** `src/camera/CameraController.cpp:10679, :10711, :11084, :11092, :11383, :11593, :11608-11612, :11656-11662, :11943@cinemate-port`; `CC:10508-10514; CameraController.hpp:245-249@cinemate-port`

**Problem.** ladderOverride_ is set in setClearHdr and cleared in setResolution, setFps, setModeLadder, setRecordingFormat, setRawBitDepth (twice) and setFpsSpeedRamp, rolled back in two places; setRawBitDepth keeps it for a 16-bit request because 'the touch UI sends it right after set_clear_hdr'. The flag is not persisted, so after a restart a held Clear HDR mode sits outside the ladder and set_resolution / set_raw_bit_depth are refused until an fps change (probable).

**Apertar way.** Cross-setting rules travel as values through the sanitiser (setFps, CC:7740-7770@upstream-1.6.0); no setter comment refers to another client's next command. Setter gates themselves are upstream shape (rule CAM-7).

**Rework.**

1. Add endLadderOverrideLocked(const CaptureSettings &next) called from applySettingsLocked: clear the override when not recording and next.fps, next.resolution or next.recordingFormat differ from settings_.
2. Keep explicit clears only in setModeLadder and setFpsSpeedRamp; keep the set and rollback in setClearHdr; delete the setRawBitDepth exception and its two writes.
3. At load (after mode_ladder settings are read): derive the override when the Clear HDR mode differs from the rung for fps, or call ladderRewriteLocked once at start.

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; --simulate: ladder on, set_clear_hdr true, restart, set_resolution is accepted.

**Needs the Pi.** Clear HDR toggles from the dial and the touch UI with the ladder on.

**Risk.** Rollback paths in setModeLadder (:11090-11094) and setClearHdr (:11657-11662).

**Depends on.** CAM-8

## CAM-32. IMX585 and IMX283 exact-mode checks repeat the bit-depth and PISP_COMP1 logic

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| duplication | minor | S | no | fix-later | CC-4-F8 |

**Where.** `src/camera/CameraController.cpp:8485-8530, :8531-8560@cinemate-port`

**Problem.** Two blocks each call formatToRawView, each carry the 'Pi 5 turns CSI2P into PISP_COMP1, reports 16 bits' exception and each write their own rejection line.

**Apertar way.** One readout check for three sensors with one condition: 'const bool invalidReadout = sensorFamily_ == SensorFamily::Imx294 ? ... : ...;' (CC:6162-6183@upstream-1.6.0).

**Rework.**

1. Free helper rawModeAdjustment(candidateConfig, rawStreamIndex, rawSize, sensorMode.bitDepth) returning the reason (empty = exact), used by both sensors.
2. The IMX585 ScalerCropMaximum test stays as the one sensor-specific line, binning from the table row.
3. Do it after CAM-1 changes the IMX585 block.

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests

**Needs the Pi.** Start at one mode per sensor: configure lines unchanged.

**Risk.** Low.

**Depends on.** CAM-1

## CAM-33. Both drivers audit their static tables at every probe; imx585 warns about a known duplicate on every boot

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | fix-later | Driver-imx585-F6, Driver-imx283-F7 |

**Where.** `imx585.c:4478-4586, :2962-2966@cinemate-port`; `imx585 tools/check_window_alignment.py:9; tools/replay_mode_table_audit.py@cinemate-port`; `imx283.c:1757-1924, :3202-3207@cinemate-port`

**Problem.** imx585_check_mode_table() runs at each probe; its table-wide duplicate check warns about 3840x2072 at [5] and [67] on every boot although they never share a get_mode_table range. The window predicate exists four times (driver, audit, two Python tools). imx283_check_mode_table is ~150 lines, six checks, dev_warn only, every probe.

**Apertar way.** No precedent: neither base driver has a probe audit.

**Rework.**

1. imx585: add 'static bool imx585_window_ok(const struct imx585_mode *m)' and use it in imx585_program_window(). Delete the probe audit (the tables are static and the host tool covers them) or scope its duplicate check per range. Merge the two Python tools into one.
2. imx283: move the audit to a host script in the driver repo, or keep only the crop-inside-active and binning-non-zero checks.

**Owner decision.** None.

**Check here.** python3 tools/replay_mode_table_audit.py passes.

**Needs the Pi.** dmesg after modprobe has no table warning.

**Risk.** Low.

**Depends on.** CAM-1

## CAM-34. Driver dead code: an unused VMAX override, identity wrappers, dead crop macros

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | minor | S | unknown | fix-later | Driver-imx585-F7, Driver-imx283-F3, Driver-imx283-F4 |

**Where.** `imx585.c:384-387, :2128, :3289-3299, :3312-3316, :4509-4530@cinemate-port`; `imx283.c:58-62, :399-412, :459-480, :709-742, :804-806, :1463, :1504, :2506-2509@cinemate-port`

**Problem.** imx585: min_vmax_default is 0 on every windowed entry (the only place it is read) and ignored on six others; two min_vmax literals are wrong (10-bit 1440x1080: 1150, derived 2230). imx283: imx283_output_width/height/crop return mode fields unchanged at 31 call sites (left from the reverted active-only experiment, a852cfe); imx283_find_nearest_mode replaces v4l2_find_nearest_size; IMX283_CROP_1X1 has no caller; three macros switch 236/924; three stale comments.

**Apertar way.** Driver author's imx585_mode computes min_hmax/min_vmax at run time (70bdb26 imx585.c:371-373); base imx283 uses mode fields and v4l2_find_nearest_size (imx283.c:1121@origin/master). STY-9.

**Rework.**

1. imx585: delete min_vmax_default, its initialisers, the ternaries in imx585_update_hmax and the audit check; fix or zero the two literals.
2. imx283: delete the three wrappers and use the mode fields; restore v4l2_find_nearest_size; add a host check that no table has duplicate transport sizes (tie-breaking differs).
3. imx283: delete IMX283_CROP_1X1 and IMX283_CROPPED_1X1_MODE; write '.left = 924' with a one-line derivation; delete the three stale comments.

**Owner decision.** None.

**Check here.** Read the diff.

**Needs the Pi.** dkms build; one take per sensor at a crop mode, frame size unchanged.

**Risk.** Low.

**Depends on.** CAM-10

## CAM-35. imx585 1440x1080 frames differently at 12-bit (1x1 window) and 10-bit (2x2 of 2880)

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | yes | fix-later | Driver-imx585-F3 |

**Where.** `imx585.c:1369-1374, :2125-2130@cinemate-port`; `Core src/camera/Imx585Modes.hpp:39-75@cinemate-port`

**Problem.** supported_modes[28] is a 1x1 crop {1200, 540, 1440, 1080}; supported_10bit_modes[2] is 2x2 over {480, 0, 2880, 2160}. Switching 12-bit to 10-bit keeps the size and changes the framing by 2x.

**Apertar way.** No precedent (no 1440x1080 or 10-bit table in the baseline); upstream sizes mean one field of view (recipe R6).

**Rework.**

1. Give both tables the same geometry (a 1x1 1440 window in the 10-bit table, or a 2x2 windowed 1440x1080 in the 12-bit table outside the HDR range), or name the difference in APERTAR.md and in the Core table comment.

**Owner decision.** None.

**Check here.** replay_mode_table_audit.py.

**Needs the Pi.** Frame grabs at 1440x1080 12-bit and 10-bit: same framing.

**Risk.** Low.

## CAM-36. imx585 12-bit Clear HDR offered on 27 1x1 crops without a recorded take

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | unknown | fix-later | Driver-imx585-F11 |

**Where.** `imx585.c:3086-3094@cinemate-port`; `APERTAR.md:160-172@cinemate-port`

**Problem.** The HDR-12 range is supported_modes[0..28]: binned 1080p, 4K and every 1x1 crop, including the 1920/2048 windows (host-only, 18c1eb2). Hardware evidence exists for 16-bit 1x1 crops and the seven full-field modes only; the 2x2 crops are gated for the same reason (unconfirmed risk).

**Apertar way.** The baseline offered 12-bit HDR at 4K only (imx585.c:1392-1394, :1429-1432@origin/apertar).

**Rework.**

1. Record one 12-bit HDR take at a 3840 crop and one at a 1920-window crop. If either fails, end the HDR-12 range after the 4K entry plus the validated crops.

**Owner decision.** None.

**Check here.** Nothing here.

**Needs the Pi.** The two takes; check DNGs for pedestal or merge artefacts.

**Risk.** None until the takes.

## CAM-37. imx283 MODE_1C window .top = 852 is centred on the old active area; .left 924 OB unchecked on raw

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | yes | fix-later | Driver-imx283-F9 |

**Where.** `imx283.c:808-835, :2632-2652@cinemate-port`

**Problem.** .top = 852 was centred against the old active.top = 108 and is programmed into VWINPOS; the corrected centre is 784, so the UHD window is 68 rows off. At .left 924 columns 0..95 were checked only on an ISP preview frame, so the DNG ActiveArea may be wrong.

**Apertar way.** No precedent.

**Rework.**

1. Take one raw 3936x2176 frame at .left 924 with .top 784 and one with .top 852; keep one value with a one-line comment.

**Owner decision.** None.

**Check here.** Nothing here.

**Needs the Pi.** The two raw frames; inspect rows/columns for optical black.

**Risk.** None until measured.

## CAM-38. Driver histories: experiments, reverts, fix-ups and WP numbers in subjects

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| commit | minor | M | no | fix-later | Driver-imx585-F12, Driver-imx283-F11 |

**Where.** `imx585-v4l2-driver git log origin/apertar..cinemate-port (55 commits)`; `imx283-v4l2-driver git log origin/master..cinemate-port (93 commits; 4350e3e..a852cfe experiment and revert)`

**Problem.** imx585: nine 'experimental:' commits on one day, about seven fix-ups of earlier commits, WP-585-n in 13 subjects. imx283: an 11-commit experiment and its revert, WP-283-n in 7 subjects; 6 commits are Will Whang's origin/6.12.y history.

**Apertar way.** The driver author's commits are one feature each with a plain subject (3680bf4, c0f5404, 11178c8, 70bdb26); STY-15.

**Rework.**

1. imx585: keep Will Whang's four commits; squash Patrik's into about six feature commits (mode families and window programming, RAW10 families, binned Clear HDR, crop reporting and geometry controls, logging, docs).
2. imx283: rebase on origin/6.12.y; squash into one mode-set commit plus 4a1662e, d810aa7, d6ec1c7, 4064e88 and one docs commit.
3. Do it after CAM-1, CAM-10, CAM-12 and CAM-27 land, so the squashed history shows the final tables.

**Owner decision.** None.

**Check here.** git diff of the squashed branch against the pre-squash tip is empty.

**Needs the Pi.** Nothing.

**Risk.** Force-push of a shared branch; Cinemate uses it.

**Depends on.** CAM-1, CAM-10, CAM-12, CAM-27

## CAM-39. imx283 IMX283_ASPECT_MODE takes 15 positional arguments; parent timing repeated in 51 rows

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | minor | S | yes | fix-later | Driver-imx283-F6 |

**Where.** `imx283.c:694-707, :1060-1111, :1466-1474@cinemate-port`

**Problem.** Rows read IMX283_ASPECT_MODE(IMX283_MODE_0, 12, 3648, 3648, 887, 3793, 3793, 900, 4000, 12, 3694, 1, 1, 96, 16); a change to a parent's timing must be repeated in every row.

**Apertar way.** imx585 baseline uses small macros over the numbers that vary, IMX585_WIN_CROP_REGS(vst, vwidth) (imx585.c:563-572@origin/apertar); the port's own IMX283_ASPECT_MODE_1C(_w, _h) (imx283.c:862) has that shape.

**Rework.**

1. One (_w, _h) wrapper per family (MODE_0/2/2A/3/1/1A) over the generic macro, like _1C; keep the CENTERED_RECTANGLE derivation. After CAM-10 the last per-row timing argument is gone.

**Owner decision.** None.

**Check here.** Preprocess both versions (gcc -E on the table only) and diff the expanded rows.

**Needs the Pi.** Nothing if the expansion is identical.

**Risk.** Low.

**Depends on.** CAM-10

## CAM-40. {res} clip-name token labels by width only

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| bug | minor | S | no | fix-later | CC-1-F11 |

**Where.** `src/camera/CameraController.cpp:1123-1130@cinemate-port`

**Problem.** width >= 3500 gives '4K', 1900-1999 gives '1080p', otherwise '<height>p'. An IMX283 5472x3648 or IMX477 4056x3040 take is named '4K'; 1332x990 gives '990p'. Only templates that use {res} are affected.

**Apertar way.** No precedent (clip names are format_date_clip upstream).

**Rework.**

1. Emit '<width>x<height>' for {res}, or explicit classes (UHD, DCI 4K, 5K, 6K); update the token help text.

**Owner decision.** None.

**Check here.** tools/clip_name_test.cpp gains the three sizes.

**Needs the Pi.** Nothing.

**Risk.** Low.

## CAM-41. Rung::compression is a free string mixing record format and compression

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | minor | S | no | fix-later | Camera-headers-F6 |

**Where.** `src/camera/ModeLadder.hpp:22-44, :160-166@cinemate-port`; `CC:10951@cinemate-port`

**Problem.** std::string compression = "" | none | lossless_jpeg | lossy_3to1 | lossy_5to1, compared as strings through the ladder code; lossy implies the LossyDng format.

**Apertar way.** rule CAM-12 / rule CAM-26: each sub-option is its own enum (RecordingFormat, CdngCompression, LossyDngRatio, Types.hpp:45-68@upstream-1.6.0) with toString and a reverse parser.

**Rework.**

1. enum class RungRecord { Default, Uncompressed, Lossless, Lossy3, Lossy5 } with toString / rungRecordFromString over the existing wire words; fillRungExtrasLocked iterates the enum.

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; ladder host test passes; get_mode_ladder reply unchanged.

**Needs the Pi.** Nothing.

**Risk.** Low.

**Depends on.** CAM-8

## CAM-42. Read-only Mode geometry controls in both drivers have no Apertar consumer

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| new-ground | nit | S | yes | keep-and-document | Driver-imx585-F13, Driver-imx283-F12 |

**Where.** `imx585.c:44-50, :3354-3367@cinemate-port`; `imx283.c:25-65, :2221-2300, :2387-2426@cinemate-port`

**Problem.** Mode Binning and Mode Crop Left/Top/Width/Height (plus imx283's nine controls at V4L2_CID_USER_BASE+0x2100) are custom read-only controls read by cinepi-raw; Apertar Core reads the selection API.

**Apertar way.** No precedent; V4L2_SEL_TGT_CROP carries the same data.

**Rework.**

1. Keep (cheap, shared with Cinemate). One APERTAR.md line per driver: 'Cinemate reads these; Apertar uses the selection API.'

**Owner decision.** None.

**Check here.** Read APERTAR.md.

**Needs the Pi.** Nothing.

**Risk.** None.

## CAM-43. imx283 base sizes 2784x1548 (MODE_2A) and 5568x3094 (MODE_1A) replaced

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| removed | nit | S | yes | keep-and-document | Driver-imx283-F13 |

**Where.** `imx283.c:1102-1111, :1168@cinemate-port; imx283.c:467-512@origin/master`

**Problem.** The full MODE_2A entry became ten 2736-wide rows; MODE_1A goes from 3078 to 3076 rows (even Bayer origin). Third-party apps asking for the old sizes get the nearest row. 1.6.0 Apertar never requested them.

**Apertar way.** No Apertar precedent (no IMX283 in 1.6.0).

**Rework.**

1. One line in imx283 APERTAR.md naming the two changed sizes and the reason.

**Owner decision.** None.

**Check here.** Read APERTAR.md.

**Needs the Pi.** Nothing.

**Risk.** None.

## CAM-44. CdngLog accepts spellings that never shipped; CdngLog::Auto means On

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| slop | nit | S | yes | fix-later | Camera-headers-F14 |

**Where.** `include/apertar/core/Types.hpp:59-62, :326-346@cinemate-port`; `src/camera/ModeLadder.hpp:168, :337@cinemate-port`

**Problem.** 'on', '12', '10', '8' map to Auto; the ladder accepts log10/log8; the ladder file reads the old rungs key. None of these was in an Apertar release.

**Apertar way.** rule CAM-25 keeps retired keys users had; these were port-internal only.

**Rework.**

1. enum class CdngLog { Off, On } with wire values off/on; accept 'auto' only if the owner's camera_settings.conf holds it; drop 12/10/8, log10/log8 and rungs (rungs goes with CAM-8).

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests; grep cdng_log in the owner's settings copy before choosing.

**Needs the Pi.** Nothing.

**Risk.** Low.

**Depends on.** CAM-8

## CAM-45. Small CameraController nits: include order, public data members, namespace spelling, lone assert, repeated mono expression, duplicated row loop

| Kind | Severity | Effort | Deliberate | Recommendation | Sources |
| --- | --- | --- | --- | --- | --- |
| mismatch | nit | S | no | fix-later | CC-1-F12, CC-1-F13, CC-4-F12, CC-5-F13, CC-1-F10 |

**Where.** `src/camera/CameraController.cpp:1-3, :43, :180, :660, :1157, :2268, :4596@cinemate-port`; `CC:8186-8187@cinemate-port`; `CC:10655, :10669, :10713, :10797, :10840, :11599, :11644, :12861@cinemate-port`; `CC:1647-1656, :1671-1680@cinemate-port`

**Problem.** FramePhaseLock.hpp, FpsCeiling.hpp and <optional> sit above the file's own header; activeTuningMutex_ and activeTuningFile_ sit in CameraSession's public section; imx283:: vs apertar::imx585::; JSON ladder_resolution from member ladderRung; a {cam} token that is always cam0; <cassert> for one assert; #endif followed directly by enum class; '(!simulateCamera_ && session_ && session_->monochromeSensor())' written eight times; applyCdngLogFrame repeats compressClearHdrFrame's row loop.

**Apertar way.** STY-5 own header first (CC:1@upstream-1.6.0); CameraSession members private at the end (CC:5918@upstream-1.6.0); one local per setter (CC:7722-7724@upstream-1.6.0); only static_assert (CC:1697@upstream-1.6.0).

**Rework.**

1. Move the three includes into the project and std groups.
2. Move the two members into the private block.
3. Short namespace form for both tables; rename the member to ladderResolution; drop {cam}; replace the assert by an explicit check; blank line after #endif.
4. One 'const bool monochrome = ...;' local per setter beside sensorFamily.
5. Leave the two row loops (fork-main code, small) unless the Log code is touched again.

**Owner decision.** None.

**Check here.** /home/user/build/bin/check_core.sh /home/user/wt/core-work core-work both tests

**Needs the Pi.** Nothing.

**Risk.** None.

**Depends on.** CAM-2

## What conforms (for the handoff)

- 27 settings fields added in place, none removed, renamed or reordered; the same fields added to both App serialisers (rule CAM-25, CMD conventions; CC:163-246@cinemate-port).
- New persisted keys as else-if branches inside the existing try, per-profile prefix unchanged (rule CAM-25; CC:817-900@cinemate-port).
- Camera-wide switches (preview_tdn, cdng_log, clip_name_template, timecode) carried across format profiles exactly where upstream carries tuningFile/timecodeMode (rule CAM-40; CC:11338-11372@cinemate-port vs CC:7945-7951@upstream-1.6.0).
- Runtime fields on CaptureSettings with a trailing 'Runtime ..., not persisted' comment: isoMax, fpsMax, isoMeasured, cdngLogApplied (rule CAM-18).
- New setters (setCdngLog, setFpsPhaseLock, setPreviewTdn, setMediaTrimEnabled) are bool setters on the one class under one mutex: lock, gate with a sentence, applySettingsLocked (rule CAM-7, rule CAM-8, rule CAM-10).
- IMX283 added by recipe R5: a fifth SensorFamily, a substring in detectSensorFamily, a case in each sensor switch, the ScalerCrop branch inside controlsForSettings and crop maths beside upstream's in ScalerCropGeometry.hpp (rule CAM-9, rule CAM-11).
- Mode tables and the ladder as pure header-only std code (Imx585Modes.hpp, Imx283Modes.hpp, ModeLadder.hpp, FramePhaseLock.hpp; rule CAM-4); no libcamera include in any new header (rule CAM-1).
- Every new session accessor has the #if APERTARCORE_HAS_LIBCAMERA ... #else neutral stub; Core builds without libcamera (rule CAM-28).
- measuredAnalogueGain() copies measuredWhiteBalance() exactly (same mutex, same stub).
- New sensor quirks sit inside the candidate loop after configure with upstream's rejectionLog format (CC:8519-8524@cinemate-port vs CC:6170-6178@upstream-1.6.0).
- stopRecording(bool mediumGone) is reached through upstream's checkRecordingFailure supervisor and keeps the recorder stop order.
- Log lines keep 'ApertarCore <area>: key=value'; new warnings are rate-limited with n == 1 || n % 30 == 0 (STY-7, rule CAM-23).
- APERTAR_RAW_CAMERA_BUFFERS and APERTAR_FPS_RAMP_GRACE_FRAMES are shaped like upstream bench knobs (unsignedEnvValue, bounds, default) (rule CAM-24).
- Speed ramp is opt-in (fpsSpeedRamp = false); H.264, ProRes and stills keep the fps refusal in a take; the completion thread never waits for storage (rule CAM-30, rule CAM-31).
- setModeLadder and setClearHdr roll back on a failed apply (rule CAM-34); saveModeLadderLocked uses settingsFile::atomicWrite (rule CAM-29).
- nextClipFolderName throws upstream's exact sentence and takes the lowest free number (rule CAM-37).
- Drivers: the four Will Whang commits, his HMAX tables, RAW10 table, Clear HDR HMAX floor and ccmp gate structure kept; imx585_program_window() uses cci_write with error returns; crop reported in native sensor coordinates; no new Kconfig, sysfs or debugfs; Makefile, dkms and setup.sh unchanged; no existing control default changed; 18 of the 20 sizes 1.6.0 Core requests are still advertised.
- imx283: experimental_modes defaults off; CROP_DEFAULT returns the active area; TRY-state crop fix; get_format_code bounds check; HTRIMMING_END = left + width as mainline; kernel 6.12 API matches the imx585 base.

## Left out, with the reason

- CC-1-F8: dropped by the unit skeptic; upstream clampCaptureSettings also normalises a string (exposureMetering, CC:534-535@upstream-1.6.0).
- Camera-headers-F8: dropped by the unit skeptic; upstream replies already carry arrays of objects (modes, App:10042-10048@upstream-1.6.0).
- X-state-consistency-8 (iso_actual 0 in the settings event): not a defect to fix; upstream does the same for wb_actual_* (CC:159, :8572@upstream-1.6.0) and no UI shows a wrong value.
- X-state-consistency-12 (ladder_tops precision): duplicate of APP-46 in the core-app list.
- X-state-consistency-14 (preview_tdn and media_trim not preset fields): duplicate of APP-47 in the core-app list.
- X-stock-behaviour-5 / X-knobs-3 (automatic storage pre-roll): APP-2 in the core-app list; the CC mechanism is CAM-6.
- X-board-support-8 (raw copy pool kept between takes): media-writer code in the CC-3 slice, other editor.
- X-board-support-7 copy-worker, per-file sync and pre-roll parts: media-writer editor; the request-count part is CAM-7.
- X-board-support-12 (APERTAR_RT taskset): APP-15 in the core-app list.
- X-state-consistency-2, -4, -5 (touch UI fps_take_max, IMX585 100/120 fallback, old FPS ceiling copies): UI and WCP editors; Core needs no change.
- X-stock-behaviour-10 UI half (Auto offered in every UI): UI and WCP editors; the Core half is CAM-14.
- X-knobs-12 hold_ms/double_ms and directIo parts: hardware and media editors; conform_fps part is CAM-18.
